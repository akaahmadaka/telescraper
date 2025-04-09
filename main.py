"""
Telescraper - Main application entry point.

Continuously scrapes DuckDuckGo Search results (via library) for keywords, extracts Telegram links
from the found pages, stores them in an SQLite database, and avoids re-processing URLs.
"""

import time
import sys
import signal
import asyncio
import queue      # Added for thread-safe queue
import threading  # Added for running sender in a separate thread

# Project imports
import config
from utils.logger import log, setup_logger
from utils.helpers import polite_delay
from database import db_manager
from scraper import search_engine, link_extractor
from bot import telegram_sender

# --- Global Variables ---
shutdown_requested = False
message_queue = queue.Queue() # Queue for sending messages to Telegram thread

def signal_handler(sig, frame):
    """Handles termination signals (like Ctrl+C) for graceful shutdown."""
    global shutdown_requested
    if not shutdown_requested:
        log.warning(f"Shutdown requested (Signal: {sig}). Finishing current tasks...")
        shutdown_requested = True
    else:
        log.warning("Forcing exit...")
        sys.exit(1) 

# --- Telegram Sender Thread ---

def telegram_sender_worker(q):
    """Worker function running in a separate thread to send Telegram messages."""
    log.info("Telegram sender thread started.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        item = q.get() # Blocks until an item is available
        if item is None:
            log.info("Received sentinel value, stopping Telegram sender thread.")
            break # Sentinel value received, exit loop

        tg_link, url, keyword = item
        log.debug(f"Sender thread received task: Send {tg_link}")
        try:
            # Run the coroutine directly on the thread's event loop
            result = loop.run_until_complete(
                telegram_sender.send_link(tg_link, url, keyword)
            )
            if not result:
                 log.warning(f"Telegram send_link function returned False for {tg_link}")
        # TimeoutError is less likely with run_until_complete unless send_link itself hangs indefinitely
        # Keep general exception handling
        except Exception as e:
            log.error(f"Error running send_link in sender thread: {e}", exc_info=True)
        finally:
            q.task_done() # Signal that the task from the queue is done

    loop.call_soon_threadsafe(loop.stop) # Stop the loop cleanly
    # loop.close() # Close the loop - careful with timing
    log.info("Telegram sender thread finished.")


# --- Main Scraping Logic ---

def run_scraper_cycle():
    """
    Runs a single cycle of scraping for all configured keywords.
    Finds URLs from search results, processes them, adds Telegram links to DB,
    and queues newly found internal links for later processing.
    """
    log.info("Starting new scraping cycle...")
    total_links_added_cycle = 0

    for i, keyword in enumerate(config.KEYWORDS):
        if shutdown_requested:
            log.info("Shutdown detected, skipping remaining keywords in this cycle.")
            break

        log.info(f"Processing keyword: '{keyword}' ({i+1}/{len(config.KEYWORDS)})")

        # 1. Perform Search using DuckDuckGo library
        try:
            search_result_urls = search_engine.perform_duckduckgo_search( # Use DuckDuckGo search function
                keyword,
                pages_to_request=config.SEARCH_PAGES_TO_REQUEST # Pass the configured number of pages (currently ignored)
            )
        except Exception as e:
            log.error(f"Unhandled error during DuckDuckGo search for '{keyword}': {e}", exc_info=True)
            search_result_urls = [] # Continue with next keyword

        if not search_result_urls:
            log.info(f"No search result URLs found for keyword '{keyword}'.")
        else:
            log.info(f"Found {len(search_result_urls)} URLs from search for '{keyword}'. Processing...")

            # 2. Extract Telegram Links from each search result URL
            for j, url in enumerate(search_result_urls):
                if shutdown_requested:
                    log.info("Shutdown detected, stopping URL processing for this keyword.")
                    break

                # Check if URL has already been processed
                if db_manager.is_url_processed(url):
                    log.debug(f"Skipping already processed URL: {url}")
                    continue # Skip to the next URL

                log.debug(f"Processing URL {j+1}/{len(search_result_urls)}: {url}")
                extraction_successful = False
                try:
                    # Extractor now returns two sets: telegram links and internal links
                    telegram_links, internal_links = link_extractor.extract_telegram_links(url)
                    # Mark as successful if no critical exception occurred during extraction
                    # (even if 0 links were found, or if network errors like timeout/HTTPError happened inside)
                    extraction_successful = True
                except Exception as e:
                    # Catch potential critical errors *outside* the extractor's own handling
                    log.error(f"Unhandled critical error during link extraction call for '{url}': {e}", exc_info=True)
                    telegram_links = set()
                    internal_links = set() # Ensure internal_links is defined even on error
                    # Don't mark as processed if the call itself failed critically

                # Mark URL as processed and queue internal links only if the extraction call completed
                if extraction_successful:
                    db_manager.add_processed_url(url)
                    if internal_links:
                        db_manager.add_to_url_queue(internal_links)

                # 3. Add found Telegram links to Database
                links_added_this_url = 0
                for tg_link in telegram_links:
                    if shutdown_requested:
                        log.info("Shutdown detected, stopping database additions.")
                        break # Stop adding links

                    try:
                        added = db_manager.add_telegram_link(tg_link, url, keyword)
                        if added:
                            links_added_this_url += 1
                            # Send notification via Telegram Bot
                            # Put message details into the queue for the sender thread
                            if config.BOT_ENABLED:
                                message_queue.put((tg_link, url, keyword))
                    except Exception as e:
                         log.error(f"Unhandled error adding link '{tg_link}' to DB: {e}", exc_info=True)
                         # Decide whether to break or continue

                total_links_added_cycle += links_added_this_url
                log.debug(f"Added {links_added_this_url} new links from {url}")

                # Polite delay between fetching individual pages
                if j < len(search_result_urls) - 1 and not shutdown_requested:
                    polite_delay(config.FETCH_DELAY_SECONDS)

        # Polite delay between different keyword searches
        if i < len(config.KEYWORDS) - 1 and not shutdown_requested:
            log.info(f"Waiting before next keyword search...")
            polite_delay(config.SEARCH_DELAY_SECONDS)

    # Removed redundant log message, combined results are logged in main()
    return total_links_added_cycle


def process_url_queue(batch_size=10):
    """
    Processes a batch of URLs from the database queue.
    Fetches URLs, extracts links, adds Telegram links to DB,
    adds new internal links back to the queue, and marks URLs as processed.
    """
    log.info(f"Checking URL queue for up to {batch_size} URLs to process...")
    urls_to_process = db_manager.get_next_url_from_queue(batch_size)

    if not urls_to_process:
        log.info("URL queue is empty.")
        return 0

    log.info(f"Processing {len(urls_to_process)} URLs from the queue...")
    total_links_added_queue = 0

    for i, url in enumerate(urls_to_process):
        if shutdown_requested:
            log.info("Shutdown detected, stopping URL queue processing.")
            # Note: URLs fetched but not processed remain removed from the queue.
            # They might be re-added later if found again via search/crawl.
            break

        # Double-check if URL has already been processed (e.g., added via search results in the same cycle)
        if db_manager.is_url_processed(url):
            log.debug(f"Skipping already processed URL from queue: {url}")
            continue

        log.debug(f"Processing queued URL {i+1}/{len(urls_to_process)}: {url}")
        extraction_successful = False
        try:
            telegram_links, internal_links = link_extractor.extract_telegram_links(url)
            extraction_successful = True
        except Exception as e:
            log.error(f"Unhandled critical error during link extraction call for queued URL '{url}': {e}", exc_info=True)
            telegram_links = set()
            internal_links = set()

        # Mark URL as processed and queue internal links if extraction completed
        if extraction_successful:
            db_manager.add_processed_url(url)
            if internal_links:
                db_manager.add_to_url_queue(internal_links)

        # Add found Telegram links to Database (use a generic keyword like 'queued')
        links_added_this_url = 0
        for tg_link in telegram_links:
            if shutdown_requested:
                log.info("Shutdown detected, stopping database additions from queue.")
                break

            try:
                # Using "queued" as the keyword for links found via the queue
                added = db_manager.add_telegram_link(tg_link, url, "queued")
                if added:
                    links_added_this_url += 1
                    # Send notification via Telegram Bot
                    # Put message details into the queue for the sender thread
                    if config.BOT_ENABLED:
                        message_queue.put((tg_link, url, "queued"))
            except Exception as e:
                 log.error(f"Unhandled error adding queued link '{tg_link}' to DB: {e}", exc_info=True)

        total_links_added_queue += links_added_this_url
        log.debug(f"Added {links_added_this_url} new links from queued URL {url}")

        # Polite delay between fetching pages from the queue
        if i < len(urls_to_process) - 1 and not shutdown_requested:
            polite_delay(config.FETCH_DELAY_SECONDS)

    log.info(f"URL queue processing finished for this batch. Added {total_links_added_queue} new links.")
    return total_links_added_queue


def main():
    """Main function to initialize and run the scraper."""
    # Setup logger (might be already initialized, but ensures it's ready)
    setup_logger()
    log.info("--- Telescraper Starting ---")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Handle termination signals

    # Setup Database
    log.info("Initializing database...")
    if not db_manager.setup_database():
        log.critical("Database setup failed. Exiting.")
        sys.exit(1)
    log.info("Database setup complete.")

    # Start the Telegram sender thread if enabled
    sender_thread = None
    if config.BOT_ENABLED and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" and config.CHAT_ID != "YOUR_CHAT_ID_HERE":
        sender_thread = threading.Thread(target=telegram_sender_worker, args=(message_queue,), daemon=True)
        sender_thread.start()
    else:
         log.info("Telegram bot not fully configured or disabled, sender thread not started.")

    # Main Loop
    cycle_count = 0
    try:
        while not shutdown_requested:
            cycle_count += 1
            log.info(f"--- Starting Cycle {cycle_count} ---")
            # Run keyword scraping cycle
            links_added_keywords = run_scraper_cycle()

            # Process a batch from the URL queue if not shutting down
            links_added_queue = 0
            if not shutdown_requested:
                links_added_queue = process_url_queue(batch_size=config.QUEUE_BATCH_SIZE if hasattr(config, 'QUEUE_BATCH_SIZE') else 10) # Add batch size config later if needed

            total_added = links_added_keywords + links_added_queue
            log.info(f"Cycle {cycle_count} complete. Total links added this cycle: {total_added} (Keywords: {links_added_keywords}, Queue: {links_added_queue})")

            if not shutdown_requested:
                log.info(f"Waiting for {config.CYCLE_DELAY_SECONDS} seconds before next cycle...")
                # Use time.sleep directly here, or helpers.polite_delay
                # Need to handle interruption during sleep
                try:
                    # Sleep in smaller chunks to check shutdown_requested more often
                    sleep_interval = 1 # Check every second
                    end_time = time.time() + config.CYCLE_DELAY_SECONDS
                    while time.time() < end_time and not shutdown_requested:
                        time.sleep(sleep_interval)
                except InterruptedError: # Should be caught by signal handler, but just in case
                     log.warning("Sleep interrupted.")
                     break # Exit loop if sleep is interrupted

    except Exception as e:
        log.critical(f"An unexpected critical error occurred in the main loop: {e}", exc_info=True)
    finally:
        log.info("--- Telescraper Shutting Down ---")

        # Signal the sender thread to stop and wait for it
        if sender_thread and sender_thread.is_alive():
            log.info("Signaling Telegram sender thread to stop...")
            message_queue.put(None) # Send sentinel value
            log.info("Waiting for message queue to empty...")
            message_queue.join() # Wait for all queued messages to be processed
            log.info("Waiting for sender thread to join...")
            sender_thread.join(timeout=10) # Wait for thread to finish
            if sender_thread.is_alive():
                log.warning("Telegram sender thread did not exit cleanly.")

        # Perform any other cleanup if needed
        # DB connections are closed after each operation in db_manager currently.
        log.info("Shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    main()
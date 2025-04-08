"""
Handles sending notifications via Telegram Bot.
"""

import time
import asyncio # Added for async operations
import telegram
from telegram.error import TelegramError
from telegram.helpers import escape_markdown # Added for escaping

import config
from utils.logger import log

# Initialize the bot instance (if token is provided)
bot = None
if config.BOT_ENABLED and config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
    try:
        bot = telegram.Bot(token=config.BOT_TOKEN)
        log.info("Telegram Bot initialized successfully.")
    except TelegramError as e:
        log.error(f"Failed to initialize Telegram Bot: {e}. Notifications disabled.", exc_info=True)
        bot = None # Ensure bot is None if initialization fails
else:
    if config.BOT_ENABLED:
        log.warning("Telegram Bot is enabled in config, but BOT_TOKEN is not set. Notifications disabled.")
    else:
        log.info("Telegram Bot notifications are disabled in config.")

async def send_link(telegram_link, source_url, keyword):
    """
    Sends a message containing the found Telegram link to the configured chat ID.

    Args:
        telegram_link (str): The Telegram link found.
        source_url (str): The URL where the link was found.
        keyword (str): The keyword associated with the finding.

    Returns:
        bool: True if the message was sent successfully (or if bot is disabled), False otherwise.
    """
    if not config.BOT_ENABLED or not bot or config.CHAT_ID == "YOUR_CHAT_ID_HERE":
        log.debug("Telegram Bot is disabled or not configured. Skipping notification.")
        return True # Return True as no action needed/failed

    # Escape potential MarkdownV2 special characters in user-provided content
    escaped_link = escape_markdown(telegram_link, version=2)
    escaped_source = escape_markdown(source_url, version=2)
    escaped_keyword = escape_markdown(keyword, version=2)

    # Note: The literal parts of the message also need escaping if they contain special chars.
    # '!' needs escaping. '.' is also reserved but often works without escaping in practice.
    message = (
        f"🔗 *New Link Found\\!* \n\n" # Escape the '!'
        f"*Link:* {escaped_link}\n"
        # Removed Source and Keyword lines as requested
    )

    try:
        log.debug(f"Attempting to send link to Telegram Chat ID: {config.CHAT_ID}")
        await bot.send_message(
            chat_id=config.CHAT_ID,
            text=message,
            parse_mode='MarkdownV2', # Use MarkdownV2 for formatting
            disable_web_page_preview=False # Optional: disable link previews
        )
        log.info(f"Successfully sent link {telegram_link} to Telegram.")

        # --- Rate Limiting ---
        # Wait *after* sending to respect API limits
        await asyncio.sleep(config.BOT_SEND_DELAY_SECONDS)
        return True

    except TelegramError as e:
        log.error(f"Failed to send message to Telegram Chat ID {config.CHAT_ID}: {e}", exc_info=True)
        # Handle specific errors if needed (e.g., chat not found, bot blocked)
        if "chat not found" in str(e):
            log.error("Please check if the BOT_TOKEN and CHAT_ID are correct and the bot is added to the chat.")
        elif "bot was blocked by the user" in str(e):
             log.error("The bot was blocked by the user/chat.")
        # Consider disabling bot temporarily if errors persist?
        return False
    except Exception as e:
        # Catch any other unexpected errors
        log.error(f"An unexpected error occurred while sending Telegram message: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # Example usage for testing (requires config.py to be set up)
    print("--- Testing Telegram Sender ---")
    if config.BOT_ENABLED and bot and config.CHAT_ID != "YOUR_CHAT_ID_HERE":
        print("Attempting to send a test message...")
        # Need to run the async function
        async def run_test():
            return await send_link(
                "https://t.me/testgroup_example",
                "http://example.com/testpage",
                "test keyword"
            )
        test_success = asyncio.run(run_test())
        if test_success:
            print("Test message send initiated successfully (check your Telegram chat).")
        else:
            print("Failed to send test message. Check logs and configuration.")
    else:
        print("Telegram Bot is disabled or not configured in config.py. Skipping test.")
    print("--- Test Complete ---")
"""
Fetches content from a given URL and extracts Telegram links (t.me/...).
"""

import requests
from bs4 import BeautifulSoup
import re
import gc # Import garbage collector module
from urllib.parse import urljoin, urlparse

import config
from utils.logger import log

# Regex to find Telegram links (more robust than just checking startswith)
# Handles http/https and potential variations in t.me links
TELEGRAM_LINK_PATTERN = re.compile(r"https?://(?:www\.)?t(?:elegram)?\.me/([\w/]+)")

def extract_telegram_links(source_url):
    """
    Fetches a webpage and extracts unique Telegram links and internal links found within it.

    Args:
        source_url (str): The URL of the webpage to scrape.

    Returns:
        tuple: A tuple containing two sets:
               - set: Unique, normalized Telegram links (e.g., 'https://t.me/groupname').
               - set: Unique, absolute internal links found on the page.
               Returns (set(), set()) if errors occur or no links are found.
    """
    log.debug(f"Attempting to extract Telegram links from: {source_url}")
    found_telegram_links = set()
    found_internal_links = set()
    source_domain = urlparse(source_url).netloc
    headers = {'User-Agent': config.USER_AGENT}
    page_content = b''
    downloaded_size = 0
    size_limit_exceeded = False
    soup = None # Initialize soup variable

    try:
        # Use stream=True to download content incrementally
        response = requests.get(source_url, headers=headers, timeout=20, allow_redirects=True, stream=True)
        response.raise_for_status() # Check for HTTP errors early

        # Check content type - only parse HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            log.debug(f"Skipping non-HTML content ({content_type}) at: {source_url}")
            log.debug(f"Skipping non-HTML content ({content_type}) at: {source_url}")
            response.close() # Close the connection if not reading content
            return found_telegram_links, found_internal_links

        # Read content in chunks and check size limit
        chunk_size = 8192 # Read 8KB at a time
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk: # filter out keep-alive new chunks
                page_content += chunk
                downloaded_size += len(chunk)
                if config.MAX_DOWNLOAD_SIZE_BYTES and downloaded_size > config.MAX_DOWNLOAD_SIZE_BYTES:
                    log.warning(f"Download limit ({config.MAX_DOWNLOAD_SIZE_BYTES} bytes) exceeded for {source_url}. Skipping parsing.")
                    size_limit_exceeded = True
                    break # Stop downloading

        response.close() # Ensure connection is closed after reading

        if size_limit_exceeded:
            return found_telegram_links, found_internal_links # Return empty sets if size limit hit

        # Decode content before parsing (assuming UTF-8, ignore errors)
        try:
            decoded_content = page_content.decode('utf-8', errors='ignore')
        except UnicodeDecodeError as e:
             log.warning(f"Could not decode content from {source_url} as UTF-8: {e}. Skipping parsing.")
             return found_telegram_links, found_internal_links

        # Parse the accumulated content
        soup = BeautifulSoup(decoded_content, 'lxml')

        # Find all anchor tags
        anchor_tags = soup.find_all('a', href=True)
        log.debug(f"Found {len(anchor_tags)} anchor tags in {source_url}")

        for tag in anchor_tags:
            href = tag['href']
            # Resolve relative URLs (though less common for external t.me links)
            # Clean the href before resolving (remove fragments, etc.)
            parsed_href = urlparse(href)
            clean_href = parsed_href._replace(fragment="").geturl()
            absolute_url = urljoin(source_url, clean_href)
            parsed_absolute_url = urlparse(absolute_url)

            # Skip non-http/https URLs
            if parsed_absolute_url.scheme not in ['http', 'https']:
                continue

            # Check if it matches the Telegram pattern
            match = TELEGRAM_LINK_PATTERN.match(absolute_url)
            if match:
                # Normalize the Telegram link
                telegram_path = match.group(1).rstrip('/')
                normalized_link = f"{config.TELEGRAM_BASE_URL}{telegram_path}"
                # Filter out preview links
                if "/s/" not in normalized_link:
                    log.debug(f"Found potential Telegram link: {normalized_link} (from {href})")
                    found_telegram_links.add(normalized_link)
                else:
                    log.debug(f"Skipping Telegram preview link: {normalized_link}")
            # Check if it's an internal link (same domain as source)
            elif parsed_absolute_url.netloc == source_domain:
                 # Optional: Add more filtering here (e.g., ignore image/css links)
                 log.debug(f"Found potential internal link: {absolute_url} (from {href})")
                 found_internal_links.add(absolute_url)



    except requests.exceptions.Timeout:
        log.warning(f"Timeout while fetching {source_url}")
    except requests.exceptions.HTTPError as e:
        # Log HTTP errors specifically, including the status code
        status_code = e.response.status_code if e.response else 'Unknown'
        log.warning(f"HTTP error fetching {source_url}: Status Code {status_code}")
    except requests.exceptions.RequestException as e:
        # Log other request errors (connection, timeout handled separately, etc.)
        log.warning(f"Request error fetching {source_url}: {e.__class__.__name__}")
    except Exception as e:
        # Catch potential BeautifulSoup errors or others
        log.error(f"Error processing {source_url}: {e}", exc_info=True)
    finally:
        # Explicitly delete large objects and suggest garbage collection
        del soup
        del page_content
        # del decoded_content # This might cause UnboundLocalError if decoding failed
        gc.collect()

    log.info(f"Extracted {len(found_telegram_links)} Telegram link(s) and {len(found_internal_links)} internal link(s) from {source_url}")

    return found_telegram_links, found_internal_links

if __name__ == '__main__':
    # Example usage if run directly
    test_url_with_links = "https://gist.github.com/rоо/50180177a685a63f4bac76250715cca4" # A dummy gist with some links
    test_url_without_links = "https://example.com"
    test_url_invalid = "invalid-url"
    test_url_non_html = "https://via.placeholder.com/150.png" # An image URL

    print(f"--- Testing URL: {test_url_with_links} ---")
    tg_links1, int_links1 = extract_telegram_links(test_url_with_links)
    print(f"Found TG links: {tg_links1}")
    print(f"Found Internal links: {int_links1}\n")

    print(f"--- Testing URL: {test_url_without_links} ---")
    tg_links2, int_links2 = extract_telegram_links(test_url_without_links)
    print(f"Found TG links: {tg_links2}")
    print(f"Found Internal links: {int_links2}\n")

    print(f"--- Testing URL: {test_url_invalid} ---")
    tg_links3, int_links3 = extract_telegram_links(test_url_invalid)
    print(f"Found TG links: {tg_links3}")
    print(f"Found Internal links: {int_links3}\n")

    print(f"--- Testing URL: {test_url_non_html} ---")
    tg_links4, int_links4 = extract_telegram_links(test_url_non_html)
    print(f"Found TG links: {tg_links4}")
    print(f"Found Internal links: {int_links4}\n")
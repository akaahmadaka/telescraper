"""
Handles searching using DuckDuckGo's HTML version (html.duckduckgo.com).
"""

import requests
from bs4 import BeautifulSoup # Used for parsing the single page result
import time
import random
from urllib.parse import urlencode

import config
from utils.logger import log

# --- DuckDuckGo HTML Configuration ---
DDG_HTML_URL = "https://html.duckduckgo.com/html/"

# CSS Selector for result links on the HTML page (inspect the page source if this breaks)
# Links are typically within divs with class="result__body" inside an 'a' tag with class="result__a"
RESULT_LINK_SELECTOR = "a.result__a"

def perform_ddg_html_search(keyword, pages_to_request=1):
    """
    Performs a search using DuckDuckGo's HTML interface.

    Note: The DDG HTML interface has limited/unreliable pagination. This function
          currently only processes the *first* page of results, regardless of the
          `pages_to_request` parameter value. The parameter is kept for potential
          future enhancements or alternative search implementations.

    Args:
        keyword (str): The search term.
        pages_to_request (int): Number of pages requested (currently ignored beyond 1).

    Returns:
        list: A list of unique URLs found in the search results.
              Returns an empty list if errors occur or no results are found.
    """
    log.info(f"Starting DuckDuckGo HTML search for keyword: '{keyword}'")
    found_urls = set()
    headers = {'User-Agent': config.USER_AGENT}

    # DDG HTML uses POST requests for subsequent pages, but GET for the first.
    # Let's stick to GET for the first page as pagination is tricky/limited here.
    # If pages_to_request > 1, log a warning indicating it's currently ignored.
    # If pages_to_request > 1, log a warning indicating it's currently ignored.
    if pages_to_request > 1:
        log.warning(f"Requested {pages_to_request} pages from DDG HTML, but current implementation only processes the first page.")

    params = {'q': keyword}
    try:
        # Use POST for the search query itself on the HTML endpoint
        response = requests.post(DDG_HTML_URL, data=params, headers=headers, timeout=20)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'lxml')

        # Find result links using the CSS selector
        link_elements = soup.select(RESULT_LINK_SELECTOR)
        log.debug(f"Found {len(link_elements)} potential link elements on DDG HTML page.")

        if not link_elements:
             log.warning(f"No results found using selector '{RESULT_LINK_SELECTOR}' for '{keyword}' on DDG HTML page.")

        for link_tag in link_elements:
            url = link_tag.get('href')
            if url:
                # Basic validation
                if url.startswith('http://') or url.startswith('https://'):
                    log.debug(f"Extracted URL: {url}")
                    found_urls.add(url)
                else:
                    log.debug(f"Skipping invalid or relative URL: {url}")

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else 'N/A'
        log.error(f"RequestException during DDG HTML search for '{keyword}': {e.__class__.__name__} (Status: {status_code}) - {e}", exc_info=True)
    except Exception as e:
        log.error(f"Error parsing DuckDuckGo HTML search results for '{keyword}': {e}", exc_info=True)

    log.info(f"Finished DuckDuckGo HTML search for '{keyword}'. Found {len(found_urls)} unique URLs.")
    return list(found_urls)

# Update the main function name to be consistent if needed, or update main.py call
# Let's keep the function name specific for clarity: perform_ddg_html_search

if __name__ == '__main__':
    # Example usage if run directly
    test_keyword = "telegram public groups list" # Example from config
    print(f"Performing test DuckDuckGo HTML search for: '{test_keyword}'")
    results = perform_ddg_html_search(test_keyword, pages_to_request=1)

    if results:
        print("\nFound URLs:")
        for url in results:
            print(url)
    else:
        print("\nNo URLs found or an error occurred.")
        print("Check logs (telescraper.log).")
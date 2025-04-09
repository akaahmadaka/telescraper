"""
Handles searching using a web search engine (currently Bing).
"""

import requests
from bs4 import BeautifulSoup # Used for parsing the single page result
import time
import random
from urllib.parse import urlencode

import config
from utils.logger import log

# --- Bing Search Configuration ---
BING_SEARCH_URL = "https://www.bing.com/search"

# CSS Selector for result links on Bing (inspect page source if this breaks)
# Links are often within <li> elements with class="b_algo", inside an <h2> -> <a>
RESULT_LINK_SELECTOR = "li.b_algo h2 a"

def perform_bing_search(keyword, pages_to_request=1):
    """
    Performs a search using Bing.

    Note: Pagination is not implemented. This function currently only processes
          the first page of results, regardless of the `pages_to_request` parameter value.
          The parameter is kept for potential future enhancements.
    Args:
        keyword (str): The search term.
        pages_to_request (int): Number of pages requested (currently ignored beyond 1).

    Returns:
        list: A list of unique URLs found in the search results.
              Returns an empty list if errors occur or no results are found.
    """
    log.info(f"Starting Bing search for keyword: '{keyword}'")
    found_urls = set()
    # Use a more common browser User-Agent for Bing
    headers = {'User-Agent': config.USER_AGENT}

    if pages_to_request > 1:
        log.warning(f"Requested {pages_to_request} pages from Bing, but current implementation only processes the first page.")

    params = {'q': keyword}
    try:
        # Use GET for Bing search
        response = requests.get(BING_SEARCH_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'lxml')

        # Find result links using the CSS selector
        link_elements = soup.select(RESULT_LINK_SELECTOR)
        log.debug(f"Found {len(link_elements)} potential link elements on Bing results page.")

        if not link_elements:
             log.warning(f"No results found using selector '{RESULT_LINK_SELECTOR}' for '{keyword}' on Bing results page.")

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
        log.error(f"RequestException during Bing search for '{keyword}': {e.__class__.__name__} (Status: {status_code}) - {e}", exc_info=True)
    except Exception as e:
        log.error(f"Error parsing Bing search results for '{keyword}': {e}", exc_info=True)

    log.info(f"Finished Bing search for '{keyword}'. Found {len(found_urls)} unique URLs.")
    return list(found_urls)

# Renamed function to perform_bing_search

if __name__ == '__main__':
    # Example usage if run directly
    test_keyword = "telegram public groups list" # Example from config
    print(f"Performing test Bing search for: '{test_keyword}'")
    results = perform_bing_search(test_keyword, pages_to_request=1)

    if results:
        print("\nFound URLs:")
        for url in results:
            print(url)
    else:
        print("\nNo URLs found or an error occurred.")
        print("Check logs (if configured).")
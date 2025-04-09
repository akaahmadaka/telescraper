"""
Handles searching using the duckduckgo-search library.
"""

from duckduckgo_search import DDGS
import config
from utils.logger import log

# Configuration for duckduckgo-search (if needed, most is handled by the library)
# We can estimate results per page if needed for max_results calculation
RESULTS_PER_PAGE_ESTIMATE = 25

def perform_duckduckgo_search(keyword, pages_to_request=1):
    """
    Performs a search using the duckduckgo-search library.

    Args:
        keyword (str): The search term.
        pages_to_request (int): The number of pages worth of results to request.

    Returns:
        list: A list of unique URLs found in the search results.
              Returns an empty list if errors occur or no results are found.
    """
    log.info(f"Starting DuckDuckGo search for keyword: '{keyword}' (requesting ~{pages_to_request} page(s))")
    found_urls = set()
    max_results_to_fetch = pages_to_request * RESULTS_PER_PAGE_ESTIMATE

    try:
        # Use the DDGS context manager for potential setup/teardown
        with DDGS() as ddgs:
            # ddgs.text returns a generator of result dictionaries
            results_generator = ddgs.text(keyword, max_results=max_results_to_fetch)

            for result in results_generator:
                if isinstance(result, dict) and 'href' in result:
                    url = result['href']
                    if url:
                        # Basic validation (library usually returns valid URLs)
                        if url.startswith('http://') or url.startswith('https://'):
                            log.debug(f"Extracted URL: {url}")
                            found_urls.add(url)
                        else:
                            log.debug(f"Skipping potentially invalid URL from library: {url}")
                else:
                    log.warning(f"Received unexpected result format from duckduckgo-search: {result}")

    except Exception as e:
        # Catch potential errors from the library or network issues
        log.error(f"Error during DuckDuckGo search for '{keyword}' using duckduckgo-search library: {e}", exc_info=True)

    if not found_urls:
        log.warning(f"No results found for '{keyword}' using duckduckgo-search library.")

    log.info(f"Finished DuckDuckGo search for '{keyword}'. Found {len(found_urls)} unique URLs.")
    return list(found_urls)

# Renamed function to perform_duckduckgo_search

if __name__ == '__main__':
    # Example usage if run directly
    test_keyword = "telegram public groups list" # Example from config
    print(f"Performing test DuckDuckGo search for: '{test_keyword}'")
    results = perform_duckduckgo_search(test_keyword, pages_to_request=1)

    if results:
        print("\nFound URLs:")
        for url in results:
            print(url)
    else:
        print("\nNo URLs found or an error occurred.")
        print("Check logs (if configured).")
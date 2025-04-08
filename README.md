# Telescraper

Telescraper is a Python application designed to continuously scrape Google Search results for specified keywords, extract Telegram group/channel links (`t.me/...`) from the resulting web pages, and store unique links in an SQLite database.

**Disclaimer:** Scraping Google Search results directly can be against their Terms of Service and may lead to temporary or permanent IP blocks. Use this tool responsibly and ethically. Consider adjusting delays in `config.py` to be respectful to Google and the target websites.

## Features

*   Searches Google for a list of keywords defined in `config.py`.
*   Scrapes resulting URLs for Telegram links.
*   Stores unique Telegram links, source URL, and the originating keyword in an SQLite database (`telescraper.db`).
*   Configurable delays between searches and page fetches.
*   Logs activity to console and optionally to `telescraper.log`.
*   Runs continuously until manually stopped (Ctrl+C).
*   Graceful shutdown handling.

## Project Structure

```
telescraper/
├── .gitignore
├── README.md
├── PLAN.md               # Project plan document
├── requirements.txt      # Python dependencies
├── config.py             # Configuration (keywords, DB path, delays)
├── main.py               # Main application entry point
│
├── scraper/
│   ├── __init__.py
│   ├── google_search.py  # Google searching logic
│   └── link_extractor.py # Telegram link extraction logic
│
├── database/
│   ├── __init__.py
│   └── db_manager.py     # SQLite database interaction
│
└── utils/
    ├── __init__.py
    ├── logger.py         # Logging setup
    └── helpers.py        # Utility functions (e.g., delays)
```

## Setup

1.  **Clone the repository (if applicable) or ensure you have all the files.**
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Keywords (Optional):**
    *   Edit the `KEYWORDS` list in `config.py` to specify the search terms you are interested in.
    *   Adjust `GOOGLE_SEARCH_PAGES`, delays (`SEARCH_DELAY_SECONDS`, `FETCH_DELAY_SECONDS`, `CYCLE_DELAY_SECONDS`), and logging settings in `config.py` as needed. Be mindful of Google's scraping policies.

## Usage

1.  **Run the scraper:**
    ```bash
    python main.py
    ```
2.  The application will start logging to the console (and `telescraper.log` if configured). It will begin searching for the first keyword, processing results, and then move to the next keyword after the configured delay.
3.  Found Telegram links will be stored in `telescraper.db`. You can use an SQLite browser tool to view the database contents.
4.  **Stop the scraper:** Press `Ctrl+C`. The application will attempt to finish its current task and shut down gracefully. Press `Ctrl+C` again to force exit if needed.

## Important Considerations

*   **Google Blocking:** Google actively tries to prevent automated scraping. Your IP might get temporarily blocked, requiring CAPTCHA solving if accessed via a browser. Increase delays in `config.py` significantly if you encounter issues. Using proxies or dedicated scraping services might be necessary for heavy usage.
*   **HTML Structure Changes:** Google frequently updates its search results page structure. The CSS selectors in `scraper/google_search.py` (`RESULT_LINK_SELECTOR`) might need updating if the script stops finding result URLs.
*   **Website Variations:** The `scraper/link_extractor.py` attempts to find `t.me` links in standard `<a>` tags. Websites use various methods to display links, so it might not find all links on all pages.
*   **Ethics:** Be respectful of the websites you are scraping. Do not overload them with requests (use appropriate `FETCH_DELAY_SECONDS`).
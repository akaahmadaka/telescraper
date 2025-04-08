"""
Configuration settings for the Telescraper project.
"""

import os

# --- Search Configuration ---

# Keywords to search for using the configured search engine (currently DuckDuckGo HTML)
# Example: ["telegram crypto groups", "telegram programming channels"]
KEYWORDS = [
    "telegram public groups list",
    "telegram channel directory",
    "telegram tech channels",
    "telegram news groups",
]

# Number of search result pages to *request* per keyword.
# NOTE: The current implementation using DuckDuckGo HTML (`search_engine.py`)
#       only processes the *first* page of results, regardless of this setting,
#       due to limitations/complexities in DDG HTML pagination.
#       This setting is kept for potential future search engine implementations.
SEARCH_PAGES_TO_REQUEST = 1 # Set to 1 to reflect current reality

# --- Scraping Configuration ---

# Base URL for Telegram links
TELEGRAM_BASE_URL = "https://t.me/"

# User-Agent string to use for requests. Helps mimic a real browser.
# Consider rotating user agents for more robust scraping (implement in helpers.py later).
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Maximum size (in bytes) for downloaded web pages to prevent memory issues
# Set to None or 0 to disable limit. 5MB = 5 * 1024 * 1024
MAX_DOWNLOAD_SIZE_BYTES = 5 * 1024 * 1024

# --- Database Configuration ---

# Path to the SQLite database file
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "telescraper.db")

# --- Timing Configuration ---

# Delay (in seconds) between consecutive searches for different keywords
# IMPORTANT: Keep this reasonably high to avoid potential rate limiting from the search engine.
SEARCH_DELAY_SECONDS = 1 * 5 # 5 minutes

# Delay (in seconds) between fetching individual website pages found in search results
# IMPORTANT: Avoid overwhelming target websites.
FETCH_DELAY_SECONDS = 10 # Increased slightly

# Delay (in seconds) after processing all keywords before starting the next cycle
CYCLE_DELAY_SECONDS = 1 * 10 # 30 minutes

# --- Logging Configuration ---
LOG_LEVEL = "DEBUG" # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(name)s - %(levelname)s - %(message)s"
LOG_FILE = None # Set to None to log only to console

# --- Telegram Bot Configuration ---

# Set to True to enable sending notifications via Telegram Bot
BOT_ENABLED = True # Default to False until configured

# Get your Bot Token from BotFather on Telegram
BOT_TOKEN = ""

# Get the Chat ID of the group/channel/user to send messages to
# For groups/channels, it usually starts with a '-'
CHAT_ID = ""

# Delay (in seconds) between sending consecutive messages to Telegram
# IMPORTANT: Keep this >= 1 to respect Telegram API limits and avoid spam flags.
BOT_SEND_DELAY_SECONDS = 2
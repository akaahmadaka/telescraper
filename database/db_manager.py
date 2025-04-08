"""
Manages interactions with the SQLite database for storing scraped Telegram links.
"""

import sqlite3
import config
from utils.logger import log # Use the logger setup in utils

DATABASE_PATH = config.DATABASE_PATH

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        log.debug(f"Database connection established to {DATABASE_PATH}")
        return conn
    except sqlite3.Error as e:
        log.error(f"Error connecting to database at {DATABASE_PATH}: {e}", exc_info=True)
        return None

def close_db_connection(conn):
    """Closes the database connection."""
    if conn:
        try:
            conn.close()
            log.debug("Database connection closed.")
        except sqlite3.Error as e:
            log.error(f"Error closing database connection: {e}", exc_info=True)

def setup_database():
    """
    Sets up the database: creates the 'links' table if it doesn't exist.
    """
    conn = get_db_connection()
    if not conn:
        log.error("Cannot set up database: No connection.")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_link TEXT NOT NULL UNIQUE,
                source_url TEXT NOT NULL,
                keyword TEXT NOT NULL,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create processed_urls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL UNIQUE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create url_queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        log.info("Database tables 'links', 'processed_urls', and 'url_queue' checked/created successfully.")
        return True
    except sqlite3.Error as e:
        log.error(f"Error setting up database table 'links': {e}", exc_info=True)
        return False
    finally:
        close_db_connection(conn)

def add_telegram_link(telegram_link, source_url, keyword):
    """
    Adds a new Telegram link to the database if it doesn't already exist.

    Args:
        telegram_link (str): The Telegram link (e.g., https://t.me/somegroup).
        source_url (str): The URL where the Telegram link was found.
        keyword (str): The keyword used in the search that led to this link.

    Returns:
        bool: True if the link was added successfully, False otherwise.
    """
    conn = get_db_connection()
    if not conn:
        log.error("Cannot add link: No database connection.")
        return False

    sql = """
        INSERT INTO links (telegram_link, source_url, keyword)
        VALUES (?, ?, ?)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (telegram_link, source_url, keyword))
        conn.commit()
        log.info(f"Added link: {telegram_link} (Source: {source_url}, Keyword: {keyword})")
        return True
    except sqlite3.IntegrityError:
        # This happens if the telegram_link is already in the database due to UNIQUE constraint
        log.debug(f"Link already exists, skipping: {telegram_link}")
        return False
    except sqlite3.Error as e:
        log.error(f"Error adding link {telegram_link} to database: {e}", exc_info=True)
        return False
    finally:
        close_db_connection(conn)

def add_processed_url(source_url):
    """Adds a source URL to the processed_urls table."""
    conn = get_db_connection()
    if not conn:
        log.error("Cannot add processed URL: No database connection.")
        return False

    sql = "INSERT OR IGNORE INTO processed_urls (source_url) VALUES (?)"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (source_url,))
        conn.commit()
        # Log only if a new row was actually inserted (changes > 0)
        if conn.total_changes > 0:
             log.debug(f"Marked URL as processed: {source_url}")
        return True
    except sqlite3.Error as e:
        log.error(f"Error adding processed URL {source_url} to database: {e}", exc_info=True)
        return False
    finally:
        close_db_connection(conn)

def is_url_processed(source_url):
    """Checks if a source URL has already been processed."""
    conn = get_db_connection()
    if not conn:
        log.error("Cannot check processed URL: No database connection.")
        # Default to False to allow processing attempt if DB check fails
        return False

    sql = "SELECT 1 FROM processed_urls WHERE source_url = ? LIMIT 1"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (source_url,))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        log.error(f"Error checking if URL is processed {source_url}: {e}", exc_info=True)
        # Default to False to allow processing attempt if DB check fails
        return False
    finally:
        close_db_connection(conn)

def add_to_url_queue(urls):
    """Adds a list of URLs to the processing queue, ignoring duplicates."""
    if not urls:
        return False

    conn = get_db_connection()
    if not conn:
        log.error("Cannot add to URL queue: No database connection.")
        return False

    sql = "INSERT OR IGNORE INTO url_queue (url) VALUES (?)"
    # Prepare data as a list of tuples for executemany
    data_to_insert = [(url,) for url in urls]

    try:
        cursor = conn.cursor()
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        inserted_count = conn.total_changes # Count how many were actually inserted
        if inserted_count > 0:
            log.info(f"Added {inserted_count} new URLs to the processing queue.")
        else:
            log.debug("No new URLs added to the queue (all duplicates).")
        return True
    except sqlite3.Error as e:
        log.error(f"Error adding URLs to queue: {e}", exc_info=True)
        return False
    finally:
        close_db_connection(conn)

def get_next_url_from_queue(batch_size=10):
    """Retrieves a batch of the oldest URLs from the queue."""
    conn = get_db_connection()
    if not conn:
        log.error("Cannot get URLs from queue: No database connection.")
        return []

    # Select oldest URLs based on added_at timestamp
    sql = "SELECT url FROM url_queue ORDER BY added_at ASC LIMIT ?"
    urls_to_process = []
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (batch_size,))
        results = cursor.fetchall()
        urls_to_process = [row['url'] for row in results]

        # Remove fetched URLs from the queue
        if urls_to_process:
            delete_sql = "DELETE FROM url_queue WHERE url IN ({})".format(','.join('?'*len(urls_to_process)))
            cursor.execute(delete_sql, urls_to_process)
            conn.commit()
            log.debug(f"Retrieved and removed {len(urls_to_process)} URLs from the queue.")

    except sqlite3.Error as e:
        log.error(f"Error retrieving URLs from queue: {e}", exc_info=True)
    finally:
        close_db_connection(conn)

    return urls_to_process

# Note: The link_exists function is kept for now, although it's not used by main.py
def link_exists(telegram_link):
    """
    Checks if a specific Telegram link already exists in the database.

    Args:
        telegram_link (str): The Telegram link to check.

    Returns:
        bool: True if the link exists, False otherwise.
    """
    conn = get_db_connection()
    if not conn:
        log.error("Cannot check link existence: No database connection.")
        # Default to True to avoid trying to re-add if DB connection fails
        return True

    sql = "SELECT 1 FROM links WHERE telegram_link = ? LIMIT 1"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (telegram_link,))
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        log.error(f"Error checking if link exists {telegram_link}: {e}", exc_info=True)
        # Default to True to avoid trying to re-add if DB check fails
        return True
    finally:
        close_db_connection(conn)

if __name__ == '__main__':
    # Example usage if run directly
    print("Setting up database...")
    if setup_database():
        print("Database setup complete.")
        print("\nAttempting to add links:")
        add_telegram_link("https://t.me/testgroup1", "http://example.com/page1", "test keyword 1")
        add_telegram_link("https://t.me/testgroup2", "http://example.com/page2", "test keyword 2")
        # Try adding the same link again
        add_telegram_link("https://t.me/testgroup1", "http://anothersite.com", "test keyword 3")

        print("\nChecking link existence:")
        print(f"Link 'https://t.me/testgroup1' exists? {link_exists('https://t.me/testgroup1')}")
        print(f"Link 'https://t.me/nonexistent' exists? {link_exists('https://t.me/nonexistent')}")
    else:
        print("Database setup failed.")
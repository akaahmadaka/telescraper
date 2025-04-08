"""
Logging configuration for the Telescraper project.
"""

import logging
import sys
import config # Import config to access settings

def setup_logger(name="telescraper"):
    """
    Sets up and returns a logger instance.

    Configures logging based on settings in config.py (LOG_LEVEL, LOG_FORMAT, LOG_FILE).
    Logs to console and optionally to a file.

    Args:
        name (str): The name for the logger instance.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if called again
    if logger.hasHandlers():
        return logger

    try:
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    except AttributeError:
        log_level = logging.INFO
        print(f"Warning: Invalid LOG_LEVEL '{config.LOG_LEVEL}' in config.py. Defaulting to INFO.")

    logger.setLevel(log_level)
    formatter = logging.Formatter(config.LOG_FORMAT)

    # Console Handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # File Handler (Optional)
    if config.LOG_FILE:
        try:
            file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to set up log file handler at {config.LOG_FILE}: {e}", exc_info=False) # Avoid traceback spam if logger is called repeatedly before fix

    return logger

# Initialize a default logger instance for easy import
log = setup_logger()

if __name__ == '__main__':
    # Example usage if run directly
    log.debug("This is a debug message.")
    log.info("This is an info message.")
    log.warning("This is a warning message.")
    log.error("This is an error message.")
    log.critical("This is a critical message.")
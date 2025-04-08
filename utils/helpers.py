"""
Utility functions for the Telescraper project.
"""

import time
import random
from utils.logger import log

def polite_delay(base_delay_seconds, jitter_seconds=2):
    """
    Introduces a delay with a small random jitter to make scraping less predictable.

    Args:
        base_delay_seconds (float): The base number of seconds to wait.
        jitter_seconds (float): The maximum number of additional random seconds to add.
    """
    delay = base_delay_seconds + random.uniform(0, jitter_seconds)
    log.debug(f"Waiting for {delay:.2f} seconds...")
    time.sleep(delay)

# Potential future additions:
# - Function to rotate User-Agent strings from a list
# - Functions for cleaning or validating URLs/data
# - etc.

if __name__ == '__main__':
    print("Testing polite_delay:")
    base = 5
    print(f"Base delay: {base} seconds")
    polite_delay(base)
    print("Delay finished.")
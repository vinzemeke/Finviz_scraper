"""
Configuration settings for the Finviz Stock Scraper.
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
URLS_FILE = DATA_DIR / "saved_urls.json"
RESULTS_DIR = DATA_DIR / "results"

# Ensure data directories exist
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Scraping settings
REQUEST_DELAY = 1.0  # Delay between requests in seconds
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 30  # Request timeout in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests

# Finviz specific settings
FINVIZ_BASE_URL = "https://finviz.com"
FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx"

# CSV output settings
CSV_ENCODING = "utf-8"
CSV_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

# Pagination settings
PAGINATION_DELAY = 0.5  # Delay between pagination requests
MAX_PAGES = 100  # Maximum number of pages to scrape (safety limit)

# Deduplication settings
DEDUP_TIME_WINDOW_HOURS = int(os.getenv('DEDUP_TIME_WINDOW_HOURS', '24'))  # Hours after which to re-scrape
DEDUP_ENABLE_CONTENT_HASH = os.getenv('DEDUP_ENABLE_CONTENT_HASH', 'true').lower() == 'true'  # Enable content hash checking
DEDUP_USE_TIME_WINDOW = os.getenv('DEDUP_USE_TIME_WINDOW', 'true').lower() == 'true'  # Use time window as fallback when hash checking is disabled
DEDUP_LOG_SKIPS = os.getenv('DEDUP_LOG_SKIPS', 'true').lower() == 'true'  # Log skipped scrapes

# Error messages
ERROR_MESSAGES = {
    "invalid_url": "Invalid Finviz URL provided",
    "network_error": "Network error occurred while scraping",
    "no_results": "No stock results found on the page",
    "pagination_error": "Error occurred while handling pagination",
    "file_error": "Error occurred while saving/loading data"
} 
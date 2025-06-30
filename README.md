# Finviz Stock Scraper

A Python web application for scraping stock ticker symbols from Finviz filtered pages. Save Finviz URLs with custom names and extract all ticker symbols, including handling pagination automatically.

## Features

- **URL Management**: Save, edit, and delete Finviz URLs with custom names (e.g., "trending stocks", "tech stocks")
- **Automatic Pagination**: Handle multi-page results to capture all stocks
- **Web Interface**: User-friendly web interface for managing URLs and scraping
- **CSV Output**: Save results in structured format for further analysis
- **Error Handling**: Robust error handling for network issues and invalid URLs
- **Respectful Scraping**: Built-in delays and proper user agents
- **Smart Deduplication**: Avoid redundant scraping with configurable time windows and content hash checking
- **Force Scrape**: Bypass deduplication rules when needed
- **SQLite Database**: Persistent storage with comprehensive scraping history

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Finviz_scraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application

Run the Flask web server:
```bash
PYTHONPATH=./src FLASK_APP=src.main FLASK_ENV=development flask run
```

The application will be available at `http://127.0.0.1:5000`

### Web Interface Features

**Adding URLs:**
- Enter a custom name (e.g., "TPS SCANNER")
- Paste a Finviz screener URL
- Click "Add URL"

**Editing URLs:**
- Click the "Edit" button (✏️) next to any saved URL
- Modify the name and/or URL
- Click "Save Changes" or "Cancel"

**Deleting URLs:**
- Click the "Delete" button (🗑️) next to any saved URL
- Confirm the deletion in the popup dialog
- The URL will be removed from your saved list

**Scraping Ticker Symbols:**
- Click the "Scrape" button next to any saved URL
- The app will extract all ticker symbols from the Finviz page (including pagination)
- Results will be displayed on the page and saved to CSV files

### Example Workflow

1. **Add your first URL:**
   - Name: "TPS SCANNER"
   - URL: `https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4`

2. **Edit the URL if needed:**
   - Click the "Edit" button
   - Change the name to "UPDATED SCANNER" or modify the URL
   - Save changes

3. **Scrape the ticker symbols:**
   - Click the "Scrape" button
   - View the extracted ticker symbols on the page

4. **Delete when no longer needed:**
   - Click the "Delete" button
   - Confirm deletion

## Output

The scraper generates CSV files in the `data/results/` directory with the following format:

```csv
url_name,ticker_symbol,timestamp
TPS SCANNER,AAPL,2024-01-15_14-30-25
TPS SCANNER,GOOGL,2024-01-15_14-30-25
TPS SCANNER,MSFT,2024-01-15_14-30-25
```

## Configuration

Edit `config/settings.py` to customize:
- Request delays
- User agent strings
- Timeout settings
- File paths
- Error messages

### Deduplication Configuration

The scraper includes intelligent hash-based deduplication to avoid redundant scraping:

**Environment Variables:**
```bash
# Time window for re-scraping (fallback only, default: 24 hours)
export DEDUP_TIME_WINDOW_HOURS=12

# Enable/disable content hash checking (default: true)
export DEDUP_ENABLE_CONTENT_HASH=true

# Use time window as fallback when hash checking is disabled (default: false)
export DEDUP_USE_TIME_WINDOW=false

# Enable/disable logging of skipped scrapes (default: true)
export DEDUP_LOG_SKIPS=true
```

**Configuration Options:**
- `DEDUP_TIME_WINDOW_HOURS`: Hours after which a URL should be re-scraped (fallback only, default: 24)
- `DEDUP_ENABLE_CONTENT_HASH`: Enable content hash checking to skip unchanged pages (default: true)
- `DEDUP_USE_TIME_WINDOW`: Use time window as fallback when hash checking is disabled (default: false)
- `DEDUP_LOG_SKIPS`: Log skipped scrapes to database for tracking (default: true)

**Force Scrape:**
- Use the "Force scrape" checkbox in the web interface to bypass deduplication rules
- Useful when you need fresh data regardless of previous scraping history

**Deduplication Logic:**
1. **Primary: Content-based**: Skip if page content hasn't changed (SHA256 hash comparison)
2. **Secondary: Time-based**: Skip if last scrape was within the configured time window (only when hash checking is disabled)
3. **Force override**: Use force-scrape to bypass all deduplication rules

**Hash-Based Deduplication Benefits:**
- More efficient: Only skips when content actually hasn't changed
- More accurate: Detects real changes regardless of time intervals
- Reduces unnecessary processing: Avoids re-parsing identical content
- Better resource utilization: Saves bandwidth and processing time

## Requirements

- Python 3.8+
- requests
- beautifulsoup4
- pandas
- click
- lxml
- flask

## Notes

- The scraper respects Finviz's robots.txt and implements reasonable delays
- Results are saved with timestamps for tracking
- Handles pagination automatically (up to 100 pages by default)
- Includes comprehensive error handling for network issues
- CSV files are preserved when URLs are edited or deleted

## License

This project is for educational purposes. Please respect Finviz's terms of service and robots.txt when using this scraper. 
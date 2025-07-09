#!/usr/bin/env python3
"""
Test script to verify ticker saving functionality.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database.database_manager import DatabaseManager
from src.storage.url_manager import URLManager
from src.scraper.scraper_engine import ScraperEngine

def test_ticker_saving():
    """Test that tickers are being saved to the database."""
    print("=== Testing Ticker Saving Functionality ===\n")
    
    # Initialize components
    db_manager = DatabaseManager()
    url_manager = URLManager(db_manager)
    
    # Check current ticker count
    initial_count = db_manager.execute_query("SELECT COUNT(*) FROM ticker_results")[0][0]
    print(f"Initial ticker count in database: {initial_count}")
    
    # Get URLs from database
    urls = db_manager.execute_query("SELECT * FROM urls LIMIT 1")
    if not urls:
        print("No URLs found in database. Please add a URL first.")
        return
    
    url_row = urls[0]
    url_id, url_name, url = url_row[0], url_row[1], url_row[2]
    print(f"Testing with URL: {url_name} (ID: {url_id})")
    print(f"URL: {url}\n")
    
    # Perform a test scrape
    try:
        scraper_engine = ScraperEngine(db_manager, url_manager)
        result = scraper_engine.scrape_url(url_name, force_scrape=True)
        
        print(f"Scrape result status: {result['status']}")
        print(f"Tickers found: {len(result.get('tickers', []))}")
        
        if result['status'] == 'completed':
            print(f"Sample tickers: {result['tickers'][:5] if result['tickers'] else 'None'}")
            
            # Check if tickers were saved
            final_count = db_manager.execute_query("SELECT COUNT(*) FROM ticker_results")[0][0]
            print(f"Final ticker count in database: {final_count}")
            print(f"Tickers added: {final_count - initial_count}")
            
            # Check recent tickers for this URL
            recent_tickers = db_manager.execute_query(
                "SELECT ticker_symbol, timestamp FROM ticker_results WHERE url_id = ? ORDER BY timestamp DESC LIMIT 5",
                (url_id,)
            )
            print(f"Recent tickers for URL {url_id}:")
            for ticker, timestamp in recent_tickers:
                print(f"  {ticker} - {timestamp}")
                
        elif result['status'] == 'skipped':
            print(f"Scrape was skipped: {result.get('reason', 'Unknown reason')}")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ticker_saving() 
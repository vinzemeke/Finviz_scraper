import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.database.database_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CacheManagerService:
    def __init__(self, db_manager: DatabaseManager, ttl_hours: int = 24):
        self.db_manager = db_manager
        self.ttl_hours = ttl_hours

    def get_cached_ticker_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        cached_data = self.db_manager.get_ticker_properties(ticker)
        if cached_data:
            last_updated_str = cached_data.get('last_updated')
            if last_updated_str:
                # SQLite stores DATETIME as TEXT, convert back to datetime object
                last_updated = datetime.fromisoformat(last_updated_str)
                if datetime.now() - last_updated < timedelta(hours=self.ttl_hours):
                    logging.info(f"Cache hit for {ticker}. Data is fresh.")
                    return cached_data
                else:
                    logging.info(f"Cache for {ticker} is stale. Last updated: {last_updated_str}")
            else:
                logging.warning(f"Cached data for {ticker} has no last_updated timestamp.")
        logging.info(f"Cache miss for {ticker}.")
        return None

    def set_cached_ticker_data(self, ticker: str, data: Dict[str, Any], chart_path: str):
        try:
            self.db_manager.save_ticker_properties(
                ticker=ticker,
                current_price=data.get('current_price'),
                market_cap=data.get('market_cap'),
                pe_ratio=data.get('pe_ratio'),
                volume=data.get('volume'),
                fifty_two_week_high=data.get('fifty_two_week_high'),
                fifty_two_week_low=data.get('fifty_two_week_low'),
                fifty_two_week_range=data.get('fifty_two_week_range'),
                ema_8=data.get('ema_8'),
                ema_21=data.get('ema_21'),
                ema_200=data.get('ema_200'),
                chart_path=chart_path
            )
            logging.info(f"Cached data for {ticker} successfully.")
        except Exception as e:
            logging.error(f"Error setting cache for {ticker}: {e}")

    def invalidate_cache(self, ticker: str):
        if self.db_manager.delete_ticker_properties(ticker):
            logging.info(f"Cache invalidated for {ticker}.")
        else:
            logging.warning(f"Could not invalidate cache for {ticker}. Maybe not found.")

    def cleanup_stale_cache(self):
        """Removes stale cache entries from the database."""
        # This would require a method in DatabaseManager to query for old entries
        # For now, we rely on get_cached_ticker_data to identify stale entries
        # and overwrite them when new data is fetched.
        logging.info("Stale cache cleanup not fully implemented at the database level yet.")

    def clear_all_cache(self):
        """Clears all cached ticker properties from the database."""
        self.db_manager.clear_all_ticker_properties()
        logging.info("All ticker properties cache cleared.")

if __name__ == '__main__':
    # Example Usage:
    # This requires a running DatabaseManager instance and a database file.
    # For a real test, you'd set up a temporary database.
    from src.database.database_manager import DatabaseManager
    from src.database.migration import MigrationManager
    import os

    # Setup a temporary database for testing
    test_db_path = 'data/test_cache.db'
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db_manager = DatabaseManager(db_path=test_db_path)
    migration_manager = MigrationManager(db_path=test_db_path)
    migration_manager.run_migrations()

    cache_manager = CacheManagerService(db_manager, ttl_hours=0.01) # Very short TTL for testing

    test_ticker = "TEST"
    test_data = {
        "current_price": 100.0,
        "market_cap": 1000000000,
        "pe_ratio": 20.5,
        "ema_8": 99.5,
        "ema_21": 98.0,
        "ema_200": 90.0
    }
    test_chart_path = "/path/to/test_chart.png"

    print(f"\n--- Testing {test_ticker} ---")

    # Test 1: Cache miss (no data yet)
    print("Test 1: Initial cache check (should be miss)")
    data = cache_manager.get_cached_ticker_data(test_ticker)
    assert data is None

    # Test 2: Set cache
    print("Test 2: Setting cache data")
    cache_manager.set_cached_ticker_data(test_ticker, test_data, test_chart_path)

    # Test 3: Cache hit (fresh data)
    print("Test 3: Checking cache immediately (should be hit)")
    data = cache_manager.get_cached_ticker_data(test_ticker)
    assert data is not None
    print(f"Cached data: {data}")

    # Test 4: Cache stale (wait for TTL to expire)
    print(f"Test 4: Waiting for cache to become stale ({cache_manager.ttl_hours * 3600} seconds)...")
    time.sleep(cache_manager.ttl_hours * 3600 * 1.1) # Wait a bit more than TTL
    data = cache_manager.get_cached_ticker_data(test_ticker)
    assert data is None
    print("Cache is now stale (as expected).")

    # Test 5: Invalidate cache
    print("Test 5: Setting cache again and then invalidating it")
    cache_manager.set_cached_ticker_data(test_ticker, test_data, test_chart_path)
    data = cache_manager.get_cached_ticker_data(test_ticker)
    assert data is not None
    cache_manager.invalidate_cache(test_ticker)
    data = cache_manager.get_cached_ticker_data(test_ticker)
    assert data is None
    print("Cache invalidated (as expected).")

    # Clean up test database
    db_manager.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"Cleaned up test database: {test_db_path}")

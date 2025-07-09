import logging
from typing import List, Dict, Any, Optional
from src.database.database_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WatchlistService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_watchlist(self, name: str, user_id: Optional[int] = None) -> Optional[int]:
        """
        Creates a new watchlist.
        """
        if not name:
            logging.error("Watchlist name cannot be empty.")
            return None
        return self.db_manager.create_watchlist(name, user_id)

    def get_watchlist(self, watchlist_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a watchlist by its ID.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return None
        return self.db_manager.get_watchlist(watchlist_id)

    def list_watchlists(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lists all watchlists, optionally filtered by user ID.
        """
        return self.db_manager.list_watchlists(user_id)

    def update_watchlist(self, watchlist_id: int, new_name: str) -> bool:
        """
        Updates the name of an existing watchlist.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return False
        if not new_name:
            logging.error("New watchlist name cannot be empty.")
            return False
        return self.db_manager.update_watchlist(watchlist_id, new_name)

    def delete_watchlist(self, watchlist_id: int) -> bool:
        """
        Deletes a watchlist by its ID.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return False
        return self.db_manager.delete_watchlist(watchlist_id)

    def add_ticker_to_watchlist(self, watchlist_id: int, ticker_symbol: str) -> bool:
        """
        Adds a ticker symbol to a watchlist.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return False
        if not ticker_symbol:
            logging.error("Ticker symbol cannot be empty.")
            return False
        return self.db_manager.add_ticker_to_watchlist(watchlist_id, ticker_symbol)

    def remove_ticker_from_watchlist(self, watchlist_id: int, ticker_symbol: str) -> bool:
        """
        Removes a ticker symbol from a watchlist.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return False
        if not ticker_symbol:
            logging.error("Ticker symbol cannot be empty.")
            return False
        return self.db_manager.remove_ticker_from_watchlist(watchlist_id, ticker_symbol)

    def get_tickers_in_watchlist(self, watchlist_id: int) -> List[str]:
        """
        Retrieves all ticker symbols in a given watchlist.
        """
        if not isinstance(watchlist_id, int) or watchlist_id <= 0:
            logging.error("Watchlist ID must be a positive integer.")
            return []
        return self.db_manager.get_tickers_in_watchlist(watchlist_id)

if __name__ == '__main__':
    # Example Usage (requires a DatabaseManager instance)
    # This part is for demonstration and would typically be run in a test or main application file
    from src.database.database_manager import DatabaseManager
    from src.database.migration import MigrationManager
    import os

    db_path = 'data/test_watchlist_service.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    migration_manager = MigrationManager(db_path)
    migration_manager.run_migrations()
    db_manager = DatabaseManager(db_path)
    watchlist_service = WatchlistService(db_manager)

    print("\n--- Testing Watchlist Service ---")

    # Create watchlist
    watchlist_id = watchlist_service.create_watchlist("My Stocks")
    if watchlist_id:
        print(f"Created watchlist with ID: {watchlist_id}")
    else:
        print("Failed to create watchlist.")

    # List watchlists
    watchlists = watchlist_service.list_watchlists()
    print(f"Current watchlists: {watchlists}")

    # Add tickers
    watchlist_service.add_ticker_to_watchlist(watchlist_id, "AAPL")
    watchlist_service.add_ticker_to_watchlist(watchlist_id, "GOOG")
    print(f"Tickers in watchlist {watchlist_id}: {watchlist_service.get_tickers_in_watchlist(watchlist_id)}")

    # Remove ticker
    watchlist_service.remove_ticker_from_watchlist(watchlist_id, "AAPL")
    print(f"Tickers in watchlist {watchlist_id} after removing AAPL: {watchlist_service.get_tickers_in_watchlist(watchlist_id)}")

    # Update watchlist
    watchlist_service.update_watchlist(watchlist_id, "My Favorite Stocks")
    updated_watchlist = watchlist_service.get_watchlist(watchlist_id)
    print(f"Updated watchlist: {updated_watchlist}")

    # Delete watchlist
    watchlist_service.delete_watchlist(watchlist_id)
    print(f"Watchlists after deletion: {watchlist_service.list_watchlists()}")

    # Test validation
    print("\n--- Testing Validation ---")
    watchlist_service.create_watchlist("") # Empty name
    watchlist_service.add_ticker_to_watchlist(watchlist_id, "") # Empty ticker
    watchlist_service.get_watchlist(0) # Invalid ID

    if os.path.exists(db_path):
        os.remove(db_path)

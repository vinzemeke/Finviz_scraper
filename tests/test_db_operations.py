import unittest
import os
from src.database.database_manager import DatabaseManager
from src.database.migration import MigrationManager

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        self.db_path = 'data/test_finviz_scraper.db'
        self.migration_manager = MigrationManager(self.db_path)
        self.db_manager = DatabaseManager(self.db_path)
        # Ensure a clean slate for each test
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Ensure base tables are created by DatabaseManager before running migrations
        self.db_manager._create_tables()
        self.migration_manager.run_migrations()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_and_get_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("My Test Watchlist")
        self.assertIsNotNone(watchlist_id)
        watchlist = self.db_manager.get_watchlist(watchlist_id)
        self.assertIsNotNone(watchlist)
        self.assertEqual(watchlist['name'], "My Test Watchlist")

    def test_list_watchlists(self):
        self.db_manager.create_watchlist("Watchlist A")
        self.db_manager.create_watchlist("Watchlist B")
        watchlists = self.db_manager.list_watchlists()
        self.assertEqual(len(watchlists), 2)
        self.assertEqual(watchlists[0]['name'], "Watchlist A")
        self.assertEqual(watchlists[1]['name'], "Watchlist B")

    def test_update_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("Old Name")
        self.assertTrue(self.db_manager.update_watchlist(watchlist_id, "New Name"))
        watchlist = self.db_manager.get_watchlist(watchlist_id)
        self.assertEqual(watchlist['name'], "New Name")

    def test_delete_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("To Be Deleted")
        self.assertTrue(self.db_manager.delete_watchlist(watchlist_id))
        watchlist = self.db_manager.get_watchlist(watchlist_id)
        self.assertIsNone(watchlist)

    def test_add_and_remove_ticker_from_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("Ticker Watchlist")
        self.assertTrue(self.db_manager.add_ticker_to_watchlist(watchlist_id, "AAPL"))
        self.assertTrue(self.db_manager.add_ticker_to_watchlist(watchlist_id, "GOOG"))
        tickers = self.db_manager.get_tickers_in_watchlist(watchlist_id)
        self.assertEqual(len(tickers), 2)
        self.assertIn("AAPL", tickers)
        self.assertIn("GOOG", tickers)

        self.assertTrue(self.db_manager.remove_ticker_from_watchlist(watchlist_id, "AAPL"))
        tickers = self.db_manager.get_tickers_in_watchlist(watchlist_id)
        self.assertEqual(len(tickers), 1)
        self.assertNotIn("AAPL", tickers)
        self.assertIn("GOOG", tickers)

    def test_save_and_get_simulation_result(self):
        sim_id = self.db_manager.save_simulation_result("AAPL", "AAPL240719C00150000", "{\"data\": \"some_json\"}")
        self.assertIsNotNone(sim_id)
        result = self.db_manager.get_simulation_result(sim_id)
        self.assertIsNotNone(result)
        self.assertEqual(result['ticker'], "AAPL")
        self.assertEqual(result['option_symbol'], "AAPL240719C00150000")

    def test_list_simulation_results(self):
        self.db_manager.save_simulation_result("GOOG", "GOOG240719C00100000", "{}")
        self.db_manager.save_simulation_result("GOOG", "GOOG240719P00100000", "{}")
        results = self.db_manager.list_simulation_results(ticker="GOOG")
        self.assertEqual(len(results), 2)

    def test_delete_simulation_result(self):
        sim_id = self.db_manager.save_simulation_result("MSFT", "MSFT240719C00200000", "{}")
        self.assertTrue(self.db_manager.delete_simulation_result(sim_id))
        result = self.db_manager.get_simulation_result(sim_id)
        self.assertIsNone(result)

    def test_save_and_get_user_preferences(self):
        self.assertTrue(self.db_manager.save_user_preferences(1, 0.03, 0.15, "{\"theme\": \"dark\"}"))
        prefs = self.db_manager.get_user_preferences(1)
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs['underpricing_threshold'], 0.03)
        self.assertEqual(prefs['strike_range'], 0.15)

    def test_update_user_preferences(self):
        self.db_manager.save_user_preferences(1, 0.05, 0.10, "{}")
        self.assertTrue(self.db_manager.update_user_preferences(1, underpricing_threshold=0.02))
        prefs = self.db_manager.get_user_preferences(1)
        self.assertEqual(prefs['underpricing_threshold'], 0.02)
        self.assertEqual(prefs['strike_range'], 0.10)

    def test_validation_create_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("")
        self.assertIsNone(watchlist_id)

    def test_validation_update_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("Valid Name")
        self.assertFalse(self.db_manager.update_watchlist(watchlist_id, ""))

    def test_validation_add_ticker_to_watchlist(self):
        watchlist_id = self.db_manager.create_watchlist("Valid Watchlist")
        self.assertFalse(self.db_manager.add_ticker_to_watchlist(watchlist_id, ""))

    def test_validation_save_simulation_result(self):
        sim_id = self.db_manager.save_simulation_result("", "", "")
        self.assertIsNone(sim_id)

    def test_validation_save_user_preferences(self):
        self.assertFalse(self.db_manager.save_user_preferences(1, 1.1, 0.1))
        self.assertFalse(self.db_manager.save_user_preferences(1, 0.1, 1.1))
        self.assertFalse(self.db_manager.save_user_preferences(-1, 0.1, 0.1))

if __name__ == '__main__':
    unittest.main()
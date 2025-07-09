import unittest
import json
import os
from datetime import datetime
import time
from unittest.mock import patch
import pandas as pd
from src.main import app, init_app_components
from src.database.database_manager import DatabaseManager
from src.database.migration import MigrationManager

class TestIntegration(unittest.TestCase):
    db_path = 'data/test_integration.db'

    @classmethod
    def setUpClass(cls):
        # Ensure the test database directory exists
        os.makedirs(os.path.dirname(cls.db_path), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Clean up the test database file after all tests
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        # Create a test client
        self.client = app.test_client()
        self.client.testing = True

        # Ensure a clean database for each test by re-initializing and migrating
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Initialize app components with the test database path
        with app.app_context():
            init_app_components(app, db_path=self.db_path)
            migration_manager = MigrationManager(db_path=self.db_path)
            app.db_manager._create_tables() # Create base tables
            migration_manager.run_migrations() # Run migrations for new tables

    def tearDown(self):
        # Clean up the test database file after each test
        if os.path.exists(self.db_path):
            os.remove(self.db_path)


    def test_01_create_watchlist_and_add_ticker(self):
        # Test 3.2.1: POST /api/watchlists
        watchlist_name = "IntegrationTestWatchlist"
        response = self.client.post("/api/watchlists", data=json.dumps({"name": watchlist_name}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn("id", data)
        self.watchlist_id = data["id"]
        print(f"Created watchlist ID: {self.watchlist_id}")

        # Verify watchlist exists
        response = self.client.get("/api/watchlists")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        print(f"Verified watchlist exists: {data}")

        # Test 3.2.5: POST /api/watchlists/<id>/tickers
        ticker_symbol = "MSFT"
        response = self.client.post(f"/api/watchlists/{self.watchlist_id}/tickers", data=json.dumps({"ticker_symbol": ticker_symbol}), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        print(f"Added ticker {ticker_symbol} to watchlist {self.watchlist_id}")

    def test_02_list_watchlists(self):
        # This test is now redundant as watchlist creation and listing is covered in test_01
        pass

    @patch('src.services.yahoo_finance_service.yf.Ticker')
    def test_03_simulate_option_end_to_end(self, mock_ticker):
        # Configure the mock yfinance.Ticker
        mock_ticker_instance = mock_ticker.return_value
        mock_ticker_instance.info = {
            'regularMarketPrice': 150.0,
            'marketCap': 1000000000000,
            'trailingPE': 25.0,
            'volume': 1000000,
            'fiftyTwoWeekHigh': 160.0,
            'fiftyTwoWeekLow': 100.0
        }
        mock_ticker_instance.history.return_value = pd.DataFrame({
            'Close': [140, 142, 145, 148, 150, 152, 155, 153, 150, 148] # Sample data for EMAs
        })

        # This requires a valid ticker and its current price
        ticker = "AAPL"
        # First, get current price (simulated or actual)
        ticker_info_response = self.client.get(f"/api/ticker_details/{ticker}")
        self.assertEqual(ticker_info_response.status_code, 200)
        ticker_info = json.loads(ticker_info_response.data)
        self.assertIsNotNone(ticker_info)
        S0 = ticker_info.get('current_price')
        self.assertIsNotNone(S0)

        simulation_params = {
            "ticker": ticker,
            "strike_price": S0 * 1.05, # Example strike slightly OTM
            "option_type": "call",
            "time_to_expiration": 0.5, # 6 months
            "risk_free_rate": 0.01,
            "volatility": 0.3,
            "num_simulations": 10000,
            "num_steps": 252
        }
        response = self.client.post("/api/simulate", data=json.dumps(simulation_params), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("simulation_data", data)
        self.assertIn("simulation_id", data)
        self.simulation_id = data["simulation_id"]
        estimated_price = data['simulation_data']['estimated_option_price']
        print(f"Simulation completed. Estimated price: {estimated_price:.2f}")

        # Test 3.3.2: GET /api/simulation/<id>
        response = self.client.get(f"/api/simulation/{self.simulation_id}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], self.simulation_id)
        self.assertIn('simulation_data', data)
        print(f"Retrieved simulation result for ID {self.simulation_id}")

        # Test 3.3.3: GET /api/simulation/<id>/export
        response = self.client.get(f"/api/simulation/{self.simulation_id}/export")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('estimated_price', data)
        print(f"Exported simulation result for ID {self.simulation_id}")

    def test_04_options_data_caching_and_refresh(self):
        ticker = "GOOG"
        # Test 3.5.1: GET /api/options/<ticker> (initial fetch)
        response = self.client.get(f"/api/options/{ticker}")
        self.assertEqual(response.status_code, 200)
        initial_data = json.loads(response.data)
        self.assertIn('calls', initial_data[list(initial_data.keys())[0]])
        print(f"Fetched options data for {ticker}")

        # Test 3.5.3: GET /api/options/<ticker>/last-updated
        response = self.client.get(f"/api/options/{ticker}/last-updated")
        self.assertEqual(response.status_code, 200)
        last_updated_data = json.loads(response.data)
        self.assertIsNotNone(last_updated_data['last_updated'])
        initial_timestamp = datetime.fromisoformat(last_updated_data['last_updated'])
        print(f"Initial timestamp for {ticker}: {initial_timestamp}")

        # Wait a bit (less than cache duration)
        time.sleep(2) 

        # Fetch again, should be from cache
        response = self.client.get(f"/api/options/{ticker}")
        self.assertEqual(response.status_code, 200)
        cached_data = json.loads(response.data)
        self.assertEqual(initial_data, cached_data) # Should be the same data
        print(f"Fetched options data for {ticker} (from cache)")

        # Test 3.5.2: POST /api/options/<ticker>/refresh
        response = self.client.post(f"/api/options/{ticker}/refresh")
        self.assertEqual(response.status_code, 200)
        print(f"Refreshed options data for {ticker}")

        # Check last-updated again, should be newer
        response = self.client.get(f"/api/options/{ticker}/last-updated")
        self.assertEqual(response.status_code, 200)
        new_last_updated_data = json.loads(response.data)
        new_timestamp = datetime.fromisoformat(new_last_updated_data['last_updated'])
        self.assertGreater(new_timestamp, initial_timestamp)
        print(f"New timestamp for {ticker}: {new_timestamp}")

    def test_05_user_preferences(self):
        user_id = 1
        # Test 3.4.1: GET /api/preferences
        response = self.client.get("/api/preferences")
        self.assertEqual(response.status_code, 200)
        initial_prefs = json.loads(response.data)
        self.assertIn('underpricing_threshold', initial_prefs)
        print(f"Initial preferences: {initial_prefs}")

        # Test 3.4.2: PUT /api/preferences
        new_threshold = 0.03
        new_strike_range = 0.12
        response = self.client.put("/api/preferences", data=json.dumps({
            "underpricing_threshold": new_threshold,
            "strike_range": new_strike_range
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(f"Updated preferences to threshold={new_threshold}, strike_range={new_strike_range}")

        response = self.client.get("/api/preferences")
        updated_prefs = json.loads(response.data)
        self.assertEqual(updated_prefs['underpricing_threshold'], new_threshold)
        self.assertEqual(updated_prefs['strike_range'], new_strike_range)

        # Test 3.4.3: POST /api/preferences/reset
        response = self.client.post("/api/preferences/reset")
        self.assertEqual(response.status_code, 200)
        print("Reset preferences to defaults")

        response = self.client.get("/api/preferences")
        reset_prefs = json.loads(response.data)
        self.assertEqual(reset_prefs['underpricing_threshold'], 0.05) # Default value
        self.assertEqual(reset_prefs['strike_range'], 0.10) # Default value

    def test_06_error_handling(self):
        # Test invalid watchlist creation
        response = self.client.post("/api/watchlists", data=json.dumps({"name": ""}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", json.loads(response.data))
        print("Tested invalid watchlist creation (empty name)")

        # Test non-existent watchlist operations
        response = self.client.delete("/api/watchlists/99999")
        self.assertEqual(response.status_code, 404)
        print("Tested deleting non-existent watchlist")

        # Test simulation with missing parameters
        response = self.client.post("/api/simulate", data=json.dumps({
            "ticker": "AAPL",
            "strike_price": 150,
            "option_type": "call",
            # Missing time_to_expiration, risk_free_rate, volatility
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", json.loads(response.data))
        print("Tested simulation with missing parameters")

if __name__ == '__main__':
    unittest.main()
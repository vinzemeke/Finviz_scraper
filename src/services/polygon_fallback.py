import os
import sys
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Ensure config is on sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from config.secrets import POLYGON_API_KEY
except ImportError:
    POLYGON_API_KEY = None
    logging.warning("Polygon.io API key not found in config/secrets.py")

class PolygonFallback:
    BASE_URL = "https://api.polygon.io/v3"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or POLYGON_API_KEY
        if not self.api_key:
            raise ValueError("Polygon.io API key is required.")

    def get_option_chain(self, ticker: str, expiry: str) -> Optional[List[Dict]]:
        """
        Fetch option contracts for a ticker and expiry from Polygon.io.
        Returns a list of contracts with OI and other fields.
        """
        url = f"{self.BASE_URL}/reference/options/contracts"
        params = {
            "underlying_ticker": ticker.upper(),
            "expiration_date": expiry,
            "limit": 1000,
            "apiKey": self.api_key
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            contracts = data.get("results", [])
            return contracts
        except Exception as e:
            logging.error(f"Polygon.io error for {ticker} {expiry}: {e}")
            return None

    def get_open_interest_map(self, ticker: str, expiry: str) -> Dict[str, int]:
        """
        Return a map: (option_type, strike) -> open_interest
        option_type: 'call' or 'put'
        strike: float (as string for key)
        """
        contracts = self.get_option_chain(ticker, expiry)
        oi_map = {}
        if not contracts:
            return oi_map
        for c in contracts:
            try:
                strike = float(c.get("strike_price"))
                option_type = c.get("type", "").lower()  # 'call' or 'put'
                oi = c.get("open_interest")
                if option_type in ("call", "put") and strike and oi is not None:
                    oi_map[(option_type, strike)] = oi
            except Exception:
                continue
        return oi_map

# Test function
if __name__ == "__main__":
    pf = PolygonFallback()
    ticker = "SPY"
    expiry = "2025-07-04"  # Next Friday expiry
    print(f"Testing Polygon.io fallback for {ticker} {expiry}...")
    contracts = pf.get_option_chain(ticker, expiry)
    if contracts:
        print(f"Found {len(contracts)} contracts.")
        print("Sample:", contracts[0])
    else:
        print("No contracts found or API error.")
    oi_map = pf.get_open_interest_map(ticker, expiry)
    print(f"OI map sample: {list(oi_map.items())[:3]}") 
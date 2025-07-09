import yfinance as yf
import pandas as pd
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .polygon_fallback import PolygonFallback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OptionsDataService:
    def __init__(self, cache_file='data/options_cache.json'):
        self.cache_file = cache_file
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_duration = timedelta(hours=1) # 1 hour cache duration
        self.polygon_fallback = PolygonFallback()
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.cache = data.get('options', {})
                    # Convert ISO format strings back to datetime objects
                    self.cache_timestamps = {k: datetime.fromisoformat(v) for k, v in data.get('timestamps', {}).items()}
                logging.info(f"Loaded options cache from {self.cache_file}")
            except Exception as e:
                logging.error(f"Error loading options cache from {self.cache_file}: {e}")
                self.cache = {}
                self.cache_timestamps = {}

    def _save_cache(self):
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_timestamps = {k: v.isoformat() for k, v in self.cache_timestamps.items()}
            data = {
                'options': self.cache,
                'timestamps': serializable_timestamps
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=4)
            logging.info(f"Saved options cache to {self.cache_file}")
        except Exception as e:
            logging.error(f"Error saving options cache to {self.cache_file}: {e}")

    def clear_cache(self):
        """
        Clears the in-memory cache and the file-based cache.
        """
        self.cache = {}
        self.cache_timestamps = {}
        self._save_cache()
        logging.info("Options cache cleared.")

    def fetch_options_chain(self, ticker_symbol: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches the options chain for a given ticker symbol using yfinance.
        Caches the results for 1 hour.
        """
        if not ticker_symbol:
            logging.error("Ticker symbol cannot be empty.")
            return None

        # Check cache first
        if not force_refresh and ticker_symbol in self.cache and \
           (datetime.now() - self.cache_timestamps[ticker_symbol]) < self.cache_duration:
            logging.info(f"Returning cached options data for {ticker_symbol}")
            return self.cache[ticker_symbol]

        try:
            ticker = yf.Ticker(ticker_symbol)
            options_data = {}
            # Get available expiration dates
            expirations = ticker.options

            if not expirations:
                logging.warning(f"No options expirations found for {ticker_symbol}")
                return None

            for exp in expirations:
                try:
                    opt = ticker.option_chain(exp)
                    # Convert DataFrames to serializable format
                    calls_data = opt.calls.to_dict(orient='records')
                    puts_data = opt.puts.to_dict(orient='records')
                    
                    # Convert any Timestamp objects to strings and handle NaN values
                    for call in calls_data:
                        for key, value in call.items():
                            if hasattr(value, 'isoformat'):  # Check if it's a Timestamp
                                call[key] = value.isoformat()
                            elif pd.isna(value):  # Handle NaN values
                                call[key] = None
                    
                    for put in puts_data:
                        for key, value in put.items():
                            if hasattr(value, 'isoformat'):  # Check if it's a Timestamp
                                put[key] = value.isoformat()
                            elif pd.isna(value):  # Handle NaN values
                                put[key] = None
                    
                    # Check if we need to use Polygon.io fallback for OI data
                    needs_oi_fallback = self._check_oi_fallback_needed(calls_data, puts_data)
                    
                    if needs_oi_fallback:
                        logging.info(f"Yahoo Finance returned zero OI for {ticker_symbol} on {exp}, using Polygon.io fallback")
                        try:
                            polygon_oi_map = self.polygon_fallback.get_open_interest_map(ticker_symbol, exp)
                            if polygon_oi_map:
                                calls_data = self._merge_oi_data_from_map(calls_data, polygon_oi_map, 'call')
                                puts_data = self._merge_oi_data_from_map(puts_data, polygon_oi_map, 'put')
                                logging.info(f"Successfully merged Polygon.io OI data for {ticker_symbol} on {exp}")
                            else:
                                logging.warning(f"Polygon.io fallback failed for {ticker_symbol} on {exp}")
                        except Exception as e:
                            logging.warning(f"Error using Polygon.io fallback for {ticker_symbol} on {exp}: {e}")
                    
                    options_data[exp] = {
                        'calls': calls_data,
                        'puts': puts_data
                    }
                except Exception as e:
                    logging.warning(f"Could not fetch options for {ticker_symbol} on {exp}: {e}")
                    continue
            
            if not options_data:
                logging.warning(f"No options data successfully fetched for {ticker_symbol}")
                return None

            logging.info(f"Successfully fetched options chain for {ticker_symbol}. Caching data.")
            self.cache[ticker_symbol] = options_data
            self.cache_timestamps[ticker_symbol] = datetime.now()
            self._save_cache()
            return options_data

        except Exception as e:
            logging.error(f"Error fetching options chain for {ticker_symbol}: {e}")
            return None

    def filter_weekly_options(self, options_chain: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters the options chain to include only weekly options (expiring on a Friday).
        """
        if not isinstance(options_chain, dict):
            logging.error("Invalid options_chain. Expected a dictionary.")
            return {}
        weekly_options = {}
        for exp_date_str, data in options_chain.items():
            try:
                # yfinance expiration dates are typically in YYYY-MM-DD format
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d')
                # Friday is weekday 4 (Monday is 0, Sunday is 6)
                if exp_date.weekday() == 4:
                    weekly_options[exp_date_str] = data
            except ValueError:
                logging.warning(f"Could not parse expiration date: {exp_date_str}")
                continue
        return weekly_options

    def filter_by_strike_range(self, options_chain: Dict[str, Any], current_price: float, strike_range_percentage: float = 0.10) -> Dict[str, Any]:
        """
        Filters options contracts based on a strike price range around the current stock price.
        Default range is +/- 10% of the current price.
        """
        if not isinstance(options_chain, dict):
            logging.error("Invalid options_chain. Expected a dictionary.")
            return {}
        if not current_price or current_price <= 0:
            logging.error("Current price must be a positive number for strike range filtering.")
            return {}
        if not (0 <= strike_range_percentage <= 1):
            logging.error("Strike range percentage must be between 0 and 1.")
            return {}

        filtered_options = {}
        lower_bound = current_price * (1 - strike_range_percentage)
        upper_bound = current_price * (1 + strike_range_percentage)

        for exp_date, data in options_chain.items():
            filtered_calls = []
            filtered_puts = []

            for call in data['calls']:
                if lower_bound <= call['strike'] <= upper_bound:
                    filtered_calls.append(call)
            
            for put in data['puts']:
                if lower_bound <= put['strike'] <= upper_bound:
                    filtered_puts.append(put)
            
            if filtered_calls or filtered_puts:
                filtered_options[exp_date] = {
                    'calls': filtered_calls,
                    'puts': filtered_puts
                }
        return filtered_options

        return filtered_options

    def extract_implied_volatility(self, option_contract: Dict[str, Any]) -> Optional[float]:
        """
        Extracts implied volatility from a single option contract.
        """
        if not isinstance(option_contract, dict):
            logging.warning("Invalid option contract format. Expected a dictionary.")
            return None
        
        iv = option_contract.get('impliedVolatility')
        if iv is None:
            logging.warning(f"Implied volatility not found for contract: {option_contract.get('contractSymbol', 'N/A')}")
            return None
        return iv

    def _check_oi_fallback_needed(self, calls_data: List[Dict], puts_data: List[Dict]) -> bool:
        """
        Check if we need to use Polygon.io fallback for OI data.
        Returns True if all OI values are zero or None.
        """
        def check_oi_values(options_list):
            if not options_list:
                return True
            for option in options_list:
                oi = option.get('openInterest')
                if oi is not None and oi != 0:
                    return False
            return True
        
        return check_oi_values(calls_data) and check_oi_values(puts_data)

    def _merge_oi_data_from_map(self, options_data: List[Dict], polygon_oi_map: Dict, option_type: str) -> List[Dict]:
        """
        Merge Polygon.io OI data with existing options data using the map format.
        Matches by strike price and option type.
        """
        for option in options_data:
            strike = option.get('strike')
            if strike is not None:
                # Look for matching OI data by strike price and option type
                map_key = (option_type, strike)
                if map_key in polygon_oi_map:
                    option['openInterest'] = polygon_oi_map[map_key]
                    option['oi_source'] = 'polygon'  # Mark the source
        
        return options_data

if __name__ == '__main__':
    # Example Usage:
    options_service = OptionsDataService()
    ticker = "AAPL"
    options_chain = options_service.fetch_options_chain(ticker)

    if options_chain:
        print(f"Options chain for {ticker}:")
        for exp_date, data in options_chain.items():
            print(f"  Expiration: {exp_date}")
            print(f"    Calls: {len(data['calls'])} contracts")
            print(f"    Puts: {len(data['puts'])} contracts")
            # print(data['calls'][0] if data['calls'] else "No calls")
            # print(data['puts'][0] if data['puts'] else "No puts")
    else:
        print(f"Failed to fetch options chain for {ticker}")

    ticker_invalid = "NONEXISTENTTICKER"
    options_chain_invalid = options_service.fetch_options_chain(ticker_invalid)
    if options_chain_invalid is None:
        print(f"\nSuccessfully handled invalid ticker: {ticker_invalid}")

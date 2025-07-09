import requests
import pandas as pd
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import yfinance as yf
from ..database.database_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockDataService:
    def __init__(self):
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_nasdaq_stocks(self) -> List[Dict[str, Any]]:
        """Fetch NASDAQ stocks from NASDAQ API."""
        try:
            # NASDAQ API endpoint for listed stocks
            url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data or 'rows' not in data['data']:
                logging.error("Invalid response format from NASDAQ API")
                return []
            
            stocks = []
            for row in data['data']['rows']:
                try:
                    # Parse market cap if available
                    market_cap = None
                    if 'marketCap' in row and row['marketCap']:
                        market_cap_str = str(row['marketCap']).replace('$', '').replace(',', '')
                        if 'B' in market_cap_str:
                            market_cap = float(market_cap_str.replace('B', '')) * 1e9
                        elif 'M' in market_cap_str:
                            market_cap = float(market_cap_str.replace('M', '')) * 1e6
                        elif 'K' in market_cap_str:
                            market_cap = float(market_cap_str.replace('K', '')) * 1e3
                        else:
                            market_cap = float(market_cap_str)
                    
                    stock_data = {
                        'symbol': row.get('symbol', '').strip(),
                        'company_name': row.get('name', '').strip(),
                        'exchange': row.get('exchange', 'NASDAQ'),
                        'sector': row.get('sector', ''),
                        'industry': row.get('industry', ''),
                        'market_cap': market_cap,
                        'is_etf': False
                    }
                    
                    if stock_data['symbol'] and stock_data['company_name']:
                        stocks.append(stock_data)
                        
                except Exception as e:
                    logging.warning(f"Error parsing stock row {row}: {e}")
                    continue
            
            logging.info(f"Fetched {len(stocks)} NASDAQ stocks")
            return stocks
            
        except Exception as e:
            logging.error(f"Error fetching NASDAQ stocks: {e}")
            return []

    def fetch_etfs(self) -> List[Dict[str, Any]]:
        """Fetch ETF data from multiple sources."""
        etfs = []
        
        try:
            # Try to fetch from ETF.com or similar
            url = "https://etfdb.com/etfs/"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                # Parse ETF data from the page
                # This is a simplified approach - in production you might want to use a proper ETF API
                logging.info("ETF fetching would require a dedicated ETF API or web scraping")
                
        except Exception as e:
            logging.warning(f"Error fetching ETFs: {e}")
        
        # For now, add some common ETFs manually
        common_etfs = [
            {'symbol': 'SPY', 'company_name': 'SPDR S&P 500 ETF Trust', 'exchange': 'NYSE', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'QQQ', 'company_name': 'Invesco QQQ Trust', 'exchange': 'NASDAQ', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'IWM', 'company_name': 'iShares Russell 2000 ETF', 'exchange': 'NYSE', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'VTI', 'company_name': 'Vanguard Total Stock Market ETF', 'exchange': 'NYSE', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'VOO', 'company_name': 'Vanguard S&P 500 ETF', 'exchange': 'NYSE', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'TQQQ', 'company_name': 'ProShares UltraPro QQQ', 'exchange': 'NASDAQ', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'SQQQ', 'company_name': 'ProShares UltraPro Short QQQ', 'exchange': 'NASDAQ', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'UVXY', 'company_name': 'ProShares Ultra VIX Short-Term Futures ETF', 'exchange': 'CBOE', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'TLT', 'company_name': 'iShares 20+ Year Treasury Bond ETF', 'exchange': 'NASDAQ', 'sector': 'ETF', 'is_etf': True},
            {'symbol': 'GLD', 'company_name': 'SPDR Gold Trust', 'exchange': 'NYSE', 'sector': 'ETF', 'is_etf': True},
        ]
        
        etfs.extend(common_etfs)
        logging.info(f"Added {len(etfs)} common ETFs")
        return etfs

    def fetch_popular_stocks(self) -> List[Dict[str, Any]]:
        """Fetch popular stocks that are commonly traded."""
        popular_stocks = [
            # Tech
            {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'MSFT', 'company_name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'GOOGL', 'company_name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'AMZN', 'company_name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'sector': 'Consumer Cyclical', 'is_etf': False},
            {'symbol': 'TSLA', 'company_name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'sector': 'Consumer Cyclical', 'is_etf': False},
            {'symbol': 'META', 'company_name': 'Meta Platforms Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'NVDA', 'company_name': 'NVIDIA Corporation', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'NFLX', 'company_name': 'Netflix Inc.', 'exchange': 'NASDAQ', 'sector': 'Communication Services', 'is_etf': False},
            {'symbol': 'AMD', 'company_name': 'Advanced Micro Devices Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            {'symbol': 'INTC', 'company_name': 'Intel Corporation', 'exchange': 'NASDAQ', 'sector': 'Technology', 'is_etf': False},
            
            # Finance
            {'symbol': 'JPM', 'company_name': 'JPMorgan Chase & Co.', 'exchange': 'NYSE', 'sector': 'Financial Services', 'is_etf': False},
            {'symbol': 'BAC', 'company_name': 'Bank of America Corp.', 'exchange': 'NYSE', 'sector': 'Financial Services', 'is_etf': False},
            {'symbol': 'WFC', 'company_name': 'Wells Fargo & Company', 'exchange': 'NYSE', 'sector': 'Financial Services', 'is_etf': False},
            {'symbol': 'GS', 'company_name': 'Goldman Sachs Group Inc.', 'exchange': 'NYSE', 'sector': 'Financial Services', 'is_etf': False},
            
            # Healthcare
            {'symbol': 'JNJ', 'company_name': 'Johnson & Johnson', 'exchange': 'NYSE', 'sector': 'Healthcare', 'is_etf': False},
            {'symbol': 'PFE', 'company_name': 'Pfizer Inc.', 'exchange': 'NYSE', 'sector': 'Healthcare', 'is_etf': False},
            {'symbol': 'UNH', 'company_name': 'UnitedHealth Group Inc.', 'exchange': 'NYSE', 'sector': 'Healthcare', 'is_etf': False},
            
            # Consumer
            {'symbol': 'KO', 'company_name': 'Coca-Cola Company', 'exchange': 'NYSE', 'sector': 'Consumer Defensive', 'is_etf': False},
            {'symbol': 'PEP', 'company_name': 'PepsiCo Inc.', 'exchange': 'NASDAQ', 'sector': 'Consumer Defensive', 'is_etf': False},
            {'symbol': 'WMT', 'company_name': 'Walmart Inc.', 'exchange': 'NYSE', 'sector': 'Consumer Defensive', 'is_etf': False},
            {'symbol': 'HD', 'company_name': 'Home Depot Inc.', 'exchange': 'NYSE', 'sector': 'Consumer Cyclical', 'is_etf': False},
            
            # Energy
            {'symbol': 'XOM', 'company_name': 'Exxon Mobil Corporation', 'exchange': 'NYSE', 'sector': 'Energy', 'is_etf': False},
            {'symbol': 'CVX', 'company_name': 'Chevron Corporation', 'exchange': 'NYSE', 'sector': 'Energy', 'is_etf': False},
            
            # Communication
            {'symbol': 'DIS', 'company_name': 'Walt Disney Company', 'exchange': 'NYSE', 'sector': 'Communication Services', 'is_etf': False},
            {'symbol': 'CMCSA', 'company_name': 'Comcast Corporation', 'exchange': 'NASDAQ', 'sector': 'Communication Services', 'is_etf': False},
        ]
        
        logging.info(f"Added {len(popular_stocks)} popular stocks")
        return popular_stocks

    def update_stock_database(self, force_refresh: bool = False) -> int:
        """Update the stock database with fresh data."""
        try:
            # Check if we need to refresh
            if not force_refresh:
                count = self.db.get_stocks_etfs_count()
                if count > 0:
                    logging.info(f"Database already contains {count} stocks/ETFs. Use force_refresh=True to update.")
                    return count
            
            logging.info("Starting stock database update...")
            
            # Clear existing data
            self.db.clear_stocks_etfs()
            
            all_stocks = []
            
            # Fetch NASDAQ stocks
            nasdaq_stocks = self.fetch_nasdaq_stocks()
            all_stocks.extend(nasdaq_stocks)
            
            # Fetch ETFs
            etfs = self.fetch_etfs()
            all_stocks.extend(etfs)
            
            # Add popular stocks
            popular_stocks = self.fetch_popular_stocks()
            all_stocks.extend(popular_stocks)
            
            # Remove duplicates based on symbol
            seen_symbols = set()
            unique_stocks = []
            for stock in all_stocks:
                symbol = stock['symbol'].upper()
                if symbol not in seen_symbols:
                    seen_symbols.add(symbol)
                    unique_stocks.append(stock)
            
            # Bulk insert into database
            inserted_count = self.db.bulk_insert_stocks_etfs(unique_stocks)
            
            logging.info(f"Successfully updated stock database with {inserted_count} stocks/ETFs")
            return inserted_count
            
        except Exception as e:
            logging.error(f"Error updating stock database: {e}")
            return 0

    def search_stocks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search stocks and ETFs by symbol or company name."""
        return self.db.search_stocks_etfs(query, limit)

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a stock/ETF."""
        return self.db.get_stock_etf_by_symbol(symbol)

    def validate_ticker(self, symbol: str) -> bool:
        """Validate if a ticker symbol exists in our database."""
        stock_info = self.get_stock_info(symbol)
        return stock_info is not None

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the stock database."""
        total_count = self.db.get_stocks_etfs_count()
        
        # Get counts by type
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM stocks_etfs WHERE is_etf = 1 AND is_active = 1")
            etf_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM stocks_etfs WHERE is_etf = 0 AND is_active = 1")
            stock_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT exchange) FROM stocks_etfs WHERE is_active = 1")
            exchange_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT sector) FROM stocks_etfs WHERE sector IS NOT NULL AND is_active = 1")
            sector_count = cursor.fetchone()[0]
            
            return {
                'total_count': total_count,
                'stock_count': stock_count,
                'etf_count': etf_count,
                'exchange_count': exchange_count,
                'sector_count': sector_count
            }
        finally:
            conn.close() 
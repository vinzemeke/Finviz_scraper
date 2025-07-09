import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_path='data/finviz_scraper.db'):
        self.db_path = db_path
        self._ensure_directory_exists()
        self._create_tables()

    def _ensure_directory_exists(self):
        dir_name = os.path.dirname(self.db_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE,
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                ticker_count INTEGER,
                error_message TEXT,
                content_hash TEXT,
                dedup_reason TEXT,
                FOREIGN KEY (url_id) REFERENCES urls(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticker_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                ticker_symbol TEXT NOT NULL,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES scraping_sessions(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticker_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                current_price REAL,
                market_cap REAL,
                pe_ratio REAL,
                volume REAL,
                fifty_two_week_high REAL,
                fifty_two_week_low REAL,
                fifty_two_week_range TEXT,
                ema_8 REAL,
                ema_21 REAL,
                ema_200 REAL,
                chart_path TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks_etfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                company_name TEXT NOT NULL,
                exchange TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                is_etf BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes separately
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_etfs_symbol ON stocks_etfs(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_etfs_company_name ON stocks_etfs(company_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_etfs_exchange ON stocks_etfs(exchange)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_etfs_sector ON stocks_etfs(sector)')
        conn.commit()
        conn.close()

    def insert_scraped_data(self, url, data_hash, data):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO scraped_data (url, hash, data) VALUES (?, ?, ?)",
                           (url, data_hash, data))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Duplicate entry for hash: {data_hash}. Skipping insertion.")
            return False
        finally:
            conn.close()

    def get_scraped_data_by_hash(self, data_hash):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT url, data FROM scraped_data WHERE hash = ?", (data_hash,))
        result = cursor.fetchone()
        conn.close()
        return result

    def get_all_scraped_data(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT url, data, timestamp FROM scraped_data ORDER BY timestamp DESC")
        results = cursor.fetchall()
        conn.close()
        return results

    def add_url(self, name: str, url: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO urls (name, url) VALUES (?, ?)", (name, url))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"URL with name '{name}' or URL '{url}' already exists. Skipping insertion.")
            return False
        finally:
            conn.close()

    def create_watchlist(self, name: str, user_id: Optional[int] = None) -> Optional[int]:
        if not name:
            logging.warning("Watchlist name cannot be empty.")
            return None
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO watchlists (name, user_id) VALUES (?, ?)", (name, user_id))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Watchlist with name '{name}' already exists. Skipping creation.")
            return None
        except Exception as e:
            logging.error(f"Error creating watchlist '{name}': {e}")
            return None
        finally:
            conn.close()

    def get_watchlist(self, watchlist_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, user_id, created_at FROM watchlists WHERE id = ?", (watchlist_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'name': row[1], 'user_id': row[2], 'created_at': row[3]}
        return None

    def list_watchlists(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT id, name, user_id, created_at FROM watchlists WHERE user_id = ? ORDER BY name", (user_id,))
        else:
            cursor.execute("SELECT id, name, user_id, created_at FROM watchlists ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [{'id': row[0], 'name': row[1], 'user_id': row[2], 'created_at': row[3]} for row in rows]

    def update_watchlist(self, watchlist_id: int, new_name: str) -> bool:
        if not new_name:
            logging.warning("New watchlist name cannot be empty.")
            return False
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE watchlists SET name = ? WHERE id = ?", (new_name, watchlist_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            logging.warning(f"Watchlist with name '{new_name}' already exists. Cannot update.")
            return False
        except Exception as e:
            logging.error(f"Error updating watchlist {watchlist_id}: {e}")
            return False
        finally:
            conn.close()

    def delete_watchlist(self, watchlist_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting watchlist {watchlist_id}: {e}")
            return False
        finally:
            conn.close()

    def add_ticker_to_watchlist(self, watchlist_id: int, ticker_symbol: str) -> bool:
        if not ticker_symbol:
            logging.warning("Ticker symbol cannot be empty.")
            return False
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO watchlist_tickers (watchlist_id, ticker_symbol) VALUES (?, ?)", (watchlist_id, ticker_symbol))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Ticker '{ticker_symbol}' already in watchlist {watchlist_id}. Skipping insertion.")
            return False
        except Exception as e:
            logging.error(f"Error adding ticker '{ticker_symbol}' to watchlist {watchlist_id}: {e}")
            return False
        finally:
            conn.close()

    def remove_ticker_from_watchlist(self, watchlist_id: int, ticker_symbol: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM watchlist_tickers WHERE watchlist_id = ? AND ticker_symbol = ?", (watchlist_id, ticker_symbol))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error removing ticker '{ticker_symbol}' from watchlist {watchlist_id}: {e}")
            return False
        finally:
            conn.close()

    def get_tickers_in_watchlist(self, watchlist_id: int) -> List[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker_symbol FROM watchlist_tickers WHERE watchlist_id = ? ORDER BY ticker_symbol", (watchlist_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def save_simulation_result(self, ticker: str, option_symbol: str, simulation_data: str) -> Optional[int]:
        if not ticker or not option_symbol or not simulation_data:
            logging.warning("Ticker, option symbol, and simulation data cannot be empty for simulation result.")
            return None
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO simulation_results (ticker, option_symbol, simulation_data) VALUES (?, ?, ?)",
                           (ticker, option_symbol, simulation_data))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving simulation result for {ticker} {option_symbol}: {e}")
            return None
        finally:
            conn.close()

    def get_simulation_result(self, simulation_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, ticker, option_symbol, simulation_data, created_at FROM simulation_results WHERE id = ?", (simulation_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'ticker': row[1], 'option_symbol': row[2], 'simulation_data': row[3], 'created_at': row[4]}
        return None

    def list_simulation_results(self, ticker: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT id, ticker, option_symbol, simulation_data, created_at FROM simulation_results"
        params = []
        if ticker:
            query += " WHERE ticker = ?"
            params.append(ticker)
        query += " ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [{'id': row[0], 'ticker': row[1], 'option_symbol': row[2], 'simulation_data': row[3], 'created_at': row[4]} for row in rows]

    def delete_simulation_result(self, simulation_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM simulation_results WHERE id = ?", (simulation_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting simulation result {simulation_id}: {e}")
            return False
        finally:
            conn.close()

    def save_user_preferences(self, user_id: int, underpricing_threshold: float, strike_range: float, other_settings: Optional[str] = None) -> bool:
        if not isinstance(user_id, int) or user_id < 0:
            logging.warning("User ID must be a non-negative integer.")
            return False
        if not (0 <= underpricing_threshold <= 1):
            logging.warning("Underpricing threshold must be between 0 and 1.")
            return False
        if not (0 <= strike_range <= 1):
            logging.warning("Strike range must be between 0 and 1.")
            return False
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_preferences (user_id, underpricing_threshold, strike_range, other_settings)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    underpricing_threshold=excluded.underpricing_threshold,
                    strike_range=excluded.strike_range,
                    other_settings=excluded.other_settings
            """, (user_id, underpricing_threshold, strike_range, other_settings))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving user preferences for user {user_id}: {e}")
            return False
        finally:
            conn.close()

    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, underpricing_threshold, strike_range, other_settings FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'user_id': row[0],
                'underpricing_threshold': row[1],
                'strike_range': row[2],
                'other_settings': row[3]
            }
        return None

    def update_user_preferences(self, user_id: int, underpricing_threshold: Optional[float] = None, strike_range: Optional[float] = None, other_settings: Optional[str] = None) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # First check if user preferences exist
        cursor.execute("SELECT COUNT(*) FROM user_preferences WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()[0] > 0
        
        if not exists:
            # Create new user preferences with defaults
            try:
                cursor.execute("""
                    INSERT INTO user_preferences (user_id, underpricing_threshold, strike_range, other_settings)
                    VALUES (?, ?, ?, ?)
                """, (user_id, 0.05, 0.10, "{}"))
                conn.commit()
            except Exception as e:
                logging.error(f"Error creating user preferences for user {user_id}: {e}")
                conn.close()
                return False
        
        # Now update the preferences
        updates = []
        params = []
        if underpricing_threshold is not None:
            updates.append("underpricing_threshold = ?")
            params.append(underpricing_threshold)
        if strike_range is not None:
            updates.append("strike_range = ?")
            params.append(strike_range)
        if other_settings is not None:
            updates.append("other_settings = ?")
            params.append(other_settings)

        if not updates:
            return True # No updates to perform, but preferences exist

        query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?"
        params.append(user_id)

        try:
            cursor.execute(query, tuple(params))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating user preferences for user {user_id}: {e}")
            return False
        finally:
            conn.close()

    def get_url_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, url, created_at, updated_at FROM urls WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'name': row[1], 'url': row[2], 'created_at': row[3], 'updated_at': row[4]}
        return None

    def list_urls(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, url, created_at, updated_at FROM urls")
        rows = cursor.fetchall()
        conn.close()
        return [{'id': row[0], 'name': row[1], 'url': row[2], 'created_at': row[3], 'updated_at': row[4]} for row in rows]

    def update_url(self, old_name: str, new_name: str, new_url: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE urls SET name = ?, url = ?, updated_at = ? WHERE name = ?",
                           (new_name, new_url, datetime.now().isoformat(), old_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_url(self, name: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM urls WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def url_exists(self, name: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls WHERE name = ?", (name,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def log_scrape_session(self, url_id: int, status: str, ticker_count: int, error_message: Optional[str], content_hash: Optional[str], dedup_reason: Optional[str]) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scraping_sessions (url_id, status, ticker_count, error_message, content_hash, dedup_reason) VALUES (?, ?, ?, ?, ?, ?)",
            (url_id, status, ticker_count, error_message, content_hash, dedup_reason)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_last_scrape_info(self, url_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, status, ticker_count, error_message, content_hash, dedup_reason FROM scraping_sessions WHERE url_id = ? ORDER BY timestamp DESC LIMIT 1",
            (url_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'session_id': row[0],
                'timestamp': row[1],
                'status': row[2],
                'ticker_count': row[3],
                'error_message': row[4],
                'content_hash': row[5],
                'dedup_reason': row[6]
            }
        return None

    def get_scrape_session_by_hash(self, url_id: int, content_hash: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, status, ticker_count, error_message, content_hash, dedup_reason FROM scraping_sessions WHERE url_id = ? AND content_hash = ? ORDER BY timestamp DESC LIMIT 1",
            (url_id, content_hash)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'session_id': row[0],
                'timestamp': row[1],
                'status': row[2],
                'ticker_count': row[3],
                'error_message': row[4],
                'content_hash': row[5],
                'dedup_reason': row[6]
            }
        return None

    def get_scrape_sessions_by_url(self, url_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT id, timestamp, status, ticker_count, error_message, content_hash, dedup_reason FROM scraping_sessions WHERE url_id = ? ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query, (url_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'session_id': row[0],
                'timestamp': row[1],
                'status': row[2],
                'ticker_count': row[3],
                'error_message': row[4],
                'content_hash': row[5],
                'dedup_reason': row[6]
            } for row in rows
        ]

    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def execute_update(self, query: str, params: Tuple = ()) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Returns:
            Number of rows affected
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount

    def get_database_stats(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get database size
        db_size = os.path.getsize(self.db_path)

        # Get table row counts
        tables = {}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()
        for table_name in table_names:
            table_name = table_name[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            tables[table_name] = cursor.fetchone()[0]

        conn.close()
        return {
            'database_size': db_size,
            'database_path': self.db_path,
            'tables': tables,
            'total_scraped_entries': tables.get('scraped_data', 0),
            'total_urls': tables.get('urls', 0),
            'completed_sessions': self._get_session_count('completed'),
            'skipped_sessions': self._get_session_count('skipped'),
            'failed_sessions': self._get_session_count('failed'),
            'total_ticker_properties': tables.get('ticker_properties', 0)
        }

    def _get_session_count(self, status: str) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scraping_sessions WHERE status = ?", (status,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def clear_all_data(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scraped_data")
        cursor.execute("DELETE FROM urls")
        cursor.execute("DELETE FROM scraping_sessions")
        cursor.execute("DELETE FROM ticker_results")
        cursor.execute("DELETE FROM ticker_properties")
        cursor.execute("DELETE FROM watchlists")
        cursor.execute("DELETE FROM watchlist_tickers")
        cursor.execute("DELETE FROM simulation_results")
        cursor.execute("DELETE FROM user_preferences")
        conn.commit()
        conn.close()

    def clear_all_ticker_properties(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ticker_properties")
        conn.commit()
        conn.close()

    def close(self):
        pass

    def save_ticker_properties(self, ticker: str, current_price: float, market_cap: float, pe_ratio: float, volume: float = None, fifty_two_week_high: float = None, fifty_two_week_low: float = None, fifty_two_week_range: str = None, ema_8: float = None, ema_21: float = None, ema_200: float = None, chart_path: str = None) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ticker_properties (ticker, current_price, market_cap, pe_ratio, volume, fifty_two_week_high, fifty_two_week_low, fifty_two_week_range, ema_8, ema_21, ema_200, chart_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    current_price=excluded.current_price,
                    market_cap=excluded.market_cap,
                    pe_ratio=excluded.pe_ratio,
                    volume=excluded.volume,
                    fifty_two_week_high=excluded.fifty_two_week_high,
                    fifty_two_week_low=excluded.fifty_two_week_low,
                    fifty_two_week_range=excluded.fifty_two_week_range,
                    ema_8=excluded.ema_8,
                    ema_21=excluded.ema_21,
                    ema_200=excluded.ema_200,
                    chart_path=excluded.chart_path,
                    last_updated=CURRENT_TIMESTAMP
            """, (ticker, current_price, market_cap, pe_ratio, volume, fifty_two_week_high, fifty_two_week_low, fifty_two_week_range, ema_8, ema_21, ema_200, chart_path))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving ticker properties for {ticker}: {e}")
            return False
        finally:
            conn.close()

    def get_ticker_properties(self, ticker: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, current_price, market_cap, pe_ratio, volume, fifty_two_week_high, fifty_two_week_low, fifty_two_week_range, ema_8, ema_21, ema_200, chart_path, last_updated
            FROM ticker_properties WHERE ticker = ?
        """, (ticker,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'ticker': row[0],
                'current_price': row[1],
                'market_cap': row[2],
                'pe_ratio': row[3],
                'volume': row[4],
                'fifty_two_week_high': row[5],
                'fifty_two_week_low': row[6],
                'fifty_two_week_range': row[7],
                'ema_8': row[8],
                'ema_21': row[9],
                'ema_200': row[10],
                'chart_path': row[11],
                'last_updated': row[12]
            }
        return None

    def delete_ticker_properties(self, ticker: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM ticker_properties WHERE ticker = ?", (ticker,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting ticker properties for {ticker}: {e}")
            return False
        finally:
            conn.close()

    # Stocks and ETFs management methods
    def add_stock_etf(self, symbol: str, company_name: str, exchange: str = None, 
                     sector: str = None, industry: str = None, market_cap: float = None, 
                     is_etf: bool = False) -> bool:
        """Add a stock or ETF to the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO stocks_etfs 
                (symbol, company_name, exchange, sector, industry, market_cap, is_etf, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (symbol.upper(), company_name, exchange, sector, industry, market_cap, is_etf))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding stock/ETF {symbol}: {e}")
            return False
        finally:
            conn.close()

    def search_stocks_etfs(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search stocks and ETFs by symbol or company name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Search by symbol (exact match first, then partial)
            cursor.execute("""
                SELECT symbol, company_name, exchange, sector, is_etf, market_cap
                FROM stocks_etfs 
                WHERE is_active = 1 AND (
                    symbol LIKE ? OR 
                    symbol LIKE ? OR 
                    company_name LIKE ? OR
                    company_name LIKE ?
                )
                ORDER BY 
                    CASE WHEN symbol = ? THEN 1
                         WHEN symbol LIKE ? THEN 2
                         WHEN company_name LIKE ? THEN 3
                         ELSE 4 END,
                    market_cap DESC NULLS LAST,
                    symbol
                LIMIT ?
            """, (
                query.upper(),  # Exact symbol match
                f"{query.upper()}%",  # Symbol starts with
                f"%{query}%",  # Company name contains
                f"{query}%",  # Company name starts with
                query.upper(),  # For ordering exact symbol matches first
                f"{query.upper()}%",  # For ordering symbol starts with
                f"{query}%",  # For ordering company name starts with
                limit
            ))
            
            rows = cursor.fetchall()
            return [{
                'symbol': row[0],
                'company_name': row[1],
                'exchange': row[2],
                'sector': row[3],
                'is_etf': bool(row[4]),
                'market_cap': row[5]
            } for row in rows]
        except Exception as e:
            logging.error(f"Error searching stocks/ETFs: {e}")
            return []
        finally:
            conn.close()

    def get_stock_etf_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock/ETF details by symbol."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT symbol, company_name, exchange, sector, industry, market_cap, is_etf
                FROM stocks_etfs 
                WHERE symbol = ? AND is_active = 1
            """, (symbol.upper(),))
            row = cursor.fetchone()
            if row:
                return {
                    'symbol': row[0],
                    'company_name': row[1],
                    'exchange': row[2],
                    'sector': row[3],
                    'industry': row[4],
                    'market_cap': row[5],
                    'is_etf': bool(row[6])
                }
            return None
        except Exception as e:
            logging.error(f"Error getting stock/ETF {symbol}: {e}")
            return None
        finally:
            conn.close()

    def bulk_insert_stocks_etfs(self, stocks_data: List[Dict[str, Any]]) -> int:
        """Bulk insert stocks and ETFs data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Prepare data for bulk insert
            data = []
            for stock in stocks_data:
                data.append((
                    stock.get('symbol', '').upper(),
                    stock.get('company_name', ''),
                    stock.get('exchange'),
                    stock.get('sector'),
                    stock.get('industry'),
                    stock.get('market_cap'),
                    stock.get('is_etf', False),
                    datetime.now()
                ))
            
            cursor.executemany("""
                INSERT OR REPLACE INTO stocks_etfs 
                (symbol, company_name, exchange, sector, industry, market_cap, is_etf, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
            return len(data)
        except Exception as e:
            conn.rollback()
            logging.error(f"Error bulk inserting stocks/ETFs: {e}")
            return 0
        finally:
            conn.close()

    def get_stocks_etfs_count(self) -> int:
        """Get total count of stocks and ETFs in database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM stocks_etfs WHERE is_active = 1")
            return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"Error getting stocks/ETFs count: {e}")
            return 0
        finally:
            conn.close()

    def clear_stocks_etfs(self) -> bool:
        """Clear all stocks and ETFs data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM stocks_etfs")
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error clearing stocks/ETFs: {e}")
            return False
        finally:
            conn.close()

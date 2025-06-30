"""
Data Storage for Finviz Stock Scraper.
Manages ticker data storage with SQLite database and CSV export.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.database.database_manager import DatabaseManager
from src.storage.url_manager import URLManager

logger = logging.getLogger(__name__)

class DataStorage:
    """Manages ticker data storage with SQLite database."""
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None, url_manager: Optional[URLManager] = None):
        """Initialize the data storage.
        
        Args:
            database_manager: Optional database manager instance.
                             If None, creates a new one.
            url_manager: Optional URL manager instance.
                        If None, creates a new one.
        """
        self.db_manager = database_manager or DatabaseManager()
        self.url_manager = url_manager or URLManager(self.db_manager)
        
        # Ensure results directory exists for CSV exports
        self.results_dir = Path(__file__).parent.parent.parent / 'data' / 'results'
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def save_tickers_to_database(self, url_name: str, tickers: List[str], status: str = 'completed', error_message: Optional[str] = None) -> Optional[int]:
        """Save ticker data to SQLite database.
        
        Args:
            url_name: Name of the URL that was scraped
            tickers: List of ticker symbols
            status: Status of the scraping session ('completed', 'failed', etc.)
            error_message: Error message if scraping failed
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            # Get URL ID
            url_data = self.url_manager.get_url_by_name(url_name)
            if not url_data:
                logger.error(f"URL '{url_name}' not found in database")
                return None
            
            url_id = url_data['id']
            
            # Create scraping session
            session_result = self.db_manager.execute_update(
                "INSERT INTO scraping_sessions (url_id, status, ticker_count, error_message) VALUES (?, ?, ?, ?)",
                (url_id, status, len(tickers), error_message)
            )
            
            if not session_result:
                logger.error("Failed to create scraping session")
                return None
            
            # Get session ID
            session_id = self.db_manager.execute_query("SELECT last_insert_rowid()")[0][0]
            
            # Insert ticker data
            if tickers:
                ticker_data = [(session_id, ticker) for ticker in tickers]
                self.db_manager.execute_many(
                    "INSERT INTO ticker_results (session_id, ticker_symbol) VALUES (?, ?)",
                    ticker_data
                )
                
                # Update session ticker count
                self.db_manager.execute_update(
                    "UPDATE scraping_sessions SET ticker_count = ? WHERE id = ?",
                    (len(tickers), session_id)
                )
            
            logger.info(f"Saved {len(tickers)} tickers to database for session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error saving tickers to database: {e}")
            return None
    
    def save_tickers_to_csv(self, url_name: str, tickers: List[str]) -> Optional[str]:
        """Save ticker data to CSV file (for backward compatibility).
        
        Args:
            url_name: Name of the URL that was scraped
            tickers: List of ticker symbols
            
        Returns:
            Path to the CSV file if successful, None otherwise
        """
        try:
            # Save to database first
            session_id = self.save_tickers_to_database(url_name, tickers)
            if not session_id:
                return None
            
            # Also save to CSV for backward compatibility
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"{url_name}_{timestamp}.csv"
            filepath = self.results_dir / filename
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['url_name', 'ticker_symbol', 'timestamp'])
                
                for ticker in tickers:
                    writer.writerow([url_name, ticker, timestamp])
            
            logger.info(f"Saved {len(tickers)} tickers to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving tickers to CSV: {e}")
            return None
    
    def get_tickers_from_database(self, url_name: str, limit: Optional[int] = None) -> List[str]:
        """Get ticker symbols from database for a specific URL.
        
        Args:
            url_name: Name of the URL
            limit: Maximum number of tickers to return (None for all)
            
        Returns:
            List of ticker symbols
        """
        try:
            # Get URL ID
            url_data = self.url_manager.get_url_by_name(url_name)
            if not url_data:
                logger.warning(f"URL '{url_name}' not found")
                return []
            
            url_id = url_data['id']
            
            # Get latest session
            session_result = self.db_manager.execute_query(
                "SELECT id FROM scraping_sessions WHERE url_id = ? AND status = 'completed' "
                "ORDER BY timestamp DESC LIMIT 1",
                (url_id,)
            )
            
            if not session_result:
                logger.warning(f"No completed sessions found for URL '{url_name}'")
                return []
            
            session_id = session_result[0][0]
            
            # Get tickers
            query = "SELECT ticker_symbol FROM ticker_results WHERE session_id = ? ORDER BY scraped_at"
            if limit:
                query += f" LIMIT {limit}"
            
            results = self.db_manager.execute_query(query, (session_id,))
            tickers = [row[0] for row in results]
            
            logger.debug(f"Retrieved {len(tickers)} tickers for URL '{url_name}'")
            return tickers
            
        except Exception as e:
            logger.error(f"Error getting tickers from database: {e}")
            return []
    
    def get_all_tickers_from_database(self, url_name: str) -> List[Dict[str, Any]]:
        """Get all ticker data from database for a specific URL.
        
        Args:
            url_name: Name of the URL
            
        Returns:
            List of dictionaries with ticker data and session information
        """
        try:
            # Get URL ID
            url_data = self.url_manager.get_url_by_name(url_name)
            if not url_data:
                logger.warning(f"URL '{url_name}' not found")
                return []
            
            url_id = url_data['id']
            
            # Get all sessions and their tickers
            results = self.db_manager.execute_query(
                "SELECT s.id, s.timestamp, s.status, s.ticker_count, s.error_message, "
                "t.ticker_symbol, t.scraped_at "
                "FROM scraping_sessions s "
                "LEFT JOIN ticker_results t ON s.id = t.session_id "
                "WHERE s.url_id = ? "
                "ORDER BY s.timestamp DESC, t.scraped_at",
                (url_id,)
            )
            
            sessions = {}
            for row in results:
                session_id = row[0]
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_id': session_id,
                        'timestamp': row[1],
                        'status': row[2],
                        'ticker_count': row[3],
                        'error_message': row[4],
                        'tickers': []
                    }
                
                if row[5]:  # ticker_symbol is not None
                    sessions[session_id]['tickers'].append({
                        'symbol': row[5],
                        'scraped_at': row[6]
                    })
            
            return list(sessions.values())
            
        except Exception as e:
            logger.error(f"Error getting all ticker data from database: {e}")
            return []
    
    def get_ticker_history(self, ticker_symbol: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get scraping history for a specific ticker symbol.
        
        Args:
            ticker_symbol: Ticker symbol to search for
            limit: Maximum number of results to return (None for all)
            
        Returns:
            List of dictionaries with scraping session information
        """
        try:
            query = """
                SELECT t.scraped_at, s.timestamp, u.name, s.status, s.ticker_count
                FROM ticker_results t
                JOIN scraping_sessions s ON t.session_id = s.id
                JOIN urls u ON s.url_id = u.id
                WHERE t.ticker_symbol = ?
                ORDER BY t.scraped_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = self.db_manager.execute_query(query, (ticker_symbol,))
            
            history = []
            for row in results:
                history.append({
                    'scraped_at': row[0],
                    'session_timestamp': row[1],
                    'url_name': row[2],
                    'status': row[3],
                    'total_tickers': row[4]
                })
            
            logger.debug(f"Retrieved {len(history)} history entries for ticker '{ticker_symbol}'")
            return history
            
        except Exception as e:
            logger.error(f"Error getting ticker history: {e}")
            return []
    
    def search_tickers(self, search_term: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for ticker symbols in the database.
        
        Args:
            search_term: Search term to match against ticker symbols
            limit: Maximum number of results to return (None for all)
            
        Returns:
            List of dictionaries with ticker information
        """
        try:
            search_pattern = f"%{search_term}%"
            query = """
                SELECT DISTINCT t.ticker_symbol, COUNT(*) as occurrence_count,
                       MAX(t.scraped_at) as last_seen
                FROM ticker_results t
                WHERE t.ticker_symbol LIKE ?
                GROUP BY t.ticker_symbol
                ORDER BY occurrence_count DESC, last_seen DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = self.db_manager.execute_query(query, (search_pattern,))
            
            tickers = []
            for row in results:
                tickers.append({
                    'symbol': row[0],
                    'occurrence_count': row[1],
                    'last_seen': row[2]
                })
            
            logger.debug(f"Found {len(tickers)} tickers matching '{search_term}'")
            return tickers
            
        except Exception as e:
            logger.error(f"Error searching tickers: {e}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored ticker data.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            stats = {}
            
            # Total tickers
            total_result = self.db_manager.execute_query("SELECT COUNT(*) FROM ticker_results")
            stats['total_tickers'] = total_result[0][0] if total_result else 0
            
            # Unique tickers
            unique_result = self.db_manager.execute_query("SELECT COUNT(DISTINCT ticker_symbol) FROM ticker_results")
            stats['unique_tickers'] = unique_result[0][0] if unique_result else 0
            
            # Total sessions
            sessions_result = self.db_manager.execute_query("SELECT COUNT(*) FROM scraping_sessions")
            stats['total_sessions'] = sessions_result[0][0] if sessions_result else 0
            
            # Completed sessions
            completed_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM scraping_sessions WHERE status = 'completed'"
            )
            stats['completed_sessions'] = completed_result[0][0] if completed_result else 0
            
            # Failed sessions
            failed_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM scraping_sessions WHERE status = 'failed'"
            )
            stats['failed_sessions'] = failed_result[0][0] if failed_result else 0
            
            # Recent activity (last 7 days)
            recent_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM ticker_results WHERE scraped_at >= datetime('now', '-7 days')"
            )
            stats['recent_tickers'] = recent_result[0][0] if recent_result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    def export_to_csv(self, url_name: str, output_path: Optional[str] = None) -> Optional[str]:
        """Export ticker data for a URL to CSV file.
        
        Args:
            url_name: Name of the URL to export
            output_path: Optional custom output path
            
        Returns:
            Path to the exported CSV file if successful, None otherwise
        """
        try:
            # Get ticker data
            tickers = self.get_tickers_from_database(url_name)
            if not tickers:
                logger.warning(f"No ticker data found for URL '{url_name}'")
                return None
            
            # Determine output path
            if not output_path:
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f"{url_name}_export_{timestamp}.csv"
                output_path = str(self.results_dir / filename)
            
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['url_name', 'ticker_symbol', 'export_timestamp'])
                
                for ticker in tickers:
                    writer.writerow([url_name, ticker, datetime.now().isoformat()])
            
            logger.info(f"Exported {len(tickers)} tickers to CSV: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None
    
    def get_tickers_for_url(self, url_name: str) -> List[str]:
        """Get the most recent ticker symbols for a specific URL.
        
        Args:
            url_name: Name of the URL
            
        Returns:
            List of ticker symbols from the most recent successful scraping
        """
        return self.get_tickers_from_database(url_name) 
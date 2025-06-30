"""
Database manager for Finviz Stock Scraper.
Handles SQLite database connections, initialization, and basic operations.
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from pathlib import Path

from config.database_config import (
    get_database_path, 
    ensure_data_directory,
    DATABASE_CONFIG,
    PERFORMANCE_CONFIG
)
from src.database.schema import get_schema_statements, get_table_names

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, database_path: Optional[str] = None):
        """Initialize the database manager.
        
        Args:
            database_path: Optional custom path to the database file.
                          If None, uses the default path from config.
        """
        self.database_path = database_path or str(get_database_path())
        self._connection = None
        self._initialized = False
        
        # Ensure data directory exists
        ensure_data_directory()
        
        # Initialize database if it doesn't exist
        if not self._is_database_initialized():
            self.initialize_database()
    
    def _is_database_initialized(self) -> bool:
        """Check if the database is properly initialized with all tables."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if all required tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN (?, ?, ?)
                """, get_table_names())
                
                existing_tables = {row[0] for row in cursor.fetchall()}
                required_tables = set(get_table_names())
                
                return existing_tables == required_tables
                
        except Exception as e:
            logger.error(f"Error checking database initialization: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize the database with schema and indexes.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Execute all schema statements
                schema_statements = get_schema_statements()
                for statement in schema_statements:
                    cursor.execute(statement)
                
                conn.commit()
                self._initialized = True
                logger.info("Database initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        connection = None
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=DATABASE_CONFIG['timeout'],
                check_same_thread=DATABASE_CONFIG['check_same_thread'],
                isolation_level=DATABASE_CONFIG['isolation_level']
            )
            
            # Configure connection for better performance
            connection.execute(f"PRAGMA cache_size = {PERFORMANCE_CONFIG['cache_size']}")
            connection.execute(f"PRAGMA temp_store = {PERFORMANCE_CONFIG['temp_store']}")
            connection.execute(f"PRAGMA synchronous = {PERFORMANCE_CONFIG['synchronous']}")
            connection.execute(f"PRAGMA journal_mode = '{PERFORMANCE_CONFIG['journal_mode']}'")
            
            yield connection
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if connection:
                connection.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in database operation: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, query: str, parameters: Tuple = ()) -> List[Tuple]:
        """Execute a SELECT query and return results.
        
        Args:
            query: SQL SELECT query
            parameters: Query parameters
            
        Returns:
            List of result rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, parameters)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def execute_update(self, query: str, parameters: Tuple = ()) -> int:
        """Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL INSERT/UPDATE/DELETE query
            parameters: Query parameters
            
        Returns:
            Number of affected rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, parameters)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing update: {e}")
            raise
    
    def execute_many(self, query: str, parameters_list: List[Tuple]) -> int:
        """Execute the same query with multiple parameter sets.
        
        Args:
            query: SQL query
            parameters_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, parameters_list)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing batch update: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get information about a table's columns.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                return [
                    {
                        'cid': col[0],
                        'name': col[1],
                        'type': col[2],
                        'notnull': bool(col[3]),
                        'default_value': col[4],
                        'pk': bool(col[5])
                    }
                    for col in columns
                ]
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and information.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {
                    'database_path': self.database_path,
                    'database_size': Path(self.database_path).stat().st_size if Path(self.database_path).exists() else 0,
                    'tables': {}
                }
                
                # Get row counts for each table
                for table_name in get_table_names():
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats['tables'][table_name] = count
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_path: Path where to save the backup
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            import shutil
            shutil.copy2(self.database_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def vacuum_database(self) -> bool:
        """Optimize the database by rebuilding it to reclaim unused space.
        
        Returns:
            True if vacuum was successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuum completed")
                return True
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            return False
    
    def get_last_scrape_info(self, url_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent scrape info for a given URL ID."""
        try:
            result = self.execute_query(
                "SELECT id, timestamp, content_hash, status, dedup_reason FROM scraping_sessions WHERE url_id = ? ORDER BY timestamp DESC LIMIT 1",
                (url_id,)
            )
            if result:
                row = result[0]
                return {
                    'session_id': row[0],
                    'timestamp': row[1],
                    'content_hash': row[2],
                    'status': row[3],
                    'dedup_reason': row[4],
                }
            return None
        except Exception as e:
            logger.error(f"Error getting last scrape info: {e}")
            return None

    def log_scrape_session(self, url_id: int, status: str, ticker_count: int = 0, error_message: str = None, content_hash: str = None, dedup_reason: str = None) -> int:
        """Insert a new scraping session log with deduplication info."""
        try:
            return self.execute_update(
                "INSERT INTO scraping_sessions (url_id, status, ticker_count, error_message, content_hash, dedup_reason) VALUES (?, ?, ?, ?, ?, ?)",
                (url_id, status, ticker_count, error_message, content_hash, dedup_reason)
            )
        except Exception as e:
            logger.error(f"Error logging scrape session: {e}")
            return 0

    def get_scrape_sessions_by_url(self, url_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scrape sessions for a given URL ID."""
        try:
            results = self.execute_query(
                "SELECT id, timestamp, status, content_hash, dedup_reason FROM scraping_sessions WHERE url_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                (url_id, limit)
            )
            return [
                {
                    'session_id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'content_hash': row[3],
                    'dedup_reason': row[4],
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error getting scrape sessions by url: {e}")
            return []

    def get_scrape_session_by_hash(self, url_id: int, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get a scrape session for a URL with a specific content hash."""
        try:
            result = self.execute_query(
                "SELECT id, timestamp, status, dedup_reason FROM scraping_sessions WHERE url_id = ? AND content_hash = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
                (url_id, content_hash)
            )
            if result:
                row = result[0]
                return {
                    'session_id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'dedup_reason': row[3],
                }
            return None
        except Exception as e:
            logger.error(f"Error getting scrape session by hash: {e}")
            return None 
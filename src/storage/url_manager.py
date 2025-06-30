"""
URL Manager for Finviz Stock Scraper.
Manages Finviz URLs with SQLite database storage.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class URLManager:
    """Manages Finviz URLs with SQLite database storage."""
    
    def __init__(self, database_manager: Optional[DatabaseManager] = None):
        """Initialize the URL manager.
        
        Args:
            database_manager: Optional database manager instance.
                             If None, creates a new one.
        """
        self.db_manager = database_manager or DatabaseManager()
    
    def save_url(self, name: str, url: str) -> bool:
        """Save a Finviz URL with a custom name.
        
        Args:
            name: Custom name for the URL (e.g., "TPS SCANNER")
            url: Finviz screener URL
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Check if URL with this name already exists
            existing = self.db_manager.execute_query(
                "SELECT id FROM urls WHERE name = ?",
                (name,)
            )
            
            if existing:
                logger.warning(f"URL with name '{name}' already exists")
                return False
            
            # Insert new URL
            result = self.db_manager.execute_update(
                "INSERT INTO urls (name, url) VALUES (?, ?)",
                (name, url)
            )
            
            if result > 0:
                logger.info(f"Saved URL '{name}' successfully")
                return True
            else:
                logger.error(f"Failed to save URL '{name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error saving URL '{name}': {e}")
            return False
    
    def get_url(self, name: str) -> Optional[str]:
        """Get a Finviz URL by name.
        
        Args:
            name: Custom name of the URL
            
        Returns:
            URL string if found, None otherwise
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT url FROM urls WHERE name = ?",
                (name,)
            )
            
            if result:
                return result[0][0]
            else:
                logger.debug(f"URL '{name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting URL '{name}': {e}")
            return None
    
    def get_url_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get URL data by name including metadata.
        
        Args:
            name: Custom name of the URL
            
        Returns:
            Dictionary with URL data if found, None otherwise
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT id, name, url, created_at, updated_at FROM urls WHERE name = ?",
                (name,)
            )
            
            if result:
                row = result[0]
                return {
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                }
            else:
                logger.debug(f"URL '{name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting URL data for '{name}': {e}")
            return None
    
    def list_urls(self) -> List[Dict[str, Any]]:
        """List all saved URLs with metadata.
        
        Returns:
            List of dictionaries containing URL data
        """
        try:
            results = self.db_manager.execute_query(
                "SELECT id, name, url, created_at, updated_at FROM urls ORDER BY created_at DESC"
            )
            
            urls = []
            for row in results:
                urls.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            
            logger.debug(f"Retrieved {len(urls)} URLs")
            return urls
            
        except Exception as e:
            logger.error(f"Error listing URLs: {e}")
            return []
    
    def update_url(self, old_name: str, new_name: str, new_url: str) -> bool:
        """Update an existing URL.
        
        Args:
            old_name: Current name of the URL
            new_name: New name for the URL
            new_url: New URL string
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Check if old URL exists
            existing = self.db_manager.execute_query(
                "SELECT id FROM urls WHERE name = ?",
                (old_name,)
            )
            
            if not existing:
                logger.warning(f"URL '{old_name}' not found")
                return False
            
            # Check if new name conflicts with existing URL (unless it's the same URL)
            if old_name != new_name:
                conflict = self.db_manager.execute_query(
                    "SELECT id FROM urls WHERE name = ?",
                    (new_name,)
                )
                
                if conflict:
                    logger.warning(f"URL with name '{new_name}' already exists")
                    return False
            
            # Update the URL
            result = self.db_manager.execute_update(
                "UPDATE urls SET name = ?, url = ? WHERE name = ?",
                (new_name, new_url, old_name)
            )
            
            if result > 0:
                logger.info(f"Updated URL '{old_name}' to '{new_name}'")
                return True
            else:
                logger.error(f"Failed to update URL '{old_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error updating URL '{old_name}': {e}")
            return False
    
    def delete_url(self, name: str) -> bool:
        """Delete a URL by name.
        
        Args:
            name: Name of the URL to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Check if URL exists
            existing = self.db_manager.execute_query(
                "SELECT id FROM urls WHERE name = ?",
                (name,)
            )
            
            if not existing:
                logger.warning(f"URL '{name}' not found")
                return False
            
            # Delete the URL (cascading delete will handle related sessions and results)
            result = self.db_manager.execute_update(
                "DELETE FROM urls WHERE name = ?",
                (name,)
            )
            
            if result > 0:
                logger.info(f"Deleted URL '{name}' successfully")
                return True
            else:
                logger.error(f"Failed to delete URL '{name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting URL '{name}': {e}")
            return False
    
    def url_exists(self, name: str) -> bool:
        """Check if a URL with the given name exists.
        
        Args:
            name: Name to check
            
        Returns:
            True if URL exists, False otherwise
        """
        try:
            result = self.db_manager.execute_query(
                "SELECT id FROM urls WHERE name = ?",
                (name,)
            )
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error checking if URL '{name}' exists: {e}")
            return False
    
    def search_urls(self, search_term: str) -> List[Dict[str, Any]]:
        """Search URLs by name or URL content.
        
        Args:
            search_term: Search term to match against names or URLs
            
        Returns:
            List of matching URLs
        """
        try:
            search_pattern = f"%{search_term}%"
            results = self.db_manager.execute_query(
                "SELECT id, name, url, created_at, updated_at FROM urls "
                "WHERE name LIKE ? OR url LIKE ? "
                "ORDER BY created_at DESC",
                (search_pattern, search_pattern)
            )
            
            urls = []
            for row in results:
                urls.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            
            logger.debug(f"Found {len(urls)} URLs matching '{search_term}'")
            return urls
            
        except Exception as e:
            logger.error(f"Error searching URLs: {e}")
            return []
    
    def get_url_stats(self) -> Dict[str, Any]:
        """Get statistics about saved URLs.
        
        Returns:
            Dictionary with URL statistics
        """
        try:
            stats = {}
            
            # Total URLs
            total_result = self.db_manager.execute_query("SELECT COUNT(*) FROM urls")
            stats['total_urls'] = total_result[0][0] if total_result else 0
            
            # URLs by creation date (last 30 days)
            recent_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM urls WHERE created_at >= datetime('now', '-30 days')"
            )
            stats['recent_urls'] = recent_result[0][0] if recent_result else 0
            
            # Most recent URL
            latest_result = self.db_manager.execute_query(
                "SELECT name, created_at FROM urls ORDER BY created_at DESC LIMIT 1"
            )
            if latest_result:
                stats['latest_url'] = {
                    'name': latest_result[0][0],
                    'created_at': latest_result[0][1]
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting URL stats: {e}")
            return {}
    
    def get_url_with_sessions(self, name: str) -> Optional[Dict[str, Any]]:
        """Get URL data with associated scraping sessions.
        
        Args:
            name: Name of the URL
            
        Returns:
            Dictionary with URL data and sessions, None if not found
        """
        try:
            # Get URL data
            url_data = self.get_url_by_name(name)
            if not url_data:
                return None
            
            # Get associated sessions
            sessions_result = self.db_manager.execute_query(
                "SELECT id, timestamp, status, ticker_count, error_message "
                "FROM scraping_sessions WHERE url_id = ? "
                "ORDER BY timestamp DESC",
                (url_data['id'],)
            )
            
            sessions = []
            for row in sessions_result:
                sessions.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'ticker_count': row[3],
                    'error_message': row[4]
                })
            
            url_data['sessions'] = sessions
            return url_data
            
        except Exception as e:
            logger.error(f"Error getting URL with sessions for '{name}': {e}")
            return None 
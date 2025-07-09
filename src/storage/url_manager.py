"""
URL Manager for Finviz Stock Scraper.
Manages Finviz URLs with SQLite database storage.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

from src.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

URLS_FILE = Path('data/saved_urls.json')

class URLManager:
    """Manages Finviz URLs with SQLite database storage."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the URL manager with a DatabaseManager instance."""
        self.db_manager = db_manager

    def save_url(self, name: str, url: str) -> bool:
        """Save a Finviz URL with a custom name to the database.
        
        Args:
            name: Custom name for the URL (e.g., "TPS SCANNER")
            url: Finviz screener URL
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            success = self.db_manager.add_url(name, url)
            if success:
                logger.info(f"Saved URL '{name}' successfully to database")
            return success
        except Exception as e:
            logger.error(f"Error saving URL '{name}' to database: {e}")
            return False
    
    def get_url(self, name: str) -> Optional[str]:
        """Get a Finviz URL by name from the database.
        
        Args:
            name: Custom name of the URL
            
        Returns:
            URL string if found, None otherwise
        """
        try:
            url_data = self.db_manager.get_url_by_name(name)
            if url_data:
                return url_data['url']
            logger.debug(f"URL '{name}' not found in database")
            return None
        except Exception as e:
            logger.error(f"Error getting URL '{name}' from database: {e}")
            return None
    
    def get_url_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get URL data by name including metadata from the database.
        
        Args:
            name: Custom name of the URL
            
        Returns:
            Dictionary with URL data if found, None otherwise
        """
        try:
            return self.db_manager.get_url_by_name(name)
        except Exception as e:
            logger.error(f"Error getting URL data for '{name}' from database: {e}")
            return None
    
    def list_urls(self) -> List[Dict[str, Any]]:
        """List all saved URLs with metadata from the database.
        
        Returns:
            List of dictionaries containing URL data
        """
        try:
            urls = self.db_manager.list_urls()
            logger.debug(f"Retrieved {len(urls)} URLs from database")
            return urls
        except Exception as e:
            logger.error(f"Error listing URLs from database: {e}")
            return []
    
    def update_url(self, old_name: str, new_name: str, new_url: str) -> bool:
        """Update an existing URL in the database.
        
        Args:
            old_name: Current name of the URL
            new_name: New name for the URL
            new_url: New URL string
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            success = self.db_manager.update_url(old_name, new_name, new_url)
            if success:
                logger.info(f"Updated URL '{old_name}' to '{new_name}' in database")
            return success
        except Exception as e:
            logger.error(f"Error updating URL '{old_name}' in database: {e}")
            return False
    
    def delete_url(self, name: str) -> bool:
        """Delete a URL by name from the database.
        
        Args:
            name: Name of the URL to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            success = self.db_manager.delete_url(name)
            if success:
                logger.info(f"Deleted URL '{name}' successfully from database")
            return success
        except Exception as e:
            logger.error(f"Error deleting URL '{name}' from database: {e}")
            return False
    
    def url_exists(self, name: str) -> bool:
        """Check if a URL with the given name exists in the database.
        
        Args:
            name: Name to check
            
        Returns:
            True if URL exists, False otherwise
        """
        try:
            return self.db_manager.url_exists(name)
        except Exception as e:
            logger.error(f"Error checking if URL '{name}' exists in database: {e}")
            return False
    
    def search_urls(self, search_term: str) -> List[Dict[str, Any]]:
        """Search URLs by name or URL content in the database.
        
        Args:
            search_term: Search term to match against names or URLs
            
        Returns:
            List of matching URLs
        """
        try:
            # This would require a new method in DatabaseManager for searching URLs
            # For now, we'll fetch all and filter in memory (less efficient for large datasets)
            all_urls = self.db_manager.list_urls()
            matching_urls = []
            for u in all_urls:
                if search_term.lower() in u['name'].lower() or search_term.lower() in u['url'].lower():
                    matching_urls.append(u)
            logger.debug(f"Found {len(matching_urls)} URLs matching '{search_term}' in database")
            return matching_urls
        except Exception as e:
            logger.error(f"Error searching URLs in database: {e}")
            return []
    
    def get_url_stats(self) -> Dict[str, Any]:
        """Get statistics about saved URLs from the database.
        
        Returns:
            Dictionary with URL statistics
        """
        try:
            # This would require new methods in DatabaseManager for specific stats
            # For now, we'll fetch all and calculate in memory
            all_urls = self.db_manager.list_urls()
            stats = {}
            
            # Total URLs
            stats['total_urls'] = len(all_urls)
            
            # URLs by creation date (last 30 days) - requires parsing datetime strings
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_urls_count = 0
            for u in all_urls:
                created_at = datetime.fromisoformat(u['created_at'])
                if created_at >= thirty_days_ago:
                    recent_urls_count += 1
            stats['recent_urls'] = recent_urls_count
            
            # Most recent URL
            if all_urls:
                latest_url_data = max(all_urls, key=lambda x: x['created_at'])
                stats['latest_url'] = {
                    'name': latest_url_data['name'],
                    'created_at': latest_url_data['created_at']
                }
            else:
                stats['latest_url'] = None
            
            return stats
        except Exception as e:
            logger.error(f"Error getting URL stats from database: {e}")
            return {}

    def get_url_with_sessions(self, name: str) -> Optional[Dict[str, Any]]:
        """Get URL data by name including associated scraping sessions from the database.
        
        Args:
            name: Custom name of the URL
            
        Returns:
            Dictionary with URL data and sessions if found, None otherwise
        """
        try:
            url_data = self.db_manager.get_url_by_name(name)
            if url_data:
                url_data['sessions'] = self.db_manager.get_scrape_sessions_by_url(url_data['id'])
            return url_data
        except Exception as e:
            logger.error(f"Error getting URL with sessions from database: {e}")
            return None
 
"""
Scraper Engine with Hash-Based Deduplication Logic
Integrates with FinvizScraper and PaginationHandler to avoid redundant scraping.
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from src.scraper.finviz_scraper import FinvizScraper
from src.utils.pagination import PaginationHandler
from src.database.database_manager import DatabaseManager
from src.storage.url_manager import URLManager
from config.settings import DEDUP_TIME_WINDOW_HOURS, DEDUP_ENABLE_CONTENT_HASH, DEDUP_LOG_SKIPS, DEDUP_USE_TIME_WINDOW

logger = logging.getLogger(__name__)

class ScraperEngine:
    """Main scraper engine with hash-based deduplication logic."""
    
    def __init__(self, db_manager: DatabaseManager, url_manager: URLManager, 
                 time_window_hours: int = None):
        """Initialize the scraper engine.
        
        Args:
            db_manager: Database manager instance
            url_manager: URL manager instance
            time_window_hours: Hours after which a URL should be re-scraped (default: from config)
        """
        self.db_manager = db_manager
        self.url_manager = url_manager
        self.time_window_hours = time_window_hours or DEDUP_TIME_WINDOW_HOURS
        
        # Initialize scraper components
        self.finviz_scraper = FinvizScraper()
        self.pagination_handler = PaginationHandler(self.finviz_scraper)
    
    def scrape_url(self, url_name: str, force_scrape: bool = False) -> Dict[str, Any]:
        """Scrape a URL with hash-based deduplication logic.
        
        Args:
            url_name: Name of the URL to scrape
            force_scrape: If True, bypass deduplication rules
            
        Returns:
            Dictionary with scraping results and metadata
        """
        # Get URL data
        url_data = self.url_manager.get_url_by_name(url_name)
        if not url_data:
            raise ValueError(f"URL '{url_name}' not found")
        
        url_id = url_data['id']
        url = url_data['url']
        
        logger.info(f"Starting scrape for URL '{url_name}' (ID: {url_id})")
        
        # Check deduplication rules (unless force_scrape is True)
        if not force_scrape:
            dedup_result = self._check_deduplication_rules(url_id, url)
            if dedup_result['should_skip']:
                logger.info(f"Skipping scrape for '{url_name}': {dedup_result['reason']}")
                # Log the skip if enabled
                if DEDUP_LOG_SKIPS:
                    self.db_manager.log_scrape_session(
                        url_id, 'skipped', 0, None, dedup_result.get('content_hash'), dedup_result['reason']
                    )
                return {
                    'url_name': url_name,
                    'url_id': url_id,
                    'tickers': [],
                    'status': 'skipped',
                    'reason': dedup_result['reason'],
                    'last_scrape': dedup_result.get('last_scrape'),
                    'content_hash': dedup_result.get('content_hash')
                }
        
        # Perform actual scraping
        try:
            # Get page content and calculate hash
            response = self.finviz_scraper._make_request(url)
            if not response:
                raise Exception("Failed to fetch URL")
            
            content_hash = self._calculate_content_hash(response.content)
            
            # Check if content has changed (even with force_scrape, we want to log the hash)
            if not force_scrape and DEDUP_ENABLE_CONTENT_HASH:
                existing_session = self.db_manager.get_scrape_session_by_hash(url_id, content_hash)
                if existing_session:
                    logger.info(f"Content unchanged for '{url_name}', skipping processing")
                    # Log the skip if enabled
                    if DEDUP_LOG_SKIPS:
                        self.db_manager.log_scrape_session(
                            url_id, 'skipped', 0, None, content_hash, 
                            f"skipped: content unchanged (hash: {content_hash[:8]}...)"
                        )
                    return {
                        'url_name': url_name,
                        'url_id': url_id,
                        'tickers': [],
                        'status': 'skipped',
                        'reason': f"Content unchanged (hash: {content_hash[:8]}...)",
                        'content_hash': content_hash
                    }
            
            # Parse content and extract tickers
            soup = BeautifulSoup(response.content, 'html.parser')
            tickers = self.pagination_handler.scrape_all_pages(url)
            
            # Log successful scrape
            self.db_manager.log_scrape_session(
                url_id, 'completed', len(tickers), None, content_hash, None
            )
            
            logger.info(f"Successfully scraped {len(tickers)} tickers from '{url_name}'")
            
            return {
                'url_name': url_name,
                'url_id': url_id,
                'tickers': tickers,
                'status': 'completed',
                'reason': None,
                'content_hash': content_hash,
                'ticker_count': len(tickers)
            }
            
        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            logger.error(f"Error scraping '{url_name}': {error_msg}")
            
            # Log failed scrape
            self.db_manager.log_scrape_session(
                url_id, 'failed', 0, error_msg, None, None
            )
            
            raise Exception(error_msg)
    
    def _check_deduplication_rules(self, url_id: int, url: str) -> Dict[str, Any]:
        """Check if scraping should be skipped based on hash-based deduplication rules.
        
        Args:
            url_id: Database ID of the URL
            url: The actual URL string
            
        Returns:
            Dictionary with deduplication decision and metadata
        """
        # Get last scrape info
        last_scrape = self.db_manager.get_last_scrape_info(url_id)
        
        if not last_scrape:
            logger.debug(f"No previous scrape found for URL ID {url_id}")
            return {'should_skip': False, 'reason': None}
        
        # Primary deduplication: Hash-based checking
        if DEDUP_ENABLE_CONTENT_HASH and last_scrape.get('content_hash'):
            # We'll check the hash after fetching the content to compare
            # This is handled in the main scrape_url method
            logger.debug(f"Hash-based deduplication enabled, will check content hash")
            return {'should_skip': False, 'reason': None, 'last_scrape': last_scrape}
        
        # Secondary deduplication: Time-based checking (only if hash checking is disabled)
        if DEDUP_USE_TIME_WINDOW:
            last_timestamp = datetime.fromisoformat(last_scrape['timestamp'].replace('Z', '+00:00'))
            time_diff = datetime.now(last_timestamp.tzinfo) - last_timestamp
            
            if time_diff < timedelta(hours=self.time_window_hours):
                logger.debug(f"Last scrape was {time_diff} ago, within {self.time_window_hours}h window")
                return {
                    'should_skip': True,
                    'reason': f"Last scraped {time_diff} ago (within {self.time_window_hours}h window)",
                    'last_scrape': last_scrape,
                    'content_hash': last_scrape.get('content_hash')
                }
        
        logger.debug(f"Deduplication checks passed, proceeding with scrape")
        return {'should_skip': False, 'reason': None, 'last_scrape': last_scrape}
    
    def _calculate_content_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of content for change detection.
        
        Args:
            content: Raw HTML content
            
        Returns:
            SHA256 hash string
        """
        return hashlib.sha256(content).hexdigest()
    
    def get_scrape_stats(self, url_name: str) -> Dict[str, Any]:
        """Get scraping statistics for a URL.
        
        Args:
            url_name: Name of the URL
            
        Returns:
            Dictionary with scraping statistics
        """
        url_data = self.url_manager.get_url_by_name(url_name)
        if not url_data:
            return {}
        
        url_id = url_data['id']
        sessions = self.db_manager.get_scrape_sessions_by_url(url_id, limit=50)
        
        stats = {
            'url_name': url_name,
            'url_id': url_id,
            'total_sessions': len(sessions),
            'completed_sessions': len([s for s in sessions if s['status'] == 'completed']),
            'failed_sessions': len([s for s in sessions if s['status'] == 'failed']),
            'skipped_sessions': len([s for s in sessions if s['status'] == 'skipped']),
            'recent_sessions': sessions[:10],
            'last_scrape': sessions[0] if sessions else None
        }
        
        return stats
    
    def validate_finviz_url(self, url: str) -> bool:
        """Validate if a URL is a valid Finviz URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid Finviz URL, False otherwise
        """
        return self.finviz_scraper.validate_url(url) 
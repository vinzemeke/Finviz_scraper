"""
Tests for hash-based deduplication functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import hashlib

from src.scraper.scraper_engine import ScraperEngine
from src.database.database_manager import DatabaseManager
from src.storage.url_manager import URLManager


class TestHashBasedDeduplication(unittest.TestCase):
    """Test hash-based deduplication functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db_manager = Mock(spec=DatabaseManager)
        self.url_manager = Mock(spec=URLManager)
        
        # Mock the scraper components that are created in ScraperEngine.__init__
        with patch('src.scraper.scraper_engine.FinvizScraper') as mock_scraper_class, \
             patch('src.scraper.scraper_engine.PaginationHandler') as mock_pagination_class:
            
            self.mock_scraper = Mock()
            mock_scraper_class.return_value = self.mock_scraper
            
            self.mock_pagination = Mock()
            mock_pagination_class.return_value = self.mock_pagination
            
            self.scraper_engine = ScraperEngine(self.db_manager, self.url_manager)
        
        # Mock URL data
        self.url_data = {
            'id': 1,
            'name': 'Test URL',
            'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300'
        }
        
        # Mock response content
        self.test_content = b"<html><body><table><tr><td>AAPL</td></tr></table></body></html>"
        self.test_hash = hashlib.sha256(self.test_content).hexdigest()
    
    def test_hash_based_deduplication_primary(self):
        """Test that hash-based checking is the primary deduplication method."""
        # Mock URL manager
        self.url_manager.get_url_by_name.return_value = self.url_data
        
        # Mock last scrape with content hash
        last_scrape = {
            'session_id': 1,
            'timestamp': '2024-01-15T10:00:00',
            'content_hash': self.test_hash,
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Mock existing session with same hash
        existing_session = {
            'session_id': 1,
            'timestamp': '2024-01-15T10:00:00',
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_scrape_session_by_hash.return_value = existing_session
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = self.test_content
        self.mock_scraper._make_request.return_value = mock_response
        
        # Test scraping with hash-based deduplication
        result = self.scraper_engine.scrape_url('Test URL', force_scrape=False)
        
        # Should skip due to unchanged content
        self.assertEqual(result['status'], 'skipped')
        self.assertIn('Content unchanged', result['reason'])
        self.assertEqual(result['content_hash'], self.test_hash)
    
    def test_hash_based_deduplication_content_changed(self):
        """Test that scraping proceeds when content has changed."""
        # Mock URL manager
        self.url_manager.get_url_by_name.return_value = self.url_data
        
        # Mock last scrape with different content hash
        last_scrape = {
            'session_id': 1,
            'timestamp': '2024-01-15T10:00:00',
            'content_hash': 'different_hash_123',
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Mock no existing session with new hash
        self.db_manager.get_scrape_session_by_hash.return_value = None
        
        # Mock HTTP response with new content
        mock_response = Mock()
        mock_response.content = self.test_content
        self.mock_scraper._make_request.return_value = mock_response
        
        # Mock pagination to return expected tickers
        self.mock_pagination.scrape_all_pages.return_value = ['AAPL', 'GOOGL']
        
        # Test scraping with changed content
        result = self.scraper_engine.scrape_url('Test URL', force_scrape=False)
        
        # Should proceed with scraping
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['tickers'], ['AAPL', 'GOOGL'])
        self.assertEqual(result['content_hash'], self.test_hash)
    
    @patch('config.settings.DEDUP_ENABLE_CONTENT_HASH', False)
    @patch('config.settings.DEDUP_USE_TIME_WINDOW', True)
    def test_time_based_fallback_when_hash_disabled(self):
        """Test time-based fallback when hash checking is disabled."""
        # Mock URL manager
        self.url_manager.get_url_by_name.return_value = self.url_data
        
        # Mock last scrape without content hash (within time window)
        last_scrape = {
            'session_id': 1,
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'content_hash': None,
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Test scraping with time-based fallback
        result = self.scraper_engine.scrape_url('Test URL', force_scrape=False)
        
        # Should skip due to time window
        self.assertEqual(result['status'], 'skipped')
        self.assertIn('within', result['reason'])
    
    def test_force_scrape_bypasses_deduplication(self):
        """Test that force scrape bypasses all deduplication rules."""
        # Mock URL manager
        self.url_manager.get_url_by_name.return_value = self.url_data
        
        # Mock last scrape with content hash
        last_scrape = {
            'session_id': 1,
            'timestamp': '2024-01-15T10:00:00',
            'content_hash': self.test_hash,
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Mock existing session with same hash
        existing_session = {
            'session_id': 1,
            'timestamp': '2024-01-15T10:00:00',
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_scrape_session_by_hash.return_value = existing_session
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = self.test_content
        self.mock_scraper._make_request.return_value = mock_response
        
        # Mock pagination to return expected tickers
        self.mock_pagination.scrape_all_pages.return_value = ['AAPL', 'GOOGL']
        
        # Test force scraping
        result = self.scraper_engine.scrape_url('Test URL', force_scrape=True)
        
        # Should proceed with scraping despite unchanged content
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['tickers'], ['AAPL', 'GOOGL'])
        self.assertEqual(result['content_hash'], self.test_hash)
    
    def test_no_previous_scrape_proceeds(self):
        """Test that scraping proceeds when no previous scrape exists."""
        # Mock URL manager
        self.url_manager.get_url_by_name.return_value = self.url_data
        
        # Mock no previous scrape
        self.db_manager.get_last_scrape_info.return_value = None
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = self.test_content
        self.mock_scraper._make_request.return_value = mock_response
        
        # Mock pagination to return expected tickers
        self.mock_pagination.scrape_all_pages.return_value = ['AAPL', 'GOOGL']
        
        # Test scraping with no previous history
        result = self.scraper_engine.scrape_url('Test URL', force_scrape=False)
        
        # Should proceed with scraping
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['tickers'], ['AAPL', 'GOOGL'])
        self.assertEqual(result['content_hash'], self.test_hash)
    
    def test_content_hash_calculation(self):
        """Test that content hash is calculated correctly."""
        # Test hash calculation
        content = b"<html><body><table><tr><td>AAPL</td></tr></table></body></html>"
        expected_hash = hashlib.sha256(content).hexdigest()
        
        calculated_hash = self.scraper_engine._calculate_content_hash(content)
        self.assertEqual(calculated_hash, expected_hash)
    
    @patch('config.settings.DEDUP_ENABLE_CONTENT_HASH', True)
    @patch('config.settings.DEDUP_USE_TIME_WINDOW', False)
    def test_deduplication_hash_enabled_time_disabled(self):
        """Test deduplication when hash is enabled and time window is disabled."""
        # Mock last scrape without content hash
        last_scrape = {
            'session_id': 1,
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'content_hash': None,  # No hash available
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Should proceed since no hash available and time window disabled
        result = self.scraper_engine._check_deduplication_rules(1, 'https://test.com')
        self.assertFalse(result['should_skip'])
    
    @patch('config.settings.DEDUP_ENABLE_CONTENT_HASH', False)
    @patch('config.settings.DEDUP_USE_TIME_WINDOW', True)
    def test_deduplication_hash_disabled_time_enabled(self):
        """Test deduplication when hash is disabled and time window is enabled."""
        # Mock last scrape without content hash (within time window)
        last_scrape = {
            'session_id': 1,
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'content_hash': None,
            'status': 'completed',
            'dedup_reason': None
        }
        self.db_manager.get_last_scrape_info.return_value = last_scrape
        
        # Should skip due to time window
        result = self.scraper_engine._check_deduplication_rules(1, 'https://test.com')
        self.assertTrue(result['should_skip'])


if __name__ == '__main__':
    unittest.main() 
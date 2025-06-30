"""
Tests for ScraperEngine with deduplication logic.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os

from src.scraper.scraper_engine import ScraperEngine
from src.database.database_manager import DatabaseManager
from src.storage.url_manager import URLManager

class TestScraperEngine:
    """Test cases for ScraperEngine with deduplication."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance with temporary database."""
        return DatabaseManager(temp_db_path)
    
    @pytest.fixture
    def url_manager(self, db_manager):
        """Create a URLManager instance."""
        return URLManager(db_manager)
    
    @pytest.fixture
    def scraper_engine(self, db_manager, url_manager):
        """Create a ScraperEngine instance."""
        return ScraperEngine(db_manager, url_manager, time_window_hours=24)
    
    def test_init_with_default_time_window(self, db_manager, url_manager):
        """Test initialization with default time window."""
        engine = ScraperEngine(db_manager, url_manager)
        assert engine.time_window_hours == 24
    
    def test_init_with_custom_time_window(self, db_manager, url_manager):
        """Test initialization with custom time window."""
        engine = ScraperEngine(db_manager, url_manager, time_window_hours=12)
        assert engine.time_window_hours == 12
    
    def test_validate_finviz_url_delegation(self, scraper_engine):
        """Test that validate_finviz_url delegates to FinvizScraper."""
        valid_url = "https://finviz.com/screener.ashx?v=111&f=cap_large"
        assert scraper_engine.validate_finviz_url(valid_url) is True
        
        invalid_url = "https://google.com"
        assert scraper_engine.validate_finviz_url(invalid_url) is False
    
    def test_scrape_url_not_found(self, scraper_engine):
        """Test scraping a URL that doesn't exist."""
        with pytest.raises(ValueError, match="URL 'nonexistent' not found"):
            scraper_engine.scrape_url("nonexistent")
    
    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_scrape_url_first_time(self, mock_session, scraper_engine, url_manager):
        """Test scraping a URL for the first time (no deduplication)."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        
        # Mock HTML content
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>
                <a href="quote.ashx?t=GOOGL&ty=c&p=d&b=1">GOOGL</a>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Mock the pagination handler to return expected tickers
        with patch.object(scraper_engine.pagination_handler, 'scrape_all_pages') as mock_paginate:
            mock_paginate.return_value = ['AAPL', 'GOOGL']
            
            # Scrape
            result = scraper_engine.scrape_url("test_url")
            
            assert result['status'] == 'completed'
            assert result['tickers'] == ['AAPL', 'GOOGL']
            assert result['ticker_count'] == 2
            assert result['content_hash'] is not None
            assert result['reason'] is None
    
    def test_scrape_url_within_time_window(self, scraper_engine, url_manager, db_manager):
        """Test that scraping is skipped if within time window."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        url_data = url_manager.get_url_by_name("test_url")
        url_id = url_data['id']
        
        # Log a recent scrape (within time window)
        db_manager.log_scrape_session(
            url_id, 'completed', 5, None, 'test_hash', None
        )
        
        # Try to scrape again
        result = scraper_engine.scrape_url("test_url")
        
        assert result['status'] == 'skipped'
        assert 'within 24h window' in result['reason']
        assert result['tickers'] == []
        assert result['last_scrape'] is not None
    
    def test_scrape_url_outside_time_window(self, scraper_engine, url_manager, db_manager):
        """Test that scraping proceeds if outside time window."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        url_data = url_manager.get_url_by_name("test_url")
        url_id = url_data['id']
        
        # Log an old scrape (outside time window)
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        db_manager.execute_update(
            "INSERT INTO scraping_sessions (url_id, timestamp, status, content_hash) VALUES (?, ?, ?, ?)",
            (url_id, old_timestamp, 'completed', 'old_hash')
        )
        
        # Mock the scraping process
        with patch.object(scraper_engine.finviz_scraper, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = b'<html><body><a href="quote.ashx?t=AAPL">AAPL</a></body></html>'
            mock_request.return_value = mock_response
            
            with patch.object(scraper_engine.pagination_handler, 'scrape_all_pages') as mock_paginate:
                mock_paginate.return_value = ['AAPL']
                
                # Try to scrape again
                result = scraper_engine.scrape_url("test_url")
                
                assert result['status'] == 'completed'
                assert result['tickers'] == ['AAPL']
    
    def test_scrape_url_content_unchanged(self, scraper_engine, url_manager, db_manager):
        """Test that scraping is skipped if content hash is unchanged."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        url_data = url_manager.get_url_by_name("test_url")
        url_id = url_data['id']
        
        # Log an old scrape with a specific hash
        old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
        content_hash = "test_hash_123"
        db_manager.execute_update(
            "INSERT INTO scraping_sessions (url_id, timestamp, status, content_hash) VALUES (?, ?, ?, ?)",
            (url_id, old_timestamp, 'completed', content_hash)
        )
        
        # Mock the scraping process to return the same hash
        with patch.object(scraper_engine.finviz_scraper, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = b'<html><body>same content</body></html>'
            mock_request.return_value = mock_response
            
            # Mock the hash calculation to return the same hash
            with patch.object(scraper_engine, '_calculate_content_hash') as mock_hash:
                mock_hash.return_value = content_hash
                
                # Try to scrape again
                result = scraper_engine.scrape_url("test_url")
                
                assert result['status'] == 'skipped'
                assert 'Content unchanged' in result['reason']
                assert result['tickers'] == []
    
    def test_force_scrape_bypasses_deduplication(self, scraper_engine, url_manager, db_manager):
        """Test that force_scrape bypasses deduplication rules."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        url_data = url_manager.get_url_by_name("test_url")
        url_id = url_data['id']
        
        # Log a recent scrape (within time window)
        db_manager.log_scrape_session(
            url_id, 'completed', 5, None, 'test_hash', None
        )
        
        # Mock the scraping process
        with patch.object(scraper_engine.finviz_scraper, '_make_request') as mock_request:
            mock_response = Mock()
            mock_response.content = b'<html><body><a href="quote.ashx?t=AAPL">AAPL</a></body></html>'
            mock_request.return_value = mock_response
            
            with patch.object(scraper_engine.pagination_handler, 'scrape_all_pages') as mock_paginate:
                mock_paginate.return_value = ['AAPL']
                
                # Try to scrape again with force_scrape=True
                result = scraper_engine.scrape_url("test_url", force_scrape=True)
                
                assert result['status'] == 'completed'
                assert result['tickers'] == ['AAPL']
    
    def test_calculate_content_hash(self, scraper_engine):
        """Test content hash calculation."""
        content = b"test content"
        hash1 = scraper_engine._calculate_content_hash(content)
        hash2 = scraper_engine._calculate_content_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
        
        # Different content should have different hash
        different_content = b"different content"
        hash3 = scraper_engine._calculate_content_hash(different_content)
        assert hash1 != hash3
    
    def test_get_scrape_stats(self, scraper_engine, url_manager, db_manager):
        """Test getting scraping statistics."""
        # Add a URL
        url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
        url_data = url_manager.get_url_by_name("test_url")
        url_id = url_data['id']
        
        # Log some sessions
        db_manager.log_scrape_session(url_id, 'completed', 5, None, 'hash1', None)
        db_manager.log_scrape_session(url_id, 'failed', 0, 'error', None, None)
        db_manager.log_scrape_session(url_id, 'skipped', 0, None, 'hash2', 'reason')
        
        # Get stats
        stats = scraper_engine.get_scrape_stats("test_url")
        
        assert stats['total_sessions'] == 3
        assert stats['completed_sessions'] == 1
        assert stats['failed_sessions'] == 1
        assert stats['skipped_sessions'] == 1
        assert stats['last_scrape'] is not None
        assert len(stats['recent_sessions']) <= 5
    
    def test_get_scrape_stats_nonexistent_url(self, scraper_engine):
        """Test getting stats for non-existent URL."""
        stats = scraper_engine.get_scrape_stats("nonexistent")
        assert stats == {}
    
    def test_configuration_time_window(self, db_manager, url_manager):
        """Test that ScraperEngine uses configuration time window."""
        # Test with custom time window
        engine = ScraperEngine(db_manager, url_manager, time_window_hours=12)
        assert engine.time_window_hours == 12
        
        # Test with default (from config)
        engine = ScraperEngine(db_manager, url_manager)
        assert engine.time_window_hours == 24  # Default from config
    
    def test_content_hash_disabled(self, db_manager, url_manager):
        """Test that content hash checking can be disabled via config."""
        # Create engine with content hash disabled
        with patch('src.scraper.scraper_engine.DEDUP_ENABLE_CONTENT_HASH', False):
            engine = ScraperEngine(db_manager, url_manager)
            
            # Add a URL
            url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
            url_data = url_manager.get_url_by_name("test_url")
            url_id = url_data['id']
            
            # Log an old scrape with a specific hash
            old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
            content_hash = "test_hash_123"
            db_manager.execute_update(
                "INSERT INTO scraping_sessions (url_id, timestamp, status, content_hash) VALUES (?, ?, ?, ?)",
                (url_id, old_timestamp, 'completed', content_hash)
            )
            
            # Mock the scraping process to return the same hash
            with patch.object(engine.finviz_scraper, '_make_request') as mock_request:
                mock_response = Mock()
                mock_response.content = b'<html><body>same content</body></html>'
                mock_request.return_value = mock_response
                
                # Mock the hash calculation to return the same hash
                with patch.object(engine, '_calculate_content_hash') as mock_hash:
                    mock_hash.return_value = content_hash
                    
                    # Mock pagination to return some tickers
                    with patch.object(engine.pagination_handler, 'scrape_all_pages') as mock_paginate:
                        mock_paginate.return_value = ['AAPL']
                        
                        # Try to scrape again - should proceed even with same hash
                        result = engine.scrape_url("test_url")
                        
                        assert result['status'] == 'completed'
                        assert result['tickers'] == ['AAPL']
    
    def test_skip_logging_disabled(self, db_manager, url_manager):
        """Test that skip logging can be disabled via config."""
        # Create engine with skip logging disabled
        with patch('src.scraper.scraper_engine.DEDUP_LOG_SKIPS', False):
            engine = ScraperEngine(db_manager, url_manager)
            
            # Add a URL
            url_manager.save_url("test_url", "https://finviz.com/screener.ashx?v=111")
            url_data = url_manager.get_url_by_name("test_url")
            url_id = url_data['id']
            
            # Log a recent scrape (within time window)
            db_manager.log_scrape_session(
                url_id, 'completed', 5, None, 'test_hash', None
            )
            
            # Try to scrape again - should skip but not log
            result = engine.scrape_url("test_url")
            
            assert result['status'] == 'skipped'
            
            # Check that no additional skip session was logged
            sessions = db_manager.get_scrape_sessions_by_url(url_id)
            assert len(sessions) == 1  # Only the original completed session 
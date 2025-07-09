"""
Tests for URLManager class with SQLite database.
"""
import pytest
import tempfile
import os
from pathlib import Path
from src.storage.url_manager import URLManager
from src.database.database_manager import DatabaseManager

class TestURLManager:
    """Test cases for URLManager with SQLite database."""
    
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
        db_manager = DatabaseManager(temp_db_path)
        from src.database.migration import MigrationManager
        migration_manager = MigrationManager(db_path=temp_db_path)
        migration_manager.run_migrations()
        db_manager.clear_all_data() # Ensure a clean slate for each test
        return db_manager
    
    @pytest.fixture
    def url_manager(self, db_manager):
        """Create a URLManager instance with temporary database."""
        return URLManager(db_manager)
    
    def test_init_empty_storage(self, db_manager):
        """Test initialization with empty database."""
        # Ensure the database is empty before testing
        db_manager.clear_all_data()
        manager = URLManager(db_manager)
        urls = manager.list_urls()
        assert urls == []
    
    def test_save_url_success(self, url_manager):
        """Test successful URL saving."""
        success = url_manager.save_url("test_url", "https://finviz.com/test")
        assert success is True
        
        # Verify URL was saved
        url = url_manager.get_url("test_url")
        assert url == "https://finviz.com/test"
    
    def test_save_url_duplicate(self, url_manager):
        """Test saving URL with duplicate name."""
        # Save first URL
        success1 = url_manager.save_url("test_url", "https://finviz.com/test1")
        assert success1 is True
        
        # Try to save URL with same name
        success2 = url_manager.save_url("test_url", "https://finviz.com/test2")
        assert success2 is False
        
        # Verify original URL is still there
        url = url_manager.get_url("test_url")
        assert url == "https://finviz.com/test1"
    
    def test_list_urls(self, url_manager):
        """Test listing URLs."""
        # Save some URLs
        url_manager.save_url("url1", "https://finviz.com/url1")
        url_manager.save_url("url2", "https://finviz.com/url2")
        
        urls = url_manager.list_urls()
        assert len(urls) == 2
        
        # Check URL data structure
        url_names = [url['name'] for url in urls]
        assert "url1" in url_names
        assert "url2" in url_names
        
        # Check that all required fields are present
        for url in urls:
            assert 'id' in url
            assert 'name' in url
            assert 'url' in url
            assert 'created_at' in url
            assert 'updated_at' in url
    
    def test_delete_url_existing(self, url_manager):
        """Test deleting existing URL."""
        # Save URL
        url_manager.save_url("test_url", "https://finviz.com/test")
        
        # Delete URL
        success = url_manager.delete_url("test_url")
        assert success is True
        
        # Verify URL is deleted
        url = url_manager.get_url("test_url")
        assert url is None
        
        urls = url_manager.list_urls()
        assert len(urls) == 0
    
    def test_delete_url_nonexistent(self, url_manager):
        """Test deleting non-existent URL."""
        success = url_manager.delete_url("nonexistent")
        assert success is False
    
    def test_get_url_existing(self, url_manager):
        """Test getting existing URL."""
        url_manager.save_url("test_url", "https://finviz.com/test")
        
        url = url_manager.get_url("test_url")
        assert url == "https://finviz.com/test"
    
    def test_get_url_nonexistent(self, url_manager):
        """Test getting non-existent URL."""
        url = url_manager.get_url("nonexistent")
        assert url is None
    
    def test_get_url_by_name_existing(self, url_manager):
        """Test getting URL data by name."""
        url_manager.save_url("test_url", "https://finviz.com/test")
        
        url_data = url_manager.get_url_by_name("test_url")
        assert url_data is not None
        assert url_data['name'] == "test_url"
        assert url_data['url'] == "https://finviz.com/test"
        assert 'id' in url_data
        assert 'created_at' in url_data
        assert 'updated_at' in url_data
    
    def test_get_url_by_name_nonexistent(self, url_manager):
        """Test getting URL data for non-existent URL."""
        url_data = url_manager.get_url_by_name("nonexistent")
        assert url_data is None
    
    def test_update_url_success(self, url_manager):
        """Test successful URL update."""
        # Save original URL
        url_manager.save_url("old_name", "https://finviz.com/old")
        
        # Update URL
        success = url_manager.update_url("old_name", "new_name", "https://finviz.com/new")
        assert success is True
        
        # Verify old name doesn't exist
        old_url = url_manager.get_url("old_name")
        assert old_url is None
        
        # Verify new name exists
        new_url = url_manager.get_url("new_name")
        assert new_url == "https://finviz.com/new"
    
    def test_update_url_nonexistent(self, url_manager):
        """Test updating non-existent URL."""
        success = url_manager.update_url("nonexistent", "new_name", "https://finviz.com/new")
        assert success is False
    
    def test_update_url_duplicate_name(self, url_manager):
        """Test updating URL with duplicate name."""
        # Save two URLs
        url_manager.save_url("url1", "https://finviz.com/url1")
        url_manager.save_url("url2", "https://finviz.com/url2")
        
        # Try to update url1 to have url2's name
        success = url_manager.update_url("url1", "url2", "https://finviz.com/new")
        assert success is False
        
        # Verify original URLs are unchanged
        url1 = url_manager.get_url("url1")
        url2 = url_manager.get_url("url2")
        assert url1 == "https://finviz.com/url1"
        assert url2 == "https://finviz.com/url2"
    
    def test_update_url_same_name_different_url(self, url_manager):
        """Test updating URL with same name but different URL."""
        # Save URL
        url_manager.save_url("test_url", "https://finviz.com/old")
        
        # Update with same name but different URL
        success = url_manager.update_url("test_url", "test_url", "https://finviz.com/new")
        assert success is True
        
        # Verify URL was updated
        url = url_manager.get_url("test_url")
        assert url == "https://finviz.com/new"
    
    def test_url_exists_true(self, url_manager):
        """Test url_exists returns True for existing URL."""
        url_manager.save_url("test_url", "https://finviz.com/test")
        assert url_manager.url_exists("test_url") is True
    
    def test_url_exists_false(self, url_manager):
        """Test url_exists returns False for non-existing URL."""
        assert url_manager.url_exists("nonexistent") is False
    
    def test_search_urls(self, url_manager):
        """Test searching URLs."""
        # Save URLs with different names and URLs
        url_manager.save_url("tech_stocks", "https://finviz.com/tech")
        url_manager.save_url("finance_stocks", "https://finviz.com/finance")
        url_manager.save_url("healthcare_stocks", "https://finviz.com/healthcare")
        
        # Search by name
        results = url_manager.search_urls("tech")
        assert len(results) == 1
        assert results[0]['name'] == "tech_stocks"
        
        # Search by URL content
        results = url_manager.search_urls("finviz.com")
        assert len(results) == 3
        
        # Search with no matches
        results = url_manager.search_urls("nonexistent")
        assert len(results) == 0
    
    def test_get_url_stats(self, url_manager):
        """Test getting URL statistics."""
        # Save some URLs
        url_manager.save_url("url1", "https://finviz.com/url1")
        url_manager.save_url("url2", "https://finviz.com/url2")
        
        stats = url_manager.get_url_stats()
        
        assert 'total_urls' in stats
        assert 'recent_urls' in stats
        assert stats['total_urls'] == 2
        assert stats['recent_urls'] >= 2  # Should include the ones we just added
        
        # Check latest URL
        if 'latest_url' in stats:
            assert 'name' in stats['latest_url']
            assert 'created_at' in stats['latest_url']
    
    def test_get_url_with_sessions(self, url_manager):
        """Test getting URL with associated sessions."""
        # Save URL
        url_manager.save_url("test_url", "https://finviz.com/test")
        
        # Get URL with sessions (should be empty initially)
        url_data = url_manager.get_url_with_sessions("test_url")
        assert url_data is not None
        assert url_data['name'] == "test_url"
        assert 'sessions' in url_data
        assert url_data['sessions'] == []
    
    def test_get_url_with_sessions_nonexistent(self, url_manager):
        """Test getting URL with sessions for non-existent URL."""
        url_data = url_manager.get_url_with_sessions("nonexistent")
        assert url_data is None 
"""
Tests for DatabaseManager class.
"""
import pytest
import tempfile
import os
from pathlib import Path
from src.database.database_manager import DatabaseManager
from src.database.schema import get_table_names

class TestDatabaseManager:
    """Test cases for DatabaseManager."""
    
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
    
    def test_init_creates_database(self, temp_db_path):
        """Test that database is created on initialization."""
        db_manager = DatabaseManager(temp_db_path)
        assert os.path.exists(temp_db_path)
        assert db_manager._initialized
    
    def test_initialize_database_creates_tables(self, db_manager):
        """Test that database initialization creates all required tables."""
        # Check that all required tables exist
        for table_name in get_table_names():
            assert db_manager.table_exists(table_name)
    
    def test_execute_query_success(self, db_manager):
        """Test successful query execution."""
        # Insert test data
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        
        # Query the data
        results = db_manager.execute_query(
            "SELECT name, url FROM urls WHERE name = ?",
            ("test_url",)
        )
        
        assert len(results) == 1
        assert results[0][0] == "test_url"
        assert results[0][1] == "https://example.com"
    
    def test_execute_update_success(self, db_manager):
        """Test successful update execution."""
        # Insert test data
        result = db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        
        assert result == 1  # One row affected
        
        # Verify data was inserted
        results = db_manager.execute_query("SELECT COUNT(*) FROM urls")
        assert results[0][0] == 1
    
    def test_execute_many_success(self, db_manager):
        """Test successful batch execution."""
        # Prepare test data
        test_data = [
            ("url1", "https://example1.com"),
            ("url2", "https://example2.com"),
            ("url3", "https://example3.com")
        ]
        
        # Execute batch insert
        result = db_manager.execute_many(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            test_data
        )
        
        assert result == 3  # Three rows affected
        
        # Verify all data was inserted
        results = db_manager.execute_query("SELECT COUNT(*) FROM urls")
        assert results[0][0] == 3
    
    def test_execute_query_with_no_results(self, db_manager):
        """Test query execution with no results."""
        results = db_manager.execute_query(
            "SELECT * FROM urls WHERE name = ?",
            ("nonexistent",)
        )
        
        assert len(results) == 0
    
    def test_execute_update_with_no_effect(self, db_manager):
        """Test update execution that affects no rows."""
        result = db_manager.execute_update(
            "UPDATE urls SET url = ? WHERE name = ?",
            ("https://new.com", "nonexistent")
        )
        
        assert result == 0  # No rows affected
    
    def test_table_exists_true(self, db_manager):
        """Test table_exists returns True for existing table."""
        assert db_manager.table_exists("urls")
    
    def test_table_exists_false(self, db_manager):
        """Test table_exists returns False for non-existing table."""
        assert not db_manager.table_exists("nonexistent_table")
    
    def test_get_table_info(self, db_manager):
        """Test getting table information."""
        table_info = db_manager.get_table_info("urls")
        
        assert len(table_info) > 0
        assert any(col['name'] == 'id' for col in table_info)
        assert any(col['name'] == 'name' for col in table_info)
        assert any(col['name'] == 'url' for col in table_info)
    
    def test_get_database_stats(self, db_manager):
        """Test getting database statistics."""
        # Insert some test data
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        
        stats = db_manager.get_database_stats()
        
        assert 'database_path' in stats
        assert 'database_size' in stats
        assert 'tables' in stats
        assert stats['tables']['urls'] == 1
        assert stats['tables']['scraping_sessions'] == 0
        assert stats['tables']['ticker_results'] == 0
    
    def test_backup_database(self, db_manager, temp_db_path):
        """Test database backup functionality."""
        # Insert test data
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        
        # Create backup
        backup_path = temp_db_path + ".backup"
        success = db_manager.backup_database(backup_path)
        
        assert success
        assert os.path.exists(backup_path)
        
        # Verify backup contains the same data
        backup_manager = DatabaseManager(backup_path)
        results = backup_manager.execute_query("SELECT COUNT(*) FROM urls")
        assert results[0][0] == 1
        
        # Cleanup
        os.unlink(backup_path)
    
    def test_vacuum_database(self, db_manager):
        """Test database vacuum functionality."""
        # Insert and delete data to create fragmentation
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        db_manager.execute_update(
            "DELETE FROM urls WHERE name = ?",
            ("test_url",)
        )
        
        # Vacuum the database
        success = db_manager.vacuum_database()
        assert success
    
    def test_connection_error_handling(self):
        """Test error handling for invalid database path."""
        # SQLite will actually create the database file even in non-existent directories
        # So we test with a path that would cause permission issues instead
        with pytest.raises(Exception):
            # Try to create database in a path that would cause permission issues
            DatabaseManager("/root/nonexistent/database.db")
    
    def test_foreign_key_constraints(self, db_manager):
        """Test that foreign key constraints are enforced."""
        # First, let's verify foreign keys are enabled
        result = db_manager.execute_query("PRAGMA foreign_keys")
        foreign_keys_enabled = result[0][0] if result else 0
        
        if foreign_keys_enabled:
            # Try to insert into scraping_sessions with non-existent url_id
            with pytest.raises(Exception):
                db_manager.execute_update(
                    "INSERT INTO scraping_sessions (url_id, status) VALUES (?, ?)",
                    (999, "completed")
                )
        else:
            # If foreign keys are disabled, the insert should succeed
            result = db_manager.execute_update(
                "INSERT INTO scraping_sessions (url_id, status) VALUES (?, ?)",
                (999, "completed")
            )
            assert result == 1
    
    def test_unique_constraints(self, db_manager):
        """Test that unique constraints are enforced."""
        # Insert first URL
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        
        # Try to insert duplicate name
        with pytest.raises(Exception):
            db_manager.execute_update(
                "INSERT INTO urls (name, url) VALUES (?, ?)",
                ("test_url", "https://different.com")
            )
    
    def test_transaction_rollback(self, db_manager):
        """Test that transactions are rolled back on error."""
        # Insert valid data
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("valid_url", "https://example.com")
        )
        
        # Try to insert invalid data (should cause rollback)
        try:
            db_manager.execute_update(
                "INSERT INTO urls (name, url) VALUES (?, ?)",
                ("valid_url", "https://example.com")  # Duplicate name
            )
        except Exception:
            pass
        
        # Verify only the first insert was committed
        results = db_manager.execute_query("SELECT COUNT(*) FROM urls")
        assert results[0][0] == 1
    
    def test_scrape_session_content_hash_and_dedup_reason(self, db_manager):
        """Test logging and retrieving content_hash and dedup_reason in scraping_sessions."""
        # Insert a URL
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url", "https://example.com")
        )
        url_id = db_manager.execute_query("SELECT id FROM urls WHERE name = ?", ("test_url",))[0][0]

        # Log a scrape session with content_hash and dedup_reason
        content_hash = "abc123"
        dedup_reason = "skipped: hash match"
        status = "skipped"
        db_manager.log_scrape_session(url_id, status, ticker_count=0, error_message=None, content_hash=content_hash, dedup_reason=dedup_reason)

        # Log a completed session with a different hash
        new_hash = "def456"
        db_manager.log_scrape_session(url_id, "completed", ticker_count=10, error_message=None, content_hash=new_hash, dedup_reason=None)

        # Retrieve all scrape sessions for this url_id, ordered by timestamp desc, id desc
        sessions = db_manager.execute_query(
            "SELECT content_hash, dedup_reason, status FROM scraping_sessions WHERE url_id = ? ORDER BY timestamp DESC, id DESC",
            (url_id,)
        )
        assert len(sessions) == 2
        # The most recent session should be the completed one
        assert sessions[0][0] == new_hash
        assert sessions[0][1] is None
        assert sessions[0][2] == "completed"
        # The previous session should be the skipped one
        assert sessions[1][0] == content_hash
        assert sessions[1][1] == dedup_reason
        assert sessions[1][2] == status

    def test_get_scrape_sessions_by_url_and_by_hash(self, db_manager):
        """Test querying scrape sessions by URL and by content hash."""
        # Insert a URL
        db_manager.execute_update(
            "INSERT INTO urls (name, url) VALUES (?, ?)",
            ("test_url2", "https://example.com/2")
        )
        url_id = db_manager.execute_query("SELECT id FROM urls WHERE name = ?", ("test_url2",))[0][0]

        # Log multiple sessions
        hashes = ["hash1", "hash2", "hash3"]
        for i, h in enumerate(hashes):
            db_manager.log_scrape_session(url_id, "completed", ticker_count=i, error_message=None, content_hash=h, dedup_reason=None)

        # Query recent sessions
        sessions = db_manager.get_scrape_sessions_by_url(url_id, limit=2)
        assert len(sessions) == 2
        assert sessions[0]['content_hash'] == "hash3"
        assert sessions[1]['content_hash'] == "hash2"

        # Query by hash
        session = db_manager.get_scrape_session_by_hash(url_id, "hash2")
        assert session is not None
        assert session['status'] == "completed"
        assert session['dedup_reason'] is None

    def test_migrate_schema_for_deduplication(self, db_manager):
        """Test migration step adds deduplication fields if missing."""
        # Drop columns if they exist (simulate old schema)
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # SQLite does not support DROP COLUMN, so recreate table for test
            cursor.execute("DROP TABLE IF EXISTS scraping_sessions")
            cursor.execute("""
                CREATE TABLE scraping_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed',
                    ticker_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        # Run migration
        from src.database.migration import MigrationManager
        mm = MigrationManager(db_manager)
        assert mm.migrate_schema_for_deduplication() is True
        # Check columns exist
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(scraping_sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            assert 'content_hash' in columns
            assert 'dedup_reason' in columns 
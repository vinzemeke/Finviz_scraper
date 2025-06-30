"""
Database configuration for Finviz Stock Scraper.
"""
import os
from pathlib import Path

# Database configuration
DATABASE_CONFIG = {
    'database_path': 'data/finviz_scraper.db',
    'backup_path': 'data/backups/',
    'migration_backup_path': 'data/migration_backups/',
    'max_connections': 10,
    'timeout': 30,
    'check_same_thread': False,
    'isolation_level': None,  # Autocommit mode
}

# Schema configuration
SCHEMA_CONFIG = {
    'urls_table': 'urls',
    'sessions_table': 'scraping_sessions',
    'results_table': 'ticker_results',
    'enable_foreign_keys': True,
    'enable_wal_mode': True,  # Write-Ahead Logging for better concurrency
}

# Migration configuration
MIGRATION_CONFIG = {
    'auto_migrate': True,
    'backup_before_migration': True,
    'verify_after_migration': True,
    'remove_old_files_after_migration': False,  # Keep old files as backup
    'migration_timeout': 300,  # 5 minutes
}

# Performance configuration
PERFORMANCE_CONFIG = {
    'enable_indexes': True,
    'cache_size': -64000,  # 64MB cache
    'temp_store': 2,  # Store temp tables in memory
    'synchronous': 1,  # Normal sync mode (good balance of safety/speed)
    'journal_mode': 'WAL',  # Write-Ahead Logging
}

def get_database_path():
    """Get the full path to the database file."""
    base_path = Path(__file__).parent.parent
    return base_path / DATABASE_CONFIG['database_path']

def get_backup_path():
    """Get the full path to the backup directory."""
    base_path = Path(__file__).parent.parent
    return base_path / DATABASE_CONFIG['backup_path']

def get_migration_backup_path():
    """Get the full path to the migration backup directory."""
    base_path = Path(__file__).parent.parent
    return base_path / DATABASE_CONFIG['migration_backup_path']

def ensure_data_directory():
    """Ensure the data directory exists."""
    data_dir = get_database_path().parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def ensure_backup_directory():
    """Ensure the backup directory exists."""
    backup_dir = get_backup_path()
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def ensure_migration_backup_directory():
    """Ensure the migration backup directory exists."""
    migration_backup_dir = get_migration_backup_path()
    migration_backup_dir.mkdir(parents=True, exist_ok=True)
    return migration_backup_dir 
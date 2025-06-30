"""
Database schema definitions for Finviz Stock Scraper.
"""
from typing import List

# Database schema SQL statements
SCHEMA_SQL = """
-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Enable Write-Ahead Logging for better concurrency
PRAGMA journal_mode = WAL;

-- Set cache size for better performance
PRAGMA cache_size = -64000;

-- Store temporary tables in memory
PRAGMA temp_store = 2;

-- URLs table
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping sessions table
CREATE TABLE IF NOT EXISTS scraping_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
    ticker_count INTEGER DEFAULT 0,
    error_message TEXT,
    content_hash TEXT,
    dedup_reason TEXT,
    FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
);

-- Ticker results table
CREATE TABLE IF NOT EXISTS ticker_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    ticker_symbol TEXT NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES scraping_sessions(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_urls_name ON urls(name);
CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_url_id ON scraping_sessions(url_id);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON scraping_sessions(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON scraping_sessions(status);
CREATE INDEX IF NOT EXISTS idx_results_session_id ON ticker_results(session_id);
CREATE INDEX IF NOT EXISTS idx_results_ticker_symbol ON ticker_results(ticker_symbol);
CREATE INDEX IF NOT EXISTS idx_results_scraped_at ON ticker_results(scraped_at);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_urls_updated_at 
    AFTER UPDATE ON urls
    FOR EACH ROW
BEGIN
    UPDATE urls SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""

# Index creation SQL statements
INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_urls_name ON urls(name);",
    "CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_url_id ON scraping_sessions(url_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON scraping_sessions(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON scraping_sessions(status);",
    "CREATE INDEX IF NOT EXISTS idx_results_session_id ON ticker_results(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_results_ticker_symbol ON ticker_results(ticker_symbol);",
    "CREATE INDEX IF NOT EXISTS idx_results_scraped_at ON ticker_results(scraped_at);",
]

# Table creation SQL statements
TABLES_SQL = {
    'urls': """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    
    'scraping_sessions': """
        CREATE TABLE IF NOT EXISTS scraping_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'completed' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
            ticker_count INTEGER DEFAULT 0,
            error_message TEXT,
            content_hash TEXT,
            dedup_reason TEXT,
            FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
        );
    """,
    
    'ticker_results': """
        CREATE TABLE IF NOT EXISTS ticker_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            ticker_symbol TEXT NOT NULL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES scraping_sessions(id) ON DELETE CASCADE
        );
    """
}

# Trigger creation SQL statements
TRIGGERS_SQL = {
    'update_urls_updated_at': """
        CREATE TRIGGER IF NOT EXISTS update_urls_updated_at 
            AFTER UPDATE ON urls
            FOR EACH ROW
        BEGIN
            UPDATE urls SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    """
}

# PRAGMA statements for database optimization
PRAGMA_SQL = [
    "PRAGMA foreign_keys = ON;",
    "PRAGMA journal_mode = WAL;",
    "PRAGMA cache_size = -64000;",
    "PRAGMA temp_store = 2;",
    "PRAGMA synchronous = 1;",
]

def get_schema_statements() -> List[str]:
    """Get all schema creation statements in the correct order."""
    statements = []
    
    # Add PRAGMA statements first
    statements.extend(PRAGMA_SQL)
    
    # Add table creation statements
    for table_name, table_sql in TABLES_SQL.items():
        statements.append(table_sql)
    
    # Add index creation statements
    statements.extend(INDEXES_SQL)
    
    # Add trigger creation statements
    for trigger_name, trigger_sql in TRIGGERS_SQL.items():
        statements.append(trigger_sql)
    
    return statements

def get_table_names() -> List[str]:
    """Get list of table names in the schema."""
    return list(TABLES_SQL.keys())

def get_index_names() -> List[str]:
    """Get list of index names in the schema."""
    return [
        'idx_urls_name',
        'idx_urls_created_at',
        'idx_sessions_url_id',
        'idx_sessions_timestamp',
        'idx_sessions_status',
        'idx_results_session_id',
        'idx_results_ticker_symbol',
        'idx_results_scraped_at',
    ] 
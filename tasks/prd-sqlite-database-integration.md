# PRD: SQLite Database Integration

## Introduction/Overview

Currently, the Finviz Stock Scraper uses file-based storage (JSON files) for managing URLs and CSV files for storing scraped ticker data. This approach has limitations in terms of data integrity, querying capabilities, and scalability. This feature will integrate SQLite as a lightweight database to provide better data management, ACID compliance, and improved performance.

## Goals

1. **Replace file-based storage** with SQLite database for URLs and ticker data
2. **Improve data integrity** with ACID compliance and proper constraints
3. **Enable better querying** capabilities for historical data analysis
4. **Maintain backward compatibility** with existing data during migration
5. **Improve performance** for large datasets and complex queries
6. **Add data relationships** between URLs and their scraped results

## User Stories

1. **As a user**, I want my URL data to be stored securely in a database so that I don't lose data due to file corruption
2. **As a user**, I want to query historical scraping results so that I can analyze trends over time
3. **As a user**, I want faster loading times when I have many saved URLs so that the application remains responsive
4. **As a developer**, I want a structured database schema so that I can easily extend the application with new features
5. **As a user**, I want my existing data to be automatically migrated so that I don't lose my saved URLs

## Functional Requirements

1. **Database Schema Design**
   - Create tables for URLs (id, name, url, created_at, updated_at)
   - Create tables for scraping sessions (id, url_id, timestamp, status)
   - Create tables for ticker results (id, session_id, ticker_symbol, scraped_at)
   - Add proper foreign key relationships and constraints

2. **Database Management**
   - Initialize database with schema on first run
   - Provide database migration from existing JSON/CSV files
   - Handle database connection and error recovery
   - Implement connection pooling for better performance

3. **URL Management Integration**
   - Update URLManager to use SQLite instead of JSON files
   - Maintain existing API interface for backward compatibility
   - Add database-specific features (search, filtering, pagination)

4. **Data Storage Integration**
   - Update DataStorage to use SQLite for ticker data
   - Maintain CSV export functionality for external tools
   - Add querying capabilities for historical data

5. **Migration System**
   - Automatically detect existing JSON/CSV files
   - Migrate data to SQLite database
   - Provide rollback capability if migration fails
   - Preserve original files as backup

6. **Performance Optimization**
   - Add database indexes for frequently queried fields
   - Implement connection pooling
   - Add query optimization for large datasets

## Non-Goals (Out of Scope)

- **Complex database features**: No need for advanced features like stored procedures or triggers
- **Multi-user support**: Single-user application, no need for user authentication or permissions
- **Real-time synchronization**: No need for real-time data sync across multiple instances
- **Advanced analytics**: Basic querying only, no complex data analysis features
- **Database administration tools**: No need for separate admin interface

## Design Considerations

### Database Schema
```sql
-- URLs table
CREATE TABLE urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping sessions table
CREATE TABLE scraping_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed',
    ticker_count INTEGER DEFAULT 0,
    FOREIGN KEY (url_id) REFERENCES urls(id)
);

-- Ticker results table
CREATE TABLE ticker_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    ticker_symbol TEXT NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES scraping_sessions(id)
);
```

### Migration Strategy
1. **Detection**: Check for existing `data/urls.json` and CSV files
2. **Backup**: Create backup copies of existing files
3. **Migration**: Import data into SQLite tables
4. **Verification**: Validate migrated data integrity
5. **Cleanup**: Optionally remove old files after successful migration

## Technical Considerations

- **SQLite**: Lightweight, serverless database perfect for single-user applications
- **SQLAlchemy**: Optional ORM for better code organization and query building
- **Connection Management**: Proper connection handling and error recovery
- **Data Validation**: Input validation and constraint enforcement
- **Backup Strategy**: Regular database backups and export functionality

## Success Metrics

1. **Data Integrity**: 100% successful migration of existing data
2. **Performance**: Faster loading times for URL lists (>50% improvement)
3. **Reliability**: Zero data loss during normal operations
4. **Compatibility**: All existing functionality works without changes
5. **Scalability**: Support for 10,000+ URLs and 100,000+ ticker records

## Open Questions

1. **ORM vs Raw SQL**: Should we use SQLAlchemy ORM or raw SQL queries?
2. **Migration Timing**: Should migration happen automatically on startup or require user confirmation?
3. **Backup Strategy**: How often should automatic backups be created?
4. **Data Retention**: Should we implement automatic cleanup of old scraping sessions?
5. **Export Format**: Should we maintain CSV export or switch to other formats? 
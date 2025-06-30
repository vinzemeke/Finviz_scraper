## Relevant Files

- `src/scraper/scraper_engine.py` - Main scraping logic; will be updated to implement deduplication rules.
- `src/database/database_manager.py` - Database logic; will be updated to store scrape history, hashes, and timestamps.
- `src/storage/data_storage.py` - Data storage logic; may be updated to support new deduplication metadata.
- `src/web/app.py` - Flask app; will be updated to support force-scrape and configuration options.
- `src/templates/` - HTML templates; may be updated for force-scrape UI.
- `src/scraper/scraper_engine.test.py` - Unit tests for scraper deduplication logic.
- `src/database/test_database_manager.py` - Unit tests for new database fields and queries.
- `src/web/test_app.py` - Integration tests for force-scrape and deduplication.

### Notes
- All new database fields should be added via migration scripts if needed.
- Tests should cover all new logic, including edge cases for skipping and force-scraping.

## Tasks

- [x] 1.0 Database & Data Model Enhancements
  - [x] 1.1 Add fields to track last scrape timestamp, content hash, and scrape status for each URL/page/ticker in the database.
  - [x] 1.2 Update database manager to support querying and updating these fields.
  - [x] 1.3 Add migration logic for existing data (if needed).
  - [x] 1.4 Add tests for new database logic.

- [x] 2.0 Scraper Engine Deduplication Logic
  - [x] 2.1 Update scraper to check last scrape timestamp before scraping.
  - [x] 2.2 Implement configurable time window for re-scraping (default: 24h).
  - [x] 2.3 Fetch and compare content hash before processing; skip if unchanged.
  - [x] 2.4 Add logic to log all scraping attempts, skips, and reasons.
  - [x] 2.5 Add tests for deduplication logic and edge cases.

- [x] 3.0 Force-Scrape & Override Support
  - [x] 3.1 Add backend support for force-scrape (bypassing deduplication rules).
  - [x] 3.2 Add UI/API option to trigger force-scrape for a URL/page/ticker.
  - [x] 3.3 Add tests for force-scrape logic.

- [x] 4.0 Configuration & Settings
  - [x] 4.1 Add support for configuring the time window (via config file or environment variable).
  - [x] 4.2 Document configuration options in README or settings file.
  - [x] 4.3 Add tests for configuration logic.

- [x] 5.0 Documentation & Success Metrics
  - [x] 5.1 Update documentation to describe deduplication rules and force-scrape.
  - [x] 5.2 Add instructions for configuring and using new features.
  - [x] 5.3 Add a section to the scrape log or stats page to show deduplication effectiveness (e.g., number of skips vs. scrapes). 
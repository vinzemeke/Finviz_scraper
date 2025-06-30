# PRD: Scraping Deduplication and Efficiency Rules

## 1. Introduction/Overview

The goal of this enhancement is to make the Finviz scraper more efficient by avoiding redundant scraping tasks. The system should intelligently skip scraping URLs/pages/tickers that have already been scraped recently or whose content has not changed, thus saving resources and reducing unnecessary load.

## 2. Goals
- Prevent redundant scraping of the same URLs/pages/tickers.
- Only re-scrape when data is stale (older than a configurable time window) or has changed.
- Maintain a log/history of scraping activity for traceability.

## 3. User Stories
- **As a user**, I want the scraper to skip URLs that have already been scraped recently, so I don't waste time and bandwidth.
- **As a user**, I want the scraper to detect if a page's content has changed before re-scraping, so I only get new data when it's actually updated.
- **As a user**, I want to be able to override these rules if I need to force a fresh scrape.

## 4. Functional Requirements
1. The system must track the last scrape timestamp for each URL/page/ticker.
2. The system must skip scraping if the last scrape was within a configurable time window (default: 24 hours).
3. The system must store a hash or snapshot of the last scraped content for each URL/page/ticker.
4. The system must compare the current page content to the last snapshot; if unchanged, skip further processing.
5. The system must allow a user to force a re-scrape, bypassing deduplication rules.
6. The system must log all scraping attempts, including skips and forced scrapes, with reasons.
7. The system must provide a way to configure the time window for re-scraping.

## 5. Non-Goals (Out of Scope)
- Distributed scraping or multi-user coordination.
- Advanced content diffing (beyond hash/snapshot comparison).
- UI for managing scraping rules (for now, configuration is via settings or code).

## 6. Design Considerations (Optional)
- Use efficient hashing (e.g., SHA256) for content change detection.
- Store scrape history and hashes in the existing SQLite database.
- Provide a simple override/force-scrape option in the UI and API.

## 7. Technical Considerations (Optional)
- Ensure backward compatibility with existing scrape logs.
- Minimize database writes by only updating on actual scrapes or content changes.
- Allow configuration of the time window via environment variable or config file.

## 8. Success Metrics
- Reduction in redundant scraping tasks (measured by scrape log).
- Accurate detection and skipping of unchanged pages.
- No loss of required data due to over-aggressive skipping.

## 9. Open Questions
- Should the time window be global or per-URL configurable?
- Should we support more granular force-scrape options (e.g., per ticker, per session)?
- How should we handle errors in hash calculation or database access? 
# Product Requirements Document: Finviz Stock Scraper

## Introduction/Overview

The Finviz Stock Scraper is a tool designed to extract ticker symbols from Finviz filtered pages. Users can save Finviz URLs with custom names (e.g., "trending stocks", "tech stocks") and scrape all ticker symbols from those pages, including handling pagination. The scraped ticker symbols will be saved for later use with the Yahoo API to pull detailed stock data.

**Problem Statement:** Manual extraction of stock ticker symbols from Finviz filtered pages is time-consuming and error-prone. Users need an automated way to scrape ticker symbols from multiple filtered Finviz pages and organize them by custom names.

**Goal:** Create an automated scraper that extracts all ticker symbols from Finviz filtered pages, handles pagination, and saves results with user-defined names for easy reference and further data processing.

## Goals

1. **Automated Extraction:** Extract all ticker symbols from Finviz filtered pages without manual intervention
2. **Pagination Support:** Handle multi-page results automatically to capture all stocks matching the filter criteria
3. **URL Management:** Allow users to save and name Finviz URLs for easy reference and repeated scraping
4. **Data Organization:** Save extracted ticker symbols with associated URL names for structured data management
5. **Reliability:** Handle common edge cases and errors gracefully

## User Stories

1. **As a stock researcher**, I want to save a Finviz URL as "trending stocks" and scrape all ticker symbols so that I can quickly get a comprehensive list of trending stocks for analysis.

2. **As a stock researcher**, I want to scrape multiple saved Finviz URLs at once so that I can efficiently gather ticker symbols from different filter criteria (e.g., "tech stocks", "small caps", "high volume").

3. **As a stock researcher**, I want the scraper to handle pagination automatically so that I don't miss any stocks that appear on subsequent pages.

4. **As a stock researcher**, I want to save the extracted ticker symbols with descriptive names so that I can easily reference them later when pulling detailed data from Yahoo API.

## Functional Requirements

1. **URL Input and Validation:** The system must accept Finviz URLs and validate that they are accessible and contain stock data.

2. **URL Naming and Storage:** The system must allow users to assign custom names to Finviz URLs and store them for future use.

3. **Ticker Symbol Extraction:** The system must extract all ticker symbols from the Finviz page, including those on subsequent pages (pagination).

4. **Pagination Handling:** The system must automatically detect and navigate through all pages of results to capture complete stock lists.

5. **Data Storage:** The system must save extracted ticker symbols with their associated URL names in a structured format (CSV file).

6. **Batch Processing:** The system must support scraping multiple saved URLs in a single operation.

7. **Error Handling:** The system must handle common errors gracefully (invalid URLs, network issues, no results found).

8. **Output Generation:** The system must generate a CSV file containing URL names and their associated ticker symbols.

## Non-Goals (Out of Scope)

1. **Real-time Data:** The scraper will not provide real-time stock data or prices
2. **Data Analysis:** The scraper will not perform any analysis on the extracted ticker symbols
3. **Yahoo API Integration:** While the output is designed for Yahoo API use, the actual API integration is out of scope
4. **Web Interface:** The scraper will be a command-line tool, not a web application
5. **Historical Data:** The scraper will not extract historical stock data from Finviz
6. **Rate Limiting Management:** Advanced rate limiting and IP rotation are out of scope for initial version

## Design Considerations

- **Command-line Interface:** Simple CLI with clear commands for saving URLs, listing saved URLs, and scraping
- **CSV Output Format:** Standard CSV format for easy integration with other tools and APIs
- **Progress Indicators:** Show progress during scraping, especially for pages with many results
- **Error Messages:** Clear, actionable error messages for common issues

## Technical Considerations

- **Programming Language:** Python (recommended for web scraping libraries like BeautifulSoup/Scrapy)
- **Dependencies:** Web scraping library, CSV handling, URL validation
- **Data Storage:** Simple file-based storage for saved URLs and scraped results
- **Robots.txt Compliance:** Respect Finviz's robots.txt and implement reasonable delays between requests
- **User Agent:** Use appropriate user agent to identify the scraper

## Success Metrics

1. **Completeness:** Successfully extract 100% of ticker symbols from Finviz filtered pages
2. **Accuracy:** Zero false positives (no non-ticker symbols in output)
3. **Reliability:** Handle pagination correctly for pages with 100+ results
4. **Usability:** Users can save and scrape URLs with minimal technical knowledge
5. **Performance:** Complete scraping of a typical Finviz page (50-100 stocks) within 30 seconds

## Open Questions

1. **Rate Limiting:** What is an acceptable delay between page requests to avoid being blocked?
2. **File Organization:** Should scraped results be organized by date, or overwrite previous results for the same URL name?
3. **URL Validation:** How strictly should we validate Finviz URLs (exact domain match vs. pattern matching)?
4. **Error Recovery:** Should the scraper retry failed requests, and if so, how many times?
5. **Output Format:** Should we include additional metadata (scrape timestamp, number of stocks found) in the output?

## Implementation Notes

- Focus on robustness over speed initially
- Implement proper error handling for network issues and page structure changes
- Consider using async/await for better performance with multiple pages
- Test with various Finviz filter combinations to ensure reliability
- Document the expected Finviz page structure for future maintenance 
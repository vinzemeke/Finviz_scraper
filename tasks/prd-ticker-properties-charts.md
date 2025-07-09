# PRD: Ticker Properties and Charts Feature

## Introduction/Overview

This feature enhances the Finviz scraper by adding detailed ticker analysis capabilities. When users scrape URLs, they will be able to view comprehensive ticker properties from Yahoo Finance and see static charts showing the weekly direction of each stock. This provides immediate insights into the scraped tickers without requiring users to visit external sites.

## Goals

1. **Enhanced Data Display**: Provide rich ticker information beyond just symbol names
2. **Visual Analysis**: Show stock performance trends through static charts
3. **Efficient Data Access**: Implement caching to minimize API calls and improve performance
4. **User-Friendly Interface**: Display data in an intuitive, clickable format
5. **Technical Indicators**: Include key moving averages for technical analysis

## User Stories

1. **As a stock analyst**, I want to see current price and market data for scraped tickers so that I can quickly assess their current market position.

2. **As a trader**, I want to view 8, 21, and 200-day EMAs for each ticker so that I can identify trend directions and potential entry/exit points.

3. **As a user**, I want to click on ticker symbols to see detailed charts so that I can visualize the stock's recent performance without leaving the application.

4. **As a frequent user**, I want the data to be cached so that I don't have to wait for repeated API calls when viewing the same tickers.

5. **As a data analyst**, I want to see volume and market cap information so that I can assess the liquidity and size of the companies.

## Functional Requirements

1. **Yahoo Finance Integration**: The system must integrate with the yfinance API to fetch real-time ticker data.

2. **Ticker Properties Display**: The system must display the following properties for each ticker:
   - Current price
   - Market cap
   - Volume
   - 8-day EMA
   - 21-day EMA
   - 200-day EMA

3. **Static Chart Generation**: The system must generate static charts showing weekly price direction for each ticker.

4. **On-Demand Data Fetching**: The system must fetch ticker data only when requested by the user, not automatically for all scraped tickers.

5. **Click-to-View Functionality**: The system must allow users to click on ticker symbols to view detailed charts and properties.

6. **Data Caching**: The system must cache ticker data to avoid repeated API calls for the same ticker within a reasonable time period.

7. **Error Handling**: The system must gracefully handle cases where Yahoo Finance data is unavailable or API calls fail.

8. **Chart Display**: The system must display charts in a modal or dedicated view when a ticker is clicked.

## Non-Goals (Out of Scope)

1. **Real-time Updates**: This feature will not provide real-time price updates; data will be fetched on-demand and cached.
2. **Interactive Charts**: Charts will be static images, not interactive JavaScript charts.
3. **Historical Data Analysis**: This feature will not provide extensive historical data analysis beyond the chart display.
4. **Trading Signals**: This feature will not provide buy/sell recommendations or trading signals.
5. **Portfolio Management**: This feature will not include portfolio tracking or management capabilities.
6. **News Integration**: This feature will not include news feeds or sentiment analysis.

## Design Considerations

1. **Modal Design**: Use a clean modal design for displaying ticker details and charts
2. **Loading States**: Show loading indicators while fetching data from Yahoo Finance
3. **Responsive Layout**: Ensure the modal and charts work well on different screen sizes
4. **Color Coding**: Use color coding to indicate price movements (green for up, red for down)
5. **Chart Styling**: Use consistent chart styling with clear labels and readable fonts

## Technical Considerations

1. **yfinance Library**: Integrate the yfinance Python library for Yahoo Finance data access
2. **Chart Generation**: Use matplotlib or similar library for generating static charts
3. **Caching Strategy**: Implement a caching mechanism with configurable TTL (Time To Live)
4. **Database Storage**: Store cached ticker data in the existing SQLite database
5. **Error Handling**: Implement robust error handling for API failures and data validation
6. **Performance**: Optimize for handling ~20 tickers per URL without significant performance impact

## Success Metrics

1. **User Engagement**: Increase in time spent viewing scraped results by 50%
2. **Data Accuracy**: 95% success rate in fetching ticker data from Yahoo Finance
3. **Performance**: Average response time under 2 seconds for cached data
4. **User Satisfaction**: Positive feedback on the enhanced data visualization capabilities
5. **Cache Efficiency**: 80% cache hit rate for repeated ticker views

## Open Questions

1. **Cache Duration**: What should be the optimal cache duration for ticker data (e.g., 15 minutes, 1 hour)?
2. **Chart Timeframe**: Should the weekly chart show 5 trading days or 7 calendar days?
3. **Data Refresh**: Should users have the ability to manually refresh data and bypass cache?
4. **Chart Size**: What should be the optimal dimensions for the static charts?
5. **Error Display**: How should we display tickers where Yahoo Finance data is unavailable?
6. **Batch Processing**: Should we implement batch API calls for multiple tickers to improve performance?

## Relevant Files

- `src/services/yahoo_finance_service.py` - Service for fetching ticker data from Yahoo Finance API
- `src/services/chart_generator.py` - Service for generating static stock charts
- `src/services/cache_manager.py` - Service for managing ticker data caching
- `src/database/database_manager.py` - Add ticker properties table and caching methods
- `src/storage/data_storage.py` - Add methods for storing and retrieving ticker properties
- `templates/ticker_details.html` - Modal template for displaying ticker details and charts
- `static/js/ticker-details.js` - JavaScript for handling ticker click events and modal display
- `static/css/ticker-details.css` - Styling for ticker details modal and charts
- `src/test_yahoo_finance_service.py` - Unit tests for Yahoo Finance service
- `src/test_chart_generator.py` - Unit tests for chart generation service
- `src/test_cache_manager.py` - Unit tests for cache management service 
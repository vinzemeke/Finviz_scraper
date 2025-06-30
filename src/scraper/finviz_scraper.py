import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import time
from config.settings import USER_AGENT, REQUEST_DELAY, TIMEOUT, MAX_RETRIES, FINVIZ_BASE_URL

class FinvizScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def validate_finviz_url(self, url: str) -> bool:
        """Validate if the URL is a valid Finviz screener URL."""
        if not url.startswith(FINVIZ_BASE_URL):
            return False
        if 'screener.ashx' not in url:
            return False
        return True

    def extract_ticker_symbols(self, url: str) -> List[str]:
        """Extract ticker symbols from a Finviz screener page."""
        if not self.validate_finviz_url(url):
            raise ValueError("Invalid Finviz URL provided")

        tickers = []
        try:
            response = self._make_request(url)
            if response is None:
                return tickers

            soup = BeautifulSoup(response.content, 'html.parser')
            tickers = self._parse_ticker_symbols(soup)
            
        except Exception as e:
            raise Exception(f"Error extracting ticker symbols: {str(e)}")

        return tickers

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                time.sleep(REQUEST_DELAY)
                return response
            except requests.RequestException as e:
                if attempt == MAX_RETRIES - 1:
                    raise Exception(f"Failed to fetch URL after {MAX_RETRIES} attempts: {str(e)}")
                time.sleep(REQUEST_DELAY * (attempt + 1))
        return None

    def _parse_ticker_symbols(self, soup: BeautifulSoup) -> List[str]:
        """Parse ticker symbols from the HTML content."""
        tickers = []
        
        # Look for ticker symbols in the screener table
        # Ticker symbols are typically in links with pattern: quote.ashx?t=TICKER
        ticker_links = soup.find_all('a', href=True)
        
        for link in ticker_links:
            href = link.get('href', '')
            if 'quote.ashx?t=' in href:
                # Extract ticker from href like "quote.ashx?t=AAPL&ty=c&p=d&b=1"
                ticker = href.split('quote.ashx?t=')[1].split('&')[0]
                if ticker and ticker not in tickers:
                    tickers.append(ticker)
        
        return tickers 
from bs4 import BeautifulSoup
from typing import List, Optional
import time
from config.settings import PAGINATION_DELAY, MAX_PAGES

class PaginationHandler:
    def __init__(self, scraper):
        self.scraper = scraper

    def detect_pagination(self, soup: BeautifulSoup) -> bool:
        """Detect if the page has pagination controls."""
        # Look for pagination elements in Finviz
        pagination_selectors = [
            'a[href*="screener.ashx"][href*="r="]',  # Links with row parameter
            '.screener-pagination',  # Pagination container
            'a:contains("Next")',  # Next page links
            'a:contains(">")'  # Arrow links
        ]
        
        for selector in pagination_selectors:
            if soup.select(selector):
                return True
        return False

    def get_total_pages(self, soup: BeautifulSoup, base_url: str) -> int:
        """Calculate total number of pages based on current page content."""
        # Look for total count in the page
        # Finviz typically shows "1-20 of 500" format
        page_info = soup.find(text=lambda text: text and 'of' in text and text.strip().isdigit() == False)
        if page_info:
            # Extract total count from text like "1-20 of 500"
            try:
                parts = page_info.strip().split()
                if 'of' in parts:
                    of_index = parts.index('of')
                    if of_index + 1 < len(parts):
                        total_count = int(parts[of_index + 1])
                        # Assume 20 items per page (Finviz default)
                        return min((total_count + 19) // 20, MAX_PAGES)
            except (ValueError, IndexError):
                pass
        
        # Fallback: check if there are multiple page links
        page_links = soup.find_all('a', href=True)
        max_page = 1
        for link in page_links:
            href = link.get('href', '')
            if 'r=' in href:
                try:
                    # Extract row number from URL like "r=21" (page 2)
                    row_part = href.split('r=')[1].split('&')[0]
                    page_num = (int(row_part) // 20) + 1
                    max_page = max(max_page, page_num)
                except (ValueError, IndexError):
                    continue
        
        return min(max_page, MAX_PAGES)

    def scrape_all_pages(self, base_url: str) -> List[str]:
        """Scrape all pages and collect all ticker symbols."""
        all_tickers = []
        current_url = base_url
        page_count = 0
        
        while page_count < MAX_PAGES:
            try:
                # Get current page
                response = self.scraper._make_request(current_url)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract tickers from current page
                page_tickers = self.scraper._parse_ticker_symbols(soup)
                all_tickers.extend(page_tickers)
                
                # Check if there are more pages
                if not self.detect_pagination(soup):
                    break
                
                # Get next page URL
                next_url = self._get_next_page_url(soup, current_url)
                if not next_url or next_url == current_url:
                    break
                
                current_url = next_url
                page_count += 1
                
                # Add delay between pages
                time.sleep(PAGINATION_DELAY)
                
            except Exception as e:
                print(f"Error scraping page {page_count + 1}: {str(e)}")
                break
        
        # Remove duplicates while preserving order
        unique_tickers = []
        seen = set()
        for ticker in all_tickers:
            if ticker not in seen:
                unique_tickers.append(ticker)
                seen.add(ticker)
        
        return unique_tickers

    def _get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Get the URL for the next page."""
        # Look for next page links
        next_links = soup.find_all('a', href=True)
        
        for link in next_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Check for next page indicators
            if any(indicator in text.lower() for indicator in ['next', '>', '»']):
                if href.startswith('http'):
                    return href
                else:
                    # Relative URL, make it absolute
                    return f"https://finviz.com{href}"
            
            # Check for row parameter indicating next page
            if 'r=' in href and 'screener.ashx' in href:
                try:
                    current_row = self._extract_row_from_url(current_url)
                    next_row = self._extract_row_from_url(href)
                    if next_row and next_row > current_row:
                        if href.startswith('http'):
                            return href
                        else:
                            return f"https://finviz.com{href}"
                except (ValueError, IndexError):
                    continue
        
        return None

    def _extract_row_from_url(self, url: str) -> Optional[int]:
        """Extract row number from URL."""
        try:
            if 'r=' in url:
                row_part = url.split('r=')[1].split('&')[0]
                return int(row_part)
        except (ValueError, IndexError):
            pass
        return None 
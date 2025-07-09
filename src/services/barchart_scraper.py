#!/usr/bin/env python3

import requests
import logging
import time
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BarchartScraper:
    """Scraper for Barchart.com options data as fallback for open interest"""
    
    def __init__(self):
        self.base_url = "https://www.barchart.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.rate_limit_delay = 2  # seconds between requests
        
    def get_options_url(self, ticker: str) -> str:
        """Generate Barchart options URL for a ticker"""
        return f"{self.base_url}/stocks/quotes/{ticker.upper()}/options"
    
    def get_expiration_url(self, ticker: str, expiration_date: str) -> str:
        """Generate Barchart options URL for specific expiration"""
        # Convert YYYY-MM-DD to MM/DD/YYYY format for Barchart
        try:
            date_obj = datetime.strptime(expiration_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d/%Y')
            return f"{self.base_url}/stocks/quotes/{ticker.upper()}/options?expiration={formatted_date}"
        except ValueError:
            logging.warning(f"Invalid date format: {expiration_date}")
            return self.get_options_url(ticker)
    
    def scrape_options_page(self, ticker: str, expiration_date: str = None) -> Optional[Dict]:
        """Scrape options data from Barchart"""
        try:
            if expiration_date:
                url = self.get_expiration_url(ticker, expiration_date)
            else:
                url = self.get_options_url(ticker)
            
            logging.info(f"Scraping Barchart options data from: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract options data
            options_data = self._parse_options_table(soup, ticker, expiration_date)
            
            if options_data:
                logging.info(f"Successfully scraped options data for {ticker}")
                return options_data
            else:
                logging.warning(f"No options data found for {ticker}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error scraping Barchart for {ticker}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error scraping Barchart for {ticker}: {e}")
            return None
        finally:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
    
    def _parse_options_table(self, soup: BeautifulSoup, ticker: str, expiration_date: str = None) -> Optional[Dict]:
        """Parse options table from Barchart HTML"""
        try:
            # Look for options tables - Barchart typically has separate tables for calls and puts
            options_data = {
                'calls': [],
                'puts': [],
                'expiration_date': expiration_date,
                'ticker': ticker
            }
            
            # Find all tables that might contain options data
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for table headers that indicate options data
                headers = table.find_all('th')
                header_text = ' '.join([h.get_text(strip=True).lower() for h in headers])
                
                if any(keyword in header_text for keyword in ['strike', 'bid', 'ask', 'volume', 'open interest']):
                    # This looks like an options table
                    rows = table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 6:  # Minimum expected columns
                            option_data = self._parse_option_row(cells)
                            if option_data:
                                # Determine if it's a call or put based on strike vs current price
                                # This is a simplified approach - Barchart may have better indicators
                                if 'call' in header_text.lower():
                                    options_data['calls'].append(option_data)
                                elif 'put' in header_text.lower():
                                    options_data['puts'].append(option_data)
                                else:
                                    # Try to determine based on strike price logic
                                    # This is a fallback and may not be accurate
                                    pass
            
            # If we found any data, return it
            if options_data['calls'] or options_data['puts']:
                return options_data
            
            return None
            
        except Exception as e:
            logging.error(f"Error parsing options table: {e}")
            return None
    
    def _parse_option_row(self, cells: List) -> Optional[Dict]:
        """Parse a single option row from table cells"""
        try:
            # Extract text from cells
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for strike price (usually a number)
            strike = None
            for text in cell_texts:
                try:
                    strike = float(text.replace(',', ''))
                    break
                except ValueError:
                    continue
            
            if not strike:
                return None
            
            # Extract other data - this is a simplified parser
            # Barchart's exact structure may vary
            option_data = {
                'strike': strike,
                'lastPrice': self._extract_float(cell_texts, 0.0),
                'bid': self._extract_float(cell_texts, 0.0),
                'ask': self._extract_float(cell_texts, 0.0),
                'volume': self._extract_int(cell_texts, 0),
                'openInterest': self._extract_int(cell_texts, 0),
                'impliedVolatility': self._extract_float(cell_texts, 0.3),
                'change': self._extract_float(cell_texts, 0.0),
                'percentChange': self._extract_float(cell_texts, 0.0)
            }
            
            return option_data
            
        except Exception as e:
            logging.error(f"Error parsing option row: {e}")
            return None
    
    def _extract_float(self, texts: List[str], default: float) -> float:
        """Extract float value from list of text strings"""
        for text in texts:
            # Remove common formatting
            clean_text = text.replace(',', '').replace('%', '').replace('$', '')
            try:
                return float(clean_text)
            except ValueError:
                continue
        return default
    
    def _extract_int(self, texts: List[str], default: int) -> int:
        """Extract integer value from list of text strings"""
        for text in texts:
            # Remove common formatting
            clean_text = text.replace(',', '').replace('K', '000').replace('M', '000000')
            try:
                return int(float(clean_text))
            except ValueError:
                continue
        return default
    
    def get_open_interest_fallback(self, ticker: str, expiration_date: str, yahoo_options: Dict) -> Dict:
        """Get open interest data from Barchart as fallback when Yahoo returns zeros"""
        try:
            # Check if Yahoo data has all zero OI
            all_zero_oi = self._check_all_zero_oi(yahoo_options)
            
            if not all_zero_oi:
                logging.info(f"Yahoo data has non-zero OI for {ticker}, skipping Barchart fallback")
                return yahoo_options
            
            logging.info(f"Yahoo data has all zero OI for {ticker}, fetching Barchart fallback")
            
            # Scrape Barchart data
            barchart_data = self.scrape_options_page(ticker, expiration_date)
            
            if not barchart_data:
                logging.warning(f"Could not fetch Barchart data for {ticker}")
                return yahoo_options
            
            # Merge Barchart OI data with Yahoo data
            merged_data = self._merge_oi_data(yahoo_options, barchart_data)
            
            return merged_data
            
        except Exception as e:
            logging.error(f"Error in OI fallback for {ticker}: {e}")
            return yahoo_options
    
    def _check_all_zero_oi(self, options_data: Dict) -> bool:
        """Check if all open interest values are zero"""
        for expiry, chain_data in options_data.items():
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])
            
            for call in calls:
                if call.get('openInterest', 0) > 0:
                    return False
            
            for put in puts:
                if put.get('openInterest', 0) > 0:
                    return False
        
        return True
    
    def _merge_oi_data(self, yahoo_data: Dict, barchart_data: Dict) -> Dict:
        """Merge Barchart OI data with Yahoo data"""
        merged_data = yahoo_data.copy()
        
        # For now, we'll just log what we found
        # In a full implementation, you'd match strikes and merge the data
        logging.info(f"Barchart data found: {len(barchart_data.get('calls', []))} calls, {len(barchart_data.get('puts', []))} puts")
        
        # This is a placeholder - you'd implement proper merging logic
        # based on strike prices and expiration dates
        
        return merged_data

# Test function
def test_barchart_scraper():
    """Test the Barchart scraper"""
    scraper = BarchartScraper()
    
    # Test with SPY
    ticker = "SPY"
    expiration = "2025-07-11"  # Use a future date
    
    print(f"Testing Barchart scraper for {ticker}...")
    data = scraper.scrape_options_page(ticker, expiration)
    
    if data:
        print("✓ Successfully scraped data")
        print(f"  Calls: {len(data.get('calls', []))}")
        print(f"  Puts: {len(data.get('puts', []))}")
        
        # Show sample data
        if data.get('calls'):
            print(f"  Sample call: {data['calls'][0]}")
        if data.get('puts'):
            print(f"  Sample put: {data['puts'][0]}")
    else:
        print("✗ Failed to scrape data")

if __name__ == "__main__":
    test_barchart_scraper() 
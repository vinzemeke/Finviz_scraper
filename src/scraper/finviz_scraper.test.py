import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from src.scraper.finviz_scraper import FinvizScraper

class TestFinvizScraper:
    @pytest.fixture
    def scraper(self):
        return FinvizScraper()

    def test_init_headers(self, scraper):
        assert 'User-Agent' in scraper.session.headers
        assert 'Accept' in scraper.session.headers
        assert 'Accept-Language' in scraper.session.headers

    def test_validate_finviz_url_valid(self, scraper):
        valid_url = "https://finviz.com/screener.ashx?v=111&f=cap_large"
        assert scraper.validate_finviz_url(valid_url) is True

    def test_validate_finviz_url_invalid_domain(self, scraper):
        invalid_url = "https://google.com/screener.ashx?v=111"
        assert scraper.validate_finviz_url(invalid_url) is False

    def test_validate_finviz_url_missing_screener(self, scraper):
        invalid_url = "https://finviz.com/news.ashx"
        assert scraper.validate_finviz_url(invalid_url) is False

    def test_validate_finviz_url_empty(self, scraper):
        assert scraper.validate_finviz_url("") is False

    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_extract_ticker_symbols_success(self, mock_session, scraper):
        # Mock HTML content with ticker symbols
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>
                <a href="quote.ashx?t=GOOGL&ty=c&p=d&b=1">GOOGL</a>
                <a href="quote.ashx?t=MSFT&ty=c&p=d&b=1">MSFT</a>
                <a href="other.ashx?t=NOTICKER">Not a ticker</a>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        url = "https://finviz.com/screener.ashx?v=111"
        tickers = scraper.extract_ticker_symbols(url)
        
        expected_tickers = ["AAPL", "GOOGL", "MSFT"]
        assert set(tickers) == set(expected_tickers)

    def test_extract_ticker_symbols_invalid_url(self, scraper):
        with pytest.raises(ValueError, match="Invalid Finviz URL provided"):
            scraper.extract_ticker_symbols("https://google.com")

    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_extract_ticker_symbols_no_tickers(self, mock_session, scraper):
        html_content = '''
        <html>
            <body>
                <a href="other.ashx?t=NOTICKER">Not a ticker</a>
                <div>No ticker symbols here</div>
            </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        url = "https://finviz.com/screener.ashx?v=111"
        tickers = scraper.extract_ticker_symbols(url)
        
        assert tickers == []

    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_extract_ticker_symbols_network_error(self, mock_session, scraper):
        mock_session_instance = Mock()
        mock_session_instance.get.side_effect = Exception("Network error")
        mock_session.return_value = mock_session_instance
        
        url = "https://finviz.com/screener.ashx?v=111"
        
        with pytest.raises(Exception, match="Error extracting ticker symbols"):
            scraper.extract_ticker_symbols(url)

    def test_parse_ticker_symbols(self, scraper):
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>
                <a href="quote.ashx?t=GOOGL&ty=c&p=d&b=1">GOOGL</a>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>  <!-- Duplicate -->
            </body>
        </html>
        '''
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tickers = scraper._parse_ticker_symbols(soup)
        
        expected_tickers = ["AAPL", "GOOGL"]
        assert set(tickers) == set(expected_tickers)
        assert len(tickers) == 2  # No duplicates 
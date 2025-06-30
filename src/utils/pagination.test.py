import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from src.utils.pagination import PaginationHandler
from src.scraper.finviz_scraper import FinvizScraper

class TestPaginationHandler:
    @pytest.fixture
    def scraper(self):
        return FinvizScraper()

    @pytest.fixture
    def pagination_handler(self, scraper):
        return PaginationHandler(scraper)

    def test_detect_pagination_with_pagination_links(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="screener.ashx?v=111&r=21">Next</a>
                <a href="screener.ashx?v=111&r=41">2</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        assert pagination_handler.detect_pagination(soup) is True

    def test_detect_pagination_without_pagination(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL">AAPL</a>
                <div>No pagination here</div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        assert pagination_handler.detect_pagination(soup) is False

    def test_get_total_pages_from_page_info(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <div>1-20 of 500 results</div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        total_pages = pagination_handler.get_total_pages(soup, "https://finviz.com/screener.ashx")
        assert total_pages == 25  # (500 + 19) // 20 = 25

    def test_get_total_pages_from_links(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="screener.ashx?v=111&r=21">2</a>
                <a href="screener.ashx?v=111&r=41">3</a>
                <a href="screener.ashx?v=111&r=61">4</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        total_pages = pagination_handler.get_total_pages(soup, "https://finviz.com/screener.ashx")
        assert total_pages == 4

    def test_get_total_pages_single_page(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <div>No pagination</div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        total_pages = pagination_handler.get_total_pages(soup, "https://finviz.com/screener.ashx")
        assert total_pages == 1

    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_scrape_all_pages_single_page(self, mock_session, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>
                <a href="quote.ashx?t=GOOGL&ty=c&p=d&b=1">GOOGL</a>
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
        tickers = pagination_handler.scrape_all_pages(url)
        
        expected_tickers = ["AAPL", "GOOGL"]
        assert set(tickers) == set(expected_tickers)

    @patch('src.scraper.finviz_scraper.requests.Session')
    def test_scrape_all_pages_multiple_pages(self, mock_session, pagination_handler):
        # First page
        page1_html = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL&ty=c&p=d&b=1">AAPL</a>
                <a href="screener.ashx?v=111&r=21">Next</a>
            </body>
        </html>
        '''
        
        # Second page
        page2_html = '''
        <html>
            <body>
                <a href="quote.ashx?t=GOOGL&ty=c&p=d&b=1">GOOGL</a>
                <a href="quote.ashx?t=MSFT&ty=c&p=d&b=1">MSFT</a>
            </body>
        </html>
        '''
        
        mock_response1 = Mock()
        mock_response1.content = page1_html
        mock_response1.raise_for_status.return_value = None
        
        mock_response2 = Mock()
        mock_response2.content = page2_html
        mock_response2.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.side_effect = [mock_response1, mock_response2]
        mock_session.return_value = mock_session_instance
        
        url = "https://finviz.com/screener.ashx?v=111"
        tickers = pagination_handler.scrape_all_pages(url)
        
        expected_tickers = ["AAPL", "GOOGL", "MSFT"]
        assert set(tickers) == set(expected_tickers)

    def test_extract_row_from_url(self, pagination_handler):
        url = "https://finviz.com/screener.ashx?v=111&r=21&f=cap_large"
        row = pagination_handler._extract_row_from_url(url)
        assert row == 21

    def test_extract_row_from_url_no_row(self, pagination_handler):
        url = "https://finviz.com/screener.ashx?v=111&f=cap_large"
        row = pagination_handler._extract_row_from_url(url)
        assert row is None

    def test_get_next_page_url_with_next_link(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="screener.ashx?v=111&r=21">Next</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        current_url = "https://finviz.com/screener.ashx?v=111"
        next_url = pagination_handler._get_next_page_url(soup, current_url)
        assert next_url == "https://finviz.com/screener.ashx?v=111&r=21"

    def test_get_next_page_url_no_next(self, pagination_handler):
        html_content = '''
        <html>
            <body>
                <a href="quote.ashx?t=AAPL">AAPL</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html_content, 'html.parser')
        current_url = "https://finviz.com/screener.ashx?v=111"
        next_url = pagination_handler._get_next_page_url(soup, current_url)
        assert next_url is None 
import yfinance as yf
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooFinanceService:
    def __init__(self):
        pass

    def get_ticker_data(self, ticker_symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            logging.debug(f"yfinance info for {ticker_symbol}: {info}")

            if not info or 'regularMarketPrice' not in info:
                logging.warning(f"Could not retrieve data for {ticker_symbol}. Info: {info}")
                return None

            # Fetch historical data for EMA calculation
            hist = ticker.history(period="1y") # Get 1 year of data for 200-day EMA
            logging.debug(f"yfinance historical data for {ticker_symbol}: {hist.head()}")

            ema_8 = None
            ema_21 = None
            ema_200 = None

            if not hist.empty:
                # Calculate EMAs
                hist['EMA_8'] = hist['Close'].ewm(span=8, adjust=False).mean()
                hist['EMA_21'] = hist['Close'].ewm(span=21, adjust=False).mean()
                hist['EMA_200'] = hist['Close'].ewm(span=200, adjust=False).mean()

                ema_8 = hist['EMA_8'].iloc[-1] if 'EMA_8' in hist.columns else None
                ema_21 = hist['EMA_21'].iloc[-1] if 'EMA_21' in hist.columns else None
                ema_200 = hist['EMA_200'].iloc[-1] if 'EMA_200' in hist.columns else None

            # Get volume and 52-week range data
            volume = info.get('volume', 0)
            fifty_two_week_high = info.get('fiftyTwoWeekHigh', 0)
            fifty_two_week_low = info.get('fiftyTwoWeekLow', 0)
            
            # Format 52-week range
            if fifty_two_week_high and fifty_two_week_low:
                fifty_two_week_range = f"{fifty_two_week_low:.2f}-{fifty_two_week_high:.2f}"
            else:
                fifty_two_week_range = "N/A"
            
            data = {
                "ticker": ticker_symbol,
                "current_price": info.get('regularMarketPrice'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "volume": volume,
                "fifty_two_week_range": fifty_two_week_range,
                "fifty_two_week_high": fifty_two_week_high,
                "fifty_two_week_low": fifty_two_week_low,
                "ema_8": ema_8,
                "ema_21": ema_21,
                "ema_200": ema_200,
                "historical_data": hist.reset_index().rename(columns={'Date': 'Date'}).to_dict(orient='records') if not hist.empty else []
            }
            return data
        except Exception as e:
            logging.error(f"Error fetching data for {ticker_symbol} from Yahoo Finance: {e}")
            return None

    def get_historical_data(self, ticker_symbol: str, period: str = "1y", interval: str = "1d"):
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period, interval=interval)
            if not hist.empty:
                # Reset index to make 'Datetime' a column for JSON serialization
                hist = hist.reset_index()
                # Rename 'Datetime' to 'Date' for consistency with ChartGeneratorService
                hist = hist.rename(columns={'Datetime': 'Date'})
                return hist.to_dict(orient='records')
            return []
        except Exception as e:
            logging.error(f"Error fetching historical data for {ticker_symbol}: {e}")
            return []

if __name__ == '__main__':
    # Example Usage:
    service = YahooFinanceService()
    ticker_data = service.get_ticker_data("AAPL")
    if ticker_data:
        print(f"AAPL Data: {ticker_data}")

    ticker_data = service.get_ticker_data("MSFT")
    if ticker_data:
        print(f"MSFT Data: {ticker_data}")

    # Test a non-existent ticker
    ticker_data = service.get_ticker_data("NONEXISTENT")
    if ticker_data:
        print(f"NONEXISTENT Data: {ticker_data}")
    else:
        print("NONEXISTENT: No data found or error occurred.")

    # Test historical data
    hist_data = service.get_historical_data("GOOGL", period="3mo")
    if hist_data:
        print(f"GOOGL 3-month historical data (first 5 entries): {hist_data[:5]}")
    else:
        print("GOOGL historical data: No data found or error occurred.")
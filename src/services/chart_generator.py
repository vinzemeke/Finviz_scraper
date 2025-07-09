import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChartGeneratorService:
    def __init__(self, static_folder='static/charts'):
        self.static_folder = static_folder
        self._ensure_static_folder_exists()

    def _ensure_static_folder_exists(self):
        if not os.path.exists(self.static_folder):
            os.makedirs(self.static_folder)
            logging.info(f"Created static charts folder: {self.static_folder}")

    def generate_price_chart(self, ticker_symbol: str, historical_data: list, emas: dict) -> str:
        logging.info(f"Attempting to generate chart for {ticker_symbol}.")
        if not historical_data:
            logging.warning(f"No historical data provided for {ticker_symbol}. Cannot generate chart.")
            return "NO_DATA"
        
        if len(historical_data) < 2:
            logging.warning(f"Insufficient historical data for {ticker_symbol} (need at least 2 data points). Cannot generate chart.")
            return "NO_DATA"
        
        # Check if we have the required columns
        required_columns = ['Close']
        if not all(col in historical_data[0] for col in required_columns):
            missing_cols = [col for col in required_columns if col not in historical_data[0]]
            logging.error(f"Missing required columns for {ticker_symbol}: {missing_cols}")
            return "NO_DATA"

        try:
            df = pd.DataFrame(historical_data)
            # Ensure 'Date' is datetime and set as index for plotting
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif 'Datetime' in df.columns: # yfinance uses Datetime for history
                df['Datetime'] = pd.to_datetime(df['Datetime'])
                df.set_index('Datetime', inplace=True)
            else:
                logging.error(f"Date/Datetime column not found in historical data for {ticker_symbol}")
                return "NO_DATA"
        except Exception as e:
            logging.error(f"Error creating DataFrame for {ticker_symbol}: {e}")
            return "NO_DATA"

        logging.info(f"DataFrame for {ticker_symbol} created. Head: {df.head()}")

        try:
            plt.style.use('seaborn-v0_8-darkgrid') # A nice, clean style
            # Create figure with more space for legend on the left
            fig, ax = plt.subplots(figsize=(12, 7))
        except Exception as e:
            logging.error(f"Error setting up matplotlib for {ticker_symbol}: {e}")
            return "NO_DATA"

        try:
            # Plotting Close Price
            ax.plot(df.index, df['Close'], label='Close Price', color='cyan', linewidth=2)

            # Plotting EMAs
            if emas:
                if 'ema_8' in emas and emas['ema_8'] is not None:
                    df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
                    ax.plot(df.index, df['EMA_8'], label='8-day EMA', color='#28a745', linestyle='--', linewidth=1) # Green
                if 'ema_21' in emas and emas['ema_21'] is not None:
                    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
                    ax.plot(df.index, df['EMA_21'], label='21-day EMA', color='#ffc107', linestyle='--', linewidth=1) # Yellow
                if 'ema_200' in emas and emas['ema_200'] is not None:
                    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
                    ax.plot(df.index, df['EMA_200'], label='200-day EMA', color='#dc3545', linestyle='--', linewidth=1) # Red

            ax.set_title(f'{ticker_symbol} Stock Price and EMAs', fontsize=16, color='white')
            ax.set_xlabel('Date', fontsize=12, color='white')
            ax.set_ylabel('Price', fontsize=12, color='white')
            # Move legend outside the chart on the left
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=10, facecolor='#1e293b', edgecolor='white', labelcolor='white')
            ax.grid(True, linestyle='-', alpha=0.3, linewidth=0.5)
        except Exception as e:
            logging.error(f"Error plotting chart for {ticker_symbol}: {e}")
            plt.close(fig)
            return "NO_DATA"

        # Save the chart
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{ticker_symbol}_price_chart_{timestamp}.png"
        filepath = os.path.join(self.static_folder, filename)
        
        try:
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='#1e293b', edgecolor='none')
            plt.close(fig)  # Close the figure to free memory
            logging.info(f"Chart saved successfully for {ticker_symbol}: {filepath}")
            return filepath
        except Exception as e:
            logging.error(f"Error saving chart for {ticker_symbol}: {e}")
            plt.close(fig)  # Close the figure even if save fails
            return "NO_DATA"

    def cleanup_old_charts(self, max_age_hours: int = 24):
        """Removes charts older than max_age_hours from the static folder."""
        now = datetime.now()
        for filename in os.listdir(self.static_folder):
            filepath = os.path.join(self.static_folder, filename)
            if os.path.isfile(filepath):
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if (now - file_mod_time).total_seconds() / 3600 > max_age_hours:
                    try:
                        os.remove(filepath)
                        logging.info(f"Cleaned up old chart: {filename}")
                    except OSError as e:
                        logging.error(f"Error deleting old chart {filename}: {e}")

if __name__ == '__main__':
    # Example Usage (requires some dummy historical data)
    chart_service = ChartGeneratorService()

    # Dummy historical data (similar to yfinance output)
    dummy_historical_data = [
        {'Date': '2023-01-01', 'Close': 150.0},
        {'Date': '2023-01-02', 'Close': 152.0},
        {'Date': '2023-01-03', 'Close': 151.5},
        {'Date': '2023-01-04', 'Close': 153.0},
        {'Date': '2023-01-05', 'Close': 155.0},
        {'Date': '2023-01-06', 'Close': 154.5},
        {'Date': '2023-01-07', 'Close': 156.0},
        {'Date': '2023-01-08', 'Close': 157.0},
        {'Date': '2023-01-09', 'Close': 158.0},
        {'Date': '2023-01-10', 'Close': 157.5},
        {'Date': '2023-01-11', 'Close': 159.0},
        {'Date': '2023-01-12', 'Close': 160.0},
        {'Date': '2023-01-13', 'Close': 161.0},
        {'Date': '2023-01-14', 'Close': 160.5},
        {'Date': '2023-01-15', 'Close': 162.0},
    ]

    # Dummy EMA values (these would typically come from YahooFinanceService)
    dummy_emas = {
        'ema_8': 158.0,
        'ema_21': 155.0,
        'ema_200': 150.0 # Assuming a longer history for this
    }

    # Generate a chart
    chart_path = chart_service.generate_price_chart("TEST", dummy_historical_data, dummy_emas)
    if chart_path:
        print(f"Chart generated at: {chart_path}")

    # Test cleanup (create a dummy old file first)
    old_file_path = os.path.join(chart_service.static_folder, "old_chart.png")
    with open(old_file_path, 'w') as f:
        f.write("dummy content")
    # Set modification time to be old
    old_timestamp = datetime.now().timestamp() - (25 * 3600) # 25 hours ago
    os.utime(old_file_path, (old_timestamp, old_timestamp))

    print("Running cleanup...")
    chart_service.cleanup_old_charts(max_age_hours=24)
    print("Cleanup complete.")

    if not os.path.exists(old_file_path):
        print("Old chart successfully cleaned up.")
    else:
        print("Old chart was not cleaned up.")
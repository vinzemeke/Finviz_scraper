import sys
import os
from datetime import datetime
import numpy as np

# Add the project root to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template_string, request, redirect, url_for, flash, render_template, send_from_directory, jsonify
import logging
from src.storage.url_manager import URLManager
from src.scraper.scraper_engine import ScraperEngine
from src.storage.data_storage import DataStorage
from src.database.database_manager import DatabaseManager
from src.database.migration import MigrationManager
from src.services.yahoo_finance_service import YahooFinanceService
from src.services.chart_generator import ChartGeneratorService
from src.services.cache_manager import CacheManagerService
from src.services.monte_carlo_service import MonteCarloService
from src.services.options_data_service import OptionsDataService
from src.services.watchlist_service import WatchlistService
from src.services.stock_data_service import StockDataService
import os
import json
from src.services.lsm_american_options import LSMAmericanOptions

def format_market_cap(market_cap: float) -> str:
    if market_cap is None:
        return "N/A"
    if market_cap >= 1_000_000_000:
        return f"${market_cap / 1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        return f"${market_cap / 1_000_000:.2f}M"
    else:
        return f"${market_cap:,.2f}"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure Flask to find templates and static files in the root directory
try:
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
except NameError:
    # Handle case when __file__ is not defined (e.g., when using exec())
    template_dir = os.path.abspath(os.path.join(os.getcwd(), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.getcwd(), 'static'))

app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)
app.secret_key = 'finviz_secret_key'

def init_app_components(app, db_path=None):
    app.db_manager = DatabaseManager(db_path=db_path or os.environ.get('FLASK_DB_PATH', 'data/finviz_scraper.db'))
    app.url_manager = URLManager(app.db_manager)
    app.scraper_engine = ScraperEngine(app.db_manager, app.url_manager)
    app.data_storage = DataStorage(app.db_manager, app.url_manager)
    app.yahoo_finance_service = YahooFinanceService()
    app.chart_generator_service = ChartGeneratorService(static_folder=os.path.join(static_dir, 'charts'))
    app.cache_manager_service = CacheManagerService(app.db_manager)
    app.monte_carlo_service = MonteCarloService()
    app.options_data_service = OptionsDataService()
    app.watchlist_service = WatchlistService(app.db_manager)
    app.stock_data_service = StockDataService()

# Initialize application components (default for production)
init_app_components(app)

def sanitize_json_response(data):
    """
    Recursively sanitize data for JSON serialization by converting inf/NaN values to null.
    """
    if isinstance(data, dict):
        return {key: sanitize_json_response(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_response(item) for item in data]
    elif isinstance(data, (np.integer, np.floating)):
        if np.isinf(data) or np.isnan(data):
            return None
        return float(data)
    elif isinstance(data, np.ndarray):
        return sanitize_json_response(data.tolist())
    elif isinstance(data, float):
        if np.isinf(data) or np.isnan(data):
            return None
        return data
    else:
        return data

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Finviz Stock Scraper</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/url-management.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/sidebar.css') }}">
    <script src="{{ url_for('static', filename='js/url-management.js') }}"></script>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>📈 Finviz Scraper</h1>
            <p>Smart Stock Data Collection</p>
        </div>
        
        <nav class="sidebar-nav">
            <a href="/" class="nav-item active">
                <span class="nav-icon">🏠</span>
                <span>Dashboard</span>
            </a>
            <a href="/stats" class="nav-item">
                <span class="nav-icon">📊</span>
                <span>Statistics</span>
            </a>
            <a href="/database_stats" class="nav-item">
                <span class="nav-icon">🗄️</span>
                <span>Database Stats</span>
            </a>
        </nav>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="container">
            <div class="page-header">
                <h2>Dashboard</h2>
                <p>Manage your Finviz URLs and scrape stock ticker symbols efficiently</p>
            </div>
            
            <div class="form-section">
                <h3>Add New URL</h3>
                <form method="post" action="/add_url">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="name">URL Name</label>
                            <input type="text" id="name" name="name" placeholder="e.g., TPS SCANNER" required>
                        </div>
                        <div class="form-group">
                            <label for="url">Finviz Screener URL</label>
                            <input type="text" id="url" name="url" placeholder="https://finviz.com/screener.ashx?..." required>
                        </div>
                        <div class="form-group">
                            <button type="submit" class="btn btn-primary">Add URL</button>
                        </div>
                    </div>
                </form>
                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    <div class="flash success">{{ messages[0] }}</div>
                  {% endif %}
                {% endwith %}
            </div>
            
            <div class="urls-section">
                <h3>Saved Scans</h3>
                {% if urls %}
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>URL</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in urls %}
                        <tr>
                            <td><strong>{{ u.name }}</strong></td>
                            <td><a href="{{ u.url }}" target="_blank" style="color: #3182ce;">{{ u.url }}</a></td>
                            <td>
                                <div class="action-buttons">
                                    <form method="post" action="/scrape" style="display:inline;">
                                        <input type="hidden" name="name" value="{{ u.name }}">
                                        <div class="force-scrape">
                                            <label>
                                                <input type="checkbox" id="force_{{ u.name }}" name="force_scrape" value="true">
                                                Force find stocks (bypass deduplication)
                                            </label>
                                        </div>
                                        <button type="submit" class="btn btn-primary">Find Stocks</button>
                                    </form>
                                    <a href="/edit_url/{{ u.name }}" class="btn-edit">✏️ Edit</a>
                                    <a href="/delete_url/{{ u.name }}" class="btn-delete" 
                                       data-url-name="{{ u.name }}" data-url="{{ u.url }}">🗑️ Delete</a>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                    <div style="text-align: center; padding: 40px; color: #718096;">
                        <p style="font-size: 1.2em; margin-bottom: 10px;">No scans saved yet</p>
                        <p>Add your first Finviz scan above to get started</p>
                    </div>
                {% endif %}
            </div>
            
            {% if results %}
            <div class="results-section">
                <h3>Stock Finding Results for "{{ results.name }}"</h3>
                {% if results.status == 'skipped' %}
                    <p><strong>Status:</strong> <span class="status-badge status-skipped">{{ results.status|title }}</span></p>
                    <p><strong>Reason:</strong> {{ results.reason }}</p>
                {% elif results.status == 'failed' %}
                    <p><strong>Status:</strong> <span class="status-badge status-failed">{{ results.status|title }}</span></p>
                    <p><strong>Reason:</strong> {{ results.reason }}</p>
                {% else %}
                    <p><strong>Status:</strong> <span class="status-badge status-completed">{{ results.status|title }}</span></p>
                    <p>Found <strong>{{ results.tickers|length }}</strong> ticker(s):</p>
                    <div style="max-height:300px;overflow:auto; margin-top: 15px;">
                    <table>
                        <thead>
                            <tr><th>Ticker Symbol</th></tr>
                        </thead>
                        <tbody>
                            {% for t in results.tickers %}
                            <tr><td><code>{{ t }}</code></td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    </div>
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
""" 

@app.route("/")
def index():
    urls = app.url_manager.list_urls()
    return render_template('dashboard.html', urls=urls, results=None)

@app.route("/view_scanned_list/<name>")
def view_scanned_list(name):
    if not app.url_manager.url_exists(name):
        flash("URL not found.")
        return redirect(url_for('index'))

    # Try to get previously scraped tickers
    previous_tickers = app.data_storage.get_tickers_for_url(name)

    if previous_tickers:
        flash(f"Displaying previously scraped data for '{name}'.")
        results = {"name": name, "tickers": previous_tickers, "status": "completed"}
    else:
        # If no previous data, initiate a new stock finding session
        flash(f"No previous data found for '{name}'. Initiating a new stock finding session.")
        try:
            scrape_result = app.scraper_engine.scrape_url(name, force_scrape=False)
            if scrape_result['status'] == 'completed':
                tickers = scrape_result['tickers']
                if tickers:
                    csv_path = app.data_storage.save_tickers_to_csv(name, tickers, scrape_result)
                    if csv_path:
                        flash(f"Successfully found {len(tickers)} stocks. Data saved to database and CSV.")
                    else:
                        flash(f"Found {len(tickers)} stocks but failed to save data.")
                else:
                    flash("No stocks found on the page.")
                results = {"name": name, "tickers": tickers, "status": "completed"}
            else:
                flash(f"Stock finding failed: {scrape_result.get('reason', 'Unknown error')}")
                results = {"name": name, "tickers": [], "status": "failed", "reason": scrape_result.get('reason')}
        except Exception as e:
            error_msg = f"Stock finding failed: {str(e)}"
            logger.error(error_msg)
            flash(error_msg)
            results = {"name": name, "tickers": [], "status": "failed", "reason": error_msg}

    urls = app.url_manager.list_urls()
    return render_template('dashboard.html', urls=urls, results=results)

@app.route("/api/ticker_details/<ticker_symbol>")
def api_ticker_details(ticker_symbol):
    ticker_symbol = ticker_symbol.upper() # Ensure uppercase
    
    # Try to get data from cache first
    cached_data = app.cache_manager_service.get_cached_ticker_data(ticker_symbol)
    
    if cached_data:
        ticker_info = cached_data
        chart_path = ticker_info.get('chart_path')
        if chart_path == 'NO_DATA':
            chart_path = None
        logger.info(f"Displaying cached data for {ticker_symbol}.")
    else:
        # Fetch fresh data if not in cache or stale
        logger.info(f"Fetching live data for {ticker_symbol}...")
        ticker_info = app.yahoo_finance_service.get_ticker_data(ticker_symbol)
        chart_path = None

        if ticker_info:
            # Generate chart
            historical_data = app.yahoo_finance_service.get_historical_data(ticker_symbol, period="3mo", interval="1d")
            emas = {
                'ema_8': ticker_info.get('ema_8'),
                'ema_21': ticker_info.get('ema_21'),
                'ema_200': ticker_info.get('ema_200')
            }
            chart_path = app.chart_generator_service.generate_price_chart(ticker_symbol, historical_data, emas)
            if chart_path == 'NO_DATA':
                chart_path = None
            # Cache the new data and chart path
            app.cache_manager_service.set_cached_ticker_data(ticker_symbol, ticker_info, chart_path)
        else:
            logger.warning(f"Could not retrieve data for {ticker_symbol}.")

    # Format market_cap before sending as JSON
    if ticker_info:
        ticker_info['market_cap_formatted'] = format_market_cap(ticker_info.get('market_cap'))
        ticker_info['chart_path'] = chart_path
        return jsonify(ticker_info)
    else:
        return jsonify({}), 404

@app.route("/charts/<filename>")
def serve_chart(filename):
    return send_from_directory(os.path.join(app.static_folder, 'charts'), filename)

@app.route("/refresh_all_data")
def refresh_all_data():
    app.cache_manager_service.clear_all_cache()
    app.chart_generator_service.cleanup_old_charts(max_age_hours=0) # Clean up all charts immediately
    flash("All cached data and charts refreshed successfully!")
    return redirect(url_for('index'))

@app.route("/add_url", methods=["POST"])
def add_url():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not url:
        flash("Both name and URL are required.")
        return redirect(url_for('index'))
    if not app.scraper_engine.validate_finviz_url(url):
        flash("Invalid Finviz screener URL.")
        return redirect(url_for('index'))
    
    success = app.url_manager.save_url(name, url)
    if success:
        flash(f"Saved URL '{name}'.")
    else:
        flash(f"Failed to save URL '{name}'. Name may already exist.")
    return redirect(url_for('index'))

@app.route("/scrape", methods=["POST"])
def scrape():
    name = request.form.get("name", "").strip()
    force_scrape = request.form.get("force_scrape", "false").lower() == "true"
    
    if not app.url_manager.url_exists(name):
        flash("URL not found.")
        return redirect(url_for('index'))
    
    try:
        # Use the new scraper engine with deduplication
        logger.info(f"Starting stock finding for scan '{name}' (force_scrape: {force_scrape})")
        
        scrape_result = app.scraper_engine.scrape_url(name, force_scrape=force_scrape)
        
        if scrape_result['status'] == 'skipped':
            # Get previous results from database when stock finding is skipped
            previous_tickers = app.data_storage.get_tickers_for_url(name)
            if previous_tickers:
                flash(f"Stock finding skipped: {scrape_result['reason']}. Showing previous results.")
                results = {"name": name, "tickers": previous_tickers, "status": "skipped", "reason": scrape_result['reason']}
            else:
                flash(f"Stock finding skipped: {scrape_result['reason']}. No previous results found.")
                results = {"name": name, "tickers": [], "status": "skipped", "reason": scrape_result['reason']}
        elif scrape_result['status'] == 'completed':
            tickers = scrape_result['tickers']
            if tickers:
                # Save to database and CSV
                csv_path = app.data_storage.save_tickers_to_csv(name, tickers, scrape_result)
                if csv_path:
                    flash(f"Successfully found {len(tickers)} stocks. Data saved to database and CSV.")
                else:
                    flash(f"Found {len(tickers)} stocks but failed to save data.")
            else:
                flash("No stocks found on the page.")
            
            results = {"name": name, "tickers": tickers, "status": "completed"}
        else:
            flash(f"Stock finding failed: {scrape_result.get('reason', 'Unknown error')}")
            results = {"name": name, "tickers": [], "status": "failed", "reason": scrape_result.get('reason')}
        
        urls = app.url_manager.list_urls()
        return render_template('dashboard.html', urls=urls, results=results)
        
    except Exception as e:
        error_msg = f"Stock finding failed: {str(e)}"
        logger.error(error_msg)
        flash(error_msg)
        return redirect(url_for('index'))

@app.route("/edit_url/<name>", methods=["GET"])
def edit_url(name):
    url_data = app.url_manager.get_url_by_name(name)
    if not url_data:
        flash("URL not found.")
        return redirect(url_for('index'))
    return render_template('edit_url.html', url_data=url_data)

@app.route("/update_url", methods=["POST"])
def update_url():
    old_name = request.form.get("old_name", "").strip()
    new_name = request.form.get("name", "").strip()
    new_url = request.form.get("url", "").strip()
    
    if not old_name or not new_name or not new_url:
        flash("All fields are required.")
        return redirect(url_for('edit_url', name=old_name))
    
    if not app.scraper_engine.validate_finviz_url(new_url):
        flash("Invalid Finviz screener URL.")
        return redirect(url_for('edit_url', name=old_name))
    
    success = app.url_manager.update_url(old_name, new_name, new_url)
    if success:
        flash(f"Successfully updated URL '{old_name}' to '{new_name}'.")
        return redirect(url_for('index'))
    else:
        flash("Failed to update URL. Name may already exist or URL not found.")
        return redirect(url_for('edit_url', name=old_name))

@app.route("/delete_url/<name>", methods=["GET"])
def delete_url(name):
    url_data = app.url_manager.get_url_by_name(name)
    if not url_data:
        flash("URL not found.")
        return redirect(url_for('index'))
    
    # Delete the URL
    success = app.url_manager.delete_url(name)
    if success:
        flash(f"Successfully deleted URL '{name}'.")
    else:
        flash("Failed to delete URL.")
    
    return redirect(url_for('index'))

@app.route("/database_stats")
def database_stats():
    """Display database statistics."""
    try:
        db_stats = app.db_manager.get_database_stats()
        url_stats = app.url_manager.get_url_stats()
        storage_stats = app.data_storage.get_storage_stats()
        
        stats = {
            'database': db_stats,
            'urls': url_stats,
            'storage': storage_stats
        }
        
        return render_template('database_stats.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        flash("Error retrieving database statistics.")
        return redirect(url_for('index'))

@app.route("/export_csv/<name>", methods=["GET"])
def export_csv(name):
    """Export ticker data for a URL to CSV."""
    try:
        csv_path = app.data_storage.export_to_csv(name)
        if csv_path:
            flash(f"Successfully exported data for '{name}' to CSV.")
        else:
            flash(f"No data found for URL '{name}'.")
    except Exception as e:
        logger.error(f"Error exporting CSV for '{name}': {e}")
        flash("Error exporting data to CSV.")
    
    return redirect(url_for('index'))

@app.route("/stats")
def stats():
    """Show scraping statistics and deduplication effectiveness."""
    try:
        # Get overall statistics
        total_scans = len(app.url_manager.list_urls())
        
        # Get scraping session statistics
        session_stats = app.db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_sessions,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_sessions
            FROM scraping_sessions
        """,)
        
        if session_stats and session_stats[0]:
            stats = session_stats[0]
            total_sessions = stats[0] or 0
            completed_sessions = stats[1] or 0
            failed_sessions = stats[2] or 0
            skipped_sessions = stats[3] or 0
        else:
            total_sessions = completed_sessions = failed_sessions = skipped_sessions = 0
        
        # Calculate deduplication effectiveness
        if total_sessions > 0:
            dedup_rate = (skipped_sessions / total_sessions) * 100
        else:
            dedup_rate = 0
        
        # Get recent activity
        recent_sessions = app.db_manager.execute_query("""
            SELECT 
                s.timestamp,
                s.status,
                s.ticker_count,
                s.dedup_reason,
                u.name as url_name
            FROM scraping_sessions s
            JOIN urls u ON s.url_id = u.id
            ORDER BY s.timestamp DESC, s.id DESC
            LIMIT 10
        """,)
        
        # Get top URLs by activity
        top_urls = app.db_manager.execute_query("""
            SELECT 
                u.name,
                COUNT(s.id) as session_count,
                SUM(CASE WHEN s.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN s.status = 'skipped' THEN 1 ELSE 0 END) as skipped_count
            FROM urls u
            LEFT JOIN scraping_sessions s ON u.id = s.url_id
            GROUP BY u.id, u.name
            ORDER BY session_count DESC
            LIMIT 5
        """,)
        
        return render_template('stats.html',
        total_scans=total_scans,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        failed_sessions=failed_sessions,
        skipped_sessions=skipped_sessions,
        dedup_rate=dedup_rate,
        top_urls=top_urls,
        recent_sessions=recent_sessions
        )
        
    except Exception as e:
        logger.error(f"Error generating stats: {e}")
        flash(f"Error generating statistics: {str(e)}")
        return redirect(url_for('index'))

@app.route("/monte_carlo")
def monte_carlo_dashboard():
    return render_template('monte_carlo.html')

@app.route("/monte_carlo/watchlists")
def monte_carlo_watchlists():
    return render_template('monte_carlo_watchlists.html')

@app.route("/monte_carlo/results")
def monte_carlo_results():
    return render_template('monte_carlo_results.html')

@app.route("/api/watchlists", methods=["POST"])
def create_watchlist():
    name = request.json.get("name")
    if not name:
        return jsonify({"error": "Watchlist name is required"}), 400
    
    watchlist_id = app.watchlist_service.create_watchlist(name)
    if watchlist_id:
        return jsonify({"message": "Watchlist created successfully", "id": watchlist_id}), 201
    else:
        return jsonify({"error": "Failed to create watchlist, name might already exist"}), 409

@app.route("/api/watchlists", methods=["GET"])
def list_watchlists():
    watchlists = app.watchlist_service.list_watchlists()
    return jsonify(watchlists), 200

@app.route("/api/watchlists/<int:watchlist_id>", methods=["PUT"])
def update_watchlist(watchlist_id):
    new_name = request.json.get("name")
    if not new_name:
        return jsonify({"error": "New watchlist name is required"}), 400
    
    if app.watchlist_service.update_watchlist(watchlist_id, new_name):
        return jsonify({"message": "Watchlist updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update watchlist, ID might not exist or name already taken"}), 404

@app.route("/api/watchlists/<int:watchlist_id>", methods=["DELETE"])
def delete_watchlist(watchlist_id):
    if app.watchlist_service.delete_watchlist(watchlist_id):
        return jsonify({"message": "Watchlist deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete watchlist, ID not found"}), 404

@app.route("/api/watchlists/<int:watchlist_id>/tickers", methods=["POST"])
def add_ticker_to_watchlist(watchlist_id):
    ticker_symbol = request.json.get("ticker_symbol")
    if not ticker_symbol:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    if app.watchlist_service.add_ticker_to_watchlist(watchlist_id, ticker_symbol.upper()):
        return jsonify({"message": "Ticker added to watchlist successfully"}), 201
    else:
        return jsonify({"error": "Failed to add ticker, it might already be in the watchlist or watchlist ID is invalid"}), 409

@app.route("/api/watchlists/<int:watchlist_id>/tickers/<string:ticker_symbol>", methods=["DELETE"])
def remove_ticker_from_watchlist(watchlist_id, ticker_symbol):
    if app.watchlist_service.remove_ticker_from_watchlist(watchlist_id, ticker_symbol.upper()):
        return jsonify({"message": "Ticker removed from watchlist successfully"}), 200
    else:
        return jsonify({"error": "Failed to remove ticker, not found in watchlist or watchlist ID is invalid"}), 404

@app.route("/api/watchlists/<int:watchlist_id>/tickers", methods=["GET"])
def get_tickers_in_watchlist(watchlist_id):
    tickers = app.watchlist_service.get_tickers_in_watchlist(watchlist_id)
    return jsonify(tickers), 200

@app.route("/api/watchlists/<int:watchlist_id>/tickers/bulk", methods=["POST"])
def bulk_add_tickers_to_watchlist(watchlist_id):
    data = request.get_json(force=True)
    tickers = data.get("tickers", [])
    if not isinstance(tickers, list) or not tickers:
        return jsonify({"error": "A non-empty list of tickers is required"}), 400
    
    added = []
    already_present = []
    failed = []
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if not ticker:
            failed.append(ticker)
            continue
        # Try to add, check if already present
        result = app.watchlist_service.add_ticker_to_watchlist(watchlist_id, ticker)
        if result:
            added.append(ticker)
        else:
            # Check if it's already present
            current = app.watchlist_service.get_tickers_in_watchlist(watchlist_id)
            if ticker in current:
                already_present.append(ticker)
            else:
                failed.append(ticker)
    return jsonify({
        "added": added,
        "already_present": already_present,
        "failed": failed,
        "message": f"Added {len(added)}, {len(already_present)} already present, {len(failed)} failed."
    }), 200

@app.route("/api/simulate", methods=["POST"])
def simulate_option():
    data = request.json
    
    # Check if this is the new format with multiple options
    if "options" in data:
        # New format: multiple options simulation
        options = data.get("options", [])
        num_simulations = data.get("num_simulations", 10000)
        risk_free_rate = data.get("risk_free_rate", 0.01)
        volatility_source = data.get("volatility_source", "implied")
        current_price = data.get("current_price")
        
        if not options or not current_price:
            return jsonify({"error": "Missing required simulation parameters"}), 400
        
        try:
            # Get the first option to determine ticker and expiry
            first_option = options[0]
            ticker = first_option.get("ticker")
            expiry_date = first_option.get("expiry_date")
            
            if not ticker or not expiry_date:
                return jsonify({"error": "Missing ticker or expiry date"}), 400
            
            # Calculate time to expiration from expiry date
            expiry_datetime = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            current_datetime = datetime.now(expiry_datetime.tzinfo)
            time_to_expiration = (expiry_datetime - current_datetime).days / 365.0
            
            if time_to_expiration <= 0:
                return jsonify({"error": "Option has already expired"}), 400
            
            # Run simulation for each option
            results = []
            options_for_analysis = []
            for option in options:
                strike_price = option.get("strike_price")
                option_type = option.get("option_type")
                
                if not strike_price or not option_type:
                    continue
                
                # Get volatility from options data if available
                volatility = 0.3  # Default volatility
                options_data = None  # Initialize options_data
                if volatility_source == "implied":
                    options_data = app.options_data_service.fetch_options_chain(ticker)
                    if options_data and expiry_date in options_data:
                        chain_data = options_data[expiry_date]
                        option_chain = chain_data.get('calls' if option_type == 'call' else 'puts', [])
                        # Find matching option and get implied volatility
                        for opt in option_chain:
                            if abs(opt.get('strike', 0) - strike_price) < 0.01:
                                volatility = opt.get('impliedVolatility', 0.3)
                                break
                
                # Get market price from options data
                market_price = 0.0
                if options_data and expiry_date in options_data:
                    chain_data = options_data[expiry_date]
                    option_chain = chain_data.get('calls' if option_type == 'call' else 'puts', [])
                    for opt in option_chain:
                        if abs(opt.get('strike', 0) - strike_price) < 0.01:
                            market_price = opt.get('lastPrice', 0.0)
                            break
                
                # Add the option to the list for batch analysis
                options_for_analysis.append({
                    "ticker": ticker,
                    "strike_price": strike_price,
                    "option_type": option_type,
                    "expiry_date": expiry_date,
                    "market_price": market_price,
                    "implied_volatility": volatility
                })
            
            # Run Monte Carlo simulation for all options at once
            if options_for_analysis:
                analysis_results = app.monte_carlo_service.analyze_multiple_options_simulation(
                    options_for_analysis, current_price, risk_free_rate, num_simulations, use_greeks=True
                )
                
                if analysis_results and 'options_results' in analysis_results:
                    results = analysis_results['options_results']
                    terminal_prices = analysis_results.get('terminal_prices', [])
                else:
                    results = []
                    terminal_prices = []
            
            if results:
                simulation_data = {
                    "ticker": ticker,
                    "current_price": current_price,
                    "expiry_date": expiry_date,
                    "time_to_expiration": time_to_expiration,
                    "options_results": results,
                    "price_paths": [],  # Placeholder for price distribution
                    "terminal_prices": terminal_prices if 'terminal_prices' in locals() else []
                }
                
                # Create a response version without large arrays for JSON serialization
                response_data = simulation_data.copy()
                
                # Sanitize the response data for JSON serialization
                response_data = sanitize_json_response(response_data)
                
                sim_id = app.db_manager.save_simulation_result(ticker, f"{ticker}_multi", json.dumps(simulation_data))
                return jsonify({
                    "message": "Simulation completed", 
                    "simulation_id": sim_id, 
                    "simulation_data": response_data
                }), 200
            else:
                return jsonify({"error": "No valid options to simulate"}), 400
                
        except Exception as e:
            logger.error(f"Error during multi-option simulation: {e}")
            return jsonify({"error": str(e)}), 500
    
    else:
        # Old format: single option simulation
        ticker = data.get("ticker")
        strike_price = data.get("strike_price")
        option_type = data.get("option_type")
        time_to_expiration = data.get("time_to_expiration")
        risk_free_rate = data.get("risk_free_rate")
        volatility = data.get("volatility")
        num_simulations = data.get("num_simulations", 10000)
        num_steps = data.get("num_steps", 252)

        if not all([ticker, strike_price, option_type, time_to_expiration, risk_free_rate, volatility]):
            return jsonify({"error": "Missing required simulation parameters"}), 400

        try:
            # Fetch current stock price
            ticker_info = app.yahoo_finance_service.get_ticker_data(ticker)
            if not ticker_info or 'current_price' not in ticker_info:
                return jsonify({"error": f"Could not get current price for {ticker}"}), 400
            S0 = ticker_info['current_price']

            analysis_results = app.monte_carlo_service.analyze_single_option_simulation(
                S0, strike_price, time_to_expiration, risk_free_rate, volatility, 
                option_type, num_simulations, num_steps, use_greeks=True
            )

            if analysis_results and len(analysis_results) > 0:
                # Remove price_paths from the response to avoid JSON serialization issues
                # Price paths are large arrays that can cause issues
                response_data = analysis_results.copy()
                if 'price_paths' in response_data:
                    del response_data['price_paths']
                
                # Sanitize the response data for JSON serialization
                response_data = sanitize_json_response(response_data)
                
                # Create a clean version for database storage (without price_paths)
                db_data = analysis_results.copy()
                if 'price_paths' in db_data:
                    del db_data['price_paths']
                
                sim_id = app.db_manager.save_simulation_result(ticker, f"{ticker}{option_type}{strike_price}", json.dumps(db_data))
                return jsonify({"message": "Simulation completed", "simulation_id": sim_id, "simulation_data": response_data}), 200
            else:
                return jsonify({"error": "Simulation failed - no results returned"}), 500
        except Exception as e:
            logger.error(f"Error during simulation: {e}")
            return jsonify({"error": str(e)}), 500

@app.route("/api/simulation/<int:simulation_id>", methods=["GET"])
def get_simulation_result(simulation_id):
    result = app.db_manager.get_simulation_result(simulation_id)
    if result:
        # Simulation data is stored as TEXT, so parse it back to dict
        result['simulation_data'] = json.loads(result['simulation_data'])
        return jsonify(result), 200
    else:
        return jsonify({"error": "Simulation result not found"}), 404

@app.route("/api/simulation/<int:simulation_id>/export", methods=["GET"])
def export_simulation_result(simulation_id):
    result = app.db_manager.get_simulation_result(simulation_id)
    if result:
        simulation_data = json.loads(result['simulation_data'])
        # For simplicity, just return as JSON for now. CSV/Excel export would be more complex.
        return jsonify(simulation_data), 200
    else:
        return jsonify({"error": "Simulation result not found"}), 404

@app.route("/api/simulate/batch", methods=["POST"])
def batch_simulate():
    data = request.json
    watchlist_id = data.get("watchlist_id")
    # Other simulation parameters would also be passed in data

    if not watchlist_id:
        return jsonify({"error": "Watchlist ID is required for batch simulation"}), 400

    tickers = app.watchlist_service.get_tickers_in_watchlist(watchlist_id)
    if not tickers:
        return jsonify({"message": "No tickers in watchlist to simulate"}), 200

    results = []
    for ticker in tickers:
        # This is a simplified example. In a real scenario, you'd fetch
        # options data for each ticker and iterate through contracts.
        # For now, just run a dummy simulation.
        try:
            # Fetch current stock price
            ticker_info = app.yahoo_finance_service.get_ticker_data(ticker)
            if not ticker_info or 'current_price' not in ticker_info:
                results.append({"ticker": ticker, "status": "failed", "error": "Could not get current price"})
                continue
            S0 = ticker_info['current_price']

            # Dummy parameters for batch simulation
            K = S0 * 1.05 # Example strike
            T = 0.5 # 6 months
            r = 0.01 # 1%
            sigma = 0.3 # 30%
            option_type = 'call'

            option_price = app.monte_carlo_service.run_monte_carlo_simulation(
                S0, K, T, r, sigma, option_type
            )
            if option_price is not None:
                simulation_data = {
                    "ticker": ticker,
                    "strike_price": K,
                    "option_type": option_type,
                    "estimated_price": option_price
                }
                sim_id = app.db_manager.save_simulation_result(ticker, f"{ticker}{option_type}{K}", json.dumps(simulation_data))
                results.append({"ticker": ticker, "status": "completed", "estimated_price": option_price, "simulation_id": sim_id})
            else:
                results.append({"ticker": ticker, "status": "failed", "error": "Simulation failed"})
        except Exception as e:
            logger.error(f"Error during batch simulation for {ticker}: {e}")
            results.append({"ticker": ticker, "status": "failed", "error": str(e)})

    return jsonify(results), 200

@app.route("/api/preferences", methods=["GET"])
def get_user_preferences():
    # Assuming a default user_id for now, as authentication is not implemented
    user_id = 1 
    preferences = app.db_manager.get_user_preferences(user_id)
    if preferences:
        # If other_settings is stored as JSON string, parse it
        if preferences.get('other_settings'):
            preferences['other_settings'] = json.loads(preferences['other_settings'])
        return jsonify(preferences), 200
    else:
        # Return default preferences if none are found for the user
        return jsonify({
            "user_id": user_id,
            "underpricing_threshold": 0.05,
            "strike_range": 0.10,
            "other_settings": {}
        }), 200

@app.route("/api/preferences", methods=["PUT"])
def update_user_preferences():
    user_id = 1 # Assuming a default user_id
    data = request.json
    underpricing_threshold = data.get("underpricing_threshold")
    strike_range = data.get("strike_range")
    other_settings = data.get("other_settings")

    # Convert other_settings dict to JSON string if present
    if isinstance(other_settings, dict):
        other_settings = json.dumps(other_settings)
    elif other_settings is not None: # Ensure it's not None if it's not a dict but still present
        other_settings = str(other_settings) # Convert to string if it's some other type

    if app.db_manager.update_user_preferences(user_id, underpricing_threshold, strike_range, other_settings):
        return jsonify({"message": "User preferences updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update user preferences"}), 500

@app.route("/api/preferences/reset", methods=["POST"])
def reset_user_preferences():
    user_id = 1 # Assuming a default user_id
    # Delete existing preferences to reset to defaults
    # Note: DatabaseManager doesn't have a direct delete_user_preferences method.
    # For now, we'll just overwrite with defaults.
    if app.db_manager.save_user_preferences(user_id, 0.05, 0.10, "{}"):
        return jsonify({"message": "User preferences reset to defaults"}), 200
    else:
        return jsonify({"error": "Failed to reset user preferences"}), 500

@app.route("/api/options/<ticker>", methods=["GET"])
def get_options_chain(ticker):
    options_chain = app.options_data_service.fetch_options_chain(ticker.upper())
    if options_chain:
        return jsonify(options_chain), 200
    else:
        return jsonify({"error": f"Could not retrieve options chain for {ticker}"}), 404

@app.route("/api/options/<ticker>/refresh", methods=["POST"])
def refresh_options_data(ticker):
    options_chain = app.options_data_service.fetch_options_chain(ticker.upper(), force_refresh=True)
    if options_chain:
        return jsonify({"message": f"Options data for {ticker} refreshed successfully"}), 200
    else:
        return jsonify({"error": f"Failed to refresh options data for {ticker}"}), 500

@app.route("/api/options/<ticker>/last-updated", methods=["GET"])
def get_options_last_updated(ticker):
    timestamp = app.options_data_service.cache_timestamps.get(ticker.upper())
    if timestamp:
        return jsonify({"ticker": ticker, "last_updated": timestamp.isoformat()}), 200
    else:
        return jsonify({"ticker": ticker, "last_updated": None, "message": "No cached data found"}), 404

@app.route("/api/lsm_american_option", methods=["POST"])
def lsm_american_option_api():
    data = request.get_json(force=True)
    required_params = ["S0", "K", "r", "sigma", "T", "option_type"]
    missing = [p for p in required_params if p not in data]
    if missing:
        return jsonify({"error": f"Missing required parameters: {', '.join(missing)}"}), 400

    # Parse parameters
    try:
        S0 = float(data["S0"])
        K = float(data["K"])
        r = float(data["r"])
        sigma = float(data["sigma"])
        T = float(data["T"])
        option_type = str(data["option_type"]).lower()
        steps = int(data.get("steps", 50))
        batch_size = int(data.get("batch_size", 5000))
        max_paths = int(data.get("max_paths", 100000))
        tolerance = float(data.get("tolerance", 0.005))
        greek_shift = float(data.get("greek_shift", 0.01))
        adaptive_batching = bool(data.get("adaptive_batching", True))
        min_batches = int(data.get("min_batches", 3))
        max_cv = float(data.get("max_cv", 0.1))
    except Exception as e:
        return jsonify({"error": f"Invalid parameter types: {str(e)}"}), 400

    # Validate option_type
    if option_type not in ["call", "put"]:
        return jsonify({"error": "option_type must be 'call' or 'put'"}), 400

    try:
        lsm = LSMAmericanOptions()
        price, greeks = lsm.lsm_american_option_with_greeks(
            S0, K, r, sigma, T,
            steps=steps, batch_size=batch_size, max_paths=max_paths,
            tolerance=tolerance, option_type=option_type,
            greek_shift=greek_shift, adaptive_batching=adaptive_batching,
            min_batches=min_batches, max_cv=max_cv
        )
        
        # Convert numpy types to Python native types for JSON serialization
        import numpy as np
        if isinstance(price, np.floating):
            price = float(price)
        if isinstance(greeks, dict):
            for key, value in greeks.items():
                if isinstance(value, np.floating):
                    greeks[key] = float(value)
                elif isinstance(value, np.integer):
                    greeks[key] = int(value)
        
        return jsonify({
            "price": price,
            "greeks": greeks
        }), 200
    except Exception as e:
        import traceback
        return jsonify({"error": f"LSM calculation failed: {str(e)}", "trace": traceback.format_exc()}), 500

@app.route("/api/lsmc/validate_ticker", methods=["POST"])
def lsmc_validate_ticker():
    """Validate ticker symbol and return basic info for LSMC workflow"""
    data = request.get_json(force=True)
    ticker = data.get("ticker", "").upper().strip()
    
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    try:
        # Get ticker data to validate it exists
        ticker_info = app.yahoo_finance_service.get_ticker_data(ticker)
        if not ticker_info:
            return jsonify({"error": f"Ticker {ticker} not found or invalid"}), 404
        
        # Check if options are available
        options_chain = app.options_data_service.fetch_options_chain(ticker)
        has_options = bool(options_chain and len(options_chain) > 0)
        
        return jsonify({
            "ticker": ticker,
            "current_price": ticker_info.get("current_price"),
            "company_name": ticker_info.get("company_name", ""),
            "has_options": has_options,
            "options_expirations": list(options_chain.keys()) if options_chain else []
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating ticker {ticker}: {e}")
        return jsonify({"error": f"Error validating ticker: {str(e)}"}), 500

@app.route("/api/lsmc/options_chain/<ticker>", methods=["GET"])
def lsmc_get_options_chain(ticker):
    """Get options chain data formatted for LSMC workflow"""
    ticker = ticker.upper().strip()
    
    # Helper functions to safely convert values
    def safe_int(value, default=0):
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    def safe_int_preserve_none(value, default=None):
        """Safe int conversion that preserves None values for open interest"""
        if value is None:
            return None
        try:
            result = int(float(value))
            return result if result > 0 else 0  # Only return 0 if actually zero, not None
        except (ValueError, TypeError):
            return default
    
    def safe_float(value, default=0.0):
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def create_complete_strike_range(calls, puts, current_price):
        """Create a complete strike range with 0.00 for missing strikes"""
        # Get all existing strikes
        existing_strikes = set()
        for call in calls:
            strike = safe_float(call.get('strike'))
            if strike > 0:
                existing_strikes.add(strike)
        for put in puts:
            strike = safe_float(put.get('strike'))
            if strike > 0:
                existing_strikes.add(strike)
        
        if not existing_strikes:
            return []
        
        # Create a comprehensive strike range
        min_strike = min(existing_strikes)
        max_strike = max(existing_strikes)
        
        # Generate strikes in 2.5 increments for most ranges, 5 for higher strikes
        strikes = []
        strike = min_strike
        while strike <= max_strike:
            strikes.append(strike)
            if strike < 50:
                strike += 2.5
            elif strike < 100:
                strike += 5
            elif strike < 200:
                strike += 5
            else:
                strike += 10
        
        return sorted(strikes)
    
    def find_option_by_strike(options, target_strike):
        """Find option with matching strike price"""
        for option in options:
            if abs(safe_float(option.get('strike')) - target_strike) < 0.01:
                return option
        return None
    
    try:
        options_chain = app.options_data_service.fetch_options_chain(ticker)
        if not options_chain:
            return jsonify({"error": f"No options data available for {ticker}"}), 404
        
        # Get current stock price
        ticker_info = app.yahoo_finance_service.get_ticker_data(ticker)
        current_price = ticker_info.get("current_price") if ticker_info else None
        
        # Format options data for LSMC workflow
        formatted_options = {}
        for expiry_date, chain_data in options_chain.items():
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])
            
            # Create complete strike range
            all_strikes = create_complete_strike_range(calls, puts, current_price)
            
            # Create complete calls list with 0.00 for missing strikes
            formatted_calls = []
            for strike in all_strikes:
                existing_call = find_option_by_strike(calls, strike)
                if existing_call:
                    try:
                        formatted_calls.append({
                            "strike": safe_float(existing_call.get('strike')),
                            "lastPrice": safe_float(existing_call.get('lastPrice')),
                            "change": safe_float(existing_call.get('change')),
                            "percentChange": safe_float(existing_call.get('percentChange')),
                            "bid": safe_float(existing_call.get('bid')),
                            "ask": safe_float(existing_call.get('ask')),
                            "volume": safe_int(existing_call.get('volume')),
                            "openInterest": safe_int_preserve_none(existing_call.get('openInterest')),
                            "impliedVolatility": safe_float(existing_call.get('impliedVolatility'), 0.3),
                            "option_type": "call"
                        })
                    except Exception as e:
                        logger.warning(f"Skipping call option due to data conversion error: {e}")
                        formatted_calls.append({
                            "strike": strike,
                            "lastPrice": 0.0,
                            "change": 0.0,
                            "percentChange": 0.0,
                            "bid": 0.0,
                            "ask": 0.0,
                            "volume": 0,
                            "openInterest": 0,
                            "impliedVolatility": 0.3,
                            "option_type": "call"
                        })
                else:
                    # Create placeholder for missing strike
                    formatted_calls.append({
                        "strike": strike,
                        "lastPrice": 0.0,
                        "change": 0.0,
                        "percentChange": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "volume": 0,
                        "openInterest": 0,
                        "impliedVolatility": 0.3,
                        "option_type": "call"
                    })
            
            # Create complete puts list with 0.00 for missing strikes
            formatted_puts = []
            for strike in all_strikes:
                existing_put = find_option_by_strike(puts, strike)
                if existing_put:
                    try:
                        formatted_puts.append({
                            "strike": safe_float(existing_put.get('strike')),
                            "lastPrice": safe_float(existing_put.get('lastPrice')),
                            "change": safe_float(existing_put.get('change')),
                            "percentChange": safe_float(existing_put.get('percentChange')),
                            "bid": safe_float(existing_put.get('bid')),
                            "ask": safe_float(existing_put.get('ask')),
                            "volume": safe_int(existing_put.get('volume')),
                            "openInterest": safe_int_preserve_none(existing_put.get('openInterest')),
                            "impliedVolatility": safe_float(existing_put.get('impliedVolatility'), 0.3),
                            "option_type": "put"
                        })
                    except Exception as e:
                        logger.warning(f"Skipping put option due to data conversion error: {e}")
                        formatted_puts.append({
                            "strike": strike,
                            "lastPrice": 0.0,
                            "change": 0.0,
                            "percentChange": 0.0,
                            "bid": 0.0,
                            "ask": 0.0,
                            "volume": 0,
                            "openInterest": 0,
                            "impliedVolatility": 0.3,
                            "option_type": "put"
                        })
                else:
                    # Create placeholder for missing strike
                    formatted_puts.append({
                        "strike": strike,
                        "lastPrice": 0.0,
                        "change": 0.0,
                        "percentChange": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "volume": 0,
                        "openInterest": 0,
                        "impliedVolatility": 0.3,
                        "option_type": "put"
                    })
            
            formatted_options[expiry_date] = {
                "calls": formatted_calls,
                "puts": formatted_puts,
                "total_calls": len(formatted_calls),
                "total_puts": len(formatted_puts)
            }
        
        return jsonify({
            "ticker": ticker,
            "current_price": current_price,
            "options_chain": formatted_options,
            "expiration_dates": list(formatted_options.keys())
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting options chain for {ticker}: {e}")
        return jsonify({"error": f"Error retrieving options chain: {str(e)}"}), 500

@app.route("/api/lsmc/simulate", methods=["POST"])
def lsmc_simulate():
    """Run LSMC simulation for selected options"""
    data = request.get_json(force=True)
    
    # Validate required parameters
    required_params = ["ticker", "selected_options", "simulation_params"]
    missing = [p for p in required_params if p not in data]
    if missing:
        return jsonify({"error": f"Missing required parameters: {', '.join(missing)}"}), 400
    
    ticker = data["ticker"].upper()
    selected_options = data["selected_options"]
    simulation_params = data["simulation_params"]
    
    if not selected_options:
        return jsonify({"error": "No options selected for simulation"}), 400
    
    try:
        # Get current stock price
        ticker_info = app.yahoo_finance_service.get_ticker_data(ticker)
        if not ticker_info:
            return jsonify({"error": f"Could not get current price for {ticker}"}), 400
        
        current_price = ticker_info['current_price']
        
        # Run LSMC simulation for each selected option
        results = []
        lsm = LSMAmericanOptions()
        
        for option in selected_options:
            try:
                # Extract option parameters
                strike_price = float(option["strike"])
                option_type = option["option_type"].lower()
                expiry_date = option["expiry_date"]
                market_price = float(option.get("lastPrice", option.get("market_price", 0)))
                
                # Handle implied volatility with minimum threshold
                raw_iv = float(option.get("impliedVolatility", option.get("implied_volatility", 0.3)))
                # Set minimum IV to 0.05 (5%) to avoid unrealistic pricing
                implied_volatility = max(raw_iv, 0.05) if raw_iv > 0 else 0.3
                
                # Calculate time to expiration
                from datetime import datetime
                expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                current_datetime = datetime.now()
                time_to_expiration = (expiry_datetime - current_datetime).days / 365.0
                
                if time_to_expiration <= 0:
                    results.append({
                        "strike": strike_price,
                        "option_type": option_type,
                        "expiry_date": expiry_date,
                        "error": "Option has expired"
                    })
                    continue
                
                # Skip options with zero market price (likely placeholder options)
                if market_price <= 0:
                    results.append({
                        "strike": strike_price,
                        "option_type": option_type,
                        "expiry_date": expiry_date,
                        "error": "Option has no market price"
                    })
                    continue
                
                # Get simulation parameters
                risk_free_rate = float(simulation_params.get("risk_free_rate", 0.01))
                steps = int(simulation_params.get("steps", 50))
                batch_size = int(simulation_params.get("batch_size", 5000))
                max_paths = int(simulation_params.get("max_paths", 100000))
                tolerance = float(simulation_params.get("tolerance", 0.005))
                greek_shift = float(simulation_params.get("greek_shift", 0.01))
                
                # Run LSMC simulation
                price, greeks = lsm.lsm_american_option_with_greeks(
                    current_price, strike_price, risk_free_rate, implied_volatility, time_to_expiration,
                    steps=steps, batch_size=batch_size, max_paths=max_paths,
                    tolerance=tolerance, option_type=option_type,
                    greek_shift=greek_shift
                )
                
                # Convert numpy types to Python native types
                import numpy as np
                if isinstance(price, np.floating):
                    price = float(price)
                if isinstance(greeks, dict):
                    for key, value in greeks.items():
                        if isinstance(value, np.floating):
                            greeks[key] = float(value)
                        elif isinstance(value, np.integer):
                            greeks[key] = int(value)
                
                # Calculate additional metrics
                undervaluation_percent = ((price - market_price) / market_price * 100) if market_price > 0 else 0
                
                result = {
                    "strike": strike_price,
                    "option_type": option_type,
                    "expiry_date": expiry_date,
                    "market_price": market_price,
                    "lsmc_price": price,
                    "undervaluation_percent": undervaluation_percent,
                    "greeks": greeks,
                    "time_to_expiration": time_to_expiration,
                    "implied_volatility": implied_volatility,
                    "risk_free_rate": risk_free_rate
                }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error simulating option {ticker} {strike_price} {option_type}: {e}")
                results.append({
                    "strike": strike_price,
                    "option_type": option_type,
                    "expiry_date": expiry_date,
                    "error": str(e)
                })
        
        # Save simulation results to database
        simulation_data = {
            "ticker": ticker,
            "current_price": current_price,
            "simulation_params": simulation_params,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        sim_id = app.db_manager.save_simulation_result(
            ticker, 
            f"LSMC_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
            json.dumps(simulation_data)
        )
        
        return jsonify({
            "message": "LSMC simulation completed",
            "simulation_id": sim_id,
            "ticker": ticker,
            "current_price": current_price,
            "results": results,
            "total_options": len(selected_options),
            "successful_simulations": len([r for r in results if "error" not in r])
        }), 200
        
    except Exception as e:
        logger.error(f"Error in LSMC simulation: {e}", exc_info=True)
        return jsonify({"error": f"LSMC simulation failed: {str(e)}"}), 500

@app.route("/lsmc_dashboard")
def lsmc_dashboard():
    return render_template('lsmc_dashboard.html')

@app.route("/watchlists")
def watchlists():
    app.logger.info("Accessing /watchlists route")
    return render_template('watchlists.html')

# Stock database management endpoints
@app.route("/api/stocks/search", methods=["GET"])
def search_stocks():
    """Search stocks and ETFs by symbol or company name."""
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify([])
    
    try:
        results = app.stock_data_service.search_stocks(query, limit)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route("/api/stocks/validate/<symbol>", methods=["GET"])
def validate_stock_symbol(symbol):
    """Validate if a stock symbol exists in our database."""
    try:
        is_valid = app.stock_data_service.validate_ticker(symbol)
        stock_info = app.stock_data_service.get_stock_info(symbol) if is_valid else None
        return jsonify({
            'valid': is_valid,
            'stock_info': stock_info
        })
    except Exception as e:
        logger.error(f"Error validating stock symbol {symbol}: {e}")
        return jsonify({'error': 'Validation failed'}), 500

@app.route("/api/stocks/database/update", methods=["POST"])
def update_stock_database():
    """Update the stock database with fresh data."""
    try:
        force_refresh = request.json.get('force_refresh', False) if request.is_json else False
        count = app.stock_data_service.update_stock_database(force_refresh=force_refresh)
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Database updated with {count} stocks/ETFs'
        })
    except Exception as e:
        logger.error(f"Error updating stock database: {e}")
        return jsonify({'error': 'Database update failed'}), 500

@app.route("/api/stocks/database/stats", methods=["GET"])
def get_stock_database_stats():
    """Get statistics about the stock database."""
    try:
        stats = app.stock_data_service.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stock database stats: {e}")
        return jsonify({'error': 'Failed to get database stats'}), 500

@app.route("/api/stocks/info/<symbol>", methods=["GET"])
def get_stock_info(symbol):
    """Get detailed information about a stock/ETF."""
    try:
        stock_info = app.stock_data_service.get_stock_info(symbol)
        if stock_info:
            return jsonify(stock_info)
        else:
            return jsonify({'error': 'Stock not found'}), 404
    except Exception as e:
        logger.error(f"Error getting stock info for {symbol}: {e}")
        return jsonify({'error': 'Failed to get stock info'}), 500

@app.route("/api/chart/<ticker>", methods=["GET"])
def api_chart_data(ticker):
    """
    Returns historical OHLCV data and EMAs for a ticker and interval.
    Query params:
      - interval: 4h, 1d, 1wk, 1mo (default: 4h)
      - period: 6mo, 1y, etc. (default: 6mo)
    """
    from flask import request
    ticker = ticker.upper()
    interval = request.args.get("interval", "4h")
    period = request.args.get("period", "6mo")

    # Map user-friendly intervals to yfinance intervals
    interval_map = {
        "4h": "4h",
        "1d": "1d",
        "1wk": "1wk",
        "1mo": "1mo"
    }
    yf_interval = interval_map.get(interval, "4h")

    # Use YahooFinanceService to fetch data
    try:
        hist = app.yahoo_finance_service.get_historical_data(ticker, period=period, interval=yf_interval)
        if not hist:
            return jsonify({"error": "No data found for this ticker/interval."}), 404
        import pandas as pd
        df = pd.DataFrame(hist)
        if df.empty or 'Close' not in df.columns:
            return jsonify({"error": "No price data found."}), 404
        # Calculate EMAs
        df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        # Prepare output
        chart_data = df.to_dict(orient='records')
        return jsonify({
            "ticker": ticker,
            "interval": interval,
            "period": period,
            "data": chart_data
        })
    except Exception as e:
        import logging
        logging.error(f"Error in /api/chart/{ticker}: {e}")
        return jsonify({"error": str(e)}), 500

def run_app():
    app.run(debug=True, port=5002, use_reloader=False)

if __name__ == "__main__":
    run_app()
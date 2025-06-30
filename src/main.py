from flask import Flask, render_template_string, request, redirect, url_for, flash, render_template
import logging
from src.storage.url_manager import URLManager
from src.scraper.scraper_engine import ScraperEngine
from src.storage.data_storage import DataStorage
from src.database.database_manager import DatabaseManager
from src.database.migration import MigrationManager
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Flask to find templates and static files in the root directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)
app.secret_key = 'finviz_secret_key'

# Initialize database and migration
db_manager = DatabaseManager()
migration_manager = MigrationManager(db_manager)

# Perform migration if needed
try:
    migration_results = migration_manager.perform_migration()
    if migration_results['migration_performed']:
        logger.info("Database migration completed successfully")
        if migration_results.get('errors'):
            logger.warning(f"Migration completed with errors: {migration_results['errors']}")
except Exception as e:
    logger.error(f"Error during migration: {e}")

# Initialize application components
url_manager = URLManager(db_manager)
scraper_engine = ScraperEngine(db_manager, url_manager)
data_storage = DataStorage(db_manager, url_manager)

HTML_TEMPLATE = """
<!DOCTYPE html>
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
                <h3>Saved URLs</h3>
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
                                                Force scrape (bypass deduplication)
                                            </label>
                                        </div>
                                        <button type="submit" class="btn btn-primary">Scrape</button>
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
                        <p style="font-size: 1.2em; margin-bottom: 10px;">No URLs saved yet</p>
                        <p>Add your first Finviz URL above to get started</p>
                    </div>
                {% endif %}
            </div>
            
            {% if results %}
            <div class="results-section">
                <h3>Scraping Results for "{{ results.name }}"</h3>
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

@app.route("/", methods=["GET"])
def index():
    urls = url_manager.list_urls()
    return render_template('dashboard.html', urls=urls, results=None)

@app.route("/add_url", methods=["POST"])
def add_url():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not url:
        flash("Both name and URL are required.")
        return redirect(url_for('index'))
    if not scraper_engine.validate_finviz_url(url):
        flash("Invalid Finviz screener URL.")
        return redirect(url_for('index'))
    
    success = url_manager.save_url(name, url)
    if success:
        flash(f"Saved URL '{name}'.")
    else:
        flash(f"Failed to save URL '{name}'. Name may already exist.")
    return redirect(url_for('index'))

@app.route("/scrape", methods=["POST"])
def scrape():
    name = request.form.get("name", "").strip()
    force_scrape = request.form.get("force_scrape", "false").lower() == "true"
    
    if not url_manager.url_exists(name):
        flash("URL not found.")
        return redirect(url_for('index'))
    
    try:
        # Use the new scraper engine with deduplication
        logger.info(f"Starting scraping for URL '{name}' (force_scrape: {force_scrape})")
        
        scrape_result = scraper_engine.scrape_url(name, force_scrape=force_scrape)
        
        if scrape_result['status'] == 'skipped':
            # Get previous results from database when scraping is skipped
            previous_tickers = data_storage.get_tickers_for_url(name)
            if previous_tickers:
                flash(f"Scraping skipped: {scrape_result['reason']}. Showing previous results.")
                results = {"name": name, "tickers": previous_tickers, "status": "skipped", "reason": scrape_result['reason']}
            else:
                flash(f"Scraping skipped: {scrape_result['reason']}. No previous results found.")
                results = {"name": name, "tickers": [], "status": "skipped", "reason": scrape_result['reason']}
        elif scrape_result['status'] == 'completed':
            tickers = scrape_result['tickers']
            if tickers:
                # Save to database and CSV
                csv_path = data_storage.save_tickers_to_csv(name, tickers)
                if csv_path:
                    flash(f"Successfully scraped {len(tickers)} tickers. Data saved to database and CSV.")
                else:
                    flash(f"Scraped {len(tickers)} tickers but failed to save data.")
            else:
                flash("No tickers found on the page.")
            
            results = {"name": name, "tickers": tickers, "status": "completed"}
        else:
            flash(f"Scraping failed: {scrape_result.get('reason', 'Unknown error')}")
            results = {"name": name, "tickers": [], "status": "failed", "reason": scrape_result.get('reason')}
        
        urls = url_manager.list_urls()
        return render_template('dashboard.html', urls=urls, results=results)
        
    except Exception as e:
        error_msg = f"Scraping failed: {str(e)}"
        logger.error(error_msg)
        flash(error_msg)
        return redirect(url_for('index'))

@app.route("/edit_url/<name>", methods=["GET"])
def edit_url(name):
    url_data = url_manager.get_url_by_name(name)
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
    
    if not scraper_engine.validate_finviz_url(new_url):
        flash("Invalid Finviz screener URL.")
        return redirect(url_for('edit_url', name=old_name))
    
    success = url_manager.update_url(old_name, new_name, new_url)
    if success:
        flash(f"Successfully updated URL '{old_name}' to '{new_name}'.")
        return redirect(url_for('index'))
    else:
        flash("Failed to update URL. Name may already exist or URL not found.")
        return redirect(url_for('edit_url', name=old_name))

@app.route("/delete_url/<name>", methods=["GET"])
def delete_url(name):
    url_data = url_manager.get_url_by_name(name)
    if not url_data:
        flash("URL not found.")
        return redirect(url_for('index'))
    
    # Delete the URL
    success = url_manager.delete_url(name)
    if success:
        flash(f"Successfully deleted URL '{name}'.")
    else:
        flash("Failed to delete URL.")
    
    return redirect(url_for('index'))

@app.route("/database_stats", methods=["GET"])
def database_stats():
    """Display database statistics."""
    try:
        db_stats = db_manager.get_database_stats()
        url_stats = url_manager.get_url_stats()
        storage_stats = data_storage.get_storage_stats()
        
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
        csv_path = data_storage.export_to_csv(name)
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
        total_urls = len(url_manager.list_urls())
        
        # Get scraping session statistics
        session_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_sessions,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_sessions
            FROM scraping_sessions
        """)
        
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
        recent_sessions = db_manager.execute_query("""
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
        """)
        
        # Get top URLs by activity
        top_urls = db_manager.execute_query("""
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
        """)
        
        return render_template('stats.html',
        total_urls=total_urls,
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

if __name__ == "__main__":
    app.run(debug=True, port=5001) 
import pytest
from src.main import app, url_manager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Clear URLs before each test by deleting from database
        try:
            url_manager.db_manager.execute_update("DELETE FROM urls")
            url_manager.db_manager.execute_update("DELETE FROM scraping_sessions")
            url_manager.db_manager.execute_update("DELETE FROM ticker_results")
        except:
            pass  # Ignore errors if tables don't exist
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Add New URL" in response.data

def test_add_url_success(client):
    response = client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    assert b"Saved URL" in response.data
    assert b"TPS SCANNER" in response.data

def test_add_url_invalid(client):
    response = client.post('/add_url', data={
        'name': 'Invalid',
        'url': 'https://google.com/'
    }, follow_redirects=True)
    assert b"Invalid Finviz screener URL" in response.data

    response = client.post('/add_url', data={
        'name': '',
        'url': ''
    }, follow_redirects=True)
    assert b"Both name and URL are required" in response.data

# Note: The scrape endpoint test is a smoke test (does not hit real Finviz)
def test_scrape_endpoint(client):
    # Add a valid URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    # Now trigger scrape (will likely fail unless mocked, but should not 500)
    response = client.post('/scrape', data={'name': 'TPS SCANNER'}, follow_redirects=True)
    assert response.status_code == 200
    # Should show either results or a flash error
    assert b"TPS SCANNER" in response.data or b"Scraping failed" in response.data

# New tests for URL management features
def test_edit_url_page_success(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Access edit page
    response = client.get('/edit_url/TPS SCANNER')
    assert response.status_code == 200
    assert b"Edit URL" in response.data
    assert b"TPS SCANNER" in response.data
    assert b"https://finviz.com/screener.ashx" in response.data

def test_edit_url_page_not_found(client):
    response = client.get('/edit_url/nonexistent', follow_redirects=True)
    assert b"URL not found" in response.data

def test_update_url_success(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Update the URL
    response = client.post('/update_url', data={
        'old_name': 'TPS SCANNER',
        'name': 'UPDATED SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=111&f=cap_large'
    }, follow_redirects=True)
    
    assert b"Successfully updated URL" in response.data
    assert b"UPDATED SCANNER" in response.data

def test_update_url_invalid_data(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Try to update with empty fields
    response = client.post('/update_url', data={
        'old_name': 'TPS SCANNER',
        'name': '',
        'url': ''
    }, follow_redirects=True)
    
    assert b"All fields are required" in response.data

def test_update_url_invalid_url(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Try to update with invalid URL
    response = client.post('/update_url', data={
        'old_name': 'TPS SCANNER',
        'name': 'UPDATED SCANNER',
        'url': 'https://google.com/'
    }, follow_redirects=True)
    
    assert b"Invalid Finviz screener URL" in response.data

def test_delete_url_success(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Delete the URL
    response = client.get('/delete_url/TPS SCANNER', follow_redirects=True)
    assert b"Successfully deleted URL" in response.data
    # The URL should be deleted from the table, but the flash message will contain the name
    # Check that the table shows "No URLs saved yet" instead of the URL
    assert b"No URLs saved yet" in response.data

def test_delete_url_not_found(client):
    response = client.get('/delete_url/nonexistent', follow_redirects=True)
    assert b"URL not found" in response.data

def test_main_page_has_edit_delete_buttons(client):
    # Add a URL first
    client.post('/add_url', data={
        'name': 'TPS SCANNER',
        'url': 'https://finviz.com/screener.ashx?v=171&f=sh_avgvol_o300,sh_price_o15,sh_short_o15,ta_highlow52w_b0to10h&ft=4'
    }, follow_redirects=True)
    
    # Check main page has edit/delete buttons
    response = client.get('/')
    assert b"Edit" in response.data
    assert b"Delete" in response.data
    assert b"data-url-name" in response.data
    assert b"data-url" in response.data

def test_force_scrape_functionality(client):
    """Test that force-scrape checkbox works correctly."""
    # Add a valid URL first
    client.post('/add_url', data={
        'name': 'FORCE TEST',
        'url': 'https://finviz.com/screener.ashx?v=171&f=cap_large'
    }, follow_redirects=True)
    
    # Test normal scrape (should respect deduplication)
    response = client.post('/scrape', data={
        'name': 'FORCE TEST',
        'force_scrape': 'false'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Test force scrape (should bypass deduplication)
    response = client.post('/scrape', data={
        'name': 'FORCE TEST',
        'force_scrape': 'true'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Verify the page contains force-scrape checkbox
    response = client.get('/')
    assert b'force_scrape' in response.data
    assert b'Force scrape (bypass deduplication)' in response.data

def test_stats_page(client):
    """Test that the stats page displays deduplication effectiveness."""
    # Add a URL and perform some scraping
    client.post('/add_url', data={
        'name': 'STATS TEST',
        'url': 'https://finviz.com/screener.ashx?v=171&f=cap_large'
    }, follow_redirects=True)
    
    # Perform a scrape
    client.post('/scrape', data={
        'name': 'STATS TEST',
        'force_scrape': 'false'
    }, follow_redirects=True)
    
    # Check the stats page
    response = client.get('/stats')
    assert response.status_code == 200
    assert b'Scraping Statistics' in response.data
    assert b'Deduplication Effectiveness' in response.data
    assert b'Total URLs' in response.data
    assert b'Total Sessions' in response.data
    assert b'Skipped (Dedup)' in response.data
    assert b'Deduplication Rate' in response.data 
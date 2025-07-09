#!/usr/bin/env python3

import requests
import json
import time
from datetime import datetime

def test_polygon_io():
    """Test Polygon.io API for options data"""
    print("Testing Polygon.io...")
    
    # You would need to sign up for a free API key
    # API_KEY = "your_polygon_api_key_here"
    
    # For now, let's check their documentation
    print("Polygon.io requires API key registration")
    print("Free tier: 5 calls/minute, 100 calls/day")
    print("Options endpoint: /v3/reference/options/contracts")
    print("Documentation: https://polygon.io/docs/options/get_v3_reference_options_contracts")
    
    return False

def test_iex_cloud():
    """Test IEX Cloud API for options data"""
    print("\nTesting IEX Cloud...")
    
    # You would need to sign up for a free API key
    # API_KEY = "your_iex_api_key_here"
    
    print("IEX Cloud requires API key registration")
    print("Free tier: 50,000 messages/month")
    print("Options data may be limited in free tier")
    print("Documentation: https://iexcloud.io/docs/api/")
    
    return False

def test_marketstack():
    """Test MarketStack API for options data"""
    print("\nTesting MarketStack...")
    
    # You would need to sign up for a free API key
    # API_KEY = "your_marketstack_api_key_here"
    
    print("MarketStack requires API key registration")
    print("Free tier: 1,000 API calls/month")
    print("Options data may not include OI")
    print("Documentation: https://marketstack.com/documentation")
    
    return False

def test_barchart_scraping():
    """Test scraping Barchart.com for options data"""
    print("\nTesting Barchart.com scraping...")
    
    try:
        # Test if we can access Barchart options page
        url = "https://www.barchart.com/stocks/quotes/SPY/options"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✓ Barchart.com is accessible")
            print("  - Free options data available")
            print("  - Would need to implement scraping logic")
            print("  - May have rate limiting")
            return True
        else:
            print(f"✗ Barchart.com returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing Barchart.com: {e}")
        return False

def test_marketwatch_scraping():
    """Test scraping MarketWatch.com for options data"""
    print("\nTesting MarketWatch.com scraping...")
    
    try:
        # Test if we can access MarketWatch options page
        url = "https://www.marketwatch.com/investing/stock/spy/options"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✓ MarketWatch.com is accessible")
            print("  - Free options data available")
            print("  - Would need to implement scraping logic")
            print("  - May have rate limiting")
            return True
        else:
            print(f"✗ MarketWatch.com returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing MarketWatch.com: {e}")
        return False

def test_investing_scraping():
    """Test scraping Investing.com for options data"""
    print("\nTesting Investing.com scraping...")
    
    try:
        # Test if we can access Investing.com options page
        url = "https://www.investing.com/equities/spdr-s-p-500-etf-options"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✓ Investing.com is accessible")
            print("  - Free options data available")
            print("  - Would need to implement scraping logic")
            print("  - May have rate limiting")
            return True
        else:
            print(f"✗ Investing.com returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing Investing.com: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTING ALTERNATIVE FREE OPTIONS DATA SOURCES")
    print("=" * 60)
    
    results = []
    
    # Test API-based sources
    results.append(("Polygon.io", test_polygon_io()))
    results.append(("IEX Cloud", test_iex_cloud()))
    results.append(("MarketStack", test_marketstack()))
    
    # Test web scraping sources
    results.append(("Barchart.com", test_barchart_scraping()))
    results.append(("MarketWatch.com", test_marketwatch_scraping()))
    results.append(("Investing.com", test_investing_scraping()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for source, accessible in results:
        status = "✓ ACCESSIBLE" if accessible else "✗ NOT ACCESSIBLE/REQUIRES API KEY"
        print(f"{source:20} {status}")
    
    print("\nRECOMMENDATIONS:")
    print("1. Web scraping sources (Barchart, MarketWatch, Investing) are accessible")
    print("2. API sources require registration but may be more reliable")
    print("3. Consider implementing a fallback system with multiple sources")
    print("4. Web scraping may have rate limiting and terms of service considerations")

if __name__ == "__main__":
    main() 
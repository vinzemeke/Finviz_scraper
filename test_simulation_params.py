#!/usr/bin/env python3
"""
Test script to simulate the frontend behavior and check what parameters 
are being passed from the strike selection page to the simulation API.
"""

import json
import requests
import sys

def test_simulation_parameters():
    """Test the simulation API with parameters that would be sent from the frontend."""
    
    base_url = "http://localhost:5001"
    
    # Test 1: Get ticker details for AAPL
    print("=== Test 1: Getting AAPL ticker details ===")
    try:
        response = requests.get(f"{base_url}/api/ticker_details/AAPL")
        if response.status_code == 200:
            ticker_data = response.json()
            print(f"Current price: ${ticker_data.get('current_price', 'N/A')}")
            print(f"Volume: {ticker_data.get('volume', 'N/A')}")
            print(f"52-week range: {ticker_data.get('fifty_two_week_range', 'N/A')}")
        else:
            print(f"Failed to get ticker details: {response.status_code}")
    except Exception as e:
        print(f"Error getting ticker details: {e}")
    
    print()
    
    # Test 2: Get options data for AAPL
    print("=== Test 2: Getting AAPL options data ===")
    try:
        response = requests.get(f"{base_url}/api/options/AAPL")
        if response.status_code == 200:
            options_data = response.json()
            expiry_dates = list(options_data.keys())
            print(f"Available expiry dates: {expiry_dates[:3]}...")  # Show first 3
            
            if expiry_dates:
                first_expiry = expiry_dates[0]
                expiry_data = options_data[first_expiry]
                calls = expiry_data.get('calls', [])
                puts = expiry_data.get('puts', [])
                print(f"First expiry ({first_expiry}): {len(calls)} calls, {len(puts)} puts")
                
                if calls:
                    sample_call = calls[0]
                    print(f"Sample call option: Strike=${sample_call.get('strike')}, "
                          f"LastPrice=${sample_call.get('lastPrice')}, "
                          f"IV={sample_call.get('impliedVolatility')}")
        else:
            print(f"Failed to get options data: {response.status_code}")
    except Exception as e:
        print(f"Error getting options data: {e}")
    
    print()
    
    # Test 3: Simulate the parameters that would be sent from frontend
    print("=== Test 3: Simulating frontend parameters ===")
    
    # This is what the frontend would send based on the getSimulationParams() method
    simulation_params = {
        "options": [
            {
                "ticker": "AAPL",
                "strike_price": 200.0,
                "option_type": "call",
                "expiry_date": "2025-12-19",
                "market_price": 5.25,
                "implied_volatility": 0.25
            }
        ],
        "num_simulations": 1000,
        "risk_free_rate": 0.05,
        "volatility_source": "implied",
        "current_price": 210.0
    }
    
    print("Parameters being sent to /api/simulate:")
    print(json.dumps(simulation_params, indent=2))
    
    # Test 4: Send the simulation request
    print("\n=== Test 4: Sending simulation request ===")
    try:
        response = requests.post(
            f"{base_url}/api/simulate",
            headers={"Content-Type": "application/json"},
            json=simulation_params
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Simulation successful!")
            print(f"Message: {result.get('message')}")
            print(f"Simulation ID: {result.get('simulation_id')}")
            
            # Check the simulation data structure
            sim_data = result.get('simulation_data', {})
            print(f"Ticker: {sim_data.get('ticker')}")
            print(f"Current price: {sim_data.get('current_price')}")
            print(f"Expiry date: {sim_data.get('expiry_date')}")
            print(f"Time to expiration: {sim_data.get('time_to_expiration')}")
            
            options_results = sim_data.get('options_results', [])
            print(f"Number of options results: {len(options_results)}")
            
            if options_results:
                first_result = options_results[0]
                print("First option result:")
                for key, value in first_result.items():
                    print(f"  {key}: {value}")
        else:
            error_data = response.json()
            print(f"Simulation failed: {error_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error during simulation: {e}")

if __name__ == "__main__":
    test_simulation_parameters() 
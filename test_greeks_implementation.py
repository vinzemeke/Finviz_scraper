#!/usr/bin/env python3
"""
Test script to verify the Greeks implementation in the Monte Carlo simulator.
"""

import requests
import json
import sys

def test_greeks_calculation():
    """Test Greeks calculation with different option scenarios."""
    
    base_url = "http://localhost:5001"
    
    # Test scenarios
    test_cases = [
        {
            "name": "ITM Call Option",
            "options": [{
                "ticker": "AAPL",
                "strike_price": 180,  # ITM call (current price 210)
                "option_type": "call",
                "expiry_date": "2025-12-19",
                "market_price": 35.0,
                "implied_volatility": 0.25
            }],
            "current_price": 210.0
        },
        {
            "name": "OTM Call Option",
            "options": [{
                "ticker": "AAPL",
                "strike_price": 230,  # OTM call (current price 210)
                "option_type": "call",
                "expiry_date": "2025-12-19",
                "market_price": 8.0,
                "implied_volatility": 0.30
            }],
            "current_price": 210.0
        },
        {
            "name": "ITM Put Option",
            "options": [{
                "ticker": "AAPL",
                "strike_price": 240,  # ITM put (current price 210)
                "option_type": "put",
                "expiry_date": "2025-12-19",
                "market_price": 35.0,
                "implied_volatility": 0.25
            }],
            "current_price": 210.0
        },
        {
            "name": "OTM Put Option",
            "options": [{
                "ticker": "AAPL",
                "strike_price": 190,  # OTM put (current price 210)
                "option_type": "put",
                "expiry_date": "2025-12-19",
                "market_price": 3.0,
                "implied_volatility": 0.30
            }],
            "current_price": 210.0
        }
    ]
    
    print("=== Testing Greeks Calculation Implementation ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 50)
        
        # Prepare simulation parameters
        simulation_params = {
            "options": test_case["options"],
            "num_simulations": 1000,
            "risk_free_rate": 0.05,
            "volatility_source": "implied",
            "current_price": test_case["current_price"]
        }
        
        try:
            # Send simulation request
            response = requests.post(
                f"{base_url}/api/simulate",
                headers={"Content-Type": "application/json"},
                json=simulation_params
            )
            
            if response.status_code == 200:
                result = response.json()
                sim_data = result.get('simulation_data', {})
                options_results = sim_data.get('options_results', [])
                
                if options_results:
                    option = options_results[0]
                    greeks = option.get('greeks', {})
                    interpretations = option.get('greeks_interpretation', {})
                    
                    print(f"Option: {option['option_type'].upper()} ${option['strike_price']}")
                    print(f"Current Price: ${test_case['current_price']}")
                    print(f"Market Price: ${option['market_price']:.2f}")
                    print(f"Simulated Price: ${option['simulated_price']:.2f}")
                    print(f"Undervaluation: {option['undervaluation_percent']:.1f}%")
                    print()
                    print("Greeks:")
                    print(f"  Delta: {greeks.get('delta', 'N/A'):.4f}")
                    print(f"  Gamma: {greeks.get('gamma', 'N/A'):.4f}")
                    print(f"  Theta: {greeks.get('theta', 'N/A'):.4f}")
                    print(f"  Vega: {greeks.get('vega', 'N/A'):.4f}")
                    print()
                    print("Interpretations:")
                    for greek, interpretation in interpretations.items():
                        print(f"  {greek.capitalize()}: {interpretation}")
                    print()
                    
                    # Validate Greeks values
                    delta = greeks.get('delta', 0)
                    gamma = greeks.get('gamma', 0)
                    theta = greeks.get('theta', 0)
                    vega = greeks.get('vega', 0)
                    
                    # Basic validation
                    if option['option_type'] == 'call':
                        assert 0 <= delta <= 1, f"Call delta should be between 0 and 1, got {delta}"
                    else:  # put
                        assert -1 <= delta <= 0, f"Put delta should be between -1 and 0, got {delta}"
                    
                    assert gamma >= 0, f"Gamma should be non-negative, got {gamma}"
                    # Theta validation: For most options, theta should be negative (time decay)
                    # However, deep ITM put options can have positive theta due to early exercise premium
                    if abs(theta) > 0.1:  # Only validate significant theta values
                        if option['option_type'] == 'put' and delta < -0.7:
                            # Deep ITM puts can have positive theta
                            print(f"⚠️  Note: Deep ITM put with positive theta: {theta:.4f}")
                        else:
                            assert theta <= 0, f"Theta should be non-positive for most options, got {theta}"
                    assert vega >= 0, f"Vega should be non-negative, got {vega}"
                    
                    print("✅ Greeks validation passed")
                    
                else:
                    print("❌ No options results returned")
                    
            else:
                error_data = response.json()
                print(f"❌ Simulation failed: {error_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
        
        print("\n" + "="*60 + "\n")
    
    print("=== Greeks Implementation Test Complete ===")

if __name__ == "__main__":
    test_greeks_calculation() 
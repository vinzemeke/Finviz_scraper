#!/usr/bin/env python3

import yfinance as yf
import json

def test_oi_data():
    tickers = ["AAPL", "TSLA", "SPY", "QQQ"]
    
    for ticker in tickers:
        print(f"\n{'='*50}")
        print(f"Testing open interest data for {ticker}")
        print(f"{'='*50}")
        
        try:
            # Get ticker object
            t = yf.Ticker(ticker)
            
            # Get available expirations
            expirations = t.options
            print(f"Available expirations: {len(expirations)} total")
            
            if expirations:
                # Get first expiration
                first_exp = expirations[0]
                print(f"Testing expiration: {first_exp}")
                
                # Get options chain
                opt = t.option_chain(first_exp)
                
                # Check calls
                calls_data = opt.calls.to_dict('records')
                calls_with_oi = [c for c in calls_data if c.get('openInterest', 0) > 0]
                calls_with_zero_oi = [c for c in calls_data if c.get('openInterest', 0) == 0]
                
                print(f"\nCalls: {len(calls_data)} total, {len(calls_with_oi)} with OI > 0, {len(calls_with_zero_oi)} with OI = 0")
                
                if calls_with_oi:
                    print("Sample calls with OI > 0:")
                    for i, call in enumerate(calls_with_oi[:3]):
                        print(f"  Call {i+1}: Strike={call.get('strike')}, OI={call.get('openInterest')}")
                
                # Check puts
                puts_data = opt.puts.to_dict('records')
                puts_with_oi = [p for p in puts_data if p.get('openInterest', 0) > 0]
                puts_with_zero_oi = [p for p in puts_data if p.get('openInterest', 0) == 0]
                
                print(f"\nPuts: {len(puts_data)} total, {len(puts_with_oi)} with OI > 0, {len(puts_with_zero_oi)} with OI = 0")
                
                if puts_with_oi:
                    print("Sample puts with OI > 0:")
                    for i, put in enumerate(puts_with_oi[:3]):
                        print(f"  Put {i+1}: Strike={put.get('strike')}, OI={put.get('openInterest')}")
                
                # Check for None values
                calls_with_none_oi = [c for c in calls_data if c.get('openInterest') is None]
                puts_with_none_oi = [p for p in puts_data if p.get('openInterest') is None]
                
                print(f"\nCalls with None OI: {len(calls_with_none_oi)}")
                print(f"Puts with None OI: {len(puts_with_none_oi)}")
                
        except Exception as e:
            print(f"Error for {ticker}: {e}")

if __name__ == "__main__":
    test_oi_data() 
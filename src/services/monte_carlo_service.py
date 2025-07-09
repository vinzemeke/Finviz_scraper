import logging
import numpy as np
import json
from datetime import datetime
from typing import List, Dict, Any
from src.services.monte_carlo_core import simulate_gbm, calculate_option_price, calculate_option_price_with_greeks
from src.services.risk_metrics_service import RiskMetricsService
from src.services.greeks_calculator import GreeksCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MonteCarloService:
    def __init__(self):
        self.risk_metrics_service = RiskMetricsService()
        self.greeks_calculator = GreeksCalculator()

    def run_monte_carlo_simulation(self, S0, K, T, r, sigma, option_type='call', num_simulations=10000, N=252, use_greeks=True):
        """
        Orchestrates the Monte Carlo simulation for option pricing.
        Includes basic error handling and parameter validation.
        """
        try:
            if use_greeks:
                option_price, greeks_history, price_paths, option_values = calculate_option_price_with_greeks(
                    S0, K, T, r, sigma, option_type, num_simulations, N
                )
                logging.info(f"Monte Carlo simulation with Greeks completed. Option price: {option_price}")
                return option_price, greeks_history, price_paths, option_values
            else:
                option_price = calculate_option_price(S0, K, T, r, sigma, option_type, num_simulations, N)
                logging.info(f"Monte Carlo simulation completed. Option price: {option_price}")
                return option_price, None, None, None
        except ValueError as ve:
            logging.error(f"Simulation parameter error: {ve}")
            return None, None, None, None
        except Exception as e:
            logging.error(f"An unexpected error occurred during Monte Carlo simulation: {e}")
            return None, None, None, None

    def analyze_single_option_simulation(self, S0: float, K: float, T: float, r: float, sigma: float, option_type: str, num_simulations: int = 10000, N: int = 252, premium: float = 0.0, use_greeks: bool = True) -> dict:
        """
        Runs Monte Carlo simulation and analyzes the results to provide various metrics for a single option.
        Now incorporates Greeks into the simulation itself.
        """
        try:
            # Run simulation with Greeks incorporated
            option_price, greeks_history, price_paths, option_values = self.run_monte_carlo_simulation(
                S0, K, T, r, sigma, option_type, num_simulations, N, use_greeks
            )
            
            if option_price is None:
                return {}

            final_prices = price_paths[-1] if price_paths is not None else None

            # Statistical calculations
            mean_final_price = np.mean(final_prices) if final_prices is not None else S0
            std_final_price = np.std(final_prices) if final_prices is not None else 0
            percentile_5 = np.percentile(final_prices, 5) if final_prices is not None else S0
            percentile_95 = np.percentile(final_prices, 95) if final_prices is not None else S0

            # Risk metrics calculation
            prob_profit = self.risk_metrics_service.calculate_probability_of_profit(final_prices, K, option_type) if final_prices is not None else 0.5
            prob_breakeven = self.risk_metrics_service.calculate_probability_of_breakeven(final_prices, K, premium, option_type) if final_prices is not None else 0.5
            prob_loss = self.risk_metrics_service.calculate_probability_of_loss(final_prices, K, premium, option_type) if final_prices is not None else 0.5
            
            # Calculate max_profit and max_loss for a single option
            if option_type == 'call':
                max_profit = K * 10  # Set a reasonable upper bound instead of infinity
                max_loss = premium
            else:  # put option
                max_profit = K - premium  # Max profit if stock goes to 0
                max_loss = premium
            
            risk_reward_ratio = self.risk_metrics_service.calculate_risk_reward_ratio(max_profit, max_loss)

            # Calculate Greeks using the simulation results if available
            if greeks_history is not None:
                # Use average Greeks from the simulation
                avg_greeks = {
                    'delta': np.mean(greeks_history['delta'][-1, :]),
                    'gamma': np.mean(greeks_history['gamma'][-1, :]),
                    'theta': np.mean(greeks_history['theta'][-1, :]),
                    'vega': np.mean(greeks_history['vega'][-1, :])
                }
                greeks_interpretation = self.greeks_calculator.interpret_greeks(avg_greeks, S0, option_type)
            else:
                # Fallback to analytical Greeks
                avg_greeks = self.greeks_calculator.black_scholes_greeks(S0, K, T, r, sigma, option_type)
                greeks_interpretation = self.greeks_calculator.interpret_greeks(avg_greeks, S0, option_type)

            # Prepare response data
            result = {
                "estimated_option_price": option_price,
                "mean_final_price": mean_final_price,
                "std_final_price": std_final_price,
                "percentile_5_final_price": percentile_5,
                "percentile_95_final_price": percentile_95,
                "probability_of_profit": prob_profit,
                "probability_of_breakeven": prob_breakeven,
                "probability_of_loss": prob_loss,
                "risk_reward_ratio": risk_reward_ratio,
                "greeks": avg_greeks,
                "greeks_interpretation": greeks_interpretation,
                "simulation_method": "greeks_incorporated" if use_greeks else "standard"
            }
            
            # Add price paths if available (but don't include in main response to avoid JSON issues)
            if price_paths is not None:
                result["price_paths"] = price_paths.tolist()
            
            # Add option values if available
            if option_values is not None:
                result["option_values"] = option_values.tolist()
            
            return result
            
        except ValueError as ve:
            logging.error(f"Simulation analysis parameter error: {ve}")
            return {}
        except Exception as e:
            logging.error(f"An unexpected error occurred during simulation analysis: {e}")
            return {}

    def analyze_multiple_options_simulation(self, options_data: List[Dict[str, Any]], S0: float, r: float, num_simulations: int = 10000, N: int = 252, use_greeks: bool = True) -> Dict[str, Any]:
        """
        Runs Monte Carlo simulation and analyzes results for multiple options.
        Now incorporates Greeks into the simulation itself.
        """
        all_options_results = []
        all_terminal_prices = []

        for option_params in options_data:
            ticker = option_params.get('ticker')
            strike_price = option_params.get('strike_price')
            option_type = option_params.get('option_type')
            expiry_date_str = option_params.get('expiry_date')
            market_price = option_params.get('market_price') # Assuming market price is passed for undervaluation
            implied_volatility = option_params.get('implied_volatility') # Assuming IV is passed

            if not all([ticker, strike_price, option_type, expiry_date_str, implied_volatility]) or market_price is None:
                logging.warning(f"Skipping option due to missing parameters: {option_params}")
                continue
            
            # Calculate T (time to expiration) from expiry_date_str
            # Assuming expiry_date_str is in YYYY-MM-DD format
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            today = datetime.now()
            T = (expiry_date - today).days / 365.0
            if T <= 0: # Option has expired or expires today
                logging.warning(f"Skipping option {ticker} {strike_price} {option_type} as it has expired.")
                continue

            try:
                single_option_analysis = self.analyze_single_option_simulation(
                    S0, strike_price, T, r, implied_volatility, option_type, num_simulations, N, premium=market_price, use_greeks=use_greeks
                )
                if single_option_analysis:
                    # Calculate undervaluation percentage
                    estimated_price = single_option_analysis['estimated_option_price']
                    undervaluation_percent = ((estimated_price - market_price) / market_price) * 100 if market_price != 0 else 0

                    option_result = {
                        "ticker": ticker,
                        "strike_price": strike_price,
                        "option_type": option_type,
                        "expiry_date": expiry_date_str,
                        "market_price": market_price,
                        "simulated_price": estimated_price,
                        "undervaluation_percent": undervaluation_percent,
                        "probability_of_profit": single_option_analysis['probability_of_profit'],
                        "probability_of_breakeven": single_option_analysis['probability_of_breakeven'],
                        "probability_of_loss": single_option_analysis['probability_of_loss'],
                        "risk_reward_ratio": single_option_analysis['risk_reward_ratio'],
                        "expected_pnl": (estimated_price - market_price), # Simplified PnL
                        "greeks": single_option_analysis.get('greeks', {}),
                        "greeks_interpretation": single_option_analysis.get('greeks_interpretation', {}),
                        "simulation_method": single_option_analysis.get('simulation_method', 'standard')
                    }
                    all_options_results.append(option_result)
                    
                    # Add price paths if available
                    if 'price_paths' in single_option_analysis:
                        all_terminal_prices.extend(single_option_analysis['price_paths'])

            except Exception as e:
                logging.error(f"Error analyzing single option {ticker} {strike_price} {option_type}: {e}")
                continue
        
        return {
            "options_results": all_options_results,
            "terminal_prices": all_terminal_prices
        }

if __name__ == '__main__':
    # Example Usage:
    mc_service = MonteCarloService()

    # Parameters for a hypothetical option
    S0 = 100      # Initial stock price
    K = 105       # Strike price
    T = 1.0       # Time to expiration in years
    r = 0.05      # Risk-free rate
    sigma = 0.2   # Volatility
    premium = 2.5 # Example premium
    
    # Call option pricing
    call_price, _, _, _ = mc_service.run_monte_carlo_simulation(S0, K, T, r, sigma, option_type='call')
    if call_price is not None:
        print(f"Estimated Call Option Price: {call_price:.2f}")

    # Analyze single option results
    analysis_results = mc_service.analyze_single_option_simulation(S0, K, T, r, sigma, 'call', premium=premium)
    if analysis_results:
        print("\nSingle Option Analysis Results:")
        for key, value in analysis_results.items():
            if key != "price_paths": # Don't print the large array
                print(f"  {key}: {value}")

    # Example for multiple options analysis
    options_to_analyze = [
        {"ticker": "AAPL", "strike_price": 150, "option_type": "call", "expiry_date": "2025-12-19", "market_price": 10.0, "implied_volatility": 0.25},
        {"ticker": "AAPL", "strike_price": 160, "option_type": "put", "expiry_date": "2025-12-19", "market_price": 8.0, "implied_volatility": 0.28},
    ]
    multiple_options_analysis = mc_service.analyze_multiple_options_simulation(options_to_analyze, S0, r)
    if multiple_options_analysis:
        print("\nMultiple Options Analysis Results:")
        print(json.dumps(multiple_options_analysis, indent=2))

    # Put option pricing
    put_price, _, _, _ = mc_service.run_monte_carlo_simulation(S0, K, T, r, sigma, option_type='put')
    if put_price is not None:
        print(f"Estimated Put Option Price: {put_price:.2f}")

    # Example with invalid parameters
    print("\nTesting with invalid parameters:")
    invalid_price, _, _, _ = mc_service.run_monte_carlo_simulation(S0, K, T, r, -0.2, option_type='call')
    if invalid_price is None:
        print("Invalid parameter test passed (returned None).")

    invalid_type_price, _, _, _ = mc_service.run_monte_carlo_simulation(S0, K, T, r, sigma, option_type='invalid')
    if invalid_type_price is None:
        print("Invalid option type test passed (returned None).")

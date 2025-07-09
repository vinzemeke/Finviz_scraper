import numpy as np
import logging
from scipy.stats import norm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def simulate_gbm(S0, mu, sigma, T, N, num_simulations):
    """
    Simulates stock prices using Geometric Brownian Motion (GBM).

    Args:
        S0 (float): Initial stock price.
        mu (float): Expected return (drift).
        sigma (float): Volatility.
        T (float): Time horizon (in years).
        N (int): Number of time steps.
        num_simulations (int): Number of simulation paths.

    Returns:
        numpy.ndarray: Array of simulated stock prices over time.
    """
    if not all(isinstance(arg, (int, float)) and arg >= 0 for arg in [S0, mu, sigma, T, N, num_simulations]):
        logging.error("Invalid input: All simulation parameters must be non-negative numbers.")
        raise ValueError("All simulation parameters must be non-negative numbers.")
    if N <= 0 or num_simulations <= 0:
        logging.error("Invalid input: N and num_simulations must be positive integers.")
        raise ValueError("N and num_simulations must be positive integers.")

    dt = T / N
    Z = np.random.standard_normal((N, num_simulations))
    daily_returns = np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z)
    price_paths = np.zeros((N + 1, num_simulations))
    price_paths[0] = S0
    for t in range(1, N + 1):
        price_paths[t] = price_paths[t-1] * daily_returns[t-1]
    return price_paths

def calculate_black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Calculate Black-Scholes Greeks for a given stock price.
    
    Args:
        S (float): Current stock price
        K (float): Strike price
        T (float): Time to expiration
        r (float): Risk-free rate
        sigma (float): Volatility
        option_type (str): 'call' or 'put'
        
    Returns:
        dict: Dictionary containing delta, gamma, theta, vega
    """
    if T <= 0:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                r * K * np.exp(-r * T) * norm.cdf(d2))
    else:  # put
        delta = norm.cdf(d1) - 1
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                r * K * np.exp(-r * T) * norm.cdf(-d2))
    
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * np.sqrt(T) * norm.pdf(d1)
    
    return {'delta': delta, 'gamma': gamma, 'theta': theta, 'vega': vega}

def calculate_option_price_with_greeks(S0, K, T, r, sigma, option_type='call', num_simulations=10000, N=252):
    """
    Calculates the option price using Monte Carlo simulation with Greeks incorporated.
    This method uses a more sophisticated approach that considers the Greeks' impact
    on option pricing throughout the simulation.

    Args:
        S0 (float): Initial stock price.
        K (float): Strike price.
        T (float): Time to expiration (in years).
        r (float): Risk-free rate.
        sigma (float): Volatility.
        option_type (str): Type of option ('call' or 'put').
        num_simulations (int): Number of simulation paths.
        N (int): Number of time steps.

    Returns:
        tuple: (option_price, greeks_history, price_paths)
    """
    if not all(isinstance(arg, (int, float)) and arg >= 0 for arg in [S0, K, T, r, sigma]):
        logging.error("Invalid input: S0, K, T, r, sigma must be non-negative numbers.")
        raise ValueError("S0, K, T, r, sigma must be non-negative numbers.")
    if option_type not in ['call', 'put']:
        logging.error("Invalid option_type. Must be 'call' or 'put'.")
        raise ValueError("Invalid option_type. Must be 'call' or 'put'.")

    dt = T / N
    price_paths = simulate_gbm(S0, r, sigma, T, N, num_simulations)
    
    # Initialize arrays to store Greeks and option values
    greeks_history = {
        'delta': np.zeros((N + 1, num_simulations)),
        'gamma': np.zeros((N + 1, num_simulations)),
        'theta': np.zeros((N + 1, num_simulations)),
        'vega': np.zeros((N + 1, num_simulations))
    }
    
    option_values = np.zeros((N + 1, num_simulations))
    
    # Calculate initial Greeks and option value
    for sim in range(num_simulations):
        greeks = calculate_black_scholes_greeks(S0, K, T, r, sigma, option_type)
        for greek in ['delta', 'gamma', 'theta', 'vega']:
            greeks_history[greek][0, sim] = greeks[greek]
        
        # Initial option value using Black-Scholes
        if option_type == 'call':
            d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            option_values[0, sim] = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            option_values[0, sim] = K * np.exp(-r * T) * norm.cdf(-d2) - S0 * norm.cdf(-d1)
    
    # Simulate option value evolution using Greeks
    for t in range(1, N + 1):
        time_remaining = T - t * dt
        
        for sim in range(num_simulations):
            current_price = price_paths[t, sim]
            prev_price = price_paths[t-1, sim]
            
            # Calculate Greeks at current price and time
            greeks = calculate_black_scholes_greeks(current_price, K, time_remaining, r, sigma, option_type)
            
            # Store Greeks
            for greek in ['delta', 'gamma', 'theta', 'vega']:
                greeks_history[greek][t, sim] = greeks[greek]
            
            # Update option value using Greeks (Taylor expansion approach)
            price_change = current_price - prev_price
            time_change = dt
            
            # Option value change using Greeks
            delta_effect = greeks['delta'] * price_change
            gamma_effect = 0.5 * greeks['gamma'] * price_change**2
            theta_effect = greeks['theta'] * time_change
            
            # Update option value
            option_values[t, sim] = option_values[t-1, sim] + delta_effect + gamma_effect + theta_effect
            
            # Ensure option value doesn't go below intrinsic value
            if option_type == 'call':
                intrinsic_value = max(current_price - K, 0)
            else:
                intrinsic_value = max(K - current_price, 0)
            
            option_values[t, sim] = max(option_values[t, sim], intrinsic_value)
    
    # Final option price is the discounted average of final option values
    final_option_price = np.exp(-r * T) * np.mean(option_values[-1, :])
    
    return final_option_price, greeks_history, price_paths, option_values

def calculate_option_price(S0, K, T, r, sigma, option_type='call', num_simulations=10000, N=252):
    """
    Calculates the option price using Monte Carlo simulation based on GBM.

    Args:
        S0 (float): Initial stock price.
        K (float): Strike price.
        T (float): Time to expiration (in years).
        r (float): Risk-free rate.
        sigma (float): Volatility.
        option_type (str): Type of option ('call' or 'put').
        num_simulations (int): Number of simulation paths.
        N (int): Number of time steps.

    Returns:
        float: Estimated option price.
    """
    if not all(isinstance(arg, (int, float)) and arg >= 0 for arg in [S0, K, T, r, sigma]):
        logging.error("Invalid input: S0, K, T, r, sigma must be non-negative numbers.")
        raise ValueError("S0, K, T, r, sigma must be non-negative numbers.")
    if option_type not in ['call', 'put']:
        logging.error("Invalid option_type. Must be 'call' or 'put'.")
        raise ValueError("Invalid option_type. Must be 'call' or 'put'.")

    price_paths = simulate_gbm(S0, r, sigma, T, N, num_simulations)
    ST = price_paths[-1]
    
    if option_type == 'call':
        payoffs = np.maximum(ST - K, 0)
    else:
        payoffs = np.maximum(K - ST, 0)
            
    option_price = np.exp(-r * T) * np.mean(payoffs)
    return option_price

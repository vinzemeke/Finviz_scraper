import numpy as np
import logging
from typing import Dict, Tuple
from scipy.stats import norm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GreeksCalculator:
    """
    Calculates option Greeks using both analytical Black-Scholes formulas
    and Monte Carlo finite difference methods.
    """
    
    def __init__(self):
        pass
    
    def black_scholes_greeks(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> Dict[str, float]:
        """
        Calculate option Greeks using analytical Black-Scholes formulas.
        
        Args:
            S (float): Current stock price
            K (float): Strike price
            T (float): Time to expiration (in years)
            r (float): Risk-free rate
            sigma (float): Volatility
            option_type (str): 'call' or 'put'
            
        Returns:
            Dict[str, float]: Dictionary containing delta, gamma, theta, vega
        """
        try:
            if T <= 0:
                raise ValueError("Time to expiration must be positive")
            
            # Calculate d1 and d2
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            # Calculate Greeks
            if option_type.lower() == 'call':
                delta = norm.cdf(d1)
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                        r * K * np.exp(-r * T) * norm.cdf(d2))
            else:  # put option
                delta = norm.cdf(d1) - 1
                theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                        r * K * np.exp(-r * T) * norm.cdf(-d2))
            
            # Gamma is the same for both calls and puts
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            
            # Vega is the same for both calls and puts
            vega = S * np.sqrt(T) * norm.pdf(d1)
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            }
            
        except Exception as e:
            logging.error(f"Error calculating Black-Scholes Greeks: {e}")
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }
    
    def monte_carlo_greeks(self, option_pricer_func, S: float, K: float, T: float, r: float, sigma: float, 
                          option_type: str = 'call', epsilon: float = 0.01) -> Dict[str, float]:
        """
        Calculate option Greeks using Monte Carlo finite difference method.
        
        Args:
            option_pricer_func: Function that calculates option price
            S (float): Current stock price
            K (float): Strike price
            T (float): Time to expiration (in years)
            r (float): Risk-free rate
            sigma (float): Volatility
            option_type (str): 'call' or 'put'
            epsilon (float): Small perturbation for finite difference
            
        Returns:
            Dict[str, float]: Dictionary containing delta, gamma, theta, vega
        """
        try:
            # Base price
            base_price = option_pricer_func(S, K, T, r, sigma, option_type)
            
            # Delta: ∂V/∂S
            price_up = option_pricer_func(S + epsilon, K, T, r, sigma, option_type)
            price_down = option_pricer_func(S - epsilon, K, T, r, sigma, option_type)
            delta = (price_up - price_down) / (2 * epsilon)
            
            # Gamma: ∂²V/∂S²
            gamma = (price_up - 2 * base_price + price_down) / (epsilon ** 2)
            
            # Theta: ∂V/∂T
            price_time_up = option_pricer_func(S, K, T + epsilon, r, sigma, option_type)
            price_time_down = option_pricer_func(S, K, T - epsilon, r, sigma, option_type)
            theta = (price_time_up - price_time_down) / (2 * epsilon)
            
            # Vega: ∂V/∂σ
            price_vol_up = option_pricer_func(S, K, T, r, sigma + epsilon, option_type)
            price_vol_down = option_pricer_func(S, K, T, r, sigma - epsilon, option_type)
            vega = (price_vol_up - price_vol_down) / (2 * epsilon)
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            }
            
        except Exception as e:
            logging.error(f"Error calculating Monte Carlo Greeks: {e}")
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }
    
    def calculate_greeks_for_option(self, S: float, K: float, T: float, r: float, sigma: float, 
                                   option_type: str = 'call', method: str = 'both') -> Dict[str, Dict[str, float]]:
        """
        Calculate Greeks using specified method(s).
        
        Args:
            S (float): Current stock price
            K (float): Strike price
            T (float): Time to expiration (in years)
            r (float): Risk-free rate
            sigma (float): Volatility
            option_type (str): 'call' or 'put'
            method (str): 'analytical', 'monte_carlo', or 'both'
            
        Returns:
            Dict[str, Dict[str, float]]: Greeks calculated by specified method(s)
        """
        result = {}
        
        if method in ['analytical', 'both']:
            result['analytical'] = self.black_scholes_greeks(S, K, T, r, sigma, option_type)
        
        if method in ['monte_carlo', 'both']:
            # For Monte Carlo, we need a pricing function
            # This would typically be passed from the Monte Carlo service
            # For now, we'll use a placeholder
            def placeholder_pricer(S, K, T, r, sigma, option_type):
                # This is a placeholder - in practice, this would be the actual Monte Carlo pricing function
                return 0.0
            
            result['monte_carlo'] = self.monte_carlo_greeks(
                placeholder_pricer, S, K, T, r, sigma, option_type
            )
        
        return result
    
    def interpret_greeks(self, greeks: Dict[str, float], S: float, option_type: str = 'call') -> Dict[str, str]:
        """
        Provide interpretation of what the Greeks mean for the option.
        
        Args:
            greeks (Dict[str, float]): Calculated Greeks
            S (float): Current stock price
            option_type (str): 'call' or 'put'
            
        Returns:
            Dict[str, str]: Interpretations of each Greek
        """
        delta = greeks.get('delta', 0)
        gamma = greeks.get('gamma', 0)
        theta = greeks.get('theta', 0)
        vega = greeks.get('vega', 0)
        
        interpretations = {
            'delta': f"Option value changes by ${delta:.4f} for every $1 change in stock price. "
                    f"{'Long' if delta > 0 else 'Short'} stock exposure.",
            'gamma': f"Delta changes by {gamma:.4f} for every $1 change in stock price. "
                    f"{'High' if gamma > 0.01 else 'Low'} gamma indicates rapid delta changes.",
            'theta': f"Option loses ${abs(theta):.4f} in value per day due to time decay. "
                    f"{'High' if abs(theta) > 0.1 else 'Low'} theta indicates rapid time decay.",
            'vega': f"Option value changes by ${vega:.4f} for every 1% change in volatility. "
                    f"{'High' if vega > 0.1 else 'Low'} vega indicates high volatility sensitivity."
        }
        
        return interpretations

if __name__ == '__main__':
    # Example usage
    calculator = GreeksCalculator()
    
    # Test parameters
    S = 100.0  # Current stock price
    K = 105.0  # Strike price
    T = 0.5    # Time to expiration (6 months)
    r = 0.05   # Risk-free rate
    sigma = 0.2  # Volatility
    
    # Calculate Greeks for a call option
    call_greeks = calculator.black_scholes_greeks(S, K, T, r, sigma, 'call')
    print("Call Option Greeks (Analytical):")
    for greek, value in call_greeks.items():
        print(f"  {greek.capitalize()}: {value:.4f}")
    
    # Calculate Greeks for a put option
    put_greeks = calculator.black_scholes_greeks(S, K, T, r, sigma, 'put')
    print("\nPut Option Greeks (Analytical):")
    for greek, value in put_greeks.items():
        print(f"  {greek.capitalize()}: {value:.4f}")
    
    # Get interpretations
    call_interpretations = calculator.interpret_greeks(call_greeks, S, 'call')
    print("\nCall Option Greek Interpretations:")
    for greek, interpretation in call_interpretations.items():
        print(f"  {greek.capitalize()}: {interpretation}") 
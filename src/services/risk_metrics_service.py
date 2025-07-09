import numpy as np
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RiskMetricsService:
    def __init__(self):
        pass

    def calculate_probability_of_profit(self, final_prices: np.ndarray, strike_price: float, option_type: str) -> float:
        """
        Calculates the probability of profit for an option.

        Args:
            final_prices (np.ndarray): Array of simulated stock prices at expiration.
            strike_price (float): The strike price of the option.
            option_type (str): Type of option ('call' or 'put').

        Returns:
            float: The probability of the option being profitable (between 0 and 1).
        """
        if not isinstance(final_prices, np.ndarray) or final_prices.size == 0:
            logging.error("final_prices must be a non-empty numpy array.")
            return 0.0
        if not isinstance(strike_price, (int, float)) or strike_price < 0:
            logging.error("Strike price must be a non-negative number.")
            return 0.0
        if option_type not in ['call', 'put']:
            logging.error("Invalid option_type. Must be 'call' or 'put'.")
            return 0.0

        if option_type == 'call':
            profitable_outcomes = np.sum(final_prices > strike_price)
        else:  # put option
            profitable_outcomes = np.sum(final_prices < strike_price)

        prob_profit = profitable_outcomes / len(final_prices)
        logging.info(f"Calculated probability of profit: {prob_profit:.4f}")
        return prob_profit

    def calculate_probability_of_breakeven(self, final_prices: np.ndarray, strike_price: float, premium: float, option_type: str) -> float:
        """
        Calculates the probability of breakeven for an option.

        Args:
            final_prices (np.ndarray): Array of simulated stock prices at expiration.
            strike_price (float): The strike price of the option.
            premium (float): The premium paid for the option.
            option_type (str): Type of option ('call' or 'put').

        Returns:
            float: The probability of the option breaking even or being profitable.
        """
        if not isinstance(final_prices, np.ndarray) or final_prices.size == 0:
            logging.error("final_prices must be a non-empty numpy array.")
            return 0.0
        if not isinstance(strike_price, (int, float)) or strike_price < 0:
            logging.error("Strike price must be a non-negative number.")
            return 0.0
        if not isinstance(premium, (int, float)) or premium < 0:
            logging.error("Premium must be a non-negative number.")
            return 0.0
        if option_type not in ['call', 'put']:
            logging.error("Invalid option_type. Must be 'call' or 'put'.")
            return 0.0

        if option_type == 'call':
            breakeven_point = strike_price + premium
            breakeven_outcomes = np.sum(final_prices >= breakeven_point)
        else:  # put option
            breakeven_point = strike_price - premium
            breakeven_outcomes = np.sum(final_prices <= breakeven_point)

        prob_breakeven = breakeven_outcomes / len(final_prices)
        logging.info(f"Calculated probability of breakeven: {prob_breakeven:.4f}")
        return prob_breakeven

    def calculate_probability_of_loss(self, final_prices: np.ndarray, strike_price: float, premium: float, option_type: str) -> float:
        """
        Calculates the probability of loss for an option.

        Args:
            final_prices (np.ndarray): Array of simulated stock prices at expiration.
            strike_price (float): The strike price of the option.
            premium (float): The premium paid for the option.
            option_type (str): Type of option ('call' or 'put').

        Returns:
            float: The probability of the option resulting in a loss.
        """
        if not isinstance(final_prices, np.ndarray) or final_prices.size == 0:
            logging.error("final_prices must be a non-empty numpy array.")
            return 1.0 # Assume 100% loss if no valid data
        if not isinstance(strike_price, (int, float)) or strike_price < 0:
            logging.error("Strike price must be a non-negative number.")
            return 1.0
        if not isinstance(premium, (int, float)) or premium < 0:
            logging.error("Premium must be a non-negative number.")
            return 1.0
        if option_type not in ['call', 'put']:
            logging.error("Invalid option_type. Must be 'call' or 'put'.")
            return 1.0

        if option_type == 'call':
            # Loss occurs if final price is less than or equal to strike price + premium (breakeven point)
            loss_outcomes = np.sum(final_prices < (strike_price + premium))
        else:  # put option
            # Loss occurs if final price is greater than or equal to strike price - premium (breakeven point)
            loss_outcomes = np.sum(final_prices > (strike_price - premium))

        prob_loss = loss_outcomes / len(final_prices)
        logging.info(f"Calculated probability of loss: {prob_loss:.4f}")
        return prob_loss

    def calculate_risk_reward_ratio(self, max_profit: float, max_loss: float) -> float:
        """
        Calculates the risk-reward ratio.

        Args:
            max_profit (float): Maximum potential profit.
            max_loss (float): Maximum potential loss.

        Returns:
            float: The risk-reward ratio. Returns 0 if max_loss is 0 to avoid division by zero.
        """
        if not isinstance(max_profit, (int, float)) or max_profit < 0:
            logging.error("Max profit must be a non-negative number.")
            return 0.0
        if not isinstance(max_loss, (int, float)) or max_loss < 0:
            logging.error("Max loss must be a non-negative number.")
            return 0.0

        if max_loss == 0:
            logging.warning("Max loss is zero, risk-reward ratio is undefined (returning 0).")
            return 0.0

        risk_reward = max_profit / max_loss
        
        # Handle infinity case
        if np.isinf(risk_reward):
            logging.warning("Risk-reward ratio is infinite, returning a large finite value.")
            return 999.99  # Return a large but finite value
        
        logging.info(f"Calculated risk-reward ratio: {risk_reward:.2f}")
        return risk_reward

if __name__ == '__main__':
    # Example Usage:
    risk_service = RiskMetricsService()

    # Sample simulated final prices (e.g., from Monte Carlo simulation)
    np.random.seed(42) # for reproducibility
    sample_final_prices = np.random.normal(loc=100, scale=5, size=10000)

    # Example Call Option
    strike_call = 100
    premium_call = 2.50
    print(f"\n--- Call Option (Strike: {strike_call}, Premium: {premium_call}) ---")
    prob_profit_call = risk_service.calculate_probability_of_profit(sample_final_prices, strike_call, 'call')
    print(f"Probability of Profit (Call): {prob_profit_call:.4f}")
    prob_breakeven_call = risk_service.calculate_probability_of_breakeven(sample_final_prices, strike_call, premium_call, 'call')
    print(f"Probability of Breakeven (Call): {prob_breakeven_call:.4f}")
    prob_loss_call = risk_service.calculate_probability_of_loss(sample_final_prices, strike_call, premium_call, 'call')
    print(f"Probability of Loss (Call): {prob_loss_call:.4f}")
    
    # For risk-reward, assume some max profit/loss for the strategy
    # This would typically come from a strategy analysis, not just option price
    max_profit_call = 1000 # Example
    max_loss_call = 250 # Example (e.g., premium paid)
    rr_ratio_call = risk_service.calculate_risk_reward_ratio(max_profit_call, max_loss_call)
    print(f"Risk-Reward Ratio (Call): {rr_ratio_call:.2f}")

    # Example Put Option
    strike_put = 100
    premium_put = 3.00
    print(f"\n--- Put Option (Strike: {strike_put}, Premium: {premium_put}) ---")
    prob_profit_put = risk_service.calculate_probability_of_profit(sample_final_prices, strike_put, 'put')
    print(f"Probability of Profit (Put): {prob_profit_put:.4f}")
    prob_breakeven_put = risk_service.calculate_probability_of_breakeven(sample_final_prices, strike_put, premium_put, 'put')
    print(f"Probability of Breakeven (Put): {prob_breakeven_put:.4f}")
    prob_loss_put = risk_service.calculate_probability_of_loss(sample_final_prices, strike_put, premium_put, 'put')
    print(f"Probability of Loss (Put): {prob_loss_put:.4f}")

    max_profit_put = 800 # Example
    max_loss_put = 300 # Example
    rr_ratio_put = risk_service.calculate_risk_reward_ratio(max_profit_put, max_loss_put)
    print(f"Risk-Reward Ratio (Put): {rr_ratio_put:.2f}")

    # Test with invalid inputs
    print("\n--- Testing Invalid Inputs ---")
    print(f"Prob Profit (invalid final_prices): {risk_service.calculate_probability_of_profit(np.array([]), 100, 'call')}")
    print(f"Prob Breakeven (invalid strike): {risk_service.calculate_probability_of_breakeven(sample_final_prices, -10, 5, 'call')}")
    print(f"Risk-Reward (zero loss): {risk_service.calculate_risk_reward_ratio(100, 0)}")
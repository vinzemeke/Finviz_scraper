import unittest
import numpy as np
from src.services.monte_carlo_service import MonteCarloService
from src.services.monte_carlo_core import simulate_gbm, calculate_option_price

class TestMonteCarloService(unittest.TestCase):

    def setUp(self):
        self.mc_service = MonteCarloService()
        self.S0 = 100.0  # Initial stock price
        self.K = 100.0   # Strike price
        self.T = 1.0     # Time to expiration (1 year)
        self.r = 0.05    # Risk-free rate (5%)
        self.sigma = 0.2 # Volatility (20%)
        self.num_simulations = 100000 # Large number for better accuracy
        self.N = 252     # Number of steps (daily)

    def test_simulate_gbm_output_shape(self):
        price_paths = simulate_gbm(self.S0, self.r, self.sigma, self.T, self.N, self.num_simulations)
        self.assertEqual(price_paths.shape, (self.N + 1, self.num_simulations))
        self.assertTrue(np.all(price_paths[0] == self.S0))

    def test_simulate_gbm_positive_prices(self):
        price_paths = simulate_gbm(self.S0, self.r, self.sigma, self.T, self.N, self.num_simulations)
        self.assertTrue(np.all(price_paths >= 0))

    def test_calculate_option_price_call(self):
        # Using Black-Scholes for comparison (simplified, for general idea)
        # A full Black-Scholes implementation would be more complex.
        # For a simple check, we expect the MC price to be close to BS price.
        # d1 = (np.log(self.S0 / self.K) + (self.r + 0.5 * self.sigma**2) * self.T) / (self.sigma * np.sqrt(self.T))
        # d2 = d1 - self.sigma * np.sqrt(self.T)
        # from scipy.stats import norm
        # bs_price = (self.S0 * norm.cdf(d1) - self.K * np.exp(-self.r * self.T) * norm.cdf(d2))
        
        # Due to randomness, we test within a reasonable range
        mc_call_price = calculate_option_price(self.S0, self.K, self.T, self.r, self.sigma, 'call', self.num_simulations, self.N)
        
        # Expected value from a reliable Black-Scholes calculator for these parameters is approx 10.45
        # We allow for a margin of error due to Monte Carlo simulation randomness
        self.assertGreater(mc_call_price, 9.0)
        self.assertLess(mc_call_price, 12.0)

    def test_calculate_option_price_put(self):
        mc_put_price = calculate_option_price(self.S0, self.K, self.T, self.r, self.sigma, 'put', self.num_simulations, self.N)
        
        # Expected value from a reliable Black-Scholes calculator for these parameters is approx 5.57
        self.assertGreater(mc_put_price, 4.0)
        self.assertLess(mc_put_price, 7.0)

    def test_run_monte_carlo_simulation_invalid_params(self):
        # Test with negative volatility
        price = self.mc_service.run_monte_carlo_simulation(self.S0, self.K, self.T, self.r, -0.2, 'call')
        self.assertIsNone(price)

        # Test with invalid option type
        price = self.mc_service.run_monte_carlo_simulation(self.S0, self.K, self.T, self.r, self.sigma, 'invalid_type')
        self.assertIsNone(price)

    def test_analyze_simulation_results_output_keys(self):
        results = self.mc_service.analyze_simulation_results(self.S0, self.K, self.T, self.r, self.sigma, 'call', premium=5.0)
        expected_keys = [
            "estimated_option_price", "mean_final_price", "std_final_price",
            "percentile_5_final_price", "percentile_95_final_price",
            "probability_of_profit", "probability_of_breakeven", "probability_of_loss",
            "risk_reward_ratio", "price_paths"
        ]
        for key in expected_keys:
            self.assertIn(key, results)

    def test_analyze_simulation_results_values(self):
        results = self.mc_service.analyze_simulation_results(self.S0, self.K, self.T, self.r, self.sigma, 'call', premium=5.0)
        self.assertIsInstance(results['estimated_option_price'], float)
        self.assertIsInstance(results['probability_of_profit'], float)
        self.assertIsInstance(results['risk_reward_ratio'], float)
        self.assertIsInstance(results['price_paths'], list)
        self.assertGreaterEqual(results['probability_of_profit'], 0.0)
        self.assertLessEqual(results['probability_of_profit'], 1.0)

if __name__ == '__main__':
    unittest.main()
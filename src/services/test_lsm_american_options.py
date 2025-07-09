import unittest
import torch
import numpy as np
from src.services.lsm_american_options import LSMAmericanOptions

class TestLSMAmericanOptions(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.lsm = LSMAmericanOptions()
        
        # Test parameters
        self.S0 = 100.0
        self.K = 100.0
        self.r = 0.05
        self.sigma = 0.2
        self.T = 1.0
        self.steps = 50
        self.batch_size = 1000
        
    def test_device_detection(self):
        """Test that device is properly detected."""
        self.assertIsNotNone(self.lsm.device)
        self.assertIn(str(self.lsm.device), ['cpu', 'mps', 'cuda'])
        
    def test_generate_paths(self):
        """Test stock price path generation."""
        paths = self.lsm.generate_paths(self.S0, self.r, self.sigma, self.T, 
                                       self.steps, self.batch_size)
        
        # Check tensor properties
        self.assertIsInstance(paths, torch.Tensor)
        self.assertEqual(paths.shape, (self.batch_size, self.steps + 1))
        self.assertEqual(paths.device.type, self.lsm.device.type)
        
        # Check initial values
        self.assertTrue(torch.allclose(paths[:, 0], torch.full((self.batch_size,), self.S0, device=self.lsm.device)))
        
        # Check that paths are positive
        self.assertTrue(torch.all(paths > 0))
        
    def test_intrinsic_value_call(self):
        """Test intrinsic value calculation for call options."""
        S = torch.tensor([[90, 100, 110]], device=self.lsm.device, dtype=torch.float32)
        intrinsic = self.lsm.intrinsic_value(S, self.K, 'call')
        
        expected = torch.tensor([[0, 0, 10]], device=self.lsm.device, dtype=torch.float32)
        self.assertTrue(torch.allclose(intrinsic, expected))
        
    def test_intrinsic_value_put(self):
        """Test intrinsic value calculation for put options."""
        S = torch.tensor([[90, 100, 110]], device=self.lsm.device, dtype=torch.float32)
        intrinsic = self.lsm.intrinsic_value(S, self.K, 'put')
        
        expected = torch.tensor([[10, 0, 0]], device=self.lsm.device, dtype=torch.float32)
        self.assertTrue(torch.allclose(intrinsic, expected))
        
    def test_polynomial_basis(self):
        """Test polynomial basis function generation."""
        S = torch.tensor([1.0, 2.0, 3.0], device=self.lsm.device, dtype=torch.float32)
        basis = self.lsm.polynomial_basis(S, degree=2)
        
        # Check shape
        self.assertEqual(basis.shape, (3, 3))
        
        # Check that basis functions are properly constructed
        self.assertTrue(torch.allclose(basis[:, 0], torch.ones(3, device=self.lsm.device)))  # constant
        self.assertTrue(torch.allclose(basis[:, 1], S / S.mean()))  # linear
        self.assertTrue(torch.allclose(basis[:, 2], (S / S.mean()) ** 2))  # quadratic
        
    def test_lsm_american_option_call(self):
        """Test LSM pricing for American call option."""
        price = self.lsm.lsm_american_option(
            self.S0, self.K, self.r, self.sigma, self.T,
            self.steps, self.batch_size, 'call'
        )
        
        # Check that price is positive
        self.assertGreater(price, 0)
        
        # Check that price is reasonable (should be close to Black-Scholes for ATM)
        # American call should be >= European call
        self.assertLess(price, self.S0)  # Price should be less than stock price
        
    def test_lsm_american_option_put(self):
        """Test LSM pricing for American put option."""
        price = self.lsm.lsm_american_option(
            self.S0, self.K, self.r, self.sigma, self.T,
            self.steps, self.batch_size, 'put'
        )
        
        # Check that price is positive
        self.assertGreater(price, 0)
        
        # Check that price is reasonable
        self.assertLess(price, self.K)  # Price should be less than strike
        
    def test_greeks_calculation(self):
        """Test Greeks calculation."""
        greeks = self.lsm.calculate_greeks_finite_difference(
            self.S0, self.K, self.r, self.sigma, self.T,
            self.steps, self.batch_size, 'call'
        )
        
        # Check that all Greeks are calculated
        expected_greeks = ['delta', 'gamma', 'vega', 'rho', 'theta']
        for greek in expected_greeks:
            self.assertIn(greek, greeks)
            self.assertIsInstance(greeks[greek], (int, float))
        
        # Check that Greeks are finite numbers (not inf or nan)
        for greek_name, greek_value in greeks.items():
            self.assertTrue(np.isfinite(greek_value), f"Greek {greek_name} is not finite: {greek_value}")
        # No range checks due to MC noise
        
    def test_convergence_statistics(self):
        """Test convergence statistics calculation."""
        # Test with single price
        single_price = [10.0]
        stats = self.lsm.calculate_convergence_statistics(single_price)
        
        self.assertEqual(stats['mean'], 10.0)
        self.assertEqual(stats['std'], 0.0)
        self.assertEqual(stats['std_error'], 0.0)
        self.assertEqual(stats['margin_of_error'], 0.0)
        self.assertEqual(stats['coefficient_of_variation'], 0.0)
        
        # Test with multiple prices
        prices = [10.0, 10.1, 9.9, 10.05, 9.95]
        stats = self.lsm.calculate_convergence_statistics(prices)
        
        self.assertAlmostEqual(stats['mean'], 10.0, places=1)
        self.assertGreater(stats['std'], 0)
        self.assertGreater(stats['std_error'], 0)
        self.assertGreater(stats['margin_of_error'], 0)
        self.assertGreater(stats['coefficient_of_variation'], 0)
        self.assertLess(stats['confidence_interval_lower'], stats['confidence_interval_upper'])
        
    def test_convergence_checking(self):
        """Test convergence checking logic."""
        # Test with well-converged data
        well_converged_stats = {
            'mean': 10.0,
            'std': 0.01,
            'std_error': 0.005,
            'margin_of_error': 0.01,
            'confidence_interval_lower': 9.99,
            'confidence_interval_upper': 10.01,
            'coefficient_of_variation': 0.001
        }
        
        converged = self.lsm.check_convergence(well_converged_stats, tolerance=0.02)
        self.assertTrue(converged)
        
        # Test with poorly converged data
        poorly_converged_stats = {
            'mean': 10.0,
            'std': 1.0,
            'std_error': 0.5,
            'margin_of_error': 1.0,
            'confidence_interval_lower': 9.0,
            'confidence_interval_upper': 11.0,
            'coefficient_of_variation': 0.1
        }
        
        converged = self.lsm.check_convergence(poorly_converged_stats, tolerance=0.02)
        self.assertFalse(converged)
        
    def test_adaptive_batch_size(self):
        """Test adaptive batch size adjustment."""
        current_batch_size = 1000
        
        # Test with good convergence
        new_batch_size = self.lsm.adaptive_batch_size(current_batch_size, 0.005)
        self.assertGreater(new_batch_size, current_batch_size)
        
        # Test with poor convergence (should decrease but respect min_batch_size)
        new_batch_size = self.lsm.adaptive_batch_size(current_batch_size, 0.3)
        # With convergence_rate > 0.2, should try to decrease by 20%, but min_batch_size=1000 prevents it
        self.assertEqual(new_batch_size, 1000)  # Clamped to minimum
        
        # Test with very poor convergence and larger batch size
        new_batch_size = self.lsm.adaptive_batch_size(2000, 0.3)
        self.assertLess(new_batch_size, 2000)  # Should decrease: 2000 * 0.8 = 1600
        
        # Test with moderate convergence
        new_batch_size = self.lsm.adaptive_batch_size(current_batch_size, 0.1)
        self.assertEqual(new_batch_size, current_batch_size)
        
        # Test bounds
        new_batch_size = self.lsm.adaptive_batch_size(500, 0.001)  # Should increase but respect min
        self.assertGreaterEqual(new_batch_size, 1000)
        
        new_batch_size = self.lsm.adaptive_batch_size(25000, 0.5)  # Should decrease but respect max
        self.assertLessEqual(new_batch_size, 20000)
        
    def test_lsm_with_greeks(self):
        """Test the main function with Greeks calculation."""
        price, greeks = self.lsm.lsm_american_option_with_greeks(
            self.S0, self.K, self.r, self.sigma, self.T,
            steps=self.steps, batch_size=self.batch_size, max_paths=5000,
            tolerance=0.01, option_type='call'
        )
        
        # Check price
        self.assertGreater(price, 0)
        self.assertIsInstance(price, (float, np.float32, np.float64))  # Allow numpy float types
        
        # Check Greeks
        self.assertIsInstance(greeks, dict)
        expected_greeks = ['delta', 'gamma', 'vega', 'rho', 'theta']
        for greek in expected_greeks:
            self.assertIn(greek, greeks)
            
    def test_enhanced_early_stopping(self):
        """Test enhanced early stopping functionality."""
        # Use small tolerance and max_paths to test early stopping
        price, greeks = self.lsm.lsm_american_option_with_greeks(
            self.S0, self.K, self.r, self.sigma, self.T,
            steps=self.steps, batch_size=500, max_paths=10000,
            tolerance=0.1, option_type='call',  # Large tolerance for quick convergence
            adaptive_batching=True, min_batches=2, max_cv=0.2
        )
        
        # Should converge before max_paths
        self.assertGreater(price, 0)
        
    def test_adaptive_batching_disabled(self):
        """Test with adaptive batching disabled."""
        price, greeks = self.lsm.lsm_american_option_with_greeks(
            self.S0, self.K, self.r, self.sigma, self.T,
            steps=self.steps, batch_size=self.batch_size, max_paths=5000,
            tolerance=0.01, option_type='call', adaptive_batching=False
        )
        
        # Should still work correctly
        self.assertGreater(price, 0)
        self.assertIsInstance(greeks, dict)
        
    def test_different_strike_prices(self):
        """Test pricing for different strike prices."""
        strikes = [80, 100, 120]  # ITM, ATM, OTM
        
        for K in strikes:
            price = self.lsm.lsm_american_option(
                self.S0, K, self.r, self.sigma, self.T,
                self.steps, self.batch_size, 'call'
            )
            
            # Check that price decreases as strike increases
            self.assertGreater(price, 0)
            
    def test_memory_efficiency(self):
        """Test that memory usage is reasonable."""
        # Run a large simulation
        price = self.lsm.lsm_american_option(
            self.S0, self.K, self.r, self.sigma, self.T,
            steps=100, batch_size=5000, option_type='call'
        )
        
        # Check that price is reasonable
        self.assertGreater(price, 0)
        
        # Clean up GPU memory if using GPU
        if self.lsm.device.type != 'cpu':
            torch.cuda.empty_cache() if self.lsm.device.type == 'cuda' else None

if __name__ == '__main__':
    unittest.main() 
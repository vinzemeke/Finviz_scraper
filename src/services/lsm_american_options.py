import torch
import torch.nn.functional as F
import numpy as np
import logging
from typing import Dict, Tuple, Optional, List
from scipy.stats import norm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LSMAmericanOptions:
    """
    Least-Squares Monte Carlo (LSM) implementation for American-style options pricing
    using PyTorch tensors with GPU acceleration support.
    Optimized for batch processing, device management, and memory efficiency.
    """
    
    def __init__(self):
        # Auto-detect device (MPS for M1 Macs, CUDA for NVIDIA, CPU fallback)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            logging.info("Using MPS (Apple Silicon GPU) device")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            logging.info("Using CUDA device")
        else:
            self.device = torch.device("cpu")
            logging.info("Using CPU device")
    
    def generate_paths(self, S0: float, r: float, sigma: float, T: float, 
                      steps: int, batch_size: int) -> torch.Tensor:
        """
        Generate stock price paths using Geometric Brownian Motion.
        All operations are vectorized and device-aware.
        Returns float32 tensor.
        """
        dt = T / steps
        Z = torch.randn(batch_size, steps, device=self.device, dtype=torch.float32)
        drift = torch.tensor((r - 0.5 * sigma**2) * dt, device=self.device, dtype=torch.float32)
        diffusion = sigma * torch.sqrt(torch.tensor(dt, device=self.device, dtype=torch.float32))
        log_returns = drift + diffusion * Z
        log_prices = torch.cumsum(log_returns, dim=1)
        log_prices = torch.cat([torch.zeros(batch_size, 1, device=self.device, dtype=torch.float32), log_prices], dim=1)
        prices = S0 * torch.exp(log_prices)
        return prices
    
    def intrinsic_value(self, S: torch.Tensor, K: float, option_type: str) -> torch.Tensor:
        """
        Calculate intrinsic value of the option. Vectorized, float32.
        """
        K_tensor = torch.tensor(K, device=S.device, dtype=S.dtype)
        if option_type.lower() == 'call':
            return torch.clamp(S - K_tensor, min=0.0)
        else:
            return torch.clamp(K_tensor - S, min=0.0)
    
    def polynomial_basis(self, S: torch.Tensor, degree: int = 2) -> torch.Tensor:
        """
        Create polynomial basis functions for regression. Vectorized, float32.
        """
        S_norm = S / S.mean()
        basis = [S_norm ** d for d in range(degree + 1)]
        return torch.stack(basis, dim=-1).float()
    
    def lsm_american_option(self, S0: float, K: float, r: float, sigma: float, T: float,
                           steps: int = 50, batch_size: int = 5000, 
                           option_type: str = 'call', degree: int = 2) -> float:
        """
        Price American option using Least-Squares Monte Carlo.
        Fully vectorized, device-aware, memory-optimized.
        """
        with torch.no_grad():
            dt = T / steps
            discount_factor = torch.exp(torch.tensor(-r * dt, device=self.device, dtype=torch.float32))
            S = self.generate_paths(S0, r, sigma, T, steps, batch_size)
            intrinsic = self.intrinsic_value(S, K, option_type)
            continuation_value = torch.zeros_like(intrinsic)
            exercise_decision = torch.zeros_like(intrinsic, dtype=torch.bool)
            # Backward induction (vectorized over batch)
            for t in range(steps - 1, 0, -1):
                S_t = S[:, t]
                intrinsic_t = intrinsic[:, t]
                itm_mask = intrinsic_t > 0
                if itm_mask.any():
                    S_itm = S_t[itm_mask]
                    intrinsic_itm = intrinsic_t[itm_mask]
                    basis = self.polynomial_basis(S_itm, degree)
                    try:
                        if basis.device.type == 'mps':
                            basis_cpu = basis.cpu()
                            intrinsic_itm_cpu = intrinsic_itm.cpu()
                            solution = torch.linalg.lstsq(basis_cpu, intrinsic_itm_cpu, rcond=None)
                            coefficients = solution.solution.to(basis.device)
                        else:
                            solution = torch.linalg.lstsq(basis, intrinsic_itm, rcond=None)
                            coefficients = solution.solution
                        fitted_values = torch.matmul(basis, coefficients)
                        continuation_value[itm_mask, t] = fitted_values
                    except (torch.linalg.LinAlgError, NotImplementedError):
                        continuation_value[itm_mask, t] = intrinsic_itm
                exercise_decision[:, t] = (intrinsic[:, t] > continuation_value[:, t]) & (intrinsic[:, t] > 0)
            # Vectorized payoff calculation
            first_exercise = torch.argmax(exercise_decision.float(), dim=1)
            exercised = exercise_decision[torch.arange(batch_size), first_exercise]
            t_exercise = first_exercise.float()
            payoff_exercise = intrinsic[torch.arange(batch_size), first_exercise] * torch.exp(torch.tensor(-r, device=self.device, dtype=torch.float32) * t_exercise * dt)
            payoff_expiry = intrinsic[:, -1] * torch.exp(torch.tensor(-r * T, device=self.device, dtype=torch.float32))
            payoffs = torch.where(exercised, payoff_exercise, payoff_expiry)
            option_price = payoffs.mean().item()
            return option_price
    
    def calculate_greeks_finite_difference(self, S0: float, K: float, r: float, sigma: float, T: float,
                                         steps: int = 50, batch_size: int = 5000,
                                         option_type: str = 'call', greek_shift: float = 0.01) -> Dict[str, float]:
        """
        Calculate Greeks using finite difference method. Uses no_grad and float32.
        """
        with torch.no_grad():
            base_price = self.lsm_american_option(S0, K, r, sigma, T, steps, batch_size, option_type)
            price_up = self.lsm_american_option(S0 * (1 + greek_shift), K, r, sigma, T, steps, batch_size, option_type)
            price_down = self.lsm_american_option(S0 * (1 - greek_shift), K, r, sigma, T, steps, batch_size, option_type)
            delta = (price_up - price_down) / (2 * S0 * greek_shift)
            gamma = (price_up + price_down - 2 * base_price) / (S0 * greek_shift) ** 2
            price_vega_up = self.lsm_american_option(S0, K, r, sigma + greek_shift, T, steps, batch_size, option_type)
            price_vega_down = self.lsm_american_option(S0, K, r, sigma - greek_shift, T, steps, batch_size, option_type)
            vega = (price_vega_up - price_vega_down) / (2 * greek_shift)
            price_rho_up = self.lsm_american_option(S0, K, r + greek_shift, sigma, T, steps, batch_size, option_type)
            price_rho_down = self.lsm_american_option(S0, K, r - greek_shift, sigma, T, steps, batch_size, option_type)
            rho = (price_rho_up - price_rho_down) / (2 * greek_shift)
            price_theta = self.lsm_american_option(S0, K, r, sigma, T * (1 - greek_shift), steps, batch_size, option_type)
            theta = (price_theta - base_price) / (T * greek_shift)
            return {
                'delta': delta,
                'gamma': gamma,
                'vega': vega,
                'rho': rho,
                'theta': theta
            }
    
    def calculate_convergence_statistics(self, prices: List[float], confidence_level: float = 0.95) -> Dict[str, float]:
        """
        Calculate comprehensive convergence statistics for early stopping.
        
        Args:
            prices: List of option prices from different batches
            confidence_level: Confidence level for confidence intervals (default: 0.95)
            
        Returns:
            Dictionary containing convergence statistics
        """
        if len(prices) < 2:
            return {
                'mean': prices[0] if prices else 0.0,
                'std': 0.0,
                'std_error': 0.0,
                'margin_of_error': 0.0,
                'confidence_interval_lower': prices[0] if prices else 0.0,
                'confidence_interval_upper': prices[0] if prices else 0.0,
                'coefficient_of_variation': 0.0,
                'converged': False
            }
        
        prices_array = np.array(prices, dtype=np.float32)
        n = len(prices_array)
        mean_price = prices_array.mean()
        std_price = prices_array.std()
        std_error = std_price / np.sqrt(n)
        
        # Calculate confidence interval
        z_score = norm.ppf((1 + confidence_level) / 2)
        margin_of_error = z_score * std_error
        ci_lower = mean_price - margin_of_error
        ci_upper = mean_price + margin_of_error
        
        # Coefficient of variation (relative standard deviation)
        coefficient_of_variation = std_price / abs(mean_price) if abs(mean_price) > 1e-10 else float('inf')
        
        return {
            'mean': mean_price,
            'std': std_price,
            'std_error': std_error,
            'margin_of_error': margin_of_error,
            'confidence_interval_lower': ci_lower,
            'confidence_interval_upper': ci_upper,
            'coefficient_of_variation': coefficient_of_variation,
            'converged': False  # Will be set by calling function
        }
    
    def check_convergence(self, stats: Dict[str, float], tolerance: float, 
                         min_batches: int = 3, max_cv: float = 0.1) -> bool:
        """
        Check if the simulation has converged based on multiple criteria.
        
        Args:
            stats: Statistics from calculate_convergence_statistics
            tolerance: Relative tolerance for margin of error
            min_batches: Minimum number of batches before checking convergence
            max_cv: Maximum allowed coefficient of variation
            
        Returns:
            True if converged, False otherwise
        """
        # Check if we have enough data
        if stats['std_error'] == 0.0:
            return False
        
        # Check margin of error criterion
        margin_criterion = stats['margin_of_error'] < tolerance * abs(stats['mean'])
        
        # Check coefficient of variation criterion
        cv_criterion = stats['coefficient_of_variation'] < max_cv
        
        # Check if confidence interval is reasonable
        ci_width = stats['confidence_interval_upper'] - stats['confidence_interval_lower']
        ci_criterion = ci_width < tolerance * abs(stats['mean']) * 2
        
        return margin_criterion and cv_criterion and ci_criterion
    
    def adaptive_batch_size(self, current_batch_size: int, convergence_rate: float, 
                           min_batch_size: int = 1000, max_batch_size: int = 20000) -> int:
        """
        Adaptively adjust batch size based on convergence rate.
        
        Args:
            current_batch_size: Current batch size
            convergence_rate: Rate of convergence (lower is better)
            min_batch_size: Minimum allowed batch size
            max_batch_size: Maximum allowed batch size
            
        Returns:
            New batch size
        """
        if convergence_rate < 0.01:  # Very good convergence
            new_batch_size = int(current_batch_size * 1.5)
        elif convergence_rate < 0.05:  # Good convergence
            new_batch_size = int(current_batch_size * 1.2)
        elif convergence_rate > 0.2:  # Poor convergence
            new_batch_size = int(current_batch_size * 0.8)
        else:
            new_batch_size = current_batch_size
        
        return max(min_batch_size, min(max_batch_size, new_batch_size))
    
    def lsm_american_option_with_greeks(self, S0: float, K: float, r: float, sigma: float, T: float,
                                       steps: int = 50, batch_size: int = 5000, max_paths: int = 100000,
                                       tolerance: float = 0.005, option_type: str = 'call', 
                                       greek_shift: float = 0.01, adaptive_batching: bool = True,
                                       min_batches: int = 3, max_cv: float = 0.1) -> Tuple[float, Dict[str, float]]:
        """
        Main function to price American option with Greeks and enhanced early stopping.
        Optimized for batch processing, device, and memory with adaptive convergence checking.
        """
        logging.info(f"Starting LSM American option pricing: {option_type} option")
        logging.info(f"Parameters: S0={S0}, K={K}, r={r}, sigma={sigma}, T={T}")
        logging.info(f"Device: {self.device}")
        logging.info(f"Adaptive batching: {adaptive_batching}")
        
        prices = []
        total_paths = 0
        current_batch_size = batch_size
        convergence_history = []
        
        with torch.no_grad():
            while total_paths < max_paths:
                price = self.lsm_american_option(S0, K, r, sigma, T, steps, current_batch_size, option_type)
                prices.append(price)
                total_paths += current_batch_size
                
                if len(prices) >= min_batches:
                    # Calculate comprehensive statistics
                    stats = self.calculate_convergence_statistics(prices)
                    
                    # Calculate convergence rate (change in mean over last few batches)
                    if len(prices) >= 5:
                        recent_mean = np.mean(prices[-5:])
                        previous_mean = np.mean(prices[-10:-5]) if len(prices) >= 10 else prices[0]
                        convergence_rate = abs(recent_mean - previous_mean) / abs(previous_mean) if abs(previous_mean) > 1e-10 else 1.0
                        convergence_history.append(convergence_rate)
                    else:
                        convergence_rate = 1.0
                    
                    # Check convergence
                    converged = self.check_convergence(stats, tolerance, min_batches, max_cv)
                    stats['converged'] = converged
                    
                    # Log detailed statistics
                    logging.info(f"Paths: {total_paths}, Batch size: {current_batch_size}")
                    logging.info(f"Mean: {stats['mean']:.6f}, Std: {stats['std']:.6f}")
                    logging.info(f"Std Error: {stats['std_error']:.6f}, Margin: {stats['margin_of_error']:.6f}")
                    logging.info(f"CV: {stats['coefficient_of_variation']:.4f}, Convergence Rate: {convergence_rate:.4f}")
                    logging.info(f"CI: [{stats['confidence_interval_lower']:.6f}, {stats['confidence_interval_upper']:.6f}]")
                    
                    if converged:
                        logging.info(f"Converged after {total_paths} paths with {len(prices)} batches")
                        break
                    
                    # Adaptive batch sizing
                    if adaptive_batching and len(prices) >= 5:
                        new_batch_size = self.adaptive_batch_size(current_batch_size, convergence_rate)
                        if new_batch_size != current_batch_size:
                            logging.info(f"Adjusting batch size from {current_batch_size} to {new_batch_size}")
                            current_batch_size = new_batch_size
            
            # Final statistics
            final_stats = self.calculate_convergence_statistics(prices)
            final_price = final_stats['mean']
            
            logging.info("Calculating Greeks...")
            greeks = self.calculate_greeks_finite_difference(S0, K, r, sigma, T, steps, 
                                                            batch_size, option_type, greek_shift)
            
            logging.info(f"LSM pricing completed. Final price: {final_price:.6f}")
            logging.info(f"Final statistics: Mean={final_stats['mean']:.6f}, Std={final_stats['std']:.6f}")
            logging.info(f"Final CI: [{final_stats['confidence_interval_lower']:.6f}, {final_stats['confidence_interval_upper']:.6f}]")
            logging.info(f"Greeks: {greeks}")
            
            return final_price, greeks 
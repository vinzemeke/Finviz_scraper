# PRD: PyTorch LSM American Options Pricing

## Overview
Replace current Monte Carlo simulation with PyTorch-based Least-Squares Monte Carlo (LSM) for American-style options pricing with Greeks calculation.

## Goals
1. Replace current Monte Carlo with LSM for accurate American options pricing
2. Leverage PyTorch GPU acceleration (M1 Metal)
3. Implement finite difference Greeks calculation
4. Add early stopping with 95% confidence intervals
5. Maintain API compatibility

## User Stories
- As a quant analyst, I want LSM pricing for accurate American options valuation
- As a trader, I want Greeks via finite differences for risk management
- As a developer, I want automatic M1 GPU utilization for performance

## Functional Requirements
1. Implement LSM algorithm with PyTorch tensors
2. Auto-detect MPS/CPU device
3. Early stopping: margin of error < tolerance × mean price
4. Calculate Greeks: Delta, Gamma, Vega, Rho, Theta
5. Function signature: `price, greeks = lsm_american_option_with_greeks(...)`
6. Integrate with existing Flask API endpoints
7. Maintain response format compatibility

## Non-Goals
- Exotic options support
- Multi-asset options
- Stochastic volatility models
- Real-time market data integration

## Technical Considerations

### Core Implementation
- Module: `src/services/lsm_american_options.py`
- Replace `monte_carlo_service.py` calls
- PyTorch-native tensor operations
- Device-aware computation (MPS/CPU)
- Finite difference Greeks calculation

### Performance Optimizations

#### Batch Processing & Vectorization
- Simulate and process paths in large batches (5,000+ paths per batch) to maximize GPU/CPU throughput
- Avoid Python loops over paths or timesteps; use PyTorch tensor ops and broadcasting
- Use efficient matrix operations for path generation and regression

#### Efficient Regression Methods
- Use polynomial basis functions of low degree (degree 2 or 3) for regression to balance accuracy and speed
- Use `torch.linalg.lstsq()` or matrix solvers instead of explicit loops for regression
- Leverage PyTorch JIT or `torch.compile()` to optimize and fuse operations

#### Device-Aware Computation
- Use `.to(device)` once per tensor to avoid frequent data transfers between CPU and GPU (Metal backend)
- Keep all intermediate tensors on the same device
- Limit number of time steps (50-100) - more steps improve accuracy but increase compute
- Avoid repeated computation by caching reused calculations (e.g., discounted factors)

#### Memory Optimization
- Use in-place PyTorch operations (like `x.mul_()`) where safe to reduce memory overhead
- Process and discard batches incrementally to keep memory usage bounded
- Don't keep unnecessary intermediate results
- Use float32 precision unless higher precision is required (halves memory usage vs float64)
- Wrap inference code in `with torch.no_grad():` to avoid storing computation graphs
- Explicitly free unused variables and call `torch.cuda.empty_cache()` if needed

## Success Metrics
- 2-5x performance improvement on M1 GPU
- 1% accuracy vs analytical solutions
- 99%+ reliability for valid inputs
- Zero breaking API changes
- Memory usage stays within 2GB for 100k paths
- Batch processing achieves 80%+ GPU utilization

## Implementation Phases
1. Core LSM algorithm with basic PyTorch tensors
2. Batch processing and vectorization optimization
3. Memory optimization and device management
4. Greeks calculation with finite differences
5. Early stopping and convergence checking
6. API integration and testing
7. Performance tuning with JIT/compile optimizations 
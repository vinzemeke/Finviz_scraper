# Task List: PyTorch LSM American Options Pricing

## Relevant Files

- `src/services/lsm_american_options.py` - Main LSM implementation module with PyTorch tensors and device management
- `src/services/test_lsm_american_options.py` - Unit tests for LSM algorithm and Greeks calculation
- `src/main.py` - Update API endpoints to use LSM service instead of Monte Carlo
- `src/main.test.py` - Integration tests for updated API endpoints
- `requirements.txt` - Add PyTorch dependency
- `tests/test_lsm_integration.py` - End-to-end tests for LSM integration

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `lsm_american_options.py` and `test_lsm_american_options.py` in the same directory).
- Use `python -m pytest tests/` to run tests. Running without a path executes all tests found by the pytest configuration.

## Tasks

- [x] 1.0 Core LSM Algorithm Implementation
- [x] 2.0 Performance Optimization and Device Management
- [x] Greeks Calculation with Finite Differences: Implement efficient, device-aware finite-difference calculation of Delta, Gamma, Vega, Theta, and Rho for American options using the LSM module. Ensure batch computation and memory efficiency. Provide clear API for requesting Greeks alongside price.
- [x] Early Stopping and Convergence Checking: Implement adaptive early stopping based on statistical convergence criteria. Add confidence interval calculation and margin of error estimation. Ensure the convergence checking is efficient and doesn't add significant overhead.
- [x] API Integration and Testing: Integrate the LSM module into the Flask API. Add endpoints for American option pricing and Greeks using the new LSM module. Ensure device/batch/parameter selection is exposed via the API. Add API-level tests for correctness, error handling, and performance.
- [ ] Add authentication to the LSM API endpoint. (Deferred for later implementation) 
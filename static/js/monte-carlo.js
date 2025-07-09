// Monte Carlo Options Simulator JavaScript

class MonteCarloSimulator {
    constructor() {
        this.currentStep = 1;
        this.ticker = '';
        this.currentStockPrice = 0;
        this.stockData = null;
        this.optionsData = null;
        this.selectedExpiry = '';
        this.selectedStrikes = new Set();
        this.simulationResults = null;
        this.charts = {}; // Initialize charts object
        
        this.initializeEventListeners();
        this.loadUserPreferences();
    }

    initializeEventListeners() {
        // Step navigation
        document.getElementById('fetch_button').addEventListener('click', () => this.fetchMarketData());
        document.getElementById('expiry_selector').addEventListener('change', (e) => this.onExpiryChange(e.target.value));
        
        // Simulation settings
        document.getElementById('num_simulations').addEventListener('input', (e) => {
            document.querySelector('.slider-value').textContent = this.formatNumber(parseInt(e.target.value));
        });
        
        // Strike selection controls
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('strike-checkbox')) {
                this.toggleStrikeSelection(e.target);
            }
        });
    }

    async loadUserPreferences() {
        try {
            const response = await fetch('/api/preferences');
            const preferences = await response.json();
            
            if (preferences.default_ticker) {
                document.getElementById('ticker_input').value = preferences.default_ticker;
                this.ticker = preferences.default_ticker;
            }
            
            if (preferences.risk_free_rate !== undefined) {
                document.getElementById('risk_free_rate').value = preferences.risk_free_rate;
            }
            
            if (preferences.num_simulations) {
                document.getElementById('num_simulations').value = preferences.num_simulations;
                document.querySelector('.slider-value').textContent = this.formatNumber(preferences.num_simulations);
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }

    async fetchMarketData() {
        const ticker = document.getElementById('ticker_input').value.toUpperCase().trim();
        if (!ticker) {
            this.showError('Please enter a valid ticker symbol');
            return;
        }

        this.ticker = ticker;
        this.showLoading('Fetching market data...');

        try {
            // Fetch stock data
            const stockResponse = await fetch(`/api/ticker_details/${ticker}`);
            if (!stockResponse.ok) {
                throw new Error('Failed to fetch stock data');
            }
            this.stockData = await stockResponse.json();

            // Fetch options data
            const optionsResponse = await fetch(`/api/options/${ticker}`);
            if (!optionsResponse.ok) {
                throw new Error('Failed to fetch options data');
            }
            this.optionsData = await optionsResponse.json();

            this.displayStockPrice();
            this.populateExpiryDropdown();
            this.enableStep1Next();
            this.hideLoading();

        } catch (error) {
            console.error('Error fetching market data:', error);
            this.showError(`Failed to fetch data for ${ticker}: ${error.message}`);
            this.hideLoading();
        }
    }

    displayStockPrice() {
        if (!this.stockData) return;

        const stockPriceDisplay = document.getElementById('stock_price_display');
        const stockSymbol = document.getElementById('stock_symbol');
        const currentPrice = document.getElementById('current_price');
        const priceChange = document.getElementById('price_change');
        const marketCap = document.getElementById('market_cap');
        const volume = document.getElementById('volume');
        const fiftyTwoWeekRange = document.getElementById('fifty_two_week_range');

        // Update stock info
        stockSymbol.textContent = this.ticker;
        currentPrice.textContent = `${parseFloat(this.stockData.current_price).toFixed(2)}`;
        
        const change = parseFloat(this.stockData.change || 0);
        const changePercent = parseFloat(this.stockData.change_percent || 0);
        const changeColor = change >= 0 ? '#28a745' : '#dc3545';
        const changeSymbol = change >= 0 ? '+' : '';
        
        priceChange.textContent = `${changeSymbol}${change.toFixed(2)} (${changeSymbol}${changePercent.toFixed(2)}%)`;
        priceChange.style.color = changeColor;

        // Update additional details
        marketCap.textContent = this.formatMarketCap(this.stockData.market_cap);
        volume.textContent = this.formatNumber(this.stockData.volume);
        fiftyTwoWeekRange.textContent = `${parseFloat(this.stockData.fifty_two_week_low || 0).toFixed(2)} - ${parseFloat(this.stockData.fifty_two_week_high || 0).toFixed(2)}`;

        // Store current price for later use
        this.currentStockPrice = parseFloat(this.stockData.current_price);
        
        stockPriceDisplay.style.display = 'block';
    }

    populateExpiryDropdown() {
        if (!this.optionsData || Object.keys(this.optionsData).length === 0) {
            this.showError('No options data available for this ticker');
            return;
        }

        const expirySelector = document.getElementById('expiry_selector');
        const expirySection = document.getElementById('expiry_section');
        
        // Clear existing options
        expirySelector.innerHTML = '<option value="">Select expiry date...</option>';
        
        // Add expiry dates
        const expiries = Object.keys(this.optionsData).sort();
        expiries.forEach(expiry => {
            const option = document.createElement('option');
            option.value = expiry;
            option.textContent = this.formatExpiryDate(expiry);
            expirySelector.appendChild(option);
        });

        expirySection.style.display = 'block';
    }

    onExpiryChange(expiry) {
        this.selectedExpiry = expiry;
        if (expiry) {
            this.populateStrikeSelection();
            this.enableStep1Next();
        } else {
            this.disableStep1Next();
        }
    }

    populateStrikeSelection() {
        if (!this.selectedExpiry || !this.optionsData[this.selectedExpiry]) {
            return;
        }

        const expiryData = this.optionsData[this.selectedExpiry];
        const callStrikes = document.getElementById('call_strikes');
        const putStrikes = document.getElementById('put_strikes');
        const currentPriceDisplay = document.getElementById('strike_current_price');

        // Update current price display
        currentPriceDisplay.textContent = `$${this.currentStockPrice.toFixed(2)}`;

        // Clear existing strikes
        callStrikes.innerHTML = '';
        putStrikes.innerHTML = '';

        // Populate call options
        if (expiryData.calls && expiryData.calls.length > 0) {
            expiryData.calls.forEach(call => {
                const strikeItem = this.createStrikeItem(call, 'call');
                callStrikes.appendChild(strikeItem);
            });
        } else {
            callStrikes.innerHTML = '<div class="loading">No call options available</div>';
        }

        // Populate put options
        if (expiryData.puts && expiryData.puts.length > 0) {
            expiryData.puts.forEach(put => {
                const strikeItem = this.createStrikeItem(put, 'put');
                putStrikes.appendChild(strikeItem);
            });
        } else {
            putStrikes.innerHTML = '<div class="loading">No put options available</div>';
        }
    }

    createStrikeItem(option, type) {
        const strikeItem = document.createElement('div');
        strikeItem.className = 'strike-item';
        strikeItem.dataset.strike = option.strike;
        strikeItem.dataset.type = type;

        const strikeInfo = document.createElement('div');
        strikeInfo.className = 'strike-info';

        const strikePrice = document.createElement('div');
        strikePrice.className = 'strike-price';
        strikePrice.textContent = `$${parseFloat(option.strike).toFixed(2)}`;

        const strikeDetails = document.createElement('div');
        strikeDetails.className = 'strike-details';
        strikeDetails.textContent = `${type.toUpperCase()} • Bid: $${parseFloat(option.bid || 0).toFixed(2)} • Ask: $${parseFloat(option.ask || 0).toFixed(2)}`;

        strikeInfo.appendChild(strikePrice);
        strikeInfo.appendChild(strikeDetails);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'strike-checkbox';
        checkbox.dataset.strike = option.strike;
        checkbox.dataset.type = type;

        strikeItem.appendChild(strikeInfo);
        strikeItem.appendChild(checkbox);

        return strikeItem;
    }

    toggleStrikeSelection(checkbox) {
        const strike = checkbox.dataset.strike;
        const type = checkbox.dataset.type;
        const key = `${type}_${strike}`;

        if (checkbox.checked) {
            this.selectedStrikes.add(key);
            checkbox.closest('.strike-item').classList.add('selected');
        } else {
            this.selectedStrikes.delete(key);
            checkbox.closest('.strike-item').classList.remove('selected');
        }

        this.updateSelectedStrikesSummary();
        this.updateStep2NextButton();
    }

    updateSelectedStrikesSummary() {
        const summary = document.getElementById('selected_strikes_summary');
        const list = document.getElementById('selected_strikes_list');

        if (this.selectedStrikes.size === 0) {
            summary.style.display = 'none';
            return;
        }

        list.innerHTML = '';
        this.selectedStrikes.forEach(key => {
            const [type, strike] = key.split('_');
            const tag = document.createElement('div');
            tag.className = 'selected-tag';
            tag.innerHTML = `
                ${type.toUpperCase()} $${parseFloat(strike).toFixed(2)}
                <span class="remove" onclick="simulator.removeStrikeSelection('${key}')">×</span>
            `;
            list.appendChild(tag);
        });

        summary.style.display = 'block';
    }

    removeStrikeSelection(key) {
        this.selectedStrikes.delete(key);
        const [type, strike] = key.split('_');
        const checkbox = document.querySelector(`input[data-strike="${strike}"][data-type="${type}"]`);
        if (checkbox) {
            checkbox.checked = false;
            checkbox.closest('.strike-item').classList.remove('selected');
        }
        this.updateSelectedStrikesSummary();
        this.updateStep2NextButton();
    }

    selectAllStrikes() {
        document.querySelectorAll('.strike-checkbox').forEach(checkbox => {
            if (!checkbox.checked) {
                checkbox.checked = true;
                this.toggleStrikeSelection(checkbox);
            }
        });
    }

    clearStrikeSelection() {
        document.querySelectorAll('.strike-checkbox').forEach(checkbox => {
            if (checkbox.checked) {
                checkbox.checked = false;
                this.toggleStrikeSelection(checkbox);
            }
        });
    }

    async runSimulation() {
        if (this.selectedStrikes.size === 0) {
            this.showError('Please select at least one strike price');
            return;
        }

        this.showLoading('Running Monte Carlo simulation...');

        try {
            const simulationParams = this.getSimulationParams();
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(simulationParams)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Simulation failed');
            }

            this.simulationResults = await response.json();
            this.displaySimulationResults();
            this.nextStep();
            this.hideLoading();

        } catch (error) {
            console.error('Simulation error:', error);
            this.showError(`Simulation failed: ${error.message}`);
            this.hideLoading();
        }
    }

    getSimulationParams() {
        const selectedOptions = [];
        this.selectedStrikes.forEach(key => {
            const [type, strike] = key.split('_');
            const optionContract = this.optionsData[this.selectedExpiry][type === 'call' ? 'calls' : 'puts'].find(
                opt => parseFloat(opt.strike) === parseFloat(strike)
            );

            let marketPrice = 0;
            let impliedVolatility = 0.3; // Default if not found

            if (optionContract) {
                marketPrice = optionContract.lastPrice || 0;
                impliedVolatility = optionContract.impliedVolatility || 0.3;
            }

            selectedOptions.push({
                ticker: this.ticker,
                strike_price: parseFloat(strike),
                option_type: type,
                expiry_date: this.selectedExpiry,
                market_price: marketPrice,
                implied_volatility: impliedVolatility
            });
        });

        return {
            options: selectedOptions,
            num_simulations: parseInt(document.getElementById('num_simulations').value),
            risk_free_rate: parseFloat(document.getElementById('risk_free_rate').value) / 100,
            volatility_source: document.querySelector('input[name="vol_source"]:checked').value,
            current_price: this.currentStockPrice
        };
    }

    displaySimulationResults() {
        if (!this.simulationResults || !this.simulationResults.simulation_data) return;
        
        const parsedSimulationData = this.simulationResults.simulation_data;

        this.displayPriceDistributionChart();
        this.renderOptionsTable(parsedSimulationData.options_results);
        this.renderTopPicks(parsedSimulationData.options_results);
        this.renderAnalyticsCharts(parsedSimulationData.options_results);
    }

    displayPriceDistributionChart() {
        const ctx = document.getElementById('price_distribution_chart').getContext('2d');
        
        if (window.priceChart) {
            window.priceChart.destroy();
        }

        // Check if we have terminal prices data
        const prices = this.simulationResults.simulation_data?.terminal_prices || [];
        if (!prices || prices.length === 0) {
            console.log('No terminal prices data available for chart');
            return;
        }
        
        const bins = this.createHistogramBins(prices, 20);

        window.priceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: bins.map(bin => `$${bin.range}`),
                datasets: [{
                    label: 'Frequency',
                    data: bins.map(bin => bin.count),
                    backgroundColor: 'rgba(0, 123, 255, 0.6)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Simulated Terminal Price Distribution'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Frequency'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Price Range'
                        }
                    }
                }
            }
        });
    }

    renderOptionsTable(optionsResults) {
        const tbody = document.querySelector('#options_table tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!optionsResults || !Array.isArray(optionsResults) || optionsResults.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" class="text-center">No simulation results available</td></tr>';
            return;
        }
        
        optionsResults.forEach(option => {
            const greeks = option.greeks || {};
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${option.strike_price.toFixed(2)}</td>
                <td>${option.option_type.toUpperCase()}</td>
                <td>${option.market_price.toFixed(2)}</td>
                <td>${option.simulated_price.toFixed(2)}</td>
                <td>${option.undervaluation_percent.toFixed(1)}%</td>
                <td>${option.probability_of_profit.toFixed(1)}%</td>
                <td>${option.expected_pnl.toFixed(2)}</td>
                <td>${greeks.delta ? greeks.delta.toFixed(4) : '-'}</td>
                <td>${greeks.gamma ? greeks.gamma.toFixed(4) : '-'}</td>
                <td>${greeks.theta ? greeks.theta.toFixed(4) : '-'}</td>
                <td>${greeks.vega ? greeks.vega.toFixed(4) : '-'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    renderTopPicks(optionsResults) {
        const topPicksContainer = document.getElementById('top_picks');
        if (!topPicksContainer) return;
        
        topPicksContainer.innerHTML = '';
        
        if (!optionsResults || !Array.isArray(optionsResults) || optionsResults.length === 0) {
            topPicksContainer.innerHTML = '<div class="card"><p>No simulation results available</p></div>';
            return;
        }

        // Sort by undervaluation percentage
        const sortedResults = [...optionsResults]
            .sort((a, b) => b.undervaluation_percent - a.undervaluation_percent)
            .slice(0, 3);

        sortedResults.forEach(result => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h5>${result.option_type.toUpperCase()} ${result.strike_price.toFixed(2)}</h5>
                <p><strong>Undervalued:</strong> ${result.undervaluation_percent.toFixed(1)}%</p>
                <p><strong>Market Price:</strong> ${result.market_price.toFixed(2)}</p>
                <p><strong>Simulated Price:</strong> ${result.simulated_price.toFixed(2)}</p>
                <p><strong>POP:</strong> ${result.probability_of_profit.toFixed(1)}%</p>
            `;
            topPicksContainer.appendChild(card);
        });
    }



    renderAnalyticsCharts(optionsResults) {
        if (!optionsResults || !Array.isArray(optionsResults) || optionsResults.length === 0) {
            console.log('No options results available for analytics charts');
            return;
        }
        this.renderUndervaluationChart(optionsResults);
        this.renderPopChart(optionsResults);
    }

    renderUndervaluationChart(optionsResults) {
        if (!optionsResults || !Array.isArray(optionsResults) || optionsResults.length === 0) {
            console.log('No data available for undervaluation chart');
            return;
        }
        
        const ctx = document.getElementById('undervaluation_chart').getContext('2d');
        
        if (this.charts.undervaluation) {
            this.charts.undervaluation.destroy();
        }
        
        this.charts.undervaluation = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Undervaluation vs Strike',
                    data: optionsResults.map(d => ({ x: d.strike_price, y: d.undervaluation_percent })),
                    backgroundColor: 'rgba(59, 130, 246, 0.6)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Strike vs. Undervaluation'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Strike Price ($)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Undervaluation (%)'
                        }
                    }
                }
            }
        });
    }

    renderPopChart(optionsResults) {
        if (!optionsResults || !Array.isArray(optionsResults) || optionsResults.length === 0) {
            console.log('No data available for POP chart');
            return;
        }
        
        const ctx = document.getElementById('pop_chart').getContext('2d');
        
        if (this.charts.pop) {
            this.charts.pop.destroy();
        }
        
        this.charts.pop = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'POP vs Strike',
                    data: optionsResults.map(d => ({ x: d.strike_price, y: d.probability_of_profit })),
                    backgroundColor: optionsResults.map(d => this.getColorForPop(d.probability_of_profit))
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Strike vs. Probability of Profit'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Strike Price ($)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Probability of Profit (%)'
                        }
                    }
                }
            }
        });
    }

    getColorForPop(pop) {
        if (pop >= 70) return 'rgba(40, 167, 69, 0.6)'; // Green for high POP
        if (pop >= 50) return 'rgba(255, 193, 7, 0.6)'; // Yellow for medium POP
        return 'rgba(220, 53, 69, 0.6)'; // Red for low POP
    }

    // Utility functions
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    formatMarketCap(marketCap) {
        if (!marketCap) return '-';
        const num = parseFloat(marketCap);
        if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
        if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
        if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
        return `$${num.toFixed(0)}`;
    }

    formatExpiryDate(expiry) {
        const date = new Date(expiry);
        return date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }

    createHistogramBins(data, numBins) {
        if (!data || data.length === 0) {
            return [];
        }
        
        const min = Math.min(...data);
        const max = Math.max(...data);
        const binSize = (max - min) / numBins;
        
        const bins = [];
        for (let i = 0; i < numBins; i++) {
            const binStart = min + i * binSize;
            const binEnd = min + (i + 1) * binSize;
            const count = data.filter(x => x >= binStart && x < binEnd).length;
            bins.push({
                range: `${binStart.toFixed(2)}-${binEnd.toFixed(2)}`,
                count: count
            });
        }
        return bins;
    }

    // Step navigation
    nextStep() {
        if (this.currentStep < 4) {
            this.currentStep++;
            this.updateProgress();
            this.showCurrentStep();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateProgress();
            this.showCurrentStep();
        }
    }

    updateProgress() {
        // Update progress steps
        document.querySelectorAll('.progress-step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            if (stepNum === this.currentStep) {
                step.classList.add('active');
            } else if (stepNum < this.currentStep) {
                step.classList.add('completed');
            }
        });

        // Update progress labels
        document.querySelectorAll('.progress-label').forEach((label, index) => {
            const stepNum = index + 1;
            label.classList.remove('active');
            if (stepNum === this.currentStep) {
                label.classList.add('active');
            }
        });
    }

    showCurrentStep() {
        document.querySelectorAll('.workflow-step').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active');
            if (stepNum === this.currentStep) {
                step.classList.add('active');
            }
        });
    }

    enableStep1Next() {
        document.getElementById('step1_next').disabled = false;
    }

    disableStep1Next() {
        document.getElementById('step1_next').disabled = true;
    }

    updateStep2NextButton() {
        const step2Next = document.getElementById('step2_next');
        step2Next.disabled = this.selectedStrikes.size === 0;
    }

    resetWorkflow() {
        this.currentStep = 1;
        this.ticker = '';
        this.currentStockPrice = 0;
        this.stockData = null;
        this.optionsData = null;
        this.selectedExpiry = '';
        this.selectedStrikes.clear();
        this.simulationResults = null;

        // Reset UI
        document.getElementById('stock_price_display').style.display = 'none';
        document.getElementById('expiry_section').style.display = 'none';
        document.getElementById('selected_strikes_summary').style.display = 'none';
        
        // Clear selections
        document.querySelectorAll('.strike-checkbox').forEach(cb => cb.checked = false);
        document.querySelectorAll('.strike-item').forEach(item => item.classList.remove('selected'));
        
        this.updateProgress();
        this.showCurrentStep();
    }

    async exportResults() {
        if (!this.simulationResults) {
            this.showError('No results to export');
            return;
        }

        try {
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ticker: this.ticker,
                    results: this.simulationResults
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `monte_carlo_${this.ticker}_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showError('Failed to export results');
        }
    }

    // UI helpers
    showLoading(message) {
        // Create or update loading overlay
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            `;
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = `
            <div style="background: white; padding: 2rem; border-radius: 8px; text-align: center;">
                <div class="loading-spinner"></div>
                <p style="margin-top: 1rem;">${message}</p>
            </div>
        `;
        overlay.style.display = 'flex';
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showError(message) {
        // Create error notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 1rem;
            border-radius: 6px;
            z-index: 10000;
            max-width: 300px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            document.body.removeChild(notification);
        }, 5000);
    }
}

// Global functions for HTML onclick handlers
let simulator;

function nextStep() {
    simulator.nextStep();
}

function previousStep() {
    simulator.previousStep();
}

function selectAllStrikes() {
    simulator.selectAllStrikes();
}

function clearStrikeSelection() {
    simulator.clearStrikeSelection();
}

function runSimulation() {
    simulator.runSimulation();
}

function exportResults() {
    simulator.exportResults();
}

function resetWorkflow() {
    simulator.resetWorkflow();
}

function toggleAccordion(id) {
    const content = document.getElementById(id);
    const header = content.previousElementSibling;
    const icon = header.querySelector('i');
    
    content.classList.toggle('active');
    icon.style.transform = content.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    simulator = new MonteCarloSimulator();
}); 
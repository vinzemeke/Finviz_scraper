// LSMC Dashboard Step Navigation and Progress Indicator

let validatedTicker = null;
let optionsChainData = null;

document.addEventListener('DOMContentLoaded', function () {
    const steps = Array.from(document.querySelectorAll('.workflow-step'));
    const progressSteps = Array.from(document.querySelectorAll('.progress-step'));
    const progressLabels = Array.from(document.querySelectorAll('.progress-label'));
    let currentStep = 0;

    function showStep(index) {
        steps.forEach((step, i) => {
            step.classList.toggle('active', i === index);
        });
        progressSteps.forEach((el, i) => {
            el.classList.toggle('active', i === index);
        });
        progressLabels.forEach((el, i) => {
            el.classList.toggle('active', i === index);
        });
        currentStep = index;
        updateNavButtons();
    }

    function updateNavButtons() {
        console.log('updateNavButtons() called. validatedTicker:', validatedTicker);
        // Step-specific next/prev buttons
        steps.forEach((step, i) => {
            const prevBtn = step.querySelector('.btn.btn-secondary');
            const nextBtn = step.querySelector('.btn.btn-primary:not([id^="run_simulation"])');
            if (prevBtn) prevBtn.disabled = (i === 0);
            if (nextBtn) {
                const canProceedResult = canProceed(i);
                console.log(`Step ${i} can proceed:`, canProceedResult);
                nextBtn.disabled = !canProceedResult;
            }
        });
    }

    function canProceed(stepIdx) {
        // Placeholder for step validation logic
        // TODO: Implement real validation for each step
        switch (stepIdx) {
            case 0:
                // Validate ticker input and data loaded
                const stockSummary = document.getElementById('stock_summary');
                const canProceedStep0 = stockSummary && stockSummary.style.display !== 'none' && validatedTicker !== null;
                console.log('Step 0 can proceed:', canProceedStep0, 'validatedTicker:', validatedTicker, 'stockSummary display:', stockSummary?.style.display);
                return canProceedStep0;
            case 1:
                // Validate options chain loaded, expiry selected, and at least one option selected
                return document.getElementById('expiry_selector').value !== '' && (document.getElementById('selected_count')?.textContent || '0') !== '0';
            case 2:
                // Ready to run simulation
                console.log("canProceed for Step 2: Returning true.");
                const step3NextBtnCheck = document.getElementById('step3_next');
                if (step3NextBtnCheck) {
                    console.log('canProceed(2) - step3_next button disabled state:', step3NextBtnCheck.disabled);
                    console.log('canProceed(2) - step3_next button display style:', step3NextBtnCheck.style.display);
                }
                return true;
            default:
                return true;
        }
    }

    window.nextStep = function () {
        if (currentStep < steps.length - 1 && canProceed(currentStep)) {
            showStep(currentStep + 1);
        }
    };

    window.previousStep = function () {
        if (currentStep > 0) {
            showStep(currentStep - 1);
        }
    };

    // Initial state
    showStep(0);

    // Initialize autocomplete functionality
    initializeAutocomplete();

    // Enable/disable next buttons on relevant events
    // Add event listeners for dynamic validation
    document.addEventListener('input', function(e) {
        console.log('Input event triggered for element:', e.target.id);
        if (e.target.id === 'ticker_input') {
            console.log('Ticker input event detected, value:', e.target.value);
            updateNavButtons();
            fetchButton.disabled = !tickerInput.value.trim();
            console.log('Input event: fetchButton.disabled =', fetchButton.disabled, 'ticker_input value:', tickerInput.value.trim());
        }
    });

    // LSMC Dashboard Step 1 & 2 Logic

    // --- Step 1: Ticker Validation ---
    const tickerInput = document.getElementById('ticker_input');
    const fetchButton = document.getElementById('fetch_button');
    const stockSummary = document.getElementById('stock_summary');
    const stockSymbol = document.getElementById('stock_symbol');
    const currentPrice = document.getElementById('current_price');
    const marketCap = document.getElementById('market_cap');
    const volume = document.getElementById('volume');
    const fiftyTwoWeekRange = document.getElementById('fifty_two_week_range');
    const impliedVolatility = document.getElementById('implied_volatility');
    const step1Next = document.getElementById('step1_next');
    const expirySelector = document.getElementById('expiry_selector');
    const chainCurrentPrice = document.getElementById('chain_current_price');
    const callOptions = document.getElementById('call_options');
    const putOptions = document.getElementById('put_options');
    const strikePrices = document.getElementById('strike_prices');

    // Debug: Check if elements are found
    console.log('DOM elements found:');
    console.log('tickerInput:', tickerInput);
    console.log('fetchButton:', fetchButton);
    console.log('stockSummary:', stockSummary);

    function setLoadingState(isLoading) {
        fetchButton.disabled = isLoading;
        console.log('setLoadingState: fetchButton.disabled =', isLoading);
        fetchButton.innerHTML = isLoading ? '<i class="fas fa-spinner fa-spin"></i> Loading...' : '<i class="fas fa-download"></i> Load Options Chain';
    }

    function showError(msg) {
        alert(msg); // TODO: Replace with a nicer UI error display
    }

    fetchButton.addEventListener('click', function () {
        const ticker = tickerInput.value.trim().toUpperCase();
        console.log('Fetch button clicked, ticker:', ticker);
        if (!ticker) {
            showError('Please enter a ticker symbol.');
            return;
        }
        setLoadingState(true);
        stockSummary.style.display = 'none';
        expirySelector.innerHTML = '<option value="">Loading expiries...</option>';
        console.log('Making API call to /api/lsmc/validate_ticker with ticker:', ticker);
        fetch(`/api/lsmc/validate_ticker`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        })
        .then(res => {
            console.log('API response status:', res.status);
            return res.json();
        })
        .then(data => {
            console.log('VALIDATION RESPONSE:', data);
            setLoadingState(false);
            if (data.error) {
                showError(data.error);
                step1Next.disabled = true;
                return;
            }
            validatedTicker = data.ticker;
            console.log('validatedTicker set to:', validatedTicker);
            // Show summary
            stockSymbol.textContent = data.ticker;
            currentPrice.textContent = data.current_price ? `$${data.current_price}` : '-';
            // TODO: Fill in marketCap, volume, etc. if available
            marketCap.textContent = data.market_cap_formatted || '-';
            volume.textContent = data.volume || '-';
            fiftyTwoWeekRange.textContent = data.fifty_two_week_range || '-';
            impliedVolatility.textContent = data.implied_volatility || '-';
            stockSummary.style.display = '';
            console.log('Stock summary display set to:', stockSummary.style.display);
            // Populate expiries
            expirySelector.innerHTML = '<option value="">Select expiration</option>';
            (data.options_expirations || []).forEach(exp => {
                const opt = document.createElement('option');
                opt.value = exp;
                opt.textContent = exp;
                expirySelector.appendChild(opt);
            });
            step1Next.disabled = false;
            fetchButton.disabled = false;
            console.log('Validation success: fetchButton.disabled =', fetchButton.disabled);
            console.log('Ticker validated successfully:', validatedTicker);
            console.log('About to call updateNavButtons()...');
            updateNavButtons(); // Update button states after successful validation
            console.log('updateNavButtons() called. Current validatedTicker:', validatedTicker);
        })
        .catch(err => {
            console.log('API call failed with error:', err);
            setLoadingState(false);
            showError('Error validating ticker.');
            step1Next.disabled = true;
            fetchButton.disabled = false;
            console.log('Validation error: fetchButton.disabled =', fetchButton.disabled);
            updateNavButtons(); // Update button states after error
        });
    });

    // --- Step 2: Expiry Selection & Options Chain ---
    expirySelector.addEventListener('change', function () {
        console.log('expirySelector changed, validatedTicker:', validatedTicker);
        currentExpiry = expirySelector.value; // Set currentExpiry here
        updateNavButtons(); // Update button states when expiry changes
        
        // Load options chain for selected expiry
        if (validatedTicker && expirySelector.value) {
            loadOptionsChain(validatedTicker, expirySelector.value);
        }
    });

    // Refresh options chain function
    window.refreshOptionsChain = function() {
        if (validatedTicker && expirySelector.value) {
            console.log('Refreshing options chain for:', validatedTicker, 'expiry:', expirySelector.value);
            loadOptionsChain(validatedTicker, expirySelector.value);
        } else {
            console.log('Cannot refresh: missing ticker or expiry');
        }
    };

    function loadOptionsChain(ticker, expiry) {
        console.log('Loading options chain for:', ticker, 'expiry:', expiry);
        
        // Show loading state
        const optionsBody = document.getElementById('selectable-options-body');
        if (optionsBody) {
            optionsBody.innerHTML = '<tr><td colspan="15" class="text-center">Loading options chain...</td></tr>';
        }
        
        fetch(`/api/lsmc/options_chain/${ticker}`)
            .then(res => res.json())
            .then(data => {
                console.log('Options chain data received:', data);
                if (data.error) {
                    console.error('Error loading options chain:', data.error);
                    if (optionsBody) {
                        optionsBody.innerHTML = '<tr><td colspan="15" class="text-center text-danger">Error loading options chain</td></tr>';
                    }
                    return;
                }
                
                optionsChainData = data;
                
                // Update current price display
                const chainCurrentPrice = document.getElementById('chain_current_price');
                if (chainCurrentPrice && data.current_price) {
                    chainCurrentPrice.textContent = `$${data.current_price}`;
                }
                
                // Render options table for selected expiry
                if (data.options_chain && data.options_chain[expiry]) {
                    renderOptionsTable(data.options_chain[expiry]);
                } else {
                    console.error('No data for expiry:', expiry);
                    if (optionsBody) {
                        optionsBody.innerHTML = '<tr><td colspan="15" class="text-center text-danger">No data available for selected expiry</td></tr>';
                    }
                }
                
                updateNavButtons();
            })
            .catch(err => {
                console.error('Error fetching options chain:', err);
                if (optionsBody) {
                    optionsBody.innerHTML = '<tr><td colspan="15" class="text-center text-danger">Error loading options chain</td></tr>';
                }
            });
    }

    function renderOptionsTable(chain) {
        const tableBody = document.getElementById('selectable-options-body'); // Changed ID to match new HTML
        tableBody.innerHTML = '';

        const strikes = Array.from(new Set([...chain.calls.map(c => c.strike), ...chain.puts.map(p => p.strike)])).sort((a, b) => a - b);

        strikes.forEach((strike, index) => {
            const call = chain.calls.find(c => c.strike === strike);
            const put = chain.puts.find(p => p.strike === strike);

            const row = document.createElement('tr');
            row.className = index % 2 === 0 ? 'even-row' : 'odd-row';

            // Calls
            if (call) {
                const optionId = `call_${call.strike}_${expirySelector.value}`;
                const callChangeClass = call.change > 0 ? 'positive' : (call.change < 0 ? 'negative' : 'neutral');
                row.innerHTML += `
                    <td><input type="checkbox" class="option-checkbox" data-option-id="${optionId}"></td>
                    <td>${call.lastPrice.toFixed(2)}</td>
                    <td>${call.bid.toFixed(2)}</td>
                    <td>${call.ask.toFixed(2)}</td>
                    <td>${formatVolume(call.volume)}</td>
                    <td>${formatOI(call.openInterest)}</td>
                    <td class="${callChangeClass}">${call.change.toFixed(2)}</td>
                    <td>${(call.impliedVolatility * 100).toFixed(1)}%</td>
                `;
            } else {
                row.innerHTML += `<td colspan="7"></td>`;
            }

            // Strike
            row.innerHTML += `<td class="strike-price">${strike.toFixed(2)}</td>`;

            // Puts
            if (put) {
                const optionId = `put_${put.strike}_${expirySelector.value}`;
                const putChangeClass = put.change > 0 ? 'positive' : (put.change < 0 ? 'negative' : 'neutral');
                row.innerHTML += `
                    <td>${(put.impliedVolatility * 100).toFixed(1)}%</td>
                    <td class="${putChangeClass}">${put.change.toFixed(2)}</td>
                    <td>${formatOI(put.openInterest)}</td>
                    <td>${formatVolume(put.volume)}</td>
                    <td>${put.ask.toFixed(2)}</td>
                    <td>${put.bid.toFixed(2)}</td>
                    <td>${put.lastPrice.toFixed(2)}</td>
                    <td><input type="checkbox" class="option-checkbox" data-option-id="${optionId}"></td>
                `;
            } else {
                row.innerHTML += `<td colspan="7"></td>`;
            }

            tableBody.appendChild(row);
        });

        // Add event listeners to checkboxes
        tableBody.querySelectorAll('.option-checkbox').forEach(cb => {
            cb.addEventListener('change', updateSelectedOptions);
        });

        // Add event listeners for select all checkboxes
        document.getElementById('select-all-calls').addEventListener('change', function() {
            const isChecked = this.checked;
            tableBody.querySelectorAll('input[data-option-id^="call_"]').forEach(cb => {
                cb.checked = isChecked;
            });
            updateSelectedOptions();
        });

        document.getElementById('select-all-puts').addEventListener('change', function() {
            const isChecked = this.checked;
            tableBody.querySelectorAll('input[data-option-id^="put_"]').forEach(cb => {
                cb.checked = isChecked;
            });
            updateSelectedOptions();
        });

        // Update selection display after rendering table
        updateSelectionDisplay();
    }

    // --- Step 3: Option Selection ---
    let selectedOptions = [];
    let currentExpiry = null;

    // Function to format volume and open interest numbers in k format when over 999
    function formatVolume(volume) {
        if (volume === null || volume === undefined || volume === 0) {
            return '0';
        }
        const num = parseInt(volume);
        if (num > 999) {
            return (num / 1000).toFixed(2) + 'k';
        }
        return num.toString();
    }
    
    // Check if OI data is available (not null/undefined)
    function isOIAvailable(value) {
        return value !== null && value !== undefined;
    }
    
    // Format OI with data quality indicator
    function formatOI(oiValue) {
        if (!isOIAvailable(oiValue)) {
            return '<span class="oi-missing" title="OI data not available from Yahoo Finance">0*</span>';
        }
        if (oiValue === 0) {
            return '<span class="oi-zero" title="OI is actually 0">0</span>';
        }
        return formatVolume(oiValue);
    }

    function updateSelectedOptions() {
        selectedOptions = [];
        if (!optionsChainData || !currentExpiry) return;
        const chain = optionsChainData.options_chain && optionsChainData.options_chain[currentExpiry];
        if (!chain) return;

        const checkedBoxes = document.querySelectorAll('#selectable-options-body .option-checkbox:checked');
        checkedBoxes.forEach(cb => {
            const optionId = cb.dataset.optionId;
            const [type, strike, expiry] = optionId.split('_');

            const options = type === 'call' ? chain.calls : chain.puts;
            const option = options.find(opt => opt.strike.toString() === strike);

            if (option) {
                selectedOptions.push({ 
                    ...option, 
                    option_type: type, 
                    expiry_date: expiry,
                    id: optionId 
                });
            }
        });

        // Update summary
        document.getElementById('selected_count').textContent = selectedOptions.length;
        document.getElementById('selected_options_list').innerHTML = '';
        selectedOptions.forEach(opt => {
            const div = document.createElement('div');
            div.className = 'selected-option-row';
            div.textContent = `${opt.option_type.toUpperCase()} | Strike: ${opt.strike} | Expiry: ${opt.expiry_date}`;
            document.getElementById('selected_options_list').appendChild(div);
        });
        document.getElementById('selected_options_summary').style.display = selectedOptions.length > 0 ? '' : 'none';
        // step3Next.disabled = selectedOptions.length === 0; // This button is now step2_next
        document.getElementById('step2_next').disabled = selectedOptions.length === 0;
        updateNavButtons(); // Update navigation button states
    }

    // Update selection display (called by drag selection)
    function updateSelectionDisplay() {
        // Update checkboxes to match selectedOptions
        document.querySelectorAll('#selectable-options-body .option-checkbox').forEach(cb => {
            const optionId = cb.dataset.optionId;
            const isSelected = selectedOptions.some(opt => opt.id === optionId);
            cb.checked = isSelected;
        });
        
        // Update summary
        document.getElementById('selected_count').textContent = selectedOptions.length;
        document.getElementById('selected_options_list').innerHTML = '';
        selectedOptions.forEach(opt => {
            const div = document.createElement('div');
            div.className = 'selected-option-row';
            div.textContent = `${opt.option_type.toUpperCase()} | Strike: ${opt.strike} | Expiry: ${opt.expiry_date}`;
            document.getElementById('selected_options_list').appendChild(div);
        });
        document.getElementById('selected_options_summary').style.display = selectedOptions.length > 0 ? '' : 'none';
        // step3Next.disabled = selectedOptions.length === 0; // This button is now step2_next
        document.getElementById('step2_next').disabled = selectedOptions.length === 0;
        updateNavButtons(); // Update navigation button states
    }

    // Step 2 to Step 3 transition: render selectable options when entering step 3
    document.getElementById('step2_next').addEventListener('click', function () {
        currentExpiry = expirySelector.value;
        // renderSelectableOptionsTable(); // This function doesn't exist, options are already rendered
        updateSelectedOptions();
    });

    

    // Selection controls
    window.selectAllOptions = function () {
        document.querySelectorAll('#selectable-options-body .option-checkbox').forEach(cb => { cb.checked = true; });
        updateSelectedOptions();
    };
    window.clearSelection = function () {
        document.querySelectorAll('#selectable-options-body .option-checkbox').forEach(cb => { cb.checked = false; });
        updateSelectedOptions();
    };
    window.selectTopOI = function (count = 5) {
        let allOpts = [];
        if (!optionsChainData || !currentExpiry) return;
        const chain = optionsChainData.options_chain && optionsChainData.options_chain[currentExpiry];
        if (!chain) return;
        chain.calls.forEach(opt => allOpts.push({ ...opt, option_type: 'call' }));
        chain.puts.forEach(opt => allOpts.push({ ...opt, option_type: 'put' }));
        allOpts.sort((a, b) => {
            const aOI = a.openInterest === null ? -1 : (a.openInterest || 0);
            const bOI = b.openInterest === null ? -1 : (b.openInterest || 0);
            return bOI - aOI;
        });
        clearSelection();
        allOpts.slice(0, count).forEach(opt => {
            const optionId = `${opt.option_type}_${opt.strike}_${currentExpiry}`;
            const cb = document.querySelector(`input[data-option-id="${optionId}"]`);
            if (cb) cb.checked = true;
        });
        updateSelectedOptions();
    };
    window.selectTopVolume = function (count = 10) {
        let allOpts = [];
        if (!optionsChainData || !currentExpiry) return;
        const chain = optionsChainData.options_chain && optionsChainData.options_chain[currentExpiry];
        if (!chain) return;
        chain.calls.forEach(opt => allOpts.push({ ...opt, option_type: 'call' }));
        chain.puts.forEach(opt => allOpts.push({ ...opt, option_type: 'put' }));
        allOpts.sort((a, b) => (b.volume || 0) - (a.volume || 0));
        clearSelection();
        allOpts.slice(0, count).forEach(opt => {
            const optionId = `${opt.option_type}_${opt.strike}_${currentExpiry}`;
            const cb = document.querySelector(`input[data-option-id="${optionId}"]`);
            if (cb) cb.checked = true;
        });
        updateSelectedOptions();
    };

    // --- Step 4: Run Simulation ---
    const batchSizeSlider = document.getElementById('batch_size');
    const maxPathsSlider = document.getElementById('max_paths');
    const toleranceSlider = document.getElementById('tolerance');
    const greekShiftSlider = document.getElementById('greek_shift');
    const runSimulationBtn = document.getElementById('run_simulation');
    const step3NextBtn = document.getElementById('step3_next');
    const simulationProgress = document.getElementById('simulation_progress');
    const simulationLog = document.getElementById('simulation_log');
    const progressBar = document.getElementById('simulation_progress_bar');
    const progressText = document.getElementById('progress_text');
    const progressPercentage = document.getElementById('progress_percentage');
    const completedOptions = document.getElementById('completed_options');
    const totalOptions = document.getElementById('total_options');
    const logContent = document.getElementById('log_content');
    const cancelSimulationBtn = document.getElementById('cancel_simulation');

    // Simulation state
    let simulationRunning = false;
    let simulationResults = [];
    let simulationStartTime = null;
    let currentSimulationRequest = null;

    // Update slider values
    if (batchSizeSlider) {
        batchSizeSlider.addEventListener('input', function () {
            this.nextElementSibling.textContent = parseInt(this.value).toLocaleString();
        });
    }
    if (maxPathsSlider) {
        maxPathsSlider.addEventListener('input', function () {
            this.nextElementSibling.textContent = parseInt(this.value).toLocaleString();
        });
    }
    if (toleranceSlider) {
        toleranceSlider.addEventListener('input', function () {
            this.nextElementSibling.textContent = parseFloat(this.value).toFixed(3);
        });
    }
    if (greekShiftSlider) {
        greekShiftSlider.addEventListener('input', function () {
            this.nextElementSibling.textContent = parseFloat(this.value).toFixed(3);
        });
    }

    // Run simulation function
    window.runSimulation = function() {
        if (!selectedOptions.length) {
            showError('No options selected for simulation.');
            return;
        }

        // Initialize simulation state
        simulationRunning = true;
        simulationResults = [];
        simulationStartTime = Date.now();
        
        // Show progress UI
        simulationProgress.style.display = 'block';
        simulationLog.style.display = 'block';
        runSimulationBtn.style.display = 'none';
        step3NextBtn.style.display = 'none';
        
        // Initialize progress
        updateProgress(0, 'Initializing simulation...', 0, selectedOptions.length);
        clearLog();
        addLogMessage('info', 'Starting LSMC simulation for ' + selectedOptions.length + ' options');
        
        // Get simulation parameters
        const simulationParams = {
            batch_size: parseInt(batchSizeSlider.value),
            max_paths: parseInt(maxPathsSlider.value),
            tolerance: parseFloat(toleranceSlider.value),
            greek_shift: parseFloat(greekShiftSlider.value)
        };
        
        addLogMessage('info', `Parameters: Batch Size=${simulationParams.batch_size}, Max Paths=${simulationParams.max_paths}, Tolerance=${simulationParams.tolerance}, Greek Shift=${simulationParams.greek_shift}`);
        
        // Simulate options one by one for real-time progress updates
        simulateOptionsSequentially(selectedOptions, simulationParams, 0);
    };

    // Simulate options sequentially with progress updates
    function simulateOptionsSequentially(options, simulationParams, currentIndex) {
        if (!simulationRunning || currentIndex >= options.length) {
            finishSimulation();
            return;
        }

        const option = options[currentIndex];
        const progress = ((currentIndex) / options.length) * 100;
        const remainingOptions = options.length - currentIndex;
        
        // Update progress
        updateProgress(progress, `Simulating option ${currentIndex + 1}/${options.length}...`, currentIndex, options.length);
        addLogMessage('info', `Processing ${option.option_type.toUpperCase()} ${option.strike} expiring ${option.expiry_date}`);
        
        // Prepare payload for single option
        const payload = {
            ticker: validatedTicker,
            selected_options: [{
                strike: parseFloat(option.strike),
                option_type: option.option_type,
                expiry_date: option.expiry_date,
                market_price: parseFloat(option.lastPrice || option.ask || 0),
                implied_volatility: parseFloat(option.impliedVolatility || 0.3),
            }],
            simulation_params: simulationParams
        };

        fetch('/api/lsmc/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                addLogMessage('error', `Failed to simulate option ${currentIndex + 1}: ${data.error}`);
                // Continue with next option even if this one fails
                simulateOptionsSequentially(options, simulationParams, currentIndex + 1);
                return;
            }
            
            if (data.results && data.results.length > 0) {
                const result = data.results[0];
                simulationResults.push(result);
                
                // Add result to log
                const mispricing = result.undervaluation_percent || 0;
                const mispricingText = mispricing > 0 ? 'UNDERVALUED' : mispricing < 0 ? 'OVERVALUED' : 'FAIR VALUE';
                addLogMessage('success', `✓ ${option.option_type.toUpperCase()} ${option.strike}: Market $${(result.market_price || 0).toFixed(2)} → LSMC $${(result.lsmc_price || 0).toFixed(2)} (${mispricingText})`);
            }
            
            // Continue with next option
            setTimeout(() => {
                simulateOptionsSequentially(options, simulationParams, currentIndex + 1);
            }, 100); // Small delay to allow UI updates
        })
        .catch(err => {
            console.error(`Error simulating option ${currentIndex + 1}:`, err);
            addLogMessage('error', `Failed to simulate option ${currentIndex + 1}: ${err.message || 'Unknown error'}`);
            // Continue with next option even if this one fails
            simulateOptionsSequentially(options, simulationParams, currentIndex + 1);
        });
    }

    

    

    // Calculate time to expiry in years
    function calculateTimeToExpiry(expiryDate) {
        const expiry = new Date(expiryDate);
        const now = new Date();
        const diffMs = expiry - now;
        return Math.max(diffMs / (1000 * 60 * 60 * 24 * 365), 0.001); // Minimum 1 day
    }

    // Update progress display
    function updateProgress(percentage, text, completed, total, remainingMs = null) {
        progressBar.style.width = percentage + '%';
        progressText.textContent = text;
        progressPercentage.textContent = percentage.toFixed(1) + '%';
        completedOptions.textContent = completed;
        totalOptions.textContent = total;
        
        if (remainingMs) {
            const remainingMinutes = Math.ceil(remainingMs / (1000 * 60));
            progressText.textContent += ` (${remainingMinutes} min remaining)`;
        }
    }

    // Add log message
    function addLogMessage(type, message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> <span class="log-message">${message}</span>`;
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // Clear log
    function clearLog() {
        logContent.innerHTML = '';
    }

    // Finish simulation
    function finishSimulation() {
        console.log("finishSimulation called.");
        simulationRunning = false;
        
        const totalTime = Date.now() - simulationStartTime;
        const minutes = Math.floor(totalTime / (1000 * 60));
        const seconds = Math.floor((totalTime % (1000 * 60)) / 1000);
        
        addLogMessage('success', `Simulation completed in ${minutes}m ${seconds}s`);
        updateProgress(100, 'Simulation completed!', selectedOptions.length, selectedOptions.length);
        
        // Show results summary
        console.log("Simulation results before display:", simulationResults);
        window.simulationResults = simulationResults; // Ensure it's accessible globally
        
        if (simulationResults.length > 0) {
            displaySimulationResults();
        } else {
            addLogMessage('warning', 'No successful simulations completed');
        }
        
        // Update UI
        runSimulationBtn.style.display = 'inline-block';
        console.log("Attempting to show step3NextBtn");
        step3NextBtn.style.display = 'inline-block';
        step3NextBtn.disabled = false;
        updateNavButtons(); // Re-evaluate navigation buttons after simulation finishes
    }

    // Display simulation results
    function displaySimulationResults() {
        console.log("displaySimulationResults called.");
        console.log("window.simulationResults:", window.simulationResults);
        if (!window.simulationResults || window.simulationResults.length === 0) {
            addLogMessage('error', 'No results to display');
            return;
        }
        
        // Calculate summary statistics
        const totalOptions = window.simulationResults.length;
        const underpriced = window.simulationResults.filter(r => (r.undervaluation_percent || 0) > 0).length;
        const overpriced = window.simulationResults.filter(r => (r.undervaluation_percent || 0) < 0).length;
        const avgMispricing = totalOptions > 0 ? window.simulationResults.reduce((sum, r) => sum + Math.abs(r.undervaluation_percent || 0), 0) / totalOptions : 0;
        
        addLogMessage('info', `Summary: ${totalOptions} options, ${underpriced} underpriced, ${overpriced} overpriced, avg mispricing: ${avgMispricing.toFixed(2)}%`);
        
        // Populate summary cards
        document.getElementById('total_simulated').textContent = totalOptions;
        document.getElementById('underpriced_count').textContent = underpriced;
        document.getElementById('overpriced_count').textContent = overpriced;
        document.getElementById('avg_mispricing').textContent = `${avgMispricing.toFixed(2)}%`;

        // Populate results table
        const resultsTableBody = document.getElementById('results_table_body');
        resultsTableBody.innerHTML = '';
        window.simulationResults.forEach(result => {
            const row = document.createElement('tr');
            const mispricingClass = (result.undervaluation_percent || 0) > 0 ? 'positive' : ((result.undervaluation_percent || 0) < 0 ? 'negative' : '');
            const difference = (result.market_price || 0) - (result.lsmc_price || 0);
            row.innerHTML = `
                <td>${validatedTicker || 'N/A'}</td>
                <td>${(result.option_type || 'N/A').toUpperCase()}</td>
                <td>${(result.strike || 0).toFixed(2)}</td>
                <td>${result.expiry_date || 'N/A'}</td>
                <td>${(result.market_price || 0).toFixed(2)}</td>
                <td>${(result.lsmc_price || 0).toFixed(2)}</td>
                <td>${difference.toFixed(2)}</td>
                <td class="${mispricingClass}">${(result.undervaluation_percent || 0).toFixed(2)}%</td>
                <td>${result.greeks && result.greeks.delta ? result.greeks.delta.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.gamma ? result.greeks.gamma.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.vega ? result.greeks.vega.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.theta ? result.greeks.theta.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.rho ? result.greeks.rho.toFixed(4) : 'N/A'}</td>
            `;
            resultsTableBody.appendChild(row);
        });

        // Enable next step button
        document.getElementById('step3_next').disabled = false;
        
        // Initialize sorting functionality
        initializeSorting();
    }

    // Cancel simulation
    window.cancelSimulation = function() {
        if (!simulationRunning) return;
        
        simulationRunning = false;
        addLogMessage('warning', 'Simulation cancelled by user');
        
        // Abort current request if any
        if (currentSimulationRequest) {
            currentSimulationRequest.abort();
        }
        
        // Reset UI
        runSimulationBtn.style.display = 'inline-block';
        step3NextBtn.style.display = 'none';
        simulationProgress.style.display = 'none';
        updateProgress(0, 'Cancelled', 0, selectedOptions.length);
    };

    // Download log
    window.downloadLog = function() {
        const logText = Array.from(logContent.children)
            .map(entry => entry.textContent)
            .join('\n');
        
        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `lsmc_simulation_log_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // Autocomplete functionality
    function initializeAutocomplete() {
        const tickerInput = document.getElementById('ticker_input');
        const dropdown = document.getElementById('autocomplete-dropdown');
        let searchTimeout = null;
        let selectedIndex = -1;
        let searchResults = [];

        // Debounced search function
        function performSearch(query) {
            if (query.length < 2) {
                hideDropdown();
                return;
            }

            fetch(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=10`)
                .then(response => response.json())
                .then(data => {
                    searchResults = data;
                    displayResults(data);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    hideDropdown();
                });
        }

        // Display search results
        function displayResults(results) {
            if (results.length === 0) {
                hideDropdown();
                return;
            }

            dropdown.innerHTML = '';
            results.forEach((result, index) => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.dataset.index = index;
                
                const symbolSpan = document.createElement('span');
                symbolSpan.className = 'autocomplete-symbol';
                symbolSpan.textContent = result.symbol;
                
                const companySpan = document.createElement('span');
                companySpan.className = 'autocomplete-company';
                companySpan.textContent = result.company_name;
                
                const exchangeSpan = document.createElement('span');
                exchangeSpan.className = 'autocomplete-exchange';
                exchangeSpan.textContent = result.exchange || 'N/A';
                
                item.appendChild(symbolSpan);
                item.appendChild(companySpan);
                item.appendChild(exchangeSpan);
                
                if (result.is_etf) {
                    const etfBadge = document.createElement('span');
                    etfBadge.className = 'autocomplete-etf-badge';
                    etfBadge.textContent = 'ETF';
                    item.appendChild(etfBadge);
                }
                
                item.addEventListener('click', () => selectResult(result));
                item.addEventListener('mouseenter', () => {
                    selectedIndex = index;
                    updateSelection();
                });
                
                dropdown.appendChild(item);
            });
            
            dropdown.style.display = 'block';
            selectedIndex = -1;
        }

        // Select a result
        function selectResult(result) {
            tickerInput.value = result.symbol;
            hideDropdown();
            // Trigger the fetch button click to load options
            fetchButton.click();
        }

        // Update selection highlighting
        function updateSelection() {
            const items = dropdown.querySelectorAll('.autocomplete-item');
            items.forEach((item, index) => {
                item.classList.toggle('selected', index === selectedIndex);
            });
        }

        // Hide dropdown
        function hideDropdown() {
            dropdown.style.display = 'none';
            selectedIndex = -1;
        }

        // Input event handler
        tickerInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Set new timeout for debounced search
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        });

        // Keyboard navigation
        tickerInput.addEventListener('keydown', function(e) {
            if (dropdown.style.display === 'none') return;
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, searchResults.length - 1);
                    updateSelection();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, -1);
                    updateSelection();
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0 && searchResults[selectedIndex]) {
                        selectResult(searchResults[selectedIndex]);
                    }
                    break;
                case 'Escape':
                    hideDropdown();
                    break;
            }
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!tickerInput.contains(e.target) && !dropdown.contains(e.target)) {
                hideDropdown();
            }
        });

        // Focus event
        tickerInput.addEventListener('focus', function() {
            const query = this.value.trim();
            if (query.length >= 2) {
                performSearch(query);
            }
        });
    }

    // Sorting functionality
    let currentSortColumn = null;
    let currentSortDirection = 'asc';

    // Initialize sorting when results are displayed
    function initializeSorting() {
        const table = document.getElementById('results_table');
        if (!table) return;

        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const sortKey = this.getAttribute('data-sort');
                sortResultsTable(sortKey);
            });
        });
    }

    // Sort the results table
    function sortResultsTable(sortKey) {
        if (!window.simulationResults || window.simulationResults.length === 0) return;

        // Update sort direction
        if (currentSortColumn === sortKey) {
            currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortColumn = sortKey;
            currentSortDirection = 'asc';
        }

        // Update header classes
        updateSortHeaders(sortKey, currentSortDirection);

        // Sort the data
        const sortedResults = [...window.simulationResults].sort((a, b) => {
            let aValue = getSortValue(a, sortKey);
            let bValue = getSortValue(b, sortKey);

            // Handle null/undefined values
            if (aValue === null || aValue === undefined) aValue = '';
            if (bValue === null || bValue === undefined) bValue = '';

            // Handle numeric values
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                return currentSortDirection === 'asc' ? aValue - bValue : bValue - aValue;
            }

            // Handle string values
            aValue = String(aValue).toLowerCase();
            bValue = String(bValue).toLowerCase();
            
            if (currentSortDirection === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });

        // Update the display
        displaySortedResults(sortedResults);
    }

    // Get the value to sort by for a given sort key
    function getSortValue(result, sortKey) {
        switch (sortKey) {
            case 'ticker':
                return validatedTicker || 'N/A';
            case 'type':
                return (result.option_type || 'N/A').toUpperCase();
            case 'strike':
                return parseFloat(result.strike) || 0;
            case 'expiry':
                return result.expiry_date || 'N/A';
            case 'market_price':
                return parseFloat(result.market_price) || 0;
            case 'simulated_price':
                return parseFloat(result.lsmc_price) || 0;
            case 'difference':
                return (parseFloat(result.market_price) || 0) - (parseFloat(result.lsmc_price) || 0);
            case 'mispricing':
                return parseFloat(result.undervaluation_percent) || 0;
            case 'delta':
                return result.greeks && result.greeks.delta ? parseFloat(result.greeks.delta) : 0;
            case 'gamma':
                return result.greeks && result.greeks.gamma ? parseFloat(result.greeks.gamma) : 0;
            case 'vega':
                return result.greeks && result.greeks.vega ? parseFloat(result.greeks.vega) : 0;
            case 'theta':
                return result.greeks && result.greeks.theta ? parseFloat(result.greeks.theta) : 0;
            case 'rho':
                return result.greeks && result.greeks.rho ? parseFloat(result.greeks.rho) : 0;
            default:
                return '';
        }
    }

    // Update sort header classes
    function updateSortHeaders(sortKey, direction) {
        const table = document.getElementById('results_table');
        if (!table) return;

        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (header.getAttribute('data-sort') === sortKey) {
                header.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    }

    // Display sorted results
    function displaySortedResults(sortedResults) {
        const resultsTableBody = document.getElementById('results_table_body');
        if (!resultsTableBody) return;

        resultsTableBody.innerHTML = '';
        sortedResults.forEach(result => {
            const row = document.createElement('tr');
            const mispricingClass = (result.undervaluation_percent || 0) > 0 ? 'positive' : ((result.undervaluation_percent || 0) < 0 ? 'negative' : '');
            const difference = (result.market_price || 0) - (result.lsmc_price || 0);
            row.innerHTML = `
                <td>${validatedTicker || 'N/A'}</td>
                <td>${(result.option_type || 'N/A').toUpperCase()}</td>
                <td>${(result.strike || 0).toFixed(2)}</td>
                <td>${result.expiry_date || 'N/A'}</td>
                <td>${(result.market_price || 0).toFixed(2)}</td>
                <td>${(result.lsmc_price || 0).toFixed(2)}</td>
                <td>${difference.toFixed(2)}</td>
                <td class="${mispricingClass}">${(result.undervaluation_percent || 0).toFixed(2)}%</td>
                <td>${result.greeks && result.greeks.delta ? result.greeks.delta.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.gamma ? result.greeks.gamma.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.vega ? result.greeks.vega.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.theta ? result.greeks.theta.toFixed(4) : 'N/A'}</td>
                <td>${result.greeks && result.greeks.rho ? result.greeks.rho.toFixed(4) : 'N/A'}</td>
            `;
            resultsTableBody.appendChild(row);
        });
    }
}); 
// Reusable autocomplete for ticker inputs on the watchlist page
// Usage: attachWatchlistAutocomplete(inputElem, dropdownElem, onSelect)

export function attachWatchlistAutocomplete(inputElem, dropdownElem, onSelect) {
    let searchTimeout = null;
    let selectedIndex = -1;
    let searchResults = [];

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

    function displayResults(results) {
        if (results.length === 0) {
            hideDropdown();
            return;
        }
        dropdownElem.innerHTML = '';
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

            dropdownElem.appendChild(item);
        });
        dropdownElem.style.display = 'block';
        selectedIndex = -1;
    }

    function selectResult(result) {
        inputElem.value = result.symbol;
        hideDropdown();
        if (onSelect) onSelect(result);
    }

    function updateSelection() {
        const items = dropdownElem.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === selectedIndex);
        });
    }

    function hideDropdown() {
        dropdownElem.style.display = 'none';
        selectedIndex = -1;
    }

    inputElem.addEventListener('input', function() {
        const query = this.value.trim();
        if (searchTimeout) clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => performSearch(query), 300);
    });

    inputElem.addEventListener('keydown', function(e) {
        if (dropdownElem.style.display === 'none') return;
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

    document.addEventListener('click', function(e) {
        if (!inputElem.contains(e.target) && !dropdownElem.contains(e.target)) {
            hideDropdown();
        }
    });

    inputElem.addEventListener('focus', function() {
        const query = this.value.trim();
        if (query.length >= 2) {
            performSearch(query);
        }
    });
} 
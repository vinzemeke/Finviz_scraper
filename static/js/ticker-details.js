document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('tickerDetailsModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalTickerSymbol = document.getElementById('modalTickerSymbol');
    const modalContent = document.getElementById('modalContent');

    document.querySelectorAll('.ticker-link').forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const tickerSymbol = this.dataset.ticker;
            modalTickerSymbol.textContent = tickerSymbol;
            modalContent.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Loading ticker details...</p>';
            modal.classList.remove('hidden');

            fetchTickerDetails(tickerSymbol);
        });
    });

    closeModalBtn.addEventListener('click', function() {
        modal.classList.add('hidden');
    });

    // Close modal if clicked outside content
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.classList.add('hidden');
        }
    });
});

function displayTickerDetails(data) {
    if (!data) {
        showError('No data found for this ticker.');
        return;
    }
    // Example: update UI fields
    document.getElementById('ticker-symbol').textContent = data.symbol || '-';
    document.getElementById('company-name').textContent = data.company_name || '-';
    document.getElementById('current-price').textContent = data.current_price !== undefined ? data.current_price : '-';
    document.getElementById('market-cap').textContent = data.market_cap !== undefined ? data.market_cap : '-';
    document.getElementById('pe-ratio').textContent = data.pe_ratio !== undefined ? data.pe_ratio : '-';
    document.getElementById('volume').textContent = data.volume !== undefined ? data.volume : '-';
    document.getElementById('fifty-two-week-high').textContent = data.fifty_two_week_high !== undefined ? data.fifty_two_week_high : '-';
    document.getElementById('fifty-two-week-low').textContent = data.fifty_two_week_low !== undefined ? data.fifty_two_week_low : '-';
    document.getElementById('ema-8').textContent = data.ema_8 !== undefined ? data.ema_8 : '-';
    document.getElementById('ema-21').textContent = data.ema_21 !== undefined ? data.ema_21 : '-';
    document.getElementById('ema-200').textContent = data.ema_200 !== undefined ? data.ema_200 : '-';
    // If chart_path is present, update chart image
    if (data.chart_path) {
        document.getElementById('ticker-chart-img').src = data.chart_path;
        document.getElementById('ticker-chart-img').style.display = '';
    } else {
        document.getElementById('ticker-chart-img').style.display = 'none';
    }
}

function fetchTickerDetails(ticker) {
    fetch(`/api/ticker_details/${ticker}`)
        .then(response => response.json())
        .then(data => {
            displayTickerDetails(data);
        })
        .catch(err => {
            showError('Failed to load ticker details.');
        });
}
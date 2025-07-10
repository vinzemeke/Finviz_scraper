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

let chartInstance = null;
let lastChartData = null;

function renderTickerChart(ticker, interval, showEMAs) {
    const canvas = document.getElementById('tickerChartCanvas');
    if (!canvas) return;
    // Fetch chart data from backend
    fetch(`/api/chart/${ticker}?interval=${interval}`)
        .then(res => res.json())
        .then(data => {
            if (!data || !data.data || !Array.isArray(data.data) || data.data.length === 0) {
                canvas.parentElement.innerHTML = '<div class="text-gray-500 dark:text-gray-400">No chart data available.</div>';
                return;
            }
            lastChartData = data.data;
            const labels = data.data.map(row => row.Date || row.date || row.Datetime || row.datetime);
            const prices = data.data.map(row => row.Close);
            const ema8 = data.data.map(row => row.EMA_8);
            const ema12 = data.data.map(row => row.EMA_12);
            const ema200 = data.data.map(row => row.EMA_200);
            // Destroy previous chart if exists
            if (chartInstance) {
                chartInstance.destroy();
            }
            chartInstance = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Close',
                            data: prices,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59,130,246,0.1)',
                            pointRadius: 0,
                            borderWidth: 2,
                            tension: 0.1,
                        },
                        showEMAs[0] ? {
                            label: 'EMA 8',
                            data: ema8,
                            borderColor: '#f59e42',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            borderDash: [4,2],
                            tension: 0.1,
                        } : null,
                        showEMAs[1] ? {
                            label: 'EMA 12',
                            data: ema12,
                            borderColor: '#10b981',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            borderDash: [2,2],
                            tension: 0.1,
                        } : null,
                        showEMAs[2] ? {
                            label: 'EMA 200',
                            data: ema200,
                            borderColor: '#ef4444',
                            borderWidth: 1.5,
                            pointRadius: 0,
                            borderDash: [8,2],
                            tension: 0.1,
                        } : null,
                    ].filter(Boolean)
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: true },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    interaction: { mode: 'nearest', axis: 'x', intersect: false },
                    scales: {
                        x: { display: true, title: { display: false } },
                        y: { display: true, title: { display: false } }
                    }
                }
            });
        })
        .catch(() => {
            canvas.parentElement.innerHTML = '<div class="text-gray-500 dark:text-gray-400">Failed to load chart data.</div>';
        });
}

function displayTickerDetails(data) {
    if (!data) {
        showError('No data found for this ticker.');
        return;
    }
    // Render info fields in ticker-info-fields
    const infoHtml = `
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <div><span class="font-semibold">Symbol:</span> <span id="ticker-symbol">${data.symbol || '-'}</span></div>
            <div><span class="font-semibold">Company:</span> <span id="company-name">${data.company_name || '-'}</span></div>
            <div><span class="font-semibold">Price:</span> <span id="current-price">${data.current_price !== undefined ? data.current_price : '-'}</span></div>
            <div><span class="font-semibold">Market Cap:</span> <span id="market-cap">${data.market_cap !== undefined ? data.market_cap : '-'}</span></div>
            <div><span class="font-semibold">P/E Ratio:</span> <span id="pe-ratio">${data.pe_ratio !== undefined ? data.pe_ratio : '-'}</span></div>
            <div><span class="font-semibold">Volume:</span> <span id="volume">${data.volume !== undefined ? data.volume : '-'}</span></div>
            <div><span class="font-semibold">52W High:</span> <span id="fifty-two-week-high">${data.fifty_two_week_high !== undefined ? data.fifty_two_week_high : '-'}</span></div>
            <div><span class="font-semibold">52W Low:</span> <span id="fifty-two-week-low">${data.fifty_two_week_low !== undefined ? data.fifty_two_week_low : '-'}</span></div>
        </div>
    `;
    document.getElementById('ticker-info-fields').innerHTML = infoHtml;
    // Render chart for default interval and EMAs
    const ticker = data.symbol;
    const interval = document.getElementById('chart-interval-select').value;
    const showEMAs = [
        document.getElementById('toggle-ema-8').checked,
        document.getElementById('toggle-ema-12').checked,
        document.getElementById('toggle-ema-200').checked
    ];
    renderTickerChart(ticker, interval, showEMAs);
    // Set up controls
    document.getElementById('chart-interval-select').onchange = function() {
        renderTickerChart(ticker, this.value, [
            document.getElementById('toggle-ema-8').checked,
            document.getElementById('toggle-ema-12').checked,
            document.getElementById('toggle-ema-200').checked
        ]);
    };
    document.getElementById('toggle-ema-8').onchange = document.getElementById('toggle-ema-12').onchange = document.getElementById('toggle-ema-200').onchange = function() {
        renderTickerChart(ticker, document.getElementById('chart-interval-select').value, [
            document.getElementById('toggle-ema-8').checked,
            document.getElementById('toggle-ema-12').checked,
            document.getElementById('toggle-ema-200').checked
        ]);
    };
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
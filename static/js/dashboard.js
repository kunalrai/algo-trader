// Update time
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
}
setInterval(updateTime, 1000);
updateTime();

// Fetch status data
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update status cards
        document.getElementById('total-balance').textContent = data.wallet.total_balance.toFixed(2);
        document.getElementById('available-balance').textContent = data.wallet.available_balance.toFixed(2);

        document.getElementById('total-positions').textContent = data.positions.total;
        document.getElementById('max-positions').textContent = data.config.max_positions;
        document.getElementById('long-positions').textContent = data.positions.long;
        document.getElementById('short-positions').textContent = data.positions.short;

        document.getElementById('leverage').textContent = data.config.leverage;
        document.getElementById('stop-loss').textContent = data.config.stop_loss;
        document.getElementById('take-profit').textContent = data.config.take_profit;

        // Update trading mode badge
        const modeBadge = document.getElementById('trading-mode-badge');
        if (data.trading_mode === 'DRY RUN') {
            modeBadge.className = 'px-3 py-1 rounded-full text-sm font-semibold bg-yellow-500 bg-opacity-20 text-yellow-500';
            modeBadge.textContent = '🔸 DRY RUN MODE';
        } else {
            modeBadge.className = 'px-3 py-1 rounded-full text-sm font-semibold bg-green-500 bg-opacity-20 text-green-500';
            modeBadge.textContent = '🟢 LIVE TRADING';
        }

        document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Fetch positions
async function fetchPositions() {
    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();

        const tbody = document.getElementById('positions-table');

        if (positions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-6 py-8 text-center text-gray-400">
                        No active positions
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const pnlClass = pos.pnl >= 0 ? 'profit' : 'loss';
            const sideClass = pos.side === 'long' ? 'text-green-400' : 'text-red-400';

            return `
                <tr class="hover:bg-gray-700">
                    <td class="px-6 py-4 whitespace-nowrap font-medium">${pos.pair}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="${sideClass} font-semibold uppercase">${pos.side}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">${pos.size.toFixed(4)}</td>
                    <td class="px-6 py-4 whitespace-nowrap">$${pos.entry_price.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap">$${pos.current_price.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="${pnlClass} font-semibold">
                            $${pos.pnl.toFixed(2)} (${pos.pnl_percent.toFixed(2)}%)
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">${pos.leverage}x</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <button onclick="closePosition('${pos.id}')"
                                class="bg-red-600 hover:bg-red-700 text-white text-xs font-semibold py-1 px-3 rounded transition duration-200">
                            Close
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error fetching positions:', error);
    }
}

// Fetch prices
async function fetchPrices() {
    try {
        const response = await fetch('/api/prices');
        const prices = await response.json();

        const container = document.getElementById('prices-container');
        container.innerHTML = prices.map(p => `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600">
                <div class="text-sm text-gray-400 mb-1">${p.name}</div>
                <div class="text-lg font-bold text-white">$${p.price.toFixed(2)}</div>
                <div class="text-xs text-gray-500 mt-1">${p.symbol}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error fetching prices:', error);
    }
}

// Fetch trading signals
async function fetchSignals() {
    try {
        const response = await fetch('/api/signals');
        const signals = await response.json();

        const container = document.getElementById('signals-container');
        container.innerHTML = signals.map(signal => {
            // Determine signal styling
            let actionClass = 'text-gray-400';
            let actionBg = 'bg-gray-700';
            let actionText = 'FLAT';

            if (signal.action === 'long') {
                actionClass = 'text-green-400';
                actionBg = 'bg-green-500 bg-opacity-20';
                actionText = '📈 LONG';
            } else if (signal.action === 'short') {
                actionClass = 'text-red-400';
                actionBg = 'bg-red-500 bg-opacity-20';
                actionText = '📉 SHORT';
            }

            // Calculate strength percentage
            const strengthPct = (signal.strength * 100).toFixed(0);
            const strengthColor = signal.strength >= 0.7 ? 'text-green-400' : signal.strength >= 0.5 ? 'text-yellow-400' : 'text-gray-400';

            // Multi-timeframe indicators
            const tfAnalysis = Object.entries(signal.analyses || {}).map(([tf, analysis]) => {
                const tfName = tf.replace('_term', '').toUpperCase();
                const trendIcon = analysis.trend === 'bullish' ? '🟢' : analysis.trend === 'bearish' ? '🔴' : '⚪';
                return `
                    <div class="flex justify-between text-xs mb-1">
                        <span class="text-gray-500">${tfName}</span>
                        <span>${trendIcon} ${analysis.trend.toUpperCase()}</span>
                        <span class="text-gray-400">RSI: ${analysis.rsi_value}</span>
                    </div>
                `;
            }).join('');

            // Support/Resistance Levels
            const sr = signal.support_resistance || {};
            const shortTermSR = sr.short_term || {};
            const longTermSR = sr.long_term || {};

            let srHTML = '';
            if (shortTermSR.support_levels || longTermSR.support_levels) {
                srHTML = `
                    <div class="border-t border-gray-600 pt-2 mt-2">
                        <div class="text-xs text-gray-500 mb-2">Support & Resistance</div>

                        ${shortTermSR.resistance_levels && shortTermSR.resistance_levels.length > 0 ? `
                            <div class="mb-2">
                                <div class="text-xs text-gray-400 mb-1">🔴 Short-term Resistance</div>
                                <div class="flex gap-1 flex-wrap">
                                    ${shortTermSR.resistance_levels.map(r =>
                    `<span class="text-xs bg-red-500 bg-opacity-20 text-red-400 px-2 py-1 rounded">$${r}</span>`
                ).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${shortTermSR.support_levels && shortTermSR.support_levels.length > 0 ? `
                            <div class="mb-2">
                                <div class="text-xs text-gray-400 mb-1">🟢 Short-term Support</div>
                                <div class="flex gap-1 flex-wrap">
                                    ${shortTermSR.support_levels.map(s =>
                    `<span class="text-xs bg-green-500 bg-opacity-20 text-green-400 px-2 py-1 rounded">$${s}</span>`
                ).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${longTermSR.resistance_levels && longTermSR.resistance_levels.length > 0 ? `
                            <div class="mb-2">
                                <div class="text-xs text-gray-400 mb-1">🔴 Long-term Resistance</div>
                                <div class="flex gap-1 flex-wrap">
                                    ${longTermSR.resistance_levels.map(r =>
                    `<span class="text-xs bg-red-600 bg-opacity-20 text-red-300 px-2 py-1 rounded">$${r}</span>`
                ).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${longTermSR.support_levels && longTermSR.support_levels.length > 0 ? `
                            <div>
                                <div class="text-xs text-gray-400 mb-1">🟢 Long-term Support</div>
                                <div class="flex gap-1 flex-wrap">
                                    ${longTermSR.support_levels.map(s =>
                    `<span class="text-xs bg-green-600 bg-opacity-20 text-green-300 px-2 py-1 rounded">$${s}</span>`
                ).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            }

            return `
                <div class="bg-gray-700 rounded-lg p-4 border border-gray-600">
                    <div class="flex justify-between items-center mb-3">
                        <div>
                            <div class="text-lg font-bold text-white">${signal.name}</div>
                            <div class="text-xs text-gray-400">$${signal.current_price.toFixed(2)}</div>
                        </div>
                        <div class="${actionBg} rounded-lg px-3 py-1">
                            <div class="${actionClass} font-bold text-sm">${actionText}</div>
                        </div>
                    </div>

                    <!-- Strength Bar -->
                    <div class="mb-3">
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-400">Strength</span>
                            <span class="${strengthColor} font-semibold">${strengthPct}%</span>
                        </div>
                        <div class="w-full bg-gray-600 rounded-full h-2">
                            <div class="bg-blue-500 h-2 rounded-full transition-all duration-300" style="width: ${strengthPct}%"></div>
                        </div>
                    </div>

                    <!-- Scores -->
                    <div class="grid grid-cols-2 gap-2 mb-3">
                        <div class="bg-gray-800 rounded p-2">
                            <div class="text-xs text-gray-400">Bullish</div>
                            <div class="text-green-400 font-bold">${(signal.bullish_score * 100).toFixed(0)}%</div>
                        </div>
                        <div class="bg-gray-800 rounded p-2">
                            <div class="text-xs text-gray-400">Bearish</div>
                            <div class="text-red-400 font-bold">${(signal.bearish_score * 100).toFixed(0)}%</div>
                        </div>
                    </div>

                    <!-- Timeframe Analysis -->
                    <div class="border-t border-gray-600 pt-2">
                        <div class="text-xs text-gray-500 mb-1">Timeframes</div>
                        ${tfAnalysis}
                    </div>

                    <!-- Support/Resistance Levels -->
                    ${srHTML}
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error fetching signals:', error);
    }
}

// Fetch liquidity data
async function fetchLiquidity() {
    try {
        const response = await fetch('/api/liquidity');
        const liquidity = await response.json();

        const container = document.getElementById('liquidity-container');
        container.innerHTML = liquidity.map(liq => {
            // Determine spread status color
            const spreadColor = liq.spread_status === 'tight' ? 'text-green-400' :
                liq.spread_status === 'normal' ? 'text-yellow-400' : 'text-red-400';

            // Imbalance color
            const imbalanceColor = liq.imbalance_status === 'bullish' ? 'text-green-400' :
                liq.imbalance_status === 'bearish' ? 'text-red-400' : 'text-gray-400';

            // Liquidity status badge
            const liquidityBadge = liq.liquidity_status === 'high' ? '🟢 HIGH' :
                liq.liquidity_status === 'medium' ? '🟡 MEDIUM' : '🔴 LOW';

            return `
                <div class="bg-gray-700 rounded-lg p-4 border border-gray-600">
                    <div class="flex justify-between items-center mb-3">
                        <div class="text-lg font-bold text-white">${liq.name}</div>
                        <div class="text-xs ${spreadColor}">${liq.spread_pct.toFixed(4)}% spread</div>
                    </div>

                    <!-- Order Book Imbalance -->
                    <div class="mb-3">
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-400">Order Imbalance</span>
                            <span class="${imbalanceColor} font-semibold uppercase">${liq.imbalance_status}</span>
                        </div>
                        <div class="flex gap-2">
                            <div class="flex-1 bg-green-500 bg-opacity-20 rounded p-2 text-center">
                                <div class="text-xs text-gray-400">Bids</div>
                                <div class="text-green-400 font-bold">${(liq.imbalance_ratio * 100).toFixed(0)}%</div>
                            </div>
                            <div class="flex-1 bg-red-500 bg-opacity-20 rounded p-2 text-center">
                                <div class="text-xs text-gray-400">Asks</div>
                                <div class="text-red-400 font-bold">${((1 - liq.imbalance_ratio) * 100).toFixed(0)}%</div>
                            </div>
                        </div>
                    </div>

                    <!-- Liquidity & Volume -->
                    <div class="grid grid-cols-2 gap-2 mb-3">
                        <div class="bg-gray-800 rounded p-2">
                            <div class="text-xs text-gray-400">Liquidity</div>
                            <div class="text-white font-semibold">${liquidityBadge}</div>
                        </div>
                        <div class="bg-gray-800 rounded p-2">
                            <div class="text-xs text-gray-400">24h Volume</div>
                            <div class="text-white font-semibold">$${(liq.volume_24h_usd / 1000000).toFixed(1)}M</div>
                        </div>
                    </div>

                    <!-- Market Maker Walls -->
                    ${liq.large_bid_wall ? `
                        <div class="border-t border-gray-600 pt-2 mb-2">
                            <div class="text-xs text-green-400">📊 Buy Wall: $${liq.large_bid_wall.price} (${liq.large_bid_wall.size} ${liq.symbol})</div>
                            <div class="text-xs text-gray-500">Strength: ${liq.large_bid_wall.strength}</div>
                        </div>
                    ` : ''}
                    ${liq.large_ask_wall ? `
                        <div class="${liq.large_bid_wall ? '' : 'border-t border-gray-600 pt-2'}">
                            <div class="text-xs text-red-400">📊 Sell Wall: $${liq.large_ask_wall.price} (${liq.large_ask_wall.size} ${liq.symbol})</div>
                            <div class="text-xs text-gray-500">Strength: ${liq.large_ask_wall.strength}</div>
                        </div>
                    ` : ''}

                    <!-- Market Maker Signal -->
                    ${liq.market_maker_signal !== 'neutral' ? `
                        <div class="border-t border-gray-600 pt-2 mt-2">
                            <div class="text-xs text-gray-400">MM Signal: <span class="font-semibold ${liq.market_maker_signal === 'bullish' ? 'text-green-400' :
                        liq.market_maker_signal === 'bearish' ? 'text-red-400' : 'text-yellow-400'
                    }">${liq.market_maker_signal.toUpperCase()}</span></div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error fetching liquidity:', error);
        document.getElementById('liquidity-container').innerHTML = `
            <div class="col-span-full text-center text-red-400 py-4">
                Error loading liquidity data
            </div>
        `;
    }
}

// Close position
async function closePosition(positionId) {
    if (!confirm('Are you sure you want to close this position?')) {
        return;
    }

    try {
        const response = await fetch('/api/close-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ position_id: positionId })
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            refreshData();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error closing position:', error);
        alert('Failed to close position');
    }
}

// Toggle trading mode
async function toggleTradingMode() {
    if (!confirm('Are you sure you want to toggle the trading mode?')) {
        return;
    }

    try {
        // Get current mode first
        const statusResponse = await fetch('/api/status');
        const statusData = await statusResponse.json();
        const isDryRun = statusData.trading_mode === 'DRY RUN';

        const response = await fetch('/api/trading/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode: isDryRun ? 'live' : 'dry_run' })
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            refreshData();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error toggling mode:', error);
        alert('Failed to toggle trading mode');
    }
}

// Close all positions
async function closeAllPositions() {
    if (!confirm('Are you sure you want to close ALL positions? This cannot be undone!')) {
        return;
    }

    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();

        for (const pos of positions) {
            await closePosition(pos.id);
        }
    } catch (error) {
        console.error('Error closing all positions:', error);
        alert('Failed to close all positions');
    }
}

// Chart variables - Chart.js
const priceCharts = {};
const tradingPairs = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT'];
const pairNames = {
    'BTCUSDT': 'btc',
    'ETHUSDT': 'eth',
    'XRPUSDT': 'xrp',
    'BNBUSDT': 'bnb',
    'SOLUSDT': 'sol'
};
let currentChartTimeframe = '5';

// Create Chart.js chart for a trading pair
function createChartJsChart(canvasId) {
    const ctx = document.getElementById(canvasId);

    if (!ctx) {
        console.error(`Canvas ${canvasId} not found`);
        return null;
    }

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Price',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f3f4f6',
                    bodyColor: '#f3f4f6',
                    borderColor: '#374151',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    },
                    grid: {
                        color: '#374151',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: '#374151',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });

    return chart;
}

// Initialize all price charts using Chart.js
function initPriceChart() {
    tradingPairs.forEach(pair => {
        const pairName = pairNames[pair];
        const canvasId = `chart-${pairName}`;

        // Create Chart.js chart
        priceCharts[pair] = createChartJsChart(canvasId);
    });

    // Add event listener for timeframe selector
    const timeframeSelector = document.getElementById('chart-timeframe-all');
    if (timeframeSelector) {
        timeframeSelector.addEventListener('change', (e) => {
            currentChartTimeframe = e.target.value;
            fetchAllChartData();
        });
    }

    // Initial data fetch
    fetchAllChartData();
}

// Fetch data for all charts
async function fetchAllChartData() {
    const promises = tradingPairs.map(pair => fetchChartDataForPair(pair));
    await Promise.all(promises);
}

// Fetch and update chart data for a specific pair
async function fetchChartDataForPair(pair) {
    try {
        const response = await fetch(`/api/chart/${pair}?interval=${currentChartTimeframe}&limit=100`);
        const data = await response.json();

        if (data.error) {
            console.error(`Chart data error for ${pair}:`, data.error);
            return;
        }

        const pairName = pairNames[pair];
        const chart = priceCharts[pair];

        if (!chart) {
            console.error(`Chart instance not found for ${pair}`);
            return;
        }

        // Update price stats
        const priceElement = document.getElementById(`${pairName}-price`);
        const changeElement = document.getElementById(`${pairName}-change`);

        if (priceElement) {
            priceElement.textContent = `$${data.current_price.toFixed(2)}`;
        }

        if (changeElement) {
            const changeValue = data.change_24h;
            changeElement.textContent = `${changeValue > 0 ? '+' : ''}${changeValue.toFixed(2)}%`;
            changeElement.className = `ml-2 font-bold ${changeValue >= 0 ? 'text-green-400' : 'text-red-400'}`;
        }

        // Prepare data for Chart.js
        const timestamps = data.candles.map(c => {
            let time = c.time;
            // If timestamp is in milliseconds, use directly; if in seconds, convert to milliseconds
            if (time < 10000000000) {
                time = time * 1000;
            }
            return new Date(time);
        });
        const prices = data.candles.map(c => parseFloat(c.close));

        // Update chart data
        chart.data.labels = timestamps;
        chart.data.datasets[0].data = prices;

        // Add support/resistance lines as additional datasets
        const sr = data.support_resistance;

        // Remove old S/R datasets (keep only price dataset at index 0)
        chart.data.datasets = [chart.data.datasets[0]];

        // Add support levels
        if (sr.support_levels && sr.support_levels.length > 0) {
            sr.support_levels.forEach((level, index) => {
                chart.data.datasets.push({
                    label: `Support ${level.toFixed(2)}`,
                    data: timestamps.map(() => level),
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    tension: 0
                });
            });
        }

        // Add resistance levels
        if (sr.resistance_levels && sr.resistance_levels.length > 0) {
            sr.resistance_levels.forEach((level, index) => {
                chart.data.datasets.push({
                    label: `Resistance ${level.toFixed(2)}`,
                    data: timestamps.map(() => level),
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    tension: 0
                });
            });
        }

        // Update the chart
        chart.update('none'); // 'none' for no animation on updates

    } catch (error) {
        console.error(`Error fetching chart data for ${pair}:`, error);
    }
}

// Refresh all data
function refreshData() {
    fetchStatus();
    fetchSignals();
    fetchLiquidity();
    fetchPositions();
    fetchPrices();
    fetchAllChartData();
}

// Auto-refresh every 5 seconds
setInterval(refreshData, 5000);

// Wait for Chart.js library to load before initializing
window.addEventListener('load', function () {
    // Give a small delay to ensure script is fully loaded
    setTimeout(function () {
        if (typeof Chart !== 'undefined') {
            initPriceChart();
            refreshData();
        } else {
            console.error('Chart.js failed to load. Please check your internet connection.');
        }
    }, 100);
});

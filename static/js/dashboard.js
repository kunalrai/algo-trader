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

        // Show P&L in balance card if in dry-run mode
        if (data.wallet.total_pnl !== undefined) {
            const pnl = data.wallet.total_pnl;
            const pnlPercent = data.wallet.pnl_percent;
            const pnlText = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pnl >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%)`;
            const pnlClass = pnl >= 0 ? 'text-xs text-green-400 mt-1' : 'text-xs text-red-400 mt-1';

            // Add P&L display if not exists
            let pnlDisplay = document.getElementById('balance-pnl-display');
            if (!pnlDisplay) {
                const balanceCard = document.getElementById('available-balance').parentElement;
                pnlDisplay = document.createElement('div');
                pnlDisplay.id = 'balance-pnl-display';
                balanceCard.appendChild(pnlDisplay);
            }
            pnlDisplay.className = pnlClass;
            pnlDisplay.textContent = `P&L: ${pnlText}`;
        }

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

        if (!container) {
            return; // Container not found
        }

        container.innerHTML = prices.map(p => `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition-all">
                <div class="flex justify-between items-start mb-1">
                    <div class="text-sm text-gray-400">${p.name}</div>
                    <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse" title="Live update every 1 second"></div>
                </div>
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
        const container = document.getElementById('signals-container');

        // If signals container doesn't exist in dashboard, skip this function
        if (!container) {
            return;
        }

        const response = await fetch('/api/signals');
        const signals = await response.json();

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
        const container = document.getElementById('liquidity-container');

        // If liquidity container doesn't exist in dashboard, skip this function
        if (!container) {
            return;
        }

        const response = await fetch('/api/liquidity');
        const liquidity = await response.json();

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

// Reset simulated wallet
async function resetWallet() {
    // Double confirmation for safety
    if (!confirm('⚠️ WARNING: This will reset your simulated wallet!\n\nAll positions will be closed and your balance will be reset to $1000.\nAll trade history and statistics will be permanently deleted.\n\nAre you absolutely sure?')) {
        return;
    }

    // Second confirmation
    if (!confirm('This is your final confirmation.\n\nReset wallet and delete all data?')) {
        return;
    }

    try {
        const response = await fetch('/api/simulated/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ ' + result.message + '\n\nDashboard will refresh now.');
            // Refresh the entire dashboard to show reset state
            refreshData();
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error resetting wallet:', error);
        alert('Failed to reset wallet. Please try again.');
    }
}

// Chart variables - Chart.js
const priceCharts = {};
// Get trading pairs dynamically from config passed from Flask template
const tradingPairs = Object.values(window.TRADING_PAIRS_CONFIG || {});
const pairNames = {};
// Build pairNames mapping dynamically
if (window.TRADING_PAIRS_CONFIG) {
    Object.entries(window.TRADING_PAIRS_CONFIG).forEach(([name, symbol]) => {
        pairNames[symbol] = name.toLowerCase();
    });
}
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
    // Skip if tradingPairs is not defined or empty
    if (!tradingPairs || tradingPairs.length === 0) {
        return;
    }

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

// Fetch bot runtime status
async function fetchBotStatus() {
    try {
        const response = await fetch('/api/bot/status');
        const status = await response.json();

        // Update bot running indicator
        const isRunning = status.bot_running;
        const statusDot = document.getElementById('bot-status-dot');
        const statusText = document.getElementById('bot-running-text');

        if (isRunning) {
            statusDot.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
            statusText.textContent = 'Running';
            statusText.className = 'text-xs font-semibold text-green-400';
        } else {
            statusDot.className = 'w-2 h-2 rounded-full bg-gray-500';
            statusText.textContent = 'Stopped';
            statusText.className = 'text-xs font-semibold text-gray-400';
        }

        // Update uptime
        document.getElementById('bot-uptime').textContent = status.uptime_formatted || '0s';
        document.getElementById('total-cycles').textContent = status.total_cycles || 0;

        // Update last scan
        document.getElementById('last-scan-time').textContent = status.last_cycle_formatted || 'Never';
        document.getElementById('seconds-since-scan').textContent = status.seconds_since_last_cycle || '--';

        // Update next scan countdown
        document.getElementById('next-scan-countdown').textContent = status.next_scan_countdown || '--';
        document.getElementById('scan-interval').textContent = status.scan_interval || 60;

        // Update pairs monitored
        const pairs = status.pairs_monitored || [];
        document.getElementById('pairs-count').textContent = pairs.length;
        document.getElementById('pairs-list').textContent = pairs.join(', ') || '--';

        // Update current action
        document.getElementById('current-action').textContent = status.current_action || 'Stopped';
        document.getElementById('action-details').textContent = status.action_details || 'Bot not running';
        document.getElementById('last-decision-time').textContent = status.last_decision_formatted || 'N/A';

    } catch (error) {
        console.error('Error fetching bot status:', error);
    }
}

// Refresh all data
function refreshData() {
    console.log('[' + new Date().toLocaleTimeString() + '] Refreshing dashboard data...');
    fetchStatus();
    fetchBotStatus();       // Bot runtime status
    fetchBotActivity();     // NEW: Bot activity feed
    fetchSignals();
    fetchLiquidity();
    fetchPositions();
    fetchPrices();
    fetchAllChartData();
    fetchPnLStats();
    fetchRecentTrades();
}

// Fetch P&L Statistics (Dry-Run Mode)
async function fetchPnLStats() {
    try {
        const response = await fetch('/api/simulated/stats');

        if (response.status === 400) {
            // Not in dry-run mode, hide the section
            document.getElementById('pnl-stats-section').style.display = 'none';
            return;
        }

        const stats = await response.json();

        // Show the P&L section
        document.getElementById('pnl-stats-section').style.display = 'block';

        // Update P&L total
        const pnlElement = document.getElementById('pnl-total');
        const pnl = stats.total_pnl || 0;
        pnlElement.textContent = `$${pnl.toFixed(2)}`;
        pnlElement.className = pnl >= 0 ? 'text-2xl font-bold text-green-400' : 'text-2xl font-bold text-red-400';

        // Update P&L percentage
        const pnlPercentElement = document.getElementById('pnl-percent');
        const pnlPercent = stats.pnl_percent || 0;
        pnlPercentElement.textContent = `${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%`;
        pnlPercentElement.className = pnlPercent >= 0 ? 'text-sm mt-1 text-green-400' : 'text-sm mt-1 text-red-400';

        // Update statistics
        document.getElementById('stat-total-trades').textContent = stats.total_trades || 0;
        document.getElementById('stat-winning').textContent = stats.winning_trades || 0;
        document.getElementById('stat-losing').textContent = stats.losing_trades || 0;
        document.getElementById('stat-win-rate').textContent = `${(stats.win_rate || 0).toFixed(1)}%`;
        document.getElementById('stat-avg-win').textContent = `$${(stats.avg_win || 0).toFixed(2)}`;
        document.getElementById('stat-avg-loss').textContent = `$${(stats.avg_loss || 0).toFixed(2)}`;

        // Calculate and display R:R ratio
        const rrRatio = stats.avg_loss !== 0 ? Math.abs(stats.avg_win / stats.avg_loss) : 0;
        document.getElementById('stat-rr-ratio').textContent = `${rrRatio.toFixed(2)}:1`;

        document.getElementById('stat-largest-win').textContent = `$${(stats.largest_win || 0).toFixed(2)}`;
        document.getElementById('stat-largest-loss').textContent = `$${(stats.largest_loss || 0).toFixed(2)}`;

    } catch (error) {
        console.error('Error fetching P&L stats:', error);
        document.getElementById('pnl-stats-section').style.display = 'none';
    }
}

// Fetch Recent Trades (Dry-Run Mode)
async function fetchRecentTrades() {
    try {
        const response = await fetch('/api/simulated/trades?limit=10');

        if (response.status === 400) {
            return; // Not in dry-run mode
        }

        const trades = await response.json();
        const tbody = document.getElementById('recent-trades-table');

        if (!trades || trades.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-4 py-8 text-center text-gray-400">
                        No trades yet. Start trading to see results here!
                    </td>
                </tr>
            `;
            return;
        }

        // Filter only closed trades
        const closedTrades = trades.filter(t => t.type === 'close');

        tbody.innerHTML = closedTrades.map(trade => {
            const pnlClass = trade.pnl >= 0 ? 'text-green-400' : 'text-red-400';
            const pnlSymbol = trade.pnl >= 0 ? '🟢' : '🔴';
            const sideClass = trade.side === 'long' ? 'text-green-400' : 'text-red-400';
            const time = new Date(trade.timestamp).toLocaleString();

            return `
                <tr class="hover:bg-gray-700">
                    <td class="px-4 py-3 text-sm text-white">${trade.pair}</td>
                    <td class="px-4 py-3 text-sm ${sideClass} font-semibold">${trade.side.toUpperCase()}</td>
                    <td class="px-4 py-3 text-sm text-white">$${trade.entry_price.toFixed(2)}</td>
                    <td class="px-4 py-3 text-sm text-white">$${trade.close_price.toFixed(2)}</td>
                    <td class="px-4 py-3 text-sm ${pnlClass} font-bold">
                        ${pnlSymbol} $${trade.pnl.toFixed(2)} (${trade.pnl_percent.toFixed(2)}%)
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-300">${trade.reason}</td>
                    <td class="px-4 py-3 text-sm text-gray-400">${time}</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error fetching recent trades:', error);
    }
}

// Activity Feed Functions
let currentActivityFilter = 'all';

// Fetch bot activity feed
async function fetchBotActivity() {
    try {
        const limit = 50;
        const url = currentActivityFilter === 'all'
            ? `/api/bot/activity?limit=${limit}`
            : `/api/bot/activity?limit=${limit}&type=${currentActivityFilter}`;

        const response = await fetch(url);
        const activities = await response.json();

        renderActivityFeed(activities);
    } catch (error) {
        console.error('Error fetching bot activity:', error);
    }
}

// Render activity feed
function renderActivityFeed(activities) {
    const feed = document.getElementById('activity-feed');

    if (!activities || activities.length === 0) {
        feed.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <svg class="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>No activity yet</p>
                <p class="text-xs text-gray-500 mt-2">Waiting for bot to start...</p>
            </div>
        `;
        return;
    }

    feed.innerHTML = activities.map(activity => renderActivityItem(activity)).join('');

    // Auto-scroll to top to see newest activities
    feed.scrollTop = 0;
}

// Render individual activity item
function renderActivityItem(activity) {
    const icons = {
        'analyzing_pair': '🔍',
        'market_scan': '📊',
        'signal_analysis': '📈',
        'signal_generated': '📊',
        'signal_rejected': '🚫',
        'signal_flat': '➖',
        'no_signal': '⏸️',
        'pair_scan_start': '🔎',
        'cycle_start': '🔄',
        'position_decision': '💭',
        'decision_start': '🤔',
        'decision_blocked': '⛔',
        'position_sizing': '📐',
        'risk_check_passed': '✅',
        'atr_calculation_failed': '⚠️',
        'position_opened': '🟢',
        'position_open_failed': '❌',
        'position_closed': '🔒',
        'bot_started': '▶️',
        'bot_stopped': '⏹️',
        'bot_initialized': '🤖',
        'risk_check': '⚠️',
        'error': '❌'
    };

    const icon = icons[activity.action_type] || '📌';
    const time = activity.time_formatted;

    // Signal Analysis Activity
    if (activity.action_type === 'signal_analysis') {
        const signalColor = activity.signal === 'long' ? 'text-green-400' :
                           activity.signal === 'short' ? 'text-red-400' : 'text-gray-400';
        const strengthPercent = (activity.strength * 100).toFixed(0);
        const strengthColor = activity.strength >= 0.7 ? 'text-green-400' : 'text-yellow-400';

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">${icon}</span>
                        <div>
                            <p class="font-semibold ${signalColor} text-lg">
                                ${activity.pair} - ${activity.signal.toUpperCase()}
                            </p>
                            <p class="text-xs text-gray-400">
                                Strength: <span class="${strengthColor}">${strengthPercent}%</span>
                                ${activity.strength >= activity.threshold ? ' (✓ Above threshold)' : ' (✗ Below threshold)'}
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap">${time}</span>
                </div>
                <div class="ml-11 text-xs text-gray-300 space-y-1">
                    ${activity.reasons ? activity.reasons.map(r => `<div class="flex items-start gap-2"><span class="text-blue-400">•</span><span>${r}</span></div>`).join('') : ''}
                </div>
            </div>
        `;
    }

    // Position Opened
    if (activity.action_type === 'position_opened') {
        const sideColor = activity.side === 'long' ? 'text-green-400' : 'text-red-400';

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">${icon}</span>
                        <div>
                            <p class="font-semibold ${sideColor} text-lg">
                                Opened ${activity.side.toUpperCase()} on ${activity.pair}
                            </p>
                            <div class="text-xs text-gray-400 mt-1 space-y-1">
                                <div>Entry: <span class="text-white">$${activity.entry_price.toFixed(2)}</span> | Size: <span class="text-white">${activity.size.toFixed(4)}</span></div>
                                <div>TP: <span class="text-green-400">$${activity.take_profit.toFixed(2)}</span> | SL: <span class="text-red-400">$${activity.stop_loss.toFixed(2)}</span> | Margin: <span class="text-yellow-400">$${activity.margin.toFixed(2)}</span></div>
                            </div>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap">${time}</span>
                </div>
            </div>
        `;
    }

    // Position Closed
    if (activity.action_type === 'position_closed') {
        const pnlColor = activity.pnl >= 0 ? 'text-green-400' : 'text-red-400';
        const pnlSign = activity.pnl >= 0 ? '+' : '';

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-gray-500 transition">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">${icon}</span>
                        <div>
                            <p class="font-semibold ${pnlColor} text-lg">
                                Closed ${activity.side.toUpperCase()} on ${activity.pair}
                            </p>
                            <div class="text-xs text-gray-400 mt-1">
                                <div>P&L: <span class="${pnlColor} font-bold">${pnlSign}$${activity.pnl.toFixed(2)} (${pnlSign}${activity.pnl_percent.toFixed(2)}%)</span></div>
                                <div class="text-gray-500 mt-1">Reason: ${activity.reason}</div>
                            </div>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap">${time}</span>
                </div>
            </div>
        `;
    }

    // Position Decision
    if (activity.action_type === 'position_decision') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-gray-300">${activity.pair}: ${activity.decision}</p>
                            <p class="text-xs text-gray-500">${activity.reason}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Analyzing Pair
    if (activity.action_type === 'analyzing_pair') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <p class="text-sm text-gray-300">Analyzing <span class="font-semibold text-blue-400">${activity.pair}</span> (${activity.coin})</p>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Risk Check
    if (activity.action_type === 'risk_check') {
        const statusColor = activity.status === 'passed' ? 'text-green-400' : 'text-yellow-400';

        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium ${statusColor}">${activity.check_type}</p>
                            <p class="text-xs text-gray-500">${activity.details}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Error
    if (activity.action_type === 'error') {
        return `
            <div class="bg-red-900 bg-opacity-20 rounded-lg p-3 border border-red-700">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-semibold text-red-400">Error: ${activity.error_type || 'Unknown'}</p>
                            <p class="text-xs text-gray-300 mt-1">${activity.message || 'An error occurred during trading operations'}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Pair Scan Start - Beginning analysis of a trading pair
    if (activity.action_type === 'pair_scan_start') {
        const timeframes = activity.timeframes ? activity.timeframes.join(', ') : 'multiple timeframes';
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-blue-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-blue-400">Starting Analysis: ${activity.pair || activity.pair_name}</p>
                            <p class="text-xs text-gray-400 mt-1">Scanning market data across ${timeframes} to identify trading opportunities</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Signal Generated - A trading signal was created
    if (activity.action_type === 'signal_generated') {
        const actionColor = activity.action === 'long' ? 'text-green-400' : activity.action === 'short' ? 'text-red-400' : 'text-gray-400';
        const strengthPct = ((activity.strength || 0) * 100).toFixed(1);
        const strengthColor = (activity.strength || 0) >= 0.7 ? 'text-green-400' : (activity.strength || 0) >= 0.5 ? 'text-yellow-400' : 'text-red-400';
        const price = activity.price ? `$${parseFloat(activity.price).toFixed(2)}` : 'N/A';

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 border-l-4 border-l-green-500">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">${icon}</span>
                        <div>
                            <p class="font-semibold ${actionColor} text-lg">
                                Signal Generated: ${(activity.action || 'Unknown').toUpperCase()} on ${activity.pair}
                            </p>
                            <p class="text-xs text-gray-400 mt-1">
                                Strategy: <span class="text-purple-400">${activity.strategy_name || 'Legacy'}</span> |
                                Price: <span class="text-white">${price}</span> |
                                Strength: <span class="${strengthColor}">${strengthPct}%</span>
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap">${time}</span>
                </div>
                ${activity.reasons && activity.reasons.length > 0 ? `
                <div class="ml-11 text-xs text-gray-300 space-y-1 mt-2 bg-gray-800 rounded p-2">
                    <p class="text-gray-500 mb-1">Signal Reasoning:</p>
                    ${activity.reasons.map(r => `<div class="flex items-start gap-2"><span class="text-green-400">•</span><span>${r}</span></div>`).join('')}
                </div>` : ''}
            </div>
        `;
    }

    // Signal Rejected - Signal was too weak
    if (activity.action_type === 'signal_rejected') {
        const strengthPct = ((activity.strength || 0) * 100).toFixed(1);
        const minRequired = ((activity.min_required || 0.6) * 100).toFixed(0);

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 border-l-4 border-l-yellow-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-yellow-400">Signal Rejected: ${activity.pair}</p>
                            <p class="text-xs text-gray-400 mt-1">
                                ${(activity.action || 'Signal').toUpperCase()} signal strength of <span class="text-red-400">${strengthPct}%</span>
                                is below the minimum threshold of <span class="text-green-400">${minRequired}%</span>
                            </p>
                            <p class="text-xs text-gray-500 mt-1">${activity.reason || 'Signal not strong enough to trade'}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Signal Flat - Market is neutral
    if (activity.action_type === 'signal_flat') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-gray-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-gray-400">Market Neutral: ${activity.pair}</p>
                            <p class="text-xs text-gray-500 mt-1">No clear directional bias detected - waiting for better opportunity</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // No Signal - Signal generator returned no data
    if (activity.action_type === 'no_signal') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-gray-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-gray-400">No Signal: ${activity.pair}</p>
                            <p class="text-xs text-gray-500 mt-1">${activity.reason || 'Insufficient data or conditions not met for signal generation'}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Decision Start - Beginning position decision process
    if (activity.action_type === 'decision_start') {
        const actionColor = activity.proposed_action === 'long' ? 'text-green-400' : 'text-red-400';
        const strengthPct = ((activity.signal_strength || 0) * 100).toFixed(1);

        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-purple-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-purple-400">Evaluating Trade: ${activity.pair}</p>
                            <p class="text-xs text-gray-400 mt-1">
                                Considering <span class="${actionColor}">${(activity.proposed_action || '').toUpperCase()}</span> position
                                at <span class="text-white">$${(activity.price || 0).toFixed(2)}</span>
                                with <span class="text-blue-400">${strengthPct}%</span> signal strength
                            </p>
                            <p class="text-xs text-gray-500 mt-1">Strategy: ${activity.strategy || 'Legacy'} | Running risk checks...</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Decision Blocked - Trade was blocked by risk management
    if (activity.action_type === 'decision_blocked') {
        const checkLabels = {
            'existing_position': 'Duplicate Position Check',
            'max_positions': 'Position Limit Check',
            'balance': 'Balance Check'
        };
        const checkLabel = checkLabels[activity.check] || 'Risk Check';

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 border-l-4 border-l-red-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-semibold text-red-400">Trade Blocked: ${activity.pair}</p>
                            <p class="text-xs text-gray-300 mt-1">${activity.reason || 'Position could not be opened'}</p>
                            <p class="text-xs text-gray-500 mt-1">
                                Failed: <span class="text-yellow-400">${checkLabel}</span>
                                ${activity.current_positions !== undefined ? ` | Current positions: ${activity.current_positions}/${activity.max_allowed}` : ''}
                                ${activity.balance !== undefined ? ` | Balance: $${activity.balance.toFixed(2)}` : ''}
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Risk Check Passed
    if (activity.action_type === 'risk_check_passed') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-green-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-green-400">Risk Checks Passed: ${activity.pair}</p>
                            <p class="text-xs text-gray-400 mt-1">
                                Balance: <span class="text-white">$${(activity.available_balance || 0).toFixed(2)}</span> |
                                Open Positions: <span class="text-blue-400">${activity.open_positions || 0}/${activity.max_positions || 3}</span>
                            </p>
                            <p class="text-xs text-gray-500 mt-1">All risk management checks passed - proceeding to position sizing</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Position Sizing
    if (activity.action_type === 'position_sizing') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-blue-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-blue-400">Calculating Position Size: ${activity.pair}</p>
                            <p class="text-xs text-gray-400 mt-1">
                                Balance: <span class="text-white">$${(activity.balance || 0).toFixed(2)}</span> |
                                Max Size: <span class="text-yellow-400">${activity.max_position_pct || 10}%</span> |
                                Leverage: <span class="text-purple-400">${activity.leverage || 10}x</span>
                            </p>
                            <p class="text-xs text-gray-500 mt-1">
                                TP: ${activity.take_profit_pct || 4}% | SL: ${activity.stop_loss_pct || 2}%
                                ${activity.use_atr_stop_loss ? `| ATR: ${activity.atr_value ? activity.atr_value.toFixed(4) : 'calculating...'}` : ''}
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Position Open Failed
    if (activity.action_type === 'position_open_failed') {
        return `
            <div class="bg-red-900 bg-opacity-20 rounded-lg p-3 border border-red-700">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-semibold text-red-400">Failed to Open Position: ${activity.pair}</p>
                            <p class="text-xs text-gray-300 mt-1">
                                Attempted ${(activity.side || '').toUpperCase()} at $${(activity.price || 0).toFixed(2)}
                            </p>
                            <p class="text-xs text-gray-500 mt-1">${activity.reason || 'Position could not be opened - check order manager logs'}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // ATR Calculation Failed
    if (activity.action_type === 'atr_calculation_failed') {
        return `
            <div class="bg-yellow-900 bg-opacity-20 rounded-lg p-3 border border-yellow-700">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-yellow-400">ATR Calculation Warning: ${activity.pair}</p>
                            <p class="text-xs text-gray-300 mt-1">Could not calculate Average True Range for dynamic stop loss</p>
                            <p class="text-xs text-gray-500 mt-1">${activity.error || 'Using default stop loss percentage instead'}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Cycle Start
    if (activity.action_type === 'cycle_start') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-cyan-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-cyan-400">Trading Cycle Started</p>
                            <p class="text-xs text-gray-400 mt-1">
                                Scanning ${activity.pairs_count || 'configured'} trading pairs for opportunities
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Bot Started
    if (activity.action_type === 'bot_started') {
        return `
            <div class="bg-green-900 bg-opacity-20 rounded-lg p-3 border border-green-700">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-semibold text-green-400">Trading Bot Started</p>
                            <p class="text-xs text-gray-300 mt-1">Bot is now actively scanning for trading opportunities</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Bot Stopped
    if (activity.action_type === 'bot_stopped') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-gray-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-semibold text-gray-400">Trading Bot Stopped</p>
                            <p class="text-xs text-gray-300 mt-1">Bot has been stopped - no new trades will be opened</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Bot Initialized
    if (activity.action_type === 'bot_initialized') {
        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600 border-l-4 border-l-blue-500">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">${icon}</span>
                        <div>
                            <p class="text-sm font-medium text-blue-400">Trading Bot Initialized</p>
                            <p class="text-xs text-gray-400 mt-1">Bot configuration loaded and ready to start</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Strategy Decision - Detailed strategy output
    if (activity.action_type === 'strategy_decision') {
        const actionColor = activity.action === 'long' ? 'text-green-400' : activity.action === 'short' ? 'text-red-400' : 'text-gray-400';
        const strengthPct = ((activity.strength || 0) * 100).toFixed(1);

        return `
            <div class="bg-gray-700 rounded-lg p-4 border border-gray-600 border-l-4 border-l-purple-500">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3">
                        <span class="text-2xl">🎯</span>
                        <div>
                            <p class="font-semibold ${actionColor} text-lg">
                                Strategy Decision: ${(activity.action || 'Unknown').toUpperCase()}
                            </p>
                            <p class="text-xs text-gray-400">
                                ${activity.pair} | Strategy: <span class="text-purple-400">${activity.strategy_name || 'Unknown'}</span> |
                                Strength: <span class="text-blue-400">${strengthPct}%</span>
                            </p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-500 whitespace-nowrap">${time}</span>
                </div>
                ${activity.decision_summary ? `<p class="ml-11 text-xs text-gray-300 mb-2">${activity.decision_summary}</p>` : ''}
                ${activity.reasons && activity.reasons.length > 0 ? `
                <div class="ml-11 text-xs text-gray-300 space-y-1 bg-gray-800 rounded p-2">
                    ${activity.reasons.map(r => `<div class="flex items-start gap-2"><span class="text-purple-400">•</span><span>${r}</span></div>`).join('')}
                </div>` : ''}
            </div>
        `;
    }

    // Decision Flow - Step-by-step decision logging
    if (activity.action_type === 'decision_flow') {
        const resultColor = activity.result === 'passed' || activity.result === 'success' ? 'text-green-400' :
                          activity.result === 'failed' || activity.result === 'blocked' ? 'text-red-400' : 'text-gray-400';

        return `
            <div class="bg-gray-700 rounded-lg p-3 border border-gray-600">
                <div class="flex justify-between items-start">
                    <div class="flex items-center gap-3">
                        <span class="text-xl">📋</span>
                        <div>
                            <p class="text-sm font-medium text-gray-300">${activity.pair}: ${activity.step || 'Decision Step'}</p>
                            <p class="text-xs ${resultColor} mt-1">Result: ${activity.result || 'Unknown'}</p>
                            ${activity.details && Object.keys(activity.details).length > 0 ?
                                `<p class="text-xs text-gray-500 mt-1">${JSON.stringify(activity.details)}</p>` : ''}
                        </div>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
            </div>
        `;
    }

    // Generic fallback - now with more detail
    const actionType = activity.action_type || 'unknown';
    const formattedType = actionType.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

    return `
        <div class="bg-gray-700 rounded-lg p-3 border border-gray-600">
            <div class="flex justify-between items-start">
                <div class="flex items-center gap-3">
                    <span class="text-xl">${icon}</span>
                    <div>
                        <p class="text-sm font-medium text-gray-300">${formattedType}</p>
                        ${activity.pair ? `<p class="text-xs text-gray-500">Pair: ${activity.pair}</p>` : ''}
                        ${activity.reason ? `<p class="text-xs text-gray-400 mt-1">${activity.reason}</p>` : ''}
                    </div>
                </div>
                <span class="text-xs text-gray-500">${time}</span>
            </div>
        </div>
    `;
}

// Filter activity by type
function filterActivity(type) {
    currentActivityFilter = type;

    // Update button styles
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('bg-blue-600', 'text-white');
        btn.classList.add('bg-gray-700', 'text-gray-300');
    });

    const activeBtn = document.getElementById(`filter-${type}`);
    if (activeBtn) {
        activeBtn.classList.remove('bg-gray-700', 'text-gray-300');
        activeBtn.classList.add('bg-blue-600', 'text-white');
    }

    // Fetch filtered activities
    fetchBotActivity();
}

// Clear activity feed
function clearActivityFeed() {
    if (confirm('Clear all activity feed data? This cannot be undone.')) {
        const feed = document.getElementById('activity-feed');
        feed.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>Activity feed cleared</p>
                <p class="text-xs text-gray-500 mt-2">New activities will appear here</p>
            </div>
        `;
    }
}

// Initial data load on page ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded - fetching initial data...');
    refreshData();
});

// Auto-refresh prices every 1 second (for real-time price updates)
setInterval(function() {
    fetchPrices();  // Update instrument prices every second
}, 1000);

// Auto-refresh all other data every 5 seconds
setInterval(function() {
    fetchStatus();
    fetchBotStatus();
    fetchBotActivity();
    fetchSignals();
    fetchLiquidity();
    fetchPositions();
    fetchAllChartData();
    fetchPnLStats();
    fetchRecentTrades();
}, 5000);

// ============================================================================
// STRATEGY MANAGEMENT FUNCTIONS
// ============================================================================

async function fetchActiveStrategy() {
    try {
        const response = await fetch('/api/strategies/active');
        const data = await response.json();

        if (data.success) {
            const strategy = data.active_strategy;
            const systemEnabled = data.strategy_system_enabled;

            // Update strategy system status
            const statusText = document.getElementById('strategy-system-text');
            if (systemEnabled && strategy) {
                statusText.textContent = 'Enabled';
                statusText.className = 'text-xs font-semibold text-green-400';
            } else {
                statusText.textContent = 'Legacy Mode';
                statusText.className = 'text-xs font-semibold text-gray-400';
            }

            // Update active strategy info
            if (strategy) {
                document.getElementById('active-strategy-name').textContent = strategy.name;
                document.getElementById('active-strategy-description').textContent = strategy.description;
                document.getElementById('strategy-version').textContent = strategy.version;
                document.getElementById('strategy-timeframes').textContent = strategy.required_timeframes.join(', ');
                document.getElementById('strategy-indicators').textContent = strategy.required_indicators.slice(0, 5).join(', ');

                // Set selector value
                const selector = document.getElementById('strategy-selector');
                if (selector && strategy.id) {
                    selector.value = strategy.id;
                }
            }
        }
    } catch (error) {
        console.error('Error fetching active strategy:', error);
    }
}

async function changeStrategy() {
    const selector = document.getElementById('strategy-selector');
    const strategyId = selector.value;

    if (!confirm(`Change trading strategy to: ${selector.options[selector.selectedIndex].text}?\n\nThis will restart the bot analysis cycle.`)) {
        return;
    }

    try {
        const response = await fetch('/api/strategies/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                strategy_id: strategyId
            })
        });

        const result = await response.json();

        if (result.success) {
            alert(`✅ Strategy changed to: ${result.active_strategy.name}\n\nThe bot will use this strategy for all future analysis.`);
            fetchActiveStrategy();
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error changing strategy:', error);
        alert('❌ Failed to change strategy. Check console for details.');
    }
}

// Wait for Chart.js library to load before initializing charts
window.addEventListener('load', function () {
    // Give a small delay to ensure script is fully loaded
    setTimeout(function () {
        if (typeof Chart !== 'undefined') {
            console.log('Chart.js loaded - initializing charts...');
            initPriceChart();
        } else {
            console.error('Chart.js failed to load. Please check your internet connection.');
        }
    }, 100);

    // Fetch strategy info on page load
    fetchActiveStrategy();
});

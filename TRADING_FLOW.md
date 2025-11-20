# Trading Simulation Flow - Complete Guide

## Overview
This document explains the complete flow of the trading simulation from startup to execution, monitoring, and dashboard updates.

---

## 🚀 System Startup Flow

### 1. User Starts System
```bash
python start_trading.py
```

**What happens:** ([start_trading.py](start_trading.py))
- Line 167: Calls `print_banner()` - Shows ASCII art banner
- Line 168: Calls `print_config()` - Displays trading configuration
- Lines 171-179: If LIVE mode, requires "YES" confirmation (safety check)
- Lines 186-193: Runs pre-flight checks:
  - `check_dependencies()` - Verifies all Python packages installed
  - `check_env_file()` - Checks for .env with API keys
- Lines 202-209: Creates 3 daemon threads:
  - `bot_thread` → Runs `run_bot()`
  - `dashboard_thread` → Runs `run_dashboard()`
  - `browser_thread` → Opens browser to http://localhost:5000
- All three components run in parallel

---

## 🤖 Bot Initialization Flow

### 2. Bot Starts ([run_bot.py](run_bot.py))

**Lines 23-62:**
```python
def main():
    bot_config = {
        'api_key': config.API_KEY,
        'api_secret': config.API_SECRET,
        'trading_pairs': config.TRADING_PAIRS,  # BTC, ETH, XRP, BNB, ZEC
        'timeframes': config.TIMEFRAMES,        # 5m, 1h, 4h
        'indicators': config.INDICATORS,        # EMA, MACD, RSI
        'risk_management': config.RISK_MANAGEMENT,
        'trading_params': config.TRADING_PARAMS
    }

    bot = TradingBot(bot_config)
    bot.start()
```

### 3. TradingBot.__init__() ([trading_bot.py:24-62](trading_bot.py#L24-L62))

**Initializes all components:**

1. **CoinDCXFuturesClient** (Line 34)
   - Handles API authentication
   - Makes requests to CoinDCX exchange

2. **DataFetcher** (Line 41)
   - Fetches candlestick data (OHLCV)
   - Calculates technical indicators (EMA, MACD, RSI)
   - Caches data for 60 seconds

3. **SignalGenerator** (Line 42)
   - Analyzes multi-timeframe data (5m, 1h, 4h)
   - Generates BUY/SELL signals with strength (0-1)
   - Checks EMA crossovers, MACD signals, RSI levels

4. **OrderManager** (Line 47)
   - **CRITICAL**: Initialized with `dry_run=True` and `simulated_balance=1000.0`
   - Creates `SimulatedWallet` instance if dry_run mode
   - Executes market orders (real or simulated)
   - Calculates position sizes, TP/SL levels

5. **PositionManager** (Line 53)
   - Tracks open positions
   - Monitors TP/SL triggers
   - Updates trailing stops

6. **WalletManager** (Line 54)
   - Checks balance health
   - Calculates utilization percentage

---

## 🔄 Main Trading Loop

### 4. TradingBot.start() ([trading_bot.py:64-86](trading_bot.py#L64-L86))

```python
def start():
    self.is_running = True
    self._display_startup_info()  # Show initial wallet balance

    while self.is_running:
        self._trading_cycle()     # Execute one cycle
        time.sleep(60)            # Wait 60 seconds (configurable)
```

**The bot runs an infinite loop, executing a trading cycle every 60 seconds.**

---

## 📊 Trading Cycle Flow (Every 60 Seconds)

### 5. TradingBot._trading_cycle() ([trading_bot.py:121-162](trading_bot.py#L121-L162))

**Step-by-step execution:**

#### **STEP 1: Check Wallet Health** (Lines 128-138)
```python
balance_health = self.wallet_manager.get_balance_health()
if balance_health['status'] == 'critical':
    # Skip new trades, only monitor existing positions
    return
```

#### **STEP 2: Monitor Existing Positions** (Lines 140-141)
```python
self._monitor_and_manage_positions()
```
- Updates current prices for all open positions
- Checks if TP (Take Profit) hit → Close with profit
- Checks if SL (Stop Loss) hit → Close with loss
- Updates trailing stops if enabled

#### **STEP 3: Check Position Limit** (Lines 143-156)
```python
if dry_run:
    current_positions = len(simulated_wallet.get_all_positions())
else:
    current_positions = position_manager.get_open_positions_count()

if current_positions >= max_positions:
    return  # Don't open new positions
```

#### **STEP 4: Scan for New Signals** (Line 159)
```python
self._scan_for_signals()
```

---

## 🔍 Signal Scanning Flow

### 6. TradingBot._scan_for_signals() ([trading_bot.py:258-275](trading_bot.py#L258-L275))

**For each trading pair (BTC, ETH, XRP, BNB, ZEC):**

```python
for name, pair in self.trading_pairs.items():
    signal = self.signal_generator.generate_signal(pair)

    if signal['action'] in ['BUY', 'SELL']:
        strength = signal['strength']

        if strength >= min_signal_strength:  # Default: 0.7
            self._execute_signal(pair, signal)
```

**Signal Generation Logic** ([signal_generator.py](signal_generator.py)):
1. Fetch 3 timeframes: 5m (short), 1h (medium), 4h (long)
2. Calculate indicators for each timeframe:
   - **EMA**: 9, 21, 50, 200 periods
   - **MACD**: 12, 26, 9 (histogram, signal line)
   - **RSI**: 14 period (overbought >70, oversold <30)

3. Analyze signals:
   - **BUY Signal**: EMA bullish cross + MACD positive + RSI oversold
   - **SELL Signal**: EMA bearish cross + MACD negative + RSI overbought

4. Calculate strength (0-1):
   - All 3 timeframes agree → Strength: 0.9-1.0
   - 2 timeframes agree → Strength: 0.6-0.8
   - 1 timeframe only → Strength: 0.3-0.5

---

## ⚡ Order Execution Flow (DRY-RUN MODE)

### 7. TradingBot._execute_signal() ([trading_bot.py:277-355](trading_bot.py#L277-L355))

**When signal strength ≥ 0.7:**

```python
def _execute_signal(pair, signal):
    # Get current price
    current_price = data_fetcher.get_latest_price(pair)  # e.g., $43,250 for BTC

    # Get wallet balance
    if dry_run:
        balance = simulated_wallet.get_balance()  # e.g., $1000 USDT

    # Open position
    result = order_manager.open_position(
        pair=pair,
        side=signal['action'],      # 'BUY' or 'SELL'
        signal_strength=signal['strength'],
        balance=balance,
        current_price=current_price
    )
```

### 8. OrderManager.open_position() ([order_manager.py:214-319](order_manager.py#L214-L319))

**Step-by-step:**

#### **A. Calculate Position Size** (Lines 236-249)
```python
risk_percent = 0.02  # 2% risk per trade
risk_amount = balance * risk_percent  # $1000 * 0.02 = $20

# Calculate position size based on stop loss
stop_loss_percent = 0.02  # 2%
position_size = risk_amount / (price * stop_loss_percent)

# Example:
# price = $43,250
# position_size = $20 / ($43,250 * 0.02) = 0.0231 BTC
```

#### **B. Apply Leverage** (Lines 251-253)
```python
leverage = 5  # 5x leverage
margin_required = (position_size * price) / leverage

# Example:
# margin = (0.0231 * $43,250) / 5 = $200 USDT
```

#### **C. Calculate TP/SL Levels** (Lines 255-260)
```python
if side == 'long':
    take_profit = price * 1.04   # +4% profit
    stop_loss = price * 0.98     # -2% loss

# Example for LONG @ $43,250:
# TP = $44,980
# SL = $42,385
```

#### **D. Execute Order** (Lines 267-279)
```python
if dry_run:
    # Simulated order
    order = {
        'order_id': 'sim_123456',
        'pair': pair,
        'side': side,
        'quantity': position_size,
        'average_price': current_price,  # ✅ FIXED: Uses actual price
        'status': 'filled'
    }
else:
    # Real API call to CoinDCX
    order = client.place_market_order(pair, side, position_size)
```

#### **E. Record in Simulated Wallet** (Lines 291-302)
```python
if dry_run and simulated_wallet:
    simulated_wallet.open_position(
        position_id=position_id,
        pair=pair,
        side=side,
        entry_price=current_price,  # ✅ Real market price
        size=position_size,
        margin=margin,
        leverage=leverage,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
```

### 9. SimulatedWallet.open_position() ([simulated_wallet.py:61-103](simulated_wallet.py#L61-L103))

**What happens in simulated wallet:**

```python
def open_position(...):
    # Lock margin from available balance
    self.data['available_balance'] -= margin  # $1000 - $200 = $800
    self.data['locked_balance'] += margin      # $0 + $200 = $200

    # Store position
    self.data['positions'][position_id] = {
        'pair': 'BTCUSDT',
        'side': 'long',
        'entry_price': 43250.00,
        'current_price': 43250.00,
        'size': 0.0231,
        'margin': 200.00,
        'leverage': 5,
        'stop_loss': 42385.00,
        'take_profit': 44980.00,
        'opened_at': 1705324496
    }

    # Save to disk
    self._save_to_disk()  # Writes to simulated_wallet.json
```

---

## 👀 Position Monitoring Flow

### 10. TradingBot._monitor_and_manage_positions() ([trading_bot.py:164-183](trading_bot.py#L164-L183))

**Every 60 seconds, for each open position:**

```python
for position in simulated_wallet.get_all_positions():
    self._manage_single_position(position)
```

### 11. TradingBot._manage_single_position() ([trading_bot.py:185-245](trading_bot.py#L185-L245))

**For each position:**

#### **A. Get Current Price** (Line 198)
```python
current_price = data_fetcher.get_latest_price(pair)
# Example: BTC now at $43,500 (was $43,250 at entry)
```

#### **B. Update Position Price** (Lines 196-201)
```python
if dry_run:
    simulated_wallet.update_position_price(position_id, current_price)
    # Updates position['current_price'] = 43500
    # Recalculates unrealized P&L
```

#### **C. Check Take Profit** (Lines 207-213)
```python
if side == 'long' and current_price >= take_profit:
    # Price hit $44,980 - CLOSE WITH PROFIT!
    simulated_wallet.close_position(
        position_id,
        current_price,
        reason="Take profit hit"
    )
```

#### **D. Check Stop Loss** (Lines 215-221)
```python
if side == 'long' and current_price <= stop_loss:
    # Price hit $42,385 - CLOSE WITH LOSS!
    simulated_wallet.close_position(
        position_id,
        current_price,
        reason="Stop loss hit"
    )
```

### 12. SimulatedWallet.close_position() ([simulated_wallet.py:123-168](simulated_wallet.py#L123-L168))

**When closing a position:**

```python
def close_position(position_id, close_price, reason):
    position = self.data['positions'][position_id]

    # Calculate P&L
    if side == 'long':
        pnl = (close_price - entry_price) * size * leverage
        # Example: ($44,980 - $43,250) * 0.0231 * 5 = $199.73

    # Release margin + P&L
    self.data['locked_balance'] -= margin      # $200 - $200 = $0
    self.data['available_balance'] += (margin + pnl)  # $800 + $399.73 = $1199.73

    # Record trade history
    self.data['trade_history'].append({
        'pair': 'BTCUSDT',
        'side': 'long',
        'entry_price': 43250.00,
        'exit_price': 44980.00,
        'size': 0.0231,
        'pnl': 199.73,
        'reason': 'Take profit hit',
        'closed_at': 1705328096
    })

    # Remove from open positions
    del self.data['positions'][position_id]

    # Save to disk
    self._save_to_disk()
```

---

## 🌐 Dashboard Flow (Parallel to Bot)

### 13. Dashboard Startup ([app.py](app.py))

**When `start_trading.py` starts the dashboard thread:**

#### **A. Initialize Flask App** (Lines 1-56)
```python
app = Flask(__name__)

# Initialize components
client = CoinDCXFuturesClient(...)
data_fetcher = DataFetcher(client)

# Initialize simulated wallet if dry-run
if config.TRADING_PARAMS['dry_run']:
    simulated_wallet = SimulatedWallet(
        initial_balance=1000.0
    )
```

**IMPORTANT**: The dashboard creates its **own instance** of `SimulatedWallet`, but it reads from the **same JSON file** (`simulated_wallet.json`) that the bot writes to!

#### **B. Start Flask Server** (Lines 855-857)
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 14. Browser Auto-Opens

**User sees dashboard at http://localhost:5000**

### 15. Dashboard JavaScript Initialization ([dashboard.js:822-842](static/js/dashboard.js#L822-L842))

```javascript
// On page load
document.addEventListener('DOMContentLoaded', function() {
    refreshData();  // Fetch initial data
});

// Auto-refresh every 5 seconds
setInterval(refreshData, 5000);
```

### 16. Dashboard Data Refresh ([dashboard.js:710-720](static/js/dashboard.js#L710-L720))

**Every 5 seconds:**

```javascript
function refreshData() {
    fetchStatus();        // Balance, positions count, config
    fetchSignals();       // Current signals for all pairs
    fetchLiquidity();     // Order book depth
    fetchPositions();     // Open positions with live P&L
    fetchPrices();        // Current market prices
    fetchAllChartData();  // Price charts
    fetchPnLStats();      // P&L statistics (dry-run only)
    fetchRecentTrades();  // Trade history (dry-run only)
}
```

---

## 🔄 Real-Time Updates Flow

### How Dashboard Gets Live Data:

#### **A. fetchPositions() API Call** ([dashboard.js:64-113](static/js/dashboard.js#L64-L113))
```javascript
async function fetchPositions() {
    const response = await fetch('/api/positions');
    const positions = await response.json();

    // Update table with current prices and P&L
    tbody.innerHTML = positions.map(pos => `
        <td>${pos.entry_price.toFixed(2)}</td>
        <td>${pos.current_price.toFixed(2)}</td>
        <td>${pos.pnl.toFixed(2)} (${pos.pnl_percent.toFixed(2)}%)</td>
    `);
}
```

#### **B. /api/positions Endpoint** ([app.py:138-171](app.py#L138-L171))
```python
@app.route('/api/positions')
def get_positions():
    if dry_run and simulated_wallet:
        positions = simulated_wallet.get_all_positions()

        # Update each position with current price
        for pos in positions:
            current_price = data_fetcher.get_latest_price(pos['pair'])
            simulated_wallet.update_position_price(pos['position_id'], current_price)

        # Return updated positions with live P&L
        return jsonify(positions)
```

**The API:**
1. Reads positions from `simulated_wallet.json`
2. Fetches current market prices from CoinDCX API
3. Calculates live unrealized P&L
4. Returns to dashboard

#### **C. fetchPnLStats() API Call** ([dashboard.js:722-768](static/js/dashboard.js#L722-L768))
```javascript
async function fetchPnLStats() {
    const response = await fetch('/api/simulated/stats');
    const stats = await response.json();

    // Update statistics display
    document.getElementById('pnl-total').textContent = `$${stats.total_pnl.toFixed(2)}`;
    document.getElementById('stat-win-rate').textContent = `${stats.win_rate.toFixed(1)}%`;
    document.getElementById('stat-total-trades').textContent = stats.total_trades;
}
```

#### **D. /api/simulated/stats Endpoint** ([app.py:525-536](app.py#L525-L536))
```python
@app.route('/api/simulated/stats')
def get_simulated_stats():
    stats = simulated_wallet.get_statistics()
    return jsonify(stats)
```

#### **E. SimulatedWallet.get_statistics()** ([simulated_wallet.py:208-245](simulated_wallet.py#L208-L245))
```python
def get_statistics():
    trades = self.data['trade_history']

    winning = [t for t in trades if t['pnl'] > 0]
    losing = [t for t in trades if t['pnl'] < 0]

    return {
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': (len(winning) / len(trades)) * 100,
        'total_pnl': sum(t['pnl'] for t in trades),
        'avg_win': sum(t['pnl'] for t in winning) / len(winning),
        'avg_loss': sum(t['pnl'] for t in losing) / len(losing),
        'largest_win': max(t['pnl'] for t in winning),
        'largest_loss': min(t['pnl'] for t in losing)
    }
```

---

## 📂 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    start_trading.py                         │
│                   (Main Launcher)                           │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
            │                                 │
    ┌───────▼────────┐              ┌────────▼─────────┐
    │   run_bot.py   │              │     app.py       │
    │  (Trading Bot) │              │   (Dashboard)    │
    └───────┬────────┘              └────────┬─────────┘
            │                                 │
            │                                 │
    ┌───────▼───────────────┐        ┌────────▼──────────────┐
    │   trading_bot.py      │        │  Flask Web Server     │
    │                       │        │  (Port 5000)          │
    │  Every 60s:           │        └────────┬──────────────┘
    │  1. Monitor positions │                 │
    │  2. Scan for signals  │                 │
    │  3. Execute trades    │        ┌────────▼──────────────┐
    └───────┬───────────────┘        │  Browser (Auto-open)  │
            │                        │  http://localhost:5000│
            │                        └────────┬──────────────┘
            │                                 │
    ┌───────▼───────────────┐                │
    │  order_manager.py     │                │
    │  (Execute trades)     │        ┌────────▼──────────────┐
    └───────┬───────────────┘        │   dashboard.js        │
            │                        │   Every 5s:           │
            │                        │   - Fetch positions   │
    ┌───────▼───────────────┐        │   - Fetch P&L stats   │
    │ simulated_wallet.py   │◄───────┤   - Fetch prices      │
    │                       │        │   - Update UI         │
    │  Manages:             │        └───────────────────────┘
    │  - Balance            │
    │  - Positions          │
    │  - Trade history      │
    └───────┬───────────────┘
            │
            │ Reads/Writes
            │
    ┌───────▼───────────────┐
    │simulated_wallet.json  │
    │                       │
    │  {                    │
    │    "initial": 1000,   │
    │    "available": 800,  │
    │    "locked": 200,     │
    │    "positions": {...},│
    │    "trades": [...]    │
    │  }                    │
    └───────────────────────┘
```

---

## ⏱️ Timeline Example

**Here's a real-world example of what happens:**

### **T+0s: System Start**
```
User: python start_trading.py

[Terminal Output]
Starting trading bot...
Starting dashboard...
Opening browser...

Bot: Initialized with $1000 USDT
Bot: Scanning 5 pairs every 60s
Dashboard: Listening on http://localhost:5000
```

### **T+5s: Browser Opens**
```
Browser opens → http://localhost:5000
Dashboard loads → Shows:
  - Balance: $1000
  - Positions: 0/3
  - Leverage: 5x
  - Status: DRY RUN MODE
```

### **T+10s: Dashboard Auto-Refresh #1**
```javascript
fetchStatus() → Balance: $1000, Positions: 0
fetchPrices() → BTC: $43,250, ETH: $2,450
fetchPnLStats() → Total P&L: $0.00, Trades: 0
```

### **T+60s: Bot First Cycle**
```
[Bot Log]
Trading Cycle - 2025-01-15 14:35:00
Balance Health: healthy (0% utilization)
No open positions
Scanning 5 pairs for signals...
  BTC: Analyzing...
    5m: NEUTRAL (0.3)
    1h: BUY (0.6)
    4h: BUY (0.8)
  Combined Signal: BUY (Strength: 0.72) ✅

SIGNAL DETECTED: BTCUSDT - BUY
  Entry: $43,250
  Size: 0.0231 BTC
  Margin: $200 USDT
  TP: $44,980 | SL: $42,385

[DRY-RUN] Position opened successfully
Position ID: pos_1705324500_BTCUSDT
```

### **T+60s: Simulated Wallet Updated**
```json
{
  "initial_balance": 1000.0,
  "available_balance": 800.0,
  "locked_balance": 200.0,
  "positions": {
    "pos_1705324500_BTCUSDT": {
      "pair": "BTCUSDT",
      "side": "long",
      "entry_price": 43250.00,
      "current_price": 43250.00,
      "size": 0.0231,
      "margin": 200.0,
      "leverage": 5,
      "stop_loss": 42385.00,
      "take_profit": 44980.00,
      "opened_at": 1705324500
    }
  },
  "trade_history": []
}
```

### **T+65s: Dashboard Auto-Refresh #2**
```javascript
fetchPositions() →
  Dashboard shows:
  ┌─────────┬──────┬────────┬──────────┬──────────┬─────────┬─────────┬────────┐
  │  PAIR   │ SIDE │  SIZE  │  ENTRY   │ CURRENT  │   P&L   │LEVERAGE │ ACTION │
  ├─────────┼──────┼────────┼──────────┼──────────┼─────────┼─────────┼────────┤
  │BTCUSDT  │LONG  │0.0231  │$43,250   │$43,250   │$0.00    │   5x    │ Close  │
  └─────────┴──────┴────────┴──────────┴──────────┴─────────┴─────────┴────────┘

fetchPnLStats() →
  Total P&L: $0.00 (+0.00%)
  Total Trades: 0
  Win Rate: 0.0%
```

### **T+120s: Bot Second Cycle**
```
[Bot Log]
Trading Cycle - 2025-01-15 14:36:00
Monitoring 1 open positions

Position: BTCUSDT LONG
  Entry: $43,250 → Current: $43,500 (+0.58%)
  Unrealized P&L: +$57.75 (✅ Profit)
  TP: $44,980 (not hit)
  SL: $42,385 (safe)

Scanning for new signals...
  (Max positions not reached: 1/3)
  ETH: NEUTRAL (0.5) - Below threshold
  XRP: NEUTRAL (0.4) - Below threshold
  No new trades
```

### **T+125s: Dashboard Shows Live Update**
```javascript
fetchPositions() →
  ┌─────────┬──────┬────────┬──────────┬──────────┬──────────────┬─────────┬────────┐
  │  PAIR   │ SIDE │  SIZE  │  ENTRY   │ CURRENT  │     P&L      │LEVERAGE │ ACTION │
  ├─────────┼──────┼────────┼──────────┼──────────┼──────────────┼─────────┼────────┤
  │BTCUSDT  │LONG  │0.0231  │$43,250   │$43,500   │$57.75 (0.58%)│   5x    │ Close  │
  └─────────┴──────┴────────┴──────────┴──────────┴──────────────┴─────────┴────────┘
```

### **T+300s: Price Hits Take Profit**
```
[Bot Log]
Trading Cycle - 2025-01-15 14:40:00
Monitoring 1 open positions

Position: BTCUSDT LONG
  Entry: $43,250 → Current: $44,980
  Take Profit HIT! 🎯

Closing position...
  Close Price: $44,980
  P&L: +$199.73 (4.62% profit)

[DRY-RUN] Position closed successfully
Reason: Take profit hit
```

### **T+300s: Wallet Updated**
```json
{
  "initial_balance": 1000.0,
  "available_balance": 1199.73,
  "locked_balance": 0.0,
  "positions": {},
  "trade_history": [
    {
      "pair": "BTCUSDT",
      "side": "long",
      "entry_price": 43250.00,
      "exit_price": 44980.00,
      "size": 0.0231,
      "pnl": 199.73,
      "pnl_percent": 4.62,
      "reason": "Take profit hit",
      "opened_at": 1705324500,
      "closed_at": 1705324800
    }
  ]
}
```

### **T+305s: Dashboard Shows Profit**
```javascript
fetchPnLStats() →
  Total P&L: $199.73 (+19.97%)  🟢
  Total Trades: 1
  Winning Trades: 1
  Losing Trades: 0
  Win Rate: 100.0%
  Avg Win: $199.73
  Largest Win: $199.73

fetchRecentTrades() →
  ┌─────────┬──────┬──────────┬──────────┬──────────┬────────────────────┐
  │  PAIR   │ SIDE │  ENTRY   │   EXIT   │   P&L    │       REASON       │
  ├─────────┼──────┼──────────┼──────────┼──────────┼────────────────────┤
  │BTCUSDT  │LONG  │$43,250   │$44,980   │+$199.73  │Take profit hit     │
  └─────────┴──────┴──────────┴──────────┴──────────┴────────────────────┘
```

---

## 🎯 Summary of Complete Flow

### **BOT (Every 60 seconds):**
1. ✅ Check wallet health
2. ✅ Monitor open positions → Update prices → Check TP/SL
3. ✅ If position limit not reached → Scan for signals
4. ✅ If strong signal (≥0.7) → Open new position
5. ✅ Write all changes to `simulated_wallet.json`

### **DASHBOARD (Every 5 seconds):**
1. ✅ Read `simulated_wallet.json` via API endpoints
2. ✅ Fetch current market prices from CoinDCX
3. ✅ Calculate live unrealized P&L for open positions
4. ✅ Update UI with latest data
5. ✅ Show statistics, charts, trade history

### **KEY FILES:**
- **simulated_wallet.json**: Single source of truth (balance, positions, trades)
- **trading_bot.py**: Main loop (60s cycle)
- **order_manager.py**: Opens/closes positions
- **simulated_wallet.py**: Manages wallet state
- **app.py**: API server for dashboard
- **dashboard.js**: Frontend updates (5s cycle)

### **DATA SYNCHRONIZATION:**
- Bot writes to `simulated_wallet.json` every trade
- Dashboard reads from `simulated_wallet.json` every 5 seconds
- Both share the same file → Always in sync! ✅

---

## 🔧 Troubleshooting

### "Dashboard not updating live"
**Cause**: Only dashboard running, bot not running
**Fix**: Run `python start_trading.py` (not just `python app.py`)

### "Entry price shows $0.00"
**Cause**: Bug in order_manager.py (FIXED in recent update)
**Fix**: Already patched - entry_price now uses current_price

### "Win rate shows 0% with open positions"
**Cause**: Statistics only count closed trades
**Solution**: This is normal - open positions don't affect win rate until closed

---

## 📝 Configuration

**Edit [config.py](config.py) to change:**

```python
TRADING_PARAMS = {
    "dry_run": True,                    # Safe mode
    "simulated_balance": 1000.0,        # Starting balance
    "max_open_positions": 3,            # Max simultaneous trades
    "min_signal_strength": 0.7,         # Signal threshold (0-1)
    "signal_scan_interval": 60          # Scan every 60s
}

RISK_MANAGEMENT = {
    "leverage": 5,                      # 5x leverage
    "stop_loss_percent": 2.0,           # 2% loss limit
    "take_profit_percent": 4.0,         # 4% profit target
    "risk_per_trade": 2.0               # 2% of balance per trade
}
```

---

## 🚀 Quick Start

```bash
# Start everything (bot + dashboard + browser)
python start_trading.py

# View dashboard
http://localhost:5000

# Stop system
Press Ctrl+C
```

---

**That's the complete flow! Every component, every file, every step explained. 🎉**

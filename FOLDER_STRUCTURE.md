# Project Folder Structure & Architecture

## Complete Folder Structure

```
algo-trader/
│
├── strategies/                          # 🆕 STRATEGY SYSTEM
│   ├── __init__.py                      # Package exports
│   ├── README.md                        # Strategy module documentation
│   ├── base_strategy.py                 # Abstract base class for all strategies
│   ├── strategy_manager.py              # Singleton strategy manager
│   ├── ema_crossover_strategy.py        # EMA crossover implementation
│   ├── macd_strategy.py                 # MACD momentum strategy
│   ├── rsi_strategy.py                  # RSI mean reversion strategy
│   └── combined_strategy.py             # Multi-indicator (original logic)
│
├── templates/                           # Flask HTML templates
│   └── dashboard.html                   # Main dashboard UI (with strategy selector)
│
├── static/                              # Static assets
│   └── js/
│       └── dashboard.js                 # Dashboard JavaScript (with strategy functions)
│
├── Core Trading Components/
│   ├── trading_bot.py                   # Main trading bot logic
│   ├── signal_generator.py              # 🔄 Signal generation (strategy-aware)
│   ├── order_manager.py                 # Order execution
│   ├── position_manager.py              # Position tracking
│   ├── wallet_manager.py                # Balance management
│   └── risk_manager.py                  # Risk controls
│
├── Market Data/
│   ├── coindcx_client.py                # Exchange API client
│   ├── data_fetcher.py                  # OHLCV data fetching
│   ├── indicators.py                    # Technical indicators
│   └── market_depth.py                  # Order book analysis
│
├── Monitoring & State/
│   ├── activity_log.py                  # Activity tracking
│   ├── bot_status.py                    # Runtime status
│   └── simulated_wallet.py              # Dry-run wallet
│
├── Configuration & Launch/
│   ├── config.py                        # 🔄 Main configuration (with STRATEGY_CONFIG)
│   ├── app.py                           # 🔄 Flask dashboard server (with strategy APIs)
│   ├── run_bot.py                       # Bot runner
│   └── start_trading.py                 # All-in-one launcher
│
├── Documentation/
│   ├── README.md                        # Main documentation
│   ├── TRADING_FLOW.md                  # How trading works
│   ├── DASHBOARD_ACTIVITY_FEED.md       # Activity feed docs
│   ├── STRATEGY_ARCHITECTURE.md         # 🆕 Strategy system architecture
│   ├── STRATEGY_QUICK_START.md          # 🆕 Quick start guide
│   └── FOLDER_STRUCTURE.md              # 🆕 This file
│
├── Testing & Utilities/
│   ├── test_signals.py                  # Signal testing
│   ├── test_wallet.py                   # Wallet testing
│   └── view_pnl.py                      # P&L viewer
│
├── Data Files (Generated)/
│   ├── bot_status.json                  # Runtime status
│   ├── activity_log.json                # Bot activity
│   ├── simulated_wallet.json            # Dry-run wallet state
│   └── trading_bot.log                  # Log file
│
└── Environment/
    ├── .env                             # API credentials (not in git)
    └── requirements.txt                 # Python dependencies
```

## Architecture Layers

### 1. Presentation Layer (UI)
```
dashboard.html ──> dashboard.js ──> Flask API (app.py)
     │                                      │
     └──────────────────────────────────────┘
                    HTTP/JSON
```

**Components:**
- TailwindCSS-based responsive dashboard
- Real-time updates via polling
- Strategy selector UI
- Activity feed display
- P&L charts and metrics

### 2. API Layer (Flask)
```
app.py
├── /api/status              # Bot status
├── /api/positions           # Open positions
├── /api/bot/status          # Runtime metrics
├── /api/bot/activity        # Activity feed
├── /api/strategies/list     # 🆕 List strategies
├── /api/strategies/active   # 🆕 Active strategy
└── /api/strategies/set      # 🆕 Change strategy
```

### 3. Business Logic Layer (Bot)
```
trading_bot.py
    ├── Initialize components
    ├── Main trading loop
    │   ├── Scan for signals ──> signal_generator.py ──> 🆕 StrategyManager
    │   ├── Check positions
    │   ├── Execute orders
    │   └── Update status
    └── Activity logging
```

### 4. Strategy Layer 🆕
```
StrategyManager (Singleton)
    ├── Register strategies
    ├── Set active strategy
    └── Analyze with strategy
         │
         ├── BaseStrategy (Abstract)
         │   ├── analyze()
         │   ├── get_required_timeframes()
         │   └── get_required_indicators()
         │
         └── Concrete Strategies
             ├── CombinedStrategy
             ├── EMACrossoverStrategy
             ├── MACDStrategy
             └── RSIStrategy
```

### 5. Data Layer
```
DataFetcher
    ├── fetch_ohlcv()
    ├── fetch_multi_timeframe_data()
    └── add_indicators()
         │
         └── TechnicalIndicators
             ├── calculate_ema()
             ├── calculate_macd()
             ├── calculate_rsi()
             └── get_support_resistance()
```

### 6. Exchange Layer
```
CoinDCXFuturesClient
    ├── get_active_instruments()
    ├── get_candlestick_data()
    ├── place_order()
    └── get_positions()
```

## Data Flow

### Signal Generation Flow (With Strategy System)

```
1. Bot Timer Trigger (60s)
        ↓
2. signal_generator.generate_signal(pair)
        ↓
3. data_fetcher.fetch_multi_timeframe_data()
        ↓
4. TechnicalIndicators.add_all_indicators()
        ↓
5. [STRATEGY SYSTEM ENABLED?]
        │
        ├── YES → StrategyManager.analyze_with_active_strategy()
        │           ↓
        │         Active Strategy.analyze(data, price)
        │           ↓
        │         Return signal with reasons
        │
        └── NO → Legacy multi-timeframe analysis
                  ↓
                Return signal
        ↓
6. Bot receives signal
        ↓
7. [Signal strength >= threshold?]
        │
        ├── YES → Open position
        │           ↓
        │         Log activity
        │           ↓
        │         Update dashboard
        │
        └── NO → Continue monitoring
```

### Dashboard Update Flow

```
Browser (Every 5 seconds)
    ↓
Fetch multiple endpoints in parallel:
    ├── /api/status           → Wallet balance, mode
    ├── /api/bot/status       → Uptime, cycles, next scan
    ├── /api/bot/activity     → Recent actions & decisions
    ├── /api/positions        → Open positions
    ├── /api/strategies/active → 🆕 Active strategy info
    └── /api/simulated/pnl    → P&L statistics
    ↓
Update DOM elements
    ↓
Render activity feed
    ↓
Update charts
```

### Strategy Change Flow

```
User clicks "Apply Strategy"
    ↓
JavaScript: changeStrategy()
    ↓
POST /api/strategies/set
    ↓
StrategyManager.set_active_strategy(id, params)
    ↓
Update config.STRATEGY_CONFIG
    ↓
Return success + strategy info
    ↓
Dashboard refreshes strategy display
    ↓
Bot uses new strategy in next cycle
```

## Component Responsibilities

### Trading Bot Core
- **trading_bot.py**: Orchestrates entire trading process
- **run_bot.py**: Initializes and starts the bot
- **start_trading.py**: All-in-one launcher (bot + dashboard)

### Signal Generation
- **signal_generator.py**: Coordinates signal generation (strategy-aware)
- **strategies/**: Pluggable strategy implementations 🆕
- **indicators.py**: Technical indicator calculations

### Order Execution
- **order_manager.py**: Places and manages orders
- **position_manager.py**: Tracks open positions
- **risk_manager.py**: Enforces risk rules

### Market Data
- **coindcx_client.py**: Exchange API wrapper
- **data_fetcher.py**: OHLCV data retrieval
- **market_depth.py**: Order book analysis

### State Management
- **bot_status.py**: Bot runtime state
- **activity_log.py**: All bot actions
- **simulated_wallet.py**: Dry-run wallet
- **wallet_manager.py**: Real wallet (live mode)

### Configuration
- **config.py**: All bot parameters
  - TRADING_PAIRS
  - INDICATORS
  - RISK_MANAGEMENT
  - TRADING_PARAMS
  - **STRATEGY_CONFIG** 🆕

### Dashboard
- **app.py**: Flask API server
- **templates/dashboard.html**: UI layout
- **static/js/dashboard.js**: Client-side logic

## Design Patterns Used

### 1. Strategy Pattern 🆕
**Where:** `strategies/`
**Purpose:** Pluggable trading algorithms
**Benefit:** Easy to add/switch strategies without changing core bot

### 2. Singleton Pattern
**Where:** `StrategyManager`, `BotStatusTracker`, `ActivityLog`
**Purpose:** Single global instance
**Benefit:** Shared state across components

### 3. Factory Pattern (Partial)
**Where:** `StrategyManager.create_custom_strategy()`
**Purpose:** Create strategy instances with custom params
**Benefit:** Flexible strategy instantiation

### 4. Observer Pattern (Implicit)
**Where:** Activity logging
**Purpose:** Log all important events
**Benefit:** Complete audit trail

### 5. Repository Pattern (Implicit)
**Where:** Data fetcher, wallet manager
**Purpose:** Abstract data access
**Benefit:** Easy to swap data sources

## Configuration Hierarchy

```
config.py (Default Settings)
    ↓
Environment Variables (.env)
    ↓
Runtime Changes (API calls)
```

**Priority:** Runtime > .env > config.py

## State Management

### Persistent State (JSON Files)
- `bot_status.json`: Bot runtime metrics
- `activity_log.json`: Historical actions (max 100 entries)
- `simulated_wallet.json`: Dry-run balance and trades

### In-Memory State
- Active strategy instance
- Current positions
- Market data cache (temporary)

### API State
- Real-time prices
- Account balance
- Open orders

## Extensibility Points

### Adding a New Strategy
1. Create `strategies/my_strategy.py`
2. Inherit from `BaseStrategy`
3. Register in `StrategyManager`
4. Add config to `config.py`
5. Add UI option to dashboard

### Adding a New Indicator
1. Add calculation to `indicators.py`
2. Update `add_all_indicators()`
3. Use in strategy's `analyze()` method
4. Add to `get_required_indicators()`

### Adding a New Exchange
1. Create `exchange_client.py`
2. Implement same interface as `CoinDCXFuturesClient`
3. Update `data_fetcher.py` to use new client
4. Update config with exchange-specific settings

### Adding a New Dashboard Widget
1. Add HTML section to `dashboard.html`
2. Add API endpoint to `app.py`
3. Add JavaScript fetch function to `dashboard.js`
4. Add to refresh interval

## Performance Considerations

### Data Fetching
- **Caching:** DataFetcher caches recent candles
- **Batching:** Multi-timeframe data fetched in parallel
- **Rate Limiting:** Respects exchange API limits

### Dashboard Updates
- **Different Intervals:**
  - Prices: 1 second
  - Other data: 5 seconds
- **Parallel Requests:** All API calls made simultaneously
- **Lazy Rendering:** Only update changed DOM elements

### Strategy Execution
- **Lightweight:** Strategies only analyze, don't fetch data
- **Fast Lookups:** Uses pandas for efficient data operations
- **Early Exit:** Returns immediately on invalid data

## Security Considerations

- API keys stored in `.env` (not in git)
- `.env` in `.gitignore`
- No API keys in logs
- Dry-run mode by default
- Position size limits enforced

## Monitoring & Debugging

### Logs
- **File:** `trading_bot.log`
- **Format:** Timestamp, level, message
- **Rotation:** Manual (implement if needed)

### Activity Feed
- **Real-time:** Via dashboard
- **Historical:** Last 100 actions
- **Filterable:** By action type

### Dashboard Metrics
- Bot uptime and cycles
- Active positions
- P&L statistics
- Current strategy
- Next scan countdown

## Testing Strategy

### Unit Testing
- Test individual strategies in isolation
- Mock market data
- Verify signal output format

### Integration Testing
- Test full signal generation flow
- Use historical data
- Verify strategy switching

### Live Testing
- **Always use dry-run mode first**
- Monitor for 24-48 hours
- Check activity feed for unexpected behavior
- Verify P&L tracking accuracy

## Deployment Options

### Local Development
```bash
python start_trading.py
```

### Production (24/7)
- Cloud VM (Oracle, Railway, etc.)
- Background process with supervisor/systemd
- Logging to file
- Automatic restart on failure

## Maintenance Tasks

### Regular
- Monitor logs for errors
- Check dry-run P&L
- Review strategy decisions
- Update dependencies

### Periodic
- Backtest strategies on new data
- Tune strategy parameters
- Add new strategies
- Update exchange API if changed

## Future Enhancements

### Planned
- Strategy backtesting framework
- Performance metrics per strategy
- Machine learning strategies
- Multi-exchange support
- Advanced charting

### Ideas
- Strategy marketplace
- Automated parameter optimization
- Sentiment analysis integration
- Multi-asset portfolio
- Mobile app

---

**Last Updated:** 2025-11-21
**Version:** 2.0 (with Strategy System)

# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User / Operator                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │      app.py         │
                    │  (Entry Point)      │
                    │  - Setup Logging    │
                    │  - Validate Config  │
                    │  - Start Bot        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   trading_bot.py    │
                    │  (Orchestrator)     │
                    │  - Trading Cycle    │
                    │  - Coordination     │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐  ┌──────────▼────────┐  ┌─────────▼────────┐
│ Signal         │  │ Position          │  │ Wallet           │
│ Generator      │  │ Manager           │  │ Manager          │
│ - Analysis     │  │ - Monitor P&L     │  │ - Balance Check  │
│ - Signals      │  │ - TP/SL Check     │  │ - Health         │
└───────┬────────┘  └──────────┬────────┘  └─────────┬────────┘
        │                      │                      │
        │           ┌──────────▼──────────┐           │
        │           │ Order               │           │
        └───────────► Manager             ◄───────────┘
                    │ - Execute Orders    │
                    │ - TP/SL Placement   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐  ┌──────────▼────────┐  ┌─────────▼────────┐
│ Data           │  │ Technical         │  │ CoinDCX          │
│ Fetcher        │  │ Indicators        │  │ API Client       │
│ - Get Candles  │  │ - EMA/MACD/RSI    │  │ - Auth           │
│ - Cache Data   │  │ - Calculations    │  │ - Endpoints      │
└───────┬────────┘  └────────────────────┘  └─────────┬────────┘
        │                                              │
        └──────────────────────┬───────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   CoinDCX Futures   │
                    │      Platform       │
                    │   (Exchange API)    │
                    └─────────────────────┘
```

## Component Interactions

### Trading Cycle Flow

```
START
  │
  ▼
┌────────────────────────────────┐
│ 1. Check Wallet Balance        │ ─── wallet_manager.get_balance_health()
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 2. Monitor Open Positions      │
│    For each position:          │
│    ├─ Get Current Price        │ ─── data_fetcher.get_latest_price()
│    ├─ Calculate P&L            │ ─── position_manager.monitor_position_pnl()
│    ├─ Check TP/SL Hit          │ ─── position_manager.check_tp_sl_hit()
│    ├─ Update Trailing Stop     │ ─── position_manager.update_trailing_stop()
│    └─ Check Signal Reversal    │ ─── signal_generator.should_close_position()
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 3. Check Position Limits       │
│    Can open new positions?     │
└────────────┬───────────────────┘
             │
             ▼
        ┌────┴────┐
        │ NO      │ YES
        │         │
        ▼         ▼
     [WAIT]  ┌────────────────────────────────┐
             │ 4. Scan for Signals            │
             │    For each pair:              │
             │    ├─ Fetch Multi-TF Data      │ ─── data_fetcher.fetch_multi_timeframe_data()
             │    ├─ Add Indicators           │ ─── indicators.add_all_indicators()
             │    ├─ Generate Signal          │ ─── signal_generator.generate_signal()
             │    └─ Evaluate Signal          │
             └────────────┬───────────────────┘
                          │
                          ▼
             ┌────────────────────────────────┐
             │ 5. Execute Trades              │
             │    If signal strength > min:   │
             │    ├─ Calculate Position Size  │ ─── order_manager.calculate_position_size()
             │    ├─ Execute Market Order     │ ─── order_manager.execute_market_order()
             │    ├─ Calculate TP/SL          │ ─── order_manager.calculate_tp_sl_prices()
             │    └─ Place TP/SL Orders       │ ─── order_manager.place_tp_sl_orders()
             └────────────┬───────────────────┘
                          │
                          ▼
             ┌────────────────────────────────┐
             │ 6. Sleep (signal_scan_interval)│
             └────────────┬───────────────────┘
                          │
                          ▼
                      [REPEAT]
```

## Signal Generation Pipeline

```
Input: Trading Pair (e.g., BTCUSDT)
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ Fetch Multi-Timeframe Data                             │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│ │ 5m Data  │  │ 1h Data  │  │ 4h Data  │             │
│ └──────────┘  └──────────┘  └──────────┘             │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Add Technical Indicators to Each Timeframe             │
│ ┌─────────────────────────────────────────────────┐   │
│ │ EMA (9, 15, 20, 50, 200)                        │   │
│ │ MACD (12, 26, 9)                                │   │
│ │ RSI (14)                                        │   │
│ └─────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Analyze Each Timeframe                                  │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│ │ 5m Analysis │  │ 1h Analysis │  │ 4h Analysis │     │
│ │ ├─ Trend    │  │ ├─ Trend    │  │ ├─ Trend    │     │
│ │ ├─ MACD     │  │ ├─ MACD     │  │ ├─ MACD     │     │
│ │ ├─ RSI      │  │ ├─ RSI      │  │ ├─ RSI      │     │
│ │ └─ Strength │  │ └─ Strength │  │ └─ Strength │     │
│ └─────────────┘  └─────────────┘  └─────────────┘     │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Combine Signals with Weights                            │
│                                                          │
│  Bullish Score = (5m × 0.3) + (1h × 0.3) + (4h × 0.4)  │
│  Bearish Score = (5m × 0.3) + (1h × 0.3) + (4h × 0.4)  │
│                                                          │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Determine Action                                        │
│                                                          │
│  IF bullish_score > 0.5 AND bullish > bearish           │
│     → LONG                                              │
│  ELSE IF bearish_score > 0.5 AND bearish > bullish      │
│     → SHORT                                             │
│  ELSE                                                    │
│     → FLAT                                              │
│                                                          │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
Output: Signal {action, strength, price, analyses}
```

## Order Execution Flow

```
Input: Signal (LONG/SHORT)
  │
  ▼
┌──────────────────────────────────┐
│ Get Available Balance            │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Calculate Position Size          │
│                                  │
│ size = (balance × leverage ×    │
│         max_percent × strength)  │
│        / current_price           │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Execute Market Order             │
│ ├─ Pair                          │
│ ├─ Side (long/short)             │
│ ├─ Size                          │
│ └─ Type (market)                 │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Get Order Response               │
│ ├─ Order ID                      │
│ ├─ Position ID                   │
│ ├─ Entry Price                   │
│ └─ Status                        │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Calculate TP/SL Prices           │
│                                  │
│ LONG:                            │
│   TP = entry × (1 + tp%)         │
│   SL = entry × (1 - sl%)         │
│                                  │
│ SHORT:                           │
│   TP = entry × (1 - tp%)         │
│   SL = entry × (1 + sl%)         │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Place TP Order                   │
│ ├─ Position ID                   │
│ ├─ TP Price                      │
│ └─ Size                          │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Place SL Order                   │
│ ├─ Position ID                   │
│ ├─ SL Price                      │
│ └─ Size                          │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Track Position Locally           │
│ └─ Add to active_positions       │
└──────────────────────────────────┘
           │
           ▼
Output: Position opened with TP/SL
```

## Position Management Flow

```
For Each Open Position:
  │
  ▼
┌──────────────────────────────────┐
│ Get Current Market Price         │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Calculate P&L                    │
│                                  │
│ LONG:                            │
│   pnl = (current - entry) × size │
│   pnl% = (current - entry) / entry × 100
│                                  │
│ SHORT:                           │
│   pnl = (entry - current) × size │
│   pnl% = (entry - current) / entry × 100
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Check TP/SL Hit                  │
│                                  │
│ LONG:                            │
│   TP hit if current >= tp_price  │
│   SL hit if current <= sl_price  │
│                                  │
│ SHORT:                           │
│   TP hit if current <= tp_price  │
│   SL hit if current >= sl_price  │
└──────────┬───────────────────────┘
           │
      ┌────┴────┐
      │ Hit?    │
      │         │
     YES       NO
      │         │
      ▼         ▼
┌─────────┐  ┌──────────────────────────────────┐
│ Close   │  │ Update Trailing Stop (if enabled)│
│Position │  │                                  │
└─────────┘  │ If position is profitable:       │
             │   LONG: Move SL up               │
             │   SHORT: Move SL down            │
             │                                  │
             │ new_sl = current × (1 ± trail%)  │
             └──────────┬───────────────────────┘
                        │
                        ▼
             ┌──────────────────────────────────┐
             │ Check Signal Reversal            │
             │                                  │
             │ Generate new signal for pair     │
             │                                  │
             │ LONG position + bearish signal   │
             │   → Close                        │
             │                                  │
             │ SHORT position + bullish signal  │
             │   → Close                        │
             └──────────┬───────────────────────┘
                        │
                   ┌────┴────┐
                   │Reversal?│
                   │         │
                  YES       NO
                   │         │
                   ▼         ▼
             ┌─────────┐  [Continue Holding]
             │ Close   │
             │Position │
             └─────────┘
```

## Data Flow

```
┌─────────────┐
│   CoinDCX   │
│   Futures   │
│  Platform   │
└──────┬──────┘
       │
       │ REST API
       │
       ▼
┌──────────────────────┐
│ coindcx_client.py    │
│ - Authentication     │
│ - HTTP Requests      │
│ - Response Parsing   │
└──────┬───────────────┘
       │
       │ Raw JSON
       │
       ▼
┌──────────────────────┐
│ data_fetcher.py      │
│ - Convert to DataFrame│
│ - Cache Data         │
└──────┬───────────────┘
       │
       │ Pandas DataFrame
       │
       ▼
┌──────────────────────┐
│ indicators.py        │
│ - Calculate EMA      │
│ - Calculate MACD     │
│ - Calculate RSI      │
└──────┬───────────────┘
       │
       │ DataFrame + Indicators
       │
       ▼
┌──────────────────────┐
│ signal_generator.py  │
│ - Analyze Trends     │
│ - Combine Timeframes │
│ - Generate Signals   │
└──────┬───────────────┘
       │
       │ Trading Signal
       │
       ▼
┌──────────────────────┐
│ order_manager.py     │
│ - Calculate Size     │
│ - Execute Orders     │
│ - Set TP/SL          │
└──────┬───────────────┘
       │
       │ Position Data
       │
       ▼
┌──────────────────────┐
│ position_manager.py  │
│ - Track Positions    │
│ - Monitor P&L        │
│ - Manage Exits       │
└──────────────────────┘
```

## Module Dependencies

```
app.py
  └── trading_bot.py
       ├── config.py
       ├── coindcx_client.py
       ├── data_fetcher.py
       │    └── coindcx_client.py
       ├── signal_generator.py
       │    ├── data_fetcher.py
       │    └── indicators.py
       ├── order_manager.py
       │    └── coindcx_client.py
       ├── position_manager.py
       │    └── coindcx_client.py
       └── wallet_manager.py
            └── coindcx_client.py
```

## Error Handling Strategy

```
┌─────────────────────┐
│  Operation Attempt  │
└──────────┬──────────┘
           │
      ┌────▼────┐
      │Success? │
      └────┬────┘
           │
      ┌────┴────┐
     YES        NO
      │          │
      │          ▼
      │    ┌──────────────────┐
      │    │ Log Error        │
      │    ├──────────────────┤
      │    │ API Error?       │
      │    │  → Return None   │
      │    │  → Continue      │
      │    ├──────────────────┤
      │    │ Critical Error?  │
      │    │  → Alert User    │
      │    │  → Stop Bot      │
      │    ├──────────────────┤
      │    │ Transient Error? │
      │    │  → Retry         │
      │    │  → Continue      │
      │    └──────────────────┘
      │
      ▼
┌─────────────────────┐
│ Continue Execution  │
└─────────────────────┘
```

## Logging Architecture

```
┌────────────────────────────────────────┐
│          All Components                │
│  (trading_bot, signal_generator, etc.) │
└──────────────────┬─────────────────────┘
                   │
                   │ Log Messages
                   │
                   ▼
         ┌─────────────────┐
         │ Python Logger   │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│ Console Handler │  │  File Handler    │
│ - Level: INFO   │  │  - Level: DEBUG  │
│ - Format: Short │  │  - Format: Full  │
└─────────────────┘  │  - Rotation: 10MB│
                     │  - Backups: 5    │
                     └──────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ trading_bot.log  │
                     │                  │
                     │ All bot activity │
                     │ Timestamped      │
                     │ Searchable       │
                     └──────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────────────┐
│          Server / Local Machine            │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  Python Environment                  │ │
│  │  - Python 3.8+                       │ │
│  │  - Dependencies (pandas, requests)   │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  Trading Bot Process                 │ │
│  │  - app.py (main)                     │ │
│  │  - trading_bot.py (running)          │ │
│  │  - All modules loaded                │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  Configuration                       │ │
│  │  - config.py (API keys, params)      │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  Logs                                │ │
│  │  - trading_bot.log                   │ │
│  │  - Rotated backup logs               │ │
│  └──────────────────────────────────────┘ │
│                                            │
└──────────────┬─────────────────────────────┘
               │
               │ HTTPS
               │
               ▼
┌──────────────────────────────────────────┐
│         CoinDCX Futures API              │
│         https://api.coindcx.com          │
│                                          │
│  - Market Data                           │
│  - Order Execution                       │
│  - Position Management                   │
│  - Wallet Information                    │
└──────────────────────────────────────────┘
```

---

This architecture enables:
- ✅ Modular, maintainable code
- ✅ Clear separation of concerns
- ✅ Comprehensive error handling
- ✅ Full audit trail via logging
- ✅ Scalable design
- ✅ Easy testing and debugging

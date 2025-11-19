# Market Microstructure Analysis Guide

## Understanding Market Makers & Liquidity

This guide explains how to analyze volume, liquidity, and market maker behavior to gain an edge in futures trading.

---

## 1. Order Book Depth (Liquidity Analysis)

### What It Shows
**Order book depth** reveals where buy and sell orders are stacked, showing support/resistance levels and market maker positioning.

### Key Metrics

#### A. Bid-Ask Spread
```
Spread = Ask Price - Bid Price
Spread % = (Spread / Mid Price) × 100
```

**Interpretation:**
- **Tight spread (< 0.05%)**: High liquidity, easy to enter/exit
- **Wide spread (> 0.2%)**: Low liquidity, high slippage risk
- **Widening spread**: Market makers pulling liquidity (caution!)

#### B. Order Book Imbalance
```
Bid Volume = Sum of all bid quantities within X% of mid price
Ask Volume = Sum of all ask quantities within X% of mid price

Imbalance Ratio = Bid Volume / (Bid Volume + Ask Volume)
```

**Interpretation:**
- **Ratio > 0.60**: Strong buy pressure (bullish)
- **Ratio < 0.40**: Strong sell pressure (bearish)
- **Ratio ≈ 0.50**: Balanced market

#### C. Order Book Delta
```
Delta = Total Bid Volume - Total Ask Volume
```

**Interpretation:**
- **Large positive delta**: Buy walls present (support)
- **Large negative delta**: Sell walls present (resistance)
- **Delta flipping**: Potential reversal signal

### Data Needed
```json
{
  "bids": [
    ["45950.00", "2.5"],    // [price, quantity]
    ["45945.00", "1.8"],
    ["45940.00", "3.2"]
  ],
  "asks": [
    ["45955.00", "1.9"],
    ["45960.00", "2.1"],
    ["45965.00", "2.8"]
  ]
}
```

**CoinDCX API**: `/market_data/orderbook` (public)

---

## 2. Trading Volume Analysis

### What It Shows
Volume shows **actual trading activity** and confirms price movements.

### Key Metrics

#### A. Volume Profile
```
Volume = Number of contracts traded in time period
Volume MA = Moving average of volume (typically 20 periods)
```

**Interpretation:**
- **Volume > MA**: Strong conviction in price move
- **Volume < MA**: Weak move, likely reversal
- **Price up + Volume up**: Healthy uptrend
- **Price up + Volume down**: Divergence, potential top

#### B. Buy vs Sell Volume
```
Buy Volume = Volume on upticks
Sell Volume = Volume on downticks

Buy/Sell Ratio = Buy Volume / Sell Volume
```

**Interpretation:**
- **Ratio > 1.5**: Aggressive buying
- **Ratio < 0.67**: Aggressive selling
- **Ratio ≈ 1.0**: Neutral sentiment

#### C. Volume-Weighted Average Price (VWAP)
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```

**Interpretation:**
- **Price > VWAP**: Bulls in control
- **Price < VWAP**: Bears in control
- **VWAP acts as dynamic support/resistance**

### Data Needed
- Current 24h volume
- Volume by candle (5m, 1h, 4h)
- Tick-by-tick trade data (if available)

**From Existing Data:**
- `get_candlestick_data()` returns `volume` field
- `get_current_prices_realtime()` returns `v` (24h volume)

---

## 3. Liquidity Metrics

### What It Shows
Liquidity measures how easily you can enter/exit positions without moving the market.

### Key Metrics

#### A. Market Depth
```
Depth (2%) = Bid volume + Ask volume within 2% of mid price
```

**Interpretation:**
- **Depth > $500K**: High liquidity
- **Depth < $100K**: Low liquidity, expect slippage

#### B. Slippage Estimate
```
Slippage = (Executed Price - Expected Price) / Expected Price

For market order of size Q:
  Walk through order book summing volume until Q is filled
  Slippage = (Average Fill Price - Best Price) / Best Price
```

**Interpretation:**
- **< 0.1%**: Negligible slippage
- **0.1-0.5%**: Moderate slippage
- **> 0.5%**: High slippage, reduce size or use limit orders

#### C. Effective Spread
```
Effective Spread = 2 × |Execution Price - Mid Price|
```

**Interpretation:**
- Lower is better
- Measures actual cost of trading

### Data Needed
- Full order book (at least 20 levels deep)
- Recent trade history
- Your intended trade size

---

## 4. Market Maker Behavior

### What It Shows
Market makers provide liquidity by placing bid/ask orders. Their behavior signals market conditions.

### Key Indicators

#### A. Large Order Detection
```
Large Order Threshold = 2 × Average Order Size

If order size > threshold:
  - Potential institutional/market maker order
  - Acts as support (buy wall) or resistance (sell wall)
```

**Interpretation:**
- **Large bid appears**: Support, potential bounce
- **Large ask appears**: Resistance, potential rejection
- **Large order pulled**: Market maker spoofing or changing view

#### B. Order Book Velocity
```
Velocity = Change in order book depth over time

High Velocity = Orders being added/removed rapidly
```

**Interpretation:**
- **High velocity on bids**: Market makers accumulating
- **High velocity on asks**: Market makers distributing
- **Both sides high velocity**: Uncertainty, wait for clarity

#### C. Iceberg Orders Detection
```
Iceberg = Large order that shows only small portion

Signs:
  - Same price level keeps refilling after being filled
  - Volume absorbed without price moving
```

**Interpretation:**
- **Buy iceberg**: Strong institutional buying (bullish)
- **Sell iceberg**: Strong institutional selling (bearish)

#### D. Spoofing Detection
```
Spoofing = Placing large fake orders to manipulate price

Signs:
  - Large orders appear then quickly disappear
  - Order pulled when price approaches
  - Pattern repeats multiple times
```

**Interpretation:**
- **Illegal but common in crypto**
- Ignore spoofing orders
- Focus on orders that actually get filled

### Data Needed
- Real-time order book updates (WebSocket)
- Trade history with timestamps
- Order book snapshots at regular intervals

---

## 5. Order Flow Analysis

### What It Shows
**Order flow** shows the actual trades happening and their aggressiveness.

### Key Metrics

#### A. Market Orders vs Limit Orders
```
Market Order = Aggressive (takes liquidity)
Limit Order = Passive (provides liquidity)

Aggression Ratio = Market Orders / Total Orders
```

**Interpretation:**
- **High aggression on buy side**: FOMO, potential top
- **High aggression on sell side**: Panic, potential bottom
- **Balanced**: Healthy market

#### B. Large Trade Detection
```
Large Trade = Trade size > 2 × Average

Track:
  - Time of large trade
  - Direction (buy/sell)
  - Price impact
```

**Interpretation:**
- **Large market buy**: Institutional entering (bullish)
- **Large market sell**: Institutional exiting (bearish)
- **Multiple large trades same direction**: Strong signal

#### C. Trade Imbalance
```
For last N trades:
  Buy Count = Trades at ask price
  Sell Count = Trades at bid price

Imbalance = (Buy Count - Sell Count) / N
```

**Interpretation:**
- **Positive imbalance**: Buyers aggressive
- **Negative imbalance**: Sellers aggressive

### Data Needed
- Recent trades (last 100-1000)
- Trade direction (buy/sell)
- Trade size
- Timestamps

**CoinDCX API**: `/market_data/trades` or WebSocket

---

## 6. Advanced Metrics

### A. Kyle's Lambda (Price Impact)
```
λ = Price Change / Volume Traded

Measures how much price moves per unit of volume
```

**Interpretation:**
- **High λ**: Illiquid market, large impact
- **Low λ**: Liquid market, small impact

### B. Amihud Illiquidity Ratio
```
Illiquidity = Avg(|Return| / Volume)

Higher value = More illiquid
```

### C. Volume Clock
```
Instead of time-based candles, use volume-based:
  - Close candle after X contracts traded
  - Normalizes different volatility periods
```

### D. Order Book Pressure
```
Pressure = Σ(Volume × Distance from mid price)

Weighted by distance - closer orders have more impact
```

---

## Implementation Strategy for CoinDCX

### Phase 1: Basic Volume & Liquidity ✅ (Already Have)
- ✅ Candlestick volume data
- ✅ 24h volume from real-time prices
- ✅ Current price

### Phase 2: Order Book Analysis (Need to Add)
```python
def get_orderbook(pair: str, depth: int = 20):
    """
    Get order book depth
    Returns: bids, asks, spread, imbalance
    """
```

### Phase 3: Trade History Analysis (Need to Add)
```python
def get_recent_trades(pair: str, limit: int = 100):
    """
    Get recent trades
    Returns: trades with size, price, direction, timestamp
    """
```

### Phase 4: Real-Time Monitoring (Future)
- WebSocket connection for live order book
- Real-time trade stream
- Order book delta calculation

---

## Dashboard Metrics to Display

### 1. Liquidity Card
```
┌─────────────────────────────┐
│ BTC Liquidity               │
├─────────────────────────────┤
│ Bid-Ask Spread: 0.02%       │
│ Order Book Imbalance: 58%   │
│ 2% Depth: $2.5M             │
│ Status: 🟢 HIGH LIQUIDITY   │
└─────────────────────────────┘
```

### 2. Volume Card
```
┌─────────────────────────────┐
│ BTC Volume                  │
├─────────────────────────────┤
│ 24h Volume: $450M           │
│ vs Average: +15%            │
│ Buy/Sell Ratio: 1.2         │
│ Trend: 📈 INCREASING        │
└─────────────────────────────┘
```

### 3. Market Maker Signals
```
┌─────────────────────────────┐
│ Market Maker Activity       │
├─────────────────────────────┤
│ Large Buy Wall: $45,800     │
│ Size: 15 BTC (Strong)       │
│ Large Sell Wall: $46,200    │
│ Size: 18 BTC (Strong)       │
│ Range: $400 ($45,800-$46,200)│
└─────────────────────────────┘
```

### 4. Order Flow
```
┌─────────────────────────────┐
│ Order Flow (Last 100 trades)│
├─────────────────────────────┤
│ Market Buys: 62             │
│ Market Sells: 38            │
│ Aggression: 🟢 BULLISH      │
│ Large Trades: 3 (Buy side)  │
└─────────────────────────────┘
```

---

## CoinDCX API Endpoints Needed

### 1. Order Book
```
GET https://public.coindcx.com/market_data/orderbook
Parameters:
  - pair: B-BTC_USDT
  - depth: 20
```

### 2. Recent Trades
```
GET https://public.coindcx.com/market_data/trades
Parameters:
  - pair: B-BTC_USDT
  - limit: 100
```

### 3. 24h Stats (Already Using)
```
GET https://public.coindcx.com/market_data/v3/current_prices/futures/rt
```

---

## Trading Strategies Using This Data

### 1. Liquidity-Based Entry
- Only enter when spread < 0.1%
- Avoid trading during low liquidity periods
- Check slippage estimate before order

### 2. Volume Confirmation
- Enter LONG only when price up + volume up
- Enter SHORT only when price down + volume up
- Exit when volume diverges from price

### 3. Order Book Imbalance
- Strong buy imbalance (>60%) + uptrend = Continue long
- Strong sell imbalance (>60%) + downtrend = Continue short
- Imbalance flips = Potential reversal

### 4. Market Maker Following
- Large buy wall appears = Support, consider long
- Large sell wall appears = Resistance, consider short
- Walls pulled = Exit positions immediately

### 5. Order Flow Trading
- 70%+ market buys in last 100 trades = Strong bullish
- 70%+ market sells in last 100 trades = Strong bearish
- Large trades cluster = Institutional activity

---

## Next Steps

1. **Add order book API** to `coindcx_client.py`
2. **Create `market_depth.py`** module for liquidity analysis
3. **Add order flow tracking** to dashboard
4. **Visualize liquidity heatmaps**
5. **Implement market maker detection**

---

**Remember**: Market microstructure analysis works best when combined with technical analysis. Use both to make informed decisions!

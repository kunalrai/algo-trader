# Custom Trading Strategies Guide

## Overview

The algo-trader platform supports user-uploaded custom trading strategies. This allows you to implement your own trading logic while leveraging the bot's infrastructure for execution, risk management, and monitoring.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Strategy Requirements](#strategy-requirements)
3. [Creating a Custom Strategy](#creating-a-custom-strategy)
4. [Available Indicators](#available-indicators)
5. [Uploading Your Strategy](#uploading-your-strategy)
6. [Testing and Validation](#testing-and-validation)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Download the Template

1. Navigate to the **Strategies** page in the dashboard
2. Click **"Upload Strategy"**
3. Click **"Download Template"** to get the starter template
4. Save it as `my_strategy.py`

### 2. Implement Your Logic

```python
from strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, min_strength=0.6):
        super().__init__()
        self.min_strength = min_strength

    def get_required_timeframes(self):
        return ['5m', '1h', '4h']

    def get_required_indicators(self):
        return ['ema_9', 'ema_21', 'rsi']

    def analyze(self, data, current_price):
        # Your trading logic here
        return {
            'action': 'long',  # 'long', 'short', or 'flat'
            'strength': 0.8,
            'confidence': 0.75,
            'reasons': ['EMA crossover detected'],
            'indicators': {},
            'metadata': {}
        }
```

### 3. Upload via Dashboard

1. Go to **Strategies** page
2. Click **"Upload Strategy"**
3. Select your `.py` file
4. Wait for validation
5. Click **"Use Strategy"** to activate it

---

## Strategy Requirements

### Mandatory Requirements

Your custom strategy **MUST**:

1. ✅ **Inherit from `BaseStrategy`**
   ```python
   from strategies.base_strategy import BaseStrategy

   class MyStrategy(BaseStrategy):
       pass
   ```

2. ✅ **Implement three required methods**:
   - `get_required_timeframes()` - Returns list of timeframes
   - `get_required_indicators()` - Returns list of indicators
   - `analyze(data, current_price)` - Returns trading signal

3. ✅ **Return correct signal format** from `analyze()`:
   ```python
   {
       'action': str,        # 'long', 'short', or 'flat'
       'strength': float,    # 0.0 to 1.0
       'confidence': float,  # 0.0 to 1.0
       'reasons': List[str], # Human-readable explanations
       'indicators': Dict,   # Indicator values used
       'metadata': Dict      # Optional additional data
   }
   ```

4. ✅ **One class per file** - Only one strategy class allowed per file

### Security Restrictions

For safety, the following are **PROHIBITED**:

❌ Importing dangerous modules: `os`, `sys`, `subprocess`, `socket`, `urllib`
❌ Using dangerous functions: `eval()`, `exec()`, `compile()`, `__import__()`
❌ File system operations: `open()`, `file()`, writing to disk
❌ Network operations: HTTP requests, socket connections

### Allowed Imports

✅ Safe for use:
- `numpy`, `pandas` - Data manipulation
- `typing` - Type hints
- `dataclasses` - Data structures
- `datetime`, `math` - Utilities
- `strategies.base_strategy.BaseStrategy` - Required base class

---

## Creating a Custom Strategy

### Step 1: Define Your Class

```python
from strategies.base_strategy import BaseStrategy
from typing import Dict, List

class MyBollingerBandsStrategy(BaseStrategy):
    """
    Custom Bollinger Bands mean reversion strategy

    Enters long when price touches lower band with oversold RSI.
    Enters short when price touches upper band with overbought RSI.
    """

    def __init__(self, bb_period=20, std_dev=2.0, rsi_threshold=30):
        super().__init__()
        self.bb_period = bb_period
        self.std_dev = std_dev
        self.rsi_threshold = rsi_threshold
```

### Step 2: Specify Timeframes

```python
    def get_required_timeframes(self) -> List[str]:
        """Timeframes needed for analysis"""
        return ['5m', '1h', '4h']
```

**Available Timeframes:**
- `'1m'` - 1 minute (high frequency, use carefully)
- `'5m'` - 5 minutes (recommended for signals)
- `'15m'` - 15 minutes
- `'30m'` - 30 minutes
- `'1h'` - 1 hour (recommended for trend confirmation)
- `'4h'` - 4 hours (recommended for long-term trend)
- `'1d'` - 1 day

**Recommendation:** Use at least 2-3 timeframes for multi-timeframe analysis.

### Step 3: Specify Indicators

```python
    def get_required_indicators(self) -> List[str]:
        """Indicators needed for analysis"""
        return [
            'bollinger_upper',
            'bollinger_lower',
            'bollinger_middle',
            'rsi',
            'ema_9',
            'ema_21'
        ]
```

See [Available Indicators](#available-indicators) section for full list.

### Step 4: Implement Analysis Logic

```python
    def analyze(self, data: Dict, current_price: float) -> Dict:
        """
        Main strategy logic

        Args:
            data: Dictionary of DataFrames, one per timeframe
                  e.g., {'5m': df_5m, '1h': df_1h, '4h': df_4h}
            current_price: Current market price

        Returns:
            Signal dictionary
        """
        # Validate data
        if not self.validate_data(data, self.get_required_timeframes()):
            return self._no_signal("Insufficient data")

        # Get data
        df_5m = data['5m']
        latest = df_5m.iloc[-1]

        # Extract indicators
        bb_upper = latest['bollinger_upper']
        bb_lower = latest['bollinger_lower']
        rsi = latest['RSI']

        # Strategy logic
        action = 'flat'
        strength = 0.0
        confidence = 0.0
        reasons = []

        # Long signal
        if current_price <= bb_lower and rsi < self.rsi_threshold:
            action = 'long'
            strength = 0.8
            confidence = 0.75
            reasons.append(f"Price at lower BB: ${current_price:.2f}")
            reasons.append(f"RSI oversold: {rsi:.1f}")

        # Short signal
        elif current_price >= bb_upper and rsi > (100 - self.rsi_threshold):
            action = 'short'
            strength = 0.8
            confidence = 0.75
            reasons.append(f"Price at upper BB: ${current_price:.2f}")
            reasons.append(f"RSI overbought: {rsi:.1f}")

        else:
            reasons.append("No signal - price within bands")

        return {
            'action': action,
            'strength': strength,
            'confidence': confidence,
            'reasons': reasons,
            'indicators': {
                'bb_upper': bb_upper,
                'bb_lower': bb_lower,
                'rsi': rsi,
                'price': current_price
            },
            'metadata': {
                'strategy': 'Bollinger Bands',
                'bb_period': self.bb_period
            }
        }

    def _no_signal(self, reason: str) -> Dict:
        """Helper to return flat signal"""
        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [reason],
            'indicators': {},
            'metadata': {}
        }
```

---

## Available Indicators

### Exponential Moving Averages (EMA)

| Indicator | Description | Period |
|-----------|-------------|--------|
| `ema_9` | Fast EMA | 9 |
| `ema_21` | Medium EMA | 21 |
| `ema_50` | Slow EMA | 50 |
| `ema_200` | Very Slow EMA | 200 |

**Access in DataFrame:**
```python
latest['EMA_9']
latest['EMA_21']
latest['EMA_50']
latest['EMA_200']
```

### MACD (Moving Average Convergence Divergence)

| Indicator | Description |
|-----------|-------------|
| `macd` | MACD line |
| `macd_signal` | Signal line |
| `macd_hist` | Histogram (MACD - Signal) |

**Access in DataFrame:**
```python
latest['MACD']
latest['MACD_signal']
latest['MACD_hist']
```

### RSI (Relative Strength Index)

| Indicator | Description | Period |
|-----------|-------------|--------|
| `rsi` | RSI oscillator | 14 |

**Access in DataFrame:**
```python
latest['RSI']  # Value between 0-100
```

### Bollinger Bands

| Indicator | Description |
|-----------|-------------|
| `bollinger_upper` | Upper band (SMA + 2*StdDev) |
| `bollinger_middle` | Middle band (SMA) |
| `bollinger_lower` | Lower band (SMA - 2*StdDev) |

**Access in DataFrame:**
```python
latest['bollinger_upper']
latest['bollinger_middle']
latest['bollinger_lower']
```

### ATR (Average True Range)

| Indicator | Description | Period |
|-----------|-------------|--------|
| `atr` | ATR for volatility | 14 |

**Access in DataFrame:**
```python
latest['ATR']
```

### OHLCV Data

Always available in every DataFrame:

```python
latest['open']     # Opening price
latest['high']     # High price
latest['low']      # Low price
latest['close']    # Closing price
latest['volume']   # Volume
```

---

## Uploading Your Strategy

### Via Dashboard UI (Recommended)

1. **Navigate to Strategies Page**
   - Login to dashboard
   - Click "Strategies" in navigation

2. **Click "Upload Strategy" Button**

3. **Select or Drag Your `.py` File**
   - Supports drag-and-drop
   - Or click to browse

4. **Wait for Validation**
   - System validates:
     - Inherits from BaseStrategy ✓
     - Has required methods ✓
     - No dangerous imports ✓
     - Proper signal format ✓

5. **Upload Successful**
   - Strategy appears in "Custom Strategies" section
   - Available in strategy selector dropdown

### File Requirements

- **Format:** `.py` (Python file)
- **Size:** Reasonable (< 1MB recommended)
- **Encoding:** UTF-8
- **Naming:** Alphanumeric + underscores (e.g., `my_strategy.py`)

---

## Testing and Validation

### Pre-Upload Validation

The system validates your strategy before saving:

✅ **Syntax Check** - Valid Python syntax
✅ **Import Check** - Only safe imports used
✅ **Class Check** - Inherits from BaseStrategy
✅ **Method Check** - Required methods implemented
✅ **Security Check** - No dangerous operations

### Testing Your Strategy

1. **Start in Paper Trading Mode**
   ```
   Always test new strategies in DRY RUN mode first!
   ```

2. **Upload and Activate Strategy**
   - Upload via dashboard
   - Click "Use Strategy" to activate
   - Bot will restart analysis cycle

3. **Monitor Performance**
   - Watch the Activity feed
   - Check signal generations
   - Review win rate and P&L

4. **Iterate and Improve**
   - Re-upload with same filename to update
   - Version number increments automatically

### Common Validation Errors

| Error | Solution |
|-------|----------|
| "No class inheriting from BaseStrategy found" | Add `from strategies.base_strategy import BaseStrategy` and inherit |
| "Missing required methods" | Implement `analyze()`, `get_required_timeframes()`, `get_required_indicators()` |
| "Disallowed import detected" | Remove imports like `os`, `sys`, `requests` |
| "Dangerous function call detected" | Remove `eval()`, `exec()`, or similar functions |
| "Syntax error" | Check Python syntax (indentation, colons, etc.) |

---

## Best Practices

### 1. Multi-Timeframe Analysis

Use multiple timeframes for confirmation:

```python
def analyze(self, data, current_price):
    df_5m = data['5m']   # Entry signals
    df_1h = data['1h']   # Trend confirmation
    df_4h = data['4h']   # Long-term trend

    # Get 5m signal
    signal_5m = self._analyze_5m(df_5m)

    # Confirm with 1h trend
    if signal_5m == 'long':
        if not self._is_bullish_1h(df_1h):
            return self._no_signal("1h trend not bullish")

    return signal_5m
```

### 2. Signal Strength Calculation

Make strength proportional to conviction:

```python
# Weak signal
if rsi < 40:
    strength = 0.5

# Strong signal
if rsi < 30:
    strength = 0.8

# Very strong signal
if rsi < 20:
    strength = 1.0
```

### 3. Error Handling

Always wrap analysis in try-except:

```python
def analyze(self, data, current_price):
    try:
        # Your logic here
        return signal
    except Exception as e:
        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [f'Error: {str(e)}'],
            'indicators': {},
            'metadata': {}
        }
```

### 4. Clear Reasoning

Provide descriptive reasons:

```python
reasons = [
    "5m: EMA 9 crossed above EMA 21 (golden cross)",
    "5m: RSI oversold at 28.5",
    "1h: Strong bullish trend confirmed",
    "Signal strength: 0.85"
]
```

### 5. Minimum Strength Threshold

Don't trade weak signals:

```python
if strength < self.min_strength:
    return self._no_signal(f"Signal too weak: {strength:.2f}")
```

### 6. Test with Historical Data

Before going live:
- Test in paper trading mode
- Run for at least 1-2 weeks
- Analyze win rate and drawdown
- Adjust parameters if needed

---

## Troubleshooting

### Strategy Not Loading

**Problem:** Strategy uploaded but not appearing in selector

**Solutions:**
1. Check validation passed (green checkmark)
2. Refresh the page
3. Check browser console for errors
4. Re-upload the file

### Strategy Generating No Signals

**Problem:** Strategy active but no trades executed

**Possible Causes:**
1. Signal strength < minimum threshold
   - **Fix:** Lower `min_signal_strength` in config

2. Insufficient data
   - **Fix:** Ensure all required timeframes/indicators available

3. Logic error in `analyze()`
   - **Fix:** Check activity log for error messages

4. Flat signals being returned
   - **Fix:** Review your logic conditions

### Validation Errors

**Problem:** Upload fails with validation error

**Solutions:**
1. Read error message carefully
2. Check [Common Validation Errors](#common-validation-errors)
3. Verify all required methods implemented
4. Remove any disallowed imports
5. Test Python syntax locally first

### Performance Issues

**Problem:** Strategy is slow or timing out

**Solutions:**
1. Reduce complexity in `analyze()`
2. Use fewer timeframes
3. Cache calculations when possible
4. Avoid loops over large datasets

### Unexpected Behavior

**Problem:** Strategy behaving differently than expected

**Debugging Steps:**
1. Add detailed `reasons` to signal output
2. Log indicator values in `indicators` dict
3. Check activity feed for all signals
4. Test with known market conditions
5. Verify data is not None or empty

---

## Advanced Topics

### Using Helper Methods from BaseStrategy

```python
class MyStrategy(BaseStrategy):
    def analyze(self, data, current_price):
        df = data['5m']

        # Use built-in helper methods
        trend_strength = self.calculate_trend_strength(
            df, fast_ema=9, slow_ema=21
        )

        normalized_rsi = self.normalize_rsi(df.iloc[-1]['RSI'])

        # Your logic here
        return signal
```

Available helpers:
- `validate_data(data, timeframes)` - Check data availability
- `calculate_trend_strength(df, fast_ema, slow_ema)` - EMA-based trend (0-1)
- `normalize_rsi(rsi_value)` - Normalize RSI to 0-1 scale

### Stateful Strategies

Maintain state between calls:

```python
class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.last_signal = None
        self.signal_count = 0

    def analyze(self, data, current_price):
        # Avoid flipping signals too frequently
        if self.last_signal == 'long':
            # Require stronger confirmation to flip
            pass

        self.signal_count += 1
        return signal
```

### Dynamic Parameters

Adjust based on market conditions:

```python
def analyze(self, data, current_price):
    df = data['1h']
    atr = df.iloc[-1]['ATR']

    # Tighter thresholds in low volatility
    if atr < 50:
        rsi_threshold = 35
    # Wider thresholds in high volatility
    else:
        rsi_threshold = 30

    # Use dynamic threshold
    if latest['RSI'] < rsi_threshold:
        action = 'long'
```

---

## Example Strategies

### 1. Simple EMA Crossover

```python
class EMACrossStrategy(BaseStrategy):
    def get_required_timeframes(self):
        return ['5m', '1h']

    def get_required_indicators(self):
        return ['ema_9', 'ema_21']

    def analyze(self, data, current_price):
        df = data['5m']
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Golden cross
        if (previous['EMA_9'] <= previous['EMA_21'] and
            current['EMA_9'] > current['EMA_21']):
            return {
                'action': 'long',
                'strength': 0.8,
                'confidence': 0.7,
                'reasons': ['Golden cross detected'],
                'indicators': {},
                'metadata': {}
            }

        # Death cross
        elif (previous['EMA_9'] >= previous['EMA_21'] and
              current['EMA_9'] < current['EMA_21']):
            return {
                'action': 'short',
                'strength': 0.8,
                'confidence': 0.7,
                'reasons': ['Death cross detected'],
                'indicators': {},
                'metadata': {}
            }

        return self._no_signal("No crossover")
```

### 2. RSI Divergence

```python
class RSIDivergenceStrategy(BaseStrategy):
    def get_required_timeframes(self):
        return ['1h']

    def get_required_indicators(self):
        return ['rsi']

    def analyze(self, data, current_price):
        df = data['1h'].tail(10)

        # Find price lows and RSI lows
        price_low_1 = df.iloc[-5]['low']
        price_low_2 = df.iloc[-1]['low']
        rsi_low_1 = df.iloc[-5]['RSI']
        rsi_low_2 = df.iloc[-1]['RSI']

        # Bullish divergence: price lower low, RSI higher low
        if price_low_2 < price_low_1 and rsi_low_2 > rsi_low_1:
            return {
                'action': 'long',
                'strength': 0.75,
                'confidence': 0.65,
                'reasons': ['Bullish RSI divergence detected'],
                'indicators': {},
                'metadata': {}
            }

        return self._no_signal("No divergence")
```

---

## Need Help?

- **Documentation:** See `SYSTEM_SETUP.md` for system setup
- **Examples:** Check `strategies/custom/example_template.py`
- **Built-in Strategies:** Review `strategies/*.py` for reference
- **Issues:** Report bugs on GitHub

---

## Summary Checklist

Before uploading your strategy:

- [ ] Inherits from `BaseStrategy`
- [ ] Implements `get_required_timeframes()`
- [ ] Implements `get_required_indicators()`
- [ ] Implements `analyze(data, current_price)`
- [ ] Returns correct signal format
- [ ] No dangerous imports or functions
- [ ] Includes error handling
- [ ] Tested locally for syntax errors
- [ ] Ready to test in paper trading mode

**Good luck with your custom strategy!** 🚀

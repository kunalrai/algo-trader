# Strategies Module

This folder contains the pluggable trading strategy system for the bot.

## Files

### Core Components

- **`base_strategy.py`** - Abstract base class that all strategies inherit from
- **`strategy_manager.py`** - Singleton manager for registering and switching strategies
- **`__init__.py`** - Package exports for clean imports

### Built-in Strategies

- **`combined_strategy.py`** - Multi-indicator strategy (original bot logic)
- **`ema_crossover_strategy.py`** - Simple EMA crossover strategy
- **`macd_strategy.py`** - MACD momentum strategy
- **`rsi_strategy.py`** - RSI mean reversion strategy

## Quick Reference

### Using Strategies

```python
from strategies.strategy_manager import get_strategy_manager

# Get manager instance
manager = get_strategy_manager()

# Set active strategy
manager.set_active_strategy('ema_crossover')

# Analyze with active strategy
signal = manager.analyze_with_active_strategy(market_data, current_price)
```

### Creating a Strategy

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__(
            name="My Strategy",
            description="What it does",
            params=params or {}
        )

    def get_required_timeframes(self):
        return ['5m', '1h']

    def get_required_indicators(self):
        return ['ema_9', 'ema_21']

    def analyze(self, data, current_price):
        # Your logic here
        return {
            'action': 'long',  # or 'short' or 'flat'
            'strength': 0.8,
            'confidence': 0.8,
            'reasons': ["Why this signal"],
            'indicators': {},
            'metadata': {}
        }
```

### Registering a Strategy

In `strategy_manager.py`:

```python
from strategies.my_strategy import MyStrategy

def _register_builtin_strategies(self):
    # ... existing strategies ...
    self.register_strategy('my_strategy', MyStrategy())
```

## Strategy Comparison

| Strategy | Complexity | Best For | Signals/Day* |
|----------|------------|----------|--------------|
| EMA Crossover | Low | Trending markets | 2-4 |
| MACD | Medium | Momentum | 3-5 |
| RSI | Low | Range-bound | 4-8 |
| Combined | High | All conditions | 2-3 |

*Approximate - varies by market conditions

## Helper Methods

All strategies inherit useful helpers from `BaseStrategy`:

### calculate_trend_strength()
```python
strength = self.calculate_trend_strength(
    ema_fast=100.5,
    ema_slow=98.3,
    price=101.2
)
# Returns 0.0-1.0
```

### normalize_rsi()
```python
strength = self.normalize_rsi(rsi_value=75)
# Returns 0.0-1.0 based on distance from extremes
```

### validate_data()
```python
if not self.validate_data(data):
    return self._flat_signal("Insufficient data")
```

## Signal Format

All strategies must return signals in this format:

```python
{
    'action': str,           # 'long', 'short', or 'flat' (REQUIRED)
    'strength': float,       # 0.0 to 1.0 (REQUIRED)
    'confidence': float,     # 0.0 to 1.0 (REQUIRED)
    'reasons': List[str],    # Human-readable explanations (REQUIRED)
    'indicators': Dict,      # Indicator values used (optional)
    'metadata': Dict         # Strategy-specific data (optional)
}
```

## Configuration

Strategies are configured in `config.py`:

```python
STRATEGY_CONFIG = {
    "enabled": True,
    "active_strategy": "ema_crossover",
    "strategy_params": {
        "ema_crossover": {
            "fast_ema": 9,
            "slow_ema": 21,
            "min_strength": 0.6
        }
    }
}
```

## Documentation

- **Quick Start:** [../STRATEGY_QUICK_START.md](../STRATEGY_QUICK_START.md)
- **Full Architecture:** [../STRATEGY_ARCHITECTURE.md](../STRATEGY_ARCHITECTURE.md)

## Adding New Strategies

1. Create strategy file in this folder
2. Inherit from `BaseStrategy`
3. Implement required methods
4. Register in `strategy_manager.py`
5. Add config in `config.py`
6. Add UI option in dashboard
7. Test with dry-run mode

## Testing Strategies

```bash
# Run bot with strategy
python start_trading.py

# Watch activity feed on dashboard
# http://localhost:5000

# Check logs
tail -f trading_bot.log | grep "Strategy"
```

## Best Practices

1. **Keep it Simple:** Start with single indicator, add complexity gradually
2. **Explain Decisions:** Always provide clear reasons in signal output
3. **Validate Data:** Check for sufficient data before analyzing
4. **Handle Errors:** Return flat signals on errors, don't crash
5. **Document Parameters:** Explain what each parameter does
6. **Set Defaults:** Provide sensible default parameters

## Examples

### Minimal Strategy
```python
class MinimalStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__("Minimal", "Always goes long", params or {})

    def get_required_timeframes(self):
        return ['5m']

    def get_required_indicators(self):
        return ['close']

    def analyze(self, data, current_price):
        return {
            'action': 'long',
            'strength': 0.5,
            'confidence': 0.5,
            'reasons': ["Always bullish"],
            'indicators': {'price': current_price},
            'metadata': {}
        }
```

### Advanced Multi-Timeframe
See `combined_strategy.py` for a complete example of multi-timeframe analysis with weighted voting.

## Strategy Lifecycle

```
1. Bot starts
2. StrategyManager initializes
3. Strategies registered
4. Active strategy set from config
5. Bot requests analysis
6. Manager calls active strategy.analyze()
7. Strategy returns signal
8. Bot executes based on signal
```

## Contributing

When adding a new strategy:

1. Follow existing code style
2. Add comprehensive docstrings
3. Include example parameters
4. Test in dry-run mode first
5. Document in STRATEGY_ARCHITECTURE.md

---

**Note:** All built-in strategies maintain the original bot's risk management and position sizing. Strategies only generate signals - execution is handled by the bot's core systems.

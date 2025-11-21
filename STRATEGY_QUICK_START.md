# Strategy System - Quick Start Guide

## 🚀 Quick Start

### Enable Strategy System

1. Open `config.py`
2. Set `STRATEGY_CONFIG['enabled'] = True`
3. Choose strategy: `STRATEGY_CONFIG['active_strategy'] = 'ema_crossover'`
4. Run: `python start_trading.py`

### Switch Strategies

**Via Dashboard:**
1. Open http://localhost:5000
2. Find "Trading Strategy" section
3. Select from dropdown
4. Click "Apply Strategy"

**Via Config:**
```python
# config.py
STRATEGY_CONFIG = {
    "enabled": True,
    "active_strategy": "macd"  # Change this
}
```

## 📊 Available Strategies

| Strategy | ID | Best For | Timeframes | Risk |
|----------|-----|----------|-----------|------|
| **Combined Multi-Indicator** | `combined` | All-around, trend-following | 5m, 1h, 4h | Medium |
| **EMA Crossover** | `ema_crossover` | Clear trends, simplicity | 5m, 1h, 4h | Medium |
| **MACD** | `macd` | Momentum, trend changes | 5m, 1h | Medium-High |
| **RSI Mean Reversion** | `rsi` | Range-bound markets | 5m, 1h | High |

## 🎯 Strategy Recommendations

### For Beginners
```python
"active_strategy": "ema_crossover"
"strategy_params": {
    "ema_crossover": {
        "min_strength": 0.7  # Higher = fewer, safer trades
    }
}
```

### For Trending Markets
```python
"active_strategy": "combined"  # Or "ema_crossover"
```

### For Range-Bound Markets
```python
"active_strategy": "rsi"
"strategy_params": {
    "rsi": {
        "oversold_level": 30,
        "overbought_level": 70
    }
}
```

### For Momentum Trading
```python
"active_strategy": "macd"
"strategy_params": {
    "macd": {
        "confirm_with_trend": True,
        "min_strength": 0.65
    }
}
```

## 🛠️ Creating Your First Custom Strategy

### 1. Create File: `strategies/simple_strategy.py`

```python
from typing import Dict, List
import pandas as pd
from strategies.base_strategy import BaseStrategy

class SimpleStrategy(BaseStrategy):
    def __init__(self, params: Dict = None):
        super().__init__(
            name="Simple Strategy",
            description="Buy when RSI < 30, sell when RSI > 70",
            params=params or {}
        )

    def get_required_timeframes(self) -> List[str]:
        return ['5m']

    def get_required_indicators(self) -> List[str]:
        return ['rsi']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        df = data['5m']
        rsi = df['rsi'].iloc[-1]

        if rsi < 30:
            return {
                'action': 'long',
                'strength': 0.8,
                'confidence': 0.8,
                'reasons': [f"RSI oversold: {rsi:.1f}"],
                'indicators': {'rsi': rsi},
                'metadata': {}
            }
        elif rsi > 70:
            return {
                'action': 'short',
                'strength': 0.8,
                'confidence': 0.8,
                'reasons': [f"RSI overbought: {rsi:.1f}"],
                'indicators': {'rsi': rsi},
                'metadata': {}
            }

        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [f"RSI neutral: {rsi:.1f}"],
            'indicators': {'rsi': rsi},
            'metadata': {}
        }
```

### 2. Register in `strategies/strategy_manager.py`

```python
from strategies.simple_strategy import SimpleStrategy

def _register_builtin_strategies(self):
    # ... existing ...
    self.register_strategy('simple', SimpleStrategy())
```

### 3. Add to `config.py`

```python
STRATEGY_CONFIG = {
    "active_strategy": "simple",
    "strategy_params": {
        "simple": {}
    }
}
```

### 4. Add to Dashboard

In `templates/dashboard.html`:

```html
<option value="simple">Simple Strategy</option>
```

## 🔧 Common Customizations

### Change Signal Threshold
```python
"strategy_params": {
    "ema_crossover": {
        "min_strength": 0.8  # Default: 0.6 (higher = stricter)
    }
}
```

### Adjust RSI Levels
```python
"strategy_params": {
    "rsi": {
        "oversold_level": 25,     # Default: 30
        "overbought_level": 75    # Default: 70
    }
}
```

### Change EMA Periods
```python
"strategy_params": {
    "ema_crossover": {
        "fast_ema": 12,   # Default: 9
        "slow_ema": 26    # Default: 21
    }
}
```

### Disable Multi-Timeframe
```python
"strategy_params": {
    "ema_crossover": {
        "use_multi_timeframe": False  # Only use 5m
    }
}
```

## 📈 Monitoring Strategy Performance

### 1. Check Activity Feed
Dashboard → "Live Activity Feed" shows strategy decisions and reasoning

### 2. View Strategy Info
Dashboard → "Trading Strategy" section shows active strategy details

### 3. Check Logs
```bash
tail -f trading_bot.log | grep "Strategy"
```

## 🐛 Troubleshooting

### Strategy Not Active
```python
# config.py
STRATEGY_CONFIG = {
    "enabled": True,  # Make sure this is True!
}
```

### No Signals Generated
- Check signal strength threshold
- Lower `min_strength` parameter
- Review activity feed for decision reasons

### Strategy Not in Dropdown
- Register in `strategy_manager.py`
- Add option to dashboard HTML
- Restart bot/dashboard

## 💡 Tips

1. **Start Conservative:** Use default parameters first
2. **Monitor Activity Feed:** Understand why strategy makes decisions
3. **Adjust Gradually:** Change one parameter at a time
4. **Match Strategy to Market:** Trending vs range-bound
5. **Use Dry-Run Mode:** Test strategies risk-free

## 🎓 Learning Path

1. **Week 1:** Use `combined` strategy with defaults
2. **Week 2:** Try `ema_crossover` strategy
3. **Week 3:** Experiment with `rsi` or `macd`
4. **Week 4:** Adjust parameters based on observations
5. **Week 5+:** Create custom strategy

## 📚 More Information

- Full documentation: [STRATEGY_ARCHITECTURE.md](STRATEGY_ARCHITECTURE.md)
- Trading flow: [TRADING_FLOW.md](TRADING_FLOW.md)
- Main README: [README.md](README.md)

## ⚠️ Important Notes

- **Backward Compatible:** Disabling strategy system (`enabled: False`) reverts to original bot logic
- **Real-Time Switching:** Change strategies without restarting bot via dashboard
- **Parameters Persist:** Changes in config persist across bot restarts
- **Activity Logging:** All strategy decisions logged to activity feed

## 🤝 Need Help?

Check the Activity Feed on the dashboard - it shows exactly why the strategy made each decision. This is the best way to understand and debug strategy behavior.

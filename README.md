# Cryptocurrency Futures Trading Bot

Advanced algorithmic trading bot for CoinDCX Futures platform with multi-timeframe technical analysis.

## Features

### Trading Capabilities
- **Multi-Coin Support**: BTC, ETH, XRP, BNB, SOL
- **Multi-Timeframe Analysis**:
  - 5-minute (short-term signals)
  - 1-hour (medium-term trend confirmation)
  - 4-hour (long-term trend)
- **Automated Order Management**: Long and Short positions in Futures market
- **Risk Management**: Automatic TP/SL calculation and execution

### Technical Indicators
- **EMA (Exponential Moving Average)**: 9, 15, 20, 50, 200 periods
- **MACD (Moving Average Convergence Divergence)**: 12, 26, 9 parameters
- **RSI (Relative Strength Index)**: 14 period with overbought/oversold detection

### Position Management
- Open and close futures positions automatically
- Hold trades until TP or SL is reached
- List and monitor all active positions
- Track futures wallet balance
- Trailing stop-loss support

## Architecture

```
app.py                  # Main entry point
├── config.py           # Configuration settings
├── coindcx_client.py   # CoinDCX API client with authentication
├── data_fetcher.py     # Market data retrieval
├── indicators.py       # Technical indicator calculations
├── signal_generator.py # Multi-timeframe signal generation
├── order_manager.py    # Order execution and TP/SL management
├── position_manager.py # Position monitoring and tracking
├── wallet_manager.py   # Futures wallet balance management
└── trading_bot.py      # Main orchestrator
```

## Installation

### Prerequisites
- Python 3.8 or higher
- CoinDCX account with Futures API enabled
- API Key and Secret from CoinDCX

### Setup

1. **Clone or download this repository**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure API credentials**

Edit [config.py](config.py) and add your CoinDCX API credentials:

```python
API_KEY = "your_actual_api_key"
API_SECRET = "your_actual_api_secret"
```

4. **Customize trading parameters** (Optional)

In [config.py](config.py), adjust settings according to your risk tolerance:

```python
RISK_MANAGEMENT = {
    "max_position_size_percent": 10,  # Max % of balance per trade
    "leverage": 5,                     # Leverage multiplier
    "stop_loss_percent": 2.0,          # Stop loss %
    "take_profit_percent": 4.0,        # Take profit %
    "trailing_stop": True,             # Enable trailing stop
    "trailing_stop_percent": 1.5       # Trailing stop distance
}
```

## Usage

### Start the Bot

```bash
python app.py
```

The bot will:
1. Validate configuration
2. Display settings summary
3. Wait for your confirmation
4. Start trading cycle

### Trading Cycle

The bot continuously:
1. **Monitors wallet balance** and health
2. **Manages existing positions** (check TP/SL, update trailing stops)
3. **Scans for new signals** across all trading pairs
4. **Executes trades** when strong signals are detected

### Stopping the Bot

Press `Ctrl+C` to gracefully stop the bot. It will display a final summary of positions and balance.

## Configuration Reference

### Trading Pairs ([config.py:12-18](config.py#L12-L18))
```python
TRADING_PAIRS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "XRP": "XRPUSDT",
    "BNB": "BNBUSDT",
    "SOL": "SOLUSDT"
}
```

### Timeframes ([config.py:20-25](config.py#L20-L25))
```python
TIMEFRAMES = {
    "short_term": "5m",   # 5 minutes
    "medium_term": "1h",  # 1 hour
    "long_term": "4h"     # 4 hours
}
```

### Risk Management ([config.py:39-46](config.py#L39-L46))
- `max_position_size_percent`: Maximum % of balance to use per trade
- `leverage`: Leverage multiplier (be cautious with high leverage)
- `stop_loss_percent`: Stop loss distance from entry
- `take_profit_percent`: Take profit distance from entry
- `trailing_stop`: Enable/disable trailing stop
- `trailing_stop_percent`: Trailing stop distance

### Trading Parameters ([config.py:48-55](config.py#L48-L55))
- `min_signal_strength`: Minimum signal strength (0-1) to execute trade
- `position_check_interval`: How often to check positions (seconds)
- `signal_scan_interval`: How often to scan for signals (seconds)
- `max_open_positions`: Maximum concurrent positions
- `enable_short`: Allow short positions
- `enable_long`: Allow long positions

## How It Works

### Signal Generation

The bot uses a multi-timeframe approach:

1. **Fetch Data**: Retrieve candlestick data for all timeframes
2. **Calculate Indicators**: Add EMA, MACD, RSI to each timeframe
3. **Analyze Each Timeframe**:
   - Trend detection using EMA alignment
   - MACD crossover signals
   - RSI overbought/oversold conditions
4. **Combine Signals**: Weight timeframes (40% long-term, 30% medium, 30% short)
5. **Generate Action**: Long, Short, or Flat based on combined analysis

### Position Management

For each open position, the bot:

1. **Monitors P&L**: Calculate real-time profit/loss
2. **Checks TP/SL**: Automatically close if targets hit
3. **Updates Trailing Stop**: Adjust stop loss as profit increases
4. **Detects Reversals**: Close if strong counter-signal appears

### Order Execution

When executing a trade:

1. **Calculate Position Size**: Based on balance, leverage, and signal strength
2. **Execute Market Order**: Open position at current market price
3. **Place TP Order**: Automatic take profit at calculated level
4. **Place SL Order**: Automatic stop loss at calculated level
5. **Track Position**: Monitor until closed

## API Endpoints Used

The bot interacts with CoinDCX Futures API:

- **Market Data**: Candlestick data, ticker prices
- **Wallet**: Balance checking, margin details
- **Positions**: List, monitor, close positions
- **Orders**: Create, cancel, edit orders
- **TP/SL**: Create take-profit and stop-loss orders

## Safety Features

- **Balance Health Monitoring**: Prevents over-leveraging
- **Configuration Validation**: Checks settings before starting
- **Position Limits**: Maximum concurrent positions
- **Signal Strength Threshold**: Only trade high-confidence signals
- **Comprehensive Logging**: All actions logged to file
- **Error Handling**: Graceful error recovery
- **Manual Override**: Stop bot anytime with Ctrl+C

## Logging

Logs are written to `trading_bot.log` with rotation (max 10MB, 5 backups).

Log levels:
- **INFO**: Trading actions, signals, position changes
- **WARNING**: Risk alerts, insufficient balance
- **ERROR**: API errors, execution failures
- **DEBUG**: Detailed technical information

## Important Warnings

⚠️ **HIGH RISK**: Futures trading involves significant risk of loss. This bot trades with real money.

⚠️ **LEVERAGE DANGER**: High leverage magnifies both gains and losses. Start with low leverage.

⚠️ **TEST FIRST**: Thoroughly test with small amounts before using larger capital.

⚠️ **MONITOR CLOSELY**: Especially during initial operation, monitor the bot closely.

⚠️ **NO GUARANTEES**: Past performance doesn't guarantee future results. Market conditions change.

⚠️ **API SECURITY**: Keep your API keys secure. Use IP whitelisting if available.

## Troubleshooting

### Bot won't start
- Check API credentials in [config.py](config.py)
- Ensure CoinDCX Futures API is enabled on your account
- Verify internet connection

### No trades executing
- Check `min_signal_strength` - may be too high
- Verify `enable_long` and `enable_short` settings
- Check if `max_open_positions` already reached
- Review logs for signal strength values

### Insufficient balance errors
- Ensure you have USDT in your Futures wallet
- Check `max_position_size_percent` setting
- Verify wallet balance via CoinDCX interface

### API errors
- Check API key permissions (Futures trading must be enabled)
- Verify API rate limits not exceeded
- Check CoinDCX API status

## Customization

### Adding More Trading Pairs

Edit [config.py:12-18](config.py#L12-L18):
```python
TRADING_PAIRS = {
    "BTC": "BTCUSDT",
    "DOGE": "DOGEUSDT",  # Add new pair
    # ... more pairs
}
```

### Adjusting Indicator Parameters

Edit [config.py:27-37](config.py#L27-L37):
```python
INDICATORS = {
    "EMA": [9, 15, 20, 50, 200],  # Modify periods
    "MACD": {
        "fast": 12,
        "slow": 26,
        "signal": 9
    },
    "RSI": {
        "period": 14,
        "overbought": 70,
        "oversold": 30
    }
}
```

### Changing Risk/Reward Ratio

Edit [config.py:39-46](config.py#L39-L46):
```python
RISK_MANAGEMENT = {
    "stop_loss_percent": 1.5,    # 1.5% risk
    "take_profit_percent": 3.0,  # 3.0% reward (2:1 ratio)
}
```

## Performance Optimization

- Adjust `signal_scan_interval` based on timeframes (default: 60 seconds)
- Use `position_check_interval` for more frequent monitoring (default: 10 seconds)
- Enable/disable trailing stops based on market volatility
- Modify signal strength threshold based on backtesting results

## License

This software is provided as-is for educational purposes. Use at your own risk.

## Disclaimer

This trading bot is an educational tool. The authors are not responsible for any financial losses incurred through its use. Always do your own research and never invest more than you can afford to lose.

## Support

For issues related to:
- **CoinDCX API**: Contact CoinDCX support
- **Bot functionality**: Review logs in `trading_bot.log`
- **Configuration**: Check this README and [config.py](config.py) comments

## Version

Version: 1.0.0
Last Updated: 2025
Platform: CoinDCX Futures

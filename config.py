# Configuration file for CoinDCX Futures Trading Bot

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_KEY = os.getenv("API_KEY", "your_api_key_here")
API_SECRET = os.getenv("API_SECRET", "your_api_secret_here")

# Base URL
BASE_URL = "https://api.coindcx.com"

# Trading Pairs - Top 5 Coins
TRADING_PAIRS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "XRP": "XRPUSDT",
    "BNB": "BNBUSDT",
    "SOL": "SOLUSDT"
}

# Timeframes
TIMEFRAMES = {
    "short_term": "5m",   # 5 minutes for short-term signals
    "medium_term": "1h",  # 1 hour for trend confirmation
    "long_term": "4h"     # 4 hours for long-term trend
}

# Technical Indicator Settings
INDICATORS = {
    "EMA": [9, 15, 20, 50, 200],
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

# Risk Management
RISK_MANAGEMENT = {
    "max_position_size_percent": 10,  # Max 10% of balance per trade
    "leverage": 5,                     # Default leverage
    "stop_loss_percent": 2.0,          # 2% stop loss
    "take_profit_percent": 4.0,        # 4% take profit (2:1 risk-reward)
    "trailing_stop": True,             # Enable trailing stop
    "trailing_stop_percent": 1.5       # Trailing stop distance
}

# Trading Parameters
TRADING_PARAMS = {
    "min_signal_strength": 0.7,        # Minimum signal strength (0-1)
    "position_check_interval": 10,     # Check positions every 10 seconds
    "signal_scan_interval": 60,        # Scan for signals every 60 seconds
    "max_open_positions": 3,           # Maximum concurrent positions
    "enable_short": True,              # Enable short positions
    "enable_long": True,               # Enable long positions
    "dry_run": True                    # Dry-run mode: analyze only, no actual trading
}

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "trading_bot.log"

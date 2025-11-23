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
    "SOL": "SOLUSDT",
    "ZEC": "ZECUSDT",
    "TAO": "TAOUSDT"
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
    },
    "ATR": {
        "period": 14,
        "multiplier": 1.5  # Stop loss = ATR * multiplier
    }
}

# Risk Management
RISK_MANAGEMENT = {
    "max_position_size_percent": 10,  # Max 10% of balance per trade
    "leverage": 5,                     # Default leverage
    "stop_loss_percent": 2.0,          # 2% stop loss (fallback if ATR not available)
    "take_profit_percent": 4.0,        # 4% take profit (2:1 risk-reward)
    "trailing_stop": True,             # Enable trailing stop
    "trailing_stop_percent": 1.5,      # Trailing stop distance
    "use_atr_stop_loss": True,         # Use ATR-based stop loss instead of fixed %
    "atr_stop_loss_multiplier": 1.5,   # ATR multiplier for stop loss (e.g., 1.5 ATR)
    "atr_take_profit_multiplier": 3.0  # ATR multiplier for take profit (e.g., 3.0 ATR for 2:1 R:R)
}

# Trading Parameters
TRADING_PARAMS = {
    "min_signal_strength": 0.7,        # Minimum signal strength (0-1)
    "position_check_interval": 10,     # Check positions every 10 seconds
    "signal_scan_interval": 60,        # Scan for signals every 60 seconds
    "max_open_positions": 3,           # Maximum concurrent positions
    "enable_short": True,              # Enable short positions
    "enable_long": True,               # Enable long positions
    "dry_run": True,                   # Dry-run mode: analyze only, no actual trading
    "simulated_balance": 1000.0        # Starting balance for dry-run mode (USDT)
}

# Strategy System Configuration
STRATEGY_CONFIG = {
    "enabled": True,                   # Enable pluggable strategy system (False = legacy mode)
    "active_strategy": "combined",     # Active strategy ID: ema_crossover, macd, rsi, combined

    # Strategy-specific parameters (overrides)
    "strategy_params": {
        "ema_crossover": {
            "fast_ema": 9,
            "slow_ema": 21,
            "min_strength": 0.6,
            "use_multi_timeframe": True
        },
        "macd": {
            "histogram_threshold": 0.0,
            "min_strength": 0.65,
            "use_histogram": True,
            "confirm_with_trend": True
        },
        "rsi": {
            "oversold_level": 30,
            "overbought_level": 70,
            "extreme_oversold": 20,
            "extreme_overbought": 80,
            "min_strength": 0.6,
            "use_divergence": False
        },
        "combined": {
            "min_signal_strength": 0.7,
            "timeframes": ['5m', '1h', '4h'],
            "weights": {
                '4h': 3.0,
                '1h': 2.0,
                '5m': 1.0
            }
        }
    }
}

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "trading_bot.log"

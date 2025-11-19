"""
Cryptocurrency Futures Trading Bot - Main Entry Point
Multi-timeframe algorithmic trading bot for CoinDCX Futures

Features:
- Multi-coin trading (BTC, ETH, XRP, BNB, SOL)
- Multi-timeframe analysis (5m, 1h, 4h)
- Technical indicators: EMA (9,15,20,50,200), MACD, RSI
- Automated TP/SL management
- Position monitoring and management
- Futures wallet balance tracking
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

import config
from trading_bot import TradingBot


def setup_logging():
    """Configure logging with file and console handlers"""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def validate_config():
    """Validate configuration settings"""
    errors = []

    # Check API credentials
    if config.API_KEY == "your_api_key_here":
        errors.append("API_KEY not configured")

    if config.API_SECRET == "your_api_secret_here":
        errors.append("API_SECRET not configured")

    # Check trading pairs
    if not config.TRADING_PAIRS:
        errors.append("No trading pairs configured")

    # Check timeframes
    if not config.TIMEFRAMES:
        errors.append("No timeframes configured")

    # Check risk management
    if config.RISK_MANAGEMENT['leverage'] < 1:
        errors.append("Invalid leverage setting")

    if config.RISK_MANAGEMENT['stop_loss_percent'] <= 0:
        errors.append("Invalid stop loss percentage")

    if config.RISK_MANAGEMENT['take_profit_percent'] <= 0:
        errors.append("Invalid take profit percentage")

    return errors


def create_bot_config():
    """Create bot configuration dict from config module"""
    return {
        'api_key': config.API_KEY,
        'api_secret': config.API_SECRET,
        'base_url': config.BASE_URL,
        'trading_pairs': config.TRADING_PAIRS,
        'timeframes': config.TIMEFRAMES,
        'indicators': config.INDICATORS,
        'risk_management': config.RISK_MANAGEMENT,
        'trading_params': config.TRADING_PARAMS
    }


def display_welcome():
    """Display welcome banner"""
    banner = """
    TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW
    Q                                                                  Q
    Q        CRYPTOCURRENCY FUTURES TRADING BOT                       Q
    Q        CoinDCX Platform                                         Q
    Q                                                                  Q
    Q        Multi-Timeframe Algorithmic Trading System               Q
    Q                                                                  Q
    ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]

    Trading Pairs: BTC, ETH, XRP, BNB, SOL
    Timeframes: 5m (short-term), 1h (medium-term), 4h (long-term)
    Indicators: EMA (9,15,20,50,200), MACD, RSI

       WARNING: This bot trades real money in futures markets.
       Ensure you understand the risks and have tested thoroughly.
       Start with small amounts and monitor carefully.

    """
    print(banner)


def main():
    """Main entry point"""
    try:
        # Display welcome
        display_welcome()

        # Setup logging
        logger = setup_logging()
        logger.info("Starting Cryptocurrency Futures Trading Bot")

        # Validate configuration
        config_errors = validate_config()
        if config_errors:
            logger.error("Configuration validation failed:")
            for error in config_errors:
                logger.error(f"  - {error}")
            logger.error("\nPlease update config.py with your API credentials and settings")
            sys.exit(1)

        logger.info("Configuration validated successfully")

        # Create bot configuration
        bot_config = create_bot_config()

        # Initialize trading bot
        logger.info("Initializing trading bot...")
        bot = TradingBot(bot_config)

        # Display configuration summary
        logger.info("\n" + "=" * 60)
        logger.info("CONFIGURATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Trading Pairs: {list(config.TRADING_PAIRS.keys())}")
        logger.info(f"Timeframes: {list(config.TIMEFRAMES.values())}")
        logger.info(f"Leverage: {config.RISK_MANAGEMENT['leverage']}x")
        logger.info(f"Stop Loss: {config.RISK_MANAGEMENT['stop_loss_percent']}%")
        logger.info(f"Take Profit: {config.RISK_MANAGEMENT['take_profit_percent']}%")
        logger.info(f"Max Position Size: {config.RISK_MANAGEMENT['max_position_size_percent']}%")
        logger.info(f"Max Open Positions: {config.TRADING_PARAMS['max_open_positions']}")
        logger.info(f"Signal Strength Threshold: {config.TRADING_PARAMS['min_signal_strength']}")
        logger.info("=" * 60 + "\n")

        # Confirm to start
        print("\nPress ENTER to start trading, or Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            logger.info("Startup cancelled by user")
            sys.exit(0)

        # Start the bot
        bot.start()

    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

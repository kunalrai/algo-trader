"""
Run Trading Bot
Main entry point to start the trading bot
"""

import logging
import os
from flask import Flask
import config
from models import db
from trading_bot import TradingBot


def create_app():
    """Create Flask app for database context"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'standalone-bot-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///algo_trader.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    # Create Flask app for database context
    app = create_app()

    with app.app_context():
        # Prepare bot configuration
        bot_config = {
            'api_key': config.API_KEY,
            'api_secret': config.API_SECRET,
            'base_url': config.BASE_URL,
            'trading_pairs': config.TRADING_PAIRS,
            'timeframes': config.TIMEFRAMES,
            'indicators': config.INDICATORS,
            'risk_management': config.RISK_MANAGEMENT,
            'trading_params': config.TRADING_PARAMS
        }

        # Display configuration
        logger.info("=" * 60)
        logger.info("TRADING BOT CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY-RUN (Safe Testing)' if config.TRADING_PARAMS['dry_run'] else 'LIVE TRADING'}")
        logger.info(f"Trading Pairs: {list(config.TRADING_PAIRS.keys())}")
        logger.info(f"Max Positions: {config.TRADING_PARAMS['max_open_positions']}")
        logger.info(f"Leverage: {config.RISK_MANAGEMENT['leverage']}x")
        logger.info(f"Signal Scan Interval: {config.TRADING_PARAMS['signal_scan_interval']}s")
        logger.info(f"Min Signal Strength: {config.TRADING_PARAMS['min_signal_strength']}")
        logger.info("=" * 60)

        if not config.TRADING_PARAMS['dry_run']:
            logger.warning("⚠️  WARNING: LIVE TRADING MODE ENABLED!")
            logger.warning("⚠️  Real trades will be executed on the exchange!")
            response = input("Type 'YES' to continue with live trading: ")
            if response != 'YES':
                logger.info("Exiting...")
                return

        # Initialize and start bot
        bot = TradingBot(bot_config)

        try:
            bot.start()
        except KeyboardInterrupt:
            logger.info("\nShutdown requested by user")
            bot.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            bot.stop()


if __name__ == "__main__":
    main()

"""
Dashboard Runner
This file is called by start_trading.py to launch the Flask dashboard
DO NOT run this file directly - use start_trading.py instead
"""

import logging
from app import app, logger
import config
from strategies.strategy_manager import get_strategy_manager

if __name__ == '__main__':
    logger.info("Starting Trading Bot Dashboard...")
    logger.info(f"Trading Mode: {'DRY RUN' if config.TRADING_PARAMS['dry_run'] else 'LIVE'}")

    # Initialize strategy system if enabled
    if config.STRATEGY_CONFIG.get('enabled', False):
        logger.info("Strategy system enabled")
        strategy_manager = get_strategy_manager()
        active_strategy_id = config.STRATEGY_CONFIG.get('active_strategy', 'combined')
        params = config.STRATEGY_CONFIG.get('strategy_params', {}).get(active_strategy_id)
        strategy_manager.set_active_strategy(active_strategy_id, params)
        logger.info(f"Active strategy: {active_strategy_id}")

    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

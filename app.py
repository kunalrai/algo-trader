"""
Flask Dashboard for Trading Bot
Real-time monitoring and control interface
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import logging
from typing import Dict, List
import config
from coindcx_client import CoinDCXFuturesClient
from data_fetcher import DataFetcher
from position_manager import PositionManager
from wallet_manager import WalletManager
from signal_generator import SignalGenerator
from indicators import TechnicalIndicators
from market_depth import MarketDepthAnalyzer
from simulated_wallet import SimulatedWallet
from bot_status import get_bot_status_tracker
from activity_log import get_activity_log
from strategies.strategy_manager import get_strategy_manager
import json
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot components
client = CoinDCXFuturesClient(
    api_key=config.API_KEY,
    api_secret=config.API_SECRET,
    base_url=config.BASE_URL
)

data_fetcher = DataFetcher(client)
position_manager = PositionManager(client, config.RISK_MANAGEMENT)
wallet_manager = WalletManager(client)
signal_generator = SignalGenerator(
    data_fetcher,
    config.INDICATORS,
    config.INDICATORS['RSI']
)
market_depth_analyzer = MarketDepthAnalyzer(client)

# Initialize simulated wallet if in dry-run mode
simulated_wallet = None
if config.TRADING_PARAMS.get('dry_run', False):
    simulated_wallet = SimulatedWallet(
        initial_balance=config.TRADING_PARAMS.get('simulated_balance', 1000.0)
    )
    logger.info(f"Dashboard: Loaded simulated wallet with balance ${simulated_wallet.get_balance():.2f}")


@app.route('/')
def index():
    """Render main dashboard - Overview page"""
    return render_template('overview.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/strategies')
def strategies():
    """Render strategies page"""
    return render_template('strategies.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/positions')
def positions():
    """Render positions page"""
    return render_template('positions.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/performance')
def performance():
    """Render performance page"""
    return render_template('performance.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/market')
def market():
    """Render market analysis page"""
    return render_template('market.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/activity')
def activity():
    """Render activity feed page"""
    return render_template('activity.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/dashboard')
def dashboard_legacy():
    """Legacy dashboard route - redirects to overview"""
    return render_template('dashboard.html', trading_pairs=config.TRADING_PAIRS)


@app.route('/api/status')
def get_status():
    """Get bot status and overview"""
    try:
        # Use simulated wallet if in dry-run mode
        if config.TRADING_PARAMS.get('dry_run') and simulated_wallet:
            wallet_info = simulated_wallet.get_balance_summary()
            positions = simulated_wallet.get_all_positions()

            status = {
                'timestamp': datetime.now().isoformat(),
                'trading_mode': 'DRY RUN',
                'wallet': {
                    'total_balance': wallet_info['total_balance'],
                    'available_balance': wallet_info['available_balance'],
                    'locked_balance': wallet_info['used_margin'],
                    'currency': 'USDT',
                    'initial_balance': wallet_info['initial_balance'],
                    'total_pnl': wallet_info['total_pnl'],
                    'pnl_percent': wallet_info['pnl_percent']
                },
                'positions': {
                    'total': len(positions),
                    'long': sum(1 for p in positions if p['side'] == 'long'),
                    'short': sum(1 for p in positions if p['side'] == 'short')
                },
                'config': {
                    'max_positions': config.TRADING_PARAMS['max_open_positions'],
                    'leverage': config.RISK_MANAGEMENT['leverage'],
                    'stop_loss': f"{config.RISK_MANAGEMENT['stop_loss_percent']}%",
                    'take_profit': f"{config.RISK_MANAGEMENT['take_profit_percent']}%"
                }
            }
        else:
            # Get wallet balance from real exchange
            wallet_info = wallet_manager.get_balance_summary()

            # Get positions
            positions = position_manager.get_all_positions()
            position_summary = position_manager.get_position_summary()

            status = {
                'timestamp': datetime.now().isoformat(),
                'trading_mode': 'LIVE',
                'wallet': {
                    'total_balance': wallet_info.get('total_balance', 0),
                    'available_balance': wallet_info.get('available_balance', 0),
                    'locked_balance': wallet_info.get('used_margin', 0),
                    'currency': 'USDT'
                },
                'positions': {
                    'total': position_summary['total_positions'],
                    'long': position_summary['long_positions'],
                    'short': position_summary['short_positions']
                },
                'config': {
                    'max_positions': config.TRADING_PARAMS['max_open_positions'],
                    'leverage': config.RISK_MANAGEMENT['leverage'],
                    'stop_loss': f"{config.RISK_MANAGEMENT['stop_loss_percent']}%",
                    'take_profit': f"{config.RISK_MANAGEMENT['take_profit_percent']}%"
                }
            }

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions')
def get_positions():
    """Get all active positions with current P&L"""
    try:
        # Use simulated wallet if in dry-run mode
        if config.TRADING_PARAMS.get('dry_run') and simulated_wallet:
            positions = simulated_wallet.get_all_positions()

            positions_data = []
            for pos in positions:
                # Get current price
                current_price = data_fetcher.get_latest_price(pos['pair'])

                # Update position price in simulated wallet
                if current_price > 0:
                    simulated_wallet.update_position_price(pos['position_id'], current_price)
                    # Get updated position
                    pos = simulated_wallet.get_position(pos['position_id'])

                positions_data.append({
                    'id': pos['position_id'],
                    'pair': pos['pair'],
                    'side': pos['side'],
                    'size': pos['size'],
                    'entry_price': pos['entry_price'],
                    'current_price': pos.get('current_price', current_price),
                    'leverage': pos['leverage'],
                    'pnl': round(pos['pnl'], 2),
                    'pnl_percent': round(pos['pnl_percent'], 2),
                    'liquidation_price': 0,  # Not calculated in simulated mode
                    'margin': pos['margin'],
                    'take_profit': pos['take_profit'],
                    'stop_loss': pos['stop_loss'],
                    'updated_at': pos.get('opened_at', '')
                })

            return jsonify(positions_data)
        else:
            # Get real positions from exchange
            positions = position_manager.get_all_positions()

            positions_data = []
            for pos in positions:
                pair = pos.get('pair', '')

                # Get current price
                # Convert B-BTC_USDT to BTCUSDT format
                if pair.startswith('B-') and '_USDT' in pair:
                    symbol = pair.replace('B-', '').replace('_USDT', 'USDT')
                    current_price = data_fetcher.get_latest_price(symbol)
                else:
                    current_price = 0

                # Determine position side (long/short) based on active_pos sign
                active_pos = float(pos.get('active_pos', 0))
                side = 'long' if active_pos > 0 else 'short'
                size = abs(active_pos)

                avg_price = float(pos.get('avg_price', 0))

                # Calculate P&L
                if avg_price > 0 and size > 0:
                    if side == 'long':
                        pnl = (current_price - avg_price) * size
                        pnl_percent = ((current_price - avg_price) / avg_price) * 100
                    else:
                        pnl = (avg_price - current_price) * size
                        pnl_percent = ((avg_price - current_price) / avg_price) * 100
                else:
                    pnl = 0
                    pnl_percent = 0

                positions_data.append({
                    'id': pos.get('id'),
                    'pair': pair,
                    'side': side,
                    'size': size,
                    'entry_price': avg_price,
                    'current_price': current_price,
                    'leverage': pos.get('leverage', 0),
                    'pnl': round(pnl, 2),
                    'pnl_percent': round(pnl_percent, 2),
                    'liquidation_price': pos.get('liquidation_price', 0),
                    'margin': pos.get('locked_margin', 0),
                    'updated_at': pos.get('updated_at')
                })

            return jsonify(positions_data)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prices')
def get_prices():
    """Get current prices for all trading pairs"""
    try:
        prices = []

        for name, symbol in config.TRADING_PAIRS.items():
            price = data_fetcher.get_latest_price(symbol)
            prices.append({
                'name': name,
                'symbol': symbol,
                'price': price
            })

        return jsonify(prices)
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/market/<symbol>')
def get_market_data(symbol):
    """Get detailed market data for a specific symbol"""
    try:
        # Get candlestick data for multiple timeframes
        timeframes_data = {}

        for tf_name, interval in config.TIMEFRAMES.items():
            df = data_fetcher.fetch_candles(symbol, interval, limit=100)

            if not df.empty:
                # Get latest candle
                latest = df.iloc[-1]
                timeframes_data[tf_name] = {
                    'interval': interval,
                    'open': float(latest['open']),
                    'high': float(latest['high']),
                    'low': float(latest['low']),
                    'close': float(latest['close']),
                    'volume': float(latest['volume']),
                    'timestamp': latest['timestamp'].isoformat()
                }

        return jsonify(timeframes_data)
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/close-position', methods=['POST'])
def close_position():
    """Close a specific position"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')

        if not position_id:
            return jsonify({'error': 'position_id required'}), 400

        # Check if dry run mode
        if config.TRADING_PARAMS['dry_run'] and simulated_wallet:
            # Get position from simulated wallet
            position = simulated_wallet.get_position(position_id)

            if not position:
                return jsonify({'error': 'Position not found'}), 404

            # Get current price to close at
            current_price = data_fetcher.get_latest_price(position['pair'])

            if current_price == 0:
                return jsonify({'error': 'Could not get current price'}), 500

            # Close position in simulated wallet
            result = simulated_wallet.close_position(
                position_id,
                current_price,
                "Manual close via dashboard"
            )

            if result:
                logger.info(f"DRY RUN: Closed position {position_id} at ${current_price:.2f}")
                return jsonify({
                    'success': True,
                    'message': f"Position closed (simulated) - P&L: ${result['final_pnl']:.2f}",
                    'position_id': position_id,
                    'pnl': result['final_pnl']
                })
            else:
                return jsonify({'error': 'Failed to close position'}), 500

        # Actually close position (live mode)
        success = position_manager.close_position(position_id, reason="Manual close via dashboard")

        if success:
            return jsonify({
                'success': True,
                'message': 'Position closed successfully',
                'position_id': position_id
            })
        else:
            return jsonify({'error': 'Failed to close position'}), 500

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update bot configuration"""
    if request.method == 'GET':
        return jsonify({
            'trading_pairs': config.TRADING_PAIRS,
            'timeframes': config.TIMEFRAMES,
            'indicators': config.INDICATORS,
            'risk_management': config.RISK_MANAGEMENT,
            'trading_params': config.TRADING_PARAMS
        })
    elif request.method == 'POST':
        # Update configuration (be careful with this in production)
        try:
            new_config = request.get_json()
            logger.info(f"Configuration update requested: {new_config}")

            # In a real app, you'd validate and update the config here
            return jsonify({'success': True, 'message': 'Config update not implemented for safety'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/trading/toggle', methods=['POST'])
def toggle_trading():
    """Toggle trading mode (dry-run / live)"""
    try:
        data = request.get_json()
        mode = data.get('mode')  # 'dry_run' or 'live'

        if mode == 'dry_run':
            config.TRADING_PARAMS['dry_run'] = True
            message = 'Switched to DRY RUN mode'
        elif mode == 'live':
            config.TRADING_PARAMS['dry_run'] = False
            message = 'Switched to LIVE trading mode'
        else:
            return jsonify({'error': 'Invalid mode'}), 400

        logger.warning(f"Trading mode changed: {message}")
        return jsonify({'success': True, 'message': message, 'dry_run': config.TRADING_PARAMS['dry_run']})
    except Exception as e:
        logger.error(f"Error toggling trading mode: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/signals')
def get_signals():
    """Get trading signals for all configured pairs"""
    try:
        signals = []

        for name, symbol in config.TRADING_PAIRS.items():
            # Generate signal for each pair
            signal = signal_generator.generate_signal(symbol, config.TIMEFRAMES)

            if signal:
                signals.append({
                    'name': name,
                    'symbol': symbol,
                    'action': signal['action'],
                    'strength': round(signal['strength'], 2),
                    'bullish_score': round(signal['bullish_score'], 2),
                    'bearish_score': round(signal['bearish_score'], 2),
                    'current_price': signal['current_price'],
                    'analyses': {
                        tf: {
                            'trend': analysis['trend'],
                            'macd_signal': analysis['macd_signal'],
                            'rsi_signal': analysis['rsi_signal'],
                            'rsi_value': round(analysis.get('rsi_value', 0), 2),
                            'strength': round(analysis['strength'], 2)
                        }
                        for tf, analysis in signal['analyses'].items()
                    }
                })

        return jsonify(signals)
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/indicators/<symbol>')
def get_indicators(symbol):
    """Get detailed technical indicators for a specific symbol"""
    try:
        # Fetch candle data
        df = data_fetcher.fetch_candles(symbol, '5m', limit=200)

        if df.empty:
            return jsonify({'error': 'No data available'}), 404

        # Add all indicators
        df = TechnicalIndicators.add_all_indicators(
            df,
            config.INDICATORS['EMA'],
            config.INDICATORS['MACD'],
            config.INDICATORS['RSI']['period']
        )

        # Get latest values
        latest = df.iloc[-1]

        indicators = {
            'symbol': symbol,
            'current_price': float(latest['close']),
            'ema': {
                f'ema_{period}': round(float(latest[f'EMA_{period}']), 2)
                for period in config.INDICATORS['EMA']
                if f'EMA_{period}' in latest
            },
            'macd': {
                'macd': round(float(latest['MACD']), 4),
                'signal': round(float(latest['MACD_signal']), 4),
                'histogram': round(float(latest['MACD_hist']), 4)
            },
            'rsi': {
                'value': round(float(latest['RSI']), 2),
                'overbought': config.INDICATORS['RSI']['overbought'],
                'oversold': config.INDICATORS['RSI']['oversold']
            },
            'trend': TechnicalIndicators.get_trend_direction(df),
            'macd_signal': TechnicalIndicators.get_macd_signal(df),
            'rsi_signal': TechnicalIndicators.get_rsi_signal(
                df,
                config.INDICATORS['RSI']['overbought'],
                config.INDICATORS['RSI']['oversold']
            )
        }

        return jsonify(indicators)
    except Exception as e:
        logger.error(f"Error getting indicators for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/liquidity')
def get_liquidity_all():
    """Get liquidity metrics for all trading pairs"""
    try:
        liquidity_data = []

        for name, symbol in config.TRADING_PAIRS.items():
            # Convert to CoinDCX format
            coindcx_pair = data_fetcher.convert_to_coindcx_symbol(symbol)

            # Get order book analysis
            analysis = market_depth_analyzer.analyze_orderbook(coindcx_pair, depth=20)

            # Get volume analysis
            volume_data = market_depth_analyzer.get_volume_analysis(coindcx_pair)

            liquidity_data.append({
                'name': name,
                'symbol': symbol,
                **analysis,
                **volume_data
            })

        return jsonify(liquidity_data)
    except Exception as e:
        logger.error(f"Error getting liquidity data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/liquidity/<symbol>')
def get_liquidity(symbol):
    """Get detailed liquidity metrics for a specific symbol"""
    try:
        # Convert to CoinDCX format
        coindcx_pair = data_fetcher.convert_to_coindcx_symbol(symbol)

        # Get full order book analysis
        analysis = market_depth_analyzer.analyze_orderbook(coindcx_pair, depth=50)

        # Get volume analysis
        volume_data = market_depth_analyzer.get_volume_analysis(coindcx_pair)

        return jsonify({
            'symbol': symbol,
            **analysis,
            **volume_data
        })
    except Exception as e:
        logger.error(f"Error getting liquidity for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulated/stats')
def get_simulated_stats():
    """Get simulated wallet statistics (dry-run mode only)"""
    try:
        if not config.TRADING_PARAMS.get('dry_run') or not simulated_wallet:
            return jsonify({'error': 'Not in dry-run mode'}), 400

        stats = simulated_wallet.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting simulated stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulated/trades')
def get_simulated_trades():
    """Get simulated trade history (dry-run mode only)"""
    try:
        if not config.TRADING_PARAMS.get('dry_run') or not simulated_wallet:
            return jsonify({'error': 'Not in dry-run mode'}), 400

        limit = int(request.args.get('limit', 20))
        trades = simulated_wallet.get_trade_history(limit=limit)

        return jsonify(trades)
    except Exception as e:
        logger.error(f"Error getting simulated trades: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulated/reset', methods=['POST'])
def reset_simulated_wallet():
    """Reset simulated wallet to initial balance (dry-run mode only)"""
    try:
        if not config.TRADING_PARAMS.get('dry_run') or not simulated_wallet:
            return jsonify({'error': 'Not in dry-run mode'}), 400

        # Get initial balance from config or request
        initial_balance = config.TRADING_PARAMS.get('simulated_balance', 1000.0)

        # Reset the wallet
        simulated_wallet.reset(initial_balance)

        logger.info(f"Simulated wallet reset to ${initial_balance:.2f}")

        return jsonify({
            'success': True,
            'message': f'Wallet reset to ${initial_balance:.2f}',
            'initial_balance': initial_balance
        })
    except Exception as e:
        logger.error(f"Error resetting simulated wallet: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/status')
def get_bot_status():
    """Get bot runtime status and current activity"""
    try:
        status_tracker = get_bot_status_tracker()
        status = status_tracker.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/activity')
def get_bot_activity():
    """Get recent bot activity feed"""
    try:
        activity_log = get_activity_log()
        limit = int(request.args.get('limit', 50))
        filter_type = request.args.get('type', None)

        activities = activity_log.get_recent_activities(limit=limit, filter_type=filter_type)
        return jsonify(activities)
    except Exception as e:
        logger.error(f"Error getting bot activity: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wallet/history')
def get_wallet_history():
    """Get wallet balance history over time (for chart)"""
    try:
        if not config.TRADING_PARAMS.get('dry_run') or not simulated_wallet:
            return jsonify({'error': 'Not in dry-run mode'}), 400

        # Get trade history
        trades = simulated_wallet.get_trade_history(limit=100)

        # Calculate balance at each trade
        initial_balance = config.TRADING_PARAMS.get('simulated_balance', 1000.0)
        balance_history = []

        # Add starting point
        if trades:
            balance_history.append({
                'timestamp': trades[0]['opened_at'] if trades else 0,
                'balance': initial_balance,
                'pnl': 0
            })

        running_balance = initial_balance
        for trade in trades:
            running_balance += trade['pnl']
            balance_history.append({
                'timestamp': trade['closed_at'],
                'balance': running_balance,
                'pnl': trade['pnl']
            })

        return jsonify(balance_history)
    except Exception as e:
        logger.error(f"Error getting wallet history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart/<symbol>')
def get_chart_data(symbol):
    """Get chart data with S/R levels for a specific symbol"""
    try:
        # Get timeframe from query parameter (default: 5m)
        interval = request.args.get('interval', '5')
        limit = int(request.args.get('limit', '100'))

        # Fetch candlestick data
        df = data_fetcher.fetch_candles(symbol, interval, limit=limit)

        if df.empty:
            return jsonify({'error': 'No data available'}), 404

        # Add indicators for S/R calculation
        df = TechnicalIndicators.add_all_indicators(
            df,
            config.INDICATORS['EMA'],
            config.INDICATORS['MACD'],
            config.INDICATORS['RSI']['period']
        )

        # Calculate support/resistance levels
        # Determine timeframe type based on interval
        if interval in ['5', '15', '30']:
            timeframe_type = 'short'
        else:
            timeframe_type = 'long'

        sr_levels = TechnicalIndicators.get_support_resistance_levels(df, timeframe_type)

        # Prepare candlestick data
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                'time': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        # Get latest price and 24h stats
        latest = df.iloc[-1]
        first = df.iloc[0]
        change_24h = ((float(latest['close']) - float(first['open'])) / float(first['open'])) * 100

        chart_data = {
            'symbol': symbol,
            'interval': interval,
            'candles': candles,
            'support_resistance': sr_levels,
            'current_price': float(latest['close']),
            'high_24h': float(df['high'].max()),
            'low_24h': float(df['low'].min()),
            'change_24h': round(change_24h, 2),
            'volume_24h': float(df['volume'].sum())
        }

        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error getting chart data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STRATEGY MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/strategies/list')
def list_strategies():
    """Get list of all available strategies"""
    try:
        strategy_manager = get_strategy_manager()
        strategies = strategy_manager.list_strategies()
        return jsonify({
            'success': True,
            'strategies': strategies,
            'strategy_system_enabled': config.STRATEGY_CONFIG.get('enabled', False)
        })
    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/active')
def get_active_strategy():
    """Get currently active strategy information"""
    try:
        strategy_manager = get_strategy_manager()
        active_info = strategy_manager.get_active_strategy_info()

        return jsonify({
            'success': True,
            'active_strategy': active_info,
            'strategy_system_enabled': config.STRATEGY_CONFIG.get('enabled', False),
            'configured_strategy': config.STRATEGY_CONFIG.get('active_strategy', 'combined')
        })
    except Exception as e:
        logger.error(f"Error getting active strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/set', methods=['POST'])
def set_active_strategy():
    """Set the active trading strategy"""
    try:
        data = request.get_json()
        strategy_id = data.get('strategy_id')

        if not strategy_id:
            return jsonify({'success': False, 'error': 'strategy_id required'}), 400

        strategy_manager = get_strategy_manager()

        # Get custom params if provided, otherwise use config
        params = data.get('params')
        if not params and strategy_id in config.STRATEGY_CONFIG.get('strategy_params', {}):
            params = config.STRATEGY_CONFIG['strategy_params'][strategy_id]

        success = strategy_manager.set_active_strategy(strategy_id, params)

        if success:
            # Update config
            config.STRATEGY_CONFIG['active_strategy'] = strategy_id
            active_info = strategy_manager.get_active_strategy_info()

            return jsonify({
                'success': True,
                'message': f'Active strategy set to: {strategy_id}',
                'active_strategy': active_info
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Strategy {strategy_id} not found'
            }), 404

    except Exception as e:
        logger.error(f"Error setting active strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/toggle', methods=['POST'])
def toggle_strategy_system():
    """Toggle strategy system on/off"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', not config.STRATEGY_CONFIG.get('enabled', False))

        config.STRATEGY_CONFIG['enabled'] = enabled

        return jsonify({
            'success': True,
            'enabled': enabled,
            'message': f"Strategy system {'enabled' if enabled else 'disabled'}"
        })
    except Exception as e:
        logger.error(f"Error toggling strategy system: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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

    app.run(debug=True, host='0.0.0.0', port=5000)

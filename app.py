"""
Flask Dashboard for Trading Bot
Real-time monitoring and control interface
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
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
from strategies.custom_strategy_loader import get_custom_strategy_loader
from models import db, init_db, User, UserProfile, UserTradingPair, CustomStrategy
from auth import auth_bp, init_auth
from werkzeug.utils import secure_filename
import json
import os

# Per-user isolation imports
from user_wallet_manager import get_user_wallet_manager
from user_bot_status import get_user_bot_status_tracker
from user_activity_log import get_user_activity_log
from user_data_fetcher import get_user_data_fetcher
from user_position_manager import get_user_position_manager
from user_order_manager import get_user_order_manager
from user_signal_generator import get_user_signal_generator

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///algo_trader.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth configuration (set these in .env)
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')

# Initialize database and authentication
init_db(app)
init_auth(app)
app.register_blueprint(auth_bp)

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


# ============================================================================
# USER-SPECIFIC TRADING COMPONENTS
# ============================================================================

def get_user_trading_mode():
    """Get the trading mode for the current user"""
    if current_user.is_authenticated and current_user.profile:
        return current_user.profile.trading_mode == 'paper'
    return config.TRADING_PARAMS.get('dry_run', True)


def get_user_client():
    """Get CoinDCX client with user's API keys if in live mode"""
    if current_user.is_authenticated and current_user.profile:
        if current_user.profile.trading_mode == 'live' and current_user.profile.has_api_keys:
            return CoinDCXFuturesClient(
                api_key=current_user.profile.coindcx_api_key,
                api_secret=current_user.profile.coindcx_api_secret,
                base_url=config.BASE_URL
            )
    return client  # Default client


def get_user_simulated_wallet():
    """Get the simulated wallet for the current user (per-user isolation)"""
    if current_user.is_authenticated:
        # Return user-specific wallet manager from database
        return get_user_wallet_manager(current_user.id)
    return None


def get_user_data_fetcher_instance():
    """Get user-specific data fetcher with isolated caching"""
    if current_user.is_authenticated:
        user_client = get_user_client()
        return get_user_data_fetcher(current_user.id, user_client)
    return data_fetcher  # Fallback to global


def get_user_position_manager_instance():
    """Get user-specific position manager"""
    if current_user.is_authenticated:
        user_client = get_user_client()
        # Get user-specific risk config
        user_risk_config = dict(config.RISK_MANAGEMENT)
        if current_user.profile:
            user_risk_config.update({
                'max_position_size_percent': current_user.profile.max_position_size_percent,
                'leverage': current_user.profile.leverage,
                'stop_loss_percent': current_user.profile.stop_loss_percent,
                'take_profit_percent': current_user.profile.take_profit_percent,
            })
        return get_user_position_manager(current_user.id, user_client, user_risk_config)
    return position_manager  # Fallback to global


def get_user_order_manager_instance():
    """Get user-specific order manager"""
    if current_user.is_authenticated:
        user_client = get_user_client()
        is_paper_mode = get_user_trading_mode()
        # Get user-specific risk config
        user_risk_config = dict(config.RISK_MANAGEMENT)
        if current_user.profile:
            user_risk_config.update({
                'max_position_size_percent': current_user.profile.max_position_size_percent,
                'leverage': current_user.profile.leverage,
                'stop_loss_percent': current_user.profile.stop_loss_percent,
                'take_profit_percent': current_user.profile.take_profit_percent,
            })
        return get_user_order_manager(current_user.id, user_client, user_risk_config, is_paper_mode)
    return None


def get_user_signal_generator_instance():
    """Get user-specific signal generator with isolated data fetching"""
    if current_user.is_authenticated:
        user_fetcher = get_user_data_fetcher_instance()
        return get_user_signal_generator(
            user_id=current_user.id,
            data_fetcher=user_fetcher,
            indicator_config=config.INDICATORS,
            rsi_config=config.INDICATORS['RSI'],
            use_strategy_system=config.STRATEGY_CONFIG.get('enabled', False)
        )
    return signal_generator  # Fallback to global


def get_user_trading_pairs():
    """Get trading pairs for the current user"""
    if current_user.is_authenticated:
        # Get user's active trading pairs from database
        user_pairs = UserTradingPair.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).all()

        if user_pairs:
            # Convert to dict format: {display_name: symbol}
            return {pair.display_name: pair.symbol for pair in user_pairs}

    # Fallback to config default
    return config.TRADING_PAIRS


# ============================================================================
# PAGE ROUTES (Protected by login_required)
# ============================================================================

@app.route('/')
@login_required
def index():
    """Render main dashboard - Overview page"""
    return render_template('overview.html', trading_pairs=get_user_trading_pairs())


@app.route('/strategies')
@login_required
def strategies():
    """Render strategies page"""
    return render_template('strategies.html', trading_pairs=get_user_trading_pairs())


@app.route('/positions')
@login_required
def positions():
    """Render positions page"""
    return render_template('positions.html', trading_pairs=get_user_trading_pairs())


@app.route('/performance')
@login_required
def performance():
    """Render performance page"""
    return render_template('performance.html', trading_pairs=get_user_trading_pairs())


@app.route('/market')
@login_required
def market():
    """Render market analysis page"""
    return render_template('market.html', trading_pairs=get_user_trading_pairs())


@app.route('/activity')
@login_required
def activity():
    """Render activity feed page"""
    return render_template('activity.html', trading_pairs=get_user_trading_pairs())


@app.route('/dashboard')
@login_required
def dashboard_legacy():
    """Legacy dashboard route - redirects to overview"""
    return render_template('dashboard.html', trading_pairs=get_user_trading_pairs())


@app.route('/api/status')
@login_required
def get_status():
    """Get bot status and overview (per-user isolation)"""
    try:
        # Use user's trading mode preference
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        # Get user-specific risk settings
        user_config = {
            'max_positions': config.TRADING_PARAMS['max_open_positions'],
            'leverage': config.RISK_MANAGEMENT['leverage'],
            'stop_loss': config.RISK_MANAGEMENT['stop_loss_percent'],
            'take_profit': config.RISK_MANAGEMENT['take_profit_percent']
        }
        if current_user.profile:
            user_config['max_positions'] = current_user.profile.max_open_positions
            user_config['leverage'] = current_user.profile.leverage
            user_config['stop_loss'] = current_user.profile.stop_loss_percent
            user_config['take_profit'] = current_user.profile.take_profit_percent

        # Use simulated wallet if in paper trading mode
        if is_paper_mode and user_wallet:
            wallet_info = user_wallet.get_balance_summary()
            positions = user_wallet.get_all_positions()

            status = {
                'timestamp': datetime.now().isoformat(),
                'trading_mode': 'DRY RUN',
                'user_id': current_user.id,
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
                    'long': sum(1 for p in positions if p.get('side') == 'long'),
                    'short': sum(1 for p in positions if p.get('side') == 'short')
                },
                'config': {
                    'max_positions': user_config['max_positions'],
                    'leverage': user_config['leverage'],
                    'stop_loss': f"{user_config['stop_loss']}%",
                    'take_profit': f"{user_config['take_profit']}%"
                }
            }
        else:
            # Get wallet balance from real exchange
            wallet_info = wallet_manager.get_balance_summary()

            # Get positions (per-user position manager)
            user_position_mgr = get_user_position_manager_instance()
            positions = user_position_mgr.get_all_positions()
            position_summary = user_position_mgr.get_position_summary()

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
@login_required
def get_positions():
    """Get all active positions with current P&L (per-user isolation)"""
    try:
        # Get user's trading pairs for filtering
        user_pairs = get_user_trading_pairs()
        user_symbols = set(user_pairs.values())

        # Use user's trading mode preference
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        # Use per-user simulated wallet if in paper trading mode
        if is_paper_mode and user_wallet:
            positions = user_wallet.get_all_positions()

            positions_data = []
            for pos in positions:
                # Filter by user's trading pairs
                if pos.get('pair') not in user_symbols:
                    continue
                # Get current price (per-user data fetcher)
                user_fetcher = get_user_data_fetcher_instance()
                current_price = user_fetcher.get_latest_price(pos.get('pair'))

                # Update position price in user's simulated wallet
                if current_price > 0:
                    user_wallet.update_position_price(pos.get('position_id'), current_price)
                    # Get updated position
                    pos = user_wallet.get_position(pos.get('position_id'))
                    if not pos:
                        continue

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
            # Get real positions from exchange (per-user)
            user_position_mgr = get_user_position_manager_instance()
            positions = user_position_mgr.get_all_positions()

            positions_data = []
            for pos in positions:
                pair = pos.get('pair', '')

                # Get current price
                # Convert B-BTC_USDT to BTCUSDT format
                if pair.startswith('B-') and '_USDT' in pair:
                    symbol = pair.replace('B-', '').replace('_USDT', 'USDT')

                    # Filter by user's trading pairs
                    if symbol not in user_symbols:
                        continue

                    user_fetcher = get_user_data_fetcher_instance()
                    current_price = user_fetcher.get_latest_price(symbol)
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
@login_required
def get_prices():
    """Get current prices for all trading pairs (per-user isolation)"""
    try:
        prices = []
        user_fetcher = get_user_data_fetcher_instance()

        for name, symbol in get_user_trading_pairs().items():
            price = user_fetcher.get_latest_price(symbol)
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
@login_required
def get_market_data(symbol):
    """Get detailed market data for a specific symbol (per-user isolation)"""
    try:
        # Get candlestick data for multiple timeframes
        user_fetcher = get_user_data_fetcher_instance()
        timeframes_data = {}

        for tf_name, interval in config.TIMEFRAMES.items():
            df = user_fetcher.fetch_candles(symbol, interval, limit=100)

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
@login_required
def close_position():
    """Close a specific position (per-user isolation)"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')

        if not position_id:
            return jsonify({'error': 'position_id required'}), 400

        # Use user's trading mode preference
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        # Check if paper trading mode
        if is_paper_mode and user_wallet:
            # Get position from user's simulated wallet
            position = user_wallet.get_position(position_id)

            if not position:
                return jsonify({'error': 'Position not found'}), 404

            # Get current price to close at (per-user data fetcher)
            user_fetcher = get_user_data_fetcher_instance()
            current_price = user_fetcher.get_latest_price(position.get('pair'))

            if current_price == 0:
                return jsonify({'error': 'Could not get current price'}), 500

            # Close position in user's simulated wallet
            result = user_wallet.close_position(
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

        # Actually close position (live mode) - per-user position manager
        user_position_mgr = get_user_position_manager_instance()
        success = user_position_mgr.close_position(position_id, reason="Manual close via dashboard")

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
@login_required
def handle_config():
    """Get or update bot configuration"""
    if request.method == 'GET':
        # Get user-specific risk management settings
        user_risk_settings = {}
        if current_user.profile:
            user_risk_settings = {
                'max_position_size_percent': current_user.profile.max_position_size_percent,
                'leverage': current_user.profile.leverage,
                'stop_loss_percent': current_user.profile.stop_loss_percent,
                'take_profit_percent': current_user.profile.take_profit_percent,
                'max_open_positions': current_user.profile.max_open_positions,
            }

        # Merge with config defaults
        risk_management = {**config.RISK_MANAGEMENT, **user_risk_settings}

        return jsonify({
            'trading_pairs': get_user_trading_pairs(),
            'timeframes': config.TIMEFRAMES,
            'indicators': config.INDICATORS,
            'risk_management': risk_management,
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
@login_required
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
@login_required
def get_signals():
    """Get trading signals for all configured pairs (per-user isolation)"""
    try:
        signals = []
        user_signal_gen = get_user_signal_generator_instance()

        for name, symbol in get_user_trading_pairs().items():
            # Generate signal for each pair (per-user signal generator)
            signal = user_signal_gen.generate_signal(symbol, config.TIMEFRAMES)

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
@login_required
def get_indicators(symbol):
    """Get detailed technical indicators for a specific symbol (per-user isolation)"""
    try:
        # Fetch candle data (per-user data fetcher)
        user_fetcher = get_user_data_fetcher_instance()
        df = user_fetcher.fetch_candles(symbol, '5m', limit=200)

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
@login_required
def get_liquidity_all():
    """Get liquidity metrics for all trading pairs (per-user isolation)"""
    try:
        liquidity_data = []
        user_fetcher = get_user_data_fetcher_instance()

        for name, symbol in get_user_trading_pairs().items():
            # Convert to CoinDCX format
            coindcx_pair = user_fetcher.convert_to_coindcx_symbol(symbol)

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
@login_required
def get_liquidity(symbol):
    """Get detailed liquidity metrics for a specific symbol (per-user isolation)"""
    try:
        # Convert to CoinDCX format
        user_fetcher = get_user_data_fetcher_instance()
        coindcx_pair = user_fetcher.convert_to_coindcx_symbol(symbol)

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
@login_required
def get_simulated_stats():
    """Get simulated wallet statistics (per-user isolation)"""
    try:
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        if not is_paper_mode or not user_wallet:
            return jsonify({'error': 'Not in paper trading mode'}), 400

        stats = user_wallet.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting simulated stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulated/trades')
@login_required
def get_simulated_trades():
    """Get simulated trade history (per-user isolation)"""
    try:
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        if not is_paper_mode or not user_wallet:
            return jsonify({'error': 'Not in paper trading mode'}), 400

        limit = int(request.args.get('limit', 20))
        trades = user_wallet.get_trade_history(limit=limit)

        return jsonify(trades)
    except Exception as e:
        logger.error(f"Error getting simulated trades: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/simulated/reset', methods=['POST'])
@login_required
def reset_simulated_wallet():
    """Reset simulated wallet to initial balance (per-user isolation)"""
    try:
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        if not is_paper_mode or not user_wallet:
            return jsonify({'error': 'Not in paper trading mode'}), 400

        # Get initial balance from user profile or config
        initial_balance = config.TRADING_PARAMS.get('simulated_balance', 1000.0)
        if current_user.profile:
            initial_balance = current_user.profile.simulated_balance or initial_balance

        # Reset the user's wallet
        user_wallet.reset(initial_balance)

        logger.info(f"User {current_user.id}: Simulated wallet reset to ${initial_balance:.2f}")

        return jsonify({
            'success': True,
            'message': f'Wallet reset to ${initial_balance:.2f}',
            'initial_balance': initial_balance
        })
    except Exception as e:
        logger.error(f"Error resetting simulated wallet: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/status')
@login_required
def get_bot_status():
    """Get bot runtime status and current activity (per-user isolation)"""
    try:
        # Get per-user bot status tracker
        user_status_tracker = get_user_bot_status_tracker(current_user.id)
        status = user_status_tracker.get_status()
        status['user_id'] = current_user.id
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/start', methods=['POST'])
@login_required
def start_bot():
    """Start the trading bot for the current user"""
    try:
        user_status_tracker = get_user_bot_status_tracker(current_user.id)
        status = user_status_tracker.get_status()

        if status['bot_running']:
            return jsonify({'success': False, 'message': 'Bot is already running'}), 400

        # Get user's trading pairs
        user_pairs = get_user_trading_pairs()
        pairs_list = list(user_pairs.values()) if user_pairs else []

        if not pairs_list:
            return jsonify({'success': False, 'message': 'No trading pairs configured. Please add trading pairs in your profile.'}), 400

        # Get scan interval from config
        scan_interval = config.TRADING_PARAMS.get('signal_scan_interval', 60)

        # Start the bot (mark as running in database)
        user_status_tracker.start_bot(scan_interval=scan_interval, pairs=pairs_list)

        logger.info(f"Bot started for user {current_user.id} with pairs: {pairs_list}")

        return jsonify({
            'success': True,
            'message': 'Bot started successfully',
            'pairs': pairs_list
        })
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/stop', methods=['POST'])
@login_required
def stop_bot():
    """Stop the trading bot for the current user"""
    try:
        user_status_tracker = get_user_bot_status_tracker(current_user.id)
        status = user_status_tracker.get_status()

        if not status['bot_running']:
            return jsonify({'success': False, 'message': 'Bot is not running'}), 400

        # Stop the bot
        user_status_tracker.stop_bot()

        logger.info(f"Bot stopped for user {current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Bot stopped successfully'
        })
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/activity')
@login_required
def get_bot_activity():
    """Get recent bot activity feed (per-user isolation)"""
    try:
        # Get per-user activity log
        user_activity_log = get_user_activity_log(current_user.id)
        limit = int(request.args.get('limit', 50))
        filter_type = request.args.get('type', None)

        activities = user_activity_log.get_recent_activities(limit=limit, filter_type=filter_type)

        # Filter activities by user's trading pairs
        user_pairs = get_user_trading_pairs()
        user_symbols = set(user_pairs.values())  # Get just the symbols (BTCUSDT, ETHUSDT, etc.)

        # Filter activities to only include user's pairs
        filtered_activities = []
        for activity in activities:
            # Check if activity has a pair field
            if 'pair' in activity:
                if activity['pair'] in user_symbols:
                    filtered_activities.append(activity)
            else:
                # Include non-pair specific activities (bot status, errors, etc.)
                filtered_activities.append(activity)

        return jsonify(filtered_activities)
    except Exception as e:
        logger.error(f"Error getting bot activity: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wallet/history')
@login_required
def get_wallet_history():
    """Get wallet balance history over time (per-user isolation)"""
    try:
        is_paper_mode = get_user_trading_mode()
        user_wallet = get_user_simulated_wallet()

        if not is_paper_mode or not user_wallet:
            return jsonify({'error': 'Not in paper trading mode'}), 400

        # Get trade history for this user
        trades = user_wallet.get_trade_history(limit=100)

        # Calculate balance at each trade
        initial_balance = config.TRADING_PARAMS.get('simulated_balance', 1000.0)
        if current_user.profile:
            initial_balance = current_user.profile.simulated_balance or initial_balance

        balance_history = []

        # Add starting point
        if trades:
            balance_history.append({
                'timestamp': trades[0].get('opened_at', '') if trades else 0,
                'balance': initial_balance,
                'pnl': 0
            })

        running_balance = initial_balance
        for trade in trades:
            running_balance += trade.get('pnl', 0)
            balance_history.append({
                'timestamp': trade.get('closed_at', ''),
                'balance': running_balance,
                'pnl': trade.get('pnl', 0)
            })

        return jsonify(balance_history)
    except Exception as e:
        logger.error(f"Error getting wallet history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart/<symbol>')
@login_required
def get_chart_data(symbol):
    """Get chart data with S/R levels for a specific symbol (per-user isolation)"""
    try:
        # Get timeframe from query parameter (default: 5m)
        interval = request.args.get('interval', '5')
        limit = int(request.args.get('limit', '100'))

        # Fetch candlestick data (per-user data fetcher)
        user_fetcher = get_user_data_fetcher_instance()
        df = user_fetcher.fetch_candles(symbol, interval, limit=limit)

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
@login_required
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
@login_required
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
@login_required
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
@login_required
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


# ============================================================================
# CUSTOM STRATEGY MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/strategies/custom/list')
@login_required
def list_custom_strategies():
    """List all custom strategies for the current user"""
    try:
        # Get strategies from database for this user
        custom_strategies = CustomStrategy.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(CustomStrategy.created_at.desc()).all()

        strategies_list = []
        for strategy in custom_strategies:
            strategies_list.append({
                'id': strategy.id,
                'strategy_id': strategy.strategy_id,
                'class_name': strategy.class_name,
                'filename': strategy.filename,
                'description': strategy.description,
                'is_validated': strategy.is_validated,
                'validation_error': strategy.validation_error,
                'created_at': strategy.created_at.isoformat(),
                'updated_at': strategy.updated_at.isoformat(),
                'last_used_at': strategy.last_used_at.isoformat() if strategy.last_used_at else None,
                'file_size': strategy.file_size
            })

        return jsonify({
            'success': True,
            'strategies': strategies_list
        })
    except Exception as e:
        logger.error(f"Error listing custom strategies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/custom/upload', methods=['POST'])
@login_required
def upload_custom_strategy():
    """Upload a new custom strategy file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Check file extension
        if not file.filename.endswith('.py'):
            return jsonify({'success': False, 'error': 'Only .py files are allowed'}), 400

        # Read file content
        file_content = file.read().decode('utf-8')
        filename = secure_filename(file.filename)

        # Load the custom strategy loader
        loader = get_custom_strategy_loader()

        # Validate the strategy code
        is_valid, error_msg, metadata = loader.validate_strategy_code(file_content, filename)

        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Strategy validation failed: {error_msg}'
            }), 400

        # Save to file system
        success, message = loader.save_strategy_file(filename, file_content, current_user.id)

        if not success:
            return jsonify({'success': False, 'error': message}), 400

        # Save to database
        strategy_id = filename[:-3] if filename.endswith('.py') else filename

        # Check if strategy already exists for this user
        existing = CustomStrategy.query.filter_by(
            user_id=current_user.id,
            strategy_id=strategy_id
        ).first()

        if existing:
            # Update existing strategy
            existing.source_code = file_content
            existing.class_name = metadata['class_name']
            existing.description = metadata.get('description', '')
            existing.is_validated = True
            existing.validation_error = None
            existing.file_size = len(file_content.encode('utf-8'))
            existing.version += 1
            existing.updated_at = datetime.utcnow()
        else:
            # Create new strategy record
            custom_strategy = CustomStrategy(
                user_id=current_user.id,
                strategy_id=strategy_id,
                class_name=metadata['class_name'],
                filename=filename,
                description=metadata.get('description', ''),
                source_code=file_content,
                is_validated=True,
                file_size=len(file_content.encode('utf-8'))
            )
            db.session.add(custom_strategy)

        db.session.commit()

        # Load the strategy into the strategy manager
        success, strategy_class, error = loader.load_strategy_from_file(filename)

        if success and strategy_class:
            # Register with strategy manager
            strategy_manager = get_strategy_manager()
            strategy_manager.register_strategy(strategy_id, strategy_class)

            logger.info(f"User {current_user.id} uploaded custom strategy: {strategy_id}")

            return jsonify({
                'success': True,
                'message': f'Strategy "{strategy_id}" uploaded successfully',
                'strategy': {
                    'strategy_id': strategy_id,
                    'class_name': metadata['class_name'],
                    'filename': filename,
                    'description': metadata.get('description', '')
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Strategy uploaded but failed to load: {error}'
            }), 500

    except Exception as e:
        logger.error(f"Error uploading custom strategy: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/custom/<int:strategy_db_id>')
@login_required
def get_custom_strategy(strategy_db_id):
    """Get details of a specific custom strategy"""
    try:
        strategy = CustomStrategy.query.filter_by(
            id=strategy_db_id,
            user_id=current_user.id
        ).first()

        if not strategy:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404

        return jsonify({
            'success': True,
            'strategy': {
                'id': strategy.id,
                'strategy_id': strategy.strategy_id,
                'class_name': strategy.class_name,
                'filename': strategy.filename,
                'description': strategy.description,
                'source_code': strategy.source_code,
                'is_validated': strategy.is_validated,
                'validation_error': strategy.validation_error,
                'version': strategy.version,
                'created_at': strategy.created_at.isoformat(),
                'updated_at': strategy.updated_at.isoformat(),
                'last_used_at': strategy.last_used_at.isoformat() if strategy.last_used_at else None
            }
        })
    except Exception as e:
        logger.error(f"Error getting custom strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/custom/<int:strategy_db_id>', methods=['DELETE'])
@login_required
def delete_custom_strategy(strategy_db_id):
    """Delete a custom strategy"""
    try:
        strategy = CustomStrategy.query.filter_by(
            id=strategy_db_id,
            user_id=current_user.id
        ).first()

        if not strategy:
            return jsonify({'success': False, 'error': 'Strategy not found'}), 404

        strategy_id = strategy.strategy_id
        filename = strategy.filename

        # Delete from file system
        loader = get_custom_strategy_loader()
        file_success, file_message = loader.delete_strategy(filename)

        # Delete from database (even if file deletion failed)
        db.session.delete(strategy)
        db.session.commit()

        logger.info(f"User {current_user.id} deleted custom strategy: {strategy_id}")

        return jsonify({
            'success': True,
            'message': f'Strategy "{strategy_id}" deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting custom strategy: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/custom/validate', methods=['POST'])
@login_required
def validate_strategy_code():
    """Validate strategy code without saving"""
    try:
        data = request.get_json()
        code = data.get('code')
        filename = data.get('filename', 'test_strategy.py')

        if not code:
            return jsonify({'success': False, 'error': 'No code provided'}), 400

        loader = get_custom_strategy_loader()
        is_valid, error_msg, metadata = loader.validate_strategy_code(code, filename)

        if is_valid:
            return jsonify({
                'success': True,
                'valid': True,
                'metadata': metadata,
                'message': 'Strategy code is valid'
            })
        else:
            return jsonify({
                'success': True,
                'valid': False,
                'error': error_msg
            })

    except Exception as e:
        logger.error(f"Error validating strategy code: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/custom/template')
@login_required
def get_strategy_template():
    """Get a template for creating custom strategies"""
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'strategies', 'custom', 'example_template.py')

        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_code = f.read()
        else:
            # Return a basic template
            template_code = """from strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    \"\"\"
    Custom trading strategy template

    Implement your trading logic by overriding the required methods.
    \"\"\"

    def __init__(self, min_strength=0.6, **kwargs):
        super().__init__()
        self.min_strength = min_strength
        # Add your custom parameters here

    def get_required_timeframes(self):
        \"\"\"Return list of required timeframes\"\"\"
        return ['5m', '1h', '4h']

    def get_required_indicators(self):
        \"\"\"Return list of required indicators\"\"\"
        return ['ema_9', 'ema_21', 'rsi', 'macd']

    def analyze(self, data, current_price):
        \"\"\"
        Analyze market data and return trading signal

        Args:
            data: Dict of timeframe data with indicators
            current_price: Current market price

        Returns:
            Signal dict with action, strength, confidence, etc.
        \"\"\"
        # Your strategy logic here

        return {
            'action': 'flat',  # 'long', 'short', or 'flat'
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': ['No signal detected'],
            'indicators': {},
            'metadata': {}
        }
"""

        return jsonify({
            'success': True,
            'template': template_code
        })
    except Exception as e:
        logger.error(f"Error getting strategy template: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # NOTE: Do not run this file directly!
    # Always use: python start_trading.py
    logger.error("="*70)
    logger.error("INCORRECT USAGE - DO NOT RUN app.py DIRECTLY!")
    logger.error("="*70)
    logger.error("This file should not be run directly.")
    logger.error("Please use the main application launcher instead:")
    logger.error("")
    logger.error("    python start_trading.py")
    logger.error("")
    logger.error("start_trading.py will handle:")
    logger.error("  - Dependency checks")
    logger.error("  - Database initialization")
    logger.error("  - Starting the bot")
    logger.error("  - Starting the dashboard")
    logger.error("  - Opening your browser")
    logger.error("="*70)
    import sys
    sys.exit(1)

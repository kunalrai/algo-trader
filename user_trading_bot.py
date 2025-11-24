"""
Per-User Trading Bot
Provides user-isolated trading bot functionality
Each user has their own bot instance that only affects their data
"""

import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from threading import Thread, Event

from flask import Flask
from flask_login import current_user

from coindcx_client import CoinDCXFuturesClient
from user_data_fetcher import UserDataFetcher, get_user_data_fetcher
from user_signal_generator import UserSignalGenerator, get_user_signal_generator
from user_order_manager import UserOrderManager, get_user_order_manager
from user_position_manager import UserPositionManager, get_user_position_manager
from user_wallet_manager import UserWalletManager, get_user_wallet_manager
from user_bot_status import get_user_bot_status_tracker
from user_activity_log import get_user_activity_log
from indicators import TechnicalIndicators
import config

logger = logging.getLogger(__name__)


class UserTradingBot:
    """
    Per-user trading bot that runs isolated for each user.
    Uses user-specific components for all operations.
    """

    def __init__(self, user_id: int, app: Flask):
        """
        Initialize trading bot for a specific user.

        Args:
            user_id: The user's database ID
            app: Flask app instance for database context
        """
        self.user_id = user_id
        self.app = app
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

        # These will be initialized when bot starts (need app context)
        self.client: Optional[CoinDCXFuturesClient] = None
        self.data_fetcher: Optional[UserDataFetcher] = None
        self.signal_generator: Optional[UserSignalGenerator] = None
        self.order_manager: Optional[UserOrderManager] = None
        self.position_manager: Optional[UserPositionManager] = None
        self.wallet_manager: Optional[UserWalletManager] = None

        # Trading state
        self.is_running = False
        self.trading_pairs: Dict[str, str] = {}
        self.timeframes: Dict[str, str] = {}
        self.trading_params: Dict = {}
        self.risk_config: Dict = {}

        # Runtime tracking
        self.start_time: Optional[float] = None
        self.total_cycles = 0

        logger.info(f"UserTradingBot created for user {user_id}")

    def _initialize_components(self):
        """Initialize all user-specific components within app context"""
        from models import User, UserProfile, UserTradingPair

        # Get user and profile
        user = User.query.get(self.user_id)
        if not user:
            raise ValueError(f"User {self.user_id} not found")

        profile = user.profile

        # Determine trading mode
        is_paper_mode = True
        if profile and profile.trading_mode == 'live' and profile.has_api_keys:
            is_paper_mode = False
            self.client = CoinDCXFuturesClient(
                api_key=profile.coindcx_api_key,
                api_secret=profile.coindcx_api_secret,
                base_url=config.BASE_URL
            )
        else:
            self.client = CoinDCXFuturesClient(
                api_key=config.API_KEY,
                api_secret=config.API_SECRET,
                base_url=config.BASE_URL
            )

        # Get user's risk config
        self.risk_config = dict(config.RISK_MANAGEMENT)
        if profile:
            self.risk_config.update({
                'max_position_size_percent': profile.max_position_size_percent,
                'leverage': profile.leverage,
                'stop_loss_percent': profile.stop_loss_percent,
                'take_profit_percent': profile.take_profit_percent,
            })

        # Get user's trading pairs
        user_pairs = UserTradingPair.query.filter_by(
            user_id=self.user_id,
            is_active=True
        ).all()

        if user_pairs:
            self.trading_pairs = {pair.display_name: pair.symbol for pair in user_pairs}
        else:
            self.trading_pairs = config.TRADING_PAIRS

        # Get trading params
        self.trading_params = dict(config.TRADING_PARAMS)
        self.trading_params['dry_run'] = is_paper_mode
        if profile:
            self.trading_params['max_open_positions'] = profile.max_open_positions

        # Get timeframes
        self.timeframes = config.TIMEFRAMES

        # Load user's saved strategy preference
        user_strategy = 'combined'  # default
        if profile and profile.default_strategy:
            user_strategy = profile.default_strategy

        # Initialize user-specific components with user's strategy
        self.data_fetcher = get_user_data_fetcher(self.user_id, self.client)
        self.signal_generator = get_user_signal_generator(
            user_id=self.user_id,
            data_fetcher=self.data_fetcher,
            indicator_config=config.INDICATORS,
            rsi_config=config.INDICATORS['RSI'],
            use_strategy_system=config.STRATEGY_CONFIG.get('enabled', False),
            user_strategy=user_strategy
        )
        self.order_manager = get_user_order_manager(
            self.user_id, self.client, self.risk_config, is_paper_mode
        )
        self.position_manager = get_user_position_manager(
            self.user_id, self.client, self.risk_config
        )
        self.wallet_manager = get_user_wallet_manager(self.user_id)

        # Verify the user's strategy was set correctly in their dedicated strategy manager
        if self.signal_generator.user_strategy == user_strategy:
            logger.info(f"User {self.user_id}: Loaded saved strategy '{user_strategy}' in dedicated strategy manager")
        else:
            logger.warning(f"User {self.user_id}: Could not load strategy '{user_strategy}', using default")

        # Log activity
        activity_log = get_user_activity_log(self.user_id)
        activity_log.log_action(
            action_type='bot_initialized',
            details={
                'user_id': self.user_id,
                'strategy': user_strategy,
                'paper_mode': is_paper_mode,
                'trading_pairs': list(self.trading_pairs.keys()),
                'risk_config': self.risk_config
            }
        )

        logger.info(f"User {self.user_id}: Components initialized (paper_mode={is_paper_mode}, strategy={user_strategy})")

    def start(self) -> bool:
        """Start the trading bot for this user"""
        if self.is_running:
            logger.warning(f"User {self.user_id}: Bot is already running")
            return False

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        return True

    def stop(self):
        """Stop the trading bot for this user"""
        if not self.is_running:
            logger.warning(f"User {self.user_id}: Bot is not running")
            return

        logger.info(f"User {self.user_id}: Stopping bot...")
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        self.is_running = False
        logger.info(f"User {self.user_id}: Bot stopped")

    def _run_loop(self):
        """Main trading loop - runs in separate thread"""
        with self.app.app_context():
            try:
                # Initialize components
                self._initialize_components()

                self.is_running = True
                self.start_time = time.time()

                # Get active strategy info from the user's signal generator (not global)
                strategy_id = self.signal_generator.user_strategy or 'combined'
                strategy_name = strategy_id  # Default to ID if name not available

                # Try to get the actual strategy name from the generator's strategy manager
                if self.signal_generator._signal_generator.strategy_manager:
                    active_strategy = self.signal_generator._signal_generator.strategy_manager.get_strategy(strategy_id)
                    if active_strategy:
                        strategy_name = active_strategy.name

                logger.info(f"User {self.user_id}: Bot starting with strategy '{strategy_id}' ({strategy_name})")

                # Update status tracker
                status_tracker = get_user_bot_status_tracker(self.user_id)
                status_tracker.start_bot(
                    scan_interval=self.trading_params.get('signal_scan_interval', 60),
                    pairs=list(self.trading_pairs.values()),
                    strategy_id=strategy_id,
                    strategy_name=strategy_name
                )

                # Log bot start
                activity_log = get_user_activity_log(self.user_id)
                activity_log.log_action(
                    action_type='bot_started',
                    details={
                        'pairs': list(self.trading_pairs.values()),
                        'mode': 'paper' if self.trading_params.get('dry_run') else 'live'
                    }
                )

                logger.info(f"User {self.user_id}: Bot started with pairs {list(self.trading_pairs.keys())}")

                # Main loop
                scan_interval = self.trading_params.get('signal_scan_interval', 60)

                while not self._stop_event.is_set():
                    try:
                        self._trading_cycle()
                        self.total_cycles += 1

                        # Update status
                        status_tracker.update_cycle(self.total_cycles)

                    except Exception as e:
                        logger.error(f"User {self.user_id}: Error in trading cycle: {e}")
                        activity_log.log_action(
                            action_type='error',
                            details={'error': str(e)}
                        )

                    # Wait for next cycle or stop signal
                    self._stop_event.wait(timeout=scan_interval)

            except Exception as e:
                logger.error(f"User {self.user_id}: Bot crashed: {e}")

            finally:
                self.is_running = False

                # Update status tracker
                with self.app.app_context():
                    status_tracker = get_user_bot_status_tracker(self.user_id)
                    status_tracker.stop_bot()

                    activity_log = get_user_activity_log(self.user_id)
                    activity_log.log_action(
                        action_type='bot_stopped',
                        details={'total_cycles': self.total_cycles}
                    )

                logger.info(f"User {self.user_id}: Bot loop ended")

    def _trading_cycle(self):
        """Execute one trading cycle"""
        status_tracker = get_user_bot_status_tracker(self.user_id)
        activity_log = get_user_activity_log(self.user_id)

        # Log cycle start
        activity_log.log_action(
            action_type='cycle_start',
            details={
                'cycle_number': self.total_cycles + 1,
                'pairs_count': len(self.trading_pairs),
                'pairs': list(self.trading_pairs.values())
            }
        )

        for pair_name, symbol in self.trading_pairs.items():
            if self._stop_event.is_set():
                break

            try:
                # Update status
                status_tracker.update_action(f"Analyzing {pair_name}", f"Scanning {symbol}")

                # Log scan start
                activity_log.log_action(
                    action_type='pair_scan_start',
                    details={
                        'pair': symbol,
                        'pair_name': pair_name,
                        'timeframes': list(self.timeframes.keys())
                    }
                )

                # Generate signal
                signal = self.signal_generator.generate_signal(symbol, self.timeframes)

                if not signal:
                    activity_log.log_action(
                        action_type='no_signal',
                        details={
                            'pair': symbol,
                            'reason': 'Signal generator returned no data'
                        }
                    )
                    continue

                # Log detailed signal analysis with strategy info
                activity_log.log_action(
                    action_type='signal_generated',
                    details={
                        'pair': symbol,
                        'action': signal['action'],
                        'strength': round(signal['strength'], 4),
                        'confidence': round(signal.get('confidence', signal['strength']), 4),
                        'price': signal.get('current_price', 0),
                        'strategy_name': signal.get('strategy_name', 'legacy'),
                        'reasons': signal.get('reasons', []),
                        'indicators': signal.get('indicators', {}),
                        'atr': signal.get('atr'),
                        'metadata': signal.get('strategy_metadata', {})
                    }
                )

                # Check if signal is strong enough
                min_strength = self.trading_params.get('min_signal_strength', 0.6)
                if signal['strength'] < min_strength:
                    activity_log.log_action(
                        action_type='signal_rejected',
                        details={
                            'pair': symbol,
                            'action': signal['action'],
                            'strength': round(signal['strength'], 4),
                            'min_required': min_strength,
                            'reason': f"Signal strength {signal['strength']:.2f} below threshold {min_strength}"
                        }
                    )
                    continue

                # Check if we can open a position
                if signal['action'] in ['long', 'short']:
                    self._process_signal(symbol, signal, activity_log, status_tracker)
                else:
                    activity_log.log_action(
                        action_type='signal_flat',
                        details={
                            'pair': symbol,
                            'action': signal['action'],
                            'reason': 'Signal action is flat - no trade'
                        }
                    )

            except Exception as e:
                logger.error(f"User {self.user_id}: Error processing {symbol}: {e}")
                activity_log.log_action(
                    action_type='error',
                    details={
                        'pair': symbol,
                        'error_type': 'processing_error',
                        'message': str(e)
                    }
                )

    def _process_signal(self, symbol: str, signal: Dict, activity_log, status_tracker):
        """Process a trading signal"""
        action = signal['action']
        strength = signal['strength']
        current_price = signal.get('current_price', 0)

        # Log decision process start
        activity_log.log_action(
            action_type='decision_start',
            details={
                'pair': symbol,
                'proposed_action': action,
                'signal_strength': round(strength, 4),
                'price': current_price,
                'strategy': signal.get('strategy_name', 'legacy')
            }
        )

        # Check if we already have a position for this pair
        if self.wallet_manager.has_position_for_pair(symbol):
            activity_log.log_action(
                action_type='decision_blocked',
                details={
                    'pair': symbol,
                    'reason': 'Already have open position for this pair',
                    'check': 'existing_position'
                }
            )
            logger.debug(f"User {self.user_id}: Already have position for {symbol}")
            return

        # Check max positions
        positions = self.wallet_manager.get_all_positions()
        max_positions = self.trading_params.get('max_open_positions', 3)
        if len(positions) >= max_positions:
            activity_log.log_action(
                action_type='decision_blocked',
                details={
                    'pair': symbol,
                    'reason': f'Maximum positions limit reached ({len(positions)}/{max_positions})',
                    'check': 'max_positions',
                    'current_positions': len(positions),
                    'max_allowed': max_positions
                }
            )
            logger.debug(f"User {self.user_id}: Max positions reached ({max_positions})")
            return

        # Get balance
        balance = self.wallet_manager.get_balance()
        if balance <= 0:
            activity_log.log_action(
                action_type='decision_blocked',
                details={
                    'pair': symbol,
                    'reason': 'Insufficient balance',
                    'check': 'balance',
                    'balance': balance
                }
            )
            logger.warning(f"User {self.user_id}: Insufficient balance")
            return

        # Log balance check passed
        activity_log.log_action(
            action_type='risk_check_passed',
            details={
                'pair': symbol,
                'check': 'balance',
                'available_balance': balance,
                'open_positions': len(positions),
                'max_positions': max_positions
            }
        )

        # Get ATR for dynamic stop loss
        atr_value = signal.get('atr')  # Try from signal first
        if atr_value is None and self.risk_config.get('use_atr_stop_loss'):
            try:
                df = self.data_fetcher.fetch_candles(symbol, '1h', limit=50)
                if not df.empty:
                    df = TechnicalIndicators.add_atr(df)
                    atr_value = df['ATR'].iloc[-1] if 'ATR' in df.columns else None
            except Exception as e:
                logger.warning(f"User {self.user_id}: Could not calculate ATR: {e}")
                activity_log.log_action(
                    action_type='atr_calculation_failed',
                    details={
                        'pair': symbol,
                        'error': str(e)
                    }
                )

        # Calculate position sizing details
        leverage = self.risk_config.get('leverage', 10)
        max_position_pct = self.risk_config.get('max_position_size_percent', 10)
        stop_loss_pct = self.risk_config.get('stop_loss_percent', 2)
        take_profit_pct = self.risk_config.get('take_profit_percent', 4)

        activity_log.log_action(
            action_type='position_sizing',
            details={
                'pair': symbol,
                'balance': balance,
                'leverage': leverage,
                'max_position_pct': max_position_pct,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct,
                'atr_value': atr_value,
                'use_atr_stop_loss': self.risk_config.get('use_atr_stop_loss', False)
            }
        )

        # Update status
        status_tracker.update_action(
            f"Opening {action.upper()} position",
            f"{symbol} @ ${current_price:.2f}"
        )

        # Open position
        result = self.order_manager.open_position_with_tp_sl(
            pair=symbol,
            side=action,
            balance=balance,
            current_price=current_price,
            signal_strength=strength,
            atr_value=atr_value
        )

        if result:
            activity_log.log_action(
                action_type='position_opened',
                details={
                    'pair': symbol,
                    'side': action,
                    'price': result['entry_price'],
                    'position_id': result.get('position_id'),
                    'size': result['position_size'],
                    'take_profit': result['take_profit'],
                    'stop_loss': result['stop_loss'],
                    'margin': result.get('margin', 0),
                    'leverage': leverage,
                    'signal_strength': round(strength, 4),
                    'strategy': signal.get('strategy_name', 'legacy'),
                    'reasons': signal.get('reasons', [])
                }
            )
            logger.info(
                f"User {self.user_id}: Opened {action.upper()} position for {symbol} "
                f"@ ${result['entry_price']:.2f}"
            )
        else:
            activity_log.log_action(
                action_type='position_open_failed',
                details={
                    'pair': symbol,
                    'side': action,
                    'price': current_price,
                    'reason': 'Order manager returned no result'
                }
            )
            logger.warning(f"User {self.user_id}: Failed to open position for {symbol}")


# Global registry of active user bots
_active_user_bots: Dict[int, UserTradingBot] = {}


def get_user_trading_bot(user_id: int, app: Flask) -> UserTradingBot:
    """
    Get or create a trading bot for the specified user.

    Args:
        user_id: User ID
        app: Flask app instance

    Returns:
        UserTradingBot instance for the user
    """
    if user_id not in _active_user_bots:
        _active_user_bots[user_id] = UserTradingBot(user_id, app)

    return _active_user_bots[user_id]


def start_user_bot(user_id: int, app: Flask) -> tuple[bool, str]:
    """
    Start the trading bot for a user.

    Args:
        user_id: User ID
        app: Flask app instance

    Returns:
        Tuple of (success, message)
    """
    bot = get_user_trading_bot(user_id, app)

    if bot.is_running:
        return False, "Bot is already running"

    success = bot.start()
    if success:
        return True, "Bot started successfully"
    else:
        return False, "Failed to start bot"


def stop_user_bot(user_id: int) -> tuple[bool, str]:
    """
    Stop the trading bot for a user.

    Args:
        user_id: User ID

    Returns:
        Tuple of (success, message)
    """
    if user_id not in _active_user_bots:
        return False, "Bot is not running"

    bot = _active_user_bots[user_id]

    if not bot.is_running:
        return False, "Bot is not running"

    bot.stop()
    return True, "Bot stopped successfully"


def is_user_bot_running(user_id: int) -> bool:
    """Check if a user's bot is running"""
    if user_id not in _active_user_bots:
        return False
    return _active_user_bots[user_id].is_running


def get_active_bot_count() -> int:
    """Get count of active bots"""
    return sum(1 for bot in _active_user_bots.values() if bot.is_running)


def stop_all_bots():
    """Stop all running bots (for shutdown)"""
    for user_id, bot in list(_active_user_bots.items()):
        if bot.is_running:
            bot.stop()
    _active_user_bots.clear()

"""
Main Trading Bot
Orchestrates multi-coin futures trading with signal-based execution
"""

import time
import logging
from typing import Dict, List
from datetime import datetime

from coindcx_client import CoinDCXFuturesClient
from data_fetcher import DataFetcher
from signal_generator import SignalGenerator
from order_manager import OrderManager
from position_manager import PositionManager
from wallet_manager import WalletManager
from bot_status import get_bot_status_tracker
from activity_log import get_activity_log

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator"""

    def __init__(self, config: Dict):
        """
        Initialize trading bot

        Args:
            config: Configuration dict with all settings
        """
        self.config = config

        # Initialize API client
        self.client = CoinDCXFuturesClient(
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            base_url=config['base_url']
        )

        # Initialize components
        self.data_fetcher = DataFetcher(self.client)
        self.signal_generator = SignalGenerator(
            self.data_fetcher,
            config['indicators'],
            config['indicators']['RSI']
        )
        self.order_manager = OrderManager(
            self.client,
            config['risk_management'],
            dry_run=config['trading_params'].get('dry_run', False),
            simulated_balance=config['trading_params'].get('simulated_balance', 1000.0)
        )
        self.position_manager = PositionManager(self.client, config['risk_management'])
        self.wallet_manager = WalletManager(self.client)

        # Trading state
        self.is_running = False
        self.trading_pairs = config['trading_pairs']
        self.timeframes = config['timeframes']
        self.trading_params = config['trading_params']

        # Runtime tracking
        self.start_time = None
        self.last_cycle_time = None
        self.total_cycles = 0
        self.last_decision = {
            'timestamp': None,
            'action': 'Initializing',
            'details': 'Bot starting up...'
        }

        # Bot status tracker (shared with dashboard)
        self.status_tracker = get_bot_status_tracker()

        # Activity log (detailed action tracking)
        self.activity_log = get_activity_log()

        logger.info("Trading bot initialized successfully")

    def start(self):
        """Start the trading bot"""
        logger.info("=" * 60)
        logger.info("STARTING CRYPTO FUTURES TRADING BOT")
        logger.info("=" * 60)

        self.is_running = True
        self.start_time = time.time()  # Record start time

        # Update status tracker
        self.status_tracker.start_bot(
            scan_interval=self.trading_params['signal_scan_interval'],
            pairs=list(self.trading_pairs.keys())
        )

        # Display initial status
        self._display_startup_info()

        # Main trading loop
        try:
            while self.is_running:
                self._trading_cycle()

                # Update status before sleep
                self.status_tracker.update_action('Waiting', f'Next scan in {self.trading_params["signal_scan_interval"]}s')

                time.sleep(self.trading_params['signal_scan_interval'])

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}")
            self.stop()

    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.is_running = False

        # Update status tracker
        self.status_tracker.stop_bot()

        # Display final summary
        self._display_final_summary()

        logger.info("Trading bot stopped")

    def _display_startup_info(self):
        """Display startup information"""
        try:
            # Get balance
            balance_summary = self.wallet_manager.get_balance_summary()

            logger.info(f"Trading Pairs: {list(self.trading_pairs.keys())}")
            logger.info(f"Timeframes: {list(self.timeframes.values())}")
            logger.info(
                f"Available Balance: {balance_summary['available_balance']:.2f} USDT"
            )
            logger.info(
                f"Max Open Positions: {self.trading_params['max_open_positions']}"
            )
            logger.info(f"Leverage: {self.config['risk_management']['leverage']}x")
            logger.info(
                f"Signal Strength Threshold: "
                f"{self.trading_params['min_signal_strength']}"
            )

        except Exception as e:
            logger.error(f"Error displaying startup info: {e}")

    def _trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # Update cycle tracking
            self.total_cycles += 1
            self.last_cycle_time = time.time()

            # Update status tracker
            self.status_tracker.update_cycle(self.total_cycles)

            logger.info("\n" + "=" * 60)
            logger.info(f"Trading Cycle #{self.total_cycles} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # 1. Check wallet balance and health
            self.status_tracker.update_action('Checking Balance', 'Verifying wallet health and available margin')

            balance_health = self.wallet_manager.get_balance_health()
            logger.info(
                f"Balance Health: {balance_health['status']} "
                f"(Utilization: {balance_health['utilization_percent']:.2f}%)"
            )

            if balance_health['status'] == 'critical':
                logger.warning("Critical balance utilization, skipping new trades")
                self.status_tracker.update_action('Risk Management', 'Critical balance - monitoring only, no new trades')
                self._monitor_positions_only()
                return

            # 2. Monitor existing positions
            self.status_tracker.update_action('Monitoring Positions', 'Checking TP/SL triggers and updating trailing stops')
            self._monitor_and_manage_positions()

            # 3. Check if we can open new positions
            if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                current_positions = len(self.order_manager.simulated_wallet.get_all_positions())
            else:
                current_positions = self.position_manager.get_open_positions_count()

            max_positions = self.trading_params['max_open_positions']

            if current_positions >= max_positions:
                logger.info(
                    f"Max positions reached ({current_positions}/{max_positions}), "
                    f"monitoring only"
                )
                self.status_tracker.update_action('Position Limit Reached', f'{current_positions}/{max_positions} positions open - monitoring only')
                return

            # 4. Scan for new trading signals
            self.status_tracker.update_action('Scanning Markets', f'Analyzing {len(self.trading_pairs)} pairs for entry signals')
            self._scan_for_signals()

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            self.status_tracker.update_action('Error', f'Trading cycle error: {str(e)}')

    def _monitor_and_manage_positions(self):
        """Monitor and manage all open positions"""
        try:
            # Get positions from simulated wallet if in dry-run mode
            if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                positions = self.order_manager.simulated_wallet.get_all_positions()
            else:
                positions = self.position_manager.get_all_positions()

            if not positions:
                logger.info("No open positions")
                return

            logger.info(f"Monitoring {len(positions)} open positions")

            for position in positions:
                self._manage_single_position(position)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    def _manage_single_position(self, position: Dict):
        """
        Manage a single position (check TP/SL, update trailing stop, etc.)

        Args:
            position: Position dict
        """
        try:
            pair = position.get('pair')
            position_id = position.get('position_id')
            side = position.get('side')

            # Get current price
            current_price = self.data_fetcher.get_latest_price(pair)

            if current_price == 0:
                logger.warning(f"Could not get price for {pair}")
                return

            # Update simulated wallet position price if in dry-run mode
            if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                self.order_manager.simulated_wallet.update_position_price(position_id, current_price)
                # Get position from simulated wallet
                sim_position = self.order_manager.simulated_wallet.get_position(position_id)
                if sim_position:
                    position = sim_position

            # Calculate P&L
            pnl_info = self.position_manager.monitor_position_pnl(position, current_price)

            logger.info(
                f"Position {pair} ({side.upper()}): "
                f"P&L: {pnl_info['pnl_percent']:.2f}% "
                f"(Entry: {pnl_info['entry_price']:.2f}, "
                f"Current: {current_price:.2f})"
            )

            # Check if TP/SL hit
            tp_sl_status = self.position_manager.check_tp_sl_hit(position, current_price)

            if tp_sl_status:
                logger.info(f"{tp_sl_status} hit for {pair}, closing position")

                # Close in simulated wallet if dry-run
                if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                    self.order_manager.simulated_wallet.close_position(
                        position_id,
                        current_price,
                        f"{tp_sl_status} reached"
                    )
                else:
                    self.position_manager.close_position(
                        position_id,
                        f"{tp_sl_status} reached"
                    )
                return

            # Update trailing stop if enabled
            new_sl = self.position_manager.update_trailing_stop(position, current_price)

            if new_sl:
                # Update position's stop loss
                position['stop_loss'] = new_sl
                self.position_manager.update_position_tracking(position_id, position)

            # Check for signal reversal
            signal = self.signal_generator.generate_signal(pair, self.timeframes)

            if signal:
                should_close = self.signal_generator.should_close_position(
                    position,
                    signal
                )

                if should_close:
                    logger.info(f"Signal reversal detected for {pair}, closing position")

                    # Close in simulated wallet if dry-run
                    if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                        self.order_manager.simulated_wallet.close_position(
                            position_id,
                            current_price,
                            "Signal reversal"
                        )
                    else:
                        self.position_manager.close_position(
                            position_id,
                            "Signal reversal"
                        )

        except Exception as e:
            logger.error(f"Error managing position: {e}")

    def _monitor_positions_only(self):
        """Monitor positions without opening new ones"""
        self._monitor_and_manage_positions()

    def _scan_for_signals(self):
        """Scan all trading pairs for signals"""
        try:
            logger.info(f"Scanning {len(self.trading_pairs)} pairs for signals...")

            for coin_name, pair in self.trading_pairs.items():
                # Log that we're analyzing this pair
                self.activity_log.log_action('analyzing_pair', {
                    'pair': pair,
                    'coin': coin_name,
                    'status': 'checking_position'
                })

                # Skip if already have position for this pair
                has_position = False
                if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                    has_position = self.order_manager.simulated_wallet.has_position_for_pair(pair)
                else:
                    has_position = self.position_manager.has_open_position_for_pair(pair)

                if has_position:
                    logger.debug(f"Skipping {pair}, already have open position")
                    self.activity_log.log_position_decision(
                        pair, 'skip', 'Already have open position for this pair'
                    )
                    continue

                # Generate signal
                signal = self.signal_generator.generate_signal(pair, self.timeframes)

                if signal:
                    # Log the signal analysis
                    reasons = signal.get('reasons', [])
                    self.activity_log.log_signal_analysis(
                        pair,
                        signal.get('action', 'flat'),
                        signal.get('strength', 0),
                        reasons
                    )

                    self._evaluate_signal(signal)

        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")
            self.activity_log.log_error('scan_error', str(e))

    def _evaluate_signal(self, signal: Dict):
        """
        Evaluate a trading signal and execute if conditions met

        Args:
            signal: Signal dict from signal generator
        """
        try:
            pair = signal['pair']
            action = signal['action']
            strength = signal['strength']
            current_price = signal['current_price']

            # Check if signal meets minimum strength
            if strength < self.trading_params['min_signal_strength']:
                logger.debug(
                    f"Signal for {pair} below threshold "
                    f"({strength:.2f} < {self.trading_params['min_signal_strength']})"
                )
                return

            # Check if action is enabled
            if action == 'long' and not self.trading_params['enable_long']:
                logger.debug(f"Long trading disabled, skipping {pair}")
                return

            if action == 'short' and not self.trading_params['enable_short']:
                logger.debug(f"Short trading disabled, skipping {pair}")
                return

            if action == 'flat':
                logger.debug(f"No clear signal for {pair}")
                return

            # Execute trade
            logger.info(
                f"SIGNAL DETECTED: {pair} - {action.upper()} "
                f"(Strength: {strength:.2f})"
            )

            self._execute_trade(pair, action, strength, current_price)

        except Exception as e:
            logger.error(f"Error evaluating signal: {e}")

    def _execute_trade(self, pair: str, side: str, strength: float, current_price: float):
        """
        Execute a trade based on signal

        Args:
            pair: Trading pair
            side: 'long' or 'short'
            strength: Signal strength
            current_price: Current market price
        """
        try:
            # Get available balance (from simulated wallet in dry-run mode)
            if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                available_balance = self.order_manager.simulated_wallet.get_balance()
            else:
                available_balance = self.wallet_manager.get_available_balance()

            if available_balance <= 0:
                logger.warning("Insufficient balance for trade")
                return

            logger.info(f"Executing {side.upper()} trade for {pair}")

            # Open position with TP/SL
            result = self.order_manager.open_position_with_tp_sl(
                pair=pair,
                side=side,
                balance=available_balance,
                current_price=current_price,
                signal_strength=strength
            )

            if result:
                logger.info(
                    f"Position opened successfully:\n"
                    f"  Pair: {pair}\n"
                    f"  Side: {side.upper()}\n"
                    f"  Entry: {result['entry_price']:.2f}\n"
                    f"  Size: {result['position_size']:.6f}\n"
                    f"  TP: {result['take_profit']:.2f}\n"
                    f"  SL: {result['stop_loss']:.2f}"
                )

                # Track position locally
                if 'position_id' in result:
                    self.position_manager.update_position_tracking(
                        result['position_id'],
                        result
                    )
            else:
                logger.error(f"Failed to open position for {pair}")

        except Exception as e:
            logger.error(f"Error executing trade: {e}")

    def _display_final_summary(self):
        """Display final summary when bot stops"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("FINAL SUMMARY")
            logger.info("=" * 60)

            # Show simulated wallet stats if in dry-run mode
            if self.trading_params.get('dry_run') and self.order_manager.simulated_wallet:
                wallet = self.order_manager.simulated_wallet
                balance_info = wallet.get_balance_summary()
                stats = wallet.get_statistics()

                logger.info(f"Initial Balance: ${balance_info['initial_balance']:.2f} USDT")
                logger.info(f"Final Balance: ${balance_info['total_balance']:.2f} USDT")
                logger.info(f"Total P&L: ${balance_info['total_pnl']:.2f} ({balance_info['pnl_percent']:.2f}%)")
                logger.info(f"Open Positions: {balance_info['position_count']}")
                logger.info(f"Total Trades: {stats['total_trades']}")

                if stats['total_trades'] > 0:
                    logger.info(f"Winning Trades: {stats['winning_trades']}")
                    logger.info(f"Losing Trades: {stats['losing_trades']}")
                    logger.info(f"Win Rate: {stats['win_rate']:.2f}%")
                    logger.info(f"Avg Win: ${stats['avg_win']:.2f}")
                    logger.info(f"Avg Loss: ${stats['avg_loss']:.2f}")
                    logger.info(f"Largest Win: ${stats['largest_win']:.2f}")
                    logger.info(f"Largest Loss: ${stats['largest_loss']:.2f}")
            else:
                # Get position summary
                summary = self.position_manager.get_position_summary()
                logger.info(
                    f"Open Positions: {summary['total_positions']} "
                    f"(Long: {summary['long_positions']}, Short: {summary['short_positions']})"
                )

                # Get balance
                balance = self.wallet_manager.get_balance_summary()
                logger.info(f"Final Balance: {balance['available_balance']:.2f} USDT")

        except Exception as e:
            logger.error(f"Error displaying final summary: {e}")

    def get_status(self) -> Dict:
        """
        Get current bot status

        Returns:
            Dict with bot status information
        """
        try:
            return {
                'is_running': self.is_running,
                'balance': self.wallet_manager.get_balance_summary(),
                'positions': self.position_manager.get_position_summary(),
                'balance_health': self.wallet_manager.get_balance_health()
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'is_running': self.is_running, 'error': str(e)}

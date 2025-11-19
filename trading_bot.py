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
        self.order_manager = OrderManager(self.client, config['risk_management'])
        self.position_manager = PositionManager(self.client, config['risk_management'])
        self.wallet_manager = WalletManager(self.client)

        # Trading state
        self.is_running = False
        self.trading_pairs = config['trading_pairs']
        self.timeframes = config['timeframes']
        self.trading_params = config['trading_params']

        logger.info("Trading bot initialized successfully")

    def start(self):
        """Start the trading bot"""
        logger.info("=" * 60)
        logger.info("STARTING CRYPTO FUTURES TRADING BOT")
        logger.info("=" * 60)

        self.is_running = True

        # Display initial status
        self._display_startup_info()

        # Main trading loop
        try:
            while self.is_running:
                self._trading_cycle()
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
            logger.info("\n" + "=" * 60)
            logger.info(f"Trading Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # 1. Check wallet balance and health
            balance_health = self.wallet_manager.get_balance_health()
            logger.info(
                f"Balance Health: {balance_health['status']} "
                f"(Utilization: {balance_health['utilization_percent']:.2f}%)"
            )

            if balance_health['status'] == 'critical':
                logger.warning("Critical balance utilization, skipping new trades")
                self._monitor_positions_only()
                return

            # 2. Monitor existing positions
            self._monitor_and_manage_positions()

            # 3. Check if we can open new positions
            current_positions = self.position_manager.get_open_positions_count()
            max_positions = self.trading_params['max_open_positions']

            if current_positions >= max_positions:
                logger.info(
                    f"Max positions reached ({current_positions}/{max_positions}), "
                    f"monitoring only"
                )
                return

            # 4. Scan for new trading signals
            self._scan_for_signals()

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def _monitor_and_manage_positions(self):
        """Monitor and manage all open positions"""
        try:
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
                # Skip if already have position for this pair
                if self.position_manager.has_open_position_for_pair(pair):
                    logger.debug(f"Skipping {pair}, already have open position")
                    continue

                # Generate signal
                signal = self.signal_generator.generate_signal(pair, self.timeframes)

                if signal:
                    self._evaluate_signal(signal)

        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")

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
            # Get available balance
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

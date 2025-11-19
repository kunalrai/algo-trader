"""
Order Manager Module
Handles order execution, TP/SL calculation, and order management
"""

from typing import Dict, Optional
import logging
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class OrderManager:
    """Manage order execution with TP/SL calculation"""

    def __init__(self, client: CoinDCXFuturesClient, risk_config: Dict):
        self.client = client
        self.risk_config = risk_config

    def calculate_position_size(self, balance: float, current_price: float,
                               leverage: int, max_position_percent: float) -> float:
        """
        Calculate position size based on available balance and risk parameters

        Args:
            balance: Available futures balance
            current_price: Current market price
            leverage: Leverage to use
            max_position_percent: Maximum % of balance to use

        Returns:
            Position size (amount of asset)
        """
        try:
            # Calculate max position value
            max_position_value = balance * (max_position_percent / 100)

            # Calculate position size considering leverage
            position_size = (max_position_value * leverage) / current_price

            logger.info(
                f"Position size calculated: {position_size:.6f} "
                f"(Balance: {balance}, Price: {current_price}, Leverage: {leverage}x)"
            )

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def calculate_tp_sl_prices(self, entry_price: float, side: str,
                              tp_percent: float, sl_percent: float) -> Dict[str, float]:
        """
        Calculate take profit and stop loss prices

        Args:
            entry_price: Entry price
            side: 'long' or 'short'
            tp_percent: Take profit percentage
            sl_percent: Stop loss percentage

        Returns:
            Dict with TP and SL prices
        """
        try:
            if side == 'long':
                # Long position
                take_profit = entry_price * (1 + tp_percent / 100)
                stop_loss = entry_price * (1 - sl_percent / 100)
            else:
                # Short position
                take_profit = entry_price * (1 - tp_percent / 100)
                stop_loss = entry_price * (1 + sl_percent / 100)

            logger.info(
                f"TP/SL calculated for {side.upper()} at {entry_price}: "
                f"TP={take_profit:.2f}, SL={stop_loss:.2f}"
            )

            return {
                'take_profit': take_profit,
                'stop_loss': stop_loss
            }

        except Exception as e:
            logger.error(f"Error calculating TP/SL: {e}")
            return {'take_profit': 0, 'stop_loss': 0}

    def execute_market_order(self, pair: str, side: str, size: float,
                           balance: float) -> Optional[Dict]:
        """
        Execute market order with calculated position size

        Args:
            pair: Trading pair
            side: 'long' or 'short'
            size: Position size
            balance: Available balance

        Returns:
            Order response or None
        """
        try:
            # Validate inputs
            if size <= 0:
                logger.error(f"Invalid position size: {size}")
                return None

            if balance <= 0:
                logger.error(f"Insufficient balance: {balance}")
                return None

            logger.info(f"Executing {side.upper()} market order for {pair}, size: {size}")

            # Execute market order
            order_response = self.client.create_order(
                pair=pair,
                side=side,
                order_type='market_order',
                size=size,
                time_in_force='GTC'
            )

            logger.info(f"Order executed successfully: {order_response}")
            return order_response

        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            return None

    def place_tp_sl_orders(self, position_id: str, tp_price: float,
                          sl_price: float, size: float) -> Dict[str, Optional[Dict]]:
        """
        Place take profit and stop loss orders for a position

        Args:
            position_id: Position ID
            tp_price: Take profit price
            sl_price: Stop loss price
            size: Position size

        Returns:
            Dict with TP and SL order responses
        """
        result = {
            'tp_order': None,
            'sl_order': None
        }

        try:
            # Place take profit order
            logger.info(f"Placing TP order at {tp_price} for position {position_id}")
            tp_order = self.client.create_take_profit_order(
                position_id=position_id,
                price=tp_price,
                size=size
            )
            result['tp_order'] = tp_order
            logger.info(f"TP order placed successfully: {tp_order}")

        except Exception as e:
            logger.error(f"Error placing TP order: {e}")

        try:
            # Place stop loss order
            logger.info(f"Placing SL order at {sl_price} for position {position_id}")
            sl_order = self.client.create_stop_loss_order(
                position_id=position_id,
                price=sl_price,
                size=size
            )
            result['sl_order'] = sl_order
            logger.info(f"SL order placed successfully: {sl_order}")

        except Exception as e:
            logger.error(f"Error placing SL order: {e}")

        return result

    def open_position_with_tp_sl(self, pair: str, side: str, balance: float,
                                current_price: float, signal_strength: float) -> Optional[Dict]:
        """
        Open a position with automatic TP/SL orders

        Args:
            pair: Trading pair
            side: 'long' or 'short'
            balance: Available balance
            current_price: Current market price
            signal_strength: Signal strength (affects position size)

        Returns:
            Dict with position and order details
        """
        try:
            # Calculate position size
            leverage = self.risk_config['leverage']
            max_position_percent = self.risk_config['max_position_size_percent']

            # Adjust position size based on signal strength
            adjusted_percent = max_position_percent * signal_strength

            position_size = self.calculate_position_size(
                balance, current_price, leverage, adjusted_percent
            )

            if position_size <= 0:
                logger.warning(f"Position size too small, skipping trade")
                return None

            # Execute market order
            order = self.execute_market_order(pair, side, position_size, balance)

            if not order:
                logger.error(f"Failed to execute market order")
                return None

            # Get entry price from order response
            entry_price = float(order.get('average_price', current_price))

            # Calculate TP/SL prices
            tp_sl = self.calculate_tp_sl_prices(
                entry_price,
                side,
                self.risk_config['take_profit_percent'],
                self.risk_config['stop_loss_percent']
            )

            # Get position ID from order
            position_id = order.get('position_id')

            if position_id:
                # Place TP/SL orders
                tp_sl_orders = self.place_tp_sl_orders(
                    position_id,
                    tp_sl['take_profit'],
                    tp_sl['stop_loss'],
                    position_size
                )

                return {
                    'order': order,
                    'position_id': position_id,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'take_profit': tp_sl['take_profit'],
                    'stop_loss': tp_sl['stop_loss'],
                    'tp_order': tp_sl_orders['tp_order'],
                    'sl_order': tp_sl_orders['sl_order'],
                    'side': side,
                    'pair': pair
                }
            else:
                logger.warning(f"No position ID in order response")
                return {
                    'order': order,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'take_profit': tp_sl['take_profit'],
                    'stop_loss': tp_sl['stop_loss'],
                    'side': side,
                    'pair': pair
                }

        except Exception as e:
            logger.error(f"Error opening position with TP/SL: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order"""
        try:
            response = self.client.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled: {response}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def cancel_all_orders_for_pair(self, pair: str) -> bool:
        """Cancel all open orders for a trading pair"""
        try:
            response = self.client.cancel_all_orders(pair)
            logger.info(f"All orders cancelled for {pair}: {response}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling orders for {pair}: {e}")
            return False

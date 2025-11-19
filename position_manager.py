"""
Position Manager Module
Monitors and manages open positions, handles TP/SL, and position tracking
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class PositionManager:
    """Manage and monitor trading positions"""

    def __init__(self, client: CoinDCXFuturesClient, risk_config: Dict):
        self.client = client
        self.risk_config = risk_config
        self.active_positions = {}  # Local tracking of positions

    def get_all_positions(self) -> List[Dict]:
        """
        Get all active positions from exchange

        Returns:
            List of active positions (only positions with active_pos > 0)
        """
        try:
            positions = self.client.get_positions()

            # Filter for only truly active positions (active_pos > 0)
            active_positions = [
                pos for pos in positions
                if abs(float(pos.get('active_pos', 0))) > 0
            ]

            logger.info(
                f"Retrieved {len(positions)} total positions, "
                f"{len(active_positions)} actually active (active_pos > 0)"
            )
            return active_positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_position_for_pair(self, pair: str) -> Optional[Dict]:
        """
        Get active position for a specific pair

        Args:
            pair: Trading pair (in CoinDCX format: 'B-BTC_USDT')

        Returns:
            Position dict or None
        """
        try:
            positions = self.client.get_positions(pair=pair)

            # Filter for active positions only
            active_positions = [
                pos for pos in positions
                if abs(float(pos.get('active_pos', 0))) > 0
            ]

            if active_positions and len(active_positions) > 0:
                return active_positions[0]
            return None
        except Exception as e:
            logger.error(f"Error getting position for {pair}: {e}")
            return None

    def update_position_tracking(self, position_id: str, position_data: Dict):
        """
        Update local position tracking

        Args:
            position_id: Position ID
            position_data: Position data dict
        """
        self.active_positions[position_id] = {
            **position_data,
            'last_updated': datetime.now()
        }

    def check_position_status(self, position_id: str) -> Optional[Dict]:
        """
        Check status of a specific position

        Args:
            position_id: Position ID

        Returns:
            Position status dict
        """
        try:
            position = self.client.get_position_by_id(position_id)
            logger.debug(f"Position {position_id} status: {position.get('status')}")
            return position
        except Exception as e:
            logger.error(f"Error checking position {position_id}: {e}")
            return None

    def monitor_position_pnl(self, position: Dict, current_price: float) -> Dict:
        """
        Calculate current P&L for a position

        Args:
            position: Position dict
            current_price: Current market price

        Returns:
            Dict with P&L information
        """
        try:
            entry_price = float(position.get('entry_price', 0))
            size = float(position.get('size', 0))
            side = position.get('side', '')

            if entry_price == 0 or size == 0:
                return {'pnl': 0, 'pnl_percent': 0}

            # Calculate P&L
            if side == 'long':
                pnl = (current_price - entry_price) * size
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # short
                pnl = (entry_price - current_price) * size
                pnl_percent = ((entry_price - current_price) / entry_price) * 100

            return {
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'current_price': current_price,
                'entry_price': entry_price
            }

        except Exception as e:
            logger.error(f"Error calculating P&L: {e}")
            return {'pnl': 0, 'pnl_percent': 0}

    def check_tp_sl_hit(self, position: Dict, current_price: float) -> Optional[str]:
        """
        Check if TP or SL has been hit

        Args:
            position: Position dict with TP/SL levels
            current_price: Current market price

        Returns:
            'TP' if take profit hit, 'SL' if stop loss hit, None otherwise
        """
        try:
            tp_price = position.get('take_profit', 0)
            sl_price = position.get('stop_loss', 0)
            side = position.get('side', '')

            if side == 'long':
                # Long position
                if tp_price > 0 and current_price >= tp_price:
                    logger.info(f"Take Profit hit for LONG position at {current_price}")
                    return 'TP'
                if sl_price > 0 and current_price <= sl_price:
                    logger.warning(f"Stop Loss hit for LONG position at {current_price}")
                    return 'SL'

            elif side == 'short':
                # Short position
                if tp_price > 0 and current_price <= tp_price:
                    logger.info(f"Take Profit hit for SHORT position at {current_price}")
                    return 'TP'
                if sl_price > 0 and current_price >= sl_price:
                    logger.warning(f"Stop Loss hit for SHORT position at {current_price}")
                    return 'SL'

        except Exception as e:
            logger.error(f"Error checking TP/SL: {e}")

        return None

    def update_trailing_stop(self, position: Dict, current_price: float) -> Optional[float]:
        """
        Update trailing stop loss based on current price

        Args:
            position: Position dict
            current_price: Current market price

        Returns:
            New stop loss price or None
        """
        if not self.risk_config.get('trailing_stop', False):
            return None

        try:
            entry_price = float(position.get('entry_price', 0))
            current_sl = position.get('stop_loss', 0)
            side = position.get('side', '')
            trailing_percent = self.risk_config.get('trailing_stop_percent', 1.5)

            if side == 'long':
                # Calculate trailing stop for long position
                profit_percent = ((current_price - entry_price) / entry_price) * 100

                # Only activate trailing stop if in profit
                if profit_percent > trailing_percent:
                    new_sl = current_price * (1 - trailing_percent / 100)

                    # Only update if new SL is higher than current
                    if current_sl == 0 or new_sl > current_sl:
                        logger.info(
                            f"Updating trailing stop for LONG: "
                            f"{current_sl:.2f} -> {new_sl:.2f}"
                        )
                        return new_sl

            elif side == 'short':
                # Calculate trailing stop for short position
                profit_percent = ((entry_price - current_price) / entry_price) * 100

                # Only activate trailing stop if in profit
                if profit_percent > trailing_percent:
                    new_sl = current_price * (1 + trailing_percent / 100)

                    # Only update if new SL is lower than current
                    if current_sl == 0 or new_sl < current_sl:
                        logger.info(
                            f"Updating trailing stop for SHORT: "
                            f"{current_sl:.2f} -> {new_sl:.2f}"
                        )
                        return new_sl

        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")

        return None

    def close_position(self, position_id: str, reason: str = "Manual close") -> bool:
        """
        Close a position

        Args:
            position_id: Position ID to close
            reason: Reason for closing

        Returns:
            True if successful
        """
        try:
            logger.info(f"Closing position {position_id}: {reason}")
            response = self.client.close_position(position_id)

            # Remove from local tracking
            if position_id in self.active_positions:
                del self.active_positions[position_id]

            logger.info(f"Position {position_id} closed successfully: {response}")
            return True

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return False

    def get_open_positions_count(self) -> int:
        """Get count of open positions"""
        try:
            positions = self.get_all_positions()
            return len(positions)
        except Exception as e:
            logger.error(f"Error getting positions count: {e}")
            return 0

    def has_open_position_for_pair(self, pair: str) -> bool:
        """
        Check if there's an open position for a pair

        Args:
            pair: Trading pair

        Returns:
            True if position exists
        """
        position = self.get_position_for_pair(pair)
        return position is not None

    def get_position_summary(self) -> Dict:
        """
        Get summary of all positions

        Returns:
            Dict with position summary
        """
        try:
            positions = self.get_all_positions()

            total_pnl = 0.0
            summary = {
                'total_positions': len(positions),
                'long_positions': 0,
                'short_positions': 0,
                'positions': []
            }

            for pos in positions:
                side = pos.get('side', '')
                if side == 'long':
                    summary['long_positions'] += 1
                elif side == 'short':
                    summary['short_positions'] += 1

                # Add position info
                summary['positions'].append({
                    'pair': pos.get('pair'),
                    'side': side,
                    'entry_price': pos.get('entry_price'),
                    'size': pos.get('size'),
                    'position_id': pos.get('position_id')
                })

            logger.info(
                f"Position summary: {summary['total_positions']} total "
                f"({summary['long_positions']} long, {summary['short_positions']} short)"
            )

            return summary

        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return {
                'total_positions': 0,
                'long_positions': 0,
                'short_positions': 0,
                'positions': []
            }

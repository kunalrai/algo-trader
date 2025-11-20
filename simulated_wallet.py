"""
Simulated Wallet for Dry-Run Mode
Tracks paper trading balance and P&L
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SimulatedWallet:
    """Simulated wallet for paper trading"""

    def __init__(self, initial_balance: float = 1000.0, data_file: str = "simulated_wallet.json"):
        """
        Initialize simulated wallet

        Args:
            initial_balance: Starting balance in USDT
            data_file: File to persist wallet data
        """
        self.data_file = data_file
        self.data = self._load_or_create(initial_balance)

    def _load_or_create(self, initial_balance: float) -> Dict:
        """Load existing wallet data or create new"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded simulated wallet: {data['balance']:.2f} USDT")
                    return data
            except Exception as e:
                logger.error(f"Error loading wallet data: {e}")

        # Create new wallet
        data = {
            'initial_balance': initial_balance,
            'balance': initial_balance,
            'locked_margin': 0.0,
            'total_pnl': 0.0,
            'positions': {},
            'trade_history': [],
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        self._save(data)
        logger.info(f"Created new simulated wallet: {initial_balance:.2f} USDT")
        return data

    def _save(self, data: Dict = None):
        """Save wallet data to file"""
        if data is None:
            data = self.data

        data['last_updated'] = datetime.now().isoformat()

        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving wallet data: {e}")

    def get_balance(self) -> float:
        """Get available balance"""
        return self.data['balance']

    def get_total_balance(self) -> float:
        """Get total balance (available + locked)"""
        return self.data['balance'] + self.data['locked_margin']

    def get_locked_margin(self) -> float:
        """Get locked margin in positions"""
        return self.data['locked_margin']

    def get_balance_summary(self) -> Dict:
        """Get balance summary"""
        total = self.get_total_balance()
        initial = self.data['initial_balance']

        return {
            'total_balance': total,
            'available_balance': self.data['balance'],
            'used_margin': self.data['locked_margin'],
            'total_pnl': self.data['total_pnl'],
            'pnl_percent': ((total - initial) / initial * 100) if initial > 0 else 0,
            'initial_balance': initial,
            'position_count': len(self.data['positions']),
            'trade_count': len(self.data['trade_history'])
        }

    def open_position(self, position_id: str, pair: str, side: str,
                     entry_price: float, size: float, margin: float,
                     leverage: int, stop_loss: float, take_profit: float) -> bool:
        """
        Open a simulated position

        Args:
            position_id: Unique position ID
            pair: Trading pair
            side: 'long' or 'short'
            entry_price: Entry price
            size: Position size
            margin: Margin required
            leverage: Leverage used
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            True if successful
        """
        if self.data['balance'] < margin:
            logger.warning(f"Insufficient balance: {self.data['balance']:.2f} < {margin:.2f}")
            return False

        # Lock margin
        self.data['balance'] -= margin
        self.data['locked_margin'] += margin

        # Create position
        position = {
            'position_id': position_id,
            'pair': pair,
            'side': side,
            'entry_price': entry_price,
            'current_price': entry_price,
            'size': size,
            'margin': margin,
            'leverage': leverage,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'opened_at': datetime.now().isoformat(),
            'status': 'open'
        }

        self.data['positions'][position_id] = position

        # Record trade
        self.data['trade_history'].append({
            'type': 'open',
            'position_id': position_id,
            'pair': pair,
            'side': side,
            'price': entry_price,
            'size': size,
            'margin': margin,
            'timestamp': datetime.now().isoformat()
        })

        self._save()

        logger.info(
            f"Opened simulated {side.upper()} position:\n"
            f"  Pair: {pair}\n"
            f"  Entry: ${entry_price:.2f}\n"
            f"  Size: {size:.6f}\n"
            f"  Margin: ${margin:.2f}\n"
            f"  Leverage: {leverage}x\n"
            f"  Available Balance: ${self.data['balance']:.2f}"
        )

        return True

    def update_position_price(self, position_id: str, current_price: float):
        """Update position with current price and calculate P&L"""
        if position_id not in self.data['positions']:
            return

        position = self.data['positions'][position_id]
        position['current_price'] = current_price

        # Calculate P&L
        entry = position['entry_price']
        size = position['size']
        side = position['side']

        if side == 'long':
            pnl = (current_price - entry) * size
        else:  # short
            pnl = (entry - current_price) * size

        position['pnl'] = pnl
        position['pnl_percent'] = (pnl / position['margin']) * 100 if position['margin'] > 0 else 0

        self._save()

    def close_position(self, position_id: str, close_price: float, reason: str = "") -> Optional[Dict]:
        """
        Close a simulated position

        Args:
            position_id: Position ID
            close_price: Closing price
            reason: Reason for closing

        Returns:
            Position result dict
        """
        if position_id not in self.data['positions']:
            logger.warning(f"Position {position_id} not found")
            return None

        position = self.data['positions'][position_id]

        # Calculate final P&L
        entry = position['entry_price']
        size = position['size']
        side = position['side']

        if side == 'long':
            pnl = (close_price - entry) * size
        else:  # short
            pnl = (entry - close_price) * size

        # Release margin + P&L
        self.data['locked_margin'] -= position['margin']
        self.data['balance'] += position['margin'] + pnl
        self.data['total_pnl'] += pnl

        # Record trade
        self.data['trade_history'].append({
            'type': 'close',
            'position_id': position_id,
            'pair': position['pair'],
            'side': position['side'],
            'entry_price': entry,
            'close_price': close_price,
            'size': size,
            'pnl': pnl,
            'pnl_percent': (pnl / position['margin']) * 100 if position['margin'] > 0 else 0,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })

        # Remove position
        result = position.copy()
        result['close_price'] = close_price
        result['final_pnl'] = pnl
        result['close_reason'] = reason

        del self.data['positions'][position_id]

        self._save()

        logger.info(
            f"Closed simulated {side.upper()} position:\n"
            f"  Pair: {position['pair']}\n"
            f"  Entry: ${entry:.2f}\n"
            f"  Exit: ${close_price:.2f}\n"
            f"  P&L: ${pnl:.2f} ({(pnl/position['margin'])*100:.2f}%)\n"
            f"  Reason: {reason}\n"
            f"  Available Balance: ${self.data['balance']:.2f}\n"
            f"  Total P&L: ${self.data['total_pnl']:.2f}"
        )

        return result

    def get_position(self, position_id: str) -> Optional[Dict]:
        """Get position by ID"""
        return self.data['positions'].get(position_id)

    def get_all_positions(self) -> List[Dict]:
        """Get all open positions"""
        return list(self.data['positions'].values())

    def has_position_for_pair(self, pair: str) -> bool:
        """Check if there's an open position for pair"""
        for pos in self.data['positions'].values():
            if pos['pair'] == pair:
                return True
        return False

    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """Get recent trade history"""
        return self.data['trade_history'][-limit:]

    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        trades = self.data['trade_history']
        closed_trades = [t for t in trades if t['type'] == 'close']

        if not closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'total_pnl': self.data['total_pnl']
            }

        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['pnl'] <= 0]

        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0,
            'avg_win': sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            'largest_win': max((t['pnl'] for t in winning_trades), default=0),
            'largest_loss': min((t['pnl'] for t in losing_trades), default=0),
            'total_pnl': self.data['total_pnl'],
            'pnl_percent': ((self.get_total_balance() - self.data['initial_balance']) / self.data['initial_balance'] * 100)
        }

    def reset(self, initial_balance: float = 1000.0):
        """Reset wallet to initial state"""
        self.data = {
            'initial_balance': initial_balance,
            'balance': initial_balance,
            'locked_margin': 0.0,
            'total_pnl': 0.0,
            'positions': {},
            'trade_history': [],
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
        self._save()
        logger.info(f"Reset simulated wallet to {initial_balance:.2f} USDT")

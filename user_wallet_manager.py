"""
Per-User Wallet Manager
Provides user-isolated wallet operations using database-backed storage
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging
import uuid

from flask_login import current_user
from models import db, UserSimulatedWallet, UserSimulatedPosition, UserTradeHistory

logger = logging.getLogger(__name__)


class UserWalletManager:
    """
    Manages per-user simulated wallets using database storage.
    Each user has their own isolated wallet, positions, and trade history.
    """

    def __init__(self, user_id: int):
        """
        Initialize wallet manager for a specific user.

        Args:
            user_id: The user's database ID
        """
        self.user_id = user_id
        self._ensure_wallet_exists()

    def _ensure_wallet_exists(self):
        """Ensure user has a simulated wallet, create if not exists"""
        wallet = UserSimulatedWallet.query.filter_by(user_id=self.user_id).first()
        if not wallet:
            # Get initial balance from user profile if available
            from models import UserProfile
            profile = UserProfile.query.filter_by(user_id=self.user_id).first()
            initial_balance = profile.simulated_balance if profile else 1000.0

            wallet = UserSimulatedWallet(
                user_id=self.user_id,
                balance=initial_balance,
                initial_balance=initial_balance
            )
            db.session.add(wallet)
            db.session.commit()
            logger.info(f"Created simulated wallet for user {self.user_id} with balance ${initial_balance:.2f}")

    def _get_wallet(self) -> UserSimulatedWallet:
        """Get user's wallet from database"""
        return UserSimulatedWallet.query.filter_by(user_id=self.user_id).first()

    def get_balance(self) -> float:
        """Get available balance"""
        wallet = self._get_wallet()
        return wallet.balance if wallet else 0.0

    def get_total_balance(self) -> float:
        """Get total balance (available + locked)"""
        wallet = self._get_wallet()
        if wallet:
            return wallet.balance + wallet.locked_margin
        return 0.0

    def get_locked_margin(self) -> float:
        """Get locked margin in positions"""
        wallet = self._get_wallet()
        return wallet.locked_margin if wallet else 0.0

    def get_balance_summary(self) -> Dict:
        """Get balance summary"""
        wallet = self._get_wallet()
        if not wallet:
            return {
                'total_balance': 0,
                'available_balance': 0,
                'used_margin': 0,
                'total_pnl': 0,
                'pnl_percent': 0,
                'initial_balance': 0,
                'position_count': 0,
                'trade_count': 0
            }

        total = wallet.balance + wallet.locked_margin
        initial = wallet.initial_balance
        positions = UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            is_open=True
        ).count()
        trades = UserTradeHistory.query.filter_by(wallet_id=wallet.id).count()

        return {
            'total_balance': total,
            'available_balance': wallet.balance,
            'used_margin': wallet.locked_margin,
            'total_pnl': wallet.total_pnl,
            'pnl_percent': ((total - initial) / initial * 100) if initial > 0 else 0,
            'initial_balance': initial,
            'position_count': positions,
            'trade_count': trades
        }

    def open_position(self, position_id: str, pair: str, side: str,
                     entry_price: float, size: float, margin: float,
                     leverage: int, stop_loss: float, take_profit: float) -> bool:
        """
        Open a simulated position for this user.

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
        wallet = self._get_wallet()
        if not wallet:
            logger.error(f"No wallet found for user {self.user_id}")
            return False

        if wallet.balance < margin:
            logger.warning(f"User {self.user_id}: Insufficient balance: {wallet.balance:.2f} < {margin:.2f}")
            return False

        try:
            # Lock margin
            wallet.balance -= margin
            wallet.locked_margin += margin

            # Create position
            position = UserSimulatedPosition(
                wallet_id=wallet.id,
                position_id=position_id,
                pair=pair,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=entry_price,
                leverage=leverage,
                margin=margin,
                take_profit=take_profit,
                stop_loss=stop_loss,
                pnl=0.0,
                pnl_percent=0.0,
                is_open=True
            )
            db.session.add(position)
            db.session.commit()

            logger.info(
                f"User {self.user_id}: Opened simulated {side.upper()} position:\n"
                f"  Pair: {pair}\n"
                f"  Entry: ${entry_price:.2f}\n"
                f"  Size: {size:.6f}\n"
                f"  Margin: ${margin:.2f}\n"
                f"  Leverage: {leverage}x\n"
                f"  Available Balance: ${wallet.balance:.2f}"
            )
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error opening position for user {self.user_id}: {e}")
            return False

    def update_position_price(self, position_id: str, current_price: float):
        """Update position with current price and calculate P&L"""
        wallet = self._get_wallet()
        if not wallet:
            return

        position = UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            position_id=position_id,
            is_open=True
        ).first()

        if not position:
            return

        position.current_price = current_price

        # Calculate P&L
        if position.side == 'long':
            pnl = (current_price - position.entry_price) * position.size
        else:  # short
            pnl = (position.entry_price - current_price) * position.size

        position.pnl = pnl
        position.pnl_percent = (pnl / position.margin) * 100 if position.margin > 0 else 0

        db.session.commit()

    def close_position(self, position_id: str, close_price: float, reason: str = "") -> Optional[Dict]:
        """
        Close a simulated position.

        Args:
            position_id: Position ID
            close_price: Closing price
            reason: Reason for closing

        Returns:
            Position result dict
        """
        wallet = self._get_wallet()
        if not wallet:
            logger.warning(f"No wallet found for user {self.user_id}")
            return None

        position = UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            position_id=position_id,
            is_open=True
        ).first()

        if not position:
            logger.warning(f"Position {position_id} not found for user {self.user_id}")
            return None

        try:
            # Calculate final P&L
            if position.side == 'long':
                pnl = (close_price - position.entry_price) * position.size
            else:  # short
                pnl = (position.entry_price - close_price) * position.size

            pnl_percent = (pnl / position.margin) * 100 if position.margin > 0 else 0

            # Release margin + P&L
            wallet.locked_margin -= position.margin
            wallet.balance += position.margin + pnl
            wallet.total_pnl += pnl
            wallet.total_trades += 1

            if pnl > 0:
                wallet.winning_trades += 1
            else:
                wallet.losing_trades += 1

            # Record trade history
            trade_record = UserTradeHistory(
                wallet_id=wallet.id,
                pair=position.pair,
                side=position.side,
                size=position.size,
                entry_price=position.entry_price,
                exit_price=close_price,
                leverage=position.leverage,
                pnl=pnl,
                pnl_percent=pnl_percent,
                close_reason=reason,
                opened_at=position.opened_at,
                closed_at=datetime.utcnow()
            )
            db.session.add(trade_record)

            # Mark position as closed
            position.is_open = False
            position.closed_at = datetime.utcnow()
            position.current_price = close_price
            position.pnl = pnl
            position.pnl_percent = pnl_percent

            db.session.commit()

            result = {
                'position_id': position_id,
                'pair': position.pair,
                'side': position.side,
                'entry_price': position.entry_price,
                'close_price': close_price,
                'size': position.size,
                'final_pnl': pnl,
                'pnl_percent': pnl_percent,
                'close_reason': reason
            }

            logger.info(
                f"User {self.user_id}: Closed simulated {position.side.upper()} position:\n"
                f"  Pair: {position.pair}\n"
                f"  Entry: ${position.entry_price:.2f}\n"
                f"  Exit: ${close_price:.2f}\n"
                f"  P&L: ${pnl:.2f} ({pnl_percent:.2f}%)\n"
                f"  Reason: {reason}\n"
                f"  Available Balance: ${wallet.balance:.2f}\n"
                f"  Total P&L: ${wallet.total_pnl:.2f}"
            )

            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error closing position for user {self.user_id}: {e}")
            return None

    def get_position(self, position_id: str) -> Optional[Dict]:
        """Get position by ID"""
        wallet = self._get_wallet()
        if not wallet:
            return None

        position = UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            position_id=position_id,
            is_open=True
        ).first()

        if not position:
            return None

        return self._position_to_dict(position)

    def get_all_positions(self) -> List[Dict]:
        """Get all open positions for this user"""
        wallet = self._get_wallet()
        if not wallet:
            return []

        positions = UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            is_open=True
        ).all()

        return [self._position_to_dict(p) for p in positions]

    def _position_to_dict(self, position: UserSimulatedPosition) -> Dict:
        """Convert position model to dictionary"""
        return {
            'position_id': position.position_id,
            'pair': position.pair,
            'side': position.side,
            'size': position.size,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'leverage': position.leverage,
            'margin': position.margin,
            'take_profit': position.take_profit,
            'stop_loss': position.stop_loss,
            'pnl': position.pnl,
            'pnl_percent': position.pnl_percent,
            'opened_at': position.opened_at.isoformat() if position.opened_at else '',
            'status': 'open' if position.is_open else 'closed'
        }

    def has_position_for_pair(self, pair: str) -> bool:
        """Check if there's an open position for pair"""
        wallet = self._get_wallet()
        if not wallet:
            return False

        return UserSimulatedPosition.query.filter_by(
            wallet_id=wallet.id,
            pair=pair,
            is_open=True
        ).count() > 0

    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """Get recent trade history"""
        wallet = self._get_wallet()
        if not wallet:
            return []

        trades = UserTradeHistory.query.filter_by(
            wallet_id=wallet.id
        ).order_by(UserTradeHistory.closed_at.desc()).limit(limit).all()

        return [{
            'pair': t.pair,
            'side': t.side,
            'size': t.size,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'leverage': t.leverage,
            'pnl': t.pnl,
            'pnl_percent': t.pnl_percent,
            'close_reason': t.close_reason,
            'opened_at': t.opened_at.isoformat() if t.opened_at else '',
            'closed_at': t.closed_at.isoformat() if t.closed_at else ''
        } for t in trades]

    def get_statistics(self) -> Dict:
        """Get trading statistics for this user"""
        wallet = self._get_wallet()
        if not wallet:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'total_pnl': 0,
                'pnl_percent': 0
            }

        # Get all closed trades
        trades = UserTradeHistory.query.filter_by(wallet_id=wallet.id).all()

        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'total_pnl': wallet.total_pnl,
                'pnl_percent': ((self.get_total_balance() - wallet.initial_balance) / wallet.initial_balance * 100) if wallet.initial_balance > 0 else 0
            }

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades) * 100) if trades else 0,
            'avg_win': sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'avg_loss': sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            'largest_win': max((t.pnl for t in winning_trades), default=0),
            'largest_loss': min((t.pnl for t in losing_trades), default=0),
            'total_pnl': wallet.total_pnl,
            'pnl_percent': ((self.get_total_balance() - wallet.initial_balance) / wallet.initial_balance * 100) if wallet.initial_balance > 0 else 0
        }

    def reset(self, initial_balance: float = None):
        """Reset wallet to initial state"""
        wallet = self._get_wallet()
        if not wallet:
            return

        if initial_balance is None:
            initial_balance = wallet.initial_balance

        try:
            # Delete all positions
            UserSimulatedPosition.query.filter_by(wallet_id=wallet.id).delete()
            # Delete all trade history
            UserTradeHistory.query.filter_by(wallet_id=wallet.id).delete()

            # Reset wallet
            wallet.balance = initial_balance
            wallet.initial_balance = initial_balance
            wallet.locked_margin = 0.0
            wallet.total_pnl = 0.0
            wallet.total_trades = 0
            wallet.winning_trades = 0
            wallet.losing_trades = 0

            db.session.commit()
            logger.info(f"User {self.user_id}: Reset simulated wallet to ${initial_balance:.2f}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting wallet for user {self.user_id}: {e}")


# Cache of user wallet managers
_user_wallet_managers: Dict[int, UserWalletManager] = {}


def get_user_wallet_manager(user_id: int = None) -> UserWalletManager:
    """
    Get or create a wallet manager for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id

    Returns:
        UserWalletManager instance for the user
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("No user ID provided and no authenticated user")
        user_id = current_user.id

    if user_id not in _user_wallet_managers:
        _user_wallet_managers[user_id] = UserWalletManager(user_id)

    return _user_wallet_managers[user_id]


def clear_user_wallet_cache(user_id: int = None):
    """Clear cached wallet manager(s)"""
    global _user_wallet_managers
    if user_id:
        _user_wallet_managers.pop(user_id, None)
    else:
        _user_wallet_managers.clear()

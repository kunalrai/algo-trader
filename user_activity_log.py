"""
Per-User Activity Log
Provides user-isolated activity logging using database storage
"""

import time
from typing import Dict, List, Optional
from datetime import datetime
import logging

from flask_login import current_user
from models import db

logger = logging.getLogger(__name__)


class UserActivity(db.Model):
    """Database model for per-user activity log entries"""
    __tablename__ = 'user_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Activity data
    timestamp = db.Column(db.Float, nullable=False, index=True)
    time_formatted = db.Column(db.String(20), nullable=False)
    action_type = db.Column(db.String(50), nullable=False, index=True)

    # Activity details (JSON string)
    details_json = db.Column(db.Text, nullable=True)

    # Common fields for quick access
    pair = db.Column(db.String(20), nullable=True, index=True)
    side = db.Column(db.String(10), nullable=True)
    price = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))

    @property
    def details(self) -> dict:
        """Get details as dict"""
        import json
        try:
            return json.loads(self.details_json) if self.details_json else {}
        except:
            return {}

    @details.setter
    def details(self, value: dict):
        """Set details from dict"""
        import json
        self.details_json = json.dumps(value) if value else '{}'

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        result = {
            'id': self.id,
            'timestamp': self.timestamp,
            'time_formatted': self.time_formatted,
            'action_type': self.action_type,
            'pair': self.pair,
            'side': self.side,
            'price': self.price,
            'pnl': self.pnl
        }
        # Merge in details
        result.update(self.details)
        return result


class UserActivityLog:
    """
    Per-user activity log using database storage.
    Each user has their own isolated activity history.
    """

    def __init__(self, user_id: int, max_entries: int = 500):
        """
        Initialize activity log for a specific user.

        Args:
            user_id: The user's database ID
            max_entries: Maximum entries to keep per user (older entries are pruned)
        """
        self.user_id = user_id
        self.max_entries = max_entries

    def _prune_old_entries(self):
        """Remove old entries if we exceed max_entries"""
        count = UserActivity.query.filter_by(user_id=self.user_id).count()
        if count > self.max_entries:
            # Get IDs of oldest entries to delete
            old_entries = UserActivity.query.filter_by(
                user_id=self.user_id
            ).order_by(UserActivity.timestamp.asc()).limit(count - self.max_entries).all()

            for entry in old_entries:
                db.session.delete(entry)

            db.session.commit()

    def log_action(self, action_type: str, details: Dict):
        """
        Log a bot action for this user.

        Args:
            action_type: Type of action (scan, signal, position, decision, etc.)
            details: Dictionary with action details
        """
        try:
            entry = UserActivity(
                user_id=self.user_id,
                timestamp=time.time(),
                time_formatted=datetime.now().strftime('%H:%M:%S'),
                action_type=action_type,
                pair=details.get('pair'),
                side=details.get('side'),
                price=details.get('price') or details.get('entry_price'),
                pnl=details.get('pnl'),
                details=details
            )
            db.session.add(entry)
            db.session.commit()

            # Periodically prune old entries
            if UserActivity.query.filter_by(user_id=self.user_id).count() > self.max_entries + 50:
                self._prune_old_entries()

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging activity for user {self.user_id}: {e}")

    def log_market_scan(self, pair: str, timeframe: str, indicators: Dict):
        """Log market data analysis"""
        self.log_action('market_scan', {
            'pair': pair,
            'timeframe': timeframe,
            'price': indicators.get('price', 0),
            'ema_9': indicators.get('ema_9', 0),
            'ema_21': indicators.get('ema_21', 0),
            'macd': indicators.get('macd', 0),
            'macd_signal': indicators.get('macd_signal', 0),
            'rsi': indicators.get('rsi', 0),
            'trend': indicators.get('trend', 'neutral')
        })

    def log_signal_analysis(self, pair: str, action: str, strength: float, reasons: List[str]):
        """Log signal generation and reasoning"""
        self.log_action('signal_analysis', {
            'pair': pair,
            'signal': action,
            'strength': strength,
            'reasons': reasons,
            'threshold': 0.7
        })

    def log_position_decision(self, pair: str, decision: str, reason: str, details: Dict = None):
        """Log position-related decisions"""
        self.log_action('position_decision', {
            'pair': pair,
            'decision': decision,
            'reason': reason,
            'details': details or {}
        })

    def log_position_opened(self, pair: str, side: str, entry_price: float, size: float,
                           tp: float, sl: float, margin: float):
        """Log position opening"""
        self.log_action('position_opened', {
            'pair': pair,
            'side': side,
            'entry_price': entry_price,
            'size': size,
            'take_profit': tp,
            'stop_loss': sl,
            'margin': margin
        })

    def log_position_closed(self, pair: str, side: str, entry_price: float,
                           exit_price: float, pnl: float, reason: str):
        """Log position closing"""
        pnl_percent = ((exit_price - entry_price) / entry_price * 100) if side == 'long' else ((entry_price - exit_price) / entry_price * 100)
        self.log_action('position_closed', {
            'pair': pair,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason
        })

    def log_risk_check(self, check_type: str, status: str, details: str):
        """Log risk management checks"""
        self.log_action('risk_check', {
            'check_type': check_type,
            'status': status,
            'details': details
        })

    def log_error(self, error_type: str, message: str):
        """Log errors"""
        self.log_action('error', {
            'error_type': error_type,
            'message': message
        })

    def log_strategy_decision(self, pair: str, strategy_name: str, action: str,
                               strength: float, reasons: List[str], indicators: Dict = None,
                               metadata: Dict = None):
        """Log detailed strategy decision for transparency"""
        self.log_action('strategy_decision', {
            'pair': pair,
            'strategy_name': strategy_name,
            'action': action,
            'strength': round(strength, 4),
            'reasons': reasons,
            'indicators': indicators or {},
            'metadata': metadata or {},
            'decision_summary': f"{strategy_name} -> {action.upper()} ({strength:.1%} strength)"
        })

    def log_decision_flow(self, pair: str, step: str, result: str, details: Dict = None):
        """Log individual steps in the decision flow for debugging"""
        self.log_action('decision_flow', {
            'pair': pair,
            'step': step,
            'result': result,
            'details': details or {}
        })

    def get_recent_activities(self, limit: int = 50, filter_type: str = None) -> List[Dict]:
        """
        Get recent activities for this user.

        Args:
            limit: Maximum number of entries to return
            filter_type: Optional filter by action_type

        Returns:
            List of activity entries (most recent first)
        """
        query = UserActivity.query.filter_by(user_id=self.user_id)

        if filter_type:
            query = query.filter_by(action_type=filter_type)

        activities = query.order_by(UserActivity.timestamp.desc()).limit(limit).all()

        return [a.to_dict() for a in activities]

    def get_signal_history(self, pair: str = None, limit: int = 20) -> List[Dict]:
        """Get signal analysis history"""
        query = UserActivity.query.filter_by(
            user_id=self.user_id,
            action_type='signal_analysis'
        )

        if pair:
            query = query.filter_by(pair=pair)

        signals = query.order_by(UserActivity.timestamp.desc()).limit(limit).all()

        return [s.to_dict() for s in signals]

    def get_position_history(self, limit: int = 20) -> List[Dict]:
        """Get position open/close history"""
        activities = UserActivity.query.filter(
            UserActivity.user_id == self.user_id,
            UserActivity.action_type.in_(['position_opened', 'position_closed'])
        ).order_by(UserActivity.timestamp.desc()).limit(limit).all()

        return [a.to_dict() for a in activities]

    def clear_old_entries(self, max_age_hours: int = 24):
        """Clear entries older than specified hours"""
        cutoff_time = time.time() - (max_age_hours * 3600)

        UserActivity.query.filter(
            UserActivity.user_id == self.user_id,
            UserActivity.timestamp < cutoff_time
        ).delete()

        db.session.commit()

    def get_statistics(self) -> Dict:
        """Get activity statistics for this user"""
        from sqlalchemy import func

        total = UserActivity.query.filter_by(user_id=self.user_id).count()

        # Count by type
        type_counts = db.session.query(
            UserActivity.action_type,
            func.count(UserActivity.id)
        ).filter_by(user_id=self.user_id).group_by(UserActivity.action_type).all()

        by_type = {t: c for t, c in type_counts}

        # Get oldest and newest
        oldest = UserActivity.query.filter_by(
            user_id=self.user_id
        ).order_by(UserActivity.timestamp.asc()).first()

        newest = UserActivity.query.filter_by(
            user_id=self.user_id
        ).order_by(UserActivity.timestamp.desc()).first()

        return {
            'total_activities': total,
            'by_type': by_type,
            'oldest_timestamp': oldest.timestamp if oldest else None,
            'newest_timestamp': newest.timestamp if newest else None
        }


# Cache of user activity logs
_user_activity_logs: Dict[int, UserActivityLog] = {}


def get_user_activity_log(user_id: int = None) -> UserActivityLog:
    """
    Get or create an activity log for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id

    Returns:
        UserActivityLog instance for the user
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("No user ID provided and no authenticated user")
        user_id = current_user.id

    if user_id not in _user_activity_logs:
        _user_activity_logs[user_id] = UserActivityLog(user_id)

    return _user_activity_logs[user_id]


def clear_user_activity_cache(user_id: int = None):
    """Clear cached activity log(s)"""
    global _user_activity_logs
    if user_id:
        _user_activity_logs.pop(user_id, None)
    else:
        _user_activity_logs.clear()

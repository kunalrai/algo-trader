"""
Per-User Bot Status Tracker
Provides user-isolated bot status tracking using database storage
"""

import time
from typing import Dict, Optional
from datetime import datetime
import logging

from flask_login import current_user
from models import db

logger = logging.getLogger(__name__)


class UserBotStatus(db.Model):
    """Database model for per-user bot status"""
    __tablename__ = 'user_bot_status'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # Bot state
    bot_running = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.Float, nullable=True)
    last_cycle_time = db.Column(db.Float, nullable=True)
    total_cycles = db.Column(db.Integer, default=0)

    # Current action
    current_action = db.Column(db.String(100), default='Stopped')
    action_details = db.Column(db.String(500), default='Bot not running')

    # Timing
    last_decision_time = db.Column(db.Float, nullable=True)
    scan_interval = db.Column(db.Integer, default=60)
    next_scan_at = db.Column(db.Float, nullable=True)

    # Pairs being monitored (JSON string)
    pairs_monitored_json = db.Column(db.Text, default='[]')

    # Active strategy
    active_strategy = db.Column(db.String(100), default='combined')
    active_strategy_name = db.Column(db.String(200), default='Combined Strategy')

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('bot_status', uselist=False))

    @property
    def pairs_monitored(self) -> list:
        """Get pairs monitored as list"""
        import json
        try:
            return json.loads(self.pairs_monitored_json) if self.pairs_monitored_json else []
        except:
            return []

    @pairs_monitored.setter
    def pairs_monitored(self, value: list):
        """Set pairs monitored from list"""
        import json
        self.pairs_monitored_json = json.dumps(value) if value else '[]'


class UserBotStatusTracker:
    """
    Per-user bot status tracker using database storage.
    Each user has their own isolated bot status.
    """

    def __init__(self, user_id: int):
        """
        Initialize status tracker for a specific user.

        Args:
            user_id: The user's database ID
        """
        self.user_id = user_id
        self._ensure_status_exists()

    def _ensure_status_exists(self):
        """Ensure user has a bot status record, create if not exists"""
        status = UserBotStatus.query.filter_by(user_id=self.user_id).first()
        if not status:
            status = UserBotStatus(user_id=self.user_id)
            db.session.add(status)
            db.session.commit()
            logger.info(f"Created bot status record for user {self.user_id}")

    def _get_status_record(self) -> Optional[UserBotStatus]:
        """Get user's bot status from database"""
        return UserBotStatus.query.filter_by(user_id=self.user_id).first()

    def start_bot(self, scan_interval: int, pairs: list, strategy_id: str = None, strategy_name: str = None):
        """Mark bot as started for this user"""
        status = self._get_status_record()
        if status:
            status.bot_running = True
            status.start_time = time.time()
            status.total_cycles = 0
            status.scan_interval = scan_interval
            status.pairs_monitored = pairs
            status.current_action = 'Starting'
            status.action_details = 'Initializing trading bot...'
            if strategy_id:
                status.active_strategy = strategy_id
            if strategy_name:
                status.active_strategy_name = strategy_name
            db.session.commit()

    def stop_bot(self):
        """Mark bot as stopped for this user"""
        status = self._get_status_record()
        if status:
            status.bot_running = False
            status.current_action = 'Stopped'
            status.action_details = 'Bot stopped by user'
            db.session.commit()

    def update_cycle(self, cycle_number: int):
        """Update cycle information"""
        status = self._get_status_record()
        if status:
            status.total_cycles = cycle_number
            status.last_cycle_time = time.time()
            status.next_scan_at = time.time() + status.scan_interval
            db.session.commit()

    def update_action(self, action: str, details: str):
        """Update current bot action"""
        status = self._get_status_record()
        if status:
            status.current_action = action
            status.action_details = details
            status.last_decision_time = time.time()
            db.session.commit()

    def update_strategy(self, strategy_id: str, strategy_name: str):
        """Update active strategy"""
        status = self._get_status_record()
        if status:
            status.active_strategy = strategy_id
            status.active_strategy_name = strategy_name
            db.session.commit()

    def get_status(self) -> Dict:
        """
        Get current bot status with calculated fields.

        Returns:
            Dict with bot status including uptime, next scan countdown, etc.
        """
        status = self._get_status_record()
        if not status:
            return {
                'bot_running': False,
                'start_time': None,
                'last_cycle_time': None,
                'total_cycles': 0,
                'current_action': 'Stopped',
                'action_details': 'Bot not running',
                'uptime_seconds': 0,
                'uptime_formatted': '0s',
                'seconds_until_next_scan': None,
                'next_scan_countdown': 'N/A'
            }

        result = {
            'bot_running': status.bot_running,
            'start_time': status.start_time,
            'last_cycle_time': status.last_cycle_time,
            'total_cycles': status.total_cycles,
            'current_action': status.current_action,
            'action_details': status.action_details,
            'last_decision_time': status.last_decision_time,
            'scan_interval': status.scan_interval,
            'pairs_monitored': status.pairs_monitored,
            'next_scan_at': status.next_scan_at,
            'active_strategy': status.active_strategy,
            'active_strategy_name': status.active_strategy_name
        }

        # Calculate uptime
        if status.bot_running and status.start_time:
            uptime_seconds = time.time() - status.start_time
            result['uptime_seconds'] = int(uptime_seconds)
            result['uptime_formatted'] = self._format_duration(uptime_seconds)
        else:
            result['uptime_seconds'] = 0
            result['uptime_formatted'] = '0s'

        # Calculate time since last cycle
        if status.last_cycle_time:
            time_since_cycle = time.time() - status.last_cycle_time
            result['seconds_since_last_cycle'] = int(time_since_cycle)
        else:
            result['seconds_since_last_cycle'] = 0

        # Calculate countdown to next scan
        if status.next_scan_at:
            time_until_scan = status.next_scan_at - time.time()
            if time_until_scan > 0:
                result['seconds_until_next_scan'] = int(time_until_scan)
                result['next_scan_countdown'] = self._format_countdown(time_until_scan)
            else:
                result['seconds_until_next_scan'] = 0
                result['next_scan_countdown'] = 'Scanning now...'
        else:
            result['seconds_until_next_scan'] = None
            result['next_scan_countdown'] = 'N/A'

        # Format timestamps
        if status.last_cycle_time:
            result['last_cycle_formatted'] = datetime.fromtimestamp(
                status.last_cycle_time
            ).strftime('%H:%M:%S')
        else:
            result['last_cycle_formatted'] = 'Never'

        if status.last_decision_time:
            result['last_decision_formatted'] = datetime.fromtimestamp(
                status.last_decision_time
            ).strftime('%H:%M:%S')
        else:
            result['last_decision_formatted'] = 'N/A'

        return result

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        seconds = int(seconds)

        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _format_countdown(self, seconds: float) -> str:
        """Format countdown timer"""
        seconds = int(seconds)
        if seconds <= 0:
            return "Now"
        elif seconds < 60:
            return f"{seconds}s"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"


# Cache of user bot status trackers
_user_status_trackers: Dict[int, UserBotStatusTracker] = {}


def get_user_bot_status_tracker(user_id: int = None) -> UserBotStatusTracker:
    """
    Get or create a bot status tracker for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id

    Returns:
        UserBotStatusTracker instance for the user
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("No user ID provided and no authenticated user")
        user_id = current_user.id

    if user_id not in _user_status_trackers:
        _user_status_trackers[user_id] = UserBotStatusTracker(user_id)

    return _user_status_trackers[user_id]


def clear_user_status_cache(user_id: int = None):
    """Clear cached status tracker(s)"""
    global _user_status_trackers
    if user_id:
        _user_status_trackers.pop(user_id, None)
    else:
        _user_status_trackers.clear()

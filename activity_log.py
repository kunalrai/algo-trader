"""
Activity Log System
Tracks all bot actions and decision-making process for real-time display
"""

import json
import time
import os
from typing import Dict, List
from datetime import datetime
from collections import deque


class ActivityLog:
    """Track and store bot activity for dashboard display"""

    def __init__(self, log_file: str = 'activity_log.json', max_entries: int = 100):
        """
        Initialize activity log

        Args:
            log_file: Path to JSON file for storing activity
            max_entries: Maximum number of entries to keep in memory
        """
        self.log_file = log_file
        self.max_entries = max_entries
        self.activities = deque(maxlen=max_entries)
        self._load()

    def _load(self):
        """Load existing activity log"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.activities = deque(data, maxlen=self.max_entries)
            except Exception:
                pass

    def _save(self):
        """Save activity log to disk"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(list(self.activities), f, indent=2)
        except Exception as e:
            print(f"Error saving activity log: {e}")

    def log_action(self, action_type: str, details: Dict):
        """
        Log a bot action

        Args:
            action_type: Type of action (scan, signal, position, decision, etc.)
            details: Dictionary with action details
        """
        entry = {
            'timestamp': time.time(),
            'time_formatted': datetime.now().strftime('%H:%M:%S'),
            'action_type': action_type,
            **details
        }

        self.activities.append(entry)
        self._save()

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
        self.log_action('position_closed', {
            'pair': pair,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': ((exit_price - entry_price) / entry_price * 100) if side == 'long' else ((entry_price - exit_price) / entry_price * 100),
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

    def get_recent_activities(self, limit: int = 50, filter_type: str = None) -> List[Dict]:
        """
        Get recent activities

        Args:
            limit: Maximum number of entries to return
            filter_type: Optional filter by action_type

        Returns:
            List of activity entries
        """
        activities_list = list(self.activities)

        if filter_type:
            activities_list = [a for a in activities_list if a.get('action_type') == filter_type]

        # Return most recent first
        return list(reversed(activities_list[-limit:]))

    def get_signal_history(self, pair: str = None, limit: int = 20) -> List[Dict]:
        """Get signal analysis history"""
        signals = [a for a in self.activities if a.get('action_type') == 'signal_analysis']

        if pair:
            signals = [s for s in signals if s.get('pair') == pair]

        return list(reversed(signals[-limit:]))

    def get_position_history(self, limit: int = 20) -> List[Dict]:
        """Get position open/close history"""
        positions = [a for a in self.activities if a.get('action_type') in ['position_opened', 'position_closed']]
        return list(reversed(positions[-limit:]))

    def clear_old_entries(self, max_age_hours: int = 24):
        """Clear entries older than specified hours"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        self.activities = deque(
            [a for a in self.activities if a.get('timestamp', 0) > cutoff_time],
            maxlen=self.max_entries
        )
        self._save()

    def get_statistics(self) -> Dict:
        """Get activity statistics"""
        total = len(self.activities)

        by_type = {}
        for activity in self.activities:
            action_type = activity.get('action_type', 'unknown')
            by_type[action_type] = by_type.get(action_type, 0) + 1

        return {
            'total_activities': total,
            'by_type': by_type,
            'oldest_timestamp': self.activities[0].get('timestamp') if self.activities else None,
            'newest_timestamp': self.activities[-1].get('timestamp') if self.activities else None
        }


# Global instance
_activity_log = None


def get_activity_log() -> ActivityLog:
    """Get or create global activity log instance"""
    global _activity_log
    if _activity_log is None:
        _activity_log = ActivityLog()
    return _activity_log

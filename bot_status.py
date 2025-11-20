"""
Bot Status Tracker
Shared state between trading bot and dashboard for real-time status updates
"""

import json
import time
import os
from typing import Dict, Optional
from datetime import datetime


class BotStatusTracker:
    """Track and persist bot runtime status"""

    def __init__(self, status_file: str = 'bot_status.json'):
        """
        Initialize bot status tracker

        Args:
            status_file: Path to JSON file for storing status
        """
        self.status_file = status_file
        self.data = self._load_or_initialize()

    def _load_or_initialize(self) -> Dict:
        """Load existing status or create new"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default status
        return {
            'bot_running': False,
            'start_time': None,
            'last_cycle_time': None,
            'total_cycles': 0,
            'current_action': 'Stopped',
            'action_details': 'Bot not running',
            'last_decision_time': None,
            'scan_interval': 60,
            'pairs_monitored': [],
            'next_scan_at': None
        }

    def _save(self):
        """Save status to disk"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving bot status: {e}")

    def start_bot(self, scan_interval: int, pairs: list):
        """Mark bot as started"""
        self.data['bot_running'] = True
        self.data['start_time'] = time.time()
        self.data['total_cycles'] = 0
        self.data['scan_interval'] = scan_interval
        self.data['pairs_monitored'] = pairs
        self.data['current_action'] = 'Starting'
        self.data['action_details'] = 'Initializing trading bot...'
        self._save()

    def stop_bot(self):
        """Mark bot as stopped"""
        self.data['bot_running'] = False
        self.data['current_action'] = 'Stopped'
        self.data['action_details'] = 'Bot stopped by user'
        self._save()

    def update_cycle(self, cycle_number: int):
        """Update cycle information"""
        self.data['total_cycles'] = cycle_number
        self.data['last_cycle_time'] = time.time()
        self.data['next_scan_at'] = time.time() + self.data['scan_interval']
        self._save()

    def update_action(self, action: str, details: str):
        """Update current bot action"""
        self.data['current_action'] = action
        self.data['action_details'] = details
        self.data['last_decision_time'] = time.time()
        self._save()

    def get_status(self) -> Dict:
        """
        Get current bot status with calculated fields

        Returns:
            Dict with bot status including uptime, next scan countdown, etc.
        """
        status = self.data.copy()

        # Calculate uptime
        if status['bot_running'] and status['start_time']:
            uptime_seconds = time.time() - status['start_time']
            status['uptime_seconds'] = int(uptime_seconds)
            status['uptime_formatted'] = self._format_duration(uptime_seconds)
        else:
            status['uptime_seconds'] = 0
            status['uptime_formatted'] = '0s'

        # Calculate time since last cycle
        if status['last_cycle_time']:
            time_since_cycle = time.time() - status['last_cycle_time']
            status['seconds_since_last_cycle'] = int(time_since_cycle)
        else:
            status['seconds_since_last_cycle'] = 0

        # Calculate countdown to next scan
        if status['next_scan_at']:
            time_until_scan = status['next_scan_at'] - time.time()
            if time_until_scan > 0:
                status['seconds_until_next_scan'] = int(time_until_scan)
                status['next_scan_countdown'] = self._format_countdown(time_until_scan)
            else:
                status['seconds_until_next_scan'] = 0
                status['next_scan_countdown'] = 'Scanning now...'
        else:
            status['seconds_until_next_scan'] = None
            status['next_scan_countdown'] = 'N/A'

        # Format timestamps
        if status['last_cycle_time']:
            status['last_cycle_formatted'] = datetime.fromtimestamp(
                status['last_cycle_time']
            ).strftime('%H:%M:%S')
        else:
            status['last_cycle_formatted'] = 'Never'

        if status['last_decision_time']:
            status['last_decision_formatted'] = datetime.fromtimestamp(
                status['last_decision_time']
            ).strftime('%H:%M:%S')
        else:
            status['last_decision_formatted'] = 'N/A'

        return status

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


# Global instance (singleton pattern)
_bot_status_tracker = None


def get_bot_status_tracker() -> BotStatusTracker:
    """Get or create global bot status tracker instance"""
    global _bot_status_tracker
    if _bot_status_tracker is None:
        _bot_status_tracker = BotStatusTracker()
    return _bot_status_tracker

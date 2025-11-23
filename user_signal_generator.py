"""
Per-User Signal Generator Module
Provides user-isolated signal generation with per-user data fetching
"""

from typing import Dict
import logging
from flask_login import current_user
from signal_generator import SignalGenerator
from user_data_fetcher import get_user_data_fetcher, UserDataFetcher
import config

logger = logging.getLogger(__name__)


class UserSignalGenerator:
    """
    User-isolated signal generator.
    Each user has their own signal generator with isolated data fetching.
    """

    def __init__(self, user_id: int, data_fetcher: UserDataFetcher,
                 indicator_config: Dict, rsi_config: Dict,
                 use_strategy_system: bool = False):
        """
        Initialize signal generator for a specific user.

        Args:
            user_id: The user's database ID
            data_fetcher: User-specific data fetcher
            indicator_config: Indicator configuration
            rsi_config: RSI configuration
            use_strategy_system: Whether to use the strategy system
        """
        self.user_id = user_id
        self._signal_generator = SignalGenerator(
            data_fetcher=data_fetcher,
            indicator_config=indicator_config,
            rsi_config=rsi_config,
            use_strategy_system=use_strategy_system
        )
        logger.debug(f"Created UserSignalGenerator for user {user_id}")

    def generate_signal(self, pair: str, timeframes: Dict[str, str]) -> Dict:
        """
        Generate trading signal for a pair using user-isolated data fetching.

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            timeframes: Dict of timeframe names and intervals

        Returns:
            Signal dict with action, strength, analyses, etc.
        """
        return self._signal_generator.generate_signal(pair, timeframes)

    def analyze_timeframe(self, df, timeframe_name: str) -> Dict:
        """Analyze a single timeframe"""
        return self._signal_generator.analyze_timeframe(df, timeframe_name)


# Cache of user signal generators
_user_signal_generators: Dict[int, UserSignalGenerator] = {}


def get_user_signal_generator(user_id: int = None,
                               data_fetcher: UserDataFetcher = None,
                               indicator_config: Dict = None,
                               rsi_config: Dict = None,
                               use_strategy_system: bool = None) -> UserSignalGenerator:
    """
    Get or create a signal generator for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id
        data_fetcher: User-specific data fetcher. If None, creates one
        indicator_config: Indicator config. If None, uses default config
        rsi_config: RSI config. If None, uses default config
        use_strategy_system: Whether to use strategy system. If None, uses config default

    Returns:
        UserSignalGenerator instance for the user
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("No user ID provided and no authenticated user")
        user_id = current_user.id

    # Check if we need to create a new instance
    if user_id not in _user_signal_generators:
        if data_fetcher is None:
            data_fetcher = get_user_data_fetcher(user_id)

        if indicator_config is None:
            indicator_config = config.INDICATORS

        if rsi_config is None:
            rsi_config = config.INDICATORS['RSI']

        if use_strategy_system is None:
            use_strategy_system = config.STRATEGY_CONFIG.get('enabled', False)

        _user_signal_generators[user_id] = UserSignalGenerator(
            user_id=user_id,
            data_fetcher=data_fetcher,
            indicator_config=indicator_config,
            rsi_config=rsi_config,
            use_strategy_system=use_strategy_system
        )

    return _user_signal_generators[user_id]


def clear_user_signal_generator_cache(user_id: int = None):
    """Clear cached signal generator(s)"""
    global _user_signal_generators
    if user_id:
        _user_signal_generators.pop(user_id, None)
    else:
        _user_signal_generators.clear()

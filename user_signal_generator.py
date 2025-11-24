"""
Per-User Signal Generator Module
Provides user-isolated signal generation with per-user data fetching and strategy selection
"""

from typing import Dict, Optional
import logging
from flask_login import current_user
from signal_generator import SignalGenerator
from user_data_fetcher import get_user_data_fetcher, UserDataFetcher
import config

logger = logging.getLogger(__name__)


class UserSignalGenerator:
    """
    User-isolated signal generator.
    Each user has their own signal generator with isolated data fetching and strategy.
    """

    def __init__(self, user_id: int, data_fetcher: UserDataFetcher,
                 indicator_config: Dict, rsi_config: Dict,
                 use_strategy_system: bool = False,
                 user_strategy: str = None):
        """
        Initialize signal generator for a specific user.

        Args:
            user_id: The user's database ID
            data_fetcher: User-specific data fetcher
            indicator_config: Indicator configuration
            rsi_config: RSI configuration
            use_strategy_system: Whether to use the strategy system
            user_strategy: User's selected strategy ID
        """
        self.user_id = user_id
        self.user_strategy = user_strategy
        self._signal_generator = SignalGenerator(
            data_fetcher=data_fetcher,
            indicator_config=indicator_config,
            rsi_config=rsi_config,
            use_strategy_system=use_strategy_system
        )

        # Create a dedicated strategy manager instance for this user
        # This ensures strategy isolation between users
        if use_strategy_system and self._signal_generator.strategy_manager:
            from strategies.strategy_manager import StrategyManager
            self._user_strategy_manager = StrategyManager()
            self._signal_generator.strategy_manager = self._user_strategy_manager

            # Set the user's preferred strategy
            if user_strategy:
                self._user_strategy_manager.set_active_strategy(user_strategy)
                logger.info(f"User {user_id}: Created dedicated strategy manager with strategy '{user_strategy}'")

        logger.debug(f"Created UserSignalGenerator for user {user_id} with strategy '{user_strategy}'")

    def generate_signal(self, pair: str, timeframes: Dict[str, str]) -> Dict:
        """
        Generate trading signal for a pair using user-isolated data fetching.
        Uses the user's dedicated strategy manager for strategy isolation.

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            timeframes: Dict of timeframe names and intervals

        Returns:
            Signal dict with action, strength, analyses, etc.
        """
        # Each user has their own strategy manager, so no need to switch strategies
        # Strategy isolation is guaranteed by the dedicated manager instance
        return self._signal_generator.generate_signal(pair, timeframes)

    def set_strategy(self, strategy_id: str) -> bool:
        """
        Update the user's active strategy.

        Args:
            strategy_id: Strategy ID to set

        Returns:
            True if successful
        """
        self.user_strategy = strategy_id
        # Use the user's dedicated strategy manager
        if hasattr(self, '_user_strategy_manager') and self._user_strategy_manager:
            success = self._user_strategy_manager.set_active_strategy(strategy_id)
            if success:
                logger.info(f"User {self.user_id}: Strategy changed to '{strategy_id}'")
            return success
        elif self._signal_generator.strategy_manager:
            return self._signal_generator.strategy_manager.set_active_strategy(strategy_id)
        return False

    def analyze_timeframe(self, df, timeframe_name: str) -> Dict:
        """Analyze a single timeframe"""
        return self._signal_generator.analyze_timeframe(df, timeframe_name)


# Cache of user signal generators
_user_signal_generators: Dict[int, UserSignalGenerator] = {}


def get_user_signal_generator(user_id: int = None,
                               data_fetcher: UserDataFetcher = None,
                               indicator_config: Dict = None,
                               rsi_config: Dict = None,
                               use_strategy_system: bool = None,
                               user_strategy: str = None) -> UserSignalGenerator:
    """
    Get or create a signal generator for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id
        data_fetcher: User-specific data fetcher. If None, creates one
        indicator_config: Indicator config. If None, uses default config
        rsi_config: RSI config. If None, uses default config
        use_strategy_system: Whether to use strategy system. If None, uses config default
        user_strategy: User's selected strategy ID. If None, loads from user profile

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

        # Load user's strategy from profile if not provided
        if user_strategy is None and use_strategy_system:
            try:
                from models import UserProfile
                profile = UserProfile.query.filter_by(user_id=user_id).first()
                if profile and profile.default_strategy:
                    user_strategy = profile.default_strategy
                else:
                    user_strategy = config.STRATEGY_CONFIG.get('active_strategy', 'combined')
            except Exception as e:
                logger.warning(f"Could not load user strategy for user {user_id}: {e}")
                user_strategy = config.STRATEGY_CONFIG.get('active_strategy', 'combined')

        _user_signal_generators[user_id] = UserSignalGenerator(
            user_id=user_id,
            data_fetcher=data_fetcher,
            indicator_config=indicator_config,
            rsi_config=rsi_config,
            use_strategy_system=use_strategy_system,
            user_strategy=user_strategy
        )

    return _user_signal_generators[user_id]


def clear_user_signal_generator_cache(user_id: int = None):
    """Clear cached signal generator(s)"""
    global _user_signal_generators
    if user_id:
        _user_signal_generators.pop(user_id, None)
    else:
        _user_signal_generators.clear()


def update_user_strategy(user_id: int, strategy_id: str) -> bool:
    """
    Update the strategy for a cached user signal generator.
    Call this when the user changes their strategy preference.

    Args:
        user_id: User ID
        strategy_id: New strategy ID

    Returns:
        True if successful
    """
    if user_id in _user_signal_generators:
        return _user_signal_generators[user_id].set_strategy(strategy_id)
    return True  # No cached generator, will be created with correct strategy on next use

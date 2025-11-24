"""
User Strategy Manager
Per-user strategy management with complete isolation between users
"""

from typing import Dict, Optional, List
import logging
from strategies.base_strategy import BaseStrategy
from strategies.ema_crossover_strategy import EMACrossoverStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.combined_strategy import CombinedStrategy
from strategies.support_resistance_strategy import SupportResistanceStrategy

logger = logging.getLogger(__name__)


class UserStrategyManager:
    """Per-user strategy manager with complete isolation between users"""

    def __init__(self, user_id: int):
        """Initialize user strategy manager

        Args:
            user_id: User ID for this strategy manager instance
        """
        self.user_id = user_id
        self._strategies: Dict[str, BaseStrategy] = {}
        self._active_strategy: Optional[BaseStrategy] = None
        self._initialized = False

        # Only log initialization once per user
        logger.debug(f"User {self.user_id}: Creating strategy manager instance")

        self._register_builtin_strategies()
        self._load_custom_strategies()
        self._initialized = True

    def _register_builtin_strategies(self):
        """Register all built-in strategies"""
        # Register all available strategies
        self.register_strategy('ema_crossover', EMACrossoverStrategy())
        self.register_strategy('macd', MACDStrategy())
        self.register_strategy('rsi', RSIStrategy())
        self.register_strategy('combined', CombinedStrategy())
        self.register_strategy('support_resistance', SupportResistanceStrategy())

        # Set default active strategy
        self.set_active_strategy('combined')

    def _load_custom_strategies(self):
        """Load all custom strategies from the custom directory"""
        try:
            from strategies.custom_strategy_loader import get_custom_strategy_loader

            loader = get_custom_strategy_loader()
            custom_strategies = loader.load_all_custom_strategies()

            for strategy_id, strategy_class in custom_strategies.items():
                try:
                    # Instantiate the strategy
                    strategy_instance = strategy_class()
                    self.register_strategy(strategy_id, strategy_instance)
                    logger.info(f"Loaded custom strategy: {strategy_id}")
                except Exception as e:
                    logger.error(f"Failed to instantiate custom strategy {strategy_id}: {e}")

        except Exception as e:
            logger.warning(f"Could not load custom strategies: {e}")

    def reload_custom_strategies(self):
        """Reload all custom strategies (useful after upload)"""
        logger.info("Reloading custom strategies...")
        self._load_custom_strategies()

    def register_strategy(self, strategy_id: str, strategy):
        """
        Register a new strategy

        Args:
            strategy_id: Unique identifier for the strategy
            strategy: Strategy instance or class
        """
        # If it's a class, instantiate it
        if isinstance(strategy, type):
            try:
                strategy = strategy()
            except Exception as e:
                logger.error(f"User {self.user_id}: Failed to instantiate strategy {strategy_id}: {e}")
                return

        if not isinstance(strategy, BaseStrategy):
            raise ValueError("Strategy must inherit from BaseStrategy")

        self._strategies[strategy_id] = strategy
        # Only log during initial setup, not for every registration
        if not self._initialized:
            logger.debug(f"User {self.user_id}: Registered strategy: {strategy_id} ({strategy.name})")

    def set_active_strategy(self, strategy_id: str, params: Dict = None) -> bool:
        """
        Set the active trading strategy

        Args:
            strategy_id: ID of strategy to activate
            params: Optional parameters to override strategy defaults

        Returns:
            True if successful, False otherwise
        """
        if strategy_id not in self._strategies:
            logger.warning(f"User {self.user_id}: Strategy '{strategy_id}' not found")
            return False

        # Get strategy class and create new instance with custom params if provided
        if params:
            strategy_class = type(self._strategies[strategy_id])
            self._active_strategy = strategy_class(params=params)
        else:
            self._active_strategy = self._strategies[strategy_id]

        # Only log when actually changing strategy, not during initialization
        if self._initialized:
            logger.info(f"User {self.user_id}: Active strategy set to: {self._active_strategy.name}")
        return True

    def get_active_strategy(self) -> Optional[BaseStrategy]:
        """
        Get the currently active strategy

        Returns:
            Active strategy instance or None
        """
        return self._active_strategy

    def get_active_strategy_id(self) -> Optional[str]:
        """
        Get the ID of the currently active strategy

        Returns:
            Strategy ID string or None
        """
        if not self._active_strategy:
            return None

        for strategy_id, strategy in self._strategies.items():
            if strategy.name == self._active_strategy.name:
                return strategy_id

        return None

    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """
        Get a specific strategy by ID

        Args:
            strategy_id: Strategy identifier

        Returns:
            Strategy instance or None
        """
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[Dict]:
        """
        Get list of all available strategies

        Returns:
            List of strategy information dictionaries
        """
        strategies = []
        for strategy_id, strategy in self._strategies.items():
            info = strategy.get_info()
            info['id'] = strategy_id
            info['is_active'] = (self._active_strategy == strategy)
            strategies.append(info)

        return strategies

    def get_active_strategy_info(self) -> Optional[Dict]:
        """
        Get information about the active strategy

        Returns:
            Strategy info dictionary or None
        """
        if not self._active_strategy:
            return None

        info = self._active_strategy.get_info()

        # Find the strategy ID
        for strategy_id, strategy in self._strategies.items():
            if strategy.name == self._active_strategy.name:
                info['id'] = strategy_id
                break

        return info

    def analyze_with_active_strategy(self, data: Dict, current_price: float) -> Optional[Dict]:
        """
        Analyze market data using the active strategy

        Args:
            data: Market data dictionary
            current_price: Current market price

        Returns:
            Signal dictionary or None if no active strategy
        """
        if not self._active_strategy:
            logger.warning(f"User {self.user_id}: No active strategy set")
            return None

        return self._active_strategy.analyze(data, current_price)

    def create_custom_strategy(self, strategy_id: str, strategy_type: str, params: Dict) -> bool:
        """
        Create and register a custom strategy instance

        Args:
            strategy_id: Unique ID for this custom strategy
            strategy_type: Base strategy type (ema_crossover, macd, rsi, combined)
            params: Custom parameters for the strategy

        Returns:
            True if successful, False otherwise
        """
        strategy_classes = {
            'ema_crossover': EMACrossoverStrategy,
            'macd': MACDStrategy,
            'rsi': RSIStrategy,
            'combined': CombinedStrategy,
            'support_resistance': SupportResistanceStrategy
        }

        if strategy_type not in strategy_classes:
            logger.warning(f"User {self.user_id}: Unknown strategy type: {strategy_type}")
            return False

        # Create new instance with custom params
        strategy_class = strategy_classes[strategy_type]
        custom_strategy = strategy_class(params=params)

        # Register it
        self.register_strategy(strategy_id, custom_strategy)
        return True


# Per-user strategy manager registry
_user_strategy_managers: Dict[int, UserStrategyManager] = {}


def get_user_strategy_manager(user_id: int) -> UserStrategyManager:
    """
    Get or create a strategy manager for a specific user.
    Each user gets their own isolated strategy manager instance.

    Args:
        user_id: User ID

    Returns:
        UserStrategyManager instance for the user
    """
    if user_id not in _user_strategy_managers:
        logger.info(f"User {user_id}: Creating new strategy manager instance")
        _user_strategy_managers[user_id] = UserStrategyManager(user_id)

    return _user_strategy_managers[user_id]


def get_strategy_manager(user_id: Optional[int] = None) -> UserStrategyManager:
    """
    Backward compatibility wrapper for get_user_strategy_manager.

    Args:
        user_id: Optional user ID. If provided, returns user-specific manager.
                 If not provided and there's only one user manager, returns that.
                 Otherwise creates a temporary manager with user_id=0 for legacy code.

    Returns:
        UserStrategyManager instance
    """
    if user_id is not None:
        return get_user_strategy_manager(user_id)

    # For legacy code that doesn't pass user_id
    # Return the first user's manager if only one exists, otherwise create a default one
    if len(_user_strategy_managers) == 1:
        return list(_user_strategy_managers.values())[0]

    # Create a default manager for user_id=0 (system/legacy)
    return get_user_strategy_manager(0)


# Backward compatibility alias
StrategyManager = UserStrategyManager

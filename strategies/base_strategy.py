"""
Base Strategy Class
All trading strategies inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""

    def __init__(self, name: str, description: str, params: Dict = None):
        """
        Initialize strategy

        Args:
            name: Strategy name
            description: Strategy description
            params: Strategy-specific parameters
        """
        self.name = name
        self.description = description
        self.params = params or {}
        self.version = "1.0.0"

    @abstractmethod
    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """
        Analyze market data and generate trading signal

        Args:
            data: Dictionary of DataFrames with keys '5m', '1h', '4h' containing OHLCV data
            current_price: Current market price

        Returns:
            Dictionary containing:
            {
                'action': 'long' | 'short' | 'flat',
                'strength': float (0.0 to 1.0),
                'confidence': float (0.0 to 1.0),
                'reasons': List[str],
                'indicators': Dict (indicator values),
                'metadata': Dict (strategy-specific data)
            }
        """
        pass

    @abstractmethod
    def get_required_timeframes(self) -> List[str]:
        """
        Get list of required timeframes for this strategy

        Returns:
            List of timeframe strings (e.g., ['5m', '1h', '4h'])
        """
        pass

    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Get list of required indicators for this strategy

        Returns:
            List of indicator names (e.g., ['ema_9', 'ema_21', 'macd', 'rsi'])
        """
        pass

    def validate_data(self, data: Dict[str, pd.DataFrame]) -> bool:
        """
        Validate that required data is present

        Args:
            data: Market data dictionary

        Returns:
            True if data is valid, False otherwise
        """
        required_timeframes = self.get_required_timeframes()

        for tf in required_timeframes:
            if tf not in data:
                return False
            if data[tf].empty:
                return False

        return True

    def get_info(self) -> Dict:
        """
        Get strategy information

        Returns:
            Dictionary with strategy metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'parameters': self.params,
            'required_timeframes': self.get_required_timeframes(),
            'required_indicators': self.get_required_indicators()
        }

    def calculate_trend_strength(self, ema_fast: float, ema_slow: float, price: float) -> float:
        """
        Helper: Calculate trend strength based on EMA positions

        Args:
            ema_fast: Fast EMA value
            ema_slow: Slow EMA value
            price: Current price

        Returns:
            Strength value between 0.0 and 1.0
        """
        if ema_fast == 0 or ema_slow == 0:
            return 0.0

        # Distance between EMAs as percentage
        ema_distance = abs(ema_fast - ema_slow) / ema_slow

        # Price position relative to EMAs
        price_above_fast = price > ema_fast
        price_above_slow = price > ema_slow

        # Strong trend if price and fast EMA are on same side of slow EMA
        if (price_above_slow and ema_fast > ema_slow) or \
           (not price_above_slow and ema_fast < ema_slow):
            strength = min(ema_distance * 10, 1.0)  # Scale to 0-1
        else:
            strength = 0.0

        return strength

    def normalize_rsi(self, rsi: float) -> float:
        """
        Helper: Normalize RSI to 0-1 scale

        Args:
            rsi: RSI value (0-100)

        Returns:
            Normalized value (0-1)
        """
        if rsi >= 70:
            return (rsi - 70) / 30  # Overbought strength
        elif rsi <= 30:
            return (30 - rsi) / 30  # Oversold strength
        else:
            return 0.0  # Neutral zone

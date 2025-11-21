"""
Trading Strategies Package
Contains all trading strategies and strategy management
"""

from strategies.base_strategy import BaseStrategy
from strategies.ema_crossover_strategy import EMACrossoverStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.combined_strategy import CombinedStrategy
from strategies.strategy_manager import StrategyManager, get_strategy_manager

__all__ = [
    'BaseStrategy',
    'EMACrossoverStrategy',
    'MACDStrategy',
    'RSIStrategy',
    'CombinedStrategy',
    'StrategyManager',
    'get_strategy_manager'
]

"""
MACD Strategy
Trading strategy based on MACD crossovers and histogram
"""

from typing import Dict, List
import pandas as pd
from strategies.base_strategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD-based trading strategy"""

    def __init__(self, params: Dict = None):
        default_params = {
            'histogram_threshold': 0.0,
            'min_strength': 0.65,
            'use_histogram': True,
            'confirm_with_trend': True
        }
        if params:
            default_params.update(params)

        super().__init__(
            name="MACD Strategy",
            description="Trades based on MACD crossovers and histogram strength",
            params=default_params
        )

    def get_required_timeframes(self) -> List[str]:
        return ['5m', '1h']

    def get_required_indicators(self) -> List[str]:
        return ['MACD', 'MACD_signal', 'MACD_hist', 'EMA_9', 'EMA_21']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """Analyze MACD signals"""
        if not self.validate_data(data):
            return self._flat_signal("Insufficient data")

        reasons = []
        strength_scores = []

        # Analyze primary timeframe (5m)
        df_5m = data['5m']
        if len(df_5m) < 2:
            return self._flat_signal("Not enough data points")

        macd = df_5m['MACD'].iloc[-1]
        macd_signal = df_5m['MACD_signal'].iloc[-1]
        macd_hist = df_5m['MACD_hist'].iloc[-1]
        prev_hist = df_5m['MACD_hist'].iloc[-2]

        # Detect crossovers
        bullish_cross = (macd > macd_signal) and (df_5m['MACD'].iloc[-2] <= df_5m['MACD_signal'].iloc[-2])
        bearish_cross = (macd < macd_signal) and (df_5m['MACD'].iloc[-2] >= df_5m['MACD_signal'].iloc[-2])

        # Histogram analysis
        hist_growing = macd_hist > prev_hist
        hist_shrinking = macd_hist < prev_hist
        hist_positive = macd_hist > 0
        hist_negative = macd_hist < 0

        action = 'flat'
        strength = 0.0

        # Bullish signals
        if bullish_cross:
            action = 'long'
            strength = 0.8
            reasons.append("5m: MACD bullish crossover")
        elif hist_positive and hist_growing:
            action = 'long'
            strength = 0.6
            reasons.append("5m: MACD histogram positive and growing")
        elif macd > macd_signal and hist_positive:
            action = 'long'
            strength = 0.5
            reasons.append("5m: MACD above signal with positive histogram")

        # Bearish signals
        if bearish_cross:
            action = 'short'
            strength = 0.8
            reasons.append("5m: MACD bearish crossover")
        elif hist_negative and not hist_growing:
            action = 'short'
            strength = 0.6
            reasons.append("5m: MACD histogram negative and falling")
        elif macd < macd_signal and hist_negative:
            action = 'short'
            strength = 0.5
            reasons.append("5m: MACD below signal with negative histogram")

        # Confirm with 1h trend if enabled
        if self.params['confirm_with_trend'] and '1h' in data:
            df_1h = data['1h']
            ema_fast_1h = df_1h['EMA_9'].iloc[-1]
            ema_slow_1h = df_1h['EMA_21'].iloc[-1]
            macd_1h = df_1h['MACD'].iloc[-1]
            signal_1h = df_1h['MACD_signal'].iloc[-1]

            trend_bullish = (ema_fast_1h > ema_slow_1h) and (macd_1h > signal_1h)
            trend_bearish = (ema_fast_1h < ema_slow_1h) and (macd_1h < signal_1h)

            if action == 'long' and trend_bullish:
                strength += 0.2
                reasons.append("1h: Trend confirmation (bullish)")
            elif action == 'short' and trend_bearish:
                strength += 0.2
                reasons.append("1h: Trend confirmation (bearish)")
            elif action == 'long' and trend_bearish:
                strength *= 0.5
                reasons.append("1h: Trend divergence (bearish trend conflicts)")
            elif action == 'short' and trend_bullish:
                strength *= 0.5
                reasons.append("1h: Trend divergence (bullish trend conflicts)")

        # Cap strength at 1.0
        strength = min(strength, 1.0)

        # Check minimum threshold
        if strength < self.params['min_strength']:
            reasons.append(f"Signal too weak ({strength:.2f} < {self.params['min_strength']})")
            action = 'flat'

        return {
            'action': action,
            'strength': strength,
            'confidence': strength,
            'reasons': reasons,
            'indicators': {
                'macd': macd,
                'macd_signal': macd_signal,
                'macd_hist': macd_hist,
                'histogram_growing': hist_growing,
                'current_price': current_price
            },
            'metadata': {
                'strategy': self.name,
                'crossover_detected': bullish_cross or bearish_cross
            }
        }

    def _flat_signal(self, reason: str) -> Dict:
        """Return a flat signal"""
        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [reason],
            'indicators': {},
            'metadata': {'strategy': self.name}
        }

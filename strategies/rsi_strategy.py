"""
RSI Mean Reversion Strategy
Trades based on RSI oversold/overbought conditions
"""

from typing import Dict, List
import pandas as pd
from strategies.base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI mean reversion trading strategy"""

    def __init__(self, params: Dict = None):
        default_params = {
            'oversold_level': 30,
            'overbought_level': 70,
            'extreme_oversold': 20,
            'extreme_overbought': 80,
            'min_strength': 0.6,
            'use_divergence': False
        }
        if params:
            default_params.update(params)

        super().__init__(
            name="RSI Mean Reversion",
            description="Trades RSI oversold/overbought conditions with mean reversion",
            params=default_params
        )

    def get_required_timeframes(self) -> List[str]:
        return ['5m', '1h']

    def get_required_indicators(self) -> List[str]:
        return ['RSI', 'close']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """Analyze RSI conditions"""
        if not self.validate_data(data):
            return self._flat_signal("Insufficient data")

        reasons = []

        # Analyze 5m RSI
        df_5m = data['5m']
        rsi_5m = df_5m['RSI'].iloc[-1]

        # Analyze 1h RSI for confirmation
        df_1h = data['1h']
        rsi_1h = df_1h['RSI'].iloc[-1]

        action = 'flat'
        strength = 0.0

        # Oversold conditions (buy signal)
        if rsi_5m <= self.params['oversold_level']:
            action = 'long'

            # Extreme oversold
            if rsi_5m <= self.params['extreme_oversold']:
                strength = 0.9
                reasons.append(f"5m: Extreme oversold (RSI: {rsi_5m:.1f})")
            else:
                strength = 0.7
                reasons.append(f"5m: Oversold (RSI: {rsi_5m:.1f})")

            # 1h confirmation
            if rsi_1h <= self.params['oversold_level']:
                strength = min(strength + 0.2, 1.0)
                reasons.append(f"1h: Also oversold (RSI: {rsi_1h:.1f}) - strong buy")
            elif rsi_1h > 50:
                reasons.append(f"1h: RSI neutral ({rsi_1h:.1f}) - mixed signal")

        # Overbought conditions (sell signal)
        elif rsi_5m >= self.params['overbought_level']:
            action = 'short'

            # Extreme overbought
            if rsi_5m >= self.params['extreme_overbought']:
                strength = 0.9
                reasons.append(f"5m: Extreme overbought (RSI: {rsi_5m:.1f})")
            else:
                strength = 0.7
                reasons.append(f"5m: Overbought (RSI: {rsi_5m:.1f})")

            # 1h confirmation
            if rsi_1h >= self.params['overbought_level']:
                strength = min(strength + 0.2, 1.0)
                reasons.append(f"1h: Also overbought (RSI: {rsi_1h:.1f}) - strong sell")
            elif rsi_1h < 50:
                reasons.append(f"1h: RSI neutral ({rsi_1h:.1f}) - mixed signal")

        # Neutral zone
        else:
            reasons.append(f"5m: RSI neutral ({rsi_5m:.1f}) - no clear signal")
            reasons.append(f"1h: RSI {rsi_1h:.1f}")

        # Check divergence if enabled
        if self.params['use_divergence'] and len(df_5m) >= 10:
            divergence = self._check_divergence(df_5m)
            if divergence:
                strength = min(strength + 0.15, 1.0)
                reasons.append(f"Bullish divergence detected" if divergence == 'bullish' else "Bearish divergence detected")

        # Check minimum threshold
        if strength < self.params['min_strength']:
            if action != 'flat':
                reasons.append(f"Signal too weak ({strength:.2f} < {self.params['min_strength']})")
            action = 'flat'

        return {
            'action': action,
            'strength': strength,
            'confidence': strength,
            'reasons': reasons,
            'indicators': {
                'rsi_5m': rsi_5m,
                'rsi_1h': rsi_1h,
                'oversold_level': self.params['oversold_level'],
                'overbought_level': self.params['overbought_level'],
                'current_price': current_price
            },
            'metadata': {
                'strategy': self.name,
                'rsi_zone': self._get_rsi_zone(rsi_5m)
            }
        }

    def _check_divergence(self, df: pd.DataFrame) -> str:
        """Check for RSI divergence (basic implementation)"""
        # This is a simplified divergence check
        # In production, you'd want more sophisticated logic

        if len(df) < 10:
            return None

        recent_prices = df['close'].iloc[-10:]
        recent_rsi = df['RSI'].iloc[-10:]

        # Bullish divergence: price making lower lows, RSI making higher lows
        price_trend = recent_prices.iloc[-1] < recent_prices.iloc[0]
        rsi_trend = recent_rsi.iloc[-1] > recent_rsi.iloc[0]

        if price_trend and rsi_trend and recent_rsi.iloc[-1] < 40:
            return 'bullish'

        # Bearish divergence: price making higher highs, RSI making lower highs
        price_trend_up = recent_prices.iloc[-1] > recent_prices.iloc[0]
        rsi_trend_down = recent_rsi.iloc[-1] < recent_rsi.iloc[0]

        if price_trend_up and rsi_trend_down and recent_rsi.iloc[-1] > 60:
            return 'bearish'

        return None

    def _get_rsi_zone(self, rsi: float) -> str:
        """Get RSI zone description"""
        if rsi <= self.params['extreme_oversold']:
            return 'extreme_oversold'
        elif rsi <= self.params['oversold_level']:
            return 'oversold'
        elif rsi >= self.params['extreme_overbought']:
            return 'extreme_overbought'
        elif rsi >= self.params['overbought_level']:
            return 'overbought'
        else:
            return 'neutral'

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

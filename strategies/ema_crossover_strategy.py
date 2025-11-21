"""
EMA Crossover Strategy
Simple strategy based on EMA crossovers across multiple timeframes
"""

from typing import Dict, List
import pandas as pd
from strategies.base_strategy import BaseStrategy


class EMACrossoverStrategy(BaseStrategy):
    """EMA Crossover trading strategy"""

    def __init__(self, params: Dict = None):
        default_params = {
            'fast_ema': 9,
            'slow_ema': 21,
            'min_strength': 0.6,
            'use_multi_timeframe': True
        }
        if params:
            default_params.update(params)

        super().__init__(
            name="EMA Crossover",
            description="Trades based on EMA crossovers across multiple timeframes",
            params=default_params
        )

    def get_required_timeframes(self) -> List[str]:
        if self.params['use_multi_timeframe']:
            return ['5m', '1h', '4h']
        return ['5m']

    def get_required_indicators(self) -> List[str]:
        return ['ema_9', 'ema_21', 'close']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """Analyze EMA crossovers"""
        if not self.validate_data(data):
            return self._flat_signal("Insufficient data")

        timeframes = self.get_required_timeframes()
        signals = {}
        reasons = []

        # Analyze each timeframe
        for tf in timeframes:
            df = data[tf]
            if len(df) < 2:
                continue

            ema_fast = df['ema_9'].iloc[-1]
            ema_slow = df['ema_21'].iloc[-1]
            prev_fast = df['ema_9'].iloc[-2]
            prev_slow = df['ema_21'].iloc[-2]

            # Detect crossover
            bullish_cross = (ema_fast > ema_slow) and (prev_fast <= prev_slow)
            bearish_cross = (ema_fast < ema_slow) and (prev_fast >= prev_slow)

            # Current trend
            bullish = ema_fast > ema_slow
            bearish = ema_fast < ema_slow

            # Calculate strength
            strength = self.calculate_trend_strength(ema_fast, ema_slow, current_price)

            if bullish_cross:
                signals[tf] = {'action': 'long', 'strength': min(strength + 0.3, 1.0)}
                reasons.append(f"{tf}: Bullish EMA crossover (EMA9 crossed above EMA21)")
            elif bearish_cross:
                signals[tf] = {'action': 'short', 'strength': min(strength + 0.3, 1.0)}
                reasons.append(f"{tf}: Bearish EMA crossover (EMA9 crossed below EMA21)")
            elif bullish:
                signals[tf] = {'action': 'long', 'strength': strength}
                reasons.append(f"{tf}: Bullish trend (EMA9 > EMA21, strength: {strength:.2f})")
            elif bearish:
                signals[tf] = {'action': 'short', 'strength': strength}
                reasons.append(f"{tf}: Bearish trend (EMA9 < EMA21, strength: {strength:.2f})")
            else:
                signals[tf] = {'action': 'flat', 'strength': 0.0}

        # Aggregate signals
        if not signals:
            return self._flat_signal("No valid signals")

        final_action, final_strength = self._aggregate_signals(signals)

        # Check minimum strength threshold
        if final_strength < self.params['min_strength']:
            reasons.append(f"Signal too weak ({final_strength:.2f} < {self.params['min_strength']})")
            final_action = 'flat'

        return {
            'action': final_action,
            'strength': final_strength,
            'confidence': final_strength,
            'reasons': reasons,
            'indicators': {
                'ema_fast': data['5m']['ema_9'].iloc[-1],
                'ema_slow': data['5m']['ema_21'].iloc[-1],
                'current_price': current_price
            },
            'metadata': {
                'timeframe_signals': signals,
                'strategy': self.name
            }
        }

    def _aggregate_signals(self, signals: Dict) -> tuple:
        """Aggregate signals from multiple timeframes"""
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0

        # Weight: 4h > 1h > 5m
        weights = {'4h': 3.0, '1h': 2.0, '5m': 1.0}

        for tf, signal in signals.items():
            weight = weights.get(tf, 1.0)
            action = signal['action']
            strength = signal['strength']

            if action == 'long':
                bullish_score += strength * weight
            elif action == 'short':
                bearish_score += strength * weight

            total_weight += weight

        # Normalize scores
        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight

        # Determine final action
        if bullish_score > bearish_score and bullish_score > 0.3:
            return 'long', bullish_score
        elif bearish_score > bullish_score and bearish_score > 0.3:
            return 'short', bearish_score
        else:
            return 'flat', max(bullish_score, bearish_score)

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

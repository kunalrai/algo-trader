"""
Combined Multi-Indicator Strategy
The original strategy - combines EMA, MACD, and RSI across multiple timeframes
"""

from typing import Dict, List
import pandas as pd
from strategies.base_strategy import BaseStrategy


class CombinedStrategy(BaseStrategy):
    """Multi-indicator combined strategy (the original bot strategy)"""

    def __init__(self, params: Dict = None):
        default_params = {
            'min_signal_strength': 0.7,
            'timeframes': ['5m', '1h', '4h'],
            'weights': {
                '4h': 3.0,
                '1h': 2.0,
                '5m': 1.0
            }
        }
        if params:
            default_params.update(params)

        super().__init__(
            name="Combined Multi-Indicator",
            description="Combines EMA, MACD, and RSI signals across multiple timeframes",
            params=default_params
        )

    def get_required_timeframes(self) -> List[str]:
        return self.params['timeframes']

    def get_required_indicators(self) -> List[str]:
        return ['EMA_9', 'EMA_21', 'MACD', 'MACD_signal', 'MACD_hist', 'RSI', 'close']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """Analyze using combined indicators"""
        if not self.validate_data(data):
            return self._flat_signal("Insufficient data")

        timeframe_analyses = {}
        reasons = []

        # Analyze each timeframe
        for tf in self.params['timeframes']:
            if tf not in data:
                continue

            df = data[tf]
            if len(df) < 2:
                continue

            analysis = self._analyze_timeframe(df, tf, current_price)
            timeframe_analyses[tf] = analysis

            # Add reasons from this timeframe
            if analysis['trend'] != 'neutral':
                reasons.append(
                    f"{tf}: {analysis['trend']} (EMA: {analysis['ema_signal']}, "
                    f"MACD: {analysis['macd_signal']}, RSI: {analysis['rsi']:.1f})"
                )

        if not timeframe_analyses:
            return self._flat_signal("No valid timeframe data")

        # Aggregate signals using weighted voting
        final_action, final_strength = self._aggregate_multi_timeframe(timeframe_analyses)

        # Build comprehensive reasons list
        if final_action == 'long':
            reasons.insert(0, f"Overall bullish signal (strength: {final_strength:.2f})")
        elif final_action == 'short':
            reasons.insert(0, f"Overall bearish signal (strength: {final_strength:.2f})")
        else:
            reasons.insert(0, "No strong trend detected")

        # Check minimum threshold
        if final_strength < self.params['min_signal_strength']:
            reasons.append(
                f"Signal below threshold ({final_strength:.2f} < {self.params['min_signal_strength']})"
            )
            final_action = 'flat'

        return {
            'action': final_action,
            'strength': final_strength,
            'confidence': final_strength,
            'reasons': reasons,
            'indicators': {
                'EMA_9': data['5m']['EMA_9'].iloc[-1],
                'EMA_21': data['5m']['EMA_21'].iloc[-1],
                'MACD': data['5m']['MACD'].iloc[-1],
                'MACD_signal': data['5m']['MACD_signal'].iloc[-1],
                'RSI': data['5m']['RSI'].iloc[-1],
                'current_price': current_price
            },
            'metadata': {
                'strategy': self.name,
                'timeframe_analyses': timeframe_analyses
            }
        }

    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str, current_price: float) -> Dict:
        """Analyze single timeframe with all indicators"""
        ema_9 = df['EMA_9'].iloc[-1]
        ema_21 = df['EMA_21'].iloc[-1]
        macd = df['MACD'].iloc[-1]
        macd_signal = df['MACD_signal'].iloc[-1]
        macd_hist = df['MACD_hist'].iloc[-1]
        rsi = df['RSI'].iloc[-1]

        # EMA analysis
        ema_bullish = ema_9 > ema_21
        ema_bearish = ema_9 < ema_21
        ema_strength = self.calculate_trend_strength(ema_9, ema_21, current_price)

        # MACD analysis
        macd_bullish = macd > macd_signal and macd_hist > 0
        macd_bearish = macd < macd_signal and macd_hist < 0

        # RSI analysis
        rsi_oversold = rsi < 30
        rsi_overbought = rsi > 70
        rsi_neutral = 30 <= rsi <= 70

        # Determine trend
        bullish_signals = sum([ema_bullish, macd_bullish, rsi_oversold or (rsi < 50 and ema_bullish)])
        bearish_signals = sum([ema_bearish, macd_bearish, rsi_overbought or (rsi > 50 and ema_bearish)])

        if bullish_signals >= 2:
            trend = 'bullish'
            strength = (bullish_signals / 3.0) * (1 + ema_strength) / 2
        elif bearish_signals >= 2:
            trend = 'bearish'
            strength = (bearish_signals / 3.0) * (1 + ema_strength) / 2
        else:
            trend = 'neutral'
            strength = 0.0

        return {
            'trend': trend,
            'strength': min(strength, 1.0),
            'ema_signal': 'bullish' if ema_bullish else 'bearish',
            'macd_signal': 'bullish' if macd_bullish else 'bearish',
            'rsi': rsi,
            'rsi_zone': 'oversold' if rsi_oversold else 'overbought' if rsi_overbought else 'neutral'
        }

    def _aggregate_multi_timeframe(self, analyses: Dict) -> tuple:
        """Aggregate signals from multiple timeframes with weighted voting"""
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0

        weights = self.params['weights']

        for tf, analysis in analyses.items():
            weight = weights.get(tf, 1.0)
            trend = analysis['trend']
            strength = analysis['strength']

            if trend == 'bullish':
                bullish_score += strength * weight
            elif trend == 'bearish':
                bearish_score += strength * weight

            total_weight += weight

        # Normalize
        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight

        # Determine final action
        if bullish_score > bearish_score and bullish_score > 0.5:
            return 'long', bullish_score
        elif bearish_score > bullish_score and bearish_score > 0.5:
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

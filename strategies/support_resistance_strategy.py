"""
Support/Resistance Long-Only Strategy
Buys near support levels and sells near resistance levels
Uses ATR for dynamic stop-loss calculation
"""

from typing import Dict, List, Optional
import pandas as pd
from strategies.base_strategy import BaseStrategy


class SupportResistanceStrategy(BaseStrategy):
    """
    Long-only strategy that:
    - Enters long positions near support levels
    - Exits (sells) near resistance levels
    - Uses ATR to determine maximum loss (stop-loss)
    """

    def __init__(self, params: Dict = None):
        default_params = {
            'support_proximity_pct': 1.0,      # Buy when price is within X% of support
            'resistance_proximity_pct': 1.0,   # Sell when price is within X% of resistance
            'atr_multiplier': 2.0,             # Stop-loss = ATR * multiplier
            'atr_period': 14,                  # ATR calculation period
            'lookback_period': 50,             # Candles to look back for S/R levels
            'num_levels': 3,                   # Number of S/R levels to calculate
            'min_strength': 0.6,               # Minimum signal strength to act
            'cluster_tolerance': 0.005,        # S/R level clustering tolerance (0.5%)
        }
        if params:
            default_params.update(params)

        super().__init__(
            name="Support/Resistance Long Only",
            description="Long-only strategy: buys near support, sells near resistance, ATR-based stop-loss",
            params=default_params
        )

    def get_required_timeframes(self) -> List[str]:
        return ['5m', '1h', '4h']

    def get_required_indicators(self) -> List[str]:
        return ['close', 'high', 'low', 'open', 'ATR', 'EMA_21', 'EMA_50']

    def analyze(self, data: Dict[str, pd.DataFrame], current_price: float) -> Dict:
        """
        Analyze market data for support/resistance trading opportunities

        Logic:
        - LONG: Price is near a support level (within proximity %)
        - EXIT (flat): Price is near a resistance level (within proximity %)
        - Stop-loss calculated as: entry_price - (ATR * atr_multiplier)
        """
        if not self.validate_data(data):
            return self._flat_signal("Insufficient data")

        reasons = []

        try:
            # Use 1h timeframe for primary S/R analysis (good balance of noise reduction)
            df_1h = data['1h']
            df_5m = data['5m']
            df_4h = data['4h']

            # Calculate support and resistance levels
            sr_levels = self._calculate_support_resistance(df_1h)
            support_levels = sr_levels['support_levels']
            resistance_levels = sr_levels['resistance_levels']

            # Get ATR for stop-loss calculation
            atr_value = self._get_atr(df_1h)
            stop_loss_distance = atr_value * self.params['atr_multiplier']

            # Check proximity to support (buy signal)
            near_support, support_info = self._check_near_support(current_price, support_levels)

            # Check proximity to resistance (sell/exit signal)
            near_resistance, resistance_info = self._check_near_resistance(current_price, resistance_levels)

            # Get trend confirmation from 4h timeframe
            trend_bullish = self._check_trend(df_4h)

            action = 'flat'
            strength = 0.0

            # Decision logic (LONG ONLY)
            if near_support and not near_resistance:
                action = 'long'
                strength = support_info['strength']
                reasons.append(f"Price ${current_price:.2f} near support ${support_info['level']:.2f}")
                reasons.append(f"Distance to support: {support_info['distance_pct']:.2f}%")

                # Boost strength if trend is bullish
                if trend_bullish:
                    strength = min(strength + 0.15, 1.0)
                    reasons.append("4h trend is bullish - confirmed")
                else:
                    reasons.append("4h trend not bullish - caution")

                # Add multi-timeframe support confirmation
                sr_5m = self._calculate_support_resistance(df_5m)
                if self._has_nearby_support(current_price, sr_5m['support_levels']):
                    strength = min(strength + 0.1, 1.0)
                    reasons.append("5m timeframe also shows nearby support")

            elif near_resistance:
                # Signal to exit/not enter (we don't short, so return flat)
                action = 'flat'
                strength = 0.0
                reasons.append(f"Price ${current_price:.2f} near resistance ${resistance_info['level']:.2f}")
                reasons.append(f"Distance to resistance: {resistance_info['distance_pct']:.2f}%")
                reasons.append("Avoiding long entry near resistance")

            else:
                # Price is in the middle - no clear signal
                reasons.append(f"Price ${current_price:.2f} not near key S/R levels")
                if support_levels:
                    reasons.append(f"Nearest support: ${support_levels[0]:.2f}")
                if resistance_levels:
                    reasons.append(f"Nearest resistance: ${resistance_levels[0]:.2f}")

            # Check minimum strength threshold
            if strength < self.params['min_strength']:
                if action != 'flat':
                    reasons.append(f"Signal too weak ({strength:.2f} < {self.params['min_strength']})")
                action = 'flat'

            # Calculate stop-loss and take-profit levels
            stop_loss_price = current_price - stop_loss_distance
            take_profit_price = resistance_levels[0] if resistance_levels else current_price * 1.03

            return {
                'action': action,
                'strength': strength,
                'confidence': strength,
                'reasons': reasons,
                'indicators': {
                    'current_price': current_price,
                    'support_levels': support_levels,
                    'resistance_levels': resistance_levels,
                    'atr': atr_value,
                    'stop_loss_distance': stop_loss_distance,
                    'stop_loss_price': round(stop_loss_price, 2),
                    'take_profit_price': round(take_profit_price, 2),
                    'near_support': near_support,
                    'near_resistance': near_resistance,
                },
                'metadata': {
                    'strategy': self.name,
                    'position_type': 'long_only',
                    'max_loss_atr': f"{self.params['atr_multiplier']}x ATR = ${stop_loss_distance:.2f}",
                    'risk_reward_ratio': round((take_profit_price - current_price) / stop_loss_distance, 2) if stop_loss_distance > 0 else 0
                }
            }

        except Exception as e:
            return self._flat_signal(f"Analysis error: {str(e)}")

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels from price data"""
        if df.empty or len(df) < self.params['lookback_period']:
            return {'support_levels': [], 'resistance_levels': []}

        lookback = self.params['lookback_period']
        num_levels = self.params['num_levels']
        tolerance = self.params['cluster_tolerance']

        recent_df = df.tail(lookback).copy()
        current_price = float(df.iloc[-1]['close'])

        highs = recent_df['high'].values
        lows = recent_df['low'].values

        resistance_points = []
        support_points = []

        # Find pivot points (local maxima and minima)
        for i in range(2, len(recent_df) - 2):
            # Resistance: local high
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_points.append(highs[i])

            # Support: local low
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_points.append(lows[i])

        # Cluster nearby levels
        def cluster_levels(levels):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = []
            current_cluster = [levels[0]]

            for level in levels[1:]:
                if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                    current_cluster.append(level)
                else:
                    clusters.append(sum(current_cluster) / len(current_cluster))
                    current_cluster = [level]

            if current_cluster:
                clusters.append(sum(current_cluster) / len(current_cluster))

            return clusters

        clustered_resistance = cluster_levels(resistance_points)
        clustered_support = cluster_levels(support_points)

        # Filter levels based on current price
        resistance_levels = sorted([r for r in clustered_resistance if r > current_price])[:num_levels]
        support_levels = sorted([s for s in clustered_support if s < current_price], reverse=True)[:num_levels]

        # Add fallback levels if not enough found
        while len(resistance_levels) < num_levels:
            next_r = current_price * (1 + 0.02 * (len(resistance_levels) + 1))
            resistance_levels.append(next_r)

        while len(support_levels) < num_levels:
            next_s = current_price * (1 - 0.02 * (len(support_levels) + 1))
            support_levels.append(next_s)

        return {
            'support_levels': [round(s, 2) for s in support_levels],
            'resistance_levels': [round(r, 2) for r in resistance_levels],
            'current_price': round(current_price, 2)
        }

    def _get_atr(self, df: pd.DataFrame) -> float:
        """Get ATR value from dataframe or calculate it"""
        # Try to get ATR from existing columns (handle case variations)
        atr_series = self._get_column(df, 'atr')
        if atr_series is not None and not atr_series.isna().all():
            return float(atr_series.iloc[-1])

        # Calculate ATR manually if not present
        period = self.params['atr_period']
        if len(df) < period:
            return 0.0

        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()

        return float(atr.iloc[-1])

    def _check_near_support(self, current_price: float, support_levels: List[float]) -> tuple:
        """Check if price is near a support level"""
        if not support_levels:
            return False, {}

        proximity_pct = self.params['support_proximity_pct']

        for support in support_levels:
            distance_pct = ((current_price - support) / support) * 100

            # Price is within proximity of support (slightly above support)
            if 0 <= distance_pct <= proximity_pct:
                # Strength increases as price gets closer to support
                strength = 0.7 + (0.3 * (1 - distance_pct / proximity_pct))
                return True, {
                    'level': support,
                    'distance_pct': distance_pct,
                    'strength': min(strength, 1.0)
                }

        return False, {}

    def _check_near_resistance(self, current_price: float, resistance_levels: List[float]) -> tuple:
        """Check if price is near a resistance level"""
        if not resistance_levels:
            return False, {}

        proximity_pct = self.params['resistance_proximity_pct']

        for resistance in resistance_levels:
            distance_pct = ((resistance - current_price) / current_price) * 100

            # Price is within proximity of resistance (slightly below resistance)
            if 0 <= distance_pct <= proximity_pct:
                strength = 0.7 + (0.3 * (1 - distance_pct / proximity_pct))
                return True, {
                    'level': resistance,
                    'distance_pct': distance_pct,
                    'strength': min(strength, 1.0)
                }

        return False, {}

    def _has_nearby_support(self, current_price: float, support_levels: List[float]) -> bool:
        """Quick check if there's nearby support (for multi-timeframe confirmation)"""
        if not support_levels:
            return False

        for support in support_levels:
            distance_pct = abs((current_price - support) / support) * 100
            if distance_pct <= self.params['support_proximity_pct'] * 1.5:
                return True

        return False

    def _get_column(self, df: pd.DataFrame, name: str) -> Optional[pd.Series]:
        """
        Get column from dataframe, handling both uppercase and lowercase naming conventions.
        The indicators module uses uppercase (EMA_21), but strategies may expect lowercase.
        """
        # Try exact match first
        if name in df.columns:
            return df[name]

        # Try uppercase version (EMA_21, RSI, MACD, etc.)
        upper_name = name.upper().replace('EMA_', 'EMA_')
        if upper_name in df.columns:
            return df[upper_name]

        # Try with underscore for EMAs (ema_21 -> EMA_21)
        if name.startswith('ema_'):
            ema_upper = f"EMA_{name.split('_')[1]}"
            if ema_upper in df.columns:
                return df[ema_upper]

        # Try ATR variations
        if name.lower() == 'atr':
            for col in ['ATR', 'atr', 'Atr']:
                if col in df.columns:
                    return df[col]

        return None

    def _check_trend(self, df: pd.DataFrame) -> bool:
        """Check if overall trend is bullish using EMAs"""
        if df.empty:
            return False

        try:
            # Get EMA columns (handle both uppercase and lowercase)
            ema_21_series = self._get_column(df, 'ema_21') or self._get_column(df, 'EMA_21')
            ema_50_series = self._get_column(df, 'ema_50') or self._get_column(df, 'EMA_50')

            if ema_21_series is not None and ema_50_series is not None:
                ema_21 = float(ema_21_series.iloc[-1])
                ema_50 = float(ema_50_series.iloc[-1])
                close = float(df['close'].iloc[-1])

                # Bullish if: price > EMA21 > EMA50
                return close > ema_21 and ema_21 > ema_50

            # Fallback: check if price is making higher lows
            if len(df) >= 10:
                recent_lows = df['low'].tail(10)
                return float(recent_lows.iloc[-1]) > float(recent_lows.iloc[0])

        except Exception:
            pass

        return False

    def _flat_signal(self, reason: str) -> Dict:
        """Return a flat (no action) signal"""
        return {
            'action': 'flat',
            'strength': 0.0,
            'confidence': 0.0,
            'reasons': [reason],
            'indicators': {},
            'metadata': {
                'strategy': self.name,
                'position_type': 'long_only'
            }
        }

"""
Trading Signal Generator
Combines multi-timeframe analysis to generate trading signals
"""

import pandas as pd
from typing import Dict, Optional
import logging
from indicators import TechnicalIndicators
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generate trading signals based on multi-timeframe technical analysis"""

    def __init__(self, data_fetcher: DataFetcher, indicator_config: Dict, rsi_config: Dict):
        self.data_fetcher = data_fetcher
        self.indicator_config = indicator_config
        self.rsi_config = rsi_config

    def analyze_timeframe(self, df: pd.DataFrame, timeframe_name: str) -> Dict:
        """
        Analyze a single timeframe

        Args:
            df: DataFrame with price data and indicators
            timeframe_name: Name of the timeframe (for logging)

        Returns:
            Dict with analysis results
        """
        if df.empty or len(df) < 50:
            logger.warning(f"Insufficient data for {timeframe_name} analysis")
            return {
                'trend': 'neutral',
                'macd_signal': 'neutral',
                'rsi_signal': 'neutral',
                'strength': 0.0
            }

        # Get signals from indicators
        trend = TechnicalIndicators.get_trend_direction(df)
        macd_signal = TechnicalIndicators.get_macd_signal(df)
        rsi_signal = TechnicalIndicators.get_rsi_signal(
            df,
            overbought=self.rsi_config['overbought'],
            oversold=self.rsi_config['oversold']
        )

        # Calculate signal strength
        strength = self._calculate_signal_strength(df, trend, macd_signal, rsi_signal)

        return {
            'trend': trend,
            'macd_signal': macd_signal,
            'rsi_signal': rsi_signal,
            'strength': strength,
            'last_close': df.iloc[-1]['close'],
            'rsi_value': df.iloc[-1]['RSI'] if 'RSI' in df.columns else 0
        }

    def _calculate_signal_strength(self, df: pd.DataFrame, trend: str,
                                   macd_signal: str, rsi_signal: str) -> float:
        """
        Calculate signal strength (0-1)

        Args:
            df: DataFrame with indicators
            trend: Trend direction
            macd_signal: MACD signal
            rsi_signal: RSI signal

        Returns:
            Signal strength between 0 and 1
        """
        strength = 0.0
        last_row = df.iloc[-1]

        # Trend alignment (0-0.4)
        if trend == 'bullish':
            strength += 0.2
            # Additional strength if price is above EMA200
            if 'EMA_200' in df.columns and last_row['close'] > last_row['EMA_200']:
                strength += 0.2
        elif trend == 'bearish':
            strength += 0.2
            if 'EMA_200' in df.columns and last_row['close'] < last_row['EMA_200']:
                strength += 0.2

        # MACD confirmation (0-0.3)
        if macd_signal == 'bullish' and trend == 'bullish':
            strength += 0.3
        elif macd_signal == 'bearish' and trend == 'bearish':
            strength += 0.3

        # RSI confirmation (0-0.3)
        if 'RSI' in df.columns:
            rsi_value = last_row['RSI']
            if trend == 'bullish' and 30 < rsi_value < 70:
                strength += 0.3
            elif trend == 'bearish' and 30 < rsi_value < 70:
                strength += 0.3
            elif rsi_signal == 'oversold' and trend == 'bullish':
                strength += 0.2
            elif rsi_signal == 'overbought' and trend == 'bearish':
                strength += 0.2

        return min(strength, 1.0)

    def generate_signal(self, pair: str, timeframes: Dict[str, str]) -> Optional[Dict]:
        """
        Generate trading signal based on multi-timeframe analysis

        Args:
            pair: Trading pair
            timeframes: Dict of timeframe names and intervals

        Returns:
            Signal dict with action, strength, and analysis details
        """
        try:
            # Fetch data for all timeframes
            logger.info(f"Generating signal for {pair}")
            multi_tf_data = self.data_fetcher.fetch_multi_timeframe_data(pair, timeframes)

            if not multi_tf_data:
                logger.warning(f"No data available for {pair}")
                return None

            # Add indicators to each timeframe
            for tf_name, df in multi_tf_data.items():
                multi_tf_data[tf_name] = TechnicalIndicators.add_all_indicators(
                    df,
                    self.indicator_config['EMA'],
                    self.indicator_config['MACD'],
                    self.indicator_config['RSI']['period']
                )

            # Analyze each timeframe
            analyses = {}
            for tf_name, df in multi_tf_data.items():
                analyses[tf_name] = self.analyze_timeframe(df, tf_name)

            # Calculate support/resistance levels
            # Short-term: Use 5m or 1h data
            # Long-term: Use 4h data
            short_term_sr = {}
            long_term_sr = {}

            if 'short_term' in multi_tf_data:
                short_term_sr = TechnicalIndicators.get_support_resistance_levels(
                    multi_tf_data['short_term'],
                    timeframe_type='short'
                )
            elif 'medium_term' in multi_tf_data:
                short_term_sr = TechnicalIndicators.get_support_resistance_levels(
                    multi_tf_data['medium_term'],
                    timeframe_type='short'
                )

            if 'long_term' in multi_tf_data:
                long_term_sr = TechnicalIndicators.get_support_resistance_levels(
                    multi_tf_data['long_term'],
                    timeframe_type='long'
                )

            # Combine signals from multiple timeframes
            signal = self._combine_multi_timeframe_signals(pair, analyses)

            # Add support/resistance to signal
            signal['support_resistance'] = {
                'short_term': short_term_sr,
                'long_term': long_term_sr
            }

            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {pair}: {e}")
            return None

    def _combine_multi_timeframe_signals(self, pair: str, analyses: Dict) -> Dict:
        """
        Combine signals from multiple timeframes

        Args:
            pair: Trading pair
            analyses: Dict of timeframe analyses

        Returns:
            Combined signal dict
        """
        # Weight different timeframes
        weights = {
            'short_term': 0.3,   # 5m
            'medium_term': 0.3,  # 1h
            'long_term': 0.4     # 4h
        }

        bullish_score = 0.0
        bearish_score = 0.0

        for tf_name, analysis in analyses.items():
            weight = weights.get(tf_name, 0.33)

            if analysis['trend'] == 'bullish':
                bullish_score += weight * analysis['strength']
            elif analysis['trend'] == 'bearish':
                bearish_score += weight * analysis['strength']

        # Determine action
        action = 'flat'
        strength = 0.0

        if bullish_score > bearish_score and bullish_score > 0.5:
            action = 'long'
            strength = bullish_score
        elif bearish_score > bullish_score and bearish_score > 0.5:
            action = 'short'
            strength = bearish_score

        # Get current price
        current_price = analyses.get('short_term', {}).get('last_close', 0)

        signal = {
            'pair': pair,
            'action': action,
            'strength': strength,
            'current_price': current_price,
            'analyses': analyses,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'timestamp': pd.Timestamp.now()
        }

        logger.info(
            f"Signal for {pair}: {action.upper()} "
            f"(Strength: {strength:.2f}, Bullish: {bullish_score:.2f}, "
            f"Bearish: {bearish_score:.2f})"
        )

        return signal

    def should_close_position(self, position: Dict, current_analysis: Dict) -> bool:
        """
        Determine if a position should be closed based on signal reversal

        Args:
            position: Current position dict
            current_analysis: Current market analysis

        Returns:
            True if position should be closed
        """
        try:
            position_side = position.get('side', '')

            # Close long if strong bearish signal
            if position_side == 'long':
                if (current_analysis.get('bearish_score', 0) > 0.6 and
                    current_analysis.get('bearish_score', 0) > current_analysis.get('bullish_score', 0)):
                    logger.info(f"Signal reversal detected for LONG position on {position.get('pair')}")
                    return True

            # Close short if strong bullish signal
            elif position_side == 'short':
                if (current_analysis.get('bullish_score', 0) > 0.6 and
                    current_analysis.get('bullish_score', 0) > current_analysis.get('bearish_score', 0)):
                    logger.info(f"Signal reversal detected for SHORT position on {position.get('pair')}")
                    return True

        except Exception as e:
            logger.error(f"Error checking position close signal: {e}")

        return False

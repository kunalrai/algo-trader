"""
Trading Signal Generator
Combines multi-timeframe analysis to generate trading signals
Supports pluggable strategy system
"""

import pandas as pd
from typing import Dict, Optional
import logging
from indicators import TechnicalIndicators
from data_fetcher import DataFetcher
from strategies.strategy_manager import get_strategy_manager

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generate trading signals based on multi-timeframe technical analysis"""

    def __init__(self, data_fetcher: DataFetcher, indicator_config: Dict, rsi_config: Dict, use_strategy_system: bool = False):
        self.data_fetcher = data_fetcher
        self.indicator_config = indicator_config
        self.rsi_config = rsi_config
        self.use_strategy_system = use_strategy_system
        self.strategy_manager = get_strategy_manager() if use_strategy_system else None

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

            # Use strategy system if enabled
            if self.use_strategy_system and self.strategy_manager:
                return self._generate_signal_with_strategy(pair, multi_tf_data, timeframes)

            # LEGACY MODE: Original signal generation
            # Analyze each timeframe
            analyses = {}
            for tf_name, df in multi_tf_data.items():
                analyses[tf_name] = self.analyze_timeframe(df, tf_name)

            # Calculate support/resistance levels
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

            # Calculate ATR from medium-term timeframe (most suitable for stop loss)
            atr_value = None
            atr_timeframe = 'medium_term' if 'medium_term' in multi_tf_data else 'short_term'
            if atr_timeframe in multi_tf_data:
                df = multi_tf_data[atr_timeframe]
                atr_period = self.indicator_config.get('ATR', {}).get('period', 14)
                atr_series = TechnicalIndicators.calculate_atr(df, period=atr_period)
                if len(atr_series) > 0 and not atr_series.isna().all():
                    atr_value = float(atr_series.iloc[-1])
                    logger.debug(f"ATR({atr_period}) for {pair}: {atr_value:.4f}")

            signal['atr'] = atr_value

            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {pair}: {e}")
            return None

    def _generate_signal_with_strategy(self, pair: str, multi_tf_data: Dict, timeframes: Dict) -> Optional[Dict]:
        """
        Generate signal using pluggable strategy system

        Args:
            pair: Trading pair
            multi_tf_data: Multi-timeframe data with indicators
            timeframes: Timeframe configuration

        Returns:
            Signal dictionary or None
        """
        try:
            active_strategy = self.strategy_manager.get_active_strategy()
            if not active_strategy:
                logger.warning("No active strategy set, falling back to legacy mode")
                return None

            # Map timeframe names to strategy format (5m, 1h, 4h)
            strategy_data = {}
            timeframe_mapping = {
                'short_term': '5m',
                'medium_term': '1h',
                'long_term': '4h'
            }

            for tf_name, df in multi_tf_data.items():
                mapped_name = timeframe_mapping.get(tf_name, tf_name)
                strategy_data[mapped_name] = df

            # Get current price
            current_price = 0
            if '5m' in strategy_data and not strategy_data['5m'].empty:
                current_price = strategy_data['5m']['close'].iloc[-1]
            elif multi_tf_data:
                first_df = next(iter(multi_tf_data.values()))
                current_price = first_df['close'].iloc[-1] if not first_df.empty else 0

            # Analyze with active strategy
            strategy_signal = self.strategy_manager.analyze_with_active_strategy(
                strategy_data,
                current_price
            )

            if not strategy_signal:
                return None

            # Calculate ATR from 1h timeframe (most suitable for stop loss)
            atr_value = None
            atr_timeframe = '1h' if '1h' in strategy_data else '5m'
            if atr_timeframe in strategy_data:
                df = strategy_data[atr_timeframe]
                atr_period = self.indicator_config.get('ATR', {}).get('period', 14)
                atr_series = TechnicalIndicators.calculate_atr(df, period=atr_period)
                if len(atr_series) > 0 and not atr_series.isna().all():
                    atr_value = float(atr_series.iloc[-1])
                    logger.debug(f"ATR({atr_period}) for {pair}: {atr_value:.4f}")

            # Build analyses dict for compatibility with legacy format
            analyses = {}
            for tf_name, df in multi_tf_data.items():
                if not df.empty:
                    analyses[tf_name] = {
                        'trend': 'neutral',
                        'macd_signal': 'neutral',
                        'rsi_signal': 'neutral',
                        'rsi_value': df['RSI'].iloc[-1] if 'RSI' in df.columns else 0,
                        'strength': strategy_signal['strength']
                    }

            # Convert strategy signal to expected format
            signal = {
                'pair': pair,
                'action': strategy_signal['action'],
                'strength': strategy_signal['strength'],
                'bullish_score': strategy_signal['strength'] if strategy_signal['action'] == 'long' else 0,
                'bearish_score': strategy_signal['strength'] if strategy_signal['action'] == 'short' else 0,
                'current_price': current_price,
                'reasons': strategy_signal['reasons'],
                'confidence': strategy_signal.get('confidence', strategy_signal['strength']),
                'indicators': strategy_signal.get('indicators', {}),
                'strategy_name': active_strategy.name,
                'strategy_metadata': strategy_signal.get('metadata', {}),
                'analyses': analyses,
                'timestamp': pd.Timestamp.now(),
                'atr': atr_value
            }

            logger.info(
                f"Signal for {pair} using {active_strategy.name}: {signal['action'].upper()} "
                f"(Strength: {signal['strength']:.2f})"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating signal with strategy for {pair}: {e}")
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

        # Build reasons list explaining the decision
        reasons = []
        for tf_name, analysis in analyses.items():
            trend = analysis.get('trend', 'neutral')
            if trend != 'neutral':
                reasons.append(f"{tf_name}: {trend} trend (strength: {analysis.get('strength', 0):.2f})")

        # Add overall scores
        if action == 'long':
            reasons.append(f"Overall bullish score: {bullish_score:.2f} > bearish: {bearish_score:.2f}")
        elif action == 'short':
            reasons.append(f"Overall bearish score: {bearish_score:.2f} > bullish: {bullish_score:.2f}")
        else:
            reasons.append(f"No clear signal - bullish: {bullish_score:.2f}, bearish: {bearish_score:.2f}")

        signal = {
            'pair': pair,
            'action': action,
            'strength': strength,
            'current_price': current_price,
            'analyses': analyses,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'reasons': reasons,  # NEW: Explanation of decision
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

"""
Technical Indicators Module
Implements EMA, MACD, RSI calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for trading signals"""

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            df: DataFrame with OHLCV data (must have 'high', 'low', 'close' columns)
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate True Range components
        tr1 = high - low  # Current high - current low
        tr2 = abs(high - close.shift(1))  # Current high - previous close
        tr3 = abs(low - close.shift(1))   # Current low - previous close

        # True Range is the max of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is the exponential moving average of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            df: DataFrame with price data
            period: EMA period
            column: Column to calculate EMA on

        Returns:
            Series with EMA values
        """
        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_all_emas(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """
        Calculate multiple EMAs and add to DataFrame

        Args:
            df: DataFrame with price data
            periods: List of EMA periods

        Returns:
            DataFrame with EMA columns added
        """
        result_df = df.copy()

        for period in periods:
            result_df[f'EMA_{period}'] = TechnicalIndicators.calculate_ema(df, period)

        return result_df

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with price data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            DataFrame with MACD columns
        """
        result_df = df.copy()

        # Calculate MACD line
        ema_fast = result_df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = result_df['close'].ewm(span=slow, adjust=False).mean()
        result_df['MACD'] = ema_fast - ema_slow

        # Calculate signal line
        result_df['MACD_signal'] = result_df['MACD'].ewm(span=signal, adjust=False).mean()

        # Calculate histogram
        result_df['MACD_hist'] = result_df['MACD'] - result_df['MACD_signal']

        return result_df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """
        Calculate Relative Strength Index

        Args:
            df: DataFrame with price data
            period: RSI period
            column: Column to calculate RSI on

        Returns:
            Series with RSI values
        """
        delta = df[column].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        # For subsequent values, use exponential moving average
        for i in range(period, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def add_all_indicators(df: pd.DataFrame, ema_periods: List[int],
                          macd_params: Dict, rsi_period: int) -> pd.DataFrame:
        """
        Add all technical indicators to DataFrame

        Args:
            df: DataFrame with OHLCV data
            ema_periods: List of EMA periods
            macd_params: MACD parameters dict
            rsi_period: RSI period

        Returns:
            DataFrame with all indicators added
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to add_all_indicators")
            return df

        result_df = df.copy()

        try:
            # Add EMAs
            for period in ema_periods:
                result_df[f'EMA_{period}'] = TechnicalIndicators.calculate_ema(result_df, period)

            # Add MACD
            result_df = TechnicalIndicators.calculate_macd(
                result_df,
                fast=macd_params['fast'],
                slow=macd_params['slow'],
                signal=macd_params['signal']
            )

            # Add RSI
            result_df['RSI'] = TechnicalIndicators.calculate_rsi(result_df, rsi_period)

            logger.debug(f"Added all indicators to DataFrame with {len(result_df)} rows")

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")

        return result_df

    @staticmethod
    def get_trend_direction(df: pd.DataFrame) -> str:
        """
        Determine trend direction based on EMAs

        Args:
            df: DataFrame with EMA indicators

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if df.empty or len(df) < 2:
            return 'neutral'

        try:
            last_row = df.iloc[-1]

            # Check EMA alignment
            # Bullish: EMA9 > EMA15 > EMA20 > EMA50
            # Bearish: EMA9 < EMA15 < EMA20 < EMA50

            if ('EMA_9' in df.columns and 'EMA_15' in df.columns and
                'EMA_20' in df.columns and 'EMA_50' in df.columns):

                if (last_row['EMA_9'] > last_row['EMA_15'] >
                    last_row['EMA_20'] > last_row['EMA_50']):
                    return 'bullish'
                elif (last_row['EMA_9'] < last_row['EMA_15'] <
                      last_row['EMA_20'] < last_row['EMA_50']):
                    return 'bearish'

        except Exception as e:
            logger.error(f"Error determining trend direction: {e}")

        return 'neutral'

    @staticmethod
    def get_macd_signal(df: pd.DataFrame) -> str:
        """
        Get MACD signal (bullish/bearish crossover)

        Args:
            df: DataFrame with MACD indicators

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if df.empty or len(df) < 2:
            return 'neutral'

        try:
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Bullish crossover: MACD crosses above signal
            if (previous['MACD'] <= previous['MACD_signal'] and
                current['MACD'] > current['MACD_signal']):
                return 'bullish'

            # Bearish crossover: MACD crosses below signal
            if (previous['MACD'] >= previous['MACD_signal'] and
                current['MACD'] < current['MACD_signal']):
                return 'bearish'

        except Exception as e:
            logger.error(f"Error getting MACD signal: {e}")

        return 'neutral'

    @staticmethod
    def get_rsi_signal(df: pd.DataFrame, overbought: float = 70, oversold: float = 30) -> str:
        """
        Get RSI signal

        Args:
            df: DataFrame with RSI indicator
            overbought: Overbought threshold
            oversold: Oversold threshold

        Returns:
            'overbought', 'oversold', or 'neutral'
        """
        if df.empty:
            return 'neutral'

        try:
            current_rsi = df.iloc[-1]['RSI']

            if current_rsi >= overbought:
                return 'overbought'
            elif current_rsi <= oversold:
                return 'oversold'

        except Exception as e:
            logger.error(f"Error getting RSI signal: {e}")

        return 'neutral'

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, lookback: int = 20, num_levels: int = 3) -> Dict:
        """
        Calculate support and resistance levels using pivot points and local extrema

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of candles to look back for finding levels
            num_levels: Number of S/R levels to return

        Returns:
            Dict with support and resistance levels
        """
        if df.empty or len(df) < lookback:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'current_price': 0
            }

        try:
            recent_df = df.tail(lookback).copy()
            current_price = float(df.iloc[-1]['close'])

            # Find local maxima (resistance) and minima (support)
            highs = recent_df['high'].values
            lows = recent_df['low'].values

            # Detect pivot points
            resistance_points = []
            support_points = []

            for i in range(2, len(recent_df) - 2):
                # Resistance: high[i] is higher than surrounding highs
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    resistance_points.append(highs[i])

                # Support: low[i] is lower than surrounding lows
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    support_points.append(lows[i])

            # Cluster similar levels (within 0.5% of each other)
            def cluster_levels(levels, tolerance=0.005):
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

            # Cluster and filter levels
            clustered_resistance = cluster_levels(resistance_points)
            clustered_support = cluster_levels(support_points)

            # Filter to get levels above/below current price
            resistance_levels = sorted([r for r in clustered_resistance if r > current_price])[:num_levels]
            support_levels = sorted([s for s in clustered_support if s < current_price], reverse=True)[:num_levels]

            # If not enough levels found, add levels based on percentage
            while len(resistance_levels) < num_levels:
                next_resistance = current_price * (1 + 0.02 * (len(resistance_levels) + 1))
                resistance_levels.append(next_resistance)

            while len(support_levels) < num_levels:
                next_support = current_price * (1 - 0.02 * (len(support_levels) + 1))
                support_levels.append(next_support)

            return {
                'support_levels': [round(s, 2) for s in support_levels[:num_levels]],
                'resistance_levels': [round(r, 2) for r in resistance_levels[:num_levels]],
                'current_price': round(current_price, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {
                'support_levels': [],
                'resistance_levels': [],
                'current_price': 0
            }

    @staticmethod
    def get_support_resistance_levels(df: pd.DataFrame, timeframe_type: str = 'short') -> Dict:
        """
        Get support and resistance levels based on timeframe

        Args:
            df: DataFrame with OHLCV data
            timeframe_type: 'short' for short-term (5m-1h) or 'long' for long-term (4h+)

        Returns:
            Dict with support/resistance levels
        """
        if timeframe_type == 'short':
            # Short-term: look back 20 candles, find 2 levels
            return TechnicalIndicators.calculate_support_resistance(df, lookback=20, num_levels=2)
        else:
            # Long-term: look back 50 candles, find 3 levels
            return TechnicalIndicators.calculate_support_resistance(df, lookback=50, num_levels=3)

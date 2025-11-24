"""
Technical Indicators Module
Uses pandas_ta library for robust indicator calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import logging

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for trading signals using pandas_ta"""

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
        if PANDAS_TA_AVAILABLE:
            return ta.atr(df['high'], df['low'], df['close'], length=period)

        # Fallback implementation
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
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
        if PANDAS_TA_AVAILABLE:
            return ta.ema(df[column], length=period)

        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Simple Moving Average

        Args:
            df: DataFrame with price data
            period: SMA period
            column: Column to calculate SMA on

        Returns:
            Series with SMA values
        """
        if PANDAS_TA_AVAILABLE:
            return ta.sma(df[column], length=period)

        return df[column].rolling(window=period).mean()

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

        if PANDAS_TA_AVAILABLE:
            macd_df = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            if macd_df is not None and not macd_df.empty:
                result_df['MACD'] = macd_df[f'MACD_{fast}_{slow}_{signal}']
                result_df['MACD_signal'] = macd_df[f'MACDs_{fast}_{slow}_{signal}']
                result_df['MACD_hist'] = macd_df[f'MACDh_{fast}_{slow}_{signal}']
                return result_df

        # Fallback implementation
        ema_fast = result_df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = result_df['close'].ewm(span=slow, adjust=False).mean()
        result_df['MACD'] = ema_fast - ema_slow
        result_df['MACD_signal'] = result_df['MACD'].ewm(span=signal, adjust=False).mean()
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
        if PANDAS_TA_AVAILABLE:
            return ta.rsi(df[column], length=period)

        # Fallback implementation
        delta = df[column].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        for i in range(period, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with price data
            period: BB period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            DataFrame with BB columns added
        """
        result_df = df.copy()

        if PANDAS_TA_AVAILABLE:
            bb_df = ta.bbands(df['close'], length=period, std=std_dev)
            if bb_df is not None and not bb_df.empty:
                result_df['BB_lower'] = bb_df[f'BBL_{period}_{std_dev}']
                result_df['BB_middle'] = bb_df[f'BBM_{period}_{std_dev}']
                result_df['BB_upper'] = bb_df[f'BBU_{period}_{std_dev}']
                result_df['BB_bandwidth'] = bb_df[f'BBB_{period}_{std_dev}']
                result_df['BB_percent'] = bb_df[f'BBP_{period}_{std_dev}']
                return result_df

        # Fallback implementation
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        result_df['BB_middle'] = sma
        result_df['BB_upper'] = sma + (std * std_dev)
        result_df['BB_lower'] = sma - (std * std_dev)
        result_df['BB_bandwidth'] = (result_df['BB_upper'] - result_df['BB_lower']) / result_df['BB_middle']
        result_df['BB_percent'] = (df['close'] - result_df['BB_lower']) / (result_df['BB_upper'] - result_df['BB_lower'])

        return result_df

    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """
        Calculate Stochastic Oscillator

        Args:
            df: DataFrame with OHLCV data
            k_period: %K period (default 14)
            d_period: %D period (default 3)

        Returns:
            DataFrame with Stochastic columns added
        """
        result_df = df.copy()

        if PANDAS_TA_AVAILABLE:
            stoch_df = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
            if stoch_df is not None and not stoch_df.empty:
                result_df['STOCH_K'] = stoch_df[f'STOCHk_{k_period}_{d_period}_3']
                result_df['STOCH_D'] = stoch_df[f'STOCHd_{k_period}_{d_period}_3']
                return result_df

        # Fallback implementation
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        result_df['STOCH_K'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        result_df['STOCH_D'] = result_df['STOCH_K'].rolling(window=d_period).mean()

        return result_df

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average Directional Index (ADX)

        Args:
            df: DataFrame with OHLCV data
            period: ADX period (default 14)

        Returns:
            DataFrame with ADX columns added
        """
        result_df = df.copy()

        if PANDAS_TA_AVAILABLE:
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=period)
            if adx_df is not None and not adx_df.empty:
                result_df['ADX'] = adx_df[f'ADX_{period}']
                result_df['DI_plus'] = adx_df[f'DMP_{period}']
                result_df['DI_minus'] = adx_df[f'DMN_{period}']
                return result_df

        # Fallback: return empty columns (ADX calculation is complex)
        result_df['ADX'] = np.nan
        result_df['DI_plus'] = np.nan
        result_df['DI_minus'] = np.nan
        logger.warning("ADX calculation requires pandas_ta - install with: pip install pandas_ta")

        return result_df

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Series with VWAP values
        """
        if PANDAS_TA_AVAILABLE:
            return ta.vwap(df['high'], df['low'], df['close'], df['volume'])

        # Fallback implementation
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV)

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Series with OBV values
        """
        if PANDAS_TA_AVAILABLE:
            return ta.obv(df['close'], df['volume'])

        # Fallback implementation
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=df.index)

    @staticmethod
    def add_all_indicators(df: pd.DataFrame, ema_periods: List[int],
                          macd_params: Dict, rsi_period: int,
                          include_extended: bool = False) -> pd.DataFrame:
        """
        Add all technical indicators to DataFrame

        Args:
            df: DataFrame with OHLCV data
            ema_periods: List of EMA periods
            macd_params: MACD parameters dict
            rsi_period: RSI period
            include_extended: Include extended indicators (BB, Stochastic, ADX, VWAP, OBV)

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

            # Add ATR
            result_df['ATR'] = TechnicalIndicators.calculate_atr(result_df)

            # Extended indicators (optional)
            if include_extended:
                # Bollinger Bands
                result_df = TechnicalIndicators.calculate_bollinger_bands(result_df)

                # Stochastic
                result_df = TechnicalIndicators.calculate_stochastic(result_df)

                # ADX
                result_df = TechnicalIndicators.calculate_adx(result_df)

                # Volume indicators
                if 'volume' in result_df.columns:
                    result_df['VWAP'] = TechnicalIndicators.calculate_vwap(result_df)
                    result_df['OBV'] = TechnicalIndicators.calculate_obv(result_df)

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

            if (previous['MACD'] <= previous['MACD_signal'] and
                current['MACD'] > current['MACD_signal']):
                return 'bullish'

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
    def get_stochastic_signal(df: pd.DataFrame, overbought: float = 80, oversold: float = 20) -> str:
        """
        Get Stochastic signal

        Args:
            df: DataFrame with Stochastic indicator
            overbought: Overbought threshold
            oversold: Oversold threshold

        Returns:
            'overbought', 'oversold', or 'neutral'
        """
        if df.empty or 'STOCH_K' not in df.columns:
            return 'neutral'

        try:
            current_k = df.iloc[-1]['STOCH_K']
            current_d = df.iloc[-1]['STOCH_D']

            if current_k >= overbought and current_d >= overbought:
                return 'overbought'
            elif current_k <= oversold and current_d <= oversold:
                return 'oversold'

        except Exception as e:
            logger.error(f"Error getting Stochastic signal: {e}")

        return 'neutral'

    @staticmethod
    def get_bb_signal(df: pd.DataFrame) -> str:
        """
        Get Bollinger Bands signal

        Args:
            df: DataFrame with Bollinger Bands indicators

        Returns:
            'upper_touch', 'lower_touch', or 'neutral'
        """
        if df.empty or 'BB_upper' not in df.columns:
            return 'neutral'

        try:
            last_row = df.iloc[-1]
            close = last_row['close']

            if close >= last_row['BB_upper']:
                return 'upper_touch'
            elif close <= last_row['BB_lower']:
                return 'lower_touch'

        except Exception as e:
            logger.error(f"Error getting BB signal: {e}")

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

            highs = recent_df['high'].values
            lows = recent_df['low'].values

            resistance_points = []
            support_points = []

            for i in range(2, len(recent_df) - 2):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    resistance_points.append(highs[i])

                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    support_points.append(lows[i])

            def cluster_levels_with_zones(levels, tolerance=0.005):
                if not levels:
                    return [], []

                levels = sorted(levels)
                clusters = []
                zones = []
                current_cluster = [levels[0]]

                for level in levels[1:]:
                    if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                        current_cluster.append(level)
                    else:
                        cluster_center = sum(current_cluster) / len(current_cluster)
                        zone_upper = max(current_cluster)
                        zone_lower = min(current_cluster)
                        zone_range = zone_upper - zone_lower
                        if zone_range < cluster_center * 0.002:  # Min 0.2% range
                            zone_range = cluster_center * 0.002
                        zone_upper = cluster_center + zone_range / 2
                        zone_lower = cluster_center - zone_range / 2

                        clusters.append(cluster_center)
                        zones.append({'upper': zone_upper, 'lower': zone_lower, 'center': cluster_center})
                        current_cluster = [level]

                if current_cluster:
                    cluster_center = sum(current_cluster) / len(current_cluster)
                    zone_upper = max(current_cluster)
                    zone_lower = min(current_cluster)
                    zone_range = zone_upper - zone_lower
                    if zone_range < cluster_center * 0.002:
                        zone_range = cluster_center * 0.002
                    zone_upper = cluster_center + zone_range / 2
                    zone_lower = cluster_center - zone_range / 2

                    clusters.append(cluster_center)
                    zones.append({'upper': zone_upper, 'lower': zone_lower, 'center': cluster_center})

                return clusters, zones

            clustered_resistance, resistance_zones_raw = cluster_levels_with_zones(resistance_points)
            clustered_support, support_zones_raw = cluster_levels_with_zones(support_points)

            # Filter and combine levels with zones
            resistance_data = [(r, z) for r, z in zip(clustered_resistance, resistance_zones_raw) if r > current_price]
            support_data = [(s, z) for s, z in zip(clustered_support, support_zones_raw) if s < current_price]

            resistance_data = sorted(resistance_data, key=lambda x: x[0])[:num_levels]
            support_data = sorted(support_data, key=lambda x: x[0], reverse=True)[:num_levels]

            resistance_levels = [r[0] for r in resistance_data]
            resistance_zones = [r[1] for r in resistance_data]
            support_levels = [s[0] for s in support_data]
            support_zones = [s[1] for s in support_data]

            # Add fallback levels with zones if needed
            while len(resistance_levels) < num_levels:
                next_resistance = current_price * (1 + 0.02 * (len(resistance_levels) + 1))
                resistance_levels.append(next_resistance)
                zone_range = next_resistance * 0.002
                resistance_zones.append({
                    'upper': next_resistance + zone_range / 2,
                    'lower': next_resistance - zone_range / 2,
                    'center': next_resistance
                })

            while len(support_levels) < num_levels:
                next_support = current_price * (1 - 0.02 * (len(support_levels) + 1))
                support_levels.append(next_support)
                zone_range = next_support * 0.002
                support_zones.append({
                    'upper': next_support + zone_range / 2,
                    'lower': next_support - zone_range / 2,
                    'center': next_support
                })

            return {
                'support_levels': [round(s, 2) for s in support_levels[:num_levels]],
                'resistance_levels': [round(r, 2) for r in resistance_levels[:num_levels]],
                'support_zones': [
                    {
                        'upper': round(z['upper'], 2),
                        'lower': round(z['lower'], 2),
                        'center': round(z['center'], 2)
                    }
                    for z in support_zones[:num_levels]
                ],
                'resistance_zones': [
                    {
                        'upper': round(z['upper'], 2),
                        'lower': round(z['lower'], 2),
                        'center': round(z['center'], 2)
                    }
                    for z in resistance_zones[:num_levels]
                ],
                'current_price': round(current_price, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {
                'support_levels': [],
                'resistance_levels': [],
                'support_zones': [],
                'resistance_zones': [],
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
            return TechnicalIndicators.calculate_support_resistance(df, lookback=20, num_levels=2)
        else:
            return TechnicalIndicators.calculate_support_resistance(df, lookback=50, num_levels=3)


# Convenience function to check if pandas_ta is available
def is_pandas_ta_available() -> bool:
    """Check if pandas_ta library is installed"""
    return PANDAS_TA_AVAILABLE

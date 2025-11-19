"""
Data Fetcher Module
Fetches and manages candlestick data for multiple timeframes
"""

import pandas as pd
from typing import Dict, List
import logging
from datetime import datetime
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches and manages market data for multiple timeframes"""

    def __init__(self, client: CoinDCXFuturesClient):
        self.client = client
        self.data_cache = {}

    def fetch_candles(self, pair: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch candlestick data and convert to DataFrame

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (5m, 1h, 4h)
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data
        """
        try:
            logger.info(f"Fetching {interval} candles for {pair}")
            candles = self.client.get_candlestick_data(pair, interval, limit)

            if not candles:
                logger.warning(f"No candle data received for {pair} {interval}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(candles)

            # Expected columns: timestamp, open, high, low, close, volume
            # Ensure proper column names and types
            if 'time' in df.columns:
                df.rename(columns={'time': 'timestamp'}, inplace=True)

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Ensure numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Sort by timestamp
            df.sort_values('timestamp', inplace=True)
            df.reset_index(drop=True, inplace=True)

            logger.info(f"Fetched {len(df)} candles for {pair} {interval}")
            return df

        except Exception as e:
            logger.error(f"Error fetching candles for {pair} {interval}: {e}")
            return pd.DataFrame()

    def fetch_multi_timeframe_data(self, pair: str, timeframes: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes

        Args:
            pair: Trading pair
            timeframes: Dict of timeframe names and intervals

        Returns:
            Dict of DataFrames for each timeframe
        """
        multi_tf_data = {}

        for tf_name, interval in timeframes.items():
            df = self.fetch_candles(pair, interval)
            if not df.empty:
                multi_tf_data[tf_name] = df
                # Cache the data
                cache_key = f"{pair}_{interval}"
                self.data_cache[cache_key] = {
                    'data': df,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning(f"Failed to fetch data for {pair} {tf_name} ({interval})")

        return multi_tf_data

    def get_latest_price(self, pair: str) -> float:
        """Get the latest price for a trading pair"""
        try:
            ticker = self.client.get_ticker(pair)
            return float(ticker.get('last_price', 0))
        except Exception as e:
            logger.error(f"Error getting latest price for {pair}: {e}")
            return 0.0

    def get_cached_data(self, pair: str, interval: str, max_age_seconds: int = 60) -> pd.DataFrame:
        """
        Get cached data if available and fresh

        Args:
            pair: Trading pair
            interval: Timeframe
            max_age_seconds: Maximum age of cached data in seconds

        Returns:
            Cached DataFrame or empty DataFrame
        """
        cache_key = f"{pair}_{interval}"

        if cache_key in self.data_cache:
            cached = self.data_cache[cache_key]
            age = (datetime.now() - cached['timestamp']).total_seconds()

            if age < max_age_seconds:
                logger.debug(f"Using cached data for {pair} {interval} (age: {age}s)")
                return cached['data']

        return pd.DataFrame()

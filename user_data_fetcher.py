"""
Per-User Data Fetcher Module
Provides user-isolated data fetching with per-user caching
"""

import pandas as pd
from typing import Dict, Optional
import logging
from datetime import datetime
from flask_login import current_user
from coindcx_client import CoinDCXFuturesClient
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class UserDataFetcher:
    """
    User-isolated data fetcher with per-user caching.
    Each user has their own isolated cache to prevent data leakage.
    """

    def __init__(self, user_id: int, client: CoinDCXFuturesClient):
        """
        Initialize data fetcher for a specific user.

        Args:
            user_id: The user's database ID
            client: CoinDCX client (can be user-specific or default)
        """
        self.user_id = user_id
        self.client = client
        self.data_cache: Dict[str, Dict] = {}
        self._base_fetcher = DataFetcher(client)
        logger.debug(f"Created UserDataFetcher for user {user_id}")

    def fetch_candles(self, pair: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch candlestick data for this user.

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (5m, 1h, 4h)
            limit: Number of candles

        Returns:
            DataFrame with OHLCV data
        """
        return self._base_fetcher.fetch_candles(pair, interval, limit)

    def fetch_multi_timeframe_data(self, pair: str, timeframes: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes with user-isolated caching.

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
                # Cache with user-specific key
                cache_key = f"{self.user_id}_{pair}_{interval}"
                self.data_cache[cache_key] = {
                    'data': df,
                    'timestamp': datetime.now()
                }
            else:
                logger.warning(f"User {self.user_id}: Failed to fetch data for {pair} {tf_name} ({interval})")

        return multi_tf_data

    def get_latest_price(self, pair: str) -> float:
        """
        Get the latest price for a trading pair.

        Args:
            pair: Trading pair in standard format (e.g., 'BTCUSDT')

        Returns:
            Current market price as float
        """
        return self._base_fetcher.get_latest_price(pair)

    def get_cached_data(self, pair: str, interval: str, max_age_seconds: int = 60) -> pd.DataFrame:
        """
        Get user-specific cached data if available and fresh.

        Args:
            pair: Trading pair
            interval: Timeframe
            max_age_seconds: Maximum age of cached data in seconds

        Returns:
            Cached DataFrame or empty DataFrame
        """
        cache_key = f"{self.user_id}_{pair}_{interval}"

        if cache_key in self.data_cache:
            cached = self.data_cache[cache_key]
            age = (datetime.now() - cached['timestamp']).total_seconds()

            if age < max_age_seconds:
                logger.debug(f"User {self.user_id}: Using cached data for {pair} {interval} (age: {age}s)")
                return cached['data']

        return pd.DataFrame()

    def clear_cache(self):
        """Clear all cached data for this user"""
        self.data_cache.clear()
        logger.info(f"User {self.user_id}: Cleared data cache")

    def clear_cache_for_pair(self, pair: str):
        """Clear cached data for a specific pair"""
        keys_to_delete = [k for k in self.data_cache.keys() if k.startswith(f"{self.user_id}_{pair}_")]
        for key in keys_to_delete:
            del self.data_cache[key]
        logger.debug(f"User {self.user_id}: Cleared cache for {pair}")

    @staticmethod
    def convert_to_coindcx_symbol(symbol: str) -> str:
        """Convert standard symbol to CoinDCX futures format"""
        return DataFetcher.convert_to_coindcx_symbol(symbol)

    @staticmethod
    def convert_interval_to_resolution(interval: str) -> str:
        """Convert timeframe interval to CoinDCX resolution format"""
        return DataFetcher.convert_interval_to_resolution(interval)


# Cache of user data fetchers
_user_data_fetchers: Dict[int, UserDataFetcher] = {}


def get_user_data_fetcher(user_id: int = None, client: CoinDCXFuturesClient = None) -> UserDataFetcher:
    """
    Get or create a data fetcher for the specified user.

    Args:
        user_id: User ID. If None, uses current_user.id
        client: CoinDCX client. If None, uses default client

    Returns:
        UserDataFetcher instance for the user
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("No user ID provided and no authenticated user")
        user_id = user_id or current_user.id

    # Check if we need to create a new instance (user ID changed or client changed)
    if user_id in _user_data_fetchers:
        existing = _user_data_fetchers[user_id]
        # If client is provided and different, recreate
        if client is not None and existing.client is not client:
            _user_data_fetchers[user_id] = UserDataFetcher(user_id, client)
    else:
        if client is None:
            # Import here to avoid circular imports
            import config
            from coindcx_client import CoinDCXFuturesClient
            client = CoinDCXFuturesClient(
                api_key=config.API_KEY,
                api_secret=config.API_SECRET,
                base_url=config.BASE_URL
            )
        _user_data_fetchers[user_id] = UserDataFetcher(user_id, client)

    return _user_data_fetchers[user_id]


def clear_user_data_fetcher_cache(user_id: int = None):
    """Clear cached data fetcher(s)"""
    global _user_data_fetchers
    if user_id:
        if user_id in _user_data_fetchers:
            _user_data_fetchers[user_id].clear_cache()
            del _user_data_fetchers[user_id]
    else:
        for fetcher in _user_data_fetchers.values():
            fetcher.clear_cache()
        _user_data_fetchers.clear()

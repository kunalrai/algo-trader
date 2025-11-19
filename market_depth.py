"""
Market Depth & Liquidity Analysis Module
Analyzes order book depth, liquidity, and market maker behavior
"""

import logging
from typing import Dict, List, Tuple
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class MarketDepthAnalyzer:
    """Analyze order book depth and liquidity metrics"""

    def __init__(self, client: CoinDCXFuturesClient):
        self.client = client

    def analyze_orderbook(self, pair: str, depth: int = 50) -> Dict:
        """
        Comprehensive order book analysis

        Args:
            pair: Trading pair in CoinDCX format (e.g., 'B-BTC_USDT')
            depth: Order book depth to fetch

        Returns:
            Dict with all liquidity metrics
        """
        try:
            # Get order book
            orderbook = self.client.get_orderbook(pair, depth)

            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                logger.warning(f"Invalid order book data for {pair}")
                return self._empty_analysis()

            bids = orderbook.get('bids', {})
            asks = orderbook.get('asks', {})

            if not bids or not asks:
                logger.warning(f"Empty order book for {pair}")
                return self._empty_analysis()

            # Parse bids and asks
            bid_levels = self._parse_levels(bids)
            ask_levels = self._parse_levels(asks)

            # Calculate metrics
            best_bid = max(bid_levels, key=lambda x: x[0]) if bid_levels else (0, 0)
            best_ask = min(ask_levels, key=lambda x: x[0]) if ask_levels else (0, 0)

            mid_price = (best_bid[0] + best_ask[0]) / 2 if best_bid[0] and best_ask[0] else 0

            spread = best_ask[0] - best_bid[0]
            spread_pct = (spread / mid_price * 100) if mid_price else 0

            # Order book imbalance
            imbalance_data = self._calculate_imbalance(bid_levels, ask_levels, mid_price)

            # Market depth
            depth_data = self._calculate_depth(bid_levels, ask_levels, mid_price)

            # Large orders (potential walls)
            large_orders = self._detect_large_orders(bid_levels, ask_levels)

            analysis = {
                'pair': pair,
                'timestamp': orderbook.get('ts', 0),
                'mid_price': round(mid_price, 2),
                'best_bid': round(best_bid[0], 2),
                'best_ask': round(best_ask[0], 2),
                'spread': round(spread, 2),
                'spread_pct': round(spread_pct, 4),
                'spread_status': self._classify_spread(spread_pct),
                'bid_volume': imbalance_data['bid_volume'],
                'ask_volume': imbalance_data['ask_volume'],
                'imbalance_ratio': imbalance_data['imbalance_ratio'],
                'imbalance_status': imbalance_data['status'],
                'depth_2pct': depth_data['depth_2pct'],
                'depth_5pct': depth_data['depth_5pct'],
                'liquidity_status': depth_data['liquidity_status'],
                'large_bid_wall': large_orders['large_bid'],
                'large_ask_wall': large_orders['large_ask'],
                'market_maker_signal': large_orders['signal']
            }

            logger.debug(f"Order book analysis for {pair}: Spread={spread_pct:.4f}%, Imbalance={imbalance_data['imbalance_ratio']:.2f}")

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing order book for {pair}: {e}")
            return self._empty_analysis()

    def _parse_levels(self, levels: Dict) -> List[Tuple[float, float]]:
        """
        Parse order book levels into list of (price, quantity) tuples

        Args:
            levels: Dict of price: quantity strings

        Returns:
            List of (price, quantity) tuples sorted by price
        """
        try:
            parsed = [
                (float(price), float(quantity))
                for price, quantity in levels.items()
            ]
            return sorted(parsed, key=lambda x: x[0])
        except Exception as e:
            logger.error(f"Error parsing order book levels: {e}")
            return []

    def _calculate_imbalance(self, bids: List[Tuple], asks: List[Tuple], mid_price: float, threshold_pct: float = 2.0) -> Dict:
        """
        Calculate order book imbalance within threshold % of mid price

        Args:
            bids: List of (price, quantity) bid tuples
            asks: List of (price, quantity) ask tuples
            mid_price: Current mid price
            threshold_pct: Percentage threshold for depth calculation

        Returns:
            Dict with imbalance metrics
        """
        threshold = mid_price * (threshold_pct / 100)

        # Sum volume within threshold
        bid_volume = sum(
            qty for price, qty in bids
            if price >= (mid_price - threshold)
        )

        ask_volume = sum(
            qty for price, qty in asks
            if price <= (mid_price + threshold)
        )

        total_volume = bid_volume + ask_volume
        imbalance_ratio = bid_volume / total_volume if total_volume > 0 else 0.5

        # Classify imbalance
        if imbalance_ratio > 0.60:
            status = 'bullish'
        elif imbalance_ratio < 0.40:
            status = 'bearish'
        else:
            status = 'neutral'

        return {
            'bid_volume': round(bid_volume, 2),
            'ask_volume': round(ask_volume, 2),
            'imbalance_ratio': round(imbalance_ratio, 2),
            'status': status
        }

    def _calculate_depth(self, bids: List[Tuple], asks: List[Tuple], mid_price: float) -> Dict:
        """
        Calculate market depth at various percentage levels

        Args:
            bids: List of (price, quantity) bid tuples
            asks: List of (price, quantity) ask tuples
            mid_price: Current mid price

        Returns:
            Dict with depth metrics
        """
        # 2% depth
        threshold_2 = mid_price * 0.02
        depth_2pct = sum(qty for price, qty in bids if price >= (mid_price - threshold_2))
        depth_2pct += sum(qty for price, qty in asks if price <= (mid_price + threshold_2))

        # 5% depth
        threshold_5 = mid_price * 0.05
        depth_5pct = sum(qty for price, qty in bids if price >= (mid_price - threshold_5))
        depth_5pct += sum(qty for price, qty in asks if price <= (mid_price + threshold_5))

        # Calculate depth in USD (approximate)
        depth_2pct_usd = depth_2pct * mid_price
        depth_5pct_usd = depth_5pct * mid_price

        # Classify liquidity
        if depth_2pct_usd > 500000:
            liquidity_status = 'high'
        elif depth_2pct_usd > 100000:
            liquidity_status = 'medium'
        else:
            liquidity_status = 'low'

        return {
            'depth_2pct': round(depth_2pct, 2),
            'depth_5pct': round(depth_5pct, 2),
            'depth_2pct_usd': round(depth_2pct_usd, 0),
            'depth_5pct_usd': round(depth_5pct_usd, 0),
            'liquidity_status': liquidity_status
        }

    def _detect_large_orders(self, bids: List[Tuple], asks: List[Tuple]) -> Dict:
        """
        Detect large orders (potential market maker walls)

        Args:
            bids: List of (price, quantity) bid tuples
            asks: List of (price, quantity) ask tuples

        Returns:
            Dict with large order detection
        """
        if not bids or not asks:
            return {
                'large_bid': None,
                'large_ask': None,
                'signal': 'neutral'
            }

        # Calculate average order size
        all_orders = [qty for _, qty in bids] + [qty for _, qty in asks]
        avg_size = sum(all_orders) / len(all_orders) if all_orders else 0
        large_threshold = avg_size * 3  # 3x average = large order

        # Find largest bid and ask
        largest_bid = max(bids, key=lambda x: x[1]) if bids else (0, 0)
        largest_ask = max(asks, key=lambda x: x[1]) if asks else (0, 0)

        large_bid = None
        if largest_bid[1] > large_threshold:
            large_bid = {
                'price': round(largest_bid[0], 2),
                'size': round(largest_bid[1], 2),
                'strength': 'strong' if largest_bid[1] > large_threshold * 2 else 'medium'
            }

        large_ask = None
        if largest_ask[1] > large_threshold:
            large_ask = {
                'price': round(largest_ask[0], 2),
                'size': round(largest_ask[1], 2),
                'strength': 'strong' if largest_ask[1] > large_threshold * 2 else 'medium'
            }

        # Determine signal
        signal = 'neutral'
        if large_bid and not large_ask:
            signal = 'bullish'
        elif large_ask and not large_bid:
            signal = 'bearish'
        elif large_bid and large_ask:
            # Both walls present - range bound
            signal = 'range_bound'

        return {
            'large_bid': large_bid,
            'large_ask': large_ask,
            'signal': signal
        }

    def _classify_spread(self, spread_pct: float) -> str:
        """Classify spread as tight, normal, or wide"""
        if spread_pct < 0.05:
            return 'tight'
        elif spread_pct < 0.2:
            return 'normal'
        else:
            return 'wide'

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            'pair': '',
            'timestamp': 0,
            'mid_price': 0,
            'best_bid': 0,
            'best_ask': 0,
            'spread': 0,
            'spread_pct': 0,
            'spread_status': 'unknown',
            'bid_volume': 0,
            'ask_volume': 0,
            'imbalance_ratio': 0.5,
            'imbalance_status': 'neutral',
            'depth_2pct': 0,
            'depth_5pct': 0,
            'liquidity_status': 'unknown',
            'large_bid_wall': None,
            'large_ask_wall': None,
            'market_maker_signal': 'neutral'
        }

    def get_volume_analysis(self, pair: str) -> Dict:
        """
        Analyze 24h volume and volume trends

        Args:
            pair: Trading pair in CoinDCX format

        Returns:
            Dict with volume metrics
        """
        try:
            prices_data = self.client.get_current_prices_realtime()

            if 'prices' not in prices_data or pair not in prices_data['prices']:
                logger.warning(f"No price data found for {pair}")
                return {
                    'volume_24h': 0,
                    'volume_24h_usd': 0,
                    'volume_status': 'unknown'
                }

            instrument_data = prices_data['prices'][pair]

            volume_24h = float(instrument_data.get('v', 0))
            last_price = float(instrument_data.get('ls', 0))
            volume_24h_usd = volume_24h * last_price

            # Classify volume (these thresholds are examples, adjust based on market)
            if volume_24h_usd > 100_000_000:  # $100M+
                volume_status = 'high'
            elif volume_24h_usd > 10_000_000:  # $10M+
                volume_status = 'medium'
            else:
                volume_status = 'low'

            return {
                'volume_24h': round(volume_24h, 2),
                'volume_24h_usd': round(volume_24h_usd, 0),
                'volume_status': volume_status,
                'price_change_pct': round(float(instrument_data.get('pc', 0)), 2)
            }

        except Exception as e:
            logger.error(f"Error analyzing volume for {pair}: {e}")
            return {
                'volume_24h': 0,
                'volume_24h_usd': 0,
                'volume_status': 'unknown'
            }

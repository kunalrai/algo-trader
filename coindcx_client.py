"""
CoinDCX Futures API Client
Handles authentication and API communication with CoinDCX Futures platform
"""

import hashlib
import hmac
import json
import time
import requests
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CoinDCXFuturesClient:
    """CoinDCX Futures API Client with authentication and endpoints"""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.coindcx.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()

    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for authentication"""
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_headers(self, payload: str) -> Dict[str, str]:
        """Generate authenticated headers"""
        return {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': self._generate_signature(payload)
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to CoinDCX API"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url)
            else:
                # Add timestamp to payload
                if data is None:
                    data = {}
                data['timestamp'] = int(time.time() * 1000)

                payload = json.dumps(data, separators=(',', ':'))
                headers = self._get_headers(payload)

                response = self.session.post(url, data=payload, headers=headers)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    # Market Data Methods

    def get_candlestick_data(self, pair: str, interval: str, limit: int = 500) -> List[Dict]:
        """
        Get candlestick data for technical analysis

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (5m, 1h, 4h, etc.)
            limit: Number of candles to fetch

        Returns:
            List of candlestick data
        """
        endpoint = "/market_data/candles"
        params = {
            "pair": pair,
            "interval": interval,
            "limit": limit
        }
        return self._make_request("GET", f"{endpoint}?pair={pair}&interval={interval}&limit={limit}")

    def get_ticker(self, pair: str) -> Dict:
        """Get current ticker price for a pair"""
        endpoint = "/market_data/ticker"
        return self._make_request("GET", f"{endpoint}?pair={pair}")

    # Wallet Methods

    def get_futures_balance(self) -> Dict:
        """Get futures wallet balance"""
        endpoint = "/futures/get_balance"
        return self._make_request("POST", endpoint, {})

    def get_wallet_details(self) -> Dict:
        """Get detailed wallet information"""
        endpoint = "/futures/wallet_details"
        return self._make_request("POST", endpoint, {})

    # Position Methods

    def get_positions(self, pair: Optional[str] = None) -> List[Dict]:
        """
        Get all active positions or positions for a specific pair

        Args:
            pair: Optional trading pair filter

        Returns:
            List of active positions
        """
        endpoint = "/futures/get_positions"
        data = {}
        if pair:
            data['pair'] = pair
        return self._make_request("POST", endpoint, data)

    def get_position_by_id(self, position_id: str) -> Dict:
        """Get specific position by ID"""
        endpoint = "/futures/get_position"
        data = {'position_id': position_id}
        return self._make_request("POST", endpoint, data)

    def close_position(self, position_id: str) -> Dict:
        """Close an entire position"""
        endpoint = "/futures/exit_position"
        data = {'position_id': position_id}
        return self._make_request("POST", endpoint, data)

    def update_leverage(self, pair: str, leverage: int) -> Dict:
        """Update leverage for a trading pair"""
        endpoint = "/futures/update_leverage"
        data = {
            'pair': pair,
            'leverage': leverage
        }
        return self._make_request("POST", endpoint, data)

    def add_margin(self, position_id: str, margin: float) -> Dict:
        """Add margin to an existing position"""
        endpoint = "/futures/add_margin"
        data = {
            'position_id': position_id,
            'margin': margin
        }
        return self._make_request("POST", endpoint, data)

    # Order Methods

    def create_order(self,
                    pair: str,
                    side: str,
                    order_type: str,
                    size: float,
                    price: Optional[float] = None,
                    stop_price: Optional[float] = None,
                    take_profit: Optional[float] = None,
                    stop_loss: Optional[float] = None,
                    time_in_force: str = "GTC") -> Dict:
        """
        Create a new futures order

        Args:
            pair: Trading pair
            side: 'long' or 'short'
            order_type: 'market_order' or 'limit_order'
            size: Order size
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            take_profit: Take profit price
            stop_loss: Stop loss price
            time_in_force: GTC, IOC, FOK

        Returns:
            Order creation response
        """
        endpoint = "/futures/create_order"
        data = {
            'pair': pair,
            'side': side,
            'order_type': order_type,
            'size': size,
            'time_in_force': time_in_force
        }

        if price:
            data['price'] = price
        if stop_price:
            data['stop_price'] = stop_price
        if take_profit:
            data['take_profit'] = take_profit
        if stop_loss:
            data['stop_loss'] = stop_loss

        return self._make_request("POST", endpoint, data)

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel a specific order"""
        endpoint = "/futures/cancel_order"
        data = {'order_id': order_id}
        return self._make_request("POST", endpoint, data)

    def cancel_all_orders(self, pair: Optional[str] = None) -> Dict:
        """Cancel all orders, optionally filtered by pair"""
        endpoint = "/futures/cancel_all_orders"
        data = {}
        if pair:
            data['pair'] = pair
        return self._make_request("POST", endpoint, data)

    def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        endpoint = "/futures/get_open_orders"
        data = {}
        if pair:
            data['pair'] = pair
        return self._make_request("POST", endpoint, data)

    def edit_order(self, order_id: str, price: Optional[float] = None,
                   size: Optional[float] = None) -> Dict:
        """Edit an existing order"""
        endpoint = "/futures/edit_order"
        data = {'order_id': order_id}
        if price:
            data['price'] = price
        if size:
            data['size'] = size
        return self._make_request("POST", endpoint, data)

    # TP/SL Methods

    def create_take_profit_order(self, position_id: str, price: float, size: float) -> Dict:
        """Create take profit order for a position"""
        endpoint = "/futures/create_tp_order"
        data = {
            'position_id': position_id,
            'price': price,
            'size': size
        }
        return self._make_request("POST", endpoint, data)

    def create_stop_loss_order(self, position_id: str, price: float, size: float) -> Dict:
        """Create stop loss order for a position"""
        endpoint = "/futures/create_sl_order"
        data = {
            'position_id': position_id,
            'price': price,
            'size': size
        }
        return self._make_request("POST", endpoint, data)

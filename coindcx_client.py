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

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, authenticated: bool = True) -> Dict:
        """Make request to CoinDCX API (authenticated or public)"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                if authenticated:
                    # Authenticated GET request - send JSON body with signature
                    if data is None:
                        data = {}
                    data['timestamp'] = int(time.time() * 1000)

                    payload = json.dumps(data, separators=(',', ':'))
                    headers = self._get_headers(payload)

                    # For authenticated GET, CoinDCX expects JSON in request body
                    response = requests.get(url, headers=headers, data=payload)
                else:
                    # Public GET request
                    response = self.session.get(url)
            else:
                # POST request (always authenticated)
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

    def get_active_instruments(self, margin_currency: str = "USDT") -> List[str]:
        """
        Get list of active trading instruments for futures

        Args:
            margin_currency: Margin currency - "USDT" or "INR" (default: "USDT")

        Returns:
            List of active instrument pairs
            [
                "B-VANRY_USDT",
                "B-BTC_USDT",
                "B-ETH_USDT",
                ...
            ]
        """
        url = f"https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments?margin_currency_short_name[]={margin_currency}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch active instruments: {e}")
            raise

    def get_candlestick_data(self, pair: str, resolution: str, from_timestamp: int, to_timestamp: int, pcode: str = "f") -> Dict:
        """
        Get candlestick data for technical analysis

        Args:
            pair: Trading pair in format 'B-SYMBOL_USDT' (e.g., 'B-BTC_USDT')
            resolution: Timeframe - '1' (1min), '5' (5min), '60' (1hour), '1D' (1day)
            from_timestamp: Start time in Unix timestamp (seconds)
            to_timestamp: End time in Unix timestamp (seconds)
            pcode: Product code - 'f' for futures (default)

        Returns:
            Dict with status and candlestick data
            {
                "s": "ok",
                "data": [
                    {
                        "open": float,
                        "high": float,
                        "low": float,
                        "volume": float,
                        "close": float,
                        "time": int  # timestamp in milliseconds
                    },
                    ...
                ]
            }
        """
        url = "https://public.coindcx.com/market_data/candlesticks"
        params = {
            "pair": pair,
            "from": from_timestamp,
            "to": to_timestamp,
            "resolution": resolution,
            "pcode": pcode
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("s") != "ok":
                logger.error(f"Candlestick API returned error status: {data}")
                raise Exception(f"API error: {data}")

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch candlestick data: {e}")
            raise

    def get_ticker(self, pair: str) -> Dict:
        """Get current ticker price for a pair"""
        endpoint = "/market_data/ticker"
        return self._make_request("GET", f"{endpoint}?pair={pair}")

    def get_current_prices_realtime(self) -> Dict:
        """
        Get real-time current prices for all futures instruments

        Returns:
            Dict with timestamp, version, and prices for all instruments
            {
                "ts": 1720429586580,  # timestamp
                "vs": 54009972,  # version
                "prices": {
                    "B-BTC_USDT": {
                        "fr": 5e-05,  # funding rate
                        "h": 0.4027,  # 24h high
                        "l": 0.3525,  # 24h low
                        "v": 18568384.9349,  # 24h volume
                        "ls": 0.4012,  # last price
                        "pc": 4.834,  # price change %
                        "mkt": "BTCUSDT",  # market
                        "btST": 1720429583629,  # binance timestamp
                        "ctRT": 1720429584517,  # coindcx timestamp
                        "skw": -207,  # skew
                        "mp": 0.40114525,  # mark price
                        "efr": 5e-05,  # effective funding rate
                        "bmST": 1720429586000,  # binance market timestamp
                        "cmRT": 1720429586117  # coindcx market timestamp
                    },
                    ...
                }
            }
        """
        url = "https://public.coindcx.com/market_data/v3/current_prices/futures/rt"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch real-time prices: {e}")
            raise

    def get_orderbook(self, pair: str, depth: int = 50) -> Dict:
        """
        Get order book depth for a futures pair

        Args:
            pair: Trading pair in CoinDCX format (e.g., 'B-BTC_USDT')
            depth: Order book depth - 10, 20, or 50 (default: 50)

        Returns:
            Dict with order book data
            {
                "ts": 1705483019891,  # timestamp
                "vs": 27570132,       # version
                "asks": {
                    "2001": "2.145",  # price: quantity
                    "2002": "4.453",
                    "2003": "2.997"
                },
                "bids": {
                    "1995": "2.618",  # price: quantity
                    "1996": "1.55"
                }
            }
        """
        # Validate depth parameter
        if depth not in [10, 20, 50]:
            logger.warning(f"Invalid depth {depth}, using 50")
            depth = 50

        url = f"https://public.coindcx.com/market_data/v3/orderbook/{pair}-futures/{depth}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch order book for {pair}: {e}")
            raise

    def get_recent_trades(self, pair: str, limit: int = 100) -> List[Dict]:
        """
        Get recent trades for a futures pair

        Args:
            pair: Trading pair in CoinDCX format (e.g., 'B-BTC_USDT')
            limit: Number of recent trades to fetch (default: 100)

        Returns:
            List of recent trades
            [
                {
                    "p": 45950.5,    # price
                    "q": 0.5,        # quantity
                    "T": 1705483019891,  # timestamp
                    "m": false       # true if buyer is maker (sell), false if taker (buy)
                },
                ...
            ]
        """
        url = f"https://public.coindcx.com/market_data/trade_history"
        params = {
            'pair': pair,
            'limit': limit
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch trade history for {pair}: {e}")
            raise

    # Currency Conversion Methods

    def get_currency_conversions(self) -> List[Dict]:
        """
        Get currency conversion rates for futures trading

        Returns:
            List of conversion rates
            [
                {
                    "symbol": "USDTINR",
                    "margin_currency_short_name": "INR",
                    "target_currency_short_name": "USDT",
                    "conversion_price": 89.0,
                    "last_updated_at": 1728460492399
                },
                ...
            ]
        """
        endpoint = "/api/v1/derivatives/futures/data/conversions"
        return self._make_request("GET", endpoint, {})

    # Wallet Methods

    def get_futures_balance(self) -> List[Dict]:
        """
        Get futures wallet balance (alias for get_wallet_details)

        Returns:
            List of wallet details per currency
        """
        return self.get_wallet_details()

    def get_wallet_details(self) -> List[Dict]:
        """
        Get detailed wallet information for futures trading

        Returns:
            List of wallet details per currency
            [
                {
                    "id": "uuid",
                    "currency_short_name": "USDT",
                    "balance": "6.1693226",
                    "locked_balance": "0.0",
                    "cross_order_margin": "0.0",
                    "cross_user_margin": "0.68534648"
                },
                ...
            ]
        """
        endpoint = "/exchange/v1/derivatives/futures/wallets"
        return self._make_request("GET", endpoint, {})

    # Position Methods

    def get_positions(self,
                     pair: Optional[str] = None,
                     margin_currency: Optional[List[str]] = None,
                     page: int = 1,
                     size: int = 100) -> List[Dict]:
        """
        Get all active positions or positions for a specific pair

        Args:
            pair: Optional trading pair filter (CoinDCX format: 'B-BTC_USDT')
            margin_currency: List of margin currencies to filter (e.g., ["USDT", "INR"])
            page: Page number for pagination (default: 1)
            size: Number of positions per page (default: 100)

        Returns:
            List of positions with details:
            [
                {
                    "id": "position-id",
                    "pair": "B-BNB_USDT",
                    "active_pos": 0.0,
                    "inactive_pos_buy": 0.0,
                    "inactive_pos_sell": 0.0,
                    "avg_price": 0.0,
                    "liquidation_price": 0.0,
                    "locked_margin": 0.0,
                    "locked_user_margin": 0.0,
                    "locked_order_margin": 0.0,
                    "take_profit_trigger": null,
                    "stop_loss_trigger": null,
                    "leverage": 10.0,
                    "maintenance_margin": 0.0,
                    "mark_price": 0.0,
                    "margin_type": "crossed",
                    "settlement_currency_avg_price": 0.0,
                    "margin_currency_short_name": "USDT",
                    "updated_at": 1717754279737
                },
                ...
            ]
        """
        endpoint = "/exchange/v1/derivatives/futures/positions"
        data = {
            'page': str(page),
            'size': str(size)
        }

        if pair:
            data['pair'] = pair

        if margin_currency:
            data['margin_currency_short_name'] = margin_currency
        else:
            # Default to USDT if not specified
            data['margin_currency_short_name'] = ["USDT"]

        return self._make_request("POST", endpoint, data)

    def get_position_by_id(self, position_id: str) -> Dict:
        """Get specific position by ID"""
        endpoint = "/futures/get_position"
        data = {'position_id': position_id}
        return self._make_request("POST", endpoint, data)

    def close_position(self, position_id: str) -> Dict:
        """
        Close an entire position

        Args:
            position_id: The position ID to close

        Returns:
            Response with status and group_id
            {
                "message": "success",
                "status": 200,
                "code": 200,
                "data": {
                    "group_id": "baf926e6B-ID_USDT1705647709"
                }
            }
        """
        endpoint = "/exchange/v1/derivatives/futures/positions/exit"
        data = {
            'timestamp': int(time.time() * 1000),
            'id': position_id
        }
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
                    total_quantity: float,
                    leverage: int,
                    price: Optional[float] = None,
                    stop_price: Optional[float] = None,
                    take_profit_price: Optional[float] = None,
                    stop_loss_price: Optional[float] = None,
                    time_in_force: str = "good_till_cancel",
                    notification: str = "no_notification",
                    hidden: bool = False,
                    post_only: bool = False) -> Dict:
        """
        Create a new futures order

        Args:
            pair: Trading pair in format 'B-SYMBOL_USDT' (e.g., 'B-BTC_USDT')
            side: 'buy' or 'sell'
            order_type: 'market_order' or 'limit_order'
            total_quantity: Order quantity
            leverage: Leverage multiplier (e.g., 10 for 10x)
            price: Limit price (required for limit orders)
            stop_price: Stop trigger price (for stop orders)
            take_profit_price: Take profit price
            stop_loss_price: Stop loss price
            time_in_force: 'good_till_cancel', 'fill_or_kill', or 'immediate_or_cancel'
            notification: 'no_notification', 'email_notification', or 'push_notification'
            hidden: Hide order from order book
            post_only: Post-only order (maker only)

        Returns:
            List with order creation response
        """
        endpoint = "/exchange/v1/derivatives/futures/orders/create"

        # Build order object
        order = {
            'side': side,
            'pair': pair,
            'order_type': order_type,
            'total_quantity': total_quantity,
            'leverage': leverage,
            'time_in_force': time_in_force,
            'notification': notification,
            'hidden': hidden,
            'post_only': post_only
        }

        # Add optional price fields
        if price is not None:
            order['price'] = str(price)
        if stop_price is not None:
            order['stop_price'] = str(stop_price)
        if take_profit_price is not None:
            order['take_profit_price'] = take_profit_price
        if stop_loss_price is not None:
            order['stop_loss_price'] = stop_loss_price

        # Wrap in timestamp body
        data = {
            'timestamp': int(time.time() * 1000),
            'order': order
        }

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

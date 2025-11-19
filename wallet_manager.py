"""
Wallet Manager Module
Manages futures wallet balance and provides balance checking functionality
"""

from typing import Dict, Optional
import logging
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class WalletManager:
    """Manage futures wallet balance and operations"""

    def __init__(self, client: CoinDCXFuturesClient):
        self.client = client
        self.cached_balance = None
        self.last_balance_check = None

    def get_futures_balance(self) -> Optional[Dict]:
        """
        Get futures wallet balance

        Returns:
            Dict with balance information
        """
        try:
            balance_response = self.client.get_futures_balance()
            logger.info(f"Futures balance retrieved: {balance_response}")

            # Parse balance response
            # Expected structure may vary, adjust based on actual API response
            if isinstance(balance_response, dict):
                self.cached_balance = balance_response
                return balance_response
            elif isinstance(balance_response, list) and len(balance_response) > 0:
                self.cached_balance = balance_response[0]
                return balance_response[0]

            logger.warning("Unexpected balance response format")
            return None

        except Exception as e:
            logger.error(f"Error getting futures balance: {e}")
            return None

    def get_available_balance(self) -> float:
        """
        Get available balance for trading

        Returns:
            Available balance as float
        """
        try:
            balance = self.get_futures_balance()

            if not balance:
                logger.warning("No balance data available")
                return 0.0

            # Try different possible field names
            available = (
                balance.get('available_balance') or
                balance.get('available') or
                balance.get('free') or
                balance.get('balance') or
                0.0
            )

            available_float = float(available)
            logger.info(f"Available balance: {available_float}")

            return available_float

        except Exception as e:
            logger.error(f"Error getting available balance: {e}")
            return 0.0

    def get_total_balance(self) -> float:
        """
        Get total futures wallet balance (including margin)

        Returns:
            Total balance as float
        """
        try:
            balance = self.get_futures_balance()

            if not balance:
                return 0.0

            # Try different possible field names
            total = (
                balance.get('total_balance') or
                balance.get('total') or
                balance.get('balance') or
                0.0
            )

            return float(total)

        except Exception as e:
            logger.error(f"Error getting total balance: {e}")
            return 0.0

    def get_margin_details(self) -> Optional[Dict]:
        """
        Get detailed margin information

        Returns:
            Dict with margin details
        """
        try:
            wallet_details = self.client.get_wallet_details()
            logger.debug(f"Wallet details: {wallet_details}")
            return wallet_details

        except Exception as e:
            logger.error(f"Error getting margin details: {e}")
            return None

    def check_sufficient_balance(self, required_amount: float) -> bool:
        """
        Check if there's sufficient balance for a trade

        Args:
            required_amount: Required balance amount

        Returns:
            True if sufficient balance available
        """
        try:
            available = self.get_available_balance()

            if available >= required_amount:
                logger.info(f"Sufficient balance: {available} >= {required_amount}")
                return True
            else:
                logger.warning(
                    f"Insufficient balance: {available} < {required_amount}"
                )
                return False

        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return False

    def get_balance_summary(self) -> Dict:
        """
        Get comprehensive balance summary

        Returns:
            Dict with balance summary
        """
        try:
            available = self.get_available_balance()
            total = self.get_total_balance()
            margin_details = self.get_margin_details()

            summary = {
                'available_balance': available,
                'total_balance': total,
                'used_margin': total - available if total > available else 0.0,
                'margin_details': margin_details
            }

            logger.info(
                f"Balance summary - Available: {available}, "
                f"Total: {total}, Used: {summary['used_margin']}"
            )

            return summary

        except Exception as e:
            logger.error(f"Error getting balance summary: {e}")
            return {
                'available_balance': 0.0,
                'total_balance': 0.0,
                'used_margin': 0.0,
                'margin_details': None
            }

    def calculate_max_position_value(self, max_percent: float, leverage: int) -> float:
        """
        Calculate maximum position value based on available balance

        Args:
            max_percent: Maximum percentage of balance to use
            leverage: Leverage multiplier

        Returns:
            Maximum position value
        """
        try:
            available = self.get_available_balance()
            max_value = (available * max_percent / 100) * leverage

            logger.info(
                f"Max position value: {max_value} "
                f"(Balance: {available}, Percent: {max_percent}%, Leverage: {leverage}x)"
            )

            return max_value

        except Exception as e:
            logger.error(f"Error calculating max position value: {e}")
            return 0.0

    def get_balance_health(self) -> Dict:
        """
        Check overall balance health and risk levels

        Returns:
            Dict with balance health metrics
        """
        try:
            summary = self.get_balance_summary()
            available = summary['available_balance']
            total = summary['total_balance']

            if total == 0:
                utilization = 0
            else:
                utilization = (summary['used_margin'] / total) * 100

            health_status = 'healthy'
            if utilization > 80:
                health_status = 'critical'
            elif utilization > 60:
                health_status = 'warning'

            health = {
                'status': health_status,
                'utilization_percent': utilization,
                'available_balance': available,
                'total_balance': total,
                'used_margin': summary['used_margin']
            }

            logger.info(
                f"Balance health: {health_status} "
                f"(Utilization: {utilization:.2f}%)"
            )

            return health

        except Exception as e:
            logger.error(f"Error checking balance health: {e}")
            return {
                'status': 'unknown',
                'utilization_percent': 0,
                'available_balance': 0,
                'total_balance': 0,
                'used_margin': 0
            }

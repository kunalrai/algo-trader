"""
Wallet Manager Module
Manages futures wallet balance and provides balance checking functionality
"""

from typing import Dict, Optional, List
import logging
from coindcx_client import CoinDCXFuturesClient

logger = logging.getLogger(__name__)


class WalletManager:
    """Manage futures wallet balance and operations"""

    def __init__(self, client: CoinDCXFuturesClient):
        self.client = client
        self.cached_balance = None
        self.last_balance_check = None

    def get_futures_balance(self, currency: str = "USDT") -> Optional[Dict]:
        """
        Get futures wallet balance for a specific currency

        Args:
            currency: Currency to get balance for (default: "USDT")

        Returns:
            Dict with balance information for the specified currency
        """
        try:
            balance_response = self.client.get_futures_balance()
            logger.info(f"Futures balance retrieved: {balance_response}")

            # API returns a list of wallets for different currencies
            if isinstance(balance_response, list):
                # Find the wallet for the requested currency
                for wallet in balance_response:
                    if wallet.get('currency_short_name') == currency:
                        self.cached_balance = wallet
                        logger.info(f"Found {currency} wallet: {wallet.get('balance')} {currency}")
                        return wallet

                logger.warning(f"No wallet found for currency: {currency}")
                # Return first wallet as fallback
                if len(balance_response) > 0:
                    self.cached_balance = balance_response[0]
                    return balance_response[0]
            elif isinstance(balance_response, dict):
                self.cached_balance = balance_response
                return balance_response

            logger.warning("Unexpected balance response format")
            return None

        except Exception as e:
            logger.error(f"Error getting futures balance: {e}")
            return None

    def get_available_balance(self) -> float:
        """
        Get available balance for trading (balance - locked_balance)

        Returns:
            Available balance as float
        """
        try:
            balance = self.get_futures_balance()

            if not balance:
                logger.warning("No balance data available")
                return 0.0

            # CoinDCX API returns: balance, locked_balance, cross_order_margin, cross_user_margin
            total = float(balance.get('balance', 0))
            locked = float(balance.get('locked_balance', 0))

            # Available balance = total balance - locked balance
            available = round(total - locked, 2)

            logger.info(f"Available balance: {available} USDT (Total: {total}, Locked: {locked})")

            return available

        except Exception as e:
            logger.error(f"Error getting available balance: {e}")
            return 0.0

    def get_total_balance(self) -> float:
        """
        Get total futures wallet balance

        Returns:
            Total balance as float
        """
        try:
            balance = self.get_futures_balance()

            if not balance:
                return 0.0

            # CoinDCX API returns 'balance' as the total balance
            total = round(float(balance.get('balance', 0)), 2)

            logger.info(f"Total balance: {total} USDT")

            return total

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

    def get_all_wallet_balances(self) -> List[Dict]:
        """
        Get wallet balances for all currencies

        Returns:
            List of wallet balances for all currencies
        """
        try:
            wallet_details = self.client.get_wallet_details()

            if not wallet_details:
                return []

            balances = []
            for wallet in wallet_details:
                balances.append({
                    'currency': wallet.get('currency_short_name'),
                    'total_balance': float(wallet.get('balance', 0)),
                    'locked_balance': float(wallet.get('locked_balance', 0)),
                    'available_balance': float(wallet.get('balance', 0)) - float(wallet.get('locked_balance', 0)),
                    'cross_order_margin': float(wallet.get('cross_order_margin', 0)),
                    'cross_user_margin': float(wallet.get('cross_user_margin', 0))
                })

            logger.info(f"Retrieved balances for {len(balances)} currencies")
            return balances

        except Exception as e:
            logger.error(f"Error getting all wallet balances: {e}")
            return []

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
            Dict with balance summary including locked balances
        """
        try:
            balance = self.get_futures_balance()

            if not balance:
                return {
                    'available_balance': 0.0,
                    'total_balance': 0.0,
                    'locked_balance': 0.0,
                    'cross_order_margin': 0.0,
                    'cross_user_margin': 0.0,
                    'used_margin': 0.0
                }

            # Parse CoinDCX wallet structure
            total = float(balance.get('balance', 0))
            locked = float(balance.get('locked_balance', 0))
            cross_order_margin = float(balance.get('cross_order_margin', 0))
            cross_user_margin = float(balance.get('cross_user_margin', 0))

            available = total - locked

            # Round to 2 decimal places for display
            summary = {
                'available_balance': round(available, 2),
                'total_balance': round(total, 2),
                'locked_balance': round(locked, 2),
                'cross_order_margin': round(cross_order_margin, 2),
                'cross_user_margin': round(cross_user_margin, 2),
                'used_margin': round(locked + cross_user_margin, 2)
            }

            logger.info(
                f"Balance summary - Total: {total} USDT, Available: {available} USDT, "
                f"Locked: {locked} USDT, Margin: {cross_user_margin} USDT"
            )

            return summary

        except Exception as e:
            logger.error(f"Error getting balance summary: {e}")
            return {
                'available_balance': 0.0,
                'total_balance': 0.0,
                'locked_balance': 0.0,
                'cross_order_margin': 0.0,
                'cross_user_margin': 0.0,
                'used_margin': 0.0
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

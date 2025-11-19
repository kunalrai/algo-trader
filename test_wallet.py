"""
Test Wallet Manager
Quick test script to verify wallet balance retrieval
"""

import logging
import config
from coindcx_client import CoinDCXFuturesClient
from wallet_manager import WalletManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_wallet():
    """Test wallet manager functionality"""

    print("="*60)
    print("Testing Wallet Manager")
    print("="*60)

    # Initialize client
    logger.info("Initializing CoinDCX client...")
    client = CoinDCXFuturesClient(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET,
        base_url=config.BASE_URL
    )

    # Initialize wallet manager
    logger.info("Initializing Wallet Manager...")
    wallet_manager = WalletManager(client)

    # Test 1: Get raw wallet details
    print("\n" + "="*60)
    print("1. Raw Wallet Details (All Currencies)")
    print("="*60)
    wallet_details = wallet_manager.get_margin_details()
    if wallet_details:
        import json
        print(json.dumps(wallet_details, indent=2))
    else:
        print("Failed to retrieve wallet details")

    # Test 2: Get USDT balance
    print("\n" + "="*60)
    print("2. USDT Futures Balance")
    print("="*60)
    balance = wallet_manager.get_futures_balance()
    if balance:
        print(f"Currency: {balance.get('currency_short_name')}")
        print(f"Total Balance: {balance.get('balance')} USDT")
        print(f"Locked Balance: {balance.get('locked_balance')} USDT")
        print(f"Cross Order Margin: {balance.get('cross_order_margin')} USDT")
        print(f"Cross User Margin: {balance.get('cross_user_margin')} USDT")
    else:
        print("Failed to retrieve balance")

    # Test 3: Get available balance
    print("\n" + "="*60)
    print("3. Available Balance (for trading)")
    print("="*60)
    available = wallet_manager.get_available_balance()
    print(f"Available Balance: {available:.4f} USDT")

    # Test 4: Get total balance
    print("\n" + "="*60)
    print("4. Total Balance")
    print("="*60)
    total = wallet_manager.get_total_balance()
    print(f"Total Balance: {total:.4f} USDT")

    # Test 5: Get balance summary
    print("\n" + "="*60)
    print("5. Balance Summary")
    print("="*60)
    summary = wallet_manager.get_balance_summary()
    print(f"Total Balance: {summary['total_balance']:.4f} USDT")
    print(f"Available Balance: {summary['available_balance']:.4f} USDT")
    print(f"Locked Balance: {summary['locked_balance']:.4f} USDT")
    print(f"Cross User Margin: {summary['cross_user_margin']:.4f} USDT")
    print(f"Used Margin: {summary['used_margin']:.4f} USDT")

    # Test 6: Get all wallet balances
    print("\n" + "="*60)
    print("6. All Wallet Balances")
    print("="*60)
    all_balances = wallet_manager.get_all_wallet_balances()
    for bal in all_balances:
        print(f"\n{bal['currency']}:")
        print(f"  Total: {bal['total_balance']:.4f}")
        print(f"  Available: {bal['available_balance']:.4f}")
        print(f"  Locked: {bal['locked_balance']:.4f}")

    # Test 7: Calculate max position value
    print("\n" + "="*60)
    print("7. Max Position Value Calculation")
    print("="*60)
    max_value = wallet_manager.calculate_max_position_value(
        max_percent=config.RISK_MANAGEMENT['max_position_size_percent'],
        leverage=config.RISK_MANAGEMENT['leverage']
    )
    print(f"Max position value: ${max_value:.2f}")
    print(f"  (Using {config.RISK_MANAGEMENT['max_position_size_percent']}% of balance with {config.RISK_MANAGEMENT['leverage']}x leverage)")

    # Test 8: Balance health
    print("\n" + "="*60)
    print("8. Balance Health Check")
    print("="*60)
    health = wallet_manager.get_balance_health()
    print(f"Status: {health['status'].upper()}")
    print(f"Utilization: {health['utilization_percent']:.2f}%")
    print(f"Available: ${health['available_balance']:.2f}")
    print(f"Total: ${health['total_balance']:.2f}")
    print(f"Used Margin: ${health['used_margin']:.2f}")

    # Test 9: Check sufficient balance
    print("\n" + "="*60)
    print("9. Sufficient Balance Check")
    print("="*60)
    test_amounts = [1.0, 5.0, 10.0, 100.0]
    for amount in test_amounts:
        sufficient = wallet_manager.check_sufficient_balance(amount)
        status = "✓ YES" if sufficient else "✗ NO"
        print(f"  ${amount:.2f} USDT: {status}")

    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_wallet()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

"""
Test User Signal Generation
Quick test to see what signals are being generated for the user
"""

import sys
import logging
from flask import Flask

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_signals():
    """Test signal generation for user"""
    from app import app
    from models import User, UserProfile
    import config

    with app.app_context():
        # Get first user
        user = User.query.first()
        if not user:
            print("No users found in database")
            return

        print(f"\n=== Testing Signals for User: {user.email} ===\n")

        # Check user's profile
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if profile:
            print(f"User Strategy: {profile.default_strategy}")
            print(f"Trading Pairs: {[p.symbol for p in user.trading_pairs if p.is_active]}")
        else:
            print("No profile found - using defaults")

        # Test signal generation
        from user_signal_generator import get_user_signal_generator
        from user_data_fetcher import get_user_data_fetcher
        from coindcx_client import CoinDCXFuturesClient

        client = CoinDCXFuturesClient(
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            base_url=config.BASE_URL
        )

        data_fetcher = get_user_data_fetcher(user.id, client)
        signal_gen = get_user_signal_generator(
            user_id=user.id,
            data_fetcher=data_fetcher,
            indicator_config=config.INDICATORS,
            rsi_config=config.INDICATORS['RSI'],
            use_strategy_system=True,
            user_strategy=profile.default_strategy if profile else 'combined'
        )

        print(f"\nSignal Generator Info:")
        print(f"  User Strategy: {signal_gen.user_strategy}")
        print(f"  Strategy System Enabled: {signal_gen._signal_generator.use_strategy_system}")

        if signal_gen._signal_generator.strategy_manager:
            active = signal_gen._signal_generator.strategy_manager.get_active_strategy()
            print(f"  Active Strategy: {active.name if active else 'None'}")
            print(f"  Active Strategy ID: {signal_gen._signal_generator.strategy_manager.get_active_strategy_id()}")

        # Test with one pair
        test_pair = "BTCUSDT"
        print(f"\n=== Generating Signal for {test_pair} ===\n")

        signal = signal_gen.generate_signal(test_pair, config.TIMEFRAMES)

        if signal:
            print(f"Signal Generated:")
            print(f"  Action: {signal['action']}")
            print(f"  Strength: {signal['strength']:.2%}")
            print(f"  Bullish Score: {signal.get('bullish_score', 0):.2%}")
            print(f"  Bearish Score: {signal.get('bearish_score', 0):.2%}")
            print(f"  Current Price: ${signal['current_price']:,.2f}")
            print(f"  Strategy: {signal.get('strategy_name', 'legacy')}")
            if 'reasons' in signal:
                print(f"  Reasons:")
                for reason in signal['reasons']:
                    print(f"    - {reason}")
        else:
            print("No signal generated (returned None)")

if __name__ == '__main__':
    test_user_signals()

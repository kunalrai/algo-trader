"""
Quick Signal Test
Test signal generation without running the full bot
"""

import logging
import config
from coindcx_client import CoinDCXFuturesClient
from data_fetcher import DataFetcher
from signal_generator import SignalGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test signal generation"""
    logger.info("=" * 60)
    logger.info("SIGNAL GENERATION TEST (Dry-Run)")
    logger.info("=" * 60)

    # Initialize components
    client = CoinDCXFuturesClient(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET,
        base_url=config.BASE_URL
    )

    data_fetcher = DataFetcher(client)
    signal_generator = SignalGenerator(
        data_fetcher,
        config.INDICATORS,
        config.INDICATORS['RSI']
    )

    # Test each trading pair
    for coin_name, symbol in config.TRADING_PAIRS.items():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing: {coin_name} ({symbol})")
        logger.info("=" * 60)

        try:
            # Get current price
            price = data_fetcher.get_latest_price(symbol)
            logger.info(f"Current Price: ${price:.2f}")

            # Generate signal
            signal = signal_generator.generate_signal(symbol, config.TIMEFRAMES)

            if signal:
                logger.info(f"\n📊 Signal Generated:")
                logger.info(f"  Action: {signal['action'].upper()}")
                logger.info(f"  Strength: {signal['strength']:.2f} (Min: {config.TRADING_PARAMS['min_signal_strength']})")
                logger.info(f"  Bullish Score: {signal['bullish_score']:.2f}")
                logger.info(f"  Bearish Score: {signal['bearish_score']:.2f}")

                # Check if signal would trigger a trade
                if signal['strength'] >= config.TRADING_PARAMS['min_signal_strength']:
                    if signal['action'] in ['long', 'short']:
                        logger.info(f"\n✅ TRADE SIGNAL: Would execute {signal['action'].upper()} position")
                    else:
                        logger.info(f"\n⏸️  No clear direction (FLAT)")
                else:
                    logger.info(f"\n❌ Signal too weak (below threshold)")

                # Show timeframe analysis
                logger.info(f"\n📈 Timeframe Analysis:")
                for tf_name, analysis in signal['analyses'].items():
                    logger.info(f"  {tf_name}:")
                    logger.info(f"    Trend: {analysis['trend']}")
                    logger.info(f"    MACD: {analysis['macd_signal']}")
                    logger.info(f"    RSI: {analysis['rsi_signal']} ({analysis.get('rsi_value', 0):.2f})")
                    logger.info(f"    Strength: {analysis['strength']:.2f}")
            else:
                logger.info("❌ No signal generated (insufficient data)")

        except Exception as e:
            logger.error(f"Error testing {coin_name}: {e}")

    logger.info(f"\n{'=' * 60}")
    logger.info("Test Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

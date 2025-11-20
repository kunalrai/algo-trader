"""
All-in-One Trading Bot Launcher
Starts bot and dashboard together with full monitoring
"""

import subprocess
import sys
import os
import time
import webbrowser
import logging
from threading import Thread
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║         🤖 CRYPTO FUTURES TRADING BOT 🤖                     ║
    ║                                                               ║
    ║         All-in-One Trading System                            ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_config():
    """Print current configuration"""
    mode = "🟡 DRY RUN (SAFE)" if config.TRADING_PARAMS['dry_run'] else "🔴 LIVE (REAL MONEY)"

    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)
    print(f"Trading Mode:       {mode}")

    if config.TRADING_PARAMS['dry_run']:
        print(f"Simulated Balance:  ${config.TRADING_PARAMS.get('simulated_balance', 1000):.2f} USDT")

    print(f"Trading Pairs:      {', '.join(config.TRADING_PAIRS.keys())}")
    print(f"Max Positions:      {config.TRADING_PARAMS['max_open_positions']}")
    print(f"Leverage:           {config.RISK_MANAGEMENT['leverage']}x")
    print(f"Stop Loss:          {config.RISK_MANAGEMENT['stop_loss_percent']}%")
    print(f"Take Profit:        {config.RISK_MANAGEMENT['take_profit_percent']}%")
    print(f"Signal Strength:    {config.TRADING_PARAMS['min_signal_strength']}")
    print(f"Scan Interval:      {config.TRADING_PARAMS['signal_scan_interval']}s")
    print("="*70)


def check_dependencies():
    """Check if all dependencies are installed"""
    logger.info("Checking dependencies...")

    required_modules = [
        ('flask', 'flask'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('requests', 'requests'),
        ('python-dotenv', 'dotenv')
    ]

    missing = []
    for package_name, import_name in required_modules:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Install with: pip install " + " ".join(missing))
        return False

    logger.info("✓ All dependencies installed")
    return True


def check_env_file():
    """Check if .env file exists with API keys"""
    if not os.path.exists('.env'):
        logger.warning("⚠️  .env file not found")
        logger.warning("   Create .env file with API_KEY and API_SECRET")
        return False

    logger.info("✓ .env file found")
    return True


def run_bot():
    """Run the trading bot"""
    logger.info("Starting trading bot...")
    try:
        subprocess.run([sys.executable, 'run_bot.py'])
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")


def run_dashboard():
    """Run the dashboard"""
    logger.info("Starting dashboard...")
    time.sleep(2)  # Wait for bot to initialize

    try:
        # Start Flask app
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")


def open_browser():
    """Open browser to dashboard"""
    time.sleep(5)  # Wait for dashboard to start
    logger.info("Opening browser...")
    try:
        webbrowser.open('http://localhost:5000')
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")
        logger.info("Manually open: http://localhost:5000")


def print_instructions():
    """Print usage instructions"""
    print("\n" + "="*70)
    print("SYSTEM STARTED")
    print("="*70)
    print("\n📊 Dashboard:      http://localhost:5000 (includes live P&L)")
    print("🛑 Stop System:     Press Ctrl+C")

    if config.TRADING_PARAMS['dry_run']:
        print("\n💡 DRY-RUN MODE FEATURES:")
        print("   ✓ $1000 simulated balance")
        print("   ✓ Real market data")
        print("   ✓ No real trades")
        print("   ✓ Full P&L tracking")
        print("   ✓ Trade history saved to: simulated_wallet.json")

    print("\n⚙️  WHAT'S HAPPENING:")
    print("   • Bot scans markets every 60 seconds")
    print("   • Analyzes EMA, MACD, RSI indicators")
    print("   • Opens positions when signals are strong (≥0.7)")
    print("   • Monitors positions with TP/SL")
    print("   • Dashboard updates every 5 seconds")

    print("\n📚 USEFUL COMMANDS:")
    print("   python view_pnl.py       - View detailed P&L report")
    print("   python test_signals.py   - Test signal generation")

    print("\n" + "="*70)
    print("\n⏳ System running... Check dashboard for live updates\n")


def main():
    """Main entry point"""
    print_banner()
    print_config()

    # Confirmation for live mode
    if not config.TRADING_PARAMS['dry_run']:
        print("\n" + "⚠️ "*35)
        print("⚠️  WARNING: LIVE TRADING MODE ENABLED!")
        print("⚠️  Real trades will be executed with real money!")
        print("⚠️ "*35)
        response = input("\nType 'YES' to continue with live trading: ")
        if response != 'YES':
            logger.info("Exiting...")
            return

    # Pre-flight checks
    print("\n" + "="*70)
    print("PRE-FLIGHT CHECKS")
    print("="*70)

    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        return

    if not check_env_file():
        logger.warning("⚠️  API credentials not configured")
        logger.info("   Continuing anyway (will use .env if available)")

    logger.info("✓ All checks passed")

    # Start components
    print("\n" + "="*70)
    print("STARTING COMPONENTS")
    print("="*70)

    # Create threads for bot and dashboard
    bot_thread = Thread(target=run_bot, daemon=True)
    dashboard_thread = Thread(target=run_dashboard, daemon=True)
    browser_thread = Thread(target=open_browser, daemon=True)

    # Start everything
    bot_thread.start()
    dashboard_thread.start()
    browser_thread.start()

    # Print instructions
    print_instructions()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("SHUTTING DOWN")
        print("="*70)
        logger.info("Stopping all components...")

        # Show final summary if dry-run
        if config.TRADING_PARAMS['dry_run']:
            print("\n📊 To view final results:")
            print("   python view_pnl.py")

        logger.info("Goodbye! 👋")


if __name__ == "__main__":
    main()

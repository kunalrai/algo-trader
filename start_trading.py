"""
═══════════════════════════════════════════════════════════════════════════════
MAIN APPLICATION ENTRY POINT
═══════════════════════════════════════════════════════════════════════════════

This is the ONLY file you should run to start the trading bot system.

Usage:
    python start_trading.py

What it does:
    - Checks all dependencies are installed
    - Initializes the database
    - Starts the trading bot
    - Starts the web dashboard
    - Opens your browser automatically

DO NOT run app.py, run_bot.py, or any other files directly!
Always use this file as the main entry point.

═══════════════════════════════════════════════════════════════════════════════
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

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║         🤖 CRYPTO FUTURES TRADING BOT 🤖                     ║
    ║                                                               ║
    ║         Professional Multi-User Trading Platform             ║
    ║         Paper Trading & Live Trading Support                 ║
    ║         ATR-Based Dynamic Stop Loss                          ║
    ║         User-Specific Trading Pairs                          ║
    ║         Superadmin Management Dashboard                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝

    THIS IS THE MAIN APPLICATION - Always run: python start_trading.py
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
        ('Flask-SQLAlchemy', 'flask_sqlalchemy'),
        ('Flask-Login', 'flask_login'),
        ('Authlib', 'authlib'),
        ('cryptography', 'cryptography'),
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
        logger.error("Install with: pip install -r requirements.txt")
        return False

    logger.info("✓ All dependencies installed")
    return True


def check_env_file():
    """Check if .env file exists with required configuration"""
    if not os.path.exists('.env'):
        logger.warning("⚠️  .env file not found")
        logger.warning("   Copy .env.example to .env and configure it")
        return False

    logger.info("✓ .env file found")

    # Check for encryption key
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    if not encryption_key or encryption_key == 'your_generated_fernet_key_here':
        logger.warning("⚠️  ENCRYPTION_KEY not set in .env")
        logger.warning("   Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")

    return True


def initialize_database():
    """Initialize database tables"""
    logger.info("Initializing database...")
    try:
        from app import app
        from models import db
        with app.app_context():
            db.create_all()
        logger.info("✓ Database initialized (algo_trader.db)")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def run_bot():
    """
    DEPRECATED: Legacy global bot removed.
    Per-user bots should be started from the dashboard UI.
    Each user starts their own isolated bot via the web interface.
    """
    logger.info("Legacy global bot disabled - using per-user bot system")
    logger.info("Users should start their own bots from the dashboard UI")
    # No longer starting run_bot.py - per-user bots only


def run_dashboard():
    """Run the dashboard"""
    logger.info("Starting dashboard...")

    try:
        # Start Flask app via run_dashboard.py
        subprocess.run([sys.executable, 'run_dashboard.py'])
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
    print("\n📊 Dashboard:       http://localhost:5000")
    print("🔐 Login Required:  Register or sign in with Google/Email")
    print("🛑 Stop System:     Press Ctrl+C")

    print("\n👤 USER FEATURES:")
    print("   ✓ Google OAuth & Email/Password login")
    print("   ✓ Personal profile with trading settings")
    print("   ✓ Select your own trading pairs (BTC, ETH, SOL, etc.)")
    print("   ✓ Paper Trading (simulated) mode")
    print("   ✓ Live Trading with your own API keys")
    print("   ✓ Encrypted API key storage")
    print("   ✓ ATR-based dynamic stop loss (adapts to volatility)")

    print("\n👑 SUPERADMIN ACCESS:")
    print("   Email:    admin@algotrader.com")
    print("   Password: superadmin123#")
    print("   Access:   Profile Menu > Admin Dashboard")

    print("\n⚙️  HOW IT WORKS:")
    print("   • Each user starts their own isolated bot from the dashboard")
    print("   • Bot scans markets based on user's scan interval")
    print("   • Analyzes using user's selected strategy (EMA, MACD, RSI, etc.)")
    print("   • Opens positions when signals are strong enough")
    print("   • Dynamic TP/SL based on market volatility (ATR)")
    print("   • Monitors positions with TP/SL")
    print("   • Dashboard updates every 5 seconds")

    print("\n📚 FIRST TIME SETUP:")
    print("   1. Open http://localhost:5000")
    print("   2. Register with email or Google")
    print("   3. Go to Profile to configure:")
    print("      • Select trading pairs you want to trade")
    print("      • Choose your trading strategy")
    print("      • Set risk management parameters")
    print("      • Add CoinDCX API keys for live trading (optional)")
    print("   4. Click 'Start Bot' to begin trading!")
    print("   5. Monitor your bot in the Activity feed")

    print("\n" + "="*70)
    print("\n⏳ System running... Open dashboard to get started\n")


def main():
    """Main entry point"""
    print_banner()
    print_config()

    # Pre-flight checks
    print("\n" + "="*70)
    print("PRE-FLIGHT CHECKS")
    print("="*70)

    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        logger.error("   Run: pip install -r requirements.txt")
        return

    if not check_env_file():
        logger.warning("⚠️  Configuration not complete")
        logger.info("   Copy .env.example to .env and configure it")

    # Initialize database
    if not initialize_database():
        logger.error("❌ Could not initialize database")
        return

    logger.info("✓ All checks passed")

    # Start components
    print("\n" + "="*70)
    print("STARTING DASHBOARD")
    print("="*70)

    # Create threads for dashboard only (no global bot)
    # Per-user bots are started from the UI by each user
    dashboard_thread = Thread(target=run_dashboard, daemon=True)
    browser_thread = Thread(target=open_browser, daemon=True)

    # Start dashboard
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
        logger.info("User data saved to: algo_trader.db")
        logger.info("Goodbye! 👋")


if __name__ == "__main__":
    main()

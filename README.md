# Crypto Futures Trading Bot

Professional multi-user cryptocurrency futures trading platform with paper trading and live trading support.

## 🚀 Quick Start

### Single Command to Start Everything

```bash
python start_trading.py
```

**That's it!** This single command will:
- ✓ Check all dependencies
- ✓ Initialize the database
- ✓ Start the trading bot
- ✓ Launch the web dashboard
- ✓ Open your browser automatically

**IMPORTANT**: Always use `python start_trading.py` - do not run any other files directly.

---

## 📋 Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Copy the example environment file:

```bash
copy .env.example .env
```

Edit `.env` to add your configuration (optional for paper trading).

---

## 🔐 Login Credentials

### Superadmin Account (Pre-created)

```
Email:    admin@algotrader.com
Password: superadmin123#
```

Use this account to:
- Manage all users
- View system-wide statistics
- Activate/deactivate users
- Access admin dashboard

### Regular Users

- Register at `http://localhost:5000/auth/register`
- Or sign in with Google OAuth

---

## ✨ Key Features

### 1. **ATR-Based Dynamic Stop Loss**
Stop loss and take profit levels automatically adjust based on market volatility (ATR indicator):
- Tighter stops in calm markets
- Wider stops in volatile markets
- Reduces false stop-outs
- Better risk/reward ratios

### 2. **User-Specific Trading Pairs**
Each user selects which cryptocurrency pairs to trade:
- Choose from BTC, ETH, SOL, TAO, and more
- Bot only scans your selected pairs
- Toggle pairs active/inactive anytime
- Activity feed shows only your pairs

### 3. **Superadmin Dashboard**
Centralized user management:
- View all registered users
- Activate/deactivate accounts
- Monitor trading activity
- System-wide statistics

### 4. **Multi-User System**
Complete user isolation:
- Personal trading settings
- Individual API keys (encrypted)
- Separate simulated wallets
- Independent trading history

### 5. **Paper Trading**
Risk-free testing:
- $1000 starting balance (configurable)
- Realistic position tracking
- Full P&L calculations
- Test strategies safely

### 6. **Live Trading**
Real trading when ready:
- Connect your CoinDCX API keys
- Encrypted key storage
- User-specific risk settings
- Live position monitoring

---

## 📊 Dashboard Access

Once started, access the dashboard at:

```
http://localhost:5000
```

### Main Pages

- **Overview**: Account balance, positions, P&L
- **Positions**: Active trades with real-time updates
- **Strategies**: View and manage trading strategies
- **Market**: Live market data and indicators
- **Activity**: Real-time bot activity feed
- **Performance**: Trading statistics and history
- **Profile**: Personal settings and trading pairs

### Superadmin Only

- **Admin Dashboard**: User management (access via Profile menu)

---

## ⚙️ Configuration

### Trading Pairs

Configure in `config.py`:

```python
TRADING_PAIRS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "TAO": "TAOUSDT"
}
```

Users can select which pairs they want to trade in their Profile.

### Risk Management

ATR-based settings in `config.py`:

```python
RISK_MANAGEMENT = {
    "use_atr_stop_loss": True,
    "atr_stop_loss_multiplier": 1.5,   # 1.5x ATR for stop loss
    "atr_take_profit_multiplier": 3.0,  # 3.0x ATR for take profit
    "leverage": 5,
    "max_position_size_percent": 10
}
```

### ATR Indicator

```python
INDICATORS = {
    "ATR": {
        "period": 14,          # 14-period ATR
        "multiplier": 1.5
    }
}
```

---

## 🛠️ System Architecture

### File Structure

```
start_trading.py       ← MAIN ENTRY POINT (run this!)
├── app.py            ← Flask web application (don't run directly)
├── run_dashboard.py  ← Dashboard launcher (called by start_trading.py)
├── run_bot.py        ← Trading bot logic (started by start_trading.py)
├── auth.py           ← Authentication & user management
├── models.py         ← Database models
├── config.py         ← Configuration settings
├── indicators.py     ← Technical indicators (includes ATR)
├── order_manager.py  ← Order execution with ATR-based TP/SL
├── signal_generator.py ← Signal generation
├── trading_bot.py    ← Main bot logic
└── templates/        ← HTML templates
    ├── base.html
    ├── overview.html
    ├── positions.html
    └── auth/
        ├── profile.html
        └── admin_users.html
```

### Database Schema

- **users**: User accounts with authentication
- **user_profiles**: Trading settings and API keys
- **user_trading_pairs**: User-selected trading pairs
- **user_simulated_wallets**: Paper trading balances
- **user_simulated_positions**: Active paper positions
- **user_trade_history**: Completed trades

---

## 📈 How It Works

### Signal Generation

1. Bot scans selected pairs every 60 seconds
2. Analyzes multiple indicators:
   - EMA crossovers
   - MACD signals
   - RSI levels
   - **ATR for volatility**
3. Generates signal strength (0-1)
4. Executes if strength ≥ 0.7

### Position Management

1. **Entry**: Market order at current price
2. **Stop Loss**: Entry ± (ATR × 1.5)
3. **Take Profit**: Entry ± (ATR × 3.0)
4. **Monitoring**: Real-time P&L tracking
5. **Exit**: TP/SL hit or manual close

### ATR-Based TP/SL Example

```
Entry Price: $50,000
ATR Value: $250
Side: LONG

Stop Loss:   $50,000 - ($250 × 1.5) = $49,625
Take Profit: $50,000 + ($250 × 3.0) = $50,750
```

In volatile markets, ATR increases → wider stops → fewer false stop-outs.

---

## 🔒 Security

### API Key Encryption

All user API keys are encrypted using Fernet encryption:
- Unique encryption key per installation
- Keys stored encrypted in database
- Decrypted only when needed for trading
- Superadmin cannot view user keys

### User Isolation

- Each user has separate database records
- API keys are user-specific
- Trading activity is isolated
- Simulated wallets are independent

### Authentication

- Password hashing with werkzeug
- Google OAuth support
- Session-based authentication
- Login required for all dashboard pages

---

## 🐛 Troubleshooting

### Issue: Dependencies missing

```bash
pip install -r requirements.txt
```

### Issue: Database errors

```bash
python migrate_add_superadmin.py
python create_superadmin.py
```

### Issue: Can't login as superadmin

Recreate the account:

```bash
python create_superadmin.py
```

### Issue: Trading pairs not showing

Check database:

```bash
python -c "from app import app; from models import db; app.app_context().push(); db.create_all()"
```

---

## 📝 Usage Examples

### Regular User Workflow

1. Start system: `python start_trading.py`
2. Register at `http://localhost:5000/auth/register`
3. Go to Profile
4. Select trading pairs (e.g., BTC, ETH)
5. Configure risk settings
6. Watch bot trade selected pairs

### Superadmin Workflow

1. Start system: `python start_trading.py`
2. Login with admin credentials
3. Click Profile → Admin Dashboard
4. View all users
5. Manage user accounts
6. Monitor system activity

### Adding New Trading Pairs

1. Edit `config.py`:
```python
TRADING_PAIRS = {
    "BTC": "BTCUSDT",
    "NEWCOIN": "NEWCOINUSDT"  # Add this
}
```

2. Users can now select "NEWCOIN" in their Profile

---

## 🎯 Trading Modes

### Paper Trading (Default)

- No real money at risk
- $1000 simulated balance
- Test strategies safely
- Perfect for learning

Set in Profile: **Trading Mode → Paper**

### Live Trading

- Real money trading
- Requires CoinDCX API keys
- User-specific keys
- Encrypted storage

Set in Profile:
1. Add API keys
2. Switch to **Trading Mode → Live**

---

## 📞 Support

For issues:
1. Check the logs in console
2. Review this README
3. Check `NEW_FEATURES_GUIDE.md` for detailed feature docs

---

## ⚠️ Important Notes

1. **Always run** `python start_trading.py` - don't run other files directly
2. **Paper trading first** - test before going live
3. **Secure your keys** - never share API keys or .env file
4. **Superadmin password** - change in production (`create_superadmin.py`)
5. **ATR adapts to volatility** - wider stops in volatile markets are normal

---

## 🚦 Quick Command Reference

```bash
# Start the system (MAIN COMMAND)
python start_trading.py

# Install dependencies
pip install -r requirements.txt

# Database migration (if needed)
python migrate_add_superadmin.py

# Create superadmin (if needed)
python create_superadmin.py

# Stop the system
Press Ctrl+C in terminal
```

---

## 📜 License

Private use only.

---

**Happy Trading! 🚀**

Always remember: `python start_trading.py` is your main entry point!

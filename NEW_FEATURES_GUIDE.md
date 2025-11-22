# New Features Guide

This guide explains the new features that have been added to your algo-trading system.

## Summary of New Features

1. **ATR-Based Dynamic Stop Loss** - Stop loss and take profit now adapt to market volatility
2. **User-Specific Trading Pairs** - Each user can select which crypto pairs they want to trade
3. **Superadmin Dashboard** - Manage all users from a centralized admin panel

---

## 1. ATR-Based Dynamic Stop Loss

### What Changed
Instead of using fixed percentage stop loss (e.g., 2%), the system now calculates stop loss based on ATR (Average True Range), which measures market volatility.

### How It Works
- **ATR Calculation**: Measures the average price range over 14 periods
- **Stop Loss**: Entry Price ± (ATR × 1.5) depending on position side
- **Take Profit**: Entry Price ± (ATR × 3.0) depending on position side
- **Fallback**: If ATR is unavailable, falls back to percentage-based calculation

### Configuration
Edit `config.py` to adjust:
```python
RISK_MANAGEMENT = {
    "use_atr_stop_loss": True,              # Enable/disable ATR-based SL
    "atr_stop_loss_multiplier": 1.5,        # Multiplier for stop loss
    "atr_take_profit_multiplier": 3.0       # Multiplier for take profit
}

INDICATORS = {
    "ATR": {
        "period": 14,                        # ATR period (bars)
        "multiplier": 1.5
    }
}
```

### Benefits
- Adapts to market conditions (tighter stops in calm markets, wider in volatile)
- Better risk management based on actual volatility
- Reduces false stop-outs during normal volatility

---

## 2. User-Specific Trading Pairs

### What Changed
Each user can now select which cryptocurrency pairs they want to trade. The bot will only scan and trade those selected pairs for each user.

### How to Use

1. **Login** to your account at http://localhost:5000
2. **Go to Profile** page
3. **Trading Instruments** section shows:
   - Your active pairs (green badges)
   - Your inactive pairs (gray badges)
   - Available pairs to add

### Actions Available

**Toggle Active/Inactive**: Click the toggle button on any pair to enable/disable it
- Green = Active (bot will trade)
- Gray = Inactive (bot will skip)

**Remove Pair**: Click "Remove" to completely delete a pair from your list

**Add New Pair**: Click the "Add [Symbol]" button to add a new trading pair

### Default Pairs
New users automatically get these pairs:
- BTC (BTCUSDT)
- ETH (ETHUSDT)
- SOL (SOLUSDT)

### Important Notes
- Only **active** pairs are traded by the bot
- Each user has their own independent pair selection
- Changes take effect on the next scan cycle
- Activity feed and positions are filtered by your selected pairs

---

## 3. Superadmin Dashboard

### Superadmin Credentials
```
Email: admin@algotrader.com
Password: superadmin123#
```

### How to Access
1. Login with superadmin credentials
2. Click your profile dropdown (top right)
3. Select "Admin Dashboard"

### Features

#### User Statistics
View real-time stats:
- Total users in the system
- Active users
- Users in live trading mode
- Users with API keys configured

#### User Management Table
For each user, you can see:
- Name and email
- Account status (Active/Inactive, Verified)
- Trading mode (Paper/Live)
- API key status
- Account creation date
- Last login time

#### Admin Actions

**Activate/Deactivate Users**:
- Click "Activate" or "Deactivate" to toggle user status
- Inactive users cannot login
- Cannot deactivate yourself
- Cannot deactivate other superadmins

**Delete Users**:
- Click "Delete" to permanently remove a user
- Confirmation required
- Cannot delete superadmins
- Cannot delete yourself
- **WARNING**: This action is irreversible and deletes all user data

### Security Notes
- Only superadmin accounts can access the admin dashboard
- Regular users cannot see or access admin features
- Superadmin badge shows in user list (red ADMIN tag)

---

## How to Start the System

**⚠️ IMPORTANT: Always use `python start_trading.py` as the main entry point!**

Do NOT run `app.py`, `run_bot.py`, or any other files directly. Only run `start_trading.py`.

### First Time Setup

1. **Install Dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment** (if not already done):
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the Application** (MAIN COMMAND):
   ```bash
   python start_trading.py
   ```

   This single command does everything:
   - Checks dependencies
   - Initializes database
   - Starts trading bot
   - Launches web dashboard
   - Opens browser automatically

### What Happens on Startup

1. Dependencies are checked
2. Database is initialized (creates tables if needed)
3. Trading bot starts in background
4. Dashboard starts on http://localhost:5000
5. Browser opens automatically

### Logging In

**Regular Users**:
- Register at http://localhost:5000/auth/register
- Or sign in with Google OAuth

**Superadmin**:
- Login at http://localhost:5000/auth/login
- Email: admin@algotrader.com
- Password: superadmin123#

---

## Configuration Files Modified

### Files You May Want to Edit

1. **config.py** - Trading parameters, ATR settings, risk management
2. **.env** - API keys, encryption key, OAuth credentials
3. **models.py** - Database schema (advanced users only)

### Files Created

1. **create_superadmin.py** - Script to create superadmin (already run)
2. **migrate_add_superadmin.py** - Database migration script (already run)

---

## Testing the New Features

### Test ATR Stop Loss
1. Start the bot in paper trading mode (dry_run = True)
2. Wait for a signal to trigger
3. Check the logs - you should see:
   ```
   ATR-based TP/SL calculated for LONG at 50000:
   ATR=250.00, SL=49625.00 (1.5x ATR), TP=50750.00 (3.0x ATR)
   ```

### Test Trading Pairs
1. Login as a regular user
2. Go to Profile
3. Deactivate all pairs except BTC
4. Watch the activity feed - only BTC signals/trades appear

### Test Superadmin
1. Login as superadmin
2. Go to Admin Dashboard
3. View all registered users
4. Try activating/deactivating a test user

---

## Troubleshooting

### Issue: "Column is_superadmin doesn't exist"
**Solution**: Run the migration script:
```bash
python migrate_add_superadmin.py
```

### Issue: "Module not found: authlib"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Can't login as superadmin
**Solution**: Create superadmin account:
```bash
python create_superadmin.py
```

### Issue: Trading pairs not showing
**Solution**: Check database initialization:
```bash
python -c "from app import app; from models import db; app.app_context().push(); db.create_all(); print('Database updated')"
```

---

## System Architecture

### Multi-User Flow
1. User logs in → Session created
2. User selects trading pairs in Profile
3. Bot scans market for ALL configured pairs
4. For each signal:
   - Check which users have this pair active
   - Execute trade for those users
5. Dashboard shows only user's selected pairs

### Data Isolation
- Each user has their own:
  - Trading pairs selection
  - API keys (encrypted)
  - Simulated wallet
  - Trading history
  - Risk settings

### Admin Oversight
- Superadmin can:
  - View all users
  - Manage user accounts
  - Monitor system usage
  - Cannot access user's API keys (encrypted)

---

## Next Steps

1. **Start Trading**: Run `python start_trading.py`
2. **Create Test User**: Register a regular user account
3. **Configure Pairs**: Select which pairs you want to trade
4. **Monitor System**: Use superadmin dashboard to oversee all users
5. **Go Live**: When ready, switch from paper to live trading in Profile

---

## Support

For issues or questions:
1. Check the logs in console output
2. Review this guide
3. Check database with: `python -c "from app import app; from models import *; ..."`

**Happy Trading!** 🚀

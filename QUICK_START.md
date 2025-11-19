# Quick Start Guide - Trading Bot Dashboard

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Flask-CORS (for API access)
- pandas, numpy (data processing)
- requests (API calls)
- python-dotenv (environment variables)

## Step 2: Configure Environment

Make sure your `.env` file has your CoinDCX API credentials:

```
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
```

## Step 3: Start the Dashboard

### Option A: Using the Batch File (Windows)
```bash
start_dashboard.bat
```

### Option B: Using Python Directly
```bash
python app.py
```

## Step 4: Access the Dashboard

Open your browser and go to:
```
http://localhost:5000
```

## What You'll See

### Dashboard Features

1. **Status Overview**
   - Total USDT balance
   - Active positions count
   - Current leverage settings
   - System status

2. **Live Market Prices**
   - BTC, ETH, XRP, BNB, SOL
   - Updates every 5 seconds

3. **Active Positions Table**
   - All open positions
   - Real-time P&L
   - Entry/current prices
   - Individual close buttons

4. **Trading Controls**
   - Toggle DRY RUN / LIVE mode
   - Refresh data manually
   - Emergency close all positions

## Safety First

The bot starts in **DRY RUN** mode by default:
- ✅ Monitor positions and prices
- ✅ Test the interface
- ❌ No real trades executed
- ❌ No funds at risk

To enable live trading:
1. Click "Toggle Trading Mode" button
2. Confirm the dialog
3. Badge will turn GREEN for LIVE mode

## Troubleshooting

### "No active positions" showing
- This is normal if you haven't opened any positions yet
- The bot filters for truly active positions (active_pos > 0)

### Balance showing $0.00
- Check your API credentials in `.env`
- Verify you have USDT in your CoinDCX Futures wallet
- Check console logs for API errors

### Dashboard won't start
- Make sure Flask is installed: `pip install Flask`
- Check if port 5000 is already in use
- Try running on a different port: `python app.py --port 5001`

### "Error fetching prices"
- Check your internet connection
- Verify CoinDCX API is accessible
- Check API rate limits

## Next Steps

1. **Monitor the Dashboard**: Watch the real-time updates
2. **Test Position Closing**: Try closing a test position (in DRY RUN mode)
3. **Explore API Endpoints**: Check the API at `/api/status`, `/api/positions`, etc.
4. **Configure Settings**: Edit `config.py` to customize trading parameters

## Important Notes

⚠️ **Security**
- Never share your API keys
- Don't expose the dashboard to the internet without authentication
- Keep `.env` file secure

⚠️ **Trading Risk**
- Always test in DRY RUN mode first
- Start with small positions in LIVE mode
- Use appropriate stop-loss settings
- Never risk more than you can afford to lose

## Support

For issues or questions:
- Check `DASHBOARD_README.md` for detailed documentation
- Review console logs for error messages
- Verify all dependencies are installed
- Check CoinDCX API status

---

**Ready to go?** Run `start_dashboard.bat` and visit http://localhost:5000

# Quick Start Guide

Get your trading bot up and running in 5 minutes!

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get CoinDCX API Credentials

1. Log in to your CoinDCX account
2. Go to **Settings** → **API Management** or visit https://coindcx.com/api-dashboard
3. Create a new API key with **Futures Trading** permissions
4. **Important**: Enable IP whitelisting for security
5. Copy your **API Key** and **API Secret**

## Step 3: Configure the Bot

Copy the example configuration:
```bash
cp config.example.py config.py
```

Edit `config.py` and update:
```python
API_KEY = "your_actual_api_key_here"
API_SECRET = "your_actual_api_secret_here"
```

## Step 4: Review Risk Settings

In `config.py`, check these settings (especially for first run):

```python
RISK_MANAGEMENT = {
    "max_position_size_percent": 5,   # Start with 5% instead of 10%
    "leverage": 2,                    # Start with 2x instead of 5x
    "stop_loss_percent": 2.0,
    "take_profit_percent": 4.0,
}

TRADING_PARAMS = {
    "max_open_positions": 1,          # Start with 1 position
    "min_signal_strength": 0.8,       # Higher threshold for first run
}
```

## Step 5: Verify Futures Wallet Balance

1. Log in to CoinDCX
2. Go to **Futures Wallet**
3. Ensure you have **USDT** available
4. Start with a small amount for testing (e.g., $100)

## Step 6: Run the Bot

```bash
python app.py
```

You'll see:
- Configuration summary
- Confirmation prompt
- Press **ENTER** to start trading
- Press **Ctrl+C** to stop

## Step 7: Monitor the Bot

Watch the console output and check `trading_bot.log` for detailed logs:

```bash
# In another terminal, watch the logs in real-time:
tail -f trading_bot.log
```

## What Happens Next?

The bot will:
1. ✅ Check your futures wallet balance
2. ✅ Scan BTC, ETH, XRP, BNB, SOL for trading signals
3. ✅ Execute trades when strong signals are found
4. ✅ Manage positions with automatic TP/SL
5. ✅ Update you via logs and console

## Common First-Time Issues

### "Configuration validation failed: API_KEY not configured"
→ Update `config.py` with your actual API credentials

### "Insufficient balance for trade"
→ Add USDT to your Futures wallet on CoinDCX

### "No candle data received"
→ Check internet connection and CoinDCX API status

### Bot executes no trades
→ Lower `min_signal_strength` to 0.6 or check if markets are ranging

## Safety Tips for First Run

1. **Start Small**: Use minimal capital for testing
2. **Monitor Closely**: Watch the first few trades carefully
3. **Check Logs**: Review `trading_bot.log` regularly
4. **Use Low Leverage**: Start with 2x or 3x leverage
5. **Limit Positions**: Set `max_open_positions` to 1 or 2
6. **Paper Trade**: Consider paper trading if available

## Stopping the Bot

**Graceful Shutdown**:
- Press **Ctrl+C** once
- Bot will finish current operations and display summary
- All positions remain open (managed by CoinDCX TP/SL orders)

**Emergency Stop**:
- Log in to CoinDCX
- Manually close positions if needed
- Cancel open orders

## Next Steps

Once comfortable with basic operation:

1. **Optimize Settings**: Adjust based on performance
2. **Increase Capital**: Gradually increase position sizes
3. **Add Pairs**: Enable more trading pairs
4. **Customize Indicators**: Tune technical indicator parameters
5. **Backtest**: Analyze historical performance

## Getting Help

- **Configuration Issues**: Review [README.md](README.md)
- **API Errors**: Check CoinDCX documentation
- **Bot Behavior**: Examine `trading_bot.log`
- **Trading Questions**: Understand your strategy first

## Remember

⚠️ **This bot trades real money** - start small and monitor closely!

Happy Trading! 🚀

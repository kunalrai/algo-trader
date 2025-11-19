# Trading Bot Dashboard

A beautiful, real-time web dashboard for monitoring and controlling your CoinDCX Futures Trading Bot.

## Features

### 📊 Real-Time Monitoring
- Live wallet balance updates
- Active positions tracking with P&L calculations
- Market prices for all configured trading pairs
- Auto-refresh every 5 seconds

### 💼 Position Management
- View all active positions with detailed metrics
- Real-time P&L calculations ($ and %)
- Individual position close functionality
- Bulk close all positions

### ⚙️ Trading Controls
- Toggle between DRY RUN and LIVE trading modes
- Manual data refresh
- System status monitoring

### 🎨 Modern UI
- Built with TailwindCSS for a clean, professional look
- Responsive design (works on desktop, tablet, and mobile)
- Dark theme optimized for extended use
- Color-coded profit/loss indicators

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your `.env` file is configured with your API credentials:
```
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
```

## Usage

### Start the Dashboard

```bash
python app.py
```

The dashboard will be available at: **http://localhost:5000**

### Access from Other Devices

If you want to access the dashboard from other devices on your network:

1. Find your computer's IP address
2. Open `http://<your-ip>:5000` on any device on the same network

## Dashboard Overview

### Status Cards (Top Row)
- **Total Balance**: Shows USDT balance (total, available, locked)
- **Active Positions**: Current/max positions with long/short breakdown
- **Leverage**: Current leverage setting with stop-loss and take-profit %
- **System Status**: Real-time connection status and last update time

### Market Prices
Real-time price display for all configured trading pairs:
- BTC, ETH, XRP, BNB, SOL

### Positions Table
Detailed view of all active positions:
- Trading pair
- Side (Long/Short)
- Position size
- Entry price
- Current price
- P&L ($ and %)
- Leverage
- Close button for each position

### Trading Controls
- **Toggle Trading Mode**: Switch between DRY RUN and LIVE trading
- **Refresh Data**: Manually refresh all data
- **Close All Positions**: Emergency close all open positions

## API Endpoints

The dashboard provides several REST API endpoints:

### GET Endpoints
- `/api/status` - Overall bot status and configuration
- `/api/positions` - All active positions with P&L
- `/api/prices` - Current market prices
- `/api/market/<symbol>` - Detailed market data for a symbol
- `/api/config` - Bot configuration

### POST Endpoints
- `/api/close-position` - Close a specific position
- `/api/trading/toggle` - Toggle trading mode (dry-run/live)

## Safety Features

### DRY RUN Mode
- By default, the bot runs in DRY RUN mode
- All trading operations are simulated
- No real orders are placed
- Safe for testing and monitoring

### Position Controls
- Confirmation dialogs before closing positions
- Individual position close functionality
- Emergency "Close All" button with double confirmation

### Trading Mode Toggle
- Prominent visual indicator (Yellow for DRY RUN, Green for LIVE)
- Confirmation required before mode change
- Logged in server console

## Configuration

The dashboard uses settings from `config.py`:

- **Trading Pairs**: Which cryptocurrencies to monitor
- **Timeframes**: Candlestick intervals (5m, 1h, 4h)
- **Risk Management**: Leverage, stop-loss, take-profit settings
- **Trading Parameters**: Max positions, signal intervals, etc.

## Troubleshooting

### Dashboard won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file has valid API credentials
- Check if port 5000 is already in use

### No data showing
- Verify your API credentials are correct
- Check your internet connection
- Look for errors in the console output
- Try the "Refresh Data" button

### Positions not updating
- The dashboard auto-refreshes every 5 seconds
- Click "Refresh Data" to force an update
- Check the "Last update" timestamp in the Status card

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Frontend**:
  - TailwindCSS (styling)
  - Vanilla JavaScript (interactivity)
  - Chart.js (for future charting features)
- **API**: RESTful JSON endpoints

## Security Notes

⚠️ **Important Security Considerations**:

1. **Never expose this dashboard to the public internet** without proper authentication
2. The current version has no authentication - only run on trusted networks
3. API keys should be kept secure in `.env` file
4. Consider adding HTTPS if accessing over network
5. For production use, implement proper authentication and rate limiting

## Future Enhancements

Potential features to add:
- [ ] User authentication (login/password)
- [ ] Historical P&L charts
- [ ] Trade history log
- [ ] Email/SMS alerts for positions
- [ ] Advanced order types (limit orders, etc.)
- [ ] Strategy backtesting interface
- [ ] Multiple user accounts

## License

Part of the CoinDCX Futures Trading Bot project.

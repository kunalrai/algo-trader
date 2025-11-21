# Multi-Strategy System - Testing Checklist

## Pre-Testing Setup

- [ ] Ensure Python environment is activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file exists with API credentials
- [ ] `config.py` has `dry_run: True` for safe testing

## 1. Basic Functionality Tests

### Strategy System Initialization
- [ ] Start bot: `python start_trading.py`
- [ ] Check console output for "Strategy system enabled" message
- [ ] Verify no errors during strategy registration
- [ ] Check log file: `tail -f trading_bot.log | grep Strategy`

### Dashboard Access
- [ ] Open browser to http://localhost:5000
- [ ] Verify dashboard loads without errors
- [ ] Check browser console for JavaScript errors (F12)
- [ ] Verify "Trading Strategy" section is visible

## 2. Strategy Display Tests

### Active Strategy Information
- [ ] "Active Strategy" shows correct name
- [ ] Strategy description displays properly
- [ ] Version number is shown
- [ ] Timeframes are listed correctly
- [ ] Indicators are displayed
- [ ] "Strategy System" status shows "Enabled" (green) or "Legacy Mode" (gray)

### Strategy Selector Dropdown
- [ ] Dropdown contains all 4 strategies:
  - [ ] Combined Multi-Indicator
  - [ ] EMA Crossover
  - [ ] MACD Strategy
  - [ ] RSI Mean Reversion
- [ ] Current active strategy is selected by default
- [ ] Dropdown is clickable and responsive

## 3. Strategy Switching Tests

### Via Dashboard
- [ ] Select different strategy from dropdown
- [ ] Click "Apply Strategy" button
- [ ] Confirmation dialog appears
- [ ] After confirming, success message shows
- [ ] Active strategy display updates
- [ ] Bot continues running without restart
- [ ] Next scan cycle uses new strategy (check activity feed)

### Via API
```bash
# Test each strategy
curl -X POST http://localhost:5000/api/strategies/set \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "ema_crossover"}'
```

- [ ] EMA Crossover switch works
- [ ] MACD switch works
- [ ] RSI switch works
- [ ] Combined switch works
- [ ] Invalid strategy returns error
- [ ] Dashboard updates automatically

## 4. Strategy Analysis Tests

### EMA Crossover Strategy
- [ ] Enable strategy: Set `active_strategy: "ema_crossover"` in config
- [ ] Restart bot
- [ ] Wait for signal scan (60 seconds)
- [ ] Check activity feed for signal analysis
- [ ] Verify reasons mention "EMA crossover" or "EMA trend"
- [ ] Check that timeframes 5m, 1h, 4h are analyzed
- [ ] Verify signal strength calculation

### MACD Strategy
- [ ] Switch to MACD strategy
- [ ] Wait for signal scan
- [ ] Check activity feed for MACD-related reasons
- [ ] Verify mentions: "MACD crossover", "histogram", "momentum"
- [ ] Check 5m and 1h timeframes are used
- [ ] Verify trend confirmation logic

### RSI Strategy
- [ ] Switch to RSI strategy
- [ ] Wait for signal scan
- [ ] Check activity feed for RSI-related reasons
- [ ] Verify mentions: "oversold", "overbought", RSI values
- [ ] Check 5m and 1h timeframes
- [ ] Test extreme levels (if market provides)

### Combined Strategy
- [ ] Switch to Combined strategy
- [ ] Wait for signal scan
- [ ] Check activity feed shows multi-indicator analysis
- [ ] Verify reasons mention EMA, MACD, and RSI
- [ ] Check all 3 timeframes (5m, 1h, 4h) analyzed
- [ ] Verify weighted scoring system

## 5. Configuration Tests

### Enable/Disable Strategy System
```python
# config.py
STRATEGY_CONFIG = {
    "enabled": False  # Disable
}
```
- [ ] Set `enabled: False`
- [ ] Restart bot
- [ ] Verify dashboard shows "Legacy Mode"
- [ ] Verify bot uses original analysis logic
- [ ] Re-enable and confirm strategy system works again

### Custom Parameters
```python
"strategy_params": {
    "ema_crossover": {
        "min_strength": 0.8  # Higher threshold
    }
}
```
- [ ] Modify parameter in config
- [ ] Restart bot
- [ ] Verify parameter takes effect (fewer signals)
- [ ] Check activity feed for threshold mentions
- [ ] Test with multiple parameters

### Strategy at Startup
- [ ] Set `active_strategy: "macd"` in config
- [ ] Restart bot
- [ ] Verify MACD is active strategy on dashboard
- [ ] Verify first signal uses MACD strategy
- [ ] Change via dashboard and confirm it works

## 6. Activity Feed Integration

### Signal Analysis Logging
- [ ] Wait for bot to scan markets
- [ ] Check activity feed for "Signal Analysis" entries
- [ ] Verify strategy name is shown
- [ ] Verify signal action (LONG/SHORT/FLAT)
- [ ] Verify strength percentage
- [ ] Check "reasons" list is populated
- [ ] Verify reasons explain strategy decision

### Filter by Strategy
- [ ] Click "Signals" filter in activity feed
- [ ] Verify only signal analysis shown
- [ ] Check that strategy reasoning is clear
- [ ] Verify different strategies have different reasoning styles

## 7. API Endpoint Tests

### List Strategies
```bash
curl http://localhost:5000/api/strategies/list
```
- [ ] Returns success: true
- [ ] Lists all 4 strategies
- [ ] Shows which strategy is active
- [ ] Includes strategy metadata (timeframes, indicators)
- [ ] Shows strategy_system_enabled status

### Get Active Strategy
```bash
curl http://localhost:5000/api/strategies/active
```
- [ ] Returns success: true
- [ ] Shows active strategy details
- [ ] Includes name, description, version
- [ ] Shows required timeframes and indicators
- [ ] Includes parameters

### Toggle Strategy System
```bash
curl -X POST http://localhost:5000/api/strategies/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```
- [ ] Disables strategy system
- [ ] Returns success message
- [ ] Dashboard updates to show "Legacy Mode"
- [ ] Re-enable with `"enabled": true`

## 8. Error Handling Tests

### Invalid Strategy ID
- [ ] Try to set non-existent strategy via API
- [ ] Verify error message returned
- [ ] Bot continues working
- [ ] Dashboard shows current strategy unchanged

### Missing Data
- [ ] Temporarily disable internet (if testing)
- [ ] Verify strategy returns flat signal
- [ ] Check activity feed shows "Insufficient data" reason
- [ ] Reconnect and verify recovery

### Configuration Errors
- [ ] Set invalid parameter value
- [ ] Restart bot
- [ ] Verify error logged or defaults used
- [ ] Bot doesn't crash

## 9. Performance Tests

### Strategy Switching Speed
- [ ] Time how long strategy switch takes (should be < 1 second)
- [ ] Verify no lag in dashboard update
- [ ] Check bot doesn't pause during switch

### Signal Generation Time
- [ ] Monitor log for signal generation duration
- [ ] Should complete in < 5 seconds per pair
- [ ] All strategies should have similar performance
- [ ] No memory leaks over time

### Dashboard Refresh
- [ ] Monitor network tab (F12) for API call frequency
- [ ] Verify calls every 5 seconds (not every 1 second)
- [ ] Check response times (should be < 500ms)
- [ ] No errors or failed requests

## 10. Integration Tests

### Full Trading Cycle
- [ ] Enable strategy system with EMA Crossover
- [ ] Wait for signal with strength >= 0.7
- [ ] Verify position opened (if signal generated)
- [ ] Check activity feed logs:
  - [ ] Market scan
  - [ ] Signal analysis with reasons
  - [ ] Position decision
  - [ ] Position opened (if applicable)
- [ ] Monitor position management
- [ ] Verify strategy name in position metadata

### Multi-Strategy Test
- [ ] Run EMA Crossover for 30 minutes, note signals
- [ ] Switch to MACD, run for 30 minutes, note signals
- [ ] Switch to RSI, run for 30 minutes, note signals
- [ ] Compare signal frequency and strength
- [ ] Verify each strategy has distinct behavior

## 11. Documentation Tests

### README Files
- [ ] Read [STRATEGY_QUICK_START.md](STRATEGY_QUICK_START.md) - understandable?
- [ ] Read [STRATEGY_ARCHITECTURE.md](STRATEGY_ARCHITECTURE.md) - comprehensive?
- [ ] Read [strategies/README.md](strategies/README.md) - helpful for developers?
- [ ] Check code examples - do they work?

### Code Comments
- [ ] Open `strategies/base_strategy.py` - well documented?
- [ ] Open `strategies/ema_crossover_strategy.py` - clear?
- [ ] Check docstrings in all strategy files
- [ ] Verify parameter descriptions

## 12. Backward Compatibility Tests

### Legacy Mode
- [ ] Disable strategy system (`enabled: False`)
- [ ] Run bot for several cycles
- [ ] Compare behavior to original bot (should be identical)
- [ ] Check signal format is compatible
- [ ] Verify no errors in logs

### Existing Users
- [ ] Use original `config.py` (without STRATEGY_CONFIG)
- [ ] Verify bot starts without errors
- [ ] Check default behavior maintained
- [ ] Enable strategy system with `combined` strategy
- [ ] Verify behavior remains identical

## 13. Edge Cases

### No Market Data
- [ ] Test with invalid trading pair
- [ ] Verify strategy handles gracefully
- [ ] Check flat signal returned
- [ ] Bot continues with other pairs

### Extreme Market Conditions
- [ ] Test during high volatility
- [ ] Verify signals still generate correctly
- [ ] Check strength calculations make sense
- [ ] Verify no crashes or errors

### Rapid Strategy Switching
- [ ] Switch strategies 5 times rapidly
- [ ] Verify no race conditions
- [ ] Check each switch completes successfully
- [ ] Verify bot doesn't get confused

## 14. User Experience Tests

### First-Time User
- [ ] Follow [STRATEGY_QUICK_START.md](STRATEGY_QUICK_START.md) step by step
- [ ] Were instructions clear?
- [ ] Could you enable strategy system?
- [ ] Could you switch strategies easily?
- [ ] Were you confused at any point?

### Dashboard Usability
- [ ] Is strategy selector easy to find?
- [ ] Is active strategy clearly displayed?
- [ ] Are reasons in activity feed understandable?
- [ ] Is it obvious which strategy is making decisions?

## 15. Final Validation

### Complete System Test
- [ ] Start fresh bot instance
- [ ] Enable strategy system
- [ ] Set active strategy to "ema_crossover"
- [ ] Open dashboard
- [ ] Let bot run for 1 hour
- [ ] Switch strategy twice during that hour
- [ ] Verify:
  - [ ] No crashes
  - [ ] No errors in logs
  - [ ] Dashboard updates correctly
  - [ ] Activity feed shows clear strategy reasoning
  - [ ] P&L tracked correctly (dry-run)
  - [ ] Bot cycles run on schedule

### Documentation Completeness
- [ ] All features documented?
- [ ] API endpoints documented?
- [ ] Strategy creation guide complete?
- [ ] Examples work as written?
- [ ] No broken links in markdown files?

## Post-Testing

### Checklist Review
- [ ] Note any failed tests
- [ ] Document any bugs found
- [ ] List improvements needed
- [ ] Verify critical features work

### Ready for Use?
- [ ] All critical tests pass
- [ ] Documentation complete
- [ ] No major bugs
- [ ] Performance acceptable

## Testing Summary

Date Tested: _______________
Tester: _______________
Environment: _______________

Tests Passed: ____ / 150+
Critical Failures: ____________
Minor Issues: ____________

Overall Status: [ ] PASS [ ] FAIL [ ] NEEDS WORK

Notes:
________________________________________________________________________________
________________________________________________________________________________
________________________________________________________________________________

## Quick Smoke Test (5 minutes)

If you only have time for a quick test:

1. [ ] Start bot: `python start_trading.py`
2. [ ] Open dashboard: http://localhost:5000
3. [ ] Verify "Trading Strategy" section visible
4. [ ] Change strategy via dropdown
5. [ ] Wait 60 seconds for signal scan
6. [ ] Check activity feed shows strategy reasoning
7. [ ] No errors in console or logs

If all above pass: **System likely working correctly**

# Multi-User Strategy Isolation Fix

## Problem

When multiple users were active simultaneously, the bot was showing incorrect strategy information in the UI. For example:
- User A selected "EMA Crossover"
- User B selected "Support/Resistance Long Only"
- Both users saw inconsistent strategy information - the UI would show one strategy while signals were generated using another

## Root Cause

The issue was caused by using a **global shared strategy manager** in multiple places:

### 1. User Trading Bot Initialization (FIXED)
**File**: `user_trading_bot.py` lines 149-155

**Problem**: When initializing the bot, the code imported and used `get_strategy_manager()` which returns a global singleton. When User A's bot started with "EMA Crossover", it would set the global manager. Then when User B's bot started with "Support/Resistance", it would overwrite the global manager, affecting User A.

**Solution**: Removed the global strategy manager usage. The user's strategy is now passed directly to `get_user_signal_generator()`, which creates a **dedicated strategy manager instance** for each user.

```python
# BEFORE (WRONG - used global manager)
from strategies.strategy_manager import get_strategy_manager
strategy_manager = get_strategy_manager()  # Global singleton!
strategy_manager.set_active_strategy(user_strategy)

# AFTER (CORRECT - uses user's dedicated manager)
self.signal_generator = get_user_signal_generator(
    user_id=self.user_id,
    data_fetcher=self.data_fetcher,
    indicator_config=config.INDICATORS,
    rsi_config=config.INDICATORS['RSI'],
    use_strategy_system=config.STRATEGY_CONFIG.get('enabled', False),
    user_strategy=user_strategy  # Passed directly
)
```

### 2. API Endpoint - Get Active Strategy (FIXED)
**File**: `app.py` `/api/strategies/active` endpoint (lines 1099-1124)

**Problem**: When the UI requested the active strategy, the endpoint would temporarily set the global manager to match the current user's preference. This created a race condition where concurrent requests from different users would overwrite each other.

**Solution**: Create a temporary strategy manager instance just for the request, never modifying the global state.

```python
# BEFORE (WRONG - modified global manager)
strategy_manager = get_strategy_manager()
if user_strategy:
    strategy_manager.set_active_strategy(user_strategy)  # Affects all users!

# AFTER (CORRECT - temporary instance)
temp_manager = StrategyManager()  # New instance, isolated
temp_manager.set_active_strategy(user_strategy_id)
active_info = temp_manager.get_active_strategy_info()
```

### 3. API Endpoint - Set Active Strategy (FIXED)
**File**: `app.py` `/api/strategies/set` endpoint (lines 1127-1189)

**Problem**: Similar to #2, this endpoint used the global manager to validate and set the strategy.

**Solution**: Use a temporary strategy manager instance for validation only. The actual user preference is saved to the database, and the user's cached signal generator is updated directly.

```python
# BEFORE (WRONG)
strategy_manager = get_strategy_manager()
strategy_manager.set_active_strategy(strategy_id)

# AFTER (CORRECT)
temp_manager = StrategyManager()  # Temporary for validation
temp_manager.set_active_strategy(strategy_id, params)

# Save to database (user-specific)
user_profile.default_strategy = strategy_id
db.session.commit()

# Update user's signal generator (user-specific)
update_user_strategy(current_user.id, strategy_id)
```

## How User Isolation Works Now

Each user has their own completely isolated strategy execution:

1. **UserSignalGenerator**: Creates a dedicated `StrategyManager` instance (not global)
   - Location: `user_signal_generator.py` lines 46-56
   - Each user's generator has `self._user_strategy_manager`
   - This manager is independent and never shared

2. **User Profile**: Strategy preference stored in database
   - Location: `models.py` `UserProfile.default_strategy` field
   - Each user's preference is persisted and loaded on bot start

3. **User Bot Status**: Current strategy tracked per-user
   - Location: `user_bot_status.py` `UserBotStatus` model
   - Fields: `active_strategy` (ID) and `active_strategy_name` (display name)
   - Updated when bot starts and when user changes strategy

4. **API Endpoints**: Never use global manager for user-specific operations
   - All endpoints create temporary managers or read from database
   - No cross-user contamination possible

## What Still Uses Global Strategy Manager (OK)

These uses are safe and correct:

1. **List Strategies** (`/api/strategies`): Read-only listing of available strategies
2. **Register Custom Strategy**: Making new strategies available to all users
3. **Strategy Manager Registration**: Initial loading of built-in strategies

## Testing

To verify the fix works:

1. Create two user accounts
2. User A: Select "EMA Crossover" strategy
3. User B: Select "Support/Resistance Long Only" strategy
4. Start both bots simultaneously
5. Verify:
   - User A's activity feed shows EMA Crossover signals
   - User B's activity feed shows Support/Resistance signals
   - Both UIs show correct strategy names independently
   - No cross-contamination occurs

## Files Modified

1. `user_trading_bot.py` - Removed global strategy manager usage in bot initialization
2. `app.py` - Fixed `/api/strategies/active` endpoint to use temporary managers
3. `app.py` - Fixed `/api/strategies/set` endpoint to use temporary managers

## Files Already Correct (No Changes Needed)

1. `user_signal_generator.py` - Already creates dedicated strategy managers
2. `user_bot_status.py` - Already tracks strategy per-user
3. `models.py` - Already has per-user strategy field

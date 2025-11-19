# CoinDCX Futures Wallet API Reference

## API Endpoint

```
GET https://api.coindcx.com/exchange/v1/derivatives/futures/wallets
```

**Authentication Required**: Yes (HMAC-SHA256 signature)

## Response Structure

### Successful Response

The API returns an **array of wallets** for different currencies (INR and USDT):

```json
[
  {
    "id": "6f74f0c0-6441-4fa8-829d-ff5b11e2488e",
    "currency_short_name": "INR",
    "balance": "0.01584248384583",
    "locked_balance": "0.0",
    "cross_order_margin": "0.0",
    "cross_user_margin": "0.0"
  },
  {
    "id": "7d7861d7-a1aa-4f75-8c0e-ee2d040b1da7",
    "currency_short_name": "USDT",
    "balance": "2.60129806728916",
    "locked_balance": "0.0",
    "cross_order_margin": "0.0",
    "cross_user_margin": "0.0"
  }
]
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique wallet identifier (UUID) |
| `currency_short_name` | string | Currency code (e.g., "USDT", "INR") |
| `balance` | string | Total balance in the wallet |
| `locked_balance` | string | Balance locked in active orders |
| `cross_order_margin` | string | Margin reserved for cross orders |
| `cross_user_margin` | string | User margin in cross positions |

## Balance Calculations

### Available Balance
```
Available Balance = balance - locked_balance
```

**Example:**
```
Balance: 2.60 USDT (rounded from 2.60129806728916)
Locked: 0.0 USDT
Available: 2.60 USDT
```

**Note**: All balances are rounded to 2 decimal places for display.

### Used Margin
```
Used Margin = locked_balance + cross_user_margin
```

**Example:**
```
Locked Balance: 0.0 USDT
Cross User Margin: 0.68534648 USDT
Used Margin: 0.68534648 USDT
```

### Free Balance (for new positions)
```
Free Balance = balance - locked_balance - cross_user_margin
```

**Example:**
```
Balance: 6.1693226 USDT
Locked: 0.0 USDT
Cross User Margin: 0.68534648 USDT
Free Balance: 5.48397612 USDT
```

## Python Implementation

### Using the Wallet Manager

```python
from coindcx_client import CoinDCXFuturesClient
from wallet_manager import WalletManager
import config

# Initialize client
client = CoinDCXFuturesClient(
    api_key=config.API_KEY,
    api_secret=config.API_SECRET
)

# Initialize wallet manager
wallet = WalletManager(client)

# Get balance summary
summary = wallet.get_balance_summary()

print(f"Total: {summary['total_balance']} USDT")
print(f"Available: {summary['available_balance']} USDT")
print(f"Locked: {summary['locked_balance']} USDT")
```

### Balance Summary Structure

```python
{
    'available_balance': 6.1693226,      # balance - locked_balance
    'total_balance': 6.1693226,          # balance field
    'locked_balance': 0.0,               # locked_balance field
    'cross_order_margin': 0.0,           # cross_order_margin field
    'cross_user_margin': 0.68534648,     # cross_user_margin field
    'used_margin': 0.68534648            # locked_balance + cross_user_margin
}
```

## Wallet Manager Methods

### 1. `get_futures_balance(currency="USDT")` → Dict
Get raw wallet data for a specific currency

```python
# Get USDT wallet (default)
balance = wallet.get_futures_balance()
# Returns: {'id': '...', 'currency_short_name': 'USDT', 'balance': '2.60...', ...}

# Get INR wallet
inr_balance = wallet.get_futures_balance(currency="INR")
# Returns: {'id': '...', 'currency_short_name': 'INR', ...}
```

### 2. `get_available_balance()` → float
Get available balance for trading

```python
available = wallet.get_available_balance()
# Returns: 2.60 (rounded to 2 decimal places)
```

### 3. `get_total_balance()` → float
Get total wallet balance

```python
total = wallet.get_total_balance()
# Returns: 2.60 (rounded to 2 decimal places)
```

### 4. `get_balance_summary()` → Dict
Get comprehensive balance breakdown

```python
summary = wallet.get_balance_summary()
# Returns: {
#     'available_balance': 2.60,
#     'total_balance': 2.60,
#     'locked_balance': 0.0,
#     'cross_order_margin': 0.0,
#     'cross_user_margin': 0.0,
#     'used_margin': 0.0
# }
# Note: All values rounded to 2 decimal places
```

### 5. `get_all_wallet_balances()` → List[Dict]
Get balances for all currencies

```python
all_balances = wallet.get_all_wallet_balances()
# Returns: [
#     {
#         'currency': 'INR',
#         'total_balance': 0.02,
#         'locked_balance': 0.0,
#         'available_balance': 0.02,
#         'cross_order_margin': 0.0,
#         'cross_user_margin': 0.0
#     },
#     {
#         'currency': 'USDT',
#         'total_balance': 2.60,
#         'locked_balance': 0.0,
#         'available_balance': 2.60,
#         'cross_order_margin': 0.0,
#         'cross_user_margin': 0.0
#     }
# ]
```

### 6. `check_sufficient_balance(amount)` → bool
Check if sufficient balance exists

```python
has_funds = wallet.check_sufficient_balance(5.0)
# Returns: True (since available = 6.17 USDT > 5.0 USDT)
```

### 7. `calculate_max_position_value(percent, leverage)` → float
Calculate maximum position size

```python
max_value = wallet.calculate_max_position_value(
    max_percent=10,  # Use 10% of balance
    leverage=5       # 5x leverage
)
# Returns: 3.08466 (6.17 * 0.10 * 5)
```

### 8. `get_balance_health()` → Dict
Check account health status

```python
health = wallet.get_balance_health()
# Returns: {
#     'status': 'healthy',
#     'utilization_percent': 11.11,
#     'available_balance': 5.48,
#     'total_balance': 6.17,
#     'used_margin': 0.69
# }
```

## Balance States

### 1. Healthy (< 60% utilization)
- **Status**: `healthy`
- **Color**: Green
- **Action**: Normal trading allowed

### 2. Warning (60-80% utilization)
- **Status**: `warning`
- **Color**: Yellow
- **Action**: Consider reducing positions

### 3. Critical (> 80% utilization)
- **Status**: `critical`
- **Color**: Red
- **Action**: High risk of liquidation

## Example Scenarios

### Scenario 1: No Active Positions
```json
{
  "balance": "100.0",
  "locked_balance": "0.0",
  "cross_user_margin": "0.0"
}
```
- Available: 100.0 USDT
- Can open new positions
- Health: Healthy (0% utilization)

### Scenario 2: Active Position with Margin
```json
{
  "balance": "100.0",
  "locked_balance": "0.0",
  "cross_user_margin": "20.0"
}
```
- Available: 100.0 USDT (not locked in orders)
- Used Margin: 20.0 USDT (position margin)
- Free: 80.0 USDT (for new positions)
- Health: Healthy (20% utilization)

### Scenario 3: Active Orders + Position
```json
{
  "balance": "100.0",
  "locked_balance": "10.0",
  "cross_user_margin": "30.0"
}
```
- Available: 90.0 USDT (100 - 10 locked)
- Used Margin: 40.0 USDT (10 + 30)
- Free: 60.0 USDT (for new positions)
- Health: Warning (40% utilization)

### Scenario 4: High Utilization
```json
{
  "balance": "100.0",
  "locked_balance": "5.0",
  "cross_user_margin": "80.0"
}
```
- Available: 95.0 USDT
- Used Margin: 85.0 USDT
- Free: 15.0 USDT
- Health: Critical (85% utilization)

## Testing

Run the test script to verify wallet integration:

```bash
python test_wallet.py
```

This will:
1. Connect to CoinDCX API
2. Retrieve wallet details
3. Display all balance calculations
4. Test balance health checks
5. Verify sufficient balance checks

## Dashboard Integration

The Flask dashboard ([app.py](app.py)) uses wallet manager:

```python
# In /api/status endpoint
wallet_info = wallet_manager.get_balance_summary()

status = {
    'wallet': {
        'total_balance': wallet_info['total_balance'],
        'available_balance': wallet_info['available_balance'],
        'locked_balance': wallet_info['used_margin'],
        'currency': 'USDT'
    }
}
```

## Common Issues

### Issue 1: Balance shows 0.0
**Cause**: No USDT in futures wallet
**Solution**: Transfer USDT to futures wallet on CoinDCX

### Issue 2: Available < Total but locked = 0
**Cause**: Active positions using margin
**Solution**: Check `cross_user_margin` field

### Issue 3: API returns empty array
**Cause**: No wallet created yet
**Solution**: Deposit funds to create wallet

## Best Practices

1. **Cache Balance Data**: Don't query on every request
   ```python
   # Good: Cache for 30 seconds
   if not cached or age > 30:
       balance = wallet.get_balance_summary()
   ```

2. **Check Before Trading**: Always verify sufficient balance
   ```python
   if wallet.check_sufficient_balance(required_margin):
       place_order()
   ```

3. **Monitor Health**: Check utilization regularly
   ```python
   health = wallet.get_balance_health()
   if health['status'] == 'critical':
       alert_user()
   ```

4. **Handle Errors**: API can fail or timeout
   ```python
   try:
       balance = wallet.get_total_balance()
   except Exception as e:
       logger.error(f"Failed to get balance: {e}")
       return cached_balance
   ```

## References

- [CoinDCX Futures API Docs](https://docs.coindcx.com/)
- [Wallet Manager Implementation](wallet_manager.py)
- [Test Script](test_wallet.py)
- [Dashboard Integration](app.py)

---

**Updated**: November 2024
**API Version**: v1
**Authentication**: HMAC-SHA256

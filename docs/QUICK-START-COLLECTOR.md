# Quick Start: Data Collector with API Authentication

## Step 1: Enable API Key Authentication

API key authentication is now **enabled** in your `local-env`:
```bash
API_KEY_REQUIRED=true
```

## Step 2: Generate Admin API Key

Run the key generator script:

```bash
python scripts/generate_admin_api_key.py
```

**Output:**
```
============================================================
✓ Admin API Key Generated Successfully!
============================================================

Key ID:  a1b2c3d4e5f6...
API Key: AbCdEf123456...XyZ

⚠ IMPORTANT: Save this API key securely!
   It will NOT be shown again.
============================================================
```

**Save this API key!** You'll need it for all admin operations.

## Step 3: Start the API Server

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Load environment
export $(cat local-env | xargs)  # Linux/Mac
# or
set -a; source local-env; set +a  # Alternative

# Start API
python run_api.py
```

## Step 4: Test Authentication

```bash
# Replace YOUR_API_KEY with the key from Step 2
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status
```

**Expected Response:**
```json
{
  "is_running": false,
  "status": "idle",
  "timestamp": "2024-11-12T..."
}
```

## Step 5: Trigger Data Collection

### Collect Historical Data (100 cryptos from Jan 2025)

```bash
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "backward",
    "start_date": "2025-01-01T00:00:00Z"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Collection task started: backward",
  "mode": "backward",
  "start_date": "2025-01-01T00:00:00Z",
  "status_endpoint": "/api/admin/collect/status"
}
```

## Step 6: Monitor Progress

```bash
# Check status every 30 seconds
watch -n 30 'curl -s -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status | jq'
```

**Progress Output:**
```json
{
  "is_running": true,
  "current_operation": "backward",
  "status": "running",
  "elapsed_seconds": 180,
  "last_results": {
    "total_cryptos": 45,
    "complete": 40,
    "partial": 3,
    "failed": 2,
    "skipped": 0,
    "total_records": 324000
  }
}
```

## What Happens During Collection?

### Smart Resume in Action

**First Run (interrupted at crypto #50):**
```
[INFO] Starting backward collection: 100 cryptos from 2025-01-01 to 2025-11-12
[INFO] BTC: Found 1 missing range(s)
[INFO] BTC: Collected 7920 records for range 2025-01-01 to 2025-11-12
[INFO] ✓ BTC: Collected 7920 records in 9.1s
[INFO] ETH: Found 1 missing range(s)
[INFO] ETH: Collected 7920 records in 8.8s
...
[INFO] DOGE: Found 1 missing range(s)
[INFO] DOGE: Collected 3960 records in 4.5s
[ERROR] Connection interrupted!  ← Stopped here
```

**Restart Collection (automatic resume):**
```
[INFO] Starting backward collection: 100 cryptos from 2025-01-01 to 2025-11-12
[INFO] BTC: All data already exists, skipping
[INFO] ETH: All data already exists, skipping
...
[INFO] DOGE: Found 1 missing range(s)  ← Resumes here!
[INFO] DOGE: Collected 3960 records in 4.3s
[INFO] ✓ DOGE: Collected 3960 records in 4.3s
[INFO] SHIB: Found 1 missing range(s)
[INFO] SHIB: Collected 7920 records in 9.0s
...
```

### Retry Logic in Action

```
[INFO] BTC: Found 1 missing range(s)
[WARNING] BTC: API error (attempt 1/3), retrying in 2s: Rate limit exceeded
[INFO] BTC: Collected 7200 records in 10.5s (after 1 retry)
[INFO] ✓ BTC: Collected 7200 records in 10.5s
```

## Common Scenarios

### Scenario 1: Initial Historical Collection

```bash
# Collect 11 months of data for 100 cryptos
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "backward",
    "start_date": "2025-01-01T00:00:00Z"
  }'

# Expected time: 8-12 minutes
# Expected records: ~792,000 (100 cryptos × 7,920 hours)
```

### Scenario 2: Daily Update

```bash
# Get latest data (runs automatically every 6 hours via scheduler)
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode": "forward"}'

# Expected time: 1-2 minutes
# Expected records: ~100-600 (depending on time since last update)
```

### Scenario 3: Fill Gaps

```bash
# Detect and fill any missing data
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "gap_fill",
    "start_date": "2025-01-01T00:00:00Z"
  }'

# Expected time: Varies (only fills gaps)
```

## Troubleshooting

### Error: "Missing API key"

```json
{
  "error": {
    "code": "MISSING_API_KEY",
    "message": "API key required"
  }
}
```

**Solution:** Add API key to request:
```bash
curl -H "X-API-Key: YOUR_API_KEY" ...
```

### Error: "Invalid API key"

```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "Invalid API key"
  }
}
```

**Solution:** Generate a new API key:
```bash
python scripts/generate_admin_api_key.py
```

### Error: "Collection already in progress"

```json
{
  "error": {
    "code": "COLLECTION_IN_PROGRESS",
    "message": "Data collection is already in progress"
  }
}
```

**Solution:** Wait for current collection to finish, or check status:
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status
```

### Collection is Slow

**Normal for initial collection:**
- 100 cryptos × 11 months = ~880 API requests
- Binance rate limits may cause delays
- Expected time: 8-12 minutes

**Check progress:**
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status | jq '.last_results'
```

## Next Steps

1. **Set up scheduled collection:**
   - The scheduler runs automatically every 6 hours
   - Configured via `COLLECTION_SCHEDULE=0 */6 * * *`

2. **Monitor via Dashboard:**
   - Start dashboard: `python run_dashboard.py`
   - Access: http://localhost:8501
   - View real-time progress and results

3. **Check data quality:**
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" \
     http://localhost:5000/api/admin/system/info
   ```

4. **Run predictions:**
   - Once data is collected, predictions will be generated automatically
   - Check: http://localhost:5000/api/predictions/top20

## Summary

✅ **API Key Authentication**: Enabled and configured  
✅ **Smart Resume**: Automatically continues from where it left off  
✅ **Retry Logic**: Failed batches are retried automatically  
✅ **Progress Tracking**: Real-time status via API  
✅ **No Duplicates**: Database-driven collection prevents duplicate requests  

**You're all set!** The collector will now safely handle interruptions and resume automatically.

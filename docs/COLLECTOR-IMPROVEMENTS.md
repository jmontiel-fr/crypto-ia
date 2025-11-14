# Data Collector Improvements - Option 3 Implementation

## Overview

The data collector has been enhanced with interruption-safe collection and smart resume capabilities. The system now intelligently checks for existing data and only fetches missing ranges, with automatic retry logic for failed requests.

## Key Features

### 1. **Smart Resume (Database-Driven)**
- Checks database before each crypto to see what data already exists
- Calculates missing date ranges dynamically
- Only requests data for gaps
- Natural resume capability - just restart and it continues where it left off
- No duplicate API calls

### 2. **Automatic Retry with Exponential Backoff**
- Failed batches are retried up to 3 times (configurable)
- Exponential backoff: 2s, 4s, 8s between retries
- Continues to next crypto if all retries fail
- Tracks retry count per crypto

### 3. **Enhanced Status Tracking**
- **Complete**: All data collected successfully
- **Partial**: Some data collected, some ranges failed
- **Failed**: No data collected
- **Skipped**: All data already exists in database

### 4. **Real-Time Progress Monitoring**
- Per-crypto progress tracking
- Overall collection progress
- Detailed error reporting
- Recent results summary

### 5. **API Key Authentication**
- Admin endpoints now require API key authentication
- Generate keys with `python scripts/generate_admin_api_key.py`
- Keys can be provided via header or query parameter

## Usage

### Generate Admin API Key

```bash
python scripts/generate_admin_api_key.py
```

Save the generated API key securely - it won't be shown again!

### Trigger Collection (with API Key)

```bash
# Using X-API-Key header
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "backward",
    "start_date": "2025-01-01T00:00:00Z"
  }'

# Using Authorization header
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "forward"
  }'

# Using query parameter
curl -X POST "http://localhost:5000/api/admin/collect/trigger?api_key=YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "gap_fill"
  }'
```

### Check Collection Status

```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
  http://localhost:5000/api/admin/collect/status
```

**Response:**
```json
{
  "is_running": true,
  "current_operation": "backward",
  "status": "running",
  "elapsed_seconds": 120,
  "last_results": {
    "total_cryptos": 100,
    "complete": 85,
    "partial": 10,
    "failed": 3,
    "skipped": 2,
    "total_records": 720000,
    "details": [...]
  }
}
```

## Collection Modes

### Backward Collection
Collects historical data from start_date to yesterday:
```json
{
  "mode": "backward",
  "start_date": "2025-01-01T00:00:00Z"
}
```

### Forward Collection
Updates data from last recorded timestamp to now:
```json
{
  "mode": "forward"
}
```

### Gap Fill
Detects and fills gaps in existing data:
```json
{
  "mode": "gap_fill",
  "start_date": "2025-01-01T00:00:00Z"
}
```

## Interruption Handling

### What Happens on Interruption?

1. **During Collection**: Data is saved immediately after each batch
2. **On Restart**: System checks database and only fetches missing data
3. **No Duplicates**: Database constraints prevent duplicate records
4. **Resume Automatically**: Just trigger collection again - it picks up where it left off

### Example Scenario

**Initial Run (interrupted at crypto #50):**
```
BTC: Complete (7,200 records)
ETH: Complete (7,200 records)
...
DOGE: Partial (3,600 records) ← Interrupted here
...
```

**Restart Collection:**
```
BTC: Skipped (already complete)
ETH: Skipped (already complete)
...
DOGE: Resume (collect remaining 3,600 records)
SHIB: Start fresh
...
```

## Configuration

### Environment Variables

```bash
# Enable API key authentication
API_KEY_REQUIRED=true

# Number of cryptos to track
TOP_N_CRYPTOS=100

# Collection schedule (cron format)
COLLECTION_SCHEDULE=0 */6 * * *

# Start date for historical data
COLLECTION_START_DATE=2025-01-01
```

### Collector Settings

```python
collector = CryptoCollector(
    binance_client=binance_client,
    top_n_cryptos=100,
    batch_size_hours=720,  # 30 days per batch
    max_retries=3  # Retry failed batches 3 times
)
```

## Monitoring

### Check Progress

```bash
# Get detailed status
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:5000/api/admin/collect/status | jq

# Get system info
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:5000/api/admin/system/info | jq
```

### Dashboard

Access the Streamlit dashboard at http://localhost:8501 to:
- View collection progress in real-time
- Trigger manual collections
- Monitor system health
- View detailed results

## Error Handling

### Automatic Retry
- API errors are retried automatically (up to 3 times)
- Exponential backoff prevents rate limiting
- Failed ranges are tracked for manual retry

### Partial Success
- If some batches fail, collected data is still saved
- Status shows "partial" with missing ranges
- Can re-run collection to fill gaps

### Complete Failure
- If all batches fail, status shows "failed"
- Error message indicates the issue
- Can retry after fixing the problem

## Performance

### For 100 Cryptos with 11 Months of History (Jan 2025 - Nov 2025)

**Initial Collection:**
- ~880 API requests (8-9 per crypto)
- ~8-12 minutes total time
- ~792,000 hourly records

**Subsequent Runs:**
- Only fetches new/missing data
- Skips already-collected cryptos
- Much faster (seconds to minutes)

**Storage:**
- SQLite: ~100-200 MB
- PostgreSQL: Similar, with better performance

## Troubleshooting

### Collection Not Starting
- Check API key is valid: `curl -H "X-API-Key: YOUR_KEY" http://localhost:5000/api/admin/collect/status`
- Verify API_KEY_REQUIRED=true in config
- Check if collection is already running

### Slow Collection
- Normal for initial historical collection (100 cryptos × 11 months)
- Binance rate limits may cause delays
- Check network connectivity

### Partial Results
- Some ranges failed - check error messages
- May be temporary API issues
- Re-run collection to fill gaps

### Missing Data
- Run gap_fill mode to detect and fill gaps
- Check Binance API availability for specific symbols
- Verify date ranges are valid

## Best Practices

1. **Initial Setup**: Run backward collection once for historical data
2. **Scheduled Updates**: Use forward collection every 6 hours
3. **Gap Maintenance**: Run gap_fill weekly to ensure completeness
4. **Monitor Status**: Check dashboard regularly for failures
5. **Secure Keys**: Store API keys securely, rotate periodically

## API Reference

### POST /api/admin/collect/trigger
Trigger manual data collection.

**Headers:**
- `X-API-Key` or `Authorization: Bearer <key>` (required)

**Body:**
```json
{
  "mode": "backward|forward|gap_fill",
  "start_date": "2025-01-01T00:00:00Z",  // optional
  "end_date": "2025-12-31T23:59:59Z"     // optional
}
```

**Response:** 202 Accepted
```json
{
  "success": true,
  "message": "Collection task started: backward",
  "mode": "backward",
  "status_endpoint": "/api/admin/collect/status"
}
```

### GET /api/admin/collect/status
Get current collection status.

**Headers:**
- `X-API-Key` or `Authorization: Bearer <key>` (required)

**Response:** 200 OK
```json
{
  "is_running": false,
  "status": "idle",
  "last_results": {
    "total_cryptos": 100,
    "complete": 95,
    "partial": 3,
    "failed": 2,
    "skipped": 0,
    "total_records": 720000
  }
}
```

## Migration from Old Collector

The new collector is backward compatible. Existing data will be detected and skipped automatically. No migration needed!

Just update your code and restart - the collector will:
1. Check what data already exists
2. Only fetch missing ranges
3. Continue from where the old collector left off

## Support

For issues or questions:
1. Check logs: `logs/crypto_saas.log`
2. Review collection status via API
3. Check dashboard for detailed results
4. Verify API key authentication is working

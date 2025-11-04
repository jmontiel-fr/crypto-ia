# Cryptocurrency Data Collectors

This module provides components for collecting cryptocurrency price data from Binance API and managing the collection process.

## Components

### 1. BinanceClient

A robust API client for interacting with Binance's public API.

**Features:**
- Automatic retry with exponential backoff
- Rate limiting to respect API constraints
- Support for hourly price data (klines)
- Market cap ranking (using volume as proxy)
- Connection testing

**Example:**
```python
from src.collectors import BinanceClient
from datetime import datetime, timedelta

# Initialize client
client = BinanceClient(
    api_key="optional",  # Not required for public endpoints
    api_secret="optional",
    max_retries=3,
    retry_delay=1.0
)

# Test connectivity
if client.test_connectivity():
    print("Connected to Binance API")

# Get top cryptocurrencies by volume
top_cryptos = client.get_top_by_market_cap(limit=50)
for crypto in top_cryptos:
    print(f"{crypto.symbol}: ${crypto.current_price}")

# Get hourly price data
end_time = datetime.now()
start_time = end_time - timedelta(days=7)
prices = client.get_hourly_prices(
    symbol="BTCUSDT",
    start_time=start_time,
    end_time=end_time
)
```

### 2. DataGapDetector

Identifies missing time ranges in historical data.

**Features:**
- Backward gap detection (from start_date to yesterday)
- Forward gap detection (from last record to now)
- Internal gap detection (missing hours within range)
- Collection status summary

**Example:**
```python
from src.collectors import DataGapDetector
from src.data import session_scope
from datetime import datetime

with session_scope() as session:
    detector = DataGapDetector(session)
    
    # Find gaps for a cryptocurrency
    gaps = detector.find_all_gaps(
        crypto_id=1,
        crypto_symbol="BTC",
        start_date=datetime(2024, 1, 1),
        end_date=datetime.now()
    )
    
    for gap in gaps:
        print(f"Gap: {gap.start_time} to {gap.end_time} ({gap.hours_missing} hours)")
    
    # Get collection summary
    summary = detector.get_collection_summary(1, "BTC")
    print(f"Completeness: {summary['completeness_percent']:.1f}%")
```

### 3. CryptoCollector

Main orchestrator for data collection operations.

**Features:**
- Backward collection (historical data)
- Forward collection (recent updates)
- Gap filling
- Progress tracking
- Batch processing
- Automatic persistence to database

**Example:**
```python
from src.collectors import BinanceClient, CryptoCollector
from datetime import datetime, timedelta

# Initialize components
client = BinanceClient()
collector = CryptoCollector(
    binance_client=client,
    top_n_cryptos=50,
    batch_size_hours=720  # 30 days per batch
)

# Collect historical data (backward)
start_date = datetime(2024, 1, 1)
results = collector.collect_backward(
    start_date=start_date,
    crypto_symbols=["BTC", "ETH", "SOL"]
)

# Update with recent data (forward)
results = collector.collect_forward()

# Fill gaps in existing data
results = collector.detect_and_fill_gaps()

# Get collection status
status = collector.get_collection_status()
print(f"Total records collected: {status['total_records_collected']}")
```

### 4. CollectorScheduler

Automated scheduler for periodic data collection.

**Features:**
- Cron-based scheduling
- Manual trigger capability
- Status tracking (idle, running, error)
- Job event listening
- Pause/resume functionality

**Example:**
```python
from src.collectors import BinanceClient, CryptoCollector, CollectorScheduler
from datetime import datetime, timedelta

# Initialize components
client = BinanceClient()
collector = CryptoCollector(client, top_n_cryptos=50)

# Create scheduler (runs every 6 hours)
scheduler = CollectorScheduler(
    binance_client=client,
    crypto_collector=collector,
    schedule_cron="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2024, 1, 1)
)

# Start automated collection
scheduler.start()

# Get status
status = scheduler.get_status()
print(f"Status: {status['status']}")
print(f"Next run: {status.get('next_run_time')}")

# Manual trigger
result = scheduler.trigger_manual_collection(
    collection_type="forward",
    crypto_symbols=["BTC", "ETH"]
)

# Stop scheduler
scheduler.stop()
```

## Data Flow

```
┌─────────────────┐
│  Binance API    │
└────────┬────────┘
         │
         │ fetch price data
         ▼
┌─────────────────┐
│ BinanceClient   │
└────────┬────────┘
         │
         │ PriceData objects
         ▼
┌─────────────────┐
│ CryptoCollector │◄──── DataGapDetector
└────────┬────────┘      (identifies gaps)
         │
         │ persist
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   Database      │
└─────────────────┘
         ▲
         │
         │ schedule
┌────────┴────────┐
│CollectorScheduler│
└─────────────────┘
```

## Configuration

The collectors use environment variables from `.env`:

```bash
# Data Collection
COLLECTION_START_DATE=2024-01-01
TOP_N_CRYPTOS=50
COLLECTION_SCHEDULE=0 */6 * * *  # Cron expression

# Binance API (optional for public endpoints)
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

## Error Handling

All components implement robust error handling:

- **BinanceClient**: Automatic retry with exponential backoff, rate limiting
- **CryptoCollector**: Continues on individual crypto failures, logs errors
- **CollectorScheduler**: Tracks error status, continues on next schedule

## Rate Limiting

The BinanceClient respects Binance API limits:
- Max 1200 requests per minute
- Max 6000 request weight per minute
- Automatic throttling when approaching limits

## Testing

Run the test suite:

```bash
python examples/test_collectors.py
```

This will test:
1. Binance API connectivity
2. Top cryptocurrency retrieval
3. Sample data collection
4. Full collector workflow
5. Gap detection
6. Scheduler functionality

## Best Practices

1. **Initial Collection**: Use `collect_backward()` to gather historical data
2. **Regular Updates**: Use `collect_forward()` or scheduler for recent data
3. **Gap Filling**: Periodically run `detect_and_fill_gaps()` to ensure completeness
4. **Monitoring**: Check `get_collection_status()` and `get_status()` regularly
5. **Error Recovery**: Review failed collections and retry if needed

## Performance

- **Batch Size**: Default 720 hours (30 days) balances API calls and memory
- **Concurrency**: Sequential processing to respect rate limits
- **Database**: Bulk inserts for efficiency
- **Caching**: No caching (always fresh data from API)

## Troubleshooting

### Connection Errors
```python
# Test connectivity first
if not client.test_connectivity():
    print("Check network connection and Binance API status")
```

### Rate Limiting
```python
# Reduce batch size or add delays
collector = CryptoCollector(
    binance_client=client,
    batch_size_hours=360  # Smaller batches
)
```

### Missing Data
```python
# Use gap detector to identify issues
with session_scope() as session:
    detector = DataGapDetector(session)
    summary = detector.get_collection_summary(crypto_id, symbol)
    print(f"Completeness: {summary['completeness_percent']:.1f}%")
```

## Future Enhancements

- Multi-exchange support (Coinbase, Kraken)
- WebSocket streaming for real-time data
- Parallel collection with rate limit coordination
- Data validation and quality checks
- Automatic retry of failed collections

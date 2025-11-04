"""
Example script demonstrating the cryptocurrency data collector usage.

This script shows how to:
1. Initialize the Binance client
2. Create a crypto collector
3. Collect historical data (backward)
4. Update with recent data (forward)
5. Set up automated collection with scheduler
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.collectors import (
    BinanceClient,
    CryptoCollector,
    CollectorScheduler,
    DataGapDetector
)
from src.config import load_config
from src.data import init_db, session_scope
from src.utils.logger import setup_logging


def test_binance_connectivity():
    """Test Binance API connectivity."""
    print("\n" + "="*60)
    print("Testing Binance API Connectivity")
    print("="*60)
    
    client = BinanceClient()
    
    if client.test_connectivity():
        print("✓ Binance API connection successful")
        
        # Get server time
        server_time = client.get_server_time()
        print(f"✓ Server time: {server_time}")
        
        return client
    else:
        print("✗ Binance API connection failed")
        return None


def test_get_top_cryptos(client: BinanceClient):
    """Test getting top cryptocurrencies."""
    print("\n" + "="*60)
    print("Getting Top Cryptocurrencies")
    print("="*60)
    
    top_cryptos = client.get_top_by_market_cap(limit=10)
    
    print(f"\nTop {len(top_cryptos)} cryptocurrencies by volume:")
    for i, crypto in enumerate(top_cryptos, 1):
        print(f"{i}. {crypto.symbol:8s} - ${crypto.current_price:>12,.2f}")
    
    return [crypto.symbol for crypto in top_cryptos]


def test_collect_sample_data(client: BinanceClient):
    """Test collecting sample price data."""
    print("\n" + "="*60)
    print("Collecting Sample Price Data")
    print("="*60)
    
    # Collect last 24 hours of BTC data
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    print(f"\nFetching BTC hourly prices from {start_time} to {end_time}")
    
    price_data = client.get_hourly_prices(
        symbol="BTCUSDT",
        start_time=start_time,
        end_time=end_time
    )
    
    print(f"✓ Collected {len(price_data)} hourly price records")
    
    if price_data:
        print(f"\nSample data:")
        print(f"  First: {price_data[0].timestamp} - ${price_data[0].price_usd:,.2f}")
        print(f"  Last:  {price_data[-1].timestamp} - ${price_data[-1].price_usd:,.2f}")
    
    return price_data


def test_crypto_collector():
    """Test the crypto collector orchestrator."""
    print("\n" + "="*60)
    print("Testing Crypto Collector")
    print("="*60)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    print("✓ Database initialized")
    
    # Create Binance client
    client = BinanceClient()
    
    # Create collector (track top 5 for testing)
    collector = CryptoCollector(
        binance_client=client,
        top_n_cryptos=5,
        batch_size_hours=24  # Small batch for testing
    )
    
    print(f"\n✓ Collector initialized (tracking top 5 cryptos)")
    
    # Get tracked cryptocurrencies
    tracked = collector.get_tracked_cryptocurrencies()
    print(f"✓ Tracking: {', '.join(tracked)}")
    
    # Collect last 24 hours (backward)
    print("\nCollecting last 24 hours of data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    results = collector.collect_backward(
        start_date=start_date,
        end_date=end_date,
        crypto_symbols=tracked[:2]  # Just first 2 for testing
    )
    
    print(f"\n✓ Collection completed:")
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.crypto_symbol}: {result.records_collected} records")
    
    return collector


def test_gap_detection():
    """Test gap detection functionality."""
    print("\n" + "="*60)
    print("Testing Gap Detection")
    print("="*60)
    
    with session_scope() as session:
        from src.data.repositories import CryptoRepository
        
        gap_detector = DataGapDetector(session)
        crypto_repo = CryptoRepository(session)
        
        # Get a crypto to test
        crypto = crypto_repo.get_by_symbol("BTC")
        
        if crypto:
            print(f"\nChecking gaps for {crypto.symbol}...")
            
            # Get collection summary
            summary = gap_detector.get_collection_summary(crypto.id, crypto.symbol)
            
            print(f"\nCollection Summary:")
            print(f"  Total records: {summary['total_records']}")
            if summary['has_data']:
                print(f"  Earliest: {summary['earliest_timestamp']}")
                print(f"  Latest: {summary['latest_timestamp']}")
                print(f"  Time span: {summary.get('time_span_days', 0)} days")
                print(f"  Completeness: {summary.get('completeness_percent', 0):.1f}%")
            else:
                print("  No data available")
        else:
            print("No BTC data found in database")


def test_scheduler():
    """Test the collector scheduler."""
    print("\n" + "="*60)
    print("Testing Collector Scheduler")
    print("="*60)
    
    # Create components
    client = BinanceClient()
    collector = CryptoCollector(
        binance_client=client,
        top_n_cryptos=5
    )
    
    # Create scheduler (every 6 hours)
    scheduler = CollectorScheduler(
        binance_client=client,
        crypto_collector=collector,
        schedule_cron="0 */6 * * *",
        start_date=datetime.now() - timedelta(days=7)
    )
    
    print("✓ Scheduler created")
    
    # Get status
    status = scheduler.get_status()
    print(f"\nScheduler Status:")
    print(f"  Status: {status['status']}")
    print(f"  Schedule: {status['schedule']}")
    print(f"  Run count: {status['run_count']}")
    
    # Test manual trigger (forward collection)
    print("\nTriggering manual collection (forward)...")
    result = scheduler.trigger_manual_collection(
        collection_type="forward",
        crypto_symbols=["BTC", "ETH"]
    )
    
    if result['success']:
        print(f"✓ Manual collection successful:")
        print(f"  Total cryptos: {result['results']['total_cryptos']}")
        print(f"  Successful: {result['results']['successful']}")
        print(f"  Total records: {result['results']['total_records']}")
    else:
        print(f"✗ Manual collection failed: {result['message']}")
    
    return scheduler


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Cryptocurrency Data Collector - Test Suite")
    print("="*60)
    
    # Setup logging
    setup_logging(log_level="INFO")
    
    # Load configuration
    config = load_config()
    print(f"\n✓ Configuration loaded")
    print(f"  Environment: {config.ENVIRONMENT}")
    print(f"  Top N Cryptos: {config.TOP_N_CRYPTOS}")
    
    try:
        # Test 1: Binance connectivity
        client = test_binance_connectivity()
        if not client:
            print("\n✗ Cannot proceed without Binance connectivity")
            return
        
        # Test 2: Get top cryptocurrencies
        top_symbols = test_get_top_cryptos(client)
        
        # Test 3: Collect sample data
        test_collect_sample_data(client)
        
        # Test 4: Crypto collector
        collector = test_crypto_collector()
        
        # Test 5: Gap detection
        test_gap_detection()
        
        # Test 6: Scheduler
        scheduler = test_scheduler()
        
        print("\n" + "="*60)
        print("All Tests Completed Successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

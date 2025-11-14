"""
Cryptocurrency data collector orchestrator.
Coordinates data collection from Binance API and persistence to database.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.collectors.binance_client import BinanceClient, BinanceAPIError, PriceData
from src.collectors.gap_detector import DataGapDetector, DataGap
from src.data.repositories import CryptoRepository, PriceHistoryRepository
from src.data.database import session_scope

logger = logging.getLogger(__name__)


@dataclass
class CollectionProgress:
    """Progress tracking for data collection."""
    crypto_symbol: str
    total_hours: int
    collected_hours: int
    failed_hours: int
    start_time: datetime
    current_time: datetime
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_hours == 0:
            return 100.0
        return (self.collected_hours / self.total_hours) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if collection is complete."""
        return self.collected_hours + self.failed_hours >= self.total_hours


@dataclass
class CollectionResult:
    """Result of a collection operation."""
    crypto_symbol: str
    success: bool
    records_collected: int
    time_range_start: datetime
    time_range_end: datetime
    duration_seconds: float
    error_message: Optional[str] = None
    status: str = "complete"  # complete, partial, failed, skipped
    missing_ranges: List[tuple] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.missing_ranges is None:
            self.missing_ranges = []


class CryptoCollector:
    """
    Main orchestrator for cryptocurrency data collection.
    
    Coordinates:
    - Fetching data from Binance API
    - Gap detection in existing data
    - Persistence to database
    - Progress tracking and logging
    """
    
    def __init__(
        self,
        binance_client: BinanceClient,
        top_n_cryptos: int = 50,
        batch_size_hours: int = 720,  # 30 days
        max_retries: int = 3
    ):
        """
        Initialize crypto collector.
        
        Args:
            binance_client: Binance API client instance.
            top_n_cryptos: Number of top cryptocurrencies to track.
            batch_size_hours: Hours of data to fetch per batch.
            max_retries: Maximum retry attempts for failed batches.
        """
        self.binance_client = binance_client
        self.top_n_cryptos = top_n_cryptos
        self.batch_size_hours = batch_size_hours
        self.max_retries = max_retries
        
        # Progress tracking
        self.current_progress: Optional[CollectionProgress] = None
        self.collection_results: List[CollectionResult] = []
        
        logger.info(
            f"CryptoCollector initialized: "
            f"top_n={top_n_cryptos}, batch_size={batch_size_hours}h, "
            f"max_retries={max_retries}"
        )
    
    def get_tracked_cryptocurrencies(self) -> List[str]:
        """
        Get list of cryptocurrency symbols to track.
        
        Returns:
            List of cryptocurrency symbols (e.g., ['BTC', 'ETH', 'SOL']).
        """
        try:
            crypto_infos = self.binance_client.get_top_by_market_cap(self.top_n_cryptos)
            symbols = [info.symbol for info in crypto_infos]
            logger.info(f"Tracking {len(symbols)} cryptocurrencies: {', '.join(symbols[:10])}...")
            return symbols
        except BinanceAPIError as e:
            logger.error(f"Failed to get tracked cryptocurrencies: {e}")
            return []
    
    def collect_backward(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        crypto_symbols: Optional[List[str]] = None
    ) -> List[CollectionResult]:
        """
        Collect historical data backward from end_date to start_date.
        
        This method gathers data from yesterday (or end_date) backward to
        the configured start_date, filling in historical gaps.
        
        Args:
            start_date: Earliest date to collect data from.
            end_date: Latest date to collect data to (default: yesterday).
            crypto_symbols: Specific symbols to collect (default: top N).
        
        Returns:
            List of CollectionResult instances.
        """
        if end_date is None:
            # Default to yesterday at midnight
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get symbols to collect
        if crypto_symbols is None:
            crypto_symbols = self.get_tracked_cryptocurrencies()
        
        if not crypto_symbols:
            logger.error("No cryptocurrencies to collect")
            return []
        
        logger.info(
            f"Starting backward collection: "
            f"{len(crypto_symbols)} cryptos from {start_date} to {end_date}"
        )
        
        results = []
        
        for symbol in crypto_symbols:
            try:
                result = self._collect_for_crypto(
                    symbol=symbol,
                    start_time=start_date,
                    end_time=end_date,
                    direction="backward"
                )
                results.append(result)
                
                if result.success:
                    logger.info(
                        f"✓ {symbol}: Collected {result.records_collected} records "
                        f"in {result.duration_seconds:.1f}s"
                    )
                else:
                    logger.warning(
                        f"✗ {symbol}: Collection failed - {result.error_message}"
                    )
                    
            except Exception as e:
                logger.error(f"Unexpected error collecting {symbol}: {e}")
                results.append(CollectionResult(
                    crypto_symbol=symbol,
                    success=False,
                    records_collected=0,
                    time_range_start=start_date,
                    time_range_end=end_date,
                    duration_seconds=0,
                    error_message=str(e)
                ))
        
        self.collection_results.extend(results)
        self._log_collection_summary(results, "backward")
        
        return results
    
    def collect_forward(
        self,
        end_date: Optional[datetime] = None,
        crypto_symbols: Optional[List[str]] = None
    ) -> List[CollectionResult]:
        """
        Collect recent data forward from last recorded date to present.
        
        This method updates data from the last recorded timestamp forward
        to the current time (or end_date).
        
        Args:
            end_date: Latest date to collect data to (default: now).
            crypto_symbols: Specific symbols to collect (default: top N).
        
        Returns:
            List of CollectionResult instances.
        """
        if end_date is None:
            end_date = datetime.now()
        
        # Get symbols to collect
        if crypto_symbols is None:
            crypto_symbols = self.get_tracked_cryptocurrencies()
        
        if not crypto_symbols:
            logger.error("No cryptocurrencies to collect")
            return []
        
        logger.info(
            f"Starting forward collection: "
            f"{len(crypto_symbols)} cryptos to {end_date}"
        )
        
        results = []
        
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            price_repo = PriceHistoryRepository(session)
            
            for symbol in crypto_symbols:
                try:
                    # Get or create crypto record
                    crypto = crypto_repo.get_or_create(symbol, symbol)
                    
                    # Get latest timestamp
                    latest_timestamp = price_repo.get_latest_timestamp(crypto.id)
                    
                    if latest_timestamp is None:
                        logger.info(
                            f"{symbol}: No existing data, skipping forward collection"
                        )
                        continue
                    
                    # Check if update is needed
                    time_diff = end_date - latest_timestamp
                    if time_diff < timedelta(hours=1):
                        logger.debug(
                            f"{symbol}: Data is up to date (latest: {latest_timestamp})"
                        )
                        continue
                    
                    # Collect from latest timestamp to end_date
                    result = self._collect_for_crypto(
                        symbol=symbol,
                        start_time=latest_timestamp,
                        end_time=end_date,
                        direction="forward"
                    )
                    results.append(result)
                    
                    if result.success:
                        logger.info(
                            f"✓ {symbol}: Collected {result.records_collected} records "
                            f"in {result.duration_seconds:.1f}s"
                        )
                    else:
                        logger.warning(
                            f"✗ {symbol}: Collection failed - {result.error_message}"
                        )
                        
                except Exception as e:
                    logger.error(f"Unexpected error collecting {symbol}: {e}")
                    results.append(CollectionResult(
                        crypto_symbol=symbol,
                        success=False,
                        records_collected=0,
                        time_range_start=latest_timestamp if latest_timestamp else end_date,
                        time_range_end=end_date,
                        duration_seconds=0,
                        error_message=str(e)
                    ))
        
        self.collection_results.extend(results)
        self._log_collection_summary(results, "forward")
        
        return results
    
    def _get_missing_ranges(
        self,
        crypto_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[tuple]:
        """
        Get missing date ranges for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID
            start_time: Start of desired range
            end_time: End of desired range
        
        Returns:
            List of (start, end) tuples for missing data
        """
        with session_scope() as session:
            price_repo = PriceHistoryRepository(session)
            
            # Get all existing timestamps
            existing_timestamps = price_repo.get_timestamps_in_range(
                crypto_id, start_time, end_time
            )
            
            if not existing_timestamps:
                # No data exists, return full range
                return [(start_time, end_time)]
            
            # Find gaps
            missing_ranges = []
            current_time = start_time
            
            # Sort timestamps
            existing_timestamps.sort()
            
            for timestamp in existing_timestamps:
                # Check if there's a gap
                if (timestamp - current_time) > timedelta(hours=1):
                    missing_ranges.append((current_time, timestamp))
                current_time = timestamp + timedelta(hours=1)
            
            # Check if there's a gap at the end
            if (end_time - current_time) > timedelta(hours=1):
                missing_ranges.append((current_time, end_time))
            
            return missing_ranges
    
    def _collect_for_crypto(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        direction: str = "backward"
    ) -> CollectionResult:
        """
        Collect data for a single cryptocurrency with smart resume.
        
        Args:
            symbol: Cryptocurrency symbol.
            start_time: Start of time range.
            end_time: End of time range.
            direction: Collection direction ('backward' or 'forward').
        
        Returns:
            CollectionResult instance.
        """
        collection_start = datetime.now()
        
        try:
            # Step 1: Check what data already exists
            with session_scope() as session:
                crypto_repo = CryptoRepository(session)
                crypto = crypto_repo.get_or_create(symbol, symbol)
                crypto_id = crypto.id
            
            # Get missing ranges
            missing_ranges = self._get_missing_ranges(crypto_id, start_time, end_time)
            
            if not missing_ranges:
                logger.info(f"{symbol}: All data already exists, skipping")
                return CollectionResult(
                    crypto_symbol=symbol,
                    success=True,
                    records_collected=0,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    duration_seconds=(datetime.now() - collection_start).total_seconds(),
                    status="skipped"
                )
            
            logger.info(f"{symbol}: Found {len(missing_ranges)} missing range(s)")
            
            # Step 2: Collect missing ranges with retry
            total_records = 0
            failed_ranges = []
            
            for range_start, range_end in missing_ranges:
                retry_count = 0
                success = False
                
                while retry_count <= self.max_retries and not success:
                    try:
                        # Fetch price data from Binance
                        trading_pair = f"{symbol}USDT"
                        price_data_list = self.binance_client.get_hourly_prices(
                            symbol=trading_pair,
                            start_time=range_start,
                            end_time=range_end
                        )
                        
                        if price_data_list:
                            # Persist to database immediately
                            records_saved = self._persist_price_data(symbol, price_data_list)
                            total_records += records_saved
                            success = True
                            logger.debug(
                                f"{symbol}: Collected {records_saved} records "
                                f"for range {range_start} to {range_end}"
                            )
                        else:
                            logger.warning(f"{symbol}: No data for range {range_start} to {range_end}")
                            retry_count += 1
                            
                    except BinanceAPIError as e:
                        retry_count += 1
                        if retry_count <= self.max_retries:
                            wait_time = 2 ** retry_count  # Exponential backoff
                            logger.warning(
                                f"{symbol}: API error (attempt {retry_count}/{self.max_retries}), "
                                f"retrying in {wait_time}s: {e}"
                            )
                            import time
                            time.sleep(wait_time)
                        else:
                            logger.error(f"{symbol}: Failed after {self.max_retries} retries: {e}")
                            failed_ranges.append((range_start, range_end))
                    
                    except Exception as e:
                        logger.error(f"{symbol}: Unexpected error: {e}")
                        failed_ranges.append((range_start, range_end))
                        break
            
            # Step 3: Determine result status
            duration = (datetime.now() - collection_start).total_seconds()
            
            if not failed_ranges:
                # Complete success
                return CollectionResult(
                    crypto_symbol=symbol,
                    success=True,
                    records_collected=total_records,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    duration_seconds=duration,
                    status="complete"
                )
            elif total_records > 0:
                # Partial success
                return CollectionResult(
                    crypto_symbol=symbol,
                    success=True,
                    records_collected=total_records,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    duration_seconds=duration,
                    status="partial",
                    missing_ranges=failed_ranges,
                    error_message=f"{len(failed_ranges)} range(s) failed"
                )
            else:
                # Complete failure
                return CollectionResult(
                    crypto_symbol=symbol,
                    success=False,
                    records_collected=0,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    duration_seconds=duration,
                    status="failed",
                    missing_ranges=failed_ranges,
                    error_message="All ranges failed"
                )
            
        except Exception as e:
            logger.error(f"Unexpected error collecting {symbol}: {e}")
            return CollectionResult(
                crypto_symbol=symbol,
                success=False,
                records_collected=0,
                time_range_start=start_time,
                time_range_end=end_time,
                duration_seconds=(datetime.now() - collection_start).total_seconds(),
                status="failed",
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _persist_price_data(
        self,
        symbol: str,
        price_data_list: List[PriceData]
    ) -> int:
        """
        Persist price data to database.
        
        Args:
            symbol: Cryptocurrency symbol.
            price_data_list: List of PriceData instances.
        
        Returns:
            Number of records saved.
        """
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            price_repo = PriceHistoryRepository(session)
            
            # Get or create cryptocurrency record
            crypto = crypto_repo.get_or_create(symbol, symbol)
            
            # Prepare price records for bulk insert
            price_records = []
            for price_data in price_data_list:
                price_records.append({
                    'crypto_id': crypto.id,
                    'timestamp': price_data.timestamp,
                    'price_usd': price_data.price_usd,
                    'volume_24h': price_data.volume_24h,
                    'market_cap': price_data.market_cap
                })
            
            # Bulk insert
            records_saved = price_repo.bulk_create(price_records)
            
            logger.debug(
                f"Persisted {records_saved}/{len(price_records)} records for {symbol}"
            )
            
            return records_saved
    
    def detect_and_fill_gaps(
        self,
        crypto_symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None
    ) -> List[CollectionResult]:
        """
        Detect gaps in existing data and fill them.
        
        Args:
            crypto_symbols: Specific symbols to check (default: top N).
            start_date: Earliest date to check for gaps.
        
        Returns:
            List of CollectionResult instances for gap filling.
        """
        if crypto_symbols is None:
            crypto_symbols = self.get_tracked_cryptocurrencies()
        
        if not crypto_symbols:
            logger.error("No cryptocurrencies to check for gaps")
            return []
        
        logger.info(f"Detecting gaps for {len(crypto_symbols)} cryptocurrencies")
        
        results = []
        
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            gap_detector = DataGapDetector(session)
            
            for symbol in crypto_symbols:
                try:
                    crypto = crypto_repo.get_by_symbol(symbol)
                    if crypto is None:
                        logger.debug(f"{symbol}: No data exists, skipping gap detection")
                        continue
                    
                    # Find all gaps
                    gaps = gap_detector.find_all_gaps(
                        crypto.id,
                        symbol,
                        start_date if start_date else datetime(2020, 1, 1),
                        datetime.now()
                    )
                    
                    if not gaps:
                        logger.debug(f"{symbol}: No gaps found")
                        continue
                    
                    logger.info(f"{symbol}: Found {len(gaps)} gap(s)")
                    
                    # Fill each gap
                    for gap in gaps:
                        result = self._collect_for_crypto(
                            symbol=symbol,
                            start_time=gap.start_time,
                            end_time=gap.end_time,
                            direction="gap_fill"
                        )
                        results.append(result)
                        
                except Exception as e:
                    logger.error(f"Error detecting gaps for {symbol}: {e}")
        
        self.collection_results.extend(results)
        self._log_collection_summary(results, "gap_fill")
        
        return results
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get current collection status with detailed progress.
        
        Returns:
            Dictionary with status information.
        """
        status = {
            "is_collecting": self.current_progress is not None,
            "total_collections": len(self.collection_results),
            "successful_collections": sum(1 for r in self.collection_results if r.success),
            "failed_collections": sum(1 for r in self.collection_results if not r.success),
            "partial_collections": sum(1 for r in self.collection_results if r.status == "partial"),
            "skipped_collections": sum(1 for r in self.collection_results if r.status == "skipped"),
            "total_records_collected": sum(r.records_collected for r in self.collection_results)
        }
        
        if self.current_progress:
            status["current_progress"] = {
                "crypto_symbol": self.current_progress.crypto_symbol,
                "progress_percent": self.current_progress.progress_percent,
                "collected_hours": self.current_progress.collected_hours,
                "total_hours": self.current_progress.total_hours
            }
        
        # Add detailed results
        if self.collection_results:
            status["recent_results"] = [
                {
                    "symbol": r.crypto_symbol,
                    "status": r.status,
                    "records": r.records_collected,
                    "duration": round(r.duration_seconds, 2),
                    "error": r.error_message
                }
                for r in self.collection_results[-10:]  # Last 10 results
            ]
        
        return status
    
    def _log_collection_summary(
        self,
        results: List[CollectionResult],
        collection_type: str
    ) -> None:
        """
        Log summary of collection results.
        
        Args:
            results: List of collection results.
            collection_type: Type of collection (backward, forward, gap_fill).
        """
        if not results:
            return
        
        complete = sum(1 for r in results if r.status == "complete")
        partial = sum(1 for r in results if r.status == "partial")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        total_records = sum(r.records_collected for r in results)
        total_duration = sum(r.duration_seconds for r in results)
        
        logger.info(
            f"\n{'='*60}\n"
            f"Collection Summary ({collection_type})\n"
            f"{'='*60}\n"
            f"Total cryptocurrencies: {len(results)}\n"
            f"Complete: {complete}\n"
            f"Partial: {partial}\n"
            f"Failed: {failed}\n"
            f"Skipped (already collected): {skipped}\n"
            f"Total records collected: {total_records}\n"
            f"Total duration: {total_duration:.1f}s\n"
            f"Average per crypto: {total_duration/len(results):.1f}s\n"
            f"{'='*60}"
        )
        
        # Log failed/partial cryptos for retry
        if partial > 0 or failed > 0:
            logger.warning("\nCryptos needing attention:")
            for r in results:
                if r.status in ["partial", "failed"]:
                    logger.warning(
                        f"  - {r.crypto_symbol}: {r.status} "
                        f"({r.records_collected} records, {r.error_message})"
                    )

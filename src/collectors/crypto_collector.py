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
        batch_size_hours: int = 720  # 30 days
    ):
        """
        Initialize crypto collector.
        
        Args:
            binance_client: Binance API client instance.
            top_n_cryptos: Number of top cryptocurrencies to track.
            batch_size_hours: Hours of data to fetch per batch.
        """
        self.binance_client = binance_client
        self.top_n_cryptos = top_n_cryptos
        self.batch_size_hours = batch_size_hours
        
        # Progress tracking
        self.current_progress: Optional[CollectionProgress] = None
        self.collection_results: List[CollectionResult] = []
        
        logger.info(
            f"CryptoCollector initialized: "
            f"top_n={top_n_cryptos}, batch_size={batch_size_hours}h"
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
    
    def _collect_for_crypto(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        direction: str = "backward"
    ) -> CollectionResult:
        """
        Collect data for a single cryptocurrency.
        
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
            # Fetch price data from Binance
            trading_pair = f"{symbol}USDT"
            price_data_list = self.binance_client.get_hourly_prices(
                symbol=trading_pair,
                start_time=start_time,
                end_time=end_time
            )
            
            if not price_data_list:
                return CollectionResult(
                    crypto_symbol=symbol,
                    success=False,
                    records_collected=0,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    duration_seconds=(datetime.now() - collection_start).total_seconds(),
                    error_message="No data returned from Binance API"
                )
            
            # Persist to database
            records_saved = self._persist_price_data(symbol, price_data_list)
            
            duration = (datetime.now() - collection_start).total_seconds()
            
            return CollectionResult(
                crypto_symbol=symbol,
                success=True,
                records_collected=records_saved,
                time_range_start=start_time,
                time_range_end=end_time,
                duration_seconds=duration
            )
            
        except BinanceAPIError as e:
            logger.error(f"Binance API error for {symbol}: {e}")
            return CollectionResult(
                crypto_symbol=symbol,
                success=False,
                records_collected=0,
                time_range_start=start_time,
                time_range_end=end_time,
                duration_seconds=(datetime.now() - collection_start).total_seconds(),
                error_message=f"Binance API error: {str(e)}"
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
        Get current collection status.
        
        Returns:
            Dictionary with status information.
        """
        status = {
            "is_collecting": self.current_progress is not None,
            "total_collections": len(self.collection_results),
            "successful_collections": sum(1 for r in self.collection_results if r.success),
            "failed_collections": sum(1 for r in self.collection_results if not r.success),
            "total_records_collected": sum(r.records_collected for r in self.collection_results)
        }
        
        if self.current_progress:
            status["current_progress"] = {
                "crypto_symbol": self.current_progress.crypto_symbol,
                "progress_percent": self.current_progress.progress_percent,
                "collected_hours": self.current_progress.collected_hours,
                "total_hours": self.current_progress.total_hours
            }
        
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
        
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_records = sum(r.records_collected for r in results)
        total_duration = sum(r.duration_seconds for r in results)
        
        logger.info(
            f"\n{'='*60}\n"
            f"Collection Summary ({collection_type})\n"
            f"{'='*60}\n"
            f"Total cryptocurrencies: {len(results)}\n"
            f"Successful: {successful}\n"
            f"Failed: {failed}\n"
            f"Total records collected: {total_records}\n"
            f"Total duration: {total_duration:.1f}s\n"
            f"{'='*60}"
        )

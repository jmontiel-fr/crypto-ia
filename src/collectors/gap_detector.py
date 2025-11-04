"""
Data gap detection logic for identifying missing time ranges in database.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any

from sqlalchemy.orm import Session

from src.data.repositories import PriceHistoryRepository

logger = logging.getLogger(__name__)


@dataclass
class DataGap:
    """Represents a gap in historical data."""
    crypto_id: int
    crypto_symbol: str
    start_time: datetime
    end_time: datetime
    hours_missing: int


class DataGapDetector:
    """
    Detects missing time ranges in cryptocurrency price history.
    
    Identifies gaps between:
    - Start date and yesterday (backward collection)
    - Last recorded date and current date (forward collection)
    """
    
    def __init__(self, session: Session):
        """
        Initialize gap detector.
        
        Args:
            session: SQLAlchemy database session.
        """
        self.session = session
        self.price_repo = PriceHistoryRepository(session)
    
    def find_gaps_backward(
        self,
        crypto_id: int,
        crypto_symbol: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[DataGap]:
        """
        Find gaps between start_date and yesterday (or end_date).
        
        This method identifies missing data when collecting historical data
        backward from a recent date to an older start date.
        
        Args:
            crypto_id: Cryptocurrency database ID.
            crypto_symbol: Cryptocurrency symbol for logging.
            start_date: Earliest date to check for data.
            end_date: Latest date to check (default: yesterday).
        
        Returns:
            List of DataGap instances representing missing time ranges.
        """
        if end_date is None:
            # Default to yesterday (don't include today as it's incomplete)
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get earliest timestamp in database
        earliest_timestamp = self.price_repo.get_earliest_timestamp(crypto_id)
        
        gaps = []
        
        if earliest_timestamp is None:
            # No data exists, entire range is a gap
            hours_missing = int((end_date - start_date).total_seconds() / 3600)
            gap = DataGap(
                crypto_id=crypto_id,
                crypto_symbol=crypto_symbol,
                start_time=start_date,
                end_time=end_date,
                hours_missing=hours_missing
            )
            gaps.append(gap)
            logger.info(
                f"No data found for {crypto_symbol}, "
                f"gap from {start_date} to {end_date} ({hours_missing} hours)"
            )
        elif earliest_timestamp > start_date:
            # Gap exists between start_date and earliest data
            hours_missing = int((earliest_timestamp - start_date).total_seconds() / 3600)
            gap = DataGap(
                crypto_id=crypto_id,
                crypto_symbol=crypto_symbol,
                start_time=start_date,
                end_time=earliest_timestamp,
                hours_missing=hours_missing
            )
            gaps.append(gap)
            logger.info(
                f"Gap found for {crypto_symbol} "
                f"from {start_date} to {earliest_timestamp} ({hours_missing} hours)"
            )
        else:
            logger.debug(
                f"No backward gap for {crypto_symbol}, "
                f"data exists from {earliest_timestamp}"
            )
        
        return gaps
    
    def find_gaps_forward(
        self,
        crypto_id: int,
        crypto_symbol: str,
        end_date: Optional[datetime] = None
    ) -> List[DataGap]:
        """
        Find gaps between last recorded date and current date (or end_date).
        
        This method identifies missing data when updating with recent data
        forward from the last recorded timestamp.
        
        Args:
            crypto_id: Cryptocurrency database ID.
            crypto_symbol: Cryptocurrency symbol for logging.
            end_date: Latest date to check (default: now).
        
        Returns:
            List of DataGap instances representing missing time ranges.
        """
        if end_date is None:
            # Default to current time
            end_date = datetime.now()
        
        # Get latest timestamp in database
        latest_timestamp = self.price_repo.get_latest_timestamp(crypto_id)
        
        gaps = []
        
        if latest_timestamp is None:
            # No data exists at all
            logger.warning(
                f"No data found for {crypto_symbol}, "
                f"cannot determine forward gap without baseline"
            )
            return gaps
        
        # Check if there's a gap between latest data and end_date
        # Allow 1 hour tolerance to avoid flagging very recent data as gaps
        time_diff = end_date - latest_timestamp
        if time_diff > timedelta(hours=1):
            hours_missing = int(time_diff.total_seconds() / 3600)
            gap = DataGap(
                crypto_id=crypto_id,
                crypto_symbol=crypto_symbol,
                start_time=latest_timestamp,
                end_time=end_date,
                hours_missing=hours_missing
            )
            gaps.append(gap)
            logger.info(
                f"Forward gap found for {crypto_symbol} "
                f"from {latest_timestamp} to {end_date} ({hours_missing} hours)"
            )
        else:
            logger.debug(
                f"No forward gap for {crypto_symbol}, "
                f"data is up to date (latest: {latest_timestamp})"
            )
        
        return gaps
    
    def find_all_gaps(
        self,
        crypto_id: int,
        crypto_symbol: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[DataGap]:
        """
        Find all gaps in data for a cryptocurrency.
        
        This method combines backward and forward gap detection to identify
        all missing time ranges.
        
        Args:
            crypto_id: Cryptocurrency database ID.
            crypto_symbol: Cryptocurrency symbol for logging.
            start_date: Earliest date to check for data.
            end_date: Latest date to check (default: now).
        
        Returns:
            List of DataGap instances representing all missing time ranges.
        """
        if end_date is None:
            end_date = datetime.now()
        
        all_gaps = []
        
        # Check for backward gaps
        backward_gaps = self.find_gaps_backward(
            crypto_id,
            crypto_symbol,
            start_date,
            end_date
        )
        all_gaps.extend(backward_gaps)
        
        # Check for forward gaps (only if we have some data)
        latest_timestamp = self.price_repo.get_latest_timestamp(crypto_id)
        if latest_timestamp is not None:
            forward_gaps = self.find_gaps_forward(
                crypto_id,
                crypto_symbol,
                end_date
            )
            all_gaps.extend(forward_gaps)
        
        return all_gaps
    
    def detect_internal_gaps(
        self,
        crypto_id: int,
        crypto_symbol: str,
        start_date: datetime,
        end_date: datetime,
        expected_interval_hours: int = 1
    ) -> List[DataGap]:
        """
        Detect gaps within existing data range.
        
        This method identifies missing hourly data points within a range
        where some data exists.
        
        Args:
            crypto_id: Cryptocurrency database ID.
            crypto_symbol: Cryptocurrency symbol for logging.
            start_date: Start of range to check.
            end_date: End of range to check.
            expected_interval_hours: Expected interval between data points.
        
        Returns:
            List of DataGap instances for internal gaps.
        """
        # Get all price records in range
        price_records = self.price_repo.get_by_crypto_and_time_range(
            crypto_id,
            start_date,
            end_date
        )
        
        if not price_records:
            logger.debug(f"No data found for {crypto_symbol} in specified range")
            return []
        
        gaps = []
        expected_interval = timedelta(hours=expected_interval_hours)
        
        # Check for gaps between consecutive records
        for i in range(len(price_records) - 1):
            current_time = price_records[i].timestamp
            next_time = price_records[i + 1].timestamp
            time_diff = next_time - current_time
            
            # If gap is larger than expected interval (with small tolerance)
            if time_diff > expected_interval + timedelta(minutes=5):
                hours_missing = int(time_diff.total_seconds() / 3600)
                gap = DataGap(
                    crypto_id=crypto_id,
                    crypto_symbol=crypto_symbol,
                    start_time=current_time,
                    end_time=next_time,
                    hours_missing=hours_missing
                )
                gaps.append(gap)
                logger.info(
                    f"Internal gap found for {crypto_symbol} "
                    f"from {current_time} to {next_time} ({hours_missing} hours)"
                )
        
        return gaps
    
    def get_collection_summary(
        self,
        crypto_id: int,
        crypto_symbol: str
    ) -> Dict[str, Any]:
        """
        Get summary of data collection status for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency database ID.
            crypto_symbol: Cryptocurrency symbol.
        
        Returns:
            Dictionary with collection status information.
        """
        earliest = self.price_repo.get_earliest_timestamp(crypto_id)
        latest = self.price_repo.get_latest_timestamp(crypto_id)
        count = self.price_repo.count_by_crypto(crypto_id)
        
        summary = {
            "crypto_id": crypto_id,
            "crypto_symbol": crypto_symbol,
            "earliest_timestamp": earliest,
            "latest_timestamp": latest,
            "total_records": count,
            "has_data": count > 0
        }
        
        if earliest and latest:
            time_span = latest - earliest
            summary["time_span_hours"] = int(time_span.total_seconds() / 3600)
            summary["time_span_days"] = time_span.days
            
            # Calculate expected vs actual records (hourly data)
            expected_records = int(time_span.total_seconds() / 3600) + 1
            summary["expected_records"] = expected_records
            summary["completeness_percent"] = (count / expected_records * 100) if expected_records > 0 else 0
        
        return summary

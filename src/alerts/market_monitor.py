"""
Market shift detection module.
Analyzes hourly price changes to detect massive market shifts.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from src.data.models import Cryptocurrency, PriceHistory
from src.data.repositories import PriceHistoryRepository

logger = logging.getLogger(__name__)


@dataclass
class MarketShift:
    """Data class representing a detected market shift."""
    crypto_id: int
    crypto_symbol: str
    crypto_name: str
    shift_type: str  # 'increase' or 'decrease'
    change_percent: float
    previous_price: Decimal
    current_price: Decimal
    timestamp: datetime
    
    def __str__(self):
        direction = "↑" if self.shift_type == "increase" else "↓"
        return (f"{self.crypto_symbol} {direction} {abs(self.change_percent):.2f}%: "
                f"${self.previous_price:.2f} → ${self.current_price:.2f}")


class MarketMonitor:
    """
    Monitors cryptocurrency market for massive price shifts.
    Detects both increases and decreases beyond configured threshold.
    """
    
    def __init__(
        self,
        db_session: Session,
        threshold_percent: float = 10.0,
        cooldown_hours: int = 4
    ):
        """
        Initialize market monitor.
        
        Args:
            db_session: Database session for querying price data
            threshold_percent: Percentage change threshold for detection (default: 10.0)
            cooldown_hours: Hours to wait before alerting again for same crypto (default: 4)
        """
        self.db_session = db_session
        self.threshold_percent = threshold_percent
        self.cooldown_hours = cooldown_hours
        self.price_repo = PriceHistoryRepository(db_session)
        
        # Track last alert time for each crypto to implement cooldown
        self._last_alert_times: Dict[int, datetime] = {}
        
        logger.info(
            f"MarketMonitor initialized with threshold={threshold_percent}%, "
            f"cooldown={cooldown_hours}h"
        )
    
    def detect_massive_shift(
        self,
        crypto_ids: Optional[List[int]] = None
    ) -> List[MarketShift]:
        """
        Detect massive market shifts for tracked cryptocurrencies.
        
        Compares current price with price from 1 hour ago to identify
        significant changes beyond the threshold.
        
        Args:
            crypto_ids: Optional list of crypto IDs to check. If None, checks all.
        
        Returns:
            List of MarketShift objects for detected shifts.
        """
        logger.info("Starting market shift detection")
        
        try:
            # Get all tracked cryptocurrencies if not specified
            if crypto_ids is None:
                cryptos = self.db_session.query(Cryptocurrency).all()
                crypto_ids = [c.id for c in cryptos]
            
            shifts = []
            current_time = datetime.utcnow()
            
            for crypto_id in crypto_ids:
                # Check cooldown
                if not self._is_cooldown_expired(crypto_id, current_time):
                    logger.debug(f"Crypto {crypto_id} in cooldown period, skipping")
                    continue
                
                # Calculate percentage change
                shift = self._check_crypto_shift(crypto_id, current_time)
                
                if shift:
                    shifts.append(shift)
                    # Update last alert time
                    self._last_alert_times[crypto_id] = current_time
                    logger.info(f"Detected shift: {shift}")
            
            logger.info(f"Market shift detection complete. Found {len(shifts)} shifts.")
            return shifts
            
        except Exception as e:
            logger.error(f"Error during market shift detection: {e}", exc_info=True)
            return []
    
    def _check_crypto_shift(
        self,
        crypto_id: int,
        current_time: datetime
    ) -> Optional[MarketShift]:
        """
        Check if a specific cryptocurrency has experienced a massive shift.
        
        Args:
            crypto_id: Cryptocurrency ID to check
            current_time: Current timestamp
        
        Returns:
            MarketShift object if shift detected, None otherwise.
        """
        try:
            # Get cryptocurrency info
            crypto = self.db_session.query(Cryptocurrency).filter(
                Cryptocurrency.id == crypto_id
            ).first()
            
            if not crypto:
                logger.warning(f"Cryptocurrency with ID {crypto_id} not found")
                return None
            
            # Get current price (most recent)
            current_price_data = self.price_repo.get_latest_price(crypto_id)
            
            if not current_price_data:
                logger.debug(f"No current price data for {crypto.symbol}")
                return None
            
            # Get price from 1 hour ago
            one_hour_ago = current_time - timedelta(hours=1)
            previous_price_data = self.price_repo.get_price_at_time(
                crypto_id,
                one_hour_ago,
                tolerance_minutes=30  # Allow 30 min tolerance for finding data
            )
            
            if not previous_price_data:
                logger.debug(f"No previous price data for {crypto.symbol}")
                return None
            
            # Calculate percentage change
            current_price = float(current_price_data.price_usd)
            previous_price = float(previous_price_data.price_usd)
            
            if previous_price == 0:
                logger.warning(f"Previous price is zero for {crypto.symbol}")
                return None
            
            change_percent = ((current_price - previous_price) / previous_price) * 100
            
            # Check if change exceeds threshold
            if abs(change_percent) >= self.threshold_percent:
                shift_type = "increase" if change_percent > 0 else "decrease"
                
                return MarketShift(
                    crypto_id=crypto_id,
                    crypto_symbol=crypto.symbol,
                    crypto_name=crypto.name,
                    shift_type=shift_type,
                    change_percent=change_percent,
                    previous_price=previous_price_data.price_usd,
                    current_price=current_price_data.price_usd,
                    timestamp=current_time
                )
            
            return None
            
        except Exception as e:
            logger.error(
                f"Error checking shift for crypto {crypto_id}: {e}",
                exc_info=True
            )
            return None
    
    def _is_cooldown_expired(self, crypto_id: int, current_time: datetime) -> bool:
        """
        Check if cooldown period has expired for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID
            current_time: Current timestamp
        
        Returns:
            True if cooldown expired or no previous alert, False otherwise.
        """
        if crypto_id not in self._last_alert_times:
            return True
        
        last_alert = self._last_alert_times[crypto_id]
        time_since_alert = current_time - last_alert
        cooldown_delta = timedelta(hours=self.cooldown_hours)
        
        return time_since_alert >= cooldown_delta
    
    def analyze_hourly_changes(self) -> Dict[str, float]:
        """
        Analyze hourly price changes for all tracked cryptocurrencies.
        
        Returns:
            Dictionary mapping crypto symbols to their percentage changes.
        """
        logger.info("Analyzing hourly changes for all cryptocurrencies")
        
        try:
            cryptos = self.db_session.query(Cryptocurrency).all()
            changes = {}
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            for crypto in cryptos:
                try:
                    current_price_data = self.price_repo.get_latest_price(crypto.id)
                    previous_price_data = self.price_repo.get_price_at_time(
                        crypto.id,
                        one_hour_ago,
                        tolerance_minutes=30
                    )
                    
                    if current_price_data and previous_price_data:
                        current_price = float(current_price_data.price_usd)
                        previous_price = float(previous_price_data.price_usd)
                        
                        if previous_price > 0:
                            change_percent = (
                                (current_price - previous_price) / previous_price
                            ) * 100
                            changes[crypto.symbol] = change_percent
                
                except Exception as e:
                    logger.error(
                        f"Error analyzing change for {crypto.symbol}: {e}"
                    )
                    continue
            
            logger.info(f"Analyzed changes for {len(changes)} cryptocurrencies")
            return changes
            
        except Exception as e:
            logger.error(f"Error analyzing hourly changes: {e}", exc_info=True)
            return {}
    
    def reset_cooldown(self, crypto_id: Optional[int] = None) -> None:
        """
        Reset cooldown for a specific crypto or all cryptos.
        
        Args:
            crypto_id: Cryptocurrency ID to reset. If None, resets all.
        """
        if crypto_id is None:
            self._last_alert_times.clear()
            logger.info("Reset cooldown for all cryptocurrencies")
        else:
            if crypto_id in self._last_alert_times:
                del self._last_alert_times[crypto_id]
                logger.info(f"Reset cooldown for crypto {crypto_id}")

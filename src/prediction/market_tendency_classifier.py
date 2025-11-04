"""
Market tendency classification for cryptocurrency markets.
Classifies overall market conditions as bullish, bearish, volatile, stable, or consolidating.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sqlalchemy.orm import Session

from src.data.models import Cryptocurrency, PriceHistory, MarketTendency
from src.data.repositories import (
    CryptoRepository,
    PriceHistoryRepository,
    MarketTendencyRepository
)

logger = logging.getLogger(__name__)


class TendencyType(Enum):
    """Market tendency types."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    VOLATILE = "volatile"
    STABLE = "stable"
    CONSOLIDATING = "consolidating"


@dataclass
class TendencyResult:
    """Data class for market tendency results."""
    tendency: str
    confidence: float
    metrics: Dict[str, float]
    timestamp: datetime


class MarketTendencyClassifier:
    """
    Classifies market tendency based on price movements and market metrics.
    
    Tendency Types:
    - Bullish: Overall upward momentum (>60% of cryptos increasing)
    - Bearish: Overall downward momentum (>60% of cryptos decreasing)
    - Volatile: High price fluctuations with no clear direction
    - Stable: Low volatility with minimal price changes
    - Consolidating: Sideways movement within tight range
    """
    
    def __init__(
        self,
        session: Session,
        lookback_hours: int = 24,
        top_n_cryptos: int = 50
    ):
        """
        Initialize market tendency classifier.
        
        Args:
            session: Database session
            lookback_hours: Hours to look back for analysis (default: 24)
            top_n_cryptos: Number of top cryptocurrencies to analyze
        """
        self.session = session
        self.lookback_hours = lookback_hours
        self.top_n_cryptos = top_n_cryptos
        
        # Initialize repositories
        self.crypto_repo = CryptoRepository(session)
        self.price_repo = PriceHistoryRepository(session)
        self.tendency_repo = MarketTendencyRepository(session)
        
        logger.info(
            f"Initialized MarketTendencyClassifier: "
            f"lookback={lookback_hours}h, "
            f"top_n={top_n_cryptos}"
        )
    
    def get_price_changes(self) -> List[Dict[str, Any]]:
        """
        Get price changes for top cryptocurrencies.
        
        Returns:
            List of dictionaries with crypto info and price changes
        """
        # Get top cryptocurrencies
        top_cryptos = self.crypto_repo.get_top_by_market_cap(self.top_n_cryptos)
        
        if not top_cryptos:
            logger.warning("No cryptocurrencies found")
            return []
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.lookback_hours)
        
        price_changes = []
        
        for crypto in top_cryptos:
            # Get price data for the period
            prices = self.price_repo.get_by_crypto_and_time_range(
                crypto.id,
                start_time,
                end_time
            )
            
            if len(prices) < 2:
                continue
            
            # Calculate metrics
            start_price = float(prices[0].price_usd)
            end_price = float(prices[-1].price_usd)
            
            # Price change percentage
            price_change_percent = ((end_price - start_price) / start_price) * 100
            
            # Volatility (standard deviation of returns)
            price_values = [float(p.price_usd) for p in prices]
            returns = np.diff(price_values) / price_values[:-1]
            volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
            
            # Market cap change
            start_market_cap = float(prices[0].market_cap) if prices[0].market_cap else 0.0
            end_market_cap = float(prices[-1].market_cap) if prices[-1].market_cap else 0.0
            
            market_cap_change_percent = 0.0
            if start_market_cap > 0:
                market_cap_change_percent = (
                    (end_market_cap - start_market_cap) / start_market_cap
                ) * 100
            
            price_changes.append({
                'crypto_id': crypto.id,
                'symbol': crypto.symbol,
                'price_change_percent': price_change_percent,
                'volatility': volatility,
                'market_cap_change_percent': market_cap_change_percent,
                'start_price': start_price,
                'end_price': end_price
            })
        
        logger.debug(f"Calculated price changes for {len(price_changes)} cryptocurrencies")
        return price_changes
    
    def calculate_market_metrics(
        self,
        price_changes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate aggregate market metrics.
        
        Args:
            price_changes: List of price change data
        
        Returns:
            Dictionary with market metrics
        """
        if not price_changes:
            return {
                'avg_change_percent': 0.0,
                'volatility_index': 0.0,
                'market_cap_change': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'positive_ratio': 0.0
            }
        
        # Average price change
        changes = [pc['price_change_percent'] for pc in price_changes]
        avg_change_percent = float(np.mean(changes))
        
        # Volatility index (average volatility)
        volatilities = [pc['volatility'] for pc in price_changes]
        volatility_index = float(np.mean(volatilities))
        
        # Market cap change
        market_cap_changes = [pc['market_cap_change_percent'] for pc in price_changes]
        market_cap_change = float(np.mean(market_cap_changes))
        
        # Count positive and negative movers
        positive_count = sum(1 for pc in price_changes if pc['price_change_percent'] > 0)
        negative_count = sum(1 for pc in price_changes if pc['price_change_percent'] < 0)
        total_count = len(price_changes)
        
        positive_ratio = positive_count / total_count if total_count > 0 else 0.0
        
        return {
            'avg_change_percent': avg_change_percent,
            'volatility_index': volatility_index,
            'market_cap_change': market_cap_change,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'positive_ratio': positive_ratio,
            'total_count': total_count
        }
    
    def classify_tendency(
        self,
        metrics: Dict[str, float]
    ) -> Tuple[TendencyType, float]:
        """
        Classify market tendency based on metrics.
        
        Args:
            metrics: Market metrics dictionary
        
        Returns:
            Tuple of (TendencyType, confidence_score)
        """
        avg_change = metrics['avg_change_percent']
        volatility = metrics['volatility_index']
        positive_ratio = metrics['positive_ratio']
        
        # Thresholds
        BULLISH_THRESHOLD = 0.60  # 60% of cryptos increasing
        BEARISH_THRESHOLD = 0.40  # 40% or less increasing (60% decreasing)
        HIGH_VOLATILITY_THRESHOLD = 0.05  # 5% volatility
        LOW_VOLATILITY_THRESHOLD = 0.01  # 1% volatility
        SIGNIFICANT_CHANGE_THRESHOLD = 2.0  # 2% average change
        
        confidence = 0.5  # Base confidence
        
        # Classification logic
        if volatility > HIGH_VOLATILITY_THRESHOLD:
            # High volatility
            tendency = TendencyType.VOLATILE
            confidence = min(0.9, 0.5 + (volatility / HIGH_VOLATILITY_THRESHOLD) * 0.2)
        
        elif positive_ratio > BULLISH_THRESHOLD and avg_change > SIGNIFICANT_CHANGE_THRESHOLD:
            # Bullish market
            tendency = TendencyType.BULLISH
            confidence = min(0.95, 0.6 + (positive_ratio - BULLISH_THRESHOLD) * 2)
        
        elif positive_ratio < BEARISH_THRESHOLD and avg_change < -SIGNIFICANT_CHANGE_THRESHOLD:
            # Bearish market
            tendency = TendencyType.BEARISH
            confidence = min(0.95, 0.6 + (BEARISH_THRESHOLD - positive_ratio) * 2)
        
        elif volatility < LOW_VOLATILITY_THRESHOLD and abs(avg_change) < SIGNIFICANT_CHANGE_THRESHOLD:
            # Stable market
            tendency = TendencyType.STABLE
            confidence = min(0.9, 0.6 + (LOW_VOLATILITY_THRESHOLD - volatility) * 10)
        
        else:
            # Consolidating (sideways movement)
            tendency = TendencyType.CONSOLIDATING
            confidence = 0.6
        
        logger.debug(
            f"Classified tendency: {tendency.value} "
            f"(confidence={confidence:.2f}, "
            f"avg_change={avg_change:.2f}%, "
            f"volatility={volatility:.4f}, "
            f"positive_ratio={positive_ratio:.2f})"
        )
        
        return tendency, confidence
    
    def analyze_market(self) -> TendencyResult:
        """
        Analyze market and classify tendency.
        
        Returns:
            TendencyResult with classification and metrics
        """
        logger.info("Analyzing market tendency")
        
        # Get price changes
        price_changes = self.get_price_changes()
        
        if not price_changes:
            logger.warning("No price data available for analysis")
            return TendencyResult(
                tendency=TendencyType.STABLE.value,
                confidence=0.0,
                metrics={},
                timestamp=datetime.now()
            )
        
        # Calculate metrics
        metrics = self.calculate_market_metrics(price_changes)
        
        # Classify tendency
        tendency_type, confidence = self.classify_tendency(metrics)
        
        result = TendencyResult(
            tendency=tendency_type.value,
            confidence=confidence,
            metrics=metrics,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"Market tendency: {result.tendency} "
            f"(confidence={result.confidence:.2f})"
        )
        
        return result
    
    def store_tendency(self, result: TendencyResult) -> MarketTendency:
        """
        Store market tendency result to database.
        
        Args:
            result: TendencyResult to store
        
        Returns:
            Created MarketTendency instance
        """
        tendency = self.tendency_repo.create(
            tendency=result.tendency,
            timestamp=result.timestamp,
            confidence=Decimal(str(result.confidence)),
            metrics=result.metrics
        )
        
        self.session.commit()
        
        logger.info(f"Stored market tendency: {result.tendency}")
        return tendency
    
    def get_latest_tendency(self) -> Optional[TendencyResult]:
        """
        Get the latest market tendency from database.
        
        Returns:
            TendencyResult or None if no data available
        """
        tendency = self.tendency_repo.get_latest()
        
        if not tendency:
            return None
        
        return TendencyResult(
            tendency=tendency.tendency,
            confidence=float(tendency.confidence) if tendency.confidence else 0.0,
            metrics=tendency.metrics or {},
            timestamp=tendency.timestamp
        )
    
    def get_tendency_history(
        self,
        hours: int = 168
    ) -> List[TendencyResult]:
        """
        Get historical market tendencies.
        
        Args:
            hours: Number of hours to look back (default: 168 = 1 week)
        
        Returns:
            List of TendencyResult objects
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        tendencies = self.tendency_repo.get_by_time_range(start_time, end_time)
        
        results = []
        for t in tendencies:
            results.append(TendencyResult(
                tendency=t.tendency,
                confidence=float(t.confidence) if t.confidence else 0.0,
                metrics=t.metrics or {},
                timestamp=t.timestamp
            ))
        
        logger.debug(f"Retrieved {len(results)} historical tendencies")
        return results
    
    def analyze_and_store(self) -> TendencyResult:
        """
        Analyze market and store result to database.
        
        Returns:
            TendencyResult with classification and metrics
        """
        # Analyze market
        result = self.analyze_market()
        
        # Store to database
        if result.confidence > 0.0:
            self.store_tendency(result)
        
        return result
    
    def get_cached_or_analyze(
        self,
        max_age_hours: int = 1
    ) -> TendencyResult:
        """
        Get cached tendency or analyze if stale.
        
        Args:
            max_age_hours: Maximum age of cached data in hours
        
        Returns:
            TendencyResult (cached or fresh)
        """
        # Try to get cached result
        cached = self.get_latest_tendency()
        
        if cached:
            age = datetime.now() - cached.timestamp
            if age.total_seconds() / 3600 < max_age_hours:
                logger.info(f"Using cached tendency ({age.total_seconds() / 60:.1f}m old)")
                return cached
        
        # Analyze fresh data
        logger.info("Cached tendency stale or missing, analyzing fresh data")
        return self.analyze_and_store()

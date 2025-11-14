"""
Repository pattern implementation for data access.
Provides clean interfaces for CRUD operations on all entities.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import desc, asc, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.data.models import (
    Cryptocurrency,
    PriceHistory,
    Prediction,
    ChatHistory,
    QueryAuditLog,
    MarketTendency,
    AlertLog,
)

logger = logging.getLogger(__name__)


class CryptoRepository:
    """Repository for Cryptocurrency CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(self, symbol: str, name: str, market_cap_rank: Optional[int] = None) -> Cryptocurrency:
        """
        Create a new cryptocurrency record.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC').
            name: Full name (e.g., 'Bitcoin').
            market_cap_rank: Market capitalization rank.
        
        Returns:
            Created Cryptocurrency instance.
        
        Raises:
            IntegrityError: If cryptocurrency with symbol already exists.
        """
        crypto = Cryptocurrency(
            symbol=symbol.upper(),
            name=name,
            market_cap_rank=market_cap_rank
        )
        self.session.add(crypto)
        self.session.flush()
        logger.debug(f"Created cryptocurrency: {symbol}")
        return crypto
    
    def get_by_id(self, crypto_id: int) -> Optional[Cryptocurrency]:
        """Get cryptocurrency by ID."""
        return self.session.query(Cryptocurrency).filter_by(id=crypto_id).first()
    
    def get_by_symbol(self, symbol: str) -> Optional[Cryptocurrency]:
        """Get cryptocurrency by symbol."""
        return self.session.query(Cryptocurrency).filter_by(symbol=symbol.upper()).first()
    
    def get_or_create(self, symbol: str, name: str, market_cap_rank: Optional[int] = None) -> Cryptocurrency:
        """
        Get existing cryptocurrency or create new one.
        
        Args:
            symbol: Cryptocurrency symbol.
            name: Full name.
            market_cap_rank: Market capitalization rank.
        
        Returns:
            Cryptocurrency instance.
        """
        crypto = self.get_by_symbol(symbol)
        if crypto is None:
            crypto = self.create(symbol, name, market_cap_rank)
        else:
            # Update market cap rank if provided
            if market_cap_rank is not None and crypto.market_cap_rank != market_cap_rank:
                crypto.market_cap_rank = market_cap_rank
                self.session.flush()
        return crypto
    
    def get_all(self, limit: Optional[int] = None) -> List[Cryptocurrency]:
        """
        Get all cryptocurrencies.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of Cryptocurrency instances.
        """
        query = self.session.query(Cryptocurrency).order_by(asc(Cryptocurrency.market_cap_rank))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_top_by_market_cap(self, limit: int) -> List[Cryptocurrency]:
        """
        Get top cryptocurrencies by market cap rank.
        
        Args:
            limit: Number of top cryptocurrencies to retrieve.
        
        Returns:
            List of Cryptocurrency instances.
        """
        return self.session.query(Cryptocurrency)\
            .filter(Cryptocurrency.market_cap_rank.isnot(None))\
            .order_by(asc(Cryptocurrency.market_cap_rank))\
            .limit(limit)\
            .all()
    
    def update(self, crypto_id: int, **kwargs) -> Optional[Cryptocurrency]:
        """
        Update cryptocurrency fields.
        
        Args:
            crypto_id: Cryptocurrency ID.
            **kwargs: Fields to update.
        
        Returns:
            Updated Cryptocurrency instance or None if not found.
        """
        crypto = self.get_by_id(crypto_id)
        if crypto:
            for key, value in kwargs.items():
                if hasattr(crypto, key):
                    setattr(crypto, key, value)
            self.session.flush()
            logger.debug(f"Updated cryptocurrency: {crypto_id}")
        return crypto
    
    def delete(self, crypto_id: int) -> bool:
        """
        Delete cryptocurrency by ID.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            True if deleted, False if not found.
        """
        crypto = self.get_by_id(crypto_id)
        if crypto:
            self.session.delete(crypto)
            self.session.flush()
            logger.debug(f"Deleted cryptocurrency: {crypto_id}")
            return True
        return False


class PriceHistoryRepository:
    """Repository for PriceHistory CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        crypto_id: int,
        timestamp: datetime,
        price_usd: Decimal,
        volume_24h: Optional[Decimal] = None,
        market_cap: Optional[Decimal] = None
    ) -> PriceHistory:
        """
        Create a new price history record.
        
        Args:
            crypto_id: Cryptocurrency ID.
            timestamp: Price timestamp.
            price_usd: Price in USD.
            volume_24h: 24-hour trading volume.
            market_cap: Market capitalization.
        
        Returns:
            Created PriceHistory instance.
        
        Raises:
            IntegrityError: If record with same crypto_id and timestamp exists.
        """
        price = PriceHistory(
            crypto_id=crypto_id,
            timestamp=timestamp,
            price_usd=price_usd,
            volume_24h=volume_24h,
            market_cap=market_cap
        )
        self.session.add(price)
        self.session.flush()
        return price
    
    def bulk_create(self, price_records: List[Dict[str, Any]]) -> int:
        """
        Bulk create price history records.
        
        Args:
            price_records: List of dictionaries with price data.
        
        Returns:
            Number of records created.
        """
        try:
            objects = [PriceHistory(**record) for record in price_records]
            self.session.bulk_save_objects(objects)
            self.session.flush()
            logger.debug(f"Bulk created {len(objects)} price history records")
            return len(objects)
        except IntegrityError as e:
            logger.warning(f"Duplicate records in bulk create: {e}")
            # Rollback and try individual inserts
            self.session.rollback()
            count = 0
            for record in price_records:
                try:
                    self.create(**record)
                    count += 1
                except IntegrityError:
                    continue
            return count
    
    def get_by_crypto_and_time_range(
        self,
        crypto_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[PriceHistory]:
        """
        Get price history for a cryptocurrency within time range.
        
        Args:
            crypto_id: Cryptocurrency ID.
            start_time: Start of time range.
            end_time: End of time range.
        
        Returns:
            List of PriceHistory instances ordered by timestamp.
        """
        return self.session.query(PriceHistory)\
            .filter(
                and_(
                    PriceHistory.crypto_id == crypto_id,
                    PriceHistory.timestamp >= start_time,
                    PriceHistory.timestamp <= end_time
                )
            )\
            .order_by(asc(PriceHistory.timestamp))\
            .all()
    
    def get_latest_by_crypto(self, crypto_id: int, limit: int = 1) -> List[PriceHistory]:
        """
        Get latest price records for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
            limit: Number of records to retrieve.
        
        Returns:
            List of PriceHistory instances ordered by timestamp descending.
        """
        return self.session.query(PriceHistory)\
            .filter(PriceHistory.crypto_id == crypto_id)\
            .order_by(desc(PriceHistory.timestamp))\
            .limit(limit)\
            .all()
    
    def get_latest_timestamp(self, crypto_id: int) -> Optional[datetime]:
        """
        Get the latest timestamp for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Latest timestamp or None if no records exist.
        """
        result = self.session.query(PriceHistory.timestamp)\
            .filter(PriceHistory.crypto_id == crypto_id)\
            .order_by(desc(PriceHistory.timestamp))\
            .first()
        return result[0] if result else None
    
    def get_timestamps_in_range(
        self,
        crypto_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[datetime]:
        """
        Get all timestamps for a cryptocurrency within time range.
        
        Args:
            crypto_id: Cryptocurrency ID.
            start_time: Start of time range.
            end_time: End of time range.
        
        Returns:
            List of timestamps ordered chronologically.
        """
        results = self.session.query(PriceHistory.timestamp)\
            .filter(
                and_(
                    PriceHistory.crypto_id == crypto_id,
                    PriceHistory.timestamp >= start_time,
                    PriceHistory.timestamp <= end_time
                )
            )\
            .order_by(asc(PriceHistory.timestamp))\
            .all()
        return [r[0] for r in results]
    
    def get_earliest_timestamp(self, crypto_id: int) -> Optional[datetime]:
        """
        Get the earliest timestamp for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Earliest timestamp or None if no records exist.
        """
        result = self.session.query(PriceHistory.timestamp)\
            .filter(PriceHistory.crypto_id == crypto_id)\
            .order_by(asc(PriceHistory.timestamp))\
            .first()
        return result[0] if result else None
    
    def count_by_crypto(self, crypto_id: int) -> int:
        """
        Count price history records for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Number of records.
        """
        return self.session.query(PriceHistory)\
            .filter(PriceHistory.crypto_id == crypto_id)\
            .count()
    
    def get_latest_price(self, crypto_id: int) -> Optional[PriceHistory]:
        """
        Get the most recent price record for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Latest PriceHistory instance or None if no records exist.
        """
        return self.session.query(PriceHistory)\
            .filter(PriceHistory.crypto_id == crypto_id)\
            .order_by(desc(PriceHistory.timestamp))\
            .first()
    
    def get_price_at_time(
        self,
        crypto_id: int,
        target_time: datetime,
        tolerance_minutes: int = 30
    ) -> Optional[PriceHistory]:
        """
        Get price record closest to a target time within tolerance.
        
        Args:
            crypto_id: Cryptocurrency ID.
            target_time: Target timestamp.
            tolerance_minutes: Time tolerance in minutes (default: 30).
        
        Returns:
            PriceHistory instance closest to target time or None.
        """
        from datetime import timedelta
        
        # Define time window
        start_time = target_time - timedelta(minutes=tolerance_minutes)
        end_time = target_time + timedelta(minutes=tolerance_minutes)
        
        # Find closest record within window
        return self.session.query(PriceHistory)\
            .filter(
                and_(
                    PriceHistory.crypto_id == crypto_id,
                    PriceHistory.timestamp >= start_time,
                    PriceHistory.timestamp <= end_time
                )
            )\
            .order_by(
                # Order by absolute difference from target time
                func.abs(
                    func.extract('epoch', PriceHistory.timestamp) -
                    func.extract('epoch', target_time)
                )
            )\
            .first()


class PredictionRepository:
    """Repository for Prediction CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        crypto_id: int,
        prediction_date: datetime,
        predicted_price: Optional[Decimal] = None,
        confidence_score: Optional[Decimal] = None,
        prediction_horizon_hours: int = 24
    ) -> Prediction:
        """
        Create a new prediction record.
        
        Args:
            crypto_id: Cryptocurrency ID.
            prediction_date: Date of prediction.
            predicted_price: Predicted price.
            confidence_score: Confidence score (0-1).
            prediction_horizon_hours: Prediction horizon in hours.
        
        Returns:
            Created Prediction instance.
        """
        prediction = Prediction(
            crypto_id=crypto_id,
            prediction_date=prediction_date,
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            prediction_horizon_hours=prediction_horizon_hours
        )
        self.session.add(prediction)
        self.session.flush()
        return prediction
    
    def bulk_create(self, predictions: List[Dict[str, Any]]) -> int:
        """
        Bulk create prediction records.
        
        Args:
            predictions: List of dictionaries with prediction data.
        
        Returns:
            Number of records created.
        """
        objects = [Prediction(**pred) for pred in predictions]
        self.session.bulk_save_objects(objects)
        self.session.flush()
        logger.debug(f"Bulk created {len(objects)} prediction records")
        return len(objects)
    
    def get_latest_predictions(self, limit: Optional[int] = None) -> List[Prediction]:
        """
        Get latest predictions across all cryptocurrencies.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of Prediction instances ordered by prediction date descending.
        """
        query = self.session.query(Prediction)\
            .order_by(desc(Prediction.prediction_date))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_by_crypto(self, crypto_id: int, limit: Optional[int] = None) -> List[Prediction]:
        """
        Get predictions for a specific cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
            limit: Maximum number of results.
        
        Returns:
            List of Prediction instances ordered by prediction date descending.
        """
        query = self.session.query(Prediction)\
            .filter(Prediction.crypto_id == crypto_id)\
            .order_by(desc(Prediction.prediction_date))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_top_performers(self, limit: int = 20) -> List[Prediction]:
        """
        Get top predicted performers based on latest predictions.
        
        Args:
            limit: Number of top performers to retrieve.
        
        Returns:
            List of Prediction instances ordered by confidence score descending.
        """
        # Get the latest prediction date
        latest_date = self.session.query(Prediction.prediction_date)\
            .order_by(desc(Prediction.prediction_date))\
            .first()
        
        if not latest_date:
            return []
        
        # Get predictions from the latest date, ordered by confidence
        return self.session.query(Prediction)\
            .filter(Prediction.prediction_date == latest_date[0])\
            .filter(Prediction.confidence_score.isnot(None))\
            .order_by(desc(Prediction.confidence_score))\
            .limit(limit)\
            .all()


class ChatHistoryRepository:
    """Repository for ChatHistory CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        session_id: str,
        question: str,
        answer: str,
        question_hash: Optional[str] = None,
        topic_valid: bool = True,
        pii_detected: bool = False,
        context_used: Optional[Dict[str, Any]] = None,
        openai_tokens_input: Optional[int] = None,
        openai_tokens_output: Optional[int] = None,
        openai_cost_usd: Optional[Decimal] = None,
        response_time_ms: Optional[int] = None
    ) -> ChatHistory:
        """
        Create a new chat history record.
        
        Args:
            session_id: User session ID.
            question: User question.
            answer: AI response.
            question_hash: SHA256 hash of question.
            topic_valid: Whether question topic is valid.
            pii_detected: Whether PII was detected.
            context_used: Context data used for response.
            openai_tokens_input: Input tokens used.
            openai_tokens_output: Output tokens used.
            openai_cost_usd: Cost in USD.
            response_time_ms: Response time in milliseconds.
        
        Returns:
            Created ChatHistory instance.
        """
        chat = ChatHistory(
            session_id=session_id,
            question=question,
            answer=answer,
            question_hash=question_hash,
            topic_valid=topic_valid,
            pii_detected=pii_detected,
            context_used=context_used,
            openai_tokens_input=openai_tokens_input,
            openai_tokens_output=openai_tokens_output,
            openai_cost_usd=openai_cost_usd,
            response_time_ms=response_time_ms
        )
        self.session.add(chat)
        self.session.flush()
        return chat
    
    def get_recent_by_session(self, session_id: str, limit: int = 3) -> List[ChatHistory]:
        """
        Get recent chat history for a session (last N Q&A pairs).
        
        Args:
            session_id: User session ID.
            limit: Number of recent messages to retrieve (default: 3).
        
        Returns:
            List of ChatHistory instances ordered by created_at descending.
        """
        return self.session.query(ChatHistory)\
            .filter(ChatHistory.session_id == session_id)\
            .order_by(desc(ChatHistory.created_at))\
            .limit(limit)\
            .all()
    
    def get_all_by_session(self, session_id: str) -> List[ChatHistory]:
        """
        Get all chat history for a session.
        
        Args:
            session_id: User session ID.
        
        Returns:
            List of ChatHistory instances ordered by created_at ascending.
        """
        return self.session.query(ChatHistory)\
            .filter(ChatHistory.session_id == session_id)\
            .order_by(asc(ChatHistory.created_at))\
            .all()
    
    def get_total_cost_by_session(self, session_id: str) -> Decimal:
        """
        Calculate total OpenAI cost for a session.
        
        Args:
            session_id: User session ID.
        
        Returns:
            Total cost in USD.
        """
        result = self.session.query(
            func.sum(ChatHistory.openai_cost_usd)
        ).filter(ChatHistory.session_id == session_id).scalar()
        return result or Decimal('0')
    
    def get_total_count(self) -> int:
        """
        Get total count of chat history records.
        
        Returns:
            Total number of chat history records.
        """
        return self.session.query(ChatHistory).count()
    
    def count_old_records(self, cutoff_date: datetime) -> int:
        """
        Count chat history records older than cutoff date.
        
        Args:
            cutoff_date: Cutoff date for old records.
            
        Returns:
            Number of old records.
        """
        return self.session.query(ChatHistory)\
            .filter(ChatHistory.created_at < cutoff_date)\
            .count()
    
    def delete_old_chat_history(self, cutoff_date: datetime) -> int:
        """
        Delete chat history records older than cutoff date.
        
        Args:
            cutoff_date: Cutoff date for deletion.
            
        Returns:
            Number of records deleted.
        """
        deleted_count = self.session.query(ChatHistory)\
            .filter(ChatHistory.created_at < cutoff_date)\
            .delete()
        
        self.session.commit()
        return deleted_count


class AuditLogRepository:
    """Repository for QueryAuditLog CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        session_id: str,
        chat_history_id: Optional[int] = None,
        question_sanitized: Optional[str] = None,
        pii_patterns_detected: Optional[List[str]] = None,
        topic_validation_result: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        rejected: bool = False,
        rejection_reason: Optional[str] = None
    ) -> QueryAuditLog:
        """
        Create a new audit log record.
        
        Args:
            session_id: User session ID.
            chat_history_id: Related chat history ID.
            question_sanitized: Sanitized question text.
            pii_patterns_detected: List of PII patterns found.
            topic_validation_result: Topic validation result.
            ip_address: User IP address.
            user_agent: User agent string.
            rejected: Whether query was rejected.
            rejection_reason: Reason for rejection.
        
        Returns:
            Created QueryAuditLog instance.
        """
        audit = QueryAuditLog(
            session_id=session_id,
            chat_history_id=chat_history_id,
            question_sanitized=question_sanitized,
            pii_patterns_detected=pii_patterns_detected,
            topic_validation_result=topic_validation_result,
            ip_address=ip_address,
            user_agent=user_agent,
            rejected=rejected,
            rejection_reason=rejection_reason
        )
        self.session.add(audit)
        self.session.flush()
        return audit
    
    def get_rejected_queries(self, limit: Optional[int] = None) -> List[QueryAuditLog]:
        """
        Get rejected queries.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of QueryAuditLog instances for rejected queries.
        """
        query = self.session.query(QueryAuditLog)\
            .filter(QueryAuditLog.rejected == True)\
            .order_by(desc(QueryAuditLog.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_pii_detections(self, limit: Optional[int] = None) -> List[QueryAuditLog]:
        """
        Get queries where PII was detected.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of QueryAuditLog instances with PII detections.
        """
        query = self.session.query(QueryAuditLog)\
            .filter(QueryAuditLog.pii_patterns_detected.isnot(None))\
            .order_by(desc(QueryAuditLog.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_total_count(self) -> int:
        """
        Get total count of audit log records.
        
        Returns:
            Total number of audit log records.
        """
        return self.session.query(QueryAuditLog).count()
    
    def count_old_records(self, cutoff_date: datetime) -> int:
        """
        Count audit log records older than cutoff date.
        
        Args:
            cutoff_date: Cutoff date for old records.
            
        Returns:
            Number of old records.
        """
        return self.session.query(QueryAuditLog)\
            .filter(QueryAuditLog.created_at < cutoff_date)\
            .count()
    
    def delete_old_audit_logs(self, cutoff_date: datetime) -> int:
        """
        Delete audit log records older than cutoff date.
        
        Args:
            cutoff_date: Cutoff date for deletion.
            
        Returns:
            Number of records deleted.
        """
        deleted_count = self.session.query(QueryAuditLog)\
            .filter(QueryAuditLog.created_at < cutoff_date)\
            .delete()
        
        self.session.commit()
        return deleted_count


class MarketTendencyRepository:
    """Repository for MarketTendency CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        tendency: str,
        timestamp: datetime,
        confidence: Optional[Decimal] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> MarketTendency:
        """
        Create a new market tendency record.
        
        Args:
            tendency: Market tendency classification.
            timestamp: Tendency timestamp.
            confidence: Confidence score (0-1).
            metrics: Additional metrics as dictionary.
        
        Returns:
            Created MarketTendency instance.
        """
        market_tendency = MarketTendency(
            tendency=tendency,
            timestamp=timestamp,
            confidence=confidence,
            metrics=metrics
        )
        self.session.add(market_tendency)
        self.session.flush()
        return market_tendency
    
    def get_latest(self) -> Optional[MarketTendency]:
        """
        Get the latest market tendency.
        
        Returns:
            Latest MarketTendency instance or None.
        """
        return self.session.query(MarketTendency)\
            .order_by(desc(MarketTendency.timestamp))\
            .first()
    
    def get_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[MarketTendency]:
        """
        Get market tendencies within time range.
        
        Args:
            start_time: Start of time range.
            end_time: End of time range.
        
        Returns:
            List of MarketTendency instances ordered by timestamp.
        """
        return self.session.query(MarketTendency)\
            .filter(
                and_(
                    MarketTendency.timestamp >= start_time,
                    MarketTendency.timestamp <= end_time
                )
            )\
            .order_by(asc(MarketTendency.timestamp))\
            .all()
    
    def get_recent(self, limit: int = 10) -> List[MarketTendency]:
        """
        Get recent market tendencies.
        
        Args:
            limit: Number of records to retrieve.
        
        Returns:
            List of MarketTendency instances ordered by timestamp descending.
        """
        return self.session.query(MarketTendency)\
            .order_by(desc(MarketTendency.timestamp))\
            .limit(limit)\
            .all()



class AlertLogRepository:
    """Repository for AlertLog CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance.
        """
        self.session = session
    
    def create(
        self,
        crypto_id: int,
        shift_type: str,
        change_percent: Decimal,
        previous_price: Decimal,
        current_price: Decimal,
        alert_message: str,
        recipient_number: str,
        sms_provider: str,
        timestamp: datetime,
        sms_message_id: Optional[str] = None,
        success: bool = False,
        error_message: Optional[str] = None
    ) -> AlertLog:
        """
        Create a new alert log record.
        
        Args:
            crypto_id: Cryptocurrency ID.
            shift_type: Type of shift ('increase' or 'decrease').
            change_percent: Percentage change.
            previous_price: Previous price.
            current_price: Current price.
            alert_message: Alert message sent.
            recipient_number: Phone number that received alert.
            sms_provider: SMS provider used ('twilio' or 'aws_sns').
            timestamp: Alert timestamp.
            sms_message_id: SMS message ID from provider.
            success: Whether alert was sent successfully.
            error_message: Error message if failed.
        
        Returns:
            Created AlertLog instance.
        """
        alert_log = AlertLog(
            crypto_id=crypto_id,
            shift_type=shift_type,
            change_percent=change_percent,
            previous_price=previous_price,
            current_price=current_price,
            alert_message=alert_message,
            recipient_number=recipient_number,
            sms_provider=sms_provider,
            timestamp=timestamp,
            sms_message_id=sms_message_id,
            success=success,
            error_message=error_message
        )
        self.session.add(alert_log)
        self.session.flush()
        return alert_log
    
    def get_recent_alerts(self, limit: int = 50) -> List[AlertLog]:
        """
        Get recent alert logs.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of AlertLog instances ordered by timestamp descending.
        """
        return self.session.query(AlertLog)\
            .order_by(desc(AlertLog.timestamp))\
            .limit(limit)\
            .all()
    
    def get_alerts_by_crypto(
        self,
        crypto_id: int,
        limit: Optional[int] = None
    ) -> List[AlertLog]:
        """
        Get alert logs for a specific cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
            limit: Maximum number of results.
        
        Returns:
            List of AlertLog instances ordered by timestamp descending.
        """
        query = self.session.query(AlertLog)\
            .filter(AlertLog.crypto_id == crypto_id)\
            .order_by(desc(AlertLog.timestamp))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_failed_alerts(self, limit: Optional[int] = None) -> List[AlertLog]:
        """
        Get failed alert logs.
        
        Args:
            limit: Maximum number of results.
        
        Returns:
            List of AlertLog instances for failed alerts.
        """
        query = self.session.query(AlertLog)\
            .filter(AlertLog.success == False)\
            .order_by(desc(AlertLog.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_last_alert_time(self, crypto_id: int) -> Optional[datetime]:
        """
        Get timestamp of last alert for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Timestamp of last alert or None if no alerts exist.
        """
        result = self.session.query(AlertLog.timestamp)\
            .filter(AlertLog.crypto_id == crypto_id)\
            .order_by(desc(AlertLog.timestamp))\
            .first()
        return result[0] if result else None
    
    def count_alerts_by_crypto(self, crypto_id: int) -> int:
        """
        Count total alerts for a cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID.
        
        Returns:
            Number of alerts.
        """
        return self.session.query(AlertLog)\
            .filter(AlertLog.crypto_id == crypto_id)\
            .count()

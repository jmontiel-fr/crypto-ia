"""
SQLAlchemy models for all database entities.
Defines the database schema for cryptocurrencies, price history, predictions,
chat history, audit logs, and market tendencies.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, Boolean, Text,
    ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from src.data.database import Base


class Cryptocurrency(Base):
    """
    Cryptocurrency metadata model.
    Stores information about tracked cryptocurrencies.
    """
    __tablename__ = 'cryptocurrencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    market_cap_rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="cryptocurrency", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="cryptocurrency", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cryptocurrency(id={self.id}, symbol='{self.symbol}', name='{self.name}')>"


class PriceHistory(Base):
    """
    Historical price data model.
    Stores hourly cryptocurrency price data.
    """
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crypto_id = Column(Integer, ForeignKey('cryptocurrencies.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price_usd = Column(Numeric(20, 8), nullable=False)
    volume_24h = Column(Numeric(20, 2), nullable=True)
    market_cap = Column(Numeric(20, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    cryptocurrency = relationship("Cryptocurrency", back_populates="price_history")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_price_history_crypto_timestamp', 'crypto_id', 'timestamp'),
        Index('idx_price_history_timestamp', 'timestamp'),
        # Unique constraint to prevent duplicate entries
        Index('uq_price_history_crypto_timestamp', 'crypto_id', 'timestamp', unique=True),
    )
    
    def __repr__(self):
        return f"<PriceHistory(crypto_id={self.crypto_id}, timestamp={self.timestamp}, price={self.price_usd})>"


class Prediction(Base):
    """
    Prediction results model.
    Stores ML model predictions for cryptocurrency prices.
    """
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crypto_id = Column(Integer, ForeignKey('cryptocurrencies.id', ondelete='CASCADE'), nullable=False)
    prediction_date = Column(DateTime, nullable=False)
    predicted_price = Column(Numeric(20, 8), nullable=True)
    confidence_score = Column(Numeric(5, 4), nullable=True)
    prediction_horizon_hours = Column(Integer, nullable=False, default=24)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    cryptocurrency = relationship("Cryptocurrency", back_populates="predictions")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_predictions_crypto_date', 'crypto_id', 'prediction_date'),
        Index('idx_predictions_date', 'prediction_date'),
    )
    
    def __repr__(self):
        return f"<Prediction(crypto_id={self.crypto_id}, date={self.prediction_date}, price={self.predicted_price})>"


class ChatHistory(Base):
    """
    Chat history model with full tracing.
    Stores user questions, AI responses, and metadata for cost tracking and analysis.
    """
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    question_hash = Column(String(64), nullable=True)  # SHA256 hash for deduplication
    topic_valid = Column(Boolean, nullable=False, default=True)
    pii_detected = Column(Boolean, nullable=False, default=False)
    context_used = Column(JSON, nullable=True)  # LSTM predictions and data used
    openai_tokens_input = Column(Integer, nullable=True)
    openai_tokens_output = Column(Integer, nullable=True)
    openai_cost_usd = Column(Numeric(10, 6), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    audit_logs = relationship("QueryAuditLog", back_populates="chat_history", cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_chat_history_session_created', 'session_id', 'created_at'),
        Index('idx_chat_history_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, session='{self.session_id}', created={self.created_at})>"


class QueryAuditLog(Base):
    """
    Query audit log model for security and compliance.
    Tracks all queries with PII detection and validation results.
    """
    __tablename__ = 'query_audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    chat_history_id = Column(Integer, ForeignKey('chat_history.id', ondelete='CASCADE'), nullable=True)
    question_sanitized = Column(Text, nullable=True)  # Question with PII removed
    pii_patterns_detected = Column(JSON, nullable=True)  # Array of PII types found (stored as JSON for compatibility)
    topic_validation_result = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    rejected = Column(Boolean, nullable=False, default=False)
    rejection_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    chat_history = relationship("ChatHistory", back_populates="audit_logs")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_audit_log_session_created', 'session_id', 'created_at'),
        Index('idx_audit_log_rejected_created', 'rejected', 'created_at'),
    )
    
    def __repr__(self):
        return f"<QueryAuditLog(id={self.id}, session='{self.session_id}', rejected={self.rejected})>"


class MarketTendency(Base):
    """
    Market tendency tracking model.
    Stores market tendency classifications over time.
    """
    __tablename__ = 'market_tendencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tendency = Column(String(50), nullable=False)  # bullish, bearish, volatile, stable, consolidating
    confidence = Column(Numeric(5, 4), nullable=True)
    metrics = Column(JSON, nullable=True)  # Additional metrics as JSON
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_market_tendency_timestamp', 'timestamp'),
        Index('idx_market_tendency_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<MarketTendency(id={self.id}, tendency='{self.tendency}', timestamp={self.timestamp})>"


class AlertLog(Base):
    """
    Alert log model for tracking sent alerts.
    Stores information about market shift alerts sent via SMS.
    """
    __tablename__ = 'alert_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crypto_id = Column(Integer, ForeignKey('cryptocurrencies.id', ondelete='CASCADE'), nullable=False)
    shift_type = Column(String(20), nullable=False)  # 'increase' or 'decrease'
    change_percent = Column(Numeric(10, 2), nullable=False)
    previous_price = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=False)
    alert_message = Column(Text, nullable=False)
    recipient_number = Column(String(20), nullable=False)
    sms_provider = Column(String(20), nullable=False)  # 'twilio' or 'aws_sns'
    sms_message_id = Column(String(100), nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    cryptocurrency = relationship("Cryptocurrency")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_alert_log_crypto_timestamp', 'crypto_id', 'timestamp'),
        Index('idx_alert_log_timestamp', 'timestamp'),
        Index('idx_alert_log_success', 'success', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AlertLog(id={self.id}, crypto_id={self.crypto_id}, shift_type='{self.shift_type}', success={self.success})>"

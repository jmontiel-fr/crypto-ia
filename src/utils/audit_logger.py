"""
Comprehensive audit logging system.
Tracks all security-relevant events and user activities for compliance and monitoring.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from flask import request, g
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON

from src.data.database import Base

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_ROTATED = "api_key_rotated"
    
    # Security events
    PII_DETECTED = "pii_detected"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_FAILURE = "csrf_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Data access events
    PREDICTION_ACCESSED = "prediction_accessed"
    MARKET_DATA_ACCESSED = "market_data_accessed"
    CHAT_QUERY_PROCESSED = "chat_query_processed"
    
    # Administrative events
    ADMIN_ACTION = "admin_action"
    CONFIG_CHANGED = "config_changed"
    DATA_COLLECTION_TRIGGERED = "data_collection_triggered"
    
    # System events
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ALERT = "performance_alert"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AuditLog(Base):
    """
    Audit log database model.
    Stores all audit events for compliance and security monitoring.
    """
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(200), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    additional_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', severity='{self.severity}')>"


class AuditLogger:
    """
    Comprehensive audit logging system.
    Handles logging of security events, user activities, and system events.
    """
    
    def __init__(self, session: Session):
        """Initialize audit logger with database session."""
        self.session = session
        
    def log_event(self, event: AuditEvent) -> Optional[AuditLog]:
        """
        Log an audit event to the database.
        
        Args:
            event: AuditEvent instance to log
            
        Returns:
            Created AuditLog instance or None if failed
        """
        try:
            audit_log = AuditLog(
                event_type=event.event_type.value,
                severity=event.severity.value,
                message=event.message,
                user_id=event.user_id,
                session_id=event.session_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                endpoint=event.endpoint,
                method=event.method,
                status_code=event.status_code,
                response_time_ms=event.response_time_ms,
                additional_data=event.additional_data,
                created_at=event.timestamp
            )
            
            self.session.add(audit_log)
            self.session.commit()
            
            logger.debug(f"Logged audit event: {event.event_type.value}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
            self.session.rollback()
            return None
    
    def log_pii_detection(self, session_id: str, patterns: List[str], 
                         question_sanitized: str, ip_address: str = None,
                         user_agent: str = None) -> None:
        """
        Log PII detection event.
        
        Args:
            session_id: User session ID
            patterns: List of PII patterns detected
            question_sanitized: Sanitized version of the question
            ip_address: Client IP address
            user_agent: Client user agent
        """
        event = AuditEvent(
            event_type=AuditEventType.PII_DETECTED,
            severity=AuditSeverity.HIGH,
            message=f"PII detected in user query: {', '.join(patterns)}",
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={
                "pii_patterns": patterns,
                "question_sanitized": question_sanitized,
                "pattern_count": len(patterns)
            }
        )
        self.log_event(event)
    
    def log_openai_usage(self, session_id: str, input_tokens: int, 
                        output_tokens: int, cost_usd: float,
                        response_time_ms: int, model: str = None) -> None:
        """
        Log OpenAI API usage for cost tracking.
        
        Args:
            session_id: User session ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            response_time_ms: Response time in milliseconds
            model: OpenAI model used
        """
        event = AuditEvent(
            event_type=AuditEventType.CHAT_QUERY_PROCESSED,
            severity=AuditSeverity.LOW,
            message=f"OpenAI API usage: {input_tokens + output_tokens} tokens, ${cost_usd:.6f}",
            session_id=session_id,
            response_time_ms=response_time_ms,
            additional_data={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
                "model": model or "unknown"
            }
        )
        self.log_event(event)
    
    def log_api_access(self, endpoint: str, method: str, status_code: int,
                      response_time_ms: int, user_id: str = None,
                      session_id: str = None, ip_address: str = None,
                      user_agent: str = None) -> None:
        """
        Log API endpoint access.
        
        Args:
            endpoint: API endpoint accessed
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            user_id: User ID if authenticated
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
        """
        # Determine severity based on status code
        if status_code >= 500:
            severity = AuditSeverity.HIGH
        elif status_code >= 400:
            severity = AuditSeverity.MEDIUM
        else:
            severity = AuditSeverity.LOW
            
        event_type = AuditEventType.PREDICTION_ACCESSED
        if "market" in endpoint.lower():
            event_type = AuditEventType.MARKET_DATA_ACCESSED
        elif "chat" in endpoint.lower():
            event_type = AuditEventType.CHAT_QUERY_PROCESSED
        elif "admin" in endpoint.lower():
            event_type = AuditEventType.ADMIN_ACTION
            
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            message=f"{method} {endpoint} - {status_code}",
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms
        )
        self.log_event(event)
    
    def log_security_event(self, event_type: AuditEventType, message: str,
                          severity: AuditSeverity = AuditSeverity.HIGH,
                          session_id: str = None, ip_address: str = None,
                          user_agent: str = None, additional_data: Dict = None) -> None:
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            message: Event description
            severity: Event severity
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
            additional_data: Additional event data
        """
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data
        )
        self.log_event(event)
    
    def get_audit_logs(self, limit: int = 100, event_type: str = None,
                      severity: str = None, start_date: datetime = None,
                      end_date: datetime = None) -> List[AuditLog]:
        """
        Retrieve audit logs with filtering.
        
        Args:
            limit: Maximum number of logs to return
            event_type: Filter by event type
            severity: Filter by severity
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of AuditLog instances
        """
        query = self.session.query(AuditLog)
        
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
            
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        try:
            deleted_count = self.session.query(AuditLog)\
                .filter(AuditLog.created_at < cutoff_date)\
                .delete()
            
            self.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old audit logs (older than {retention_days} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}", exc_info=True)
            self.session.rollback()
            return 0


def get_request_info() -> Dict[str, str]:
    """
    Extract request information from Flask request context.
    
    Returns:
        Dictionary with IP address and user agent
    """
    try:
        return {
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown')
        }
    except RuntimeError:
        # Outside request context
        return {
            "ip_address": None,
            "user_agent": None
        }
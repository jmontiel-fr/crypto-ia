"""
Audit Logging Middleware for Flask API.
Automatically logs all API requests and responses for security and compliance.
"""

import logging
import time
from functools import wraps
from typing import Optional
from flask import request, g, current_app
from sqlalchemy.orm import Session

from src.data.database import get_session
from src.utils.audit_logger import AuditLogger, AuditEventType, AuditSeverity, get_request_info

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Middleware for automatic audit logging of API requests.
    """
    
    def __init__(self, app=None):
        """Initialize audit middleware."""
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
    
    def before_request(self):
        """Called before each request."""
        # Store request start time
        g.request_start_time = time.time()
        
        # Initialize audit logger session
        try:
            g.audit_session = get_session()
            g.audit_logger = AuditLogger(g.audit_session)
        except Exception as e:
            logger.error(f"Failed to initialize audit logger: {e}", exc_info=True)
            g.audit_session = None
            g.audit_logger = None
    
    def after_request(self, response):
        """Called after each request."""
        if not hasattr(g, 'audit_logger') or g.audit_logger is None:
            return response
        
        try:
            # Calculate response time
            response_time_ms = None
            if hasattr(g, 'request_start_time'):
                response_time_ms = int((time.time() - g.request_start_time) * 1000)
            
            # Get request info
            request_info = get_request_info()
            
            # Extract user/session info
            user_id = getattr(g, 'user_id', None)
            session_id = getattr(g, 'session_id', None)
            
            # Log the API access
            g.audit_logger.log_api_access(
                endpoint=request.endpoint or request.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                session_id=session_id,
                ip_address=request_info.get('ip_address'),
                user_agent=request_info.get('user_agent')
            )
            
        except Exception as e:
            logger.error(f"Error in audit middleware after_request: {e}", exc_info=True)
        
        return response
    
    def teardown_request(self, exception=None):
        """Called when request context is torn down."""
        if hasattr(g, 'audit_session') and g.audit_session:
            try:
                g.audit_session.close()
            except Exception as e:
                logger.error(f"Error closing audit session: {e}", exc_info=True)


def audit_endpoint(event_type: AuditEventType = None, severity: AuditSeverity = AuditSeverity.LOW):
    """
    Decorator for specific endpoint audit logging.
    
    Args:
        event_type: Specific event type for this endpoint
        severity: Severity level for this endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the original function
            result = f(*args, **kwargs)
            
            # Log specific event if audit logger is available
            if hasattr(g, 'audit_logger') and g.audit_logger:
                try:
                    request_info = get_request_info()
                    
                    # Determine event type if not specified
                    if event_type is None:
                        endpoint = request.endpoint or request.path
                        if 'prediction' in endpoint.lower():
                            audit_event_type = AuditEventType.PREDICTION_ACCESSED
                        elif 'market' in endpoint.lower():
                            audit_event_type = AuditEventType.MARKET_DATA_ACCESSED
                        elif 'chat' in endpoint.lower():
                            audit_event_type = AuditEventType.CHAT_QUERY_PROCESSED
                        elif 'admin' in endpoint.lower():
                            audit_event_type = AuditEventType.ADMIN_ACTION
                        else:
                            audit_event_type = AuditEventType.PREDICTION_ACCESSED
                    else:
                        audit_event_type = event_type
                    
                    # Log the specific event
                    g.audit_logger.log_security_event(
                        event_type=audit_event_type,
                        message=f"Endpoint accessed: {request.method} {request.endpoint or request.path}",
                        severity=severity,
                        session_id=getattr(g, 'session_id', None),
                        ip_address=request_info.get('ip_address'),
                        user_agent=request_info.get('user_agent'),
                        additional_data={
                            "endpoint": request.endpoint or request.path,
                            "method": request.method,
                            "user_id": getattr(g, 'user_id', None)
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error in audit endpoint decorator: {e}", exc_info=True)
            
            return result
        
        return decorated_function
    return decorator


def log_security_event(event_type: AuditEventType, message: str, 
                      severity: AuditSeverity = AuditSeverity.HIGH,
                      additional_data: dict = None):
    """
    Helper function to log security events from anywhere in the API.
    
    Args:
        event_type: Type of security event
        message: Event description
        severity: Event severity
        additional_data: Additional event data
    """
    if hasattr(g, 'audit_logger') and g.audit_logger:
        try:
            request_info = get_request_info()
            
            g.audit_logger.log_security_event(
                event_type=event_type,
                message=message,
                severity=severity,
                session_id=getattr(g, 'session_id', None),
                ip_address=request_info.get('ip_address'),
                user_agent=request_info.get('user_agent'),
                additional_data=additional_data
            )
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}", exc_info=True)
    else:
        # Fallback to regular logging if audit logger not available
        logger.warning(f"Security event (no audit logger): {event_type.value} - {message}")


def log_pii_detection(session_id: str, patterns: list, question_sanitized: str):
    """
    Helper function to log PII detection events.
    
    Args:
        session_id: User session ID
        patterns: List of PII patterns detected
        question_sanitized: Sanitized version of the question
    """
    if hasattr(g, 'audit_logger') and g.audit_logger:
        try:
            request_info = get_request_info()
            
            g.audit_logger.log_pii_detection(
                session_id=session_id,
                patterns=patterns,
                question_sanitized=question_sanitized,
                ip_address=request_info.get('ip_address'),
                user_agent=request_info.get('user_agent')
            )
            
        except Exception as e:
            logger.error(f"Error logging PII detection: {e}", exc_info=True)
    else:
        logger.warning(f"PII detection (no audit logger): {patterns} in session {session_id}")


def log_openai_usage(session_id: str, input_tokens: int, output_tokens: int, 
                    cost_usd: float, response_time_ms: int, model: str = None):
    """
    Helper function to log OpenAI API usage.
    
    Args:
        session_id: User session ID
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Cost in USD
        response_time_ms: Response time in milliseconds
        model: OpenAI model used
    """
    if hasattr(g, 'audit_logger') and g.audit_logger:
        try:
            g.audit_logger.log_openai_usage(
                session_id=session_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                response_time_ms=response_time_ms,
                model=model
            )
            
        except Exception as e:
            logger.error(f"Error logging OpenAI usage: {e}", exc_info=True)
    else:
        logger.info(f"OpenAI usage (no audit logger): {input_tokens + output_tokens} tokens, ${cost_usd:.6f}")
"""
Secure logging utilities to prevent secrets from appearing in logs.
"""

import logging
import re
from typing import Optional, List


class SecureFormatter(logging.Formatter):
    """
    Custom log formatter that redacts sensitive information.
    """
    
    # Patterns to detect and redact
    SENSITIVE_PATTERNS = [
        # API keys and tokens
        (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(api[_-]?secret["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(auth[_-]?token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # Bearer tokens
        (re.compile(r'(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE), r'\1***REDACTED***'),
        
        # Passwords
        (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']{6,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(passwd["\']?\s*[:=]\s*["\']?)([^\s"\']{6,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(pwd["\']?\s*[:=]\s*["\']?)([^\s"\']{6,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # Secret keys
        (re.compile(r'(secret[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # Database connection strings with passwords
        (re.compile(r'(postgresql://[^:]+:)([^@]+)(@)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(mysql://[^:]+:)([^@]+)(@)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # AWS credentials
        (re.compile(r'(aws[_-]?access[_-]?key[_-]?id["\']?\s*[:=]\s*["\']?)([A-Z0-9]{20})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        (re.compile(r'(aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9/+]{40})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # Twilio credentials
        (re.compile(r'(account[_-]?sid["\']?\s*[:=]\s*["\']?)([A-Z0-9]{34})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
        
        # Generic long alphanumeric strings that might be secrets (after specific patterns)
        # This is more aggressive and might catch false positives
        # (re.compile(r'(["\']?)([a-zA-Z0-9_\-]{40,})(["\']?)', re.IGNORECASE), r'\1***REDACTED***\3'),
    ]
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """
        Initialize secure formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
        """
        super().__init__(fmt, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record and redact sensitive information.
        
        Args:
            record: Log record to format
        
        Returns:
            Formatted and sanitized log message
        """
        # Format the message normally first
        message = super().format(record)
        
        # Apply redaction patterns
        sanitized_message = self._redact_sensitive_info(message)
        
        return sanitized_message
    
    def _redact_sensitive_info(self, message: str) -> str:
        """
        Redact sensitive information from message.
        
        Args:
            message: Original message
        
        Returns:
            Sanitized message
        """
        sanitized = message
        
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        
        return sanitized


def setup_secure_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Set up secure logging with sensitive information redaction.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_format: Optional custom log format
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create secure formatter
    formatter = SecureFormatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create directory if it doesn't exist
        import os
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logging.info(f"Secure logging configured with level: {log_level}")


def validate_log_message(message: str, raise_on_secret: bool = False) -> bool:
    """
    Validate that a log message doesn't contain secrets.
    
    Args:
        message: Message to validate
        raise_on_secret: Whether to raise exception if secret detected
    
    Returns:
        True if no secrets detected, False otherwise
    
    Raises:
        ValueError: If raise_on_secret is True and secret detected
    """
    formatter = SecureFormatter()
    sanitized = formatter._redact_sensitive_info(message)
    
    has_secrets = '***REDACTED***' in sanitized
    
    if has_secrets:
        if raise_on_secret:
            raise ValueError("Log message contains sensitive information")
        return False
    
    return True


class SecureLogger:
    """
    Wrapper around standard logger that ensures no secrets are logged.
    """
    
    def __init__(self, name: str):
        """
        Initialize secure logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self._formatter = SecureFormatter()
    
    def _sanitize(self, message: str) -> str:
        """Sanitize message before logging."""
        return self._formatter._redact_sensitive_info(message)
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(self._sanitize(message), *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""
        self.logger.info(self._sanitize(message), *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(self._sanitize(message), *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message."""
        self.logger.error(self._sanitize(message), *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(self._sanitize(message), *args, **kwargs)


def get_secure_logger(name: str) -> SecureLogger:
    """
    Get a secure logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        SecureLogger instance
    """
    return SecureLogger(name)

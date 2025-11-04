"""
Input validation and sanitization utilities.
Provides comprehensive validation for API endpoints to prevent security vulnerabilities.
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, field: str, message: str, code: str = 'VALIDATION_ERROR'):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{field}: {message}")


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    errors: List[ValidationError]
    sanitized_data: Dict[str, Any]
    
    def add_error(self, field: str, message: str, code: str = 'VALIDATION_ERROR'):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, code))
        self.is_valid = False


class InputValidator:
    """
    Comprehensive input validator with sanitization capabilities.
    """
    
    # Common regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?[0-9]{10,15}$')
    CRYPTO_SYMBOL_PATTERN = re.compile(r'^[A-Z]{2,10}$')
    API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]{20,}$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)", re.IGNORECASE),
        re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),
        re.compile(r"(\b(OR|AND)\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        re.compile(r"('|(\\x27)|(\\x2D\\x2D))", re.IGNORECASE),
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),
        re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<object[^>]*>.*?</object>", re.IGNORECASE | re.DOTALL),
        re.compile(r"<embed[^>]*>", re.IGNORECASE),
    ]
    
    def __init__(self):
        """Initialize the validator."""
        self.result = ValidationResult(is_valid=True, errors=[], sanitized_data={})
    
    def validate_string(
        self,
        field: str,
        value: Any,
        min_length: int = 0,
        max_length: int = 1000,
        pattern: Optional[re.Pattern] = None,
        required: bool = True,
        allow_empty: bool = False
    ) -> str:
        """
        Validate and sanitize string input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Optional regex pattern to match
            required: Whether field is required
            allow_empty: Whether to allow empty strings
        
        Returns:
            Sanitized string value
        
        Raises:
            ValidationError: If validation fails
        """
        # Check if value exists
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return ""
        
        # Convert to string
        if not isinstance(value, str):
            value = str(value)
        
        # Check empty string
        if not value.strip():
            if required and not allow_empty:
                raise ValidationError(field, "Field cannot be empty", "EMPTY")
            if not allow_empty:
                return ""
        
        # Sanitize for XSS
        sanitized = self._sanitize_xss(value)
        
        # Check for SQL injection
        if self._contains_sql_injection(sanitized):
            raise ValidationError(field, "Invalid characters detected", "INVALID_CHARS")
        
        # Check length
        if len(sanitized) < min_length:
            raise ValidationError(field, f"Must be at least {min_length} characters", "TOO_SHORT")
        
        if len(sanitized) > max_length:
            raise ValidationError(field, f"Must be no more than {max_length} characters", "TOO_LONG")
        
        # Check pattern
        if pattern and not pattern.match(sanitized):
            raise ValidationError(field, "Invalid format", "INVALID_FORMAT")
        
        return sanitized.strip()
    
    def validate_integer(
        self,
        field: str,
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True
    ) -> Optional[int]:
        """
        Validate integer input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            required: Whether field is required
        
        Returns:
            Validated integer value
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        # Try to convert to integer
        try:
            if isinstance(value, str):
                # Remove whitespace and check for empty
                value = value.strip()
                if not value:
                    if required:
                        raise ValidationError(field, "Field is required", "REQUIRED")
                    return None
            
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(field, "Must be a valid integer", "INVALID_TYPE")
        
        # Check range
        if min_value is not None and int_value < min_value:
            raise ValidationError(field, f"Must be at least {min_value}", "TOO_SMALL")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(field, f"Must be no more than {max_value}", "TOO_LARGE")
        
        return int_value
    
    def validate_float(
        self,
        field: str,
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        required: bool = True
    ) -> Optional[float]:
        """
        Validate float input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            required: Whether field is required
        
        Returns:
            Validated float value
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        # Try to convert to float
        try:
            if isinstance(value, str):
                # Remove whitespace and check for empty
                value = value.strip()
                if not value:
                    if required:
                        raise ValidationError(field, "Field is required", "REQUIRED")
                    return None
            
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(field, "Must be a valid number", "INVALID_TYPE")
        
        # Check for NaN and infinity
        if not isinstance(float_value, (int, float)) or float_value != float_value:  # NaN check
            raise ValidationError(field, "Must be a valid number", "INVALID_TYPE")
        
        # Check range
        if min_value is not None and float_value < min_value:
            raise ValidationError(field, f"Must be at least {min_value}", "TOO_SMALL")
        
        if max_value is not None and float_value > max_value:
            raise ValidationError(field, f"Must be no more than {max_value}", "TOO_LARGE")
        
        return float_value
    
    def validate_boolean(
        self,
        field: str,
        value: Any,
        required: bool = True
    ) -> Optional[bool]:
        """
        Validate boolean input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
        
        Returns:
            Validated boolean value
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        # Handle string representations
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ('true', '1', 'yes', 'on'):
                return True
            elif value in ('false', '0', 'no', 'off'):
                return False
            elif not value:
                if required:
                    raise ValidationError(field, "Field is required", "REQUIRED")
                return None
            else:
                raise ValidationError(field, "Must be a valid boolean", "INVALID_TYPE")
        
        # Handle boolean type
        if isinstance(value, bool):
            return value
        
        # Handle numeric types
        if isinstance(value, (int, float)):
            return bool(value)
        
        raise ValidationError(field, "Must be a valid boolean", "INVALID_TYPE")
    
    def validate_email(self, field: str, value: Any, required: bool = True) -> Optional[str]:
        """
        Validate email address.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
        
        Returns:
            Validated email address
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        email = self.validate_string(field, value, max_length=254, required=required)
        
        if email and not self.EMAIL_PATTERN.match(email):
            raise ValidationError(field, "Invalid email format", "INVALID_EMAIL")
        
        return email.lower() if email else None
    
    def validate_phone(self, field: str, value: Any, required: bool = True) -> Optional[str]:
        """
        Validate phone number.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
        
        Returns:
            Validated phone number
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        phone = self.validate_string(field, value, max_length=20, required=required)
        
        if phone:
            # Remove common formatting characters
            cleaned_phone = re.sub(r'[\s\-\(\)\.]+', '', phone)
            
            if not self.PHONE_PATTERN.match(cleaned_phone):
                raise ValidationError(field, "Invalid phone number format", "INVALID_PHONE")
            
            return cleaned_phone
        
        return None
    
    def validate_crypto_symbol(self, field: str, value: Any, required: bool = True) -> Optional[str]:
        """
        Validate cryptocurrency symbol.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
        
        Returns:
            Validated crypto symbol
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        symbol = self.validate_string(field, value, min_length=2, max_length=10, required=required)
        
        if symbol:
            symbol = symbol.upper()
            if not self.CRYPTO_SYMBOL_PATTERN.match(symbol):
                raise ValidationError(field, "Invalid cryptocurrency symbol", "INVALID_SYMBOL")
            
            return symbol
        
        return None
    
    def validate_datetime(
        self,
        field: str,
        value: Any,
        required: bool = True,
        format_string: str = "%Y-%m-%d"
    ) -> Optional[datetime]:
        """
        Validate datetime input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
            format_string: Expected datetime format
        
        Returns:
            Validated datetime object
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                if required:
                    raise ValidationError(field, "Field is required", "REQUIRED")
                return None
            
            try:
                return datetime.strptime(value, format_string)
            except ValueError:
                raise ValidationError(field, f"Invalid date format, expected {format_string}", "INVALID_DATE")
        
        raise ValidationError(field, "Must be a valid date", "INVALID_TYPE")
    
    def validate_choice(
        self,
        field: str,
        value: Any,
        choices: List[str],
        required: bool = True,
        case_sensitive: bool = False
    ) -> Optional[str]:
        """
        Validate choice from predefined options.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            choices: List of valid choices
            required: Whether field is required
            case_sensitive: Whether comparison is case sensitive
        
        Returns:
            Validated choice
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        choice = self.validate_string(field, value, required=required)
        
        if choice:
            # Prepare choices for comparison
            if case_sensitive:
                valid_choices = choices
                comparison_value = choice
            else:
                valid_choices = [c.lower() for c in choices]
                comparison_value = choice.lower()
            
            if comparison_value not in valid_choices:
                raise ValidationError(
                    field,
                    f"Must be one of: {', '.join(choices)}",
                    "INVALID_CHOICE"
                )
            
            # Return original case from choices if not case sensitive
            if not case_sensitive:
                for original_choice in choices:
                    if original_choice.lower() == comparison_value:
                        return original_choice
            
            return choice
        
        return None
    
    def validate_json_object(
        self,
        field: str,
        value: Any,
        required: bool = True,
        max_size: int = 10000
    ) -> Optional[Dict[str, Any]]:
        """
        Validate JSON object input.
        
        Args:
            field: Field name for error reporting
            value: Value to validate
            required: Whether field is required
            max_size: Maximum JSON string size
        
        Returns:
            Validated dictionary
        
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(field, "Field is required", "REQUIRED")
            return None
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                if required:
                    raise ValidationError(field, "Field is required", "REQUIRED")
                return None
            
            if len(value) > max_size:
                raise ValidationError(field, f"JSON too large (max {max_size} characters)", "TOO_LARGE")
            
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValidationError(field, f"Invalid JSON: {str(e)}", "INVALID_JSON")
        
        raise ValidationError(field, "Must be a valid JSON object", "INVALID_TYPE")
    
    def _sanitize_xss(self, value: str) -> str:
        """
        Sanitize string for XSS prevention.
        
        Args:
            value: String to sanitize
        
        Returns:
            Sanitized string
        """
        # HTML escape
        sanitized = html.escape(value, quote=True)
        
        # Remove dangerous patterns
        for pattern in self.XSS_PATTERNS:
            sanitized = pattern.sub('', sanitized)
        
        return sanitized
    
    def _contains_sql_injection(self, value: str) -> bool:
        """
        Check if string contains SQL injection patterns.
        
        Args:
            value: String to check
        
        Returns:
            True if SQL injection detected
        """
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                logger.warning(f"SQL injection pattern detected: {pattern.pattern}")
                return True
        
        return False


def validate_request_data(
    data: Dict[str, Any],
    validation_rules: Dict[str, Callable[[InputValidator, str, Any], Any]]
) -> ValidationResult:
    """
    Validate request data using provided rules.
    
    Args:
        data: Request data to validate
        validation_rules: Dictionary mapping field names to validation functions
    
    Returns:
        ValidationResult with validation status and sanitized data
    """
    validator = InputValidator()
    result = ValidationResult(is_valid=True, errors=[], sanitized_data={})
    
    for field, validation_func in validation_rules.items():
        try:
            value = data.get(field)
            sanitized_value = validation_func(validator, field, value)
            result.sanitized_data[field] = sanitized_value
        except ValidationError as e:
            result.add_error(e.field, e.message, e.code)
    
    return result


# Common validation rule factories
def required_string(min_length: int = 1, max_length: int = 1000, pattern: Optional[re.Pattern] = None):
    """Factory for required string validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> str:
        return validator.validate_string(field, value, min_length, max_length, pattern, required=True)
    return validate


def optional_string(min_length: int = 0, max_length: int = 1000, pattern: Optional[re.Pattern] = None):
    """Factory for optional string validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> Optional[str]:
        return validator.validate_string(field, value, min_length, max_length, pattern, required=False)
    return validate


def required_integer(min_value: Optional[int] = None, max_value: Optional[int] = None):
    """Factory for required integer validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> int:
        return validator.validate_integer(field, value, min_value, max_value, required=True)
    return validate


def optional_integer(min_value: Optional[int] = None, max_value: Optional[int] = None):
    """Factory for optional integer validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> Optional[int]:
        return validator.validate_integer(field, value, min_value, max_value, required=False)
    return validate


def required_choice(choices: List[str], case_sensitive: bool = False):
    """Factory for required choice validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> str:
        return validator.validate_choice(field, value, choices, required=True, case_sensitive=case_sensitive)
    return validate


def optional_choice(choices: List[str], case_sensitive: bool = False):
    """Factory for optional choice validation."""
    def validate(validator: InputValidator, field: str, value: Any) -> Optional[str]:
        return validator.validate_choice(field, value, choices, required=False, case_sensitive=case_sensitive)
    return validate
"""
API utility functions.
Provides common utilities for request validation and response formatting.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from flask import request
from functools import wraps

logger = logging.getLogger(__name__)


def validate_required_fields(data: dict, required_fields: list) -> Tuple[bool, Optional[str]]:
    """
    Validate that required fields are present in request data.
    
    Args:
        data: Request data dictionary
        required_fields: List of required field names
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "Request body is required"
    
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def validate_field_type(data: dict, field: str, expected_type: type) -> Tuple[bool, Optional[str]]:
    """
    Validate field type.
    
    Args:
        data: Request data dictionary
        field: Field name
        expected_type: Expected Python type
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if field not in data:
        return True, None  # Field not present, skip type check
    
    if not isinstance(data[field], expected_type):
        return False, f"Field '{field}' must be of type {expected_type.__name__}"
    
    return True, None


def validate_string_length(
    value: str,
    field_name: str,
    min_length: int = 0,
    max_length: int = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate string length.
    
    Args:
        value: String value to validate
        field_name: Name of the field (for error message)
        min_length: Minimum length (default: 0)
        max_length: Maximum length (default: None = no limit)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(value) < min_length:
        return False, f"Field '{field_name}' must be at least {min_length} characters"
    
    if max_length and len(value) > max_length:
        return False, f"Field '{field_name}' must not exceed {max_length} characters"
    
    return True, None


def validate_integer_range(
    value: int,
    field_name: str,
    min_value: int = None,
    max_value: int = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate integer range.
    
    Args:
        value: Integer value to validate
        field_name: Name of the field (for error message)
        min_value: Minimum value (default: None = no limit)
        max_value: Maximum value (default: None = no limit)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_value is not None and value < min_value:
        return False, f"Field '{field_name}' must be at least {min_value}"
    
    if max_value is not None and value > max_value:
        return False, f"Field '{field_name}' must not exceed {max_value}"
    
    return True, None


def validate_enum(
    value: str,
    field_name: str,
    valid_values: list
) -> Tuple[bool, Optional[str]]:
    """
    Validate enum value.
    
    Args:
        value: Value to validate
        field_name: Name of the field (for error message)
        valid_values: List of valid values
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value not in valid_values:
        return False, f"Field '{field_name}' must be one of: {', '.join(valid_values)}"
    
    return True, None


def format_error_response(
    code: str,
    message: str,
    details: str = None,
    status_code: int = 400
) -> Tuple[Dict[str, Any], int]:
    """
    Format standardized error response.
    
    Args:
        code: Error code (e.g., 'INVALID_REQUEST')
        message: Human-readable error message
        details: Additional error details (optional)
        status_code: HTTP status code
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'error': {
            'code': code,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return response, status_code


def format_success_response(
    data: Dict[str, Any],
    message: str = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        metadata: Optional metadata (pagination, etc.)
    
    Returns:
        Response dictionary
    """
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if metadata:
        response['metadata'] = metadata
    
    return response


def log_request_info():
    """
    Log request information.
    
    Decorator to log incoming requests.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.info(
                f"Request: {request.method} {request.path} "
                f"from {request.remote_addr}"
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_timestamp_to_request():
    """
    Add timestamp to request environment.
    
    Used for error responses.
    """
    request.environ['REQUEST_TIMESTAMP'] = datetime.now().isoformat()


def parse_pagination_params(
    default_limit: int = 20,
    max_limit: int = 100
) -> Tuple[int, int]:
    """
    Parse pagination parameters from request.
    
    Args:
        default_limit: Default limit if not specified
        max_limit: Maximum allowed limit
    
    Returns:
        Tuple of (limit, offset)
    """
    limit = request.args.get('limit', default_limit, type=int)
    limit = min(limit, max_limit)  # Cap at max_limit
    
    offset = request.args.get('offset', 0, type=int)
    offset = max(offset, 0)  # Ensure non-negative
    
    return limit, offset


def parse_datetime_param(
    param_name: str,
    required: bool = False
) -> Optional[datetime]:
    """
    Parse datetime parameter from request.
    
    Args:
        param_name: Parameter name
        required: Whether parameter is required
    
    Returns:
        Datetime object or None
    
    Raises:
        ValueError: If parameter is required but missing or invalid
    """
    value = request.args.get(param_name)
    
    if not value:
        if required:
            raise ValueError(f"Parameter '{param_name}' is required")
        return None
    
    try:
        # Support ISO 8601 format with or without 'Z'
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(
            f"Parameter '{param_name}' must be in ISO 8601 format: "
            "YYYY-MM-DDTHH:MM:SSZ"
        )


def get_client_info() -> Dict[str, str]:
    """
    Get client information from request.
    
    Returns:
        Dictionary with client info (IP, user agent, etc.)
    """
    return {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'referer': request.headers.get('Referer', 'Unknown'),
        'method': request.method,
        'path': request.path
    }


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    # Strip whitespace
    value = value.strip()
    
    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    return value


class RequestValidator:
    """
    Request validator class for complex validation scenarios.
    """
    
    def __init__(self, data: dict):
        """
        Initialize validator with request data.
        
        Args:
            data: Request data dictionary
        """
        self.data = data
        self.errors = []
    
    def require_field(self, field: str, field_type: type = None) -> 'RequestValidator':
        """
        Require a field to be present.
        
        Args:
            field: Field name
            field_type: Expected type (optional)
        
        Returns:
            Self for chaining
        """
        if field not in self.data:
            self.errors.append(f"Field '{field}' is required")
        elif field_type and not isinstance(self.data[field], field_type):
            self.errors.append(
                f"Field '{field}' must be of type {field_type.__name__}"
            )
        
        return self
    
    def validate_string(
        self,
        field: str,
        min_length: int = 0,
        max_length: int = None
    ) -> 'RequestValidator':
        """
        Validate string field.
        
        Args:
            field: Field name
            min_length: Minimum length
            max_length: Maximum length
        
        Returns:
            Self for chaining
        """
        if field not in self.data:
            return self
        
        value = self.data[field]
        
        if not isinstance(value, str):
            self.errors.append(f"Field '{field}' must be a string")
            return self
        
        if len(value) < min_length:
            self.errors.append(
                f"Field '{field}' must be at least {min_length} characters"
            )
        
        if max_length and len(value) > max_length:
            self.errors.append(
                f"Field '{field}' must not exceed {max_length} characters"
            )
        
        return self
    
    def validate_integer(
        self,
        field: str,
        min_value: int = None,
        max_value: int = None
    ) -> 'RequestValidator':
        """
        Validate integer field.
        
        Args:
            field: Field name
            min_value: Minimum value
            max_value: Maximum value
        
        Returns:
            Self for chaining
        """
        if field not in self.data:
            return self
        
        value = self.data[field]
        
        if not isinstance(value, int):
            self.errors.append(f"Field '{field}' must be an integer")
            return self
        
        if min_value is not None and value < min_value:
            self.errors.append(f"Field '{field}' must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            self.errors.append(f"Field '{field}' must not exceed {max_value}")
        
        return self
    
    def validate_enum(
        self,
        field: str,
        valid_values: list
    ) -> 'RequestValidator':
        """
        Validate enum field.
        
        Args:
            field: Field name
            valid_values: List of valid values
        
        Returns:
            Self for chaining
        """
        if field not in self.data:
            return self
        
        value = self.data[field]
        
        if value not in valid_values:
            self.errors.append(
                f"Field '{field}' must be one of: {', '.join(map(str, valid_values))}"
            )
        
        return self
    
    def is_valid(self) -> bool:
        """
        Check if validation passed.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.errors) == 0
    
    def get_errors(self) -> list:
        """
        Get validation errors.
        
        Returns:
            List of error messages
        """
        return self.errors
    
    def get_error_message(self) -> str:
        """
        Get formatted error message.
        
        Returns:
            Formatted error message string
        """
        return '; '.join(self.errors)

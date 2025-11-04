"""
Validation decorators for Flask routes.
Provides easy-to-use decorators for request validation.
"""

import logging
from functools import wraps
from typing import Dict, Any, Callable, Optional
from flask import request, jsonify

from src.api.validation.input_validator import validate_request_data, ValidationError
from src.api.app import format_error_response

logger = logging.getLogger(__name__)


def validate_json(validation_rules: Dict[str, Callable]):
    """
    Decorator to validate JSON request body.
    
    Args:
        validation_rules: Dictionary mapping field names to validation functions
    
    Returns:
        Decorator function
    
    Usage:
        @validate_json({
            'name': required_string(min_length=1, max_length=100),
            'age': required_integer(min_value=0, max_value=150),
            'email': lambda v, f, val: v.validate_email(f, val)
        })
        def create_user():
            # Access validated data via request.validated_data
            data = request.validated_data
            return jsonify({'message': 'User created', 'data': data})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if request has JSON content type
            if not request.is_json:
                return jsonify(format_error_response(
                    'INVALID_CONTENT_TYPE',
                    'Content-Type must be application/json',
                    'Request must include JSON data with proper Content-Type header',
                    400
                )[0]), 400
            
            # Get JSON data
            try:
                json_data = request.get_json()
                if json_data is None:
                    return jsonify(format_error_response(
                        'INVALID_JSON',
                        'Invalid JSON data',
                        'Request body must contain valid JSON',
                        400
                    )[0]), 400
            except Exception as e:
                logger.warning(f"JSON parsing error: {e}")
                return jsonify(format_error_response(
                    'JSON_PARSE_ERROR',
                    'Failed to parse JSON',
                    str(e),
                    400
                )[0]), 400
            
            # Validate data
            result = validate_request_data(json_data, validation_rules)
            
            if not result.is_valid:
                # Format validation errors
                error_details = {}
                for error in result.errors:
                    if error.field not in error_details:
                        error_details[error.field] = []
                    error_details[error.field].append({
                        'message': error.message,
                        'code': error.code
                    })
                
                return jsonify(format_error_response(
                    'VALIDATION_ERROR',
                    'Request validation failed',
                    error_details,
                    400
                )[0]), 400
            
            # Store validated data in request object
            request.validated_data = result.sanitized_data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_query_params(validation_rules: Dict[str, Callable]):
    """
    Decorator to validate query parameters.
    
    Args:
        validation_rules: Dictionary mapping parameter names to validation functions
    
    Returns:
        Decorator function
    
    Usage:
        @validate_query_params({
            'page': optional_integer(min_value=1),
            'limit': optional_integer(min_value=1, max_value=100),
            'sort': optional_choice(['name', 'date', 'price'])
        })
        def list_items():
            # Access validated params via request.validated_params
            params = request.validated_params
            return jsonify({'params': params})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get query parameters
            query_data = request.args.to_dict()
            
            # Validate parameters
            result = validate_request_data(query_data, validation_rules)
            
            if not result.is_valid:
                # Format validation errors
                error_details = {}
                for error in result.errors:
                    if error.field not in error_details:
                        error_details[error.field] = []
                    error_details[error.field].append({
                        'message': error.message,
                        'code': error.code
                    })
                
                return jsonify(format_error_response(
                    'VALIDATION_ERROR',
                    'Query parameter validation failed',
                    error_details,
                    400
                )[0]), 400
            
            # Store validated parameters in request object
            request.validated_params = result.sanitized_data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_form_data(validation_rules: Dict[str, Callable]):
    """
    Decorator to validate form data.
    
    Args:
        validation_rules: Dictionary mapping field names to validation functions
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get form data
            form_data = request.form.to_dict()
            
            # Validate data
            result = validate_request_data(form_data, validation_rules)
            
            if not result.is_valid:
                # Format validation errors
                error_details = {}
                for error in result.errors:
                    if error.field not in error_details:
                        error_details[error.field] = []
                    error_details[error.field].append({
                        'message': error.message,
                        'code': error.code
                    })
                
                return jsonify(format_error_response(
                    'VALIDATION_ERROR',
                    'Form validation failed',
                    error_details,
                    400
                )[0]), 400
            
            # Store validated data in request object
            request.validated_form = result.sanitized_data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_path_params(validation_rules: Dict[str, Callable]):
    """
    Decorator to validate path parameters.
    
    Args:
        validation_rules: Dictionary mapping parameter names to validation functions
    
    Returns:
        Decorator function
    
    Usage:
        @validate_path_params({
            'user_id': lambda v, f, val: v.validate_integer(f, val, min_value=1)
        })
        def get_user(user_id):
            # user_id is already validated
            return jsonify({'user_id': user_id})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate path parameters
            result = validate_request_data(kwargs, validation_rules)
            
            if not result.is_valid:
                # Format validation errors
                error_details = {}
                for error in result.errors:
                    if error.field not in error_details:
                        error_details[error.field] = []
                    error_details[error.field].append({
                        'message': error.message,
                        'code': error.code
                    })
                
                return jsonify(format_error_response(
                    'VALIDATION_ERROR',
                    'Path parameter validation failed',
                    error_details,
                    400
                )[0]), 400
            
            # Update kwargs with validated values
            kwargs.update(result.sanitized_data)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def sanitize_output(sanitize_func: Optional[Callable[[Any], Any]] = None):
    """
    Decorator to sanitize response data.
    
    Args:
        sanitize_func: Optional function to sanitize response data
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            if sanitize_func:
                # Apply custom sanitization
                if hasattr(response, 'get_json'):
                    # Flask Response object
                    json_data = response.get_json()
                    if json_data:
                        sanitized_data = sanitize_func(json_data)
                        response.set_data(jsonify(sanitized_data).get_data())
                elif isinstance(response, dict):
                    # Dictionary response
                    response = sanitize_func(response)
            
            return response
        
        return decorated_function
    return decorator


# Common validation rule combinations
def api_key_creation_rules():
    """Validation rules for API key creation."""
    from src.api.validation import required_string, optional_string, optional_integer, required_choice
    
    return {
        'name': required_string(min_length=1, max_length=100),
        'role': required_choice(['user', 'admin', 'readonly']),
        'expires_in_days': optional_integer(min_value=1, max_value=3650),  # Max 10 years
        'description': optional_string(max_length=500)
    }


def chat_query_rules():
    """Validation rules for chat queries."""
    from src.api.validation import required_string, optional_string
    
    return {
        'question': required_string(min_length=1, max_length=2000),
        'session_id': optional_string(min_length=1, max_length=100)
    }


def prediction_query_rules():
    """Validation rules for prediction queries."""
    from src.api.validation import optional_integer, optional_choice
    
    return {
        'limit': optional_integer(min_value=1, max_value=100),
        'sort': optional_choice(['predicted_change', 'confidence', 'symbol']),
        'order': optional_choice(['asc', 'desc'])
    }


def admin_collection_rules():
    """Validation rules for admin collection triggers."""
    import re
    from src.api.validation import optional_string, required_choice
    
    return {
        'mode': required_choice(['manual', 'scheduled']),
        'start_date': optional_string(pattern=re.compile(r'^\d{4}-\d{2}-\d{2}$')),
        'end_date': optional_string(pattern=re.compile(r'^\d{4}-\d{2}-\d{2}$'))
    }
"""
API key authentication middleware.
Validates API keys for protected endpoints using the API key manager.
"""

import logging
from flask import request, jsonify, g
from functools import wraps
from typing import Optional, Callable

from src.api.auth.api_key_manager import ApiKeyManager, ApiKeyRole

logger = logging.getLogger(__name__)


def get_api_key_from_request() -> Optional[str]:
    """
    Extract API key from request.
    
    Checks in order:
    1. Authorization header (Bearer token)
    2. X-API-Key header
    3. Query parameter 'api_key'
    
    Returns:
        API key string or None
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Check X-API-Key header
    api_key_header = request.headers.get('X-API-Key')
    if api_key_header:
        return api_key_header
    
    # Check query parameter
    api_key_param = request.args.get('api_key')
    if api_key_param:
        return api_key_param
    
    return None


def get_api_key_manager() -> Optional[ApiKeyManager]:
    """
    Get API key manager from Flask application context.
    
    Returns:
        ApiKeyManager instance or None if not available
    """
    return getattr(g, 'api_key_manager', None)


def require_api_key():
    """
    Middleware to require valid API key.
    
    Returns:
        None if valid, error response if invalid
    """
    api_key = get_api_key_from_request()
    
    if not api_key:
        logger.warning(f"Missing API key from {request.remote_addr}")
        return jsonify({
            'error': {
                'code': 'MISSING_API_KEY',
                'message': 'API key required',
                'details': 'Provide API key in Authorization header, X-API-Key header, or api_key query parameter'
            }
        }), 401
    
    # Get API key manager
    api_key_manager = get_api_key_manager()
    if not api_key_manager:
        logger.error("API key manager not available")
        return jsonify({
            'error': {
                'code': 'AUTHENTICATION_ERROR',
                'message': 'Authentication service unavailable',
                'details': 'Please try again later'
            }
        }), 503
    
    # Validate API key
    key_info = api_key_manager.validate_api_key(api_key)
    
    if not key_info:
        logger.warning(f"Invalid API key from {request.remote_addr}")
        return jsonify({
            'error': {
                'code': 'INVALID_API_KEY',
                'message': 'Invalid API key',
                'details': 'The provided API key is not valid'
            }
        }), 401
    
    # Store key info in request context
    request.api_key_info = key_info
    
    logger.debug(f"Authenticated request with key: {key_info.key_id} ({key_info.name})")
    
    return None


def require_admin():
    """
    Middleware to require admin role.
    
    Returns:
        None if admin, error response if not
    """
    # First check API key
    api_key_response = require_api_key()
    if api_key_response:
        return api_key_response
    
    # Check if user has admin role
    key_info = getattr(request, 'api_key_info', None)
    
    if not key_info or key_info.role != ApiKeyRole.ADMIN:
        logger.warning(f"Non-admin access attempt from {request.remote_addr} with key: {key_info.key_id if key_info else 'None'}")
        return jsonify({
            'error': {
                'code': 'INSUFFICIENT_PERMISSIONS',
                'message': 'Admin access required',
                'details': 'This endpoint requires admin privileges'
            }
        }), 403
    
    return None


def require_role(required_role: ApiKeyRole):
    """
    Middleware to require specific role.
    
    Args:
        required_role: Required role for access
    
    Returns:
        None if authorized, error response if not
    """
    # First check API key
    api_key_response = require_api_key()
    if api_key_response:
        return api_key_response
    
    # Check if user has required role
    key_info = getattr(request, 'api_key_info', None)
    
    if not key_info:
        return jsonify({
            'error': {
                'code': 'AUTHENTICATION_ERROR',
                'message': 'Authentication required',
                'details': 'Valid API key required'
            }
        }), 401
    
    # Admin role can access everything
    if key_info.role == ApiKeyRole.ADMIN:
        return None
    
    # Check specific role
    if key_info.role != required_role:
        logger.warning(f"Insufficient permissions from {request.remote_addr} with key: {key_info.key_id} (has {key_info.role.value}, needs {required_role.value})")
        return jsonify({
            'error': {
                'code': 'INSUFFICIENT_PERMISSIONS',
                'message': f'{required_role.value.title()} access required',
                'details': f'This endpoint requires {required_role.value} privileges'
            }
        }), 403
    
    return None


def api_key_required(f: Callable) -> Callable:
    """
    Decorator to require API key for endpoint.
    
    Args:
        f: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = require_api_key()
        if response:
            return response
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator to require admin role for endpoint.
    
    Args:
        f: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = require_admin()
        if response:
            return response
        return f(*args, **kwargs)
    
    return decorated_function


def role_required(required_role: ApiKeyRole):
    """
    Decorator factory to require specific role for endpoint.
    
    Args:
        required_role: Required role for access
    
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = require_role(required_role)
            if response:
                return response
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def readonly_allowed(f: Callable) -> Callable:
    """
    Decorator to allow readonly, user, or admin access.
    
    Args:
        f: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = require_api_key()
        if response:
            return response
        return f(*args, **kwargs)
    
    return decorated_function

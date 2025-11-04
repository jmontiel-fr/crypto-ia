"""
CSRF protection middleware.
Provides basic CSRF token generation and validation.
"""

import secrets
import logging
from flask import session, request, jsonify
from functools import wraps

logger = logging.getLogger(__name__)


def generate_csrf_token():
    """
    Generate a CSRF token and store it in the session.
    
    Returns:
        CSRF token string
    """
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token(token):
    """
    Validate a CSRF token against the session token.
    
    Args:
        token: Token to validate
    
    Returns:
        True if valid, False otherwise
    """
    session_token = session.get('_csrf_token')
    
    if not session_token:
        logger.warning("No CSRF token in session")
        return False
    
    if not token:
        logger.warning("No CSRF token provided in request")
        return False
    
    return secrets.compare_digest(session_token, token)


def csrf_protect(f):
    """
    Decorator to protect routes with CSRF validation.
    
    Args:
        f: Function to decorate
    
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip CSRF for API endpoints (they use API key auth)
        if request.path.startswith('/api/'):
            return f(*args, **kwargs)
        
        # Skip CSRF for GET, HEAD, OPTIONS, TRACE
        if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            return f(*args, **kwargs)
        
        # Get token from header or form data
        token = request.headers.get('X-CSRF-Token')
        
        if not token and request.is_json:
            data = request.get_json(silent=True)
            if data:
                token = data.get('csrf_token')
        
        if not token:
            token = request.form.get('csrf_token')
        
        # Validate token
        if not validate_csrf_token(token):
            logger.warning(
                f"CSRF validation failed for {request.method} {request.path} "
                f"from {request.remote_addr}"
            )
            return jsonify({
                'error': {
                    'code': 'CSRF_VALIDATION_FAILED',
                    'message': 'CSRF token validation failed',
                    'details': 'Invalid or missing CSRF token'
                }
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_csrf_token():
    """
    Middleware to require valid CSRF token for non-API routes.
    
    Returns:
        None if valid, error response if invalid
    """
    # Skip CSRF for API endpoints (they use API key auth)
    if request.path.startswith('/api/'):
        return None
    
    # Skip CSRF for GET, HEAD, OPTIONS requests
    if request.method in ['GET', 'HEAD', 'OPTIONS']:
        return None
    
    # Get CSRF token from various sources
    csrf_token = None
    
    # Check X-CSRF-Token header
    csrf_token = request.headers.get('X-CSRF-Token')
    
    # Check form data
    if not csrf_token:
        csrf_token = request.form.get('csrf_token')
    
    # Check JSON data
    if not csrf_token and request.is_json:
        json_data = request.get_json(silent=True)
        if json_data:
            csrf_token = json_data.get('csrf_token')
    
    if not csrf_token:
        logger.warning(f"Missing CSRF token from {request.remote_addr}")
        return jsonify({
            'error': {
                'code': 'MISSING_CSRF_TOKEN',
                'message': 'CSRF token required',
                'details': 'Include CSRF token in X-CSRF-Token header or form data'
            }
        }), 403
    
    if not validate_csrf_token(csrf_token):
        logger.warning(f"Invalid CSRF token from {request.remote_addr}")
        return jsonify({
            'error': {
                'code': 'INVALID_CSRF_TOKEN',
                'message': 'Invalid CSRF token',
                'details': 'CSRF token is invalid or expired'
            }
        }), 403
    
    return None


def get_csrf_token():
    """
    Get the current CSRF token (generates one if needed).
    
    Returns:
        CSRF token string
    """
    return generate_csrf_token()

"""
Flask application factory and configuration.
Creates and configures the Flask app with all middleware and blueprints.
"""

import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from typing import Dict, Any

from src.config.config_loader import Config

logger = logging.getLogger(__name__)


def create_app(config: Config) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config: Application configuration
    
    Returns:
        Configured Flask application
    """
    import os
    
    # Get the directory where app.py is located
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(
        __name__,
        template_folder=os.path.join(app_dir, 'templates'),
        static_folder=os.path.join(app_dir, 'static')
    )
    
    # Configure Flask
    app.config['SECRET_KEY'] = config.secret_key
    app.config['JSON_SORT_KEYS'] = False
    
    # Session configuration
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Configure CORS
    allowed_origins = config.allowed_origins.split(',') if config.allowed_origins != '*' else '*'
    CORS(app, origins=allowed_origins, supports_credentials=True)
    
    logger.info(f"CORS configured with origins: {allowed_origins}")
    
    # Register middleware
    register_middleware(app, config)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Flask application created and configured")
    
    return app


def register_middleware(app: Flask, config: Config) -> None:
    """
    Register middleware for the Flask application.
    
    Args:
        app: Flask application
        config: Application configuration
    """
    # Audit logging middleware (must be first to capture all requests)
    from src.api.middleware.audit_middleware import AuditMiddleware
    audit_middleware = AuditMiddleware(app)
    
    # Request logging middleware
    @app.before_request
    def log_request():
        """Log incoming requests."""
        logger.info(
            f"{request.method} {request.path} "
            f"from {request.remote_addr} "
            f"- User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
        )
    
    @app.after_request
    def log_response(response):
        """Log outgoing responses."""
        logger.info(
            f"{request.method} {request.path} "
            f"- Status: {response.status_code}"
        )
        return response
    
    # API key authentication middleware (if required)
    if config.api_key_required:
        from src.api.middleware.auth import require_api_key
        
        @app.before_request
        def check_api_key():
            """Check API key for protected endpoints."""
            # Skip authentication for health check and public endpoints
            if request.path in ['/health', '/']:
                return None
            
            return require_api_key()
    
    # Rate limiting middleware
    from src.api.middleware.rate_limiter import RateLimiter
    
    rate_limiter = RateLimiter(
        requests_per_minute=config.rate_limit_per_minute
    )
    
    @app.before_request
    def check_rate_limit():
        """Check rate limit for requests."""
        # Skip rate limiting for health check
        if request.path == '/health':
            return None
        
        return rate_limiter.check_rate_limit(request)
    
    logger.info("Middleware registered")


def register_blueprints(app: Flask) -> None:
    """
    Register API blueprints.
    
    Args:
        app: Flask application
    """
    from src.api.routes.predictions import predictions_bp
    from src.api.routes.market import market_bp
    from src.api.routes.chat import chat_bp
    from src.api.routes.admin import admin_bp
    from src.api.routes.health import health_bp
    from src.api.routes.api_keys import api_keys_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(predictions_bp, url_prefix='/api/predictions')
    app.register_blueprint(market_bp, url_prefix='/api/market')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(api_keys_bp, url_prefix='/api/admin/keys')
    
    logger.info("Blueprints registered")


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the Flask application.
    
    Args:
        app: Flask application
    """
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Invalid request',
                'details': str(error),
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors."""
        return jsonify({
            'error': {
                'code': 'UNAUTHORIZED',
                'message': 'Authentication required',
                'details': 'Valid API key required',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors."""
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'Access denied',
                'details': 'Insufficient permissions',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Resource not found',
                'details': f'The requested URL {request.path} was not found',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Rate Limit Exceeded errors."""
        return jsonify({
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Too many requests',
                'details': 'Rate limit exceeded. Please try again later.',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An internal error occurred',
                'details': 'Please try again later',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions."""
        # Log the error
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # Return generic error response
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'details': str(error) if app.debug else 'Please contact support',
                'timestamp': request.environ.get('REQUEST_TIMESTAMP')
            }
        }), 500
    
    logger.info("Error handlers registered")


def format_error_response(
    code: str,
    message: str,
    details: str = None,
    status_code: int = 400
) -> tuple[Dict[str, Any], int]:
    """
    Format standardized error response.
    
    Args:
        code: Error code
        message: Error message
        details: Additional details (optional)
        status_code: HTTP status code
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    from datetime import datetime
    
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
    message: str = None
) -> Dict[str, Any]:
    """
    Format standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
    
    Returns:
        Response dictionary
    """
    from datetime import datetime
    
    response = {
        'success': True,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    
    if message:
        response['message'] = message
    
    return response

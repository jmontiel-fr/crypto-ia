"""
Main entry point for Flask API server.
Initializes and runs the Flask application.
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.config_loader import load_config
from src.api.app import create_app
from src.utils.logger import setup_logging
from src.data.database import get_session_factory
from src.api.auth.api_key_manager import ApiKeyManager

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for Flask API server.
    """
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        logger.info("Starting Crypto Market Analysis API")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"API Host: {config.api_host}:{config.api_port}")
        
        # Create Flask app
        app = create_app(config)
        
        # Store config in app context
        app.config['APP_CONFIG'] = config
        
        # Initialize database session factory
        session_factory = get_session_factory(config.database_url)
        
        # Initialize API key manager and store in app context
        @app.before_request
        def setup_api_key_manager():
            """Set up API key manager for each request."""
            from flask import g
            if not hasattr(g, 'api_key_manager'):
                session = session_factory()
                g.api_key_manager = ApiKeyManager(session)
                
        @app.teardown_appcontext
        def close_db_session(error):
            """Close database session after request."""
            from flask import g
            if hasattr(g, 'api_key_manager'):
                g.api_key_manager.db_session.close()
        
        # Run Flask app
        app.run(
            host=config.api_host,
            port=config.api_port,
            debug=(config.environment == 'local'),
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start API server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

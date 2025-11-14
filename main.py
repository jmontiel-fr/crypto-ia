#!/usr/bin/env python3
"""
Main Entry Point for Crypto Market Analysis SaaS
Initializes all components and provides unified startup sequence.
"""

import sys
import os
import logging
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_loader import load_config, Config
from src.data.database import create_tables, get_session, test_connection
from src.utils.logger import setup_logging
from src.utils.audit_logger import AuditLogger, AuditEventType, AuditSeverity

# Global variables for graceful shutdown
shutdown_requested = False
running_services = []

logger = logging.getLogger(__name__)


class ApplicationStartup:
    """
    Handles the complete application startup sequence.
    """
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.startup_errors = []
        self.startup_warnings = []
        
    def initialize(self) -> bool:
        """
        Initialize the complete application.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Step 1: Setup logging
            self._setup_logging()
            logger.info("Starting Crypto Market Analysis SaaS initialization...")
            
            # Step 2: Load configuration
            if not self._load_configuration():
                return False
            
            # Step 3: Test database connection
            if not self._test_database():
                return False
            
            # Step 4: Initialize database schema
            if not self._initialize_database():
                return False
            
            # Step 5: Validate external services
            if not self._validate_external_services():
                return False
            
            # Step 6: Initialize audit logging
            if not self._initialize_audit_logging():
                return False
            
            # Step 7: Validate required directories
            if not self._validate_directories():
                return False
            
            # Step 8: Log startup completion
            self._log_startup_completion()
            
            return True
            
        except Exception as e:
            logger.error(f"Critical error during initialization: {e}", exc_info=True)
            return False
    
    def _setup_logging(self) -> None:
        """Setup application logging."""
        try:
            # Get environment path from environment variable if available
            env_path = os.getenv('ENVIRONMENT_PATH')
            log_level = os.getenv('LOG_LEVEL', 'INFO')
            log_file = os.getenv('LOG_FILE', 'logs/crypto_saas.log')
            
            setup_logging(
                log_level=log_level,
                log_file=log_file,
                base_path=env_path
            )
            logger.info("Logging system initialized")
        except Exception as e:
            print(f"Failed to setup logging: {e}")
            raise
    
    def _load_configuration(self) -> bool:
        """Load and validate configuration."""
        try:
            self.config = load_config()
            logger.info(f"Configuration loaded successfully (Environment: {self.config.environment})")
            return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.startup_errors.append(f"Configuration error: {e}")
            return False
    
    def _test_database(self) -> bool:
        """Test database connectivity."""
        try:
            if test_connection():
                logger.info("Database connection test successful")
                return True
            else:
                logger.error("Database connection test failed")
                self.startup_errors.append("Database connection failed")
                return False
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            self.startup_errors.append(f"Database error: {e}")
            return False
    
    def _initialize_database(self) -> bool:
        """Initialize database schema if needed."""
        try:
            create_tables()
            logger.info("Database schema initialized")
            return True
        except Exception as e:
            logger.error(f"Database schema initialization failed: {e}")
            self.startup_errors.append(f"Database schema error: {e}")
            return False
    
    def _validate_external_services(self) -> bool:
        """Validate external service configurations."""
        validation_passed = True
        
        # Check OpenAI API key
        if not self.config.openai_api_key or self.config.openai_api_key.startswith('your-'):
            logger.warning("OpenAI API key not configured - chat functionality will be limited")
            self.startup_warnings.append("OpenAI API key not configured")
        else:
            logger.info("OpenAI API key configured")
        
        # Check Binance API credentials
        if not self.config.binance_api_key or self.config.binance_api_key.startswith('your-'):
            logger.warning("Binance API credentials not configured - data collection will be limited")
            self.startup_warnings.append("Binance API credentials not configured")
        else:
            logger.info("Binance API credentials configured")
        
        # Check SMS configuration
        if self.config.alert_enabled:
            if not self.config.sms_phone_number or self.config.sms_phone_number.startswith('+1234'):
                logger.warning("SMS phone number not configured - alerts will not work")
                self.startup_warnings.append("SMS phone number not configured")
            else:
                logger.info("SMS alert configuration validated")
        
        return validation_passed
    
    def _initialize_audit_logging(self) -> bool:
        """Initialize audit logging system."""
        try:
            session = get_session()
            audit_logger = AuditLogger(session)
            
            # Log application startup
            audit_logger.log_security_event(
                event_type=AuditEventType.SYSTEM_ERROR,  # Using available event type
                message="Application startup initiated",
                severity=AuditSeverity.LOW,
                additional_data={
                    "environment": self.config.environment,
                    "startup_warnings": self.startup_warnings
                }
            )
            
            session.close()
            logger.info("Audit logging system initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audit logging: {e}")
            self.startup_warnings.append(f"Audit logging error: {e}")
            return True  # Non-critical error
    
    def _validate_directories(self) -> bool:
        """Validate and create required directories."""
        try:
            # Determine base path from environment configuration
            base_path = Path(self.config.environment_path) if self.config.environment_path else Path.cwd()
            
            directories = [
                "logs",
                "certs",
                "models",
                "tmp"
            ]
            
            for directory in directories:
                dir_path = base_path / directory
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")
                else:
                    logger.debug(f"Directory exists: {dir_path}")
            
            logger.info(f"Directory structure validated at: {base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to validate directories: {e}")
            self.startup_warnings.append(f"Directory validation error: {e}")
            return True  # Non-critical error
    
    def _log_startup_completion(self) -> None:
        """Log startup completion with summary."""
        logger.info("=" * 60)
        logger.info("Crypto Market Analysis SaaS - Startup Complete")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.config.environment}")
        logger.info(f"Deployment Path: {self.config.environment_path or 'Current directory'}")
        logger.info(f"Database URL: {self.config.database_url.split('@')[1] if '@' in self.config.database_url else 'configured'}")
        logger.info(f"Web UI: {self.config.web_ui_protocol}://{self.config.web_ui_host}:{self.config.web_ui_port}")
        logger.info(f"API Port: {self.config.api_port}")
        logger.info(f"Streamlit Port: {self.config.streamlit_port}")
        
        if self.startup_warnings:
            logger.warning("Startup warnings:")
            for warning in self.startup_warnings:
                logger.warning(f"  - {warning}")
        
        logger.info("=" * 60)
        logger.info("Application ready for service startup")
        logger.info("=" * 60)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def start_flask_api(config: Config):
    """Start the Flask API server."""
    try:
        logger.info("Starting Flask API server...")
        from src.api.main import main as api_main
        api_main()
    except Exception as e:
        logger.error(f"Failed to start Flask API: {e}", exc_info=True)
        raise


def start_streamlit_dashboard():
    """Start the Streamlit dashboard."""
    try:
        logger.info("Starting Streamlit dashboard...")
        import subprocess
        import sys
        
        # Start Streamlit as subprocess
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.port=8501",
            "--server.address=127.0.0.1",
            "--server.headless=true"
        ])
        
        running_services.append(("streamlit", process))
        logger.info("Streamlit dashboard started")
        
    except Exception as e:
        logger.error(f"Failed to start Streamlit dashboard: {e}", exc_info=True)
        raise


def start_background_services(config: Config):
    """Start background services (collectors, alerts, etc.)."""
    try:
        # Start data collector scheduler
        if config.collection_schedule:
            logger.info("Starting data collector scheduler...")
            from src.collectors.scheduler import start_collector_scheduler
            start_collector_scheduler()
        
        # Start alert system
        if config.alert_enabled:
            logger.info("Starting alert system...")
            from src.alerts.alert_scheduler import start_alert_scheduler
            start_alert_scheduler()
        
        # Start log retention scheduler
        logger.info("Starting log retention scheduler...")
        from src.utils.retention_scheduler import start_retention_scheduler
        start_retention_scheduler()
        
        logger.info("Background services started")
        
    except Exception as e:
        logger.error(f"Failed to start background services: {e}", exc_info=True)
        # Don't raise - background services are not critical for basic functionality


def health_check() -> Dict[str, Any]:
    """Perform application health check."""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {},
        "warnings": []
    }
    
    try:
        # Check database
        if test_connection():
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
        
        # Check configuration
        config = load_config()
        health_status["services"]["configuration"] = "healthy"
        
        # Check external services
        if not config.openai_api_key or config.openai_api_key.startswith('your-'):
            health_status["warnings"].append("OpenAI API key not configured")
        
        if not config.binance_api_key or config.binance_api_key.startswith('your-'):
            health_status["warnings"].append("Binance API credentials not configured")
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


def main():
    """Main entry point."""
    print("Crypto Market Analysis SaaS - Starting...")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize application
    startup = ApplicationStartup()
    if not startup.initialize():
        print("Application initialization failed. Check logs for details.")
        sys.exit(1)
    
    # Get configuration
    config = startup.config
    
    try:
        # Determine startup mode based on command line arguments
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
        else:
            mode = "api"  # Default mode
        
        if mode == "api":
            # Start Flask API only
            start_flask_api(config)
            
        elif mode == "dashboard":
            # Start Streamlit dashboard only
            start_streamlit_dashboard()
            
            # Keep main process alive
            while not shutdown_requested:
                time.sleep(1)
                
        elif mode == "services":
            # Start background services only
            start_background_services(config)
            
            # Keep main process alive
            while not shutdown_requested:
                time.sleep(1)
                
        elif mode == "all":
            # Start all services
            start_background_services(config)
            start_streamlit_dashboard()
            
            # Start Flask API (this will block)
            start_flask_api(config)
            
        elif mode == "health":
            # Perform health check and exit
            health = health_check()
            print(f"Health Status: {health['status']}")
            if health.get('warnings'):
                print("Warnings:")
                for warning in health['warnings']:
                    print(f"  - {warning}")
            sys.exit(0 if health['status'] in ['healthy', 'degraded'] else 1)
            
        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: api, dashboard, services, all, health")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Performing cleanup...")
        for service_name, process in running_services:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {service_name}")
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
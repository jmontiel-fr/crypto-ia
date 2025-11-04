#!/usr/bin/env python
"""
Database initialization script.
Creates all tables and performs initial setup.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_loader import load_config
from src.utils.logger import setup_logging
from src.data.database import init_db, create_tables, check_connection

# Import all models to ensure they're registered with Base
from src.data.models import (
    Cryptocurrency,
    PriceHistory,
    Prediction,
    ChatHistory,
    QueryAuditLog,
    MarketTendency,
)

logger = logging.getLogger(__name__)


def main():
    """Initialize database and create tables."""
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(config)
        
        logger.info("Starting database initialization...")
        
        # Initialize database connection
        init_db(config)
        
        # Check connection
        if not check_connection():
            logger.error("Database connection check failed")
            sys.exit(1)
        
        # Create all tables
        logger.info("Creating database tables...")
        create_tables()
        
        logger.info("Database initialization completed successfully!")
        logger.info("All tables have been created.")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

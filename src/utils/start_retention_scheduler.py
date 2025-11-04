#!/usr/bin/env python3
"""
Start the log retention scheduler.
This script can be run as a standalone service or integrated into the main application.
"""

import logging
import signal
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.retention_scheduler import start_retention_scheduler, stop_retention_scheduler
from src.config.config_loader import load_config

logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down retention scheduler...")
    stop_retention_scheduler()
    sys.exit(0)


def main():
    """Main entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting log retention scheduler service")
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the scheduler
        start_retention_scheduler()
        logger.info("Log retention scheduler started successfully")
        
        # Keep the process running
        logger.info("Retention scheduler is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        stop_retention_scheduler()
    except Exception as e:
        logger.error(f"Error starting retention scheduler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
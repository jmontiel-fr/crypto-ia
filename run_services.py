#!/usr/bin/env python3
"""
Background Services Entry Point
Starts data collectors, alert system, and other background services.
"""

import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import ApplicationStartup, setup_signal_handlers, shutdown_requested

def main():
    """Start background services."""
    print("Starting Crypto Market Analysis SaaS - Background Services")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize application
    startup = ApplicationStartup()
    if not startup.initialize():
        print("Application initialization failed. Check logs for details.")
        sys.exit(1)
    
    config = startup.config
    
    try:
        # Start data collector scheduler
        if config.collection_schedule:
            print("Starting data collector scheduler...")
            from src.collectors.scheduler import start_collector_scheduler
            start_collector_scheduler()
        
        # Start alert system
        if config.alert_enabled:
            print("Starting alert system...")
            from src.alerts.alert_scheduler import start_alert_scheduler
            start_alert_scheduler()
        
        # Start log retention scheduler
        print("Starting log retention scheduler...")
        from src.utils.retention_scheduler import start_retention_scheduler
        start_retention_scheduler()
        
        print("Background services started successfully")
        print("Press Ctrl+C to stop services")
        
        # Keep services running
        while not shutdown_requested:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nBackground services stopped by user")
    except Exception as e:
        print(f"Background services error: {e}")
        sys.exit(1)
    finally:
        print("Stopping background services...")
        try:
            from src.collectors.scheduler import stop_collector_scheduler
            from src.alerts.alert_scheduler import stop_alert_scheduler
            from src.utils.retention_scheduler import stop_retention_scheduler
            
            stop_collector_scheduler()
            stop_alert_scheduler()
            stop_retention_scheduler()
        except:
            pass

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Unified Startup Script for Crypto Market Analysis SaaS
Handles different deployment scenarios and service combinations.
"""

import sys
import os
import argparse
import time
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import ApplicationStartup, setup_signal_handlers, shutdown_requested

def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Crypto Market Analysis SaaS Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py --api                    # Start API server only
  python start.py --dashboard              # Start dashboard only
  python start.py --services               # Start background services only
  python start.py --all                    # Start all components
  python start.py --health                 # Perform health check
  python start.py --api --services         # Start API and background services
  python start.py --development            # Development mode (all services)
  python start.py --production             # Production mode (optimized)
        """
    )
    
    # Service selection
    parser.add_argument('--api', action='store_true', 
                       help='Start Flask API server')
    parser.add_argument('--dashboard', action='store_true', 
                       help='Start Streamlit dashboard')
    parser.add_argument('--services', action='store_true', 
                       help='Start background services (collectors, alerts)')
    parser.add_argument('--all', action='store_true', 
                       help='Start all components')
    
    # Predefined modes
    parser.add_argument('--development', action='store_true',
                       help='Development mode (all services, debug logging)')
    parser.add_argument('--production', action='store_true',
                       help='Production mode (optimized settings)')
    
    # Utility commands
    parser.add_argument('--health', action='store_true',
                       help='Perform health check and exit')
    parser.add_argument('--validate', action='store_true',
                       help='Validate configuration and exit')
    
    # Options
    parser.add_argument('--port', type=int, default=5000,
                       help='API server port (default: 5000)')
    parser.add_argument('--dashboard-port', type=int, default=8501,
                       help='Dashboard port (default: 8501)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='API server host (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--no-init', action='store_true',
                       help='Skip application initialization')
    
    return parser

def validate_configuration():
    """Validate configuration and report issues."""
    print("Validating configuration...")
    
    startup = ApplicationStartup()
    if startup.initialize():
        print("✓ Configuration validation passed")
        
        if startup.startup_warnings:
            print("\nWarnings:")
            for warning in startup.startup_warnings:
                print(f"  ⚠ {warning}")
        
        return True
    else:
        print("✗ Configuration validation failed")
        
        if startup.startup_errors:
            print("\nErrors:")
            for error in startup.startup_errors:
                print(f"  ✗ {error}")
        
        return False

def start_api_server(host='0.0.0.0', port=5000, debug=False):
    """Start the Flask API server."""
    print(f"Starting API server on {host}:{port}")
    
    # Set environment variables for Flask
    os.environ['FLASK_HOST'] = host
    os.environ['FLASK_PORT'] = str(port)
    if debug:
        os.environ['FLASK_DEBUG'] = '1'
    
    from src.api.main import main as api_main
    api_main()

def start_dashboard(port=8501):
    """Start the Streamlit dashboard."""
    print(f"Starting dashboard on http://localhost:{port}")
    
    process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "dashboard.py",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.headless=true"
    ])
    
    return process

def start_background_services():
    """Start background services."""
    print("Starting background services...")
    
    try:
        # Import and start schedulers
        from src.collectors.scheduler import start_collector_scheduler
        from src.alerts.alert_scheduler import start_alert_scheduler
        from src.utils.retention_scheduler import start_retention_scheduler
        
        start_collector_scheduler()
        start_alert_scheduler()
        start_retention_scheduler()
        
        print("✓ Background services started")
        return True
    except Exception as e:
        print(f"✗ Failed to start background services: {e}")
        return False

def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle utility commands first
    if args.health:
        from main import health_check
        health = health_check()
        print(f"Health Status: {health['status']}")
        sys.exit(0 if health['status'] in ['healthy', 'degraded'] else 1)
    
    if args.validate:
        success = validate_configuration()
        sys.exit(0 if success else 1)
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize application unless skipped
    if not args.no_init:
        startup = ApplicationStartup()
        if not startup.initialize():
            print("Application initialization failed. Use --validate to check configuration.")
            sys.exit(1)
        config = startup.config
    
    # Determine what services to start
    start_api = args.api or args.all or args.development or args.production
    start_dash = args.dashboard or args.all or args.development
    start_bg = args.services or args.all or args.development or args.production
    
    # Default to API if nothing specified
    if not (start_api or start_dash or start_bg):
        start_api = True
    
    # Set debug mode
    debug_mode = args.debug or args.development
    
    processes = []
    
    try:
        # Start background services first
        if start_bg:
            if start_background_services():
                print("✓ Background services running")
            else:
                print("⚠ Background services failed to start")
        
        # Start dashboard
        if start_dash:
            dashboard_process = start_dashboard(args.dashboard_port)
            processes.append(('dashboard', dashboard_process))
            print("✓ Dashboard started")
        
        # Start API server (this will block if it's the only service)
        if start_api:
            if start_dash or start_bg:
                # Run API in background if other services are running
                print("Starting API server in background mode...")
                # For now, we'll run API in foreground as it's the main service
                start_api_server(args.host, args.port, debug_mode)
            else:
                # Run API in foreground
                start_api_server(args.host, args.port, debug_mode)
        else:
            # Keep main process alive if only background services
            print("Services running. Press Ctrl+C to stop.")
            while not shutdown_requested:
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
    finally:
        # Cleanup processes
        print("Stopping services...")
        for service_name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✓ Stopped {service_name}")
            except:
                try:
                    process.kill()
                    print(f"✓ Killed {service_name}")
                except:
                    pass
        
        # Stop background services
        try:
            from src.collectors.scheduler import stop_collector_scheduler
            from src.alerts.alert_scheduler import stop_alert_scheduler
            from src.utils.retention_scheduler import stop_retention_scheduler
            
            stop_collector_scheduler()
            stop_alert_scheduler()
            stop_retention_scheduler()
            print("✓ Background services stopped")
        except:
            pass
        
        print("Shutdown complete")

if __name__ == "__main__":
    main()
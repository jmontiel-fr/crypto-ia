#!/usr/bin/env python3
"""
Flask API Entry Point
Starts only the Flask REST API server.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import ApplicationStartup, setup_signal_handlers
from src.api.main import main as api_main

def main():
    """Start Flask API server."""
    print("Starting Crypto Market Analysis SaaS - API Server")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize application
    startup = ApplicationStartup()
    if not startup.initialize():
        print("Application initialization failed. Check logs for details.")
        sys.exit(1)
    
    # Start Flask API
    try:
        api_main()
    except KeyboardInterrupt:
        print("\nAPI server stopped by user")
    except Exception as e:
        print(f"API server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
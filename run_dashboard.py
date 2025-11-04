#!/usr/bin/env python3
"""
Streamlit Dashboard Entry Point
Starts only the Streamlit dashboard.
"""

import sys
import subprocess
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import ApplicationStartup, setup_signal_handlers, shutdown_requested

def main():
    """Start Streamlit dashboard."""
    print("Starting Crypto Market Analysis SaaS - Dashboard")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize application
    startup = ApplicationStartup()
    if not startup.initialize():
        print("Application initialization failed. Check logs for details.")
        sys.exit(1)
    
    # Start Streamlit dashboard
    try:
        print("Starting Streamlit dashboard on http://localhost:8501")
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.port=8501",
            "--server.address=127.0.0.1"
        ])
        
        # Keep process alive
        while not shutdown_requested:
            if process.poll() is not None:
                print("Streamlit process ended")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
    except Exception as e:
        print(f"Dashboard error: {e}")
        sys.exit(1)
    finally:
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

if __name__ == "__main__":
    main()
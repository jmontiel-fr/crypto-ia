#!/usr/bin/env python3
"""
Health Check Entry Point
Performs comprehensive system health check and reports status.
"""

import sys
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import health_check

def main():
    """Perform health check and report status."""
    try:
        health = health_check()
        
        # Print human-readable status
        print(f"System Status: {health['status'].upper()}")
        print("-" * 40)
        
        # Service status
        if 'services' in health:
            print("Services:")
            for service, status in health['services'].items():
                status_icon = "✓" if status == "healthy" else "✗"
                print(f"  {status_icon} {service}: {status}")
        
        # Warnings
        if health.get('warnings'):
            print("\nWarnings:")
            for warning in health['warnings']:
                print(f"  ⚠ {warning}")
        
        # Errors
        if health.get('error'):
            print(f"\nError: {health['error']}")
        
        # JSON output for scripts
        if len(sys.argv) > 1 and sys.argv[1] == "--json":
            print("\nJSON Output:")
            print(json.dumps(health, indent=2))
        
        # Exit code based on health status
        if health['status'] == 'healthy':
            sys.exit(0)
        elif health['status'] == 'degraded':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
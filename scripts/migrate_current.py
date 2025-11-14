#!/usr/bin/env python3
"""
Check current database migration version
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def show_current_version():
    """Show current database migration version"""
    
    print("=" * 70)
    print("Database Migration - Current Version")
    print("=" * 70)
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("\n❌ ERROR: DATABASE_URL environment variable is not set")
        print("\nPlease set DATABASE_URL before checking version:")
        print("  export DATABASE_URL=postgresql://user:pass@host:port/dbname")
        sys.exit(1)
    
    print(f"\nDatabase: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL', '') else 'unknown'}")
    print("\nCurrent migration version:")
    print("-" * 70)
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Show current version
        command.current(alembic_cfg, verbose=True)
        
        print("-" * 70)
        print("\nTo upgrade to latest:")
        print("  python scripts/migrate_upgrade.py")
        print("\nTo downgrade:")
        print("  python scripts/migrate_downgrade.py [revision]")
        
    except Exception as e:
        print("-" * 70)
        print(f"\n❌ Failed to get current version: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    show_current_version()

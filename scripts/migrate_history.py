#!/usr/bin/env python3
"""
Show database migration history
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def show_history():
    """Show migration history"""
    
    print("=" * 70)
    print("Database Migration - History")
    print("=" * 70)
    print("\nAvailable migrations:")
    print("-" * 70)
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Show history
        command.history(alembic_cfg, verbose=True)
        
        print("-" * 70)
        print("\nTo check current version:")
        print("  python scripts/migrate_current.py")
        
    except Exception as e:
        print("-" * 70)
        print(f"\n❌ Failed to get history: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    show_history()

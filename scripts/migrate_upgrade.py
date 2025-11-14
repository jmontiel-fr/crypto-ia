#!/usr/bin/env python3
"""
Run database migrations (upgrade to latest)
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def upgrade_database():
    """Upgrade database to latest migration"""
    
    print("=" * 70)
    print("Database Migration - Upgrade")
    print("=" * 70)
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("\n❌ ERROR: DATABASE_URL environment variable is not set")
        print("\nPlease set DATABASE_URL before running migrations:")
        print("  export DATABASE_URL=postgresql://user:pass@host:port/dbname")
        sys.exit(1)
    
    print(f"\nDatabase: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL', '') else 'unknown'}")
    print("\nRunning migrations...")
    print("-" * 70)
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Run upgrade
        command.upgrade(alembic_cfg, "head")
        
        print("-" * 70)
        print("\n✅ Database upgraded successfully!")
        print("\nTo check current version:")
        print("  python scripts/migrate_current.py")
        
    except Exception as e:
        print("-" * 70)
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    upgrade_database()

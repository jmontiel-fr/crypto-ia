#!/usr/bin/env python3
"""
Rollback database migrations (downgrade)
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def downgrade_database(revision='base'):
    """Downgrade database to specified revision"""
    
    print("=" * 70)
    print("Database Migration - Downgrade")
    print("=" * 70)
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("\n❌ ERROR: DATABASE_URL environment variable is not set")
        print("\nPlease set DATABASE_URL before running migrations:")
        print("  export DATABASE_URL=postgresql://user:pass@host:port/dbname")
        sys.exit(1)
    
    print(f"\nDatabase: {os.getenv('DATABASE_URL').split('@')[1] if '@' in os.getenv('DATABASE_URL', '') else 'unknown'}")
    print(f"Target revision: {revision}")
    
    # Confirm downgrade
    if revision == 'base':
        print("\n⚠️  WARNING: This will remove ALL migrations and drop all tables!")
    else:
        print(f"\n⚠️  WARNING: This will rollback to revision {revision}")
    
    confirm = input("\nAre you sure you want to continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("\n❌ Downgrade cancelled")
        sys.exit(0)
    
    print("\nRunning downgrade...")
    print("-" * 70)
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Run downgrade
        command.downgrade(alembic_cfg, revision)
        
        print("-" * 70)
        print("\n✅ Database downgraded successfully!")
        print("\nTo check current version:")
        print("  python scripts/migrate_current.py")
        
    except Exception as e:
        print("-" * 70)
        print(f"\n❌ Downgrade failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Get revision from command line argument
    revision = sys.argv[1] if len(sys.argv) > 1 else 'base'
    downgrade_database(revision)

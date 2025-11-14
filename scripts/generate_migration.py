#!/usr/bin/env python3
"""
Generate Alembic migration without database connection
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic.config import Config
from alembic import command

def generate_initial_migration():
    """Generate initial migration file"""
    
    # Set DATABASE_URL to avoid connection issues
    os.environ['DATABASE_URL'] = 'postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db'
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Generate migration
    print("Generating initial migration...")
    command.revision(
        alembic_cfg,
        message="Initial schema with all tables",
        autogenerate=True
    )
    
    print("Migration generated successfully!")

if __name__ == '__main__':
    generate_initial_migration()

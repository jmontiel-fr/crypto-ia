#!/usr/bin/env python3
"""
Script to create the API keys table in the database.
Run this script to add the api_keys table to your existing database.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_loader import load_config
from src.data.database import get_engine, Base
from src.api.auth.api_key_manager import ApiKey


def create_api_keys_table():
    """Create the API keys table."""
    print("Creating API keys table...")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database engine
        engine = get_engine(config.database_url)
        
        # Create the api_keys table
        ApiKey.__table__.create(engine, checkfirst=True)
        
        print("✅ API keys table created successfully!")
        print("\nTable structure:")
        print("- id: Primary key")
        print("- key_id: Unique key identifier")
        print("- key_hash: Hashed API key")
        print("- name: Human-readable name")
        print("- role: user/admin/readonly")
        print("- created_at: Creation timestamp")
        print("- last_used: Last usage timestamp")
        print("- expires_at: Expiration timestamp (optional)")
        print("- is_active: Active status")
        print("- created_by: Who created the key")
        print("- description: Optional description")
        
        print("\nNext steps:")
        print("1. Create your first admin API key:")
        print("   python scripts/manage_api_keys.py create 'Admin Key' --role admin")
        print("2. Test the API with your new key")
        
    except Exception as e:
        print(f"❌ Error creating API keys table: {e}")
        sys.exit(1)


if __name__ == '__main__':
    create_api_keys_table()
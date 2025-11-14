#!/usr/bin/env python3
"""
Generate an admin API key for the application.
Run this script to create an initial admin API key.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_loader import load_config
from src.data.database import session_scope, create_tables
from src.api.auth.api_key_manager import ApiKeyManager, ApiKeyRole


def main():
    """Generate admin API key."""
    print("=" * 60)
    print("Admin API Key Generator")
    print("=" * 60)
    
    # Load config
    try:
        config = load_config()
        print(f"✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return 1
    
    # Ensure tables exist
    try:
        create_tables()
        print(f"✓ Database tables ready")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return 1
    
    # Generate API key
    try:
        with session_scope() as session:
            api_key_manager = ApiKeyManager(session)
            
            # Check if admin key already exists
            existing_keys = api_key_manager.list_api_keys()
            admin_keys = [k for k in existing_keys if k.role == ApiKeyRole.ADMIN]
            
            if admin_keys:
                print(f"\n⚠ Warning: {len(admin_keys)} admin key(s) already exist:")
                for key in admin_keys:
                    print(f"  - {key.name} (ID: {key.key_id})")
                
                response = input("\nGenerate another admin key? (y/N): ")
                if response.lower() != 'y':
                    print("Cancelled.")
                    return 0
            
            # Get key name
            key_name = input("\nEnter a name for this API key (default: Admin Key): ").strip()
            if not key_name:
                key_name = "Admin Key"
            
            # Generate key
            key_id, api_key = api_key_manager.generate_api_key(
                name=key_name,
                role=ApiKeyRole.ADMIN,
                description="Admin API key for data collection and system management"
            )
            
            print("\n" + "=" * 60)
            print("✓ Admin API Key Generated Successfully!")
            print("=" * 60)
            print(f"\nKey ID:  {key_id}")
            print(f"API Key: {api_key}")
            print("\n⚠ IMPORTANT: Save this API key securely!")
            print("   It will NOT be shown again.")
            print("\nUsage:")
            print(f"  curl -H 'X-API-Key: {api_key}' http://localhost:5000/api/admin/collect/status")
            print(f"  curl -H 'Authorization: Bearer {api_key}' http://localhost:5000/api/admin/collect/status")
            print("=" * 60)
            
            return 0
            
    except Exception as e:
        print(f"\n✗ Failed to generate API key: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

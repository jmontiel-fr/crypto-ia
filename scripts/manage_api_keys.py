#!/usr/bin/env python3
"""
Script to manage API keys for the Crypto SaaS application.
Provides command-line interface for creating, listing, and managing API keys.
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_loader import load_config
from src.data.database import get_session_factory
from src.api.auth.api_key_manager import ApiKeyManager, ApiKeyRole


def create_key(args):
    """Create a new API key."""
    print(f"\nCreating API key: {args.name}")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # Parse role
        try:
            role = ApiKeyRole(args.role.lower())
        except ValueError:
            print(f"❌ Invalid role: {args.role}")
            print(f"   Valid roles: {', '.join([r.value for r in ApiKeyRole])}")
            return
        
        # Create the key
        key_id, api_key = api_key_manager.generate_api_key(
            name=args.name,
            role=role,
            expires_in_days=args.expires_in_days,
            created_by='CLI Admin',
            description=args.description
        )
        
        print(f"✅ API key created successfully!")
        print(f"   Key ID: {key_id}")
        print(f"   API Key: {api_key}")
        print(f"   Name: {args.name}")
        print(f"   Role: {role.value}")
        
        if args.expires_in_days:
            print(f"   Expires in: {args.expires_in_days} days")
        else:
            print("   Expires: Never")
        
        print("\n⚠️  IMPORTANT: Save the API key now - it won't be shown again!")
        print("   Use this key in your requests:")
        print(f"   curl -H 'Authorization: Bearer {api_key}' ...")
        print(f"   curl -H 'X-API-Key: {api_key}' ...")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error creating API key: {e}")
        sys.exit(1)


def list_keys(args):
    """List all API keys."""
    print("\nAPI Keys")
    print("=" * 80)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # List keys
        keys = api_key_manager.list_api_keys(include_inactive=args.include_inactive)
        
        if not keys:
            print("No API keys found.")
            return
        
        # Print header
        print(f"{'Key ID':<32} {'Name':<20} {'Role':<10} {'Status':<8} {'Created':<12} {'Last Used':<12}")
        print("-" * 80)
        
        # Print keys
        for key_info in keys:
            status = "Active" if key_info.is_active else "Inactive"
            created = key_info.created_at.strftime('%Y-%m-%d')
            last_used = key_info.last_used.strftime('%Y-%m-%d') if key_info.last_used else 'Never'
            
            print(f"{key_info.key_id:<32} {key_info.name:<20} {key_info.role.value:<10} {status:<8} {created:<12} {last_used:<12}")
        
        print(f"\nTotal: {len(keys)} keys")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error listing API keys: {e}")
        sys.exit(1)


def revoke_key(args):
    """Revoke an API key."""
    print(f"\nRevoking API key: {args.key_id}")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # Get key info first
        key_info = api_key_manager.get_api_key_info(args.key_id)
        if not key_info:
            print(f"❌ API key not found: {args.key_id}")
            return
        
        print(f"   Key: {key_info.name} ({key_info.role.value})")
        
        if not args.force:
            confirm = input("   Are you sure you want to revoke this key? (y/N): ")
            if confirm.lower() != 'y':
                print("   Cancelled.")
                return
        
        # Revoke the key
        success = api_key_manager.revoke_api_key(args.key_id)
        
        if success:
            print("✅ API key revoked successfully!")
        else:
            print("❌ Failed to revoke API key")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error revoking API key: {e}")
        sys.exit(1)


def rotate_key(args):
    """Rotate an API key."""
    print(f"\nRotating API key: {args.key_id}")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # Get key info first
        key_info = api_key_manager.get_api_key_info(args.key_id)
        if not key_info:
            print(f"❌ API key not found: {args.key_id}")
            return
        
        print(f"   Key: {key_info.name} ({key_info.role.value})")
        
        if not key_info.is_active:
            print("❌ Cannot rotate inactive key")
            return
        
        if not args.force:
            confirm = input("   Are you sure you want to rotate this key? (y/N): ")
            if confirm.lower() != 'y':
                print("   Cancelled.")
                return
        
        # Rotate the key
        result = api_key_manager.rotate_api_key(args.key_id)
        
        if result:
            key_id, new_api_key = result
            print("✅ API key rotated successfully!")
            print(f"   Key ID: {key_id}")
            print(f"   New API Key: {new_api_key}")
            print("\n⚠️  IMPORTANT: Update your applications with the new key!")
        else:
            print("❌ Failed to rotate API key")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error rotating API key: {e}")
        sys.exit(1)


def cleanup_keys(args):
    """Clean up expired API keys."""
    print("\nCleaning up expired API keys")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # Cleanup expired keys
        count = api_key_manager.cleanup_expired_keys()
        
        print(f"✅ Cleaned up {count} expired API keys")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error cleaning up expired keys: {e}")
        sys.exit(1)


def show_key_info(args):
    """Show detailed information about an API key."""
    print(f"\nAPI Key Information: {args.key_id}")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create database session
        session_factory = get_session_factory(config.database_url)
        session = session_factory()
        
        # Create API key manager
        api_key_manager = ApiKeyManager(session)
        
        # Get key info
        key_info = api_key_manager.get_api_key_info(args.key_id)
        
        if not key_info:
            print(f"❌ API key not found: {args.key_id}")
            return
        
        print(f"   Key ID: {key_info.key_id}")
        print(f"   Name: {key_info.name}")
        print(f"   Role: {key_info.role.value}")
        print(f"   Status: {'Active' if key_info.is_active else 'Inactive'}")
        print(f"   Created: {key_info.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if key_info.last_used:
            print(f"   Last Used: {key_info.last_used.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("   Last Used: Never")
        
        if key_info.expires_at:
            print(f"   Expires: {key_info.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Check if expired
            if key_info.expires_at < datetime.utcnow():
                print("   ⚠️  This key has expired!")
        else:
            print("   Expires: Never")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error getting API key info: {e}")
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Manage API keys for Crypto SaaS application'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create key command
    create_parser = subparsers.add_parser('create', help='Create a new API key')
    create_parser.add_argument('name', help='Name for the API key')
    create_parser.add_argument('--role', choices=['user', 'admin', 'readonly'], 
                              default='user', help='Role for the API key (default: user)')
    create_parser.add_argument('--expires-in-days', type=int, 
                              help='Number of days until expiration (default: never)')
    create_parser.add_argument('--description', help='Description for the API key')
    create_parser.set_defaults(func=create_key)
    
    # List keys command
    list_parser = subparsers.add_parser('list', help='List all API keys')
    list_parser.add_argument('--include-inactive', action='store_true',
                            help='Include inactive keys in the list')
    list_parser.set_defaults(func=list_keys)
    
    # Show key info command
    info_parser = subparsers.add_parser('info', help='Show detailed key information')
    info_parser.add_argument('key_id', help='Key ID to show information for')
    info_parser.set_defaults(func=show_key_info)
    
    # Revoke key command
    revoke_parser = subparsers.add_parser('revoke', help='Revoke an API key')
    revoke_parser.add_argument('key_id', help='Key ID to revoke')
    revoke_parser.add_argument('--force', action='store_true',
                              help='Skip confirmation prompt')
    revoke_parser.set_defaults(func=revoke_key)
    
    # Rotate key command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate an API key')
    rotate_parser.add_argument('key_id', help='Key ID to rotate')
    rotate_parser.add_argument('--force', action='store_true',
                              help='Skip confirmation prompt')
    rotate_parser.set_defaults(func=rotate_key)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired API keys')
    cleanup_parser.set_defaults(func=cleanup_keys)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("=" * 70)
    print("Crypto SaaS API Key Manager")
    print("=" * 70)
    
    # Call the appropriate function
    args.func(args)
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
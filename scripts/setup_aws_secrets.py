#!/usr/bin/env python3
"""
Script to set up secrets in AWS Secrets Manager.
Run this script to migrate secrets from .env file to AWS Secrets Manager.
"""

import os
import sys
import argparse
import json
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.secrets_manager import SecretsManager


# List of sensitive environment variables to store in Secrets Manager
SENSITIVE_VARS = [
    'OPENAI_API_KEY',
    'BINANCE_API_KEY',
    'BINANCE_API_SECRET',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'SECRET_KEY',
    'DATABASE_URL',  # Contains password
]


def load_env_file(env_file: str) -> Dict[str, str]:
    """
    Load environment variables from file.
    
    Args:
        env_file: Path to environment file
    
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if not os.path.exists(env_file):
        print(f"Error: Environment file not found: {env_file}")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    return env_vars


def create_secrets_in_aws(
    env_vars: Dict[str, str],
    secrets_manager: SecretsManager,
    secret_prefix: str = 'crypto-saas'
) -> None:
    """
    Create secrets in AWS Secrets Manager.
    
    Args:
        env_vars: Dictionary of environment variables
        secrets_manager: SecretsManager instance
        secret_prefix: Prefix for secret names
    """
    print(f"\nCreating secrets in AWS Secrets Manager with prefix: {secret_prefix}")
    print("=" * 70)
    
    created_count = 0
    skipped_count = 0
    
    for var_name in SENSITIVE_VARS:
        if var_name not in env_vars:
            print(f"⚠️  Skipping {var_name}: not found in environment file")
            skipped_count += 1
            continue
        
        value = env_vars[var_name]
        
        # Skip placeholder values
        if any(placeholder in value.lower() for placeholder in [
            'your_', 'change_me', 'example', 'placeholder'
        ]):
            print(f"⚠️  Skipping {var_name}: contains placeholder value")
            skipped_count += 1
            continue
        
        # Create secret name with prefix
        secret_name = f"{secret_prefix}/{var_name}"
        
        # Create secret
        success = secrets_manager.create_secret(
            secret_name=secret_name,
            secret_value=value,
            description=f"Crypto SaaS - {var_name}"
        )
        
        if success:
            print(f"✅ Created secret: {secret_name}")
            created_count += 1
        else:
            print(f"❌ Failed to create secret: {secret_name}")
    
    print("\n" + "=" * 70)
    print(f"Summary: {created_count} created, {skipped_count} skipped")


def create_combined_secret(
    env_vars: Dict[str, str],
    secrets_manager: SecretsManager,
    secret_name: str = 'crypto-saas/all-secrets'
) -> None:
    """
    Create a single secret containing all sensitive variables as JSON.
    
    Args:
        env_vars: Dictionary of environment variables
        secrets_manager: SecretsManager instance
        secret_name: Name for the combined secret
    """
    print(f"\nCreating combined secret: {secret_name}")
    print("=" * 70)
    
    secrets_dict = {}
    
    for var_name in SENSITIVE_VARS:
        if var_name in env_vars:
            value = env_vars[var_name]
            
            # Skip placeholder values
            if not any(placeholder in value.lower() for placeholder in [
                'your_', 'change_me', 'example', 'placeholder'
            ]):
                secrets_dict[var_name] = value
    
    if not secrets_dict:
        print("⚠️  No valid secrets found to store")
        return
    
    # Convert to JSON
    secrets_json = json.dumps(secrets_dict, indent=2)
    
    # Create secret
    success = secrets_manager.create_secret(
        secret_name=secret_name,
        secret_value=secrets_json,
        description="Crypto SaaS - All sensitive configuration"
    )
    
    if success:
        print(f"✅ Created combined secret with {len(secrets_dict)} variables")
        print(f"   Variables: {', '.join(secrets_dict.keys())}")
    else:
        print(f"❌ Failed to create combined secret")


def list_secrets(secrets_manager: SecretsManager, secret_prefix: str = 'crypto-saas') -> None:
    """
    List existing secrets in AWS Secrets Manager.
    
    Args:
        secrets_manager: SecretsManager instance
        secret_prefix: Prefix to filter secrets
    """
    print(f"\nListing secrets with prefix: {secret_prefix}")
    print("=" * 70)
    
    try:
        import boto3
        client = boto3.client('secretsmanager', region_name=secrets_manager.aws_region)
        
        response = client.list_secrets()
        
        matching_secrets = [
            s for s in response.get('SecretList', [])
            if s['Name'].startswith(secret_prefix)
        ]
        
        if not matching_secrets:
            print(f"No secrets found with prefix: {secret_prefix}")
            return
        
        print(f"Found {len(matching_secrets)} secrets:\n")
        
        for secret in matching_secrets:
            print(f"  • {secret['Name']}")
            if 'Description' in secret:
                print(f"    Description: {secret['Description']}")
            print()
        
    except Exception as e:
        print(f"Error listing secrets: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Set up secrets in AWS Secrets Manager for Crypto SaaS'
    )
    
    parser.add_argument(
        '--env-file',
        default='aws-env',
        help='Path to environment file (default: aws-env)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    parser.add_argument(
        '--prefix',
        default='crypto-saas',
        help='Prefix for secret names (default: crypto-saas)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['individual', 'combined', 'list'],
        default='individual',
        help='Mode: individual secrets, combined JSON secret, or list existing (default: individual)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AWS Secrets Manager Setup for Crypto SaaS")
    print("=" * 70)
    
    # Initialize secrets manager
    secrets_manager = SecretsManager(environment='production', aws_region=args.region)
    
    if args.mode == 'list':
        list_secrets(secrets_manager, args.prefix)
        return
    
    # Load environment file
    print(f"\nLoading environment file: {args.env_file}")
    env_vars = load_env_file(args.env_file)
    print(f"Loaded {len(env_vars)} environment variables")
    
    # Create secrets based on mode
    if args.mode == 'individual':
        create_secrets_in_aws(env_vars, secrets_manager, args.prefix)
    elif args.mode == 'combined':
        create_combined_secret(env_vars, secrets_manager, f"{args.prefix}/all-secrets")
    
    print("\n" + "=" * 70)
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Update your aws-env file to reference secrets (optional)")
    print("2. Verify secrets in AWS Console")
    print("3. Test application with secrets manager enabled")
    print("=" * 70)


if __name__ == '__main__':
    main()

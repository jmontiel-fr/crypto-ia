#!/usr/bin/env python3
"""
Environment Configuration Loader
Automatically loads the appropriate environment file based on context.
"""

import os
import sys
from pathlib import Path

def detect_environment():
    """
    Detect the current environment based on various indicators.
    
    Returns:
        str: Environment name ('local', 'aws', 'production', 'development')
    """
    # Check explicit environment variable
    if os.getenv('ENVIRONMENT'):
        return os.getenv('ENVIRONMENT').lower()
    
    # Check if running on AWS EC2
    try:
        import requests
        # Try to access EC2 metadata service
        response = requests.get(
            'http://169.254.169.254/latest/meta-data/instance-id',
            timeout=1
        )
        if response.status_code == 200:
            return 'aws'
    except:
        pass
    
    # Check for AWS-specific environment variables
    if os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION'):
        return 'aws'
    
    # Check for development indicators
    if os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG') == 'true':
        return 'development'
    
    # Default to local
    return 'local'

def load_environment_file(env_name=None):
    """
    Load the appropriate environment file.
    
    Args:
        env_name: Specific environment name to load, or None for auto-detection
    """
    if env_name is None:
        env_name = detect_environment()
    
    # Map environment names to file names
    env_files = {
        'local': 'local-env',
        'development': 'local-env',
        'aws': 'aws-env',
        'production': 'aws-env'
    }
    
    env_file = env_files.get(env_name, 'local-env')
    env_path = Path(env_file)
    
    if not env_path.exists():
        # Try with .env extension
        env_path = Path(f"{env_file}.env")
        if not env_path.exists():
            print(f"Warning: Environment file not found: {env_file}")
            return False
    
    # Load environment variables from file
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
        
        print(f"Loaded environment configuration: {env_path}")
        return True
    except Exception as e:
        print(f"Error loading environment file {env_path}: {e}")
        return False

def main():
    """Main entry point for standalone usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load environment configuration")
    parser.add_argument('--env', choices=['local', 'aws', 'development', 'production'],
                       help='Specific environment to load')
    parser.add_argument('--detect', action='store_true',
                       help='Detect and print current environment')
    parser.add_argument('--list', action='store_true',
                       help='List available environment files')
    
    args = parser.parse_args()
    
    if args.detect:
        env = detect_environment()
        print(f"Detected environment: {env}")
        return
    
    if args.list:
        print("Available environment files:")
        for env_file in ['local-env', 'aws-env', 'local-env.env', 'aws-env.env']:
            if Path(env_file).exists():
                print(f"  ✓ {env_file}")
            else:
                print(f"  ✗ {env_file}")
        return
    
    # Load environment
    success = load_environment_file(args.env)
    if success:
        print("Environment loaded successfully")
        
        # Print some key variables (without sensitive values)
        safe_vars = [
            'ENVIRONMENT', 'WEB_UI_HOST', 'WEB_UI_PORT', 'API_PORT',
            'STREAMLIT_PORT', 'DATABASE_URL', 'LOG_LEVEL'
        ]
        
        print("\nKey configuration:")
        for var in safe_vars:
            value = os.getenv(var, 'Not set')
            if 'DATABASE_URL' in var and '@' in value:
                # Hide password in database URL
                value = value.split('@')[1] if '@' in value else value
                value = f"***@{value}"
            print(f"  {var}: {value}")
    else:
        print("Failed to load environment")
        sys.exit(1)

if __name__ == "__main__":
    main()
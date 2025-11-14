"""
Environment Configuration Validator
Validates required environment variables and configuration settings
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import re


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class EnvironmentValidator:
    """Validates environment configuration"""
    
    # Required variables for all environments
    REQUIRED_VARS = [
        'ENVIRONMENT',
        'DATABASE_URL',
        'OPENAI_API_KEY',
        'WEB_UI_HOST',
        'SECRET_KEY',
    ]
    
    # Variables that should not have example values in production
    EXAMPLE_VALUES = [
        'your_openai_key_here',
        'your_binance_key_here',
        'your_twilio_sid_here',
        'CHANGE_ME',
        'local_dev_secret_key_change_in_production',
    ]
    
    # SSL certificate paths to verify
    SSL_CERT_VARS = [
        'SSL_CERT_PATH',
        'SSL_KEY_PATH',
    ]
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize validator
        
        Args:
            environment: Environment name (local, production). If None, reads from ENVIRONMENT var
        """
        self.environment = environment or os.getenv('ENVIRONMENT', 'local')
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Run validation checks
        self._validate_required_vars()
        self._validate_database_url()
        self._validate_openai_config()
        self._validate_ssl_certificates()
        self._validate_production_settings()
        self._validate_api_keys()
        self._validate_alert_config()
        self._validate_paths()
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_required_vars(self):
        """Check that all required variables are set"""
        for var in self.REQUIRED_VARS:
            value = os.getenv(var)
            if not value:
                self.errors.append(f"Required environment variable '{var}' is not set")
            elif not value.strip():
                self.errors.append(f"Required environment variable '{var}' is empty")
    
    def _validate_database_url(self):
        """Validate database connection string"""
        db_url = os.getenv('DATABASE_URL', '')
        
        if not db_url:
            return  # Already caught by required vars check
        
        # Check format
        if not db_url.startswith('postgresql://'):
            self.errors.append("DATABASE_URL must start with 'postgresql://'")
            return
        
        # Parse URL components
        try:
            # Remove protocol
            url_parts = db_url.replace('postgresql://', '')
            
            # Check for credentials
            if '@' not in url_parts:
                self.errors.append("DATABASE_URL must include credentials (user:password@host)")
                return
            
            creds, host_db = url_parts.split('@', 1)
            
            # Check credentials format
            if ':' not in creds:
                self.errors.append("DATABASE_URL credentials must be in format user:password")
            
            # Check host and database
            if '/' not in host_db:
                self.errors.append("DATABASE_URL must include database name")
            else:
                host_port, db_name = host_db.split('/', 1)
                
                if not db_name:
                    self.errors.append("DATABASE_URL database name cannot be empty")
                
                # Warn about default passwords
                if 'crypto_pass' in creds and self.environment == 'production':
                    self.warnings.append("Using default database password in production is not recommended")
        
        except Exception as e:
            self.errors.append(f"Invalid DATABASE_URL format: {str(e)}")
    
    def _validate_openai_config(self):
        """Validate OpenAI configuration"""
        api_key = os.getenv('OPENAI_API_KEY', '')
        
        if not api_key:
            return  # Already caught by required vars check
        
        # Check for example value
        if api_key in self.EXAMPLE_VALUES:
            self.errors.append("OPENAI_API_KEY is set to example value. Please provide a valid API key")
        
        # Check key format (OpenAI keys start with 'sk-')
        if not api_key.startswith('sk-') and api_key not in self.EXAMPLE_VALUES:
            self.warnings.append("OPENAI_API_KEY does not start with 'sk-'. Verify this is a valid key")
        
        # Check model is set
        model = os.getenv('OPENAI_MODEL', '')
        if not model:
            self.warnings.append("OPENAI_MODEL is not set. Will use default model")
    
    def _validate_ssl_certificates(self):
        """Validate SSL certificate paths exist"""
        for var in self.SSL_CERT_VARS:
            cert_path = os.getenv(var, '')
            
            if not cert_path:
                self.warnings.append(f"{var} is not set. HTTPS may not work")
                continue
            
            # Check if path exists
            path = Path(cert_path)
            if not path.exists():
                self.warnings.append(f"{var} points to non-existent file: {cert_path}")
            elif not path.is_file():
                self.errors.append(f"{var} does not point to a file: {cert_path}")
            else:
                # Check file permissions
                if var == 'SSL_KEY_PATH':
                    # Private key should have restricted permissions
                    if path.stat().st_mode & 0o077:
                        self.warnings.append(f"SSL private key {cert_path} has overly permissive permissions")
    
    def _validate_production_settings(self):
        """Validate production-specific settings"""
        if self.environment != 'production':
            return
        
        # Check SECRET_KEY is not default
        secret_key = os.getenv('SECRET_KEY', '')
        if secret_key in self.EXAMPLE_VALUES:
            self.errors.append("SECRET_KEY must be changed from default value in production")
        
        if len(secret_key) < 32:
            self.warnings.append("SECRET_KEY should be at least 32 characters for production")
        
        # Check DEBUG is disabled
        debug = os.getenv('DEBUG', 'false').lower()
        if debug in ('true', '1', 'yes'):
            self.warnings.append("DEBUG mode is enabled in production. This is not recommended")
        
        # Check LOG_LEVEL
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        if log_level == 'DEBUG':
            self.warnings.append("LOG_LEVEL is set to DEBUG in production. Consider using INFO or WARNING")
        
        # Check API key requirement
        api_key_required = os.getenv('API_KEY_REQUIRED', 'false').lower()
        if api_key_required not in ('true', '1', 'yes'):
            self.warnings.append("API_KEY_REQUIRED is disabled in production. This is a security risk")
    
    def _validate_api_keys(self):
        """Validate API keys are not example values"""
        api_key_vars = [
            'BINANCE_API_KEY',
            'BINANCE_API_SECRET',
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
        ]
        
        for var in api_key_vars:
            value = os.getenv(var, '')
            if value and value in self.EXAMPLE_VALUES:
                self.warnings.append(f"{var} is set to example value. Update with actual credentials if using this service")
    
    def _validate_alert_config(self):
        """Validate alert system configuration"""
        alert_enabled = os.getenv('ALERT_ENABLED', 'false').lower()
        
        if alert_enabled in ('true', '1', 'yes'):
            # Check SMS provider is configured
            sms_provider = os.getenv('SMS_PROVIDER', '')
            if not sms_provider:
                self.warnings.append("ALERT_ENABLED is true but SMS_PROVIDER is not set")
            
            # Check phone number format
            phone = os.getenv('SMS_PHONE_NUMBER', '')
            if phone and not re.match(r'^\+\d{10,15}$', phone):
                self.warnings.append("SMS_PHONE_NUMBER should be in E.164 format (e.g., +1234567890)")
            
            # Check provider-specific config
            if sms_provider == 'twilio':
                if not os.getenv('TWILIO_ACCOUNT_SID'):
                    self.errors.append("SMS_PROVIDER is 'twilio' but TWILIO_ACCOUNT_SID is not set")
                if not os.getenv('TWILIO_AUTH_TOKEN'):
                    self.errors.append("SMS_PROVIDER is 'twilio' but TWILIO_AUTH_TOKEN is not set")
            elif sms_provider == 'aws_sns':
                if not os.getenv('AWS_SNS_TOPIC_ARN'):
                    self.errors.append("SMS_PROVIDER is 'aws_sns' but AWS_SNS_TOPIC_ARN is not set")
    
    def _validate_paths(self):
        """Validate file paths exist"""
        # Check log directory
        log_file = os.getenv('LOG_FILE', '')
        if log_file:
            log_dir = Path(log_file).parent
            if not log_dir.exists():
                self.warnings.append(f"Log directory does not exist: {log_dir}. It will be created on startup")
    
    def print_results(self):
        """Print validation results to console"""
        if self.errors:
            print("\n❌ Configuration Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Configuration validation passed!")
    
    def validate_or_exit(self):
        """Validate configuration and exit if errors found"""
        is_valid, errors, warnings = self.validate_all()
        
        self.print_results()
        
        if not is_valid:
            print("\n❌ Configuration validation failed. Please fix the errors above.")
            sys.exit(1)
        
        if warnings:
            print("\n⚠️  Configuration has warnings but will continue.")
        
        return True


def validate_database_connection():
    """
    Test database connection
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL not set")
            return False
        
        # Create engine with short timeout
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={'connect_timeout': 5}
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("✅ Database connection successful")
        return True
    
    except ImportError:
        print("⚠️  SQLAlchemy not installed. Skipping database connection test")
        return True
    
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False


def main():
    """Main validation entry point"""
    print("=" * 70)
    print("Crypto Market Analysis SaaS - Configuration Validator")
    print("=" * 70)
    
    # Check if .env file is loaded
    if not os.getenv('ENVIRONMENT'):
        print("\n⚠️  No environment variables loaded.")
        print("Make sure to load your .env file before running this validator.")
        print("\nExample:")
        print("  export $(cat local-env | xargs)")
        print("  python -m src.config.validator")
        sys.exit(1)
    
    environment = os.getenv('ENVIRONMENT', 'local')
    print(f"\nEnvironment: {environment}")
    print("-" * 70)
    
    # Run validation
    validator = EnvironmentValidator(environment)
    validator.validate_or_exit()
    
    # Test database connection
    print("\n" + "-" * 70)
    print("Testing database connection...")
    print("-" * 70)
    validate_database_connection()
    
    print("\n" + "=" * 70)
    print("Validation complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()

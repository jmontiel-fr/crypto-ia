"""
Environment Variable Validation Module

This module validates required environment variables and checks their values
to ensure the application is properly configured before startup.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class EnvironmentValidator:
    """Validates environment variables and configuration"""
    
    # Required environment variables
    REQUIRED_VARS = [
        'DATABASE_URL',
        'OPENAI_API_KEY',
        'SECRET_KEY',
    ]
    
    # Optional but recommended variables
    RECOMMENDED_VARS = [
        'COLLECTION_START_DATE',
        'TOP_N_CRYPTOS',
        'WEB_UI_HOST',
        'LOG_LEVEL',
    ]
    
    # Variables that should not use example values in production
    EXAMPLE_PATTERNS = [
        'your_',
        'CHANGE_ME',
        'example',
        'test_key',
        'dummy',
    ]
    
    def __init__(self, environment: str = None):
        """
        Initialize validator
        
        Args:
            environment: Environment name (local, production, etc.)
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
        self._validate_api_keys()
        self._validate_numeric_values()
        self._validate_file_paths()
        self._check_recommended_vars()
        self._check_production_settings()
        
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
        """Validate DATABASE_URL format and connectivity"""
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return  # Already caught by required vars check
        
        try:
            parsed = urlparse(db_url)
            
            # Check scheme
            if parsed.scheme not in ['postgresql', 'postgres']:
                self.errors.append(
                    f"DATABASE_URL must use postgresql:// scheme, got: {parsed.scheme}"
                )
            
            # Check hostname
            if not parsed.hostname:
                self.errors.append("DATABASE_URL missing hostname")
            
            # Check database name
            if not parsed.path or parsed.path == '/':
                self.errors.append("DATABASE_URL missing database name")
            
            # Check credentials
            if not parsed.username:
                self.warnings.append("DATABASE_URL missing username")
            if not parsed.password:
                self.warnings.append("DATABASE_URL missing password")
            
            # Check for example values
            if parsed.password and any(pattern in parsed.password.lower() 
                                      for pattern in self.EXAMPLE_PATTERNS):
                if self.environment == 'production':
                    self.errors.append(
                        "DATABASE_URL contains example password in production environment"
                    )
                else:
                    self.warnings.append(
                        "DATABASE_URL appears to contain example password"
                    )
                    
        except Exception as e:
            self.errors.append(f"Invalid DATABASE_URL format: {str(e)}")
    
    def _validate_openai_config(self):
        """Validate OpenAI API configuration"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return  # Already caught by required vars check
        
        # Check for example values
        if any(pattern in api_key.lower() for pattern in self.EXAMPLE_PATTERNS):
            self.errors.append(
                "OPENAI_API_KEY appears to be an example value. "
                "Please set a valid OpenAI API key."
            )
        
        # Check key format (OpenAI keys start with 'sk-')
        if not api_key.startswith('sk-'):
            self.warnings.append(
                "OPENAI_API_KEY does not start with 'sk-'. "
                "This may not be a valid OpenAI API key."
            )
        
        # Validate model name
        model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        valid_models = ['gpt-4o-mini', 'gpt-4o', 'gpt-4', 'gpt-3.5-turbo']
        if model not in valid_models:
            self.warnings.append(
                f"OPENAI_MODEL '{model}' is not a recognized model. "
                f"Valid models: {', '.join(valid_models)}"
            )
        
        # Validate temperature
        try:
            temp = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
            if not 0 <= temp <= 2:
                self.warnings.append(
                    f"OPENAI_TEMPERATURE should be between 0 and 2, got: {temp}"
                )
        except ValueError:
            self.errors.append("OPENAI_TEMPERATURE must be a number")
        
        # Validate max tokens
        try:
            max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '500'))
            if max_tokens < 1 or max_tokens > 4096:
                self.warnings.append(
                    f"OPENAI_MAX_TOKENS should be between 1 and 4096, got: {max_tokens}"
                )
        except ValueError:
            self.errors.append("OPENAI_MAX_TOKENS must be an integer")
    
    def _validate_ssl_certificates(self):
        """Validate SSL certificate paths"""
        cert_path = os.getenv('SSL_CERT_PATH')
        key_path = os.getenv('SSL_KEY_PATH')
        
        if cert_path:
            if not Path(cert_path).exists():
                self.warnings.append(
                    f"SSL certificate file not found: {cert_path}"
                )
        
        if key_path:
            if not Path(key_path).exists():
                self.warnings.append(
                    f"SSL key file not found: {key_path}"
                )
            elif Path(key_path).exists():
                # Check permissions on key file
                stat_info = Path(key_path).stat()
                if stat_info.st_mode & 0o077:
                    self.warnings.append(
                        f"SSL key file has insecure permissions: {key_path}. "
                        "Should be readable only by owner (chmod 600)"
                    )
    
    def _validate_api_keys(self):
        """Validate API keys for external services"""
        # Binance API keys
        binance_key = os.getenv('BINANCE_API_KEY')
        binance_secret = os.getenv('BINANCE_API_SECRET')
        
        if binance_key and any(pattern in binance_key.lower() 
                               for pattern in self.EXAMPLE_PATTERNS):
            self.warnings.append(
                "BINANCE_API_KEY appears to be an example value"
            )
        
        if binance_secret and any(pattern in binance_secret.lower() 
                                  for pattern in self.EXAMPLE_PATTERNS):
            self.warnings.append(
                "BINANCE_API_SECRET appears to be an example value"
            )
        
        # Twilio credentials
        if os.getenv('SMS_PROVIDER') == 'twilio':
            twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
            twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if not twilio_sid:
                self.warnings.append(
                    "SMS_PROVIDER is 'twilio' but TWILIO_ACCOUNT_SID is not set"
                )
            elif any(pattern in twilio_sid.lower() for pattern in self.EXAMPLE_PATTERNS):
                self.warnings.append(
                    "TWILIO_ACCOUNT_SID appears to be an example value"
                )
            
            if not twilio_token:
                self.warnings.append(
                    "SMS_PROVIDER is 'twilio' but TWILIO_AUTH_TOKEN is not set"
                )
            elif any(pattern in twilio_token.lower() for pattern in self.EXAMPLE_PATTERNS):
                self.warnings.append(
                    "TWILIO_AUTH_TOKEN appears to be an example value"
                )
        
        # AWS SNS
        if os.getenv('SMS_PROVIDER') == 'aws_sns':
            sns_topic = os.getenv('AWS_SNS_TOPIC_ARN')
            if not sns_topic:
                self.warnings.append(
                    "SMS_PROVIDER is 'aws_sns' but AWS_SNS_TOPIC_ARN is not set"
                )
    
    def _validate_numeric_values(self):
        """Validate numeric configuration values"""
        numeric_configs = {
            'TOP_N_CRYPTOS': (1, 100),
            'PREDICTION_HORIZON_HOURS': (1, 168),
            'SEQUENCE_LENGTH': (24, 720),
            'ALERT_THRESHOLD_PERCENT': (0.1, 100),
            'ALERT_COOLDOWN_HOURS': (1, 24),
            'RATE_LIMIT_PER_MINUTE': (1, 10000),
            'DB_POOL_SIZE': (1, 100),
            'DB_MAX_OVERFLOW': (0, 100),
        }
        
        for var, (min_val, max_val) in numeric_configs.items():
            value_str = os.getenv(var)
            if value_str:
                try:
                    value = float(value_str)
                    if not min_val <= value <= max_val:
                        self.warnings.append(
                            f"{var} should be between {min_val} and {max_val}, got: {value}"
                        )
                except ValueError:
                    self.errors.append(f"{var} must be a number, got: {value_str}")
    
    def _validate_file_paths(self):
        """Validate file and directory paths"""
        log_file = os.getenv('LOG_FILE')
        if log_file:
            log_dir = Path(log_file).parent
            if not log_dir.exists():
                self.warnings.append(
                    f"Log directory does not exist: {log_dir}. "
                    "It will be created on startup."
                )
    
    def _check_recommended_vars(self):
        """Check for recommended but optional variables"""
        for var in self.RECOMMENDED_VARS:
            if not os.getenv(var):
                self.warnings.append(
                    f"Recommended environment variable '{var}' is not set. "
                    "Using default value."
                )
    
    def _check_production_settings(self):
        """Check production-specific settings"""
        if self.environment != 'production':
            return
        
        # Check SECRET_KEY is not default
        secret_key = os.getenv('SECRET_KEY', '')
        if 'local' in secret_key.lower() or 'dev' in secret_key.lower():
            self.errors.append(
                "SECRET_KEY appears to be a development value in production environment"
            )
        
        # Check DEBUG is disabled
        debug = os.getenv('DEBUG', 'false').lower()
        if debug in ['true', '1', 'yes']:
            self.errors.append(
                "DEBUG should be disabled in production environment"
            )
        
        # Check LOG_LEVEL
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        if log_level == 'DEBUG':
            self.warnings.append(
                "LOG_LEVEL is set to DEBUG in production. "
                "Consider using INFO or WARNING."
            )
        
        # Check API key requirement
        api_key_required = os.getenv('API_KEY_REQUIRED', 'true').lower()
        if api_key_required not in ['true', '1', 'yes']:
            self.errors.append(
                "API_KEY_REQUIRED should be enabled in production environment"
            )
    
    def print_report(self):
        """Print validation report"""
        is_valid, errors, warnings = self.validate_all()
        
        print("\n" + "="*70)
        print(f"Environment Configuration Validation Report")
        print(f"Environment: {self.environment}")
        print("="*70)
        
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        
        if not errors and not warnings:
            print("\n✅ All configuration checks passed!")
        
        print("\n" + "="*70)
        
        return is_valid


def validate_environment(raise_on_error: bool = True) -> bool:
    """
    Validate environment configuration
    
    Args:
        raise_on_error: If True, raise ConfigValidationError on validation failure
        
    Returns:
        True if validation passed, False otherwise
        
    Raises:
        ConfigValidationError: If validation fails and raise_on_error is True
    """
    validator = EnvironmentValidator()
    is_valid, errors, warnings = validator.validate_all()
    
    # Log warnings
    for warning in warnings:
        logger.warning(warning)
    
    # Handle errors
    if not is_valid:
        for error in errors:
            logger.error(error)
        
        if raise_on_error:
            error_msg = f"Configuration validation failed with {len(errors)} error(s)"
            raise ConfigValidationError(error_msg)
    
    return is_valid


if __name__ == '__main__':
    # Run validation when executed directly
    validator = EnvironmentValidator()
    is_valid = validator.print_report()
    
    exit(0 if is_valid else 1)

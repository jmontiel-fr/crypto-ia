"""
Secrets management module.
Integrates AWS Secrets Manager for production credentials and local .env for development.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages secrets retrieval from AWS Secrets Manager or local environment.
    Provides caching and rotation support.
    """
    
    def __init__(self, environment: str = 'local', aws_region: Optional[str] = None):
        """
        Initialize secrets manager.
        
        Args:
            environment: 'local' or 'production'
            aws_region: AWS region for Secrets Manager (required for production)
        """
        self.environment = environment
        self.aws_region = aws_region or os.getenv('AWS_REGION', 'us-east-1')
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache secrets for 5 minutes
        
        # Initialize AWS client for production
        self._secrets_client = None
        if self.environment == 'production':
            try:
                import boto3
                self._secrets_client = boto3.client(
                    'secretsmanager',
                    region_name=self.aws_region
                )
                logger.info(f"AWS Secrets Manager client initialized for region {self.aws_region}")
            except ImportError:
                logger.warning("boto3 not installed. AWS Secrets Manager unavailable.")
            except Exception as e:
                logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
        
        logger.info(f"SecretsManager initialized for {environment} environment")
    
    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Retrieve a secret value.
        
        Args:
            secret_name: Name of the secret (env var name or AWS secret name)
            use_cache: Whether to use cached value if available
        
        Returns:
            Secret value or None if not found
        """
        # Check cache first
        if use_cache and self._is_cached(secret_name):
            logger.debug(f"Returning cached value for secret: {secret_name}")
            return self._cache[secret_name]
        
        # Retrieve secret based on environment
        if self.environment == 'production':
            value = self._get_from_aws(secret_name)
        else:
            value = self._get_from_env(secret_name)
        
        # Cache the value
        if value is not None:
            self._cache[secret_name] = value
            self._cache_timestamps[secret_name] = datetime.utcnow()
        
        return value
    
    def get_secret_dict(self, secret_name: str, use_cache: bool = True) -> Optional[Dict[str, str]]:
        """
        Retrieve a secret that contains multiple key-value pairs (JSON format).
        
        Args:
            secret_name: Name of the secret
            use_cache: Whether to use cached value if available
        
        Returns:
            Dictionary of secret values or None if not found
        """
        secret_string = self.get_secret(secret_name, use_cache)
        
        if secret_string is None:
            return None
        
        try:
            return json.loads(secret_string)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secret as JSON: {secret_name}, error: {e}")
            return None
    
    def _get_from_aws(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from AWS Secrets Manager.
        
        Args:
            secret_name: AWS secret name
        
        Returns:
            Secret value or None if not found
        """
        if self._secrets_client is None:
            logger.error("AWS Secrets Manager client not initialized")
            return None
        
        try:
            response = self._secrets_client.get_secret_value(SecretId=secret_name)
            
            # Secrets can be stored as SecretString or SecretBinary
            if 'SecretString' in response:
                logger.info(f"Retrieved secret from AWS Secrets Manager: {secret_name}")
                return response['SecretString']
            else:
                logger.warning(f"Secret {secret_name} is binary, not supported")
                return None
                
        except self._secrets_client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret not found in AWS Secrets Manager: {secret_name}")
            return None
        except self._secrets_client.exceptions.InvalidRequestException as e:
            logger.error(f"Invalid request to AWS Secrets Manager: {e}")
            return None
        except self._secrets_client.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter for AWS Secrets Manager: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret from AWS: {secret_name}, error: {e}")
            return None
    
    def _get_from_env(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from environment variables.
        
        Args:
            secret_name: Environment variable name
        
        Returns:
            Secret value or None if not found
        """
        value = os.getenv(secret_name)
        
        if value is None:
            logger.debug(f"Secret not found in environment: {secret_name}")
        else:
            logger.debug(f"Retrieved secret from environment: {secret_name}")
        
        return value
    
    def _is_cached(self, secret_name: str) -> bool:
        """
        Check if secret is cached and cache is still valid.
        
        Args:
            secret_name: Name of the secret
        
        Returns:
            True if cached and valid, False otherwise
        """
        if secret_name not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(secret_name)
        if timestamp is None:
            return False
        
        # Check if cache has expired
        if datetime.utcnow() - timestamp > self._cache_ttl:
            logger.debug(f"Cache expired for secret: {secret_name}")
            del self._cache[secret_name]
            del self._cache_timestamps[secret_name]
            return False
        
        return True
    
    def clear_cache(self, secret_name: Optional[str] = None) -> None:
        """
        Clear cached secrets.
        
        Args:
            secret_name: Specific secret to clear, or None to clear all
        """
        if secret_name:
            self._cache.pop(secret_name, None)
            self._cache_timestamps.pop(secret_name, None)
            logger.info(f"Cleared cache for secret: {secret_name}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all cached secrets")
    
    def validate_no_secrets_in_logs(self, log_message: str, sensitive_patterns: Optional[list] = None) -> bool:
        """
        Validate that log message doesn't contain sensitive information.
        
        Args:
            log_message: Log message to validate
            sensitive_patterns: List of sensitive patterns to check for
        
        Returns:
            True if no secrets detected, False otherwise
        """
        if sensitive_patterns is None:
            # Default patterns to check
            sensitive_patterns = [
                'api_key', 'api_secret', 'password', 'token', 'secret_key',
                'auth_token', 'account_sid', 'private_key', 'access_key'
            ]
        
        log_lower = log_message.lower()
        
        for pattern in sensitive_patterns:
            if pattern in log_lower:
                # Check if it's just the key name or actual value
                # Look for patterns like "api_key=value" or "api_key: value"
                if any(sep in log_message for sep in ['=', ':', 'Bearer']):
                    logger.warning(f"Potential secret detected in log message: {pattern}")
                    return False
        
        return True
    
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """
        Rotate a secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret to rotate
            new_value: New secret value
        
        Returns:
            True if rotation successful, False otherwise
        """
        if self.environment != 'production':
            logger.warning("Secret rotation only supported in production environment")
            return False
        
        if self._secrets_client is None:
            logger.error("AWS Secrets Manager client not initialized")
            return False
        
        try:
            self._secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=new_value
            )
            
            # Clear cache for this secret
            self.clear_cache(secret_name)
            
            logger.info(f"Successfully rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_name}: {e}")
            return False
    
    def create_secret(self, secret_name: str, secret_value: str, description: str = "") -> bool:
        """
        Create a new secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name for the new secret
            secret_value: Secret value
            description: Optional description
        
        Returns:
            True if creation successful, False otherwise
        """
        if self.environment != 'production':
            logger.warning("Secret creation only supported in production environment")
            return False
        
        if self._secrets_client is None:
            logger.error("AWS Secrets Manager client not initialized")
            return False
        
        try:
            self._secrets_client.create_secret(
                Name=secret_name,
                SecretString=secret_value,
                Description=description
            )
            
            logger.info(f"Successfully created secret: {secret_name}")
            return True
            
        except self._secrets_client.exceptions.ResourceExistsException:
            logger.warning(f"Secret already exists: {secret_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to create secret {secret_name}: {e}")
            return False


def get_secrets_manager(environment: Optional[str] = None) -> SecretsManager:
    """
    Factory function to get a SecretsManager instance.
    
    Args:
        environment: Environment name ('local' or 'production')
                    If None, reads from ENVIRONMENT env var
    
    Returns:
        SecretsManager instance
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'local')
    
    aws_region = os.getenv('AWS_REGION')
    
    return SecretsManager(environment=environment, aws_region=aws_region)

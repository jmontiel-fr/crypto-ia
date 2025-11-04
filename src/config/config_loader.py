"""
Configuration loader module to read and validate environment variables.
Supports both local and AWS deployment environments.
Integrates with SecretsManager for secure credential handling.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import logging

from src.config.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration class holding all application settings."""
    
    # Environment
    environment: str
    
    # Database
    database_url: str
    db_pool_size: int
    db_max_overflow: int
    
    # Web UI
    web_ui_host: str
    web_ui_port: int
    web_ui_protocol: str
    
    # SSL Certificate
    ssl_cert_path: Optional[str]
    ssl_key_path: Optional[str]
    
    # Data Collection
    collection_start_date: str
    top_n_cryptos: int
    collection_schedule: str
    binance_api_key: Optional[str]
    binance_api_secret: Optional[str]
    
    # Prediction Engine
    model_type: str
    prediction_horizon_hours: int
    model_retrain_schedule: str
    sequence_length: int
    
    # GenAI
    openai_api_key: str
    openai_model: str
    openai_max_tokens: int
    openai_temperature: float
    
    # Alert System
    alert_enabled: bool
    alert_threshold_percent: float
    alert_cooldown_hours: int
    sms_provider: str
    sms_phone_number: Optional[str]
    twilio_account_sid: Optional[str]
    twilio_auth_token: Optional[str]
    twilio_from_number: Optional[str]
    aws_sns_topic_arn: Optional[str]
    
    # API
    api_host: str
    api_port: int
    api_key_required: bool
    rate_limit_per_minute: int
    
    # Streamlit
    streamlit_port: int
    
    # AWS
    aws_region: Optional[str]
    
    # Security
    secret_key: str
    allowed_origins: str
    
    # Logging
    log_level: str
    log_file: str


def load_config(env_file: Optional[str] = None, use_secrets_manager: bool = True) -> Config:
    """
    Load configuration from environment variables.
    
    Args:
        env_file: Optional path to .env file. If not provided, will look for
                 .env, local-env, or aws-env in the current directory.
        use_secrets_manager: Whether to use SecretsManager for sensitive credentials
    
    Returns:
        Config object with all settings loaded and validated.
    
    Raises:
        ValueError: If required configuration is missing or invalid.
    """
    # Load environment variables from file
    if env_file:
        load_dotenv(env_file)
    else:
        # Try to find environment file
        for env_name in ['.env', 'local-env', 'aws-env']:
            if os.path.exists(env_name):
                load_dotenv(env_name)
                logger.info(f"Loaded configuration from {env_name}")
                break
    
    # Initialize secrets manager if enabled
    secrets_manager = None
    if use_secrets_manager:
        environment = os.getenv('ENVIRONMENT', 'local')
        secrets_manager = get_secrets_manager(environment)
        logger.info(f"SecretsManager enabled for {environment} environment")
    
    # Helper function to get required env var (with secrets manager support)
    def get_required(key: str, use_secrets: bool = False) -> str:
        if use_secrets and secrets_manager:
            value = secrets_manager.get_secret(key)
        else:
            value = os.getenv(key)
        
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    # Helper function to get optional env var (with secrets manager support)
    def get_optional(key: str, default: Optional[str] = None, use_secrets: bool = False) -> Optional[str]:
        if use_secrets and secrets_manager:
            value = secrets_manager.get_secret(key)
            return value if value is not None else default
        return os.getenv(key, default)
    
    # Helper function to get boolean
    def get_bool(key: str, default: bool = False) -> bool:
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    # Helper function to get int
    def get_int(key: str, default: int) -> int:
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be an integer, got: {value}")
    
    # Helper function to get float
    def get_float(key: str, default: float) -> float:
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Environment variable {key} must be a float, got: {value}")
    
    try:
        config = Config(
            # Environment
            environment=get_optional('ENVIRONMENT', 'local'),
            
            # Database
            database_url=get_required('DATABASE_URL'),
            db_pool_size=get_int('DB_POOL_SIZE', 5),
            db_max_overflow=get_int('DB_MAX_OVERFLOW', 10),
            
            # Web UI
            web_ui_host=get_optional('WEB_UI_HOST', 'localhost'),
            web_ui_port=get_int('WEB_UI_PORT', 10443),
            web_ui_protocol=get_optional('WEB_UI_PROTOCOL', 'https'),
            
            # SSL Certificate
            ssl_cert_path=get_optional('SSL_CERT_PATH'),
            ssl_key_path=get_optional('SSL_KEY_PATH'),
            
            # Data Collection
            collection_start_date=get_optional('COLLECTION_START_DATE', '2024-01-01'),
            top_n_cryptos=get_int('TOP_N_CRYPTOS', 50),
            collection_schedule=get_optional('COLLECTION_SCHEDULE', '0 */6 * * *'),
            binance_api_key=get_optional('BINANCE_API_KEY', use_secrets=True),
            binance_api_secret=get_optional('BINANCE_API_SECRET', use_secrets=True),
            
            # Prediction Engine
            model_type=get_optional('MODEL_TYPE', 'LSTM'),
            prediction_horizon_hours=get_int('PREDICTION_HORIZON_HOURS', 24),
            model_retrain_schedule=get_optional('MODEL_RETRAIN_SCHEDULE', '0 2 * * 0'),
            sequence_length=get_int('SEQUENCE_LENGTH', 168),
            
            # GenAI
            openai_api_key=get_required('OPENAI_API_KEY', use_secrets=True),
            openai_model=get_optional('OPENAI_MODEL', 'gpt-4o-mini'),
            openai_max_tokens=get_int('OPENAI_MAX_TOKENS', 500),
            openai_temperature=get_float('OPENAI_TEMPERATURE', 0.7),
            
            # Alert System
            alert_enabled=get_bool('ALERT_ENABLED', True),
            alert_threshold_percent=get_float('ALERT_THRESHOLD_PERCENT', 10.0),
            alert_cooldown_hours=get_int('ALERT_COOLDOWN_HOURS', 4),
            sms_provider=get_optional('SMS_PROVIDER', 'twilio'),
            sms_phone_number=get_optional('SMS_PHONE_NUMBER'),
            twilio_account_sid=get_optional('TWILIO_ACCOUNT_SID', use_secrets=True),
            twilio_auth_token=get_optional('TWILIO_AUTH_TOKEN', use_secrets=True),
            twilio_from_number=get_optional('TWILIO_FROM_NUMBER'),
            aws_sns_topic_arn=get_optional('AWS_SNS_TOPIC_ARN'),
            
            # API
            api_host=get_optional('API_HOST', '0.0.0.0'),
            api_port=get_int('API_PORT', 5000),
            api_key_required=get_bool('API_KEY_REQUIRED', False),
            rate_limit_per_minute=get_int('RATE_LIMIT_PER_MINUTE', 100),
            
            # Streamlit
            streamlit_port=get_int('STREAMLIT_PORT', 8501),
            
            # AWS
            aws_region=get_optional('AWS_REGION'),
            
            # Security
            secret_key=get_required('SECRET_KEY', use_secrets=True),
            allowed_origins=get_optional('ALLOWED_ORIGINS', '*'),
            
            # Logging
            log_level=get_optional('LOG_LEVEL', 'INFO'),
            log_file=get_optional('LOG_FILE', 'logs/crypto_saas.log'),
        )
        
        # Validate configuration
        _validate_config(config)
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def _validate_config(config: Config) -> None:
    """
    Validate configuration values.
    
    Args:
        config: Configuration object to validate.
    
    Raises:
        ValueError: If configuration is invalid.
    """
    # Validate database URL format
    if not config.database_url.startswith('postgresql://'):
        raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
    
    # Validate model type
    if config.model_type not in ['LSTM', 'GRU']:
        raise ValueError(f"MODEL_TYPE must be 'LSTM' or 'GRU', got: {config.model_type}")
    
    # Validate SMS provider
    if config.alert_enabled and config.sms_provider not in ['twilio', 'aws_sns']:
        raise ValueError(f"SMS_PROVIDER must be 'twilio' or 'aws_sns', got: {config.sms_provider}")
    
    # Validate SMS configuration only if alerts are enabled
    if config.alert_enabled:
        if config.sms_provider == 'twilio':
            if not all([config.twilio_account_sid, config.twilio_auth_token, config.twilio_from_number]):
                logger.warning("Alert system enabled with Twilio but missing credentials. Alerts will be disabled.")
        elif config.sms_provider == 'aws_sns':
            if not config.aws_sns_topic_arn:
                logger.warning("Alert system enabled with AWS SNS but missing topic ARN. Alerts will be disabled.")
        
        if not config.sms_phone_number:
            logger.warning("Alert system enabled but SMS_PHONE_NUMBER not set. Alerts will be disabled.")
    
    # Validate SSL configuration for production
    if config.environment == 'production':
        if not config.ssl_cert_path or not config.ssl_key_path:
            raise ValueError("Production environment requires SSL_CERT_PATH and SSL_KEY_PATH")
    
    # Validate secret key
    if config.secret_key == 'local_dev_secret_key_change_in_production' and config.environment == 'production':
        raise ValueError("SECRET_KEY must be changed for production environment")
    
    # Validate log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if config.log_level.upper() not in valid_log_levels:
        raise ValueError(f"LOG_LEVEL must be one of {valid_log_levels}, got: {config.log_level}")
    
    logger.info("Configuration validation successful")

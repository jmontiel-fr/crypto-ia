"""
Example script to test the configuration loader.
This demonstrates how to load and use configuration in the application.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import load_config
from src.utils import setup_logging, get_logger


def main():
    """Main function to demonstrate configuration loading."""
    try:
        # Load configuration
        print("Loading configuration...")
        config = load_config()
        
        # Set up logging
        setup_logging(config.log_level, config.log_file)
        logger = get_logger(__name__)
        
        logger.info("Configuration loaded successfully!")
        
        # Display some configuration values
        print("\n" + "="*60)
        print("Configuration Summary")
        print("="*60)
        print(f"Environment: {config.environment}")
        print(f"Database URL: {config.database_url}")
        print(f"Web UI: {config.web_ui_protocol}://{config.web_ui_host}:{config.web_ui_port}")
        print(f"Top N Cryptos: {config.top_n_cryptos}")
        print(f"Model Type: {config.model_type}")
        print(f"OpenAI Model: {config.openai_model}")
        print(f"Alert Enabled: {config.alert_enabled}")
        print(f"API Port: {config.api_port}")
        print(f"Log Level: {config.log_level}")
        print("="*60)
        
        logger.info("Configuration test completed successfully")
        
    except Exception as e:
        print(f"\nError loading configuration: {e}")
        print("\nMake sure you have created a 'local-env' or '.env' file with required variables:")
        print("  - DATABASE_URL")
        print("  - OPENAI_API_KEY")
        print("  - SECRET_KEY")
        print("\nYou can copy from local-env.example:")
        print("  cp local-env.example local-env")
        sys.exit(1)


if __name__ == "__main__":
    main()

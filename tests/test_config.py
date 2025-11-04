"""Tests for configuration loader module."""

import os
import pytest
from src.config.config_loader import load_config, Config


def test_config_validation_requires_database_url(monkeypatch):
    """Test that configuration validation requires DATABASE_URL."""
    # Clear all environment variables
    for key in list(os.environ.keys()):
        if key.startswith(('DATABASE_', 'OPENAI_', 'SECRET_')):
            monkeypatch.delenv(key, raising=False)
    
    with pytest.raises(ValueError, match="Required environment variable DATABASE_URL"):
        load_config()


def test_config_validation_requires_openai_key(monkeypatch):
    """Test that configuration validation requires OPENAI_API_KEY."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    
    with pytest.raises(ValueError, match="Required environment variable OPENAI_API_KEY"):
        load_config()


def test_config_validation_requires_secret_key(monkeypatch):
    """Test that configuration validation requires SECRET_KEY."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    
    with pytest.raises(ValueError, match="Required environment variable SECRET_KEY"):
        load_config()


def test_config_loads_with_minimal_required_vars(monkeypatch):
    """Test that configuration loads with minimal required variables."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    
    config = load_config()
    
    assert config.database_url == 'postgresql://user:pass@localhost/db'
    assert config.openai_api_key == 'test-openai-key'
    assert config.secret_key == 'test-secret-key'
    assert config.environment == 'local'  # default
    assert config.model_type == 'LSTM'  # default


def test_config_validates_database_url_format(monkeypatch):
    """Test that configuration validates DATABASE_URL format."""
    monkeypatch.setenv('DATABASE_URL', 'mysql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    
    with pytest.raises(ValueError, match="DATABASE_URL must be a PostgreSQL connection string"):
        load_config()


def test_config_validates_model_type(monkeypatch):
    """Test that configuration validates MODEL_TYPE."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('MODEL_TYPE', 'INVALID')
    
    with pytest.raises(ValueError, match="MODEL_TYPE must be 'LSTM' or 'GRU'"):
        load_config()


def test_config_validates_production_secret_key(monkeypatch):
    """Test that production environment requires changed SECRET_KEY."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'local_dev_secret_key_change_in_production')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('SSL_CERT_PATH', '/path/to/cert.pem')
    monkeypatch.setenv('SSL_KEY_PATH', '/path/to/key.pem')
    
    with pytest.raises(ValueError, match="SECRET_KEY must be changed for production"):
        load_config()


def test_config_loads_optional_values(monkeypatch):
    """Test that configuration loads optional values with defaults."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    
    config = load_config()
    
    # Check defaults
    assert config.db_pool_size == 5
    assert config.top_n_cryptos == 50
    assert config.prediction_horizon_hours == 24
    assert config.openai_model == 'gpt-4o-mini'
    assert config.alert_enabled is True
    assert config.api_port == 5000


def test_config_parses_boolean_values(monkeypatch):
    """Test that configuration correctly parses boolean values."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('ALERT_ENABLED', 'false')
    monkeypatch.setenv('API_KEY_REQUIRED', 'true')
    
    config = load_config()
    
    assert config.alert_enabled is False
    assert config.api_key_required is True


def test_config_parses_numeric_values(monkeypatch):
    """Test that configuration correctly parses numeric values."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('TOP_N_CRYPTOS', '100')
    monkeypatch.setenv('ALERT_THRESHOLD_PERCENT', '15.5')
    monkeypatch.setenv('OPENAI_TEMPERATURE', '0.8')
    
    config = load_config()
    
    assert config.top_n_cryptos == 100
    assert config.alert_threshold_percent == 15.5
    assert config.openai_temperature == 0.8

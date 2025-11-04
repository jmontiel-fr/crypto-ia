"""
Basic tests for Flask API endpoints.
Tests core functionality without requiring full database setup.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    config = Mock()
    config.secret_key = 'test_secret_key'
    config.allowed_origins = '*'
    config.api_key_required = False
    config.rate_limit_per_minute = 100
    return config


@pytest.fixture
def app(mock_config):
    """Create Flask app for testing."""
    from src.api.app import create_app
    
    app = create_app(mock_config)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert data['service'] == 'crypto-market-analysis-api'


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get('/')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'service' in data
    assert 'endpoints' in data
    assert 'health' in data['endpoints']


def test_404_error(client):
    """Test 404 error handling."""
    response = client.get('/nonexistent')
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert 'error' in data
    assert data['error']['code'] == 'NOT_FOUND'


def test_predictions_endpoint_structure(client):
    """Test predictions endpoint returns proper structure."""
    # Mock the prediction engine
    with patch('src.api.routes.predictions.get_prediction_engine') as mock_engine:
        mock_pred = Mock()
        mock_pred.symbol = 'BTC'
        mock_pred.name = 'Bitcoin'
        mock_pred.current_price = Decimal('45000.00')
        mock_pred.predicted_price = Decimal('46500.00')
        mock_pred.predicted_change_percent = 3.33
        mock_pred.confidence_score = 0.85
        mock_pred.prediction_horizon_hours = 24
        mock_pred.timestamp = datetime.now()
        
        mock_engine_instance = Mock()
        mock_engine_instance.get_cached_predictions.return_value = [mock_pred]
        mock_engine.return_value = mock_engine_instance
        
        with patch('src.api.routes.predictions.session_scope'):
            response = client.get('/api/predictions/top20')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert 'predictions' in data
            assert 'prediction_time' in data
            assert 'horizon_hours' in data
            assert 'count' in data


def test_market_tendency_endpoint_structure(client):
    """Test market tendency endpoint returns proper structure."""
    with patch('src.api.routes.market.MarketTendencyClassifier') as mock_classifier:
        mock_result = Mock()
        mock_result.tendency = 'bullish'
        mock_result.confidence = 0.78
        mock_result.metrics = {
            'avg_change_percent': 2.5,
            'volatility_index': 0.15,
            'market_cap_change': 1.8,
            'positive_count': 35,
            'negative_count': 15,
            'positive_ratio': 0.70,
            'total_count': 50
        }
        mock_result.timestamp = datetime.now()
        
        mock_classifier_instance = Mock()
        mock_classifier_instance.get_cached_or_analyze.return_value = mock_result
        mock_classifier.return_value = mock_classifier_instance
        
        with patch('src.api.routes.market.session_scope'):
            response = client.get('/api/market/tendency')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert 'tendency' in data
            assert 'confidence' in data
            assert 'metrics' in data
            assert 'timestamp' in data


def test_chat_query_validation(client):
    """Test chat query endpoint validation."""
    # Test missing question
    response = client.post(
        '/api/chat/query',
        json={'session_id': 'test-123'}
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    
    # Test missing session_id
    response = client.post(
        '/api/chat/query',
        json={'question': 'What is Bitcoin?'}
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    
    # Test empty question
    response = client.post(
        '/api/chat/query',
        json={'question': '', 'session_id': 'test-123'}
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_rate_limiter():
    """Test rate limiter functionality."""
    from src.api.middleware.rate_limiter import RateLimiter
    
    limiter = RateLimiter(requests_per_minute=10)
    
    # Should allow first request
    assert limiter._consume_token('127.0.0.1') == True
    
    # Check remaining tokens
    remaining = limiter.get_remaining_tokens('127.0.0.1')
    assert remaining == 9


def test_api_key_validation():
    """Test API key validation."""
    from src.api.middleware.auth import validate_api_key
    
    # Valid key
    key_info = validate_api_key('dev_key_12345')
    assert key_info is not None
    assert key_info['role'] == 'user'
    
    # Invalid key
    key_info = validate_api_key('invalid_key')
    assert key_info is None


def test_request_validator():
    """Test request validator utility."""
    from src.api.utils import RequestValidator
    
    # Valid data
    data = {
        'name': 'Test',
        'age': 25,
        'type': 'user'
    }
    
    validator = RequestValidator(data)
    validator.require_field('name', str)
    validator.require_field('age', int)
    validator.validate_enum('type', ['user', 'admin'])
    
    assert validator.is_valid() == True
    
    # Invalid data
    data = {
        'name': '',
        'age': 'not_a_number'
    }
    
    validator = RequestValidator(data)
    validator.require_field('name', str)
    validator.validate_string('name', min_length=1)
    validator.require_field('age', int)
    
    assert validator.is_valid() == False
    assert len(validator.get_errors()) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

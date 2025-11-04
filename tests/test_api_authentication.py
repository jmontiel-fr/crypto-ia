"""
Tests for API authentication and authorization system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.api.auth.api_key_manager import ApiKeyManager, ApiKeyRole, ApiKeyInfo
from src.api.middleware.auth import (
    get_api_key_from_request,
    require_api_key,
    require_admin,
    require_role
)


class TestApiKeyManager:
    """Test cases for ApiKeyManager."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def api_key_manager(self, mock_session):
        """Create ApiKeyManager instance."""
        return ApiKeyManager(mock_session)
    
    def test_generate_api_key(self, api_key_manager):
        """Test API key generation."""
        # Mock database operations
        api_key_manager.db_session.add = Mock()
        api_key_manager.db_session.commit = Mock()
        
        # Generate key
        key_id, api_key = api_key_manager.generate_api_key(
            name="Test Key",
            role=ApiKeyRole.USER,
            expires_in_days=30,
            created_by="Test User",
            description="Test description"
        )
        
        # Verify results
        assert len(key_id) == 32  # 16 bytes hex = 32 chars
        assert len(api_key) > 40  # URL-safe base64 encoded
        assert api_key_manager.db_session.add.called
        assert api_key_manager.db_session.commit.called
    
    def test_validate_api_key_success(self, api_key_manager):
        """Test successful API key validation."""
        # Mock database query
        mock_db_key = Mock()
        mock_db_key.key_id = "test_key_id"
        mock_db_key.name = "Test Key"
        mock_db_key.role = "user"
        mock_db_key.created_at = datetime.utcnow()
        mock_db_key.last_used = None
        mock_db_key.expires_at = None
        mock_db_key.is_active = True
        
        api_key_manager.db_session.query.return_value.filter.return_value.first.return_value = mock_db_key
        api_key_manager._update_last_used = Mock()
        
        # Test validation
        result = api_key_manager.validate_api_key("test_api_key")
        
        # Verify result
        assert result is not None
        assert result.key_id == "test_key_id"
        assert result.name == "Test Key"
        assert result.role == ApiKeyRole.USER
        assert result.is_active is True
    
    def test_validate_api_key_not_found(self, api_key_manager):
        """Test API key validation when key not found."""
        # Mock database query returning None
        api_key_manager.db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test validation
        result = api_key_manager.validate_api_key("invalid_key")
        
        # Verify result
        assert result is None
    
    def test_validate_api_key_expired(self, api_key_manager):
        """Test API key validation when key is expired."""
        # Mock database query with expired key
        mock_db_key = Mock()
        mock_db_key.expires_at = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        mock_db_key.is_active = True
        
        api_key_manager.db_session.query.return_value.filter.return_value.first.return_value = mock_db_key
        
        # Test validation
        result = api_key_manager.validate_api_key("expired_key")
        
        # Verify result
        assert result is None
    
    def test_revoke_api_key(self, api_key_manager):
        """Test API key revocation."""
        # Mock database operations
        mock_db_key = Mock()
        mock_db_key.is_active = True
        
        api_key_manager.db_session.query.return_value.filter.return_value.first.return_value = mock_db_key
        api_key_manager.db_session.commit = Mock()
        api_key_manager._clear_cache_for_key_id = Mock()
        
        # Test revocation
        result = api_key_manager.revoke_api_key("test_key_id")
        
        # Verify result
        assert result is True
        assert mock_db_key.is_active is False
        assert api_key_manager.db_session.commit.called
        assert api_key_manager._clear_cache_for_key_id.called
    
    def test_rotate_api_key(self, api_key_manager):
        """Test API key rotation."""
        # Mock database operations
        mock_db_key = Mock()
        mock_db_key.is_active = True
        
        api_key_manager.db_session.query.return_value.filter.return_value.first.return_value = mock_db_key
        api_key_manager.db_session.commit = Mock()
        api_key_manager._clear_cache_for_key_id = Mock()
        
        # Test rotation
        result = api_key_manager.rotate_api_key("test_key_id")
        
        # Verify result
        assert result is not None
        key_id, new_api_key = result
        assert key_id == "test_key_id"
        assert len(new_api_key) > 40
        assert api_key_manager.db_session.commit.called
        assert api_key_manager._clear_cache_for_key_id.called
    
    def test_cleanup_expired_keys(self, api_key_manager):
        """Test cleanup of expired keys."""
        # Mock database operations
        mock_expired_key1 = Mock()
        mock_expired_key2 = Mock()
        expired_keys = [mock_expired_key1, mock_expired_key2]
        
        api_key_manager.db_session.query.return_value.filter.return_value.all.return_value = expired_keys
        api_key_manager.db_session.commit = Mock()
        
        # Test cleanup
        count = api_key_manager.cleanup_expired_keys()
        
        # Verify result
        assert count == 2
        assert mock_expired_key1.is_active is False
        assert mock_expired_key2.is_active is False
        assert api_key_manager.db_session.commit.called


class TestAuthMiddleware:
    """Test cases for authentication middleware."""
    
    @patch('src.api.middleware.auth.request')
    def test_get_api_key_from_authorization_header(self, mock_request):
        """Test extracting API key from Authorization header."""
        mock_request.headers.get.side_effect = lambda key: {
            'Authorization': 'Bearer test_api_key_123'
        }.get(key)
        mock_request.args.get.return_value = None
        
        result = get_api_key_from_request()
        
        assert result == 'test_api_key_123'
    
    @patch('src.api.middleware.auth.request')
    def test_get_api_key_from_header(self, mock_request):
        """Test extracting API key from X-API-Key header."""
        mock_request.headers.get.side_effect = lambda key: {
            'Authorization': None,
            'X-API-Key': 'test_api_key_456'
        }.get(key)
        mock_request.args.get.return_value = None
        
        result = get_api_key_from_request()
        
        assert result == 'test_api_key_456'
    
    @patch('src.api.middleware.auth.request')
    def test_get_api_key_from_query_param(self, mock_request):
        """Test extracting API key from query parameter."""
        mock_request.headers.get.return_value = None
        mock_request.args.get.return_value = 'test_api_key_789'
        
        result = get_api_key_from_request()
        
        assert result == 'test_api_key_789'
    
    @patch('src.api.middleware.auth.request')
    def test_get_api_key_not_found(self, mock_request):
        """Test when no API key is provided."""
        mock_request.headers.get.return_value = None
        mock_request.args.get.return_value = None
        
        result = get_api_key_from_request()
        
        assert result is None
    
    @patch('src.api.middleware.auth.get_api_key_manager')
    @patch('src.api.middleware.auth.get_api_key_from_request')
    @patch('src.api.middleware.auth.request')
    def test_require_api_key_success(self, mock_request, mock_get_key, mock_get_manager):
        """Test successful API key requirement."""
        # Mock API key extraction
        mock_get_key.return_value = 'valid_api_key'
        
        # Mock API key manager
        mock_manager = Mock()
        mock_key_info = ApiKeyInfo(
            key_id='test_key',
            name='Test Key',
            role=ApiKeyRole.USER,
            created_at=datetime.utcnow(),
            is_active=True
        )
        mock_manager.validate_api_key.return_value = mock_key_info
        mock_get_manager.return_value = mock_manager
        
        # Mock request
        mock_request.remote_addr = '127.0.0.1'
        
        # Test requirement
        result = require_api_key()
        
        # Verify result
        assert result is None  # Success returns None
        assert mock_request.api_key_info == mock_key_info
    
    @patch('src.api.middleware.auth.get_api_key_from_request')
    @patch('src.api.middleware.auth.request')
    @patch('src.api.middleware.auth.jsonify')
    def test_require_api_key_missing(self, mock_jsonify, mock_request, mock_get_key):
        """Test API key requirement when key is missing."""
        # Mock missing API key
        mock_get_key.return_value = None
        mock_request.remote_addr = '127.0.0.1'
        
        # Mock jsonify response
        mock_response = Mock()
        mock_jsonify.return_value = mock_response
        
        # Test requirement
        result = require_api_key()
        
        # Verify result
        assert result == (mock_response, 401)
        mock_jsonify.assert_called_once()
        
        # Check error response structure
        call_args = mock_jsonify.call_args[0][0]
        assert 'error' in call_args
        assert call_args['error']['code'] == 'MISSING_API_KEY'
    
    @patch('src.api.middleware.auth.get_api_key_manager')
    @patch('src.api.middleware.auth.get_api_key_from_request')
    @patch('src.api.middleware.auth.request')
    @patch('src.api.middleware.auth.jsonify')
    def test_require_api_key_invalid(self, mock_jsonify, mock_request, mock_get_key, mock_get_manager):
        """Test API key requirement when key is invalid."""
        # Mock API key extraction
        mock_get_key.return_value = 'invalid_api_key'
        mock_request.remote_addr = '127.0.0.1'
        
        # Mock API key manager returning None (invalid key)
        mock_manager = Mock()
        mock_manager.validate_api_key.return_value = None
        mock_get_manager.return_value = mock_manager
        
        # Mock jsonify response
        mock_response = Mock()
        mock_jsonify.return_value = mock_response
        
        # Test requirement
        result = require_api_key()
        
        # Verify result
        assert result == (mock_response, 401)
        mock_jsonify.assert_called_once()
        
        # Check error response structure
        call_args = mock_jsonify.call_args[0][0]
        assert 'error' in call_args
        assert call_args['error']['code'] == 'INVALID_API_KEY'
    
    @patch('src.api.middleware.auth.require_api_key')
    @patch('src.api.middleware.auth.request')
    @patch('src.api.middleware.auth.jsonify')
    def test_require_admin_success(self, mock_jsonify, mock_request, mock_require_key):
        """Test successful admin requirement."""
        # Mock successful API key validation
        mock_require_key.return_value = None
        
        # Mock admin key info
        mock_key_info = ApiKeyInfo(
            key_id='admin_key',
            name='Admin Key',
            role=ApiKeyRole.ADMIN,
            created_at=datetime.utcnow(),
            is_active=True
        )
        mock_request.api_key_info = mock_key_info
        
        # Test admin requirement
        result = require_admin()
        
        # Verify result
        assert result is None  # Success returns None
    
    @patch('src.api.middleware.auth.require_api_key')
    @patch('src.api.middleware.auth.request')
    @patch('src.api.middleware.auth.jsonify')
    def test_require_admin_insufficient_permissions(self, mock_jsonify, mock_request, mock_require_key):
        """Test admin requirement with insufficient permissions."""
        # Mock successful API key validation
        mock_require_key.return_value = None
        
        # Mock user key info (not admin)
        mock_key_info = ApiKeyInfo(
            key_id='user_key',
            name='User Key',
            role=ApiKeyRole.USER,
            created_at=datetime.utcnow(),
            is_active=True
        )
        mock_request.api_key_info = mock_key_info
        mock_request.remote_addr = '127.0.0.1'
        
        # Mock jsonify response
        mock_response = Mock()
        mock_jsonify.return_value = mock_response
        
        # Test admin requirement
        result = require_admin()
        
        # Verify result
        assert result == (mock_response, 403)
        mock_jsonify.assert_called_once()
        
        # Check error response structure
        call_args = mock_jsonify.call_args[0][0]
        assert 'error' in call_args
        assert call_args['error']['code'] == 'INSUFFICIENT_PERMISSIONS'


if __name__ == '__main__':
    pytest.main([__file__])
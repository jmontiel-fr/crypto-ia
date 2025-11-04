"""
API key management endpoints.
Provides CRUD operations for API keys (admin only).
"""

import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from typing import Dict, Any

from src.api.middleware.auth import admin_required
from src.api.auth.api_key_manager import ApiKeyRole
from src.api.app import format_error_response, format_success_response
from src.api.validation.decorators import validate_json, validate_query_params, api_key_creation_rules
from src.api.validation import optional_string, required_choice

logger = logging.getLogger(__name__)

api_keys_bp = Blueprint('api_keys', __name__)


@api_keys_bp.route('', methods=['POST'])
@admin_required
@validate_json(api_key_creation_rules())
def create_api_key():
    """
    Create a new API key.
    
    Request body:
    {
        "name": "Key name",
        "role": "user|admin|readonly",
        "expires_in_days": 365,  // optional
        "description": "Key description"  // optional
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "key_id": "abc123...",
            "api_key": "actual-key-string",
            "name": "Key name",
            "role": "user",
            "expires_at": "2025-01-01T00:00:00Z"
        }
    }
    """
    try:
        # Get validated data from decorator
        data = request.validated_data
        
        name = data['name']
        role = ApiKeyRole(data['role'])
        expires_in_days = data.get('expires_in_days')
        description = data.get('description')
        
        # Get current user info for audit
        current_key_info = getattr(request, 'api_key_info', None)
        created_by = current_key_info.name if current_key_info else 'Unknown'
        
        # Create API key
        api_key_manager = g.api_key_manager
        key_id, api_key = api_key_manager.generate_api_key(
            name=name,
            role=role,
            expires_in_days=expires_in_days,
            created_by=created_by,
            description=description
        )
        
        # Get key info for response
        key_info = api_key_manager.get_api_key_info(key_id)
        
        response_data = {
            'key_id': key_id,
            'api_key': api_key,  # Only returned on creation
            'name': key_info.name,
            'role': key_info.role.value,
            'created_at': key_info.created_at.isoformat(),
            'expires_at': key_info.expires_at.isoformat() if key_info.expires_at else None
        }
        
        logger.info(f"Created API key {key_id} for {name} by {created_by}")
        
        return jsonify(format_success_response(
            response_data,
            'API key created successfully'
        ))
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        return format_error_response(
            'CREATION_FAILED',
            'Failed to create API key',
            str(e),
            500
        )


@api_keys_bp.route('', methods=['GET'])
@admin_required
@validate_query_params({
    'include_inactive': lambda v, f, val: v.validate_boolean(f, val, required=False)
})
def list_api_keys():
    """
    List all API keys.
    
    Query parameters:
    - include_inactive: true/false (default: false)
    
    Returns:
    {
        "success": true,
        "data": {
            "keys": [
                {
                    "key_id": "abc123...",
                    "name": "Key name",
                    "role": "user",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_used": "2024-01-02T12:00:00Z",
                    "expires_at": "2025-01-01T00:00:00Z",
                    "is_active": true
                }
            ],
            "total": 5
        }
    }
    """
    try:
        # Get validated parameters from decorator
        params = getattr(request, 'validated_params', {})
        include_inactive = params.get('include_inactive', False)
        
        api_key_manager = g.api_key_manager
        keys = api_key_manager.list_api_keys(include_inactive=include_inactive)
        
        keys_data = []
        for key_info in keys:
            keys_data.append({
                'key_id': key_info.key_id,
                'name': key_info.name,
                'role': key_info.role.value,
                'created_at': key_info.created_at.isoformat(),
                'last_used': key_info.last_used.isoformat() if key_info.last_used else None,
                'expires_at': key_info.expires_at.isoformat() if key_info.expires_at else None,
                'is_active': key_info.is_active
            })
        
        response_data = {
            'keys': keys_data,
            'total': len(keys_data)
        }
        
        return jsonify(format_success_response(response_data))
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}", exc_info=True)
        return format_error_response(
            'LIST_FAILED',
            'Failed to list API keys',
            str(e),
            500
        )


@api_keys_bp.route('/<key_id>', methods=['GET'])
@admin_required
def get_api_key(key_id: str):
    """
    Get information about a specific API key.
    
    Returns:
    {
        "success": true,
        "data": {
            "key_id": "abc123...",
            "name": "Key name",
            "role": "user",
            "created_at": "2024-01-01T00:00:00Z",
            "last_used": "2024-01-02T12:00:00Z",
            "expires_at": "2025-01-01T00:00:00Z",
            "is_active": true
        }
    }
    """
    try:
        api_key_manager = g.api_key_manager
        key_info = api_key_manager.get_api_key_info(key_id)
        
        if not key_info:
            return format_error_response(
                'KEY_NOT_FOUND',
                'API key not found',
                f'No API key found with ID: {key_id}',
                404
            )
        
        response_data = {
            'key_id': key_info.key_id,
            'name': key_info.name,
            'role': key_info.role.value,
            'created_at': key_info.created_at.isoformat(),
            'last_used': key_info.last_used.isoformat() if key_info.last_used else None,
            'expires_at': key_info.expires_at.isoformat() if key_info.expires_at else None,
            'is_active': key_info.is_active
        }
        
        return jsonify(format_success_response(response_data))
        
    except Exception as e:
        logger.error(f"Error getting API key {key_id}: {e}", exc_info=True)
        return format_error_response(
            'GET_FAILED',
            'Failed to get API key',
            str(e),
            500
        )


@api_keys_bp.route('/<key_id>/revoke', methods=['POST'])
@admin_required
def revoke_api_key(key_id: str):
    """
    Revoke an API key.
    
    Returns:
    {
        "success": true,
        "data": {
            "key_id": "abc123...",
            "revoked": true
        }
    }
    """
    try:
        api_key_manager = g.api_key_manager
        
        # Check if key exists
        key_info = api_key_manager.get_api_key_info(key_id)
        if not key_info:
            return format_error_response(
                'KEY_NOT_FOUND',
                'API key not found',
                f'No API key found with ID: {key_id}',
                404
            )
        
        # Revoke the key
        success = api_key_manager.revoke_api_key(key_id)
        
        if not success:
            return format_error_response(
                'REVOCATION_FAILED',
                'Failed to revoke API key',
                'An error occurred while revoking the key',
                500
            )
        
        # Get current user info for audit
        current_key_info = getattr(request, 'api_key_info', None)
        revoked_by = current_key_info.name if current_key_info else 'Unknown'
        
        logger.info(f"Revoked API key {key_id} ({key_info.name}) by {revoked_by}")
        
        response_data = {
            'key_id': key_id,
            'revoked': True
        }
        
        return jsonify(format_success_response(
            response_data,
            'API key revoked successfully'
        ))
        
    except Exception as e:
        logger.error(f"Error revoking API key {key_id}: {e}", exc_info=True)
        return format_error_response(
            'REVOCATION_FAILED',
            'Failed to revoke API key',
            str(e),
            500
        )


@api_keys_bp.route('/<key_id>/rotate', methods=['POST'])
@admin_required
def rotate_api_key(key_id: str):
    """
    Rotate an API key (generate new key value).
    
    Returns:
    {
        "success": true,
        "data": {
            "key_id": "abc123...",
            "api_key": "new-key-string",
            "rotated": true
        }
    }
    """
    try:
        api_key_manager = g.api_key_manager
        
        # Check if key exists
        key_info = api_key_manager.get_api_key_info(key_id)
        if not key_info:
            return format_error_response(
                'KEY_NOT_FOUND',
                'API key not found',
                f'No API key found with ID: {key_id}',
                404
            )
        
        if not key_info.is_active:
            return format_error_response(
                'KEY_INACTIVE',
                'Cannot rotate inactive key',
                'Only active keys can be rotated',
                400
            )
        
        # Rotate the key
        result = api_key_manager.rotate_api_key(key_id)
        
        if not result:
            return format_error_response(
                'ROTATION_FAILED',
                'Failed to rotate API key',
                'An error occurred while rotating the key',
                500
            )
        
        rotated_key_id, new_api_key = result
        
        # Get current user info for audit
        current_key_info = getattr(request, 'api_key_info', None)
        rotated_by = current_key_info.name if current_key_info else 'Unknown'
        
        logger.info(f"Rotated API key {key_id} ({key_info.name}) by {rotated_by}")
        
        response_data = {
            'key_id': rotated_key_id,
            'api_key': new_api_key,  # Only returned on rotation
            'rotated': True
        }
        
        return jsonify(format_success_response(
            response_data,
            'API key rotated successfully'
        ))
        
    except Exception as e:
        logger.error(f"Error rotating API key {key_id}: {e}", exc_info=True)
        return format_error_response(
            'ROTATION_FAILED',
            'Failed to rotate API key',
            str(e),
            500
        )


@api_keys_bp.route('/cleanup', methods=['POST'])
@admin_required
def cleanup_expired_keys():
    """
    Clean up expired API keys.
    
    Returns:
    {
        "success": true,
        "data": {
            "cleaned_up": 3
        }
    }
    """
    try:
        api_key_manager = g.api_key_manager
        count = api_key_manager.cleanup_expired_keys()
        
        # Get current user info for audit
        current_key_info = getattr(request, 'api_key_info', None)
        cleaned_by = current_key_info.name if current_key_info else 'Unknown'
        
        logger.info(f"Cleaned up {count} expired API keys by {cleaned_by}")
        
        response_data = {
            'cleaned_up': count
        }
        
        return jsonify(format_success_response(
            response_data,
            f'Cleaned up {count} expired API keys'
        ))
        
    except Exception as e:
        logger.error(f"Error cleaning up expired keys: {e}", exc_info=True)
        return format_error_response(
            'CLEANUP_FAILED',
            'Failed to cleanup expired keys',
            str(e),
            500
        )
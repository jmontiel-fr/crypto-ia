"""
API key generation and management system.
Handles API key creation, validation, rotation, and storage.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

from src.data.database import Base

logger = logging.getLogger(__name__)


class ApiKeyRole(Enum):
    """API key roles with different permission levels."""
    USER = "user"
    ADMIN = "admin"
    READONLY = "readonly"


@dataclass
class ApiKeyInfo:
    """API key information."""
    key_id: str
    name: str
    role: ApiKeyRole
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class ApiKey(Base):
    """
    API key database model.
    Stores hashed API keys with metadata.
    """
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    key_id = Column(String(32), unique=True, nullable=False, index=True)
    key_hash = Column(String(64), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ApiKey(key_id='{self.key_id}', name='{self.name}', role='{self.role}')>"


class ApiKeyManager:
    """
    Manages API key generation, validation, and lifecycle.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize API key manager.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self._key_cache: Dict[str, ApiKeyInfo] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def generate_api_key(
        self,
        name: str,
        role: ApiKeyRole = ApiKeyRole.USER,
        expires_in_days: Optional[int] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate a new API key.
        
        Args:
            name: Human-readable name for the key
            role: Role/permission level for the key
            expires_in_days: Optional expiration in days
            created_by: Who created the key
            description: Optional description
        
        Returns:
            Tuple of (key_id, actual_api_key)
        """
        # Generate key ID and actual API key
        key_id = self._generate_key_id()
        api_key = self._generate_api_key_string()
        
        # Hash the API key for storage
        key_hash = self._hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create database record
        db_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            role=role.value,
            expires_at=expires_at,
            created_by=created_by,
            description=description
        )
        
        try:
            self.db_session.add(db_key)
            self.db_session.commit()
            
            logger.info(f"Generated API key: {key_id} for {name} with role {role.value}")
            
            return key_id, api_key
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create API key: {e}")
            raise
    
    def validate_api_key(self, api_key: str) -> Optional[ApiKeyInfo]:
        """
        Validate an API key and return key information.
        
        Args:
            api_key: API key to validate
        
        Returns:
            ApiKeyInfo if valid, None if invalid
        """
        # Check cache first
        if self._is_cached(api_key):
            key_info = self._key_cache[api_key]
            self._update_last_used(key_info.key_id)
            return key_info
        
        # Hash the provided key
        key_hash = self._hash_api_key(api_key)
        
        try:
            # Query database
            db_key = self.db_session.query(ApiKey).filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True
            ).first()
            
            if not db_key:
                logger.debug("API key not found or inactive")
                return None
            
            # Check expiration
            if db_key.expires_at and db_key.expires_at < datetime.utcnow():
                logger.warning(f"API key expired: {db_key.key_id}")
                return None
            
            # Create key info
            key_info = ApiKeyInfo(
                key_id=db_key.key_id,
                name=db_key.name,
                role=ApiKeyRole(db_key.role),
                created_at=db_key.created_at,
                last_used=db_key.last_used,
                expires_at=db_key.expires_at,
                is_active=db_key.is_active
            )
            
            # Cache the result
            self._cache_key_info(api_key, key_info)
            
            # Update last used timestamp
            self._update_last_used(db_key.key_id)
            
            logger.debug(f"Validated API key: {db_key.key_id}")
            return key_info
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: Key ID to revoke
        
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            db_key = self.db_session.query(ApiKey).filter(
                ApiKey.key_id == key_id
            ).first()
            
            if not db_key:
                logger.warning(f"API key not found for revocation: {key_id}")
                return False
            
            db_key.is_active = False
            self.db_session.commit()
            
            # Clear from cache
            self._clear_cache_for_key_id(key_id)
            
            logger.info(f"Revoked API key: {key_id}")
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False
    
    def rotate_api_key(self, key_id: str) -> Optional[Tuple[str, str]]:
        """
        Rotate an API key (generate new key, keep same metadata).
        
        Args:
            key_id: Key ID to rotate
        
        Returns:
            Tuple of (key_id, new_api_key) if successful, None otherwise
        """
        try:
            db_key = self.db_session.query(ApiKey).filter(
                ApiKey.key_id == key_id,
                ApiKey.is_active == True
            ).first()
            
            if not db_key:
                logger.warning(f"API key not found for rotation: {key_id}")
                return None
            
            # Generate new API key
            new_api_key = self._generate_api_key_string()
            new_key_hash = self._hash_api_key(new_api_key)
            
            # Update database record
            db_key.key_hash = new_key_hash
            self.db_session.commit()
            
            # Clear from cache
            self._clear_cache_for_key_id(key_id)
            
            logger.info(f"Rotated API key: {key_id}")
            return key_id, new_api_key
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to rotate API key {key_id}: {e}")
            return None
    
    def list_api_keys(self, include_inactive: bool = False) -> List[ApiKeyInfo]:
        """
        List all API keys.
        
        Args:
            include_inactive: Whether to include inactive keys
        
        Returns:
            List of ApiKeyInfo objects
        """
        try:
            query = self.db_session.query(ApiKey)
            
            if not include_inactive:
                query = query.filter(ApiKey.is_active == True)
            
            db_keys = query.order_by(ApiKey.created_at.desc()).all()
            
            return [
                ApiKeyInfo(
                    key_id=db_key.key_id,
                    name=db_key.name,
                    role=ApiKeyRole(db_key.role),
                    created_at=db_key.created_at,
                    last_used=db_key.last_used,
                    expires_at=db_key.expires_at,
                    is_active=db_key.is_active
                )
                for db_key in db_keys
            ]
            
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []
    
    def get_api_key_info(self, key_id: str) -> Optional[ApiKeyInfo]:
        """
        Get information about a specific API key.
        
        Args:
            key_id: Key ID to look up
        
        Returns:
            ApiKeyInfo if found, None otherwise
        """
        try:
            db_key = self.db_session.query(ApiKey).filter(
                ApiKey.key_id == key_id
            ).first()
            
            if not db_key:
                return None
            
            return ApiKeyInfo(
                key_id=db_key.key_id,
                name=db_key.name,
                role=ApiKeyRole(db_key.role),
                created_at=db_key.created_at,
                last_used=db_key.last_used,
                expires_at=db_key.expires_at,
                is_active=db_key.is_active
            )
            
        except Exception as e:
            logger.error(f"Failed to get API key info for {key_id}: {e}")
            return None
    
    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired API keys.
        
        Returns:
            Number of keys cleaned up
        """
        try:
            expired_keys = self.db_session.query(ApiKey).filter(
                ApiKey.expires_at < datetime.utcnow(),
                ApiKey.is_active == True
            ).all()
            
            count = 0
            for key in expired_keys:
                key.is_active = False
                count += 1
            
            self.db_session.commit()
            
            # Clear cache
            self._key_cache.clear()
            self._cache_timestamps.clear()
            
            logger.info(f"Cleaned up {count} expired API keys")
            return count
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to cleanup expired keys: {e}")
            return 0
    
    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        return secrets.token_hex(16)  # 32 character hex string
    
    def _generate_api_key_string(self) -> str:
        """Generate a secure API key string."""
        # Generate 32 bytes (256 bits) of random data
        random_bytes = secrets.token_bytes(32)
        # Encode as base64-like string but URL safe
        return secrets.token_urlsafe(32)  # Results in ~43 character string
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _update_last_used(self, key_id: str) -> None:
        """Update last used timestamp for a key."""
        try:
            self.db_session.query(ApiKey).filter(
                ApiKey.key_id == key_id
            ).update({
                'last_used': datetime.utcnow()
            })
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Failed to update last used for {key_id}: {e}")
            self.db_session.rollback()
    
    def _is_cached(self, api_key: str) -> bool:
        """Check if API key validation result is cached and valid."""
        if api_key not in self._key_cache:
            return False
        
        timestamp = self._cache_timestamps.get(api_key)
        if not timestamp:
            return False
        
        if datetime.utcnow() - timestamp > self._cache_ttl:
            del self._key_cache[api_key]
            del self._cache_timestamps[api_key]
            return False
        
        return True
    
    def _cache_key_info(self, api_key: str, key_info: ApiKeyInfo) -> None:
        """Cache API key validation result."""
        self._key_cache[api_key] = key_info
        self._cache_timestamps[api_key] = datetime.utcnow()
    
    def _clear_cache_for_key_id(self, key_id: str) -> None:
        """Clear cache entries for a specific key ID."""
        to_remove = []
        for api_key, key_info in self._key_cache.items():
            if key_info.key_id == key_id:
                to_remove.append(api_key)
        
        for api_key in to_remove:
            del self._key_cache[api_key]
            del self._cache_timestamps[api_key]
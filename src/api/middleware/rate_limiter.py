"""
Rate limiting middleware.
Implements token bucket algorithm for rate limiting.
"""

import logging
import time
from flask import request, jsonify
from typing import Dict, Tuple
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits requests per minute per IP address.
    """
    
    def __init__(self, requests_per_minute: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.tokens_per_second = requests_per_minute / 60.0
        
        # Storage: {ip_address: (tokens, last_update_time)}
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (requests_per_minute, time.time())
        )
        
        self.lock = Lock()
        
        logger.info(f"Rate limiter initialized: {requests_per_minute} requests/minute")
    
    def _get_tokens(self, ip_address: str) -> float:
        """
        Get current token count for IP address.
        
        Args:
            ip_address: Client IP address
        
        Returns:
            Current token count
        """
        with self.lock:
            tokens, last_update = self.buckets[ip_address]
            
            # Calculate tokens to add based on time elapsed
            now = time.time()
            time_elapsed = now - last_update
            tokens_to_add = time_elapsed * self.tokens_per_second
            
            # Update tokens (capped at max)
            new_tokens = min(
                self.requests_per_minute,
                tokens + tokens_to_add
            )
            
            # Update bucket
            self.buckets[ip_address] = (new_tokens, now)
            
            return new_tokens
    
    def _consume_token(self, ip_address: str) -> bool:
        """
        Try to consume a token for the request.
        
        Args:
            ip_address: Client IP address
        
        Returns:
            True if token consumed, False if rate limit exceeded
        """
        with self.lock:
            tokens = self._get_tokens(ip_address)
            
            if tokens >= 1.0:
                # Consume token
                new_tokens = tokens - 1.0
                self.buckets[ip_address] = (new_tokens, time.time())
                return True
            else:
                # Rate limit exceeded
                return False
    
    def check_rate_limit(self, request_obj) -> None:
        """
        Check rate limit for request.
        
        Args:
            request_obj: Flask request object
        
        Returns:
            None if allowed, error response if rate limit exceeded
        """
        # Get client IP address
        ip_address = request_obj.remote_addr
        
        # Try to consume token
        if not self._consume_token(ip_address):
            logger.warning(f"Rate limit exceeded for {ip_address}")
            
            # Calculate retry-after time
            tokens = self._get_tokens(ip_address)
            tokens_needed = 1.0 - tokens
            retry_after = int(tokens_needed / self.tokens_per_second) + 1
            
            response = jsonify({
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Too many requests',
                    'details': f'Rate limit: {self.requests_per_minute} requests per minute',
                    'retry_after_seconds': retry_after
                }
            })
            response.status_code = 429
            response.headers['Retry-After'] = str(retry_after)
            
            return response
        
        return None
    
    def get_remaining_tokens(self, ip_address: str) -> int:
        """
        Get remaining tokens for IP address.
        
        Args:
            ip_address: Client IP address
        
        Returns:
            Number of remaining tokens
        """
        tokens = self._get_tokens(ip_address)
        return int(tokens)
    
    def reset_bucket(self, ip_address: str) -> None:
        """
        Reset token bucket for IP address.
        
        Args:
            ip_address: Client IP address
        """
        with self.lock:
            self.buckets[ip_address] = (self.requests_per_minute, time.time())
        
        logger.info(f"Reset rate limit bucket for {ip_address}")
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old bucket entries.
        
        Args:
            max_age_seconds: Maximum age of buckets to keep
        
        Returns:
            Number of buckets removed
        """
        with self.lock:
            now = time.time()
            old_ips = [
                ip for ip, (_, last_update) in self.buckets.items()
                if now - last_update > max_age_seconds
            ]
            
            for ip in old_ips:
                del self.buckets[ip]
            
            if old_ips:
                logger.info(f"Cleaned up {len(old_ips)} old rate limit buckets")
            
            return len(old_ips)

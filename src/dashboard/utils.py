"""
Utility functions for Streamlit dashboard.
Handles API calls and data formatting.
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the Flask API."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API (e.g., http://localhost:5000)
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON body for POST requests
        
        Returns:
            Response data as dictionary
        
        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise
    
    def get_top_predictions(
        self,
        limit: int = 20,
        use_cache: bool = True,
        max_age_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get top cryptocurrency predictions.
        
        Args:
            limit: Number of predictions to return
            use_cache: Whether to use cached predictions
            max_age_hours: Maximum age of cached predictions
        
        Returns:
            Predictions data
        """
        return self._make_request(
            'GET',
            '/api/predictions/top20',
            params={
                'limit': limit,
                'use_cache': str(use_cache).lower(),
                'max_age_hours': max_age_hours
            }
        )
    
    def get_crypto_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Get prediction for specific cryptocurrency.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., BTC)
        
        Returns:
            Prediction data
        """
        return self._make_request(
            'GET',
            f'/api/predictions/crypto/{symbol}'
        )
    
    def get_market_tendency(
        self,
        use_cache: bool = True,
        max_age_hours: int = 1,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get current market tendency.
        
        Args:
            use_cache: Whether to use cached tendency
            max_age_hours: Maximum age of cached tendency
            lookback_hours: Hours to look back for analysis
        
        Returns:
            Market tendency data
        """
        return self._make_request(
            'GET',
            '/api/market/tendency',
            params={
                'use_cache': str(use_cache).lower(),
                'max_age_hours': max_age_hours,
                'lookback_hours': lookback_hours
            }
        )
    
    def get_tendency_history(self, hours: int = 168) -> Dict[str, Any]:
        """
        Get historical market tendencies.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Historical tendency data
        """
        return self._make_request(
            'GET',
            '/api/market/tendency/history',
            params={'hours': hours}
        )
    
    def get_market_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive market overview.
        
        Returns:
            Market overview data
        """
        return self._make_request('GET', '/api/market/overview')
    
    def trigger_collection(
        self,
        mode: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Trigger manual data collection.
        
        Args:
            mode: Collection mode (backward, forward, gap_fill)
            start_date: Start date for collection
            end_date: End date for collection
        
        Returns:
            Collection task response
        """
        data = {'mode': mode}
        
        if start_date:
            data['start_date'] = start_date.isoformat()
        if end_date:
            data['end_date'] = end_date.isoformat()
        
        return self._make_request('POST', '/api/admin/collect/trigger', json=data)
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get current data collection status.
        
        Returns:
            Collection status data
        """
        return self._make_request('GET', '/api/admin/collect/status')
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and statistics.
        
        Returns:
            System info data
        """
        return self._make_request('GET', '/api/admin/system/info')


def format_currency(value: float) -> str:
    """
    Format value as currency.
    
    Args:
        value: Numeric value
    
    Returns:
        Formatted currency string
    """
    if value >= 1000:
        return f"${value:,.2f}"
    elif value >= 1:
        return f"${value:.2f}"
    else:
        return f"${value:.6f}"


def format_percentage(value: float) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Numeric value
    
    Returns:
        Formatted percentage string
    """
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def get_tendency_emoji(tendency: str) -> str:
    """
    Get emoji for market tendency.
    
    Args:
        tendency: Market tendency string
    
    Returns:
        Emoji character
    """
    emoji_map = {
        'bullish': '🚀',
        'bearish': '📉',
        'volatile': '⚡',
        'stable': '😌',
        'consolidating': '🔄'
    }
    return emoji_map.get(tendency.lower(), '❓')


def get_tendency_color(tendency: str) -> str:
    """
    Get color for market tendency.
    
    Args:
        tendency: Market tendency string
    
    Returns:
        Color name or hex code
    """
    color_map = {
        'bullish': '#00c853',
        'bearish': '#d32f2f',
        'volatile': '#ff6f00',
        'stable': '#1976d2',
        'consolidating': '#7b1fa2'
    }
    return color_map.get(tendency.lower(), '#757575')


def format_number(value: int) -> str:
    """
    Format large numbers with appropriate suffixes.
    
    Args:
        value: Numeric value
    
    Returns:
        Formatted number string
    """
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)


def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: Datetime object
    
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        return "N/A"
    
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"


def get_severity_color(severity: str) -> str:
    """
    Get color for audit log severity.
    
    Args:
        severity: Severity level
    
    Returns:
        Color hex code
    """
    color_map = {
        'low': '#4caf50',      # Green
        'medium': '#ff9800',   # Orange
        'high': '#f44336',     # Red
        'critical': '#9c27b0'  # Purple
    }
    return color_map.get(severity.lower(), '#757575')


def get_event_type_icon(event_type: str) -> str:
    """
    Get icon for audit event type.
    
    Args:
        event_type: Event type string
    
    Returns:
        Icon emoji
    """
    icon_map = {
        'auth_success': '✅',
        'auth_failure': '❌',
        'pii_detected': '🚨',
        'chat_query_processed': '💬',
        'prediction_accessed': '🎯',
        'market_data_accessed': '📊',
        'admin_action': '⚙️',
        'system_error': '🔥',
        'rate_limit_exceeded': '⏰'
    }
    return icon_map.get(event_type.lower(), '📝')

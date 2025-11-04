"""
Health check endpoint.
Provides system health and status information.
"""

import logging
from flask import Blueprint, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with system health status
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'crypto-market-analysis-api',
        'version': '1.0.0'
    }), 200


@health_bp.route('/', methods=['GET'])
def root():
    """
    Root endpoint.
    
    Returns:
        JSON response with API information
    """
    return jsonify({
        'service': 'Crypto Market Analysis API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'predictions': '/api/predictions/top20',
            'market_tendency': '/api/market/tendency',
            'chat': '/api/chat/query',
            'admin': '/api/admin/*'
        },
        'documentation': 'See README.md for API documentation'
    }), 200

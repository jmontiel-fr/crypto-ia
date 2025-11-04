"""
Market endpoints.
Provides market tendency and overall market analysis.
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime

from src.data.database import session_scope
from src.prediction.market_tendency_classifier import MarketTendencyClassifier, TendencyResult

logger = logging.getLogger(__name__)

market_bp = Blueprint('market', __name__)


def format_tendency_response(result: TendencyResult) -> dict:
    """
    Format tendency result for API response.
    
    Args:
        result: TendencyResult object
    
    Returns:
        Formatted response dictionary
    """
    return {
        'tendency': result.tendency,
        'confidence': round(result.confidence, 2),
        'metrics': {
            'avg_change_percent': round(result.metrics.get('avg_change_percent', 0.0), 2),
            'volatility_index': round(result.metrics.get('volatility_index', 0.0), 4),
            'market_cap_change': round(result.metrics.get('market_cap_change', 0.0), 2),
            'positive_count': result.metrics.get('positive_count', 0),
            'negative_count': result.metrics.get('negative_count', 0),
            'positive_ratio': round(result.metrics.get('positive_ratio', 0.0), 2),
            'total_count': result.metrics.get('total_count', 0)
        },
        'timestamp': result.timestamp.isoformat()
    }


@market_bp.route('/tendency', methods=['GET'])
def get_market_tendency():
    """
    Get current market tendency.
    
    Query Parameters:
        - use_cache: Whether to use cached tendency (default: true)
        - max_age_hours: Maximum age of cached tendency in hours (default: 1)
        - lookback_hours: Hours to look back for analysis (default: 24)
    
    Returns:
        JSON response with market tendency classification
    """
    try:
        # Parse query parameters
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        max_age_hours = request.args.get('max_age_hours', 1, type=int)
        lookback_hours = request.args.get('lookback_hours', 24, type=int)
        
        logger.info(
            f"Fetching market tendency "
            f"(use_cache={use_cache}, lookback={lookback_hours}h)"
        )
        
        with session_scope() as session:
            classifier = MarketTendencyClassifier(
                session=session,
                lookback_hours=lookback_hours
            )
            
            if use_cache:
                # Try to get cached tendency
                result = classifier.get_cached_or_analyze(max_age_hours=max_age_hours)
                
                if result:
                    age_seconds = (datetime.now() - result.timestamp).total_seconds()
                    cached = age_seconds < (max_age_hours * 3600)
                    
                    logger.info(
                        f"Returning {'cached' if cached else 'fresh'} market tendency: "
                        f"{result.tendency} (confidence={result.confidence:.2f})"
                    )
                    
                    response = format_tendency_response(result)
                    response['cached'] = cached
                    
                    return jsonify(response), 200
            
            # Analyze fresh data
            result = classifier.analyze_and_store()
            
            if result.confidence == 0.0:
                return jsonify({
                    'error': {
                        'code': 'INSUFFICIENT_DATA',
                        'message': 'Unable to determine market tendency',
                        'details': 'Insufficient price data available'
                    }
                }), 503
            
            logger.info(
                f"Generated fresh market tendency: "
                f"{result.tendency} (confidence={result.confidence:.2f})"
            )
            
            response = format_tendency_response(result)
            response['cached'] = False
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching market tendency: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'TENDENCY_ERROR',
                'message': 'Failed to fetch market tendency',
                'details': str(e)
            }
        }), 500


@market_bp.route('/tendency/history', methods=['GET'])
def get_tendency_history():
    """
    Get historical market tendencies.
    
    Query Parameters:
        - hours: Number of hours to look back (default: 168 = 1 week)
    
    Returns:
        JSON response with historical tendencies
    """
    try:
        hours = request.args.get('hours', 168, type=int)
        hours = min(hours, 720)  # Cap at 30 days
        
        logger.info(f"Fetching tendency history for {hours} hours")
        
        with session_scope() as session:
            classifier = MarketTendencyClassifier(session=session)
            
            history = classifier.get_tendency_history(hours=hours)
            
            if not history:
                return jsonify({
                    'tendencies': [],
                    'count': 0,
                    'hours': hours
                }), 200
            
            response = {
                'tendencies': [format_tendency_response(t) for t in history],
                'count': len(history),
                'hours': hours,
                'start_time': history[0].timestamp.isoformat() if history else None,
                'end_time': history[-1].timestamp.isoformat() if history else None
            }
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching tendency history: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'HISTORY_ERROR',
                'message': 'Failed to fetch tendency history',
                'details': str(e)
            }
        }), 500


@market_bp.route('/overview', methods=['GET'])
def get_market_overview():
    """
    Get comprehensive market overview.
    
    Combines current tendency with key market metrics.
    
    Returns:
        JSON response with market overview
    """
    try:
        logger.info("Fetching market overview")
        
        with session_scope() as session:
            classifier = MarketTendencyClassifier(session=session)
            
            # Get current tendency
            tendency_result = classifier.get_cached_or_analyze(max_age_hours=1)
            
            if not tendency_result or tendency_result.confidence == 0.0:
                return jsonify({
                    'error': {
                        'code': 'INSUFFICIENT_DATA',
                        'message': 'Unable to generate market overview',
                        'details': 'Insufficient price data available'
                    }
                }), 503
            
            # Get price changes for additional context
            price_changes = classifier.get_price_changes()
            
            # Calculate additional metrics
            top_gainers = sorted(
                price_changes,
                key=lambda x: x['price_change_percent'],
                reverse=True
            )[:5]
            
            top_losers = sorted(
                price_changes,
                key=lambda x: x['price_change_percent']
            )[:5]
            
            response = {
                'tendency': format_tendency_response(tendency_result),
                'top_gainers': [
                    {
                        'symbol': g['symbol'],
                        'change_percent': round(g['price_change_percent'], 2)
                    }
                    for g in top_gainers
                ],
                'top_losers': [
                    {
                        'symbol': l['symbol'],
                        'change_percent': round(l['price_change_percent'], 2)
                    }
                    for l in top_losers
                ],
                'total_cryptos_analyzed': len(price_changes),
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'OVERVIEW_ERROR',
                'message': 'Failed to fetch market overview',
                'details': str(e)
            }
        }), 500

"""
Prediction endpoints.
Provides cryptocurrency price predictions and top performers.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
from typing import List

from src.data.database import session_scope
from src.prediction.prediction_engine import PredictionEngine, PredictionResult
from src.prediction.lstm_model import LSTMModel
from src.prediction.data_preprocessor import DataPreprocessor
from src.config.config_loader import Config

logger = logging.getLogger(__name__)

predictions_bp = Blueprint('predictions', __name__)


def get_prediction_engine() -> PredictionEngine:
    """
    Get or create prediction engine instance.
    
    Returns:
        PredictionEngine instance
    """
    # Get from app context if available
    if hasattr(current_app, 'prediction_engine'):
        return current_app.prediction_engine
    
    # Create new instance
    # Note: In production, this should be initialized once at app startup
    logger.warning("Creating new prediction engine instance (should be initialized at startup)")
    
    from src.data.database import get_session
    session = get_session()
    
    # Load model and preprocessor
    # For MVP, we'll use cached predictions if model not loaded
    model = LSTMModel(
        input_shape=(168, 5),  # 168 hours, 5 features
        units=64,
        dropout=0.2
    )
    
    preprocessor = DataPreprocessor(sequence_length=168)
    
    engine = PredictionEngine(
        session=session,
        model=model,
        preprocessor=preprocessor,
        prediction_horizon_hours=24
    )
    
    return engine


def format_prediction_response(predictions: List[PredictionResult]) -> dict:
    """
    Format prediction results for API response.
    
    Args:
        predictions: List of PredictionResult objects
    
    Returns:
        Formatted response dictionary
    """
    return {
        'predictions': [
            {
                'symbol': pred.symbol,
                'name': pred.name,
                'current_price': float(pred.current_price),
                'predicted_price': float(pred.predicted_price),
                'predicted_change_percent': round(pred.predicted_change_percent, 2),
                'confidence': round(pred.confidence_score, 2)
            }
            for pred in predictions
        ],
        'prediction_time': predictions[0].timestamp.isoformat() if predictions else datetime.now().isoformat(),
        'horizon_hours': predictions[0].prediction_horizon_hours if predictions else 24,
        'count': len(predictions)
    }


@predictions_bp.route('/top20', methods=['GET'])
def get_top20_predictions():
    """
    Get top 20 cryptocurrency predictions.
    
    Query Parameters:
        - limit: Number of predictions to return (default: 20, max: 50)
        - use_cache: Whether to use cached predictions (default: true)
        - max_age_hours: Maximum age of cached predictions in hours (default: 24)
    
    Returns:
        JSON response with top predictions
    """
    try:
        # Parse query parameters
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        max_age_hours = request.args.get('max_age_hours', 24, type=int)
        
        logger.info(f"Fetching top {limit} predictions (use_cache={use_cache})")
        
        with session_scope() as session:
            engine = get_prediction_engine()
            engine.session = session
            
            if use_cache:
                # Try to get cached predictions
                predictions = engine.get_cached_predictions(
                    limit=limit,
                    max_age_hours=max_age_hours
                )
                
                if predictions:
                    logger.info(f"Returning {len(predictions)} cached predictions")
                    response = format_prediction_response(predictions)
                    response['cached'] = True
                    
                    # Add cache headers
                    resp = jsonify(response)
                    resp.headers['Cache-Control'] = f'public, max-age={max_age_hours * 3600}'
                    return resp, 200
                
                logger.info("No valid cached predictions, generating fresh predictions")
            
            # Generate fresh predictions
            predictions = engine.predict_top_performers(limit=limit)
            
            if not predictions:
                return jsonify({
                    'error': {
                        'code': 'NO_PREDICTIONS',
                        'message': 'Unable to generate predictions',
                        'details': 'Insufficient data or model not available'
                    }
                }), 503
            
            # Cache predictions
            engine.cache_predictions(predictions)
            
            logger.info(f"Generated and cached {len(predictions)} fresh predictions")
            
            response = format_prediction_response(predictions)
            response['cached'] = False
            
            # Add cache headers
            resp = jsonify(response)
            resp.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            
            return resp, 200
            
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'PREDICTION_ERROR',
                'message': 'Failed to fetch predictions',
                'details': str(e)
            }
        }), 500


@predictions_bp.route('/crypto/<symbol>', methods=['GET'])
def get_crypto_prediction(symbol: str):
    """
    Get prediction for a specific cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH)
    
    Returns:
        JSON response with prediction for the cryptocurrency
    """
    try:
        symbol = symbol.upper()
        
        logger.info(f"Fetching prediction for {symbol}")
        
        with session_scope() as session:
            from src.data.repositories import CryptoRepository
            
            crypto_repo = CryptoRepository(session)
            crypto = crypto_repo.get_by_symbol(symbol)
            
            if not crypto:
                return jsonify({
                    'error': {
                        'code': 'CRYPTO_NOT_FOUND',
                        'message': f'Cryptocurrency {symbol} not found',
                        'details': 'This cryptocurrency is not tracked by the system'
                    }
                }), 404
            
            engine = get_prediction_engine()
            engine.session = session
            
            # Generate prediction
            prediction = engine.predict_single_crypto(crypto.id)
            
            if not prediction:
                return jsonify({
                    'error': {
                        'code': 'PREDICTION_UNAVAILABLE',
                        'message': f'Prediction unavailable for {symbol}',
                        'details': 'Insufficient historical data'
                    }
                }), 503
            
            response = {
                'symbol': prediction.symbol,
                'name': prediction.name,
                'current_price': float(prediction.current_price),
                'predicted_price': float(prediction.predicted_price),
                'predicted_change_percent': round(prediction.predicted_change_percent, 2),
                'confidence': round(prediction.confidence_score, 2),
                'prediction_time': prediction.timestamp.isoformat(),
                'horizon_hours': prediction.prediction_horizon_hours
            }
            
            return jsonify(response), 200
            
    except Exception as e:
        logger.error(f"Error fetching prediction for {symbol}: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'PREDICTION_ERROR',
                'message': f'Failed to fetch prediction for {symbol}',
                'details': str(e)
            }
        }), 500

"""
Portfolio evaluation API endpoints.
Provides portfolio prediction and optimization services.
"""

import logging
from flask import Blueprint, jsonify, request
from dataclasses import asdict

from src.api.middleware.validation import validate_json
from src.data.database import session_scope
from src.prediction.portfolio_evaluator import PortfolioEvaluator
from src.config.config_loader import load_config

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint('portfolio', __name__)


def portfolio_evaluation_rules():
    """Validation rules for portfolio evaluation."""
    return {
        'holdings': {
            'type': 'dict',
            'required': True,
            'minlength': 1,
            'maxlength': 50,
            'valueschema': {
                'type': 'number',
                'min': 0.000001
            }
        },
        'use_cache': {
            'type': 'boolean',
            'required': False,
            'default': True
        }
    }


def portfolio_comparison_rules():
    """Validation rules for portfolio comparison."""
    return {
        'portfolios': {
            'type': 'dict',
            'required': True,
            'minlength': 2,
            'maxlength': 10,
            'valueschema': {
                'type': 'dict',
                'minlength': 1,
                'valueschema': {
                    'type': 'number',
                    'min': 0.000001
                }
            }
        }
    }


@portfolio_bp.route('/evaluate', methods=['POST'])
@validate_json(portfolio_evaluation_rules())
def evaluate_portfolio():
    """
    Evaluate a cryptocurrency portfolio and predict 24-hour performance.
    
    Request Body:
        {
            "holdings": {
                "BTC": 0.5,
                "ETH": 2.0,
                "SOL": 100
            },
            "use_cache": true
        }
    
    Response:
        {
            "total_current_value": 50000.00,
            "total_predicted_value": 52500.00,
            "total_change_usd": 2500.00,
            "total_change_percent": 5.0,
            "holdings": [...],
            "best_performers": [...],
            "worst_performers": [...],
            "risk_score": 3.2,
            "confidence_score": 0.82,
            "timestamp": "2025-11-12T14:30:00",
            "prediction_horizon_hours": 24
        }
    """
    try:
        data = request.get_json()
        holdings = data['holdings']
        use_cache = data.get('use_cache', True)
        
        logger.info(f"Portfolio evaluation request: {len(holdings)} holdings")
        
        # Load config
        config = load_config()
        
        # Evaluate portfolio
        with session_scope() as session:
            evaluator = PortfolioEvaluator(config, session)
            evaluation = evaluator.evaluate_portfolio(holdings, use_cache=use_cache)
        
        # Convert to dict
        result = {
            'total_current_value': evaluation.total_current_value,
            'total_predicted_value': evaluation.total_predicted_value,
            'total_change_usd': evaluation.total_change_usd,
            'total_change_percent': evaluation.total_change_percent,
            'holdings': [
                {
                    'symbol': h.symbol,
                    'quantity': h.quantity,
                    'current_price': h.current_price,
                    'current_value': h.current_value,
                    'predicted_price': h.predicted_price,
                    'predicted_value': h.predicted_value,
                    'predicted_change_percent': h.predicted_change_percent,
                    'predicted_change_usd': h.predicted_change_usd
                }
                for h in evaluation.holdings
            ],
            'best_performers': evaluation.best_performers,
            'worst_performers': evaluation.worst_performers,
            'risk_score': evaluation.risk_score,
            'confidence_score': evaluation.confidence_score,
            'timestamp': evaluation.timestamp,
            'prediction_horizon_hours': evaluation.prediction_horizon_hours
        }
        
        return jsonify(result), 200
    
    except ValueError as e:
        logger.warning(f"Invalid portfolio: {e}")
        return jsonify({
            'error': {
                'code': 'INVALID_PORTFOLIO',
                'message': str(e)
            }
        }), 400
    
    except Exception as e:
        logger.error(f"Portfolio evaluation error: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'EVALUATION_ERROR',
                'message': 'Failed to evaluate portfolio',
                'details': str(e)
            }
        }), 500


@portfolio_bp.route('/compare', methods=['POST'])
@validate_json(portfolio_comparison_rules())
def compare_portfolios():
    """
    Compare multiple portfolios.
    
    Request Body:
        {
            "portfolios": {
                "Conservative": {
                    "BTC": 1.0,
                    "ETH": 5.0
                },
                "Aggressive": {
                    "SOL": 500,
                    "AVAX": 200
                },
                "Balanced": {
                    "BTC": 0.5,
                    "ETH": 2.0,
                    "SOL": 100
                }
            }
        }
    
    Response:
        {
            "portfolios": {...},
            "rankings": {
                "by_return": [...],
                "by_risk": [...]
            },
            "best_portfolio": "Aggressive",
            "timestamp": "2025-11-12T14:30:00"
        }
    """
    try:
        data = request.get_json()
        portfolios = data['portfolios']
        
        logger.info(f"Portfolio comparison request: {len(portfolios)} portfolios")
        
        # Load config
        config = load_config()
        
        # Compare portfolios
        with session_scope() as session:
            evaluator = PortfolioEvaluator(config, session)
            comparison = evaluator.compare_portfolios(portfolios)
        
        return jsonify(comparison), 200
    
    except ValueError as e:
        logger.warning(f"Invalid portfolios: {e}")
        return jsonify({
            'error': {
                'code': 'INVALID_PORTFOLIOS',
                'message': str(e)
            }
        }), 400
    
    except Exception as e:
        logger.error(f"Portfolio comparison error: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'COMPARISON_ERROR',
                'message': 'Failed to compare portfolios',
                'details': str(e)
            }
        }), 500


@portfolio_bp.route('/optimize', methods=['POST'])
def optimize_portfolio():
    """
    Get portfolio optimization suggestions.
    
    Request Body:
        {
            "holdings": {
                "BTC": 0.5,
                "ETH": 2.0,
                "DOGE": 1000
            },
            "target_value": 60000,
            "max_risk": 5.0
        }
    
    Response:
        {
            "current_portfolio": {...},
            "suggestions": [
                {
                    "action": "ADD",
                    "symbol": "SOL",
                    "reason": "Top predicted performer (+12.5%)",
                    "predicted_change": 12.5
                },
                {
                    "action": "REDUCE",
                    "symbol": "DOGE",
                    "reason": "Predicted to decline (-3.2%)",
                    "predicted_change": -3.2
                }
            ],
            "timestamp": "2025-11-12T14:30:00"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'holdings' not in data:
            return jsonify({
                'error': {
                    'code': 'MISSING_HOLDINGS',
                    'message': 'Field "holdings" is required'
                }
            }), 400
        
        holdings = data['holdings']
        target_value = data.get('target_value')
        max_risk = data.get('max_risk')
        
        logger.info(f"Portfolio optimization request: {len(holdings)} holdings")
        
        # Load config
        config = load_config()
        
        # Optimize portfolio
        with session_scope() as session:
            evaluator = PortfolioEvaluator(config, session)
            optimization = evaluator.optimize_portfolio(
                holdings,
                target_value=target_value,
                max_risk=max_risk
            )
        
        return jsonify(optimization), 200
    
    except Exception as e:
        logger.error(f"Portfolio optimization error: {e}", exc_info=True)
        return jsonify({
            'error': {
                'code': 'OPTIMIZATION_ERROR',
                'message': 'Failed to optimize portfolio',
                'details': str(e)
            }
        }), 500

"""
Portfolio evaluation using LSTM/GRU predictions.
Evaluates a portfolio of cryptocurrencies and predicts 24-hour performance.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.data.repositories import CryptoRepository, PriceHistoryRepository, PredictionRepository
from src.prediction.prediction_cache import PredictionCache
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


@dataclass
class PortfolioHolding:
    """Represents a single holding in a portfolio."""
    symbol: str
    quantity: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    predicted_price: Optional[float] = None
    predicted_value: Optional[float] = None
    predicted_change_percent: Optional[float] = None
    predicted_change_usd: Optional[float] = None


@dataclass
class PortfolioEvaluation:
    """Complete portfolio evaluation result."""
    total_current_value: float
    total_predicted_value: float
    total_change_usd: float
    total_change_percent: float
    holdings: List[PortfolioHolding]
    best_performers: List[Dict[str, Any]]
    worst_performers: List[Dict[str, Any]]
    risk_score: float
    confidence_score: float
    timestamp: str
    prediction_horizon_hours: int = 24


class PortfolioEvaluator:
    """
    Evaluates cryptocurrency portfolios using LSTM/GRU predictions.
    """
    
    def __init__(self, config: Config, session: Session):
        """
        Initialize portfolio evaluator.
        
        Args:
            config: Application configuration
            session: Database session
        """
        self.config = config
        self.session = session
        self.crypto_repo = CryptoRepository(session)
        self.price_repo = PriceHistoryRepository(session)
        self.prediction_repo = PredictionRepository(session)
        self.cache = PredictionCache(config)
        
        logger.info("Initialized PortfolioEvaluator")
    
    def evaluate_portfolio(
        self,
        holdings: Dict[str, float],
        use_cache: bool = True
    ) -> PortfolioEvaluation:
        """
        Evaluate a portfolio and predict 24-hour performance.
        
        Args:
            holdings: Dictionary of {symbol: quantity}
                     Example: {"BTC": 0.5, "ETH": 2.0, "SOL": 100}
            use_cache: Whether to use cached predictions
        
        Returns:
            PortfolioEvaluation with predictions
        """
        logger.info(f"Evaluating portfolio with {len(holdings)} holdings")
        
        portfolio_holdings = []
        total_current_value = 0.0
        total_predicted_value = 0.0
        confidence_scores = []
        
        for symbol, quantity in holdings.items():
            try:
                # Get current price
                crypto = self.crypto_repo.get_by_symbol(symbol)
                if not crypto:
                    logger.warning(f"{symbol}: Not found in database")
                    continue
                
                latest_prices = self.price_repo.get_latest_by_crypto(crypto.id, limit=1)
                if not latest_prices:
                    logger.warning(f"{symbol}: No price data available")
                    continue
                
                current_price = float(latest_prices[0].price_usd)
                current_value = current_price * quantity
                
                # Get prediction
                prediction = None
                
                if use_cache:
                    # Try cache first
                    cached_pred = self.cache.get_prediction(symbol)
                    if cached_pred:
                        prediction = cached_pred
                else:
                    # Get from database
                    db_predictions = self.prediction_repo.get_latest_by_crypto(
                        crypto.id,
                        limit=1
                    )
                    if db_predictions:
                        pred = db_predictions[0]
                        prediction = {
                            'predicted_change_percent': float(pred.predicted_change_percent),
                            'confidence_score': float(pred.confidence_score)
                        }
                
                if not prediction:
                    logger.warning(f"{symbol}: No prediction available")
                    # Use 0% change as fallback
                    prediction = {
                        'predicted_change_percent': 0.0,
                        'confidence_score': 0.0
                    }
                
                # Calculate predicted values
                predicted_change_percent = prediction['predicted_change_percent']
                predicted_price = current_price * (1 + predicted_change_percent / 100)
                predicted_value = predicted_price * quantity
                predicted_change_usd = predicted_value - current_value
                
                # Create holding
                holding = PortfolioHolding(
                    symbol=symbol,
                    quantity=quantity,
                    current_price=current_price,
                    current_value=current_value,
                    predicted_price=predicted_price,
                    predicted_value=predicted_value,
                    predicted_change_percent=predicted_change_percent,
                    predicted_change_usd=predicted_change_usd
                )
                
                portfolio_holdings.append(holding)
                total_current_value += current_value
                total_predicted_value += predicted_value
                confidence_scores.append(prediction['confidence_score'])
                
            except Exception as e:
                logger.error(f"{symbol}: Error evaluating: {e}")
                continue
        
        if not portfolio_holdings:
            raise ValueError("No valid holdings in portfolio")
        
        # Calculate totals
        total_change_usd = total_predicted_value - total_current_value
        total_change_percent = (total_change_usd / total_current_value) * 100 if total_current_value > 0 else 0
        
        # Sort holdings by predicted change
        sorted_holdings = sorted(
            portfolio_holdings,
            key=lambda h: h.predicted_change_percent or 0,
            reverse=True
        )
        
        # Get best and worst performers
        best_performers = [
            {
                'symbol': h.symbol,
                'quantity': h.quantity,
                'current_value': h.current_value,
                'predicted_change_percent': h.predicted_change_percent,
                'predicted_change_usd': h.predicted_change_usd
            }
            for h in sorted_holdings[:3]
        ]
        
        worst_performers = [
            {
                'symbol': h.symbol,
                'quantity': h.quantity,
                'current_value': h.current_value,
                'predicted_change_percent': h.predicted_change_percent,
                'predicted_change_usd': h.predicted_change_usd
            }
            for h in sorted_holdings[-3:]
        ]
        
        # Calculate risk score (based on volatility of predictions)
        if len(portfolio_holdings) > 1:
            changes = [h.predicted_change_percent for h in portfolio_holdings if h.predicted_change_percent is not None]
            import numpy as np
            risk_score = float(np.std(changes)) if changes else 0.0
        else:
            risk_score = 0.0
        
        # Average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Create evaluation result
        evaluation = PortfolioEvaluation(
            total_current_value=total_current_value,
            total_predicted_value=total_predicted_value,
            total_change_usd=total_change_usd,
            total_change_percent=total_change_percent,
            holdings=portfolio_holdings,
            best_performers=best_performers,
            worst_performers=worst_performers,
            risk_score=risk_score,
            confidence_score=avg_confidence,
            timestamp=datetime.now().isoformat(),
            prediction_horizon_hours=self.config.prediction_horizon_hours
        )
        
        logger.info(
            f"Portfolio evaluation complete: "
            f"${total_current_value:.2f} → ${total_predicted_value:.2f} "
            f"({total_change_percent:+.2f}%)"
        )
        
        return evaluation
    
    def compare_portfolios(
        self,
        portfolios: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Compare multiple portfolios.
        
        Args:
            portfolios: Dictionary of {portfolio_name: holdings}
                       Example: {
                           "Conservative": {"BTC": 1.0, "ETH": 5.0},
                           "Aggressive": {"SOL": 500, "AVAX": 200}
                       }
        
        Returns:
            Comparison results with rankings
        """
        logger.info(f"Comparing {len(portfolios)} portfolios")
        
        evaluations = {}
        
        for name, holdings in portfolios.items():
            try:
                evaluation = self.evaluate_portfolio(holdings)
                evaluations[name] = evaluation
            except Exception as e:
                logger.error(f"Error evaluating portfolio '{name}': {e}")
                continue
        
        if not evaluations:
            raise ValueError("No valid portfolios to compare")
        
        # Rank by predicted return
        ranked = sorted(
            evaluations.items(),
            key=lambda x: x[1].total_change_percent,
            reverse=True
        )
        
        comparison = {
            'portfolios': {
                name: {
                    'current_value': eval.total_current_value,
                    'predicted_value': eval.total_predicted_value,
                    'predicted_change_percent': eval.total_change_percent,
                    'predicted_change_usd': eval.total_change_usd,
                    'risk_score': eval.risk_score,
                    'confidence_score': eval.confidence_score
                }
                for name, eval in evaluations.items()
            },
            'rankings': {
                'by_return': [
                    {
                        'rank': i + 1,
                        'name': name,
                        'predicted_return': eval.total_change_percent
                    }
                    for i, (name, eval) in enumerate(ranked)
                ],
                'by_risk': [
                    {
                        'rank': i + 1,
                        'name': name,
                        'risk_score': eval.risk_score
                    }
                    for i, (name, eval) in enumerate(
                        sorted(evaluations.items(), key=lambda x: x[1].risk_score)
                    )
                ]
            },
            'best_portfolio': ranked[0][0] if ranked else None,
            'timestamp': datetime.now().isoformat()
        }
        
        return comparison
    
    def optimize_portfolio(
        self,
        current_holdings: Dict[str, float],
        target_value: Optional[float] = None,
        max_risk: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Suggest portfolio optimizations based on predictions.
        
        Args:
            current_holdings: Current portfolio holdings
            target_value: Target portfolio value (optional)
            max_risk: Maximum acceptable risk score (optional)
        
        Returns:
            Optimization suggestions
        """
        logger.info("Generating portfolio optimization suggestions")
        
        # Evaluate current portfolio
        current_eval = self.evaluate_portfolio(current_holdings)
        
        # Get all available predictions
        top_predictions = self.cache.get_top_predictions(limit=20)
        
        if not top_predictions:
            return {
                'error': 'No predictions available for optimization',
                'current_portfolio': current_eval
            }
        
        # Generate suggestions
        suggestions = []
        
        # Suggest adding top performers not in portfolio
        for pred in top_predictions[:5]:
            symbol = pred.get('symbol')
            if symbol not in current_holdings:
                suggestions.append({
                    'action': 'ADD',
                    'symbol': symbol,
                    'reason': f"Top predicted performer ({pred.get('predicted_change_percent', 0):+.2f}%)",
                    'predicted_change': pred.get('predicted_change_percent', 0)
                })
        
        # Suggest reducing/removing worst performers in portfolio
        for holding in current_eval.worst_performers:
            if holding['predicted_change_percent'] < -2:  # Predicted to lose >2%
                suggestions.append({
                    'action': 'REDUCE',
                    'symbol': holding['symbol'],
                    'reason': f"Predicted to decline ({holding['predicted_change_percent']:+.2f}%)",
                    'predicted_change': holding['predicted_change_percent']
                })
        
        return {
            'current_portfolio': {
                'value': current_eval.total_current_value,
                'predicted_value': current_eval.total_predicted_value,
                'predicted_change_percent': current_eval.total_change_percent,
                'risk_score': current_eval.risk_score
            },
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }

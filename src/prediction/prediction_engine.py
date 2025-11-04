"""
Prediction engine for cryptocurrency price forecasting.
Main interface for generating predictions and ranking top performers.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from src.data.models import Cryptocurrency, PriceHistory, Prediction
from src.data.repositories import (
    CryptoRepository,
    PriceHistoryRepository,
    PredictionRepository
)
from src.prediction.lstm_model import LSTMModel
from src.prediction.data_preprocessor import DataPreprocessor

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Data class for prediction results."""
    crypto_id: int
    symbol: str
    name: str
    current_price: Decimal
    predicted_price: Decimal
    predicted_change_percent: float
    confidence_score: float
    prediction_horizon_hours: int
    timestamp: datetime


class PredictionEngine:
    """
    Main prediction engine for cryptocurrency price forecasting.
    
    Features:
    - Generate predictions for all tracked cryptocurrencies
    - Rank top performers by predicted performance
    - Calculate confidence scores
    - Cache predictions to database
    """
    
    def __init__(
        self,
        session: Session,
        model: LSTMModel,
        preprocessor: DataPreprocessor,
        prediction_horizon_hours: int = 24,
        min_data_points: int = 200
    ):
        """
        Initialize prediction engine.
        
        Args:
            session: Database session
            model: Trained LSTM/GRU model
            preprocessor: Data preprocessor instance
            prediction_horizon_hours: Prediction horizon in hours (default: 24)
            min_data_points: Minimum data points required for prediction
        """
        self.session = session
        self.model = model
        self.preprocessor = preprocessor
        self.prediction_horizon_hours = prediction_horizon_hours
        self.min_data_points = min_data_points
        
        # Initialize repositories
        self.crypto_repo = CryptoRepository(session)
        self.price_repo = PriceHistoryRepository(session)
        self.prediction_repo = PredictionRepository(session)
        
        logger.info(
            f"Initialized PredictionEngine: "
            f"horizon={prediction_horizon_hours}h, "
            f"min_data_points={min_data_points}"
        )
    
    def predict_single_crypto(
        self,
        crypto_id: int,
        use_latest_data: bool = True
    ) -> Optional[PredictionResult]:
        """
        Generate prediction for a single cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID
            use_latest_data: Whether to use latest available data
        
        Returns:
            PredictionResult or None if insufficient data
        """
        # Get cryptocurrency info
        crypto = self.crypto_repo.get_by_id(crypto_id)
        if not crypto:
            logger.warning(f"Cryptocurrency not found: {crypto_id}")
            return None
        
        # Get historical price data
        latest_prices = self.price_repo.get_latest_by_crypto(
            crypto_id,
            limit=self.preprocessor.sequence_length + 100  # Extra for technical indicators
        )
        
        if len(latest_prices) < self.min_data_points:
            logger.warning(
                f"Insufficient data for {crypto.symbol}: "
                f"{len(latest_prices)} < {self.min_data_points}"
            )
            return None
        
        # Reverse to chronological order
        latest_prices = list(reversed(latest_prices))
        
        # Preprocess data
        preprocessed = self.preprocessor.preprocess(
            latest_prices,
            fit=False,  # Use fitted scaler from training
            create_splits=False
        )
        
        X = preprocessed['X']
        if len(X) == 0:
            logger.warning(f"Failed to create sequences for {crypto.symbol}")
            return None
        
        # Use the last sequence for prediction
        X_latest = X[-1:]  # Shape: (1, sequence_length, num_features)
        
        # Make prediction
        y_pred_normalized = self.model.predict(X_latest)
        
        # Inverse transform to get actual price
        y_pred = self.preprocessor.inverse_transform_price(y_pred_normalized)
        predicted_price = float(y_pred[0][0])
        
        # Get current price
        current_price = float(latest_prices[-1].price_usd)
        
        # Calculate predicted change percentage
        predicted_change_percent = ((predicted_price - current_price) / current_price) * 100
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            X_latest,
            y_pred_normalized,
            latest_prices
        )
        
        result = PredictionResult(
            crypto_id=crypto_id,
            symbol=crypto.symbol,
            name=crypto.name,
            current_price=Decimal(str(current_price)),
            predicted_price=Decimal(str(predicted_price)),
            predicted_change_percent=predicted_change_percent,
            confidence_score=confidence_score,
            prediction_horizon_hours=self.prediction_horizon_hours,
            timestamp=datetime.now()
        )
        
        logger.debug(
            f"Prediction for {crypto.symbol}: "
            f"current=${current_price:.2f}, "
            f"predicted=${predicted_price:.2f} "
            f"({predicted_change_percent:+.2f}%), "
            f"confidence={confidence_score:.2f}"
        )
        
        return result
    
    def predict_all_cryptos(
        self,
        crypto_ids: Optional[List[int]] = None
    ) -> List[PredictionResult]:
        """
        Generate predictions for multiple cryptocurrencies.
        
        Args:
            crypto_ids: List of cryptocurrency IDs (None = all tracked cryptos)
        
        Returns:
            List of PredictionResult objects
        """
        if crypto_ids is None:
            # Get all tracked cryptocurrencies
            cryptos = self.crypto_repo.get_all()
            crypto_ids = [c.id for c in cryptos]
        
        logger.info(f"Generating predictions for {len(crypto_ids)} cryptocurrencies")
        
        predictions = []
        for crypto_id in crypto_ids:
            try:
                result = self.predict_single_crypto(crypto_id)
                if result:
                    predictions.append(result)
            except Exception as e:
                logger.error(f"Error predicting crypto_id={crypto_id}: {e}", exc_info=True)
        
        logger.info(f"Generated {len(predictions)} predictions")
        return predictions
    
    def predict_top_performers(
        self,
        limit: int = 20,
        crypto_ids: Optional[List[int]] = None
    ) -> List[PredictionResult]:
        """
        Generate predictions and return top performers.
        
        Args:
            limit: Number of top performers to return (default: 20)
            crypto_ids: List of cryptocurrency IDs to consider (None = all)
        
        Returns:
            List of top PredictionResult objects sorted by predicted performance
        """
        # Generate predictions for all cryptos
        predictions = self.predict_all_cryptos(crypto_ids)
        
        if not predictions:
            logger.warning("No predictions generated")
            return []
        
        # Sort by predicted change percentage (descending)
        predictions.sort(key=lambda p: p.predicted_change_percent, reverse=True)
        
        # Get top performers
        top_performers = predictions[:limit]
        
        logger.info(
            f"Top {len(top_performers)} performers: "
            f"{', '.join([f'{p.symbol}({p.predicted_change_percent:+.2f}%)' for p in top_performers[:5]])}"
        )
        
        return top_performers
    
    def cache_predictions(
        self,
        predictions: List[PredictionResult]
    ) -> int:
        """
        Cache predictions to database.
        
        Args:
            predictions: List of PredictionResult objects
        
        Returns:
            Number of predictions cached
        """
        if not predictions:
            return 0
        
        prediction_records = []
        for pred in predictions:
            prediction_records.append({
                'crypto_id': pred.crypto_id,
                'prediction_date': pred.timestamp,
                'predicted_price': pred.predicted_price,
                'confidence_score': Decimal(str(pred.confidence_score)),
                'prediction_horizon_hours': pred.prediction_horizon_hours
            })
        
        count = self.prediction_repo.bulk_create(prediction_records)
        self.session.commit()
        
        logger.info(f"Cached {count} predictions to database")
        return count
    
    def get_cached_predictions(
        self,
        limit: int = 20,
        max_age_hours: int = 24
    ) -> List[PredictionResult]:
        """
        Get cached predictions from database.
        
        Args:
            limit: Number of predictions to retrieve
            max_age_hours: Maximum age of predictions in hours
        
        Returns:
            List of PredictionResult objects from cache
        """
        # Get top performers from database
        db_predictions = self.prediction_repo.get_top_performers(limit=limit)
        
        if not db_predictions:
            logger.info("No cached predictions found")
            return []
        
        # Check if predictions are fresh
        latest_prediction = db_predictions[0]
        age = datetime.now() - latest_prediction.created_at
        
        if age.total_seconds() / 3600 > max_age_hours:
            logger.info(f"Cached predictions are stale ({age.total_seconds() / 3600:.1f}h old)")
            return []
        
        # Convert to PredictionResult objects
        results = []
        for pred in db_predictions:
            crypto = self.crypto_repo.get_by_id(pred.crypto_id)
            if not crypto:
                continue
            
            # Get current price
            latest_price = self.price_repo.get_latest_by_crypto(pred.crypto_id, limit=1)
            current_price = latest_price[0].price_usd if latest_price else pred.predicted_price
            
            # Calculate predicted change
            predicted_change_percent = (
                (float(pred.predicted_price) - float(current_price)) / float(current_price)
            ) * 100
            
            results.append(PredictionResult(
                crypto_id=pred.crypto_id,
                symbol=crypto.symbol,
                name=crypto.name,
                current_price=current_price,
                predicted_price=pred.predicted_price,
                predicted_change_percent=predicted_change_percent,
                confidence_score=float(pred.confidence_score) if pred.confidence_score else 0.0,
                prediction_horizon_hours=pred.prediction_horizon_hours,
                timestamp=pred.prediction_date
            ))
        
        logger.info(f"Retrieved {len(results)} cached predictions")
        return results
    
    def _calculate_confidence(
        self,
        X: np.ndarray,
        y_pred: np.ndarray,
        price_history: List[PriceHistory]
    ) -> float:
        """
        Calculate confidence score for prediction.
        
        Confidence is based on:
        - Data quality (completeness, recency)
        - Price volatility (lower volatility = higher confidence)
        - Sequence consistency
        
        Args:
            X: Input sequence
            y_pred: Predicted value
            price_history: Historical price data
        
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 1.0
        
        # Factor 1: Data completeness (0.0 - 0.3)
        data_completeness = min(len(price_history) / self.min_data_points, 1.0)
        confidence *= (0.7 + 0.3 * data_completeness)
        
        # Factor 2: Price volatility (0.0 - 0.3)
        recent_prices = [float(p.price_usd) for p in price_history[-50:]]
        if len(recent_prices) > 1:
            volatility = np.std(recent_prices) / np.mean(recent_prices)
            # Lower volatility = higher confidence
            volatility_factor = max(0.0, 1.0 - volatility * 5)  # Scale volatility
            confidence *= (0.7 + 0.3 * volatility_factor)
        
        # Factor 3: Prediction magnitude (0.0 - 0.2)
        # Extreme predictions get lower confidence
        pred_value = float(y_pred[0][0])
        if 0.1 < pred_value < 0.9:  # Normalized range
            confidence *= 1.0
        else:
            confidence *= 0.8
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def generate_and_cache_predictions(
        self,
        limit: int = 20,
        crypto_ids: Optional[List[int]] = None
    ) -> List[PredictionResult]:
        """
        Generate predictions and cache them to database.
        
        Args:
            limit: Number of top performers to return
            crypto_ids: List of cryptocurrency IDs to consider
        
        Returns:
            List of top PredictionResult objects
        """
        # Generate predictions
        top_performers = self.predict_top_performers(limit=limit, crypto_ids=crypto_ids)
        
        # Cache to database
        if top_performers:
            self.cache_predictions(top_performers)
        
        return top_performers

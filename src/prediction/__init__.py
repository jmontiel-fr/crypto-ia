"""
Prediction module for cryptocurrency price forecasting.

This module provides:
- Data preprocessing pipeline with technical indicators
- LSTM/GRU model architecture
- Model training pipeline with early stopping and checkpointing
- Prediction engine for generating forecasts
- Market tendency classification
"""

from src.prediction.data_preprocessor import DataPreprocessor
from src.prediction.lstm_model import LSTMModel, GRUModel, create_model
from src.prediction.model_trainer import ModelTrainer, TrainingScheduler
from src.prediction.prediction_engine import PredictionEngine, PredictionResult
from src.prediction.market_tendency_classifier import (
    MarketTendencyClassifier,
    TendencyResult,
    TendencyType
)

__all__ = [
    'DataPreprocessor',
    'LSTMModel',
    'GRUModel',
    'create_model',
    'ModelTrainer',
    'TrainingScheduler',
    'PredictionEngine',
    'PredictionResult',
    'MarketTendencyClassifier',
    'TendencyResult',
    'TendencyType',
]

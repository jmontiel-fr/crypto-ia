"""
LSTM/GRU model architecture for cryptocurrency price prediction.
Implements deep learning models using TensorFlow/Keras.
"""

import logging
import os
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks

logger = logging.getLogger(__name__)


class LSTMModel:
    """
    LSTM-based model for time series prediction.
    
    Architecture:
    - 2-3 LSTM layers with 64-128 units
    - Dropout layers (0.2-0.3) for regularization
    - Dense output layer for price prediction
    """
    
    def __init__(
        self,
        sequence_length: int = 168,
        num_features: int = 10,
        lstm_units: list = None,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        model_type: str = 'LSTM'
    ):
        """
        Initialize LSTM model.
        
        Args:
            sequence_length: Number of time steps in input sequences
            num_features: Number of features per time step
            lstm_units: List of units for each LSTM layer (default: [128, 64, 32])
            dropout_rate: Dropout rate for regularization (default: 0.2)
            learning_rate: Learning rate for optimizer (default: 0.001)
            model_type: Type of recurrent layer ('LSTM' or 'GRU')
        """
        self.sequence_length = sequence_length
        self.num_features = num_features
        self.lstm_units = lstm_units or [128, 64, 32]
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.model_type = model_type.upper()
        
        self.model: Optional[keras.Model] = None
        self.history: Optional[Dict[str, Any]] = None
        
        logger.info(
            f"Initialized {self.model_type}Model: "
            f"sequence_length={sequence_length}, "
            f"num_features={num_features}, "
            f"units={self.lstm_units}"
        )
    
    def build_model(self) -> keras.Model:
        """
        Build the LSTM/GRU model architecture.
        
        Returns:
            Compiled Keras model
        """
        model = models.Sequential(name=f'{self.model_type}_Price_Predictor')
        
        # Input layer
        model.add(layers.Input(shape=(self.sequence_length, self.num_features)))
        
        # Recurrent layers
        for i, units in enumerate(self.lstm_units):
            # Return sequences for all layers except the last
            return_sequences = (i < len(self.lstm_units) - 1)
            
            if self.model_type == 'LSTM':
                model.add(layers.LSTM(
                    units=units,
                    return_sequences=return_sequences,
                    name=f'lstm_{i+1}'
                ))
            elif self.model_type == 'GRU':
                model.add(layers.GRU(
                    units=units,
                    return_sequences=return_sequences,
                    name=f'gru_{i+1}'
                ))
            else:
                raise ValueError(f"Invalid model_type: {self.model_type}. Must be 'LSTM' or 'GRU'")
            
            # Dropout for regularization
            model.add(layers.Dropout(self.dropout_rate, name=f'dropout_{i+1}'))
        
        # Output layer (single value prediction)
        model.add(layers.Dense(1, activation='linear', name='output'))
        
        # Compile model
        optimizer = keras.optimizers.Adam(learning_rate=self.learning_rate)
        model.compile(
            optimizer=optimizer,
            loss='mean_squared_error',
            metrics=['mean_absolute_error', 'mean_absolute_percentage_error']
        )
        
        self.model = model
        logger.info(f"Built {self.model_type} model with {model.count_params()} parameters")
        
        return model
    
    def get_model(self) -> keras.Model:
        """
        Get the model, building it if necessary.
        
        Returns:
            Keras model
        """
        if self.model is None:
            self.build_model()
        return self.model
    
    def summary(self) -> None:
        """Print model summary."""
        if self.model is None:
            self.build_model()
        self.model.summary()
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on input data.
        
        Args:
            X: Input sequences of shape (num_samples, sequence_length, num_features)
        
        Returns:
            Predictions of shape (num_samples, 1)
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        predictions = self.model.predict(X, verbose=0)
        logger.debug(f"Made predictions for {len(X)} samples")
        
        return predictions
    
    def save_model(self, filepath: str) -> None:
        """
        Save model to file.
        
        Args:
            filepath: Path to save the model (should end with .keras or .h5)
        """
        if self.model is None:
            raise ValueError("No model to save. Build and train model first.")
        
        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        self.model.save(filepath)
        logger.info(f"Saved model to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load model from file.
        
        Args:
            filepath: Path to the saved model file
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        self.model = keras.models.load_model(filepath)
        logger.info(f"Loaded model from {filepath}")
    
    def save_weights(self, filepath: str) -> None:
        """
        Save model weights to file.
        
        Args:
            filepath: Path to save the weights
        """
        if self.model is None:
            raise ValueError("No model to save. Build model first.")
        
        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        self.model.save_weights(filepath)
        logger.info(f"Saved model weights to {filepath}")
    
    def load_weights(self, filepath: str) -> None:
        """
        Load model weights from file.
        
        Args:
            filepath: Path to the saved weights file
        """
        if self.model is None:
            self.build_model()
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Weights file not found: {filepath}")
        
        self.model.load_weights(filepath)
        logger.info(f"Loaded model weights from {filepath}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get model configuration.
        
        Returns:
            Dictionary with model configuration
        """
        return {
            'sequence_length': self.sequence_length,
            'num_features': self.num_features,
            'lstm_units': self.lstm_units,
            'dropout_rate': self.dropout_rate,
            'learning_rate': self.learning_rate,
            'model_type': self.model_type
        }
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LSTMModel':
        """
        Create model from configuration.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            LSTMModel instance
        """
        return cls(
            sequence_length=config['sequence_length'],
            num_features=config['num_features'],
            lstm_units=config['lstm_units'],
            dropout_rate=config['dropout_rate'],
            learning_rate=config['learning_rate'],
            model_type=config['model_type']
        )


class GRUModel(LSTMModel):
    """
    GRU-based model for time series prediction.
    Inherits from LSTMModel with model_type='GRU'.
    """
    
    def __init__(
        self,
        sequence_length: int = 168,
        num_features: int = 10,
        gru_units: list = None,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001
    ):
        """
        Initialize GRU model.
        
        Args:
            sequence_length: Number of time steps in input sequences
            num_features: Number of features per time step
            gru_units: List of units for each GRU layer (default: [128, 64, 32])
            dropout_rate: Dropout rate for regularization (default: 0.2)
            learning_rate: Learning rate for optimizer (default: 0.001)
        """
        super().__init__(
            sequence_length=sequence_length,
            num_features=num_features,
            lstm_units=gru_units,
            dropout_rate=dropout_rate,
            learning_rate=learning_rate,
            model_type='GRU'
        )


def create_model(
    model_type: str = 'LSTM',
    sequence_length: int = 168,
    num_features: int = 10,
    **kwargs
) -> LSTMModel:
    """
    Factory function to create LSTM or GRU model.
    
    Args:
        model_type: Type of model ('LSTM' or 'GRU')
        sequence_length: Number of time steps in input sequences
        num_features: Number of features per time step
        **kwargs: Additional arguments for model initialization
    
    Returns:
        LSTMModel or GRUModel instance
    """
    model_type = model_type.upper()
    
    if model_type == 'LSTM':
        return LSTMModel(
            sequence_length=sequence_length,
            num_features=num_features,
            model_type='LSTM',
            **kwargs
        )
    elif model_type == 'GRU':
        return GRUModel(
            sequence_length=sequence_length,
            num_features=num_features,
            **kwargs
        )
    else:
        raise ValueError(f"Invalid model_type: {model_type}. Must be 'LSTM' or 'GRU'")

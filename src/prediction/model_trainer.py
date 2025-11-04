"""
Model training pipeline for LSTM/GRU models.
Handles training orchestration, validation, and model versioning.
"""

import logging
import os
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

import numpy as np
from tensorflow import keras
from tensorflow.keras import callbacks

from src.prediction.lstm_model import LSTMModel, create_model

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Orchestrates model training with early stopping, checkpointing, and metrics tracking.
    """
    
    def __init__(
        self,
        model: LSTMModel,
        model_dir: str = 'models',
        model_name: Optional[str] = None
    ):
        """
        Initialize model trainer.
        
        Args:
            model: LSTMModel or GRUModel instance
            model_dir: Directory to save models and artifacts
            model_name: Name for the model (default: auto-generated with timestamp)
        """
        self.model = model
        self.model_dir = Path(model_dir)
        self.model_name = model_name or f"{model.model_type.lower()}_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create model directory
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Training history
        self.history: Optional[Dict[str, Any]] = None
        self.best_model_path: Optional[str] = None
        
        logger.info(f"Initialized ModelTrainer for {self.model_name}")
    
    def create_callbacks(
        self,
        patience: int = 10,
        min_delta: float = 0.0001,
        monitor: str = 'val_loss',
        restore_best_weights: bool = True
    ) -> list:
        """
        Create training callbacks.
        
        Args:
            patience: Number of epochs with no improvement before stopping
            min_delta: Minimum change to qualify as improvement
            monitor: Metric to monitor for early stopping
            restore_best_weights: Whether to restore best weights after training
        
        Returns:
            List of Keras callbacks
        """
        # Checkpoint path
        checkpoint_path = self.model_dir / self.model_name / 'checkpoints' / 'best_model.keras'
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.best_model_path = str(checkpoint_path)
        
        callback_list = [
            # Early stopping
            callbacks.EarlyStopping(
                monitor=monitor,
                patience=patience,
                min_delta=min_delta,
                restore_best_weights=restore_best_weights,
                verbose=1
            ),
            
            # Model checkpoint
            callbacks.ModelCheckpoint(
                filepath=str(checkpoint_path),
                monitor=monitor,
                save_best_only=True,
                verbose=1
            ),
            
            # Reduce learning rate on plateau
            callbacks.ReduceLROnPlateau(
                monitor=monitor,
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            ),
            
            # TensorBoard logging
            callbacks.TensorBoard(
                log_dir=str(self.model_dir / self.model_name / 'logs'),
                histogram_freq=1
            )
        ]
        
        logger.debug(f"Created {len(callback_list)} training callbacks")
        return callback_list
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        patience: int = 10,
        verbose: int = 1
    ) -> Dict[str, Any]:
        """
        Train the model.
        
        Args:
            X_train: Training input sequences
            y_train: Training target values
            X_val: Validation input sequences
            y_val: Validation target values
            epochs: Maximum number of training epochs
            batch_size: Batch size for training
            patience: Early stopping patience
            verbose: Verbosity level (0, 1, or 2)
        
        Returns:
            Training history dictionary
        """
        logger.info(f"Starting training: epochs={epochs}, batch_size={batch_size}")
        logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")
        
        # Get or build model
        model = self.model.get_model()
        
        # Create callbacks
        callback_list = self.create_callbacks(patience=patience)
        
        # Train model
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callback_list,
            verbose=verbose
        )
        
        self.history = history.history
        
        # Log final metrics
        final_loss = history.history['loss'][-1]
        final_val_loss = history.history['val_loss'][-1]
        logger.info(f"Training completed: final_loss={final_loss:.6f}, final_val_loss={final_val_loss:.6f}")
        
        return self.history
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model on test data.
        
        Args:
            X_test: Test input sequences
            y_test: Test target values
        
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Evaluating model on {len(X_test)} test samples")
        
        model = self.model.get_model()
        
        # Get predictions
        y_pred = model.predict(X_test, verbose=0)
        
        # Calculate metrics
        metrics = self.calculate_metrics(y_test, y_pred)
        
        logger.info(f"Evaluation metrics: {metrics}")
        return metrics
    
    def calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate evaluation metrics.
        
        Args:
            y_true: True target values
            y_pred: Predicted values
        
        Returns:
            Dictionary with MAE, RMSE, MAPE
        """
        # Flatten arrays if needed
        y_true = y_true.flatten()
        y_pred = y_pred.flatten()
        
        # Mean Absolute Error
        mae = np.mean(np.abs(y_true - y_pred))
        
        # Root Mean Squared Error
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        
        # Mean Absolute Percentage Error
        # Avoid division by zero
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else 0.0
        
        # R-squared
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'mape': float(mape),
            'r2': float(r2)
        }
    
    def save_model_artifacts(
        self,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save model and associated artifacts.
        
        Args:
            version: Model version string (default: timestamp)
            metadata: Additional metadata to save
        
        Returns:
            Path to saved model directory
        """
        version = version or datetime.now().strftime('%Y%m%d_%H%M%S')
        version_dir = self.model_dir / self.model_name / f'v_{version}'
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = version_dir / 'model.keras'
        self.model.save_model(str(model_path))
        
        # Save model configuration
        config_path = version_dir / 'config.json'
        config = self.model.get_config()
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Save training history
        if self.history:
            history_path = version_dir / 'history.json'
            with open(history_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        
        # Save metadata
        metadata = metadata or {}
        metadata.update({
            'model_name': self.model_name,
            'version': version,
            'created_at': datetime.now().isoformat(),
            'model_type': self.model.model_type
        })
        
        metadata_path = version_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved model artifacts to {version_dir}")
        return str(version_dir)
    
    @staticmethod
    def load_model_artifacts(model_path: str) -> Tuple[LSTMModel, Dict[str, Any]]:
        """
        Load model and metadata from saved artifacts.
        
        Args:
            model_path: Path to model directory
        
        Returns:
            Tuple of (LSTMModel instance, metadata dictionary)
        """
        model_dir = Path(model_path)
        
        # Load configuration
        config_path = model_dir / 'config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create model from config
        model = LSTMModel.from_config(config)
        
        # Load model weights
        keras_model_path = model_dir / 'model.keras'
        model.load_model(str(keras_model_path))
        
        # Load metadata
        metadata_path = model_dir / 'metadata.json'
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Loaded model from {model_path}")
        return model, metadata
    
    def get_latest_version(self) -> Optional[str]:
        """
        Get the latest model version.
        
        Returns:
            Path to latest model version or None
        """
        model_path = self.model_dir / self.model_name
        if not model_path.exists():
            return None
        
        # Find all version directories
        version_dirs = [d for d in model_path.iterdir() if d.is_dir() and d.name.startswith('v_')]
        
        if not version_dirs:
            return None
        
        # Sort by creation time and get latest
        latest = max(version_dirs, key=lambda d: d.stat().st_mtime)
        return str(latest)


class TrainingScheduler:
    """
    Manages periodic model retraining.
    """
    
    def __init__(self, schedule_config: Optional[Dict[str, Any]] = None):
        """
        Initialize training scheduler.
        
        Args:
            schedule_config: Configuration for training schedule
        """
        self.schedule_config = schedule_config or {}
        logger.info("Initialized TrainingScheduler")
    
    def should_retrain(self, last_training_time: datetime) -> bool:
        """
        Determine if model should be retrained.
        
        Args:
            last_training_time: Timestamp of last training
        
        Returns:
            True if retraining is needed
        """
        # Default: retrain weekly
        retrain_interval_days = self.schedule_config.get('retrain_interval_days', 7)
        
        days_since_training = (datetime.now() - last_training_time).days
        
        should_retrain = days_since_training >= retrain_interval_days
        
        if should_retrain:
            logger.info(f"Retraining needed: {days_since_training} days since last training")
        
        return should_retrain
    
    def schedule_training(self, trainer: ModelTrainer, **training_kwargs) -> Dict[str, Any]:
        """
        Schedule and execute model training.
        
        Args:
            trainer: ModelTrainer instance
            **training_kwargs: Arguments for training
        
        Returns:
            Training results
        """
        logger.info("Scheduled training started")
        
        # Execute training
        history = trainer.train(**training_kwargs)
        
        # Save model artifacts
        version_path = trainer.save_model_artifacts()
        
        return {
            'history': history,
            'version_path': version_path,
            'timestamp': datetime.now().isoformat()
        }

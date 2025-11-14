"""
Incremental training system for LSTM/GRU models.
Supports both full retraining and incremental updates.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from sqlalchemy.orm import Session

from src.data.database import session_scope
from src.data.repositories import CryptoRepository, PriceHistoryRepository
from src.prediction.lstm_model import create_model
from src.prediction.data_preprocessor import DataPreprocessor
from src.prediction.model_trainer import ModelTrainer
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """
    Manages incremental and full training for cryptocurrency models.
    """
    
    def __init__(self, config: Config):
        """
        Initialize incremental trainer.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.model_dir = Path("models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initialized IncrementalTrainer")
    
    def incremental_update(
        self,
        crypto_symbols: Optional[List[str]] = None,
        hours_back: int = 6,
        epochs: int = 5
    ) -> Dict[str, Any]:
        """
        Perform incremental training update on new data.
        
        Args:
            crypto_symbols: List of crypto symbols to update (None = all)
            hours_back: Hours of new data to train on
            epochs: Number of training epochs
        
        Returns:
            Dictionary with update results
        """
        start_time = time.time()
        logger.info(f"Starting incremental update: {hours_back}h back, {epochs} epochs")
        
        results = {
            'total_cryptos': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'duration_seconds': 0,
            'details': []
        }
        
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            price_repo = PriceHistoryRepository(session)
            
            # Get cryptos to update
            if crypto_symbols is None:
                cryptos = crypto_repo.get_top_by_market_cap(self.config.top_n_cryptos)
                crypto_symbols = [c.symbol for c in cryptos]
            
            results['total_cryptos'] = len(crypto_symbols)
            
            for symbol in crypto_symbols:
                try:
                    crypto = crypto_repo.get_by_symbol(symbol)
                    if not crypto:
                        logger.warning(f"{symbol}: Not found in database, skipping")
                        results['skipped'] += 1
                        continue
                    
                    # Check if model exists
                    model_path = self.model_dir / f"{symbol}_latest.keras"
                    if not model_path.exists():
                        logger.warning(f"{symbol}: No existing model, skipping incremental update")
                        results['skipped'] += 1
                        continue
                    
                    # Get new data
                    end_time = datetime.now()
                    start_time_data = end_time - timedelta(hours=hours_back)
                    
                    new_prices = price_repo.get_by_crypto_and_time_range(
                        crypto.id,
                        start_time_data,
                        end_time
                    )
                    
                    if len(new_prices) < 10:
                        logger.warning(f"{symbol}: Insufficient new data ({len(new_prices)} records)")
                        results['skipped'] += 1
                        continue
                    
                    # Load existing model
                    model = create_model(
                        model_type=self.config.model_type,
                        sequence_length=self.config.sequence_length
                    )
                    model.load_model(str(model_path))
                    
                    # Prepare data
                    preprocessor = DataPreprocessor(sequence_length=self.config.sequence_length)
                    
                    # Load scaler from training
                    scaler_path = self.model_dir / f"{symbol}_scaler.pkl"
                    if scaler_path.exists():
                        import pickle
                        with open(scaler_path, 'rb') as f:
                            preprocessor.scaler = pickle.load(f)
                    
                    # Preprocess new data
                    processed = preprocessor.preprocess(
                        new_prices,
                        fit=False,  # Use existing scaler
                        create_splits=False
                    )
                    
                    if processed is None or processed['X'] is None:
                        logger.warning(f"{symbol}: Preprocessing failed")
                        results['failed'] += 1
                        continue
                    
                    X = processed['X']
                    y = processed['y']
                    
                    if len(X) < 5:
                        logger.warning(f"{symbol}: Too few sequences ({len(X)})")
                        results['skipped'] += 1
                        continue
                    
                    # Incremental training
                    trainer = ModelTrainer(model, model_dir=str(self.model_dir))
                    
                    # Train with fewer epochs
                    history = model.model.fit(
                        X, y,
                        epochs=epochs,
                        batch_size=16,
                        verbose=0,
                        validation_split=0.2
                    )
                    
                    # Save updated model
                    model.save_model(str(model_path))
                    
                    final_loss = history.history['loss'][-1]
                    logger.info(f"{symbol}: Incremental update complete (loss={final_loss:.6f})")
                    
                    results['successful'] += 1
                    results['details'].append({
                        'symbol': symbol,
                        'status': 'success',
                        'samples': len(X),
                        'loss': float(final_loss)
                    })
                    
                except Exception as e:
                    logger.error(f"{symbol}: Incremental update failed: {e}")
                    results['failed'] += 1
                    results['details'].append({
                        'symbol': symbol,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        results['duration_seconds'] = time.time() - start_time
        
        logger.info(
            f"Incremental update complete: "
            f"{results['successful']}/{results['total_cryptos']} successful, "
            f"{results['duration_seconds']:.1f}s"
        )
        
        return results
    
    def full_retrain(
        self,
        crypto_symbols: Optional[List[str]] = None,
        months_back: int = 6,
        epochs: int = 50,
        batch_size: int = 25
    ) -> Dict[str, Any]:
        """
        Perform full retraining on all data.
        
        Args:
            crypto_symbols: List of crypto symbols to train (None = all)
            months_back: Months of historical data to use
            epochs: Number of training epochs
            batch_size: Number of cryptos to train in each batch
        
        Returns:
            Dictionary with training results
        """
        start_time = time.time()
        logger.info(f"Starting full retraining: {months_back} months, {epochs} epochs")
        
        results = {
            'total_cryptos': 0,
            'successful': 0,
            'failed': 0,
            'duration_seconds': 0,
            'batches': []
        }
        
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            price_repo = PriceHistoryRepository(session)
            
            # Get cryptos to train
            if crypto_symbols is None:
                cryptos = crypto_repo.get_top_by_market_cap(self.config.top_n_cryptos)
                crypto_symbols = [c.symbol for c in cryptos]
            
            results['total_cryptos'] = len(crypto_symbols)
            
            # Train in batches
            for i in range(0, len(crypto_symbols), batch_size):
                batch = crypto_symbols[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(crypto_symbols) + batch_size - 1) // batch_size
                
                logger.info(f"Training batch {batch_num}/{total_batches}: {len(batch)} cryptos")
                
                batch_results = self._train_batch(
                    batch,
                    months_back,
                    epochs,
                    session
                )
                
                results['successful'] += batch_results['successful']
                results['failed'] += batch_results['failed']
                results['batches'].append(batch_results)
        
        results['duration_seconds'] = time.time() - start_time
        
        logger.info(
            f"Full retraining complete: "
            f"{results['successful']}/{results['total_cryptos']} successful, "
            f"{results['duration_seconds']/3600:.1f}h"
        )
        
        return results
    
    def _train_batch(
        self,
        crypto_symbols: List[str],
        months_back: int,
        epochs: int,
        session: Session
    ) -> Dict[str, Any]:
        """Train a batch of cryptocurrencies."""
        batch_start = time.time()
        
        results = {
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        crypto_repo = CryptoRepository(session)
        price_repo = PriceHistoryRepository(session)
        
        for symbol in crypto_symbols:
            try:
                crypto = crypto_repo.get_by_symbol(symbol)
                if not crypto:
                    logger.warning(f"{symbol}: Not found in database")
                    results['failed'] += 1
                    continue
                
                # Get historical data
                end_time = datetime.now()
                start_time_data = end_time - timedelta(days=months_back * 30)
                
                prices = price_repo.get_by_crypto_and_time_range(
                    crypto.id,
                    start_time_data,
                    end_time
                )
                
                if len(prices) < 500:
                    logger.warning(f"{symbol}: Insufficient data ({len(prices)} records)")
                    results['failed'] += 1
                    continue
                
                # Preprocess data
                preprocessor = DataPreprocessor(sequence_length=self.config.sequence_length)
                processed = preprocessor.preprocess(prices, fit=True, create_splits=True)
                
                if processed is None:
                    logger.warning(f"{symbol}: Preprocessing failed")
                    results['failed'] += 1
                    continue
                
                # Create and train model
                model = create_model(
                    model_type=self.config.model_type,
                    sequence_length=self.config.sequence_length
                )
                model.build_model()
                
                trainer = ModelTrainer(model, model_dir=str(self.model_dir))
                
                history = trainer.train(
                    X_train=processed['X_train'],
                    y_train=processed['y_train'],
                    X_val=processed['X_val'],
                    y_val=processed['y_val'],
                    epochs=epochs,
                    batch_size=32,
                    patience=10,
                    verbose=0
                )
                
                # Save model and scaler
                model_path = self.model_dir / f"{symbol}_latest.keras"
                model.save_model(str(model_path))
                
                scaler_path = self.model_dir / f"{symbol}_scaler.pkl"
                import pickle
                with open(scaler_path, 'wb') as f:
                    pickle.dump(preprocessor.scaler, f)
                
                final_loss = history['loss'][-1]
                logger.info(f"{symbol}: Training complete (loss={final_loss:.6f})")
                
                results['successful'] += 1
                results['details'].append({
                    'symbol': symbol,
                    'status': 'success',
                    'samples': len(processed['X_train']),
                    'loss': float(final_loss)
                })
                
            except Exception as e:
                logger.error(f"{symbol}: Training failed: {e}")
                results['failed'] += 1
                results['details'].append({
                    'symbol': symbol,
                    'status': 'failed',
                    'error': str(e)
                })
        
        results['duration_seconds'] = time.time() - batch_start
        
        return results

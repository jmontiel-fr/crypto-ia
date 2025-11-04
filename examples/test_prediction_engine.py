"""
Example script demonstrating the prediction engine usage.

This script shows how to:
1. Load historical price data
2. Preprocess data with technical indicators
3. Create and train an LSTM model
4. Generate predictions for cryptocurrencies
5. Classify market tendency
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.database import get_session
from src.data.repositories import CryptoRepository, PriceHistoryRepository
from src.prediction import (
    DataPreprocessor,
    create_model,
    ModelTrainer,
    PredictionEngine,
    MarketTendencyClassifier
)


def example_preprocessing():
    """Example: Data preprocessing with technical indicators."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Data Preprocessing")
    print("="*60)
    
    session = get_session()
    
    try:
        # Get a cryptocurrency
        crypto_repo = CryptoRepository(session)
        price_repo = PriceHistoryRepository(session)
        
        crypto = crypto_repo.get_by_symbol('BTC')
        if not crypto:
            print("BTC not found in database. Please run data collection first.")
            return
        
        # Get historical data (last 30 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        price_history = price_repo.get_by_crypto_and_time_range(
            crypto.id,
            start_time,
            end_time
        )
        
        print(f"\nLoaded {len(price_history)} price records for {crypto.symbol}")
        
        # Preprocess data
        preprocessor = DataPreprocessor(sequence_length=168)
        result = preprocessor.preprocess(
            price_history,
            fit=True,
            create_splits=True
        )
        
        print(f"\nPreprocessing results:")
        print(f"  - Total sequences: {len(result['X'])}")
        print(f"  - Training samples: {len(result['X_train'])}")
        print(f"  - Validation samples: {len(result['X_val'])}")
        print(f"  - Test samples: {len(result['X_test'])}")
        print(f"  - Features per timestep: {result['X'].shape[2] if len(result['X']) > 0 else 0}")
        
        # Show feature names
        if not result['df'].empty:
            features = preprocessor.get_feature_names(result['df'])
            print(f"\nFeatures: {', '.join(features)}")
        
    finally:
        session.close()


def example_model_creation():
    """Example: Creating and building LSTM/GRU models."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Model Creation")
    print("="*60)
    
    # Create LSTM model
    print("\nCreating LSTM model...")
    lstm_model = create_model(
        model_type='LSTM',
        sequence_length=168,
        num_features=10,
        lstm_units=[128, 64, 32],
        dropout_rate=0.2,
        learning_rate=0.001
    )
    
    lstm_model.build_model()
    print("\nLSTM Model Summary:")
    lstm_model.summary()
    
    # Create GRU model
    print("\n" + "-"*60)
    print("Creating GRU model...")
    gru_model = create_model(
        model_type='GRU',
        sequence_length=168,
        num_features=10,
        gru_units=[128, 64],
        dropout_rate=0.3
    )
    
    gru_model.build_model()
    print("\nGRU Model Summary:")
    gru_model.summary()


def example_training():
    """Example: Training a model (requires sufficient data)."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Model Training")
    print("="*60)
    
    session = get_session()
    
    try:
        # Get data
        crypto_repo = CryptoRepository(session)
        price_repo = PriceHistoryRepository(session)
        
        crypto = crypto_repo.get_by_symbol('BTC')
        if not crypto:
            print("BTC not found in database.")
            return
        
        # Get historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=60)
        
        price_history = price_repo.get_by_crypto_and_time_range(
            crypto.id,
            start_time,
            end_time
        )
        
        if len(price_history) < 500:
            print(f"Insufficient data for training: {len(price_history)} records")
            print("Need at least 500 records. Please run data collection first.")
            return
        
        print(f"\nPreparing data from {len(price_history)} records...")
        
        # Preprocess
        preprocessor = DataPreprocessor(sequence_length=168)
        data = preprocessor.preprocess(price_history, fit=True, create_splits=True)
        
        if len(data['X_train']) == 0:
            print("Failed to create training sequences")
            return
        
        # Create model
        model = create_model(
            model_type='LSTM',
            sequence_length=168,
            num_features=data['X_train'].shape[2],
            lstm_units=[64, 32],
            dropout_rate=0.2
        )
        
        # Train model
        print("\nTraining model (this may take a few minutes)...")
        trainer = ModelTrainer(model, model_dir='models', model_name='btc_example')
        
        history = trainer.train(
            data['X_train'], data['y_train'],
            data['X_val'], data['y_val'],
            epochs=20,  # Reduced for example
            batch_size=32,
            patience=5,
            verbose=1
        )
        
        # Evaluate
        print("\nEvaluating model...")
        metrics = trainer.evaluate(data['X_test'], data['y_test'])
        
        print("\nTest Metrics:")
        for metric, value in metrics.items():
            print(f"  {metric.upper()}: {value:.4f}")
        
        # Save model
        version_path = trainer.save_model_artifacts(version='example_v1')
        print(f"\nModel saved to: {version_path}")
        
    finally:
        session.close()


def example_prediction():
    """Example: Generating predictions."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Generating Predictions")
    print("="*60)
    
    print("\nNote: This example requires a trained model.")
    print("Run example_training() first or load a pre-trained model.")
    print("\nExample code:")
    print("""
    session = get_session()
    
    # Load trained model
    model, metadata = ModelTrainer.load_model_artifacts('models/btc_example/v_example_v1')
    
    # Create preprocessor (must match training configuration)
    preprocessor = DataPreprocessor(sequence_length=168)
    
    # Create prediction engine
    engine = PredictionEngine(
        session=session,
        model=model,
        preprocessor=preprocessor,
        prediction_horizon_hours=24
    )
    
    # Generate predictions for top 20 performers
    top_performers = engine.predict_top_performers(limit=20)
    
    print("\\nTop 20 Predicted Performers:")
    for i, pred in enumerate(top_performers, 1):
        print(f"{i}. {pred.symbol}: {pred.predicted_change_percent:+.2f}% "
              f"(confidence: {pred.confidence_score:.2f})")
    
    # Cache predictions
    engine.cache_predictions(top_performers)
    
    session.close()
    """)


def example_market_tendency():
    """Example: Market tendency classification."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Market Tendency Classification")
    print("="*60)
    
    session = get_session()
    
    try:
        # Create classifier
        classifier = MarketTendencyClassifier(
            session=session,
            lookback_hours=24,
            top_n_cryptos=50
        )
        
        # Analyze market
        print("\nAnalyzing market tendency...")
        result = classifier.analyze_and_store()
        
        print(f"\nMarket Tendency: {result.tendency.upper()}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"\nMetrics:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
        
        # Get historical tendencies
        print("\n" + "-"*60)
        print("Recent Market Tendencies (last 7 days):")
        history = classifier.get_tendency_history(hours=168)
        
        if history:
            for i, h in enumerate(history[-10:], 1):  # Last 10 entries
                print(f"{i}. {h.timestamp.strftime('%Y-%m-%d %H:%M')}: "
                      f"{h.tendency} (confidence: {h.confidence:.2f})")
        else:
            print("No historical data available")
        
    finally:
        session.close()


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("PREDICTION ENGINE EXAMPLES")
    print("="*60)
    
    # Run examples
    example_preprocessing()
    example_model_creation()
    # example_training()  # Uncomment to run training (requires data)
    example_prediction()
    example_market_tendency()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == '__main__':
    main()

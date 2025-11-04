# Prediction Module

This module implements the LSTM/GRU-based prediction engine for cryptocurrency price forecasting.

## Components

### 1. DataPreprocessor (`data_preprocessor.py`)

Handles data preprocessing and feature engineering:

- **Price normalization** using MinMaxScaler
- **Technical indicators**: RSI, MACD, Bollinger Bands
- **Sequence generation** for time series (default: 168-hour windows)
- **Train/validation/test split** for model training

**Usage:**
```python
from src.prediction import DataPreprocessor

preprocessor = DataPreprocessor(sequence_length=168)
result = preprocessor.preprocess(price_history, fit=True, create_splits=True)

X_train = result['X_train']
y_train = result['y_train']
```

### 2. LSTMModel / GRUModel (`lstm_model.py`)

Deep learning model architecture:

- **2-3 LSTM/GRU layers** with 64-128 units
- **Dropout layers** (0.2-0.3) for regularization
- **Dense output layer** for price prediction
- **Model save/load** functionality

**Usage:**
```python
from src.prediction import create_model

model = create_model(
    model_type='LSTM',
    sequence_length=168,
    num_features=10,
    lstm_units=[128, 64, 32],
    dropout_rate=0.2
)

model.build_model()
model.summary()
```

### 3. ModelTrainer (`model_trainer.py`)

Training pipeline with:

- **Early stopping** to prevent overfitting
- **Model checkpointing** to save best weights
- **Learning rate reduction** on plateau
- **Validation metrics** (MAE, RMSE, MAPE, R²)
- **Model versioning** and artifact storage

**Usage:**
```python
from src.prediction import ModelTrainer

trainer = ModelTrainer(model, model_dir='models', model_name='btc_predictor')

history = trainer.train(
    X_train, y_train,
    X_val, y_val,
    epochs=100,
    batch_size=32,
    patience=10
)

metrics = trainer.evaluate(X_test, y_test)
version_path = trainer.save_model_artifacts(version='v1.0')
```

### 4. PredictionEngine (`prediction_engine.py`)

Main interface for generating predictions:

- **Single crypto prediction** with confidence scores
- **Batch predictions** for multiple cryptocurrencies
- **Top performers ranking** by predicted performance
- **Prediction caching** to database

**Usage:**
```python
from src.prediction import PredictionEngine

engine = PredictionEngine(
    session=db_session,
    model=trained_model,
    preprocessor=preprocessor,
    prediction_horizon_hours=24
)

# Generate predictions for top 20 performers
top_20 = engine.predict_top_performers(limit=20)

# Cache predictions to database
engine.cache_predictions(top_20)

# Get cached predictions
cached = engine.get_cached_predictions(limit=20, max_age_hours=24)
```

### 5. MarketTendencyClassifier (`market_tendency_classifier.py`)

Classifies overall market conditions:

- **Bullish**: >60% of cryptos increasing
- **Bearish**: >60% of cryptos decreasing
- **Volatile**: High price fluctuations
- **Stable**: Low volatility
- **Consolidating**: Sideways movement

**Usage:**
```python
from src.prediction import MarketTendencyClassifier

classifier = MarketTendencyClassifier(
    session=db_session,
    lookback_hours=24,
    top_n_cryptos=50
)

# Analyze and store market tendency
result = classifier.analyze_and_store()

print(f"Market is {result.tendency} (confidence: {result.confidence:.2f})")
print(f"Metrics: {result.metrics}")

# Get cached tendency
cached = classifier.get_cached_or_analyze(max_age_hours=1)
```

## Complete Workflow Example

```python
from sqlalchemy.orm import Session
from src.data.database import get_session
from src.data.repositories import PriceHistoryRepository, CryptoRepository
from src.prediction import (
    DataPreprocessor,
    create_model,
    ModelTrainer,
    PredictionEngine,
    MarketTendencyClassifier
)

# 1. Get database session
session = get_session()

# 2. Load historical data
crypto_repo = CryptoRepository(session)
price_repo = PriceHistoryRepository(session)

crypto = crypto_repo.get_by_symbol('BTC')
price_history = price_repo.get_by_crypto_and_time_range(
    crypto.id,
    start_time,
    end_time
)

# 3. Preprocess data
preprocessor = DataPreprocessor(sequence_length=168)
data = preprocessor.preprocess(price_history, fit=True, create_splits=True)

# 4. Create and train model
model = create_model(
    model_type='LSTM',
    sequence_length=168,
    num_features=data['X_train'].shape[2]
)

trainer = ModelTrainer(model, model_dir='models')
history = trainer.train(
    data['X_train'], data['y_train'],
    data['X_val'], data['y_val'],
    epochs=100,
    batch_size=32
)

# 5. Evaluate model
metrics = trainer.evaluate(data['X_test'], data['y_test'])
print(f"Test metrics: {metrics}")

# 6. Save model
version_path = trainer.save_model_artifacts(version='v1.0')

# 7. Generate predictions
engine = PredictionEngine(session, model, preprocessor)
top_performers = engine.predict_top_performers(limit=20)

for pred in top_performers[:5]:
    print(f"{pred.symbol}: {pred.predicted_change_percent:+.2f}% (confidence: {pred.confidence_score:.2f})")

# 8. Analyze market tendency
classifier = MarketTendencyClassifier(session)
tendency = classifier.analyze_and_store()
print(f"Market tendency: {tendency.tendency} (confidence: {tendency.confidence:.2f})")

session.close()
```

## Model Artifacts Structure

```
models/
└── lstm_model_20250101_120000/
    ├── v_20250101_120000/
    │   ├── model.keras          # Saved Keras model
    │   ├── config.json          # Model configuration
    │   ├── history.json         # Training history
    │   └── metadata.json        # Model metadata
    ├── checkpoints/
    │   └── best_model.keras     # Best model checkpoint
    └── logs/
        └── ...                  # TensorBoard logs
```

## Configuration

Key parameters can be configured via environment variables:

```bash
# Model configuration
MODEL_TYPE=LSTM                    # or GRU
SEQUENCE_LENGTH=168                # 7 days of hourly data
PREDICTION_HORIZON_HOURS=24        # 24-hour prediction

# Training configuration
MODEL_RETRAIN_SCHEDULE="0 2 * * 0"  # Weekly on Sunday at 2 AM
```

## Requirements

- TensorFlow >= 2.15.0
- NumPy >= 1.26.0
- Pandas >= 2.1.0
- scikit-learn >= 1.3.0
- SQLAlchemy >= 2.0.0

## Performance Metrics

The model is evaluated using:

- **MAE** (Mean Absolute Error): Average absolute difference between predicted and actual prices
- **RMSE** (Root Mean Squared Error): Square root of average squared differences
- **MAPE** (Mean Absolute Percentage Error): Average percentage error
- **R²** (R-squared): Proportion of variance explained by the model

Target performance:
- MAPE < 5% for stable markets
- MAPE < 10% for volatile markets
- R² > 0.7 for good predictions

## Notes

- Models should be retrained periodically (weekly recommended) to adapt to market changes
- Confidence scores help identify reliable predictions
- Market tendency provides context for individual predictions
- Cache predictions to reduce computation time for API requests

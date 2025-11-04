"""
Data preprocessing pipeline for LSTM/GRU prediction models.
Handles feature engineering, normalization, and sequence generation.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocesses cryptocurrency price data for time series prediction.
    
    Features:
    - Price normalization using MinMaxScaler
    - Technical indicators calculation (RSI, MACD, Bollinger Bands)
    - Sequence generation for time series windows
    - Train/validation/test split
    """
    
    def __init__(self, sequence_length: int = 168):
        """
        Initialize data preprocessor.
        
        Args:
            sequence_length: Number of time steps in each sequence (default: 168 hours = 7 days)
        """
        self.sequence_length = sequence_length
        self.price_scaler = MinMaxScaler(feature_range=(0, 1))
        self.volume_scaler = MinMaxScaler(feature_range=(0, 1))
        self.feature_scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_fitted = False
        
        logger.info(f"Initialized DataPreprocessor with sequence_length={sequence_length}")
    
    def prepare_dataframe(self, price_history: List[Any]) -> pd.DataFrame:
        """
        Convert price history records to pandas DataFrame.
        
        Args:
            price_history: List of PriceHistory model instances
        
        Returns:
            DataFrame with columns: timestamp, price_usd, volume_24h, market_cap
        """
        if not price_history:
            logger.warning("Empty price history provided")
            return pd.DataFrame()
        
        data = []
        for record in price_history:
            data.append({
                'timestamp': record.timestamp,
                'price_usd': float(record.price_usd) if record.price_usd else 0.0,
                'volume_24h': float(record.volume_24h) if record.volume_24h else 0.0,
                'market_cap': float(record.market_cap) if record.market_cap else 0.0
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        logger.debug(f"Prepared DataFrame with {len(df)} records")
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: Series of prices
            period: RSI period (default: 14)
        
        Returns:
            Series of RSI values (0-100)
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Fill NaN values with 50 (neutral)
        rsi = rsi.fillna(50)
        
        return rsi
    
    def calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Series of prices
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)
        
        Returns:
            Tuple of (MACD line, Signal line, MACD histogram)
        """
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        macd_histogram = macd_line - signal_line
        
        # Fill NaN values with 0
        macd_line = macd_line.fillna(0)
        signal_line = signal_line.fillna(0)
        macd_histogram = macd_histogram.fillna(0)
        
        return macd_line, signal_line, macd_histogram
    
    def calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: Series of prices
            period: Moving average period (default: 20)
            num_std: Number of standard deviations (default: 2.0)
        
        Returns:
            Tuple of (Middle band, Upper band, Lower band)
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        # Fill NaN values with price
        middle_band = middle_band.fillna(prices)
        upper_band = upper_band.fillna(prices)
        lower_band = lower_band.fillna(prices)
        
        return middle_band, upper_band, lower_band
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to DataFrame.
        
        Args:
            df: DataFrame with price_usd column
        
        Returns:
            DataFrame with additional technical indicator columns
        """
        if df.empty or 'price_usd' not in df.columns:
            logger.warning("Cannot calculate technical indicators: invalid DataFrame")
            return df
        
        # RSI
        df['rsi'] = self.calculate_rsi(df['price_usd'])
        
        # MACD
        macd_line, signal_line, macd_histogram = self.calculate_macd(df['price_usd'])
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = macd_histogram
        
        # Bollinger Bands
        bb_middle, bb_upper, bb_lower = self.calculate_bollinger_bands(df['price_usd'])
        df['bb_middle'] = bb_middle
        df['bb_upper'] = bb_upper
        df['bb_lower'] = bb_lower
        
        # Bollinger Band Width (normalized)
        df['bb_width'] = (bb_upper - bb_lower) / bb_middle
        df['bb_width'] = df['bb_width'].fillna(0)
        
        # Price position within Bollinger Bands
        df['bb_position'] = (df['price_usd'] - bb_lower) / (bb_upper - bb_lower)
        df['bb_position'] = df['bb_position'].fillna(0.5)
        
        logger.debug("Added technical indicators to DataFrame")
        return df
    
    def normalize_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Normalize features using MinMaxScaler.
        
        Args:
            df: DataFrame with features
            fit: Whether to fit the scaler (True for training, False for inference)
        
        Returns:
            DataFrame with normalized features
        """
        if df.empty:
            return df
        
        df_normalized = df.copy()
        
        # Normalize price
        if 'price_usd' in df.columns:
            price_values = df[['price_usd']].values
            if fit:
                df_normalized['price_usd'] = self.price_scaler.fit_transform(price_values)
            else:
                df_normalized['price_usd'] = self.price_scaler.transform(price_values)
        
        # Normalize volume
        if 'volume_24h' in df.columns:
            volume_values = df[['volume_24h']].values
            if fit:
                df_normalized['volume_24h'] = self.volume_scaler.fit_transform(volume_values)
            else:
                df_normalized['volume_24h'] = self.volume_scaler.transform(volume_values)
        
        # Normalize other features (technical indicators)
        feature_columns = [col for col in df.columns if col not in ['timestamp', 'price_usd', 'volume_24h', 'market_cap']]
        if feature_columns:
            feature_values = df[feature_columns].values
            if fit:
                normalized_features = self.feature_scaler.fit_transform(feature_values)
            else:
                normalized_features = self.feature_scaler.transform(feature_values)
            
            for i, col in enumerate(feature_columns):
                df_normalized[col] = normalized_features[:, i]
        
        if fit:
            self.is_fitted = True
        
        logger.debug(f"Normalized features (fit={fit})")
        return df_normalized
    
    def create_sequences(
        self,
        df: pd.DataFrame,
        target_column: str = 'price_usd'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time series prediction.
        
        Args:
            df: DataFrame with normalized features
            target_column: Column to predict (default: 'price_usd')
        
        Returns:
            Tuple of (X sequences, y targets)
            X shape: (num_sequences, sequence_length, num_features)
            y shape: (num_sequences,)
        """
        if df.empty or len(df) < self.sequence_length + 1:
            logger.warning(f"Insufficient data for sequence creation: {len(df)} records")
            return np.array([]), np.array([])
        
        # Select feature columns (exclude timestamp)
        feature_columns = [col for col in df.columns if col != 'timestamp']
        data = df[feature_columns].values
        
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length):
            # Input sequence
            X.append(data[i:i + self.sequence_length])
            
            # Target (next price)
            target_idx = feature_columns.index(target_column)
            y.append(data[i + self.sequence_length, target_idx])
        
        X = np.array(X)
        y = np.array(y)
        
        logger.debug(f"Created sequences: X shape={X.shape}, y shape={y.shape}")
        return X, y
    
    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            X: Input sequences
            y: Target values
            train_ratio: Ratio of training data (default: 0.7)
            val_ratio: Ratio of validation data (default: 0.15)
            test_ratio: Ratio of test data (default: 0.15)
        
        Returns:
            Tuple of (X_train, y_train, X_val, y_val, X_test, y_test)
        """
        if len(X) == 0:
            logger.warning("Cannot split empty data")
            return np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([])
        
        # Validate ratios
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"
        
        n_samples = len(X)
        train_size = int(n_samples * train_ratio)
        val_size = int(n_samples * val_ratio)
        
        # Split sequentially (important for time series)
        X_train = X[:train_size]
        y_train = y[:train_size]
        
        X_val = X[train_size:train_size + val_size]
        y_val = y[train_size:train_size + val_size]
        
        X_test = X[train_size + val_size:]
        y_test = y[train_size + val_size:]
        
        logger.info(f"Split data: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")
        return X_train, y_train, X_val, y_val, X_test, y_test
    
    def preprocess(
        self,
        price_history: List[Any],
        fit: bool = True,
        create_splits: bool = True
    ) -> Dict[str, Any]:
        """
        Complete preprocessing pipeline.
        
        Args:
            price_history: List of PriceHistory model instances
            fit: Whether to fit scalers (True for training, False for inference)
            create_splits: Whether to create train/val/test splits
        
        Returns:
            Dictionary containing:
            - df: Processed DataFrame
            - X: Input sequences
            - y: Target values
            - X_train, y_train, X_val, y_val, X_test, y_test (if create_splits=True)
        """
        # Step 1: Prepare DataFrame
        df = self.prepare_dataframe(price_history)
        if df.empty:
            logger.error("Failed to prepare DataFrame")
            return {'df': df, 'X': np.array([]), 'y': np.array([])}
        
        # Step 2: Add technical indicators
        df = self.add_technical_indicators(df)
        
        # Step 3: Normalize features
        df_normalized = self.normalize_features(df, fit=fit)
        
        # Step 4: Create sequences
        X, y = self.create_sequences(df_normalized)
        
        result = {
            'df': df,
            'df_normalized': df_normalized,
            'X': X,
            'y': y
        }
        
        # Step 5: Split data (optional)
        if create_splits and len(X) > 0:
            X_train, y_train, X_val, y_val, X_test, y_test = self.split_data(X, y)
            result.update({
                'X_train': X_train,
                'y_train': y_train,
                'X_val': X_val,
                'y_val': y_val,
                'X_test': X_test,
                'y_test': y_test
            })
        
        logger.info("Preprocessing pipeline completed successfully")
        return result
    
    def inverse_transform_price(self, normalized_price: np.ndarray) -> np.ndarray:
        """
        Convert normalized price back to original scale.
        
        Args:
            normalized_price: Normalized price values
        
        Returns:
            Original scale price values
        """
        if not self.is_fitted:
            logger.warning("Scaler not fitted, cannot inverse transform")
            return normalized_price
        
        # Reshape if needed
        if normalized_price.ndim == 1:
            normalized_price = normalized_price.reshape(-1, 1)
        
        return self.price_scaler.inverse_transform(normalized_price)
    
    def get_feature_names(self, df: pd.DataFrame) -> List[str]:
        """
        Get list of feature names used in sequences.
        
        Args:
            df: DataFrame with features
        
        Returns:
            List of feature column names
        """
        return [col for col in df.columns if col != 'timestamp']

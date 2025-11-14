"""
Prediction caching system for fast API responses.
Pre-generates and caches predictions to avoid blocking during training.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session

from src.data.database import session_scope
from src.data.repositories import CryptoRepository
from src.prediction.prediction_engine import PredictionEngine, PredictionResult
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


@dataclass
class CachedPrediction:
    """Cached prediction with metadata."""
    symbol: str
    prediction: Dict[str, Any]
    generated_at: str
    expires_at: str
    
    def is_expired(self) -> bool:
        """Check if prediction is expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires


class PredictionCache:
    """
    Manages prediction caching for fast API responses.
    """
    
    def __init__(self, config: Config, cache_ttl_hours: int = 1):
        """
        Initialize prediction cache.
        
        Args:
            config: Application configuration
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.config = config
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_dir = Path("cache/predictions")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._memory_cache: Dict[str, CachedPrediction] = {}
        
        logger.info(f"Initialized PredictionCache: TTL={cache_ttl_hours}h")
    
    def get_prediction(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached prediction for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
        
        Returns:
            Cached prediction or None if not found/expired
        """
        # Check memory cache first
        if symbol in self._memory_cache:
            cached = self._memory_cache[symbol]
            if not cached.is_expired():
                logger.debug(f"{symbol}: Serving from memory cache")
                return cached.prediction
            else:
                logger.debug(f"{symbol}: Memory cache expired")
                del self._memory_cache[symbol]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{symbol}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                cached = CachedPrediction(**data)
                
                if not cached.is_expired():
                    # Load into memory cache
                    self._memory_cache[symbol] = cached
                    logger.debug(f"{symbol}: Serving from disk cache")
                    return cached.prediction
                else:
                    logger.debug(f"{symbol}: Disk cache expired")
                    cache_file.unlink()
            
            except Exception as e:
                logger.error(f"{symbol}: Error reading cache: {e}")
        
        return None
    
    def set_prediction(
        self,
        symbol: str,
        prediction: Dict[str, Any]
    ) -> None:
        """
        Cache a prediction.
        
        Args:
            symbol: Cryptocurrency symbol
            prediction: Prediction data to cache
        """
        now = datetime.now()
        expires_at = now + timedelta(hours=self.cache_ttl_hours)
        
        cached = CachedPrediction(
            symbol=symbol,
            prediction=prediction,
            generated_at=now.isoformat(),
            expires_at=expires_at.isoformat()
        )
        
        # Save to memory
        self._memory_cache[symbol] = cached
        
        # Save to disk
        cache_file = self.cache_dir / f"{symbol}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(asdict(cached), f, indent=2)
            
            logger.debug(f"{symbol}: Cached prediction (expires {expires_at})")
        
        except Exception as e:
            logger.error(f"{symbol}: Error writing cache: {e}")
    
    def get_top_predictions(self, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached top predictions.
        
        Args:
            limit: Number of top predictions to return
        
        Returns:
            List of cached predictions or None if not found
        """
        cache_file = self.cache_dir / "top_predictions.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                generated_at = datetime.fromisoformat(data['generated_at'])
                expires_at = datetime.fromisoformat(data['expires_at'])
                
                if datetime.now() < expires_at:
                    logger.debug(f"Serving top {limit} predictions from cache")
                    return data['predictions'][:limit]
                else:
                    logger.debug("Top predictions cache expired")
                    cache_file.unlink()
            
            except Exception as e:
                logger.error(f"Error reading top predictions cache: {e}")
        
        return None
    
    def set_top_predictions(self, predictions: List[Dict[str, Any]]) -> None:
        """
        Cache top predictions.
        
        Args:
            predictions: List of predictions to cache
        """
        now = datetime.now()
        expires_at = now + timedelta(hours=self.cache_ttl_hours)
        
        data = {
            'predictions': predictions,
            'generated_at': now.isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        cache_file = self.cache_dir / "top_predictions.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Cached {len(predictions)} top predictions (expires {expires_at})")
        
        except Exception as e:
            logger.error(f"Error writing top predictions cache: {e}")
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cache for a symbol or all symbols.
        
        Args:
            symbol: Symbol to clear (None = clear all)
        """
        if symbol:
            # Clear specific symbol
            if symbol in self._memory_cache:
                del self._memory_cache[symbol]
            
            cache_file = self.cache_dir / f"{symbol}.json"
            if cache_file.exists():
                cache_file.unlink()
            
            logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all
            self._memory_cache.clear()
            
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            logger.info("Cleared all prediction cache")
    
    def pregenerate_predictions(
        self,
        crypto_symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Pre-generate predictions for all cryptos.
        
        This should be run before training starts to ensure
        fast API responses during training.
        
        Args:
            crypto_symbols: List of symbols to generate (None = all)
        
        Returns:
            Dictionary with generation results
        """
        start_time = time.time()
        logger.info("Starting prediction pre-generation")
        
        results = {
            'total_cryptos': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'duration_seconds': 0
        }
        
        with session_scope() as session:
            crypto_repo = CryptoRepository(session)
            
            # Get cryptos
            if crypto_symbols is None:
                cryptos = crypto_repo.get_top_by_market_cap(self.config.top_n_cryptos)
                crypto_symbols = [c.symbol for c in cryptos]
            
            results['total_cryptos'] = len(crypto_symbols)
            
            # Generate predictions
            all_predictions = []
            
            for symbol in crypto_symbols:
                try:
                    crypto = crypto_repo.get_by_symbol(symbol)
                    if not crypto:
                        logger.warning(f"{symbol}: Not found")
                        results['failed'] += 1
                        continue
                    
                    # Check if model exists
                    model_path = Path("models") / f"{symbol}_latest.keras"
                    if not model_path.exists():
                        logger.warning(f"{symbol}: No model found")
                        results['failed'] += 1
                        continue
                    
                    # Generate prediction (this will be implemented in prediction engine)
                    # For now, create a placeholder
                    prediction = {
                        'symbol': symbol,
                        'name': crypto.name,
                        'predicted_change_percent': 0.0,  # Placeholder
                        'confidence_score': 0.0,  # Placeholder
                        'generated_at': datetime.now().isoformat()
                    }
                    
                    # Cache it
                    self.set_prediction(symbol, prediction)
                    all_predictions.append(prediction)
                    
                    results['successful'] += 1
                    results['cached'] += 1
                    
                except Exception as e:
                    logger.error(f"{symbol}: Prediction generation failed: {e}")
                    results['failed'] += 1
            
            # Sort by predicted change and cache top predictions
            all_predictions.sort(
                key=lambda x: x.get('predicted_change_percent', 0),
                reverse=True
            )
            self.set_top_predictions(all_predictions)
        
        results['duration_seconds'] = time.time() - start_time
        
        logger.info(
            f"Prediction pre-generation complete: "
            f"{results['successful']}/{results['total_cryptos']} successful, "
            f"{results['duration_seconds']:.1f}s"
        )
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            'memory_cache_size': len(self._memory_cache),
            'disk_cache_files': len(list(self.cache_dir.glob("*.json"))),
            'cache_ttl_hours': self.cache_ttl_hours
        }
        
        # Count expired entries
        expired = 0
        for cached in self._memory_cache.values():
            if cached.is_expired():
                expired += 1
        
        stats['expired_entries'] = expired
        
        return stats

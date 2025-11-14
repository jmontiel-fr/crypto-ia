#!/usr/bin/env python3
"""
Training orchestration script.
Handles both incremental updates and full retraining with prediction pre-generation.
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_loader import load_config
from src.prediction.incremental_trainer import IncrementalTrainer
from src.prediction.prediction_cache import PredictionCache

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/training.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_incremental_update(config):
    """Run incremental training update."""
    logger.info("="*60)
    logger.info("INCREMENTAL TRAINING UPDATE")
    logger.info("="*60)
    
    trainer = IncrementalTrainer(config)
    
    # Run incremental update
    results = trainer.incremental_update(
        hours_back=6,
        epochs=5
    )
    
    logger.info(f"Incremental update results:")
    logger.info(f"  Total: {results['total_cryptos']}")
    logger.info(f"  Successful: {results['successful']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info(f"  Skipped: {results['skipped']}")
    logger.info(f"  Duration: {results['duration_seconds']/60:.1f} minutes")
    
    # Regenerate predictions for updated models
    logger.info("Regenerating predictions for updated models...")
    cache = PredictionCache(config, cache_ttl_hours=1)
    
    updated_symbols = [
        d['symbol'] for d in results['details']
        if d.get('status') == 'success'
    ]
    
    if updated_symbols:
        cache_results = cache.pregenerate_predictions(updated_symbols)
        logger.info(f"Cached {cache_results['cached']} predictions")
    
    return results


def run_full_retrain(config, batch_size=25):
    """Run full retraining with prediction pre-generation."""
    logger.info("="*60)
    logger.info("FULL RETRAINING")
    logger.info("="*60)
    
    # Step 1: Pre-generate predictions BEFORE training
    logger.info("Step 1: Pre-generating predictions (before training)...")
    cache = PredictionCache(config, cache_ttl_hours=24)  # 24h cache during training
    
    cache_results = cache.pregenerate_predictions()
    logger.info(f"Pre-generated {cache_results['successful']} predictions")
    logger.info(f"Cache duration: {cache_results['duration_seconds']/60:.1f} minutes")
    
    # Step 2: Run full retraining
    logger.info("Step 2: Starting full retraining...")
    trainer = IncrementalTrainer(config)
    
    results = trainer.full_retrain(
        months_back=6,
        epochs=50,
        batch_size=batch_size
    )
    
    logger.info(f"Full retraining results:")
    logger.info(f"  Total: {results['total_cryptos']}")
    logger.info(f"  Successful: {results['successful']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info(f"  Duration: {results['duration_seconds']/3600:.1f} hours")
    logger.info(f"  Batches: {len(results['batches'])}")
    
    # Step 3: Regenerate predictions with new models
    logger.info("Step 3: Regenerating predictions with new models...")
    cache = PredictionCache(config, cache_ttl_hours=1)  # Back to 1h cache
    
    final_cache_results = cache.pregenerate_predictions()
    logger.info(f"Final cache: {final_cache_results['successful']} predictions")
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run model training')
    parser.add_argument(
        '--mode',
        choices=['incremental', 'full'],
        default='incremental',
        help='Training mode'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Batch size for full retraining'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded: {config.environment}")
        
        # Run training
        start_time = datetime.now()
        
        if args.mode == 'incremental':
            results = run_incremental_update(config)
        else:
            results = run_full_retrain(config, args.batch_size)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("="*60)
        logger.info(f"Training complete!")
        logger.info(f"Mode: {args.mode}")
        logger.info(f"Total duration: {duration/3600:.2f} hours")
        logger.info(f"Started: {start_time}")
        logger.info(f"Finished: {end_time}")
        logger.info("="*60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

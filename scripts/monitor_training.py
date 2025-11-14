#!/usr/bin/env python3
"""
Training monitoring script.
Monitors training progress, cache status, and system resources.
"""

import sys
import os
import psutil
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.config_loader import load_config
from src.prediction.prediction_cache import PredictionCache


def get_system_resources():
    """Get current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_used_mb': memory.used / (1024 * 1024),
        'memory_total_mb': memory.total / (1024 * 1024),
        'memory_percent': memory.percent,
        'disk_used_gb': disk.used / (1024 * 1024 * 1024),
        'disk_total_gb': disk.total / (1024 * 1024 * 1024),
        'disk_percent': disk.percent
    }


def check_training_status():
    """Check if training is currently running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'run_training.py' in ' '.join(cmdline):
                return {
                    'is_running': True,
                    'pid': proc.info['pid'],
                    'started': datetime.fromtimestamp(proc.create_time()).isoformat()
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return {'is_running': False}


def get_model_status():
    """Get status of trained models."""
    models_dir = Path('models')
    
    if not models_dir.exists():
        return {'total_models': 0, 'models': []}
    
    models = []
    for model_file in models_dir.glob('*_latest.keras'):
        symbol = model_file.stem.replace('_latest', '')
        stat = model_file.stat()
        
        models.append({
            'symbol': symbol,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    # Sort by modification time (newest first)
    models.sort(key=lambda x: x['modified'], reverse=True)
    
    return {
        'total_models': len(models),
        'models': models[:10]  # Show latest 10
    }


def get_cache_status(config):
    """Get prediction cache status."""
    try:
        cache = PredictionCache(config)
        stats = cache.get_cache_stats()
        
        # Check if top predictions are cached
        top_cached = cache.get_top_predictions(limit=1)
        stats['top_predictions_cached'] = top_cached is not None
        
        return stats
    except Exception as e:
        return {'error': str(e)}


def get_training_logs(lines=20):
    """Get recent training log entries."""
    log_file = Path('logs/training.log')
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except Exception as e:
        return [f"Error reading logs: {e}"]


def main():
    """Main monitoring function."""
    print("="*70)
    print("TRAINING MONITORING DASHBOARD")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # System Resources
    print("SYSTEM RESOURCES")
    print("-"*70)
    resources = get_system_resources()
    print(f"CPU Usage:    {resources['cpu_percent']:.1f}%")
    print(f"Memory:       {resources['memory_used_mb']:.0f} MB / {resources['memory_total_mb']:.0f} MB ({resources['memory_percent']:.1f}%)")
    print(f"Disk:         {resources['disk_used_gb']:.1f} GB / {resources['disk_total_gb']:.1f} GB ({resources['disk_percent']:.1f}%)")
    print()
    
    # Training Status
    print("TRAINING STATUS")
    print("-"*70)
    training_status = check_training_status()
    if training_status['is_running']:
        print(f"Status:       🔄 RUNNING")
        print(f"PID:          {training_status['pid']}")
        print(f"Started:      {training_status['started']}")
    else:
        print(f"Status:       ✓ IDLE")
    print()
    
    # Model Status
    print("MODEL STATUS")
    print("-"*70)
    model_status = get_model_status()
    print(f"Total Models: {model_status['total_models']}")
    if model_status['models']:
        print(f"\nRecently Updated:")
        for model in model_status['models'][:5]:
            print(f"  • {model['symbol']:<10} {model['size_mb']:>6.1f} MB  {model['modified']}")
    print()
    
    # Cache Status
    print("PREDICTION CACHE")
    print("-"*70)
    try:
        config = load_config()
        cache_status = get_cache_status(config)
        
        if 'error' in cache_status:
            print(f"Error: {cache_status['error']}")
        else:
            print(f"Memory Cache:     {cache_status['memory_cache_size']} entries")
            print(f"Disk Cache:       {cache_status['disk_cache_files']} files")
            print(f"Cache TTL:        {cache_status['cache_ttl_hours']} hours")
            print(f"Expired Entries:  {cache_status['expired_entries']}")
            print(f"Top Predictions:  {'✓ Cached' if cache_status.get('top_predictions_cached') else '✗ Not cached'}")
    except Exception as e:
        print(f"Error loading cache status: {e}")
    print()
    
    # Recent Logs
    print("RECENT TRAINING LOGS (last 10 lines)")
    print("-"*70)
    logs = get_training_logs(lines=10)
    for log in logs:
        print(log)
    print()
    
    print("="*70)
    
    # Health Check
    print("\nHEALTH CHECK")
    print("-"*70)
    
    warnings = []
    errors = []
    
    # Check CPU
    if resources['cpu_percent'] > 95:
        errors.append("⚠️  CPU usage critical (>95%)")
    elif resources['cpu_percent'] > 80:
        warnings.append("⚠️  CPU usage high (>80%)")
    
    # Check Memory
    if resources['memory_percent'] > 95:
        errors.append("⚠️  Memory usage critical (>95%)")
    elif resources['memory_percent'] > 80:
        warnings.append("⚠️  Memory usage high (>80%)")
    
    # Check Disk
    if resources['disk_percent'] > 90:
        errors.append("⚠️  Disk usage critical (>90%)")
    elif resources['disk_percent'] > 80:
        warnings.append("⚠️  Disk usage high (>80%)")
    
    # Check Models
    if model_status['total_models'] == 0:
        warnings.append("⚠️  No trained models found")
    elif model_status['total_models'] < 20:
        warnings.append(f"⚠️  Only {model_status['total_models']} models trained (expected 100)")
    
    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors and not warnings:
        print("✓ All systems healthy")
    
    print("="*70)


if __name__ == "__main__":
    main()

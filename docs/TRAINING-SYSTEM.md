## Training System Documentation

## Overview

The training system implements a hybrid approach combining incremental updates with periodic full retraining, optimized for t3.micro instances.

### Key Features

✅ **Incremental Training**: Updates models every 6 hours with new data (10 minutes)  
✅ **Full Retraining**: Complete retraining weekly (20 hours)  
✅ **Prediction Caching**: Pre-generated predictions for fast API responses  
✅ **Background Processing**: Training doesn't block API requests  
✅ **Resource Optimization**: Designed for 1 GB RAM instances  

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Training System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Incremental Trainer                                        │
│  ├─ Runs every 6 hours                                     │
│  ├─ Trains on last 6 hours of data                         │
│  ├─ Updates existing models (5 epochs)                     │
│  └─ Duration: ~10 minutes for 100 cryptos                  │
│                                                             │
│  Full Retrainer                                             │
│  ├─ Runs weekly (Sunday 2 AM)                              │
│  ├─ Trains on 6 months of data                             │
│  ├─ Creates new models (50 epochs)                         │
│  └─ Duration: ~20 hours for 100 cryptos                    │
│                                                             │
│  Prediction Cache                                           │
│  ├─ Pre-generates predictions before training              │
│  ├─ Caches for 1-24 hours                                  │
│  ├─ Serves fast API responses (0.5-1s)                     │
│  └─ Updates after training completes                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Training Schedule

### Weekly Cycle

```
Sunday 01:55 AM - Pre-generate predictions (cache for 24h)
Sunday 02:00 AM - Full retraining starts
Sunday 10:00 PM - Full retraining completes
Sunday 10:05 PM - Regenerate predictions (cache for 1h)

Monday-Saturday:
  00:00 - Incremental update + cache refresh
  06:00 - Incremental update + cache refresh
  12:00 - Incremental update + cache refresh
  18:00 - Incremental update + cache refresh

Next Sunday - Repeat cycle
```

### Training Times

| Training Type | Frequency | Duration | Cryptos | Data |
|---------------|-----------|----------|---------|------|
| **Incremental** | Every 6h | 10 min | 100 | 6 hours |
| **Full** | Weekly | 20 hours | 100 | 6 months |

---

## Configuration

### Environment Variables

```bash
# Training Configuration
TRAIN_BATCH_SIZE=25              # Cryptos per batch
TRAIN_MONTHS_BACK=6              # Months of historical data
TRAIN_EPOCHS=50                  # Epochs for full training

# Incremental Training
INCREMENTAL_ENABLED=true         # Enable incremental updates
INCREMENTAL_EPOCHS=5             # Epochs for incremental
INCREMENTAL_SCHEDULE=0 */6 * * * # Every 6 hours

# Full Retraining
FULL_RETRAIN_SCHEDULE=0 2 * * 0  # Sunday 2 AM
FULL_RETRAIN_ENABLED=true        # Enable full retraining

# Prediction Caching
PREDICTION_CACHE_ENABLED=true    # Enable caching
PREDICTION_CACHE_TTL_HOURS=1     # Cache duration
```

---

## Usage

### Manual Training

**Incremental Update:**
```bash
python scripts/run_training.py --mode incremental
```

**Full Retraining:**
```bash
python scripts/run_training.py --mode full --batch-size 25
```

### Automated Training (Cron)

**Setup cron jobs:**
```bash
chmod +x scripts/setup_training_cron.sh
./scripts/setup_training_cron.sh
```

**Verify cron jobs:**
```bash
crontab -l | grep training
```

**View logs:**
```bash
# Full retraining logs
tail -f logs/cron_full_retrain.log

# Incremental update logs
tail -f logs/cron_incremental.log

# Detailed training logs
tail -f logs/training.log
```

### Monitoring

**Check training status:**
```bash
python scripts/monitor_training.py
```

**Output:**
```
======================================================================
TRAINING MONITORING DASHBOARD
======================================================================
Timestamp: 2025-11-12T14:30:00

SYSTEM RESOURCES
----------------------------------------------------------------------
CPU Usage:    45.2%
Memory:       687 MB / 1024 MB (67.1%)
Disk:         12.3 GB / 20.0 GB (61.5%)

TRAINING STATUS
----------------------------------------------------------------------
Status:       ✓ IDLE

MODEL STATUS
----------------------------------------------------------------------
Total Models: 100

Recently Updated:
  • BTC        2.3 MB  2025-11-12T02:15:00
  • ETH        2.1 MB  2025-11-12T02:27:00
  • SOL        2.0 MB  2025-11-12T02:39:00

PREDICTION CACHE
----------------------------------------------------------------------
Memory Cache:     100 entries
Disk Cache:       101 files
Cache TTL:        1 hours
Expired Entries:  0
Top Predictions:  ✓ Cached

HEALTH CHECK
----------------------------------------------------------------------
✓ All systems healthy
======================================================================
```

---

## Performance

### Resource Usage

**During Incremental Update:**
- CPU: 20-30%
- Memory: 400-600 MB
- Duration: 10 minutes
- API Impact: None (predictions served from cache)

**During Full Retraining:**
- CPU: 70-80%
- Memory: 700-900 MB
- Duration: 20 hours
- API Impact: Minimal (1-2s response vs 0.5-1s normal)

### API Response Times

| Scenario | Response Time | Notes |
|----------|---------------|-------|
| Normal (cached) | 0.5-1s | Predictions from cache |
| During incremental | 0.5-1s | No impact (cache used) |
| During full retrain | 1-2s | Slight slowdown |
| Cache miss | 3-5s | Generates prediction on-demand |

---

## Prediction Caching Strategy

### Pre-Generation Workflow

```python
# Before training (1:55 AM):
1. Generate predictions for all 100 cryptos
2. Cache predictions for 24 hours
3. Cache top 20 predictions

# During training (2:00 AM - 10:00 PM):
4. API serves from cache (fast responses)
5. Training runs in background
6. No impact on API performance

# After training (10:05 PM):
7. Regenerate predictions with new models
8. Cache for 1 hour
9. Resume normal operation
```

### Cache Management

**Cache Locations:**
- Memory: In-process cache (fastest)
- Disk: `cache/predictions/*.json` (persistent)

**Cache TTL:**
- Normal: 1 hour
- During training: 24 hours
- Expires automatically

**Cache Invalidation:**
```bash
# Clear all cache
python -c "from src.prediction.prediction_cache import PredictionCache; \
           from src.config.config_loader import load_config; \
           cache = PredictionCache(load_config()); \
           cache.clear_cache()"

# Clear specific symbol
python -c "from src.prediction.prediction_cache import PredictionCache; \
           from src.config.config_loader import load_config; \
           cache = PredictionCache(load_config()); \
           cache.clear_cache('BTC')"
```

---

## Troubleshooting

### Training Not Starting

**Check cron jobs:**
```bash
crontab -l
```

**Check logs:**
```bash
tail -f logs/cron_full_retrain.log
tail -f logs/training.log
```

**Manual test:**
```bash
python scripts/run_training.py --mode incremental
```

### High Memory Usage

**Symptoms:**
- Memory > 950 MB
- OOM errors in logs
- Training crashes

**Solutions:**
1. Reduce batch size:
   ```bash
   TRAIN_BATCH_SIZE=20  # Instead of 25
   ```

2. Reduce training data:
   ```bash
   TRAIN_MONTHS_BACK=3  # Instead of 6
   ```

3. Upgrade to t3.small (2 GB RAM)

### Slow API Responses

**Symptoms:**
- API responses > 3 seconds
- Users complaining about slowness

**Solutions:**
1. Check cache status:
   ```bash
   python scripts/monitor_training.py
   ```

2. Regenerate cache:
   ```bash
   python -c "from src.prediction.prediction_cache import PredictionCache; \
              from src.config.config_loader import load_config; \
              cache = PredictionCache(load_config()); \
              cache.pregenerate_predictions()"
   ```

3. Check if training is running:
   ```bash
   ps aux | grep run_training.py
   ```

### Training Takes Too Long

**Expected times:**
- Incremental: 10 minutes
- Full: 20 hours

**If slower:**
1. Check CPU usage:
   ```bash
   top
   ```

2. Check disk I/O:
   ```bash
   iostat -x 1
   ```

3. Reduce batch size or data range

---

## Best Practices

### 1. Monitor Regularly

```bash
# Add to cron (every hour)
0 * * * * /path/to/scripts/monitor_training.py >> /path/to/logs/monitoring.log 2>&1
```

### 2. Backup Models

```bash
# Before full retraining
tar -czf models_backup_$(date +%Y%m%d).tar.gz models/
```

### 3. Test Before Production

```bash
# Test incremental update
python scripts/run_training.py --mode incremental

# Check results
python scripts/monitor_training.py
```

### 4. Set Up Alerts

```bash
# CloudWatch alarms for:
# - CPU > 95% for 5 minutes
# - Memory > 950 MB
# - Disk > 90%
```

### 5. Review Logs Weekly

```bash
# Check for errors
grep -i error logs/training.log | tail -20

# Check for warnings
grep -i warning logs/training.log | tail -20
```

---

## FAQ

**Q: Can I change training schedule?**  
A: Yes, edit `INCREMENTAL_SCHEDULE` and `FULL_RETRAIN_SCHEDULE` in `local-env`

**Q: How much does training cost?**  
A: On t3.micro: $0 extra (included in instance cost)

**Q: Can I train more than 100 cryptos?**  
A: Yes, but increase `TRAIN_BATCH_SIZE` and expect longer training times

**Q: What if training fails?**  
A: Models from previous week are still used. Fix issue and retry.

**Q: Can I skip full retraining?**  
A: Not recommended. Incremental updates accumulate errors over time.

**Q: How do I know if cache is working?**  
A: Check API response times (<1s = cached, >3s = not cached)

---

## Support

For issues:
1. Check logs: `logs/training.log`
2. Run monitoring: `python scripts/monitor_training.py`
3. Check system resources: `top`, `free -h`
4. Review this documentation

---

**Last Updated:** November 12, 2025  
**Version:** 1.0.0

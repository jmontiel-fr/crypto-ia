# Training System Quick Start

## 5-Minute Setup

### Step 1: Configuration Already Done ✅

Your `local-env` is already configured with:
- ✅ Incremental training enabled
- ✅ Full retraining scheduled (Sunday 2 AM)
- ✅ Prediction caching enabled
- ✅ 6 months of training data
- ✅ Batch size optimized for t3.micro

### Step 2: Setup Automated Training

```bash
# Make scripts executable and setup cron jobs
chmod +x scripts/setup_training_cron.sh
./scripts/setup_training_cron.sh
```

**Output:**
```
✓ Added full retraining cron job (Sunday 2 AM)
✓ Added incremental update cron job (every 6 hours)

Training Schedule:
==================
• Incremental updates: Every 6 hours (00:00, 06:00, 12:00, 18:00)
• Full retraining: Every Sunday at 2:00 AM
```

### Step 3: Run Initial Training

```bash
# This will take ~20 hours for 100 cryptos
# Run in background or use screen/tmux
python scripts/run_training.py --mode full --batch-size 25 &

# Monitor progress
tail -f logs/training.log
```

### Step 4: Monitor Training

```bash
# Check status anytime
python scripts/monitor_training.py
```

---

## That's It!

Your training system is now:
- ✅ Updating models every 6 hours (10 minutes each)
- ✅ Full retraining weekly (20 hours on Sunday)
- ✅ Caching predictions for fast API responses
- ✅ Running in background without blocking API

---

## What Happens Next?

### This Week:
```
Now         - Initial training starts (20 hours)
Tomorrow    - Training completes, predictions cached
Daily       - Incremental updates every 6 hours (10 min each)
Next Sunday - Full retraining again
```

### API Performance:
- **Normal**: 0.5-1 second (cached predictions)
- **During training**: 1-2 seconds (slight slowdown)
- **Cache miss**: 3-5 seconds (generates on-demand)

### Resource Usage:
- **CPU**: 20-80% (depending on training)
- **Memory**: 400-900 MB (safe for t3.micro)
- **Disk**: ~500 MB for models + cache

---

## Quick Commands

```bash
# Monitor training
python scripts/monitor_training.py

# View logs
tail -f logs/training.log

# Check cron jobs
crontab -l | grep training

# Manual incremental update
python scripts/run_training.py --mode incremental

# Manual full retraining
python scripts/run_training.py --mode full
```

---

## Troubleshooting

**Training not starting?**
```bash
# Check cron jobs
crontab -l

# Check logs
tail -f logs/cron_full_retrain.log
```

**API slow?**
```bash
# Check cache
python scripts/monitor_training.py

# Regenerate cache
python -c "from src.prediction.prediction_cache import PredictionCache; from src.config.config_loader import load_config; PredictionCache(load_config()).pregenerate_predictions()"
```

**High memory?**
```bash
# Check usage
free -h

# Reduce batch size in local-env
TRAIN_BATCH_SIZE=20
```

---

## Next Steps

1. ✅ Wait for initial training to complete (~20 hours)
2. ✅ Verify predictions are cached
3. ✅ Test API response times
4. ✅ Monitor weekly retraining
5. ✅ Review logs regularly

**Full Documentation:** `docs/TRAINING-SYSTEM.md`

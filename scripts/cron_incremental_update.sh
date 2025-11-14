#!/bin/bash
# Cron job for incremental training updates (runs every 6 hours)

# Set working directory
cd "$(dirname "$0")/.." || exit 1

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Load environment variables
export $(cat local-env | grep -v '^#' | xargs)

# Run incremental update
echo "[$(date)] Starting incremental training update..."
python scripts/run_training.py --mode incremental

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "[$(date)] Incremental update completed successfully"
else
    echo "[$(date)] Incremental update failed with code $exit_code"
fi

exit $exit_code

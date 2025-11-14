#!/bin/bash
# Cron job for full retraining (runs weekly on Sunday 2 AM)

# Set working directory
cd "$(dirname "$0")/.." || exit 1

# Activate virtual environment
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Load environment variables
export $(cat local-env | grep -v '^#' | xargs)

# Run full retraining
echo "[$(date)] Starting full retraining..."
python scripts/run_training.py --mode full --batch-size 25

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "[$(date)] Full retraining completed successfully"
else
    echo "[$(date)] Full retraining failed with code $exit_code"
fi

exit $exit_code

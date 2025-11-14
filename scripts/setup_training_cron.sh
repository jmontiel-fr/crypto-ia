#!/bin/bash
# Setup cron jobs for automated training

echo "Setting up training cron jobs..."

# Get absolute path to project directory
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Make scripts executable
chmod +x "$PROJECT_DIR/scripts/cron_full_retrain.sh"
chmod +x "$PROJECT_DIR/scripts/cron_incremental_update.sh"

# Create cron entries
CRON_FULL="0 2 * * 0 $PROJECT_DIR/scripts/cron_full_retrain.sh >> $PROJECT_DIR/logs/cron_full_retrain.log 2>&1"
CRON_INCREMENTAL="0 */6 * * * $PROJECT_DIR/scripts/cron_incremental_update.sh >> $PROJECT_DIR/logs/cron_incremental.log 2>&1"

# Check if cron entries already exist
crontab -l 2>/dev/null | grep -q "cron_full_retrain.sh"
FULL_EXISTS=$?

crontab -l 2>/dev/null | grep -q "cron_incremental_update.sh"
INCREMENTAL_EXISTS=$?

# Add cron entries if they don't exist
if [ $FULL_EXISTS -ne 0 ] || [ $INCREMENTAL_EXISTS -ne 0 ]; then
    # Get existing crontab
    crontab -l 2>/dev/null > /tmp/crontab.tmp
    
    # Add new entries
    if [ $FULL_EXISTS -ne 0 ]; then
        echo "$CRON_FULL" >> /tmp/crontab.tmp
        echo "✓ Added full retraining cron job (Sunday 2 AM)"
    else
        echo "✓ Full retraining cron job already exists"
    fi
    
    if [ $INCREMENTAL_EXISTS -ne 0 ]; then
        echo "$CRON_INCREMENTAL" >> /tmp/crontab.tmp
        echo "✓ Added incremental update cron job (every 6 hours)"
    else
        echo "✓ Incremental update cron job already exists"
    fi
    
    # Install new crontab
    crontab /tmp/crontab.tmp
    rm /tmp/crontab.tmp
    
    echo ""
    echo "Cron jobs installed successfully!"
else
    echo "✓ All cron jobs already exist"
fi

echo ""
echo "Current cron schedule:"
echo "====================="
crontab -l | grep -E "(cron_full_retrain|cron_incremental_update)"

echo ""
echo "Training Schedule:"
echo "=================="
echo "• Incremental updates: Every 6 hours (00:00, 06:00, 12:00, 18:00)"
echo "• Full retraining: Every Sunday at 2:00 AM"
echo ""
echo "Logs:"
echo "• Full retraining: logs/cron_full_retrain.log"
echo "• Incremental updates: logs/cron_incremental.log"
echo "• Training details: logs/training.log"

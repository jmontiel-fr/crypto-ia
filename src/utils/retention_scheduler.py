"""
Log Retention Scheduler.
Schedules automatic cleanup of old logs based on retention policies.
"""

import logging
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from src.utils.log_retention import run_log_retention_cleanup

logger = logging.getLogger(__name__)


class RetentionScheduler:
    """
    Scheduler for automatic log retention cleanup.
    """
    
    def __init__(self):
        """Initialize the retention scheduler."""
        self.scheduler = None
        self.is_running = False
        
        # Configure scheduler
        executors = {
            'default': ThreadPoolExecutor(max_workers=1)
        }
        
        self.scheduler = BackgroundScheduler(
            executors=executors,
            timezone='UTC'
        )
        
    def start(self):
        """Start the retention scheduler."""
        if self.is_running:
            logger.warning("Retention scheduler is already running")
            return
        
        try:
            # Get schedule from environment (default: daily at 2 AM UTC)
            schedule = os.getenv('LOG_RETENTION_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
            
            # Parse cron expression
            cron_parts = schedule.split()
            if len(cron_parts) != 5:
                logger.error(f"Invalid cron expression: {schedule}")
                return
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Add the cleanup job
            self.scheduler.add_job(
                func=self._run_cleanup_job,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    timezone='UTC'
                ),
                id='log_retention_cleanup',
                name='Log Retention Cleanup',
                replace_existing=True,
                max_instances=1,  # Prevent overlapping executions
                misfire_grace_time=3600  # Allow 1 hour grace time for missed jobs
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Log retention scheduler started with schedule: {schedule}")
            
        except Exception as e:
            logger.error(f"Failed to start retention scheduler: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the retention scheduler."""
        if not self.is_running:
            logger.warning("Retention scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Log retention scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping retention scheduler: {e}", exc_info=True)
    
    def _run_cleanup_job(self):
        """Execute the log retention cleanup job."""
        try:
            logger.info("Starting scheduled log retention cleanup")
            run_log_retention_cleanup()
            logger.info("Scheduled log retention cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Scheduled log retention cleanup failed: {e}", exc_info=True)
    
    def trigger_manual_cleanup(self):
        """Trigger manual log retention cleanup."""
        try:
            logger.info("Triggering manual log retention cleanup")
            
            # Add a one-time job to run immediately
            self.scheduler.add_job(
                func=self._run_cleanup_job,
                trigger='date',
                run_date=datetime.utcnow(),
                id='manual_log_cleanup',
                name='Manual Log Cleanup',
                replace_existing=True
            )
            
            logger.info("Manual log retention cleanup triggered")
            
        except Exception as e:
            logger.error(f"Failed to trigger manual cleanup: {e}", exc_info=True)
            raise
    
    def get_next_run_time(self) -> str:
        """
        Get the next scheduled run time.
        
        Returns:
            Next run time as ISO string or 'Not scheduled'
        """
        if not self.is_running:
            return "Not scheduled"
        
        try:
            job = self.scheduler.get_job('log_retention_cleanup')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
            else:
                return "Not scheduled"
                
        except Exception as e:
            logger.error(f"Error getting next run time: {e}", exc_info=True)
            return "Error"
    
    def get_job_status(self) -> dict:
        """
        Get the current job status.
        
        Returns:
            Dictionary with job status information
        """
        try:
            job = self.scheduler.get_job('log_retention_cleanup')
            
            if not job:
                return {
                    "scheduled": False,
                    "next_run_time": None,
                    "last_run_time": None
                }
            
            return {
                "scheduled": True,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_time": None,  # APScheduler doesn't track this by default
                "job_id": job.id,
                "job_name": job.name
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}", exc_info=True)
            return {"error": str(e)}


# Global scheduler instance
_retention_scheduler = None


def get_retention_scheduler() -> RetentionScheduler:
    """
    Get the global retention scheduler instance.
    
    Returns:
        RetentionScheduler instance
    """
    global _retention_scheduler
    
    if _retention_scheduler is None:
        _retention_scheduler = RetentionScheduler()
    
    return _retention_scheduler


def start_retention_scheduler():
    """Start the global retention scheduler."""
    scheduler = get_retention_scheduler()
    scheduler.start()


def stop_retention_scheduler():
    """Stop the global retention scheduler."""
    global _retention_scheduler
    
    if _retention_scheduler:
        _retention_scheduler.stop()
        _retention_scheduler = None


if __name__ == "__main__":
    # Allow running as standalone script for testing
    import time
    
    scheduler = RetentionScheduler()
    
    try:
        scheduler.start()
        print("Retention scheduler started. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped.")
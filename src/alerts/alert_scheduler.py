"""
Alert scheduler module.
Manages scheduled execution of market shift detection and alerting.
"""

import logging
from typing import Optional
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from sqlalchemy.orm import Session, sessionmaker

from src.alerts.alert_system import AlertSystem
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


class AlertScheduler:
    """
    Scheduler for automated alert system execution.
    Uses APScheduler to run hourly market shift checks.
    """
    
    def __init__(
        self,
        session_factory: sessionmaker,
        config: Config
    ):
        """
        Initialize alert scheduler.
        
        Args:
            session_factory: SQLAlchemy session factory for creating database sessions
            config: Application configuration
        """
        self.session_factory = session_factory
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_run_time: Optional[datetime] = None
        self.last_run_status: Optional[str] = None
        self.error_count = 0
        
        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        
        logger.info("AlertScheduler initialized")
    
    def start(self) -> None:
        """
        Start the alert scheduler.
        Schedules hourly execution of market shift checks.
        """
        if self.is_running:
            logger.warning("AlertScheduler already running")
            return
        
        if not self.config.alert_enabled:
            logger.info("Alert system disabled in configuration, scheduler not started")
            return
        
        try:
            # Schedule hourly execution (at the top of every hour)
            # This runs more frequently than the collector to catch shifts quickly
            self.scheduler.add_job(
                func=self._run_alert_check,
                trigger=CronTrigger(minute=0),  # Every hour at minute 0
                id='alert_check',
                name='Market Shift Alert Check',
                replace_existing=True,
                max_instances=1,  # Prevent overlapping executions
                misfire_grace_time=300  # 5 minutes grace period
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("AlertScheduler started - running hourly at minute 0")
            
        except Exception as e:
            logger.error(f"Failed to start AlertScheduler: {e}", exc_info=True)
            raise
    
    def stop(self) -> None:
        """
        Stop the alert scheduler.
        Waits for any running jobs to complete.
        """
        if not self.is_running:
            logger.warning("AlertScheduler not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("AlertScheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping AlertScheduler: {e}", exc_info=True)
    
    def _run_alert_check(self) -> None:
        """
        Execute alert check job.
        Creates a new database session and runs the alert system.
        """
        session = None
        try:
            logger.info("Starting scheduled alert check")
            
            # Create new database session
            session = self.session_factory()
            
            # Create alert system instance
            alert_system = AlertSystem(
                db_session=session,
                config=self.config
            )
            
            # Check for market shifts and send alerts
            shifts = alert_system.check_market_shifts()
            
            # Update status
            self.last_run_time = datetime.utcnow()
            self.last_run_status = 'success'
            
            logger.info(
                f"Alert check completed successfully. "
                f"Detected {len(shifts)} shifts."
            )
            
        except Exception as e:
            self.last_run_status = 'error'
            self.error_count += 1
            logger.error(f"Error during scheduled alert check: {e}", exc_info=True)
            
            # Rollback on error
            if session:
                session.rollback()
            
        finally:
            # Always close the session
            if session:
                session.close()
    
    def run_now(self) -> bool:
        """
        Manually trigger an alert check immediately.
        
        Returns:
            True if check completed successfully, False otherwise
        """
        logger.info("Manual alert check triggered")
        
        try:
            self._run_alert_check()
            return self.last_run_status == 'success'
            
        except Exception as e:
            logger.error(f"Error during manual alert check: {e}", exc_info=True)
            return False
    
    def get_status(self) -> dict:
        """
        Get current scheduler status.
        
        Returns:
            Dictionary with status information
        """
        next_run = None
        if self.is_running:
            job = self.scheduler.get_job('alert_check')
            if job:
                next_run = job.next_run_time
        
        return {
            'is_running': self.is_running,
            'alert_enabled': self.config.alert_enabled,
            'last_run_time': self.last_run_time,
            'last_run_status': self.last_run_status,
            'next_run_time': next_run,
            'error_count': self.error_count,
            'threshold_percent': self.config.alert_threshold_percent,
            'cooldown_hours': self.config.alert_cooldown_hours,
            'sms_provider': self.config.sms_provider
        }
    
    def _job_executed_listener(self, event) -> None:
        """
        Listener for successful job execution.
        
        Args:
            event: APScheduler job execution event
        """
        logger.debug(f"Job executed successfully: {event.job_id}")
    
    def _job_error_listener(self, event) -> None:
        """
        Listener for job execution errors.
        
        Args:
            event: APScheduler job error event
        """
        logger.error(
            f"Job execution failed: {event.job_id}, "
            f"Exception: {event.exception}",
            exc_info=True
        )
        self.error_count += 1
    
    def reset_error_count(self) -> None:
        """Reset the error counter."""
        self.error_count = 0
        logger.info("Error count reset")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.
        
        Returns:
            Next run time or None if scheduler not running
        """
        if not self.is_running:
            return None
        
        job = self.scheduler.get_job('alert_check')
        return job.next_run_time if job else None


# Global scheduler instance
_alert_scheduler = None


def get_alert_scheduler() -> AlertScheduler:
    """
    Get the global alert scheduler instance.
    
    Returns:
        AlertScheduler instance
    """
    global _alert_scheduler
    
    if _alert_scheduler is None:
        from src.config.config_loader import load_config
        from src.data.database import get_session_factory
        
        config = load_config()
        session_factory = get_session_factory(config.database_url)
        
        _alert_scheduler = AlertScheduler(
            session_factory=session_factory,
            config=config
        )
    
    return _alert_scheduler


def start_alert_scheduler():
    """Start the global alert scheduler."""
    scheduler = get_alert_scheduler()
    scheduler.start()


def stop_alert_scheduler():
    """Stop the global alert scheduler."""
    global _alert_scheduler
    
    if _alert_scheduler:
        _alert_scheduler.stop()
        _alert_scheduler = None


def get_alert_status():
    """Get the status of the global alert scheduler."""
    global _alert_scheduler
    
    if _alert_scheduler:
        return _alert_scheduler.get_status()
    else:
        return {
            "is_running": False,
            "alert_enabled": False,
            "message": "Scheduler not initialized"
        }

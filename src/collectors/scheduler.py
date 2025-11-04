"""
Scheduler for automated cryptocurrency data collection.
Uses APScheduler to run collection tasks on a schedule.
"""

import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from enum import Enum

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from src.collectors.crypto_collector import CryptoCollector
from src.collectors.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class CollectorStatus(Enum):
    """Status of the collector scheduler."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class CollectorScheduler:
    """
    Scheduler for automated cryptocurrency data collection.
    
    Manages:
    - Scheduled collection based on cron expression
    - Manual trigger capability
    - Status tracking
    - Error handling and recovery
    """
    
    def __init__(
        self,
        binance_client: BinanceClient,
        crypto_collector: CryptoCollector,
        schedule_cron: str = "0 */6 * * *",  # Every 6 hours by default
        start_date: Optional[datetime] = None,
        timezone: str = "UTC"
    ):
        """
        Initialize collector scheduler.
        
        Args:
            binance_client: Binance API client instance.
            crypto_collector: CryptoCollector instance.
            schedule_cron: Cron expression for collection schedule.
            start_date: Start date for historical collection.
            timezone: Timezone for scheduler (default: UTC).
        """
        self.binance_client = binance_client
        self.crypto_collector = crypto_collector
        self.schedule_cron = schedule_cron
        self.start_date = start_date
        self.timezone = timezone
        
        # Status tracking
        self.status = CollectorStatus.IDLE
        self.last_run_time: Optional[datetime] = None
        self.last_run_success: Optional[bool] = None
        self.last_error: Optional[str] = None
        self.run_count = 0
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        logger.info(
            f"CollectorScheduler initialized with schedule: {schedule_cron} ({timezone})"
        )
    
    def start(self) -> None:
        """
        Start the scheduler.
        
        Begins automated collection based on the configured schedule.
        """
        if self.scheduler.running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Add scheduled job
            trigger = CronTrigger.from_crontab(self.schedule_cron, timezone=self.timezone)
            self.scheduler.add_job(
                func=self._scheduled_collection,
                trigger=trigger,
                id="crypto_collection",
                name="Cryptocurrency Data Collection",
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.status = CollectorStatus.IDLE
            
            logger.info(f"Scheduler started with cron: {self.schedule_cron}")
            
        except Exception as e:
            self.status = CollectorStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self) -> None:
        """
        Stop the scheduler.
        
        Stops automated collection. Running jobs will complete.
        """
        if not self.scheduler.running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.status = CollectorStatus.STOPPED
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            raise
    
    def trigger_manual_collection(
        self,
        collection_type: str = "forward",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        crypto_symbols: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Manually trigger data collection.
        
        Args:
            collection_type: Type of collection ('forward', 'backward', 'gap_fill').
            start_date: Start date for collection (for backward collection).
            end_date: End date for collection.
            crypto_symbols: Specific symbols to collect (default: top N).
        
        Returns:
            Dictionary with collection results.
        """
        if self.status == CollectorStatus.RUNNING:
            return {
                "success": False,
                "message": "Collection is already running",
                "status": self.status.value
            }
        
        logger.info(
            f"Manual collection triggered: type={collection_type}, "
            f"start={start_date}, end={end_date}"
        )
        
        try:
            self.status = CollectorStatus.RUNNING
            self.last_run_time = datetime.now()
            
            if collection_type == "backward":
                if start_date is None:
                    start_date = self.start_date
                if start_date is None:
                    return {
                        "success": False,
                        "message": "start_date is required for backward collection",
                        "status": self.status.value
                    }
                results = self.crypto_collector.collect_backward(
                    start_date=start_date,
                    end_date=end_date,
                    crypto_symbols=crypto_symbols
                )
            elif collection_type == "forward":
                results = self.crypto_collector.collect_forward(
                    end_date=end_date,
                    crypto_symbols=crypto_symbols
                )
            elif collection_type == "gap_fill":
                results = self.crypto_collector.detect_and_fill_gaps(
                    crypto_symbols=crypto_symbols,
                    start_date=start_date
                )
            else:
                return {
                    "success": False,
                    "message": f"Invalid collection type: {collection_type}",
                    "status": self.status.value
                }
            
            # Update status
            self.status = CollectorStatus.IDLE
            self.last_run_success = True
            self.run_count += 1
            
            # Prepare response
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            total_records = sum(r.records_collected for r in results)
            
            return {
                "success": True,
                "message": "Collection completed successfully",
                "status": self.status.value,
                "results": {
                    "total_cryptos": len(results),
                    "successful": successful,
                    "failed": failed,
                    "total_records": total_records,
                    "collection_type": collection_type
                }
            }
            
        except Exception as e:
            self.status = CollectorStatus.ERROR
            self.last_run_success = False
            self.last_error = str(e)
            logger.error(f"Manual collection failed: {e}")
            
            return {
                "success": False,
                "message": f"Collection failed: {str(e)}",
                "status": self.status.value,
                "error": str(e)
            }
    
    def _scheduled_collection(self) -> None:
        """
        Execute scheduled collection.
        
        This method is called automatically by the scheduler.
        Performs forward collection to update with latest data.
        """
        logger.info("Starting scheduled collection")
        
        try:
            self.status = CollectorStatus.RUNNING
            self.last_run_time = datetime.now()
            
            # Perform forward collection (update with latest data)
            results = self.crypto_collector.collect_forward()
            
            # Update status
            self.status = CollectorStatus.IDLE
            self.last_run_success = True
            self.run_count += 1
            
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            total_records = sum(r.records_collected for r in results)
            
            logger.info(
                f"Scheduled collection completed: "
                f"{successful} successful, {failed} failed, "
                f"{total_records} records collected"
            )
            
        except Exception as e:
            self.status = CollectorStatus.ERROR
            self.last_run_success = False
            self.last_error = str(e)
            logger.error(f"Scheduled collection failed: {e}", exc_info=True)
    
    def _job_listener(self, event) -> None:
        """
        Listen to scheduler job events.
        
        Args:
            event: APScheduler event.
        """
        if event.exception:
            logger.error(f"Job {event.job_id} raised an exception: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status.
        
        Returns:
            Dictionary with status information.
        """
        status_info = {
            "status": self.status.value,
            "is_running": self.scheduler.running if self.scheduler else False,
            "schedule": self.schedule_cron,
            "timezone": self.timezone,
            "run_count": self.run_count,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_success": self.last_run_success,
            "last_error": self.last_error
        }
        
        # Add next run time if scheduler is running
        if self.scheduler and self.scheduler.running:
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                status_info["next_run_time"] = next_run.isoformat() if next_run else None
        
        # Add collector status
        collector_status = self.crypto_collector.get_collection_status()
        status_info["collector"] = collector_status
        
        return status_info
    
    def get_schedule_info(self) -> Dict[str, Any]:
        """
        Get information about scheduled jobs.
        
        Returns:
            Dictionary with schedule information.
        """
        if not self.scheduler or not self.scheduler.running:
            return {
                "scheduler_running": False,
                "jobs": []
            }
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "scheduler_running": True,
            "jobs": jobs_info
        }
    
    def pause(self) -> None:
        """Pause the scheduler (jobs won't run but scheduler stays active)."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.pause()
            logger.info("Scheduler paused")
    
    def resume(self) -> None:
        """Resume the scheduler after pausing."""
        if self.scheduler:
            self.scheduler.resume()
            logger.info("Scheduler resumed")
    
    def is_running(self) -> bool:
        """
        Check if scheduler is running.
        
        Returns:
            True if scheduler is running, False otherwise.
        """
        return self.scheduler.running if self.scheduler else False


# Global scheduler instance
_collector_scheduler = None


def get_collector_scheduler() -> CollectorScheduler:
    """
    Get the global collector scheduler instance.
    
    Returns:
        CollectorScheduler instance
    """
    global _collector_scheduler
    
    if _collector_scheduler is None:
        from src.config.config_loader import load_config
        from src.collectors.binance_client import BinanceClient
        from src.collectors.crypto_collector import CryptoCollector
        from src.data.database import get_session_factory
        
        config = load_config()
        session_factory = get_session_factory(config.database_url)
        
        binance_client = BinanceClient(
            api_key=config.binance_api_key,
            api_secret=config.binance_api_secret
        )
        
        crypto_collector = CryptoCollector(
            binance_client=binance_client,
            session_factory=session_factory,
            top_n_cryptos=config.top_n_cryptos
        )
        
        _collector_scheduler = CollectorScheduler(
            binance_client=binance_client,
            crypto_collector=crypto_collector,
            schedule_cron=config.collection_schedule,
            start_date=config.collection_start_date
        )
    
    return _collector_scheduler


def start_collector_scheduler():
    """Start the global collector scheduler."""
    scheduler = get_collector_scheduler()
    scheduler.start()


def stop_collector_scheduler():
    """Stop the global collector scheduler."""
    global _collector_scheduler
    
    if _collector_scheduler:
        _collector_scheduler.stop()
        _collector_scheduler = None


def get_collector_status():
    """Get the status of the global collector scheduler."""
    global _collector_scheduler
    
    if _collector_scheduler:
        return _collector_scheduler.get_status()
    else:
        return {
            "status": "stopped",
            "is_running": False,
            "message": "Scheduler not initialized"
        }

"""
Log Retention Policy Implementation.
Handles automatic cleanup of old audit logs and chat history based on retention policies.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from dataclasses import dataclass
import os

from src.data.database import get_session
from src.utils.audit_logger import AuditLogger, AuditEventType, AuditSeverity
from src.data.repositories import ChatHistoryRepository, AuditLogRepository

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Retention policy configuration."""
    audit_logs_days: int = 90  # Keep audit logs for 90 days
    chat_history_days: int = 30  # Keep chat history for 30 days
    query_audit_logs_days: int = 365  # Keep query audit logs for 1 year (compliance)
    system_logs_days: int = 30  # Keep system logs for 30 days
    
    @classmethod
    def from_env(cls) -> 'RetentionPolicy':
        """Load retention policy from environment variables."""
        return cls(
            audit_logs_days=int(os.getenv('AUDIT_LOGS_RETENTION_DAYS', '90')),
            chat_history_days=int(os.getenv('CHAT_HISTORY_RETENTION_DAYS', '30')),
            query_audit_logs_days=int(os.getenv('QUERY_AUDIT_LOGS_RETENTION_DAYS', '365')),
            system_logs_days=int(os.getenv('SYSTEM_LOGS_RETENTION_DAYS', '30'))
        )


class LogRetentionManager:
    """
    Manages log retention policies and cleanup operations.
    """
    
    def __init__(self, retention_policy: RetentionPolicy = None):
        """
        Initialize log retention manager.
        
        Args:
            retention_policy: Retention policy configuration
        """
        self.policy = retention_policy or RetentionPolicy.from_env()
        
    def cleanup_all_logs(self) -> Dict[str, int]:
        """
        Clean up all logs according to retention policy.
        
        Returns:
            Dictionary with cleanup results for each log type
        """
        results = {}
        session = get_session()
        
        try:
            # Initialize components
            audit_logger = AuditLogger(session)
            chat_repo = ChatHistoryRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Clean up audit logs
            results['audit_logs'] = self._cleanup_audit_logs(audit_logger)
            
            # Clean up chat history
            results['chat_history'] = self._cleanup_chat_history(chat_repo)
            
            # Clean up query audit logs (longer retention for compliance)
            results['query_audit_logs'] = self._cleanup_query_audit_logs(audit_repo)
            
            # Log the cleanup operation
            total_deleted = sum(results.values())
            audit_logger.log_event(
                event_type=AuditEventType.ADMIN_ACTION,
                severity=AuditSeverity.LOW,
                message=f"Log retention cleanup completed: {total_deleted} records deleted",
                additional_data={
                    "cleanup_results": results,
                    "retention_policy": {
                        "audit_logs_days": self.policy.audit_logs_days,
                        "chat_history_days": self.policy.chat_history_days,
                        "query_audit_logs_days": self.policy.query_audit_logs_days
                    }
                }
            )
            
            logger.info(f"Log retention cleanup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during log retention cleanup: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()
    
    def _cleanup_audit_logs(self, audit_logger: AuditLogger) -> int:
        """Clean up old audit logs."""
        try:
            deleted_count = audit_logger.cleanup_old_logs(self.policy.audit_logs_days)
            logger.info(f"Cleaned up {deleted_count} audit logs older than {self.policy.audit_logs_days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up audit logs: {e}", exc_info=True)
            return 0
    
    def _cleanup_chat_history(self, chat_repo: ChatHistoryRepository) -> int:
        """Clean up old chat history."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.policy.chat_history_days)
            deleted_count = chat_repo.delete_old_chat_history(cutoff_date)
            logger.info(f"Cleaned up {deleted_count} chat history records older than {self.policy.chat_history_days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up chat history: {e}", exc_info=True)
            return 0
    
    def _cleanup_query_audit_logs(self, audit_repo: AuditLogRepository) -> int:
        """Clean up old query audit logs (longer retention for compliance)."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.policy.query_audit_logs_days)
            deleted_count = audit_repo.delete_old_audit_logs(cutoff_date)
            logger.info(f"Cleaned up {deleted_count} query audit logs older than {self.policy.query_audit_logs_days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up query audit logs: {e}", exc_info=True)
            return 0
    
    def get_retention_status(self) -> Dict[str, Any]:
        """
        Get current retention status and statistics.
        
        Returns:
            Dictionary with retention statistics
        """
        session = get_session()
        
        try:
            audit_logger = AuditLogger(session)
            chat_repo = ChatHistoryRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Calculate cutoff dates
            audit_cutoff = datetime.utcnow() - timedelta(days=self.policy.audit_logs_days)
            chat_cutoff = datetime.utcnow() - timedelta(days=self.policy.chat_history_days)
            query_audit_cutoff = datetime.utcnow() - timedelta(days=self.policy.query_audit_logs_days)
            
            # Get counts
            status = {
                "retention_policy": {
                    "audit_logs_days": self.policy.audit_logs_days,
                    "chat_history_days": self.policy.chat_history_days,
                    "query_audit_logs_days": self.policy.query_audit_logs_days
                },
                "current_counts": {
                    "total_audit_logs": session.query(audit_logger.AuditLog).count(),
                    "total_chat_history": chat_repo.get_total_count(),
                    "total_query_audit_logs": audit_repo.get_total_count()
                },
                "eligible_for_cleanup": {
                    "audit_logs": session.query(audit_logger.AuditLog)
                        .filter(audit_logger.AuditLog.created_at < audit_cutoff).count(),
                    "chat_history": chat_repo.count_old_records(chat_cutoff),
                    "query_audit_logs": audit_repo.count_old_records(query_audit_cutoff)
                },
                "cutoff_dates": {
                    "audit_logs": audit_cutoff.isoformat(),
                    "chat_history": chat_cutoff.isoformat(),
                    "query_audit_logs": query_audit_cutoff.isoformat()
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting retention status: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()
    
    def validate_retention_policy(self) -> Dict[str, Any]:
        """
        Validate the current retention policy.
        
        Returns:
            Dictionary with validation results
        """
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check minimum retention periods
        if self.policy.audit_logs_days < 30:
            validation["warnings"].append("Audit logs retention is less than 30 days - consider compliance requirements")
        
        if self.policy.query_audit_logs_days < 365:
            validation["warnings"].append("Query audit logs retention is less than 1 year - may not meet compliance requirements")
        
        if self.policy.chat_history_days < 7:
            validation["warnings"].append("Chat history retention is less than 7 days - may impact user experience")
        
        # Check maximum retention periods
        if self.policy.audit_logs_days > 2555:  # 7 years
            validation["warnings"].append("Audit logs retention is more than 7 years - consider storage costs")
        
        # Check for zero or negative values
        for field_name, value in [
            ("audit_logs_days", self.policy.audit_logs_days),
            ("chat_history_days", self.policy.chat_history_days),
            ("query_audit_logs_days", self.policy.query_audit_logs_days)
        ]:
            if value <= 0:
                validation["errors"].append(f"{field_name} must be greater than 0")
                validation["valid"] = False
        
        return validation


def run_log_retention_cleanup():
    """
    Entry point for scheduled log retention cleanup.
    Can be called from cron job or scheduler.
    """
    try:
        logger.info("Starting scheduled log retention cleanup")
        
        manager = LogRetentionManager()
        
        # Validate policy first
        validation = manager.validate_retention_policy()
        if not validation["valid"]:
            logger.error(f"Invalid retention policy: {validation['errors']}")
            return
        
        if validation["warnings"]:
            logger.warning(f"Retention policy warnings: {validation['warnings']}")
        
        # Run cleanup
        results = manager.cleanup_all_logs()
        
        logger.info(f"Log retention cleanup completed successfully: {results}")
        
    except Exception as e:
        logger.error(f"Failed to run log retention cleanup: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Allow running as standalone script
    run_log_retention_cleanup()
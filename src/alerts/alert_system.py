"""
Alert system orchestrator module.
Coordinates market shift detection and SMS notification sending.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import logging

from sqlalchemy.orm import Session

from src.alerts.market_monitor import MarketMonitor, MarketShift
from src.alerts.sms_gateway import SMSGateway, SMSGatewayFactory, SMSResult
from src.data.repositories import AlertLogRepository
from src.config.config_loader import Config

logger = logging.getLogger(__name__)


class AlertSystem:
    """
    Main coordinator for the alert system.
    Detects market shifts and sends SMS notifications.
    """
    
    def __init__(
        self,
        db_session: Session,
        config: Config,
        sms_gateway: Optional[SMSGateway] = None
    ):
        """
        Initialize alert system.
        
        Args:
            db_session: Database session for data access
            config: Application configuration
            sms_gateway: Optional SMS gateway instance (will be created if not provided)
        """
        self.db_session = db_session
        self.config = config
        self.alert_log_repo = AlertLogRepository(db_session)
        
        # Initialize market monitor
        self.market_monitor = MarketMonitor(
            db_session=db_session,
            threshold_percent=config.alert_threshold_percent,
            cooldown_hours=config.alert_cooldown_hours
        )
        
        # Initialize SMS gateway
        if sms_gateway:
            self.sms_gateway = sms_gateway
        else:
            self.sms_gateway = self._create_sms_gateway()
        
        logger.info(
            f"AlertSystem initialized (enabled={config.alert_enabled}, "
            f"threshold={config.alert_threshold_percent}%, "
            f"provider={config.sms_provider})"
        )
    
    def _create_sms_gateway(self) -> Optional[SMSGateway]:
        """
        Create SMS gateway based on configuration.
        
        Returns:
            SMSGateway instance or None if configuration is invalid
        """
        if not self.config.alert_enabled:
            logger.info("Alert system disabled in configuration")
            return None
        
        if not self.config.sms_phone_number:
            logger.warning("SMS phone number not configured, alerts disabled")
            return None
        
        try:
            if self.config.sms_provider == 'twilio':
                if not all([
                    self.config.twilio_account_sid,
                    self.config.twilio_auth_token,
                    self.config.twilio_from_number
                ]):
                    logger.warning("Twilio credentials incomplete, alerts disabled")
                    return None
                
                gateway = SMSGatewayFactory.create_gateway(
                    provider='twilio',
                    account_sid=self.config.twilio_account_sid,
                    auth_token=self.config.twilio_auth_token,
                    from_number=self.config.twilio_from_number
                )
                
            elif self.config.sms_provider == 'aws_sns':
                gateway = SMSGatewayFactory.create_gateway(
                    provider='aws_sns',
                    topic_arn=self.config.aws_sns_topic_arn,
                    region_name=self.config.aws_region or 'us-east-1'
                )
                
            else:
                logger.error(f"Unsupported SMS provider: {self.config.sms_provider}")
                return None
            
            if gateway and gateway.validate_config():
                logger.info(f"SMS gateway initialized: {self.config.sms_provider}")
                return gateway
            else:
                logger.warning("SMS gateway validation failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create SMS gateway: {e}", exc_info=True)
            return None
    
    def check_market_shifts(self) -> List[MarketShift]:
        """
        Check for market shifts and send alerts.
        
        This is the main method that should be called by the scheduler.
        It detects shifts, sends SMS notifications, and logs results.
        
        Returns:
            List of detected MarketShift objects
        """
        if not self.config.alert_enabled:
            logger.debug("Alert system disabled, skipping check")
            return []
        
        logger.info("Starting market shift check")
        
        try:
            # Detect market shifts
            shifts = self.market_monitor.detect_massive_shift()
            
            if not shifts:
                logger.info("No market shifts detected")
                return []
            
            logger.info(f"Detected {len(shifts)} market shifts")
            
            # Send alerts for each shift
            for shift in shifts:
                self._send_alert(shift)
            
            # Commit all changes
            self.db_session.commit()
            
            return shifts
            
        except Exception as e:
            logger.error(f"Error during market shift check: {e}", exc_info=True)
            self.db_session.rollback()
            return []
    
    def _send_alert(self, shift: MarketShift) -> bool:
        """
        Send SMS alert for a market shift.
        
        Args:
            shift: MarketShift object to alert about
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            # Format alert message
            message = self._format_alert_message(shift)
            
            # Send SMS if gateway is available
            if self.sms_gateway and self.config.sms_phone_number:
                result = self.sms_gateway.send_sms(
                    to_number=self.config.sms_phone_number,
                    message=message
                )
                
                # Log alert
                self._log_alert(shift, message, result)
                
                if result.success:
                    logger.info(f"Alert sent successfully for {shift.crypto_symbol}")
                    return True
                else:
                    logger.error(f"Failed to send alert for {shift.crypto_symbol}: {result.error}")
                    return False
            else:
                logger.warning("SMS gateway not available, alert not sent")
                # Still log the alert attempt
                self._log_alert(
                    shift,
                    message,
                    SMSResult(success=False, error="SMS gateway not configured")
                )
                return False
                
        except Exception as e:
            logger.error(f"Error sending alert for {shift.crypto_symbol}: {e}", exc_info=True)
            return False
    
    def _format_alert_message(self, shift: MarketShift) -> str:
        """
        Format alert message for SMS.
        
        Args:
            shift: MarketShift object
        
        Returns:
            Formatted message string
        """
        direction = "📈 SURGE" if shift.shift_type == "increase" else "📉 DROP"
        symbol = shift.crypto_symbol
        change = abs(shift.change_percent)
        prev_price = float(shift.previous_price)
        curr_price = float(shift.current_price)
        
        # Format timestamp
        time_str = shift.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        
        message = (
            f"{direction} ALERT: {symbol}\n"
            f"Change: {change:.2f}%\n"
            f"Price: ${prev_price:.2f} → ${curr_price:.2f}\n"
            f"Time: {time_str}"
        )
        
        return message
    
    def _log_alert(
        self,
        shift: MarketShift,
        message: str,
        result: SMSResult
    ) -> None:
        """
        Log alert to database.
        
        Args:
            shift: MarketShift object
            message: Alert message that was sent
            result: SMSResult from send operation
        """
        try:
            self.alert_log_repo.create(
                crypto_id=shift.crypto_id,
                shift_type=shift.shift_type,
                change_percent=Decimal(str(shift.change_percent)),
                previous_price=shift.previous_price,
                current_price=shift.current_price,
                alert_message=message,
                recipient_number=self.config.sms_phone_number or "N/A",
                sms_provider=self.config.sms_provider,
                timestamp=shift.timestamp,
                sms_message_id=result.message_id,
                success=result.success,
                error_message=result.error
            )
            logger.debug(f"Alert logged for {shift.crypto_symbol}")
            
        except Exception as e:
            logger.error(f"Failed to log alert: {e}", exc_info=True)
    
    def get_alert_statistics(self) -> dict:
        """
        Get statistics about sent alerts.
        
        Returns:
            Dictionary with alert statistics
        """
        try:
            recent_alerts = self.alert_log_repo.get_recent_alerts(limit=100)
            failed_alerts = self.alert_log_repo.get_failed_alerts(limit=100)
            
            total_alerts = len(recent_alerts)
            successful_alerts = sum(1 for a in recent_alerts if a.success)
            failed_count = len(failed_alerts)
            
            success_rate = (
                (successful_alerts / total_alerts * 100)
                if total_alerts > 0 else 0
            )
            
            return {
                'total_alerts': total_alerts,
                'successful_alerts': successful_alerts,
                'failed_alerts': failed_count,
                'success_rate': round(success_rate, 2),
                'last_alert': recent_alerts[0].timestamp if recent_alerts else None
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}", exc_info=True)
            return {
                'total_alerts': 0,
                'successful_alerts': 0,
                'failed_alerts': 0,
                'success_rate': 0,
                'last_alert': None
            }
    
    def test_alert(self, test_message: str = "Test alert from Crypto Market Analysis") -> bool:
        """
        Send a test alert to verify SMS configuration.
        
        Args:
            test_message: Message to send for testing
        
        Returns:
            True if test alert sent successfully, False otherwise
        """
        if not self.sms_gateway:
            logger.error("SMS gateway not configured")
            return False
        
        if not self.config.sms_phone_number:
            logger.error("SMS phone number not configured")
            return False
        
        try:
            logger.info("Sending test alert")
            result = self.sms_gateway.send_sms(
                to_number=self.config.sms_phone_number,
                message=test_message
            )
            
            if result.success:
                logger.info(f"Test alert sent successfully: {result.message_id}")
                return True
            else:
                logger.error(f"Test alert failed: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending test alert: {e}", exc_info=True)
            return False

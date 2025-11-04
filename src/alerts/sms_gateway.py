"""
SMS gateway integration module.
Provides abstraction for multiple SMS providers (Twilio, AWS SNS).
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SMSResult:
    """Result of SMS send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    def __str__(self):
        if self.success:
            return f"SMS sent successfully (ID: {self.message_id})"
        else:
            return f"SMS failed: {self.error}"


class SMSGateway(ABC):
    """
    Abstract base class for SMS gateway providers.
    Defines interface for sending SMS messages.
    """
    
    @abstractmethod
    def send_sms(self, to_number: str, message: str) -> SMSResult:
        """
        Send SMS message.
        
        Args:
            to_number: Recipient phone number in E.164 format (+1234567890)
            message: Message text to send
        
        Returns:
            SMSResult indicating success or failure
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate gateway configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass


class TwilioGateway(SMSGateway):
    """
    Twilio SMS gateway implementation.
    Uses Twilio API to send SMS messages.
    """
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        max_retries: int = 3
    ):
        """
        Initialize Twilio gateway.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number to send from
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.max_retries = max_retries
        self.client = None
        
        # Initialize Twilio client
        try:
            from twilio.rest import Client
            self.client = Client(account_sid, auth_token)
            logger.info("Twilio gateway initialized successfully")
        except ImportError:
            logger.error("Twilio library not installed. Install with: pip install twilio")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            raise
    
    def validate_config(self) -> bool:
        """
        Validate Twilio configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.error("Twilio configuration incomplete")
            return False
        
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        # Validate phone number format
        if not self.from_number.startswith('+'):
            logger.error(f"Invalid from_number format: {self.from_number}")
            return False
        
        return True
    
    def send_sms(self, to_number: str, message: str) -> SMSResult:
        """
        Send SMS via Twilio.
        
        Args:
            to_number: Recipient phone number in E.164 format
            message: Message text to send
        
        Returns:
            SMSResult indicating success or failure
        """
        if not self.validate_config():
            return SMSResult(
                success=False,
                error="Invalid Twilio configuration"
            )
        
        # Validate recipient number format
        if not to_number.startswith('+'):
            logger.error(f"Invalid to_number format: {to_number}")
            return SMSResult(
                success=False,
                error=f"Invalid phone number format: {to_number}"
            )
        
        # Attempt to send with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Sending SMS to {to_number} (attempt {attempt + 1}/{self.max_retries})"
                )
                
                message_obj = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
                
                logger.info(f"SMS sent successfully: {message_obj.sid}")
                return SMSResult(
                    success=True,
                    message_id=message_obj.sid
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"SMS send attempt {attempt + 1} failed: {e}"
                )
                
                # Don't retry on certain errors
                if "invalid" in str(e).lower() or "not found" in str(e).lower():
                    break
        
        # All retries failed
        logger.error(f"Failed to send SMS after {self.max_retries} attempts: {last_error}")
        return SMSResult(
            success=False,
            error=last_error
        )


class AWSSNSGateway(SMSGateway):
    """
    AWS SNS SMS gateway implementation.
    Uses AWS SNS to send SMS messages.
    """
    
    def __init__(
        self,
        topic_arn: Optional[str] = None,
        region_name: str = 'us-east-1',
        max_retries: int = 3
    ):
        """
        Initialize AWS SNS gateway.
        
        Args:
            topic_arn: SNS topic ARN (optional, can send direct SMS without topic)
            region_name: AWS region name (default: us-east-1)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.topic_arn = topic_arn
        self.region_name = region_name
        self.max_retries = max_retries
        self.client = None
        
        # Initialize SNS client
        try:
            import boto3
            self.client = boto3.client('sns', region_name=region_name)
            logger.info(f"AWS SNS gateway initialized for region {region_name}")
        except ImportError:
            logger.error("boto3 library not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS SNS client: {e}")
            raise
    
    def validate_config(self) -> bool:
        """
        Validate AWS SNS configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.client:
            logger.error("AWS SNS client not initialized")
            return False
        
        # Topic ARN is optional for direct SMS
        if self.topic_arn and not self.topic_arn.startswith('arn:aws:sns:'):
            logger.error(f"Invalid SNS topic ARN format: {self.topic_arn}")
            return False
        
        return True
    
    def send_sms(self, to_number: str, message: str) -> SMSResult:
        """
        Send SMS via AWS SNS.
        
        Args:
            to_number: Recipient phone number in E.164 format
            message: Message text to send
        
        Returns:
            SMSResult indicating success or failure
        """
        if not self.validate_config():
            return SMSResult(
                success=False,
                error="Invalid AWS SNS configuration"
            )
        
        # Validate recipient number format
        if not to_number.startswith('+'):
            logger.error(f"Invalid to_number format: {to_number}")
            return SMSResult(
                success=False,
                error=f"Invalid phone number format: {to_number}"
            )
        
        # Attempt to send with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Sending SMS to {to_number} via SNS "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                
                # Send direct SMS (not via topic)
                response = self.client.publish(
                    PhoneNumber=to_number,
                    Message=message,
                    MessageAttributes={
                        'AWS.SNS.SMS.SMSType': {
                            'DataType': 'String',
                            'StringValue': 'Transactional'  # For critical alerts
                        }
                    }
                )
                
                message_id = response.get('MessageId')
                logger.info(f"SMS sent successfully via SNS: {message_id}")
                return SMSResult(
                    success=True,
                    message_id=message_id
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"SMS send attempt {attempt + 1} failed: {e}"
                )
                
                # Don't retry on certain errors
                if "invalid" in str(e).lower() or "not authorized" in str(e).lower():
                    break
        
        # All retries failed
        logger.error(f"Failed to send SMS via SNS after {self.max_retries} attempts: {last_error}")
        return SMSResult(
            success=False,
            error=last_error
        )


class SMSGatewayFactory:
    """
    Factory for creating SMS gateway instances based on configuration.
    """
    
    @staticmethod
    def create_gateway(
        provider: str,
        **kwargs
    ) -> Optional[SMSGateway]:
        """
        Create SMS gateway instance based on provider.
        
        Args:
            provider: Provider name ('twilio' or 'aws_sns')
            **kwargs: Provider-specific configuration
        
        Returns:
            SMSGateway instance or None if provider not supported
        
        Raises:
            ValueError: If required configuration is missing
        """
        provider = provider.lower()
        
        if provider == 'twilio':
            required = ['account_sid', 'auth_token', 'from_number']
            missing = [k for k in required if k not in kwargs]
            if missing:
                raise ValueError(f"Missing Twilio configuration: {missing}")
            
            return TwilioGateway(
                account_sid=kwargs['account_sid'],
                auth_token=kwargs['auth_token'],
                from_number=kwargs['from_number'],
                max_retries=kwargs.get('max_retries', 3)
            )
        
        elif provider == 'aws_sns':
            return AWSSNSGateway(
                topic_arn=kwargs.get('topic_arn'),
                region_name=kwargs.get('region_name', 'us-east-1'),
                max_retries=kwargs.get('max_retries', 3)
            )
        
        else:
            logger.error(f"Unsupported SMS provider: {provider}")
            return None

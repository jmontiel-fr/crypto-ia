"""
Alert system package.
Provides market shift detection and SMS notification functionality.
"""

from src.alerts.market_monitor import MarketMonitor, MarketShift
from src.alerts.sms_gateway import (
    SMSGateway,
    TwilioGateway,
    AWSSNSGateway,
    SMSGatewayFactory,
    SMSResult
)
from src.alerts.alert_system import AlertSystem
from src.alerts.alert_scheduler import AlertScheduler

__all__ = [
    'MarketMonitor',
    'MarketShift',
    'SMSGateway',
    'TwilioGateway',
    'AWSSNSGateway',
    'SMSGatewayFactory',
    'SMSResult',
    'AlertSystem',
    'AlertScheduler',
]

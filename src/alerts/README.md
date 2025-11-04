# Alert System Module

This module provides market shift detection and SMS notification functionality for the Crypto Market Analysis SaaS platform.

## Overview

The alert system monitors cryptocurrency prices hourly and sends SMS notifications when massive market shifts are detected (price changes exceeding a configurable threshold).

## Components

### 1. MarketMonitor (`market_monitor.py`)

Analyzes hourly price changes to detect massive market shifts.

**Key Features:**
- Configurable threshold percentage for shift detection
- Cooldown mechanism to prevent alert spam (max 1 alert per crypto per N hours)
- Detects both increases and decreases
- Tracks last alert time for each cryptocurrency

**Usage:**
```python
from src.alerts import MarketMonitor

monitor = MarketMonitor(
    db_session=session,
    threshold_percent=10.0,  # Alert on 10% changes
    cooldown_hours=4         # Wait 4 hours between alerts
)

# Detect shifts for all tracked cryptocurrencies
shifts = monitor.detect_massive_shift()

for shift in shifts:
    print(f"{shift.crypto_symbol}: {shift.change_percent:.2f}%")
```

### 2. SMS Gateway (`sms_gateway.py`)

Provides abstraction for multiple SMS providers with retry logic.

**Supported Providers:**
- **Twilio**: Primary SMS provider
- **AWS SNS**: Alternative for AWS deployments

**Usage:**
```python
from src.alerts import SMSGatewayFactory

# Create Twilio gateway
gateway = SMSGatewayFactory.create_gateway(
    provider='twilio',
    account_sid='your_account_sid',
    auth_token='your_auth_token',
    from_number='+1234567890'
)

# Send SMS
result = gateway.send_sms(
    to_number='+1234567890',
    message='BTC surged 12% in the last hour!'
)

if result.success:
    print(f"SMS sent: {result.message_id}")
else:
    print(f"Failed: {result.error}")
```

### 3. AlertSystem (`alert_system.py`)

Main coordinator that orchestrates shift detection and notification sending.

**Key Features:**
- Integrates MarketMonitor and SMS Gateway
- Formats alert messages with crypto symbol, change %, prices, and timestamp
- Logs all alerts to database for audit trail
- Provides alert statistics and testing functionality

**Usage:**
```python
from src.alerts import AlertSystem
from src.config import load_config

config = load_config()
alert_system = AlertSystem(
    db_session=session,
    config=config
)

# Check for shifts and send alerts
shifts = alert_system.check_market_shifts()

# Get statistics
stats = alert_system.get_alert_statistics()
print(f"Success rate: {stats['success_rate']}%")

# Test SMS configuration
alert_system.test_alert("Test message")
```

### 4. AlertScheduler (`alert_scheduler.py`)

Manages scheduled execution using APScheduler.

**Key Features:**
- Hourly execution at the top of each hour
- Error handling and retry logic
- Status tracking and health checks
- Manual trigger capability

**Usage:**
```python
from src.alerts import AlertScheduler
from src.data.database import SessionLocal
from src.config import load_config

config = load_config()
scheduler = AlertScheduler(
    session_factory=SessionLocal,
    config=config
)

# Start scheduler
scheduler.start()

# Get status
status = scheduler.get_status()
print(f"Next run: {status['next_run_time']}")

# Manual trigger
scheduler.run_now()

# Stop scheduler
scheduler.stop()
```

## Configuration

Alert system configuration is managed through environment variables:

```bash
# Enable/disable alert system
ALERT_ENABLED=true

# Threshold percentage for market shift detection
ALERT_THRESHOLD_PERCENT=10.0

# Cooldown period between alerts for same crypto (hours)
ALERT_COOLDOWN_HOURS=4

# SMS provider: twilio or aws_sns
SMS_PROVIDER=twilio

# Phone number to receive alerts (E.164 format)
SMS_PHONE_NUMBER=+1234567890

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+1234567890

# AWS SNS Configuration (alternative)
AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:crypto-alerts
AWS_REGION=us-east-1
```

## Database Schema

### AlertLog Table

Stores information about sent alerts for audit trail:

```sql
CREATE TABLE alert_logs (
    id SERIAL PRIMARY KEY,
    crypto_id INTEGER REFERENCES cryptocurrencies(id),
    shift_type VARCHAR(20) NOT NULL,  -- 'increase' or 'decrease'
    change_percent NUMERIC(10, 2) NOT NULL,
    previous_price NUMERIC(20, 8) NOT NULL,
    current_price NUMERIC(20, 8) NOT NULL,
    alert_message TEXT NOT NULL,
    recipient_number VARCHAR(20) NOT NULL,
    sms_provider VARCHAR(20) NOT NULL,
    sms_message_id VARCHAR(100),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Alert Message Format

SMS alerts are formatted as follows:

```
📈 SURGE ALERT: BTC
Change: 12.50%
Price: $45000.00 → $50625.00
Time: 2025-11-01 14:00 UTC
```

or

```
📉 DROP ALERT: ETH
Change: 10.25%
Price: $3000.00 → $2692.50
Time: 2025-11-01 14:00 UTC
```

## Error Handling

The alert system includes comprehensive error handling:

1. **SMS Send Failures**: Automatic retry with exponential backoff (max 3 attempts)
2. **Database Errors**: Transaction rollback and logging
3. **Configuration Errors**: Graceful degradation (alerts disabled if config invalid)
4. **Network Errors**: Retry logic with timeout handling

All errors are logged to the application log file and can be monitored via CloudWatch.

## Testing

### Test SMS Configuration

```python
from src.alerts import AlertSystem

alert_system = AlertSystem(db_session, config)
success = alert_system.test_alert("Test message from Crypto Analysis")
```

### Manual Alert Check

```python
from src.alerts import AlertScheduler

scheduler = AlertScheduler(SessionLocal, config)
scheduler.run_now()
```

## Monitoring

### Alert Statistics

```python
stats = alert_system.get_alert_statistics()
# Returns:
# {
#     'total_alerts': 150,
#     'successful_alerts': 145,
#     'failed_alerts': 5,
#     'success_rate': 96.67,
#     'last_alert': datetime(2025, 11, 1, 14, 0, 0)
# }
```

### Scheduler Status

```python
status = scheduler.get_status()
# Returns:
# {
#     'is_running': True,
#     'alert_enabled': True,
#     'last_run_time': datetime(2025, 11, 1, 14, 0, 0),
#     'last_run_status': 'success',
#     'next_run_time': datetime(2025, 11, 1, 15, 0, 0),
#     'error_count': 0,
#     'threshold_percent': 10.0,
#     'cooldown_hours': 4,
#     'sms_provider': 'twilio'
# }
```

## Integration with Main Application

The alert scheduler should be started when the application starts:

```python
# In main.py or app startup
from src.alerts import AlertScheduler
from src.data.database import SessionLocal
from src.config import load_config

config = load_config()
alert_scheduler = AlertScheduler(SessionLocal, config)
alert_scheduler.start()

# Register shutdown handler
import atexit
atexit.register(alert_scheduler.stop)
```

## Cost Considerations

### Twilio Pricing (approximate)
- SMS: $0.0075 per message (US)
- With 24 hourly checks per day and 10% shift probability: ~$0.018/day = ~$0.54/month

### AWS SNS Pricing (approximate)
- SMS: $0.00645 per message (US)
- Similar usage: ~$0.015/day = ~$0.46/month

## Security Considerations

1. **Credentials**: Store SMS provider credentials in environment variables or AWS Secrets Manager
2. **Phone Numbers**: Validate E.164 format before sending
3. **Rate Limiting**: Cooldown mechanism prevents SMS spam
4. **Audit Trail**: All alerts logged to database with full traceability
5. **Error Logging**: Sensitive data (credentials) never logged

## Future Enhancements

- Multiple recipient support
- Alert priority levels (critical, warning, info)
- Email notifications as alternative to SMS
- Webhook notifications for integration with other systems
- Alert templates for customizable messages
- Alert rules engine for complex conditions

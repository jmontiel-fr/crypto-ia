# Security & Conformance Guide - Crypto Market Analysis SaaS

This guide documents the security measures, compliance considerations, and best practices implemented in the Crypto Market Analysis SaaS.

## Table of Contents

- [Security Overview](#security-overview)
- [Data Protection](#data-protection)
- [PII Protection Mechanisms](#pii-protection-mechanisms)
- [Network Security](#network-security)
- [Authentication & Authorization](#authentication--authorization)
- [Audit Logging & Monitoring](#audit-logging--monitoring)
- [Compliance Considerations](#compliance-considerations)
- [Incident Response](#incident-response)
- [Security Best Practices](#security-best-practices)
- [Secrets Management](#secrets-management)

## Security Overview

The Crypto Market Analysis SaaS implements a comprehensive security framework designed to protect user data, ensure system integrity, and maintain compliance with industry standards.

### Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimal access rights for all components
3. **Zero Trust**: Verify everything, trust nothing
4. **Privacy by Design**: Data protection built into the system
5. **Continuous Monitoring**: Real-time security monitoring and alerting

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Network Security (AWS Security Groups, SSL/TLS)         │
│ 2. Application Security (Input validation, CSRF protection)│
│ 3. Data Security (Encryption at rest/transit, PII filtering)│
│ 4. Access Control (API keys, rate limiting)                │
│ 5. Monitoring (Audit logs, intrusion detection)            │
│ 6. Compliance (GDPR, data retention, audit trails)         │
└─────────────────────────────────────────────────────────────┘
```

## Data Protection

### Encryption

**Data in Transit:**
- All communications use TLS 1.2+ encryption
- HTTPS enforced for all web traffic
- API calls encrypted end-to-end
- Database connections use SSL/TLS

**Data at Rest:**
- EBS volumes encrypted with AWS KMS
- Database files encrypted on disk
- Log files stored with encryption
- Backup files encrypted before storage

**Implementation:**
```bash
# SSL/TLS Configuration
SSL_CERT_PATH=/etc/ssl/certs/crypto-saas.crt
SSL_KEY_PATH=/etc/ssl/private/crypto-saas.key

# Database encryption
DATABASE_URL=postgresql://user:pass@localhost:5432/db?sslmode=require

# EBS encryption (Terraform)
resource "aws_ebs_volume" "encrypted" {
  encrypted = true
  kms_key_id = aws_kms_key.main.arn
}
```

### Data Classification

**Public Data:**
- Cryptocurrency prices and market data
- General market trends and analysis
- Public API documentation

**Internal Data:**
- System configuration and logs
- Performance metrics
- Application code and algorithms

**Confidential Data:**
- User queries and chat history
- API keys and credentials
- Audit logs and security events

**Restricted Data:**
- Any personally identifiable information (PII)
- Authentication tokens
- Encryption keys

### Data Retention

**Automated Retention Policies:**
- **Chat History**: 30 days (configurable)
- **Audit Logs**: 90 days (configurable)
- **Query Audit Logs**: 365 days (compliance requirement)
- **System Logs**: 30 days (configurable)

**Implementation:**
```python
# Log retention configuration
AUDIT_LOGS_RETENTION_DAYS=90
CHAT_HISTORY_RETENTION_DAYS=30
QUERY_AUDIT_LOGS_RETENTION_DAYS=365
SYSTEM_LOGS_RETENTION_DAYS=30

# Automated cleanup
from src.utils.log_retention import LogRetentionManager
manager = LogRetentionManager()
manager.cleanup_all_logs()
```

## PII Protection Mechanisms

### Multi-Layer PII Detection

The system implements comprehensive PII detection to prevent personal information from being processed or stored.

#### Detection Methods

**1. Regex Pattern Matching:**
```python
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
}
```

**2. Named Entity Recognition (NER):**
```python
import spacy
nlp = spacy.load("en_core_web_sm")

def detect_names(text):
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
```

**3. Financial Data Detection:**
```python
FINANCIAL_PATTERNS = {
    'bank_account': r'\b\d{8,17}\b',
    'routing_number': r'\b\d{9}\b',
    'iban': r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'
}
```

#### PII Handling Workflow

```mermaid
graph TD
    A[User Input] --> B[PII Detection]
    B --> C{PII Found?}
    C -->|Yes| D[Block Request]
    C -->|No| E[Process Request]
    D --> F[Log Security Event]
    E --> G[Sanitize for Logs]
    F --> H[Return Error Message]
    G --> I[Store Sanitized Data]
```

#### Implementation Example

```python
from src.genai.pii_filter import PIIFilter

def process_user_query(question: str, session_id: str):
    pii_filter = PIIFilter()
    
    # Detect PII
    pii_result = pii_filter.contains_pii(question)
    
    if pii_result.contains_pii:
        # Log security event
        audit_logger.log_pii_detection(
            session_id=session_id,
            patterns=pii_result.patterns_found,
            question_sanitized=pii_result.sanitized_text
        )
        
        # Return error to user
        return {
            "error": "Personal information detected. Please remove personal details and try again.",
            "rejected": True
        }
    
    # Process query normally
    return process_query(question, session_id)
```

### PII Protection Features

**Automatic Blocking:**
- Queries containing PII are automatically rejected
- User receives friendly error message
- No PII is processed or stored

**Sanitization:**
- PII is removed from logs and audit trails
- Sanitized versions stored for compliance
- Original PII never persists in system

**Pattern Tracking:**
- Types of PII detected are logged
- Trends analyzed for security improvements
- No actual PII values stored

## Network Security

### AWS Security Groups

**Inbound Rules:**
```hcl
# SSH access (port 22) - Developer IP only
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["203.0.113.42/32"]  # Your IP only
}

# HTTPS access (port 443) - Developer IP only
ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["203.0.113.42/32"]  # Your IP only
}

# Custom HTTPS port (10443) - Developer IP only
ingress {
  from_port   = 10443
  to_port     = 10443
  protocol    = "tcp"
  cidr_blocks = ["203.0.113.42/32"]  # Your IP only
}
```

**Outbound Rules:**
```hcl
# All outbound traffic allowed (for API calls, updates)
egress {
  from_port   = 0
  to_port     = 0
  protocol    = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}
```

### SSL/TLS Configuration

**Certificate Management:**
- Self-signed certificates for development
- Let's Encrypt or commercial certificates for production
- Automatic certificate renewal
- Strong cipher suites only

**Nginx SSL Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name crypto-ai.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/crypto-saas.crt;
    ssl_certificate_key /etc/ssl/private/crypto-saas.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

### Network Monitoring

**fail2ban Configuration:**
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/secure
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
```

## Authentication & Authorization

### API Authentication

**Development Environment:**
- No authentication required for ease of development
- Rate limiting still enforced

**Production Environment:**
- API key required for all endpoints
- Keys generated with cryptographically secure random values
- Key rotation supported

**Implementation:**
```python
from src.api.middleware.auth import require_api_key

@app.before_request
def check_api_key():
    if request.path in ['/health', '/']:
        return None
    return require_api_key()
```

### Rate Limiting

**Default Limits:**
- 100 requests per minute per IP address
- Configurable per endpoint
- Burst protection with token bucket algorithm

**Implementation:**
```python
from src.api.middleware.rate_limiter import RateLimiter

rate_limiter = RateLimiter(requests_per_minute=100)

@app.before_request
def check_rate_limit():
    if request.path == '/health':
        return None
    return rate_limiter.check_rate_limit(request)
```

### Access Control

**Role-Based Access:**
- **Public**: Health checks, basic API access
- **User**: Chat queries, predictions, market data
- **Admin**: System management, audit logs, configuration

**Session Management:**
- Session-based tracking for chat continuity
- No persistent user sessions
- Session data expires after inactivity

## Audit Logging & Monitoring

### Comprehensive Audit Trail

**All Events Logged:**
- API requests and responses
- Chat queries (sanitized)
- PII detection events
- Authentication attempts
- System errors and exceptions
- Configuration changes

**Audit Log Structure:**
```python
@dataclass
class AuditEvent:
    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    additional_data: Optional[Dict[str, Any]]
    timestamp: datetime
```

### Security Event Types

**Authentication Events:**
- `AUTH_SUCCESS` - Successful API key validation
- `AUTH_FAILURE` - Failed authentication attempt
- `API_KEY_CREATED` - New API key generated
- `API_KEY_REVOKED` - API key revoked

**Security Events:**
- `PII_DETECTED` - Personal information detected and blocked
- `SQL_INJECTION_ATTEMPT` - SQL injection attempt detected
- `XSS_ATTEMPT` - Cross-site scripting attempt
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded

**Data Access Events:**
- `PREDICTION_ACCESSED` - Prediction data accessed
- `MARKET_DATA_ACCESSED` - Market data accessed
- `CHAT_QUERY_PROCESSED` - Chat query processed

### Query Tracing

**Complete Query Lifecycle:**
```python
# Query audit log entry
{
    "session_id": "user-session-123",
    "question_sanitized": "What are the best cryptos to invest in?",
    "pii_patterns_detected": [],
    "topic_validation_result": "valid_crypto_topic",
    "ip_address": "203.0.113.42",
    "user_agent": "Mozilla/5.0...",
    "rejected": false,
    "openai_tokens_input": 150,
    "openai_tokens_output": 300,
    "openai_cost_usd": 0.0002,
    "response_time_ms": 2500,
    "timestamp": "2025-11-01T14:30:00Z"
}
```

### Cost Tracking

**OpenAI Usage Monitoring:**
- Token usage per query
- Cost calculation per request
- Daily/monthly usage summaries
- Budget alerts and limits

**Implementation:**
```python
def log_openai_usage(session_id: str, input_tokens: int, 
                    output_tokens: int, cost_usd: float):
    audit_logger.log_openai_usage(
        session_id=session_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        response_time_ms=response_time_ms,
        model="gpt-4o-mini"
    )
```

### Real-Time Monitoring

**CloudWatch Integration:**
- Application logs streamed to CloudWatch
- Custom metrics for security events
- Automated alerting for critical events

**Metrics Tracked:**
- Request volume and response times
- Error rates by endpoint
- PII detection frequency
- Authentication failure rates
- Resource utilization

## Compliance Considerations

### GDPR Compliance

**Data Protection Principles:**
1. **Lawfulness**: Processing based on legitimate interest
2. **Purpose Limitation**: Data used only for stated purposes
3. **Data Minimization**: Only necessary data collected
4. **Accuracy**: Data kept accurate and up-to-date
5. **Storage Limitation**: Data retained only as long as necessary
6. **Security**: Appropriate security measures implemented

**GDPR Implementation:**
```python
# Right to be forgotten
def delete_user_data(session_id: str):
    # Delete chat history
    chat_repo.delete_by_session(session_id)
    
    # Anonymize audit logs
    audit_repo.anonymize_session(session_id)
    
    # Remove from caches
    cache.delete_session_data(session_id)
```

**Data Subject Rights:**
- **Right to Access**: Users can request their data
- **Right to Rectification**: Data can be corrected
- **Right to Erasure**: Data can be deleted on request
- **Right to Portability**: Data can be exported
- **Right to Object**: Users can opt out of processing

### Data Retention Policies

**Retention Periods:**
- **Chat History**: 30 days (user convenience)
- **Audit Logs**: 90 days (security monitoring)
- **Query Audit Logs**: 365 days (compliance requirement)
- **System Logs**: 30 days (operational needs)

**Automated Cleanup:**
```python
# Daily retention cleanup
@scheduler.scheduled_job('cron', hour=2)
def cleanup_old_data():
    retention_manager = LogRetentionManager()
    results = retention_manager.cleanup_all_logs()
    logger.info(f"Retention cleanup: {results}")
```

### Compliance Monitoring

**Audit Dashboard:**
- PII detection statistics
- Data retention compliance
- Access control effectiveness
- Security event trends

**Compliance Reports:**
- Monthly security summaries
- Data processing activities
- Incident response logs
- Risk assessments

## Incident Response

### Incident Classification

**Severity Levels:**
- **Critical**: System compromise, data breach
- **High**: Service disruption, security vulnerability
- **Medium**: Performance degradation, minor security issue
- **Low**: Informational, routine maintenance

### Response Procedures

**Immediate Response (0-1 hours):**
1. **Assess Impact**: Determine scope and severity
2. **Contain Threat**: Isolate affected systems
3. **Notify Stakeholders**: Alert relevant personnel
4. **Document Incident**: Create incident record

**Investigation Phase (1-24 hours):**
1. **Collect Evidence**: Gather logs and forensic data
2. **Analyze Root Cause**: Determine how incident occurred
3. **Assess Damage**: Evaluate impact and data exposure
4. **Implement Fixes**: Apply immediate remediation

**Recovery Phase (24-72 hours):**
1. **Restore Services**: Bring systems back online
2. **Verify Security**: Ensure threats are eliminated
3. **Monitor Systems**: Watch for recurring issues
4. **Update Documentation**: Record lessons learned

### Incident Response Team

**Roles and Responsibilities:**
- **Incident Commander**: Overall response coordination
- **Security Analyst**: Threat analysis and containment
- **System Administrator**: Technical remediation
- **Communications Lead**: Stakeholder notifications

### Communication Plan

**Internal Communications:**
- Immediate notification via monitoring alerts
- Regular status updates during incident
- Post-incident review and documentation

**External Communications:**
- User notifications for service disruptions
- Regulatory notifications if required
- Public disclosure for significant incidents

### Recovery Procedures

**System Recovery:**
```bash
# Emergency procedures
./local-scripts/control-remote.sh stop
./local-scripts/deploy-to-aws.sh --skip-terraform
./local-scripts/control-remote.sh start
./local-scripts/control-remote.sh health
```

**Data Recovery:**
```bash
# Database restoration
sudo -u postgres pg_restore -d crypto_db backup.sql
sudo systemctl restart crypto-saas-*
```

## Security Best Practices

### Development Security

**Secure Coding Practices:**
- Input validation on all user inputs
- Parameterized queries to prevent SQL injection
- Output encoding to prevent XSS
- Proper error handling without information disclosure

**Code Review Process:**
- Security-focused code reviews
- Automated security scanning
- Dependency vulnerability checks
- Regular security updates

### Deployment Security

**Infrastructure Security:**
- Minimal attack surface
- Regular security updates
- Network segmentation
- Monitoring and alerting

**Configuration Management:**
- Secure defaults
- Configuration validation
- Change management process
- Version control for configurations

### Operational Security

**Access Management:**
- Principle of least privilege
- Regular access reviews
- Strong authentication requirements
- Session management

**Monitoring and Response:**
- Continuous security monitoring
- Automated threat detection
- Incident response procedures
- Regular security assessments

### User Security

**Privacy Protection:**
- PII detection and blocking
- Data minimization
- Transparent privacy practices
- User control over data

**Communication Security:**
- End-to-end encryption
- Secure protocols only
- Certificate validation
- Security headers

## Secrets Management

### Secret Types

**API Keys:**
- OpenAI API keys
- Binance API credentials
- Twilio authentication tokens
- AWS access keys

**Certificates:**
- SSL/TLS certificates
- Private keys
- Certificate authorities

**Database Credentials:**
- Database passwords
- Connection strings
- Encryption keys

### Storage Methods

**Development Environment:**
```bash
# Local environment file
OPENAI_API_KEY=sk-your-key-here
BINANCE_API_KEY=your-binance-key
DATABASE_URL=postgresql://user:pass@localhost/db
```

**Production Environment:**
```bash
# AWS Secrets Manager (recommended)
aws secretsmanager create-secret \
  --name crypto-saas/openai-key \
  --secret-string "sk-your-actual-key"

# Environment variables (alternative)
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id crypto-saas/openai-key \
  --query SecretString --output text)
```

### Secret Rotation

**Automated Rotation:**
```python
# API key rotation
def rotate_api_key():
    # Generate new key
    new_key = generate_secure_key()
    
    # Update in secrets manager
    update_secret('crypto-saas/api-key', new_key)
    
    # Update application configuration
    restart_services()
    
    # Revoke old key
    revoke_old_key()
```

**Rotation Schedule:**
- **API Keys**: Every 90 days
- **Database Passwords**: Every 180 days
- **SSL Certificates**: Before expiration
- **Encryption Keys**: Annually

### Security Controls

**Access Control:**
- Secrets accessible only to authorized services
- Role-based access to secret management
- Audit logging for all secret access

**Encryption:**
- Secrets encrypted at rest
- Encrypted transmission
- Hardware security modules (HSM) for critical keys

**Monitoring:**
- Secret access logging
- Unauthorized access alerts
- Expiration monitoring
- Usage analytics

This security and conformance guide provides comprehensive coverage of the security measures implemented in the Crypto Market Analysis SaaS. Regular reviews and updates ensure continued protection against evolving threats.
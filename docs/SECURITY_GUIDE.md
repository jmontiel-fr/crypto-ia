# Security Implementation Guide

This guide documents the comprehensive security measures implemented in the Crypto Market Analysis SaaS application.

## Overview

The application implements multiple layers of security to protect against common web vulnerabilities and ensure data integrity:

1. **Input Validation and Sanitization**
2. **API Authentication and Authorization**
3. **CSRF Protection**
4. **SQL Injection Prevention**
5. **XSS Protection**
6. **Secrets Management**
7. **Secure Logging**

## Input Validation and Sanitization

### InputValidator Class

The `InputValidator` class (`src/api/validation/input_validator.py`) provides comprehensive input validation:

**Features:**
- XSS sanitization using HTML escaping
- SQL injection pattern detection
- Type validation (string, integer, float, boolean, email, phone, etc.)
- Length and range validation
- Pattern matching with regex
- Choice validation from predefined options
- JSON object validation

**Usage Example:**
```python
from src.api.validation import InputValidator, ValidationError

validator = InputValidator()

try:
    # Validate and sanitize user input
    name = validator.validate_string('name', user_input, min_length=1, max_length=100)
    age = validator.validate_integer('age', user_input, min_value=0, max_value=150)
    email = validator.validate_email('email', user_input)
except ValidationError as e:
    print(f"Validation error in {e.field}: {e.message}")
```

### Validation Decorators

Flask route decorators (`src/api/validation/decorators.py`) provide automatic validation:

```python
from src.api.validation.decorators import validate_json
from src.api.validation import required_string, required_integer

@validate_json({
    'name': required_string(min_length=1, max_length=100),
    'age': required_integer(min_value=0, max_value=150)
})
def create_user():
    # Access validated data
    data = request.validated_data
    return jsonify({'message': 'User created', 'data': data})
```

### Security Patterns Detected

**SQL Injection Patterns:**
- SQL keywords (SELECT, INSERT, UPDATE, DELETE, etc.)
- Comment patterns (-- and /* */)
- Boolean logic patterns (OR 1=1, AND 1=1)
- Quote patterns

**XSS Patterns:**
- Script tags (`<script>`)
- JavaScript URLs (`javascript:`)
- Event handlers (`onclick`, `onload`, etc.)
- Iframe, object, and embed tags

## API Authentication and Authorization

### API Key System

The application uses a comprehensive API key system for authentication:

**Features:**
- Secure key generation using `secrets` module
- SHA-256 hashing for storage
- Role-based access control (USER, ADMIN, READONLY)
- Key expiration and rotation
- Usage tracking and audit logging
- Caching with TTL for performance

**API Key Roles:**
- **USER**: Access to predictions and chat endpoints
- **ADMIN**: Full access including key management
- **READONLY**: Read-only access to data endpoints

**Usage:**
```python
from src.api.middleware.auth import api_key_required, admin_required

@api_key_required
def get_predictions():
    # Requires valid API key
    return jsonify({'predictions': []})

@admin_required
def create_api_key():
    # Requires admin role
    return jsonify({'message': 'Key created'})
```

### API Key Management

**Create API Key:**
```bash
python scripts/manage_api_keys.py create "My API Key" --role user --expires-in-days 365
```

**List API Keys:**
```bash
python scripts/manage_api_keys.py list
```

**Revoke API Key:**
```bash
python scripts/manage_api_keys.py revoke <key_id>
```

**Rotate API Key:**
```bash
python scripts/manage_api_keys.py rotate <key_id>
```

## CSRF Protection

Cross-Site Request Forgery protection is implemented for web forms:

**Features:**
- Secure token generation using `secrets.token_urlsafe()`
- Session-based token storage
- Constant-time comparison to prevent timing attacks
- Multiple token sources (header, form data, JSON)
- Automatic exemption for API endpoints

**Usage:**
```python
from src.api.middleware.csrf import csrf_protect, get_csrf_token

@csrf_protect
def submit_form():
    # CSRF token automatically validated
    return jsonify({'message': 'Form submitted'})

# In templates
csrf_token = get_csrf_token()
```

**Client-side Usage:**
```html
<!-- In forms -->
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">

<!-- In AJAX requests -->
<script>
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': '{{ csrf_token }}',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
</script>
```

## SQL Injection Prevention

Multiple layers of protection against SQL injection:

### 1. Parameterized Queries

SQLAlchemy ORM automatically uses parameterized queries:

```python
# Safe - uses parameterized query
user = session.query(User).filter(User.email == user_email).first()

# Unsafe - never do this
# query = f"SELECT * FROM users WHERE email = '{user_email}'"
```

### 2. Input Validation

The `InputValidator` detects SQL injection patterns:

```python
validator = InputValidator()

# This will raise ValidationError
try:
    validator.validate_string('input', "'; DROP TABLE users; --")
except ValidationError as e:
    print(f"SQL injection detected: {e.message}")
```

### 3. Database Permissions

- Use dedicated database user with minimal permissions
- No DDL permissions (CREATE, DROP, ALTER)
- Read/write access only to required tables

## XSS Protection

Cross-Site Scripting protection through multiple mechanisms:

### 1. Input Sanitization

Automatic HTML escaping and dangerous pattern removal:

```python
# Input: <script>alert('xss')</script>Hello
# Output: Hello (script tags removed)
sanitized = validator.validate_string('input', malicious_input)
```

### 2. Content Security Policy (CSP)

Implement CSP headers in production:

```python
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:;"
    )
    return response
```

### 3. Output Encoding

Always encode output in templates:

```html
<!-- Safe -->
<p>{{ user_input | e }}</p>

<!-- Unsafe -->
<p>{{ user_input | safe }}</p>
```

## Secrets Management

Comprehensive secrets management system:

### Local Development

```bash
# Store in local-env file
OPENAI_API_KEY=sk-your-key
SECRET_KEY=your-secret-key
```

### AWS Production

```bash
# Set up AWS Secrets Manager
python scripts/setup_aws_secrets.py --env-file aws-env --mode individual

# Or use combined secret
python scripts/setup_aws_secrets.py --env-file aws-env --mode combined
```

### Features

- Automatic environment detection
- AWS Secrets Manager integration
- Secret caching with TTL
- Rotation support
- Validation to prevent secrets in logs

## Secure Logging

Prevents sensitive information from appearing in logs:

### SecureFormatter

Automatically redacts sensitive patterns:

```python
from src.utils.secure_logging import setup_secure_logging

# Set up secure logging
setup_secure_logging(log_level='INFO', log_file='logs/app.log')

# Logs are automatically sanitized
logger.info(f"API key: {api_key}")  # Logs: "API key: ***REDACTED***"
```

### Patterns Redacted

- API keys and tokens
- Passwords and secret keys
- Database connection strings
- Bearer tokens
- AWS credentials
- Phone numbers and emails (in some contexts)

## Security Headers

Implement security headers in production:

```python
@app.after_request
def add_security_headers(response):
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Force HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
```

## Rate Limiting

Protect against abuse with rate limiting:

```python
from src.api.middleware.rate_limiter import RateLimiter

# Configure in app.py
rate_limiter = RateLimiter(requests_per_minute=100)

@app.before_request
def check_rate_limit():
    if request.path != '/health':
        return rate_limiter.check_rate_limit(request)
```

## Security Testing

### Automated Tests

Run security-focused tests:

```bash
# Input validation tests
python -m pytest tests/test_input_validation.py

# Authentication tests
python -m pytest tests/test_api_authentication.py

# Security integration tests
python -m pytest tests/test_security_integration.py
```

### Manual Security Testing

**SQL Injection Testing:**
```bash
# Test with malicious input
curl -X POST http://localhost:5000/api/chat/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"question": "'; DROP TABLE users; --"}'
```

**XSS Testing:**
```bash
# Test with XSS payload
curl -X POST http://localhost:5000/api/chat/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"question": "<script>alert(\"xss\")</script>"}'
```

**Authentication Testing:**
```bash
# Test without API key
curl -X GET http://localhost:5000/api/predictions/top20

# Test with invalid API key
curl -X GET http://localhost:5000/api/predictions/top20 \
  -H "Authorization: Bearer invalid-key"
```

## Security Monitoring

### Audit Logging

All security events are logged:

- Failed authentication attempts
- PII detection events
- SQL injection attempts
- XSS attempts
- CSRF token validation failures
- Rate limit violations

### Log Analysis

Monitor logs for security events:

```bash
# Search for authentication failures
grep "Invalid API key" logs/app.log

# Search for injection attempts
grep "SQL injection pattern detected" logs/app.log

# Search for XSS attempts
grep "XSS pattern detected" logs/app.log
```

## Incident Response

### Security Incident Checklist

1. **Immediate Response:**
   - Identify affected systems
   - Contain the incident
   - Preserve evidence

2. **Investigation:**
   - Analyze logs
   - Identify attack vectors
   - Assess damage

3. **Recovery:**
   - Patch vulnerabilities
   - Rotate compromised credentials
   - Update security measures

4. **Post-Incident:**
   - Document lessons learned
   - Update security procedures
   - Conduct security review

### Emergency Procedures

**Compromise API Key:**
```bash
# Immediately revoke compromised key
python scripts/manage_api_keys.py revoke <compromised-key-id>

# Generate new key for legitimate user
python scripts/manage_api_keys.py create "Replacement Key" --role user
```

**Database Compromise:**
```bash
# Change database password
# Update DATABASE_URL in secrets manager
# Restart application
```

## Compliance Considerations

### GDPR Compliance

- PII detection and filtering
- Data retention policies
- Right to deletion
- Audit logging

### SOC 2 Considerations

- Access controls
- Audit logging
- Encryption at rest and in transit
- Security monitoring

### Industry Best Practices

- OWASP Top 10 protection
- Secure coding practices
- Regular security assessments
- Vulnerability management

## Security Configuration Checklist

### Development Environment

- [ ] Use HTTPS (self-signed certificates OK)
- [ ] Enable secure logging
- [ ] Use strong secret keys
- [ ] Enable input validation
- [ ] Test security features

### Production Environment

- [ ] Use valid SSL certificates
- [ ] Enable all security headers
- [ ] Use AWS Secrets Manager
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerts
- [ ] Regular security updates
- [ ] Backup and recovery procedures

## Security Updates

Keep security components updated:

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip audit

# Update system packages (on server)
sudo yum update  # Amazon Linux
```

## Contact Information

For security issues:
- Report vulnerabilities responsibly
- Include detailed reproduction steps
- Provide impact assessment
- Allow reasonable disclosure timeline

This security implementation provides comprehensive protection against common web vulnerabilities while maintaining usability and performance.
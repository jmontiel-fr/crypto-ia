# Secrets Management Guide

This guide explains how to manage sensitive credentials securely in the Crypto Market Analysis SaaS application.

## Overview

The application uses a dual-mode secrets management system:

- **Local Development**: Secrets stored in `.env` files (local-env)
- **AWS Production**: Secrets stored in AWS Secrets Manager

## Architecture

### SecretsManager Class

The `SecretsManager` class (`src/config/secrets_manager.py`) provides:

- Automatic environment detection (local vs production)
- AWS Secrets Manager integration for production
- Local environment variable fallback for development
- Secret caching with TTL (5 minutes)
- Secret rotation support
- Validation to prevent secrets in logs

### Secure Logging

The `SecureFormatter` class (`src/utils/secure_logging.py`) automatically redacts sensitive information from logs:

- API keys and tokens
- Passwords and secret keys
- Database connection strings
- AWS credentials
- Bearer tokens

## Local Development Setup

### 1. Create Local Environment File

```bash
# Copy the example file
cp local-env.example local-env

# Edit with your actual values
nano local-env
```

### 2. Set Sensitive Variables

```bash
# Required
OPENAI_API_KEY=sk-your-actual-openai-key
SECRET_KEY=your-random-secret-key

# Optional (for full functionality)
BINANCE_API_KEY=your-binance-key
BINANCE_API_SECRET=your-binance-secret
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
```

### 3. Generate Secret Key

```bash
# Generate a secure random secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

## AWS Production Setup

### Prerequisites

1. AWS account with appropriate permissions
2. AWS CLI configured with credentials
3. boto3 Python package installed

### Option 1: Automated Setup (Recommended)

Use the provided script to migrate secrets from your environment file:

```bash
# Create individual secrets (one per variable)
python scripts/setup_aws_secrets.py \
    --env-file aws-env \
    --region us-east-1 \
    --prefix crypto-saas \
    --mode individual

# Or create a single combined secret (all variables in JSON)
python scripts/setup_aws_secrets.py \
    --env-file aws-env \
    --region us-east-1 \
    --prefix crypto-saas \
    --mode combined

# List existing secrets
python scripts/setup_aws_secrets.py \
    --region us-east-1 \
    --prefix crypto-saas \
    --mode list
```

### Option 2: Manual Setup via AWS Console

1. Navigate to AWS Secrets Manager in the AWS Console
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Add key-value pairs for each sensitive variable:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `BINANCE_API_KEY`: Your Binance API key
   - `BINANCE_API_SECRET`: Your Binance API secret
   - `TWILIO_ACCOUNT_SID`: Your Twilio account SID
   - `TWILIO_AUTH_TOKEN`: Your Twilio auth token
   - `SECRET_KEY`: Your application secret key
5. Name the secret: `crypto-saas/all-secrets`
6. Add description: "Crypto SaaS sensitive configuration"
7. Configure rotation (optional)
8. Review and store

### Option 3: Manual Setup via AWS CLI

```bash
# Create individual secrets
aws secretsmanager create-secret \
    --name crypto-saas/OPENAI_API_KEY \
    --description "OpenAI API Key" \
    --secret-string "sk-your-actual-key" \
    --region us-east-1

aws secretsmanager create-secret \
    --name crypto-saas/SECRET_KEY \
    --description "Application Secret Key" \
    --secret-string "your-random-secret-key" \
    --region us-east-1

# Create combined secret (JSON format)
aws secretsmanager create-secret \
    --name crypto-saas/all-secrets \
    --description "Crypto SaaS All Secrets" \
    --secret-string '{
        "OPENAI_API_KEY": "sk-your-actual-key",
        "BINANCE_API_KEY": "your-binance-key",
        "BINANCE_API_SECRET": "your-binance-secret",
        "TWILIO_ACCOUNT_SID": "your-twilio-sid",
        "TWILIO_AUTH_TOKEN": "your-twilio-token",
        "SECRET_KEY": "your-random-secret-key"
    }' \
    --region us-east-1
```

## IAM Permissions

The EC2 instance needs the following IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:crypto-saas/*"
        }
    ]
}
```

For secret rotation, add:

```json
{
    "Effect": "Allow",
    "Action": [
        "secretsmanager:UpdateSecret",
        "secretsmanager:RotateSecret"
    ],
    "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:crypto-saas/*"
}
```

## Usage in Code

### Automatic Integration

The `Config` class automatically uses `SecretsManager` for sensitive variables:

```python
from src.config.config_loader import load_config

# Load configuration (automatically uses SecretsManager in production)
config = load_config()

# Access secrets (retrieved from AWS Secrets Manager in production)
openai_key = config.openai_api_key
secret_key = config.secret_key
```

### Manual Usage

```python
from src.config.secrets_manager import get_secrets_manager

# Get secrets manager instance
secrets_manager = get_secrets_manager()

# Retrieve individual secret
api_key = secrets_manager.get_secret('OPENAI_API_KEY')

# Retrieve JSON secret
all_secrets = secrets_manager.get_secret_dict('crypto-saas/all-secrets')
openai_key = all_secrets.get('OPENAI_API_KEY')

# Clear cache (force refresh)
secrets_manager.clear_cache('OPENAI_API_KEY')
```

## Secret Rotation

### Automatic Rotation (AWS Secrets Manager)

Configure automatic rotation in AWS Secrets Manager:

1. Navigate to your secret in AWS Console
2. Click "Edit rotation"
3. Enable automatic rotation
4. Set rotation schedule (e.g., every 30 days)
5. Select or create a Lambda function for rotation

### Manual Rotation

```python
from src.config.secrets_manager import get_secrets_manager

secrets_manager = get_secrets_manager('production')

# Rotate a secret
new_value = "new-secret-value"
success = secrets_manager.rotate_secret('crypto-saas/OPENAI_API_KEY', new_value)

if success:
    print("Secret rotated successfully")
```

## Security Best Practices

### 1. Never Commit Secrets

Add to `.gitignore`:

```
# Environment files with secrets
local-env
aws-env
.env

# Backup files
*.env.backup
*-env.backup
```

### 2. Use Strong Secret Keys

```bash
# Generate strong random keys
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Validate Logs

The application automatically redacts secrets from logs, but you can validate manually:

```python
from src.utils.secure_logging import validate_log_message

message = "API key: sk-abc123"
is_safe = validate_log_message(message)  # Returns False

# Raise exception if secrets detected
validate_log_message(message, raise_on_secret=True)  # Raises ValueError
```

### 4. Use Secure Logging

```python
from src.utils.secure_logging import setup_secure_logging, get_secure_logger

# Set up secure logging
setup_secure_logging(log_level='INFO', log_file='logs/app.log')

# Use secure logger
logger = get_secure_logger(__name__)
logger.info(f"API key: {api_key}")  # Automatically redacted
```

### 5. Limit Secret Access

- Use IAM roles with least privilege
- Restrict secret access to specific resources
- Enable CloudTrail logging for secret access
- Set up alerts for unauthorized access attempts

### 6. Regular Audits

```bash
# List all secrets
aws secretsmanager list-secrets --region us-east-1

# Check secret metadata
aws secretsmanager describe-secret \
    --secret-id crypto-saas/OPENAI_API_KEY \
    --region us-east-1

# View secret access logs (CloudTrail)
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceName,AttributeValue=crypto-saas/OPENAI_API_KEY \
    --region us-east-1
```

## Troubleshooting

### Secret Not Found

```
Error: Secret not found in AWS Secrets Manager: crypto-saas/OPENAI_API_KEY
```

**Solution:**
1. Verify secret exists: `aws secretsmanager list-secrets`
2. Check secret name matches exactly
3. Verify AWS region is correct
4. Check IAM permissions

### Access Denied

```
Error: Access denied to secret: crypto-saas/OPENAI_API_KEY
```

**Solution:**
1. Verify EC2 instance has IAM role attached
2. Check IAM role has `secretsmanager:GetSecretValue` permission
3. Verify resource ARN in IAM policy matches secret ARN

### Boto3 Not Installed

```
Warning: boto3 not installed. AWS Secrets Manager unavailable.
```

**Solution:**
```bash
pip install boto3
```

### Cache Issues

If secrets are not updating:

```python
from src.config.secrets_manager import get_secrets_manager

secrets_manager = get_secrets_manager()
secrets_manager.clear_cache()  # Clear all cached secrets
```

## Environment Variables Reference

### Sensitive Variables (Use Secrets Manager in Production)

- `OPENAI_API_KEY` - OpenAI API key
- `BINANCE_API_KEY` - Binance API key
- `BINANCE_API_SECRET` - Binance API secret
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token
- `SECRET_KEY` - Application secret key
- `DATABASE_URL` - Database connection string (contains password)

### Non-Sensitive Variables (Can Use .env)

- `ENVIRONMENT` - Environment name (local/production)
- `TOP_N_CRYPTOS` - Number of cryptocurrencies to track
- `COLLECTION_SCHEDULE` - Data collection schedule
- `MODEL_TYPE` - ML model type (LSTM/GRU)
- `ALERT_ENABLED` - Enable/disable alerts
- `LOG_LEVEL` - Logging level

## Migration Checklist

When moving from local to production:

- [ ] Create AWS Secrets Manager secrets
- [ ] Verify IAM permissions for EC2 instance
- [ ] Update aws-env file (remove sensitive values)
- [ ] Test secret retrieval in production
- [ ] Enable CloudTrail logging
- [ ] Set up secret rotation (optional)
- [ ] Configure monitoring and alerts
- [ ] Document secret names and purposes
- [ ] Train team on secret management procedures

## Cost Considerations

AWS Secrets Manager pricing (as of 2024):

- $0.40 per secret per month
- $0.05 per 10,000 API calls
- Free tier: 30-day trial for new secrets

For this application with ~7 secrets:
- Monthly cost: ~$2.80 (7 secrets × $0.40)
- API calls: Minimal due to caching (~$0.01/month)
- **Total: ~$3/month**

## Additional Resources

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [boto3 Secrets Manager Reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html)
- [Secret Rotation Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

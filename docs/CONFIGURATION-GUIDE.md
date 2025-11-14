# Configuration Guide

## Overview

This guide explains all configuration options for the Crypto Market Analysis SaaS application.

## Configuration Files Summary

### Local Development

| File | Database | Use Case | Setup Complexity |
|------|----------|----------|------------------|
| `local-env.sqlite.example` | SQLite | Quick testing, development | ⭐ Easy (no DB install) |
| `local-env.postgresql.example` | PostgreSQL | Production-like testing | ⭐⭐ Medium (requires PostgreSQL) |

### AWS Production

| File | Database | Use Case | Setup Complexity |
|------|----------|----------|------------------|
| `aws-env.ec2.example` | PostgreSQL on EC2 | Small deployments, lower cost | ⭐⭐ Medium (automated scripts) |
| `aws-env.rds.example` | Amazon RDS | Production, high availability | ⭐⭐⭐ Advanced (requires RDS setup) |

## Quick Start Guide

### Local Development - SQLite (Fastest)

```bash
# 1. Copy template
cp local-env.sqlite.example local-env

# 2. Edit configuration
nano local-env
# Update: OPENAI_API_KEY

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python start.py --all

# 5. Access
# API: http://localhost:5000/api/health
# Dashboard: http://localhost:8501
```

### Local Development - PostgreSQL (Production-like)

```bash
# 1. Install PostgreSQL
# Windows: https://www.postgresql.org/download/windows/
# macOS: brew install postgresql
# Linux: sudo apt install postgresql

# 2. Create database
sudo -u postgres psql
CREATE DATABASE crypto_db;
CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
\q

# 3. Copy template
cp local-env.postgresql.example local-env

# 4. Edit configuration
nano local-env
# Update: DATABASE_URL, OPENAI_API_KEY

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run migrations
alembic upgrade head

# 7. Run application
python start.py --all
```

### AWS Production - EC2 with PostgreSQL

```bash
# 1. Launch EC2 instance (t3.small, Amazon Linux 2023)

# 2. SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# 3. Clone repository
sudo mkdir -p /opt/crypto-ia
sudo chown ec2-user:ec2-user /opt/crypto-ia
cd /opt/crypto-ia
git clone <your-repo-url> .

# 4. Run setup scripts
sudo ./remote-scripts/install-dependencies.sh
sudo ./remote-scripts/setup-postgresql.sh
sudo ./remote-scripts/setup-application.sh

# 5. Configure environment
cp aws-env.ec2.example aws-env
nano aws-env
# Update: OPENAI_API_KEY, WEB_UI_HOST, SECRET_KEY

# 6. Start services
sudo ./remote-scripts/start-services.sh

# 7. Verify
sudo systemctl status crypto-saas-*
curl http://localhost:5000/api/health
```

### AWS Production - EC2 with RDS

```bash
# 1. Create RDS PostgreSQL instance
# - Engine: PostgreSQL 15
# - Instance: db.t3.micro or db.t3.small
# - Storage: 20GB with autoscaling
# - VPC: Same as EC2
# - Security Group: Allow 5432 from EC2

# 2. Launch EC2 instance in same VPC

# 3. SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# 4. Clone repository
sudo mkdir -p /opt/crypto-ia
sudo chown ec2-user:ec2-user /opt/crypto-ia
cd /opt/crypto-ia
git clone <your-repo-url> .

# 5. Run setup scripts (skip PostgreSQL setup)
sudo ./remote-scripts/install-dependencies.sh
sudo ./remote-scripts/setup-application.sh

# 6. Configure environment
cp aws-env.rds.example aws-env
nano aws-env
# Update: DATABASE_URL (with RDS endpoint), OPENAI_API_KEY, etc.

# 7. Initialize database
source venv/bin/activate
alembic upgrade head

# 8. Start services
sudo ./remote-scripts/start-services.sh
```

## Configuration Options Comparison

### Database Options

| Feature | SQLite | PostgreSQL (EC2) | PostgreSQL (RDS) |
|---------|--------|------------------|------------------|
| **Setup Time** | Instant | 5 minutes | 10 minutes |
| **Cost** | Free | Included in EC2 | ~$15-30/month |
| **Performance** | Good for dev | Good | Excellent |
| **Scalability** | Limited | Medium | High |
| **Backups** | Manual | Automated (script) | Automated (AWS) |
| **High Availability** | No | No | Yes (Multi-AZ) |
| **Maintenance** | None | Manual | Automated |
| **Best For** | Development | Small production | Production |

### Deployment Options

| Feature | Local (SQLite) | Local (PostgreSQL) | AWS (EC2) | AWS (RDS) |
|---------|----------------|-------------------|-----------|-----------|
| **Setup Complexity** | ⭐ Easy | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐⭐ Advanced |
| **Monthly Cost** | $0 | $0 | ~$15 | ~$30-50 |
| **Reliability** | Low | Medium | Medium | High |
| **Scalability** | None | Low | Medium | High |
| **Monitoring** | Manual | Manual | CloudWatch | CloudWatch + RDS |
| **Backups** | Manual | Manual | Automated | Automated |
| **SSL/HTTPS** | Optional | Optional | Required | Required |

## Required Configuration

### Minimum Required (All Environments)

```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here  # REQUIRED for chat functionality

# Database
DATABASE_URL=<your-database-url>  # REQUIRED

# Security
SECRET_KEY=<random-secret-key>  # REQUIRED for production
```

### Recommended for Production

```bash
# Domain and SSL
WEB_UI_HOST=your-domain.com
WEB_UI_PROTOCOL=https
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# API Security
API_KEY_REQUIRED=true

# Alerts
ALERT_ENABLED=true
SMS_PROVIDER=aws_sns  # or twilio
AWS_SNS_TOPIC_ARN=arn:aws:sns:region:account:topic

# Data Collection
BINANCE_API_KEY=your-key
BINANCE_API_SECRET=your-secret
```

## Environment Variables Reference

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `local` | Environment name (local, production) |
| `ENVIRONMENT_PATH` | No | Current dir | Deployment path for files |
| `DATABASE_URL` | Yes | - | Database connection string |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for chat |
| `SECRET_KEY` | Yes | - | Secret key for sessions |

### Web UI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEB_UI_HOST` | No | `localhost` | Web UI hostname |
| `WEB_UI_PORT` | No | `10443` | Web UI port |
| `WEB_UI_PROTOCOL` | No | `http` | Protocol (http/https) |
| `SSL_CERT_PATH` | No | - | SSL certificate path |
| `SSL_KEY_PATH` | No | - | SSL key path |

### Data Collection

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `COLLECTION_START_DATE` | No | `2024-01-01` | Start date for data collection |
| `TOP_N_CRYPTOS` | No | `50` | Number of cryptos to track |
| `COLLECTION_SCHEDULE` | No | `0 */6 * * *` | Cron schedule for collection |
| `BINANCE_API_KEY` | No | - | Binance API key |
| `BINANCE_API_SECRET` | No | - | Binance API secret |

### Alerts

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALERT_ENABLED` | No | `true` | Enable alert system |
| `ALERT_THRESHOLD_PERCENT` | No | `10.0` | Price change threshold |
| `SMS_PROVIDER` | No | `twilio` | SMS provider (twilio/aws_sns) |
| `SMS_PHONE_NUMBER` | No | - | Phone number for alerts |
| `AWS_SNS_TOPIC_ARN` | No | - | AWS SNS topic ARN |
| `TWILIO_ACCOUNT_SID` | No | - | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | No | - | Twilio auth token |

### API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_HOST` | No | `0.0.0.0` | API server host |
| `API_PORT` | No | `5000` | API server port |
| `API_KEY_REQUIRED` | No | `false` | Require API key authentication |
| `RATE_LIMIT_PER_MINUTE` | No | `100` | API rate limit |

### Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FILE` | No | `logs/crypto_saas.log` | Log file path |
| `AUDIT_LOGS_RETENTION_DAYS` | No | `90` | Audit log retention |
| `CHAT_HISTORY_RETENTION_DAYS` | No | `30` | Chat history retention |

## Security Best Practices

### Development

- ✅ Use SQLite for quick testing
- ✅ Keep API keys in environment files (not in code)
- ✅ Use `.gitignore` to exclude `local-env` and `aws-env`
- ✅ Use test/placeholder keys for services you're not using

### Production

- ✅ Use PostgreSQL (EC2 or RDS)
- ✅ Generate strong `SECRET_KEY`: `openssl rand -hex 32`
- ✅ Enable `API_KEY_REQUIRED=true`
- ✅ Use HTTPS with valid SSL certificates
- ✅ Enable `ALERT_ENABLED=true` for monitoring
- ✅ Configure automated backups
- ✅ Use AWS Secrets Manager for sensitive credentials
- ✅ Restrict Security Group access
- ✅ Enable CloudWatch monitoring
- ✅ Use Multi-AZ RDS for high availability

## Troubleshooting

### Issue: Database Connection Failed

**SQLite:**
```bash
# Check if database file exists
ls -la crypto_test.db

# Check ENVIRONMENT_PATH
echo $ENVIRONMENT_PATH
```

**PostgreSQL:**
```bash
# Test connection
psql -h localhost -U crypto_user -d crypto_db

# Check if PostgreSQL is running
sudo systemctl status postgresql
```

**RDS:**
```bash
# Test connection from EC2
psql -h your-rds-endpoint.rds.amazonaws.com -U crypto_user -d crypto_db

# Check security group allows 5432 from EC2
```

### Issue: OpenAI API Key Invalid

```bash
# Verify key format (should start with sk-)
echo $OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: Services Not Starting

```bash
# Check service status
sudo systemctl status crypto-saas-*

# View logs
sudo journalctl -u crypto-saas-api -f
tail -f /var/log/crypto-saas/*.log

# Check configuration
python -c "from src.config.config_loader import load_config; load_config()"
```

## Additional Resources

- [Environment Path Guide](./ENVIRONMENT-PATH-GUIDE.md)
- [Local Deployment Guide](./LOCAL-DEPLOYMENT-GUIDE.md)
- [Deployment Guide](../DEPLOYMENT-GUIDE.md)
- [Security Guide](../SECURITY-CONFORMANCE-GUIDE.md)

# Environment Path Configuration Guide

## Overview

The `ENVIRONMENT_PATH` configuration variable allows you to specify where the application should store its runtime data, logs, models, and other files. This is particularly useful for:

- **Local Development**: Deploy to a specific directory like `C:\crypto-ia`
- **AWS Production**: Deploy to `/opt/crypto-ia`
- **Multi-environment setups**: Keep different environments isolated

## Configuration

### Local Environment (Windows)

In your `local-env` file:

```ini
# Deployment Path (where the application is deployed)
ENVIRONMENT_PATH=C:\crypto-ia
```

### Local Environment (Linux/macOS)

In your `local-env` file:

```ini
# Deployment Path (where the application is deployed)
ENVIRONMENT_PATH=/home/user/crypto-ia
```

### AWS Production

In your `aws-env` file:

```ini
# Deployment Path (where the application is deployed)
ENVIRONMENT_PATH=/opt/crypto-ia
```

### Default Behavior

If `ENVIRONMENT_PATH` is not set or is empty, the application will use the current working directory.

## What Gets Stored in ENVIRONMENT_PATH

When `ENVIRONMENT_PATH` is configured, the following directories and files are created/accessed relative to this path:

```
C:\crypto-ia\                    (or /opt/crypto-ia on AWS)
├── logs\
│   └── crypto_saas.log         # Application logs
├── models\
│   └── [model files]           # Trained ML models
├── certs\
│   ├── cert.pem                # SSL certificates
│   └── key.pem
├── tmp\                        # Temporary files
└── crypto_test.db              # SQLite database (local only)
```

## How It Works

### 1. Directory Creation

On startup, the application automatically creates these directories under `ENVIRONMENT_PATH`:

- `logs/` - For application and audit logs
- `models/` - For trained prediction models
- `certs/` - For SSL certificates
- `tmp/` - For temporary files

### 2. Log Files

All log files are written relative to `ENVIRONMENT_PATH`:

```python
# If ENVIRONMENT_PATH=C:\crypto-ia
# LOG_FILE=logs/crypto_saas.log
# Actual path: C:\crypto-ia\logs\crypto_saas.log
```

### 3. Database Files (SQLite)

For local development with SQLite:

```ini
DATABASE_URL=sqlite:///./crypto_test.db
ENVIRONMENT_PATH=C:\crypto-ia
```

The database file will be created at: `C:\crypto-ia\crypto_test.db`

### 4. Model Storage

ML models are saved relative to `ENVIRONMENT_PATH`:

```python
# Models saved to: C:\crypto-ia\models\
```

### 5. SSL Certificates

Certificate paths can be relative or absolute:

```ini
# Relative path (resolved from ENVIRONMENT_PATH)
SSL_CERT_PATH=certs/cert.pem
SSL_KEY_PATH=certs/key.pem

# Absolute path (used as-is)
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/private/key.pem
```

## Setup Instructions

### Step 1: Create the Deployment Directory

**Windows:**
```cmd
mkdir C:\crypto-ia
cd C:\crypto-ia
```

**Linux/macOS:**
```bash
sudo mkdir -p /opt/crypto-ia
sudo chown $USER:$USER /opt/crypto-ia
cd /opt/crypto-ia
```

### Step 2: Configure Environment File

Edit your `local-env` or `aws-env` file:

```ini
ENVIRONMENT_PATH=C:\crypto-ia  # Windows
# or
ENVIRONMENT_PATH=/opt/crypto-ia  # Linux/macOS/AWS
```

### Step 3: Deploy Application Code

**Option A: Clone repository to deployment path**
```bash
cd C:\crypto-ia  # or /opt/crypto-ia
git clone <repository-url> .
```

**Option B: Copy files to deployment path**
```bash
# Copy application files
xcopy /E /I source-dir C:\crypto-ia  # Windows
# or
cp -r source-dir/* /opt/crypto-ia/  # Linux/macOS
```

### Step 4: Run Application

The application will automatically use `ENVIRONMENT_PATH` for all file operations:

```bash
python start.py --all
```

## Verification

Check that directories were created correctly:

**Windows:**
```cmd
dir C:\crypto-ia
```

**Linux/macOS:**
```bash
ls -la /opt/crypto-ia
```

You should see:
```
logs/
models/
certs/
tmp/
crypto_test.db (if using SQLite)
```

## Path Resolution Examples

### Example 1: Local Windows Development

```ini
ENVIRONMENT_PATH=C:\crypto-ia
LOG_FILE=logs/crypto_saas.log
DATABASE_URL=sqlite:///./crypto_test.db
```

Resolved paths:
- Logs: `C:\crypto-ia\logs\crypto_saas.log`
- Database: `C:\crypto-ia\crypto_test.db`
- Models: `C:\crypto-ia\models\`

### Example 2: AWS Production

```ini
ENVIRONMENT_PATH=/opt/crypto-ia
LOG_FILE=/var/log/crypto-saas/app.log
DATABASE_URL=postgresql://user:pass@localhost/db
```

Resolved paths:
- Logs: `/var/log/crypto-saas/app.log` (absolute path, used as-is)
- Database: PostgreSQL (not file-based)
- Models: `/opt/crypto-ia/models/`

### Example 3: No ENVIRONMENT_PATH (Current Directory)

```ini
# ENVIRONMENT_PATH not set
LOG_FILE=logs/crypto_saas.log
```

Resolved paths:
- Logs: `./logs/crypto_saas.log` (relative to current directory)
- Models: `./models/`

## Troubleshooting

### Issue: Permission Denied

**Problem:** Cannot create directories in `ENVIRONMENT_PATH`

**Solution:**
```bash
# Linux/macOS
sudo chown -R $USER:$USER /opt/crypto-ia

# Windows: Run as Administrator or adjust folder permissions
```

### Issue: Database File Not Found

**Problem:** SQLite database not created in expected location

**Solution:** Check that `ENVIRONMENT_PATH` is set correctly and the directory exists:
```bash
echo $ENVIRONMENT_PATH  # Linux/macOS
echo %ENVIRONMENT_PATH%  # Windows
```

### Issue: Logs Not Being Written

**Problem:** Log files not appearing in expected location

**Solution:** 
1. Verify `ENVIRONMENT_PATH` is set
2. Check directory permissions
3. Review startup logs for path resolution messages

## Best Practices

1. **Use Absolute Paths**: Always use absolute paths for `ENVIRONMENT_PATH`
   ```ini
   # Good
   ENVIRONMENT_PATH=C:\crypto-ia
   ENVIRONMENT_PATH=/opt/crypto-ia
   
   # Avoid
   ENVIRONMENT_PATH=../crypto-ia
   ```

2. **Consistent Path Separators**: Use forward slashes in config files (works on all platforms)
   ```ini
   # Good (works everywhere)
   ENVIRONMENT_PATH=C:/crypto-ia
   
   # Also works
   ENVIRONMENT_PATH=C:\crypto-ia
   ```

3. **Separate Environments**: Use different paths for different environments
   ```ini
   # local-env
   ENVIRONMENT_PATH=C:\crypto-ia-dev
   
   # aws-env
   ENVIRONMENT_PATH=/opt/crypto-ia
   ```

4. **Backup Important Data**: Regularly backup the deployment directory
   ```bash
   # Backup models and database
   tar -czf backup.tar.gz /opt/crypto-ia/models /opt/crypto-ia/*.db
   ```

## Integration with Deployment Scripts

The deployment scripts automatically use `ENVIRONMENT_PATH`:

```bash
# scripts/update-code.sh reads ENVIRONMENT_PATH from env files
./scripts/update-code.sh

# Deploys to path specified in ENVIRONMENT_PATH
```

## API Reference

### Python Path Utilities

```python
from src.utils.path_utils import (
    get_base_path,
    resolve_path,
    ensure_directory,
    get_log_path,
    get_model_path
)

# Get base deployment path
base = get_base_path()  # Returns Path('C:/crypto-ia')

# Resolve relative path
log_path = resolve_path('logs/app.log')  # C:/crypto-ia/logs/app.log

# Ensure directory exists
models_dir = ensure_directory('models')  # Creates and returns path

# Get specific paths
log_file = get_log_path()  # Default log path
model_dir = get_model_path()  # Model storage path
```

## Summary

The `ENVIRONMENT_PATH` configuration provides a flexible way to control where your application stores its data. By setting this variable, you can:

- Deploy to a specific directory structure
- Keep environments isolated
- Simplify deployment and backup procedures
- Maintain consistency between local and production environments

For more information, see:
- [Deployment Guide](../DEPLOYMENT-GUIDE.md)
- [Development Guide](../DEVELOPMENT-GUIDE.md)
- [Local Deployment Guide](./LOCAL-DEPLOYMENT-GUIDE.md)

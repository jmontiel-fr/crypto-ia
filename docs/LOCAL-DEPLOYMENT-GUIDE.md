# Local Deployment Guide

## Overview

This guide provides step-by-step instructions for setting up the Crypto Market Analysis SaaS on your local development machine.

**Prerequisites:**
- Windows 10/11, macOS, or Linux
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
- Internet connection

**Important:** This application supports deployment to a specific directory using the `ENVIRONMENT_PATH` configuration. See the [Environment Path Guide](./ENVIRONMENT-PATH-GUIDE.md) for details.

---

## Quick Start (Automated)

If you want to use the automated setup script:

```bash
# Run the setup script
./local-scripts/setup-local-env.sh

# Follow the prompts
```

The script will:
1. Install system dependencies
2. Set up PostgreSQL
3. Create Python virtual environment
4. Install Python packages
5. Configure environment variables
6. Run database migrations
7. Generate SSL certificates

---

## Manual Setup (Step by Step)

### Step 1: Install PostgreSQL

#### Windows

**Option A: Using PostgreSQL Installer**

1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer (version 15 recommended)
3. During installation:
   - Set password for postgres user (remember this!)
   - Port: 5432 (default)
   - Locale: Default
4. Add PostgreSQL to PATH:
   ```cmd
   setx PATH "%PATH%;C:\Program Files\PostgreSQL\15\bin"
   ```

**Option B: Using Chocolatey**

```powershell
# Install Chocolatey if not installed
# Then install PostgreSQL
choco install postgresql15

# Start PostgreSQL service
net start postgresql-x64-15
```

**Verify Installation:**
```cmd
psql --version
# Should show: psql (PostgreSQL) 15.x
```

#### macOS

**Using Homebrew:**

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Verify installation
psql --version
```

**Using Postgres.app:**

1. Download from https://postgresapp.com/
2. Move to Applications folder
3. Open Postgres.app
4. Click "Initialize" to create a new server
5. Add to PATH in `~/.zshrc` or `~/.bash_profile`:
   ```bash
   export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
   ```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib libpq-dev

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
```

#### Linux (CentOS/RHEL/Fedora)

```bash
# Install PostgreSQL
sudo dnf install postgresql-server postgresql-contrib postgresql-devel

# Initialize database
sudo postgresql-setup --initdb

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
psql --version
```

---

### Step 2: Create Database and User

#### Windows

```cmd
# Open Command Prompt as Administrator
# Connect to PostgreSQL
psql -U postgres

# In psql prompt, run:
CREATE DATABASE crypto_db;
CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
ALTER USER crypto_user CREATEDB;

# Connect to the database
\c crypto_db

# Grant schema privileges
GRANT ALL ON SCHEMA public TO crypto_user;

# Exit psql
\q
```

#### macOS/Linux

```bash
# Switch to postgres user (Linux only)
sudo -u postgres psql

# Or connect directly (macOS)
psql postgres

# In psql prompt, run:
CREATE DATABASE crypto_db;
CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
ALTER USER crypto_user CREATEDB;

# Connect to the database
\c crypto_db

# Grant schema privileges
GRANT ALL ON SCHEMA public TO crypto_user;

# Exit psql
\q
```

**Verify Database Creation:**

```bash
# Connect to the database
psql -U crypto_user -d crypto_db -h localhost

# You should see the psql prompt
# Type \q to exit
```

---

### Step 3: Install Python

#### Windows

1. Download Python 3.11+ from https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "Add Python to PATH"
4. Click "Install Now"

**Verify:**
```cmd
python --version
# Should show: Python 3.11.x or higher
```

#### macOS

```bash
# Using Homebrew
brew install python@3.11

# Verify
python3 --version
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv python3.11-dev

# CentOS/RHEL/Fedora
sudo dnf install python3.11 python3.11-devel

# Verify
python3.11 --version
```

---

### Step 4: Clone and Setup Project

```bash
# Navigate to your projects directory
cd ~/projects  # or C:\Users\YourName\projects on Windows

# Clone the repository (if using git)
# git clone <repository-url>
# cd crypto-market-analysis-saas

# Or if you already have the code, navigate to it
cd crypto-market-analysis-saas

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

---

### Step 5: Install Python Dependencies

```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# Install all dependencies
pip install -r requirements.txt

# This will take several minutes...

# Download spaCy language model for PII detection
python -m spacy download en_core_web_sm
```

---

### Step 6: Configure Environment Variables

```bash
# Copy the example environment file
# Windows:
copy local-env.example local-env

# macOS/Linux:
cp local-env.example local-env

# Edit the local-env file
# Windows:
notepad local-env

# macOS/Linux:
nano local-env
# or
code local-env  # if using VS Code
```

**Update these required values:**

```bash
# Database (should match what you created in Step 2)
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db

# OpenAI API Key (REQUIRED - get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Binance API (Optional - can use free tier without keys)
BINANCE_API_KEY=your_binance_key_here
BINANCE_API_SECRET=your_binance_secret_here

# SMS Alerts (Optional - for testing, set ALERT_ENABLED=false)
ALERT_ENABLED=false
# Or configure Twilio:
# SMS_PROVIDER=twilio
# TWILIO_ACCOUNT_SID=your_sid
# TWILIO_AUTH_TOKEN=your_token
# TWILIO_FROM_NUMBER=+1234567890
# SMS_PHONE_NUMBER=+1234567890
```

**Load environment variables:**

```bash
# Windows (PowerShell):
Get-Content local-env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}

# Windows (CMD):
for /f "tokens=*" %i in (local-env) do set %i

# macOS/Linux:
export $(cat local-env | xargs)
```

---

### Step 7: Run Database Migrations

```bash
# Make sure virtual environment is activated
# Make sure environment variables are loaded

# Run migrations to create database tables
python scripts/migrate_upgrade.py

# You should see:
# ✅ Database upgraded successfully!

# Verify tables were created
psql -U crypto_user -d crypto_db -h localhost -c "\dt"

# You should see 7 tables:
# - cryptocurrencies
# - price_history
# - predictions
# - chat_history
# - query_audit_log
# - market_tendencies
# - alert_logs
```

---

### Step 8: Generate Admin API Key

**Required for data collection and admin operations:**

```bash
# Make sure virtual environment is activated
# Make sure environment variables are loaded

# Generate admin API key
python scripts/generate_admin_api_key.py

# Follow the prompts
# Example output:
# ============================================================
# ✓ Admin API Key Generated Successfully!
# ============================================================
# 
# Key ID:  a1b2c3d4e5f6789012345678
# API Key: AbCdEf123456789XyZ_secure_key_here
# 
# ⚠ IMPORTANT: Save this API key securely!
#    It will NOT be shown again.
# ============================================================
```

**⚠️ Critical:** 
- Save this API key in a secure location (password manager, secure notes)
- You'll need it for:
  - Triggering data collection
  - Accessing admin endpoints
  - System management operations
- The key is stored hashed in the database and cannot be retrieved later
- If lost, generate a new key

**Test the API key:**
```bash
# Replace YOUR_API_KEY with the generated key
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status

# Expected response:
# {"is_running": false, "status": "idle", ...}
```

---

### Step 9: Generate SSL Certificates (Optional)

For HTTPS support in local development:

```bash
# Run the SSL certificate generation script
./local-scripts/generate-ssl-cert.sh

# Or manually:
mkdir -p certs/local

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/local/key.pem \
  -out certs/local/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Dev/CN=crypto-ai.local"

# Update hosts file (optional)
# Windows: C:\Windows\System32\drivers\etc\hosts
# macOS/Linux: /etc/hosts
# Add line:
# 127.0.0.1 crypto-ai.local
```

---

### Step 10: Initialize Database with Sample Data (Optional)

```bash
# Run the database initialization script
python scripts/init_database.py

# This will create some sample cryptocurrencies
```

---

### Step 11: Start the Application

You need to run multiple services. Open separate terminal windows for each:

**Terminal 1 - Flask API:**
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Load environment variables
export $(cat local-env | xargs)  # or use Windows equivalent

# Start API server
python run_api.py

# You should see:
# * Running on http://0.0.0.0:5000
```

**Terminal 2 - Streamlit Dashboard:**
```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat local-env | xargs)

# Start dashboard
python run_dashboard.py

# You should see:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
```

**Terminal 3 - Data Collector (Optional):**
```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat local-env | xargs)

# Start data collector
python -m src.collectors.scheduler

# This will run in the background collecting data
```

---

### Step 12: Trigger Initial Data Collection

**Collect historical data for 100 cryptocurrencies:**

```bash
# Replace YOUR_API_KEY with the key from Step 8
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "backward",
    "start_date": "2025-01-01T00:00:00Z"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Collection task started: backward",
#   "mode": "backward",
#   "status_endpoint": "/api/admin/collect/status"
# }
```

**Monitor collection progress:**
```bash
# Check status every 30 seconds
watch -n 30 'curl -s -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status | jq'

# Or manually:
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status
```

**Expected Progress:**
```json
{
  "is_running": true,
  "current_operation": "backward",
  "status": "running",
  "elapsed_seconds": 180,
  "last_results": {
    "total_cryptos": 45,
    "complete": 40,
    "partial": 3,
    "failed": 2,
    "skipped": 0,
    "total_records": 324000
  }
}
```

**Collection Time:**
- **100 cryptos**: ~8-12 minutes
- **11 months of data** (Jan 2025 - Nov 2025): ~792,000 hourly records
- **Storage**: ~160-270 MB

**After completion:**
- Predictions will be available at `/api/predictions/top20`
- Market tendency at `/api/market/tendency`
- Dashboard will show data visualizations

**Scheduled Updates:**
- Collection runs automatically every 6 hours (configurable)
- Uses `forward` mode to fetch only new data
- Takes ~30-60 seconds per update
- No manual intervention needed

---

### Step 13: Verify Installation

**Test API:**
```bash
# In a new terminal
curl http://localhost:5000/api/health

# Should return:
# {"status":"healthy","timestamp":"..."}
```

**Test Dashboard:**
Open browser to: http://localhost:8501

**Test Chat Interface:**
Open browser to: https://crypto-ai.local:10443/chat
(Accept the self-signed certificate warning)

---

## Troubleshooting

### PostgreSQL Connection Issues

**Error: "psql: error: connection to server on socket"**

```bash
# Check if PostgreSQL is running
# Windows:
sc query postgresql-x64-15

# macOS:
brew services list | grep postgresql

# Linux:
sudo systemctl status postgresql

# Start if not running
# Windows:
net start postgresql-x64-15

# macOS:
brew services start postgresql@15

# Linux:
sudo systemctl start postgresql
```

**Error: "FATAL: password authentication failed"**

```bash
# Reset password
# Windows (as Administrator):
psql -U postgres
ALTER USER crypto_user WITH PASSWORD 'crypto_pass';

# Linux:
sudo -u postgres psql
ALTER USER crypto_user WITH PASSWORD 'crypto_pass';
```

**Error: "FATAL: database does not exist"**

```bash
# Create the database
psql -U postgres
CREATE DATABASE crypto_db;
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
```

### Python/Pip Issues

**Error: "pip: command not found"**

```bash
# Use python -m pip instead
python -m pip install -r requirements.txt
```

**Error: "No module named 'venv'"**

```bash
# Install python3-venv
# Ubuntu/Debian:
sudo apt install python3.11-venv

# Then recreate venv
python3.11 -m venv venv
```

### OpenAI API Issues

**Error: "Invalid API key"**

1. Get a valid API key from https://platform.openai.com/api-keys
2. Update `local-env` file with the correct key
3. Reload environment variables
4. Restart the application

**Error: "Rate limit exceeded"**

- You've exceeded OpenAI's rate limits
- Wait a few minutes and try again
- Consider upgrading your OpenAI plan

### Port Already in Use

**Error: "Address already in use"**

```bash
# Find process using the port
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID>

# Or use a different port in local-env:
API_PORT=5001
STREAMLIT_PORT=8502
```

---

## Development Workflow

### Daily Development

```bash
# 1. Start PostgreSQL (if not auto-starting)
# 2. Activate virtual environment
source venv/bin/activate

# 3. Load environment variables
export $(cat local-env | xargs)

# 4. Start services (in separate terminals)
python run_api.py
python run_dashboard.py

# 5. Make your changes
# 6. Test your changes
pytest

# 7. Stop services (Ctrl+C in each terminal)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_basic.py

# Run specific test
pytest tests/test_api_basic.py::test_health_endpoint
```

### Database Management

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
python scripts/migrate_upgrade.py

# Rollback migration
python scripts/migrate_downgrade.py -1

# Check current version
python scripts/migrate_current.py
```

### Backup Database

```bash
# Create backup
pg_dump -U crypto_user -d crypto_db -h localhost > backup.sql

# Restore backup
psql -U crypto_user -d crypto_db -h localhost < backup.sql
```

---

## Next Steps

1. **Get API Keys:**
   - OpenAI: https://platform.openai.com/api-keys
   - Binance (optional): https://www.binance.com/en/my/settings/api-management
   - Twilio (optional): https://www.twilio.com/console

2. **Collect Initial Data:**
   ```bash
   # Trigger manual data collection
   curl -X POST http://localhost:5000/api/admin/collect/trigger \
     -H "Content-Type: application/json" \
     -d '{"mode":"manual","start_date":"2024-01-01"}'
   ```

3. **Train ML Models:**
   - Wait for data collection to complete
   - Models will train automatically on schedule
   - Or trigger manually through the API

4. **Explore the Dashboard:**
   - Open http://localhost:8501
   - View predictions and market analysis

5. **Test Chat Interface:**
   - Open https://crypto-ai.local:10443/chat
   - Ask questions about cryptocurrencies

---

## Additional Resources

- [DEVELOPMENT-GUIDE.md](../DEVELOPMENT-GUIDE.md) - Detailed development guide
- [REST-API-GUIDE.md](../REST-API-GUIDE.md) - API documentation
- [USER-GUIDE.md](../USER-GUIDE.md) - User guide
- [alembic/README.md](../alembic/README.md) - Database migrations

---

## Getting Help

If you encounter issues:

1. Check this troubleshooting section
2. Review error messages carefully
3. Check logs in `logs/` directory
4. Verify environment variables are set correctly
5. Ensure PostgreSQL is running
6. Verify Python virtual environment is activated

---

**Last Updated**: November 11, 2024  
**Version**: 1.0.0

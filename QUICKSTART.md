# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- PostgreSQL installed and running
- Python 3.11+ installed
- OpenAI API key

---

## Step 1: Install PostgreSQL

**Windows:**
```cmd
# Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql15
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

## Step 2: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Run these commands:
CREATE DATABASE crypto_db;
CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
ALTER USER crypto_user CREATEDB;
\c crypto_db
GRANT ALL ON SCHEMA public TO crypto_user;
\q
```

---

## Step 3: Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## Step 4: Configure Environment

```bash
# Copy SQLite config (quick start - no database install needed)
cp local-env.sqlite.example local-env

# OR copy PostgreSQL config (production-like)
# cp local-env.postgresql.example local-env

# Edit local-env and set:
# - DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db
# - OPENAI_API_KEY=sk-your-key-here

# Load environment variables
# Windows PowerShell:
Get-Content local-env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }

# macOS/Linux:
export $(cat local-env | xargs)
```

---

## Step 5: Initialize Database

```bash
# Run migrations
python scripts/migrate_upgrade.py
```

---

## Step 6: Generate Admin API Key

```bash
# Generate API key for admin operations
python scripts/generate_admin_api_key.py

# Save the generated key - you'll need it for data collection!
# Example output:
# Key ID:  a1b2c3d4e5f6...
# API Key: AbCdEf123456...XyZ
```

**⚠️ Important:** Save this API key securely - it won't be shown again!

---

## Step 7: Start Services

**Terminal 1 - API:**
```bash
source venv/bin/activate  # or venv\Scripts\activate
export $(cat local-env | xargs)  # or Windows equivalent
python run_api.py
```

**Terminal 2 - Dashboard:**
```bash
source venv/bin/activate
export $(cat local-env | xargs)
python run_dashboard.py
```

---

## Step 8: Trigger Initial Data Collection

```bash
# Replace YOUR_API_KEY with the key from Step 6
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "backward",
    "start_date": "2025-01-01T00:00:00Z"
  }'

# Monitor progress (takes ~10 minutes for 100 cryptos)
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:5000/api/admin/collect/status
```

**Expected Time:** 8-12 minutes for 100 cryptos with 11 months of history (Jan 2025 - Nov 2025)

---

## Step 9: Access the Application

- **API**: http://localhost:5000/api/health
- **Dashboard**: http://localhost:8501
- **Chat**: https://crypto-ai.local:10443/chat

**After data collection completes**, you can:
- View predictions at http://localhost:5000/api/predictions/top20
- Check market tendency at http://localhost:5000/api/market/tendency
- Use the dashboard for visualizations

---

## Common Commands

### Database
```bash
# Check connection
psql -U crypto_user -d crypto_db -h localhost

# List tables
psql -U crypto_user -d crypto_db -h localhost -c "\dt"

# Backup
pg_dump -U crypto_user -d crypto_db > backup.sql

# Restore
psql -U crypto_user -d crypto_db < backup.sql
```

### Migrations
```bash
# Apply migrations
python scripts/migrate_upgrade.py

# Check current version
python scripts/migrate_current.py

# Rollback
python scripts/migrate_downgrade.py -1
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_api_basic.py
```

---

## Troubleshooting

**PostgreSQL not running?**
```bash
# Windows:
net start postgresql-x64-15

# macOS:
brew services start postgresql@15

# Linux:
sudo systemctl start postgresql
```

**Can't connect to database?**
```bash
# Check if PostgreSQL is listening
psql -U postgres -c "SELECT 1"

# Reset password
psql -U postgres
ALTER USER crypto_user WITH PASSWORD 'crypto_pass';
```

**Port already in use?**
```bash
# Find and kill process
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID>
```

**Missing OpenAI key?**
1. Get key from https://platform.openai.com/api-keys
2. Update `local-env` file
3. Reload environment variables
4. Restart services

---

## Need More Help?

See detailed guides:
- [docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md) - Complete setup guide
- [DEVELOPMENT-GUIDE.md](DEVELOPMENT-GUIDE.md) - Development workflow
- [REST-API-GUIDE.md](REST-API-GUIDE.md) - API documentation

---

**Quick Links:**
- PostgreSQL Download: https://www.postgresql.org/download/
- Python Download: https://www.python.org/downloads/
- OpenAI API Keys: https://platform.openai.com/api-keys
- Binance API: https://www.binance.com/en/my/settings/api-management

---

✅ **You're all set! Happy coding!** 🎉

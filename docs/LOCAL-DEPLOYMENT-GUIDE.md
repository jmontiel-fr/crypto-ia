# Local Development Deployment Guide

This guide covers setting up the Crypto Market Analysis SaaS for local development on your workstation.

## Overview

The local development environment provides:
- Complete application stack running on your machine
- Local PostgreSQL database
- Self-signed SSL certificates
- Hot-reload development servers
- Debug logging and development tools

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows (with WSL2)
- **Python**: 3.11 or higher
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 10GB free space minimum
- **Network**: Internet connection for API dependencies

### Required Software
- **Python 3.11+**: [Download Python](https://www.python.org/downloads/)
- **PostgreSQL**: [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git**: [Download Git](https://git-scm.com/downloads)
- **OpenSSL**: For SSL certificate generation

### API Keys Required
- **OpenAI API Key**: [Get API Key](https://platform.openai.com/api-keys) (Required)
- **Binance API Keys**: [Get API Keys](https://www.binance.com/en/my/settings/api-management) (Optional)
- **Twilio Credentials**: [Get Credentials](https://console.twilio.com/) (Optional, for SMS alerts)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd crypto-market-analysis-saas
```

### 2. Run the Setup Script

The automated setup script will handle most of the configuration:

```bash
# Make the script executable
chmod +x local-scripts/setup-local-env.sh

# Run the setup script
./local-scripts/setup-local-env.sh
```

The script will:
- Install system dependencies
- Create Python virtual environment
- Set up PostgreSQL database
- Generate SSL certificates
- Create configuration files
- Run database migrations

### 3. Configure API Keys

Edit the `local-env` file created by the setup script:

```bash
nano local-env
```

**Required Configuration:**
```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=your_openai_key_here

# Database (configured by setup script)
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db
```

**Optional Configuration:**
```bash
# Binance API (for live data collection)
BINANCE_API_KEY=your_binance_key_here
BINANCE_API_SECRET=your_binance_secret_here

# Twilio (for SMS alerts)
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_FROM_NUMBER=+1234567890
SMS_PHONE_NUMBER=+1234567890
```

### 4. Start the Application

Activate the virtual environment and start the services:

```bash
# Activate virtual environment
source venv/bin/activate

# Start Flask API (Terminal 1)
python -m src.api.main

# Start Streamlit Dashboard (Terminal 2)
streamlit run dashboard.py --server.port=8501

# Optional: Start background services (Terminal 3)
python -m src.collectors.scheduler &
python -m src.alerts.alert_scheduler &
python -m src.utils.start_retention_scheduler &
```

### 5. Access the Application

- **Main Application**: https://crypto-ai.local:10443
- **Streamlit Dashboard**: http://localhost:8501
- **API Health Check**: https://crypto-ai.local:10443/api/health

## Manual Setup (Alternative)

If you prefer manual setup or the automated script fails:

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib libpq-dev build-essential \
    curl git openssl ca-certificates
```

**macOS (with Homebrew):**
```bash
brew update
brew install python@3.11 postgresql openssl curl git
```

**Windows (WSL2):**
```bash
# Use Ubuntu commands in WSL2
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib libpq-dev build-essential \
    curl git openssl ca-certificates
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3. Setup PostgreSQL

**Start PostgreSQL:**
```bash
# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew services start postgresql

# Windows (WSL2)
sudo service postgresql start
```

**Create Database:**
```bash
# Ubuntu/Debian
sudo -u postgres psql -c "CREATE DATABASE crypto_db;"
sudo -u postgres psql -c "CREATE USER crypto_user WITH PASSWORD 'crypto_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;"
sudo -u postgres psql -c "ALTER USER crypto_user CREATEDB;"

# macOS
createdb crypto_db
psql -d crypto_db -c "CREATE USER crypto_user WITH PASSWORD 'crypto_pass';"
psql -d crypto_db -c "GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;"
psql -d crypto_db -c "ALTER USER crypto_user CREATEDB;"
```

### 4. Generate SSL Certificates

```bash
chmod +x local-scripts/generate-ssl-cert.sh
./local-scripts/generate-ssl-cert.sh --local-only
```

### 5. Configure Environment

```bash
cp local-env.example local-env
# Edit local-env with your API keys
```

### 6. Run Database Migrations

```bash
python -c "
from src.data.database import create_tables
create_tables()
print('Database tables created')
"
```

### 7. Add Local Domain to Hosts File

Add this line to your hosts file:
```
127.0.0.1 crypto-ai.local
```

**Hosts file locations:**
- **Linux/macOS**: `/etc/hosts`
- **Windows**: `C:\Windows\System32\drivers\etc\hosts`

## Development Workflow

### Starting Development

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Start services in separate terminals:**
   ```bash
   # Terminal 1: API Server
   python -m src.api.main
   
   # Terminal 2: Dashboard
   streamlit run dashboard.py --server.port=8501
   
   # Terminal 3: Background Services (optional)
   python -m src.collectors.scheduler
   ```

### Making Changes

1. **Code changes** are automatically reloaded in development mode
2. **Database changes** require running migrations
3. **Configuration changes** require restarting services

### Testing

```bash
# Run tests
python -m pytest

# Run specific test file
python -m pytest tests/test_api.py

# Run with coverage
python -m pytest --cov=src
```

### Database Management

```bash
# Connect to database
psql -h localhost -U crypto_user -d crypto_db

# View tables
\dt

# Reset database (careful!)
python -c "
from src.data.database import drop_all_tables, create_tables
drop_all_tables()
create_tables()
print('Database reset complete')
"
```

## Troubleshooting

### Common Issues

**1. PostgreSQL Connection Error**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Check connection
psql -h localhost -U crypto_user -d crypto_db
```

**2. SSL Certificate Issues**
```bash
# Regenerate certificates
./local-scripts/generate-ssl-cert.sh --local-only

# Trust certificate in browser
# Chrome: Settings > Privacy and security > Security > Manage certificates
# Firefox: Settings > Privacy & Security > Certificates > View Certificates
```

**3. Python Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**4. Port Already in Use**
```bash
# Find process using port
lsof -i :5000  # API port
lsof -i :8501  # Streamlit port

# Kill process
kill -9 <PID>
```

**5. OpenAI API Errors**
- Verify API key is correct in `local-env`
- Check API key has sufficient credits
- Ensure API key has proper permissions

### Logs and Debugging

**Application Logs:**
```bash
# View logs
tail -f logs/crypto_saas.log

# Debug mode (more verbose)
LOG_LEVEL=DEBUG python -m src.api.main
```

**Database Logs:**
```bash
# PostgreSQL logs location varies by OS
# Ubuntu: /var/log/postgresql/
# macOS: /usr/local/var/log/
```

### Performance Optimization

**For Development:**
```bash
# Reduce data collection frequency
COLLECTION_SCHEDULE="0 */12 * * *"  # Every 12 hours instead of 6

# Reduce model complexity
SEQUENCE_LENGTH=24  # 1 day instead of 7 days

# Disable alerts in development
ALERT_ENABLED=false
```

## Configuration Reference

### Environment Variables

**Required:**
- `OPENAI_API_KEY`: OpenAI API key for chat functionality
- `DATABASE_URL`: PostgreSQL connection string

**Optional:**
- `BINANCE_API_KEY`: Binance API key for live data
- `BINANCE_API_SECRET`: Binance API secret
- `TWILIO_*`: Twilio credentials for SMS alerts
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `COLLECTION_START_DATE`: Start date for historical data collection

### Service Ports

- **Flask API**: 5000
- **Streamlit Dashboard**: 8501
- **HTTPS Web UI**: 10443
- **PostgreSQL**: 5432

### File Structure

```
crypto-market-analysis-saas/
├── src/                    # Application source code
├── tests/                  # Test files
├── local-scripts/          # Local deployment scripts
├── certs/local/           # SSL certificates
├── logs/                  # Application logs
├── venv/                  # Python virtual environment
├── local-env              # Local environment configuration
├── requirements.txt       # Python dependencies
└── dashboard.py           # Streamlit dashboard entry point
```

## Next Steps

1. **Explore the Application:**
   - Visit the Streamlit dashboard to see market data
   - Try the chat interface for AI-powered analysis
   - Check the API endpoints

2. **Customize Configuration:**
   - Add your own cryptocurrency symbols to track
   - Adjust prediction parameters
   - Configure alert thresholds

3. **Development:**
   - Read the code documentation in each module
   - Run tests to understand functionality
   - Make changes and see them reflected immediately

4. **Deploy to AWS:**
   - When ready, follow the [AWS Deployment Guide](AWS-DEPLOYMENT-GUIDE.md)
   - Use the local environment for development and testing

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs in `logs/crypto_saas.log`
3. Check the main project README for additional information
4. Ensure all prerequisites are properly installed

Happy developing! 🚀
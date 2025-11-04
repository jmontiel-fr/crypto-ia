# Development Guide - Crypto Market Analysis SaaS

This guide covers everything you need to know for developing and contributing to the Crypto Market Analysis SaaS project.

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [OpenAI API Setup](#openai-api-setup)
- [Database Management](#database-management)
- [Testing](#testing)
- [Development Workflow](#development-workflow)
- [Adding New Features](#adding-new-features)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Git
- OpenSSL (for SSL certificates)

### 1-Minute Setup

```bash
# Clone the repository
git clone <repository-url>
cd crypto-market-analysis-saas

# Run the automated setup script
chmod +x local-scripts/setup-local-env.sh
./local-scripts/setup-local-env.sh

# Edit configuration with your API keys
nano local-env

# Activate virtual environment
source venv/bin/activate

# Start the application
python -m src.api.main
```

## Project Structure

```
crypto-market-analysis-saas/
├── src/                          # Main application source code
│   ├── api/                      # Flask REST API
│   │   ├── routes/              # API route handlers
│   │   ├── middleware/          # Authentication, rate limiting, audit
│   │   ├── templates/           # HTML templates (chat interface)
│   │   └── static/              # Static assets (CSS, JS)
│   ├── collectors/              # Data collection from Binance API
│   ├── prediction/              # LSTM/GRU prediction engine
│   ├── genai/                   # OpenAI integration and chat system
│   ├── alerts/                  # SMS alert system
│   ├── dashboard/               # Streamlit dashboard pages
│   ├── data/                    # Database models and repositories
│   ├── config/                  # Configuration management
│   └── utils/                   # Utilities (logging, audit, retention)
├── terraform/                   # AWS infrastructure as code
├── local-scripts/               # Local development and deployment scripts
├── remote-scripts/              # Scripts that run on AWS EC2
├── tests/                       # Test suite
├── docs/                        # Additional documentation
├── certs/                       # SSL certificates (local and AWS)
├── logs/                        # Application logs
├── requirements.txt             # Python dependencies
├── dashboard.py                 # Streamlit dashboard entry point
├── local-env.example            # Local environment template
├── aws-env.example              # AWS environment template
└── README.md                    # Project overview
```

### Script Organization

The project uses a clear separation between local and remote scripts:

#### Local Scripts (`local-scripts/`)
Scripts that run on your **local development machine**:

- `setup-local-env.sh` - Complete local environment setup
- `generate-ssl-cert.sh` - SSL certificate generation
- `deploy-to-aws.sh` - Full AWS deployment automation
- `sync-code.sh` - Incremental code updates to AWS
- `control-remote.sh` - Remote service management

#### Remote Scripts (`remote-scripts/`)
Scripts that run on the **AWS EC2 instance**:

- `install-dependencies.sh` - System package installation
- `setup-postgresql.sh` - PostgreSQL installation and configuration
- `setup-application.sh` - Application environment setup
- `start-services.sh` - Service startup and management

This separation ensures clear responsibilities and makes deployment automation reliable.

## Local Development Setup

### Automated Setup (Recommended)

The easiest way to set up your development environment:

```bash
# Make the setup script executable
chmod +x local-scripts/setup-local-env.sh

# Run the automated setup
./local-scripts/setup-local-env.sh
```

This script will:
- Install system dependencies (Python, PostgreSQL, etc.)
- Create a Python virtual environment
- Install Python dependencies
- Set up PostgreSQL database
- Generate SSL certificates
- Create environment configuration
- Run database migrations
- Verify the setup

### Manual Setup

If you prefer manual setup or need to troubleshoot:

#### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib libpq-dev build-essential \
    curl git openssl
```

**macOS:**
```bash
brew install python@3.11 postgresql openssl curl git
```

**Amazon Linux/CentOS:**
```bash
sudo dnf install python3.11 python3.11-pip python3.11-devel \
    postgresql-server postgresql-devel gcc gcc-c++ make \
    curl git openssl
```

#### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

#### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Set Up PostgreSQL

**Start PostgreSQL service:**
```bash
# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew services start postgresql

# Amazon Linux/CentOS
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Create database and user:**
```bash
# Ubuntu/Debian/Amazon Linux
sudo -u postgres psql -c "CREATE DATABASE crypto_db;"
sudo -u postgres psql -c "CREATE USER crypto_user WITH PASSWORD 'crypto_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;"
sudo -u postgres psql -c "ALTER USER crypto_user CREATEDB;"

# macOS
createdb crypto_db
psql -d crypto_db -c "CREATE USER crypto_user WITH PASSWORD 'crypto_pass';"
psql -d crypto_db -c "GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;"
```

#### 5. Generate SSL Certificates

```bash
chmod +x local-scripts/generate-ssl-cert.sh
./local-scripts/generate-ssl-cert.sh --local-only
```

#### 6. Configure Environment

```bash
cp local-env.example local-env
# Edit local-env with your configuration
nano local-env
```

#### 7. Set Up Local Domain

Add to your `/etc/hosts` file:
```
127.0.0.1 crypto-ai.local
```

#### 8. Run Database Migrations

```bash
python -c "
from src.data.database import create_tables
create_tables()
print('Database tables created')
"
```

## OpenAI API Setup

The application requires an OpenAI API key for the chat functionality.

### 1. Create OpenAI Account

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up for an account or log in
3. Verify your email address
4. Add payment method (required for API access)

### 2. Generate API Key

1. Navigate to [API Keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Give it a descriptive name (e.g., "Crypto SaaS Development")
4. Copy the key immediately (you won't see it again)

### 3. Configure API Key

Add your API key to the environment configuration:

```bash
# Edit your local-env file
nano local-env

# Add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 4. Test API Connection

```bash
# Activate virtual environment
source venv/bin/activate

# Test OpenAI connection
python -c "
from src.genai.genai_engine import GenAIEngine
from src.data.database import get_session

session = get_session()
engine = GenAIEngine(session)
print('OpenAI API connection successful')
session.close()
"
```

### 5. API Usage and Costs

**Model Configuration:**
- Default model: `gpt-4o-mini` (cost-effective)
- Alternative: `gpt-4` (higher quality, higher cost)

**Cost Estimates (gpt-4o-mini):**
- Input: ~$0.15 per 1M tokens
- Output: ~$0.60 per 1M tokens
- Average query: ~$0.0002 (150 input + 300 output tokens)
- 1000 queries: ~$0.20

**Cost Control:**
- Set `OPENAI_MAX_TOKENS=500` to limit response length
- Monitor usage in OpenAI dashboard
- Use audit logging to track costs

## Database Management

### Database Migrations

The project uses SQLAlchemy for database management. For simple schema changes, you can recreate tables:

```bash
# Drop and recreate all tables (development only!)
python -c "
from src.data.database import drop_tables, create_tables
drop_tables()
create_tables()
print('Database reset complete')
"
```

For production-ready migrations, consider using Alembic:

```bash
# Initialize Alembic (one-time setup)
pip install alembic
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head
```

### Database Backup and Restore

**Backup:**
```bash
pg_dump -h localhost -U crypto_user -d crypto_db > backup.sql
```

**Restore:**
```bash
psql -h localhost -U crypto_user -d crypto_db < backup.sql
```

### Database Inspection

```bash
# Connect to database
psql -h localhost -U crypto_user -d crypto_db

# List tables
\dt

# Describe table structure
\d table_name

# View data
SELECT * FROM cryptocurrencies LIMIT 10;
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_database_layer.py

# Run specific test
pytest tests/test_database_layer.py::test_cryptocurrency_crud
```

### Test Structure

```
tests/
├── conftest.py                  # Test configuration and fixtures
├── test_database_layer.py       # Database and repository tests
├── test_collectors.py           # Data collection tests
├── test_prediction_engine.py    # ML model tests
├── test_genai_engine.py         # Chat system tests
├── test_api_endpoints.py        # API endpoint tests
└── test_utils.py                # Utility function tests
```

### Writing Tests

Example test structure:

```python
import pytest
from src.data.database import get_session
from src.data.repositories import CryptocurrencyRepository

def test_cryptocurrency_crud():
    """Test cryptocurrency CRUD operations."""
    session = get_session()
    repo = CryptocurrencyRepository(session)
    
    # Create
    crypto = repo.create("BTC", "Bitcoin", 1)
    assert crypto.symbol == "BTC"
    
    # Read
    found = repo.get_by_symbol("BTC")
    assert found.name == "Bitcoin"
    
    # Update
    updated = repo.update(crypto.id, market_cap_rank=2)
    assert updated.market_cap_rank == 2
    
    # Delete
    repo.delete(crypto.id)
    assert repo.get_by_symbol("BTC") is None
    
    session.close()
```

### Test Database

Tests use a separate test database to avoid affecting development data:

```bash
# Create test database
sudo -u postgres psql -c "CREATE DATABASE crypto_test_db;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crypto_test_db TO crypto_user;"
```

## Development Workflow

### Starting Development

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Start services in separate terminals:**

   **Terminal 1 - Flask API:**
   ```bash
   python -m src.api.main
   ```

   **Terminal 2 - Streamlit Dashboard:**
   ```bash
   streamlit run dashboard.py --server.port=8501
   ```

   **Terminal 3 - Data Collector (optional):**
   ```bash
   python -m src.collectors.scheduler
   ```

3. **Access the application:**
   - Main application: https://crypto-ai.local:10443
   - Streamlit dashboard: http://localhost:8501
   - API documentation: https://crypto-ai.local:10443/api/health

### Development Tools

**Code Formatting:**
```bash
# Install formatting tools
pip install black isort flake8

# Format code
black src/
isort src/

# Check code style
flake8 src/
```

**Type Checking:**
```bash
# Install mypy
pip install mypy

# Check types
mypy src/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push branch
git push origin feature/new-feature

# Create pull request (via GitHub/GitLab)
```

### Environment Variables

**Development vs Production:**
- `local-env` - Local development configuration
- `aws-env` - AWS production configuration

**Key Variables:**
```bash
# Required
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://crypto_user:crypto_pass@localhost:5432/crypto_db

# Optional but recommended
BINANCE_API_KEY=your-binance-key
BINANCE_API_SECRET=your-binance-secret
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
```

## Adding New Features

### 1. Database Changes

**Add new model:**
```python
# src/data/models.py
class NewModel(Base):
    __tablename__ = 'new_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Add repository:**
```python
# src/data/repositories.py
class NewModelRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, name: str) -> NewModel:
        model = NewModel(name=name)
        self.session.add(model)
        self.session.flush()
        return model
```

### 2. API Endpoints

**Add new route:**
```python
# src/api/routes/new_feature.py
from flask import Blueprint, jsonify, request
from src.data.database import get_session
from src.data.repositories import NewModelRepository

new_feature_bp = Blueprint('new_feature', __name__)

@new_feature_bp.route('/items', methods=['GET'])
def get_items():
    session = get_session()
    repo = NewModelRepository(session)
    items = repo.get_all()
    session.close()
    
    return jsonify({
        'items': [{'id': item.id, 'name': item.name} for item in items]
    })
```

**Register blueprint:**
```python
# src/api/app.py
from src.api.routes.new_feature import new_feature_bp

def register_blueprints(app: Flask):
    # ... existing blueprints
    app.register_blueprint(new_feature_bp, url_prefix='/api/new-feature')
```

### 3. Dashboard Pages

**Add new dashboard page:**
```python
# src/dashboard/pages/new_page.py
import streamlit as st
from src.dashboard.utils import APIClient

def show():
    st.title("New Feature Dashboard")
    
    # Get data from API
    client = APIClient("http://localhost:5000")
    data = client._make_request('GET', '/api/new-feature/items')
    
    # Display data
    if data.get('items'):
        st.dataframe(data['items'])
    else:
        st.info("No data available")
```

**Add to main dashboard:**
```python
# dashboard.py
elif page == "🆕 New Feature":
    from src.dashboard.pages import new_page
    new_page.show()
```

### 4. Background Tasks

**Add new background service:**
```python
# src/new_service/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

class NewServiceScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        self.scheduler.add_job(
            func=self.run_task,
            trigger="interval",
            minutes=30,
            id='new_service_task'
        )
        self.scheduler.start()
    
    def run_task(self):
        # Implement your background task
        pass
```

### 5. Testing New Features

**Add tests:**
```python
# tests/test_new_feature.py
import pytest
from src.data.repositories import NewModelRepository

def test_new_model_creation():
    session = get_session()
    repo = NewModelRepository(session)
    
    model = repo.create("Test Item")
    assert model.name == "Test Item"
    
    session.close()
```

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -h localhost -U crypto_user -l

# Test connection
python -c "
from src.data.database import get_session
session = get_session()
print('Database connection successful')
session.close()
"
```

**2. SSL Certificate Issues**
```bash
# Regenerate certificates
./local-scripts/generate-ssl-cert.sh --local-only

# Check certificate validity
openssl x509 -in certs/local/cert.pem -text -noout
```

**3. OpenAI API Errors**
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test API connection
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**4. Port Already in Use**
```bash
# Find process using port
lsof -i :5000
lsof -i :8501

# Kill process
kill -9 <PID>
```

**5. Permission Errors**
```bash
# Fix file permissions
chmod +x local-scripts/*.sh
chmod 600 certs/local/key.pem
chmod 644 certs/local/cert.pem
```

### Debug Mode

Enable debug mode for detailed error messages:

```bash
# In local-env file
DEBUG=true
LOG_LEVEL=DEBUG
FLASK_ENV=development
```

### Logging

**View application logs:**
```bash
# Real-time logs
tail -f logs/crypto_saas.log

# Search logs
grep "ERROR" logs/crypto_saas.log
```

**Enable verbose logging:**
```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

**Database query optimization:**
```python
# Use query profiling
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    print(f"Query took {total:.4f} seconds: {statement[:50]}...")
```

**Memory usage monitoring:**
```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB
```

### Getting Help

1. **Check logs** for error messages
2. **Search issues** in the project repository
3. **Review documentation** for similar problems
4. **Test with minimal configuration** to isolate issues
5. **Create detailed bug reports** with:
   - Error messages
   - Steps to reproduce
   - Environment details
   - Log excerpts

## Development Best Practices

### Code Style

- Follow PEP 8 for Python code style
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Use meaningful variable and function names

### Security

- Never commit API keys or secrets to version control
- Use environment variables for configuration
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Keep dependencies updated

### Performance

- Use database indexes for frequently queried columns
- Implement caching for expensive operations
- Use connection pooling for database connections
- Monitor memory usage and optimize as needed
- Profile code to identify bottlenecks

### Testing

- Write tests for all new features
- Aim for high test coverage (>80%)
- Use meaningful test names that describe what is being tested
- Test both success and failure scenarios
- Use fixtures to set up test data

This development guide should help you get started with contributing to the Crypto Market Analysis SaaS project. For deployment and production setup, see the [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md).
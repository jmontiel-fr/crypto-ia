# Crypto Market Analysis SaaS

An AI-powered cryptocurrency market analysis platform that provides predictions, market insights, and intelligent chat capabilities.

## 🚀 Quick Start

### Prerequisites

**You need:**
1. **Python 3.11+** - Programming language
2. **OpenAI API Key** - Get from https://platform.openai.com/api-keys
3. **Database** (Optional) - SQLite (no install) or PostgreSQL ([Install Guide](docs/LOCAL-DEPLOYMENT-GUIDE.md#step-1-install-postgresql))

> 💡 **New to the project?** See [CONFIGURATION-OPTIONS.md](CONFIGURATION-OPTIONS.md) for a quick guide on choosing the right setup.

### Local Development Setup

**Option 1: Quick Start (5 minutes)**

See [QUICKSTART.md](QUICKSTART.md) for the fastest way to get running.

**Option 2: Automated Setup**

```bash
# Run the automated setup script
./local-scripts/setup-local-env.sh

# Follow the prompts to:
# - Install dependencies
# - Setup PostgreSQL database
# - Configure environment
# - Run migrations
```

**Option 3: Manual Setup**

See [docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md) for detailed step-by-step instructions.

### Start the Application

```bash
# Terminal 1 - API Server
source venv/bin/activate
export $(cat local-env | xargs)
python run_api.py

# Terminal 2 - Dashboard
source venv/bin/activate
export $(cat local-env | xargs)
python run_dashboard.py
```

**Access the application:**
- **API Health**: http://localhost:5000/api/health
- **Dashboard**: http://localhost:8501
- **Chat Interface**: https://crypto-ai.local:10443/chat

### AWS Deployment (Production)

```bash
# Configure Terraform
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# Deploy infrastructure
terraform init && terraform apply

# Deploy application
cd ..
./local-scripts/deploy-to-aws.sh
```

## 📋 Features

### 🤖 AI-Powered Predictions
- **LSTM/GRU Models**: Deep learning predictions for top 20 cryptocurrencies
- **24-Hour Forecasts**: Next-day performance predictions with confidence scores
- **Market Tendency Analysis**: Bullish, bearish, volatile, stable, or consolidating

### 💬 Intelligent Chat Interface
- **Natural Language Queries**: Ask questions about crypto markets in plain English
- **Context-Aware Responses**: Combines internal predictions with external knowledge
- **Safety Features**: PII protection, topic validation, content filtering

### 🔄 Smart Data Collection (NEW!)
- **Interruption-Safe**: Resume automatically after interruptions without losing progress
- **Smart Resume**: Only fetches missing data ranges (no duplicates)
- **Automatic Retry**: Failed batches retry up to 3 times with exponential backoff
- **Real-Time Progress**: Monitor collection status per-crypto and overall
- **100 Cryptos Tracked**: Top 100 cryptocurrencies by market cap with hourly data

### 📊 Interactive Dashboard
- **Real-Time Data**: Live cryptocurrency prices and market data
- **Visual Analytics**: Interactive charts and trend analysis
- **Admin Controls**: System monitoring and audit capabilities

### 🔔 Smart Alerts
- **SMS Notifications**: Real-time alerts for significant market movements
- **Configurable Thresholds**: Customize alert sensitivity
- **Spam Protection**: Intelligent cooldown periods

### 🔒 Enterprise Security
- **PII Protection**: Automatic detection and blocking of personal information
- **Comprehensive Auditing**: Full audit trail of all activities
- **Data Encryption**: End-to-end encryption for all communications
- **Compliance Ready**: GDPR-compliant data handling

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Crypto Market Analysis SaaS              │
├─────────────────────────────────────────────────────────────┤
│  Web UI (Bootstrap5)     │  Dashboard (Streamlit)          │
│  - Chat Interface        │  - Data Visualization           │
│  - Real-time Updates     │  - Admin Controls               │
├─────────────────────────────────────────────────────────────┤
│                    REST API (Flask)                         │
│  - Predictions  - Market Data  - Chat  - Admin             │
├─────────────────────────────────────────────────────────────┤
│  LSTM Engine    │  GenAI Engine   │  Alert System          │
│  - Predictions  │  - OpenAI API   │  - SMS Gateway         │
│  - Training     │  - PII Filter   │  - Monitoring          │
├─────────────────────────────────────────────────────────────┤
│  Data Collector │  Audit Logger   │  Retention Manager     │
│  - Binance API  │  - Security     │  - Cleanup             │
│  - Scheduler    │  - Compliance   │  - Policies            │
├─────────────────────────────────────────────────────────────┤
│                PostgreSQL Database                          │
│  - Price Data  - Predictions  - Chat History  - Audit Logs │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

**Backend:**
- Python 3.11+
- Flask (REST API)
- SQLAlchemy (ORM)
- PostgreSQL (Database)
- TensorFlow/Keras (ML Models)

**Frontend:**
- Streamlit (Dashboard)
- Bootstrap 5 (Chat Interface)
- Plotly (Charts)
- JavaScript (Interactivity)

**AI/ML:**
- OpenAI GPT-4o-mini (Chat)
- LSTM/GRU Networks (Predictions)
- spaCy (NLP/PII Detection)

**Infrastructure:**
- AWS EC2 (Compute)
- Terraform (Infrastructure as Code)
- Nginx (Reverse Proxy)
- systemd (Service Management)

**Security:**
- SSL/TLS Encryption
- PII Detection & Filtering
- Comprehensive Audit Logging
- Rate Limiting & Authentication

## 📖 Documentation

- **[Development Guide](DEVELOPMENT-GUIDE.md)** - Setup, development, and contribution guide
- **[Deployment Guide](DEPLOYMENT-GUIDE.md)** - AWS deployment and infrastructure
- **[User Guide](USER-GUIDE.md)** - How to use the platform
- **[Security Guide](SECURITY-CONFORMANCE-GUIDE.md)** - Security and compliance

## 🚀 Usage Examples

### Starting Services

```bash
# Start all services (development)
python start.py --development

# Start only API server
python start.py --api

# Start only dashboard
python start.py --dashboard

# Start background services only
python start.py --services

# Production mode
python start.py --production
```

### API Usage

```bash
# Get top 20 predictions
curl https://crypto-ai.your-domain.com/api/predictions/top20

# Get market tendency
curl https://crypto-ai.your-domain.com/api/market/tendency

# Chat query
curl -X POST https://crypto-ai.your-domain.com/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Should I invest in Bitcoin?", "session_id": "test"}'

# Health check
curl https://crypto-ai.your-domain.com/api/health
```

### Service Management (AWS)

```bash
# Check service status
./local-scripts/control-remote.sh status

# View logs
./local-scripts/control-remote.sh logs

# Restart services
./local-scripts/control-remote.sh restart

# Health check
./local-scripts/control-remote.sh health
```

## ⚙️ Configuration

### Environment Variables

**Required:**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/crypto_db
```

**Optional:**
```bash
BINANCE_API_KEY=your-binance-key
BINANCE_API_SECRET=your-binance-secret
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
SMS_PHONE_NUMBER=+1234567890
```

### Configuration Files

**Local Development:**
- **`local-env`** - Your local configuration (you create this)
- **`local-env.sqlite.example`** - SQLite template (quick start, no DB install)
- **`local-env.postgresql.example`** - PostgreSQL template (production-like)

**AWS Production:**
- **`aws-env`** - Your AWS configuration (you create this)
- **`aws-env.ec2.example`** - EC2 with PostgreSQL template (simpler, lower cost)
- **`aws-env.rds.example`** - EC2 with RDS template (managed DB, high availability)

**Infrastructure:**
- **`terraform/terraform.tfvars`** - Terraform infrastructure configuration

**Choose Your Local Database:**

```bash
# Option 1: SQLite (Quick Start - No installation required)
cp local-env.sqlite.example local-env

# Option 2: PostgreSQL (Production-like - Requires PostgreSQL)
cp local-env.postgresql.example local-env
```

**Choose Your AWS Database:**

```bash
# Option 1: EC2 with PostgreSQL (Simpler, automated setup)
cp aws-env.ec2.example aws-env

# Option 2: EC2 with RDS (Managed database, better for production)
cp aws-env.rds.example aws-env
```

**Deployment Path Configuration:**

The application supports deployment to a specific directory using `ENVIRONMENT_PATH`:

```bash
# Local (Windows)
ENVIRONMENT_PATH=C:\crypto-ia

# Local (Linux/macOS)
ENVIRONMENT_PATH=/opt/crypto-ia

# AWS Production
ENVIRONMENT_PATH=/opt/crypto-ia
```

This controls where logs, models, databases, and other files are stored. See [Environment Path Guide](docs/ENVIRONMENT-PATH-GUIDE.md) for details.

## 💰 Cost Estimates

### AWS Infrastructure (t3.micro)
- **EC2 Instance**: ~$7.50/month
- **EBS Storage**: ~$7.00/month
- **Data Transfer**: ~$1-5/month
- **Total**: ~$15-20/month

### OpenAI API (gpt-4o-mini)
- **Light Usage** (100 queries/day): ~$0.60/month
- **Moderate Usage** (1000 queries/day): ~$6.00/month
- **Heavy Usage** (5000 queries/day): ~$30.00/month

### SMS Alerts (Twilio)
- **10 alerts/month**: ~$0.08
- **100 alerts/month**: ~$0.75

## 🔧 Development

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Node.js 18+ (optional)
- OpenAI API key

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
createdb crypto_db
python -c "from src.data.database import create_tables; create_tables()"

# Generate SSL certificates
./local-scripts/generate-ssl-cert.sh --local-only

# Start development server
python start.py --development
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Health check
python health_check.py
```

## 🔒 Security Features

- **API Key Authentication**: Secure admin endpoints with hashed API keys stored in database
- **PII Protection**: Automatic detection and blocking of personal information
- **Data Encryption**: All data encrypted in transit and at rest
- **Audit Logging**: Comprehensive logging of all system activities
- **Access Control**: Role-based API key authentication and rate limiting
- **Network Security**: Restricted access via AWS Security Groups
- **Compliance**: GDPR-compliant data handling and retention

**Generate Admin API Key:**
```bash
python scripts/generate_admin_api_key.py
```

## 📊 Monitoring

### Health Checks
```bash
# System health
python health_check.py

# Service status
./local-scripts/control-remote.sh health

# API health
curl https://crypto-ai.your-domain.com/api/health
```

### Logs
```bash
# Application logs
tail -f logs/crypto_saas.log

# Service logs (AWS)
./local-scripts/control-remote.sh logs -f

# Audit logs
# Available via admin dashboard
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the development guide
4. **Run tests**: `pytest`
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the guides in the docs/ directory
- **Issues**: Report bugs and request features via GitHub Issues
- **Health Check**: Use `python health_check.py` to diagnose problems
- **Logs**: Check application logs for error details

## 🎯 Roadmap

- [ ] Multi-exchange data support (Coinbase, Kraken)
- [ ] Real-time WebSocket data streaming
- [ ] Advanced technical indicators
- [ ] Portfolio optimization recommendations
- [ ] Mobile app for alerts and monitoring
- [ ] Multi-language support
- [ ] Sentiment analysis from social media
- [ ] Backtesting framework

---

**Built with ❤️ for the crypto community**

--
-

## 📚 Documentation

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md)** - Complete local setup guide
- **[DEVELOPMENT-GUIDE.md](DEVELOPMENT-GUIDE.md)** - Development workflow and best practices

### Deployment
- **[DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)** - AWS deployment instructions
- **[docs/RDS-MIGRATION-GUIDE.md](docs/RDS-MIGRATION-GUIDE.md)** - Migrate to Amazon RDS

### Usage
- **[USER-GUIDE.md](USER-GUIDE.md)** - How to use the system
- **[REST-API-GUIDE.md](REST-API-GUIDE.md)** - API documentation with examples
- **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** - Dashboard features
- **[docs/QUICK-START-COLLECTOR.md](docs/QUICK-START-COLLECTOR.md)** - Data collection quick start (NEW!)
- **[docs/COLLECTOR-IMPROVEMENTS.md](docs/COLLECTOR-IMPROVEMENTS.md)** - Smart collector features (NEW!)

### Operations
- **[alembic/README.md](alembic/README.md)** - Database migrations
- **[SECURITY-CONFORMANCE-GUIDE.md](SECURITY-CONFORMANCE-GUIDE.md)** - Security practices

### Reference
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Project completion summary

---

## 🔧 Common Tasks

### Database Operations

```bash
# Run migrations
python scripts/migrate_upgrade.py

# Check current version
python scripts/migrate_current.py

# Rollback migration
python scripts/migrate_downgrade.py -1

# Backup database
pg_dump -U crypto_user -d crypto_db > backup.sql
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_api_basic.py
```

### Data Collection

```bash
# Trigger manual collection
curl -X POST http://localhost:5000/api/admin/collect/trigger \
  -H "Content-Type: application/json" \
  -d '{"mode":"manual","start_date":"2024-01-01"}'

# Check collection status
curl http://localhost:5000/api/admin/collect/status
```

---

## 🐛 Troubleshooting

### PostgreSQL Issues

**Can't connect to database:**
```bash
# Check if PostgreSQL is running
# Windows:
sc query postgresql-x64-15

# macOS:
brew services list | grep postgresql

# Linux:
sudo systemctl status postgresql
```

**Database doesn't exist:**
```bash
psql -U postgres
CREATE DATABASE crypto_db;
CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
```

### Python Issues

**Module not found:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Port already in use:**
```bash
# Find and kill process using port 5000
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID>
```

### OpenAI API Issues

**Invalid API key:**
1. Get a valid key from https://platform.openai.com/api-keys
2. Update `local-env` file
3. Reload environment variables
4. Restart services

See [docs/LOCAL-DEPLOYMENT-GUIDE.md#troubleshooting](docs/LOCAL-DEPLOYMENT-GUIDE.md#troubleshooting) for more solutions.

---

## 💡 Tips

- **First Time Setup**: Follow [QUICKSTART.md](QUICKSTART.md) for the fastest path
- **Need Help**: Check [docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md) for detailed instructions
- **PostgreSQL Required**: You must have PostgreSQL installed and running
- **OpenAI Key Required**: Get your API key before starting
- **Multiple Terminals**: You need separate terminals for API and Dashboard

---

## 📞 Support

For detailed help with specific topics:

| Topic | Documentation |
|-------|---------------|
| Local Setup | [docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md) |
| AWS Deployment | [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) |
| API Usage | [REST-API-GUIDE.md](REST-API-GUIDE.md) |
| Database | [alembic/README.md](alembic/README.md) |
| Security | [SECURITY-CONFORMANCE-GUIDE.md](SECURITY-CONFORMANCE-GUIDE.md) |

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: November 11, 2024

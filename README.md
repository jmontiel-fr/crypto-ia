# Crypto Market Analysis SaaS

An AI-powered cryptocurrency market analysis platform that provides predictions, market insights, and intelligent chat capabilities.

## 🚀 Quick Start

### Local Development (1-Minute Setup)

```bash
# Clone and setup
git clone <repository-url>
cd crypto-market-analysis-saas

# Automated setup
chmod +x local-scripts/setup-local-env.sh
./local-scripts/setup-local-env.sh

# Add your OpenAI API key
nano local-env

# Start the application
python start.py --development
```

**Access the application:**
- Main App: https://crypto-ai.local:10443
- Dashboard: http://localhost:8501
- API: https://crypto-ai.local:10443/api

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

- **`local-env`** - Local development configuration
- **`aws-env`** - AWS production configuration
- **`terraform/terraform.tfvars`** - Infrastructure configuration

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

- **PII Protection**: Automatic detection and blocking of personal information
- **Data Encryption**: All data encrypted in transit and at rest
- **Audit Logging**: Comprehensive logging of all system activities
- **Access Control**: API key authentication and rate limiting
- **Network Security**: Restricted access via AWS Security Groups
- **Compliance**: GDPR-compliant data handling and retention

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
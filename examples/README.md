# Crypto Market Analysis SaaS

A comprehensive cryptocurrency market analysis and prediction system built with Python, Flask, SQLAlchemy, and deep learning.

## Features

- **Automated Data Collection**: Gather historical cryptocurrency data from Binance API
- **Deep Learning Predictions**: LSTM/GRU-based price predictions for top cryptocurrencies
- **GenAI Chat Interface**: Natural language market analysis powered by OpenAI
- **Market Tendency Analysis**: Real-time classification of market conditions
- **SMS Alerts**: Automated notifications for significant market shifts
- **Interactive Dashboards**: Streamlit-based visualization and Bootstrap5 chat UI
- **REST API**: Comprehensive API for predictions, market data, and chat queries

## Project Structure

```
crypto-market-analysis-saas/
├── src/                          # Main application code
│   ├── config/                   # Configuration management
│   ├── utils/                    # Logging and utilities
│   ├── data/                     # Database models and repositories
│   ├── collectors/               # Data collection modules
│   ├── prediction/               # ML prediction engine
│   ├── genai/                    # OpenAI integration
│   ├── api/                      # Flask REST API
│   └── alerts/                   # Alert system
├── terraform/                    # AWS infrastructure as code
├── local-scripts/                # Local deployment scripts
├── remote-scripts/               # Remote server scripts
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment configuration template
├── local-env.example             # Local development config
├── aws-env.example               # AWS production config
└── README.md                     # This file
```

## Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 15+
- OpenAI API key
- (Optional) Binance API credentials
- (Optional) Twilio or AWS SNS for SMS alerts

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crypto-market-analysis-saas
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   ```bash
   # Create database and user
   psql -U postgres
   CREATE DATABASE crypto_db;
   CREATE USER crypto_user WITH PASSWORD 'crypto_pass';
   GRANT ALL PRIVILEGES ON DATABASE crypto_db TO crypto_user;
   ```

5. **Configure environment**
   ```bash
   cp local-env.example local-env
   # Edit local-env with your configuration
   ```

6. **Run database migrations**
   ```bash
   # Coming in next tasks
   ```

7. **Start the application**
   ```bash
   # Coming in next tasks
   ```

## Configuration

The application uses environment variables for configuration. Three template files are provided:

- `.env.example`: General template with all options documented
- `local-env.example`: Local development configuration
- `aws-env.example`: AWS production configuration

Key configuration areas:

- **Database**: PostgreSQL connection settings
- **Data Collection**: Binance API, collection schedule, tracked cryptocurrencies
- **Prediction Engine**: Model type (LSTM/GRU), training schedule
- **GenAI**: OpenAI API key and model settings
- **Alerts**: SMS provider, thresholds, notification settings
- **Security**: SSL certificates, API keys, secret keys

## Development

### Running Tests

```bash
pytest
pytest --cov=src  # With coverage
```

### Code Quality

```bash
flake8 src/
black src/
```

## Deployment

### AWS Deployment

See `DEPLOYMENT-GUIDE.md` (coming in later tasks) for detailed AWS deployment instructions using Terraform.

### Local Deployment

See `DEVELOPMENT-GUIDE.md` (coming in later tasks) for local development setup.

## Documentation

- `DEVELOPMENT-GUIDE.md`: Development setup and workflows (coming soon)
- `DEPLOYMENT-GUIDE.md`: AWS deployment procedures (coming soon)
- `USER-GUIDE.md`: System usage and features (coming soon)
- `SECURITY-CONFORMANCE-GUIDE.md`: Security practices (coming soon)

## Architecture

The system follows a modular architecture with clear separation of concerns:

1. **Data Collection Layer**: Automated gathering from Binance API
2. **Storage Layer**: PostgreSQL with SQLAlchemy ORM
3. **Analysis Layer**: Deep learning prediction engine
4. **API Layer**: Flask REST API
5. **Presentation Layer**: Streamlit dashboards + Bootstrap5 chat UI
6. **Alert Layer**: SMS notification system

## Technology Stack

- **Backend**: Python 3.10+, Flask, SQLAlchemy
- **Database**: PostgreSQL 15+
- **ML/AI**: TensorFlow, OpenAI API, spaCy
- **Frontend**: Streamlit, HTML5, CSS, Bootstrap5
- **Infrastructure**: AWS (EC2, optional RDS), Terraform
- **Scheduling**: APScheduler
- **Notifications**: Twilio or AWS SNS

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on GitHub.

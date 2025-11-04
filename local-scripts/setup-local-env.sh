#!/bin/bash
# Local Environment Setup Script for Crypto Market Analysis SaaS
# Sets up the complete local development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
PYTHON_VERSION="3.11"
VENV_NAME="venv"
DB_NAME="crypto_db"
DB_USER="crypto_user"
DB_PASSWORD="crypto_pass"
LOCAL_DOMAIN="crypto-ai.local"
LOCAL_PORT="10443"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Install system dependencies
install_system_deps() {
    local os=$(detect_os)
    
    log "Installing system dependencies for $os..."
    
    case $os in
        "linux")
            if command_exists apt-get; then
                # Ubuntu/Debian
                sudo apt-get update
                sudo apt-get install -y \
                    python${PYTHON_VERSION} \
                    python${PYTHON_VERSION}-venv \
                    python${PYTHON_VERSION}-dev \
                    postgresql \
                    postgresql-contrib \
                    libpq-dev \
                    build-essential \
                    curl \
                    git \
                    openssl \
                    ca-certificates
            elif command_exists yum; then
                # CentOS/RHEL/Amazon Linux
                sudo yum update -y
                sudo yum install -y \
                    python${PYTHON_VERSION} \
                    python${PYTHON_VERSION}-pip \
                    python${PYTHON_VERSION}-devel \
                    postgresql-server \
                    postgresql-devel \
                    gcc \
                    gcc-c++ \
                    make \
                    curl \
                    git \
                    openssl \
                    ca-certificates
            elif command_exists dnf; then
                # Fedora/newer RHEL
                sudo dnf update -y
                sudo dnf install -y \
                    python${PYTHON_VERSION} \
                    python${PYTHON_VERSION}-pip \
                    python${PYTHON_VERSION}-devel \
                    postgresql-server \
                    postgresql-devel \
                    gcc \
                    gcc-c++ \
                    make \
                    curl \
                    git \
                    openssl \
                    ca-certificates
            else
                log_error "Unsupported Linux distribution"
                exit 1
            fi
            ;;
        "macos")
            if command_exists brew; then
                brew update
                brew install python@${PYTHON_VERSION} postgresql openssl curl git
            else
                log_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
                exit 1
            fi
            ;;
        "windows")
            log_warn "Windows detected. Please ensure you have:"
            log_warn "- Python ${PYTHON_VERSION} installed"
            log_warn "- PostgreSQL installed"
            log_warn "- Git installed"
            log_warn "- OpenSSL installed (or use Git Bash)"
            ;;
        *)
            log_error "Unsupported operating system: $OSTYPE"
            exit 1
            ;;
    esac
}

# Check Python version
check_python() {
    log "Checking Python installation..."
    
    if command_exists python${PYTHON_VERSION}; then
        PYTHON_CMD="python${PYTHON_VERSION}"
    elif command_exists python3; then
        local version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$version" == "${PYTHON_VERSION}" ]]; then
            PYTHON_CMD="python3"
        else
            log_error "Python ${PYTHON_VERSION} not found. Found version: $version"
            exit 1
        fi
    elif command_exists python; then
        local version=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$version" == "${PYTHON_VERSION}" ]]; then
            PYTHON_CMD="python"
        else
            log_error "Python ${PYTHON_VERSION} not found. Found version: $version"
            exit 1
        fi
    else
        log_error "Python not found. Please install Python ${PYTHON_VERSION}"
        exit 1
    fi
    
    log "Found Python: $($PYTHON_CMD --version)"
}

# Create virtual environment
create_venv() {
    log "Creating Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    if [[ -d "$VENV_NAME" ]]; then
        log_warn "Virtual environment already exists. Removing..."
        rm -rf "$VENV_NAME"
    fi
    
    $PYTHON_CMD -m venv "$VENV_NAME"
    
    # Activate virtual environment
    if [[ -f "$VENV_NAME/bin/activate" ]]; then
        source "$VENV_NAME/bin/activate"
    elif [[ -f "$VENV_NAME/Scripts/activate" ]]; then
        source "$VENV_NAME/Scripts/activate"
    else
        log_error "Could not find virtual environment activation script"
        exit 1
    fi
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    log "Virtual environment created and activated"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_error "requirements.txt not found in project root"
        exit 1
    fi
    
    pip install -r "$PROJECT_ROOT/requirements.txt"
    
    log "Python dependencies installed"
}

# Setup PostgreSQL
setup_postgresql() {
    log "Setting up PostgreSQL database..."
    
    local os=$(detect_os)
    
    # Start PostgreSQL service
    case $os in
        "linux")
            if command_exists systemctl; then
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
            elif command_exists service; then
                sudo service postgresql start
            fi
            ;;
        "macos")
            if command_exists brew; then
                brew services start postgresql
            fi
            ;;
        "windows")
            log_warn "Please start PostgreSQL service manually on Windows"
            ;;
    esac
    
    # Wait for PostgreSQL to start
    sleep 3
    
    # Create database and user
    log "Creating database and user..."
    
    # Try different approaches based on OS
    if [[ "$os" == "linux" ]]; then
        # Linux approach
        sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME};" 2>/dev/null || log_warn "Database ${DB_NAME} may already exist"
        sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || log_warn "User ${DB_USER} may already exist"
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
        sudo -u postgres psql -c "ALTER USER ${DB_USER} CREATEDB;"
    elif [[ "$os" == "macos" ]]; then
        # macOS approach
        createdb "$DB_NAME" 2>/dev/null || log_warn "Database ${DB_NAME} may already exist"
        psql -d "$DB_NAME" -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || log_warn "User ${DB_USER} may already exist"
        psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
        psql -d "$DB_NAME" -c "ALTER USER ${DB_USER} CREATEDB;"
    else
        log_warn "Please create PostgreSQL database manually:"
        log_warn "  Database: ${DB_NAME}"
        log_warn "  User: ${DB_USER}"
        log_warn "  Password: ${DB_PASSWORD}"
    fi
    
    log "PostgreSQL setup completed"
}

# Generate SSL certificate
generate_ssl_cert() {
    log "Generating self-signed SSL certificate..."
    
    local cert_dir="$PROJECT_ROOT/certs/local"
    mkdir -p "$cert_dir"
    
    # Generate private key
    openssl genrsa -out "$cert_dir/key.pem" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$cert_dir/key.pem" -out "$cert_dir/cert.pem" -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=${LOCAL_DOMAIN}"
    
    # Set permissions
    chmod 600 "$cert_dir/key.pem"
    chmod 644 "$cert_dir/cert.pem"
    
    log "SSL certificate generated at $cert_dir"
}

# Create local environment file
create_local_env() {
    log "Creating local environment configuration..."
    
    local env_file="$PROJECT_ROOT/local-env"
    local example_file="$PROJECT_ROOT/local-env.example"
    
    if [[ -f "$env_file" ]]; then
        log_warn "local-env file already exists. Creating backup..."
        cp "$env_file" "$env_file.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    if [[ -f "$example_file" ]]; then
        cp "$example_file" "$env_file"
    else
        log_warn "local-env.example not found. Creating basic configuration..."
        cat > "$env_file" << EOF
# Environment
ENVIRONMENT=local

# Database (Local PostgreSQL)
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Web UI
WEB_UI_HOST=${LOCAL_DOMAIN}
WEB_UI_PORT=${LOCAL_PORT}
WEB_UI_PROTOCOL=https

# SSL Certificate
SSL_CERT_PATH=./certs/local/cert.pem
SSL_KEY_PATH=./certs/local/key.pem

# Data Collection
COLLECTION_START_DATE=2024-01-01
TOP_N_CRYPTOS=50
COLLECTION_SCHEDULE=0 */6 * * *
BINANCE_API_KEY=your_binance_key_here
BINANCE_API_SECRET=your_binance_secret_here

# Prediction Engine
MODEL_TYPE=LSTM
PREDICTION_HORIZON_HOURS=24
MODEL_RETRAIN_SCHEDULE=0 2 * * 0
SEQUENCE_LENGTH=168

# GenAI
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Alert System
ALERT_ENABLED=true
ALERT_THRESHOLD_PERCENT=10.0
ALERT_COOLDOWN_HOURS=4
SMS_PROVIDER=twilio
SMS_PHONE_NUMBER=+1234567890
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_FROM_NUMBER=+1234567890

# API
API_HOST=0.0.0.0
API_PORT=5000
API_KEY_REQUIRED=false
RATE_LIMIT_PER_MINUTE=100

# Streamlit
STREAMLIT_PORT=8501

# Security
SECRET_KEY=local_dev_secret_key_change_in_production
ALLOWED_ORIGINS=https://${LOCAL_DOMAIN}:${LOCAL_PORT}

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/crypto_saas.log

# Log Retention
AUDIT_LOGS_RETENTION_DAYS=90
CHAT_HISTORY_RETENTION_DAYS=30
QUERY_AUDIT_LOGS_RETENTION_DAYS=365
SYSTEM_LOGS_RETENTION_DAYS=30
LOG_RETENTION_SCHEDULE=0 2 * * *
EOF
    fi
    
    log "Local environment file created: $env_file"
    log_warn "Please edit $env_file and add your API keys:"
    log_warn "  - OPENAI_API_KEY"
    log_warn "  - BINANCE_API_KEY and BINANCE_API_SECRET (optional)"
    log_warn "  - Twilio credentials (optional, for SMS alerts)"
}

# Add local domain to hosts file
add_local_domain() {
    log "Adding local domain to hosts file..."
    
    local hosts_file="/etc/hosts"
    local entry="127.0.0.1 ${LOCAL_DOMAIN}"
    
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        hosts_file="/c/Windows/System32/drivers/etc/hosts"
    fi
    
    if ! grep -q "$LOCAL_DOMAIN" "$hosts_file" 2>/dev/null; then
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            log_warn "Please add the following line to $hosts_file manually:"
            log_warn "$entry"
        else
            echo "$entry" | sudo tee -a "$hosts_file" > /dev/null
            log "Added $LOCAL_DOMAIN to hosts file"
        fi
    else
        log "Local domain already exists in hosts file"
    fi
}

# Create log directory
create_log_dir() {
    log "Creating log directory..."
    
    local log_dir="$PROJECT_ROOT/logs"
    mkdir -p "$log_dir"
    
    log "Log directory created: $log_dir"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Check if alembic is configured
    if [[ -f "alembic.ini" ]]; then
        python -m alembic upgrade head
    else
        log_warn "Alembic not configured. Creating database tables directly..."
        python -c "
from src.data.database import create_tables
create_tables()
print('Database tables created')
"
    fi
    
    log "Database migrations completed"
}

# Test the setup
test_setup() {
    log "Testing the setup..."
    
    cd "$PROJECT_ROOT"
    
    # Test database connection
    python -c "
from src.data.database import get_session
try:
    session = get_session()
    session.execute('SELECT 1')
    session.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"
    
    # Test imports
    python -c "
try:
    from src.config.config_loader import load_config
    config = load_config()
    print('✓ Configuration loading successful')
except Exception as e:
    print(f'✗ Configuration loading failed: {e}')
    exit(1)
"
    
    log "Setup test completed successfully"
}

# Print next steps
print_next_steps() {
    log "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Edit the configuration file: $PROJECT_ROOT/local-env"
    echo "   - Add your OpenAI API key"
    echo "   - Add Binance API credentials (optional)"
    echo "   - Add Twilio credentials for SMS alerts (optional)"
    echo
    echo "2. Activate the virtual environment:"
    echo "   source $PROJECT_ROOT/$VENV_NAME/bin/activate"
    echo
    echo "3. Start the services:"
    echo "   # Flask API"
    echo "   python -m src.api.main"
    echo
    echo "   # Streamlit Dashboard (in another terminal)"
    echo "   streamlit run dashboard.py --server.port=8501"
    echo
    echo "4. Access the application:"
    echo "   - Main application: https://${LOCAL_DOMAIN}:${LOCAL_PORT}"
    echo "   - Streamlit dashboard: http://localhost:8501"
    echo
    echo "5. For development, you can also run individual components:"
    echo "   - Data collector: python -m src.collectors.scheduler"
    echo "   - Alert system: python -m src.alerts.alert_scheduler"
    echo "   - Log retention: python -m src.utils.start_retention_scheduler"
    echo
    log_info "Happy coding! 🚀"
}

# Main execution
main() {
    log "Starting local environment setup for Crypto Market Analysis SaaS"
    
    # Check if running from correct directory
    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Install system dependencies
    install_system_deps
    
    # Check Python
    check_python
    
    # Create virtual environment
    create_venv
    
    # Install Python dependencies
    install_python_deps
    
    # Setup PostgreSQL
    setup_postgresql
    
    # Generate SSL certificate
    generate_ssl_cert
    
    # Create local environment file
    create_local_env
    
    # Add local domain to hosts file
    add_local_domain
    
    # Create log directory
    create_log_dir
    
    # Run database migrations
    run_migrations
    
    # Test the setup
    test_setup
    
    # Print next steps
    print_next_steps
}

# Run main function
main "$@"
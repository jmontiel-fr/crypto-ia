#!/bin/bash
# Remote Application Setup Script
# Configures the Crypto Market Analysis SaaS application on AWS EC2

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_USER="crypto-app"
APP_DIR="/opt/crypto-saas"
LOG_DIR="/var/log/crypto-saas"
VENV_DIR="$APP_DIR/venv"
NGINX_CONF_DIR="/etc/nginx"
SYSTEMD_DIR="/etc/systemd/system"
SSL_CERT_DIR="/etc/ssl/certs"
SSL_KEY_DIR="/etc/ssl/private"

# Logging functions
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Create Python virtual environment
create_virtualenv() {
    log "Creating Python virtual environment..."
    
    # Remove existing venv if present
    if [[ -d "$VENV_DIR" ]]; then
        log_warn "Removing existing virtual environment"
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment as app user
    su - "$APP_USER" -c "python3 -m venv $VENV_DIR"
    
    # Upgrade pip, setuptools, and wheel
    su - "$APP_USER" -c "$VENV_DIR/bin/pip install --upgrade pip setuptools wheel"
    
    log "Virtual environment created at $VENV_DIR"
}

# Install Python dependencies
install_python_dependencies() {
    log "Installing Python dependencies from requirements.txt..."
    
    if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
        log_error "requirements.txt not found in $APP_DIR"
        log_error "Please deploy application code first"
        exit 1
    fi
    
    # Install dependencies as app user
    su - "$APP_USER" -c "$VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt"
    
    # Download spaCy language model for PII detection
    log "Downloading spaCy language model..."
    su - "$APP_USER" -c "$VENV_DIR/bin/python -m spacy download en_core_web_sm"
    
    log "Python dependencies installed successfully"
}

# Configure environment file
configure_environment() {
    log "Configuring environment file..."
    
    if [[ -f "$APP_DIR/aws-env.example" ]]; then
        if [[ ! -f "$APP_DIR/.env" ]]; then
            # Copy example to .env
            cp "$APP_DIR/aws-env.example" "$APP_DIR/.env"
            log_warn "Created .env from aws-env.example"
            log_warn "IMPORTANT: Edit $APP_DIR/.env with actual values before starting services"
        else
            log_info ".env file already exists, skipping"
        fi
    else
        log_error "aws-env.example not found in $APP_DIR"
        exit 1
    fi
    
    # Set ownership and permissions
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    log "Environment file configured"
}

# Generate self-signed SSL certificate
generate_ssl_certificate() {
    log "Generating self-signed SSL certificate..."
    
    # Create SSL directories if they don't exist
    mkdir -p "$SSL_CERT_DIR"
    mkdir -p "$SSL_KEY_DIR"
    
    # Certificate details
    DOMAIN="crypto-ai.crypto-vision.com"
    CERT_FILE="$SSL_CERT_DIR/crypto-ai-cert.pem"
    KEY_FILE="$SSL_KEY_DIR/crypto-ai-key.pem"
    
    # Check if certificate already exists
    if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
        log_info "SSL certificate already exists, skipping generation"
        return
    fi
    
    # Generate self-signed certificate (valid for 365 days)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:www.$DOMAIN"
    
    # Set permissions
    chmod 644 "$CERT_FILE"
    chmod 600 "$KEY_FILE"
    
    log "SSL certificate generated at $CERT_FILE"
    log_warn "This is a self-signed certificate. For production, use a certificate from a trusted CA."
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Backup existing configuration
    if [[ -f "$NGINX_CONF_DIR/nginx.conf" ]]; then
        cp "$NGINX_CONF_DIR/nginx.conf" "$NGINX_CONF_DIR/nginx.conf.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    # Create Nginx configuration for the application
    cat > "$NGINX_CONF_DIR/conf.d/crypto-saas.conf" << 'EOF'
# Crypto Market Analysis SaaS Nginx Configuration

# Upstream for Flask API
upstream flask_api {
    server 127.0.0.1:5000;
    keepalive 32;
}

# Upstream for Streamlit Dashboard
upstream streamlit_dashboard {
    server 127.0.0.1:8501;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name crypto-ai.crypto-vision.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name crypto-ai.crypto-vision.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/crypto-ai-cert.pem;
    ssl_certificate_key /etc/ssl/private/crypto-ai-key.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/crypto-saas-access.log;
    error_log /var/log/nginx/crypto-saas-error.log;
    
    # Max upload size
    client_max_body_size 10M;
    
    # API endpoints
    location /api/ {
        proxy_pass http://flask_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Chat interface
    location /chat {
        proxy_pass http://flask_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Streamlit dashboard
    location / {
        proxy_pass http://streamlit_dashboard;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket support for Streamlit
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
    
    # Streamlit WebSocket endpoint
    location /_stcore/stream {
        proxy_pass http://streamlit_dashboard/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://flask_api/health;
        access_log off;
    }
}
EOF
    
    # Test Nginx configuration
    nginx -t
    
    log "Nginx configured successfully"
}

# Create systemd service for Flask API
create_flask_service() {
    log "Creating systemd service for Flask API..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-api.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Flask API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python $APP_DIR/run_api.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/api.log
StandardError=append:$LOG_DIR/api-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $APP_DIR/models $APP_DIR/data

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    log "Flask API service created"
}

# Create systemd service for Streamlit Dashboard
create_streamlit_service() {
    log "Creating systemd service for Streamlit Dashboard..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-dashboard.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Streamlit Dashboard
After=network.target crypto-saas-api.service
Wants=crypto-saas-api.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/streamlit run $APP_DIR/dashboard.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/dashboard.log
StandardError=append:$LOG_DIR/dashboard-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $APP_DIR/models $APP_DIR/data

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    log "Streamlit Dashboard service created"
}

# Create systemd service for Data Collector
create_collector_service() {
    log "Creating systemd service for Data Collector..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-collector.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Data Collector
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python -m src.collector.scheduler
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/collector.log
StandardError=append:$LOG_DIR/collector-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $APP_DIR/data

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    log "Data Collector service created"
}

# Create systemd service for Alert System
create_alert_service() {
    log "Creating systemd service for Alert System..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-alerts.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Alert System
After=network.target postgresql.service crypto-saas-api.service
Wants=postgresql.service crypto-saas-api.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python -m src.alerts.scheduler
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/alerts.log
StandardError=append:$LOG_DIR/alerts-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    log "Alert System service created"
}

# Initialize database
initialize_database() {
    log "Initializing database..."
    
    # Check if database is accessible
    if ! su - "$APP_USER" -c "PGPASSWORD=\$(grep DATABASE_URL $APP_DIR/.env | cut -d: -f3 | cut -d@ -f1) psql -h localhost -U crypto_user -d crypto_db -c 'SELECT 1' >/dev/null 2>&1"; then
        log_error "Cannot connect to database. Please ensure PostgreSQL is running and configured."
        exit 1
    fi
    
    # Run database migrations
    log "Running database migrations..."
    su - "$APP_USER" -c "cd $APP_DIR && $VENV_DIR/bin/alembic upgrade head"
    
    log "Database initialized successfully"
}

# Create application directories
create_app_directories() {
    log "Creating application directories..."
    
    # Create necessary directories
    mkdir -p "$APP_DIR/models"
    mkdir -p "$APP_DIR/data"
    mkdir -p "$APP_DIR/certs"
    mkdir -p "$LOG_DIR"
    
    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
    
    # Set permissions
    chmod 755 "$APP_DIR/models"
    chmod 755 "$APP_DIR/data"
    chmod 700 "$APP_DIR/certs"
    chmod 755 "$LOG_DIR"
    
    log "Application directories created"
}

# Enable and reload systemd services
enable_services() {
    log "Enabling systemd services..."
    
    # Reload systemd daemon
    systemctl daemon-reload
    
    # Enable services
    systemctl enable crypto-saas-api.service
    systemctl enable crypto-saas-dashboard.service
    systemctl enable crypto-saas-collector.service
    systemctl enable crypto-saas-alerts.service
    systemctl enable nginx.service
    
    log "Services enabled"
}

# Verify setup
verify_setup() {
    log "Verifying setup..."
    
    # Check virtual environment
    if [[ -d "$VENV_DIR" ]]; then
        log_info "✓ Virtual environment exists"
    else
        log_error "✗ Virtual environment not found"
        exit 1
    fi
    
    # Check environment file
    if [[ -f "$APP_DIR/.env" ]]; then
        log_info "✓ Environment file exists"
    else
        log_error "✗ Environment file not found"
        exit 1
    fi
    
    # Check SSL certificate
    if [[ -f "$SSL_CERT_DIR/crypto-ai-cert.pem" && -f "$SSL_KEY_DIR/crypto-ai-key.pem" ]]; then
        log_info "✓ SSL certificate exists"
    else
        log_error "✗ SSL certificate not found"
        exit 1
    fi
    
    # Check Nginx configuration
    if nginx -t >/dev/null 2>&1; then
        log_info "✓ Nginx configuration valid"
    else
        log_error "✗ Nginx configuration invalid"
        exit 1
    fi
    
    # Check systemd services
    local services=("crypto-saas-api" "crypto-saas-dashboard" "crypto-saas-collector" "crypto-saas-alerts")
    for service in "${services[@]}"; do
        if systemctl is-enabled "$service.service" >/dev/null 2>&1; then
            log_info "✓ Service $service enabled"
        else
            log_error "✗ Service $service not enabled"
            exit 1
        fi
    done
    
    log "Setup verification completed"
}

# Print setup summary
print_summary() {
    log "Application setup completed successfully!"
    echo
    log_info "Setup Summary:"
    echo "  Virtual environment: $VENV_DIR"
    echo "  Environment file: $APP_DIR/.env"
    echo "  SSL certificate: $SSL_CERT_DIR/crypto-ai-cert.pem"
    echo "  Nginx configuration: $NGINX_CONF_DIR/conf.d/crypto-saas.conf"
    echo
    log_info "Systemd services created:"
    echo "  - crypto-saas-api.service (Flask API)"
    echo "  - crypto-saas-dashboard.service (Streamlit Dashboard)"
    echo "  - crypto-saas-collector.service (Data Collector)"
    echo "  - crypto-saas-alerts.service (Alert System)"
    echo
    log_warn "IMPORTANT: Before starting services:"
    echo "1. Edit $APP_DIR/.env with actual configuration values"
    echo "2. Ensure PostgreSQL is running and accessible"
    echo "3. Verify database connection settings"
    echo
    log_info "To start all services:"
    echo "  sudo systemctl start crypto-saas-api"
    echo "  sudo systemctl start crypto-saas-dashboard"
    echo "  sudo systemctl start crypto-saas-collector"
    echo "  sudo systemctl start crypto-saas-alerts"
    echo "  sudo systemctl start nginx"
    echo
    log_info "Or use the start-services.sh script:"
    echo "  sudo $APP_DIR/remote-scripts/start-services.sh"
    echo
    log_info "To check service status:"
    echo "  sudo systemctl status crypto-saas-*"
    echo
    log_info "To view logs:"
    echo "  sudo journalctl -u crypto-saas-api -f"
    echo "  sudo tail -f $LOG_DIR/api.log"
}

# Main execution
main() {
    log "Starting application setup for Crypto Market Analysis SaaS"
    
    # Check if running as root
    check_root
    
    # Create application directories
    create_app_directories
    
    # Create Python virtual environment
    create_virtualenv
    
    # Install Python dependencies
    install_python_dependencies
    
    # Configure environment file
    configure_environment
    
    # Generate SSL certificate
    generate_ssl_certificate
    
    # Configure Nginx
    configure_nginx
    
    # Create systemd services
    create_flask_service
    create_streamlit_service
    create_collector_service
    create_alert_service
    
    # Initialize database
    initialize_database
    
    # Enable services
    enable_services
    
    # Verify setup
    verify_setup
    
    # Print summary
    print_summary
}

# Run main function
main "$@"

#!/bin/bash
# Application Setup Script for AWS EC2
# Configures the Crypto Market Analysis SaaS application

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
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/crypto-saas"
CONFIG_DIR="/etc/crypto-saas"
CERT_DIR="$APP_DIR/certs"
NGINX_CONF_DIR="/etc/nginx"
SYSTEMD_DIR="/etc/systemd/system"

# Service ports
FLASK_PORT=5000
STREAMLIT_PORT=8501
HTTPS_PORT=10443

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

# Verify prerequisites
verify_prerequisites() {
    log "Verifying prerequisites..."
    
    # Check if application user exists
    if ! id "$APP_USER" &>/dev/null; then
        log_error "Application user $APP_USER does not exist"
        log_error "Please run install-dependencies.sh first"
        exit 1
    fi
    
    # Check if PostgreSQL is running
    if ! systemctl is-active --quiet postgresql-crypto.service; then
        log_error "PostgreSQL service is not running"
        log_error "Please run setup-postgresql.sh first"
        exit 1
    fi
    
    # Check if application directory exists
    if [[ ! -d "$APP_DIR" ]]; then
        log_error "Application directory $APP_DIR does not exist"
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    log "Prerequisites verified"
}

# Create Python virtual environment
create_virtual_environment() {
    log "Creating Python virtual environment..."
    
    # Remove existing venv if it exists
    if [[ -d "$VENV_DIR" ]]; then
        log_warn "Removing existing virtual environment"
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
    
    # Upgrade pip, setuptools, and wheel
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
    
    log "Virtual environment created at $VENV_DIR"
}

# Install Python dependencies
install_python_dependencies() {
    log "Installing Python dependencies..."
    
    # Check if requirements.txt exists
    if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
        log_error "requirements.txt not found in $APP_DIR"
        log_error "Please deploy application code first"
        exit 1
    fi
    
    # Install dependencies
    log_info "This may take several minutes..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
    
    # Download spaCy language model
    log_info "Downloading spaCy language model..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" -m spacy download en_core_web_sm
    
    log "Python dependencies installed"
}

# Configure environment variables
configure_environment() {
    log "Configuring environment variables..."
    
    # Check if aws-env.example exists
    if [[ ! -f "$APP_DIR/aws-env.example" ]]; then
        log_error "aws-env.example not found in $APP_DIR"
        exit 1
    fi
    
    # Create .env file if it doesn't exist
    if [[ ! -f "$APP_DIR/.env" ]]; then
        log_info "Creating .env file from aws-env.example"
        sudo -u "$APP_USER" cp "$APP_DIR/aws-env.example" "$APP_DIR/.env"
        
        # Load database configuration
        if [[ -f "$CONFIG_DIR/database.conf" ]]; then
            source "$CONFIG_DIR/database.conf"
            
            # Update database connection in .env
            sudo -u "$APP_USER" sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" "$APP_DIR/.env"
            sudo -u "$APP_USER" sed -i "s|^DB_HOST=.*|DB_HOST=$DB_HOST|" "$APP_DIR/.env"
            sudo -u "$APP_USER" sed -i "s|^DB_PORT=.*|DB_PORT=$DB_PORT|" "$APP_DIR/.env"
            sudo -u "$APP_USER" sed -i "s|^DB_NAME=.*|DB_NAME=$DB_NAME|" "$APP_DIR/.env"
            sudo -u "$APP_USER" sed -i "s|^DB_USER=.*|DB_USER=$DB_USER|" "$APP_DIR/.env"
            sudo -u "$APP_USER" sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|" "$APP_DIR/.env"
            
            log_info "Database configuration updated in .env"
        else
            log_warn "Database configuration file not found"
            log_warn "Please update .env manually with database credentials"
        fi
        
        log_warn "IMPORTANT: Update .env with your API keys and configuration"
        log_warn "Required: OPENAI_API_KEY, BINANCE_API_KEY, SMS credentials"
    else
        log_info ".env file already exists"
    fi
    
    # Set proper permissions
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    log "Environment configuration completed"
}

# Run database migrations
run_database_migrations() {
    log "Running database migrations..."
    
    # Check if alembic is configured
    if [[ -f "$APP_DIR/alembic.ini" ]]; then
        log_info "Running Alembic migrations..."
        cd "$APP_DIR"
        sudo -u "$APP_USER" "$VENV_DIR/bin/alembic" upgrade head
        log "Database migrations completed"
    else
        log_warn "Alembic not configured, running init_database.py instead"
        if [[ -f "$APP_DIR/scripts/init_database.py" ]]; then
            cd "$APP_DIR"
            sudo -u "$APP_USER" "$VENV_DIR/bin/python" scripts/init_database.py
            log "Database initialized"
        else
            log_warn "No database initialization script found"
            log_warn "Database schema may need to be created manually"
        fi
    fi
}

# Generate SSL certificates
generate_ssl_certificates() {
    log "Generating SSL certificates..."
    
    # Create certificate directory
    mkdir -p "$CERT_DIR"
    chown "$APP_USER:$APP_USER" "$CERT_DIR"
    chmod 755 "$CERT_DIR"
    
    # Generate self-signed certificate for AWS environment
    if [[ ! -f "$CERT_DIR/server.crt" || ! -f "$CERT_DIR/server.key" ]]; then
        log_info "Generating self-signed SSL certificate..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$CERT_DIR/server.key" \
            -out "$CERT_DIR/server.crt" \
            -subj "/C=US/ST=State/L=City/O=CryptoSaaS/CN=crypto-ai.crypto-vision.com"
        
        # Set permissions
        chown "$APP_USER:$APP_USER" "$CERT_DIR/server.key" "$CERT_DIR/server.crt"
        chmod 600 "$CERT_DIR/server.key"
        chmod 644 "$CERT_DIR/server.crt"
        
        log "SSL certificates generated"
    else
        log_info "SSL certificates already exist"
    fi
}

# Create systemd service for Flask API
create_flask_service() {
    log "Creating Flask API systemd service..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-api.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Flask API
After=network.target postgresql-crypto.service
Wants=postgresql-crypto.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python run_api.py
Restart=always
RestartSec=10

# Logging
StandardOutput=append:$LOG_DIR/api.log
StandardError=append:$LOG_DIR/api-error.log

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$LOG_DIR $APP_DIR/models
ProtectHome=yes

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
    log "Creating Streamlit Dashboard systemd service..."
    
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
ExecStart=$VENV_DIR/bin/streamlit run dashboard.py --server.port=$STREAMLIT_PORT --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

# Logging
StandardOutput=append:$LOG_DIR/dashboard.log
StandardError=append:$LOG_DIR/dashboard-error.log

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$LOG_DIR
ProtectHome=yes

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
    log "Creating Data Collector systemd service..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-collector.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Data Collector
After=network.target postgresql-crypto.service
Wants=postgresql-crypto.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python -m src.collectors.scheduler
Restart=always
RestartSec=10

# Logging
StandardOutput=append:$LOG_DIR/collector.log
StandardError=append:$LOG_DIR/collector-error.log

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$LOG_DIR
ProtectHome=yes

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
    log "Creating Alert System systemd service..."
    
    cat > "$SYSTEMD_DIR/crypto-saas-alerts.service" << EOF
[Unit]
Description=Crypto Market Analysis SaaS - Alert System
After=network.target postgresql-crypto.service
Wants=postgresql-crypto.service

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

# Logging
StandardOutput=append:$LOG_DIR/alerts.log
StandardError=append:$LOG_DIR/alerts-error.log

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$LOG_DIR
ProtectHome=yes

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    log "Alert System service created"
}

# Configure Nginx as reverse proxy
configure_nginx() {
    log "Configuring Nginx as reverse proxy..."
    
    # Backup existing nginx configuration
    if [[ -f "$NGINX_CONF_DIR/nginx.conf" ]]; then
        cp "$NGINX_CONF_DIR/nginx.conf" "$NGINX_CONF_DIR/nginx.conf.backup"
    fi
    
    # Create Nginx configuration for the application
    cat > "$NGINX_CONF_DIR/sites-available/crypto-saas" << EOF
# Crypto Market Analysis SaaS Nginx Configuration

# Upstream for Flask API
upstream flask_api {
    server 127.0.0.1:$FLASK_PORT;
}

# Upstream for Streamlit Dashboard
upstream streamlit_dashboard {
    server 127.0.0.1:$STREAMLIT_PORT;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name crypto-ai.crypto-vision.com www.crypto-vision.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://\$host\$request_uri;
}

# HTTPS server for Chat Interface and API
server {
    listen $HTTPS_PORT ssl http2;
    server_name crypto-ai.crypto-vision.com;
    
    # SSL Configuration
    ssl_certificate $CERT_DIR/server.crt;
    ssl_certificate_key $CERT_DIR/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log $LOG_DIR/nginx-access.log;
    error_log $LOG_DIR/nginx-error.log;
    
    # Max upload size
    client_max_body_size 10M;
    
    # Root location - serve static landing page
    location / {
        root $APP_DIR/static;
        index index.html;
        try_files \$uri \$uri/ =404;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://flask_api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Chat interface
    location /chat {
        proxy_pass http://flask_api/chat;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

# HTTP server for Streamlit Dashboard
server {
    listen 8501;
    server_name crypto-ai.crypto-vision.com www.crypto-vision.com;
    
    # Logging
    access_log $LOG_DIR/nginx-streamlit-access.log;
    error_log $LOG_DIR/nginx-streamlit-error.log;
    
    location / {
        proxy_pass http://streamlit_dashboard;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /_stcore/stream {
        proxy_pass http://streamlit_dashboard/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF
    
    # Create sites-enabled directory if it doesn't exist
    mkdir -p "$NGINX_CONF_DIR/sites-enabled"
    
    # Enable the site
    ln -sf "$NGINX_CONF_DIR/sites-available/crypto-saas" "$NGINX_CONF_DIR/sites-enabled/crypto-saas"
    
    # Remove default site if it exists
    rm -f "$NGINX_CONF_DIR/sites-enabled/default"
    
    # Test Nginx configuration
    if nginx -t; then
        log "Nginx configuration is valid"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
    
    log "Nginx configured successfully"
}

# Create static landing page
create_landing_page() {
    log "Creating static landing page..."
    
    # Create static directory
    mkdir -p "$APP_DIR/static"
    chown "$APP_USER:$APP_USER" "$APP_DIR/static"
    
    # Create simple landing page
    cat > "$APP_DIR/static/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Market Analysis SaaS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .landing-container {
            background: white;
            border-radius: 20px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
        }
        .btn-custom {
            padding: 15px 40px;
            font-size: 18px;
            margin: 10px;
            border-radius: 50px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div class="landing-container text-center">
        <h1>🚀 Crypto Market Analysis</h1>
        <p class="lead">AI-Powered Cryptocurrency Market Predictions</p>
        <p class="text-muted">Access our powerful tools for cryptocurrency market analysis and predictions</p>
        
        <div class="mt-5">
            <a href="http://crypto-ai.crypto-vision.com:8501" class="btn btn-primary btn-custom">
                📊 View Dashboard
            </a>
            <a href="/chat" class="btn btn-success btn-custom">
                💬 Chat Assistant
            </a>
        </div>
        
        <div class="mt-5">
            <small class="text-muted">
                Powered by LSTM Neural Networks & OpenAI
            </small>
        </div>
    </div>
</body>
</html>
EOF
    
    chown "$APP_USER:$APP_USER" "$APP_DIR/static/index.html"
    
    log "Landing page created"
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

# Create health check script
create_health_check() {
    log "Creating health check script..."
    
    cat > /usr/local/bin/crypto-saas-health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Crypto Market Analysis SaaS

set -euo pipefail

LOG_FILE="/var/log/crypto-saas/health-check.log"

# Function to log with timestamp
log_health() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check Flask API
if systemctl is-active --quiet crypto-saas-api.service; then
    if curl -sf http://localhost:5000/api/health >/dev/null 2>&1; then
        log_health "INFO: Flask API is healthy"
    else
        log_health "WARNING: Flask API service running but not responding"
    fi
else
    log_health "ERROR: Flask API service is not running"
fi

# Check Streamlit Dashboard
if systemctl is-active --quiet crypto-saas-dashboard.service; then
    log_health "INFO: Streamlit Dashboard is running"
else
    log_health "ERROR: Streamlit Dashboard service is not running"
fi

# Check Data Collector
if systemctl is-active --quiet crypto-saas-collector.service; then
    log_health "INFO: Data Collector is running"
else
    log_health "ERROR: Data Collector service is not running"
fi

# Check Alert System
if systemctl is-active --quiet crypto-saas-alerts.service; then
    log_health "INFO: Alert System is running"
else
    log_health "ERROR: Alert System service is not running"
fi

# Check Nginx
if systemctl is-active --quiet nginx.service; then
    log_health "INFO: Nginx is running"
else
    log_health "ERROR: Nginx service is not running"
fi

# Check disk space
DISK_USAGE=$(df /opt | awk 'NR==2 {print $5}' | sed 's/%//')
if [[ $DISK_USAGE -gt 90 ]]; then
    log_health "WARNING: Disk usage is ${DISK_USAGE}%"
fi

log_health "INFO: Health check completed"
EOF
    
    chmod +x /usr/local/bin/crypto-saas-health-check.sh
    
    # Create cron job for health checks
    cat > /etc/cron.d/crypto-saas-health-check << EOF
# Crypto SaaS health check every 5 minutes
*/5 * * * * root /usr/local/bin/crypto-saas-health-check.sh
EOF
    
    log "Health check script created"
}

# Verify application setup
verify_setup() {
    log "Verifying application setup..."
    
    # Check virtual environment
    if [[ -d "$VENV_DIR" && -f "$VENV_DIR/bin/python" ]]; then
        log_info "✓ Virtual environment exists"
    else
        log_error "✗ Virtual environment not found"
        exit 1
    fi
    
    # Check .env file
    if [[ -f "$APP_DIR/.env" ]]; then
        log_info "✓ Environment configuration exists"
    else
        log_error "✗ .env file not found"
        exit 1
    fi
    
    # Check SSL certificates
    if [[ -f "$CERT_DIR/server.crt" && -f "$CERT_DIR/server.key" ]]; then
        log_info "✓ SSL certificates exist"
    else
        log_error "✗ SSL certificates not found"
        exit 1
    fi
    
    # Check systemd services
    local services=("crypto-saas-api" "crypto-saas-dashboard" "crypto-saas-collector" "crypto-saas-alerts")
    for service in "${services[@]}"; do
        if [[ -f "$SYSTEMD_DIR/${service}.service" ]]; then
            log_info "✓ Service ${service} configured"
        else
            log_error "✗ Service ${service} not found"
            exit 1
        fi
    done
    
    # Check Nginx configuration
    if [[ -f "$NGINX_CONF_DIR/sites-available/crypto-saas" ]]; then
        log_info "✓ Nginx configuration exists"
    else
        log_error "✗ Nginx configuration not found"
        exit 1
    fi
    
    log "Application setup verification completed"
}

# Print setup summary
print_summary() {
    log "Application setup completed successfully!"
    echo
    log_info "Application Configuration:"
    echo "  Application Directory: $APP_DIR"
    echo "  Virtual Environment: $VENV_DIR"
    echo "  Log Directory: $LOG_DIR"
    echo "  Configuration Directory: $CONFIG_DIR"
    echo "  SSL Certificates: $CERT_DIR"
    echo
    log_info "Services Created:"
    echo "  - crypto-saas-api.service (Flask API on port $FLASK_PORT)"
    echo "  - crypto-saas-dashboard.service (Streamlit on port $STREAMLIT_PORT)"
    echo "  - crypto-saas-collector.service (Data Collector)"
    echo "  - crypto-saas-alerts.service (Alert System)"
    echo "  - nginx.service (Reverse Proxy on port $HTTPS_PORT)"
    echo
    log_info "Access URLs:"
    echo "  Landing Page: https://crypto-ai.crypto-vision.com:$HTTPS_PORT"
    echo "  Dashboard: http://crypto-ai.crypto-vision.com:$STREAMLIT_PORT"
    echo "  Chat Interface: https://crypto-ai.crypto-vision.com:$HTTPS_PORT/chat"
    echo "  API: https://crypto-ai.crypto-vision.com:$HTTPS_PORT/api/"
    echo
    log_info "Next Steps:"
    echo "1. Update $APP_DIR/.env with your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - BINANCE_API_KEY (if required)"
    echo "   - SMS provider credentials (Twilio or AWS SNS)"
    echo
    echo "2. Start services:"
    echo "   sudo systemctl start crypto-saas-api"
    echo "   sudo systemctl start crypto-saas-dashboard"
    echo "   sudo systemctl start crypto-saas-collector"
    echo "   sudo systemctl start crypto-saas-alerts"
    echo "   sudo systemctl start nginx"
    echo
    echo "3. Or use the start-services.sh script:"
    echo "   sudo /opt/crypto-saas/remote-scripts/start-services.sh"
    echo
    echo "4. Check service status:"
    echo "   sudo systemctl status crypto-saas-*"
    echo
    echo "5. View logs:"
    echo "   tail -f $LOG_DIR/*.log"
    echo
    log_warn "Important Security Notes:"
    echo "  - Update .env file with production API keys"
    echo "  - SSL certificates are self-signed (consider Let's Encrypt for production)"
    echo "  - Ensure Security Group allows traffic on ports 22, 443, 8501, and $HTTPS_PORT"
    echo "  - Review and update Nginx security headers as needed"
}

# Main execution
main() {
    log "Starting application setup for Crypto Market Analysis SaaS"
    
    # Check if running as root
    check_root
    
    # Verify prerequisites
    verify_prerequisites
    
    # Create Python virtual environment
    create_virtual_environment
    
    # Install Python dependencies
    install_python_dependencies
    
    # Configure environment variables
    configure_environment
    
    # Run database migrations
    run_database_migrations
    
    # Generate SSL certificates
    generate_ssl_certificates
    
    # Create systemd services
    create_flask_service
    create_streamlit_service
    create_collector_service
    create_alert_service
    
    # Configure Nginx
    configure_nginx
    
    # Create landing page
    create_landing_page
    
    # Enable services
    enable_services
    
    # Create health check
    create_health_check
    
    # Verify setup
    verify_setup
    
    # Print summary
    print_summary
}

# Run main function
main "$@"

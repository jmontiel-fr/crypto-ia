#!/bin/bash
# PostgreSQL Setup Script for AWS EC2
# Installs and configures PostgreSQL 15 on EC2 instance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_VERSION="15"
DB_NAME="crypto_db"
DB_USER="crypto_user"
DB_PASSWORD="crypto_pass_$(openssl rand -hex 8)"
DATA_DIR="/data/postgresql"
BACKUP_DIR="/data/postgresql/backups"
APP_USER="crypto-app"

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

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect operating system"
        exit 1
    fi
    
    log "Detected OS: $OS $VERSION"
}

# Install PostgreSQL
install_postgresql() {
    log "Installing PostgreSQL $POSTGRES_VERSION..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y postgresql${POSTGRES_VERSION}-server postgresql${POSTGRES_VERSION} postgresql${POSTGRES_VERSION}-contrib
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get update
            apt-get install -y postgresql-${POSTGRES_VERSION} postgresql-client-${POSTGRES_VERSION} postgresql-contrib-${POSTGRES_VERSION}
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y postgresql${POSTGRES_VERSION}-server postgresql${POSTGRES_VERSION} postgresql${POSTGRES_VERSION}-contrib
            else
                yum install -y postgresql${POSTGRES_VERSION}-server postgresql${POSTGRES_VERSION} postgresql${POSTGRES_VERSION}-contrib
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y postgresql-server postgresql postgresql-contrib
            ;;
        *)
            log_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    log "PostgreSQL $POSTGRES_VERSION installed"
}

# Setup data directory on separate EBS volume
setup_data_directory() {
    log "Setting up PostgreSQL data directory..."
    
    # Check if data volume is mounted
    if ! mountpoint -q "$DATA_DIR"; then
        log_warn "Data directory $DATA_DIR is not a mount point"
        log_warn "Ensure the EBS volume is properly mounted"
        
        # Create directory anyway for single-volume setups
        mkdir -p "$DATA_DIR"
    fi
    
    # Create subdirectories
    mkdir -p "$DATA_DIR/data"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$DATA_DIR/logs"
    mkdir -p "$DATA_DIR/archive"
    
    # Set ownership to postgres user
    chown -R postgres:postgres "$DATA_DIR"
    chmod 700 "$DATA_DIR/data"
    chmod 755 "$BACKUP_DIR"
    chmod 755 "$DATA_DIR/logs"
    chmod 755 "$DATA_DIR/archive"
    
    log "Data directory configured at $DATA_DIR"
}

# Initialize PostgreSQL database
initialize_database() {
    log "Initializing PostgreSQL database..."
    
    # Check if database is already initialized
    if [[ -f "$DATA_DIR/data/PG_VERSION" ]]; then
        log_warn "PostgreSQL database already initialized"
        return 0
    fi
    
    case $OS in
        "amzn"|"centos"|"rhel"|"rocky"|"almalinux"|"fedora")
            # Red Hat family
            sudo -u postgres /usr/pgsql-${POSTGRES_VERSION}/bin/initdb -D "$DATA_DIR/data" --locale=en_US.UTF-8 --encoding=UTF8
            ;;
        "ubuntu"|"debian")
            # Debian family
            sudo -u postgres /usr/lib/postgresql/${POSTGRES_VERSION}/bin/initdb -D "$DATA_DIR/data" --locale=en_US.UTF-8 --encoding=UTF8
            ;;
    esac
    
    log "PostgreSQL database initialized"
}

# Configure PostgreSQL
configure_postgresql() {
    log "Configuring PostgreSQL..."
    
    local config_file="$DATA_DIR/data/postgresql.conf"
    local hba_file="$DATA_DIR/data/pg_hba.conf"
    
    # Backup original configuration files
    cp "$config_file" "$config_file.backup"
    cp "$hba_file" "$hba_file.backup"
    
    # Configure postgresql.conf
    cat >> "$config_file" << EOF

# Crypto Market Analysis SaaS Configuration
# Performance and memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Connection settings
max_connections = 100
listen_addresses = 'localhost'
port = 5432

# Logging settings
log_destination = 'stderr'
logging_collector = on
log_directory = '$DATA_DIR/logs'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 10MB

# Archive settings (for future backup improvements)
archive_mode = on
archive_command = 'cp %p $DATA_DIR/archive/%f'
archive_timeout = 300

# Security settings
ssl = off
password_encryption = scram-sha-256

# Autovacuum settings
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
EOF
    
    # Configure pg_hba.conf for local connections
    cat > "$hba_file" << EOF
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             $DB_USER                               md5
local   $DB_NAME        $DB_USER                               md5

# IPv4 local connections
host    all             postgres        127.0.0.1/32            scram-sha-256
host    $DB_NAME        $DB_USER        127.0.0.1/32            scram-sha-256

# IPv6 local connections
host    all             postgres        ::1/128                 scram-sha-256
host    $DB_NAME        $DB_USER        ::1/128                 scram-sha-256
EOF
    
    # Set proper permissions
    chown postgres:postgres "$config_file" "$hba_file"
    chmod 600 "$config_file" "$hba_file"
    
    log "PostgreSQL configuration updated"
}

# Create systemd service file
create_systemd_service() {
    log "Creating systemd service file..."
    
    case $OS in
        "amzn"|"centos"|"rhel"|"rocky"|"almalinux"|"fedora")
            # Red Hat family
            local pg_bin_dir="/usr/pgsql-${POSTGRES_VERSION}/bin"
            ;;
        "ubuntu"|"debian")
            # Debian family
            local pg_bin_dir="/usr/lib/postgresql/${POSTGRES_VERSION}/bin"
            ;;
    esac
    
    cat > /etc/systemd/system/postgresql-crypto.service << EOF
[Unit]
Description=PostgreSQL database server for Crypto Market Analysis SaaS
Documentation=man:postgres(1)
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=postgres
ExecStart=$pg_bin_dir/postgres -D $DATA_DIR/data
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGINT
TimeoutSec=0

# Restart settings
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$DATA_DIR
ProtectHome=yes

# Resource limits
LimitNOFILE=65536
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable postgresql-crypto.service
    
    log "Systemd service created and enabled"
}

# Start PostgreSQL service
start_postgresql() {
    log "Starting PostgreSQL service..."
    
    systemctl start postgresql-crypto.service
    
    # Wait for PostgreSQL to start
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
            break
        fi
        
        log_info "Waiting for PostgreSQL to start (attempt $attempt/$max_attempts)..."
        sleep 2
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "PostgreSQL failed to start after $max_attempts attempts"
        systemctl status postgresql-crypto.service
        exit 1
    fi
    
    log "PostgreSQL service started successfully"
}

# Create database and user
create_database_and_user() {
    log "Creating database and user..."
    
    # Create database user
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || log_warn "User $DB_USER may already exist"
    
    # Create database
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || log_warn "Database $DB_NAME may already exist"
    
    # Grant privileges
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"
    
    # Create extensions
    sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
    sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS \"pg_stat_statements\";"
    
    log "Database $DB_NAME and user $DB_USER created"
}

# Configure database connection for application
configure_app_connection() {
    log "Configuring application database connection..."
    
    # Create .pgpass file for application user
    local pgpass_file="/home/$APP_USER/.pgpass"
    echo "localhost:5432:$DB_NAME:$DB_USER:$DB_PASSWORD" > "$pgpass_file"
    chown "$APP_USER:$APP_USER" "$pgpass_file"
    chmod 600 "$pgpass_file"
    
    # Create database connection info file
    local db_info_file="/etc/crypto-saas/database.conf"
    cat > "$db_info_file" << EOF
# Database connection configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
EOF
    
    chown "$APP_USER:$APP_USER" "$db_info_file"
    chmod 600 "$db_info_file"
    
    log "Application database connection configured"
}

# Setup database backup script
setup_backup_script() {
    log "Setting up database backup script..."
    
    cat > /usr/local/bin/backup-crypto-db.sh << 'EOF'
#!/bin/bash
# PostgreSQL backup script for Crypto Market Analysis SaaS

set -euo pipefail

# Configuration
DB_NAME="crypto_db"
DB_USER="crypto_user"
BACKUP_DIR="/data/postgresql/backups"
RETENTION_DAYS=7

# Create backup filename with timestamp
BACKUP_FILE="$BACKUP_DIR/crypto_db_$(date +%Y%m%d_%H%M%S).sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup: $BACKUP_FILE"
sudo -u postgres pg_dump -U postgres -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Set permissions
chmod 600 "$BACKUP_FILE"

# Clean up old backups
echo "Cleaning up backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "crypto_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE"
EOF
    
    chmod +x /usr/local/bin/backup-crypto-db.sh
    
    # Create cron job for daily backups
    cat > /etc/cron.d/crypto-db-backup << EOF
# Daily PostgreSQL backup for Crypto Market Analysis SaaS
0 2 * * * root /usr/local/bin/backup-crypto-db.sh >> /var/log/crypto-saas/backup.log 2>&1
EOF
    
    log "Database backup script and cron job created"
}

# Configure PostgreSQL monitoring
setup_monitoring() {
    log "Setting up PostgreSQL monitoring..."
    
    # Create monitoring script
    cat > /usr/local/bin/postgres-health-check.sh << 'EOF'
#!/bin/bash
# PostgreSQL health check script

set -euo pipefail

DB_NAME="crypto_db"
LOG_FILE="/var/log/crypto-saas/postgres-health.log"

# Function to log with timestamp
log_health() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql-crypto.service; then
    log_health "ERROR: PostgreSQL service is not running"
    exit 1
fi

# Check database connectivity
if ! sudo -u postgres psql -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
    log_health "ERROR: Cannot connect to database $DB_NAME"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df /data/postgresql | awk 'NR==2 {print $5}' | sed 's/%//')
if [[ $DISK_USAGE -gt 90 ]]; then
    log_health "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Check connection count
CONN_COUNT=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" | xargs)
if [[ $CONN_COUNT -gt 80 ]]; then
    log_health "WARNING: High connection count: $CONN_COUNT"
fi

log_health "INFO: PostgreSQL health check passed"
EOF
    
    chmod +x /usr/local/bin/postgres-health-check.sh
    
    # Create cron job for health checks
    cat > /etc/cron.d/postgres-health-check << EOF
# PostgreSQL health check every 5 minutes
*/5 * * * * root /usr/local/bin/postgres-health-check.sh
EOF
    
    log "PostgreSQL monitoring configured"
}

# Verify PostgreSQL installation
verify_installation() {
    log "Verifying PostgreSQL installation..."
    
    # Check service status
    if systemctl is-active --quiet postgresql-crypto.service; then
        log_info "✓ PostgreSQL service is running"
    else
        log_error "✗ PostgreSQL service is not running"
        exit 1
    fi
    
    # Check database connectivity
    if sudo -u postgres psql -c "SELECT version();" >/dev/null 2>&1; then
        local version=$(sudo -u postgres psql -t -c "SELECT version();" | xargs)
        log_info "✓ PostgreSQL connectivity: $version"
    else
        log_error "✗ Cannot connect to PostgreSQL"
        exit 1
    fi
    
    # Check database and user
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        log_info "✓ Database $DB_NAME exists"
    else
        log_error "✗ Database $DB_NAME does not exist"
        exit 1
    fi
    
    # Check application user connection
    if PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        log_info "✓ Application user $DB_USER can connect"
    else
        log_error "✗ Application user $DB_USER cannot connect"
        exit 1
    fi
    
    # Check data directory
    if [[ -d "$DATA_DIR/data" && -f "$DATA_DIR/data/PG_VERSION" ]]; then
        log_info "✓ Data directory configured at $DATA_DIR"
    else
        log_error "✗ Data directory not properly configured"
        exit 1
    fi
    
    log "PostgreSQL installation verification completed"
}

# Print setup summary
print_summary() {
    log "PostgreSQL setup completed successfully!"
    echo
    log_info "PostgreSQL Configuration:"
    echo "  Version: PostgreSQL $POSTGRES_VERSION"
    echo "  Data Directory: $DATA_DIR/data"
    echo "  Backup Directory: $BACKUP_DIR"
    echo "  Service: postgresql-crypto.service"
    echo
    log_info "Database Configuration:"
    echo "  Database Name: $DB_NAME"
    echo "  Database User: $DB_USER"
    echo "  Connection: localhost:5432"
    echo
    log_info "Files Created:"
    echo "  - /etc/systemd/system/postgresql-crypto.service"
    echo "  - /etc/crypto-saas/database.conf"
    echo "  - /home/$APP_USER/.pgpass"
    echo "  - /usr/local/bin/backup-crypto-db.sh"
    echo "  - /usr/local/bin/postgres-health-check.sh"
    echo
    log_info "Cron Jobs:"
    echo "  - Daily backup at 2:00 AM"
    echo "  - Health check every 5 minutes"
    echo
    log_info "Connection String:"
    echo "  DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    echo
    log_warn "Important:"
    echo "  - Database password has been generated and saved"
    echo "  - Update your application .env file with the connection details"
    echo "  - The database is configured for local connections only"
}

# Main execution
main() {
    log "Starting PostgreSQL setup for Crypto Market Analysis SaaS"
    
    # Check if running as root
    check_root
    
    # Detect operating system
    detect_os
    
    # Install PostgreSQL
    install_postgresql
    
    # Setup data directory
    setup_data_directory
    
    # Initialize database
    initialize_database
    
    # Configure PostgreSQL
    configure_postgresql
    
    # Create systemd service
    create_systemd_service
    
    # Start PostgreSQL
    start_postgresql
    
    # Create database and user
    create_database_and_user
    
    # Configure application connection
    configure_app_connection
    
    # Setup backup script
    setup_backup_script
    
    # Setup monitoring
    setup_monitoring
    
    # Verify installation
    verify_installation
    
    # Print summary
    print_summary
}

# Run main function
main "$@"
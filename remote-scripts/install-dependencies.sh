#!/bin/bash
# Remote Dependency Installation Script
# Installs system packages and dependencies on AWS EC2 instance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.11"
APP_USER="crypto-app"
APP_DIR="/opt/crypto-saas"
LOG_DIR="/var/log/crypto-saas"

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

# Detect OS and package manager
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

# Update system packages
update_system() {
    log "Updating system packages..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf update -y
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get update -y
            apt-get upgrade -y
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf update -y
            else
                yum update -y
            fi
            ;;
        "fedora")
            # Fedora
            dnf update -y
            ;;
        *)
            log_error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    log "System packages updated"
}

# Install Python and development tools
install_python() {
    log "Installing Python $PYTHON_VERSION and development tools..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y \
                python${PYTHON_VERSION} \
                python${PYTHON_VERSION}-pip \
                python${PYTHON_VERSION}-devel \
                gcc \
                gcc-c++ \
                make \
                openssl-devel \
                libffi-devel \
                bzip2-devel \
                readline-devel \
                sqlite-devel \
                xz-devel \
                zlib-devel \
                ncurses-devel \
                tk-devel \
                gdbm-devel \
                db4-devel \
                libpcap-devel
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y \
                python${PYTHON_VERSION} \
                python${PYTHON_VERSION}-pip \
                python${PYTHON_VERSION}-dev \
                python${PYTHON_VERSION}-venv \
                build-essential \
                gcc \
                g++ \
                make \
                libssl-dev \
                libffi-dev \
                libbz2-dev \
                libreadline-dev \
                libsqlite3-dev \
                liblzma-dev \
                zlib1g-dev \
                libncurses5-dev \
                tk-dev \
                libgdbm-dev \
                libdb-dev \
                libpcap-dev
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y \
                    python${PYTHON_VERSION} \
                    python${PYTHON_VERSION}-pip \
                    python${PYTHON_VERSION}-devel \
                    gcc \
                    gcc-c++ \
                    make \
                    openssl-devel \
                    libffi-devel \
                    bzip2-devel \
                    readline-devel \
                    sqlite-devel \
                    xz-devel \
                    zlib-devel \
                    ncurses-devel \
                    tk-devel \
                    gdbm-devel \
                    libdb-devel \
                    libpcap-devel
            else
                yum install -y \
                    python${PYTHON_VERSION} \
                    python${PYTHON_VERSION}-pip \
                    python${PYTHON_VERSION}-devel \
                    gcc \
                    gcc-c++ \
                    make \
                    openssl-devel \
                    libffi-devel \
                    bzip2-devel \
                    readline-devel \
                    sqlite-devel \
                    xz-devel \
                    zlib-devel \
                    ncurses-devel \
                    tk-devel \
                    gdbm-devel \
                    libdb-devel \
                    libpcap-devel
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y \
                python${PYTHON_VERSION} \
                python${PYTHON_VERSION}-pip \
                python${PYTHON_VERSION}-devel \
                gcc \
                gcc-c++ \
                make \
                openssl-devel \
                libffi-devel \
                bzip2-devel \
                readline-devel \
                sqlite-devel \
                xz-devel \
                zlib-devel \
                ncurses-devel \
                tk-devel \
                gdbm-devel \
                libdb-devel \
                libpcap-devel
            ;;
    esac
    
    # Create symbolic links for python and pip
    ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3
    ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python
    ln -sf /usr/bin/pip${PYTHON_VERSION} /usr/bin/pip3
    ln -sf /usr/bin/pip${PYTHON_VERSION} /usr/bin/pip
    
    # Verify Python installation
    python --version
    pip --version
    
    log "Python $PYTHON_VERSION installed successfully"
}

# Install PostgreSQL client libraries
install_postgresql_client() {
    log "Installing PostgreSQL client libraries..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y \
                postgresql15-devel \
                libpq-devel
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y \
                postgresql-client \
                libpq-dev \
                postgresql-server-dev-all
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y \
                    postgresql-devel \
                    libpq-devel
            else
                yum install -y \
                    postgresql-devel \
                    libpq-devel
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y \
                postgresql-devel \
                libpq-devel
            ;;
    esac
    
    log "PostgreSQL client libraries installed"
}

# Install system dependencies for ML libraries
install_ml_dependencies() {
    log "Installing system dependencies for ML libraries..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y \
                openblas-devel \
                lapack-devel \
                atlas-devel \
                freetype-devel \
                libpng-devel \
                libjpeg-turbo-devel \
                hdf5-devel \
                netcdf-devel
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y \
                libopenblas-dev \
                liblapack-dev \
                libatlas-base-dev \
                libfreetype6-dev \
                libpng-dev \
                libjpeg-dev \
                libhdf5-dev \
                libnetcdf-dev \
                gfortran
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y \
                    openblas-devel \
                    lapack-devel \
                    atlas-devel \
                    freetype-devel \
                    libpng-devel \
                    libjpeg-turbo-devel \
                    hdf5-devel \
                    netcdf-devel \
                    gcc-gfortran
            else
                yum install -y \
                    openblas-devel \
                    lapack-devel \
                    atlas-devel \
                    freetype-devel \
                    libpng-devel \
                    libjpeg-turbo-devel \
                    hdf5-devel \
                    netcdf-devel \
                    gcc-gfortran
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y \
                openblas-devel \
                lapack-devel \
                atlas-devel \
                freetype-devel \
                libpng-devel \
                libjpeg-turbo-devel \
                hdf5-devel \
                netcdf-devel \
                gcc-gfortran
            ;;
    esac
    
    log "ML dependencies installed"
}

# Install additional system tools
install_system_tools() {
    log "Installing additional system tools..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y \
                git \
                curl \
                wget \
                unzip \
                zip \
                tar \
                gzip \
                htop \
                tree \
                vim \
                nano \
                tmux \
                screen \
                jq \
                awscli \
                rsync \
                lsof \
                netstat-nat \
                telnet \
                nc \
                bind-utils \
                ca-certificates \
                openssl \
                cronie
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y \
                git \
                curl \
                wget \
                unzip \
                zip \
                tar \
                gzip \
                htop \
                tree \
                vim \
                nano \
                tmux \
                screen \
                jq \
                awscli \
                rsync \
                lsof \
                net-tools \
                telnet \
                netcat \
                dnsutils \
                ca-certificates \
                openssl \
                cron
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y \
                    git \
                    curl \
                    wget \
                    unzip \
                    zip \
                    tar \
                    gzip \
                    htop \
                    tree \
                    vim \
                    nano \
                    tmux \
                    screen \
                    jq \
                    awscli \
                    rsync \
                    lsof \
                    net-tools \
                    telnet \
                    nc \
                    bind-utils \
                    ca-certificates \
                    openssl \
                    cronie
            else
                yum install -y \
                    git \
                    curl \
                    wget \
                    unzip \
                    zip \
                    tar \
                    gzip \
                    htop \
                    tree \
                    vim \
                    nano \
                    tmux \
                    screen \
                    jq \
                    awscli \
                    rsync \
                    lsof \
                    net-tools \
                    telnet \
                    nc \
                    bind-utils \
                    ca-certificates \
                    openssl \
                    cronie
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y \
                git \
                curl \
                wget \
                unzip \
                zip \
                tar \
                gzip \
                htop \
                tree \
                vim \
                nano \
                tmux \
                screen \
                jq \
                awscli \
                rsync \
                lsof \
                net-tools \
                telnet \
                nc \
                bind-utils \
                ca-certificates \
                openssl \
                cronie
            ;;
    esac
    
    log "System tools installed"
}

# Create application user
create_app_user() {
    log "Creating application user..."
    
    # Check if user already exists
    if id "$APP_USER" &>/dev/null; then
        log_warn "User $APP_USER already exists"
    else
        # Create user with home directory
        useradd -m -s /bin/bash "$APP_USER"
        
        # Add user to wheel/sudo group for administrative tasks
        case $OS in
            "ubuntu"|"debian")
                usermod -aG sudo "$APP_USER"
                ;;
            *)
                usermod -aG wheel "$APP_USER"
                ;;
        esac
        
        log "User $APP_USER created"
    fi
    
    # Create application directories
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "/etc/crypto-saas"
    
    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$LOG_DIR"
    chown -R "$APP_USER:$APP_USER" "/etc/crypto-saas"
    
    # Set permissions
    chmod 755 "$APP_DIR"
    chmod 755 "$LOG_DIR"
    chmod 755 "/etc/crypto-saas"
    
    log "Application directories created and configured"
}

# Install Nginx
install_nginx() {
    log "Installing Nginx..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y nginx
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y nginx
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y nginx
            else
                yum install -y nginx
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y nginx
            ;;
    esac
    
    # Enable Nginx service
    systemctl enable nginx
    
    log "Nginx installed and enabled"
}

# Install Node.js (for potential future frontend needs)
install_nodejs() {
    log "Installing Node.js..."
    
    # Install Node.js 18.x LTS
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y nodejs npm
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y nodejs npm
            else
                yum install -y nodejs npm
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y nodejs npm
            ;;
    esac
    
    # Verify installation
    node --version
    npm --version
    
    log "Node.js installed successfully"
}

# Configure system limits
configure_system_limits() {
    log "Configuring system limits..."
    
    # Create limits configuration
    cat > /etc/security/limits.d/crypto-saas.conf << EOF
# Crypto Market Analysis SaaS system limits
$APP_USER soft nofile 65536
$APP_USER hard nofile 65536
$APP_USER soft nproc 32768
$APP_USER hard nproc 32768
$APP_USER soft memlock unlimited
$APP_USER hard memlock unlimited
EOF
    
    # Configure systemd limits
    mkdir -p /etc/systemd/system.conf.d
    cat > /etc/systemd/system.conf.d/crypto-saas.conf << EOF
[Manager]
DefaultLimitNOFILE=65536
DefaultLimitNPROC=32768
DefaultLimitMEMLOCK=infinity
EOF
    
    # Reload systemd configuration
    systemctl daemon-reload
    
    log "System limits configured"
}

# Configure log rotation
configure_log_rotation() {
    log "Configuring log rotation..."
    
    cat > /etc/logrotate.d/crypto-saas << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload crypto-saas-* 2>/dev/null || true
    endscript
}
EOF
    
    log "Log rotation configured"
}

# Install and configure fail2ban for security
install_fail2ban() {
    log "Installing and configuring fail2ban..."
    
    case $OS in
        "amzn")
            # Amazon Linux
            dnf install -y fail2ban
            ;;
        "ubuntu"|"debian")
            # Ubuntu/Debian
            apt-get install -y fail2ban
            ;;
        "centos"|"rhel"|"rocky"|"almalinux")
            # CentOS/RHEL/Rocky/AlmaLinux
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y fail2ban
            else
                yum install -y fail2ban
            fi
            ;;
        "fedora")
            # Fedora
            dnf install -y fail2ban
            ;;
    esac
    
    # Configure fail2ban
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF
    
    # Enable and start fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    
    log "fail2ban installed and configured"
}

# Verify installations
verify_installations() {
    log "Verifying installations..."
    
    # Check Python
    if python --version >/dev/null 2>&1; then
        log_info "✓ Python: $(python --version)"
    else
        log_error "✗ Python installation failed"
        exit 1
    fi
    
    # Check pip
    if pip --version >/dev/null 2>&1; then
        log_info "✓ pip: $(pip --version)"
    else
        log_error "✗ pip installation failed"
        exit 1
    fi
    
    # Check PostgreSQL client
    if pg_config --version >/dev/null 2>&1; then
        log_info "✓ PostgreSQL client: $(pg_config --version)"
    else
        log_warn "⚠ PostgreSQL client may not be properly installed"
    fi
    
    # Check Nginx
    if nginx -v >/dev/null 2>&1; then
        log_info "✓ Nginx: $(nginx -v 2>&1)"
    else
        log_error "✗ Nginx installation failed"
        exit 1
    fi
    
    # Check Node.js
    if node --version >/dev/null 2>&1; then
        log_info "✓ Node.js: $(node --version)"
    else
        log_warn "⚠ Node.js may not be properly installed"
    fi
    
    # Check application user
    if id "$APP_USER" >/dev/null 2>&1; then
        log_info "✓ Application user: $APP_USER"
    else
        log_error "✗ Application user creation failed"
        exit 1
    fi
    
    # Check directories
    if [[ -d "$APP_DIR" && -d "$LOG_DIR" ]]; then
        log_info "✓ Application directories created"
    else
        log_error "✗ Application directories creation failed"
        exit 1
    fi
    
    log "Installation verification completed"
}

# Print installation summary
print_summary() {
    log "Dependency installation completed successfully!"
    echo
    log_info "Installation Summary:"
    echo "  Python: $(python --version 2>&1)"
    echo "  pip: $(pip --version 2>&1 | cut -d' ' -f1-2)"
    echo "  Nginx: $(nginx -v 2>&1)"
    echo "  Node.js: $(node --version 2>&1)"
    echo "  Application user: $APP_USER"
    echo "  Application directory: $APP_DIR"
    echo "  Log directory: $LOG_DIR"
    echo
    log_info "Services enabled:"
    echo "  - nginx"
    echo "  - fail2ban"
    echo "  - cronie/cron"
    echo
    log_info "Next steps:"
    echo "1. Run setup-postgresql.sh to install and configure PostgreSQL"
    echo "2. Run setup-application.sh to configure the application environment"
    echo "3. Deploy application code to $APP_DIR"
    echo "4. Start application services"
}

# Main execution
main() {
    log "Starting dependency installation for Crypto Market Analysis SaaS"
    
    # Check if running as root
    check_root
    
    # Detect operating system
    detect_os
    
    # Update system packages
    update_system
    
    # Install Python and development tools
    install_python
    
    # Install PostgreSQL client libraries
    install_postgresql_client
    
    # Install ML dependencies
    install_ml_dependencies
    
    # Install system tools
    install_system_tools
    
    # Create application user
    create_app_user
    
    # Install Nginx
    install_nginx
    
    # Install Node.js
    install_nodejs
    
    # Configure system limits
    configure_system_limits
    
    # Configure log rotation
    configure_log_rotation
    
    # Install fail2ban
    install_fail2ban
    
    # Verify installations
    verify_installations
    
    # Print summary
    print_summary
}

# Run main function
main "$@"
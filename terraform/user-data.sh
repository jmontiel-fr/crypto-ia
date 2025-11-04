#!/bin/bash
# User Data Script for Crypto Market Analysis SaaS EC2 Instance
# This script runs on first boot to set up the basic system

set -euo pipefail  # Exit on any error, undefined variables, or pipe failures

# Variables passed from Terraform
PROJECT_NAME="${project_name}"
DOMAIN_NAME="${domain_name}"

# Logging setup
LOG_FILE="/var/log/user-data.log"
exec > >(tee -a $LOG_FILE)
exec 2>&1

echo "=== Starting user-data script at $(date) ==="
echo "Project: $PROJECT_NAME"
echo "Domain: $DOMAIN_NAME"

# Update system packages
echo "=== Updating system packages ==="
dnf update -y

# Install essential packages
echo "=== Installing essential packages ==="
dnf install -y \
    git \
    curl \
    wget \
    unzip \
    htop \
    tree \
    vim \
    tmux \
    jq \
    awscli \
    amazon-cloudwatch-agent

# Install Python 3.11 and development tools
echo "=== Installing Python and development tools ==="
dnf install -y \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    libffi-devel \
    bzip2-devel \
    readline-devel \
    sqlite-devel \
    xz-devel

# Create symbolic links for python and pip
ln -sf /usr/bin/python3.11 /usr/bin/python3
ln -sf /usr/bin/python3.11 /usr/bin/python
ln -sf /usr/bin/pip3.11 /usr/bin/pip3
ln -sf /usr/bin/pip3.11 /usr/bin/pip

# Install PostgreSQL 15
echo "=== Installing PostgreSQL 15 ==="
dnf install -y postgresql15-server postgresql15-devel postgresql15-contrib

# Create application user
echo "=== Creating application user ==="
useradd -m -s /bin/bash crypto-app
usermod -aG wheel crypto-app

# Create application directories
echo "=== Creating application directories ==="
mkdir -p /opt/crypto-saas
mkdir -p /var/log/crypto-saas
mkdir -p /etc/crypto-saas
mkdir -p /data/postgresql

# Set ownership
chown -R crypto-app:crypto-app /opt/crypto-saas
chown -R crypto-app:crypto-app /var/log/crypto-saas
chown -R crypto-app:crypto-app /etc/crypto-saas

# Format and mount the PostgreSQL data volume
echo "=== Setting up PostgreSQL data volume ==="
# Wait for the volume to be attached
while [ ! -e /dev/nvme1n1 ] && [ ! -e /dev/xvdf ]; do
    echo "Waiting for PostgreSQL data volume to be attached..."
    sleep 5
done

# Determine the device name (newer instances use nvme, older use xvd)
if [ -e /dev/nvme1n1 ]; then
    DEVICE="/dev/nvme1n1"
else
    DEVICE="/dev/xvdf"
fi

echo "Found PostgreSQL data volume at: $DEVICE"

# Check if the volume is already formatted
if ! blkid $DEVICE; then
    echo "Formatting PostgreSQL data volume..."
    mkfs.ext4 $DEVICE
fi

# Mount the volume
echo "Mounting PostgreSQL data volume..."
mount $DEVICE /data/postgresql

# Add to fstab for persistent mounting
DEVICE_UUID=$(blkid -s UUID -o value $DEVICE)
echo "UUID=$DEVICE_UUID /data/postgresql ext4 defaults,nofail 0 2" >> /etc/fstab

# Set ownership for PostgreSQL data directory
chown -R postgres:postgres /data/postgresql

# Install Nginx
echo "=== Installing Nginx ==="
dnf install -y nginx

# Enable and start services
echo "=== Enabling services ==="
systemctl enable nginx
systemctl enable amazon-cloudwatch-agent

# Configure CloudWatch agent
echo "=== Configuring CloudWatch agent ==="
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/crypto-saas/*.log",
                        "log_group_name": "/aws/ec2/$PROJECT_NAME",
                        "log_stream_name": "{instance_id}/application",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/nginx/access.log",
                        "log_group_name": "/aws/ec2/$PROJECT_NAME",
                        "log_stream_name": "{instance_id}/nginx-access",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/nginx/error.log",
                        "log_group_name": "/aws/ec2/$PROJECT_NAME",
                        "log_stream_name": "{instance_id}/nginx-error",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "CWAgent",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
systemctl start amazon-cloudwatch-agent

# Create a basic Nginx configuration
echo "=== Creating basic Nginx configuration ==="
cat > /etc/nginx/conf.d/crypto-saas.conf << EOF
# Basic configuration - will be updated by deployment script
server {
    listen 80 default_server;
    server_name $DOMAIN_NAME;
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl default_server;
    listen 10443 ssl;
    server_name $DOMAIN_NAME;
    
    # SSL configuration will be added by deployment script
    ssl_certificate /etc/ssl/certs/crypto-saas.crt;
    ssl_certificate_key /etc/ssl/private/crypto-saas.key;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Flask API
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Streamlit Dashboard
    location /dashboard/ {
        proxy_pass http://127.0.0.1:8501/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Chat Interface
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Create SSL directory
mkdir -p /etc/ssl/private
chmod 700 /etc/ssl/private

# Generate temporary self-signed certificate
echo "=== Generating temporary SSL certificate ==="
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/crypto-saas.key \
    -out /etc/ssl/certs/crypto-saas.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_NAME"

chmod 600 /etc/ssl/private/crypto-saas.key
chmod 644 /etc/ssl/certs/crypto-saas.crt

# Create systemd service files templates
echo "=== Creating systemd service templates ==="

# Flask API service
cat > /etc/systemd/system/crypto-saas-api.service << EOF
[Unit]
Description=Crypto Market Analysis SaaS API
After=network.target postgresql.service

[Service]
Type=simple
User=crypto-app
Group=crypto-app
WorkingDirectory=/opt/crypto-saas
Environment=PATH=/opt/crypto-saas/venv/bin
ExecStart=/opt/crypto-saas/venv/bin/python -m src.api.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-saas-api

[Install]
WantedBy=multi-user.target
EOF

# Streamlit Dashboard service
cat > /etc/systemd/system/crypto-saas-dashboard.service << EOF
[Unit]
Description=Crypto Market Analysis SaaS Dashboard
After=network.target

[Service]
Type=simple
User=crypto-app
Group=crypto-app
WorkingDirectory=/opt/crypto-saas
Environment=PATH=/opt/crypto-saas/venv/bin
ExecStart=/opt/crypto-saas/venv/bin/streamlit run dashboard.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-saas-dashboard

[Install]
WantedBy=multi-user.target
EOF

# Data Collector service
cat > /etc/systemd/system/crypto-saas-collector.service << EOF
[Unit]
Description=Crypto Market Analysis SaaS Data Collector
After=network.target postgresql.service

[Service]
Type=simple
User=crypto-app
Group=crypto-app
WorkingDirectory=/opt/crypto-saas
Environment=PATH=/opt/crypto-saas/venv/bin
ExecStart=/opt/crypto-saas/venv/bin/python -m src.collectors.scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-saas-collector

[Install]
WantedBy=multi-user.target
EOF

# Alert System service
cat > /etc/systemd/system/crypto-saas-alerts.service << EOF
[Unit]
Description=Crypto Market Analysis SaaS Alert System
After=network.target postgresql.service

[Service]
Type=simple
User=crypto-app
Group=crypto-app
WorkingDirectory=/opt/crypto-saas
Environment=PATH=/opt/crypto-saas/venv/bin
ExecStart=/opt/crypto-saas/venv/bin/python -m src.alerts.alert_scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-saas-alerts

[Install]
WantedBy=multi-user.target
EOF

# Log Retention service
cat > /etc/systemd/system/crypto-saas-retention.service << EOF
[Unit]
Description=Crypto Market Analysis SaaS Log Retention
After=network.target postgresql.service

[Service]
Type=simple
User=crypto-app
Group=crypto-app
WorkingDirectory=/opt/crypto-saas
Environment=PATH=/opt/crypto-saas/venv/bin
ExecStart=/opt/crypto-saas/venv/bin/python -m src.utils.start_retention_scheduler
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=crypto-saas-retention

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Create deployment status file
echo "=== Creating deployment status file ==="
cat > /opt/crypto-saas/deployment-status.json << EOF
{
    "user_data_completed": true,
    "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project_name": "$PROJECT_NAME",
    "domain_name": "$DOMAIN_NAME",
    "instance_id": "$(curl -s http://169.254.169.254/latest/meta-data/instance-id)",
    "availability_zone": "$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)",
    "instance_type": "$(curl -s http://169.254.169.254/latest/meta-data/instance-type)",
    "ami_id": "$(curl -s http://169.254.169.254/latest/meta-data/ami-id)",
    "public_ipv4": "$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)",
    "local_ipv4": "$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)",
    "services_installed": [
        "nginx",
        "postgresql15",
        "python3.11",
        "cloudwatch-agent"
    ],
    "next_steps": [
        "Deploy application code",
        "Configure PostgreSQL",
        "Set up SSL certificates",
        "Start application services"
    ]
}
EOF

chown crypto-app:crypto-app /opt/crypto-saas/deployment-status.json

# Create welcome message
echo "=== Creating welcome message ==="
cat > /etc/motd << EOF

=======================================================
  Crypto Market Analysis SaaS - EC2 Instance Ready
=======================================================

Instance Information:
- Project: $PROJECT_NAME
- Domain: $DOMAIN_NAME
- Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)
- Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)
- Availability Zone: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)

Services Installed:
✓ Python 3.11
✓ PostgreSQL 15
✓ Nginx
✓ CloudWatch Agent

Next Steps:
1. Deploy application code using deployment scripts
2. Configure PostgreSQL database
3. Set up SSL certificates
4. Start application services

Useful Commands:
- Check deployment status: cat /opt/crypto-saas/deployment-status.json
- View logs: journalctl -u crypto-saas-*
- Check services: systemctl status crypto-saas-*

=======================================================

EOF

echo "=== User-data script completed successfully at $(date) ==="
echo "Instance is ready for application deployment."
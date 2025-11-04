# Deployment Guide - Crypto Market Analysis SaaS

This guide covers deploying the Crypto Market Analysis SaaS to AWS using Terraform and automated deployment scripts.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [Terraform Deployment](#terraform-deployment)
- [Application Deployment](#application-deployment)
- [Service Management](#service-management)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Environment Configuration](#environment-configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Future Scaling](#future-scaling)

## Overview

The deployment architecture consists of:

- **Single EC2 Instance**: Amazon Linux 2023 t3.micro (free tier eligible)
- **PostgreSQL on EC2**: Database installed directly on the instance
- **Elastic IP**: Static public IP address
- **Security Groups**: Restricted access from your IP only
- **SSL Certificates**: Self-signed certificates for HTTPS
- **Systemd Services**: All application components as managed services

**Estimated Monthly Cost**: $15-20 USD (t3.micro + EBS storage + data transfer)

## Prerequisites

### Required Tools

Install these tools on your local development machine:

```bash
# Terraform (>= 1.5.0)
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform

# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# SSH and rsync (usually pre-installed)
sudo apt-get install openssh-client rsync
```

### Required Information

Before starting, gather:

- **Your public IP address**: Visit https://whatismyipaddress.com/
- **Domain name**: Where you want to host the application
- **SSH key pair**: For EC2 access
- **OpenAI API key**: For chat functionality
- **AWS credentials**: Access key and secret key

## AWS Account Setup

### 1. Create AWS Account

1. Go to [AWS Console](https://aws.amazon.com/console/)
2. Create a new account or sign in
3. Complete account verification
4. Add payment method (required for EC2)

### 2. Create IAM User

**Create deployment user with necessary permissions:**

1. Go to IAM → Users → Create User
2. User name: `crypto-saas-deployer`
3. Attach policies:
   - `AmazonEC2FullAccess`
   - `AmazonVPCFullAccess`
   - `IAMFullAccess`
   - `AmazonSSMFullAccess`
   - `CloudWatchFullAccess`

4. Create access key for CLI access
5. Download credentials CSV file

### 3. Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# Enter your credentials:
# AWS Access Key ID: [Your access key]
# AWS Secret Access Key: [Your secret key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### 4. Create SSH Key Pair

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 2048 -f ~/.ssh/crypto-saas-key

# Set proper permissions
chmod 600 ~/.ssh/crypto-saas-key
chmod 644 ~/.ssh/crypto-saas-key.pub

# Get public key content (needed for Terraform)
cat ~/.ssh/crypto-saas-key.pub
```

## Terraform Deployment

### 1. Configure Terraform Variables

```bash
# Navigate to terraform directory
cd terraform/

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

**Required configuration:**

```hcl
# Project Configuration
project_name = "crypto-market-analysis-saas"
environment  = "prod"
owner_email  = "your-email@example.com"

# AWS Configuration
aws_region = "us-east-1"

# Network Configuration (choose one option)

# Option 1: Use existing VPC/subnet
# vpc_id    = "vpc-xxxxxxxxx"
# subnet_id = "subnet-xxxxxxxxx"

# Option 2: Create new VPC/subnet
vpc_cidr           = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"

# Security Configuration (REQUIRED - replace with your IP)
dev_workstation_cidr = "203.0.113.42/32"  # Your public IP/32

# EC2 Configuration
instance_type       = "t3.micro"  # Free tier eligible
root_volume_size    = 20          # GB
postgres_volume_size = 50         # GB

# SSH Key Configuration
create_key_pair    = true
public_key_content = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... [your public key]"

# Application Configuration
domain_name = "crypto-ai.your-domain.com"  # Your domain

# Monitoring
log_retention_days = 30
enable_backup     = true
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan deployment (review changes)
terraform plan

# Apply deployment
terraform apply

# Type 'yes' to confirm
```

**Deployment takes 5-10 minutes and will output:**
- Instance ID
- Elastic IP address
- SSH connection commands
- Application URLs

### 3. Update DNS

After deployment, update your domain's DNS:

```bash
# Get the Elastic IP
terraform output elastic_ip

# Update your DNS provider:
# A record: crypto-ai.your-domain.com → [Elastic IP]
```

## Application Deployment

### 1. Prepare Environment Configuration

```bash
# Return to project root
cd ..

# Create AWS environment file
cp aws-env.example aws-env

# Edit with your configuration
nano aws-env
```

**Key settings to update:**

```bash
# Database (leave as localhost - PostgreSQL runs on same instance)
DATABASE_URL=postgresql://crypto_user:CHANGE_PASSWORD@localhost:5432/crypto_db

# Domain
WEB_UI_HOST=crypto-ai.your-domain.com

# API Keys (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key-here
BINANCE_API_KEY=your-binance-key-here
BINANCE_API_SECRET=your-binance-secret-here

# SMS Alerts (optional)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
SMS_PHONE_NUMBER=+1234567890

# Security
SECRET_KEY=generate-a-random-secret-key-here
```

### 2. Run Full Deployment

```bash
# Make deployment script executable
chmod +x local-scripts/deploy-to-aws.sh

# Run full deployment
./local-scripts/deploy-to-aws.sh
```

This script will:
1. ✅ Verify Terraform infrastructure
2. ✅ Sync application code to EC2
3. ✅ Install system dependencies
4. ✅ Set up PostgreSQL database
5. ✅ Configure application environment
6. ✅ Start all services
7. ✅ Verify deployment

**Deployment takes 10-15 minutes.**

### 3. Verify Deployment

```bash
# Check service status
./local-scripts/control-remote.sh status

# Test API endpoints
curl -k https://[ELASTIC_IP]/api/health

# Check application health
./local-scripts/control-remote.sh health
```

## Service Management

### Available Services

The application runs as systemd services:

- `crypto-saas-api` - Flask REST API (port 5000)
- `crypto-saas-dashboard` - Streamlit dashboard (port 8501)
- `crypto-saas-collector` - Data collection from Binance
- `crypto-saas-alerts` - SMS alert system
- `crypto-saas-retention` - Log cleanup scheduler

### Service Commands

```bash
# Start all services
./local-scripts/control-remote.sh start

# Stop all services
./local-scripts/control-remote.sh stop

# Restart all services
./local-scripts/control-remote.sh restart

# Check status
./local-scripts/control-remote.sh status

# View logs
./local-scripts/control-remote.sh logs

# Follow logs in real-time
./local-scripts/control-remote.sh logs -f

# Control individual services
./local-scripts/control-remote.sh start api
./local-scripts/control-remote.sh logs dashboard
./local-scripts/control-remote.sh restart collector
```

### Manual Service Management

If you need to manage services directly on the EC2 instance:

```bash
# SSH to instance
./local-scripts/control-remote.sh connect

# Or use specific SSH command
ssh -i ~/.ssh/crypto-saas-key.pem ec2-user@[ELASTIC_IP]

# On the instance:
sudo systemctl status crypto-saas-*
sudo systemctl restart crypto-saas-api
sudo journalctl -u crypto-saas-api -f
```

## SSL Certificate Setup

### Self-Signed Certificates (Default)

The deployment automatically creates self-signed certificates:

```bash
# Generate certificates for AWS environment
./local-scripts/generate-ssl-cert.sh --aws-only

# Certificates are automatically deployed during application setup
```

### Production SSL Certificates (Recommended)

For production use, replace self-signed certificates with trusted certificates:

#### Option 1: Let's Encrypt (Free)

```bash
# SSH to instance
./local-scripts/control-remote.sh connect

# Install certbot
sudo dnf install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d crypto-ai.your-domain.com

# Certificates auto-renew via cron
```

#### Option 2: AWS Certificate Manager + ALB

For future scaling, use ALB with ACM certificates:

1. Request certificate in AWS Certificate Manager
2. Create Application Load Balancer
3. Configure ALB to use ACM certificate
4. Point ALB to EC2 instance

### Certificate Verification

```bash
# Check certificate details
openssl x509 -in /etc/ssl/certs/crypto-saas.crt -text -noout

# Test HTTPS connection
curl -I https://crypto-ai.your-domain.com

# Check certificate expiration
openssl x509 -in /etc/ssl/certs/crypto-saas.crt -noout -dates
```

This deployment guide provides comprehensive instructions for deploying the Crypto Market Analysis SaaS to AWS. For development setup, see the [DEVELOPMENT-GUIDE.md](DEVELOPMENT-GUIDE.md).
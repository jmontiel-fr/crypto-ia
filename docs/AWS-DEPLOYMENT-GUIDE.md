# AWS Deployment Guide

This guide covers deploying the Crypto Market Analysis SaaS to Amazon Web Services (AWS) for production use.

## Overview

The AWS deployment provides:
- Production-ready infrastructure on AWS EC2
- PostgreSQL database on dedicated EBS volume
- SSL/TLS encryption with self-signed certificates
- Automated backups and monitoring
- Scalable architecture with future RDS migration path

## Prerequisites

### AWS Account Setup
- **AWS Account**: [Create AWS Account](https://aws.amazon.com/free/)
- **AWS CLI**: [Install AWS CLI](https://aws.amazon.com/cli/)
- **Terraform**: [Install Terraform](https://www.terraform.io/downloads) (>= 1.5.0)

### Required Tools
- **SSH Client**: For connecting to EC2 instances
- **rsync**: For file synchronization
- **Git**: For code management

### AWS Permissions
Your AWS user/role needs permissions for:
- EC2 (instances, security groups, key pairs, EBS volumes)
- VPC (if creating new VPC)
- IAM (roles, policies, instance profiles)
- CloudWatch (logs, metrics)
- Systems Manager (SSM)

### Cost Considerations
**Estimated Monthly Costs (t3.micro):**
- EC2 t3.micro instance: ~$7.50
- EBS storage (70GB): ~$7.00
- Elastic IP: $0 (when attached)
- Data transfer: ~$1-5
- **Total: ~$15-20/month**

## Quick Start

### 1. Clone and Prepare

```bash
git clone <repository-url>
cd crypto-market-analysis-saas
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# REQUIRED: Your public IP for SSH/HTTPS access
dev_workstation_cidr = "YOUR.IP.ADDRESS.HERE/32"

# REQUIRED: Your SSH public key content
public_key_content = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your-public-key-here"

# REQUIRED: Your domain name
domain_name = "crypto-ai.your-domain.com"

# REQUIRED: Your email for tagging
owner_email = "your-email@example.com"

# Optional: AWS region
aws_region = "us-east-1"

# Optional: Instance type
instance_type = "t3.micro"
```

**Get Your Public IP:**
```bash
curl -s https://checkip.amazonaws.com/
```

**Get Your SSH Public Key:**
```bash
cat ~/.ssh/id_rsa.pub
```

### 4. Configure Application Environment

```bash
cd ..
cp aws-env.example aws-env
```

Edit `aws-env` with your API keys:

```bash
# REQUIRED: OpenAI API Key
OPENAI_API_KEY=your_openai_key_here

# Optional: Binance API Keys
BINANCE_API_KEY=your_binance_key_here
BINANCE_API_SECRET=your_binance_secret_here

# Optional: SMS Alerts (AWS SNS)
SMS_PROVIDER=aws_sns
SMS_PHONE_NUMBER=+1234567890
AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:crypto-alerts
```

### 5. Deploy to AWS

```bash
# Full deployment (infrastructure + application)
./local-scripts/deploy-to-aws.sh
```

This script will:
1. Deploy infrastructure with Terraform
2. Wait for EC2 instance to be ready
3. Sync application code
4. Install dependencies
5. Set up PostgreSQL
6. Configure application
7. Start services

### 6. Update DNS

After deployment, update your DNS to point your domain to the Elastic IP:

```bash
# Get the Elastic IP from Terraform output
cd terraform
terraform output elastic_ip
```

Point your domain's A record to this IP address.

### 7. Access Your Application

- **Main Application**: https://your-domain.com
- **Streamlit Dashboard**: https://your-domain.com:8501
- **API Health Check**: https://your-domain.com/api/health

## Manual Deployment Steps

If you prefer step-by-step deployment:

### 1. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply infrastructure
terraform apply
```

### 2. Get Connection Information

```bash
# Get outputs
terraform output

# Note the instance ID and Elastic IP
INSTANCE_ID=$(terraform output -raw instance_id)
ELASTIC_IP=$(terraform output -raw elastic_ip)
```

### 3. Connect to Instance

```bash
# SSH to instance
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP

# Or use SSM Session Manager
aws ssm start-session --target $INSTANCE_ID
```

### 4. Deploy Application Code

```bash
# From your local machine
./local-scripts/sync-code.sh
```

### 5. Install Dependencies

```bash
# On EC2 instance
sudo /opt/crypto-saas/remote-scripts/install-dependencies.sh
```

### 6. Setup PostgreSQL

```bash
# On EC2 instance
sudo /opt/crypto-saas/remote-scripts/setup-postgresql.sh
```

### 7. Setup Application

```bash
# On EC2 instance
sudo /opt/crypto-saas/remote-scripts/setup-application.sh
```

### 8. Start Services

```bash
# On EC2 instance
sudo /opt/crypto-saas/remote-scripts/start-services.sh
```

## Service Management

### Remote Control Script

Use the remote control script to manage services from your local machine:

```bash
# Check service status
./local-scripts/control-remote.sh status

# Start all services
./local-scripts/control-remote.sh start

# Stop all services
./local-scripts/control-remote.sh stop

# Restart all services
./local-scripts/control-remote.sh restart

# View logs
./local-scripts/control-remote.sh logs

# Follow logs in real-time
./local-scripts/control-remote.sh logs -f

# Check application health
./local-scripts/control-remote.sh health

# Connect via SSH
./local-scripts/control-remote.sh connect
```

### Individual Service Control

```bash
# Control specific services
./local-scripts/control-remote.sh start api
./local-scripts/control-remote.sh restart dashboard
./local-scripts/control-remote.sh logs collector -f
```

### Available Services

- **crypto-saas-api**: Flask API server
- **crypto-saas-dashboard**: Streamlit dashboard
- **crypto-saas-collector**: Data collection service
- **crypto-saas-alerts**: Alert monitoring service
- **crypto-saas-retention**: Log retention service

## Code Updates

### Sync Code Changes

```bash
# Sync only changed files
./local-scripts/sync-code.sh

# Sync without restarting services
./local-scripts/sync-code.sh --no-restart

# Preview what would be synced
./local-scripts/sync-code.sh --dry-run
```

### Full Redeployment

```bash
# Redeploy application (skip infrastructure)
./local-scripts/deploy-to-aws.sh --skip-terraform
```

## Monitoring and Maintenance

### Health Checks

```bash
# Comprehensive health check
./local-scripts/control-remote.sh health

# Check specific endpoints
curl -k https://your-domain.com/api/health
curl -k https://your-domain.com/api/predictions/top20
```

### Log Monitoring

```bash
# View recent logs
./local-scripts/control-remote.sh logs

# Follow logs in real-time
./local-scripts/control-remote.sh logs -f

# View specific service logs
./local-scripts/control-remote.sh logs api -f
```

### System Information

```bash
# Get system information
./local-scripts/control-remote.sh info

# Check resource usage
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP "htop"
```

### Database Management

```bash
# Connect to database
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo -u postgres psql -d crypto_db

# Manual backup
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo /usr/local/bin/backup-crypto-db.sh

# View backup files
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
ls -la /data/postgresql/backups/
```

## Security Configuration

### SSL Certificates

The deployment uses self-signed certificates. For production, consider:

1. **Let's Encrypt** (free):
   ```bash
   # On EC2 instance
   sudo dnf install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. **AWS Certificate Manager** (for ALB):
   - Request certificate in ACM
   - Use with Application Load Balancer

### Security Groups

The default security group allows:
- **SSH (22)**: From your IP only
- **HTTPS (443)**: From your IP only
- **Custom HTTPS (10443)**: From your IP only

To allow public access:
```bash
# Edit terraform/terraform.tfvars
dev_workstation_cidr = "0.0.0.0/0"  # Allow from anywhere (less secure)
```

### Access Methods

1. **SSH with Key Pair**:
   ```bash
   ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
   ```

2. **AWS Systems Manager (SSM)**:
   ```bash
   aws ssm start-session --target $INSTANCE_ID
   ```

3. **EC2 Instance Connect**:
   ```bash
   aws ec2-instance-connect send-ssh-public-key \
     --instance-id $INSTANCE_ID \
     --availability-zone us-east-1a \
     --instance-os-user ec2-user \
     --ssh-public-key file://~/.ssh/id_rsa.pub
   ```

## Backup and Recovery

### Automated Backups

- **Database**: Daily backups at 2 AM UTC
- **EBS Snapshots**: Configured via Data Lifecycle Manager
- **Retention**: 7 days for database, configurable for EBS

### Manual Backup

```bash
# Database backup
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo /usr/local/bin/backup-crypto-db.sh

# EBS snapshot
aws ec2 create-snapshot --volume-id vol-xxxxxxxxx --description "Manual backup"
```

### Recovery

```bash
# Restore database from backup
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo -u postgres psql -d crypto_db < /data/postgresql/backups/backup_file.sql
```

## Scaling and Optimization

### Vertical Scaling

Update instance type in `terraform.tfvars`:
```hcl
instance_type = "t3.small"  # or t3.medium, t3.large
```

Then apply changes:
```bash
cd terraform
terraform apply
```

### Horizontal Scaling (Future)

The architecture supports future scaling:
- **Application Load Balancer**: Distribute traffic
- **Auto Scaling Group**: Multiple EC2 instances
- **RDS PostgreSQL**: Managed database
- **ElastiCache**: Redis caching

### Performance Tuning

**Database Optimization:**
```bash
# Connect to database
sudo -u postgres psql -d crypto_db

# Check performance
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

**Application Optimization:**
- Increase worker processes in production
- Enable caching for predictions
- Optimize database queries

## Troubleshooting

### Common Issues

**1. Terraform Deployment Fails**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Validate Terraform configuration
terraform validate

# Check specific error in terraform output
```

**2. Cannot Connect to Instance**
```bash
# Check instance status
aws ec2 describe-instances --instance-ids $INSTANCE_ID

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx

# Verify SSH key
ssh-keygen -l -f ~/.ssh/your-key.pem
```

**3. Services Not Starting**
```bash
# Check service status
./local-scripts/control-remote.sh status

# View service logs
./local-scripts/control-remote.sh logs

# Check system resources
./local-scripts/control-remote.sh info
```

**4. Database Connection Issues**
```bash
# Check PostgreSQL status
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo systemctl status postgresql-crypto

# Check database connectivity
sudo -u postgres psql -c "SELECT 1;"
```

**5. SSL Certificate Issues**
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/certs/crypto-saas.crt -text -noout

# Regenerate certificates
./local-scripts/generate-ssl-cert.sh --aws-only
```

### Log Locations

**Application Logs:**
- `/var/log/crypto-saas/`
- `journalctl -u crypto-saas-*`

**System Logs:**
- `/var/log/messages`
- `/var/log/cloud-init.log`
- `/var/log/cloud-init-output.log`

**Database Logs:**
- `/data/postgresql/logs/`

### Performance Issues

**High CPU Usage:**
```bash
# Check processes
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP "htop"

# Check application performance
./local-scripts/control-remote.sh health
```

**High Memory Usage:**
```bash
# Check memory usage
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP "free -h"

# Restart services to free memory
./local-scripts/control-remote.sh restart
```

**Disk Space Issues:**
```bash
# Check disk usage
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP "df -h"

# Clean up old logs
ssh -i ~/.ssh/your-key.pem ec2-user@$ELASTIC_IP
sudo find /var/log -name "*.log" -mtime +30 -delete
```

## Cost Optimization

### Right-Sizing

**Monitor Usage:**
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time 2023-01-01T00:00:00Z \
  --end-time 2023-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

**Optimization Strategies:**
- Use Reserved Instances for 30-40% savings
- Schedule instances to stop during off-hours
- Use Spot Instances for development
- Optimize EBS volume sizes

### Resource Management

**Stop Instance When Not Needed:**
```bash
# Stop instance
aws ec2 stop-instances --instance-ids $INSTANCE_ID

# Start instance
aws ec2 start-instances --instance-ids $INSTANCE_ID
```

**Automated Scheduling:**
```bash
# Create Lambda function to start/stop instances
# Use EventBridge to schedule execution
```

## Migration to RDS (Future)

When ready to scale, migrate to RDS:

1. **Create RDS Instance**
2. **Export Data**: `pg_dump` from EC2 PostgreSQL
3. **Import Data**: `pg_restore` to RDS
4. **Update Configuration**: Point application to RDS
5. **Test and Validate**
6. **Decommission EC2 PostgreSQL**

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check application health
- Review logs for errors
- Monitor resource usage
- Verify backups

**Monthly:**
- Update system packages
- Review security groups
- Check SSL certificate expiry
- Optimize database performance

**Quarterly:**
- Review and optimize costs
- Update application dependencies
- Security audit
- Disaster recovery testing

### Getting Help

1. **Check Logs**: Always start with application and system logs
2. **Health Checks**: Use the built-in health check commands
3. **AWS Support**: Use AWS support for infrastructure issues
4. **Documentation**: Refer to component-specific documentation

## Next Steps

1. **Production Hardening:**
   - Implement proper SSL certificates
   - Set up monitoring and alerting
   - Configure automated backups
   - Implement security best practices

2. **Scaling Preparation:**
   - Monitor usage patterns
   - Plan for load balancer implementation
   - Consider RDS migration
   - Implement caching strategies

3. **Operational Excellence:**
   - Set up monitoring dashboards
   - Implement automated deployments
   - Create runbooks for common operations
   - Plan disaster recovery procedures

Congratulations on your AWS deployment! 🚀
# RDS Migration Guide

## Overview

This guide documents the migration path from EC2-hosted PostgreSQL to Amazon RDS PostgreSQL. This migration provides improved scalability, automated backups, and managed database operations.

## Why Migrate to RDS?

### Benefits
- **Automated Backups**: Point-in-time recovery with automated snapshots
- **High Availability**: Multi-AZ deployments for failover
- **Scalability**: Easy vertical and horizontal scaling
- **Managed Updates**: Automated patching and maintenance
- **Monitoring**: Enhanced CloudWatch metrics
- **Security**: Encryption at rest and in transit

### Cost Considerations

**Current Setup (EC2 PostgreSQL):**
- t3.micro EC2 instance: ~$7.50/month
- EBS storage (20GB): ~$2/month
- **Total**: ~$9.50/month

**RDS PostgreSQL:**
- db.t3.micro instance: ~$15/month
- Storage (20GB): ~$2.30/month
- Backup storage (20GB): ~$2/month
- **Total**: ~$19.30/month

**Cost Increase**: ~$10/month (~100% increase)

### When to Migrate

Consider migrating to RDS when:
- Database size exceeds 50GB
- Need high availability (Multi-AZ)
- Require automated backup management
- Want to reduce operational overhead
- Need better performance monitoring
- Scaling requirements increase

## Pre-Migration Checklist

- [ ] Review current database size and growth rate
- [ ] Estimate RDS costs for your workload
- [ ] Plan maintenance window for migration
- [ ] Test migration process in development
- [ ] Backup current database
- [ ] Document current database configuration
- [ ] Prepare rollback plan

## Migration Steps

### Phase 1: Preparation

#### 1.1 Create Database Backup

```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance

# Create backup
sudo /opt/crypto-saas/remote-scripts/backup-database.sh

# Download backup to local machine
scp -i your-key.pem ec2-user@your-instance:/data/postgresql/backups/crypto_db_backup_*.sql.gz ./
```

#### 1.2 Document Current Configuration

```bash
# Get current database settings
sudo -u postgres psql -d crypto_db -c "SHOW ALL;" > current_config.txt

# Get database size
sudo -u postgres psql -d crypto_db -c "SELECT pg_size_pretty(pg_database_size('crypto_db'));"

# Get table sizes
sudo -u postgres psql -d crypto_db -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Phase 2: Create RDS Instance

#### 2.1 Update Terraform Configuration

Uncomment the RDS configuration in `terraform/rds.tf`:

```hcl
# terraform/rds.tf
resource "aws_db_subnet_group" "crypto_saas" {
  name       = "crypto-saas-db-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "Crypto SaaS DB Subnet Group"
  }
}

resource "aws_db_instance" "crypto_saas" {
  identifier = "crypto-saas-db"
  
  # Engine
  engine         = "postgres"
  engine_version = "15.4"
  
  # Instance
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true
  
  # Database
  db_name  = "crypto_db"
  username = "crypto_user"
  password = var.db_password  # Use AWS Secrets Manager
  port     = 5432
  
  # Backup
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  # High Availability (optional, increases cost)
  multi_az = false  # Set to true for production
  
  # Networking
  db_subnet_group_name   = aws_db_subnet_group.crypto_saas.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  
  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn            = aws_iam_role.rds_monitoring.arn
  
  # Deletion protection
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "crypto-saas-db-final-snapshot"
  
  tags = {
    Name        = "Crypto SaaS Database"
    Environment = "production"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "crypto-saas-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "Crypto SaaS RDS Security Group"
  }
}

# Output RDS endpoint
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.crypto_saas.endpoint
  sensitive   = true
}
```

#### 2.2 Apply Terraform Changes

```bash
cd terraform

# Initialize (if needed)
terraform init

# Plan changes
terraform plan -out=rds-migration.tfplan

# Review the plan carefully
# Apply changes
terraform apply rds-migration.tfplan
```

#### 2.3 Get RDS Endpoint

```bash
# Get RDS endpoint from Terraform output
terraform output rds_endpoint

# Example output: crypto-saas-db.abc123.us-east-1.rds.amazonaws.com:5432
```

### Phase 3: Data Migration

#### 3.1 Restore Backup to RDS

```bash
# From your local machine or EC2 instance
# Set RDS connection details
export RDS_HOST="crypto-saas-db.abc123.us-east-1.rds.amazonaws.com"
export RDS_PORT="5432"
export RDS_USER="crypto_user"
export RDS_PASSWORD="your_rds_password"
export RDS_DB="crypto_db"

# Restore backup to RDS
gunzip -c crypto_db_backup_*.sql.gz | \
  PGPASSWORD=$RDS_PASSWORD psql \
  -h $RDS_HOST \
  -p $RDS_PORT \
  -U $RDS_USER \
  -d $RDS_DB

# Verify data
PGPASSWORD=$RDS_PASSWORD psql \
  -h $RDS_HOST \
  -p $RDS_PORT \
  -U $RDS_USER \
  -d $RDS_DB \
  -c "SELECT COUNT(*) FROM cryptocurrencies;"
```

#### 3.2 Verify Data Integrity

```bash
# Compare record counts
echo "EC2 PostgreSQL:"
sudo -u postgres psql -d crypto_db -c "
SELECT 
    'cryptocurrencies' as table, COUNT(*) FROM cryptocurrencies
UNION ALL
SELECT 'price_history', COUNT(*) FROM price_history
UNION ALL
SELECT 'predictions', COUNT(*) FROM predictions
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history;
"

echo "RDS PostgreSQL:"
PGPASSWORD=$RDS_PASSWORD psql -h $RDS_HOST -U $RDS_USER -d $RDS_DB -c "
SELECT 
    'cryptocurrencies' as table, COUNT(*) FROM cryptocurrencies
UNION ALL
SELECT 'price_history', COUNT(*) FROM price_history
UNION ALL
SELECT 'predictions', COUNT(*) FROM predictions
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history;
"
```

### Phase 4: Update Application Configuration

#### 4.1 Update Environment Variables

```bash
# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance

# Update .env file
sudo nano /opt/crypto-saas/.env

# Change DATABASE_URL to RDS endpoint
DATABASE_URL=postgresql://crypto_user:password@crypto-saas-db.abc123.us-east-1.rds.amazonaws.com:5432/crypto_db
```

#### 4.2 Test Application Connection

```bash
# Test database connection
cd /opt/crypto-saas
source venv/bin/activate
python -c "
from src.data.database import get_db_session
session = get_db_session()
print('✓ Database connection successful')
session.close()
"
```

#### 4.3 Restart Services

```bash
# Restart all services
sudo /opt/crypto-saas/remote-scripts/restart-services.sh

# Verify services are running
sudo systemctl status crypto-saas-*
```

### Phase 5: Validation and Monitoring

#### 5.1 Functional Testing

```bash
# Test API endpoints
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://crypto-ai.crypto-vision.com:10443/api/health

curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://crypto-ai.crypto-vision.com:10443/api/predictions/top20

# Test chat interface
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Bitcoin?", "session_id": "test-123"}' \
  https://crypto-ai.crypto-vision.com:10443/api/chat/query
```

#### 5.2 Monitor RDS Performance

```bash
# Check RDS metrics in AWS Console
# - CPU Utilization
# - Database Connections
# - Read/Write IOPS
# - Free Storage Space

# Or use AWS CLI
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=crypto-saas-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Phase 6: Decommission EC2 PostgreSQL

#### 6.1 Create Final Backup

```bash
# Create one last backup from EC2 PostgreSQL
sudo /opt/crypto-saas/remote-scripts/backup-database.sh

# Upload to S3 for long-term storage
aws s3 cp /data/postgresql/backups/crypto_db_backup_*.sql.gz \
  s3://your-backup-bucket/ec2-postgresql-final-backup/
```

#### 6.2 Stop EC2 PostgreSQL Service

```bash
# Stop PostgreSQL service
sudo systemctl stop postgresql-crypto.service
sudo systemctl disable postgresql-crypto.service

# Verify it's stopped
sudo systemctl status postgresql-crypto.service
```

#### 6.3 Clean Up (Optional)

```bash
# Remove PostgreSQL data (after confirming RDS is working)
# CAUTION: This is irreversible!
sudo rm -rf /data/postgresql/data

# Keep backups for 30 days before removing
```

## Rollback Plan

If issues occur during migration:

### Quick Rollback

```bash
# 1. Update .env back to EC2 PostgreSQL
sudo nano /opt/crypto-saas/.env
# Change DATABASE_URL back to: postgresql://crypto_user:password@localhost:5432/crypto_db

# 2. Start EC2 PostgreSQL
sudo systemctl start postgresql-crypto.service

# 3. Restart application services
sudo /opt/crypto-saas/remote-scripts/restart-services.sh

# 4. Verify services
sudo systemctl status crypto-saas-*
```

### Full Rollback

```bash
# 1. Restore from backup if needed
sudo /opt/crypto-saas/remote-scripts/backup-database.sh --restore /path/to/backup.sql.gz

# 2. Follow quick rollback steps above

# 3. Destroy RDS instance (if desired)
cd terraform
terraform destroy -target=aws_db_instance.crypto_saas
```

## Post-Migration Optimization

### Enable Multi-AZ (High Availability)

```bash
# Update Terraform
# Set multi_az = true in terraform/rds.tf

terraform apply
```

### Configure Read Replicas

```hcl
# terraform/rds.tf
resource "aws_db_instance" "crypto_saas_replica" {
  identifier             = "crypto-saas-db-replica"
  replicate_source_db    = aws_db_instance.crypto_saas.identifier
  instance_class         = "db.t3.micro"
  publicly_accessible    = false
  skip_final_snapshot    = true
  
  tags = {
    Name = "Crypto SaaS Database Replica"
  }
}
```

### Enable Enhanced Monitoring

```bash
# Already configured in Terraform with monitoring_interval = 60
# View metrics in AWS Console > RDS > Monitoring
```

### Set Up Automated Backups to S3

```bash
# Create S3 bucket for backups
aws s3 mb s3://crypto-saas-db-backups

# RDS automated backups are already enabled
# Retention period: 7 days (configurable)
```

## Cost Optimization

### Right-Size Instance

Monitor usage and adjust instance class:
- Start with db.t3.micro
- Upgrade to db.t3.small if CPU > 80%
- Consider db.t4g.micro (ARM-based) for cost savings

### Storage Optimization

- Use gp3 instead of gp2 for better performance/cost
- Enable storage autoscaling
- Archive old data to S3

### Reserved Instances

For long-term use, purchase Reserved Instances:
- 1-year: ~30% savings
- 3-year: ~50% savings

## Troubleshooting

### Connection Issues

```bash
# Test connectivity from EC2
telnet crypto-saas-db.abc123.us-east-1.rds.amazonaws.com 5432

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Verify RDS is available
aws rds describe-db-instances --db-instance-identifier crypto-saas-db
```

### Performance Issues

```bash
# Check slow queries
PGPASSWORD=$RDS_PASSWORD psql -h $RDS_HOST -U $RDS_USER -d $RDS_DB -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Check connection count
PGPASSWORD=$RDS_PASSWORD psql -h $RDS_HOST -U $RDS_USER -d $RDS_DB -c "
SELECT count(*) FROM pg_stat_activity;
"
```

### Backup/Restore Issues

```bash
# List available snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier crypto-saas-db

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier crypto-saas-db-restored \
  --db-snapshot-identifier snapshot-name
```

## References

- [AWS RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [PostgreSQL on RDS](https://aws.amazon.com/rds/postgresql/)
- Project DEPLOYMENT-GUIDE.md

---

**Last Updated**: 2024-11-11  
**Version**: 1.0.0

# Terraform Infrastructure for Crypto Market Analysis SaaS

This directory contains Terraform configuration files for deploying the Crypto Market Analysis SaaS infrastructure on AWS.

## Overview

The infrastructure includes:
- EC2 instance (Amazon Linux 2023, t3.micro by default)
- Elastic IP for static public IP address
- Security Group with restricted access
- EBS volumes for root and PostgreSQL data
- IAM role with SSM and CloudWatch permissions
- CloudWatch Log Group for application logs
- Optional VPC and subnet creation

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version >= 1.5.0)
3. **SSH key pair** for EC2 access
4. **Your public IP address** for security group configuration

## Quick Start

### 1. Configure Variables

Copy the example variables file and customize it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required: Your public IP for SSH/HTTPS access
dev_workstation_cidr = "YOUR.IP.ADDRESS.HERE/32"

# Required: Your SSH public key content
public_key_content = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your-public-key-here"

# Required: Your domain name
domain_name = "crypto-ai.your-domain.com"

# Required: Your email for tagging
owner_email = "your-email@example.com"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan Deployment

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

### 5. Update DNS

After deployment, update your DNS to point your domain to the Elastic IP:

```bash
# Get the Elastic IP from Terraform output
terraform output elastic_ip
```

## Configuration Options

### Network Configuration

**Option 1: Use Existing VPC/Subnet**
```hcl
vpc_id    = "vpc-xxxxxxxxx"
subnet_id = "subnet-xxxxxxxxx"
```

**Option 2: Create New VPC/Subnet**
```hcl
vpc_id             = ""  # Leave empty
subnet_id          = ""  # Leave empty
vpc_cidr           = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
```

### Instance Configuration

```hcl
instance_type        = "t3.micro"  # Free tier eligible
root_volume_size     = 20          # GB
postgres_volume_size = 50          # GB
```

### Security Configuration

```hcl
# Your public IP (required)
dev_workstation_cidr = "203.0.113.42/32"

# SSH key configuration
create_key_pair    = true
public_key_content = "ssh-rsa AAAAB3NzaC1yc2E..."
```

## Outputs

After successful deployment, Terraform provides useful outputs:

```bash
# View all outputs
terraform output

# Specific outputs
terraform output elastic_ip
terraform output ssh_command
terraform output application_url
```

### Key Outputs

- **elastic_ip**: Public IP address of the instance
- **instance_id**: EC2 instance ID
- **ssh_command**: Ready-to-use SSH command
- **ssm_command**: AWS SSM Session Manager command
- **application_url**: Main application URL
- **next_steps**: List of next deployment steps

## Access Methods

### 1. SSH Access
```bash
# Use the output command
terraform output ssh_command

# Or manually
ssh -i ~/.ssh/your-key.pem ec2-user@ELASTIC_IP
```

### 2. AWS Systems Manager (SSM)
```bash
# Use the output command
terraform output ssm_command

# Or manually
aws ssm start-session --target INSTANCE_ID --region us-east-1
```

### 3. EC2 Instance Connect
```bash
# Use the output command
terraform output ec2_instance_connect_command
```

## Security Features

- **Restricted Access**: SSH and HTTPS only from your IP
- **Encrypted Storage**: All EBS volumes encrypted at rest
- **IAM Role**: Least privilege access for EC2 instance
- **Security Groups**: Minimal required ports open
- **SSM Access**: Secure shell access without SSH keys

## Monitoring

- **CloudWatch Logs**: Application logs automatically collected
- **CloudWatch Metrics**: System metrics (CPU, memory, disk)
- **Detailed Monitoring**: Optional enhanced EC2 monitoring

## Cost Optimization

### Free Tier Eligible Configuration
```hcl
instance_type        = "t3.micro"
root_volume_size     = 20
postgres_volume_size = 20
enable_backup        = false
log_retention_days   = 7
```

### Estimated Monthly Costs (t3.micro)
- EC2 instance: ~$7.50
- EBS storage (70GB): ~$7.00
- Elastic IP: $0 (when attached)
- Data transfer: ~$1-5
- **Total: ~$15-20/month**

## Backup Configuration

```hcl
enable_backup         = true
backup_retention_days = 7
backup_schedule      = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
```

## Troubleshooting

### Common Issues

1. **Invalid IP Address**
   ```
   Error: Invalid CIDR block format
   ```
   Solution: Ensure your IP is in CIDR format (e.g., `203.0.113.42/32`)

2. **SSH Key Issues**
   ```
   Error: Invalid public key format
   ```
   Solution: Use the full SSH public key content from `~/.ssh/id_rsa.pub`

3. **VPC/Subnet Not Found**
   ```
   Error: VPC/Subnet does not exist
   ```
   Solution: Verify VPC/subnet IDs or leave empty to create new ones

### Getting Help

1. **Check Terraform logs**:
   ```bash
   export TF_LOG=DEBUG
   terraform apply
   ```

2. **Validate configuration**:
   ```bash
   terraform validate
   ```

3. **Check AWS resources**:
   ```bash
   aws ec2 describe-instances --instance-ids INSTANCE_ID
   ```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources including data volumes.

## File Structure

```
terraform/
├── main.tf                    # Main infrastructure configuration
├── variables.tf               # Input variables definition
├── outputs.tf                 # Output values definition
├── terraform.tfvars.example   # Example variables file
├── user-data.sh              # EC2 initialization script
└── README.md                 # This file
```

## Next Steps

After Terraform deployment:

1. **Update DNS**: Point your domain to the Elastic IP
2. **Deploy Application**: Use the deployment scripts in `../local-scripts/`
3. **Configure SSL**: Set up proper SSL certificates
4. **Test Application**: Verify all services are running
5. **Monitor**: Check CloudWatch logs and metrics

## Advanced Configuration

### Backend State Management

For production use, configure remote state storage:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "crypto-saas/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### Multi-Environment Setup

Use workspaces for different environments:

```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod
```

### Custom Tags

Add custom tags to all resources:

```hcl
additional_tags = {
  CostCenter = "Engineering"
  Team       = "DevOps"
  Purpose    = "Crypto Analysis SaaS"
}
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Terraform and AWS documentation
3. Check the project's main README for deployment guides
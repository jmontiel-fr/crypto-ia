# Crypto Market Analysis SaaS - Terraform Configuration
# Main infrastructure configuration for AWS deployment

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for state management
  # Uncomment and configure for production use
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "crypto-saas/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "crypto-market-analysis-saas"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner_email
    }
  }
}

# Local values for resource references
locals {
  # Determine VPC ID to use
  vpc_id = var.vpc_id != "" ? var.vpc_id : (
    var.use_default_vpc && length(data.aws_vpc.default) > 0 ? data.aws_vpc.default[0].id : aws_vpc.main[0].id
  )
  
  # Determine subnet ID to use
  subnet_id = var.subnet_id != "" ? var.subnet_id : (
    var.use_default_vpc && length(data.aws_subnet.default_first) > 0 ? data.aws_subnet.default_first[0].id : aws_subnet.public[0].id
  )
  
  # Common tags for all resources
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner_email
    },
    var.additional_tags
  )
}

# Create VPC if not using existing one and not using default VPC
resource "aws_vpc" "main" {
  count = var.vpc_id == "" && !var.use_default_vpc ? 1 : 0
  
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Create Internet Gateway if creating new VPC
resource "aws_internet_gateway" "main" {
  count = var.vpc_id == "" && !var.use_default_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id
  
  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Create public subnet if not using existing one and not using default VPC
resource "aws_subnet" "public" {
  count = var.subnet_id == "" && !var.use_default_vpc ? 1 : 0
  
  vpc_id                  = local.vpc_id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-subnet"
    Type = "public"
  }
}

# Create route table for public subnet if creating new VPC
resource "aws_route_table" "public" {
  count = var.vpc_id == "" && !var.use_default_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }
  
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Associate route table with public subnet
resource "aws_route_table_association" "public" {
  count = var.subnet_id == "" && !var.use_default_vpc ? 1 : 0
  
  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

# Remove duplicate data sources (now in data.tf)

# Create key pair for EC2 access
resource "aws_key_pair" "main" {
  count = var.create_key_pair ? 1 : 0
  
  key_name   = "${var.project_name}-key"
  public_key = var.public_key_content
  
  tags = {
    Name = "${var.project_name}-key-pair"
  }
}

# Security groups and IAM resources are now in separate files

# Elastic IP for the EC2 instance
resource "aws_eip" "main" {
  domain = "vpc"
  
  tags = {
    Name = "${var.project_name}-eip"
  }
}

# EBS volume for PostgreSQL data
resource "aws_ebs_volume" "postgres_data" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = var.postgres_volume_size
  type              = "gp3"
  encrypted         = true
  
  tags = {
    Name = "${var.project_name}-postgres-data"
    Type = "database"
  }
}

# EC2 Instance
resource "aws_instance" "main" {
  ami                     = data.aws_ami.amazon_linux.id
  instance_type           = var.instance_type
  key_name                = var.create_key_pair ? aws_key_pair.main[0].key_name : var.existing_key_pair_name
  vpc_security_group_ids  = [local.app_security_group_id]
  subnet_id               = local.subnet_id
  iam_instance_profile    = local.instance_profile_name
  availability_zone       = data.aws_availability_zones.available.names[0]
  
  # Root volume configuration
  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
    
    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }
  
  # User data script for initial setup
  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    project_name = var.project_name
    domain_name  = var.domain_name
  }))
  
  # Enable detailed monitoring
  monitoring = true
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-instance"
    Type = "application-server"
  })
  
  # Ensure EIP and EBS volume are created first
  depends_on = [
    aws_eip.main,
    aws_ebs_volume.postgres_data
  ]
}

# Associate Elastic IP with EC2 instance
resource "aws_eip_association" "main" {
  instance_id   = aws_instance.main.id
  allocation_id = aws_eip.main.id
}

# Attach EBS volume to EC2 instance
resource "aws_volume_attachment" "postgres_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.postgres_data.id
  instance_id = aws_instance.main.id
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/ec2/${var.project_name}"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name = "${var.project_name}-log-group"
  }
}
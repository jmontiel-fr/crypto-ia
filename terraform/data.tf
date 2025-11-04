# Data Sources for Terraform Configuration
# Retrieves information about existing AWS resources

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current AWS region
data "aws_region" "current" {}

# Get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  
  filter {
    name   = "state"
    values = ["available"]
  }
}

# Get available availability zones
data "aws_availability_zones" "available" {
  state = "available"
  
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# Get existing VPC if specified
data "aws_vpc" "existing" {
  count = var.vpc_id != "" ? 1 : 0
  id    = var.vpc_id
}

# Get existing subnet if specified
data "aws_subnet" "existing" {
  count = var.subnet_id != "" ? 1 : 0
  id    = var.subnet_id
}

# Get existing internet gateway for the VPC
data "aws_internet_gateway" "existing" {
  count = var.vpc_id != "" ? 1 : 0
  
  filter {
    name   = "attachment.vpc-id"
    values = [var.vpc_id]
  }
}

# Get the default route table for existing VPC
data "aws_route_table" "existing_public" {
  count = var.vpc_id != "" && var.subnet_id != "" ? 1 : 0
  
  subnet_id = var.subnet_id
}

# Get existing key pair if specified
data "aws_key_pair" "existing" {
  count    = !var.create_key_pair && var.existing_key_pair_name != "" ? 1 : 0
  key_name = var.existing_key_pair_name
}

# Get the latest AWS Systems Manager parameter for Amazon Linux 2023
data "aws_ssm_parameter" "amazon_linux_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
}

# Get current AWS partition (aws, aws-cn, aws-us-gov)
data "aws_partition" "current" {}

# Get AWS service endpoints for the current region
data "aws_service" "ec2" {
  service_id = "ec2"
  region     = data.aws_region.current.name
}

# Get default VPC if no VPC specified and not creating new one
data "aws_vpc" "default" {
  count   = var.vpc_id == "" && var.use_default_vpc ? 1 : 0
  default = true
}

# Get default subnets if using default VPC
data "aws_subnets" "default" {
  count = var.vpc_id == "" && var.use_default_vpc ? 1 : 0
  
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
  
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# Get the first default subnet
data "aws_subnet" "default_first" {
  count = var.vpc_id == "" && var.use_default_vpc && length(data.aws_subnets.default[0].ids) > 0 ? 1 : 0
  id    = data.aws_subnets.default[0].ids[0]
}
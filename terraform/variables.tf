# Terraform Variables for Crypto Market Analysis SaaS
# Define all input variables for the infrastructure

# Project Configuration
variable "project_name" {
  description = "Name of the project (used for resource naming)"
  type        = string
  default     = "crypto-market-analysis-saas"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "owner_email" {
  description = "Email address of the project owner"
  type        = string
  default     = "admin@example.com"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address."
  }
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# Network Configuration
variable "vpc_id" {
  description = "ID of existing VPC (leave empty to create new VPC)"
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "ID of existing public subnet (leave empty to create new subnet)"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (only used if creating new VPC)"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet (only used if creating new subnet)"
  type        = string
  default     = "10.0.1.0/24"
  
  validation {
    condition     = can(cidrhost(var.public_subnet_cidr, 0))
    error_message = "Public subnet CIDR must be a valid IPv4 CIDR block."
  }
}

# Security Configuration
variable "dev_workstation_cidr" {
  description = "CIDR block for developer workstation (for SSH and HTTPS access)"
  type        = string
  
  validation {
    condition     = can(cidrhost(var.dev_workstation_cidr, 0))
    error_message = "Developer workstation CIDR must be a valid IPv4 CIDR block (e.g., 203.0.113.42/32)."
  }
}

# EC2 Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
  
  validation {
    condition = contains([
      "t3.micro", "t3.small", "t3.medium", "t3.large",
      "t3a.micro", "t3a.small", "t3a.medium", "t3a.large",
      "t2.micro", "t2.small", "t2.medium", "t2.large"
    ], var.instance_type)
    error_message = "Instance type must be a valid t2, t3, or t3a instance type."
  }
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 20
  
  validation {
    condition     = var.root_volume_size >= 8 && var.root_volume_size <= 100
    error_message = "Root volume size must be between 8 and 100 GB."
  }
}

variable "postgres_volume_size" {
  description = "Size of the PostgreSQL data EBS volume in GB"
  type        = number
  default     = 50
  
  validation {
    condition     = var.postgres_volume_size >= 20 && var.postgres_volume_size <= 500
    error_message = "PostgreSQL volume size must be between 20 and 500 GB."
  }
}

# Key Pair Configuration
variable "create_key_pair" {
  description = "Whether to create a new key pair (true) or use existing one (false)"
  type        = bool
  default     = true
}

variable "public_key_content" {
  description = "Public key content for SSH access (required if create_key_pair is true)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "existing_key_pair_name" {
  description = "Name of existing key pair (required if create_key_pair is false)"
  type        = string
  default     = ""
}

# Application Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "crypto-ai.crypto-vision.com"
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\\.[a-zA-Z]{2,}$", var.domain_name))
    error_message = "Domain name must be a valid domain format."
  }
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# Feature Flags
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring for EC2 instance"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated EBS volume backups"
  type        = bool
  default     = true
}

# Cost Control
variable "enable_termination_protection" {
  description = "Enable termination protection for EC2 instance"
  type        = bool
  default     = false
}

variable "enable_stop_protection" {
  description = "Enable stop protection for EC2 instance"
  type        = bool
  default     = false
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Number of days to retain EBS volume backups"
  type        = number
  default     = 7
  
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

variable "backup_schedule" {
  description = "Cron expression for backup schedule (UTC)"
  type        = string
  default     = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
  
  validation {
    condition     = can(regex("^cron\\(", var.backup_schedule))
    error_message = "Backup schedule must be a valid cron expression starting with 'cron('."
  }
}

# Network Options
variable "use_default_vpc" {
  description = "Use default VPC if no VPC ID specified"
  type        = bool
  default     = false
}

# Security Group Options
variable "create_database_sg" {
  description = "Create separate security group for database (future RDS use)"
  type        = bool
  default     = false
}

variable "create_alb_sg" {
  description = "Create security group for Application Load Balancer (future use)"
  type        = bool
  default     = false
}

# IAM Options
variable "create_lambda_role" {
  description = "Create IAM role for Lambda functions (future use)"
  type        = bool
  default     = false
}

# Backup Notification Options
variable "enable_backup_notifications" {
  description = "Enable SNS notifications for backup events"
  type        = bool
  default     = false
}

variable "enable_backup_monitoring" {
  description = "Enable CloudWatch monitoring for backup failures"
  type        = bool
  default     = true
}
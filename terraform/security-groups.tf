# Security Groups Configuration
# Defines network security rules for the infrastructure

# Main security group for the application
resource "aws_security_group" "crypto_ai_sg" {
  name_prefix = "${var.project_name}-sg-"
  description = "Security group for Crypto AI SaaS application"
  vpc_id      = local.vpc_id
  
  # SSH access from developer workstation
  ingress {
    description = "SSH from developer workstation"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.dev_workstation_cidr]
    
    tags = {
      Name = "SSH Access"
      Type = "Management"
    }
  }
  
  # HTTPS access from developer workstation (standard port)
  ingress {
    description = "HTTPS from developer workstation"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.dev_workstation_cidr]
    
    tags = {
      Name = "HTTPS Access"
      Type = "Application"
    }
  }
  
  # Custom HTTPS port for development
  ingress {
    description = "Custom HTTPS port for development"
    from_port   = 10443
    to_port     = 10443
    protocol    = "tcp"
    cidr_blocks = [var.dev_workstation_cidr]
    
    tags = {
      Name = "Development HTTPS"
      Type = "Development"
    }
  }
  
  # HTTP redirect (optional, for SSL redirect)
  ingress {
    description = "HTTP for SSL redirect"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.dev_workstation_cidr]
    
    tags = {
      Name = "HTTP Redirect"
      Type = "Application"
    }
  }
  
  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    
    tags = {
      Name = "All Outbound"
      Type = "Outbound"
    }
  }
  
  tags = {
    Name = "${var.project_name}-security-group"
    Type = "Application Security Group"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Optional: Database security group (for future RDS migration)
resource "aws_security_group" "database_sg" {
  count = var.create_database_sg ? 1 : 0
  
  name_prefix = "${var.project_name}-db-sg-"
  description = "Security group for database access"
  vpc_id      = local.vpc_id
  
  # PostgreSQL access from application security group
  ingress {
    description     = "PostgreSQL from application"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.crypto_ai_sg.id]
    
    tags = {
      Name = "PostgreSQL Access"
      Type = "Database"
    }
  }
  
  # No outbound rules needed for database
  tags = {
    Name = "${var.project_name}-database-security-group"
    Type = "Database Security Group"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Optional: Load balancer security group (for future ALB)
resource "aws_security_group" "alb_sg" {
  count = var.create_alb_sg ? 1 : 0
  
  name_prefix = "${var.project_name}-alb-sg-"
  description = "Security group for Application Load Balancer"
  vpc_id      = local.vpc_id
  
  # HTTPS from internet
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    
    tags = {
      Name = "HTTPS Internet"
      Type = "Load Balancer"
    }
  }
  
  # HTTP from internet (for redirect)
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    
    tags = {
      Name = "HTTP Internet"
      Type = "Load Balancer"
    }
  }
  
  # Outbound to application instances
  egress {
    description     = "To application instances"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.crypto_ai_sg.id]
    
    tags = {
      Name = "To Application"
      Type = "Load Balancer"
    }
  }
  
  tags = {
    Name = "${var.project_name}-alb-security-group"
    Type = "Load Balancer Security Group"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security group rule for application to database (when using separate DB SG)
resource "aws_security_group_rule" "app_to_db" {
  count = var.create_database_sg ? 1 : 0
  
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.database_sg[0].id
  security_group_id        = aws_security_group.crypto_ai_sg.id
  description              = "Application to database access"
}

# Local values for security group references
locals {
  # Primary application security group
  app_security_group_id = aws_security_group.crypto_ai_sg.id
  
  # Database security group (if created)
  db_security_group_id = var.create_database_sg ? aws_security_group.database_sg[0].id : null
  
  # ALB security group (if created)
  alb_security_group_id = var.create_alb_sg ? aws_security_group.alb_sg[0].id : null
  
  # All security group IDs for easy reference
  security_group_ids = compact([
    aws_security_group.crypto_ai_sg.id,
    var.create_database_sg ? aws_security_group.database_sg[0].id : null,
    var.create_alb_sg ? aws_security_group.alb_sg[0].id : null
  ])
}
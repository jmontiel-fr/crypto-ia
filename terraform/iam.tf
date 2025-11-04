# IAM Configuration for EC2 Instance
# Defines roles, policies, and permissions for the application

# IAM role for EC2 instance
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = data.aws_region.current.name
          }
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-ec2-role"
    Type = "EC2 Service Role"
  }
}

# Attach AWS managed policy for SSM
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach AWS managed policy for CloudWatch Agent
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_server_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Custom policy for application-specific permissions
resource "aws_iam_policy" "app_policy" {
  name        = "${var.project_name}-app-policy"
  description = "Custom policy for Crypto Market Analysis SaaS application"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs permissions
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups"
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/${var.project_name}*"
        ]
      },
      # CloudWatch Metrics permissions
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = [
              "CWAgent",
              "AWS/EC2",
              "${var.project_name}/Application"
            ]
          }
        }
      },
      # EC2 instance metadata permissions
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeVolumes",
          "ec2:DescribeTags"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:Region" = data.aws_region.current.name
          }
        }
      },
      # SNS permissions for alerts (if using AWS SNS)
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:sns:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.project_name}-*"
      },
      # Secrets Manager permissions (for future use)
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
      # S3 permissions for model artifacts and backups (future use)
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:s3:::${var.project_name}-*",
          "arn:${data.aws_partition.current.partition}:s3:::${var.project_name}-*/*"
        ]
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-app-policy"
    Type = "Application Policy"
  }
}

# Attach custom policy to role
resource "aws_iam_role_policy_attachment" "app_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# Create instance profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
  
  tags = {
    Name = "${var.project_name}-ec2-profile"
    Type = "EC2 Instance Profile"
  }
}

# Optional: IAM policy for backup operations
resource "aws_iam_policy" "backup_policy" {
  count = var.enable_backup ? 1 : 0
  
  name        = "${var.project_name}-backup-policy"
  description = "Policy for automated backup operations"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:DeleteSnapshot",
          "ec2:DescribeSnapshots",
          "ec2:DescribeVolumes",
          "ec2:CreateTags"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:Region" = data.aws_region.current.name
          }
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-backup-policy"
    Type = "Backup Policy"
  }
}

# Attach backup policy if enabled
resource "aws_iam_role_policy_attachment" "backup_policy" {
  count = var.enable_backup ? 1 : 0
  
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.backup_policy[0].arn
}

# IAM role for future Lambda functions (optional)
resource "aws_iam_role" "lambda_role" {
  count = var.create_lambda_role ? 1 : 0
  
  name = "${var.project_name}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-lambda-role"
    Type = "Lambda Service Role"
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  count = var.create_lambda_role ? 1 : 0
  
  role       = aws_iam_role.lambda_role[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Local values for IAM references
locals {
  # EC2 role ARN
  ec2_role_arn = aws_iam_role.ec2_role.arn
  
  # Instance profile name
  instance_profile_name = aws_iam_instance_profile.ec2_profile.name
  
  # Lambda role ARN (if created)
  lambda_role_arn = var.create_lambda_role ? aws_iam_role.lambda_role[0].arn : null
}
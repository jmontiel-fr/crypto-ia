# Backup Configuration for EBS Volumes
# Implements automated backup using AWS Backup or Data Lifecycle Manager

# Data Lifecycle Manager (DLM) policy for EBS snapshots
resource "aws_dlm_lifecycle_policy" "ebs_backup" {
  count = var.enable_backup ? 1 : 0
  
  description        = "EBS backup policy for ${var.project_name}"
  execution_role_arn = aws_iam_role.dlm_lifecycle_role[0].arn
  state              = "ENABLED"
  
  policy_details {
    resource_types   = ["VOLUME"]
    target_tags = {
      Project = var.project_name
    }
    
    schedule {
      name = "${var.project_name}-daily-backup"
      
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["02:00"]  # 2 AM UTC
      }
      
      retain_rule {
        count = var.backup_retention_days
      }
      
      tags_to_add = {
        Name        = "${var.project_name}-automated-backup"
        Type        = "automated-snapshot"
        Environment = var.environment
        CreatedBy   = "dlm-lifecycle-policy"
      }
      
      copy_tags = true
    }
  }
  
  tags = {
    Name = "${var.project_name}-backup-policy"
    Type = "Backup Policy"
  }
}

# IAM role for DLM lifecycle policy
resource "aws_iam_role" "dlm_lifecycle_role" {
  count = var.enable_backup ? 1 : 0
  
  name = "${var.project_name}-dlm-lifecycle-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-dlm-lifecycle-role"
    Type = "DLM Service Role"
  }
}

# Attach AWS managed policy for DLM
resource "aws_iam_role_policy_attachment" "dlm_lifecycle_role_policy" {
  count = var.enable_backup ? 1 : 0
  
  role       = aws_iam_role.dlm_lifecycle_role[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

# SNS topic for backup notifications (optional)
resource "aws_sns_topic" "backup_notifications" {
  count = var.enable_backup && var.enable_backup_notifications ? 1 : 0
  
  name = "${var.project_name}-backup-notifications"
  
  tags = {
    Name = "${var.project_name}-backup-notifications"
    Type = "Backup Notifications"
  }
}

# SNS topic policy
resource "aws_sns_topic_policy" "backup_notifications" {
  count = var.enable_backup && var.enable_backup_notifications ? 1 : 0
  
  arn = aws_sns_topic.backup_notifications[0].arn
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.backup_notifications[0].arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# CloudWatch alarm for backup failures
resource "aws_cloudwatch_metric_alarm" "backup_failure" {
  count = var.enable_backup && var.enable_backup_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-backup-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SnapshotCreateFailure"
  namespace           = "AWS/DLM"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors backup failures for ${var.project_name}"
  alarm_actions       = var.enable_backup_notifications ? [aws_sns_topic.backup_notifications[0].arn] : []
  
  dimensions = {
    PolicyId = aws_dlm_lifecycle_policy.ebs_backup[0].id
  }
  
  tags = {
    Name = "${var.project_name}-backup-failure-alarm"
    Type = "Backup Monitoring"
  }
}

# Local values for backup references
locals {
  # Backup policy ID
  backup_policy_id = var.enable_backup ? aws_dlm_lifecycle_policy.ebs_backup[0].id : null
  
  # Backup notifications topic ARN
  backup_notifications_topic_arn = var.enable_backup && var.enable_backup_notifications ? aws_sns_topic.backup_notifications[0].arn : null
}
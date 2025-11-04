# Terraform Outputs for Crypto Market Analysis SaaS
# Define all output values from the infrastructure

# Network Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = local.vpc_id
}

output "subnet_id" {
  description = "ID of the public subnet"
  value       = local.subnet_id
}

output "security_group_id" {
  description = "ID of the security group"
  value       = local.app_security_group_id
}

# EC2 Instance Information
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.main.id
}

output "instance_type" {
  description = "Type of the EC2 instance"
  value       = aws_instance.main.instance_type
}

output "instance_state" {
  description = "Current state of the EC2 instance"
  value       = aws_instance.main.instance_state
}

output "availability_zone" {
  description = "Availability zone of the EC2 instance"
  value       = aws_instance.main.availability_zone
}

# Network Access Information
output "elastic_ip" {
  description = "Elastic IP address of the EC2 instance"
  value       = aws_eip.main.public_ip
}

output "public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.main.public_dns
}

output "private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.main.private_ip
}

# Application URLs
output "application_url" {
  description = "Main application URL"
  value       = "https://${var.domain_name}"
}

output "application_url_ip" {
  description = "Application URL using IP address"
  value       = "https://${aws_eip.main.public_ip}:10443"
}

output "streamlit_dashboard_url" {
  description = "Streamlit dashboard URL"
  value       = "https://${var.domain_name}:8501"
}

# Storage Information
output "postgres_volume_id" {
  description = "ID of the PostgreSQL data EBS volume"
  value       = aws_ebs_volume.postgres_data.id
}

output "postgres_volume_size" {
  description = "Size of the PostgreSQL data volume in GB"
  value       = aws_ebs_volume.postgres_data.size
}

output "root_volume_id" {
  description = "ID of the root EBS volume"
  value       = aws_instance.main.root_block_device[0].volume_id
}

# IAM Information
output "iam_role_name" {
  description = "Name of the IAM role for the EC2 instance"
  value       = aws_iam_role.ec2_role.name
}

output "iam_role_arn" {
  description = "ARN of the IAM role for the EC2 instance"
  value       = local.ec2_role_arn
}

output "instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = local.instance_profile_name
}

# Key Pair Information
output "key_pair_name" {
  description = "Name of the key pair used for SSH access"
  value       = var.create_key_pair ? aws_key_pair.main[0].key_name : var.existing_key_pair_name
}

# CloudWatch Information
output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app_logs.arn
}

# Connection Commands
output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.create_key_pair ? aws_key_pair.main[0].key_name : var.existing_key_pair_name}.pem ec2-user@${aws_eip.main.public_ip}"
}

output "ssm_command" {
  description = "AWS CLI command to connect via SSM Session Manager"
  value       = "aws ssm start-session --target ${aws_instance.main.id} --region ${var.aws_region}"
}

output "ec2_instance_connect_command" {
  description = "AWS CLI command to connect via EC2 Instance Connect"
  value       = "aws ec2-instance-connect send-ssh-public-key --instance-id ${aws_instance.main.id} --availability-zone ${aws_instance.main.availability_zone} --instance-os-user ec2-user --ssh-public-key file://~/.ssh/${var.create_key_pair ? aws_key_pair.main[0].key_name : var.existing_key_pair_name}.pub --region ${var.aws_region}"
}

# Deployment Information
output "deployment_info" {
  description = "Summary of deployment information"
  value = {
    project_name    = var.project_name
    environment     = var.environment
    aws_region      = var.aws_region
    instance_id     = aws_instance.main.id
    elastic_ip      = aws_eip.main.public_ip
    domain_name     = var.domain_name
    instance_type   = var.instance_type
    key_pair_name   = var.create_key_pair ? aws_key_pair.main[0].key_name : var.existing_key_pair_name
    security_group  = local.app_security_group_id
    postgres_volume = aws_ebs_volume.postgres_data.id
  }
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (USD)"
  value = {
    ec2_instance = var.instance_type == "t3.micro" ? "~$7.50" : "varies"
    ebs_storage  = "~${(var.root_volume_size + var.postgres_volume_size) * 0.10}"
    elastic_ip   = "$0 (when attached)"
    data_transfer = "~$1-5 (depending on usage)"
    cloudwatch   = "~$0.50 (basic monitoring)"
    total_estimate = var.instance_type == "t3.micro" ? "~$15-20" : "varies"
  }
}

# Security Information
output "security_summary" {
  description = "Security configuration summary"
  value = {
    ssh_access_from     = var.dev_workstation_cidr
    https_access_from   = var.dev_workstation_cidr
    encryption_at_rest  = "Enabled (EBS volumes)"
    iam_role           = aws_iam_role.ec2_role.name
    ssm_access         = "Enabled"
    cloudwatch_logs    = "Enabled"
  }
}

# Next Steps
output "next_steps" {
  description = "Next steps after Terraform deployment"
  value = [
    "1. Update DNS: Point ${var.domain_name} to ${aws_eip.main.public_ip}",
    "2. Connect to instance: ${aws_instance.main.id}",
    "3. Run deployment script: ./local-scripts/deploy-to-aws.sh",
    "4. Configure SSL certificate for ${var.domain_name}",
    "5. Test application at https://${var.domain_name}",
    "6. Monitor logs in CloudWatch: ${aws_cloudwatch_log_group.app_logs.name}"
  ]
}
#!/bin/bash
# AWS Deployment Script for Crypto Market Analysis SaaS
# Deploys the complete application to AWS EC2 instance

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
REMOTE_SCRIPTS_DIR="$PROJECT_ROOT/remote-scripts"
AWS_ENV_FILE="$PROJECT_ROOT/aws-env"
AWS_ENV_EXAMPLE="$PROJECT_ROOT/aws-env.example"

# Default values
INSTANCE_ID=""
ELASTIC_IP=""
KEY_FILE=""
REMOTE_USER="ec2-user"
REMOTE_APP_DIR="/opt/crypto-saas"
SKIP_TERRAFORM=false
SKIP_CODE_SYNC=false
SKIP_DEPENDENCIES=false
SKIP_POSTGRESQL=false
SKIP_APPLICATION=false
SKIP_SERVICES=false
DRY_RUN=false

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Print usage
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -i, --instance-id ID     EC2 instance ID (auto-detected from Terraform if not provided)"
    echo "  -e, --elastic-ip IP      Elastic IP address (auto-detected from Terraform if not provided)"
    echo "  -k, --key-file FILE      SSH private key file path"
    echo "  -u, --user USER          Remote user (default: ec2-user)"
    echo "  --skip-terraform         Skip Terraform infrastructure deployment"
    echo "  --skip-code-sync         Skip code synchronization"
    echo "  --skip-dependencies      Skip dependency installation"
    echo "  --skip-postgresql        Skip PostgreSQL setup"
    echo "  --skip-application       Skip application setup"
    echo "  --skip-services          Skip service startup"
    echo "  --dry-run                Show what would be done without executing"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0                                    # Full deployment"
    echo "  $0 --skip-terraform                  # Deploy to existing infrastructure"
    echo "  $0 -k ~/.ssh/my-key.pem              # Use specific SSH key"
    echo "  $0 --dry-run                         # Preview deployment steps"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running from project root
    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Check required tools
    local missing_tools=()
    
    if ! command -v terraform >/dev/null 2>&1; then
        missing_tools+=("terraform")
    fi
    
    if ! command -v aws >/dev/null 2>&1; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v ssh >/dev/null 2>&1; then
        missing_tools+=("ssh")
    fi
    
    if ! command -v rsync >/dev/null 2>&1; then
        missing_tools+=("rsync")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured or invalid"
        log_error "Please run 'aws configure' or set AWS environment variables"
        exit 1
    fi
    
    log "Prerequisites check passed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    if [[ "$SKIP_TERRAFORM" == true ]]; then
        log_info "Skipping Terraform deployment"
        return 0
    fi
    
    log "Deploying infrastructure with Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Check if terraform.tfvars exists
    if [[ ! -f "terraform.tfvars" ]]; then
        log_error "terraform.tfvars not found in $TERRAFORM_DIR"
        log_error "Please copy terraform.tfvars.example to terraform.tfvars and configure it"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would run: terraform plan"
        return 0
    fi
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log_info "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Apply deployment
    log_info "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Clean up plan file
    rm -f tfplan
    
    log "Infrastructure deployment completed"
    
    cd "$PROJECT_ROOT"
}

# Get deployment information from Terraform
get_terraform_outputs() {
    log "Getting deployment information from Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Get instance ID if not provided
    if [[ -z "$INSTANCE_ID" ]]; then
        INSTANCE_ID=$(terraform output -raw instance_id 2>/dev/null || echo "")
        if [[ -z "$INSTANCE_ID" ]]; then
            log_error "Could not get instance ID from Terraform outputs"
            exit 1
        fi
    fi
    
    # Get Elastic IP if not provided
    if [[ -z "$ELASTIC_IP" ]]; then
        ELASTIC_IP=$(terraform output -raw elastic_ip 2>/dev/null || echo "")
        if [[ -z "$ELASTIC_IP" ]]; then
            log_error "Could not get Elastic IP from Terraform outputs"
            exit 1
        fi
    fi
    
    # Get key pair name if key file not provided
    if [[ -z "$KEY_FILE" ]]; then
        local key_name=$(terraform output -raw key_pair_name 2>/dev/null || echo "")
        if [[ -n "$key_name" ]]; then
            KEY_FILE="$HOME/.ssh/${key_name}.pem"
            if [[ ! -f "$KEY_FILE" ]]; then
                log_warn "Key file not found at $KEY_FILE"
                log_warn "Please specify the correct key file with -k option"
            fi
        fi
    fi
    
    log "Deployment information:"
    log "  Instance ID: $INSTANCE_ID"
    log "  Elastic IP: $ELASTIC_IP"
    log "  Key File: $KEY_FILE"
    
    cd "$PROJECT_ROOT"
}

# Wait for instance to be ready
wait_for_instance() {
    log "Waiting for EC2 instance to be ready..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would wait for instance $INSTANCE_ID to be ready"
        return 0
    fi
    
    # Wait for instance to be running
    log_info "Waiting for instance to be in running state..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    
    # Wait for status checks to pass
    log_info "Waiting for status checks to pass..."
    aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID"
    
    # Wait for SSH to be available
    log_info "Waiting for SSH to be available..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
           "$REMOTE_USER@$ELASTIC_IP" "echo 'SSH connection successful'" >/dev/null 2>&1; then
            break
        fi
        
        log_info "SSH attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "SSH connection failed after $max_attempts attempts"
        exit 1
    fi
    
    log "Instance is ready for deployment"
}

# Sync application code to remote instance
sync_code() {
    if [[ "$SKIP_CODE_SYNC" == true ]]; then
        log_info "Skipping code synchronization"
        return 0
    fi
    
    log "Synchronizing application code to remote instance..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would sync code to $REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR"
        return 0
    fi
    
    # Create remote directory
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo mkdir -p $REMOTE_APP_DIR && sudo chown $REMOTE_USER:$REMOTE_USER $REMOTE_APP_DIR"
    
    # Sync application code
    rsync -avz --delete \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='venv' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='local-env' \
        --exclude='logs' \
        --exclude='models' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
        "$PROJECT_ROOT/" "$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/"
    
    # Copy AWS environment file if it exists
    if [[ -f "$AWS_ENV_FILE" ]]; then
        log_info "Copying AWS environment configuration..."
        scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
            "$AWS_ENV_FILE" "$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/.env"
    elif [[ -f "$AWS_ENV_EXAMPLE" ]]; then
        log_warn "aws-env not found, copying aws-env.example..."
        scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
            "$AWS_ENV_EXAMPLE" "$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/.env"
        log_warn "Please edit .env file on the remote instance with your configuration"
    else
        log_error "No AWS environment configuration found"
        exit 1
    fi
    
    log "Code synchronization completed"
}

# Execute remote script
execute_remote_script() {
    local script_name="$1"
    local description="$2"
    
    log "Executing remote script: $description..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would execute: $script_name"
        return 0
    fi
    
    local script_path="$REMOTE_APP_DIR/remote-scripts/$script_name"
    
    # Make script executable and run it
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "chmod +x $script_path && sudo $script_path"
    
    log "Remote script completed: $description"
}

# Install dependencies
install_dependencies() {
    if [[ "$SKIP_DEPENDENCIES" == true ]]; then
        log_info "Skipping dependency installation"
        return 0
    fi
    
    execute_remote_script "install-dependencies.sh" "Installing system dependencies"
}

# Setup PostgreSQL
setup_postgresql() {
    if [[ "$SKIP_POSTGRESQL" == true ]]; then
        log_info "Skipping PostgreSQL setup"
        return 0
    fi
    
    execute_remote_script "setup-postgresql.sh" "Setting up PostgreSQL database"
}

# Setup application
setup_application() {
    if [[ "$SKIP_APPLICATION" == true ]]; then
        log_info "Skipping application setup"
        return 0
    fi
    
    execute_remote_script "setup-application.sh" "Setting up application environment"
}

# Start services
start_services() {
    if [[ "$SKIP_SERVICES" == true ]]; then
        log_info "Skipping service startup"
        return 0
    fi
    
    execute_remote_script "start-services.sh" "Starting application services"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would verify deployment"
        return 0
    fi
    
    # Check if services are running
    log_info "Checking service status..."
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo systemctl status crypto-saas-api crypto-saas-dashboard crypto-saas-collector crypto-saas-alerts --no-pager" || true
    
    # Test API endpoint
    log_info "Testing API endpoint..."
    local api_url="https://$ELASTIC_IP/api/health"
    if curl -k -s --connect-timeout 10 "$api_url" >/dev/null 2>&1; then
        log "✓ API endpoint is responding"
    else
        log_warn "⚠ API endpoint is not responding (this may be normal during initial startup)"
    fi
    
    # Check application logs
    log_info "Checking recent application logs..."
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo journalctl -u crypto-saas-api --no-pager -n 10" || true
    
    log "Deployment verification completed"
}

# Print deployment summary
print_deployment_summary() {
    log "Deployment completed successfully!"
    echo
    log_info "Deployment Summary:"
    echo "  Instance ID: $INSTANCE_ID"
    echo "  Elastic IP: $ELASTIC_IP"
    echo "  SSH Access: ssh -i $KEY_FILE $REMOTE_USER@$ELASTIC_IP"
    echo
    log_info "Application URLs:"
    echo "  Main Application: https://$ELASTIC_IP"
    echo "  API Health Check: https://$ELASTIC_IP/api/health"
    echo "  Streamlit Dashboard: https://$ELASTIC_IP:8501"
    echo
    log_info "Service Management:"
    echo "  Check status: ./local-scripts/control-remote.sh status"
    echo "  View logs: ./local-scripts/control-remote.sh logs"
    echo "  Restart services: ./local-scripts/control-remote.sh restart"
    echo
    log_info "Next Steps:"
    echo "1. Update DNS to point your domain to $ELASTIC_IP"
    echo "2. Configure SSL certificates for your domain"
    echo "3. Test all application features"
    echo "4. Set up monitoring and alerts"
    echo
    log_warn "Remember to:"
    echo "- Configure your API keys in the .env file on the remote instance"
    echo "- Set up proper SSL certificates for production use"
    echo "- Configure backup and monitoring"
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--instance-id)
                INSTANCE_ID="$2"
                shift 2
                ;;
            -e|--elastic-ip)
                ELASTIC_IP="$2"
                shift 2
                ;;
            -k|--key-file)
                KEY_FILE="$2"
                shift 2
                ;;
            -u|--user)
                REMOTE_USER="$2"
                shift 2
                ;;
            --skip-terraform)
                SKIP_TERRAFORM=true
                shift
                ;;
            --skip-code-sync)
                SKIP_CODE_SYNC=true
                shift
                ;;
            --skip-dependencies)
                SKIP_DEPENDENCIES=true
                shift
                ;;
            --skip-postgresql)
                SKIP_POSTGRESQL=true
                shift
                ;;
            --skip-application)
                SKIP_APPLICATION=true
                shift
                ;;
            --skip-services)
                SKIP_SERVICES=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    log "Starting AWS deployment for Crypto Market Analysis SaaS"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "DRY RUN MODE - No actual changes will be made"
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Get deployment information
    get_terraform_outputs
    
    # Wait for instance to be ready
    wait_for_instance
    
    # Sync application code
    sync_code
    
    # Install dependencies
    install_dependencies
    
    # Setup PostgreSQL
    setup_postgresql
    
    # Setup application
    setup_application
    
    # Start services
    start_services
    
    # Verify deployment
    verify_deployment
    
    # Print summary
    if [[ "$DRY_RUN" != true ]]; then
        print_deployment_summary
    else
        log_info "DRY RUN completed - no actual deployment was performed"
    fi
}

# Run main function with all arguments
main "$@"
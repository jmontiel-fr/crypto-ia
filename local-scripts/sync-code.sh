#!/bin/bash
# Code Synchronization Script for Crypto Market Analysis SaaS
# Syncs only changed files to AWS EC2 instance for faster updates

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
REMOTE_USER="ec2-user"
REMOTE_APP_DIR="/opt/crypto-saas"

# Default values
INSTANCE_ID=""
ELASTIC_IP=""
KEY_FILE=""
DRY_RUN=false
RESTART_SERVICES=true
BACKUP_REMOTE=true
VERBOSE=false
EXCLUDE_PATTERNS=()

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
    echo "  --no-restart             Don't restart services after sync"
    echo "  --no-backup              Don't create backup of remote files"
    echo "  --exclude PATTERN        Additional exclude pattern for rsync"
    echo "  --dry-run                Show what would be synced without actually syncing"
    echo "  -v, --verbose            Enable verbose output"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0                                    # Sync all changes and restart services"
    echo "  $0 --no-restart                      # Sync without restarting services"
    echo "  $0 --dry-run                         # Preview what would be synced"
    echo "  $0 --exclude '*.log' --exclude 'tmp' # Exclude additional patterns"
    echo "  $0 -v                                # Verbose output"
}

# Get deployment information from Terraform
get_terraform_outputs() {
    log "Getting deployment information from Terraform..."
    
    if [[ ! -d "$TERRAFORM_DIR" ]]; then
        log_error "Terraform directory not found: $TERRAFORM_DIR"
        exit 1
    fi
    
    cd "$TERRAFORM_DIR"
    
    # Get instance ID if not provided
    if [[ -z "$INSTANCE_ID" ]]; then
        INSTANCE_ID=$(terraform output -raw instance_id 2>/dev/null || echo "")
        if [[ -z "$INSTANCE_ID" ]]; then
            log_error "Could not get instance ID from Terraform outputs"
            log_error "Please provide instance ID with -i option"
            exit 1
        fi
    fi
    
    # Get Elastic IP if not provided
    if [[ -z "$ELASTIC_IP" ]]; then
        ELASTIC_IP=$(terraform output -raw elastic_ip 2>/dev/null || echo "")
        if [[ -z "$ELASTIC_IP" ]]; then
            log_error "Could not get Elastic IP from Terraform outputs"
            log_error "Please provide Elastic IP with -e option"
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

# Check if remote instance is accessible
check_remote_access() {
    log "Checking remote instance accessibility..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would check SSH access to $REMOTE_USER@$ELASTIC_IP"
        return 0
    fi
    
    if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
         "$REMOTE_USER@$ELASTIC_IP" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_error "Cannot connect to remote instance via SSH"
        log_error "Please check:"
        log_error "  - Instance is running: aws ec2 describe-instances --instance-ids $INSTANCE_ID"
        log_error "  - Security group allows SSH from your IP"
        log_error "  - SSH key file is correct: $KEY_FILE"
        exit 1
    fi
    
    log "Remote instance is accessible"
}

# Create backup of remote files
create_remote_backup() {
    if [[ "$BACKUP_REMOTE" != true ]]; then
        log_info "Skipping remote backup"
        return 0
    fi
    
    log "Creating backup of remote files..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would create backup of remote files"
        return 0
    fi
    
    local backup_dir="/tmp/crypto-saas-backup-$(date +%Y%m%d_%H%M%S)"
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo mkdir -p $backup_dir && sudo cp -r $REMOTE_APP_DIR $backup_dir/ && echo 'Backup created at: $backup_dir'"
    
    log "Remote backup created"
}

# Get list of changed files
get_changed_files() {
    log "Analyzing changed files..."
    
    # Use git to find changed files if in a git repository
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        log_info "Using git to detect changed files..."
        
        # Get uncommitted changes
        local uncommitted=$(git -C "$PROJECT_ROOT" diff --name-only)
        
        # Get untracked files
        local untracked=$(git -C "$PROJECT_ROOT" ls-files --others --exclude-standard)
        
        # Get recently committed changes (last 10 commits)
        local recent=$(git -C "$PROJECT_ROOT" diff --name-only HEAD~10..HEAD)
        
        # Combine all changes
        local all_changes=$(echo -e "$uncommitted\n$untracked\n$recent" | sort -u | grep -v '^$')
        
        if [[ -n "$all_changes" ]]; then
            log_info "Changed files detected:"
            echo "$all_changes" | while read -r file; do
                if [[ -n "$file" ]]; then
                    log_info "  $file"
                fi
            done
        else
            log_info "No changed files detected"
        fi
    else
        log_info "Not a git repository, will sync all files"
    fi
}

# Build rsync exclude patterns
build_exclude_patterns() {
    local exclude_args=()
    
    # Default exclude patterns
    local default_excludes=(
        '.git'
        '__pycache__'
        '*.pyc'
        '*.pyo'
        '.pytest_cache'
        'venv'
        'node_modules'
        '.env'
        'local-env'
        'logs'
        'models'
        '.DS_Store'
        '*.log'
        '.vscode'
        '.idea'
        '*.swp'
        '*.swo'
        '*~'
        '.coverage'
        'htmlcov'
        'dist'
        'build'
        '*.egg-info'
        '.tox'
        '.mypy_cache'
        'terraform.tfstate*'
        'terraform.tfvars'
        '.terraform'
        'tfplan'
        'certs/local'
        'tmp'
        'temp'
    )
    
    # Add default excludes
    for pattern in "${default_excludes[@]}"; do
        exclude_args+=("--exclude=$pattern")
    done
    
    # Add custom excludes
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_args+=("--exclude=$pattern")
    done
    
    echo "${exclude_args[@]}"
}

# Sync code to remote instance
sync_code() {
    log "Synchronizing code to remote instance..."
    
    local rsync_args=(
        "-avz"
        "--delete"
        "--human-readable"
        "--progress"
    )
    
    # Add verbose flag if requested
    if [[ "$VERBOSE" == true ]]; then
        rsync_args+=("--verbose")
    fi
    
    # Add dry-run flag if requested
    if [[ "$DRY_RUN" == true ]]; then
        rsync_args+=("--dry-run")
        log_info "[DRY RUN] Showing what would be synced:"
    fi
    
    # Build exclude patterns
    local exclude_patterns
    exclude_patterns=($(build_exclude_patterns))
    
    # Add exclude patterns to rsync args
    rsync_args+=("${exclude_patterns[@]}")
    
    # Add SSH options
    rsync_args+=("-e" "ssh -i $KEY_FILE -o StrictHostKeyChecking=no")
    
    # Source and destination
    rsync_args+=("$PROJECT_ROOT/")
    rsync_args+=("$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/")
    
    # Execute rsync
    log_info "Running rsync with options: ${rsync_args[*]}"
    
    if rsync "${rsync_args[@]}"; then
        if [[ "$DRY_RUN" != true ]]; then
            log "Code synchronization completed successfully"
        else
            log_info "Dry run completed - no files were actually synced"
        fi
    else
        log_error "Code synchronization failed"
        exit 1
    fi
}

# Update environment configuration
update_environment() {
    log "Updating environment configuration..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would update environment configuration"
        return 0
    fi
    
    local aws_env_file="$PROJECT_ROOT/aws-env"
    local aws_env_example="$PROJECT_ROOT/aws-env.example"
    
    # Copy AWS environment file if it exists
    if [[ -f "$aws_env_file" ]]; then
        log_info "Updating AWS environment configuration..."
        scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
            "$aws_env_file" "$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/.env"
    elif [[ -f "$aws_env_example" ]]; then
        log_warn "aws-env not found, checking if .env exists on remote..."
        if ! ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
             "test -f $REMOTE_APP_DIR/.env"; then
            log_warn "No .env file on remote, copying aws-env.example..."
            scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
                "$aws_env_example" "$REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR/.env"
        fi
    fi
    
    log "Environment configuration updated"
}

# Install/update Python dependencies
update_dependencies() {
    log "Updating Python dependencies..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would update Python dependencies"
        return 0
    fi
    
    # Check if requirements.txt was updated
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "cd $REMOTE_APP_DIR && source venv/bin/activate && pip install -r requirements.txt"
    
    log "Python dependencies updated"
}

# Restart services
restart_services() {
    if [[ "$RESTART_SERVICES" != true ]]; then
        log_info "Skipping service restart"
        return 0
    fi
    
    log "Restarting application services..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would restart application services"
        return 0
    fi
    
    # Restart all crypto-saas services
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo systemctl restart crypto-saas-api crypto-saas-dashboard crypto-saas-collector crypto-saas-alerts crypto-saas-retention"
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    log_info "Checking service status..."
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
        "sudo systemctl status crypto-saas-api crypto-saas-dashboard --no-pager" || true
    
    log "Services restarted"
}

# Verify sync
verify_sync() {
    log "Verifying synchronization..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would verify synchronization"
        return 0
    fi
    
    # Check if main application files exist
    local files_to_check=(
        "src/api/main.py"
        "dashboard.py"
        "requirements.txt"
        ".env"
    )
    
    for file in "${files_to_check[@]}"; do
        if ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
           "test -f $REMOTE_APP_DIR/$file"; then
            log_info "✓ $file exists on remote"
        else
            log_warn "✗ $file missing on remote"
        fi
    done
    
    # Test API endpoint
    log_info "Testing API endpoint..."
    local api_url="https://$ELASTIC_IP/api/health"
    if curl -k -s --connect-timeout 10 "$api_url" >/dev/null 2>&1; then
        log "✓ API endpoint is responding"
    else
        log_warn "⚠ API endpoint is not responding (services may still be starting)"
    fi
    
    log "Synchronization verification completed"
}

# Print sync summary
print_sync_summary() {
    log "Code synchronization completed successfully!"
    echo
    log_info "Sync Summary:"
    echo "  Target: $REMOTE_USER@$ELASTIC_IP:$REMOTE_APP_DIR"
    echo "  Services restarted: $RESTART_SERVICES"
    echo "  Backup created: $BACKUP_REMOTE"
    echo
    log_info "Application URLs:"
    echo "  Main Application: https://$ELASTIC_IP"
    echo "  API Health Check: https://$ELASTIC_IP/api/health"
    echo "  Streamlit Dashboard: https://$ELASTIC_IP:8501"
    echo
    log_info "Next Steps:"
    echo "  Check logs: ./local-scripts/control-remote.sh logs"
    echo "  Check status: ./local-scripts/control-remote.sh status"
    echo "  Test application: curl -k https://$ELASTIC_IP/api/health"
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
            --no-restart)
                RESTART_SERVICES=false
                shift
                ;;
            --no-backup)
                BACKUP_REMOTE=false
                shift
                ;;
            --exclude)
                EXCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
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
    
    log "Starting code synchronization for Crypto Market Analysis SaaS"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "DRY RUN MODE - No actual changes will be made"
    fi
    
    # Check if running from project root
    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Get deployment information
    get_terraform_outputs
    
    # Check remote access
    check_remote_access
    
    # Create backup
    create_remote_backup
    
    # Analyze changed files
    get_changed_files
    
    # Sync code
    sync_code
    
    # Update environment
    update_environment
    
    # Update dependencies
    update_dependencies
    
    # Restart services
    restart_services
    
    # Verify sync
    verify_sync
    
    # Print summary
    if [[ "$DRY_RUN" != true ]]; then
        print_sync_summary
    else
        log_info "Dry run completed - no actual synchronization was performed"
    fi
}

# Run main function with all arguments
main "$@"
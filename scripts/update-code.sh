#!/bin/bash
# Universal Code Update Script
# Works for both local and remote (AWS) deployments
# Copies code to deployment directory and restarts services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (source code location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

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

# Detect environment
detect_environment() {
    if [[ -f "$SOURCE_DIR/local-env" ]]; then
        # Load local-env to get ENVIRONMENT variable
        export $(grep -v '^#' "$SOURCE_DIR/local-env" | grep ENVIRONMENT= | xargs)
        export $(grep -v '^#' "$SOURCE_DIR/local-env" | grep DEPLOYMENT_PATH= | xargs)
    elif [[ -f "$SOURCE_DIR/aws-env" ]]; then
        export $(grep -v '^#' "$SOURCE_DIR/aws-env" | grep ENVIRONMENT= | xargs)
        export $(grep -v '^#' "$SOURCE_DIR/aws-env" | grep DEPLOYMENT_PATH= | xargs)
    elif [[ -f "$SOURCE_DIR/.env" ]]; then
        export $(grep -v '^#' "$SOURCE_DIR/.env" | grep ENVIRONMENT= | xargs)
        export $(grep -v '^#' "$SOURCE_DIR/.env" | grep DEPLOYMENT_PATH= | xargs)
    fi
    
    # Default to local if not set
    ENVIRONMENT="${ENVIRONMENT:-local}"
    
    # Set deployment path based on environment
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "aws" ]]; then
        DEPLOY_PATH="${DEPLOYMENT_PATH:-/opt/crypto-saas}"
        ENV_FILE="aws-env"
    else
        DEPLOY_PATH="${DEPLOYMENT_PATH:-C:/crypto-ia}"
        ENV_FILE="local-env"
    fi
    
    log "Environment: $ENVIRONMENT"
    log "Deployment Path: $DEPLOY_PATH"
}

# Check if running with appropriate permissions
check_permissions() {
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "aws" ]]; then
        if [[ $EUID -ne 0 ]]; then
            log_error "This script must be run as root for production deployment"
            exit 1
        fi
    fi
}

# Create deployment directory
create_deploy_directory() {
    log "Creating deployment directory..."
    
    if [[ ! -d "$DEPLOY_PATH" ]]; then
        mkdir -p "$DEPLOY_PATH"
        log_info "Created directory: $DEPLOY_PATH"
    else
        log_info "Directory already exists: $DEPLOY_PATH"
    fi
    
    # Create subdirectories
    mkdir -p "$DEPLOY_PATH/logs"
    mkdir -p "$DEPLOY_PATH/certs"
    mkdir -p "$DEPLOY_PATH/models"
    mkdir -p "$DEPLOY_PATH/backups"
}

# Backup current deployment
backup_current_deployment() {
    if [[ -d "$DEPLOY_PATH/src" ]]; then
        log "Creating backup of current deployment..."
        
        local backup_dir="$DEPLOY_PATH/backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Backup critical files
        cp -r "$DEPLOY_PATH/src" "$backup_dir/" 2>/dev/null || true
        cp "$DEPLOY_PATH/.env" "$backup_dir/" 2>/dev/null || true
        cp "$DEPLOY_PATH/$ENV_FILE" "$backup_dir/" 2>/dev/null || true
        
        log_info "Backup created: $backup_dir"
        
        # Keep only last 5 backups
        cd "$DEPLOY_PATH/backups"
        ls -t | tail -n +6 | xargs -r rm -rf
    fi
}

# Copy source code
copy_source_code() {
    log "Copying source code to deployment directory..."
    
    # Files and directories to copy
    local items=(
        "src"
        "alembic"
        "scripts"
        "tests"
        "dashboard.py"
        "main.py"
        "run_api.py"
        "run_dashboard.py"
        "run_services.py"
        "health_check.py"
        "requirements.txt"
        "alembic.ini"
        "pytest.ini"
    )
    
    for item in "${items[@]}"; do
        if [[ -e "$SOURCE_DIR/$item" ]]; then
            log_info "Copying $item..."
            cp -r "$SOURCE_DIR/$item" "$DEPLOY_PATH/"
        else
            log_warn "Item not found: $item"
        fi
    done
    
    # Copy environment file if it doesn't exist in deployment
    if [[ ! -f "$DEPLOY_PATH/.env" ]] && [[ -f "$SOURCE_DIR/$ENV_FILE" ]]; then
        log_info "Copying environment file..."
        cp "$SOURCE_DIR/$ENV_FILE" "$DEPLOY_PATH/.env"
    else
        log_info "Environment file already exists in deployment, skipping"
    fi
    
    # Copy remote scripts for AWS deployment
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "aws" ]]; then
        if [[ -d "$SOURCE_DIR/remote-scripts" ]]; then
            log_info "Copying remote scripts..."
            cp -r "$SOURCE_DIR/remote-scripts" "$DEPLOY_PATH/"
        fi
    fi
}

# Setup Python virtual environment
setup_virtual_environment() {
    log "Setting up Python virtual environment..."
    
    local venv_path="$DEPLOY_PATH/venv"
    
    if [[ ! -d "$venv_path" ]]; then
        log_info "Creating new virtual environment..."
        python3 -m venv "$venv_path"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate and upgrade pip
    source "$venv_path/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install -r "$DEPLOY_PATH/requirements.txt"
    
    # Download spaCy model
    log_info "Downloading spaCy language model..."
    python -m spacy download en_core_web_sm || log_warn "spaCy model download failed"
    
    deactivate
}

# Set permissions
set_permissions() {
    log "Setting permissions..."
    
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "aws" ]]; then
        # AWS deployment - set ownership to crypto-app user
        local app_user="crypto-app"
        
        if id "$app_user" &>/dev/null; then
            chown -R "$app_user:$app_user" "$DEPLOY_PATH"
            log_info "Set ownership to $app_user"
        else
            log_warn "User $app_user does not exist, skipping ownership change"
        fi
        
        # Set appropriate permissions
        chmod -R 755 "$DEPLOY_PATH/src"
        chmod -R 755 "$DEPLOY_PATH/scripts"
        chmod 600 "$DEPLOY_PATH/.env"
        chmod -R 700 "$DEPLOY_PATH/certs"
    else
        # Local deployment - current user
        log_info "Using current user permissions"
        chmod 600 "$DEPLOY_PATH/.env" 2>/dev/null || true
    fi
}

# Restart services
restart_services() {
    log "Restarting services..."
    
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "aws" ]]; then
        # AWS deployment - use systemd
        if [[ -f "$DEPLOY_PATH/remote-scripts/restart-services.sh" ]]; then
            log_info "Restarting systemd services..."
            "$DEPLOY_PATH/remote-scripts/restart-services.sh"
        else
            log_warn "Restart script not found, skipping service restart"
        fi
    else
        # Local deployment - just notify user
        log_info "Local deployment complete"
        log_warn "Please restart your services manually:"
        echo "  1. Stop current services (Ctrl+C in terminals)"
        echo "  2. Navigate to: $DEPLOY_PATH"
        echo "  3. Activate venv: source venv/bin/activate (or venv\\Scripts\\activate on Windows)"
        echo "  4. Start API: python run_api.py"
        echo "  5. Start Dashboard: python run_dashboard.py"
    fi
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    local errors=0
    
    # Check critical files
    local critical_files=(
        "$DEPLOY_PATH/src"
        "$DEPLOY_PATH/run_api.py"
        "$DEPLOY_PATH/run_dashboard.py"
        "$DEPLOY_PATH/requirements.txt"
        "$DEPLOY_PATH/.env"
        "$DEPLOY_PATH/venv"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ -e "$file" ]]; then
            log_info "✓ $file"
        else
            log_error "✗ $file not found"
            ((errors++))
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        log "Deployment verification passed!"
        return 0
    else
        log_error "Deployment verification failed with $errors errors"
        return 1
    fi
}

# Print deployment summary
print_summary() {
    log "Deployment Summary"
    echo
    log_info "Environment: $ENVIRONMENT"
    log_info "Source: $SOURCE_DIR"
    log_info "Deployment: $DEPLOY_PATH"
    echo
    log_info "Deployment Structure:"
    echo "  $DEPLOY_PATH/"
    echo "  ├── src/              # Application code"
    echo "  ├── venv/             # Python virtual environment"
    echo "  ├── logs/             # Application logs"
    echo "  ├── certs/            # SSL certificates"
    echo "  ├── models/           # ML models"
    echo "  ├── backups/          # Code backups"
    echo "  ├── .env              # Environment configuration"
    echo "  └── run_api.py        # API entry point"
    echo
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        log_info "Next Steps (Local):"
        echo "  1. cd $DEPLOY_PATH"
        echo "  2. source venv/bin/activate (or venv\\Scripts\\activate on Windows)"
        echo "  3. python run_api.py"
        echo "  4. python run_dashboard.py (in another terminal)"
    else
        log_info "Next Steps (AWS):"
        echo "  Services should be restarting automatically"
        echo "  Check status: sudo systemctl status crypto-saas-*"
        echo "  View logs: sudo journalctl -u crypto-saas-api -f"
    fi
}

# Main execution
main() {
    log "Starting code update process..."
    echo
    
    # Detect environment
    detect_environment
    
    # Check permissions
    check_permissions
    
    # Create deployment directory
    create_deploy_directory
    
    # Backup current deployment
    backup_current_deployment
    
    # Copy source code
    copy_source_code
    
    # Setup virtual environment
    setup_virtual_environment
    
    # Set permissions
    set_permissions
    
    # Verify deployment
    if ! verify_deployment; then
        log_error "Deployment verification failed!"
        exit 1
    fi
    
    # Restart services
    restart_services
    
    # Print summary
    echo
    print_summary
    
    echo
    log "Code update completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Universal code update script for local and remote deployments"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --dry-run      Show what would be done without making changes"
        echo
        echo "Environment Detection:"
        echo "  - Reads ENVIRONMENT and DEPLOYMENT_PATH from local-env or aws-env"
        echo "  - Local: Deploys to path specified in DEPLOYMENT_PATH (default: C:/crypto-ia)"
        echo "  - AWS: Deploys to /opt/crypto-saas"
        echo
        echo "Examples:"
        echo "  $0                    # Auto-detect and deploy"
        echo "  $0 --dry-run          # Show what would be done"
        exit 0
        ;;
    --dry-run)
        log "DRY RUN MODE - No changes will be made"
        detect_environment
        echo
        log_info "Would deploy from: $SOURCE_DIR"
        log_info "Would deploy to: $DEPLOY_PATH"
        log_info "Environment: $ENVIRONMENT"
        exit 0
        ;;
    "")
        # Run main deployment
        main "$@"
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

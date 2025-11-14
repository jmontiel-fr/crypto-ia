#!/bin/bash
# Restart all Crypto Market Analysis SaaS services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Services to manage
SERVICES=(
    "postgresql-crypto"
    "crypto-saas-api"
    "crypto-saas-dashboard"
    "crypto-saas-collector"
    "crypto-saas-alerts"
    "nginx"
)

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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Restart a single service
restart_service() {
    local service=$1
    
    log "Restarting $service..."
    
    if systemctl restart "$service"; then
        log_info "✓ $service restarted successfully"
        return 0
    else
        log_error "✗ Failed to restart $service"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local service=$1
    local max_wait=30
    local count=0
    
    log_info "Waiting for $service to be ready..."
    
    while [[ $count -lt $max_wait ]]; do
        if systemctl is-active --quiet "$service"; then
            log_info "✓ $service is ready"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    log_warn "⚠ $service may not be fully ready"
    return 1
}

# Main execution
main() {
    log "Restarting all Crypto Market Analysis SaaS services"
    
    # Check if running as root
    check_root
    
    local failed_services=()
    
    # Restart services in order
    for service in "${SERVICES[@]}"; do
        if ! restart_service "$service"; then
            failed_services+=("$service")
        fi
        
        # Wait for critical services to be ready
        if [[ "$service" == "postgresql-crypto" || "$service" == "crypto-saas-api" ]]; then
            wait_for_service "$service"
        fi
    done
    
    echo
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        log "All services restarted successfully!"
    else
        log_error "Some services failed to restart:"
        for service in "${failed_services[@]}"; do
            echo "  - $service"
        done
        exit 1
    fi
    
    echo
    log_info "Service Status:"
    systemctl status "${SERVICES[@]}" --no-pager | grep -E "Active:|Loaded:" || true
    
    echo
    log_info "To view logs:"
    echo "  sudo journalctl -u crypto-saas-api -f"
    echo "  sudo journalctl -u crypto-saas-dashboard -f"
    echo "  sudo tail -f /var/log/crypto-saas/*.log"
}

# Run main function
main "$@"

#!/bin/bash
# Stop all Crypto Market Analysis SaaS services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Services to manage (in reverse order for stopping)
SERVICES=(
    "nginx"
    "crypto-saas-alerts"
    "crypto-saas-collector"
    "crypto-saas-dashboard"
    "crypto-saas-api"
    "postgresql"
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

# Stop a single service
stop_service() {
    local service=$1
    
    log "Stopping $service..."
    
    if ! systemctl is-active --quiet "$service"; then
        log_warn "$service is not running"
        return 0
    fi
    
    if systemctl stop "$service"; then
        log_info "✓ $service stopped successfully"
        return 0
    else
        log_error "✗ Failed to stop $service"
        return 1
    fi
}

# Wait for service to stop
wait_for_stop() {
    local service=$1
    local max_wait=30
    local count=0
    
    log_info "Waiting for $service to stop..."
    
    while [[ $count -lt $max_wait ]]; do
        if ! systemctl is-active --quiet "$service"; then
            log_info "✓ $service stopped"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    log_warn "⚠ $service did not stop gracefully, forcing..."
    systemctl kill "$service"
    return 1
}

# Main execution
main() {
    log "Stopping all Crypto Market Analysis SaaS services"
    
    # Check if running as root
    check_root
    
    local failed_services=()
    
    # Stop services in reverse order
    for service in "${SERVICES[@]}"; do
        if ! stop_service "$service"; then
            failed_services+=("$service")
        fi
        
        # Wait for critical services to stop
        if [[ "$service" == "crypto-saas-api" || "$service" == "postgresql" ]]; then
            wait_for_stop "$service"
        fi
    done
    
    echo
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        log "All services stopped successfully!"
    else
        log_error "Some services failed to stop:"
        for service in "${failed_services[@]}"; do
            echo "  - $service"
        done
        exit 1
    fi
    
    echo
    log_info "Service Status:"
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo "  ✗ $service: still running"
        else
            echo "  ✓ $service: stopped"
        fi
    done
}

# Run main function
main "$@"

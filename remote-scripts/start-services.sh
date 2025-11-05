#!/bin/bash
# Start all Crypto Market Analysis SaaS services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Services to manage
SERVICES=(
    "postgresql"
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

# Start a single service
start_service() {
    local service=$1
    
    log "Starting $service..."
    
    if systemctl is-active --quiet "$service"; then
        log_warn "$service is already running"
        return 0
    fi
    
    if systemctl start "$service"; then
        log_info "✓ $service started successfully"
        return 0
    else
        log_error "✗ Failed to start $service"
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

# Check service health
check_health() {
    log "Checking service health..."
    
    # Check PostgreSQL
    if systemctl is-active --quiet postgresql; then
        if sudo -u postgres psql -c "SELECT 1" >/dev/null 2>&1; then
            log_info "✓ PostgreSQL is healthy"
        else
            log_warn "⚠ PostgreSQL is running but not responding"
        fi
    fi
    
    # Check API health endpoint
    if systemctl is-active --quiet crypto-saas-api; then
        sleep 2  # Give API time to start
        if curl -s -f http://localhost:5000/health >/dev/null 2>&1; then
            log_info "✓ Flask API is healthy"
        else
            log_warn "⚠ Flask API is running but health check failed"
        fi
    fi
    
    # Check Streamlit
    if systemctl is-active --quiet crypto-saas-dashboard; then
        sleep 2  # Give Streamlit time to start
        if curl -s -f http://localhost:8501 >/dev/null 2>&1; then
            log_info "✓ Streamlit Dashboard is healthy"
        else
            log_warn "⚠ Streamlit Dashboard is running but not responding"
        fi
    fi
    
    # Check Nginx
    if systemctl is-active --quiet nginx; then
        if curl -s -f -k https://localhost/health >/dev/null 2>&1; then
            log_info "✓ Nginx is healthy"
        else
            log_warn "⚠ Nginx is running but not responding"
        fi
    fi
}

# Main execution
main() {
    log "Starting all Crypto Market Analysis SaaS services"
    
    # Check if running as root
    check_root
    
    local failed_services=()
    
    # Start services in order
    for service in "${SERVICES[@]}"; do
        if ! start_service "$service"; then
            failed_services+=("$service")
        fi
        
        # Wait for critical services to be ready
        if [[ "$service" == "postgresql" || "$service" == "crypto-saas-api" ]]; then
            wait_for_service "$service"
        fi
    done
    
    echo
    
    # Check health
    check_health
    
    echo
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        log "All services started successfully!"
    else
        log_error "Some services failed to start:"
        for service in "${failed_services[@]}"; do
            echo "  - $service"
        done
        exit 1
    fi
    
    echo
    log_info "Service Status:"
    systemctl status "${SERVICES[@]}" --no-pager | grep -E "Active:|Loaded:" || true
    
    echo
    log_info "Access Points:"
    echo "  - API: https://crypto-ai.crypto-vision.com/api"
    echo "  - Dashboard: https://crypto-ai.crypto-vision.com"
    echo "  - Chat: https://crypto-ai.crypto-vision.com/chat"
    echo
    log_info "To view logs:"
    echo "  sudo journalctl -u crypto-saas-api -f"
    echo "  sudo tail -f /var/log/crypto-saas/api.log"
}

# Run main function
main "$@"

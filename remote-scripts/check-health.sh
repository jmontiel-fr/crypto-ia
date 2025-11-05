#!/bin/bash
# Check health of all Crypto Market Analysis SaaS services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Services to check
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

# Check systemd service status
check_service_status() {
    local service=$1
    
    if systemctl is-active --quiet "$service"; then
        echo -e "  ${GREEN}✓${NC} $service: running"
        return 0
    else
        echo -e "  ${RED}✗${NC} $service: stopped"
        return 1
    fi
}

# Check PostgreSQL health
check_postgresql() {
    log_info "Checking PostgreSQL..."
    
    if systemctl is-active --quiet postgresql; then
        if sudo -u postgres psql -c "SELECT version();" >/dev/null 2>&1; then
            local version=$(sudo -u postgres psql -t -c "SELECT version();" | head -n1 | xargs)
            echo -e "  ${GREEN}✓${NC} PostgreSQL is healthy"
            echo "    Version: $version"
            
            # Check database
            if sudo -u postgres psql -d crypto_db -c "SELECT COUNT(*) FROM cryptocurrencies;" >/dev/null 2>&1; then
                local crypto_count=$(sudo -u postgres psql -t -d crypto_db -c "SELECT COUNT(*) FROM cryptocurrencies;" | xargs)
                echo "    Cryptocurrencies tracked: $crypto_count"
            fi
            
            return 0
        else
            echo -e "  ${RED}✗${NC} PostgreSQL is running but not responding"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} PostgreSQL is not running"
        return 1
    fi
}

# Check Flask API health
check_api() {
    log_info "Checking Flask API..."
    
    if systemctl is-active --quiet crypto-saas-api; then
        if curl -s -f http://localhost:5000/health >/dev/null 2>&1; then
            local response=$(curl -s http://localhost:5000/health)
            echo -e "  ${GREEN}✓${NC} Flask API is healthy"
            echo "    Response: $response"
            return 0
        else
            echo -e "  ${YELLOW}⚠${NC} Flask API is running but health check failed"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} Flask API is not running"
        return 1
    fi
}

# Check Streamlit Dashboard health
check_dashboard() {
    log_info "Checking Streamlit Dashboard..."
    
    if systemctl is-active --quiet crypto-saas-dashboard; then
        if curl -s -f http://localhost:8501 >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Streamlit Dashboard is healthy"
            return 0
        else
            echo -e "  ${YELLOW}⚠${NC} Streamlit Dashboard is running but not responding"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} Streamlit Dashboard is not running"
        return 1
    fi
}

# Check Nginx health
check_nginx() {
    log_info "Checking Nginx..."
    
    if systemctl is-active --quiet nginx; then
        if nginx -t >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Nginx configuration is valid"
        else
            echo -e "  ${YELLOW}⚠${NC} Nginx configuration has errors"
        fi
        
        if curl -s -f -k https://localhost/health >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Nginx is serving requests"
            return 0
        else
            echo -e "  ${YELLOW}⚠${NC} Nginx is running but not responding"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} Nginx is not running"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $usage -lt 80 ]]; then
        echo -e "  ${GREEN}✓${NC} Disk usage: ${usage}%"
    elif [[ $usage -lt 90 ]]; then
        echo -e "  ${YELLOW}⚠${NC} Disk usage: ${usage}% (warning)"
    else
        echo -e "  ${RED}✗${NC} Disk usage: ${usage}% (critical)"
    fi
    
    # Check log directory
    if [[ -d /var/log/crypto-saas ]]; then
        local log_size=$(du -sh /var/log/crypto-saas | cut -f1)
        echo "    Log directory size: $log_size"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."
    
    local mem_total=$(free -m | awk 'NR==2 {print $2}')
    local mem_used=$(free -m | awk 'NR==2 {print $3}')
    local mem_percent=$((mem_used * 100 / mem_total))
    
    if [[ $mem_percent -lt 80 ]]; then
        echo -e "  ${GREEN}✓${NC} Memory usage: ${mem_percent}% (${mem_used}MB / ${mem_total}MB)"
    elif [[ $mem_percent -lt 90 ]]; then
        echo -e "  ${YELLOW}⚠${NC} Memory usage: ${mem_percent}% (${mem_used}MB / ${mem_total}MB)"
    else
        echo -e "  ${RED}✗${NC} Memory usage: ${mem_percent}% (${mem_used}MB / ${mem_total}MB)"
    fi
}

# Check CPU load
check_cpu() {
    log_info "Checking CPU load..."
    
    local load=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    echo "  Load average: $load"
    
    local cpu_count=$(nproc)
    echo "  CPU cores: $cpu_count"
}

# Check recent errors in logs
check_logs() {
    log_info "Checking recent errors in logs..."
    
    local log_dir="/var/log/crypto-saas"
    
    if [[ -d "$log_dir" ]]; then
        local error_count=$(grep -i "error" "$log_dir"/*.log 2>/dev/null | tail -n 100 | wc -l)
        
        if [[ $error_count -eq 0 ]]; then
            echo -e "  ${GREEN}✓${NC} No recent errors in logs"
        elif [[ $error_count -lt 10 ]]; then
            echo -e "  ${YELLOW}⚠${NC} Found $error_count recent errors in logs"
        else
            echo -e "  ${RED}✗${NC} Found $error_count recent errors in logs"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Log directory not found"
    fi
}

# Print service uptime
check_uptime() {
    log_info "Service uptime:"
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            local uptime=$(systemctl show "$service" --property=ActiveEnterTimestamp --value)
            echo "  $service: $uptime"
        fi
    done
}

# Main execution
main() {
    log "Crypto Market Analysis SaaS - Health Check"
    echo
    
    # System information
    log_info "System Information:"
    echo "  Hostname: $(hostname)"
    echo "  OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "  Kernel: $(uname -r)"
    echo "  Uptime: $(uptime -p)"
    echo
    
    # Check service status
    log_info "Service Status:"
    local unhealthy_count=0
    for service in "${SERVICES[@]}"; do
        if ! check_service_status "$service"; then
            ((unhealthy_count++))
        fi
    done
    echo
    
    # Detailed health checks
    check_postgresql
    echo
    
    check_api
    echo
    
    check_dashboard
    echo
    
    check_nginx
    echo
    
    # System resources
    check_disk_space
    echo
    
    check_memory
    echo
    
    check_cpu
    echo
    
    # Logs
    check_logs
    echo
    
    # Uptime
    check_uptime
    echo
    
    # Summary
    if [[ $unhealthy_count -eq 0 ]]; then
        log "Overall Status: ${GREEN}HEALTHY${NC}"
        exit 0
    else
        log_error "Overall Status: ${RED}UNHEALTHY${NC} ($unhealthy_count services down)"
        exit 1
    fi
}

# Run main function
main "$@"

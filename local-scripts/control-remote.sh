#!/bin/bash
# Remote Control Script for Crypto Market Analysis SaaS
# Manages services on AWS EC2 instance from local workstation

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

# Service names
SERVICES=(
    "crypto-saas-api"
    "crypto-saas-dashboard"
    "crypto-saas-collector"
    "crypto-saas-alerts"
    "crypto-saas-retention"
)

# Default values
INSTANCE_ID=""
ELASTIC_IP=""
KEY_FILE=""
COMMAND=""
SERVICE=""
FOLLOW_LOGS=false
LOG_LINES=50

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
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Commands:"
    echo "  start [SERVICE]          Start all services or specific service"
    echo "  stop [SERVICE]           Stop all services or specific service"
    echo "  restart [SERVICE]        Restart all services or specific service"
    echo "  status [SERVICE]         Show status of all services or specific service"
    echo "  logs [SERVICE]           Show logs for all services or specific service"
    echo "  health                   Check application health"
    echo "  info                     Show system information"
    echo "  connect                  Connect to remote instance via SSH"
    echo
    echo "Services:"
    for service in "${SERVICES[@]}"; do
        echo "  ${service#crypto-saas-}"
    done
    echo
    echo "Options:"
    echo "  -i, --instance-id ID     EC2 instance ID (auto-detected from Terraform if not provided)"
    echo "  -e, --elastic-ip IP      Elastic IP address (auto-detected from Terraform if not provided)"
    echo "  -k, --key-file FILE      SSH private key file path"
    echo "  -u, --user USER          Remote user (default: ec2-user)"
    echo "  -f, --follow             Follow logs in real-time (for logs command)"
    echo "  -n, --lines NUM          Number of log lines to show (default: 50)"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0 status                            # Show status of all services"
    echo "  $0 start api                         # Start only the API service"
    echo "  $0 logs dashboard -f                 # Follow dashboard logs"
    echo "  $0 restart                           # Restart all services"
    echo "  $0 health                            # Check application health"
    echo "  $0 connect                           # SSH to remote instance"
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
    
    log_info "Connection details:"
    log_info "  Instance ID: $INSTANCE_ID"
    log_info "  Elastic IP: $ELASTIC_IP"
    log_info "  Key File: $KEY_FILE"
    
    cd "$PROJECT_ROOT"
}

# Check if remote instance is accessible
check_remote_access() {
    if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
         "$REMOTE_USER@$ELASTIC_IP" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_error "Cannot connect to remote instance via SSH"
        log_error "Please check:"
        log_error "  - Instance is running: aws ec2 describe-instances --instance-ids $INSTANCE_ID"
        log_error "  - Security group allows SSH from your IP"
        log_error "  - SSH key file is correct: $KEY_FILE"
        exit 1
    fi
}

# Execute remote command
execute_remote_command() {
    local command="$1"
    local description="$2"
    
    log_info "$description"
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" "$command"
}

# Get service name with prefix
get_service_name() {
    local service="$1"
    
    # If service already has prefix, return as-is
    if [[ "$service" == crypto-saas-* ]]; then
        echo "$service"
        return
    fi
    
    # Add prefix
    echo "crypto-saas-$service"
}

# Validate service name
validate_service() {
    local service="$1"
    local full_service_name=$(get_service_name "$service")
    
    for valid_service in "${SERVICES[@]}"; do
        if [[ "$valid_service" == "$full_service_name" ]]; then
            return 0
        fi
    done
    
    log_error "Invalid service: $service"
    log_error "Valid services: ${SERVICES[*]#crypto-saas-}"
    exit 1
}

# Start services
start_services() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        validate_service "$service"
        local full_service_name=$(get_service_name "$service")
        log "Starting service: $full_service_name"
        execute_remote_command "sudo systemctl start $full_service_name" "Starting $full_service_name..."
        execute_remote_command "sudo systemctl status $full_service_name --no-pager" "Checking status..."
    else
        log "Starting all services..."
        local services_list="${SERVICES[*]}"
        execute_remote_command "sudo systemctl start $services_list" "Starting all services..."
        execute_remote_command "sudo systemctl status ${SERVICES[*]} --no-pager" "Checking status..."
    fi
    
    log "Service start completed"
}

# Stop services
stop_services() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        validate_service "$service"
        local full_service_name=$(get_service_name "$service")
        log "Stopping service: $full_service_name"
        execute_remote_command "sudo systemctl stop $full_service_name" "Stopping $full_service_name..."
        execute_remote_command "sudo systemctl status $full_service_name --no-pager" "Checking status..."
    else
        log "Stopping all services..."
        local services_list="${SERVICES[*]}"
        execute_remote_command "sudo systemctl stop $services_list" "Stopping all services..."
        execute_remote_command "sudo systemctl status ${SERVICES[*]} --no-pager" "Checking status..."
    fi
    
    log "Service stop completed"
}

# Restart services
restart_services() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        validate_service "$service"
        local full_service_name=$(get_service_name "$service")
        log "Restarting service: $full_service_name"
        execute_remote_command "sudo systemctl restart $full_service_name" "Restarting $full_service_name..."
        sleep 3  # Give service time to start
        execute_remote_command "sudo systemctl status $full_service_name --no-pager" "Checking status..."
    else
        log "Restarting all services..."
        local services_list="${SERVICES[*]}"
        execute_remote_command "sudo systemctl restart $services_list" "Restarting all services..."
        sleep 5  # Give services time to start
        execute_remote_command "sudo systemctl status ${SERVICES[*]} --no-pager" "Checking status..."
    fi
    
    log "Service restart completed"
}

# Show service status
show_status() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        validate_service "$service"
        local full_service_name=$(get_service_name "$service")
        log "Showing status for service: $full_service_name"
        execute_remote_command "sudo systemctl status $full_service_name --no-pager -l" "Service status:"
    else
        log "Showing status for all services..."
        execute_remote_command "sudo systemctl status ${SERVICES[*]} --no-pager -l" "All services status:"
    fi
    
    # Also show process information
    log_info "Process information:"
    execute_remote_command "ps aux | grep -E '(crypto-saas|python|streamlit)' | grep -v grep" "Running processes:"
}

# Show logs
show_logs() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        validate_service "$service"
        local full_service_name=$(get_service_name "$service")
        log "Showing logs for service: $full_service_name"
        
        if [[ "$FOLLOW_LOGS" == true ]]; then
            log_info "Following logs (press Ctrl+C to stop)..."
            execute_remote_command "sudo journalctl -u $full_service_name -f" "Following logs for $full_service_name:"
        else
            execute_remote_command "sudo journalctl -u $full_service_name -n $LOG_LINES --no-pager" "Last $LOG_LINES lines for $full_service_name:"
        fi
    else
        log "Showing logs for all services..."
        
        if [[ "$FOLLOW_LOGS" == true ]]; then
            log_info "Following logs for all services (press Ctrl+C to stop)..."
            local services_list="${SERVICES[*]}"
            execute_remote_command "sudo journalctl -u ${services_list// / -u } -f" "Following logs for all services:"
        else
            for svc in "${SERVICES[@]}"; do
                log_info "=== Logs for $svc ==="
                execute_remote_command "sudo journalctl -u $svc -n $LOG_LINES --no-pager" "Last $LOG_LINES lines for $svc:"
                echo
            done
        fi
    fi
}

# Check application health
check_health() {
    log "Checking application health..."
    
    # Check system resources
    log_info "System resources:"
    execute_remote_command "free -h && df -h && uptime" "System status:"
    
    echo
    
    # Check service status
    log_info "Service status:"
    execute_remote_command "sudo systemctl is-active ${SERVICES[*]} | paste <(printf '%s\n' ${SERVICES[*]}) -" "Service status:"
    
    echo
    
    # Check API endpoints
    log_info "API health checks:"
    
    # Health endpoint
    local health_url="https://$ELASTIC_IP/api/health"
    if ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
       "curl -k -s --connect-timeout 10 '$health_url'" >/dev/null 2>&1; then
        log_info "✓ API health endpoint is responding"
    else
        log_warn "✗ API health endpoint is not responding"
    fi
    
    # Predictions endpoint
    local predictions_url="https://$ELASTIC_IP/api/predictions/top20"
    if ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
       "curl -k -s --connect-timeout 10 '$predictions_url'" >/dev/null 2>&1; then
        log_info "✓ Predictions endpoint is responding"
    else
        log_warn "✗ Predictions endpoint is not responding"
    fi
    
    # Streamlit dashboard
    local dashboard_url="http://$ELASTIC_IP:8501"
    if ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP" \
       "curl -s --connect-timeout 10 '$dashboard_url'" >/dev/null 2>&1; then
        log_info "✓ Streamlit dashboard is responding"
    else
        log_warn "✗ Streamlit dashboard is not responding"
    fi
    
    echo
    
    # Check database connection
    log_info "Database connection:"
    execute_remote_command "cd $REMOTE_APP_DIR && source venv/bin/activate && python -c \"
from src.data.database import get_session
try:
    session = get_session()
    session.execute('SELECT 1')
    session.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
\"" "Database status:"
    
    echo
    
    # Check recent errors
    log_info "Recent errors (last 10 minutes):"
    execute_remote_command "sudo journalctl -u ${SERVICES[*]// / -u } --since '10 minutes ago' --grep ERROR --no-pager | tail -10" "Recent errors:" || log_info "No recent errors found"
    
    log "Health check completed"
}

# Show system information
show_info() {
    log "Gathering system information..."
    
    # Instance information
    log_info "Instance information:"
    execute_remote_command "curl -s http://169.254.169.254/latest/meta-data/instance-id && echo" "Instance ID:"
    execute_remote_command "curl -s http://169.254.169.254/latest/meta-data/instance-type && echo" "Instance type:"
    execute_remote_command "curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone && echo" "Availability zone:"
    execute_remote_command "curl -s http://169.254.169.254/latest/meta-data/public-ipv4 && echo" "Public IP:"
    
    echo
    
    # System information
    log_info "System information:"
    execute_remote_command "uname -a" "Kernel:"
    execute_remote_command "cat /etc/os-release | grep PRETTY_NAME" "OS:"
    execute_remote_command "uptime" "Uptime:"
    execute_remote_command "free -h" "Memory:"
    execute_remote_command "df -h /" "Disk usage:"
    
    echo
    
    # Application information
    log_info "Application information:"
    execute_remote_command "cd $REMOTE_APP_DIR && ls -la" "Application directory:"
    execute_remote_command "cd $REMOTE_APP_DIR && source venv/bin/activate && python --version" "Python version:"
    execute_remote_command "cd $REMOTE_APP_DIR && test -f .env && echo 'Environment file exists' || echo 'Environment file missing'" "Environment:"
    
    echo
    
    # Network information
    log_info "Network information:"
    execute_remote_command "ss -tlnp | grep -E ':(5000|8501|443|80)'" "Listening ports:"
    
    log "System information gathered"
}

# Connect to remote instance
connect_to_remote() {
    log "Connecting to remote instance..."
    log_info "Use 'exit' to disconnect"
    
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$ELASTIC_IP"
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|health|info|connect)
                COMMAND="$1"
                shift
                # Check if next argument is a service name (not an option)
                if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
                    SERVICE="$1"
                    shift
                fi
                ;;
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
            -f|--follow)
                FOLLOW_LOGS=true
                shift
                ;;
            -n|--lines)
                LOG_LINES="$2"
                shift 2
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
    
    # Check if command was provided
    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        print_usage
        exit 1
    fi
    
    log "Remote control for Crypto Market Analysis SaaS"
    log_info "Command: $COMMAND${SERVICE:+ $SERVICE}"
    
    # Get deployment information
    get_terraform_outputs
    
    # Check remote access
    check_remote_access
    
    # Execute command
    case "$COMMAND" in
        start)
            start_services "$SERVICE"
            ;;
        stop)
            stop_services "$SERVICE"
            ;;
        restart)
            restart_services "$SERVICE"
            ;;
        status)
            show_status "$SERVICE"
            ;;
        logs)
            show_logs "$SERVICE"
            ;;
        health)
            check_health
            ;;
        info)
            show_info
            ;;
        connect)
            connect_to_remote
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            print_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
#!/bin/bash
# Database Backup Script for Crypto Market Analysis SaaS
# Creates compressed PostgreSQL backups with rotation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/data/postgresql/backups"
DB_NAME="crypto_db"
DB_USER="crypto_user"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/crypto_db_backup_$TIMESTAMP.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"  # Optional: Set S3 bucket name for cloud backups
LOG_FILE="/var/log/crypto-saas/backup.log"

# Logging functions
log() {
    local msg="${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    echo -e "$msg"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_warn() {
    local msg="${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    echo -e "$msg"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

log_error() {
    local msg="${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    echo -e "$msg"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

log_info() {
    local msg="${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
    echo -e "$msg"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}

# Check if running as root or postgres user
check_permissions() {
    if [[ $EUID -ne 0 ]] && [[ $(whoami) != "postgres" ]]; then
        log_error "This script must be run as root or postgres user"
        exit 1
    fi
}

# Create backup directory
create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        chown postgres:postgres "$BACKUP_DIR"
        chmod 700 "$BACKUP_DIR"
    fi
}

# Check PostgreSQL is running
check_postgresql() {
    log "Checking PostgreSQL status..."
    
    if ! systemctl is-active --quiet postgresql-crypto; then
        log_error "PostgreSQL is not running"
        exit 1
    fi
    
    # Test database connectivity
    if [[ $(whoami) == "postgres" ]]; then
        if ! psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
            log_error "Cannot connect to database $DB_NAME"
            exit 1
        fi
    else
        if ! su - postgres -c "psql -U $DB_USER -d $DB_NAME -c 'SELECT 1'" >/dev/null 2>&1; then
            log_error "Cannot connect to database $DB_NAME"
            exit 1
        fi
    fi
    
    log_info "✓ PostgreSQL is running and accessible"
}

# Create database backup
create_backup() {
    log "Creating database backup..."
    
    # Run pg_dump as postgres user with verbose output
    if [[ $(whoami) == "postgres" ]]; then
        if pg_dump -U "$DB_USER" -d "$DB_NAME" -F p -f "$BACKUP_FILE" --verbose 2>&1 | tee -a "$LOG_FILE"; then
            log_info "pg_dump completed successfully"
        else
            log_error "pg_dump failed"
            exit 1
        fi
    else
        if su - postgres -c "pg_dump -U $DB_USER -d $DB_NAME -F p -f $BACKUP_FILE --verbose" 2>&1 | tee -a "$LOG_FILE"; then
            log_info "pg_dump completed successfully"
        else
            log_error "pg_dump failed"
            exit 1
        fi
    fi
    
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "Backup file was not created"
        exit 1
    fi
    
    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "✓ Backup created: $BACKUP_FILE ($backup_size)"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."
    
    gzip "$BACKUP_FILE"
    
    if [[ ! -f "$COMPRESSED_FILE" ]]; then
        log_error "Compressed backup was not created"
        exit 1
    fi
    
    local compressed_size=$(du -h "$COMPRESSED_FILE" | cut -f1)
    log_info "✓ Backup compressed: $COMPRESSED_FILE ($compressed_size)"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    if gzip -t "$COMPRESSED_FILE" 2>/dev/null; then
        log_info "✓ Backup integrity verified"
        return 0
    else
        log_error "✗ Backup integrity check failed"
        return 1
    fi
}

# Upload to S3 (optional)
upload_to_s3() {
    if [[ -z "$S3_BUCKET" ]]; then
        log_info "S3 upload not configured, skipping"
        return 0
    fi
    
    log "Uploading backup to S3..."
    
    if command -v aws >/dev/null 2>&1; then
        local s3_path="s3://$S3_BUCKET/backups/$(basename $COMPRESSED_FILE)"
        
        if aws s3 cp "$COMPRESSED_FILE" "$s3_path"; then
            log_info "✓ Backup uploaded to $s3_path"
            return 0
        else
            log_warn "⚠ Failed to upload backup to S3"
            return 1
        fi
    else
        log_warn "⚠ AWS CLI not installed, skipping S3 upload"
        return 1
    fi
}

# Rotate old backups
rotate_backups() {
    log "Rotating old backups (keeping last $RETENTION_DAYS days)..."
    
    local deleted_count=0
    
    # Find and delete backups older than retention period
    while IFS= read -r old_backup; do
        if [[ -f "$old_backup" ]]; then
            rm -f "$old_backup"
            log_info "Deleted old backup: $(basename $old_backup)"
            ((deleted_count++))
        fi
    done < <(find "$BACKUP_DIR" -name "crypto_db_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS)
    
    if [[ $deleted_count -eq 0 ]]; then
        log_info "No old backups to delete"
    else
        log_info "✓ Deleted $deleted_count old backup(s)"
    fi
}

# List existing backups
list_backups() {
    log_info "Existing backups:"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count=$(find "$BACKUP_DIR" -name "crypto_db_backup_*.sql.gz" -type f | wc -l)
        
        if [[ $backup_count -eq 0 ]]; then
            echo "  No backups found"
        else
            find "$BACKUP_DIR" -name "crypto_db_backup_*.sql.gz" -type f -printf "  %p (%s bytes, %TY-%Tm-%Td %TH:%TM)\n" | sort -r
            echo "  Total: $backup_count backup(s)"
            
            local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
            echo "  Total size: $total_size"
        fi
    else
        echo "  Backup directory does not exist"
    fi
}

# Get database statistics
get_db_stats() {
    log_info "Database statistics:"
    
    if [[ $(whoami) == "postgres" ]]; then
        local db_size=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));")
        local table_count=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        local crypto_count=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM cryptocurrencies;" 2>/dev/null || echo "0")
        local price_count=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM price_history;" 2>/dev/null || echo "0")
    else
        local db_size=$(su - postgres -c "psql -U $DB_USER -d $DB_NAME -t -c \"SELECT pg_size_pretty(pg_database_size('$DB_NAME'));\"")
        local table_count=$(su - postgres -c "psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';\"")
        local crypto_count=$(su - postgres -c "psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM cryptocurrencies;\"" 2>/dev/null || echo "0")
        local price_count=$(su - postgres -c "psql -U $DB_USER -d $DB_NAME -t -c \"SELECT COUNT(*) FROM price_history;\"" 2>/dev/null || echo "0")
    fi
    
    echo "  Database size: $(echo $db_size | xargs)"
    echo "  Tables: $(echo $table_count | xargs)"
    echo "  Cryptocurrencies: $(echo $crypto_count | xargs)"
    echo "  Price records: $(echo $price_count | xargs)"
}

# Print backup summary
print_summary() {
    log "Backup completed successfully!"
    echo
    log_info "Backup Summary:"
    echo "  Backup file: $COMPRESSED_FILE"
    echo "  Backup size: $(du -h $COMPRESSED_FILE | cut -f1)"
    echo "  Timestamp: $TIMESTAMP"
    echo "  Retention: $RETENTION_DAYS days"
    echo
    list_backups
    echo
    get_db_stats
    echo
    log_info "To restore this backup:"
    echo "  gunzip -c $COMPRESSED_FILE | psql -U $DB_USER -d $DB_NAME"
}

# Send notification on failure
send_failure_notification() {
    local error_msg="$1"
    
    log_error "Backup failed: $error_msg"
    
    # Log to system log
    logger -t crypto-saas-backup "BACKUP FAILED: $error_msg"
    
    # Could integrate with alert system here
    # Example: curl -X POST http://localhost:5000/api/admin/alert -d "Backup failed: $error_msg"
}

# Main execution
main() {
    log "Starting database backup for Crypto Market Analysis SaaS"
    
    # Ensure log directory exists
    mkdir -p "$(dirname $LOG_FILE)"
    
    # Check permissions
    check_permissions
    
    # Create backup directory
    create_backup_dir
    
    # Check PostgreSQL
    if ! check_postgresql; then
        send_failure_notification "PostgreSQL check failed"
        exit 1
    fi
    
    # Create backup
    if ! create_backup; then
        send_failure_notification "Backup creation failed"
        exit 1
    fi
    
    # Compress backup
    if ! compress_backup; then
        send_failure_notification "Backup compression failed"
        exit 1
    fi
    
    # Verify backup
    if ! verify_backup; then
        send_failure_notification "Backup verification failed"
        exit 1
    fi
    
    # Upload to S3 (optional)
    upload_to_s3
    
    # Rotate old backups
    rotate_backups
    
    # Print summary
    print_summary
    
    log "Backup process completed successfully"
}

# Handle script arguments
case "${1:-}" in
    --list)
        list_backups
        exit 0
        ;;
    --stats)
        get_db_stats
        exit 0
        ;;
    --restore)
        if [[ -z "${2:-}" ]]; then
            log_error "Please specify backup file to restore"
            echo "Usage: $0 --restore <backup_file>"
            exit 1
        fi
        
        RESTORE_FILE="$2"
        if [[ ! -f "$RESTORE_FILE" ]]; then
            log_error "Backup file not found: $RESTORE_FILE"
            exit 1
        fi
        
        log_warn "WARNING: This will restore the database from backup"
        log_warn "All current data will be replaced!"
        read -p "Are you sure? (yes/no): " confirm
        
        if [[ "$confirm" != "yes" ]]; then
            log "Restore cancelled"
            exit 0
        fi
        
        log "Restoring database from $RESTORE_FILE..."
        
        if [[ "$RESTORE_FILE" == *.gz ]]; then
            gunzip -c "$RESTORE_FILE" | psql -U "$DB_USER" -d "$DB_NAME"
        else
            psql -U "$DB_USER" -d "$DB_NAME" < "$RESTORE_FILE"
        fi
        
        log "Database restored successfully"
        exit 0
        ;;
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --list              List existing backups"
        echo "  --stats             Show database statistics"
        echo "  --restore <file>    Restore database from backup file"
        echo "  --help              Show this help message"
        echo
        echo "Environment variables:"
        echo "  S3_BACKUP_BUCKET    S3 bucket name for cloud backups (optional)"
        echo
        echo "Examples:"
        echo "  $0                                    # Create backup"
        echo "  $0 --list                             # List backups"
        echo "  $0 --restore /path/to/backup.sql.gz   # Restore backup"
        exit 0
        ;;
    "")
        # Run main backup
        main "$@"
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

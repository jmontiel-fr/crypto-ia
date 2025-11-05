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
BACKUP_DIR="/var/backups/crypto-saas"
DB_NAME="crypto_db"
DB_USER="crypto_user"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/crypto_db_backup_$TIMESTAMP.sql"
COMPRESSED_FILE="$BACKUP_FILE.gz"
S3_BUCKET=""  # Optional: Set S3 bucket name for cloud backups

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
    
    if ! systemctl is-active --quiet postgresql; then
        log_error "PostgreSQL is not running"
        exit 1
    fi
    
    log_info "✓ PostgreSQL is running"
}

# Create database backup
create_backup() {
    log "Creating database backup..."
    
    # Run pg_dump as postgres user
    if [[ $(whoami) == "postgres" ]]; then
        pg_dump -U "$DB_USER" -d "$DB_NAME" -F p -f "$BACKUP_FILE"
    else
        su - postgres -c "pg_dump -U $DB_USER -d $DB_NAME -F p -f $BACKUP_FILE"
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

# Main execution
main() {
    log "Starting database backup for Crypto Market Analysis SaaS"
    
    # Check permissions
    check_permissions
    
    # Create backup directory
    create_backup_dir
    
    # Check PostgreSQL
    check_postgresql
    
    # Create backup
    create_backup
    
    # Compress backup
    compress_backup
    
    # Verify backup
    verify_backup
    
    # Upload to S3 (optional)
    upload_to_s3
    
    # Rotate old backups
    rotate_backups
    
    # Print summary
    print_summary
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
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --list    List existing backups"
        echo "  --stats   Show database statistics"
        echo "  --help    Show this help message"
        echo
        echo "Environment variables:"
        echo "  S3_BUCKET    S3 bucket name for cloud backups (optional)"
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

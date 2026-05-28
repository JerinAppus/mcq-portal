#!/bin/bash
# MCQ Battle Platform AWS S3 Backup Automation Script
# Sourced by cron to daily backup DB (SQLite or PostgreSQL) + application assets

# --- CONFIGURATION & ENV LOADING ---
ENV_FILE="/home/ubuntu/mcq-portal/.env"
LOG_DIR="/home/ubuntu/mcq-portal/logs"
BACKUP_TEMP_DIR="/tmp/mcq_backups"
RETENTION_DAYS=7

# Ensure log directory exists
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup.log"

# Function to log messages
log_msg() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
    # Also log to system syslog for centralized monitoring
    logger -t mcq-backup "[$level] $message"
}

log_msg "INFO" "Starting backup process..."

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    # Export variables so they are available to subshells
    set -a
    source "$ENV_FILE"
    set +a
    log_msg "INFO" "Loaded environment variables from $ENV_FILE"
else
    log_msg "ERROR" "Environment file $ENV_FILE not found! Aborting backup."
    exit 1
fi

# Fallback S3 Bucket name from environment variable
# Expected: S3_BACKUP_BUCKET=my-mcq-backup-bucket
if [ -z "$S3_BACKUP_BUCKET" ]; then
    log_msg "WARNING" "S3_BACKUP_BUCKET is not set in .env. Attempting fallback to S3_BUCKET."
    S3_BACKUP_BUCKET="$S3_BUCKET"
fi

if [ -z "$S3_BACKUP_BUCKET" ]; then
    log_msg "ERROR" "No AWS S3 bucket name specified in env (S3_BACKUP_BUCKET or S3_BUCKET). Aborting upload."
    exit 1
fi

# Set up timestamps and filenames
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
BACKUP_NAME="mcq_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_TEMP_DIR/$BACKUP_NAME"
mkdir -p "$BACKUP_PATH"

# --- DETECT DATABASE TYPE & EXPORT DUMP ---
# Default fallback to sqlite if database url is not provided or contains sqlite
DB_URL=${DATABASE_URL:-"sqlite:///instance/mcq_battle.db"}

log_msg "INFO" "Database URL detected: $DB_URL"

if [[ "$DB_URL" =~ ^sqlite ]]; then
    log_msg "INFO" "SQLite database detected. Copying database file..."
    
    # Extract path from URL (remove sqlite:///)
    # E.g., sqlite:///instance/mcq_battle.db -> instance/mcq_battle.db
    SQLITE_PATH=$(echo "$DB_URL" | sed 's|^sqlite:///||')
    
    # If path is relative, prefix with application root
    if [[ ! "$SQLITE_PATH" =~ ^/ ]]; then
        SQLITE_PATH="/home/ubuntu/mcq-portal/$SQLITE_PATH"
    fi
    
    if [ -f "$SQLITE_PATH" ]; then
        # Perform a secure hot copy (SQLite allows copying while open, but sqlite3 .backup is safer)
        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$SQLITE_PATH" ".timeout 5000" ".backup '$BACKUP_PATH/database_backup.sqlite'"
            DB_EXPORT_STATUS=$?
        else
            cp "$SQLITE_PATH" "$BACKUP_PATH/database_backup.sqlite"
            DB_EXPORT_STATUS=$?
        fi
        
        if [ $DB_EXPORT_STATUS -eq 0 ]; then
            log_msg "INFO" "SQLite database copied successfully."
        else
            log_msg "ERROR" "Failed to copy SQLite database!"
            exit 1
        fi
    else
        log_msg "ERROR" "SQLite database file not found at: $SQLITE_PATH"
        exit 1
    fi

elif [[ "$DB_URL" =~ ^postgres ]]; then
    log_msg "INFO" "PostgreSQL database detected. Running pg_dump..."
    
    if ! command -v pg_dump &> /dev/null; then
        log_msg "ERROR" "pg_dump utility is not installed! Cannot backup PostgreSQL database."
        exit 1
    fi
    
    # Run pg_dump directly using the full connection string
    # pg_dump can take the connection URI via -d flag
    PGPASSWORD="$DB_PASSWORD" pg_dump -d "$DB_URL" -F c -b -v -f "$BACKUP_PATH/database_backup.dump" &>> "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log_msg "INFO" "PostgreSQL database dumped successfully."
    else
        log_msg "ERROR" "PostgreSQL pg_dump failed! Check Nginx/App logs."
        exit 1
    fi
else
    log_msg "WARNING" "Unknown database engine. Skipping database backup."
fi

# --- BUNDLE MEDIA & ASSETS ---
# If application stores uploaded avatars or local JSON files, back up instance/ and frontend files
log_msg "INFO" "Archiving application directories..."
APP_INSTANCE_DIR="/home/ubuntu/mcq-portal/instance"
if [ -d "$APP_INSTANCE_DIR" ]; then
    cp -r "$APP_INSTANCE_DIR" "$BACKUP_PATH/instance_backup"
    log_msg "INFO" "Instance directory archived."
fi

# --- CREATE COMPRESSED TARBALL ---
ARCHIVE_FILE="$BACKUP_TEMP_DIR/$BACKUP_NAME.tar.gz"
log_msg "INFO" "Creating compressed archive tarball: $ARCHIVE_FILE"
tar -czf "$ARCHIVE_FILE" -C "$BACKUP_TEMP_DIR" "$BACKUP_NAME" &>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    log_msg "INFO" "Compressed tarball created successfully."
else
    log_msg "ERROR" "Failed to create compressed tarball!"
    rm -rf "$BACKUP_PATH"
    exit 1
fi

# --- UPLOAD TO AMAZON S3 ---
log_msg "INFO" "Uploading archive to Amazon S3 bucket: s3://$S3_BACKUP_BUCKET/backups/"

if ! command -v aws &> /dev/null; then
    log_msg "ERROR" "AWS CLI utility is not installed! Cannot upload backup to S3."
    rm -rf "$BACKUP_PATH" "$ARCHIVE_FILE"
    exit 1
fi

# Execute S3 upload command
aws s3 cp "$ARCHIVE_FILE" "s3://$S3_BACKUP_BUCKET/backups/$BACKUP_NAME.tar.gz" &>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    log_msg "INFO" "Backup uploaded successfully to S3!"
    UPLOAD_SUCCESS=true
else
    log_msg "ERROR" "AWS S3 upload failed!"
    UPLOAD_SUCCESS=false
fi

# --- CLEAN UP LOCAL TEMPORARY FILES ---
log_msg "INFO" "Cleaning up local temporary backup directory..."
rm -rf "$BACKUP_PATH"
rm -f "$ARCHIVE_FILE"

# Clean up older backups from /tmp/mcq_backups if any remain
find "$BACKUP_TEMP_DIR" -type f -name "mcq_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

log_msg "INFO" "Backup process finished."

if [ "$UPLOAD_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi

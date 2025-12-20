# File: scripts/backup_db.sh
#!/bin/bash
set -e

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/cashpilot_${DATE}.sql.gz"
KEEP_DAYS=30

# Load DATABASE_PUBLIC_URL from .env.backup
if [ -f .env.backup ]; then
    export $(grep -v '^#' .env.backup | xargs)
else
    echo "❌ .env.backup file not found!"
    echo "Create .env.backup with: DATABASE_PUBLIC_URL=postgresql://..."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "🔄 Starting backup at $(date)"

# Backup using public URL from environment
pg_dump "$DATABASE_PUBLIC_URL" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    if [ "$SIZE" = "20" ]; then
        echo "❌ Backup failed - file too small (likely empty)"
        exit 1
    fi
    echo "✅ Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Clean old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$KEEP_DAYS -delete
echo "🧹 Cleaned backups older than $KEEP_DAYS days"

echo ""
echo "📊 Current backups:"
ls -lht "$BACKUP_DIR" | head -n 6
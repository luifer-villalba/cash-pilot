# File: scripts/restore_db.sh
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore_db.sh <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lht backups/*.sql.gz 2>/dev/null | head -n 5
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will OVERWRITE the production database!"
echo "📁 Backup file: $BACKUP_FILE"
echo ""
read -p "Type 'RESTORE' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo ""
echo "🔄 Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | railway run psql $DATABASE_URL

echo "✅ Restore completed at $(date)"
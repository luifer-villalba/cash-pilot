# File: scripts/restore_production.sh
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore_production.sh <backup_file.sql.gz>"
    echo ""
    echo "⚠️  WARNING: This restores to RAILWAY PRODUCTION database!"
    echo "⚠️  For safe testing, use: ./scripts/restore_to_local.sh"
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

# Load DATABASE_PUBLIC_URL from .env.backup
if [ -f .env.backup ]; then
    export $(grep -v '^#' .env.backup | xargs)
else
    echo "❌ .env.backup file not found!"
    exit 1
fi

echo "⚠️⚠️⚠️  DANGER ZONE  ⚠️⚠️⚠️"
echo "This will OVERWRITE the RAILWAY PRODUCTION database!"
echo "📁 Backup file: $BACKUP_FILE"
echo "🌐 Target: Railway Production"
echo ""
echo "💡 To test safely first, use:"
echo "   ./scripts/restore_to_local.sh $BACKUP_FILE"
echo ""
read -p "Type 'RESTORE TO PRODUCTION' to confirm: " CONFIRM

if [ "$CONFIRM" != "RESTORE TO PRODUCTION" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo ""
echo "🔄 Restoring to PRODUCTION..."
gunzip -c "$BACKUP_FILE" | psql "$DATABASE_PUBLIC_URL"

echo "✅ Production restore completed at $(date)"
echo "⚠️  Verify application immediately!"
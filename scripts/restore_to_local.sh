# File: scripts/restore_to_local.sh (renamed from test_restore.sh)
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/restore_to_local.sh <backup_file.sql.gz>"
    echo ""
    echo "💡 This safely restores to LOCAL Docker database for testing"
    echo "💡 Production database is NOT affected"
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

echo "🧪 Restoring to LOCAL Docker database (safe testing)..."
echo "📁 Backup: $BACKUP_FILE"
echo "💡 Production database will NOT be affected"
echo ""

# Start local DB
echo "🔄 Starting local PostgreSQL..."
docker compose up -d db
sleep 3

# Local connection
DB_LOCAL="postgresql://cashpilot:dev_password_change_in_prod@localhost:5432/cashpilot_dev"

# Drop and recreate database
echo "🗑️  Dropping existing local database..."
docker compose exec -T db psql -U cashpilot -d postgres -c "DROP DATABASE IF EXISTS cashpilot_dev;"
docker compose exec -T db psql -U cashpilot -d postgres -c "CREATE DATABASE cashpilot_dev;"

# Restore backup
echo "🔄 Restoring backup to local..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U cashpilot -d cashpilot_dev 2>&1 | grep -v "role \"postgres\" does not exist" | grep -v "unrecognized configuration parameter"

# Verify
echo ""
echo "✅ Local restore completed!"
echo ""
echo "📊 Data verification:"
docker compose exec -T db psql -U cashpilot -d cashpilot_dev -c "
SELECT 'businesses' as table_name, COUNT(*) as records FROM businesses
UNION ALL
SELECT 'cash_sessions', COUNT(*) FROM cash_sessions
UNION ALL
SELECT 'users', COUNT(*) FROM users;
"

echo ""
echo "🌐 Start app to test restored data:"
echo "   docker compose up app"
echo "   Visit: http://localhost:8000"
echo ""
echo "💡 To restore to production (DANGEROUS):"
echo "   ./scripts/restore_production.sh $BACKUP_FILE"
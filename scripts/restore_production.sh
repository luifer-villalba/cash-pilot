#!/bin/bash
# File: scripts/restore_production.sh

set -e

echo "⚠️  CashPilot Production Restore Script"
echo "========================================"
echo ""
echo "🚨 WARNING: This will REPLACE your production database!"
echo ""

# Load environment variables from .env.backup
if [ -f .env.backup ]; then
    set -a
    source .env.backup
    set +a
else
    echo "❌ .env.backup file not found"
    echo "   Create it with: DATABASE_PUBLIC_URL=your_railway_url"
    exit 1
fi

if [ -z "$DATABASE_PUBLIC_URL" ]; then
    echo "❌ DATABASE_PUBLIC_URL not set in .env.backup"
    exit 1
fi

# Check if backup file provided
if [ -z "$1" ]; then
    BACKUP_DIR="${BACKUP_DIR:-backups}"
    echo "❌ No backup file specified"
    echo "Usage: $0 ${BACKUP_DIR}/cashpilot_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "📦 Backup file: $BACKUP_FILE"
echo "🎯 Target: PRODUCTION DATABASE"
echo ""
read -p "Type 'YES' to confirm restore to production: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo ""
echo "🧹 Dropping and recreating schema on PRODUCTION..."
psql "$DATABASE_PUBLIC_URL" <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO PUBLIC;
SQL

echo "🔄 Restoring to PRODUCTION from backup..."
gunzip -c "$BACKUP_FILE" | psql "$DATABASE_PUBLIC_URL"

echo ""
echo "🔎 Verifying production restore..."
psql "$DATABASE_PUBLIC_URL" -c "SELECT NOW() AS restore_verified_at;"

echo ""
echo "✅ Production restore complete!"
echo "⚠️  Remember to run migrations if needed: alembic upgrade head"
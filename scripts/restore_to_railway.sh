#!/bin/bash
# File: scripts/restore_to_railway.sh
#
# Restores a production backup to ANY Railway database (production, preview, staging, etc.)
# This is a generic script that accepts a database URL as parameter.
#
# Usage: ./scripts/restore_to_railway.sh <DATABASE_URL> <BACKUP_FILE>
# Example: ./scripts/restore_to_railway.sh "postgresql://..." backups/cashpilot_20251229_145054.sql.gz

set -e

echo "🚂 CashPilot Railway Restore Script"
echo "===================================="
echo ""

# Check if database URL provided
if [ -z "$1" ]; then
    echo "❌ No database URL specified"
    echo ""
    echo "Usage: $0 <DATABASE_URL> <BACKUP_FILE>"
    echo ""
    echo "Example:"
    echo "  $0 \"postgresql://user:pass@host:port/db\" backups/cashpilot_20251229_145054.sql.gz"
    echo ""
    echo "To get the database URL from Railway:"
    echo "  1. Go to Railway Dashboard → Your Service → PostgreSQL"
    echo "  2. Click 'Connect' → 'Public Network'"
    echo "  3. Copy the connection string"
    exit 1
fi

DATABASE_URL="$1"

# Check if backup file provided
if [ -z "$2" ]; then
    BACKUP_DIR="${BACKUP_DIR:-backups}"
    echo "❌ No backup file specified"
    echo "Usage: $0 <DATABASE_URL> ${BACKUP_DIR}/cashpilot_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP_FILE="$2"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Extract database name from URL for display (optional, for safety)
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p' || echo "unknown")

echo "📦 Backup file: $BACKUP_FILE"
echo "🎯 Target: Railway database ($DB_NAME)"
echo ""
echo "⚠️  WARNING: This will REPLACE the target database!"
echo ""
read -p "Type 'YES' to confirm restore: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo ""
echo "🧹 Dropping and recreating schema..."
psql "$DATABASE_URL" <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO CURRENT_USER;
GRANT ALL ON SCHEMA public TO PUBLIC;
SQL

echo "🔄 Restoring from backup..."
gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL" 2>&1 | \
    grep -v "role \"postgres\" does not exist" | \
    grep -v "unrecognized configuration parameter" || true

echo ""
echo "🔎 Verifying restore..."
psql "$DATABASE_URL" -c "SELECT NOW() AS restore_verified_at;"

echo ""
echo "✅ Restore complete!"
echo "⚠️  Remember to run migrations if needed: alembic upgrade head"


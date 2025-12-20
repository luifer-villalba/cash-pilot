#!/bin/bash
# File: scripts/restore_to_local.sh
#
# Restores a production backup to your LOCAL DOCKER database.
# Requirements: Docker Compose must be running (docker compose up -d db)
#
# Usage: ./scripts/restore_to_local.sh backups/cashpilot_20251220_161902.sql.gz

set -e

echo "🧪 CashPilot Local Restore Script"
echo "=================================="
echo ""
echo "⚠️  This script is for Docker-based development only"
echo ""

# Check if backup file provided
if [ -z "$1" ]; then
    echo "❌ No backup file specified"
    echo "Usage: $0 backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker &> /dev/null || ! command -v docker compose &> /dev/null; then
    echo "❌ Docker or Docker Compose not found"
    echo "   This script requires Docker Compose for local development"
    exit 1
fi

echo "📦 Backup file: $BACKUP_FILE"
echo "🎯 Target: Local Docker database (cashpilot_dev)"
echo ""

# Ensure Docker database is running
if ! docker compose ps db | grep -q "Up"; then
    echo "🚀 Starting local database..."
    docker compose up -d db
    echo "⏳ Waiting for database to be ready..."
    sleep 5
fi

# Stop app container to release database connections
echo "🛑 Stopping app container to release database connections..."
docker compose stop app 2>/dev/null || true

# Wait a moment for connections to close
sleep 2

# Terminate any remaining connections and drop/recreate database
echo "🧹 Dropping and recreating local database..."
docker compose exec -T db psql -U cashpilot -d postgres <<'SQL'
-- Terminate all connections to the database
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'cashpilot_dev' AND pid <> pg_backend_pid();

-- Drop and recreate
DROP DATABASE IF EXISTS cashpilot_dev;
CREATE DATABASE cashpilot_dev OWNER cashpilot;
SQL

echo "🔄 Restoring from backup..."
sleep 2 # Give database time to fully create

# Restore backup (filter out harmless warnings)
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U cashpilot -d cashpilot_dev 2>&1 | \
    grep -v "role \"postgres\" does not exist" | \
    grep -v "unrecognized configuration parameter" || true

echo ""
echo "🔎 Verifying local restore..."
docker compose exec -T db psql -U cashpilot -d cashpilot_dev -c "SELECT NOW() AS restore_verified_at;"

echo ""
echo "✅ Local restore complete!"
echo "🧪 Test your application: make run"
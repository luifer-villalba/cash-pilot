#!/bin/bash
# File: scripts/backup_production.sh

set -e

echo "🗄️  CashPilot Production Backup Script"
echo "======================================"

# Load DATABASE_PUBLIC_URL from .env.backup
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

# Create backups directory
mkdir -p backups

# Generate filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backups/cashpilot_${TIMESTAMP}.sql.gz"

echo "📦 Creating backup: $BACKUP_FILE"

# Run pg_dump and compress
pg_dump "$DATABASE_PUBLIC_URL" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    # Check file size (works on Linux and macOS)
    SIZE_BYTES=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
    SIZE_HUMAN=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')

    if [ "$SIZE_BYTES" -lt 1024 ]; then
        echo "❌ Backup failed - file too small ($SIZE_HUMAN)"
        exit 1
    fi

    echo "✅ Backup created successfully: $SIZE_HUMAN"
    echo "📁 Location: $BACKUP_FILE"
else
    echo "❌ Backup file not created"
    exit 1
fi

# Clean up old backups (keep last 30 days)
echo "🧹 Cleaning up old backups (keeping last 30 days)..."
find backups/ -name "cashpilot_*.sql.gz" -mtime +30 -delete

echo "✅ Backup complete!"
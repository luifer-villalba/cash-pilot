# File: docs/backup_restore.md
# CashPilot Database Backup & Restore

## Prerequisites

1. **Install Railway CLI:**
```bash
   npm i -g @railway/cli
```

2. **Link project:**
```bash
   railway link
   # Select: cash-pilot-production
```

3. **Login:**
```bash
   railway login
```

## Manual Backup (Weekly)

**Every Sunday:**
```bash
cd ~/projects/cash-pilot
chmod +x scripts/backup_db.sh
./scripts/backup_db.sh
```

**Output:**
```
🔄 Starting backup at Sun Dec 22 15:00:00 2024
✅ Backup created: backups/cashpilot_20241222_150000.sql.gz (2.3M)
🧹 Cleaned backups older than 30 days
```

## Restore from Backup

**List available backups:**
```bash
ls -lht backups/
```

**Restore:**
```bash
chmod +x scripts/restore_db.sh
./scripts/restore_db.sh backups/cashpilot_20241222_150000.sql.gz
```

**Confirm by typing:** `RESTORE`

## Pre-Migration Backup (MANDATORY)

**Before ANY Alembic migration:**
```bash
# 1. Backup first
./scripts/backup_db.sh

# 2. Then migrate
alembic upgrade head

# 3. If migration fails, restore
./scripts/restore_db.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

## Google Drive Sync (Optional)

**Install rclone:**
```bash
# macOS
brew install rclone

# Ubuntu/Debian
sudo apt install rclone
```

**Configure Google Drive:**
```bash
rclone config
# Choose: n (new remote)
# Name: gdrive
# Type: drive
# Follow OAuth flow
```

**Sync backups:**
```bash
rclone sync backups/ gdrive:CashPilot_Backups
```

## Automated Backup (Optional)

**macOS/Linux - Weekly cron:**
```bash
# Open crontab
crontab -e

# Add line (runs every Sunday at 3 AM)
0 3 * * 0 cd /path/to/cash-pilot && ./scripts/backup_db.sh >> logs/backup.log 2>&1
```

**Create logs directory:**
```bash
mkdir -p logs
```

## Backup Storage Strategy

- **Local retention:** 30 days (auto-cleanup)
- **Cloud sync:** Weekly to Google Drive (manual)
- **Pre-migration:** Keep separate backup before schema changes
- **Location:** `backups/` (gitignored)

## Troubleshooting

**"Railway CLI not found":**
```bash
npm i -g @railway/cli
railway login
railway link
```

**"Permission denied":**
```bash
chmod +x scripts/backup_db.sh
chmod +x scripts/restore_db.sh
```

**"No DATABASE_URL":**
```bash
# Railway CLI auto-injects DATABASE_URL
# Make sure you're in linked project
railway status
```

## Security Notes

- ✅ Backups are gitignored (never committed)
- ✅ Local backups encrypted by macOS FileVault/Linux LUKS
- ✅ Google Drive backups in private folder
- ❌ Never share backup files publicly
- ❌ Never commit `.sql` or `.sql.gz` files to Git
# File: docs/backup_restore.md
# CashPilot Database Backup & Restore

> **Note:** This guide is for Railway deployments. Adapt for your hosting provider.

## Scripts Overview

| Script | Purpose | Target | Safety |
|--------|---------|--------|--------|
| `backup_production.sh` | Create backup | Railway Production | ✅ Safe (read-only) |
| `restore_to_local.sh` | Test restore | Local Docker | ✅ Safe (isolated) |
| `restore_to_railway.sh` | Restore to any Railway DB | Any Railway environment | ⚠️ Use with caution |
| `restore_production.sh` | Emergency restore | Railway Production | ⚠️ DANGEROUS |

---

## Prerequisites

### 1. Install PostgreSQL 17 Client
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import repository key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update and install
sudo apt update
sudo apt install postgresql-client-17

# Verify
pg_dump --version  # Should show 17.x
```

### 2. Create `.env.backup` File
```bash
# Get public URL from Railway dashboard → PostgreSQL → Connect → Public Network
echo 'DATABASE_PUBLIC_URL=postgresql://postgres:PASSWORD@switchyard.proxy.rlwy.net:PORT/railway' > .env.backup
```

### 3. Add to `.gitignore`
```bash
echo '.env.backup' >> .gitignore
```

---

## Backup Production Database

### Weekly Backup (Recommended)
```bash
./scripts/backup_production.sh
```

**Output:**
```
🗄️  CashPilot Production Backup Script
======================================
📦 Creating backup: backups/cashpilot_20251220_161902.sql.gz
✅ Backup created successfully: 12K
📁 Location: backups/cashpilot_20251220_161902.sql.gz
🧹 Cleaning up old backups (keeping last 30 days)...
✅ Backup complete!
```

**Storage:**
- Location: `backups/` directory (gitignored)
- Retention: 30 days (automatic cleanup)
- Naming: `cashpilot_YYYYMMDD_HHMMSS.sql.gz`

### Pre-Migration Backup (MANDATORY)

**Before ANY Alembic migration:**
```bash
# 1. Backup first
./scripts/backup_production.sh

# 2. Verify backup succeeded (file exists and is non-empty)
ls -lh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz

# 3. Optional but recommended: test restore locally in an isolated environment
./scripts/restore_to_local.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz

# 4. Then migrate
alembic upgrade head

# 5. If migration fails, restore
./scripts/restore_production.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

---

## Testing Backups Locally

**⚠️ Docker-only:** The `restore_to_local.sh` script requires Docker Compose and won't work with native PostgreSQL installations.

**Always test backups before trusting them:**
```bash
# Restore to local Docker database
./scripts/restore_to_local.sh backups/cashpilot_20251220_161902.sql.gz
```

**Output:**
```
🧪 CashPilot Local Restore Script
==================================

⚠️  This script is for Docker-based development only

📦 Backup file: backups/cashpilot_20251220_161902.sql.gz
🎯 Target: Local Docker database (cashpilot_dev)

🛑 Stopping app container to release database connections...
🧹 Dropping and recreating local database...
🔄 Restoring from backup...
SET
SET
...
🔎 Verifying local restore...
      restore_verified_at      
-------------------------------
 2025-12-20 19:19:58.794226+00
(1 row)

✅ Local restore complete!
🧪 Test your application: make run
```

**Verify restored data:**
```bash
make run
# Visit http://localhost:8000
# Login and check data looks correct
```

### For Native PostgreSQL Users

If you're not using Docker, manually restore with:
```bash
dropdb cashpilot_dev
createdb cashpilot_dev -O cashpilot
gunzip -c backups/cashpilot_20251220_161902.sql.gz | psql cashpilot_dev
```

---

## Restore to Any Railway Database (Preview/Staging/Test)

**Use Case:** Copy production data to a preview deployment, staging environment, or test database.

**Script:** `restore_to_railway.sh`

### Get Database URL from Railway

1. Go to Railway Dashboard → Your Service → PostgreSQL
2. Click "Connect" → "Public Network"
3. Copy the connection string

### Restore Process

```bash
./scripts/restore_to_railway.sh \
  "postgresql://postgres:PASSWORD@HOST:PORT/railway" \
  backups/cashpilot_20251229_145054.sql.gz
```

**Example:**
```bash
./scripts/restore_to_railway.sh \
  "postgresql://postgres:mypass@switchyard.proxy.rlwy.net:12345/railway" \
  backups/cashpilot_20251229_145054.sql.gz
```

**What it does:**
1. Prompts for confirmation (type "YES")
2. Drops and recreates the target database schema
3. Restores the backup
4. Verifies the restore was successful

**Safety:**
- ✅ Generic script works with any Railway database
- ⚠️ Always verify you're using the correct database URL
- ⚠️ This will replace all data in the target database

---

## Restore to Production (Emergency Only)

⚠️ **DANGER ZONE** - Only use in emergencies (data loss, corruption, bad migration)

### Safety Checklist

- [ ] **Test restore locally first** using `restore_to_local.sh`
- [ ] Verify restored data looks correct
- [ ] Confirm backup file is correct
- [ ] Notify team/users of downtime
- [ ] Have recent backup ready

### Restore Process
```bash
# 1. ALWAYS test locally first
./scripts/restore_to_local.sh backups/cashpilot_20251220_160224.sql.gz

# 2. Verify data in local app
make run

# 3. Only then restore to production
./scripts/restore_production.sh backups/cashpilot_20251220_160224.sql.gz
```

**Confirmation required:**
```
⚠️  CashPilot Production Restore Script
========================================

🚨 WARNING: This will REPLACE your production database!

📦 Backup file: backups/cashpilot_20251220_160224.sql.gz
🎯 Target: PRODUCTION DATABASE

Type 'YES' to confirm restore to production:
```

**After restore:**
- Immediately verify application at your app URL
- Check critical data (businesses, sessions, users)
- Test key functionality (login, session creation)

---

## Verify Backup Contents

### Check Backup Has Data
```bash
# List tables in backup
gunzip -c backups/backup.sql.gz | grep "^COPY"

# See sample business data
gunzip -c backups/backup.sql.gz | grep -A 5 "^COPY public.businesses"

# Count lines (approximate size)
gunzip -c backups/backup.sql.gz | wc -l
```

### Expected Output
```bash
$ gunzip -c backups/backup.sql.gz | grep "^COPY"
COPY public.alembic_version (version_num) FROM stdin;
COPY public.businesses (id, name, address, phone, is_active, created_at, updated_at) FROM stdin;
COPY public.cash_sessions (...) FROM stdin;
COPY public.users (...) FROM stdin;
```

---

## Backup Schedule

### Recommended Frequency

| Trigger | When | Command |
|---------|------|---------|
| **Weekly** | Every Sunday | `./scripts/backup_production.sh` |
| **Pre-migration** | Before `alembic upgrade` | `./scripts/backup_production.sh` |
| **Pre-deployment** | Before merging to main | `./scripts/backup_production.sh` |

### Calendar Reminder

Set weekly reminder:
- **Day:** Sunday
- **Time:** 10:00 AM (or convenient time)
- **Task:** Run CashPilot backup script

---

## Google Drive Sync (Optional)

### Install rclone
```bash
# macOS
brew install rclone

# Ubuntu/Debian
sudo apt install rclone
```

### Configure Google Drive
```bash
rclone config
# Choose: n (new remote)
# Name: gdrive
# Type: drive
# Follow OAuth flow
```

### Sync Backups
```bash
# One-time sync
rclone sync backups/ gdrive:CashPilot_Backups

# Add to weekly routine
./scripts/backup_production.sh
rclone sync backups/ gdrive:CashPilot_Backups
```

---

## Troubleshooting

### "Railway CLI not found"
```bash
npm i -g @railway/cli
railway login
railway link
```

### "Permission denied"
```bash
chmod +x scripts/backup_production.sh
chmod +x scripts/restore_production.sh
chmod +x scripts/restore_to_local.sh
```

### "No DATABASE_URL"
```bash
# Make sure .env.backup exists
cat .env.backup

# Should contain:
# DATABASE_PUBLIC_URL=postgresql://...
```

### "pg_dump version mismatch"
```bash
# Install PostgreSQL 17 client (see Prerequisites)
pg_dump --version  # Must be 17.x
```

### "Backup file too small"

- Check `.env.backup` has correct DATABASE_PUBLIC_URL
- Verify Railway database is accessible
- Check network connection

### "Database is being accessed by other users" (Local Restore)

The `restore_to_local.sh` script automatically handles this by:
1. Stopping the app container
2. Terminating active connections
3. Dropping and recreating the database

If issues persist, manually stop all containers:
```bash
docker compose down
docker compose up -d db
./scripts/restore_to_local.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

---

## Security Notes

- ✅ Backups are gitignored (never committed)
- ✅ `.env.backup` is gitignored (credentials protected)
- ✅ Local backups encrypted by OS (FileVault/LUKS)
- ✅ Google Drive backups in private folder
- ❌ Never share backup files publicly
- ❌ Never commit `.sql` or `.sql.gz` files to Git
- ❌ Never share `.env.backup` file

---

## Why Manual Backups?

Railway Hobby plan ($0/month) does not include automated backups. Options:

1. **Manual backups** (current solution) - Free, requires discipline
2. **Railway Pro** ($20/month) - Includes automated daily backups
3. **GitHub Actions** - Automated cloud backups (more complex setup)

For a portfolio project, manual backups are appropriate. For production revenue-generating systems, consider Railway Pro plan for automated backups.

---

## Related Commands
```bash
# List all backups
ls -lht backups/

# Delete specific backup
rm backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz

# Delete old backups manually (>30 days)
find backups/ -name "*.sql.gz" -mtime +30 -delete

# Check backup file size
ls -lh backups/cashpilot_20251220_160224.sql.gz
```
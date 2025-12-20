# File: docs/backup_restore.md
# CashPilot Database Backup & Restore

> **Note:** This guide is for Railway deployments. Adapt for your hosting provider.

## Scripts Overview

| Script | Purpose | Target | Safety |
|--------|---------|--------|--------|
| `backup_production.sh` | Create backup | Railway Production | ✅ Safe (read-only) |
| `restore_to_local.sh` | Test restore | Local Docker | ✅ Safe (isolated) |
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
🔄 Starting backup at Sat Dec 20 16:02:24 -03 2025
✅ Backup created: backups/cashpilot_20251220_160224.sql.gz (12K)
🧹 Cleaned backups older than 30 days
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

# 2. Then migrate
alembic upgrade head

# 3. If migration fails, restore
./scripts/restore_production.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

---

## Test Restore Locally (Safe)

**Always test backups before trusting them:**
```bash
# Restore to local Docker database
./scripts/restore_to_local.sh backups/cashpilot_20251220_160224.sql.gz
```

**Output:**
```
🧪 Restoring to LOCAL Docker database (safe testing)...
📁 Backup: backups/cashpilot_20251220_160224.sql.gz
💡 Production database will NOT be affected

🔄 Starting local PostgreSQL...
🗑️  Dropping existing local database...
🔄 Restoring backup to local...
✅ Local restore completed!

📊 Data verification:
  table_name   | records 
---------------+---------
 businesses    |       5
 cash_sessions |      76
 users         |      15

🌐 Start app to test restored data:
   docker compose up app
   Visit: http://localhost:8000
```

**Verify restored data:**
```bash
docker compose up app
# Visit http://localhost:8000
# Login and check data looks correct
```

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
docker compose up app

# 3. Only then restore to production
./scripts/restore_production.sh backups/cashpilot_20251220_160224.sql.gz
```

**Confirmation required:**
```
⚠️⚠️⚠️  DANGER ZONE  ⚠️⚠️⚠️
This will OVERWRITE the RAILWAY PRODUCTION database!
📁 Backup file: backups/cashpilot_20251220_160224.sql.gz
🌐 Target: Railway Production

Type 'RESTORE TO PRODUCTION' to confirm:
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

### "Backup file too small (20 bytes)"

- Check `.env.backup` has correct DATABASE_PUBLIC_URL
- Verify Railway database is accessible
- Check network connection

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
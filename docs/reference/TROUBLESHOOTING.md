# Troubleshooting Guide — CashPilot

> 📚 Reference Document  
> This guide helps diagnose and fix common issues in CashPilot.

## Purpose

Provide solutions to common problems encountered during development, deployment, and operation of CashPilot.

---

## Table of Contents

1. [Development Environment Issues](#development-environment-issues)
2. [Database Issues](#database-issues)
3. [Authentication & RBAC Issues](#authentication--rbac-issues)
4. [Cash Session Issues](#cash-session-issues)
5. [Reporting Issues](#reporting-issues)
6. [Performance Issues](#performance-issues)
7. [Deployment Issues](#deployment-issues)
8. [Legacy Browser Issues](#legacy-browser-issues)

---

## Development Environment Issues

### Docker Container Won't Start

**Symptoms:** `docker compose up` fails or containers exit immediately

**Solutions:**

1. **Check logs:**
   ```bash
   docker compose logs app
   docker compose logs db
   ```

2. **Port conflicts:**
   ```bash
   # Check if port 8000 is in use
   sudo lsof -ti:8000
   
   # Kill process or change port in docker-compose.yml
   ```

3. **Permission issues:**
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER .
   ```

4. **Rebuild containers:**
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

### Hot Reload Not Working

**Symptoms:** Code changes don't reflect in running application

**Solutions:**

1. **Verify development mode:**
   ```bash
   # Check if ENVIRONMENT=development in .env
   grep ENVIRONMENT .env
   ```

2. **Restart application:**
   ```bash
   docker compose restart app
   ```

3. **Check volume mounts:**
   ```bash
   # Verify volumes in docker-compose.yml
   docker compose config
   ```

### Imports Not Found

**Symptoms:** `ModuleNotFoundError` when running code

**Solutions:**

1. **Rebuild container:**
   ```bash
   docker compose build app
   ```

2. **Check Python path:**
   ```bash
   docker compose exec app python -c "import sys; print(sys.path)"
   ```

3. **Reinstall dependencies:**
   ```bash
   docker compose exec app pip install -e .
   ```

---

## Database Issues

### Cannot Connect to Database

**Symptoms:** `FATAL: password authentication failed` or connection refused

**Solutions:**

1. **Verify DATABASE_URL:**
   ```bash
   docker compose exec app env | grep DATABASE_URL
   ```

2. **Check database container:**
   ```bash
   docker compose ps db
   docker compose logs db
   ```

3. **Reset database:**
   ```bash
   docker compose down
   docker volume rm cash-pilot_postgres_data
   docker compose up -d
   make migrate
   ```

### Migration Conflicts

**Symptoms:** `FAILED: Multiple head revisions are present` or `Can't locate revision`

**Solutions:**

1. **Check migration state:**
   ```bash
   docker compose exec app alembic current
   docker compose exec app alembic history
   ```

2. **Merge heads:**
   ```bash
   docker compose exec app alembic merge heads -m "merge migrations"
   docker compose exec app alembic upgrade head
   ```

3. **Reset migrations (CAUTION: Development only):**
   ```bash
   # Backup data first!
   docker compose exec app alembic downgrade base
   docker compose exec app alembic upgrade head
   ```

### Data Integrity Errors

**Symptoms:** `IntegrityError`, `UNIQUE constraint failed`, or foreign key violations

**Solutions:**

1. **Check constraints:**
   ```sql
   -- Connect to database
   docker compose exec db psql -U cashpilot_user -d cashpilot
   
   -- List constraints
   SELECT * FROM information_schema.table_constraints 
   WHERE table_name = 'your_table';
   ```

2. **Fix data manually:**
   ```bash
   docker compose exec db psql -U cashpilot_user -d cashpilot
   
   -- Run corrective SQL
   UPDATE cash_sessions SET ... WHERE ...;
   ```

3. **Create data migration:**
   ```bash
   # Create empty migration
   docker compose exec app alembic revision -m "fix data integrity"
   
   # Edit migration file to include data fixes
   ```

---

## Authentication & RBAC Issues

### User Cannot Log In

**Symptoms:** "Invalid credentials" error with correct password

**Solutions:**

1. **Verify user exists:**
   ```bash
   docker compose exec db psql -U cashpilot_user -d cashpilot \
     -c "SELECT id, email, is_active FROM users WHERE email = 'user@example.com';"
   ```

2. **Check if account is active:**
   ```sql
   -- User must have is_active = true
   UPDATE users SET is_active = true WHERE email = 'user@example.com';
   ```

3. **Reset password:**
   ```bash
   docker compose exec app python src/cashpilot/scripts/createuser.py \
     --email user@example.com --reset-password
   ```

### Session Expires Too Quickly

**Symptoms:** User logged out unexpectedly

**Solutions:**

1. **Check session timeout settings** in `src/cashpilot/core/config.py`:
   - Admin: 2 hours
   - Cashier: 10 hours

2. **Verify session storage:**
   ```bash
   # Check if sessions are being persisted
   docker compose logs app | grep "session"
   ```

### Cashier Can Access Admin Features

**Symptoms:** RBAC bypass, unauthorized access

**Solutions:**

1. **Verify role:**
   ```sql
   SELECT id, email, role FROM users WHERE email = 'user@example.com';
   -- Role should be 'CASHIER', not 'ADMIN'
   ```

2. **Check RBAC dependencies** in route definitions:
   ```python
   # Should have require_admin() or require_cashier() dependency
   @router.get("/admin/...")
   async def admin_route(user = Depends(require_admin)):
       ...
   ```

3. **Clear browser cache:**
   ```bash
   # Old session data might be cached
   # User should log out and log back in
   ```

### Cashier Cannot Access Assigned Business

**Symptoms:** "Access denied" to business they should access

**Solutions:**

1. **Verify business assignment:**
   ```sql
   SELECT ub.*, u.email, b.name 
   FROM user_businesses ub
   JOIN users u ON ub.user_id = u.id
   JOIN businesses b ON ub.business_id = b.id
   WHERE u.email = 'cashier@example.com';
   ```

2. **Assign business:**
   ```bash
   docker compose exec app python -c "
   from cashpilot.scripts.assign_cashiers import assign_user_to_business
   assign_user_to_business('user-uuid', 'business-uuid')
   "
   ```

3. **Check database transaction commit:**
   ```python
   # Ensure session.commit() is called after assignment
   ```

---

## Cash Session Issues

### Cannot Open Multiple Sessions

**Symptoms:** "Session already open" error

**Solutions:**

1. **Close existing session:**
   ```sql
   UPDATE cash_sessions 
   SET status = 'closed', closed_at = NOW() 
   WHERE cashier_id = 'user-uuid' AND status = 'open';
   ```

2. **Check business rules:**
   - Only one open session per cashier+business is allowed
   - Verify this is intentional behavior

### Reconciliation Totals Don't Match

**Symptoms:** Discrepancies between expected and calculated totals

**Solutions:**

1. **Verify calculation logic** in `src/cashpilot/api/cash_session_edit.py`:
   ```python
   # cash_sales = (final_cash + envelope) - initial_cash
   ```

2. **Check for missing line items:**
   ```sql
   SELECT * FROM expense_items WHERE session_id = 'session-uuid';
   SELECT * FROM transfer_items WHERE session_id = 'session-uuid';
   ```

3. **Recalculate manually:**
   ```python
   # Use Python shell to recalculate
   docker compose exec app python
   
   from cashpilot.models import CashSession
   session = # ... fetch session
   # Manually calculate and compare
   ```

### Audit Log Missing Entries

**Symptoms:** Edit history not recorded

**Solutions:**

1. **Verify audit middleware** is registered in `src/cashpilot/main.py`

2. **Check audit fields:**
   ```sql
   SELECT * FROM cash_session_audit_logs 
   WHERE session_id = 'session-uuid' 
   ORDER BY timestamp DESC;
   ```

3. **Ensure audit logging is triggered:**
   ```python
   # Must call audit logging function after edits
   create_audit_log(session_id, user, action, ...)
   ```

---

## Reporting Issues

### Weekly Trend Report Shows Incorrect Data

**Symptoms:** Wrong totals or missing days

**Solutions:**

1. **Clear cache:**
   ```bash
   # Reports are cached for performance
   # Force refresh by clearing cache keys
   docker compose exec app python -c "
   from cashpilot.core.cache import cache
   cache.delete_pattern('weekly_trend_*')
   "
   ```

2. **Verify date range:**
   ```python
   # Check week boundaries for correct business day logic
   # Week starts Monday, ends Sunday
   ```

3. **Check timezone:**
   ```python
   # All dates must be in America/Asuncion timezone
   from cashpilot.utils.timezone import get_business_timezone
   ```

### PDF Export Fails

**Symptoms:** 500 error or blank PDF

**Solutions:**

1. **Check WeasyPrint installation:**
   ```bash
   docker compose exec app python -c "import weasyprint"
   ```

2. **Verify template rendering:**
   ```bash
   # Test HTML generation first
   curl http://localhost:8000/reports/weekly-trend?business_id=...
   ```

3. **Check logs for CSS/font errors:**
   ```bash
   docker compose logs app | grep -i weasyprint
   ```

### Daily Reconciliation Not Auto-Refreshing

**Symptoms:** HTMX polling not working

**Solutions:**

1. **Check HTMX attribute:**
   ```html
   <!-- Must have hx-trigger="load, every 45s" -->
   <div hx-get="/admin/reconciliation/..." 
        hx-trigger="load, every 45s" 
        hx-swap="outerHTML">
   ```

2. **Verify browser compatibility:**
   ```javascript
   // HTMX 1.9.10 should work on IE11
   // Check console for errors
   ```

3. **Test manually:**
   ```bash
   # Hit endpoint directly
   curl http://localhost:8000/admin/reconciliation/business-id/2026-02-15
   ```

---

## Performance Issues

### Slow Page Loads

**Symptoms:** Dashboard takes >5 seconds to load

**Solutions:**

1. **Check database queries:**
   ```bash
   # Enable query logging
   docker compose logs app | grep "SELECT"
   ```

2. **Add database indexes:**
   ```sql
   CREATE INDEX idx_sessions_business_date 
   ON cash_sessions(business_id, opened_at);
   ```

3. **Profile slow queries:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM cash_sessions WHERE ...;
   ```

4. **Implement pagination:**
   ```python
   # Limit results
   sessions = query.limit(50).offset((page - 1) * 50)
   ```

### High Memory Usage

**Symptoms:** Container using >2GB RAM

**Solutions:**

1. **Check for memory leaks:**
   ```bash
   docker stats cash-pilot-app-1
   ```

2. **Limit query result sizes:**
   ```python
   # Don't load all sessions at once
   # Use pagination and eager loading
   ```

3. **Adjust connection pool:**
   ```python
   # In database configuration
   pool_size=5, max_overflow=10
   ```

---

## Deployment Issues

### Railway Build Fails

**Symptoms:** Deployment fails during build

**Solutions:**

1. **Check build logs** in Railway dashboard

2. **Verify Dockerfile:**
   ```bash
   # Test build locally
   docker build -t cashpilot:test .
   ```

3. **Check dependency versions:**
   ```bash
   # Ensure pyproject.toml has correct versions
   cat pyproject.toml | grep -A 20 "\[project.dependencies\]"
   ```

### Database Migration Fails in Production

**Symptoms:** Alembic errors during deployment

**Solutions:**

1. **Backup database first:**
   ```bash
   ./scripts/backup_production.sh
   ```

2. **Run migration manually:**
   ```bash
   # SSH into Railway or use CLI
   railway run alembic upgrade head
   ```

3. **Rollback if needed:**
   ```bash
   railway run alembic downgrade -1
   ```

### Static Files Not Loading

**Symptoms:** CSS/JS returns 404

**Solutions:**

1. **Check static file mounting:**
   ```python
   # In main.py
   app.mount("/static", StaticFiles(directory="static"), name="static")
   ```

2. **Verify file paths:**
   ```bash
   # Files should be in static/ directory
   ls -la static/css/
   ```

3. **Check CDN/proxy settings:**
   ```nginx
   # If using reverse proxy
   location /static/ {
       alias /app/static/;
   }
   ```

---

## Legacy Browser Issues

### JavaScript Not Working on Windows 7

**Symptoms:** Functionality broken on IE11 or Chrome 50

**Solutions:**

1. **Verify polyfills loaded:**
   ```html
   <!-- Check templates/base.html for polyfills -->
   <script>/* Polyfills for Promise, fetch, etc. */</script>
   ```

2. **Check console errors:**
   ```javascript
   // Use IE11 Developer Tools to see errors
   // Common issue: ES6 arrow functions, template literals
   ```

3. **Test compatibility:**
   ```bash
   # Use BrowserStack or similar
   # Or test on real Windows 7 VM
   ```

4. **Review compatibility guide:**
   - See [Windows 7 Compatibility Guide](w7-compatibility.md)

### CSS Not Rendering Correctly

**Symptoms:** Layout broken on legacy browsers

**Solutions:**

1. **Check CSS fallbacks:**
   ```css
   /* Must have fallbacks for CSS variables */
   color: var(--color-primary, #3b82f6);
   ```

2. **Verify PostCSS autoprefixer:**
   ```bash
   # Check if vendor prefixes are added
   cat static/css/output.css | grep -E "(-webkit-|-moz-)"
   ```

3. **Test @supports blocks:**
   ```css
   /* Fallbacks for unsupported features */
   @supports not (backdrop-filter: blur(1px)) {
       background-color: rgba(255, 255, 255, 0.95) !important;
   }
   ```

---

## Getting Help

If you can't resolve an issue:

1. **Search documentation:**
   - Check `docs/` directory
   - Review [Architecture docs](../architecture/ARCHITECTURE.md)

2. **Check existing issues:**
   - Search GitHub issues
   - Look for similar problems

3. **Enable debug logging:**
   ```python
   # In config.py
   LOGGING_LEVEL = "DEBUG"
   ```

4. **Create detailed bug report:**
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs and error messages
   - Environment details

5. **Contact maintainers:**
   - Open GitHub issue
   - Include relevant context

---

## Related Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) - Setup guide
- [API.md](API.md) - API reference
- [w7-compatibility.md](w7-compatibility.md) - Legacy browser support
- [backup_restore.md](../runbooks/backup_restore.md) - Database operations
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System architecture

# 💰 CashPilot

Business cash register reconciliation system built for multi-location operations. Replaces manual paper-based daily reconciliation with automated session tracking, multi-payment support, and role-based access control.

**Live:** https://cash-pilot-production.up.railway.app

---

## What It Does

**Problem:** Business managers spend 30+ minutes daily reconciling cash by hand, tracking payments across cash/card/transfers, and managing discrepancies in spreadsheets.

**Solution:** 
- Cashiers open a shift with initial cash → track payments throughout day → close with auto-reconciliation
- System flags discrepancies instantly (short 15,000₲? it tells you)
- Admins manage users, assign them to business locations, reset passwords
- Complete audit trail of every edit (who changed what, when, why)
- Requires an internet connection; offline mode is not currently supported

---

## Built With

**Backend:** FastAPI • SQLAlchemy 2.0 async • PostgreSQL • asyncpg  
**Frontend:** Jinja2 templates • Tailwind CSS • DaisyUI • HTMX pagination  
**DevOps:** Docker • Alembic migrations • Railway deployment • GitHub auto-deploy  
**Testing:** pytest • 167+ async tests • RBAC coverage  
**i18n:** Spanish/English (Babel)

---

## Getting Started
```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot

# Create .env file (see docker-compose.yml for required variables)
# Required: DATABASE_URL, SESSION_SECRET_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

# All commands via Makefile
make build              # Build containers
make up                 # Start services
make migrate            # Run migrations
make seed               # Create demo data (3 businesses, 87 sessions)
make test               # Run 167+ tests
make logs               # View live logs

# Visit http://localhost:8000
# Login: admin@example.com / password123 (from seed)
```

---

## Feature Walkthrough

**Dashboard**
- Paginated session list with date, business, cashier, reconciliation status
- Filter by date range, cashier, business, session status
- Admin-only toggle to view deleted sessions (excluded from statistics)
- Quick links to open new session or view details

**Session Lifecycle**
1. **Create** — Cashier selects business, enters initial cash, optional expenses
2. **Track** — Log cash/card/transfer amounts throughout shift
   - Add multiple expense line items (description + amount)
   - Add multiple bank transfer line items (description + amount)
   - Totals auto-calculate from line items
3. **Close** — Auto-calculates: `cash_sales = (final_cash + envelope) - initial_cash`
4. **Edit** — Corrections within 12 hours (admins anytime)
5. **Flag** — Mark discrepancies with reason for follow-up
6. **Delete/Restore** — Soft delete (admin-only). Deleted sessions don't affect statistics. Can be restored anytime

**Admin Panel**
- List all users, create new ones (auto-generates passwords)
- Assign cashiers to business locations (M:N relationship)
- Disable accounts without deleting
- View and restore deleted cash sessions
- View audit logs of who edited what and when

**Reports & Analytics**
- **Weekly Revenue Trend** — Compare current week vs previous 4 weeks with day-by-day breakdown
  - Interactive charts showing week-over-week comparison
  - Growth percentage calculations with trend indicators (↑ ↓ →)
  - Identify highest/lowest revenue days
  - Cached results for performance (5min for current week, 1hr for historical)
  - Supports all businesses with real-time filtering

**Permission System**
- **Admin:** Can create/edit/delete businesses, manage all sessions, reset passwords, view/restore deleted sessions
- **Cashier:** Limited to assigned businesses only; within those, can create and view only their own sessions (edit within 12hr window) and cannot view sessions created by other cashiers. Cannot access deleted sessions (even their own)

---

## Why This Matters

This isn't a toy app. It's solving a real business problem for real businesses. Every feature exists because someone said "we need this to not waste time on paperwork."

- **Audit Trail:** Every edit tracked with timestamp, user, old/new values — required for accounting
- **Soft Deletes:** Sessions can be recovered, nothing is permanently lost. Admins can toggle deleted sessions view. Deleted sessions excluded from statistics but preserved for audit
- **Input Validation:** Comprehensive null/undefined/type checking prevents crashes from unexpected input
- **Reconciliation Math:** Automatic calculation removes manual errors
- **Multi-Location:** Cashiers work across different businesses, each gets their own view
- **Production Ready:** Runs 24/7 on Railway, handles failures gracefully

---

## Code Quality

- **167+ Tests** — Every RBAC rule tested, async patterns verified, edge cases covered
- **Type Hints** — Full coverage with Pydantic v2, SQLAlchemy Mapped types
- **Input Validation** — Comprehensive validation for null, undefined, and unexpected types across all endpoints
- **Linting** — ruff, black, isort with pre-commit hooks
- **Error Handling** — Custom exceptions with context, structured JSON logging
- **Async Throughout** — No blocking I/O, connection pooling, proper session management
- **Security Best Practices** — XSS prevention using `createElement`/`textContent` instead of `innerHTML`, CSRF protection

---

## Development Guidelines

**Reports & Analytics:**
- **Always update URL with filters** — Use `window.history.pushState()` to update URL parameters when users change filters (business, date, etc.)
  - Makes reports shareable (users can copy/paste URL with specific filters)
  - Browser back/forward buttons work correctly
  - Page refresh preserves selected filters
  - Example: `/reports/weekly-trend?year=2026&week=1&business_id=abc123`
- **Prevent XSS** — Use `createElement()` and `textContent` instead of `innerHTML` when displaying dynamic data
- **Cache strategically** — Use versioned cache keys (e.g., `v4`) for calculation logic changes
- **Error handling** — Always show user-friendly error messages, log technical details to console

---

## Technical Decisions (And Why)

**Session-Based Auth (Not JWT)**  
Users stay logged in across browser reloads. Simpler for business staff who aren't tech-savvy. Timeout enforced: 30min for cashiers, 2hrs for admins.

**Server-Rendered Templates (Not SPA)**  
HTML from the backend keeps things lean. No JavaScript framework bloat. HTMX for pagination. Jinja2 for i18n. Works fine.

**Soft Deletes (Not Hard Deletes)**  
Accountants need to see the full history. Businesses and sessions have `is_active` or `is_deleted` flags. Recovery is one flag flip. Admins can toggle deleted sessions view in dashboard. Deleted sessions are excluded from statistics but preserved with audit metadata (deleted_by, deleted_at).

**PostgreSQL + Async SQLAlchemy**  
Multi-location = concurrent sessions. Async handles it without complexity. Alembic migrations keep schema versioned.

**Structured Logging with Request IDs**  
When something breaks, trace the exact request through the logs. Every log entry includes a correlation ID.

**Cache Versioning Strategy**  
Reports use versioned cache keys (e.g., `weekly_trend_v4`) to handle calculation logic changes. When logic changes, increment the version constant—old entries naturally expire via TTL. Prevents stale data after deployments without requiring manual cache flushes.

---

## Project Structure
```
src/cashpilot/
├── api/                    # FastAPI routers
│   ├── routes/             # Frontend routes (dashboard, sessions, businesses, reports)
│   └── *.py                # API endpoints (auth, business, sessions, admin, user, reports)
├── models/                 # SQLAlchemy ORM + Pydantic schemas
├── core/                   # Database, security, errors, logging, validation
├── middleware/             # Request ID correlation
├── utils/                  # Timezone helpers (Paraguay-specific)
└── scripts/                # seed.py, createuser.py, assign_cashiers.py

tests/                      # 167+ async pytest tests
├── test_rbac.py           # 40+ permission tests
├── test_session_form_rbac.py
├── test_user_business_assignment.py
└── conftest.py / factories.py

templates/                  # Jinja2 HTML + Tailwind
├── login.html
├── index.html (dashboard)
├── businesses/
├── sessions/
├── admin/
├── reports/               # Analytics & reporting templates
└── partials/

alembic/                    # Database migrations
translations/               # Spanish/English
scripts/                    # Backup/restore scripts (Railway-specific)
docker-compose.yml          # PostgreSQL + FastAPI
Makefile                    # make test, make seed, etc.
```

---

## Deployment

**Production:** Railway (auto-deploy from `main` branch)
```bash
git push origin main
# → GitHub webhook → Railway builds & deploys
# Check logs at https://railway.app
```

**Environment:**
```env
DATABASE_URL=postgresql://...
SESSION_SECRET_KEY=...
ENVIRONMENT=production
```

**Monitoring:**
- Railway metrics (CPU, memory, response times)
- JSON structured logs with request IDs
- Alembic migrations tracked in git

---

## Database Backups (Optional)

> **Note:** Backup scripts are configured for Railway deployments. Adapt for your hosting provider.

Railway's Hobby plan doesn't include automated backups. The `scripts/` directory includes optional backup/restore tooling for production safety.

### Quick Start (Railway)
```bash
# Setup (one-time)
cp .env.backup.example .env.backup
# Edit .env.backup with your Railway database URL

# Weekly backup
./scripts/backup_production.sh

# Test restore locally
./scripts/restore_to_local.sh backups/cashpilot_20251220_160224.sql.gz

# Restore to Railway PR deployment (for testing)
./scripts/restore_to_railway.sh "DATABASE_URL" backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

**See [docs/backup_restore.md](docs/backup_restore.md) for complete setup guide.**

**Critical moments to backup:**
- Before schema migrations (`alembic upgrade`)
- Before deploying to production
- Weekly (recommended)

**Other hosting providers:** Adapt scripts in `scripts/` directory or use provider's native backup features (Heroku Postgres, AWS RDS, etc).

---

## Contributing
```bash
git checkout -b feature/your-feature
make test       # Verify tests pass
make fmt        # Format code
make lint       # Check linting
make audit      # Security audit
git add .
git commit -m "feat: your change description"
git push origin feature/your-feature
# Create PR to main
```

Use Linear for ticket tracking (MIZ-XXX prefix). Reference in commit messages.

---

## Database Schema

**Tables:**
- `users` — Email, hashed password, role (ADMIN/CASHIER), is_active flag
- `businesses` — Name, address, phone, is_active flag
- `user_businesses` — M:N assignment (which cashier works at which business)
- `cash_sessions` — Initial/final cash, payments, reconciliation, is_deleted flag
- `expense_items` — Line items for expenses (description, amount) linked to sessions
- `transfer_items` — Line items for bank transfers (description, amount) linked to sessions
- `cash_session_audit_logs` — Edit history (timestamp, user, old/new values, reason)

**Timezone:** America/Asuncion (Paraguay). All times stored UTC, displayed in local.

---

## What's Missing

**Extended Analytics** — Discrepancy patterns, cashier performance metrics, predictive trends  
**CSV Export** — Download sessions for accounting  
**Email Alerts** — Notify admin of large discrepancies  
**Mobile App** — Native iOS/Android for on-the-go session management

These are intentionally not built yet. Current focus is on core reconciliation and essential reporting.

---

## License

Portfolio / freelance work. Not open source. Available for discussion.
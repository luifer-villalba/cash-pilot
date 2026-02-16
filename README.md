# 💰 CashPilot

Business cash register reconciliation system built for multi-location operations. Replaces manual paper-based daily reconciliation with automated session tracking, multi-payment support, and role-based access control.

[![Documentation](https://img.shields.io/badge/docs-available-blue)](docs/README.md)
[![Security](https://img.shields.io/badge/security-policy-green)](SECURITY.md)
[![Tests](https://img.shields.io/badge/tests-262+-success)](tests/)

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

**Backend:** FastAPI 0.128.0+ • SQLAlchemy 2.0.35 • PostgreSQL • asyncpg 0.29.0  
**Frontend:** Jinja2 3.1.0+ • Tailwind CSS 4.1.18 • DaisyUI 5.5.14 • HTMX 1.9.10  
**DevOps:** Docker • Alembic 1.13.3 • Railway deployment • GitHub auto-deploy  
**Testing:** pytest 8.3.2 • 262+ async tests • RBAC coverage  
**i18n:** Spanish/English (Babel 2.14.0)

**Compatibility:** Windows 7+ (IE11, Chrome 50+, Firefox 45+) - See [Windows 7 Compatibility Guide](docs/reference/w7-compatibility.md)

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
make test               # Run 262+ tests
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

- **262+ Tests** — Every RBAC rule tested, async patterns verified, edge cases covered
- **Type Hints** — Full coverage with Pydantic v2, SQLAlchemy Mapped types
- **Input Validation** — Comprehensive validation for null, undefined, and unexpected types across all endpoints
- **Linting** — ruff, black, isort with pre-commit hooks
- **Error Handling** — Custom exceptions with context, structured JSON logging
- **Async Throughout** — No blocking I/O, connection pooling, proper session management

---

## Technical Decisions (And Why)

**Session-Based Auth (Not JWT)**  
Users stay logged in across browser reloads. Simpler for business staff who aren't tech-savvy. Timeout enforced: 10 hours for cashiers, 2hrs for admins.

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

tests/                      # 262+ async pytest tests
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

## Documentation

📚 **Full documentation available in [`/docs`](docs/README.md)**

**Quick Links:**
- [Documentation Index](docs/README.md) - Complete guide to all documentation
- [Getting Started Guide](docs/reference/GETTING_STARTED.md) - Developer setup and first steps
- [API Reference](docs/reference/API.md) - Complete API endpoint documentation
- [Troubleshooting Guide](docs/reference/TROUBLESHOOTING.md) - Common issues and solutions
- [Design System](docs/reference/design_readme.md) - UI/UX patterns and component guidelines
- [Windows 7 Compatibility](docs/reference/w7-compatibility.md) - Legacy browser support guide
- [Backup & Restore](docs/runbooks/backup_restore.md) - Database backup procedures
- [Security Policy](SECURITY.md) - Security practices and vulnerability tracking
- [Contributing Guide](CONTRIBUTING.md) - How to contribute to the project

**Feature Documentation:**
- [Weekly Trend Report](docs/reference/features/WEEKLY_TREND_REPORT.md) - Week-over-week revenue analysis
- [Daily Reconciliation](docs/reference/features/DAILY_RECONCILIATION.md) - System vs manual entry comparison

**For New Developers:** Start with the [Getting Started Guide](docs/reference/GETTING_STARTED.md) and [Documentation Index](docs/README.md) for recommended reading paths.

---

## Deployment

**Production:** Railway (auto-deploy from `main` branch)
```bash
git push origin main
# → GitHub webhook → Railway builds & deploys
# Check logs at https://railway.app
```

**Environment Variables:**
```env
# Required
DATABASE_URL=postgresql://...
SESSION_SECRET_KEY=...
ENVIRONMENT=production

# Optional
RAILWAY_STATIC_URL=...  # For static file serving
ROOT_PATH=...           # For reverse proxy setups
SENTRY_DSN=...          # For error tracking
```

**Monitoring:**
- Railway metrics (CPU, memory, response times)
- JSON structured logs with request IDs
- Alembic migrations tracked in git
- Sentry error tracking (if configured)

**See Also:** [Backup & Restore Guide](docs/runbooks/backup_restore.md) for production database management

---

## Database Backups

> **Note:** Backup scripts are configured for Railway deployments. Adapt for your hosting provider.

Railway's Hobby plan doesn't include automated backups. The `scripts/` directory includes optional backup/restore tooling for production safety.

**📖 Complete Guide:** See [Backup & Restore Guide](docs/runbooks/backup_restore.md) for detailed instructions.

**Quick Start:**
```bash
# Setup (one-time)
cp .env.backup.example .env.backup
# Edit .env.backup with your Railway database URL

# Weekly backup
./scripts/backup_production.sh

# Test restore locally
./scripts/restore_to_local.sh backups/cashpilot_YYYYMMDD_HHMMSS.sql.gz
```

**Critical moments to backup:**
- Before schema migrations (`alembic upgrade`)
- Before deploying to production
- Weekly (recommended)

**📖 Complete Guide:** See [Backup & Restore Guide](docs/runbooks/backup_restore.md) for detailed instructions.

---

## Security

⚠️ **Important:** Review our [Security Policy](SECURITY.md) before contributing.

**Security Practices:**
- Automated security audits via `pip-audit` (pre-commit + CI)
- Monthly manual audits (first Monday of each month)
- All CVEs tracked and documented in [SECURITY.md](SECURITY.md)
- Vulnerability reporting process documented

**Current Status:** No active critical or high-severity CVEs. See [SECURITY.md](SECURITY.md) for details.

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

**Guidelines:**
- Use Linear for ticket tracking (MIZ-XXX prefix). Reference in commit messages.
- Follow [Design System Guide](docs/reference/design_readme.md) for UI changes
- Ensure [Windows 7 compatibility](docs/reference/w7-compatibility.md) for frontend changes
- Review [Security Policy](SECURITY.md) before submitting PRs

**See Also:** [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines

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
**Email Alerts** — Notify admin of large discrepancies  
**Mobile App** — Native iOS/Android for on-the-go session management

These are intentionally not built yet. Current focus is on core reconciliation and essential reporting.

---

## License

Portfolio / freelance work. Not open source. Available for discussion.

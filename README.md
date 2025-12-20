# 💰 CashPilot

Pharmacy cash register reconciliation system built for 5-6 pharmacy locations in Paraguay. Replaces manual paper-based daily reconciliation with automated session tracking, multi-payment support, and role-based access control.

**Live:** https://cash-pilot-production.up.railway.app

---

## What It Does

**Problem:** Pharmacy managers spend 30+ minutes daily reconciling cash by hand, tracking payments across cash/card/transfers, and managing discrepancies in spreadsheets.

**Solution:** 
- Cashiers open a shift with initial cash → track payments throughout day → close with auto-reconciliation
- System flags discrepancies instantly (short 15,000₲? it tells you)
- Admins manage users, assign them to pharmacy locations, reset passwords
- Complete audit trail of every edit (who changed what, when, why)
- Requires an internet connection; offline mode is not currently supported

---

## Built With

**Backend:** FastAPI • SQLAlchemy 2.0 async • PostgreSQL • asyncpg  
**Frontend:** Jinja2 templates • Tailwind CSS • DaisyUI • HTMX pagination  
**DevOps:** Docker • Alembic migrations • Railway deployment • GitHub auto-deploy  
**Testing:** pytest • 160+ async tests • RBAC coverage  
**i18n:** Spanish/English (Babel)

---

## Getting Started
```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot
cp .env.example .env

# All commands via Makefile
make build              # Build containers
make up                 # Start services
make migrate            # Run migrations
make seed               # Create demo data (3 pharmacies, 87 sessions)
make test               # Run 160+ tests
make logs               # View live logs

# Visit http://localhost:8000
# Login: admin@example.com / password123 (from seed)
```

---

## Feature Walkthrough

**Dashboard**
- Paginated session list with date, business, cashier, reconciliation status
- Filter by date range, cashier, pharmacy, session status
- Quick links to open new session or view details

**Session Lifecycle**
1. **Create** — Cashier selects pharmacy, enters initial cash, optional expenses
2. **Track** — Log cash/card/transfer amounts throughout shift
3. **Close** — Auto-calculates: `cash_sales = (final_cash + envelope) - initial_cash`
4. **Edit** — Corrections within 12 hours (admins anytime)
5. **Flag** — Mark discrepancies with reason for follow-up

**Admin Panel**
- List all users, create new ones (auto-generates passwords)
- Assign cashiers to pharmacy locations (M:N relationship)
- Disable accounts without deleting
- View audit logs of who edited what and when

**Permission System**
- **Admin:** Can create/edit/delete businesses, manage all sessions, reset passwords
- **Cashier:** Limited to assigned pharmacies only; within those, can create and view only their own sessions (edit within 12hr window) and cannot view sessions created by other cashiers

---

## Why This Matters

This isn't a toy app. It's solving a real business problem for real pharmacies. Every feature exists because someone said "we need this to not waste time on paperwork."

- **Audit Trail:** Every edit tracked with timestamp, user, old/new values — required for accounting
- **Soft Deletes:** Sessions can be recovered, nothing is permanently lost
- **Reconciliation Math:** Automatic calculation removes manual errors
- **Multi-Location:** Cashiers work across different pharmacies, each gets their own view
- **Production Ready:** Runs 24/7 on Railway, handles failures gracefully

---

## Code Quality

- **160+ Tests** — Every RBAC rule tested, async patterns verified, edge cases covered
- **Type Hints** — Full coverage with Pydantic v2, SQLAlchemy Mapped types
- **Linting** — ruff, black, isort with pre-commit hooks
- **Error Handling** — Custom exceptions with context, structured JSON logging
- **Async Throughout** — No blocking I/O, connection pooling, proper session management

---

## Technical Decisions (And Why)

**Session-Based Auth (Not JWT)**  
Users stay logged in across browser reloads. Simpler for pharmacy staff who aren't tech-savvy. Timeout enforced: 30min for cashiers, 2hrs for admins.

**Server-Rendered Templates (Not SPA)**  
HTML from the backend keeps things lean. No JavaScript framework bloat. HTMX for pagination. Jinja2 for i18n. Works fine.

**Soft Deletes (Not Hard Deletes)**  
Accountants need to see the full history. Businesses and sessions have `is_active` or `is_deleted` flags. Recovery is one flag flip.

**PostgreSQL + Async SQLAlchemy**  
Multi-location = concurrent sessions. Async handles it without complexity. Alembic migrations keep schema versioned.

**Structured Logging with Request IDs**  
When something breaks, trace the exact request through the logs. Every log entry includes a correlation ID.

---

## Project Structure
```
src/cashpilot/
├── api/                    # FastAPI routers (auth, business, sessions, admin)
├── models/                 # SQLAlchemy ORM + Pydantic schemas
├── core/                   # Database, security, errors, logging, validation
├── middleware/             # Request ID correlation
├── utils/                  # Timezone helpers (Paraguay-specific)
└── scripts/                # seed.py, createuser.py

tests/                      # 160+ async pytest tests
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
echo 'DATABASE_PUBLIC_URL=your_railway_public_url' > .env.backup

# Weekly backup
./scripts/backup_production.sh

# Test restore locally
./scripts/restore_to_local.sh backups/cashpilot_20251220_160224.sql.gz
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
- `user_businesses` — M:N assignment (which cashier works at which pharmacy)
- `cash_sessions` — Initial/final cash, payments, reconciliation, is_deleted flag
- `cash_session_audit_logs` — Edit history (timestamp, user, old/new values, reason)

**Timezone:** America/Asuncion (Paraguay). All times stored UTC, displayed in local.

---

## What's Missing

**Analytics Dashboard** — Revenue trends, discrepancy patterns, cashier performance  
**CSV Export** — Download sessions for accounting  
**Email Alerts** — Notify admin of large discrepancies  

These are intentionally not built yet. v1 focuses on core reconciliation working perfectly.

---

## License

Portfolio / freelance work. Not open source. Available for discussion.
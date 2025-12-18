# File: README.md

# 💰 CashPilot

**Pharmacy cash register reconciliation system** — Replace manual paper-based processes with automated daily session tracking and multi-payment reconciliation.

Built for **5-6 pharmacy locations** in Paraguay, serving as both a **production business tool** and a **portfolio project** demonstrating modern Python/FastAPI development.

---

## ✨ Features

### ✅ Implemented (Dec 2024)
- **Session-based Authentication** - Login/logout with session management
- **Multi-location Ready** - Business CRUD with user-business assignment
- **Full Cash Session Lifecycle**
  - Create sessions with initial cash amounts
  - Track payments: cash, credit/debit cards, bank transfers
  - Close sessions with auto-reconciliation
  - Edit closed sessions when corrections needed
  - Flag/unflag sessions for discrepancy management
- **Auto-Reconciliation Formula** - Automatic calculation of cash sales and differences
- **Responsive Frontend** - Jinja2 templates + Tailwind CSS + DaisyUI
- **Internationalization** - Spanish/English with Babel
- **Demo Data** - Seed script creates 3 pharmacies + 87 realistic sessions
- **Production Deployment** - Railway with auto-deploy from GitHub
- **54+ Tests** - Comprehensive pytest coverage with async patterns

### 🚧 Roadmap (Q1 2026)
- **Role-Based Access Control** - Admin vs Cashier permissions
- **Soft Delete & Restore** - Recoverable deletions with audit trails
- **Analytics Dashboard** - Daily/weekly reporting with charts
- **Audit Logs** - Complete action history tracking

---

## 🏗️ Architecture
```
Business 1:N CashSession
User M:N Business (role-aware assignment)

Models (SQLAlchemy async):
  Business → name, location, is_active
  CashSession → initial_cash, final_cash, payment methods, reconciliation
  User → email, hashed_password, role (ADMIN/CASHIER)

Schemas (Pydantic) → Request/Response validation
Templates (Jinja2) → Server-side rendered UI
```

**Stack:** FastAPI • SQLAlchemy async • PostgreSQL • Alembic • pytest • Docker • Jinja2 • Tailwind • DaisyUI • Babel • Railway

---

## 🚀 Quick Start

**Prerequisites:** Docker + Docker Compose
```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot
cp .env.example .env
docker compose build
make migrate-upgrade
make hook-install
make run
```

**Access:**
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Login: `admin@cashpilot.com` / `admin123` (from seed data)

---

## 🌿 Git Workflow

**Branches:**
- `main` → Production (auto-deploys to Railway)
- `dev` → Active development
- `feature/MIZ-XXX` → Feature branches from `dev`

**Flow:**
```bash
git checkout dev
git pull origin dev
git checkout -b feature/MIZ-123
# work → test → commit
git push -u origin feature/MIZ-123
# PR to dev → review → merge
# When ready: PR dev → main
```

**PR Requirements:** Tests pass • Code formatted • Linting passes • Pre-commit hook installed

---

## 🛠️ Commands

| Command | Description |
|---------|-------------|
| `make run` | Start FastAPI server (http://localhost:8000) |
| `make test` | Run full pytest suite |
| `make fmt` | Auto-format (black, ruff, isort) |
| `make lint` | Check code quality |
| `make migrate-upgrade` | Apply DB migrations |
| `make seed` | Load demo data (3 pharmacies + 87 sessions) |
| `make sh` | Shell into app container |
| `make createuser` | Create new user interactively |

---

## 💰 Auto-Reconciliation Logic

CashSession automatically calculates:
```python
# Core formula
cash_sales = (final_cash - initial_cash) + envelope_amount

# Total income from all payment methods
total_sales = cash_sales + credit_card + debit_card + bank_transfer

# Reconciliation check
difference = total_sales - cash_sales
```

**Difference Interpretation:**
- `0` = Perfect match ✅
- `> 0` = Cash shortage (missing money) ⚠️
- `< 0` = Cash overage (extra money) 📦

**Real-world example:**
- Initial cash: Gs 500,000
- Final cash: Gs 1,200,000
- Envelope deposits: Gs 300,000
- Credit cards: Gs 450,000
- **Result:** `cash_sales = (1,200,000 - 500,000) + 300,000 = 1,000,000`
- **Total:** `1,000,000 + 450,000 = 1,450,000`
- **Difference:** `0` (balanced session)

---

## 📁 Structure
```
cashpilot/
├── src/cashpilot/
│   ├── api/              # FastAPI routers (businesses, sessions, auth)
│   ├── models/           # SQLAlchemy models + Pydantic schemas
│   ├── core/             # Database, config, errors, logging
│   ├── middleware/       # Request ID, CORS, session management
│   └── scripts/          # seed.py, createuser.py
├── tests/                # pytest suite (54+ tests)
├── alembic/              # Database migrations
├── templates/            # Jinja2 HTML (dashboard, sessions, auth)
├── static/               # Tailwind CSS, JavaScript
├── translations/         # i18n (Spanish/English)
└── docker-compose.yml    # PostgreSQL + FastAPI services
```

---

## 🌱 Demo Data
```bash
make seed
```

**Creates:**
- 3 businesses (Farmacia Central, Farmacia Norte, Farmacia Este)
- 2 users (admin + cashier)
- 87 cash sessions across 3 months with realistic data
- Various reconciliation scenarios (balanced, shortages, overages)

---

## 🧪 Testing
```bash
# Run all tests
make test

# Specific test file
docker compose run --rm app pytest tests/test_session.py -v

# With coverage
docker compose run --rm app pytest --cov=cashpilot tests/
```

**Test Coverage:** 54+ tests across models, API endpoints, auth, reconciliation logic

---

## 📊 Database

**Tables:**
- `businesses` - Pharmacy locations
- `cash_sessions` - Daily shift tracking with reconciliation
- `users` - Authentication + role management
- `user_businesses` - Many-to-many assignment table

**Migrations:** Alembic version-controlled schema changes

**Timezone:** America/Asuncion (Paraguay)

---

## 🎨 Design System

See `DESIGN_README.md` for:
- 6-tier color coding for financial numbers
- Component templates (metric cards, session headers)
- Emoji + uppercase label patterns
- Anti-patterns to avoid

**Key Principle:** Clarity over beauty — users need to understand numbers at a glance.

---

## ⚠️ Troubleshooting
```bash
make rebuild         # Full rebuild (stops containers, removes volumes)
make fix-perms       # Fix file permissions in WSL2
make migrate-current # Check current migration status
docker compose logs -f app  # View live logs
```

**Common Issues:**
- Hot reload not working → Check Docker Compose Watch config
- Permission errors → Run `make fix-perms`
- Migration conflicts → Check `alembic/versions/` for head state

---

## 🚀 Deployment

**Production:** Railway (https://cash-pilot-production.up.railway.app)

**Auto-deploy:** Push to `main` branch triggers Railway deployment

**Environment Variables:**
```env
DATABASE_URL=postgresql://...
SESSION_SECRET_KEY=<production-secret>
ENVIRONMENT=production
```

---

## 👤 Author

**Luis Fernando Villalba**  
Backend Developer | Asunción, Paraguay

[LinkedIn](https://linkedin.com/in/luis-fernando-villalba) • [GitHub](https://github.com/luifer-villalba)

**Goal:** Secure remote Python/FastAPI role (USD 6K+/month) by Q1-Q2 2026

---

## 📜 License

This project is a portfolio demonstration. Not licensed for commercial use without permission.

---

*Portfolio project demonstrating production-ready FastAPI development with async SQLAlchemy, comprehensive testing, session-based auth, and modern frontend integration (Jinja2 + Tailwind + DaisyUI).*
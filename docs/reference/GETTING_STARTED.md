# Getting Started with CashPilot

> 📚 Reference Document  
> This guide helps new developers get up and running with CashPilot development.

## Purpose

This guide walks you through setting up your local development environment, understanding the codebase structure, and making your first contribution to CashPilot.

---

## Prerequisites

Before you begin, ensure you have:

- **Git** installed
- **Docker** and **Docker Compose** installed
- **Text editor or IDE** (VS Code recommended)
- **Basic knowledge** of:
  - Python (FastAPI, SQLAlchemy)
  - HTML/CSS (Jinja2 templates, Tailwind CSS)
  - PostgreSQL
  - Git workflow

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot
```

---

## Step 2: Set Up Environment

### Create `.env` File

```bash
# Copy example (if available) or create from scratch
touch .env
```

Add the following environment variables:

```env
# Database
DATABASE_URL=postgresql://cashpilot_user:cashpilot_pass@db:5432/cashpilot
POSTGRES_USER=cashpilot_user
POSTGRES_PASSWORD=cashpilot_pass
POSTGRES_DB=cashpilot

# Security
SESSION_SECRET_KEY=your-secret-key-here-min-32-chars

# Application
ENVIRONMENT=development
```

**Note:** For `SESSION_SECRET_KEY`, generate a secure random string:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 3: Build and Start Services

Using the Makefile (recommended):

```bash
# Build containers
make build

# Start services (PostgreSQL + FastAPI)
make up

# Run database migrations
make migrate

# Seed demo data (3 businesses, sample users, 87 sessions)
make seed
```

**Without Make:**
```bash
docker compose build
docker compose up -d
docker compose exec app alembic upgrade head
docker compose exec app python src/cashpilot/scripts/seed.py
```

---

## Step 4: Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

**Default Credentials (from seed):**
- **Admin:** `admin@example.com` / `password123`
- **Cashier:** `cashier@example.com` / `password123`

---

## Step 5: Explore the Codebase

### Recommended Reading Order

1. **Product Documentation** (understand what we're building)
   - [docs/product/PRODUCT_VISION.md](../product/PRODUCT_VISION.md)
   - [docs/product/REQUIREMENTS.md](../product/REQUIREMENTS.md)
   - [docs/product/ACCEPTANCE_CRITERIA.md](../product/ACCEPTANCE_CRITERIA.md)

2. **Architecture** (understand how it's built)
   - [docs/architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
   - [docs/architecture/CODE_MAP.md](../architecture/CODE_MAP.md)
   - [docs/architecture/DATA_MODEL.md](../architecture/DATA_MODEL.md)

3. **SDLC** (understand how we work)
   - [docs/sdlc/WORKFLOW.md](../sdlc/WORKFLOW.md)
   - [docs/sdlc/DEFINITION_OF_READY.md](../sdlc/DEFINITION_OF_READY.md)

### Codebase Structure Quick Reference

```
src/cashpilot/
├── api/              # HTTP routes and endpoints
├── core/             # Auth, RBAC, security, config
├── models/           # Database models (SQLAlchemy)
├── middleware/       # Request/response middleware
├── utils/            # Helper functions
└── scripts/          # Maintenance scripts

templates/            # Jinja2 HTML templates
static/               # CSS, JavaScript
tests/                # 29 test files with 300+ tests
alembic/              # Database migrations
docs/                 # All documentation
```

---

## Step 6: Run Tests

```bash
# Run all tests
make test

# Run specific test file
docker compose exec app pytest tests/test_auth.py

# Run with coverage
docker compose exec app pytest --cov=cashpilot tests/

# Run specific test
docker compose exec app pytest tests/test_auth.py::test_login_success -v
```

---

## Step 7: Make Your First Change

### Example: Add a New Field to Business Model

**Follow the workflow:**

1. **Create a branch**
   ```bash
   git checkout -b feat/add-business-email
   ```

2. **Update the model** (`src/cashpilot/models/business.py`)
   ```python
   email: Mapped[str | None] = mapped_column(String(255), nullable=True)
   ```

3. **Create migration**
   ```bash
   make migration-create message="add email to businesses"
   ```

4. **Update DATA_MODEL.md** (document your change)

5. **Run migration**
   ```bash
   make migrate
   ```

6. **Update templates** (if UI changes needed)

7. **Write tests** (if behavior changes)
   ```python
   def test_business_email():
       business = Business(name="Test", email="test@example.com")
       assert business.email == "test@example.com"
   ```

8. **Run tests**
   ```bash
   make test
   ```

9. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add email field to business model"
   git push origin feat/add-business-email
   ```

10. **Create Pull Request** (use the PR template)

---

## Common Development Tasks

### Running Database Migrations

```bash
# Create a new migration
make migration-create message="your migration description"

# Or manually
docker compose exec app alembic revision --autogenerate -m "your message"

# Apply migrations
make migrate

# Or manually
docker compose exec app alembic upgrade head

# Rollback migration
docker compose exec app alembic downgrade -1
```

### Viewing Logs

```bash
# View live logs
make logs

# Or manually
docker compose logs -f app

# View database logs
docker compose logs -f db
```

### Code Quality

```bash
# Format code (black, isort)
make fmt

# Run linter (ruff)
make lint

# Security audit
make audit
```

### Working with Translations

```bash
# Extract translatable strings
docker compose exec app pybabel extract -F babel.cfg -o translations/messages.pot .

# Update translations for Spanish
docker compose exec app pybabel update -i translations/messages.pot -d translations -l es_PY

# Compile translations
docker compose exec app pybabel compile -d translations
```

### Seed Database with Sample Data

```bash
# Full seed (3 businesses, users, 87 sessions)
make seed

# Or manually
docker compose exec app python src/cashpilot/scripts/seed.py
```

### Reset Database (CAUTION: Deletes all data)

```bash
# Stop services
docker compose down

# Remove volume
docker volume rm cash-pilot_postgres_data

# Restart and migrate
docker compose up -d
make migrate
make seed
```

---

## Development Tips

### 1. Hot Reload

FastAPI automatically reloads on code changes when running in development mode. Just save your file and refresh your browser.

### 2. Database GUI

Use a PostgreSQL client to inspect the database:
- **Host:** localhost
- **Port:** 5432
- **Database:** cashpilot
- **User:** cashpilot_user
- **Password:** cashpilot_pass

Recommended tools:
- **pgAdmin** (free, full-featured)
- **DBeaver** (free, multi-database)
- **TablePlus** (paid, beautiful)

### 3. Interactive Python Shell

```bash
docker compose exec app python
```

Then import and explore:
```python
from cashpilot.models import User, Business, CashSession
from cashpilot.core.db import get_db

# Explore models
```

### 4. Debugging

Add breakpoints using Python's debugger:
```python
import pdb; pdb.set_trace()
```

Or use VS Code's debugger with Docker (see `.vscode/launch.json` if configured).

---

## Troubleshooting

### "Port 8000 already in use"

```bash
# Find and kill process
sudo lsof -ti:8000 | xargs kill -9

# Or use different port
docker compose up -d --env PORT=8001
```

### "Database connection refused"

```bash
# Check if database container is running
docker compose ps

# Restart database
docker compose restart db

# Check logs
docker compose logs db
```

### "Migration conflicts"

```bash
# Check current migration state
docker compose exec app alembic current

# Check migration history
docker compose exec app alembic history

# Fix conflicts by merging or recreating migrations
```

### "Tests failing"

```bash
# Clear test cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +

# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## Next Steps

Once you're comfortable with the basics:

1. **Read feature documentation** in `docs/reference/` for specific features
2. **Review existing PRs** to understand code review expectations
3. **Pick a task** from `docs/implementation/IMPROVEMENT_BACKLOG.md`
4. **Ask questions** - open an issue or contact maintainers

---

## Related Documentation

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [AI_PLAYBOOK.md](../sdlc/AI_PLAYBOOK.md) - Using AI tools
- [CODE_MAP.md](../architecture/CODE_MAP.md) - Where to add code
- [TEST_PLAN.md](../sdlc/TEST_PLAN.md) - Testing strategy
- [API.md](../reference/API.md) - API endpoint reference

---

## Getting Help

- **Documentation:** Check `docs/` directory first
- **Issues:** Search existing GitHub issues
- **Maintainers:** Contact via email or GitHub
- **Code:** Read the source code - it's well-documented!

Welcome to CashPilot development! 🚀

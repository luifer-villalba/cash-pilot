# CashPilot 💰

A modern, Docker-first backend for pharmacy cash register reconciliation. Built with Python best practices for clean architecture and maintainability.

## 🎯 Project Purpose

CashPilot is a pharmacy cash register reconciliation system designed to:
- Track daily cash sessions (shifts) per pharmacy location
- Auto-calculate cash sales and detect shortages
- Manage multiple pharmacy locations (businesses)
- Provide audit trail for cash handling

Built with production-ready FastAPI patterns and clean architecture principles.

## 🚀 Quickstart

### Prerequisites
- Docker & Docker Compose installed
- No local Python required

### Environment Setup

1. **Copy environment template**
```bash
cp .env.example .env
```

2. **Review and customize** `.env` if needed (defaults work for local dev)

3. **Build and start services**
```bash
docker compose build
docker compose up -d
```

### Development Setup

1. **Clone and build**
```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot
docker compose build
```

2. **Run migrations**
```bash
make migrate-upgrade
```

3. **Install git hooks** (blocks commits if linting fails)
```bash
make hook-install
```

4. **Start the server**
```bash
make run
```

The API will be available at [http://localhost:8000](http://localhost:8000)

## 🛠️ Available Commands

| Command | Description |
|---------|-------------|
| `make run` | Start the FastAPI server on port 8000 |
| `make test` | Run the test suite with pytest |
| `make fmt` | Auto-format code (ruff + black + isort) |
| `make lint` | Check code quality (runs in pre-commit hook) |
| `make sh` | Open shell inside Docker container |
| `make hook-install` | Install git pre-commit hook |
| `make migrate-create` | Create a new database migration |
| `make migrate-upgrade` | Apply pending migrations |
| `make migrate-current` | Show current migration version |
| `make check-db` | Inspect database tables and version |

## 📁 Project Structure
```
cashpilot/
├── src/
│   └── cashpilot/          # Main application package
│       ├── api/            # API endpoints
│       │   ├── health.py   # Health check endpoint
│       │   ├── business.py # Business CRUD operations
│       │   └── cash_session.py # Cash session management
│       ├── models/         # Database models and schemas
│       │   ├── business.py # Pharmacy location model
│       │   ├── cash_session.py # Cash session model
│       │   ├── business_schemas.py # Business Pydantic schemas
│       │   ├── cash_session_schemas.py # Session Pydantic schemas
│       │   └── enums.py    # Domain enums (MovementType, SessionStatus)
│       ├── core/           # Core utilities
│       │   └── db.py       # Database config & session management
│       └── main.py         # FastAPI application factory
├── tests/                  # Test suite
│   ├── conftest.py         # Pytest fixtures
│   └── test_health.py      # Health endpoint tests
├── alembic/                # Database migrations
├── .githooks/              # Git hooks (pre-commit)
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration (app + db)
├── Makefile                # Development commands
├── pyproject.toml          # Python dependencies & tool configs
└── README.md               # This file
```

## 🌐 API Documentation

### Running the Server

Start the FastAPI server with:
```bash
make run
```

The server runs on [http://localhost:8000](http://localhost:8000)

### Core Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok"}
```

#### Businesses (Pharmacy Locations)

**Create a business:**
```bash
curl -X POST http://localhost:8000/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Farmacia Central",
    "address": "Av. España 123",
    "phone": "+595981234567"
  }'
```

**Get a business:**
```bash
curl http://localhost:8000/businesses/{business_id}
```

**Update a business:**
```bash
curl -X PUT http://localhost:8000/businesses/{business_id} \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

#### Cash Sessions (Shifts)

**List sessions (optional filtering):**
```bash
curl "http://localhost:8000/cash-sessions?business_id={business_id}&skip=0&limit=50"
```

**Open a new session:**
```bash
curl -X POST http://localhost:8000/cash-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "uuid-here",
    "cashier_name": "María López",
    "initial_cash": 500000.00,
    "shift_hours": "08:00-16:00"
  }'
```

**Get session details:**
```bash
curl http://localhost:8000/cash-sessions/{session_id}
```

**Close a session:**
```bash
curl -X PUT http://localhost:8000/cash-sessions/{session_id} \
  -H "Content-Type: application/json" \
  -d '{
    "final_cash": 1250000.00,
    "envelope_amount": 300000.00,
    "expected_sales": 1000000.00,
    "closing_ticket": "T-12345",
    "notes": "Normal shift, no issues"
  }'
```

### Interactive API Documentation

Once the server is running, access the auto-generated API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Running Tests

Execute the test suite with:
```bash
make test
```

Current test coverage includes:
- Health endpoint functionality
- Response format validation
- Content-type headers

## 📊 Database

The project uses PostgreSQL with SQLAlchemy ORM (async) and Alembic for migrations.

### Current Schema

**businesses**
- `id` (UUID, PK)
- `name` (String, indexed)
- `address` (String, optional)
- `phone` (String, optional)
- `is_active` (Boolean, indexed, default: true)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**cash_sessions**
- `id` (UUID, PK)
- `business_id` (UUID, FK → businesses.id, indexed)
- `status` (String, indexed) - "OPEN" or "CLOSED"
- `cashier_name` (String)
- `shift_hours` (String, optional)
- `opened_at` (DateTime)
- `closed_at` (DateTime, optional)
- `initial_cash` (Numeric 12,2)
- `final_cash` (Numeric 12,2, optional)
- `envelope_amount` (Numeric 12,2, default: 0.00)
- `expected_sales` (Numeric 12,2, default: 0.00)
- `closing_ticket` (String, optional)
- `notes` (String, optional)

**Calculated properties** (CashSession model):
- `cash_sales` = `(final_cash + envelope_amount) - initial_cash`
- `difference` = `cash_sales - expected_sales`

### Relationships
- One Business → Many CashSessions
- CashSession belongs to one Business

## 🔄 Development Workflow

1. Make changes in `src/`
2. Run `make fmt` to auto-format
3. Run `make test` to verify tests pass
4. Commit → pre-commit hook runs `make lint` automatically
5. If lint fails, fix issues and commit again

## 📚 Next Steps

### Sprint 3: Production Ready
- [ ] Add comprehensive tests for Business + CashSession endpoints
- [ ] Add seed script with sample data
- [ ] Set up GitHub Actions CI/CD
- [ ] Deploy to Render/Railway with PostgreSQL
- [ ] Add architecture diagram to README

### Future Enhancements
- [ ] Add authentication and authorization (JWT)
- [ ] Implement filtering and pagination for list endpoints
- [ ] Add Movement model for detailed cash flow tracking
- [ ] Add Category model for expense/income categorization
- [ ] Implement daily/weekly/monthly reports
- [ ] Add API rate limiting
- [ ] Implement error handling middleware
- [ ] Add structured logging (loguru)
- [ ] Add monitoring (Datadog/Sentry integration)

## 🧪 Testing

The project uses pytest with FastAPI TestClient:

```bash
# Run all tests
make test

# Run tests in the container shell (for debugging)
make sh
pytest -v
```

## 🏗️ Architecture Patterns

**Application Factory**: `create_app()` returns fresh FastAPI instance for clean test isolation

**Async SQLAlchemy**: All database operations use async/await with AsyncSession

**Dependency Injection**: Database sessions injected via `Depends(get_db)`

**Pydantic Schemas**: Separate schemas for Create/Read/Update operations

**Alembic Migrations**: Version-controlled database schema changes

**Code Quality**: Pre-commit hooks enforce ruff, black, isort standards

## 👤 Author

**Luis F. Villalba** - Backend Developer  
[LinkedIn](https://linkedin.com/in/luis-fernando-villalba) | [GitHub](https://github.com/luifer-villalba)

---

*This project demonstrates production-ready FastAPI backend development with clean architecture, async patterns, and comprehensive testing.*
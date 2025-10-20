# CashPilot 💰

A modern, Docker-first backend for personal cash flow tracking. Built with Python best practices for clean architecture and maintainability.

## 🎯 Project Purpose

CashPilot is a learning-focused MVP designed to demonstrate:
- Clean backend architecture with FastAPI
- Docker-first development workflow
- Code quality automation (ruff, black, isort)
- Production-ready project structure
- RESTful API design with automated documentation

## 🚀 Quickstart

### Prerequisites
- Docker & Docker Compose installed
- No local Python required

### Setup

1. **Clone and build**
```bash
git clone https://github.com/luifer-villalba/cash-pilot.git
cd cash-pilot
docker compose build
```

2. **Install git hooks** (blocks commits if linting fails)
```bash
make hook-install
```

3. **Run code formatting**
```bash
make fmt
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

## 📁 Project Structure
```
cashpilot/
├── src/
│   └── cashpilot/          # Main application package
│       ├── api/            # API endpoints
│       ├── models/         # Database models and schemas
│       ├── core/           # Core utilities (database config)
│       └── main.py         # FastAPI application factory
├── tests/                  # Test suite
├── alembic/                # Database migrations
├── .githooks/              # Git hooks (pre-commit)
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
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

### Available Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok"}
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

## 🔄 Development Workflow

1. Make changes in `src/`
2. Run `make fmt` to auto-format
3. Run `make test` to verify tests pass
4. Commit → pre-commit hook runs `make lint` automatically
5. If lint fails, fix issues and commit again

## 📊 Database

The project uses PostgreSQL with SQLAlchemy ORM and Alembic for migrations.

### Database Commands

| Command | Description |
|---------|-------------|
| `make migrate-create` | Create a new migration |
| `make migrate-up` | Apply pending migrations |
| `make migrate-current` | Show current migration version |
| `make migrate-downgrade` | Rollback last migration |
| `make check-db` | Inspect database tables and version |

### Current Schema

- **movements**: Stores income/expense transactions
  - Fields: id, occurred_at, type, amount_gs, description, category
  - Indexes on: occurred_at, type, category

## 📚 Next Steps

- [ ] Implement CRUD endpoints for movements
- [ ] Add authentication and authorization
- [ ] Implement filtering and pagination
- [ ] Add comprehensive integration tests
- [ ] Set up GitHub Actions CI/CD
- [ ] Add API rate limiting
- [ ] Implement error handling middleware
- [ ] Add logging and monitoring

## 🧪 Testing

The project uses pytest with FastAPI TestClient:

```bash
# Run all tests
make test

# Run tests in the container shell (for debugging)
make sh
pytest -v
```

## 👤 Author

**Luis F. Villalba** - Backend Developer  
[LinkedIn](https://linkedin.com/in/luis-fernando-villalba) | [GitHub](https://github.com/luifer-villalba)

---

*This project follows Python best practices and is designed as a portfolio piece for backend development roles.*
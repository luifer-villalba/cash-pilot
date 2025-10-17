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
│       └── main.py         # FastAPI application factory
├── tests/                  # Test suite
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

## 🔄 Development Workflow

1. Make changes in `src/`
2. Run `make fmt` to auto-format
3. Run `make test` to verify tests pass
4. Commit → pre-commit hook runs `make lint` automatically
5. If lint fails, fix issues and commit again

## 📚 Next Steps

- [x] FastAPI integration with health endpoint
- [x] Application factory pattern implementation
- [x] Test suite setup with pytest
- [ ] Database setup with PostgreSQL
- [ ] Movement model CRUD endpoints
- [ ] Authentication and authorization
- [ ] Docker Compose with database service
- [ ] API rate limiting and security headers

## 👤 Author

**Luis F. Villalba** - Backend Developer  
[LinkedIn](https://linkedin.com/in/luis-fernando-villalba) | [GitHub](https://github.com/luifer-villalba)

---

*This project follows Python best practices and is designed as a portfolio piece for backend development roles.*
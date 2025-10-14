# CashPilot 💰

A modern, Docker-first backend for personal cash flow tracking. Built with Python best practices for clean architecture and maintainability.

## 🎯 Project Purpose

CashPilot is a learning-focused MVP designed to demonstrate:
- Clean backend architecture (Django/FastAPI)
- Docker-first development workflow
- Code quality automation (ruff, black, isort)
- Production-ready project structure

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

## 🛠️ Available Commands

| Command | Description |
|---------|-------------|
| `make fmt` | Auto-format code (ruff + black + isort) |
| `make lint` | Check code quality (runs in pre-commit hook) |
| `make sh` | Open shell inside Docker container |
| `make hook-install` | Install git pre-commit hook |

## 📁 Project Structure
```
cashpilot/
├── src/
│   └── cashpilot/          # Main application package
├── .githooks/              # Git hooks (pre-commit)
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── Makefile                # Development commands
├── pyproject.toml          # Python dependencies & tool configs
└── README.md               # This file
```

## 🔄 Development Workflow

1. Make changes in `src/`
2. Run `make fmt` to auto-format
3. Commit → pre-commit hook runs `make lint` automatically
4. If lint fails, fix issues and commit again

## 📚 Next Steps

- [ ] FastAPI integration (MIZ-6)
- [ ] Database setup with PostgreSQL
- [ ] Authentication endpoints
- [ ] Docker Compose with database service

## 👤 Author

**Luis F. Villalba** - Backend Developer  
[LinkedIn](https://linkedin.com/in/luis-fernando-villalba) | [GitHub](https://github.com/luifer-villalba)

---

*This project follows Python best practices and is designed as a portfolio piece for backend development roles.*
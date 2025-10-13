# 💰 CashPilot – Backend (Docker-only Setup)

## 🧭 Overview
CashPilot is a modern backend template for a personal or micro-business cash-flow tracker.

This initial setup (ticket MIZ-5) gives you:
- 🐳 **Docker-only environment** – no Python installed locally.
- 🧹 **Code quality tools** – `ruff`, `black`, and `isort` for linting and formatting.
- 🚫 **Git pre-commit hook** – automatically blocks commits if code quality checks fail.
- ⚙️ **Makefile** – simple commands for setup, formatting, linting, and hooks.
- 🧩 **src layout** – ready for FastAPI integration in the next ticket (MIZ-6).

---

## ⚙️ Quickstart

### 1️⃣ Build the image
```bash
docker compose build
```

### 2️⃣ Install the Git hook
```bash
make hook-install
```

### 3️⃣ Create the code base folder
```bash
mkdir -p src/cashpilot && touch src/cashpilot/__init__.py
```

### 4️⃣ Format and lint everything
```bash
make fmt
```

### 5️⃣ Commit your first setup
```bash
git add -A
git commit -m "chore: init docker-only toolchain with git hook"
```

---

## 🧪 Useful Commands

| Command | Description |
|----------|-------------|
| `make fmt` | Auto-fix and format code (ruff + black + isort). |
| `make lint` | Check code style without fixing (blocks commit if failing). |
| `make sh` | Open a shell inside the container for manual commands. |
| `make hook-install` | Installs the `.githooks/pre-commit` hook to Git. |

---

## 🚦 Pre-commit Hook Behavior
Each time you run `git commit`, the following happens automatically:

1. Docker runs `make lint` inside the container.  
2. If any check fails (`ruff`, `black`, `isort`), the commit is blocked.  
3. Run `make fmt` to auto-fix and then commit again.

---

## 🧱 Project Structure
```
cashpilot/
├─ src/
│  └─ cashpilot/__init__.py
├─ .githooks/pre-commit
├─ Dockerfile
├─ docker-compose.yml
├─ Makefile
├─ pyproject.toml
└─ README.md
```

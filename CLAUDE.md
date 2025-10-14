# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CashPilot is a FastAPI-based backend for a personal/micro-business cash-flow tracker. The project uses a **Docker-only development environment** — no local Python installation required. All development commands run inside Docker containers.

## Development Commands

All commands are executed via the Makefile and run inside Docker:

- **Build the Docker image**: `docker compose build`
- **Format code**: `make fmt` (auto-fixes with ruff, black, isort)
- **Lint code**: `make lint` (checks without fixing — used by pre-commit hook)
- **Run FastAPI server**: `make run` (starts uvicorn on port 8000)
- **Run tests**: `make test` (runs pytest)
- **Open shell in container**: `make sh` (for manual commands)
- **Install git hook**: `make hook-install` (sets up pre-commit linting)

## Architecture

### Application Factory Pattern

The FastAPI application uses a factory pattern in `src/cashpilot/main.py`:

- `create_app()` function returns a fresh FastAPI instance
- This enables clean test isolation, different configurations per environment, and easier dependency injection
- When running the server directly, it calls `create_app()` and passes the result to uvicorn

### Source Layout

- Uses `src/` layout with the package under `src/cashpilot/`
- `PYTHONPATH=/app/src` is set in docker-compose.yml
- Package is installed in editable mode inside the Docker image
- To run the app: `make run` which executes `python -m src.cashpilot.main`

### Code Quality

The project enforces code quality through:

- **Pre-commit hook** (`.githooks/pre-commit`): automatically runs `make lint` before each commit and blocks if it fails
- **Linters**: ruff (E, W, F, I, N rules), black, isort
- **Configuration**: all tool configs in `pyproject.toml` with line length 100, Python 3.12 target

## Docker Workflow

Since this is a Docker-only setup:

1. **Never** invoke Python, pip, pytest, uvicorn, or linters directly from the host
2. **Always** use Make commands which wrap `docker compose run --rm app ...`
3. Code changes are immediately available via volume mount (`./:/app`)
4. The container has both runtime deps (FastAPI, uvicorn) and dev deps (pytest, ruff, black, isort)

## Running the Server

The server runs via `make run` which maps port 8000:8000. The `/health` endpoint returns `{"status": "ok"}`.

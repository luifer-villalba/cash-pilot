.PHONY: fmt lint sh hook-install run test

fmt:
	docker compose run --rm app bash -lc "black src && isort src && ruff format src && ruff check --fix --unsafe-fixes src"

lint:
	docker compose run --rm app bash -lc "ruff check src && black --check src && isort --check-only src"

sh:
	docker compose run --rm app bash

hook-install:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo '✔ Hook pre-commit instalado (docker-only).'

# Run the FastAPI server with uvicorn
run:
	docker compose run --rm --service-ports app uvicorn cashpilot.main:create_app --factory --reload --host 0.0.0.0 --port 8000

# Pytest (when we add tests)
test:
	docker compose run --rm app bash -lc "pytest -q"

# Alembic migration commands
migrate-create:
	@read -p "Migration name: " name; \
	docker compose exec app alembic revision --autogenerate -m "$$name"

migrate-up:
	docker compose exec app alembic upgrade head

migrate-current:
	docker compose exec app alembic current

migrate-history:
	docker compose exec app alembic history

migrate-downgrade:
	docker compose exec app alembic downgrade -1

# Clean rebuild (use when things get weird)
rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "✅ Clean rebuild complete"

# Quick rebuild (faster, for dependency changes)
rebuild-quick:
	docker compose down
	docker compose build
	@echo "✅ Quick rebuild complete"

check-sync:
	@echo "Checking file sync..."
	docker compose exec app ls -la /app/src/cashpilot/
	@echo ""
	@echo "If files are missing, run: make rebuild"
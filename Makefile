.PHONY: fmt lint sh hook-install run dev restart up down logs watch dev-watch test \
        migrate-create migrate-up migrate-current migrate-history migrate-downgrade \
        check-db rebuild rebuild-quick check-sync

# ---------- Code quality ----------
fmt:
	docker compose run --rm app bash -lc "black src && isort src && ruff format src && ruff check --fix --unsafe-fixes src"

lint:
	docker compose run --rm app bash -lc "ruff check src && black --check src && isort --check-only src"

# ---------- Utilities ----------
sh:
	docker compose exec app bash

hook-install:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo '✔ Pre-commit hook installed.'

# ---------- Run ----------
run dev:
	@echo "🚀 Starting development environment..."
	docker compose down --remove-orphans
	docker compose up -d db app
	@echo "➡️  App available at: http://127.0.0.1:8000/docs"

reload:
	@echo "♻️  Forcing manual reload..."
	docker compose exec app bash -lc "touch /app/src/cashpilot/main.py"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app

# ---------- Compose Watch (requires v2.22+) ----------
watch:
	docker compose watch

dev-watch:
	@echo "🚀 Starting app + db and enabling Compose Watch..."
	docker compose up -d db app
	docker compose watch

# ---------- Tests ----------
test:
	docker compose run --rm app bash -lc "pytest -q"

# ---------- Alembic migrations ----------
migrate-create:
	@read -p "Migration name: " name; \
	docker compose exec app alembic revision --autogenerate -m "$$name"

migrate-upgrade:
	docker compose exec app alembic upgrade head

migrate-current:
	docker compose exec app sh -c "cd /app && alembic current"

migrate-history:
	docker compose exec app alembic history

migrate-downgrade:
	docker compose exec app alembic downgrade -1

# ---------- Database ----------
check-db:
	@echo "📋 Listing tables..."
	docker compose exec db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "\dt"'
	@echo "🧩 Current Alembic version:"
	docker compose exec db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "SELECT * FROM alembic_version;"'

# ---------- Rebuild ----------
rebuild:
	@echo "🧱 Clean rebuild..."
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "✅ Clean rebuild complete."

rebuild-quick:
	@echo "⚙️ Quick rebuild..."
	docker compose down
	docker compose build
	@echo "✅ Quick rebuild complete."

# ---------- Sync diagnostics ----------
check-sync:
	@echo "🔍 Verifying synced files inside the container..."
	docker compose exec app ls -la /app/src/cashpilot/
	@echo ""
	@echo "👉 If files are missing: make rebuild"
	@echo "👉 If everything looks good but app is stale: make restart"
	@echo "✅ Sync check complete."
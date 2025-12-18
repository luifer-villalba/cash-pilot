# File: Makefile

.PHONY: fmt lint sh hook-install run dev up down logs watch dev-watch test \
        migrate-create migrate-upgrade migrate-current migrate-history migrate-downgrade \
        check-db rebuild rebuild-quick fix-perms clean-branches seed seed-reset \
        createuser list-users i18n-extract i18n-init-es i18n-compile i18n-update \
        build-css watch-css favicons

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

fix-perms:
	@echo "🔧 Fixing file permissions in src/..."
	sudo chown -R $$USER:$$USER .
	chmod -R u+w src/
	@echo "✅ File permissions fixed"

# ---------- Git ----------
clean-branches:
	git branch -D $$(git branch | grep -v "main" | xargs)

# ---------- Run ----------
run dev:
	@echo "🎨 Building CSS..."
	@docker compose run --rm css-builder
	@echo "🚀 Starting development environment..."
	docker compose down --remove-orphans
	docker compose up -d db app
	@echo "✅ Services started (detached mode)"
	@echo "➡️  Dashboard: http://127.0.0.1:8000/"
	@echo "➡️  Swagger docs: http://127.0.0.1:8000/docs"

reload:
	@echo "♻️  Forcing manual reload..."
	docker compose exec app bash -lc "touch /app/src/cashpilot/main.py"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app

# ---------- Full Reset ----------
reset:
	@echo "🔥 Full reset: dropping everything, rebuilding, and starting..."
	docker compose down -v
	docker compose build --no-cache
	docker compose up -d db app
	@echo "✅ Reset complete"
	@echo "➡️  Dashboard: http://127.0.0.1:8000/"
	@echo "➡️  Swagger docs: http://127.0.0.1:8000/docs"

# ---------- Compose Watch ----------
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

# ---------- User Management ----------
create-user:
	docker compose exec app python -m cashpilot.scripts.create_user

assign-cashiers:
	docker compose exec app python -m cashpilot.scripts.assign_cashiers

list-users:
	docker compose exec db psql -U cashpilot -d cashpilot_dev -c "SELECT id, email, is_active, created_at FROM users ORDER BY created_at DESC;"

# ---------- Seed Data ----------
seed:
	@echo "🌱 Seeding demo data..."
	docker compose exec app python -m cashpilot.scripts.seed
	@echo "✅ Seed complete. Check output above for details."

seed-reset:
	@echo "⚠️  Dropping all data and re-seeding..."
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose exec db sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "TRUNCATE TABLE cash_sessions, businesses CASCADE;"'
	@$(MAKE) seed

# ---------- i18n / Translations ----------
i18n-extract:
	@echo "🌍 Extracting translatable strings..."
	docker compose exec app pybabel extract -F babel.cfg -o translations/messages.pot /app/

i18n-init-es:
	@echo "🌍 Initializing Spanish translations..."
	docker compose exec app pybabel init -i translations/messages.pot -d translations -l es_PY

i18n-compile:
	@echo "🌍 Compiling translations..."
	docker compose exec app pybabel compile -d translations

i18n-update:
	@echo "🌍 Updating Spanish translations from extracted strings..."
	docker compose exec app pybabel update -i translations/messages.pot -d translations -l es_PY

# ---------- CSS Build ----------
build-css:
	@echo "🎨 Building CSS..."
	docker compose run --rm css-builder
	@echo "✅ CSS built: static/css/main.css"

watch-css:
	@echo "👀 Watching CSS for changes..."
	docker compose run --rm css-builder npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --watch

# ---------- Favicons ----------
favicons:
	@echo "🎨 Generating favicons..."
	docker compose exec app python -m cashpilot.scripts.generate_favicons
	@echo "✅ Favicons generated in static/"

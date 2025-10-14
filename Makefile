.PHONY: fmt lint sh hook-install run test

fmt:
	docker compose run --rm app bash -lc "ruff check --fix src && ruff format src && isort src && black src"

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
	docker compose run --rm --service-ports app python -m src.cashpilot.main

# Pytest (when we add tests)
test:
	docker compose run --rm app bash -lc "pytest -q"
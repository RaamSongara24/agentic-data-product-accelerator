.PHONY: dev db db-stop migrate verify test lint clean help

dev: ## Start FastAPI development server
	@echo "==> Starting FastAPI app on :8000"
	uv run uvicorn agentic_data_product.app.main:app --reload --host 0.0.0.0 --port 8000

db: ## Start PostgreSQL with Docker Compose
	@echo "==> Starting PostgreSQL container"
	docker compose up -d postgres

db-stop: ## Stop PostgreSQL Docker Compose service
	@echo "==> Stopping PostgreSQL container"
	docker compose stop postgres

migrate: ## Apply database migrations
	@echo "==> Applying migrations"
	uv run adp-migrate

test: ## Run all tests (unit + integration if PostgreSQL running)
	@set -e; \
	echo "==> Running unit tests"; \
	uv run pytest tests/unit -q; \
	if docker compose ps postgres 2>/dev/null | rg -q "Up|running|healthy"; then \
		echo "==> PostgreSQL detected; running integration tests"; \
		uv run pytest tests/integration -q -m integration; \
	else \
		echo "==> PostgreSQL not running; skipping integration tests"; \
	fi

lint: ## Run Ruff lint + format check + MyPy
	@set -e; \
	echo "==> Running Ruff lint"; \
	uv run ruff check .; \
	echo "==> Running Ruff format check"; \
	uv run ruff format --check .; \
	echo "==> Running MyPy"; \
	uv run mypy src

verify: ## Run full validation suite with summary
	@set -e; \
	STATUS="PASS"; \
	echo "==> [1/5] Ruff lint"; \
	if ! uv run ruff check .; then STATUS="FAIL"; fi; \
	echo "==> [2/5] Ruff format check"; \
	if ! uv run ruff format --check .; then STATUS="FAIL"; fi; \
	echo "==> [3/5] MyPy"; \
	if ! uv run mypy src; then STATUS="FAIL"; fi; \
	echo "==> [4/5] Unit tests"; \
	if ! uv run pytest tests/unit -q; then STATUS="FAIL"; fi; \
	echo "==> [5/5] Integration tests"; \
	if docker compose ps postgres 2>/dev/null | rg -q "Up|running|healthy"; then \
		if ! uv run pytest tests/integration -q -m integration; then STATUS="FAIL"; fi; \
	else \
		echo "PostgreSQL not running; integration tests skipped."; \
	fi; \
	echo ""; \
	if [ "$$STATUS" = "PASS" ]; then \
		echo "Validation summary: PASS"; \
	else \
		echo "Validation summary: FAIL"; \
		exit 1; \
	fi

clean: ## Remove temporary and cache files
	@echo "==> Cleaning cache and temp files"
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf tests/**/__pycache__ src/**/__pycache__
	rm -f tests/**/*.pyc src/**/*.pyc

help: ## List available commands
	@echo "Available commands:"; \
	awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

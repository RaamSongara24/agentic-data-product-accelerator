.PHONY: sync lint format typecheck test test-unit test-integration up down run health

sync:
	uv sync --group dev

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy src

test-unit:
	uv run pytest tests/unit -q

test-integration:
	uv run pytest tests/integration -q -m integration

test: test-unit

up:
	docker compose up -d --build

down:
	docker compose down

run:
	uv run uvicorn agentic_data_product.app.main:app --reload --host 0.0.0.0 --port 8000

health:
	curl -sf http://127.0.0.1:8000/health | python3 -m json.tool
	curl -sf http://127.0.0.1:8000/ready | python3 -m json.tool

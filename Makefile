install:
	uv venv && uv pip install -e ".[dev]"

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

format:
	uv run ruff format .

run:
	uv run uvicorn app.main:app --reload

.PHONY: install test lint format run

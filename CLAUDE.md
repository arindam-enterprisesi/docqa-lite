# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

DocQA-lite is a deliberately tiny FastAPI training starter for an "AI-Autonomous SDLC" hands-on session. The goal is to use GitHub Spec Kit (`/speckit.constitution` → `/speckit.specify` → `/speckit.clarify` / `plan` / `tasks` / `analyze` → `/speckit.implement`) to build a **document library with search** (upload, list, get, search) on top of it, implemented tests-first, then reviewed by a subagent and submitted as a PR.

Search must use **TF-IDF via scikit-learn** — no LLM or external API calls — so tests stay fast and deterministic. No secrets/env vars are required.

## Commands

Tooling is `uv` (Python ≥ 3.11). All commands go through the Makefile:

```bash
make install   # uv venv && uv pip install -e ".[dev]"
make test      # uv run pytest -q
make lint      # uv run ruff check . && uv run ruff format --check .
make format    # uv run ruff format .
make run       # uv run uvicorn app.main:app --reload  (http://localhost:8000, docs at /docs)
```

Single test: `uv run pytest tests/test_main.py::test_root_returns_service_name -q`

`make install` uses `uv pip install`, which does not honor `uv.lock`; use `uv sync --extra dev` for locked versions.

## Architecture

- `app/main.py` defines the single `FastAPI` instance `app` (imported by uvicorn as `app.main:app` and by tests). Currently only `GET /` exists.
- `app/__init__.py` holds `__version__`, which is the single source for the version reported by the API.
- Tests use `fastapi.testclient.TestClient(app)` in-process (requires `httpx`, a dev dependency).
- `data/sample_docs/` contains five short Markdown policy documents (expense, IT security, leave, onboarding, travel) intended as the corpus for search features and tests.
- `scikit-learn` (search) and `python-multipart` (file uploads) are already declared dependencies but not yet used.
- setuptools packages only `app` (`[tool.setuptools] packages = ["app"]`); new code under other top-level packages won't be installed.

## Conventions

Ruff: line length 100, target py311, lint rules `E, F, I, B, UP` (import sorting enforced). `make lint` must pass, including the format check.

## Custom Rules

- Every Function gets a unit test
- No new dependency without prior authorization or asking
- Never read or edit .env files

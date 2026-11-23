# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DocQA-lite is a deliberately tiny FastAPI starter for an "AI-Autonomous SDLC" training session. The goal is to build a **document library with search** (upload, list, get, search) on top of it using GitHub Spec Kit (`/speckit.constitution` → `specify` → `clarify` → `plan` → `tasks` → `analyze` → `implement`), tests first, then AI review and a PR.

Search must use **TF-IDF via scikit-learn** — no LLM or API key — so tests stay fast and deterministic. `scikit-learn` and `python-multipart` (for uploads) are already declared dependencies but not yet used.

## Environment

The `.venv` was created from **WSL (Linux)**; run all commands inside WSL, not Windows PowerShell. If `uv` isn't found: `source $HOME/.local/bin/env`.

## Commands

```bash
make install   # uv venv && uv pip install -e ".[dev]"
make test      # uv run pytest -q
make lint      # uv run ruff check . && uv run ruff format --check .
make format    # uv run ruff format .
make run       # uv run uvicorn app.main:app --reload  -> http://localhost:8000 (/docs for OpenAPI)
```

Single test: `uv run pytest tests/test_main.py::test_root_returns_service_name -q`

Ruff: line length 100, target py311, rules `E F I B UP` (includes import sorting). Python >= 3.11.

## Permissions

`.claude/settings.json` pre-allows `make`, `pytest`, `ruff` (bare or via `uv run`) and `git status`/`diff`/`log`; it denies reading `.env` / `.env.*` files and `git push`. Don't try to work around the denials — ask the user to push.

## Structure

- `app/main.py` — `create_app(sample_dir)` factory plus module-level `app = create_app()`. A lifespan
  handler loads `data/sample_docs/*.md` and `*.markdown` into the repository and builds the search index on
  `app.state` (`repository`, `index`, `lock`). Endpoints: `GET /`, `GET /health`,
  `POST /documents` (multipart `file`), `GET /documents`, `GET /documents/{id}`, `GET /search?q=&k=`.
- `app/repository.py` — frozen `Document` dataclass, `DocumentRepository` Protocol,
  `InMemoryDocumentRepository` (swap storage here).
- `app/ingest.py` — upload validation (`sanitize_filename`, `check_extension`, `decode_upload`,
  raising `UploadRejected` → 413/415/422), `extract_title`, `load_sample_dir`.
- `app/search.py` — `SearchIndex` (TF-IDF + cosine, rebuilt on every upload) and `make_snippet`.
- `app/models.py` — pydantic v2 response models.
- `app/__init__.py` — `__version__`, the single source of the version used by the API.
- `tests/` — pytest, in-process. Library tests MUST use the `client` / `make_client` fixtures from
  `tests/conftest.py` (they enter `TestClient(create_app())` as a context manager so the lifespan
  runs); a bare `TestClient(app)` skips start-up and has no documents. Use
  `tests/helpers.server_log_text` for "never logged" assertions (it ignores the client's httpx logs).
  `DOCQA_PERF=1` enables the wall-clock search benchmark, which is skipped by default.
- `data/sample_docs/` — five short Markdown policy docs (expense, IT security, leave, onboarding, travel) to use as the search corpus/test fixtures.
- `specs/001-document-library-search/` — spec, plan, research, data model, contract, tasks for the
  document library feature. Ruff excludes `.specify/` (vendored Spec Kit scripts).

The first test run takes ~50 s to import scikit-learn/scipy from `/mnt/c`; cloning the repo into
the WSL filesystem (e.g. `~/`) makes this much faster.

The `StarletteDeprecationWarning` about `httpx` during tests comes from FastAPI's TestClient import and is harmless.

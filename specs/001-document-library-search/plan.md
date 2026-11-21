# Implementation Plan: Document Library with Search

**Branch**: `001-document-library-search` (spec dir; the current git branch is `day-practice`) |
**Date**: 2026-11-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-document-library-search/spec.md`

## Summary

Add an in-memory document library to the existing FastAPI app:

- upload `.md`, `.markdown` and `.txt` files (at most 1 MB each, at most 100 documents in total)
- list documents, and fetch one by id
- search with TF-IDF and cosine similarity, returning the top k results with a score and a snippet

At start-up the five sample documents are loaded through a FastAPI `lifespan` handler. Storage is a
small, thread-safe repository class that route handlers reach through a FastAPI dependency, so it
can be swapped later. The TF-IDF index (scikit-learn `TfidfVectorizer`) is rebuilt synchronously
after each upload. Requests and responses are pydantic v2 models. Development is tests-first with
pytest and `TestClient`.

## Technical Context

**Language/Version**: Python 3.11 (`requires-python >= 3.11`)

**Primary Dependencies**: FastAPI 0.165, pydantic 2.14, scikit-learn 1.9 (`TfidfVectorizer`,
`cosine_similarity`), python-multipart (upload parsing). All of these are already declared;
**no new dependencies**.

**Storage**: In-process memory only (`dict` behind `InMemoryDocumentRepository`). Nothing is written
to disk (FR-018).

**Testing**: pytest + `fastapi.testclient.TestClient` (httpx), used as a context manager so the
lifespan runs.

**Target Platform**: Linux/macOS/WSL dev machine; `uvicorn` through `make run`

**Project Type**: Single web service (one FastAPI app)

**Performance Goals**: Search returns in under 1 second with 100 documents (SC-003); an upload is
searchable on the next request (SC-004)

**Constraints**: No network or LLM calls; deterministic results; at most 1 MB per file and at most
100 documents; never log document content or query text; the test suite runs in under 30 seconds

**Scale/Scope**: At most 100 documents (about 100 MB at worst); 4 new endpoints; one user (training)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Pre-design | Post-design |
|-----------|-------|-----------|-------------|
| I. Fixed stack | Python 3.11, FastAPI single `app`, pydantic v2 models, code under `app/` | ✅ | ✅ All new modules live in `app/`; schemas use pydantic v2 `BaseModel`/`Field` |
| II. Test-first | Tests written before code; every function unit-tested; in-process and deterministic; `make test` + `make lint` must pass | ✅ | ✅ One test module per source module (see Structure); lifespan gives each test a fresh library; no randomness in assertions (ids aren't asserted by value) |
| III. Simplicity | No database server, no external API, no new service; abstractions justified | ✅ | ⚠️ The repository class is an extra abstraction. It was requested by the user and is justified under Complexity Tracking. No Protocol or DI framework is added. |
| IV. Secure by default | Inputs validated at the boundary; errors are 4xx; no content, queries or secrets in logs; filenames never become paths | ✅ | ✅ R4 sets the validation order and status codes; R5 reduces filenames to a basename; R8 redacts `?q=` from uvicorn access logs |
| V. Justified dependencies | No new dependency without plan justification and approval | ✅ | ✅ None added |

**Gate result**: PASS (one justified item, see below).

## Project Structure

### Documentation (this feature)

```text
specs/001-document-library-search/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R9
├── data-model.md        # Phase 1: entities, schemas, components
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   └── http-api.md      # Phase 1: endpoint contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
app/
├── __init__.py          # __version__ (unchanged)
├── main.py              # + lifespan, dependencies, /documents and /search routes
├── config.py            # NEW limits and paths (data-model.md § Constants)
├── models.py            # NEW Document, SearchResult, pydantic API schemas
├── text.py              # NEW safe_filename, derive_title, has_allowed_extension, decode_utf8
├── repository.py        # NEW InMemoryDocumentRepository, LibraryFullError
├── search.py            # NEW SearchIndex (rebuild, search, snippet)
├── loader.py            # NEW load_sample_documents
└── logging_filters.py   # NEW RedactQueryFilter

tests/
├── conftest.py              # NEW `client` fixture (with TestClient(app))
├── test_main.py             # existing
├── test_health.py           # existing
├── test_text.py             # NEW unit
├── test_repository.py       # NEW unit
├── test_search_index.py     # NEW unit (scores, ordering, snippet, empty index)
├── test_loader.py           # NEW unit (tmp_path fixtures, missing/unreadable file)
├── test_logging_filters.py  # NEW unit
├── test_documents.py        # NEW API: upload, list, get (US2, US3)
└── test_search.py           # NEW API: search (US1)
```

**Structure Decision**: A flat set of modules inside the existing `app` package. It's the only
package setuptools installs, and the feature is small enough that sub-packages would only add
indirection. Tests mirror the modules one to one: one file for each source module plus one for each
API area.

## Design Overview

1. **Start-up**: the `lifespan` handler creates a repository and an index on `app.state`, calls
   `load_sample_documents(SAMPLE_DOCS_DIR)`, adds each document, calls
   `index.rebuild(repo.list())`, and installs `RedactQueryFilter` on `uvicorn.access`.
2. **Upload**: validate (R4), build a `Document` (R5), call `repo.add` (which may raise
   `LibraryFullError`, mapped to 409), call `index.rebuild(repo.list())`, and return 201 with a
   `DocumentSummary`. Rebuilding is guarded by the index's own lock so that a search never sees a
   half-built index.
3. **Search**: validate `q` and `k` with `Query(...)` constraints plus an explicit check that `q`
   isn't blank after trimming, then call `index.search(q, k)` (R2) and attach snippets (R6).
4. **List / Get**: read straight from the repository; return 404 for an unknown id.

See [research.md](./research.md) for the reasoning behind each choice and
[contracts/http-api.md](./contracts/http-api.md) for status codes.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Repository class (Constitution III, extra abstraction) | The user explicitly asked for swappable storage. The class gives one seam (`get_repository` dependency) to replace in-memory storage later, and keeps the lock and the 100-document cap in one place. | A module-level dict can't be overridden through `dependency_overrides`, spreads the cap and lock logic across handlers, and leaks state between tests. |

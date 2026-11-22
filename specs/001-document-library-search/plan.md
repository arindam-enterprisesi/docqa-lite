# Implementation Plan: Document Library with Search

**Branch**: `001-document-library-search` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-document-library-search/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Add an in-memory document library to the existing FastAPI app: upload a `.md`/`.markdown`/`.txt`
file (≤ 1 MB, UTF-8), list documents, fetch one by id, and search with a text query that returns
the top k (1–20, default 5) documents with a 0–1 relevance score and a ≤ 200-char snippet. The
five files in `data/sample_docs/` load at start-up. Storage sits behind a small
`DocumentRepository` Protocol (one in-memory implementation) so it can be swapped later. Search
uses scikit-learn `TfidfVectorizer` + cosine similarity, and the index is rebuilt after every
upload. Request/response shapes are pydantic v2 models; tests are pytest + `TestClient` against
an app factory so every test gets an isolated library. See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (ruff target py311)

**Primary Dependencies**: FastAPI 0.165, pydantic 2.14, scikit-learn 1.9 (TfidfVectorizer,
linear_kernel), python-multipart (uploads), uvicorn; all already declared in `pyproject.toml`

**Storage**: In-process memory (`InMemoryDocumentRepository`, dict in insertion order); no
persistence across restarts

**Testing**: pytest + `fastapi.testclient.TestClient` used as a context manager on
`create_app()` (runs the lifespan, fresh state per test); unit tests for repository, ingest
helpers and search index

**Target Platform**: Linux (WSL) dev machine; uvicorn ASGI server

**Project Type**: web-service (single FastAPI app, API only)

**Performance Goals**: search over ≤ 1,000 docs answers in < 1 s (SC-004); index rebuild on upload
in well under 1 s at that size

**Constraints**: no network/external API, no DB server, no new dependencies, deterministic
results, never log document content or query text, 1 MB upload cap enforced by a bounded read

**Scale/Scope**: ≤ ~1,000 short English documents; 4 new endpoints; ~5 small modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|-----------|------|:------------:|:-----------:|
| I. Fixed Technology Stack | Python 3.11, FastAPI, pydantic v2 models for all request/response bodies; ruff clean | ✅ | ✅ `app/models.py` uses `BaseModel`/`ConfigDict` only |
| II. Test-First | Tests written first and seen failing; in-process `TestClient`; deterministic; `make test` green | ✅ | ✅ Test modules listed below; app factory isolates state; scores rounded; stable tie-break |
| III. Keep It Simple | No DB server, no external calls, no new service; abstractions justified | ✅ | ✅ In-memory only; TF-IDF local. Repository Protocol justified in Complexity Tracking |
| IV. Secure by Default | All inputs validated → 4xx; no path traversal; no content/secrets in logs | ✅ | ✅ Bounded read (413), extension allow-list (415), UTF-8/empty (422), q/k limits (422); filename basename only, never a path; logs carry id/filename/size only (R9) |
| V. Justified Dependencies | No new dependency without justification | ✅ | ✅ None added (R10) |

**Result**: PASS, no unjustified violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-document-library-search/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: entities + validation rules
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   └── openapi.yaml     # Phase 1: HTTP contract for the 4 new endpoints
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
app/
├── __init__.py          # __version__ (unchanged)
├── main.py              # create_app(sample_dir) factory, lifespan loads samples, routes; app = create_app()
├── models.py            # pydantic v2: DocumentSummary, DocumentOut, SearchHit, SearchResponse
├── repository.py        # Document record, DocumentRepository Protocol, InMemoryDocumentRepository
├── ingest.py            # sanitize_filename, validate/decode upload bytes, extract_title, load_sample_dir
└── search.py            # SearchIndex: rebuild(docs), search(q, k) -> hits; make_snippet

tests/
├── conftest.py          # fixtures: client (with TestClient(create_app()) as c), tmp sample dirs
├── test_main.py         # existing / and /health tests (unchanged)
├── test_repository.py   # add/get/list, insertion order, unknown id
├── test_ingest.py       # filename sanitising, extension allow-list, size/empty/UTF-8, title rules
├── test_search.py       # ranking on samples, k limit, zero-score exclusion, stop-word query,
│                        # empty corpus, tie order, snippet length/relevance, determinism
├── test_api_documents.py  # start-up load, upload 201/413/415/422, list, get 200/404
└── test_api_search.py     # /search happy paths, new upload searchable, q/k validation 422
```

**Structure Decision**: Single project. The new modules live in the existing `app/` package
(`[tool.setuptools] packages = ["app"]`, so no packaging change), and tests sit flat in `tests/`
next to the existing `test_main.py`. Routes stay in `main.py`; the feature is too small to need
routers.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `DocumentRepository` Protocol + one implementation (an abstraction under Principle III) | The user asked for storage that can be swapped later (e.g., SQLite or files) without touching routes or search | A module-level dict would make swapping a rewrite and would leak state between tests; the Protocol is about 10 lines and adds no dependency |

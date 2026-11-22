# feat: document library with TF-IDF search

Spec: [`specs/001-document-library-search/spec.md`](specs/001-document-library-search/spec.md)
(plan: [`plan.md`](specs/001-document-library-search/plan.md),
tasks: [`tasks.md`](specs/001-document-library-search/tasks.md),
contract: [`contracts/`](specs/001-document-library-search/contracts/))

## What was built

- `POST /documents` — multipart upload; returns 201 with metadata. Validates extension (415),
  size up to 1 MiB (413) and encoding (422); sanitizes filenames; derives the title.
- `GET /documents` and `GET /documents/{id}` — list and fetch, 404 for unknown ids.
- `GET /search?q=&k=` — TF-IDF + cosine similarity via scikit-learn (no LLM or API key).
  `q` is 1–500 chars, `k` is 1–20 (default 5). Scores are rounded and capped at 1,
  zero scores are dropped, ties are stable, and stop-word-only queries return `[]`.
- Start-up lifespan loads `data/sample_docs/*.md` and builds the index; the index is rebuilt on
  every upload.
- Modules: `app/repository.py` (Document, repository Protocol, in-memory store),
  `app/ingest.py`, `app/search.py`, `app/models.py`. `create_app(sample_dir)` factory in
  `app/main.py`.
- No new dependencies; `pyproject.toml` only adds a ruff exclude for `.specify/`.
- Adds Spec Kit artifacts (`specs/`, `.specify/`), `CLAUDE.md` and `.claude/` settings.

## How it was tested

- `make test`: 95 passed, 1 skipped (the `DOCQA_PERF` wall-clock benchmark for SC-004, skipped by
  default), 1 harmless httpx deprecation warning.
- `make lint`: ruff check and format check clean.
- Tests cover the repository, ingest validation, the search index, the documents and search
  APIs, and "never logged" checks for document content. Library tests use the `client` /
  `make_client` fixtures so the lifespan runs.

## Review findings

Reviewed by the `spec-reviewer` agent against the spec, plan and constitution.
Verdict: ready to merge. All 17 FRs are implemented and no constitution violations were found.

Open items, all minor:

1. Oversized uploads are fully received and spooled by Starlette before the 413 check
   (`app/main.py:59-64`). The limit is enforced, just late. A Content-Length precheck would fix it.
2. Repository reads are not guarded by the lock that uploads use. Unlikely to matter in CPython.
3. Some tests assert only status codes and that `detail` is present, not message text (415
   accepted types, 413 limit, whitespace-only query, and similar).
4. SC-004 (1,000 docs in under 1 s) rests on the skipped benchmark, which was not run.
5. Not reviewed: `contracts/openapi.yaml`, `data-model.md` and `quickstart.md` field-level
   conformance.
6. Nits: undeclared direct numpy/scipy imports in `app/search.py:217-218` (the scipy one is
   annotation-only); a literal BOM character in `app/ingest.py:196`; a bare `TestClient(app)`
   in `tests/test_main.py:6`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

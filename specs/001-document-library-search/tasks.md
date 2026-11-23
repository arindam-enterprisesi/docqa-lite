---

description: "Task list for feature 001-document-library-search"
---

# Tasks: Document Library with Search

**Input**: Design documents from `/specs/001-document-library-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: REQUIRED. Constitution Principle II (Test-First, NON-NEGOTIABLE) overrides the
template's "tests are optional" default. In every phase, the test tasks come first and MUST be run
and seen to FAIL before the implementation tasks that follow them.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

## Path Conventions

Single project per plan.md: application code in `app/`, tests flat in `tests/`.
References such as "research R5" point to sections of `research.md`; "data-model.md
`Document.size`" points to that entity field's row in `data-model.md`.

**Test client rule (research R4)**: every library test MUST use
`with TestClient(create_app(...)) as client:` (via the fixtures from T002). A bare
`TestClient(app)` does not run the lifespan, so the sample docs never load.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm a green baseline and add shared test fixtures

- [X] T001 Run `make test` and `make lint` on the unchanged repo and confirm both pass (baseline for `tests/test_main.py` and `app/main.py`)
- [X] T002 Create `tests/conftest.py` with fixtures: `sample_dir` (absolute path to `data/sample_docs`), `make_sample_dir` (factory writing given `{filename: bytes}` into `tmp_path` and returning the directory), and `client` / `make_client` that yield `with TestClient(create_app(sample_dir=...)) as c:`; import `create_app` *inside* the fixtures so collection works before it exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Document record, repository, sample loading, pydantic response models, app factory.
Every story needs these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests (write first, confirm they fail)

- [X] T003 [P] Write `tests/test_repository.py`: `InMemoryDocumentRepository.add` then `get` returns the same Document; `get` of an unknown id returns `None`; `list()` returns documents in insertion order; `Document` is immutable (assigning to a field raises)
- [X] T004 [P] Write foundational tests in `tests/test_ingest.py`: `extract_title` returns the first `# ` heading text (ignores `##`), falls back to the filename stem, truncates to 200 chars; `load_sample_dir(sample_dir)` returns 5 Documents sorted by filename, each with `source == "sample"`, `size` equal to the file's byte length and the expected titles (e.g., "Annual Leave Policy"); a directory containing one non-UTF-8 `.md` file plus one valid file loads only the valid one and logs the skipped filename (use `caplog`; assert the bad file's bytes/text are not in any log record); a missing directory returns `[]`
- [X] T005 [P] Write `tests/test_app.py`: inside `with TestClient(create_app()) as c`, `c.app.state.repository.list()` holds the 5 samples; `create_app(sample_dir=<empty tmp dir>)` starts with 0 documents; two apps from `create_app()` do not share repository state; existing `GET /` and `GET /health` still return 200

### Implementation

- [X] T006 [P] Implement `app/repository.py`: frozen dataclass `Document` with fields per data-model.md `Document.id`, `Document.title`, `Document.filename`, `Document.size`, `Document.content`, `Document.source` (use `Literal["sample", "upload"]` for `Document.source`); `DocumentRepository` `typing.Protocol` with `add(doc) -> None`, `get(doc_id) -> Document | None`, `list() -> list[Document]`; `InMemoryDocumentRepository` backed by an insertion-ordered dict (research R3)
- [X] T007 Implement `extract_title(content, filename)` and `load_sample_dir(path) -> list[Document]` in `app/ingest.py`: title per data-model.md `Document.title`; samples get `uuid4().hex` ids per data-model.md `Document.id` and `source="sample"` per data-model.md `Document.source`; load `*.md` and `*.markdown` (case-insensitive) sorted by filename; pass each through the upload size/UTF-8/non-empty gate, skip failing or unreadable files and log `sample_skipped filename=<name>` with the status or exception class only via `logging.getLogger("docqa")` (research R9) (depends on T006)
- [X] T008 [P] Implement pydantic v2 models in `app/models.py`: `DocumentSummary` (fields per data-model.md `Document.id`, `Document.title`, `Document.filename`, `Document.size`, `Document.source`), `DocumentOut(DocumentSummary)` adding data-model.md `Document.content`, `SearchHit` (data-model.md `SearchHit.id`, `SearchHit.title`, `SearchHit.score`, `SearchHit.snippet`), `SearchResponse` (`query: str`, `k: int`, `results: list[SearchHit]`) matching `contracts/openapi.yaml` schemas; use `ConfigDict(frozen=True)`, no pydantic v1 APIs
- [X] T009 Refactor `app/main.py` into `create_app(sample_dir: Path | None = DEFAULT_SAMPLE_DIR) -> FastAPI` with a `lifespan` that builds an `InMemoryDocumentRepository`, loads `load_sample_dir(sample_dir)` into it, and stores it on `app.state.repository` together with `app.state.lock = threading.Lock()`; keep `GET /` and `GET /health` unchanged; keep the module-level `app = create_app()`; `DEFAULT_SAMPLE_DIR` resolves `data/sample_docs` relative to the repo root, not the CWD (depends on T006, T007)

**Checkpoint**: `uv run pytest tests/test_repository.py tests/test_ingest.py tests/test_app.py tests/test_main.py -q` passes. Samples load at start-up (FR-001, SC-001).

---

## Phase 3: User Story 1 - Search the policy library (Priority: P1) 🎯 MVP

**Goal**: `GET /search?q=&k=` ranks documents by TF-IDF relevance and returns up to k hits, each
with a score and a snippet.

**Independent Test**: With no uploads, `GET /search?q=annual%20leave` returns "Annual Leave Policy"
first with 0 < score ≤ 1 and a snippet of ≤ 200 chars; `q=zebra` returns `[]`.

### Tests for User Story 1 (write first, confirm they fail) ⚠️

- [X] T010 [P] [US1] Write ranking tests in `tests/test_search.py` against a `SearchIndex` rebuilt from `load_sample_dir(sample_dir)`: "annual leave" → Leave Policy first; "receipt reimbursement" with k=2 → ≤ 2 hits, Expense first, scores descending; "zebra" → `[]`; "the and of" → `[]`; each of the 5 sample docs is the top hit for a distinctive phrase from it (SC-002); all scores are in (0, 1] with ≤ 4 decimals; the same query twice gives identical hits (SC-006); two identical-content docs tie and come back in insertion order; `rebuild([])` and a stop-word-only corpus (e.g., one doc "the and of") don't raise and every search returns `[]`
- [X] T011 [US1] Add snippet tests to `tests/test_search.py`: `make_snippet` output is ≤ 200 chars, contains a query term (case-insensitive) when the doc has one, never starts with `#`, ends with "…" only when truncated, cuts at a word boundary, and falls back to the first non-heading passage when no term matches (same file as T010, so run it after T010)
- [X] T012 [P] [US1] Write `tests/test_api_search.py` using the `client` fixture: `q=annual leave` → 200, first `results[0].title == "Annual Leave Policy"`, body has `query`, `k`, `results` with `id/title/score/snippet`; `k` omitted → response `k == 5`; `k=2` → ≤ 2 results; `q=zebra` → `results == []`; 422 for: missing `q`, `q` of only spaces, `q` of 501 chars, `k=0`, `k=21`, `k=abc`; `query` in the response is whitespace-trimmed; with `caplog` at DEBUG, the query text appears in no log record

### Implementation for User Story 1

- [X] T013 [US1] Implement `SearchIndex` in `app/search.py` per research R1/R2/R8: `rebuild(documents)` fits `TfidfVectorizer(stop_words="english", sublinear_tf=True)` and stores one immutable snapshot `(vectorizer, matrix, doc_ids, titles)` in a single attribute; on `ValueError` (empty vocabulary) or no docs it stores an empty snapshot; `search(query, k) -> list[SearchHit]` scores with `linear_kernel`, drops scores ≤ 0, sorts stably by score descending (ties keep insertion order), keeps the top k, rounds per data-model.md `SearchHit.score`, and fills data-model.md `SearchHit.id` and `SearchHit.title` (depends on T008)
- [X] T014 [US1] Implement `make_snippet(content, query_terms) -> str` in `app/search.py` per research R7 and data-model.md `SearchHit.snippet`; get query terms from the snapshot vectorizer's `build_analyzer()` so stop words/lowercasing match ranking; call it from `SearchIndex.search` (depends on T013)
- [X] T015 [US1] Wire search into `app/main.py`: in the lifespan, create `SearchIndex`, call `rebuild(repository.list())` and store it as `app.state.index`; add `GET /search` with `q: str = Query(min_length=1, max_length=500)` and `k: int = Query(5, ge=1, le=20)` per data-model.md "Request validation rules" (`q`, `k`); reject `q.strip() == ""` with `HTTPException(422, "Query must contain non-whitespace characters")`; return `SearchResponse(query=q.strip(), k=k, results=...)`; never log `q` (depends on T009, T014)

**Checkpoint**: `uv run pytest tests/test_search.py tests/test_api_search.py -q` passes; US1 works on its own (MVP).

---

## Phase 4: User Story 2 - Upload a new document (Priority: P2)

**Goal**: `POST /documents` accepts a valid `.md`/`.markdown`/`.txt` UTF-8 file of up to 1 MB,
assigns an id, and makes it searchable straight away.

**Independent Test**: Upload `# Quokka Care\nFeed the quokka daily.` as `q.md` → 201 with id and
title "Quokka Care"; then `GET /search?q=quokka` returns it first.

**Dependency note**: US2 rebuilds the US1 `SearchIndex` and its acceptance scenario 2 uses
`/search`, so it needs Phase 3 done (T013–T015).

### Tests for User Story 2 (write first, confirm they fail) ⚠️

- [X] T016 [P] [US2] Add upload-validation unit tests to `tests/test_ingest.py`: `sanitize_filename("../../etc/passwd.md") == "passwd.md"`, `"..\\..\\x.txt"` → `"x.txt"`, surrounding whitespace stripped, names longer than 255 chars rejected or truncated per data-model.md; extension check accepts `.md`, `.markdown`, `.txt` in any case and rejects `.pdf`, `.MD.exe`, and no extension; `decode_upload`: `b""` → empty error, 1,048,576 bytes accepted, 1,048,577 → too-large error, `b"\xff\xfe"` → encoding error, a UTF-8 BOM is stripped from the content while the size still counts the raw bytes
- [X] T017 [P] [US2] Write upload API tests in `tests/test_api_documents.py` using the `client` fixture (check library size via `client.app.state.repository.list()` so US2 tests don't depend on the US3 list endpoint): valid `.md` → 201 with `id`, `title` (from heading), `filename`, `size`, `source == "upload"`; `.txt` without heading → title is the filename stem; same file uploaded twice → 2 different ids; then `/search?q=quokka` → that doc is first (SC-003); 413 for a 1,048,577-byte file; 415 for `report.pdf`; 422 for an empty file, invalid UTF-8, and a request without a `file` field; after each rejection the document count is unchanged; filename `../../evil.md` comes back as `evil.md`; with `caplog` at DEBUG, the uploaded content appears in no log record

### Implementation for User Story 2

- [X] T018 [US2] Implement upload helpers in `app/ingest.py` per research R5: constants `MAX_BYTES = 1_048_576` and `ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt"}`; `sanitize_filename(raw) -> str` producing data-model.md `Document.filename`; `decode_upload(data: bytes) -> str` enforcing data-model.md `Document.size` and `Document.content` (non-empty, UTF-8, BOM stripped); raise a small `UploadRejected(status_code, detail)` exception carrying 413/415/422 and a human-readable reason that never includes file content
- [X] T019 [US2] Add `POST /documents` to `app/main.py` (status 201, `response_model=DocumentSummary`): take `file: UploadFile`; read at most `MAX_BYTES + 1` bytes; check the filename/extension and decode via T018 helpers and map `UploadRejected` to `HTTPException`; build a `Document` with a fresh id per data-model.md `Document.id`, title via `extract_title`, and `source="upload"` per data-model.md `Document.source`; under `app.state.lock`, `repository.add(doc)` then `index.rebuild(repository.list())`; log `document_added id=… filename=… size=…` only (depends on T015, T018)

**Checkpoint**: `uv run pytest tests/test_ingest.py tests/test_api_documents.py -q` passes; uploads become searchable.

---

## Phase 5: User Story 3 - Browse and read documents (Priority: P3)

**Goal**: `GET /documents` lists metadata for every document; `GET /documents/{id}` returns one
document with its full content, or 404.

**Independent Test**: Fresh start → `GET /documents` lists exactly the 5 samples without
`content`; `GET /documents/<an id from the list>` returns full content; `GET /documents/nope` → 404.

### Tests for User Story 3 (write first, confirm they fail) ⚠️

- [X] T020 [US3] Add list/get API tests to `tests/test_api_documents.py`: fresh `client` → `GET /documents` returns 5 items sorted by filename with keys exactly `{id, title, filename, size, source}` (no `content`) and the 5 expected titles; after an upload (via `POST /documents` or adding directly to `client.app.state.repository`) the list has 6 items with the new one last; `GET /documents/{id}` → 200 with `content` equal to the sample file's text; `GET /documents/does-not-exist` → 404 with a `detail` string (same file as T017, so not [P] with it)

### Implementation for User Story 3

- [X] T021 [US3] Add `GET /documents` (`response_model=list[DocumentSummary]`, repository insertion order) and `GET /documents/{document_id}` (`response_model=DocumentOut`, `HTTPException(404, "Document not found")` for an unknown id; don't echo the id into logs) to `app/main.py` (depends on T009)

**Checkpoint**: All three stories pass their tests independently; `make test` is green.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story guards, docs, quality gates

- [X] T022 [P] Write `tests/test_logging.py`: one `client` session that uploads a doc with a unique marker string, searches for it, and fetches it, with `caplog` at DEBUG for all loggers; assert the marker and the query text appear in no log record (FR-017, Principle IV)
- [X] T023 [P] Add a performance test to `tests/test_search.py`: build a `SearchIndex` over 1,000 deterministic synthetic documents (generated from a fixed word list, no randomness) and assert one `search` call finishes in < 1 s (SC-004)
- [X] T024 [P] Update the "Structure" section of `CLAUDE.md` with the new modules (`app/models.py`, `app/repository.py`, `app/ingest.py`, `app/search.py`), the 4 endpoints, and the `with TestClient(create_app())` test rule
- [X] T025 Run `make format`, then `make lint` and `make test`; fix everything until both pass with no failures
- [X] T026 Walk through the manual scenarios 1–14 and the log check in `specs/001-document-library-search/quickstart.md` against `make run` and record any deviation
- [ ] T027 Run an AI review of the full diff (e.g., `/code-review`), then address each finding or record why it was declined, in the PR description (constitution quality gate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: needs Setup; BLOCKS all stories
- **US1 (Phase 3)**: needs Foundational
- **US2 (Phase 4)**: needs Foundational **and US1** (rebuilds `SearchIndex`; acceptance uses `/search`)
- **US3 (Phase 5)**: needs Foundational only; can run in parallel with US1/US2 (shares
  `tests/test_api_documents.py` and `app/main.py` with US2, so coordinate edits)
- **Polish (Phase 6)**: needs all stories

### Task-level dependencies

- T006 → T007 → T009; T008 → T013 → T014 → T015
- T009 → T015, T021; T015 + T018 → T019
- Tests before implementation in each phase: T003–T005 before T006–T009; T010–T012 before
  T013–T015; T016–T017 before T018–T019; T020 before T021

### Story completion order

```text
Setup → Foundational ─┬─ US1 (P1, MVP) ── US2 (P2)
                      └─ US3 (P3)  (independent)
                                   └──────────── Polish
```

### Parallel Opportunities

- Phase 2 tests: T003, T004, T005 (three different files)
- Phase 2 implementation: T006 and T008 together; T007 after T006
- US1 tests: T010 (test_search.py) with T012 (test_api_search.py); T011 after T010
- US2 tests: T016 (test_ingest.py) with T017 (test_api_documents.py)
- US3 can be built alongside US1 (different test file from US1; `main.py` route additions are
  small, separate functions)
- Polish: T022, T023, T024 together

---

## Parallel Example: User Story 1

```bash
# Write US1 tests together (different files):
Task: "T010 ranking tests in tests/test_search.py"
Task: "T012 /search API tests in tests/test_api_search.py"

# Then, in order: T011 (snippet tests) → confirm red → T013 → T014 → T015 → confirm green
```

## Parallel Example: User Story 2

```bash
Task: "T016 upload-validation unit tests in tests/test_ingest.py"
Task: "T017 upload API tests in tests/test_api_documents.py"
# Then T018 → T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (samples load at start-up)
2. Phase 3 US1 → **STOP and VALIDATE**: quickstart scenarios 2–6
3. Demo: searchable policy library with zero uploads

### Incremental Delivery

1. Setup + Foundational → samples in memory
2. + US1 → search (MVP)
3. + US2 → uploads, searchable immediately
4. + US3 → browse and read
5. Polish → logging guard, performance check, docs, lint/test, quickstart, AI review, PR

---

## Notes

- [P] = different files, no dependency on incomplete tasks
- Red → Green → Refactor: run each test task and see it fail for the right reason before implementing
- Never log document content, snippets or query text (research R9)
- Commit after each phase checkpoint; a human pushes (git push is denied for the agent)

---

description: "Task list for Document Library with Search"
---

# Tasks: Document Library with Search

**Input**: Design documents from `specs/001-document-library-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: REQUIRED. Constitution II (Test-First, non-negotiable) and CLAUDE.md ("every function gets
a unit test") apply. Every test task comes before the code it covers and MUST be run and seen to
FAIL before that code is written.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as
its own increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1, US2, US3)
- Paths are relative to the repository root. Code goes in `app/` (the only installed package);
  tests go in `tests/`.

## Conventions for every task

- Test files use the `client` fixture from `tests/conftest.py` for API tests. Never use a bare
  `TestClient(app)`, because it skips the lifespan and no sample documents get loaded.
- Never assert on an id's value (ids are random `uuid4().hex`); assert on titles and filenames
  instead.
- Logging: ids, sizes, counts and status codes only. Never log document content, query text or
  snippets (FR-016).
- After each implementation task, `uv run pytest -q` for the touched test file must pass. At each
  checkpoint, `make test` and `make lint` must both pass.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the baseline and add shared configuration and test scaffolding.

- [X] T001 Confirm the baseline: run `uv sync --extra dev`, `make test` and `make lint` and check all pass on the unchanged repo. Do NOT modify dependencies in `pyproject.toml` (plan.md: no new dependencies) — NOTE: tests pass (2/2); `make lint` fails on 10 pre-existing errors in untracked `.specify/scripts/python/` (not in app/ or tests/)
- [X] T002 [P] Create `app/config.py` with the constants in data-model.md § Constants (`MAX_UPLOAD_BYTES`, `MAX_DOCUMENTS`, `ALLOWED_EXTENSIONS`, `DEFAULT_K`, `MIN_K`, `MAX_K`, `MAX_QUERY_CHARS`, `SNIPPET_CHARS`, `MAX_FILENAME_CHARS`, `SAMPLE_DOCS_DIR`). Compute `SAMPLE_DOCS_DIR` as `Path(__file__).resolve().parent.parent / "data" / "sample_docs"`
- [X] T003 [P] Create `tests/conftest.py` with a function-scoped `client` fixture: `with TestClient(app) as c: yield c` (research.md R7, R9)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Document` entity, the title helper, the repository, the sample loader and the
lifespan that loads the 5 samples. All three stories depend on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Write failing tests for `derive_title(content, filename)` in `tests/test_text.py`: the first `# ` heading is used even when it isn't on the first line; `## Sub` is ignored; `#NoSpace` is ignored; surrounding whitespace is stripped; no heading falls back to the filename stem for `.md`, `.markdown` and `.txt` (research.md R5)
- [X] T005 [P] Write failing tests for the `Document` model in `tests/test_models.py`: valid construction; `source` rejects values other than `"sample"`/`"upload"`; the instance is immutable (frozen)
- [X] T006 [P] Write failing tests for `InMemoryDocumentRepository` in `tests/test_repository.py`: `add` then `get` returns the same document; `get` of an unknown id returns `None`; `list` keeps insertion order; `count`; `clear`; `add` raises `LibraryFullError` once `count == max_documents` and leaves the count unchanged (construct with `max_documents=3` for the test, default `MAX_DOCUMENTS`)
- [X] T007 [P] Write failing tests for `load_sample_documents(directory)` in `tests/test_loader.py` using `tmp_path`: loads only `*.md`, sorted by filename; sets `source="sample"`, a derived title and `size_bytes` equal to the file's byte length; skips a file with invalid UTF-8 and loads the rest; a missing directory returns `[]` without raising; the real `SAMPLE_DOCS_DIR` yields exactly 5 documents
- [X] T008 [P] Write failing tests for start-up in `tests/test_app_startup.py`: inside the `client` fixture, `app.state.repository.count() == 5`; two separate `with TestClient(app)` blocks each start with exactly 5 documents (isolation, FR-018); `get_repository` returns `app.state.repository`
- [ ] T009 Implement `derive_title(content: str, filename: str) -> str` in `app/text.py` per data-model.md `Document.title` (make T004 pass)
- [ ] T010 Implement the frozen `Document` pydantic model in `app/models.py` per data-model.md `Document.id`, `Document.title`, `Document.filename`, `Document.size_bytes`, `Document.content`, `Document.source` (make T005 pass)
- [ ] T011 Implement `LibraryFullError` and a thread-safe `InMemoryDocumentRepository(max_documents: int = MAX_DOCUMENTS)` with `add`, `get`, `list`, `count` and `clear` behind a `threading.Lock` in `app/repository.py` (research.md R1; make T006 pass)
- [ ] T012 Implement `load_sample_documents(directory: Path) -> list[Document]` in `app/loader.py`. Give each document a `uuid4().hex` id per data-model.md `Document.id`, use `source="sample"` per data-model.md `Document.source`, and on a skipped file log a warning that names only the filename (research.md R7; make T007 pass)
- [ ] T013 Add a `lifespan` async context manager and a `get_repository(request: Request)` dependency to `app/main.py`. The lifespan creates a new `InMemoryDocumentRepository` on `app.state.repository`, loads `SAMPLE_DOCS_DIR` and adds each document. Pass `lifespan=` to the existing `FastAPI(...)` call and keep `GET /` and `GET /health` unchanged (make T008 pass)
- [ ] T014 Checkpoint: `make test` and `make lint` pass

**Checkpoint**: The service starts with the 5 sample documents held in memory.

---

## Phase 3: User Story 1 - Search the library (Priority: P1) 🎯 MVP

**Goal**: `GET /search?q=&k=` returns up to k sample (and later uploaded) documents ranked by TF-IDF
cosine score, each with a score and a snippet of at most 200 characters.

**Independent Test**: With only the samples loaded, `GET /search?q=annual+leave+days` returns the
leave policy first with 0 < score ≤ 1 and a snippet.

### Tests for User Story 1 ⚠️ (write first, confirm they FAIL)

- [ ] T015 [P] [US1] Write failing unit tests for `SearchIndex.rebuild` / `SearchIndex.search` in `tests/test_search_index.py`:
  - an empty index returns `[]`
  - rebuilding on documents that contain only stop words doesn't raise, and search returns `[]`
  - "reimbursed meals receipt" ranks the expense document first, using the real samples from `load_sample_documents`
  - a term found in no document returns `[]`
  - a query of only stop words ("the and of") returns `[]`
  - every score is in (0, 1] and has at most 4 decimals
  - `len(results) <= k`
  - two documents with identical content tie and are ordered by id ascending
  - the same input gives the same output twice
  - a second `rebuild` replaces the earlier corpus
  - search over 100 documents of about 1 KB each finishes in under 1 s (SC-003)
- [ ] T016 [US1] Write failing unit tests for `SearchIndex.snippet(content, query)` in `tests/test_search_index.py`:
  - length ≤ 200 in every case, including when ellipses are added
  - centred on the earliest whole-word match, case-insensitive
  - starts with `…` only when it doesn't begin at offset 0, and ends with `…` only when it is cut before the end
  - no match gives the first 200 characters
  - whitespace and newlines are collapsed
  - content shorter than 200 characters is returned whole without ellipses
- [ ] T017 [P] [US1] Write failing unit tests for `RedactQueryFilter` in `tests/test_logging_filters.py`: a `uvicorn.access`-style record whose args contain path `/search?q=secret+text` comes out as `/search?<redacted>`; a path with no `?` is unchanged; `filter()` always returns `True`; installing the filter twice doesn't add a duplicate
- [ ] T018 [P] [US1] Write failing API tests in `tests/test_search.py`:
  - spec US1 acceptance scenarios 1–4
  - SC-002: parametrise over the 5 samples with a distinctive phrase each (e.g. "multi-factor authentication passwords" → IT Security Policy) and assert that sample ranks first
  - `k=2` returns at most 2 results, sorted by descending score
  - default k is 5
  - `k=0`, `k=21` and `k=abc` give 422
  - missing `q`, `q=%20%20` and a 501-character `q` give 422; a 500-character `q` gives 200
  - the response has exactly the keys `query`, `k` and `results`; each hit has `id`, `title`, `score` and `snippet`
  - `caplog` at DEBUG contains no query text and no snippet text

### Implementation for User Story 1

- [ ] T019 [US1] Add a `SearchResult` dataclass per data-model.md `SearchResult.id`, `SearchResult.title`, `SearchResult.score`, `SearchResult.snippet`, and pydantic `SearchHit` / `SearchResponse` (fields `query`, `k`, `results`) to `app/models.py`
- [ ] T020 [US1] Implement `SearchIndex` in `app/search.py` per research.md R2 and R3:
  - `rebuild(documents)` fits `TfidfVectorizer(stop_words="english", sublinear_tf=True)` on `title + "\n" + content`; handles an empty list and `ValueError` (empty vocabulary) by marking the index empty; guarded by a `threading.Lock`
  - `search(query, k)` uses `cosine_similarity`, drops scores ≤ 0, sorts by `(-score, id)`, slices to k and rounds per data-model.md `SearchResult.score`
  - make T015 pass
- [ ] T021 [US1] Implement `SearchIndex.snippet(content, query)` in `app/search.py` per research.md R6. Use the fitted vectorizer's `build_analyzer()` to tokenise, falling back to lower-case `\w+` tokens when the index is empty. Length limit per data-model.md `SearchResult.snippet`. Have `search` fill `snippet` on each result (make T016 pass)
- [ ] T022 [P] [US1] Implement `RedactQueryFilter(logging.Filter)` and an idempotent `install_query_redaction()` that attaches it to the `uvicorn.access` logger, in `app/logging_filters.py` (research.md R8; make T017 pass)
- [ ] T023 [US1] Wire search into `app/main.py` (make T018 pass):
  - in `lifespan`, create `SearchIndex` on `app.state.index`, call `rebuild(repository.list())` after the samples load, and call `install_query_redaction()`
  - add a `get_index` dependency
  - add `GET /search` returning `SearchResponse`, with `q: str = Query(..., max_length=MAX_QUERY_CHARS)` per data-model.md `SearchQuery.q` plus an explicit 422 `"Query must not be blank"` when `q.strip()` is empty, and `k: int = Query(DEFAULT_K, ge=MIN_K, le=MAX_K)` per data-model.md `SearchQuery.k`
  - search with the trimmed query and echo the trimmed query in `query`
  - log only the result count
- [ ] T024 [US1] Checkpoint: `make test` and `make lint` pass. Smoke-test the `/search` rows of quickstart.md

**Checkpoint**: MVP. Search works over the sample library.

---

## Phase 4: User Story 2 - Upload a document (Priority: P2)

**Goal**: `POST /documents` accepts a `.md`, `.markdown` or `.txt` file of valid UTF-8, at most
1 MB, while the library holds fewer than 100 documents. It returns 201 with a `DocumentSummary`, and
the document is searchable right away.

**Independent Test**: Upload a `.txt` containing a unique word, get 201 with an id, then search for
the word and find that document.

**Story dependency**: Acceptance scenario 2 (searchable after upload) needs `SearchIndex` from US1.
The upload validation can be built and tested without it.

### Tests for User Story 2 ⚠️ (write first, confirm they FAIL)

- [ ] T025 [P] [US2] Add failing unit tests to `tests/test_text.py`:
  - `safe_filename`: `../../etc/passwd.md` → `passwd.md`; `a\\b\\c.txt` → `c.txt`; cut to 255 characters; empty or whitespace input → `""`
  - `has_allowed_extension`: `.md`, `.MD`, `.markdown` and `.txt` → True; `.pdf`, `.md.pdf`, no extension and `""` → False
  - `decode_utf8`: valid bytes → str; `b"\xff\xfe"` → raises `ValueError`
- [ ] T026 [P] [US2] Write failing API tests for upload in `tests/test_documents.py`:
  - spec US2 acceptance scenarios 1–6
  - 201 body has exactly `id`, `title`, `filename` and `size_bytes`
  - title comes from the H1, otherwise from the filename stem
  - `NOTES.MD` is accepted
  - `notes.md` sent as `application/octet-stream` is accepted
  - `report.pdf` sent as `text/plain` gives 415
  - a file with no extension gives 415
  - exactly 1,048,576 bytes gives 201; 1,048,577 bytes gives 413
  - a 2 MB `.pdf` gives 415, because the extension is checked before the size
  - empty file gives 422; `b"\xff\xfe"` gives 422; missing `file` field gives 422
  - filename `../../x.md` is stored as `x.md`
  - two identical uploads get different ids
  - a word unique to an upload is found by `/search` straight after it
  - with 95 small uploads added to the 5 samples, the next upload gives 409 and the count stays at 100
  - `caplog` contains no uploaded content

### Implementation for User Story 2

- [ ] T027 [US2] Implement `safe_filename`, `has_allowed_extension` and `decode_utf8` in `app/text.py` per research.md R5 and data-model.md `Document.filename` and `Document.content` (make T025 pass)
- [ ] T028 [US2] Add the pydantic `DocumentSummary` model (`id`, `title`, `filename`, `size_bytes`) to `app/models.py`, with fields matching data-model.md `Document.id`, `Document.title`, `Document.filename`, `Document.size_bytes`
- [ ] T029 [US2] Implement `POST /documents` (status 201, `response_model=DocumentSummary`, `file: UploadFile`) in `app/main.py` (make T026 pass):
  - check in the order given in research.md R4 and contracts/http-api.md: extension → read at most `MAX_UPLOAD_BYTES + 1` bytes → size → empty → UTF-8 → build `Document` with `source="upload"` → `repository.add`
  - set `size_bytes` from the raw byte length per data-model.md `Document.size_bytes`
  - map `LibraryFullError` to 409
  - call `index.rebuild(repository.list())`
  - log `id` and `size_bytes` only
  - use the exact error messages from contracts/http-api.md
- [ ] T030 [US2] Checkpoint: `make test` and `make lint` pass. Smoke-test the upload rows of quickstart.md

**Checkpoint**: The library grows, and uploads are searchable right away.

---

## Phase 5: User Story 3 - Browse and read documents (Priority: P3)

**Goal**: `GET /documents` lists summaries (no content) in library order. `GET /documents/{id}`
returns the full document, or 404.

**Independent Test**: On a fresh start the list holds exactly the 5 samples in filename order.
Fetching one returns its full content.

### Tests for User Story 3 ⚠️ (write first, confirm they FAIL)

- [ ] T031 [US3] Add failing API tests for list and get to `tests/test_documents.py`:
  - spec US3 acceptance scenarios 1–4
  - list body is `{"documents": [...], "count": 5}`, with filenames in sorted order and no `content` key in any item
  - fetching each listed id returns `content` equal to the matching file in `data/sample_docs/` read as UTF-8
  - `GET /documents/does-not-exist` gives 404 `{"detail": "Document not found"}`
  - after an upload (when US2 is present) the new document appears last

### Implementation for User Story 3

- [ ] T032 [US3] Add the pydantic models `DocumentDetail` (the `DocumentSummary` fields plus `content` per data-model.md `Document.content`) and `DocumentList` (`documents`, `count`) to `app/models.py`. If US2 isn't done yet, add `DocumentSummary` here instead
- [ ] T033 [US3] Implement `GET /documents` (returns `DocumentList`) and `GET /documents/{document_id}` (returns `DocumentDetail`, or 404 `"Document not found"`) in `app/main.py`, using `get_repository` (make T031 pass)
- [ ] T034 [US3] Checkpoint: `make test` and `make lint` pass

**Checkpoint**: All three user stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T035 [P] Add unit tests for the remaining pydantic schemas in `tests/test_models.py` (`DocumentSummary`, `DocumentDetail`, `DocumentList`, `SearchHit`, `SearchResponse` serialise to the shapes in contracts/http-api.md), so every class and function has a unit test (CLAUDE.md rule)
- [ ] T036 [P] Update the Architecture section of `CLAUDE.md`: new modules (`config`, `models`, `text`, `repository`, `search`, `loader`, `logging_filters`), the 4 endpoints, that the lifespan loads the samples, and that tests must use the `client` fixture
- [ ] T037 Privacy pass: run `grep -rn "log" app/` and confirm no logger call includes `content`, `q`/`query` or `snippet` values (FR-016, Constitution IV); fix any that do in the affected `app/*.py` file
- [ ] T038 Run the manual walkthrough in `specs/001-document-library-search/quickstart.md` (sections 2 and 3) and confirm each expected result, including `GET /search?<redacted>` in the server log
- [ ] T039 Final gate: `make test` (under 30 s, SC-006) and `make lint` pass. Confirm `git diff pyproject.toml` shows no dependency changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all stories
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on Foundational. Its "searchable after upload" behaviour (T026 scenario 2, T029 rebuild) depends on US1's `SearchIndex` (T020, T023)
- **US3 (Phase 5)**: depends only on Foundational. It is independent of US1 and US2 (T031's "after upload" case runs only when US2 exists)
- **Polish (Phase 6)**: depends on every story being finished

### Task-level dependencies

- T004 → T009; T005 → T010; T006 → T011; T007 → T012; T008 → T013
- T010 → T011, T012 (both use `Document`); T009 → T012 (loader derives titles)
- T015 → T020; T016 → T021; T017 → T022; T018 → T023; T019 → T020 → T021 → T023; T022 → T023
- T025 → T027; T026 → T029; T027, T028 → T029
- T031 → T033; T032 → T033
- Same-file ordering (not [P] with each other): `app/main.py`: T013 → T023 → T029 → T033; `app/models.py`: T010 → T019 → T028 → T032; `tests/test_text.py`: T004 → T025; `tests/test_search_index.py`: T015 → T016; `tests/test_documents.py`: T026 → T031

### Within each user story

Tests are written and FAIL → models → services → endpoint → checkpoint.

---

## Parallel Examples

```text
# Phase 2: write all foundational tests together (different files)
T004 tests/test_text.py | T005 tests/test_models.py | T006 tests/test_repository.py
T007 tests/test_loader.py | T008 tests/test_app_startup.py

# Phase 3 (US1): tests in parallel, then the redaction filter alongside the search index
T015 tests/test_search_index.py | T017 tests/test_logging_filters.py | T018 tests/test_search.py
T022 app/logging_filters.py  (in parallel with T019–T021 in app/models.py / app/search.py)

# Phase 4 (US2): both test files at once
T025 tests/test_text.py | T026 tests/test_documents.py

# After Phase 2, US3 (T031–T033) can run in parallel with US1, apart from shared-file ordering
# in app/main.py and app/models.py
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational
2. Phase 3 US1: search over the 5 samples
3. **STOP and validate**: run the `/search` quickstart rows; this is a demoable MVP

### Incremental delivery

1. Add US2 (upload): the library grows, and uploads are searchable right away
2. Add US3 (list and get): users can browse and read documents in full
3. Polish: schema tests, docs, the privacy pass, the quickstart run and the final gate

Each step finishes with `make test` and `make lint` green, which is a natural commit point.

---

## Notes

- [P] means a different file with no dependency on an incomplete task
- Confirm each test fails for the right reason (a missing feature, not an import typo) before writing
  the code
- Don't add dependencies; scikit-learn, FastAPI, pydantic and python-multipart are already declared
- Never read or edit `.env` files

# Research: Document Library with Search

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-21

The Technical Context had no open questions after the user's planning input. Each entry below records
a design decision, why it was chosen, and what else was considered. Installed versions checked in
`.venv`: FastAPI 0.165.0, pydantic 2.14.4, scikit-learn 1.9.1.

## R1. Storage behind a repository class

- **Decision**: A concrete `InMemoryDocumentRepository` in `app/repository.py`. It holds documents in
  a `dict[str, Document]`, preserving insertion order, behind a `threading.Lock`. Its public methods
  are `add`, `get`, `list`, `count` and `clear`. Route handlers reach it only through a FastAPI
  dependency, `get_repository`, that returns the instance on `app.state`.
- **Rationale**: The user asked for a swappable repository. A small class plus a dependency gives a
  single place to swap (`app.dependency_overrides[get_repository]`) without adding a framework. The
  lock is needed because FastAPI runs sync handlers in a thread pool. FR-018 forbids disk writes, so
  storage is a plain dict.
- **Alternatives considered**: (a) a module-level dict, rejected because it can't be swapped and
  leaks state between tests; (b) a `typing.Protocol` plus implementation, deferred because it adds a
  file and indirection for a second implementation that doesn't exist yet; (c) SQLite in memory,
  rejected as unnecessary (Constitution III).

## R2. Search: TF-IDF with cosine similarity

- **Decision**: `app/search.py` defines `SearchIndex`. `rebuild(documents)` fits
  `TfidfVectorizer(stop_words="english", sublinear_tf=True)` on title + content of every document and
  stores the matrix. `search(query, k)` transforms the query and computes `cosine_similarity`. It
  drops scores ≤ 0, sorts by `(-score, doc_id)`, keeps the top k and rounds scores to 4 decimals.
- **Rationale**: This is what the user and CLAUDE.md require, and it needs no new dependency. TF-IDF
  vectors are non-negative and L2-normalised, so cosine scores already fall in [0, 1] (FR-009).
  English stop words make a query of only common words score 0 and return an empty list (an edge
  case in the spec). Sorting on `(-score, id)` makes tie order deterministic (FR-014).
- **Alternatives considered**: BM25 (it would need a new dependency or hand-written code); raw term
  counts (worse ranking); character n-grams (noisier for short policy documents).

## R3. Rebuilding the index

- **Decision**: Rebuild the whole index synchronously inside the upload request, after the document
  is stored and before the response is sent. Do the same once after the sample documents load. With
  an empty library the index is marked empty and search returns `[]` without fitting, because
  fitting on zero documents raises `ValueError`. Fitting can also raise
  `ValueError: empty vocabulary` if every document contains only stop words; catch it and treat the
  index as empty.
- **Rationale**: The user requested it, and it makes uploads searchable immediately (FR-013,
  SC-004). With at most 100 documents of at most 1 MB each (FR-019), a refit takes well under a
  second.
- **Alternatives considered**: Incremental `partial_fit` (TfidfVectorizer doesn't support it);
  rebuilding lazily at search time (it shifts the cost onto searches and makes the code harder to
  follow).

## R4. Upload validation order and HTTP status codes

- **Decision**: `POST /documents` takes a multipart field `file` and checks, in this order:
  1. Filename present and with an allowed extension (`.md`, `.markdown`, `.txt`, case-insensitive),
     otherwise **415**.
  2. Read at most 1,048,577 bytes; more than 1,048,576 means **413**.
  3. Zero bytes means **422**.
  4. Invalid UTF-8 (strict decode) means **422**.
  5. Library already holds 100 documents means **409**.

  On success the response is **201**. Every error uses FastAPI's standard
  `{"detail": "<message>"}` body, and the message never repeats document content.
- **Rationale**: The cheap checks come first, and reading is capped so a huge upload is never fully
  buffered. The status codes follow standard HTTP meanings, and all are 4xx (SC-005). The declared
  content type is ignored (Clarification Q2).
- **Alternatives considered**: Returning 400 for everything (less informative); 507 for a full
  library (a 5xx, which SC-005 forbids).

## R5. Filenames, titles and ids

- **Decision**:
  - `filename` is the basename after splitting on both `/` and `\`, capped at 255 characters.
  - `title` is the text of the first line matching `^#\s+(.+)$`, stripped. If there is none, it is
    the filename without its extension.
  - `id` is `uuid.uuid4().hex`.
  - Sample documents get `source="sample"` and uploads get `source="upload"`.
- **Rationale**: Taking only the basename stops `../` from showing up in metadata, and since nothing
  is written to disk, path traversal can't happen anyway (FR-017). Random ids are opaque and unique
  (FR-004).
- **Alternatives considered**: Sequential integer ids (guessable, and they collide after a restart
  in a confusing way); a content hash (FR-004 and the spec's duplicate-upload rule require that
  duplicates get distinct ids).

## R6. Snippet extraction

- **Decision**: Tokenise the query with the fitted vectorizer's `build_analyzer()`. Find the earliest
  case-insensitive whole-word match of any query token in the content, with whitespace collapsed to
  single spaces. Take a window of up to 200 characters centred on that match. Prefix `…` if the
  window doesn't start at the beginning and suffix `…` if it doesn't reach the end, with both
  ellipses counted within the 200 characters. If no token matches, use the first 200 characters.
- **Rationale**: This meets FR-011 and is deterministic. It reuses the same tokenisation as scoring
  so that highlighted terms match what was ranked.
- **Alternatives considered**: Picking the sentence with the best score (more complex, little gain
  for documents this short).

## R7. Loading sample documents at start-up

- **Decision**: A FastAPI `lifespan` handler creates a fresh repository and index on `app.state`,
  loads every `*.md` in `data/sample_docs/` (sorted by filename, UTF-8), skips any unreadable file
  with a warning that names only the file, and builds the index. The folder path comes from a
  module constant computed from the location of `app/`.
- **Rationale**: Loading is automatic (FR-001). A missing file doesn't stop start-up (an edge case in
  the spec). Each `with TestClient(app)` block runs the lifespan, so every test gets a fresh library
  with exactly the 5 samples, which keeps tests isolated and deterministic.
- **Alternatives considered**: Loading at import time (makes tests share state, and import-time I/O
  is a side effect); `@app.on_event("startup")` (deprecated in FastAPI).

## R8. Logging

- **Decision**: Use a module logger `logging.getLogger("docqa")`. Log only events with an id, size,
  count or status, for example `document stored id=… bytes=…`. Never log content, query text or
  snippets.
- **Query strings in access logs**: uvicorn's access logger (`uvicorn.access`) writes the request
  line including `?q=…`, which would leak query text. The lifespan handler installs a small
  `logging.Filter` on `uvicorn.access` that replaces everything after `?` in the logged path with
  `?<redacted>`. This lives in the app, so it works no matter how the server is started.
- **Rationale**: FR-016 and Constitution IV.
- **Alternatives considered**: `POST /search` with a JSON body (a less natural read-only API, and
  query text could still leak elsewhere); `--no-access-log` in the Makefile (it loses useful status
  logging and depends on how the server is launched).

## R9. Tests

- **Decision**: pytest with `fastapi.testclient.TestClient` used as a context manager in a
  `client` fixture in `tests/conftest.py`. Test files:
  - `tests/test_documents.py`: upload, list and get endpoints
  - `tests/test_search.py`: search endpoint
  - `tests/test_repository.py`: repository unit tests
  - `tests/test_search_index.py`: index, scoring and snippet unit tests
  - `tests/test_text.py`: helper unit tests
  - `tests/test_loader.py`: sample loader unit tests, using `tmp_path`
  - `tests/test_logging_filters.py`: redaction filter unit tests

  The cap and size limits are tested with generated in-memory bytes, so no fixtures are written to
  disk.
- **Rationale**: Constitution II (every function gets a unit test, and tests are deterministic and
  run in-process) and the saved preference for one test file per feature area.

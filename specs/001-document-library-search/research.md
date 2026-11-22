# Research: Document Library with Search

**Feature**: `001-document-library-search` | **Date**: 2026-11-21

The Technical Context had no open NEEDS CLARIFICATION items: the user fixed the stack (FastAPI,
pydantic v2, scikit-learn TF-IDF, in-memory repository, pytest + TestClient). The decisions below
settle the remaining design choices. Search behaviour was checked with a prototype over
`data/sample_docs/` (scikit-learn 1.9.1, FastAPI 0.165.0, pydantic 2.14.4 installed in `.venv`).

## R1. Ranking: TfidfVectorizer + cosine similarity

- **Decision**: `TfidfVectorizer(stop_words="english", sublinear_tf=True, lowercase=True)` fitted
  on all document texts; score = cosine similarity between the query vector and each document
  vector, computed with `linear_kernel` (TF-IDF rows are L2-normalised, so the dot product equals
  cosine and lies in [0, 1]).
- **Rationale**: Required by the user and CLAUDE.md; deterministic, offline, and fast for ≤ 1,000
  short docs. English stop words make a query like "the and of" score 0 for every document, which
  gives the spec's "common words only → empty list" behaviour for free (verified in prototype).
  `sublinear_tf` stops long documents with repeated terms from dominating.
- **Prototype results** (sample docs): "annual leave" → only Leave Policy (0.436);
  "receipt reimbursement" → Expense (0.161) > Travel (0.064); "zebra" and "the and of" → all 0.
- **Alternatives considered**: `cosine_similarity` (same result, extra normalisation work);
  BM25 (needs a new dependency → rejected by Principle V); embeddings/LLM (forbidden by
  Principle III).

## R2. Index lifecycle: full rebuild on every upload

- **Decision**: A `SearchIndex` holds the fitted vectorizer, the document matrix and the ordered
  list of document ids. `rebuild(documents)` refits from scratch. It runs once at start-up after
  the sample docs load, and again after every successful upload.
- **Rationale**: Requested by the user. IDF weights change whenever the corpus changes, so a refit
  is the only correct option with `TfidfVectorizer`. Refitting 1,000 short docs takes milliseconds.
- **Edge**: `fit` raises `ValueError("empty vocabulary")` when there are no documents or every
  token is a stop word. The index catches this and becomes an empty index (every search returns
  `[]`) so search never fails with a server error.
- **Concurrency**: FastAPI runs sync endpoints in a thread pool, so a `threading.Lock` makes
  "add document + rebuild index" one step, and a search always reads one consistent
  (vectorizer, matrix, ids) snapshot. The snapshot is swapped in by assigning a single attribute.
- **Alternatives considered**: incremental `partial_fit` (TfidfVectorizer doesn't support it);
  `HashingVectorizer` + `TfidfTransformer` (more moving parts for no gain at this scale).

## R3. Storage: repository behind a Protocol

- **Decision**: `DocumentRepository` is a `typing.Protocol` with `add`, `get`, `list`, plus
  `InMemoryDocumentRepository`, which stores documents in a dict in insertion order.
- **Rationale**: The user wants to be able to swap storage later. A Protocol costs one small class
  and no dependency. Insertion order gives a stable list order and a tie-break for search.
- **Alternatives considered**: module-level dict (can't be swapped, and state leaks between tests);
  SQLite (persistence is out of scope per the spec's Assumptions).

## R4. App wiring and test isolation: app factory + lifespan

- **Decision**: `create_app(sample_dir: Path | None = DEFAULT_SAMPLE_DIR) -> FastAPI` builds a
  fresh repository and index and stores them on `app.state`. A `lifespan` handler loads the sample
  docs at start-up. `app = create_app()` stays at module level for `uvicorn app.main:app` and the
  existing tests.
- **Rationale**: Each test gets a fresh library (`with TestClient(create_app()) as client:` runs
  the lifespan), so uploads in one test can't affect another. That is Principle II's determinism
  rule. Passing `sample_dir` lets tests point at a temporary folder (e.g., an unreadable or empty
  one).
- **Note**: `TestClient(app)` without `with` does **not** run the lifespan. That's fine for the
  existing `/` and `/health` tests, but every library test MUST use the context-manager form.

## R5. Upload handling and validation

- **Decision**:
  - `POST /documents` with a multipart field `file` (`UploadFile`; `python-multipart` is already
    declared).
  - Read at most `MAX_BYTES + 1` (1,048,577) bytes; more than `MAX_BYTES` → **413**. This avoids
    trusting the `Content-Length` header.
  - Filename: take the base name after the last `/` or `\`, strip whitespace, cap at 255 chars.
    The extension (case-insensitive) must be in `{.md, .markdown, .txt}`, otherwise **415**.
    The filename is stored as metadata only and never used as a filesystem path.
  - Content: empty → **422**; `bytes.decode("utf-8")` fails → **422**. A UTF-8 BOM is stripped.
  - The client-sent content type is ignored (unreliable); the extension and UTF-8 decoding decide.
- **Rationale**: Each failure gets its own HTTP code, so tests can assert the exact reason (FR-016,
  SC-005). Bounded reads mean the size limit can't be dodged.
- **Alternatives considered**: middleware that limits request size (more code; still needs a
  per-file check); trusting `UploadFile.size` (it can be missing).

## R6. Error response shape

- **Decision**: Use FastAPI's default `{"detail": ...}` body. Custom rejections raise
  `HTTPException(status_code, detail="<human-readable reason>")`. Query/`k` validation uses
  FastAPI `Query(min_length=1, max_length=500)`, `Query(ge=1, le=20)` and gives **422** with
  pydantic's error list. Whitespace-only `q` is rejected after `strip()` with a 422 detail string.
- **Rationale**: Standard, documented in OpenAPI, no custom exception handlers needed.

## R7. Snippet extraction

- **Decision**: Split the content into segments on blank lines and sentence ends (`. ` `! ` `? `),
  drop Markdown heading markers (`#`) and empty segments. Query terms are the vectorizer's analyzed
  tokens (lowercase, stop words removed). Pick the first segment containing one of those terms as
  a whole word (case-insensitive); if none, use the first non-heading segment. Collapse whitespace
  and trim to ≤ 200 characters, cutting at a word boundary and adding "…" (the "…" counts toward
  the 200).
- **Rationale**: Deterministic, cheap, and makes the snippet relevant to the query (FR-013).
- **Alternatives considered**: centring a window on the first hit (can cut words mid-sentence);
  highlighting markup (not required).

## R8. IDs, titles, ordering, score format

- **Decision**:
  - IDs: `uuid.uuid4().hex`. They're opaque (spec), and tests never hard-code them; they look ids
    up via list or the upload response.
  - Title: first line matching `^# (.+)$` (level-1 heading), stripped; otherwise the filename stem.
  - List order: insertion order (samples sorted by filename, then uploads).
  - Search order: score descending, ties by insertion order (stable sort). Scores > 0 only, and
    rounded to 4 decimals in the response so repeated runs compare equal.
- **Rationale**: Meets FR-005, FR-006, FR-012 and SC-006.

## R9. Logging (Principle IV)

- **Decision**: Use the standard `logging` module (`logging.getLogger("docqa")`). Log only events
  with id, base filename and byte size (e.g., `document_added id=… filename=… size=…`), and
  skipped sample files by name with the exception class name only. Never log content, snippets,
  or query text.
- **Rationale**: FR-017 and the constitution. Query text could hold sensitive terms, so it isn't
  logged either.

## R10. Dependencies (Principle V)

- **Decision**: No new dependencies. Everything used is already declared: `fastapi`, `pydantic`,
  `scikit-learn` (pulls in `numpy` and `scipy`), `python-multipart`, `uvicorn`; dev: `pytest`,
  `httpx`, `ruff`.

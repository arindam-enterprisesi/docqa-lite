# Data Model: Document Library with Search

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

All state is in memory (FR-018). Nothing is persisted.

## Constants (`app/config.py`)

| Name | Value | Source |
|------|-------|--------|
| `MAX_UPLOAD_BYTES` | 1_048_576 | FR-003 |
| `MAX_DOCUMENTS` | 100 | FR-019 |
| `ALLOWED_EXTENSIONS` | {".md", ".markdown", ".txt"} | FR-002 |
| `DEFAULT_K` / `MIN_K` / `MAX_K` | 5 / 1 / 20 | FR-008 |
| `MAX_QUERY_CHARS` | 500 | FR-012 |
| `SNIPPET_CHARS` | 200 | FR-011 |
| `MAX_FILENAME_CHARS` | 255 | R5 |
| `SAMPLE_DOCS_DIR` | `<repo>/data/sample_docs` | FR-001 |

## Entity: Document (internal, `app/models.py`)

Frozen dataclass or pydantic model held by the repository.

| Field | Type | Rules |
|-------|------|-------|
| `id` | `str` | `uuid4().hex`, 32 lowercase hex characters, unique, assigned by the system (FR-004) |
| `title` | `str` | First `# ` heading, otherwise the filename stem (FR-005); non-empty |
| `filename` | `str` | Basename of the supplied name, at most 255 characters, display only (FR-017) |
| `size_bytes` | `int` | Length of the raw upload in bytes; 1 ≤ size ≤ 1,048,576 |
| `content` | `str` | Strictly decoded UTF-8 text; non-empty |
| `source` | `Literal["sample", "upload"]` | How the document entered the library |

**Lifecycle**: created when it is loaded or uploaded, then immutable, then gone when the process
exits. Documents can't be updated or deleted (see the spec's Assumptions).

**Invariants**: `count() ≤ MAX_DOCUMENTS`; ids are unique; listing order is insertion order
(sample documents sorted by filename first, then uploads in the order they arrived).

## Entity: SearchResult (internal)

| Field | Type | Rules |
|-------|------|-------|
| `id` | `str` | Id of an existing document |
| `title` | `str` | Copied from the document |
| `score` | `float` | 0 < score ≤ 1, rounded to 4 decimals (FR-009, FR-010) |
| `snippet` | `str` | At most 200 characters, taken from the content (FR-011) |

Ordering: by score descending, then by `id` ascending (FR-014).

## API schemas (pydantic v2, `app/models.py`)

| Schema | Fields | Used by |
|--------|--------|---------|
| `DocumentSummary` | `id`, `title`, `filename`, `size_bytes` | `GET /documents` items, `POST /documents` 201 |
| `DocumentDetail` | `DocumentSummary` fields + `content` | `GET /documents/{id}` |
| `DocumentList` | `documents: list[DocumentSummary]`, `count: int` | `GET /documents` |
| `SearchQuery` | `q: str` (stripped, 1–500 characters), `k: int` (1–20, default 5) | `GET /search` query parameters |
| `SearchHit` | `id`, `title`, `score`, `snippet` | `GET /search` items |
| `SearchResponse` | `query: str`, `k: int`, `results: list[SearchHit]` | `GET /search` |

`source` is internal and is not exposed in the responses.

## Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `InMemoryDocumentRepository` | `app/repository.py` | `add(doc)`, which raises `LibraryFullError` when at the cap; `get(id) -> Document \| None`; `list() -> list[Document]`; `count()`; `clear()`. Thread-safe. |
| `SearchIndex` | `app/search.py` | `rebuild(docs)`; `search(query, k) -> list[SearchResult]`; `snippet(content, query) -> str` |
| Text helpers | `app/text.py` | `safe_filename(name)`, `derive_title(content, filename)`, `has_allowed_extension(name)`, `decode_utf8(data)` |
| Sample loader | `app/loader.py` | `load_sample_documents(dir) -> list[Document]` |
| Log redaction | `app/logging_filters.py` | `RedactQueryFilter` for `uvicorn.access` (R8) |
| Routes and lifespan | `app/main.py` | Wiring, the `get_repository` and `get_index` dependencies, mapping errors to HTTP status codes |

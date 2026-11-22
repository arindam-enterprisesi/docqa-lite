# Data Model: Document Library with Search

**Feature**: `001-document-library-search` | **Date**: 2026-11-21

All storage is in-memory (see [research.md](research.md) R3). Entities below are domain records;
API shapes are in [contracts/openapi.yaml](contracts/openapi.yaml).

## Document (domain record)

| Field      | Type                           | Rules / source                                                   |
|------------|--------------------------------|------------------------------------------------------------------|
| `id`       | str (32 hex chars)             | `uuid4().hex`, assigned on creation, unique, immutable           |
| `title`    | str (1–200 chars)              | First `# ` heading, else filename stem (FR-006); truncated to 200 |
| `filename` | str (1–255 chars)              | Base name only, no `/` or `\`; extension in `.md .markdown .txt` |
| `size`     | int (1–1,048,576)              | Byte length of the uploaded UTF-8 content (before BOM strip)     |
| `content`  | str                            | Full decoded UTF-8 text, non-empty                               |
| `source`   | `"sample"` \| `"upload"`       | `sample` for start-up docs, `upload` for API uploads             |

- Immutable after creation (no update or delete in this feature). Implemented as a frozen
  dataclass or a frozen pydantic model.
- **Lifecycle**: created → stored (in the repository) → indexed (after the next `rebuild`). There
  are no other states. Everything is lost on process exit; samples are recreated on every start.

## Search Index (internal, not exposed)

| Field        | Description                                                        |
|--------------|--------------------------------------------------------------------|
| `vectorizer` | Fitted `TfidfVectorizer`, or `None` when the corpus is empty      |
| `matrix`     | Sparse TF-IDF matrix, one row per indexed document                 |
| `doc_ids`    | Document ids in repository insertion order, aligned with `matrix` rows |

- Rebuilt from `repository.list()` at start-up and after each upload; replaced as one snapshot.

## Search Hit (derived, per request)

| Field     | Type                  | Rules                                                         |
|-----------|-----------------------|---------------------------------------------------------------|
| `id`      | str                   | Id of the matched Document                                    |
| `title`   | str                   | Title of the matched Document                                 |
| `score`   | float, 0 < score ≤ 1  | Cosine similarity rounded to 4 decimals; 0-score docs excluded |
| `snippet` | str, 1–200 chars      | Query-relevant passage (research R7)                          |

## Request validation rules

| Input            | Rule                                                        | Failure |
|------------------|-------------------------------------------------------------|---------|
| upload `file`    | field present                                               | 422     |
| upload size      | 1 ≤ bytes ≤ 1,048,576                                       | 413 (too big) / 422 (empty) |
| upload extension | `.md`, `.markdown`, `.txt` (case-insensitive)               | 415     |
| upload encoding  | valid UTF-8                                                 | 422     |
| `q`              | 1–500 chars, not whitespace-only                            | 422     |
| `k`              | integer 1–20, default 5                                     | 422     |
| `document_id`    | must exist                                                  | 404     |

## Relationships

- Repository 1 — * Document; the Search Index refers to Documents by `id` only (it holds a copy of
  the vectorized text, not the Document objects).
- A Search Hit refers to exactly one Document.

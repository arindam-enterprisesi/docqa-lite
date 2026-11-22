# HTTP API Contract: Document Library with Search

Base URL: `http://localhost:8000`. All bodies are JSON unless stated otherwise. Errors use FastAPI's
standard shape, `{"detail": "<message>"}`; when FastAPI's own request validation fails, `detail` is
a list of error objects. Schemas are defined in [data-model.md](../data-model.md).

Existing endpoints `GET /` and `GET /health` are unchanged.

---

## POST /documents — upload a document

Request: `multipart/form-data` with a single file field named `file`.

| Status | When | Body |
|--------|------|------|
| 201 | Stored | `DocumentSummary` |
| 409 | Library already holds 100 documents | `{"detail": "Library full: maximum 100 documents"}` |
| 413 | File larger than 1,048,576 bytes | `{"detail": "File too large: maximum 1048576 bytes"}` |
| 415 | Missing filename or extension not `.md`/`.markdown`/`.txt` | `{"detail": "Unsupported file type: allowed .md, .markdown, .txt"}` |
| 422 | `file` field missing | FastAPI validation error |
| 422 | File is empty | `{"detail": "File is empty"}` |
| 422 | Content is not valid UTF-8 | `{"detail": "File is not valid UTF-8 text"}` |

Checks run in this order: extension, size, empty, UTF-8, capacity. The declared content type is
ignored.

Example 201:

```json
{"id": "3f2a…", "title": "Remote Work Policy", "filename": "remote.md", "size_bytes": 412}
```

---

## GET /documents — list documents

| Status | Body |
|--------|------|
| 200 | `DocumentList`: `{"documents": [DocumentSummary, …], "count": 5}` |

Order: sample documents sorted by filename, then uploads in the order they arrived. `content` is
never included.

---

## GET /documents/{id} — fetch one document

| Status | When | Body |
|--------|------|------|
| 200 | Found | `DocumentDetail` (summary fields + `content`) |
| 404 | Unknown id | `{"detail": "Document not found"}` |

---

## GET /search?q=&k= — search documents

| Param | Type | Rules |
|-------|------|-------|
| `q` | string | Required; trimmed; 1–500 characters |
| `k` | int | Optional; default 5; 1 ≤ k ≤ 20 |

| Status | When | Body |
|--------|------|------|
| 200 | Valid query (including no matches) | `SearchResponse` |
| 422 | `q` missing, blank after trimming, or longer than 500 characters; `k` out of range or not an integer | FastAPI validation error, or `{"detail": "Query must not be blank"}` |

Example 200:

```json
{
  "query": "meal allowance",
  "k": 5,
  "results": [
    {"id": "9c1e…", "title": "Expense Reimbursement Policy", "score": 0.4123,
     "snippet": "…Meals during business travel are reimbursed up to a daily limit of 50 USD…"}
  ]
}
```

Guarantees: `len(results) ≤ k`; every `score` is in (0, 1]; results are sorted by score descending,
then id ascending; each `snippet` is at most 200 characters; the same library and query always give
the same response.

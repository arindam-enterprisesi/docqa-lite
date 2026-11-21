# Quickstart: Document Library with Search

Validation guide that proves the feature works from end to end. The endpoints are defined in
[contracts/http-api.md](./contracts/http-api.md).

## Prerequisites

```bash
make install      # or: uv sync --extra dev
```

## 1. Automated checks (the gate before any PR)

```bash
make test         # all tests pass, with no network access needed
make lint         # ruff check + format check pass
```

Expected: every test in `tests/test_documents.py`, `tests/test_search.py`,
`tests/test_repository.py`, `tests/test_search_index.py`, `tests/test_text.py`,
`tests/test_loader.py` and `tests/test_logging_filters.py` passes. The suite
finishes in under 30 seconds (SC-006).

## 2. Manual smoke test

```bash
make run          # http://localhost:8000, interactive docs at /docs
```

In a second terminal:

| Step | Command | Expected |
|------|---------|----------|
| Samples loaded (SC-001) | `curl -s localhost:8000/documents` | `count` is 5; titles include "Expense Reimbursement Policy" |
| Fetch one | `curl -s localhost:8000/documents/<id from list>` | 200 with `content` |
| Unknown id | `curl -si localhost:8000/documents/nope` | 404 |
| Search (US1) | `curl -s 'localhost:8000/search?q=annual+leave+days&k=2'` | At most 2 results; the leave policy is first; score in (0, 1]; snippet at most 200 characters |
| No match | `curl -s 'localhost:8000/search?q=zxqvy'` | `"results": []` |
| Blank query | `curl -si 'localhost:8000/search?q=%20'` | 422 |
| Upload (US2) | `printf '# Remote Work\nStaff may work remotely on Fridays.\n' > /tmp/r.md && curl -s -F file=@/tmp/r.md localhost:8000/documents` | 201, `title` is "Remote Work" |
| Searchable now (SC-004) | `curl -s 'localhost:8000/search?q=remotely+fridays'` | The uploaded document is first |
| Wrong type | `curl -si -F file=@some.pdf localhost:8000/documents` | 415 |
| Too large | `head -c 1048577 /dev/zero \| tr '\0' a > /tmp/big.txt && curl -si -F file=@/tmp/big.txt localhost:8000/documents` | 413 |
| Restart wipes uploads (FR-018) | Restart `make run`, then list | `count` is 5 again |

## 3. Privacy check (FR-016)

While doing step 2, check the server log: it shows ids, sizes and status codes, and never document
text or query strings. Search requests appear as `GET /search?<redacted>`.

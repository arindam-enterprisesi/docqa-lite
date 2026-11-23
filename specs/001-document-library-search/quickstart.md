# Quickstart & Validation: Document Library with Search

How to prove feature `001-document-library-search` works end to end. Endpoint shapes are in
[contracts/openapi.yaml](contracts/openapi.yaml); validation rules are in
[data-model.md](data-model.md).

## Prerequisites

- WSL shell in the repo root; `uv` on PATH (`source $HOME/.local/bin/env` if not).
- `make install` done (no new dependencies are added by this feature).

## Automated validation

```bash
make test   # all pytest suites, including the new library/search tests
make lint   # ruff check + format check
```

Both MUST pass (constitution, Principle II and the quality gates).

## Manual validation (running server)

```bash
make run    # http://localhost:8000, OpenAPI UI at /docs
```

In a second WSL shell:

| # | Scenario (spec ref) | Command | Expected |
|---|---------------------|---------|----------|
| 1 | Samples loaded (US3-1, SC-001) | `curl -s localhost:8000/documents` | 200; 5 entries (expense, IT security, leave, onboarding, travel), no `content` field |
| 2 | Search samples (US1-1) | `curl -s 'localhost:8000/search?q=annual%20leave'` | 200; first result title "Annual Leave Policy", score in (0, 1], snippet ≤ 200 chars |
| 3 | Top-k (US1-2) | `curl -s 'localhost:8000/search?q=receipt%20reimbursement&k=2'` | ≤ 2 results; first is "Expense Reimbursement Policy"; scores descending |
| 4 | No match (US1-3) | `curl -s 'localhost:8000/search?q=zebra'` | 200; `"results": []` |
| 5 | Blank query (US1-4) | `curl -s -o /dev/null -w '%{http_code}' 'localhost:8000/search?q=%20%20'` | 422 |
| 6 | Bad k (edge) | `curl -s -o /dev/null -w '%{http_code}' 'localhost:8000/search?q=leave&k=0'` | 422 (same for `k=21`) |
| 7 | Upload (US2-1) | `printf '# Quokka Care\nFeed the quokka daily.\n' > /tmp/q.md && curl -s -F file=@/tmp/q.md localhost:8000/documents` | 201; JSON with `id`, title "Quokka Care", filename `q.md`, `source: upload` |
| 8 | New doc searchable (US2-2, SC-003) | `curl -s 'localhost:8000/search?q=quokka'` | first result title "Quokka Care" |
| 9 | Get by id (US3-3) | `curl -s localhost:8000/documents/<id from step 7>` | 200; includes full `content` |
| 10 | Unknown id (US3-4) | `curl -s -o /dev/null -w '%{http_code}' localhost:8000/documents/nope` | 404 |
| 11 | Too large (US2-3) | `head -c 1048577 /dev/zero \| tr '\0' a > /tmp/big.txt && curl -s -o /dev/null -w '%{http_code}' -F file=@/tmp/big.txt localhost:8000/documents` | 413; then `/documents` still lists the same count |
| 12 | Wrong type (US2-4) | `echo hi > /tmp/r.pdf && curl -s -o /dev/null -w '%{http_code}' -F file=@/tmp/r.pdf localhost:8000/documents` | 415 |
| 13 | Empty / non-UTF-8 (US2-5) | `: > /tmp/e.md` / `printf '\xff\xfe' > /tmp/b.txt`, upload each | 422 each |
| 14 | Restart (Assumptions) | stop and restart `make run`, list documents | only the 5 samples again |

## Log check (Principle IV)

While running steps 7–13, the server log MUST NOT show any document text, snippets, or query text,
only ids, filenames and sizes.

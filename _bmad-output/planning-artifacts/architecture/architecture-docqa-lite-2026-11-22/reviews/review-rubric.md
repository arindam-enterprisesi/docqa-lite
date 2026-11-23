# Rubric review: ARCHITECTURE-SPINE.md (docqa-lite)

Reviewer: read-only. Checked against app/*.py, PRD, constitution, uv.lock, specs/.../contracts.

## Verdict
Sound and mostly faithful to the code, but not ready as-is. Import graph, lock usage, status codes, sample sort order, score rounding and snippet cap all check out. Fix the 2 high findings and the medium gaps in the operational envelope and port contract before ratifying.

## Verified correct (no action)
- Import graph and diagram match code (main imports all four; ingest->repository; search->repository+models; repository/models import nothing from app; ingest/search never import each other or FastAPI).
- Upload: repository.add + index.rebuild under app.state.lock; search reads snapshot without lock; single-assignment swap in `rebuild`.
- Status map 413/415/422/404; bounded read `MAX_BYTES+1`; samples via `sorted(glob)`; stable argsort; rounding, cap 1.0, drop zero after rounding; 200-char snippet.
- Stack versions match the .venv; uv.lock exists. Venv is Python 3.12.3.

## Findings

### HIGH
1. **AD-8 cannot prevent query-text leakage.** Rule says never log query text, but the only enforcement is the `docqa` logger discipline. Under `make run`, uvicorn's access log prints the full request line, `GET /search?q=<text>`. The spine does not decide access-log handling (`--no-access-log` or a filter). Also, the AD title says "never ... echoed", yet `SearchResponse` echoes `query`, and FastAPI's default 422 body for `q`/`k` includes an `input` field with the offending value. Narrow the rule (what is covered: document content vs query) and decide the access-log setting.
2. **Error-body convention is false (Conventions, AD-6).** "Error body is `{"detail": "<readable reason>"}`" holds only for HTTPException paths. Query-parameter and missing-`file` validation 422s come from FastAPI's default handler, where `detail` is a list of objects (`loc`, `msg`, `type`, `input`). There is no custom exception handler in the code. Either ratify both shapes explicitly or add a handler decision; as written, two units could implement it differently (AD-6 "divergent error bodies").

### MEDIUM
3. **AD-2 / AD-7: the port's ordering contract is unstated.** AD-7's "samples first, then upload order" depends on `DocumentRepository.list()` returning insertion order, and on `add` of a duplicate id (the dict silently overwrites it, contradicting "adding a new record"). The Protocol states neither. A replacement backend can diverge without violating the AD text. Put list-order and id-uniqueness into AD-2.
4. **Operational envelope undecided (Deferred/Conventions).**
   - Logging config: the `docqa` logger has no handler or level set; INFO events (`library_ready`, `document_added`) are dropped under default root WARNING, so the AD-8 events are invisible at run time.
   - Memory and library-size ceiling: only upload latency is deferred; there is no cap on total documents or bytes (each upload up to 1 MB, held in memory, full rebuild per upload).
   - Request-body bound: Starlette spools the whole multipart body before the bounded `read`, so 413 is returned only after full receipt; no server or proxy limit is decided.
   - FR1 failure mode: a missing sample dir silently yields an empty library; bad files only warn. Not decided.
   - Duplicate filenames/content are allowed; not stated.
5. **Concurrency model not fixed.** Routes are sync `def` (run in the threadpool), which is why a `threading.Lock` is correct. The spine does not forbid converting routes to `async def` (which would block the loop with the lock and the CPU-bound rebuild). Also `list`/`get` read the repository lock-free while uploads mutate it; the spine only blesses lock-free search. Add a rule.
6. **AD-1 / AD-5 enforceability.** "Arrows are the only permitted imports" and "no `--workers`" are text only; nothing checks them (no import-graph test, and `make run` is the only run target so AD-5 is moot there). Specify a cheap check (an ast-based import test in `tests/`; constitution V bars new deps like import-linter without plan justification). AD-1 "module-level mutable state forbidden" sits beside module-level `app = create_app()`; state the exception.
7. **NFR1 (300 ms at 1,000 docs) is mapped to AD-4 but not governed.** AD-4 gives lock-free reads, not a latency bar. The PRD's open item (how NFR1 is measured) is not carried into the spine as decided or open. Add it to Deferred or Open Questions with the method and threshold.

### LOW
8. **AD-7 tie claim is imprecise.** Stable sort is on raw scores; docs whose scores differ below the 4th decimal but round equal are ordered by raw score, not insertion order.
9. **Naming/convert conventions overstated.** `SearchHit` and `SearchResponse` do not follow `*Out`/`*Summary`; the search route builds `SearchResponse` directly and `SearchIndex` constructs `SearchHit`, so "routes convert with `model_validate`" is not universal. Also AD-1/AD-3: the lifespan calls `repository.add` outside the lock (fine at start-up, but AD-3's "routes never call add" should say lifespan is the exception).
10. **Stack section.** Labelled "not web-checked"; the verified-current criterion is unmet. Cite `uv.lock` as the pin source and note pyproject uses `>=` floors. Versions match the venv.

## Coverage
FR1-FR6, NFR1-NFR3 all mapped. NFR2 omits that 422 for FastAPI validation uses a different body (see 2). Deferred items cannot make two units diverge except "Config via environment" and "Deployment target" interacting with finding 4 (logging and request limits).

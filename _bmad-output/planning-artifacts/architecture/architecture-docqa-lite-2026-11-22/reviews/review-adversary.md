# Adversarial review: ARCHITECTURE-SPINE.md (docqa-lite)

Method: read-only. Checked the spine against app/main.py, search.py, ingest.py, repository.py, models.py and the PRD (epics 1-3). Each finding is two units that obey every AD to the letter yet diverge, plus the AD fix.

Verdict: sound for the current code, but not yet safe for parallel story work. The spine ratifies today's code and leaves the seams between ADs open. Five holes need new or tightened ADs before stories fan out. None needs a design change.

## F1 (critical) Sample loading bypasses AD-6 and can make the wire layer 500

- Unit A (Epic 1, FR1) adds sample files, for example a zero-byte `empty.md`, a `.md` over 1 MB, or a whitespace-only file. Under AD-1/AD-2/AD-7 it only calls `load_sample_dir`, which skips only unreadable or non-UTF-8 files.
- Unit B (Epic 3, NFR2) hardens upload validation in `decode_upload` per AD-6 and tests only uploads.
- Result: `Document(size=0)` or `size>1_048_576` enters the repository. `DocumentSummary` declares `size: Field(ge=1, le=1_048_576)`, so `GET /documents` fails response validation and returns a 5xx for the whole library. AD-6 ("never yields a 5xx") covers uploads only, and AD-6 lists no sample-side rule.
- Related, FR1 divergence: `load_sample_dir` globs `*.md`, while FR2 accepts `.markdown`. "Every Markdown file" is undefined.
- Related, validation gap: `decode_upload` only rejects blank content. A file made only of stop words or punctuation (`the and of`) returns 201 but can never be a hit. If it is the only document, `rebuild` sets `_snapshot=None`. This breaks FR3 ("appears in the next search") with no AD owning the case.
- Fix, new AD-10 "One admission gate": every Document, from any source, passes the same invariants before `repository.add`. Those are 1 <= size <= MAX_BYTES, valid UTF-8, non-blank, title 1..200, filename 1..255. Sample loading skips (and logs `sample_skipped`) any file that fails. Also state that the wire models' constraints are a subset of the admission gate. Decide explicitly whether a content-with-no-indexable-terms upload is rejected 422 or accepted but unsearchable, and whether samples are `*.md` only.

## F2 (high) AD-3 mutation path is contradicted by the code and has no failure atomicity

- Unit A (a "delete" or "bulk upload" story) copies the upload route's pattern: `with lock: repository.add(...); index.rebuild(...)` inside the route. This obeys AD-3 literally ("inside app.state.lock"). AD-3's "routes never call add/rebuild separately" is violated by the existing `upload_document`, which calls both. "Extract when a second caller appears" gives the second developer no named function and no owner.
- Unit B (Epic 2, perf fix) changes `rebuild` to raise on resource errors, or adds validation inside rebuild. In the route, `repository.add` has already happened and no rollback exists. The repository then holds a doc the index lacks, the route returns a 5xx, and list, get and search disagree permanently. AD-3 and AD-6 are silent on ordering (add then rebuild, versus build the new snapshot first and then commit).
- Also: `rebuild` swallows only `ValueError`, so the "empty vocabulary" case silently drops the index for the whole library. A later caller cannot tell "no hits" from "index dropped".
- Fix, tighten AD-3: name one function now (`Library.mutate`, or `add_document(state, doc)` in main.py). Order is build the new snapshot from `repository.list() + [doc]`, then `repository.add`, then swap, all under the lock, with failure leaving both unchanged. Only that function may call `repository.add` or `index.rebuild` after start-up. The lifespan is the single documented exception.

## F3 (high) Repository Protocol has no ordering or duplicate-id contract, yet AD-7 depends on it

- Unit A (new backend, per AD-2, "implement the Protocol") returns `list()` from a database in primary-key or id order (uuid hex is random). It satisfies the Protocol types and AD-2.
- Unit B (search, AD-7 "ties keep insertion order") assumes `list()` is insertion order, with samples first.
- Result: ordering of `GET /documents` and of search ties changes. `add` of an existing id silently replaces in the in-memory adapter. Another adapter would raise or append.
- Fix, tighten AD-2/AD-7: the Protocol contract is `list()` returns insertion order, `add` of a duplicate id raises (or is a documented no-op), and `get` is O(1). Add a contract test that any adapter must pass.

## F4 (medium) Tie-order and score-rounding ambiguity breaks FR6 determinism

- AD-7 says "stable sort, ties keep insertion order... scores rounded to 4 dp".
- Unit A sorts on raw cosine scores (the current code). Unit B, reading "rank by the reported score", sorts on rounded scores.
- Result: two docs with raw 0.50004 and 0.50001 both display 0.5; A orders by raw value, B by insertion order. Raw near-ties can also flip across BLAS or numpy builds, so "identical results" is not guaranteed.
- Fix, tighten AD-7: rank key is the rounded (4 dp) score, ties break on insertion index. Do this by sorting on `(-rounded, index)`, not a stable argsort of raw floats.

## F5 (medium) Contradiction between "never echoed" and the wire, plus error-body shape

- AD-8 says content is "never logged or echoed" and the convention says the error body is `{"detail": "<readable reason>"}`.
- Real behaviour: `SearchResponse.query` echoes the (stripped) query text, which is the intended contract. FastAPI's built-in 422 for `q` over 500 chars or a bad `k` returns `detail` as a list of objects that include an `input` field with the offending value, and the same happens for a missing multipart `file`. The query text is echoed in an error body, and `detail` is not a string.
- Unit A (Epic 3) asserts `detail` is a string and adds a custom handler. Unit B asserts the default list shape (the existing tests may already pin it). Both read AD-6 and the convention as satisfied.
- Fix, tighten AD-8/AD-6: define "echoed" as "in error bodies and logs only" (the success `query` field is allowed). State the single 422 body shape for validation errors (default list or a string via one handler in `create_app`), and say whether `input` may appear. Only `create_app` registers exception handlers.

## F6 (medium) No rule that routes are sync `def`, and the perf test seeding path is unspecified

- AD-4 and AD-3 rely on a `threading.Lock` plus FastAPI's threadpool, which is true only for `def` routes. Unit A adds a new route as `async def` that takes the lock and calls `rebuild`. It obeys every AD, but blocks the event loop for the whole O(n) TF-IDF build, which stalls every search (AD-4's lock-free read promise) and can deadlock with a threadpool writer holding the lock.
- Epic 2 needs 1,000 documents (NFR1). Unit A seeds by 1,000 `POST /documents` (each does a full rebuild, so O(n^2)). Unit B seeds by writing `app.state.repository.add` plus `index.rebuild` directly, which AD-3 and AD-2 forbid for "routes" but not for tests. Neither is ruled out, and the two tests measure different things (cold versus warm index).
- Fix: add to AD-1 or AD-4 "Routes that touch the lock or the index are sync `def`; blocking work is never done in `async def`." Add a test-seeding rule: a `make_client(docs=...)` fixture or a `build_library(documents)` helper in `tests/helpers` is the only way to bulk-seed, and it goes through the same function as F2.

## Lower-severity notes

- (low) Bare `TestClient(app)` without the lifespan makes `app.state.repository` missing and every route a 500. This is a convention, not an AD-6 guarantee. Optionally make routes fail closed or fail at import.
- (low) `list_documents` and `get_document` read the repository without the lock while writers mutate the dict. CPython makes `list(dict.values())` effectively atomic, but AD-4 does not state "reads are safe only because of the GIL". A non-CPython or non-dict adapter (F3) would break it.
- (low) `size` is `len(data)` for uploads (bytes, BOM included) and `len(raw)` for samples. Consistent today, but undocumented. State "size is the byte length of the stored file".
- (low) NFR1 and AD-4 are in tension: the "fix the search path" branch of Epic 2 cannot use incremental or lazy indexing. The spine should say the fix space is query-path only (for example cache the analyzer, avoid per-call `build_analyzer`), so the Epic 2 story does not propose a rebuild change.

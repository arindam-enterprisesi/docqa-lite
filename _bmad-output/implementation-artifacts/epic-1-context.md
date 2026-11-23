# Epic 1 Context: Dependable document library

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Content owners can add documents and anyone can list and read them, with the baseline behavior locked so it can't regress. This is brownfield: the API already exists and is tested, so the work is confirming behavior, locking it with tests, and closing gaps. There is no greenfield setup.

## Stories

- Story 1.1: Sample documents load at start-up
- Story 1.2: Upload a Markdown or text document
- Story 1.3: List documents in a predictable order
- Story 1.4: Read one document
- Story 1.5: Lock the API contract

## Requirements & Constraints

- Every Markdown sample in `data/sample_docs/` loads at start-up, so it is listable and searchable with no user action.
- Upload accepts `.md`, `.markdown`, `.txt`: valid UTF-8, 1 to 1,048,576 bytes. It returns 201 with id, title, filename and size. Title is the first level-1 heading, else the filename without its extension. `size` is the stored byte length.
- `GET /documents` returns id, title, filename and size, never full content. `GET /documents/{id}` returns metadata plus full content, and 404 with a string `detail` for an unknown id.
- Every existing endpoint, status code and response shape stays unchanged. The existing test suite keeps passing. The only permitted test change is the opt-in timing threshold (Epic 2).
- Invalid input gets a 4xx with a readable reason, never a 5xx. Document contents never reach logs or error messages.
- Out of scope: auth, PDF/binary formats, update/delete, persistence, any API contract change.

## Technical Decisions

- Layering: `main` imports `ingest`/`search`/`models`/`repository`. `ingest` and `search` never import each other, `main`, or FastAPI. `repository` and `models` import nothing from `app`.
- Only `create_app()` builds repository, index and lock, in its lifespan. State lives only on `app.state` (`repository`, `index`, `lock`), with no module-level mutable state. Routes that take the lock stay sync `def`.
- All storage goes through `DocumentRepository` (`add`, `get`, `list`). `Document` is frozen. `list()` returns insertion order, ids are unique, and `get` returns `None` for an unknown id. Any new adapter must pass the same contract tests.
- Each library mutation does the repository change and the full index rebuild together inside `app.state.lock`, all-or-nothing. A failed rebuild leaves both unchanged and is a logged 5xx. Extract the upload block into one named function before a second mutation caller exists.
- Upload checks live in `ingest.py` (`sanitize_filename`, `check_extension`, `decode_upload`) and raise `UploadRejected(status_code, detail)`, converted to `HTTPException`. Status map: 413 too large, 415 wrong type, 422 invalid content, 404 unknown id.
- There are two frozen error body shapes: string `detail` for this code's rejections, and FastAPI's list `detail` for framework validation. No custom exception handlers.
- Read at most `MAX_BYTES + 1`; never trust `Content-Length`. Reduce filenames to a base name.
- Every document, from upload or sample, passes the same admission checks before `repository.add`: size 1 to 1,048,576, valid UTF-8, non-empty text, title 1-200 chars, filename 1-255 chars. Wire model constraints are never stricter than the gate. A failing sample is skipped and logged by filename only.
- Open questions: whether `.markdown` samples load (today `load_sample_dir` globs only `*.md`), and whether an upload with no indexable terms is accepted (today: 201 but never findable; lock that behavior with a test).
- Listing order: samples first (sorted by filename), then uploads in upload order.
- Logging uses the `docqa` logger with `key=value` events, ids/filenames/sizes only. Ids come from `new_id()` (`uuid4().hex`) only. Limits are module constants. Python 3.11 floor.
- Single process only. State is in memory and lost on restart.
- The public API contract is frozen by `specs/001-document-library-search/contracts/` and the existing tests.

## Cross-Story Dependencies

- 1.1 fixes the sample loader and gate that 1.2's admission checks share (same gate for samples and uploads).
- 1.3's ordering rule depends on 1.1 (samples sorted by filename) and 1.2 (upload order).
- 1.5 closes the epic, so it runs last and guards all of 1.1-1.4.
- Epic 2 (search, new-upload searchability) and Epic 3 (error handling, log privacy) build on this baseline.

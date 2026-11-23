---
status: final
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-docqa-lite-2026-11-22/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-docqa-lite-2026-11-22/ARCHITECTURE-SPINE.md
---

# docqa-lite - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for docqa-lite, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: At start-up the system loads every Markdown file in `data/sample_docs/` into the Library, so they are listable and searchable with no user action.
FR2: A user can upload one `.md`, `.markdown` or `.txt` file of valid UTF-8 text, up to 1 MB, via `POST /documents`. The system returns 201 with the new id, title, filename and size. The title is the first level-1 heading, else the filename without its extension.
FR3: An uploaded Document appears in the results of the next search.
FR4: `GET /documents` returns every Document with id, title, filename and size, without full content.
FR5: `GET /documents/{id}` returns metadata and full content. An unknown id returns a not-found response.
FR6: `GET /search?q=&k=` ranks Documents by TF-IDF relevance to the Query and returns at most k Search Results (k from 1 to 20, default 5), best first. Each has id, title, a score from 0 to 1, and a snippet of at most 200 characters. Documents with zero relevance are not returned. The same Query over the same Library always returns identical results, and no external or AI service is used.

### NonFunctional Requirements

NFR1: Search over a Library of 1,000 Documents responds in under 300 ms. Measured as the median of repeated searches against a warm index on the development environment, through the opt-in `DOCQA_PERF=1` check (the constitution bans wall-clock assertions in default tests). The existing threshold is under 1 s, so this is a tighter bar.
NFR2: Each of these invalid inputs is rejected with a 4xx response and a human-readable reason, and none causes a 5xx: a disallowed file type (415), an empty file, a file over 1,048,576 bytes (413), non-UTF-8 content, an empty or whitespace-only Query, a Query over 500 characters, and k outside 1 to 20 (422 where no other code applies). Document contents are never written to logs or error messages.
NFR3: Every existing endpoint, status code and response shape is unchanged. The existing test suite continues to pass. The one permitted test change is tightening the opt-in timing threshold to meet NFR1.

### Additional Requirements

- Brownfield: the API already exists and is tested; there is no starter template and no greenfield setup story. Work is confirming, locking and closing gaps (PRD epics 1-3).
- AD-1: Imports follow the layering (`main` -> `ingest`/`search`/`models`/`repository`; `ingest` and `search` never import each other, `main` or FastAPI; `repository` and `models` import nothing from `app`). Only `create_app()` builds the repository, index and lock, in its lifespan. State lives only on `app.state` (`repository`, `index`, `lock`); no module-level mutable state. Routes taking the lock stay sync `def`.
- AD-2: All storage goes through `DocumentRepository` (`add`, `get`, `list`). `Document` is frozen. `list()` returns insertion order, ids unique, `get` returns `None` for unknown id. Any new adapter must pass the same contract tests.
- AD-3: Every library mutation does the repository change and index rebuild together inside `app.state.lock`, all-or-nothing; a failed rebuild leaves both unchanged and is a logged 5xx. Extract the upload block into one named function before a second mutation caller exists.
- AD-4: The index is rebuilt in full on every mutation and replaces the `_Snapshot` in a single reference assignment. Search reads the snapshot lock-free. Perf tests seed 1,000 documents via the repository and one rebuild, not 1,000 uploads. No incremental or lazy updates.
- AD-5: Exactly one process (no `--workers`, no replicas); state is in memory and lost on restart.
- AD-6: Upload checks live in `ingest.py` (`sanitize_filename`, `check_extension`, `decode_upload`) raising `UploadRejected(status_code, detail)`, converted to `HTTPException`. Query limits (length 1-500, non-blank, k 1-20) via route `Query` declarations plus a whitespace check, 422. Status map: 413 too large, 415 wrong type, 422 invalid content/query, 404 unknown id. Two frozen error body shapes (string `detail` for this code's rejections; FastAPI's list `detail` for framework validation). No custom exception handlers. Bounded read of `MAX_BYTES + 1`; `Content-Length` never trusted. Filenames reduced to a base name.
- AD-7: `GET /documents` returns samples first (sorted by filename), then uploads in upload order. Search orders by rounded score descending, then insertion order. Scores rounded to 4 decimals, capped at 1.0, zero scores dropped after rounding (today's code sorts on the raw score; the rounded key is the rule). Snippets at most 200 chars. No wall-clock, randomness or external service.
- AD-8: Log via the `docqa` logger as `key=value` events with ids, filenames and sizes only; never document content or query text. Run targets start uvicorn with `--no-access-log`.
- AD-9: The public API contract (endpoints, status codes, response shapes) is frozen by `specs/001-document-library-search/contracts/` and the existing tests.
- AD-10: Every document, from upload or sample, passes the same admission checks before `repository.add`: size 1 to 1,048,576 bytes, valid UTF-8, non-empty text, title 1-200 chars, filename 1-255 chars. Wire model constraints are never stricter than the gate. A failing sample is skipped and logged by filename. Open: whether `.markdown` samples load, and whether an upload with no indexable terms is accepted (today: 201 but never findable).
- Conventions: ids are `uuid4().hex` from `new_id()` only; `size` is the stored byte length; limits are module constants; Python 3.11 floor; test first; library tests use the `client` / `make_client` fixtures, never a bare `TestClient(app)`; `DOCQA_PERF=1` gates every wall-clock check; run targets are only `make run` and in-process `TestClient`.
- Out of scope: auth and per-user libraries, PDF/binary formats, AI answers, update/delete, persistence, any change to the API contract.
- Deferred (no stories): upload latency ceiling at ~1,000 docs, multi-process/persistent storage, update/delete, deployment target, env config, library size cap, `docqa` log handler/level, spooled multipart before 413, missing-sample-dir warning, import-graph test for AD-1/AD-5.

### UX Design Requirements

None. No UX design document exists; docqa-lite is an API-only service.

### FR Coverage Map

FR1: Epic 1 - Sample documents load at start-up through the admission gate
FR2: Epic 1 - Upload a Markdown or text document
FR3: Epic 2 - An uploaded document is searchable on the next search
FR4: Epic 1 - List documents, with deterministic ordering
FR5: Epic 1 - Get a document, 404 for an unknown id
FR6: Epic 2 - Deterministic TF-IDF search
NFR1: Epic 2 - Search under 300 ms at 1,000 documents
NFR2: Epic 3 - Invalid input gets a clear 4xx, never a 5xx; content is never logged
NFR3: Epic 1 - Frozen API and existing tests (guardrail for all epics)

## Epic List

### Epic 1: Dependable document library
Content owners can add documents and anyone can list and read them, confident the baseline behavior can't regress.
**FRs covered:** FR1, FR2, FR4, FR5 (NFR3)

### Epic 2: Fast, accurate search
An employee types plain words and gets the right policy back quickly, and a newly uploaded document is findable on the next search.
**FRs covered:** FR3, FR6 (NFR1)

### Epic 3: Safe handling of bad input
Anyone who sends a bad file or query gets a clear 4xx reason, never a server error, and document and query text never reach the logs.
**FRs covered:** none directly (NFR2)

## Epic 1: Dependable document library

Content owners can add documents and anyone can list and read them, confident the baseline behavior can't regress.

### Story 1.1: Sample documents load at start-up

As an employee,
I want the sample policy documents available the moment the service starts,
So that I can search without uploading anything.

**Implements:** FR1, NFR2; AD-1, AD-2, AD-7, AD-10

**Acceptance Criteria:**

**Given** `data/sample_docs/` holds `.md` and `.markdown` files
**When** the app starts
**Then** every one is in the Library and listed
**And** the `.markdown` case is written test-first, then `load_sample_dir` is fixed (today it globs only `*.md`)

**Given** a sample is empty, over 1,048,576 bytes, or not valid UTF-8
**When** the app starts
**Then** that file is skipped and logged by filename only (AD-10)
**And** the app still starts and `GET /documents` returns 200

**Given** the 5 shipped sample documents and the `client` fixture
**When** the library is listed
**Then** all 5 are present

### Story 1.2: Upload a Markdown or text document

As a content owner,
I want to upload a `.md`, `.markdown` or `.txt` file,
So that it joins the Library.

**Implements:** FR2, NFR2; AD-2, AD-3, AD-6, AD-10

**Acceptance Criteria:**

**Given** a valid UTF-8 file of 1 byte to 1,048,576 bytes
**When** I `POST /documents`
**Then** I get 201 with id, title, filename and size
**And** `size` is the stored byte length

**Given** content with a level-1 heading
**When** it is uploaded
**Then** the title is that heading
**And** with no heading the title is the filename without its extension

**Given** a filename containing a path such as `../../x.md`
**When** it is uploaded
**Then** only the base name is stored (AD-6)

**Given** an upload with no indexable terms (for example only stop words)
**When** it is uploaded
**Then** it returns 201 as today
**And** a test documents and locks that behavior

### Story 1.3: List documents in a predictable order

As an employee,
I want to see every document in the Library,
So that I know what it holds.

**Implements:** FR4; AD-2, AD-7

**Acceptance Criteria:**

**Given** the samples and two uploads
**When** I call `GET /documents`
**Then** samples come first sorted by filename, then uploads in upload order (AD-7)

**Given** any Library
**When** I call `GET /documents`
**Then** each item has id, title, filename and size
**And** never the full content

### Story 1.4: Read one document

As an employee,
I want to open a document by id,
So that I can read the full policy.

**Implements:** FR5; AD-2, AD-6

**Acceptance Criteria:**

**Given** a valid id
**When** I call `GET /documents/{id}`
**Then** I get 200 with metadata and full content

**Given** an unknown id
**When** I call `GET /documents/{id}`
**Then** I get 404 with a string `detail`

### Story 1.5: Lock the API contract

As a maintainer,
I want a guard on the public contract,
So that no later change slips in unnoticed.

**Implements:** NFR3; AD-9

**Acceptance Criteria:**

**Given** the files in `specs/001-document-library-search/contracts/`
**When** the contract test runs
**Then** it asserts the status codes and response field names of all five endpoints (NFR3, AD-9)

**Given** the full existing test suite
**When** `make test` and `make lint` run
**Then** both pass with no test changed except the permitted opt-in timing threshold (NFR3)

## Epic 2: Fast, accurate search

An employee types plain words and gets the right policy back quickly, and a newly uploaded document is findable on the next search.

### Story 2.1: Find the right policy with plain words

As an employee,
I want to type plain words and get the matching documents back,
So that I find the policy without knowing which file holds it.

**Implements:** FR6; AD-4, AD-7

**Acceptance Criteria:**

**Given** a distinctive phrase from each of the 5 sample documents
**When** I call `GET /search?q=...`
**Then** that document is the top result, 5 of 5

**Given** a matching query
**When** results are returned
**Then** each has id, title, a score from 0 to 1, and a snippet of at most 200 characters

**Given** a query that matches nothing
**When** I search
**Then** I get 200 with an empty list
**And** documents with zero relevance are never returned

**Given** `k` is omitted
**When** I search
**Then** at most 5 results come back, best first
**And** with `k` from 1 to 20, at most k come back

### Story 2.2: Same query, same results, every time

As an employee,
I want identical results for identical queries,
So that I can trust what I see.

**Implements:** FR6; AD-7

**Acceptance Criteria:**

**Given** the same Library and the same query
**When** I search twice
**Then** the two responses are identical

**Given** two documents whose scores tie after rounding to 4 decimals
**When** I search
**Then** they are ordered by insertion order (AD-7)
**And** the test is written first with a tie that exists only after rounding, then the sort key is changed from the raw score to the rounded score

**Given** any search
**When** results are produced
**Then** no wall-clock time, randomness or external or AI service influences them

### Story 2.3: An uploaded document is searchable on the next search

As a content owner,
I want my upload to show up in search straight away,
So that I don't wait for it to be indexed.

**Implements:** FR3; AD-3, AD-4, AD-5

**Acceptance Criteria:**

**Given** a new upload containing a distinctive phrase
**When** the 201 comes back and I search for that phrase
**Then** the uploaded document is the top result

**Given** an upload that fails validation
**When** the rejection is returned
**Then** the Library and index are unchanged
**And** earlier search results are identical (AD-3)

### Story 2.4: Search stays under 300 ms at 1,000 documents

As an employee,
I want search to stay fast on a large Library,
So that it never slows me down.

**Implements:** NFR1, NFR3; AD-4

**Acceptance Criteria:**

**Given** 1,000 documents seeded through the repository plus one index rebuild (AD-4)
**When** the opt-in `DOCQA_PERF=1` check runs
**Then** the median of repeated searches on a warm index is under 300 ms
**And** the timing threshold in the existing test is tightened from 1 s to 300 ms, the one permitted test change (NFR3)

**Given** the check fails
**When** the story is implemented
**Then** the search path is fixed until it passes
**And** if it already passes, the story is only the threshold change

**Given** a default test run (no `DOCQA_PERF`)
**When** the suite runs
**Then** it contains no wall-clock assertion

## Epic 3: Safe handling of bad input

Anyone who sends a bad file or query gets a clear 4xx reason, never a server error, and document and query text never reach the logs.

### Story 3.1: A bad upload gets a clear reason

As a content owner,
I want a clear message when my file is rejected,
So that I know how to fix it.

**Implements:** NFR2; AD-6, AD-10

**Acceptance Criteria:**

**Given** a disallowed file type such as `.pdf` or `.docx`
**When** I upload it
**Then** I get 415 with a string `detail` naming the accepted types

**Given** an empty file
**When** I upload it
**Then** I get 422 with a readable reason

**Given** a file over 1,048,576 bytes
**When** I upload it
**Then** I get 413
**And** the server reads at most `MAX_BYTES + 1` and never trusts `Content-Length` (AD-6)

**Given** non-UTF-8 content
**When** I upload it
**Then** I get 422

**Given** a request with no `file` part
**When** I upload
**Then** I get FastAPI's default 422 with a list `detail`
**And** the two frozen error body shapes are unchanged (AD-6, AD-9)

**Given** any of the above
**When** the response is returned
**Then** it is never a 5xx

### Story 3.2: A bad search gets a clear reason

As an employee,
I want a clear message when my query is invalid,
So that I can correct it.

**Implements:** NFR2; AD-6

**Acceptance Criteria:**

**Given** an empty or whitespace-only `q`
**When** I search
**Then** I get 422

**Given** `q` longer than 500 characters
**When** I search
**Then** I get 422

**Given** `k` of 0, 21 or a non-number
**When** I search
**Then** I get 422

**Given** `q` of 1 and of 500 characters, and `k` of 1 and of 20
**When** I search
**Then** each request succeeds

**Given** any of the above
**When** the response is returned
**Then** it is never a 5xx

### Story 3.3: Document and query text never reach the logs

As a content owner,
I want assurance that my documents and searches are not logged,
So that sensitive policy text stays private.

**Implements:** NFR2; AD-8

**Acceptance Criteria:**

**Given** an upload containing a unique marker string
**When** it succeeds or is rejected
**Then** the marker appears in neither the server log nor the error body (AD-8)

**Given** a search for a unique marker string
**When** the search completes
**Then** the marker does not appear in the server log
**And** the `query` field in the successful response is unchanged, as it is part of the frozen contract

**Given** the log assertions
**When** they run
**Then** they use `tests/helpers.server_log_text`, which ignores the client's httpx logs

**Given** the run targets
**When** `make run` starts uvicorn
**Then** it passes `--no-access-log`, because the access log prints the request line with the query string

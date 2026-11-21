# Feature Specification: Document Library with Search

**Feature Branch**: `day-practice`

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "Build a document library with search. Users can upload a Markdown or
plain-text document through the API (max 1 MB), list all documents, fetch one document by id, and
search across documents with a text query that returns the top k results with a relevance score and
a short snippet. The five files in data/sample_docs are loaded automatically at start-up. Out of
scope for now: authentication, PDF files, AI-generated answers."

## Clarifications

### Session 2026-11-21

- Q: Should documents that users upload still be there after the service restarts? → A: No —
  in-memory only; uploads are lost on restart and the 5 sample documents are reloaded each start.
- Q: How should the service decide whether an uploaded file is an allowed Markdown or plain-text
  file? → A: Extension `.md`, `.markdown` or `.txt` (case-insensitive) plus valid UTF-8 content;
  the client-declared content type is ignored.
- Q: Should there be a limit on how many documents the library can hold? → A: Yes — at most 100
  documents in total (samples included); further uploads are rejected with a "library full"
  error until restart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search the library (Priority: P1)

An employee looking for policy information types a question or keywords (e.g. "meal allowance
limit") and gets back the most relevant documents, ranked best-first, each with a relevance score
and a short snippet of text so they can judge relevance without opening the document.

**Why this priority**: Finding information is the core value of the library. Because the five
sample policy documents are loaded automatically, search delivers value on day one even before
anyone uploads anything.

**Independent Test**: Start the service with only the sample documents, search for "annual leave
days", and confirm the leave policy is the top result with a positive score and a snippet.

**Acceptance Scenarios**:

1. **Given** the library contains the sample documents, **When** a user searches for "reimbursed
   meals receipt", **Then** the expense policy is ranked first and the result includes its id,
   title, a relevance score, and a snippet.
2. **Given** the library contains the sample documents, **When** a user searches with k = 2,
   **Then** at most 2 results are returned, ordered by descending score.
3. **Given** the library contains the sample documents, **When** a user searches for a term that
   appears in no document (e.g. "zxqvy"), **Then** an empty result list is returned (not an
   error).
4. **Given** any library state, **When** a user submits an empty or whitespace-only query,
   **Then** the request is rejected with a clear validation error.

---

### User Story 2 - Upload a document (Priority: P2)

A user adds a new Markdown or plain-text document to the library. The system stores it, assigns it
an identifier, and makes it immediately searchable.

**Why this priority**: Uploading lets the library grow beyond the built-in samples; without it the
library is read-only.

**Independent Test**: Upload a small `.txt` file containing a unique word, confirm the response
contains a new id, then search for that word and confirm the uploaded document is returned.

**Acceptance Scenarios**:

1. **Given** a valid Markdown file under 1 MB, **When** the user uploads it, **Then** the system
   confirms creation and returns the new document's id, title, filename, and size.
2. **Given** a document was just uploaded, **When** the user searches for a word unique to it,
   **Then** that document appears in the results.
3. **Given** a file larger than 1 MB, **When** the user uploads it, **Then** the upload is
   rejected with an error stating the size limit, and nothing is stored.
4. **Given** a file that is not Markdown or plain text (e.g. a PDF), **When** the user uploads it,
   **Then** the upload is rejected with an error stating the accepted types, and nothing is
   stored.
5. **Given** an empty file, **When** the user uploads it, **Then** the upload is rejected.
6. **Given** the library already holds 100 documents, **When** the user uploads another valid
   file, **Then** the upload is rejected with a "library full" error and the document count stays
   at 100.

---

### User Story 3 - Browse and read documents (Priority: P3)

A user lists every document in the library to see what is available, and opens a single document by
its id to read its full content.

**Why this priority**: Browsing complements search and lets users read a full document after
finding it via a snippet, but the library is still useful without it.

**Independent Test**: List documents on a fresh start and confirm exactly the five sample documents
appear; fetch one by id and confirm the full content is returned.

**Acceptance Scenarios**:

1. **Given** a freshly started library, **When** the user lists documents, **Then** exactly the
   five sample documents are listed, each with id, title, filename, and size (but not full
   content).
2. **Given** a document exists, **When** the user fetches it by id, **Then** its id, title,
   filename, size, and full content are returned.
3. **Given** an id that does not exist, **When** the user fetches it, **Then** a "not found" error
   is returned.
4. **Given** a document was uploaded, **When** the user lists documents, **Then** the list
   includes it.

---

### Edge Cases

- File exactly 1 MB (1,048,576 bytes) is accepted; 1 byte more is rejected.
- File whose bytes are not valid UTF-8 text is rejected as unreadable.
- `NOTES.MD` (upper-case extension) is accepted; `notes.md` sent with a declared type of
  `application/octet-stream` is accepted; `report.pdf` is rejected even if declared as
  `text/plain`; a file with no extension is rejected.
- Filename containing path separators or traversal sequences (e.g. `../../etc/passwd.md`) is
  accepted only as a display name and never influences where anything is stored.
- Two uploads with the same filename or identical content are both accepted and receive distinct
  ids.
- k of 0, negative, or above the maximum is rejected with a validation error.
- k larger than the number of matching documents returns only the matching documents.
- Query made only of very common words (e.g. "the and of") returns an empty list or low-scoring
  results, never an error.
- Overly long query (above the maximum length) is rejected.
- A sample document missing or unreadable at start-up does not prevent the service from starting;
  the remaining documents are loaded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load every Markdown file in the sample documents folder into the library
  automatically when the service starts, with no user action.
- **FR-002**: Users MUST be able to upload a single document whose filename ends in `.md`,
  `.markdown` or `.txt` (case-insensitive) and whose content is valid UTF-8 text. The file type
  declared by the client MUST be ignored for this decision.
- **FR-003**: System MUST reject uploads larger than 1 MB (1,048,576 bytes), empty uploads, uploads
  with any other file type, and uploads that are not valid UTF-8 text, with a descriptive error and
  without storing anything.
- **FR-004**: System MUST assign each stored document a unique, opaque identifier and return it on
  successful upload.
- **FR-005**: System MUST derive a document title from its first Markdown level-1 heading if
  present, otherwise from the filename without extension.
- **FR-006**: Users MUST be able to list all documents; each list entry MUST include id, title,
  filename, and size in bytes, and MUST NOT include the full content.
- **FR-007**: Users MUST be able to fetch one document by id, receiving id, title, filename, size,
  and full content; an unknown id MUST produce a "not found" error.
- **FR-008**: Users MUST be able to search with a text query and an optional result count k
  (default 5, minimum 1, maximum 20).
- **FR-009**: Search MUST return at most k results ordered by descending relevance score; each
  result MUST include document id, title, a relevance score between 0 and 1, and a snippet.
- **FR-010**: Search MUST exclude documents with no relevance to the query (score of 0).
- **FR-011**: The snippet MUST be a passage of at most 200 characters taken from the document text,
  centred on the first occurrence of a query term where one exists, otherwise the document's
  opening text.
- **FR-012**: Queries MUST be 1–500 characters after trimming whitespace; empty or over-long
  queries MUST be rejected with a validation error.
- **FR-013**: Newly uploaded documents MUST be searchable immediately after the upload succeeds.
- **FR-014**: Search results MUST be deterministic: the same library contents and query always
  produce the same results, scores, and order (ties broken by document id).
- **FR-015**: Search relevance MUST be computed locally from document text, without calls to any
  external or AI service.
- **FR-016**: System MUST NOT record document contents or query text in logs.
- **FR-017**: Uploaded filenames MUST be treated as display metadata only and MUST NOT determine
  any storage location.
- **FR-018**: The library MUST be held in memory only: uploaded documents MUST NOT be written to
  disk, are lost when the service restarts, and after a restart the library contains exactly the
  sample documents.
- **FR-019**: The library MUST hold at most 100 documents in total, sample documents included. An
  upload that would exceed this limit MUST be rejected with a descriptive "library full" error and
  MUST NOT be stored.

### Key Entities

- **Document**: A unit of text in the library. Attributes: id (unique, assigned by the system),
  title (derived), filename (as supplied, display only), size in bytes, full text content, and
  source (sample or uploaded).
- **Search Result**: A ranked match for a query. Attributes: document id, title, relevance score
  (0–1), snippet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Immediately after start-up, 100% of the five sample documents are listed and
  searchable without any manual step.
- **SC-002**: For each sample document, a query built from a distinctive phrase in that document
  ranks it first (5 of 5).
- **SC-003**: With the library holding up to 100 documents, search results are returned in under
  1 second.
- **SC-004**: An uploaded document is findable by search on the very next request (0 delay).
- **SC-005**: 100% of invalid inputs listed in the requirements and edge cases (oversize, empty,
  wrong type, non-UTF-8, bad k, empty/over-long query, unknown id, library full) receive a descriptive client
  error and never a server failure.
- **SC-006**: The automated test suite for this feature runs without network access and completes
  in under 30 seconds.

## Assumptions

- **Storage is in-memory**: uploaded documents are kept for the lifetime of the running service and
  are lost on restart; the sample documents are reloaded on every start. Persistent storage is out
  of scope.
- Only Markdown (`.md`, `.markdown`) and plain-text (`.txt`) files are accepted; file type is
  judged by extension (case-insensitive) and content being valid UTF-8 text, never by the
  client-declared type.
- Sample documents are loaded from the project's sample documents folder; only `.md` files there
  are loaded.
- No update or delete of documents in this iteration.
- Duplicate uploads are allowed; no de-duplication is performed.
- Single-user/training usage; the library is capped at 100 documents (FR-019), so no scale target
  beyond SC-003 applies.
- Out of scope: authentication/authorisation, PDF and other binary formats, AI-generated answers or
  summaries, pagination of the document list.

# Feature Specification: Document Library with Search

**Feature Branch**: `001-document-library-search`

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "Build a document library with search. Users can upload a Markdown or plain-text document through the API (max 1 MB), list all documents, fetch one document by id, and search across documents with a text query that returns the top k results with a relevance score and a short snippet. The five files in data/sample_docs are loaded automatically at start-up. Out of scope for now: authentication, PDF files, AI-generated answers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search the policy library (Priority: P1)

An employee has a question such as "how many days of annual leave do I get?" and types a
short text query. The service returns the most relevant documents, best match first, each with
a relevance score and a short snippet so the employee can tell at a glance which document
answers the question.

**Why this priority**: Search is the core value of the library. Because the five sample policy
documents are loaded automatically at start-up, search delivers value on its own even before
anyone uploads a document.

**Independent Test**: Start the service with no uploads, query for "annual leave carry over",
and confirm the Annual Leave Policy is the top result with a score and a snippet.

**Acceptance Scenarios**:

1. **Given** the service has just started, **When** a user searches for "annual leave",
   **Then** the Annual Leave Policy is the first result, with a relevance score and a snippet
   taken from that document.
2. **Given** the service has just started, **When** a user searches for "receipt reimbursement"
   with k = 2, **Then** at most 2 results are returned, the Expense Reimbursement Policy is
   first, and results are ordered from highest to lowest score.
3. **Given** the service has just started, **When** a user searches for a term that appears in
   no document (e.g., "zebra"), **Then** an empty result list is returned (not an error).
4. **Given** any state, **When** a user searches with an empty or whitespace-only query,
   **Then** the request is rejected with a clear validation message.

---

### User Story 2 - Upload a new document (Priority: P2)

A content owner adds a new Markdown or plain-text document to the library. The service accepts
it, assigns it a unique id, and the document immediately becomes searchable alongside the
existing ones.

**Why this priority**: Uploading turns a fixed demo corpus into a usable library, but search
already delivers value without it.

**Independent Test**: Upload a small `.md` file containing a distinctive word, confirm an id is
returned, then search for that word and confirm the new document is the top result.

**Acceptance Scenarios**:

1. **Given** a valid Markdown file under 1 MB, **When** a user uploads it, **Then** the service
   confirms success and returns the new document's id, title, filename, and size.
2. **Given** a document was just uploaded containing the word "quokka", **When** a user searches
   for "quokka", **Then** that document is the first result.
3. **Given** a file larger than 1 MB, **When** a user uploads it, **Then** the upload is rejected
   with a message stating the size limit, and the library is unchanged.
4. **Given** a file that is not Markdown or plain text (e.g., `report.pdf`), **When** a user
   uploads it, **Then** the upload is rejected with a message listing the accepted types.
5. **Given** an empty file or a file that is not valid UTF-8 text, **When** a user uploads it,
   **Then** the upload is rejected with a clear message.

---

### User Story 3 - Browse and read documents (Priority: P3)

A user lists all documents in the library to see what is available, then opens one by its id to
read its full content.

**Why this priority**: Browsing supports discovery and lets users read a search hit in full, but
it is secondary to finding and adding content.

**Independent Test**: Start the service, list documents and confirm the five sample documents
appear; fetch one by id and confirm its full content is returned.

**Acceptance Scenarios**:

1. **Given** the service has just started, **When** a user lists documents, **Then** exactly the
   five sample documents are listed, each with id, title, filename, and size (without full
   content).
2. **Given** a document has been uploaded, **When** a user lists documents, **Then** the list
   includes it in addition to the sample documents.
3. **Given** a known document id, **When** a user fetches it, **Then** the full content and its
   metadata are returned.
4. **Given** an id that does not exist, **When** a user fetches it, **Then** a "not found"
   response is returned.

---

### Edge Cases

- A search with k less than 1 or greater than the maximum (20) is rejected with a validation
  message; when k is omitted the default of 5 is used.
- A search where k is larger than the number of matching documents returns only the matching
  documents (fewer than k results).
- A query made only of very common words (e.g., "the and of") returns an empty list rather than
  arbitrary documents.
- A query longer than 500 characters is rejected with a validation message.
- Uploading a file with the same name or content as an existing document creates a new document
  with a new id (no silent overwrite).
- Uploaded filenames containing path segments (e.g., `../../etc/passwd.md`) are reduced to their
  base name and never affect where or how anything is stored.
- A file exactly 1 MB (1,048,576 bytes) is accepted; one byte more is rejected.
- Two documents with equal scores are returned in a stable, repeatable order.
- If a sample document cannot be read at start-up, is empty, is over 1,048,576 bytes, or is not
  valid UTF-8, the service still starts with the remaining documents and records which file was
  skipped (by name only, never its contents).

## Requirements *(mandatory)*

### Functional Requirements

**Start-up**

- **FR-001**: System MUST automatically load every Markdown file (`.md` or `.markdown`) in the sample
  documents folder (currently five) into the library at start-up, so they are listable and searchable without any
  user action.

**Upload**

- **FR-002**: Users MUST be able to upload a single document as a file.
- **FR-003**: System MUST accept only files with the extensions `.md`, `.markdown`, or `.txt`
  whose content is valid UTF-8 text.
- **FR-004**: System MUST reject files larger than 1 MB (1,048,576 bytes) and empty files.
- **FR-005**: On successful upload, System MUST assign a unique, opaque id and return the
  document's id, title, filename, and size.
- **FR-006**: System MUST derive a document's title from its first Markdown level-1 heading; if
  none exists, the title is the filename without its extension.
- **FR-007**: An uploaded document MUST be included in search results for any subsequent search.

**List and get**

- **FR-008**: Users MUST be able to list all documents; each entry includes id, title, filename,
  and size, but not the full content.
- **FR-009**: Users MUST be able to fetch one document by id, receiving its metadata and full
  content.
- **FR-010**: Fetching an unknown id MUST return a "not found" response.

**Search**

- **FR-011**: Users MUST be able to search with a text query (1–500 non-whitespace-only
  characters) and an optional result count k (integer 1–20, default 5).
- **FR-012**: Search MUST rank documents by textual relevance to the query and return at most k
  results ordered by descending relevance score, with ties broken in a stable, repeatable order.
- **FR-013**: Each search result MUST include the document id, title, a relevance score between
  0 and 1, and a snippet of at most 200 characters taken from the document text, preferring a
  passage that contains a query term.
- **FR-014**: Documents with zero relevance to the query MUST NOT be returned.
- **FR-015**: Search MUST produce identical results for identical library contents and queries
  (deterministic), and MUST NOT depend on any external or AI service.

**Validation and safety**

- **FR-016**: All invalid input (bad file type, size, encoding, query, or k) MUST be rejected with
  a client-error response containing a human-readable reason; invalid input MUST NOT cause a
  server error.
- **FR-017**: System MUST NOT write document contents to logs or error messages.

### Key Entities

- **Document**: A text document in the library. Attributes: id (unique, opaque), title,
  original filename (base name only), size in bytes, full text content, and source (sample or
  uploaded).
- **Search Result**: A ranked match for a query. Attributes: document id, title, relevance score
  (0–1), and snippet (≤ 200 characters).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Immediately after start-up, all 5 sample documents are listable and searchable with
  zero manual steps.
- **SC-002**: For each of the 5 sample documents, a query using a distinctive phrase from that
  document returns it as the top result (5 of 5).
- **SC-003**: A newly uploaded document is findable by search in the very next request.
- **SC-004**: Search results for a library of up to 1,000 documents appear in under 1 second.
- **SC-005**: 100% of invalid uploads and queries in the acceptance scenarios are rejected with a
  clear reason and none cause a server error.
- **SC-006**: Running the same query twice against the same library yields identical results and
  scores every time.

## Assumptions

- Authentication, authorization, and per-user libraries are out of scope; every caller can see
  and upload all documents.
- PDF and other binary formats, and AI-generated answers or summaries, are out of scope.
- The library is held only for the lifetime of the running service: uploaded documents are lost
  on restart, while the sample documents are reloaded at every start-up.
- Updating and deleting documents are out of scope for this feature.
- Duplicate uploads are allowed and each receives its own id.
- Documents are short business texts in English; no language-specific stemming or translation is
  required.
- Search is keyword relevance ranking (term-weighted), not semantic or AI-based.
- Expected scale is small (at most around 1,000 documents) for the training context.

---
title: "PRD: docqa-lite"
status: final
created: 2026-11-22
updated: 2026-11-22
---

# PRD: docqa-lite (MVP, brownfield)

> `[ASSUMPTION]` tags mark inferences not yet confirmed by the author.

## 1. Purpose and Context

docqa-lite is a document library with search: upload Markdown or plain-text documents, list and read them, and find the right one with a plain-words query. **This is a brownfield PRD.** The upload, list, get and search API already exists and is tested (see `specs/001-document-library-search/`). This MVP fixes the requirements, sets two quality bars, and defines the work needed to meet them. It builds on `brief.md` in `_bmad-output/planning-artifacts/briefs/brief-docqa-lite-2026-11-22/` and does not repeat it.

**Primary user** `[ASSUMPTION]`: an employee who needs a specific policy answer and doesn't know which document holds it. **Secondary:** the content owner who adds documents.

**Hard constraint:** the existing API (endpoints, status codes, response shapes) must keep working unchanged.

## 2. Glossary

- **Document** — a text file in the library, with an id, title, filename, size and full content.
- **Library** — the set of all Documents: the sample documents loaded at start-up plus anything uploaded.
- **Query** — the text a user searches with.
- **Search Result** — a matching Document with id, title, relevance score (0 to 1) and snippet.

## 3. Functional Requirements

All FRs describe existing behavior that must be preserved. Endpoints are in parentheses.

- **FR1: Load sample documents.** At start-up the system loads every Markdown file in `data/sample_docs/` into the Library, so they are listable and searchable with no user action.
- **FR2: Upload a Document** (`POST /documents`). A user can upload one `.md`, `.markdown` or `.txt` file of valid UTF-8 text, up to 1 MB. The system returns 201 with the new id, title, filename and size. The title is the first level-1 heading, else the filename without its extension.
- **FR3: Upload is immediately searchable.** An uploaded Document appears in the results of the next search.
- **FR4: List Documents** (`GET /documents`). Returns every Document with id, title, filename and size, without full content.
- **FR5: Get a Document** (`GET /documents/{id}`). Returns metadata and full content. An unknown id returns a not-found response.
- **FR6: Search** (`GET /search?q=&k=`). Ranks Documents by TF-IDF relevance to the Query and returns at most k Search Results (k from 1 to 20, default 5), best first. Each has id, title, a score from 0 to 1, and a snippet of at most 200 characters. Documents with zero relevance are not returned. The same Query over the same Library always returns identical results, and no external or AI service is used.

## 4. Non-Functional Requirements

- **NFR1: Search response time.** Search over a Library of 1,000 Documents responds in **under 300 ms**. `[ASSUMPTION]` Measured as the median of repeated searches against a warm index on the development environment, through the same opt-in check (`DOCQA_PERF=1`) that exists today, because the project constitution bans wall-clock assertions in default tests. The existing spec (SC-004) and benchmark only require under 1 s, so this is a tighter bar.
- **NFR2: Input validation.** Each of these invalid inputs is rejected with a 4xx response and a human-readable reason, and none causes a 5xx: a disallowed file type (415), an empty file, a file over 1,048,576 bytes (413), non-UTF-8 content, an empty or whitespace-only Query, a Query over 500 characters, and k outside 1 to 20 (422 where no other code applies). Document contents are never written to logs or error messages.
- **NFR3: Backward compatibility.** Every existing endpoint, status code and response shape is unchanged. The existing test suite continues to pass. The one permitted test change is tightening the opt-in timing threshold to meet NFR1.

## 5. Epics (MVP)

1. **Epic 1: Protect the library API baseline.** Covers FR1 to FR5 and NFR3. Confirm that tests lock the current upload, list, get and start-up behavior, and close any gap found.
2. **Epic 2: Search that meets the performance bar.** Covers FR6 and NFR1. Tighten the opt-in timing check from under 1 s to under 300 ms at 1,000 Documents, and fix the search path if it fails. Acceptance: a distinctive phrase from each of the 5 sample Documents returns that Document as the top Search Result (5 of 5).
3. **Epic 3: Input validation and safety.** Covers NFR2. Confirm every invalid-input case returns a clear 4xx, and that no Document content reaches the logs.

## 6. Out of Scope (MVP)

Authentication and per-user libraries, PDF and other binary formats, AI-generated answers, update and delete, persistence across restarts, and any change to the existing API contract.

## 7. Risks and Open Items

- `[ASSUMPTION]` The implementation likely already meets most of this, so the real MVP work is proving the 300 ms bar and confirming validation coverage. If NFR1 already passes, Epic 2 shrinks to updating the test.
- The search index is rebuilt on every upload (per project notes). NFR1 covers search time only. Upload latency at 1,000 Documents is not a stated requirement.
- `project-context.md` was requested as an input but does not exist in the repository. This PRD was built from the brief, the spec and the code.
- **Open, to confirm before architecture:** how NFR1 is measured (the median, warm-index, opt-in method in NFR1 is a default, not a decision), and the primary user and problem, which are still inferred from the brief. The opt-in timing check is not enforced in default CI runs.

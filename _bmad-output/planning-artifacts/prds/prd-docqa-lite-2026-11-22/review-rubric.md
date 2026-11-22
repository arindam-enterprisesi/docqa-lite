# PRD Quality Review — docqa-lite (MVP, brownfield)

## Overall verdict
A tight, honest brownfield PRD. Its API claims match `app/main.py` and the existing spec, its scope and risks are candid, and every FR/NFR maps to an epic. What is at risk is the headline NFR (NFR1): its measurement method is loose and conflicts with the project's own no-wall-clock-in-default-tests rule. NFR3 ("existing tests pass without modification") also contradicts Epic 2, which edits an existing test. No critical issues.

## Decision-readiness — adequate
The PRD states its main bet plainly: the code probably already meets most of this, so the work is proving 300 ms and confirming validation. That is stated as a decision, not buried. The tightening from the spec's SC-004 (1 s) to 300 ms is called out. Upload latency at 1,000 Documents is acknowledged and deliberately not required, which is a real trade-off named. It does not say who owns the 300 ms number or why 300 ms rather than 1 s, so the tightening reads as arbitrary.

### Findings
- **low** Rationale for 300 ms missing (§4 NFR1) — The PRD says it is "a tighter bar" than SC-004 but not why. *Fix:* add one clause, or mark the number `[ASSUMPTION]`.

## Substance over theater — strong
There is no persona, innovation or vision theater. NFRs carry real thresholds (300 ms, 1,048,576 bytes, 500 chars, k 1 to 20). The Purpose section is specific to this product. Nothing reads as furniture.

## Strategic coherence — adequate
The thesis is "lock the baseline, then prove two quality bars", and the epics follow it. Success metrics are absent, but for a two-page training PRD the NFRs serve as the bars. Epics 1 and 3 are verification work rather than outcomes. That is appropriate for brownfield, though it makes them look like tasks.

### Findings
- **low** Epics lack a stated completion condition (§5) — Epic 1 says "close any gap found" without saying what done looks like. *Fix:* add a one-line exit criterion per epic (for example "each FR has at least one passing test").

## Done-ness clarity — adequate
FR1 to FR6 are mostly testable. They carry concrete limits (1 MB, 200-char snippet, k 1 to 20, score 0 to 1, 201 on create). Weak spots:

### Findings
- **medium** NFR1 measurement is under-specified and conflicts with project rules (§4 NFR1, §5 Epic 2) — "Measured server-side for a single request on the development environment" has no corpus definition, no warm or cold distinction, no percentile or repeat count, and no hardware. The existing benchmark (`tests/test_search.py::test_search_over_1000_documents_under_one_second`) times `index.search` directly, not the HTTP path, with one wall-clock sample. It is skipped unless `DOCQA_PERF=1`, because the constitution forbids wall-clock assertions in default tests. So the 300 ms bar would never be enforced in CI. *Fix:* define the measurement (corpus size and shape, warm index, median or p95 over N runs, in-process vs HTTP). State that it is an opt-in check. Say whether the constitution exception is acceptable.
- **medium** NFR2 "never causes a 5xx" is universally quantified (§4 NFR2) — It cannot be proven for "every invalid input". Only the enumerated cases are checkable. The cases not listed include a missing `file` part, a non-multipart body, a filename that sanitizes to empty, and an extension-only filename. *Fix:* scope the claim to the listed cases plus "missing or malformed upload body", and drop "every".
- **low** FR5 and NFR2 name no status codes (§3 FR5, §4 NFR2) — The code uses 404, 413, 415 and 422 (`app/main.py`, `app/ingest.py`). NFR3 says status codes are frozen, but the PRD never lists them, so a regression in a status code is not checkable from this document. *Fix:* add a small status-code table (404 unknown id, 413 over 1 MB, 415 bad type, 422 empty / non-UTF-8 / blank query or out-of-range k).
- **low** FR6 drops stable tie-breaking (§3 FR6) — Spec FR-012 requires ties to be ordered stably. The PRD's "identical results" partly covers this but does not state it. FR1 also omits the spec's behavior when a sample file is unreadable (the service starts and skips it). *Fix:* add both, or state they are intentionally dropped.

## Scope honesty — strong
The Out of Scope list is explicit and matches the spec's assumptions (no auth, no PDF, no AI answers, no update or delete, no persistence). The three `[ASSUMPTION]` tags, the missing `project-context.md` and the inferred primary user are all disclosed. Open-items density is appropriate for the stakes. The PRD does not index its assumptions, which is fine at this length.

## Downstream usability — adequate
FR1 to FR6, NFR1 to NFR3 and Epics 1 to 3 have contiguous IDs. Every FR and NFR is covered by at least one epic: FR1 to FR5 and NFR3 by Epic 1, FR6 and NFR1 by Epic 2, NFR2 by Epic 3. There are no orphans.

### Findings
- **medium** NFR3 contradicts Epic 2 (§4 NFR3 vs §5 Epic 2, §7) — NFR3 requires the existing test suite to "continue to pass without modification", but Epic 2 and §7 explicitly change the existing under-1-s timing test to under 300 ms. *Fix:* reword NFR3 to "existing functional tests pass unmodified; the opt-in timing test is the one permitted change".
- **low** Epic 3 splits one requirement's scope oddly (§5) — Epic 3 owns the no-logging half of NFR2, but FR2 and FR6 already touch inputs. This is acceptable, but the epic does not say which tests exist (`tests/test_logging.py` is present). *Fix:* optional cross-reference.

## Shape fit — strong
A capability-spec shape with no user journeys suits a small brownfield API. The brownfield references are accurate. The endpoints, the 1 MB limit, the 500-character query limit, k 1 to 20 with default 5, the 201 status, the title rule and the `data/sample_docs` load all match `app/main.py` and the spec. The one deviation is deliberate and flagged: 300 ms vs the spec's 1 s.

## Mechanical notes
- Glossary use is consistent: Document, Library, Query and Search Result are capitalized throughout. Minor drift: "metadata" (FR4, FR5) and "snippet" (FR6) are not glossary terms. "results" is sometimes lowercase for Search Results.
- IDs are contiguous with no duplicates, and there are no broken cross-references.
- Inline `[ASSUMPTION]` tags (§1 primary user, §4 NFR1 measurement, §7 "likely meets most") have no end index. This is acceptable for the length but would not round-trip if an index were required.
- Front matter says `status: draft`, which is consistent with the open assumptions.
- The reference to `brief.md` resolves; the file exists under `_bmad-output/planning-artifacts/briefs/brief-docqa-lite-2026-11-22/`.

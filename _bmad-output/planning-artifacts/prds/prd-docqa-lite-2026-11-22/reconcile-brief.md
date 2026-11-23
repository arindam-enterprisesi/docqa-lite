# Reconciliation: brief.md vs prd.md

Input: brief-docqa-lite-2026-11-22/brief.md

## Contradictions
- None real. Search latency differs (brief: under 1 s; PRD NFR1: under 300 ms), but the PRD states this is a deliberate tightening per the author's request and cites SC-004. Not a gap.
- Scope in/out, upload limits (1 MB, .md/.markdown/.txt), k default 5 / max 20, 1,000 docs, sample docs at start-up, no persistence: all consistent.

## Gaps (all low severity)
1. Success criterion "a distinctive phrase from each of the 5 sample documents returns that document as the top result (5 of 5)" has no PRD counterpart. FR1/FR6 cover loading and ranking but not this acceptance check. Useful as an Epic 2 acceptance test.
2. Vision / evolution path omitted: persistent storage, update/delete, access control, more file types, later semantic search and generated answers, each added "behind the same tested interface". The PRD lists these only as out of scope, and does not say the interface should stay stable for them. Partly covered by NFR3.
3. Training-exercise context and the "no adoption or business metrics apply" stance are not carried over. The PRD defers to the brief, and `[ASSUMPTION]` tags are retained, so this is minor. The differentiators "no API key / no per-query cost" and "small enough to understand end to end" appear only partly (FR6 says no external or AI service).
4. Content-owner success ("findable immediately, no re-indexing step") is captured by FR3 but the "no re-indexing step" wording is not. Trivial.

## Verdict
No material gaps. The PRD faithfully carries scope, users, constraints and deterministic-by-design intent. Items 1 and 2 are optional additions.

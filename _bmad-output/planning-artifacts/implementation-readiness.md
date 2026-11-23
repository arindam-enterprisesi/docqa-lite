# Implementation Readiness: docqa-lite

**Date:** 2026-11-22
**Verdict:** FAIL — the plan is not implementable as recorded.
**Scope of check:** planning artifacts only (brief, PRD, architecture spine, `epics.md`). Code and tests were not run or compared.

**Question applied:** could a developer implement these epics without inventing decisions nothing records?

## Artifacts inventoried

| Artifact | Path | State |
| --- | --- | --- |
| Brief | `briefs/brief-docqa-lite-2026-11-22/brief.md` | present |
| PRD | `prds/prd-docqa-lite-2026-11-22/prd.md` | final |
| Architecture spine | `architecture/architecture-docqa-lite-2026-11-22/ARCHITECTURE-SPINE.md` | final |
| Epics and stories | `epics.md` | **draft, `stepsCompleted: [1, 2]`, no stories** |
| UX | none | fine: API-only service, no UI stories |

## Findings (most severe first)

### 1. No stories exist — blocking
`epics.md` holds requirements, a coverage map and three epic summaries, followed by the raw template (`{{epic_title_N}}`, `{{story_title_N_M}}`). There are no story headings, acceptance criteria or Given/When/Then. Sprint tracking has nothing to track, and a developer would have to invent every story.
**Fix:** `bmad-create-epics-and-stories`, resuming from step 3.

### 2. Epic 3 has no direct FR coverage
Epic 3 ("Safe handling of bad input") covers only NFR2. That is acceptable for a brownfield baseline-locking plan, but its stories must be written as user-facing outcomes (for example, "a bad upload gets a clear reason"), not as "add tests".
**Fix:** resolve during story writing in `bmad-create-epics-and-stories`.

### 3. Two open decisions the stories depend on
- AD-10: whether `.markdown` samples load. FR1 says "every Markdown file"; the code may only accept `.md`.
- AD-10: whether an upload with no indexable terms is accepted. Today it returns 201 and can never be found.
**Fix:** decide both and record them in the acceptance criteria. Use `bmad-correct-course` only if a decision changes the PRD.

### 4. PRD open confirmations
- The NFR1 measurement method (median, warm index, opt-in `DOCQA_PERF=1`) is a default, not a decision.
- Primary user and problem are still `[ASSUMPTION]`.
Not blocking. Confirming them removes the provisional status from Epic 2's acceptance criteria.

### 5. Possible architecture/code mismatch on ordering
AD-7 ranks search on the rounded score, but the spine notes that today's code sorts on the raw score. That implies a code change the PRD does not mention, so it needs its own story or an explicit decision to leave it.
**Fix:** raise it during story writing.

### 6. Epic names differ between PRD and `epics.md`
PRD: "Protect the library API baseline", "Search that meets the performance bar", "Input validation and safety". `epics.md` renames all three. Scope matches; the difference is cosmetic.
**Fix:** align names when completing `epics.md`.

## What passes
- Every FR and NFR maps to an epic in the coverage map.
- Architecture decisions are recorded and the PRD and spine agree.
- No UX artifact is needed.

## Next step
Run `bmad-create-epics-and-stories`, then rerun readiness (`bmad-sprint-planning`).

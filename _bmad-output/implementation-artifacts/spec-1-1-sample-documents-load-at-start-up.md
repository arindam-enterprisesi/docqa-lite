---
title: '1-1 Sample documents load at start-up'
type: 'feature'
created: '2026-11-23'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `load_sample_dir` in `app/ingest.py` globs only `*.md`, so `.markdown` samples never load. It also skips only non-UTF-8 files, so empty and over-1,048,576-byte samples are admitted, which breaks the admission gate every document must pass (AD-10).

**Approach:** Test first, then make `load_sample_dir` load `*.md` and `*.markdown` (case-insensitive, sorted by filename). Route each sample's bytes through the same size, UTF-8 and non-empty checks as uploads, and skip a failing file with a warning logged by filename only. The app must still start and `GET /documents` must return 200.

</frozen-after-approval>

## Implementation Notes

- Code Map: `app/ingest.py` (`load_sample_dir`, `decode_upload`, `check_extension`), `app/main.py` (lifespan calls `load_sample_dir`; no change expected), `tests/test_ingest.py` (sample loader tests, fixtures `make_sample_dir` and `sample_dir`), `tests/test_app.py` (start-up tests, fixtures `client` and `make_client`).
- Reuse `decode_upload` for the gate. It already raises `UploadRejected` (413/422) and strips the BOM. Log `type(exc).__name__` or status only, never `exc.detail` content or file text.
- Tests to add (red first): `.markdown` sample loads; empty, whitespace-only, over-limit and non-UTF-8 samples are skipped, logged by filename only, and the app starts with `GET /documents` returning 200 (via `make_client`); the 5 shipped samples are all listed.
- Keep `.txt` and other extensions ignored (existing test `test_load_sample_dir_ignores_non_markdown_files`).
- Do not touch `Makefile`. The uncommitted `run:` target there reads `/bma`, which is outside this story.

## Review Triage Log

- low (patched): skip log omitted why a sample failed; now logs `status` and the fixed `reason` text, never content.
- low (rejected): no test for the `OSError` branch; branch unchanged, bounded read covered by the `too-large` case.
- low (rejected): `iterdir`/`is_file` outside the `try`; pre-existing (old `glob` behaved the same), rare.
- false: extension rules duplicated/case-insensitive; AC limits samples to `.md`/`.markdown`, `.txt` stays ignored, case-insensitivity is deliberate.
- low (rejected): BOM untested for samples; stripping is `decode_upload`'s job and is already tested.
- false/low (rejected): hardcoded sample filenames and no search-consistency test; AC says "all 5 present", existing tests already hardcode the titles.
- medium (deferred): CLAUDE.md and specs still say `*.md`; see `deferred-work.md`.

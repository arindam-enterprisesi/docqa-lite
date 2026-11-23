---
title: '1-2 Upload a Markdown or text document'
type: 'feature'
created: '2026-11-23'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `POST /documents` already meets Story 1.2, but two acceptance criteria have no test: a `.markdown` upload, and an upload with no indexable terms (for example only stop words), which returns 201 today yet is never findable. Neither behavior is locked.

**Approach:** Add tests, written first, that lock both behaviors in `tests/test_api_documents.py`. Change production code only if a test shows a real gap. The no-indexable-terms upload keeps returning 201, and the library and search for other documents stay intact.

</frozen-after-approval>

## Implementation Notes

- Code Map: `app/main.py` (`upload_document`), `app/ingest.py` (`sanitize_filename`, `check_extension`, `decode_upload`, `extract_title`), `app/search.py` (`SearchIndex.rebuild` sets the snapshot to `None` only when the whole library has an empty vocabulary), `tests/test_api_documents.py` (`upload` and `count` helpers, `client` fixture).
- Already covered, so not duplicated: 201 with id, title, filename, size and source, with `size` equal to the byte length (`test_upload_markdown_returns_201_with_metadata`); heading title; stem fallback (`test_upload_txt_without_heading_uses_stem`); base-name filename (`test_upload_path_traversal_name_is_reduced`).
- Same-epic context: Story 1-1 changed only the sample loader and the 1000-document cap landed separately; neither touches upload validation.
- Implementation: tests only (`tests/test_api_documents.py`); no production change was needed. A first draft asserted identical scores after adding a document, which failed because TF-IDF scores shift with corpus size (0.4358 to 0.4335). The test now compares ranking only.

## Review Triage Log

- medium (patched): the stop-word-only query assertion passed whether or not the document was indexed; removed it.
- low (patched): duplicated id-list comprehension; extracted `ranked_ids`.
- medium (patched): `SearchIndex.rebuild`'s empty-vocabulary branch was never reached; added a stop-word-only upload into an empty library (201, search 200 with `[]`).
- low (rejected): thin `.markdown` test; `.MARKDOWN`/`.MD` are covered by `test_allowed_extensions`, `.mdx`/bare `.markdown` by `test_rejected_extensions_are_415`.
- false: no empty/whitespace upload test; `test_upload_empty_is_422` and `test_whitespace_only_upload_is_422` exist.
- false/low (rejected): weak ranking assertion and hardcoded count; comparing id lists catches a changed result count, and neighbouring tests hardcode counts the same way.

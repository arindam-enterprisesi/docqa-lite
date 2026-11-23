- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-sample-documents-load-at-start-up.md`
  summary: Update CLAUDE.md and specs/001-document-library-search artifacts, which still say samples are `data/sample_docs/*.md`, to say `.md`/`.markdown` samples pass the upload admission gate and failing ones are skipped and logged.
  evidence: `load_sample_dir` now loads `.markdown`, applies the size/UTF-8/non-empty gate, and skips failures; the docs describe the old `*.md`-only behavior. Deferred because the fix edits CLAUDE.md and specs.

<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Bump rationale: initial ratification; all placeholders replaced with concrete principles.

Modified principles (template slot → new title):
  - [PRINCIPLE_1_NAME] → I. Fixed Technology Stack
  - [PRINCIPLE_2_NAME] → II. Test-First (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] → III. Keep It Simple
  - [PRINCIPLE_4_NAME] → IV. Secure by Default
  - [PRINCIPLE_5_NAME] → V. Justified Dependencies

Added sections:
  - Technical Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
  - Governance (filled)

Removed sections: none

Templates reviewed (read at runtime, not modified by this command):
  - .specify/templates/plan-template.md — "Constitution Check" gate reads this file ✅
  - .specify/templates/spec-template.md — no change required ✅
  - .specify/templates/tasks-template.md — ⚠ says tests are "OPTIONAL"; Principle II makes them
    mandatory, so /speckit-tasks MUST always generate test tasks (constitution takes precedence)

Deferred TODOs: none
-->

# DocQA-lite Constitution

## Core Principles

### I. Fixed Technology Stack

- Application code MUST target Python 3.11 (`requires-python >= 3.11`, ruff `target-version = py311`).
- The HTTP layer MUST be FastAPI; request and response models MUST be pydantic v2 models
  (`BaseModel`, `model_validate`, `ConfigDict` — no pydantic v1 compatibility APIs).
- Code MUST pass `make lint` (ruff rules `E F I B UP`, line length 100, formatted with ruff).

Rationale: a single, small, well-known stack keeps the training codebase readable and lets every
participant and AI agent reason about it the same way.

### II. Test-First (NON-NEGOTIABLE)

- Every feature and every bug fix MUST be accompanied by pytest tests under `tests/`.
- Tests MUST be written before the implementation and observed to fail before the code that makes
  them pass is written (Red → Green → Refactor).
- API behaviour MUST be tested in-process with `fastapi.testclient.TestClient(app)`; tests MUST NOT
  require a running server, network access, or an API key.
- Tests MUST be deterministic: no reliance on wall-clock time, randomness, or test ordering without
  explicit control (e.g., fixed seeds, isolated per-test state).
- `make test` MUST pass before any change is merged.

Rationale: tests are the executable form of the spec; deterministic, fast tests make AI-driven
implementation verifiable.

### III. Keep It Simple

- The service MUST NOT depend on a database server; persistence, if needed, MUST use in-process
  memory or the local filesystem (or an embedded store such as SQLite if justified in the plan).
- The service MUST NOT make calls to external APIs or network services at runtime or in tests
  (this includes LLM APIs; search uses TF-IDF via scikit-learn).
- Features MUST be delivered within the existing single FastAPI application; no new service,
  worker, queue, or container MAY be introduced.
- Prefer the simplest design that satisfies the spec (YAGNI); added abstractions MUST be justified
  in the plan's Complexity Tracking section.

Rationale: the project is deliberately tiny; every moving part added costs setup time and
non-determinism.

### IV. Secure by Default

- All external inputs (path/query parameters, JSON bodies, uploaded files and their metadata)
  MUST be validated via pydantic models or explicit checks: type, length/size limits, allowed
  content types, and non-empty constraints. Invalid input MUST yield a 4xx response, never a 500.
- Uploaded filenames and identifiers MUST NOT be used to build filesystem paths without
  sanitisation (no path traversal).
- Logs, error messages, and exception traces MUST NOT contain document contents, secrets,
  credentials, or the contents of `.env` files. Log identifiers and sizes, not bodies.
- Secrets MUST NOT be committed to the repository.

Rationale: a document service handles potentially sensitive text; leaking it through logs or
accepting malformed input are the most likely failure modes.

### V. Justified Dependencies

- No new runtime or dev dependency MAY be added to `pyproject.toml` unless the feature's `plan.md`
  names it and justifies why existing dependencies (FastAPI, pydantic, scikit-learn,
  python-multipart, the standard library) are insufficient.
- The justification MUST state the alternative considered and the reason it was rejected.

Rationale: every dependency adds supply-chain risk, install time, and maintenance; the declared
set already covers the planned document library and search features.

## Technical Constraints

- Runtime: Python 3.11+, FastAPI, pydantic v2, uvicorn; search via scikit-learn TF-IDF.
- Uploads: `python-multipart`; upload size limits MUST be defined in the spec or plan.
- Environment: commands run inside WSL using `uv` via the Makefile
  (`make install`, `make test`, `make lint`, `make run`).
- Version: `app/__init__.py::__version__` is the single source of truth for the API version.
- Test corpus: `data/sample_docs/` is the canonical fixture set for search behaviour.

## Development Workflow & Quality Gates

- Features follow the Spec Kit flow: constitution → specify → clarify → plan → tasks → analyze →
  implement.
- Every `plan.md` MUST include a Constitution Check confirming compliance with Principles I–V;
  any deviation MUST be recorded in Complexity Tracking with justification.
- In `tasks.md`, test tasks MUST precede the implementation tasks they cover.
- Before opening a PR: `make test` and `make lint` MUST pass; an AI review of the diff MUST be
  performed and its findings addressed or explicitly declined with reason.
- Pushing to the remote is performed by a human, not by the AI agent.

## Governance

- This constitution supersedes other project practices; where `CLAUDE.md` or other guidance
  conflicts with it, the constitution wins until amended.
- Amendments are made via `/speckit-constitution`, MUST include a Sync Impact Report, and MUST be
  reviewed by a human before commit.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle, MINOR for
  adding a principle/section or materially expanding guidance, PATCH for clarifications.
- Compliance is checked at plan time (Constitution Check), at `/speckit-analyze`, and during PR
  review; reviewers MUST reject changes that violate a principle without recorded justification.

**Version**: 1.0.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21

<!--
Sync Impact Report
==================
Version change: (unratified template) → 1.0.0
Modified principles (placeholder → named):
  - [PRINCIPLE_1_NAME] → I. Fixed Technology Stack
  - [PRINCIPLE_2_NAME] → II. Test-First (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] → III. Simplicity: In-Process Only
  - [PRINCIPLE_4_NAME] → IV. Secure by Default
  - [PRINCIPLE_5_NAME] → V. Justified Dependencies
Added sections:
  - Technical Constraints (was [SECTION_2_NAME])
  - Development Workflow & Quality Gates (was [SECTION_3_NAME])
  - Governance (filled)
Removed sections: none
Templates: not modified (read at runtime by dependent commands, per command scope guard)
Follow-up TODOs: none
NOTE: This report is scratch material for review; remove it before committing.
-->

# DocQA-lite Constitution

## Core Principles

### I. Fixed Technology Stack

- All application code MUST target Python 3.11 (`requires-python >= 3.11`, ruff `target-version
  = py311`).
- The HTTP layer MUST be FastAPI, using the single `app` instance defined in `app/main.py`.
- Request and response models MUST be pydantic v2 models (`BaseModel`, `Field`,
  `model_validator`/`field_validator`); pydantic v1 APIs and compatibility shims are prohibited.
- New application code MUST live under the `app` package, the only package setuptools installs.

**Rationale**: A single, fixed stack keeps the training starter small and lets every participant
reason about the same code paths.

### II. Test-First (NON-NEGOTIABLE)

- Every feature MUST ship with pytest tests, and every new function MUST have a unit test.
- Tests MUST be written before the implementation and MUST be observed failing before the code
  that makes them pass is written (Red → Green → Refactor).
- Endpoint tests MUST use `fastapi.testclient.TestClient(app)` in-process and MUST NOT depend on
  the network, wall-clock timing, or randomness without a fixed seed.
- `make test` MUST pass and `make lint` (ruff check + format check) MUST pass before any task is
  marked complete or any PR is opened.

**Rationale**: The session's goal is spec-driven, tests-first delivery; deterministic in-process
tests keep feedback fast and reviews trustworthy.

### III. Simplicity: In-Process Only

- No database server (PostgreSQL, MySQL, Redis, Elasticsearch, etc.). Storage MUST be in-process
  (memory) or local files.
- No external API calls at runtime or in tests, including LLM or hosted embedding services.
  Search MUST use TF-IDF via scikit-learn.
- No new service, container, worker, or process: the deliverable is one FastAPI app run by
  `make run`.
- Additional abstraction layers (repositories, plugin systems, DI frameworks) MUST be justified in
  the plan's Complexity Tracking; default is the simplest working design (YAGNI).

**Rationale**: The project is a deliberately tiny starter; every moving part added is one more
thing that can make tests slow, flaky, or require secrets.

### IV. Secure by Default

- All external input (path/query params, JSON bodies, uploaded files and their names) MUST be
  validated at the boundary via pydantic models or explicit checks: types, required fields,
  length/size limits, allowed content types, and empty/blank values.
- Invalid input MUST be rejected with a 4xx response and a non-leaking error message; it MUST NOT
  cause a 5xx.
- Document contents, search queries' matched text, and secrets MUST NEVER be written to logs.
  Logs MAY include identifiers, counts, sizes, and status codes.
- No secrets or environment-variable configuration is required; `.env` files MUST NOT be read or
  edited by tooling or agents.
- Uploaded filenames MUST NOT be used to construct filesystem paths without sanitisation
  (no path traversal).

**Rationale**: Document libraries handle potentially sensitive text; boundary validation and
content-free logging prevent the most common leaks.

### V. Justified Dependencies

- No new runtime or dev dependency MAY be added unless the feature's `plan.md` names it, states
  why existing dependencies (FastAPI, pydantic, scikit-learn, python-multipart, stdlib) are
  insufficient, and the addition is explicitly approved by the user before installation.
- Dependencies MUST be declared in `pyproject.toml`; ad-hoc installs are prohibited.

**Rationale**: Every dependency is a supply-chain, licensing, and maintenance cost; the existing
set already covers uploads and search.

## Technical Constraints

- Runtime: Python 3.11, FastAPI, pydantic v2, uvicorn; search via scikit-learn TF-IDF.
- Tooling: `uv` via the Makefile (`make install`, `make test`, `make lint`, `make format`,
  `make run`).
- Style: ruff, line length 100, lint rules `E, F, I, B, UP`; formatting enforced by
  `ruff format --check`.
- Version: `app/__init__.py` `__version__` is the single source of the version reported by the
  API.
- Test corpus: `data/sample_docs/` (five Markdown policy documents) is the canonical fixture set
  for search features.

## Development Workflow & Quality Gates

- Features follow the Spec Kit flow: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`.
- Each plan MUST include a Constitution Check that evaluates Principles I–V; any violation MUST be
  recorded with justification in Complexity Tracking or the plan MUST be revised.
- Tests for a feature go in `tests/test_<feature>.py`.
- Before a PR: `make test` and `make lint` pass, a review (subagent or human) confirms compliance
  with this constitution, and the PR description lists any added dependency with its justification.

## Governance

- This constitution supersedes other practices for DocQA-lite. Where `CLAUDE.md` and this document
  conflict, the stricter rule applies until the conflict is resolved by amendment.
- Amendments are made via `/speckit-constitution`, MUST include a Sync Impact Report reviewed by a
  human, and MUST state the version bump rationale.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle, MINOR for
  adding a principle/section or materially expanding guidance, PATCH for clarifications and
  wording.
- Compliance is verified at three points: the plan's Constitution Check, `/speckit-analyze`, and
  PR review. Non-compliant work MUST NOT be merged.

**Version**: 1.0.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21

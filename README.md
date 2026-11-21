# DocQA-lite (training starter)

A deliberately tiny FastAPI service used in the **AI-Autonomous SDLC** hands-on session.
During the session you will use **Claude Code** in the terminal and **GitHub Spec Kit** to
specify, plan and build a *document library with search* on top of this starter.

No LLM API key is needed: search will use TF-IDF (scikit-learn), so tests are fast and deterministic.

## Prerequisites

- Git, Python 3.11+
- [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash`
- Spec Kit CLI: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

## Quick start

```bash
make install   # create .venv and install dependencies
make test      # 1 test should pass
make run       # http://localhost:8000
```

## Layout

```text
app/                 FastAPI application (app/main.py)
tests/               pytest tests
data/sample_docs/    five short policy documents to search over
Makefile             install | test | lint | format | run
```

## What you will build in the session

1. `/speckit.constitution` - project principles
2. `/speckit.specify` - a document library with search (upload, list, get, search)
3. `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`
4. `/speckit.implement` - tests first, then code
5. AI review with a subagent, then a pull request

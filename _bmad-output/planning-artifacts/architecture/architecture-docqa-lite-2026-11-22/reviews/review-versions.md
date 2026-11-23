# Review: versions and reality-check lens

Target: ARCHITECTURE-SPINE.md. Reviewer: read-only. Date: 2026-11-22.

## Verdict
PASS with minor notes. Every Stack-table version matches the project .venv exactly. The library-behaviour claims hold and match the code. The remaining gap is that "not web-checked" is stated and web checks were inconclusive; no stale technology was found.

## Version table vs `uv pip list` (Python 3.12.3 venv)
| Package | Spine | venv | Match |
| --- | --- | --- | --- |
| FastAPI | 0.165.0 | 0.165.0 | yes |
| Starlette | 1.10.0 | 1.10.0 | yes |
| pydantic | 2.14.4 | 2.14.4 | yes |
| scikit-learn | 1.9.1 | 1.9.1 | yes |
| scipy | 1.18.1 | 1.18.1 | yes |
| numpy | 2.5.5 | 2.5.5 | yes |
| python-multipart | 0.0.34 | 0.0.34 | yes |
| uvicorn | 0.54.0 | 0.54.0 | yes |
| pytest | 9.2.0 | 9.2.0 | yes |
| ruff | 0.17.6 | 0.17.6 | yes |
| Python floor | 3.11 | requires-python >=3.11; constitution line 36 | yes |

Not in the table but relevant: httpx 0.28.1 (TestClient dependency, a dev extra) and anyio 4.16.0.

## Findings

1. [medium] The Stack table lists installed versions, not constraints. pyproject.toml declares only loose floors (fastapi>=0.110, scikit-learn>=1.4, python-multipart>=0.0.9, pytest>=8, ruff>=0.5) and there is no lockfile. A fresh `make install` can resolve different versions, so the table is a snapshot, not a pin. Suggest rewording the header to "versions installed at 2026-11-22; floors in pyproject.toml" and listing the floors. The 3.11 floor is the only real constraint, and the spine already says so.
2. [medium] The web check was inconclusive. A web search gave FastAPI "0.162.7" (Nov 13 2026, from a third-party mirror). The venv has 0.165.0, which is newer, so that source is stale or unreliable. It does not show 0.165.0 is wrong, but 0.165.0 is unconfirmed against PyPI. Starlette 1.0.0 was released 2026-03-22 and removed APIs deprecated before 1.0, so 1.10.0 is a post-1.0 line. No TestClient/httpx breakage is indicated; the harmless httpx warning noted in CLAUDE.md is consistent with this. scikit-learn 1.9.0 was published 2026-06-02 and supports Python 3.11 to 3.14. No TfidfVectorizer deprecation was found (single search, not exhaustive). 1.9 adds narwhals as a dependency and an experimental callbacks API, neither of which affects this design. python-multipart 0.0.34 was not specifically checked. Low risk, but the spine's "not web-checked" caveat is honest and should stay.
3. [low] AD-4 relies on `self._snapshot = _Snapshot(...)` being an atomic single assignment, which holds under the CPython GIL. It is not guaranteed on free-threaded (no-GIL) 3.13t/3.14t builds, which scikit-learn 1.9 now supports. Plain attribute assignment of a reference is still atomic in practice there, so this is only a note. The spine could say "single reference assignment" rather than leaning on the GIL.
4. [low] The spine does not name the threadpool dependency. Its lock choice is correct (see below) but only implicit. Add a one-line rationale to AD-3 or AD-4.

## Library-behaviour claims
- Sync `def` endpoints run in a threadpool: CONFIRMED. FastAPI runs non-async path functions via anyio's `run_in_threadpool`. In app/main.py, `root`, `health`, `upload_document`, `list_documents`, `get_document` and `search` are all plain `def`; only the lifespan is async. Concurrent requests therefore run in separate threads, so `threading.Lock` is the correct primitive. An `asyncio.Lock` would be wrong here. The lock is created in the lifespan (main.py:42) and used only in upload (main.py:77), as AD-1 and AD-3 state. One caveat: if anyone makes an endpoint `async def`, the blocking `with state.lock` would stall the event loop. Worth one sentence in AD-3.
- TfidfVectorizer IDF is corpus-global: CONFIRMED. `fit_transform` learns one `idf_` vector from the whole training corpus, so adding a document changes every document's weights. This supports AD-4's "full rebuild, no incremental" rule. search.py:41 builds `TfidfVectorizer(stop_words="english", sublinear_tf=True, lowercase=True)` per rebuild and swaps `_Snapshot` in one assignment (search.py:47), as the spine says. The `_TOKEN_RE` in search.py copies the vectorizer's default token_pattern. If sklearn changed that default, the snippet and highlight logic could drift. The default has been stable for years; this is a low risk worth a comment.
- python-multipart: the spine says only that uploads are read with a bounded `MAX_BYTES + 1` read. It makes no claim about multipart library internals, so there is nothing to verify. Note that Starlette spools large uploads to disk (SpooledTemporaryFile) before the route's bounded read, so the 413 check bounds memory in the route, not the transport. This is not claimed in the spine.

## Technologies named: still exist and fit
FastAPI, Starlette, pydantic v2, scikit-learn, uvicorn, pytest, ruff, uv and Make are all current and actively released. Nothing deprecated or abandoned. The spine adds no new dependency; it ratifies the existing code.

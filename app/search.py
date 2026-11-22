"""TF-IDF search over the library (research R1, R2, R7, R8)."""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from app.models import SearchHit
from app.repository import Document

SNIPPET_MAX_CHARS = 200
SCORE_DECIMALS = 4

_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")  # TfidfVectorizer's default token pattern
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class _Snapshot:
    vectorizer: TfidfVectorizer
    matrix: spmatrix
    docs: tuple[Document, ...]


class SearchIndex:
    """Holds one immutable index snapshot; ``rebuild`` swaps it in a single assignment."""

    def __init__(self) -> None:
        self._snapshot: _Snapshot | None = None

    def rebuild(self, documents: Sequence[Document]) -> None:
        docs = tuple(documents)
        if not docs:
            self._snapshot = None
            return
        vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True, lowercase=True)
        try:
            matrix = vectorizer.fit_transform([d.content for d in docs])
        except ValueError:  # empty vocabulary: every token is a stop word
            self._snapshot = None
            return
        self._snapshot = _Snapshot(vectorizer=vectorizer, matrix=matrix, docs=docs)

    def search(self, query: str, k: int) -> list[SearchHit]:
        snapshot = self._snapshot
        if snapshot is None:
            return []
        analyzer: Callable[[str], list[str]] = snapshot.vectorizer.build_analyzer()
        terms = analyzer(query)
        if not terms:
            return []
        scores = linear_kernel(snapshot.vectorizer.transform([query]), snapshot.matrix).ravel()
        order = np.argsort(-scores, kind="stable")  # ties keep insertion order
        hits: list[SearchHit] = []
        for i in order:
            score = min(round(float(scores[i]), SCORE_DECIMALS), 1.0)
            if score <= 0:  # filter after rounding so a tiny score is never reported as 0
                break
            doc = snapshot.docs[i]
            hits.append(
                SearchHit(
                    id=doc.id,
                    title=doc.title,
                    score=score,
                    snippet=make_snippet(doc.content, terms),
                )
            )
            if len(hits) == k:
                break
        return hits


def _segments(content: str) -> tuple[list[str], list[str]]:
    """Split content into (body sentences, heading texts), Markdown markers removed."""
    body: list[str] = []
    headings: list[str] = []
    for block in re.split(r"\n\s*\n", content):
        text_lines: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    headings.append(heading)
            elif stripped:
                text_lines.append(stripped)
        if text_lines:
            body.extend(s for s in _SENTENCE_SPLIT_RE.split(" ".join(text_lines)) if s)
    return body, headings


def _truncate(text: str) -> str:
    text = _WS_RE.sub(" ", text).strip()
    if len(text) <= SNIPPET_MAX_CHARS:
        return text
    cut = text[: SNIPPET_MAX_CHARS - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip() + "…"


def make_snippet(content: str, query_terms: Sequence[str]) -> str:
    """First passage containing a query term (whole word, case-insensitive), ≤ 200 chars."""
    body, headings = _segments(content)
    wanted = {t.lower() for t in query_terms}
    for segment in body:
        if wanted & {t.lower() for t in _TOKEN_RE.findall(segment)}:
            return _truncate(segment)
    if body:
        return _truncate(body[0])
    if headings:
        return _truncate(headings[0])
    return ""

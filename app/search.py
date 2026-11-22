"""TF-IDF search over the library (research.md R2, R3, R6)."""

import re
import threading
from collections.abc import Callable, Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import SNIPPET_CHARS
from app.models import Document, SearchResult

_ELLIPSIS = "…"


class SearchIndex:
    """TF-IDF index rebuilt from the full document list; safe to share across threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._documents: list[Document] = []

    def rebuild(self, documents: Iterable[Document]) -> None:
        """Refit the index on exactly these documents, replacing any previous corpus."""
        docs = list(documents)
        vectorizer: TfidfVectorizer | None = TfidfVectorizer(
            stop_words="english", sublinear_tf=True
        )
        matrix = None
        if docs:
            try:
                matrix = vectorizer.fit_transform([f"{d.title}\n{d.content}" for d in docs])
            except ValueError:  # empty vocabulary, e.g. only stop words
                matrix = None
        if matrix is None:
            vectorizer, docs = None, []
        with self._lock:
            self._vectorizer, self._matrix, self._documents = vectorizer, matrix, docs

    def search(self, query: str, k: int) -> list[SearchResult]:
        """Return up to k matches with score > 0, by score desc then id asc."""
        with self._lock:
            vectorizer, matrix, docs = self._vectorizer, self._matrix, self._documents
        if vectorizer is None or not docs:
            return []
        query_vector = vectorizer.transform([query])
        if query_vector.nnz == 0:
            return []
        scores = cosine_similarity(query_vector, matrix).ravel()
        ranked = sorted(
            ((round(float(s), 4), d) for s, d in zip(scores, docs, strict=True)),
            key=lambda pair: (-pair[0], pair[1].id),
        )
        analyzer = vectorizer.build_analyzer()
        return [
            SearchResult(
                id=doc.id,
                title=doc.title,
                score=score,
                snippet=self._snippet(doc.content, query, analyzer),
            )
            for score, doc in ranked[:k]
            if score > 0
        ]

    def snippet(self, content: str, query: str) -> str:
        """Return <= SNIPPET_CHARS of content centred on the first query-term match."""
        with self._lock:
            vectorizer = self._vectorizer
        analyzer = vectorizer.build_analyzer() if vectorizer is not None else None
        return self._snippet(content, query, analyzer)

    @staticmethod
    def _snippet(content: str, query: str, analyzer: Callable[[str], list[str]] | None) -> str:
        text = " ".join(content.split())
        if len(text) <= SNIPPET_CHARS:
            return text
        tokens = analyzer(query) if analyzer is not None else re.findall(r"\w+", query.lower())
        centre = 0
        first = None
        for token in set(tokens):
            match = re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE)
            if match and (first is None or match.start() < first.start()):
                first = match
        if first is not None:
            centre = (first.start() + first.end()) // 2
        start = min(max(0, centre - SNIPPET_CHARS // 2), len(text) - SNIPPET_CHARS)
        end = start + SNIPPET_CHARS
        if start > 0:
            start += 1  # room for the leading ellipsis
        if end < len(text):
            end -= 1  # room for the trailing ellipsis
        prefix = _ELLIPSIS if start > 0 else ""
        suffix = _ELLIPSIS if end < len(text) else ""
        return f"{prefix}{text[start:end]}{suffix}"

"""In-memory document storage (research.md R1)."""

import threading

from app.config import MAX_DOCUMENTS
from app.models import Document


class LibraryFullError(Exception):
    """Raised when adding a document would exceed the library cap."""


class InMemoryDocumentRepository:
    """Thread-safe, insertion-ordered document store held in process memory."""

    def __init__(self, max_documents: int = MAX_DOCUMENTS) -> None:
        self._max_documents = max_documents
        self._documents: dict[str, Document] = {}
        self._lock = threading.Lock()

    def add(self, document: Document) -> None:
        """Store a document; raise LibraryFullError if the cap is reached."""
        with self._lock:
            if len(self._documents) >= self._max_documents:
                raise LibraryFullError(f"Library full: maximum {self._max_documents} documents")
            self._documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        """Return the document with this id, or None."""
        with self._lock:
            return self._documents.get(document_id)

    def list(self) -> list[Document]:
        """Return all documents in insertion order."""
        with self._lock:
            return list(self._documents.values())

    def count(self) -> int:
        """Return the number of stored documents."""
        with self._lock:
            return len(self._documents)

    def clear(self) -> None:
        """Remove every document."""
        with self._lock:
            self._documents.clear()

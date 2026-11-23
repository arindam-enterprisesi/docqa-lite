"""Document record and storage. Storage sits behind a Protocol so it can be swapped later."""

from dataclasses import dataclass
from typing import Literal, Protocol

Source = Literal["sample", "upload"]


@dataclass(frozen=True, slots=True)
class Document:
    """An immutable text document in the library (see data-model.md, Document)."""

    id: str
    title: str
    filename: str
    size: int
    content: str
    source: Source


class DocumentRepository(Protocol):
    def add(self, doc: Document) -> None: ...

    def get(self, doc_id: str) -> Document | None: ...

    def list(self) -> list[Document]: ...


class InMemoryDocumentRepository:
    """Process-local storage; documents are kept in insertion order."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    def add(self, doc: Document) -> None:
        self._docs[doc.id] = doc

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def list(self) -> list[Document]:
        return list(self._docs.values())

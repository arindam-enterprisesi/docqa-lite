import pytest

from app.config import MAX_DOCUMENTS
from app.models import Document
from app.repository import InMemoryDocumentRepository, LibraryFullError


def make_document(doc_id: str) -> Document:
    return Document(
        id=doc_id,
        title=f"Title {doc_id}",
        filename=f"{doc_id}.md",
        size_bytes=4,
        content="text",
        source="upload",
    )


def test_add_then_get_returns_same_document():
    repo = InMemoryDocumentRepository()
    doc = make_document("a")
    repo.add(doc)
    assert repo.get("a") == doc


def test_get_unknown_id_returns_none():
    assert InMemoryDocumentRepository().get("missing") is None


def test_list_preserves_insertion_order():
    repo = InMemoryDocumentRepository()
    for doc_id in ["c", "a", "b"]:
        repo.add(make_document(doc_id))
    assert [d.id for d in repo.list()] == ["c", "a", "b"]


def test_count_tracks_added_documents():
    repo = InMemoryDocumentRepository()
    assert repo.count() == 0
    repo.add(make_document("a"))
    repo.add(make_document("b"))
    assert repo.count() == 2


def test_clear_empties_repository():
    repo = InMemoryDocumentRepository()
    repo.add(make_document("a"))
    repo.clear()
    assert repo.count() == 0
    assert repo.list() == []


def test_add_raises_library_full_at_cap_and_keeps_count():
    repo = InMemoryDocumentRepository(max_documents=3)
    for doc_id in ["a", "b", "c"]:
        repo.add(make_document(doc_id))
    with pytest.raises(LibraryFullError):
        repo.add(make_document("d"))
    assert repo.count() == 3
    assert repo.get("d") is None


def test_default_cap_is_max_documents():
    repo = InMemoryDocumentRepository()
    for i in range(MAX_DOCUMENTS):
        repo.add(make_document(f"id{i}"))
    with pytest.raises(LibraryFullError):
        repo.add(make_document("overflow"))

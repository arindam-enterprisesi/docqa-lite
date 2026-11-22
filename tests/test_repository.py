import dataclasses

import pytest

from app.repository import Document, InMemoryDocumentRepository


def make_doc(doc_id: str, filename: str = "a.md") -> Document:
    return Document(
        id=doc_id,
        title=f"Title {doc_id}",
        filename=filename,
        size=5,
        content="hello",
        source="upload",
    )


def test_add_then_get_returns_same_document():
    repo = InMemoryDocumentRepository()
    doc = make_doc("one")
    repo.add(doc)
    assert repo.get("one") == doc


def test_get_unknown_id_returns_none():
    repo = InMemoryDocumentRepository()
    assert repo.get("missing") is None


def test_list_returns_documents_in_insertion_order():
    repo = InMemoryDocumentRepository()
    for doc_id in ["c", "a", "b"]:
        repo.add(make_doc(doc_id))
    assert [d.id for d in repo.list()] == ["c", "a", "b"]


def test_list_returns_a_copy():
    repo = InMemoryDocumentRepository()
    repo.add(make_doc("one"))
    repo.list().clear()
    assert len(repo.list()) == 1


def test_document_is_immutable():
    doc = make_doc("one")
    with pytest.raises(dataclasses.FrozenInstanceError):
        doc.title = "changed"  # type: ignore[misc]

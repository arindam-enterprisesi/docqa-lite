import pytest
from pydantic import ValidationError

from app.models import Document


def make_document(**overrides) -> Document:
    fields = {
        "id": "a" * 32,
        "title": "Title",
        "filename": "file.md",
        "size_bytes": 10,
        "content": "Some text.",
        "source": "upload",
    }
    fields.update(overrides)
    return Document(**fields)


def test_document_valid_construction():
    doc = make_document()
    assert doc.title == "Title"
    assert doc.source == "upload"
    assert doc.size_bytes == 10


@pytest.mark.parametrize("source", ["sample", "upload"])
def test_document_accepts_known_sources(source):
    assert make_document(source=source).source == source


def test_document_rejects_unknown_source():
    with pytest.raises(ValidationError):
        make_document(source="web")


def test_document_is_frozen():
    doc = make_document()
    with pytest.raises(ValidationError):
        doc.title = "Changed"

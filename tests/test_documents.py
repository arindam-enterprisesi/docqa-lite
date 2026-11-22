import logging

import pytest

from app.config import MAX_DOCUMENTS, MAX_UPLOAD_BYTES, SAMPLE_DOCS_DIR


def upload(client, filename, data: bytes, content_type="text/markdown"):
    return client.post("/documents", files={"file": (filename, data, content_type)})


# --- US2: upload (T026) -------------------------------------------------------


def test_upload_returns_201_with_summary(client):
    response = upload(client, "remote.md", b"# Remote Work\n\nStaff may work remotely.")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "filename", "size_bytes"}
    assert body["title"] == "Remote Work"
    assert body["filename"] == "remote.md"
    assert body["size_bytes"] == len(b"# Remote Work\n\nStaff may work remotely.")


def test_title_falls_back_to_filename_stem(client):
    response = upload(client, "plain-notes.txt", b"No heading here.", "text/plain")
    assert response.json()["title"] == "plain-notes"


def test_uploaded_document_is_searchable_immediately(client):
    upload(client, "unique.txt", b"The zephyrquokka protocol applies.", "text/plain")
    results = client.get("/search", params={"q": "zephyrquokka"}).json()["results"]
    assert [r["title"] for r in results] == ["unique"]


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("NOTES.MD", "text/markdown"),
        ("notes.md", "application/octet-stream"),
        ("notes.markdown", "text/markdown"),
    ],
)
def test_accepted_by_extension_regardless_of_declared_type(client, filename, content_type):
    assert upload(client, filename, b"hello", content_type).status_code == 201


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("report.pdf", "text/plain"),
        ("noextension", "text/plain"),
        ("a.md/", "text/markdown"),
        ("/", "text/markdown"),
    ],
)
def test_unsupported_type_rejected_with_415(client, filename, content_type):
    response = upload(client, filename, b"hello", content_type)
    assert response.status_code == 415
    assert response.json() == {"detail": "Unsupported file type: allowed .md, .markdown, .txt"}


def test_exactly_max_size_accepted(client):
    assert upload(client, "max.txt", b"a" * MAX_UPLOAD_BYTES, "text/plain").status_code == 201


def test_over_max_size_rejected_with_413(client):
    response = upload(client, "big.txt", b"a" * (MAX_UPLOAD_BYTES + 1), "text/plain")
    assert response.status_code == 413
    assert response.json() == {"detail": f"File too large: maximum {MAX_UPLOAD_BYTES} bytes"}


def test_extension_checked_before_size(client):
    response = upload(client, "huge.pdf", b"a" * (2 * MAX_UPLOAD_BYTES), "application/pdf")
    assert response.status_code == 415


def test_empty_file_rejected(client):
    response = upload(client, "empty.md", b"")
    assert response.status_code == 422
    assert response.json() == {"detail": "File is empty"}


def test_invalid_utf8_rejected(client):
    response = upload(client, "bad.md", b"\xff\xfe")
    assert response.status_code == 422
    assert response.json() == {"detail": "File is not valid UTF-8 text"}


def test_missing_file_field_rejected(client):
    assert client.post("/documents").status_code == 422


def test_rejected_upload_is_not_stored(client):
    upload(client, "report.pdf", b"hello", "text/plain")
    upload(client, "empty.md", b"")
    assert client.get("/documents").json()["count"] == 5


def test_path_traversal_filename_reduced_to_basename(client):
    response = upload(client, "../../x.md", b"# Traversal\ntext")
    assert response.status_code == 201
    assert response.json()["filename"] == "x.md"


def test_duplicate_uploads_get_distinct_ids(client):
    first = upload(client, "dup.md", b"same content").json()["id"]
    second = upload(client, "dup.md", b"same content").json()["id"]
    assert first != second


def test_library_full_rejected_with_409(client):
    for i in range(MAX_DOCUMENTS - 5):
        assert upload(client, f"doc{i}.txt", f"doc {i}".encode(), "text/plain").status_code == 201
    response = upload(client, "overflow.txt", b"one too many", "text/plain")
    assert response.status_code == 409
    assert response.json() == {"detail": f"Library full: maximum {MAX_DOCUMENTS} documents"}
    assert client.get("/documents").json()["count"] == MAX_DOCUMENTS


def test_uploaded_content_not_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    upload(client, "private.md", b"# Private\n\nconfidential-salary-figures")
    assert "confidential-salary-figures" not in caplog.text


# --- US3: list and get (T031) -------------------------------------------------


def test_list_returns_five_samples_sorted_without_content(client):
    response = client.get("/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    filenames = [d["filename"] for d in body["documents"]]
    assert filenames == sorted(p.name for p in SAMPLE_DOCS_DIR.glob("*.md"))
    for item in body["documents"]:
        assert set(item) == {"id", "title", "filename", "size_bytes"}


def test_get_each_document_returns_full_content(client):
    for item in client.get("/documents").json()["documents"]:
        response = client.get(f"/documents/{item['id']}")
        assert response.status_code == 200
        detail = response.json()
        assert set(detail) == {"id", "title", "filename", "size_bytes", "content"}
        expected = (SAMPLE_DOCS_DIR / item["filename"]).read_text(encoding="utf-8")
        assert detail["content"] == expected


def test_get_unknown_id_returns_404(client):
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_uploaded_document_listed_last(client):
    upload(client, "zz-new.md", b"# Newest\ntext")
    documents = client.get("/documents").json()["documents"]
    assert len(documents) == 6
    assert documents[-1]["title"] == "Newest"

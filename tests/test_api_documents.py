import logging

from app.ingest import MAX_BYTES
from tests.helpers import server_log_text


def upload(client, name: str, data: bytes):
    return client.post("/documents", files={"file": (name, data, "text/markdown")})


def count(client) -> int:
    return len(client.app.state.repository.list())


# --- upload (T017, US2) ---------------------------------------------------------------------


def test_upload_markdown_returns_201_with_metadata(client):
    data = b"# Quokka Care\nFeed the quokka daily.\n"
    response = upload(client, "q.md", data)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "filename", "size", "source"}
    assert body["title"] == "Quokka Care"
    assert body["filename"] == "q.md"
    assert body["size"] == len(data)
    assert body["source"] == "upload"
    assert count(client) == 6


def test_upload_txt_without_heading_uses_stem(client):
    assert upload(client, "plain-notes.txt", b"hello world").json()["title"] == "plain-notes"


def test_duplicate_upload_gets_new_id(client):
    first = upload(client, "a.md", b"same").json()["id"]
    second = upload(client, "a.md", b"same").json()["id"]
    assert first != second
    assert count(client) == 7


def test_uploaded_document_is_searchable_immediately(client):
    doc_id = upload(client, "q.md", b"# Quokka Care\nFeed the quokka daily.").json()["id"]
    results = client.get("/search", params={"q": "quokka"}).json()["results"]
    assert results[0]["id"] == doc_id


def test_upload_exactly_one_megabyte_is_accepted(client):
    assert upload(client, "big.txt", b"a" * MAX_BYTES).status_code == 201


def test_upload_too_large_is_413_and_library_unchanged(client):
    response = upload(client, "big.txt", b"a" * (MAX_BYTES + 1))
    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]
    assert count(client) == 5


def test_upload_pdf_is_415(client):
    response = upload(client, "report.pdf", b"%PDF-1.4")
    assert response.status_code == 415
    assert ".md" in response.json()["detail"]
    assert count(client) == 5


def test_upload_empty_is_422(client):
    assert upload(client, "e.md", b"").status_code == 422
    assert count(client) == 5


def test_upload_invalid_utf8_is_422(client):
    assert upload(client, "b.txt", b"\xff\xfe\xfa").status_code == 422
    assert count(client) == 5


def test_upload_without_file_field_is_422(client):
    assert client.post("/documents").status_code == 422
    assert count(client) == 5


def test_upload_path_traversal_name_is_reduced(client):
    assert upload(client, "../../evil.md", b"text").json()["filename"] == "evil.md"


def test_upload_content_is_not_logged(client, caplog):
    with caplog.at_level(logging.DEBUG):
        upload(client, "s.md", b"# S\nCONFIDENTIAL-PAYLOAD-XYZ")
    assert "CONFIDENTIAL-PAYLOAD-XYZ" not in server_log_text(caplog.records)


# --- list and get (T020, US3) ---------------------------------------------------------------

SAMPLE_TITLES = [
    "Expense Reimbursement Policy",
    "IT Security Policy",
    "Annual Leave Policy",
    "New Joiner Onboarding Guide",
    "Business Travel Policy",
]


def test_list_returns_five_samples_without_content(client):
    response = client.get("/documents")
    assert response.status_code == 200
    items = response.json()
    assert [i["title"] for i in items] == SAMPLE_TITLES
    assert [i["filename"] for i in items] == sorted(i["filename"] for i in items)
    for item in items:
        assert set(item) == {"id", "title", "filename", "size", "source"}
        assert item["source"] == "sample"


def test_list_includes_upload_last(client):
    new_id = upload(client, "n.md", b"# New Doc\nbody").json()["id"]
    items = client.get("/documents").json()
    assert len(items) == 6
    assert items[-1]["id"] == new_id


def test_get_document_returns_full_content(client, sample_dir):
    item = next(i for i in client.get("/documents").json() if i["filename"] == "leave-policy.md")
    response = client.get(f"/documents/{item['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == (sample_dir / "leave-policy.md").read_text(encoding="utf-8")
    assert body["title"] == "Annual Leave Policy"


def test_get_unknown_document_is_404(client):
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


# --- library size cap -----------------------------------------------------------------------


def test_upload_past_document_cap_is_409_and_library_unchanged(client, monkeypatch):
    monkeypatch.setattr("app.main.MAX_DOCUMENTS", 7)
    assert upload(client, "a.md", b"# A\nalpha").status_code == 201
    assert upload(client, "b.md", b"# B\nbravo").status_code == 201
    before = client.get("/search", params={"q": "alpha"}).json()
    response = upload(client, "c.md", b"# C\ncharlie")
    assert response.status_code == 409
    assert "7" in response.json()["detail"]
    assert count(client) == 7
    assert client.get("/search", params={"q": "alpha"}).json() == before
    assert client.get("/search", params={"q": "charlie"}).json()["results"] == []


def test_upload_exactly_at_cap_is_accepted(client, monkeypatch):
    monkeypatch.setattr("app.main.MAX_DOCUMENTS", 6)
    assert upload(client, "a.md", b"# A\nalpha").status_code == 201
    assert count(client) == 6


def test_default_document_cap_is_1000():
    from app.ingest import MAX_DOCUMENTS

    assert MAX_DOCUMENTS == 1000

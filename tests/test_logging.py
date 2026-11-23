"""FR-017 / Principle IV: document content and query text never reach the server's logs."""

import logging

from tests.helpers import server_log_text

MARKER = "ZZ-UNIQUE-CONTENT-MARKER"
QUERY = "pineapple-sentinel-query"


def test_full_session_never_logs_content_or_query(client, caplog):
    with caplog.at_level(logging.DEBUG):
        created = client.post(
            "/documents",
            files={"file": ("m.md", f"# Marked\n{MARKER} {QUERY}".encode(), "text/markdown")},
        )
        assert created.status_code == 201
        doc_id = created.json()["id"]
        assert client.get("/search", params={"q": QUERY}).json()["results"][0]["id"] == doc_id
        assert MARKER in client.get(f"/documents/{doc_id}").json()["content"]
        client.post("/documents", files={"file": ("bad.txt", b"\xff" + MARKER.encode())})

    logged = server_log_text(caplog.records)
    assert "document_added" in logged  # the app does log events…
    assert MARKER not in logged  # …but never the content
    assert QUERY not in logged

import logging

from app.logging_filters import RedactQueryFilter, install_query_redaction


def make_access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:5000", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_query_string_is_redacted():
    record = make_access_record("/search?q=secret+text&k=2")
    RedactQueryFilter().filter(record)
    assert "secret" not in record.getMessage()
    assert "/search?<redacted>" in record.getMessage()


def test_path_without_query_is_unchanged():
    record = make_access_record("/documents")
    RedactQueryFilter().filter(record)
    assert '"GET /documents HTTP/1.1" 200' in record.getMessage()


def test_filter_always_returns_true():
    assert RedactQueryFilter().filter(make_access_record("/search?q=x")) is True
    assert RedactQueryFilter().filter(make_access_record("/health")) is True


def test_install_is_idempotent():
    logger = logging.getLogger("uvicorn.access")
    install_query_redaction()
    install_query_redaction()
    assert sum(isinstance(f, RedactQueryFilter) for f in logger.filters) == 1

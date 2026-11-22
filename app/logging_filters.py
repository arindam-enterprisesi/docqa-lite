"""Keep query text out of server access logs (FR-016, research.md R8)."""

import logging

_REDACTED = "?<redacted>"


def _redact(value: object) -> object:
    if isinstance(value, str) and "?" in value:
        return value.split("?", 1)[0] + _REDACTED
    return value


class RedactQueryFilter(logging.Filter):
    """Replace any query string in log record arguments with '?<redacted>'."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_redact(arg) for arg in record.args)
        return True


def install_query_redaction() -> None:
    """Attach RedactQueryFilter to the uvicorn access logger once."""
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactQueryFilter) for f in logger.filters):
        logger.addFilter(RedactQueryFilter())

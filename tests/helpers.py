import logging


def server_log_text(records: list[logging.LogRecord]) -> str:
    """Joined log messages, excluding the test client's own ``httpx`` request logging."""
    return " ".join(r.getMessage() for r in records if not r.name.startswith("httpx"))

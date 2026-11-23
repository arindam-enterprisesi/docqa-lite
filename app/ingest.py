"""Turning raw files into Documents: title extraction and sample loading."""

import logging
import re
import uuid
from pathlib import Path, PurePosixPath

from app.repository import Document

logger = logging.getLogger("docqa")

MAX_TITLE_CHARS = 200
MAX_BYTES = 1_048_576
MAX_FILENAME_CHARS = 255
ALLOWED_EXTENSIONS = (".md", ".markdown", ".txt")
_SAMPLE_EXTENSIONS = (".md", ".markdown")
_HEADING_RE = re.compile(r"^#[ \t]+(.*?)\s*$")


class UploadRejected(Exception):
    """An upload failed validation. ``detail`` is safe to show and never contains file content."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def new_id() -> str:
    return uuid.uuid4().hex


def extract_title(content: str, filename: str) -> str:
    """First non-empty level-1 Markdown heading, else the filename without its extension."""
    for line in content.splitlines():
        match = _HEADING_RE.match(line)
        if match and match.group(1):
            return match.group(1)[:MAX_TITLE_CHARS]
    return PurePosixPath(filename).stem[:MAX_TITLE_CHARS] or filename[:MAX_TITLE_CHARS]


def sanitize_filename(raw: str) -> str:
    """Base name only (after the last ``/`` or ``\\``); stem shortened to fit 255 chars."""
    name = re.split(r"[/\\]", raw)[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()  # no newlines etc. in logs
    if len(name) > MAX_FILENAME_CHARS:
        suffix = PurePosixPath(name).suffix
        if len(suffix) > 16:  # not a real extension; it will fail the type check anyway
            suffix = ""
        stem = name[: len(name) - len(suffix)]
        name = stem[: MAX_FILENAME_CHARS - len(suffix)] + suffix
    return name


def check_extension(filename: str) -> None:
    """Raise 415 unless the (sanitised) filename has an allowed extension and a non-empty stem."""
    path = PurePosixPath(filename)
    if not filename or path.suffix.lower() not in ALLOWED_EXTENSIONS or not path.stem:
        accepted = ", ".join(ALLOWED_EXTENSIONS)
        raise UploadRejected(415, f"Unsupported file type; accepted: {accepted}")


def decode_upload(data: bytes) -> str:
    """Validate size and encoding; return the text with any UTF-8 BOM removed."""
    if len(data) > MAX_BYTES:
        raise UploadRejected(413, "File too large; the maximum size is 1 MB (1,048,576 bytes)")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise UploadRejected(422, "File is not valid UTF-8 text") from None
    text = text.removeprefix("\ufeff")
    if not text.strip():
        raise UploadRejected(422, "File is empty")
    return text


def load_sample_dir(path: Path | None) -> list[Document]:
    """Load every ``.md``/``.markdown`` file in ``path`` (sorted by name).

    Samples pass the same size/UTF-8/non-empty gate as uploads; a failing file is skipped and
    logged by filename only.
    """
    if path is None or not path.is_dir():
        return []
    docs: list[Document] = []
    files = (f for f in path.iterdir() if f.suffix.lower() in _SAMPLE_EXTENSIONS and f.is_file())
    for file in sorted(files, key=lambda f: f.name):
        try:
            with file.open("rb") as handle:
                raw = handle.read(MAX_BYTES + 1)  # bounded: an oversize sample is never fully read
            content = decode_upload(raw)
        except OSError as exc:
            logger.warning("sample_skipped filename=%s error=%s", file.name, type(exc).__name__)
            continue
        except UploadRejected as exc:
            logger.warning(
                "sample_skipped filename=%s status=%d reason=%r",
                file.name,
                exc.status_code,
                exc.detail,
            )
            continue
        docs.append(
            Document(
                id=new_id(),
                title=extract_title(content, file.name),
                filename=file.name,
                size=len(raw),
                content=content,
                source="sample",
            )
        )
    return docs

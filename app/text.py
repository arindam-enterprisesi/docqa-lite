"""Text helpers for document metadata."""

import re
from pathlib import PurePosixPath

from app.config import ALLOWED_EXTENSIONS, MAX_FILENAME_CHARS

_H1_PATTERN = re.compile(r"^#[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def derive_title(content: str, filename: str) -> str:
    """Return the first non-blank level-1 Markdown heading, else the filename stem."""
    for match in _H1_PATTERN.finditer(content):
        heading = match.group(1).strip()
        if heading:
            return heading
    return PurePosixPath(filename).stem


def safe_filename(name: str) -> str:
    """Return the display basename of a client-supplied filename ('' if none)."""
    basename = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return basename[:MAX_FILENAME_CHARS]


def has_allowed_extension(name: str) -> bool:
    """True if the filename ends in an allowed extension (case-insensitive)."""
    return PurePosixPath(name).suffix.lower() in ALLOWED_EXTENSIONS


def decode_utf8(data: bytes) -> str:
    """Strictly decode UTF-8; raises ValueError (UnicodeDecodeError) if invalid."""
    return data.decode("utf-8")

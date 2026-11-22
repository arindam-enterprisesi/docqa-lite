import pytest

from app.text import decode_utf8, has_allowed_extension, safe_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.md", "passwd.md"),
        ("a\\b\\c.txt", "c.txt"),
        ("plain.md", "plain.md"),
        ("  spaced.md  ", "spaced.md"),
        ("", ""),
        ("   ", ""),
        ("folder/", ""),
    ],
)
def test_safe_filename(raw, expected):
    assert safe_filename(raw) == expected


def test_safe_filename_truncates_to_255_chars():
    assert len(safe_filename("x" * 300 + ".md")) == 255


@pytest.mark.parametrize("name", ["a.md", "A.MD", "notes.markdown", "readme.txt", "x.Txt"])
def test_allowed_extensions(name):
    assert has_allowed_extension(name) is True


@pytest.mark.parametrize("name", ["report.pdf", "a.md.pdf", "noext", "", ".md", "image.png"])
def test_disallowed_extensions(name):
    assert has_allowed_extension(name) is False


def test_decode_utf8_valid():
    assert decode_utf8("Café".encode()) == "Café"


def test_decode_utf8_invalid_raises_value_error():
    with pytest.raises(ValueError):
        decode_utf8(b"\xff\xfe")

import pytest

from app.text import derive_title


def test_derive_title_uses_first_h1():
    assert derive_title("# Expense Policy\n\nBody text.", "expense.md") == "Expense Policy"


def test_derive_title_finds_h1_not_on_first_line():
    content = "Intro paragraph.\n\n# Real Title\n\nMore text.\n# Second Title\n"
    assert derive_title(content, "doc.md") == "Real Title"


def test_derive_title_ignores_lower_level_headings():
    content = "## Subsection\n\nText.\n"
    assert derive_title(content, "notes.md") == "notes"


def test_derive_title_ignores_hash_without_space():
    assert derive_title("#NoSpace\nText", "tagged.md") == "tagged"


def test_derive_title_strips_surrounding_whitespace():
    assert derive_title("#   Padded Title   \n", "x.md") == "Padded Title"


def test_derive_title_falls_back_when_heading_is_blank():
    # analysis U1: a whitespace-only heading must not yield an empty title.
    assert derive_title("#    \nText", "fallback.md") == "fallback"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("leave-policy.md", "leave-policy"),
        ("readme.markdown", "readme"),
        ("plain notes.txt", "plain notes"),
    ],
)
def test_derive_title_falls_back_to_filename_stem(filename, expected):
    assert derive_title("No heading here.\n", filename) == expected

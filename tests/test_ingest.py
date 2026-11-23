import logging

import pytest

from app.ingest import (
    MAX_BYTES,
    UploadRejected,
    check_extension,
    decode_upload,
    extract_title,
    load_sample_dir,
    sanitize_filename,
)

EXPECTED_SAMPLE_TITLES = {
    "expense-policy.md": "Expense Reimbursement Policy",
    "it-security-policy.md": "IT Security Policy",
    "leave-policy.md": "Annual Leave Policy",
    "onboarding-guide.md": "New Joiner Onboarding Guide",
    "travel-policy.md": "Business Travel Policy",
}


# --- extract_title -------------------------------------------------------------------------


def test_title_from_first_level1_heading():
    assert extract_title("intro\n# Main Title\n# Second\n", "x.md") == "Main Title"


def test_title_ignores_level2_headings():
    assert extract_title("## Sub heading\nbody\n", "notes.md") == "notes"


def test_title_falls_back_to_filename_stem():
    assert extract_title("just text", "my-notes.txt") == "my-notes"


def test_title_skips_empty_heading():
    assert extract_title("# \n# Real\n", "x.md") == "Real"


def test_title_truncated_to_200_chars():
    title = extract_title("# " + "a" * 300, "x.md")
    assert len(title) == 200


# --- load_sample_dir -----------------------------------------------------------------------


def test_load_sample_dir_loads_five_sorted_samples(sample_dir):
    docs = load_sample_dir(sample_dir)
    assert [d.filename for d in docs] == sorted(EXPECTED_SAMPLE_TITLES)
    for doc in docs:
        assert doc.source == "sample"
        assert doc.title == EXPECTED_SAMPLE_TITLES[doc.filename]
        assert doc.size == (sample_dir / doc.filename).stat().st_size
        assert doc.content
    assert len({d.id for d in docs}) == 5


def test_load_sample_dir_skips_non_utf8_file_and_logs_name_only(make_sample_dir, caplog):
    secret = b"\xff\xfeTOPSECRET-CONTENT"
    directory = make_sample_dir({"bad.md": secret, "good.md": b"# Good\nfine text"})
    with caplog.at_level(logging.DEBUG):
        docs = load_sample_dir(directory)
    assert [d.filename for d in docs] == ["good.md"]
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "bad.md" in messages
    assert "TOPSECRET" not in messages


def test_load_sample_dir_ignores_non_markdown_files(make_sample_dir):
    directory = make_sample_dir({"a.md": b"# A\ntext", "b.txt": b"plain"})
    assert [d.filename for d in load_sample_dir(directory)] == ["a.md"]


def test_load_sample_dir_loads_markdown_extension_sorted_with_md(make_sample_dir):
    directory = make_sample_dir(
        {"b.markdown": b"# B\ntext", "a.md": b"# A\ntext", "c.MARKDOWN": b"# C\ntext"}
    )
    assert [d.filename for d in load_sample_dir(directory)] == ["a.md", "b.markdown", "c.MARKDOWN"]


@pytest.mark.parametrize(
    "bad",
    [b"", b"  \n\t ", b"x" * (MAX_BYTES + 1), b"\xff\xfeTOPSECRET-CONTENT"],
    ids=["empty", "blank", "too-large", "non-utf8"],
)
def test_load_sample_dir_skips_samples_failing_the_admission_gate(make_sample_dir, caplog, bad):
    directory = make_sample_dir({"bad.md": bad, "good.markdown": b"# Good\nfine text"})
    with caplog.at_level(logging.DEBUG):
        docs = load_sample_dir(directory)
    assert [d.filename for d in docs] == ["good.markdown"]
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "bad.md" in messages
    assert "TOPSECRET" not in messages


def test_load_sample_dir_accepts_sample_of_exactly_max_bytes(make_sample_dir):
    directory = make_sample_dir({"edge.md": b"x" * MAX_BYTES})
    assert [d.size for d in load_sample_dir(directory)] == [MAX_BYTES]


def test_load_sample_dir_missing_directory_returns_empty(tmp_path):
    assert load_sample_dir(tmp_path / "nope") == []


def test_load_sample_dir_none_returns_empty():
    assert load_sample_dir(None) == []


# --- upload validation (T016) --------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.md", "passwd.md"),
        ("..\\..\\x.txt", "x.txt"),
        ("  notes.md  ", "notes.md"),
        ("dir/sub/readme.markdown", "readme.markdown"),
        ("a\nfake_log_line.md", "afake_log_line.md"),
    ],
)
def test_sanitize_filename_keeps_base_name(raw, expected):
    assert sanitize_filename(raw) == expected


def test_sanitize_filename_shortens_stem_and_keeps_extension():
    name = sanitize_filename("a" * 300 + ".md")
    assert len(name) == 255
    assert name.endswith(".md")


@pytest.mark.parametrize("name", ["a.md", "B.MD", "c.markdown", "d.Txt"])
def test_allowed_extensions(name):
    check_extension(name)  # does not raise


@pytest.mark.parametrize("name", ["report.pdf", "evil.MD.exe", "noext", "", ".md"])
def test_rejected_extensions_are_415(name):
    with pytest.raises(UploadRejected) as exc:
        check_extension(name)
    assert exc.value.status_code == 415


def test_empty_upload_is_422():
    with pytest.raises(UploadRejected) as exc:
        decode_upload(b"")
    assert exc.value.status_code == 422


def test_whitespace_only_upload_is_422():
    with pytest.raises(UploadRejected) as exc:
        decode_upload(b"  \n\t ")
    assert exc.value.status_code == 422


def test_exactly_max_bytes_accepted():
    assert len(decode_upload(b"a" * MAX_BYTES)) == MAX_BYTES


def test_one_byte_over_is_413():
    with pytest.raises(UploadRejected) as exc:
        decode_upload(b"a" * (MAX_BYTES + 1))
    assert exc.value.status_code == 413


def test_invalid_utf8_is_422_and_detail_has_no_content():
    with pytest.raises(UploadRejected) as exc:
        decode_upload(b"\xff\xfeSECRET")
    assert exc.value.status_code == 422
    assert "SECRET" not in exc.value.detail


def test_bom_is_stripped():
    assert decode_upload("﻿# Hi".encode()) == "# Hi"

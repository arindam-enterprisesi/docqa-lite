from app.config import SAMPLE_DOCS_DIR
from app.loader import load_sample_documents


def test_loads_only_markdown_sorted_by_filename(tmp_path):
    (tmp_path / "b.md").write_text("# Bravo\n\nSecond.", encoding="utf-8")
    (tmp_path / "a.md").write_text("# Alpha\n\nFirst.", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("not loaded", encoding="utf-8")

    docs = load_sample_documents(tmp_path)

    assert [d.filename for d in docs] == ["a.md", "b.md"]
    assert [d.title for d in docs] == ["Alpha", "Bravo"]


def test_sets_sample_source_size_and_unique_ids(tmp_path):
    content = "# Café\n\nNon-ASCII text."
    (tmp_path / "cafe.md").write_text(content, encoding="utf-8")
    (tmp_path / "other.md").write_text("plain", encoding="utf-8")

    docs = load_sample_documents(tmp_path)

    cafe = docs[0]
    assert cafe.source == "sample"
    assert cafe.size_bytes == len(content.encode("utf-8"))
    assert cafe.content == content
    assert len({d.id for d in docs}) == 2


def test_title_falls_back_to_stem_without_heading(tmp_path):
    (tmp_path / "no-heading.md").write_text("Just text.", encoding="utf-8")
    assert load_sample_documents(tmp_path)[0].title == "no-heading"


def test_skips_invalid_utf8_and_loads_the_rest(tmp_path):
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe\x00broken")
    (tmp_path / "good.md").write_text("# Good", encoding="utf-8")

    docs = load_sample_documents(tmp_path)

    assert [d.filename for d in docs] == ["good.md"]


def test_missing_directory_returns_empty_list(tmp_path):
    assert load_sample_documents(tmp_path / "does-not-exist") == []


def test_real_sample_directory_yields_five_documents():
    docs = load_sample_documents(SAMPLE_DOCS_DIR)
    assert len(docs) == 5
    assert "Expense Reimbursement Policy" in {d.title for d in docs}

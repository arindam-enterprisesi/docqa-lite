import time

import pytest

from app.config import SAMPLE_DOCS_DIR, SNIPPET_CHARS
from app.loader import load_sample_documents
from app.models import Document
from app.search import SearchIndex


def make_document(doc_id: str, content: str, title: str = "Doc") -> Document:
    return Document(
        id=doc_id,
        title=title,
        filename=f"{doc_id}.md",
        size_bytes=len(content.encode("utf-8")),
        content=content,
        source="upload",
    )


@pytest.fixture
def sample_index() -> SearchIndex:
    index = SearchIndex()
    index.rebuild(load_sample_documents(SAMPLE_DOCS_DIR))
    return index


# --- T015: rebuild / search -------------------------------------------------


def test_empty_index_returns_no_results():
    index = SearchIndex()
    index.rebuild([])
    assert index.search("anything", 5) == []


def test_unbuilt_index_returns_no_results():
    assert SearchIndex().search("anything", 5) == []


def test_stop_word_only_corpus_does_not_raise():
    index = SearchIndex()
    index.rebuild([make_document("a", "the and of", title="the")])
    assert index.search("the", 5) == []


def test_relevant_document_ranks_first(sample_index):
    results = sample_index.search("reimbursed meals receipt", 5)
    assert results[0].title == "Expense Reimbursement Policy"


def test_unknown_term_returns_empty(sample_index):
    assert sample_index.search("zxqvy", 5) == []


def test_stop_word_query_returns_empty(sample_index):
    assert sample_index.search("the and of", 5) == []


def test_scores_are_in_range_and_rounded(sample_index):
    results = sample_index.search("leave days employees", 20)
    assert results
    for result in results:
        assert 0 < result.score <= 1
        assert result.score == round(result.score, 4)


def test_results_limited_to_k_and_sorted(sample_index):
    results = sample_index.search("policy employees manager", 2)
    assert len(results) <= 2
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_ties_are_broken_by_id_ascending():
    index = SearchIndex()
    index.rebuild(
        [
            make_document("bbb", "identical searchable text"),
            make_document("aaa", "identical searchable text"),
            make_document("ccc", "unrelated words entirely"),
        ]
    )
    results = index.search("searchable", 5)
    assert [r.id for r in results] == ["aaa", "bbb"]


def test_search_is_deterministic(sample_index):
    first = sample_index.search("travel flights manager", 5)
    second = sample_index.search("travel flights manager", 5)
    assert first == second


def test_rebuild_replaces_previous_corpus():
    index = SearchIndex()
    index.rebuild([make_document("a", "alpha content")])
    index.rebuild([make_document("b", "bravo content")])
    assert index.search("alpha", 5) == []
    assert [r.id for r in index.search("bravo", 5)] == ["b"]


def test_search_over_100_documents_is_fast():
    words = ["policy", "travel", "leave", "expense", "laptop", "badge", "manager", "portal"]
    docs = [
        make_document(f"d{i:03d}", " ".join(words[(i + j) % len(words)] for j in range(150)))
        for i in range(100)
    ]
    index = SearchIndex()
    index.rebuild(docs)
    start = time.perf_counter()
    index.search("travel portal manager", 5)
    assert time.perf_counter() - start < 1.0


# --- T016: snippet ------------------------------------------------------------


LONG_TEXT = ("filler words here. " * 30) + "The KEYWORD appears here. " + ("trailing text. " * 30)


def test_snippet_never_exceeds_limit():
    assert len(SearchIndex().snippet(LONG_TEXT, "keyword")) <= SNIPPET_CHARS


def test_snippet_is_centred_on_match_case_insensitive():
    snippet = SearchIndex().snippet(LONG_TEXT, "keyword")
    assert "KEYWORD" in snippet
    assert snippet.startswith("…")
    assert snippet.endswith("…")


def test_snippet_has_no_leading_ellipsis_when_match_at_start():
    text = "Keyword at the very start. " + ("more text. " * 40)
    snippet = SearchIndex().snippet(text, "keyword")
    assert snippet.startswith("Keyword")
    assert snippet.endswith("…")
    assert len(snippet) <= SNIPPET_CHARS


def test_snippet_without_match_uses_opening_text():
    text = "Opening sentence. " + ("other words. " * 40)
    snippet = SearchIndex().snippet(text, "absent")
    assert snippet.startswith("Opening sentence.")
    assert len(snippet) <= SNIPPET_CHARS


def test_snippet_matches_whole_words_only():
    text = ("x " * 120) + "cart " + ("y " * 10) + "art gallery " + ("z " * 120)
    snippet = SearchIndex().snippet(text, "art")
    assert "art gallery" in snippet


def test_snippet_collapses_whitespace():
    snippet = SearchIndex().snippet("Line one.\n\n   Line   two.", "two")
    assert snippet == "Line one. Line two."


def test_short_content_returned_whole_without_ellipses():
    assert SearchIndex().snippet("Short text about leave.", "leave") == "Short text about leave."


def test_search_results_include_snippets(sample_index):
    result = sample_index.search("phishing", 1)[0]
    assert "phishing" in result.snippet.lower()
    assert len(result.snippet) <= SNIPPET_CHARS

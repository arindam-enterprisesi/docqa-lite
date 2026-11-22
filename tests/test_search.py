import os
import time

import pytest

from app.ingest import load_sample_dir
from app.repository import Document
from app.search import SearchIndex, make_snippet


def doc(doc_id: str, content: str, title: str | None = None) -> Document:
    return Document(
        id=doc_id,
        title=title or doc_id,
        filename=f"{doc_id}.md",
        size=len(content.encode()),
        content=content,
        source="upload",
    )


@pytest.fixture
def sample_index(sample_dir) -> SearchIndex:
    index = SearchIndex()
    index.rebuild(load_sample_dir(sample_dir))
    return index


# --- ranking (T010) ------------------------------------------------------------------------


def test_annual_leave_ranks_leave_policy_first(sample_index):
    hits = sample_index.search("annual leave", 5)
    assert hits[0].title == "Annual Leave Policy"


def test_top_k_limits_and_orders_results(sample_index):
    hits = sample_index.search("receipt reimbursement", 2)
    assert 1 <= len(hits) <= 2
    assert hits[0].title == "Expense Reimbursement Policy"
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("query", ["zebra", "the and of"])
def test_no_relevant_terms_returns_empty(sample_index, query):
    assert sample_index.search(query, 5) == []


@pytest.mark.parametrize(
    ("phrase", "title"),
    [
        ("itemised receipt finance system", "Expense Reimbursement Policy"),
        ("full-disk encryption password manager", "IT Security Policy"),
        ("annual leave carried over", "Annual Leave Policy"),
        ("onboarding buddy badge", "New Joiner Onboarding Guide"),
        ("economy class flights travel portal", "Business Travel Policy"),
    ],
)
def test_distinctive_phrase_finds_each_sample_first(sample_index, phrase, title):
    assert sample_index.search(phrase, 5)[0].title == title


def test_scores_in_range_with_at_most_four_decimals(sample_index):
    for hit in sample_index.search("policy travel leave security expense", 20):
        assert 0 < hit.score <= 1
        assert round(hit.score, 4) == hit.score


def test_search_is_deterministic(sample_index):
    assert sample_index.search("travel approval", 5) == sample_index.search("travel approval", 5)


def test_ties_keep_insertion_order():
    index = SearchIndex()
    index.rebuild([doc("first", "kiwi orchard"), doc("second", "kiwi orchard"), doc("x", "pear")])
    hits = index.search("kiwi", 5)
    assert [h.id for h in hits] == ["first", "second"]
    assert hits[0].score == hits[1].score


def test_empty_corpus_returns_empty():
    index = SearchIndex()
    index.rebuild([])
    assert index.search("anything", 5) == []


def test_stop_word_only_corpus_does_not_raise():
    index = SearchIndex()
    index.rebuild([doc("a", "the and of")])
    assert index.search("the", 5) == []


def test_unbuilt_index_returns_empty():
    assert SearchIndex().search("leave", 5) == []


# --- snippets (T011) -----------------------------------------------------------------------

POLICY = (
    "# Annual Leave Policy\n\n"
    "Full-time employees receive 24 days of annual leave per calendar year. "
    "Leave accrues monthly.\n\n"
    "Up to five unused days can be carried over to the next year."
)


def test_snippet_contains_query_term():
    snippet = make_snippet(POLICY, ["carried"])
    assert "carried" in snippet.lower()


def test_snippet_matches_case_insensitively():
    assert "full-time" in make_snippet(POLICY, ["employees"]).lower()


def test_snippet_never_starts_with_heading_marker():
    assert not make_snippet(POLICY, ["annual"]).startswith("#")


def test_snippet_falls_back_to_first_body_passage():
    assert make_snippet(POLICY, ["nomatch"]).startswith("Full-time employees")


def test_snippet_falls_back_to_heading_when_no_body():
    assert make_snippet("# Quokka", ["quokka"]) == "Quokka"


def test_long_snippet_truncated_at_word_boundary_with_ellipsis():
    content = "alpha " + " ".join(["lorem"] * 100)
    snippet = make_snippet(content, ["alpha"])
    assert len(snippet) <= 200
    assert snippet.endswith("…")
    assert snippet[:-1].endswith("lorem")


def test_short_snippet_has_no_ellipsis():
    assert not make_snippet(POLICY, ["carried"]).endswith("…")


def test_search_hits_carry_snippets(sample_index):
    hit = sample_index.search("carried over", 1)[0]
    assert len(hit.snippet) <= 200
    assert "carried over" in hit.snippet.lower()


# --- performance (T023, SC-004) -------------------------------------------------------------

WORDS = [
    "policy", "travel", "leave", "expense", "laptop", "password", "manager", "approval",
    "receipt", "hotel", "flight", "badge", "training", "security", "holiday", "budget",
]  # fmt: skip


def synthetic_docs(n: int) -> list[Document]:
    return [
        doc(f"d{i}", " ".join(WORDS[(i * 7 + j) % len(WORDS)] for j in range(60)) + f" uniq{i}")
        for i in range(n)
    ]


def test_search_over_1000_documents_is_correct():
    index = SearchIndex()
    index.rebuild(synthetic_docs(1000))
    hits = index.search("uniq421", 5)
    assert hits[0].id == "d421"


@pytest.mark.skipif(
    os.environ.get("DOCQA_PERF") != "1",
    reason="timing check; run with DOCQA_PERF=1 (constitution: no wall-clock in default tests)",
)
def test_search_over_1000_documents_under_one_second():
    index = SearchIndex()
    index.rebuild(synthetic_docs(1000))
    start = time.perf_counter()
    index.search("travel approval receipt", 5)
    assert time.perf_counter() - start < 1.0

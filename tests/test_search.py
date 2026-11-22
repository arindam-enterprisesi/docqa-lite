import logging

import pytest

from app.main import get_index

SECRET_QUERY = "phishing credentials"


def search(client, **params):
    return client.get("/search", params=params)


def test_relevant_document_first_with_full_shape(client):
    response = search(client, q="reimbursed meals receipt")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"query", "k", "results"}
    top = body["results"][0]
    assert set(top) == {"id", "title", "score", "snippet"}
    assert top["title"] == "Expense Reimbursement Policy"
    assert 0 < top["score"] <= 1
    assert top["snippet"]


@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("reimbursed meals receipt", "Expense Reimbursement Policy"),
        ("password manager encryption phishing", "IT Security Policy"),
        ("annual leave sick days", "Annual Leave Policy"),
        ("onboarding buddy first day", "New Joiner Onboarding Guide"),
        ("flights hotels travel portal", "Business Travel Policy"),
    ],
)
def test_each_sample_ranks_first_for_distinctive_query(client, query, title):
    assert search(client, q=query).json()["results"][0]["title"] == title


def test_k_limits_results_and_sorts_by_score(client):
    results = search(client, q="policy employees manager days", k=2).json()["results"]
    assert len(results) <= 2
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_default_k_is_five(client):
    body = search(client, q="policy").json()
    assert body["k"] == 5
    assert len(body["results"]) <= 5


def test_no_match_returns_empty_list(client):
    response = search(client, q="zxqvy")
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_query_is_trimmed_and_echoed(client):
    assert search(client, q="  leave  ").json()["query"] == "leave"


def test_snippets_within_limit(client):
    for hit in search(client, q="employees", k=20).json()["results"]:
        assert len(hit["snippet"]) <= 200


@pytest.mark.parametrize("k", ["0", "21", "abc", "-1"])
def test_invalid_k_rejected(client, k):
    assert search(client, q="leave", k=k).status_code == 422


def test_missing_query_rejected(client):
    assert client.get("/search").status_code == 422


@pytest.mark.parametrize("q", ["", "   ", "\t\n"])
def test_blank_query_rejected(client, q):
    response = search(client, q=q)
    assert response.status_code == 422


def test_query_length_limits(client):
    assert search(client, q="a" * 500).status_code == 200
    assert search(client, q="a" * 501).status_code == 422


def test_query_length_counted_after_trimming(client):
    assert search(client, q="  " + "a" * 500 + "  ").status_code == 200


def test_query_and_snippets_not_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    body = search(client, q=SECRET_QUERY).json()
    log_text = caplog.text
    assert SECRET_QUERY not in log_text
    assert "phishing" not in log_text
    for hit in body["results"]:
        assert hit["snippet"] not in log_text


def test_get_index_returns_app_state_index(client):
    class FakeRequest:
        app = client.app

    assert get_index(FakeRequest()) is client.app.state.index

import logging

import pytest

from tests.helpers import server_log_text


def test_search_returns_leave_policy_first(client):
    response = client.get("/search", params={"q": "annual leave"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"query", "k", "results"}
    first = body["results"][0]
    assert first["title"] == "Annual Leave Policy"
    assert set(first) == {"id", "title", "score", "snippet"}
    assert 0 < first["score"] <= 1
    assert len(first["snippet"]) <= 200


def test_default_k_is_five(client):
    assert client.get("/search", params={"q": "policy"}).json()["k"] == 5


def test_k_limits_results(client):
    body = client.get("/search", params={"q": "receipt reimbursement", "k": 2}).json()
    assert len(body["results"]) <= 2
    assert body["results"][0]["title"] == "Expense Reimbursement Policy"


def test_no_match_returns_empty_list(client):
    response = client.get("/search", params={"q": "zebra"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_query_is_trimmed(client):
    assert client.get("/search", params={"q": "  leave  "}).json()["query"] == "leave"


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "   "},
        {"q": "a" * 501},
        {"q": "leave", "k": 0},
        {"q": "leave", "k": 21},
        {"q": "leave", "k": "abc"},
    ],
)
def test_invalid_search_input_is_422(client, params):
    response = client.get("/search", params=params)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_query_text_is_not_logged(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.get("/search", params={"q": "marmalade-sentinel"})
    assert "marmalade-sentinel" not in server_log_text(caplog.records)

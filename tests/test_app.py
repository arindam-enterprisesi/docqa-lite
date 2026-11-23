from app import __version__


def test_startup_loads_five_samples(client):
    docs = client.app.state.repository.list()
    assert len(docs) == 5
    assert all(d.source == "sample" for d in docs)


def test_empty_sample_dir_starts_empty(make_client, make_sample_dir):
    c = make_client(sample_dir=make_sample_dir({}))
    assert c.app.state.repository.list() == []


def test_startup_lists_all_five_shipped_samples(client):
    names = {d["filename"] for d in client.get("/documents").json()}
    assert names == {
        "expense-policy.md",
        "it-security-policy.md",
        "leave-policy.md",
        "onboarding-guide.md",
        "travel-policy.md",
    }


def test_startup_loads_markdown_samples_and_skips_bad_ones(make_client, make_sample_dir):
    directory = make_sample_dir(
        {"a.markdown": b"# A\ntext", "b.md": b"", "c.md": b"\xff\xfe", "d.md": b"# D\ntext"}
    )
    c = make_client(sample_dir=directory)
    response = c.get("/documents")
    assert response.status_code == 200
    assert [d["filename"] for d in response.json()] == ["a.markdown", "d.md"]


def test_apps_do_not_share_state(make_client):
    first = make_client()
    second = make_client()
    assert first.app.state.repository is not second.app.state.repository


def test_root_and_health_still_work(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok", "version": __version__}

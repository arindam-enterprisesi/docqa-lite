from app import __version__


def test_startup_loads_five_samples(client):
    docs = client.app.state.repository.list()
    assert len(docs) == 5
    assert all(d.source == "sample" for d in docs)


def test_empty_sample_dir_starts_empty(make_client, make_sample_dir):
    c = make_client(sample_dir=make_sample_dir({}))
    assert c.app.state.repository.list() == []


def test_apps_do_not_share_state(make_client):
    first = make_client()
    second = make_client()
    assert first.app.state.repository is not second.app.state.repository


def test_root_and_health_still_work(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok", "version": __version__}

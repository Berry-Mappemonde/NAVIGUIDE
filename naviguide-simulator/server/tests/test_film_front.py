"""Le film et l'horloge répondent sans passer par la file du briefing."""
from fastapi.testclient import TestClient

import film_front


def test_film_returns_the_snapshot(monkeypatch):
    monkeypatch.setattr(
        film_front.official_store,
        "serve_film",
        lambda **kwargs: {"status": "ready", "chapters": [], "lang": kwargs["lang"]},
    )
    client = TestClient(film_front.app)
    res = client.get("/voyage/official/film?lang=en&seconds=0")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["lang"] == "en"


def test_clock_returns_the_stored_bytes(monkeypatch):
    monkeypatch.setattr(film_front.official_store, "serve_clock_bytes", lambda: b'{"t":1}')
    client = TestClient(film_front.app)
    res = client.get("/voyage/official/clock")
    assert res.status_code == 200
    assert res.json() == {"t": 1}


def test_missing_clock_says_preparing(monkeypatch):
    monkeypatch.setattr(film_front.official_store, "serve_clock_bytes", lambda: None)
    monkeypatch.setattr(film_front.official_store, "nudge_fill_process", lambda: None)
    client = TestClient(film_front.app)
    res = client.get("/voyage/official/clock")
    assert res.status_code == 200
    assert res.json()["status"] == film_front.official_store.PREPARING

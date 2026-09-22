"""Lot R8b — GET /ici/moment renvoie un Moment signé."""
from __future__ import annotations

from fastapi.testclient import TestClient

import main
from moment import load_official_mini, signature


def test_ici_moment_uses_nearest_pearl(monkeypatch):
    voy = load_official_mini()
    pearl = voy["pearls"][0]
    import pearl_store
    pearl_store.put_pearl("r8b-la-rochelle", pearl, "rich", 46.15, -1.16)

    async def boom(*_a, **_k):
        raise AssertionError("fill_dossier ne doit pas être appelé si une perle est à portée")

    monkeypatch.setattr(main, "fill_dossier", boom)
    client = TestClient(main.app)
    res = client.get(
        "/ici/moment",
        params={"lat": 46.15, "lon": -1.16, "t": "2026-05-15T08:00:00Z", "mode": "follow"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body.get("signature")
    assert body["signature"] == signature(body)
    assert body["pos"]["lat"] == 46.15
    assert body["mode"] == "follow"
    assert body["here"]["zee"]["mrgid"] == 5677
    assert isinstance(body["alerts"], list)
    assert isinstance(body["around"], list)
    assert isinstance(body["sources"], list)
    assert body["leg"]["to"] == "Fort-de-France (Martinique)"


def test_ici_moment_computes_bag_like_ici(monkeypatch):
    voy = load_official_mini()
    pearl = voy["pearls"][0]

    async def fake(lat, lon, radius_nm=30, **_k):
        assert lat == 46.15
        assert lon == -1.16
        assert radius_nm == 30
        return pearl

    monkeypatch.setattr(main, "fill_dossier", fake)
    client = TestClient(main.app)
    res = client.get(
        "/ici/moment",
        params={"lat": 46.15, "lon": -1.16, "t": "2026-05-15T08:00:00Z", "mode": "simulation", "lang": "fr"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["signature"] == signature(body)
    assert body["mode"] == "simulation"
    assert body["here"]["zee"]["mrgid"] == 5677
    assert body["t"].startswith("2026-05-15")


def test_ici_moment_rejects_bad_coords():
    client = TestClient(main.app)
    res = client.get("/ici/moment", params={"lat": 120, "lon": 0})
    assert res.status_code == 400

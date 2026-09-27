"""Lot RF2 — stock officiel : une interface, deux dos, aucun calcul sur la requête."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

import official_store
from official_store import (
    DiskBackend,
    FAMILIES,
    FILM_SCRIPT_REV,
    MongoBackend,
    OfficialStore,
    PREPARING,
    READY,
    film_snapshot_stale,
    make_key,
    preparing_payload,
)

T0 = "2026-05-15T08:00:00Z"
NOW = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


class _FakeColl:
    def __init__(self):
        self.docs = {}

    def find_one(self, filt):
        return self.docs.get((filt or {}).get("_id"))

    def replace_one(self, filt, doc, upsert=True):
        self.docs[doc["_id"]] = dict(doc)
        return type("R", (), {"upserted_id": doc["_id"], "modified_count": 1})()


class _FakeDB:
    def __init__(self):
        self.cols = {}

    def __getitem__(self, name):
        return self.cols.setdefault(name, _FakeColl())


class FakeMongoClient:
    """Client in-process, même contrat que mongomock pour notre dos. Pas de réseau."""

    def __init__(self):
        self.dbs = {}

    def __getitem__(self, name):
        return self.dbs.setdefault(name, _FakeDB())


def _mongo_client():
    try:
        import mongomock
        return mongomock.MongoClient()
    except ImportError:
        return FakeMongoClient()


def _stores(tmp_path):
    disk = OfficialStore(DiskBackend(tmp_path / "disk"), now=lambda: NOW)
    mongo = OfficialStore(MongoBackend(_mongo_client()), now=lambda: NOW)
    return [("disk", disk), ("mongo", mongo)]


def _payload(family, tag="A"):
    if family == "film":
        return {
            "fr": {
                "chapters": [{"id": "c1", "text": f"Saint-Maur {tag} 15 mai 2026", "tA": T0, "tB": T0}],
                "source": "rules", "chars": 20, "targetSeconds": 0,
            },
            "default": {
                "chapters": [{"id": "c1", "text": f"Saint-Maur {tag} 15 mai 2026", "tA": T0, "tB": T0}],
                "source": "rules", "chars": 20, "targetSeconds": 0,
            },
        }
    if family == "eta":
        return {"stops": {"Dzaoudzi (Mayotte)": {
            "members": 12, "p10": "2026-10-11T00:00:00Z", "p90": "2026-10-13T00:00:00Z",
        }}}
    if family == "climo":
        return {"clock": {"t0": T0, "vertices": [{"lat": 46.15, "lon": -1.16, "iso": T0}]}, "regimes": [], "fiches": []}
    if family == "ici":
        return {"points": [{"lat": 46.15, "lon": -1.16, "nm": 0, "bag": {"zee": {"name": "FR"}, "at": {"lat": 46.15, "lon": -1.16}}}]}
    if family == "plan_review":
        return {"legs": [{"from": "La Rochelle", "to": "Fort-de-France (Martinique)"}]}
    return {"moments": [{"t": T0, "signature": tag}], "journal": {"count": 2, "latest": [{"t": T0, "kind": "stop", "name": "La Rochelle"}], "events": [], "days": []}}


@pytest.mark.parametrize("backend_name", ["disk", "mongo"])
def test_same_key_no_recompute(tmp_path, backend_name):
    store = dict(_stores(tmp_path))[backend_name]
    key = make_key("routeA", T0, "2026-09-26")
    calls = {"n": 0}

    def compute(voy, now):
        calls["n"] += 1
        return _payload("film", "once")

    voy = {"t0": T0, "points": [{"lat": 1, "lon": 2}], "marks": []}
    first = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=True,
    )
    assert first == READY
    key = store.family_key("film", voy, NOW)
    stored_at = store.get("film", key)["storedAt"]
    again = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=False,
    )
    assert again == "unchanged"
    assert calls["n"] == 1
    assert store.get("film", key)["storedAt"] == stored_at


@pytest.mark.parametrize("backend_name", ["disk", "mongo"])
def test_missing_is_preparing(tmp_path, backend_name):
    store = dict(_stores(tmp_path))[backend_name]
    assert store.get("film") is None
    body = preparing_payload("film", {"chapters": []})
    assert body["status"] == PREPARING
    assert body["reason"] == "en préparation"


@pytest.mark.parametrize("backend_name", ["disk", "mongo"])
def test_restart_rereads_same_payload(tmp_path, backend_name):
    if backend_name == "disk":
        root = tmp_path / "persist"
        a = OfficialStore(DiskBackend(root), now=lambda: NOW)
        key = make_key("r", T0, "2026-09-26")
        a.put("moments", _payload("moments"), key)
        b = OfficialStore(DiskBackend(root), now=lambda: NOW)
        hit = b.get("moments", key)
        assert hit["payload"]["journal"]["count"] == 2
        assert hit["storedAt"]
    else:
        client = _mongo_client()
        a = OfficialStore(MongoBackend(client), now=lambda: NOW)
        key = make_key("r", T0, "2026-09-26")
        a.put("eta", _payload("eta"), key)
        b = OfficialStore(MongoBackend(client), now=lambda: NOW)
        hit = b.get("eta", key)
        assert hit["payload"]["stops"]["Dzaoudzi (Mayotte)"]["members"] == 12


@pytest.mark.parametrize("backend_name", ["disk", "mongo"])
def test_atomic_replace_and_all_families(tmp_path, backend_name):
    store = dict(_stores(tmp_path))[backend_name]
    key = make_key("r", T0, "2026-09-26")
    for name in FAMILIES:
        store.put(name, _payload(name, "v1"), key)
        store.put(name, _payload(name, "v2"), key)
        hit = store.get(name, key)
        assert hit["payload"] is not None
        assert hit["storedAt"]
    st = store.status(key)
    assert all(st["families"][n]["status"] == READY for n in FAMILIES)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_FORECAST_BACKEND", "synthetic")
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path / "voyages"))
    import voyage_store
    voyage_store._DIR = tmp_path / "voyages"
    official_store.reset_store()
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


def test_http_missing_is_preparing_not_500(client):
    r = client.get("/voyage/official/journal")
    assert r.status_code == 200
    assert r.json()["status"] == PREPARING
    assert r.json()["latest"] == []

    film = client.get("/voyage/official/film?lang=fr&seconds=0")
    assert film.status_code == 200
    assert film.json()["status"] == PREPARING
    assert film.json()["chapters"] == []

    eta = client.get("/voyage/official/eta", params={"stop": "Dzaoudzi (Mayotte)"})
    assert eta.status_code == 200
    assert eta.json().get("members") == 0
    assert eta.json()["status"] == PREPARING

    review = client.get("/voyage/official/plan-review")
    assert review.status_code == 200
    assert review.json()["status"] == PREPARING
    assert review.json()["legs"] == []

    clock = client.get("/voyage/official/clock")
    assert clock.status_code == 200
    assert clock.json()["status"] == PREPARING


def test_http_serves_store_when_externals_would_fail(client, monkeypatch):
    import ensemble_eta
    import film_script
    import plan_review
    import voyage_api

    def boom(*_a, **_k):
        raise AssertionError("fournisseur appelé sur la requête")

    monkeypatch.setattr(film_script, "official_film", boom)
    monkeypatch.setattr(plan_review, "review_official", boom)
    monkeypatch.setattr(ensemble_eta, "peek_official_eta", boom)
    monkeypatch.setattr(ensemble_eta, "preheat_official_eta", boom)
    monkeypatch.setattr(voyage_api, "_climo_clock", boom)
    monkeypatch.setattr(voyage_api, "_kick_official_eta", boom)
    monkeypatch.setattr(voyage_api, "_kick_official_moments", boom)

    official_store.put("film", _payload("film"))
    official_store.put("plan_review", _payload("plan_review"))
    official_store.put("eta", _payload("eta"))
    official_store.put("climo", _payload("climo"))
    official_store.put("moments", _payload("moments"))

    film = client.get("/voyage/official/film?lang=fr&seconds=0")
    assert film.status_code == 200
    assert "Saint-Maur" in film.json()["chapters"][0]["text"]
    assert film.json()["status"] == READY

    review = client.get("/voyage/official/plan-review")
    assert review.status_code == 200
    assert review.json()["legs"][0]["to"] == "Fort-de-France (Martinique)"

    eta = client.get("/voyage/official/eta", params={"stop": "Dzaoudzi (Mayotte)"})
    assert eta.status_code == 200
    assert eta.json()["members"] == 12

    clock = client.get("/voyage/official/clock")
    assert clock.status_code == 200
    assert clock.json()["t0"].startswith("2026-05-15")

    journal = client.get("/voyage/official/journal")
    assert journal.status_code == 200
    assert journal.json()["status"] == READY
    assert journal.json()["latest"][0]["kind"] == "stop"


def test_http_ici_official_point_from_store_not_fill(client, monkeypatch):
    import main
    import voyage_api

    def boom(*_a, **_k):
        raise AssertionError("fill_dossier sur la requête officielle")

    monkeypatch.setattr(main, "fill_dossier", boom)
    voy = voyage_api.seed_official_voyage()
    assert voy and voy.get("points")
    official_store.put("ici", _payload("ici"))

    r = client.get("/ici", params={"lat": 46.15, "lon": -1.16})
    assert r.status_code == 200
    body = r.json()
    assert body.get("cached") is True or (body.get("zee") or {}).get("name") == "FR"


AIR_MARKS = [
    {"name": "Saint-Maur (Berry, Indre)", "nm": 0, "filmNm": 0, "lat": 46.8, "lon": 1.6},
    {"name": "Cayenne (Guyane)", "nm": 4000, "filmNm": 4000, "lat": 4.9, "lon": -52.3},
    {"name": "Halifax (Nouvelle-Écosse)", "nm": 4100, "filmNm": 4100, "lat": 44.6, "lon": -63.6},
    {"name": "Nouméa (Nouvelle-Calédonie)", "nm": 19000, "filmNm": 19000, "lat": -22.2, "lon": 166.4},
]


def _air_voy():
    return {
        "t0": T0,
        "points": [{"lat": 46.8, "lon": 1.6}, {"lat": 4.9, "lon": -52.3}],
        "marks": AIR_MARKS,
        "clock": {"t0": T0, "marks": AIR_MARKS, "vertices": []},
    }


def _stale_film_payload():
    chapter = {
        "id": "c1",
        "text": "Le 1er juillet, départ vers Saint-Pierre.",
        "tA": T0,
        "tB": T0,
    }
    plan = {"chapters": [chapter], "source": "rules", "chars": 40, "targetSeconds": 0}
    return {"fr": plan, "default": plan}


def _rf5_from_marks(marks, lang="fr"):
    import film_script
    outbound, back = film_script._air_pair_sentences(marks, lang)
    text = f"{outbound} {back}".strip()
    return {
        "chapters": [{"id": "c1", "text": text, "tA": T0, "tB": T0}],
        "source": "rules",
        "chars": len(text),
        "targetSeconds": 0,
        "hasWritten": False,
    }


def test_film_key_includes_script_rev(tmp_path):
    store = OfficialStore(DiskBackend(tmp_path / "disk"), now=lambda: NOW)
    voy = {"t0": T0, "points": [{"lat": 1, "lon": 2}], "marks": []}
    film_key = store.family_key("film", voy, NOW)
    base = store.current_key(voy, NOW)
    assert film_key == f"{base}:{FILM_SCRIPT_REV}"
    assert store.family_key("eta", voy, NOW) == base


def test_stale_film_refreshed_when_marks_have_air_pair(tmp_path):
    store = OfficialStore(DiskBackend(tmp_path / "disk"), now=lambda: NOW)
    voy = _air_voy()
    calls = {"n": 0}

    def compute(_voy, _now):
        calls["n"] += 1
        plan = _rf5_from_marks(_voy.get("marks") or [])
        return {"fr": plan, "default": plan}

    key = store.family_key("film", voy, NOW)
    store.put("film", _stale_film_payload(), key)
    assert film_snapshot_stale(store.get("film", key)["payload"], voy)
    status = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=False,
    )
    assert status == READY
    assert calls["n"] == 1
    blob = " ".join(
        c.get("text") or ""
        for c in store.get("film", key)["payload"]["fr"]["chapters"]
    )
    low = blob.lower()
    assert "prend l'avion pour" in low
    assert "retour en avion vers" in low

    again = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=False,
    )
    assert again == "unchanged"
    assert calls["n"] == 1


def test_ajaccio_refresh_does_not_invent_air(tmp_path):
    store = OfficialStore(DiskBackend(tmp_path / "disk"), now=lambda: NOW)
    voy = {
        "t0": T0,
        "points": [{"lat": 46.15, "lon": -1.16}],
        "marks": [
            {"name": "La Rochelle", "nm": 0, "lat": 46.15, "lon": -1.16},
            {"name": "Ajaccio (Corse)", "nm": 1820, "lat": 41.9, "lon": 8.7},
        ],
        "clock": {"t0": T0, "marks": [], "vertices": []},
    }
    plan = {
        "chapters": [{"id": "c1", "text": "Le 15 mai, départ vers Ajaccio.", "tA": T0, "tB": T0}],
        "source": "rules", "chars": 30, "targetSeconds": 0,
    }

    def compute(_voy, _now):
        return {"fr": plan, "default": plan}

    assert film_snapshot_stale({"fr": plan}, voy) is False
    status = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=True,
    )
    assert status == READY
    blob = store.get("film", store.family_key("film", voy, NOW))["payload"]["fr"]["chapters"][0]["text"]
    assert "prend l'avion" not in blob
    assert "retour en avion" not in blob


def test_cayenne_voyage_uses_itinerary_halifax_for_air(tmp_path):
    """Voyage stocké sans Halifax : l'itinéraire Berry (route.geojson) porte la paire."""
    from film_script import _route_has_air_pair

    if not _route_has_air_pair(official_store._itinerary_marks()):
        return
    store = OfficialStore(DiskBackend(tmp_path / "disk"), now=lambda: NOW)
    voy = {
        "t0": T0,
        "points": [{"lat": 4.9, "lon": -52.3}],
        "marks": [{"name": "Cayenne (Guyane)", "nm": 4000, "lat": 4.9, "lon": -52.3}],
        "clock": {"t0": T0, "marks": [], "vertices": []},
    }
    plan = {
        "chapters": [{
            "id": "c1",
            "text": "Le 18 août, départ vers Saint-Pierre.",
            "fromName": "Cayenne (Guyane)",
            "toName": "Saint-Pierre (Saint-Pierre-et-Miquelon)",
        }],
        "source": "rules", "chars": 40, "targetSeconds": 0,
    }
    stale = {"fr": plan, "default": plan}
    assert film_snapshot_stale(stale, voy)

    def compute(v, _now):
        raw = {
            "chapters": [dict(plan["chapters"][0])],
            "source": "rules", "chars": 40, "targetSeconds": 0,
        }
        done = official_store._apply_air_sentences(raw, "fr", v)
        return {"fr": done, "default": done}

    status = official_store.refresh_family(
        "film", compute=compute, now=NOW, store=store, voy=voy, force=True,
    )
    assert status == READY
    blob = store.get("film", store.family_key("film", voy, NOW))["payload"]["fr"]["chapters"][0]["text"]
    low = blob.lower()
    assert "prend l'avion pour" in low
    assert "retour en avion vers" in low


def test_http_force_refresh_film_serves_air_when_marks_have_pair(client, monkeypatch):
    import film_script
    import voyage_store
    from tests.test_voyage_journal import PUBLIC
    from voyage_clock import OFFICIAL_VOYAGE_ID

    body = {
        "t0": T0,
        "expedition_id": "berry-mappemonde-2026",
        "routeKind": "berry",
        "follow": True,
        "forecast": False,
        "official": True,
        "points": [
            {"lat": 46.8, "lon": 1.6, "cumNm": 0},
            {"lat": 4.9, "lon": -52.3, "cumNm": 4000},
            {"lat": 44.6, "lon": -63.6, "cumNm": 4100},
            {"lat": -22.2, "lon": 166.4, "cumNm": 19000},
        ],
        "marks": AIR_MARKS,
    }
    put = client.put("/voyage/official", json=body, headers=PUBLIC)
    assert put.status_code == 200
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)
    assert voy and voy.get("marks")
    names = " ".join(m.get("name") or "" for m in voy["marks"])
    assert "Cayenne" in names and "Halifax" in names

    async def from_marks(*, lang="fr", **_k):
        return _rf5_from_marks(voy.get("marks") or [], lang)

    monkeypatch.setattr(film_script, "official_film", from_marks)
    official_store.put("film", _stale_film_payload())
    stale = client.get("/voyage/official/film?lang=fr&seconds=0")
    assert stale.status_code == 200
    assert stale.json()["status"] == PREPARING
    assert stale.json()["chapters"] == []

    assert official_store.refresh_family("film", force=True) == READY
    film = client.get("/voyage/official/film?lang=fr&seconds=0")
    assert film.status_code == 200
    blob = " ".join(c.get("text") or "" for c in film.json().get("chapters") or [])
    low = blob.lower()
    assert "prend l'avion pour" in low
    assert "retour en avion vers" in low

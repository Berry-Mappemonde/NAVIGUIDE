"""Journal serveur du voyage officiel — mémoire honnête, jamais inventée."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import admin_guard
import forecast_cube
import saildocs
import voyage_api
import voyage_journal as journal
import voyage_store
from voyage_clock import OFFICIAL_T0, OFFICIAL_VOYAGE_ID, parse_iso

PUBLIC = {"X-Real-IP": "203.0.113.7", "X-Forwarded-For": "203.0.113.7"}
T0 = parse_iso(OFFICIAL_T0)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_FORECAST_BACKEND", "synthetic")
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path / "voyages"))
    monkeypatch.setenv("NAVIGUIDE_FORECAST_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("NAVIGUIDE_GRIB_DIR", str(tmp_path / "grib"))
    monkeypatch.setenv("NAVIGUIDE_GRIB_AUTO", "0")
    monkeypatch.delenv(admin_guard.ADMIN_ENV, raising=False)
    voyage_store._DIR = tmp_path / "voyages"
    forecast_cube.CACHE_DIR = tmp_path / "cache"
    saildocs.GRIB_DIR = tmp_path / "grib"
    journal.reset()
    admin_guard.reset_limiters()
    from main import app
    return TestClient(app)


def _official():
    return {
        "t0": OFFICIAL_T0,
        "expedition_id": "berry-mappemonde-2026",
        "routeKind": "berry",
        "follow": True,
        "forecast": False,
        "startAt": "la-rochelle",
        "official": True,
        "points": [
            {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
            {"lat": 40.0, "lon": -15.0, "cumNm": 650, "filmCum": 650, "jump": False, "nonMaritime": False},
            {"lat": 28.0, "lon": -30.0, "cumNm": 1450, "filmCum": 1450, "jump": False, "nonMaritime": False},
            {"lat": 14.6, "lon": -61.07, "cumNm": 3350, "filmCum": 3350, "jump": False, "nonMaritime": False},
        ],
        "marks": [
            {"name": "La Rochelle", "nm": 0, "filmNm": 0, "lat": 46.15, "lon": -1.16, "index": 0},
            {"name": "Fort-de-France (Martinique)", "nm": 3350, "filmNm": 3350, "lat": 14.6, "lon": -61.07, "index": 3},
        ],
    }


def _freeze(monkeypatch, when: datetime):
    monkeypatch.setattr(voyage_api, "_now", lambda: when)


def test_positions_every_six_hours_from_t0_and_idempotent(client, monkeypatch):
    now = T0 + timedelta(days=2, hours=5)  # 2026-05-17T13:00Z
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)

    first = journal.tick(voy, now, force=True)
    assert first["positions"] == 10  # 15/05 06 12 18 · 16/05 ×4 · 17/05 00 06 12
    again = journal.tick(voy, now, force=True)
    assert again["positions"] == 0

    days = journal.list_days()
    assert [d["day"] for d in days] == ["2026-05-15", "2026-05-16", "2026-05-17"]
    entries = journal.read_day("2026-05-16")
    assert [e["t"][11:13] for e in entries if e["kind"] == "position"] == ["00", "06", "12"] + ["18"]
    sample = entries[0]
    assert sample["basis"] == "clock"
    assert sample["lat"] is not None and sample["lon"] is not None
    assert sample["status"] in ("live", "waiting", "arrived")

    # The next day brings only the missing slots.
    later = now + timedelta(hours=13)  # 2026-05-18T02:00Z → 17/05 18h, 18/05 00h
    assert journal.tick(voy, later, force=True)["positions"] == 2


def test_stops_are_recorded_once_passed(client, monkeypatch):
    client.put("/voyage/official", json=_official())
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)
    marks = voy["clock"]["marks"]
    assert marks and marks[-1]["name"].startswith("Fort-de-France")
    arrival = T0 + timedelta(hours=float(marks[-1]["tHours"]))

    before = journal.record_stops(voy["clock"], arrival - timedelta(hours=1))
    assert before == 0
    after = journal.record_stops(voy["clock"], arrival + timedelta(hours=1))
    assert after >= 1
    stops = journal.latest(10, kinds=["stop"])
    assert stops[0]["event"] == "arrival"
    assert stops[0]["name"].startswith("Fort-de-France")
    assert stops[0]["basis"] == "clock"
    assert journal.record_stops(voy["clock"], arrival + timedelta(hours=1)) == 0


def test_grib_at_the_boat_once_per_cycle(client, monkeypatch):
    now = T0 + timedelta(days=3)
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)
    record = {
        "status": "ready",
        "cycle": "2026-05-18T06:00:00Z",
        "model": "GFS",
        "source": "openmeteo",
        "samples": [{
            "lat": 44.0, "lon": -6.0, "t": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "windKnots": 14.2, "dirFromDeg": 250, "pressHpa": 1013.2, "rainMm": 0.2, "hs": 1.1,
        }],
    }
    assert journal.record_grib(record, voy["clock"], now) is True
    assert journal.record_grib(record, voy["clock"], now) is False  # same cycle
    assert journal.record_grib({"status": "pending"}, voy["clock"], now) is False
    g = journal.latest(5, kinds=["grib"])[0]
    assert g["windKnots"] == 14.2 and g["hs"] == 1.1 and g["basis"] == "forecast"
    assert g["cycle"] == "2026-05-18T06:00:00Z"


def test_public_reads_and_admin_note(client, monkeypatch):
    now = T0 + timedelta(days=1)
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())

    r = client.get("/voyage/official/journal", headers=PUBLIC)
    assert r.status_code == 200
    body = r.json()
    assert body["voyageId"] == OFFICIAL_VOYAGE_ID
    assert body["count"] >= 4
    assert body["latest"][0]["t"] >= body["latest"][-1]["t"]  # newest first
    assert body["days"][0]["day"] == "2026-05-15"

    day = client.get(f"/voyage/official/journal/{body['days'][0]['day']}", headers=PUBLIC)
    assert day.status_code == 200 and day.json()["entries"]
    assert client.get("/voyage/official/journal/2030-01-01", headers=PUBLIC).status_code == 404
    assert client.get("/voyage/official/journal/pas-un-jour", headers=PUBLIC).status_code == 400

    # Note : écriture humaine, admin seulement (503 sans secret derrière nginx).
    assert client.post("/voyage/official/journal/note", json={"text": "Départ !"}, headers=PUBLIC).status_code == 503
    monkeypatch.setenv(admin_guard.ADMIN_ENV, "s")
    assert client.post("/voyage/official/journal/note", json={"text": "Départ !"}, headers=PUBLIC).status_code == 401
    ok = client.post(
        "/voyage/official/journal/note",
        json={"text": "  Largué les amarres,   vent de NO.  ", "author": "Clément"},
        headers={**PUBLIC, admin_guard.ADMIN_HEADER: "s"},
    )
    assert ok.status_code == 200
    assert ok.json()["text"] == "Largué les amarres, vent de NO."
    assert ok.json()["author"] == "Clément"
    bad = client.post("/voyage/official/journal/note", json={"text": "   "}, headers={**PUBLIC, admin_guard.ADMIN_HEADER: "s"})
    assert bad.status_code == 400
    latest = client.get("/voyage/official/journal?limit=3", headers=PUBLIC).json()["latest"]
    assert latest[0]["kind"] == "note"


def test_tick_is_throttled_for_public_reads(client, monkeypatch):
    now = T0 + timedelta(days=1)
    _freeze(monkeypatch, now)
    client.put("/voyage/official", json=_official())
    voy = voyage_store.load_voyage(OFFICIAL_VOYAGE_ID)
    journal.reset()
    assert journal.tick(voy, now)["skipped"] is False
    assert journal.tick(voy, now)["skipped"] is True
    assert journal.tick(voy, now, force=True)["skipped"] is False
    assert journal.tick(None, now)["skipped"] is True

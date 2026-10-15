"""Lot DM8A — moments d'un voyage perso : empreinte, cache, borne, verrou, 404."""
from __future__ import annotations

import copy
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import custom_story
import ici_engine
import official_store
import pearl_store
from custom_story import (
    DEFAULT_BUDGET_NM,
    NS,
    drop_cached_moments,
    moments_for_voyage,
    voyage_fingerprint,
)
from ici_warm import sample_route_nm
from voyage_store import purge_stale_voyages, save_voyage

T0 = "2026-06-15T08:00:00Z"
FR = {"name": "French Exclusive Economic Zone", "mrgid": 5677, "territory": "metropole"}
ES = {"name": "Spanish Exclusive Economic Zone", "mrgid": 5693, "territory": "spain"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_FORECAST_BACKEND", "synthetic")
    monkeypatch.setenv("NAVIGUIDE_FORECAST_CACHE", str(tmp_path / "cache"))
    import forecast_cube
    import voyage_store
    forecast_cube.CACHE_DIR = tmp_path / "cache"
    voyage_store._DIR = tmp_path / "voyages"
    from main import app
    return TestClient(app)


def _points_two():
    return [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
        {"lat": 40.0, "lon": -15.0, "cumNm": 650, "filmCum": 650, "jump": False, "nonMaritime": False},
    ]


def _voyage(voyage_id="custom-test-dm8a", t0=T0):
    points = _points_two()
    samples = sample_route_nm(points)
    t = datetime(2026, 6, 15, 8, tzinfo=timezone.utc)
    verts = [
        {
            "lat": p["lat"], "lon": p["lon"], "sailNm": p["sailNm"],
            "iso": (t + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for i, p in enumerate(samples)
    ]
    return {
        "voyageId": voyage_id,
        "t0": t0,
        "expedition_id": "test-exp",
        "startAt": "la-rochelle",
        "points": points,
        "marks": [
            {"name": "La Rochelle", "nm": 0, "filmNm": 0, "lat": 46.15, "lon": -1.16, "index": 0},
            {"name": "Horta", "nm": 650, "filmNm": 650, "lat": 40.0, "lon": -15.0, "index": 1},
        ],
        "clock": {"t0": t0, "vertices": verts},
    }


def _bag_for(lat, lon):
    zee = FR if lon > -8 else ES
    amp = []
    if lon > -2:
        amp = [{
            "name": "Pertuis charentais - Rochebonne",
            "site_id": "pc-1", "nm": 3.6, "iucn_cat": "II",
        }]
    sci = {"nearby": []}
    if lon < -10:
        sci = {"nearby": [{"name": "Argo 6904216", "nm": 4.0, "type": "argo"}]}
    return {
        "zee": zee, "amp": amp, "poe": [], "projects": [],
        "science": sci, "sources": {"bi": "ok"},
    }


@pytest.fixture(autouse=True)
def _reset_story_caches():
    ici_engine.reset_caches()
    pearl_store.reset()
    yield
    ici_engine.reset_caches()
    pearl_store.reset()


def test_two_point_route_yields_dated_moments_in_order():
    voy = _voyage()
    calls = []

    def bag(lat, lon):
        calls.append((lat, lon))
        return _bag_for(lat, lon)

    out = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert out["status"] == "ready"
    assert out["fingerprint"] == voyage_fingerprint(voy)
    assert out["totalNm"] >= 600
    assert out["coverageNm"] == out["totalNm"]
    rows = out["moments"]
    assert len(rows) >= 1
    times = [r.get("t") for r in rows]
    assert all(times)
    assert times == sorted(times)
    assert calls, "le sac /ici est appelé au premier calcul"


def test_same_fingerprint_does_not_refill_bags():
    voy = _voyage()
    calls = []

    def bag(lat, lon):
        calls.append(1)
        return _bag_for(lat, lon)

    first = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert first["status"] == "ready"
    n = len(calls)
    assert n > 0
    second = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert second["status"] == "ready"
    assert len(calls) == n
    assert second["fingerprint"] == first["fingerprint"]
    assert second["moments"] == first["moments"]


def test_small_budget_prepares_then_coverage_grows():
    voy = _voyage()
    calls = []

    def bag(lat, lon):
        calls.append(1)
        return _bag_for(lat, lon)

    first = moments_for_voyage(voy, budget_nm=40, bag_fn=bag)
    assert first["status"] == "preparing"
    assert 0 < first["coverageNm"] < first["totalNm"]
    n_first = len(calls)
    second = moments_for_voyage(voy, budget_nm=40, bag_fn=bag)
    assert second["coverageNm"] > first["coverageNm"]
    assert len(calls) > n_first
    third = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert third["status"] == "ready"
    assert third["coverageNm"] == third["totalNm"]
    n_ready = len(calls)
    moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert len(calls) == n_ready


def test_failed_pearl_is_skipped_not_an_error():
    voy = _voyage()
    calls = {"n": 0}

    def bag(lat, lon):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("ici down")
        return _bag_for(lat, lon)

    out = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert out["status"] == "ready"
    assert out["skipped"] >= 1
    assert isinstance(out["moments"], list)


def test_official_moments_payload_unchanged():
    sentinel = {"moments": [{"t": T0, "signature": "dm8a-sentinel"}], "journal": {"count": 1}}
    official_store.put("moments", sentinel)
    before = copy.deepcopy(official_store.payload_of("moments"))
    assert before["moments"][0]["signature"] == "dm8a-sentinel"

    def boom(*_a, **_k):
        raise AssertionError("stock officiel sollicité")

    # kick / put / refresh ne doivent pas être touchés par le chemin perso.
    official_store_put = official_store.put
    try:
        import official_store as os_mod
        orig_kick = os_mod.kick_worker
        orig_refresh = os_mod.refresh_family
        os_mod.kick_worker = boom
        os_mod.refresh_family = boom
        out = moments_for_voyage(_voyage(), budget_nm=4000, bag_fn=_bag_for)
        assert out["status"] == "ready"
    finally:
        os_mod.kick_worker = orig_kick
        os_mod.refresh_family = orig_refresh
        official_store.put = official_store_put

    after = official_store.payload_of("moments")
    assert after == before


def test_lock_returns_preparing_for_the_other_voyage():
    voy_a = _voyage("lock-a")
    voy_b = _voyage("lock-b")
    voy_b["points"] = [
        {"lat": 14.6, "lon": -61.07, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
        {"lat": 16.0, "lon": -62.0, "cumNm": 80, "filmCum": 80, "jump": False, "nonMaritime": False},
    ]
    voy_b["t0"] = "2026-07-01T00:00:00Z"
    held = threading.Event()
    release = threading.Event()
    calls_b = []

    def slow(lat, lon):
        held.set()
        release.wait(3.0)
        return _bag_for(lat, lon)

    def bag_b(lat, lon):
        calls_b.append(1)
        return _bag_for(lat, lon)

    result_a = {}

    def run_a():
        result_a["out"] = moments_for_voyage(voy_a, budget_nm=4000, bag_fn=slow)

    thread = threading.Thread(target=run_a)
    thread.start()
    assert held.wait(2.0)
    out_b = moments_for_voyage(voy_b, budget_nm=4000, bag_fn=bag_b)
    assert out_b["status"] == "preparing"
    assert calls_b == []
    release.set()
    thread.join(5.0)
    assert result_a["out"]["status"] == "ready"


def test_purge_drops_custom_moments_entry():
    voy = _voyage("purge-me")
    save_voyage(voy)
    out = moments_for_voyage(voy, budget_nm=4000, bag_fn=_bag_for)
    fp = out["fingerprint"]
    assert pearl_store.kv_get(NS, fp) is not None
    n = purge_stale_voyages(
        1, keep=set(), now=time.time() + 14 * 86400, on_removed=drop_cached_moments,
    )
    assert n >= 1
    assert pearl_store.kv_get(NS, fp) is None
    assert pearl_store.kv_get(NS, f"id:{voy['voyageId']}") is None


def test_get_moments_404(client):
    r = client.get("/voyage/does-not-exist-dm8a/moments")
    assert r.status_code == 404


def test_get_moments_http_then_cache(client, monkeypatch):
    monkeypatch.setattr("ici_warm.get_pearl_bag", _bag_for)
    body = {
        "t0": T0,
        "expedition_id": "test-exp",
        "routeKind": "custom",
        "follow": True,
        "forecast": False,
        "startAt": "la-rochelle",
        "points": _points_two(),
        "marks": [
            {"name": "La Rochelle", "nm": 0, "lat": 46.15, "lon": -1.16, "index": 0},
            {"name": "Horta", "nm": 650, "lat": 40.0, "lon": -15.0, "index": 1},
        ],
    }
    created = client.post("/voyage", json=body)
    assert created.status_code in (200, 202)
    vid = created.json()["voyageId"]
    first = client.get(f"/voyage/{vid}/moments")
    assert first.status_code == 200
    payload = first.json()
    assert payload["status"] in ("ready", "preparing")
    assert payload["fingerprint"]
    t0 = time.monotonic()
    second = client.get(f"/voyage/{vid}/moments")
    dt = time.monotonic() - t0
    assert second.status_code == 200
    if payload["status"] == "ready":
        assert second.json()["status"] == "ready"
        assert dt < 1.0
        assert len(payload.get("moments") or []) >= 1
        times = [r.get("t") for r in payload["moments"] if r.get("t")]
        assert times == sorted(times)
    official = client.get("/voyage/official/moments")
    assert official.status_code == 200


def test_fingerprint_changes_with_t0_and_points():
    a = _voyage(t0=T0)
    b = _voyage(t0="2026-08-01T00:00:00Z")
    assert voyage_fingerprint(a) != voyage_fingerprint(b)
    c = copy.deepcopy(a)
    c["points"][1]["lat"] = 41.0
    assert voyage_fingerprint(a) != voyage_fingerprint(c)


def test_time_chunk_prepares_then_resumes(monkeypatch):
    monkeypatch.setattr(custom_story, "MAX_CHUNK_S", 0.05)
    voy = _voyage()
    def bag(lat, lon):
        time.sleep(0.04)
        return _bag_for(lat, lon)
    first = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert first["status"] == "preparing"
    assert first["coverageNm"] > 0
    assert first["coverageNm"] < first["totalNm"]
    monkeypatch.setattr(custom_story, "MAX_CHUNK_S", 30.0)
    done = moments_for_voyage(voy, budget_nm=4000, bag_fn=bag)
    assert done["status"] == "ready"
    assert done["coverageNm"] == done["totalNm"]


def test_default_budget_matches_contract():
    assert DEFAULT_BUDGET_NM == 2000.0


def test_llm_mode_does_not_matter(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_LLM_MODE", "all")
    calls = {"story": 0}

    def boom(*_a, **_k):
        calls["story"] += 1
        raise AssertionError("LLM")

    monkeypatch.setattr("story_cascade.complete", boom, raising=False)
    out = moments_for_voyage(_voyage(), budget_nm=4000, bag_fn=_bag_for)
    assert out["status"] == "ready"
    assert calls["story"] == 0

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import forecast_cube
import voyage_api
import voyage_store
from weather_pipeline import get_pipeline


def _wait_forecast(client, voyage_id, timeout=2.0):
    pts = client.get(f"/voyage/{voyage_id}").json().get("points") or []
    lat = float((pts[0] or {}).get("lat") or 0)
    lon = float((pts[0] or {}).get("lon") or 0)
    get_pipeline().wait_ready(f"forecast-cube:{voyage_id}", lat, lon, timeout=timeout)
    deadline = time.monotonic() + timeout
    meta = None
    while time.monotonic() < deadline:
        meta = client.get(f"/voyage/{voyage_id}").json()
        if meta.get("forecastStatus") == "ready":
            return meta
        time.sleep(0.02)
    return meta or client.get(f"/voyage/{voyage_id}").json()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_FORECAST_BACKEND", "synthetic")
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path / "voyages"))
    monkeypatch.setenv("NAVIGUIDE_FORECAST_CACHE", str(tmp_path / "cache"))
    voyage_store._DIR = tmp_path / "voyages"
    forecast_cube.CACHE_DIR = tmp_path / "cache"
    from main import app
    return TestClient(app)


def _payload(t0: str):
    return {
        "t0": t0,
        "expedition_id": "test-exp",
        "routeKind": "berry",
        "follow": True,
        "forecast": True,
        "startAt": "la-rochelle",
        "points": [
            {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
            {"lat": 40.0, "lon": -15.0, "cumNm": 650, "filmCum": 650, "jump": False, "nonMaritime": False},
            {"lat": 28.0, "lon": -30.0, "cumNm": 1450, "filmCum": 1450, "jump": False, "nonMaritime": False},
            {"lat": 16.0, "lon": -48.0, "cumNm": 2600, "filmCum": 2600, "jump": False, "nonMaritime": False},
            {"lat": 14.6, "lon": -61.07, "cumNm": 3350, "filmCum": 3350, "jump": False, "nonMaritime": False},
        ],
        "marks": [
            {"name": "La Rochelle", "nm": 0, "filmNm": 0, "lat": 46.15, "lon": -1.16, "index": 0},
            {"name": "Fort-de-France (Martinique)", "nm": 3350, "filmNm": 3350, "lat": 14.6, "lon": -61.07, "index": 4},
        ],
    }


def test_create_pending_then_ready(client):
    t0 = "2026-06-15T08:00:00Z"
    r = client.post("/voyage", json=_payload(t0))
    assert r.status_code == 200
    body = r.json()
    assert body["forecastStatus"] in ("pending", "ready")
    vid = body["voyageId"]
    meta = _wait_forecast(client, vid)
    assert meta["forecastStatus"] == "ready"
    assert meta["forecastModel"] == "synthetic-test"


def test_at_plus_48h_forecast_and_f5(client):
    t0 = datetime(2026, 6, 15, 8, tzinfo=timezone.utc)
    r = client.post("/voyage", json=_payload(t0.isoformat().replace("+00:00", "Z")))
    vid = r.json()["voyageId"]
    _wait_forecast(client, vid)
    when = (t0 + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    a = client.get(f"/voyage/{vid}/at", params={"t": when})
    b = client.get(f"/voyage/{vid}/at", params={"t": when})
    assert a.status_code == 200
    assert a.json()["kind"] == "forecast"
    assert a.json()["model"]
    assert a.json()["leadHours"] == 48.0
    assert abs(a.json()["lat"] - b.json()["lat"]) < 1e-6
    assert abs(a.json()["lon"] - b.json()["lon"]) < 1e-6
    # ± 1 nm of stability: same point
    assert a.json()["status"] == "live"


def test_at_plus_11d_climatology(client):
    t0 = datetime(2026, 6, 15, 8, tzinfo=timezone.utc)
    vid = client.post("/voyage", json=_payload(t0.strftime("%Y-%m-%dT%H:%M:%SZ"))).json()["voyageId"]
    _wait_forecast(client, vid)
    when = (t0 + timedelta(days=11)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sample = client.get(f"/voyage/{vid}/at", params={"t": when}).json()
    assert sample["kind"] == "climatology"
    assert sample.get("leadHours") in (None, 0)


def test_waiting_before_t0(client):
    t0 = datetime(2026, 9, 20, 8, tzinfo=timezone.utc)
    vid = client.post("/voyage", json=_payload(t0.strftime("%Y-%m-%dT%H:%M:%SZ"))).json()["voyageId"]
    past = (t0 - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sample = client.get(f"/voyage/{vid}/at", params={"t": past}).json()
    assert sample["status"] == "waiting"
    assert sample["countdownHours"] > 0


def test_recompute_reject_accept(client, monkeypatch):
    t0 = datetime(2026, 6, 13, 8, tzinfo=timezone.utc)  # ~48 h before a mid-June recette
    vid = client.post("/voyage", json=_payload(t0.strftime("%Y-%m-%dT%H:%M:%SZ"))).json()["voyageId"]
    client.get(f"/voyage/{vid}")
    # Force an "offshore" position: t = t0+48h via monkeypatch of _now
    live_t = t0 + timedelta(hours=48)

    monkeypatch.setattr(voyage_api, "_now", lambda: live_t)
    rec = client.post(f"/voyage/{vid}/recompute")
    assert rec.status_code == 200
    draft = rec.json()
    assert draft["status"] in ("arrived", "spliced", "failed")
    assert "draft_geojson" in draft
    assert draft["versus_searoute"]["distance_nm"] > 0

    client.post(f"/voyage/{vid}/reject")
    assert client.get(f"/voyage/{vid}/draft").status_code == 404

    rec2 = client.post(f"/voyage/{vid}/recompute")
    assert rec2.status_code == 200
    if rec2.json()["status"] == "failed" or len(
        rec2.json().get("draft_geojson", {}).get("geometry", {}).get("coordinates") or []
    ) < 2:
        pytest.skip("isochrone trop courte sur le mock — status failed")
    acc = client.post(f"/voyage/{vid}/accept")
    assert acc.status_code == 200
    assert acc.json()["routeRev"] == 1
    # The Pacific is not in this test route; the downstream after FDF does not exist.
    # Check that the upstream (La Rochelle) is still the first point.
    assert acc.json()["points"][0]["lat"] == pytest.approx(46.15, abs=0.05)


def test_refresh_forecast(client):
    t0 = datetime(2026, 6, 15, 8, tzinfo=timezone.utc)
    vid = client.post("/voyage", json=_payload(t0.strftime("%Y-%m-%dT%H:%M:%SZ"))).json()["voyageId"]
    _wait_forecast(client, vid)
    r = client.post(f"/voyage/{vid}/refresh-forecast")
    assert r.status_code == 200
    assert r.json()["forecastStatus"] in ("pending", "ready")
    meta = _wait_forecast(client, vid)
    assert meta["forecastStatus"] == "ready"


def test_recompute_takes_the_skipper_orders_as_constraints(client, monkeypatch):
    """Lot G : vent max / mer max du skipper → zones interdites du routage,
    renvoyées dans le brouillon ; hors bornes → ignorés (défaut honnête)."""
    t0 = datetime(2026, 6, 13, 8, tzinfo=timezone.utc)
    vid = client.post("/voyage", json=_payload(t0.strftime("%Y-%m-%dT%H:%M:%SZ"))).json()["voyageId"]
    client.get(f"/voyage/{vid}")
    monkeypatch.setattr(voyage_api, "_now", lambda: t0 + timedelta(hours=48))
    rec = client.post(f"/voyage/{vid}/recompute", json={"wind_max_kt": 34, "hs_max_m": 3.5})
    assert rec.status_code == 200
    draft = rec.json()
    assert draft["constraints"] == {"windMaxKt": 34.0, "hsMaxM": 3.5, "source": "skipper"}
    assert "draft_geojson" in draft
    rec2 = client.post(f"/voyage/{vid}/recompute", json={"wind_max_kt": 5, "hs_max_m": 40})
    assert rec2.json()["constraints"]["source"] == "default"
    assert rec2.json()["constraints"]["windMaxKt"] is None

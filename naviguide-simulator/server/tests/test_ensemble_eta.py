"""Lot C6 — ETA p10/p50/p90, faux serveur HTTP Ensemble, cache 6 h."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx
import pytest

from hindcast import bind_http, block_network, reset_hooks, unblock_network
from pearl_store import kv_get

import ensemble_eta
from ensemble_eta import (
    CACHE_NS,
    CACHE_TTL_S,
    ENSEMBLE_MODELS,
    FORECAST_DAYS,
    arrival_quantiles,
    compute_eta,
    empty_eta,
    empirical_quantile,
    fetch_point_members,
    parse_members,
    sample_leg_points,
)

NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
LAT, LON = 46.15, -1.16

C4_POLAR = {
    "twa_rows": [40, 60, 90, 120, 150, 180],
    "tws_cols": [8, 12, 16, 20],
    "matrix": [
        [5.0, 6.5, 7.5, 8.0],
        [6.0, 7.5, 8.5, 9.0],
        [7.0, 8.5, 9.5, 10.0],
        [6.5, 8.0, 9.0, 10.0],
        [5.5, 7.0, 8.0, 9.0],
        [4.5, 6.0, 7.0, 8.0],
    ],
}


@pytest.fixture(autouse=True)
def _hooks():
    reset_hooks()
    saved_url = ensemble_eta.ENSEMBLE_URL
    yield
    ensemble_eta.ENSEMBLE_URL = saved_url
    reset_hooks()
    unblock_network()


def _hours(n: int = 48) -> list[str]:
    return [(NOW + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n)]


def _ensemble_json(times: list[str], speeds: list[float], direction: float = 0.0) -> dict:
    hourly = {"time": times}
    for i, kn in enumerate(speeds, start=1):
        hourly[f"wind_speed_10m_member{i:02d}"] = [kn] * len(times)
        hourly[f"wind_direction_10m_member{i:02d}"] = [direction] * len(times)
    return {"hourly": hourly}


class _EnsembleHandler(BaseHTTPRequestHandler):
    payload = {"hourly": {"time": []}}
    hits = 0
    fail = False

    def do_GET(self):  # noqa: N802
        type(self).hits += 1
        if self.fail:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"down")
            return
        body = json.dumps(self.payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_a):
        return


def _start_server(payload: dict, *, fail: bool = False):
    _EnsembleHandler.payload = payload
    _EnsembleHandler.hits = 0
    _EnsembleHandler.fail = fail
    server = ThreadingHTTPServer(("127.0.0.1", 0), _EnsembleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _bind_server(server: ThreadingHTTPServer):
    host, port = server.server_address
    origin = f"http://{host}:{port}"

    def factory():
        return httpx.Client(timeout=5.0)

    bind_http(factory)
    ensemble_eta.ENSEMBLE_URL = origin + "/v1/ensemble"
    return origin


def _leg():
    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
        {"lat": 46.15, "lon": -2.16, "cumNm": 30, "filmCum": 30, "jump": False, "nonMaritime": False},
    ]
    marks = [{"name": "Fort-de-France (Martinique)", "nm": 30, "filmNm": 30, "lat": 46.15, "lon": -2.16, "index": 1}]
    sample = {"lat": 46.15, "lon": -1.16, "sailNm": 0, "filmNm": 0}
    return points, marks, sample


def test_quantiles_identical_and_dispersed():
    t0 = NOW
    same = [t0 + timedelta(hours=48)] * 30
    p10, p50, p90 = arrival_quantiles(same)
    assert p10 == p50 == p90
    assert p10 == same[0]
    spread = [t0 + timedelta(hours=h) for h in (20, 24, 28, 32, 36, 40, 48, 56, 64, 72)]
    a, b, c = arrival_quantiles(spread)
    assert a < b < c
    assert empirical_quantile([1.0, 1.0, 1.0], 0.1) == 1.0


def test_parse_members_control_and_prefixed():
    times = _hours(3)
    payload = {
        "hourly": {
            "time": times,
            "wind_speed_10m": [10.0, 10.0, 10.0],
            "wind_direction_10m": [0.0, 0.0, 0.0],
            "gfs_seamless_wind_speed_10m_member01": [12.0, 12.0, 12.0],
            "gfs_seamless_wind_direction_10m_member01": [90.0, 90.0, 90.0],
        }
    }
    members = parse_members(payload)
    assert "control" in members
    assert any(k.endswith("member01") for k in members)
    assert members["control"][0]["speedKnots"] == 10.0


def test_thirty_identical_members_p10_eq_p90():
    times = _hours(72)
    payload = _ensemble_json(times, [12.0] * 30, direction=0.0)
    server = _start_server(payload)
    try:
        _bind_server(server)
        points, marks, sample = _leg()
        out = compute_eta(
            points=points, marks=marks, stop="Fort-de-France",
            now=NOW, polar_raw=C4_POLAR, sample=sample,
        )
        assert out["members"] == 30
        assert out["p10"] and out["p50"] and out["p90"]
        assert out["p10"] == out["p50"] == out["p90"]
        assert out["source"] == "open-meteo-ensemble"
    finally:
        server.shutdown()


def test_dispersed_members_p10_lt_p50_lt_p90():
    times = _hours(96)
    speeds = [8.0] * 10 + [12.0] * 10 + [20.0] * 10
    payload = _ensemble_json(times, speeds, direction=0.0)
    server = _start_server(payload)
    try:
        _bind_server(server)
        points, marks, sample = _leg()
        out = compute_eta(
            points=points, marks=marks, stop="Fort-de-France",
            now=NOW, polar_raw=C4_POLAR, sample=sample,
        )
        assert out["members"] == 30
        assert out["p10"] < out["p50"] < out["p90"]
    finally:
        server.shutdown()


def test_api_down_members_zero():
    server = _start_server({"hourly": {"time": []}}, fail=True)
    try:
        _bind_server(server)
        points, marks, sample = _leg()
        out = compute_eta(
            points=points, marks=marks, stop="Fort-de-France",
            now=NOW, polar_raw=C4_POLAR, sample=sample,
        )
        assert out["members"] == 0
        assert out["p10"] is None and out["p50"] is None and out["p90"] is None
        assert out["source"] is None
        assert empty_eta(NOW)["members"] == 0
    finally:
        server.shutdown()


def test_cache_six_hours_second_call_without_network():
    times = _hours(24)
    payload = _ensemble_json(times, [12.0] * 5, direction=0.0)
    server = _start_server(payload)
    try:
        _bind_server(server)
        first = fetch_point_members(LAT, LON)
        assert first
        hits = _EnsembleHandler.hits
        assert hits >= 1
        block_network()
        second = fetch_point_members(LAT, LON)
        assert len(second) == len(first)
        assert _EnsembleHandler.hits == hits
        assert CACHE_TTL_S == 6 * 3600
        hit = kv_get(CACHE_NS, ensemble_eta._cache_key(LAT, LON), max_age_s=CACHE_TTL_S)
        assert hit and hit["value"]["members"]
    finally:
        unblock_network()
        server.shutdown()


def test_sample_leg_points_step_at_most_60nm():
    points = [
        {"lat": 0.0, "lon": 0.0, "cumNm": 0},
        {"lat": 0.0, "lon": 0.1, "cumNm": 20},
        {"lat": 0.0, "lon": 2.0, "cumNm": 140},
        {"lat": 0.0, "lon": 2.1, "cumNm": 150},
    ]
    sampled = sample_leg_points(points, 60.0)
    assert sampled[0]["cumNm"] == 0
    assert sampled[-1]["cumNm"] == 150
    gaps = [sampled[i + 1]["cumNm"] - sampled[i]["cumNm"] for i in range(len(sampled) - 1)]
    assert all(g <= 60.0 + 1e-6 for g in gaps)
    assert ENSEMBLE_MODELS == "gfs_seamless,ecmwf_ifs025"
    assert FORECAST_DAYS == 15

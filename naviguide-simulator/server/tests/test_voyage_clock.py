"""B0 — contrat JSON table A = table serveur + tests mars / juillet."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from climatology_zones import zone_wind_at
from voyage_clock import (
    AIR_CALENDAR_HOURS,
    build_voyage_clock,
    find_start_index,
    sample_clock_at_hours,
    sample_clock_at_time,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "clock_golden_route.json"
GOLDEN = json.loads(FIXTURE.read_text(encoding="utf-8"))

VERTEX_KEYS = {
    "filmNm", "sailNm", "lat", "lon", "bearing", "tHours", "iso",
    "speedKnots", "windKnots", "twa", "month", "vehicle", "kind", "seaHours",
}
TABLE_KEYS = {"t0", "kind", "vertices", "marks", "seaHours", "quayHours", "arrivalIso"}


def _clock(t0: str, **extra):
    return build_voyage_clock(
        GOLDEN["points"],
        GOLDEN["marks"],
        t0,
        polar_raw=None,
        start_at="la-rochelle",
        **extra,
    )


def test_schema_golden():
    c = _clock("2026-06-15T08:00:00Z")
    assert TABLE_KEYS <= set(c)
    assert c["kind"] == "climatology"
    v = c["vertices"][-1]
    assert VERTEX_KEYS <= set(v)
    assert c["vertices"][0]["tHours"] == 0
    hours = [x["tHours"] for x in c["vertices"]]
    assert hours == sorted(hours)


def test_june_fdf_after_t0():
    c = _clock("2026-06-15T08:00:00Z")
    fdf = next(m for m in c["marks"] if "Fort-de-France" in m["name"])
    assert datetime.fromisoformat(fdf["iso"].replace("Z", "+00:00")) > datetime(
        2026, 6, 15, 8, tzinfo=timezone.utc
    )


def test_march_vs_july_fdf():
    mar = _clock("2026-03-15T08:00:00Z")
    jul = _clock("2026-07-15T08:00:00Z")
    a = next(m for m in mar["marks"] if "Fort-de-France" in m["name"])
    b = next(m for m in jul["marks"] if "Fort-de-France" in m["name"])
    da = datetime.fromisoformat(a["iso"].replace("Z", "+00:00"))
    db = datetime.fromisoformat(b["iso"].replace("Z", "+00:00"))
    assert abs((da - db).total_seconds()) > 24 * 3600


def test_quay_48h_same_filmn():
    c = _clock("2026-06-15T08:00:00Z")
    fdf = next(m for m in c["marks"] if "Fort-de-France" in m["name"])
    assert fdf["holdHours"] == 48
    same = [v for v in c["vertices"] if abs(v["filmNm"] - fdf["filmNm"]) < 1e-6]
    assert len(same) >= 2
    assert same[-1]["tHours"] - same[0]["tHours"] >= 47.9


def test_air_hop():
    points = [
        {"lat": 4.9, "lon": -52.3, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 44.6, "lon": -63.6, "cumNm": 0, "filmCum": 80, "jump": True},
    ]
    c = build_voyage_clock(points, [], "2026-06-15T08:00:00Z", start_at="saint-maur")
    assert c["vertices"][-1]["tHours"] == AIR_CALENDAR_HOURS
    assert c["vertices"][-1]["speedKnots"] is None
    assert c["vertices"][-1]["vehicle"] == "plane"


def test_no_polar_climatology():
    c = _clock("2026-06-15T08:00:00Z")
    assert any(v["kind"] == "climatology" and (v["speedKnots"] or 0) > 0 for v in c["vertices"])


def test_antimeridian_monotone():
    points = [
        {"lat": -20, "lon": 170, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": -20, "lon": 176, "cumNm": 300, "filmCum": 300, "jump": False},
        {"lat": -20, "lon": -178, "cumNm": 600, "filmCum": 600, "jump": False},
        {"lat": -20, "lon": -170, "cumNm": 900, "filmCum": 900, "jump": False},
    ]
    c = build_voyage_clock(points, [], "2026-06-15T08:00:00Z", start_at="saint-maur")
    hours = [v["tHours"] for v in c["vertices"]]
    assert hours == sorted(hours)


def test_start_saint_maur_land_dt():
    points = [
        {"lat": 46.8, "lon": 1.63, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": True},
        {"lat": 46.15, "lon": -1.16, "cumNm": 200, "filmCum": 200, "jump": False, "nonMaritime": True},
        {"lat": 45.0, "lon": -5.0, "cumNm": 400, "filmCum": 400, "jump": False, "nonMaritime": False},
    ]
    marks = [{"name": "La Rochelle", "nm": 200, "filmNm": 200, "index": 1}]
    assert find_start_index(points, marks, "saint-maur") == 0
    c = build_voyage_clock(points, marks, "2026-06-15T08:00:00Z", start_at="saint-maur")
    at_lr = next(v for v in c["vertices"] if abs(v["sailNm"] - 200) < 1e-6 and v["vehicle"] != "quay")
    assert at_lr["tHours"] == 4


def test_sample_waiting_and_live():
    c = _clock("2026-06-15T08:00:00Z")
    waiting = sample_clock_at_time(c, "2026-06-14T08:00:00Z")
    assert waiting["status"] == "waiting"
    live = sample_clock_at_hours(c, 12)
    assert live["status"] == "live"
    assert live["iso"] == "2026-06-15T20:00:00Z"


def test_js_py_same_schema_keys():
    """Le golden partagé impose les mêmes clés des deux côtés."""
    c = _clock(GOLDEN["t0"])
    assert TABLE_KEYS <= set(c)
    assert VERTEX_KEYS <= set(c["vertices"][0])
    # La Rochelle juin : vent de zone ≠ 0
    z = zone_wind_at(46.15, -1.16, 6)
    assert z["kind"] == "climatology"
    assert z["speedKnots"] > 0

"""B0 — contrat JSON table A = table serveur + tests mars / juillet."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from climatology_zones import zone_wind_at
from voyage_clock import (
    AIR_CALENDAR_HOURS,
    DEFAULT_BMAP_PORT_DAYS,
    OFFICIAL_T0,
    OFFICIAL_VOYAGE_ID,
    PLANNING_MIN_KN,
    build_voyage_clock,
    find_start_index,
    planning_speed_for,
    polar_boat_speed,
    polar_efficiency,
    port_days_for,
    sample_clock_at_hours,
    sample_clock_at_time,
    sog_along_route,
    wave_polar_factor,
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


def test_official_t0_and_bmap_3_days():
    assert OFFICIAL_T0.startswith("2026-05-15")
    assert OFFICIAL_VOYAGE_ID == "berry-mappemonde-2026-officiel"
    assert DEFAULT_BMAP_PORT_DAYS == 3
    assert port_days_for("Ajaccio") == 3
    assert port_days_for("Cayenne") == 3
    assert port_days_for("Papeete") == 3
    assert port_days_for("Halifax") == 1


def test_quay_72h_same_filmn():
    c = _clock("2026-06-15T08:00:00Z")
    fdf = next(m for m in c["marks"] if "Fort-de-France" in m["name"])
    assert fdf["holdHours"] == 72
    same = [v for v in c["vertices"] if abs(v["filmNm"] - fdf["filmNm"]) < 1e-6]
    assert len(same) >= 2
    assert same[-1]["tHours"] - same[0]["tHours"] >= 71.9


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


def test_atlas_wind_fn_keeps_kind_and_hs():
    def wind_fn(lat, lon, t):
        return {
            "speedKnots": 22.0,
            "dirFromDeg": 80.0,
            "kind": "climatology",
            "source": "atlas",
            "period": "1980-2020",
            "doi": {"wind": "10.48670/moi-00183"},
            "hsP50": 1.2,
            "hsP90": 2.6,
            "currentKn": 0.3,
        }

    c = _clock("2026-06-15T08:00:00Z", wind_fn=wind_fn)
    sea = next(v for v in c["vertices"] if (v.get("speedKnots") or 0) > 0)
    assert sea["kind"] == "climatology"
    assert sea["source"] == "atlas"
    assert sea["hsP90"] == 2.6
    assert sea["period"] == "1980-2020"


def test_sample_at_quay_speed_zero():
    c = _clock("2026-06-15T08:00:00Z")
    fdf = next(m for m in c["marks"] if "Fort-de-France" in m["name"])
    s = sample_clock_at_hours(c, float(fdf["tHours"]) + 1)
    assert s["atQuay"] is True
    assert s["speedKnots"] == 0
    assert s["vehicle"] == "quay"


def test_c2_steps_cap_30nm_or_1h_and_mid_step_wind():
    calls = []

    def wind_fn(lat, lon, t):
        calls.append((lat, lon, t))
        return {"speedKnots": 20.0, "dirFromDeg": 0.0, "kind": "hindcast", "regime": "hindcast", "sources": ["om-era5"], "spread": 1.0}

    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 46.15, "lon": -3.5, "cumNm": 90, "filmCum": 90, "jump": False},
    ]
    t0 = datetime(2026, 5, 15, 8, tzinfo=timezone.utc)
    c = build_voyage_clock(points, [], t0, start_at="saint-maur", wind_fn=wind_fn)
    sea = [v for v in c["vertices"] if v.get("vehicle") == "main" and (v.get("speedKnots") or 0) > 0]
    assert len(sea) >= 2
    for a, b in zip(sea, sea[1:]):
        assert (b["sailNm"] - a["sailNm"]) <= 30.0 + 1e-6
        assert (b["tHours"] - a["tHours"]) <= 1.0 + 1e-6
    assert sea[0]["regime"] == "hindcast"
    assert sea[0]["sources"] == ["om-era5"]
    assert calls, "vent lu à mi-pas"


def test_c2_regime_flips_at_now():
    now = datetime(2026, 5, 17, 8, tzinfo=timezone.utc)

    def wind_fn(lat, lon, t):
        if t < now:
            return {"speedKnots": 14.0, "dirFromDeg": 80.0, "kind": "hindcast", "regime": "hindcast", "sources": ["om-forecast"], "spread": 0.5}
        return {"speedKnots": 16.0, "dirFromDeg": 90.0, "kind": "forecast", "regime": "forecast"}

    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 40.0, "lon": -15.0, "cumNm": 650, "filmCum": 650, "jump": False},
    ]
    c = build_voyage_clock(points, [], "2026-05-15T08:00:00Z", start_at="saint-maur", wind_fn=wind_fn)
    before = sample_clock_at_time(c, now - timedelta(hours=2))
    after = sample_clock_at_time(c, now + timedelta(hours=2))
    assert before["regime"] == "hindcast"
    assert after["regime"] == "forecast"


def test_js_py_same_schema_keys():
    """Le golden partagé impose les mêmes clés des deux côtés."""
    c = _clock(GOLDEN["t0"])
    assert TABLE_KEYS <= set(c)
    assert VERTEX_KEYS <= set(c["vertices"][0])
    # La Rochelle juin : vent de zone ≠ 0
    z = zone_wind_at(46.15, -1.16, 6)
    assert z["kind"] == "climatology"
    assert z["speedKnots"] > 0


# ── Lot C4 — courant, vagues, efficacité, climatologie ────────────────────────

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

# Même table que skipperOrders.test.js (parité JS/Python).
C4_PLANNING_POLAR = {
    "twa_rows": [60, 90, 120, 150],
    "tws_cols": [6, 10, 14, 20],
    "matrix": [[4, 6, 7, 8], [5, 7, 8.5, 10], [4.5, 6.5, 8, 10], [3.5, 5, 7, 9]],
}


def _c4_leg(wind):
    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 46.15, "lon": -2.16, "cumNm": 30, "filmCum": 30, "jump": False},
    ]
    return build_voyage_clock(
        points, [], "2026-06-15T08:00:00Z",
        polar_raw=C4_POLAR, start_at="saint-maur",
        wind_fn=lambda lat, lon, t: dict(wind),
    )


def test_c4_current_along_and_against():
    polar = polar_boat_speed(C4_POLAR, 90, 16)
    assert polar == 9.5
    assert abs(polar_efficiency() - 0.85) < 1e-9
    expected = polar * 0.85 + 2.0
    along = {"speedKnots": 16.0, "dirFromDeg": 0.0, "kind": "hindcast",
             "currentKn": 2.0, "currentToDeg": 270.0, "hs": 1.0}
    # cap 270° (ouest) : lon diminue, courant vers l'ouest = dans l'axe
    c = _c4_leg(along)
    sea = next(v for v in c["vertices"] if (v.get("speedKnots") or 0) > 0)
    assert abs(sea["speedKnots"] - expected) < 0.15
    against = {**along, "currentToDeg": 90.0}
    c2 = _c4_leg(against)
    sea2 = next(v for v in c2["vertices"] if (v.get("speedKnots") or 0) > 0)
    assert abs(sea2["speedKnots"] - (polar * 0.85 - 2.0)) < 0.15
    # uo/vo : 2 kn vers l'ouest = uo < 0
    uo = -2.0 / 1.943844
    vec = sog_along_route(polar * 0.85, {"uo": uo, "vo": 0.0}, 270.0)
    assert abs(vec - expected) < 1e-3


def test_c4_wave_polar_continuous_and_head_worse_than_follow():
    f24 = wave_polar_factor(2.4, 0.0)
    f26 = wave_polar_factor(2.6, 0.0)
    assert abs(f26 - f24) < 0.08
    assert f24 > f26
    assert wave_polar_factor(1.5, 0.0) == 1.0
    assert abs(wave_polar_factor(4.0, 0.0) - 0.6) < 1e-9
    assert abs(wave_polar_factor(4.0, 180.0) - 0.85) < 1e-9
    assert wave_polar_factor(5.0, 0.0) == wave_polar_factor(4.0, 0.0)
    head = wave_polar_factor(3.0, 0.0)
    follow = wave_polar_factor(3.0, 180.0)
    assert head < follow
    # L'horloge : mer de face plus lente que mer arrière, même Hs.
    base = {"speedKnots": 16.0, "dirFromDeg": 0.0, "kind": "hindcast", "hs": 3.0}
    face = _c4_leg({**base, "waveFromDeg": 270.0})
    back = _c4_leg({**base, "waveFromDeg": 90.0})
    sf = next(v for v in face["vertices"] if (v.get("speedKnots") or 0) > 0)["speedKnots"]
    sb = next(v for v in back["vertices"] if (v.get("speedKnots") or 0) > 0)["speedKnots"]
    assert sf < sb


def test_c4_climatology_jensen_mean_of_times():
    """Temps aux p25/p50/p75 moyenné ≥ temps à la moyenne (inégalité de Jensen)."""
    mean_kn = 12.0
    draws = [6.0, 12.0, 20.0]
    heading = 90.0
    wind_from = 0.0  # TWA 90°
    speeds = []
    for kn in draws:
        twa = 90.0
        stw = polar_boat_speed(C4_POLAR, twa, kn) * polar_efficiency()
        speeds.append(max(0.5, stw))
    t_avg = sum(1.0 / s for s in speeds) / 3.0
    t_mean = 1.0 / (polar_boat_speed(C4_POLAR, 90.0, mean_kn) * polar_efficiency())
    assert t_avg >= t_mean - 1e-9
    rose = {
        "speedKnots": mean_kn, "dirFromDeg": wind_from, "kind": "climatology",
        "roseKnots": draws, "hs": 1.0,
    }
    mean_only = {
        "speedKnots": mean_kn, "dirFromDeg": wind_from, "kind": "climatology", "hs": 1.0,
    }
    c_rose = _c4_leg(rose)
    c_mean = _c4_leg(mean_only)
    assert c_rose["seaHours"] >= c_mean["seaHours"] - 1e-6


def test_c4_planning_speed_parity_with_js():
    assert abs(polar_efficiency() - 0.85) < 1e-9
    assert planning_speed_for(C4_PLANNING_POLAR, 10, 90) == 6.0
    assert planning_speed_for(C4_PLANNING_POLAR, 20, 150) == 7.7
    assert planning_speed_for(C4_PLANNING_POLAR, 0, 90) == PLANNING_MIN_KN

"""Lot C2 — hindcast multi-sources, médiane, cache, conventions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from climatology_zones import boat_speed_from_wind
from forecast_blend import blended_wind
from hindcast import (
    ERA5_PRODUCTS,
    ERA5_STRONG_WIND_FACTOR,
    MS_TO_KN,
    apply_era5_correction,
    at,
    bind_cmems,
    bind_http,
    block_network,
    fill_era5_along,
    past_passage_slots,
    reset_hooks,
    series,
    uncovered_era5_slots,
    uv_to_current_to,
)
from pearl_store import kv_count
from voyage_clock import build_voyage_clock, parse_iso, sample_clock_at_time, sog_along_route, to_iso

T0 = datetime(2026, 5, 15, 8, tzinfo=timezone.utc)
DAY0 = "2026-05-15"
DAY1 = "2026-05-16"
LAT, LON = 46.15, -1.16


@pytest.fixture(autouse=True)
def _hooks():
    reset_hooks()
    yield
    reset_hooks()


def _dates(start: str, end: str) -> list[str]:
    d = datetime.fromisoformat(start).date()
    last = datetime.fromisoformat(end).date()
    out = []
    while d <= last:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _hours(start: str, end: str) -> list[str]:
    times = []
    for day in _dates(start, end):
        times.extend(f"{day}T{h:02d}:00" for h in range(24))
    return times


def _om_json(times: list[str], *, speed: float, marine: bool = False, era5_hours: dict | None = None) -> dict:
    n = len(times)
    if marine:
        return {"hourly": {
            "time": times,
            "wave_height": [1.2] * n,
            "wave_direction": [240.0] * n,
            "wave_period": [8.0] * n,
            "ocean_current_velocity": [0.2] * n,
            "ocean_current_direction": [90.0] * n,
        }}
    speeds = []
    for iso in times:
        if era5_hours and iso[11:13] in era5_hours:
            speeds.append(era5_hours[iso[11:13]])
        else:
            speeds.append(speed)
    return {"hourly": {
        "time": times,
        "wind_speed_10m": speeds,
        "wind_direction_10m": [0.0] * n,
        "wind_gusts_10m": [s + 3 for s in speeds],
    }}


def bind_om(*, forecast_kn=20.0, era5_kn=20.0, marine_ok=True, era5_hours=None, fail_hosts=()):
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if any(h in host for h in fail_hosts):
            return httpx.Response(503, text="down")
        params = dict(request.url.params)
        start = params.get("start_date")
        end = params.get("end_date") or start
        times = _hours(start, end)
        if "marine-api" in host:
            if not marine_ok:
                return httpx.Response(400, text="unknown current vars")
            return httpx.Response(200, json=_om_json(times, speed=0, marine=True))
        if "archive-api" in host:
            return httpx.Response(200, json=_om_json(times, speed=era5_kn, era5_hours=era5_hours))
        return httpx.Response(200, json=_om_json(times, speed=forecast_kn))

    bind_http(lambda: httpx.Client(transport=httpx.MockTransport(handler)))


def _cmems_rows(start, end, **fields):
    t = start if getattr(start, "tzinfo", None) else start.replace(tzinfo=timezone.utc)
    e = end if getattr(end, "tzinfo", None) else end.replace(tzinfo=timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    rows = []
    cur = t
    while cur <= e:
        rows.append({"t": to_iso(cur), **fields})
        cur += timedelta(hours=1)
    return rows


def bind_ok_cmems(*, wind_kn=20.0, fail_wind=False):
    def wind(_la, _lo, start, end):
        if fail_wind:
            raise RuntimeError("cmems-wind down")
        return _cmems_rows(start, end, speedKnots=wind_kn, dirFromDeg=0.0)

    def wave(_la, _lo, start, end):
        return _cmems_rows(start, end, hs=1.5, waveDirFromDeg=240.0, wavePeriodS=8.0)

    def phy(_la, _lo, start, end):
        return _cmems_rows(start, end, currentKn=0.4, currentToDeg=90.0)

    bind_cmems(wind=wind, wave=wave, phy=phy)


def test_median_of_three_wind_sources():
    bind_om(forecast_kn=8.0, era5_kn=10.0)
    bind_ok_cmems(wind_kn=12.0)
    packed = series(LAT, LON, DAY0)
    hour = next(h for h in packed["hours"] if h["t"].startswith(f"{DAY0}T12"))
    assert hour["speedKnots"] == 10.0
    assert set(hour["byVar"]["speedKnots"]["sources"]) == {"om-forecast", "om-era5", "cmems-wind"}
    assert hour["spread"] == 4.0
    assert hour["regime"] == "hindcast"


def test_one_source_down_spread_from_two():
    bind_om(forecast_kn=8.0, era5_kn=12.0)
    bind_ok_cmems(fail_wind=True)
    hour = next(h for h in series(LAT, LON, DAY0)["hours"] if h["t"].startswith(f"{DAY0}T06"))
    assert hour["speedKnots"] == 10.0
    assert hour["spread"] == 4.0
    assert "cmems-wind" not in hour["sources"]
    assert "om-forecast" in hour["sources"] and "om-era5" in hour["sources"]


def test_cache_second_call_without_network():
    bind_om()
    bind_ok_cmems()
    first = series(LAT, LON, DAY0)
    assert first["hours"]
    block_network()
    second = series(LAT, LON, DAY0)
    assert len(second["hours"]) == len(first["hours"])
    assert second["hours"][0]["speedKnots"] == first["hours"][0]["speedKnots"]


def test_all_sources_down_empty_then_climatology():
    bind_http(lambda: httpx.Client(transport=httpx.MockTransport(
        lambda _r: httpx.Response(503, text="down")
    )))
    bind_cmems(
        wind=lambda *_a: (_ for _ in ()).throw(RuntimeError("down")),
        wave=lambda *_a: (_ for _ in ()).throw(RuntimeError("down")),
        phy=lambda *_a: (_ for _ in ()).throw(RuntimeError("down")),
    )
    packed = series(LAT, LON, DAY0)
    assert packed["hours"] == []
    empty = at(LAT, LON, T0)
    assert empty["speedKnots"] is None
    assert empty["sources"] == []
    climo = blended_wind(
        LAT, LON, T0 - timedelta(hours=2), T0, None,
        atlas_network=False, now=T0, hindcast_fn=lambda *_a: empty,
    )
    assert climo["kind"] == "climatology"
    assert climo["regime"] == "climatology"
    assert climo.get("reason") == "hindcast_empty"


def test_era5_correction_only_above_15ms_and_only_era5():
    strong_kn = 16.0 * MS_TO_KN
    weak_kn = 10.0 * MS_TO_KN
    bind_om(forecast_kn=strong_kn, era5_kn=strong_kn, era5_hours={"12": weak_kn})
    bind_ok_cmems(wind_kn=strong_kn)
    packed = series(LAT, LON, DAY0)
    strong = next(h for h in packed["hours"] if h["t"].startswith(f"{DAY0}T00"))
    weak = next(h for h in packed["hours"] if h["t"].startswith(f"{DAY0}T12"))
    era5_strong = strong["bySource"]["om-era5"]["speedKnots"]
    fc_strong = strong["bySource"]["om-forecast"]["speedKnots"]
    era5_weak = weak["bySource"]["om-era5"]["speedKnots"]
    assert abs(fc_strong - strong_kn) < 1e-6
    assert abs(era5_strong - apply_era5_correction(strong_kn)) < 1e-6
    assert era5_strong > strong_kn
    assert abs(era5_weak - weak_kn) < 1e-6
    assert abs(apply_era5_correction(weak_kn) - weak_kn) < 1e-6
    assert ERA5_STRONG_WIND_FACTOR == 1.05


def test_uo_east_vo_zero_current_to_90():
    kn, to_deg = uv_to_current_to(1.0, 0.0)
    assert abs(kn - MS_TO_KN) < 1e-6
    assert to_deg == 90.0


def test_two_days_known_wind_position_within_1nm():
    bind_om(forecast_kn=20.0, era5_kn=20.0)
    bind_ok_cmems(wind_kn=20.0)
    t0 = T0
    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 46.15, "lon": -13.5, "cumNm": 500, "filmCum": 500, "jump": False},
    ]

    def wind_fn(lat, lon, t):
        return at(lat, lon, t)

    clock = build_voyage_clock(points, [], t0, polar_raw=None, start_at="saint-maur", wind_fn=wind_fn)
    sample = sample_clock_at_time(clock, t0 + timedelta(hours=48))
    expected_kn = boat_speed_from_wind(20.0)
    assert expected_kn == 9.0
    pack = at(LAT, LON, t0)
    # Lot C4 : le courant du hindcast est projeté sur la route (cap 270°).
    sog = max(0.5, sog_along_route(expected_kn, pack, 270.0))
    assert sample is not None
    assert abs(sample["sailNm"] - sog * 48.0) <= 1.0
    assert sample["regime"] == "hindcast"


def test_quay_speed_zero_keeps_hindcast_regime():
    bind_om()
    bind_ok_cmems()
    t0 = T0
    points = [
        {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": 46.0, "lon": -3.0, "cumNm": 80, "filmCum": 80, "jump": False},
    ]
    marks = [{"name": "Fort-de-France (Martinique)", "nm": 80, "filmNm": 80, "index": 1}]
    clock = build_voyage_clock(points, marks, t0, start_at="saint-maur", wind_fn=lambda la, lo, t: at(la, lo, t))
    mark = clock["marks"][0]
    sample = sample_clock_at_time(clock, parse_iso(mark["iso"]) + timedelta(hours=1))
    assert sample["atQuay"] is True
    assert sample["speedKnots"] == 0
    assert sample["regime"] == "hindcast"


def test_wx_from_hindcast_uses_duration_and_max():
    from voyage_journal import latest, record_wx_from_hindcast

    clock = {
        "t0": to_iso(T0),
        "vertices": [
            {"iso": "2026-05-16T00:00:00Z", "regime": "hindcast", "windKnots": 36.0, "hs": 2.0, "lat": 46.1, "lon": -1.2},
            {"iso": "2026-05-16T06:00:00Z", "regime": "hindcast", "windKnots": 41.0, "hs": 2.1, "lat": 46.0, "lon": -1.4},
        ],
    }
    assert record_wx_from_hindcast(clock, T0 + timedelta(days=3)) == 1
    assert record_wx_from_hindcast(clock, T0 + timedelta(days=3)) == 0
    wx = latest(5, kinds=("wx",))[0]
    assert wx["basis"] == "hindcast"
    assert wx["maxWindKnots"] == 41.0
    assert wx["hours"] >= 6.0


# ── Lot RA8 — ERA5 le long de la route, sans Copernicus ───────────────────────

RA8_POLAR = {
    "twa_rows": [40, 60, 90, 120, 150, 180],
    "tws_cols": [8, 12, 16, 20, 24],
    "matrix": [
        [5.0, 6.5, 7.5, 8.0, 8.2],
        [6.0, 7.5, 8.5, 9.0, 9.2],
        [7.0, 8.5, 9.5, 10.0, 10.4],
        [6.5, 8.0, 9.0, 10.0, 10.2],
        [5.5, 7.0, 8.0, 9.0, 9.2],
        [4.5, 6.0, 7.0, 8.0, 8.2],
    ],
}

# Point hors des fixtures C2 pour ne pas réutiliser un blend Copernicus.
RA8_LAT, RA8_LON = 12.345, -23.456


def test_cmems_skipped_without_credentials(monkeypatch):
    monkeypatch.delenv("COPERNICUS_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUS_PASSWORD", raising=False)
    bind_om(era5_kn=14.0, forecast_kn=14.0)
    packed = series(RA8_LAT, RA8_LON, DAY0)
    assert "om-era5" in packed["products"]
    assert "cmems-wind" not in packed["products"]
    assert "cmems-wave" not in packed["products"]
    assert "cmems-phy" not in packed["products"]
    hour = next(h for h in packed["hours"] if h["t"].startswith(f"{DAY0}T08"))
    assert hour["regime"] == "hindcast"
    assert hour["speedKnots"] == 14.0
    assert "om-era5" in hour["sources"]


def test_era5_fill_raises_store_without_copernicus(monkeypatch):
    monkeypatch.delenv("COPERNICUS_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUS_PASSWORD", raising=False)
    bind_om(era5_kn=22.0)
    before = kv_count("hindcast")
    n = fill_era5_along([(RA8_LAT, RA8_LON, DAY0)])
    assert n >= 1
    assert kv_count("hindcast") > before
    hour = at(RA8_LAT, RA8_LON, T0, products=ERA5_PRODUCTS)
    assert hour["speedKnots"] == 22.0
    assert hour["regime"] == "hindcast"
    assert hour["sources"] == ["om-era5"]


def test_past_vertex_speed_from_era5_not_climatology(monkeypatch):
    """Sommet daté dans le passé : régime hindcast, vitesse = ERA5 × polaire."""
    monkeypatch.delenv("COPERNICUS_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUS_PASSWORD", raising=False)
    era5_kn = 24.0
    bind_om(era5_kn=era5_kn, forecast_kn=era5_kn)
    t0 = T0
    now = t0 + timedelta(hours=36)
    points = [
        {"lat": RA8_LAT, "lon": RA8_LON, "cumNm": 0, "filmCum": 0, "jump": False},
        {"lat": RA8_LAT, "lon": RA8_LON - 1.0, "cumNm": 30, "filmCum": 30, "jump": False},
    ]
    climo = build_voyage_clock(points, [], t0, polar_raw=RA8_POLAR, start_at="saint-maur")
    climo_sea = next(v for v in climo["vertices"] if (v.get("speedKnots") or 0) > 0)

    n = fill_era5_along([(RA8_LAT, RA8_LON, DAY0), (RA8_LAT, RA8_LON - 1.0, DAY0)])
    assert n >= 1

    def wind_fn(lat, lon, t):
        return blended_wind(
            lat, lon, t, t0, None,
            atlas_network=False, now=now,
            hindcast_fn=lambda la, lo, tt: at(la, lo, tt, products=ERA5_PRODUCTS),
        )

    clock = build_voyage_clock(
        points, [], t0, polar_raw=RA8_POLAR, start_at="saint-maur", wind_fn=wind_fn,
    )
    past = next(
        v for v in clock["vertices"]
        if parse_iso(v["iso"]) < now and (v.get("speedKnots") or 0) > 0
    )
    assert past["regime"] == "hindcast"
    assert past["sources"] == ["om-era5"]
    assert past["windKnots"] == era5_kn
    assert past["speedKnots"] != climo_sea["speedKnots"]
    from voyage_clock import polar_boat_speed, polar_efficiency
    stw = polar_boat_speed(RA8_POLAR, past["twa"], era5_kn) * polar_efficiency()
    assert abs(past["speedKnots"] - stw) < 0.3


def test_uncovered_slots_after_date_shift():
    lat, lon = 1.111, -2.222
    now = T0 + timedelta(days=3)
    clock = {
        "vertices": [
            {"lat": lat, "lon": lon, "iso": "2026-05-15T12:00:00Z", "vehicle": "main"},
            {"lat": lat, "lon": lon, "iso": "2026-05-20T12:00:00Z", "vehicle": "main"},
            {"lat": lat, "lon": lon, "iso": "2026-05-16T08:00:00Z", "vehicle": "plane"},
        ],
    }
    slots = past_passage_slots(clock, now)
    assert (lat, lon, DAY0) in slots
    assert (lat, lon, "2026-05-20") not in slots
    assert all(s[2] != "2026-05-16" for s in slots)
    missing = uncovered_era5_slots(clock, now)
    assert (lat, lon, DAY0) in missing

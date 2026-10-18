"""Parité : drapeau éteint (ancien chemin) et drapeau allumé servent les mêmes valeurs."""
from weather_pipeline import get_async_weather_queue, get_pipeline, route_snapshot

WAVE_OPENMETEO = {
    "kind": "forecast",
    "source": "openmeteo-gfs-wave",
    "hs": 1.1,
    "dirDeg": 270.0,
    "periodS": 6.5,
    "time": "2026-09-16T09:00",
}

WAVE_COPERNICUS = {
    "latitude": 46.15,
    "longitude": -1.16,
    "significant_wave_height_m": 2.4,
    "mean_wave_period": 8.5,
    "mean_wave_direction": 310.0,
    "source": "copernicus-marine",
}


def _serve(monkeypatch, flag, provider, fixture, lat=46.15, lon=-1.16):
    monkeypatch.setenv("NAVIGUIDE_WEATHER_PIPELINE", flag)
    get_pipeline().clear()
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return dict(fixture)

    body = route_snapshot(provider, lat, lon, loader)
    if body.get("status") != "ready":
        get_pipeline().wait_ready(provider, lat, lon, timeout=2)
        body = route_snapshot(provider, lat, lon, loader)
    assert body["status"] == "ready", body
    for key, value in fixture.items():
        assert body[key] == value
    assert calls["n"] == 1
    return {key: body[key] for key in fixture}


def test_openmeteo_wave_parity(monkeypatch):
    off = _serve(monkeypatch, "0", "openmeteo-gfs-wave", WAVE_OPENMETEO)
    on = _serve(monkeypatch, "1", "openmeteo-gfs-wave", WAVE_OPENMETEO)
    assert off == on == WAVE_OPENMETEO
    assert get_async_weather_queue().cached_status("openmeteo-gfs-wave", 46.15, -1.16) == "ready"


def test_copernicus_wave_parity(monkeypatch):
    off = _serve(monkeypatch, "0", "wave", WAVE_COPERNICUS)
    on = _serve(monkeypatch, "1", "wave", WAVE_COPERNICUS)
    assert off == on == WAVE_COPERNICUS
    assert get_async_weather_queue().cached_status("wave", 46.15, -1.16) == "ready"

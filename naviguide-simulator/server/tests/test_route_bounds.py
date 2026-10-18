"""Bornes et terre franche de GET /route. Searoute est simulé."""
from fastapi.testclient import TestClient

import main
from route_engine import endpoint_on_land


def test_start_lat_out_of_range_is_422():
    client = TestClient(main.app)
    response = client.get("/route", params={
        "start_lat": 999,
        "start_lon": -1.15,
        "end_lat": 43.5,
        "end_lon": -5.6,
    })
    assert response.status_code == 422


def test_longitude_out_of_range_is_422():
    client = TestClient(main.app)
    response = client.get("/route", params={
        "start_lat": 46.15,
        "start_lon": 181,
        "end_lat": 43.5,
        "end_lon": -5.6,
    })
    assert response.status_code == 422
    south = client.get("/route", params={
        "start_lat": -91,
        "start_lon": -1,
        "end_lat": 0,
        "end_lon": -1,
    })
    assert south.status_code == 422


def test_inland_endpoint_is_422_on_land(monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("searoute ne doit pas partir pour un point sur terre")

    monkeypatch.setattr(main, "searoute_with_exact_end", boom)
    client = TestClient(main.app)
    response = client.get("/route", params={
        "start_lat": 48.8566,
        "start_lon": 2.3522,
        "end_lat": 46.2,
        "end_lon": -1.7,
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "on_land"


def test_coastal_ports_are_not_inland():
    assert endpoint_on_land(48.8566, 2.3522) is True
    for lat, lon in ((46.157, -1.151), (43.545, -5.662), (38.722, -9.139)):
        assert endpoint_on_land(lat, lon) is False, (lat, lon)


def test_same_point_at_sea_does_not_call_searoute(monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("probe même point")

    monkeypatch.setattr(main, "searoute_with_exact_end", boom)
    client = TestClient(main.app)
    response = client.get("/route", params={
        "start_lat": 46.2,
        "start_lon": -2.4,
        "end_lat": 46.2,
        "end_lon": -2.4,
    })
    assert response.status_code == 200
    coords = response.json()["geometry"]["coordinates"]
    assert len(coords) == 2


def test_searoute_timeout_then_one_offshore_retry(monkeypatch):
    import time

    import route_engine

    monkeypatch.setattr(route_engine, "SEAROUTE_TIMEOUT_S", 0.05)
    calls = []

    def slow_then_ok(start, end):
        calls.append((start, end))
        if len(calls) == 1:
            time.sleep(0.35)
            return None
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[start[0], start[1]], [end[0], end[1]]],
            },
            "properties": {"length": 8, "units": "km"},
        }

    monkeypatch.setattr(route_engine.sr, "searoute", slow_then_ok)
    start, end = (-1.7, 46.25), (-2.1, 46.05)
    route = route_engine.searoute_with_exact_end(start, end)
    assert route is not None
    assert len(calls) == 2
    assert calls[1] != calls[0]
    route_engine._route_cache.pop(route_engine._route_cache_key(start, end), None)

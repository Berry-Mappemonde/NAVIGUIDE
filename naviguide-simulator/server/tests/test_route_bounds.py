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
    # Une longitude dépliée est repliée (voir plus bas) ; au-delà de ±540°, refus.
    client = TestClient(main.app)
    response = client.get("/route", params={
        "start_lat": 46.15,
        "start_lon": 541,
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


def test_searoute_timeout_is_a_single_attempt(monkeypatch):
    """Un échec ou un délai dépassé ne relance pas searoute (plus de nouvel essai au large)."""
    import route_engine

    calls = []

    def timed_out(start, end, timeout_s=None):
        calls.append((start, end))
        return None

    monkeypatch.setattr(route_engine, "_invoke_searoute", timed_out)
    start, end = (-1.7, 46.25), (-2.1, 46.05)
    route_engine._route_cache.pop(route_engine._route_cache_key(start, end), None)
    route = route_engine.searoute_with_exact_end(start, end)
    assert route is None
    assert len(calls) == 1
    assert calls[0] == (start, end)


def test_searoute_deadline_is_about_8_s():
    import route_engine

    assert 6.0 <= route_engine.SEAROUTE_TIMEOUT_S <= 10.0


def test_timed_out_call_leaves_no_work_running():
    """À l'échéance, le process qui calculait est tué : rien ne continue derrière."""
    import time

    from searoute_worker import TIMED_OUT, ProcessRunner

    runner = ProcessRunner()
    try:
        assert runner.run("math:hypot", (3, 4), 30) == 5.0
        t0 = time.monotonic()
        assert runner.run("time:sleep", (30,), 0.5) is TIMED_OUT
        assert time.monotonic() - t0 < 5
        assert not runner.last_worker.proc.is_alive()
        assert runner.run("math:hypot", (6, 8), 30) == 10.0
    finally:
        runner.shutdown()


def test_searoute_runs_through_the_process_runner(monkeypatch):
    import route_engine
    import searoute_worker

    seen = []

    def fake_run(target, args, timeout_s):
        seen.append((target, args, timeout_s))
        return searoute_worker.TIMED_OUT

    monkeypatch.setattr(searoute_worker.RUNNER, "run", fake_run)
    assert route_engine._invoke_searoute((-1.7, 46.25), (-2.1, 46.05)) is None
    assert seen == [("searoute:searoute", ([-1.7, 46.25], [-2.1, 46.05]), route_engine.SEAROUTE_TIMEOUT_S)]


def test_unfolded_longitude_is_wrapped_not_refused(monkeypatch):
    seen = []

    def fake_route(start, end):
        seen.append((start, end))
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[start[0], start[1]], [end[0], end[1]]]},
            "properties": {"length": 1, "units": "km"},
        }

    monkeypatch.setattr(main, "searoute_with_exact_end", fake_route)
    client = TestClient(main.app)
    for lon, wrapped in ((236.84, -123.16), (181.0, -179.0), (-200.0, 160.0)):
        response = client.get("/route", params={
            "start_lat": 37.0,
            "start_lon": lon,
            "end_lat": 36.0,
            "end_lon": lon - 1,
        })
        assert response.status_code == 200, (lon, response.text)
        start, end = seen[-1]
        assert abs(start[0] - wrapped) < 1e-6
        assert -180.0 <= end[0] <= 180.0
        # La géométrie revient dans le repère déplié de l'appelant.
        assert abs(response.json()["geometry"]["coordinates"][0][0] - lon) < 1e-6


def test_non_finite_or_absurd_longitude_is_422():
    client = TestClient(main.app)
    for bad in ("nan", "inf", "-inf", "540.5", "-541"):
        response = client.get("/route", params={
            "start_lat": 37.0,
            "start_lon": bad,
            "end_lat": 36.0,
            "end_lon": -123.0,
        })
        assert response.status_code == 422, bad


def test_end_longitude_beyond_540_is_422_and_540_is_accepted(monkeypatch):
    seen = []

    def fake_route(start, end):
        seen.append((start, end))
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[start[0], start[1]], [end[0], end[1]]]},
            "properties": {"length": 1, "units": "km"},
        }

    monkeypatch.setattr(main, "searoute_with_exact_end", fake_route)
    monkeypatch.setattr(main, "endpoint_on_land", lambda *_a, **_k: False)
    client = TestClient(main.app)
    for bad in (540.01, 541, -540.5, 900):
        response = client.get("/route", params={
            "start_lat": 0.0, "start_lon": 170.0, "end_lat": 1.0, "end_lon": bad,
        })
        assert response.status_code == 422, bad
    assert seen == []
    for edge in (540, -540):
        response = client.get("/route", params={
            "start_lat": 0.0, "start_lon": 170.0, "end_lat": 1.0, "end_lon": edge,
        })
        assert response.status_code == 200, (edge, response.text)
        _start, end = seen[-1]
        assert -180.0 <= end[0] <= 180.0
        assert abs(abs(end[0]) - 180.0) < 1e-6
    response = client.get("/route", params={
        "start_lat": 0.0, "start_lon": 540, "end_lat": 1.0, "end_lon": 179.0,
    })
    assert response.status_code == 200, response.text


def test_runner_caps_concurrent_searoute_processes():
    import threading
    import time as _time

    import searoute_worker

    assert searoute_worker.MAX_BUSY == 4
    runner = searoute_worker.ProcessRunner(max_busy=1)
    try:
        results = {}

        def slow():
            results["slow"] = runner.run("time:sleep", (1.5,), 20.0)

        t = threading.Thread(target=slow)
        t.start()
        _time.sleep(0.3)
        t0 = _time.monotonic()
        # The only slot is busy: this call waits its deadline, then gives up
        # without starting a second process.
        assert runner.run("time:sleep", (0,), 0.3) is searoute_worker.TIMED_OUT
        assert _time.monotonic() - t0 < 1.0
        t.join(30)
        assert results["slow"] is None
        # Slot free again: the next call runs.
        assert runner.run("time:sleep", (0,), 20.0) is None
    finally:
        runner.shutdown()

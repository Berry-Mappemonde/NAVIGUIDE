import threading
from datetime import datetime, timedelta, timezone

from saildocs import last_ready_cycle, to_iso
from weather_pipeline import WeatherPipeline, cache_key, forecast_cycle, weather_cell


def test_bind_ignores_async_client_transport():
    from weather_pipeline import bind_weather_transport, weather_http_transport

    class FakeAsyncTransport:
        pass

    bind_weather_transport(FakeAsyncTransport())
    assert weather_http_transport() is None


def test_same_quarter_degree_shares_a_cell():
    assert weather_cell(10.01, 20.01) == weather_cell(10.12, 20.12)
    assert weather_cell(10.01, 20.01) != weather_cell(10.30, 20.30)


def test_cache_key_includes_provider_and_cycle():
    when = datetime(2026, 9, 16, 15, tzinfo=timezone.utc)
    a = cache_key("wind", 10.01, 20.01, when)
    b = cache_key("wave", 10.01, 20.01, when)
    later = cache_key("wind", 10.01, 20.01, when + timedelta(hours=12))
    assert a[0] == "wind"
    assert a[1:] == b[1:]
    assert a[0] != b[0]
    assert a[3] == forecast_cycle(when)
    assert later[3] != a[3]


def test_snapshot_is_immediate_and_deduplicates_loader():
    pipe = WeatherPipeline()
    calls = []
    started = threading.Event()
    release = threading.Event()

    def loader():
        started.set()
        release.wait(1)
        calls.append(1)
        return {"ok": True, "n": len(calls)}

    first = pipe.snapshot("wind", 10.01, 20.01, loader)
    second = pipe.snapshot("wind", 10.12, 20.12, loader)
    assert first["status"] == "pending"
    assert first["refreshing"] is True
    assert second["status"] == "pending"
    assert started.wait(1)
    release.set()
    ready = pipe.wait_ready("wind", 10.01, 20.01, timeout=2)
    cached = pipe.snapshot("wind", 10.12, 20.12, loader)
    assert ready["status"] == "ready"
    assert ready["ok"] is True
    assert cached["status"] == "ready"
    assert cached["n"] == 1
    assert calls == [1]


def test_new_cycle_keeps_stale_ready_and_refreshes():
    pipe = WeatherPipeline()
    early = datetime(2026, 9, 16, 8, tzinfo=timezone.utc)
    late = datetime(2026, 9, 16, 20, tzinfo=timezone.utc)
    assert to_iso(last_ready_cycle(early)) != to_iso(last_ready_cycle(late))

    pipe.snapshot("wind", 46.15, -1.16, lambda: {"wind_speed_knots": 8}, when=early)
    first = pipe.wait_ready("wind", 46.15, -1.16, when=early, timeout=2)
    assert first["status"] == "ready"
    assert first["wind_speed_knots"] == 8

    started = threading.Event()
    release = threading.Event()

    def next_loader():
        started.set()
        release.wait(1)
        return {"wind_speed_knots": 14}

    stale = pipe.snapshot("wind", 46.15, -1.16, next_loader, when=late)
    assert stale["status"] == "ready"
    assert stale["refreshing"] is True
    assert stale["wind_speed_knots"] == 8
    assert stale["cycle"] == to_iso(last_ready_cycle(early))
    assert started.wait(1)
    release.set()
    fresh = pipe.wait_ready("wind", 46.15, -1.16, when=late, timeout=2)
    assert fresh["status"] == "ready"
    assert fresh["wind_speed_knots"] == 14
    assert fresh["cycle"] == to_iso(last_ready_cycle(late))


def test_kick_does_not_start_a_second_thread():
    pipe = WeatherPipeline()
    release = threading.Event()

    def loader():
        release.wait(1)
        return {"ok": True}

    assert pipe.kick("official-grib", 46.15, -1.16, loader) is True
    assert pipe.kick("official-grib", 46.15, -1.16, loader) is False
    assert pipe.provider_busy("official-grib") is True
    release.set()
    pipe.wait_ready("official-grib", 46.15, -1.16, timeout=2)
    assert pipe.provider_busy("official-grib") is False


def test_error_is_durable_until_forced():
    pipe = WeatherPipeline()

    def boom():
        raise RuntimeError("down")

    pipe.snapshot("wind", 1.0, 2.0, boom)
    err = pipe.wait_ready("wind", 1.0, 2.0, timeout=2)
    assert err["status"] == "error"
    again = pipe.snapshot("wind", 1.0, 2.0, boom)
    assert again["status"] == "error"
    assert again["refreshing"] is False
    assert pipe.kick("wind", 1.0, 2.0, boom) is False


def test_snapshot_group_pending_until_every_product_ready():
    pipe = WeatherPipeline()
    release = threading.Event()

    def load(kind):
        def _load():
            release.wait(1)
            return {"source": kind}
        return _load

    body = pipe.snapshot_group(
        (
            ("wind", "wind", load("wind")),
            ("wave", "wave", load("wave")),
        ),
        10.0,
        20.0,
    )
    assert body["status"] == "pending"
    assert body["wind"]["status"] == "pending"
    release.set()
    pipe.wait_providers(["wind", "wave"], 10.0, 20.0, timeout=2)
    ready = pipe.snapshot_group(
        (
            ("wind", "wind", load("wind")),
            ("wave", "wave", load("wave")),
        ),
        10.0,
        20.0,
    )
    assert ready["status"] == "ready"
    assert ready["wind"]["source"] == "wind"
    assert ready["wave"]["source"] == "wave"

from fastapi.testclient import TestClient

import main


def _weather(kind, calls):
    def load(request):
        calls[kind] += 1
        return {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "source": kind,
        }
    return load


def test_weather_composite_reuses_cell_cache(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_GRIB_AUTO", "0")
    main._weather_cache.clear()
    calls = {"wind": 0, "wave": 0, "current": 0}
    monkeypatch.setattr(main, "_load_wind", _weather("wind", calls))
    monkeypatch.setattr(main, "_load_wave", _weather("wave", calls))
    monkeypatch.setattr(main, "_load_current", _weather("current", calls))
    client = TestClient(main.app)

    first = client.post("/weather", json={"latitude": 10.01, "longitude": 20.01})
    second = client.post("/weather", json={"latitude": 10.12, "longitude": 20.12})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["wind"]["source"] == "wind"
    assert calls == {"wind": 1, "wave": 1, "current": 1}


def test_ports_are_filtered_by_requested_bbox(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_GRIB_AUTO", "0")
    async def ports():
        return [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [2, 48]}, "properties": {"name": "Brest"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-61, 14]}, "properties": {"name": "Fort-de-France"}},
        ]

    monkeypatch.setattr(main, "fetch_wpi_features", ports)
    response = TestClient(main.app).get("/proxy/ports", params={"bbox": "-5,40,10,55"})

    assert response.status_code == 200
    assert [feature["properties"]["name"] for feature in response.json()["features"]] == ["Brest"]
    assert "max-age=180" in response.headers["cache-control"]


def test_wms_proxy_sets_browser_cache_headers(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_GRIB_AUTO", "0")
    class Response:
        status_code = 200
        content = b"png"

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(main.httpx, "AsyncClient", Client)
    response = TestClient(main.app).get("/proxy/zee/wms", params={"bbox": "-1,40,1,42"})

    assert response.status_code == 200
    assert "max-age=21600" in response.headers["cache-control"]

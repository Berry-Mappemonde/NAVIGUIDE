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
    main._catalog_cache.clear()
    main._catalog_tasks.clear()
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


def test_catalog_proxy_indexes_source_and_returns_only_requested_view(monkeypatch):
    main._catalog_cache.clear()
    main._catalog_tasks.clear()
    calls = []

    async def catalog_features(catalog):
        calls.append(catalog)
        return [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [2, 48]},
                "properties": {"source": "argo", "name": "Argo Brest"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-61, 14]},
                "properties": {"source": "argo", "name": "Argo Martinique"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [2.1, 48.1]},
                "properties": {"source": "sextant", "name": "Sextant Brest"},
            },
        ]

    monkeypatch.setattr(main, "_fetch_catalog_features", catalog_features)
    client = TestClient(main.app)
    response = client.get(
        "/proxy/catalog/science",
        params={"bbox": "-5,40,10,55", "zoom": 8, "source": "argo"},
    )
    cached = client.get(
        "/proxy/catalog/science",
        params={"bbox": "-5,40,10,55", "zoom": 8, "source": "argo"},
    )

    assert response.status_code == 200
    assert cached.status_code == 200
    assert [feature["properties"]["name"] for feature in response.json()["features"]] == ["Argo Brest"]
    assert response.json()["metadata"]["rendered"] <= 420
    assert calls == ["science"]


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

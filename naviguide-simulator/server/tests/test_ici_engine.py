import asyncio

import httpx

from ici_engine import (
    FRENCH_EEZ_MRGID,
    eez_plausible,
    empty_dossier,
    feature_latlon,
    fill_dossier,
    haversine_nm,
    nearest_places,
    parse_coord,
    pick_eez_record,
    radius_bbox,
    reset_caches,
    zee_from_record,
)

FR_EEZ = {
    "placeType": "EEZ",
    "preferredGazetteerName": "French Exclusive Economic Zone",
    "MRGID": 5677,
    "latitude": 46.07,
    "longitude": -1.96,
}


LA_ROCHELLE = (46.15, -1.16)


def _point(name, lat, lon, url=None):
    props = {"name": name, "lat": lat, "lon": lon}
    if url:
        props["source_urls"] = [url]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }


def test_haversine_and_bbox():
    nm = haversine_nm(46.15, -1.16, 46.15, -1.16)
    assert nm < 0.05
    # ~30 nm nord
    north = haversine_nm(46.15, -1.16, 46.65, -1.16)
    assert 29 < north < 31
    # antiméridien
    wrap = haversine_nm(0, 179.5, 0, -179.5)
    assert wrap < 70
    minx, miny, maxx, maxy = radius_bbox(46.15, -1.16, 30)
    assert minx < -1.16 < maxx
    assert miny < 46.15 < maxy
    assert maxy - miny == 1.0  # 30 nm / 60


def test_parse_coord_decimal_and_dms():
    assert parse_coord(46.15) == 46.15
    assert parse_coord("46.15") == 46.15
    assert abs(parse_coord("46°09'00\"N") - 46.15) < 0.01
    assert parse_coord(None) is None


def test_zee_from_record_and_pick():
    high = zee_from_record(None)
    assert high["name"] == "Haute mer"
    assert high["gold"] is False
    rec = {
        "placeType": "EEZ",
        "preferredGazetteerName": "French Exclusive Economic Zone",
        "MRGID": 5677,
        "latitude": 46.07,
        "longitude": -1.96,
    }
    zee = zee_from_record(rec)
    assert zee["mrgid"] == 5677
    assert zee["territory"] == "france_metropolitaine"
    assert zee["gold"] is False
    assert 5677 in FRENCH_EEZ_MRGID
    assert eez_plausible(rec, 46.15, -1.16)
    far = {
        "placeType": "EEZ",
        "preferredGazetteerName": "Brazilian Exclusive Economic Zone",
        "MRGID": 8464,
        "latitude": -11.1,
        "longitude": -39.4,
    }
    assert eez_plausible(far, 0.0, -30.0) is False
    picked = pick_eez_record([
        {"placeType": "Nation", "MRGID": 1},
        rec,
    ])
    assert picked["MRGID"] == 5677


def test_nearest_places_caps_and_prefers_props_latlon():
    here_lat, here_lon = LA_ROCHELLE
    far = _point("Loin", 50.0, -5.0)
    poly = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[-10, 40], [-10, 41], [-9, 41], [-9, 40], [-10, 40]]]},
        "properties": {"name": "Pertuis", "lat": 46.16, "lon": -1.17},
    }
    close = _point("Minimes", 46.14, -1.17, "https://douane.gouv.fr/la-rochelle")
    found = nearest_places([far, poly, close], here_lat, here_lon, 30, 5)
    assert [x["name"] for x in found] == ["Pertuis", "Minimes"]
    assert found[0]["nm"] < 5
    plat, plon = feature_latlon(poly)
    assert abs(plat - 46.16) < 0.001


def test_empty_dossier_contract():
    d = empty_dossier(*LA_ROCHELLE)
    assert d["version"] == 1
    assert d["zee"] is None
    assert d["poe"] == []
    assert d["nearby"]["marinas"] == []
    assert d["polar"] is None
    assert d["sources"]["bi"] is None


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "marineregions.org" in url:
        return httpx.Response(200, json=[FR_EEZ])
    if "poe/ports" in url:
        return httpx.Response(200, json={
            "type": "FeatureCollection",
            "features": [_point("La Rochelle", 46.15, -1.15, "https://douane.gouv.fr/la-rochelle")],
        })
    if "/amp?" in url:
        return httpx.Response(200, json={
            "type": "FeatureCollection",
            "features": [_point("Pertuis charentais", 46.16, -1.20)],
        })
    if url.endswith("/export/geojson"):
        return httpx.Response(200, json={
            "type": "FeatureCollection",
            "features": [_point("Récif sentinelle", 46.18, -1.12)] + [
                _point(f"Projet loin {i}", 10.0, 10.0) for i in range(20)
            ],
        })
    if "marinas.geojson" in url:
        return httpx.Response(200, json={
            "type": "FeatureCollection",
            "features": [_point("Port des Minimes", 46.14, -1.17)],
        })
    if "capitaineries.geojson" in url:
        return httpx.Response(200, json={
            "type": "FeatureCollection",
            "features": [_point("Capitainerie La Rochelle", 46.15, -1.16)],
        })
    if "world-port-index" in url:
        return httpx.Response(200, json={
            "ports": [{"portName": "LA ROCHELLE", "latitude": 46.15, "longitude": -1.15}],
        })
    return httpx.Response(404, json={"detail": url})


def test_fill_dossier_la_rochelle_mocked():
    reset_caches()
    transport = httpx.MockTransport(_handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await fill_dossier(46.15, -1.16, client=client)

    d = asyncio.run(run())
    assert d["zee"]["mrgid"] == 5677
    assert d["zee"]["gold"] is True
    assert d["poe"][0]["name"] == "La Rochelle"
    assert d["poe"][0]["url"].startswith("https://douane.gouv.fr")
    assert d["amp"][0]["name"] == "Pertuis charentais"
    assert d["projects"][0]["name"] == "Récif sentinelle"
    assert len(d["projects"]) == 1
    assert d["nearby"]["marinas"][0]["name"] == "Port des Minimes"
    assert d["nearby"]["wpi"][0]["name"] == "LA ROCHELLE"
    assert d["sources"]["zee"] == "marineregions"
    assert d["sources"]["bi"] == "ok"
    assert "grid" not in (d.get("polar") or {})


def test_fill_dossier_bi_down_keeps_zee():
    reset_caches()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "marineregions.org" in url:
            return httpx.Response(200, json=[FR_EEZ])
        if "world-port-index" in url:
            return httpx.Response(200, json={"ports": []})
        return httpx.Response(503, json={"detail": "down"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fill_dossier(46.15, -1.16, client=client)

    d = asyncio.run(run())
    assert d["zee"]["name"].startswith("French")
    assert d["zee"]["gold"] is False
    assert d["poe"] == []
    assert d["amp"] == []
    assert d["sources"]["bi"] == "unavailable"


def test_fill_dossier_partial_bi_keeps_poe():
    reset_caches()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "marineregions.org" in url:
            return httpx.Response(200, json=[FR_EEZ])
        if "poe/ports" in url:
            return httpx.Response(200, json={
                "type": "FeatureCollection",
                "features": [_point("La Rochelle", 46.15, -1.15, "https://douane.gouv.fr/x")],
            })
        if "world-port-index" in url:
            return httpx.Response(200, json={"ports": []})
        return httpx.Response(500, json={"detail": "amp down"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fill_dossier(46.15, -1.16, client=client)

    d = asyncio.run(run())
    assert d["poe"][0]["name"] == "La Rochelle"
    assert d["zee"]["gold"] is True
    assert d["amp"] == []
    assert d["sources"]["bi"] == "partial"


def test_lookup_zee_inland_port_uses_offshore_probe():
    reset_caches()
    hits = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        hits["n"] += 1
        if "/46.15000/-1.16000/" in url:
            return httpx.Response(200, json=[{
                "placeType": "Nation",
                "preferredGazetteerName": "France",
                "MRGID": 17,
            }])
        return httpx.Response(200, json=[FR_EEZ])

    async def run():
        from ici_engine import lookup_zee
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await lookup_zee(client, 46.15, -1.16)

    zee, src = asyncio.run(run())
    assert src == "marineregions"
    assert zee["mrgid"] == 5677
    assert hits["n"] >= 2


def test_lookup_zee_rejects_distant_gazetteer_eez():
    reset_caches()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{
            "placeType": "EEZ",
            "preferredGazetteerName": "Brazilian Exclusive Economic Zone",
            "MRGID": 8464,
            "latitude": -11.1,
            "longitude": -39.4,
        }])

    async def run():
        from ici_engine import lookup_zee
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await lookup_zee(client, 0.0, -30.0)

    zee, src = asyncio.run(run())
    assert src == "marineregions"
    assert zee["name"] == "Haute mer"
    assert zee["mrgid"] is None


def test_fill_dossier_haute_mer():
    reset_caches()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "marineregions.org" in url:
            return httpx.Response(200, json=[])
        if "world-port-index" in url:
            return httpx.Response(200, json={"ports": []})
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fill_dossier(0.0, -30.0, client=client)

    d = asyncio.run(run())
    assert d["zee"]["name"] == "Haute mer"
    assert d["zee"]["mrgid"] is None
    assert d["poe"] == []
    assert d["zee"]["gold"] is False

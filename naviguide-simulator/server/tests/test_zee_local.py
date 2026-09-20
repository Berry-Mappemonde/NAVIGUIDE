"""ZEE locale (lot B) : point-dans-polygone sur la couche VLIZ servie par BI."""
import asyncio
import json

import httpx
import pytest

import ici_engine
import zee_local


def _square(mrgid, geoname, country, lon0, lon1, lat0, lat1):
    return {
        "type": "Feature",
        "properties": {"mrgid": mrgid, "geoname": geoname, "name": country, "sovereign": country, "pol_type": "200NM", "iso2": country[:2].upper()},
        "geometry": {"type": "Polygon", "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]},
    }


def _layer():
    # A "French" box off the Bay of Biscay and a "Spanish" box south of 43.5°N.
    return {"type": "FeatureCollection", "features": [
        _square(5677, "French Exclusive Economic Zone", "France", -10.0, -1.0, 43.5, 48.5),
        _square(5693, "Spanish Exclusive Economic Zone", "Spain", -12.0, -1.5, 36.0, 43.5),
    ]}


@pytest.fixture(autouse=True)
def _fresh():
    zee_local.reset()
    yield
    zee_local.reset()


def test_unknown_until_loaded_then_contains_high_seas_and_ashore():
    assert zee_local.zee_at(46.0, -3.0) is zee_local.UNKNOWN
    zee_local.cache_path().write_text(json.dumps(_layer()))
    assert zee_local.load_from_file() == 2
    st = zee_local.status()
    assert st["loaded"] and st["features"] == 2
    # Off La Rochelle: French, never Spanish (the gazetteer's mistake).
    fr = zee_local.zee_at(46.15, -2.0)
    assert fr["mrgid"] == 5677 and fr["territory"] == "france_metropolitaine" and fr["country"] == "France"
    # South of the boundary: Spanish.
    assert zee_local.zee_at(43.0, -3.0)["mrgid"] == 5693
    # Far out west: high seas (None), not an error.
    assert zee_local.zee_at(40.0, -30.0) is None
    # Saint-Maur (Berry, 200 km inland): ashore, named after the nearest EEZ's country.
    ashore = zee_local.zee_at(46.8, 1.6)
    assert ashore["ashore"] is True and ashore["name"] == "À terre (France)" and ashore["mrgid"] is None


def test_boat_alongside_is_in_its_countrys_eez():
    zee_local.cache_path().write_text(json.dumps(_layer()))
    zee_local.load_from_file()
    # La Rochelle marina sits on the land mask; the box starts at -1.0 (12 nm probe reaches -1.16 - 0.2).
    alongside = zee_local.zee_at(46.15, -1.16)
    assert alongside["mrgid"] == 5677, alongside


def test_lookup_zee_prefers_the_local_layer_and_names_the_source():
    zee_local.cache_path().write_text(json.dumps(_layer()))
    zee_local.load_from_file()

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=[])

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await ici_engine.lookup_zee(c, 46.15, -2.0), await ici_engine.lookup_zee(c, 40.0, -30.0)

    (zee, src), (high, src2) = asyncio.run(run())
    assert zee["mrgid"] == 5677 and src == "vliz-local"
    assert high["mrgid"] is None and high["name"] == "Haute mer" and src2 == "vliz-local"
    assert calls == [], "MarineRegions is not called when the layer is loaded"


def test_lookup_zee_falls_back_to_the_gazetteer_when_not_loaded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"placeType": "EEZ", "MRGID": 5677, "preferredGazetteerName": "French Exclusive Economic Zone", "latitude": 46.0, "longitude": -3.0}])

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await ici_engine.lookup_zee(c, 46.15, -2.0)

    zee, src = asyncio.run(run())
    assert zee["mrgid"] == 5677 and src == "marineregions"


def test_ensure_loaded_downloads_once_and_reuses_the_file():
    body = json.dumps(_layer()).encode() + b" " * 10_000
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=body, headers={"content-type": "application/geo+json"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            ok = await zee_local.ensure_loaded(client=c)
            zee_local.reset()
            ok2 = await zee_local.ensure_loaded(client=c)
            return ok, ok2

    ok, ok2 = asyncio.run(run())
    assert ok and ok2
    assert len(calls) == 1, "second load comes from the cached file"
    assert zee_local.cache_path().exists()


def test_refresh_zee_local_corrects_stored_pearls_without_losing_rich_layers():
    import ici_warm
    import pearl_store
    from ici_engine import thin_cache_key

    zee_local.cache_path().write_text(json.dumps(_layer()))
    zee_local.load_from_file()
    key = thin_cache_key(46.15, -2.0, 30)
    # A rich pearl filled by the gazetteer, wrongly Spanish, with science on board.
    pearl_store.put_pearl(key, {
        "zee": {"name": "Spanish Exclusive Economic Zone", "mrgid": 5693, "territory": None, "gold": False},
        "poe": [{"name": "Bilbao", "nm": 80}],
        "science": {"nearby": [{"name": "REPHY"}]},
        "sources": {"zee": "marineregions", "bi": "ok"},
    }, "rich", 46.15, -2.0)
    changed = asyncio.run(ici_warm.refresh_zee_local(pause_s=0))
    assert changed == 1
    row = pearl_store.get_pearl(key)
    assert row["kind"] == "rich"
    assert row["bag"]["zee"]["mrgid"] == 5677
    assert row["bag"]["sources"]["zee"] == "vliz-local"
    assert row["bag"]["science"]["nearby"][0]["name"] == "REPHY", "rich layers kept"
    assert row["bag"]["poe"] == [] or isinstance(row["bag"]["poe"], list)  # BI unreachable in tests → []
    # Idempotent.
    assert asyncio.run(ici_warm.refresh_zee_local(pause_s=0)) == 0

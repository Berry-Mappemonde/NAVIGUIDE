"""Pré-génération des perles along (ici_warm) : échantillonnage, cache disque, chauffeur."""
import asyncio
import json

import httpx

import ici_engine
import ici_warm
from ici_engine import fill_dossier, reset_caches, thin_cache_key
from tests.test_ici_engine import _handler  # mock BI + MarineRegions


def _route():
    pts = []
    # 200 nm of sea eastward along 46.15°N (1° lon ≈ 41.6 nm), then a hop.
    for i in range(0, 25):
        pts.append({"lat": 46.15, "lon": -1.16 - i * 0.2, "cumNm": i * 8.3, "filmCum": i * 8.3})
    pts.append({"lat": 44.0, "lon": -63.0, "cumNm": 3000, "filmCum": 3100, "jump": True})
    pts.append({"lat": 46.8, "lon": 1.6, "cumNm": 0, "filmCum": 0, "nonMaritime": True})
    return pts


def test_sample_route_every_12_nm_skips_hops_and_land():
    pearls = ici_warm.sample_route(_route())
    assert 15 <= len(pearls) <= 19, len(pearls)
    assert pearls[0][0] == 46.15 and abs(pearls[0][1] + 1.16) < 1e-9
    for (la1, lo1), (la2, lo2) in zip(pearls, pearls[1:]):
        d = ici_warm._haversine_nm(la1, lo1, la2, lo2)
        assert 11.5 <= d <= 13.0, d
    assert all(abs(lo) <= 180 for _, lo in pearls)
    assert ici_warm.sample_route([]) == []


def test_cache_round_trips_through_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path))
    import voyage_store
    monkeypatch.setattr(voyage_store, "_DIR", tmp_path)
    reset_caches()
    ici_engine.thin_cache_put(thin_cache_key(46.15, -1.16, 30, None), {"zee": {"mrgid": 5677}, "sources": {"bi": "ok"}})
    assert ici_warm.save_cache_to_disk(force=True) is True
    path = ici_warm.cache_path()
    assert path.exists()
    assert "5677" in path.read_text()
    reset_caches()
    assert ici_engine.thin_cache_get(thin_cache_key(46.15, -1.16, 30, None)) is None
    assert ici_warm.load_cache_from_disk() == 1
    assert ici_engine.thin_cache_get(thin_cache_key(46.15, -1.16, 30, None))["zee"]["mrgid"] == 5677
    # A stale (> 7 days) or malformed entry is dropped on load.
    path.write_text(json.dumps({"x": {"ts": 0, "bag": {}}, "bad": 1}))
    reset_caches()
    assert ici_warm.load_cache_from_disk() == 0


def test_warmer_fills_the_cache_once_and_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path))
    import voyage_store
    monkeypatch.setattr(voyage_store, "_DIR", tmp_path)
    reset_caches()
    voyage_store.save_voyage({"voyageId": "berry-mappemonde-2026-officiel", "points": _route()[:6], "marks": [], "t0": "2026-05-15T08:00:00Z"})

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return _handler(request)

    transport = httpx.MockTransport(handler)
    real_fill = ici_engine.fill_dossier

    async def patched(lat, lon, radius_nm=30.0, client=None, **kw):
        async with httpx.AsyncClient(transport=transport) as c:
            return await real_fill(lat, lon, radius_nm, client=c, **kw)

    monkeypatch.setattr(ici_engine, "fill_dossier", patched)
    out = asyncio.run(ici_warm.warm_official_route(pause_s=0))
    assert out["status"] == "done"
    assert out["total"] >= 3
    assert out["done"] == out["total"]
    assert out["cached"] == 0
    n_calls = len(calls)
    assert n_calls > 0
    assert ici_warm.cache_path().exists()
    # Second pass: everything is already in the cache, no upstream call.
    out2 = asyncio.run(ici_warm.warm_official_route(pause_s=0))
    assert out2["cached"] == out2["total"]
    assert len(calls) == n_calls


def test_warmer_is_disabled_by_env(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_ICI_WARM", "0")
    assert ici_warm.warm_enabled() is False
    assert ici_warm.start_background() is False
    assert ici_warm.status()["status"] == "disabled"
    monkeypatch.setenv("NAVIGUIDE_ICI_WARM", "1")
    assert ici_warm.warm_enabled() is True

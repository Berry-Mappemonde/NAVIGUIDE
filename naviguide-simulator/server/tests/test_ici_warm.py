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


def test_store_round_trips_between_restarts():
    reset_caches()
    ici_engine.thin_cache_put(thin_cache_key(46.15, -1.16, 30, None), {"zee": {"mrgid": 5677}, "sources": {"bi": "ok"}}, "rich", 46.15, -1.16)
    reset_caches()  # a restart forgets memory, not the store
    assert ici_engine.thin_cache_get(thin_cache_key(46.15, -1.16, 30, None))["zee"]["mrgid"] == 5677
    assert ici_warm.status()["store"]["rich"] == 1


def test_warmer_fills_rich_pearls_once_and_reports(tmp_path, monkeypatch):
    import voyage_store
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
    assert out["status"] == "done" and out["kind"] == "rich"
    assert out["total"] >= 3
    assert out["done"] == out["total"]
    assert out["cached"] == 0
    n_calls = len(calls)
    assert n_calls > 0
    assert out["store"]["rich"] == out["total"], "every pearl is rich in the store"
    # A rich pearl carries the timeless layers a thin one skips.
    la, lo = ici_warm.sample_route(_route()[:6])[0]
    bag = ici_engine.thin_cache_get(thin_cache_key(la, lo, 30))
    assert bag["pearl"] == "rich"
    assert "science" in bag and "aton" in bag and "emodnet" in bag
    assert bag["weather"]["reason"] == "not_in_along_pearl", "weather stays live"
    assert bag["satellites"]["reason"] == "not_in_along_pearl"
    # Second pass: everything is already in the store, no upstream call.
    out2 = asyncio.run(ici_warm.warm_official_route(pause_s=0))
    assert out2["cached"] == out2["total"]
    assert len(calls) == n_calls
    # A thin request is served by the rich pearl (superset), without any call.
    async def thin_req():
        async with httpx.AsyncClient(transport=transport) as c:
            return await real_fill(la, lo, 30.0, client=c, thin=True)
    served = asyncio.run(thin_req())
    assert served["cached"] is True and served["pearl"] == "rich"
    assert len(calls) == n_calls


def test_official_pearls_endpoint_lists_canonical_positions(tmp_path, monkeypatch):
    import voyage_store
    ici_warm._pearls_cache["pearls"] = None
    voyage_store.save_voyage({"voyageId": "berry-mappemonde-2026-officiel", "points": _route(), "marks": [], "t0": "2026-05-15T08:00:00Z", "routeRev": 0})
    out = ici_warm.official_pearls()
    assert out["stepNm"] == 12.0
    assert out["count"] == len(out["pearls"]) >= 15
    assert all(len(p) == 2 for p in out["pearls"])
    assert out["warm"]["status"] in ("idle", "disabled", "running", "done")
    # Same cell as the warmer → the thin cache key ignores the month.
    from ici_engine import thin_cache_key
    la, lo = out["pearls"][0]
    assert thin_cache_key(la, lo, 30, 9) == thin_cache_key(la, lo, 30, None)


def test_status_exposes_llm_budget_counters():
    st = ici_warm.status()
    assert "llm" in st
    for tier in ("fast", "write", "judge"):
        assert set(st["llm"][tier]) >= {"tokens", "calls", "usd"}
        assert st["llm"][tier]["tokens"] == 0
        assert st["llm"][tier]["calls"] == 0


def test_warmer_is_disabled_by_env(monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_ICI_WARM", "0")
    assert ici_warm.warm_enabled() is False
    assert ici_warm.start_background() is False
    assert ici_warm.status()["status"] == "disabled"
    monkeypatch.setenv("NAVIGUIDE_ICI_WARM", "1")
    assert ici_warm.warm_enabled() is True


def test_pearls_carry_the_clocks_sail_scale_including_the_land_leg():
    """Lot K (correctif) : la perle porte le cumNm de la route — l'échelle de
    l'horloge — et non des milles comptés depuis le premier point de mer.
    Sans ça, chaque ligne du journal issue des perles était datée ~16 h trop tôt."""
    pts = [
        {"lat": 46.8, "lon": 1.6, "cumNm": 0, "filmCum": 0, "nonMaritime": True},        # Saint-Maur
        {"lat": 46.15, "lon": -1.16, "cumNm": 122.3, "filmCum": 122.3, "nonMaritime": True},  # La Rochelle (land end)
        {"lat": 46.24, "lon": -1.26, "cumNm": 128.8, "filmCum": 128.8},                    # first sea point
        {"lat": 46.1, "lon": -1.7, "cumNm": 156.0, "filmCum": 156.0},
        {"lat": 45.86, "lon": -2.45, "cumNm": 190.5, "filmCum": 190.5},
    ]
    pearls = ici_warm.sample_route_nm(pts)
    assert pearls[0]["sailNm"] == 128.8, pearls[0]
    assert all(b["sailNm"] > a["sailNm"] for a, b in zip(pearls, pearls[1:]))
    assert pearls[-1]["sailNm"] <= 190.5 + 0.01
    # Without cumNm the old accumulation still works (0 at the first sea point).
    bare = ici_warm.sample_route_nm([{k: v for k, v in p.items() if k != "cumNm"} for p in pts])
    assert bare[0]["sailNm"] == 0

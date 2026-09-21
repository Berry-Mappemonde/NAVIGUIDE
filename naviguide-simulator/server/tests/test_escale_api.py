"""Fiche d'escale (lot C) : listes de faits OSM + BI, paragraphe par la cascade, cache 7 j."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import escale_api
import ici_engine
import pearl_store
import story_cascade
from tests.test_ici_engine import _handler  # mock BI + MarineRegions


def _osm_elements():
    return [
        {"type": "node", "id": 1, "lat": 46.1500, "lon": -1.1700, "tags": {"amenity": "fuel", "name": "Station du port", "fuel:diesel": "yes", "opening_hours": "Mo-Su 08:00-20:00"}},
        {"type": "node", "id": 2, "lat": 46.1520, "lon": -1.1650, "tags": {"amenity": "drinking_water"}},
        {"type": "way", "id": 3, "center": {"lat": 46.1600, "lon": -1.1500}, "tags": {"shop": "supermarket", "name": "Carrefour Market", "website": "https://carrefour.fr"}},
        {"type": "node", "id": 4, "lat": 46.1480, "lon": -1.1720, "tags": {"shop": "chandlery", "name": "Accastillage Diffusion", "phone": "+33 5 46 00 00 00"}},
        {"type": "way", "id": 5, "center": {"lat": 46.1450, "lon": -1.1800}, "tags": {"waterway": "boatyard", "name": "Chantier des Minimes"}},
        {"type": "node", "id": 6, "lat": 46.1580, "lon": -1.1530, "tags": {"tourism": "museum", "name": "Musée Maritime"}},
        {"type": "node", "id": 7, "lat": 46.1585, "lon": -1.1535, "tags": {"tourism": "attraction"}},  # unnamed: dropped
        {"type": "node", "id": 8, "lat": 46.1590, "lon": -1.1540, "tags": {"amenity": "pharmacy", "name": "Pharmacie du Port"}},
    ]


def _transport(calls=None, osm_fail=False):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if calls is not None:
            calls.append(url)
        if "overpass" in url:
            if osm_fail:
                return httpx.Response(503, text="busy")
            return httpx.Response(200, json={"elements": _osm_elements()})
        if "tokenfactory.nebius.com" in url or "integrate.api.nvidia.com" in url or "openrouter.ai" in url or "api.anthropic.com" in url:
            return httpx.Response(200, json={"choices": [{"message": {"content": "La Rochelle offre le Port des Minimes et une capitainerie. Carburant à la Station du port, courses au Carrefour Market. Port d’entrée officiel : La Rochelle - La Pallice."}}]})
        return _handler(request)
    return httpx.MockTransport(handler)


def test_classify_osm_groups_names_and_drops_unnamed_shops():
    out = escale_api.classify_osm(_osm_elements(), 46.15, -1.16)
    assert out["services"]["fuel"][0]["name"] == "Station du port"
    assert out["services"]["fuel"][0]["fuel"] == ["diesel"]
    assert out["services"]["water"][0]["name"] == "drinking water"  # a tap needs no name
    assert out["supplies"]["supermarkets"][0]["url"] == "https://carrefour.fr"
    assert out["maintenance"]["chandlery"][0]["phone"].startswith("+33")
    assert out["maintenance"]["boatyards"][0]["name"] == "Chantier des Minimes"
    assert [i["name"] for i in out["tourism"]["museums"]] == ["Musée Maritime"]
    assert "sights" not in out["tourism"], "unnamed attraction dropped"
    assert out["health"]["pharmacies"][0]["nm"] < 1


def test_build_escale_merges_bag_and_osm_and_writes_a_paragraph(monkeypatch):
    ici_engine.reset_caches()
    monkeypatch.setenv("NEBIUS_API_KEY", "test")
    monkeypatch.setenv("NVIDIA_API_KEY", "test")
    monkeypatch.setattr(story_cascade, "nebius_key", lambda: "test")
    monkeypatch.setattr(story_cascade, "nvidia_key", lambda: "test")
    calls = []

    async def run():
        async with httpx.AsyncClient(transport=_transport(calls)) as c:
            return await escale_api.build_escale("La Rochelle", 46.15, -1.16, "fr", client=c)

    fiche = asyncio.run(run())
    s = fiche["sections"]
    assert list(s.keys()) == [k for k in escale_api.SECTION_ORDER if k in s], "sections in reading order"
    assert "services" in s and "supplies" in s and "maintenance" in s and "tourism" in s
    assert s["formalities"]["zee"]["mrgid"] == 5677
    assert fiche["paragraph"]["status"] == "ready"
    assert "Minimes" in fiche["paragraph"]["text"]
    assert fiche["paragraph"]["source"] == "nemotron-lightning"
    assert fiche["sources"]["osm"] == "osm-overpass"
    assert any("overpass" in u for u in calls)


def test_without_llm_the_lists_stand_alone(monkeypatch):
    ici_engine.reset_caches()
    monkeypatch.setattr(story_cascade, "nebius_key", lambda: "")
    monkeypatch.setattr(story_cascade, "nvidia_key", lambda: "")
    monkeypatch.setattr(story_cascade, "openrouter_key", lambda: "")
    monkeypatch.setattr(story_cascade, "anthropic_key", lambda: "")

    async def run():
        async with httpx.AsyncClient(transport=_transport(osm_fail=True)) as c:
            return await escale_api.build_escale("La Rochelle", 46.15, -1.16, "fr", client=c)

    fiche = asyncio.run(run())
    assert fiche["paragraph"]["status"] == "failed"
    assert fiche["paragraph"]["text"] is None
    assert "services" not in fiche["sections"], "Overpass down: no invented services"
    assert fiche["sources"]["osm"].startswith("overpass_unavailable")
    assert "formalities" in fiche["sections"], "BI layers still there"


def test_endpoint_caches_seven_days(monkeypatch):
    ici_engine.reset_caches()
    calls = []
    transport = _transport(calls)
    real = escale_api.build_escale

    async def patched(name, lat, lon, lang="fr", client=None, **kw):
        async with httpx.AsyncClient(transport=transport) as c:
            return await real(name, lat, lon, lang, client=c, **kw)

    monkeypatch.setattr(escale_api, "build_escale", patched)
    from main import app
    client = TestClient(app)
    r = client.get("/escale?name=La%20Rochelle&lat=46.15&lon=-1.16&lang=fr")
    assert r.status_code == 200
    body = r.json()
    assert body["cached"] is False and body["sections"]
    n = len(calls)
    r2 = client.get("/escale?name=La%20Rochelle&lat=46.15&lon=-1.16&lang=fr")
    assert r2.json()["cached"] is True
    assert len(calls) == n, "served from the store"
    assert pearl_store.kv_count("escale") == 1
    assert client.get("/escale?name=x&lat=95&lon=0").status_code == 400


def test_endpoint_rebuilds_when_cached_paragraph_is_prompt(monkeypatch):
    """Lot RA1 : un paragraphe-prompt en cache 7 j ne doit plus être servi."""
    key = escale_api.escale_key("La Rochelle", 46.15, -1.16, "en")
    pearl_store.kv_put("escale", key, {
        "name": "La Rochelle", "lat": 46.15, "lon": -1.16, "lang": "en",
        "sections": {"mooring": {"marinas": [{"name": "Minimes"}]}},
        "paragraph": {
            "status": "ready",
            "text": "Request: Present a stop/escales to a sailing crew arriving at La Rochelle.",
            "source": "rules",
        },
        "sources": {},
    })
    calls = []
    rebuilt = {
        "name": "La Rochelle", "lat": 46.15, "lon": -1.16, "lang": "en",
        "sections": {"mooring": {"marinas": [{"name": "Minimes"}]}},
        "paragraph": {
            "status": "ready",
            "text": "La Rochelle has the Minimes marina.",
            "source": "nemotron-lightning",
        },
        "sources": {},
    }

    async def patched(*_a, **_k):
        calls.append(1)
        return rebuilt

    monkeypatch.setattr(escale_api, "build_escale", patched)
    from main import app
    client = TestClient(app)
    body = client.get("/escale?name=La%20Rochelle&lat=46.15&lon=-1.16&lang=en").json()
    assert calls == [1]
    assert body["cached"] is False
    assert body["paragraph"]["text"] == "La Rochelle has the Minimes marina."
    assert "Request:" not in (body["paragraph"]["text"] or "")


def test_endpoint_strips_leaked_enrich_from_cache():
    """Lot RA1 : un enrich science-prompt ne doit pas sortir sur la fiche."""
    key = escale_api.escale_key("La Rochelle", 46.15, -1.16, "en")
    pearl_store.kv_put("escale", key, {
        "name": "La Rochelle", "lat": 46.15, "lon": -1.16, "lang": "en",
        "sections": {
            "around": {"science": [{
                "name": "REPHY",
                "nm": 9.4,
                "enrich": {
                    "text": "**Analyze User Input:** Entity: REPHY dataset",
                    "url": "https://example.com/rephy",
                },
            }]},
        },
        "paragraph": {"status": "ready", "text": "La Rochelle has a marina.", "source": "rules"},
        "sources": {},
    })
    from main import app
    client = TestClient(app)
    body = client.get("/escale?name=La%20Rochelle&lat=46.15&lon=-1.16&lang=en").json()
    blob = json.dumps(body)
    assert "Analyze User Input" not in blob
    assert body["cached"] is True
    assert body["sections"]["around"]["science"][0]["name"] == "REPHY"
    enrich = body["sections"]["around"]["science"][0].get("enrich") or {}
    assert "Analyze" not in (enrich.get("text") or "")


def test_write_paragraph_uses_fast_tier_and_keeps_source(monkeypatch):
    seen = {}

    async def fake_cascade(system, user, client=None, **kw):
        seen.update(kw)
        return "La Rochelle a une marina et une capitainerie.", "nemotron-lightning"

    monkeypatch.setattr(escale_api, "cascade_text", fake_cascade)
    sections = {"mooring": {"marinas": [{"name": "Minimes", "nm": 0.2}]}}
    out = asyncio.run(escale_api.write_paragraph("La Rochelle", sections, "fr"))
    assert seen.get("tier") == "fast"
    assert out["status"] == "ready"
    assert out["source"] == "nemotron-lightning"
    assert out["engine"] == "nemotron-lightning"


def test_write_paragraph_en_translates_and_keeps_figures(monkeypatch):
    seen = []

    async def fake_cascade(system, user, client=None, **kw):
        seen.append(("cascade", kw.get("tier"), "français" in system or "Tu présentes" in system))
        return "La Rochelle a le Port des Minimes à 0,2 nm.", "nemotron-lightning"

    async def fake_tr(text, lang, client=None, **kw):
        seen.append(("translate", lang))
        assert "0,2" in text or "0.2" in text
        assert "Minimes" in text
        return "La Rochelle has the Port des Minimes at 0.2 nm.", "nemotron-lightning"

    monkeypatch.setattr(escale_api, "cascade_text", fake_cascade)
    monkeypatch.setattr(escale_api, "translate", fake_tr)
    sections = {"mooring": {"marinas": [{"name": "Minimes", "nm": 0.2}]}}
    out = asyncio.run(escale_api.write_paragraph("La Rochelle", sections, "en"))
    assert ("cascade", "fast", True) in seen
    assert ("translate", "en") in seen
    assert out["status"] == "ready"
    assert out["source"] == "nemotron-lightning"
    assert "Minimes" in out["text"]
    assert "0.2" in out["text"] or "0,2" in out["text"]
    assert "99" not in out["text"]

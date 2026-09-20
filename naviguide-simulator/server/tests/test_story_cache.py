"""Récits pré-générés (lot F) : cache par (type, stableKey, lang), cascade habituelle, budget."""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

import ici_engine
import pearl_store
import story_cache
import story_cascade
import voyage_store
from ici_engine import thin_cache_key
from tests.test_voyage_journal import PUBLIC, _official
from voyage_clock import OFFICIAL_VOYAGE_ID


def _llm(answer="Le bateau entre dans la ZEE espagnole ; ports d’entrée officiels : Bilbao, Santander."):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "tokenfactory.nebius.com" in url or "integrate.api.nvidia.com" in url or "openrouter.ai" in url or "api.anthropic.com" in url:
            calls.append(url)
            return httpx.Response(200, json={"choices": [{"message": {"content": answer}}]})
        return httpx.Response(404)
    return httpx.MockTransport(handler), calls


def test_key_only_for_position_independent_events():
    assert story_cache.story_key({"type": "zee-enter", "stableKey": "zee-enter:5693", "lang": "fr"}) == "zee-enter|zee-enter:5693|fr"
    assert story_cache.story_key({"event": "poe-ahead", "stableKey": "poe-ahead:5693:Bilbao", "lang": "en-GB"}) == "poe-ahead|poe-ahead:5693:Bilbao|en"
    assert story_cache.story_key({"type": "wind-gale", "stableKey": "wind-gale:x"}) is None, "a gale is written live"
    assert story_cache.story_key({"type": "zee-enter"}) is None, "no stable key, no cache"


def test_story_endpoint_reads_the_cache_then_writes_through_it(monkeypatch):
    monkeypatch.setattr(story_cascade, "nebius_key", lambda: "test")
    monkeypatch.setattr(story_cascade, "nvidia_key", lambda: "test")
    transport, calls = _llm()
    real = story_cascade.write_story

    async def patched(body, client=None):
        async with httpx.AsyncClient(transport=transport) as c:
            return await real(body, c)

    monkeypatch.setattr(story_cascade, "write_story", patched)
    import main
    monkeypatch.setattr(main, "write_story", patched)
    from main import app
    client = TestClient(app)
    body = {"event": "zee-enter", "type": "zee-enter", "stableKey": "zee-enter:5693", "lang": "fr", "payload": {"zee": {"name": "Spanish EEZ", "mrgid": 5693}}}
    r1 = client.post("/ici/story", json=body, headers=PUBLIC).json()
    assert r1["status"] == "ready" and r1["cached"] is False and len(calls) == 1
    r2 = client.post("/ici/story", json={**body, "eventId": "other"}, headers=PUBLIC).json()
    assert r2["status"] == "ready" and r2["cached"] is True and r2["engine"].startswith("cache:")
    assert r2["text"] == r1["text"]
    assert len(calls) == 1, "served from the store"
    assert story_cache.budget_used_today() == 1
    # A gale is never cached.
    gale = {"event": "wind-gale", "type": "wind-gale", "stableKey": "wind-gale:x", "lang": "fr", "payload": {}}
    client.post("/ici/story", json=gale, headers=PUBLIC)
    client.post("/ici/story", json=gale, headers=PUBLIC)
    # gale is not in the story store, but cascade_text caches the prompt.
    assert len(calls) == 2
    assert pearl_store.kv_count("story") == 1


def test_pregeneration_from_pearls_under_budget(monkeypatch):
    ici_engine.reset_caches()
    monkeypatch.setattr(story_cascade, "nebius_key", lambda: "test")
    monkeypatch.setattr(story_cascade, "nvidia_key", lambda: "test")
    transport, calls = _llm()
    real = story_cascade.write_story

    async def patched(body, client=None):
        async with httpx.AsyncClient(transport=transport) as c:
            return await real(body, c)

    monkeypatch.setattr(story_cascade, "write_story", patched)
    voy = {**_official(), "voyageId": OFFICIAL_VOYAGE_ID}
    voyage_store.save_voyage(voy)
    import ici_warm
    pearls = ici_warm.sample_route_nm(voy["points"])
    fr = {"name": "French Exclusive Economic Zone", "mrgid": 5677, "gold": True}
    es = {"name": "Spanish Exclusive Economic Zone", "mrgid": 5693}
    for i, p in enumerate(pearls[:30]):
        zee = fr if i < 12 else es
        poe = [{"name": "La Rochelle - La Pallice", "id": "lr", "nm": 1.0, "url": "https://douane.gouv.fr"}] if i == 0 else [{"name": "Bilbao", "nm": 60}]
        ici_engine.thin_cache_put(thin_cache_key(p["lat"], p["lon"], 30.0), {"zee": zee, "amp": [], "poe": poe, "sources": {"bi": "ok"}})
    bodies = story_cache.pregen_bodies(voy["points"], "fr")
    keys = sorted(story_cache.story_key(b) for b in bodies)
    assert "zee-enter|zee-enter:5693|fr" in keys, keys
    assert any(k.startswith("poe-ahead|poe-ahead:5677:La Rochelle") for k in keys)
    zee_body = next(b for b in bodies if b["type"] == "zee-enter")
    assert zee_body["payload"]["poe"][0]["name"] == "Bilbao" and "nm" not in zee_body["payload"]["poe"][0], "no boat distance in a pre-generated text"

    monkeypatch.setenv("NAVIGUIDE_STORY_BUDGET_PER_DAY", "1")
    out = asyncio.run(story_cache.pregenerate_official(voy["points"], pause_s=0))
    assert out["planned"] == len(bodies) >= 2
    assert out["written"] == 1 and out["skippedBudget"] == len(bodies) - 1, out
    assert out["budgetLeftToday"] == 0
    # Second run: the written one is cached, nothing spent beyond the budget.
    monkeypatch.setenv("NAVIGUIDE_STORY_BUDGET_PER_DAY", "10")
    out2 = asyncio.run(story_cache.pregenerate_official(voy["points"], pause_s=0))
    assert out2["cached"] == 1 and out2["written"] == len(bodies) - 1
    assert out2["stored"] == len(bodies)

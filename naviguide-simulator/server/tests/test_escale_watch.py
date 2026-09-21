"""Veille Tavily + enrichissement science — faux Tavily + faux Nemotron (lot L4)."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

import escale_watch
import llm_budget
import voyage_journal as journal
from voyage_clock import parse_iso


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
PORT = {
    "name": "Nouméa",
    "lat": -22.2758,
    "lon": 166.4483,
    "url": "https://www.portautonome.nc/",
}
SCI = {
    "name": "IRD Nouméa",
    "lat": -22.3,
    "lon": 166.44,
    "url": "https://www.ird.fr/noumea",
}
TAVILY_HIT = {
    "title": "Avis aux navigateurs — Motu Uta",
    "url": "https://www.portautonome.nc/avis",
    "content": "Travaux annoncés à la marina de Motu Uta.",
}
SUMMARY = "Travaux annoncés à la marina de Motu Uta"
ENRICH = "L'IRD Nouméa observe le climat du Pacifique Sud"


def _chat_ok(text, model="nvidia/Nemotron-3_5-Lightning"):
    return {
        "choices": [{"message": {"content": text}}],
        "model": model,
        "usage": {"prompt_tokens": 40, "completion_tokens": 20},
    }


def _handler(seen=None, search_body=None, summary=SUMMARY, extract_text=ENRICH):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url.endswith("/search"):
            if search_body is not None:
                search_body.append(json.loads(request.read().decode()))
            return httpx.Response(200, json={"results": [TAVILY_HIT]})
        if url.endswith("/extract"):
            return httpx.Response(200, json={
                "results": [{"url": SCI["url"], "raw_content": extract_text}],
            })
        if "tokenfactory" in url:
            return httpx.Response(200, json=_chat_ok(summary))
        return httpx.Response(404, json={"detail": url})
    return handler


def _keys(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("NEBIUS_API_KEY", "tf-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_watch_query_and_window():
    q = escale_watch.watch_query("Nouméa")
    assert "Nouméa" in q
    assert "marina OR port OR harbour" in q
    assert "notice OR avis OR travaux OR fermeture OR event" in q
    assert "noumea.nc" in escale_watch.official_domains("Nouméa")
    clock = {
        "t0": "2026-09-10T08:00:00Z",
        "marks": [
            {"name": "Nouméa", "iso": "2026-09-20T08:00:00Z", "lat": -22.27, "lon": 166.44},
            {"name": "Trop tôt", "iso": "2026-08-01T08:00:00Z"},
            {"name": "Trop tard", "iso": "2026-12-01T08:00:00Z"},
        ],
    }
    names = [s["name"] for s in escale_watch.stops_in_window(clock, NOW)]
    assert names == ["Nouméa"]
    late = NOW + timedelta(days=3)
    assert escale_watch.stops_in_window(clock, late) == []


def test_one_watch_writes_news_with_url(monkeypatch):
    _keys(monkeypatch)
    journal.reset()
    seen, bodies = [], []

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(seen, bodies))) as client:
            return await escale_watch.watch_stop(PORT, NOW, client=client)

    entry = asyncio.run(run())
    assert entry["kind"] == "news"
    assert entry["name"] == "Nouméa"
    assert entry["url"] == TAVILY_HIT["url"]
    assert "Travaux" in entry["text"]
    assert "42" not in entry["text"]
    assert entry["id"] == "news:noumea:2026-09-20"
    assert parse_iso(entry["expires"]) > NOW
    logged = journal.latest(5, kinds=("news",))
    assert len(logged) == 1
    assert logged[0]["url"] == TAVILY_HIT["url"]
    assert any(u.endswith("/search") for u in seen)
    assert bodies[0]["topic"] == "news"
    assert bodies[0]["days"] == 7
    assert bodies[0]["max_results"] == 5
    assert llm_budget.tavily_usage()["credits"] == 1


def test_two_days_one_search_per_day(monkeypatch):
    _keys(monkeypatch)
    journal.reset()
    seen = []
    day1 = NOW
    day2 = NOW + timedelta(days=1)

    async def once(when):
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(seen))) as client:
            a = await escale_watch.watch_stop(PORT, when, client=client)
            b = await escale_watch.watch_stop(PORT, when, client=client)
            return a, b

    first, again = asyncio.run(once(day1))
    assert first and again and first["id"] == again["id"]
    searches = [u for u in seen if u.endswith("/search")]
    assert len(searches) == 1
    asyncio.run(once(day2))
    searches = [u for u in seen if u.endswith("/search")]
    assert len(searches) == 2
    assert llm_budget.tavily_usage()["credits"] == 2


def test_science_extract_attached_once(monkeypatch):
    _keys(monkeypatch)
    seen = []
    item = dict(SCI)

    async def once():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(seen, summary=ENRICH))) as client:
            return await escale_watch.enrich_entity(item, client=client)

    first = asyncio.run(once())
    assert first["text"]
    assert first["url"] == SCI["url"]
    assert item["enrich"]["text"] == first["text"]
    extracts = [u for u in seen if u.endswith("/extract")]
    assert len(extracts) == 1
    second = asyncio.run(once())
    assert second["text"] == first["text"]
    assert len([u for u in seen if u.endswith("/extract")]) == 1


def test_credit_budget_blocks_second_search(monkeypatch):
    _keys(monkeypatch)
    monkeypatch.setenv("NAVIGUIDE_TAVILY_DAILY_CREDITS", "1")
    seen = []
    other = {**PORT, "name": "Ajaccio"}

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler(seen))) as client:
            a = await escale_watch.watch_stop(PORT, NOW, client=client)
            b = await escale_watch.watch_stop(other, NOW, client=client)
            return a, b

    a, b = asyncio.run(run())
    assert a and a["kind"] == "news"
    assert b is None
    assert len([u for u in seen if u.endswith("/search")]) == 1
    assert llm_budget.tavily_usage()["credits"] == 1
    assert llm_budget.allow_tavily() is False


def test_filter_numbers_drops_invented_figure():
    facts = {"results": [TAVILY_HIT]}
    cleaned, dropped = __import__("story_cascade", fromlist=["filter_numbers"]).filter_numbers(
        "Travaux pour 42 bateaux à Motu Uta.", facts,
    )
    assert dropped >= 1
    assert "42" not in cleaned


def test_ici_warm_hooks_daily_watch():
    src = Path(__file__).resolve().parents[1].joinpath("ici_warm.py").read_text()
    assert "escale_watch" in src
    assert "run_daily" in src
    assert "news" in Path(__file__).resolve().parents[1].joinpath("voyage_journal.py").read_text()

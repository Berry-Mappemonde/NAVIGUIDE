"""Veille web Tavily pour le chat journal (port prochain)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

import llm_budget
import port_web_context
import tavily_client


def test_build_query_includes_port_and_region():
    q = port_web_context.build_query("Nouméa", "New Caledonia")
    assert "Nouméa" in q
    assert "New Caledonia" in q


def test_fetch_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    out = asyncio.run(port_web_context.fetch_port_web("La Rochelle"))
    assert out["status"] == "unavailable"
    assert out["reason"] == "no-key"
    assert llm_budget.tavily_usage()["calls"] == 0


def test_fetch_search_cached(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert "search" in str(request.url)
        body = json.loads(request.content.decode())
        assert "Nouméa" in body.get("query", "")
        return httpx.Response(200, json={
            "results": [{
                "title": "Port info",
                "url": "https://example.com/port",
                "content": "Travaux sur le quai.",
            }],
        })

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            a = await port_web_context.fetch_port_web("Nouméa", client=client)
            b = await port_web_context.fetch_port_web("Nouméa", client=client)
            return a, b

    first, second = asyncio.run(run())
    assert first["status"] == "ready"
    assert first["sources"][0]["url"] == "https://example.com/port"
    assert second["status"] == "ready"
    assert len(seen) == 1
    assert llm_budget.tavily_usage()["calls"] == 1


def test_attach_puts_port_web_on_context(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            ctx = {"nextStop": {"name": "Papeete"}}
            await port_web_context.attach(ctx, client, datetime.now(timezone.utc))
            return ctx

    ctx = asyncio.run(run())
    assert "portWeb" in ctx
    assert ctx["portWeb"]["status"] in {"ready", "unavailable"}


def test_pick_port_label_falls_back_to_nearest_named_port():
    from port_web_context import pick_port_label

    ctx = {"around": {"portsOfEntry": [], "ports": [{"name": "Lorient", "nm": 3.2}], "marinas": [{"name": "Kernevel"}]}}
    assert pick_port_label(ctx) == "Lorient"
    assert pick_port_label({"nextStop": {"name": "Mindelo"}, **ctx}) == "Mindelo"
    assert pick_port_label({"around": {"ports": [{"nm": 1}]}}) is None

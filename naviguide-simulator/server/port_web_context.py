"""Contexte web Tavily pour le journal de bord (port / région autour du bateau).

Une recherche Tavily max par port et par jour (cache `pearl_store`). Sans clé,
plafond ou erreur réseau : `status=unavailable`, jamais de texte inventé.
Les extraits alimentent Nemotron (faits JSON du chat) ; les URLs reviennent
dans `webSources` pour l'UI.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

import llm_budget
import tavily_client
from escale_watch import slug

log = logging.getLogger("naviguide-simulator.port-web")

NS = "port-web"
TTL_S = 86400.0
SEARCH_DAYS = 14
MAX_RESULTS = 4
MAX_SNIPPET = 480


def enabled() -> bool:
    """Activé par défaut (hackathon Tavily). `NAVIGUIDE_PORT_WEB=0` pour couper."""
    return (os.environ.get("NAVIGUIDE_PORT_WEB") or "1").strip().lower() not in (
        "0", "false", "off", "no",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _day(now: datetime | None = None) -> str:
    t = now or datetime.now(timezone.utc)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _cache_key(port: str, day: str | None = None) -> str:
    return f"{day or _day()}:{slug(port)}"


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason, "sources": [], "fetchedAt": None}


def pick_port_label(ctx: dict[str, Any]) -> str | None:
    """Prochaine escale, sinon escale nommée dans le bateau / l'horloge."""
    stop = ctx.get("nextStop") if isinstance(ctx.get("nextStop"), dict) else None
    name = (stop or {}).get("name") if stop else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    boat = ctx.get("boat") if isinstance(ctx.get("boat"), dict) else {}
    mark = boat.get("atMark") if isinstance(boat.get("atMark"), dict) else None
    if mark and isinstance(mark.get("name"), str) and mark["name"].strip():
        return mark["name"].strip()
    official = ctx.get("official") if isinstance(ctx.get("official"), dict) else {}
    at = official.get("atMark") if isinstance(official.get("atMark"), dict) else None
    if at and isinstance(at.get("name"), str) and at["name"].strip():
        return at["name"].strip()
    # Film / simulation sans horloge officielle : port nommé le plus proche du bateau.
    around = ctx.get("around") if isinstance(ctx.get("around"), dict) else {}
    for key in ("portsOfEntry", "ports", "marinas", "harbourMasters"):
        for row in around.get(key) or []:
            if isinstance(row, dict) and isinstance(row.get("name"), str) and row["name"].strip():
                return row["name"].strip()
    return None


def pick_region_hint(ctx: dict[str, Any]) -> str | None:
    around = ctx.get("around") if isinstance(ctx.get("around"), dict) else {}
    zee = around.get("zee") if isinstance(around.get("zee"), dict) else {}
    name = zee.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def build_query(port: str, region: str | None = None) -> str:
    bits = [port.strip(), "port", "maritime", "sailing"]
    if region:
        bits.append(region.strip())
    return " ".join(b for b in bits if b)


def _normalize_results(raw: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url.startswith("http") or url in seen:
            continue
        title = str(item.get("title") or "").strip() or urlparse(url).netloc
        snippet = str(item.get("content") or item.get("raw_content") or "").strip()
        snippet = re.sub(r"\s+", " ", snippet)[:MAX_SNIPPET]
        seen.add(url)
        out.append({"title": title, "url": url, "snippet": snippet})
        if len(out) >= MAX_RESULTS:
            break
    return out


def _load_cache(port: str, day: str | None = None) -> dict[str, Any] | None:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(NS, _cache_key(port, day), TTL_S)
    val = (hit or {}).get("value")
    return val if isinstance(val, dict) else None


def _save_cache(port: str, payload: dict[str, Any], day: str | None = None) -> None:
    import pearl_store  # noqa: PLC0415

    pearl_store.kv_put(NS, _cache_key(port, day), payload)


async def fetch_port_web(
    port: str,
    *,
    region: str | None = None,
    now: datetime | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Recherche Tavily (cache 24 h)."""
    label = (port or "").strip()
    if not label:
        return _unavailable("no-port")
    if not enabled():
        return _unavailable("disabled")
    if not tavily_client.api_key():
        return _unavailable("no-key")
    if not llm_budget.allow_tavily():
        return _unavailable("budget")

    day = _day(now)
    cached = _load_cache(label, day)
    if cached and cached.get("status") in {"ready", "unavailable"}:
        return dict(cached)

    query = build_query(label, region)
    try:
        data = await tavily_client.search(
            query,
            topic="news",
            days=SEARCH_DAYS,
            max_results=MAX_RESULTS,
            client=client,
        )
    except Exception as exc:
        log.warning("port-web Tavily: %s", exc)
        out = _unavailable("error")
        _save_cache(label, {**out, "fetchedAt": _now_iso(), "port": label}, day)
        return out

    sources = _normalize_results(data.get("results") if isinstance(data, dict) else [])
    llm_budget.remember_tavily_port(label)
    if not sources:
        out = _unavailable("empty")
        _save_cache(label, {**out, "fetchedAt": _now_iso(), "port": label, "query": query}, day)
        return out

    excerpts = [s["snippet"] for s in sources if s.get("snippet")]
    out: dict[str, Any] = {
        "status": "ready",
        "port": label,
        "query": query,
        "region": region,
        "fetchedAt": _now_iso(),
        "sources": sources,
        "excerpts": excerpts[:MAX_RESULTS],
        "basis": "tavily",
    }
    _save_cache(label, out, day)
    return out


async def attach(
    ctx: dict[str, Any],
    http: httpx.AsyncClient | None,
    now: datetime | None = None,
) -> None:
    port = pick_port_label(ctx)
    if not port:
        ctx["portWeb"] = _unavailable("no-port")
        return
    region = pick_region_hint(ctx)
    ctx["portWeb"] = await fetch_port_web(port, region=region, now=now, client=http)


def web_sources_for_response(ctx: dict[str, Any] | None) -> list[dict[str, str]]:
    pw = (ctx or {}).get("portWeb") if isinstance(ctx, dict) else None
    if not isinstance(pw, dict) or pw.get("status") != "ready":
        return []
    src = pw.get("sources")
    if not isinstance(src, list):
        return []
    return [s for s in src if isinstance(s, dict) and s.get("url")]

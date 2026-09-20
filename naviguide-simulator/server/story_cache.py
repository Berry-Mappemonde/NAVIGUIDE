"""Récits pré-générés (lot F, commentaires 6-8 du porteur : sans Nebius).

Le récit LLM d'une carte est prêt **avant** que le bateau y arrive :

- cache SQLite (`pearl_store.kv`, ns « story », 7 jours) indexé par
  `(type, stableKey, lang)` — pour les seuls événements dont le texte ne
  dépend pas de l'instant du bateau (entrer dans une ZEE, quitter une ZEE,
  aire marine protégée, port d'entrée devant) ; un coup de vent, une alerte
  de profondeur ou un repli restent rédigés à chaud ;
- `POST /ici/story` lit le cache d'abord, puis la cascade habituelle
  (NIM → OpenRouter → Claude) et garde le résultat ;
- après les perles, le chauffeur **pré-génère** les récits des événements
  que le film lèvera sur la route officielle (ZEE entrées, ports d'entrée),
  trois en vol, sous un budget journalier (`NAVIGUIDE_STORY_BUDGET_PER_DAY`,
  300) — jamais sans cache, le crédit ne brûle pas deux fois.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("naviguide-simulator.story-cache")

STORY_TTL_S = 7 * 86400.0
CACHEABLE_TYPES = frozenset({"zee-enter", "zee-exit", "amp-enter", "amp-ahead", "poe-ahead"})
PREGEN_PARALLEL = 3
PREGEN_PAUSE_S = 0.5


def budget_per_day() -> int:
    try:
        return max(0, int(os.environ.get("NAVIGUIDE_STORY_BUDGET_PER_DAY") or 300))
    except ValueError:
        return 300


def pregen_langs() -> tuple[str, ...]:
    raw = (os.environ.get("NAVIGUIDE_STORY_LANGS") or "fr").strip()
    return tuple(l.strip()[:2] for l in raw.split(",") if l.strip()) or ("fr",)


# ── key / lookup ────────────────────────────────────────────────────────────

def story_key(body: dict | None) -> Optional[str]:
    """(type, stableKey, lang) → key, or None when this event is not cacheable."""
    if not isinstance(body, dict):
        return None
    typ = str(body.get("type") or body.get("event") or "")
    stable = body.get("stableKey")
    if typ not in CACHEABLE_TYPES or not stable:
        return None
    lang = str(body.get("lang") or "fr")[:2].lower()
    return f"{typ}|{stable}|{lang}"


def get_cached(body: dict | None) -> Optional[dict]:
    key = story_key(body)
    if not key:
        return None
    import pearl_store  # noqa: PLC0415
    hit = pearl_store.kv_get("story", key, STORY_TTL_S)
    if not hit or not isinstance(hit.get("value"), dict) or not hit["value"].get("text"):
        return None
    v = hit["value"]
    return {
        "status": "ready",
        "text": v["text"],
        "engine": f"cache:{v.get('engine') or 'llm'}",
        "cascade": "nim-or-claude",
        "tavily": None,
        "nvidia": v.get("engine"),
        "cached": True,
        "cachedAt": hit["ts"],
    }


def put_cached(body: dict | None, result: dict | None) -> bool:
    key = story_key(body)
    if not key or not isinstance(result, dict) or result.get("status") != "ready" or not result.get("text"):
        return False
    import pearl_store  # noqa: PLC0415
    return pearl_store.kv_put("story", key, {"text": result["text"], "engine": result.get("engine"), "type": body.get("type")})


# ── budget ──────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def budget_used_today() -> int:
    import pearl_store  # noqa: PLC0415
    hit = pearl_store.kv_get("story-budget", _today())
    try:
        return int((hit or {}).get("value") or 0)
    except (TypeError, ValueError):
        return 0


def budget_left() -> int:
    return max(0, budget_per_day() - budget_used_today())


def _spend(n: int = 1) -> None:
    import pearl_store  # noqa: PLC0415
    pearl_store.kv_put("story-budget", _today(), budget_used_today() + n)


# ── the cascade, through the cache ──────────────────────────────────────────

async def story_through_cache(body: dict, client=None, writer=None) -> dict[str, Any]:
    """What POST /ici/story returns: the cache when it knows, else the cascade
    (`writer`, default story_cascade.write_story) — and remember."""
    if writer is None:
        from story_cascade import write_story  # noqa: PLC0415
        writer = write_story
    hit = get_cached(body)
    if hit:
        return hit
    out = await writer(body, client) if client is not None else await writer(body)
    if put_cached(body, out):
        _spend(1)
    return {**(out or {}), "cached": False}


# ── pre-generation from the pearls ──────────────────────────────────────────

def pregen_bodies(points: list[dict], lang: str = "fr") -> list[dict]:
    """The story requests a film will make on the official route, from the
    warmed pearls: ZEE entered (with its official ports of entry, no boat
    distance — the text must serve at any position) and ports of entry
    passed. Same `type` / `stableKey` as the client's events."""
    from ici_engine import thin_cache_get, thin_cache_key  # noqa: PLC0415
    from ici_warm import route_events_from_pearls, sample_route_nm  # noqa: PLC0415

    bodies: dict[str, dict] = {}
    pearls = sample_route_nm(points)
    for ev in route_events_from_pearls(points):
        if ev["kind"] == "zee" and ev["event"] == "enter" and ev.get("mrgid"):
            mrgid = ev["mrgid"]
            pearl = pearls[ev["idx"]] if 0 <= ev["idx"] < len(pearls) else None
            bag = thin_cache_get(thin_cache_key(pearl["lat"], pearl["lon"], 30.0)) if pearl else None
            poe = [{"name": p.get("name"), "url": p.get("url")} for p in ((bag or {}).get("poe") or [])[:4] if isinstance(p, dict) and p.get("name")]
            gold = bool(((bag or {}).get("zee") or {}).get("gold"))
            body = {
                "event": "zee-enter", "type": "zee-enter", "stableKey": f"zee-enter:{mrgid}", "lang": lang,
                "severity": "watch", "judge": "now", "name": ev.get("name"),
                "payload": {"zee": {"name": ev.get("name"), "mrgid": mrgid, "gold_pack": gold}, "poe": poe,
                            "weather": None, "weather_reason": "not_in_this_event", "rain": None, "rain_reason": "not_in_this_event",
                            "tavily": None, "nvidia": None},
                "tavily": None, "nvidia": None,
            }
            bodies.setdefault(story_key(body), body)
        elif ev["kind"] == "poe" and ev.get("name"):
            mrgid = ev.get("mrgid") or "x"
            body = {
                "event": "poe-ahead", "type": "poe-ahead", "stableKey": f"poe-ahead:{mrgid}:{ev['name']}", "lang": lang,
                "severity": "info", "judge": "now", "name": ev["name"],
                "payload": {"poe": {"name": ev["name"], "url": ev.get("url")}, "zee": {"mrgid": ev.get("mrgid")}, "tavily": None, "nvidia": None},
                "tavily": None, "nvidia": None,
            }
            bodies.setdefault(story_key(body), body)
    return list(bodies.values())


_state: dict[str, Any] = {"status": "idle", "planned": 0, "cached": 0, "written": 0, "failed": 0, "skippedBudget": 0, "startedAt": None, "finishedAt": None}


def status() -> dict[str, Any]:
    import pearl_store  # noqa: PLC0415
    return {**_state, "stored": pearl_store.kv_count("story"), "budgetLeftToday": budget_left()}


async def pregenerate_official(points: list[dict], *, pause_s: float = PREGEN_PAUSE_S, client=None) -> dict[str, Any]:
    """Write ahead the stories of the official route, under today's budget."""
    from story_cascade import write_story  # noqa: PLC0415
    bodies = [b for lang in pregen_langs() for b in pregen_bodies(points, lang)]
    _state.update({"status": "running", "planned": len(bodies), "cached": 0, "written": 0, "failed": 0, "skippedBudget": 0,
                   "startedAt": time.time(), "finishedAt": None})
    todo = []
    for body in bodies:
        if get_cached(body):
            _state["cached"] += 1
        else:
            todo.append(body)

    async def one(body: dict) -> None:
        if budget_left() <= 0:
            _state["skippedBudget"] += 1
            return
        try:
            out = await write_story(body, client)
        except Exception as exc:
            _state["failed"] += 1
            log.debug("pré-génération %s : %s", body.get("stableKey"), exc)
            return
        if put_cached(body, out):
            _spend(1)
            _state["written"] += 1
        else:
            _state["failed"] += 1
        await asyncio.sleep(pause_s)

    for i in range(0, len(todo), PREGEN_PARALLEL):
        await asyncio.gather(*(one(b) for b in todo[i:i + PREGEN_PARALLEL]))
    _state["status"] = "done"
    _state["finishedAt"] = time.time()
    log.info("récits pré-générés : %d écrits, %d déjà là, %d échecs, %d hors budget",
             _state["written"], _state["cached"], _state["failed"], _state["skippedBudget"])
    return status()

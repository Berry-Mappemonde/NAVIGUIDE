"""Veille Tavily par escale (U10) + enrichissement science / projet (U12).

Lot L4. Un `search` par escale et par jour (J-10 → J+2), résumé Nano
(`tier=fast`) sans chiffre nouveau. Un `extract` par entité, cache
définitif ns `enrich`. Jamais d'appel depuis le navigateur.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

import llm_budget
import tavily_client
from story_cascade import cascade_text, filter_numbers
from voyage_clock import parse_iso, to_iso

log = logging.getLogger("naviguide-simulator.watch")

WATCH_NS = "watch"
ENRICH_NS = "enrich"
WATCH_BEFORE_DAYS = 10
WATCH_AFTER_DAYS = 2
WATCH_EXPIRE_DAYS = 2
SEARCH_DAYS = 7
SEARCH_MAX = 5
ENRICH_DAILY_CAP = 8
MAX_EXTRACT_CHARS = 8_000

WATCH_SYSTEM = (
    "Tu résumes une veille portuaire en UNE phrase. "
    "Aucun chiffre qui n'est pas déjà dans les extraits. "
    "Pas d'invention. Thinking OFF."
)
ENRICH_SYSTEM = (
    "Tu extraits UNE phrase factuelle sur cette station ou ce projet, "
    "d'après l'extrait officiel seulement. "
    "Aucun chiffre qui n'est pas déjà dans l'extrait. "
    "Pas d'invention. Thinking OFF."
)

# Domaines officiels connus (ports du voyage Berry). Sinon : pas de filtre.
_KNOWN_DOMAINS: dict[str, tuple[str, ...]] = {
    "noumea": ("noumea.nc", "portautonome.nc"),
    "nouméa": ("noumea.nc", "portautonome.nc"),
    "la rochelle": ("portlarochelle.com", "douane.gouv.fr"),
    "fort-de-france": ("douane.gouv.fr", "martinique.gouv.fr"),
    "ajaccio": ("douane.gouv.fr", "corse.gouv.fr"),
    "brisbane": ("msq.qld.gov.au",),
    "san francisco": ("sfport.com",),
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FOLD = str.maketrans("àâäáéèêëíìîïóòôöúùûüçñ", "aaaaeeeeiiiioooouuuucn")


def slug(name: str) -> str:
    folded = (name or "").strip().lower().translate(_FOLD)
    return _SLUG_RE.sub("-", folded).strip("-") or "escale"


def watch_query(port: str) -> str:
    name = (port or "").strip() or "port"
    return (
        f"{name} marina OR port OR harbour "
        "(notice OR avis OR travaux OR fermeture OR event)"
    )


def official_domains(name: str, urls: Iterable[str] | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    key = (name or "").strip().lower()
    for host in _KNOWN_DOMAINS.get(key, ()):
        if host not in seen:
            seen.add(host)
            out.append(host)
    for raw in urls or []:
        host = _host_of(raw)
        if host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


def _host_of(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return None
    try:
        host = (urlparse(raw).hostname or "").lower()
    except Exception:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _utc(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _day(now: datetime) -> str:
    return _utc(now).strftime("%Y-%m-%d")


def _day_start(now: datetime) -> datetime:
    t = _utc(now)
    return t.replace(hour=0, minute=0, second=0, microsecond=0)


def expires_at(now: datetime) -> datetime:
    """Fin exclusive de J+2 (visible le jour J, J+1 et J+2)."""
    return _day_start(now) + timedelta(days=WATCH_EXPIRE_DAYS + 1)


def expired(entry: dict[str, Any] | None, now: datetime | None = None) -> bool:
    if not entry:
        return True
    raw = entry.get("expires")
    if not raw:
        try:
            t = parse_iso(entry.get("t") or "")
        except Exception:
            return False
        return _utc(now) >= expires_at(t)
    try:
        return _utc(now) >= parse_iso(str(raw))
    except Exception:
        return False


def _arrival(clock: dict[str, Any], mark: dict[str, Any]) -> datetime | None:
    if mark.get("iso"):
        try:
            return parse_iso(mark["iso"])
        except Exception:
            pass
    if mark.get("tHours") is None:
        return None
    try:
        return parse_iso(clock["t0"]) + timedelta(hours=float(mark["tHours"]))
    except Exception:
        return None


def stops_in_window(
    clock: dict[str, Any] | None,
    now: datetime,
    *,
    before_days: int = WATCH_BEFORE_DAYS,
    after_days: int = WATCH_AFTER_DAYS,
) -> list[dict[str, Any]]:
    """Escales dont l'arrivée est dans [now − after ; now + before] wait:

    Fenêtre produit : de J-10 (10 j avant l'arrivée) à J+2 (2 j après).
    """
    if not clock:
        return []
    now_u = _utc(now)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mark in clock.get("marks") or []:
        if not isinstance(mark, dict):
            continue
        name = str(mark.get("name") or "").strip()
        if not name:
            continue
        when = _arrival(clock, mark)
        if when is None:
            continue
        start = when - timedelta(days=before_days)
        end = when + timedelta(days=after_days)
        if now_u < start or now_u > end:
            continue
        key = slug(name)
        if key in seen:
            continue
        seen.add(key)
        item = {
            "name": name,
            "slug": key,
            "arrival": when,
            "lat": mark.get("lat"),
            "lon": mark.get("lon"),
            "url": mark.get("url"),
        }
        out.append(item)
    return out


def _cache_get(ns: str, key: str, max_age_s: float | None = None) -> dict[str, Any] | None:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(ns, key, max_age_s)
    val = (hit or {}).get("value")
    return val if isinstance(val, dict) else None


def _cache_put(ns: str, key: str, value: Any) -> None:
    import pearl_store  # noqa: PLC0415

    pearl_store.kv_put(ns, key, value)


def _index_key(day: str) -> str:
    return f"index:{day}"


def _index_get(day: str) -> list[dict[str, Any]]:
    import pearl_store  # noqa: PLC0415

    hit = pearl_store.kv_get(WATCH_NS, _index_key(day))
    val = (hit or {}).get("value")
    if isinstance(val, list):
        return [e for e in val if isinstance(e, dict)]
    return []


def _index_put(day: str, entry: dict[str, Any]) -> None:
    rows = [e for e in _index_get(day) if e.get("id") != entry.get("id")]
    rows.append(entry)
    _cache_put(WATCH_NS, _index_key(day), rows)


def watch_cache_key(name: str, now: datetime) -> str:
    return f"{slug(name)}:{_day(now)}"


def _first_url(results: list[Any]) -> str | None:
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def _fallback_sentence(results: list[Any], facts: Any) -> str:
    for item in results:
        if not isinstance(item, dict):
            continue
        raw = item.get("content") or item.get("title") or ""
        if not isinstance(raw, str) or not raw.strip():
            continue
        first = raw.strip().split("\n")[0].strip()
        cleaned, _ = filter_numbers(first, facts)
        if cleaned:
            return cleaned.split(".")[0].strip()
    return ""


async def _summarize(
    system: str,
    user: str,
    facts: Any,
    fallback: str,
    *,
    client: httpx.AsyncClient | None,
) -> tuple[str, str]:
    if not llm_budget.allow("fast"):
        text, _ = filter_numbers(fallback, facts)
        return (text or "").strip(), "budget"
    try:
        text, source = await cascade_text(
            system, user, client, tier="fast", fallback=fallback or "",
            facts=facts, max_tokens=80,
        )
    except Exception as exc:
        log.debug("résumé veille/enrich : %s", exc)
        text, _ = filter_numbers(fallback, facts)
        return (text or "").strip(), "rules"
    cleaned, _ = filter_numbers(text or "", facts)
    out = (cleaned or "").strip()
    if not out:
        out, _ = filter_numbers(fallback, facts)
        out = (out or "").strip()
        if source not in {"budget", "rules"}:
            source = "rules"
    # Une phrase : on coupe au premier point final.
    if "." in out:
        out = out.split(".")[0].strip()
    return out, source


async def search_watch(
    port: str,
    *,
    include_domains: Iterable[str] | None = None,
    now: datetime | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Un search Tavily par (escale, jour). Cache ns `watch`."""
    when = _utc(now)
    key = watch_cache_key(port, when)
    hit = _cache_get(WATCH_NS, key)
    if hit and "results" in hit:
        return {**hit, "cached": True}
    empty = {"results": [], "credits": 0, "cached": False, "query": watch_query(port)}
    if not tavily_client.api_key():
        return {**empty, "reason": "no-key"}
    if not llm_budget.allow_tavily():
        return {**empty, "reason": "budget"}
    data = await tavily_client.search(
        watch_query(port),
        topic="news",
        days=SEARCH_DAYS,
        max_results=SEARCH_MAX,
        include_domains=include_domains,
        client=client,
    )
    stored = {
        "results": data.get("results") or [],
        "credits": data.get("credits") or 0,
        "query": watch_query(port),
        "day": _day(when),
    }
    _cache_put(WATCH_NS, key, stored)
    return {**stored, "cached": False}


def news_entry(
    stop: dict[str, Any],
    text: str,
    url: str | None,
    now: datetime,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    when = _utc(now)
    day = _day(when)
    name = str(stop.get("name") or "").strip()
    exp = expires_at(when)
    host = _host_of(url)
    entry: dict[str, Any] = {
        "id": f"news:{slug(name)}:{day}",
        "kind": "news",
        "t": to_iso(when.replace(hour=12, minute=0, second=0, microsecond=0)),
        "event": "watch",
        "name": name,
        "text": text,
        "url": url,
        "source": source or host,
        "expires": to_iso(exp),
        "title": {"fr": "Veille", "en": "Watch"},
        "facts": {"name": name, "day": day},
        "basis": "tavily",
    }
    lat, lon = stop.get("lat"), stop.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        entry["lat"] = round(float(lat), 4)
        entry["lon"] = round(float(lon), 4)
        entry["entity"] = {
            "kind": "escale",
            "name": name,
            "lat": round(float(lat), 4),
            "lon": round(float(lon), 4),
            "url": url,
        }
    return {k: v for k, v in entry.items() if v is not None}


async def watch_stop(
    stop: dict[str, Any],
    now: datetime,
    *,
    include_domains: Iterable[str] | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Veille d'une escale : search (1 crédit / jour) + phrase + journal."""
    name = str(stop.get("name") or "").strip()
    if not name:
        return None
    domains = list(include_domains) if include_domains is not None else official_domains(
        name, [stop.get("url")] if stop.get("url") else None,
    )
    found = await search_watch(name, include_domains=domains or None, now=now, client=client)
    results = found.get("results") or []
    if found.get("reason") in {"no-key", "budget"} and not results:
        return None
    facts = {"port": name, "results": results}
    fallback = _fallback_sentence(results, facts)
    url = _first_url(results)
    if not results and not fallback:
        # Journée sans résultat : on mémorise le search (déjà en cache) sans
        # inventer une entrée journal.
        return None
    user = (
        f"Escale : {name}\n"
        f"Résultats Tavily (faits, ne pas inventer de chiffre) :\n"
        f"{results!r}\n\n"
        "Une phrase, sans chiffre nouveau."
    )
    sentence, source = await _summarize(
        WATCH_SYSTEM, user, facts, fallback, client=client,
    )
    if not sentence:
        return None
    entry = news_entry(stop, sentence, url, now, source=source)
    try:
        import voyage_journal  # noqa: PLC0415

        voyage_journal.record_news(entry)
    except Exception as exc:
        log.debug("journal news : %s", exc)
    _index_put(_day(now), entry)
    return entry


async def run_daily_watch(
    voy: dict[str, Any] | None,
    now: datetime | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Tâche quotidienne : une veille par escale dans la fenêtre J-10 → J+2."""
    when = _utc(now)
    clock = (voy or {}).get("clock") if isinstance(voy, dict) else None
    stops = stops_in_window(clock, when)
    if not stops:
        return {"watched": 0, "wrote": 0, "skipped": True, "reason": "no-stop"}
    if not tavily_client.api_key():
        return {"watched": 0, "wrote": 0, "skipped": True, "reason": "no-key"}
    wrote = 0
    for stop in stops:
        try:
            entry = await watch_stop(stop, when, client=client)
        except Exception as exc:
            log.debug("veille %s : %s", stop.get("name"), exc)
            continue
        if entry:
            wrote += 1
    return {"watched": len(stops), "wrote": wrote, "skipped": False}


def enrich_key(item: dict[str, Any] | None) -> str | None:
    if not isinstance(item, dict):
        return None
    for raw in (item.get("url"), item.get("visit_url"), item.get("manager_url")):
        if isinstance(raw, str) and raw.startswith("http"):
            return raw.strip()
    return None


def _enrich_day_count(day: str | None = None) -> int:
    hit = _cache_get(ENRICH_NS, f"day-count:{day or _day(_utc())}")
    try:
        return int((hit or {}).get("n") or 0)
    except (TypeError, ValueError):
        return 0


def _enrich_day_inc(day: str | None = None) -> None:
    d = day or _day(_utc())
    _cache_put(ENRICH_NS, f"day-count:{d}", {"n": _enrich_day_count(d) + 1})


def enrich_daily_cap() -> int:
    import os  # noqa: PLC0415

    raw = (os.environ.get("NAVIGUIDE_ENRICH_DAILY") or "").strip()
    if not raw:
        return ENRICH_DAILY_CAP
    try:
        return max(0, int(raw))
    except ValueError:
        return ENRICH_DAILY_CAP


async def enrich_entity(
    item: dict[str, Any],
    *,
    client: httpx.AsyncClient | None = None,
    extract: bool = True,
) -> dict[str, Any] | None:
    """Phrase sourcée, une fois, cache définitif. Sans URL : rien."""
    url = enrich_key(item)
    if not url:
        return item.get("enrich") if isinstance(item.get("enrich"), dict) else None
    hit = _cache_get(ENRICH_NS, url)
    if hit and hit.get("text"):
        item["enrich"] = hit
        return hit
    if not extract:
        return None
    if not tavily_client.api_key() or not llm_budget.allow_tavily():
        return None
    if _enrich_day_count() >= enrich_daily_cap():
        return None
    data = await tavily_client.extract([url], depth="basic", client=client)
    _enrich_day_inc()
    raw = (data.get("text") or "")[:MAX_EXTRACT_CHARS]
    facts = {"name": item.get("name"), "url": url, "extract": raw}
    fallback = ""
    if raw:
        fallback, _ = filter_numbers(raw.split("\n")[0].strip(), facts)
    user = (
        f"Entité : {item.get('name') or ''}\n"
        f"URL : {url}\n"
        f"Extrait officiel :\n{raw}\n\n"
        "Une phrase sourcée, sans chiffre nouveau."
    )
    sentence, source = await _summarize(
        ENRICH_SYSTEM, user, facts, fallback or "", client=client,
    )
    if not sentence:
        return None
    stored = {"text": sentence, "url": url, "source": source}
    _cache_put(ENRICH_NS, url, stored)
    item["enrich"] = stored
    return stored


def _science_items(bag: dict[str, Any]) -> list[dict[str, Any]]:
    sci = bag.get("science")
    if isinstance(sci, dict):
        items = sci.get("nearby") or []
    elif isinstance(sci, list):
        items = sci
    else:
        items = []
    return [it for it in items if isinstance(it, dict)]


async def enrich_bag(
    bag: dict[str, Any],
    *,
    client: httpx.AsyncClient | None = None,
    extract: bool = True,
) -> dict[str, Any]:
    for item in _science_items(bag):
        try:
            await enrich_entity(item, client=client, extract=extract)
        except Exception as exc:
            log.debug("enrich science : %s", exc)
    for item in bag.get("projects") or []:
        if not isinstance(item, dict):
            continue
        try:
            await enrich_entity(item, client=client, extract=extract)
        except Exception as exc:
            log.debug("enrich projet : %s", exc)
    return bag


def attach_cached_news(bag: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    when = _utc(now)
    seen = {n.get("id") for n in (bag.get("news") or []) if isinstance(n, dict)}
    extra: list[dict[str, Any]] = []
    for delta in (0, 1, 2):
        day = (when - timedelta(days=delta)).strftime("%Y-%m-%d")
        for entry in _index_get(day):
            if expired(entry, when) or entry.get("id") in seen:
                continue
            seen.add(entry.get("id"))
            extra.append(entry)
    if extra:
        bag["news"] = list(bag.get("news") or []) + extra
    return bag


def attach_cached(bag: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Lecture seule du cache (pas de réseau) : news du jour + phrases enrich."""
    attach_cached_news(bag, now)
    for item in _science_items(bag) + [p for p in (bag.get("projects") or []) if isinstance(p, dict)]:
        url = enrich_key(item)
        if not url:
            continue
        hit = _cache_get(ENRICH_NS, url)
        if hit and hit.get("text"):
            item["enrich"] = hit
    return bag


async def run_daily_enrich(
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Parcourt les perles riches : extract une fois par URL officielle."""
    import pearl_store  # noqa: PLC0415
    from ici_engine import thin_cache_put  # noqa: PLC0415

    if not tavily_client.api_key():
        return {"entities": 0, "wrote": 0, "skipped": True, "reason": "no-key"}
    wrote = 0
    seen = 0
    for key, row in pearl_store.iter_pearls("rich"):
        bag = row.get("bag")
        if not isinstance(bag, dict):
            continue
        before = {
            enrich_key(it)
            for it in _science_items(bag) + list(bag.get("projects") or [])
            if isinstance(it, dict) and isinstance((it.get("enrich") or {}).get("text"), str)
        }
        await enrich_bag(bag, client=client, extract=True)
        after = {
            enrich_key(it)
            for it in _science_items(bag) + list(bag.get("projects") or [])
            if isinstance(it, dict) and isinstance((it.get("enrich") or {}).get("text"), str)
        }
        seen += len(_science_items(bag)) + len(bag.get("projects") or [])
        if after - before:
            wrote += len(after - before)
            try:
                lat, lon = float(key.split(":")[0]), float(key.split(":")[1])
            except Exception:
                lat = lon = None
            thin_cache_put(key, bag, "rich", lat, lon)
    return {"entities": seen, "wrote": wrote, "skipped": False}


async def run_daily(
    voy: dict[str, Any] | None = None,
    now: datetime | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Veille des escales + enrichissement des perles (une passe)."""
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415

    trip = voy if voy is not None else load_voyage(OFFICIAL_VOYAGE_ID)
    watch = await run_daily_watch(trip, now, client=client)
    enrich = await run_daily_enrich(client=client)
    return {"watch": watch, "enrich": enrich}

"""Pré-génération des perles along de la route officielle (plan §1.3 ; lot P).

Le film joue à 15–175 nm/s ; un sac `/ici` met 1–8 s. Les événements du film
viennent donc des perles — les mêmes pour tous les visiteurs. Ce module :

- garde les perles dans la base embarquée (`pearl_store`, SQLite dans
  `voyage_data/`), rechargées à la demande ; l'ancien `ici_thin_cache.json`
  est migré une fois au démarrage ;
- au démarrage, **chauffe** les perles **riches** de la route officielle
  (toutes les couches sans horodatage : ZEE, ports d'entrée, AMP, ports,
  projets, fiches science, mouillages, balisage, EMODnet), une tous les
  SAMPLE_NM (12 nm), à un rythme doux (1 perle / WARM_PAUSE_S) —
  MarineRegions et Overpass ne sont appelés qu'une fois par cellule.

`NAVIGUIDE_ICI_WARM=0` désactive le chauffeur (tests, dev sans réseau).
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("naviguide-simulator.ici-warm")

SAMPLE_NM = 12.0
# A rich pearl costs ~4-8 s upstream (MarineRegions + BI + Overpass + EMODnet);
# the pause on top keeps Overpass at well under one request a second.
WARM_PAUSE_S = float(os.environ.get("NAVIGUIDE_ICI_WARM_PAUSE_S") or 1.0)
WARM_PARALLEL = max(1, int(os.environ.get("NAVIGUIDE_ICI_WARM_PARALLEL") or 2))
LEGACY_TTL_S = 7 * 86400.0
POE_NEARBY_NM = 15.0  # a port of entry this close to a pearl was "passed" (journal, lot A)

_state: dict[str, Any] = {
    "status": "idle",  # idle | running | done | disabled | error
    "kind": "rich",
    "total": 0,
    "done": 0,
    "cached": 0,
    "errors": 0,
    "startedAt": None,
    "finishedAt": None,
}


def cache_path() -> Path:
    """The former JSON cache — only read once, to migrate it into SQLite."""
    from voyage_store import voyage_dir
    return voyage_dir() / "ici_thin_cache.json"


def warm_enabled() -> bool:
    return (os.environ.get("NAVIGUIDE_ICI_WARM") or "1").strip() not in ("0", "false", "no")


def stories_enabled() -> bool:
    """Pre-generation of the LLM stories after the pearls (lot F); off in tests."""
    return (os.environ.get("NAVIGUIDE_STORY_PREGEN") or "1").strip() not in ("0", "false", "no")


def status() -> dict[str, Any]:
    import llm_budget  # noqa: PLC0415
    import pearl_store  # noqa: PLC0415
    return {**_state, "store": pearl_store.info(), "llm": llm_budget.status()}


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _wrap_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def sample_route_nm(points: list[dict], step_nm: float = SAMPLE_NM) -> list[dict]:
    """Pearls every `step_nm` along the sea points, interpolated inside long
    segments (the official route has ~32 nm between points). Land legs and
    air hops are skipped; each sea stretch starts with its own pearl.
    Each pearl carries `sailNm` on the **clock's scale** — the route point's
    `cumNm` (which counts the land leg Saint-Maur → La Rochelle, as the clock
    does), interpolated inside a segment. Without `cumNm`, sea miles are
    accumulated from the first sea point."""
    out: list[dict] = []
    if not points:
        return out
    prev = None
    prev_cum = 0.0
    carry = 0.0  # distance since the last pearl
    sail = 0.0   # accumulated sea miles (fallback scale)
    for p in points:
        try:
            lat, lon = float(p["lat"]), float(p["lon"])
        except Exception:
            continue
        if p.get("nonMaritime") or p.get("jump"):
            prev = None
            continue
        cum = p.get("cumNm")
        cum = float(cum) if isinstance(cum, (int, float)) else None
        if prev is None:
            base = cum if cum is not None else sail
            out.append({"lat": lat, "lon": _wrap_lon(lon), "sailNm": round(base, 2)})
            carry = 0.0
            prev = (lat, lon)
            prev_cum = base
            continue
        seg = _haversine_nm(prev[0], prev[1], lat, lon)
        if seg <= 0:
            continue
        pos = step_nm - carry  # distance along this segment to the next pearl
        while pos <= seg:
            t = pos / seg
            out.append({
                "lat": prev[0] + (lat - prev[0]) * t,
                "lon": _wrap_lon(prev[1] + (lon - prev[1]) * t),
                "sailNm": round(prev_cum + pos, 2),
            })
            pos += step_nm
        carry = seg - (pos - step_nm)
        sail += seg
        prev = (lat, lon)
        prev_cum = cum if cum is not None else prev_cum + seg
    return out


def sample_route(points: list[dict], step_nm: float = SAMPLE_NM) -> list[tuple[float, float]]:
    """Positions only (warmer, GET /ici/pearls)."""
    return [(p["lat"], p["lon"]) for p in sample_route_nm(points, step_nm)]


def route_events_from_pearls(points: list[dict]) -> list[dict]:
    """What the warmed pearls know about the route, in order: ZEE entered /
    left, marine protected areas that come within reach, ports of entry
    passed (≤ POE_NEARBY_NM). Pearls not cached yet are unknown — no event
    is invented across a gap.

    Each event: { kind: "zee" | "amp" | "poe", event, name, mrgid | siteId |
    poeId, lat, lon, sailNm, idx }. The journal dates `sailNm` with the clock."""
    from ici_engine import thin_cache_get, thin_cache_key  # noqa: PLC0415

    events: list[dict] = []
    state: dict | None = None      # confirmed ZEE (None = high seas)
    state_known = False
    candidate: tuple | None = None  # (zee_or_None, pearl, idx) seen once, waiting for a second pearl
    seen_amp: set[str] = set()
    seen_poe: set[str] = set()
    for idx, pearl in enumerate(sample_route_nm(points)):
        bag = thin_cache_get(thin_cache_key(pearl["lat"], pearl["lon"], 30.0))
        if bag is None:
            state_known = False
            candidate = None
            continue
        zee = bag.get("zee") or None
        mrgid = zee.get("mrgid") if isinstance(zee, dict) else None
        ashore = bool(isinstance(zee, dict) and (zee.get("ashore") or str(zee.get("name", "")).startswith("À terre")))
        cur = None if (mrgid is None or ashore) else {"mrgid": mrgid, "name": zee.get("name"), "territory": zee.get("territory")}
        cur_id = cur["mrgid"] if cur else None
        state_id = state["mrgid"] if state else None
        # Ports of entry within reach of the pearl (lot A): once per port.
        for poe in (bag.get("poe") or [])[:3]:
            if not isinstance(poe, dict) or not poe.get("name"):
                continue
            nm = poe.get("nm")
            if not isinstance(nm, (int, float)) or nm > POE_NEARBY_NM:
                continue
            key = str(poe.get("id") or poe.get("site_id") or poe["name"])
            if key in seen_poe:
                continue
            seen_poe.add(key)
            events.append({
                "kind": "poe", "event": "passed", "name": poe["name"], "poeId": key,
                "nm": nm, "url": poe.get("url"), "mrgid": cur_id,
                "lat": round(pearl["lat"], 4), "lon": round(pearl["lon"], 4), "sailNm": pearl["sailNm"], "idx": idx, "basis": "pearl",
            })
        if not state_known:
            state, state_known, candidate = cur, True, None
        elif cur_id == state_id:
            candidate = None
        elif candidate is not None and (candidate[0]["mrgid"] if candidate[0] else None) == cur_id:
            # Two consecutive pearls agree (≥ 24 nm): a real crossing, not a
            # gazetteer flap along a boundary. Dated at the first of the two.
            first_pearl, first_idx = candidate[1], candidate[2]
            base = {"lat": round(first_pearl["lat"], 4), "lon": round(first_pearl["lon"], 4), "sailNm": first_pearl["sailNm"], "idx": first_idx, "basis": "pearl"}
            if state is not None:
                events.append({"kind": "zee", "event": "exit", "name": state["name"], "mrgid": state_id, "territory": state.get("territory"), **base})
            if cur is not None:
                events.append({"kind": "zee", "event": "enter", "name": cur["name"], "mrgid": cur_id, "territory": cur.get("territory"), **base})
            state, candidate = cur, None
        else:
            candidate = (cur, pearl, idx)
        for amp in (bag.get("amp") or [])[:2]:
            if not isinstance(amp, dict) or not amp.get("name"):
                continue
            key = str(amp.get("site_id") or amp.get("id") or amp["name"])
            if key in seen_amp:
                continue
            seen_amp.add(key)
            events.append({
                "kind": "amp", "event": "nearby", "name": amp["name"], "siteId": key,
                "nm": amp.get("nm"), "visitUrl": amp.get("visit_url") or amp.get("url"),
                "lat": round(pearl["lat"], 4), "lon": round(pearl["lon"], 4), "sailNm": pearl["sailNm"], "idx": idx, "basis": "pearl",
            })
    return events


# ── store ───────────────────────────────────────────────────────────────────

def load_cache_from_disk() -> int:
    """Startup: migrate the former JSON cache into SQLite (once). The store
    itself needs no loading — the engine reads it on demand."""
    import pearl_store  # noqa: PLC0415
    return pearl_store.import_legacy_json(cache_path(), LEGACY_TTL_S)


# ── the warmer ────────────────────────────────────────────────────────────────

async def warm_official_route(pause_s: float = WARM_PAUSE_S, rich: bool = True) -> dict[str, Any]:
    """Collect the (rich) pearl of every sample of the official route, gently.
    Pearls already rich in the store are skipped; thin ones are upgraded."""
    from ici_engine import fill_dossier, thin_cache_get, thin_cache_key  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    points = (voy or {}).get("points") or []
    pearls = sample_route(points)
    _state.update({
        "status": "running", "kind": "rich" if rich else "thin", "total": len(pearls),
        "done": 0, "cached": 0, "errors": 0, "startedAt": time.time(), "finishedAt": None,
    })
    if not pearls:
        _state["status"] = "done"
        _state["finishedAt"] = time.time()
        return status()
    month = None

    async def one(lat: float, lon: float) -> None:
        key = thin_cache_key(lat, lon, 30.0)
        if thin_cache_get(key, rich=rich) is not None:
            _state["cached"] += 1
            _state["done"] += 1
            return
        try:
            await fill_dossier(lat, lon, 30.0, month=month, thin=True, rich=rich)
        except Exception as exc:  # network hiccup: keep going
            _state["errors"] += 1
            log.debug("perle %.3f,%.3f : %s", lat, lon, exc)
        _state["done"] += 1
        await asyncio.sleep(pause_s)

    # The local ZEE layer first (lot B): pearls filled with it never flap,
    # and the pearls already stored get their ZEE re-read right away.
    try:
        import zee_local  # noqa: PLC0415
        if await zee_local.ensure_loaded():
            _state["zeeRefreshed"] = await refresh_zee_local()
    except Exception as exc:
        log.debug("ZEE locale au démarrage du chauffeur : %s", exc)
    # Two pearls in flight: a rich pearl waits ~8 s on Overpass + EMODnet +
    # BI; two at a time halves the first run without leaning on Overpass.
    for i in range(0, len(pearls), WARM_PARALLEL):
        await asyncio.gather(*(one(la, lo) for la, lo in pearls[i:i + WARM_PARALLEL]))
    try:
        _state["zeeRefreshed"] = await refresh_zee_local()
    except Exception as exc:
        log.debug("relecture ZEE locale : %s", exc)
    # Lot F: the stories of the route's events, written ahead of the film.
    if stories_enabled():
        try:
            import story_cache  # noqa: PLC0415
            _state["stories"] = await story_cache.pregenerate_official(points)
        except Exception as exc:
            log.debug("pré-génération des récits : %s", exc)
    _state["status"] = "done"
    _state["finishedAt"] = time.time()
    log.info("perles officielles chauffées (%s) : %d (%d déjà en base, %d erreurs)",
             _state["kind"], _state["done"], _state["cached"], _state["errors"])
    return status()


async def refresh_zee_local(pause_s: float = 0.2) -> int:
    """Re-read the ZEE of every stored pearl with the local VLIZ layer (lot B):
    pearls filled from the gazetteer keep their rich layers, only `zee`
    (and the ports of entry, which hang on the ZEE) change. Returns the
    number of pearls corrected. No-op while the layer is not loaded."""
    import pearl_store  # noqa: PLC0415
    import zee_local  # noqa: PLC0415
    from ici_engine import _poe_from_fc, _get_json, bi_base, thin_cache_put, zee_from_record  # noqa: PLC0415

    if not zee_local.status()["loaded"]:
        return 0
    import httpx  # noqa: PLC0415
    changed = 0
    async with httpx.AsyncClient() as http:
        for n, (key, row) in enumerate(list(pearl_store.iter_pearls())):
            if n % 25 == 0:
                await asyncio.sleep(0)  # let the API breathe between batches
            bag = row["bag"]
            if (bag.get("sources") or {}).get("zee") == "vliz-local":
                continue
            try:
                lat, lon = float(key.split(":")[0]), float(key.split(":")[1])
            except Exception:
                continue
            local = zee_local.zee_at(lat, lon)
            if local is zee_local.UNKNOWN:
                return changed
            new_zee = local if local is not None else zee_from_record(None)
            old = bag.get("zee") or {}
            bag["sources"] = {**(bag.get("sources") or {}), "zee": "vliz-local"}
            if (old.get("mrgid") != new_zee.get("mrgid")) or bool(old.get("ashore")) != bool(new_zee.get("ashore")):
                bag["zee"] = {**new_zee, "gold": bool(old.get("gold")) if old.get("mrgid") == new_zee.get("mrgid") else False}
                mrgid = new_zee.get("mrgid")
                if mrgid:
                    try:
                        data = await _get_json(http, f"{bi_base()}/poe/ports?mrgid={int(mrgid)}", timeout=4.0)
                        bag["poe"] = _poe_from_fc(data, lat, lon)
                    except Exception:
                        bag["poe"] = []
                else:
                    bag["poe"] = []
                changed += 1
                await asyncio.sleep(pause_s)
            thin_cache_put(key, bag, row["kind"], lat, lon)
    if changed:
        log.info("ZEE locale : %d perles corrigées", changed)
    return changed


_pearls_cache: dict[str, Any] = {"rev": None, "pearls": None}


def official_pearls() -> dict[str, Any]:
    """The canonical pearls of the official route: the client samples the
    same positions, so its thin bags hit the warmed cache."""
    from voyage_store import load_voyage  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    points = (voy or {}).get("points") or []
    rev = (voy or {}).get("routeRev"), len(points)
    if _pearls_cache["pearls"] is None or _pearls_cache["rev"] != rev:
        _pearls_cache["pearls"] = [[round(la, 5), round(lo, 5)] for la, lo in sample_route(points)]
        _pearls_cache["rev"] = rev
    return {
        "voyageId": OFFICIAL_VOYAGE_ID if voy else None,
        "stepNm": SAMPLE_NM,
        "count": len(_pearls_cache["pearls"]),
        "pearls": _pearls_cache["pearls"],
        "warm": status(),
    }


def start_background(loop: asyncio.AbstractEventLoop | None = None) -> bool:
    """Called at server startup. Never raises."""
    try:
        load_cache_from_disk()
    except Exception as exc:
        log.warning("rechargement du cache perles : %s", exc)
    if not warm_enabled():
        _state["status"] = "disabled"
        return False
    try:
        loop = loop or asyncio.get_event_loop()
        loop.create_task(warm_official_route())
        return True
    except Exception as exc:
        _state["status"] = "error"
        log.warning("chauffeur de perles non lancé : %s", exc)
        return False

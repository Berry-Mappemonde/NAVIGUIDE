"""Pré-génération des perles along de la route officielle (plan §1.3, forme minimale).

Le film joue à 15–175 nm/s ; un sac `/ici` met 1–8 s. Les événements du film
(ZEE, ports d'entrée, AMP, ports) viennent donc des perles thin — les mêmes
pour tous les visiteurs. Ce module :

- garde le cache des sacs thin **sur disque** (`voyage_data/ici_thin_cache.json`),
  rechargé au démarrage, écrit au plus toutes les 30 s ;
- au démarrage, **chauffe** les perles de la route officielle, une tous les
  ROUTE_SAMPLE_NM (12 nm), à un rythme doux (1 perle / WARM_PAUSE_S) —
  MarineRegions n'est appelé qu'une fois par cellule, jamais rafalé.

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
# A thin bag already costs ~4 s upstream (MarineRegions + BI); the pause on
# top keeps the whole route under ~4 h on a first run.
WARM_PAUSE_S = float(os.environ.get("NAVIGUIDE_ICI_WARM_PAUSE_S") or 0.5)
SAVE_EVERY_S = 30.0

_state: dict[str, Any] = {
    "status": "idle",  # idle | running | done | disabled | error
    "total": 0,
    "done": 0,
    "cached": 0,
    "errors": 0,
    "startedAt": None,
    "finishedAt": None,
}
_last_save = 0.0


def cache_path() -> Path:
    from voyage_store import voyage_dir
    return voyage_dir() / "ici_thin_cache.json"


def warm_enabled() -> bool:
    return (os.environ.get("NAVIGUIDE_ICI_WARM") or "1").strip() not in ("0", "false", "no")


def status() -> dict[str, Any]:
    return dict(_state)


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
    Each pearl carries `sailNm`, the sea miles from the first sea point (the
    same scale as the clock's `sailNm`)."""
    out: list[dict] = []
    if not points:
        return out
    prev = None
    carry = 0.0  # distance since the last pearl
    sail = 0.0   # sea miles so far
    for p in points:
        try:
            lat, lon = float(p["lat"]), float(p["lon"])
        except Exception:
            continue
        if p.get("nonMaritime") or p.get("jump"):
            prev = None
            continue
        if prev is None:
            out.append({"lat": lat, "lon": _wrap_lon(lon), "sailNm": round(sail, 2)})
            carry = 0.0
            prev = (lat, lon)
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
                "sailNm": round(sail + pos, 2),
            })
            pos += step_nm
        carry = seg - (pos - step_nm)
        sail += seg
        prev = (lat, lon)
    return out


def sample_route(points: list[dict], step_nm: float = SAMPLE_NM) -> list[tuple[float, float]]:
    """Positions only (warmer, GET /ici/pearls)."""
    return [(p["lat"], p["lon"]) for p in sample_route_nm(points, step_nm)]


def route_events_from_pearls(points: list[dict]) -> list[dict]:
    """What the warmed pearls know about the route, in order: ZEE entered /
    left, marine protected areas that come within reach. Pearls not cached
    yet are unknown — no event is invented across a gap.

    Each event: { kind: "zee" | "amp", event, name, mrgid | siteId, lat, lon,
    sailNm, idx }. The journal turns `sailNm` into a time with the clock."""
    from ici_engine import thin_cache_get, thin_cache_key  # noqa: PLC0415

    events: list[dict] = []
    state: dict | None = None      # confirmed ZEE (None = high seas)
    state_known = False
    candidate: tuple | None = None  # (zee_or_None, pearl, idx) seen once, waiting for a second pearl
    seen_amp: set[str] = set()
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


# ── disk persistence of the thin cache ────────────────────────────────────────

def load_cache_from_disk() -> int:
    from ici_engine import _thin_cache  # noqa: PLC0415
    path = cache_path()
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        log.warning("cache perles illisible (%s) : on repart de zéro", exc)
        return 0
    now = time.time()
    n = 0
    for key, hit in (data or {}).items():
        if not isinstance(hit, dict) or "bag" not in hit:
            continue
        if now - float(hit.get("ts") or 0) > 7 * 86400:
            continue
        _thin_cache[key] = {"ts": float(hit.get("ts") or now), "bag": hit["bag"]}
        n += 1
    log.info("cache perles : %d cellules rechargées", n)
    return n


def save_cache_to_disk(force: bool = False) -> bool:
    global _last_save
    from ici_engine import _thin_cache  # noqa: PLC0415
    if not force and time.time() - _last_save < SAVE_EVERY_S:
        return False
    path = cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_thin_cache, ensure_ascii=False, default=str))
        tmp.replace(path)
        _last_save = time.time()
        return True
    except Exception as exc:
        log.warning("cache perles non écrit : %s", exc)
        return False


# ── the warmer ────────────────────────────────────────────────────────────────

async def warm_official_route(pause_s: float = WARM_PAUSE_S) -> dict[str, Any]:
    """Collect the thin bag of every pearl of the official route, gently."""
    from ici_engine import fill_dossier, thin_cache_get, thin_cache_key  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    points = (voy or {}).get("points") or []
    pearls = sample_route(points)
    _state.update({
        "status": "running", "total": len(pearls), "done": 0, "cached": 0, "errors": 0,
        "startedAt": time.time(), "finishedAt": None,
    })
    if not pearls:
        _state["status"] = "done"
        _state["finishedAt"] = time.time()
        return status()
    month = None
    for lat, lon in pearls:
        key = thin_cache_key(lat, lon, 30.0)
        if thin_cache_get(key) is not None:
            _state["cached"] += 1
            _state["done"] += 1
            continue
        try:
            await fill_dossier(lat, lon, 30.0, month=month, thin=True)
        except Exception as exc:  # network hiccup: keep going
            _state["errors"] += 1
            log.debug("perle %.3f,%.3f : %s", lat, lon, exc)
        _state["done"] += 1
        save_cache_to_disk()
        await asyncio.sleep(pause_s)
    save_cache_to_disk(force=True)
    _state["status"] = "done"
    _state["finishedAt"] = time.time()
    log.info("perles officielles chauffées : %d (%d déjà en cache, %d erreurs)",
             _state["done"], _state["cached"], _state["errors"])
    return status()


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

"""Client atlas BI — GET /climatology/point (+ crossings).

kind: climatology. Zone fallback only if the API is dead / empty.
Never relabel the pack as forecast.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, Optional, Tuple

import httpx

from climatology_zones import zone_wind_at


def bi_base() -> str:
    return (os.getenv("BI_API_URL") or "http://127.0.0.1:8001/api").rstrip("/")

log = logging.getLogger("naviguide-simulator.atlas")

KIND = "climatology"
TIMEOUT_S = 4.0
DEAD_S = 45.0
CELL = 0.5
MAX_WORKERS = 8

_cache: dict[str, dict] = {}
_lock = threading.Lock()
_dead_until = 0.0


def reset_atlas_cache() -> None:
    global _dead_until
    with _lock:
        _cache.clear()
        _dead_until = 0.0


def _cell_key(lat: float, lon: float, month: int) -> str:
    la = round(round(float(lat) / CELL) * CELL, 4)
    lo = round(round(float(lon) / CELL) * CELL, 4)
    m = max(1, min(12, int(month or 1)))
    return f"{la}:{lo}:{m}"


def _mark_dead() -> None:
    global _dead_until
    _dead_until = time.time() + DEAD_S


def atlas_is_dead() -> bool:
    return time.time() < _dead_until


def _zone(lat: float, lon: float, month: int) -> Dict[str, Any]:
    pack = zone_wind_at(lat, lon, month)
    pack["source"] = "zone_fallback"
    pack["kind"] = KIND
    pack["period"] = None
    pack["doi"] = None
    return pack


def wind_from_point(payload: Optional[dict]) -> Optional[Dict[str, Any]]:
    if not payload or payload.get("kind") != KIND:
        return None
    rose = payload.get("wind_atlas") or {}
    block = rose.get("most_likely") or rose.get("vector_mean")
    if not isinstance(block, dict) or block.get("speed_knots") is None:
        return None
    try:
        speed = float(block["speed_knots"])
        direction = float(block.get("dir_deg") or 0)
    except (TypeError, ValueError):
        return None
    wave = payload.get("wave") or {}
    current = payload.get("current") or {}
    cyclone = payload.get("cyclone") or {}
    return {
        "speedKnots": speed,
        "dirFromDeg": direction,
        "source": "atlas",
        "kind": KIND,
        "period": payload.get("period") or (payload.get("periods") or {}).get("wind"),
        "doi": payload.get("doi"),
        "periods": payload.get("periods"),
        "provenance": payload.get("provenance"),
        "hs": wave.get("hs_p90_m") if wave.get("hs_p90_m") is not None else wave.get("hs_p50_m"),
        "hsP50": wave.get("hs_p50_m"),
        "hsP90": wave.get("hs_p90_m"),
        "currentKn": current.get("speed_knots"),
        "currentToDeg": current.get("direction_to_deg"),
        "cycloneNearby": cyclone.get("nearby"),
        "crossings": cyclone.get("crossings_if_leg"),
        "point": payload,
    }


def _get_json(url: str, params: dict, client: httpx.Client | None = None) -> Any:
    own = client is None
    http = client or httpx.Client(timeout=TIMEOUT_S)
    try:
        r = http.get(url, params=params, headers={"Accept": "application/json"}, timeout=TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            http.close()


def fetch_atlas_point(
    lat: float,
    lon: float,
    month: int,
    dest_lat: float | None = None,
    dest_lon: float | None = None,
    day: int | None = None,
    client: httpx.Client | None = None,
) -> Optional[dict]:
    if atlas_is_dead():
        return None
    params: dict[str, Any] = {"lat": lat, "lon": lon, "month": int(month)}
    if dest_lat is not None and dest_lon is not None:
        params["dest_lat"] = dest_lat
        params["dest_lon"] = dest_lon
    if day is not None:
        params["day"] = day
    try:
        return _get_json(f"{bi_base()}/climatology/point", params, client)
    except Exception as exc:
        log.info("atlas point down: %s", exc)
        _mark_dead()
        return None


def fetch_atlas_crossings(
    lat1: float, lon1: float, lat2: float, lon2: float, month: int,
    day: int | None = None,
    client: httpx.Client | None = None,
) -> Optional[dict]:
    if atlas_is_dead():
        return None
    params: dict[str, Any] = {
        "lat1": lat1, "lon1": lon1, "lat2": lat2, "lon2": lon2, "month": int(month),
    }
    if day is not None:
        params["day"] = day
    try:
        return _get_json(f"{bi_base()}/climatology/crossings", params, client)
    except Exception as exc:
        log.info("atlas crossings down: %s", exc)
        return None


def atlas_wind_at(
    lat: float,
    lon: float,
    month: int,
    client: httpx.Client | None = None,
) -> Dict[str, Any]:
    key = _cell_key(lat, lon, month)
    with _lock:
        hit = _cache.get(key)
    if hit is not None:
        return hit["wind"] if hit.get("wind") else _zone(lat, lon, month)
    payload = fetch_atlas_point(lat, lon, month, client=client)
    wind = wind_from_point(payload)
    with _lock:
        _cache[key] = {"point": payload, "wind": wind}
    return wind if wind else _zone(lat, lon, month)


def atlas_wind_at_dt(lat: float, lon: float, t) -> Dict[str, Any]:
    return atlas_wind_at(lat, lon, t.month)


def prefetch_atlas_cells(cells: Iterable[Tuple[float, float, int]]) -> int:
    """Warm the cache. Returns how many atlas hits landed."""
    todo = []
    seen = set()
    for lat, lon, month in cells:
        key = _cell_key(lat, lon, month)
        if key in seen:
            continue
        seen.add(key)
        with _lock:
            if key in _cache:
                continue
        todo.append((lat, lon, month, key))
    if not todo or atlas_is_dead():
        return 0
    hits = 0

    def one(item):
        la, lo, m, key = item
        payload = fetch_atlas_point(la, lo, m)
        wind = wind_from_point(payload)
        with _lock:
            _cache[key] = {"point": payload, "wind": wind}
        return 1 if wind else 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = [pool.submit(one, item) for item in todo]
        for fut in as_completed(futs):
            try:
                hits += int(fut.result())
            except Exception:
                pass
    return hits


def prefetch_points(points: list, months: Iterable[int]) -> int:
    cells = []
    seen = set()
    for p in points or []:
        if p.get("jump") or p.get("nonMaritime"):
            continue
        key = (round(float(p["lat"]) * 2) / 2, round(float(p["lon"]) * 2) / 2)
        if key in seen:
            continue
        seen.add(key)
        for m in months:
            cells.append((p["lat"], p["lon"], int(m)))
    return prefetch_atlas_cells(cells)


def climatology_block(
    lat: float,
    lon: float,
    month: int,
    dest_lat: float | None = None,
    dest_lon: float | None = None,
    client: httpx.Client | None = None,
) -> dict:
    """Full /point (+ crossings) for ICI / later analysis."""
    point = fetch_atlas_point(lat, lon, month, dest_lat, dest_lon, client=client)
    crossings = None
    if dest_lat is not None and dest_lon is not None:
        crossings = fetch_atlas_crossings(lat, lon, dest_lat, dest_lon, month, client=client)
    wind = wind_from_point(point)
    if wind:
        if crossings and isinstance(point, dict):
            cyc = dict(point.get("cyclone") or {})
            cyc["crossings_if_leg"] = crossings
            point = {**point, "cyclone": cyc, "crossings": crossings}
        return {
            "kind": KIND,
            "source": "atlas",
            "month": month,
            "period": point.get("period") if point else None,
            "doi": point.get("doi") if point else None,
            "periods": point.get("periods") if point else None,
            "provenance": point.get("provenance") if point else None,
            "point": point,
            "crossings": crossings or (point.get("cyclone") or {}).get("crossings_if_leg"),
            "wind": {
                "speedKnots": wind["speedKnots"],
                "dirFromDeg": wind["dirFromDeg"],
                "kind": KIND,
                "source": "atlas",
            },
        }
    zone = _zone(lat, lon, month)
    return {
        "kind": KIND,
        "source": "zone_fallback" if point is None else "empty",
        "month": month,
        "period": None,
        "doi": None,
        "point": point,
        "crossings": crossings,
        "wind": zone,
    }

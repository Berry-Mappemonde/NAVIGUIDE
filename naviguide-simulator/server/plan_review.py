"""Revue de plan par règles (lot K, plan général §1.8).

Par jambe de la route officielle (d'une escale à la suivante), ce que les
données déjà collectées disent — rien d'autre :

- calendrier : départ, arrivée, jours de mer, jours à quai à l'arrivée
  (horloge officielle) ;
- formalités : ZEE traversées et leurs ports d'entrée officiels, dossier
  Gold présent ou non (perles chauffées ; une perle inconnue = trou compté,
  pas deviné) ;
- aires marines protégées à portée sur la jambe (perles).

La saison (rose des vents, cyclones IBTrACS) est lue côté client dans le
cache de l'atlas, pour le mois de la jambe. Aucun LLM ici.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from voyage_clock import parse_iso, to_iso


def _sail_nm_at(clock: dict, t_hours: float) -> float:
    """Sea miles of the clock at `t_hours` (the pearls are indexed in sea miles)."""
    best = None
    for v in clock.get("vertices") or []:
        if abs(float(v.get("tHours") or 0) - t_hours) < 1e-6:
            best = v
            break
    if best is None:
        return 0.0
    return float(best.get("sailNm") or 0)


def legs_from_clock(clock: dict, start_name: str | None = None) -> list[dict]:
    """Consecutive stops → legs with sea-mile bounds and dates. The clock's
    marks are the arrivals; the departure is the first vertex."""
    marks = [m for m in (clock.get("marks") or []) if m.get("name") and m.get("tHours") is not None]
    marks.sort(key=lambda m: float(m.get("tHours") or 0))
    verts = clock.get("vertices") or []
    if not verts:
        return []
    # The vertex from which the boat sails (the land leg before it counts
    # miles too, but on wheels): its miles and hour open the first leg.
    sea_start = verts[0]
    for a, b in zip(verts, verts[1:]):
        if b.get("vehicle") in ("main", "side"):
            sea_start = a
            break
    start = {"name": start_name or clock.get("startAt") or "Départ", "tHours": float(sea_start.get("tHours") or 0),
             "holdHours": 0, "_sailNm": float(sea_start.get("sailNm") or 0)}
    if not marks or abs(float(marks[0]["tHours"]) - start["tHours"]) > 1e-6:
        marks = [start] + marks
    t0 = parse_iso(clock["t0"])
    legs = []
    for a, b in zip(marks, marks[1:]):
        dep = t0 + timedelta(hours=float(a["tHours"]) + float(a.get("holdHours") or 0))
        arr = t0 + timedelta(hours=float(b["tHours"]))
        from_nm = a["_sailNm"] if "_sailNm" in a else (
            _sail_nm_at(clock, float(a["tHours"]) + float(a.get("holdHours") or 0)) or _sail_nm_at(clock, float(a["tHours"])))
        to_nm = _sail_nm_at(clock, float(b["tHours"]))
        if to_nm <= from_nm + 0.5:
            continue  # an air hop or a land leg: nothing to sail
        legs.append({
            "from": a["name"], "to": b["name"],
            "departIso": to_iso(dep), "arriveIso": to_iso(arr),
            "daysAtSea": round(max(0.0, (arr - dep).total_seconds()) / 86400, 1),
            "holdDays": round(float(b.get("holdHours") or 0) / 24),
            "fromNm": from_nm, "toNm": to_nm, "legNm": round(to_nm - from_nm),
            "month": arr.month,
        })
    return legs


SEASON_SAMPLES = 3
SEASON_BUDGET_S = 6.0


def _leg_sample_points(clock: dict, leg: dict, n: int = SEASON_SAMPLES) -> list[tuple[float, float]]:
    verts = [v for v in (clock.get("vertices") or [])
             if v.get("lat") is not None and leg["fromNm"] - 0.5 <= float(v.get("sailNm") or 0) <= leg["toNm"] + 0.5]
    if not verts:
        return []
    step = max(1, len(verts) // n)
    return [(float(v["lat"]), float(v["lon"])) for v in verts[::step][:n]]


def season_for_leg(clock: dict, leg: dict, *, budget_deadline: float | None = None) -> dict[str, Any]:
    """The month's climatology on the leg, from the BI atlas (server cache,
    zone fallback never counted as data): worst gale %, most cyclone tracks
    nearby, cells read / missing."""
    import time  # noqa: PLC0415
    from climatology_atlas import atlas_wind_at  # noqa: PLC0415

    gale = cyc = None
    cells = missing = 0
    for lat, lon in _leg_sample_points(clock, leg):
        if budget_deadline is not None and time.monotonic() > budget_deadline:
            missing += 1
            continue
        try:
            w = atlas_wind_at(lat, lon, int(leg["month"]))
        except Exception:
            w = None
        point = (w or {}).get("point") if isinstance(w, dict) else None
        if not point or (w or {}).get("source") != "atlas":
            missing += 1
            continue
        cells += 1
        rose = point.get("rose") or {}
        g = rose.get("gale_pct", (point.get("wind_atlas") or {}).get("gale_pct"))
        if isinstance(g, (int, float)):
            gale = max(gale or 0.0, float(g))
        c = (point.get("cyclone") or {}).get("nearby")
        if isinstance(c, (int, float)):
            cyc = max(cyc or 0, int(c))
    return {"galePct": gale, "cyclones": cyc, "cells": cells, "missing": missing, "month": leg["month"], "source": "atlas" if cells else None}


def review_official(voy: dict, now: datetime | None = None, *, season: bool = True) -> dict[str, Any]:
    import time  # noqa: PLC0415
    from ici_engine import thin_cache_get, thin_cache_key  # noqa: PLC0415
    from ici_warm import route_events_from_pearls, sample_route_nm  # noqa: PLC0415

    clock = voy.get("clock") or {}
    points = voy.get("points") or []
    # The sea start is the stop at the clock's first vertex (La Rochelle: the
    # Saint-Maur → La Rochelle leg is land and has no vertex at sea).
    start_name = None
    verts = clock.get("vertices") or []
    if verts:
        # Same sea-start vertex as legs_from_clock: name it from the marks.
        sea_start = verts[0]
        for a, b in zip(verts, verts[1:]):
            if b.get("vehicle") in ("main", "side"):
                sea_start = a
                break
        film0 = float(sea_start.get("filmNm") or 0)
        best = None
        for m in voy.get("marks") or []:
            if not m.get("name"):
                continue
            d = abs(float(m.get("filmNm", m.get("nm")) or 0) - film0)
            if best is None or d < best[0]:
                best = (d, m["name"])
        if best and best[0] <= 1.0:
            start_name = best[1]
    legs = legs_from_clock(clock, start_name) if clock.get("t0") else []
    pearls = sample_route_nm(points)
    events = route_events_from_pearls(points) if pearls else []

    # Pearls known / unknown per leg, and the ZEE seen on the leg (by pearl).
    for leg in legs:
        zees: dict[Any, dict] = {}
        known = unknown = 0
        for p in pearls:
            if not (leg["fromNm"] - 0.5 <= p["sailNm"] <= leg["toNm"] + 0.5):
                continue
            bag = thin_cache_get(thin_cache_key(p["lat"], p["lon"], 30.0))
            if bag is None:
                unknown += 1
                continue
            known += 1
            z = bag.get("zee") or {}
            mrgid = z.get("mrgid")
            if mrgid and not z.get("ashore"):
                cur = zees.setdefault(mrgid, {"mrgid": mrgid, "name": z.get("name"), "gold": bool(z.get("gold")), "poe": set()})
                cur["gold"] = cur["gold"] or bool(z.get("gold"))
                for poe in (bag.get("poe") or [])[:4]:
                    if isinstance(poe, dict) and poe.get("name"):
                        cur["poe"].add(poe["name"])
        amps = {e["siteId"] for e in events if e["kind"] == "amp" and leg["fromNm"] - 0.5 <= e["sailNm"] <= leg["toNm"] + 0.5}
        leg["pearls"] = {"known": known, "unknown": unknown}
        leg["zees"] = [
            {"mrgid": z["mrgid"], "name": z["name"], "gold": z["gold"], "poe": sorted(z["poe"])[:4]}
            for z in zees.values()
        ]
        leg["ampCount"] = len(amps)
        # Rules (facts only): formalities to check = a ZEE without a Gold pack
        # and without a known official port of entry.
        to_check = [z["name"] for z in leg["zees"] if not z["gold"] and not z["poe"]]
        leg["flags"] = []
        if to_check:
            leg["flags"].append({"kind": "formalities", "names": to_check[:4]})
        if unknown and not known:
            leg["flags"].append({"kind": "unknown", "count": unknown})
        if leg["holdDays"] == 0 and leg["daysAtSea"] >= 3:
            leg["flags"].append({"kind": "no-rest"})
    if season:
        deadline = time.monotonic() + SEASON_BUDGET_S
        for leg in legs:
            leg["season"] = season_for_leg(clock, leg, budget_deadline=deadline)
    return {
        "voyageId": voy.get("voyageId"),
        "generatedAt": to_iso(now) if now else None,
        "legs": legs,
        "pearlsWarmed": sum(l["pearls"]["known"] for l in legs),
        "pearlsUnknown": sum(l["pearls"]["unknown"] for l in legs),
    }

"""Table d’horloge — même algo que src/engine/voyageClock.js (contrat A = B)."""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from climatology_atlas import atlas_wind_at_dt, prefetch_points
from climatology_zones import boat_speed_from_wind

_PORT_DAYS_PATH = Path(__file__).resolve().parent / "data" / "port_days.json"
_PORT_DAYS_CACHE: Optional[dict] = None

AIR_CALENDAR_HOURS = 8.0
AIR_HOP_RETURN_NM = 80.0
LAND_CALENDAR_HOURS = 4.0
MIN_KNOTS = 0.5
WAVE_NOGO_M = 2.5
# WAVE_NOGO_DT_FACTOR (×3 dès 2,5 m) retiré lot C4 — voir wave_polar_factor.
MAX_STEP_NM = 30.0
MAX_STEP_H = 1.0
OFFICIAL_VOYAGE_ID = "berry-mappemonde-2026-officiel"
OFFICIAL_T0 = "2026-05-15T08:00:00Z"
DEFAULT_BMAP_PORT_DAYS = 3
PLANNING_MIN_KN = 3.0
POLAR_EFFICIENCY_DEFAULT = 0.85
MS_TO_KN = 1.943844
WAVE_POLAR_HS_FLAT_M = 1.5
WAVE_POLAR_HS_FULL_M = 4.0
WAVE_POLAR_HEAD = 0.6
WAVE_POLAR_FOLLOW = 0.85
TWA_CLOSE_HAULED_MIN = 40.0
TWA_RUNNING_MAX = 170.0

WindFn = Callable[[float, float, datetime], Dict[str, Any]]


def _norm_stop(name: str) -> str:
    return re.sub(r"[\s\-]+", "-", (name or "").strip().lower())


def port_days_table() -> dict:
    """Table sourcée (`server/data/port_days.json`). Valeurs = convention actuelle."""
    global _PORT_DAYS_CACHE
    if _PORT_DAYS_CACHE is not None:
        return _PORT_DAYS_CACHE
    try:
        raw = json.loads(_PORT_DAYS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        raw = {
            "default": DEFAULT_BMAP_PORT_DAYS,
            "source": "programme Berry-Mappemonde 2026",
            "stops": {"Saint-Maur": 0, "La Rochelle": 3, "Halifax": 1},
        }
    if not isinstance(raw, dict):
        raw = {"default": DEFAULT_BMAP_PORT_DAYS, "source": "", "stops": {}}
    raw.setdefault("default", DEFAULT_BMAP_PORT_DAYS)
    raw.setdefault("stops", {})
    _PORT_DAYS_CACHE = raw
    return raw


def port_days_for(name: str) -> int:
    table = port_days_table()
    n = _norm_stop(name)
    best_days: Optional[int] = None
    best_len = -1
    for key, days in (table.get("stops") or {}).items():
        k = _norm_stop(str(key))
        if k and k in n and len(k) > best_len:
            try:
                best_days = int(days)
            except (TypeError, ValueError):
                continue
            best_len = len(k)
    if best_days is not None:
        return best_days
    try:
        return int(table.get("default", DEFAULT_BMAP_PORT_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_BMAP_PORT_DAYS


def official_clock_params() -> dict:
    """Constantes d'horloge exposées par GET /voyage/official (`params`)."""
    table = port_days_table()
    try:
        port_default = int(table.get("default", DEFAULT_BMAP_PORT_DAYS))
    except (TypeError, ValueError):
        port_default = DEFAULT_BMAP_PORT_DAYS
    return {
        "landHours": LAND_CALENDAR_HOURS,
        "airHours": AIR_CALENDAR_HOURS,
        "minKnots": MIN_KNOTS,
        "portDaysDefault": port_default,
        "polarEfficiency": polar_efficiency(),
    }


def parse_iso(iso: str) -> datetime:
    raw = str(iso).replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_nm = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r_nm * math.asin(min(1.0, math.sqrt(a)))


def _side_dest_indices(pts: List[dict]) -> set:
    """Indices entre une paire de sauts aller/retour (Halifax ↔ SPM) : pas de milles voile."""
    jumps = [i for i, p in enumerate(pts) if p.get("jump")]
    side: set = set()
    used: set = set()
    for a, ja in enumerate(jumps):
        if ja in used or ja < 1:
            continue
        origin = pts[ja - 1]
        for jb in jumps[a + 1:]:
            if jb in used:
                continue
            dest = pts[jb]
            if _haversine_nm(origin["lat"], origin["lon"], dest["lat"], dest["lon"]) <= AIR_HOP_RETURN_NM:
                side.update(range(ja + 1, jb))
                used.add(ja)
                used.add(jb)
                break
    return side


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = lon2 - lon1
    while dlon > 180:
        dlon -= 360
    while dlon < -180:
        dlon += 360
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(dlon)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def twa_deg(heading: float, wind_from: float) -> float:
    h = ((heading % 360) + 360) % 360
    w = ((wind_from % 360) + 360) % 360
    raw = abs(w - h)
    return 360 - raw if raw > 180 else raw


def _bracket(val: float, arr: List[float]) -> tuple[int, int]:
    if not arr:
        return 0, 0
    if val <= arr[0]:
        return 0, 0
    last = len(arr) - 1
    if val >= arr[last]:
        return last, last
    for i in range(last):
        if val <= arr[i + 1]:
            return i, i + 1
    return last, last


def polar_boat_speed(raw: Optional[dict], twa: float, tws: float) -> Optional[float]:
    if not raw:
        return None
    rows = [float(x) for x in (raw.get("twa_rows") or [])]
    cols = [float(x) for x in (raw.get("tws_cols") or [])]
    matrix = raw.get("matrix") or []
    if not rows or not cols or not matrix:
        return None
    a = abs(float(twa))
    w = float(tws)
    if w <= 0 or a <= 0:
        return 0.0
    a = min(180.0, a)
    tws_max = cols[-1]
    eff_w = min(w, tws_max)
    twa_min = rows[0]

    def bilinear(ta: float, tw: float) -> float:
        i0, i1 = _bracket(ta, rows)
        j0, j1 = _bracket(tw, cols)
        v00 = float(matrix[i0][j0])
        v10 = float(matrix[i1][j0])
        v01 = float(matrix[i0][j1])
        v11 = float(matrix[i1][j1])
        t_span = (rows[i1] - rows[i0]) or 1
        w_span = (cols[j1] - cols[j0]) or 1
        ft = 0.0 if i0 == i1 else (ta - rows[i0]) / t_span
        fw = 0.0 if j0 == j1 else (tw - cols[j0]) / w_span
        return (
            v00 * (1 - ft) * (1 - fw)
            + v10 * ft * (1 - fw)
            + v01 * (1 - ft) * fw
            + v11 * ft * fw
        )

    if a < twa_min:
        return round(bilinear(twa_min, eff_w) * (a / twa_min), 3)
    if a > rows[-1]:
        a = rows[-1]
    return round(bilinear(a, eff_w), 3)


def polar_efficiency() -> float:
    """Facteur de croisière (lot C4). Variable d'environnement POLAR_EFFICIENCY."""
    raw = os.environ.get("POLAR_EFFICIENCY", str(POLAR_EFFICIENCY_DEFAULT))
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = POLAR_EFFICIENCY_DEFAULT
    if v <= 0:
        v = POLAR_EFFICIENCY_DEFAULT
    return min(1.0, v)


def wave_polar_factor(hs: Optional[float], relative_deg: float = 90.0) -> float:
    """Facteur continu Hs × angle relatif houle/cap (lot C4, A7).

    f = 1 jusqu'à 1,5 m ; linéaire jusqu'à 0,6 (mer de face) / 0,85 (mer
    arrière) à 4 m ; plafonné au-delà. Angle 0° = mer de face (houle « de »
    dans le cap), 180° = mer arrière.
    """
    if hs is None:
        return 1.0
    try:
        h = float(hs)
    except (TypeError, ValueError):
        return 1.0
    if h <= WAVE_POLAR_HS_FLAT_M:
        return 1.0
    rel = max(0.0, min(180.0, abs(float(relative_deg))))
    f_full = WAVE_POLAR_HEAD + (WAVE_POLAR_FOLLOW - WAVE_POLAR_HEAD) * (rel / 180.0)
    if h >= WAVE_POLAR_HS_FULL_M:
        return f_full
    t = (h - WAVE_POLAR_HS_FLAT_M) / (WAVE_POLAR_HS_FULL_M - WAVE_POLAR_HS_FLAT_M)
    return 1.0 + t * (f_full - 1.0)


def current_along_route_kn(w: dict, heading_deg: float) -> float:
    """Projection du vecteur courant (uo/vo ou kn « vers ») sur la route."""
    if not isinstance(w, dict):
        return 0.0
    uo, vo = w.get("uo"), w.get("vo")
    if uo is not None and vo is not None:
        try:
            east_kn = float(uo) * MS_TO_KN
            north_kn = float(vo) * MS_TO_KN
        except (TypeError, ValueError):
            return 0.0
    elif w.get("currentKn") is not None:
        try:
            kn = float(w.get("currentKn") or 0)
            to_deg = float(w.get("currentToDeg") or 0)
        except (TypeError, ValueError):
            return 0.0
        rad = math.radians(to_deg)
        east_kn = kn * math.sin(rad)
        north_kn = kn * math.cos(rad)
    else:
        return 0.0
    h = math.radians(heading_deg)
    return east_kn * math.sin(h) + north_kn * math.cos(h)


def sog_along_route(stw: float, w: dict, heading_deg: float) -> float:
    """SOG = projection sur la route de (vecteur polaire + vecteur courant)."""
    return float(stw) + current_along_route_kn(w, heading_deg)


def planning_speed_for(polar_raw: Optional[dict], tws: float, twa: float) -> Optional[float]:
    """Vitesse de planification : polaire × POLAR_EFFICIENCY, plancher 3 kn."""
    bs = polar_boat_speed(polar_raw, twa, tws)
    if bs is None:
        return None
    kn = max(PLANNING_MIN_KN, float(bs) * polar_efficiency())
    # Même arrondi que Math.round JS (demi loin de zéro), pas le banker Python.
    return math.floor(kn * 10 + 0.5) / 10.0


def _harmonic_mean(values: List[float]) -> float:
    vals = [float(v) for v in values if v is not None and float(v) > 1e-9]
    if not vals:
        return MIN_KNOTS
    return len(vals) / sum(1.0 / v for v in vals)


def _wave_relative_deg(heading: float, w: dict) -> float:
    wave_from = w.get("waveFromDeg")
    if wave_from is None:
        wave_from = w.get("waveDirDeg")
    if wave_from is None:
        return 90.0
    try:
        return twa_deg(heading, float(wave_from))
    except (TypeError, ValueError):
        return 90.0


def _stw_from_wind(polar_raw, brg: float, w: dict) -> tuple[float, float, str]:
    """Vitesse surface : polaire × efficacité × polaire de vagues (sans courant).

    `boat_speed_from_wind` n'est appelé que sans polaire (lot C7, `basis`).
    """
    twa = twa_deg(brg, float(w.get("dirFromDeg") or 0))
    from_polar = polar_boat_speed(polar_raw, twa, float(w.get("speedKnots") or 0))
    if from_polar is not None:
        speed = float(from_polar) * polar_efficiency()
        basis = "polar"
    else:
        speed = boat_speed_from_wind(w.get("speedKnots") or 0)
        basis = "fallback"
    speed *= wave_polar_factor(w.get("hs"), _wave_relative_deg(brg, w))
    return float(speed), twa, basis


def _r1(n: Optional[float]) -> Optional[float]:
    if n is None:
        return None
    return round(float(n), 1)


def _r4(n: float) -> float:
    return round(float(n), 4)


def _wrap_lon(lon: float) -> float:
    x = lon
    while x > 180:
        x -= 360
    while x < -180:
        x += 360
    return x


def _mark_indices(marks: List[dict], points: List[dict]) -> List[dict]:
    out = []
    for m in marks or []:
        if isinstance(m.get("index"), int) and 0 <= m["index"] < len(points):
            out.append({**m, "index": m["index"]})
            continue
        target = m.get("nm", m.get("filmNm", 0))
        best, best_d = 0, float("inf")
        for i, p in enumerate(points):
            d = abs((p.get("cumNm") or 0) - (target or 0))
            if d < best_d:
                best, best_d = i, d
        out.append({**m, "index": best})
    return out


def find_start_index(points: List[dict], marks: List[dict], start_at: str = "la-rochelle") -> int:
    if start_at == "saint-maur" or not points:
        return 0
    for m in _mark_indices(marks, points):
        if re.search(r"la rochelle", str(m.get("name") or ""), re.I):
            return int(m["index"])
    return 0


def _default_wind(lat: float, lon: float, t: datetime) -> Dict[str, Any]:
    pack = atlas_wind_at_dt(lat, lon, t)
    pack.setdefault("regime", pack.get("kind") or "climatology")
    return pack


def _lerp_lon(lon1: float, lon2: float, t: float) -> float:
    d = lon2 - lon1
    while d > 180:
        d -= 360
    while d < -180:
        d += 360
    return _wrap_lon(lon1 + d * t)


def _point_along(a: dict, b: dict, frac: float) -> dict:
    f = max(0.0, min(1.0, float(frac)))
    span = float(b.get("cumNm") or 0) - float(a.get("cumNm") or 0)
    film_span = float(b.get("filmCum", b.get("cumNm", 0)) or 0) - float(a.get("filmCum", a.get("cumNm", 0)) or 0)
    return {
        "lat": a["lat"] + f * (b["lat"] - a["lat"]),
        "lon": _lerp_lon(a["lon"], b["lon"], f),
        "cumNm": float(a.get("cumNm") or 0) + f * span,
        "filmCum": float(a.get("filmCum", a.get("cumNm", 0)) or 0) + f * film_span,
        "jump": False,
        "nonMaritime": False,
    }


def _wind_pack_from(w: dict, twa: Optional[float] = None) -> Dict[str, Any]:
    return {
        "speedKnots": w.get("speedKnots"),
        "twa": twa,
        "kind": w.get("kind") or w.get("regime") or "climatology",
        "regime": w.get("regime") or w.get("kind") or "climatology",
        "sources": list(w.get("sources") or []),
        "spread": w.get("spread"),
        "model": w.get("model"),
        "leadHours": w.get("leadHours"),
        "reason": w.get("reason"),
        "source": w.get("source"),
        "period": w.get("period"),
        "doi": w.get("doi"),
        "hs": w.get("hs"),
        "hsP50": w.get("hsP50"),
        "hsP90": w.get("hsP90"),
        "currentKn": w.get("currentKn"),
        "currentToDeg": w.get("currentToDeg"),
        "uo": w.get("uo"),
        "vo": w.get("vo"),
        "waveFromDeg": w.get("waveFromDeg", w.get("waveDirDeg")),
        "roseKnots": list(w["roseKnots"]) if isinstance(w.get("roseKnots"), (list, tuple)) else None,
    }


def _speed_from_wind(polar_raw, brg: float, w: dict) -> tuple[float, float, str]:
    """SOG sur la route. Climatologie : moyenne harmonique des 3 tirages rose."""
    draws = w.get("roseKnots") if isinstance(w, dict) else None
    kind = (w.get("kind") or w.get("regime") or "") if isinstance(w, dict) else ""
    if kind == "climatology" and isinstance(draws, (list, tuple)) and len(draws) >= 3:
        sogs: List[float] = []
        twa = 0.0
        basis = "fallback"
        for kn in list(draws)[:3]:
            pack = {**w, "speedKnots": kn}
            stw, twa, basis = _stw_from_wind(polar_raw, brg, pack)
            sogs.append(max(MIN_KNOTS, sog_along_route(stw, w, brg)))
        return _harmonic_mean(sogs), twa, basis
    stw, twa, basis = _stw_from_wind(polar_raw, brg, w)
    return max(MIN_KNOTS, sog_along_route(stw, w, brg)), twa, basis


def _clock_kind(vertices: List[dict]) -> str:
    kinds = {(v.get("regime") or v.get("kind")) for v in vertices if v.get("regime") or v.get("kind")}
    if "hindcast" in kinds or "forecast" in kinds:
        if kinds <= {"hindcast"}:
            return "hindcast"
        return "mixed"
    return "climatology"


def _emit(p: dict, t_hours: float, t0: datetime, bearing: float,
          speed_knots: Optional[float], wind: dict, vehicle: str, month: int,
          sea_hours: float = 0.0, basis: str = "fallback") -> dict:
    when = t0 + timedelta(hours=t_hours)
    veh = "main" if vehicle == "boat" else vehicle
    speed_basis = basis if basis in {"polar", "fallback"} else "fallback"
    return {
        "filmNm": _r4(p.get("filmCum", p.get("cumNm", 0)) or 0),
        "sailNm": _r4(p.get("cumNm", 0) or 0),
        "lat": p["lat"],
        "lon": _wrap_lon(p["lon"]),
        "bearing": _r1(bearing),
        "tHours": _r4(t_hours),
        "iso": to_iso(when),
        "speedKnots": _r1(speed_knots),
        "windKnots": _r1(wind.get("speedKnots")),
        "twa": _r1(wind.get("twa")),
        "month": month,
        "vehicle": veh,
        "seaHours": _r4(sea_hours),
        "basis": speed_basis,
        "kind": wind.get("kind") or wind.get("regime") or "climatology",
        "regime": wind.get("regime") or wind.get("kind") or "climatology",
        "sources": list(wind.get("sources") or []),
        "spread": wind.get("spread"),
        "model": wind.get("model"),
        "leadHours": wind.get("leadHours"),
        "reason": wind.get("reason"),
        "source": wind.get("source"),
        "period": wind.get("period"),
        "doi": wind.get("doi"),
        "hs": wind.get("hs"),
        "hsP50": wind.get("hsP50"),
        "hsP90": wind.get("hsP90"),
        "currentKn": wind.get("currentKn"),
        "currentToDeg": wind.get("currentToDeg"),
    }


def build_voyage_clock(
    points: List[dict],
    marks: Optional[List[dict]] = None,
    t0: str | datetime = "",
    polar_raw: Optional[dict] = None,
    start_at: str = "la-rochelle",
    wind_fn: Optional[WindFn] = None,
) -> Dict[str, Any]:
    pts = list(points or [])
    t0d = parse_iso(t0) if not isinstance(t0, datetime) else t0
    if t0d.tzinfo is None:
        t0d = t0d.replace(tzinfo=timezone.utc)
    if wind_fn is None:
        months = {t0d.month, (t0d.month % 12) + 1, ((t0d.month + 1) % 12) + 1}
        prefetch_points(pts, months)
    wind_at = wind_fn or _default_wind
    marks = marks or []
    start_idx = find_start_index(pts, marks, start_at)
    tagged = _mark_indices(marks, pts)
    mark_by_index = {m["index"]: m for m in tagged}

    vertices: List[dict] = []
    clock_marks: List[dict] = []
    t_hours = 0.0
    sea_hours = 0.0
    quay_hours = 0.0

    if not pts:
        iso = to_iso(t0d)
        return {
            "t0": iso,
            "kind": "climatology",
            "vertices": [],
            "marks": [],
            "seaHours": 0,
            "quayHours": 0,
            "arrivalIso": iso,
        }

    clock_basis = "polar" if polar_raw else "fallback"
    last_speed_basis = clock_basis

    for i in range(start_idx):
        nxt = pts[i + 1] if i + 1 < len(pts) else pts[i]
        vertices.append(_emit(
            pts[i], 0.0, t0d,
            bearing_deg(pts[i]["lat"], pts[i]["lon"], nxt["lat"], nxt["lon"]),
            None, {"kind": "climatology"}, "land", t0d.month, 0.0,
            basis=clock_basis,
        ))

    start = pts[start_idx]
    start_next = pts[start_idx + 1] if start_idx + 1 < len(pts) else start
    vertices.append(_emit(
        start, 0.0, t0d,
        bearing_deg(start["lat"], start["lon"], start_next["lat"], start_next["lon"]),
        None, {"kind": "climatology"},
        "land" if start.get("nonMaritime") else "main",
        t0d.month, 0.0,
        basis=clock_basis,
    ))

    land_end_idx = -1
    if start_at == "saint-maur":
        for m in tagged:
            if re.search(r"la rochelle", str(m.get("name") or ""), re.I):
                land_end_idx = int(m["index"])
                break

    side_idx = _side_dest_indices(pts)
    sail_nm = float(start.get("cumNm") or 0)

    for i in range(start_idx, len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if (i + 1) in side_idx:
            continue
        brg = bearing_deg(a["lat"], a["lon"], b["lat"], b["lon"])
        span_nm = max(0.0, float(b.get("cumNm") or 0) - float(a.get("cumNm") or 0))
        vehicle = "main"
        speed_knots: Optional[float] = None
        wind_pack: Dict[str, Any] = {"kind": "climatology"}
        air_edge = bool(b.get("jump"))
        if not air_edge and b.get("air"):
            continue

        if air_edge:
            t_hours += AIR_CALENDAR_HOURS
            vehicle = "plane"
            vertices.append(_emit(
                {**b, "cumNm": sail_nm}, t_hours, t0d, brg, speed_knots, wind_pack, vehicle,
                (t0d + timedelta(hours=t_hours)).month,
                sea_hours,
                basis=clock_basis,
            ))
        elif a.get("nonMaritime") and b.get("nonMaritime"):
            vehicle = "land"
            if start_at == "saint-maur" and land_end_idx >= 0 and i + 1 == land_end_idx:
                t_hours += LAND_CALENDAR_HOURS
            sail_nm = float(b.get("cumNm") or sail_nm)
            vertices.append(_emit(
                b, t_hours, t0d, brg, speed_knots, wind_pack, vehicle,
                (t0d + timedelta(hours=t_hours)).month,
                sea_hours,
                basis=clock_basis,
            ))
        else:
            pos_nm = 0.0
            while pos_nm < span_nm - 1e-9:
                rem = span_nm - pos_nm
                guess = min(MAX_STEP_NM, rem)
                mid_frac = (pos_nm + guess / 2.0) / span_nm if span_nm else 0.5
                mid = _point_along(a, b, mid_frac)
                w0 = wind_at(mid["lat"], mid["lon"], t0d + timedelta(hours=t_hours))
                speed0, _twa0, _basis0 = _speed_from_wind(polar_raw, brg, w0)
                dt0 = guess / speed0
                if dt0 > MAX_STEP_H:
                    guess = speed0 * MAX_STEP_H
                    dt0 = MAX_STEP_H
                    mid_frac = (pos_nm + guess / 2.0) / span_nm if span_nm else 0.5
                    mid = _point_along(a, b, mid_frac)
                when_mid = t0d + timedelta(hours=t_hours + dt0 / 2.0)
                w = wind_at(mid["lat"], mid["lon"], when_mid)
                speed_knots, twa, last_speed_basis = _speed_from_wind(polar_raw, brg, w)
                dt = guess / speed_knots
                if dt > MAX_STEP_H + 1e-6:
                    guess = speed_knots * MAX_STEP_H
                    dt = MAX_STEP_H
                t_hours += dt
                sea_hours += dt
                pos_nm += guess
                sail_nm += guess
                wind_pack = _wind_pack_from(w, twa)
                pt = b if pos_nm >= span_nm - 1e-6 else _point_along(a, b, pos_nm / span_nm)
                vertices.append(_emit(
                    {**pt, "cumNm": sail_nm}, t_hours, t0d, brg, speed_knots, wind_pack, "main",
                    (t0d + timedelta(hours=t_hours)).month,
                    sea_hours,
                    basis=last_speed_basis,
                ))

        arrived = mark_by_index.get(i + 1)
        if arrived and i + 1 != start_idx and vehicle != "plane":
            hold = port_days_for(str(arrived.get("name") or "")) * 24
            clock_marks.append({
                "name": arrived.get("name"),
                "filmNm": _r4(b.get("filmCum", b.get("cumNm", 0)) or 0),
                "tHours": _r4(t_hours),
                "iso": to_iso(t0d + timedelta(hours=t_hours)),
                "holdHours": hold,
            })
            if hold > 0:
                t_hours += hold
                quay_hours += hold
                vertices.append(_emit(
                    {**b, "cumNm": sail_nm}, t_hours, t0d, brg, 0.0,
                    {"kind": wind_pack.get("kind") or "climatology",
                     "regime": wind_pack.get("regime") or wind_pack.get("kind") or "climatology",
                     "sources": list(wind_pack.get("sources") or []),
                     "spread": wind_pack.get("spread"),
                     "speedKnots": wind_pack.get("speedKnots")},
                    "quay",
                    (t0d + timedelta(hours=t_hours)).month,
                    sea_hours,
                    basis=last_speed_basis,
                ))

    last = vertices[-1]
    return {
        "t0": to_iso(t0d),
        "kind": _clock_kind(vertices),
        "vertices": vertices,
        "marks": clock_marks,
        "seaHours": _r4(sea_hours),
        "quayHours": _r4(quay_hours),
        "arrivalIso": last.get("iso") or to_iso(t0d),
        "startAt": start_at,
    }


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def sample_clock_at_hours(clock: dict, t_hours: float) -> Optional[dict]:
    verts = clock.get("vertices") or []
    if not verts:
        return None
    x = float(t_hours)
    if x <= verts[0]["tHours"]:
        return {**verts[0], "atQuay": False, "status": "waiting" if x < 0 else "live"}
    last = verts[-1]
    if x >= last["tHours"]:
        at_quay = last.get("vehicle") == "quay"
        out = {**last, "atQuay": at_quay, "status": "arrived"}
        if at_quay:
            out["speedKnots"] = 0
            out["vehicle"] = "quay"
            if out.get("plannedKnots") is None:
                out["plannedKnots"] = last.get("speedKnots")
        return out
    for i in range(len(verts) - 1):
        a, b = verts[i], verts[i + 1]
        if x > b["tHours"]:
            continue
        span = (b["tHours"] - a["tHours"]) or 1
        t = (x - a["tHours"]) / span
        if abs((b.get("filmNm") or 0) - (a.get("filmNm") or 0)) < 1e-6:
            hold = 0.0
            for m in clock.get("marks") or []:
                if abs((m.get("filmNm") or 0) - (a.get("filmNm") or 0)) < 1e-4:
                    hold = float(m.get("holdHours") or 0)
                    break
            return {
                **a,
                "tHours": x,
                "atQuay": True,
                "status": "live",
                "vehicle": "quay",
                "speedKnots": 0,
                "plannedKnots": a.get("speedKnots"),
                "holdHours": hold,
            }
        t0 = parse_iso(clock["t0"])
        return {
            **a,
            "lat": _lerp(a["lat"], b["lat"], t),
            "lon": _lerp(a["lon"], b["lon"], t),
            "filmNm": _lerp(a["filmNm"], b["filmNm"], t),
            "sailNm": _lerp(a["sailNm"], b["sailNm"], t),
            "tHours": x,
            "iso": to_iso(t0 + timedelta(hours=x)),
            "atQuay": False,
            "status": "live",
            "kind": a["kind"] if t < 0.5 else b["kind"],
            "regime": (a.get("regime") or a.get("kind")) if t < 0.5 else (b.get("regime") or b.get("kind")),
            "sources": (a.get("sources") if t < 0.5 else b.get("sources")) or [],
            "spread": a.get("spread") if t < 0.5 else b.get("spread"),
            "speedKnots": b.get("speedKnots") if b.get("speedKnots") is not None else a.get("speedKnots"),
            "windKnots": b.get("windKnots") if b.get("windKnots") is not None else a.get("windKnots"),
            "model": b.get("model") or a.get("model"),
            "leadHours": b.get("leadHours") if b.get("leadHours") is not None else a.get("leadHours"),
            "seaHours": _lerp(float(a.get("seaHours") or 0), float(b.get("seaHours") or 0), t),
        }
    return {**last, "atQuay": False, "status": "arrived"}


def sample_clock_at_time(clock: dict, when: datetime | str) -> Optional[dict]:
    t0 = parse_iso(clock["t0"])
    w = parse_iso(when) if not isinstance(when, datetime) else when
    if w.tzinfo is None:
        w = w.replace(tzinfo=timezone.utc)
    hours = (w - t0).total_seconds() / 3600.0
    if hours < 0:
        v = (clock.get("vertices") or [{}])[0]
        return {
            **v,
            "atQuay": True,
            "status": "waiting",
            "countdownHours": -hours,
            "speedKnots": 0,
            "vehicle": "quay",
            "plannedKnots": v.get("speedKnots"),
        }
    return sample_clock_at_hours(clock, hours)

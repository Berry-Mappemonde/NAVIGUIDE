"""Table d’horloge — même algo que src/engine/voyageClock.js (contrat A = B)."""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from climatology_zones import boat_speed_from_wind, zone_wind_at

AIR_CALENDAR_HOURS = 8.0
LAND_CALENDAR_HOURS = 4.0
MIN_KNOTS = 0.5
WAVE_NOGO_M = 2.5
WAVE_NOGO_DT_FACTOR = 3.0
OFFICIAL_VOYAGE_ID = "berry-mappemonde-2026-officiel"
OFFICIAL_T0 = "2026-05-15T08:00:00Z"
DEFAULT_BMAP_PORT_DAYS = 3

WindFn = Callable[[float, float, datetime], Dict[str, Any]]


def port_days_for(name: str) -> int:
    n = (name or "").lower()
    if re.search(r"saint-?\s*maur", n):
        return 0
    if "la rochelle" in n:
        return 3
    if "halifax" in n:
        return 1
    return DEFAULT_BMAP_PORT_DAYS


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
    return zone_wind_at(lat, lon, t.month)


def _emit(p: dict, t_hours: float, t0: datetime, bearing: float,
          speed_knots: Optional[float], wind: dict, vehicle: str, month: int,
          sea_hours: float = 0.0) -> dict:
    when = t0 + timedelta(hours=t_hours)
    veh = "main" if vehicle == "boat" else vehicle
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
        "kind": wind.get("kind") or "climatology",
        "model": wind.get("model"),
        "leadHours": wind.get("leadHours"),
        "reason": wind.get("reason"),
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

    for i in range(start_idx):
        nxt = pts[i + 1] if i + 1 < len(pts) else pts[i]
        vertices.append(_emit(
            pts[i], 0.0, t0d,
            bearing_deg(pts[i]["lat"], pts[i]["lon"], nxt["lat"], nxt["lon"]),
            None, {"kind": "climatology"}, "land", t0d.month, 0.0,
        ))

    start = pts[start_idx]
    start_next = pts[start_idx + 1] if start_idx + 1 < len(pts) else start
    vertices.append(_emit(
        start, 0.0, t0d,
        bearing_deg(start["lat"], start["lon"], start_next["lat"], start_next["lon"]),
        None, {"kind": "climatology"},
        "land" if start.get("nonMaritime") else "main",
        t0d.month, 0.0,
    ))

    land_end_idx = -1
    if start_at == "saint-maur":
        for m in tagged:
            if re.search(r"la rochelle", str(m.get("name") or ""), re.I):
                land_end_idx = int(m["index"])
                break

    for i in range(start_idx, len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        brg = bearing_deg(a["lat"], a["lon"], b["lat"], b["lon"])
        span_nm = max(0.0, float(b.get("cumNm") or 0) - float(a.get("cumNm") or 0))
        when = t0d + timedelta(hours=t_hours)
        vehicle = "main"
        speed_knots: Optional[float] = None
        wind_pack: Dict[str, Any] = {"kind": "climatology"}

        if b.get("jump"):
            t_hours += AIR_CALENDAR_HOURS
            vehicle = "plane"
        elif a.get("nonMaritime") and b.get("nonMaritime"):
            vehicle = "land"
            if start_at == "saint-maur" and land_end_idx >= 0 and i + 1 == land_end_idx:
                t_hours += LAND_CALENDAR_HOURS
        else:
            mid_lat = (a["lat"] + b["lat"]) / 2
            mid_lon = (a["lon"] + b["lon"]) / 2
            w = wind_at(mid_lat, mid_lon, when)
            twa = twa_deg(brg, float(w.get("dirFromDeg") or 0))
            from_polar = polar_boat_speed(polar_raw, twa, float(w.get("speedKnots") or 0))
            speed_knots = from_polar if from_polar is not None else boat_speed_from_wind(w.get("speedKnots") or 0)
            speed_knots = max(MIN_KNOTS, float(speed_knots))
            dt = span_nm / speed_knots
            hs = w.get("hs")
            if hs is not None and float(hs) >= WAVE_NOGO_M:
                dt *= WAVE_NOGO_DT_FACTOR
            t_hours += dt
            sea_hours += dt
            wind_pack = {
                "speedKnots": w.get("speedKnots"),
                "twa": twa,
                "kind": w.get("kind") or "climatology",
                "model": w.get("model"),
                "leadHours": w.get("leadHours"),
                "reason": w.get("reason"),
            }

        vertices.append(_emit(
            b, t_hours, t0d, brg, speed_knots, wind_pack, vehicle,
            (t0d + timedelta(hours=t_hours)).month,
            sea_hours,
        ))

        arrived = mark_by_index.get(i + 1)
        if arrived and i + 1 != start_idx:
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
                    b, t_hours, t0d, brg, 0.0,
                    {"kind": wind_pack.get("kind") or "climatology",
                     "speedKnots": wind_pack.get("speedKnots")},
                    "quay",
                    (t0d + timedelta(hours=t_hours)).month,
                    sea_hours,
                ))

    last = vertices[-1]
    kinds = {v.get("kind") for v in vertices if v.get("kind")}
    return {
        "t0": to_iso(t0d),
        "kind": "mixed" if "forecast" in kinds else "climatology",
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
        return {**last, "atQuay": last.get("vehicle") == "quay", "status": "arrived"}
    for i in range(len(verts) - 1):
        a, b = verts[i], verts[i + 1]
        if x > b["tHours"]:
            continue
        span = (b["tHours"] - a["tHours"]) or 1
        t = (x - a["tHours"]) / span
        if abs((b.get("filmNm") or 0) - (a.get("filmNm") or 0)) < 1e-6:
            return {**a, "tHours": x, "atQuay": True, "status": "live", "vehicle": "quay"}
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
        return {**v, "atQuay": True, "status": "waiting", "countdownHours": -hours}
    return sample_clock_at_hours(clock, hours)

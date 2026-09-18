"""Isochrone d’une jambe — copie adaptée (pas d’import depuis naviguide/).

Propagate / prune / land mask. vent, courant, vague et polar sont injectés.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from voyage_clock import WAVE_NOGO_M, bearing_deg, polar_boat_speed, twa_deg
from climatology_zones import boat_speed_from_wind

try:
    from global_land_mask import globe as _globe
    # Direct grid indexing: globe.is_land() rebuilds numpy arrays and runs
    # min/max/any on every scalar call (~50 µs). The isochrone asks a million
    # times per leg — a /recompute took 77 s, 85 % in that overhead.
    _MASK = _globe._mask  # True = ocean, shape (21600, 43200), 1 km
    _LAT0 = float(_globe._lat[0])
    _DLAT = float(_globe._lat[1] - _globe._lat[0])
    _LON0 = float(_globe._lon[0])
    _DLON = float(_globe._lon[1] - _globe._lon[0])
    _LAT_MIN, _LAT_MAX = float(_globe._lat.min()), float(_globe._lat.max())
    _LON_MIN, _LON_MAX = float(_globe._lon.min()), float(_globe._lon.max())
    _USE_GLOBAL_LAND_MASK = True
except Exception:
    _USE_GLOBAL_LAND_MASK = False

_R_NM = 3440.065

_LAND_BOXES_FALLBACK = [
    (30, 65, -125, -58),
    (9, 20, -88, -76),
    (-45, 8, -72, -40),
    (42, 65, 5, 35),
    (36.5, 43.8, -9.3, 3.2),   # Iberia — land-crossing test
    (31.0, 36.2, -10.0, -1.0),  # Maroc atlantique
    (-28, 32, 0, 42),
    (15, 28, 38, 58),
    (10, 28, 72, 85),
    (-5, 22, 95, 115),
    (-38, -18, 120, 145),
    (-90, -63, -180, 180),
    (62, 82, -52, -20),
    (-23, -13, 44, 49),
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _R_NM * math.asin(math.sqrt(min(1.0, a)))


def move_position(lat: float, lon: float, bearing: float, dist_nm: float) -> Tuple[float, float]:
    d = dist_nm / _R_NM
    b = math.radians(bearing)
    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    phi2 = math.asin(math.sin(phi1) * math.cos(d) + math.cos(phi1) * math.sin(d) * math.cos(b))
    lam2 = lam1 + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(phi1),
        math.cos(d) - math.sin(phi1) * math.sin(phi2),
    )
    lat2 = math.degrees(phi2)
    lon2 = (math.degrees(lam2) + 540) % 360 - 180
    return (round(lat2, 5), round(lon2, 5))


def is_land(lat: float, lon: float) -> bool:
    if _USE_GLOBAL_LAND_MASK:
        try:
            la = min(max(float(lat), _LAT_MIN), _LAT_MAX)
            lo = min(max(float(lon), _LON_MIN), _LON_MAX)
            # Same truncation as globe.lat_to_index / lon_to_index (astype int).
            return not bool(_MASK[int((la - _LAT0) / _DLAT), int((lo - _LON0) / _DLON)])
        except Exception:
            pass
    for la, lb, loa, lob in _LAND_BOXES_FALLBACK:
        if la <= lat <= lb and loa <= lon <= lob:
            return True
    return False


_PATH_SAMPLES = 8


def is_path_clear(lat1: float, lon1: float, lat2: float, lon2: float) -> bool:
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    if dlon > 180:
        dlon -= 360
    elif dlon < -180:
        dlon += 360
    for i in range(1, _PATH_SAMPLES + 1):
        t = i / _PATH_SAMPLES
        lat = lat1 + t * dlat
        lon = (lon1 + t * dlon + 540) % 360 - 180
        if is_land(lat, lon):
            return False
    return True


@dataclass
class IsoPoint:
    lat: float
    lon: float
    time: datetime
    heading: float = 0.0
    boat_speed: float = 0.0
    wind_speed: float = 0.0
    wind_dir: float = 0.0
    kind: str = "climatology"
    parent: Optional["IsoPoint"] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "time": self.time.isoformat(),
            "heading": self.heading,
            "boat_speed": self.boat_speed,
            "wind_speed": self.wind_speed,
            "wind_dir": self.wind_dir,
            "kind": self.kind,
        }


def _boat_speed(polar_raw: Optional[dict], twa: float, tws: float) -> float:
    k = polar_boat_speed(polar_raw, twa, tws)
    if k is None:
        k = boat_speed_from_wind(tws)
    return float(k)


def _propagate(
    prev: List[IsoPoint],
    polar_raw: Optional[dict],
    time_step_h: float,
    heading_step_deg: int,
    current_time: datetime,
    wind_fn: Callable,
    current_fn: Optional[Callable],
    wave_nogo_fn: Optional[Callable],
) -> List[IsoPoint]:
    result = []
    next_t = current_time + timedelta(hours=time_step_h)
    for pt in prev:
        w = wind_fn(pt.lat, pt.lon, current_time) or {}
        wind_spd = float(w.get("speedKnots") or 0)
        wind_dir = float(w.get("dirFromDeg") or 0)
        kind = w.get("kind") or "climatology"
        cur = current_fn(pt.lat, pt.lon, current_time) if current_fn else None
        for hdg in range(0, 360, heading_step_deg):
            twa = twa_deg(hdg, wind_dir)
            spd = _boat_speed(polar_raw, twa, wind_spd)
            if spd < 0.3:
                continue
            dist = spd * time_step_h
            nlat, nlon = move_position(pt.lat, pt.lon, hdg, dist)
            if cur:
                uo = cur.get("uo")
                vo = cur.get("vo")
                if uo is not None and vo is not None:
                    kn = math.hypot(float(uo), float(vo)) * 1.943844
                    to_deg = (math.degrees(math.atan2(float(uo), float(vo))) + 360) % 360
                    nlat, nlon = move_position(nlat, nlon, to_deg, kn * time_step_h)
                elif cur.get("speed_knots"):
                    nlat, nlon = move_position(
                        nlat, nlon, cur.get("direction_to_deg") or 0,
                        float(cur["speed_knots"]) * time_step_h,
                    )
            if not (-85 <= nlat <= 85):
                continue
            if wave_nogo_fn and wave_nogo_fn(nlat, nlon, next_t):
                continue
            if not is_path_clear(pt.lat, pt.lon, nlat, nlon):
                continue
            result.append(IsoPoint(
                lat=nlat, lon=nlon, time=next_t, heading=float(hdg),
                boat_speed=spd, wind_speed=wind_spd, wind_dir=wind_dir,
                kind=kind, parent=pt,
            ))
    return result


def _prune(points: List[IsoPoint], sectors: int = 72) -> List[IsoPoint]:
    if not points:
        return []
    cen_lat = sum(p.lat for p in points) / len(points)
    cen_lon = sum(p.lon for p in points) / len(points)
    sec_size = 360.0 / sectors
    best: Dict[int, Tuple[float, IsoPoint]] = {}
    for p in points:
        brg = bearing_deg(cen_lat, cen_lon, p.lat, p.lon)
        sec = int(brg / sec_size) % sectors
        dist = haversine(cen_lat, cen_lon, p.lat, p.lon)
        if sec not in best or dist > best[sec][0]:
            best[sec] = (dist, p)
    return [v[1] for v in best.values()]


def _trace(node: Optional[IsoPoint]) -> List[IsoPoint]:
    route = []
    while node is not None:
        route.append(node)
        node = node.parent
    route.reverse()
    return route


def _closest_on_line(lat: float, lon: float, coords: List[Tuple[float, float]]) -> Tuple[int, float]:
    best_i, best_d = 0, float("inf")
    for i, (la, lo) in enumerate(coords):
        d = haversine(lat, lon, la, lo)
        if d < best_d:
            best_i, best_d = i, d
    return best_i, best_d


def default_wave_nogo(wind_fn: Callable, hs_limit: float = WAVE_NOGO_M):
    def fn(lat: float, lon: float, t: datetime) -> bool:
        w = wind_fn(lat, lon, t) or {}
        hs = w.get("hs")
        return hs is not None and float(hs) >= hs_limit
    return fn


def nudge_offshore(lat: float, lon: float, max_nm: float = 40.0) -> Tuple[float, float]:
    """Si le départ est sur terre (corde trop droite), glisse vers la mer."""
    if not is_land(lat, lon):
        return lat, lon
    for dist in (5.0, 10.0, 20.0, max_nm):
        for hdg in range(0, 360, 45):
            nlat, nlon = move_position(lat, lon, hdg, dist)
            if not is_land(nlat, nlon):
                return nlat, nlon
    return lat, lon


def run_leg_isochrone(
    dep_lat: float,
    dep_lon: float,
    dst_lat: float,
    dst_lon: float,
    departure_time: datetime,
    wind_fn: Callable,
    polar_raw: Optional[dict] = None,
    current_fn: Optional[Callable] = None,
    wave_nogo_fn: Optional[Callable] = None,
    time_step_h: float = 6.0,
    heading_step_deg: int = 10,
    max_steps: int = 120,
    arrival_radius_nm: float = 50.0,
    prune_sectors: int = 72,
    searoute_coords: Optional[List[Tuple[float, float]]] = None,
) -> Dict[str, Any]:
    if departure_time.tzinfo is None:
        departure_time = departure_time.replace(tzinfo=timezone.utc)
    if wave_nogo_fn is None:
        wave_nogo_fn = default_wave_nogo(wind_fn)

    dep_lat, dep_lon = nudge_offshore(dep_lat, dep_lon)
    start = IsoPoint(lat=dep_lat, lon=dep_lon, time=departure_time)
    current_iso = [start]
    all_isos = [[start.to_dict()]]
    best_arrival: Optional[IsoPoint] = None
    steps_taken = 0
    kinds: List[str] = []

    for step in range(max_steps):
        current_time = departure_time + timedelta(hours=step * time_step_h)
        candidates = _propagate(
            current_iso, polar_raw, time_step_h, heading_step_deg, current_time,
            wind_fn, current_fn, wave_nogo_fn,
        )
        if not candidates:
            break
        for pt in candidates:
            kinds.append(pt.kind)
            if haversine(pt.lat, pt.lon, dst_lat, dst_lon) <= arrival_radius_nm:
                best_arrival = pt
                break
        if best_arrival:
            steps_taken = step + 1
            break
        current_iso = _prune(candidates, prune_sectors)
        all_isos.append([p.to_dict() for p in current_iso])
        steps_taken = step + 1

    status = "failed"
    route_pts: List[IsoPoint] = []
    if best_arrival:
        route_pts = _trace(best_arrival)
        dest_time = best_arrival.time + timedelta(
            hours=haversine(best_arrival.lat, best_arrival.lon, dst_lat, dst_lon)
            / max(best_arrival.boat_speed, 0.1)
        )
        route_pts.append(IsoPoint(lat=dst_lat, lon=dst_lon, time=dest_time, kind=best_arrival.kind))
        status = "arrived"
    elif current_iso:
        closest = min(current_iso, key=lambda p: haversine(p.lat, p.lon, dst_lat, dst_lon))
        route_pts = _trace(closest)
        if searoute_coords:
            idx, _ = _closest_on_line(closest.lat, closest.lon, searoute_coords)
            for la, lo in searoute_coords[idx:]:
                route_pts.append(IsoPoint(lat=la, lon=lo, time=closest.time, kind="climatology"))
            status = "spliced"
        else:
            status = "failed"

    coords = [[p.lon, p.lat] for p in route_pts]
    dist = 0.0
    for i in range(len(route_pts) - 1):
        dist += haversine(route_pts[i].lat, route_pts[i].lon, route_pts[i + 1].lat, route_pts[i + 1].lon)
    hours = 0.0
    if route_pts:
        hours = (route_pts[-1].time - departure_time).total_seconds() / 3600.0
    kind_mix = sorted({k for k in kinds if k} | {p.kind for p in route_pts if p.kind})

    return {
        "status": status,
        "kind_mix": kind_mix or ["climatology"],
        "draft_geojson": {
            "type": "Feature",
            "properties": {"role": "isochrone-leg", "status": status},
            "geometry": {"type": "LineString", "coordinates": coords},
        },
        "hours": round(hours, 2),
        "distance_nm": round(dist, 2),
        "isochrones": all_isos if False else [],  # off by default
        "steps": steps_taken,
        "route": [p.to_dict() for p in route_pts],
    }

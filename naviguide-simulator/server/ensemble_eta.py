"""ETA probabiliste par ensembles Open-Meteo (lot C6).

Au-delà de 7 jours, l'arrivée n'est pas une date unique : p10 / p50 / p90
des intégrations par membre. Sans ensemble = `{members: 0}`, jamais inventé.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from climatology_atlas import atlas_wind_at_dt
from hindcast import hours_from_om, om_get, point_key
from isochrone import haversine
from pearl_store import kv_get, kv_put
from voyage_clock import (
    PLANNING_MIN_KN,
    build_voyage_clock,
    parse_iso,
    sample_clock_at_time,
    to_iso,
)

log = logging.getLogger("naviguide-simulator.ensemble-eta")

ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
ENSEMBLE_MODELS = "gfs_seamless,ecmwf_ifs025"
FORECAST_DAYS = 15
CACHE_NS = "ensemble"
CACHE_TTL_S = 6 * 3600
MAX_POINT_NM = 60.0
SOURCE = "open-meteo-ensemble"
# Lot RA7 : un membre à ~0 kn faisait exploser p90 (7 mois). Même plancher
# que voyage_clock.planning_speed_for ; la fourchette affichée reste de
# quelques jours autour de p50 (jamais inventée : sans membres valides → vide).
ETA_MIN_KN = PLANNING_MIN_KN
ETA_MAX_SPAN_DAYS = 7.0
ETA_TIGHTEN_TAG = "t3"
_SPEED_KEY = re.compile(r"^(?:(?P<model>.+)_)?wind_speed_10m(?:_member(?P<n>\d+))?$")

WindFn = Callable[[float, float, datetime], Dict[str, Any]]


def empty_eta(now: Optional[datetime] = None) -> dict:
    when = now or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return {
        "p10": None,
        "p50": None,
        "p90": None,
        "members": 0,
        "source": None,
        "computedAt": to_iso(when),
        "memberKnots": [],
    }


def _as_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_iso(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _norm_stop(name: str) -> str:
    return re.sub(r"[\s\-]+", "-", (name or "").strip().lower())


def match_stop(name: str, query: str) -> bool:
    n, q = _norm_stop(name), _norm_stop(query)
    if not n or not q:
        return False
    return q == n or q in n or n in q


def empirical_quantile(sorted_vals: List[float], q: float) -> Optional[float]:
    """Quantile empirique : interpolation linéaire d'indice (n−1)·q."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    q = min(1.0, max(0.0, float(q)))
    idx = (n - 1) * q
    lo = int(math.floor(idx))
    hi = min(lo + 1, n - 1)
    w = idx - lo
    return float(sorted_vals[lo]) * (1.0 - w) + float(sorted_vals[hi]) * w


def arrival_quantiles(arrivals: List[datetime]) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    if not arrivals:
        return None, None, None
    stamps = sorted(a.timestamp() for a in arrivals)
    out = []
    for q in (0.10, 0.50, 0.90):
        sec = empirical_quantile(stamps, q)
        out.append(None if sec is None else datetime.fromtimestamp(sec, tz=timezone.utc))
    return out[0], out[1], out[2]


def implied_speed_kn(remaining_nm: float, start: datetime, arrival: datetime) -> float:
    """Vitesse moyenne implicite (nm / heures) d'un membre, 0 si dégénéré."""
    hours = (arrival - start).total_seconds() / 3600.0
    if hours <= 0 or remaining_nm <= 0:
        return 0.0
    return float(remaining_nm) / hours


def tighten_eta_arrivals(
    arrivals: List[datetime],
    *,
    remaining_nm: float,
    now: datetime,
    min_kn: float = ETA_MIN_KN,
) -> List[datetime]:
    """Écarte les membres plus lents que le plancher de planification (3 kn)."""
    kept: List[datetime] = []
    for arr in arrivals or []:
        if implied_speed_kn(remaining_nm, now, arr) + 1e-9 >= float(min_kn):
            kept.append(arr)
    return kept


def bound_eta_quantiles(
    p10: Optional[datetime],
    p50: Optional[datetime],
    p90: Optional[datetime],
    max_span_days: float = ETA_MAX_SPAN_DAYS,
) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """Borne p10–p90 à une fenêtre de quelques jours autour de p50."""
    if not p10 or not p50 or not p90:
        return p10, p50, p90
    span = (p90 - p10).total_seconds() / 86400.0
    if span <= float(max_span_days) + 1e-9:
        return p10, p50, p90
    half = timedelta(days=float(max_span_days) / 2.0)
    lo = max(p10, p50 - half)
    hi = min(p90, p50 + half)
    if hi < lo:
        lo = hi = p50
    return lo, p50, hi


def tighten_eta_payload(eta: dict, now: Optional[datetime] = None) -> dict:
    """Filet : fourchette déjà calculée (cache ancien) → resserrée ou vide."""
    if not eta or _positive_members(eta.get("members")) <= 0:
        return empty_eta(now)
    knots = eta.get("memberKnots") or []
    if knots and not any(_as_kn(k) >= ETA_MIN_KN for k in knots):
        return empty_eta(now)
    try:
        p10 = _as_dt(eta["p10"]) if eta.get("p10") else None
        p50 = _as_dt(eta["p50"]) if eta.get("p50") else None
        p90 = _as_dt(eta["p90"]) if eta.get("p90") else None
    except Exception:
        return empty_eta(now)
    if not p10 or not p50 or not p90:
        return empty_eta(now)
    p10, p50, p90 = bound_eta_quantiles(p10, p50, p90)
    out = dict(eta)
    out["p10"] = to_iso(p10) if p10 else None
    out["p50"] = to_iso(p50) if p50 else None
    out["p90"] = to_iso(p90) if p90 else None
    if knots:
        out["memberKnots"] = [round(_as_kn(k), 2) for k in knots if _as_kn(k) >= ETA_MIN_KN]
    return out


def _positive_members(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def _as_kn(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_members(payload: Optional[dict]) -> Dict[str, List[dict]]:
    """Colonnes `wind_speed_10m` / `wind_speed_10m_member01` (+ préfixe modèle)."""
    hourly = (payload or {}).get("hourly") or {}
    times = hourly.get("time") or []
    speed_keys = []
    for key in hourly:
        if key == "time":
            continue
        m = _SPEED_KEY.match(key)
        if m:
            speed_keys.append((key, m.group("model") or "", m.group("n")))
    members: Dict[str, List[dict]] = {}
    rows = hours_from_om(payload)
    if not rows and times:
        return {}
    isos = sorted(rows.keys())
    for key, model, num in speed_keys:
        mid = f"{model + ':' if model else ''}{('member' + num) if num else 'control'}"
        series = []
        dir_key = key.replace("wind_speed_10m", "wind_direction_10m")
        for iso in isos:
            row = rows[iso]
            spd = row.get(key)
            if spd is None:
                continue
            try:
                series.append({
                    "t": iso,
                    "speedKnots": float(spd),
                    "dirFromDeg": None if row.get(dir_key) is None else float(row[dir_key]),
                })
            except (TypeError, ValueError):
                continue
        if series:
            members[mid] = series
    return members


def _cache_key(lat: float, lon: float) -> str:
    return f"{point_key(lat, lon)}:{ENSEMBLE_MODELS}:{FORECAST_DAYS}"


def fetch_point_members(lat: float, lon: float) -> Dict[str, List[dict]]:
    """Une requête Ensemble API, cache 6 h. Vide si panne (jamais inventé)."""
    key = _cache_key(lat, lon)
    hit = kv_get(CACHE_NS, key, max_age_s=CACHE_TTL_S)
    if hit and isinstance(hit.get("value"), dict):
        raw = hit["value"].get("members")
        if isinstance(raw, dict) and raw:
            return raw
    try:
        data = om_get(ENSEMBLE_URL, {
            "latitude": f"{float(lat):.4f}",
            "longitude": f"{float(lon):.4f}",
            "models": ENSEMBLE_MODELS,
            "hourly": "wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "kn",
            "forecast_days": FORECAST_DAYS,
            "timezone": "UTC",
            "cell_selection": "sea",
        })
    except RuntimeError:
        return {}
    members = parse_members(data)
    if members:
        kv_put(CACHE_NS, key, {"members": members, "source": SOURCE})
    return members


def sample_leg_points(points: List[dict], max_nm: float = MAX_POINT_NM) -> List[dict]:
    """Sommets de la jambe, pas ≤ 60 nm (on saute les points trop proches)."""
    if not points:
        return []
    out = [points[0]]
    last_nm = float(points[0].get("cumNm") or 0)
    last = points[0]
    for p in points[1:]:
        nm = float(p.get("cumNm") or 0)
        gap = nm - last_nm
        if gap > max_nm + 1e-6:
            steps = max(2, int(math.ceil(gap / max_nm)))
            for i in range(1, steps):
                frac = i / steps
                out.append({
                    "lat": last["lat"] + frac * (p["lat"] - last["lat"]),
                    "lon": last["lon"] + frac * (p["lon"] - last["lon"]),
                    "cumNm": last_nm + frac * gap,
                    "filmCum": float(last.get("filmCum") or last_nm) + frac * (
                        float(p.get("filmCum") or nm) - float(last.get("filmCum") or last_nm)
                    ),
                })
            out.append(p)
            last_nm, last = nm, p
        elif gap >= max_nm - 1e-6 or p is points[-1]:
            if p is not out[-1]:
                out.append(p)
            last_nm, last = nm, p
    if points[-1] is not out[-1]:
        out.append(points[-1])
    return out


def _nearest_hour(series: List[dict], when: datetime) -> Optional[dict]:
    if not series:
        return None
    return min(series, key=lambda h: abs((_as_dt(h["t"]) - when).total_seconds()))


def _nearest_point(points: List[dict], lat: float, lon: float) -> Optional[dict]:
    if not points:
        return None
    return min(points, key=lambda p: haversine(lat, lon, float(p["lat"]), float(p["lon"])))


def _climo_pack(lat: float, lon: float, t: datetime) -> dict:
    try:
        pack = atlas_wind_at_dt(lat, lon, t)
    except Exception:
        pack = {}
    pack = dict(pack or {})
    pack.setdefault("kind", "climatology")
    pack.setdefault("regime", "climatology")
    return pack


def _member_at(
    member_id: str,
    fields: List[dict],
    lat: float,
    lon: float,
    t: datetime,
    now: datetime,
) -> dict:
    """Vent du membre si t ≤ now+15 j ; sinon climatologie médiane. Mer / courant = climato."""
    climo = _climo_pack(lat, lon, t)
    horizon = now + timedelta(days=FORECAST_DAYS)
    if t > horizon:
        return climo
    pt = _nearest_point(fields, lat, lon)
    series = (pt or {}).get("members", {}).get(member_id) or []
    hour = _nearest_hour(series, t)
    if not hour or hour.get("speedKnots") is None:
        return climo
    return {
        **climo,
        "speedKnots": hour["speedKnots"],
        "dirFromDeg": hour.get("dirFromDeg") if hour.get("dirFromDeg") is not None else climo.get("dirFromDeg"),
        "kind": "ensemble",
        "regime": "ensemble",
        "source": SOURCE,
        "roseKnots": None,
    }


def _remaining_points(points: List[dict], sample: dict, end_nm: float) -> List[dict]:
    start_nm = float(sample.get("sailNm") or sample.get("filmNm") or 0)
    out = [{
        "lat": float(sample["lat"]),
        "lon": float(sample["lon"]),
        "cumNm": start_nm,
        "filmCum": float(sample.get("filmNm") or start_nm),
        "jump": False,
        "nonMaritime": False,
    }]
    for p in points or []:
        nm = float(p.get("cumNm") or 0)
        if nm <= start_nm + 0.01:
            continue
        if nm > end_nm + 0.5:
            break
        out.append(p)
    return out


def _find_stop(marks: List[dict], stop: str) -> Optional[dict]:
    for m in marks or []:
        if match_stop(str(m.get("name") or ""), stop):
            return m
    return None


def _integrate_member(
    points: List[dict],
    stop_name: str,
    now: datetime,
    polar_raw: Optional[dict],
    wind_fn: WindFn,
) -> Optional[datetime]:
    if len(points) < 2:
        return None
    end = points[-1]
    marks = [{
        "name": stop_name,
        "index": len(points) - 1,
        "nm": float(end.get("cumNm") or 0),
        "filmNm": float(end.get("filmCum") or end.get("cumNm") or 0),
        "lat": end.get("lat"),
        "lon": end.get("lon"),
    }]
    clock = build_voyage_clock(
        points, marks, now, polar_raw=polar_raw,
        start_at="saint-maur", wind_fn=wind_fn,
    )
    for m in clock.get("marks") or []:
        if match_stop(str(m.get("name") or ""), stop_name) and m.get("iso"):
            return _as_dt(m["iso"])
    iso = clock.get("arrivalIso")
    return _as_dt(iso) if iso else None


def compute_eta(
    *,
    points: List[dict],
    marks: List[dict],
    stop: str,
    now: datetime,
    polar_raw: Optional[dict] = None,
    sample: Optional[dict] = None,
    clock: Optional[dict] = None,
) -> dict:
    """Intègre la jambe restante pour chaque membre → p10 / p50 / p90.

    `sample` = position actuelle (sinon échantillon d'horloge à `now`).
    """
    now = _as_dt(now)
    empty = empty_eta(now)
    stop_mark = _find_stop(marks, stop)
    if not stop_mark or not points:
        return empty
    if sample is None and clock:
        sample = sample_clock_at_time(clock, now)
    if not sample or sample.get("lat") is None:
        return empty
    result_key = (
        f"eta:{_norm_stop(stop)}:{point_key(sample['lat'], sample['lon'])}"
        f":{now.strftime('%Y-%m-%d')}:{now.hour // 6}:{ETA_TIGHTEN_TAG}"
    )
    cached = kv_get(CACHE_NS, result_key, max_age_s=CACHE_TTL_S)
    if cached and isinstance(cached.get("value"), dict) and cached["value"].get("members"):
        return tighten_eta_payload(cached["value"], now)
    end_nm = float(stop_mark.get("nm") or stop_mark.get("filmNm") or 0)
    start_nm = float(sample.get("sailNm") or sample.get("filmNm") or 0)
    if end_nm <= start_nm + 0.5:
        return empty
    remaining = _remaining_points(points, sample, end_nm)
    if len(remaining) < 2:
        return empty
    probes = sample_leg_points(remaining, MAX_POINT_NM)
    fields: List[dict] = []
    member_ids: set[str] = set()
    for p in probes:
        try:
            members = fetch_point_members(float(p["lat"]), float(p["lon"]))
        except RuntimeError:
            members = {}
        except Exception as exc:
            log.info("ensemble %s: %s", point_key(p["lat"], p["lon"]), exc)
            members = {}
        if members:
            fields.append({"lat": p["lat"], "lon": p["lon"], "members": members})
            member_ids.update(members)
    if not fields or not member_ids:
        return empty
    arrivals: List[datetime] = []
    for mid in sorted(member_ids):
        def wind_fn(lat, lon, t, _mid=mid):
            return _member_at(_mid, fields, lat, lon, t, now)
        try:
            arrived = _integrate_member(remaining, str(stop_mark.get("name") or stop), now, polar_raw, wind_fn)
        except Exception as exc:
            log.info("ensemble integrate %s: %s", mid, exc)
            arrived = None
        if arrived is not None:
            arrivals.append(arrived)
    if not arrivals:
        return empty
    remaining_nm = max(0.0, end_nm - start_nm)
    kept = tighten_eta_arrivals(arrivals, remaining_nm=remaining_nm, now=now)
    if not kept:
        return empty
    member_knots = [round(implied_speed_kn(remaining_nm, now, arr), 2) for arr in kept]
    p10, p50, p90 = arrival_quantiles(kept)
    p10, p50, p90 = bound_eta_quantiles(p10, p50, p90)
    if not p10 or not p50 or not p90:
        return empty
    out = {
        "p10": to_iso(p10),
        "p50": to_iso(p50),
        "p90": to_iso(p90),
        "members": len(kept),
        "source": SOURCE,
        "computedAt": to_iso(now),
        "memberKnots": member_knots,
    }
    kv_put(CACHE_NS, result_key, out)
    return out


def official_eta(voy: dict, stop: str, now: datetime, polar_raw: Optional[dict] = None) -> dict:
    clock = voy.get("clock")
    if not clock:
        clock = build_voyage_clock(
            voy.get("points") or [],
            voy.get("marks") or [],
            voy.get("t0") or now,
            polar_raw=polar_raw,
            start_at=voy.get("startAt") or "la-rochelle",
        )
    return tighten_eta_payload(compute_eta(
        points=voy.get("points") or [],
        marks=voy.get("marks") or clock.get("marks") or [],
        stop=stop,
        now=now,
        polar_raw=polar_raw,
        clock=clock,
    ), now)

"""wind_fn(lat, lon, t) : prévision 0–7 j, fondu 7–10 j, climatologie ensuite."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from climatology_zones import zone_wind_at
from forecast_cube import ForecastCube
from voyage_clock import parse_iso

FORECAST_FULL_HOURS = 7 * 24
FORECAST_BLEND_END_HOURS = 10 * 24


def _hours_since(t0: datetime, t: datetime) -> float:
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    if t0.tzinfo is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    return (t - t0).total_seconds() / 3600.0


def _blend_dir(a: float, b: float, w: float) -> float:
    """w = poids de b (0 = a, 1 = b). Plus courte arc."""
    d = (b - a + 540) % 360 - 180
    return (a + d * w + 360) % 360


def blended_wind(
    lat: float,
    lon: float,
    t: datetime,
    t0: datetime | str,
    cube: Optional[ForecastCube],
) -> Dict[str, Any]:
    t0d = parse_iso(t0) if not isinstance(t0, datetime) else t0
    hours = _hours_since(t0d, t)
    climo = zone_wind_at(lat, lon, t.month)

    if cube is None or hours > FORECAST_BLEND_END_HOURS:
        return {**climo, "hs": None}

    fc = cube.at(lat, lon, t)
    if fc is None:
        return {**climo, "reason": "no_forecast_cell", "hs": None}

    if hours < FORECAST_FULL_HOURS:
        return fc

    # Linear fade of knots (and direction) between D+7 and D+10.
    w = (hours - FORECAST_FULL_HOURS) / float(FORECAST_BLEND_END_HOURS - FORECAST_FULL_HOURS)
    w = max(0.0, min(1.0, w))
    return {
        "speedKnots": fc["speedKnots"] * (1 - w) + climo["speedKnots"] * w,
        "dirFromDeg": _blend_dir(fc["dirFromDeg"], climo["dirFromDeg"], w),
        "hs": fc.get("hs"),
        "uo": fc.get("uo"),
        "vo": fc.get("vo"),
        "kind": "forecast" if w < 1 else "climatology",
        "model": fc.get("model"),
        "leadHours": fc.get("leadHours"),
        "source": "blend",
        "blend": round(w, 3),
    }


def make_wind_fn(t0: datetime | str, cube: Optional[ForecastCube]):
    def wind_fn(lat: float, lon: float, t: datetime) -> Dict[str, Any]:
        return blended_wind(lat, lon, t, t0, cube)
    return wind_fn

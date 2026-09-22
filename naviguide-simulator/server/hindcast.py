"""Hindcast multi-sources — Open-Meteo + Copernicus, fusion par médiane.

Une source en panne manque ; aucune source → champ vide (jamais inventé).
Cache SQLite `pearl_store.kv` ns `hindcast`, clé (point, produit, jour).
"""
from __future__ import annotations

import logging
import math
import os
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import httpx

from pearl_store import kv_get, kv_put
from voyage_clock import parse_iso, to_iso

log = logging.getLogger("naviguide-simulator.hindcast")

ERA5_STRONG_WIND_FACTOR = 1.05
ERA5_STRONG_WIND_MS = 15.0
MS_TO_KN = 1.943844
HINDCAST_PAD_DAYS = 2
CACHE_NS = "hindcast"
FETCH_TIMEOUT_S = 20.0
POINT_DECIMALS = 3

OM_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
OM_ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
OM_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
OM_WIND_HOURLY = "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
OM_MARINE_HOURLY = (
    "wave_height,wave_direction,wave_period,"
    "ocean_current_velocity,ocean_current_direction"
)
OM_MARINE_HOURLY_WAVES = "wave_height,wave_direction,wave_period"

SRC_OM_FORECAST = "om-forecast"
SRC_OM_ERA5 = "om-era5"
SRC_OM_MARINE = "om-marine"
SRC_CMEMS_WIND = "cmems-wind"
SRC_CMEMS_WAVE = "cmems-wave"
SRC_CMEMS_PHY = "cmems-phy"

PRODUCTS = (
    SRC_OM_FORECAST,
    SRC_OM_ERA5,
    SRC_OM_MARINE,
    SRC_CMEMS_WIND,
    SRC_CMEMS_WAVE,
    SRC_CMEMS_PHY,
)
# Vent du passé pour l'horloge (lot RA8) : ERA5 Open-Meteo, sans Copernicus.
ERA5_PRODUCTS = (SRC_OM_ERA5,)

# Tests branchent un client / des fetchers CMEMS. Jamais le réseau réel.
_http_factory: Optional[Callable[[], httpx.Client]] = None
_cmems_wind: Optional[Callable] = None
_cmems_wave: Optional[Callable] = None
_cmems_phy: Optional[Callable] = None
_fetch_blocked = False


def bind_http(factory: Optional[Callable[[], httpx.Client]]) -> None:
    global _http_factory
    _http_factory = factory


def bind_cmems(*, wind=None, wave=None, phy=None) -> None:
    global _cmems_wind, _cmems_wave, _cmems_phy
    _cmems_wind, _cmems_wave, _cmems_phy = wind, wave, phy


def block_network() -> None:
    """Deuxième appel cache : tout fetch lève (test « sans réseau »)."""
    global _fetch_blocked
    _fetch_blocked = True


def unblock_network() -> None:
    global _fetch_blocked
    _fetch_blocked = False


def reset_hooks() -> None:
    bind_http(None)
    bind_cmems(wind=None, wave=None, phy=None)
    unblock_network()


def hindcast_enabled() -> bool:
    raw = (os.getenv("NAVIGUIDE_HINDCAST") or "1").lower()
    if raw in ("0", "false", "no"):
        return False
    if (os.getenv("NAVIGUIDE_FORECAST_BACKEND") or "").lower() == "synthetic":
        return False
    return True


def point_key(lat: float, lon: float) -> str:
    return f"{round(float(lat), POINT_DECIMALS):.{POINT_DECIMALS}f}:{round(float(lon), POINT_DECIMALS):.{POINT_DECIMALS}f}"


def cache_key(lat: float, lon: float, product: str, day: str) -> str:
    return f"{point_key(lat, lon)}:{product}:{day}"


def _day_str(day: str | datetime) -> str:
    if isinstance(day, datetime):
        if day.tzinfo is None:
            day = day.replace(tzinfo=timezone.utc)
        return day.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return str(day)[:10]


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_iso(str(value) if "T" in str(value) else f"{value}T00:00:00Z")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def uv_to_wind_from(u: float, v: float) -> tuple[float, float]:
    """eastward, northward (m/s) → (kn, direction « de »)."""
    speed_ms = math.sqrt(u * u + v * v)
    from_deg = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
    return speed_ms * MS_TO_KN, from_deg


def uv_to_current_to(uo: float, vo: float) -> tuple[float, float]:
    """uo, vo (m/s) → (kn, direction « vers »). uo=1, vo=0 → 90°."""
    speed_ms = math.sqrt(uo * uo + vo * vo)
    to_deg = (math.degrees(math.atan2(uo, vo)) + 360.0) % 360.0
    return speed_ms * MS_TO_KN, to_deg


def apply_era5_correction(speed_kn: float) -> float:
    """Facteur 1,05 seulement au-dessus de 15 m/s, seulement ERA5."""
    speed_ms = float(speed_kn) / MS_TO_KN
    if speed_ms > ERA5_STRONG_WIND_MS:
        speed_ms *= ERA5_STRONG_WIND_FACTOR
    return speed_ms * MS_TO_KN


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def _circ_median(degs: List[float]) -> Optional[float]:
    if not degs:
        return None
    if len(degs) == 1:
        return float(degs[0]) % 360.0
    best, best_s = degs[0], float("inf")
    for cand in degs:
        s = sum(abs(((x - cand + 180.0) % 360.0) - 180.0) for x in degs)
        if s < best_s:
            best, best_s = cand, s
    return float(best) % 360.0


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def _client() -> httpx.Client:
    if _http_factory:
        return _http_factory()
    return httpx.Client(timeout=FETCH_TIMEOUT_S)


def _om_get(url: str, params: dict) -> Optional[dict]:
    if _fetch_blocked:
        raise RuntimeError("hindcast network blocked")
    try:
        with _client() as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        log.info("open-meteo %s: %s", url.split("/")[2], exc)
        return None


def om_get(url: str, params: dict) -> Optional[dict]:
    """Client HTTP Open-Meteo partagé (hindcast, ensembles). `None` si panne."""
    return _om_get(url, params)


def hours_from_om(payload: Optional[dict]) -> Dict[str, dict]:
    return _hours_from_om(payload)


def _hours_from_om(payload: Optional[dict]) -> Dict[str, dict]:
    hourly = (payload or {}).get("hourly") or {}
    times = hourly.get("time") or []
    out: Dict[str, dict] = {}
    for i, raw in enumerate(times):
        try:
            iso = to_iso(parse_iso(raw if "Z" in raw or "+" in raw[10:] else f"{raw}:00Z" if len(raw) == 16 else f"{raw}Z"))
        except Exception:
            continue
        out[iso] = {k: (hourly[k][i] if i < len(hourly.get(k) or []) else None) for k in hourly if k != "time"}
    return out


def _fetch_om_forecast(lat: float, lon: float, day: str) -> Optional[dict]:
    data = _om_get(OM_FORECAST_URL, {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": day,
        "end_date": day,
        "hourly": OM_WIND_HOURLY,
        "wind_speed_unit": "kn",
        "timezone": "UTC",
    })
    if data is None:
        return None
    hours = {}
    for iso, row in _hours_from_om(data).items():
        hours[iso] = {
            "speedKnots": _num(row.get("wind_speed_10m")),
            "dirFromDeg": _num(row.get("wind_direction_10m")),
            "gustKnots": _num(row.get("wind_gusts_10m")),
        }
    return {"hours": hours, "source": SRC_OM_FORECAST}


def _fetch_om_era5(lat: float, lon: float, day: str) -> Optional[dict]:
    data = _om_get(OM_ERA5_URL, {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": day,
        "end_date": day,
        "hourly": OM_WIND_HOURLY,
        "wind_speed_unit": "kn",
        "timezone": "UTC",
    })
    if data is None:
        return None
    hours = {}
    for iso, row in _hours_from_om(data).items():
        raw = _num(row.get("wind_speed_10m"))
        hours[iso] = {
            "speedKnots": apply_era5_correction(raw) if raw is not None else None,
            "dirFromDeg": _num(row.get("wind_direction_10m")),
            "gustKnots": _num(row.get("wind_gusts_10m")),
        }
    return {"hours": hours, "source": SRC_OM_ERA5}


def _fetch_om_marine(lat: float, lon: float, day: str) -> Optional[dict]:
    data = _om_get(OM_MARINE_URL, {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": day,
        "end_date": day,
        "hourly": OM_MARINE_HOURLY,
        "timezone": "UTC",
    })
    if data is None:
        data = _om_get(OM_MARINE_URL, {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "start_date": day,
            "end_date": day,
            "hourly": OM_MARINE_HOURLY_WAVES,
            "timezone": "UTC",
        })
    if data is None:
        return None
    hours = {}
    for iso, row in _hours_from_om(data).items():
        current_ms = _num(row.get("ocean_current_velocity"))
        hours[iso] = {
            "hs": _num(row.get("wave_height")),
            "waveDirFromDeg": _num(row.get("wave_direction")),
            "wavePeriodS": _num(row.get("wave_period")),
            "currentKn": None if current_ms is None else current_ms * MS_TO_KN,
            "currentToDeg": _num(row.get("ocean_current_direction")),
        }
    return {"hours": hours, "source": SRC_OM_MARINE}


def _cmems_creds() -> tuple[Optional[str], Optional[str]]:
    return os.getenv("COPERNICUS_USERNAME"), os.getenv("COPERNICUS_PASSWORD")


def _cmems_hook(product: str):
    if product == SRC_CMEMS_WIND:
        return _cmems_wind
    if product == SRC_CMEMS_WAVE:
        return _cmems_wave
    if product == SRC_CMEMS_PHY:
        return _cmems_phy
    return None


def _product_enabled(product: str) -> bool:
    """CMEMS : seulement si un hook de test ou des identifiants sont là.

    Sans ça, RA8 ne tente même pas Copernicus — le vent du passé vient d'ERA5.
    """
    if product not in (SRC_CMEMS_WIND, SRC_CMEMS_WAVE, SRC_CMEMS_PHY):
        return True
    if _cmems_hook(product) is not None:
        return True
    user, password = _cmems_creds()
    return bool(user and password)


def _window_for_day(day: str) -> tuple[datetime, datetime]:
    d0 = parse_iso(f"{day}T00:00:00Z")
    start = d0 - timedelta(days=HINDCAST_PAD_DAYS)
    end = d0 + timedelta(days=HINDCAST_PAD_DAYS, hours=23)
    return start, end


def _split_cmems_by_day(rows: List[dict]) -> Dict[str, dict]:
    by_day: Dict[str, dict] = {}
    for row in rows or []:
        t = row.get("t")
        if not t:
            continue
        day = str(t)[:10]
        by_day.setdefault(day, {"hours": {}})
        by_day[day]["hours"][t] = {k: v for k, v in row.items() if k != "t"}
    return by_day


def _fetch_cmems_wind(lat: float, lon: float, day: str) -> Optional[dict]:
    if _fetch_blocked:
        raise RuntimeError("hindcast network blocked")
    start, end = _window_for_day(day)
    hook = _cmems_wind
    if hook is None:
        try:
            from copernicus.getWind import get_wind_series
            user, password = _cmems_creds()
            hook = lambda la, lo, s, e: get_wind_series(la, lo, start=s, end=e, username=user, password=password)
        except Exception as exc:
            log.info("cmems-wind import: %s", exc)
            return None
    try:
        rows = hook(lat, lon, start, end) or []
    except Exception as exc:
        log.info("cmems-wind: %s", exc)
        return None
    by_day = _split_cmems_by_day(rows)
    packed = by_day.get(day)
    return {"hours": (packed or {}).get("hours") or {}, "source": SRC_CMEMS_WIND, "extraDays": by_day}


def _fetch_cmems_wave(lat: float, lon: float, day: str) -> Optional[dict]:
    if _fetch_blocked:
        raise RuntimeError("hindcast network blocked")
    start, end = _window_for_day(day)
    hook = _cmems_wave
    if hook is None:
        try:
            from copernicus.getWave import get_wave_series
            user, password = _cmems_creds()
            hook = lambda la, lo, s, e: get_wave_series(la, lo, start=s, end=e, username=user, password=password)
        except Exception as exc:
            log.info("cmems-wave import: %s", exc)
            return None
    try:
        rows = hook(lat, lon, start, end) or []
    except Exception as exc:
        log.info("cmems-wave: %s", exc)
        return None
    by_day = _split_cmems_by_day(rows)
    packed = by_day.get(day)
    return {"hours": (packed or {}).get("hours") or {}, "source": SRC_CMEMS_WAVE, "extraDays": by_day}


def _fetch_cmems_phy(lat: float, lon: float, day: str) -> Optional[dict]:
    if _fetch_blocked:
        raise RuntimeError("hindcast network blocked")
    start, end = _window_for_day(day)
    hook = _cmems_phy
    if hook is None:
        try:
            from copernicus.getCurrent import get_current_series
            user, password = _cmems_creds()
            hook = lambda la, lo, s, e: get_current_series(la, lo, start=s, end=e, username=user, password=password)
        except Exception as exc:
            log.info("cmems-phy import: %s", exc)
            return None
    try:
        rows = hook(lat, lon, start, end) or []
    except Exception as exc:
        log.info("cmems-phy: %s", exc)
        return None
    by_day = _split_cmems_by_day(rows)
    packed = by_day.get(day)
    return {"hours": (packed or {}).get("hours") or {}, "source": SRC_CMEMS_PHY, "extraDays": by_day}


_FETCHERS = {
    SRC_OM_FORECAST: _fetch_om_forecast,
    SRC_OM_ERA5: _fetch_om_era5,
    SRC_OM_MARINE: _fetch_om_marine,
    SRC_CMEMS_WIND: _fetch_cmems_wind,
    SRC_CMEMS_WAVE: _fetch_cmems_wave,
    SRC_CMEMS_PHY: _fetch_cmems_phy,
}


def _blend_cache_id(products: tuple) -> str:
    wanted = tuple(products)
    if wanted == PRODUCTS:
        return "blend"
    return "blend:" + "+".join(wanted)


def _load_product(lat: float, lon: float, product: str, day: str, *, fetch: bool = True) -> Optional[dict]:
    key = cache_key(lat, lon, product, day)
    hit = kv_get(CACHE_NS, key)
    if hit and isinstance(hit.get("value"), dict):
        return hit["value"]
    if _fetch_blocked:
        raise RuntimeError("hindcast network blocked")
    if not fetch:
        return None
    fetcher = _FETCHERS[product]
    raw = fetcher(lat, lon, day)
    if raw is None:
        return None
    extra = raw.pop("extraDays", None)
    stored = {"hours": raw.get("hours") or {}, "source": product}
    kv_put(CACHE_NS, key, stored)
    if extra:
        for extra_day, pack in extra.items():
            if extra_day == day:
                continue
            kv_put(CACHE_NS, cache_key(lat, lon, product, extra_day), {
                "hours": pack.get("hours") or {},
                "source": product,
            })
    return stored


def _fuse_scalar(samples: List[tuple[str, float]], circular: bool = False) -> dict:
    if not samples:
        return {"value": None, "sources": [], "spread": None, "values": {}}
    values = {src: val for src, val in samples}
    nums = list(values.values())
    if circular:
        value = _circ_median(nums)
        arcs = [abs(((x - y + 180.0) % 360.0) - 180.0) for x in nums for y in nums]
        spread = max(arcs) if arcs else 0.0
    else:
        value = _median(nums)
        spread = (max(nums) - min(nums)) if nums else None
    return {
        "value": None if value is None else round(float(value), 3),
        "sources": [src for src, _ in samples],
        "spread": None if spread is None else round(float(spread), 3),
        "values": values,
    }


def _fuse_hour(by_source: Dict[str, dict]) -> dict:
    wind_speed, wind_dir, gust = [], [], []
    hs, wave_dir, period = [], [], []
    cur_kn, cur_to = [], []
    for src, row in by_source.items():
        if row.get("speedKnots") is not None:
            wind_speed.append((src, float(row["speedKnots"])))
        if row.get("dirFromDeg") is not None:
            wind_dir.append((src, float(row["dirFromDeg"])))
        if row.get("gustKnots") is not None:
            gust.append((src, float(row["gustKnots"])))
        if row.get("hs") is not None:
            hs.append((src, float(row["hs"])))
        if row.get("waveDirFromDeg") is not None:
            wave_dir.append((src, float(row["waveDirFromDeg"])))
        if row.get("wavePeriodS") is not None:
            period.append((src, float(row["wavePeriodS"])))
        if row.get("currentKn") is not None:
            cur_kn.append((src, float(row["currentKn"])))
        if row.get("currentToDeg") is not None:
            cur_to.append((src, float(row["currentToDeg"])))
    fused = {
        "speedKnots": _fuse_scalar(wind_speed),
        "dirFromDeg": _fuse_scalar(wind_dir, circular=True),
        "gustKnots": _fuse_scalar(gust),
        "hs": _fuse_scalar(hs),
        "waveDirFromDeg": _fuse_scalar(wave_dir, circular=True),
        "wavePeriodS": _fuse_scalar(period),
        "currentKn": _fuse_scalar(cur_kn),
        "currentToDeg": _fuse_scalar(cur_to, circular=True),
    }
    sources = []
    for src in PRODUCTS:
        if src in by_source:
            sources.append(src)
    return {
        "speedKnots": fused["speedKnots"]["value"],
        "dirFromDeg": fused["dirFromDeg"]["value"],
        "gustKnots": fused["gustKnots"]["value"],
        "hs": fused["hs"]["value"],
        "waveDirFromDeg": fused["waveDirFromDeg"]["value"],
        "wavePeriodS": fused["wavePeriodS"]["value"],
        "currentKn": fused["currentKn"]["value"],
        "currentToDeg": fused["currentToDeg"]["value"],
        "sources": sources,
        "spread": fused["speedKnots"]["spread"],
        "byVar": fused,
        "bySource": by_source,
        "kind": "hindcast",
        "regime": "hindcast",
    }


def series(
    lat: float,
    lon: float,
    day: str | datetime,
    *,
    products: Optional[tuple] = None,
    fetch: bool = True,
) -> dict:
    """Vent / houle / courant horaires du `day` (UTC), sources demandées, médiane.

    `products=ERA5_PRODUCTS` : archive Open-Meteo seulement (lot RA8).
    `fetch=False` : cache uniquement, aucun appel réseau.
    """
    day = _day_str(day)
    wanted = tuple(products) if products else PRODUCTS
    blend_key = cache_key(lat, lon, _blend_cache_id(wanted), day)
    hit = kv_get(CACHE_NS, blend_key)
    if hit and isinstance(hit.get("value"), dict) and hit["value"].get("hours"):
        return hit["value"]

    loaded: Dict[str, dict] = {}
    for product in wanted:
        if not _product_enabled(product):
            continue
        try:
            pack = _load_product(lat, lon, product, day, fetch=fetch)
        except RuntimeError:
            raise
        except Exception as exc:
            log.info("hindcast %s: %s", product, exc)
            pack = None
        if pack and pack.get("hours"):
            loaded[product] = pack

    times: set[str] = set()
    for pack in loaded.values():
        times.update(pack.get("hours") or {})
    hours = []
    for iso in sorted(times):
        by_source = {}
        for src, pack in loaded.items():
            row = (pack.get("hours") or {}).get(iso)
            if row:
                by_source[src] = row
        fused = _fuse_hour(by_source)
        fused["t"] = iso
        hours.append(fused)
    out = {
        "day": day,
        "lat": round(float(lat), 4),
        "lon": round(float(lon), 4),
        "hours": hours,
        "products": sorted(loaded.keys()),
    }
    if fetch:
        kv_put(CACHE_NS, blend_key, out)
    return out


def at(
    lat: float,
    lon: float,
    t: datetime | str,
    *,
    products: Optional[tuple] = None,
    fetch: bool = True,
) -> dict:
    """Heure la plus proche ; champs vides si rien n'a répondu."""
    when = _as_dt(t)
    day = when.strftime("%Y-%m-%d")
    try:
        packed = series(lat, lon, day, products=products, fetch=fetch)
    except Exception:
        packed = {"hours": []}
    hours = packed.get("hours") or []
    if not hours:
        return {
            "speedKnots": None,
            "dirFromDeg": None,
            "gustKnots": None,
            "hs": None,
            "currentKn": None,
            "currentToDeg": None,
            "sources": [],
            "spread": None,
            "kind": "hindcast",
            "regime": "hindcast",
            "reason": "hindcast_empty",
        }
    target = to_iso(when)
    best = min(hours, key=lambda h: abs((parse_iso(h["t"]) - when).total_seconds()))
    return {**best, "kind": "hindcast", "regime": "hindcast", "t": best.get("t") or target}


def empty_pack() -> dict:
    return {
        "speedKnots": None,
        "dirFromDeg": None,
        "sources": [],
        "spread": None,
        "kind": "hindcast",
        "regime": "hindcast",
        "reason": "hindcast_empty",
    }


def past_passage_slots(clock: dict, now: datetime | str) -> List[tuple[float, float, str]]:
    """(lat, lon, jour) des sommets déjà parcourus, hors avion."""
    now_d = _as_dt(now)
    slots: List[tuple[float, float, str]] = []
    seen: set[tuple[str, str]] = set()
    for v in (clock or {}).get("vertices") or []:
        if v.get("vehicle") in ("plane", "side"):
            continue
        iso = v.get("iso")
        if not iso or v.get("lat") is None or v.get("lon") is None:
            continue
        try:
            t = parse_iso(iso)
        except Exception:
            continue
        if t >= now_d:
            continue
        day = t.strftime("%Y-%m-%d")
        key = (point_key(v["lat"], v["lon"]), day)
        if key in seen:
            continue
        seen.add(key)
        slots.append((float(v["lat"]), float(v["lon"]), day))
    return slots


def uncovered_era5_slots(clock: dict, now: datetime | str) -> List[tuple[float, float, str]]:
    """Points du passé sans série ERA5 en cache — à compléter en fond."""
    missing: List[tuple[float, float, str]] = []
    for lat, lon, day in past_passage_slots(clock, now):
        hit = kv_get(CACHE_NS, cache_key(lat, lon, SRC_OM_ERA5, day))
        hours = ((hit or {}).get("value") or {}).get("hours") if hit else None
        if not hours:
            missing.append((lat, lon, day))
    return missing


def fill_era5_along(slots, *, fetch: bool = True) -> int:
    """Archive ERA5 Open-Meteo le long du trait, sans Copernicus.

    Une série par (point arrondi, jour). Le cache SQLite évite le retéléchargement.
    """
    n = 0
    seen: set[tuple[str, str]] = set()
    for item in slots or []:
        if not item or len(item) < 3:
            continue
        try:
            lat, lon, day = float(item[0]), float(item[1]), _day_str(item[2])
        except (TypeError, ValueError):
            continue
        key = (point_key(lat, lon), day)
        if key in seen:
            continue
        seen.add(key)
        try:
            packed = series(lat, lon, day, products=ERA5_PRODUCTS, fetch=fetch)
        except Exception as exc:
            log.info("era5 fill %s: %s", key, exc)
            continue
        if packed.get("hours"):
            n += 1
    return n

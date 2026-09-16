"""NAVIGUIDE simulator API — searoute, polar (sans chat), proxies, vent."""
from __future__ import annotations

import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import httpx

from mem_limits import (
    ZEE_CACHE_MAX_BYTES,
    ZEE_MAX_FEATURES_CAP,
    ZEE_NO_BBOX_MAX_FEATURES,
    ZEE_RESPONSE_MAX_BYTES,
    lru_set,
    too_large,
)
from ici_engine import ICI_RADIUS_NM, fetch_wpi_features, fill_dossier
from polar_api import router as polar_router
from route_engine import searoute_with_exact_end
from voyage_api import router as voyage_router

load_dotenv()

COPERNICUS_USERNAME = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASSWORD = os.getenv("COPERNICUS_PASSWORD")

try:
    from copernicus.getWind import get_wind_data_at_position
    from copernicus.getWave import get_wave_data_at_position
    from copernicus.getCurrent import get_current_data_at_position
except Exception:
    get_wind_data_at_position = None
    get_wave_data_at_position = None
    get_current_data_at_position = None

app = FastAPI(
    title="NAVIGUIDE simulator",
    description="Cockpit Berry-Mappemonde — hors production.",  # pragma: allowlist secret
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(polar_router)
app.include_router(voyage_router)


@app.on_event("startup")
def _startup_official_grib():
    """Dernier GRIB dès le boot serveur — pas attendre le premier GET front."""
    try:
        from voyage_api import _kick_official_grib
        _kick_official_grib()
    except Exception:
        pass


class PositionRequest(BaseModel):
    latitude: float
    longitude: float


_WEATHER_CACHE_TTL = 300.0
_WEATHER_CACHE_MAX = 256
_WEATHER_CELL_DEG = 0.25
_weather_cache: dict = {}


def _weather_cell(kind: str, lat: float, lon: float) -> tuple[str, int, int]:
    wrapped_lon = ((float(lon) + 180.0) % 360.0) - 180.0
    return (
        kind,
        math.floor((float(lat) + 90.0) / _WEATHER_CELL_DEG),
        math.floor((wrapped_lon + 180.0) / _WEATHER_CELL_DEG),
    )


def _cached_weather(kind: str, request: PositionRequest, loader) -> dict:
    key = _weather_cell(kind, request.latitude, request.longitude)
    now = time.monotonic()
    hit = _weather_cache.get(key)
    if hit and now - hit["at"] < _WEATHER_CACHE_TTL:
        return dict(hit["data"])
    data = loader(request)
    lru_set(_weather_cache, key, {"at": now, "data": dict(data)}, max_items=_WEATHER_CACHE_MAX)
    return data


@app.get("/")
def health():
    return {"service": "naviguide-simulator", "version": "0.2.0"}


@app.get("/ici")
async def get_ici(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_nm: float = Query(ICI_RADIUS_NM, ge=5, le=40),
    month: int | None = Query(None, ge=1, le=12),
    dest_lat: float | None = Query(None),
    dest_lon: float | None = Query(None),
):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(400, "lat/lon hors limites")
    if dest_lat is not None and not (-90 <= dest_lat <= 90):
        raise HTTPException(400, "dest_lat hors limites")
    if dest_lon is not None and not (-180 <= dest_lon <= 180):
        raise HTTPException(400, "dest_lon hors limites")
    return await fill_dossier(lat, lon, radius_nm, month=month, dest_lat=dest_lat, dest_lon=dest_lon)


@app.get("/route")
def get_route(
    start_lat: float = Query(...),
    start_lon: float = Query(...),
    end_lat: float = Query(...),
    end_lon: float = Query(...),
    check_wind: bool = Query(False),
):
    start = (start_lon, start_lat)
    end = (end_lon, end_lat)
    try:
        route = searoute_with_exact_end(start, end)
        if route is None:
            raise HTTPException(status_code=404, detail="Route non trouvée")
        return route
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _sim_wind(lat: float, lon: float) -> dict:
    import datetime
    import random

    rng = random.Random(int(abs(lat * 100) + abs(lon * 100)))
    speed_ms = rng.uniform(3, 18)
    direction = round(rng.uniform(0, 360), 1)
    u = round(-speed_ms * math.sin(math.radians(direction)), 3)
    v = round(-speed_ms * math.cos(math.radians(direction)), 3)
    return {
        "latitude": lat,
        "longitude": lon,
        "u_component": u,
        "v_component": v,
        "wind_speed": round(speed_ms, 2),
        "wind_speed_kmh": round(speed_ms * 3.6, 1),
        "wind_speed_knots": round(speed_ms * 1.944, 1),
        "wind_direction": direction,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "simulation": True,
        "source": "estimated (Copernicus unavailable)",
    }


def _sim_wave(lat: float, lon: float) -> dict:
    import datetime
    import random

    rng = random.Random(int(abs(lat * 137) + abs(lon * 73)))
    return {
        "latitude": lat,
        "longitude": lon,
        "significant_wave_height_m": round(rng.uniform(0.3, 4.5), 2),
        "mean_wave_period": round(rng.uniform(4, 14), 1),
        "mean_wave_direction": round(rng.uniform(0, 360), 1),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "simulation": True,
        "source": "estimated (Copernicus unavailable)",
    }


def _sim_current(lat: float, lon: float) -> dict:
    import datetime
    import random

    rng = random.Random(int(abs(lat * 211) + abs(lon * 157)))
    speed_ms = rng.uniform(0.05, 1.2)
    direction = round(rng.uniform(0, 360), 1)
    return {
        "latitude": lat,
        "longitude": lon,
        "u_component": round(speed_ms * math.sin(math.radians(direction)), 4),
        "v_component": round(speed_ms * math.cos(math.radians(direction)), 4),
        "speed_ms": round(speed_ms, 3),
        "speed_knots": round(speed_ms * 1.944, 2),
        "speed_kmh": round(speed_ms * 3.6, 2),
        "direction_deg": direction,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "simulation": True,
        "source": "estimated (Copernicus unavailable)",
    }


def _load_wind(request: PositionRequest) -> dict:
    try:
        if COPERNICUS_USERNAME and COPERNICUS_PASSWORD and get_wind_data_at_position:
            wind_data = get_wind_data_at_position(
                latitude=request.latitude,
                longitude=request.longitude,
                username=COPERNICUS_USERNAME,
                password=COPERNICUS_PASSWORD,
            )
            if wind_data is not None:
                return wind_data
    except Exception:
        pass
    return _sim_wind(request.latitude, request.longitude)


def _load_wave(request: PositionRequest) -> dict:
    try:
        if COPERNICUS_USERNAME and COPERNICUS_PASSWORD and get_wave_data_at_position:
            wave_data = get_wave_data_at_position(
                latitude=request.latitude,
                longitude=request.longitude,
                username=COPERNICUS_USERNAME,
                password=COPERNICUS_PASSWORD,
            )
            if wave_data is not None:
                return wave_data
    except Exception:
        pass
    return _sim_wave(request.latitude, request.longitude)


def _load_current(request: PositionRequest) -> dict:
    try:
        if COPERNICUS_USERNAME and COPERNICUS_PASSWORD and get_current_data_at_position:
            current_data = get_current_data_at_position(
                latitude=request.latitude,
                longitude=request.longitude,
                username=COPERNICUS_USERNAME,
                password=COPERNICUS_PASSWORD,
            )
            if current_data is not None:
                return current_data
    except Exception:
        pass
    return _sim_current(request.latitude, request.longitude)


@app.post("/wind")
def get_wind(request: PositionRequest):
    return _cached_weather("wind", request, _load_wind)


@app.post("/wave")
def get_wave(request: PositionRequest):
    return _cached_weather("wave", request, _load_wave)


@app.post("/current")
def get_current(request: PositionRequest):
    return _cached_weather("current", request, _load_current)


@app.post("/weather")
def get_weather(request: PositionRequest):
    """Une requête UI, trois produits dédupliqués par cellule."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        wind = pool.submit(get_wind, request)
        wave = pool.submit(get_wave, request)
        current = pool.submit(get_current, request)
        return {
            "wind": wind.result(),
            "wave": wave.result(),
            "current": current.result(),
        }


_WPI_CACHE_TTL = 86_400
_zee_cache: dict = {"entries": {}}
_ZEE_CACHE_TTL = 86_400
_VLIZ_WMS = "https://geo.vliz.be/geoserver/MarineRegions/wms"
_WMS_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=21600, stale-while-revalidate=86400",
}
_SEAMARK_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
}

_DMS_RE = re.compile(
    r"""(\d+)\s*[°d]\s*(\d+)\s*[''′]\s*(\d+(?:\.\d+)?)\s*[""″]?\s*([NSEW]?)""",
    re.IGNORECASE,
)


def _parse_coord(value: Optional[Union[str, float, int]]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    m = _DMS_RE.search(s)
    if m:
        deg, mins, secs, hemi = m.groups()
        decimal = float(deg) + float(mins) / 60.0 + float(secs) / 3600.0
        if hemi.upper() in ("S", "W"):
            decimal = -decimal
        return decimal
    return None


@app.get("/proxy/zee/wms")
async def proxy_zee_wms(request: Request):
    params = dict(request.query_params)
    bbox = params.get("bbox") or params.get("BBOX")
    if not bbox:
        raise HTTPException(status_code=400, detail="Missing bbox parameter")
    params.setdefault("service", "WMS")
    params.setdefault("version", "1.1.1")
    params.setdefault("request", "GetMap")
    params["layers"] = "eez_boundaries"
    params.setdefault("format", "image/png")
    params.setdefault("transparent", "true")
    params.setdefault("srs", "EPSG:3857")
    params.setdefault("width", "512")
    params.setdefault("height", "512")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_VLIZ_WMS, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"VLIZ WMS HTTP {resp.status_code}")
            return Response(content=resp.content, media_type="image/png", headers=_WMS_CACHE_HEADERS)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ZEE WMS error: {exc}") from exc


@app.get("/proxy/zee")
async def proxy_zee(
    bbox: Optional[str] = Query(None),
    maxFeatures: int = Query(80, ge=1, le=ZEE_MAX_FEATURES_CAP),
):
    if not bbox and maxFeatures > ZEE_NO_BBOX_MAX_FEATURES:
        raise HTTPException(400, "bbox (minlon,minlat,maxlon,maxlat) requis pour les ZEE")
    cache_key = bbox or f"nobbox:{maxFeatures}"
    cached = _zee_cache.get("entries") or {}
    hit = cached.get(cache_key)
    if hit and (time.time() - hit["ts"] < _ZEE_CACHE_TTL):
        return JSONResponse(content=hit["data"])
    params: dict = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "eez",
        "outputFormat": "application/json",
        "maxFeatures": maxFeatures,
    }
    if bbox:
        params["bbox"] = bbox
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.get(
                "https://geo.vliz.be/geoserver/MarineRegions/wfs",
                params=params,
            )
            resp.raise_for_status()
            raw = resp.content or b""
            if too_large(len(raw), ZEE_RESPONSE_MAX_BYTES):
                raise HTTPException(502, f"ZEE upstream trop volumineux ({len(raw)} octets)")
            data = resp.json()
            if bbox and not too_large(len(raw), ZEE_CACHE_MAX_BYTES):
                lru_set(_zee_cache.setdefault("entries", {}), cache_key, {"data": data, "ts": time.time()}, max_items=4)
            return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ZEE upstream error: {exc}") from exc


def _parse_ports_bbox(raw: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    if not raw:
        return None
    try:
        west, south, east, north = (float(value) for value in raw.split(","))
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "bbox ports invalide") from exc
    if south > north or south < -90 or north > 90:
        raise HTTPException(400, "bbox ports invalide")
    return west, south, east, north


def _port_in_bbox(feature: dict, bbox: Optional[tuple[float, float, float, float]]) -> bool:
    if bbox is None:
        return True
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        return False
    lon, lat = float(coords[0]), float(coords[1])
    west, south, east, north = bbox
    if lat < south or lat > north:
        return False
    copies = (lon - 360.0, lon, lon + 360.0)
    if west <= east:
        return any(west <= value <= east for value in copies)
    return any(value >= west or value <= east for value in copies)


@app.get("/proxy/ports")
async def proxy_ports(bbox: Optional[str] = Query(None)):
    parsed_bbox = _parse_ports_bbox(bbox)
    try:
        features = await fetch_wpi_features()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WPI upstream error: {exc}") from exc
    visible = [feature for feature in features if _port_in_bbox(feature, parsed_bbox)]
    return JSONResponse(
        content={"type": "FeatureCollection", "features": visible},
        headers={"Cache-Control": "public, max-age=180, stale-while-revalidate=600"},
    )


_OPENSEAMAP_HOSTS = ["tiles.openseamap.org", "t1.openseamap.org"]


def _transparent_tile_256() -> bytes:
    try:
        import io
        from PIL import Image

        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except ImportError:
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


_TRANSPARENT_TILE = None


def _get_transparent_tile() -> bytes:
    global _TRANSPARENT_TILE
    if _TRANSPARENT_TILE is None:
        _TRANSPARENT_TILE = _transparent_tile_256()
    return _TRANSPARENT_TILE


@app.get("/proxy/seamark/{z:int}/{x:int}/{y}.png")
async def proxy_seamark(z: int, x: int, y: str):
    try:
        y_int = int(y)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tile y")
    async with httpx.AsyncClient(timeout=12.0) as client:
        for host in _OPENSEAMAP_HOSTS:
            url = f"https://{host}/seamark/{z}/{x}/{y_int}.png"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return Response(content=resp.content, media_type="image/png", headers=_SEAMARK_CACHE_HEADERS)
            except Exception:
                continue
    return Response(content=_get_transparent_tile(), media_type="image/png", headers=_SEAMARK_CACHE_HEADERS)

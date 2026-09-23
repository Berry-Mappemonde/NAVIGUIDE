"""Passerelle `/bi/climatology/*` → Blue Intelligence, avec cache disque.

En production nginx sert `/bi/` avant uvicorn (cache nginx partagé, voir
infra/vps/nginx-bi-climatology-cache.conf) : cette route ne tourne qu'en dev
(proxy Vite `/bi` → :8010), en CI et en preview Playwright.

Incident 2026-09-21 : les simulateurs de dev et les tests frappaient
blueintelligence.online en direct (600-800 req/s). Ici :
- chaque URL n'est demandée qu'une fois par machine (cache disque, 30 jours,
  dans ~/.cache/naviguide/bi-cache — partagé entre les checkouts d'une même
  machine ; NAVIGUIDE_BI_CACHE_DIR pour le déplacer) ;
- 50 requêtes identiques en vol = un seul appel amont ;
- 6 appels amont au plus en parallèle ;
- amont mort (5xx / réseau) : 30 s sans réessayer, réponse 502 immédiate
  → le client passe en repli zone (kind reste « climatology »).

Incident 2026-09-22 (poste de recette) : 3 762 réponses 502 sur `point` pour
281 succès. Cause : `wind.geojson` pèse 26 Mo et met ~18 s à sortir du VPS ;
avec un délai unique de 12 s elle échouait à chaque fois et son échec marquait
TOUT l'atlas mort 30 s — les centaines de `point` du film tombaient en 502
alors que l'atlas répondait en 0,2 s. D'où : un repos PAR point d'accès, et un
délai propre aux couches `*.geojson`.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()

_SIM_ROOT = Path(__file__).resolve().parent.parent
ALLOWED = frozenset({
    "point", "crossings", "meta",
    "wind.geojson", "wave.geojson", "current.geojson", "cyclones.geojson",
})
TTL_S = 30 * 24 * 3600
TIMEOUT_S = 12.0            # point, crossings, meta : l'atlas répond en moins d'une seconde
LAYER_TIMEOUT_S = 90.0      # *.geojson : wind.geojson = 26 Mo, ~18 s même derrière nginx (22 sept.)
DEAD_S = 30.0
MAX_UPSTREAM = 6
CACHE_CONTROL = f"public, max-age={TTL_S}"

_dead_until: dict[str, float] = {}      # repos par point d'accès : une couche lente ne bloque pas les points
_locks: dict[str, asyncio.Lock] = {}
_sem: asyncio.Semaphore | None = None


def bi_base() -> str:
    return (os.getenv("BI_API_URL") or "https://blueintelligence.online/api").rstrip("/")


def cache_dir() -> Path:
    """Un cache par machine, pas par checkout : les worktrees des lots (poste de recette) repartaient
    chacun d'un cache vide et refrappaient le VPS de zéro à chaque lot."""
    raw = os.getenv("NAVIGUIDE_BI_CACHE_DIR")
    if raw:
        return Path(raw)
    try:
        home = Path.home()
        if home.is_dir():
            return home / ".cache" / "naviguide" / "bi-cache"
    except (RuntimeError, OSError):
        pass
    return _SIM_ROOT / ".dev" / "bi-cache"


def timeout_for(rest_or_url: str) -> float:
    return LAYER_TIMEOUT_S if rest_or_url.endswith(".geojson") else TIMEOUT_S


def cache_key(rest: str, query: str) -> str:
    return hashlib.sha1(f"{rest}?{query}".encode("utf-8")).hexdigest()


def canonical_query(request: Request) -> str:
    """Même cellule, même clé : paramètres triés, valeurs telles quelles."""
    items = sorted(request.query_params.multi_items())
    return "&".join(f"{k}={v}" for k, v in items)


def is_dead(rest: str | None = None) -> bool:
    """Sans argument : au moins un point d'accès en repos (tests) ; avec : ce point d'accès-là."""
    now = time.time()
    if rest is None:
        return any(until > now for until in _dead_until.values())
    return _dead_until.get(rest, 0.0) > now


def mark_dead(rest: str) -> None:
    _dead_until[rest] = time.time() + DEAD_S


def reset() -> None:
    _dead_until.clear()
    _locks.clear()


def _sem_get() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(MAX_UPSTREAM)
    return _sem


def _read_cache(path: Path) -> bytes | None:
    try:
        if time.time() - path.stat().st_mtime > TTL_S:
            return None
        return path.read_bytes()
    except OSError:
        return None


def _write_cache(path: Path, body: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(body)
        tmp.replace(path)
    except OSError:
        pass


async def fetch_upstream(url: str, params: list[tuple[str, str]]) -> tuple[int, bytes]:
    """(status, body). Isolé pour les tests (monkeypatch). Délai selon la nature de l'URL (couche ou point)."""
    async with httpx.AsyncClient(timeout=timeout_for(url)) as client:
        r = await client.get(url, params=params, headers={"Accept": "application/json"})
        return r.status_code, r.content


def _json_response(body: bytes, status: str, code: int = 200) -> Response:
    return Response(
        content=body,
        status_code=code,
        media_type="application/json",
        headers={"Cache-Control": CACHE_CONTROL, "X-Cache-Status": status},
    )


@router.get("/bi/climatology/{rest:path}")
async def bi_climatology(rest: str, request: Request):
    if rest not in ALLOWED:
        raise HTTPException(404, "not a climatology endpoint")
    query = canonical_query(request)
    key = cache_key(rest, query)
    path = cache_dir() / key[:2] / f"{key}.json"

    cached = _read_cache(path)
    if cached is not None:
        return _json_response(cached, "HIT")
    if is_dead(rest):
        raise HTTPException(502, f"atlas unavailable (cooldown {rest})")

    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _read_cache(path)  # rempli par la requête jumelle
        if cached is not None:
            return _json_response(cached, "HIT")
        if is_dead(rest):
            raise HTTPException(502, f"atlas unavailable (cooldown {rest})")
        params = request.query_params.multi_items()
        try:
            async with _sem_get():
                status, body = await fetch_upstream(f"{bi_base()}/climatology/{rest}", params)
        except Exception as exc:  # réseau, timeout, refus de connexion — ce point d'accès seulement
            mark_dead(rest)
            raise HTTPException(502, f"atlas unavailable ({type(exc).__name__})") from exc
        if status >= 500 or status == 429:
            mark_dead(rest)
            raise HTTPException(502, f"atlas unavailable (upstream {status})")
        if status != 200:
            return Response(content=body, status_code=status, media_type="application/json")
        _write_cache(path, body)
        return _json_response(body, "MISS")

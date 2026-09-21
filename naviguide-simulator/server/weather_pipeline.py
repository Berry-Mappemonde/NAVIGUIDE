"""Pipeline météo asynchrone partagé.

Tous les fournisseurs passent ici : tâche de rafraîchissement dédupliquée,
état durable (pending / ready / error) et cache par cellule 0,25° + cycle GFS.
Les handlers répondent tout de suite ; le client actualise à faible cadence.

Le pipeline **transporte** les champs déjà convertis par les loaders
(hindcast, Copernicus getWind / getWave / getCurrent, forecast_cube, saildocs).
Il ne recalcule pas les vecteurs. Conventions (lot C5, cahier § 20) :

- 1 m/s = 1,943844 kn (1 kn = 1 852 m/h)
- vent et vagues : direction **« de »** (météorologique), atan2(-u, -v)
- courant : direction **« vers »** (océanographique), atan2(uo, vo) ;
  uo = 1, vo = 0 → 90° (est)
"""
from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Callable, Iterable, Optional

from saildocs import last_ready_cycle, to_iso

log = logging.getLogger("naviguide-simulator.weather")

CELL_DEG = 0.25
CACHE_MAX = 256
WAIT_POLL_S = 0.02

Loader = Callable[[], dict]

_http_transport = None


def bind_weather_transport(transport) -> None:
    """Les tests branchent un MockTransport. Jamais le transport async d’un AsyncClient."""
    global _http_transport
    if transport is not None and type(transport).__name__ != "MockTransport":
        transport = None
    _http_transport = transport


def weather_http_transport():
    return _http_transport


def wrap_lon(lon: float) -> float:
    x = float(lon)
    while x > 180.0:
        x -= 360.0
    while x < -180.0:
        x += 360.0
    return x


def weather_cell(lat: float, lon: float) -> tuple[int, int]:
    wrapped = wrap_lon(lon)
    return (
        math.floor((float(lat) + 90.0) / CELL_DEG),
        math.floor((wrapped + 180.0) / CELL_DEG),
    )


def cell_center(i: int, j: int) -> tuple[float, float]:
    lat = (i * CELL_DEG) - 90.0 + CELL_DEG / 2.0
    lon = (j * CELL_DEG) - 180.0 + CELL_DEG / 2.0
    return lat, lon


def forecast_cycle(when=None) -> str:
    return to_iso(last_ready_cycle(when))


def cache_key(provider: str, lat: float, lon: float, when=None) -> tuple[str, int, int, str]:
    i, j = weather_cell(lat, lon)
    return (provider, i, j, forecast_cycle(when))


def _cell_public(i: int, j: int) -> dict:
    lat, lon = cell_center(i, j)
    return {"i": i, "j": j, "deg": CELL_DEG, "lat": round(lat, 5), "lon": round(lon, 5)}


def _lru_set(cache: dict, key, value) -> None:
    if key in cache:
        cache.pop(key)
    elif len(cache) >= CACHE_MAX:
        cache.pop(next(iter(cache)))
    cache[key] = value


class WeatherPipeline:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[tuple, dict] = {}
        self._inflight: dict[tuple, threading.Thread] = {}

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._inflight.clear()
        bind_weather_transport(None)

    def peek(self, provider: str, lat: float, lon: float, when=None) -> Optional[dict]:
        key = cache_key(provider, lat, lon, when)
        with self._lock:
            hit = self._cache.get(key)
            return dict(hit) if hit else None

    def provider_busy(self, provider: str) -> bool:
        with self._lock:
            return any(
                key[0] == provider and thread.is_alive()
                for key, thread in self._inflight.items()
            )

    def refreshing(self, provider: str, lat: float, lon: float, when=None) -> bool:
        key = cache_key(provider, lat, lon, when)
        with self._lock:
            thread = self._inflight.get(key)
            return bool(thread and thread.is_alive())

    def kick(
        self,
        provider: str,
        lat: float,
        lon: float,
        loader: Loader,
        *,
        when=None,
        force: bool = False,
    ) -> bool:
        """Démarre au plus un rafraîchissement pour cette clé cellule/cycle."""
        key = cache_key(provider, lat, lon, when)
        with self._lock:
            thread = self._inflight.get(key)
            if thread and thread.is_alive():
                return False
            hit = self._cache.get(key)
            if not force and hit and hit.get("status") in {"ready", "error"}:
                return False
            started = threading.Thread(
                target=self._run,
                args=(key, loader),
                name=f"naviguide-wx-{provider}-{key[1]}-{key[2]}",
                daemon=True,
            )
            self._inflight[key] = started
            pending = self._pending_record(key, refreshing=True, prev=hit)
            _lru_set(self._cache, key, pending)
            started.start()
        return True

    def snapshot(
        self,
        provider: str,
        lat: float,
        lon: float,
        loader: Loader,
        *,
        when=None,
        force: bool = False,
    ) -> dict:
        """Réponse immédiate. Lance le loader hors chemin si la cellule/cycle manque."""
        key = cache_key(provider, lat, lon, when)
        stale = self._stale_ready(provider, key[1], key[2], key[3])
        with self._lock:
            hit = self._cache.get(key)
            thread = self._inflight.get(key)
            busy = bool(thread and thread.is_alive())
            if hit and hit.get("status") in {"ready", "error"} and not force:
                return self._public(hit, lat, lon, refreshing=busy)
            if busy:
                if stale:
                    return self._public(stale, lat, lon, refreshing=True)
                return self._public(hit or self._pending_record(key, True), lat, lon, refreshing=True)
        self.kick(provider, lat, lon, loader, when=when, force=force)
        if stale and not force:
            return self._public(stale, lat, lon, refreshing=True)
        with self._lock:
            hit = self._cache.get(key)
            thread = self._inflight.get(key)
            busy = bool(thread and thread.is_alive())
        if hit and hit.get("status") in {"ready", "error"}:
            return self._public(hit, lat, lon, refreshing=False)
        return self._public(hit or self._pending_record(key, True), lat, lon, refreshing=busy or True)

    def snapshot_group(
        self,
        jobs: Iterable[tuple[str, str, Loader]],
        lat: float,
        lon: float,
        *,
        when=None,
        force: bool = False,
    ) -> dict:
        parts: dict[str, dict] = {}
        for name, provider, loader in jobs:
            parts[name] = self.snapshot(provider, lat, lon, loader, when=when, force=force)
        statuses = [part.get("status") for part in parts.values()]
        if any(status == "pending" for status in statuses) or not statuses:
            overall = "pending"
        elif any(status == "ready" for status in statuses):
            overall = "ready"
        elif any(status == "error" for status in statuses):
            overall = "error"
        else:
            overall = "absent"
        cycle = next((part.get("cycle") for part in parts.values() if part.get("cycle")), forecast_cycle(when))
        return {
            "status": overall,
            "refreshing": any(bool(part.get("refreshing")) for part in parts.values()),
            "cycle": cycle,
            "cell": _cell_public(*weather_cell(lat, lon)),
            **parts,
        }

    def wait_ready(
        self,
        provider: str,
        lat: float,
        lon: float,
        *,
        when=None,
        timeout: float = 2.0,
    ) -> dict:
        deadline = time.monotonic() + timeout
        key = cache_key(provider, lat, lon, when)
        while time.monotonic() < deadline:
            with self._lock:
                hit = self._cache.get(key)
                thread = self._inflight.get(key)
                busy = bool(thread and thread.is_alive())
            if hit and hit.get("status") in {"ready", "error"} and not busy:
                return self._public(hit, lat, lon, refreshing=False)
            time.sleep(WAIT_POLL_S)
        with self._lock:
            hit = self._cache.get(key)
        return self._public(hit or self._pending_record(key, True), lat, lon, refreshing=True)

    def wait_providers(
        self,
        providers: Iterable[str],
        lat: float,
        lon: float,
        *,
        when=None,
        timeout: float = 3.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        for provider in providers:
            remain = max(0.05, deadline - time.monotonic())
            self.wait_ready(provider, lat, lon, when=when, timeout=remain)

    def _run(self, key: tuple, loader: Loader) -> None:
        try:
            data = loader() or {}
            record = {
                "status": "ready",
                "provider": key[0],
                "cycle": key[3],
                "cell": _cell_public(key[1], key[2]),
                "data": dict(data),
                "error": None,
                "updated_at": time.monotonic(),
            }
            with self._lock:
                _lru_set(self._cache, key, record)
        except Exception as exc:
            log.warning("météo %s cellule %s,%s: %s", key[0], key[1], key[2], exc)
            record = {
                "status": "error",
                "provider": key[0],
                "cycle": key[3],
                "cell": _cell_public(key[1], key[2]),
                "data": None,
                "error": getattr(exc, "reason", None) or f"{type(exc).__name__}",
                "updated_at": time.monotonic(),
            }
            with self._lock:
                _lru_set(self._cache, key, record)
        finally:
            with self._lock:
                if self._inflight.get(key) is threading.current_thread():
                    self._inflight.pop(key, None)

    def _stale_ready(self, provider: str, i: int, j: int, cycle: str) -> Optional[dict]:
        with self._lock:
            best = None
            for key, hit in self._cache.items():
                if key[0] != provider or key[1] != i or key[2] != j:
                    continue
                if hit.get("status") != "ready":
                    continue
                if key[3] == cycle:
                    return dict(hit)
                if best is None or str(key[3]) > str(best.get("cycle") or ""):
                    best = dict(hit)
            return best

    def _pending_record(self, key: tuple, refreshing: bool, prev: Optional[dict] = None) -> dict:
        return {
            "status": "pending",
            "provider": key[0],
            "cycle": key[3],
            "cell": _cell_public(key[1], key[2]),
            "data": dict((prev or {}).get("data") or {}) or None,
            "error": None,
            "updated_at": time.monotonic(),
            "refreshing": refreshing,
        }

    def _public(self, record: dict, lat: float, lon: float, *, refreshing: bool) -> dict:
        body: dict[str, Any] = dict(record.get("data") or {})
        body["status"] = record.get("status") or "pending"
        body["refreshing"] = refreshing or bool(record.get("refreshing"))
        body["provider"] = record.get("provider")
        body["cycle"] = record.get("cycle")
        body["cell"] = record.get("cell")
        body.setdefault("latitude", lat)
        body.setdefault("longitude", lon)
        if record.get("error") and not body.get("reason"):
            body["reason"] = record["error"]
        return body


_PIPELINE = WeatherPipeline()


def get_pipeline() -> WeatherPipeline:
    return _PIPELINE

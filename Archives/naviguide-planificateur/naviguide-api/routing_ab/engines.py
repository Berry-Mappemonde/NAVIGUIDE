"""Adaptateurs des moteurs comparés (searoute, scgraph, graphe enrichi)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .enriched import enriched_route
from .legs import LonLat

API_DIR = Path(__file__).resolve().parents[1]
SR16_VENV = API_DIR / ".venv-ab-sr16"
WORKER = Path(__file__).resolve().parent / "searoute_worker.py"


@dataclass
class EngineResult:
    engine_id: str
    coords: list[list[float]]  # [lon, lat]
    elapsed_ms: float
    version: str
    error: Optional[str] = None


RouteFn = Callable[[LonLat, LonLat], list[list[float]]]


def _searoute_inprocess(start: LonLat, end: LonLat) -> list[list[float]]:
    import searoute as sr

    route = sr.searoute(start, end)
    coords = route["geometry"]["coordinates"]
    return [list(p[:2]) for p in coords]


def _searoute_version() -> str:
    try:
        import importlib.metadata

        return importlib.metadata.version("searoute")
    except Exception:
        try:
            import searoute as sr

            return getattr(sr, "__version__", "unknown")
        except Exception:
            return "missing"


def _run_searoute_worker(python: str, start: LonLat, end: LonLat) -> list[list[float]]:
    proc = subprocess.run(
        [python, str(WORKER), json.dumps(list(start)), json.dumps(list(end))],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    route = json.loads(proc.stdout)
    coords = route["geometry"]["coordinates"]
    return [list(p[:2]) for p in coords]


def ensure_searoute16_venv() -> Path:
    """Crée un venv isolé avec searoute==1.6.0 si besoin."""
    python = SR16_VENV / "bin" / "python"
    if python.is_file():
        probe = subprocess.run(
            [str(python), "-c", "import importlib.metadata as m; print(m.version('searoute'))"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0 and probe.stdout.strip() == "1.6.0":
            return python
    subprocess.run([sys.executable, "-m", "venv", str(SR16_VENV)], check=True)
    pip = SR16_VENV / "bin" / "pip"
    subprocess.run(
        [str(pip), "install", "--quiet", "searoute==1.6.0", "geojson"],
        check=True,
    )
    return python


class _ScgraphGraph:
    def __init__(self, name: str):
        from scgraph import GeoGraph

        self.name = name
        self.graph = GeoGraph.load_geograph(name)

    def route(self, start: LonLat, end: LonLat) -> list[list[float]]:
        out = self.graph.get_shortest_path(
            origin_node={"latitude": start[1], "longitude": start[0]},
            destination_node={"latitude": end[1], "longitude": end[0]},
            output_units="km",
        )
        path = out.get("coordinate_path") or []
        # scgraph: [lat, lon] → GeoJSON [lon, lat]
        coords: list[list[float]] = []
        for pt in path:
            if isinstance(pt, dict):
                coords.append([float(pt["longitude"]), float(pt["latitude"])])
            else:
                coords.append([float(pt[1]), float(pt[0])])
        return coords


_SCGRAPH_CACHE: dict[str, _ScgraphGraph] = {}


def _scgraph_route(name: str, start: LonLat, end: LonLat) -> list[list[float]]:
    if name not in _SCGRAPH_CACHE:
        _SCGRAPH_CACHE[name] = _ScgraphGraph(name)
    return _SCGRAPH_CACHE[name].route(start, end)


def _timed(fn: RouteFn, start: LonLat, end: LonLat) -> tuple[list[list[float]], float, Optional[str]]:
    t0 = time.perf_counter()
    try:
        coords = fn(start, end)
        ms = (time.perf_counter() - t0) * 1000
        return coords, ms, None
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000
        return [], ms, f"{type(exc).__name__}: {exc}"


def available_engines(include_sr16: bool = True) -> list[str]:
    ids: list[str] = []
    try:
        import searoute  # noqa: F401

        ids.append("searoute_14")
    except ImportError:
        pass
    if include_sr16:
        ids.append("searoute_16")
    try:
        import scgraph  # noqa: F401

        ids.extend(["scgraph_marnet", "scgraph_oak_ridge"])
    except ImportError:
        pass
    if "searoute_14" in ids or "scgraph_marnet" in ids:
        ids.append("enriched_sailing")
    return ids


def _base_cargo_fn() -> RouteFn:
    try:
        import searoute  # noqa: F401

        return _searoute_inprocess
    except ImportError:
        return lambda a, b: _scgraph_route("marnet", a, b)


def run_engine(engine_id: str, start: LonLat, end: LonLat) -> EngineResult:
    if engine_id == "searoute_14":
        coords, ms, err = _timed(_searoute_inprocess, start, end)
        return EngineResult(engine_id, coords, ms, _searoute_version(), err)

    if engine_id == "searoute_16":
        def _fn(a: LonLat, b: LonLat) -> list[list[float]]:
            python = ensure_searoute16_venv()
            return _run_searoute_worker(str(python), a, b)

        coords, ms, err = _timed(_fn, start, end)
        return EngineResult(engine_id, coords, ms, "1.6.0", err)

    if engine_id == "scgraph_marnet":
        coords, ms, err = _timed(lambda a, b: _scgraph_route("marnet", a, b), start, end)
        return EngineResult(engine_id, coords, ms, "scgraph-marnet", err)

    if engine_id == "scgraph_oak_ridge":
        coords, ms, err = _timed(
            lambda a, b: _scgraph_route("oak_ridge_maritime", a, b), start, end
        )
        return EngineResult(engine_id, coords, ms, "scgraph-oak_ridge_maritime", err)

    if engine_id == "enriched_sailing":
        base = _base_cargo_fn()
        coords, ms, err = _timed(lambda a, b: enriched_route(base, a, b), start, end)
        return EngineResult(engine_id, coords, ms, "enriched+cargo", err)

    return EngineResult(engine_id, [], 0.0, "unknown", f"moteur inconnu: {engine_id}")


def skip_slow_scgraph() -> bool:
    return os.environ.get("ROUTING_AB_SKIP_SCGRAPH") == "1"

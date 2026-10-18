"""Lance le banc A/B et écrit JSON / GeoJSON / HTML.

Usage (depuis naviguide-api/) :
    python -m routing_ab.compare --out routing_ab/out
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .engines import available_engines, run_engine
from .enriched import vias_for_leg
from .findings import summarize
from .legs import BENCHMARK_LEGS, CORE_LEG_IDS, BenchmarkLeg
from .metrics import measure

ENGINE_COLORS = {
    "searoute_14": "#2563eb",
    "searoute_16": "#0891b2",
    "scgraph_marnet": "#ea580c",
    "scgraph_oak_ridge": "#92400e",
    "enriched_sailing": "#16a34a",
}

ENGINE_LABELS = {
    "searoute_14": "searoute 1.4 (prod)",
    "searoute_16": "searoute 1.6",
    "scgraph_marnet": "scgraph marnet (même graphe)",
    "scgraph_oak_ridge": "scgraph Oak Ridge",
    "enriched_sailing": "enrichi voile (portes + décalage)",
}


def _land_fn():
    try:
        from global_land_mask import globe

        return lambda lat, lon: bool(globe.is_land(lat, lon))
    except Exception:
        return None


def run_comparison(
    engine_ids: Optional[list[str]] = None,
    core_only: bool = False,
    include_sr16: bool = True,
) -> dict:
    """Exécute tous les moteurs sur toutes les jambes et retourne un rapport."""
    legs: tuple[BenchmarkLeg, ...] = BENCHMARK_LEGS
    if core_only:
        legs = tuple(leg for leg in legs if leg.id in CORE_LEG_IDS)
    engines = engine_ids or available_engines(include_sr16=include_sr16)
    is_land = _land_fn()
    rows: list[dict] = []
    features: list[dict] = []

    for leg in legs:
        vias = vias_for_leg(leg.start, leg.end)
        for engine_id in engines:
            result = run_engine(engine_id, leg.start, leg.end)
            metrics = measure(
                result.coords, leg.start, leg.end, result.elapsed_ms, is_land
            ) if result.coords else {
                "n_points": 0,
                "length_nm": None,
                "geodesic_nm": None,
                "length_ratio": None,
                "elapsed_ms": round(result.elapsed_ms, 1),
                "coral_sea_pts": None,
                "land_hits": None,
                "antimeridian_jumps": None,
                "anti_shipping": None,
                "lanes": [],
                "ok": False,
            }
            row = {
                "leg_id": leg.id,
                "leg_label": leg.label,
                "family": leg.family,
                "engine": engine_id,
                "engine_label": ENGINE_LABELS.get(engine_id, engine_id),
                "version": result.version,
                "error": result.error,
                "vias": [[v[0], v[1]] for v in vias],
                **metrics,
            }
            rows.append(row)
            if result.coords:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "leg_id": leg.id,
                        "leg_label": leg.label,
                        "family": leg.family,
                        "engine": engine_id,
                        "engine_label": ENGINE_LABELS.get(engine_id, engine_id),
                        "color": ENGINE_COLORS.get(engine_id, "#444"),
                        "length_nm": metrics.get("length_nm"),
                        "anti_shipping": metrics.get("anti_shipping"),
                        "coral_sea_pts": metrics.get("coral_sea_pts"),
                        "ok": metrics.get("ok"),
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": result.coords,
                    },
                })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Comparaison Problème A uniquement. GET /route de production "
            "n'est pas modifié."
        ),
        "engines": engines,
        "legs": [leg.id for leg in legs],
        "rows": rows,
        "findings": summarize(rows),
        "geojson": {"type": "FeatureCollection", "features": features},
    }


def _html_report(report: dict) -> str:
    rows_json = json.dumps(report["rows"])
    geo_json = json.dumps(report["geojson"])
    colors = json.dumps(ENGINE_COLORS)
    labels = json.dumps(ENGINE_LABELS)
    findings = report.get("findings", {})
    bullets = "".join(f"<li>{b}</li>" for b in findings.get("bullets", []))
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <title>NAVIGUIDE — banc A/B routage mer</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    body {{ font-family: Georgia, serif; margin: 0; background: #f6f3ee; color: #1c1917; }}
    header {{ padding: 1rem 1.5rem; background: #1e3a5f; color: #fff; }}
    header p {{ margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; }}
    #map {{ height: 520px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; background: #fff; }}
    th, td {{ border: 1px solid #d6d3d1; padding: 0.35rem 0.5rem; text-align: left; }}
    th {{ background: #e7e5e4; }}
    .ok {{ color: #166534; }}
    .bad {{ color: #b91c1c; }}
    .wrap {{ padding: 1rem 1.5rem 2rem; overflow-x: auto; }}
    .legend span {{ display: inline-block; width: 12px; height: 12px; margin-right: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>Banc A/B — routage mer NAVIGUIDE</h1>
    <p>Graphes cargos vs graphe enrichi voile. La route de production n'est pas changée.</p>
  </header>
  <div id="map"></div>
  <div class="wrap">
    <h2>Ce que montre ce run</h2>
    <ul>{bullets}</ul>
    <p class="legend" id="legend"></p>
    <table id="tbl"></table>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const rows = {rows_json};
    const fc = {geo_json};
    const colors = {colors};
    const labels = {labels};
    const map = L.map('map').setView([0, 20], 2);
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; OpenStreetMap'
    }}).addTo(map);
    const layer = L.geoJSON(fc, {{
      style: f => ({{
        color: f.properties.color,
        weight: f.properties.engine === 'enriched_sailing' ? 4 : 2.5,
        opacity: 0.85
      }}),
      onEachFeature: (f, lyr) => {{
        lyr.bindPopup(
          f.properties.leg_label + '<br>' + f.properties.engine_label +
          '<br>' + (f.properties.length_nm || '?') + ' nm'
        );
      }}
    }}).addTo(map);
    if (fc.features.length) map.fitBounds(layer.getBounds().pad(0.15));
    document.getElementById('legend').innerHTML = Object.keys(labels).map(id =>
      '<span style="background:' + colors[id] + '"></span>' + labels[id]
    ).join(' &nbsp; ');
    const headers = ['Jambe','Moteur','Pts','nm','Ratio','ms','Corail','Terre','±180','Anti-trafic','OK'];
    const tbl = document.getElementById('tbl');
    tbl.innerHTML = '<tr>' + headers.map(h => '<th>'+h+'</th>').join('') + '</tr>' +
      rows.map(r => {{
        const ok = r.ok && !r.error;
        return '<tr class="' + (ok ? 'ok' : 'bad') + '">' +
          [r.leg_label, r.engine_label, r.n_points, r.length_nm, r.length_ratio,
           r.elapsed_ms, r.coral_sea_pts, r.land_hits, r.antimeridian_jumps,
           r.anti_shipping, ok ? 'oui' : (r.error || 'non')].map(c => '<td>'+(c??'')+'</td>').join('') +
        '</tr>';
      }}).join('');
  </script>
</body>
</html>
"""


def write_report(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps({k: v for k, v in report.items() if k != "geojson"}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "routes.geojson").write_text(
        json.dumps(report["geojson"]),
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(_html_report(report), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Banc A/B routage mer NAVIGUIDE")
    parser.add_argument("--out", default="routing_ab/out", help="Dossier de sortie")
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--no-sr16", action="store_true", help="Ne pas installer searoute 1.6")
    args = parser.parse_args(argv)
    report = run_comparison(core_only=args.core_only, include_sr16=not args.no_sr16)
    write_report(report, Path(args.out))
    print(f"écrit {args.out}/index.html  ({len(report['rows'])} lignes)")
    fails = [r for r in report["rows"] if r.get("error")]
    if fails:
        print(f"{len(fails)} erreur(s) moteur")
        for row in fails:
            print(f"  {row['engine']} / {row['leg_id']}: {row['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

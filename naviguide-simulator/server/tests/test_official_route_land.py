"""La route Berry du fichier ne traverse pas la terre.

Le fichier est le résultat du routeur. L'application le charge : la route
Berry ne se recalcule pas à chaque ouverture. Seule la jambe terrestre
Saint-Maur → La Rochelle a le droit de toucher la terre.
"""
import json
from pathlib import Path

from route_engine import segment_crosses_land

ROUTE = Path(__file__).resolve().parents[2] / "public" / "route.geojson"


def test_official_route_avoids_land():
    fc = json.loads(ROUTE.read_text())
    assert len(fc["features"]) == 72
    wallis = [
        f for f in fc["features"]
        if "Wallis" in (f.get("properties") or {}).get("from", "")
        and "Nouméa" in (f.get("properties") or {}).get("to", "")
    ]
    assert len(wallis) == 2
    hits = []
    maritime = 0
    for feature in fc["features"]:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        if props.get("type") == "overland":
            assert props.get("from", "").startswith("Saint-Maur")
            assert len(geom["coordinates"]) == 2
            continue
        assert props.get("type") == "maritime"
        maritime += 1
        coords = geom["coordinates"]
        for i in range(len(coords) - 1):
            a, b = coords[i], coords[i + 1]
            if segment_crosses_land(a[0], a[1], b[0], b[1]):
                hits.append((props.get("from"), props.get("to"), a, b))
    assert maritime == 35
    assert hits == []

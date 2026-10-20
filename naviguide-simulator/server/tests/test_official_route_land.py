"""La route Berry du fichier ne traverse pas la terre.

Le fichier est le résultat du routeur (searoute, puis avoid_land). On le
recharge tel quel : la route Berry ne se recalcule pas à chaque ouverture.
Le contrôle est le même que celui du moteur. Trois segments restent marqués
par la grille 1/4° alors que le routeur n'a pas pu les détourner : la sortie
du port de La Rochelle, la sortie du port d'Halifax, et le canal de Panama.
"""
import json
from pathlib import Path

from route_engine import segment_crosses_land

ROUTE = Path(__file__).resolve().parents[2] / "public" / "route.geojson"

# Coordonnées exactes des trois résidus (aller et retour pour les ports).
RESIDUAL = {
    ((-1.167, 46.1541), (-1.261231, 46.239161)),
    ((-1.261231, 46.239161), (-1.167, 46.1541)),
    ((-63.562088, 44.655955), (-63.48793, 44.535185)),
    ((-63.48793, 44.535185), (-63.562088, 44.655955)),
    ((-79.821304, 9.423012), (-79.821304, 9.173012)),
}


def _key(a, b):
    def r(point):
        return (round(float(point[0]), 5), round(float(point[1]), 5))
    return (r(a), r(b))


def test_official_route_avoids_land():
    fc = json.loads(ROUTE.read_text())
    assert len(fc["features"]) == 72
    wallis = [
        f for f in fc["features"]
        if "Wallis" in (f.get("properties") or {}).get("from", "")
        and "Nouméa" in (f.get("properties") or {}).get("to", "")
    ]
    assert len(wallis) == 2
    residual = {_key(a, b) for a, b in RESIDUAL}
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
            if not segment_crosses_land(a[0], a[1], b[0], b[1]):
                continue
            if _key(a, b) in residual:
                continue
            hits.append((props.get("from"), props.get("to"), a, b))
    assert maritime == 35
    assert hits == []

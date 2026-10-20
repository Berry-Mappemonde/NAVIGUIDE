"""Recalcule un FeatureCollection Berry et n'écrit pas le fichier public.

Le module n'est pas chargé au démarrage du serveur. Sans ``--write`` il
imprime un rapport et quitte 0 quand le candidat tient le contrat. Avec
``--write`` il exige ``--dest``. ``public/route.geojson`` et tout lien vers
ce fichier sont refusés avant le calcul.

Chaque feature maritime est recalculée par ``searoute_with_exact_end``.
L'overland Saint-Maur → La Rochelle est recopiée. Aucune feature
Cayenne ↔ Halifax n'est ajoutée. Halifax ↔ Saint-Pierre restent deux
jambes maritimes séparées.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

_SERVER = Path(__file__).resolve().parent
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))

from route_contract import (  # noqa: E402
    PANAMA_BOX,
    SUEZ_BOX,
    in_passage_box,
    iter_vertices,
    line_strings,
)

DEADLINE_S = 90.0


def public_route_file() -> Path:
    """Fichier publié. Il peut être passé en ``--src`` ; il ne peut pas être ``--dest``."""
    return Path(__file__).resolve().parent.parent / "public" / "route.geojson"


def dest_targets_public_route(dest: Path | str) -> bool:
    """Vrai si ``dest`` est le fichier public ou un lien (fichier ou dossier) vers lui.

    En cas de doute (chemin illisible), on refuse.
    """
    public = public_route_file()
    try:
        asked = Path(dest).expanduser()
        if not asked.is_absolute():
            asked = Path.cwd() / asked
        asked_abs = Path(os.path.normpath(os.path.abspath(asked)))
        public_abs = Path(os.path.normpath(os.path.abspath(public)))
        if asked_abs == public_abs:
            return True
        if Path(os.path.realpath(asked)) == Path(os.path.realpath(public)):
            return True
        if asked.exists() and public.exists() and os.path.samefile(asked, public):
            return True
    except OSError:
        return True
    return False


def _default_route_fn(start, end, deadline=None):
    from route_engine import searoute_with_exact_end

    if deadline is None:
        deadline = time.monotonic() + DEADLINE_S
    return searoute_with_exact_end(start, end, deadline=deadline)


def _label(props: dict) -> str:
    return f"{props.get('from') or '?'} → {props.get('to') or '?'}"


def _as_lonlat_line(coords) -> list[list[float]] | None:
    if not isinstance(coords, list):
        return None
    out: list[list[float]] = []
    try:
        for coord in coords:
            if coord is None or len(coord) < 2:
                return None
            out.append([float(coord[0]), float(coord[1])])
    except (TypeError, ValueError):
        return None
    if len(out) < 2:
        return None
    return out


def _engine_line(route) -> list[list[float]] | None:
    if not isinstance(route, dict):
        return None
    geom = route.get("geometry") or {}
    if geom.get("type") not in (None, "LineString"):
        return None
    return _as_lonlat_line(geom.get("coordinates"))


def _constraint_open(route) -> bool:
    if not isinstance(route, dict):
        return False
    props = route.get("properties") or {}
    return props.get("constraintStatus") == "open"


def _blob(props: dict) -> str:
    return " ".join(str(props.get(key) or "") for key in ("name", "from", "to"))


def _maritime(lines: list[dict], src: str, dst: str) -> list[dict]:
    return [
        line
        for line in lines
        if line["type"] == "maritime" and src in line["from"] and dst in line["to"]
    ]


def contract_violations(feature_collection: dict) -> list[str]:
    """Écarts au contrat d'écriture : Panama, pas sous 40° S, pas Suez, cap, Halifax, une overland.

    Le compte des 35 jambes du fichier publié n'est pas ici : ce garde juge
    le candidat, pas le fichier que l'application charge.
    """
    violations: list[str] = []
    lines = line_strings(feature_collection)
    cayenne = [
        line
        for line in lines
        if "Cayenne" in line["from"] and "Papeete" in line["to"]
    ]
    if not cayenne:
        violations.append("Cayenne → Papeete absente")
    else:
        in_panama = False
        too_far_south = False
        for line in cayenne:
            for lon, lat in (
                (float(coord[0]), float(coord[1])) for coord in line["coordinates"]
            ):
                if lat < -40.0:
                    too_far_south = True
                if in_passage_box(lon, lat, PANAMA_BOX):
                    in_panama = True
        if not in_panama:
            violations.append("aucun sommet de Cayenne → Papeete dans la boîte Panama")
        if too_far_south:
            violations.append("Cayenne → Papeete descend sous 40° S")
    suez = [
        (lon, lat)
        for lon, lat in iter_vertices(feature_collection)
        if in_passage_box(lon, lat, SUEZ_BOX)
    ]
    if suez:
        violations.append("sommet dans la boîte Suez")
    named = any(
        "Bonne Espérance" in _blob((feature.get("properties") or {}))
        for feature in feature_collection.get("features") or []
    )
    if not named:
        violations.append("cap de Bonne Espérance non nommé")
    if len(_maritime(lines, "Halifax", "Saint-Pierre")) != 1 or len(
        _maritime(lines, "Saint-Pierre", "Halifax")
    ) != 1:
        violations.append("Halifax ↔ Saint-Pierre doit rester deux jambes maritimes")
    joined = []
    for feature in feature_collection.get("features") or []:
        props = feature.get("properties") or {}
        src = props.get("from") or ""
        dst = props.get("to") or ""
        if ("Cayenne" in src and "Halifax" in dst) or (
            "Halifax" in src and "Cayenne" in dst
        ):
            joined.append((src, dst))
    if joined:
        violations.append("feature Cayenne ↔ Halifax")
    overland = [
        feature
        for feature in feature_collection.get("features") or []
        if (feature.get("properties") or {}).get("type") == "overland"
    ]
    if len(overland) != 1:
        violations.append("une seule jambe overland attendue")
    else:
        props = overland[0].get("properties") or {}
        geom = overland[0].get("geometry") or {}
        coords = geom.get("coordinates") or []
        if not str(props.get("from") or "").startswith("Saint-Maur") or props.get("to") != "La Rochelle":
            violations.append("l'overland n'est pas Saint-Maur → La Rochelle")
        if geom.get("type") != "LineString" or len(coords) != 2:
            violations.append("l'overland Saint-Maur n'est plus la droite d'origine")
    return violations


def _overland(feature_collection: dict) -> list[dict]:
    return [
        feature
        for feature in feature_collection.get("features") or []
        if (feature.get("properties") or {}).get("type") == "overland"
    ]


def rebuild_collection(feature_collection: dict, route_fn, deadline: float | None = None) -> tuple[dict, list[str]]:
    """Retourne ``(candidat, violations)``. N'écrit rien.

    ``route_fn(start, end, deadline=...)`` renvoie une feature GeoJSON, ou
    rien si la jambe n'a pas de ligne. Une jambe sans ligne est absente du
    candidat. ``constraintStatus == open`` interdit l'écriture.
    """
    if deadline is None:
        deadline = time.monotonic() + DEADLINE_S
    candidate = copy.deepcopy(feature_collection)
    features: list[dict] = []
    failures: list[str] = []
    open_legs: list[str] = []
    for feature in feature_collection.get("features") or []:
        geom = (feature or {}).get("geometry") or {}
        props = (feature or {}).get("properties") or {}
        if props.get("type") != "maritime":
            features.append(copy.deepcopy(feature))
            continue
        label = _label(props)
        if geom.get("type") != "LineString":
            failures.append(f"{label} : géométrie maritime inattendue")
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            failures.append(f"{label} : extrémités manquantes")
            continue
        start = (float(coords[0][0]), float(coords[0][1]))
        end = (float(coords[-1][0]), float(coords[-1][1]))
        try:
            route = route_fn(start, end, deadline=deadline)
        except Exception as exc:
            failures.append(f"{label} : {exc}")
            continue
        line = _engine_line(route)
        if line is None:
            failures.append(f"{label} : jambe maritime non recalculée")
            continue
        if _constraint_open(route):
            open_legs.append(label)
        cloned = copy.deepcopy(feature)
        cloned["geometry"]["coordinates"] = line
        features.append(cloned)
    candidate["features"] = features
    violations = contract_violations(candidate)
    if _overland(feature_collection) != _overland(candidate):
        violations.append("overland Saint-Maur modifiée")
    violations.extend(failures)
    for label in open_legs:
        violations.append(f"constraintStatus open : {label}")
    return candidate, violations


def format_report(candidate: dict, violations: list[str], *, write: bool) -> str:
    lines = line_strings(candidate)
    panama = any(
        in_passage_box(float(coord[0]), float(coord[1]), PANAMA_BOX)
        for line in lines
        if "Cayenne" in line["from"] and "Papeete" in line["to"]
        for coord in line["coordinates"]
    )
    suez = [
        pair
        for pair in iter_vertices(candidate)
        if in_passage_box(pair[0], pair[1], SUEZ_BOX)
    ]
    cape = any(
        "Bonne Espérance" in _blob((feature.get("properties") or {}))
        for feature in candidate.get("features") or []
    )
    halifax = len(_maritime(lines, "Halifax", "Saint-Pierre")) + len(
        _maritime(lines, "Saint-Pierre", "Halifax")
    )
    overland = [
        feature
        for feature in candidate.get("features") or []
        if (feature.get("properties") or {}).get("type") == "overland"
    ]
    cayenne_halifax = [
        feature
        for feature in candidate.get("features") or []
        if _joins_cayenne_halifax(feature.get("properties") or {})
    ]
    open_count = sum(1 for item in violations if item.startswith("constraintStatus open"))
    rows = [
        f"Cayenne → Papeete : {'Panama présent' if panama else 'Panama absent'}",
        f"Suez : {'aucun sommet' if not suez else f'{len(suez)} sommet(s)'}",
        f"Bonne Espérance : {'nommé' if cape else 'absent'}",
        f"Halifax ↔ Saint-Pierre : {halifax} jambes maritimes",
        f"overland : {len(overland)}",
        f"Cayenne ↔ Halifax : {'aucune' if not cayenne_halifax else str(len(cayenne_halifax))}",
        f"contraintes ouvertes : {'aucune' if open_count == 0 else str(open_count)}",
        f"écriture : {'oui' if write and not violations else 'non'}",
        f"verdict : {'conforme' if not violations else 'refusé'}",
    ]
    rows.extend(f"- {item}" for item in violations)
    return "\n".join(rows) + "\n"


def _joins_cayenne_halifax(props: dict) -> bool:
    src = props.get("from") or ""
    dst = props.get("to") or ""
    return ("Cayenne" in src and "Halifax" in dst) or ("Halifax" in src and "Cayenne" in dst)


def _write_candidate(dest: Path, candidate: dict) -> None:
    if dest_targets_public_route(dest):
        raise OSError("public/route.geojson")
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(candidate, ensure_ascii=False, indent=2) + "\n"
    temporary = dest.with_name(dest.name + ".tmp")
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, dest)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None, route_fn=None) -> int:
    parser = argparse.ArgumentParser(description="Recalcule un FeatureCollection Berry sans publier le fichier public.")
    parser.add_argument("--src", required=True, help="FeatureCollection GeoJSON (pas un chemin figé)")
    parser.add_argument("--write", action="store_true", help="Écrit le candidat. Exige --dest.")
    parser.add_argument("--dest", default=None, help="Fichier candidat. Interdit : public/route.geojson.")
    args = parser.parse_args(argv)
    if args.write and not args.dest:
        print("refusé : --write exige --dest", file=sys.stderr)
        return 2
    if args.write and dest_targets_public_route(args.dest):
        print(
            "refusé : --dest ne peut pas être public/route.geojson ni un lien vers ce fichier",
            file=sys.stderr,
        )
        return 2
    try:
        feature_collection = json.loads(Path(args.src).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        print(f"source illisible : {exc}", file=sys.stderr)
        return 2
    if not isinstance(feature_collection, dict):
        print("source illisible : FeatureCollection attendu", file=sys.stderr)
        return 2
    fn = route_fn or _default_route_fn
    try:
        candidate, violations = rebuild_collection(feature_collection, fn)
    except (TypeError, ValueError, KeyError) as exc:
        print(f"candidat illisible : {exc}", file=sys.stderr)
        return 1
    wrote = False
    if args.write and not violations:
        dest = Path(args.dest)
        if not dest.is_absolute():
            dest = Path.cwd() / dest
        if dest_targets_public_route(dest):
            print(
                "refusé : --dest ne peut pas être public/route.geojson ni un lien vers ce fichier",
                file=sys.stderr,
            )
            return 2
        try:
            _write_candidate(dest, candidate)
            wrote = True
        except OSError as exc:
            violations.append(f"écriture impossible : {exc}")
    sys.stdout.write(format_report(candidate, violations, write=wrote))
    if violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

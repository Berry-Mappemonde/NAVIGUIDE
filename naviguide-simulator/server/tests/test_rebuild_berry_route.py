"""Outil de recalcul : moteur simulé, aucun appel searoute, rien dans le fichier public.

Le FeatureCollection de test n'est pas le fichier publié. Il ne va ni dans
public/route.geojson, ni dans un stock du poste.
"""
import json
from pathlib import Path

import pytest

from rebuild_berry_route import (
    dest_targets_public_route,
    main,
    public_route_file,
    rebuild_collection,
)

PANAMA = [-79.9, 9.1]
SUEZ = [32.2, 30.2]
CAYENNE = [-52.33, 4.94]
PAPEETE = [-149.57, -17.54]
HALIFAX = [-63.57, 44.65]
SPM = [-56.17, 46.78]
CAPE_A = [18.5, -34.4]
CAPE_B = [20.0, -35.0]
SAINT_MAUR = [2.47, 48.79]
LA_ROCHELLE = [-1.15, 46.16]


def _line(src: str, dst: str, kind: str, coords: list, name: str | None = None) -> dict:
    props = {"from": src, "to": dst, "type": kind}
    if name:
        props["name"] = name
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def sample_collection() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            _line("Cayenne", "Papeete", "maritime", [CAYENNE, [-70.0, 12.0], PAPEETE]),
            _line("Halifax", "Saint-Pierre", "maritime", [HALIFAX, SPM]),
            _line("Saint-Pierre", "Halifax", "maritime", [SPM, HALIFAX]),
            _line(
                "Le Cap",
                "Melbourne",
                "maritime",
                [CAPE_A, CAPE_B],
                name="Cap de Bonne Espérance",
            ),
            _line("Saint-Maur-des-Fossés", "La Rochelle", "overland", [SAINT_MAUR, LA_ROCHELLE]),
            {
                "type": "Feature",
                "properties": {"name": "Papeete"},
                "geometry": {"type": "Point", "coordinates": PAPEETE},
            },
        ],
    }


def _key(point) -> tuple[float, float]:
    return (round(float(point[0]), 2), round(float(point[1]), 2))


def _feature(coords, *, open_status: bool = False) -> dict:
    props = {"length": 1.0, "units": "km"}
    if open_status:
        props["constraintStatus"] = "open"
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def _engine(
    calls: list,
    *,
    suez: bool = False,
    drop_halifax: bool = False,
    open_leg: bool = False,
    drop_panama: bool = False,
    horn: bool = False,
):
    def route_fn(start, end, deadline=None):
        calls.append((_key(start), _key(end)))
        pair = (_key(start), _key(end))
        if pair == (_key(SAINT_MAUR), _key(LA_ROCHELLE)):
            raise AssertionError("l'overland ne se recalcule pas")
        if pair == (_key(CAYENNE), _key(PAPEETE)):
            if drop_panama:
                return _feature([CAYENNE, [-70.0, 12.0], PAPEETE])
            if horn:
                return _feature([CAYENNE, PANAMA, [-67.0, -55.0], PAPEETE])
            return _feature([CAYENNE, PANAMA, PAPEETE])
        if pair == (_key(HALIFAX), _key(SPM)):
            return _feature([HALIFAX, SPM], open_status=open_leg)
        if pair == (_key(SPM), _key(HALIFAX)):
            if drop_halifax:
                return None
            return _feature([SPM, HALIFAX])
        if pair == (_key(CAPE_A), _key(CAPE_B)):
            coords = [CAPE_A, SUEZ, CAPE_B] if suez else [CAPE_A, CAPE_B]
            return _feature(coords)
        raise AssertionError(f"jambe inattendue {pair}")

    return route_fn


def _write_src(tmp_path: Path) -> Path:
    src = tmp_path / "collection.geojson"
    src.write_text(json.dumps(sample_collection()), encoding="utf-8")
    return src


def _public_digest() -> bytes:
    return public_route_file().read_bytes()


def test_collection_argument_does_not_touch_the_public_file(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("moteur réel")

    monkeypatch.setattr("rebuild_berry_route._default_route_fn", boom)
    before = _public_digest()
    calls: list = []
    source = sample_collection()
    candidate, violations = rebuild_collection(source, _engine(calls))
    assert violations == []
    assert len(calls) == 4
    assert not list(tmp_path.iterdir())
    assert _public_digest() == before
    cayenne = next(
        feature
        for feature in candidate["features"]
        if (feature.get("properties") or {}).get("from") == "Cayenne"
    )
    assert PANAMA in cayenne["geometry"]["coordinates"]
    assert [feature for feature in candidate["features"] if (feature.get("properties") or {}).get("type") == "overland"] == [
        feature for feature in source["features"] if (feature.get("properties") or {}).get("type") == "overland"
    ]


def test_dry_run_report_is_compliant_and_writes_nothing(tmp_path, monkeypatch, capsys):
    def boom(*_args, **_kwargs):
        raise AssertionError("moteur réel")

    monkeypatch.setattr("rebuild_berry_route._default_route_fn", boom)
    src = _write_src(tmp_path)
    raw = src.read_text(encoding="utf-8")
    before = _public_digest()
    calls: list = []
    code = main(["--src", str(src)], route_fn=_engine(calls))
    out = capsys.readouterr().out
    assert code == 0
    assert len(calls) == 4
    assert "Cayenne → Papeete : Panama présent" in out
    assert "Suez : aucun sommet" in out
    assert "Bonne Espérance : nommé" in out
    assert "Halifax ↔ Saint-Pierre : 2 jambes maritimes" in out
    assert "overland : 1" in out
    assert "Cayenne ↔ Halifax : aucune" in out
    assert "contraintes ouvertes : aucune" in out
    assert "écriture : non" in out
    assert "verdict : conforme" in out
    assert src.read_text(encoding="utf-8") == raw
    assert _public_digest() == before
    assert list(tmp_path.glob("*.geojson")) == [src]


def test_write_outside_public_keeps_contract(tmp_path, capsys):
    src = _write_src(tmp_path)
    source = json.loads(src.read_text(encoding="utf-8"))
    before = _public_digest()
    dest = tmp_path / "candidat.geojson"
    calls: list = []
    code = main(
        ["--src", str(src), "--write", "--dest", str(dest)],
        route_fn=_engine(calls),
    )
    capsys.readouterr()
    assert code == 0
    assert dest.is_file()
    written = json.loads(dest.read_text(encoding="utf-8"))
    assert len(written["features"]) == len(source["features"])
    assert [f for f in written["features"] if (f.get("properties") or {}).get("type") == "overland"] == [
        f for f in source["features"] if (f.get("properties") or {}).get("type") == "overland"
    ]
    papeete = next(
        f
        for f in written["features"]
        if (f.get("properties") or {}).get("from") == "Cayenne"
    )
    assert PANAMA in papeete["geometry"]["coordinates"]
    halifax = [
        feature
        for feature in written["features"]
        if (feature.get("properties") or {}).get("type") == "maritime"
        and "Halifax" in ((feature.get("properties") or {}).get("from") or "")
        and "Saint-Pierre" in ((feature.get("properties") or {}).get("to") or "")
    ]
    spm = [
        feature
        for feature in written["features"]
        if (feature.get("properties") or {}).get("type") == "maritime"
        and "Saint-Pierre" in ((feature.get("properties") or {}).get("from") or "")
        and "Halifax" in ((feature.get("properties") or {}).get("to") or "")
    ]
    assert len(halifax) == 1 and len(spm) == 1
    assert halifax[0] is not spm[0]
    assert dest_targets_public_route(dest) is False
    assert _public_digest() == before


@pytest.mark.parametrize(
    ("flag", "needle"),
    [
        ("suez", "sommet dans la boîte Suez"),
        ("halifax", "deux jambes maritimes"),
        ("panama", "boîte Panama"),
        ("horn", "40° S"),
    ],
)
def test_suez_or_lost_halifax_exits_nonzero_and_writes_nothing(tmp_path, capsys, flag, needle):
    src = _write_src(tmp_path)
    before = _public_digest()
    dest = tmp_path / "candidat.geojson"
    calls: list = []
    code = main(
        ["--src", str(src), "--write", "--dest", str(dest)],
        route_fn=_engine(
            calls,
            suez=flag == "suez",
            drop_halifax=flag == "halifax",
            drop_panama=flag == "panama",
            horn=flag == "horn",
        ),
    )
    out = capsys.readouterr().out
    assert code != 0
    assert needle in out
    assert "verdict : refusé" in out
    assert "écriture : non" in out
    assert not dest.exists()
    assert _public_digest() == before
    assert calls


def test_dry_run_refusal_writes_nothing(tmp_path, capsys):
    src = _write_src(tmp_path)
    before = _public_digest()
    code = main(["--src", str(src)], route_fn=_engine([], suez=True))
    out = capsys.readouterr().out
    assert code != 0
    assert "sommet dans la boîte Suez" in out
    assert "écriture : non" in out
    assert _public_digest() == before
    assert list(tmp_path.glob("*.geojson")) == [src]


def test_server_startup_and_ci_do_not_launch_the_tool():
    server = Path(__file__).resolve().parents[1]
    root = server.parents[1]
    assert "rebuild_berry_route" not in (server / "main.py").read_text(encoding="utf-8")
    workflow = root / ".github" / "workflows" / "ci.yml"
    assert "rebuild_berry_route" not in workflow.read_text(encoding="utf-8")


def test_open_constraint_is_not_written(tmp_path, capsys):
    src = _write_src(tmp_path)
    before = _public_digest()
    dest = tmp_path / "candidat.geojson"
    code = main(
        ["--src", str(src), "--write", "--dest", str(dest)],
        route_fn=_engine([], open_leg=True),
    )
    out = capsys.readouterr().out
    assert code != 0
    assert "constraintStatus open" in out
    assert "verdict : refusé" in out
    assert not dest.exists()
    assert _public_digest() == before


def test_write_without_dest_is_refused_before_compute(tmp_path, capsys):
    calls: list = []
    code = main(
        ["--write", "--src", str(tmp_path / "absent.geojson")],
        route_fn=_engine(calls),
    )
    err = capsys.readouterr().err
    assert code != 0
    assert calls == []
    assert "--dest" in err
    assert "source illisible" not in err


def test_write_public_route_is_refused_before_compute(tmp_path, monkeypatch, capsys):
    public = public_route_file()
    before = public.read_bytes()
    calls: list = []
    simulator = public.parent.parent
    monkeypatch.chdir(simulator)
    targets = [
        str(public),
        "public/route.geojson",
        str(public.parent / ".." / "public" / "route.geojson"),
    ]
    link = tmp_path / "lien.geojson"
    link.symlink_to(public)
    targets.append(str(link))
    linked_dir = tmp_path / "pub"
    linked_dir.symlink_to(public.parent, target_is_directory=True)
    targets.append(str(linked_dir / "route.geojson"))
    for dest in targets:
        calls.clear()
        code = main(
            ["--src", str(tmp_path / "absent.geojson"), "--write", "--dest", dest],
            route_fn=_engine(calls),
        )
        captured = capsys.readouterr()
        assert code != 0, dest
        assert calls == [], dest
        assert "public/route.geojson" in captured.err, dest
        assert "source illisible" not in captured.err
        assert "verdict" not in captured.out
        assert public.read_bytes() == before
    assert dest_targets_public_route(link)
    assert dest_targets_public_route(linked_dir / "route.geojson")

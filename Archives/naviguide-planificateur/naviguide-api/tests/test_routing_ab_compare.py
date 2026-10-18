"""Intégration du banc A/B — saute un moteur s'il n'est pas installé."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.compare import run_comparison, write_report
from routing_ab.engines import available_engines, run_engine
from routing_ab.legs import CORE_LEG_IDS, NOUMEA, TORRES_ITIN, WALLIS


def test_available_engines_lists_enriched_when_cargo_present():
    ids = available_engines(include_sr16=False)
    if "searoute_14" in ids or "scgraph_marnet" in ids:
        assert "enriched_sailing" in ids


@pytest.mark.skipif("searoute_14" not in available_engines(include_sr16=False), reason="searoute absent")
def test_searoute_returns_linestring_torres():
    result = run_engine("searoute_14", NOUMEA, TORRES_ITIN)
    assert result.error is None
    assert len(result.coords) >= 2
    assert result.coords[0][0] != result.coords[-1][0]


@pytest.mark.skipif("searoute_14" not in available_engines(include_sr16=False), reason="searoute absent")
def test_enriched_torres_is_not_coral_detour():
    from routing_ab.metrics import path_length_nm

    cargo = run_engine("searoute_14", NOUMEA, TORRES_ITIN)
    enriched = run_engine("enriched_sailing", NOUMEA, TORRES_ITIN)
    assert cargo.error is None and enriched.error is None
    cargo_nm = path_length_nm(cargo.coords)
    enriched_nm = path_length_nm(enriched.coords)
    assert enriched_nm < cargo_nm * 1.35
    assert not any(p[1] > -14 and p[0] > 147 for p in enriched.coords)


@pytest.mark.skipif("searoute_14" not in available_engines(include_sr16=False), reason="searoute absent")
def test_enriched_noumea_arafura_uses_torres_gate():
    from routing_ab.legs import ARAFURA

    result = run_engine("enriched_sailing", NOUMEA, ARAFURA)
    assert result.error is None
    near_gate = any(
        141.7 <= p[0] <= 143.0 and -10.9 <= p[1] <= -10.3
        for p in result.coords
    )
    assert near_gate, "la route enrichie doit enfiler les portes Torres"


def test_comparison_report_shape_core_without_sr16(tmp_path):
    engines = [e for e in available_engines(include_sr16=False) if e != "scgraph_oak_ridge"]
    if not engines:
        pytest.skip("aucun moteur cargo installé")
    report = run_comparison(engine_ids=engines, core_only=True, include_sr16=False)
    assert set(report["legs"]) == CORE_LEG_IDS
    assert report["rows"]
    write_report(report, tmp_path)
    assert (tmp_path / "index.html").is_file()
    geo = json.loads((tmp_path / "routes.geojson").read_text())
    assert geo["type"] == "FeatureCollection"


@pytest.mark.skipif("searoute_14" not in available_engines(include_sr16=False), reason="searoute absent")
def test_wallis_noumea_does_not_circumnavigate():
    result = run_engine("searoute_14", WALLIS, NOUMEA)
    if result.error:
        pytest.skip(result.error)
    from routing_ab.metrics import path_length_nm

    nm = path_length_nm(result.coords)
    assert nm < 4000, f"détour globe suspect: {nm} nm"

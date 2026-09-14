from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.advise import build_advice, write_advice
from routing_ab.engines import available_engines


def test_build_advice_lists_itinerary_torres():
    # The catalogue part does not need searoute
    from routing_ab.itinerary_gates import ITINERARY_GATES

    assert any("Torres" in g.name for g in ITINERARY_GATES)


@pytest.mark.skipif("searoute_14" not in available_engines(include_sr16=False), reason="searoute absent")
def test_advise_writes_html(tmp_path):
    advice = build_advice()
    write_advice(advice, tmp_path)
    assert (tmp_path / "advise.html").is_file()
    verdicts = {d["id"]: d["decision"]["verdict"] for d in advice["decisions"]}
    assert verdicts.get("torres_gne_pow") == "GARDER"
    assert verdicts.get("mentawai_west") in {"INUTILE", "GARDER", "JETER"}
    assert "Panama" in advice["next_gate"].get("recommendation", "") or advice["next_gate"].get("missing_canals") == []

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.findings import summarize


def _row(leg, engine, nm, ok=True):
    return {
        "leg_id": leg,
        "engine": engine,
        "length_nm": nm,
        "ok": ok,
    }


def test_summarize_detects_oak_ridge_and_enriched_fail():
    rows = [
        _row("a", "searoute_14", 100),
        _row("a", "searoute_16", 110),
        _row("a", "scgraph_marnet", 105),
        _row("a", "scgraph_oak_ridge", 200),
        _row("a", "enriched_sailing", 100, ok=False),
    ]
    out = summarize(rows)
    assert out["oak_ridge_longer_legs"] == ["a"]
    assert out["enriched_failures"] == ["a"]
    assert out["bullets"]

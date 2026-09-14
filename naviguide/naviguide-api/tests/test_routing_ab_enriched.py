"""Portes voile et décalage cargo — déterministes, sans réseau."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.enriched import (
    GATES,
    enriched_route,
    gates_for_leg,
    offset_from_cargo,
    stitch_via_route,
    vias_for_leg,
)
from routing_ab.legs import ARAFURA, HAUT_AUS_2, HAUT_AUS_3, NOUMEA, TORRES_ITIN, WALLIS


def test_torres_gate_applies_to_noumea_torres():
    ids = {g.id for g in gates_for_leg(NOUMEA, TORRES_ITIN)}
    assert "torres_gne_pow" in ids


def test_mentawai_gate_applies_to_haut_aus():
    ids = {g.id for g in gates_for_leg(HAUT_AUS_2, HAUT_AUS_3)}
    assert "mentawai_west" in ids


def test_antimeridian_gate_applies_to_wallis_noumea():
    ids = {g.id for g in gates_for_leg(WALLIS, NOUMEA)}
    assert "antimeridian_pacific" in ids


def test_torres_vias_are_between_noumea_and_arafura():
    vias = vias_for_leg(NOUMEA, ARAFURA)
    lons = [v[0] for v in vias]
    assert any(141.5 < lon < 143.5 for lon in lons)


def test_ocean_leg_has_no_torres_via():
    # Cape Verde → Saint Lucia must not receive Torres vias
    vias = vias_for_leg((-24.531, 13.919), (-61.498, 13.499))
    assert vias == []


def test_stitch_inserts_vias_in_order():
    calls: list[tuple] = []

    def fake(a, b):
        calls.append((a, b))
        return [list(a), list(b)]

    vias = vias_for_leg(NOUMEA, TORRES_ITIN)
    coords = stitch_via_route(fake, NOUMEA, TORRES_ITIN)
    assert coords[0] == list(NOUMEA)
    assert coords[-1] == list(TORRES_ITIN)
    assert len(calls) == 1 + len(vias)
    if vias:
        assert calls[0][1] == vias[0]


def test_offset_moves_long_busy_stretch():
    # Fake route in the Strait of Dover, long enough to trigger the offset
    coords = [[-1.0 + i * 0.15, 51.0] for i in range(20)]
    out = offset_from_cargo(coords, offset_nm=30.0, min_run_nm=50.0)
    moved = sum(
        1 for a, b in zip(coords, out) if abs(a[0] - b[0]) > 0.01 or abs(a[1] - b[1]) > 0.01
    )
    assert moved >= 3


def test_offset_skips_torres_gate():
    coords = [[142.1, -10.6], [142.2, -10.55], [142.3, -10.5]]
    out = offset_from_cargo(coords, offset_nm=30.0, min_run_nm=1.0)
    assert out == [list(p) for p in coords]


def test_gates_have_stable_ids():
    assert {g.id for g in GATES} == {
        "torres_gne_pow",
        "mentawai_west",
        "antimeridian_pacific",
    }


def test_detour_guard_falls_back_to_cargo():
    start, end = NOUMEA, ARAFURA

    def fake(a, b):
        if tuple(a) == start and tuple(b) == end:
            return [list(start), list(end)]
        return [list(a), [150.0, -12.0], [155.0, -13.0], list(b)]

    out = enriched_route(fake, start, end)
    assert [tuple(p) for p in out] == [start, end]

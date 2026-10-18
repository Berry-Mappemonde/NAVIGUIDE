from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routing_ab.decide import decide_gate
from routing_ab.filament import dist_to_filament_nm, mean_dist_to_filament_nm, offset_from_filament
from routing_ab.itinerary_gates import ITINERARY_GATES, missing_canals_on_path


def test_garder_if_already_in_itinerary():
    d = decide_gate(1645, 1633, 0, 0, 0, 0, 0.55, in_itinerary=True)
    assert d["verdict"] == "GARDER"


def test_jeter_if_coral_worse():
    d = decide_gate(1645, 2679, 0, 2, 0, 0, 0.55, in_itinerary=False)
    assert d["verdict"] == "JETER"


def test_inutile_if_quiet_and_longer():
    d = decide_gate(1416, 1880, 0, 0, 0, 0, 1.0, in_itinerary=False)
    assert d["verdict"] == "INUTILE"


def test_garder_if_fixes_coral():
    d = decide_gate(2600, 1650, 3, 0, 0, 0, 0.5, in_itinerary=False)
    assert d["verdict"] == "GARDER"


def test_itinerary_has_torres():
    names = [g.name for g in ITINERARY_GATES]
    assert any("Torres" in n for n in names)


def test_missing_panama_on_fake_path():
    # A point in the Panama box, no itinerary plot there
    path = [[-80.0, 9.0], [-90.0, 5.0]]
    assert "Panama" in missing_canals_on_path(path)


def test_filament_offset_moves_middle():
    cargo = [[-25.0 + i, 13.0] for i in range(12)]
    shifted = offset_from_filament(cargo, offset_nm=20.0, keep_ends_frac=0.2, is_land=None)
    mid = len(cargo) // 2
    assert shifted[0] == cargo[0]
    assert shifted[-1] == cargo[-1]
    dist = dist_to_filament_nm(shifted[mid][0], shifted[mid][1], cargo)
    assert dist > 10
    assert mean_dist_to_filament_nm(shifted, cargo) > mean_dist_to_filament_nm(cargo, cargo)

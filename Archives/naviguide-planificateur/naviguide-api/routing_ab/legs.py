"""Jambes Berry utilisées pour le banc A/B.

Les coordonnées viennent de itineraryPoints.ts et des tests Torres
historiques (WP 141.9 / -10.7). Rien n'est inventé hors de ces sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

LonLat = Tuple[float, float]  # (lon, lat)


@dataclass(frozen=True)
class BenchmarkLeg:
    id: str
    label: str
    start: LonLat
    end: LonLat
    family: str  # torres | mentawai | antimeridian | ocean
    notes: str


# Itinerary (lon, lat) — same numbers as itineraryPoints.ts / test_regression.py
NOUMEA = (166.4572, -22.2958)
TORRES_ITIN = (142.135679, -10.543294)
TORRES_LEGACY = (141.9, -10.7)
ARAFURA = (135.7760571767464, -8.975505823887872)
HAUT_AUS_2 = (105.09261288903605, -9.365171092340532)
HAUT_AUS_3 = (88.60640235539029, 6.372651054775204)
PAPEETE = (-149.5685, -17.5116)
WALLIS = (-176.2036, -13.2725)
CAYENNE = (-52.3533, 4.9333)
CAP_VERDE = (-24.531, 13.919)
SAINTE_LUCIE = (-61.498, 13.499)


BENCHMARK_LEGS: tuple[BenchmarkLeg, ...] = (
    BenchmarkLeg(
        id="noumea_torres_itin",
        label="Nouméa → Torres (WP itinéraire)",
        start=NOUMEA,
        end=TORRES_ITIN,
        family="torres",
        notes="Détroit de Torres, risque de détour mer de Corail.",
    ),
    BenchmarkLeg(
        id="noumea_torres_legacy",
        label="Nouméa → Torres (WP tests 141.9)",
        start=NOUMEA,
        end=TORRES_LEGACY,
        family="torres",
        notes="Waypoint historique de test_torres.py (Prince of Wales).",
    ),
    BenchmarkLeg(
        id="torres_arafura",
        label="Torres → Arafura",
        start=TORRES_ITIN,
        end=ARAFURA,
        family="torres",
        notes="Sortie ouest du détroit vers la mer d'Arafura.",
    ),
    BenchmarkLeg(
        id="haut_aus_2_3",
        label="haut Australie 2 → 3 (Mentawai / Sumatra)",
        start=HAUT_AUS_2,
        end=HAUT_AUS_3,
        family="mentawai",
        notes="Arc qui rase Nias / Mentawai si le graphe cargo coupe trop près.",
    ),
    BenchmarkLeg(
        id="wallis_noumea",
        label="Wallis → Nouméa (antiméridien)",
        start=WALLIS,
        end=NOUMEA,
        family="antimeridian",
        notes="Franchissement ±180°. Le trait ne doit pas faire le tour du globe.",
    ),
    BenchmarkLeg(
        id="papeete_wallis",
        label="Papeete → Wallis",
        start=PAPEETE,
        end=WALLIS,
        family="antimeridian",
        notes="Traversée Pacifique, proche de la ligne de changement de date.",
    ),
    BenchmarkLeg(
        id="cayenne_papeete",
        label="Cayenne → Papeete",
        start=CAYENNE,
        end=PAPEETE,
        family="ocean",
        notes="Très longue jambe : montre le couloir cargo transocéanique.",
    ),
    BenchmarkLeg(
        id="cap_verde_sainte_lucie",
        label="Cap-Vert → Sainte-Lucie",
        start=CAP_VERDE,
        end=SAINTE_LUCIE,
        family="ocean",
        notes="Alizés Atlantique, couloir transatlantique cargo.",
    ),
)


CORE_LEG_IDS = frozenset({
    "noumea_torres_itin",
    "noumea_torres_legacy",
    "torres_arafura",
    "haut_aus_2_3",
    "wallis_noumea",
})


def legs_by_id(*ids: str) -> tuple[BenchmarkLeg, ...]:
    wanted = set(ids)
    return tuple(leg for leg in BENCHMARK_LEGS if leg.id in wanted)

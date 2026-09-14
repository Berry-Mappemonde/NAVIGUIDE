"""Portes déjà présentes dans l'itinéraire Berry (itineraryPoints.ts).

Ce sont les vrais plots de production : le frontend les enchaîne, puis
``GET /route`` calcule chaque jambe. Ce n'est PAS la liste prototype
``enriched.GATES`` (Mentawai ouest, via 180°) — celle-là n'est pas branchée.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cargo import NO_OFFSET_BOXES, _in_box
from .legs import LonLat


@dataclass(frozen=True)
class ItineraryGate:
    name: str
    lon: float
    lat: float
    kind: str  # escale | porte
    note: str


# Copie fidèle des « Point intermédiaire » + escales-clés de itineraryPoints.ts
ITINERARY_GATES: tuple[ItineraryGate, ...] = (
    ItineraryGate("Avant Corse", 8.438, 41.181, "porte", "Contournement Corse"),
    ItineraryGate("Ajaccio", 8.7386, 41.9192, "escale", "Escale"),
    ItineraryGate("Après Corse N", 8.664, 43.306, "porte", "Sortie Corse"),
    ItineraryGate("Après Corse E", 9.844, 42.221, "porte", "Sortie Corse"),
    ItineraryGate("Canaries", -15.181, 29.325, "escale", "Escale"),
    ItineraryGate("Cap-Vert", -24.531, 13.919, "porte", "Plot alizés"),
    ItineraryGate("Sainte-Lucie", -61.498, 13.499, "escale", "Escale"),
    ItineraryGate("Torres (GNEC)", 142.135679, -10.543294, "porte", "Détroit — déjà dans l'app"),
    ItineraryGate("Haut Australie 1", 135.776, -8.976, "porte", "Arafura"),
    ItineraryGate("Haut Australie 2", 105.093, -9.365, "porte", "Sud Indonésie"),
    ItineraryGate("Haut Australie 3", 88.606, 6.373, "porte", "Nord océan Indien"),
    ItineraryGate("Cap Bonne-Espérance", 14.084, -33.583, "porte", "Contournement Afrique"),
    ItineraryGate("Sainte-Hélène", -5.7392, -15.9165, "porte", "Plot Atlantique S"),
    ItineraryGate("Ascension", -14.3291, -7.9692, "porte", "Plot Atlantique S"),
    ItineraryGate("Ascension–Cap-Vert", -24.595, 4.649, "porte", "Remontée Atlantique"),
)


# Canaux / détroits où une porte manquerait si une jambe les traverse sans plot.
CANAL_HINTS: tuple[tuple[str, tuple], ...] = (
    ("Panama", NO_OFFSET_BOXES[1]),
    ("Suez", NO_OFFSET_BOXES[2]),
    ("Gibraltar", NO_OFFSET_BOXES[3]),
    ("Torres", NO_OFFSET_BOXES[0]),
)


def itinerary_covers_box(box: tuple) -> bool:
    return any(_in_box(g.lon, g.lat, box) for g in ITINERARY_GATES)


def coords_hit_box(coords: list[list[float]], box: tuple) -> bool:
    return any(_in_box(p[0], p[1], box) for p in coords)


def missing_canals_on_path(coords: list[list[float]]) -> list[str]:
    """Canaux croisés par le trait cargo, sans plot d'itinéraire dedans."""
    missing: list[str] = []
    for name, box in CANAL_HINTS:
        if coords_hit_box(coords, box) and not itinerary_covers_box(box):
            missing.append(name)
    return missing


def as_lonlat(gate: ItineraryGate) -> LonLat:
    return (gate.lon, gate.lat)

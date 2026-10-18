"""Règles automatiques GARDER / JETER / INUTILE — le skipper peut contredire."""

from __future__ import annotations

from typing import Any, Optional


def decide_gate(
    cargo_nm: Optional[float],
    gated_nm: Optional[float],
    cargo_coral: int,
    gated_coral: int,
    cargo_land: int,
    gated_land: int,
    cargo_anti: Optional[float],
    in_itinerary: bool,
    extra_ratio_useless: float = 1.10,
    extra_ratio_reject: float = 1.35,
) -> dict[str, Any]:
    """Décide à partir des chiffres, pas à partir d'une carte regardée à la main."""
    if cargo_nm is None or gated_nm is None or cargo_nm <= 0:
        return {"verdict": "À MESURER", "why": "pas assez de chiffres (moteur absent)."}

    ratio = gated_nm / cargo_nm
    if gated_coral > cargo_coral:
        return {
            "verdict": "JETER",
            "why": "la porte recréé un détour mer de Corail (ou l'aggrave).",
            "ratio": round(ratio, 3),
        }
    if gated_land > cargo_land + 1:
        return {
            "verdict": "JETER",
            "why": "la porte ajoute des points sur terre.",
            "ratio": round(ratio, 3),
        }
    if ratio > extra_ratio_reject:
        return {
            "verdict": "JETER",
            "why": f"détour trop long ({ratio:.2f}× la route cargo).",
            "ratio": round(ratio, 3),
        }
    if in_itinerary and gated_coral == 0:
        return {
            "verdict": "GARDER",
            "why": "déjà dans l'itinéraire Berry, et le trait reste propre.",
            "ratio": round(ratio, 3),
        }
    if (
        cargo_coral == 0
        and cargo_land == 0
        and (cargo_anti or 0) >= 0.99
        and ratio > extra_ratio_useless
    ):
        return {
            "verdict": "INUTILE",
            "why": (
                "le cargo est déjà hors couloir et hors terre ; "
                f"la porte allonge de {(ratio - 1) * 100:.0f} % sans gain trafic."
            ),
            "ratio": round(ratio, 3),
        }
    if cargo_coral > 0 and gated_coral == 0:
        return {
            "verdict": "GARDER",
            "why": "la porte évite un détour mer de Corail.",
            "ratio": round(ratio, 3),
        }
    return {
        "verdict": "GARDER",
        "why": "la porte n'empire ni la terre ni la Corail, allongement acceptable.",
        "ratio": round(ratio, 3),
    }

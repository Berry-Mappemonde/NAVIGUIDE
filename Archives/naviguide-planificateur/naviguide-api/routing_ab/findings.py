"""Synthèse automatique à partir des lignes du banc A/B."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_leg: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_leg[row["leg_id"]][row["engine"]] = row

    sr14_vs_16: list[float] = []
    sr14_vs_marnet: list[float] = []
    for engines in by_leg.values():
        a, b = engines.get("searoute_14"), engines.get("searoute_16")
        if a and b and a.get("length_nm") and b.get("length_nm"):
            sr14_vs_16.append(abs(a["length_nm"] - b["length_nm"]))
        a, c = engines.get("searoute_14"), engines.get("scgraph_marnet")
        if a and c and a.get("length_nm") and c.get("length_nm"):
            sr14_vs_marnet.append(abs(a["length_nm"] - c["length_nm"]))

    oak_worse = []
    for leg_id, engines in by_leg.items():
        a, oak = engines.get("searoute_14"), engines.get("scgraph_oak_ridge")
        if a and oak and a.get("length_nm") and oak.get("length_nm"):
            if oak["length_nm"] > a["length_nm"] * 1.15:
                oak_worse.append(leg_id)

    enriched_fail = [
        row["leg_id"]
        for row in rows
        if row["engine"] == "enriched_sailing" and not row.get("ok")
    ]

    bullets = [
        "searoute 1.4 et 1.6 restent le même type de couloir cargo ; "
        f"écart médian de longueur ≈ {_median(sr14_vs_16):.0f} nm.",
        "scgraph marnet suit le même graphe que searoute "
        f"(écart médian ≈ {_median(sr14_vs_marnet):.0f} nm) : ce n'est pas un nouveau chenal.",
        (
            "scgraph Oak Ridge allonge nettement : " + ", ".join(oak_worse) + "."
            if oak_worse
            else "scgraph Oak Ridge reste comparable sur ces jambes."
        ),
        (
            "Le graphe enrichi a encore des échecs (Corail / détour) : "
            + ", ".join(enriched_fail)
            if enriched_fail
            else "Après garde-fou, le graphe enrichi n'introduit plus de détour Corail."
        ),
        "Cayenne → Papeete : tous les graphes cargos bruts piquent la terre "
        "(canaux / îles). Le pipeline /route (avoid_land) reste nécessaire.",
        "GET /route de production n'est pas modifié. Prochaine étape : "
        "portes voile validées une par une, puis décalage cargo hors détroits.",
    ]
    return {
        "sr14_vs_sr16_median_nm": round(_median(sr14_vs_16), 1),
        "sr14_vs_marnet_median_nm": round(_median(sr14_vs_marnet), 1),
        "oak_ridge_longer_legs": oak_worse,
        "enriched_failures": enriched_fail,
        "bullets": bullets,
    }


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2

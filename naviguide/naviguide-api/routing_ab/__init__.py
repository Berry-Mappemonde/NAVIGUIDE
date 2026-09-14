"""Banc d'essai A/B du routage mer NAVIGUIDE (Problème A).

Compare les graphes cargos (searoute, scgraph) et un graphe enrichi
voile (portes de catamaran + décalage hors couloirs). Ne change pas
l'endpoint de production ``GET /route``.
"""

from .legs import BENCHMARK_LEGS

__all__ = ["BENCHMARK_LEGS"]

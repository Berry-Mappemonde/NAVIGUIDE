# Banc A/B — routage mer (Problème A)

Compare, **sans changer** `GET /route` :

1. `searoute` 1.4.3 (production)
2. `searoute` 1.6.0 (venv isolé)
3. `scgraph` sur `marnet` (même graphe cargo que searoute)
4. `scgraph` sur `oak_ridge_maritime`
5. graphe **enrichi voile** : portes Torres / Mentawai / antiméridien + décalage hors couloirs cargos

## Lancer

```bash
cd naviguide/naviguide-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-routing-ab.txt
python -m pytest tests/test_routing_ab_metrics.py tests/test_routing_ab_enriched.py tests/test_routing_ab_compare.py -q
python -m routing_ab.compare --out routing_ab/out
```

Ouvrir `routing_ab/out/index.html`.

`searoute` 1.6 est installé à la demande dans `.venv-ab-sr16/` (gitignoré). Pour l’éviter : `--no-sr16`.

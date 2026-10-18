# A/B bench — sea routing (Problem A)

Compare, **without changing** `GET /route`:

1. `searoute` 1.4.3 (production)
2. `searoute` 1.6.0 (isolated venv)
3. `scgraph` on `marnet` (same cargo graph as searoute)
4. `scgraph` on `oak_ridge_maritime`
5. **enriched sail** graph: Torres / Mentawai / antimeridian gates + offset off cargo corridors

## Run

```bash
cd naviguide/naviguide-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-routing-ab.txt
python -m pytest tests/test_routing_ab_metrics.py tests/test_routing_ab_enriched.py tests/test_routing_ab_compare.py -q
python -m routing_ab.compare --out routing_ab/out
```

Open `routing_ab/out/index.html`.

Automatic advice (gates already on the itinerary, KEEP/DROP, next gate, 20 nm):

```bash
python -m routing_ab.advise --out routing_ab/out
```

Open `routing_ab/out/advise.html`.

`searoute` 1.6 is installed on demand in `.venv-ab-sr16/` (gitignored). To skip it: `--no-sr16`.

# Stock officiel figé (lot RF11)

Date du gel : 2026-09-27 (UTC).
Archive : `server/tests/fixtures/official_store.tar.gz` (703104 octets).
Familles présentes : climo, film, ici, moments, plan_review.
Familles absentes du poste (restent « en préparation ») : eta.
Clés :

- `c4a0d2dc06cea61b:2026-05-15T08:00:00Z:2026-09-27`
- `c4a0d2dc06cea61b:2026-05-15T08:00:00Z:2026-09-27:rf5`

Commande pour régénérer (après un vrai calcul, si la route ou t0 change) :

```bash
cd naviguide-simulator
.venv/bin/python scripts/prepare_official_store.py
.venv/bin/python scripts/freeze_official_store.py
```

Le script lit `~/.cache/naviguide/voyage-store` (ou `NAVIGUIDE_OFFICIAL_STORE_DIR`).
Aucune donnée n'est inventée : on gèle le stock déjà calculé.

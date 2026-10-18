# Répétition générale de la séparation des dépôts

## Verdict (plan `bd696abb` / branche répétition `b93c083d`, `main` `e1e26e02`)

Date : 18 octobre 2026. Source filtrée : `main` `e1e26e02fb2e23e4620bf19133056e9945810e14` (merge #572 CI shardée, #574 film-front, #573 LT1, #567 Overpass). Plan exécuté : `cursor/plan-separation-depots-c3c8` à `bd696abb`. Aucun dépôt GitHub créé ou renommé. Aucun push hors des branches #554 et #555. Aucune action sur un serveur. Aucune fusion. Aucun test supprimé, ignoré par un marqueur nouveau, ni affaibli.

**Répétition GREEN : le split peut être lancé sur cet arbre.** Zéro échec de contrôle automatisé. Le journal live du voyage officiel peut rester à **1** ligne `moments` au split ; la migration copie quand même `naviguide.sqlite.bak-rekey-20261015`, tout `official-store/` et `moments-restore-20261018T033021Z/` ; la restauration live est le lot **MR1** après le split sur Contabo (section 8 et critère 9.14 du plan).

### Compteurs (dernière passe `bash scripts/repetition_split.sh`)

| Suite | Dépôt | Résultat |
|---|---|---|
| `pytest tests` (cwd `backend`, Mongo `bi_ci`, uvicorn `127.0.0.1:8001`) | Blue Intelligence | **1215 passed, 0 failed, 2 skipped** |
| `pytest` (cwd `naviguide-simulator`, `NAVIGUIDE_POSTE_API=http://127.0.0.1:9`) | NAVIGUIDE | **854 passed, 0 failed, 3 skipped** |
| `npm test` (`node --test`) | NAVIGUIDE | **929 pass, 0 fail, 0 skipped** |
| `npm test` (Jest) | Blue Intelligence | **40 tests, 0 fail** |
| `node --test src/utils/recetteAg.test.js` | NAVIGUIDE | **8 pass, 0 fail** |
| `infra/vps/ci/test_prod_jobs_busy.py` | les deux | **32 tests, OK** |
| `infra/vps/ci/test_simulator_deploy_manifest.py` | mono | **5 tests, OK** |
| Contrôles statiques (`check_split_coverage`, `generate_split_ci_diffs --check`, diffs plan = générateur, MR1 dans le plan) | les deux | **OK** |
| `bash -n` des scripts nommés par chaque `deploy-gate` (copies bi-work / ng-work) | les deux | OK |

Résumé script : **PASS 26, FAIL 0, AVERT 1** (rappel manuel Devpost Q13, pas un échec).

### CI shardée (#572)

Blue Intelligence après diff 6.6 : jobs `frontend`, `audit-tags`, `backend-pytest-shard` (×6), agrégateur requis **« API Blue Intelligence — pytest »** (`ci_pytest_gate.py`), `deploy-gate` avec `R_BACKEND`. NAVIGUIDE retire shards, agrégateur et chemins seed/Overpass. Génération : `python3 scripts/generate_split_ci_diffs.py --check`.

### Classeur (`main` `e1e26e02`)

```text
fichiers suivis : 1876
Blue Intelligence seul : 592
NAVIGUIDE seul : 1245
les deux : 36
exclus : 3
non classés : 0
lignes --emit bi : 98
lignes --emit ng : 118
```

### Migration données (MR1)

Le plan § 7–9 impose la copie intégrale de `voyage_data/` (dont `*.bak*` sqlite et toutes les clés `official-store/`), plus `moments-restore-20261018T033021Z/`, vérification SHA-256, et sur Contabo **1142** `moments` pour `berry-mappemonde-2026-officiel` dans `naviguide.sqlite.bak-rekey-20261015` (lecture seule). Nettoyage OVH **bloqué** tant que MR1 n'est pas vert et que le propriétaire n'a pas autorisé l'effacement.

### Bloquant

Aucun échec de suite sur cette VM. La vérification des **1142** moments sur Contabo se fait le jour J (fichiers OVH), pas dans cette répétition locale.

Les PR ouvertes hors de ce `main` restent une décision du propriétaire avant le filtre.

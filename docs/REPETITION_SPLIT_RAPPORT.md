# Répétition générale de la séparation des dépôts

## Verdict (plan `56fa0ef2`, `main` `14350b8c`)

Date : 17 octobre 2026, nuit. Source filtrée : `main` `14350b8c41a227addfb777437106732ab8903cbd` (merge #561). Plan exécuté : `cursor/plan-separation-depots-c3c8` à `56fa0ef2`. Aucun dépôt GitHub créé ou renommé. Aucun push hors des branches déjà ouvertes (#554, #555). Aucune action sur un serveur. Aucune fusion. Aucun test supprimé, ignoré par un marqueur nouveau, ni affaibli. Le split lui-même n'est pas lancé.

**Répétition GREEN : le split peut être lancé sur cet arbre.** Zéro échec, y compris les deux qui restaient sur `90ab81e5`. `test_localized_query_multilang` attend la requête famille anglaise pour l'ISO `XX` (décision du 17 octobre, commit `48e48120`). `test_serper_google_style_merged` passe sans `SERPER_API_KEY` : le correctif de `_add_serper_jobs` est celui de la #561, déjà sur `main`. La #563 est fermée, doublon de ce correctif.

### Compteurs

| Suite | Dépôt | Résultat |
|---|---|---|
| `pytest tests` (cwd `backend`, Mongo `bi_ci`, uvicorn `127.0.0.1:8001`, sans clé Serper) | Blue Intelligence | **1 214 passed, 0 failed, 2 skipped**, 334,35 s, exit 0 |
| `pytest` (cwd `naviguide-simulator`, `NAVIGUIDE_POSTE_API=http://127.0.0.1:9`) | NAVIGUIDE | **836 passed, 0 failed, 3 skipped**, 161,33 s, exit 0 |
| `npm test` (`node --test`) | NAVIGUIDE | **929 pass, 0 fail, 0 skipped**, 284 suites, 61,2 s |
| `npm test` (Jest) | Blue Intelligence | **10 suites, 40 tests, 0 fail** |
| `npm run build` (Vite) | NAVIGUIDE | OK, 2,01 s |
| `npm run build` (CRA) | Blue Intelligence | OK |
| `node --test src/utils/recetteAg.test.js` | NAVIGUIDE | **8 pass, 0 fail** |
| `pytest server/tests/test_wind_float16.py` | NAVIGUIDE | **2 passed** |
| `pytest -k test_naviguide_query_not_painted` | Blue Intelligence | **1 passed** (32 deselected) |
| `python3 infra/vps/ci/test_prod_jobs_busy.py` | les deux | **31 tests, OK** |
| `bash -n` des six scripts nommés par chaque `deploy-gate` | les deux | OK |
| `infra/agents/run_lots.py --dry-run --only C1` | NAVIGUIDE | exit 0 |

Les deux skips Blue Intelligence sont déjà écrits dans les tests : `tests/test_climatology.py::test_meteo_agent_cites_ibtracs_integer` (`langgraph` absent) et `tests/test_ner_unclos_osm.py::TestOsmBadges::test_validate_osm_status_progressing` (la tâche Overpass répond `running: false`, skip « tâche Overpass non active »). Le job de CI pose `POE_AUTO_REFRESH=0`. Le build CRA était sur le disque avant le chargement de `test_spa_static_head.py` : ce test est dans les 1 214 passed.

Les trois skips NAVIGUIDE sont les tests `poste` de `server/tests/test_film_discours.py` (lignes 456, 663 et 776), raison déjà écrite : « poste : stock du poste absent en CI ». Cette VM a `CI=true`. La répétition pose en plus `NAVIGUIDE_POSTE_API` vers `127.0.0.1:9`, où rien n'écoute. Le serveur de développement sur 8010 n'a pas été arrêté. Les assertions de ces trois tests n'ont pas changé.

## Alignement sur la CI backend (#561, sur `main`)

Mongo local de la VM (mongod 8.0, `127.0.0.1:27017`, base `bi_ci` seulement). Les scripts sont ceux du dépôt filtré (`backend/scripts/seed_ci_mongo.py`, `backend/scripts/enrich_ci_osm.py`).

- `backend/.env` : `MONGO_URL`, `DB_NAME=bi_ci`, `CORS_ORIGINS=*`, `SEARXNG_URL=http://127.0.0.1:8888`, aucune clé.
- `frontend/.env` : `REACT_APP_BACKEND_URL=http://127.0.0.1:8001`.
- Seed : `bi_ci: 4463 projets, 1169 ports, 285 ZEE dont 165 au statut ia`.
- Enrichissement : `round 1: 1169 validés, 0 échecs, 1166 depuis le cache, 5s`, puis `1169/1169 ports avec osm_confidence, 48 anomalies`. Cache repris de la passe précédente (`seed/ports_of_entry.geojson` inchangé, SHA-256 `5a8b24b1…`).
- uvicorn lancé depuis la copie filtrée, `GET /api/` répond 200.

## Diffs 6.6 de `ci.yml` (régénérés sur `14350b8c`)

Seul `ci.yml` a changé parmi les fichiers de la section 6.6 depuis `23be7ba8` (+108/−1, job `backend`). `git apply --check` accepte les huit diffs sur `14350b8c`. Les six autres (`deploy.yml`, `dependabot.yml`, `prepare-ssh.sh`, des deux côtés) s'appliquent encore tels quels. `plan_deploy.py` et `test_prod_jobs_busy.py` ne sont pas réécrits.

Blue Intelligence, jobs après le diff : `frontend`, `audit-tags`, `backend`, `deploy-gate`.

- Le job `backend` garde le nom « API Blue Intelligence — pytest » (Mongo de CI, seed, cache Overpass, `enrich_ci_osm.py`, uvicorn, `pytest tests`).
- `deploy-gate.needs` est `[frontend, audit-tags, backend]`. La variable `R_BACKEND` reste. La boucle ne cite plus `R_CHANGES`, `R_SIMULATOR`, `R_E2E`.
- Les jobs `changes`, `simulator` et `simulator-e2e` sortent. Le `bash -n` ne nomme plus `infra/vps/naviguide/deploy-naviguide.sh` ni `deploy-simulator.sh`.
- Le commentaire d'en-tête sur le pytest de l'API reste. La puce simulateur est remplacée par « Copie Blue Intelligence. Les jobs simulateur ne sont pas dans ce dépôt. »

NAVIGUIDE, jobs après le diff : `changes`, `simulator`, `simulator-e2e`, `deploy-gate`.

- Sortent : `frontend`, `audit-tags`, et le job `backend` entier (service Mongo, `frontend/.env`, `seed/ports_of_entry.geojson`, `backend/requirements.txt`, `scripts/seed_ci_mongo.py`, `scripts/enrich_ci_osm.py`, uvicorn, pytest).
- Sortent aussi `R_FRONTEND`, `R_AUDIT`, `R_BACKEND`, et le commentaire d'en-tête sur le pytest de l'API.
- `deploy-gate.needs` est `[changes, simulator, simulator-e2e]`.
- Le `bash -n` ne nomme plus `infra/vps/deploy-app.sh` ni `infra/vps/sync-public-nginx.sh`.
- L'en-tête devient : « Copie NAVIGUIDE. Frontend Blue Intelligence, audit des tags et le pytest de l'API Blue Intelligence ne sont pas dans ce dépôt. Le simulateur est testé si la PR le touche. »
- Après application, `ci.yml` ne contient plus `frontend/.env`, `seed/`, `backend/requirements.txt`, `scripts/seed_ci_mongo.py`, `scripts/enrich_ci_osm.py`, `scripts/audit_tags.py`, `uvicorn`.

Les deux `ci.yml` obtenus ont été relus dans les copies de travail. Les assertions ci-dessus tiennent sur les fichiers appliqués.

## Filtre sur `14350b8c`

```text
self-test : 64 cas tenus
fichiers suivis : 1852
Blue Intelligence seul : 578
NAVIGUIDE seul : 1236
les deux : 35
exclus : 3
non classés : 0
écarts d'historique : 0
--emit bi : exit 0, 91 lignes
--emit ng : exit 0, 116 lignes
--verify bi : 613 chemins tenus
--verify ng : 1271 chemins tenus
```

578 + 1 236 + 35 + 3 = 1 852. Les fichiers de la #561 (`backend/scripts/seed_ci_mongo.py`, `enrich_ci_osm.py`, leurs tests, `ci.yml`) tombent sous des préfixes déjà classés. Le classeur n'a pas été modifié.

`git ls-remote` du miroir local en fin de passe : **41** `refs/heads/*`, **562** `refs/pull/*/head`, **12** `refs/pull/*/merge`, **5** tags. Le clone filtré est `--bare --single-branch --branch main` du miroir local (pas de `git@github.com:…/Blue-Intelligence-Map.git`, ce nom est celui d'après le renommage). Il ne contient pas `refs/pull`. Les cinq tags `data-*` sont retirés du bare NAVIGUIDE avant `filter-repo`. Ils restent sur le bare Blue Intelligence.

Le premier commit de `backend/app/services/poe_pipeline.py` dans l'historique filtré est `9372925`, 2026-08-28 05:18:01 UTC. `backend/poe.py` et `memory/PRD.md` sont dans l'historique Blue Intelligence. `.env.example`, `memory/test_credentials.md` et `.emergent` n'y sont pas. L'historique NAVIGUIDE ne contient pas `Archives/Blue-Intelligence`, `backend`, `prototype_ai_studio`, `memory`, `.env.example`, `.emergent`.

`git clone --mirror` reste dans le plan : c'est la copie locale de l'archive. `git push --mirror` n'y est plus, ni dans la copie NAVIGUIDE du plan.

Balayage `-S` sans afficher de valeur : aucun `ghp_`, `github_pat_`, `sk-or-v1-`, ni bloc de clé privée. Les motifs `nvapi-`, `tvly-` et `AKIA` tombent dans des README, des tests ou des archives déjà suivis. Ce n'est pas un passage gitleaks. Plus gros fichier des copies de travail : 17,9 Mo (`backend/data/eez_french.geojson`). Aucun fichier à 50 Mo ou plus.

## Scripts joués

`--archive` est le miroir complet (`/tmp/split-rehearsal/mirror.git`). Les SHA `15e41b4e` et `bef9f0f3` y sont des commits. `scripts/split_post_filter.py self-check` : exit 0.

| Commande | Résultat |
|---|---|
| `shared` et `public-name`, rôles `bi` et `ng` | exit 0. Les quatre fichiers du commit 6.6 sont encore ceux du filtre au moment du `git apply`. Pas de `REVUE_21_SEPT.md_SOIR` corrompu. |
| quatre `git apply` par dépôt (section 6.6), dont les diffs `ci.yml` neufs | exit 0 |
| section 6.7 | 1 870 et 10 513 octets. `recetteAg.test.js` : 8 pass, 0 fail. |
| section 6.8 | 3 671 octets. `backend/tests/test_climatology.py` inchangé. `test_naviguide_query_not_painted` : 1 passed. |
| `film-discours` | exit 0. L'ancien chemin `docs/FILM_DISCOURS_ETAT_2026-09-28.md` n'est plus dans les fichiers contrôlés. La fixture est à côté du test. |
| `repo-paths` | exit 0. `compile()` tient. Le `grep` des chaînes déplacées est vide hors `repo_paths.py`. `--dry-run --only C1` : exit 0. |
| `cross-imports` | exit 0. `public/route.geojson` est un fichier de 57 033 octets. `climatology_common.py`, `climatology_wind.py` et les douze `wind-MM.npz` sont copiés. `test_wind_float16.py` : 2 passed. `npm test` : 929 pass. Les tests ne sont pas modifiés. |

Commits locaux, non poussés vers GitHub : Blue Intelligence `3ceb120` (CI) puis `9e03050` (copie `climatology_query.py`). NAVIGUIDE `891dfa7` (CI), `c324584` (6.7), `92099e6` (discours), `8bba4a8` (`repo_paths`), `d91843a` (route et vent).

## Push explicite, en local seulement

Dépôts nus locaux, avec un crochet qui refuse toute autre référence. Rien n'a été poussé vers un dépôt GitHub neuf.

Blue Intelligence : `refs/heads/main` (`9e03050`) puis les cinq tags `data-*`, un par un. `git ls-remote` ne montre que ces six références. `git push` de `refs/pull/1/head` : refusé, exit 1.

NAVIGUIDE : `refs/heads/main` seulement (`d91843a`). Pas de tag `data-*`. `git push` de `refs/pull/1/head` : refusé, exit 1.

## Bloquant

Aucun échec de suite. Aucune question produit en suspens sur un test rouge.

Les PR encore ouvertes au moment de cette passe ne sont pas dans `main` `14350b8c` : #564, #562, #557, #555, #554, #553, #549, #547, #546, #543, #542. Le plan les laisse à la décision du propriétaire (les fusionner avant le filtre, ou les laisser sur l'archive). Cette répétition ne les fusionne pas. #561 est sur `main`. #563 est fermée.

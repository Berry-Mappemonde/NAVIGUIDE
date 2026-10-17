# Répétition générale de la séparation des dépôts

## Verdict (plan `4e905e67`, `main` `90ab81e5`)

Date : 17 octobre 2026, soir. Source filtrée : `main` `90ab81e5a674921416263fbd73c3d05762a06b4c` (merge #559, après #556 et #560). Plan exécuté : `cursor/plan-separation-depots-c3c8` à `4e905e67`. Aucun dépôt GitHub créé ou renommé. Aucun push hors des branches de cette répétition (#554, #555, #562, #563). Aucune action sur un serveur. Aucune fusion. Aucun test supprimé, ignoré par un marqueur nouveau, ni affaibli.

**Le split passe. Zéro échec n'est pas atteint : il en reste deux, déjà rouges sur le monodépôt.** Rien d'autre ne échoue. Les 18 erreurs Mongo / URL ont disparu. Les tests OSM passent après l'enrichissement réel. Les tests poste ne dépendent plus du port 8010 dans cette exécution. Les sections 6.0, 6.4 et 6.5 ont été jouées par `scripts/split_post_filter.py`. Le plan ne contient plus de `git push --mirror`.

### Ce qui échoue encore

| Test | Où | Résultat mesuré | Décision |
|---|---|---|---|
| `backend/tests/test_ner_unclos_osm.py::TestUnclosUnit::test_localized_query_multilang` | ligne 118, `assert localized_query({"sov_iso2": "XX", "name": "Nowhere"}) is None` | La fonction renvoie `'official ports of entry yacht marina customs gazette list Nowhere'`. | **Test obsolète. Non modifié.** Le test date du 26 août 2026 (`59f00222`). Le 7 septembre 2026, `b6f4a855` remplace `return tpl.format(name=place) if tpl else None` par `return family_classic_query(place, lang)`. Cette fonction est la requête des polygones sans `if iso`. Revenir à `None` annulerait cette décision. **Question pour le propriétaire : faut-il attendre la requête famille anglaise, ou le cas ISO inconnu doit-il de nouveau renvoyer `None` ?** |
| `backend/tests/test_poe_v2_pipeline.py::TestFindSourcesTinyfish::test_serper_google_style_merged` | ligne 1045 | Sans `SERPER_API_KEY`, sur l'arbre filtré de `main` : 1 failed en 2,14 s (`serper_queries` vide). Avec la clé factice `ci-dummy-not-a-secret` : 1 passed en 1,95 s. Avec le correctif de la #563, sans clé : 1 passed en 1,94 s. | **Bug produit, pas un test obsolète.** Le test et la porte sont le même commit (`5c6e496e`). `_add_serper_jobs` sortait tout de suite quand la clé était vide, donc les requêtes n'étaient jamais construites. Le test remplace `_serper_search_safe`, pas la résolution de la clé. Correctif : les tirs sont toujours planifiés ; `_serper_search_safe` renvoie `[]` et n'appelle pas Serper si la clé est vide. Le test n'est pas modifié. PR : https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/563. La #561 contient le même changement de comportement. |

Aucun autre échec. Les skips déjà écrits dans le dépôt ne sont pas des échecs. Ils sont listés plus bas.

## Alignement sur la CI backend (PR #561)

La #561 (`cursor/backend-pytest-ci-f963`) existe. La suite a été lancée comme son job, sur le Mongo local de la VM (mongod 8.0, `127.0.0.1:27017`, base `bi_ci` seulement — pas l'OVH, pas Atlas) :

- `backend/.env` : `MONGO_URL`, `DB_NAME=bi_ci`, `CORS_ORIGINS=*`, `SEARXNG_URL=http://127.0.0.1:8888`, aucune clé.
- `frontend/.env` : `REACT_APP_BACKEND_URL=http://127.0.0.1:8001`.
- `seed_ci_mongo.py` de la #561 : 4 463 projets, 1 169 ports, 285 ZEE.
- `enrich_ci_osm.py` de la #561 : Overpass via `overpass_around` / `score_confidence`, puis le scan d'anomalies. Sortie : `1169/1169 ports avec osm_confidence, 48 anomalies`, 0 échec Overpass, 536 s au premier passage. Cache : `/tmp/split-rehearsal/r7/osm-ports.json`.
- uvicorn de la copie filtrée sur `127.0.0.1:8001`, `GET /api/` répond 200.
- `pytest tests -q --tb=line`, sans `SERPER_API_KEY`.

`pytest backend/tests` sur la copie Blue Intelligence, après les commits du plan : **2 failed, 1 199 passed, 2 skipped, 0 error**, en 337,55 s. Les trois tests OSM (`test_ports_expose_osm_properties`, `test_osm_checked_total_increasing`, `test_ports_all_osm_validated`) passent. Les 18 erreurs de la passe précédente (URL absente, Mongo vers `127.0.0.1:9`) ne se reproduisent pas.

Les 2 skipped de cette passe : `tests/test_climatology.py:545` (`langgraph` absent, skip déjà écrit) et `tests/test_spa_static_head.py` (le build CRA n'était pas encore sur le disque au chargement du module). Ce second test, relancé seul après le build : **1 passed**.

## Poste

`test_poste_stock_discours`, `test_poste_stock_anchor_positions` et le troisième test poste échouent si le code prend `http://127.0.0.1:8010` par défaut et qu'un serveur y répond. Le film servi (premier chapitre « Arrivée le 15 mai. ») ne satisfait pas l'assertion de discours. L'ancre Gibraltar mesurée sur ce serveur dépasse 30 nm. Les assertions n'ont pas été modifiées.

Cette VM a `CI=true`. Les trois tests prennent alors le skip déjà écrit (« stock du poste absent en CI »). En plus, la répétition pose `NAVIGUIDE_POSTE_API=http://127.0.0.1:9` (rien n'écoute). Le serveur de développement sur 8010 n'a pas été arrêté.

La fragilité est le défaut d'URL, pas l'assertion. PR : https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/562. Sans la variable, avec 8010 encore ouvert, le fichier entier sur cette branche : 18 passed, 3 skipped. Le nouveau test `test_poste_api_exige_une_variable` vérifie que le défaut ne sonde pas le port. Il n'est pas marqué `poste`.

`pytest` du serveur NAVIGUIDE, après les scripts : **836 passed, 3 skipped**, exit 0, en 100,02 s. Les trois skips sont ces tests poste.

## Filtre sur `90ab81e5`

```text
self-test : 64 cas tenus
fichiers suivis : 1848
Blue Intelligence seul : 574
NAVIGUIDE seul : 1236
les deux : 35
exclus : 3
non classés : 0
écarts d'historique : 0
--emit bi : exit 0, 91 lignes
--emit ng : exit 0, 116 lignes
--verify bi : 609 chemins tenus
--verify ng : 1271 chemins tenus
```

574 + 1 236 + 35 + 3 = 1 848. Les fichiers des #556, #559 et #560 tombent sous des préfixes déjà classés. Le classeur n'a pas été modifié.

`git ls-remote` en fin de passe : **40** `refs/heads/*`, **561** `refs/pull/*/head`, **12** `refs/pull/*/merge`, **5** tags. Le clone filtré est `--bare --single-branch --branch main` : il ne contient pas `refs/pull`. Les cinq tags `data-*` sont retirés du bare NAVIGUIDE avant `filter-repo`. Ils restent sur le bare Blue Intelligence.

Le premier commit de `backend/app/services/poe_pipeline.py` dans l'historique filtré est `9372925`, 2026-08-28 05:18:01 UTC.

`git clone --mirror` reste dans le plan : c'est la copie locale de l'archive, pas un envoi. `git push --mirror` n'y est plus.

## Scripts joués

Depuis le checkout du plan, `--archive` = le miroir complet (les SHA `15e41b4e` et `bef9f0f3` ne sont pas des ancêtres de `main` ; un clone `--single-branch` s'arrête sur `git show`).

| Commande | Résultat |
|---|---|
| `self-check` | exit 0 |
| `shared --role bi` et `shared --role ng` | exit 0 |
| `public-name --role bi` et `public-name --role ng` | exit 0. Pas de `REVUE_21_SEPT.md_SOIR` corrompu. La copie NAVIGUIDE du plan ne contient pas `git push --mirror`. `git clone --mirror` y reste. |
| quatre `git apply` Blue Intelligence et quatre NAVIGUIDE (section 6.6) | `--check` puis apply, exit 0, y compris après les scripts. Les diffs visent le `ci.yml` d'avant le job `backend` de la #561. Quand ce job sera sur `main`, il faudra les régénérer : Blue Intelligence garde le job, NAVIGUIDE le retire. |
| section 6.7 | 1 870 et 10 513 octets. `node --test` de `recetteAg.test.js` : 8 pass, 0 fail. |
| section 6.8 | 3 671 octets. `git diff --exit-code` sur `test_climatology.py` : vide. `pytest -k test_naviguide_query_not_painted` : 1 passed. |
| `film-discours` | exit 0. L'ancien chemin `docs/FILM_DISCOURS_ETAT_2026-09-28.md` n'est plus dans les quatre fichiers contrôlés. |
| `repo-paths` | exit 0. `compile()` tient. `run_lots.py --dry-run --only C1` : exit 0. |
| `cross-imports` | exit 0. Le lien `public/route.geojson` (57 033 octets, #558) est remplacé par le fichier. `climatology_common.py`, `climatology_wind.py` et les douze `wind-MM.npz` sont copiés (#560). `test_wind_float16.py` : 2 passed. `npm test` : **929 pass, 0 fail**. Les tests ne sont pas modifiés. `officialRouteSource.test.js` ne vérifie le lien que si `backend/data/route.geojson` est à côté du simulateur. |

`bash -n` des six scripts de chaque `deploy-gate` : OK. `test_prod_jobs_busy.py` : 31 passed des deux côtés.

`npm test` du frontend : 10 suites, 40 tests. `npm run build` CRA : OK. `npm run build` du simulateur : OK en 1,81 s.

## Push explicite, en local seulement

Dépôts nus locaux, avec un crochet qui refuse toute référence autre que celles du plan. Rien n'a été poussé vers un dépôt GitHub neuf.

Blue Intelligence : `refs/heads/main` puis les cinq tags `data-*`, un par un. `git ls-remote` ne montre que ces six références. `git push origin HEAD:refs/pull/1/head` : refusé, exit 1.

NAVIGUIDE : `refs/heads/main` seulement (tête `1ca8700`, qui inclut `cross-imports`). Pas de tag `data-*` dans cette copie. `git ls-remote` ne montre que `refs/heads/main`.

## Question

`test_localized_query_multilang`, ligne 118 : faut-il attendre la requête famille anglaise pour un ISO inconnu, ou ce cas doit-il de nouveau renvoyer `None` ?

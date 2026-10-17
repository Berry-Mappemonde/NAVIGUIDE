# Répétition générale de la séparation des dépôts

## Verdict sur le plan corrigé (PR #554)

Date de cette passe : 17 octobre 2026, soir. Source filtrée : `main` `6dabfb84078c16b1693e1069ae574a12ba366585` (16:03 −0400, merge #544). Commandes prises telles quelles dans `cursor/plan-separation-depots-c3c8` au commit `7a859ed8` (`docs/PLAN_SEPARATION_DEPOTS.md`, `scripts/check_split_coverage.py`). Aucun dépôt GitHub neuf. Aucune fusion. Push seulement vers des dépôts bare locaux.

**Le plan corrigé ne passe pas encore sur la tête de `main`.** Le classeur tient ses chiffres sur sa propre branche (1 835 fichiers, 575 / 1 222 / 35 / 3 / 0). Sur `main` actuel il s'arrête : `--emit` sort 1 et n'écrit aucun fichier de chemins. Le filtre qu'il décrirait une fois ce stop levé a été mesuré quand même (les 91 et 114 lignes sont identiques à celles de la branche #554). Quatre des cinq bloquants de la passe précédente sont levés ou écrits dans le plan. Deux restent : l'import `climatology_query`, et la CI, dont le texte n'est pas encore scindé.

### Les cinq bloquants

| Bloquant | État | Preuve sur les dépôts filtrés |
|---|---|---|
| `docs/recette/` | **Résolu** | 312 fichiers, tous dans NAVIGUIDE, aucun dans Blue Intelligence. `docs/recette/lot-rc56/01-glisse.jpg` (arrivé avec #544) est dans NAVIGUIDE. `--verify ng` exige `docs/recette/` et passe (1 274 chemins). |
| `infra/` entier dans Blue Intelligence | **Résolu** | `run_lots.py` et `infra/vps/naviguide/` sont seulement dans NAVIGUIDE. `deploy-app.sh` et `infra/vps/ci/README.md` sont seulement dans Blue Intelligence. Les deux dépôts gardent, comme le plan le dit, `infra/vps/ci/` (scripts), les deux nginx de climatologie, `infra/vps/README.md` et les quatre scripts `gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py`. |
| Import `climatology_query` | **Toujours présent** | `backend/tests/test_climatology.py` est dans Blue Intelligence, `naviguide/naviguide-api/climatology_query.py` est dans NAVIGUIDE. Pytest backend : `ModuleNotFoundError: No module named 'climatology_query'`. |
| CI scindée | **Partiellement résolu** | L'affectation des fichiers est faite : `weekly-data-build.yml` seulement Blue Intelligence, `zap-baseline.yml` et `.zap/rules.tsv` seulement NAVIGUIDE, `.gitignore` et `.nvmrc` dans les deux. `ci.yml`, `deploy.yml` et `dependabot.yml` sont copiés **octet pour octet** (mêmes SHA `8bd39472`, `3fe376d9`, `9cf8bab9`). La section 6 décrit la réécriture, elle ne la contient pas. Le `deploy-gate` du `ci.yml` copié échoue des deux côtés (scripts de l'autre produit absents). `npm test` du simulateur : 921 réussis, **1 échec**, parce que `recetteAg.test.js` lit `frontend/src/components/map/cycloneTracks.js`. |
| Données disque du simulateur | **Résolu dans le plan, non exécuté** | La #554 ne crée pas la base `naviguide_simulator`. La section 8 copie `voyage_data/naviguide.sqlite` et `official-store/` par `sqlite3 .backup` et `rsync`, vers `/home/naviguide/naviguide-data/`. Cette répétition n'a pas ouvert le VPS. |

### Commandes, et où elles s'arrêtent

```bash
python3 scripts/check_split_coverage.py --self-test
# self-test : 62 cas tenus

# sur la branche #554 (7a859ed8), dans un clone de cette branche
python3 scripts/check_split_coverage.py
# fichiers suivis : 1835
# Blue Intelligence seul : 575
# NAVIGUIDE seul : 1222
# les deux : 35
# exclus : 3
# non classés : 0
# lignes : 91 et 114
# écarts d'historique : 0

# sur main 6dabfb84, script copié mais non suivi
python3 scripts/check_split_coverage.py
# fichiers suivis : 1853
# Blue Intelligence seul : 574
# NAVIGUIDE seul : 1239
# les deux : 35
# exclus : 3
# non classés : 2
# écarts d'historique : 0
# exit 1
python3 scripts/check_split_coverage.py --emit bi > /tmp/bi-paths.txt   # exit 1, fichier vide
python3 scripts/check_split_coverage.py --emit ng > /tmp/ng-paths.txt   # exit 1, fichier vide
```

Les deux non classés, arrivés avec le merge #545, sont nommés en prose au § 4.9 (« vers NAVIGUIDE ») et absents des ensembles du script :

- `.cursor/rules/specs-suivent-l-interface.mdc`
- `docs/PLAN_BATCH_2026-10-16.md`

Les 91 et 114 lignes calculées par `emit()` sur `main` sont identiques à `--emit` sur la branche #554 (`diff` vide). Elles ont été passées à `git filter-repo --paths-from-file` sur deux clones `--bare --single-branch --branch main` de `6dabfb84`. Ce n'est pas la commande officielle : celle-ci s'arrête avant d'écrire le fichier. C'est le filtre que cette commande produirait si les deux fichiers avaient une classe, ou si l'on réutilisait les fichiers de chemins de la #554.

```bash
git clone --bare --single-branch --branch main --no-local <miroir-local-de-main> /tmp/bi-bare
git -C /tmp/bi-bare show-ref | grep refs/pull || echo "pas de refs/pull"
git -C /tmp/bi-bare tag -l
# data-2026-09-14 … data-2026-10-12
git -C /tmp/bi-bare filter-repo --paths-from-file /tmp/bi-paths.txt
# 1,41 s

git clone --bare --single-branch --branch main --no-local <miroir> /tmp/ng-bare
git -C /tmp/ng-bare tag -l | while read -r t; do git -C /tmp/ng-bare tag -d "$t"; done
git -C /tmp/ng-bare filter-repo --paths-from-file /tmp/ng-paths.txt
# 0,74 s
```

Le clone `--bare --single-branch` n'a pas de `refs/pull`. Le plan a raison de remplacer `--mirror` par ça. `--no-local` est ajouté seulement parce que la source est un miroir déjà sur la VM : filter-repo refuse un clone local qui n'est pas un vrai transfert. L'URL du plan (`git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git`) n'a pas été appelée.

`--verify bi` : 609 chemins tenus. `--verify ng` : 1 274 chemins tenus. `backend/poe.py` est dans l'historique Blue Intelligence (7 lignes). `memory/PRD.md` aussi (37). `.env.example`, `memory/test_credentials.md` et `.emergent` n'y sont pas. L'historique NAVIGUIDE ne contient ni `Archives/Blue-Intelligence/`, ni `backend/`, ni `prototype_ai_studio/`, ni `memory/`, ni `.env.example`, ni `.emergent`.

| | Fichiers sur la tête | Seulement lui | Dans les deux | Absents des deux |
|---|---:|---:|---:|---:|
| Blue Intelligence | 609 | 574 | 35 | |
| NAVIGUIDE | 1 274 | 1 239 | 35 | |
| `main` (1 853) | | | | **5** |

Les 5 absents : les 3 exclus voulus (`.gitconfig`, les deux doublons `Archives/naviguide-nova/docs/`) et les 2 non classés. Aucun autre fichier de `main` ne disparaît des deux côtés. `docs/recette/` : 0 et 312. Arbres identiques à `main` : `backend` `af7bc8d9`, `frontend` `150f459d`, `naviguide` `29aa977b`, `naviguide-simulator` `29cb2485`.

La tête Blue Intelligence filtrée est `89154e43`, « docs: update GenAI.works hackathon plan (#539) », pas le merge #544 : les commits #540 et #544 ne touchent que des chemins NAVIGUIDE. La tête NAVIGUIDE est `2eb25c6a`, merge #544. `git log` de `backend/app/services/poe_pipeline.py` commence à `9372925`, **2026-08-28 05:18:01 UTC**.

### Tests

| Suite | Dépôt | Résultat |
|---|---|---|
| `pytest` backend, `MONGO_URL=mongodb://127.0.0.1:9/none` | Blue Intelligence | **2 failed, 1 078 passed, 4 skipped, 18 errors, 651 s.** L'échec nouveau par rapport au mono-dépôt est `test_naviguide_query_not_painted`. L'autre, `test_serper_google_style_merged`, échoue déjà sur le mono-dépôt. Les 18 errors sont les tests qui exigent `REACT_APP_BACKEND_URL` ou un Mongo (port fermé). |
| `pytest` simulateur | NAVIGUIDE | **833 passed, 3 skipped, 104,78 s, exit 0.** |
| `npm test` puis `npm run build` dans `frontend/` | Blue Intelligence | **OK.** 10 suites, 40 tests, `build/index.html`. |
| `npm test` dans `naviguide-simulator/` | NAVIGUIDE | **KO.** 921 passés, 1 échoué, 4,4 s. `src/utils/recetteAg.test.js` (« I — atlas climatologie ») ouvre `../../../frontend/src/components/map/cycloneTracks.js`, absent de ce dépôt. |
| `npm run build` du simulateur | NAVIGUIDE | **OK.** `dist/index.html`, 876 ms. |
| `python3 scripts/audit_tags.py --geojson seed/projects.geojson seed/ports_of_entry.geojson` | Blue Intelligence | **OK** (rapport, pas un contrôle dur). |
| Le même `audit_tags.py` | NAVIGUIDE | **KO.** `scripts/` n'est pas dans ce dépôt. |
| `bash -n` du `deploy-gate` tel que `ci.yml` l'écrit | Blue Intelligence | **KO** sur `infra/vps/naviguide/deploy-naviguide.sh` et `deploy-simulator.sh` (absents). Les six scripts Blue Intelligence passent `bash -n`. `test_prod_jobs_busy.py` : 31 tests OK. |
| Le même `deploy-gate` | NAVIGUIDE | **KO** sur `deploy-app.sh` et `sync-public-nginx.sh` (absents). `deploy-naviguide.sh`, `deploy-simulator.sh`, `prepare-ssh.sh`, `rsync-to-vps.sh` passent `bash -n`. |

Le job `frontend` de la CI copiée part à chaque push NAVIGUIDE et n'a pas de dossier `frontend/`. Le job `simulator` a, lui, son dossier, son pytest et son build. La CI n'est donc pas exécutable telle que le filtre la laisse : il manque le commit de la section 6, et il manque de retirer du test simulateur la lecture du frontend Blue Intelligence.

### Push explicite

Contre un bare local dont le `pre-receive` refuse `refs/pull/*` :

```bash
git --git-dir=/tmp/bi-bare push <bare> refs/heads/main:refs/heads/main
git --git-dir=/tmp/bi-bare push <bare> refs/tags/data-2026-09-14:refs/tags/data-2026-09-14
# idem 09-21, 09-28, 10-05, 10-12
git --git-dir=/tmp/ng-bare push <bare> refs/heads/main:refs/heads/main
```

Les six push Blue Intelligence et le push NAVIGUIDE sortent **0**. Le bare Blue Intelligence ne contient que `refs/heads/main` et les cinq tags `data-*` (`data-2026-10-05` et `data-2026-10-12` pointent le même objet `348dfcd1`). Le bare NAVIGUIDE ne contient que `refs/heads/main`. Aucun tag `data-*` n'y restait après le `tag -d` du plan. Aucune `refs/pull`. Ce push n'inclut pas le commit d'adaptation de la section 6 : ce commit n'existe pas encore, la section est une liste, pas un diff.

### Corrections qui restent à écrire dans le plan

1. Mettre `.cursor/rules/specs-suivent-l-interface.mdc` et `docs/PLAN_BATCH_2026-10-16.md` dans les ensembles NAVIGUIDE du script (le § 4.9 le dit déjà). Sans ça, sur `main` du 17 octobre 16:03, `--emit` sort 1 et le filtre officiel ne démarre pas. Ces deux fichiers ne doivent pas disparaître des deux dépôts.
2. Remplacer la section 6 par les fichiers réécrits, ou par un diff applicable. Aujourd'hui `ci.yml`, `deploy.yml` et `dependabot.yml` partent identiques dans les deux dépôts, et le `deploy-gate` est rouge des deux côtés.
3. Retirer de `naviguide-simulator/src/utils/recetteAg.test.js` les quatre lectures de `frontend/src/components/map/cycloneTracks.js` et `useClimatologyLayer.js`, ou copier le contrat dans le simulateur. Sinon `npm test` du dépôt NAVIGUIDE a 1 échec sur 922.
4. Couper `backend/tests/test_climatology.py::test_naviguide_query_not_painted` de `naviguide/naviguide-api/climatology_query.py`. Le pytest backend du dépôt filtré a un échec de plus que le mono-dépôt.
5. Mettre à jour le décompte du § 5 (550 `refs/pull`, 42 branches, PR #529 à #551 encore ouvertes). Au moment de cette passe, `main` est `6dabfb84`, le miroir a 37 branches et 564 `refs/pull`, et plusieurs de ces numéros sont déjà fusionnés. Le clone `--bare --single-branch` ne les emporte pas : ce point ne bloque pas le push, il rend le texte faux.
6. Le premier commit de la section 6 (chemins `/home/ubuntu/blue-intelligence`, hôte Contabo, `BIM_REPO`) n'est pas produit par le filtre. Il reste à l'écrire avant le push réel. Cette répétition a poussé la tête filtrée, pas cette adaptation.

---

## Passe précédente : plan de `main`, avant la #554

Date de la répétition : 17 octobre 2026. Machine : copie locale dans la VM, sans dépôt GitHub créé, sans push des historiques filtrés, sans accès au VPS ni à Mongo.

**Verdict de cette passe-là : le split ne passe pas en l'état.** Le verdict qui compte est celui du plan corrigé, en tête de ce fichier.

Le code gardé par le filtre est intact : l'arbre `backend/` et l'arbre `frontend/` du dépôt Blue Intelligence sont identiques à `main`, l'arbre `naviguide-simulator/` du dépôt NAVIGUIDE aussi. Les builds frontend passent. Le pytest du simulateur passe (833 tests). Le pytest backend passe pour 1 078 tests. En revanche la commande du plan, exécutée telle qu'elle est écrite, fait disparaître 141 fichiers de `main` des deux dépôts à la fois, n'emporte aucun workflow, et `git push --mirror` embarque les `refs/pull/*` (le push est refusé par un remote qui imite le refus GitHub des refs cachées).

`main` de cette conclusion : `6dabfb84078c16b1693e1069ae574a12ba366585` (17 octobre 2026, 16:03 −0400, « Merge pull request #544 »). 1 429 commits sur `main`, 1 656 commits toutes refs, 37 branches, 564 refs `refs/pull/*`, 5 tags. Sont dedans les merges #550, #545, #529, #530, #533, #536, #534, #540 et #544, ainsi que le commit TV1 `c9e52822`. `docs/PLAN_SEPARATION_DEPOTS.md` n'a pas bougé depuis `563b79e4` (diff vide jusqu'à cette tête). Le plan parle encore de 1 249 commits et du remote `Blue-Intelligence-Map`. Ce nom répond `301` vers `https://github.com/Berry-Mappemonde/Blue-Intelligence`.

`main` a bougé pendant la répétition. Une passe a été mesurée sur `0ad99920` (#550), une sur `b0849889` (#534), une sur `208aff5b` (#540). Les tableaux ci-dessous sont la passe relancée après le merge #544, sur des clones frais dans `/tmp/split-rehearsal/r4/`. Les orphelins restent 141 puis 113 : les commits ajoutés sont des fichiers de `naviguide-simulator/` et de `docs/recette/`, plus la règle `.cursor` arrivée avec #545. Les branches encore ouvertes (lot RC57, branches `cursor/*`, dont celle de ce rapport) restent dans le miroir : `git push --mirror` les publierait.

## Bloquants

1. **141 fichiers de `main` ne sont dans aucun des deux dépôts** si l'on exécute le filtre tel qu'il est écrit. Ce sont `.github/` (5), `.gitignore`, `.nvmrc`, `.zap/rules.tsv`, `.cursor/` (20, dont `.cursor/rules/specs-suivent-l-interface.mdc` arrivé avec #545), `.gitconfig`, `.vscode/tasks.json` et `Archives/` (111). Le plan dit que `Archives/` et `.cursor/` vont à NAVIGUIDE, mais la phrase qui décrit le filtre NAVIGUIDE ne les passe pas à `--path`.
2. **Aucun workflow.** `.github/` est absent des deux commandes. Les deux dépôts naissent sans CI, sans déploiement, sans Dependabot, sans ZAP.
3. **`.gitignore` racine absent du dépôt Blue Intelligence.** `backend/` et `frontend/` n'ont pas de `.gitignore` à eux. Un `backend/.env` ne serait plus ignoré. Le plan affirme que `.env*` est déjà ignoré : cela devient faux dès que le fichier racine n'est plus là.
4. **`git push --mirror` ne passe pas** vers un remote qui refuse `refs/pull/*`, et il passe en embarquant ces refs vers un remote qui les accepte. Les quatre dépôts filtrés gardent les refs de pull (564 côté Blue Intelligence, 493 ou 564 côté NAVIGUIDE) et toutes les branches restantes (35 ou 37), pas seulement `main`. Parmi ces branches : le lot RC57 encore ouvert, et `cursor/repetition-split-7363`.
5. **Les workflows, si on les ajoute tels quels, ne sont pas cohérents.** Dans la copie corrigée, la CI NAVIGUIDE lance encore les jobs Blue Intelligence (`frontend`, `audit-tags`, `deploy-gate`) dont les chemins n'existent pas. `deploy.yml` décrit encore trois sites. `weekly-data-build.yml` dans NAVIGUIDE appelle `scripts/audit_tags.py`, absent. Dependabot pointe vers des dossiers absents des deux côtés.
6. **La liste NAVIGUIDE n'est pas exécutable.** Le plan ne donne pas de bloc `--path` pour NAVIGUIDE, seulement « `naviguide-simulator/`, `naviguide/`, `infra/vps/naviguide/`, et les docs du simulateur ». Cette répétition a traduit cela par les trois dossiers plus les deux fichiers nommés dans la même section (`docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md`, `docs/HACKATHON_DEVPOST_SOUMISSION.md`). Résultat : 390 fichiers de `docs/` restent seulement dans Blue Intelligence. `docs/recette/` (312 fichiers, 21,87 Mo) est cité par 157 fichiers du simulateur et n'est pas dans le dépôt NAVIGUIDE.
7. **Éléments mixtes au mauvais endroit.** `infra/` entier part dans Blue Intelligence, donc `infra/agents/` (lots, `run_lots.py`, juge VL) et `infra/vps/ci/` aussi. NAVIGUIDE n'a ni l'un ni l'autre. Les deux fichiers nginx de cache climatologie (`infra/vps/nginx-bi-climatology-cache.conf`, `infra/vps/nginx-snippet-bi-climatology.conf`) sont dans Blue Intelligence seulement. `deploy-simulator.sh`, lui, est dans les deux.
8. **Un import croisé casse un test backend.** `backend/tests/test_climatology.py::test_naviguide_query_not_painted` importe `climatology_query` depuis `naviguide/naviguide-api/`. Le test est vert sur le mono-dépôt, rouge après le filtre Blue Intelligence (`ModuleNotFoundError`).
9. **Les tags `data-*` ne doivent pas être poussés vers NAVIGUIDE.** Les cinq tags survivent au filtre, mais dans NAVIGUIDE leur arbre n'a plus les GeoJSON ni les `.npz`. `data-2026-10-05` et `data-2026-10-12` pointent déjà le même commit sur `main` (`f08b707d`) ; après réécriture ils pointent encore le même commit, propre à chaque dépôt.

Ajouter les cinq chemins oubliés (`.github/`, `.gitignore`, `.nvmrc`, `.zap/`, `.cursor/`) aux deux filtres ramène les orphelins de 141 à 113. Les 113 restants sont `Archives/` (111), `.gitconfig` et `.vscode/tasks.json`. Cet ajout ne scinde pas les workflows ni `infra/` ni les docs. Le split ne passe toujours pas.

10. **Les données du simulateur ne sont pas dans Mongo, et le filtre ne les transporte pas.** Sur le serveur OVH, la base `naviguide_simulator` n'existe pas. Le stock est sur disque : `voyage_data/naviguide.sqlite` et `voyage_data/official-store/`. Ces chemins sont ignorés par git (`naviguide-simulator/.gitignore`) et exclus du rsync de déploiement. Le § 6 du plan (« Mongo does not move ») vise la base Blue Intelligence (`poe_ports`), pas un dump de cette base absente. `infra/vps/README.md` décrit encore la création de l'utilisateur Mongo `naviguide_sim`. Suivre cette page créerait une base que la production n'utilise pas, et laisser le sqlite dans l'ancien checkout `~/blue-intelligence-map` ferait démarrer `~/naviguide` à vide.

## 1. Commandes exécutées

Outils : Git 2.43.0, Python 3.12.3, Node 24.22.0 (npm 11.19.1), `git-filter-repo` 2.47.0 (`git-filter-repo --version` affiche `a40bce548d2c`). `.nvmrc` contient `24`. Les builds ont utilisé ce Node 24, pas le Node 22 déjà présent sur la VM.

```bash
python3 -m pip install --user git-filter-repo
export PATH="$HOME/.local/bin:$PATH"

git clone --mirror https://github.com/Berry-Mappemonde/Blue-Intelligence.git /tmp/split-rehearsal/mirror.git
```

Quatre clones frais, chacun avec un seul remote `origin`, un seul pack et zéro objet libre, pour que `git-filter-repo` accepte de tourner sans `--force` (le plan n'en passe pas). `--no-local` est requis : filter-repo refuse un clone local qui n'est pas un vrai transfert.

```bash
git clone --mirror --no-local /tmp/split-rehearsal/mirror.git /tmp/split-rehearsal/bi-asis.git
git clone --mirror --no-local /tmp/split-rehearsal/mirror.git /tmp/split-rehearsal/ng-asis.git
git clone --mirror --no-local /tmp/split-rehearsal/mirror.git /tmp/split-rehearsal/bi-fix.git
git clone --mirror --no-local /tmp/split-rehearsal/mirror.git /tmp/split-rehearsal/ng-fix.git
```

Filtre Blue Intelligence, texte du plan (section 3) :

```bash
git -C /tmp/split-rehearsal/bi-asis.git filter-repo \
  --path backend/ --path frontend/ --path infra/ \
  --path docs/ --path scripts/ --path seed/ \
  --path README.md --path LICENSE --path LICENSE-MIT --path LICENSE-APACHE
```

Filtre NAVIGUIDE, lecture littérale de la même section. Le plan n'a pas de bloc de commande. « Les docs du simulateur » n'est pas un chemin : seuls les deux fichiers cités par leur nom ont été gardés.

```bash
git -C /tmp/split-rehearsal/ng-asis.git filter-repo \
  --path naviguide-simulator/ \
  --path naviguide/ \
  --path infra/vps/naviguide/ \
  --path docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md \
  --path docs/HACKATHON_DEVPOST_SOUMISSION.md
```

Deuxième passage, sur des clones frais (un filtre déjà appliqué a détruit les blobs : on ne peut pas « rajouter » un chemin ensuite). Les cinq chemins oubliés sont ajoutés aux deux commandes :

```bash
git -C /tmp/split-rehearsal/bi-fix.git filter-repo \
  --path backend/ --path frontend/ --path infra/ \
  --path docs/ --path scripts/ --path seed/ \
  --path README.md --path LICENSE --path LICENSE-MIT --path LICENSE-APACHE \
  --path .github/ --path .gitignore --path .nvmrc --path .zap/ --path .cursor/

git -C /tmp/split-rehearsal/ng-fix.git filter-repo \
  --path naviguide-simulator/ \
  --path naviguide/ \
  --path infra/vps/naviguide/ \
  --path docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md \
  --path docs/HACKATHON_DEVPOST_SOUMISSION.md \
  --path .github/ --path .gitignore --path .nvmrc --path .zap/ --path .cursor/
```

La passe qui sert de conclusion a d'abord fait `git -C /tmp/split-rehearsal/mirror.git remote update --prune`, puis quatre clones frais dans `/tmp/split-rehearsal/r4/`, mêmes commandes `filter-repo`. Durées : Blue Intelligence tel quel 1,71 s, NAVIGUIDE tel quel 0,58 s, Blue Intelligence corrigé 1,60 s, NAVIGUIDE corrigé 0,59 s. Chaque passage parse 1 656 commits. Le remote `origin` est retiré à la fin, comme le dit l'outil. Aucun `--force`.

Copies de travail pour les tests (branche `main` seulement) :

```bash
git clone --no-local --single-branch --branch main /tmp/split-rehearsal/bi-fix.git /tmp/split-rehearsal/work/bi-fix
git clone --no-local --single-branch --branch main /tmp/split-rehearsal/ng-fix.git /tmp/split-rehearsal/work/ng-fix
```

Piège opérationnel : sur un clone miroir, filter-repo imprime une liste `git branch -d` qui contient `main` et les 41 autres branches (« branches outside the refs/remotes/ hierarchy were not removed »). Un miroir n'a pas de `refs/remotes/`. Ces commandes effaceraient les branches que le filtre vient de réécrire. Il ne faut pas les lancer.

## 2. Tailles, commits, arbres

| Dépôt | Commits sur main | Commits toutes refs | Pack | Tête (message) | Branches | refs/pull | Tags |
|---|---:|---:|---:|---|---:|---:|---:|
| miroir | 1 429 | 1 656 | 283,41 Mio | `6dabfb84` merge #544 | 37 | 564 | 5 |
| BI tel quel | 981 | 1 119 | 270,90 Mio | `e0935409` merge #544 | 37 | 564 | 5 |
| NG tel quel | 743 | 855 | 11,39 Mio | `258f839a` merge #544 | 35 | 493 | 5 |
| BI corrigé | 1 023 | 1 161 | 270,97 Mio | `cdbe5423` merge #544 | 37 | 564 | 5 |
| NG corrigé | 809 | 927 | 11,47 Mio | `29347d89` merge #544 | 37 | 564 | 5 |

Les SHA de tête sont réécrits. Le message et la date du commit d'origine sont gardés. Les deux dépôts s'arrêtent sur le merge #544 : il touche `naviguide-simulator/` et un JPEG de `docs/recette/`. Le pack du miroir reste 283,41 Mio : les commits arrivés depuis le premier clone sont encore en objets libres, pas repackés. `du` du miroir : 285 Mo.

Arbres `git rev-parse main:<dossier>` :

| Dossier | Miroir | BI tel quel | BI corrigé | NG tel quel | NG corrigé |
|---|---|---|---|---|---|
| `backend` | `af7bc8d9` | `af7bc8d9` | `af7bc8d9` | absent | absent |
| `frontend` | `150f459d` | `150f459d` | `150f459d` | absent | absent |
| `naviguide` | `29aa977b` | absent | absent | `29aa977b` | `29aa977b` |
| `naviguide-simulator` | `29cb2485` | absent | absent | `29cb2485` | `29cb2485` |

`backend/`, `frontend/` et `naviguide/` ont les mêmes SHA d'arbre que sur le miroir `0ad99920`. Le pytest backend, le build `frontend/` et le build `naviguide-app` de la première passe couvrent donc cette tête. `naviguide-simulator/` a changé (`64da6062` sur #550, `29cb2485` sur #544) : le pytest et le build Vite du simulateur ont été relancés sur cette tête. Les octets sont les mêmes entre la copie telle quelle et la copie corrigée.

Preuve d'historique GenAI, sur le dépôt BI filtré : `git log --reverse -- backend/app/services/poe_pipeline.py` commence à `a9c2021`, **2026-08-28 05:18:01 UTC**, « refactor(backend): apply docs/ARCHITECTURE.md layout ». 52 commits touchent ce chemin. Sur le miroir, le même commit d'origine est `b4fae8c7`, même date. C'est avant septembre 2026. Le SHA change, la date non. `--follow` ne remonte pas plus tôt, ni sur le miroir ni après le filtre.

NAVIGUIDE tel quel perd deux branches devenues vides : `emergent` et `compatibilisation-python-openrouter`. Elles restent dans Blue Intelligence. Le passage corrigé les garde aussi côté NAVIGUIDE, parce que ces historiques touchent `.github/` ou `.cursor/`.

## 3. Fichiers de main : qui les garde

`main` contient **1 853** fichiers.

| | Fichiers | Seulement BI | Seulement NG | Dans les deux | Dans aucun |
|---|---:|---:|---:|---:|---:|
| Tel quel | BI 918, NG 807 | 905 | 794 | 13 | **141** |
| Chemins oubliés ajoutés | BI 946, NG 835 | 905 | 794 | 41 | **113** |

Répartition de `main` : `naviguide-simulator` 612, `docs` 392, `backend` 333, `naviguide` 182, `Archives` 111, `frontend` 105, `infra` 55, `scripts` 27, `.cursor` 20, `.github` 5, `seed` 2, puis un fichier chacun pour `.gitconfig`, `.gitignore`, `.nvmrc`, `.vscode`, `.zap`, `LICENSE`, `LICENSE-APACHE`, `LICENSE-MIT`, `README.md`.

Seulement dans Blue Intelligence (les deux passages) : `docs` 390, `backend` 333, `frontend` 105, `infra` 44 (les 11 fichiers de `infra/vps/naviguide/` sont dans les deux), `scripts` 27, `seed` 2, les trois licences et `README.md`.

Seulement dans NAVIGUIDE : `naviguide-simulator` 612, `naviguide` 182.

### Dans les deux dépôts, filtre tel quel (13)

- `docs/HACKATHON_DEVPOST_SOUMISSION.md`
- `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md`
- `infra/vps/naviguide/deploy-naviguide.sh`
- `infra/vps/naviguide/deploy-simulator.sh`
- `infra/vps/naviguide/naviguide-api.service`
- `infra/vps/naviguide/naviguide-orchestrator.service`
- `infra/vps/naviguide/naviguide-polar.service`
- `infra/vps/naviguide/naviguide-simulator.service`
- `infra/vps/naviguide/naviguide.env.example`
- `infra/vps/naviguide/nginx-naviguide.conf`
- `infra/vps/naviguide/nginx-simulator.conf`
- `infra/vps/naviguide/publish-simulator-from-mac.sh`
- `infra/vps/naviguide/simulator.env.example`

Le passage corrigé duplique en plus les 28 chemins ajoutés (`.github/` entier, `.gitignore`, `.nvmrc`, `.zap/rules.tsv`, `.cursor/` entier, 20 fichiers). Les copier des deux côtés évite qu'ils disparaissent. Cela ne les attribue pas au bon produit.

### Absents des deux dépôts, filtre tel quel (141)

- `.cursor/environment.json`
- `.cursor/hooks.json`
- `.cursor/hooks/simulator-ensure-dev.sh`
- `.cursor/hooks/simulator-mark-edited.sh`
- `.cursor/hooks/simulator-open-browser.sh`
- `.cursor/hooks/simulator-preview-ask.py`
- `.cursor/hooks/simulator-preview-ask.test.py`
- `.cursor/hooks/simulator-preview-lib.sh`
- `.cursor/hooks/simulator-request-open.sh`
- `.cursor/install.sh`
- `.cursor/preview.sh`
- `.cursor/rules/anti-regression-visuelle-simulateur.mdc`
- `.cursor/rules/base-de-donnees-vps.mdc`
- `.cursor/rules/environnement-utilisateur.mdc`
- `.cursor/rules/modeles-cursor-uniquement.mdc`
- `.cursor/rules/naviguide-simulator-preview.mdc`
- `.cursor/rules/pas-de-verification-video.mdc`
- `.cursor/rules/reparations-sur-github.mdc`
- `.cursor/rules/specs-suivent-l-interface.mdc`
- `.cursor/start.sh`
- `.gitconfig`
- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/weekly-data-build.yml`
- `.github/workflows/zap-baseline.yml`
- `.gitignore`
- `.nvmrc`
- `.vscode/tasks.json`
- `.zap/rules.tsv`
- `Archives/Blue-Intelligence/.cursor/plans/wayback_best_captures.md`
- `Archives/Blue-Intelligence/README-EN.txt`
- `Archives/Blue-Intelligence/README.ARCHIVE.md`
- `Archives/Blue-Intelligence/README.md`
- `Archives/Blue-Intelligence/README.txt`
- `Archives/Blue-Intelligence/cruiserswiki-structure.json`
- `Archives/Blue-Intelligence/data/DeepLinkCacheProjectsLists.json`
- `Archives/Blue-Intelligence/data/DeepLinkCacheProjectsPages.json`
- `Archives/Blue-Intelligence/data/MasterSeeds.json`
- `Archives/Blue-Intelligence/data/extraction-gold.example.json`
- `Archives/Blue-Intelligence/data/gshhg/README.md`
- `Archives/Blue-Intelligence/data/gshhg/gshhs_c_l1.b`
- `Archives/Blue-Intelligence/data/nautical-extraction-pack.default.json`
- `Archives/Blue-Intelligence/docs/BLUE_INTELLIGENCE_FIX.md`
- `Archives/Blue-Intelligence/docs/CRUISERSWIKI_SCRAPING.md`
- `Archives/Blue-Intelligence/docs/DEPLOIEMENT-VPS-OVH.md`
- `Archives/Blue-Intelligence/docs/EXTRACTION_PACK_WORKFLOW.md`
- `Archives/Blue-Intelligence/docs/VISION_EXTRACTION_NAUTICALS_HYBRIDE.md`
- `Archives/Blue-Intelligence/docs/WAYBACK_CDX.md`
- `Archives/Blue-Intelligence/docs/pitch-blue-intelligence.txt`
- `Archives/Blue-Intelligence/env.example`
- `Archives/Blue-Intelligence/env/wayback-cdx.public.env.example`
- `Archives/Blue-Intelligence/lib/cruiserswiki-fetch.ts`
- `Archives/Blue-Intelligence/lib/domainScoring.ts`
- `Archives/Blue-Intelligence/lib/gshhg-data.ts`
- `Archives/Blue-Intelligence/lib/gshhg-landmask.ts`
- `Archives/Blue-Intelligence/lib/nautical-extraction-pack.ts`
- `Archives/Blue-Intelligence/lib/semanticDedup.ts`
- `Archives/Blue-Intelligence/lib/wayback-phase2.ts`
- `Archives/Blue-Intelligence/lib/wayback-phase3-agent.ts`
- `Archives/Blue-Intelligence/lib/wayback-phase3.ts`
- `Archives/Blue-Intelligence/package.json`
- `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-MANUAL_EN.md`
- `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-MANUAL_FR.md`
- `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-README_EN.md`
- `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-README_FR.md`
- `Archives/Blue-Intelligence/scripts/cruiserswiki-structure-agent.ts`
- `Archives/Blue-Intelligence/scripts/download-gshhg.ts`
- `Archives/Blue-Intelligence/scripts/embed-gshhg.mjs`
- `Archives/Blue-Intelligence/scripts/export-wayback-wikitext-sample.ts`
- `Archives/Blue-Intelligence/scripts/semantic_similarity_test.ts`
- `Archives/Blue-Intelligence/scripts/validate-extraction-pack.ts`
- `Archives/Blue-Intelligence/scripts/verify-setup.ts`
- `Archives/Blue-Intelligence/server.ts`
- `Archives/Blue-Intelligence/src/App.tsx`
- `Archives/Blue-Intelligence/src/ErrorBoundary.tsx`
- `Archives/Blue-Intelligence/src/components/ConfirmCodeModal.tsx`
- `Archives/Blue-Intelligence/src/components/HelpTooltip.tsx`
- `Archives/Blue-Intelligence/src/components/SettingsSidebar.tsx`
- `Archives/Blue-Intelligence/src/config/defaults.ts`
- `Archives/Blue-Intelligence/src/config/useConfig.ts`
- `Archives/Blue-Intelligence/src/i18n/I18nContext.ts`
- `Archives/Blue-Intelligence/src/i18n/I18nProvider.tsx`
- `Archives/Blue-Intelligence/src/i18n/translations.ts`
- `Archives/Blue-Intelligence/src/i18n/useI18n.ts`
- `Archives/Blue-Intelligence/src/index.css`
- `Archives/Blue-Intelligence/src/main.tsx`
- `Archives/Blue-Intelligence/src/theme.ts`
- `Archives/Blue-Intelligence/src/utils/safeStorage.ts`
- `Archives/Blue-Intelligence/src/utils/tinyfishContext.ts`
- `Archives/Blue-Intelligence/tests/nautical-extraction-pack.test.ts`
- `Archives/Blue-Intelligence/types/tensorflow.d.ts`
- `Archives/README.md`
- `Archives/naviguide-navsecops/.ai-catalog-mapping.json`
- `Archives/naviguide-navsecops/.cursor/rules/naviguide-duo-yaml.mdc`
- `Archives/naviguide-navsecops/.dockerignore`
- `Archives/naviguide-navsecops/.gitlab-ci.yml`
- `Archives/naviguide-navsecops/Dockerfile`
- `Archives/naviguide-navsecops/README.md`
- `Archives/naviguide-navsecops/README.source.md`
- `Archives/naviguide-navsecops/agents/agent.yml`
- `Archives/naviguide-navsecops/agents/agent.yml.template`
- `Archives/naviguide-navsecops/docs/BERRY_MAPPEMONDE_ROUTE_DIGEST.md`
- `Archives/naviguide-navsecops/docs/CHAT_CONTEXT_SPEC.md`
- `Archives/naviguide-navsecops/docs/DATA.md`
- `Archives/naviguide-navsecops/docs/MANUAL.md`
- `Archives/naviguide-navsecops/docs/NAVSECOPS_PR_MATRIX.md`
- `Archives/naviguide-navsecops/docs/NAVSECOPS_TECHNICAL_ROADMAP.md`
- `Archives/naviguide-navsecops/docs/PLAN_DEV_NOVA.md`
- `Archives/naviguide-navsecops/docs/SETUP_NOVA_CREDITS.md`
- `Archives/naviguide-navsecops/flows/flow.yml`
- `Archives/naviguide-navsecops/flows/flow.yml.template`
- `Archives/naviguide-navsecops/frontend/App.jsx`
- `Archives/naviguide-navsecops/frontend/Sidebar.jsx`
- `Archives/naviguide-navsecops/frontend/buildChatContext.js`
- `Archives/naviguide-navsecops/naviguide-api/env.example`
- `Archives/naviguide-navsecops/naviguide-api/main.py`
- `Archives/naviguide-navsecops/naviguide-api/naviguide_duo.py`
- `Archives/naviguide-navsecops/naviguide-api/naviguide_navsecops_auth.py`
- `Archives/naviguide-navsecops/naviguide-api/naviguide_navsecops_pipeline.py`
- `Archives/naviguide-navsecops/naviguide-api/naviguide_navsecops_store.py`
- `Archives/naviguide-navsecops/naviguide-api/naviguide_navsecops_sync.py`
- `Archives/naviguide-navsecops/naviguide-api/requirements.txt`
- `Archives/naviguide-navsecops/naviguide_workspace/llm_utils.py`
- `Archives/naviguide-navsecops/polar_api/main.py`
- `Archives/naviguide-navsecops/proxy_server.py`
- `Archives/naviguide-navsecops/routes/berry-mappemonde-route-order.json`
- `Archives/naviguide-navsecops/routes/naviguide-berry-mappemonde.geojson`
- `Archives/naviguide-navsecops/scripts/diagnose_llm.py`
- `Archives/naviguide-navsecops/scripts/download_geodata.sh`
- `Archives/naviguide-navsecops/scripts/fetch_data.sh`
- `Archives/naviguide-navsecops/scripts/gitlab_mr_navsecops.sh`
- `Archives/naviguide-navsecops/scripts/gitlab_navsecops_chain.sh`
- `Archives/naviguide-navsecops/scripts/test_bedrock.py`
- `Archives/naviguide-navsecops/scripts/validate_berry_route_order.py`
- `Archives/naviguide-nova/README.md`
- `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md`
- `Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md`
- `Archives/naviguide-nova/llm/llm_utils.py`
- `Archives/naviguide-nova/orchestrator/graph.py`
- `Archives/naviguide-nova/orchestrator/nodes.py`

`Archives/` se répartit en `Archives/Blue-Intelligence/` (62), `Archives/naviguide-navsecops/` (42), `Archives/naviguide-nova/` (6) et `Archives/README.md` (1). Le complément du 17 octobre dit que `Archives/Blue-Intelligence/` ne doit pas partir dans NAVIGUIDE. Aujourd'hui il ne part nulle part.

Après ajout des cinq chemins, il reste **113** absents : les 111 de `Archives/`, plus `.gitconfig` et `.vscode/tasks.json`. `.gitconfig` ne contient qu'une identité (`user.email = github@emergent.sh`, `user.name = emergent-agent-e1`). Le plan a raison de ne pas le garder. Il faut le dire dans la commande, sinon il disparaît sans décision. `.vscode/tasks.json` n'est cité par aucune des deux listes.

### `.gitignore`

Sur `main`, les fichiers d'ignore suivis sont `.gitignore`, `infra/agents/.gitignore`, `naviguide-simulator/.gitignore`, `naviguide/.gitignore`. Pas de `.gitignore` dans `backend/` ni dans `frontend/`.

Le filtre tel quel :

- Blue Intelligence garde seulement `infra/agents/.gitignore` (journaux de lots, pas les `.env` ni `node_modules`).
- NAVIGUIDE garde les ignore du simulateur et de `naviguide/` (ils ignorent `node_modules/`, `dist/`, `.venv/`, `.env` dans ces dossiers). Il ne garde pas l'ignore racine.

Fichiers d'environnement suivis par git, valeurs non recopiées ici, seulement la forme :

- `naviguide/naviguide-app/.env` : trois clés `VITE_*`, les trois sont des URL.
- `naviguide/naviguide-app/.env.production` : cinq clés `VITE_*`, les cinq sont des URL.
- Les `.env.example` ont des valeurs vides, ou des libellés `your_copernicus_username`, `your_copernicus_password`, `sk-ant-...`, `PORT=8000`.

Ces deux `.env` suivis partent dans NAVIGUIDE. Ils restent suivis même quand l'ignore racine est ajouté : un ignore ne retire pas un fichier déjà dans l'historique.

## 4. Gros fichiers

Limite GitHub : rejet au-dessus de 100 Mo par blob, avertissement au-dessus de 50 Mo. Aucun LFS, pas de `.gitattributes`.

Sur toutes les refs du miroir, et encore dans les deux historiques Blue Intelligence : **14 blobs ≥ 10 Mo, 0 ≥ 50 Mo, 0 ≥ 100 Mo.** Les deux historiques NAVIGUIDE : **0 blob ≥ 10 Mo.**

| Taille | Chemin |
|---|---|
| 17.90 Mo | `backend/data/eez_french.geojson` |
| 17.62 Mo | `backend/data/eez_world_map.geojson` |
| 12.65 Mo | `backend/data/climatology/wind/wind-11.npz` |
| 12.59 Mo | `backend/data/climatology/wind/wind-09.npz` |
| 12.52 Mo | `backend/data/climatology/wind/wind-06.npz` |
| 12.38 Mo | `backend/data/climatology/wind/wind-01.npz` |
| 12.36 Mo | `backend/data/climatology/wind/wind-03.npz` |
| 12.35 Mo | `backend/data/climatology/wind/wind-12.npz` |
| 12.34 Mo | `backend/data/climatology/wind/wind-10.npz` |
| 12.34 Mo | `backend/data/climatology/wind/wind-05.npz` |
| 12.33 Mo | `backend/data/climatology/wind/wind-04.npz` |
| 12.32 Mo | `backend/data/climatology/wind/wind-02.npz` |
| 12.19 Mo | `backend/data/climatology/wind/wind-08.npz` |
| 12.18 Mo | `backend/data/climatology/wind/wind-07.npz` |

Le plus gros est `backend/data/eez_french.geojson` à 17,90 Mo. `eez_world_map.geojson` est à 17,62 Mo. Les douze `wind-*.npz` vont de 12,18 Mo à 12,65 Mo. Le filtre Blue Intelligence les garde (mêmes SHA de blob). Un push GitHub ne devrait pas être refusé pour la taille. Le filet LFS du plan reste inutile pour cette limite, sur cet historique.

Le tag `data-2026-10-12` du dépôt BI filtré contient encore `backend/data/eez_world_map.geojson` et `backend/data/climatology/wind/wind-01.npz`. Le même tag dans NAVIGUIDE tel quel ne les contient pas : l'arbre tagué est le sous-ensemble filtré (docs nommés, `infra/vps/naviguide/`, simulateur).

## 5. Workflows

Tel quel : les cinq fichiers `.github/dependabot.yml`, `ci.yml`, `deploy.yml`, `weekly-data-build.yml`, `zap-baseline.yml` sont absents des deux dépôts. `.nvmrc` aussi, donc un workflow recopié à la main et qui fait `node-version-file: .nvmrc` échoue à `setup-node`.

Passage corrigé : les cinq fichiers sont présents des deux côtés, byte pour byte ceux de `main` (le filtre ne réécrit pas leur contenu). Ils décrivent encore le mono-dépôt.

### `ci.yml` dans Blue Intelligence corrigé

Présents : `.nvmrc`, `frontend/package-lock.json`, `scripts/audit_tags.py`, les deux seeds, `infra/vps/ci/test_prod_jobs_busy.py`, et tous les scripts bash cités par `deploy-gate` (y compris `infra/vps/naviguide/deploy-*.sh`, parce que `infra/` entier est gardé).

Absents : `naviguide-simulator/package-lock.json`, `naviguide-simulator/server/requirements.txt`.

Conséquence : les jobs `frontend`, `audit-tags` et `deploy-gate` ont leurs fichiers. Les jobs `simulator` et `simulator-e2e` ne partent que si le diff touche `naviguide-simulator/**` ou `ci.yml`. Un edit de `ci.yml` les lance, puis `npm ci` échoue dans un dossier qui n'existe pas. Le job `frontend` ne lance pas le pytest backend. C'était déjà vrai sur `main`.

### `ci.yml` dans NAVIGUIDE corrigé

Présents : `.nvmrc`, le lock et les requirements du simulateur, `deploy-naviguide.sh`, `deploy-simulator.sh`.

Absents : `frontend/package-lock.json`, `scripts/audit_tags.py`, les deux seeds, `infra/vps/ci/test_prod_jobs_busy.py`, `infra/vps/deploy-app.sh`, `infra/vps/sync-public-nginx.sh`, `prepare-ssh.sh`, `rsync-to-vps.sh`, `apply-site.sh`, `apply-pending.sh`.

Conséquence : le job `frontend` part à chaque push (pas de filtre de chemins) et échoue. `audit-tags` échoue. `deploy-gate` échoue sur le premier `bash -n`. Les jobs simulateur peuvent passer, eux, parce que le dossier est là. **Copier `.github/` tel quel dans NAVIGUIDE rend la CI rouge.**

### `deploy.yml`

Les deux copies gardent le cron `*/20 * * * *`, les branches `main` et `recette`, les secrets `VPS_SSH_KEY` et `VPS_HOST`, et les trois jobs `blueintelligence.online`, `www.naviguide.fr`, `simulator.naviguide.fr`.

Blue Intelligence corrigé a `plan_deploy.py` et les scripts `infra/vps/ci/`, pas les `package-lock.json` de `naviguide/` ni du simulateur. Un déploiement « naviguide » ou « simulator » cassera au `npm ci`. NAVIGUIDE corrigé a les deux lockfiles naviguide, et n'a pas `plan_deploy.py` ni `prepare-ssh.sh` ni `rsync-to-vps.sh` : le job `plan` échoue avant tout déploiement.

`prepare-ssh.sh` écrit encore `REMOTE_APP=/home/ubuntu/blue-intelligence-map` (valeur par défaut). Le filtre ne change pas cette ligne.

### Les trois autres

- `weekly-data-build.yml` : cron lundi 05:00 UTC, `contents: write`, URL par défaut `https://blueintelligence.online`, release `data-<date>`. Dans Blue Intelligence corrigé, `scripts/audit_tags.py` est là. Dans NAVIGUIDE corrigé, ce script est absent : le job échoue, et s'il était réparé il publierait des releases de données BI dans le dépôt NAVIGUIDE.
- `zap-baseline.yml` : cible `https://simulator.naviguide.fr`, règles `.zap/rules.tsv`. Les deux sont présents dans NAVIGUIDE corrigé : le workflow est cohérent là. Les deux sont aussi présents dans Blue Intelligence corrigé : un dépôt BI lancerait le scan du simulateur et ouvrirait l'issue « ZAP baseline — simulateur ».
- `dependabot.yml` : npm `/naviguide-simulator`, npm `/frontend`, pip `/naviguide-simulator/server`, github-actions `/`. Pas de pip `/backend`. Dans chaque dépôt corrigé, au moins un `directory` n'existe pas.

## 6. Imports cassés et références croisées

Il n'y a pas d'`import naviguide` dans le Python de `backend/`. La cassure réelle est un `sys.path` vers l'autre produit.

`backend/tests/test_climatology.py` (fonction `test_naviguide_query_not_painted`) ajoute `naviguide/naviguide-api` au `sys.path` et fait `import climatology_query`. Le module est `naviguide/naviguide-api/climatology_query.py`. `naviguide/naviguide-api/main.py` importe le même module.

- Mono-dépôt, même venv, mêmes variables (`MONGO_URL` sur `127.0.0.1:9`) : le test climatologie **passe**.
- Dépôt BI filtré : **échoue**, `ModuleNotFoundError: No module named 'climatology_query'`.

`infra/agents/run_lots.py` est dans le dépôt BI. Il pose `DEFAULT_REPO = "https://github.com/Berry-Mappemonde/Blue-Intelligence"` et `sim = ROOT / "naviguide-simulator"`. Ce dossier n'existe pas dans le dépôt BI (`ensure-dev.sh` absent). Il n'existe pas non plus `infra/agents/` dans le dépôt NAVIGUIDE. Les scripts qui importent `run_lots` (`loop.py`, `watchdog.py`, `review_agent.py`, `plan_corrections.py`, `devpost_answers.py`, `test_vl_film_review.py`) sont donc dans le dépôt qui n'a pas le simulateur.

Fichiers de code du dépôt BI (tel quel) qui citent `naviguide-simulator`, hors markdown : `infra/agents/run_lots.py` (14), `infra/vps/naviguide/deploy-simulator.sh` (12), `publish-simulator-from-mac.sh` (6), `devpost_code_share.py` (3), `review_agent.py` (3), `rsync-to-vps.sh` (3), `apply-site.sh` (2), `plan_deploy.py` (2), `naviguide-simulator.service` (2), `nginx-simulator.conf` (2), `vl_film_review.py` (1), `test_vl_film_review.py` (1). Le markdown en ajoute beaucoup, surtout `docs/LOTS_ORDRE_ET_PROMPTS.md` (200 occurrences). Ces docs sont dans BI, pas dans NG.

`BIM_REPO` apparaît dans `gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py`, tous sous `infra/agents/`, donc seulement dans BI.

Côté NAVIGUIDE, l'appel HTTP vers Blue Intelligence est voulu. `BI_API_URL` est dans `server/bi_proxy.py`, `server/main.py`, `server/ici_engine.py`, `server/amp_nogo.py`, `server/climatology_atlas.py`, `server/tests/conftest.py`, `server/tests/test_ici_engine.py`, et `naviguide/naviguide-app/src/components/MaritimeLayers.jsx` (`VITE_BI_API_URL`). Le défaut reste `https://blueintelligence.online/api`. `conftest.py` force `http://127.0.0.1:9/api` pendant pytest.

`docs/recette` est cité par 157 fichiers du simulateur, et par `naviguide-simulator/scripts/amp-route.py`. Le dossier `docs/recette/` (312 fichiers, 21,87 Mo) est dans le dépôt BI seulement.

`docs/HACKATHON_DEVPOST_SOUMISSION.md`, seul fichier markdown de NAVIGUIDE qui contient `Berry-Mappemonde/Blue-Intelligence` (3 fois), part avec NAVIGUIDE. Après création d'un nouveau dépôt qui reprend ce nom, cette URL montrera Blue Intelligence.

`recette.blueintelligence.online` dans le dépôt BI : `infra/agents/run_lots.py`, `GROK_BOT_ROUTINE.md`, `GROK_BOT_DEVPOST.md`.

Les deux conf nginx de cache climatologie sont absentes du dépôt NAVIGUIDE et présentes dans Blue Intelligence. `infra/vps/naviguide/deploy-simulator.sh` est dans les deux.

## 7. Chemins codés en dur

Le filtre ne réécrit aucune ligne. Comptage `git grep -F` sur `main` filtré, fichiers de code (py, js, jsx, mjs, sh, yml, service, conf, json).

Dépôt BI tel quel :

| Motif | Fichiers de code | Occurrences de code |
|---|---:|---:|
| `blue-intelligence-map` | 18 | 31 |
| `/home/ubuntu` | 10 | 23 |
| `Berry-Mappemonde/Blue-Intelligence` | 9 | 11 |
| `Blue-Intelligence-Map` | 1 | 1 |

Fichiers de code avec `blue-intelligence-map` : `infra/vps/nginx-blue-intelligence.conf` (4), `sync-public-nginx.sh` (3), `blue-intelligence.service` (2), `deploy-app.sh` (2), les quatre units `infra/vps/naviguide/*.service` (2 chacun), `deploy-naviguide.sh` (2), `deploy-simulator.sh` (2), `apply-pending.sh`, `apply-site.sh`, `prepare-ssh.sh`, `prod_jobs_busy.py`, `rsync-to-vps.sh`, `nginx-naviguide.conf`, `nginx-simulator.conf`, `publish-simulator-from-mac.sh`.

Dépôt NG tel quel : `blue-intelligence-map` dans 9 fichiers de code (15 occurrences), tous sous `infra/vps/naviguide/` (les quatre units, les deux `deploy-*.sh`, les deux nginx, `publish-simulator-from-mac.sh`). `/home/ubuntu` dans les quatre units et `publish-simulator-from-mac.sh`.

`Blue-Intelligence-Map` reste surtout dans la documentation (21 fichiers, 33 occurrences côté BI, dont 1 seule dans du code).

## 8. Motifs de secrets

Recherche `git log -S` sur toutes les refs réécrites, sans afficher les valeurs, puis `git grep` sur `main` filtré pour distinguer l'historique de l'arbre actuel.

Sur `main` des dépôts filtrés, aujourd'hui :

- `nvapi-` : trois tests backend (`nvapi-test`, `nvapi-secret`, `nvapi-ui`, `nvapi-x`) et, côté NAVIGUIDE, `naviguide/README.md` (`nvapi-...`) plus `test_story_cascade.py`. Ce sont des gabarits.
- `tvly-` : trois tests du simulateur, suffixes courts (longueur 9), gabarits.
- `mongodb+srv://` : `backend/scripts/sync_backend_env.py` et deux tests. Hôtes `cluster0.abc.mongodb.net`, `cluster.mongodb.net`, `x.mongodb.net`, utilisateur `u`.
- `hf_` : 11 fichiers backend, tous des identifiants de code (`hf_channel`, `hf_ok`, `hf_part`, …). Aucun jeton long.
- `sk-or-v1-`, `ghp_`, `github_pat_`, `AKIA`, `AIza`, `BEGIN PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY` : **0** sur `main` filtré.

Dans l'historique seulement : `github_pat_` a deux commits qui touchent `scripts/gmail/test_classer.py`. Ce fichier n'est plus dans `main`. La valeur n'a pas été affichée. `nvapi-` apparaît aussi dans d'anciennes versions de `README.md` qui ne l'ont plus. Cette recherche par motifs n'est pas un scanner dédié.

## 9. Tests et builds

Les arbres de code étant identiques entre « tel quel » et « corrigé », une exécution par produit couvre les deux copies. Rien n'a été pointé vers le VPS, Atlas, ni `blueintelligence.online`. `MONGO_URL` des tests backend vaut `mongodb://127.0.0.1:9/none` (port fermé). Les clés d'API ont été retirées de l'environnement. Aucun `backend/.env` n'a été copié (il n'est pas dans git).

### Frontend

| Build | Commande | Résultat |
|---|---|---|
| Blue Intelligence `frontend/` | Node 24.22.0, `npm ci`, `npm run build` | **OK**, `build/index.html` présent. « Compiled successfully. » Avertissement Node `DEP0176` (`fs.F_OK`) pendant le build. |
| Simulateur (tête #544, arbre `29cb2485`) | Node 24.22.0, `npm ci`, `npm run build` (`vite build`) | **OK**, `dist/index.html` présent, build en 572 ms. Avertissement de chunk > 500 ko. |
| Ancien site `naviguide/naviguide-app` | `npm ci`, `npm run build` | **OK**, `dist/index.html` présent, build Vite en 4,75 s. Avertissement de chunk > 500 ko (`maplibre`, 1 023 ko). |

### Pytest simulateur (dépôt NAVIGUIDE)

```bash
python3 -m venv /tmp/split-rehearsal/venv-sim
pip install -r naviguide-simulator/server/requirements.txt
cd naviguide-simulator && python -m pytest -q --tb=line
```

Relancé sur la copie NAVIGUIDE corrigée de `6dabfb84` (le simulateur a changé depuis #550 : lots DC, ED, VS, CH, RC56, TV1).

**OK. 833 passed, 3 skipped, 20 warnings, 84,90 s, exit 0.** Les warnings sont des `DeprecationWarning` FastAPI (`on_event`) et shapely (`ops.transform`), plus un `UserWarning` d'operation id dupliquée sur `polar_chat_removed`. `conftest.py` envoie `BI_API_URL` vers `127.0.0.1:9` et retire les clés LLM. La passe #550 donnait 794 passed sur l'arbre `64da6062`.

### Pytest backend (dépôt Blue Intelligence)

```bash
python3 -m venv /tmp/split-rehearsal/venv-bi
pip install -r backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd backend
export MONGO_URL='mongodb://127.0.0.1:9/none' DB_NAME='none'
python -m pytest -q --tb=line --continue-on-collection-errors
```

`pip` exit 0, y compris `torch==2.13.0+cpu`, `spacy==3.8.16`, `sentence-transformers==6.0.0`.

L'arbre `backend/` est `af7bc8d9` sur #550 et sur #540. Ce pytest n'a pas été relancé : le résultat ci-dessous est celui de la première passe, et il vaut pour cette tête.

**KO global, exit 1. 1 078 passed, 4 skipped, 2 failed, 18 errors, 539,67 s.**

Les 8 erreurs de collecte viennent de tests qui exigent `REACT_APP_BACKEND_URL` (lu dans `frontend/.env`, absent du clone) et qui parleraient à une API déjà lancée : `test_blue_intelligence.py`, `test_import_and_regression.py`, `test_ml_jobs.py`, `test_ner_unclos_osm.py`, `test_poe_api.py`, `test_refactor_core.py`, `test_serp_ml_resume.py`, `test_zoom_and_new_features.py`. Sans cette variable, ils s'arrêtent avant tout HTTP. C'est le comportement voulu ici : ne pas appeler la production.

10 erreurs de setup sont des `ServerSelectionTimeoutError` vers `127.0.0.1:9` (connexion refusée) : trois tests de `test_listing_control.py`, trois de `test_p0_survive.py`, un de `test_poe_multirun.py`, deux de `test_poe_v2_pipeline.py` (`TestRunReport`), un de `test_run_fingerprint.py`. Ils voulaient un Mongo. Ils ont trouvé le port fermé, pas la base du VPS.

Deux échecs :

- `tests/test_climatology.py::test_naviguide_query_not_painted` — **causé par le filtre**. `ModuleNotFoundError: No module named 'climatology_query'`. Le même test, relancé dans `/workspace/backend` (mono-dépôt, même venv), **passe**.
- `tests/test_poe_v2_pipeline.py::TestFindSourcesTinyfish::test_serper_google_style_merged` — `assert False` sur les requêtes Serper. Le même test **échoue aussi** sur le mono-dépôt (`1 failed, 1 passed` pour la paire). L'arbre `backend/` est celui de `main`. Cet échec n'est pas introduit par le split.

Le pytest backend n'est pas dans `ci.yml`. Une CI qui lancerait tout le dossier `backend/tests` sans tri serait rouge, filtre ou pas, à cause des tests qui exigent une API et un Mongo.

## 10. Simulation de push

Pour chaque dépôt filtré, deux dépôts bare locaux vides. L'un a un hook `pre-receive` qui refuse tout le lot si une ref `refs/pull/*` est dans le push, et qui imprime `deny updating a hidden ref`. L'autre accepte tout. Aucun remote GitHub n'a été ajouté. Rien n'a été poussé vers GitHub à part, plus tard, la branche de cette PR.

Commandes, pour chaque dépôt :

```bash
git init --bare /tmp/split-rehearsal/push/<nom>-hook.git
git init --bare /tmp/split-rehearsal/push/<nom>-open.git
# hook copié dans <nom>-hook.git/hooks/pre-receive

git -C <dépôt-filtré> push --dry-run --mirror <open>
git -C <dépôt-filtré> push --mirror <hook>          # doit échouer
git -C <dépôt-filtré> push <hook> refs/heads/main:refs/heads/main
git -C <dépôt-filtré> push <hook> 'refs/tags/*:refs/tags/*'
git -C <dépôt-filtré> push --mirror <open>          # doit embarquer les refs/pull
```

| Dépôt | dry-run --mirror | push --mirror vers le hook | main + tags vers le hook | push --mirror vers le bare ouvert |
|---|---|---|---|---|
| BI tel quel | exit 0, 37 branches, 5 tags, **564 pull** | **exit 1**, 564 refs cachées rejetées, **0 ref écrite** | **exit 0 + exit 0**, seulement `main` et les 5 tags | **exit 0**, heads=37 tags=5 pull=564 |
| NG tel quel | exit 0, 35 branches, 5 tags, **493 pull** | **exit 1**, 493 rejetées, 0 ref | **exit 0 + exit 0** | **exit 0**, heads=35 tags=5 pull=493 |
| BI corrigé | exit 0, 37 / 5 / **564** | **exit 1**, 0 ref | **exit 0 + exit 0** | **exit 0**, 37 / 5 / 564 |
| NG corrigé | exit 0, 37 / 5 / **564** | **exit 1**, 0 ref | **exit 0 + exit 0** | **exit 0**, 37 / 5 / 564 |

Le message du hook, extrait du push BI tel quel sur cette tête : `remote: error: deny updating a hidden ref: refs/pull/1/head` (et les 563 autres), puis `remote: error: 564 hidden ref(s) rejected; push aborted`, puis `pre-receive hook declined` pour chaque branche, y compris `main`. Comme le hook rejette le lot entier, aucune branche n'est créée. Côté GitHub le refus des refs cachées a la même forme (`deny updating a hidden ref`) ; selon que le serveur rejette le lot ou seulement ces refs, `git push --mirror` se termine en erreur. Dans les deux lectures, la commande du plan ne dépose pas un dépôt propre : soit elle échoue, soit elle publie 37 branches (35 côté NAVIGUIDE tel quel) et des centaines de `refs/pull/*`. Les branches déjà mergées ont été effacées du remote ; il reste 37 branches, dont `fix/lot-rc57-dc3-spec-par-jambe` et cette branche de rapport.

La séquence qui passe, contre le même hook :

```bash
git push <remote> refs/heads/main:refs/heads/main
git push <remote> 'refs/tags/*:refs/tags/*'
```

Après coup, le bare du hook ne contient que `refs/heads/main` et `refs/tags/data-2026-09-14`, `data-2026-09-21`, `data-2026-09-28`, `data-2026-10-05`, `data-2026-10-12`. Pour NAVIGUIDE, ces tags `data-*` ne sont pas les archives de données (section 4). Les pousser quand même crée des tags au mauvais contenu.

`git push --dry-run --mirror` liste les branches par leur nom court (`* [new branch] main -> main`) et les pulls par leur ref complète (`* [new reference] refs/pull/1/head -> refs/pull/1/head`).

## 11. Données du simulateur

Le plan ne nomme pas `naviguide_simulator`. Sa phrase « Mongo does not move. Same mongod, same data » et le contrôle `poe_ports` parlent de la base Blue Intelligence. Rien, dans le filtre, ne déplace un dump Mongo.

Le code, lui, a deux histoires. `naviguide-simulator/server/pearl_store.py` ouvre un SQLite, `voyage_dir()/naviguide.sqlite`, et écrit : « Pas de MongoDB côté simulateur : Mongo reste la base de Blue Intelligence. » `official_store.py` garde le nom de base `naviguide_simulator` et l'utilise seulement quand `SIMULATOR_MONGO_URL` est défini ; sinon les six familles (moments, film, eta, climo, ici, plan_review) vont dans `server/voyage_data/official-store/`, ou dans `NAVIGUIDE_OFFICIAL_STORE_DIR`. `infra/vps/README.md` documente encore la création de cette base et de l'utilisateur `naviguide_sim`, et propose `NAVIGUIDE_VOYAGE_DIR=/var/lib/naviguide/voyage_data` sans que le lot ait copié les fichiers.

Indication du porteur, 17 octobre 2026, pour cette répétition : sur l'OVH, la base `naviguide_simulator` n'existe pas. Les données du simulateur sont dans le SQLite `voyage_data/naviguide.sqlite` et dans `voyage_data/official-store/`, sur disque. Aucun de ces fichiers n'est suivi par git (vérifié : `git ls-tree` de `main` ne contient ni `naviguide.sqlite`, ni `official-store`, ni `voyage_data`). Cette répétition n'a pas ouvert de session sur le VPS et n'a pas listé le disque du serveur.

Conséquence pour le split : changer le dossier git de `~/blue-intelligence-map` vers `~/naviguide` ne transporte pas ce stock. Si les fichiers sont dans le checkout actuel (`naviguide-simulator/server/voyage_data/`), il faut les copier à la main. S'ils sont déjà hors checkout via les variables d'environnement, les units du nouveau dépôt doivent garder les mêmes chemins. Un `mongodump` de `naviguide_simulator` ne récupérerait rien.

## 12. Corrections à écrire dans le plan

1. Remplacer la phrase NAVIGUIDE par une commande `--path` complète. Y mettre une liste de docs, pas « les docs du simulateur ». Au minimum, tout ce que le code lit : `docs/recette/`, `docs/LOTS_ORDRE_ET_PROMPTS.md`, `docs/REGLES_WORKFLOW_AGENT.md`, `docs/WORKFLOW_INDUSTRIEL.md`, les `docs/PLAN_*` du simulateur, `docs/HACKATHON_DEVPOST_SOUMISSION.md`, `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md`.
2. Garder `.gitignore` et `.nvmrc` dans les deux dépôts. Sans l'ignore racine, le dépôt Blue Intelligence n'ignore ni `backend/.env`, ni `frontend/node_modules`, ni `build/`.
3. Garder `.github/`, puis le scinder avant le premier push qui déclenche Actions. Blue Intelligence : jobs `frontend`, `audit-tags`, un `deploy-gate` limité à ses scripts, `weekly-data-build.yml`, Dependabot `frontend` et `backend`. NAVIGUIDE : jobs `simulator` et `simulator-e2e`, déploiement `naviguide` et `simulator`, `zap-baseline.yml`, Dependabot simulateur. Retirer de chaque copie les jobs de l'autre produit. Retirer la branche `recette` du `deploy.yml` Blue Intelligence.
4. Mettre `.zap/` dans NAVIGUIDE seulement. Le workflow vise `simulator.naviguide.fr`.
5. Découper `.cursor/` par fichier. Blue Intelligence : `environment.json`, `install.sh`, `start.sh`, `preview.sh`, et les règles Mongo, modèles, vidéo, réparations, environnement. NAVIGUIDE : `hooks.json`, les scripts `simulator-*`, les règles anti-régression et preview. Les règles communes (environnement, modèles, pas de vidéo) sont à copier, pas à laisser d'un seul côté par oubli.
6. Découper `Archives/`. `Archives/Blue-Intelligence/` (62 fichiers) vers Blue Intelligence. `Archives/naviguide-navsecops/`, `Archives/naviguide-nova/` et `Archives/README.md` vers NAVIGUIDE. Tant que ce n'est pas dans une commande, les 111 fichiers disparaissent des deux.
7. Ne pas garder `.gitconfig`. Décider de `.vscode/tasks.json` dans la commande, pour qu'il ne soit pas un oubli.
8. Ne pas donner `infra/` entier à Blue Intelligence sans liste. `infra/agents/` va avec NAVIGUIDE (ou une copie réduite des scripts génériques `gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py` dans chaque dépôt, avec `BIM_REPO` changé). `infra/vps/ci/` doit être scindé : chaque dépôt n'a que les scripts de ses sites. Les deux fichiers `nginx-bi-climatology-*.conf` doivent être dans le dépôt qui déploie le simulateur, et rester disponibles pour les vhosts Blue Intelligence.
9. Remplacer `git push --mirror` par le push de `refs/heads/main` et des tags voulus. Ne pas pousser les 37 branches restantes (`emergent`, `cursor/*`, branches de lots ouverts). Ne pousser les tags `data-*` que vers le dépôt Blue Intelligence.
10. Dire explicitement de ne pas lancer les `git branch -d` imprimés par filter-repo sur un clone `--mirror`.
11. Partir d'un clone miroir frais par dépôt. Un second `filter-repo` sur le résultat ne récupère pas les chemins déjà détruits.
12. Corriger l'import `climatology_query` : soit le test backend embarque une copie ou un extrait, soit il ne dépend plus de `naviguide/naviguide-api/`. Tant que cette ligne reste, le pytest backend du dépôt BI a un échec de plus que le mono-dépôt.
13. Mettre à jour les chiffres du plan : remote `Berry-Mappemonde/Blue-Intelligence` (l'ancien nom renvoie un 301), 1 429 commits sur `main` au 17 octobre 2026, 16:03 −0400 (`6dabfb84`, merge #544). `git-filter-repo` 2.47.0 s'installe par `pip install --user` et n'est pas sur le `PATH` par défaut.
14. Les chemins `/home/ubuntu/blue-intelligence-map` dans les units et les scripts ne sont pas modifiés par le filtre. Le § 6 du plan les traite au moment du VPS. Ils sont encore dans les deux dépôts après le filtre. `DEFAULT_REPO` et l'URL dans `docs/HACKATHON_DEVPOST_SOUMISSION.md` pointent encore le mono-dépôt : après le renommage, cette URL sera le nouveau dépôt Blue Intelligence.
15. Le pytest backend hermétique (1 078 verts ici) peut devenir un job de CI. Les 8 fichiers qui lisent `REACT_APP_BACKEND_URL` et les tests qui ouvrent Mongo restent hors de ce job tant qu'ils n'ont pas de double hors ligne.
16. Ne pas migrer une base Mongo `naviguide_simulator` : elle n'existe pas sur l'OVH. Le § 6 du plan (« Mongo does not move », compteur `poe_ports`) concerne la base Blue Intelligence, sur le même `mongod`. Le stock du simulateur est sur disque, hors git : `voyage_data/naviguide.sqlite` (perles, cache ERA5, `pearl_store.py` dit explicitement qu'il n'y a pas de Mongo côté simulateur) et `voyage_data/official-store/` (voyage officiel ; `official_store.py` n'ouvre Mongo que si `SIMULATOR_MONGO_URL` est posé, sinon `DiskBackend`). `naviguide-simulator/.gitignore` ignore `server/voyage_data/`. `infra/vps/ci/rsync-to-vps.sh` et `publish-simulator-from-mac.sh` excluent ce dossier. Au basculement des checkouts, copier ce répertoire vers le nouvel arbre, ou laisser `NAVIGUIDE_VOYAGE_DIR` et `NAVIGUIDE_OFFICIAL_STORE_DIR` pointer le dossier déjà hors checkout. Ne pas exécuter le `db.createUser` de `infra/vps/README.md` (base `naviguide_simulator`, utilisateur `naviguide_sim`) dans le cadre du split : cette page décrit une base que le serveur n'a pas.

## 13. Ce qui n'a pas été fait

Aucun dépôt GitHub créé. Aucun push des historiques filtrés. Aucun renommage. Aucun merge. Aucun appel au VPS, à Mongo, ni à l'API de production. Le disque du serveur n'a pas été listé : l'emplacement `voyage_data/` est celui indiqué par le porteur et par le code, pas une vérification SSH. Le hook de la section 10 est une imitation locale du refus des refs cachées, pas une réponse réelle de GitHub. Les tests Playwright, le job `deploy-gate` et les workflows Actions n'ont pas été lancés sur un runner : leur cohérence est déduite des chemins présents ou absents. Le scan de secrets est un `git log -S` et un `git grep`, pas gitleaks.

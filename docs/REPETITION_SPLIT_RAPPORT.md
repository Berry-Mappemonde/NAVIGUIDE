# Répétition générale de la séparation des dépôts

Date de la répétition : 17 octobre 2026. Machine : copie locale dans la VM, sans dépôt GitHub créé, sans push des historiques filtrés, sans accès au VPS ni à Mongo.

**Verdict : le split ne passe pas en l'état.**

Le code gardé par le filtre est intact : l'arbre `backend/` et l'arbre `frontend/` du dépôt Blue Intelligence sont identiques à `main`, l'arbre `naviguide-simulator/` du dépôt NAVIGUIDE aussi. Les builds frontend passent. Le pytest du simulateur passe. Le pytest backend passe pour 1 078 tests. En revanche la commande du plan, exécutée telle qu'elle est écrite, fait disparaître 140 fichiers de `main` des deux dépôts à la fois, n'emporte aucun workflow, et `git push --mirror` embarque les `refs/pull/*` (le push est refusé par un remote qui imite le refus GitHub des refs cachées).

`main` lu pour le clone miroir : `0ad999207649e5c8f7dd699185477ce2151e7abb` (17 octobre 2026, 15:21 −0400, « Merge pull request #550 »). 1 403 commits sur `main`, 1 643 commits toutes refs, 42 branches, 566 refs `refs/pull/*`, 5 tags. Le fichier `docs/PLAN_SEPARATION_DEPOTS.md` est identique à celui du commit `563b79e4` (diff vide). Le plan parle encore de 1 249 commits et du remote `Blue-Intelligence-Map`. Ce nom répond `301` vers `https://github.com/Berry-Mappemonde/Blue-Intelligence`.

Après la fin des filtres, `origin/main` a avancé jusqu’à `a7d56b541c0afa9f018defa03b6bc629d8736eb6` (merge #536). Le diff `0ad99920..a7d56b54` ne touche pas `docs/PLAN_SEPARATION_DEPOTS.md`. Il ajoute 27 fichiers : un règle `.cursor/rules/specs-suivent-l-interface.mdc` (orpheline avec le filtre tel quel, dupliquée si l’on ajoute `.cursor/` aux deux), quatre fichiers sous `docs/` (ils resteraient seulement dans Blue Intelligence, dont des JPEG de `docs/recette/`) et le reste sous `naviguide-simulator/` (lots DC1–DC3, ED1, film). Les chiffres de fichiers, de pytest et de builds ci-dessous sont ceux du miroir `0ad99920`. Le verdict ne change pas : ces ajouts suivent les mêmes trous.

## Bloquants

1. **140 fichiers de `main` ne sont dans aucun des deux dépôts** si l'on exécute le filtre tel qu'il est écrit. Ce sont `.github/` (5), `.gitignore`, `.nvmrc`, `.zap/rules.tsv`, `.cursor/` (19), `.gitconfig`, `.vscode/tasks.json` et `Archives/` (111). Le plan dit que `Archives/` et `.cursor/` vont à NAVIGUIDE, mais la phrase qui décrit le filtre NAVIGUIDE ne les passe pas à `--path`.
2. **Aucun workflow.** `.github/` est absent des deux commandes. Les deux dépôts naissent sans CI, sans déploiement, sans Dependabot, sans ZAP.
3. **`.gitignore` racine absent du dépôt Blue Intelligence.** `backend/` et `frontend/` n'ont pas de `.gitignore` à eux. Un `backend/.env` ne serait plus ignoré. Le plan affirme que `.env*` est déjà ignoré : cela devient faux dès que le fichier racine n'est plus là.
4. **`git push --mirror` ne passe pas** vers un remote qui refuse `refs/pull/*`, et il passe en embarquant ces refs vers un remote qui les accepte. Les quatre dépôts filtrés gardent les refs de pull (566 côté Blue Intelligence, 495 ou 566 côté NAVIGUIDE) et toutes les branches restantes (40 ou 42), pas seulement `main`.
5. **Les workflows, si on les ajoute tels quels, ne sont pas cohérents.** Dans la copie corrigée, la CI NAVIGUIDE lance encore les jobs Blue Intelligence (`frontend`, `audit-tags`, `deploy-gate`) dont les chemins n'existent pas. `deploy.yml` décrit encore trois sites. `weekly-data-build.yml` dans NAVIGUIDE appelle `scripts/audit_tags.py`, absent. Dependabot pointe vers des dossiers absents des deux côtés.
6. **La liste NAVIGUIDE n'est pas exécutable.** Le plan ne donne pas de bloc `--path` pour NAVIGUIDE, seulement « `naviguide-simulator/`, `naviguide/`, `infra/vps/naviguide/`, et les docs du simulateur ». Cette répétition a traduit cela par les trois dossiers plus les deux fichiers nommés dans la même section (`docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md`, `docs/HACKATHON_DEVPOST_SOUMISSION.md`). Résultat : 380 fichiers de `docs/` restent seulement dans Blue Intelligence. `docs/recette/` (303 fichiers, 23 Mo) est cité par 149 specs du simulateur et n'est pas dans le dépôt NAVIGUIDE.
7. **Éléments mixtes au mauvais endroit.** `infra/` entier part dans Blue Intelligence, donc `infra/agents/` (lots, `run_lots.py`, juge VL) et `infra/vps/ci/` aussi. NAVIGUIDE n'a ni l'un ni l'autre. Les deux fichiers nginx de cache climatologie (`infra/vps/nginx-bi-climatology-cache.conf`, `infra/vps/nginx-snippet-bi-climatology.conf`) sont dans Blue Intelligence seulement. `deploy-simulator.sh`, lui, est dans les deux.
8. **Un import croisé casse un test backend.** `backend/tests/test_climatology.py::test_naviguide_query_not_painted` importe `climatology_query` depuis `naviguide/naviguide-api/`. Le test est vert sur le mono-dépôt, rouge après le filtre Blue Intelligence (`ModuleNotFoundError`).
9. **Les tags `data-*` ne doivent pas être poussés vers NAVIGUIDE.** Les cinq tags survivent au filtre, mais dans NAVIGUIDE leur arbre n'a plus les GeoJSON ni les `.npz`. `data-2026-10-05` et `data-2026-10-12` pointent déjà le même commit sur `main` (`f08b707d`) ; après réécriture ils pointent encore le même commit, propre à chaque dépôt.

Ajouter les cinq chemins oubliés (`.github/`, `.gitignore`, `.nvmrc`, `.zap/`, `.cursor/`) aux deux filtres ramène les orphelins de 140 à 113. Les 113 restants sont `Archives/` (111), `.gitconfig` et `.vscode/tasks.json`. Cet ajout ne scinde pas les workflows ni `infra/` ni les docs. Le split ne passe toujours pas.

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

Durées annoncées par filter-repo : Blue Intelligence tel quel 1,65 s, NAVIGUIDE tel quel 0,56 s, Blue Intelligence corrigé 1,55 s, NAVIGUIDE corrigé 0,61 s. Chaque passage parse 1 643 commits. Le remote `origin` est retiré à la fin, comme le dit l'outil. Aucun `--force`.

Copies de travail pour les tests (branche `main` seulement) :

```bash
git clone --no-local --single-branch --branch main /tmp/split-rehearsal/bi-fix.git /tmp/split-rehearsal/work/bi-fix
git clone --no-local --single-branch --branch main /tmp/split-rehearsal/ng-fix.git /tmp/split-rehearsal/work/ng-fix
```

Piège opérationnel : sur un clone miroir, filter-repo imprime une liste `git branch -d` qui contient `main` et les 41 autres branches (« branches outside the refs/remotes/ hierarchy were not removed »). Un miroir n'a pas de `refs/remotes/`. Ces commandes effaceraient les branches que le filtre vient de réécrire. Il ne faut pas les lancer.

## 2. Tailles, commits, arbres

| Dépôt | Commits sur main | Commits toutes refs | Pack | Tête (message) | Branches | refs/pull | Tags |
|---|---:|---:|---:|---|---:|---:|---:|
| miroir | 1 403 | 1 643 | 283,41 Mio | `0ad99920` merge #550 | 42 | 566 | 5 |
| BI tel quel | 957 | 1 107 | 270,83 Mio | `bff79652` merge #550 | 42 | 566 | 5 |
| NG tel quel | 719 | 849 | 11,42 Mio | `00a85869` merge #538 | 40 | 495 | 5 |
| BI corrigé | 999 | 1 149 | 270,91 Mio | `44728243` merge #550 | 42 | 566 | 5 |
| NG corrigé | 784 | 922 | 11,50 Mio | `e89bfa72` merge #538 | 42 | 566 | 5 |

Les SHA de tête sont réécrits. Le message et la date du commit d'origine sont gardés. NAVIGUIDE s'arrête au merge #538 (17 octobre, 08:19 −0400, docs hackathon) parce que les commits suivants sur `main` (#539 docs GenAI, #550 `infra/agents`) ne touchent aucun chemin gardé par le filtre NAVIGUIDE. L'arbre du simulateur, lui, est le même.

Arbres `git rev-parse main:<dossier>` :

| Dossier | Miroir | BI tel quel | BI corrigé | NG tel quel | NG corrigé |
|---|---|---|---|---|---|
| `backend` | `af7bc8d9` | `af7bc8d9` | `af7bc8d9` | absent | absent |
| `frontend` | `150f459d` | `150f459d` | `150f459d` | absent | absent |
| `naviguide-simulator` | `64da6062` | absent | absent | `64da6062` | `64da6062` |

Les tests et les builds ont donc été lancés une fois par produit, sur la copie corrigée. Le résultat vaut pour la copie telle quelle : les octets des dossiers testés sont les mêmes.

Preuve d'historique GenAI, sur le dépôt BI filtré : `git log --reverse -- backend/app/services/poe_pipeline.py` commence à `a9c2021`, **2026-08-28 05:18:01 UTC**, « refactor(backend): apply docs/ARCHITECTURE.md layout ». 52 commits touchent ce chemin. Sur le miroir, le même commit d'origine est `b4fae8c7`, même date. C'est avant septembre 2026. Le SHA change, la date non. `--follow` ne remonte pas plus tôt, ni sur le miroir ni après le filtre.

NAVIGUIDE tel quel perd deux branches devenues vides : `emergent` et `compatibilisation-python-openrouter`. Elles restent dans Blue Intelligence. Le passage corrigé les garde aussi côté NAVIGUIDE, parce que ces historiques touchent `.github/` ou `.cursor/`.

## 3. Fichiers de main : qui les garde

`main` contient **1 834** fichiers.

| | Fichiers | Seulement BI | Seulement NG | Dans les deux | Dans aucun |
|---|---:|---:|---:|---:|---:|
| Tel quel | BI 908, NG 799 | 895 | 786 | 13 | **140** |
| Chemins oubliés ajoutés | BI 935, NG 826 | 895 | 786 | 40 | **113** |

Répartition de `main` : `naviguide-simulator` 604, `docs` 382, `backend` 333, `naviguide` 182, `Archives` 111, `frontend` 105, `infra` 55, `scripts` 27, `.cursor` 19, `.github` 5, `seed` 2, puis un fichier chacun pour `.gitconfig`, `.gitignore`, `.nvmrc`, `.vscode`, `.zap`, `LICENSE`, `LICENSE-APACHE`, `LICENSE-MIT`, `README.md`.

Seulement dans Blue Intelligence (les deux passages) : `docs` 380, `backend` 333, `frontend` 105, `infra` 44 (les 11 fichiers de `infra/vps/naviguide/` sont dans les deux), `scripts` 27, `seed` 2, les trois licences et `README.md`.

Seulement dans NAVIGUIDE : `naviguide-simulator` 604, `naviguide` 182.

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

Le passage corrigé duplique en plus les 27 chemins ajoutés (`.github/` entier, `.gitignore`, `.nvmrc`, `.zap/rules.tsv`, `.cursor/` entier). Les copier des deux côtés évite qu'ils disparaissent. Cela ne les attribue pas au bon produit.

### Absents des deux dépôts, filtre tel quel (140)

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

`docs/recette` est cité par 149 fichiers du simulateur (specs e2e, 162 occurrences), et par `naviguide-simulator/scripts/amp-route.py`. Le dossier `docs/recette/` (303 fichiers, 23 Mo) est dans le dépôt BI seulement.

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
| Simulateur | `npm ci`, `npm run build` (`vite build`) | **OK**, `dist/index.html` présent. |
| Ancien site `naviguide/naviguide-app` | `npm ci`, `npm run build` | **OK**, `dist/index.html` présent, build Vite en 4,75 s. Avertissement de chunk > 500 ko (`maplibre`, 1 023 ko). |

### Pytest simulateur (dépôt NAVIGUIDE)

```bash
python3 -m venv /tmp/split-rehearsal/venv-sim
pip install -r naviguide-simulator/server/requirements.txt
cd naviguide-simulator && python -m pytest -q --tb=line
```

**OK. 794 passed, 3 skipped, 20 warnings, 80,25 s, exit 0.** Les warnings sont des `DeprecationWarning` FastAPI (`on_event`) et shapely (`ops.transform`). `conftest.py` envoie `BI_API_URL` vers `127.0.0.1:9` et retire les clés LLM.

### Pytest backend (dépôt Blue Intelligence)

```bash
python3 -m venv /tmp/split-rehearsal/venv-bi
pip install -r backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd backend
export MONGO_URL='mongodb://127.0.0.1:9/none' DB_NAME='none'
python -m pytest -q --tb=line --continue-on-collection-errors
```

`pip` exit 0, y compris `torch==2.13.0+cpu`, `spacy==3.8.16`, `sentence-transformers==6.0.0`.

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
| BI tel quel | exit 0, 42 branches, 5 tags, **566 pull** | **exit 1**, 566 refs cachées rejetées, **0 ref écrite** | **exit 0 + exit 0**, seulement `main` et les 5 tags | **exit 0**, heads=42 tags=5 pull=566 |
| NG tel quel | exit 0, 40 branches, 5 tags, **495 pull** | **exit 1**, 495 rejetées, 0 ref | **exit 0 + exit 0** | **exit 0**, heads=40 tags=5 pull=495 |
| BI corrigé | exit 0, 42 / 5 / **566** | **exit 1**, 0 ref | **exit 0 + exit 0** | **exit 0**, 42 / 5 / 566 |
| NG corrigé | exit 0, 42 / 5 / **566** | **exit 1**, 0 ref | **exit 0 + exit 0** | **exit 0**, 42 / 5 / 566 |

Le message du hook, extrait du push BI tel quel : `remote: error: deny updating a hidden ref: refs/pull/1/head` (et les 565 autres), puis `remote: error: 566 hidden ref(s) rejected; push aborted`, puis `pre-receive hook declined` pour chaque branche, y compris `main`. Comme le hook rejette le lot entier, aucune branche n'est créée. Côté GitHub le refus des refs cachées a la même forme (`deny updating a hidden ref`) ; selon que le serveur rejette le lot ou seulement ces refs, `git push --mirror` se termine en erreur. Dans les deux lectures, la commande du plan ne dépose pas un dépôt propre : soit elle échoue, soit elle publie 42 branches et des centaines de `refs/pull/*`.

La séquence qui passe, contre le même hook :

```bash
git push <remote> refs/heads/main:refs/heads/main
git push <remote> 'refs/tags/*:refs/tags/*'
```

Après coup, le bare du hook ne contient que `refs/heads/main` et `refs/tags/data-2026-09-14`, `data-2026-09-21`, `data-2026-09-28`, `data-2026-10-05`, `data-2026-10-12`. Pour NAVIGUIDE, ces tags `data-*` ne sont pas les archives de données (section 4). Les pousser quand même crée des tags au mauvais contenu.

`git push --dry-run --mirror` liste les branches par leur nom court (`* [new branch] main -> main`) et les pulls par leur ref complète (`* [new reference] refs/pull/1/head -> refs/pull/1/head`).

## 11. Corrections à écrire dans le plan

1. Remplacer la phrase NAVIGUIDE par une commande `--path` complète. Y mettre une liste de docs, pas « les docs du simulateur ». Au minimum, tout ce que le code lit : `docs/recette/`, `docs/LOTS_ORDRE_ET_PROMPTS.md`, `docs/REGLES_WORKFLOW_AGENT.md`, `docs/WORKFLOW_INDUSTRIEL.md`, les `docs/PLAN_*` du simulateur, `docs/HACKATHON_DEVPOST_SOUMISSION.md`, `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md`.
2. Garder `.gitignore` et `.nvmrc` dans les deux dépôts. Sans l'ignore racine, le dépôt Blue Intelligence n'ignore ni `backend/.env`, ni `frontend/node_modules`, ni `build/`.
3. Garder `.github/`, puis le scinder avant le premier push qui déclenche Actions. Blue Intelligence : jobs `frontend`, `audit-tags`, un `deploy-gate` limité à ses scripts, `weekly-data-build.yml`, Dependabot `frontend` et `backend`. NAVIGUIDE : jobs `simulator` et `simulator-e2e`, déploiement `naviguide` et `simulator`, `zap-baseline.yml`, Dependabot simulateur. Retirer de chaque copie les jobs de l'autre produit. Retirer la branche `recette` du `deploy.yml` Blue Intelligence.
4. Mettre `.zap/` dans NAVIGUIDE seulement. Le workflow vise `simulator.naviguide.fr`.
5. Découper `.cursor/` par fichier. Blue Intelligence : `environment.json`, `install.sh`, `start.sh`, `preview.sh`, et les règles Mongo, modèles, vidéo, réparations, environnement. NAVIGUIDE : `hooks.json`, les scripts `simulator-*`, les règles anti-régression et preview. Les règles communes (environnement, modèles, pas de vidéo) sont à copier, pas à laisser d'un seul côté par oubli.
6. Découper `Archives/`. `Archives/Blue-Intelligence/` (62 fichiers) vers Blue Intelligence. `Archives/naviguide-navsecops/`, `Archives/naviguide-nova/` et `Archives/README.md` vers NAVIGUIDE. Tant que ce n'est pas dans une commande, les 111 fichiers disparaissent des deux.
7. Ne pas garder `.gitconfig`. Décider de `.vscode/tasks.json` dans la commande, pour qu'il ne soit pas un oubli.
8. Ne pas donner `infra/` entier à Blue Intelligence sans liste. `infra/agents/` va avec NAVIGUIDE (ou une copie réduite des scripts génériques `gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py` dans chaque dépôt, avec `BIM_REPO` changé). `infra/vps/ci/` doit être scindé : chaque dépôt n'a que les scripts de ses sites. Les deux fichiers `nginx-bi-climatology-*.conf` doivent être dans le dépôt qui déploie le simulateur, et rester disponibles pour les vhosts Blue Intelligence.
9. Remplacer `git push --mirror` par le push de `refs/heads/main` et des tags voulus. Ne pas pousser les 42 branches (`emergent`, `cursor/*` de septembre, branches de PR ouvertes). Ne pousser les tags `data-*` que vers le dépôt Blue Intelligence.
10. Dire explicitement de ne pas lancer les `git branch -d` imprimés par filter-repo sur un clone `--mirror`.
11. Partir d'un clone miroir frais par dépôt. Un second `filter-repo` sur le résultat ne récupère pas les chemins déjà détruits.
12. Corriger l'import `climatology_query` : soit le test backend embarque une copie ou un extrait, soit il ne dépend plus de `naviguide/naviguide-api/`. Tant que cette ligne reste, le pytest backend du dépôt BI a un échec de plus que le mono-dépôt.
13. Mettre à jour les chiffres du plan : remote `Berry-Mappemonde/Blue-Intelligence` (l'ancien nom renvoie un 301), 1 403 commits sur `main` au 17 octobre 2026, 15:21 −0400. `git-filter-repo` 2.47.0 s'installe par `pip install --user` et n'est pas sur le `PATH` par défaut.
14. Les chemins `/home/ubuntu/blue-intelligence-map` dans les units et les scripts ne sont pas modifiés par le filtre. Le § 6 du plan les traite au moment du VPS. Ils sont encore dans les deux dépôts après le filtre. `DEFAULT_REPO` et l'URL dans `docs/HACKATHON_DEVPOST_SOUMISSION.md` pointent encore le mono-dépôt : après le renommage, cette URL sera le nouveau dépôt Blue Intelligence.
15. Le pytest backend hermétique (1 078 verts ici) peut devenir un job de CI. Les 8 fichiers qui lisent `REACT_APP_BACKEND_URL` et les tests qui ouvrent Mongo restent hors de ce job tant qu'ils n'ont pas de double hors ligne.

## 12. Ce qui n'a pas été fait

Aucun dépôt GitHub créé. Aucun push des historiques filtrés. Aucun renommage. Aucun merge. Aucun appel au VPS, à Mongo, ni à l'API de production. Le hook de la section 10 est une imitation locale du refus des refs cachées, pas une réponse réelle de GitHub. Les tests Playwright, le job `deploy-gate` et les workflows Actions n'ont pas été lancés sur un runner : leur cohérence est déduite des chemins présents ou absents. Le scan de secrets est un `git log -S` et un `git grep`, pas gitleaks.

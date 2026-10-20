[English](README.md)

# NAVIGUIDE

[![Licence : MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![Licence : Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

NAVIGUIDE est le cockpit de l’expédition Berry-Mappemonde : une carte, le bateau, et un briefing écrit seulement à partir de faits structurés, avec NVIDIA Nemotron sur Nebius Token Factory.

**Live: https://naviguide.fr**

**Vidéo de démo :** TODO (Berry)

> **Pas pour la navigation.** Cartes et chiffres viennent de sources publiques et de calculs. Ce n’est pas une carte officielle. Vérifiez les publications des États avant une décision en mer.

## Ce que c’est, et pour qui

NAVIGUIDE suit l’expédition Berry-Mappemonde sur une carte et briefe le prochain port à partir de faits structurés : frontières maritimes, ports, aires protégées, vent et état de mer.
Il sert l’équipage et toute personne qui suit ce voyage. Le départ officiel verrouillé est le 15 mai 2026, 08:00 UTC.
Il sert aussi les juges du hackathon Nebius × NVIDIA, qui veulent voir Nemotron répondre sur Token Factory à partir de ces faits, pas d’un chat ouvert.
Un fait manquant reste vide. Un chiffre n’apparaît que s’il est déjà dans une mesure ou une source publiée.
Ce n’est pas une carte officielle, et ce n’est pas fait pour décider en mer.

Manuels : [français](docs/MANUEL_UTILISATEUR.md), [anglais](docs/USER_MANUAL.md).

## L’essayer en 60 secondes

Sur [https://naviguide.fr](https://naviguide.fr). La première visite s’ouvre en anglais. Cliquez **FR** pour les libellés français.

1. Cliquez **Suivre l’expédition**.
2. Cliquez **Revoir l’expédition**. S’il est grisé, l’info-bulle dit **en préparation**.
3. Quand les commandes du film sont là, **Brut** et **Rédigé** sont côte à côte. **Rédigé** est la narration écrite. Si **Rédigé** est grisé, l’info-bulle dit **pas encore rédigé pour cette durée**.
4. Quand le bateau est à une escale, le panneau s’intitule **Fiche d’escale**. Si cette escale est dans la fenêtre de veille et qu’une veille a été gardée, une carte porte le nom du port, les mots **veille du**, et une date, plus une phrase. Sans veille gardée, cette carte est absente. La fiche liste quand même les lieux qu’elle a.
5. Dans le panneau latéral, **Journal de bord — posez une question**. Le champ dit **Quel vent au bateau ? Prochaine escale ?** Le bouton a pour info-bulle **Envoyer**.
6. Cliquez **Tracer votre propre route**.

Une question simple du journal est répondue à partir des faits déjà collectés. Un pourquoi, un comment, ou une question longue est celle envoyée à Nemotron 3 Ultra quand le budget le permet. Le journal affiche alors : **Vous échangez avec une intelligence artificielle. Les réponses sont générées automatiquement et peuvent contenir des erreurs.**

## Comment on utilise NVIDIA Nemotron sur Nebius Token Factory

L’inférence principale va sur Nebius Token Factory. Les identifiants ci-dessous sont les défauts de `naviguide-simulator/server/llm_budget.py`. Une variable `NAVIGUIDE_TF_MODEL_*` peut en remplacer un.

| Geste | Palier | Modèle | Fichier |
|---|---|---|---|
| Question du journal, JSON seulement | `nano` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | `naviguide-simulator/server/logbook_chat.py` |
| Identifiants des moments du film | `nano` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | `naviguide-simulator/server/film_script.py` |
| Deuxième question de veille, un id d’une liste fixe | `nano` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | `naviguide-simulator/server/escale_watch.py` |
| Phrases courtes, et français vers anglais | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/story_cascade.py` |
| Paragraphe de la fiche d’escale | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/escale_api.py` |
| Résumé de veille en une phrase | `fast` | `nvidia/Nemotron-3_5-Lightning` | `naviguide-simulator/server/escale_watch.py` |
| Carte « ici » quand un récit écrit est demandé | `write` | `nvidia/nemotron-3-super-120b-a12b` | `naviguide-simulator/server/story_cache.py` |
| Chapitres du film écrit | `write` | `nvidia/nemotron-3-super-120b-a12b` | `naviguide-simulator/server/film_script.py` |
| Commentaire de la revue du plan | `write` | `nvidia/nemotron-3-super-120b-a12b` | `naviguide-simulator/server/plan_review.py` |
| Éditer, puis juger, le film écrit | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/film_script.py` |
| Question difficile du journal | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/logbook_chat.py` |
| Affirmation périmée sur un port officiel, seulement si ce juge est allumé | `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `naviguide-simulator/server/truth_judge.py` |
| Regarder un dessin local de la route (pas le routage du bouton Tracer) | — | `nvidia/Nemotron-3.5-Super-VL` | `naviguide-simulator/server/vl_route.py` |

Le palier `deep` utilise le même identifiant Ultra. Aucun module de `naviguide-simulator/server/` n’appelle `tier="deep"` sur ce commit. L’appel VL ne part que de `naviguide-simulator/scripts/one_shot.py` avec `--run`. L’image envoyée est dessinée localement. Les tuiles de la carte ne sont pas envoyées.

Hôtes dans `naviguide-simulator/server/story_cascade.py` : Nano sur `https://api.tokenfactory.nebius.com/v1` (base EU), Lightning et Super sur la même base par défaut, Ultra (`deep` et `judge`) sur `https://api.tokenfactory.us-central1.nebius.com/v1`.

**Cascade.** Un cache SQLite de 24 h est lu d’abord. Si le budget du jour ou `NAVIGUIDE_LLM_MODE` refuse l’appel, rien n’est envoyé et la source est `budget`. Sinon l’ordre par défaut de `DEFAULT_PROVIDERS` est Token Factory, puis NIM, puis OpenRouter, puis Claude. Si l’appelant a fourni un texte de repli et que chaque fournisseur a échoué, la source est `rules`.

Sur le palier `fast` seulement, un corps Token Factory vide, un statut HTTP 500 ou plus, ou un délai dépassé, est retenté une fois sur Token Factory avec le modèle Super. Un 4xx ne prend pas ce second essai. Sur le palier `nano`, un échec Token Factory est retenté une fois sur Token Factory en Lightning, puis la cascade continue. NIM est `openai/gpt-oss-20b` sur `https://integrate.api.nvidia.com/v1/chat/completions`. OpenRouter vaut par défaut `openai/gpt-4o-mini`. Claude est `claude-haiku-4-5`.

**Chiffres.** `filter_numbers` dans `naviguide-simulator/server/story_cascade.py` retire chaque phrase qui contient un nombre absent des faits. Une phrase sans nombre est gardée. Le filtre ne prend pas une invention non numérique.

**Budgets** quand la variable correspondante est absente (`naviguide-simulator/server/llm_budget.py`) :

| Palier | Jetons par jour |
|---|---|
| `nano` | 100 000 |
| `fast` | 200 000 |
| `write` | 150 000 |
| `deep` | 80 000 |
| `judge` | 60 000 |

Les questions difficiles du journal qui atteignent Ultra sont aussi plafonnées à 10 appels par jour. Il n’y a pas de coupure en dollars tant que `NAVIGUIDE_LLM_DAILY_USD` n’est pas posé. Les chiffres commentés dans `naviguide-simulator/server/.env.example` ne sont pas ces défauts. Le mode par défaut est `on-demand` (une action de la personne, pas un travail de fond). `off` ne paie jamais. `all` est explicite.

**Preuve publique.** `GET /ici/warm/status` contient `llm`, et `llm.lastSourceByTier` quand un palier a déjà répondu. La valeur est la source qui a répondu (`nemotron-nano`, `nemotron-lightning`, `nemotron-super`, `nemotron-ultra`, ou le nom d’un repli), pas une phrase du modèle.

À l’écran, une réponse Token Factory est nommée en texte, par exemple **Nemotron 3.5 Lightning · Token Factory**. La barre du film garde une ligne courte, **Modèles**, qui nomme le modèle qui a répondu. Un repli reste étiqueté **NVIDIA NIM (repli)**, **OpenRouter**, **Claude** ou **règles**. Il n’y a pas de logo tiers.

## Tavily

Il n’y a aucun bouton Tavily.

La veille est un travail du serveur. Elle reste éteinte tant que `NAVIGUIDE_TAVILY_WATCH` n’est pas `1` (le défaut est `0`). Allumée, elle couvre une escale de 10 jours avant l’arrivée jusqu’à 2 jours après, au plus deux tours, une fois par escale. Lightning écrit une phrase à partir des extraits. S’il faut un second tour, Nano choisit un id restant dans une liste fixe. Il n’invente pas de question. Plafonds, sauf surcharge : 2 recherches par escale, 6 recherches par jour, 80 crédits Tavily par jour. La carte datée, quand une veille est gardée et pas expirée, s’intitule `{name} · veille du {date}`.

Le juge séparé « relire la page officielle du port » est éteint tant que `NAVIGUIDE_TRUTH_JUDGE` n’est pas `1`.

## Architecture et sources de données

```
naviguide.fr  →  nginx  →  naviguide-simulator
                            ├── Vite / React (dist/)
                            └── FastAPI (uvicorn :8010)
```

Le simulateur ne fait pas tourner MongoDB. Blue Intelligence est une API HTTP séparée. L’arbre partiel `backend/` de ce dépôt n’est pas cette API.

Une licence n’est écrite ici que si ce dépôt la nomme. La fiche (URL, crédit à l’écran, date de relevé) est [naviguide-simulator/DATA_SOURCES.md](naviguide-simulator/DATA_SOURCES.md).

| Source | Licence écrite dans ce dépôt |
|---|---|
| Marine Regions, ZEE v12 | CC-BY 4.0. Ce dépôt ne contient pas CC-BY-NC-SA et ne tranche pas cet écart. |
| OpenStreetMap | ODbL est nommé pour le balisage OpenSeaMap. Le fond crédite les contributeurs OpenStreetMap. |
| EMODnet | CC-BY 4.0 |
| World Port Index, Copernicus Marine, GEBCO, ProtectedSeas / AMP, Saildocs / GRIB, Tavily, Blue Intelligence | Pas nommée à côté de ces sources. Voir la fiche. |

Gouvernance des modèles : [naviguide-simulator/docs/AI_GOVERNANCE.md](naviguide-simulator/docs/AI_GOVERNANCE.md).

## Lancer en local

| Outil | Version |
|---|---|
| Node.js | 24 ([.nvmrc](.nvmrc)) |
| Python | 3.12 (comme dans [.github/workflows/ci.yml](.github/workflows/ci.yml)) |

Depuis un clone propre :

```bash
git clone https://github.com/Berry-Mappemonde/NAVIGUIDE.git
cd NAVIGUIDE/naviguide-simulator
```

Sur macOS, `./dev-mac.sh` crée `.venv` et installe les paquets npm la première fois que ces dossiers manquent, puis sert l’API sur le port 8010 et l’interface sur le port 5174.

Ou installez et lancez les deux processus vous-même :

```bash
npm ci
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010
npm run dev
```

`npm run dev` est le serveur de développement Vite. `npm run server` est la même API avec `--reload` sur `127.0.0.1:8010`.

Noms dans [naviguide-simulator/server/.env.example](naviguide-simulator/server/.env.example), et nulle part une valeur : `NEBIUS_API_KEY`, `NAVIGUIDE_TF_BASE`, `NAVIGUIDE_TF_MODEL_NANO`, `NAVIGUIDE_TF_MODEL_FAST`, `NAVIGUIDE_TF_MODEL_WRITE`, `NAVIGUIDE_TF_MODEL_JUDGE`, `NAVIGUIDE_LLM_PROVIDERS`, `NAVIGUIDE_LLM_DAILY_TOKENS_NANO`, `NAVIGUIDE_LLM_DAILY_TOKENS_FAST`, `NAVIGUIDE_LLM_DAILY_TOKENS_WRITE`, `NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `NVIDIA_API_KEY`, `TAVILY_API_KEY`, `TAVILY_API_BASE`, `NAVIGUIDE_TAVILY_WATCH`, `NAVIGUIDE_WATCH_DAILY_SEARCHES`.

`NAVIGUIDE_LLM_MODE` est lu par le serveur et n’est pas dans cet exemple. Posez `NAVIGUIDE_LLM_MODE=off` pour tourner sans appel de modèle payant. Les récits restent alors sur les règles, le cache, ou le texte local.

Les paquets Python sont épinglés dans [naviguide-simulator/server/requirements.txt](naviguide-simulator/server/requirements.txt).

## Tests

Depuis `naviguide-simulator/` :

```bash
npm test
python -m pytest -q
npx playwright test
```

La CI joue les mêmes tests Node, le build Vite et pytest quand `naviguide-simulator/` change, puis Playwright. Voir [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Déploiement

Un merge sur `main` déploie [https://naviguide.fr](https://naviguide.fr) sur Contabo. Le workflow est [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

## Ce qui a changé depuis le 26 août 2026

Mesuré depuis git, fichiers de code seulement. Les lignes sont copiées de cette mesure. Ce n’est pas une estimation.

Au 2026-08-26 (commit dfca7b1, 2026-08-20) : 0 fichiers de code, 0 lignes — pas de naviguide-simulator/.
Depuis le 2026-08-26 : 174 566 de ces lignes ont été écrites ou réécrites → **100.0 %** du code actuel.
Brassage : +220 468 / −25 851 lignes, 811 fichiers touchés, 1094 commits (141.1 % du code actuel en ajouts + suppressions).

## IA responsable et sécurité

Le texte généré est marqué. Le libellé est **Contenu généré par IA (modèle : {model})**. Le même bloc pose `data-ai-generated`. La charge utile du serveur peut porter `ai_generated` et `generated_at` (`naviguide-simulator/server/ai_transparency.py`). L’avis du journal est la phrase citée dans le parcours de 60 secondes. C’est le marquage que ce dépôt livre pour l’article 50 de l’AI Act. Le dépôt ne tranche pas si le produit est à haut risque, ni comment les deux alinéas de l’article 50 s’y rattachent : voir [naviguide-simulator/docs/AI_GOVERNANCE.md](naviguide-simulator/docs/AI_GOVERNANCE.md). Ce dépôt ne contient pas de chaîne « filigrane ».

Ce checkout ne contient pas de répertoire d’évaluation adverse ni de rapport de tests adverses. Ce README ne dit pas que le produit a été testé avec NVIDIA garak ou promptfoo.

Politique : [SECURITY.md](SECURITY.md). Fiche des sources : [naviguide-simulator/DATA_SOURCES.md](naviguide-simulator/DATA_SOURCES.md).

[![CodeQL](https://github.com/Berry-Mappemonde/NAVIGUIDE/actions/workflows/codeql.yml/badge.svg)](https://github.com/Berry-Mappemonde/NAVIGUIDE/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/Berry-Mappemonde/NAVIGUIDE/badge)](https://scorecard.dev/viewer/?uri=github.com/Berry-Mappemonde/NAVIGUIDE)

Les badges pointent vers [.github/workflows/codeql.yml](.github/workflows/codeql.yml) et [.github/workflows/scorecard.yml](.github/workflows/scorecard.yml). CodeQL n’est pas un contrôle requis. [SECURITY.md](SECURITY.md) note qu’au 18 octobre 2026 ce dépôt n’avait pas encore de résultat CodeQL publié.

## Licence

Le code est [MIT](LICENSE-MIT) ou [Apache-2.0](LICENSE-APACHE), au choix. Les données gardent la licence nommée plus haut, ou celle de la fiche. Les poids Nemotron ne sont pas dans ce dépôt. Ils sont servis par Token Factory et NIM sous la [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/).

# NAVIGUIDE — Blue Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

A [Berry-Mappemonde](https://berrymappemonde.org) project. Code is **MIT or Apache-2.0**.

> [!WARNING]
> **Ne convient pas à la navigation / Not for navigation.**
> Les cartes et les chiffres viennent de sources publiques et de calculs.
> Ce n’est pas une carte marine officielle. Vérifiez toujours les publications
> gouvernementales avant une décision en mer.

## Français

**NAVIGUIDE simulator** est un briefing qui glisse. Un catamaran suit la
vraie route de l’expédition Berry-Mappemonde (départ de Saint-Maur le
15 mai 2026, territoires français d’outre-mer, retour à La Rochelle).
Autour du bateau, l’application montre ce qui compte : une frontière
maritime, un port d’entrée officiel, une aire protégée, le vent, la
prochaine escale. Un champ inconnu reste vide. Aucun chiffre n’est inventé.

**Blue Intelligence** ([blueintelligence.online](https://blueintelligence.online))
est la mémoire des sources (marinas, capitaineries, ports d’entrée, aires
protégées, science, projets). Le simulateur l’interroge ; les deux produits
ne partagent pas la même base.

### Trois modes, plus le film

| Mode | Ce que vous voyez |
|------|-------------------|
| **Suivre l’expédition** | Le bateau à la position d’aujourd’hui. La carte le suit. |
| **Simulation** | La même horloge, que vous faites avancer. Date de départ et limites du skipper. |
| **Tracer ma route** | Vous posez des points (ou importez un fichier). Le même briefing apparaît. |
| **Revoir l’expédition** | Un film raconté, de Saint-Maur jusqu’à aujourd’hui. |

Manuel écran par écran : [docs/MANUEL_UTILISATEUR.md](docs/MANUEL_UTILISATEUR.md).

### En production

- Simulateur : [simulator.naviguide.fr](https://simulator.naviguide.fr)
- Blue Intelligence : [blueintelligence.online](https://blueintelligence.online)
- Ancien planificateur : [www.naviguide.fr](https://www.naviguide.fr)

### Lancer en local (macOS)

Il faut **Node.js 18+** et **Python 3.11+**. Dans le Terminal :

```bash
cd naviguide-simulator
bash dev-mac.sh
```

Le script démarre l’interface et ouvre le navigateur. Les clés (Nemotron,
Tavily, Copernicus…) vivent hors du dépôt, dans
`~/.config/naviguide/simulator.env` — ne les commitez jamais.
Sans clés, l’application tourne quand même : le récit retombe sur des
règles, pas sur un modèle.

### Nemotron, Token Factory, Tavily

Textes générés (briefing, journal, film, fiches) : cascade côté serveur —
**[Nebius Token Factory](https://tokenfactory.nebius.com/)** (Nemotron), puis
**NVIDIA NIM** (`gpt-oss-20b`), puis **OpenRouter** (`gpt-4o-mini`), puis
**Anthropic Claude Haiku 4.5**, puis un texte **uniquement par règles** si
tout échoue ou si le budget du jour est épuisé. Par défaut le mode est
**on-demand** (appel payant seulement quand vous posez une question ou
demandez un « Rédigé », pas en tâche de fond). Les prompts identiques sont
mis en **cache** (environ 24 h). Un **filtre serveur** retire tout chiffre que
le modèle n’a pas reçu dans les faits (`filter_numbers`).

Plafonds journaliers de tokens (défauts) : **200 000** (Lightning), **150 000**
(Super), **40 000** (Ultra). L’interface affiche la source réelle (ex.
« Nemotron 3 Ultra · Token Factory », avec les marques NVIDIA / Nebius /
Token Factory sous les réponses Nemotron).

| Modèle | Usages principaux |
|--------|-------------------|
| **Nemotron 3.5 Lightning** | Fiche d’escale, résumés **Tavily**, choix des moments du film, traduction FR→EN, conseil de route, questions courtes au chat (&lt; 80 caractères). |
| **Nemotron 3 Super** | Briefing courant, chat journal (questions longues), revue de plan, script du film. |
| **Nemotron 3 Ultra** (`nvidia/Nemotron-3-Ultra-550b-a55b`) | Chat avec *pourquoi / comment* ou mots de route ; récit des **moments clés** (arrivée au port, grain, cyclone, alerte profondeur, marina refuge, tout événement de sévérité `alert`). |

Pour chaque escale à venir, **Tavily** cherche une fois des nouvelles récentes
et datées ; Lightning les résume sans chiffre nouveau (en production sur
[simulator.naviguide.fr](https://simulator.naviguide.fr)). La mémoire des
sources reste sur
[blueintelligence.online](https://blueintelligence.online).

### Licence

Le code est sous **MIT ou Apache License 2.0** (`LICENSE-MIT`,
`LICENSE-APACHE`). Les données (OpenStreetMap, Marine Regions, EMODnet…)
gardent leur licence d’origine. Les poids Nemotron restent sous licence
NVIDIA.

Index des plans : [docs/README.md](docs/README.md).
Esprit de l’application : [docs/ESPRIT_DE_L_APPLICATION.md](docs/ESPRIT_DE_L_APPLICATION.md).

## English

**NAVIGUIDE simulator** is a briefing that glides. A catamaran follows the
real Berry-Mappemonde route (Saint-Maur, 15 May 2026, French overseas
territories, back to La Rochelle). Around the boat the app shows what
matters: a maritime border, an official port of entry, a protected area,
the wind, the next harbour. Unknown fields stay empty. No number is invented.

**Blue Intelligence** ([blueintelligence.online](https://blueintelligence.online))
is the memory of sources (marinas, harbour masters, ports of entry, MPAs,
science, projects). The simulator queries it over HTTP; the two products
do not share a database.

### Three modes, plus the film

| Mode | What you see |
|------|----------------|
| **Follow expedition** | The boat at today’s position. The map follows. |
| **Simulation** | The same clock, advanced on demand. Your departure date and skipper limits. |
| **Draw your own route** | Click points (or import a file). The same briefing appears. |
| **Replay the expedition** | A narrated film from Saint-Maur to today. |

Screen-by-screen manual: [docs/USER_MANUAL.md](docs/USER_MANUAL.md).

### Live

- Simulator: [simulator.naviguide.fr](https://simulator.naviguide.fr)
- Blue Intelligence: [blueintelligence.online](https://blueintelligence.online)
- Legacy planner: [www.naviguide.fr](https://www.naviguide.fr)

### Run locally (macOS)

You need **Node.js 18+** and **Python 3.11+**. In Terminal:

```bash
cd naviguide-simulator
bash dev-mac.sh
```

The script starts the UI and opens the browser. Keys (Nemotron, Tavily,
Copernicus…) live outside the repo, in
`~/.config/naviguide/simulator.env` — never commit them.
Without keys the app still runs: the story falls back to rules, not a model.

### Nemotron, Token Factory, Tavily

Generated copy (briefing, logbook, film, sheets): server-side cascade —
**[Nebius Token Factory](https://tokenfactory.nebius.com/)** (Nemotron), then
**NVIDIA NIM** (`gpt-oss-20b`), then **OpenRouter** (`gpt-4o-mini`), then
**Anthropic Claude Haiku 4.5**, then **rules-only** text if everything fails
or the daily budget is spent. Default mode is **on-demand** (paid calls only
when you ask a question or click “Write”, not in background warm-up). Identical
prompts are **cached** (~24 h). A **server filter** drops any number the model
was not given in the facts (`filter_numbers`).

Default daily token caps: **200k** (Lightning), **150k** (Super), **40k**
(Ultra). The UI shows the actual source (e.g. “Nemotron 3 Ultra · Token
Factory”, with NVIDIA / Nebius / Token Factory marks under Nemotron answers).

| Model | Main uses |
|-------|-----------|
| **Nemotron 3.5 Lightning** | Port-of-call sheet, **Tavily** summaries, picking film moments, FR→EN translation, route advice, short chat questions (&lt; 80 characters). |
| **Nemotron 3 Super** | Everyday briefing, logbook chat (longer questions), plan review, film script. |
| **Nemotron 3 Ultra** (`nvidia/Nemotron-3-Ultra-550b-a55b`) | Chat with *why/how* or route-plan wording; narrative of **key moments** (port arrival, gale, cyclone, depth alert, marina refuge, any `alert` severity event). |

For each coming stopover, **Tavily** searches once for recent, dated news;
Lightning summarises it without new numbers (live on
[simulator.naviguide.fr](https://simulator.naviguide.fr)). Source memory lives
on [blueintelligence.online](https://blueintelligence.online).

### Licence

Code is **MIT or Apache License 2.0** (`LICENSE-MIT`, `LICENSE-APACHE`).
Cartographic data keep their original licences. Nemotron weights stay
under the NVIDIA licence.

Plans index: [docs/README.md](docs/README.md).
What the app is for: [docs/ESPRIT_DE_L_APPLICATION.md](docs/ESPRIT_DE_L_APPLICATION.md).

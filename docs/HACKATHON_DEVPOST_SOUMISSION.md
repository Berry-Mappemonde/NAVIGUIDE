# Soumission Devpost — Nebius × NVIDIA Global AI Hackathon

Version **1.0** — 20 septembre 2026. Textes **en anglais** (exigé par les
règles), prêts à coller ; consignes en français. Ton : honnête, vrai, court,
compréhensible par un jury qui n'est pas que technique (marketing, UX).
Ce document remplace la partie « soumission » de `hackathon-nebius-nvidia.md`.

## 0. Avant de soumettre — ce qui doit être vrai

Les règles exigent un **appel runtime à Nebius Token Factory** avec un
**modèle NVIDIA open source**. Aujourd'hui le simulateur appelle NIM
(`integrate.api.nvidia.com`) : **ne pas soumettre avant** que le lot L1 (et
idéalement L2–L3, `PLAN_NEMOTRON_NEBIUS_TAVILY.md`) soit **en production** sur
`simulator.naviguide.fr`. Liste de contrôle :

- [ ] Lot L1 mergé et déployé : le libellé « Nemotron 3 Super · Token Factory »
      apparaît sous un récit en prod.
- [ ] Lot L3 (Tavily + Ultra) si l'on coche « Yes » à Tavily — sinon cocher « No ».
- [ ] Crédits Token Factory valides **jusqu'au 15 décembre** (juges) : demander
      les +25 $ (formulaire Devpost) et +25 $ (Builders Program) maintenant ;
      vérifier l'expiration de l'essai (13 sept. + 29 j ≈ 12 oct.).
- [ ] Dépôt public, licence **MIT** visible dans « About » (déjà le cas :
      `Berry-Mappemonde/Blue-Intelligence`, MIT), `README` avec installation et
      lancement du simulateur **en anglais**, section « How we use Nemotron on
      Token Factory / Tavily ».
- [ ] Vidéo YouTube publique **< 3 min** (cible 2:30), sans musique protégée,
      montrant l'app en marche ; pas de logos tiers hors les nôtres.
- [ ] Tous les textes en anglais (ou traduction fournie) ; la démo est
      bilingue FR/EN, mettre l'app en anglais dans la vidéo.
- [ ] « Existing project » : la case « significantly updated » est remplie
      (§ 3) — c'est vrai : tout ce qui est listé a été fait après le 26 août.

## 1. Project overview

**Project name** (≤ 60 caractères — le champ est vide sur la capture, le
titre du brouillon est trop long) :

```
NAVIGUIDE — a sailor's briefing that glides
```

Variante : `NAVIGUIDE for Berry-Mappemonde: maps, not chatbots` (49).

**Elevator pitch** (≤ 200 caractères) :

```
A circumnavigation on a live map: the boat glides, official sources speak when they matter, and Nemotron on Nebius tells the story without ever inventing a number.
```
(179 caractères.)

**Thumbnail** : garder l'actuel (globe + satellite + « NAVIGUIDE for
Berry-Mappemonde »), ratio 3:2, ≤ 5 Mo.

## 2. Project details — « About the project »

Coller tel quel (Markdown accepté). Les liens sont réels.

```md
## Inspiration

A round-the-world voyage cannot run on a chatbot. Skippers need a **map** and a **briefing**: where am I, what around me matters right now — a maritime border, the official port of entry, a marine protected area, a gale, a research station, the next harbour and its services — and, just as important, **what the system does not know**.

[Berry-Mappemonde](https://berrymappemonde.org) is a French non-profit sailing a catamaran from Saint-Maur (Paris) around the French overseas territories and back to La Rochelle. We build the tools that crew would actually use.

> Unknown field = empty. Never invented. A sailor might trust this map.

## What it does

Two live products, one job: turn messy maritime data into something a human can use at sea.

**[Blue Intelligence](https://blueintelligence.online)** is the memory: a world map of marinas, harbour masters, official ports of entry (verified against government pages — we call them *Gold*), marine protected areas, ocean-science layers and conservation projects, collected and refreshed by agents.

**[NAVIGUIDE simulator](https://simulator.naviguide.fr)** is the briefing. Press play: the boat glides along the real route. Every ~30 nautical miles the app builds a small *bag* of what lies within 60 nm — borders, Gold ports of entry, protected areas, wind and sea state, research stations, the coming harbour — and **rules** (not a model) decide what interrupts you (*NOW*: safety and decisions) and what waits for a quiet moment (*FREE*: science, projects, seabed).

Then the story is told. **NVIDIA Nemotron 3 on Nebius Token Factory** writes the briefing, the harbour sheet, the answers in the logbook chat and the narrated replay of the whole expedition — from structured facts only. Every number on screen comes from a source or a calculation; a filter rejects any figure the model did not receive. When the boat enters a new country's waters, **Tavily** re-reads the official port-of-entry page and Nemotron 3 Ultra strikes out whatever is no longer supported.

Three ways to use it:
- **Follow the expedition** — today's position, camera follow, cards that pause the film, and *Replay*: a 2 min 30 narrated film of the voyage so far, with events popping out of the boat as the voice reaches them.
- **Simulation** — same clock, your departure date, your skipper limits (max wind, max wave height) and a route recomputed around them.
- **Draw your own route** — click a route anywhere; the same briefing appears.

## How we built it

- Python / FastAPI server with an embedded SQLite memory (pearls of pre-computed context, journal, story cache) so the app answers in milliseconds and keeps working offline.
- React + Leaflet client; the map follows a real voyage clock integrated from the boat's polar diagram, wind and sea state.
- Sources: Marine Regions EEZ polygons, World Port Index, OpenStreetMap marinas and harbour masters, official ports-of-entry pages, marine protected areas, EMODnet bathymetry and cables, Copernicus Marine (wind, waves, currents), GRIB forecasts, a climatology atlas (wind roses, cyclone seasons).
- LLM layer on **Nebius Token Factory** (OpenAI-compatible API): Nemotron 3 Super writes; Nemotron 3.5 Lightning ranks, extracts and translates; Nemotron 3 Ultra judges one visible action at a time. Everything is cached, budgeted and labelled with its source in the UI.
- **Tavily** search/extract for dated harbour notices and to re-verify Gold ports of entry.
- CI: unit tests (JS + Python), production build, security audits, Playwright smoke tests; every feature ships as a small pull request with a visual acceptance script.

## Challenges we ran into

- Making a boat *glide* over 39,000 nm without teleporting: a proper voyage clock, camera follow that does not jitter, cards that pause the film only when it matters.
- Keeping the model honest: numbers come from facts, unknown fields stay empty, and every generated paragraph shows where it came from.
- Sources that lie or move: an official page changes, a protected area is redrawn — hence Gold verification and Tavily re-checks.
- Long-context budgets for our own AI coding agents: the plan is split into small, visually testable lots.

## Accomplishments that we're proud of

Two products online. A journal that remembers every border, port of entry, protected area, gale and note along the route. A narrated replay a non-sailor can watch. A codebase small agents can safely extend.

## What we learned

A briefing is not a chat. Rules decide *when*; the model decides *how to say it*; sources decide *what is true*.

## What's next

Hindcast of the real weather the boat met since 15 May 2026 (the position as the sum of real speeds), a globe view, route advice explained in plain words, and the same briefing for any crew's own voyage.

## Nemotron, Token Factory and Tavily — where exactly

- `naviguide-simulator/server/story_cascade.py` — Token Factory first (Nemotron 3 Super / 3.5 Lightning / 3 Ultra by tier), fallbacks, daily token budget, source labels.
- `server/story_cache.py`, `logbook_chat.py`, `escale_api.py`, `film_script.py` — briefing, chat, harbour sheet, replay script.
- `server/truth_judge.py`, `server/tavily_client.py` — Tavily extract + Nemotron 3 Ultra verdicts on Gold ports of entry.
- Live: https://simulator.naviguide.fr — the source label under each generated paragraph reads "Nemotron 3 Super · Token Factory".
```

**Built with** (tags, ≤ 25) : `python`, `fastapi`, `react`, `vite`, `leaflet`,
`sqlite`, `tailwind`, `nemotron`, `nebius-token-factory`, `tavily`,
`copernicus-marine`, `emodnet`, `openstreetmap`, `marine-regions`,
`playwright`, `nginx`, `ubuntu`, `github-actions`, `mongodb`, `openrouter`,
`web-speech-api`.
Retirer de la liste actuelle ce qui n'est pas dans la soumission (ex.
`langsmith`) et ajouter `nemotron`, `nebius-token-factory`, `tavily`.

**Try it out links** : `https://simulator.naviguide.fr` et
`https://blueintelligence.online` (déjà saisis) ; ajouter le dépôt
`https://github.com/Berry-Mappemonde/Blue-Intelligence`.

**Image gallery** (5 captures 3:2, prises par le spec Playwright du film,
app en anglais) : 1) Follow mode à la position du jour avec une carte NOW ;
2) le film à mi-Atlantique avec une bulle « Gale 38 kn » ; 3) fiche
d'escale ; 4) revue de plan (tableau) ; 5) « Draw your own route » Brisbane →
San Francisco.

**Video demo link** : YouTube public, 2:30. Plan de tournage (aucun
enregistrement d'écran par l'agent : c'est le porteur qui filme) :

| Temps | Écran | Voix (EN) |
|---|---|---|
| 0:00–0:15 | Follow mode, position du jour, carte NOW | « This is NAVIGUIDE. A catamaran, a real voyage, and a briefing that only says what its sources know. » |
| 0:15–2:05 | **Replay** plein écran film (lot F5), voix de l'app | le script du film (Nemotron) — c'est l'app qui parle |
| 2:05–2:20 | Chat : « How fast are we going? » → « At quay, 0 kn » ; fiche d'escale ; badge « Verified · Tavily + Nemotron 3 Ultra » | « Every number is a fact. Tavily re-reads the official page; Nemotron judges. » |
| 2:20–2:30 | Draw your own route, la route apparaît, une carte NOW | « Draw your own route. Same briefing. Not for navigation — for understanding the sea. » |

## 3. Additional info — réponses

| Champ | Réponse |
|---|---|
| Submitter Type | **Organization** si le porteur soumet au nom de l'association Berry-Mappemonde (cohérent avec « Organization Name ») ; sinon **Team**. Le brouillon dit Team : à trancher. |
| Organization Name | `Berry-Mappemonde (French non-profit association)` — ou `N/A` si Team. |
| Submitter Country of Residence | `France` |
| Canada province | `N/A` |
| Track | **Best apps and agents** |
| New or existing prior to August 26, 2026? | **Existing** |
| If existing, how significantly updated with Nebius tools | voir texte ci-dessous |
| Public code repository | `https://github.com/Berry-Mappemonde/Blue-Intelligence` (MIT, README, section Nemotron/Token Factory) |
| Working demo URL | `https://simulator.naviguide.fr` |
| Which model(s), why that size | voir ci-dessous |
| Nemotron output quality (1–10) | **à noter après L1–L3** ; ne pas inventer une note. Proposition de texte ci-dessous, chiffre à compléter. |
| Fine-tune / prompt-engineer / out of the box | voir ci-dessous |
| Compared to other models | voir ci-dessous |
| Nebius capabilities most valuable | voir ci-dessous |
| Recommend Nemotron on Nebius (1–10) | à noter après usage |
| Experience vs previous environments (1–10) | à noter après usage |
| Additional features that would have helped | voir ci-dessous |
| Hope to see next from Nemotron team | voir ci-dessous |
| Did you use Tavily? | **Yes** seulement si L3 est en prod ; sinon **No** |
| Builders & Brews city | `Paris` (Thu, Oct 1) si le porteur y va ; sinon vide. Rappel : un seul bonus par projet (Tavily 3 000 $ vaut mieux que City 500 $) — la case ne coûte rien mais ne cumule pas. |

**Existing project — what changed since August 26, 2026** :

```
NAVIGUIDE existed as a flat map with a route and a polar panel. Since August 26 we rebuilt it around the voyage: a real voyage clock and camera follow, the "bag" of nearby context every 30 nm (EEZ, Gold ports of entry, MPAs, weather, science, harbours) with rule-based NOW/FREE cards, a persistent SQLite memory, a journal of every border, port of entry, protected area and gale, harbour sheets, a logbook chat, plan review by rules, isochrone route advice with skipper limits, and the narrated replay. The LLM layer moved to Nebius Token Factory: Nemotron 3 Super writes every generated paragraph (briefing, harbour sheet, chat, replay script), Nemotron 3.5 Lightning ranks and translates, Nemotron 3 Ultra judges Gold ports of entry against pages re-read by Tavily. All of this is in the repository history (pull requests #189–#2xx).
```

**Which model(s) did you use, and why that size/variant** :

```
Nemotron 3.5 Lightning for high-volume, low-stakes calls (ranking events for the replay, extraction, FR↔EN translation) — cheapest and fast. Nemotron 3 Super 120B (12B active) for everything the user reads (briefing, harbour sheet, logbook chat, replay script): the best quality/cost for long structured prompts, 262k context. Nemotron 3 Ultra only as a judge, one visible action at a time (is this Gold port-of-entry sheet still supported by the official page Tavily just re-read?). The model never produces a number: a server-side filter rejects any figure absent from the facts.
```

**Fine-tune / prompt-engineer / out of the box** :

```
Out of the box, prompt-engineered. Prompts carry structured facts (JSON) and hard constraints (keep every number, name and date as given; mark events with tags; target length). A server filter enforces the number rule; failures fall back to a rules-generated text and are counted. No fine-tuning: the data changes daily and the product must work with the rules alone.
```

**Compared to other models** (à compléter avec l'observation réelle ; gabarit) :

```
We ran the same prompts through our previous cascade (an open 20B model on NIM, GPT-4o-mini via OpenRouter, Claude Haiku as last resort). [Fill after L1–L3: instruction following on the number rule and the event tags; French quality; latency; cost per generated paragraph.] Numbers we can state: Super costs about $0.003 per replay script and the whole product runs on roughly $0.20 a day.
```

**Which Nebius platform capabilities were most valuable** :

```
Token Factory's OpenAI-compatible API (one base_url change from our previous provider), per-token pricing with no infrastructure, and having Lightning / Super / Ultra behind the same endpoint so a "tier" parameter picks the model. We run inference only (no GPU instances); deployment is our own Ubuntu VPS with nginx, and Token Factory is called server-side with caching, a daily token budget and a fallback chain.
```

**Additional features / improvements** (proposer honnêtement, après usage) :

```
[Fill after use — candidates: a per-key spend cap and alerting in the console; a published model catalogue with ids, context windows and prices in one machine-readable place; longer trial credit validity so judges can test in December; structured-output (JSON schema) guarantees for Super and Ultra.]
```

**What do you most hope to see next** :

```
Smaller Nemotron variants with reliable structured output and long context for on-board use (a boat has poor connectivity), and a hosted embeddings model from the Nemotron family on Token Factory.
```

## 4. Profil Devpost (le porteur fournira la page ; gabarit)

- **Nom** : Clément Filisetti · **Titre** : Founder, Berry-Mappemonde (non-profit) — NAVIGUIDE & Blue Intelligence.
- **Bio (≤ 3 lignes)** : « Sailor and builder. I run Berry-Mappemonde, a French non-profit sailing a catamaran around the French overseas territories, and I build the open tools the crew uses: a world map of maritime sources and a briefing that glides. Not for navigation — for understanding the sea. »
- **Liens** : GitHub `Berry-Mappemonde`, `berrymappemonde.org`, `blueintelligence.online`, `simulator.naviguide.fr`.
- **Compétences** : Python, FastAPI, React, Leaflet, geospatial data, agentic pipelines.
- **Éviter** : jargon interne (« perles », « sac ») sans explication, promesses non livrées, tout chiffre non vérifiable.

## 5. Ce que les juges notent (et où on marque des points)

| Critère | Ce qu'on montre |
|---|---|
| Technological Implementation | Token Factory en runtime, trois tailles de Nemotron par usage, cache + budget + source affichée ; Tavily ancré sur **une fiche** |
| Design | un produit complet : trois modes, cartes, fiches, chat, replay narré, bilingue, mode clair |
| Potential Impact | un vrai équipage, une vraie route, des sources officielles ; « not for navigation » assumé ; réutilisable pour toute route dessinée |
| Quality of the Idea | le sac de 60 nm jugé par des règles, le modèle qui n'a pas le droit d'inventer un chiffre, le juge de vérité à la source |

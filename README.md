# NAVIGUIDE — Blue Intelligence expedition briefing

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

A [Berry-Mappemonde](https://berrymappemonde.org) project. Code is **MIT or Apache-2.0** (see [License](#license)).

> **Not for navigation.** Maps and figures come from public sources and calculations. This is not an official chart. Always check government publications before decisions at sea.

**NAVIGUIDE is live at [https://naviguide.fr](https://naviguide.fr).**  
**Every merge to `main` deploys this version** (GitHub Actions → Contabo VPS; see [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)).

The **Blue Intelligence** HTTP API remains at [https://blueintelligence.online/api](https://blueintelligence.online/api) (separate repository: [Berry-Mappemonde/Blue-Intelligence](https://github.com/Berry-Mappemonde/Blue-Intelligence)).

This repository is the **NAVIGUIDE** codebase submitted to the [Nebius × NVIDIA Global AI Hackathon on Devpost](https://nebiusglobalaihackathon.devpost.com/). Hackathon planning and submission copy live under [`docs/`](docs/) (for example [`docs/HACKATHON_DEVPOST_SOUMISSION.md`](docs/HACKATHON_DEVPOST_SOUMISSION.md)).

---

## What NAVIGUIDE is

**NAVIGUIDE simulator** is an expedition cockpit: a Leaflet map, a moving catamaran on the real Berry-Mappemonde circumnavigation route (departure Saint-Maur, 15 May 2026, French overseas territories, return to La Rochelle), and a **briefing** built from structured facts—maritime borders, official ports of entry (“Gold”), marine protected areas, wind and sea state, science layers, and the next harbour. Empty fields stay empty; numbers are not invented.

Around the boat, the app assembles a small **“here” bag** (`ici()` on the server) from map data and from **Blue Intelligence** over HTTP. Rules (not a model) decide what interrupts the sailor (*NOW*) versus what waits for a quiet moment (*FREE*).

| Mode | What you see |
|------|----------------|
| **Follow the expedition** | Today’s position, camera follow, briefing cards, logbook, and **Replay** (narrated film of the voyage so far). |
| **Simulation** | The same clock, advanced on demand; departure date and skipper limits (wind, waves); route recomputation. |
| **Draw your own route** | Click or import a route; the same briefing pipeline applies. |
| **Replay / film** | Scripted chapters with optional **Raw** vs **Written** narration (see [NVIDIA & Nebius](#nvidia-nemotron-models-and-nebius-token-factory)). |

Screen-by-screen manual: [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) (English), [`docs/MANUEL_UTILISATEUR.md`](docs/MANUEL_UTILISATEUR.md) (French). Simulator-focused notes: [`naviguide-simulator/README.md`](naviguide-simulator/README.md).

---

## Architecture

```
naviguide.fr  ──►  nginx (VPS)  ──►  naviguide-simulator
                      │                ├── Vite/React SPA (dist/)
                      │                └── FastAPI (uvicorn :8010)
                      │
                      └── HTTP ──►  blueintelligence.online/api  (other repo / OVH)
```

| Area | Role |
|------|------|
| [`naviguide-simulator/`](naviguide-simulator/) | **Main application**: React 19 + Vite 8 frontend, Python **FastAPI** server (`server/main.py`), on-disk stores (no MongoDB on the simulator VPS). |
| [`naviguide-simulator/server/`](naviguide-simulator/server/) | API on port **8010**: routing, weather pipeline, `ici()` bag, LLM cascade, film script, logbook chat, Tavily watch, BI proxy. |
| [`backend/`](backend/) | **Partial copy** in this repo: climatology wind helpers and sample `.npz` data—not the full Blue Intelligence API. |
| [`infra/vps/`](infra/vps/) | Deploy scripts, systemd units, nginx snippets, env templates for the Contabo host (`naviguide@13.140.164.185`). Details: [`infra/vps/README.md`](infra/vps/README.md). |
| [`docs/`](docs/) | Plans, hackathon submission text, user manuals, recette screenshots. |
| [`Archives/`](Archives/) | Archived planner / navsecops trees (not part of the live product). |

**CI** (`.github/workflows/ci.yml`) runs when `naviguide-simulator/**` changes: Node unit tests, Vite build, `pytest`, npm/pip audit, and Playwright e2e on a frozen store. The Blue Intelligence frontend and API pytest suite are **not** in this repository.

**Production:** `https://naviguide.fr` serves the built simulator; `www.naviguide.fr` and `simulator.naviguide.fr` redirect there ([`infra/vps/README.md`](infra/vps/README.md)).

---

## Installation

### Prerequisites

Versions pinned or used in CI (do not guess newer majors unless you accept drift from lockfiles):

| Tool | Version |
|------|---------|
| **Node.js** | **24** (see [`.nvmrc`](.nvmrc)) |
| **npm** | Uses `naviguide-simulator/package-lock.json` (`npm ci`) |
| **Python** | **3.12** (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)) |
| **pip packages** | Pinned in [`naviguide-simulator/server/requirements.txt`](naviguide-simulator/server/requirements.txt) (FastAPI 0.142.2, uvicorn 0.54.0, …) |

Frontend stack (from [`naviguide-simulator/package.json`](naviguide-simulator/package.json)): React 19.1.1, Vite 8.3.4, Leaflet 1.9.4, Tailwind 4.1.17.

### Clone and install dependencies

```bash
git clone https://github.com/Berry-Mappemonde/NAVIGUIDE.git
cd NAVIGUIDE/naviguide-simulator
npm ci
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt
```

### Environment variables

Copy templates and fill values **locally**—never commit secrets:

| Template | Purpose |
|----------|---------|
| [`naviguide-simulator/server/.env.example`](naviguide-simulator/server/.env.example) | LLM cascade (Nebius, NIM, OpenRouter, Claude), Tavily, optional model overrides. |
| [`infra/vps/naviguide/simulator.env.example`](infra/vps/naviguide/simulator.env.example) | Production-oriented: Copernicus, admin secret, CORS, `BI_API_URL`, LLM mode caps. |

**Hackathon / Nemotron (Token Factory)** — from `server/.env.example`:

- `NEBIUS_API_KEY` — Nebius Token Factory API key (required for live Nemotron calls).
- Optional: `NAVIGUIDE_TF_BASE`, `NAVIGUIDE_TF_BASE_ULTRA`, `NAVIGUIDE_TF_MODEL_FAST`, `NAVIGUIDE_TF_MODEL_WRITE`, `NAVIGUIDE_TF_MODEL_DEEP`, `NAVIGUIDE_TF_MODEL_JUDGE`, `NAVIGUIDE_LLM_PROVIDERS`, `NAVIGUIDE_LLM_DAILY_TOKENS_*`, `NAVIGUIDE_LLM_MODE`, `NAVIGUIDE_CHAT_ULTRA_PER_DAY`, `NAVIGUIDE_LLM_DAILY_USD`.

**Fallback LLMs (optional):** `NVIDIA_API_KEY` (NIM), `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`.

**Tavily (optional):** `TAVILY_API_KEY`, `TAVILY_API_BASE`, `NAVIGUIDE_TAVILY_WATCH`, `NAVIGUIDE_WATCH_DAILY_SEARCHES`.

**Blue Intelligence:** `BI_API_URL` (default in code: `https://blueintelligence.online/api`), `BI_ADMIN_KEY` for Gold review fiches (see simulator env example).

**Weather (optional):** `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD` (see infra example).

On macOS, project hooks may use `~/.config/naviguide/simulator.env` (documented in [`docs/WORKFLOW_INDUSTRIEL.md`](docs/WORKFLOW_INDUSTRIEL.md)). **Without API keys**, the app still runs: stories fall back to **rules**, caches, or mocks; CI runs with no secrets.

---

## Usage

### Local development

**macOS (recommended in-repo scripts):**

```bash
cd naviguide-simulator
bash ensure-dev.sh --open    # API + Vite in background, browser on http://localhost:5174
# or
bash dev-mac.sh              # foreground Vite
bash stop-dev.sh             # stop background servers
```

**Generic (two terminals):**

```bash
cd naviguide-simulator
source .venv/bin/activate
npm run server    # uvicorn on http://127.0.0.1:8010
npm run dev       # Vite on http://localhost:5174 (proxies API)
```

Other npm scripts ([`package.json`](naviguide-simulator/package.json)): `npm run build`, `npm run preview`, `npm run e2e`, `npm run e2e:store`.

### Tests

From `naviguide-simulator/`:

| Command | What it runs |
|---------|----------------|
| `npm test` | Node.js unit tests (`src/**/*.test.js`, engine, hooks, UI contracts). |
| `python -m pytest -q` | Python API tests (`server/tests/`, see [`pytest.ini`](naviguide-simulator/pytest.ini)). |
| `npm run e2e` | Playwright (full suite; some `poste` specs skipped without a live store). |
| `PW_WITH_API=1 npm run e2e:store` | Playwright lots with API + frozen store. |

CI mirrors: `npm test`, `npm run build`, `pytest`, Playwright shards ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

---

## Dependencies (summary)

- **Map & UI:** Leaflet, React, Tailwind, Lucide icons.
- **Server:** FastAPI, httpx, searoute, shapely, geographiclib, Copernicus Marine client, pandas/numpy/xarray for GRIB/climatology paths, pymongo only where tests or tooling expect it—not a simulator production MongoDB ([`docs/PLAN_SEPARATION_DEPOTS.md`](docs/PLAN_SEPARATION_DEPOTS.md)).
- **External APIs (when keys are set):** Nebius Token Factory (Nemotron), NVIDIA NIM, OpenRouter, Anthropic, Tavily, Copernicus, Blue Intelligence HTTP API.

Attributions for map tiles and data layers: [`naviguide-simulator/README.md`](naviguide-simulator/README.md#licences-and-attributions).

---

## NVIDIA Nemotron models and Nebius Token Factory

Hackathon rules require a **runtime call to Nebius Token Factory** with at least one **NVIDIA open-source model**. This codebase routes **primary inference** through Token Factory; NVIDIA **NIM** (`integrate.api.nvidia.com`, model `openai/gpt-oss-20b`) is a **fallback** provider in the same cascade—not counted as the hackathon Token Factory path, but implemented for resilience.

### Token Factory endpoints and configuration

| Item | Location |
|------|----------|
| Default API base (Nano / Lightning / Super) | `https://api.tokenfactory.nebius.com/v1` — [`naviguide-simulator/server/story_cascade.py`](naviguide-simulator/server/story_cascade.py) (`TOKENFACTORY_BASE`, `NAVIGUIDE_TF_BASE`) |
| Ultra / judge region base | `https://api.tokenfactory.us-central1.nebius.com/v1` — same file (`TOKENFACTORY_ULTRA_BASE`, `NAVIGUIDE_TF_BASE_ULTRA`) |
| API key | `NEBIUS_API_KEY` — [`story_cascade.py`](naviguide-simulator/server/story_cascade.py) (`nebius_key()`), [`server/.env.example`](naviguide-simulator/server/.env.example) |
| Provider order | `NAVIGUIDE_LLM_PROVIDERS` default `tokenfactory,nim,openrouter,claude` — [`story_cascade.py`](naviguide-simulator/server/story_cascade.py) |
| HTTP chat call | `_call_tokenfactory()` → `/chat/completions` — [`story_cascade.py`](naviguide-simulator/server/story_cascade.py) |
| Embeddings (logbook RAG) | `{TOKENFACTORY_BASE}/embeddings` — [`naviguide-simulator/server/logbook_chat.py`](naviguide-simulator/server/logbook_chat.py) |

### Default Nemotron model IDs (overridable via `NAVIGUIDE_TF_MODEL_*`)

Defined in [`naviguide-simulator/server/llm_budget.py`](naviguide-simulator/server/llm_budget.py) (`DEFAULT_MODELS`, `SOURCE_FOR_TIER`):

| Tier | Default model ID | UI source label suffix |
|------|------------------|-------------------------|
| `fast` | `nvidia/Nemotron-3_5-Lightning` | `nemotron-lightning` |
| `write` | `nvidia/nemotron-3-super-120b-a12b` | `nemotron-super` |
| `deep` / `judge` | `nvidia/Nemotron-3-Ultra-550b-a55b` | `nemotron-ultra` |

Daily token caps, USD estimates, and `NAVIGUIDE_LLM_MODE` (`off` | `on-demand` | `all`) are enforced in [`llm_budget.py`](naviguide-simulator/server/llm_budget.py) before any paid call.

### Where Nemotron is used (server modules)

| Module | Role |
|--------|------|
| [`story_cascade.py`](naviguide-simulator/server/story_cascade.py) | Central `cascade_text()` / `translate()`; `filter_numbers()` on LLM output; 24h LLM cache. |
| [`story_cache.py`](naviguide-simulator/server/story_cache.py) | Briefing stories via `cascade_text(tier="write")`. |
| [`logbook_chat.py`](naviguide-simulator/server/logbook_chat.py) | Logbook Q&A; tier `fast` vs `judge` (Ultra) routing; embeddings via Token Factory. |
| [`escale_api.py`](naviguide-simulator/server/escale_api.py) | Port-of-call paragraphs (`tier="fast"`). |
| [`escale_watch.py`](naviguide-simulator/server/escale_watch.py) | Tavily search/extract summaries (`tier="fast"`). |
| [`film_script.py`](naviguide-simulator/server/film_script.py) | Film moment selection (fast), chapter writing (write), editing/judging (judge/Ultra). |
| [`plan_review.py`](naviguide-simulator/server/plan_review.py) | Plan review comments (`tier="write"`). |
| [`official_store.py`](naviguide-simulator/server/official_store.py) | Written film sources `nemotron-super-token-factory`, reviewed `nemotron-super-reviewed-ultra`. |
| [`truth_judge.py`](naviguide-simulator/server/truth_judge.py) | Gold PoE: Tavily extract + Ultra `judge` tier for stale claims. |

**Tavily** is not a Nebius service; it is integrated beside Nemotron ([`tavily_client.py`](naviguide-simulator/server/tavily_client.py), [`escale_watch.py`](naviguide-simulator/server/escale_watch.py), [`truth_judge.py`](naviguide-simulator/server/truth_judge.py)) with budgets in [`llm_budget.py`](naviguide-simulator/server/llm_budget.py).

### UI disclosure

When the cascade returns a Nemotron Token Factory source, the UI shows translated labels and official **NVIDIA / Nebius / Token Factory** marks — [`naviguide-simulator/src/utils/llmSourceLabel.js`](naviguide-simulator/src/utils/llmSourceLabel.js), assets under [`naviguide-simulator/src/assets/brand/`](naviguide-simulator/src/assets/brand/) (usage notes in [`SOURCES.md`](naviguide-simulator/src/assets/brand/SOURCES.md)).

### Safety: no invented numbers

`filter_numbers()` in [`story_cascade.py`](naviguide-simulator/server/story_cascade.py) (also used from [`logbook_chat.py`](naviguide-simulator/server/logbook_chat.py)) drops sentences that introduce figures not present in the fact pack.

---

## Other Nebius services

**In this repository’s runtime code, only Nebius Token Factory is integrated** (HTTP API bases above, `NEBIUS_API_KEY`). Archived hackathon docs mention optional **Token Factory Data Lab** and **Sandboxes** as stretch goals ([`docs/archives/hackathon-nebius-nvidia.en.md`](docs/archives/hackathon-nebius-nvidia.en.md)); there are **no** calls to Nebius AI Cloud Jobs, Endpoints, or DevPods in `naviguide-simulator/server/`.

---

## Relation to Blue Intelligence

[Blue Intelligence](https://blueintelligence.online) holds curated maritime source data (marinas, harbour masters, Gold ports of entry, MPAs, science layers, projects). **NAVIGUIDE does not share its database.**

The simulator reads BI over HTTP:

- Default base URL: [`naviguide-simulator/server/main.py`](naviguide-simulator/server/main.py), [`ici_engine.py`](naviguide-simulator/server/ici_engine.py), [`bi_proxy.py`](naviguide-simulator/server/bi_proxy.py) (`BI_API_URL` or `https://blueintelligence.online/api`).
- Vite dev proxy: [`naviguide-simulator/vite.config.js`](naviguide-simulator/vite.config.js) (`BI_PROXY_TARGET`).

Full API and MongoDB live in the **[Berry-Mappemonde/Blue-Intelligence](https://github.com/Berry-Mappemonde/Blue-Intelligence)** repository (OVH deployment). This split is documented in [`docs/PLAN_SEPARATION_DEPOTS.md`](docs/PLAN_SEPARATION_DEPOTS.md).

---

## License

- **Code:** [MIT](LICENSE) / [Apache-2.0](LICENSE-APACHE) (dual-licensed; choose one).
- **Map and data layers:** retain upstream licences (OpenStreetMap, EMODnet, GEBCO, etc.—see simulator README).
- **Nemotron model weights:** NVIDIA model licence (inference via Token Factory/NIM under your API keys).

---

## Links

| Resource | URL |
|----------|-----|
| Live app | [https://naviguide.fr](https://naviguide.fr) |
| Blue Intelligence API | [https://blueintelligence.online/api](https://blueintelligence.online/api) |
| Blue Intelligence repo | [https://github.com/Berry-Mappemonde/Blue-Intelligence](https://github.com/Berry-Mappemonde/Blue-Intelligence) |
| Hackathon | [https://nebiusglobalaihackathon.devpost.com/](https://nebiusglobalaihackathon.devpost.com/) |
| Nebius Token Factory docs | [https://docs.tokenfactory.nebius.com/](https://docs.tokenfactory.nebius.com/) |
| Docs index | [`docs/README.md`](docs/README.md) |
| Archive monorepo (history) | [Berry-Mappemonde/Blue-Intelligence-Map](https://github.com/Berry-Mappemonde/Blue-Intelligence-Map) |

---

### Résumé (français)

**NAVIGUIDE** est en ligne sur [https://naviguide.fr](https://naviguide.fr). Chaque merge sur `main` déploie cette version. Le dépôt contient le simulateur (carte Leaflet, moteur d’escale, film, journal) et son serveur FastAPI ; l’API **Blue Intelligence** reste sur [blueintelligence.online](https://blueintelligence.online/api) (autre dépôt). Les textes générés passent d’abord par **Nebius Token Factory** avec les modèles **NVIDIA Nemotron** (Lightning / Super / Ultra), puis des replis documentés dans le code. Installation et variables d’environnement : voir les sections ci-dessus et [`naviguide-simulator/server/.env.example`](naviguide-simulator/server/.env.example).

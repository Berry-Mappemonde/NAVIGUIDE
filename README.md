# Blue Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

**Blue Intelligence** turns the living web of maritime data into a usable geospatial database, shown on an interactive world map.

Published at **[blueintelligence.online](https://blueintelligence.online)** — a [Berry-Mappemonde](https://berrymappemonde.org) project. <!-- pragma: allowlist secret -->

LLM completions go through OpenAI-compatible APIs: **NVIDIA NIM** and **[Nebius Token Factory](https://tokenfactory.nebius.com/)**, including the **[NVIDIA Nemotron](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)** family (Nano, Super, Ultra, Lightning). Code in this repository is **dual-licensed MIT / Apache-2.0** (`LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE`).

> [!WARNING]
> **Not for navigation**
>
> Blue Intelligence aggregates participatory data (OpenStreetMap) and
> automatic extractions from public sources. No hydrographic or customs
> authority verifies them: marinas, harbour masters, ports of entry, MPAs
> and the “Nautical chart” basemap are indicative only. Always check
> official nautical charts and government publications before any decision
> at sea. The climatology atlas (7th mode) is a monthly statistic over a
> written period, **not** tomorrow’s wind.

## The seven modes

| Mode | Colour | Content |
|------|--------|---------|
| **Projects** | cyan | ~4,500 marine conservation projects discovered and extracted automatically from major foundation portals (web-agent swarm + LLM) |
| **Marinas** | red | Worldwide `leisure=marina` directory (OpenStreetMap), `osm_id` identity, deterministic Google Maps link. Larger point if a `/maps/place/` sheet was found (TinyFish Search / OSM tag) — none are filtered out. Anchorages stay on the route corridor. Outside Formalities / PoE. |
| **Harbour masters** | sky | Worldwide OSM `office=harbour_master` offices + SHOM CATSCF=6 overlay (France). Phone and VHF read from tags, then official sites. Not attached to marinas. |
| **Formalities** | amber | The ~285 worldwide Exclusive Economic Zones (Marine Regions v12) and their official recreational **Ports of Entry**, extracted from government sources |
| **MPA** | green | ProtectedSeas Navigator polygons + **two separate URLs**: manager site (`manager_url`) and visit / entry procedures (`visit_url`). The visit URL is never a copy of the ProtectedSeas Website. |
| **Science** | violet | Oceanographic datasets placed on the map with a direct link to their portal sheet: **Sextant/SISMER** (Ifremer) and **ODATIS** catalogues (GeoNetwork JSON API), SeaDataNet **EDMED** (SPARQL), active **Argo** floats (Coriolis ERDDAP) and **CSR** campaign tracks (Ifremer SPARQL). EMODnet WMS layers (bathymetry, seabed, cables). EMODnet approach depth in marina/anchorage popups. Structured APIs only — no LLM, no scraping, non-destructive upsert. |
| **Climatology** | teal `#2dd4bf` | Sourced monthly atlas (`kind: climatology`): wind roses, P50/P90 swell, surface current, IBTrACS tracks. Snapshots precomputed off the VPS, served here. **Not** a GFS/IFS forecast. NAVIGUIDE consumes the same files without painting them. Review / Gold not wired (same as Science). |

Plus an **operations console** (batch triggers, telemetry, KPIs), a **Review** tab (human review then Gold — see `docs/CAHIER_DES_CHARGES_REVIEW.md` and `docs/CONTRATS_REVIEW_PAR_MODE.md`) and contextual GeoJSON export/import.

## Basemaps and seamap practices

Three basemaps cycle via the header button: **dark**,
**light** (Esri raster) and **Nautical chart** — the
[Open Waters: Seamap](https://github.com/openwatersio/seamap) vector style
(IALA marks, lights, Seascape depths), rendered by `maplibre-gl-leaflet`
loaded on demand. A “Not for navigation” warning is shown on this
basemap. In production, `infra/vps/seamap/` self-hosts the dated PMTiles
archive (~26 GB), style and sprites on the VPS.

Marina popups carry **service badges**: the colour answers a skipper
question (Berthing / Provisions / Technical / Ashore); the tooltip lists
the OSM tags that support it — nothing is invented.

The repository also follows seamap engineering practices:

- **Versioned GeoJSON exports** — each export carries `metadata` (dated
  version + sha256 fingerprint, counts, licence, warning); dated
  **immutable** snapshots via `POST /api/export/snapshot` (`backend/exports/`).
- **Weekly rebuild** — `.github/workflows/weekly-data-build.yml`
  archives every Monday the 7 exports + an overlay PMTiles in a
  `data-<YYYY-MM-DD>` release, immutable by construction.
- **Tag catalogue** — `docs/CATALOGUE_SEAMARK.md` +
  `backend/data/seamark_catalog.json`; audit via `scripts/audit_tags.py`
  (reports in `docs/audits/`).
- **Locked layer order** — `frontend/src/components/map/layerOrder.js`
  is frozen by a jest test (`npm test`).

The plan that puts these pieces into **four tracks** (control, chart,
official hydro, satellite) and says what benefits Blue Intelligence
vs the NAVIGUIDE simulator: `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.

## Architecture

```
blue-intelligence/
├── backend/            FastAPI (Python 3.11+) + MongoDB
│   ├── server.py       Entry point, REST /api/* endpoints
│   ├── llm_core.py     LLM adapter — NIM (completions) or OpenRouter; :online stays OpenRouter
│   ├── pipeline.py     Discovery/extraction swarm for marine projects
│   ├── poe.py          [EEZ → Ports of Entry] pipeline (poe_routes.py = endpoints)
│   ├── marinas.py      Worldwide OSM leisure=marina dump; anchorages = route corridor
│   ├── enrichment.py   Marina enrichment (OpenRouter → TinyFish → OSM tags)
│   ├── geo.py / geo_core.py       Geocoding, coastal snap, spatial validation
│   ├── extract_core.py            Parse cascade N1 trafilatura → N2 Readability → N3 TinyFish
│   ├── dedup_core.py / rag_core.py / ml_core.py   Dedup, local RAG, local ML models
│   ├── zee.py          Official-route EEZ crossings
│   ├── data/           Embedded references (route, EEZ, curated marinas)
│   └── models/         Trained local ML models (gatekeeper, SERP classifier, NER)
├── frontend/           React (CRA) + Leaflet + Tailwind
│   └── src/components/ MapView, BatchHub (audit), SettingsPanel, per-mode panels
├── docs/               PRD, Projects spec, Formalities (PoE) spec, Review spec, per-mode Review contracts, rules/parameters, architecture, NVIDIA LLM audit (`nvidia-llm-audit.md`), carto tracks plan (`PLAN_IMPLEMENTATION_FILIERES_CARTO.md`)
├── infra/              Self-hosted SearXNG (`searxng/`) + OVH VPS production deploy (`vps/`)
├── scripts/            Ops tooling (backup restore)
├── naviguide/          NAVIGUIDE — expedition route planner (standalone app, see `naviguide/README.md`)
└── naviguide-simulator/  Simulator (off-prod, simulator.naviguide.fr) — `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` (EN: `.en.md`); climo clock `PLAN_IMPLEMENTATION_SIMULATION_A.md`; virtual boat `PLAN_IMPLEMENTATION_SIMULATION_B.md`
```

### Artificial intelligence: NIM / Token Factory, Nemotron, OpenRouter for the web

JSON completions (gatekeeper, extraction, geocoding, PoE judge) go through an **OpenAI-compatible** API: **[NVIDIA NIM](https://build.nvidia.com)** if `NVIDIA_API_KEY` is set, otherwise **[OpenRouter](https://openrouter.ai)**. The same HTTP contract also serves **[Nebius Token Factory](https://tokenfactory.nebius.com/)** (endpoint `https://api.tokenfactory.us-central1.nebius.com/v1/`) to run **NVIDIA Nemotron** models without a GPU cluster. Grounded web search (`:online`) stays on OpenRouter:

- **Completions**: `NVIDIA_API_KEY` (hosted NIM — per-usage chains in `nvidia.CHAINS`) if present; otherwise OpenRouter;
- **Nemotron**: catalogue ids `nvidia/nemotron-*` (Nano 30B, Super 120B, Ultra 550B, Lightning 30B, Omni) — pinnable via `NVIDIA_MODEL` / `NVIDIA_MODEL_CHAIN_*`; the persisted label is `nvidia-nemotron` (`backend/app/core/nvidia.py`);
- **Token Factory**: [Nebius Token Factory](https://tokenfactory.nebius.com/) serves the same Nemotron models behind the OpenAI-compatible API (`https://api.tokenfactory.us-central1.nebius.com/v1/`); the NIM adapter already speaks that contract;
- **Web search**: `OPENROUTER_API_KEY` only (`:online`) — NIM / Token Factory have no web plugin;
- **OpenRouter model**: `OPENROUTER_MODEL` (default `openai/gpt-4o-mini`);
- **Without a key**, the app still works in degraded mode: keyword heuristics + local ML models (TF-IDF, spaCy NER) with no AI network calls.

The pipeline **never invents content**: every field not found in the sources stays `null`; every port of entry is geocoded then spatially validated inside its EEZ polygon.

## NAVIGUIDE (monorepo)

The `naviguide/` folder hosts **NAVIGUIDE**, the Berry-Mappemonde expedition route planner (React Vite + MapLibre GL; FastAPI services: land-avoiding routing, Copernicus data, LangGraph multi-agent orchestrator, polars). The `naviguide-berry-mappemonde` repository was merged here with its full history, cleaned along the way (`naviguide-api/venv` removed from the entire history).

- **Standalone app**: startup, dependencies and deploy are separate from Blue Intelligence — see `naviguide/README.md` (`naviguide/naviguide_workspace/start_local.sh` to run everything locally).
- **Production**: [www.naviguide.fr](https://www.naviguide.fr), hosted on the same OVH VPS as blueintelligence.online — see `infra/vps/README.md` and `infra/vps/naviguide/`.
- **Blue Intelligence layers**: the NAVIGUIDE map shows the 5 modes (Projects, Marinas, Harbour masters, Ports of Entry, MPA) via `GET /api/export/*` GeoJSON exports, consumed same-origin on the `/bi/*` path (Vite proxy in dev, nginx in production).

## Local startup

### Prerequisites

- Python 3.11+, Node.js 18+, local MongoDB (or MongoDB Atlas)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium   # local JS page rendering (PoE pipeline)
cp .env.example .env        # then fill in the variables (see below)
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env        # leave REACT_APP_BACKEND_URL empty (same-origin)
npm start                   # http://localhost:3000 (dev, hot reload)
```

### Cloud Agent preview / remote access (single port)

To view the app from the Cursor UI (**Ports** or **Browser** tab) without a client-side `localhost` problem:

```bash
bash .cursor/preview.sh     # build + UI + API on http://localhost:8001
```

Open port **8001** (“Application UI + API”) in the **Ports** tab of the Cursor agent page, then click **Open in Browser**. UI and API share the same origin — no network call to `localhost:8001` from the remote browser.

The CRA dev server (port 3000) remains available for hot reload during development.

## Environment variables (secrets)

### `backend/.env`

| Variable | Required | Role |
|----------|----------|------|
| `MONGO_URL` | ✅ | MongoDB connection string |
| `DB_NAME` | ✅ | MongoDB database name |
| `CORS_ORIGINS` | ✅ | Allowed origins, comma-separated (`https://blueintelligence.online` in prod) |
| `NVIDIA_API_KEY` | recommended | NVIDIA NIM key (`nvapi-…`) — per-usage chains (`nvidia.CHAINS`), including a [Nemotron](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/) id pinned via `NVIDIA_MODEL` |
| `LLM_PROVIDER` | optional | `auto` (default: NVIDIA if a key is set), `nvidia`, or `openrouter` |
| `NVIDIA_MODEL` | optional | Chain prefix (except `legal`); default already first: Pro-0813. For Nemotron: `nvidia/nemotron-3-nano-30b-a3b` (or Super / Ultra / Lightning) |
| `NVIDIA_MODEL_SECONDARY` | optional | Replaces Muse **wherever it appears** in `CHAINS` (3rd) |
| `NVIDIA_MODEL_LEGAL` | optional | Head of the `legal` chain (default `moonshotai/kimi-k3`) |
| `NVIDIA_MODEL_CHAIN_JUDGE` | optional | Full override, comma-separated ids (same for `_EXTRACT`, `_PAGE`, …) |
| `OPENROUTER_API_KEY` | recommended | OpenRouter key — `:online` web search and fallback if NIM is absent |
| `OPENROUTER_MODEL` | optional | OpenRouter model (default `openai/gpt-4o-mini`) |
| `ANTHROPIC_API_KEY` | optional | Claude Haiku 4.5 for PoE extraction only — inert if `CLAUDE_BUDGET_USD` (or the UI cap) is 0 |
| `CLAUDE_BUDGET_USD` | optional | Local Claude cap (USD). Stops at 90%. Default 0 = Claude off |
| `TINYFISH_API_KEY` | optional | TinyFish agent (projects swarm & marina enrichment — the PoE pipeline uses local Playwright rendering) |
| `GEONAMES_USERNAME` | optional | GeoNames account (parallel Nominatim ∥ GeoNames geocoding). On [geonames.org/manageaccount](https://www.geonames.org/manageaccount): **Click to enable** the free webservice — without that the API returns error 10 and the pipeline disables GeoNames for the process | <!-- pragma: allowlist secret -->
| `SEARXNG_URL` | optional | Self-hosted SearXNG instance (see `infra/searxng/`) — preferred over public instances for PoE search |
| `RESEND_API_KEY` | optional | Project-report emails (Resend) |
| `SENDER_EMAIL` / `REPORT_RECIPIENT` | optional | Sender / recipient for reports |

### `frontend/.env`

| Variable | Required | Role |
|----------|----------|------|
| `REACT_APP_BACKEND_URL` | optional | Public backend URL (no trailing slash). **Leave empty for same-origin mode**: in dev the CRA proxy routes `/api` to `localhost:8001`; in production the reverse proxy serves `/api/*`. Set only if the backend lives on another domain |

## Deploy on blueintelligence.online

Self-hosted production on an OVH VPS (Ubuntu) behind Cloudflare — full
procedure, idempotent scripts and runbook in **`infra/vps/README.md`**:

1. **Application**: uvicorn (`SERVE_FRONTEND=1`, local port 8001) serves the built UI **and** the API, behind the VPS nginx (Let's Encrypt TLS). systemd service `blue-intelligence`.
2. **MongoDB**: MongoDB Community 8.0 self-hosted on the VPS (`127.0.0.1` only, authentication on) — end of Atlas M0 throttling. Indexes are created automatically at startup. Daily `mongodump` backups (14-day rotation).
   ⚠️ **The VPS is the live database since the 2026-09-10 DNS cutover**: never re-run `infra/vps/sync-from-atlas.sh` (Atlas is frozen at the pre-cutover state; the script is locked). Restore = local backups only.
3. An alternate hosting (static build + `/api/*` reverse proxy + Atlas) remains possible: see the environment variables above.

## API (overview)

- `GET /api/` — service health · `GET /docs` — interactive OpenAPI
- `GET /api/projects` · `GET /api/funders` · `GET /api/categories` — Projects mode
- `POST /api/swarm/deploy` · `GET /api/swarm/status` — discovery pipeline
- `GET /api/marinas` · `POST /api/marinas/build` · `POST /api/marinas/enrich-batch` — Marinas mode
- `GET /api/capitaineries` · `POST /api/capitaineries/build` · `POST /api/capitaineries/enrich-batch` — Harbour masters mode
- `GET /api/poe/zones` · `GET /api/poe/ports` — Formalities mode (`POST …/generate` and `generate-batch`: 410)
- `POST /api/poe/runs` · `GET /api/poe/runs/{id}/status` · `GET /api/poe/runs/{id}/diff` · `GET /api/poe/runs/{id}/report` — versioned PoE runs
- `GET /api/export/{geojson|marinas.geojson|anchorages.geojson|capitaineries.geojson|amp.geojson|poe.geojson|route.geojson}` — versioned GeoJSON exports (`metadata` block)
- `POST /api/export/snapshot` · `GET /api/export/snapshots[/{date}/{file}]` — dated immutable snapshots

## Initial data (seed)

The `seed/` folder holds production GeoJSON exports:

```bash
# Projects (4,463) — via the API
curl -X POST http://localhost:8001/api/import/geojson \
  -H "Content-Type: application/json" --data-binary @seed/projects.geojson
# Ports of Entry (1,169) + zone statuses — via the script
python scripts/restore_data.py poe seed/ports_of_entry.geojson
python scripts/restore_data.py zones
```

The 285-EEZ referential is built from the Console (Formalities mode → “Build EEZ referential”).

## Tests

```bash
cd backend && source .venv/bin/activate
python -m pytest tests/ -x -q          # some tests require the server running (REACT_APP_BACKEND_URL)
```

## Licence

Blue Intelligence **code** (this repository) is **dual-licensed MIT / Apache License 2.0**. You may choose either:

- [MIT License](LICENSE-MIT) — also copied into [`LICENSE`](LICENSE) (the file GitHub displays)
- [Apache License 2.0](LICENSE-APACHE)

`SPDX-License-Identifier: MIT OR Apache-2.0`

**Weights** of [NVIDIA Nemotron](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/) models invoked via NIM or [Token Factory](https://tokenfactory.nebius.com/) remain under the [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/) — distinct from the code licence.

Cartographic data (OSM, Marine Regions, Seamap, etc.) keep their original licences, listed below.

## Data & attributions

- **EEZ**: Flanders Marine Institute — [Marine Regions](https://marineregions.org), Maritime Boundaries v12 (CC-BY 4.0)
- **Marinas / geocoding**: © [OpenStreetMap](https://openstreetmap.org) contributors (ODbL), Nominatim, Overpass, GeoNames
- **Route**: official Berry-Mappemonde expedition route
- **“Nautical chart” basemap**: © [Open Waters: Seamap](https://openwaters.io/charts/seamap) (CC-BY 4.0) on data © OpenStreetMap contributors (ODbL), [Seascape](https://github.com/openwatersio/seascape) bathymetry, [VersaTiles](https://versatiles.org) basemaps, relief © Mapterhorn
- **MPA**: ProtectedSeas Navigator (centroids and metadata) · **France harbour masters**: SHOM (Licence Ouverte Etalab) · **United States**: NOAA ENC Direct to GIS

### Map library licences

100% permissive chain, verified: `leaflet` (BSD-2), `maplibre-gl` (BSD-3),
`@maplibre/maplibre-gl-leaflet` (ISC), `pmtiles` (BSD-3). The npm package
`@openwaters/seamap` is **GPL-3.0 and intentionally unused**: the
frontend consumes the served `style.json` (CC-BY 4.0), as data.

> ⚠️ Formalities-mode information is **indicative** — always check with the authorities before departure. The “Nautical chart” basemap is **not for navigation** (see the warning at the top of this document).

# Implementation plan — `naviguide-simulator/` stage 1

Workshop document. It locks **how to place the folder** in this repo, and
**what to code first**.

Version **3.0** — 13 September 2026.

**Français :** [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)  
**Hackathon briefing (EN) :** [hackathon-nebius-nvidia.en.md](./hackathon-nebius-nvidia.en.md)

**What 3.0 changes vs 2.0**

The skipper locked the cockpit: keep the **boat engine** and the
**film**, drop what the project (briefing / `ici()` pack) will
replace, and drop what a simulated expedition does not need.

| 2.0 decision (cancelled) | 3.0 decision (this one) |
|---|---|
| Polar **chat** (`POST /polar/chat`, `PolarChatSection`) | Polar **engine + upload + VMG** only. The story = the project |
| **4 simulation chats** (Ports / Safety / Weather / Cruisers) | **Forbidden.** Do not copy `AgentPanel` or `/agents/*` |
| GeoJSON / KML import + GeoJSON / KML export | **Forbidden.** Useless here. Custom route = **draw + searoute** |
| Backend that copies the 4 SSE agents | Backend = searoute + polar (no chat) + proxies + wind |

What **does not change** since 2.0:

- extractable subfolder, **Leaflet** (no MapLibre) ;
- prod `naviguide.fr` / `blueintelligence.online` **untouched** ;
- **searoute** for Berry **and** for “draw your own route” ;
- **full** polar engine (parse, 181×61 grid, VMG, upload) ;
- NAVIGUIDE UI / UX **except** the exclusions above ;
- `ici()` still an **empty pack** (stage 2).

Stages 2 to 6 (real pack, EEZ events, Gold, Tavily, Nemotron) are
recalled so we do **not** start them too early — **they are not
delivered here**.

**Contents**

1. In one sentence
2. Why this stage exists
3. Skipper contract (in / out)
4. Vocabulary
5. Architecture decisions (locked)
6. Target tree
7. Copy / adapt / invent / throw away
8. Simulator backend
9. Polar engine (no chat)
10. NAVIGUIDE UI / UX (what remains)
11. BerryCard without import
12. Leaflet map and panes
13. Berry film: searoute, boat, fallback
14. Draw your own route
15. Layer pills
16. Stub `ici()`
17. Data, ports, variables
18. Build order (1.0 → 1.9)
19. Files touched / forbidden
20. Recipe
21. Risks
22. Handoff to stage 2
23. Documents and files this plan inherits

---

## 1. In one sentence

Create `naviguide-simulator/` in **this** repo: the NAVIGUIDE
**cockpit** (Berry route, draw your own route, polars, simulation),
projected on a **Leaflet** map with layer pills — **without** the
4 chats, **without** polar chat, **without** file import/export,
**without** touching `naviguide.fr` or `blueintelligence.online`.

---

## 2. Why this stage exists

The hackathon product is not a second Blue Intelligence. It is the
**film**: the boat moves, you see the cockpit map, and later a small
“from here” pack feeds **one** story.

Without stage 1 there is no cockpit, no position, no pills. The `ici()`
engine (stage 2) would have nothing to wrap around.

The 4 chats Ports / Safety / Weather / Cruisers and polar chat are the
**old spoken cockpit**. The project replaces them: one event briefing,
later fed by the pack. Copying them now rebuilds what we decided to
drop.

GeoJSON / KML import / export serves an operator or another program.
Here the route comes from **Berry** or **pencil + searoute**. Not from
a file.

Stage 1 **does not call** Tavily or Nemotron. It prepares:

- the **projector** (Leaflet + legend) ;
- the **film** (Berry route, boat, draw) ;
- the **boat engine** (searoute + polar), so ETA and the track are the
  skipper’s, not a 7-knot straight line ;
- a Briefing **slot** (local text), ready for the story.

---

## 3. Skipper contract (in / out)

### We ship

At the end of stage 1, locally:

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010 --reload   # one Terminal
npm install && npm run dev                     # another Terminal
```

Open `http://localhost:5174`. You recognise NAVIGUIDE, on Leaflet:

1. **Two 320 px panels**: left (expedition) and right (language,
   theme, stats, polars). FR / EN, dark / light.
2. **BerryCard**: Berry route, **draw your own route**, continue,
   finish, delete, Berry ↔ custom toggle. **No** GeoJSON / KML buttons.
3. **Berry route** computed **leg by leg via searoute** (same stop
   logic as `App.jsx`: overland Berry↔La Rochelle, skip Marigot /
   Halifax, Halifax↔SPM maritime, Cayenne→Papeete). Spinner + progress
   pill.
4. **Simulation mode**: Previous / Next, boat snapped to the route
   (`useLegContext`), drag, `flyTo`. **No** `AgentPanel`.
5. **Full polar engine**: Leopard 46 CSV auto-loaded, PDF / CSV / XLSX
   drop, 181×61 grid on the server, VMG table. **No** polar chat.
6. **Draw your own route**: map clicks → searoute `GET /route` (not a
   chord), undo / redo, green banner, Finish → the route becomes
   active.
7. **Ten layer pills** (EEZ, WPI, Marks, Projects, Marinas, Harbor
   offices, PoE, MPA, Science, Climatology) — Leaflet drawing, several
   ON together.
8. **Route click** → point wind / wave / current
   (`POST /wind|wave|current`).
9. Single **Briefing** (24 h local cache, optional orchestrator,
   otherwise local text / draw hint). This is **the project slot**.
10. Stub `ici()` wired on every step (typed JSON, still empty on EEZ).
11. Folder `README.md`: how to run, ports, “prod untouched”, what does
    not exist yet.

**If the simulator backend is down**: the Berry route still draws from
`public/route.geojson` (internal copy of `backend/data/route.geojson`).
This file is **not** a skipper import. Draw, polar and EEZ / WPI
proxies show an honest error. The film must not go black.

Prod does not change.

### We do not ship

| Forbidden in stage 1 | Why |
|---|---|
| **4 chats** Ports / Safety / Weather / Cruisers (`AgentPanel`, `/agents/*`) | Replaced by the project (briefing / `ici()`) |
| **Polar chat** (`PolarChatSection`, `POST /api/v1/polar/chat`) | Same: the story is not a Q&A on the VMG table |
| **GeoJSON / KML import** (`parseGeoJSON`, `parseKML`, file inputs) | Useless: Berry or pencil |
| **GeoJSON / KML export** (`buildGeoJSON`, `buildKML`, Download buttons) | Useless in this project |
| Console, Review, Swarm, 6 operator modes | Blue Intelligence UX, not the cockpit |
| MapLibre map / “nautical chart” PMTiles | We change projector |
| Weather-routing isochrones (port 3010) | Another engine, not in prod |
| LangGraph orchestrator **inside** the folder | The briefing **calls** the existing one if it is up; else local text |
| `polar_agent.py` (Deploy AI / Claude Opus) | Dead path |
| Tavily, Nemotron, Token Factory | Stages 5–6 |
| Spatial queries “in this EEZ / 30 nm” | That is real `ici()` = stage 2 |
| BI **operator** imports / exports | We **read** the same URLs, we write nothing |
| Editing `frontend/`, `backend/`, `naviguide/`, `infra/vps/` | Prod does not move |
| `react-leaflet` | BI hooks talk to a bare `L.Map` |
| `searoute-js` (npm, **never used** in `App.jsx`) | The real engine is Python `searoute==1.4.3` |
| `llm_cascade.py` | No polar chat and no agents in this folder |
| Dumping 4,500 projects into a prompt | The pack LLM does not exist here yet |

**GeoJSON nuance (do not confuse with skipper import/export):**

| Yes (internal) | No (skipper) |
|---|---|
| `customRoute` = in-memory `FeatureCollection` after “Finish” | Open a `.geojson` / `.kml` from disk |
| `public/route.geojson` = **fallback** if searoute is down | “Export” / “Import” button |
| Map layers read as GeoJSON (`/bi/export/*`) | Download the displayed route |

---

## 4. Vocabulary

| Word | Meaning here |
|---|---|
| **Film** | What the skipper sees: two sidebars, route, boat, pills, draw |
| **Projector** | The map: Leaflet, not MapLibre |
| **Legend** | ON/OFF pills (EEZ, WPI, Marks, …) |
| **Boat engine** | searoute (the track) + polar (speed / VMG) |
| **The project** | Later: event story from `ici()`. In stage 1: **one** Briefing panel |
| **Backpack / `ici()`** | Small JSON around the boat. Stage 1 = **empty** pack (except maybe boat name if polar is loaded) |
| **Official route (fallback)** | `backend/data/route.geojson` → `public/route.geojson` if searoute is down. Not an import |
| **Escale** | Flagged stop (La Rochelle, Ajaccio…). An intermediate point is not one |
| **Gold** | Reviewed Formalities fiche. Unused in stage 1 |
| **Prod** | `blueintelligence.online` and `naviguide.fr` |

---

## 5. Architecture decisions (locked)

### 5.1 A subfolder, not a fork

```
Blue-Intelligence-Map/
├── frontend/                 # BI prod — forbidden
├── backend/                  # API prod — forbidden
├── naviguide/                # NAVIGUIDE prod — forbidden
├── naviguide-simulator/      # NEW, extractable later (hackathon)
└── docs/
    ├── PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md  # this file
    └── hackathon-nebius-nvidia.en.md
```

Later: `git subtree split` (or a clean copy) to the hackathon repo.
So **no** runtime import like `../../frontend/src/...` or
`../../naviguide/...`: we **copy** modules, we do not glue the two
apps.

### 5.2 Stack

| Choice | Like… | Not like… |
|---|---|---|
| Vite 7 + React 19 + Tailwind 4 | `naviguide/naviguide-app` | CRA in `frontend/` |
| Bare Leaflet 1.9 (`L.map`) | `frontend/src/components/MapView.js` | MapLibre / `react-map-gl` |
| FastAPI **in the folder** (`server/`, port **8010**) | extracts from `naviguide-api` + `polar_api` **without chat** | calling prod, ports 8000 / 8004 |
| Vite port **5174** | — | 5173 (NAVIGUIDE) and 3000 (CRA) |
| FR first, then EN | NAVIGUIDE i18n (useful keys) | randomly amputated keys |

Leaflet **without** `react-leaflet`: Blue Intelligence already creates
the map by hand. Glueing that into `react-leaflet` would rewrite
everything.

### 5.3 Route: searoute first, official GeoJSON as fallback

NAVIGUIDE today calls `GET /route?start_lat=…` **leg by leg**
(`App.jsx` ~L.523–676, batches of 4). That is searoute + land
avoidance (`searoute_with_exact_end` → `avoid_land` → densify →
sanitize).

Stage 1 **replays that film**:

1. Stops come from `ITINERARY_POINTS` (copy of
   `naviguide-app/src/constants/itineraryPoints.ts`, ~41 points,
   PNG flags).
2. Legs are **the same** (skip Marigot / Halifax / SPM / Cayenne,
   insert Marigot→Cayenne, Halifax↔SPM, Cayenne→Papeete, overland
   Saint-Maur↔La Rochelle).
3. Each sea leg = `GET /route` on the **simulator backend**.
4. A→B orientation (`orientCoords`): searoute may return B→A.
5. If the backend is down **or** a leg fails: fall back (whole route,
   or leg by leg) to `public/route.geojson` via `routeFromOfficial.js`.

**Consequence:** the film runs **without** prod `naviguide-api`. The
simulator has **its** `/route`. Do not proxy to `:8000` “to go faster”:
that would glue the folder to prod and break hackathon extraction.

### 5.4 Polar: the live engine, not the chat, not the dead LangGraph

“Full polar engine **except the chat**” = what NAVIGUIDE uses to
**compute**, not to **talk**:

| Source file | Role | In stage 1 |
|---|---|---|
| `naviguide/polar_agent/polar_engine.py` | Parse PDF / CSV / XLSX, interpolation, 181×61 grid, VMG | **Yes** |
| `naviguide/naviguide_workspace/polar_api/main.py` — `upload`, `GET /{id}`, `GET /{id}/summary` | Persistence + summary | **Yes** |
| `polar_api` — `POST /chat`, `_build_polar_system_prompt`, `_polar_fallback_reply` | LLM Q&A | **No** |
| `naviguide-app/.../Sidebar.jsx` — `PolarChatSection` | Chat UI | **No** |
| `ExportSidebar.jsx` — drop + VMG table + auto-Leopard 46 | Engine UI | **Yes** |
| `naviguide/polar_agent/polar_agent.py` | Deploy AI, Claude Opus | **No** |
| `llm_cascade.py` | NIM → OpenRouter → Claude cascade | **No** (no local chat at all) |

The front **does not download** the 181×61 grid: only `vmg_summary`
(TWS 8 / 10 / 12 / 16 / 20 / 25). That is already the right “pack”
for later.

**Film ETA:** `useLegContext` stays at 7 kt **until there is point
wind**. Once `POST /wind` answers, read `polar.speed(twa, tws)` and
pass `speedKnots` to the hook. Without a loaded polar: 7 kt. Do **not**
wire isochrone weather-routing.

### 5.5 Layers: same URLs, new drawing, not the “one mode” hooks

Blue Intelligence shows **one** mode at a time. Copying those hooks
as-is would reproduce “one mode at a time”.

**Do not import them.** **Steal** styles / panes / popups / canvas,
**rewrite** the glue: button ON → fetch once → `map.addLayer`. Several
layers ON together.

The 4,500 projects stay on the **map** if the pill is on. The LLM
(later) will see only a handful via `ici()`.

### 5.6 Simulation: like NAVIGUIDE, without the 4 agents

Simulation is a **button**. OFF on load; the skipper presses it.

When ON: `SimulationPanel` only (from→to, nm, ETA, heading, Previous /
Next). No Ports / Safety / Weather / Cruisers tabs underneath.

### 5.7 One backend in the folder — required, slimmer than 2.0

`searoute-js` is in the NAVIGUIDE `package.json` and is **never
imported**. The engine is Python.

One FastAPI process (`server/`, **8010**) serves:

- `/route` (searoute + avoid-land) ;
- `/api/v1/polar/upload`, `GET /{id}`, `GET /{id}/summary` ;
- `/proxy/zee/wms`, `/proxy/zee`, `/proxy/ports`, `/proxy/seamark` ;
- `/wind`, `/wave`, `/current` (Copernicus if credentials, else
  `_sim_wind` / `_sim_wave` / `_sim_current` already in
  `naviguide-api`).

**No** `/agents/*`. **No** `/api/v1/polar/chat`. No second polar
uvicorn on 8004.

---

## 6. Target tree

```
naviguide-simulator/
├── README.md
├── package.json                 # name: naviguide-simulator
├── vite.config.js               # port 5174, proxy /route /proxy /api /bi /wind…
├── index.html
├── public/
│   ├── route.geojson            # internal fallback (copy of backend/data/route.geojson)
│   ├── Leopard46_Standard_Sails.csv
│   └── logo-*.png / flags/
├── server/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI: route + polar (no chat) + proxy + wind
│   ├── route_engine.py          # extracts from naviguide-api/main.py (searoute → sanitize)
│   ├── polar_engine.py          # copy of naviguide/polar_agent/polar_engine.py
│   ├── polar_api.py             # upload + GET + summary only
│   ├── mem_limits.py
│   ├── copernicus/              # getWind / getWave / getCurrent (copy)
│   ├── polar_data/              # persisted JSON (gitignore)
│   └── geo_data/                # optional: NE 1:10m; else global_land_mask
├── src/
│   ├── main.jsx
│   ├── App.jsx                  # ported NAVIGUIDE film: state + Leaflet, no MapLibre
│   ├── index.css
│   ├── constants/
│   │   ├── layers.js            # 10 pills
│   │   └── itineraryPoints.js   # copy (PNG → public/flags)
│   ├── engine/
│   │   └── ici.js               # stub
│   ├── hooks/
│   │   ├── useLegContext.js
│   │   ├── useSimulatorMap.js   # L.map, panes, Esri dark/light
│   │   └── useMarkerOffsets.js
│   ├── i18n/                    # fr.js + en.js (useful keys; dead keys OK)
│   ├── layers/                  # one Leaflet hook per layer + route
│   ├── components/
│   │   ├── Sidebar.jsx          # BerryCard without import, pills, sim, briefing — NO PolarChat or AgentPanel
│   │   ├── ToolsSidebar.jsx     # language, theme, stats, polar — NO export
│   │   ├── SimulationPanel.jsx
│   │   ├── LayerFichePopup.jsx  # Leaflet popup
│   │   ├── CatamaranMarker.js   # L.marker + DivIcon
│   │   └── WindDirectionArrow.jsx
│   └── utils/                   # geo, escales, simulationRoute, customRouteBriefing,
│                                # waypointsFromCollection, routeFromOfficial, layerIdentify
│                                # NO parseGeoJSON / parseKML / buildGeoJSON / buildKML
└── src/**/*.test.js
```

`ToolsSidebar.jsx` = `ExportSidebar.jsx` **without** the Download
section. Rename so we do not lie. Do **not** create `AgentPanel.jsx`.

---

## 7. Copy / adapt / invent / throw away

### We copy (almost verbatim)

| Source | Destination | Note |
|---|---|---|
| `hooks/useLegContext.js` + tests | `src/hooks/` | Zero API |
| `utils/simulationRoute.js`, `geo.js`, `escales.js`, `customRouteBriefing.js`, `waypointsFromCollection.js` + tests | `src/utils/` | `waypointsFromCollection` serves pencil **Finish**, not a file |
| `components/SimulationPanel.jsx` | same | |
| `i18n/fr.js`, `en.js`, `LangContext.jsx` | `src/i18n/` | Dead keys (export, agents, polarChat) may stay |
| `constants/itineraryPoints.ts` + `assets/img/flags/*` | `src/constants/` + `public/flags/` | `.js` is enough |
| `polar_engine.py` | `server/polar_engine.py` | |
| `polar_api/main.py`: helpers + **upload / get / summary** | `server/polar_api.py` | **Cut** everything `chat` |
| `naviguide-api/main.py`: searoute → `/route`, proxies, wind/wave/current, `_sim_*` | `server/route_engine.py` + `main.py` | Extract, **not** 1500 lines in one blob; **not** `/agents` routes |
| `frontend/.../map/constants.js` (styles) | `src/layers/styles.js` | + `TILE_URLS.light` |
| `layerOrder.js`, `points.js` | `src/layers/` | + `boat` pane |
| `backend/data/route.geojson` | `public/route.geojson` | internal fallback |
| `Leopard46_Standard_Sails.csv` + logos | `public/` | |

`ITINERARY_POINTS` **is** the Berry stop list. Flags are part of the UX.

### We adapt (new Leaflet glue + lighter cockpit)

| Idea taken from | What we change |
|---|---|
| `App.jsx` (~1800 lines) | Same route / draw / sim / briefing **state**. Drop file `handleRouteImport`. Keep activating a `FeatureCollection` **born from the pencil** (`handleCustomRoute` is a better name). MapLibre `<Map>` JSX becomes `useSimulatorMap` |
| `Sidebar.jsx` | BerryCard **without** `parseGeoJSON` / `parseKML` / file inputs. **No** `PolarChatSection`. **No** `AgentPanel` |
| `ExportSidebar.jsx` | Becomes `ToolsSidebar.jsx`: drop `downloadFile`, `buildGeoJSON`, `buildKML`, both Download buttons |
| `CatamaranMarker.jsx` | Same rotation / flip ; `L.marker` + `L.divIcon` |
| `useMarkerOffsets` | Recalc in Leaflet pixels (`latLngToLayerPoint`) |
| `MaritimeLayers.jsx` | No MapLibre `Source`/`Layer` ; Leaflet `useXLayer` hooks + Science + Climatology |
| `LayerFichePopup` | `L.popup` |
| Route / EEZ click | Leaflet hit-test |
| Polar fetch | `VITE_API_URL=''` + Vite proxy, no `localhost:8004` |

### We do not invent

No new route format. No new public prod API. No new Gold model. The
`ici()` stub locks the JSON **shape** for stage 2.

### We throw away (do not copy, even “for later”)

- `AgentPanel.jsx`
- `naviguide-api/agents/` (`custom`, `guard`, `meteo`, `pirate`,
  `deploy_ai`)
- `PolarChatSection` / `PolarChatBubble`
- `parseGeoJSON`, `parseKML`, `stemName` on the file-import path
- `buildGeoJSON`, `buildKML`, `downloadFile`, `ExportButton`
- `polar_api`: `PolarChatRequest`, `polar_chat`,
  `_build_polar_system_prompt`, `_polar_fallback_reply`
- `llm_cascade.py`, `polar_agent.py`

---

## 8. Simulator backend

Single file `server/main.py`, port **8010**.

### 8.1 `GET /route`

Contract **identical** to `naviguide-api`:

```
GET /route?start_lat=&start_lon=&end_lat=&end_lon=&check_wind=false
→ Feature | FeatureCollection
```

Pipeline to copy into `route_engine.py` (this order, already proven):

1. `sr.searoute(start, end)`
2. Prefix / suffix exact origin and destination if > 1 km
3. `avoid_land` (`global_land_mask` + NE STRtree **if** `geo_data/` is
   present)
4. `_densify_coords(max_km=75)`
5. `_sanitize_route_coords`
6. second `avoid_land`
7. bidirectional cache (`_route_cache_key`, `lru_set`)

`geo_data/ne_10m_*.shp` is **not in the repo** today. Prod code
tolerates absence (`_NE_TREE is None`). Document: high-res mask =
optional ; without shapefiles, `global_land_mask` is enough for
stage 1.

**Forbidden:** load `eez_world_map.geojson` (18 MB) “to help searoute”.

### 8.2 Polar — see §9

Mounted under `/api/v1/polar/*` **without** `/chat`.

### 8.3 Proxies and Copernicus

Copies from `naviguide-api/main.py`:

- `/proxy/zee/wms` — VLIZ `eez_boundaries` tiles
- `/proxy/zee` — WFS bbox (EEZ click)
- `/proxy/ports` — WPI
- `/proxy/seamark/{z}/{x}/{y}.png` — fallback ; the front tries
  `tiles.openseamap.org` first
- `POST /wind|/wave|/current` — Copernicus if `COPERNICUS_USERNAME` /
  `COPERNICUS_PASSWORD`, else `_sim_*`

### 8.4 What the backend **does not expose**

- `POST /agents/{custom,guard,meteo,pirate}`
- `POST /api/v1/polar/chat`
- `POST /simulation/position` (snap already lives in `useLegContext`,
  on the front, with no API)

---

## 9. Polar engine (no chat)

### 9.1 Library (`server/polar_engine.py`)

Behaviour to keep (already tested in prod):

- `PolarData.speed(twa, tws)` — bilinear + TWA→0 fade + TWS plateau
- `optimal_upwind` / `optimal_downwind` / `optimal_gybe_angle`
- `summary()` for TWS 8, 10, 12, 16, 20, 25
- `generate_full_grid()` → 181×61
- `parse_polar_csv` / `parse_polar_excel` / `parse_polar_pdf` /
  `parse_polar_text`

Dependencies: `numpy`, `pandas`, `openpyxl`, `pdfplumber` (text PDF) ;
`pytesseract` + `pdf2image` **optional** (scanned PDFs). Without
Tesseract, an image PDF → honest 422 (“image PDF: install tesseract”).

### 9.2 API (`server/polar_api.py`)

| Method | Path | Role |
|---|---|---|
| POST | `/api/v1/polar/upload` | multipart `file` + `expedition_id` + `boat_name` |
| GET | `/api/v1/polar/{id}` | full grid (the front **does not download it** for the UI) |
| GET | `/api/v1/polar/{id}/summary` | VMG only |

**No** `POST /api/v1/polar/chat`.

Default `expedition_id`: `berry-mappemonde-2026`.

Storage: `server/polar_data/polar_{id}.json` (gitignore).

### 9.3 UI (right panel only)

**Pixel-contract** behaviour with NAVIGUIDE **minus the chat**:

1. On mount, fetch `/Leopard46_Standard_Sails.csv` → automatic
   “Leopard 46” upload.
2. PDF / CSV / XLSX drop zone, Analysing / Loaded / Failed badge.
3. VMG table (upwind | downwind) for the 6 TWS.
4. **No** “Chat” input in the left sidebar.

The polar story, later, goes through the event briefing (“on this leg,
at 12 kt wind, upwind VMG …”) — not a free Q&A.

### 9.4 Engine tests (no UI)

`server/tests/test_polar_engine.py`:

- Leopard 46 CSV parses ;
- `speed(90, 12)` > 0 ;
- `summary()[12]` has `upwind` and `downwind` ;
- `generate_full_grid().shape == (181, 61)` ;
- TWA 0 → speed 0.

`server/tests/test_polar_api.py` (optional but useful): `POST /upload`
the CSV then `GET /summary` ; **no** `/chat` test.

---

## 10. NAVIGUIDE UI / UX (what remains)

This is **the** stage-1 skipper criterion. We port the screen, we
change the projector, we **remove** the three exclusions.

### 10.1 Left column — `Sidebar.jsx` (320 px, `slate-900`)

Top to bottom, **in this order**:

1. NAVIGUIDE logo.
2. **BerryCard** — states `berry-active` / `draw-mode` /
   `file-active` / `berry-active-file-loaded`: **Draw**, Finish,
   Continue, Delete, Berry ↔ custom toggle. **No** GeoJSON / KML.
3. Layer pills.
4. Simulation button (Play / exit).
5. If simulation ON: `SimulationPanel` **only**.
6. “Getting started” box if there is no plan yet.
7. **Briefing** (orchestrator text, or `buildLocalCustomBriefing` on a
   custom route, or hint while drawing). Later: event story.

**No** Polar Chat between 6 and 7.

Floating toggle `left-4` / `left-[322px]`.

### 10.2 Right column — `ToolsSidebar.jsx` (320 px, sky edge)

1. FR / EN.
2. Dark / Light (toggles Esri basemap: `TILE_URLS.dark` / `.light`).
3. Route stats (nm, segments, points).
4. Polar drop + VMG table.

**No** “Download” / Export GeoJSON / Export KML section.

Floating toggle `right-4` / `right-[322px]`.

### 10.3 Map chrome (outside layers)

Ported from `App.jsx`:

- “Computing routes…” overlay then `routesProgress` pill ;
- draw banner (green, undo / redo, searoute spinner) ;
- escale flags + hover ;
- satellite popup (Wind / Wave / Current tabs +
  `WindDirectionArrow`) ;
- layer fiche popup (`LayerFichePopup`) ;
- name / flags edit for a **drawn** waypoint ;
- clipboard toast if it already exists.

### 10.4 Briefing — the project slot

Same **client** contract as NAVIGUIDE, **one** text:

- Berry: `POST …/expedition/plan/berry-mappemonde` **if**
  `VITE_ORCHESTRATOR_URL` is set **and** the service answers ;
  else 24 h `localStorage` cache, else the “Getting started” box is
  enough.
- Custom (**drawn** route): `POST …/expedition/plan` 8 s max, else
  `buildLocalCustomBriefing`.

Do **not** copy `naviguide_orchestrator/`. Without an orchestrator, UX
stays complete (local text). Do **not** add 4 tabs to “fill the
void”: the void is intentional; that is where the story will land.

### 10.5 What is **not** NAVIGUIDE UX (do not add)

- Console / Review / Swarm tabs.
- HelloAsso donation grid.
- “One layer = one operator mode”.
- The 4 chats and polar chat (even though they exist in NAVIGUIDE
  today: the skipper **removed** them for this project).

---

## 11. BerryCard without import

Today (`Sidebar.jsx` L.232–441) the card has 4 states, and
`import-mode` shows **GeoJSON + KML + Draw**.

We **simplify**:

| State | Display |
|---|---|
| `berry-active` | Berry logo + **Draw your own route** button |
| `draw-mode` (or `isDrawing`) | Switcher if a custom route already exists ; **Finish** ; no files |
| `file-active` | Berry \| Custom switcher ; **Continue** ; **Delete** |
| `berry-active-file-loaded` | Switcher (Berry on) + link to redraw |

Rules:

- “Draw” click → `onDrawStart` (no `setCardMode("import-mode")` that
  opens `<input type="file">`).
- **Finish** → `onDrawFinish()` returns an in-memory
  `FeatureCollection` → `setCustomRoute`. This is **not** a disk
  import. Internal name `importedGeoJSON` may stay during the port ;
  better: `drawnRoute`.
- **Delete** → back to Berry.
- **No** `parseGeoJSON` / `parseKML` / `geoJsonRef` / `kmlRef`.

i18n labels `importOrDraw`, `clickToImport`, `clickNewImport` become
`drawOwnRoute` / `drawNewRoute` (or reuse existing `drawOwnRoute`).

---

## 12. Leaflet map and panes

Create once, `useSimulatorMap`:

```js
L.map(el, {
  center: [22, 5],
  zoom: 3,
  zoomSnap: 0.25,
  minZoom: 2,
  maxZoom: 18,
  worldCopyJump: true,
});
```

Basemap: `TILE_URLS.dark` by default, `TILE_URLS.light` if `isLightMode`.
**No** MapLibre, **no** PMTiles.

| Pane | z-index | Content |
|---|---|---|
| `tilePane` | 200 | Esri basemap |
| `zee-wms` | 250 | EEZ tiles |
| `balisage` | 260 | OpenSeaMap |
| `route` | 380 | Berry / custom / draw polyline (green while drawing) |
| `amp` | 420 | MPA polygons |
| canvas points | renderer | projects, marinas, … |
| `markerPane` | 600 | flags, WPI |
| `boat` | 620 | catamaran |
| `popupPane` | 700 | popups |

`panes.test.js` (same discipline as
`frontend/src/components/map/__tests__/layerOrder.test.js`).

**Antimeridian:** searoute + `_normalize_antimeridian` already in the
pipeline. If GeoJSON fallback: two Wallis→Nouméa `LineString`s, **do
not** merge them. `flyTo`: `[lat, lon]` (Leaflet), longitude in
]−180, 180].

CSS: `leaflet/dist/leaflet.css`. No default Leaflet icon (divIcon /
circleMarker only) — avoids the Vite `marker-icon.png` trap.

---

## 13. Berry film: searoute, boat, fallback

### 13.1 Building legs

Copy the “Fetch segments” `useEffect` from `App.jsx` (L.523–676)
into a testable `src/utils/berryLegs.js` module:

- `nonMaritimeNames`: Saint-Maur|La Rochelle and return ;
- `skipFromNames`: Marigot, Cayenne, Halifax, Saint-Pierre ;
- inserts: Marigot→Cayenne, Halifax→SPM, SPM→Halifax, Cayenne→Papeete ;
- `SEGMENT_BATCH_SIZE = 4` ;
- `orientCoords` ;
- `check_wind: false` on the initial fetch (wind = click, not 40×
  Copernicus).

### 13.2 Fallback `routeFromOfficial.js`

If `GET /route` fails for **all** legs of the first batch: load
`/route.geojson`, convert:

```
LineString + from/to/type  → segments (nonMaritime ⇔ type === "overland")
Point + point_type         → stops (flag ⇔ escale)
```

Show a discreet banner: “Official route (searoute unavailable)”.

This is **not** a skipper import.

### 13.3 Simulation

Already-proven chain:

```
segments + stops
  → buildSimTargets()
  → simulationStartPos()
  → useLegContext(lat, lon, segments, stops, speedKnots, simulationStep)
```

Controls: `handleSimNext` / `Prev`, snap,
`map.flyTo([lat, lon], { duration: 0.8 })`, drag → re-snap. Route
change (`customRoute`) → boat at the start.

`speedKnots`: 7, or polar×wind if both are there (§5.4).

### 13.4 Boat marker

Port of `CatamaranMarker.jsx`: image, canvas transparency, east/west +
southern-hemisphere rotation, `boat` pane. Without image: cyan CSS
triangle.

---

## 14. Draw your own route

**Not** straight segments. Contract = `App.jsx` L.287–445 + banner
L.913+.

| Action | Behaviour |
|---|---|
| Draw | `drawingMode=true`, hide Berry, crosshair, simulation OFF |
| Click 1 | place the point, no fetch |
| Click 2+ | `GET /route?start_lat…` between previous and new ; **green** polyline |
| Undo | drop point + segment, invalidate in-flight fetch (`fetchIdRef`) |
| Redo | restore point + segment |
| Finish | `drawnSegments` + `drawnPoints` → in-memory FeatureCollection → `customRoute` ; **blue** track |
| Continue | resume existing points |
| Delete | back to Berry, `applyBerryBriefing` |
| Back to Berry | `customRoute = null`, Berry searoute segments (or fallback) reappear |

**No** `.geojson` / `.kml` import.

While drawing: Berry / custom **hidden** (`drawnLines` only).
`canFinishDraw` = ≥ 2 points **and** no fetch in flight.

If searoute fails on **one** segment: keep the point, **orange dashed**
straight line + “searoute failed — temporary chord” pill. Do not abort
the draw.

Drawn waypoints: click → name + flags (`handleSaveDrawPointMeta`).

---

## 15. Layer pills (cockpit legend)

Same UI as `Sidebar.jsx` L.502–531: `rounded-full` pills, coloured
dot, spinner, red border on error.

NAVIGUIDE today has **8** pills (`ALL_LAYER_CONFIG`). The simulator
adds **2** (Science, Climatology) — the “BI-only” / “not a map layer
yet” layers.

| Key | Label | Colour | Source | Default |
|---|---|---|---|---|
| `zee` | EEZ | `#0e7490` | VLIZ WMS via `/proxy/zee/wms` | ON |
| `wpi` | WPI ports | `#f59e0b` | `/proxy/ports` | OFF |
| `balisage` | Marks | `#10b981` | OpenSeaMap tiles (direct, proxy fallback) | OFF |
| `projects` | Projects | `#06b6d4` | `/bi/export/geojson` | OFF |
| `marinas` | Marinas | `#ef4444` | `/bi/export/marinas.geojson` | OFF |
| `capitaineries` | Harbor | `#7dd3fc` | `/bi/export/capitaineries.geojson` | OFF |
| `poe` | PoE | `#d97706` | `/bi/export/poe.geojson` | OFF |
| `amp` | MPA | `#22c55e` | `/bi/amp?bbox=` (polygons) | OFF |
| `science` | Science | `#a78bfa` | `/bi/export/science.geojson` | OFF |
| `climatology` | Climate | `#38bdf8` | **no fetch** — stub banner | OFF |

Rules: fetch on first ON ; AMP bbox debounce 420 ms ; marinas /
projects on **canvas** ; EEZ = WMS boundaries, not the 18 MB GeoJSON ;
climatology = pill + banner (“wind regime: stage 6”).
`climatology.py` is **not** a world layer.

State: `{ show, loading, error, data }`. No layer is “the active mode”.

---

## 16. Stub `ici()` — the empty pack

File: `src/engine/ici.js`.

```js
export const ICI_RADIUS_NM = 30;

export function emptyDossier(lat, lon) {
  return {
    version: 1,
    at: { lat, lon },
    radiusNm: ICI_RADIUS_NM,
    zee: null,
    poe: [],
    amp: [],
    projects: [],
    nearby: { marinas: [], capitaineries: [], wpi: [] },
    marks: [],
    science: null,
    weather: null,
    polar: null,     // stage 1: { boat, vmgHint } IF loaded — never the grid
    event: null,
  };
}

export function ici(lat, lon, extras = {}) {
  const d = emptyDossier(lat, lon);
  if (extras.polarMeta) {
    d.polar = {
      boat: extras.polarMeta.boat_name,
      vmgHint: extras.polarMeta.vmg_summary?.["12"] ?? null,
    };
  }
  return d;
}
```

Called on every `legContext.snappedPosition`. Display: `<details>`
“Cockpit dossier” under the briefing. **Forbidden** to paste in the
FeatureCollections lit on the map.

This JSON is the **project** contract. In stage 1 it is almost empty:
that is honest. Do not fill it with a chat.

---

## 17. Data, ports, variables

`vite.config.js` (dev only):

```js
server: {
  port: 5174,
  proxy: {
    "/route":     { target: "http://localhost:8010", changeOrigin: true },
    "/proxy":     { target: "http://localhost:8010", changeOrigin: true },
    "/wind":      { target: "http://localhost:8010", changeOrigin: true },
    "/wave":      { target: "http://localhost:8010", changeOrigin: true },
    "/current":   { target: "http://localhost:8010", changeOrigin: true },
    "/api/v1":    { target: "http://localhost:8010", changeOrigin: true },
    "/bi": {
      target: "http://localhost:8001",
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/bi/, "/api"),
    },
  },
}
```

**No** `/agents` proxy.

Create **no** route in `backend/` or `naviguide/`. Deploy nothing on
the VPS.

| If… | Then… |
|---|---|
| Simulator backend down | Berry via `public/route.geojson`. Polar / draw / EEZ WMS / WPI = honest error. Marks OK (public tiles) |
| Simulator backend up, BI down | Film + polar + searoute + EEZ/WPI OK. BI pills = error |
| Both up | All layers read-only |

Variables:

- `VITE_API_URL=` (empty = same origin, Vite proxy)
- `VITE_POLAR_API_URL=` (same)
- `VITE_BI_BASE=/bi`
- `VITE_ORCHESTRATOR_URL=` **optional**
- `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` — optional (else
  `_sim_*`)

**No** Tavily key. **No** LLM key is required for stage 1 (no local
chat). The orchestrator, if already running, may have its own — that
is not the simulator folder.

**Never** run `infra/vps/sync-from-atlas.sh`. The simulator does not
talk to Mongo.

---

## 18. Build order (1.0 → 1.9)

Do not start polar (1.5) if searoute (1.2) is not moving: no track, no
film. Do not start layers (1.7) if UX (1.4) is not placed: pills have
nowhere to live.

### 1.0 — Vite + FastAPI skeleton

- `package.json`: react, react-dom, leaflet, lucide-react, tailwind 4,
  `@tailwindcss/vite`, `@vitejs/plugin-react`. **No** `maplibre-gl`
  nor `react-map-gl` nor `searoute-js`.
- Scripts: `dev`, `build`, `preview`, `test`, `server`.
- `server/requirements.txt`: fastapi, uvicorn, searoute, geographiclib,
  shapely, global-land-mask, numpy, pandas, openpyxl, pdfplumber,
  python-multipart, httpx, python-dotenv (+ optional pytesseract,
  copernicusmarine). **No** anthropic / langgraph “for agents”.
- `README.md`: two commands, ports 5174 / 8010, “prod untouched”,
  “we have / we do not have” table (no chats, no import/export).
- Recipe: “NAVIGUIDE simulator” page + `GET http://localhost:8010/`
  → `{ "service": "naviguide-simulator" }`.

### 1.1 — Map + basemap + panes

- `useSimulatorMap`: `L.map`, dark tile, `invalidateSize`, light theme.
- `createPanes` + order test.
- Leaflet CSS.

### 1.2 — searoute + Berry route

- Extract `route_engine.py` + `GET /route`.
- Python test: a short sea leg (e.g. La Rochelle → a point 20 nm
  offshore) returns a `LineString` ≥ 2 points.
- `berryLegs.js` + batched fetch + progress pill.
- `routeFromOfficial` fallback + tests (overland, antimeridian = 2
  segments).
- `useRouteLayer`: casing + stroke, dashed overland, escales, green
  while drawing.

### 1.3 — Boat that moves

- Copy `useLegContext`, `simulationRoute`, `geo`, `escales` + tests.
- `SimulationPanel`, `CatamaranMarker`, `flyTo`.
- Recipe: 5× Next from Saint-Maur → Bay of Biscay / Corsica approach,
  heading and nm change.

### 1.4 — UI / UX (lighter chrome)

- `Sidebar`: BerryCard **without import**, pills, sim, briefing.
- `ToolsSidebar`: language, theme, stats (polar still “API missing”
  if 1.5 is not ready).
- **Check absence** of: GeoJSON/KML buttons, Export buttons, Polar
  Chat, 4 agent tabs.
- Recipe: you recognise NAVIGUIDE, you **do not** see the chats.

### 1.5 — Polar engine (no chat)

- Copy `polar_engine.py` + upload/get/summary routes + default CSV.
- §9.4 tests.
- Wire drop / VMG / auto-Leopard 46.
- (Later in 1.5) `speedKnots` from polar×wind.
- Negative recipe: `POST /api/v1/polar/chat` → **404**.

### 1.6 — Draw your own route

- `App.jsx` handlers + undo/redo banner + Finish / Continue / Delete.
- Recipe: 3 Atlantic clicks, track **that avoids land**, simulation on
  **that** line, back to Berry.
- Negative recipe: no `<input type="file" accept=".geojson">`.

### 1.7 — Pills + layer drawing

Order: Marks → EEZ WMS → WPI → PoE → MPA → Science → Projects →
Harbor offices → Marinas (OFF, canvas) → Climatology stub.

### 1.8 — Route click (wind / wave / current)

- `POST /wind|/wave|/current` + 3-tab popup.
- Recipe: click the track → numbers (real or `_sim_*`), no crash.
  **No** agent call.

### 1.9 — Stub `ici()` + polish

- `ici.js` + key test.
- *Not for navigation* disclaimer.
- Final README: “this works / this does not exist yet” table.
- One line in the **root** `README.md` only once 1.0 exists.

**“Stage 1 done” criterion:** a beginner skipper runs the two
commands, recognises NAVIGUIDE, moves the boat on Berry, loads / sees
Leopard 46 polars, draws 3 **searoute** points, turns AMP on (if local
BI) or sees a clear error, **finds no chat** and no import/export
button, and understands the event story (full `ici()`) is not there.
Without that, we do not start stage 2.

---

## 19. Files touched / forbidden

### We create

- all of `naviguide-simulator/**`
- this document (already)

### We may add, once the 1.0 skeleton exists

- one line in the root `README.md`: “Simulator (out of prod):
  `naviguide-simulator/` — see
  `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md`”

### We do not open

- `frontend/src/**`
- `backend/app/**`
- `naviguide/naviguide-app/**`, `naviguide/naviguide-api/**`,
  `naviguide/polar_agent/**` (we **read** to copy, we **do not
  edit**)
- `infra/vps/**`
- prod CI workflows

If stage 2 needs `GET /api/ici?lat=&lon=`, that will be a
**simulator server** route, not prod. Not now.

---

## 20. Recipe

Machine: **macOS**, Terminal. Three tabs are enough (server, front,
optionally BI).

### A. Film + searoute + polar (simulator backend)

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
```

Other tab:

```bash
cd naviguide-simulator
npm install
npm run dev
```

Open `http://localhost:5174`.

| # | Action | Expected |
|---|---|---|
| A1 | Page loads | Two sidebars, dark map, spinner then Berry track |
| A2 | Polars (**right** panel) | Leopard 46 VMG table (or clear error if parse fails) |
| A3 | Simulation → Next × 3 | Boat moves, from/to, nm, heading. **No** Ports/Weather/… tabs |
| A4 | Previous | One step back, no Cape Verde jump |
| A5 | Draw 3 sea clicks | **Green** track that skirts land, undo works |
| A6 | Finish | Blue track, local briefing, simulation on **this** route |
| A7 | “Berry-Mappemonde” | Back to official searoute |
| A8 | Right panel | Language, theme, stats, polar — **no** Export buttons |
| A9 | BerryCard | Draw / Continue / Delete — **no** GeoJSON / KML |
| A10 | Click the track | Wind / wave / current popup (real or simulated) |
| A11 | `<details>` dossier | `zee: null`, `polar.boat` if loaded |
| A12 | Light / FR | Esri light basemap, labels English→French |
| A13 | Left sidebar | Briefing (or “Getting started”) — **no** Polar Chat |

### B. Film only (simulator backend **off**)

| # | Action | Expected |
|---|---|---|
| B1 | Reload | Track from `public/route.geojson`, “searoute unavailable” banner |
| B2 | Draw | Honest error, no blank page |
| B3 | Polar | Failed badge, the rest lives |

### C. BI layers (optional)

Blue Intelligence backend on `:8001`. Reload.

| # | Action | Expected |
|---|---|---|
| C1 | PoE ON | Amber pins, name popup |
| C2 | MPA ON, Caribbean zoom | Green polygons |
| C3 | Marinas ON | Smooth map (canvas) |

### D. Automated tests

```bash
cd naviguide-simulator && npm test
cd naviguide-simulator && .venv/bin/python -m pytest server/tests -q
```

Must pass: `berryLegs`, `routeFromOfficial`, `simulationRoute`,
`geo`, `ici`, `panes`, `polar_engine`.

### E. Negative recipes (forbidden regressions)

| # | Action | Expected |
|---|---|---|
| E1 | Search “Ports / Safety / Weather / Cruisers” | Absent |
| E2 | `curl -X POST http://localhost:8010/api/v1/polar/chat` | 404 |
| E3 | `curl -X POST http://localhost:8010/agents/meteo` | 404 |
| E4 | Search a “GeoJSON” / “KML” / “Export” button | Absent |
| E5 | `grep -R AgentPanel naviguide-simulator/src` | No file |

---

## 21. Risks

| Risk | Severity | Guard |
|---|---|---|
| Copy `Sidebar.jsx` **as-is** (chat + agents + import) | High | **Surgical** port: strip before the first UI commit |
| Copy `useAmpLayer` with `mode === "amp"` | High | New toggle hooks |
| Glue the simulator to `naviguide-api:8000` | High | **8010** backend in the folder |
| Use `searoute-js` “to go faster” | High | Unused in prod ; Python only |
| Put the 4 chats back “until the project arrives” | Product | The Briefing **is** the slot ; 4 chats drown the judge |
| Put import back “just in case” | Product | Draw + Berry are enough ; file = out of contract |
| Turn Marinas on by default | Medium | OFF + canvas |
| Load `eez_world_map.geojson` | High | WMS boundaries |
| `flyTo([lon, lat])` (MapLibre order) | High | Leaflet = `[lat, lon]` ; test Corsica |
| Wallis–Nouméa antimeridian | Medium | 2 LineStrings / searoute normalisation |
| Runtime import from `frontend/` or `naviguide/` | High | copies |
| Touch nginx / VPS “to test” | Blocking | localhost only |
| Swallow the 181×61 grid into `ici()` | Product | `vmg_summary` only |
| Scanned PDF without Tesseract | Low | 422 + message |
| Believe stage 1 is “ready for Nemotron” | Product | empty pack = honest ; stage 2 next |
| Copy `polar_agent.py` Deploy AI | Medium | `polar_engine` + 3 routes, period |

---

## 22. Handoff to stage 2

Stage 2 may start **only** if A1–A7, A11 and E1–E5 pass.

Then we fill the pack, **without** Tavily:

1. Which EEZ contains the point (`zee_crossings` / shapely) — **1**
   polygon, name, mrgid, Gold yes/no.
2. PoE of **this** EEZ + URL.
3. MPA / projects / 3–5 marinas-harbor-WPI within 20–30 nm.
4. “We enter this EEZ” event.
5. `polar`: already primed (boat + VMG) ; add speed / ETA **for this**
   leg.
6. The **Briefing** narrates that JSON (Nano / Lightning). Still
   **not** 4 chats.

Nano / Tavily / Ultra stay at stages 5–6. Stretch MPA “park, season,
anchorage” and climatology overlay = after the pack.

Global contract reminder:

> Pills light the whole layer. The LLM sees only a handful.
> One step = free `ici()`. Tavily = EEZ entry, skipper click, or
> alert.
> Polar and searoute speak to the **point** and **this** leg, not the
> globe.
> One story, not four agents.

---

## 23. Documents and files this plan inherits

- Product thread “simulation = film, `ici()` = engine, pills = map”
  (September 2026).
- Skipper call 13 September **morning**: polar + UX + searoute +
  draw (v2.0).
- Skipper call 13 September **evening** (this one): polar **without
  chat**, UX **without** 4 agents, **without** GeoJSON import/export.
- [hackathon-nebius-nvidia.en.md](./hackathon-nebius-nvidia.en.md) —
  English briefing (orientations + how we win). Simulator Simulation
  mode **is** the film (player), not the 4 chats on `www.naviguide.fr`.
- `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` — not a world layer at
  stage 1.
- `docs/ARCHITECTURE.md` — `MapView.js` + one hook per layer.
- Living code:
  - film: `naviguide/naviguide-app/src/App.jsx` (searoute L.523–676,
    draw L.287–445, chrome L.824+), `Sidebar.jsx` (BerryCard L.232–441,
    pills L.502–531, **PolarChat L.16–138 discard**, **AgentPanel
    L.573–577 discard**), `ExportSidebar.jsx` (polar L.517+ keep,
    export L.496–515 discard), `useLegContext.js`,
    `MaritimeLayers.jsx` ;
  - polar: `naviguide/polar_agent/polar_engine.py`,
    `naviguide/naviguide_workspace/polar_api/main.py` (L.151–270 yes,
    L.273–375 chat no) ;
  - searoute: `naviguide/naviguide-api/main.py`
    (`searoute_with_exact_end`, `avoid_land`, `GET /route`) ;
  - projector: `frontend/src/components/MapView.js`,
    `frontend/src/components/map/*` ;
  - internal fallback: `backend/data/route.geojson` ;
  - layer **read** exports: `GET /api/export/*`,
    `GET /api/amp?bbox=`.

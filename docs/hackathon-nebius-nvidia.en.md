# Nebius × NVIDIA hackathon — single briefing

**Product:** NAVIGUIDE Simulator — we replay Berry-Mappemonde.  
**Track:** Best Apps and Agents  
**Code:** `naviguide-simulator/` (in place, extractable) — **not** a patch of `www.naviguide.fr`  
**Live demo:** https://simulator.naviguide.fr  
**Date:** 14 September 2026 — aligned with the *Naviguide simulation cockpit* thread  
**Français :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

**Leaflet cockpit plan (EN):** [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md)

**Submission deadline:** Friday 30 October 2026, 10:00 PT  
**Judging:** 1–15 December 2026 · results around 11 January 2027  
**IRL:** Builders & Brews **Toronto, Tuesday 29 September 2026** (not Paris)

Internal briefing, not a Devpost write-up. One English file for strategy **and** how we win. Older copies (Clearance Brief in `backend/`, 4 chats, ConTree as a second repo, MapLibre, prod `llm_cascade`) are **cancelled**.

---

## 1. How we win

Judges will see hundreds of Nemotron chatbots. We win if, in **20 seconds of video**, they understand:

> A boat **slides** along a real circumnavigation (Play, not 70 clicks). It enters an EEZ. The map shows **Gold** Ports of Entry. Tavily **re-checks that fiche**, not the world. Nemotron Ultra **strikes** what is no longer proven. The story comes from a small “from the cockpit” pack, not the whole map.

We submit **one product**: the **simulator**. **Simulation mode** *is* the film. `ici()` builds the backpack. Nano / Lightning **narrate**. Tavily **re-checks this EEZ’s Gold fiche**. Ultra **strikes**. One Briefing, **not** 4 chats.

The long-term eco-tourism mega-briefing (every layer) is the **same** product, serialized: film + pack + Gold PoE + Tavily/Ultra first; the rest later plugs into the same Briefing.

| Criterion (equal weight) | Our proof |
|---|---|
| **Technological Implementation** | Token Factory runtime (not NIM). Nano / Lightning narrate. Ultra judges. Tavily anchored on one fiche. |
| **Design** | A Leaflet **player** (Play / cinema / 4 speeds), one briefing, layer pills. Not 4 chats, not the BI Console. |
| **Potential Impact** | Real pleasure-craft formalities (EEZ / PoE), Berry-Mappemonde, honest disclaimer. |
| **Quality of the Idea** | `ici()` backpack, not a container. Tavily = official text. Stretch: sandbox = geometry proof. Ultra is not on every click. |

**Target prizes:** Grand Prize ($20,000) + Tavily bonus ($3,000). One bonus only: Tavily over City ($500), while still going to Toronto.

**NIM (`integrate.api.nvidia.com`) does not count.** All submission inference goes through Token Factory + at least one Nemotron.

---

## 2. Three “simulation modes” — do not mix them up

| Object | Where | What it is | Submission? |
|---|---|---|---|
| **Simulator Simulation mode** | `naviguide-simulator/` · [simulator.naviguide.fr](https://simulator.naviguide.fr) | The **film**: catamaran on Berry (or draw + searoute), Leaflet, one Briefing, pills | **Yes — this is the product** |
| **NAVIGUIDE prod** simulation | `www.naviguide.fr` · MapLibre · `:9004` | Still the **4 chats** + polar chat + GeoJSON import | **No.** We do not touch it |
| Blue Intelligence **7 modes** | `blueintelligence.online` | Operator UX (including climatology atlas) — one mode at a time | **No.** The cockpit can light several pills at once |

Skipper (13–14 Sep): *“The project rests on this [simulation] mode.”* Then: *“I also want a real-speed mode with the expedition’s true speed.”*

This is no longer a chat. It is a **voyage**. Prod `www` keeps its old simulation mode. A judge must **not** open `www.naviguide.fr` thinking that is the entry.

---

## 3. The film (what the judge sees)

1. We **replay** the expedition. **Play**: the boat **slides** (not a teleport on every Next).  
2. Four speeds: slow · normal · fast-forward · **real** (polar × point wind; default 7 kt if there is no wind).  
3. It **enters an EEZ** (Blue Intelligence polygon).  
4. If **Gold**: Ports of Entry + official URL. If not Gold: the briefing says so — we do not fake it.  
5. Tavily does not search the world: it **re-checks that fiche**.  
6. Ultra strikes what is no longer proven.  
7. A weather / climate event: the agent narrates the bulletin — Copernicus / satellite popup = **point numbers**.  
8. Stretch MPA: nearby park / season / anchorage.  
9. Stretch sandbox (if ready): “verified in a Nebius sandbox”.

Target Simulation-mode controls:

| Control | Role |
|---|---|
| **Simulation mode** / **Exit simulation** | Enter / leave. On exit: **the boat disappears** |
| Play / Pause | The film runs by itself |
| Previous / Next | Step (escale or playhead, **not** all 1,246 points one by one) |
| Escale bar | Jump (Papeete, Fort-de-France…) |
| Keyboard | Space, arrows, C/E (camera), 1–4 (speed) |
| HUD | FROM → TO, remaining, covered, duration / ETA, heading |
| Camera | Follows the boat **without** locking zoom 8 (keep the world shot) |
| Cinema | Sidebars can close **without** losing Play / keyboard |

---

## 4. The hackathon (useful rules)

- **Page:** https://nebiusglobalaihackathon.devpost.com/  
- **Sponsor:** Nebius B.V. · **Admin:** Devpost  
- **~3,660** registrants on 12 September 2026  
- France is eligible (excluded: Brazil, Québec, Russia, Crimea, Cuba, Iran, DPRK, OFAC)

**Eliminatory:** a **runtime Token Factory** call **or** Nebius AI Cloud (Jobs / Endpoints / DevPods) + **at least one** NVIDIA open-source model.

Judges are **not required** to run the code. “Push past the obvious”: a Nemotron wrapper loses.

| Prize | Amount | Our choice |
|---|---|---|
| Grand / 2nd / 3rd | $20k / $10k / $6k | Overall target |
| Track | Jetson Orin Nano | If not Overall |
| Best Use of Tavily | $3,000 | **Target bonus** (runtime call) |
| City Winner | $500 | Toronto — **one bonus**: we prefer Tavily |
| Feedback | $100 + swag | Fill it in anyway |

---

## 5. Locked architecture (v3.0 + film)

```
Skipper (Leaflet cockpit, two 320 px sidebars)
        │  Simulation mode = player (Play / 4 speeds)
        ▼
ici(lat, lon)     ← backpack (~30 nm), NOT 4,500 projects
        │
Event?  ──no──►  JSON only (free)
        │ yes
        ▼
Tavily (this fiche) → Nano narrates → Ultra judges
        │
        ├─ stretch Data Lab: each briefing = a log (after Nano)
        └─ stretch Sandbox: geo proof (EEZ entry)
        ▼
One Briefing + pills on the map
```

| Word | Meaning |
|---|---|
| Film | **Player**: Play, slide, 4 speeds including real, cinema, keyboard |
| Projector | **Leaflet** (Esri basemap, like BI), **not** MapLibre |
| Title / logo | “NAVIGUIDE simulator” + supplied logo (not the NAVIGUIDE monogram) |
| Legend | Several pills **ON**: EEZ, WPI, marks, Projects, Marinas, Harbor offices, PoE, MPA, Climate (preview), **Science split** (Sextant, Argo, ODATIS, EDMED, CSR, Bathymetry, Seabed, Cables) |
| Boat engine | Python searoute + polar (VMG / upload), **no chat**, **no** 181×61 grid in the prompt |
| Situation engine | `ici()` **before** any LLM |
| The project | One event story (Briefing), not 4 agents |

### Backpack

Radius ~20–50 nm (target **30 nm**) + “which EEZ contains this point”:

| Layer | In the pack | Not this |
|---|---|---|
| EEZ | 1 polygon, name, `mrgid`, Gold? | 285 texts |
| PoE | Ports **of this EEZ**, official URL, status | All PoE |
| MPA / Projects | Near the track | The catalogue |
| Marinas / offices / WPI | 3–5 nearest | All of OSM |
| Marks | Local | The world |
| Science | 0 or 1 **local** dataset (one pill) | All 8 catalogues |
| Wind / wave / current | At the **point** | The globe |
| Polars | Speed / ETA **for this leg** | 181×61 grid / CSV |
| Tavily | This fiche / this notice | `search("ports of entry")` |

Pills light the **whole** layer on the map. The LLM sees only a handful.

### Forbidden

| Forbidden | Why |
|---|---|
| 4 chats Ports / Safety / Weather / Cruisers | Replaced by the Briefing |
| Polar chat (`POST /polar/chat`) | The story is not a VMG Q&A |
| GeoJSON / KML import / export | Route = Berry **or** pencil + searoute |
| Console / Review / Swarm / 7 operator modes | Blue Intelligence UX |
| MapLibre / “nautical chart” PMTiles | We changed projector |
| Wiring `:9000` / `:9004` or `www…/simulator` | `/route` clash, polar **with** chat; **separate** nginx |
| ConTree / Sandboxes as a **2nd** submission | A sandbox **inside** the simulator = stretch |
| NIM as the submission brain | Out of rules |
| Editing `frontend/`, `backend/`, `naviguide/`, www nginx | Prod stays untouched |

**Prod `www.naviguide.fr` / `blueintelligence.online` stay untouched.** Subdomain `simulator.` + separate systemd `:8010`.

---

## 6. Where it lives

The monorepo is **public**, MIT (PR #78).

```
Blue-Intelligence-Map/
├── frontend/ backend/ naviguide/   # PROD — read, do not edit
├── naviguide-simulator/            # hackathon PRODUCT (Vite 5174, FastAPI 8010)
└── docs/
    ├── hackathon-nebius-nvidia.en.md                         # this file
    └── PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md  # workshop (EN)
```

| Where | Role |
|---|---|
| `naviguide-simulator/` | Extractable code — **no** `../../frontend` imports |
| https://simulator.naviguide.fr | VPS demo (A record, certbot, **dedicated** nginx, `:8010`) |
| `www.naviguide.fr` | NAVIGUIDE prod — MapLibre, chats, polar `:9004` |
| Dedicated public repo (later) | Devpost URL: `git subtree split` or copy, README EN |

Create the dedicated repo by hand (the GitHub agent is read-only).

---

## 7. Real constraints

### Gold PoE

Tavily leans on **the map**, not the other way around. Contest minimum: EEZs on the **Berry route** (and the demo leg). Skipper ambition: **285** if the accelerator keeps the Gold bar. A **false** Gold is worse than “probable”.

The 11 polygons already Gold stay an **eval set**. Disclaimer: not for navigation.

The simulator **reads** `/bi/export/poe.geojson` (or a frozen export in `public/`).

### Credits received (13 September)

**Berry-Mappemonde** org:

| Service | Observed | Use |
|---|---|---|
| Token Factory | ~**$60**; 29-day trial | Nano / Lightning / Ultra. `NEBIUS_API_KEY` off git |
| Tavily Researcher | **10,000** + **3,125** add-on | Extract / Search / Research **mini** on **this** fiche |
| Toloka / Tendem | $50 + $50 | Out of submission |

Discipline: **one Ultra per visible action**. Tavily `mini`. No Search on every film frame.

### Prototype routing

Searoute + polar + point wind. No isochrone weather-routing. Draw = pencil + searoute. Observed Berry route: **~39,390 nm**, **35** segments (**34** sea, **1** land Saint-Maur → La Rochelle), **1,246** route points — hence a player, not 1,246 Next clicks.

---

## 8. Code state (14 September)

### Simulator (the product)

**Done:** `naviguide-simulator/` tree; Leaflet; Berry + draw; polar **without** chat; two sidebars; title / logo; pills (Science × 8); **Simulation mode** button; Previous / Next; drag on the track; wind/wave/current popup; FR/EN; theme; live on `simulator.naviguide.fr`. `/agents/*` and `/polar/chat` → **404**.

**In progress** (*Naviguide simulation cockpit*, 14 Sep): turn Simulation mode into a **player** — Play / Pause, slide, escale bar, cinema, keyboard, **4 speeds including real**. Camera follows without glue. Escale cards. Hide the boat on Exit.

**Not started:** real `ici()` pack; Tavily; Nemotron; operator climate overlay.

### Live audit (13 Sep evening, before the player)

What still **blocks** a 3-minute film:

- Next **teleports** (grain = 1,246 points, many “Intermediate point” labels);  
- camera glued at zoom ~8 — no world shot;  
- dead keyboard; controls **trapped** in the left sidebar;  
- start already “arrived” (0 nm remaining, boat at La Rochelle);  
- Briefing **never changes**;  
- boat **stays** after Exit;  
- ETA still **magic 7 kt** while the wind popup shows ~18 kt (wind, not VMG).

The on-screen **cockpit dossier** is **not** the `ici()` pack (no EEZ / PoE / `entered_eez`). Do not sell it as such.

### Prod (read-only)

NIM everywhere. NAVIGUIDE www: 4 chats, MapLibre, polar **with** chat. BI: 7th climatology-atlas mode. **The submission is not those READMEs.**

---

## 9. Roadmap to 30 October

| Stage | What | Hackathon | Who |
|---|---|---|---|
| **Done** | Credits; Toronto; Leaflet cockpit stage 1; `simulator.` demo; logo; Science × 8 | Zero Nemotron | Both |
| **1b** | **Player**: Play, slide, 4 speeds (including **real**), keyboard, camera, clean exit | Still no Tavily | Agent — **now** (the project rests on this mode) |
| **2** | Real `ici()` pack (EEZ, PoE, nearby, `entered_eez`) | Still no Tavily | Agent — **after** a recipe-ready film |
| **3** | Gold Berry route, maybe 285 | Demo fuel | Human |
| **4** | Nano narrates the JSON | Token Factory | Agent |
| **5** | Tavily fiche sentinel | $3,000 bonus | Agent |
| **6** | Ultra + stretches; video + repo | Submit | Both |
| **29 Sep** | Toronto — **show the film** (Play), pack started if possible | Mentors | Human |

Skipper order (14 Sep): **film before `ici()`**. Nemotron on a click album = wrapper. Nemotron on a cockpit with no pack = empty prompt.

### Stage 1 — cockpit (shipped, do not break it)

Detail: [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md).

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
# other Terminal
npm install && npm run dev   # http://localhost:5174
```

**Backend 8010:** `/route`, polar upload/get/summary (**no** `/chat`), proxies, `/wind|/wave|/current`. No `/agents/*`.

**Do not write** `frontend/`, `backend/`, `naviguide/`, or www nginx.

### Stage 1b — the player (in progress)

Film exit criterion: a stranger hits **Play**, sees the boat **slide** from Saint-Maur offshore in under 20 s, changes speed (including **real**), exits: the boat **vanishes**. Keyboard works **even** with sidebars closed. Readable escale names. Not 70 Next clicks to reach the Caribbean.

### Stage 2 — the real pack (`ici()`)

**Simulator** server: EEZ of the point, PoE for that `mrgid`, 3–5 points / 30 nm, `entered_eez`. The Briefing **changes**. Plain JSON in `<details>`.

### Stages 3–6

Gold (skipper) → Nano narrates → Tavily on **this EEZ’s URL** → Ultra 1× / action. AMP / Data Lab / sandbox stretches: §11.

---

## 10. Token Factory and Tavily (technical)

**Not before** a recipe-ready film **and** a non-empty pack.

**Endpoints:** `https://api.tokenfactory.nebius.com/v1/` (Nano / Lightning) · `https://api.tokenfactory.us-central1.nebius.com/v1/` (Ultra).

| Role | ID (re-check `GET /v1/models?verbose=true`) | Price / M tok |
|---|---|---|
| Volume / story | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0.06 / 0.24 |
| Fast agents | `nvidia/Nemotron-3_5-Lightning` | 0.06 / 0.24 |
| Judge (1× / action) | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1.00 / 3.00 |

Thinking OFF for JSON / short text. Parse `content` **and** `reasoning_content`.

**Tavily:** Extract the official URL first. **No** `include_answer`. No Search on every Play frame.

---

## 11. Token Factory stretches — Data Lab and Sandboxes (same product)

Not a second submission. Not SWE-bench. **After** Nano speaks.

| Priority | Stretch | In the 3-min video? | When |
|---|---|---|---|
| Film | MPA / project near the track | Yes if ready | Stage 6 |
| Once Nano speaks | **Data Lab** — measure briefings (ZDR **off**) | No | After real Nano calls |
| May enter the film | **Sandbox** — geo proof (shapely / `zee_crossings`) | 5–8 s if fluent | After `ici()` + Nano |
| Later | Two searoute runs; polar “12 kt → 7 kt?” | No | If the core is polished |

Tavily = official **text**. Sandbox = **geometry**. Honest fallback: the same script on `:8010`.

Data Lab / ZDR / A·B branches unchanged — logs = prompt + `ici()` JSON + Nano + Ultra; SQL “Ultra struck a port”; eval set = 11 Gold + demo leg. Docs: https://docs.tokenfactory.nebius.com/data-lab/overview · https://docs.tokenfactory.nebius.com/sandboxes/overview

---

## 12. 3-minute video

English, public YouTube, **Play running**. Not 70 clicks. No copyrighted music.

| Time | Shot | The judge must read |
|---|---|---|
| 0:00–0:20 | Problem | Skipper, EEZ — **not** a chatbot |
| 0:20–0:45 | Film | **Play**, sliding boat, a beat of real speed, pills |
| 0:45–1:20 | Gold + Tavily | PoE fiche + URL; .gouv sources |
| 1:20–1:55 | Ultra | 2 ports struck (missing citation) |
| 1:55–2:25 | Pack | `ici()` JSON — not 4,500 projects |
| 2:25–2:45 | Token Factory | ~90% Lightning / 10% Ultra split |
| 2:45–3:00 | Impact | Berry route, disclaimer, `simulator.naviguide.fr` |

Say aloud: **Nebius Token Factory**, **Nemotron 3 Ultra vs Nano**, **Tavily on this EEZ fiche**.

---

## 13. Devpost submission

- Track **Best Apps and Agents** only.  
- Demo URL: **https://simulator.naviguide.fr** (not `www.naviguide.fr`).  
- Public repo + MIT. README **English**.  
- “Significantly updated” during the period.  
- Testable through **15 December 2026**.  
- Keys off git.

---

## 14. “We can win” recipe

1. Open **simulator.naviguide.fr**, recognise a **cockpit** (not www, not the Console).  
2. **Play**: the boat slides; **real speed** is available.  
3. See an EEZ, PoE, a link.  
4. See Tavily **on that fiche**.  
5. See Ultra **contradict** Nano once.  
6. README: `ici()` contract + two local commands.

Without 1–2 there is no film. Without 3–5 there is not yet a winning entry. Data Lab / sandbox are **off** this list.

---

## 15. Losing risks

| Risk | Guard |
|---|---|
| Filming `www.naviguide.fr` (4 chats) | **simulator.** URL; README delta |
| 70 Next / teleports | Play player + escale grain |
| Controls trapped in the sidebar | Keyboard + cinema bar |
| Boat left on Exit | Hide the marker |
| Nemotron wrapper on NAVIGUIDE www | Simulator folder + Token Factory |
| 4 chats “for now” | Briefing only |
| Tavily hello-world | Extract the **Gold URL** |
| Wiring `:9004` / `/simulator` path | `:8010` service + dedicated nginx |
| `ici()` before a recipe-ready film | Stage 1b first (skipper order) |
| Nemotron before `ici()` | Empty prompt |
| Fake Gold / ZDR on / 2nd ConTree repo | Honest status; ZDR off; one product |

---

## 16. Sources

- *Naviguide simulation cockpit* thread (13–14 September 2026) + live audit of `simulator.naviguide.fr`  
- https://nebiusglobalaihackathon.devpost.com/ · https://docs.tokenfactory.nebius.com/ · https://docs.tavily.com/  
- Code: `naviguide-simulator/`; prod read-only `polar_engine.py`, `zee_crossings.py`, `MapView.js`

---

## 17. Next action

1. **Agent:** finish the Simulation-mode **player** (Play, real speed, clean exit, keyboard) — **no** Tavily or Nemotron.  
2. **Human:** Gold (route first); Toronto on the 29th.  
3. **Then:** `ici()` pack, then Token Factory.

Winning recipe: §14. Data Lab / Sandboxes: §11, **after** Nano.

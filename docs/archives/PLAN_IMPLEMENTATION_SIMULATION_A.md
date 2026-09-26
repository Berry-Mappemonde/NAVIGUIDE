> **Archivé le 22 septembre 2026 — réalisé.** Horloge climatologique livrée. Index : [docs/README.md](../README.md).

# Implementation plan — Simulation A (climatological clock)

Workshop document for **`naviguide-simulator/`** only.
It locks **how to date the film**: same searoute line, typical wind of
the month, bar in days at sea. This is **not** a forecast, **not** a
live boat, **not** a route recalculation.

Version **1.0** — 14 September 2026.

**Sequel (forbidden until A is recipe-ready):**
[PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md)
(virtual boat, Follow mode, one-leg isochrone).

**English :** not yet. The stage 1 film remains
[PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md).

**Hackathon briefing (FR) :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

---

## What 1.0 locks

Simulation mode already has a **player** (Play, 4 screen speeds,
playhead in nm, 1.4 s stations, Halifax relay, cinema). It has no
civil clock. We cannot say “we leave on 15 June”.

A adds **only** that:

| We keep | We add | We refuse |
|---|---|---|
| Searoute line (Berry or drawn) | Departure date `t0` | GRIB / GFS / IFS |
| Play / Pause / scrub in nm | `vertex → date` table | Isochrones, port 3010 |
| Engine polar (no chat) | Knots = polar × wind **of the month** | Copernicus poll every 25 s for the ETA |
| Air / relay film (`filmCast`) | Calendar days in port | “Arrival Tuesday 14:00” |
| Leaflet, prod untouched | Dated HUD + `kind: climatology` | Modify `www` / BI |

---

**Contents**

1. In one sentence
2. Why this stage exists
3. Skipper contract (in / out)
4. Vocabulary
5. Architecture decisions (locked)
6. Code state (already there / to wire / to write)
7. Clock table
8. Polar: wire the `raw`
9. UI / UX
10. Tree
11. Build order (A0 → A6)
12. Files touched / forbidden
13. Recipe
14. Risks
15. Handoff to simulation B
16. Documents this plan inherits

---

## 1. In one sentence

Give Simulation mode a **departure date** and a **clock in
days at sea**: the boat stays on the searoute line, advances at
polar × **typical wind of the month** at that place, and a leg’s ETA
**changes** if we leave in March rather than in July.

---

## 2. Why this stage exists

Today Play is a **film**: miles, 4 screen speeds, cruise knot
(mean VMG) or yesterday’s wind every 25 s. We cannot
say “we leave on 15 June”.

Berry-Mappemonde lasts months (~39 390 nm). A forecast model
(GFS, IFS) is honest only for **7 to 10 days**. The only honest
simulation of the **whole** expedition is climatology: “in June,
here, the regime is more like this”.

Without A, simulation B has no calendar, no time table, no dated
HUD. Wiring a GRIB before this clock is animating wind on
a film that does not know what day it is.

---

## 3. Skipper contract (in / out)

### We deliver

Locally (`http://localhost:5174`), Simulation mode ON:

1. A **Departure date** field (day + month + UTC time). Default:
   **1 June 08:00 UTC**, sea departure = **La Rochelle**.
2. On **Play**, the boat still slides. The bar shows the **nm**,
   the **days at sea** and the **civil date**
   (e.g. `d18 · 3 July 14:00 UTC`).
3. The HUD shows **local** knots (polar × wind of the month), the
   TWA, and `kind: climatology`. The leg ETA **is no longer**
   `nm / 7`.
4. Changing departure from **15 March** to **15 July** recomputes
   the clock: Fort-de-France no longer has the same arrival date.
5. At flagged stops: **days in port** (calendar), not
   only the film’s 1.4 s pause.
6. Wake + clickable stop list (components already written, to
   mount).
7. Banner: *Typical wind of the month, not tomorrow’s weather.*

If searoute is down: same clock on `public/route.geojson`.

### We do not deliver

| Forbidden in A | Why |
|---|---|
| GRIB, GFS, IFS, Open-Meteo files | That is B |
| Isochrones, port 3010, new line | That is B “recompute” |
| Wall clock = sea clock (“I’ll be back Wednesday”) | That is B “Follow” |
| Polar chat, 4 agents, GeoJSON import | Already excluded from the simulator |
| 181×61 polar grid in the browser | Only the raw table |
| Modify `naviguide/`, `frontend/`, `www` | Prod untouched |
| Claim an arrival “on Tuesday at 14:00” | Forbidden by the climatology plan |
| Current / swell P90 in the integrator | A+ (after the BI atlas), not A.0 |

Prod (`www.naviguide.fr`, `blueintelligence.online`) does not change.

---

## 4. Vocabulary

| Word | Meaning here |
|---|---|
| **Film** | Play / Pause / scrub already there (film nm, planes, Halifax relay) |
| **Civil clock** | UTC date and time of the virtual boat |
| **t0** | Instant of **sea** departure (La Rochelle by default) |
| **Clock table** | Each vertex: `filmNm`, `lat/lon`, `tHours` since t0, `datetime`, knots, wind, `kind` |
| **Days at sea** | Hours under way **excluding** stops, excluding plane |
| **Days in port** | Calendar pause at a flagged stop |
| **Month wind** | Atlas / zones, `kind: climatology`. Not Copernicus NRT |
| **Integrator** | `dt = nm / ground_knots` along the **fixed** line |
| **kind** | Mandatory label. In A: always `"climatology"` |

---

## 5. Architecture decisions (locked)

### 5.1 Same polyline

The line stays searoute (Berry or “draw your own”). A **does
not redraw** the route. Only the clock moves.

### 5.2 Sea departure = La Rochelle

Saint-Maur → La Rochelle: land, outside the polar integrator.

- Default: `t0` = first maritime stop (La Rochelle).
- Option: “from Saint-Maur” → a fixed `dt` (e.g. 4 h), **without**
  polar.

Cayenne ↔ Halifax plane: fixed **calendar** duration
(`AIR_CALENDAR_HOURS` = 8), not the polar.

Halifax ↔ Saint-Pierre relay: same table, vehicle `side`, month
wind on **this** line.

### 5.3 Wind = climatology, polar = raw

- Wind: `zoneWindAt` in
  `naviguide-simulator/src/utils/climatologyWind.js` (copy of
  `climatology.py`). Later, the same atlas API as Blue Intelligence
  **if** it responds; else zones. Always `kind: climatology`.
- Speed: `polarBoatSpeed` on the **raw** table (~20×15). No
  `POST /wind` call every 25 s for clock A.
- Current / swell P90: **outside A.0**. Speed = polar × wind
  only.

### 5.4 One table, two scrubbers

`playback.nm` remains the film source (camera, wake, `ici()`,
1.4 s stations).

The table gives `filmNm → datetime`. A click on the bar = seek in nm
(as today). The displayed date **follows**. A “days”
graduation besides nm is optional (A+, not A.0).

The 4 Play profiles (real / reading / normal / fast) remain
**screen speeds**. They do not compute the civil clock.

In A, the “real” profile (1 s screen = 1 s sea) is **not** the
default: useless over 200 days at sea. It serves as a preview on
**one** leg.

### 5.5 Days in port

Default table (not a file import):

| Stop | Days in port |
|---|---|
| La Rochelle | 3 |
| Other flagged stops | 2 |
| Halifax relay (hub) | 1 |
| Saint-Maur | 0 |

During a stay: `datetime` advances, `filmNm` does not move, HUD
“in port”. The 1.4 s film pause (`STATION_HOLD_MS`) **stays** for
accelerated Play: it is not the same object as days in port.

### 5.6 Where it runs

Table computation **on the client** (zone wind + raw polar =
synchronous, ~1 246 points). No new uvicorn. The polar server
already serves `GET /api/v1/polar/{id}` with `raw`.

### 5.7 Two `kind`s that do not mix

The map click `POST /wind|/wave|/current` stays NRT / ANFC (yesterday’s
wind). It **does not feed** clock A. The film HUD says
climatology. The click popup says recent observation. Two sentences,
two `kind`s.

---

## 6. Code state (already there / to wire / to write)

### Already in the film (do not rewrite)

| Piece | File |
|---|---|
| Playhead nm + stations | `src/engine/routePlayhead.js`, `src/hooks/useRoutePlayback.js` |
| 4 screen speeds | `src/engine/playSpeeds.js` |
| Berry / plane / relay actors | `src/engine/filmCast.js` |
| Bar + pills | `src/components/SimulationFilmBar.jsx` |
| Catamaran rotation | `src/components/CatamaranMarker.jsx` |
| Server polar | `server/polar_engine.py`, `server/polar_api.py` |
| Zone wind | `src/utils/climatologyWind.js` |
| Polar × wind at the point | `src/engine/alongTrackSpeed.js`, `src/engine/polarSpeed.js` |

### Written, not mounted (to wire in A0 / A1)

| Piece | File | Missing |
|---|---|---|
| Wake | `src/engine/filmWake.js`, `src/layers/useWakeLayer.js` | call in `App.jsx` |
| Stop list | `src/components/EscaleLegend.jsx` | mount in `Sidebar.jsx` + i18n keys |
| `alongTrackSpeed` | `src/engine/alongTrackSpeed.js` | nobody calls it |
| Polar `raw` | `GET /api/v1/polar/{id}` | `ToolsSidebar` keeps only `vmg_summary` |

### To write

`voyageClock.js`, `useVoyageClock.js`, `DepartureField.jsx`, and the
HUD / bar glue.

---

## 7. Clock table

### Input

- `flat` (`flattenRoute`) + `marks` (stops);
- ISO UTC `t0`;
- `polarRaw` or `null` (then `boatSpeedFromWind`);
- `portDays`;
- `startAt` = `"la-rochelle"` | `"saint-maur"`.

### Integrator (sea edge)

```
month = monthOf(t0 + tHours)
wind  = zoneWindAt(lat, lon, month)
knots = alongTrackSpeed({ lat, lon, bearing, month, polarRaw }).speedKnots
dt    = spanNm / max(knots, 0.5)     # hours; floor 0.5 kn
tHours += dt
```

Air edge (`jump`): `tHours += AIR_CALENDAR_HOURS` (8).
Port: on crossing a mark, `tHours += portDays * 24`.

### Output (internal JSON, B contract too)

```js
{
  t0,
  kind: "climatology",
  vertices: [
    {
      filmNm, sailNm, lat, lon, bearing,
      tHours, iso, speedKnots, windKnots, twa, month, vehicle,
    },
  ],
  marks: [{ name, filmNm, tHours, iso, holdHours }],
  seaHours, quayHours, arrivalIso,
}
```

Recompute if: route, polar, t0, portDays or startAt change.
**Once**, not every frame.

### Unit tests (no browser)

- March vs July, same nm: Fort-de-France `arrivalIso` **different**.
- t0 = 15 June 08:00, La Rochelle departure → Fort-de-France date > 15 June.
- 2 d in port: 48 h hole in `iso` at constant `filmNm`.
- Air hop: +8 h, `speedKnots` null.
- Without polar: source `climatology`, no crash.
- Antimeridian: `tHours` monotonic.
- `startAt: "saint-maur"`: first `dt` without polar.

---

## 8. Polar: wire the `raw`

Today `ToolsSidebar.jsx` keeps only `vmg_summary`.

After upload / auto-load Leopard 46:

1. `GET /api/v1/polar/{expedition_id}`;
2. keep `raw: { twa_rows, tws_cols, matrix }`;
3. **do not** keep `grid` (181×61).

`useExpeditionSpeed` (25 s Copernicus poll + `GET …/speed`): **cut**
as soon as the clock table exists. Else two knots on screen
(cruise / NRT vs table).

The VMG table in the right sidebar remains the **boat engine** (upload,
summary). The film only needs a knot number at **this**
position.

---

## 9. UI / UX

### Left sidebar (simulation ON)

- `DepartureField`: date, UTC time, selector
  “Sea departure: La Rochelle | Saint-Maur”.
- Under `SimulationPanel`: `EscaleLegend` (click = `seek`).
- HUD: local knots, civil date, `climatology · June` — no more
  `@ 7 kt` alone.

### Bottom bar

Fill already travelled + stop pills (already there). Subtitle:

`4 210 nm · d18 · 3 Jul. 14:00 UTC`

Scrub = nm, as today.

### Map

`useWakeLayer(mapRef, { flat, sailNm: cast.sailNm, enabled: simulationMode })`.
No mandatory new “atlas” layer (the climatology plan:
invisible in NAVIGUIDE).

### Disclaimer

Visible as soon as A is ON, one line, FR/EN.

---

## 10. Tree

Everything in `naviguide-simulator/`:

```
src/engine/voyageClock.js             # NEW — builds the table
src/engine/voyageClock.test.js
src/engine/alongTrackSpeed.js         # already there — wire
src/engine/polarSpeed.js              # already there
src/utils/climatologyWind.js          # already there
src/hooks/useVoyageClock.js           # NEW — t0, table, seek
src/components/DepartureField.jsx     # NEW
src/components/SimulationFilmBar.jsx  # dates + days
src/components/SimulationPanel.jsx    # local knots + kind
src/components/EscaleLegend.jsx       # already there — mount
src/layers/useWakeLayer.js            # already there — call
src/components/ToolsSidebar.jsx       # keep polar.raw
src/components/Sidebar.jsx            # DepartureField + legend
src/App.jsx                           # glue
src/i18n/fr.js
src/i18n/en.js
```

**No** runtime import from `../../naviguide/` nor
`../../frontend/`. We do **not** copy `isochrone.py` in A.

---

## 11. Build order (A0 → A6)

| # | What | Exit criterion |
|---|---|---|
| **A0** | Wire wake + stop list + i18n | Visual, zero weather |
| **A1** | `polar.raw` in state | `alongTrackSpeed` testable with Leopard 46 |
| **A2** | `voyageClock.js` + March / July tests | Table without UI |
| **A3** | `useVoyageClock` + `DepartureField` | Changing t0 regenerates the table |
| **A4** | HUD + bar (date, days, local knots, kind) | No more magic 7 kt |
| **A5** | Calendar stays | “N d in port” banner + date that jumps |
| **A6** | Atlantic recipe + disclaimer | §13 green |

Do not start A3 if A2 does not have the March ≠ July tests.
Do not start B until A4 is recipe-ready.

A0 can start in parallel with A1 (no weather dependency).

---

## 12. Files touched / forbidden

**Yes:** `naviguide-simulator/src/**` (+ tests), i18n keys.

**No:**

- `naviguide/` (including `naviguide_weather_routing/`)
- `frontend/`, `backend/`
- `infra/vps/` (except a doc pointer, not a deploy)
- `server/copernicus/getWind.py` / `getWave.py` / `getCurrent.py`
  (NRT click, other `kind`)
- port 3010

---

## 13. Recipe

1. Leopard 46 polar loaded. Simulation mode. t0 = **15 June 08:00 UTC**,
   La Rochelle departure.
2. Play: the boat leaves; the bar shows a date ≥ 15 June;
   `kind` climatology.
3. Same route, t0 = **15 March**: Fort-de-France arrival date
   **different** (several days of gap, visible).
4. Click “Fort-de-France” in the list: boat **and** date
   consistent.
5. At a stop: date +2 d (default) without moving the boat, then
   resume.
6. Cayenne → Halifax hop: plane, date +~8 h, no polar knots.
7. Leave: the boat disappears (stage 1b contract).
8. Disclaimer visible.
9. Backend off: film + clock A (zones + polar if already in
   memory). Searoute down = fallback `public/route.geojson`.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Two knots on screen (25 s poll vs table) | Cut `useExpeditionSpeed` from A4 |
| 1 246 points too slow | Table **once**, not every frame |
| Non-monotonic `tHours` (jumps, antimeridian) | Tests; hops = +8 h outside polar |
| “15 June” read as a forecast | Disclaimer + mandatory `kind` |
| Saint-Maur departure = polar on the motorway | Sea t0 = La Rochelle by default |
| Confusing 1.4 s pause and days in port | Two constants, two HUDs |

---

## 15. Handoff to simulation B

A is done when: clock table + t0 + ETA that depends on the month + dated
HUD + March / July tests + §13 recipe.

B replaces **only** the `wind(lat, lon, t)` function for the
first 10 days, adds the wall clock, then a button that
**changes one leg’s line**. The integrator and the bar are not
rewritten.

The §7 JSON schema **is** B’s input contract.

Detail: [PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md).

---

## 16. Documents this plan inherits

- [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)
  — film, searoute, polar without chat, Leaflet.
- [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md)
  — `kind: climatology`, not GFS as the engine of a circumnavigation.
- [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md) — the product
  is the simulator, not `www.naviguide.fr`.
- [REGLES_PARAMETRES.md](../REGLES_PARAMETRES.md) §3.6 — `no_llm_for_numbers`,
  `wave_nogo_m` (A+ only).
- Live A code: `alongTrackSpeed.js`, `climatologyWind.js`,
  `polarSpeed.js`, `routePlayhead.js`, `filmCast.js`,
  `server/polar_api.py`.

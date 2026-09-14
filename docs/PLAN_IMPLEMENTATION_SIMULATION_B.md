# Implementation plan — Simulation B (live virtual boat)

Workshop document for **`naviguide-simulator/`** only.
It locks **how to follow a dated virtual boat** and **recompute a
leg**: 0–10 d forecast, Follow mode, isochrone to the next
stop. This is **not** the climatological film (A), **not** a worldwide
GRIB, **not** an isochrone of all of Berry.

Version **1.0** — 14 September 2026.

**Prerequisite:** [PLAN_IMPLEMENTATION_SIMULATION_A.md](./PLAN_IMPLEMENTATION_SIMULATION_A.md)
recipe-ready (clock table, t0, dated HUD, March / July tests).
**Do not start B until A4 is green.**

**English :** not yet.

**Hackathon briefing (FR) :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

---

## What 1.0 locks

A says: “in June, typically, on the searoute line”.
B says: “if I leave La Rochelle **tomorrow**, here are the next 10
days, and here is where the boat **is** on Wednesday”. A **Recompute**
button proposes a **new line to the next stop**.

| We keep (A) | We add (B) | We refuse |
|---|---|---|
| `vertex → date` table | 10 d forecast `windFn(lat, lon, t)` | Globe GRIB on the VPS |
| Default searoute line | Follow mode (`now()` = playhead) | 39 000 nm isochrone |
| Uploaded polar | Recompute **of one leg** | Prod port 3010 |
| HUD + `kind` | Play ghost ≠ live marker | VISIR / Windy / SignalK as a dep |
| Prod untouched | Corridor cube + 12 h cache | Wind invented by an LLM |

---

**Contents**

1. In one sentence
2. Why this stage exists
3. Skipper contract (in / out)
4. Vocabulary
5. Architecture decisions (locked)
6. Forecast cube
7. Follow mode
8. Route recompute
9. Simulator API (port 8010)
10. UI / UX
11. Tree
12. Build order (B0 → B8)
13. Files touched / forbidden
14. Recipe
15. Risks
16. A → B link
17. Out of scope
18. Documents this plan inherits

---

## 1. In one sentence

Start a **virtual boat on a real date** (e.g. tomorrow
08:00 UTC): for ~10 days it advances with the **forecast**
wind / current / wave; you **find it** where it should be when
reopening the app; a **Recompute** button proposes a **new line**
to the next stop (isochrone), without claiming to know Papeete to
the nearest day.

---

## 2. Why this stage exists

A is honest for the **whole** expedition (months). It does not say
the wind of **next Tuesday**.

B is the **tactical** complement: 0–10 day window, as the
climatology plan had put **outside V1** of the atlas (`kind: forecast`, other
workshop). This workshop **is** that other workshop, bounded to the
simulator.

Without Follow mode, B is only an A film with fresher wind.
Without recompute, the boat stays glued to the searoute line even if the
model says to pass further south. Both gestures share the **same**
clock table as A.

---

## 3. Skipper contract (in / out)

### We deliver

Locally, then on `simulator.naviguide.fr` **if** the cube fits in
memory (§14.12):

1. **New voyage**: t0 (tomorrow 08:00 UTC possible), polar, Berry
   or custom route.
2. **First 10 days**: knots = polar × **forecast** at the point and
   at the hour. HUD: `kind: forecast`, model **named**
   (e.g. GFS 0.25° / CMEMS ANFC), validity `+36 h`.
3. **After D+10**: fade toward table A. HUD: `kind: climatology`.
   Never an invented GFS for November.
4. **Follow mode**: **wall** clock = sea clock. Close the computer,
   come back 2 days later: the boat has advanced 2 days (if t0 has
   passed). If t0 is in the future: boat **in port** until t0.
5. **Play** in Follow mode = **preview** (ghost): you can scrub the
   future without moving the live boat. Button / `L` key:
   “Back to live”.
6. **Recompute the route**: from the live position → **next
   flagged stop** only. 6 h isochrone, forecast wind then
   climatology. Preview (new line + old searoute dashed) →
   Accept / Refuse.
7. Recompute **refused by default** for the whole circumnavigation in
   one go.
8. Double disclaimer: 0–10 d forecast / climatology afterwards / not
   suitable for navigation.

Cube down: the voyage stays on **A alone** + banner “forecast
unavailable, climatology”. The film does not go black.

### We do not deliver

| Forbidden in B | Why |
|---|---|
| Worldwide GRIB on the VPS | 8 GB, climatology plan |
| 39 000 nm isochrone | Dishonest + unplayable |
| VISIR-2, Windy plugin, SignalK as a dependency | We copy the algo, not the repos |
| Wire prod port 3010 | Not deployed; other polar singleton |
| Skipper GRIB import (Saildocs) in v1 | The server cuts the corridor |
| Open-Meteo `best_match` without naming the model | Climatology law |
| Weather chat that invents a wind | `climatology.no_llm_for_numbers` |
| Modify `www` / Blue Intelligence | Prod untouched |
| AIS / Iridium of the real catamaran | Other product |
| Tavily / Nemotron | Other hackathon stage |

---

## 4. Vocabulary

| Word | Meaning here |
|---|---|
| **Voyage** | Instance: `voyageId`, t0, polar, route, revision |
| **Live** | Position = clock table at `now()` (UTC) |
| **Preview / ghost** | Play or scrub **without** moving live |
| **Corridor** | ~200 nm buffer around the ~1 500 nm **ahead** of the boat, 10 d, not 3 h |
| **Cube** | Wind + wave + current with a **time** axis |
| **Fade** | Between D+7 and D+10, forecast → climatology blend |
| **Recompute** | New geometry **of one leg**, then we **replay** A/B on that line |
| **Revision** | `routeRev`: searoute v0, isochrone v1, v2… |
| **kind** | `"forecast"` or `"climatology"` on each step / vertex |

---

## 5. Architecture decisions (locked)

### 5.1 B extends A, it does not replace it

Same JSON schema as A §7. We pass it `windFn(lat, lon, t)`:

| When | Wind |
|---|---|
| `t < t0 + 7 d` | Forecast cube |
| `t` in `[t0+7 d, t0+10 d]` | Linear blend (wind or knots) |
| `t > t0 + 10 d` | `zoneWindAt` / atlas (A) |

Play, the bar, the wake, `ici()` do not change contract.

JS `voyageClock.js` **stays** for A and for the offline preview
(climo only). As soon as a cube exists, the **official** table of the live
voyage = server response (same schema).

### 5.2 Cube: no globe GRIB

**Pragmatic B v1** (Copernicus account already in `simulator.env`):

| Field | Product | What we change |
|---|---|---|
| Wave | `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i` | Open `valid_time` from t0 to t0+10 d, **corridor**, no more `time=-1` |
| Current | `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` | Same, 3 h subsample |
| 10 m wind | Open-Meteo Marine **GFS** (model **named**) | L4 NRT (`getWind.py`) = yesterday, **forbidden** for B |

**B-alt** (later, not v1): GFS GRIB2 NOMADS cut **outside**
the live request, pipeline like climo snapshots, never a globe `wget` at
Play.

Disk cache `server/forecast_cache/{voyageId}/` (gitignore), one
small grid, TTL 6–12 h. Relaunch a fetch in Follow mode if the
cache is older than 12 h (new 00/12 UTC run).

### 5.3 Follow mode = persistence

A voyage lives longer than a tab.

- `localStorage` key `naviguide_sim_voyage_v1`: `voyageId`, t0,
  routeKind, routeRev, accepted isochrone hash.
- Server: `server/voyage_data/voyage_{id}.json` (same spirit as
  `polar_data/`) to find the boat on another browser /
  after publish.

Live position **computed**, not stored every minute:

```
position = table.at(now)
```

We persist t0 + route revision + polar id.

| Wall clock | Boat |
|---|---|
| `now < t0` | In port, HUD “casting off in …” |
| `t0 ≤ now ≤ end of table` | Live on the line |
| `now` after the end | Arrival (or end of expedition) |

### 5.4 Play ≠ Live

| Control | Effect |
|---|---|
| Follow mode ON | **Live** marker (solid). Wall clock |
| Play / scrub | **Ghost** marker (outline). Live **stays** |
| “Back to live” / `L` | Camera + HUD on `now` |
| Leave Follow | Back to film A (frozen table, no more wall clock) |

We do not let Play **move** the live boat.

### 5.5 Recompute = one leg, not the world

```
live position → next flagged stop
10 d forecast horizon, then climatology up to THIS stop
time step 6 h, heading 10°, max ~120 steps
```

If the isochrone does not reach the stop: we **splice** the best
point onto the **remaining searoute** of this leg. Status `spliced`.

The rest of Berry (following stops): **searoute unchanged**. We
**only recreate the clock** from the new
arrival time.

Old line: dashes, pane underneath. New: solid line.
Isochrone envelopes: **off** by default (toggle).

Recompute **disabled** in air / relay phase (`filmCast` plane or
`side`). A handles the cast.

### 5.6 Copy the isochrone, do not call prod

`naviguide/naviguide_workspace/naviguide_weather_routing/`: Berry
polar **singleton**, **zone** wind, port 3010 **absent** in prod.

In the simulator:

- copy `isochrone.py` (propagate / prune / land mask) to
  `naviguide-simulator/server/isochrone.py`;
- inject `wind_fn`, `current_fn`, `wave_nogo_fn`;
- `polar` = **uploaded** polar (Leopard 46 or skipper file);
- `kind` on each step: `forecast` or `climatology`.

**No** `import` from `../../naviguide/`. The simulator folder
stays extractable.

### 5.7 Waves = brake, not the knot

`climatology.wave_nogo_m` = 2.5 m
([REGLES_PARAMETRES.md](./REGLES_PARAMETRES.md) §3.6).

- In climo: P90 (when the BI atlas exists; else no wave no-go
  in v1).
- In forecast: cube Hs.

If no-go: the isochrone step is **dropped**. On a fixed polyline (without
recompute), `dt` × 3 or 6 h hove-to (one constant, tested). We
do not invent a formed-sea polar.

### 5.8 Zero LLM

B is numbered wind. No Nemotron, no Tavily, no weather
chat.

### 5.9 Asynchronous creation

`POST /voyage` answers immediately (table A, `forecast: pending`).
The cube fills in the background. `GET /voyage/{id}` moves to `ready`.
The UI shows a banner, never a 30 s blocking spinner.

---

## 6. Forecast cube

### Cut

On creation / on refresh:

1. Take ~1 500 nm of route **ahead** of live (or from t0 if
   still in port).
2. ~200 nm buffer → bbox (handle the antimeridian: two rectangles if
   needed).
3. Window `t0 … t0+10 d` (or `now … now+10 d` on refresh).
4. Variables: 10 m wind `u/v` (or force + dir), Hs, surface current
   `uo/vo`.
5. Write the cache. If too large: shrink the corridor, **do not** switch
   to the globe.

### Interpolation

`cube.at(lat, lon, t)`: nearest neighbour or spatial bilinear +
temporal linear. Land / NaN → `null` → A fallback (zone) **and**
`kind` stays honest (`climatology` + `reason: "no_forecast_cell"`).

### Memory

Target: one voyage cube **< 80 MB**. Recipe test. The VPS has
`MemoryMax=1G` for `naviguide-simulator`.

---

## 7. Follow mode

### Persistence

```js
{
  voyageId, t0, expedition_id,
  routeKind, routeRev,
  follow: true,
  forecastStatus: "pending" | "ready" | "unavailable",
}
```

### Clock

`GET /voyage/{id}/at?t=` (default `now`). The front does not integrate the
cube. It displays the returned position.

A local tick (1/min, or on focus resume) is enough. No rAF
for live.

### Two markers

- Live: solid `useCatamaranMarker`, `draggable: false` in Follow
  (drag would break `now()`).
- Ghost: second outline marker, only if Play / scrub ≠ live.

Camera: follows the **ghost** during preview, the **live** otherwise.
`useFilmCamera` already there: pass it the active actor.

---

## 8. Route recompute

### Input

```
from = live position
to   = next flagged stop (or to_name)
t    = now
polar = upload
wind_fn / current_fn / wave_nogo_fn = blend §5.1
time_step_h = 6
heading_step_deg = 10
max_steps = 120
arrival_radius_nm = 50
```

### Output

```js
{
  status: "arrived" | "spliced" | "failed",
  kind_mix: ["forecast", "climatology"],
  draft_geojson,
  hours, distance_nm,
  versus_searoute: { hours, distance_nm },
}
```

### Acceptance

1. Replace the current leg with `draft_geojson`.
2. Increment `routeRev`.
3. Rebuild the clock table **from** the new arrival
   (downstream = searoute A/B).
4. Upstream (already travelled) does not move.

Refuse: nothing. The draft expires (or `GET /draft` returns it as long
as we have not accepted).

---

## 9. Simulator API (port 8010)

| Method | Path | Role |
|---|---|---|
| POST | `/voyage` | Creates: t0, `expedition_id`, route, `follow` |
| GET | `/voyage/{id}` | Metadata + `routeRev` + `forecastStatus` |
| GET | `/voyage/{id}/clock` | Clock table (A schema) |
| GET | `/voyage/{id}/at?t=` | Live position / at `t` (default `now`) |
| POST | `/voyage/{id}/refresh-forecast` | Reload the corridor (12 h) |
| POST | `/voyage/{id}/recompute` | Isochrone → candidate leg |
| GET | `/voyage/{id}/draft` | Proposed line + status |
| POST | `/voyage/{id}/accept` | Apply the revision |
| POST | `/voyage/{id}/reject` | Drop the draft |

`POST /wind|/wave|/current` **unchanged** (NRT click). Other `kind`.

No `/agents/*`. No `/api/v1/polar/chat`.

---

## 10. UI / UX

### Creation

A fields + “Virtual boat (10 d forecast)” checkbox + “Follow mode”.

If Follow and t0 in the future: *The boat does not sail before …*.

### Live HUD

Date **now**, knots, named model, validity, `forecast` or
`climatology`. Green **LIVE** pill vs grey **preview**.

### Recompute

Button in `SimulationPanel` only if:

- Follow ON;
- vehicle = boat (not plane, not relay);
- `forecastStatus !== "pending"` (or climo only, with banner).

Spinner. Dialog: searoute vs proposed nm and hours, double-line
map. Accept / Keep searoute.

### Keyboard

`L` = back to live. **No** shortcut for Recompute
(too easy to launch by mistake).

---

## 11. Tree

```
naviguide-simulator/server/
  voyage_api.py              # routes §9
  voyage_store.py            # voyage_data/*.json
  forecast_cube.py           # CMEMS corridor + named wind
  forecast_blend.py          # wind_fn(t)
  isochrone.py               # adapted copy (no prod import)
  voyage_clock.py            # same algo as JS A, server side
  voyage_data/               # gitignore
  forecast_cache/            # gitignore
  tests/test_voyage_clock.py
  tests/test_forecast_blend.py
  tests/test_isochrone_leg.py
src/hooks/useVirtualVessel.js
src/components/FollowToggle.jsx
src/components/RecomputeDialog.jsx
src/layers/useAltRouteLayer.js
src/i18n/fr.js
src/i18n/en.js
```

---

## 12. Build order (B0 → B8)

| # | What | Exit criterion |
|---|---|---|
| **B0** | A table JSON contract = server table | One shared golden test |
| **B1** | Corridor `forecast_cube` + cache, **without** isochrone | 1 point, t0+36 h, wind ≠ June zone |
| **B2** | `wind_fn` + server clock | 10 d forecast, d11 = climo |
| **B3** | `GET /at?t=now` + `useVirtualVessel` + LIVE pill | F5: same position |
| **B4** | Play = ghost, `L` = live | Two markers, only one “true” |
| **B5** | Isochrone copy + `wind_fn` + polar upload | Short-leg test (mock cube OK) |
| **B6** | `recompute` + dialog + accept/reject + dashes | Geometry of **one** leg |
| **B7** | 12 h cube refresh in Follow | After refresh, live may move |
| **B8** | Recipe + cube memory < 80 MB + disclaimer | §14 green |

Do not open B5 if B3 does not survive an F5.
Do not isochrone all of Berry “to see”.

---

## 13. Files touched / forbidden

**Yes:** `naviguide-simulator/server/**` (new modules + tests),
`naviguide-simulator/src/**` (B hooks / UI), i18n,
`server/.gitignore` (`voyage_data/`, `forecast_cache/`).

**One-off copy:** `isochrone.py` (and land mask /
bathymetry helpers **if** indispensable), copied and adapted. Then no
more link.

**No:**

- `naviguide/` as a runtime import, `www`, skipper nginx
- `frontend/`, `backend/` (except **reading** a climo snapshot already
  published, as GET)
- Deploying port 3010
- `getWind.py` as a B source (48 h NRT)
- `infra/vps/` except, **later**, Copernicus variables already planned
  in `simulator.env`

---

## 14. Recipe

### Live

1. t0 = **tomorrow 08:00 UTC**, La Rochelle, Leopard 46, Follow ON.
2. Today: boat in port, countdown.
3. Accelerated recipe: t0 = **36 h ago**. Position **offshore**,
   HUD `forecast`, named model, validity.
4. F5: same lat/lon ± 1 nm.
5. Play: ghost advances, live **still**. `L`: back to live.
6. Auto test: `GET /at?t=t0+48h` (no need to move the system
   clock).

### Fade

7. `GET /at?t=t0+11d`: `kind: climatology`. No more GFS validity.

### Recompute

8. From an Atlantic position, Recompute → Fort-de-France.
   Proposed line ≠ searoute (often). Status `arrived` or `spliced`.
9. Refuse: searoute unchanged.
10. Accept: solid line = isochrone, searoute dashed,
    clock **after** Fort-de-France reset, the Pacific **not**
    recomputed.
11. Cube down: banner + A. No LLM wind.

### Memory

12. Server process: cube < ~80 MB. Else shrink the corridor.

---

## 15. Risks

| Risk | Mitigation |
|---|---|
| “Arrival Papeete on 3 November” from GFS | d>10 = climo; HUD writes it |
| VPS OOM | Corridor + cache; never global GRIB |
| Two polar engines (3010 vs upload) | One only: the simulator’s |
| Isochrone through land | Copy’s land mask; Iberia / Morocco tests |
| Live + Play fighting | Ghost vs solid, §5.4 |
| Slow CMEMS on POST /voyage | Async, `forecast: pending` |
| Halifax relay during a live | Recompute off in air / side |
| ECMWF licence | IFS outside v1; GFS or CMEMS **named** |
| Cube that expires during Follow | 12 h refresh, banner if `unavailable` |

---

## 16. A → B link

```
A : fixed line + wind(month)      → table (vertex → date)
B : same table + wind(lat,lon,t) → 10 d forecast, then A
    + now() as playhead            → Follow
    + isochrone(leg)               → new line, then table again
```

| Skipper question | Plan |
|---|---|
| We leave 15 June, all of Berry, ETA by season | **A** |
| We leave tomorrow, I find it on Wednesday | **B Follow** |
| GFS says to pass further south to the Antilles | **B Recompute** |
| Whole mappemonde recomputed every morning | **Nobody** — outside the contract |

Two separate merge requests. No single “A+B” PR.

---

## 17. Out of scope

- VISIR-2, CO₂, scientific voyage plan.
- Historical Sea Routing as a **replacement** of searoute (other
  permanent monthly geometry): only if one day we want
  “which month, which route” **without** forecast. Neither A nor B.
- AIS replay of the real boat.
- Operator GRIB overlay on every layer.
- Self-hosting Open-Meteo, globe NOMADS ingestion.
- Writing into `naviguide.fr` / Blue Intelligence.
- 8th “Climatology” pill in the simulator.

---

## 18. Documents this plan inherits

- [PLAN_IMPLEMENTATION_SIMULATION_A.md](./PLAN_IMPLEMENTATION_SIMULATION_A.md)
  — clock, t0, JSON schema, polar `raw`.
- [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)
  — film, exclusions, prod untouched.
- [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md)
  §4, §21 — 0–10 d forecast = other `kind`, outside atlas V1; **this**
  workshop.
- [REGLES_PARAMETRES.md](./REGLES_PARAMETRES.md) §3.6 —
  `wave_nogo_m`, `no_llm_for_numbers`, `avoid_cyclone_tracks`.
- Code to **copy** (not import):
  `naviguide/naviguide_workspace/naviguide_weather_routing/isochrone.py`.
- Code to **extend**: `naviguide-simulator/server/copernicus/getWave.py`,
  `getCurrent.py` (`valid_time` idea, not NRT / forecast merge in
  the same click endpoint).

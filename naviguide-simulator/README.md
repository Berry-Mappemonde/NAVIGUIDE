# NAVIGUIDE simulator

**Off-production** subfolder: the Berry-Mappemonde expedition cockpit <!-- pragma: allowlist secret -->
(Leaflet map, layer buttons, moving boat, searoute, polars).

`www.naviguide.fr` and `blueintelligence.online` are **not** the same
site. Planned publication: **https://simulator.naviguide.fr** (free
subdomain, same VPS, separate nginx).

FR plan: [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md) (v3.0)
EN plan: [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md)
Simulation A (climatology clock): [`docs/PLAN_IMPLEMENTATION_SIMULATION_A.md`](../docs/PLAN_IMPLEMENTATION_SIMULATION_A.md)
Simulation B (virtual boat, after A): [`docs/PLAN_IMPLEMENTATION_SIMULATION_B.md`](../docs/PLAN_IMPLEMENTATION_SIMULATION_B.md)

## Run (macOS, Terminal)

Two tabs. From this folder:

```bash
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

## Publish on the VPS

When the `simulator.naviguide.fr` DNS already points at `135.125.226.16`
(from the Mac, or any machine with Node + SSH):

```bash
cd /path/to/Blue-Intelligence-Map
bash infra/vps/naviguide/publish-simulator-from-mac.sh
```

That builds the site on the Mac, copies only this folder and the
simulator infra files, then on the VPS: Python venv, `:8010` service, **separate** nginx,
extended Let's Encrypt certificate (free). `www.naviguide.fr` is not
redeployed. Details: `infra/vps/README.md` (simulator section).

| It works | It does not exist yet |
|---|---|
| NAVIGUIDE film (2 sidebars, Berry, simulation, briefing) | 4 Ports / Safety / Weather / Cruisers chats |
| Climatology clock: departure date, days at sea, ETA by month | GRIB / GFS / “arrival Tuesday 2 pm” (simulation B) |
| Searoute + draw your own route | Polar chat |
| Polar upload + VMG table (Leopard 46) | GeoJSON or KML import / export |
| Civil clock + virtual boat (Follow, named 10-day forecast, recompute **one** leg) | Globe GRIB, 39 000 nm isochrone, port 3010 |
| Layer chips (Sextant, Argo, ODATIS, EDMED, CSR, bathymetry, seabed, cables + Climatology stub) | |
| `ici()`: EEZ, Gold PoE, MPA / projects / ports within 30 nm — the briefing tells this bag | Tavily / Nemotron / Token Factory (steps 5–6) |
| Route click → wind / wave / current | Dump of the whole map into the story |

**Not for navigation.**

## Licences and attributions

The repository is **MIT / Apache-2.0**. The simulator does not ship LeafletPlayback,
TrackPlayBack, deck.gl or signalk-polar-performance: those are *ideas*
(clock, wake, TWA→knots). The film / polar code is original.

To display (already in the footer, the map and the modal):

| Source | Licence / credit |
|---|---|
| Leaflet | BSD-2-Clause — “Leaflet” in the attribution control |
| Esri Canvas tiles | “Tiles © Esri” |
| OpenSeaMap (marks) | ODbL — “© OpenSeaMap contributors” |
| EMODnet (bathy / seabed / cables) | CC-BY — WMS attribution |
| GEBCO (offshore sounding in the bag) | GEBCO Compilation Group — OpenTopoData point lookup (GEBCO 2020), `null` within 20 M of a port |
| Leopard 46 polar | ORC file loaded by the user / local default |

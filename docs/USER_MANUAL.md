# User manual — NAVIGUIDE simulator

This manual lists **every button** on screen, in one line each.
No jargon. The app is **not for navigation**.

Live: [simulator.naviguide.fr](https://simulator.naviguide.fr).
French version: [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md).

On first launch a **Not for navigation** window appears.
**Accept** closes it and opens the map.

The map fills the centre. A **left panel** (expedition, layers, briefing),
a **right panel** (tools), and a **bar** at the bottom (time, playback).
**Hide sidebar** / **Hide panel** folds the matching panel; click again
to reopen it.

---

## 1. Follow expedition

The boat is at **today’s** position. The map follows it.
The official departure is 15 May 2026, 08:00 UTC — you cannot change
it in this mode.

| Button | What it does |
|--------|----------------|
| **Follow expedition** | Shows the boat at today’s position and frames the map on it. |
| **Simulation** | Leaves Follow and opens playback (see chapter 2). |
| **Berry** | Returns to the official Berry-Mappemonde route. |
| **Draw your own route** | Switches to drawing (see chapter 3). |
| **Replay the expedition** | Starts the narrated film (see chapter 4). |
| **Now** | Shows what matters around the boat right now. |
| **Story** | Shows the voyage story up to today. |
| **Log** | Shows the logbook, day by day. |
| **Listen** | Reads the story aloud. |
| **Stop** (next to Listen) | Mutes the voice. |
| **Send** | Sends your question to the logbook. |
| **See on the map** | Frames the boat and the place the card is about. |
| **Official sheet / site** | Opens the official page (port of entry, protected area…). |
| **Data source** | Opens the source of the number on screen. |
| **Google Maps sheet** | Opens the place in Google Maps. |
| **Next** (on a card) | Goes to the next card. |
| **Close** (on a card) | Dismisses the card. |
| **Back to live (L)** | If you moved in time: return to “now”. |
| **Layers** | Turns a map layer on or off (see below). |
| **Hide sidebar** | Folds the left panel. |

**Layers** (left panel):

| Button | What it does |
|--------|----------------|
| **GRIB2** | Shows wind and sea from the latest forecast around the boat. |
| **EEZ** | Shows exclusive economic zones. |
| **WPI ports** | Shows World Port Index harbours. |
| **Marks** | Shows sea marks (OpenSeaMap). |
| **Projects** | Shows marine conservation projects. |
| **Marinas** | Shows marinas. |
| **Harbour master** | Shows harbour-master offices. |
| **Port of entry** | Shows official ports of entry. |
| **MPA** | Shows marine protected areas. |
| **Sextant / Argo / ODATIS / EDMED / CSR** | Shows a science layer. |
| **Bathymetry** | Shows shaded relief of the seabed. |
| **Seabed** | Shows seabed type. |
| **Cables** | Shows submarine cables. |
| **Climate** | Shows the monthly atlas (typical wind, not tomorrow). |
| **Wind / Swell / Currents / Cyclones** (under Climate) | Turns on one atlas map. |

Click a point on the route: a **Satellite data** sheet opens.

| Button | What it does |
|--------|----------------|
| **Wind** | Shows wind speed and direction at that point. |
| **Waves** | Shows significant wave height and period. |
| **Currents** | Shows the surface current. |

If the boat enters a listed piracy zone, a **Piracy** card appears.
Outside the zone it disappears.

---

## 2. Simulation

Same map, same briefing. You **advance** time.
The departure date starts as today; you can change it.

| Button | What it does |
|--------|----------------|
| **Simulation** | Enters this mode (Play, speeds, stop jumps). |
| **Follow expedition** | Leaves Simulation and returns to today’s position. |
| **Day (UTC)** | Changes the departure day. |
| **UTC time** | Changes the departure hour. |
| **Play** | Moves the boat forward. |
| **Pause** | Stops the boat where it is. |
| **Previous stop** | Jumps to the previous harbour and recentres the map. |
| **Go to next stop** | Jumps to the next harbour and recentres the map. |
| **real** | 1 second on screen = 1 second at sea. |
| **read** | Slow: time to read during an ocean crossing. |
| **normal** | Usual playback speed. |
| **fast** | Quick crossing. |
| **Cinema** | The map follows the boat. Zoom or pan frees the view; click again to recapture. |
| **Film fullscreen** | Hides the panels so the map fills the screen. Escape or click again restores them. |
| **Auto stop** | On: pause at every harbour. Off: sail through harbours. |
| **Hide the bar** | Folds the bottom bar. |
| **Ask for advice** | Proposes another track to the next harbour, under your limits. |
| **Keep searoute** | Keeps the current track. |
| **Accept** | Replaces this leg with the proposed track. |
| **Stops** (list) | A click on a name jumps to that harbour. |

Layers, briefing, logbook and **Replay the expedition** work as in Follow.

---

## 3. Draw your own route

You draw a route. The briefing is about **that route**,
not Berry-Mappemonde.

| Button | What it does |
|--------|----------------|
| **Draw your own route** | Starts drawing: each click on the sea drops a point. |
| **Finish** | Closes the track and builds the briefing for this route. |
| **Undo the last point** | Removes the last point. |
| **Import** | Loads a GeoJSON or KML file (points or line) as waypoints. |
| **Continue drawing** | Adds points to a finished route. |
| **Delete route** | Clears the drawn route. |
| **Back to Berry-Mappemonde route** | Leaves drawing and restores the official route. |

If a route is already there, **Import** asks
**Replace the current route?** — confirm replaces it, cancel keeps the old one.
An unreadable file shows **Unreadable file**; nothing else changes.
More than 60 points: **60 points maximum**.

---

## 4. Replay the expedition

A film of the route, from Saint-Maur to today, told aloud.
Start it from **Follow expedition**.

| Button | What it does |
|--------|----------------|
| **Replay the expedition** | Starts the film. The voice leads the boat. |
| **Stop** | Stops the film and returns to Follow. |
| **Film fullscreen** | Hides the panels for the film. |
| **Raw** | Shows the rules-written story (no model). Greyed out if missing. |
| **Written** | Shows the drafted story (Nemotron). Greyed out if missing. |
| **2:30** / **3:00** | Sets the film length. |

During the film a **bubble** may leave the boat at an event
(gale, harbour). **Close** dismisses it.
Harbour sheets do not open during the film.

---

## 5. Right panel

The expedition and the tools. **Show panel** / **Hide panel**
opens or folds it.

| Button | What it does |
|--------|----------------|
| **Language** | Switches the interface to French or English. |
| **Dark** / **Light** | Changes the map and panel theme. |
| **Show** / **Hide** (polars) | Opens or closes the polar table. |
| **Drop a file** | Loads a polar (PDF, CSV or XLSX) instead of the default. |
| **Plan review** | Lists each leg and what to watch (wind, shipping lanes…). |
| **Apply** | Applies the suggested date or corridor for a leg. |
| **Harbour sheet** | Opens the port sheet (services, formalities, sources). Clicking the harbour flag does the same. |
| **GeoJSON** | Downloads the route on screen (Berry, simulation or drawing). |
| **KML** | Downloads the same route as KML. |
| **Coastal** / **Cruise** / **Offshore** | Sets the skipper character (wind and sea limits). |
| **Back to Berry orders** | Restores the expedition limits. |
| **Ask for advice** | Same as in Simulation: another track to the next harbour. |
| **Advanced settings** | Opens or closes the detailed skipper numbers. |
| **OK** (admin key) | Saves the key in this browser only (edit the official route, GRIB or polar). |

The **route summary** is not a button: it shows legs, stops and distance.
A chip may name a shipping **lane** the track crosses; the line on the
map does not move.

---

## What the app does not do

This is **not** a nautical chart, **not** a GPS, **not** a chatbot
that invents. An empty field means: we do not know. Atlas wind is a
typical month, not tomorrow’s forecast.

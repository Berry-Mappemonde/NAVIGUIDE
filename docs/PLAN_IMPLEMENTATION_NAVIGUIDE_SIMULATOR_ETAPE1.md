# Plan d’implémentation — `naviguide-simulator/` étape 1

Document de chantier. Il fige **comment poser le dossier** dans ce dépôt, et
**quoi coder en premier**.

Version **3.0** — 13 septembre 2026.

**Ce que la 3.0 change par rapport à la 2.0**

Le skipper a tranché le cockpit : on garde le **moteur bateau** et le
**film**, on retire ce que le projet (briefing / sac `ici()`) va
remplacer, et ce qui ne sert pas à une expédition simulée.

| Décision 2.0 (annulée) | Décision 3.0 (celle-ci) |
|---|---|
| Polar **chat** (`POST /polar/chat`, `PolarChatSection`) | Polar **moteur + upload + VMG** seulement. Le récit = le projet |
| **4 chats** simulation (Ports / Sécurité / Météo / Cruisers) | **Interdits.** `AgentPanel` et `/agents/*` ne se copient pas |
| Import GeoJSON / KML + export GeoJSON / KML | **Interdits.** Inutiles ici. La route perso = **draw + searoute** |
| Backend qui recopie les 4 agents SSE | Backend = searoute + polar (sans chat) + proxies + vent |

Ce qui **ne change pas** depuis la 2.0 :

- sous-dossier extractible, **Leaflet** (plus de MapLibre) ;
- prod `naviguide.fr` / `blueintelligence.online` **intouchées** ;
- **searoute** pour Berry **et** pour « draw your own route » ;
- polar engine **complet** (parse, grille 181×61, VMG, upload) ;
- UI / UX NAVIGUIDE **sauf** les exclusions ci-dessus ;
- `ici()` encore un **sac vide** (étape 2).

Les étapes 2 à 6 (sac réel, événements ZEE, Gold, Tavily, Nemotron) sont
rappelées pour ne pas les commencer trop tôt — **elles ne sont pas
livrées ici**.

**Sommaire**

1. En une phrase
2. Pourquoi cette étape existe
3. Contrat skipper (dans / hors)
4. Vocabulaire
5. Décisions d’architecture (verrouillées)
6. Arborescence cible
7. Copier / adapter / inventer / jeter
8. Backend du simulateur
9. Polar engine (sans chat)
10. UI / UX NAVIGUIDE (ce qui reste)
11. BerryCard sans import
12. Carte Leaflet et panes
13. Film Berry : searoute, bateau, fallback
14. Draw your own route
15. Boutons de couches
16. Stub `ici()`
17. Données, ports, variables
18. Ordre de chantier (1.0 → 1.9)
19. Fichiers touchés / interdits
20. Recette
21. Risques
22. Passage à l’étape 2
23. Documents et fichiers dont ce plan hérite

---

## 1. En une phrase

Créer `naviguide-simulator/` dans **ce** dépôt : le **cockpit** de
NAVIGUIDE (route Berry, tracer sa route, polaires, simulation), projeté
sur une carte **Leaflet** avec les boutons de couches — **sans** les
4 chats, **sans** chat polar, **sans** import/export de fichiers,
**sans** toucher `naviguide.fr` ni `blueintelligence.online`.

---

## 2. Pourquoi cette étape existe

Le produit hackathon, ce n’est pas un deuxième Blue Intelligence. C’est
le **film** : le bateau avance, on voit la carte du cockpit, et plus tard
un petit dossier « vu d’ici » nourrit **un** récit.

Sans l’étape 1, il n’y a ni cockpit, ni position, ni boutons. Le moteur
`ici()` (étape 2) n’aurait rien autour de quoi travailler.

Les 4 chats Ports / Sécurité / Météo / Cruisers et le chat polar sont
**l’ancien cockpit parlé**. Le projet les remplace : un briefing
d’événement, nourri plus tard par le sac. Les copier maintenant, c’est
reconstruire ce qu’on a décidé d’abandonner.

L’import / export GeoJSON / KML sert l’opérateur ou un autre logiciel.
Ici la route vient de **Berry** ou du **crayon + searoute**. Pas d’un
fichier.

L’étape 1 **n’appelle pas** Tavily ni Nemotron. Elle prépare :

- le **projecteur** (Leaflet + légende) ;
- le **film** (route Berry, bateau, tracer) ;
- le **moteur bateau** (searoute + polar), pour que l’ETA et le trait
  soient ceux du skipper, pas une ligne droite à 7 nœuds ;
- un **emplacement** Briefing (texte local), prêt à recevoir le récit.

---

## 3. Contrat skipper (dans / hors)

### On livre

À la fin de l’étape 1, en local :

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010 --reload   # un Terminal
npm install && npm run dev                     # un autre Terminal
```

Ouvrir `http://localhost:5174`. On reconnaît NAVIGUIDE, sur Leaflet :

1. **Deux panneaux** 320 px : gauche (expédition) et droite (langue,
   thème, stats, polaires). FR / EN, sombre / clair.
2. **BerryCard** : route Berry, **draw your own route**, continuer,
   terminer, supprimer, bascule Berry ↔ perso. **Pas** de boutons
   GeoJSON / KML.
3. **Route Berry** calculée **jambe par jambe via searoute** (même
   logique d’escales que `App.jsx` : overland Berry↔La Rochelle, skip
   Marigot / Halifax, Halifax↔SPM maritime, Cayenne→Papeete). Spinner +
   pastille de progression.
4. **Mode simulation** : Précédent / Suivant, bateau collé à la route
   (`useLegContext`), drag, `flyTo`. **Pas** d’`AgentPanel`.
5. **Polar engine complet** : CSV Leopard 46 chargé tout seul, drop
   PDF / CSV / XLSX, grille 181×61 côté serveur, tableau VMG. **Pas**
   de chat polar.
6. **Draw your own route** : clics carte → `GET /route` searoute (pas
   une corde), undo / redo, bandeau vert, Terminer → la route devient
   active.
7. **Dix boutons** de couches (ZEE, WPI, Balisage, Projets, Marinas,
   Capit., PoE, AMP, Science, Climatologie) — dessin Leaflet, plusieurs
   allumées ensemble.
8. **Clic route** → vent / vague / courant au point
   (`POST /wind|wave|current`).
9. **Briefing** unique (cache local 24 h, orchestrateur optionnel,
   sinon texte local / hint de tracé). C’est **l’emplacement du
   projet**.
10. Stub `ici()` branché à chaque pas (JSON typé, encore vide côté ZEE).
11. `README.md` du dossier : lancer, ports, « prod intouchée », ce qui
    n’existe pas encore.

**Si le backend simulateur est éteint** : la route Berry se dessine
quand même depuis `public/route.geojson` (copie interne de
`backend/data/route.geojson`). Ce fichier n’est **pas** un import
skipper. Le tracer, le polar et les proxies ZEE / WPI affichent une
erreur honnête. Le film ne doit pas être noir.

La prod ne change pas.

### On ne livre pas

| Interdit en étape 1 | Pourquoi |
|---|---|
| **4 chats** Ports / Sécurité / Météo / Cruisers (`AgentPanel`, `/agents/*`) | Remplacés par le projet (briefing / `ici()`) |
| **Chat polar** (`PolarChatSection`, `POST /api/v1/polar/chat`) | Idem : le récit n’est pas un Q&A sur le tableau VMG |
| **Import GeoJSON / KML** (`parseGeoJSON`, `parseKML`, inputs fichier) | Inutile : Berry ou crayon |
| **Export GeoJSON / KML** (`buildGeoJSON`, `buildKML`, boutons Télécharger) | Inutile dans ce projet |
| Console, Review, Swarm, 6 modes opérateur | UX Blue Intelligence, pas le cockpit |
| Carte MapLibre / fond PMTiles « carte marine » | On change de projecteur |
| Isochrones weather-routing (port 3010) | Autre moteur, pas déployé en prod |
| Orchestrateur LangGraph **dans** le dossier | Le briefing **appelle** l’existant s’il tourne ; sinon texte local |
| `polar_agent.py` (Deploy AI / Claude Opus) | Chemin mort |
| Tavily, Nemotron, Token Factory | Étapes 5–6 |
| Requêtes spatiales « dans cette ZEE / 30 nm » | C’est `ici()` réel = étape 2 |
| Imports / exports **opérateur** BI | On **lit** les mêmes URLs, on n’écrit rien |
| Modifier `frontend/`, `backend/`, `naviguide/`, `infra/vps/` | La prod ne bouge pas |
| `react-leaflet` | Les hooks BI parlent à un `L.Map` nu |
| `searoute-js` (npm, **jamais utilisé** dans `App.jsx`) | Le moteur réel est Python `searoute==1.4.3` |
| `llm_cascade.py` | Plus de chat polar ni d’agents dans ce dossier |
| Coller 4 500 projets dans un prompt | Le LLM du sac n’existe pas encore ici |

**Nuance GeoJSON (à ne pas confondre avec l’import/export skipper) :**

| Oui (interne) | Non (skipper) |
|---|---|
| `customRoute` = `FeatureCollection` **en mémoire** après « Terminer » | Ouvrir un `.geojson` / `.kml` depuis le disque |
| `public/route.geojson` = **secours** si searoute est down | Bouton « Exporter » / « Importer » |
| Couches carte lues en GeoJSON (`/bi/export/*`) | Télécharger la route affichée |

---

## 4. Vocabulaire

| Mot | Sens ici |
|---|---|
| **Film** | Ce que le skipper voit : deux sidebars, route, bateau, boutons, tracer |
| **Projecteur** | La carte : Leaflet, plus MapLibre |
| **Légende** | Les pastilles ON/OFF (ZEE, WPI, Balisage, …) |
| **Moteur bateau** | searoute (le trait) + polar (la vitesse / le VMG) |
| **Le projet** | Plus tard : récit d’événement depuis `ici()`. En étape 1 : **un** panneau Briefing |
| **Sac à dos / `ici()`** | Petit JSON autour du bateau. Étape 1 = sac **vide** (sauf éventuellement nom du bateau si polar chargé) |
| **Route officielle (fallback)** | `backend/data/route.geojson` → `public/route.geojson` si searoute est down. Pas un import |
| **Escale** | Stop avec drapeau (La Rochelle, Ajaccio…). Un point intermédiaire n’en est pas une |
| **Gold** | Fiche Formalités relue. Inutile à l’étape 1 |
| **Prod** | `blueintelligence.online` et `naviguide.fr` |

---

## 5. Décisions d’architecture (verrouillées)

### 5.1 Un sous-dossier, pas un fork

```
Blue-Intelligence-Map/
├── frontend/                 # prod BI — interdite
├── backend/                  # prod API — interdite
├── naviguide/                # prod NAVIGUIDE — interdite
├── naviguide-simulator/      # NOUVEAU, extractible plus tard (hackathon)
└── docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md
```

Plus tard : `git subtree split` (ou copie propre) vers le dépôt
hackathon. Donc **aucune** import runtime du style
`../../frontend/src/...` ou `../../naviguide/...` : on **copie** les
modules, on n’attache pas les deux apps.

### 5.2 Pile technique

| Choix | Comme… | Pas comme… |
|---|---|---|
| Vite 7 + React 19 + Tailwind 4 | `naviguide/naviguide-app` | CRA de `frontend/` |
| Leaflet 1.9 **nu** (`L.map`) | `frontend/src/components/MapView.js` | MapLibre / `react-map-gl` |
| FastAPI **dans le dossier** (`server/`, port **8010**) | extraits de `naviguide-api` + `polar_api` **sans chat** | appeler la prod, ports 8000 / 8004 |
| Port Vite **5174** | — | 5173 (NAVIGUIDE) et 3000 (CRA) |
| FR d’abord, EN ensuite | i18n NAVIGUIDE (clés utiles) | clés amputées au hasard |

Leaflet **sans** `react-leaflet` : Blue Intelligence crée déjà la carte
à la main. Recoller ça dans `react-leaflet` ferait tout réécrire.

### 5.3 Route : searoute d’abord, GeoJSON officiel en secours

NAVIGUIDE aujourd’hui appelle `GET /route?start_lat=…` **jambe par
jambe** (`App.jsx` ~L.523–676, lots de 4). C’est searoute + évitement
des terres (`searoute_with_exact_end` → `avoid_land` → densify →
sanitize).

L’étape 1 **refait ce film** :

1. Les stops viennent de `ITINERARY_POINTS` (copie de
   `naviguide-app/src/constants/itineraryPoints.ts`, ~41 points,
   drapeaux PNG).
2. Les jambes sont **les mêmes** (skip Marigot / Halifax / SPM /
   Cayenne, insert Marigot→Cayenne, Halifax↔SPM, Cayenne→Papeete,
   overland Saint-Maur↔La Rochelle).
3. Chaque jambe maritime = `GET /route` du **backend simulateur**.
4. Orientation A→B (`orientCoords`) : searoute peut renvoyer B→A.
5. Si le backend est down **ou** qu’une jambe échoue : on bascule
   (toute la route, ou jambe par jambe) sur `public/route.geojson` via
   `routeFromOfficial.js`.

**Conséquence :** le film marche **sans** `naviguide-api` de prod. Le
simulateur a **son** `/route`. On ne proxy pas vers `:8000` « pour
aller plus vite » : ça recollerait le dossier à la prod et casserait
l’extraction hackathon.

### 5.4 Polar : le moteur vivant, pas le chat, pas le LangGraph mort

« Polar engine complet **sauf le chat** » = ce que NAVIGUIDE utilise
pour **calculer**, pas pour **discuter** :

| Fichier source | Rôle | Dans l’étape 1 |
|---|---|---|
| `naviguide/polar_agent/polar_engine.py` | Parse PDF / CSV / XLSX, interpolation, grille 181×61, VMG | **Oui** |
| `naviguide/naviguide_workspace/polar_api/main.py` — `upload`, `GET /{id}`, `GET /{id}/summary` | Persistance + résumé | **Oui** |
| `polar_api` — `POST /chat`, `_build_polar_system_prompt`, `_polar_fallback_reply` | Q&A LLM | **Non** |
| `naviguide-app/.../Sidebar.jsx` — `PolarChatSection` | UI chat | **Non** |
| `ExportSidebar.jsx` — drop + tableau VMG + auto-Leopard 46 | UI moteur | **Oui** |
| `naviguide/polar_agent/polar_agent.py` | Deploy AI, Claude Opus | **Non** |
| `llm_cascade.py` | Cascade NIM → OpenRouter → Claude | **Non** (plus aucun chat local) |

Le front **ne télécharge pas** la grille 181×61 : seulement
`vmg_summary` (TWS 8 / 10 / 12 / 16 / 20 / 25). C’est déjà le bon
« sac » pour plus tard.

**ETA du film :** `useLegContext` reste à 7 kt **tant qu’il n’y a pas
de vent au point**. Dès que `POST /wind` répond, on lit
`polar.speed(twa, tws)` et on passe `speedKnots` au hook. Sans polar
chargé : 7 kt. On ne câble **pas** l’isochrone weather-routing.

### 5.5 Couches : mêmes URLs, nouveau dessin, pas les hooks « un mode »

Blue Intelligence n’affiche **qu’un** mode à la fois. Les recopier tels
quels reproduirait « un mode à la fois ».

**On ne les importe pas.** On **vole** styles / panes / popups /
canvas, on **réécrit** la colle : bouton ON → fetch une fois →
`map.addLayer`. Plusieurs couches allumées ensemble.

Les 4 500 projets restent sur la **carte** si on allume le bouton. Le
LLM (plus tard) n’en verra qu’une poignée via `ici()`.

### 5.6 Simulation : comme NAVIGUIDE, sans les 4 agents

La simulation est un **bouton**. OFF au chargement, le skipper appuie.

Quand elle est ON : `SimulationPanel` (from→to, nm, ETA, cap,
Précédent / Suivant) **uniquement**. Pas d’onglets Ports / Sécurité /
Météo / Cruisers en dessous.

### 5.7 Un backend dans le dossier — obligatoire, plus mince que la 2.0

`searoute-js` est dans le `package.json` NAVIGUIDE et **n’est jamais
importé**. Le moteur est Python.

Un seul process FastAPI (`server/`, **8010**) sert :

- `/route` (searoute + avoid-land) ;
- `/api/v1/polar/upload`, `GET /{id}`, `GET /{id}/summary` ;
- `/proxy/zee/wms`, `/proxy/zee`, `/proxy/ports`, `/proxy/seamark` ;
- `/wind`, `/wave`, `/current` (Copernicus si identifiants, sinon
  `_sim_wind` / `_sim_wave` / `_sim_current` déjà dans
  `naviguide-api`).

**Pas** `/agents/*`. **Pas** `/api/v1/polar/chat`. Pas de second
uvicorn polar sur 8004.

---

## 6. Arborescence cible

```
naviguide-simulator/
├── README.md
├── package.json                 # name: naviguide-simulator
├── vite.config.js               # port 5174, proxy /route /proxy /api /bi /wind…
├── index.html
├── public/
│   ├── route.geojson            # fallback interne (copie backend/data/route.geojson)
│   ├── Leopard46_Standard_Sails.csv
│   └── logo-*.png / flags/
├── server/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI : route + polar (sans chat) + proxy + wind
│   ├── route_engine.py          # extraits de naviguide-api/main.py (searoute → sanitize)
│   ├── polar_engine.py          # copie de naviguide/polar_agent/polar_engine.py
│   ├── polar_api.py             # upload + GET + summary seulement
│   ├── mem_limits.py
│   ├── copernicus/              # getWind / getWave / getCurrent (copie)
│   ├── polar_data/              # JSON persistés (gitignore)
│   └── geo_data/                # optionnel : NE 1:10m ; sinon global_land_mask
├── src/
│   ├── main.jsx
│   ├── App.jsx                  # film NAVIGUIDE porté : état + Leaflet, plus MapLibre
│   ├── index.css
│   ├── constants/
│   │   ├── layers.js            # 10 pastilles
│   │   └── itineraryPoints.js   # copie (PNG → public/flags)
│   ├── engine/
│   │   └── ici.js               # stub
│   ├── hooks/
│   │   ├── useLegContext.js
│   │   ├── useSimulatorMap.js   # L.map, panes, fond Esri dark/light
│   │   └── useMarkerOffsets.js
│   ├── i18n/                    # fr.js + en.js (clés utiles ; clés mortes OK)
│   ├── layers/                  # un hook Leaflet par couche + route
│   ├── components/
│   │   ├── Sidebar.jsx          # BerryCard sans import, pills, sim, briefing — PAS PolarChat ni AgentPanel
│   │   ├── ToolsSidebar.jsx     # langue, thème, stats, polar — PAS export
│   │   ├── SimulationPanel.jsx
│   │   ├── LayerFichePopup.jsx  # popup Leaflet
│   │   ├── CatamaranMarker.js   # L.marker + DivIcon
│   │   └── WindDirectionArrow.jsx
│   └── utils/                   # geo, escales, simulationRoute, customRouteBriefing,
│                                # waypointsFromCollection, routeFromOfficial, layerIdentify
│                                # PAS parseGeoJSON / parseKML / buildGeoJSON / buildKML
└── src/**/*.test.js
```

`ToolsSidebar.jsx` = `ExportSidebar.jsx` **sans** la section Télécharger.
On renomme pour ne pas mentir. On **ne crée pas** `AgentPanel.jsx`.

---

## 7. Copier / adapter / inventer / jeter

### On copie (presque mot pour mot)

| Source | Destination | Note |
|---|---|---|
| `hooks/useLegContext.js` + tests | `src/hooks/` | Zéro API |
| `utils/simulationRoute.js`, `geo.js`, `escales.js`, `customRouteBriefing.js`, `waypointsFromCollection.js` + tests | `src/utils/` | `waypointsFromCollection` sert le **Terminer** du crayon, pas un fichier |
| `components/SimulationPanel.jsx` | idem | |
| `i18n/fr.js`, `en.js`, `LangContext.jsx` | `src/i18n/` | On peut laisser des clés mortes (export, agents, polarChat) |
| `constants/itineraryPoints.ts` + `assets/img/flags/*` | `src/constants/` + `public/flags/` | `.js` suffit |
| `polar_engine.py` | `server/polar_engine.py` | |
| `polar_api/main.py` : helpers + **upload / get / summary** | `server/polar_api.py` | **Couper** tout ce qui est `chat` |
| `naviguide-api/main.py` : searoute → `/route`, proxies, wind/wave/current, `_sim_*` | `server/route_engine.py` + `main.py` | Extraire, **pas** les 1500 lignes d’un bloc ; **pas** les routes `/agents` |
| `frontend/.../map/constants.js` (styles) | `src/layers/styles.js` | + `TILE_URLS.light` |
| `layerOrder.js`, `points.js` | `src/layers/` | + pane `boat` |
| `backend/data/route.geojson` | `public/route.geojson` | fallback interne |
| `Leopard46_Standard_Sails.csv` + logos | `public/` | |

`ITINERARY_POINTS` **est** la liste des stops Berry. Les drapeaux font
partie de l’UX.

### On adapte (nouvelle colle Leaflet + cockpit allégé)

| Idée prise chez | Ce qu’on change |
|---|---|
| `App.jsx` (~1800 lignes) | Même **état** route / draw / sim / briefing. On retire `handleRouteImport` **fichier**. On garde l’activation d’une `FeatureCollection` **née du crayon** (`handleCustomRoute` est un meilleur nom). Le JSX `<Map>` MapLibre devient `useSimulatorMap` |
| `Sidebar.jsx` | BerryCard **sans** `parseGeoJSON` / `parseKML` / inputs fichier. **Pas** de `PolarChatSection`. **Pas** d’`AgentPanel` |
| `ExportSidebar.jsx` | Devient `ToolsSidebar.jsx` : on jette `downloadFile`, `buildGeoJSON`, `buildKML`, les deux boutons Télécharger |
| `CatamaranMarker.jsx` | Même rotation / flip ; `L.marker` + `L.divIcon` |
| `useMarkerOffsets` | Recalcul en pixels Leaflet (`latLngToLayerPoint`) |
| `MaritimeLayers.jsx` | Plus de `Source`/`Layer` MapLibre ; hooks `useXLayer` Leaflet + Science + Climatologie |
| `LayerFichePopup` | `L.popup` |
| Clic route / ZEE | hit-test Leaflet |
| Fetch polar | `VITE_API_URL=''` + proxy Vite, plus `localhost:8004` |

### On n’invente pas

Pas de nouveau format de route. Pas de nouvelle API publique prod. Pas
de nouveau modèle Gold. Le stub `ici()` fixe la **forme** du JSON pour
l’étape 2.

### On jette (ne pas copier, même « pour plus tard »)

- `AgentPanel.jsx`
- `naviguide-api/agents/` (`custom`, `guard`, `meteo`, `pirate`,
  `deploy_ai`)
- `PolarChatSection` / `PolarChatBubble`
- `parseGeoJSON`, `parseKML`, `stemName` côté import fichier
- `buildGeoJSON`, `buildKML`, `downloadFile`, `ExportButton`
- `polar_api` : `PolarChatRequest`, `polar_chat`,
  `_build_polar_system_prompt`, `_polar_fallback_reply`
- `llm_cascade.py`, `polar_agent.py`

---

## 8. Backend du simulateur

Fichier unique `server/main.py`, port **8010**.

### 8.1 `GET /route`

Contrat **identique** à `naviguide-api` :

```
GET /route?start_lat=&start_lon=&end_lat=&end_lon=&check_wind=false
→ Feature | FeatureCollection
```

Pipeline à copier dans `route_engine.py` (dans cet ordre, déjà éprouvé) :

1. `sr.searoute(start, end)`
2. Préfixer / suffixer l’origine et la destination exactes si > 1 km
3. `avoid_land` (masque `global_land_mask` + STRtree NE **si**
   `geo_data/` est présent)
4. `_densify_coords(max_km=75)`
5. `_sanitize_route_coords`
6. second `avoid_land`
7. cache bidirectionnel (`_route_cache_key`, `lru_set`)

`geo_data/ne_10m_*.shp` **n’est pas dans le dépôt** aujourd’hui. Le
code prod tolère l’absence (`_NE_TREE is None`). On documente : masquer
haute résolution = option ; sans shapefiles, `global_land_mask` suffit
pour l’étape 1.

**Interdit :** charger `eez_world_map.geojson` (18 Mo) « pour aider
searoute ».

### 8.2 Polar — voir §9

Monté sous `/api/v1/polar/*` **sans** `/chat`.

### 8.3 Proxies et Copernicus

Copies de `naviguide-api/main.py` :

- `/proxy/zee/wms` — tuiles VLIZ `eez_boundaries`
- `/proxy/zee` — WFS bbox (clic ZEE)
- `/proxy/ports` — WPI
- `/proxy/seamark/{z}/{x}/{y}.png` — repli ; le front essaie d’abord
  `tiles.openseamap.org`
- `POST /wind|/wave|/current` — Copernicus si `COPERNICUS_USERNAME` /
  `COPERNICUS_PASSWORD`, sinon `_sim_*`

### 8.4 Ce que le backend **n’expose pas**

- `POST /agents/{custom,guard,meteo,pirate}`
- `POST /api/v1/polar/chat`
- `POST /simulation/position` (le snap vit déjà dans `useLegContext`,
  côté front, sans API)

---

## 9. Polar engine (sans chat)

### 9.1 Bibliothèque (`server/polar_engine.py`)

Comportement à préserver (déjà testé en prod) :

- `PolarData.speed(twa, tws)` — bilinéaire + fade TWA→0 + plateau TWS
- `optimal_upwind` / `optimal_downwind` / `optimal_gybe_angle`
- `summary()` pour TWS 8, 10, 12, 16, 20, 25
- `generate_full_grid()` → 181×61
- `parse_polar_csv` / `parse_polar_excel` / `parse_polar_pdf` /
  `parse_polar_text`

Dépendances : `numpy`, `pandas`, `openpyxl`, `pdfplumber` (PDF texte) ;
`pytesseract` + `pdf2image` **optionnels** (PDF scannés). Sans
Tesseract, un PDF image → 422 honnête (« PDF image : installez
tesseract »).

### 9.2 API (`server/polar_api.py`)

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/api/v1/polar/upload` | multipart `file` + `expedition_id` + `boat_name` |
| GET | `/api/v1/polar/{id}` | grille complète (le front **ne la télécharge pas** pour l’UI) |
| GET | `/api/v1/polar/{id}/summary` | VMG seul |

**Pas de** `POST /api/v1/polar/chat`.

`expedition_id` par défaut : `berry-mappemonde-2026`.

Stockage : `server/polar_data/polar_{id}.json` (gitignore).

### 9.3 UI (panneau droit seulement)

Comportement **pixel-contrat** avec NAVIGUIDE **moins le chat** :

1. Au montage, fetch `/Leopard46_Standard_Sails.csv` → upload
   automatique « Leopard 46 ».
2. Drop zone PDF / CSV / XLSX, badge Analysing / Chargé / Échec.
3. Tableau VMG (près | portant) pour les 6 TWS.
4. **Aucun** champ de saisie « Chat » dans la sidebar gauche.

Le récit sur les polaires, plus tard, passera par le briefing
d’événement (« sur cette jambe, à 12 kt de vent, VMG près … ») — pas
par un Q&A libre.

### 9.4 Tests moteur (sans UI)

`server/tests/test_polar_engine.py` :

- CSV Leopard 46 se parse ;
- `speed(90, 12)` > 0 ;
- `summary()[12]` a `upwind` et `downwind` ;
- `generate_full_grid().shape == (181, 61)` ;
- TWA 0 → vitesse 0.

`server/tests/test_polar_api.py` (optionnel mais utile) : `POST /upload`
du CSV puis `GET /summary` ; **aucun** test `/chat`.

---

## 10. UI / UX NAVIGUIDE (ce qui reste)

C’est **le** critère de l’étape 1 côté skipper. On porte l’écran, on
change le projecteur, on **retire** les trois exclusions.

### 10.1 Colonne gauche — `Sidebar.jsx` (320 px, `slate-900`)

De haut en bas, **dans cet ordre** :

1. Logo NAVIGUIDE.
2. **BerryCard** — états `berry-active` / `draw-mode` /
   `file-active` / `berry-active-file-loaded` : **Dessiner**, Terminer,
   Continuer, Supprimer, bascule Berry ↔ perso. **Pas** GeoJSON / KML.
3. Pastilles de couches.
4. Bouton simulation (Play / quitter).
5. Si simulation ON : `SimulationPanel` **seulement**.
6. Encadré « Pour commencer » s’il n’y a pas encore de plan.
7. **Briefing** (texte orchestrateur, ou `buildLocalCustomBriefing` sur
   une route perso, ou hint pendant le tracé). Plus tard : récit
   d’événement.

**Pas** de Polar Chat entre 6 et 7.

Toggle flottant `left-4` / `left-[322px]`.

### 10.2 Colonne droite — `ToolsSidebar.jsx` (320 px, liseré ciel)

1. FR / EN.
2. Sombre / Clair (bascule le fond Esri : `TILE_URLS.dark` / `.light`).
3. Stats de route (nm, segments, points).
4. Drop polaire + tableau VMG.

**Pas** de section « Télécharger » / Export GeoJSON / Export KML.

Toggle flottant `right-4` / `right-[322px]`.

### 10.3 Chrome carte (hors couches)

Portés depuis `App.jsx` :

- overlay « Calcul des routes… » puis pastille `routesProgress` ;
- bandeau de tracé (vert, undo / redo, spinner searoute) ;
- drapeaux d’escales + hover ;
- popup satellite (onglets Vent / Vague / Courant +
  `WindDirectionArrow`) ;
- popup fiche couche (`LayerFichePopup`) ;
- édition nom / drapeaux d’un waypoint **tracé** ;
- toast presse-papiers s’il existe déjà.

### 10.4 Briefing — l’emplacement du projet

Même contrat **client** que NAVIGUIDE, **un seul** texte :

- Berry : `POST …/expedition/plan/berry-mappemonde` **si**
  `VITE_ORCHESTRATOR_URL` est défini **et** que le service répond ;
  sinon cache `localStorage` 24 h, sinon l’encadré « Pour commencer »
  suffit.
- Perso (route **dessinée**) : `POST …/expedition/plan` 8 s max, sinon
  `buildLocalCustomBriefing`.

On **ne copie pas** `naviguide_orchestrator/`. Sans orchestrateur,
l’UX reste complète (texte local). On n’ajoute **pas** 4 onglets pour
« remplir » le vide : le vide est volontaire, c’est là que le récit
arrivera.

### 10.5 Ce qui n’est **pas** de l’UX NAVIGUIDE (on n’ajoute pas)

- Onglets Console / Review / Swarm.
- Grille de dons HelloAsso.
- Mode « un layer = un mode opérateur ».
- Les 4 chats et le chat polar (même s’ils existent dans NAVIGUIDE
  aujourd’hui : le skipper les a **retirés** pour ce projet).

---

## 11. BerryCard sans import

Aujourd’hui (`Sidebar.jsx` L.232–441) la carte a 4 états, et
`import-mode` montre **GeoJSON + KML + Dessiner**.

On **simplifie** :

| État | Affichage |
|---|---|
| `berry-active` | Logo Berry + bouton **Dessiner votre route** |
| `draw-mode` (ou `isDrawing`) | Switcher s’il existe déjà une perso ; **Terminer** ; pas de fichiers |
| `file-active` | Switcher Berry \| Route perso ; **Continuer** ; **Supprimer** |
| `berry-active-file-loaded` | Switcher (Berry allumé) + lien pour retracer |

Règles :

- Clic « Dessiner » → `onDrawStart` (pas de `setCardMode("import-mode")`
  qui ouvre des `<input type="file">`).
- **Terminer** → `onDrawFinish()` renvoie une `FeatureCollection`
  **en mémoire** → `setCustomRoute`. Ce n’est **pas** un import
  disque. On peut garder le nom interne `importedGeoJSON` le temps du
  port, mais mieux : `drawnRoute`.
- **Supprimer** → retour Berry.
- **Aucun** `parseGeoJSON` / `parseKML` / `geoJsonRef` / `kmlRef`.

Les libellés i18n `importOrDraw`, `clickToImport`, `clickNewImport`
deviennent `drawOwnRoute` / `drawNewRoute` (ou on réutilise
`drawOwnRoute` déjà existant).

---

## 12. Carte Leaflet et panes

Création (une fois, `useSimulatorMap`) :

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

Fond : `TILE_URLS.dark` par défaut, `TILE_URLS.light` si `isLightMode`.
**Pas** de MapLibre, **pas** de PMTiles.

| Pane | z-index | Contenu |
|---|---|---|
| `tilePane` | 200 | Fond Esri |
| `zee-wms` | 250 | Tuiles ZEE |
| `balisage` | 260 | OpenSeaMap |
| `route` | 380 | Polyligne Berry / perso / tracé (vert pendant le draw) |
| `amp` | 420 | Polygones AMP |
| points canvas | renderer | projets, marinas, … |
| `markerPane` | 600 | drapeaux, WPI |
| `boat` | 620 | catamaran |
| `popupPane` | 700 | popups |

Test `panes.test.js` (même discipline que
`frontend/src/components/map/__tests__/layerOrder.test.js`).

**Antiméridien :** searoute + `_normalize_antimeridian` déjà dans le
pipeline. Si fallback GeoJSON : deux `LineString` Wallis→Nouméa, **ne
pas** les fusionner. `flyTo` : `[lat, lon]` (Leaflet), longitude dans
]−180, 180].

CSS : `leaflet/dist/leaflet.css`. Pas d’icône par défaut Leaflet
(divIcon / circleMarker uniquement) — évite le piège Vite
`marker-icon.png`.

---

## 13. Film Berry : searoute, bateau, fallback

### 13.1 Construction des jambes

Copier le `useEffect` « Fetch des segments » de `App.jsx` (L.523–676)
dans un module `src/utils/berryLegs.js` (testable) :

- `nonMaritimeNames` : Saint-Maur|La Rochelle et retour ;
- `skipFromNames` : Marigot, Cayenne, Halifax, Saint-Pierre ;
- inserts : Marigot→Cayenne, Halifax→SPM, SPM→Halifax, Cayenne→Papeete ;
- `SEGMENT_BATCH_SIZE = 4` ;
- `orientCoords` ;
- `check_wind: false` sur le fetch initial (le vent = clic, pas 40×
  Copernicus).

### 13.2 Fallback `routeFromOfficial.js`

Si `GET /route` échoue pour **toutes** les jambes du premier lot :
charger `/route.geojson`, convertir :

```
LineString + from/to/type  → segments (nonMaritime ⇔ type === "overland")
Point + point_type         → stops (flag ⇔ escale)
```

Afficher un bandeau discret : « Route officielle (searoute
indisponible) ».

Ce n’est **pas** un import skipper.

### 13.3 Simulation

Chaîne déjà éprouvée :

```
segments + stops
  → buildSimTargets()
  → simulationStartPos()
  → useLegContext(lat, lon, segments, stops, speedKnots, simulationStep)
```

Contrôles : `handleSimNext` / `Prev`, snap,
`map.flyTo([lat, lon], { duration: 0.8 })`, drag → re-snap. Changement
de route (`customRoute`) → bateau au départ.

`speedKnots` : 7, ou polar×vent si les deux sont là (§5.4).

### 13.4 Marqueur bateau

Port de `CatamaranMarker.jsx` : image, transparence canvas, rotation
est/ouest + hémisphère sud, pane `boat`. Sans image : triangle CSS
cyan.

---

## 14. Draw your own route

**Pas** des segments droits. Contrat = `App.jsx` L.287–445 + bandeau
L.913+.

| Action | Comportement |
|---|---|
| Dessiner | `drawingMode=true`, cache Berry, curseur croix, simulation OFF |
| Clic 1 | pose le point, pas de fetch |
| Clic 2+ | `GET /route?start_lat…` entre le précédent et le nouveau ; polyligne **verte** |
| Undo | retire point + segment, invalide le fetch en vol (`fetchIdRef`) |
| Redo | restaure point + segment |
| Terminer | `drawnSegments` + `drawnPoints` → FeatureCollection **mémoire** → `customRoute` ; trait **bleu** |
| Continuer | reprend les points déjà là |
| Supprimer | retour Berry, `applyBerryBriefing` |
| Revenir à Berry | `customRoute = null`, les segments searoute Berry (ou le fallback) réapparaissent |

**Pas** d’import `.geojson` / `.kml`.

Pendant le tracé : Berry / perso **masqués** (`drawnLines` seulement).
`canFinishDraw` = ≥ 2 points **et** pas de fetch en cours.

Si searoute échoue sur **un** segment : garder le point, ligne droite
**en pointillés orange** + pastille « searoute a échoué — corde
temporaire ». On n’abandonne pas le tracé.

Waypoints tracés : clic → nom + drapeaux (`handleSaveDrawPointMeta`).

---

## 15. Boutons de couches (légende du cockpit)

Même UI que `Sidebar.jsx` L.502–531 : pastilles `rounded-full`, point
coloré, spinner, bordure rouge si erreur.

NAVIGUIDE aujourd’hui a **8** pastilles (`ALL_LAYER_CONFIG`). Le
simulateur en ajoute **2** (Science, Climatologie) — ce sont les
couches « seulement BI » / « pas encore une couche carte ».

| Clé | Libellé | Couleur | Source | Défaut |
|---|---|---|---|---|
| `zee` | ZEE | `#0e7490` | WMS VLIZ via `/proxy/zee/wms` | ON |
| `wpi` | Ports WPI | `#f59e0b` | `/proxy/ports` | OFF |
| `balisage` | Balisage | `#10b981` | tuiles OpenSeaMap (direct, proxy en repli) | OFF |
| `projects` | Projets | `#06b6d4` | `/bi/export/geojson` | OFF |
| `marinas` | Marinas | `#ef4444` | `/bi/export/marinas.geojson` | OFF |
| `capitaineries` | Capit. | `#7dd3fc` | `/bi/export/capitaineries.geojson` | OFF |
| `poe` | PoE | `#d97706` | `/bi/export/poe.geojson` | OFF |
| `amp` | AMP | `#22c55e` | `/bi/amp?bbox=` (polygones) | OFF |
| `science` | Science | `#a78bfa` | `/bi/export/science.geojson` | OFF |
| `climatology` | Climat | `#38bdf8` | **aucun fetch** — bandeau stub | OFF |

Règles : fetch au premier ON ; AMP bbox debounce 420 ms ; marinas /
projets en **canvas** ; ZEE = WMS limites, pas le GeoJSON 18 Mo ;
climatologie = pastille + bandeau (« régime de vent : étape 6 »).
`climatology.py` n’est **pas** une couche monde.

État : `{ show, loading, error, data }`. Aucune couche n’est « le mode
actif ».

---

## 16. Stub `ici()` — le sac vide

Fichier : `src/engine/ici.js`.

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
    polar: null,     // étape 1 : { boat, vmgHint } SI chargé — jamais la grille
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

Appelé à chaque `legContext.snappedPosition`. Affichage : `<details>`
« Dossier cockpit » sous le briefing. **Interdit** d’y coller les
FeatureCollections allumées sur la carte.

Ce JSON est le contrat du **projet**. En étape 1 il est presque vide :
c’est honnête. On ne le remplit pas avec un chat.

---

## 17. Données, ports, variables

`vite.config.js` (dev seulement) :

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

**Pas** de proxy `/agents`.

On ne crée **aucune** route dans `backend/` ni `naviguide/`. On ne
déploie rien sur le VPS.

| Si… | Alors… |
|---|---|
| Backend simulateur down | Berry via `public/route.geojson`. Polar / draw / ZEE WMS / WPI = erreur honnête. Balisage OK (tuiles publiques) |
| Backend simulateur up, BI down | Film + polar + searoute + ZEE/WPI OK. Pastilles BI = erreur |
| Les deux up | Toutes les couches lecture seule |

Variables :

- `VITE_API_URL=` (vide = même origine, proxy Vite)
- `VITE_POLAR_API_URL=` (idem)
- `VITE_BI_BASE=/bi`
- `VITE_ORCHESTRATOR_URL=` **optionnel**
- `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` — optionnel (sinon
  `_sim_*`)

**Aucune** clé Tavily. **Aucune** clé LLM n’est requise pour l’étape 1
(plus de chat local). L’orchestrateur, s’il tourne déjà, peut avoir
les siennes — ce n’est pas le dossier simulateur.

**Ne jamais** lancer `infra/vps/sync-from-atlas.sh`. Le simulateur ne
parle pas à Mongo.

---

## 18. Ordre de chantier (1.0 → 1.9)

Ne pas commencer le polar (1.5) si searoute (1.2) n’avance pas : sans
trait, pas de film. Ne pas commencer les couches (1.7) si l’UX (1.4)
n’est pas posée : les pastilles n’ont nulle part où vivre.

### 1.0 — Squelette Vite + FastAPI

- `package.json` : react, react-dom, leaflet, lucide-react, tailwind 4,
  `@tailwindcss/vite`, `@vitejs/plugin-react`. **Pas** de `maplibre-gl`
  ni `react-map-gl` ni `searoute-js`.
- Scripts : `dev`, `build`, `preview`, `test`, `server`.
- `server/requirements.txt` : fastapi, uvicorn, searoute, geographiclib,
  shapely, global-land-mask, numpy, pandas, openpyxl, pdfplumber,
  python-multipart, httpx, python-dotenv (+ optionnels pytesseract,
  copernicusmarine). **Pas** d’anthropic / langgraph « pour les
  agents ».
- `README.md` : deux commandes, ports 5174 / 8010, « prod intouchée »,
  tableau « on a / on n’a pas » (pas de chats, pas d’import/export).
- Recette : page « NAVIGUIDE simulator » + `GET http://localhost:8010/`
  → `{ "service": "naviguide-simulator" }`.

### 1.1 — Carte + fond + panes

- `useSimulatorMap` : `L.map`, tuile dark, `invalidateSize`, thème clair.
- `createPanes` + test d’ordre.
- CSS Leaflet.

### 1.2 — searoute + route Berry

- Extraire `route_engine.py` + `GET /route`.
- Test Python : une jambe courte mer (ex. La Rochelle → un point à
  20 nm au large) renvoie une `LineString` ≥ 2 points.
- `berryLegs.js` + fetch par lots + pastille de progression.
- Fallback `routeFromOfficial` + tests (overland, antiméridien = 2
  segments).
- `useRouteLayer` : casing + trait, overland en tirets, escales, verts
  pendant le draw.

### 1.3 — Bateau qui avance

- Copier `useLegContext`, `simulationRoute`, `geo`, `escales` + tests.
- `SimulationPanel`, `CatamaranMarker`, `flyTo`.
- Recette : 5× Suivant depuis Saint-Maur → golfe de Gascogne / approche
  Corse, cap et nm qui changent.

### 1.4 — UI / UX (chrome allégé)

- `Sidebar` : BerryCard **sans import**, pills, sim, briefing.
- `ToolsSidebar` : langue, thème, stats (polar encore « API absente »
  si 1.5 n’est pas prêt).
- **Vérifier l’absence** de : boutons GeoJSON/KML, boutons Export,
  Polar Chat, 4 onglets agents.
- Recette : on reconnaît NAVIGUIDE, on ne voit **pas** les chats.

### 1.5 — Polar engine (sans chat)

- Copier `polar_engine.py` + routes upload/get/summary + CSV défaut.
- Tests §9.4.
- Brancher drop / VMG / auto-Leopard 46.
- (Plus tard dans 1.5) `speedKnots` depuis polar×vent.
- Recette négative : `POST /api/v1/polar/chat` → **404**.

### 1.6 — Draw your own route

- Handlers `App.jsx` + bandeau undo/redo + Terminer / Continuer /
  Supprimer.
- Recette : 3 clics Atlantique, trait **qui évite les terres**,
  simulation sur **cette** ligne, retour Berry.
- Recette négative : aucun `<input type="file" accept=".geojson">`.

### 1.7 — Pastilles + dessin des couches

Ordre : Balisage → ZEE WMS → WPI → PoE → AMP → Science → Projets →
Capitaineries → Marinas (OFF, canvas) → Climatologie stub.

### 1.8 — Clic route (vent / vague / courant)

- `POST /wind|/wave|/current` + popup 3 onglets.
- Recette : clic sur le trait → chiffres (réels ou `_sim_*`), pas de
  crash. **Pas** d’appel agent.

### 1.9 — Stub `ici()` + polish

- `ici.js` + test des clés.
- Disclaimer *Ne convient pas à la navigation*.
- README final : tableau « ça marche / ça n’existe pas encore ».
- Une ligne dans le `README.md` **racine** seulement quand 1.0 existe.

**Critère « étape 1 terminée » :** un skipper débutant lance les deux
commandes, reconnaît NAVIGUIDE, avance le bateau sur Berry, charge /
voit les polaires Leopard 46, trace 3 points **searoute**, allume AMP
(si BI local) ou voit une erreur claire, **ne trouve aucun chat** ni
bouton import/export, et comprend que le récit d’événement (`ici()`
plein) n’est pas là. Sans ça, on ne passe pas à l’étape 2.

---

## 19. Fichiers touchés / interdits

### On crée

- tout `naviguide-simulator/**`
- ce document (déjà)

### On peut ajouter, quand le squelette 1.0 existe

- une ligne dans le `README.md` racine : « Simulateur (hors prod) :
  `naviguide-simulator/` — voir
  `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` »

### On n’ouvre pas

- `frontend/src/**`
- `backend/app/**`
- `naviguide/naviguide-app/**`, `naviguide/naviguide-api/**`,
  `naviguide/polar_agent/**` (on **lit** pour copier, on **n’édite
  pas**)
- `infra/vps/**`
- les workflows CI de la prod

Si l’étape 2 a besoin d’un `GET /api/ici?lat=&lon=`, ce sera une route
**du serveur simulateur**, pas de la prod. Pas maintenant.

---

## 20. Recette

Machine : **macOS**, Terminal. Trois onglets suffisent (serveur, front,
éventuellement BI).

### A. Film + searoute + polar (backend simulateur)

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
```

Autre onglet :

```bash
cd naviguide-simulator
npm install
npm run dev
```

Ouvrir `http://localhost:5174`.

| # | Action | Attendu |
|---|---|---|
| A1 | Page charge | Deux sidebars, carte sombre, spinner puis trait Berry |
| A2 | Polaires (panneau **droit**) | Tableau VMG Leopard 46 (ou erreur claire si parse KO) |
| A3 | Simulation → Suivant × 3 | Bateau avance, from/to, nm, cap. **Pas** d’onglets Ports/Météo/… |
| A4 | Précédent | Retour d’un cran, pas de saut Cap-Vert |
| A5 | Dessiner 3 clics mer | Trait **vert** qui contourne la terre, undo marche |
| A6 | Terminer | Trait bleu, briefing local, simulation sur **cette** route |
| A7 | « Berry-Mappemonde » | Retour à l’officielle searoute |
| A8 | Panneau droit | Langue, thème, stats, polar — **pas** de boutons Export |
| A9 | BerryCard | Dessiner / Continuer / Supprimer — **pas** GeoJSON / KML |
| A10 | Clic sur le trait | Popup vent / vague / courant (réel ou simulé) |
| A11 | `<details>` dossier | `zee: null`, `polar.boat` si chargé |
| A12 | Clair / FR | Fond Esri light, libellés anglais→français |
| A13 | Sidebar gauche | Briefing (ou « Pour commencer ») — **pas** de Chat polar |

### B. Film seul (backend simulateur **éteint**)

| # | Action | Attendu |
|---|---|---|
| B1 | Recharger | Trait depuis `public/route.geojson`, bandeau « searoute indisponible » |
| B2 | Dessiner | Erreur honnête, pas de page blanche |
| B3 | Polar | Badge Échec, le reste vit |

### C. Couches BI (optionnel)

Backend Blue Intelligence sur `:8001`. Recharger.

| # | Action | Attendu |
|---|---|---|
| C1 | PoE ON | Pastilles ambre, popup nom |
| C2 | AMP ON, zoom Caraïbes | Polygones verts |
| C3 | Marinas ON | Carte fluide (canvas) |

### D. Tests auto

```bash
cd naviguide-simulator && npm test
cd naviguide-simulator && .venv/bin/python -m pytest server/tests -q
```

Doivent passer : `berryLegs`, `routeFromOfficial`, `simulationRoute`,
`geo`, `ici`, `panes`, `polar_engine`.

### E. Recettes négatives (régressions interdites)

| # | Action | Attendu |
|---|---|---|
| E1 | Chercher « Ports / Sécurité / Météo / Cruisers » | Absent |
| E2 | `curl -X POST http://localhost:8010/api/v1/polar/chat` | 404 |
| E3 | `curl -X POST http://localhost:8010/agents/meteo` | 404 |
| E4 | Chercher un bouton « GeoJSON » / « KML » / « Exporter » | Absent |
| E5 | `grep -R AgentPanel naviguide-simulator/src` | Aucun fichier |

---

## 21. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Recopier `Sidebar.jsx` **tel quel** (chat + agents + import) | Haute | Port **chirurgical** : retirer avant le premier commit UI |
| Recopier `useAmpLayer` avec `mode === "amp"` | Haute | Nouveaux hooks toggle |
| Recoller le simulateur à `naviguide-api:8000` | Haute | Backend **8010** dans le dossier |
| Utiliser `searoute-js` « pour aller plus vite » | Haute | Inutilisé en prod ; Python uniquement |
| Remettre les 4 chats « le temps que le projet arrive » | Produit | Le Briefing **est** l’emplacement ; les 4 chats noient le juge |
| Remettre l’import « au cas où » | Produit | Draw + Berry suffisent ; fichier = hors contrat |
| Allumer Marinas par défaut | Moyenne | OFF + canvas |
| Charger `eez_world_map.geojson` | Haute | WMS limites |
| `flyTo([lon, lat])` (ordre MapLibre) | Haute | Leaflet = `[lat, lon]` ; tester Corse |
| Antiméridien Wallis–Nouméa | Moyenne | 2 LineString / normalisation searoute |
| Import runtime depuis `frontend/` ou `naviguide/` | Haute | copies |
| Toucher nginx / VPS « pour tester » | Bloquante | localhost seulement |
| Avaler la grille 181×61 dans `ici()` | Produit | `vmg_summary` seulement |
| PDF scanné sans Tesseract | Basse | 422 + message |
| Croire l’étape 1 « prête pour Nemotron » | Produit | sac vide = honnête ; étape 2 ensuite |
| Copier `polar_agent.py` Deploy AI | Moyenne | `polar_engine` + 3 routes, point |

---

## 22. Passage à l’étape 2

L’étape 2 peut commencer **uniquement** si A1–A7, A11 et E1–E5 passent.

Alors on remplit le sac, **sans** Tavily :

1. Quelle ZEE contient le point (`zee_crossings` / shapely) — **1**
   polygone, nom, mrgid, Gold oui/non.
2. PoE de **cette** ZEE + URL.
3. AMP / projets / 3–5 marinas-capit-WPI dans 20–30 nm.
4. Événement « on entre dans cette ZEE ».
5. `polar` : déjà amorcé (bateau + VMG) ; y ajouter vitesse / ETA **de
   cette** jambe.
6. Le **Briefing** raconte ce JSON (Nano / Lightning). Ce n’est
   **toujours pas** 4 chats.

Nano / Tavily / Ultra restent aux étapes 5–6. Stretch AMP « parc,
saison, mouillage » et overlay climatologie = après le sac.

Rappel du contrat global :

> Les boutons allument toute la couche. Le LLM n’en voit qu’une poignée.
> Un pas = `ici()` gratuit. Tavily = entrée de ZEE, clic skipper, ou
> alerte.
> Polar et searoute parlent au **point** et à **cette** jambe, pas au
> globe.
> Un récit, pas quatre agents.

---

## 23. Documents et fichiers dont ce plan hérite

- Discussion produit « simulation = film, `ici()` = moteur, boutons =
  carte » (septembre 2026).
- Arbitrage skipper du 13 septembre **matin** : polar + UX + searoute +
  draw (v2.0).
- Arbitrage skipper du 13 septembre **soir** (celui-ci) : polar **sans
  chat**, UX **sans** 4 agents, **sans** import/export GeoJSON.
- `docs/hackathon-nebius-nvidia.md` — cahier unique (orientations +
  plan pour gagner). Dossier autonome extractible.
- `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` — pas une couche monde à
  l’étape 1.
- `docs/ARCHITECTURE.md` — `MapView.js` + un hook par couche.
- Code vivant :
  - film : `naviguide/naviguide-app/src/App.jsx` (searoute L.523–676,
    draw L.287–445, chrome L.824+), `Sidebar.jsx` (BerryCard L.232–441,
    pills L.502–531, **PolarChat L.16–138 à jeter**, **AgentPanel
    L.573–577 à jeter**), `ExportSidebar.jsx` (polar L.517+ à garder,
    export L.496–515 à jeter), `useLegContext.js`,
    `MaritimeLayers.jsx` ;
  - polar : `naviguide/polar_agent/polar_engine.py`,
    `naviguide/naviguide_workspace/polar_api/main.py` (L.151–270 oui,
    L.273–375 chat non) ;
  - searoute : `naviguide/naviguide-api/main.py`
    (`searoute_with_exact_end`, `avoid_land`, `GET /route`) ;
  - projecteur : `frontend/src/components/MapView.js`,
    `frontend/src/components/map/*` ;
  - fallback interne : `backend/data/route.geojson` ;
  - exports **lecture** couches : `GET /api/export/*`,
    `GET /api/amp?bbox=`.

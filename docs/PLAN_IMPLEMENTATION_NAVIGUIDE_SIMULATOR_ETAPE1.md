# Plan d’implémentation — `naviguide-simulator/` étape 1

Document de chantier. Il fige **comment poser le dossier** dans ce dépôt, et
**quoi coder en premier**.

Version **2.0** — 13 septembre 2026.

**Ce que la 2.0 change par rapport à la 1.0**

La 1.0 excluait le polar engine, searoute, et réduisait la sidebar à un
« film mince ». Le skipper a tranché autrement pour l’étape 1 :

| Décision 1.0 (annulée) | Décision 2.0 (celle-ci) |
|---|---|
| Route officielle figée, **pas** searoute | **searoute** pour Berry **et** pour « draw your own route » |
| Polar engine hors périmètre, ETA @ 7 kt | **Polar engine complet** (parse, grille 181×61, VMG, upload, chat) |
| Sidebar mince, pas d’Export, pas de Polar Chat | **UI / UX complète de NAVIGUIDE** (les deux panneaux, BerryCard, briefing, chats, export) |
| Tracer = segments **droits** | Tracer = **searoute** jambe par jambe, undo / redo, continuer, terminer |

Ce qui **ne change pas** : sous-dossier extractible, **Leaflet** (plus de
MapLibre), prod `naviguide.fr` / `blueintelligence.online` **intouchées**,
pas de Console / Review / Swarm, `ici()` encore un **sac vide** (étape 2).

Les étapes 2 à 6 (sac réel, événements ZEE, Gold, Tavily, Nemotron) sont
rappelées pour ne pas les commencer trop tôt — **elles ne sont pas livrées
ici**.

**Sommaire**

1. En une phrase
2. Pourquoi cette étape existe
3. Ce que l’on livre
4. Ce que l’on ne livre pas
5. Vocabulaire
6. Décisions d’architecture (verrouillées)
7. Arborescence cible
8. Copier / adapter / inventer
9. Backend du simulateur (searoute + polar + proxies)
10. Polar engine complet
11. UI / UX complète de NAVIGUIDE
12. Carte Leaflet et panes
13. Film Berry : searoute, bateau, fallback
14. Draw your own route
15. Boutons de couches
16. Stub `ici()`
17. Données, ports, variables
18. Ordre de chantier (1.0 → 1.10)
19. Fichiers touchés / interdits
20. Recette
21. Risques
22. Passage à l’étape 2
23. Documents dont ce plan hérite

---

## 1. En une phrase

Créer `naviguide-simulator/` dans **ce** dépôt : le **cockpit NAVIGUIDE
complet** (deux sidebars, polaires, searoute, tracer sa route), projeté sur
une carte **Leaflet** avec les boutons de couches, **sans** toucher
`naviguide.fr` ni `blueintelligence.online`.

---

## 2. Pourquoi cette étape existe

Le produit hackathon, ce n’est pas un deuxième Blue Intelligence. C’est le
**film** : le bateau avance, on voit la carte du cockpit, et plus tard un
petit dossier « vu d’ici » nourrit un récit.

Sans l’étape 1, il n’y a ni cockpit, ni position, ni boutons. Le moteur
`ici()` (étape 2) n’aurait rien autour de quoi travailler.

L’étape 1 **n’appelle pas** Tavily ni Nemotron. Elle prépare :

- le **projecteur** (Leaflet + légende) ;
- le **film** (route Berry, bateau, tracer / importer) ;
- le **moteur bateau** (searoute + polar), pour que l’ETA et le trait
  soient ceux du skipper, pas une ligne droite à 7 nœuds.

---

## 3. Ce que l’on livre

À la fin de l’étape 1, en local :

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010 --reload   # un Terminal
npm install && npm run dev                     # un autre Terminal
```

Ouvrir `http://localhost:5174`. On voit **la même UX skipper que NAVIGUIDE**,
sur Leaflet :

1. **Deux panneaux** 320 px : gauche (expédition) et droite (export / polaires),
   FR / EN, sombre / clair.
2. **BerryCard** : route Berry, import GeoJSON / KML, **draw your own route**,
   continuer, terminer, supprimer, bascule Berry ↔ perso.
3. **Route Berry** calculée **jambe par jambe via searoute** (même logique
   d’escales que `App.jsx` : overland Berry↔La Rochelle, skip Marigot / Halifax,
   Halifax↔SPM maritime, Cayenne→Papeete). Spinner + pastille de progression.
4. **Mode simulation** : Précédent / Suivant, bateau collé à la route
   (`useLegContext`), drag, `flyTo`.
5. **Polar engine complet** : CSV Leopard 46 chargé tout seul, drop
   PDF / CSV / XLSX, grille 181×61, tableau VMG, chat polaire.
6. **Draw your own route** : clics carte → `GET /route` searoute (pas une
   corde), undo / redo, bandeau vert, Terminer → la route devient active.
7. **Export** GeoJSON + KML de la route affichée.
8. **Dix boutons** de couches (ZEE, WPI, Balisage, Projets, Marinas, Capit.,
   PoE, AMP, Science, Climatologie) — dessin Leaflet, plusieurs allumées
   ensemble.
9. **Clic route** → vent / vague / courant au point (`POST /wind|wave|current`).
10. **AgentPanel** (Ports / Sécurité / Météo / Cruisers) + **Briefing**
    (cache local 24 h, orchestrateur optionnel, sinon texte local).
11. Stub `ici()` branché à chaque pas (JSON typé, encore vide côté ZEE).
12. `README.md` du dossier : lancer, ports, « prod intouchée ».

**Si le backend simulateur est éteint** : la route Berry se dessine quand
même depuis `public/route.geojson` (copie de `backend/data/route.geojson`).
Le tracer, le polar et les proxies ZEE / WPI affichent une erreur honnête.
Le film ne doit pas être noir.

La prod ne change pas. Aucun merge n’est requis vers `main` pour que
blueintelligence.online ou naviguide.fr restent tels quels.

---

## 4. Ce que l’on ne livre pas

| Interdit en étape 1 | Pourquoi |
|---|---|
| Console, Review, Swarm, 6 modes opérateur | UX Blue Intelligence, pas le cockpit |
| Carte MapLibre / fond PMTiles « carte marine » | On change de projecteur ; Seamap = plus tard, optionnel |
| Isochrones weather-routing (port 3010) | Autre moteur, déjà « pas déployé » en prod |
| Orchestrateur LangGraph **dans** le dossier | Le briefing **appelle** l’existant s’il tourne ; sinon texte local |
| `polar_agent.py` (Deploy AI / Claude Opus) | Chemin mort ; le chat vivant est `polar_api` + `llm_cascade` |
| Tavily, Nemotron, Token Factory | Étapes 5–6 |
| Requêtes spatiales « dans cette ZEE / 30 nm » | C’est `ici()` réel = étape 2 |
| Imports / exports opérateur BI | On **lit** les mêmes URLs, on n’écrit rien |
| Modifier `frontend/`, `backend/`, `naviguide/`, `infra/vps/` | La prod ne bouge pas |
| `react-leaflet` | Les hooks BI parlent à un `L.Map` nu |
| `searoute-js` (npm, **jamais utilisé** dans `App.jsx`) | Le moteur réel est Python `searoute==1.4.3` |
| Coller 4 500 projets dans un prompt | Le LLM du sac n’existe pas encore ici |

Les **4 chats** Ports / Sécurité / Météo / Cruisers **sont dans l’étape 1** :
ils font partie de l’UX NAVIGUIDE demandée. Plus tard, le récit unique
« Briefing d’événement » pourra les remplacer. On ne les retire pas
maintenant.

---

## 5. Vocabulaire

| Mot | Sens ici |
|---|---|
| **Film** | Ce que le skipper voit : deux sidebars, route, bateau, boutons, tracer |
| **Projecteur** | La carte : Leaflet, plus MapLibre |
| **Légende** | Les pastilles ON/OFF (ZEE, WPI, Balisage, …) |
| **Moteur bateau** | searoute (le trait) + polar (la vitesse / le VMG) |
| **Sac à dos / `ici()`** | Petit JSON autour du bateau. Étape 1 = sac **vide** (sauf éventuellement nom du bateau si polar chargé) |
| **Route officielle (fallback)** | `backend/data/route.geojson` → `public/route.geojson` si searoute est down |
| **Escale** | Stop avec drapeau (La Rochelle, Ajaccio…). Un point intermédiaire n’en est pas une |
| **Gold** | Fiche Formalités relue. Inutile à l’étape 1 |
| **Prod** | `blueintelligence.online` et `naviguide.fr` |

---

## 6. Décisions d’architecture (verrouillées)

### 6.1 Un sous-dossier, pas un fork

```
Blue-Intelligence-Map/
├── frontend/                 # prod BI — interdite
├── backend/                  # prod API — interdite
├── naviguide/                # prod NAVIGUIDE — interdite
├── naviguide-simulator/      # NOUVEAU, extractible plus tard (hackathon)
└── docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md
```

Plus tard : `git subtree split` (ou copie propre) vers le dépôt hackathon.
Donc **aucune** import runtime du style `../../frontend/src/...` ou
`../../naviguide/...` : on **copie** les modules, on n’attache pas les deux
apps.

### 6.2 Pile technique

| Choix | Comme… | Pas comme… |
|---|---|---|
| Vite 7 + React 19 + Tailwind 4 | `naviguide/naviguide-app` | CRA de `frontend/` |
| Leaflet 1.9 **nu** (`L.map`) | `frontend/src/components/MapView.js` | MapLibre / `react-map-gl` |
| FastAPI **dans le dossier** (`server/`, port **8010**) | extraits de `naviguide-api` + `polar_api` | appeler la prod, ports 8000 / 8004 |
| Port Vite **5174** | — | 5173 (NAVIGUIDE) et 3000 (CRA) |
| FR d’abord, EN ensuite | i18n NAVIGUIDE **complet** | clés amputées |

Leaflet **sans** `react-leaflet` : Blue Intelligence crée déjà la carte à la
main. Recoller ça dans `react-leaflet` ferait tout réécrire.

### 6.3 Route : searoute d’abord, GeoJSON officiel en secours

NAVIGUIDE aujourd’hui appelle `GET /route?start_lat=…` **jambe par jambe**
(`App.jsx` ~L.523–676, lots de 4). C’est searoute + évitement des terres
(`searoute_with_exact_end` → `avoid_land` → densify → sanitize).

L’étape 1 **refait ce film** :

1. Les stops viennent de `ITINERARY_POINTS` (copie de
   `naviguide-app/src/constants/itineraryPoints.ts`, ~41 points, drapeaux PNG).
2. Les jambes sont **les mêmes** (skip Marigot / Halifax / SPM / Cayenne,
   insert Marigot→Cayenne, Halifax↔SPM, Cayenne→Papeete, overland
   Saint-Maur↔La Rochelle).
3. Chaque jambe maritime = `GET /route` du **backend simulateur**.
4. Orientation A→B (`orientCoords`) : searoute peut renvoyer B→A.
5. Si le backend est down **ou** qu’une jambe échoue : on bascule (toute la
   route, ou jambe par jambe) sur `public/route.geojson` via
   `routeFromOfficial.js`.

**Conséquence :** le film marche **sans** `naviguide-api` de prod. Le
simulateur a **son** `/route`. On ne proxy pas vers `:8000` « pour aller
plus vite » : ça recollerait le dossier à la prod et casserait
l’extraction hackathon.

### 6.4 Polar : le moteur vivant, pas le LangGraph mort

« Polar engine complet » = ce que NAVIGUIDE **utilise vraiment** :

| Fichier source | Rôle |
|---|---|
| `naviguide/polar_agent/polar_engine.py` | Parse PDF / CSV / XLSX, interpolation bilinéaire, grille 181×61, VMG près / portant |
| `naviguide/naviguide_workspace/polar_api/main.py` | `POST /upload`, `GET /{id}`, `GET /{id}/summary`, `POST /chat` |
| `naviguide/naviguide-app/public/Leopard46_Standard_Sails.csv` | Chargé tout seul au démarrage |
| `ExportSidebar.jsx` + `PolarChatSection` | UI |

On **ne copie pas** `polar_agent/polar_agent.py` (Deploy AI, `CLIENT_ID`,
Claude Opus 4.1) : le chat de prod passe déjà par `llm_cascade` dans
`polar_api`. Même contrat : LLM si une clé est là, sinon réponse structurée
sur le tableau VMG.

Le LLM du chat polar **n’avale pas** la grille 181×61 : seulement le
`vmg_summary` (TWS 8 / 10 / 12 / 16 / 20 / 25). C’est déjà le bon « sac ».

**ETA du film :** `useLegContext` reste à 7 kt **tant qu’il n’y a pas de
vent au point**. Dès que `POST /wind` répond, on lit `polar.speed(twa, tws)`
et on passe `speedKnots` au hook. Sans polar chargé : 7 kt. On ne câble
**pas** l’isochrone weather-routing.

### 6.5 Couches : mêmes URLs, nouveau dessin, pas les hooks « un mode »

Blue Intelligence n’affiche **qu’un** mode à la fois. Les recopier tels
quels reproduirait « un mode à la fois ».

**On ne les importe pas.** On **vole** styles / panes / popups / canvas, on
**réécrit** la colle : bouton ON → fetch une fois → `map.addLayer`.
Plusieurs couches allumées ensemble.

Les 4 500 projets restent sur la **carte** si on allume le bouton. Le LLM
(plus tard) n’en verra qu’une poignée via `ici()`.

### 6.6 Simulation : comme NAVIGUIDE, pas forcée ON

Dans le film NAVIGUIDE, la simulation est un **bouton**. L’UX complète =
même geste : OFF au chargement, le skipper appuie. (La 1.0 la forçait ON
parce que le film était réduit. Ici le film **est** NAVIGUIDE.)

### 6.7 Un backend dans le dossier — obligatoire

La 1.0 disait « pas de backend ». Avec searoute + polar, c’est faux.
`searoute-js` est dans le `package.json` NAVIGUIDE et **n’est jamais
importé**. Le moteur est Python.

Un seul process FastAPI (`server/`, **8010**) sert :

- `/route` (searoute + avoid-land) ;
- `/api/v1/polar/*` ;
- `/proxy/zee/wms`, `/proxy/zee`, `/proxy/ports`, `/proxy/seamark` ;
- `/wind`, `/wave`, `/current` (Copernicus si identifiants, sinon
  `_sim_wind` / `_sim_wave` / `_sim_current` déjà dans `naviguide-api`) ;
- `/agents/{custom,guard,meteo,pirate}` (SSE, même contrat que
  `AgentPanel.jsx`).

Pas de second uvicorn polar sur 8004. Tout est derrière le proxy Vite.

---

## 7. Arborescence cible

```
naviguide-simulator/
├── README.md
├── package.json                 # name: naviguide-simulator
├── vite.config.js               # port 5174, proxy /route /proxy /api /bi /agents /wind…
├── index.html
├── public/
│   ├── route.geojson            # fallback (copie backend/data/route.geojson)
│   ├── Leopard46_Standard_Sails.csv
│   └── logo-*.png / flags/
├── server/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI : route + polar + proxy + wind + agents
│   ├── route_engine.py          # extraits de naviguide-api/main.py (searoute → sanitize)
│   ├── polar_engine.py          # copie de naviguide/polar_agent/polar_engine.py
│   ├── polar_api.py             # extraits de polar_api/main.py (chemins locaux)
│   ├── llm_cascade.py           # copie optionnelle ; chat polar / agents si clés
│   ├── mem_limits.py
│   ├── agents/                  # custom, guard, meteo, pirate + context_block
│   ├── copernicus/              # getWind / getWave / getCurrent (copie)
│   ├── polar_data/              # JSON persistés (gitignore)
│   └── geo_data/                # optionnel : NE 1:10m si on les a ; sinon global_land_mask
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
│   │   └── useMarkerOffsets.js  # offsets drapeaux (px Leaflet)
│   ├── i18n/                    # fr.js + en.js COMPLETS (polar, agents, draw…)
│   ├── layers/                  # un hook Leaflet par couche + route
│   ├── components/
│   │   ├── Sidebar.jsx          # copie NAVIGUIDE (BerryCard, pills, sim, agents, polar chat, briefing)
│   │   ├── ExportSidebar.jsx    # copie (langue, thème, stats, polar, export)
│   │   ├── SimulationPanel.jsx
│   │   ├── AgentPanel.jsx
│   │   ├── LayerFichePopup.jsx  # popup Leaflet, plus MapLibre Popup
│   │   ├── CatamaranMarker.js   # L.marker + DivIcon
│   │   └── WindDirectionArrow.jsx
│   └── utils/                   # geo, escales, simulationRoute, customRouteBriefing,
│                                # waypointsFromCollection, routeFromOfficial, layerIdentify
└── src/**/*.test.js
```

---

## 8. Copier / adapter / inventer

### On copie (presque mot pour mot)

| Source | Destination | Note |
|---|---|---|
| `hooks/useLegContext.js` + tests | `src/hooks/` | Zéro API |
| `utils/simulationRoute.js`, `geo.js`, `escales.js`, `customRouteBriefing.js`, `waypointsFromCollection.js` + tests | `src/utils/` | |
| `components/Sidebar.jsx` | idem | BerryCard + PolarChat + AgentPanel **inclus** |
| `components/ExportSidebar.jsx` | idem | polar + export GeoJSON/KML |
| `components/SimulationPanel.jsx`, `AgentPanel.jsx` | idem | URLs → même origine (`''` ou `VITE_API_URL`) |
| `i18n/fr.js`, `en.js`, `LangContext.jsx` | `src/i18n/` | **toutes** les clés |
| `constants/itineraryPoints.ts` + `assets/img/flags/*` | `src/constants/` + `public/flags/` | `.js` suffit |
| `polar_engine.py` | `server/polar_engine.py` | |
| `polar_api/main.py` (helpers + 4 routes) | `server/polar_api.py` monté sur `main.py` | `POLAR_DATA_DIR` local |
| `naviguide-api/main.py` : searoute → `/route`, proxies, wind/wave/current, `_sim_*` | `server/route_engine.py` + `main.py` | **pas** tout le fichier 1500 lignes d’un bloc : extraire |
| `naviguide-api/agents/*` | `server/agents/` | SSE |
| `frontend/.../map/constants.js` (styles) | `src/layers/styles.js` | + `TILE_URLS.light` pour le thème clair |
| `layerOrder.js`, `points.js` | `src/layers/` | + pane `boat` |
| `backend/data/route.geojson` | `public/route.geojson` | fallback |
| `Leopard46_Standard_Sails.csv` + logos | `public/` | |

`ITINERARY_POINTS` **est** la liste des stops Berry (contrairement à la 1.0
qui voulait uniquement le GeoJSON officiel). Les drapeaux font partie de
l’UX.

### On adapte (nouvelle colle Leaflet)

| Idée prise chez | Ce qu’on change |
|---|---|
| `App.jsx` (~1800 lignes) | Même **état** et mêmes handlers (draw, searoute, sim, briefing). Le JSX `<Map>` MapLibre devient `useSimulatorMap` + couches Leaflet |
| `CatamaranMarker.jsx` | Même rotation / flip ; `L.marker` + `L.divIcon` |
| `useMarkerOffsets` | Recalcul en pixels Leaflet (`latLngToLayerPoint`) |
| `MaritimeLayers.jsx` | Plus de `Source`/`Layer` MapLibre ; hooks `useXLayer` Leaflet |
| `LayerFichePopup` | `L.popup` |
| Clic route / ZEE | `map.eachLayer` / hit-test Leaflet (distance à la polyligne, `featureContains`) |
| Fetch polar / agents | `VITE_API_URL=''` + proxy Vite, plus `localhost:8004` |

### On n’invente pas

Pas de nouveau format de route. Pas de nouvelle API publique prod. Pas de
nouveau modèle Gold. Le stub `ici()` fixe la **forme** du JSON pour
l’étape 2.

---

## 9. Backend du simulateur

Fichier unique `server/main.py`, port **8010**.

### 9.1 `GET /route`

Contrat **identique** à `naviguide-api` :

```
GET /route?start_lat=&start_lon=&end_lat=&end_lon=&check_wind=false
→ Feature | FeatureCollection
```

Pipeline à copier dans `route_engine.py` (dans cet ordre, déjà éprouvé) :

1. `sr.searoute(start, end)`
2. Préfixer / suffixer l’origine et la destination exactes si > 1 km
3. `avoid_land` (masque `global_land_mask` + STRtree NE **si** `geo_data/`
   est présent)
4. `_densify_coords(max_km=75)`
5. `_sanitize_route_coords`
6. second `avoid_land`
7. cache bidirectionnel (`_route_cache_key`, `lru_set`)

`geo_data/ne_10m_*.shp` **n’est pas dans le dépôt** aujourd’hui. Le code
prod tolère l’absence (`_NE_TREE is None`). On documente : masquer haute
résolution = option ; sans shapefiles, `global_land_mask` suffit pour
l’étape 1.

**Interdit :** charger `eez_world_map.geojson` (18 Mo) « pour aider
searoute ».

### 9.2 Polar — voir §10

Monté sous `/api/v1/polar/*`.

### 9.3 Proxies et Copernicus

Copies de `naviguide-api/main.py` :

- `/proxy/zee/wms` — tuiles VLIZ `eez_boundaries`
- `/proxy/zee` — WFS bbox (clic ZEE)
- `/proxy/ports` — WPI
- `/proxy/seamark/{z}/{x}/{y}.png` — repli ; le front essaie d’abord
  `tiles.openseamap.org`
- `POST /wind|/wave|/current` — Copernicus si `COPERNICUS_USERNAME` /
  `COPERNICUS_PASSWORD`, sinon `_sim_*`

### 9.4 Agents

Copies de `naviguide-api/agents/` + les 4 routes SSE. Sans clé LLM :
texte structuré (déjà le cas en prod). **Pas** un Search Tavily à chaque
message.

---

## 10. Polar engine complet

### 10.1 Bibliothèque (`server/polar_engine.py`)

Comportement à préserver (déjà testé en prod) :

- `PolarData.speed(twa, tws)` — bilinéaire + fade TWA→0 + plateau TWS
- `optimal_upwind` / `optimal_downwind` / `optimal_gybe_angle`
- `summary()` pour TWS 8, 10, 12, 16, 20, 25
- `generate_full_grid()` → 181×61
- `parse_polar_csv` / `parse_polar_excel` / `parse_polar_pdf` /
  `parse_polar_text`

Dépendances : `numpy`, `pandas`, `openpyxl`, `pdfplumber` (PDF texte) ;
`pytesseract` + `pdf2image` **optionnels** (PDF scannés). Sans Tesseract,
un PDF image → 422 honnête (« PDF image : installez tesseract »).

### 10.2 API (`server/polar_api.py`)

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/api/v1/polar/upload` | multipart `file` + `expedition_id` + `boat_name` |
| GET | `/api/v1/polar/{id}` | grille complète (le front **ne la télécharge pas** pour le chat) |
| GET | `/api/v1/polar/{id}/summary` | VMG seul |
| POST | `/api/v1/polar/chat` | historique court + `vmg_summary` dans le prompt |

`expedition_id` par défaut : `berry-mappemonde-2026` (constante
`ExportSidebar`).

Stockage : `server/polar_data/polar_{id}.json` (gitignore).

### 10.3 UI (panneau droit + chat gauche)

Comportement **pixel-contrat** avec NAVIGUIDE :

1. Au montage, fetch `/Leopard46_Standard_Sails.csv` → upload automatique
   « Leopard 46 ».
2. Drop zone PDF / CSV / XLSX, badge Analysing / Chargé / Échec.
3. Tableau VMG (près | portant) pour les 6 TWS.
4. Chat gauche désactivé tant que `polarData` est null ; ensuite
   `POST /api/v1/polar/chat`.

### 10.4 Tests moteur (sans UI)

`server/tests/test_polar_engine.py` :

- CSV Leopard 46 se parse ;
- `speed(90, 12)` > 0 ;
- `summary()[12]` a `upwind` et `downwind` ;
- `generate_full_grid().shape == (181, 61)` ;
- TWA 0 → vitesse 0.

---

## 11. UI / UX complète de NAVIGUIDE

C’est **le** critère de l’étape 1 côté skipper. On porte l’écran, on change
le projecteur.

### 11.1 Colonne gauche — `Sidebar.jsx` (320 px, `slate-900`)

De haut en bas, **dans cet ordre** (déjà le fichier vivant) :

1. Logo NAVIGUIDE.
2. **BerryCard** — états `berry-active` / `import-mode` / `file-active` /
   `berry-active-file-loaded` : import GeoJSON, import KML, Dessiner,
   Terminer, Continuer, Supprimer, bascule Berry ↔ perso.
3. Pastilles de couches.
4. Bouton simulation (Play / quitter).
5. Si simulation ON : `SimulationPanel` (from→to, nm, ETA, cap, Précédent /
   Suivant) puis `AgentPanel` (4 onglets SSE).
6. Encadré « Pour commencer » s’il n’y a pas encore de plan.
7. **Polar Chat**.
8. **Briefing** (texte orchestrateur, ou `buildLocalCustomBriefing` sur une
   route perso, ou hint pendant le tracé).

Toggle flottant `left-4` / `left-[322px]`.

### 11.2 Colonne droite — `ExportSidebar.jsx` (320 px, liseré ciel)

1. FR / EN.
2. Sombre / Clair (bascule le fond Esri : `TILE_URLS.dark` / `.light`).
3. Stats de route (nm, segments, points).
4. Drop polaire + tableau VMG.
5. Export GeoJSON / KML (`buildGeoJSON` / `buildKML` déjà dans le fichier).

Toggle flottant `right-4` / `right-[322px]`.

### 11.3 Chrome carte (hors couches)

Portés depuis `App.jsx` :

- overlay « Calcul des routes… » puis pastille `routesProgress` ;
- bandeau de tracé (vert, undo / redo, spinner searoute) ;
- drapeaux d’escales + hover ;
- popup satellite (onglets Vent / Vague / Courant + `WindDirectionArrow`) ;
- popup fiche couche (`LayerFichePopup`) ;
- édition nom / drapeaux d’un waypoint tracé ;
- toast presse-papiers s’il existe déjà.

### 11.4 Briefing

Même contrat que NAVIGUIDE :

- Berry : `POST …/expedition/plan/berry-mappemonde` **si**
  `VITE_ORCHESTRATOR_URL` est défini **et** que le service répond ;
  sinon cache `localStorage` 24 h, sinon pas de briefing IA (l’encadré
  « Pour commencer » suffit).
- Perso : `POST …/expedition/plan` 8 s max, sinon
  `buildLocalCustomBriefing`.

On **ne copie pas** `naviguide_orchestrator/`. Le simulateur est un
**client**. Sans orchestrateur, l’UX reste complète (texte local).

### 11.5 Ce qui n’est **pas** de l’UX NAVIGUIDE (on n’ajoute pas)

- Onglets Console / Review / Swarm.
- Grille de dons HelloAsso.
- Mode « un layer = un mode opérateur ».

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
pipeline. Si fallback GeoJSON : deux `LineString` Wallis→Nouméa, **ne pas**
les fusionner. `flyTo` : `[lat, lon]` (Leaflet), longitude dans ]−180, 180].

CSS : `leaflet/dist/leaflet.css`. Pas d’icône par défaut Leaflet (divIcon /
circleMarker uniquement) — évite le piège Vite `marker-icon.png`.

---

## 13. Film Berry : searoute, bateau, fallback

### 13.1 Construction des jambes

Copier le `useEffect` « Fetch des segments » de `App.jsx` (L.523–676) dans
un module `src/utils/berryLegs.js` (testable) :

- `nonMaritimeNames` : Saint-Maur|La Rochelle et retour ;
- `skipFromNames` : Marigot, Cayenne, Halifax, Saint-Pierre ;
- inserts : Marigot→Cayenne, Halifax→SPM, SPM→Halifax, Cayenne→Papeete ;
- `SEGMENT_BATCH_SIZE = 4` ;
- `orientCoords` ;
- `check_wind: false` sur le fetch initial (le vent = clic, pas 40× Copernicus).

### 13.2 Fallback `routeFromOfficial.js`

Si `GET /route` échoue pour **toutes** les jambes du premier lot : charger
`/route.geojson`, convertir :

```
LineString + from/to/type  → segments (nonMaritime ⇔ type === "overland")
Point + point_type         → stops (flag ⇔ escale)
```

Afficher un bandeau discret : « Route officielle (searoute indisponible) ».

### 13.3 Simulation

Chaîne déjà éprouvée :

```
segments + stops
  → buildSimTargets()
  → simulationStartPos()
  → useLegContext(lat, lon, segments, stops, speedKnots, simulationStep)
```

Contrôles : `handleSimNext` / `Prev`, snap, `map.flyTo([lat, lon], { duration: 0.8 })`,
drag → re-snap. Changement de route (`customRoute`) → bateau au départ.

`speedKnots` : 7, ou polar×vent si les deux sont là (§6.4).

### 13.4 Marqueur bateau

Port de `CatamaranMarker.jsx` : image, transparence canvas, rotation
est/ouest + hémisphère sud, pane `boat`. Sans image : triangle CSS cyan.

---

## 14. Draw your own route

**Pas** des segments droits. Contrat = `App.jsx` L.287–445 + bandeau L.913+.

| Action | Comportement |
|---|---|
| Dessiner | `drawingMode=true`, cache Berry, curseur croix, simulation OFF |
| Clic 1 | pose le point, pas de fetch |
| Clic 2+ | `GET /route?start_lat…` entre le précédent et le nouveau ; polyligne **verte** |
| Undo | retire point + segment, invalide le fetch en vol (`fetchIdRef`) |
| Redo | restaure point + segment |
| Terminer | `drawnSegments` + `drawnPoints` → FeatureCollection → `customRoute` ; trait **bleu** |
| Continuer | reprend les points déjà là |
| Supprimer | retour Berry, `applyBerryBriefing` |
| Import `.geojson` / `.kml` | `parseGeoJSON` / `parseKML` (déjà dans `Sidebar.jsx`) → même pipeline |
| Revenir à Berry | `customRoute = null`, les segments searoute Berry (ou le fallback) réapparaissent |

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

Règles inchangées vs 1.0 : fetch au premier ON ; AMP bbox debounce 420 ms ;
marinas / projets en **canvas** ; ZEE = WMS limites, pas le GeoJSON 18 Mo ;
climatologie = pastille + bandeau (« régime de vent : étape 6 »).

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
    "/agents":    { target: "http://localhost:8010", changeOrigin: true },
    "/api/v1":    { target: "http://localhost:8010", changeOrigin: true },
    "/bi": {
      target: "http://localhost:8001",
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/bi/, "/api"),
    },
  },
}
```

On ne crée **aucune** route dans `backend/` ni `naviguide/`. On ne déploie
rien sur le VPS.

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
- `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` — optionnel (sinon `_sim_*`)
- clés LLM — optionnelles (chat polar / agents : fallback structuré)

Aucune clé Tavily. **Ne jamais** lancer `infra/vps/sync-from-atlas.sh`.
Le simulateur ne parle pas à Mongo.

---

## 18. Ordre de chantier (1.0 → 1.10)

Ne pas commencer le polar (1.5) si searoute (1.2) n’avance pas : sans trait,
pas de film. Ne pas commencer les couches (1.7) si l’UX (1.4) n’est pas
posée : les pastilles n’ont nulle part où vivre.

### 1.0 — Squelette Vite + FastAPI

- `package.json` : react, react-dom, leaflet, lucide-react, tailwind 4,
  `@tailwindcss/vite`, `@vitejs/plugin-react`. **Pas** de `maplibre-gl`
  ni `react-map-gl` ni `searoute-js`.
- Scripts : `dev`, `build`, `preview`, `test`, `server`.
- `server/requirements.txt` : fastapi, uvicorn, searoute, geographiclib,
  shapely, global-land-mask, numpy, pandas, openpyxl, pdfplumber,
  python-multipart, httpx, python-dotenv (+ optionnels pytesseract,
  copernicusmarine, anthropic).
- `README.md` : deux commandes, ports 5174 / 8010, « prod intouchée »,
  lien vers ce plan.
- Recette : page « NAVIGUIDE simulator » + `GET http://localhost:8010/`
  → `{ "service": "naviguide-simulator" }`.

### 1.1 — Carte + fond + panes

- `useSimulatorMap` : `L.map`, tuile dark, `invalidateSize`, thème clair.
- `createPanes` + test d’ordre.
- CSS Leaflet.

### 1.2 — searoute + route Berry

- Extraire `route_engine.py` + `GET /route`.
- Test Python : une jambe courte mer (ex. La Rochelle → un point à 20 nm
  au large) renvoie une `LineString` ≥ 2 points.
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

### 1.4 — UI / UX complète (chrome)

- Copier `Sidebar` (BerryCard **entière**), `ExportSidebar` (sans polar
  encore branché si 1.5 n’est pas prêt : drop zone visible, erreur
  « polar API »), i18n complet, FR/EN, sombre/clair.
- Briefing local + hint de tracé.
- Recette : on reconnaît NAVIGUIDE les yeux fermés, sans MapLibre.

### 1.5 — Polar engine complet

- Copier `polar_engine.py` + routes + CSV défaut.
- Tests §10.4.
- Brancher drop / VMG / chat / auto-Leopard 46.
- (Plus tard dans 1.5) `speedKnots` depuis polar×vent.

### 1.6 — Draw your own route

- Handlers `App.jsx` + bandeau undo/redo + Terminer / Continuer / Supprimer.
- Recette : 3 clics Atlantique, trait **qui évite les terres**, simulation
  sur **cette** ligne, retour Berry.

### 1.7 — Pastilles + dessin des couches

Ordre : Balisage → ZEE WMS → WPI → PoE → AMP → Science → Projets →
Capitaineries → Marinas (OFF, canvas) → Climatologie stub.

### 1.8 — Import / export

- Import GeoJSON / KML (déjà dans BerryCard).
- Export depuis `ExportSidebar` (déjà écrit) : vérifier que les segments
  Leaflet (pas MapLibre) alimentent `buildGeoJSON`.
- Recette : exporter Berry, réimporter, le trait revient.

### 1.9 — Clic route + AgentPanel

- `POST /wind|/wave|/current` + popup 3 onglets.
- Copier agents SSE. Recette : onglet Ports sur une jambe → texte (LLM ou
  fallback), pas de crash.

### 1.10 — Stub `ici()` + polish

- `ici.js` + test des clés.
- Disclaimer *Ne convient pas à la navigation*.
- README final : tableau « ça marche / ça n’existe pas encore ».
- Une ligne dans le `README.md` **racine** seulement quand 1.0 existe.

**Critère « étape 1 terminée » :** un skipper débutant lance les deux
commandes, reconnaît NAVIGUIDE, avance le bateau sur Berry, charge / voit
les polaires Leopard 46, trace 3 points **searoute**, allume AMP (si BI
local) ou voit une erreur claire, et comprend que le récit d’événement
(`ici()` plein) n’est pas là. Sans ça, on ne passe pas à l’étape 2.

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
  `naviguide/polar_agent/**` (on **lit** pour copier, on **n’édite pas**)
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
| A2 | Polaires | Tableau VMG Leopard 46 (ou erreur claire si parse KO) |
| A3 | Simulation → Suivant × 3 | Bateau avance, from/to, nm, cap |
| A4 | Précédent | Retour d’un cran, pas de saut Cap-Vert |
| A5 | Dessiner 3 clics mer | Trait **vert** qui contourne la terre, undo marche |
| A6 | Terminer | Trait bleu, briefing local, simulation sur **cette** route |
| A7 | « Berry-Mappemonde » | Retour à l’officielle searoute |
| A8 | Export GeoJSON | Fichier téléchargé, réimportable |
| A9 | Chat polar « VMG à 12 kt » | Chiffres du tableau, pas une grille |
| A10 | Clic sur le trait | Popup vent / vague / courant (réel ou simulé) |
| A11 | `<details>` dossier | `zee: null`, `polar.boat` si chargé |
| A12 | Clair / FR | Fond Esri light, libellés anglais→français |

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

---

## 21. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Recopier `useAmpLayer` avec `mode === "amp"` | Haute | Nouveaux hooks toggle |
| Recoller le simulateur à `naviguide-api:8000` | Haute | Backend **8010** dans le dossier |
| Utiliser `searoute-js` « pour aller plus vite » | Haute | Inutilisé en prod ; Python uniquement |
| Allumer Marinas par défaut | Moyenne | OFF + canvas |
| Charger `eez_world_map.geojson` | Haute | WMS limites |
| `flyTo([lon, lat])` (ordre MapLibre) | Haute | Leaflet = `[lat, lon]` ; tester Corse |
| Antiméridien Wallis–Nouméa | Moyenne | 2 LineString / normalisation searoute |
| Import runtime depuis `frontend/` ou `naviguide/` | Haute | copies |
| Toucher nginx / VPS « pour tester » | Bloquante | localhost seulement |
| Avaler la grille 181×61 dans le chat / `ici()` | Produit | `vmg_summary` seulement |
| PDF scanné sans Tesseract | Basse | 422 + message |
| Croire l’étape 1 « prête pour Nemotron » | Produit | sac vide = honnête ; étape 2 ensuite |
| Copier `polar_agent.py` Deploy AI | Moyenne | `polar_api` + cascade / fallback |

---

## 22. Passage à l’étape 2

L’étape 2 peut commencer **uniquement** si A1–A7 et A11 passent.

Alors on remplit le sac, **sans** Tavily :

1. Quelle ZEE contient le point (`zee_crossings` / shapely) — **1**
   polygone, nom, mrgid, Gold oui/non.
2. PoE de **cette** ZEE + URL.
3. AMP / projets / 3–5 marinas-capit-WPI dans 20–30 nm.
4. Événement « on entre dans cette ZEE ».
5. `polar` : déjà amorcé (bateau + VMG) ; y ajouter vitesse / ETA **de
   cette** jambe.

Nano / Tavily / Ultra restent aux étapes 5–6. Stretch AMP « parc, saison,
mouillage » et overlay climatologie = après le sac.

Rappel du contrat global :

> Les boutons allument toute la couche. Le LLM n’en voit qu’une poignée.
> Un pas = `ici()` gratuit. Tavily = entrée de ZEE, clic skipper, ou alerte.
> Polar et searoute parlent au **point** et à **cette** jambe, pas au globe.

---

## 23. Documents dont ce plan hérite

- Discussion produit « simulation = film, `ici()` = moteur, boutons = carte »
  (septembre 2026) **et** arbitrage skipper du 13 septembre : polar
  complet + UX NAVIGUIDE complète + searoute + draw your own route.
- `docs/hackathon-nebius-nvidia.md` — un seul produit, dossier autonome
  extractible.
- `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` — pas une couche monde à
  l’étape 1.
- `docs/ARCHITECTURE.md` — `MapView.js` + un hook par couche.
- Code vivant :
  - film : `naviguide/naviguide-app/src/App.jsx` (searoute L.523–676,
    draw L.287–445, chrome L.824+), `Sidebar.jsx`, `ExportSidebar.jsx`,
    `useLegContext.js`, `MaritimeLayers.jsx` ;
  - polar : `naviguide/polar_agent/polar_engine.py`,
    `naviguide/naviguide_workspace/polar_api/main.py` ;
  - searoute : `naviguide/naviguide-api/main.py`
    (`searoute_with_exact_end`, `avoid_land`, `GET /route`) ;
  - projecteur : `frontend/src/components/MapView.js`,
    `frontend/src/components/map/*` ;
  - fallback : `backend/data/route.geojson` ;
  - exports : `GET /api/export/*`, `GET /api/amp?bbox=`.

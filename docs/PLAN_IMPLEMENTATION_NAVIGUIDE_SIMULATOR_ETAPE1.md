# Plan d’implémentation — `naviguide-simulator/` étape 1

Document de chantier. Il fige **comment poser le dossier** dans ce dépôt, et
**quoi coder en premier** : la carte Leaflet, les boutons de couches, la route
Berry-Mappemonde, le bateau qui avance.

Écrit en langage simple : c’est le contrat de l’étape 1. Les étapes 2 à 6
(moteur `ici()`, événements, Gold, Tavily, Nemotron) sont rappelées pour
ne pas les commencer trop tôt — **elles ne sont pas livrées ici**.

Version **1.0** — 13 septembre 2026.

**Sommaire**

1. En une phrase
2. Pourquoi cette étape existe
3. Ce que l’on livre
4. Ce que l’on ne livre pas
5. Vocabulaire
6. Décisions d’architecture (verrouillées)
7. Arborescence cible
8. Copier / adapter / inventer
9. Carte Leaflet et panes
10. Boutons de couches (légende du cockpit)
11. Film : route officielle + bateau
12. Tracer / importer une route
13. Sidebar (film, pas la Console)
14. Stub `ici()` — le sac vide
15. Données et proxies (prod intouchée)
16. Ordre de chantier (1.0 → 1.8)
17. Fichiers touchés / interdits
18. Recette
19. Risques
20. Passage à l’étape 2
21. Documents dont ce plan hérite

---

## 1. En une phrase

Créer `naviguide-simulator/` dans **ce** dépôt : une petite app Vite qui
**rejoue** Berry-Mappemonde sur une carte **Leaflet**, avec les **boutons de
couches** du cockpit, **sans** toucher `naviguide.fr` ni `blueintelligence.online`.

---

## 2. Pourquoi cette étape existe

Le produit hackathon, ce n’est pas un deuxième Blue Intelligence. C’est le
**film** : le bateau avance, on voit la carte du cockpit, et plus tard un
petit dossier « vu d’ici » nourrit un récit.

Sans l’étape 1, il n’y a ni cockpit, ni position, ni boutons. Le moteur
`ici()` (étape 2) n’aurait rien autour de quoi travailler.

L’étape 1 **n’appelle pas** de LLM. Elle prépare le projecteur (Leaflet) et
le film (route + bateau + légende).

---

## 3. Ce que l’on livre

À la fin de l’étape 1, en local (`npm run dev` dans le dossier) :

1. Une carte Leaflet (fond sombre Esri, comme Blue Intelligence).
2. La **route officielle** Berry-Mappemonde dessinée (double trait + escales).
3. Un **mode simulation** : Précédent / Suivant, le bateau avance et reste
   collé à la route (`useLegContext`).
4. Une **sidebar** type NAVIGUIDE : logo, pastilles de couches, bouton
   simulation, métriques (nm, ETA, cap), un encart Briefing **vide / texte
   local**.
5. **Dix boutons** de couches, mêmes pastilles qu’aujourd’hui dans NAVIGUIDE,
   plus Science et Climatologie.
6. Les couches **s’allument vraiment** (fetch au premier ON, dessin Leaflet).
   Climatologie = pastille / bandeau stub, pas un globe.
7. **Importer** un GeoJSON ou **tracer** une route perso (segments droits).
8. Un fichier `ici()` qui renvoie un JSON vide mais **typé** (sac à dos).
9. Un `README.md` dans le dossier : comment lancer, ce qui est hors périmètre.

La prod ne change pas. Aucun merge n’est requis vers `main` pour que
blueintelligence.online ou naviguide.fr restent tels quels.

---

## 4. Ce que l’on ne livre pas

| Interdit en étape 1 | Pourquoi |
|---|---|
| Console, Review, Swarm, 6 modes opérateur | UX Blue Intelligence, pas le cockpit |
| Carte MapLibre / fond « carte marine » | On change de projecteur ; Seamap = plus tard, optionnel |
| Les 4 chats Ports / Sécurité / Météo / Cruisers | Un seul panneau Briefing, plus tard |
| Polar engine, upload CSV, VMG réelle | Hors film ; ETA = 7 nœuds constants |
| Orchestrateur LangGraph, briefing IA | Texte local ou placeholder |
| Tavily, Nemotron, Token Factory | Étapes 5–6 |
| Requêtes spatiales « dans cette ZEE / 30 nm » | C’est `ici()` réel = étape 2 |
| Imports / exports opérateur BI | On **lit** les mêmes URLs, on n’écrit rien |
| Modifier `frontend/`, `backend/`, `naviguide/` | La prod ne bouge pas |
| `react-leaflet` | Les hooks BI parlent à un `L.Map` nu |
| Coller 4 500 projets dans un prompt | Le LLM n’existe pas encore ici |

---

## 5. Vocabulaire

| Mot | Sens ici |
|---|---|
| **Film** | Ce que le skipper voit : sidebar, route, bateau, boutons |
| **Projecteur** | La carte : Leaflet, plus MapLibre |
| **Légende** | Les pastilles ON/OFF (ZEE, WPI, Balisage, …) |
| **Sac à dos / `ici()`** | Petit JSON autour du bateau. Étape 1 = sac **vide** |
| **Route officielle** | `backend/data/route.geojson`, déjà servi par `GET /api/route` |
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
Donc **aucune** import runtime du style `../../frontend/src/...` : on **copie**
les petits modules (géométrie, styles), on n’attache pas les deux apps.

### 6.2 Pile technique

| Choix | Comme… | Pas comme… |
|---|---|---|
| Vite 7 + React 19 + Tailwind 4 | `naviguide/naviguide-app` | CRA de `frontend/` |
| Leaflet 1.9 **nu** (`L.map`) | `frontend/src/components/MapView.js` | MapLibre de NAVIGUIDE |
| Port dev **5174** | — | 5173 (NAVIGUIDE) et 3000 (CRA) |
| FR d’abord, EN ensuite | i18n NAVIGUIDE | — |

Leaflet **sans** `react-leaflet` : Blue Intelligence crée déjà la carte à la
main et lui accroche des panes / canvas. Recoller ça dans `react-leaflet`
ferait tout réécrire.

### 6.3 Route : le GeoJSON officiel, pas searoute

NAVIGUIDE aujourd’hui appelle `naviguide-api GET /route?start_lat=…` (searoute,
évitement des terres) **jambe par jambe**. Ça tire tout le moteur routing /
polaire.

L’étape 1 charge **une fois** la route officielle :

- d’abord `public/route.geojson` (copie de `backend/data/route.geojson`, ~56 Ko) ;
- si le backend BI tourne, on peut rafraîchir via `/bi/route` (même fichier).

Les `LineString` deviennent les `routeSegments` de `useLegContext`.
`type: "overland"` → `nonMaritime: true` (Berry → La Rochelle).
Les `Point` (`escale` / `intermediate`) deviennent les stops.

**Conséquence :** le film marche **sans** `naviguide-api` et **sans**
orchestrateur. Seules les couches ZEE WMS / WPI ont besoin du proxy NAVIGUIDE
— et si le proxy est down, le bouton affiche l’erreur, la route continue.

### 6.4 Couches : mêmes URLs, nouveau dessin, pas les hooks « un mode »

Blue Intelligence n’affiche **qu’un** mode à la fois (`mode === "amp"`, etc.).
Les hooks (`useAmpLayer`, `useFormalitiesLayers`, …) **refusent** de peindre
si le mode n’est pas le bon. Les recopier tels quels dans le simulateur
reproduirait « un mode à la fois ».

**On ne les importe pas.** On **vole** :

- couleurs / `ampStyle` / `zoneStyle` / traits de route (`constants.js`) ;
- panes (`layerOrder.js`) ;
- popups (`useAmpLayer.popupHtml`, science, zone) ;
- canvas `makePointGroup` / `penRadius` (`points.js`).

On **réécrit** la colle : « bouton ON → fetch (une fois) → `map.addLayer` ;
bouton OFF → `map.removeLayer` ». Plusieurs couches peuvent être allumées
ensemble. C’est la légende du cockpit.

Les 4 500 projets et les marinas OSM restent sur la **carte** si on allume
le bouton. Le LLM (plus tard) n’en verra qu’une poignée via `ici()`.

### 6.5 Simulation allumée par défaut

Ici, la simulation **est** le produit. Au chargement : mode simulation ON,
bateau au départ de la route affichée (Saint-Maur).

### 6.6 Un Briefing, zéro chat d’agents

Pas de `AgentPanel`. Pas de Polar Chat. Un encart « Briefing » avec un texte
fixe du type : *« Le récit du voyage arrive quand le sac à dos (`ici()`) sera
plein. Pour l’instant : vous êtes sur la route officielle. »* plus les
chiffres déjà calculés par `useLegContext`.

---

## 7. Arborescence cible

```
naviguide-simulator/
├── README.md
├── package.json                 # name: naviguide-simulator
├── vite.config.js               # port 5174, proxy /bi et /proxy
├── index.html
├── public/
│   ├── route.geojson            # copie de backend/data/route.geojson
│   └── logo-*.png               # logos NAVIGUIDE / Berry (copie)
├── src/
│   ├── main.jsx
│   ├── App.jsx                  # état : couches, sim, route berry|custom
│   ├── index.css                # Tailwind 4 + overrides popups Leaflet
│   ├── constants/
│   │   └── layers.js            # LAYER_CONFIG (10 pastilles + couleurs)
│   ├── engine/
│   │   └── ici.js               # stub — voir §14
│   ├── hooks/
│   │   ├── useLegContext.js     # copie naviguide-app
│   │   └── useSimulatorMap.js   # crée L.map, panes, fond Esri
│   ├── i18n/
│   │   ├── fr.js
│   │   ├── en.js
│   │   └── LangContext.jsx      # copie allégée
│   ├── layers/
│   │   ├── styles.js            # copie utile de frontend/.../constants.js
│   │   ├── panes.js             # copie de layerOrder.js + pane bateau
│   │   ├── points.js            # copie de makePointGroup / penRadius
│   │   ├── useRouteLayer.js     # dessine public/route.geojson
│   │   ├── useZeeWmsLayer.js
│   │   ├── useWpiLayer.js
│   │   ├── useBalisageLayer.js  # tuiles OpenSeaMap
│   │   ├── useProjectsLayer.js
│   │   ├── useMarinasLayer.js
│   │   ├── useCapitaineriesLayer.js
│   │   ├── usePoeLayer.js
│   │   ├── useAmpLayer.js       # polygones + bbox
│   │   ├── useScienceLayer.js
│   │   └── useClimatologyLayer.js  # stub visuel
│   ├── components/
│   │   ├── Sidebar.jsx          # film, sans AgentPanel ni Polar Chat
│   │   ├── LayerPills.jsx       # pastilles (capture NAVIGUIDE)
│   │   ├── SimulationPanel.jsx  # copie
│   │   ├── BriefingPanel.jsx    # placeholder
│   │   └── CatamaranMarker.js   # L.marker + DivIcon, pas MapLibre
│   └── utils/
│       ├── geo.js
│       ├── escales.js
│       ├── simulationRoute.js
│       └── routeFromOfficial.js # GeoJSON officiel → segments + stops
└── src/**/*.test.js             # node:test, comme naviguide-app
```

Pas de backend dans ce dossier à l’étape 1.

---

## 8. Copier / adapter / inventer

### On copie (presque mot pour mot)

| Source | Destination | Note |
|---|---|---|
| `naviguide/.../hooks/useLegContext.js` | `src/hooks/useLegContext.js` | Zéro API, déjà autonome |
| `naviguide/.../utils/simulationRoute.js` | `src/utils/simulationRoute.js` | + ses tests |
| `naviguide/.../utils/geo.js` | `src/utils/geo.js` | haversine, `featuresToSegments` |
| `naviguide/.../utils/escales.js` | `src/utils/escales.js` | prochaine escale |
| `naviguide/.../components/SimulationPanel.jsx` | idem | Précédent / Suivant |
| `naviguide/.../i18n/LangContext.jsx` + clés utiles de `fr.js` / `en.js` | `src/i18n/` | sans clés polar / agents |
| `frontend/.../map/constants.js` (styles) | `src/layers/styles.js` | `ampStyle`, `zoneStyle`, couleurs route, `TILE_URLS` |
| `frontend/.../map/layerOrder.js` | `src/layers/panes.js` | + pane `boat` (z-index ~620, au-dessus des markers) |
| `frontend/.../map/points.js` | `src/layers/points.js` | canvas, pas de cluster |
| `backend/data/route.geojson` | `public/route.geojson` | source de vérité du film |
| Logos + `catamaran.jpg` | `public/` / `src/assets/` | droits déjà dans le dépôt |

`ITINERARY_POINTS` (drapeaux PNG) : **on ne le recopie pas** comme liste
parallèle. Les stops viennent du GeoJSON officiel (`point_type`). Les drapeaux
sont un plus visuel (étape 1b) : pastille d’escale suffit pour le film.

### On adapte (nouvelle colle Leaflet)

| Idée prise chez | Ce qu’on change |
|---|---|
| `MapView.js` | Une carte unique, **toutes** les couches toggleables, pas de `mode` |
| `MaritimeLayers.jsx` `ALL_LAYER_CONFIG` | + Science (`#a78bfa`) + Climatologie (`#38bdf8`) |
| `Sidebar.jsx` pastilles L.504–531 | Extraire dans `LayerPills.jsx` |
| `CatamaranMarker.jsx` | Même rotation / flip ; `L.marker` + `L.divIcon` au lieu de `Marker` MapLibre |
| `useRouteLayer.js` BI | Lit `public/route.geojson` (ou `/bi/route`), pas `api.get("/route")` via axios CRA |
| Fetch BI de `useBiLayer` | `VITE_BI_BASE` = `/bi` (rewrite → `/api`) |
| AMP bbox + debounce 420 ms | Comme `MaritimeLayers.useAmpPolygons` et `useAmpLayer` BI |
| Draw route de `App.jsx` | Segments **droits** entre clics — **pas** `GET /route?start_lat` |

### On n’invente pas

Pas de nouveau format de route. Pas de nouvelle API. Pas de nouveau modèle
de données Gold. Le stub `ici()` fixe juste la **forme** du JSON pour l’étape 2.

---

## 9. Carte Leaflet et panes

Création (une fois, dans `useSimulatorMap`) :

```js
L.map(el, {
  center: [22, 5],
  zoom: 3,
  zoomSnap: 0.25,
  minZoom: 2,
  maxZoom: 18,
  worldCopyJump: true,   // circumnavigation
  // maxBounds monde comme BI si besoin d’éviter le vide infini
});
```

Fond : `TILE_URLS.dark` (Esri World Dark Gray). **Pas** de MapLibre, **pas**
de PMTiles Seamap.

Panes (ordre verrouillé, test Jest/node comme BI) :

| Pane | z-index | Contenu |
|---|---|---|
| `tilePane` (builtin) | 200 | Fond Esri |
| `zee-wms` | 250 | Tuiles ZEE |
| `balisage` | 260 | OpenSeaMap |
| `route` | 380 | Polyligne officielle / perso |
| `amp` | 420 | Polygones AMP |
| `overlayPane` | 400 | (Leaflet) |
| points canvas | via renderer | projets, marinas, … |
| `markerPane` | 600 | — |
| `boat` | 620 | catamaran |
| `popupPane` | 700 | popups |

Un test `panes.test.js` fige la liste (même discipline que
`frontend/src/components/map/__tests__/layerOrder.test.js`).

**Antiméridien :** la route officielle est déjà coupée en deux `LineString`
(`antimeridian_part` 1 et 2, Wallis → Nouméa). Les dessiner telles quelles,
comme BI. `flyTo` du bateau : longitude dans ]−180, 180]. Ne pas fusionner
les deux morceaux en une seule ligne qui traverse la carte.

---

## 10. Boutons de couches (légende du cockpit)

Même UI que la capture / `Sidebar.jsx` : pastilles `rounded-full`, point
coloré, spinner au chargement, bordure rouge si erreur.

| Clé | Libellé | Couleur | Source | Défaut |
|---|---|---|---|---|
| `zee` | ZEE | `#0e7490` | WMS VLIZ via `/proxy/zee/wms` (même URL que NAVIGUIDE) | ON (tuiles = pas de gros JSON) |
| `wpi` | Ports WPI | `#f59e0b` | `/proxy/ports` | OFF |
| `balisage` | Balisage | `#10b981` | tuiles OpenSeaMap (direct, ou `/proxy/seamark` si dispo) | OFF |
| `projects` | Projets | `#06b6d4` | `/bi/export/geojson` | OFF |
| `marinas` | Marinas | `#ef4444` | `/bi/export/marinas.geojson` | OFF |
| `capitaineries` | Capit. | `#7dd3fc` | `/bi/export/capitaineries.geojson` | OFF |
| `poe` | PoE | `#d97706` | `/bi/export/poe.geojson` | OFF |
| `amp` | AMP | `#22c55e` | `/bi/amp?bbox=` (polygones, pas les centroïdes) | OFF |
| `science` | Science | `#a78bfa` | `/bi/export/science.geojson` | OFF |
| `climatology` | Climat | `#38bdf8` | **aucun fetch** — bandeau « régime de vent : étape 6 » | OFF |

Règles :

- Fetch **au premier ON** seulement (sauf AMP : refetch bbox au `moveend`,
  debounce 420 ms).
- Marinas / projets : renderer **canvas** (`makePointGroup`). Jamais de
  cluster MarkerCluster (BI l’a abandonné).
- ZEE = **limites WMS** (`eez_boundaries`), pas le fichier 18 Mo
  `eez_world_map.geojson`.
- Balisage : URL publique `https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png`
  en premier (aucun backend). Le proxy NAVIGUIDE est un repli.
- Climatologie : si ON, un petit bandeau sous les pastilles
  (« Climatologie : overlay mensuel prévu à l’étape 6. Copernicus = chiffres
  au point, plus tard. »). Pas de grille, pas d’appel `climatology.py`.
- Popups : HTML copié de BI (AMP : `manager_url` + `visit_url` séparés ;
  Science : portail + DOI). Pas besoin d’être pixel-perfect.

État d’une couche : `{ show, loading, error, data }`. Le bouton lit ça.
Aucune couche n’est « le mode actif ».

---

## 11. Film : route officielle + bateau

### 11.1 Conversion officielle → simulation

Nouveau module `routeFromOfficial.js` :

```
FeatureCollection
  LineString + properties.from/to/type
  Point + point_type escale|intermediate
        ↓
{
  segments: [{ coords: [[lon,lat],...], from, to, nonMaritime }],
  stops:    [{ name, lat, lon, flag: boolean }]
}
```

- `nonMaritime` ⇔ `properties.type === "overland"`.
- `flag` ⇔ `point_type === "escale"` (pour `nextEscaleStop`).
- Ordre des LineString = ordre du fichier (déjà chronologique).
- Deux LineString Wallis→Nouméa : **deux** segments, bateau qui « saute »
  l’antiméridien au step suivant — acceptable en étape 1.

Puis la chaîne déjà éprouvée :

```
segments + stops
  → buildSimTargets()     // [départ, mid0, end0, mid1, end1, …]
  → simulationStartPos()
  → useLegContext(lat, lon, segments, stops, 7, simulationStep)
```

On **ne** recrée **pas** la logique spéciale de `App.jsx` (skip Marigot,
Halifax aérien, etc.) : le GeoJSON officiel l’a déjà tranchée.

### 11.2 Contrôles

Comme aujourd’hui :

- `handleSimNext` / `handleSimPrev` avancent dans `simTargets` ;
- après snap, `map.flyTo([lat, lon], zoom, { duration: 0.8 })` sur
  `legContext.snappedPosition` (Leaflet : `[lat, lon]`, pas `[lon, lat]`) ;
- drag du bateau : `L.Marker` `draggable: true` → on met à jour la position
  brute → `useLegContext` recolle → on replace le marqueur sur le snap.

Métriques affichées : from → to, nm restants, ETA @ 7 kt, nm parcourus, cap.

### 11.3 Marqueur bateau

Port de `CatamaranMarker.jsx` :

- image `catamaran.jpg`, fond blanc rendu transparent (canvas, déjà écrit) ;
- rotation selon `bearing` (même règle est/ouest + hémisphère sud) ;
- `L.divIcon` dans le pane `boat`.

Sans image, repli : triangle CSS cyan. Le film ne doit pas casser.

---

## 12. Tracer / importer une route

Dans le film (table « on copie »). **Simplifié** : pas d’appel searoute.

| Action | Comportement étape 1 |
|---|---|
| Revenir à Berry | `customRoute = null`, recharge `public/route.geojson` |
| Import `.geojson` | `featuresToSegments` + waypoints → même pipeline sim |
| Dessiner | clics carte → points ; segment = **ligne droite** `[A, B]` |
| Terminer | construit une FeatureCollection, devient la route active |
| Supprimer | retour Berry |

Le bateau reprend le départ à chaque changement de route (déjà le cas dans
`App.jsx` via `useEffect` sur `customRoute`).

Hors étape 1 : évitement des terres, undo/redo sophistiqué, Polar, briefing
orchestrateur. Un undo simple (dernier point) suffit.

---

## 13. Sidebar (film, pas la Console)

De haut en bas :

1. Logo NAVIGUIDE + carte Berry (switch Berry / import / dessiner).
2. `LayerPills` (10 boutons).
3. Bouton simulation (ON par défaut).
4. `SimulationPanel` (métriques + Précédent / Suivant).
5. `BriefingPanel` placeholder.

Pas de colonne droite (`ExportSidebar`). Pas de grille de dons. Largeur 320 px,
même fond `slate-900` que NAVIGUIDE.

---

## 14. Stub `ici()` — le sac vide

Fichier : `src/engine/ici.js`.

```js
/** @typedef {object} SituationDossier */

export const ICI_RADIUS_NM = 30;

export function emptyDossier(lat, lon) {
  return {
    version: 1,
    at: { lat, lon },
    radiusNm: ICI_RADIUS_NM,
    zee: null,          // { name, mrgid, gold } — étape 2
    poe: [],            // ports de CETTE ZEE
    amp: [],            // dans le rayon
    projects: [],
    nearby: { marinas: [], capitaineries: [], wpi: [] },
    marks: [],          // balisage local
    science: null,      // 0 ou 1 jeu
    weather: null,      // Copernicus au point
    polar: null,        // volontairement null (pas le moteur)
    event: null,        // entrée ZEE, avis, …
  };
}

/** Étape 1 : ne remplit rien. Appelé à chaque pas pour figer le contrat. */
export function ici(lat, lon, _layers) {
  return emptyDossier(lat, lon);
}
```

Dans `App.jsx`, à chaque changement de `legContext.snappedPosition` :

```js
const dossier = ici(snapLat, snapLon);
```

Affichage étape 1 : un `<details>` discret « Dossier cockpit (vide) » sous
le briefing, pour vérifier que le contrat est branché. Pas un chat.

**Interdit :** y coller les FeatureCollections allumées sur la carte.

---

## 15. Données et proxies (prod intouchée)

`vite.config.js` (dev seulement) :

```js
server: {
  port: 5174,
  proxy: {
    "/bi": {
      target: "http://localhost:8001",
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/bi/, "/api"),
    },
    "/proxy": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
}
```

C’est **le même contrat** que `naviguide/naviguide-app/vite.config.js`.
On ne crée pas de nouvelle route FastAPI. On ne déploie rien sur le VPS.

| Si… | Alors… |
|---|---|
| Personne n’a lancé le backend BI | Route officielle via `public/route.geojson`. Couches BI = erreur sur le bouton |
| Personne n’a lancé naviguide-api | ZEE WMS / WPI = erreur. Balisage reste OK (tuiles publiques) |
| Les deux tournent en local | Toutes les couches se remplissent, **lecture seule** |

Variables :

- `VITE_BI_BASE=/bi` (défaut)
- `VITE_NG_API=` (optionnel, pour `/proxy`)

Aucune clé LLM, aucune clé Tavily, aucun `.env` secret à l’étape 1.

**Ne jamais** lancer `infra/vps/sync-from-atlas.sh`. Le simulateur ne parle
pas à Mongo.

---

## 16. Ordre de chantier (1.0 → 1.8)

Ne pas commencer 1.5 si 1.3 n’avance pas : le film avant la légende.

### 1.0 — Squelette Vite (½ journée de code)

- `npm create` / `package.json` à la main : react, react-dom, leaflet,
  lucide-react, tailwind 4, `@tailwindcss/vite`, `@vitejs/plugin-react`.
- Scripts : `dev`, `build`, `preview`, `test` (`node --test src/**/*.test.js`).
- `README.md` : lancer, port 5174, « prod intouchée », lien vers ce plan.
- Vérifier : page blanche + titre « NAVIGUIDE simulator ».

### 1.1 — Carte + fond + panes

- `useSimulatorMap` : `L.map`, tuile dark, `invalidateSize` au resize.
- `createPanes` + test d’ordre.
- CSS Leaflet importé (`leaflet/dist/leaflet.css`). Pas d’icône par défaut
  Leaflet (on n’utilise que circleMarker / divIcon) — évite le piège Vite
  des chemins `marker-icon.png`.

### 1.2 — Route officielle

- Copier `backend/data/route.geojson` → `public/route.geojson`.
- `routeFromOfficial.js` + tests (nombre de LineString, overland,
  antiméridien = 2 segments, stops escale vs intermediate).
- `useRouteLayer` : casing + trait, escales cliquables, intermédiaires muets
  (styles BI).

### 1.3 — Bateau qui avance

- Copier `useLegContext`, `simulationRoute`, `geo`, `escales` + leurs tests.
- État `simulationStep` / `catamaranPos` comme `App.jsx` (sans MapLibre).
- `SimulationPanel` + boutons.
- `CatamaranMarker` Leaflet + `flyTo` après snap.
- Recette minimale : 5× Suivant depuis Saint-Maur → on voit le golfe de
  Gascogne / l’approche Corse, cap et nm qui changent.

### 1.4 — Sidebar film

- Logo, switch Berry (déjà la seule route), bouton simulation.
- `BriefingPanel` placeholder.
- `<details>` dossier `ici()` vide.

### 1.5 — Pastilles (UI seule)

- `LAYER_CONFIG` à 10 clés.
- Cliquer inverse `show`. Spinner / erreur encore inertes.
- Recette : les 10 pastilles se voient, Science et Climat sont là.

### 1.6 — Dessin des couches

Ordre d’implémentation (du moins risqué au plus lourd) :

1. Balisage (tuiles publiques)
2. ZEE WMS (si proxy ; sinon erreur honnête)
3. WPI (si proxy)
4. PoE (points, export léger)
5. AMP (polygones bbox — réutiliser `ampStyle` + popup)
6. Science (points + popup portail)
7. Projets (canvas, lazy)
8. Capitaineries
9. Marinas (le plus gros — **OFF par défaut**, canvas obligatoire)
10. Climatologie stub

Chaque couche : test « toggle ON ajoute le layer, OFF l’enlève » si possible
en unitaire (mock `L.layerGroup`). Sinon recette manuelle.

### 1.7 — Route perso

- Import fichier GeoJSON (parser déjà dans `Sidebar.jsx` NAVIGUIDE, à copier
  sans le KML si on veut rester mince).
- Draw : clics + lignes droites + Terminer / Annuler.
- Recette : 3 clics, simulation sur **cette** ligne, retour Berry.

### 1.8 — Stub `ici()` + polish

- `ici.js` + test : le JSON a toutes les clés, tableaux vides, `zee: null`.
- Appel à chaque pas.
- README final : tableau « ça marche / ça n’existe pas encore ».
- Disclaimer visible : *Ne convient pas à la navigation* (même phrase que
  le README racine).

**Critère « étape 1 terminée » :** un skipper débutant lance `npm run dev`,
voit la route, avance le bateau, allume AMP et PoE (si BI local) ou voit
une erreur claire sur le bouton, et comprend que le briefing IA n’est pas
là. Sans ça, on ne passe pas à `ici()` réel.

---

## 17. Fichiers touchés / interdits

### On crée

- tout `naviguide-simulator/**`
- ce document (déjà)

### On peut ajouter, plus tard dans l’étape 1

- une ligne dans le `README.md` **racine** : « Simulateur (hors prod) :
  `naviguide-simulator/` — voir `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` »
  — seulement quand le squelette 1.0 existe, pour ne pas promettre une app
  absente.

### On n’ouvre pas

- `frontend/src/**`
- `backend/app/**` (aucune route nouvelle)
- `naviguide/naviguide-app/**`, `naviguide/naviguide-api/**`
- `infra/vps/**`
- les workflows CI de la prod (le simulateur a ses propres `npm test` locaux)

Si un jour l’étape 2 a besoin d’un `GET /api/ici?lat=&lon=`, ce sera un
router **nouveau** et flagué, pas un changement des exports existants. Pas
maintenant.

---

## 18. Recette

Machine : macOS, Terminal. Deux terminaux suffisent.

### A. Film seul (aucun backend)

```bash
cd naviguide-simulator
npm install
npm run dev
```

Ouvrir `http://localhost:5174`.

| # | Action | Attendu |
|---|---|---|
| A1 | Page charge | Carte sombre, route claire, bateau près de Saint-Maur |
| A2 | Suivant × 3 | Bateau avance, sidebar : from/to, nm, cap |
| A3 | Précédent | Retour d’un cran, pas de saut Cap-Vert |
| A4 | Pastille Balisage | Tuiles OpenSeaMap ou erreur réseau honnête |
| A5 | Pastille Climat | Bandeau stub, pas de crash |
| A6 | `<details>` dossier | JSON `zee: null`, tableaux `[]` |
| A7 | Import 2 points GeoJSON | Route perso, bateau au premier point |
| A8 | « Route Berry » | Retour à l’officielle |

### B. Couches BI (optionnel)

Dans un autre Terminal, lancer le backend Blue Intelligence comme d’habitude
(`backend` sur `:8001`). Recharger le simulateur.

| # | Action | Attendu |
|---|---|---|
| B1 | PoE ON | Pastilles ambre, popup avec nom |
| B2 | AMP ON, zoom Caraïbes | Polygones verts, pas toute la planète d’un coup |
| B3 | Marinas ON | La carte reste fluide (canvas). Si ça rame, laisser OFF et noter |

### C. Tests auto

```bash
cd naviguide-simulator && npm test
```

Doivent passer : `routeFromOfficial`, `simulationRoute`, `geo`, `ici` stub,
`panes`.

---

## 19. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Recopier `useAmpLayer` avec `mode === "amp"` | Haute | Nouveaux hooks toggle, styles seulement |
| Dépendre de searoute / polar pour le film | Haute | `public/route.geojson` |
| Allumer Marinas par défaut | Moyenne | OFF + canvas |
| Charger `eez_world_map.geojson` (18 Mo) | Haute | WMS limites uniquement |
| `flyTo([lon, lat])` (ordre MapLibre) | Haute | Leaflet = `[lat, lon]` ; tester Corse |
| Antiméridien Wallis–Nouméa | Moyenne | garder les 2 LineString |
| Import runtime depuis `frontend/` | Haute | copies, dossier extractible |
| Toucher nginx / VPS « pour tester » | Bloquante | localhost seulement |
| Croire l’étape 1 « prête pour Nemotron » | Produit | sac vide = honnête ; étape 2 ensuite |

---

## 20. Passage à l’étape 2

L’étape 2 peut commencer **uniquement** si A1–A3 et A6 passent.

Alors on remplit le sac, **sans** LLM :

1. Quelle ZEE contient le point (`point-in-polygon` / index déjà dans
   `zee_crossings` / `geo.py`) — **1** polygone, nom, mrgid, Gold oui/non.
2. PoE de **cette** ZEE + URL.
3. AMP / projets / 3–5 marinas-capit-WPI dans 20–30 nm.
4. Événement « on entre dans cette ZEE » (changement de mrgid).

Nano / Tavily / Ultra restent aux étapes 5–6. Stretch AMP « parc, saison,
mouillage » et overlay climatologie = après le sac.

Rappel du contrat global (ne pas l’oublier en codant l’étape 1) :

> Les boutons allument toute la couche. Le LLM n’en voit qu’une poignée.
> Un pas = `ici()` gratuit. Tavily = entrée de ZEE, clic skipper, ou alerte.

---

## 21. Documents dont ce plan hérite

- Discussion produit « simulation = film, `ici()` = moteur, boutons = carte »
  (septembre 2026).
- `docs/hackathon-nebius-nvidia.md` — un seul produit, pas la plateforme ;
  dossier autonome extractible.
- `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` — la climatologie n’est **pas**
  une couche monde à l’étape 1 ; bouton = pastille / régime, Copernicus = au
  point plus tard.
- `docs/ARCHITECTURE.md` — `MapView.js` + un hook par couche, panes verrouillés.
- Code vivant :
  - film : `naviguide/naviguide-app/src/App.jsx`, `useLegContext.js`,
    `Sidebar.jsx`, `MaritimeLayers.jsx`, `simulationRoute.js` ;
  - projecteur : `frontend/src/components/MapView.js`,
    `frontend/src/components/map/*` ;
  - route : `backend/data/route.geojson`, `GET /api/route` ;
  - exports : `GET /api/export/*`, `GET /api/amp?bbox=`.

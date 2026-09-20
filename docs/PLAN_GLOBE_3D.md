# Plan — Un globe **en plus** de la carte plane (MapLibre GL JS), sans toucher à Leaflet

Version **2.0** — 20 septembre 2026 (v1.0 le même jour, révisée sur décision
du porteur : *« je ne veux pas remplacer Leaflet par MapLibre ; je veux les
deux : soit une deuxième application avec un globe, soit une deuxième
"carte" qui serait un globe »*). Règles : `docs/REGLES_WORKFLOW_AGENT.md`.
Recherches refaites le 20 septembre sur MapLibre GL JS (sources en bas).

## 0. Décision

- **Leaflet reste la carte.** Aucun fichier `src/map/*`, `src/layers/*` ni
  aucun composant existant n'est modifié pour le globe (hors deux points
  d'entrée : un bouton et une route d'URL). Plancher `main` intact.
- **Le globe est une deuxième vue**, MapLibre GL JS v6 en projection globe,
  qui lit **les mêmes données** (route, horloge, perles, journal, couches) par
  **les mêmes hooks et la même API**. Deux façons de l'héberger, à trancher
  par le porteur au lot G0 :

| | **Option A — même application, deuxième « carte »** | **Option B — deuxième application** |
|---|---|---|
| Où | `naviguide-simulator/src/globe/` ; onglet **Carte / Globe** au-dessus de la zone carte ; la carte Leaflet reste montée (cachée par `display:none`, jamais démontée) quand le globe est visible | `naviguide-globe/` (Vite + React), déployée sur `globe.naviguide.fr`, même API `:8010`, moteur JS partagé par un paquet `@naviguide/engine` (workspace npm) |
| Ce qu'on réutilise | tout : sidebars, barre film, hooks, i18n, cartes, replay, chat | le serveur et les moteurs purs (`src/engine/*`, `src/utils/*`) ; l'UI est réécrite ou copiée |
| Ce qu'on risque | un état partagé à deux vues (on l'a déjà : `scene` de `MapScene.jsx`) ; +≈ 250 ko gzip chargés **à la demande** | duplication d'UI, deux déploiements, dérive |
| Effort | ≈ 9 jours-agent | ≈ 15 jours-agent |
| Avis | **recommandée** : un seul produit, le globe comme un onglet, tout le reste identique | si le porteur veut un site « globe » à part pour la communication |

Les lots ci-dessous sont écrits pour l'option A ; l'option B reprend les
mêmes lots avec `naviguide-globe/` comme racine et un lot G0b de squelette.

## 1. Ce que MapLibre GL JS sait faire aujourd'hui (vérifié le 20 sept.)

- **Version** : 6.10.0 ; **ESM uniquement** (plus d'UMD) ; avec Vite il faut
  un appel unique `setWorkerUrl()` (voir Installation) ; `import * as maplibregl from 'maplibre-gl'`.
- **Globe** : dans le style, `"projection": {"type": "globe"}` — sphère à
  faible zoom, passage progressif en Mercator vers le zoom 6–12 (le type
  `globe` est un préréglage de l'interpolation `vertical-perspective` →
  `mercator`). `map.setProjection()` se fait dans `style.load` et doit être
  réappliqué à chaque changement de style. Ciel : `sky.atmosphere-blend`
  (atmosphère visible à faible zoom, fondu vers zoom 7).
- **Sources** : raster XYZ (nos fonds Esri sombre/clair, EMODnet), **WMS**
  (`tiles: [url WMS avec bbox={bbox-epsg-3857}]`), GeoJSON (lignes, polygones,
  cercles, symboles), vector tiles / **PMTiles** (recommandé pour les
  polygones ZEE lourds : un seul fichier statique servi par nginx, plugin
  `pmtiles`).
- **Marqueurs HTML** (`maplibregl.Marker` avec `element`) : sur le globe, un
  marqueur passé **derrière la sphère** prend l'opacité `opacityWhenCovered`
  et sa popup se ferme — nos catamaran, avion, drapeaux passent tels quels.
- **Popups** ancrées (`Popup.setLngLat`) : la bulle événement du film.
- **Antiméridien** : une ligne qui traverse 180° se dessine en **dépliant**
  la longitude (ajouter/retirer 360° au point suivant si l'écart ≥ 180°) —
  notre route officielle est déjà dépliée (`filmCum`), c'est un avantage ;
  `LngLatBounds.adjustAntiMeridian()` existe pour `fitBounds`. Point connu :
  GeoJSON **aux pôles** (issue #6072) — sans objet pour nous.
- **Caméra** : `flyTo` / `easeTo` / `jumpTo` suivent la sphère ;
  `fitBounds` ; `pitch`, `bearing`, `roll` ; `getZoom()` **baisse quand la
  caméra s'incline** vers un pôle (ne pas piloter des tailles par le zoom en
  mode globe). Passage `vertical-perspective` → `globe` non animé (#5114) :
  rester en `globe`.
- **Couches WebGL personnalisées** sur le globe : possibles mais il faut le
  prélude de projection (`args.shaderData.vertexShaderPrelude`, recompiler
  quand `variantName` change) et la formule de profondeur de MapLibre pour
  cacher la face arrière (billet mercator.blue, mai 2026). → nos flèches GRIB
  et roses climatologiques passent en couches **`symbol`** (icônes générées
  par `canvas` → `map.addImage`, rotation `icon-rotate` par donnée), pas en
  couche custom.
- **v6** : événements en classes (tester `type`, pas `instanceof`) ;
  propriétés GeoJSON imbriquées désormais des objets (pas de `JSON.parse`) ;
  `setMissingStyleImageResolver` remplace le listener `styleimagemissing` ;
  `zoomLevelsToOverscale` change le découpage des tuiles vectorielles.
- **React** : `react-map-gl/maplibre` 8.1.2 supporte v6 ; mais comme pour
  Leaflet (classe `MapSceneController` pilotée par `useEffect`), on garde
  **`maplibre-gl` nu** dans un `GlobeSceneController` — pas de wrapper.
- **Performance** : guide officiel « Optimising MapLibre Performance: Tips
  for Large GeoJSON Datasets » ; règle : GeoJSON < 5 Mo, sinon tuiles
  vectorielles (tippecanoe → PMTiles).
- **Coût** : 0 $ (BSD ; nos tuiles actuelles ; PMTiles statique).

## 2. Architecture (option A)

```
src/map/MapScene.jsx (Leaflet, inchangé)  ─┐
                                           ├─ même objet `scene` (route, horloge, bateau, couches, cartes, film)
src/globe/GlobeScene.jsx  (MapLibre)      ─┘
src/globe/GlobeSceneController.js   — miroir de MapSceneController pour MapLibre : sources/couches, marqueurs, caméra, popups
src/globe/globeStyle.js             — style JSON : fonds, projection globe, sky, light
src/globe/layers/*.js               — route, bateau, escales, BI (points/polygones), WMS, GRIB symbols, climato symbols, PMTiles ZEE
src/globe/GlobeToggle.jsx           — onglet Carte / Globe (au-dessus de la zone carte), préférence mémorisée, `?view=globe`
```

- `App.jsx` : un seul ajout — `view === "globe"` monte `GlobeScene` **à côté**
  de `MapScene` (lazy `import()`), et passe le même `scene`. Leaflet reste
  monté et continue de recevoir `scene` (pas de démontage, pas de perte
  d'état) ; il est masqué par CSS pendant que le globe est visible.
- Tout ce qui parle à la carte par `window.__naviguideScene` continue de
  parler à Leaflet ; le globe expose `window.__naviguideGlobe` (tests).
- Les clics sur le globe (fiches, popups, dessin) appellent **les mêmes
  callbacks** que Leaflet (`onFocus`, `onEscaleSheet`, `drawing.add`…).

## 3. Les lots

Ordre : **G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7**. Chaque lot : Carte
(Leaflet) **inchangée** — recette « aucun changement visible » sur les trois
parcours fixes — et un pas de plus pour le Globe. Taille : S ≤ ½ j, M ≤ 2 j.

### Lot G0 — Éprouvette et décision A / B (S)

Page hors application `naviguide-simulator/globe-spike.html` (Vite
multi-page, non déployée) : MapLibre 6 globe, fond raster sombre (URL de
`src/layers/styles.js`), WMS ZEE, route officielle (`GET /voyage/official`),
marqueur HTML catamaran qui avance, `flyTo`, mesure FPS / poids / temps de
chargement des polygones VLIZ en GeoJSON puis en PMTiles (tippecanoe).
**Sortie** : `docs/audits/GLOBE_SPIKE.md` (chiffres, captures) et la décision
A / B du porteur. Critères go : ≥ 30 FPS sur MacBook, route continue au
Pacifique, ZEE < 3 s.

### Lot G1 — Onglet Carte / Globe, fond, attribution, caméra (M)

`GlobeScene.jsx`, `GlobeSceneController.js`, `globeStyle.js`,
`GlobeToggle.jsx` ; `App.jsx` **par extrait** (`rg -n "MapScene" src/App.jsx`) :
montage conditionnel + `scene` partagé ; `setWorkerUrl` ; attribution avec
liens (lot M). **Recette (Globe)** : onglet « Globe » → sphère avec fond
sombre et atmosphère, molette, attribution ; onglet « Carte » → Leaflet exactement
comme avant (capture avant/après identique). Spec : `data-testid="view-globe"`,
`window.__naviguideGlobe.getProjection().type === "globe"`.

### Lot G2 — Route, bateau, escales, avion, sillage, caméra qui suit (M)

Sources GeoJSON `route-done` / `route-todo` (longitudes dépliées), marqueurs
HTML (catamaran, avion, drapeaux — un seul exemplaire chacun), sillage, saut
avion en arc, `easeTo` continu en Suivre. **Recette (Globe)** : Suivre à
Nouméa ; Simulation : le bateau avance, la caméra suit ; capture Papeete →
Mata-Utu (ligne continue).

### Lot G3 — Couches BI, ZEE en PMTiles, fiches (M)

Ports, PoE, AMP, science, projets, balisage ; ZEE : PMTiles générées par un
script `infra/tiles/build_zee_pmtiles.sh` (tippecanoe), servies par nginx
(`/tiles/zee.pmtiles`, `Accept-Ranges`) ; clic → mêmes fiches (`CardLinks`).
**Recette (Globe)** : Calques → chaque case ; clic port → fiche ; ZEE
survolée en surbrillance.

### Lot G4 — GRIB et climatologie en symboles (M)

Icônes générées (flèches, barbules, roses) → `symbol` ; mêmes chiffres que
la popup satellite. **Recette** : captures Carte / Globe côte à côte, même
vent.

### Lot G5 — Popups, bulle événement, tracer ma route (M)

Popup satellite ancrée ; bulle du film (plan film F4) ancrée au marqueur ;
dessin par clics (mêmes callbacks). **Recette** : Brisbane → SF sur le globe
(grand cercle), trois onglets Vent / Vagues / Courants.

### Lot G6 — Le film sur le globe (S)

Caméra : `easeTo` 30 Hz, altitude constante par chapitre, `pitch` 25–35°,
orbite douce (`bearing` +2°/s) pendant les bulles longues. **Recette** :
Revoir l'expédition en Globe, 2 min 30, zoom stable, bulles.

### Lot G7 — Parité et tests sur les deux vues (S)

Liste de parité cochée ; spec Playwright joué avec `?view=carte` et
`?view=globe` ; le défaut reste **Carte** sauf décision du porteur.

## 4. Effort, risques, coût

- **Effort option A** : G0 1 j, G1 1,5 j, G2 1,5 j, G3 2 j, G4 1,5 j, G5 1,5 j,
  G6 0,5 j, G7 0,5 j ≈ **10 jours-agent**. Option B : + squelette d'app,
  copie des sidebars/barre film, déploiement ≈ **+5 j**.
- **Risques** : PMTiles à générer (tippecanoe sur le Mac ou le VPS) ; Safari
  et WebGL2 ; deux vues qui consomment `scene` (le Leaflet caché continue de
  calculer : mesurer, et si besoin geler ses effets quand il est masqué —
  **sans le démonter**) ; `getZoom` sous inclinaison.
- **Coût** : 0 $.

## 5. Réponse au porteur

On garde Leaflet tel quel et on ajoute un **onglet Globe** (option A) — ou
un site globe séparé (option B) — alimenté par les mêmes données, en
MapLibre GL JS 6 (libre, 0 $). Dix jours-agent pour l'option A ; le film
peut se tourner sur le globe si G0–G2 et G6 sont recettés avant la vidéo,
sinon sur la carte.

## Sources (20 sept. 2026)

- MapLibre GL JS 6.10.0 — « Display a globe with an atmosphere » (style
  `projection: globe`, `sky.atmosphere-blend`, `light`) ; « Display line
  that crosses 180th meridian » (dépliage de longitude) ; « v5 to v6
  migration guide » (ESM only, `setWorkerUrl`, événements en classes,
  propriétés GeoJSON imbriquées, `setMissingStyleImageResolver`) ; « Add a
  WMS source » ; « PMTiles source and protocol » ; « Optimising MapLibre
  Performance: Tips for Large GeoJSON Datasets » ; API `Map` (`flyTo` suit
  la sphère), `LngLatBounds.adjustAntiMeridian`, `FitBoundsOptions`.
- MapLibre Style Spec — `projection` (`vertical-perspective` → `mercator`
  par interpolation sur le zoom).
- GitHub maplibre-gl-js — #5079 (opacité des marqueurs derrière le globe,
  fermeture des popups), #5114 (pas d'animation `vertical-perspective` →
  `globe`), #6072 (GeoJSON aux pôles), #8168 (suivi des cassures v6).
- mercator.blue, « Putting custom WebGL layers on MapLibre's globe »
  (28 mai 2026) : prélude de projection, formule de profondeur, `getZoom`
  sous inclinaison.
- react-map-gl 8.1.2 (juil. 2026) : support MapLibre v6 ; Stadia Maps,
  « Turn your maps into a 3D globe ».

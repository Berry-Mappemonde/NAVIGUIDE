# Plan — La même application sur un globe (« version Google Earth »)

Version **1.0** — 20 septembre 2026. Règles : `docs/REGLES_WORKFLOW_AGENT.md`.
Question du porteur : *« est-il possible de faire exactement la même
application avec un globe, Google Earth, y compris toutes les fonctionnalités,
sauf qu'au lieu d'une carte plane ce sera un globe ? Qu'est-ce que ça
nécessite ? »* Réponse courte : **oui, mais pas avec Google Earth** ; avec un
moteur de globe dans le navigateur, et la façon la moins risquée est de garder
Leaflet comme plancher et d'ajouter un rendu « Globe » derrière une
abstraction. Recherches faites le 20 septembre (sources en bas).

## 0. Ce que « Google Earth » veut dire aujourd'hui

| Produit | Programmable pour notre app ? | Verdict |
|---|---|---|
| **Google Earth** (application, earth.google.com) | Non. Le plugin « Google Earth API » est mort depuis 2015. Earth Web importe des KML/KMZ et des projets, sans code applicatif, sans nos couches dynamiques, sans nos panneaux. | Écarté pour l'app. Utile pour **une vidéo** : exporter la route en KML et la survoler dans **Google Earth Studio** (rendu cinématique) = plan B pour la vidéo de soumission. |
| **Google Maps Platform — 3D Maps** (`<gmp-map-3d>`, Maps JavaScript API) | Oui : globe photoréaliste, `Polyline3DElement`, `Marker3DElement` (+ popover), `Polygon3DElement`, `Model3DElement` (glTF : un catamaran 3D), `flyCameraTo` / `flyCameraAround`, événements caméra. **Limites** : pas de couche raster à nous (pas de fond sombre Esri, pas de bathymétrie EMODnet, pas de WMS ZEE, pas de symboles GRIB peints), vecteurs seulement ; statut **Preview** (gratuit, sans SLA), tarification à l'usage annoncée à la GA ; **restriction EEE** documentée pour les tuiles photoréalistes (`Map Tiles API` refusée aux comptes facturés dans l'Espace économique européen) — à vérifier pour `gmp-map-3d` avec un compte français. | Spectaculaire, mais fermé, incertain (prix, EEE), et il faudrait abandonner la moitié de nos couches. Non recommandé comme moteur principal. |
| **CesiumJS** (open source, Apache-2) | Oui : vrai globe 3D, terrain, 3D Tiles (y compris les tuiles Google via Cesium ion, même restriction EEE), `ImageryLayer` WMS/XYZ (nos fonds et WMS marchent), entités GeoJSON, billboards HTML, caméra libre. Lourd (≈ 3–4 Mo), courbe d'apprentissage, WebGL exigeant sur portable. | Bon si l'on veut du **relief** (bathymétrie en 3D, atterrages). Sur-dimensionné pour une route océanique. |
| **MapLibre GL JS v5/v6** (open source, BSD) — projection **globe** | Oui : globe à faible zoom qui devient Mercator en zoomant (≈ zoom 6), **sources raster XYZ et WMS**, GeoJSON (lignes, polygones, cercles, symboles), `Marker` HTML (nos icônes catamaran / avion / drapeaux), `Popup` ancrés, `flyTo` / `easeTo` / `jumpTo`, couches WebGL personnalisées (des billets de 2026 montrent des couches custom sur le globe). Léger (≈ 800 ko), même modèle mental que Leaflet. Points connus : GeoJSON aux pôles (issue #6072), rendu des lignes très longues qui coupent l'antiméridien à tester. | **Recommandé.** C'est le chemin où l'on garde **toutes** nos couches et où la migration se fait couche par couche. |

Autres écartés : deck.gl `GlobeView` (expérimental, pas de raster), Globe.gl /
three-globe (jolis, mais pas de tuiles WMS ni de popups riches), Mapbox GL
(propriétaire, facturé).

## 1. Ce qu'il faut porter (inventaire du code Leaflet)

Leaflet touche **≈ 2 300 lignes** dans 17 fichiers ; le reste de l'app
(moteur, hooks, sidebars, film, serveur) est indépendant de la carte.

| Fichier | Lignes | Ce qu'il fait avec Leaflet | Équivalent MapLibre |
|---|---|---|---|
| `src/map/MapSceneController.js` | 881 | carte, marqueurs (13 `polyline`, 8 `marker`, 9 `divIcon`), caméra (`setView`, `flyTo`, `fitBounds`), copies-monde des drapeaux, waypoints | `Map`, `Marker` HTML, sources GeoJSON `route`, `route-done`, `waypoints`, `flyTo`/`easeTo`, plus de copies-monde (le globe n'en a pas besoin) |
| `src/layers/useToggleLayers.js` | 403 | couches BI (GeoJSON points/polygones, `circleMarker`), WMS ZEE, EMODnet | sources GeoJSON + couches `circle`/`fill`/`line`/`symbol` ; `raster` WMS |
| `src/layers/useClimatologyLayer.js` + `climatologyPaint.js` | 250 + | roses/cyclones peints sur `L.canvas` | couche `symbol` avec icônes générées (canvas → `addImage`) ou couche custom |
| `src/layers/useGribCorridorLayer.js` + `gribSymbols` | 136 | flèches / barbules GRIB sur canvas | idem : `symbol` avec rotation par donnée (`icon-rotate`) — plus fluide que le canvas |
| `src/layers/popupFit.js`, popup satellite | 260 | `L.popup` positionné | `Popup` ancré (`setLngLat`) |
| `useRouteLayer`, `useAltRouteLayer`, `useAirHopLine`, `useWakeLayer`, `points.js`, `spatialCatalogLayer.js` | ≈ 600 | polylignes, sillage, saut avion | sources GeoJSON ; le saut avion en `line` géodésique (le globe rend l'arc naturellement) |
| `CatamaranMarker.jsx`, `PlaneMarker.jsx` | 154 | `divIcon` React | `Marker` avec `element` React (portal) |
| `MapScene.jsx`, `useSimulatorMap.js`, `main.jsx` | 246 | montage, `window.__naviguideScene` | idem |

Ce qui devient **plus simple** sur un globe : les copies-monde (drapeaux ×3),
la ligne de changement de date (route Pacifique), les grands cercles (le saut
avion, la ligne Brisbane → SF), la caméra du film (orbite).
Ce qui devient **plus difficile** : les 2 couches canvas (climatologie, GRIB)
et le rendu des polygones ZEE de VLIZ (lourds ; passer par tuiles vectorielles
ou simplification serveur), les tests de contrat qui lisent `getZoom()`.

## 2. Décision d'architecture : un adaptateur, deux moteurs

On n'échange pas Leaflet contre MapLibre d'un coup (plancher `main`). On
introduit une **interface de scène** que `MapSceneController` consomme, avec
deux implémentations :

```
src/map/adapters/SceneAdapter.d.ts   (contrat : createMap, setCamera, flyTo, addLineSource, updateLine,
                                       addPointLayer, addRaster, addWms, marker(create/move/remove), popup, on(event))
src/map/adapters/leaflet/…           (l'existant, déplacé, comportement identique)
src/map/adapters/maplibre/…          (le globe)
```

Le choix se fait par une **préférence utilisateur** « Carte / Globe » dans les
outils de droite (défaut : Carte tant que la parité n'est pas recettée), et
par `?engine=globe` pour les tests. `window.__naviguideScene.engine` dit lequel
tourne. Le bundle du globe est chargé **à la demande** (`import()`).

## 3. Les lots

Ordre : **G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8**. Taille : S ≤ ½ jour,
M ≤ 2 jours, L ≤ 4 jours. Chaque lot : « Carte » inchangé (recette « aucun
changement visible » sur les trois parcours fixes) **et** un pas de plus pour
« Globe ».

### Lot G0 — Éprouvette (S)

Page **hors application** `naviguide-simulator/globe-spike.html` : MapLibre
globe, fond raster sombre (même URL Esri que `styles.js`), WMS ZEE, la route
officielle (GeoJSON du serveur), un marqueur HTML catamaran qui avance,
`flyTo`. Mesures : FPS sur MacBook, poids du bundle, rendu de la route à
l'antiméridien, polygones ZEE VLIZ (temps de chargement). **Sortie** : une
page de mesures dans la PR et la décision go / no-go (critères : ≥ 30 FPS,
route continue, ZEE < 3 s).

### Lot G1 — Adaptateur de scène, moteur Leaflet (M)

Extraire l'interface § 2 ; `MapSceneController` ne touche plus `L.` que par
l'adaptateur. **Aucun changement visible** ; tous les tests de contrat passent
(`MapSceneMarkers.test.js`, `sceneGate.test.js`). Spec fumée inchangé.

### Lot G2 — Moteur globe : fonds, attribution, caméra (M)

Adaptateur MapLibre : carte, fonds raster (sombre / clair), attribution
(liens du lot M), `setCamera`/`flyTo`, préférence « Carte / Globe » (défaut
Carte). **Recette (Globe)** : le globe s'affiche avec le fond sombre, la
molette zoome, l'attribution a ses liens ; capture. **Carte** : inchangé.

### Lot G3 — Route, bateau, escales, avion, sillage (M)

Sources GeoJSON pour la route (faite / à venir), marqueurs HTML (catamaran,
avion, drapeaux sans copies-monde), sillage, saut avion en arc. Caméra qui
suit (mode Suivre). **Recette (Globe)** : Suivre à Nouméa : bateau, route,
drapeaux ; Simulation : le bateau avance, la caméra suit ; capture à
l'antiméridien (route Papeete → Mata-Utu continue).

### Lot G4 — Couches BI et WMS (M)

Ports, PoE, AMP, science, projets, balisage (points / polygones), ZEE WMS,
EMODnet ; popups des fiches (`CardLinks` inchangés). **Recette (Globe)** :
Calques → chaque case affiche sa couche ; clic sur un port ouvre la fiche.

### Lot G5 — GRIB et climatologie en symboles (M)

Flèches GRIB et roses climatologiques en couches `symbol` (icônes générées).
**Recette (Globe)** : Simulation, GRIB visible autour du bateau, roses au
zoom monde ; captures Carte / Globe côte à côte (même vent, mêmes chiffres
dans la popup satellite).

### Lot G6 — Tracer ma route, popups satellite, bulle événement (M)

Dessin (clics → segments searoute), popup Vent / Vagues / Courants ancrée,
bulle événement du film (plan film, lot F4) ancrée au marqueur. **Recette** :
Brisbane → SF sur le globe (grand cercle Pacifique, pas l'Alaska) ; popup
satellite avec ses trois onglets.

### Lot G7 — Le film sur le globe (S)

Caméra du film : `easeTo` continu, altitude constante par chapitre, légère
inclinaison (`pitch` 30°) et orbite douce pendant les bulles longues.
**Recette** : Revoir l'expédition en Globe : 2 min 30, zoom stable, bulles.
C'est le plan « waouh » de la vidéo si G0–G6 sont recettés à temps ; sinon la
vidéo se fait en Carte.

### Lot G8 — Parité, défaut, nettoyage (S)

Liste de parité cochée (toutes les surfaces du plancher `main` disponibles en
Globe) ; si oui, le défaut peut passer à Globe **sur décision du porteur** ;
Leaflet reste disponible (Carte) ; tests de contrat exécutés sur les deux
moteurs (`?engine=`).

## 4. Effort, risques, coût

- **Effort** : G0 1 j, G1 2 j, G2 1 j, G3 2 j, G4 2 j, G5 2 j, G6 2 j, G7 1 j,
  G8 1 j ≈ **14 jours-agent**, sécables ; rien n'oblige à finir avant la
  soumission — G0 à G3 suffisent pour un plan de film sur globe.
- **Risques** : performance des polygones ZEE (mitigation : tuiles vectorielles
  `tippecanoe` servies par nginx, ou simplification serveur déjà en place dans
  `zee_local.py`) ; couches canvas à réécrire ; Safari WebGL2 ; tests de contrat
  qui lisent l'API Leaflet (à faire passer par l'adaptateur).
- **Coût** : **0 $** en MapLibre (bibliothèque libre, nos tuiles actuelles).
  Google 3D Maps : gratuit en Preview, tarif inconnu à la GA, risque EEE ;
  Cesium : libre, ion facultatif.

## 5. Réponse au porteur

Oui, la même application peut tourner sur un globe, avec toutes ses
fonctions, en ~14 jours-agent par lots recettables, sans rien perdre du
plancher : MapLibre GL JS en projection globe derrière un adaptateur, Leaflet
gardé comme « Carte ». « Google Earth » au sens strict n'est pas une plateforme
d'application ; Google Maps 3D est possible mais fermé, payant à terme et
vecteurs seulement ; Cesium est la voie si un jour on veut le relief.

## Sources (20 sept. 2026)

- Google, référence `Map3DElement` (Maps JavaScript API, mis à jour le
  17 sept. 2026) : propriétés, `flyCameraTo`, `flyCameraAround`, événements.
- Google, liste de prix Maps Platform (10 sept. 2026) : « Photorealistic 3D
  Tiles » 1 000 requêtes racine gratuites puis 6 $/1 000.
- Spatialized.io, « Google Maps 3D Tutorial » : 3D Maps en **Preview, gratuit**,
  tarification à la GA ; `Polyline3DElement`, `Marker3DInteractiveElement`,
  `Polygon3DElement`, `Model3DElement` ; **restriction EEE** de la Map Tiles API.
- MapLibre GL JS : exemples « Display a globe with an atmosphere », « Add a
  WMS source » ; Stadia Maps, « Turn your maps into a 3D globe » (globe depuis
  la v5) ; guide de migration v5 → v6 ; mercator.blue, « Putting custom WebGL
  layers on MapLibre's globe » (mai 2026) ; issue #6072 (GeoJSON aux pôles).
- Cesium, « Photorealistic 3D Tiles from Google Maps in CesiumJS ».

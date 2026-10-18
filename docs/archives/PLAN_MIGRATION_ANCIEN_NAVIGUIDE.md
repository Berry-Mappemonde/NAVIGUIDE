# Plan — Intégrer ce qui reste utile de l'ancien NAVIGUIDE (lots N1 → N4)

Version **1.0** — 21 septembre 2026, soir. Révision de l'analyse Ask du 20 sept.
(`~/agent-tools/ask-agents-20260920-212506/03.log` : matrice « unique / remplacé /
mort » et lots H0, M1 → M5) à la lumière des **décisions du porteur du 21 sept.** :

- **Import ET export de route, GeoJSON ET KML** — l'ancienne interdiction de
  l'étape 1 est levée. Import dans « Tracer ma route », export dans le panneau
  droit.
- **Anti-trafic (score) et piraterie (cartes NOW)** — gardés, depuis le moteur
  searoute et les données de l'ancien (`routing_ab/cargo.py`, `risk_engine.py`).
- **Pas de portage des 4 discours thématiques** (Ports / Sécurité / Météo /
  Cruisers) — abandonnés.
- Règle d'or inchangée : **on copie une idée ou une donnée, jamais un
  `App.jsx`** ; on n'édite pas `naviguide/` (on le lit) ; aucune surface de
  `main` n'est retirée ; les chiffres viennent des tables, jamais d'un LLM.

## 0. Ce qui est déjà remplacé (ne rien recopier)

Carte + route Berry + searoute, dessin de route, simulation, polaire, météo
Copernicus, calques BI, climatologie (atlas BI), briefing (`ici()`), chat
(`LogbookChat`), isochrones (une jambe + skipper). Le graphe voile
`routing_ab` (portes Torres / Mentawai, décalage hors couloirs) reste de la R&D
**après le 28** ; `llm_cascade.py`, `proxy_server.py`, les 4 services et
l'orchestrateur LangGraph ne sont **pas** repris. Archiver l'ancien (README
« legacy », `www.naviguide.fr` → simulateur) vient **après** les lots, avec la
séparation des dépôts (H1).

## 1. Les lots

Convention : « Fichiers » = les seuls à ouvrir. Les fichiers de `naviguide/`
sont **lus**, jamais modifiés. Recette = ce que le porteur voit dans Chrome.

### N1 — Import GeoJSON / KML dans « Tracer ma route » (M)

Objectif : dans « Tracer ma route », un bouton **Importer** accepte un fichier
`.geojson` / `.json` / `.kml` ; ses points (et la ligne, s'il n'y a pas de
points) deviennent les waypoints de la route dessinée, dans l'ordre du fichier ;
le tracé se calcule comme après des clics (searoute par jambes) ; le sac `ici()`
se remplit sur cette route (lot T). Rien n'est perdu de ce qui existe (dessin au
clic, Terminé, effacer).

Source à lire : `naviguide/naviguide-app/src/utils/waypointsFromCollection.js`
(Points → waypoints ; sinon LineString → waypoints échantillonnés, l. 6-30) ; le
KML n'y est pas parsé : à écrire (DOMParser : `Placemark > Point > coordinates`,
`LineString > coordinates`, ordre du fichier).

Fichiers (simulateur) : `src/utils/routeImport.js` (créer : `parseRouteFile(text, name) → {points:[{lat,lon,name}], source}` GeoJSON + KML, erreurs lisibles), `src/utils/routeImport.test.js` (créer, fixtures GeoJSON Points / LineString / KML), `src/hooks/useRouteDrawing.js` (166 l. : ajouter `importPoints(points)` qui rejoue le flux d'un clic par point), le composant du mode dessin (rg -n "drawing|Terminé|drawnPoints" src/components/*.jsx : bouton Importer + `<input type=file accept=".geojson,.json,.kml">`), `src/i18n/fr.js`, `en.js`, `src/App.jsx` PAR EXTRAIT (rg -n "useRouteDrawing|onDrawingWaypointClick|addDrawnPoint").

Étapes : 1) parseur GeoJSON (Point, MultiPoint, LineString, FeatureCollection ; noms depuis `properties.name`) et KML (Placemark Point / LineString) → points ordonnés, dédoublonnés (< 0,1 nm), limité à 60 points (message au-delà) ; 2) `importPoints` : même chemin que les clics (searoute par jambe, `Terminé` disponible), remplace la route dessinée en cours (confirmation si elle n'est pas vide) ; 3) bouton **Importer** dans le mode Tracer, à côté de Terminé / Effacer, pas de texte d'aide ; 4) erreurs : fichier illisible → message court, rien d'autre ne change.

Tests : `routeImport.test.js` — GeoJSON Points, LineString seule, KML Placemarks, KML LineString, fichier vide/invalide ; `useRouteDrawing.test.js` — `importPoints` produit le même état que N clics. `npm test`, `npx vite build`, spec e2e `e2e/lots/n1-import.spec.js` (charge une fixture, la route apparaît).

Recette (visuelle) : Tracer ma route → **Importer** → choisir un `.geojson` de 3 points (fixture fournie dans la PR) → **tu dois voir** les 3 drapeaux et la route calculée entre eux ; refaire avec un `.kml` → même chose ; puis **Terminé** → le sac se remplit autour du bateau comme après des clics.

### N2 — Export GeoJSON / KML de la route de la vue, panneau droit (S)

Objectif : dans le panneau droit (outils), un bloc **Exporter** avec deux boutons
**GeoJSON** et **KML** qui téléchargent la **route de la vue** : Berry en Suivre
(trait + escales + drapeaux), la route dessinée en Tracer, la route de la
simulation en Simulation. Noms de fichiers datés. Rien d'autre ne change.

Source à lire : `naviguide/naviguide-app/src/components/ExportSidebar.jsx`
(`downloadFile` l. 59-70, `buildGeoJSON` l. 72-115, `buildKML` l. 116-225 :
couleurs KML aabbggrr, placemarks).

Fichiers : `src/utils/routeExport.js` (créer : `buildGeoJSON(segments, points, name)`, `buildKML(segments, points, name)`, `downloadFile` — portés et allégés), `src/utils/routeExport.test.js` (créer), `src/components/ToolsSidebar.jsx` (489 l. : bloc Exporter, deux boutons, `data-testid="export-geojson"` / `"export-kml"`), `src/i18n/fr.js`, `en.js`, `src/App.jsx` PAR EXTRAIT (rg -n "ToolsSidebar" : passer la route de la vue — segments + marques).

Étapes : 1) porter `buildGeoJSON` / `buildKML` (FeatureCollection : une LineString par jambe avec `properties` {from, to, nm, kind mer/terre/air}, un Point par escale avec nom et pays ; KML équivalent, jambes avion en pointillé) ; 2) la route de la vue : Suivre = route officielle, Tracer = route dessinée, Simulation = route simulée ; 3) deux boutons dans le panneau droit, pas de texte d'aide ; nom `naviguide-<mode>-<AAAA-MM-JJ>.geojson|kml`.

Tests : `routeExport.test.js` — GeoJSON valide (JSON.parse, types), KML bien formé (DOMParser), jambes avion marquées, N escales → N Points. `npm test`, `npx vite build`, spec `e2e/lots/n2-export.spec.js` (clic → téléchargement intercepté, contenu non vide).

Recette (visuelle) : Panneau droit → **Exporter** → **GeoJSON** → **tu dois voir** un fichier téléchargé qui s'ouvre dans un visualiseur (geojson.io) avec la route et les escales ; **KML** → même chose dans Google Earth ; en Tracer, l'export contient la route dessinée.

### N3 — Score anti-trafic depuis le moteur searoute (M)

Objectif : chaque jambe en mer porte un **score anti-trafic** (1,0 = hors des
couloirs de cargos, 0,0 = dedans) et la liste des couloirs traversés ; la Revue
du plan affiche une pastille par jambe (« couloir : Gibraltar, Malacca »), le
panneau droit une pastille pour la route de la vue ; le trait **ne change pas**
(le décalage hors couloir reste de la R&D `routing_ab`, après le 28). Le score
alimente l'expert (R10a : alerte `traffic`, poids 1).

Source à lire : `naviguide/naviguide-api/routing_ab/cargo.py` (`SHIPPING_LANES`
l. 15-41, `_in_box`, `point_lane_weight`, `anti_shipping_score` l. 60-73,
`lane_hits` l. 74) et ses tests (`test_routing_ab_metrics.py`) ; côté simulateur
`src/layers/riskColors.js` (couleurs MapLibre orphelines, à recoder en Leaflet
ou à laisser).

Fichiers : `server/shipping_lanes.py` (créer : copie de `SHIPPING_LANES` + fonctions, source citée), `server/tests/test_shipping_lanes.py` (créer, repris de l'ancien), `server/route_engine.py` PAR EXTRAIT (rg -n "def route|segments|meta" : score et `lane_hits` en métadonnée de chaque jambe, après searoute, jamais dans la géométrie), `server/plan_review.py` (pastille par jambe), `src/components/PlanReview.jsx`, `src/components/ToolsSidebar.jsx` PAR EXTRAIT (pastille route de la vue), `src/i18n/fr.js`, `en.js`.

Étapes : 1) module serveur + tests ; 2) `GET /route` et la route officielle exposent `antiShipping: {score, lanes[]}` par jambe (métadonnée) ; 3) Revue du plan : « couloirs : Gibraltar » sous la jambe, teinte ambre si score < 0,55 ; panneau droit : pastille route ; 4) pas de texte d'aide, pas de changement de trait.

Tests : `test_shipping_lanes.py` ; `test_route_engine` — Berry Gibraltar / Aden / Malacca → score < 1 et couloirs nommés, géométrie identique ; `PlanReview.test.js` — pastille. `npm test`, `.venv/bin/python -m pytest -q`, `npx vite build`.

Recette (visuelle) : Panneau droit → Revue du plan → jambe **Ajaccio → Fort-de-France** : « couloirs : Gibraltar » ; jambe **Nouméa → Dzaoudzi** : rien ou Malacca selon le trait ; le trait sur la carte est **inchangé**.

### N4 — Zones de piraterie → cartes NOW et alertes (S)

Objectif : quand le bateau (Suivre, Simulation, film) est dans une zone de
piraterie recensée, une carte NOW « Piraterie — <zone> · niveau <HIGH/MEDIUM> ·
source IMB/UKMTO » apparaît (et disparaît hors zone) ; l'expert (R10a) en fait
une alerte `piracy` (poids 3 HIGH, 2 MEDIUM, 1 LOW). Aucun score composite, aucune
note inventée.

Source à lire : `naviguide/naviguide_workspace/naviguide_agent3/risk_engine.py`
(`PIRACY_ZONES` l. 42-49 : boîtes lat/lon + niveau ; `CYCLONE_BASINS` : **ne pas
copier**, l'atlas BI a la saison cyclonique).

Fichiers : `server/data/piracy_zones.json` (créer : les boîtes, niveau, source, date de la table), `server/piracy.py` (créer : `zone_at(lat, lon)`), `server/tests/test_piracy.py`, `server/ici_warm.py` PAR EXTRAIT ou `server/main.py` PAR EXTRAIT (rg -n "def ici|bag\[" : ajouter `piracy` au sac), `src/engine/momentCard.js` PAR EXTRAIT (rg -n "kind ===|severity" : carte NOW `piracy`), `src/engine/momentCard.test.js`, `src/i18n/fr.js`, `en.js`.

Étapes : 1) table JSON versionnée + `zone_at` ; 2) le sac `ici()` porte `piracy: {name, level, source}` ou rien ; 3) carte NOW « Piraterie » (sévérité alerte si HIGH, décision sinon), une seule, disparaît hors zone ; 4) exposée à l'expert (R10a) comme alerte datée.

Tests : `test_piracy.py` — Aden → HIGH, Atlantique nord → rien ; `momentCard.test.js` — carte NOW présente/absente. `npm test`, `.venv/bin/python -m pytest -q`, `npx vite build`.

Recette (visuelle) : Simulation → placer le curseur dans le **golfe d'Aden** (jambe Dzaoudzi → …) → **tu dois voir** une carte NOW « Piraterie — Horn of Africa / Gulf Aden · HIGH · IMB/UKMTO » ; au large de La Rochelle → **aucune** carte piraterie.

## 2. Ordre et pile

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | N1 | M | routeImport.js, useRouteDrawing.js, mode Tracer |
| 2 | N2 | S | routeExport.js, ToolsSidebar.jsx |
| 3 | N3 | M | shipping_lanes.py, route_engine.py, PlanReview |
| 4 | N4 | S | piracy.py, ici, momentCard |

Lancement : `caffeinate -i python3 infra/agents/run_lots.py --from N1 --until N4`
(ou via `loop.py`, quand le GO les cite). Après les lots : archiver l'ancien
(README legacy, redirection `www.naviguide.fr`) dans le lot H1 (séparation des
dépôts, 26–27 sept.).

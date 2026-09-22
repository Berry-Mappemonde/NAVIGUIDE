> **Archivé le 22 septembre 2026 — réalisé** (P1 GRIB `pending`, profil prod). Mémoire : catalogues spatiaux, pipeline météo partagé, Web Worker. Index : [docs/README.md](../README.md).

# Pipeline d’affichage — simulator.naviguide.fr

## Décision : les 4 leviers à traiter d’abord

1. **Sortir l’animation du rendu global React.** Pendant une lecture, `useRoutePlayback` publie le playhead à **12 Hz** ; cela re-rend `App` et ses deux sidebars, puis recalcule notamment les statistiques complètes de route.
2. **Rendre le sillage incrémental.** À chaque tick, `useWakeLayer` reconstruit les coordonnées du chemin accompli *et* restant, les triple pour le tour du monde et les repasse à Leaflet.
3. **Éviter de détruire/recréer les objets Leaflet mobiles.** Les barbules GRIB, les drapeaux et les icônes bateau sont actuellement régénérés par groupes au lieu d’être mis à jour.
4. **Ne plus bloquer l’affichage sur des fetchs lents.** Le premier GRIB peut exécuter des appels externes synchrones dans la requête ; l’import automatique de la polaire fait un upload, un calcul et une écriture à chaque ouverture.

Ces quatre points ciblent les lags les plus plausibles sans changer l’expérience visuelle. Ils sont établis par lecture statique complète du simulateur, **pas** par mesure d’une session navigateur.

---

## Portée et méthode

- Périmètre lu : uniquement `/workspace/naviguide-simulator` (frontend, serveur, tests, styles, assets et configuration Vite).
- Technologies réellement utilisées : React 19, Leaflet, tuiles raster, WMS, SVG/HTML de `divIcon`, Canvas Leaflet pour les points.
- **Absent du graphe de rendu** : WebGL, shader, worker navigateur, `OffscreenCanvas`, modèle 3D, Three.js, deck.gl et MapLibre.
- Le simulateur ne contient donc pas de pipeline GPU applicatif à optimiser : le coût se répartit surtout entre DOM/Leaflet, géométrie JavaScript, tuiles réseau et calculs serveur.

## Carte du pipeline

```text
Données
  route.geojson | API route | horloge/polaire | météo/GRIB | couches/tuiles
        ↓
Chargement
  fetch navigateur, tuiles Leaflet, WMS, API FastAPI, cache local/session
        ↓
Décodage / préparation
  JSON → segments/points ; CSV → polaire ; météo → échantillons ;
  flattenRoute + buildVoyageClock + interpolation du playhead
        ↓
État
  App (état React central) + hooks Leaflet impératifs + refs de couche
        ↓
Layout
  projection Leaflet lat/lon → pixels ; positionnement des drapeaux ;
  deux sidebars CSS ; calcul de la barre film
        ↓
Paint / composite
  raster (fond, WMS, balisage) + SVG Leaflet (tracés) +
  Canvas Leaflet (points) + DOM/SVG divIcon (bateaux, GRIB, drapeaux) +
  UI React/CSS
```

### Chemins principaux

| Cas | Data → rendu |
|---|---|
| Ouverture | `App` charge d’abord `/route.geojson` via `loadOfficialBerryRoute`, convertit les entités en segments/escales, aplatit la route (`flattenRoute`), construit l’horloge (`buildVoyageClock`), puis initialise la carte Leaflet. |
| Repli route | Si le GeoJSON statique échoue à charger, `App` appelle `/route` (searoute) par lots de 4 jambes. Chaque lot met `segments` à jour et reconstruit la couche de tracé ; `sceneReady` la garde masquée jusqu’à la route complète. |
| Dessin libre | `handleDrawingClick` appelle `fetchDrawnSegment`, qui appelle `/route` pour chaque nouveau segment ; `useRouteLayer` affiche ce segment à son arrivée. |
| Lecture du film | `useRoutePlayback` fait évoluer `nm` via `requestAnimationFrame`, `interpolateCast` déduit bateau/avion/relais, puis les hooks de couche mettent à jour sillage, bateau, caméra et UI. |
| Mode suivi | `useOfficialExpedition` crée/lit l’horloge officielle, recalcule la position locale chaque seconde et charge le GRIB initial, puis toutes les 60 s. |
| Clic sur une route | `fetchSatellite` lance en parallèle trois POST (vent, vagues, courants), puis ouvre le panneau React central. |
| Couches optionnelles | `useToggleLayers` ajoute/enlève tuiles WMS/raster ou instancie des objets Leaflet depuis un GeoJSON chargé à la demande. |

---

## Où chaque élément est dessiné

| Famille visible | Où et comment | Travail synchrone / blocage probable | Chargement ou refetch |
|---|---|---|---|
| Fond clair/sombre | `useSimulatorMap`, `L.tileLayer` Esri | Décodage raster et composite navigateur ; bascule de thème remplace toute la couche | Tuiles à l’ouverture et après pan/zoom ; rechargement au changement de thème |
| Limites ZEE, bathymétrie, fonds, câbles | `useToggleLayers`, couches WMS Leaflet | Raster distant ; coût surtout réseau/décodage/composite | Une tuile par zone visible ; aucune politique de cache applicative explicite |
| Balisage | `useToggleLayers`, tuiles raster | Si une tuile échoue, la couche de secours est ajoutée sans retirer la couche initiale : deux sources peuvent dessiner/fetcher | Tuiles à chaque déplacement ; secours à la première erreur |
| Route officielle, repli et route tracée | Route officielle : `useWakeLayer` (partie parcourue/restante) ; dessin/personnalisée : `useRouteLayer`, `L.polyline` | Le groupe complet de dessin/personnalisé est supprimé puis recréé à un changement de route. La route officielle réutilise les polylignes de sillage (coût détaillé à la ligne suivante). | GeoJSON statique au démarrage ; repli searoute seulement si ce chargement échoue, états par lots mais tracé masqué jusqu’à la fin ; dessin tracé à chaque nouveau segment |
| Sillage accompli/restant | `useWakeLayer`, `L.polyline` | **À 12 Hz :** parcours complet des points, découpe, copies monde, conversion en `LatLng`, `setLatLngs` sur deux séries de lignes | Pas de fetch ; animation continue |
| Bateau, bateau live/fantôme/relais, bateau de dessin | `useCatamaranMarker`, `L.marker` + `divIcon` HTML/JPEG | À chaque position/cap : génération d’HTML + `L.divIcon` + `setIcon` sur les 3 copies monde ; le navigateur refait le DOM de l’icône | Pas de fetch hors données du mode |
| Avion | `usePlaneMarker`, `L.marker` + SVG inline | Même modèle `setIcon` à chaque tick pendant le transfert ; coût court mais réel | Pas de fetch |
| Drapeaux / points dessinés | Effet dans `App`, `L.marker` + `divIcon` HTML/PNG | Nouveau `L.layerGroup` et tous les marqueurs recréés après chaque recalcul d’offset | Recalcul offset sur `moveend`/`zoomend`, délai 120 ms |
| GRIB : barbules et disques de vagues | `useGribCorridorLayer` ; SVG dans `divIcon`, cercles Leaflet | Groupe entier détruit puis recréé au changement de cellule (pas de 0,05°), heure ou données. Jusqu’à 80 échantillons × 3 copies × deux primitives | GRIB forcé au premier affichage puis GET toutes les 60 s |
| Ports, projets, marinas, capitaineries, PoE | `useToggleLayers` + `addPointLayer` ; points Canvas Leaflet | Création d’un objet Leaflet + listener par entité ; pas de clustering ni filtrage viewport | GeoJSON complet, lazy une fois par montage |
| Catalogues scientifiques | `useToggleLayers` + `addScienceSourceLayer` ; Canvas pour points, SVG pour lignes | Filtrage et création de toutes les entités de la source ; pas de découpage spatial | Un gros GeoJSON partagé, lazy au premier toggle |
| AMP | `useToggleLayers`, `L.geoJSON` | À chaque `moveend`, réponse entière convertie en nouvelle couche GeoJSON ; requêtes non annulées ni dédupliquées | Débounce 420 ms, mais la caméra cinéma peut provoquer une série de `moveend` |
| Barre film, sidebars, modales, toast, popup de fiche, panneau satellite | React + Tailwind/CSS | Tous rediffés depuis `App` lors du tick film et du tick live ; layout léger individuellement, coûteux collectivement | Briefing personnalisé avec timeout ; panneau satellite au clic |
| Masque de chargement | React + `backdrop-blur-sm`, animation CSS | Composite potentiellement plus lourd mais seulement pendant le chargement | Conditionné par `sceneReady` |

### Ordre des calques Leaflet

`layerOrder.js` fixe : fond (200) → WMS (240–270) → route (380) → traces science (410) → AMP (420) → bateaux (620) → popup Leaflet (700). Les sidebars et panneaux React sont au-dessus (z-index 2000+). Cet ordre est clair et ne constitue pas lui-même un goulet.

---

## Goulots observables directement dans le code

### P0 — coût pendant chaque animation

1. **Calcul intégral des statistiques à chaque rendu.**  
   Dans `App`, `summarizeRoute(statsSegs)` est appelé directement dans le corps du composant. Il parcourt tous les segments et toutes leurs coordonnées, et exécute un calcul haversine pour chaque arête. Comme `playback.nm` change jusqu’à 12 fois/s, ce calcul revient sans que la route ait changé.

2. **Sillage O(n) à 12 Hz, puis ×3 copies monde.**  
   `useWakeLayer` appelle `remainingParts` et `wakeParts` à chaque changement de `sailNm`. Ces deux fonctions reparcourent l’itinéraire entier ; `worldCopyParts` triple ensuite les tableaux. Leaflet reçoit deux jeux complets de coordonnées. C’est probablement le premier frein sur itinéraire dense.

3. **Rendu React centralisé.**  
   `App` concentre état de carte, lecture, panneau, modales, couches, briefing et données. Chaque `setNm` de `useRoutePlayback` rediffuse aussi `Sidebar`, `ToolsSidebar` et `SimulationFilmBar`. L’absence de `React.memo`, de sous-arbre de lecture isolé ou de store sélectif rend la fréquence d’animation contagieuse.

4. **Icônes mobiles remplacées plutôt que transformées.**  
   `CatamaranMarker.jsx` et `PlaneMarker.jsx` recréent une icône Leaflet et appellent `setIcon` à chaque déplacement. La rotation pourrait être appliquée au nœud DOM déjà créé ; la position resterait `setLatLng`.

### P1 — reconstructions Leaflet évitables

5. **GRIB recréé au fil du déplacement.**  
   `useGribCorridorLayer` enlève le groupe courant avant de créer cercles et `divIcon` à nouveau. La granularité de cellule (0,05°) implique un renouvellement fréquent, particulièrement en lecture accélérée.

6. **Drapeaux recréés après les mouvements caméra.**  
   `useMarkerOffsets` écoute `moveend` et `zoomend`, recalcule un placement anti-chevauchement, puis l’effet de `App` recrée le groupe complet. En mode cinéma, `useFilmCamera` exécute un `setView` animé au plus toutes les 700 ms : il peut alimenter cette boucle.

7. **AMP sensible à la caméra animée.**  
   L’effet AMP lance un fetch après 420 ms sur chaque `moveend`, sans `AbortController`, clé de requête, cache bbox ou protection contre les réponses arrivées dans le désordre. Quand la caméra suit le bateau, ce n’est plus une action utilisateur ponctuelle.

8. **Repli de route : calcul progressif, pas de tracé visible progressif.**  
   Dans `App`, chaque lot reçu met à jour `segments`, mais `routeReady` reste faux jusqu’au dernier lot et `sceneReady` masque `useRouteLayer` et `useWakeLayer`. Il n’y a donc pas de flash de polylignes intermédiaires ; il reste des re-rendus et un parcours searoute complet.

### P1 — délai de disponibilité des données

9. **GRIB forcé dans le chemin critique.**  
   `useOfficialExpedition` appelle `refreshGrib({ force: true })` au premier échantillon disponible. Côté serveur, `refresh_official_grib` appelle synchroniquement `maybe_refresh_official`, qui appelle `fetch_latest_payload`. Cette dernière boucle les points du couloir et fait pour chacun un appel vent puis un appel vagues, séquentiellement.

10. **Les fetchs météo ponctuels ouvrent un dataset distant pour chaque clic.**  
    Les handlers `get_wind`, `get_wave`, `get_current` de `server/main.py` sont synchrones et appellent chacun `copernicusmarine.open_dataset` sans cache de cellule. FastAPI les exécute hors event loop dans le pool de threads : ils ne bloquent pas le thread principal du navigateur, mais ils peuvent saturer les workers, retarder les réponses et cumuler sur les trois requêtes du clic.

11. **Polaire par défaut retraitée à chaque ouverture.**  
    `ToolsSidebar.loadDefaultPolars` télécharge le CSV puis appelle systématiquement l’upload. `polar_api._serialize_polar` génère une grille 181×61, sérialise et écrit un JSON disque, même si la même polaire est déjà présente. Le client n’a besoin que des données brutes et du résumé.

12. **Point d’entrée “ports” sans budget d’entités.**  
    `/proxy/ports` construit et renvoie toutes les entités de l’index mondial ; le client les transforme toutes en objets Leaflet à l’activation. Le nombre réel d’entités n’est pas mesuré ici, mais l’algorithme est linéaire et sans cluster ni filtre bbox.

### P2 — comportement qui mérite correction/mesure

13. **Le briefing “ici” peut réarmer son debounce à chaque tick.**  
    `useIciDossier` dépend de `boat.lat/lon`. Tant qu’aucune requête n’a fini, un déplacement continu peut annuler le timeout de 800 ms et le recréer. À vitesse normale/rapide, cela peut retarder la requête jusqu’à une pause, tout en créant du churn d’effets.

14. **Horloge live à 1 Hz dans la racine React.**  
    `useOfficialExpedition` appelle `setNowMs` chaque seconde et reconstruit `live`. C’est raisonnable isolément, mais cela s’ajoute au rendu global et ne devrait pas forcer les panneaux immobiles.

15. **Deux ressources image semblent inexistantes.**  
    La liste `public/` ne contient que les deux SVG, le GeoJSON et le CSV, alors que `index.html` référence `favicon-n-bl.png` et `Sidebar.jsx` référence `/logo-naviguide.png`. Cela implique vraisemblablement deux 404 évitables au chargement et un logo absent. Les PNG de drapeaux et le JPEG bateau sont importés par Vite, donc suivent un autre chemin.

---

## Recommandations priorisées

| Priorité | Action précise | Fichiers / symboles | Impact | Effort | Risque |
|---|---|---|---|---|---|
| P0 | Mémoïser `statsSegs` et `summarizeRoute`; mémoïser aussi les totaux de `ToolsSidebar`. | `App.jsx` (`statsSegs`, `stats`), `ToolsSidebar.jsx` | Évite une traversée complète de route à chaque frame | Faible | Très faible |
| P0 | Isoler le playhead animé dans un sous-arbre carte/film mémorisé ; ne publier vers React que les valeurs HUD nécessaires à cadence limitée. | `useRoutePlayback.js`, `App.jsx`, nouveau contrôleur de scène | Réduit le re-render massif à 12 Hz | Moyen | Moyen : préserver scrubbing/stop |
| P0 | Mettre à jour le sillage avec un curseur d’index et des polylignes persistantes ; plafonner la cadence visuelle si nécessaire (p. ex. 6–8 Hz). | `useWakeLayer.js`, `filmWake.js` | Réduit allocations JS et updates Leaflet pendant le film | Moyen | Moyen : transitions/hops/antiméridien |
| P0 | Servir la polaire par défaut pré-calculée, ou lire son résumé avant upload ; mettre en cache par hash de fichier. | `ToolsSidebar.jsx` (`loadDefaultPolars`), `polar_api.py` (`_serialize_polar`, `upload_polar`) | Accélère chaque ouverture, évite CPU et I/O serveur répétés | Moyen | Faible |
| P1 | Réutiliser les marqueurs GRIB : indexer par clé position/temps, faire `setLatLng` et modifier le DOM/SVG existant ; élargir la cellule ou throttle. | `useGribCorridorLayer.js`, `gribSymbols.js` | Supprime les vagues de création DOM/Leaflet | Moyen | Moyen |
| P1 | Conserver le groupe de drapeaux et patcher les positions/HTML au lieu de le détruire; ne recalculer les offsets que quand le zoom change ou lors d’un arrêt caméra. | `App.jsx` (effet drapeaux), `useMarkerOffsets.js` | Fluidifie le mode cinéma et le pan | Moyen | Faible à moyen |
| P1 | Coalescer/annuler les requêtes AMP par bbox quantifiée et dernière requête gagnante; ignorer le suivi caméra ou augmenter le debounce en cinéma. | `useToggleLayers.js` (effet AMP), `useFilmCamera.js` | Réduit réseau, parsing JSON et reconstruction géométrique | Moyen | Faible |
| P1 | Passer le GRIB à un état `pending` immédiat et réaliser la mise à jour hors chemin GET; partager la tâche en cours entre visiteurs. | `voyage_api.py` (`get_official_grib`, `refresh_official_grib`, `_kick_official_grib`), `grib_fetch.py` | Réduit le temps au premier affichage et les requêtes doublons | Moyen | Moyen : protocole de statut |
| P1 | Paralléliser avec limite les appels vent/vagues du couloir, ou réduire le nombre de points quand l’écran ne peut pas les distinguer. | `grib_fetch.py` (`fetch_latest_payload`) | Réduit la latence réseau GRIB | Moyen | Faible |
| P1 | Cacher les réponses vent/vague/courant par cellule et TTL court; fournir un endpoint composite pour le popup. | `server/main.py` (`get_wind`, `get_wave`, `get_current`), `App.jsx` (`fetchSatellite`) | Réduit triple latence et pression sur le pool de threads | Moyen | Faible |
| P1 | Pour les gros jeux de points, renvoyer seulement la bbox/tuile visible et ajouter clustering ou canvas agrégé. | `useToggleLayers.js` (`addPointLayer`, `addScienceSourceLayer`), endpoint `/proxy/ports` | Évite des milliers d’objets/handlers invisibles | Élevé | Moyen |
| P2 | Mettre `lastScheduled`/position échantillonnée dans une ref, puis déclencher `useIciDossier` à fréquence bornée. | `useIciDossier.js` | Stabilise briefing et supprime le churn de debounce | Faible | Faible |
| P2 | Garder le `divIcon` et tourner son enfant avec CSS; n’appeler `setIcon` que si l’asset/classe change. | `CatamaranMarker.jsx`, `PlaneMarker.jsx` | Diminue le churn DOM des mobiles | Moyen | Faible |
| P2 | Remplacer les deux URLs PNG manquantes par les assets réellement disponibles ou fournir les PNG. | `index.html`, `Sidebar.jsx`, `public/` | Supprime 404 et défaut visuel | Faible | Très faible |
| P2 | Mettre des en-têtes de cache et, si nécessaire, un cache proxy pour les tuiles WMS. Passer proprement au secours balisage au lieu de superposer deux sources. | `server/main.py` (`proxy_zee_wms`, `proxy_seamark`), `useToggleLayers.js` | Réduit rechargements lors de pan/zoom | Moyen | Faible |

## Quick wins (premier lot)

1. `useMemo` autour de `summarizeRoute` dans `App`.
2. `React.memo` pour `Sidebar`, `ToolsSidebar` et `SimulationFilmBar`, après stabilisation des props/callbacks.
3. Mémoïser les compteurs `maritimeSegs`, `overlandSegs`, `totalPoints` de `ToolsSidebar`.
4. Réparer les URLs d’icônes absentes.
5. Ajouter annulation + séquence de requête à l’AMP et au panneau météo.
6. Ne pas lancer `refreshGrib({ force: true })` lorsqu’un GRIB frais est déjà en cache.
7. Basculer le fallback balisage au lieu de laisser les deux tile layers actifs.
8. Limiter l’update du sillage/position à une cadence visuelle mesurée plutôt qu’à toute variation calculée.

## Suivi d’implémentation — P0 à P2

### Implémenté — P0

- [x] Les segments de statistiques et `summarizeRoute` sont mémorisés dans `App`; les compteurs de `ToolsSidebar` le sont également.
- [x] `Sidebar`, `ToolsSidebar` et `SimulationFilmBar` sont mémorisés; les props stables des panneaux sont stabilisées et le HUD de la sidebar est publié au plus à 4 Hz.
- [x] Le calcul de lecture reste au `requestAnimationFrame`, mais sa publication visuelle est plafonnée à 8 Hz.
- [x] Le sillage garde désormais ses polylignes Leaflet : la route restante est construite une fois, les sommets franchis sont ajoutés avec un curseur et seul le court segment terminal est mis à jour à chaque rafraîchissement.
- [x] La polaire par défaut déjà calculée est relue depuis un endpoint client sans la grille complète; l’upload ne sert plus qu’au premier démarrage sans cache.
- [x] Les deux URLs PNG inexistantes ont été remplacées par le SVG NAVIGUIDE disponible.
- [x] Les requêtes AMP et le panneau météo ont une annulation et un identifiant de séquence : seule la dernière réponse peut modifier l’interface.
- [x] Le premier GRIB utilise le GET cache-aware au lieu de forcer un rafraîchissement; le fallback de balisage retire la couche distante avant d’ajouter le proxy.

### Implémenté — P1

- [x] Le groupe GRIB et ses primitives Leaflet sont conservés ; les entrées sont indexées par maille (et slot de stencil), leurs coordonnées, styles et SVG sont patchés sans reconstruire le groupe.
- [x] Le groupe des drapeaux est persistant ; les marqueurs existants reçoivent position, contenu HTML et données d’interaction à jour. Le placement anti-chevauchement ne se recalcule plus au fil de la caméra, seulement après son arrêt ou un zoom.
- [x] Les requêtes AMP utilisent une bbox quantifiée, un cache local borné, une annulation et un identifiant de dernière requête ; elles sont suspendues pendant le suivi cinéma.
- [x] Les GET GRIB ne font plus de fetch Open-Meteo : ils retournent le cache et l’état `pending` si une tâche partagée est en cours. Le rafraîchissement est dédupliqué par voyage.
- [x] Les requêtes vent et vagues du couloir GRIB sont exécutées en parallèle, avec une limite globale de huit requêtes.
- [x] Vent, vagues et courants sont cachés cinq minutes par cellule de 0,25° ; `POST /weather` agrège les trois produits, en parallèle, pour un seul aller-retour depuis le popup.
- [x] Les ports sont demandés au proxy avec une bbox quantifiée et un cache borné client/serveur ; les catalogues de points et sources scientifiques ne construisent que les entités visibles dans le viewport Canvas.

### Implémenté — P2

- [x] `useIciDossier` mémorise la position planifiée et borne la programmation à une fois toutes les huit secondes : le debounce n’est plus annulé par les ticks du playhead.
- [x] Les `divIcon` bateau et avion ne sont plus recréés à chaque position/cap ; seule la rotation CSS de leur enfant est mise à jour.
- [x] Les proxys WMS ZEE et tuiles Seamark envoient désormais des en-têtes `Cache-Control`.

### Chantiers structurants — état

- [x] Le contrôleur impératif `MapScene` sort les hooks Leaflet et le playhead de `App`. La scène possède les calques mobiles (route, sillage, bateaux, avion, sauts aériens, drapeaux), applique leur cycle `add / update / remove` et ne publie vers React qu’un instantané HUD borné à 4 Hz.
- [ ] Des catalogues spatiaux complets (tuiles vectorielles, index serveur pour chaque source, clustering hiérarchique) restent à dimensionner si les données excèdent encore le budget visible.
- [ ] Un pipeline météo asynchrone partagé complet (statut durable et cache par cycle généralisé à tous les fournisseurs) reste à concevoir ; seul le GRIB officiel est dédupliqué ici.
- [ ] Le Web Worker reste conditionné à un profilage runtime démontrant du calcul JavaScript significatif.

## Chantiers structurants

- **Contrôleur `MapScene` impératif — fait** : `App` ne possède plus de hook Leaflet ni de boucle `requestAnimationFrame`. `MapSceneController` garde les objets Leaflet vivants, et `ScenePlaybackController` les met à jour sans re-rendu global.
- **Rendu spatial des catalogues — reste** : API bbox ou tuiles vectorielles, clustering, niveau de détail lié au zoom et bornage du nombre de features affichées.
- **Pipeline météo asynchrone partagé** : tâche de rafraîchissement dédupliquée, cache serveur par cellule/cycle, réponse immédiate avec état, actualisation client à faible cadence.
- **Web Worker seulement après mesure** : candidat pour `flattenRoute`, `buildVoyageClock`, calcul des offsets et pré-calcul de sillage sur route dense. Un worker ne réduit pas le coût de peinture Leaflet ni de DOM ; il ne doit pas être le premier changement.

---

## Ce qui est déjà favorable à la fluidité

- La route officielle est un GeoJSON statique chargé avant le coûteux repli searoute.
- Les points de cartes utilisent Canvas Leaflet, pas un `divIcon` par point.
- Plusieurs données sont déjà lazy et certaines caches serveur existent : routes (64 entrées), GRIB récent, cube de prévision (12 h), catalogue ICI (1 h), ports (24 h), profondeur (6 h).
- Le GRIB public est plafonné à 80 échantillons, et le couloir est borné géographiquement.
- La caméra est déjà limitée à une mise à jour toutes les 700 ms en suivi normal.
- `useWakeLayer` réutilise les polylignes existantes : l’optimisation à faire porte surtout sur les tableaux complets qui lui sont fournis à chaque tick.

## Ce qui n’a pas été vérifié

- Aucun profilage runtime n’a été lancé : pas de FPS, long tasks, usage mémoire, waterfall, taille des bundles, taille réelle des GeoJSON ni temps de réponse des fournisseurs externes.
- Les impacts sont donc classés en **évidents par structure de code** (boucles à chaque tick, destructions de groupes, appels synchrones) et non en millisecondes mesurées.
- Il faut confirmer les priorités avec Chrome Performance (lecture normale/rapide, caméra cinéma, GRIB actif, gros calques actifs), puis Network (démarrage, GRIB, WMS, popup météo).
- Le comportement réel des caches HTTP dépend des en-têtes du serveur de déploiement et des fournisseurs ; aucune configuration de cache navigateur/CDN n’est visible dans le dossier du simulateur.
- La génération de prévision dans `forecast_cube.py` n’est pas un chemin chaud dans l’UI actuelle : `App` appelle `useVirtualVessel` avec `forecast: false`. Elle mérite une mesure uniquement si cette option est réactivée.

## Séquence de validation recommandée après implémentation

1. Capturer une trace Performance de 20 s en lecture normale, puis rapide, avec la caméra cinéma.
2. Comparer le nombre de re-renders de `App`, les long tasks, le FPS et les appels `setLatLngs` avant/après.
3. Activer séparément GRIB, AMP, ports et un catalogue scientifique ; mesurer nombre d’objets Leaflet, mémoire et requêtes après pan.
4. Mesurer TTFB et durée totale du premier GRIB, puis un rafraîchissement à chaud.
5. Tester visuellement les passages antiméridien, le sillage, les deux transferts aériens et la réactivité du scrub.

# Plan complémentaire en lots — revue visuelle du 19–20 septembre 2026

Version **1.0** — 20 septembre 2026. Suite du [plan en lots](PLAN_LOTS_AGENT_SIMULATEUR.md)
(lots P → K, tous **mergés sur `main`** le 20 sept.). Ce document découpe la
**revue visuelle complète du porteur** (soir du 19, matin du 20) en lots
**recettables visuellement**, écrits pour un worker Cursor **Grok 4.6 Extra
High Fast (256 k de contexte)** : chaque lot tient dans une fenêtre, cite
ses fichiers et ses lignes, et se recette en cinq minutes.

## 0. Règles pour le worker (à coller dans chaque brief)

- Lire **d'abord** `docs/PLAN_LOTS_AGENT_SIMULATEUR.md` § 0 (règles qui ne se
  discutent pas : `main` plancher de l'UI, aucun chiffre par un LLM, pas de
  Tavily / Nemotron / Nebius avant le lot L, recette = tests + captures).
- **Budget de contexte** : ne jamais lire `src/App.jsx` (1 620 lignes) ni
  `src/map/MapSceneController.js` (880 lignes) en entier — toujours par
  extraits `rg -n "motif" fichier` puis `Read` avec `offset`/`limit`.
  Chaque lot ci-dessous liste **les seuls fichiers à ouvrir**.
- Lancer : `cd naviguide-simulator && bash dev-mac.sh` (API :8010 + Vite
  :5174). Tests : `npm test`, `.venv/bin/python -m pytest -q`,
  `npx vite build`, `npm run e2e` (fumée Playwright).
- Une branche par lot depuis `main` à jour, une PR, **pas de merge** ; la
  description = objectif, cause racine, ce qui change, tests, recette
  (captures fixes).
- Si deux lots doivent se suivre, le brief le dit ; sinon ils sont indépendants
  et peuvent partir en parallèle sur des fichiers différents.

## 1. Ce que la revue a montré (causes racines déjà identifiées)

| Observation du porteur | Cause racine (vérifiée dans le code) | Lot |
|---|---|---|
| Crédits carte : « Esri » deux fois, « Garmin » sans raison visible, pas de lien sur « OpenStreetMap contributors » | `src/layers/styles.js:12` `TILE_ATTRIBUTION = 'Tiles © <a>Esri</a> — Esri, HERE, Garmin, OpenStreetMap contributors'` : la mention légale Esri (fournisseurs HERE, Garmin, OSM) est collée après le lien Esri, sans liens | M |
| Citations du briefing pas toujours liées, redites | `src/engine/iciBriefing.js` : `sourceSentence` cite des noms de sources sans URL ; « Polaire chargée » et la climatologie apparaissent à deux endroits | M |
| Le chat « journal de bord » bouge avec la taille du sac `ici` | `src/components/Sidebar.jsx` : le chat est rendu **après** les blocs à hauteur variable (carte NOW, briefing, récit) | N |
| Deux boutons son dans la barre (Écouter + 🔊 du replay) ; boutons de mode et Revoir dispersés | `src/components/SimulationFilmBar.jsx` : `ListenButton` en haut, `replay-voice` en bas, commutateur Suivre / Simulation à droite | O |
| Vitesse « 11,9 kn » à quai (chat et barre) | `server/voyage_clock.py:379` et `src/engine/voyageClock.js:486` : à quai, l'échantillon recopie le sommet d'arrivée (`{**a, atQuay: True}`) dont `speedKnots` = vitesse de la jambe | P2 |
| Replay : saccades, dézoom / rezoom | `src/map/MapSceneController.js:124` `zoomForRemaining(remainingNm)` — le zoom cible change à chaque jambe (courtes jambes des Antilles → zoom 6–7, Atlantique → 3) ; `setView` animé toutes les 700 ms sur un bateau qui avance de ~200 nm/s | Q |
| Récit qui commence au jour 12 | le replay démarre avant que `GET /voyage/official/journal` (60 entrées + `events`) soit arrivé : les premiers paragraphes se calculent tard | Q |
| « Puis, puis, puis… », pas de tronçon terrestre, pas d'événements marquants ni de spots à terre | `src/engine/expeditionStory.js` : connecteur unique `Puis, le …`, départ raconté depuis Saint-Maur sans le tronçon route, seuls ZEE / AMP / PoE / wx sont racontés | R |
| Route dessinée Brisbane → San Francisco qui monte au détroit de Béring et traverse l'Alaska | le client envoie la longitude **dépliée** du 2ᵉ point (236,84° = −123,16° + 360) ; `server/route_engine.py:571` la passe telle quelle à `searoute` qui attend [−180, 180] | S |
| « Les couches Blue Intelligence n'ont pas répondu, seules les ZEE et les ports WPI sont conservés » après Terminer | même longitude dépliée envoyée à `GET /ici` (→ 400 « lon hors limites ») et aux couches BI ; à vérifier aussi : carte FREE périmée (« Port Bourgenay 15,1 nm » alors que le bateau est au large de la Mauritanie) = la boucle FREE rejoue des cartes d'un sac ancien | T |
| Zoom difficile, lenteurs | à profiler (lot U) : 36 drapeaux × 3 copies-monde recalculés à chaque `zoomend`, WMS ZEE, effets `moveend` | U |
| Chat : la vitesse ne varie pas | même cause que P2 (vitesse de l'horloge, pas la vitesse du moment) ; le contexte du chat ne reçoit pas la vitesse mesurée | P2 |

## 2. Les lots

Taille : S ≤ ½ jour, M ≤ 2 jours. Ordre conseillé : **P2 → M → N → O → S → T → Q → R → U**. P2, M, N, O, S sont indépendants ; T après S ; R après Q.

### Lot P2 — Vitesse réelle, zéro à quai (S)

**Objectif.** Un bateau à quai a une vitesse de 0 ; en mer, la vitesse citée est celle du moment (GRIB × polaire), pas celle de la jambe planifiée.

**Fichiers à ouvrir.** `server/voyage_clock.py` (l. 360–400), `src/engine/voyageClock.js` (l. 458–512), `server/logbook_chat.py` (`build_context`, l. 60–150), `src/App.jsx` **par extrait** : `rg -n "chatContextRef.current = " src/App.jsx` (≈ l. 520–535) et `rg -n "boatKnots|liveKnots" src/App.jsx`.

**Étapes.** 1) Dans les deux échantillonneurs, la branche « à quai » renvoie `speedKnots: 0` (et `"vehicle": "quay"`). 2) Le contexte du chat porte `official.speedKnots` = 0 à quai, sinon la vitesse **mesurée** que le client envoie (`context.boat.speedKnots` = `expeditionSpeed.live` en Suivre) avec `basis: "measured"`, et la vitesse planifiée à part (`plannedKnots`). 3) La barre film affiche « à quai » à la place de « 11.9 kt » quand `atQuay`.

**Tests.** Python : `test_voyage_clock.py` (échantillon à quai → 0) ; JS : `voyageClock.test.js` idem ; `test_logbook_chat.py` : contexte à quai → `speedKnots: 0`.

**Recette.** Suivre, bateau à Nouméa : ligne d'horloge « … · à quai » ; chat : « À quelle vitesse va le bateau ? » → « à quai, 0 kn ». Simulation en mer : la vitesse varie avec le vent.

### Lot M — Crédits carte et citations (S)

**Objectif.** Une seule mention Esri, les fournisseurs nommés une fois avec un lien chacun, OpenStreetMap lié ; dans le briefing, chaque source citée est un lien et rien n'est dit deux fois.

**Fichiers.** `src/layers/styles.js` (l. 12), `src/engine/iciBriefing.js` (`sourceSentence`, `legSentence`, `climatologySentence` — `rg -n "function sourceSentence|function legSentence|Polaire chargée" src/engine/iciBriefing.js`), `src/engine/briefingLinks.js` (`entityLinks`), tests `iciBriefing.test.js`.

**Étapes.** 1) `TILE_ATTRIBUTION` = `Tuiles © <a href=esri>Esri</a> · données Esri, <a href=here>HERE</a>, <a href=garmin>Garmin</a>, © <a href=osm copyright>OpenStreetMap contributors</a>` (Garmin et HERE sont des fournisseurs des fonds Esri : la mention est **obligatoire** dans les conditions Esri — on la garde, liée, en une fois). 2) `sourceSentence` : table source → URL (Open-Meteo, RTOFS/NOAA, EMODnet, GEBCO, CMEMS/Copernicus, MarineRegions/VLIZ, OSM, douane.gouv.fr, CDSE) et rendu par `segmentBriefing` en liens. 3) Dédoublonner : « Polaire chargée » une seule fois (dans la ligne d'étape), la climatologie une seule fois (bandeau ou briefing, pas les deux).

**Recette.** Bas de carte : « Tuiles © Esri · données Esri, HERE, Garmin, © OpenStreetMap contributors », quatre liens cliquables. Briefing à La Rochelle : chaque nom de source souligné cliquable ; « Polaire chargée » une fois.

### Lot N — Panneau gauche stable (S)

**Objectif.** Le chat en haut du panneau gauche ; les blocs à contenu variable (carte « À bord, maintenant », sac `ici`, récit) ont une **hauteur fixe** avec défilement interne : rien ne saute quand le sac change.

**Fichiers.** `src/components/Sidebar.jsx` (ordre des blocs l. 275–360), `src/components/LogbookChat.jsx`, `src/components/MomentCards.jsx` (variante `inline`), `src/index.css` (règles `.light-mode` à conserver).

**Étapes.** 1) Ordre : Berry card → **chat** (hauteur fixe 168 px, historique défilant) → étape (`SimulationPanel`) → carte NOW (`max-h-40`, défilement) → FREE → fiche d'escale → sac `ici` (`h-64`, défilement, placeholder « Le sac se remplit… » à la même hauteur) → récit (`h-56`, défilement) → journal. 2) Les hauteurs sont des constantes CSS (`--sim-box-h-*`) pour un réglage unique. 3) Mode clair : mêmes règles.

**Recette.** Suivre, lecture : le champ du chat ne bouge pas quand une carte apparaît ou que le briefing change ; le sac et le récit défilent dans leur cadre. Capture sombre + claire.

### Lot O — Barre film compacte, un seul bouton son (S)

**Objectif.** Une seule rangée de commandes : **Masquer la barre · Écouter · Suivre l'expédition · Simulation · Revoir l'expédition**, puis les commandes de lecture compactes ; un seul bouton son.

**Fichiers.** `src/components/SimulationFilmBar.jsx` (rangée du haut l. 110–160, rangée du bas l. 226–330), `src/components/ListenButton.jsx`, `src/hooks/useReplay.js` (`voice`), `src/App.jsx` **par extrait** : `rg -n "replayControls|speechText=" src/App.jsx`.

**Étapes.** 1) Supprimer le 🔊 du replay : `replay.voice` suit l'état du bouton **Écouter** (un `ListenButton` qui, pendant un replay, lit le paragraphe courant ; hors replay, le récit + briefing comme aujourd'hui). 2) Rangée unique à gauche : Masquer la barre (Cinéma seulement) · Écouter · [Suivre l'expédition | Simulation] · Revoir ; à droite : lecture / pause, prochaine escale, Stop auto, vitesses (pilules plus petites, `text-[9px]`). 3) Les tests de contrat (`useReplay.test.js`, `filmBarLayout.test.js`) suivent.

**Recette.** Suivre et Simulation : une rangée, aucun bouton en double ; la barre fait au plus deux lignes de texte + une rangée de commandes. Capture.

### Lot S — Route dessinée transpacifique (S)

**Objectif.** Brisbane → San Francisco tracé à la main donne une route directe dans le Pacifique, sans détour par Béring ni traversée de l'Alaska.

**Cause racine.** Longitude dépliée (236,84°) envoyée à `GET /route` puis à `searoute`, qui attend [−180, 180].

**Fichiers.** `src/hooks/useRouteDrawing.js` (`fetchSegment`), `server/main.py` (`get_route`, l. 230–250), `server/route_engine.py` (`searoute_with_exact_end`, l. 546–620), `server/tests/test_route_engine.py`.

**Étapes.** 1) Serveur : `get_route` **replie** `start_lon` / `end_lon` dans [−180, 180] avant `searoute_with_exact_end`, et la réponse est **redépliée** pour que la ligne suive le point de départ (pas de saut de 360° entre deux sommets — réutiliser `_normalize_antimeridian`). 2) Client : `fetchSegment` replie aussi (ceinture et bretelles) et redéplie le résultat relativement au point précédent. 3) Fixture : Brisbane (−27,0 ; 153,4) → San Francisco (37,7 ; −122,4) : aucun sommet au nord de 50° N, aucun sur terre, longueur < 7 500 nm.

**Recette.** Tracer votre propre route : point à l'est de l'Australie, point à San Francisco → trait vert direct dans le Pacifique, « 6 4xx nm ». Capture.

### Lot T — Sac `ici()` et cartes pour la route dessinée (S)

**Objectif.** Après « Terminer », le briefing raconte le sac autour du bateau de la route dessinée (ZEE, ports, AMP, science…) ; aucune carte ne cite un lieu à plus de 60 nm.

**Fichiers.** `src/hooks/useIciDossier.js` (construction de l'URL `/ici` — `rg -n "q.set\(" src/hooks/useIciDossier.js`), `src/hooks/useIciAlong.js` (échantillonnage des perles de la route courante), `src/engine/momentCard.js` (boucle FREE, l. 320–330 et 485–530), tests correspondants.

**Étapes.** 1) Replier `lon` dans toute requête `/ici`, `/weather/forecast`, `/api/climatology/point` (utilitaire `wrapLon` dans `src/utils/geo.js`). 2) Perles de la route dessinée : vérifier que `useIciAlong` échantillonne la **route courante** (`customRoute`) et non l'officielle ; sinon corriger la source. 3) Boucle FREE : une carte dont l'entité est à plus de `FREE_STALE_NM` (60 nm) du bateau sort de la boucle. 4) Message « seules ZEE et WPI conservés » : ne le montrer que si BI a vraiment échoué (`sources.bi === "unavailable"`), pas pour une perle thin.

**Recette.** Route dessinée au large de la Mauritanie : briefing avec la ZEE mauritanienne et les ports WPI proches ; aucune carte « Port Bourgenay ». Capture.

### Lot Q — Replay fluide, récit prêt au départ, narration qui dure le replay (M)

**Objectif.** « Revoir l'expédition » est agréable à regarder : zoom stable, mouvement continu, récit prêt dès le départ, et la **narration dure exactement le temps du replay**.

**Fichiers.** `src/map/MapSceneController.js` (`syncCamera` l. 780–830, `zoomForRemaining` l. 124), `src/hooks/useReplay.js`, `src/hooks/useReplayVoice.js`, `src/engine/replay.js`, `src/App.jsx` **par extrait** : `rg -n "replay\." src/App.jsx`.

**Étapes.** 1) Caméra de replay : quand `live.replay`, zoom **fixe** (4, ou celui qui montre la jambe entière : `fitBounds` de la jambe au changement de jambe seulement), `panTo` sans animation à 20 Hz, jamais `flyTo`, pas de `zoomForRemaining`. 2) Départ : `start()` attend que `journal` et `storyParagraphs` soient prêts (état « Préparation du récit… » ≤ 2 s ; sinon on part quand même après 3 s) ; le premier paragraphe est lu à t0. 3) Rythme : la narration mène. Pour chaque jambe, on estime la durée de lecture (mots × 60 / 160) ; la vitesse du replay sur la jambe = jambe / durée ; à la fin de la voix (`onEnd`), on passe à la jambe suivante. Sans voix (bouton coupé), 1 jour/s comme aujourd'hui. 4) Le texte lu est **le récit du sac du moment** (celui du panneau gauche à Nouméa), paragraphe par paragraphe, cartes du journal en parallèle.

**Tests.** `replay.test.js` : plan de rythme (durée par jambe, vitesse), `MapSceneMarkers.test.js` : pas de `flyTo` pendant le replay (contrat).

**Recette.** Suivre → Revoir : zoom constant, mouvement fluide, la voix commence par « L'expédition Berry-Mappemonde a quitté Saint-Maur… » dès le départ, le bateau arrive au live quand la voix se tait. Deux captures (mi-parcours, fin).

### Lot R — Récit de la traversée : moins mécanique, plus d'événements (M)

**Objectif.** Un récit qui se lit : connecteurs variés, le tronçon terrestre raconté, les événements marquants (coups de vent, changements de climatologie, escales et ce qu'on y voit, fiches science croisées), et — en option — une rédaction par la cascade LLM habituelle, sans jamais un chiffre nouveau.

**Fichiers.** `src/engine/expeditionStory.js` (+ test), `server/voyage_journal.py` (`record_route_events`), `server/ici_warm.py` (`route_events_from_pearls`), `server/escale_api.py` (cache des fiches : tourisme), nouveau `server/story_expedition.py` (rédaction en cache, ns `kv` « expedition-story »).

**Étapes.** 1) Connecteurs : rotation (« Puis », « Le 27 mai », « Trois jours plus tard », « Cap ensuite sur ») — jamais deux fois le même d'affilée ; test. 2) Départ : « L'expédition a quitté Saint-Maur le 15 mai 2026 par la route (122 nm) et a pris la mer à La Rochelle le même jour. » 3) Événements : `kind: sci` (fiche science ≤ 5 nm d'une perle riche, une fois) et `kind: climo` (changement de mois d'atlas avec rose différente) ajoutés au journal par les perles ; escales : « À Ajaccio, 3 jours à quai — Palais Fesch, maison Bonaparte » depuis la fiche d'escale en cache (section tourisme, 2 lieux au plus). 4) Rédaction optionnelle : `GET /voyage/official/story?lang=fr` renvoie le texte brut (ci-dessus) **et** une version rédigée par la cascade (NIM → OpenRouter → Claude), régénérée quand le journal change (au plus 1×/jour), filtrée par le même filtre de chiffres que le chat ; le client offre « brut / rédigé » (brut par défaut). 5) Longueur : la version lue en replay (lot Q) est celle affichée.

**Recette.** Suivre, récit à Nouméa : pas de « Puis » deux fois de suite ; première phrase avec la route et La Rochelle ; jambe Ajaccio → Fort-de-France avec au moins un événement météo ou science ; escale Ajaccio avec un lieu remarquable. Capture brut + rédigé.

### Lot U — Zoom réactif (M)

**Objectif.** Le zoom à la molette répond immédiatement ; aucune tâche > 50 ms pendant un zoom.

**Fichiers.** `src/map/MapSceneController.js` (`syncWaypoints` l. 586–670, `onMoveEnd`, `syncDynamicWorldCopies`), `src/hooks/useMarkerOffsets.js`, `src/layers/useToggleLayers.js` (WMS ZEE), `docs/PROFIL_BUILD_PROD_2026-09-19.md` (méthode).

**Étapes.** 1) Profiler un zoom (Chrome Performance, 10 s de molette) sur le build de prod ; noter les trois postes. 2) Mesures probables : copies-monde des drapeaux seulement si la vue touche ±180° ; `setIcon` sauté quand la clé d'icône n'a pas changé (déjà) mais **pas de recalcul d'offsets pendant l'animation de zoom** (`zoomanim` → attendre `zoomend` + 250 ms) ; `preferCanvas: true` pour les polylignes ; réutiliser les `divIcon` ; ne pas relancer `/ici` ni le récit sur `moveend`. 3) Re-profiler, consigner dans `docs/`.

**Recette.** Zoom molette sur l'Atlantique : fluide ; profil avant / après joint à la PR.

### Lot L (rappel, plus tard) — Nemotron via Nebius + Tavily : l'objet du hackathon

Corrigé dans le plan en lots : **Nemotron (raisonnement long, via la plateforme Nebius, 60 $ de crédit) + Tavily** (veille datée par escale, juge de vérité des récits). Pas avant que M → U soient recettés ; spécification à écrire à ce moment-là.

### Reste hors de ce plan

G3 (conseil de route en Suivre, préalable : brouillon d'équipage), second découpage d'`App.jsx` (`useSceneWiring`) si le fichier redevient un frein, CSP nginx bloquante après lecture des rapports.

## 3. Brief type pour un worker Grok 4.6 Extra High Fast

```text
Contexte : lis docs/PLAN_LOTS_AGENT_SIMULATEUR.md § 0 puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le lot <X> (texte intégral).
Fichiers : ouvre SEULEMENT ceux listés dans le lot ; App.jsx et MapSceneController.js par `rg -n` + Read avec offset/limit.
Branche : feat/lot-<x>-<slug> depuis main à jour. Une PR sur main, pas de merge.
Tests : npm test, .venv/bin/python -m pytest -q, npx vite build ; npm run e2e si la barre film ou les panneaux changent.
Recette : les étapes « Recette » du lot, captures fixes dans la PR (pas de vidéo).
Interdits : retirer une surface visible sur main ; un chiffre produit par un LLM ; Tavily / Nemotron / Nebius.
Modèle : cursor-grok-4.6-xhigh-fast (jamais claude-* sur un worker Cloud).
```

# Plan — Corrections de la revue du 23 septembre (matin) : lots RD1 → RD8

Version **1.0** — 23 septembre 2026. Le porteur a recetté dans Chrome le batch
RB1 → RC5 (PR #269 → #302, 28 PR ouvertes, pile linéaire). Il n'a pas fait de
revue PR par PR (« tu considères que la revue du bot vaut pour la revue PR par
PR ») : il a coché 8 items sur 98 (R8c #279, R9a #281, RC3 #298) et livré une
**revue globale de l'application**, très mécontente. Ce plan transforme cette
revue — et les 14 KO du réviseur de nuit (bot) — en lots correctifs RD1 → RD8 (RD8 ajouté le 24 sept. : couches en tuiles),
à enchaîner par `infra/agents/run_lots.py`.

**Prérequis.** Les lots RD partent de `main` **après merge de la pile
#269 → #302** (merger la PR de tête #302 suffit, pile linéaire — la décision
de merger reste au porteur). Les ancres `fichier:ligne` ci-dessous sont lues
sur la tête de pile (`fix/lot-rc5-film-ecran`, PR #302) : ce sera l'état de
`main` après merge. Quand un constat existe déjà sur `main` d'avant-pile,
c'est dit explicitement.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4).
- **Ne rien faire qui n'est pas demandé** (REGLES § 1) — c'est le reproche
  central de la revue : « Ne fais pas des choses que je ne demande pas. Si je
  les demande pas, c'est que je les veux pas. » L'encadré jaune des couloirs,
  les carrés verts des lignes d'escales, l'ouverture du panneau gauche au clic
  sur la carte : autant de surfaces **jamais demandées**, à retirer — pas à
  améliorer.
- **Rien de superflu à l'écran** : un onglet qui n'affiche rien (Récit vide en
  Simulation) est un bouton qui ne marche pas ; il se remplit ou il n'existe
  pas sur cet écran.
- **Aucun chiffre produit par un LLM** ; le récit du film puise dans les faits
  du journal des moments, champ inconnu = silence, jamais une phrase de
  remplissage.
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF. Plus **Revoir l'expédition** en Suivre : priorité.

## 1. Revue par PR (cases du porteur, verdict du réviseur de nuit)

Le porteur n'a pas relu PR par PR : le verdict PR par PR est celui du bot
(14 KO sur 28 PR), assumé par le porteur. Cochés porteur : 8.

| PR | Lot | Porteur | Bot (réviseur de nuit) | Suite |
|---|---|---|---|---|
| #269 | RB1 | — | rien vu de KO (chorégraphie et jambe mer : captures OK) | recette au prochain batch |
| #270 | RB2 | — (mais « citations blanches » en revue globale) | rien vu de KO | → RD2 |
| #271 | RB3 | — | rien vu de KO | — |
| #272 | RB4 | — | rien vu de KO | — |
| #273 | RB5 | — | 2 items non vérifiables (audio) ; texte OK | — |
| #274 | RB6 | — | 1 non vérifiable (audio) | — |
| #275 | RB7 | — | **2 KO** : pas de « arrivée entre le … et le … », sonde `eta` → `members: 0` | → RD4 |
| #276 | RB8 | — (mais « clic route mort » en revue globale) | 2 non vérifiables | → RD1 |
| #277 | R8a | — | rien vu de KO | — |
| #278 | R8b | — | rien vu de KO | — |
| #279 | R8c | **3 / 5 cochés** | rien vu de KO | clic drapeau → RD1 |
| #281 | R9a | **3 / 3 cochés** | rien vu de KO | — |
| #284 | R9b | — | **1 KO** : liste Journal présente mais **0 entrée** (voyage officiel absent du poste) | → RD4, RD6 |
| #285 | R9c | — | **2 KO** : saut d'escale (pas d'arrivée à La Rochelle) ; bulle titrée « Escale · 15 mai » au lieu du nom | paires corrigées par RC4/RC5 (le porteur entend les paires) ; contenu → RD7 ; moments absents → RD4 |
| #286 | R10a | — | rien vu de KO | — |
| #287 | R10b | — | rien vu de KO | — |
| #289 | R10c | — | rien vu de KO | — |
| #290 | R10d | — | **1 KO** : bouton toujours « Recalculer l'itinéraire », pas « Demander conseil » | § 3 : le libellé « Demander conseil » **est** dans la pile (`src/i18n/fr.js:508`, rendu `SimulationPanel.jsx:202`) ; le KO correspond au libellé de `main` — build du poste pas à jour. À re-vérifier en recette, pas de lot. |
| #291 | N1 | — | rien vu de KO | — |
| #292 | N2 | — | rien vu de KO | — |
| #293 | N3 | — | **1 KO** : pas de jambe Ajaccio → Fort-de-France ni « couloirs : Gibraltar » (plan-review 404 sur le poste) ; et le porteur : encadré jaune jamais demandé | → RD3 (encadré), RD4 (404) |
| #294 | N4 | — | rien vu de KO | — |
| #295 | D0 | — | rien vu de KO | — |
| #296 | RC1 | — | 1 non vérifiable (`/voyage/official` 404 sur le poste) | → RD4 |
| #297 | RC2 | — | rien vu de KO | — |
| #298 | RC3 | **2 / 2 cochés** | rien vu de KO | — |
| #299 | RC4 | — | **1 KO** : sous-titre encore sans paires | corrigé par RC5 (tête de pile) ; le porteur entend les paires — vérifier en recette |
| #302 | RC5 | — | **7 KO** : 502 `/bi/climatology/*` (×5, poste/VPS) ; film fini à ~121 s au lieu de 150 ; « Leopard 46 » aussi dans Paramètres avancés | 502 = environnement du poste (§ 3) ; durée → RD7 ; nom du bateau → RD3 |

## 2. Revue générale (la voix du porteur, point par point)

1. **Au rechargement, on tombe en Simulation.** `App.jsx:169` :
   `useState(VIEW_SIMULATION)` (identique sur `main` d'avant-pile — pas une
   régression de la pile, mais le porteur le refuse). → **RD5**.
2. **Le clic sur la route ne marche plus ; seul Saint-Pierre-et-Miquelon
   répond ; le pop-up Copernicus (Vent / Vagues / Courants) ne s'ouvre pas ;
   seuls les points colorés sont sélectionnables ; le trait bleu ne l'est
   plus.** Deux causes lues : (a) `MapScene.jsx:159-173` — le clic carte teste
   `pointToSegmentPx(...) < 16` avec les longitudes **de base** de
   `segment.coords`, alors que RB8 dessine la route aussi sur les copies du
   monde (lng ± 360) : tout clic sur une copie échoue (`pointToSegmentPx`,
   `MapScene.jsx:11-28`, ne normalise pas Δlongitude) ; (b) les marqueurs
   d'escale intercepteurs (`MapSceneController.js:843-850`,
   `stopPropagation`) routent vers `openEscaleFromUi`. → **RD1**.
3. **Cliquer près d'un drapeau (ou sur un point de la branche
   Halifax ↔ Saint-Pierre) ouvre le panneau gauche — jamais demandé.**
   `App.jsx:855-859` : `openEscaleFromUi` fait `setSidebarOpen(true)` ;
   câblé au clic marqueur (`App.jsx:1557`) et aux lignes d'escales
   (`App.jsx:1655`). → **RD1**.
4. **Des carrés verts dans les lignes des escales — inconnus, jamais
   demandés ; le clic ouvre aussi le panneau gauche.** Ce sont les boutons
   `▤` `escale-sheet-open` (`EscaleLegend.jsx:34-44`, teinte émeraude),
   branchés sur `openEscaleFromUi`. → **RD1** (retrait).
5. **Les citations (crédits carte) sont devenues blanches / sur fond blanc ;
   elles doivent avoir le fond de carte derrière elles.** Lu dans le code :
   en **mode clair**, la bande des crédits est blanc opaque
   (`index.css:28-31`, `rgba(255,255,255,0.8)`, préexistant) et RB2 a ajouté
   un zoom blanc en mode clair (bloc `.light-mode .leaflet-control-zoom`,
   diff `index.css` de la pile) ; sur les captures de la pile, la bande
   sombre n'est plus discernable derrière les crédits. → **RD2** (reproduire
   dans les deux thèmes, rétablir une bande translucide discrète — jamais un
   aplat blanc).
6. **Encadré jaune dans le panneau droit (Bay of Biscay, Gibraltar, Western
   Med, North Atlantic Main, Caribbean West, Coral Lane, Indian Ocean West,
   Malacca, Torres commercial, Cape Approaches) — jamais demandé.**
   `ToolsSidebar.jsx:13-27` (`viewRouteAntiShipping` agrège tous les couloirs
   de toutes les jambes) et rendu `ToolsSidebar.jsx:397-407` (badge
   `route-anti-shipping`, bordure ambre). Le lot N3 ne demandait que la
   pastille **par jambe** dans la Revue du plan (`PlanReview.jsx:135-141`,
   conforme). → **RD3** (retrait du badge agrégé).
7. **Tracer ma route : le point se pose à côté du clic, on ne vise pas.**
   `MapSceneController.js:806-807` (déjà sur `main` :796-797) : le rond
   dessiné fait 10 px (14 avec bordure) posé au coin haut-gauche d'une icône
   24×24 ancrée `[12,12]` → il s'affiche ~5 px au-dessus/à gauche du vrai
   lat/lon. → **RD2**.
8. **L'encadré gauche « Récit / Journal » : Récit toujours vide, trois
   onglets mal faits, un grand espace.** `App.jsx:813-814` :
   `storyParagraphs` renvoie `[]` hors Suivre ou sans horloge officielle ;
   `Sidebar.jsx:472` : le slot `story` n'est rendu que `isSuivre &&
   !isDrawing`. L'app démarrant en Simulation, l'onglet Récit y est un espace
   vide. → **RD6** (onglet qui se remplit ou n'existe pas) et **RD4** (sans
   voyage officiel en base, l'horloge manque aussi en Suivre).
9. **Le récit du film est pourri : « Le ciel reste haut. La mer porte le
   bateau. La route tient le cap. Le vent reste le vent », répété à chaque
   jambe.** `film_script.py:39` (tuple `ATMOS`), injecté en `:1215` (pool) et
   `:1338` (pad), plus `:1599` (« La mer reste la mer… »). Le porteur veut un
   récit qui **exploite les vraies données** : marinas croisées, aires
   marines protégées, stations scientifiques, traces historiques de cyclones,
   richesse culturelle des escales — tout ce qui tombe dans Récit / Journal.
   → **RD7**.
10. **Nouvelle tactique demandée pour la durée du film : les options (2 min 30
    / 3 min) deviennent décochables et AUCUNE n'est cochée par défaut ; sans
    durée cochée, le film raconte à peu près tout le produit du panneau
    gauche (Récit + Journal), cohérent, et prend le temps que ça prend.**
    `SimulationFilmBar.jsx:458-470` (options `[150, 180]`),
    `useReplay.js:177` (défaut `FILM_TARGET_SECONDS`). → **RD7**.
11. **La date de départ n'est plus réglable ; en Simulation ça part « 15 mai
    08:00 UTC », sans année ; la date de Revoir l'expédition doit être
    réglable (2025 possible), distincte de la Simulation.** Le champ « Date
    de départ » existe encore en Simulation (`ToolsSidebar.jsx:421-425`,
    `showDeparture={isSimulation}` `App.jsx:1658`, câblé `voyage.t0`
    `:1659`), mais il est enfoui sous la Revue du plan et le badge couloirs ;
    l'horloge de la barre film n'affiche pas l'année ; aucun réglage
    n'existe pour la date de départ du replay. → **RD5**.
12. **Le journal, c'est bien (cyclones, haute mer, marina, aire marine
    protégée), mais il faut savoir à chaque fois LESQUELS.** Le serveur
    passe les noms (`moment_journal.py:223` : `_change("amp", SCORE_AMP,
    name, fact)`) ; l'affichage client n'en montre pas toujours le nom.
    → **RD6**.
13. **Le toggle du panneau gauche doit être à la même hauteur que celui du
    panneau droit** (le zoom n'est plus en haut à gauche depuis RB2).
    `Sidebar.jsx:327-331` : fermé, le toggle gauche est à `top-[92px]` ; le
    toggle droit est à `top-4` (`ToolsSidebar.jsx`, bouton chevron).
    → **RD2**.
14. **Régression : la remise du chiffre au profil (34 → 29 → ↺ → 34) ne
    marche plus** (réparée par R1, recassée). Mécanisme lu :
    `SkipperOrdersPanel.jsx:76-79` (`handleReset`), `:106`
    (`disabled={!forced}`), `resetNumberToProfile` `:69-73` ; **le diff de la
    pile ne touche ni ce composant ni le hook des ordres** — la cause est à
    reproduire puis à chercher dans le forçage (`forced`) et le câblage
    `onSkipperExpert={skipper.setExpert}` (`App.jsx:1666`). → **RD3**.
15. **« À la limite, la Revue du plan pourrait être un onglet du panneau
    gauche. »** Décision notée, pas tranchée par le porteur (« à la
    limite ») : aucun lot — voir § 3.

## 3. Ce qui est reporté ou fondu, et pourquoi

- **Globe (lots G2 et G5, à venir)** : les corrections de clics et de
  précision valent aussi pour la vue globe — fondues dans leurs prompts
  (« Constat de la revue du 23 sept. ») pour que le globe ne reproduise pas
  les bugs : G5 (clic route → pop-up Copernicus, clic drapeau n'ouvre jamais
  un panneau) ; G2 (marqueur de point ancré exactement sur le lat/lon).
- **« Demander conseil » (KO bot #290)** : le libellé est déjà dans la pile
  (`src/i18n/fr.js:508`, rendu `SimulationPanel.jsx:202`) ; le KO du bot
  correspond au libellé de `main` — build du poste pas rechargé. À
  re-vérifier à la recette du batch RD ; pas de lot.
- **502 `/bi/climatology/*` et `ERR_CONNECTION_CLOSED` (KO bot #302)** :
  environnement du poste de recette / VPS (l'atlas BI ne répondait pas), pas
  un défaut du code du simulateur. Noté pour le porteur : relancer la recette
  avec l'atlas joignable ; si le 502 revient en prod, c'est un ticket infra,
  pas un lot simulateur.
- **Revue du plan en onglet du panneau gauche** : suggestion du porteur au
  conditionnel. Décision **notée, non exécutée** — à confirmer par le porteur
  avant d'ouvrir un lot (déplacement de surface : REGLES § 1, on ne déplace
  pas sans demande ferme).
- **Ordre du récit (saut de La Rochelle, KO bot #285/#299)** : corrigé par
  RC4 + RC5 (tête de pile) ; la revue du porteur **entend les paires**
  (« Départ vers La Rochelle. Arrivée à La Rochelle… ») ; simple vérification
  en recette, pas de nouveau lot. Le **contenu** du récit, lui, va dans RD7.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour App.jsx et MapSceneController.js). « Recette » = ce que le
porteur voit dans Chrome, par écran. Ancres `fichier:ligne` = tête de pile
#302 (= `main` après merge). Pile linéaire RD1 → RD8.

### RD1 — Le clic sur la carte fait ce qu'il dit : route → pop-up Copernicus, jamais le panneau gauche (M)

Cause racine : (a) `src/map/MapScene.jsx:159-173` — le clic carte ne
reconnaît la route que si `pointToSegmentPx(map, lat, lon, segment.coords)
< 16` ; `pointToSegmentPx` (`MapScene.jsx:11-28`) compare des longitudes non
normalisées, donc tout clic sur une **copie du monde** (route RB8 à ±360°)
échoue — d'où « le seul endroit cliquable, c'est Saint-Pierre-et-Miquelon »
(copie de base). (b) `src/App.jsx:855-859` — `openEscaleFromUi` fait
`setSidebarOpen(true)` : chaque clic sur un marqueur d'escale
(`MapSceneController.js:843-850`, `onWaypointClick` → `App.jsx:1557`) ou sur
le bouton `▤` des lignes d'escales (`EscaleLegend.jsx:34-44`,
`onEscaleSheet` → `App.jsx:1655`) **ouvre le panneau gauche** — jamais
demandé.

Fichiers : `src/map/MapScene.jsx`, `src/App.jsx` PAR EXTRAIT
(`rg -n "openEscaleFromUi|onWaypointClick|onEscaleSheet|setSidebarOpen"`),
`src/components/EscaleLegend.jsx`, `src/utils/geo.js` (`wrapLon`), tests
associés (`EscaleLegend`, `MapScene` s'il existe, sinon test utilitaire).

Étapes :
1. `pointToSegmentPx` : normaliser l'écart de longitude modulo 360 (ramener
   le clic et les sommets dans la même copie, p. ex. via `wrapLon` ou en
   minimisant |Δlng|) — le clic sur la route répond sur **toutes** les copies
   du monde et à **tous** les zooms ; le seuil reste 16 px.
2. Le clic sur la route (trait coloré **et** trait bleu de base, hors jambes
   avion) ouvre le **pop-up Copernicus** (onglets Vent / Vagues / Courants)
   — comportement `handleMapRouteClick` existant, rien d'autre.
3. `openEscaleFromUi` n'ouvre **plus** le panneau gauche : retirer
   `setSidebarOpen(true)`. Le clic sur un drapeau charge la fiche d'escale
   dans la section Ici de l'encadré **si le panneau est déjà ouvert** ;
   panneau fermé → le clic ne déclenche rien de visible (aucune ouverture
   automatique).
4. Retirer le bouton `▤` (`escale-sheet-open`) des lignes d'escales — les
   carrés verts jamais demandés ; la ligne d'escale garde son clic existant
   (déplacer le curseur du film).
5. Tests : clic simulé à lng +360 d'un segment → `onRouteClick` appelé ;
   `openEscaleFromUi` n'appelle jamais `setSidebarOpen` ; `EscaleLegend` ne
   rend plus `escale-sheet-open`.

Recette (visuelle) :
- Suivre, carte monde, puis carte tirée d'un tour complet vers la droite :
  un clic sur la route (n'importe où, trait bleu compris) ouvre la carte
  satellite **Vent / Vagues / Courants** — des deux côtés du monde, à tous
  les zooms.
- Suivre : cliquer sur un drapeau ou près d'un drapeau **n'ouvre pas** le
  panneau gauche ; panneau ouvert, le même clic remplit la section Ici.
- Panneau gauche, liste des escales : **plus aucun carré vert** dans les
  lignes ; cliquer une ligne déplace le curseur comme avant.

### RD2 — Habillage carte : crédits sur le fond de carte, toggle gauche aligné, point de tracé sous la souris (S)

Cause racine : crédits — en mode clair la bande est blanc opaque
(`src/index.css:28-31`, `rgba(255,255,255,0.8)`, préexistant sur `main`) et
le zoom RB2 ajoute un second bloc blanc à côté (`index.css`, bloc
`.light-mode .leaflet-control-zoom`) ; le porteur veut « le fond de carte
derrière eux ». Toggle — `src/components/Sidebar.jsx:327-331` : fermé, le
toggle gauche est à `top-[92px]` alors que le toggle droit est à `top-4`
(`ToolsSidebar.jsx`, bouton chevron) ; la raison historique (zoom en haut à
gauche) a disparu avec RB2. Point de tracé —
`src/map/MapSceneController.js:806-807` (main :796-797) : rond html 10 px
(14 avec bordure) au coin haut-gauche d'une icône `iconSize [24,24]` ancrée
`[12,12]` → rendu ~5 px au-dessus/à gauche du lat/lon cliqué : « on n'arrive
pas à viser ».

Fichiers : `src/index.css`, `src/components/Sidebar.jsx`,
`src/map/MapSceneController.js` PAR EXTRAIT (`rg -n "10px;height:10px|iconAnchor"`),
tests associés.

Étapes :
1. Reproduire dans Chrome (thème sombre puis clair) l'état des crédits ;
   remplacer tout aplat blanc (attribution et zoom en mode clair) par la même
   bande translucide discrète que le mode sombre — le fond de carte reste
   visible derrière ; ne pas toucher au contenu des crédits (« Esri » une
   fois, REGLES § 1).
2. Toggle gauche fermé à `top-4`, même hauteur que le toggle droit, panneaux
   ouverts ou fermés.
3. Centrer le rond de tracé : le pixel cliqué est le **centre** du rond
   (icône 14×14 ancrée [7,7], ou marge centrant le rond dans 24×24) ; même
   correction pour le premier point (vert) et les suivants (blancs).
4. Tests : montage — l'icône du point dessiné a `iconAnchor` au centre exact
   du rond ; un instantané CSS/e2e vérifie l'alignement des deux toggles.

Recette (visuelle) :
- Tous écrans carte, thème sombre puis clair : les crédits et le zoom se
  lisent **sur le fond de carte**, sans bande blanche opaque.
- Panneaux fermés : les deux chevrons (gauche et droit) sont à la **même
  hauteur**.
- Tracer ma route, zoom moyen puis fort : le point se pose **exactement sous
  la croix**, on vise un cap précis sans décalage.

### RD3 — Panneau droit : encadré jaune retiré, nom du bateau une fois, remise du chiffre au profil réparée (S)

Cause racine : encadré jaune — `src/components/ToolsSidebar.jsx:13-27`
(`viewRouteAntiShipping` agrège les couloirs de **toutes** les jambes) et
rendu `:397-407` (badge `route-anti-shipping`, bordure ambre, « Bay of
Biscay · Gibraltar · … ») — jamais demandé : le lot N3 prévoyait la pastille
**par jambe** dans la Revue du plan (`PlanReview.jsx:135-141`, conforme, à
garder). Nom du bateau — `src/components/SkipperOrdersPanel.jsx:192` : la
rangée « Bateau » répète le nom du polar (« Leopard 46 ») déjà affiché sous
Polaires (KO bot #302 ; REGLES § 1 : un libellé n'apparaît qu'une fois).
Remise du chiffre — mécanisme `SkipperOrdersPanel.jsx:69-79` + `:106`
(`disabled={!forced}`) ; **le diff de la pile ne touche ni le composant ni
le hook des ordres** : cause à établir sur poste (forçage `forced` jamais
posé ? câblage `onSkipperExpert={skipper.setExpert}`, `App.jsx:1666` ?) —
ne pas coder à l'aveugle, reproduire d'abord.

Fichiers : `src/components/ToolsSidebar.jsx`,
`src/components/SkipperOrdersPanel.jsx`, `src/components/PlanReview.jsx`
(lecture : la pastille par jambe reste), `src/App.jsx` PAR EXTRAIT
(`rg -n "skipper|setExpert"`), tests associés.

Étapes :
1. Supprimer le badge agrégé `route-anti-shipping` et
   `viewRouteAntiShipping` ; la pastille « couloirs : X » **par jambe** de la
   Revue du plan reste telle quelle.
2. Retirer la rangée « Bateau : <nom> » de Paramètres avancés ; le nom du
   bateau ne se lit que sous Polaires ; longueur / tirant d'eau restent.
3. Reproduire la panne de la remise au profil (34 → 29 → ↺) ; corriger la
   cause constatée ; ajouter le test de non-régression (forcer une valeur →
   `forced` vrai → ↺ actif → retour à la valeur du profil), pour chaque champ
   numérique.
4. Tests : `ToolsSidebar` ne rend plus `route-anti-shipping` ;
   `SkipperOrdersPanel` n'affiche le nom du bateau nulle part ; cycle
   remise-au-profil vert.

Recette (visuelle) :
- Panneau droit : **plus d'encadré jaune** listant les couloirs ; dans Revue
  du plan, chaque jambe garde sa ligne « couloirs : … » quand elle en croise.
- Paramètres avancés : le nom du bateau n'apparaît **plus** ; il reste
  visible sous Polaires, une seule fois à l'écran.
- Paramètres avancés : changer un chiffre (34 → 29) → la flèche ↺ s'allume ;
  cliquer ↺ → **le chiffre du profil revient** (34).

### RD4 — Le voyage officiel existe dès le démarrage du serveur : fourchette, journal, moments, film (M)

Cause racine : `server/voyage_api.py:699-707` — `_kick_official_eta` (comme
les warms moments / film / hindcast) **abandonne** si
`load_voyage(OFFICIAL_VOYAGE_ID)` est `None` ; or le voyage officiel n'est
créé que par l'endpoint client `ensure_official`
(`voyage_api.py:766`, PUT) ; le démarrage serveur (`server/main.py:84-97`)
préchauffe le GRIB et « ici » mais **ne sème pas le voyage**. Sur un poste
frais : `GET /voyage/official` → 404 (constaté par le bot), ensemble ETA
`members: 0` (KO #275, pas de « arrivée entre le … et le … »), journal à
**0 entrée** (KO #284), film en repli sans bulles d'approche (KO #285),
Récit vide même en Suivre (l'horloge officielle manque).

Fichiers : `server/voyage_api.py` PAR EXTRAIT
(`rg -n "_kick_official|ensure_official|OFFICIAL_VOYAGE_ID"`),
`server/main.py`, `server/ensemble_eta.py` (lecture),
`server/tests/test_voyage_api.py`, `server/tests/test_ensemble_eta.py`
s'il existe.

Étapes :
1. Au démarrage du serveur : si le voyage officiel n'est pas en base, le
   créer côté serveur avec le même corps que `ensure_official` (itinéraire
   Berry embarqué) — sans dépendre d'un client ni d'une clé.
2. Enchaîner alors les préchauffages existants (`_kick_official_hindcast`,
   `_kick_official_eta`, `_kick_official_moments`,
   `_kick_official_film_story`), en tâche de fond, sans bloquer le démarrage.
3. `GET /voyage/official` ne renvoie plus jamais 404 sur un poste frais ;
   l'ensemble ETA a `members > 0` quelques minutes après le lancement ; les
   moments du journal se remplissent.
4. Tests (pytest, store vide en fixture) : après startup, le voyage officiel
   existe ; `_kick_official_eta` ne renvoie plus False pour cause de voyage
   absent ; aucun appel réseau dans les tests (fixtures).

Recette (visuelle) :
- Poste relancé de zéro (script de recette) : Suivre s'ouvre sur le voyage,
  la liste des escales affiche sous la prochaine escale « **arrivée entre
  le … et le …** » (deux dates proches) au plus quelques minutes après le
  lancement, sans recharger.
- Panneau gauche, onglet Journal : des lignes du 15 mai à aujourd'hui —
  **jamais une liste vide**.
- Suivre → Revoir l'expédition : le film démarre tout de suite, bulles
  comprises.

### RD5 — Démarrage en Suivre ; dates réglables, avec l'année (S)

Cause racine : `src/App.jsx:169` — `useState(VIEW_SIMULATION)` : l'app
s'ouvre en Simulation (identique sur `main` d'avant-pile ; le porteur veut
l'expédition d'abord). Date de Simulation : le champ existe
(`ToolsSidebar.jsx:421-425`, `showDeparture={isSimulation}`
`App.jsx:1658`, câblé `voyage.t0` `:1659`) mais il est enfoui sous la Revue
du plan (et le badge couloirs, retiré par RD3) — le porteur ne le trouve
plus ; l'horloge de la barre film affiche « 15 mai 08:00 UTC » **sans
année**. Revoir l'expédition : aucun réglage de date de départ n'existe —
le film officiel part du 15 mai 2026 (RB5, voulu par défaut), mais le
porteur veut pouvoir **simuler un départ décalé** (« on pourrait partir en
2025 »), réglage **distinct** de la Simulation.

Fichiers : `src/App.jsx` PAR EXTRAIT (`rg -n "VIEW_SIMULATION|view, setView|showDeparture"`),
`src/components/ToolsSidebar.jsx`, `src/components/DepartureField.jsx`,
`src/components/SimulationFilmBar.jsx` PAR EXTRAIT (ligne d'horloge,
`rg -n "UTC"`), `src/hooks/useReplay.js` PAR EXTRAIT (paramètres envoyés au
film), `src/i18n/fr.js`, `src/i18n/en.js`, tests associés.

Étapes :
1. La vue initiale au chargement est **Suivre** (`VIEW_SUIVRE`) ; Simulation
   et Tracer restent à un clic.
2. Remonter « Date de départ » au-dessus de la Revue du plan dans le panneau
   droit (Simulation) ; vérifier qu'éditer la date change bien l'horloge de
   la simulation (départ affiché, positions recalculées).
3. L'horloge de la barre film affiche **l'année** (« 15 mai 2026 · 08:00
   UTC ») dans tous les modes.
4. En Suivre, à côté de « Revoir l'expédition » : la date de départ du
   replay est réglable (même gabarit que le champ de Simulation), **défaut
   15 mai 2026** — la régler décale les dates déclamées et affichées du
   film ; indépendante du t0 de la Simulation ; aucune date inventée : tout
   dérive de la date choisie et des durées réelles des jambes.
5. Tests : la vue initiale est Suivre ; le champ de replay décale les dates
   du script (test JS sur le paramètre envoyé + test py si le serveur reçoit
   la date) ; l'année est présente dans le libellé d'horloge.

Recette (visuelle) :
- Recharger l'application → on arrive sur **Suivre l'expédition**.
- Simulation, panneau droit : « Date de départ » **visible sans dérouler**,
  la changer déplace le départ (la barre film suit) ; l'horloge de la barre
  affiche **l'année**.
- Suivre : régler la date de Revoir sur 2025 → le film déclame « … a quitté
  Saint-Maur le 15 mai 2025 » ; remettre le défaut → 2026 ; le t0 de la
  Simulation n'a pas bougé.

### RD6 — L'encadré gauche tient parole : Récit jamais vide, journal qui nomme, sans trou (S, après RD4)

Cause racine : `src/App.jsx:813-814` — `storyParagraphs` renvoie `[]` si
`!isSuivre || !officialClock` ; `src/components/Sidebar.jsx:472` — le slot
`story` n'est rendu que `isSuivre && !isDrawing` : en Simulation (vue par
défaut avant RD5) l'onglet **Récit** de l'encadré (`IciMaintenant.jsx:260-263`,
slot `ici-story-slot`) affiche un espace vide — « Récit est toujours vide »,
« il y a un espace ». Journal : le serveur nomme les événements
(`server/moment_journal.py:223` passe `name` pour une AMP), mais des lignes
s'affichent sans le nom (« Aire marine protégée » sec, capture #284) — « il
faudrait qu'on sache à chaque fois ce sont lesquels ».

Fichiers : `src/components/IciMaintenant.jsx`, `src/components/Sidebar.jsx`
PAR EXTRAIT (`rg -n "story=|journal="`), `src/App.jsx` PAR EXTRAIT
(`rg -n "storyParagraphs"`), `src/hooks/useMomentJournal.js`,
`server/moment_journal.py` (lecture : les noms existent), tests associés.

Étapes :
1. Un onglet ne mène jamais à du vide (REGLES § 1) : en Simulation et en
   Tracer, l'onglet Récit **n'apparaît pas** (Maintenant · Journal
   seulement) ; en Suivre il apparaît et se remplit (avec RD4, l'horloge
   officielle est toujours là).
2. Chaque ligne du Journal nomme son événement : « Aire marine protégée —
   <nom> », « Cyclone — <nom> (<année>) », « Marina — <nom> », « Ports
   d'entrée : <nom> » (déjà nommé) ; le nom vient du fait serveur, jamais
   inventé ; ligne sans nom en base → le type seul, comme aujourd'hui.
3. Resserrer l'espace entre les onglets et le contenu (le « trou » vu par le
   porteur) : pas de slot réservé vide sous Maintenant · Récit · Journal.
4. Tests : en Simulation l'onglet Récit n'est pas rendu ; en Suivre avec
   horloge, `story-paragraph` non vide ; une entrée AMP avec nom en fixture
   → la ligne du journal contient le nom.

Recette (visuelle) :
- Simulation, panneau gauche : les onglets sont **Maintenant · Journal** —
  aucun onglet Récit vide, aucun espace mort sous les onglets.
- Suivre, panneau gauche, onglet Récit : des paragraphes du voyage dès
  l'ouverture.
- Onglet Journal : chaque ligne dit **lequel** (« Aire marine protégée —
  Iroise », pas « Aire marine protégée » sec).

### RD7 — Le film déclame les vraies données du journal ; durée libre par défaut (M, après RD4)

Cause racine : `server/film_script.py:39` — le tuple `ATMOS` (« Le ciel
reste haut. », « La mer porte le bateau. », « La route tient le cap. », « Le
vent reste le vent. ») meuble chaque jambe via le pool `:1215` et le pad
`:1338`, plus `:1599` (« La mer reste la mer… ») : exactement les phrases
que le porteur récite pour s'en moquer. Les vraies données (marinas, AMP,
stations, cyclones datés, fiches d'escale) sont dans les moments
(`server/moment_journal.py`) mais le script ne les déclame pas quand la
sélection sous budget de 2 min 30 les écarte — et la durée est figée :
`SimulationFilmBar.jsx:458-470` (deux options 150 / 180 s, toujours l'une
active), `useReplay.js:177` (défaut `FILM_TARGET_SECONDS`). KO bot #302 :
le film s'arrête à ~121 s au lieu de 150 (le budget coupe avant la fin).

Fichiers : `server/film_script.py`, `server/tests/test_film_script.py`,
`src/components/SimulationFilmBar.jsx` PAR EXTRAIT
(`rg -n "filmDuration|targetSeconds"`), `src/hooks/useReplay.js`,
`src/hooks/useReplay.test.js`, `src/i18n/fr.js`, `src/i18n/en.js`.

Étapes :
1. Supprimer `ATMOS` et tous les pads de remplissage : une jambe sans fait
   notable est racontée plus court (départ, arrivée, distance) — la voix ne
   meuble jamais.
2. Les deux durées (2 min 30, 3 min) deviennent **décochables** (re-clic =
   décoché) et **aucune n'est cochée par défaut**. Durée cochée → le budget
   s'applique comme aujourd'hui et va **jusqu'au bout** (corrige les ~121 s
   du KO #302). Aucune durée cochée → pas de budget : le film raconte tout
   ce que portent Récit et Journal, et prend le temps que ça prend.
3. Sans budget, le script déroule le journal des moments dans l'ordre de la
   route (paires départ/arrivée conservées, RC4/RC5) : le bateau passe à
   côté de telle **marina**, part de tel **port**, traverse telle **aire
   marine protégée**, passe au large de telles **stations scientifiques**,
   croise la **trace historique de tel cyclone** (nom + année), arrive à
   telle escale **riche en culture** (faits de la fiche d'escale). Chaque
   fait est nommé ; les chiffres passent par `filter_numbers` ; champ
   inconnu = silence, jamais une phrase gabarit.
4. La voix arrondit les distances déclamées (« 1 820 milles nautiques »,
   jamais de décimale ni d'unité abrégée) — l'affichage écrit garde « nm ».
5. Tests : le script officiel ne contient plus aucune phrase d'`ATMOS` ni de
   pad ; fixture de moments riches → chaque type (marina, AMP, station,
   cyclone, escale) cité au moins une fois sans budget ; avec budget 150 s,
   la durée jouée atteint la cible ; aucune décimale dans les distances
   déclamées.

Recette (visuelle) :
- Suivre, barre film : les pilules **2:30** et **3:00** sont **décochées**
  par défaut ; cliquer coche, recliquer décoche.
- Revoir l'expédition sans durée cochée : le récit **nomme** des marinas,
  des aires marines protégées, des stations, des cyclones (nom et année) et
  la culture des escales — et on n'entend **plus jamais** « La mer porte le
  bateau », « Le ciel reste haut », « Le vent reste le vent ».
- Revoir avec 2:30 coché : le film tient environ 2 min 30, jusqu'au bout.

### RD8 — Couches climatologie en tuiles : la zone visible, au détail natif (M, indépendant)

Demande du porteur (24 sept.) : « un lot qui résout le poids de wind.geojson
grâce à des tuiles ». Constat (mesuré le 24 sept.) : le front charge
`wind.geojson?month=m&spacing_deg=4` — **1,6 Mo** pour le vent (0,5 Mo
courants), le globe entier à chaque changement de mois, et la couche reste
**grossière partout** (un point tous les 4°, ~440 km, même au zoom maximum)
alors que l'atlas est à 1° (43 205 cellules ; sans décimation le fichier fait
26 Mo et sort du VPS en 18 s). Des tuiles règlent les deux : on ne charge que
ce qu'on regarde, au détail natif quand on zoome.

Cause racine : `backend/app/routers/climatology.py:180-207` — trois routes
`/climatology/{kind}.geojson` globales, seule décimation `spacing_deg` ;
`backend/app/services/climatology_wind.py:214-262` (`wind_geojson`, idem
`wave_geojson`, `current_geojson`) — parcours de toute la grille
`lats × lons`, rose des vents complète (`directions_from`) sur chaque point ;
`naviguide-simulator/src/layers/useClimatologyLayer.js:102,124,146` — trois
`fetchJson(atlasLayerUrl(kind, m, { spacing_deg: "4" }))` sur le monde entier ;
`src/utils/atlasPoint.js:60` (`atlasLayerUrl`).

Fichiers (backend BI) : `backend/app/routers/climatology.py`,
`backend/app/services/climatology_wind.py`, `climatology_wave.py`,
`climatology_current.py`, `backend/tests/test_climatology.py` ;
(simulateur) : `src/layers/useClimatologyLayer.js`, `src/utils/atlasPoint.js`,
`src/utils/atlasPoint.test.js`, `src/layers/climatologyPaint.js` PAR EXTRAIT
(lecture seule : le rendu ne change pas), `server/bi_proxy.py` (liste
`ALLOWED`), `server/tests/test_bi_proxy.py`, `e2e/lots/rd8-tuiles.spec.js`.
`infra/vps/nginx-bi-climatology-cache.conf` : la clé `~^/(api|bi)/climatology/(?<rest>.*)$`
couvre déjà les tuiles — ne pas toucher.

Étapes :
1. Backend : route `GET /api/climatology/{kind}/tiles/{z}/{x}/{y}.json?month=`
   (`kind` ∈ wind | wave | current ; `stat` pour wave comme aujourd'hui).
   Tuile XYZ Web Mercator (même schéma que les tuiles Leaflet), bbox depuis
   z/x/y (lat bornée ±85). Pas de décimation en degrés : `step_deg =
   max(1, 16 / 2**z)` → z ≤ 2 : 4°, z = 3 : 2°, z ≥ 4 : 1° (natif). Un
   itérateur commun `iter_cells(bundle, bbox, step)` sert les tuiles ET les
   `.geojson` existants (sortie inchangée, `is_land` respecté).
2. Propriétés **légères** dans les tuiles : vent `speed_knots`,
   `dir_from_deg`, `calm_pct`, `gale_pct` ; vagues `hs_m` (+ `stat`), `dir` ;
   courants `speed_knots`, `direction_to_deg`. Jamais `directions_from` (la
   rose reste servie par `/climatology/point` au clic, comme aujourd'hui).
   Cible : une tuile ≤ 80 Ko, une vue plein écran ≤ 1 Mo au total.
3. En-tête `Cache-Control` = `CACHE_CONTROL_LAYER` (climatologie 1980-2020,
   immuable) ; tuile hors océan ou sans snapshot → `FeatureCollection` vide,
   200. `bi_proxy.ALLOWED` accepte `^(wind|wave|current)/tiles/\d+/\d+/\d+\.json$`
   (cache disque par URL, repos par point d'accès conservé).
4. Front : `atlasTileUrl(kind, month, z, x, y, extra)` dans `atlasPoint.js`
   (`atlasLayerUrl` reste pour l'export) ; `useClimatologyLayer.js` remplace
   les trois chargements globaux par un chargeur de tuiles : à `moveend` /
   `zoomend` (200 ms de débounce), `zTile = clamp(round(zoom), 0, 6)`, tuiles
   visibles + une marge d'une tuile, antiméridien géré (x modulo 2^z) ;
   cache `Map` clé `kind:month:z/x/y`, `AbortController` par mois/kind ;
   les features des tuiles visibles sont fusionnées dans la collection
   passée à `climatologyPaint.js` — **le rendu ne change pas** (mêmes
   flèches, mêmes couleurs, même popup au clic). Tuiles sorties de l'écran
   (au-delà de la marge) libérées.
5. Tests : backend — bbox(z,x,y) sur 4 tuiles connues, pas par zoom
   (4°/2°/1°), une tuile ne contient que des points dans sa bbox, propriétés
   légères seulement, tuile vide = 200, `.geojson` inchangé ; simulateur —
   énumération des tuiles visibles (dont un viewport qui chevauche
   l'antiméridien), `atlasTileUrl`, `bi_proxy` accepte/refuse les bons
   chemins ; e2e `rd8-tuiles.spec.js` — couche vent allumée : requêtes
   `/bi/climatology/wind/tiles/…json` seulement, **aucune** `wind.geojson` ;
   après un pan, de nouvelles tuiles ; des flèches dessinées.

Recette (visuelle) :
- Suivre, pastille vent (panneau droit) allumée → **tu dois voir** les
  flèches de vent en moins de 2 s sur la zone affichée.
- Zoome sur le golfe de Gascogne → **tu dois voir** les flèches se
  **densifier** (une par degré, ~110 km) au lieu d'une tous les 4° ; recule →
  elles s'espacent, sans trou ni saut.
- Fais glisser la carte vers l'ouest → **tu dois voir** les flèches
  apparaître sur la nouvelle zone en moins de 2 s ; l'ancienne zone ne
  clignote pas.
- Onglet Réseau de Chrome (F12) : des requêtes `…/wind/tiles/4/…json` de
  quelques dizaines de Ko, **aucune** `wind.geojson`.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | RD1 | M | MapScene.jsx, App.jsx, EscaleLegend.jsx (clics carte) |
| 2 | RD2 | S | index.css, Sidebar.jsx, MapSceneController.js (habillage, ancre du point) |
| 3 | RD3 | S | ToolsSidebar.jsx, SkipperOrdersPanel.jsx (panneau droit) |
| 4 | RD4 | M | voyage_api.py, main.py (voyage officiel semé, préchauffages) |
| 5 | RD5 | S | App.jsx, ToolsSidebar.jsx, SimulationFilmBar.jsx (Suivre au départ, dates) |
| 6 | RD6 | S | IciMaintenant.jsx, Sidebar.jsx, useMomentJournal.js (Récit, journal nommé) — après RD4 |
| 7 | RD7 | M | film_script.py, SimulationFilmBar.jsx, useReplay.js (récit du film, durée libre) — après RD4 |
| 8 | RD8 | M | backend climatology.py / climatology_wind.py, useClimatologyLayer.js, atlasPoint.js, bi_proxy.py (couches en tuiles) — indépendant |

Lancement : la boucle (`loop.py`) part seule au merge de la PR de ce
document, **empilée sur la pile #269 → #302** si elle n'est pas mergée
(les ancres ci-dessus ont été lues sur sa tête), depuis `main` sinon. À la
main, si besoin :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --check
caffeinate -i python3 infra/agents/run_lots.py --from RD1 --until RD8 --resume
```

Fin de batch : le poste de recette s'ouvre seul (W0) ; recette par écran ;
merge des PR dans l'ordre de la pile.

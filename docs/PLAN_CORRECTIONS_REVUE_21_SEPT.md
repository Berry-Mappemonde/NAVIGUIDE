# Plan — Corrections de la revue du 21 septembre (nuit 2 : lots R1 → R13)

Version **1.0** — 21 septembre 2026. Le porteur a recetté, dans Chrome, la pile
P2 → L6 (24 PR) sur la dernière branche du batch, puis l'application dans son
ensemble. La pile est **mergée** (#208, #237, #210) et déployée. Ce plan
transforme ses constats en lots de correction, un par PR, à enchaîner la nuit
par `infra/agents/run_lots.py`. Les chantiers de fond (produit unique « ici et
maintenant », journal → récit, expert en circumnavigation) sont dans
`PLAN_ICI_JOURNAL_EXPERT.md` (nuit 3).

Chaque lot suit `REGLES_WORKFLOW_AGENT.md` — en particulier § 1 « rien de
superflu à l'écran » et § 4 « la recette, c'est regarder Chrome, rien d'autre ».

## 0. Ce que la revue a appris (à lire avant tout lot)

- Le porteur **regarde l'application** ; il ne lance rien. Une recette qui
  parle de `data-testid`, de `GET`, de coordonnées ou de fixture n'est pas une
  recette : c'est de la review automatique.
- Les agents ont ajouté des **textes d'explication** dans l'interface, des
  **libellés répétés** (Esri deux fois, le bateau nommé deux fois), une
  **rangée de plus** dans la barre film, un **bouton qui ne marche pas**
  (remettre le chiffre du profil), une **bascule inactive non grisée**. Tout
  cela est interdit désormais (REGLES § 1).
- « Revoir l'expédition » est la surface la plus regardée (vidéo Devpost) : le
  premier clic rate, la voix coupe, le bateau saute de position en position, la
  caméra part vers la Mongolie avant de revenir. C'est la priorité de la nuit.
- La bulle F4 se déclenche à l'envers : elle recopie la carte « décision » du
  panneau gauche **hors film** (bulle « balisage » à l'ouverture, impossible à
  fermer) et se tait **pendant le film**.
- Trois parcours fixes pour toute recette : **Suivre à Nouméa**, **Simulation
  La Rochelle → Ajaccio**, **Tracer ma route Brisbane → San Francisco** ; plus
  **Revoir l'expédition** en Suivre.

## 1. Constats → lots

| Constat du porteur | Lot |
|---|---|
| Phrases d'aide inutiles (journal de bord, revue du plan, chiffres Expert) | R1 |
| « Polaires chargées — Léopard 46 » : le bateau est déjà nommé dans Paramètres avancés | R1 |
| « Esri » deux fois dans les crédits carte | R1 |
| Bouton « remettre le chiffre du profil » (cercle) inerte | R1 |
| Bascule brut / rédigé inactive pendant le film mais pas grisée | R1 |
| Rangée « hindcast · prévision · climatologie » ajoutée sous la barre film | R2 |
| « Masquer la barre » absent en Simulation | R2 |
| Pas de bouton « Escale précédente » à côté de « Prochaine escale » | R2 |
| Premier clic sur « Revoir l'expédition » : deux secondes puis rien | R3 |
| La voix s'arrête avant la fin du récit | R3 |
| Au lancement du film la caméra file vers la Mongolie puis revient sur la Corse | R3 |
| Voix anglaise inaudible | R3 |
| Le film est une suite de captures : le bateau saute, la caméra saute | R4 |
| « Puis, puis, puis » à chaque escale | R5 |
| Étape terrestre (Saint-Maur → La Rochelle) comptée en milles nautiques | R5 |
| Bulle « balisage » collée au bateau à l'ouverture, impossible à fermer | R6 |
| Aucune bulle pendant le film | R6 |
| Fiche d'escale dans le panneau gauche, avec un bouton Écouter | R7 |
| Revue du plan : « 20 septembre → 31 octobre » et « 4,5 jours de mer » sur la même jambe | R11 |
| Fourchette d'arrivée (p10–p90) illisible sous la prochaine escale | R11 |
| On peut tirer la carte hors de ses limites : écran tout bleu | R12 |
| Zoom molette saccadé (non vérifié sur build de prod) | R12 |
| Redites partout dans l'interface | R13 |
| Fiche d'escale et « À bord maintenant » pas à hauteur fixe ; produit unique ; journal ; « Ce que je changerais » ; recalcul 4 643 nm au lieu de 1 371 | nuit 3 (`PLAN_ICI_JOURNAL_EXPERT.md`) |

## 2. Les lots

Convention : « Fichiers » = les seuls fichiers à ouvrir (App.jsx et
MapSceneController.js par `rg -n` + `Read` avec offset/limit). « Recette » =
ce que le porteur voit dans Chrome, rangé par écran.

### R1 — Nettoyage : textes parasites, Esri, polaire, bouton mort, bascule grisée (S)

Objectif : plus une phrase d'explication dans l'interface ; « Esri » une fois ;
« Polaires chargées » sans nom de bateau ; le bouton de remise au profil
marche ; brut / rédigé grisé pendant le film.

État actuel :
- `src/i18n/fr.js:200` `logbookChatHint`, rendu `src/components/LogbookChat.jsx:54`.
- `src/i18n/fr.js:240` `planReviewSummary`, rendu `src/App.jsx:1297` (rg -n "planReviewSummary").
- `src/i18n/fr.js:499` `skipperExpertHint`, rendu `src/components/SkipperOrdersPanel.jsx:300`.
- `src/components/ToolsSidebar.jsx:314` : ``${t("polarLoaded")} — ${polarData.boat_name || …}``.
- `src/layers/styles.js:12` : « Tuiles © Esri · données Esri, HERE, Garmin, © OpenStreetMap contributors ».
- `src/components/SkipperOrdersPanel.jsx:63-95` `NumberRow` : le bouton de remise est `disabled={!forced}` et son `onClick` ne remet pas la valeur du profil (vérifier le câblage `onReset` l. 143 / 191).
- `src/components/SimulationFilmBar.jsx:367` et `:445` : `disabled={Boolean(replay.active)}` sans classe `disabled:`.

Étapes :
1. Supprimer les trois rendus et les trois clés (`fr.js`, `en.js`). Ne rien
   mettre à la place.
2. `ToolsSidebar.jsx:314` : texte = `t("polarLoaded")` seul.
3. `styles.js:12` : « Tuiles © <a>Esri</a> — <a>HERE</a>, <a>Garmin</a>, © <a>OpenStreetMap contributors</a> » (quatre liens, Esri une fois).
4. `NumberRow` : le bouton remet la valeur du profil courant (`PROFILES[profile][field]`) et repasse `forced` à faux ; actif dès qu'une valeur est forcée.
5. Bascule brut / rédigé : ajouter `disabled:opacity-30 disabled:cursor-not-allowed` ; pendant le film, `aria-disabled="true"`.

Tests : `styles.test.js` — exactement une occurrence de « Esri » dans toute la
chaîne ; `SkipperOrdersPanel.test.js` (créer si absent) — clic sur remise →
valeur du profil, `forced` faux ; test de contrat i18n : les trois clés
n'existent plus dans `fr.js` ni `en.js`. `npm test`, `npx vite build`.

Recette :
- Suivre — panneau gauche, encadré Journal de bord : sous « Poser une question », **aucune phrase** d'explication.
- Panneau droit — Paramètres avancés → Chiffres : **aucune phrase** sous les chiffres ; modifier un chiffre puis cliquer le cercle → **le chiffre du profil revient**.
- Panneau droit — outils : « **Polaires chargées** » puis « voir les polaires », **sans « Léopard 46 »**.
- Panneau droit — Revue du plan : en tête, **aucune phrase** « Par jambe : calendrier… ».
- Carte — crédits en bas à droite : « Tuiles © Esri — HERE, Garmin, © OpenStreetMap contributors » : **Esri une seule fois**.
- Revoir — pendant le film, les pilules **brut / rédigé sont grisées**.

### R2 — Barre film : une seule rangée, Masquer partout, Escale précédente (S)

État actuel : `src/components/SimulationFilmBar.jsx:225-245` rangée de
légende des régimes (`regimeLegend`) ; `hideBar` l. 58/116 et bouton
« Masquer la barre » affiché en Cinéma seulement (lot O) ; `goToNextStop`
l. 474-479 avec `canNext` ; clé i18n `previousEscale` (« Escale précédente »)
existe dans `fr.js` et `en.js` sans être utilisée ; handler « prochaine
escale » dans `src/App.jsx` (rg -n "goToNextStop|onNextStop").

Étapes :
1. Retirer la rangée de légende de la barre. La légende (trois couleurs :
   hindcast = ce que le bateau a vraiment rencontré, prévision = 10 jours
   devant, climatologie = moyenne du mois au-delà) devient l'info-bulle
   (`title`) de la pilule de vitesse / régime de la barre, et une ligne dans
   la Revue du plan (panneau droit, au-dessus du tableau). Hauteur de la
   barre ≤ 96 px (contrat du lot O).
2. « Masquer la barre » visible en Suivre **et** en Simulation, Cinéma ou
   non ; « Afficher la barre » réapparaît au même endroit (bord bas).
3. Bouton « Escale précédente » (`data-testid="prev-stop"`) à gauche de
   « Prochaine escale », même style, désactivé (grisé) à la première escale ;
   il se place sur l'escale précédente comme « Prochaine escale » sur la suivante.

Tests : `filmBarLayout.test.js` — pas de `regimeLegend` dans la barre, un
`prev-stop`, hauteur ; `useExpedition*`/handler : escale précédente depuis la
2e escale → 1re ; depuis la 1re → inchangé. `npm test`, `npx vite build`,
`npm run e2e -- e2e/lots/o-barre.spec.js` (doit rester vert).

Recette :
- Simulation — barre film : **une seule rangée** ; **« Masquer la barre »** présent ; le survol de la pilule de vitesse montre la **légende des trois couleurs**.
- Simulation — « **Escale précédente** » et « Prochaine escale » côte à côte ; à La Rochelle, « Escale précédente » est **grisé** ; après « Prochaine escale », « Escale précédente » **ramène à La Rochelle**.
- Suivre — même barre, « Masquer la barre » présent hors Cinéma.

### R3 — Revoir l'expédition : premier clic fiable, voix qui va au bout, caméra sans détour (M)

État actuel : `src/hooks/useReplay.js` (démarrage l. 150-170, boucle
l. 228-310, fetch du script l. 106), `src/hooks/useReplayVoice.js`,
`src/utils/speak.js` (voix l. 49-62, une seule utterance par chapitre),
`src/map/filmCamera.js`, `src/map/MapSceneController.js` (rg -n
"flyTo|filmCamera|syncCamera"). Symptômes : au premier clic le film s'arrête
après ~2 s (hypothèse : `speechSynthesis.getVoices()` vide au premier appel,
`onend` immédiat → tous les chapitres s'enchaînent) ; la voix coupe au milieu
d'un long chapitre (Chrome interrompt les utterances longues) ; au départ un
`flyTo` sur l'emprise de toute la route précède celui du chapitre 1.

Étapes :
1. Démarrage : attendre `voiceschanged` (≤ 1 s) avant la première utterance ;
   si `onend` arrive sans aucun `onboundary` et en < 500 ms, relancer une fois,
   puis basculer en mode linéaire (sans voix) **sans arrêter le film**. Le
   film ne se termine que quand le dernier chapitre est joué.
2. Voix : découper chaque chapitre en phrases (≤ 200 caractères), enchaîner
   les utterances, `charIdx` global conservé pour `onboundary` ; keep-alive
   `pause()/resume()` toutes les 10 s pendant une utterance (Chrome).
3. Caméra : le premier mouvement est celui du chapitre 1 (emprise de la jambe,
   zoom borné [3 ; 7]) ; aucun `flyTo` / `fitBounds` sur la route entière au
   lancement ni au « Retour au live ».
4. Anglais : choisir la voix parmi une liste de préférence (`Google UK English
   Female`, `Google US English`, `Samantha`, `Daniel`, `Karen`, `Moira`, puis
   toute voix `en-*`), `rate` 0,95 ; français : `Google français`, `Thomas`,
   `Amélie`, `Audrey`, puis `fr-*`.
5. `useReplay.test.js` : scénario « onend immédiat sans boundary » → relance
   puis linéaire, film non terminé ; `speak.test.js` : découpage en phrases,
   `charIdx` global monotone ; `filmCamera.test.js` : premier `flyTo` = chapitre 1.

Tests : ci-dessus + `npm run e2e -- e2e/lots/f1-film.spec.js` (durée 142–158 s
en linéaire, inchangé). `npm test`, `npx vite build`.

Recette :
- Revoir — Suivre → **premier** clic sur « Revoir l'expédition » : la voix parle et le bateau part **dès le premier clic** ; la caméra se pose **directement** sur la première jambe (pas de détour vers l'Asie).
- Revoir — laisser le film 2 min 30 : la voix **ne s'arrête pas** avant « Retour au live » ; le film se termine sur la position du jour.
- Revoir — langue anglaise : la voix est **compréhensible** (voix système anglaise, débit normal).

### R4 — Film fluide : le bateau glisse, la caméra suit (M)

État actuel : `src/hooks/useReplay.js:240-260` — avec voix, le temps rejoué
n'avance qu'à chaque `onboundary` (`voiceCharRef`) : la position du bateau est
un escalier au rythme des mots ; sans voix, `frac` par frame (déjà continu).
Caméra : `setView` à 30 Hz sur cette position → mêmes sauts. Fichiers :
`src/hooks/useReplay.js`, `src/engine/replay.js` (`timeAt`), `src/map/filmCamera.js`,
`src/map/MapSceneController.js` (rg -n "setView|filmCamera"), `src/hooks/useReplay.test.js`,
`src/engine/replay.test.js`, `src/map/filmCamera.test.js`.

Étapes :
1. Temps rejoué continu : à chaque frame, `t += dt × vitesseNominale(chapitre)`
   (secondes de chapitre ÷ caractères, calibrée par F1) ; chaque `onboundary`
   donne une cible `timeAt(charIdx)` vers laquelle `t` se recale par
   interpolation en ≤ 300 ms (jamais de saut arrière visible : si la cible est
   derrière, ralentir à 0,7 × jusqu'à rejoindre).
2. Position du bateau = interpolation le long du trait (entre deux points de la
   route, linéaire en lat/lon dépliée) — jamais « le point le plus proche ».
3. Caméra : `setView(bateau au tiers avant, zoom fixe, {animate:false})` à
   chaque frame ; le déplacement par frame est borné (≤ 2 % de la largeur de
   l'écran) hors changement de chapitre ; changement de chapitre = un seul
   `flyTo` 1,2 s (F1).
4. Sillage (`filmWake.js`) et marqueur bateau suivent la même position.

Tests : `useReplay.test.js` — faux timers : 60 frames entre deux boundaries →
60 positions strictement croissantes, écart max entre deux frames < 1/30 de la
jambe ; `replay.test.js` — `positionAt(t)` continue ; `filmCamera.test.js` —
déplacement par frame borné. `npm test`, `npx vite build`, `npm run e2e -- e2e/lots/f1-film.spec.js`.

Recette :
- Revoir — pendant une jambe, le bateau **avance sans à-coups** (comme un film, pas une suite de captures) ; la carte **glisse** avec lui ; le zoom **ne change pas** ; au changement de jambe, un seul mouvement de caméra.

### R5 — Récit : connecteurs variés, kilomètres à terre (S)

État actuel : `src/engine/expeditionStory.js:261` écrit « Puis, le … » en dur
à chaque escale alors que la rotation de connecteurs existe l. 412
(`fr: ["Puis", "Ensuite", "Plus loin", "De là", "Sur la route", "À la jambe
suivante"]`, `en` idem) ; `server/film_script.py:26` a la même liste côté
serveur. L'étape terrestre Saint-Maur → La Rochelle est comptée en nm dans le
récit et dans la carte « Escale » (`src/engine/momentCard.js`).

Étapes :
1. `expeditionStory.js` : le connecteur d'un paragraphe est
   `connecteurs[i % n]` ; jamais deux fois le même à la suite ; tests mis à jour
   (les chaînes attendues changent : c'est voulu).
2. `film_script.py` : même règle pour le script du film.
3. Étape terrestre (`leg.kind === "land"` ou équivalent — rg -n "land|terrestre"
   dans `src/utils/berryLegs.js`, `src/engine/expeditionStory.js`,
   `src/engine/momentCard.js`) : distance en **km** (1 nm = 1,852 km), durée en
   heures de route, libellé « par la route ».
4. `fr.js` / `en.js` : unités.

Tests : `expeditionStory.test.js` — deux paragraphes consécutifs n'ont pas le
même connecteur ; une étape terrestre donne « km » ; `server/tests/test_film_script.py`
idem côté serveur. `npm test`, `pytest -q`, `npx vite build`.

Recette :
- Suivre — panneau gauche, Récit de la traversée : les paragraphes commencent par des mots **différents** (« Puis », « Ensuite », « Plus loin »…), jamais trois « Puis » de suite.
- Simulation — placé sur Saint-Maur : la carte « Escale » dit « **… km** par la route », pas des milles nautiques.

### R6 — Bulles sur le bateau : pendant le film seulement, événements importants, fermables (M)

État actuel : `src/components/MomentCards.jsx:113-118` publie la carte
« décision » du panneau gauche dans la bulle **hors film** (d'où la bulle
« balisage » à l'ouverture) ; `src/hooks/useReplay.js:270-285` publie pendant
le film via `pickFilmEvent` (`src/components/eventBubble.js:76`) qui lit
`chapter.events` du script `GET /voyage/official/film` (`server/film_script.py`) —
si le script n'a pas d'événements, rien n'apparaît. `src/components/EventBubble.jsx`
(bulle Leaflet ancrée au bateau, Échap la ferme) n'a pas de croix.

Étapes :
1. `MomentCards.jsx` : ne plus publier dans la bulle hors film (supprimer
   l'effet l. 113-118). Hors film, aucune bulle sur le bateau.
2. Serveur `film_script.py` : chaque chapitre porte ses événements
   `{charIdx, kind, title, fact, score}` construits depuis le journal du
   voyage : arrivée / départ d'escale (score 3), entrée dans une ZEE (2),
   alerte météo vent ≥ seuil du skipper ou Hs ≥ 3 m (3), AMP à portée (1),
   station / campagne scientifique croisée (2), changement de régime (1). Un
   test Python avec le voyage officiel : chaque chapitre de mer a ≥ 1 événement.
3. Client : la bulle s'affiche pour tout événement de score ≥ 2, ou quand la
   somme des scores des événements non montrés depuis 20 s atteint 3 (« somme
   d'événements ») ; une seule bulle à l'écran, ≥ 3 s, remplacée par la
   suivante (gate existante).
4. `EventBubble.jsx` : croix « × » (`data-testid="event-bubble-close"`) et Échap
   ferment la bulle ; le film continue ; la carte NOW du panneau gauche montre
   le même texte.
5. Vérifier avec l'API locale que `GET /voyage/official/film` renvoie des
   `events` non vides ; sinon corriger la source côté serveur (c'est le
   symptôme « rien n'apparaît »).

Tests : `eventBubble.test.js` — seuil et somme ; `EventBubble.test.js` — croix ;
`MomentCards.test.js` — plus de publication hors film ; `test_film_script.py` —
événements par chapitre. `npm test`, `pytest -q`, `npx vite build`,
`npm run e2e -- e2e/lots/f4-bulle.spec.js` (mettre à jour : la bulle apparaît
pendant le film, pas à l'ouverture).

Recette :
- Suivre — à l'ouverture, **aucune bulle** sur le bateau.
- Revoir — dans la première minute, une bulle **ancrée au bateau** apparaît (escale, ZEE, alerte…) ; la croix la ferme ; le film continue ; une bulle suivante remplace la précédente ; jamais deux à la fois.
- Revoir — la carte NOW du panneau gauche montre **le même texte** que la bulle.

### R7 — Fiche d'escale sur la carte, au clic sur le drapeau (S)

État actuel : `src/components/Sidebar.jsx:405` rend `EscaleSheet`
(`src/components/EscaleSheet.jsx`, bouton Écouter l. 122) dans le panneau
gauche ; la fiche s'ouvre depuis la légende des escales (`onEscaleSheet`,
`src/App.jsx:1514`, `src/hooks/useEscaleSheetState.js`) ; les drapeaux
d'escale sont les marqueurs `waypointMarkers` de `src/map/MapSceneController.js:698-735`,
dont le clic ne sert qu'au mode dessin (l. 727-731). Le motif d'une fiche en
popup Leaflet avec du React existe : `src/components/LayerFichePopup.jsx` et
`attachEventBubble` (`src/components/EventBubble.jsx:134`).

Étapes :
1. `MapSceneController.js` : hors dessin, le clic sur un drapeau appelle
   `this.callbacks.onWaypointClick?.(point, index)`.
2. Nouveau `src/components/EscalePopup.jsx` : popup Leaflet ancrée au drapeau,
   contenu = la fiche actuelle (mêmes `data-testid="escale-*"`), **sans**
   bouton Écouter, avec croix ; largeur ≤ 340 px, défilement interne au-delà
   de 260 px de haut ; s'ouvre sur clic drapeau **et** depuis la légende des
   escales (même état `useEscaleSheetState`).
3. `Sidebar.jsx` : retirer le rendu de `EscaleSheet` (la fiche n'a plus de
   place dans le panneau gauche). `EscaleSheet.jsx` devient le contenu de la
   popup (fichier conservé, `ListenButton` retiré).
4. `fr.js` / `en.js` : rien de nouveau (croix = `close` existante).

Tests : `MapSceneMarkers.test.js` — clic drapeau hors dessin → `onWaypointClick` ;
`EscaleSheet.test.js` — aucun `ListenButton` ; `Sidebar.layout.test.js` — plus
d'`EscaleSheet` dans le panneau. `npm test`, `npx vite build`, spec e2e
`e2e/lots/r7-escale.spec.js` : clic sur le drapeau d'Ajaccio → popup avec le
nom de l'escale.

Recette :
- Simulation — cliquer le **drapeau d'Ajaccio** sur la carte : la fiche d'escale s'ouvre **sur le drapeau** ; **pas de bouton Écouter** ; la croix la ferme.
- Suivre — panneau gauche : **plus de fiche d'escale** dedans ; la légende des escales (bas de carte) ouvre la même fiche **sur la carte**.

### R11 — Fourchette d'arrivée lisible et cohérente (S)

État actuel : `src/components/EscaleLegend.jsx:77` et
`src/components/PlanReview.jsx:66` utilisent `formatEtaRange`
(`src/hooks/usePlanReview.js`), clé `etaRange` : « entre le {p10} et le {p90}
(p10–p90, {n} membres) » ; la revue du plan montre pour Nouméa → Dzaoudzi
« 20 septembre → 31 octobre » et « 4,5 jours de mer » (incohérent avec 42 j).
Serveur : `server/plan_review.py`, `server/voyage_api.py` (`/voyage/official/eta`,
`/voyage/official/plan-review`).

Étapes :
1. Trouver d'où vient « 4,5 jours de mer » (jours à quai ? jambe précédente ?
   division par 10 ?) : test Python sur le voyage officiel — `seaDays` de la
   jambe = distance ÷ vitesse planifiée ÷ 24 à ± 10 %.
2. Libellé : « arrivée entre le 31 oct. et le 4 nov. » (sans « p10–p90 » ni
   « membres » dans l'interface ; ces détails vont dans l'info-bulle).
3. Même fourchette sous la prochaine escale (Suivre) et dans la revue du plan
   (même source, même arrondi).

Tests : `usePlanReview.test.js` — formatage ; `test_plan_review.py` —
cohérence jours de mer / distance / vitesse. `npm test`, `pytest -q`.

Recette :
- Suivre — sous la prochaine escale : « **arrivée entre le … et le …** » (deux dates, rien d'autre).
- Panneau droit — Revue du plan, jambe Nouméa → Dzaoudzi : **la même fourchette** et un nombre de jours de mer **cohérent** avec 42 jours à 8 nœuds.

### R12 — Carte : limites de déplacement, zoom vérifié sur build de prod (S)

État actuel : `src/map/MapSceneController.js:176-178` — `minZoom: 2`,
`worldCopyJump: false`, pas de `maxBounds` : on peut tirer la carte jusqu'à
n'avoir que du bleu. Le lot U (#229) a livré le zoom molette « sans longtask
> 50 ms » ; le porteur l'a vu saccadé sur le serveur de dev, pas sur le build
de prod.

Étapes :
1. `maxBounds` en latitude seulement (lat ∈ [−85 ; 85], longitude libre pour
   les routes dépliées au-delà de 180°), `maxBoundsViscosity: 1`.
2. Zoom : mesurer sur le build de prod (`bash ensure-dev.sh --prod`) avec
   Performance → si un long task > 50 ms subsiste au zoom molette, le nommer
   (couche GRIB, ZEE, sillage…) et le différer à `zoomend` ; sinon écrire dans
   la PR que c'est vérifié.

Tests : `MapSceneBoundary.test.js` — options de la carte ; spec e2e existant du
lot U rejoué sur le build de prod. `npm test`, `npx vite build`.

Recette :
- Suivre — tirer la carte vers le haut ou le bas au maximum : **on ne dépasse pas les pôles**, jamais un écran entièrement bleu.
- Suivre — zoom molette sur l'Atlantique : **la carte suit tout de suite**, sans saccade.

### R13 — Redites : compter, puis supprimer (S)

Objectif : un libellé n'apparaît qu'une fois par écran. Outil + première passe
de suppression.

Étapes :
1. `naviguide-simulator/scripts/redites.mjs` : lit `src/i18n/fr.js`, liste
   les groupes de mots (≥ 2 mots, hors mots vides) présents dans ≥ 2 valeurs,
   et les valeurs identiques sous deux clés ; sortie triée par fréquence.
2. `e2e/lots/r13-redites.spec.js` : pour les quatre écrans (Suivre, Simulation,
   Tracer, panneau droit ouvert), `document.body.innerText` → lignes présentes
   ≥ 2 fois sur le même écran ; écrit `docs/recette/lot-r13/redites-<écran>.txt`.
3. Supprimer les redites évidentes trouvées (même texte deux fois sur le même
   écran ; « Léopard 46 » hors Paramètres avancés ; « climatologie » plus d'une
   fois par écran ; « Polaire » plus d'une fois) — garder la première
   occurrence, lister chaque suppression dans la PR.

Tests : `npm test`, `npx vite build`, le spec ci-dessus. Recette :
- Suivre / Simulation / Tracer — parcourir l'écran : **aucun texte identique deux fois** ; le nom du bateau **une fois** (Paramètres avancés).

## 3. Ordre, pile, tailles

Pile linéaire, dans cet ordre (les lots qui touchent `SimulationFilmBar.jsx`
et `useReplay.js` se suivent pour éviter les conflits) :

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | R1 | S | i18n, ToolsSidebar, styles, SkipperOrdersPanel, SimulationFilmBar |
| 2 | R2 | S | SimulationFilmBar, App (escale précédente) |
| 3 | R3 | M | useReplay, speak, filmCamera |
| 4 | R4 | M | useReplay, replay, filmCamera |
| 5 | R5 | S | expeditionStory, film_script.py, momentCard |
| 6 | R6 | M | MomentCards, EventBubble, eventBubble, film_script.py |
| 7 | R7 | S | MapSceneController, EscaleSheet → EscalePopup, Sidebar |
| 8 | R11 | S | plan_review.py, usePlanReview, EscaleLegend, PlanReview |
| 9 | R12 | S | MapSceneController |
| 10 | R13 | S | scripts/redites.mjs, i18n, spec |

Lancement (soir) : `caffeinate -i python3 infra/agents/run_lots.py --from R1 --until R13`.
Fin de batch : le poste de recette s'ouvre seul (W0). Matin : recette par écran,
merge de la dernière PR.

## 4. Nuit 3

`PLAN_ICI_JOURNAL_EXPERT.md` : R8 (produit unique « ici et maintenant »), R9
(journal des changements → récit de 2 min 30), R10 (expert en circumnavigation :
analyse de la route, compromis écart local / décalage de date qui minimise les
alertes), découpés en sous-lots tenables par un agent à 256 k de contexte.

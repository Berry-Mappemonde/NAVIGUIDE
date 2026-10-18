# Plan — Corrections de la 2ᵉ revue (21 sept. au soir) : lots RA1 → RA8

Version **1.0** — 21 septembre 2026, soir. Le porteur a recetté dans Chrome le
batch R1 → R13 (PR #239 → #248, poste de recette W0). Beaucoup de progrès, mais
« Revoir l'expédition » — **la surface la plus importante pour Devpost** — reste
bugué, et une régression critique est apparue une fois les clés posées : le
**texte du modèle (fiche d'escale, chat) affiche le prompt et le raisonnement**.

Ce plan liste tout ce que la revue a relevé, le classe en lots correctifs
(RA1 → RA8) à enchaîner la nuit par `infra/agents/run_lots.py`, et dit ce qui
est **reporté** aux chantiers R8/R9/R10 (`PLAN_ICI_JOURNAL_EXPERT.md`) pour ne
pas refaire un travail qui sera remplacé.

Prérequis : la pile R1 → R13 est **mergée** (merger la PR de tête #248 suffit,
pile linéaire) ; ce document et les prompts RA sont sur `main` (merger sa PR) ;
les agents partent de `main`.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4).
- **Rien de superflu à l'écran** (REGLES § 1) : R13 a laissé une redite
  (« Croisière · 36 h » à côté de « Paramètres avancés ») — la règle tient
  toujours, et le détecteur de redites doit voir les états repliés/dépliés.
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF. Plus **Revoir l'expédition** en Suivre : priorité.

## 1. Revue par PR (ce que le porteur a vu)

### PR #239 (R1 — nettoyage) — mergeable, un défaut
- OK : plus de phrases d'aide (journal, revue du plan, chiffres) ; remise du chiffre au profil marche (34 → 29 → cercle → 34) ; « Polaires chargées » sans bateau ; crédits « Tuiles © Esri… » corrects.
- **Défaut** : « Croisière · 36 h » s'affiche **deux fois** — dans l'en-tête replié de « Paramètres avancés » **et** dans le panneau (profil + budget). R13 aurait dû le voir → RA6.
- **Défaut** : les **crédits carte sont coupés par la barre de lecture** → RA6.

### PR #240 (R2 — barre film) — mergeable, dépend d'autres lots pour le film
- OK : plus de rangée « prévision/climatologie » dans la barre ; « Masquer la barre » à gauche de Cinéma ; « Escale précédente / suivante » marchent ; Masquer/Afficher marche.
- **Manque** : pas d'info-bulle de vitesse **en mode Suivre** (seulement en Simulation) → RA6.
- **Demande de fond (météo historique)** : en Suivre, la vitesse du tronçon **déjà parcouru** doit venir de la **météo historique** le long de la route depuis le 15 mai 2026 (hindcast), pas de la climatologie ; les 10 jours devant = prévision GRIB. Source la plus simple : l'**archive Open-Meteo (ERA5)** — gratuite, sans clé, déjà branchée dans `server/hindcast.py` (fusion médiane avec Copernicus) → RA8.

### PR #241 (R3 — premier clic Revoir) — gros progrès, bugs restants
- OK : premier clic lance voix + départ immédiat ; caméra directe sur la 1ʳᵉ jambe ; voix tient jusqu'au « Retour au live » ; **voix anglaise bien meilleure**, intelligible.
- **Bug** : **ordre du récit faux** — « … Portuguese EEZ. Puis départ vers Fort-de-France. Escale à Ajaccio (Corse) » : le discours annonce Fort-de-France puis raconte Ajaccio (décalage d'une jambe), et **des escales sont répétées** (Ajaccio deux fois) → RA2.
- **Bugs film** (voir #242) : fond de carte qui disparaît, position live instable → RA3/RA4.

### PR #242 (R4 — film fluide) — le suivi caméra est bon, le reste bugue
- OK : « le suivi de caméra, c'est exactement ce que je veux » ; le zoom ne saute pas au début.
- **Bug** : au bout d'un moment **le bateau saute de position en position** (ne suit plus le trait) → RA3.
- **Bug** : le **fond de carte s'efface complètement** pendant la lecture → RA3.
- **Bug** : **bug de zoom quand le film s'arrête** (il finit sur Cayenne) → RA3.
- **Bug** : le trajet **avion** Cayenne → Saint-Pierre-et-Miquelon est coloré/cliquable comme un trajet en mer ; il doit être **noir pointillé**, non cliquable, hors analyse climato → RA4.

### PR #243 (R5 — connecteurs, km à terre) — partiel
- OK : les paragraphes du récit alternent les connecteurs (perfectible).
- **Bug** : la **fiche d'escale (Port of Call sheet) affiche le prompt** au lieu du texte (« **Analyze User Input: Task: Translate…** Wait, let me re-read carefully… ») → RA1.
- **Bug fiche escale** (R7) : texte **non scrollable**, **croix qui ne ferme pas**, ancrage peu pratique → RA5.
- **À vérifier** après RA1 : la carte « Escale » de Saint-Maur en **km par la route** (déjà OK dans la carte « à bord maintenant » : « 227 km par la route, 4 h »).

### PR #244 (R6 — bulle événement) — logique à revoir
- OK : aucune bulle collée au bateau à l'ouverture ; en Suivre, une bulle apparaît et se ferme.
- **Bug** : en passant de Simulation (fiche escale ouverte) à Suivre, **la fiche reste** et gêne, et **pendant le film** ; les boutons Écouter/Stop/Revoir **ne répondent plus** → RA5.
- **Demande** : la bulle doit servir le film — apparaître **à l'approche d'une escale** ou sur un **événement notable (coup de vent annoncé par GRIB2)**, pas « j'arrive en Corse » ; **dézoomer** sur l'archipel des Caraïbes (arrête de sauter d'île en île) → RA3 (affichage) ; le **choix des événements** → R9.

### PR #246 (R11 — fourchette d'arrivée) — partiel
- OK : Revue du plan, jambe Nouméa → Dzaoudzi : « 9 152 nm · 47,7 j de mer · 3 j à quai ».
- **Bug** : **rien sous la prochaine escale** en Suivre (la fourchette « arriver entre le … et le … » ne s'affiche pas) → RA7.
- **Bug** : intervalle **absurde** « 13 nov. → 10 juin » (7 mois pour 47 j) : un membre d'ensemble dégénéré (vitesse ~0) fait exploser p90 → RA7.

### PR #247 (R12 — bornes carte, zoom) — OK, un défaut
- OK : on ne tire plus la carte au-delà des pôles.
- **Défaut** : la carte se **déroule à l'infini** en longitude (répétition du monde) ; il faut **une seule copie à gauche et à droite** → RA4.

### PR #245 (R7 — fiche escale sur le drapeau) — voir #243/#244
- La fiche s'ouvre sur la carte mais : **croix cassée**, **non scrollable**, **reste pendant le film/Suivre** → RA5. (Sa place définitive : l'encadré unique de R8.)

### PR #248 (R13 — redites) — a raté la redite skipper
- Le détecteur ne voit pas les doublons repli/dépli (en-tête `<summary>` vs contenu) → RA6.

## 2. Revue générale (application entière)

- **Fiche d'escale et chat affichent le prompt/raisonnement du modèle** (clés posées) → RA1. Cause : `_call_tokenfactory` n'éteint pas le *thinking* de Nemotron (contrairement à `_call_nim`) et `_clean_text` ne retire pas le raisonnement.
- **Journal de bord** : gros vide violet entre « poser une question » et le champ ; il faut un **cadre de réponse** où la réponse s'écrira → RA6.
- **Position live instable** : au rechargement, le bateau apparaît à Nouméa (cache) puis saute après Panama ; probablement les jambes avion faussent la distance / un recalcul client divergent → RA4.
- **Revoir l'expédition = la priorité** : RA2 (ordre), RA3 (rendu), RA4 (avion + live), RA5 (boutons) le remettent d'aplomb avant R8/R9.

## 3. Ce qui est reporté (folded), pour ne pas jeter du travail

- **Placement** de la fiche d'escale, des cartes « à bord maintenant », des fiches science, de « pendant ce temps autour du bateau » dans **un seul encadré** → **R8** (`PLAN_ICI_JOURNAL_EXPERT.md`). RA5 se contente de rendre la fiche **fermable** et de ne pas l'afficher pendant le film ; R8 la déplacera.
- **Choix des événements** de bulle et **texte du récit du film** → **R9** (journal des moments → récit). RA2 corrige seulement l'**ordre** dans le générateur actuel (le film Devpost doit être correct tout de suite) ; RA3 corrige l'**affichage** de la bulle.
- **Vitesse réelle par la météo historique le long de la route** → **RA8** (source Open-Meteo ERA5, sans clé — pas de dépendance Copernicus), après que le film soit solide.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read` offset/limit
pour App.jsx et MapSceneController.js). « Recette » = ce que le porteur voit
dans Chrome, par écran. Pile linéaire dans l'ordre RA1 → RA8.

### RA1 — La pensée du modèle ne s'affiche jamais (fiche d'escale, chat, traduction, film rédigé) — CRITIQUE (M)

Cause racine : `server/story_cascade.py` — `_call_tokenfactory` (payload
~l. 424-440) n'envoie pas `chat_template_kwargs={"thinking": False}` /
`reasoning_effort:"low"` alors que `_call_nim` (l. 460-470) le fait ; Nemotron
émet donc son raisonnement, `_openai_text` (l. 389) le renvoie tel quel et
`_clean_text` (l. 284) ne retire que les fences. Fiche d'escale (`escale_api.py`
→ `cascade_text`/`translate`) et chat (`logbook_chat.py:429` → `cascade_text`)
affichent alors « **Analyze User Input: Task: Translate…** Wait, let me
re-read… ».

Fichiers : `server/story_cascade.py` (`_call_tokenfactory`, `_openai_text`,
`_clean_text`, `_META_RE`, `translate`), `server/tests/test_story_cascade.py`,
`server/escale_api.py` PAR EXTRAIT (`rg -n "translate|tidy_story|cascade_text"`),
`server/logbook_chat.py` PAR EXTRAIT (`rg -n "cascade_text|filter_numbers"`),
`server/tests/test_escale_api.py` / `server/tests/test_logbook_chat.py` s'ils existent.

Étapes :
1. `_call_tokenfactory` : ajouter `"chat_template_kwargs": {"thinking": False}`
   et `"reasoning_effort": "low"` au payload (comme NIM).
2. `_openai_text` : ignorer `message.reasoning_content` ; ne lire que
   `message.content` ; retirer tout bloc `<think>…</think>` (et un `<think>`
   ouvert sans fermeture : couper à partir de la balise).
3. `_clean_text` : après les fences, retirer un préambule méta en tête
   (« Analyze User Input », « Task: », « Constraints: », « Request: »,
   « Wait, », « Let me », « The user says », « Thinking OFF », lignes en
   `**gras**` de consigne) jusqu'à la première vraie phrase.
4. Garde-fou : si le texte nettoyé contient encore un fragment du system
   prompt (p. ex. « translate a sailing-log paragraph », « Keep every number »),
   renvoyer le `fallback` (source `rules`) plutôt que la fuite.
5. Tests : une réponse Token Factory factice contenant `<think>…</think>` +
   raisonnement + phrase finale → seule la phrase finale sort ; une réponse qui
   n'est **que** du raisonnement → fallback ; le payload Token Factory contient
   `chat_template_kwargs.thinking == False`.

Recette (visuelle) :
- Simulation, langue **anglais**, clic sur le **drapeau de Saint-Maur** → la fiche « Port of call sheet » contient de **vraies phrases anglaises** sur l'escale, **jamais** « Analyze User Input / Task / Wait, let me… ».
- Suivre, Journal de bord → poser « À quelle vitesse va le bateau ? » → la réponse est **une phrase**, pas un prompt.

### RA2 — L'ordre du récit suit exactement le voyage (S)

Cause racine : le récit apparie « départ vers la jambe i+1 » avec « arrivée à
l'escale i » (décalage d'une jambe) et répète des escales. `expeditionStory.js`
(`legParagraph` ~l. 281-305, `stopsWithDates` l. 124-141) et le film serveur
`server/film_script.py` (chapitres `dated_marks` l. 138-153, assemblage
l. 270-293).

Étapes :
1. Apparier chaque paragraphe/chapitre à **une seule** jambe `stops[i] → stops[i+1]` :
   « départ de stops[i] le {départ}, … , arrivée à stops[i+1] le {arrivée}, N jours à quai ».
2. Dédoublonner les escales (déjà `abs(filmNm) < 0.6` côté serveur : vérifier
   que l'itinéraire Berry n'a pas deux marques au même nom à des filmNm proches).
3. L'ordre est **strictement** celui de la route (`filmNm` croissant) ; aucune
   escale citée deux fois ; « départ vers X » = l'escale **suivante** réelle.
4. Tests : `expeditionStory.test.js` et `test_film_script.py` — sur le voyage
   officiel, la suite des noms cités est exactement Saint-Maur, La Rochelle,
   Ajaccio, Fort-de-France, … (ordre de la route), sans répétition, chaque
   « départ vers X » suivi de « arrivée à X ».

Recette (visuelle) :
- Suivre → Revoir l'expédition (FR puis EN) : le récit énonce les escales **dans l'ordre du voyage** (Saint-Maur → La Rochelle → **Ajaccio/Corse** → Fort-de-France → …), **sans** annoncer Fort-de-France avant la Corse, **sans** répéter une escale.

### RA3 — Revoir l'expédition : fond de carte gardé, aucun saut, zoom stable en fin, dézoom archipels, bulle utile (M)

Fichiers : `src/map/MapSceneController.js` PAR EXTRAIT (base layer l. 194 et
`switchBaseLayer` l. 425-432 ; caméra film l. 367-415 ; `syncFilmCamera`),
`src/map/filmCamera.js` (+ test), `src/engine/filmCast.js` (interpolation, air),
`src/hooks/useReplay.js` (boucle l. 228-310 ; position le long du trait),
`src/hooks/useReplay.test.js`.

Étapes :
1. **Fond de carte** : la couche de tuiles reste visible pendant tout le film ;
   si `switchBaseLayer` est appelé pendant le film (zoom/régime), ne jamais
   laisser la carte sans tuiles (ré-ajouter avant de retirer, ou ne pas
   switcher pendant `filmActive`).
2. **Aucun saut** : la position du bateau est interpolée **le long du trait**
   sur **toute** la durée (fin de film comprise), jamais « le sommet le plus
   proche » ni un saut de plan ; poursuivre RA jusqu'au dernier chapitre.
3. **Zoom stable en fin** : quand le film se termine (sur Cayenne ou ailleurs),
   pas de saut de zoom ; retour au live sans `fitBounds` sauvage.
4. **Dézoom archipels** : le zoom d'un chapitre borne l'emprise de la jambe mais
   plafonne pour qu'un chapitre « saut d'île en île » (Caraïbes) montre
   l'ensemble de la sous-branche, sans sauter d'île en île.
5. **Bulle utile** (affichage) : la bulle apparaît **à l'approche d'une escale**
   et sur un **événement notable** ; une seule à la fois ; fermable (croix,
   Échap) ; le film continue. (Le **choix** des événements — coup de vent GRIB2,
   station — est raffiné en R9.)
6. Tests : `useReplay.test.js` — 60 frames entre deux boundaries → positions
   monotones le long du trait jusqu'au dernier chapitre ; `filmCamera.test.js` —
   zoom plafonné pour une jambe à sauts courts ; pas de switch de base layer
   pendant `filmActive`.

Recette (visuelle) :
- Revoir → pendant tout le film : le **fond de carte reste** ; le bateau **glisse** sans saut jusqu'à la fin ; le **zoom ne saute pas** quand ça s'arrête ; dans les **Caraïbes**, la caméra montre l'archipel sans sauter d'île en île ; une **bulle** apparaît à l'approche des escales, fermable.

### RA4 — Jambes avion : trait noir pointillé, hors distance, position live stable, carte bornée en longitude (M)

Fichiers : `src/map/MapSceneController.js` PAR EXTRAIT (tracé de la route
officielle `addRouteLine` l. 63 et segments l. 457-492 ; `maxBounds` l. 182),
`src/utils/berryLegs.js` (type de jambe : mer / terre / **air**),
`src/engine/filmCast.js` (`isAirPhase`), `server/voyage_clock.py` PAR EXTRAIT
(jambe avion l. 541-548 ; distance voile), `server/voyage_api.py` PAR EXTRAIT
(clock officielle), tests associés.

Étapes :
1. **Trait avion noir pointillé** : les segments de la route officielle dont la
   jambe est de type air (Cayenne ↔ Saint-Pierre-et-Miquelon, sauts Pacifique)
   sont tracés en **noir pointillé**, **non colorés** par régime, **non
   cliquables** (pas de fiche, pas de survol).
2. **Hors analyse climato** : la vitesse/régime affichés et la couleur ne
   s'appliquent qu'aux jambes en mer.
3. **Position live stable** : la position live vient **d'une seule source**
   (l'horloge officielle serveur) ; au rechargement, le bateau ne « saute » pas
   d'une position cache à une autre ; la distance parcourue affichée **exclut**
   les milles des jambes avion (le vol prend `AIR_CALENDAR_HOURS`, il n'ajoute
   pas de milles « à la voile »).
4. **Longitude bornée** : la carte se déroule **au plus une copie du monde à
   gauche et à droite** (pas de répétition infinie) — `maxBounds` en longitude
   bornée (p. ex. `[-540, 540]`) ou `worldCopyJump` + limite, tuiles `noWrap`
   au-delà.
5. Tests : `MapSceneBoundary.test.js` — longitude bornée ; `berryLegs`/route —
   une jambe air produit un trait `dash` noir non interactif ;
   `test_voyage_clock.py` — la distance « voile » cumulée exclut les jambes air ;
   position live déterministe pour une date donnée (deux appels → même position).

Recette (visuelle) :
- Suivre, carte monde : le trait **Cayenne ↔ Saint-Pierre** (et les sauts Pacifique) est **noir pointillé**, pas violet/bleu, non cliquable.
- Recharger (Cmd R) plusieurs fois en Suivre : le bateau apparaît **à la même position** (pas de saut Nouméa → Panama).
- Tirer la carte sur les côtés : le monde ne se répète **qu'une fois** de chaque côté.

### RA5 — Logique des boutons de lecture + pas de fiche d'escale pendant le film (M)

Fichiers : `src/hooks/useReplay.js` (stop / états), `src/components/SimulationFilmBar.jsx`
(boutons ; `stopAuto` l. 78-79 ; `replay` controls l. 407), `src/App.jsx` PAR
EXTRAIT (`rg -n "escaleStop|openEscaleSheet|replay|onStop|returnToLive"`),
`src/components/EscalePopup.jsx` (croix), tests associés.

Étapes :
1. **Stop stoppe** : un bouton clair arrête le film (voix + animation + caméra)
   et revient à la vue Suivre normale ; distinct de « Stop auto » (arrêt à la
   prochaine escale) et de « Écouter » (voix on/off), chacun étiqueté et faisant
   ce qu'il dit. Pas d'état où plus aucun bouton ne répond.
2. **Machine à états** cohérente : Suivre ↔ Simulation ↔ Revoir ; passer de
   Simulation à Suivre **ferme** la fiche d'escale ; lancer Revoir **ferme** la
   fiche d'escale.
3. **Pas de fiche pendant le film** : aucune popup d'escale visible pendant
   Revoir ni au passage en Suivre ; **croix et Échap ferment** la fiche
   (corrige R7 : la croix ne fermait pas).
4. Tests : `useReplay.test.js` — `stop()` remet `active=false`, coupe la voix,
   libère la caméra ; test d'état — passer en Suivre/Revoir vide `escaleStop` ;
   `EscalePopup.test.js` — la croix appelle `onClose`.

Recette (visuelle) :
- Simulation → ouvrir la fiche d'escale → **Suivre** : la fiche **disparaît**. Lancer **Revoir** : pas de fiche ; **Stop** arrête net ; **Écouter** coupe/relance la voix ; aucun bouton « mort ».

### RA6 — Finitions : redite skipper, crédits au-dessus de la barre, km jambe terrestre, cadre de réponse du chat, détecteur repli/dépli (S)

Fichiers : `src/components/SkipperOrdersPanel.jsx` (`<summary>` l. 183-195 vs
budget l. 257), `src/layers/styles.js` / `src/index.css` (position des crédits),
`src/components/SimulationFilmBar.jsx` (libellé jambe terrestre : km),
`src/components/LogbookChat.jsx` (cadre de réponse ; vide l. ~54),
`naviguide-simulator/scripts/redites.mjs` (R13), `src/i18n/fr.js`/`en.js`.

Étapes :
1. **Redite skipper** : l'en-tête replié de « Paramètres avancés » ne répète pas
   le profil + budget déjà dans le panneau ; garder une seule occurrence.
2. **Crédits au-dessus de la barre** : l'attribution Leaflet est remontée
   (marge basse ≥ hauteur de la barre film) pour ne pas être **coupée** par la
   barre de lecture.
3. **Info-bulle de vitesse en Suivre** : la pilule de vitesse a la même
   info-bulle « hindcast/prévision/climatologie » qu'en Simulation (R2 ne l'a
   mise qu'en Simulation).
4. **Jambe terrestre en km** dans la barre film (Saint-Maur → La Rochelle :
   « … km par la route · h de route », pas « nm »).
5. **Cadre de réponse du chat** : sous « Poser une question », un cadre visible
   destiné à la réponse (remplit le vide violet) ; la réponse s'y écrit.
6. **Détecteur** `redites.mjs` : compter aussi les doublons entre un `<summary>`
   replié et le contenu déplié (rendre les deux, comparer).
7. Tests : `SkipperOrdersPanel.test.js` — le profil/budget n'apparaît qu'une
   fois ; `styles.test.js` / test de layout — la marge des crédits ≥ hauteur
   barre ; `LogbookChat.test.js` — le cadre de réponse est présent.

Recette (visuelle) :
- Panneau droit → « Paramètres avancés » : « Croisière · 36 h » **une seule fois**.
- Carte : les crédits ne sont **pas coupés** par la barre.
- Suivre : survol de la vitesse → info-bulle des trois régimes.
- Simulation, Saint-Maur : la barre dit « **km par la route** ».
- Journal de bord : un **cadre** attend la réponse (plus de grand vide violet).

### RA7 — Fourchette d'arrivée sous la prochaine escale + intervalle resserré (S)

Cause racine : `EscaleLegend.jsx:77` calcule bien `formatEtaRange`, mais
l'ensemble ETA (C6) est vide ou dégénéré en Suivre : un membre à ~0 kn fait un
p90 à 7 mois (« 13 nov. → 10 juin »). Fichiers : `src/hooks/usePlanReview.js`
(`formatEtaRange` l. 25, `useOfficialEta`), `src/components/EscaleLegend.jsx`
(l. 75-78), `server/voyage_api.py` PAR EXTRAIT (`/voyage/official/eta`
ensemble), `server/plan_review.py`, tests.

Étapes :
1. **Sous la prochaine escale (Suivre)** : afficher « arriver entre le … et le … »
   (deux dates courtes) quand l'ensemble existe ; sinon rien (jamais inventé).
2. **Resserrer** : écarter les membres à vitesse dégénérée (plancher 3 kn, comme
   la planification `voyage_clock.boat_speed`), et/ou borner p10–p90 à une
   fenêtre plausible ; le détail p10–p90/membres reste en info-bulle.
3. Tests : `test_voyage_api`/`test_plan_review` — sur le voyage officiel,
   l'intervalle Nouméa → Dzaoudzi est **de quelques jours**, pas de mois ;
   `usePlanReview.test.js` — pas de membre à 0 kn dans la fourchette.

Recette (visuelle) :
- Suivre → **sous la prochaine escale** : « arriver entre le … et le … » (deux dates).
- Panneau droit → Revue du plan, Nouméa → Dzaoudzi : une fourchette **de quelques jours** (plus « 13 nov. → 10 juin »).

### RA8 — Vitesse réelle par la météo historique le long de la route (hindcast + prévision) — après le film (M)

Demande du porteur : en Suivre, la vitesse du tronçon **déjà parcouru** vient de
la **météo historique** le long de la route depuis le **15 mai 2026** ; les
**10 jours devant** = prévision GRIB ; au-delà = climatologie. Aujourd'hui la
route est violette (climatologie) partout parce que le hindcast n'alimente pas
encore la vitesse / le régime.

**Source : l'archive Open-Meteo (ERA5), pas d'obligation Copernicus.** Le porteur
l'a noté : plutôt que des GRIB2 Copernicus (clé + gros téléchargement + ~40 min),
la **météo historique Open-Meteo** suffit et est déjà là. `server/hindcast.py`
lit déjà `archive-api.open-meteo.com/v1/archive` (ERA5, vent horaire depuis 1940,
**sans clé**) et `historical-forecast-api.open-meteo.com`, et **fusionne par
médiane** avec Copernicus/CMEMS quand les identifiants existent ; une source en
panne manque, aucune source → champ vide (jamais inventé). RA8 ne dépend donc
**pas** de Copernicus : le vent du passé vient d'ERA5 Open-Meteo ; CMEMS reste un
bonus (vagues, courant) par fusion.

Fichiers à ouvrir (seulement) : `server/hindcast.py` (ERA5 Open-Meteo `OM_ERA5_URL`,
fusion), `server/voyage_api.py` PAR EXTRAIT (`_fill_hindcast_then_forecast`,
`_kick_official_hindcast` l. 629-655), `server/voyage_clock.py` (régime par
sommet `_clock_kind` l. 421-424, vitesse), `server/tests/test_hindcast.py`,
`server/tests/test_voyage_clock.py`.

Étapes :
1. Vérifier que le **vent ERA5 Open-Meteo** est bien lu pour dater/teindre le
   tronçon parcouru (régime `hindcast`), la prévision GFS Open-Meteo sur 10 jours,
   la climatologie au-delà ; `/ici/warm/status` → `store.hindcast` monte **sans**
   dépendre de Copernicus.
2. Si le hindcast ne couvre pas toute la route parcourue : compléter le
   remplissage ERA5 le long du trait (dates réelles de passage), en tâche de fond,
   sans bloquer le démarrage.
3. La vitesse d'un sommet passé vient du vent réel de l'époque × la polaire
   (pas de la climatologie) ; aucun appel réseau dans les tests (fixtures ERA5).
4. Tests : `test_hindcast`/`test_voyage_clock` — un sommet daté dans le passé a
   `regime=hindcast` et une vitesse issue du vent ERA5 (fixture), pas de la
   climatologie ; une réponse Open-Meteo archive factice suffit (pas de Copernicus).

Recette (visuelle) :
- Suivre : le **tronçon déjà parcouru** est teinté **hindcast** (plus tout violet climatologie) ; la vitesse d'un point passé correspond au vent réel de l'époque, **sans** clé Copernicus.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | RA1 | M | story_cascade.py (thinking off + strip reasoning) |
| 2 | RA2 | S | expeditionStory.js, film_script.py (ordre) |
| 3 | RA3 | M | MapSceneController.js, filmCamera.js, useReplay.js (rendu film) |
| 4 | RA4 | M | MapSceneController.js, berryLegs.js, voyage_clock.py (avion, live, bornes) |
| 5 | RA5 | M | useReplay.js, SimulationFilmBar.jsx, App.jsx (boutons, fiche) |
| 6 | RA6 | S | SkipperOrdersPanel, styles, LogbookChat, redites.mjs (finitions) |
| 7 | RA7 | S | usePlanReview.js, EscaleLegend.jsx, voyage_api.py (fourchette) |
| 8 | RA8 | M | hindcast.py, voyage_clock.py (météo historique ERA5 Open-Meteo, sans Copernicus) — **après le film** |

Lancement (soir), une fois la pile R1 → R13 mergée (#248) et la PR de ce
document mergée :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --check
caffeinate -i python3 infra/agents/run_lots.py --from RA1 --until RA8
```

Fin de batch : le poste de recette s'ouvre seul (W0) ; recette par écran ;
merge de la dernière PR.

## 6. Nuit suivante — R8/R9/R10 révisés

Voir `PLAN_ICI_JOURNAL_EXPERT.md` (mis à jour avec la revue du soir) : encadré
**sans titre** qui absorbe toutes les pop-up de carte ; récit de 2 min 30
**préchauffé** et **découpé** pour tenir dans les limites de Nemotron ; expert
en circumnavigation dont l'alerte cyclone ne compte **que si le bateau croise la
trace historique à la date (saison) où le cyclone a eu lieu**.

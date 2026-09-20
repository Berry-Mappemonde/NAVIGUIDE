# Plan — « Revoir l'expédition » : un film de 2 min 30, raconté, avec ses événements

Version **1.0** — 20 septembre 2026. Règles : `docs/REGLES_WORKFLOW_AGENT.md`.
Ce plan **remplace** les lots Q et R de `PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md`
(qui restent valables comme description des causes racines) par une cible
plus précise, demandée par le porteur le 20 septembre.

## 0. La cible, en une page

Quand on appuie sur **Revoir l'expédition** (mode Suivre) :

1. Le bateau part de **Saint-Maur** (15 mai 2026), prend la route jusqu'à
   La Rochelle, puis la mer, et parcourt la route Berry-Mappemonde jusqu'à
   **sa position du moment**. Mouvement **continu**, zoom **stable**, caméra
   qui suit.
2. Une **voix raconte** l'expédition, du départ à aujourd'hui : bien écrit,
   chronologique, varié, avec des **événements** — un coup de vent, un
   changement de régime climatique (alizés, pot au noir…), une station
   scientifique croisée de près, une aire marine traversée, une escale et ce
   qu'on y voit.
3. Chaque événement raconté **s'ouvre à l'écran au moment où la voix le dit**,
   dans une **bulle qui part du bateau** (popup ancrée au marqueur), propre,
   lisible, qui se referme quand l'événement suivant arrive.
4. Le film dure **2 min 30** (150 s), quelle que soit la longueur du voyage
   déjà parcouru : c'est la durée de la vidéo de soumission du hackathon.
   Option 3 min pour l'usage courant (réglage, défaut 2:30).
5. Le texte lu est **le récit**, pas le panneau de Nouméa : il est écrit pour
   150 s de voix (≈ 375 mots, ≈ 2 400 caractères en français), en français et
   en anglais.

Ce qui existe déjà et sert de base : `useReplay` (1 s/jour, cartes du journal),
`replay.js` (fenêtre, échantillon, cartes), `expeditionStory.js` (récit par
jambe, GRIB, événements ZEE/AMP/PoE/wx), `useReplayVoice` (Web Speech),
`story_cache.py` (SQLite), journal v2 (`voyage_journal.py` : stop, zee, amp,
poe, wx, note).

## 1. Principe : la voix mène, le bateau suit

Le Web Speech API ne garantit pas la durée d'une lecture. On ne cale donc pas
la voix sur le bateau : on cale **le bateau sur la voix**.

- Le récit est découpé en **chapitres**. Chaque chapitre couvre un intervalle
  du voyage `[tA, tB]` (ISO du journal) et porte un texte.
- Quand le chapitre commence à être lu, le bateau est à `tA` ; l'avancement de
  la lecture (événement `onboundary`, index de caractère / longueur du
  chapitre) fait progresser le temps rejoué linéairement vers `tB` ; à
  `onend`, on est à `tB` et on passe au chapitre suivant.
- Les **événements** d'un chapitre ont chacun une position dans le texte
  (index du caractère où la phrase commence) : la bulle s'ouvre quand la
  lecture franchit cet index, et se ferme à l'événement suivant ou à la fin
  du chapitre (minimum 3 s à l'écran).
- **Durée totale** : le script est écrit pour 150 s à `rate = 1`. Au premier
  chapitre on mesure la vitesse réelle de la voix (caractères/s) et on
  ajuste `utterance.rate` des chapitres suivants dans [0,9 ; 1,25] pour
  retomber sur 150 s ± 8 s. Sans voix (bouton coupé), le bateau avance à
  `durée du voyage / 150 s` et les bulles s'ouvrent aux dates des événements.
- Navigateur sans Web Speech (Safari iOS sans voix installée) : mode sans voix
  + sous-titres (le texte du chapitre courant s'affiche dans la barre film).

## 2. Les événements : détection, sélection, écriture

### 2.1 Candidats (calcul, jamais LLM)

Le journal officiel (`GET /voyage/official/journal`) fournit déjà `stop`,
`zee`, `amp`, `poe`, `wx`, `note`. Deux détecteurs manquent, à ajouter à
`server/voyage_journal.py` (et alimentés par les perles riches de
`ici_warm.py`) :

| Kind | Règle | Données |
|---|---|---|
| `climo` | changement de **régime** entre deux perles consécutives : rose des vents dominante qui tourne de ≥ 90°, ou passage alizés → calmes équatoriaux (vent moyen < 8 kn sur 2 perles), ou entrée/sortie de la saison cyclonique | atlas climatologie (déjà en perle : `climo.rose`, `climo.cyclones`) |
| `sci` | station / campagne scientifique à ≤ 10 nm de la route, une fois par entité | couche science des perles riches |
| `wx` (existant, à enrichir) | coup de vent ≥ 34 kn (force 8) ou Hs ≥ 4 m ; ajouter la **durée** (heures) et le **max** | GRIB / hindcast (voir `PLAN_AUDIT_CALCULS.md` § 3) |
| `stop` (existant, à enrichir) | jours à quai + 2 lieux remarquables de la fiche d'escale (section tourisme, en cache) | `escale_api.py` |

Chaque candidat porte : `t` (ISO), `lat/lon`, `kind`, `title`, `facts`
(nombres et noms **seuls autorisés dans le texte**), `entity` (pour la bulle :
lien carte, site officiel, Google Maps — déjà `CardLinks`).

### 2.2 Sélection (règles d'abord, LLM en option)

Un film de 150 s supporte **6 à 9 bulles**. Sélection par règles, déterministe :

1. Toujours : départ (Saint-Maur → La Rochelle, route), chaque **escale**
   effectuée (max 6 ; au-delà, garder les escales de plus de 2 jours à quai
   et les premières/dernières), l'arrivée « aujourd'hui ».
2. Puis, par score : `wx` (max × durée), `climo`, `sci`, `amp`, `zee`, `poe` —
   jusqu'au quota, en évitant deux événements à moins de 3 % du temps total.

Option LLM (lot F3) : Nemotron (via Token Factory, cf.
`PLAN_NEMOTRON_NEBIUS_TAVILY.md`) reçoit la liste complète des candidats
(JSON, ≤ 8 k tokens) et renvoie **les identifiants** des 6–9 retenus avec une
raison d'une ligne. Il ne produit ni chiffre ni texte narratif à cette étape.
Repli : la sélection par règles. Le résultat est en cache (clé = hash du
journal + lang + durée cible).

### 2.3 Écriture du script

Deux versions, toutes deux disponibles :

- **Brut** (règles, `expeditionStory.js` étendu) : chapitres = jambes entre
  escales ; connecteurs en rotation ; phrases d'événement depuis des gabarits
  (`« Le 27 mai, au large du cap Finisterre, le vent est monté à 38 nœuds
  pendant six heures. »`). Longueur contrôlée : on retire d'abord les
  événements de score le plus bas jusqu'à ≤ 2 400 caractères.
- **Rédigé** (Nemotron 3 Super via Token Factory) : le modèle reçoit le brut
  et les faits, doit garder **tous les nombres, noms et dates tels quels**,
  varier la langue, tenir 2 300–2 500 caractères, marquer chaque événement par
  une balise `[[ev:<id>]]` au début de sa phrase (pour ancrer la bulle). Le
  serveur vérifie : filtre des nombres (`filter_numbers`), présence de toutes
  les balises, longueur ; sinon repli sur le brut. Cache SQLite
  (`story_cache.py`, ns `film`), régénéré au plus 1×/jour et à chaque nouvelle
  escale. Coût : ~6 k tokens entrée + 1 k sortie ≈ **0,003 $ par génération**.

Anglais : même pipeline avec `lang=en` (le brut est déjà bilingue).

## 3. La bulle « événement » (remplace la carte NOW pendant le film)

- Composant `EventBubble` rendu **dans un `L.popup`** ancré au marqueur du
  bateau (`autoPan: false`, `closeButton: false`, classe `event-bubble`),
  mis à jour à chaque déplacement du marqueur (`popup.setLatLng`).
- Contenu : icône du kind, titre (≤ 40 caractères), 1–2 lignes de faits,
  chips (vent, Hs, jours à quai…), liens `CardLinks`. Largeur 280 px, fond
  sombre translucide, flèche vers le bateau. Mode clair : contrastes du lot I.
- Apparition/disparition : fondu 200 ms ; minimum 3 s ; une seule bulle à la
  fois ; le clavier `Échap` la ferme sans arrêter le film.
- Pendant le film, la carte NOW de la sidebar **n'est pas retirée** : elle
  affiche la même carte (texte identique) — la bulle est l'événement « à
  l'écran », la sidebar garde l'historique. Hors film (Suivre / Simulation),
  la carte NOW ouvre **aussi** la bulle sur le bateau quand une carte
  d'alerte ou de décision arrive (même composant), et la sidebar reste comme
  aujourd'hui (plancher `main`).

## 4. Caméra et cinématique

- **Zoom fixe pendant un chapitre**, choisi pour que la jambe du chapitre
  tienne dans 70 % de la fenêtre (`getBoundsZoom` au début du chapitre),
  borné [3 ; 7] ; transition de zoom **uniquement** au changement de chapitre,
  en `flyTo` de 1,2 s pendant la première phrase.
- **Pan continu** : `setView(boat, zoom, {animate: false})` à 30 Hz depuis la
  boucle `requestAnimationFrame` du film, avec le bateau au **tiers avant**
  de l'écran (offset dans la direction du cap), sidebars comprises.
- Route déjà parcourue en trait plein, à venir en pointillé ; le tronçon
  route (Saint-Maur → La Rochelle) en icône voiture.
- Aucun `zoomForRemaining`, aucun `fitBounds` en cours de chapitre ; les
  drapeaux/escales ne sont pas recalculés pendant le film (`waypointsDirty`
  gelé — cf. lot I).
- Fin du film : le bateau arrive à sa position live, la bulle « Aujourd'hui »
  s'ouvre (position, vitesse mesurée ou « à quai », prochaine escale), la
  voix se tait, le mode Suivre reprend.

## 5. Les lots

Ordre : **F1 → F2 → F3 → F4 → F5** (F3 et F4 indépendants après F2). Taille :
S ≤ ½ jour, M ≤ 2 jours.

### Lot F1 — Chapitrage et cinématique menée par la voix (M)

**Fichiers.** `src/engine/replay.js` (+ test), `src/hooks/useReplay.js`,
`src/hooks/useReplayVoice.js`, `src/utils/speech.js`, `src/map/MapSceneController.js`
**par extrait** (`rg -n "syncCamera|zoomForRemaining" …`), `src/components/SimulationFilmBar.jsx`
(sous-titres + réglage 2:30 / 3:00), `src/i18n/{fr,en}.js`.

**Étapes.** 1) `filmPlan({chapters, targetSeconds})` dans `replay.js` :
répartit 150 s entre chapitres au prorata des caractères ; expose
`timeAt(chapterIdx, charIdx)`. 2) `useReplay` : boucle `rAF` ; `onboundary`
→ `charIdx` ; `onend` → chapitre suivant ; sans voix, avance linéaire. 3)
Calibrage du `rate` après le chapitre 1. 4) Caméra § 4. 5) Barre film :
sous-titre du chapitre courant, sélecteur 2:30 / 3:00, progression.

**Tests.** `replay.test.js` : répartition des 150 s, `timeAt` monotone,
calibrage borné. Contrat : aucun `flyTo` hors changement de chapitre.

**Recette (changement visible).** Suivre → Revoir : le zoom ne bouge pas
pendant une jambe ; le bateau est au tiers avant ; le film dure 150 s ± 8 s
(chronomètre) ; la voix commence par « L'expédition Berry-Mappemonde a quitté
Saint-Maur le 15 mai 2026… ». Spec `e2e/lots/f1-film.spec.js` : assert zoom
constant sur 4 s, durée mesurée (mode sans voix) entre 142 et 158 s ; captures
`01-depart`, `02-atlantique`, `03-arrivee`.

### Lot F2 — Événements `climo` et `sci`, enrichissement `wx` et `stop` (M)

**Fichiers.** `server/voyage_journal.py` (+ test), `server/ici_warm.py`
(`route_events_from_pearls`), `server/escale_api.py` (tourisme en cache),
`src/engine/journalFormat.js`, `src/engine/momentCard.js`, `src/i18n/*`.

**Étapes.** § 2.1. Les nouveaux kinds passent par le journal (mise à jour
dynamique déjà en place), puis par `cardFromJournalEntry`.

**Tests.** `test_voyage_journal.py` : régime qui tourne de 120° → `climo` ;
deux perles calmes → `climo` « calmes » ; station à 6 nm → `sci` une seule
fois ; `wx` avec durée/max.

**Recette (changement visible).** Journal (`GET /voyage/official/journal?kinds=climo,sci`)
non vide ; en Suivre, le fil de cartes montre une carte « Changement de
régime » entre Canaries et Antilles. Spec : présence d'au moins une carte
`data-kind="climo"` dans le fil ; capture.

### Lot F3 — Script du film : brut, sélection, version rédigée par Nemotron (M)

**Fichiers.** `src/engine/expeditionStory.js` (+ test), nouveau
`server/film_script.py` (+ test), `server/story_cache.py` (ns `film`),
`server/story_cascade.py` (fournisseur Token Factory, cf.
`PLAN_NEMOTRON_NEBIUS_TAVILY.md` lot L1), `server/main.py` (route
`GET /voyage/official/film?lang=fr&seconds=150`).

**Étapes.** § 2.2 et § 2.3. Réponse : `{chapters:[{id, tA, tB, text, events:[{id, charIdx, card}]}], source: "rules"|"nemotron", chars, targetSeconds}`.
Le client (`useReplay`) consomme ce plan ; sans API, il construit le brut
en local (`expeditionStory.js`) pour tenir debout seul.

**Tests.** Python : longueur bornée, toutes les balises présentes, aucun
nombre nouveau (fixture avec un faux LLM qui triche → repli brut), cache. JS :
brut ≤ 2 400 caractères, connecteurs jamais deux fois de suite, événements
ancrés à un index valide.

**Recette (changement visible).** Suivre → Revoir : le texte lu contient le
tronçon route, chaque escale, un coup de vent daté avec sa force, un
changement de régime ; « Source du récit : Nemotron (Token Factory) » ou
« règles » dans la barre film ; bascule brut / rédigé. Spec : le sous-titre
du chapitre 1 contient « Saint-Maur » et « La Rochelle » ; capture.

### Lot F4 — Bulle événement sur le bateau (S)

**Fichiers.** nouveau `src/components/EventBubble.jsx` (+ test contrat),
`src/map/MapSceneController.js` **par extrait** (`syncMarkers`, marqueur
principal), `src/index.css` (mode clair), `src/hooks/useReplay.js`,
`src/components/MomentCards.jsx` (bulle aussi hors film, § 3).

**Tests.** Contrat : la bulle suit le marqueur (`popup.getLatLng()` = bateau
après `update`), une seule bulle à la fois, minimum 3 s.

**Recette (changement visible).** Pendant le film, chaque événement lu ouvre
une bulle depuis le bateau (flèche sur le bateau), avec titre, faits, liens ;
la carte NOW de la sidebar montre le même texte. Spec : `data-testid="event-bubble"`
visible ≤ 1 s après le début de la phrase d'événement (mode sans voix : à la
date), capture `01-bulle-coup-de-vent`, `02-bulle-escale`.

### Lot F5 — Version anglaise et réglages pour la vidéo (S)

**Fichiers.** `src/i18n/en.js`, `server/film_script.py` (lang), barre film
(bouton « Plein écran film » qui masque les sidebars — **sans les retirer** :
un bouton pour revenir), `docs/HACKATHON_DEVPOST_SOUMISSION.md` § vidéo.

**Recette.** Langue EN : le film se lit en anglais, 150 s ; « Plein écran
film » cache les panneaux, `Échap` les rend. Capture plein écran à
mi-parcours (c'est le plan de la vidéo de soumission).

## 6. Ce que le porteur verra à la fin

Un clic sur **Revoir l'expédition** : la carte se cale sur Saint-Maur, la voix
raconte le départ, le bateau roule jusqu'à La Rochelle puis navigue ; à
chaque escale, coup de vent, changement de régime ou station croisée, une
bulle s'ouvre sur le bateau pendant que la voix le dit ; le zoom ne saute pas ;
au bout de 2 min 30, le bateau est à sa position d'aujourd'hui et la bulle
« Aujourd'hui » donne sa vitesse (ou « à quai ») et sa prochaine escale.

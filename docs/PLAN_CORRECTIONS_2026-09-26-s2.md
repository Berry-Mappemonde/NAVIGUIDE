# Plan — Corrections de la revue du 26 septembre (session 2) : lots RE1 → RE7

Version **1.0** — 26 septembre 2026. Le porteur a recetté dans Chrome la pile
#269 → #322 (41 PR ouvertes, pile linéaire) : 48 items cochés sur 154 (dont 32
par le bot), **8 KO du porteur, tous nouveaux** depuis la session précédente
(2026-09-23T22:32:34Z), plus une **revue globale du discours du film**
(7 884 mots, ~52 minutes : « le journal brut déversé »), avec un discours
alternatif en référence. Ce plan transforme ces 8 KO 🆕 et la revue globale en
lots correctifs RE1 → RE7, à enchaîner par `infra/agents/run_lots.py`. Les
54 KO du bot ont déjà été lus par les plans précédents
(`PLAN_CORRECTIONS_2026-09-23.md` § 1–§ 3) : ils ne sont **pas** replanifiés
ici ; seuls ceux qui recoupent un KO 🆕 sont cités en appui.

**Prérequis.** Les lots RE partent de `main` **après merge de la pile
#269 → #322** (merger la PR de tête #322 suffit, pile linéaire — la décision
reste au porteur). Les ancres `fichier:ligne` ci-dessous sont lues sur la tête
de pile (`fix/lot-rc9-journal-eta-repoll`, PR #322) : ce sera l'état de `main`
après merge. Quand un constat vient d'une autre branche (RD8), c'est dit.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4).
- **Rien de superflu à l'écran** (REGLES § 1) : un bouton visible marche ou
  n'existe pas ; un état inactif est grisé ; une pilule qui ne peut rien faire
  n'est pas affichée.
- **Aucun chiffre produit par un LLM** ; le récit du film puise dans les faits
  du journal des moments ; champ inconnu = **silence**, jamais un gabarit
  (« station croisée : Station croisée » est exactement la faute à bannir).
- **La demande la plus récente du porteur l'emporte** : le démarrage en
  Simulation + Cinéma (26 sept.) remplace le « démarrage en Suivre » de RD5
  (23 sept.) — voir § 2, décision D1.
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF. Plus **Revoir l'expédition** en Suivre : priorité.

## 1. Revue par PR (cases du porteur, verdict du réviseur de nuit)

48 / 154 cochés (porteur 16, bot 32). Les KO bot déjà lus par un plan
précédent ne sont pas replanifiés ; la colonne « Suite » ne cite que ce qui
appartient à ce plan.

| PR | Lot | Porteur | KO 🆕 du porteur | Bot (rappel) | Suite |
|---|---|---|---|---|---|
| #269 | RB1 | 0/4 — pas vu | — | rien | recette au prochain batch |
| #270 | RB2 | 0/5 — pas vu | — | rien | — |
| #271 | RB3 | 0/3 — pas vu | — | rien | — |
| #272 | RB4 | 0/5 — pas vu | — | rien | — |
| #273 | RB5 | 0/4 — pas vu | — | 2 non vérifiables (audio) | — |
| #274 | RB6 | 0/3 — pas vu | — | 1 non vérifiable (audio) | — |
| #275 | RB7 | 0/2 — pas vu | — | 2 KO : `members: 0`, pas de fourchette | déjà lu (plan du 23, RD4/RC7/RC9) ; persiste → **RE5** |
| #276 | RB8 | 0/3 — pas vu | — | 2 non vérifiables | — |
| #277 | R8a | 0/3 — pas vu | — | rien | — |
| #278 | R8b | 0/4 — pas vu | — | rien | — |
| #279 | R8c | 3/5 | — | rien | — |
| #281 | R9a | 3/3 ✅ | — | rien | — |
| #284 | R9b | 0/4 — pas vu | — | 1 KO : liste Journal à 0 entrée | déjà lu (RD4/RC9) ; lisibilité → **RE3** |
| #285 | R9c | 0/5 — pas vu | — | 2 KO : saut d'escale, bulle « Escale · 15 mai » | déjà lu (RC4/RC5, RD4, RD7) |
| #286 | R10a | 0/3 — pas vu | — | rien | — |
| #287 | R10b | 0/3 — pas vu | — | rien | — |
| #289 | R10c | 0/1 — pas vu | — | rien | — |
| #290 | R10d | 0/6 — pas vu | — | 1 KO : bouton resté « Recalculer l'itinéraire » | déjà tranché (plan du 23 § 3) ; re-vu par le bot → § 3, à re-vérifier à la recette RE |
| #291 | N1 | 0/5 — pas vu | — | rien | — |
| #292 | N2 | 0/4 — pas vu | — | rien | — |
| #293 | N3 | 0/2 — pas vu | — | 1 KO : plan-review sans jambes sur le poste | déjà lu (RD4/RC8) |
| #294 | N4 | 0/2 — pas vu | — | rien | — |
| #295 | D0 | 0/5 — pas vu | — | rien | — |
| #296 | RC1 | 0/3 — pas vu | — | 1 non vérifiable (poste) | — |
| #297 | RC2 | 0/3 — pas vu | — | rien | — |
| #298 | RC3 | 2/2 ✅ | — | rien | — |
| #299 | RC4 | 0/3 — pas vu | — | 1 KO : sous-titre sans paires | déjà lu (RC5) |
| #302 | RC5 | 0/3 — pas vu | — | 7 KO : 502 climato (poste), film ~121 s, nom du bateau | déjà lu (plan du 23 § 1/§ 3, RD3, RD7) |
| #309 | RD1 | 6/6 (porteur 2) | **un clic sur Saint-Maur ou La Rochelle dans la liste d'escales ouvre la fiche Fort-de-France** | 3 KO (fiche Ici, curseur, 524) | → **RE2** |
| #310 | RD2 | 6/6 🤖 | — | 2 KO console (404/524, poste) | env. § 3 |
| #311 | RD3 | 4/4 | — | 2 KO (coup de vent 50, eta 404) | déjà lu ; env. § 3 |
| #312 | RD4 | 2/4 | **l'app doit s'ouvrir en Simulation, mode Cinéma, vue monde dézoomée** ; **lignes du journal noires sur fond sombre** | 4 KO (fourchette, journal vide, 524) | → **RE1** (accueil), **RE3** (lisibilité), **RE5** (fourchette) |
| #313 | RD5 | 4/7 | **changer la date de départ dans la barre de lecture ne met pas à jour la ligne « 14 220 nm · j112 · … »** | 2 KO console (502/524, poste) | → **RE4** |
| #314 | RD6 | 4/4 | — | 2 KO (Iroise absent : données du poste ; console) | env. § 3 |
| #315 | RD7 | 4/5 | **les boutons 2:30 et 3:00 sont visibles même quand ils ne devraient pas l'être** | 1 KO console (poste) | → **RE3** ; revue globale du discours → **RE7** |
| #317 | RD8 | 0/4 | **pas de flèches de vent, erreurs console** | 5 KO : tuiles 404 (route absente du backend BI du poste) | → **RE6** + § 3 (déploiement) |
| #318 | RD9 | 5/5 (porteur 3) | **Suivre → Simulation : le Cinéma doit se décliquer et les deux panneaux s'ouvrir** | 4 KO (revue vide sur le poste, console) | → **RE1** |
| #319 | RC6 | 2/2 🤖 | **en Suivre, la liste des escales du panneau droit doit être informative, pas cliquable** | 1 KO console (poste) | → **RE2** |
| #320 | RC7 | 0/3 — pas vu | — | 3 KO : `members: 0`, journal vide, console | déjà lu ; persiste → **RE5** |
| #321 | RC8 | 3/3 🤖 | — | 1 KO console (poste) | — |
| #322 | RC9 | 0/3 — pas vu | **déjà évoqués : Simulation s'ouvre monde dézoomé + Cinéma ; les ETA d'escale ne sont pas vues ; journal noir sur fond sombre** | 10 KO (`members: 0`, journal, console, advice 400) | → **RE1**, **RE3**, **RE5** |

## 2. Revue générale (la voix du porteur, point par point)

La revue globale porte sur **le discours que la voix lit** (`/voyage/official/film`,
style brut, sans durée) : 9 chapitres, 7 884 mots, ~52 minutes. « RD7 a bien
retiré “la mer porte le bateau”, mais l'a remplacé par la lecture intégrale du
journal, sans sélection, sans noms, sans dédoublonnage, sans géographie ni
chronologie. » Les onze points, avec la cause lue dans le code (tête de pile
#322) :

1. **Le journal brut déversé** (~200 items sur La Rochelle → Ajaccio) : sans
   budget coché (mode par défaut RD7), `build_raw_from_moments`
   (`server/film_script.py:1564`) déroule **tous** les moments de la fenêtre,
   sans tri ni plafond par jambe. → **RE7**.
2. **« station croisée : Station croisée » ×240** : gabarit
   `film_script.py:1473` avec un titre par défaut « Station croisée »
   (`server/moment_journal.py:201-202`) : le type est lu à la place du nom.
   La règle RD7 « champ inconnu = silence » n'est pas appliquée ici. → **RE7**.
3. **Doublons en rafale** (« Gran Roque » ×8, « Cocorite » ×9…) : la
   déduplication de `pick_changes` (`film_script.py:1436-1449`) ne porte que
   sur l'`id` du changement, jamais sur le **nom** au fil de la jambe ; la
   marina ressort à chaque pas de temps (`film_script.py:1480`). → **RE7**.
4. **Phrases fausses** : « entrée dans Ports d'entrée : Les Sables-d'Olonne »
   (le titre du moment `moment_journal.py:191` est injecté tel quel dans le
   gabarit « entrée dans {title} » `film_script.py:1471`) ; « entrée dans
   Entrée dans Zone économique exclusive espagnole » (même mécanique, titre
   déjà verbalisé). → **RE7** (vocabulaire : « à portée de », « entrée dans
   les eaux… » une fois).
5. **L'absence de donnée racontée** : « Aucun port d'entrée officiel n'est
   connu pour… » ×58 (`moment_journal.py:187`, repris par le film). Sans nom,
   pas de phrase. → **RE7**.
6. **Données brutes lues à la lettre** (IUCN Unassigned, Overlapping claim,
   coquilles de la source, couloirs en anglais posés en fin de jambe par la
   revue RD9, `film_script.py:848` `_append_review_sentences`) : nettoyage des
   libellés avant déclamation. → **RE7**.
7. **Chronologie qui recule** : une fenêtre de chapitre commence à
   l'**arrivée** à l'escale de départ (`_windows`, `film_script.py:1049` :
   `tA = iso` de l'escale `from`), mais la phrase de départ cite la date de
   **sortie** (arrivée + jours à quai, `_depart_towards`,
   `film_script.py:1117`) : « le 18 mai, départ vers Ajaccio » puis trente
   lignes datées du 15 mai. → **RE7**.
8. **Géographie** (Monaco, Bastia, la Sardaigne sur Ajaccio → Fort-de-France) :
   les « voisins à portée » d'un large rayon entrent au journal puis au film
   sans filtre de distance à la route. → **RE7** (tri par importance et par
   position sur la route).
9. **Sauts d'avion jamais dits** : `_windows` ne connaît pas le véhicule de la
   jambe (aucun champ avion dans `film_script.py:1049-1091`) ; l'auditeur
   entend un bateau qui se téléporte. → **RE7**.
10. **Dernier chapitre sans destination ni arrivée** : la dernière fenêtre a
    `to: None` (`film_script.py:1072-1083`) et rien ne la referme (« Le
    26 septembre, station croisée » en guise de fin). → **RE7** (« aujourd'hui,
    le bateau est à… »).
11. **Rien de ce que le porteur voulait entendre** (cyclones nommés, stations,
    aires protégées, cultures d'escale) : les faits existent dans les moments
    mais la sélection ne les met pas en avant. → **RE7**.

Le **discours alternatif** du porteur (dans la revue, avec l'astérisque sur
les dates Papeete/Wallis) est **la référence de recette** de RE7 : mêmes
données, dédoublonnées, dans l'ordre de la route.

**Décisions actées :**

- **D1 — Écran d'accueil.** « L'application doit s'ouvrir sur le mode
  simulation en mode cinéma et en vue monde dézoomée » (KO #312, répété
  #322). Cette demande du 26 sept. **remplace** le « démarrage en Suivre » de
  RD5 (revue du 23 sept., case cochée par le bot le 26) : la demande la plus
  récente l'emporte. RD5 reste valable pour tout le reste (dates réglables,
  année à l'horloge). → **RE1**.
- **D2 — Bascule des modes.** « Quand on passe du mode suivre au mode
  simulation, le mode Cinéma doit se décliquer et les panneaux droit et
  gauche doivent s'ouvrir » (KO #318). Lecture combinée avec D1 : au
  **chargement**, l'app est en Simulation + Cinéma + monde dézoomé (mode
  vitrine) ; dès que l'utilisateur **bascule** de Suivre vers Simulation, le
  Cinéma se décoche et les deux panneaux s'ouvrent (mode travail). L'entrée
  en Suivre garde son comportement actuel (Cinéma). → **RE1**.
- **D3 — Liste des escales.** « En mode suivre, on ne devrait pas pouvoir
  cliquer sur les escales dans la liste des escales du sidebar droit, elles
  devraient être là en mode informatif seulement » (KO #319). Le clic-ligne
  « déplacer le curseur » (recette RD1) disparaît donc **en Suivre** ; il
  reste en Simulation, où le curseur appartient à l'utilisateur. → **RE2**.

## 3. Ce qui est reporté ou fondu, et pourquoi

- **Globe (lots à venir G1, G4, G5)** : les corrections de cette revue valent
  aussi pour la vue globe — fondues dans leurs prompts (« Constat de la revue
  du 26 sept. ») : **G1** (caméra initiale = monde dézoomé, parité RE1) ;
  **G4** (repli des couches climato si les tuiles ne répondent pas, parité
  RE6) ; **G5** (liste des escales informative en Suivre et fiche = escale
  cliquée, parité RE2). Aucun autre lot à venir (G0, G2, G3, G6, G7, H1) ne
  couvre un constat de cette revue.
- **Tuiles climatologie 404 sur le poste (#317)** : le bot l'a prouvé par
  sonde directe — la route `…/climatology/{kind}/tiles/…` n'existe pas sur le
  backend BI que le poste interroge : le backend déployé est celui de `main`,
  la PR #317 (qui l'ajoute) n'est pas mergée. Ce n'est **pas** un défaut du
  code de RD8 : au merge, `deploy.yml` déploiera aussi le backend (dit dans la
  PR #317, « Hors périmètre »). Le lot **RE6** ajoute le repli côté client
  pour que la couche ne soit plus jamais muette pendant ce genre de décalage.
- **502 / 524 / `ERR_CONNECTION_CLOSED` sur `/bi/climatology/*`, `/ici`,
  `/voyage/official/*` (KO bot récurrents, ~185 erreurs par écran)** :
  environnement du poste de recette / VPS sous charge de préchauffage — déjà
  tranché au plan du 23 (§ 3), rien de neuf à planifier. Si ces erreurs
  survivent au batch RE en prod, c'est un ticket infra.
- **« Demander conseil » (#290, KO bot re-vu ce 26 sept.)** : le libellé est
  dans la pile (`src/i18n/fr.js:508`, rendu `SimulationPanel.jsx:202`, jugé le
  23) ; le bot l'a revu absent **sur le même poste pas à jour**. À re-vérifier
  à la recette du batch RE sur le build de la pile mergée ; si le bouton dit
  encore « Recalculer l'itinéraire », ouvrir un lot au prochain cycle.
- **Dates Papeete / Wallis absentes du récit** : l'astérisque du porteur le
  dit lui-même — elles viennent de l'ancienne version ; sur le poste, l'ETA
  du voyage semé met Papeete au 14 octobre. La **clôture** de la dernière
  jambe est dans RE7 ; l'exactitude des dates du voyage semé appartient à RD4
  (PR #312, codée, en recette) — pas de nouveau lot.
- **Cases non cochées sans KO (35 PR « pas vu »)** : revue à la volée non
  terminée, pas des refus — elles restent à cocher au prochain passage ;
  aucune n'est orpheline d'un plan.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour App.jsx et MapSceneController.js). « Recette » = ce que le
porteur voit dans Chrome, par écran. Ancres `fichier:ligne` = tête de pile
#322 (= `main` après merge), sauf mention RD8 (branche
`feat/lot-rd8-tuiles-climato`). Pile linéaire RE1 → RE7.

### RE1 — Accueil en Simulation + Cinéma + monde ; la bascule Suivre → Simulation décoche le Cinéma et ouvre les panneaux (M)

Cause racine : (a) accueil — `src/App.jsx:171` (`useState(VIEW_SUIVRE)`,
posé par RD5), `:173` (`cinemaMode` démarre `false`), `:165-166` (les deux
panneaux démarrent ouverts) : l'app s'ouvre en Suivre, panneaux ouverts, hors
Cinéma — le porteur veut Simulation + Cinéma + monde dézoomé (D1). La carte
naît bien en vue monde (`src/map/MapSceneController.js:197`, `zoom: 2`) mais
le suivi live la recadre sur le bateau (`MapSceneController.js:931`,
`setView([lat, lon], 6.5)`). (b) bascule — `selectView`
(`src/App.jsx:985-1022`) : la branche `next === VIEW_SUIVRE` (`:993-1003`)
**entre** en Cinéma (ferme les panneaux, `setCinemaMode(true)`), mais la
branche inverse (`:1004-1009`, vers Simulation/Tracer) ne touche ni au Cinéma
ni aux panneaux : en venant de Suivre (donc Cinéma actif), la Simulation
reste en Cinéma, panneaux fermés — KO #318. `leaveCinema` existe déjà
(`App.jsx:961-967`) et restaure les panneaux.

Fichiers : `src/App.jsx` PAR EXTRAIT
(`rg -n "VIEW_SUIVRE|cinemaMode|selectView|leaveCinema|recaptureBoat"`),
`src/map/MapSceneController.js` PAR EXTRAIT (`rg -n "zoom: 2|6.5"`, lecture),
`src/hooks/` si un hook d'état de vue existe, `src/i18n/fr.js`,
`src/i18n/en.js` (si libellé), tests associés.

Étapes :
1. État initial : vue `VIEW_SIMULATION`, `cinemaMode` vrai, les deux panneaux
   fermés (mêmes effets que `toggleCinema` à l'allumage, sans clic) ; la
   carte reste en vue monde dézoomée (zoom initial 2) — aucun recadrage
   automatique sur le bateau tant que l'utilisateur n'a rien demandé.
2. Bascule Suivre → Simulation : appeler `leaveCinema()` (Cinéma décoché,
   bouton relevé) et ouvrir les **deux** panneaux — quel que soit l'état
   sauvegardé par `cinemaSavedRef` (le porteur veut les voir ouverts).
3. L'entrée en Suivre garde le comportement actuel (Cinéma + recadrage) ;
   Tracer garde le sien ; le bouton Cinéma manuel garde le sien.
4. Tests : au montage, la vue est Simulation et le Cinéma actif ; après
   bascule Suivre → Simulation, `cinemaMode` faux et les deux panneaux
   ouverts ; la vue initiale de la carte reste monde (pas de recadrage au
   chargement).

Recette (visuelle) :
- Recharger l'application → **tu dois voir** la carte monde entière
  (dézoomée), le bouton **Simulation** enfoncé, le bouton **Cinéma** enfoncé,
  les deux panneaux fermés, la barre film seule en bas.
- Clique **Suivre l'expédition**, puis reviens sur **Simulation** → **tu dois
  voir** le bouton Cinéma se **relever** et les panneaux gauche **et** droit
  s'ouvrir d'eux-mêmes.
- Suivre : comportement inchangé (Cinéma, caméra sur le bateau).

### RE2 — Liste des escales : informative en Suivre ; la fiche ouverte est celle de l'escale cliquée (S)

Cause racine : chaque ligne de la liste (panneau droit, encadré Expédition)
est un bouton (`src/components/EscaleLegend.jsx:15-35`, `onClick` →
`onSeek`), câblé `ToolsSidebar.jsx:213` → `handleSidebarSeek`
(`src/App.jsx:1407-1411` : `setUserPreview(true)` + `playback.seek`) — actif
en Suivre comme ailleurs, alors que le porteur veut la liste **informative en
Suivre** (D3). Fiche Fort-de-France : le seul chemin d'ouverture automatique
est `useEscaleSheetState.js:70-81` — à quai (`atQuay`), la fiche de l'escale
la plus proche (≤ 5 nm) de `clockSample` s'ouvre seule (câblage
`src/App.jsx:526-531`) ; après le clic-ligne en Suivre, l'aperçu et
l'échantillon d'horloge divergent du curseur (KO bot #309 : le curseur reste
sur la jambe live) et la fiche ouverte n'est pas celle du nom cliqué —
**reproduire sur poste** le cas exact « clic Saint-Maur → fiche
Fort-de-France » avant de corriger, ne pas coder à l'aveugle.

Fichiers : `src/components/EscaleLegend.jsx`,
`src/components/ToolsSidebar.jsx` PAR EXTRAIT (`rg -n "EscaleLegend"`),
`src/App.jsx` PAR EXTRAIT (`rg -n "handleSidebarSeek|useEscaleSheetState"`),
`src/hooks/useEscaleSheetState.js`, tests associés.

Étapes :
1. En Suivre, les lignes d'escales ne sont **plus des boutons** : pas de
   curseur main, pas de survol cliquable, aucune action au clic — la liste
   affiche nom, distance, date, jours à quai, fourchette, rien d'autre. En
   Simulation, le clic-ligne garde son effet actuel (déplacer le curseur).
2. Reproduire « clic Saint-Maur / La Rochelle → fiche Fort-de-France » ;
   corriger la cause constatée (fiche auto ouverte pour une autre escale que
   celle voulue) ; documenter fichier:ligne dans la PR. La règle : une fiche
   qui s'ouvre porte **toujours** le nom de l'escale que l'utilisateur a
   désignée (drapeau cliqué), ou de l'escale à quai — jamais d'une troisième.
3. Tests : en Suivre, la ligne d'escale n'est pas un bouton (aucun gestionnaire
   de clic) ; en Simulation, le clic déplace le curseur ; la fiche auto ne
   s'ouvre que pour l'escale à quai la plus proche.

Recette (visuelle) :
- Suivre, panneau droit, liste des escales : le pointeur ne devient **pas**
  une main sur les lignes ; cliquer Saint-Maur ou La Rochelle → **rien ne
  s'ouvre**, le curseur ne bouge pas, aucune fiche Fort-de-France.
- Simulation, même liste : cliquer Ajaccio → le curseur de la barre film se
  place sur Ajaccio, comme avant.
- Suivre, panneau gauche ouvert, cliquer le **drapeau** d'Ajaccio sur la
  carte → la fiche **Ajaccio** (et pas une autre) en tête de la section Ici.

### RE3 — Lisibilité : lignes du Journal jamais noires sur fond sombre ; pilules 2:30 / 3:00 seulement quand le film peut se lancer (S)

Cause racine : (a) journal — chaque ligne est un bouton en `text-inherit`
(`src/components/IciMaintenant.jsx:64`) : la couleur dépend du parent, et la
seule règle explicite est celle du thème clair
(`src/index.css:328-330`, `color: rgb(30 41 59)` — presque noir) ; selon le
thème et le conteneur, les lignes sortent **noires sur fond sombre** (KO #312
et #322, vu sur le poste). Aucune couleur n'est posée pour le thème sombre.
(b) pilules — le bloc `film-duration`
(`src/components/SimulationFilmBar.jsx:463-486`) est rendu dès que `replay`
existe, c'est-à-dire partout en Suivre avec horloge officielle
(`src/App.jsx:862`) ; pendant le film (`replay.active`) les pilules restent
affichées, seulement estompées (`disabled:opacity-30`) — le porteur les voit
« même quand ils ne devraient pas être visibles » (KO #315, capture à
l'appui). Règle REGLES § 1 : un bouton qui ne peut rien faire n'est pas
affiché.

Fichiers : `src/components/IciMaintenant.jsx`, `src/index.css`,
`src/components/SimulationFilmBar.jsx` PAR EXTRAIT
(`rg -n "film-duration|replay-controls"`), tests associés.

Étapes :
1. Poser une couleur **explicite** sur les lignes du journal dans les deux
   thèmes : claire sur fond sombre (même teinte que les autres textes de
   l'encadré), foncée sur fond clair (règle existante conservée) ; vérifier
   dans Chrome, thème sombre puis clair, qu'aucune ligne n'est noire sur
   sombre ni blanche sur clair.
2. Les pilules 2:30 / 3:00 ne sont rendues **que** lorsque le bouton
   « Revoir l'expédition » est visible et que le film n'est **pas** lancé
   (`!replay.active`) ; pendant le film (bouton Stop affiché) et dans tout
   autre état, elles disparaissent — pas d'estompage.
3. Tests : la classe/règle de couleur du journal existe pour les deux
   thèmes ; le bloc des durées n'est pas rendu quand le film est actif ;
   il l'est à côté du bouton de lancement.

Recette (visuelle) :
- Suivre, panneau gauche, onglet Journal, thème sombre : **tu dois lire**
  chaque ligne (texte clair sur fond sombre) ; passe en thème clair → texte
  foncé sur fond clair.
- Suivre, barre film : **2:30** et **3:00** visibles à côté de « Revoir
  l'expédition », aucun enfoncé ; lance le film → les deux pilules
  **disparaissent** (il reste Stop et la jauge) ; Stop → elles reviennent.
- Simulation et Tracer : jamais de pilules 2:30 / 3:00.

### RE4 — La date de départ de la barre pilote la ligne d'état (S)

Cause racine : le champ date de la barre (Suivre, à côté de « Revoir
l'expédition », `src/components/SimulationFilmBar.jsx:428-436`,
`replay-departure`) ne nourrit que le **script du film** : `useReplay.js`
n'utilise `t0` que dans la requête du film et le contrôle du texte
(`src/hooks/useReplay.js:320`, `:342`, `:356-367`). La ligne d'état de la
barre (`clock-line`, `SimulationFilmBar.jsx:221-232` : « 14 220 nm · j112 ·
26 sept. 2026 · 09:14 UTC · Restants 1 985 nm · ETA 11 j · 8.3 kt · TWA 159° ·
LIVE · climatologie ») est bâtie sur l'horloge officielle, elle-même remise au
départ par défaut à chaque entrée en Suivre (`src/App.jsx:993-995`,
`voyage.setStartAt(DEFAULT_START_AT)`). Changer la date ne recalcule donc
**rien** de visible dans la ligne — KO #313.

Fichiers : `src/components/SimulationFilmBar.jsx` PAR EXTRAIT
(`rg -n "clock-line|replay-departure"`), `src/hooks/useReplay.js`,
`src/App.jsx` PAR EXTRAIT (`rg -n "clockLine|setStartAt|replayControls"`),
`src/engine/voyageClock.js` (lecture), tests associés.

Étapes :
1. Quand la date de départ du champ de la barre change, la ligne d'état
   affichée est recalculée pour ce départ : jour de voyage (« j… »), dates,
   distances restantes et ETA dérivés de la même horloge décalée — une seule
   vérité à l'écran, jamais la ligne de l'ancien départ à côté du film du
   nouveau.
2. Le décalage reste **local à Suivre / Revoir** (RD5 : indépendant du t0 de
   la Simulation) ; remettre la date par défaut restaure la ligne LIVE
   actuelle ; aucune date inventée : tout dérive de la date choisie et des
   durées réelles des jambes.
3. Tests : changer le t0 du replay change le libellé de la ligne d'état
   (année et jour de voyage) ; la remise au défaut restaure la ligne
   d'origine ; le t0 de la Simulation ne bouge pas.

Recette (visuelle) :
- Suivre : règle la date de la barre sur le 15/05/2025 → **tu dois voir** la
  ligne d'état changer (année 2025 dans la date, jour de voyage recalculé) —
  pas seulement le sous-titre du film.
- Remets 15/05/2026 → la ligne redevient celle d'aujourd'hui (LIVE).
- Simulation, panneau droit : la date de départ de la Simulation n'a pas
  bougé.

### RE5 — Fourchette d'arrivée : l'ensemble aboutit, ou la réponse dit pourquoi (M)

Cause racine : le porteur ne voit toujours pas « arrivée entre le … et
le … » (KO #322 ; sondes bot #275, #320, #322 : `GET /voyage/official/eta` →
200, `members: 0`, `p10/p50/p90: null` après plusieurs minutes). Lu sur la
tête de pile : `GET /voyage/official/eta`
(`server/voyage_api.py:1144-1152`) relance le warm tant que le cache est vide
(RC9, `_kick_official_eta`, `voyage_api.py:935-983`) ; le calcul
(`compute_eta`, `server/ensemble_eta.py:437`) sonde la jambe restante **tous
les 60 nm** (`sample_leg_points`, `ensemble_eta.py:260`,
`MAX_POINT_NM = 60.0` `:33`) et fait **un appel API ensemble par sonde**
(`fetch_point_members`, boucle `:474-487`) : sur Cayenne → Papeete
(~4 600 nm restants), ≈ 75 appels à `ensemble-api.open-meteo.com` par cycle ;
chaque échec est avalé en `log.info` (`:483`) et l'ensemble vide retourne
`empty` (`:488-489`) — la réponse HTTP reste 200 `members: 0` **sans jamais
dire pourquoi**. L'hypothèse la plus probable (limitation / rejet de l'API
sous cette rafale) est à **confirmer sur poste** par les logs avant de
corriger — ne pas coder à l'aveugle.

Fichiers : `server/ensemble_eta.py`, `server/voyage_api.py` PAR EXTRAIT
(`rg -n "_kick_official_eta|official/eta"`),
`server/tests/test_ensemble_eta.py`, `server/tests/test_voyage_api.py`.

Étapes :
1. Reproduire sur poste (logs du warm) et noter la cause exacte des membres
   à zéro (rejet API, réseau, autre) dans la PR.
2. Plafonner les sondes par jambe (p. ex. ≤ 12, réparties sur la jambe,
   premier et dernier point conservés) : l'intégration par membre
   (`_member_at` interpole déjà au plus proche) garde sa précision de
   fourchette, le nombre d'appels API tombe d'un ordre de grandeur.
3. La réponse de l'ETA officielle porte un champ d'état honnête quand
   `members: 0` : dernière tentative, raison (« ensemble indisponible »,
   « hors horizon »), prochaine relance — jamais une date inventée (la règle
   du module reste : sans membres, pas de fourchette).
4. Espacer les relances en échec (repli progressif) au lieu de marteler à
   chaque GET.
5. Tests : fixture d'API ensemble qui échoue → réponse avec `members: 0` et
   la raison ; fixture qui répond → `members > 0`, fourchette bornée ; le
   nombre de sondes par jambe est plafonné.

Recette (visuelle) :
- Poste relancé (script de recette), Suivre, liste des escales : sous la
  prochaine escale, **tu dois voir** « arrivée entre le … et le … » (deux
  dates proches) au plus quelques minutes après le lancement, sans recharger.
- Si l'ensemble est réellement injoignable : **rien** sous l'escale (pas de
  date inventée) — et la PR montre où lire la raison.

### RE6 — Couches climatologie : jamais muettes — repli sur la couche globale si les tuiles échouent (S)

Cause racine : sur la branche RD8 (`feat/lot-rd8-tuiles-climato`),
`loadTiles` (`src/layers/useClimatologyLayer.js:157-181`) avale chaque échec
de tuile en collection vide (`catch → []`, `:172-175`) : quand le backend BI
ne connaît pas la route des tuiles (poste du 26 sept. : sonde bot en 404,
route livrée par la PR #317 non déployée), la couche affiche « roses 0 ·
Atlas muet » et **aucune flèche** (KO #317), alors que l'ancienne route
globale `.geojson` existe toujours côté backend et que `atlasLayerUrl` est
conservé pour l'export.

Fichiers : `src/layers/useClimatologyLayer.js`, `src/utils/atlasPoint.js`
(lecture), `src/utils/atlasPoint.test.js`, `e2e/lots/` (spec du lot), tests
associés.

Étapes :
1. Si **toutes** les tuiles d'une passe échouent en erreur HTTP (hors
   annulation) pour une couche allumée, recharger la couche par l'ancienne
   route globale (`atlasLayerUrl`, espacement 4°) : des flèches valent mieux
   que rien ; le bandeau de la couche dit la source réellement employée.
2. Au mouvement de carte ou au changement de mois suivant, retenter d'abord
   les tuiles (le repli n'est jamais définitif).
3. Ne rien changer au rendu ni au chemin nominal des tuiles (RD8) ; le repli
   ne se déclenche que sur échec total.
4. Tests : fixture où les tuiles répondent en erreur → la couche charge la
   route globale et des features existent ; fixture où les tuiles répondent →
   aucun appel à la route globale.

Recette (visuelle) :
- Suivre, pastille Vent allumée, poste dont le backend n'a pas les tuiles :
  **tu dois voir** des flèches de vent quand même (maille 4°) et un bandeau
  qui dit la source — plus jamais « roses 0 · Atlas muet ».
- Poste avec backend à jour : les flèches se densifient au zoom comme prévu
  par RD8, rien ne change.

### RE7 — Le discours du film : un récit, pas le journal déversé (M, après RE5 dans la pile)

Le porteur : « c'est un KO sur la PR de RD7 (le film), avec ce texte comme
référence de ce qu'on attend » — son discours alternatif (§ 2) est la
référence de recette. Onze défauts, six règles.

Cause racine (lue sur la tête de pile #322) : `server/film_script.py` —
gabarits `change_sentence` (`:1452-1509`) : « entrée dans {title} » (`:1471`)
double le verbe quand le titre du moment est déjà verbalisé
(« entrée dans Entrée dans ZEE… ») et lit les types de moments comme des
noms ; « station croisée : {title} » (`:1473`) avec titre par défaut
« Station croisée » (`server/moment_journal.py:201-202`) → « station
croisée : Station croisée » ×240 ; « marina croisée : {name} » (`:1480`) émis
à chaque pas de temps sans dédoublonnage par nom (« Gran Roque » ×8) — la
déduplication de `pick_changes` (`:1436-1449`) ne porte que sur l'`id` ;
« Aucun port d'entrée officiel n'est connu… » (`moment_journal.py:187`) et
« Ports d'entrée : {nom} » (`:191`) racontent l'absence de donnée et un
libellé de liste comme des événements ; fenêtres de chapitre `_windows`
(`:1049-1091`) : `tA` = **arrivée** à l'escale de départ, mais la phrase de
départ (`_depart_towards`, `:1117-1134`) cite la date de **sortie** (arrivée
+ quai) → chronologie qui recule ; aucune notion de véhicule dans les
fenêtres → sauts d'avion muets ; dernière fenêtre `to: None` (`:1072-1083`)
jamais refermée ; libellés de la revue et des sources déclamés bruts
(`_append_review_sentences`, `:848` ; « IUCN Unassigned », couloirs en
anglais).

Fichiers : `server/film_script.py`, `server/moment_journal.py`,
`server/tests/test_film_script.py`, `server/tests/test_moment_journal.py`,
`src/i18n/fr.js`, `src/i18n/en.js` (si libellés côté client).

Étapes (les six règles du porteur, dans ses mots) :
1. **Un événement = une fois** : dédoublonner par **nom** (port, marina,
   zone, station) sur toute la jambe, pas par pas de temps ni par id.
2. **Sans nom, pas de phrase** : un moment dont le nom manque (titre égal au
   type, « Station croisée ») ou qui raconte une absence (« Aucun port
   d'entrée connu ») ne produit **aucune** phrase — silence.
3. **Trier par importance et par position sur la route** : escales et ZEE
   traversées (toujours), aires protégées et détroits, marinas quand le
   bateau passe dedans ou à côté ; les « voisins » à plus de quelques milles
   de la route ne sont pas la route (filtre de distance sur les moments
   déclamés).
4. **Vocabulaire juste** : « à portée de » ou « devant » pour un port ;
   « entrée dans les eaux <pays> » pour une ZEE, **une seule fois** par
   jambe ; couloirs traduits (« golfe de Gascogne », « détroit de
   Gibraltar ») ; libellés de la source nettoyés avant déclamation (codes
   IUCN, parenthèses techniques, anglais, coquilles connues) — nettoyage par
   règles, jamais un chiffre inventé.
5. **Chronologie stricte** dans la jambe (les événements entre l'arrivée et
   la sortie de l'escale se racontent **avant** la phrase de départ, ou la
   fenêtre commence à la sortie) ; **sauts d'avion dits explicitement**
   (« l'équipage prend l'avion pour… », « retour en avion vers… ») ; la
   **dernière jambe est fermée** : destination, arrivée, ou « aujourd'hui, le
   bateau est à… ».
6. **Chiffres arrondis et dits en toutes lettres** (déjà RD7 pour les
   distances : vérifier qu'aucune décimale ni abréviation ne subsiste) ;
   milles nautiques en mer, kilomètres à terre.
7. Tests : fixture de moments reproduisant les onze défauts (doublons,
   libellés vides, « entrée dans Entrée dans », voisins lointains, jambe
   avion, dernière jambe ouverte) → le script généré n'a **aucun** doublon de
   nom par jambe, aucune phrase sans nom, aucun « entrée dans » doublé, dit
   l'avion, ferme le dernier chapitre ; le nombre de mots du script complet
   sans budget reste sous un plafond raisonnable (ordre de grandeur du
   discours de référence, ~800 mots, pas 7 884) ; cyclone nommé avec année,
   station nommée, aire protégée nommée, fait de culture d'escale présents
   quand la fixture les porte.

Recette (visuelle) :
- Suivre, Revoir l'expédition, sans durée cochée : **tu dois entendre** un
  récit qui suit la route (départ Saint-Maur, La Rochelle, les pertuis, le
  golfe de Gascogne, Gibraltar…), chaque lieu nommé **une fois**, jamais
  « station croisée : Station croisée », jamais « Aucun port d'entrée… »,
  jamais « entrée dans Entrée dans… ».
- Au passage de la Guyane : **tu dois entendre** l'avion dit explicitement
  (aller et retour), plus aucun bateau téléporté.
- À la fin : **tu dois entendre** la dernière jambe fermée (« aujourd'hui, le
  bateau est à… »).
- Le compteur du film sans budget : un récit de l'ordre de quelques minutes,
  plus jamais ~52 minutes.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | RE1 | M | App.jsx (vue initiale, selectView, Cinéma), MapSceneController.js (lecture) |
| 2 | RE2 | S | EscaleLegend.jsx, ToolsSidebar.jsx, useEscaleSheetState.js (liste informative, bonne fiche) |
| 3 | RE3 | S | IciMaintenant.jsx, index.css, SimulationFilmBar.jsx (journal lisible, pilules) |
| 4 | RE4 | S | SimulationFilmBar.jsx, useReplay.js, App.jsx (ligne d'état pilotée par la date) |
| 5 | RE5 | M | ensemble_eta.py, voyage_api.py (sondes plafonnées, état honnête) |
| 6 | RE6 | S | useClimatologyLayer.js (repli .geojson) |
| 7 | RE7 | M | film_script.py, moment_journal.py (le récit, les six règles) — après RE5 |

Lancement : la boucle (`loop.py`) part seule au merge de la PR de ce
document, **empilée sur la pile #269 → #322** si elle n'est pas mergée (les
ancres ci-dessus ont été lues sur sa tête), depuis `main` sinon. À la main,
si besoin :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --check
caffeinate -i python3 infra/agents/run_lots.py --from RE1 --until RE7 --resume
```

Fin de batch : le poste de recette s'ouvre seul (W0) ; recette par écran ;
merge des PR dans l'ordre de la pile.

# Plan — Corrections de la revue du 22 septembre (matin) : lots RB1 → RB8

Version **1.0** — 22 septembre 2026, matin. Le porteur a recetté dans Chrome le
batch RA1 → RA8 (PR #250 → #258, poste de recette) : **22 items cochés sur 29,
0 commentaire KO dans les cases**, mais une **revue globale dense** (dictée) et
des KO du réviseur de nuit (bot) sur RA2, RA3, RA4 et RA7. Le point le plus
grave : la **régression de chorégraphie** introduite par RA4 — le trajet
Halifax ↔ Saint-Pierre-et-Miquelon, une jambe **en mer**, est devenu un trait
avion noir pointillé.

Ce plan classe tout ce que la revue a relevé en lots correctifs (RB1 → RB8) à
enchaîner par `infra/agents/run_lots.py`, dit ce qui est **fondu** dans les
lots à venir du programme (R8a, R8c, R9c, R10d — leurs prompts sont complétés
dans `docs/LOTS_ORDRE_ET_PROMPTS.md`), et note les décisions. Après RB8, la
nuit **continue avec le programme pré-rédigé jusqu'à D0** (R8a → R10d,
N1 → N4, D0).

Prérequis : la pile RA1 → RA8 est **mergée** (merger la PR de tête #258
suffit, pile linéaire) ; ce document et les prompts RB sont sur `main`
(merger sa PR) ; les agents partent de `main`.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4). Sa recette est
  la vérité : un item coché par le bot mais contredit par le porteur (Stop,
  prompt du journal) est **KO**.
- **Rien de superflu à l'écran** (REGLES § 1). La revue du 22 le répète :
  « il faut que ça soit un produit » — les cartes flottantes vont dans
  l'encadré du panneau gauche (R8c), pas de bouton Écouter dupliqué.
- **`main` (après merge RA) est le plancher** : corriger RA4 (RB1, RB8) sans
  retirer ce que RA4 a apporté (bornes de longitude, trait avion pour les
  vraies jambes avion).
- Les régressions décrites ici vivent dans la pile RA (PR #250 → #258) : les
  anchors « (RA4) » renvoient au code de cette pile, les autres à `main`.
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF. Plus **Revoir l'expédition** en Suivre : toujours la
  priorité (Devpost).

## 1. Revue par PR (cases du porteur, KO du réviseur de nuit, verdict)

### PR #250 (RA1 — pensée du modèle) — 2/2 cochés (bot), mais contredit par la revue globale
- Le bot a validé la fiche EN de Saint-Maur et le journal.
- **Mais** le porteur : « quand je pose une question au journal de bord, j'ai
  toujours un prompt », et la capture de la nuit (PR #252, fiche Pointe-à-Pitre)
  montre « Input: A large JSON object… Task: Present a scale stop… ».
  Verdict : le nettoyage RA1 est bon, la **fuite ressort du cache** 7 j des
  fiches, rempli avant RA1 → **RB3**.

### PR #251 (RA2 — ordre du récit) — 0/3, 3 KO bot
- KO bot : le récit FR/EN commence par « a quitté La Rochelle », **Saint-Maur
  absent du texte** ; sous-titre du film « La Rochelle → Ajaccio ».
- Le porteur entend la même chose dans le film : « a quitté la Rochelle le
  25 avril 2027 et a pris la route vers Ajaccio ». Verdict : RA2 n'a pas
  suffi sur le poste de recette ; le chapitre « départ » du film lit une
  horloge de simulation, pas le départ officiel → **RB5**.

### PR #252 (RA3 — rendu du film) — 4/5 cochés par le porteur
- OK porteur : fond de carte gardé, glisse sans saut, zoom stable, archipels.
- KO bot : pas de bulle carte à l'approche des escales (seule la carte
  latérale « ON BOARD, NOW »). Verdict : mergeable ; le déclenchement des
  bulles d'escale relève du journal des moments → **fondu dans R9c**.

### PR #253 (RA4 — avion, live, bornes) — 3/3 cochés, mais régression majeure
- OK porteur : trait avion non cliquable ; Cmd R stable ; la carte bute.
- **Régression (revue globale)** : Halifax ↔ Saint-Pierre-et-Miquelon est
  traité comme une jambe avion (noir pointillé, hors climato) alors que
  c'est un trajet **en bateau**, avec la chorégraphie d'avant (bateau
  stationné à Cayenne, avion, bateau relais) → **RB1**.
- **Manque (revue globale)** : la route n'est pas reproduite sur la copie
  du monde **de droite** (côté Afrique) ; à gauche elle l'est → **RB8**.
- KO bot non confirmé par le porteur : après rechargement, écran « Tracé en
  cours » (0 points) — probablement un état vierge du navigateur du bot ;
  noté § 3, pas de lot.

### PR #254 (RA5 — Stop, fiche hors lecture) — 7/7 cochés (bot), contredit en séance
- Le porteur, pendant Revoir : « j'ai appuyé sur stop et ça a encore pas
  marché ». Verdict : la machine à états est bonne à froid (bot), mais
  **pendant la lecture vocale** Stop ne coupe pas tout → **RB6**.

### PR #256 (RA6 — finitions) — 5/5 cochés (bot)
- Verdict : mergeable, rien à reprendre.

### PR #257 (RA7 — fourchette d'arrivée) — 0/2, 2 KO bot
- KO bot : rien sous la prochaine escale ; Revue du plan sans fenêtre
  resserrée (« perles pas encore chauffées »). Verdict : le code d'affichage
  existe mais l'**ensemble ETA n'est jamais prêt** sur un poste frais
  (`{members: 0}`) → **RB7**.

### PR #258 (RA8 — vitesse du passé ERA5) — 1/2
- OK bot : trait parcouru teinté hindcast.
- Non vérifiable : aucun survol d'un point parcouru ne montre la vitesse de
  l'époque. Verdict : mergeable ; l'info-bulle de survol des segments
  parcourus est ajoutée par **RB8** (même fichier que les copies de route).

## 2. Revue générale (les mots du porteur → où ça va)

1. **« Halifax ↔ Saint-Pierre, c'est un trajet en bateau »** : revenir à la
   chorégraphie d'avant — bateau stationné à Cayenne ; avion Cayenne →
   Halifax ; un bateau relais apparaît à Halifax, fait Halifax →
   Saint-Pierre → Halifax **en mer** (climatologie calculée dessus) ; avion
   retour pendant que le bateau relais disparaît ; le bateau resté à Cayenne
   continue vers la Polynésie. « Tu as laissé le bateau parcourir le trajet
   en pointillé noir… c'est complètement stupide » → **RB1**.
2. **Cartes flottantes** : « cette carte à bord maintenant qui apparaît en
   haut… les encadrés en bas à droite pendant ce temps autour du bateau…
   il faut les mettre dans le sidebar gauche… tout inclure dans un encadré.
   Il faut que ça soit un produit. Il faut enlever les boutons Écouter
   [transcrit « moutons écoutés »] de ces encadrés » — vu en Simulation ET
   en Suivre → **fondu dans R8c** (c'est exactement son objet).
3. **Zoom +/−** : masqué par le sidebar gauche en haut à gauche ; le mettre
   **à l'horizontale, compact, en bas à droite**, à côté des citations
   « Leaflet | Tuiles © Esri — HERE, Garmin, OpenStreetMap contributors »
   → **RB2**.
4. **Journal de bord** : « j'ai toujours un prompt » (capture) → **RB3**.
5. **Barre de lecture** : « une barre de scroll est apparue… trop pourrie » ;
   remplacer réel / lecture / normale / accélérée par **un seul bouton
   forward à 4 niveaux** (réel → lecture → normale → accélérée → réel) ;
   « escale précédente / prochaine escale » → **petites flèches** ;
   « Écouter » → **symbole du haut-parleur** → **RB4**.
6. **La voix** : « c'est pas des nanomètres, c'est des milles nautiques…
   il faut que t'écrives en toutes lettres dans ce qui est déclamé »
   → **RB5** (et garde-fou fondu dans R9c).
7. **La date** : « c'est pas le 25 avril 2027, c'est la date qu'on avait
   choisie du 15 mai 2026, la date officielle du départ de l'expédition
   virtuelle » ; et le film doit partir de Saint-Maur → **RB5**.
8. **Ça coupe** : la voix s'arrête en plein milieu, « puis ça se repositionne
   sur la Polynésie » ; « j'ai appuyé sur stop et ça a encore pas marché » ;
   « revoir l'expédition, ça marche toujours pas » → **RB6**.
9. **Langues mélangées** : « le bateau navigue dans French Exclusive
   Economic Zone, French Polynesia, Polynésie française… c'est pas bon »
   (aussi vu : « (Guadeloupe) (Guadeloupe) », et « Ce que je changerais »
   en anglais dans l'UI FR) → **fondu dans R8a** (noms localisés dans
   build_moment) et **R10d** (conseil dans la langue de l'interface).
10. **Libellé météo de la barre** : « climatologie · GFS + GFS-Wave
    (Open-Meteo) » — « si c'est les deux, mettre climatologie + GFS ;
    si c'est un des deux, mettre seulement celui qui est utilisé » → **RB4**.
11. **Copies du monde** : à droite (côté africain), « le trajet complet
    n'est pas reproduit » ; à gauche il l'est → **RB8**.
12. **Copernicus down** : « il y a marqué estimé dans le popup vents vagues
    courants » — comportement honnête voulu, pas de lot (§ 3).

## 3. Ce qui est reporté ou fondu, et pourquoi

- **Cartes flottantes → encadré unique** : fondu dans **R8c** (constat du
  22 sept. ajouté à son prompt). RB n'y touche pas pour ne pas jeter le
  travail : R8c retire les pop-up et loge tout dans l'encadré produit.
- **Noms de ZEE localisés, pas de FR/EN mélangé** : fondu dans **R8a**
  (build_moment fournit `here` avec des noms dans la langue demandée).
  Cause lue : `src/engine/iciBriefing.js:187` insère le nom marineregions
  brut (anglais) dans la phrase française.
- **Bulle carte à l'approche des escales** (KO bot RA3) : fondu dans **R9c**
  (le journal des moments fournit l'événement « approche d'escale » que la
  bulle du film affiche).
- **Unités en toutes lettres dans la voix** : corrigé tout de suite par
  **RB5** ; garde-fou fondu dans **R9c** (le futur script du film ne doit
  pas régresser).
- **« Ce que je changerais » en anglais dans l'UI FR** : fondu dans **R10d**
  (la phrase du conseil est rendue dans la langue de l'interface).
- **« Estimé » quand Copernicus est down** : décision — c'est le repli
  honnête voulu (une source en panne manque, rien n'est inventé) ; RA8 a
  rendu le hindcast indépendant de Copernicus. Pas de lot.
- **KO bot RA4 « Tracé en cours » après rechargement** : non reproduit par
  le porteur (Cmd R validé sur son poste) ; à surveiller à la prochaine
  recette, pas de lot.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour App.jsx et MapSceneController.js). « Recette » = ce que le
porteur voit dans Chrome, par écran. « (RA4) » = code de la pile RA mergée ;
sinon les lignes sont celles de `main`. Pile linéaire RB1 → RB8.

### RB1 — Halifax ↔ Saint-Pierre redevient une jambe MER ; l'avion ne vole que Cayenne ↔ Halifax — RÉGRESSION MAJEURE (M)

Cause racine : `src/utils/berryLegs.js` (RA4) l. 62-77 — `airStopKey`
reconnaît {cayenne, halifax, spm} et `isAirLegNames` déclare « air »
**toute** paire différente, donc aussi Halifax ↔ Saint-Pierre-et-Miquelon
(jambe **mer**) ; `legKind` (l. 83) et `officialRouteLineStyle` (l. 90)
propagent l'erreur (noir pointillé, non cliquable, hors régime).
La chorégraphie voulue existe sur `main` : `src/engine/filmCast.js` l. 63-64
(« Outbound / return air-hop pair (Cayenne → Halifax … Halifax → Cayenne).
Between them: decoupled sailing (Halifax ↔ Saint-Pierre) ») et l. 230
(« Trois acteurs : bateau Berry (main), avion (plane), bateau relais
(side) ») ; `buildBerryLegs` (`berryLegs.js` l. 18-44 sur main) crée déjà
les jambes relais Halifax → SPM → Halifax.

Fichiers : `src/utils/berryLegs.js`, `src/utils/berryLegs.test.js`,
`src/engine/filmCast.js` (lecture : la chorégraphie de référence),
`src/map/MapSceneController.js` PAR EXTRAIT (`rg -n "officialRouteLineStyle|isAirSegment|addRouteLine"`),
`server/voyage_clock.py` PAR EXTRAIT (`rg -n "air|AIR_CALENDAR"`),
`server/tests/test_voyage_clock.py`.

Étapes :
1. `isAirLegNames` ne dit « air » **que** pour Cayenne ↔ Halifax (aller et
   retour). Halifax ↔ Saint-Pierre (les deux sens) = jambe **mer** : trait
   coloré par régime, cliquable, climatologie/vitesse calculées dessus.
2. Côté serveur : la jambe Halifax ↔ SPM compte ses milles **à la voile**
   et son temps de mer ; seules les jambes Cayenne ↔ Halifax restent au
   régime avion (`AIR_CALENDAR_HOURS`, zéro mille voile).
3. Vérifier que la chorégraphie de `filmCast.js` (bateau stationné à
   Cayenne, avion, bateau relais qui apparaît/disparaît à Halifax) est
   intacte après la pile RA — si un lot RA l'a dégradée, la restaurer à
   l'identique de `main` d'avant la pile.
4. Tests : `berryLegs.test.js` — Halifax → SPM et SPM → Halifax donnent
   `legKind === "sea"` et un style nul (pas de noir pointillé) ; Cayenne →
   Halifax et Halifax → Cayenne donnent « air » ; `test_voyage_clock.py` —
   la distance voile inclut Halifax ↔ SPM et exclut Cayenne ↔ Halifax.

Recette (visuelle) :
- **Suivre**, carte monde : le trait Halifax ↔ Saint-Pierre est **coloré
  comme une jambe de mer** (plus de noir pointillé), un clic dessus répond ;
  seuls Cayenne ↔ Halifax (et les sauts Pacifique) restent noirs pointillés.
- **Revoir l'expédition**, passage en Guyane : le bateau **reste à
  Cayenne**, l'avion décolle vers Halifax ; un bateau apparaît à Halifax,
  **navigue** jusqu'à Saint-Pierre puis revient ; l'avion repart vers
  Cayenne pendant que le bateau d'Halifax disparaît ; à l'atterrissage,
  l'avion disparaît et le bateau de Cayenne continue vers la Polynésie.

### RB2 — Le zoom : horizontal, compact, en bas à droite à côté des crédits (S)

Cause racine : `src/map/MapSceneController.js` l. 173-184 — `L.map(container,
{...})` ne passe pas `zoomControl: false` : le contrôle Leaflet par défaut
s'affiche **en haut à gauche**, sous le sidebar gauche qui le masque (visible
sur les captures de la nuit : les boutons +/− sous le bouton d'ouverture du
panneau).

Fichiers : `src/map/MapSceneController.js` PAR EXTRAIT (l. 170-200 et
`rg -n "attributionControl|control"`), `src/index.css`, tests associés
(`rg -n "zoom" src/map/*.test.js`).

Étapes :
1. Désactiver le contrôle par défaut ; ajouter le contrôle de zoom en
   **bas à droite** (`position: "bottomright"`), juste à côté de
   l'attribution « Leaflet | Tuiles © Esri… ».
2. CSS : boutons **à l'horizontale** (+ et − côte à côte) et **plus
   compacts** que le défaut Leaflet (« il est gros le bouton zoom ») ;
   au-dessus de la barre de lecture, jamais recouverts par elle ni par
   les crédits.
3. Aucune autre surface ne bouge (les crédits restent entiers — RA6).
4. Tests : le test de montage de la carte vérifie que le contrôle existe
   et sa position bas-droite.

Recette (visuelle) :
- **Tous écrans carte** : plus de +/− en haut à gauche ; en **bas à
  droite**, deux petits boutons + − **à l'horizontale** à côté des crédits,
  cliquables (le zoom marche), visibles sidebars ouverts ou fermés, barre
  de lecture affichée ou masquée.

### RB3 — Plus jamais de prompt : le cache des fiches est re-nettoyé (S)

Cause racine : `server/escale_api.py` l. 286 et l. 361-374 — la fiche
d'escale est servie depuis le cache `pearl_store.kv_get("escale", …,
ESCALE_TTL_S)` (TTL 7 jours) **sans repasser par le nettoyage** : les
paragraphes fuités générés avant RA1 (« Input: A large JSON object… Task:
Present a scale stop… », capture PR #252) ressortent tels quels pendant
7 jours. Le garde RA1 existe (`server/story_cascade.py`, `_PROMPT_LEAK_RE`
l. 58, `_clean_text` l. 336-340 sur la branche RA1) mais ne s'applique
qu'à la génération.

Fichiers : `server/escale_api.py`, `server/story_cascade.py`,
`server/tests/test_story_cascade.py`, `server/tests/test_escale_api.py`
(créer s'il n'existe pas), `server/logbook_chat.py` PAR EXTRAIT
(`rg -n "cascade_text|kv_get|cache"`).

Étapes :
1. À la **lecture du cache** (fiche d'escale, et chat s'il a un cache) :
   repasser le paragraphe par `_clean_text` ; si le texte nettoyé est vide
   ou détecté fuité, **invalider la clé** et regénérer (ou servir le repli
   `rules`), jamais servir la fuite.
2. Élargir `_PROMPT_LEAK_RE` aux formes vues le 22 : « Input: A large JSON
   object », « What's for the boat », « - Task: » — et à leurs équivalents
   traduits si le pipeline traduit la fiche.
3. Le chat (`logbook_chat.py`) passe par le même garde : une réponse fuitée
   → repli honnête du journal, jamais le prompt.
4. Tests : une entrée de cache contenant le texte fuité de la capture →
   la route renvoie le repli `rules` et la clé est invalidée ; une entrée
   saine → servie inchangée.

Recette (visuelle) :
- **Simulation**, langue anglaise, drapeau de **Pointe-à-Pitre** (l'escale
  de la capture) : la fiche contient de vraies phrases sur l'escale,
  jamais « Input: … », « Task: … », « JSON ».
- **Suivre**, Journal de bord, « À quelle vitesse va le bateau ? » : une
  phrase de réponse (ou l'échec honnête), **jamais un prompt** — y compris
  en reposant la même question (réponse en cache).

### RB4 — Barre de lecture sans barre de scroll : un bouton de vitesse à 4 niveaux, des flèches, un haut-parleur (S)

Cause racine : `src/components/SimulationFilmBar.jsx` l. 311 — la rangée de
commandes est en `overflow-x-auto` : quand les boutons dépassent (4 pilules
de vitesse `SPEEDS` l. 9-12 : real / read / normal / fast + « Escale
précédente » / « Aller à la prochaine escale » + « Écouter » en toutes
lettres), une **barre de défilement** apparaît dans la barre de lecture.
Libellé météo : `clockRegimeText` l. 556-570 concatène régime et sources
(« climatologie · GFS + GFS-Wave (Open-Meteo) ») sans dire ce qui est
réellement employé au point courant.

Fichiers : `src/components/SimulationFilmBar.jsx`, ses tests
(`rg -n "SimulationFilmBar" src/components/*.test.js*`), `src/i18n/fr.js`,
`src/i18n/en.js`.

Étapes :
1. Remplacer les 4 pilules par **un seul bouton** qui affiche le niveau
   courant et **cycle à chaque clic** : réel → lecture → normale →
   accélérée → réel. Même logique de vitesses qu'avant, aucun niveau
   supprimé.
2. « Escale précédente » / « Aller à la prochaine escale » deviennent deux
   boutons **flèches** (‹ ›) avec le libellé complet en info-bulle ;
   « Écouter » devient l'**icône haut-parleur** (état coupé/actif visible),
   libellé complet en info-bulle.
3. La rangée tient sur **une ligne sans défilement** aux largeurs
   d'écran courantes ; retirer l'`overflow-x-auto` devenu inutile.
4. Libellé météo : afficher **« climatologie + GFS »** si les deux
   alimentent le point courant, sinon **seulement** celui qui est employé ;
   le détail des modèles reste en info-bulle.
5. i18n fr + en pour chaque libellé/info-bulle.
6. Tests : le cycle du bouton (4 clics → retour à réel) ; pas de pilule de
   vitesse résiduelle ; le libellé météo pour « les deux » et « un seul ».

Recette (visuelle) :
- **Suivre et Simulation**, barre de lecture : **aucune barre de
  défilement** ; un seul bouton de vitesse qui passe de réel → lecture →
  normale → accélérée puis revient à réel en cliquant ; deux flèches pour
  les escales ; un haut-parleur à la place d'Écouter.
- Dans la ligne d'horloge : « climatologie + GFS » seulement si les deux
  sont utilisés, sinon le seul employé.

### RB5 — Le film part de Saint-Maur le 15 mai 2026 et la voix dit « milles nautiques » (M)

Cause racine : `server/film_script.py` l. 425-430 — le chapitre « depart »
prend `(start or {}).get("iso") or (clock or {}).get("t0")` et le nom de
`start` : quand le client envoie l'horloge d'une **simulation** (date de
départ réglée dans le panneau), le film déclame « a quitté La Rochelle le
25 avril 2027 » au lieu du départ **officiel** (Saint-Maur, 15 mai 2026) —
c'est aussi pour ça que Saint-Maur manque en tête (KO bot RA2). Et
l. 595-598, la phrase « le bateau est à {distLabel} du départ » emploie
l'abréviation « nm » (l. 574) que la voix lit « nanètres ».

Fichiers : `server/film_script.py`, `server/tests/test_film_script.py`,
`src/hooks/useReplay.js` PAR EXTRAIT (`rg -n "film|script|fetch"` : ce que
le client envoie), `src/engine/expeditionStory.js` (tête du récit,
`stopsWithDates` l. 124-141), `src/engine/expeditionStory.test.js`.

Étapes :
1. Pour le voyage **officiel**, le chapitre « depart » lit la **première
   marque de la route officielle** (Saint-Maur) et la **date officielle du
   départ (15 mai 2026)** — jamais le `t0` d'une horloge de simulation ni
   une date recalculée. La suite énonce Saint-Maur → La Rochelle →
   Ajaccio → Fort-de-France dans l'ordre de la route (finit le travail
   de RA2 sur le poste réel).
2. Dans **tout texte déclamé** (film serveur et récit client) : les unités
   en toutes lettres — « milles nautiques » / « nautical miles », « km »
   → « kilomètres » ; l'affichage écrit peut garder « nm ».
3. Aucune date ni distance inventée : tout vient de la route officielle et
   de l'horloge officielle.
4. Tests : `test_film_script.py` — le script officiel commence par
   Saint-Maur et « 15 mai 2026 » même quand la requête porte une horloge de
   simulation ; aucun « nm » nu dans les phrases du script ;
   `expeditionStory.test.js` — la tête du récit nomme Saint-Maur.

Recette (visuelle) :
- **Suivre → Revoir l'expédition** (FR puis EN) : la voix commence par
  « L'expédition Berry-Mappemonde a quitté **Saint-Maur** le **15 mai
  2026**… » — jamais « La Rochelle », jamais « 2027 » ; on entend « milles
  nautiques », jamais « nanomètres ».
- Le sous-titre du film affiche la même suite d'escales que la liste de
  droite, dans le même ordre.

### RB6 — La voix ne coupe plus, Stop coupe tout, la caméra ne saute pas sur la Polynésie (M)

Cause racine : `src/utils/speak.js` l. 182-275 — « onend sans boundary en
< 500 ms → une relance, puis mode linéaire » : quand Chrome coupe une
utterance en cours (keep-alive l. 9, chunks de 200 caractères l. 10), le
film bascule ou **finit prématurément** ; et `src/hooks/useReplay.js`
l. 48-71 — à la fin (ou sur Stop), « retour au live » : une fin prématurée
**recale la caméra sur la position live (Polynésie)** en plein film. Le
Stop « qui ne marche pas » du porteur : pendant la lecture vocale, l'arrêt
ne coupe pas tout (voix, animation, caméra) d'un seul geste.

Fichiers : `src/utils/speak.js`, `src/utils/speak.test.js`,
`src/hooks/useReplay.js`, `src/hooks/useReplay.test.js`,
`src/components/SimulationFilmBar.jsx` PAR EXTRAIT
(`rg -n "onStop|stopReplay|listen"`).

Étapes :
1. Coupure en plein chunk : **reprendre au chunk suivant** (ou re-lire le
   chunk coupé) au lieu de finir le film ; la bascule en linéaire ne
   déclenche jamais un « retour au live » tant que des chapitres restent.
2. La caméra ne se recale sur la position live **que** si le film est
   vraiment fini ou si le porteur a cliqué Stop — jamais sur un incident
   de voix.
3. **Stop** : un clic coupe la voix (`speechSynthesis.cancel`), l'animation
   et libère la caméra **dans le même geste**, y compris pendant qu'une
   utterance joue ; le bouton répond au premier clic.
4. Tests : `speak.test.js` — un `onend` prématuré au milieu des chunks →
   le texte continue au chunk suivant, pas de fin ; `useReplay.test.js` —
   un incident de voix ne met pas `finish` ; `stop()` pendant la lecture
   coupe voix + animation + caméra.

Recette (visuelle) :
- **Suivre → Revoir l'expédition**, laisser parler plusieurs minutes : la
  voix ne s'arrête pas en plein milieu d'une phrase ; la carte ne se
  recale jamais sur la Polynésie pendant le film.
- Cliquer **Stop** pendant que la voix parle : tout s'arrête net (voix,
  bateau, caméra) au premier clic, et « Revoir l'expédition » revient.

### RB7 — La fourchette d'arrivée s'affiche vraiment : ensemble préchauffé (S)

Cause racine : `server/voyage_api.py` l. 781-788 — `/voyage/official/eta`
appelle `ensemble_eta.official_eta` qui renvoie `{members: 0}` tant que
rien n'a chauffé les membres (« Sans membres : {members: 0} ») ; côté
client `src/components/EscaleLegend.jsx` l. 75-78 et
`src/hooks/usePlanReview.js` l. 47-57 n'affichent rien dans ce cas
(honnête, mais sur un poste frais la fourchette n'apparaît **jamais** —
les 2 KO bot de RA7, « perles pas encore chauffées »).

Fichiers : `server/voyage_api.py` PAR EXTRAIT (`rg -n "official/eta|_kick_official"`),
`server/ensemble_eta.py`, `server/tests/test_ensemble_eta.py` (ou le test
existant de l'ETA), `src/hooks/usePlanReview.js`,
`src/components/EscaleLegend.jsx`, tests JS associés.

Étapes :
1. **Préchauffer** l'ensemble ETA du voyage officiel au démarrage du
   serveur, en tâche de fond (comme `_kick_official_hindcast`), sans
   bloquer le démarrage ; rafraîchi avec les perles.
2. Le client **re-demande** l'ETA tant que `members == 0` (léger, avec
   recul progressif) : la fourchette apparaît dès qu'elle est prête, sans
   recharger la page.
3. Garder l'intervalle **resserré** de RA7 (membres à vitesse dégénérée
   écartés) ; même phrase et même arrondi en Suivre et dans la Revue du
   plan ; sans ensemble, toujours rien d'inventé.
4. Tests : serveur — après préchauffage sur la fixture officielle,
   `members > 0` et fenêtre de quelques jours pour Nouméa → Dzaoudzi ;
   client — l'affichage apparaît quand la réponse passe de `members: 0`
   à un ensemble plein.

Recette (visuelle) :
- **Suivre**, liste des escales, sous la prochaine : « arrivée entre le …
  et le … » (deux dates proches) visible au plus quelques minutes après le
  lancement, sans recharger.
- **Panneau droit → Revue du plan**, jambe Nouméa → Dzaoudzi : la même
  fourchette de quelques jours (plus jamais 7 mois, plus jamais rien).

### RB8 — La route sur les deux copies du monde ; survol d'un segment parcouru (S)

Cause racine : `src/utils/geo.js` l. 87-94 — `worldCopyCoords` fait trois
copies (0, +360, −360) d'une ligne **déjà dépliée** sur près de 360° de
longitude : dans les bornes ±540° posées par RA4 (`MapSceneController.js`
RA4 l. 44 `MAP_LON_BOUND = 540`), la copie **de droite** ne couvre pas le
côté africain du second monde — le porteur voit le trajet répété à gauche
mais pas à droite. Le survol des segments parcourus (RA8, item non
vérifiable) n'existe pas encore dans le tracé des segments.

Fichiers : `src/utils/geo.js`, `src/utils/geo.test.js`,
`src/map/MapSceneController.js` PAR EXTRAIT (`WORLD_OFFSETS` l. 40,
`addRouteLine` l. 63, segments l. 457-492), `MapSceneBoundary.test.js`
(ou le test de bornes de RA4), `src/i18n/fr.js`, `src/i18n/en.js`.

Étapes :
1. Les copies de la route couvrent **toute** la fenêtre navigable (±540°) :
   calculer les décalages nécessaires d'après l'étendue réelle de la ligne
   dépliée (p. ex. 0, ±360, +720 si besoin) au lieu du triplet fixe —
   même trajectoire visible à gauche **et** à droite, jusqu'à la butée.
2. Appliquer la même règle aux drapeaux/escales portés par la route si
   eux aussi manquent d'un côté.
3. **Survol d'un segment déjà parcouru** : une info-bulle courte donne la
   vitesse hindcast de l'époque (la donnée de RA8), rien pour les jambes
   avion ; aucun nouveau panneau.
4. Tests : `geo.test.js` — une ligne dépliée sur 360° produit des copies
   couvrant [−540, 540] ; test de bornes — après un grand glissement à
   droite, des points de route existent dans la fenêtre est ; un segment
   parcouru expose sa vitesse d'époque.

Recette (visuelle) :
- **Suivre**, tirer la carte **vers la droite** jusqu'à la butée : le
  trajet complet (Halifax, Antilles compris) est dessiné aussi de ce
  côté-là, comme à gauche.
- Survoler le trait **déjà parcouru** : une petite info-bulle donne la
  vitesse de l'époque ; sur un trait avion, rien.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Touche surtout |
|---|---|---|---|
| 1 | RB1 | M | berryLegs.js, voyage_clock.py (Halifax ↔ SPM en mer, chorégraphie) |
| 2 | RB2 | S | MapSceneController.js, index.css (zoom bas droite horizontal) |
| 3 | RB3 | S | escale_api.py, story_cascade.py (cache re-nettoyé, garde élargi) |
| 4 | RB4 | S | SimulationFilmBar.jsx (bouton 4 niveaux, flèches, haut-parleur, libellé météo) |
| 5 | RB5 | M | film_script.py, expeditionStory.js (Saint-Maur, 15 mai 2026, milles nautiques) |
| 6 | RB6 | M | speak.js, useReplay.js (voix sans coupure, Stop total, caméra) |
| 7 | RB7 | S | voyage_api.py, ensemble_eta.py, EscaleLegend.jsx (ETA préchauffé) |
| 8 | RB8 | S | geo.js, MapSceneController.js (copies du monde, survol parcouru) |

Puis le programme pré-rédigé continue **jusqu'à D0** : R8a → R10d (avec les
constats du 22 sept. fondus dans R8a, R8c, R9c, R10d), N1 → N4, D0.

Lancement, une fois la pile RA1 → RA8 mergée (#258) et la PR de ce document
mergée :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --dry-run --from RB1 --until D0
caffeinate -i python3 infra/agents/run_lots.py --from RB1 --until D0
```

Fin de batch : le poste de recette s'ouvre seul ; recette par écran ; merges
dans l'ordre de la pile.

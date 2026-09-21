# Plan — « Ici et maintenant », le journal des moments, l'expert en circumnavigation (nuit 3 : R8, R9, R10)

Version **1.0** — 21 septembre 2026. Trois chantiers demandés par le porteur
lors de la revue du 21 septembre, qui sont en réalité **un seul produit vu
sous trois angles** :

1. **R8 — un seul encadré « Ici et maintenant »** qui occupe tout le panneau
   gauche sous le chat et remplace le sac ici, « pendant ce temps autour du
   bateau », les fiches (satellite, climatologie, science, balisage), la
   dernière ligne d'étape (milles restants, ETA, milles parcourus, cap) et les
   alertes « à bord maintenant » (sécurité, décision).
2. **R9 — le journal des moments** : chaque fois que cet encadré change le long
   de la route, on enregistre (position, heure, contenu) ; la suite de ces
   changements est analysée pour fabriquer **une histoire chronologique**, lue
   à haute voix en **2 min 30** quand on clique « Revoir l'expédition ».
3. **R10 — l'expert en circumnavigation** : « Ce que je changerais » (revue du
   plan) et « Recalculer l'itinéraire » (ordres du skipper) deviennent une seule
   fonction : analyser la route, compter ce qui ne va pas (les alertes du
   journal), proposer un **compromis** entre un écart local (a) et un décalage
   de date (b) qui **minimise le nombre d'alertes** sur toute l'expédition —
   sachant que (b) décale toutes les escales suivantes et impose de réanalyser
   toute l'expédition.

Le fil rouge : **une seule fonction `build_moment` côté serveur** produit
l'encadré ; sa sortie horodatée est le journal ; le journal est la matière du
récit **et** la mesure (alertes) que l'expert cherche à minimiser.

## 0. Contraintes de fabrication (agent Grok 4.6 xhigh fast, 256 k de contexte)

Ce que la nuit 1 a montré : un lot tient dans un agent quand il **ouvre ≤ 6
fichiers**, n'a **jamais** besoin de lire `App.jsx` (1 750 lignes),
`voyage_api.py` (1 234), `MapSceneController.js` (1 000), `expeditionStory.js`
(903), `film_script.py` (890), `momentCard.js` (821) ou `eventRules.js` (812)
en entier, et livre **≤ 400 lignes de diff** hors tests. 256 k, c'est large
pour lire, étroit pour raisonner longtemps : un agent qui lit trois gros
fichiers en entier a déjà brûlé la moitié de sa fenêtre avant d'écrire une
ligne. Donc :

- **Sous-lots par couche** : d'abord le modèle (fonction pure + tests, aucune
  UI), puis le stockage / l'API, puis l'affichage, puis le branchement. Chaque
  sous-lot a un **contrat de données** écrit ici (§ 1.1, § 2.1, § 3.1) : un
  agent n'a pas à lire le code du sous-lot précédent, il lit le contrat.
- **Nouveaux fichiers plutôt que gros fichiers modifiés** : `server/moment.py`,
  `server/moment_journal.py`, `server/plan_alerts.py`, `server/plan_advisor.py`,
  `src/components/IciMaintenant.jsx`, `src/hooks/useMoment.js`. Les gros
  fichiers ne sont touchés que par `rg -n` + `Read offset/limit`, pour brancher.
- **Le serveur calcule, le client affiche.** Une seule implémentation de
  `build_moment` (Python). Le client ne recalcule rien : il rend un objet
  `Moment`. Pas de parité JS/Python à maintenir (leçon du lot C5).
- **Fixtures** : chaque sous-lot serveur livre une fixture JSON du voyage
  officiel réduite (3 escales, 40 points) dans `server/tests/fixtures/` ; les
  sous-lots UI l'utilisent (pas d'API en CI).
- **Pile linéaire dans l'ordre ci-dessous** ; les sous-lots d'un même chantier
  se suivent ; R8 avant R9 avant R10 (chacun consomme la sortie du précédent).

## 1. R8 — Un seul encadré « Ici et maintenant »

### 1.0 Ce que le porteur verra

Panneau gauche, de haut en bas : carte Berry (logos) → chat (hauteur fixe,
inchangé) → **un seul encadré** qui prend **toute la hauteur restante**, avec
trois onglets en tête : **Maintenant** (défaut) · **Récit** · **Journal**.
Le contenu défile à l'intérieur ; rien ne saute quand il change. Plus de
« sac ici », de « pendant ce temps », de « à bord maintenant », de fiche
d'escale (lot R7) ni de blocs séparés : les surfaces du plancher `main`
restent **joignables** (onglets), aucune n'est retirée.

Onglet **Maintenant**, dans cet ordre :

1. **Étape** — une ligne : « Nouméa → Dzaoudzi · J95 · 8,0 kn · reste 9 004 nm ·
   arrivée entre le 31 oct. et le 4 nov. » (la dernière ligne d'étape d'aujourd'hui,
   régime teinté comme la route).
2. **Alertes** — 0 à n pastilles (sécurité en rouge, décision en ambre) : vent
   ≥ seuil du skipper, Hs ≥ 3 m, saison cyclonique du mois dans la zone, ZEE
   sans port d'entrée connu, AMP à portée avec restriction, arrivée de nuit…
   Chaque pastille se ferme (×) **individuellement** ; fermer n'en ouvre pas une
   autre.
3. **Ici** — le sac : ZEE et formalités, port d'entrée le plus proche, AMP,
   balisage, fond, météo au bateau — le briefing actuel, liens de sources
   conservés (lot M), **sans phrase répétée** (lot R13).
4. **Autour du bateau** — une ligne par élément (satellite CDSE, climatologie
   du mois, science / station croisée, marina), dépliable ; ce sont les fiches
   « FREE » d'aujourd'hui, compactées.
5. **Sources** — une ligne.

Onglet **Récit** : le récit de la traversée (aujourd'hui « Récit de la
traversée », hauteur fixe validée par le porteur) — en R9c il devient la lecture
du journal. Onglet **Journal** : la liste chronologique des changements (R9b).

### 1.1 Contrat de données — `Moment`

```json
{
  "t": "2026-09-21T15:14:00Z",          // heure du voyage (horloge officielle ou curseur)
  "pos": {"lat": -20.1, "lon": 168.9},
  "mode": "follow | simulation | drawn",
  "leg": {"from": "Nouméa", "to": "Dzaoudzi", "day": 95, "kn": 8.0, "basis": "planned|measured",
          "remainingNm": 9004, "doneNm": 19324, "headingDeg": 262,
          "eta": {"p10": "2026-10-31", "p90": "2026-11-04"}, "regime": "hindcast|forecast|climatology"},
  "alerts": [{"id": "wind-2026-09-23", "kind": "wind|sea|cyclone|entry|mpa|night|other",
              "severity": "alert|decision", "title": "…", "fact": "…", "until": "…"}],
  "here": {"zee": {"name": "…", "mrgid": 8446, "entry": {"known": true, "ports": ["…"]}},
           "mpa": [...], "seamarks": [...], "seabed": {...}, "weather": {...},
           "sentences": ["…", "…"], "links": [{"label": "…", "url": "…"}]},
  "around": [{"kind": "satellite|climatology|science|marina", "title": "…", "fact": "…", "url": "…"}],
  "sources": ["Open-Meteo", "CDSE", "…"],
  "signature": "sha1 des champs stables (alerts.id, here.zee.mrgid, here.entry, around[].title, leg.to, leg.regime)"
}
```

`signature` ignore ce qui bouge sans rien dire (secondes, milles restants au
mille près, cap au degré près). Deux moments de même signature sont **le même
moment** : c'est ce qui rend le journal court (R9).

### 1.2 Sous-lots

**R8a — Le modèle `build_moment` (serveur, sans UI) · S/M**
Fichiers : `server/moment.py` (créer), `server/tests/test_moment.py` (créer),
`server/tests/fixtures/official_mini.json` (créer : 3 escales, 40 points, 12
perles, horloge), lecture par extrait de `server/ici_warm.py` (forme d'une
perle : `rg -n "bag\[" server/ici_warm.py`), `server/voyage_clock.py` (t par
point), `server/plan_review.py` (saison / AMP). Livre `build_moment(perle,
clock_point, leg, skipper_thresholds) -> Moment` et `signature(moment)`.
Tests : mêmes entrées → même signature ; un mille de plus ne change pas la
signature ; une nouvelle ZEE la change ; toute alerte a un `fact` non vide.
Aucun chiffre inventé : tout vient de la perle et de l'horloge.

**R8b — L'endpoint et l'encadré (API + UI) · M**
Fichiers : `server/main.py` par extrait (ajouter `GET /ici/moment?lat&lon&t&mode`
qui prend la perle la plus proche — ou calcule le sac comme `/ici` — puis
`build_moment`), `src/hooks/useMoment.js` (créer : fetch + état, repli sur la
fixture quand l'API ne répond pas), `src/components/IciMaintenant.jsx` (créer :
trois onglets, sections § 1.0, hauteur = reste du panneau : conteneur
`flex-1 min-h-0 overflow-auto`), `src/components/IciMaintenant.test.js`,
`src/index.css` (variables de hauteur, mode clair), `src/i18n/fr.js`, `en.js`.
Recette : Suivre — un seul encadré sous le chat, trois onglets, il prend toute
la hauteur ; fermer une alerte n'en ouvre pas une autre.

**R8c — Le branchement et le retrait des anciens blocs · S/M**
Fichiers : `src/components/Sidebar.jsx` (remplacer MomentCards inline, FREE,
sac ici, récit, journal par `IciMaintenant` ; onglets Récit et Journal reçoivent
les composants existants), `src/components/Sidebar.layout.test.js`,
`src/App.jsx` **par extrait** (`rg -n "iciBriefing|freeCards|momentCards|storyText|journal"`) :
un seul objet `moment` passé au panneau ; Simulation et Tracer passent par le
même endpoint (position du curseur / de la route dessinée). Les `data-testid`
existants sont conservés (alias). Recette : Simulation et Tracer — le même
encadré, rempli à la position du curseur ; aucune surface de `main`
inaccessible.

## 2. R9 — Le journal des moments et le récit de 2 min 30

### 2.0 Où vit le journal, et pourquoi là

Le porteur a décrit le mécanisme : « enregistrer la position et le contenu de
l'encadré à chaque fois qu'il change ». Si on l'enregistre **dans le navigateur
au fil de l'eau**, le journal du voyage officiel ne contient que ce que ce
navigateur a vu (quelques positions par jour, rien du passé) et chaque visiteur
a le sien. Or le serveur possède déjà **tout le passé et tout le futur** de la
route : 3 272 perles réchauffées le long du trait (`ici_warm.py`, SQLite
`pearls`), l'horloge officielle (t par point), les régimes (hindcast /
prévision / climatologie), l'ETA par ensembles. Donc :

- **Le journal du voyage officiel est une table dérivée, côté serveur** : pour
  chaque perle dans l'ordre de la route, `build_moment` → `signature` ; on ne
  garde une ligne que quand la signature change. Ordre de grandeur : 3 272
  perles → 300 à 800 moments distincts × ~2 Ko = 1 à 2 Mo. SQLite existante
  (`pearl_store.py`, table `moments`), réchauffée après les perles et
  rafraîchie chaque jour (le passé se fige quand le hindcast est rempli ; le
  futur change avec les prévisions).
- **Le journal d'une simulation ou d'une route dessinée** est local au
  navigateur (`localStorage`, clé = identifiant de route, ≤ 2 000 entrées) :
  construit à partir des `Moment` reçus de `/ici/moment` au fil du curseur.
  Il sert à l'onglet Journal ; il ne sert pas au film (le film est celui du
  voyage officiel).

### 2.1 Contrat de données — ligne de journal

```json
{"voyageId": "official", "seq": 128, "t": "2026-06-02T08:00:00Z",
 "pos": {"lat": 32.1, "lon": -16.9}, "legIdx": 2, "signature": "…",
 "changes": [{"kind": "zee-enter", "score": 2, "title": "Entrée dans la ZEE du Maroc", "fact": "…"},
             {"kind": "alert-on", "score": 3, "title": "Vent 34 kn attendu", "fact": "…"}],
 "moment": { …Moment complet… }}
```

`changes` = différence avec la ligne précédente (`diff_moments(prev, cur)`),
chaque changement porte un **score** 1–3 : arrivée/départ d'escale 3, alerte
qui s'allume 3, entrée de ZEE 2, station scientifique croisée 2, changement de
régime 1, AMP à portée 1, alerte qui s'éteint 1. Ce sont **les mêmes
événements** que ceux de la bulle (lot R6) : R6 les construit depuis le journal
quotidien en nuit 2, R9c les rebranche sur ce journal des moments.

### 2.2 Le récit de 2 min 30 : une synthèse, pas une lecture

150 s de voix française ≈ **2 400 caractères** (F1 répartit le temps au prorata
des caractères ; 180 s ≈ 2 900). Le journal en fait dix fois plus. Le récit est
donc une **sélection sous budget**, puis une **rédaction** :

1. **Chapitres** = jambes entre escales (F1, inchangé) ; budget de caractères
   par chapitre au prorata des jours de mer, plancher 120 caractères (une
   jambe d'un jour a droit à une phrase), le reste réparti.
2. **Sélection** par chapitre : les changements du journal triés par score
   décroissant puis date ; on prend dans l'ordre chronologique tant que le
   budget tient ; toujours l'arrivée à l'escale (score 3) ; jamais deux
   changements de même `kind` à moins de 10 % du chapitre l'un de l'autre
   (« entrée ZEE Espagne, entrée ZEE Portugal, entrée ZEE Maroc » devient une
   seule phrase « trois ZEE traversées »). Regroupement par `kind` quand ils
   sont ≥ 3 : « 4 alertes de vent entre le 2 et le 9 juin ».
3. **Brut** : une phrase par changement retenu, gabarit par `kind`, connecteurs
   variés (R5), chiffres = ceux des `fact`. Toujours disponible, sans LLM.
4. **Rédigé** (option, F3) : Nemotron réécrit le chapitre à partir du brut, sous
   `filter_numbers` (aucun nombre absent des faits), même budget ± 10 %. Le
   sous-titre « source » dit lequel des deux est lu.
5. Les `events` de chaque chapitre (bulles R6) = exactement les changements
   retenus, `charIdx` = position de leur phrase dans le texte du chapitre.

Tests : longueur totale du brut dans [budget − 10 % ; budget + 10 %] ; chaque
chapitre ≥ 1 phrase ; l'arrivée de chaque escale est présente ; aucun nombre du
rédigé absent des faits ; deux chapitres consécutifs ne commencent pas par le
même connecteur.

### 2.3 Sous-lots

**R9a — Table `moments`, remplissage, endpoint (serveur) · M**
Fichiers : `server/moment_journal.py` (créer : `diff_moments`, `warm_moments(voyage_id)`
qui parcourt les perles dans l'ordre de la route et n'écrit que les changements
de signature, `read_moments(voyage_id, until=None)`), `server/pearl_store.py`
par extrait (table `moments` dans `_SCHEMA`), `server/voyage_api.py` par extrait
(`GET /voyage/official/moments?until=` ; lancement de `warm_moments` en tâche de
fond après le réchauffage des perles — `rg -n "_kick_official_hindcast|warm_official_route"`),
`server/tests/test_moment_journal.py`, fixture R8a. Recette (aucun changement
visible) : `/ici/warm/status` montre `moments: n` ; les trois parcours marchent
comme avant.

**R9b — L'onglet Journal et la lecture du journal par l'encadré · S/M**
Fichiers : `src/hooks/useMomentJournal.js` (créer : officiel = serveur ;
simulation / dessin = `localStorage`), `src/components/IciMaintenant.jsx`
(onglet Journal : liste chronologique « date · position · ce qui a changé »,
clic = placer le curseur là), `src/components/IciMaintenant.test.js`, `fr.js`,
`en.js`. En Suivre, l'onglet Maintenant lit le moment du journal ≤ maintenant
(cohérence exacte entre l'encadré et le journal). Recette : Suivre — onglet
Journal, les entrées défilent du 15 mai à aujourd'hui ; cliquer une entrée
place le film / le curseur à cette date.

**R9c — Le film raconte le journal (serveur) · M**
Fichiers : `server/film_script.py` par extrait (`rg -n "def build_script|chapters|events|written"` :
remplacer la source des phrases par la sélection § 2.2), `server/story_cascade.py`
par extrait (réécriture sous `filter_numbers`, existant), `server/tests/test_film_script.py`,
`src/hooks/useReplay.js` **rien** (le format du script ne change pas : chapitres,
texte, `events`). Recette : Revoir — le film raconte, dans l'ordre, ce qui a
changé le long de la route (ZEE, alertes, escales, stations) ; il dure toujours
2 min 30 ; les bulles montrent les mêmes événements que le texte.

## 3. R10 — L'expert en circumnavigation

### 3.0 La question posée et la réponse

« Ce que je changerais » doit dire **où ça coince et quoi faire** ; « Recalculer
l'itinéraire » a proposé 4 643 nm au lieu de 1 371 parce qu'il **évitait tout
vent > 30 kn** sans borne de distance ni de corridor : un routeur sans juge.
Le porteur tranche : la réponse est un **compromis** entre

- **(a) l'écart local** — même corridor, écart borné (distance ≤ +20 %, ≤ 300 nm
  du trait), qui ne change pas les dates ;
- **(b) le décalage de date** — partir plus tôt ou plus tard d'une escale, ce qui
  **décale toutes les escales suivantes** (jours à quai conservés) et impose de
  **réévaluer toute l'expédition** ;

qui **minimise le nombre d'alertes pondérées sur toute la route**, à coût
borné (jours de décalage, milles en plus). Ni (a) seul, ni (b) seul : le
meilleur mélange, expliqué.

### 3.1 Contrat de données — plan évalué et conseil

```json
// evaluate_plan(plan) — plan = jambes + dates de départ + jours à quai + seuils du skipper
{"legs": [{"idx": 3, "from": "Nouméa", "to": "Dzaoudzi", "depart": "2026-10-01", "arrive": "2026-11-02",
           "alerts": [{"kind": "cyclone", "severity": "alert", "when": "2026-10-20", "where": {"lat": -12, "lon": 60},
                       "fact": "Saison cyclonique du sud-ouest de l'océan Indien : novembre à avril", "weight": 3}],
           "score": 9, "frozen": false}],           // frozen = jambe déjà naviguée : jamais modifiée
 "total": 27}

// advise(plan, leg_idx) — le compromis
{"leg": 3, "best": {"shiftDays": +7, "corridor": "north", "extraNm": 41, "alertsBefore": 11, "alertsAfter": 5,
                    "totalBefore": 27, "totalAfter": 19, "cascade": [{"stop": "Dzaoudzi", "was": "2026-11-02", "now": "2026-11-09"}, …],
                    "facts": ["…"], "sentence": "Partir de Nouméa le 8 octobre plutôt que le 1er et passer 120 nm plus au nord entre 60° et 50° E : 5 alertes au lieu de 11 sur cette jambe (+41 nm) ; toutes les escales suivantes reculent de 7 jours."},
 "alternatives": [ …top 3… ]}
```

### 3.2 Comment on calcule (et pourquoi c'est rapide)

- **Évaluer** un plan = pour chaque jambe non figée, échantillonner le trait
  tous les 60 nm, dater chaque échantillon avec la vitesse planifiée (polaire ×
  vent du mois, lot C4), et interroger : la climatologie du mois (vent P90, Hs
  P90, mois cycloniques — atlas déjà en cache côté BI, `plan_review.py` s'en
  sert), la prévision quand l'échantillon est à < 10 jours, le hindcast pour
  le passé (figé), les seuils du skipper, les ZEE et ports d'entrée (perles),
  les AMP. Une alerte par échantillon au plus par `kind` ; pondération
  `weight` 1–3. Coût : quelques centaines de lectures en cache → **< 2 s** par
  plan ; résultat mis en cache par (hash du trait, dates au jour, seuils).
- **Candidats** : décalages `d ∈ {−21, −14, −7, 0, +7, +14, +21}` jours du départ
  de la jambe choisie, propagés aux suivantes × corridors `{référence, nord,
  sud}` où nord/sud = trait de référence décalé de 150 nm puis relissé (grands
  cercles entre jalons), distance ≤ +20 % — **pas** d'isochrone libre. 21
  candidats × < 2 s : le conseil arrive en moins d'une minute, en tâche de fond
  avec un état « en cours ».
- **Score** = `Σ weight des alertes` + `0,3 × |d|` (jours) + `0,02 × extraNm`.
  Le meilleur est retenu ; les trois suivants sont proposés en alternatives.
  Le **routeur isochrone garde une place** : si le meilleur candidat garde
  ≥ 1 alerte de vent sur la jambe, on lui demande un écart **dans le corridor**
  du candidat (contraintes : distance cap, corridor ±300 nm, seuil du skipper)
  — c'est le « recalculer » d'aujourd'hui, mais **bridé et jugé**.
- **Le LLM n'écrit que la phrase** (`sentence`) à partir de `facts`, sous
  `filter_numbers` (cascade existante, `ADVICE_SYSTEM` dans `voyage_api.py`) ;
  repli gabarit sans LLM.

### 3.3 Ce que le porteur verra

- **Revue du plan** (panneau droit) : pour chaque jambe, une ligne « alertes :
  n » teintée ; « Ce que je changerais » = la `sentence` du meilleur compromis
  de la jambe la plus chargée, avec trois pastilles « 11 → 5 alertes ·
  +41 nm · +7 j », et un bouton **Appliquer** qui crée le brouillon de voyage
  (flux existant `draft` / `recompute` / `accept`) et affiche **deux colonnes**
  (aujourd'hui / conseillé : distance, jours de mer, alertes, dates d'escale
  décalées). Plus de tableau à six routes sans explication.
- **Ordres du skipper** : « Recalculer l'itinéraire » devient **« Demander
  conseil »** → même carte deux colonnes, pour la jambe courante. Un écart de
  route ne dépasse jamais +20 % de distance.

### 3.4 Sous-lots

**R10a — L'évaluateur `evaluate_plan` (serveur) · M**
Fichiers : `server/plan_alerts.py` (créer), `server/tests/test_plan_alerts.py`,
fixture R8a + une fixture climatologie mensuelle (12 mois × 6 cases),
`server/plan_review.py` par extrait (réutiliser la lecture de l'atlas et des
jours à quai), `server/voyage_clock.py` par extrait (dater les échantillons).
Tests : voyage officiel évalué < 2 s ; décaler Nouméa de +30 jours change le
total ; les jambes passées ne changent jamais ; chaque alerte a un `fact` et
un `when`. Recette : aucun changement visible.

**R10b — Le compromis par décalage de date `advise` (serveur) · M**
Fichiers : `server/plan_advisor.py` (créer : candidats de décalage, cascade
des escales, score, phrase gabarit), `server/tests/test_plan_advisor.py`,
`server/voyage_api.py` par extrait (`GET /voyage/official/advice?leg=` avec
état `pending|done`, réécriture LLM via `ADVICE_SYSTEM` sous `filter_numbers`).
Tests : le score du meilleur ≤ celui du plan actuel ; la cascade décale toutes
les escales suivantes du même nombre de jours ; jours à quai conservés ;
déterminisme. Recette : aucun changement visible (l'endpoint répond).

**R10c — L'écart local borné (serveur) · M**
Fichiers : `server/plan_advisor.py` (corridors nord / sud relissés, cap
+20 %), `server/isochrone.py` par extrait (`rg -n "def route|max_wind|constraints"` :
ajouter corridor ± 300 nm et cap de distance ; jamais d'écart libre),
`server/tests/test_plan_advisor.py`. Tests : aucun candidat > +20 % ;
aucun point à > 300 nm du trait de référence ; le cas « La Rochelle → Ajaccio,
vent max 30 kn » rend une route ≤ 1 650 nm (1 371 × 1,2). Recette : Simulation —
Ordres du skipper, vent max 30 kn, « Demander conseil » : la route proposée fait
**≤ 1 650 nm**, plus jamais 4 643.

**R10d — L'interface : revue du plan conseillée, deux colonnes, Appliquer · M**
Fichiers : `src/components/PlanReview.jsx`, `src/hooks/usePlanReview.js`,
`src/components/SkipperOrdersPanel.jsx` par extrait (bouton), la carte de
comparaison existante (`rg -n "RouteCompare|comparatif|six routes" src/components`),
tests associés, `fr.js`, `en.js`, `src/App.jsx` par extrait (flux draft /
accept existant). Recette : Panneau droit — Revue du plan : chaque jambe a
« alertes : n » ; « Ce que je changerais » est une phrase qui nomme la jambe, le
décalage et l'écart, avec « 11 → 5 alertes · +41 nm · +7 j » ; **Appliquer**
montre deux colonnes et les dates d'escale décalées. Simulation — « Demander
conseil » remplace « Recalculer l'itinéraire », même carte.

## 4. Ordre de la nuit 3 et ce qui reste à trancher

| # | Sous-lot | Taille | Dépend de |
|---|---|---|---|
| 1 | R8a modèle `build_moment` | S/M | R6, R7 mergés (nuit 2) |
| 2 | R8b endpoint + encadré | M | R8a |
| 3 | R8c branchement | S/M | R8b |
| 4 | R9a table + remplissage + endpoint | M | R8a |
| 5 | R9b onglet Journal | S/M | R8c, R9a |
| 6 | R9c le film raconte le journal | M | R9a, R6 |
| 7 | R10a évaluateur | M | R8a |
| 8 | R10b compromis par dates | M | R10a |
| 9 | R10c écart local borné | M | R10b |
| 10 | R10d interface | M | R10c, R8c |

Dix sous-lots de taille M : c'est **deux nuits** au rythme observé (11 PR en
3 h pour des S/M), ou une nuit pour R8 + R9 et une pour R10. À trancher par le
porteur avant le lancement :

1. **Onglets ou empilement** dans l'encadré unique (§ 1.0 propose trois onglets
   pour ne retirer aucune surface).
2. **Poids du score** de l'expert (§ 3.2 : 0,3 par jour de décalage, 0,02 par
   mille) — ce sont des réglages du skipper, exposés dans Paramètres avancés ou
   fixes ?
3. **Le journal des simulations** reste local au navigateur (§ 2.0) — ou faut-il
   le garder côté serveur pour la route dessinée aussi ?

Les prompts `<!-- LOT -->` de ces dix sous-lots s'écrivent dans
`LOTS_ORDRE_ET_PROMPTS.md` une fois ces trois points tranchés et la nuit 2
mergée.

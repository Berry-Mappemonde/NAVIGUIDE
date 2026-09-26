# Plan — Corrections de la revue du 26 septembre (session 4) : lots RF1 → RF9

Version **1.1** — 26 septembre 2026 (amendée le soir même selon les
commentaires du porteur sur la PR #336 : lot **RF9** — le voyage officiel est
précalculé et stocké — inséré **avant RF2** ; RF2 réduit à la robustesse, RF3
lit le stock ; les pilules **2:30 / 3:00 restent**, RF7 corrige **leur place**
dans la barre au lieu de les retirer). Le porteur a recetté dans Chrome la pile
#325 → #334 (lots RE1 → RE7, RC10, RC11) : 13 items cochés sur 26 (dont 11 par
le bot), **8 KO du porteur, tous nouveaux** depuis la session précédente
(2026-09-26T10:55:38Z), plus une **revue globale en quatre priorités
imposées** : les erreurs de console partout, les erreurs de console pendant le
film, le discours du film, la cinématique du film — « tout autre correctif
passe après ces quatre ». Ce plan transforme ces 8 KO 🆕, les priorités et les
commentaires de la PR #336 en 9 lots correctifs — RF1, **RF9**, RF2 → RF8,
dans cet ordre — à enchaîner par `infra/agents/run_lots.py`. Les KO
du bot déjà lus par les plans précédents (`PLAN_CORRECTIONS_2026-09-23.md`,
`PLAN_CORRECTIONS_2026-09-26-s2.md`) ne sont **pas** replanifiés ici ; seuls
ceux qui recoupent un KO 🆕 ou une priorité sont cités en appui.

**Prérequis.** Les lots RF partent de `main` **après merge de la pile
#325 → #334** (pile linéaire : merger la PR de tête #334 suffit — la décision
reste au porteur). Les ancres `fichier:ligne` ci-dessous sont lues sur la tête
de pile (`fix/lot-rc11-revoir-grise`, PR #334) : ce sera l'état de `main`
après merge — elle contient le code des lots RE1 → RE7, RC10 et RC11.

**Le fil rouge de cette session.** Sur le poste de recette, le voyage officiel
ne répondait plus (`POST /voyage` 500 puis 429, `GET /ici` 500, polaires 500) :
le Journal est resté vide, le récit du film est retombé sur le court trajet de
la Simulation, et le porteur n'a **pas pu recetter** #327, #331, #333 et #334
(« revue non faite car le Journal est vide »). Quatre des huit KO 🆕 ont cette
seule cause serveur — c'est le couple **RF9** (le voyage officiel est
précalculé et stocké, le serveur sert) + **RF2** (robustesse), en tête de pile
avec RF1.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4).
- **Rien de superflu à l'écran** (REGLES § 1) : un bouton visible marche ou
  n'existe pas. Quand ce plan **retire** une surface (« Récit : règles »),
  c'est sur **demande explicite du porteur** (KO #327). Les pilules
  **2:30 / 3:00 restent** (décochées par défaut, RD7) : le porteur demande de
  corriger **leur place** dans la barre, pas de les retirer (commentaires sur
  la PR #336, captures du 26 sept. 18:10).
- **Le voyage officiel est précalculé et stocké** (commentaires sur la PR
  #336) : tout ce dont Suivre et Revoir ont besoin est calculé **une fois**,
  rangé dans un stock **persistant** (il survit aux redémarrages et aux
  déploiements), puis **servi tel quel** par l'API — jamais de calcul ni
  d'appel à un fournisseur externe dans le chemin d'une requête. C'est le lot
  **RF9**, placé avant RF2.
- **Aucun chiffre produit par un LLM** ; champ inconnu = silence.
- **La demande la plus récente du porteur l'emporte** : l'accueil en
  **Suivre** + Cinéma + monde dézoomé (KO #325, 26 sept. session 4)
  **remplace** l'accueil en Simulation de la décision D1 du plan s2
  (26 sept. session 2) — voir § 2, décision D1'.
- **Chaque erreur rouge de console a une cause et un lot** (priorité 1 du
  porteur) : ce classement remplace, pour les 400/500 applicatifs, le
  « environnement du poste, rien à planifier » du plan du 23 (§ 3).
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF. Plus **Revoir l'expédition** en Suivre, console
  ouverte : c'est le parcours n° 1 de cette session.

## 1. Revue par PR (cases du porteur, verdict du réviseur de nuit)

13 / 26 cochés (porteur 2, bot 11). Les KO bot déjà lus par un plan précédent
ne sont pas replanifiés ; la colonne « Suite » ne cite que ce qui appartient à
ce plan.

| PR | Lot | Porteur | KO 🆕 du porteur | Bot (rappel) | Suite |
|---|---|---|---|---|---|
| #325 | RE1 | 3/3 (porteur 1) | **l'application doit s'ouvrir en Suivre + Cinéma + carte monde entière (dézoomée)** | 4 KO : caméra pas recadrée en Suivre (`POST /voyage` 500 en est la cause), console 500, advice 400 | → **RF6** (accueil, D1') ; console → **RF1**, **RF2** |
| #326 | RE2 | 3/3 🤖 | **les escales de la liste du panneau droit doivent être juste informatives quel que soit le mode** | rien | → **RF7** (D2') |
| #327 | RE3 | 1/5 | **journal vide** (devrait être rempli depuis le départ) ; **pilules 2:30 / 3:00 : lecture corrigée par le porteur (PR #336) — les garder, mais elles débordent de la barre film et passent sous le panneau droit (captures du 26 sept. 18:10) : corriger leur place** ; **supprimer « Récit : règles »** (jamais demandé) ; **encadré date/heure de départ à la taille exacte du format XX-XX-XXXX XX:XX** ; **Tracer bugue et refuse de dézoomer** (voulu : monde entièrement dézoomé) | 1 KO console (~188–257 erreurs rouges : advice 400, /voyage 500→429, /ici 5xx, polar 500, climato 500…) | journal → **RF9**, **RF2** ; barre → **RF7** (D3') ; Tracer → **RF6** (D4') ; console → **RF1**, **RF2** |
| #328 | RE4 | 3/3 🤖 | — | 1 KO console (429/500, advice 400, ERR_HTTP2) | → **RF1**, **RF2** |
| #329 | RE5 | 0/2 | **« idem pré-revue »** (fourchette toujours absente, `members: 0`) | 3 KO : advice 400, ERR_CONNECTION_CLOSED sur /ici et /eta, ERR_HTTP2 | § 3 (re-recette après RF9 + RF2 ; RE5 est codé, l'ETA et la fourchette sont servies depuis le stock RF9) ; advice → **RF1** |
| #330 | RE6 | 2/2 (porteur 1) | **avec les roses de vent affichées, le zoom est très lent et l'appli se fige** | — | → **RF8** ; parité globe fondue dans **G4** |
| #331 | RE7 | 0/4 | **KO général : le journal est vide et le récit ne contient aucun événement** | 3 KO : l'avion n'est pas dit (Cayenne nommée, aucun vol) ; console film (400 advice, 500 /eta et /ici en rafale) | journal/récit → **RF9**, **RF2** ; avion → **RF4** ; console film → **RF3** |
| #333 | RC10 | 1/2 🤖 | **revue non faite car le Journal est vide** | 2 KO : le sous-titre de fin (« Aujourd'hui, le bateau est à… ») n'apparaît pas, barre récit absente une fois le film arrêté ; console film > 1 000 erreurs | journal → **RF9**, **RF2** ; fin du film → **RF4** ; console film → **RF3** |
| #334 | RC11 | 0/2 | **revue non faite car le Journal est vide** | 8 KO : advice 400 (×5 écrans), fourchette absente (`members: 0`), 404 tuiles climato, chat « Quel vent » sans réponse | journal → **RF9**, **RF2** ; advice → **RF1** ; fourchette, tuiles, chat → § 3 |

Les captures du bot confirment le fil rouge : ligne d'état retombée sur
« Saint-Maur → La Rochelle · 0 nm · j0 » (le trajet court de la Simulation, pas
le voyage LIVE), Journal réduit à la seule ligne « 15 mai 2026 · départ »,
bandeau « Échec — Service des polaires indisponible » dans le panneau droit,
et, pendant le film, un **damier de tuiles grises** sur tout le fond de carte
(#331, #333, #334).

## 2. Revue générale (les quatre priorités du porteur, point par point)

Le porteur impose l'ordre : « Les lots correctifs se font dans cet ordre,
avant tout le reste. » La pile RF le suit.

**Priorité 1 — Les erreurs de console, partout.** « Chaque erreur rouge a une
cause et un lot, aucune n'est laissée pour plus tard. » Causes lues sur la
tête de pile :

1. `GET /voyage/official/advice?leg=…&lang=fr` → **400** (vu sur les 9 PR,
   tous écrans) : le client choisit l'indice de jambe sur les jambes de
   `/voyage/official/plan-review` (`src/hooks/usePlanReview.js:118`
   `pickHeaviestLegIdx`, `:434`, envoi `:253-257`) puis le serveur applique
   cet indice à un **autre** plan : `request_advice`
   (`server/plan_advisor.py:556`) borne l'indice sur `prepare_plan(voy)`,
   dont les jambes viennent de `legs_from_clock(clock…) if clock.get("t0")
   else []` (`server/plan_alerts.py:87`) — **zéro jambe** tant que l'horloge
   du voyage officiel n'est pas posée. Indice hors bornes → `ValueError`
   (`plan_advisor.py:567`) → HTTP 400 (`server/voyage_api.py:1258`), et le
   client re-sonde à chaque rafraîchissement de la revue. → **RF1**.
2. `POST /voyage` → **500 puis 429**, `GET /ici` → **500**, `/ici/moment`,
   `/ici/pearls`, `/ici/warm/status`, `/voyage/official/eta`, `plan-review`,
   `/api/v1/polar/…/client` → **500** : le serveur du poste tombe sur le
   parcours nominal. À reproduire par les **logs** (ne pas coder à
   l'aveugle) ; points lus dans le code : la création de voyage recalcule
   l'horloge climatologique **en synchrone à chaque POST**
   (`server/voyage_api.py:516`, `_climo_clock` sur ~1 200 sommets) ; en cas
   d'échec, le client **recrée en boucle** (`src/hooks/useVirtualVessel.js:156`,
   `create()` relancé à chaque changement d'identité des entrées, sans repli)
   jusqu'au limiteur `voyage-create` 6/min → **429**
   (`server/voyage_api.py:79`) ; la lecture des polaires n'a **aucune garde**
   (`server/polar_api.py:40` `json.load`, `:82` `data["raw"]` — un fichier
   corrompu ou à l'ancien format → 500 à chaque GET, et le bandeau « Échec —
   Service des polaires indisponible »). Conséquence directe : **journal
   vide** (KO #327, #331, #333, #334) — sans voyage officiel, pas de moments
   à lire. Réponse en deux lots (commentaires PR #336) : **RF9** — le voyage
   officiel est **précalculé et stocké**, le serveur **sert** et ne calcule
   plus au moment de la demande ; **RF2** — la robustesse (plus de 500 bruts,
   polaires gardées, re-créations espacées), sans plus rien recalculer
   lui-même. → **RF9**, **RF2**.
3. `404 /bi/climatology/wind/tiles/…` (#334, console D) : la route des tuiles
   n'existe pas sur le backend BI du poste — c'est le **déploiement** de la
   PR #317, déjà tranché (plan s2 § 3) ; le repli client est codé (RE6,
   PR #330). Rien à replanifier. → § 3.
4. `ERR_CONNECTION_CLOSED` / `ERR_HTTP2_PROTOCOL_ERROR` en rafale : le même
   serveur qui tombe (point 2) ferme ses connexions ; RF2 traite la cause
   applicative, et si ces erreurs survivent à RF2 en prod, c'est un ticket
   infra (décision du 23 conservée). → **RF2** + § 3.

**Priorité 2 — Les erreurs de console pendant le film.** Pendant « Revoir
l'expédition », le bateau **du film** alimente les mêmes hooks que le bateau
live : `useIciDossier` reste branché sur `cast` (`src/App.jsx:722`,
`enabled: Boolean(cast)` — seules les *stories* sont coupées, `:723`) et
re-sonde `/ici` tous les 3 milles (`src/hooks/useIciDossier.js:17`
`MOVE_NM = 3`, re-planification l.218-247) : un tour du monde en ~2 minutes →
des **centaines de requêtes**, chacune en 500 sur le poste (compteur console
> 1 000, #333) ; même mécanique pour l'ETA d'escale re-sondée pendant le film
(`src/components/EscaleLegend.jsx:108` + `usePlanReview.js:351`). Avec RF9,
le film **lit le stock** (script, sacs par point) : RF3 devient trivial —
geler les hooks pendant le film, un rattrapage à l'arrêt. → **RF3** (après
RF9).

**Priorité 3 — Le discours du film.** Les six règles (dédoublonner par nom,
sans nom = silence, trié par la route, vocabulaire juste, chronologie stricte
et sauts d'avion dits, dernière jambe fermée) sont **le lot RE7, codé**
(PR #331) — pas replanifiées ici. Ce qui reste après la recette de nuit :
(a) le bot n'entend **pas l'avion** alors que les phrases existent dans le
code de la pile (`server/film_script.py:1415-1417`, fenêtres `vehicle`
`:384-392`, rattrapage `:1993-2022`) — cause à reproduire sur le film
officiel complet (fenêtre avion perdue par la fusion/sélection sous
`targetSeconds` ≈ 108 s, ou `vehicle` absent des marques du voyage semé) ;
(b) le sous-titre de fin (« Aujourd'hui, le bateau est à… ») **disparaît**
avec la barre récit dès que le film s'arrête (KO bot #333) ; (c) « le récit ne
contient aucun événement » (KO #331) est le fil rouge serveur — RF9 + RF2.
→ **RF4** (a et b), **RF9** + **RF2** (c).

**Priorité 4 — La cinématique du film.** « Un vrai film — caméra qui suit le
bateau, mouvements fluides, pas une série de sauts ; zoom stable pendant une
jambe. » Cause lue : la caméra du film avance par `setView(…, animate: false)`
**à chaque frame React** (`src/map/filmCamera.js:174`, appelé depuis la boucle
rAF de `useReplay` qui pose `setTMs` à 60 Hz — `src/hooks/useReplay.js:688` —
donc un re-render complet de l'app par frame), avec un pan borné à 2 % de
l'écran par frame (`src/engine/replay.js:31`) et un `flyTo` de 1,2 s au
changement de chapitre : dès que la cadence chute (rendu React + Leaflet +
couches), la caméra **saute** de position en position ; et les déplacements
permanents laissent le fond de carte en **damier gris** (tuiles jamais
chargées — captures #331, #333, #334). Le zoom par chapitre est déjà stable
(`filmChapterZoom`). → **RF5**.

**Décisions actées :**

- **D1' — Accueil (remplace D1 du plan s2).** « Ce que je voulais c'est que
  l'application s'ouvre en mode **Suivre** + Cinéma + carte monde entière
  (dézoomée) » (KO #325). La demande la plus récente l'emporte : l'accueil
  passe de Simulation (RE1) à **Suivre**, Cinéma enfoncé, monde entier,
  **aucun recadrage automatique** sur le bateau au chargement. Le clic sur
  « Suivre l'expédition » garde son recadrage (case cochée par le porteur
  sur #325) ; la bascule Suivre → Simulation garde D2 du plan s2 (Cinéma
  décoché, deux panneaux ouverts). → **RF6**.
- **D2' — Liste des escales (étend D3 du plan s2).** « Le mieux c'est que les
  escales… soient juste informatives **quel que soit le mode** » (KO #326).
  Le clic-ligne de la Simulation (déplacer le curseur) disparaît aussi ; la
  liste n'est plus cliquable nulle part. → **RF7**.
- **D3' — Barre de lecture : pilules gardées et remises dans le cadre
  (lecture du KO #327 corrigée par le porteur, PR #336).** Les pilules
  **2:30 / 3:00 restent** (décochées par défaut, RD7 ; le film sans durée
  reste le défaut) mais **ne débordent plus** du cadre de la barre film et
  **ne passent plus sous le panneau droit** quand il est ouvert (captures du
  porteur, 26 sept. 18:10 : les pilules sortent du cadre à droite de « Revoir
  l'expédition »). La barre s'adapte à la largeur disponible (panneau droit
  ouvert ou fermé) : les pilules restent dans son cadre, à côté de « Revoir
  l'expédition », ou passent **sous lui** si la place manque — jamais hors
  cadre, jamais sous un panneau. « **Récit : règles** » (jamais demandé) est
  retiré ; l'encadré date + heure de départ prend **exactement** la place du
  format « XX-XX-XXXX XX:XX ». → **RF7**.
- **D4' — Tracer.** « En mode Tracer, l'application affiche une carte monde
  entièrement dézoomée » ; le bug qui **refuse de dézoomer** est à reproduire
  et corriger. → **RF6**.
- **D5' — Le voyage officiel est précalculé et stocké (commentaires du
  porteur sur la PR #336).** RF2 et RF3 réduisaient la charge mais laissaient
  le serveur *calculer à la demande* (au démarrage, à chaque voyage, pendant
  le film). Principe inverse pour le **voyage officiel** : journal des
  moments, script du film, ETA et fourchettes par escale, climatologie et
  fiches par point de la route, sac « ici » par point, plan review sont
  **précalculés une fois** et **stockés de façon persistante** (base de
  données — MongoDB est déjà sur le VPS — ou fichiers sur disque, au choix,
  mais qui survit aux redémarrages **et aux déploiements**), puis **servis
  tels quels** par l'API. Règles : une seule version par (route officielle,
  t0, date des données) ; un **travail de fond** met à jour le stock quand
  une entrée manque ou vieillit, jamais dans le chemin d'une requête ; l'API
  répond depuis le stock en **< 200 ms** et n'appelle plus les fournisseurs
  externes (Copernicus, Open-Meteo, atlas BI, LLM) au moment de la demande ;
  entrée manquante → réponse honnête « **en préparation** », pas un 500 ni un
  recalcul synchrone ; le poste de recette part avec un **stock déjà rempli**
  (le script de recette le remplit ou le copie). → **RF9** (avant RF2) ;
  RF2 garde ses corrections de robustesse mais ne recalcule plus rien
  lui-même ; RF3 devient trivial (le film lit le stock).

## 3. Ce qui est reporté ou fondu, et pourquoi

- **Globe (lots à venir G1, G4, G5, G6)** : constats de cette session fondus
  dans leurs prompts (« Constat de la revue du 26 sept., session 4 ») :
  **G1** (caméra initiale — l'accueil devient Suivre + monde, D1' remplace le
  constat RE1) ; **G4** (roses en couches symbol décimées, jamais un nœud DOM
  par rose — parité RF8) ; **G5** (liste des escales informative dans tous
  les modes — parité RF7/D2') ; **G6** (caméra du film continue, parité RF5).
  Aucun autre lot à venir (G0, G2, G3, G7, H1) ne couvre un constat de cette
  revue.
- **Fourchette d'arrivée (#329, « idem pré-revue »)** : le lot **RE5 est
  codé** (PR #329 : sondes plafonnées, raison honnête quand `members: 0`,
  relances espacées) ; sur le poste, l'ETA restait à `members: 0` avec
  `ERR_CONNECTION_CLOSED` — l'ensemble n'a pas pu être re-testé sur un
  serveur sain. L'ETA et les fourchettes par escale font partie du **stock
  RF9** (précalculées, servies telles quelles). Re-recetter **après merge de
  la pile + RF9 + RF2** ; si la raison
  affichée est un quota de l'API ensemble, c'est une décision du porteur
  (clé, autre source) — pas un nouveau lot aujourd'hui.
- **404 tuiles climatologie (#334, console D)** : route absente du backend BI
  du poste — livrée par le merge de la PR #317 (le déploiement suit `main`) ;
  le repli client est codé (RE6, PR #330). Déjà tranché au plan s2 § 3.
- **Chat « Quel vent au bateau ? » sans réponse (#334)** : « aucun modèle n'a
  répondu » — clés / modèles de la cascade (L1, L2) absents ou épuisés sur le
  poste de recette : environnement, pas un défaut de code. À re-vérifier sur
  le poste préparé par le script de recette ; si l'échec persiste avec des
  clés valides, ouvrir un lot au prochain cycle.
- **`ERR_CONNECTION_CLOSED` / `ERR_HTTP2_PROTOCOL_ERROR`** : conséquence du
  serveur qui tombe (§ 2, priorité 1, point 4) — la cause applicative est
  RF2 ; s'ils survivent à RF2 en prod, ticket infra (décision du 23
  conservée).
- **RC10 / RC11 (#333, #334) « revue non faite »** : ce ne sont pas des refus
  de leur code — le Journal vide (RF2) a bloqué la recette. Leurs cases
  restent à cocher au prochain passage, sur un poste sain. Le seul défaut
  observé de leur périmètre (sous-titre de fin absent après l'arrêt) part
  dans **RF4**.
- **Cases décochées sans KO (#327 items 1, 2, 3 et 5 ; #329 ; #331 ; #334)** :
  toutes bloquées par le serveur du poste (journal vide, fourchette absente) —
  re-recette après RF2, aucune n'est orpheline d'un plan.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour App.jsx et MapSceneController.js). « Recette » = ce que le
porteur voit dans Chrome, par écran. Ancres `fichier:ligne` = tête de pile
#334 (= `main` après merge). Pile linéaire RF1 → **RF9** → RF2 → RF3 → … →
RF8 (RF9 inséré avant RF2 sur les commentaires de la PR #336), dans l'ordre
des priorités du porteur.

### RF1 — Console : plus jamais de 400 sur `/voyage/official/advice` (S)

Cause racine : le client calcule l'indice de la jambe la plus chargée sur les
jambes de `/voyage/official/plan-review` (`src/hooks/usePlanReview.js:118`
`pickHeaviestLegIdx`, choisi `:434`, envoyé `:253-257`
`defaultAdviceFetch`) ; le serveur applique cet indice à un plan **différent** :
`request_advice` (`server/plan_advisor.py:556`) borne sur
`prepare_plan(voy)`, dont les jambes viennent de
`legs_from_clock(clock…) if clock.get("t0") else []`
(`server/plan_alerts.py:87`) — **0 jambe** tant que l'horloge officielle
n'est pas posée, et un compte différent de celui de la revue sinon. Indice
hors bornes → `ValueError` (`plan_advisor.py:567`) → HTTP 400
(`server/voyage_api.py:1258`), re-sondé à chaque rafraîchissement de la revue
(toutes les `REFRESH_MS`) : le 400 apparaît sur **tous** les écrans, toutes
les PR.

Fichiers : `server/voyage_api.py` PAR EXTRAIT (`rg -n "official/advice"`),
`server/plan_advisor.py`, `server/plan_alerts.py` (lecture),
`src/hooks/usePlanReview.js`, `server/tests/test_plan_advisor.py`,
`src/hooks/usePlanReview.test.js`.

Étapes :
1. Une seule vérité pour l'indice : le conseil accepte l'indice **des jambes
   de la revue** (même référentiel que `plan-review`), ou traduit
   explicitement l'un vers l'autre — au choix du lot, documenté dans la PR.
2. Une jambe hors du plan préparé (horloge absente, jambe passée) ne répond
   plus 400 : réponse 200 avec un état honnête (`unavailable` + raison), que
   le client sait lire — il **cesse de re-sonder** jusqu'au prochain
   changement de revue.
3. Aucun 4xx/5xx dans la console au parcours nominal Suivre / Simulation /
   Tracer pour ce endpoint.
4. Tests : fixture voyage sans horloge → advice répond un état sans erreur
   HTTP ; indice de la revue = indice accepté par le serveur ; le client ne
   re-sonde pas après `unavailable`.

Recette (visuelle) :
- Suivre, console ouverte, recharger et rester 2 minutes : **tu ne dois
  voir** aucune ligne rouge `advice` (ni 400 ni autre).
- Simulation et Tracer : même vérification.
- Panneau gauche, onglet Revue du plan : la revue s'affiche comme avant
  (conseil compris quand il existe).

### RF9 — Le voyage officiel est précalculé et stocké : le serveur sert, il ne calcule plus (M)

Principe (D5', commentaires du porteur sur la PR #336) — pas un bug mais un
renversement : RF2 et RF3 réduisent la charge mais laissent le serveur
**calculer à la demande** — au démarrage (`startup_official_voyage` +
préchauffages, `server/main.py:84-135`, `voyage_api.py:763`), à chaque voyage
(`_climo_clock` en synchrone à chaque `POST /voyage`,
`server/voyage_api.py:516`), pendant le film (`/ici` et ETA re-sondés). Pour
le **voyage officiel**, tout ce dont Suivre et Revoir ont besoin est
**précalculé une fois**, **stocké de façon persistante**, puis **servi tel
quel** par l'API.

Périmètre du stock : journal des moments, script du film, ETA et fourchettes
par escale, climatologie et fiches par point de la route, sac « ici » par
point, plan review.

Règles :
- **une seule version** par (route officielle, t0, date des données) — c'est
  la clé de version du stock ;
- un **travail de fond** (au boot puis périodique) met à jour le stock quand
  une entrée **manque ou vieillit** — jamais dans le chemin d'une requête ;
- l'API répond **depuis le stock en < 200 ms** et n'appelle **plus aucun
  fournisseur externe** (Copernicus, Open-Meteo, atlas BI, LLM) au moment de
  la demande ;
- entrée manquante → réponse honnête « **en préparation** » (état propre que
  le client sait afficher), **jamais** un 500 ni un recalcul synchrone ;
- le poste de recette part avec un **stock déjà rempli** : le script de
  recette le remplit (ou le copie) avant d'ouvrir Chrome.

Où vit le stock — au choix du lot, documenté dans la PR : **fichiers /
SQLite sur disque** dans `voyage_dir()` (la base `naviguide.sqlite` de
`server/pearl_store.py` existe déjà, avec les tables `moments` et `kv` ;
répertoire `NAVIGUIDE_VOYAGE_DIR`, défaut `server/voyage_data/`) **ou
MongoDB** (déjà en place sur le VPS, `127.0.0.1:27017`). Sur le **poste** :
le `voyage_dir()` du checkout, rempli par le script de recette. Sur le
**VPS** : `NAVIGUIDE_VOYAGE_DIR` pointé sur un répertoire **hors du dossier
de déploiement** (ex. `/home/ubuntu/naviguide-data/`, réglé dans
`~/.config/naviguide/simulator.env`) — le stock survit aux redémarrages **et
aux déploiements**. Premier démarrage : stock vide → le travail de fond le
remplit ; l'API répond « en préparation » entre-temps, jamais une erreur.

Fichiers : `server/voyage_api.py` PAR EXTRAIT
(`rg -n "startup_official_voyage|official"`), `server/main.py` PAR EXTRAIT
(`rg -n "startup"`), `server/pearl_store.py`, `server/voyage_store.py`,
nouveau module du stock (ex. `server/official_store.py`), `server/tests/`
(tests du stock).

Étapes :
1. Le module du stock : clé (route officielle, t0, date des données),
   lecture/écriture des six familles du périmètre, horodatage par entrée,
   remplacement atomique d'une version par la suivante.
2. Le travail de fond : au boot puis périodiquement, il compare le stock à la
   clé courante, calcule ce qui manque ou a vieilli et remplace — hors du
   chemin des requêtes : jamais un client n'attend un calcul.
3. Les routes du voyage officiel (journal, script du film, ETA et
   fourchettes, climatologie et fiches, sac « ici », plan review) répondent
   **depuis le stock** ; plus aucun appel Copernicus / Open-Meteo / atlas BI /
   LLM au moment de la demande ; entrée absente → état « en préparation ».
4. Le script de recette remplit (ou copie) le stock avant d'ouvrir le
   navigateur : sur le poste préparé, le porteur ne voit jamais « en
   préparation ».
5. Tests : clé identique → aucun recalcul ; entrée manquante → « en
   préparation » sans 500 ni recalcul synchrone ; fournisseurs externes
   mockés pour échouer s'ils sont appelés pendant une requête → les réponses
   passent quand même ; le stock relu après un redémarrage simulé sert les
   mêmes données.

Recette (visuelle) :
- Poste préparé (script de recette), Suivre : le Journal, la fourchette
  d'arrivée et la Revue du plan s'affichent **immédiatement** au chargement —
  aucune attente, aucune ligne rouge en console.
- Recharger la page : aussi immédiat — rien ne se recalcule.
- Revoir l'expédition : le film part sans délai (le script est lu du stock).

### RF2 — Le serveur tient debout : plus de 500/429 au parcours nominal, le Journal se remplit (M, après RF9)

Cause racine (à **confirmer sur poste par les logs** avant de coder — ne pas
deviner) : sur le poste de recette, `POST /voyage` répond 500 puis 429,
`GET /ici` 500, et tout le voyage officiel suit (`/ici/moment`, `/ici/pearls`,
`/ici/warm/status`, `/voyage/official/eta`, `plan-review`,
`/api/v1/polar/…/client` en 500) → **Journal vide**, récit sans événement,
ligne d'état retombée sur le trajet de la Simulation (KO #327, #331, #333,
#334). Points lus dans le code : la création de voyage recalcule l'horloge
climatologique **en synchrone à chaque POST** (`server/voyage_api.py:516`,
`_climo_clock` = `build_voyage_clock` sur ~1 200 sommets, `:142-150`) ; en
cas d'échec le client **recrée en boucle** (`src/hooks/useVirtualVessel.js:156`,
`create()` relancé sans repli progressif) jusqu'au limiteur `voyage-create`
6/min → 429 (`server/voyage_api.py:79`) ; la lecture des polaires est sans
garde (`server/polar_api.py:40` `json.load` d'un fichier possiblement
corrompu, `:82` `data["raw"]` KeyError sur un format ancien → 500 et bandeau
« Échec — Service des polaires indisponible », capture #325) ; le semis et
les préchauffages partent tous au boot (`server/main.py:84-135`,
`startup_official_voyage` `voyage_api.py:763` + warms en fils).

Périmètre après RF9 (commentaires PR #336) : les recalculs (horloge climato,
semis, préchauffages, journal) appartiennent au **stock et au travail de fond
de RF9** — RF2 garde ses **corrections de robustesse** (plus de 500 bruts,
erreurs propres et datées, polaires gardées, repli progressif du client) mais
**ne recalcule plus rien lui-même**.

Fichiers : `server/voyage_api.py` PAR EXTRAIT
(`rg -n "create_voyage|_climo_clock|_create_limited"`), `server/polar_api.py`,
`server/main.py` PAR EXTRAIT (`rg -n "startup|/ici"`),
`src/hooks/useVirtualVessel.js`, `server/tests/test_voyage_api.py`,
`server/tests/` (test polaires).

Étapes :
1. Reproduire sur poste (journal uvicorn/systemd pendant le parcours
   nominal) ; noter la ou les exceptions exactes (fichier:ligne) dans la PR.
2. Plus aucun 500 brut sur le parcours nominal : chaque cause trouvée est
   corrigée ; les handlers concernés répondent une erreur propre et datée
   (raison lisible) quand une dépendance manque — jamais une stack avalée.
3. Polaires : un fichier stocké corrompu ou à l'ancien format ne casse plus
   la route — repli sur la polaire par défaut, avertissement en log, et le
   panneau droit garde « Polaires chargées ».
4. La création du voyage officiel ne recalcule **rien** dans le chemin de la
   requête : l'horloge climato et le journal sont **lus du stock RF9** (une
   entrée absente répond « en préparation », le travail de fond la produit) ;
   le client espace ses re-créations (repli progressif) au lieu de marteler
   jusqu'au 429.
5. Le Journal (panneau gauche) se remplit des événements **depuis le départ**
   (lus du stock RF9) dès que le serveur est sain — c'est la définition du
   fini de ce lot.
6. Tests : fixture polaire corrompue → 200 avec repli ; création de voyage en
   échec → le client attend avant de retenter (pas de 429) ; parcours nominal
   sous TestClient sans aucun 500.

Recette (visuelle) :
- Poste relancé (script de recette), Suivre, console ouverte, 3 minutes :
  **aucune ligne rouge** (`/voyage`, `/ici`, polaires, climatologie).
- Panneau gauche, onglet Journal : **rempli des événements depuis le départ**
  (15 mai 2026), pas une seule ligne.
- Ligne d'état de la barre : le voyage LIVE (jour > 100, milles parcourus),
  plus jamais « 0 nm · j0 · Saint-Maur → La Rochelle » après chargement.
- Panneau droit : « Polaires chargées », plus jamais « Échec — Service des
  polaires indisponible ».

### RF3 — Pendant le film : le client ne mitraille plus l'API — le film lit le stock (S, après RF9)

Cause racine : pendant « Revoir l'expédition », le bateau du film alimente
les hooks du live — `useIciDossier` reste actif (`src/App.jsx:722`,
`enabled: Boolean(cast)` ; seules les stories sont coupées `:723`
`stories: !replay.active`) et re-sonde `/ici` dès que le bateau a bougé de
3 nm (`src/hooks/useIciDossier.js:17` `MOVE_NM = 3`, re-planification et
re-fetch au posé du sac l.218-247) : un tour du monde en ~2 minutes déclenche
des centaines de `GET /ici?lat=…` (rafale > 1 000 entrées console, KO bot
#333, #331) ; l'ETA d'escale est re-sondée au fil des changements de jambe du
film (`src/components/EscaleLegend.jsx:108`, `usePlanReview.js:351`
`useOfficialEta`). Après RF9, ce lot devient **trivial** : tout ce que le
film montre (script, sacs par point, ETA) est déjà dans le **stock** — il ne
reste qu'à geler les hooks du live pendant le film.

Fichiers : `src/App.jsx` PAR EXTRAIT (`rg -n "useIciDossier|replay.active"`),
`src/hooks/useIciDossier.js`, `src/components/EscaleLegend.jsx` PAR EXTRAIT
(`rg -n "useOfficialEta"`), `src/hooks/usePlanReview.js` PAR EXTRAIT,
tests associés.

Étapes :
1. Pendant `replay.active`, le sac « ici », `/ici/moment`, l'ETA d'escale et
   le conseil restent **gelés sur la position live** (celle d'avant le film) —
   aucune requête déclenchée par la position du film ; ce que le film montre
   vient du **stock RF9** (script, sacs par point), déjà chargé au lancement.
2. À l'arrêt du film (Stop ou fin), **une seule** requête de rattrapage
   remet le sac et l'ETA à jour sur la position live.
3. Ne rien changer au film lui-même (récit, caméra, sous-titres) ni au
   comportement hors film.
4. Tests : simulation d'un replay qui traverse 3 000 nm → zéro appel `/ici`
   pendant le film, un appel après l'arrêt ; l'ETA n'est pas re-sondée
   pendant le film.

Recette (visuelle) :
- Suivre, console ouverte, Revoir l'expédition sans durée cochée, laisser
  le film aller **du lancement à la fin** : **aucune ligne rouge** et le
  compteur réseau ne s'affole plus (plus jamais > 1 000 requêtes).
- Même vérification avec la pilule 2:30 cochée (les pilules restent, D3').
- Après Stop : le panneau gauche montre à nouveau le sac de la position live.

### RF4 — Le récit dit l'avion, et la fin du film reste affichée (S, après RF2)

Cause racine : les phrases d'avion **existent** sur la tête de pile
(`server/film_script.py:1415` « retour en avion vers… », `:1417`
« l'équipage prend l'avion pour… », fenêtres `vehicle` `:384-392` et `:1448`,
rattrapage depuis les moments `:1993-2022` et `:2107-2110`) mais le bot ne
les entend pas (KO #331 : sous-titres nomment Cayenne, aucun « avion »,
chapitres 0–2, ~107 s) — cause à **reproduire** sur le film officiel
complet : fenêtre avion perdue par la fusion/sélection des chapitres sous
`targetSeconds` ≈ 108 s, ou `vehicle` absent des marques du voyage semé —
documenter fichier:ligne dans la PR. Fin du film : quand le film s'arrête, la
barre récit disparaît et le sous-titre « Aujourd'hui, le bateau est à… »
n'est jamais visible (KO bot #333) — le dernier chapitre est fermé dans le
script (RE7) mais l'UI ne le laisse pas à l'écran.

Fichiers : `server/film_script.py`, `server/tests/test_film_script.py`,
`src/hooks/useReplay.js` PAR EXTRAIT (`rg -n "finish|subtitle"`),
`src/components/SimulationFilmBar.jsx` PAR EXTRAIT (`rg -n "subtitle|récit"`),
tests associés.

Étapes :
1. Reproduire sur le film officiel complet (poste sain après RF2) : générer
   le script sans budget, vérifier la présence des phrases d'avion aux jambes
   Cayenne ↔ Halifax ; noter la cause exacte de leur absence à l'écoute.
2. La sélection/fusion des chapitres ne peut **jamais** faire tomber une
   phrase d'avion : une jambe avion est dite (aller et retour), quel que soit
   le budget.
3. À la fin du film, le sous-titre de clôture (« Aujourd'hui, le bateau est
   à… ») reste **visible** à l'écran (dans la barre ou l'encadré du récit)
   tant que l'utilisateur n'a pas repris la main — l'arrêt ne l'efface pas.
4. Tests : fixture avec jambe avion + budget serré → le script garde l'avion
   aller et retour ; l'état de fin du replay conserve le dernier sous-titre.

Recette (visuelle) :
- Suivre, Revoir l'expédition sans durée : au passage de la Guyane, **tu dois
  entendre** l'avion (aller **et** retour) — plus aucun bateau téléporté.
- Laisser le film finir : **tu dois voir** « Aujourd'hui, le bateau est à… »
  rester affiché après la fin.
- Le récit contient les événements du journal (poste sain), plus jamais le
  seul enchaînement « départ vers Ajaccio ».

### RF5 — Cinématique : un vrai film — caméra qui suit, mouvements fluides, zoom stable, fond visible (M)

Cause racine : la caméra du film est pilotée par le rendu React — la boucle
rAF de `useReplay` pose `setTMs` à chaque frame (`src/hooks/useReplay.js:688`)
→ re-render de l'app à 60 Hz → `applyFilmCamera` fait un
`map.setView(…, { animate: false })` par frame (`src/map/filmCamera.js:174`),
pan borné à 2 % de l'écran par frame (`src/engine/replay.js:31`
`FILM_PAN_MAX_SCREEN`), `flyTo` 1,2 s au changement de chapitre : dès que la
cadence réelle chute (re-render + Leaflet + couches), la caméra avance par
**sauts** visibles — exactement « une série de sauts d'une position à
l'autre » (priorité 4). Les déplacements permanents laissent le fond de carte
en **damier gris** (tuiles jamais chargées — captures #331, #333, #334). Le
zoom par chapitre est déjà stable (`filmChapterZoom`, `filmCamera.js:74-107`) :
le conserver.

Fichiers : `src/map/filmCamera.js`, `src/map/MapSceneController.js` PAR
EXTRAIT (`rg -n "syncFilmCamera|filmActive"`), `src/hooks/useReplay.js` PAR
EXTRAIT (`rg -n "setTMs|requestAnimationFrame"`), `src/engine/replay.js`
(lecture), `src/map/filmCamera.test.js`, tests associés.

Étapes :
1. Découpler la caméra du rendu React : une boucle impérative (rAF côté
   contrôleur de carte) interpole la position caméra entre les échantillons
   du film — le bateau **glisse**, la caméra suit sans à-coups, même si le
   rendu React rame.
2. Zoom constant pendant toute une jambe (comportement `filmChapterZoom`
   conservé) ; un seul mouvement de transition au changement de jambe.
3. Le fond de carte reste visible : le mouvement laisse aux tuiles le temps
   de se charger (vitesse de pan bornée par la disponibilité du cache, ou
   préchargement des tuiles le long de la jambe au zoom du chapitre) — plus
   de damier gris en milieu de chapitre.
4. Ne rien changer au script, à la voix ni aux sous-titres.
5. Tests : sur un replay simulé à cadence dégradée (frames espacées), les
   positions caméra successives restent monotones et espacées d'au plus le
   pas borné (pas de saut) ; le zoom ne varie pas dans une jambe ;
   `npm run e2e` du lot mesure le zoom stable sur 4 s (gabarit REGLES § 5).

Recette (visuelle) :
- Suivre, Revoir l'expédition : **tu dois voir** la caméra suivre le bateau
  qui glisse — aucun saut de position, aucun à-coup au milieu d'une jambe.
- Pendant une jambe : le zoom ne bouge pas ; au changement de jambe : un
  seul mouvement doux.
- Le fond de carte reste dessiné (océan, côtes) pendant tout le film — plus
  de damier gris.

### RF6 — Accueil en Suivre + Cinéma + monde (D1') ; Tracer s'ouvre monde entier et dézoome librement (D4') (S)

Cause racine : accueil — `src/App.jsx:169` (`useState(VIEW_SIMULATION)`, posé
par RE1 sur la décision D1 du plan s2, que le KO #325 **remplace**) ; en
Suivre, l'entrée recadre sur le bateau (`selectView`, branche
`next === VIEW_SUIVRE` `App.jsx:996-1006`, `recaptureBoat()` `:1006`) — au
**chargement** il ne faut ni recadrage ni dépendance au serveur (le bot a vu
la caméra rester monde uniquement parce que `POST /voyage` 500 — le
comportement voulu par D1' devient la règle, réseau sain ou pas). Le reste de
RE1 (bascule Suivre → Simulation : Cinéma décoché, panneaux ouverts — cases
cochées #325) ne bouge pas. Tracer — le porteur voit l'application « buguer
et refuser de dézoomer » (KO #327) : à reproduire dans Chrome (candidats lus :
`minZoom: 2` + `maxBounds` à viscosité 1, `src/map/MapSceneController.js:196-205` —
sur un écran large, le zoom minimal effectif imposé par les bornes peut
dépasser 2 ; caméra du mode dessin) — corriger la cause constatée,
documenter fichier:ligne dans la PR ; à l'**entrée** en Tracer, la carte
montre le monde entier dézoomé.

Fichiers : `src/App.jsx` PAR EXTRAIT
(`rg -n "VIEW_SIMULATION|selectView|recaptureBoat|cinemaMode"`),
`src/map/MapSceneController.js` PAR EXTRAIT
(`rg -n "minZoom|maxBounds|MAP_MAX_BOUNDS"`), `src/App.test.jsx` (ou tests
d'état de vue existants), `e2e/lots/` (spec du lot).

Étapes :
1. État initial : vue **Suivre**, `cinemaMode` vrai, panneaux fermés, carte
   monde entière (zoom initial) — **aucun recadrage automatique** sur le
   bateau au chargement, quel que soit l'état du serveur.
2. Le **clic** sur « Suivre l'expédition » (depuis un autre mode, ou reclic)
   garde son comportement : Cinéma + caméra sur le bateau (case cochée #325).
   La bascule Suivre → Simulation garde RE1/D2 (Cinéma décoché, deux panneaux
   ouverts).
3. Tracer : reproduire le refus de dézoom, corriger ; à l'entrée en Tracer la
   carte montre le monde entier ; le dézoom molette/boutons descend toujours
   jusqu'à la vue monde.
4. Tests : au montage, vue Suivre + Cinéma actif + pas de recadrage ; après
   clic Suivre, recadrage ; en Tracer, le zoom minimal atteint la vue monde.

Recette (visuelle) :
- Recharger l'application → **tu dois voir** la carte monde entière
  (dézoomée), **Suivre** enfoncé, **Cinéma** enfoncé, les deux panneaux
  fermés, la barre film seule en bas.
- Cliquer **Simulation** puis revenir par **Suivre l'expédition** → la caméra
  se pose sur le bateau (comme avant).
- **Tracer ma route** → **tu dois voir** la carte monde entièrement dézoomée ;
  molette arrière n'importe où : la carte dézoome jusqu'à la vue monde, sans
  blocage.

### RF7 — Liste des escales informative partout (D2') ; barre : pilules 2:30 / 3:00 dans le cadre, « Récit : règles » retiré, encadré date au format (D3') (S)

Cause racine : liste — les lignes restent des boutons hors Suivre :
`src/App.jsx:1668` (`onSeekEscale={isSuivre ? undefined : handleSidebarSeek}`,
posé par RE2 sur D3, que le KO #326 **étend**) → `ToolsSidebar.jsx:213` →
`EscaleLegend.jsx:31-60` (`interactive = typeof onSeek === "function"`).
Barre — pilules : le bloc `film-duration`
(`src/components/SimulationFilmBar.jsx:467-489`) **déborde du cadre de la
barre** à droite de « Revoir l'expédition » et **passe sous le panneau
droit** quand il est ouvert (captures du porteur, 26 sept. 18:10) : la barre
ne s'adapte pas à la largeur disponible et les pilules ne passent jamais à la
ligne. Le porteur les **garde** (décochées par défaut, RD7) et demande de
corriger **leur place** — lecture du KO #327 corrigée par ses commentaires
sur la PR #336 ; « Récit : règles » : `SimulationFilmBar.jsx:377`
(`filmStorySource` = « Récit : {source} », `src/i18n/fr.js:238`) — jamais
demandé ; encadré date/heure : conteneur `replay-departure` figé à
`w-[9.75rem]` + champ heure séparé (`SimulationFilmBar.jsx:428-436`) — le
porteur veut la taille **exacte** du format « XX-XX-XXXX XX:XX ».

Fichiers : `src/App.jsx` PAR EXTRAIT (`rg -n "onSeekEscale"`),
`src/components/EscaleLegend.jsx`, `src/components/SimulationFilmBar.jsx` PAR
EXTRAIT (`rg -n "film-duration|filmStorySource|replay-departure"`),
`src/i18n/fr.js`, `src/i18n/en.js`, `src/components/filmBarLayout.test.js`.

Étapes :
1. Liste des escales : plus aucun `onSeek` passé, dans **aucun** mode — les
   lignes affichent nom, distance, date, jours à quai, fourchette ; pas de
   curseur main, aucune action au clic (le clic-curseur de la barre film
   reste, lui, inchangé).
2. Pilules 2:30 / 3:00 : **gardées** (décochées par défaut ; le film sans
   durée reste le défaut ; l'API de budget RD7 n'est pas touchée). La barre
   s'adapte à la **largeur disponible** (panneau droit ouvert ou fermé) : les
   pilules restent **dans le cadre de la barre**, à côté de « Revoir
   l'expédition », ou passent **sous lui** si la place manque — jamais hors
   cadre, jamais sous un panneau. Test de layout mis à jour.
3. « Récit : règles » : libellé retiré de la barre (la source du récit reste
   lisible dans la PR / les tests, pas à l'écran).
4. Encadré date + heure de départ : une seule boîte à la taille du contenu
   « XX-XX-XXXX XX:XX » (largeur au format, pas un rem arbitraire), mêmes
   valeurs, même comportement.
5. Tests : EscaleLegend sans gestionnaire de clic dans tous les modes ; le
   layout de la barre garde `film-duration` **dans le cadre** (panneau droit
   ouvert et fermé) et ne contient plus « Récit : » ; la boîte date/heure a
   la largeur de son format.

Recette (visuelle) :
- Suivre **et** Simulation, panneau droit, liste des escales : le pointeur ne
  devient jamais une main ; cliquer une escale → **rien ne se passe**.
- Suivre, barre film, panneau droit **fermé puis ouvert** : les pilules
  **2:30 / 3:00 restent dans le cadre de la barre**, à côté de « Revoir
  l'expédition » (ou dessous si la place manque) — jamais coupées, jamais
  sous le panneau ; **plus de « Récit : règles »** ; l'encadré date + heure
  fait exactement la taille de « 15-05-2026 08:00 » ; le bouton « Revoir
  l'expédition » respire.
- Le film se lance toujours (sans durée par défaut, pilules décochées).

### RF8 — Roses de vent : zoom fluide, l'application ne se fige plus (M)

Cause racine : chaque rose est un `L.marker` avec `divIcon` SVG — un nœud DOM
par rose (`src/layers/useClimatologyLayer.js:178-190` `makeWind`), dupliqué
pour chaque copie du monde (`:132-135` boucle `climoPointLngs` — ×3), et le
groupe entier est **reconstruit à chaque `zoomend`/`moveend`**
(`:294-295` → `onView`, reconstruction `:126-145` `addPointMarkers` /
`replaceGroup`) ; au détail natif des tuiles RD8 (1° au zoom), des centaines
de nœuds DOM sont jetés et recréés à chaque cran de zoom → « le zoom est très
lent et l'appli se fige » (KO #330).

Fichiers : `src/layers/useClimatologyLayer.js`,
`src/layers/climatologyPaint.js` (lecture), `src/layers/climoTiles.js`
(lecture), `src/layers/useClimatologyLayer.test.js` (ou tests associés),
`e2e/lots/` (spec du lot).

Étapes :
1. Mesurer d'abord (Performance de Chrome sur le poste : durée d'un cran de
   zoom avec la couche Vent allumée), noter le chiffre avant/après dans la
   PR.
2. Alléger le rendu : décimation par niveau de zoom (nombre de roses à
   l'écran plafonné, comme la maille le prévoit), réutilisation des marqueurs
   inchangés entre deux passes (mise à jour au lieu de destruction), et
   duplication des copies du monde seulement pour celles visibles.
3. Pas de reconstruction pendant l'animation de zoom : une seule passe au
   `zoomend`, débouncée ; l'annulation en vol reste (AbortController).
4. Rendu identique à l'œil (mêmes roses, mêmes popups, même bandeau) — seul
   le coût change ; le repli RE6 (couche globale) n'est pas touché.
5. Tests : deux passes successives sur la même vue ne recréent pas les
   marqueurs ; le nombre de features rendues à zoom monde reste sous un
   plafond ; fumée e2e du lot (zoom avec pastille Vent, temps borné).

Recette (visuelle) :
- Suivre, pastille **Vent** allumée : zoom molette avant/arrière sur
  l'Atlantique → **fluide**, l'application ne se fige plus, les roses se
  redessinent sans à-coup.
- Les roses, leurs popups et le bandeau de source sont identiques à avant.
- Pastille éteinte : rien ne change.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Priorité porteur | Touche surtout |
|---|---|---|---|---|
| 1 | RF1 | S | 1 (console) | voyage_api.py, plan_advisor.py, usePlanReview.js (advice sans 400) |
| 2 | RF9 | M | 1 (console — principe D5') | official_store (nouveau), voyage_api.py, main.py, pearl_store.py (le voyage officiel précalculé et stocké, travail de fond, l'API sert) |
| 3 | RF2 | M | 1 (console) | voyage_api.py, polar_api.py, useVirtualVessel.js (robustesse : erreurs propres, polaires gardées, repli client — lit le stock RF9) — après RF9 |
| 4 | RF3 | S | 2 (console film) | App.jsx, useIciDossier.js, EscaleLegend.jsx (le film lit le stock, hooks gelés) — après RF9 |
| 5 | RF4 | S | 3 (discours) | film_script.py, useReplay.js, SimulationFilmBar.jsx (avion dit, fin affichée) — après RF2 |
| 6 | RF5 | M | 4 (cinématique) | filmCamera.js, MapSceneController.js, useReplay.js (caméra fluide, fond visible) |
| 7 | RF6 | S | après | App.jsx, MapSceneController.js (accueil Suivre D1', Tracer monde D4') |
| 8 | RF7 | S | après | EscaleLegend.jsx, SimulationFilmBar.jsx, i18n (liste informative D2' ; pilules dans le cadre, « Récit : règles » retiré D3') |
| 9 | RF8 | M | après | useClimatologyLayer.js (roses : zoom fluide) |

Lancement : la boucle (`loop.py`) part seule au merge de la PR de ce
document, **empilée sur la pile #325 → #334** si elle n'est pas mergée (les
ancres ci-dessus ont été lues sur sa tête), depuis `main` sinon. À la main,
si besoin :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --check
caffeinate -i python3 infra/agents/run_lots.py --from RF1 --until RF8 --resume
```

(`--from RF1 --until RF8` couvre les **9** lots : RF9 est inséré entre RF1 et
RF2 dans l'ordre du fichier des prompts, que le lanceur suit.)

Fin de batch : le poste de recette s'ouvre seul (W0) ; recette par écran,
console ouverte (priorités 1 et 2 du porteur : zéro ligne rouge, du
chargement à la fin du film) ; merge des PR dans l'ordre de la pile.

# Plan — Corrections de la revue du 27 septembre (session 5) : lots RH1 → RH2

Version **1.0** — 27 septembre 2026. Le porteur a recetté dans Chrome la pile
#325 → #386 (27 PR : lots RE1 → RE7, RC10 → RC18, RF1 → RF11) : 26 items
cochés sur 91 (dont 22 par le bot), **8 KO du porteur — aucun nouveau**
(🆕 : 0) depuis la session précédente (2026-09-26T22:32:16Z), et une revue
globale **vide** (`REVUE_GLOBALE.md` sans contenu). Les 8 KO sont tous sur
la pile #325 → #334 et **déjà planifiés** par
`docs/PLAN_CORRECTIONS_2026-09-26-s4.md` (lots RF1 → RF10, codés — PR #345 →
#359) ; les KO du réviseur de nuit sur les PR suivantes sont couverts par les
lots correctifs de la file (RC12 → RC18, codés — PR #361 → #386). Cette
session est donc un **passage de contrôle** : ce plan ne replanifie rien — il
rattache chaque constat à son lot en file (§ 1, § 3) et n'ouvre que **deux
petits lots** pour les deux seuls défauts que rien ne couvre, causes lues
dans le code de `main` : le chat du journal n'a **aucun repli par les faits**
quand la cascade de modèles échoue (**RH1**), et le client **avorte ses
propres requêtes en plein vol**, ce qui peint des `net::ERR_ABORTED` rouges
en console (**RH2**).

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4). La recette est
  visuelle : ouvre, clique, regarde — jamais de `curl`, de `data-testid` ni
  de coordonnées dans une étape de recette.
- **Rien de superflu à l'écran** (REGLES § 1) : aucun des deux lots de ce
  plan n'ajoute ni ne retire une surface visible — RH1 remplace un message
  d'échec par une vraie réponse, RH2 est invisible hors console.
- **Aucun chiffre produit par un LLM** : le repli du chat (RH1) répond par un
  **gabarit** dont chaque nombre vient des faits du contexte
  (`filter_numbers` reste juge) ; champ inconnu = silence.
- **Les quatre priorités du 26 sept. restent l'ordre** (console partout,
  console pendant le film, discours du film, cinématique) : les lots RF et
  RC en file les servent ; RH1 et RH2 relèvent tous deux de la priorité 1
  (console propre, chat qui répond).
- **Ne pas replanifier** : 0 KO 🆕 — tout KO de cette revue a déjà son lot
  (§ 1) ou sa décision (§ 3). Les lots RH ne doublonnent aucun lot en file.
- Trois parcours fixes : Suivre à Nouméa, Simulation La Rochelle → Ajaccio,
  Tracer Brisbane → SF ; plus Revoir l'expédition en Suivre, console ouverte.

## 1. Revue par PR (cases du porteur, verdict du réviseur de nuit)

26 / 91 cochés (porteur 4, bot 22), 8 KO porteur (tous anciens), 38 KO bot.
La colonne « Suite » rattache chaque constat au lot en file qui le couvre ;
**RH1** et **RH2** sont les seuls lots nouveaux de ce plan.

| PR | Lot | Cochés | KO porteur (ancien) | Bot (verdict de nuit) | Suite |
|---|---|---|---|---|---|
| #325 | RE1 | 3/3 | accueil voulu en **Suivre** + Cinéma + monde | caméra pas recadrée au clic Suivre (cause : `POST /voyage` 500) ; console 500, advice 400 | accueil → **RF7** (#353) + **RC14** (#381) ; serveur → **RF2/RF3** (#346, #348) + **RC18** (#386) ; advice → **RF1** (#345, 4/4 ✅) |
| #326 | RE2 | 3/3 | liste des escales informative **quel que soit le mode** | rien | → **RF8** (#354, D2') |
| #327 | RE3 | 1/5 | journal vide ; pilules 2:30/3:00 hors cadre ; « Récit : règles » à supprimer ; encadré date au format ; Tracer refuse de dézoomer | journal vide (5xx), console | journal → **RF2/RF3** + **RC17** (#385) ; barre → **RF8** (D3') ; Tracer → **RF7** + **RC14** ; console → **RF1/RF3** |
| #328 | RE4 | 3/3 | — | console (429/500, advice 400) | → **RF1/RF3** + **RC18** |
| #329 | RE5 | 0/2 | « idem pré-revue » (fourchette absente) | `eta` en `members: 0`, connexions fermées | fourchette servie du stock → **RF2** + **RC9** (en file) ; re-recette sur poste sain (§ 3) |
| #330 | RE6 | 2/2 | zoom très lent, l'appli se fige avec les roses | non vérifiable (tuiles OK sur la tête testée) | → **RF9** (#357) |
| #331 | RE7 | 0/4 | KO général : journal vide, récit sans événement | avion pas dit ; console film en rafale | journal/récit → **RF2/RF3** + **RC17** ; avion → **RF5** (#351) + **RC13** (#363) + **RC16** (#384) ; console film → **RF4** (#350) |
| #333 | RC10 | 1/2 | revue non faite (Journal vide) | sous-titre de fin absent après l'arrêt ; console film > 1 000 | fin du film → **RF5** + **RC16** ; console → **RF4** ; re-recette |
| #334 | RC11 | 0/2 | revue non faite (Journal vide) | advice 400 (×5), fourchette absente, **404 tuiles climato**, **chat sans réponse** | advice → **RF1** ; fourchette → **RC9** ; tuiles → § 3 ; chat → **RH1** |
| #345 | RF1 | 4/4 🤖 | — | aucune ligne rouge advice sur les 3 modes ✅ | rien |
| #346 | RF2 | 5/6 | — | 13 217 nm affichés vs « 13 214 » attendus ; `POST /voyage` 524 | milles → § 3 (pas un défaut) ; 524 → **RC18** |
| #348 | RF3 | 3/4 | — | 1 430 erreurs rouges pendant le recalcul du stock (524, connexions fermées) ; polaires ✅ | → **RC18** (remplissage en processus séparé) ; journal → **RC17** |
| #350 | RF4 | 1/2 🤖 | — | film sans rafale `/ici` ✅ ; sac live après Stop pas vu | re-recette (rien d'orphelin) |
| #351 | RF5 | 0/3 | — | stock `/film` sans « avion » (9 chapitres, stock RF2 non recalculé) | script servi → **RC13** ; recalcul du stock → **RC17/RC18** ; lisibilité → **RC16** |
| #352 | RF6 | 0/4 | — | pas vu | re-recette |
| #353 | RF7 | 0/4 | — | Tracer : zoom 3.0 > 2.25 (Amériques, pas le monde) | → **RC14** (#381) |
| #354 | RF8 | 0/6 | — | pas vu | re-recette |
| #357 | RF9 | 0/3 | — | console (serveur du poste) | serveur → **RC18** ; re-recette |
| #359 | RF10 | 0/4 | — | pas vu (relance du poste hors portée du bot) | re-recette |
| #361 | RC12 | 0/4 | — | 503 `/voyage/…/at` en Simulation | → **RC15** (#383) |
| #363 | RC13 | 0/3 | — | sous-titre avion **tronqué par le CSS** (`truncate`) — le texte complet est dans `GET /film` | → **RC16** (#384) |
| #381 | RC14 | 0/5 | — | `net::ERR_ABORTED` sur `/ici/warm/status` et `/voyage/official/eta` | → **RH2** |
| #382 | RF11 | 0/3 | — | pas vu | re-recette |
| #383 | RC15 | 0/2 | — | pas vu | re-recette |
| #384 | RC16 | 0/1 | — | fourchette absente (`members: 0`, « attendu RC9 ») ; **404 tuiles climato vent** ; **chat « Quel vent au bateau ? » sans réponse** | fourchette → **RC9** ; tuiles → § 3 ; chat → **RH1** |
| #385 | RC17 | 0/4 | — | pas vu (lot de la nuit, sans captures) | re-recette |
| #386 | RC18 | 0/3 | — | pas vu (lot de la nuit, sans captures) | re-recette |

## 2. Revue générale

`REVUE_GLOBALE.md` est **vide** : le porteur n'a rien ajouté hors cases à
cette session. Les quatre priorités imposées le 26 sept. (console partout,
console film, discours, cinématique) restent la doctrine ; la pile en file
(RF1 → RF10, RC12 → RC18) les sert. Les deux seuls constats de la nuit
qu'aucun lot ne couvre sont des restes de la priorité 1 :

1. **Le chat du journal ne répond pas** (« Le journal n'a pas pu répondre
   (aucun modèle n'a répondu) », #334 et #384, deux cycles de suite). Le plan
   s4 § 3 l'avait classé « environnement (clés) » avec la consigne « si
   l'échec persiste, ouvrir un lot au prochain cycle » : l'échec persiste,
   et la cause est **dans le code** — l'appel à la cascade ne passe pas le
   repli par les faits qu'elle sait pourtant servir (§ 4, RH1).
2. **Des `net::ERR_ABORTED` rouges** en console au chargement et en
   Simulation (#381) : le client coupe ses propres requêtes en plein vol —
   pas une panne serveur, un motif d'écriture des effets React (§ 4, RH2).

## 3. Ce qui est reporté ou fondu, et pourquoi

- **Les 8 KO du porteur (#325 → #334)** : tous anciens, tous déjà transformés
  en lots par le plan s4 — accueil Suivre (RF7 + RC14), liste informative
  (RF8), journal vide (RF2/RF3 + RC17/RC18), barre film (RF8), Tracer
  (RF7 + RC14), fourchette (RF2 + RC9), roses (RF9), récit/avion
  (RF5 + RC13/RC16/RC17). Ces lots sont **codés, en recette** : rien à
  replanifier, tout à recetter sur un poste sain.
- **404 `/bi/climatology/wind/tiles/…` (#334, #384)** : la décision des plans
  s2 § 3 et s4 § 3 tient — et le code de `main` la confirme : la route existe
  et répond un FeatureCollection **vide en 200** hors zone ou sans donnée
  (`backend/app/routers/climatology.py:222-247`) ; elle ne répond 404 que
  pour un `kind` inconnu (`:235`). Des 404 en série = le backend BI interrogé
  par le poste n'a pas cette route (déploiement en retard sur `main`). Le
  repli client est codé (RE6, #330). À re-vérifier à la prochaine recette ;
  si les 404 persistent alors que le VPS a bien déployé `main`, c'est un
  ticket infra — pas un lot.
- **Fourchette d'arrivée absente (`members: 0` — #329, #334, #384)** : l'ETA
  et les fourchettes font partie du **stock RF2** (servies telles quelles) et
  le réviseur de nuit note « attendu RC9 » — le lot est en file. Re-recetter
  après le remplissage du stock (RC17/RC18) ; si la raison affichée est un
  quota de l'API ensemble, décision du porteur (clé, autre source).
- **13 217 nm au lieu de « 13 214 nm » (#346)** : pas un défaut — la valeur
  attendue de la case était un instantané au moment de l'écriture de la PR ;
  le bateau avance et la ligne LIVE suit. Le porteur a d'ailleurs coché
  l'item. Aucune suite.
- **524 / `ERR_CONNECTION_CLOSED` / `ERR_HTTP2_PROTOCOL_ERROR` (#346, #348,
  #357)** : le remplissage du stock écrase encore l'API sur le poste — c'est
  exactement le périmètre de **RC18** (#386 : remplissage dans un processus
  séparé à priorité basse). S'ils survivent à RC18 en prod : ticket infra
  (décision du 23, conservée).
- **Stock sans avion (#351), sous-titre tronqué (#363), fin du film
  (#333)** : couverts par **RC13** (GET /film sert le script RF5), **RC16**
  (l'avion se lit à l'écran), **RC17** (le stock retrouve ses événements),
  **RF5** (la fin reste affichée) — codés, en recette.
- **503 `/voyage/…/at` (#361)** : couvert par **RC15** (#383), codé.
- **Cases décochées sans KO (18 PR « pas vu »)** : revue à la volée non
  terminée — pas des refus ; elles restent à cocher au prochain passage sur
  un poste au stock rempli. Aucune n'est orpheline d'un plan.
- **Chat du journal** : la décision « environnement » du plan s4 § 3 est
  **remplacée** — la cause est lue dans le code (§ 4, RH1) ; la vérification
  des clés sur le poste reste utile mais ne suffit plus.
- **Fondu dans un lot à venir** : un seul complément — **R8c** (encadré
  unique du panneau gauche) reçoit le garde-fou de RH2 (« Constat de la revue
  du 27 sept. » : aucun effet du panneau n'avorte une requête qu'il vient de
  lancer — pas de `net::ERR_ABORTED` réintroduit au rebranchement). Aucun
  autre lot à venir (R8a/b, R9, R10, N1-4, D0, H1, G0-G7) ne couvre un
  constat de cette session ; les parités globe des sessions précédentes
  restent fondues dans G1, G4, G5 et G6.

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour App.jsx et MapSceneController.js). « Recette » = ce que le
porteur voit dans Chrome. Ancres `fichier:ligne` lues sur `main`
(`ac96569`). Les deux lots sont indépendants (ils partent de `main`, aucun
fichier commun avec la pile en file).

### RH1 — Le chat du journal répond depuis les faits quand aucun modèle ne répond (S)

Cause racine : `answer_question` appelle la cascade **sans repli** —
`cascade_text(system, user, http, tier=chat_tier(question))`
(`server/logbook_chat.py:429`) ; or `cascade_text` prévoit exactement ce
repli : « A string fallback — even empty — yields `source=rules` after every
provider failed » et, sans lui, garde l'ancien contrat « raise when no
backend » (`server/story_cascade.py:742-758`). Toute panne de cascade (clés
absentes ou épuisées, quota, réseau) remonte donc en
`{"status": "failed"}` (`logbook_chat.py:430-431`) et le client affiche
« Le journal n'a pas pu répondre (aucun modèle n'a répondu) »
(`src/i18n/fr.js:222`, rendu `src/components/LogbookChat.jsx:61-62`) — alors
que le contexte contient déjà les faits chiffrés : vent au bateau
`windKnots` / `dirFromDeg` (`logbook_chat.py:140-148`), vitesse
(`:152-180`), prochaine escale (`:149`). Un repli « rules » existe d'ailleurs
déjà dans la même fonction pour l'autre branche (texte vidé par
`filter_numbers`, `:435-438`). KO bot #334 et #384, persistant sur deux
cycles — la condition du plan s4 § 3 (« si l'échec persiste, ouvrir un lot au
prochain cycle ») est remplie.

Fichiers : `server/logbook_chat.py`, `server/story_cascade.py` (lecture),
`server/tests/test_logbook_chat.py`, `src/components/LogbookChat.jsx` PAR
EXTRAIT (`rg -n "failed|chat-source"`), `src/i18n/fr.js`, `src/i18n/en.js`.

Étapes :
1. Un gabarit de réponse **par les faits** (FR et EN), construit depuis le
   contexte déjà assemblé par `build_context` : vent au bateau
   (`official.wind.windKnots`, `dirFromDeg`) quand la question parle de
   vent/mer, vitesse (`boat.speedKnots`, « à quai » si 0), prochaine escale
   (`nextStop`) — **chaque nombre vient du contexte**, aucun n'est rédigé ;
   `filter_numbers` reste appliqué. Sans fait pertinent : la phrase existante
   « Le journal n'a pas cette information dans ses données. »
2. `answer_question` passe ce gabarit en `fallback` à `cascade_text` : quand
   tous les fournisseurs échouent, la réponse part quand même —
   `status: "ready"`, `source: "rules"`. Le statut `failed` ne subsiste que
   si même le gabarit est impossible (contexte illisible).
3. Côté client, rien de nouveau à l'écran : la réponse « rules » s'affiche
   comme les autres (la source est déjà rendue sous le texte,
   `chat-source`) ; le message d'échec reste pour le seul vrai `failed`.
4. Tests : cascade mockée en échec + contexte avec vent → réponse contenant
   **le chiffre exact du contexte**, `source: "rules"`, jamais `failed` ;
   cascade en échec + question hors données → phrase « pas cette
   information » ; cascade qui répond → comportement inchangé.

Recette (visuelle) :
- Suivre (ligne d'état LIVE), panneau gauche, poser « Quel vent au bateau ? »
  → **tu dois voir** une phrase avec le vent en nœuds (kn) et sa direction —
  plus jamais « Le journal n'a pas pu répondre (aucun modèle n'a répondu) ».
- Poser une question dont le journal n'a pas la donnée (« Quel est le prix du
  gasoil ? ») → **tu dois voir** « Le journal n'a pas cette information dans
  ses données. » — jamais un chiffre inventé.
- Simulation, même question vent → une phrase, jamais le message d'échec.

### RH2 — Console : plus de `net::ERR_ABORTED` au parcours nominal (S)

Cause racine : deux effets client **coupent leurs propres requêtes en plein
vol**, et Chrome peint chaque abandon en rouge `net::ERR_ABORTED` (KO bot
#381 : `/ici/warm/status` en Simulation, `/voyage/official/eta?stop=…` au
chargement) :
1. `src/components/Sidebar.jsx:307-322` — l'effet qui lit la source du récit
   dépend de `[showIciBriefing, briefing]` : chaque nouveau texte de
   briefing (il change au fil du voyage) rejoue l'effet, dont le nettoyage
   `ctrl.abort()` (`:320`) coupe le `GET /ici/warm/status` en vol — alors
   que le drapeau `cancelled` (`:309`, `:319`) suffit déjà à ignorer la
   réponse.
2. `src/hooks/usePlanReview.js:351-372` (`useOfficialEta`) —
   `pollOfficialEta` boucle avec relances espacées ; le nettoyage
   `controller.abort()` (`:368`) coupe le `GET /voyage/official/eta` en vol
   à chaque changement de deps (`enabled`, `stopName` — au chargement, le
   nom de la prochaine escale arrive puis évolue) et au démontage (bascule
   de mode ; second usage `src/components/EscaleLegend.jsx:76`). L'attente
   entre deux sondes est déjà interruptible (`sleep(…, signal)`, `:345`) :
   c'est **elle** qu'il faut couper, pas la requête partie.

Fichiers : `src/components/Sidebar.jsx` PAR EXTRAIT
(`rg -n "warm/status"`), `src/hooks/usePlanReview.js`,
`src/components/EscaleLegend.jsx` PAR EXTRAIT (`rg -n "useOfficialEta"`),
`src/hooks/usePlanReview.test.js`.

Étapes :
1. `Sidebar` : la lecture de `warm/status` ne se rejoue que quand
   `showIciBriefing` passe à vrai (pas à chaque texte de briefing) ; une
   requête déjà partie va au bout et sa réponse est ignorée par le drapeau
   `cancelled` — plus aucun `abort()` d'une requête en vol.
2. `useOfficialEta` : à l'arrêt (démontage, changement d'escale), la boucle
   s'arrête **entre** deux sondes — l'attente interruptible est coupée, la
   requête en vol se termine et sa réponse est ignorée (`alive`) ; pas de
   relance quand `stopName` n'a pas changé. Même motif appliqué à l'effet
   `plan-review` du même fichier (`:396-422`) s'il peint aussi des abandons.
3. Aucun changement d'écran : mêmes données, même fraîcheur, mêmes
   fourchettes affichées ; seul le bruit console disparaît.
4. Tests : démontage pendant une requête en vol → aucun `abort()` du fetch,
   aucune mise à jour d'état après démontage ; changement de briefing → pas
   de nouvelle requête `warm/status` ; changement de `stopName` → une seule
   boucle active.

Recette (visuelle) :
- Ouvre l'application, console ouverte, enchaîne Suivre → Simulation →
  Tracer ma route → Suivre, laisse 2 minutes → **tu ne dois voir** aucune
  ligne rouge `net::ERR_ABORTED` (ni `/ici/warm/status`, ni
  `/voyage/official/eta`).
- Panneau droit : la fourchette « arrivée entre le … et le … » de la
  prochaine escale s'affiche comme avant (quand le stock la sert).
- Rien d'autre ne change à l'écran.

## 5. Ordre, pile, lancement

| # | Lot | Taille | Priorité porteur | Touche surtout |
|---|---|---|---|---|
| 1 | RH1 | S | 1 (le chat répond) | logbook_chat.py (repli par les faits, source « rules ») |
| 2 | RH2 | S | 1 (console propre) | Sidebar.jsx, usePlanReview.js (plus d'abort en vol) |

Les deux lots partent de `main`, sans dépendance entre eux ni avec la pile
en file (aucun fichier commun avec RF/RC en cours de recette) — la chaîne
nocturne peut les empiler dans cet ordre. Vérification :

```bash
cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only
python3 infra/agents/run_lots.py --dry-run --from RH1 --until RH2
caffeinate -i python3 infra/agents/run_lots.py --from RH1 --until RH2 --resume
```

Le gros de la session reste la **re-recette** : merger la pile dans l'ordre,
laisser RC18 remplir le stock, puis recocher les 18 PR « pas vu » sur un
poste sain (§ 3).

# Plan — Corrections de la revue du 16 oct. 2026 (session 7)

Version **1.0** — 16 octobre 2026, matin. Session W7 n° 7 (`since`
2026-10-14T23:34:12Z). Le porteur a recetté dans Chrome la pile Batch 2
(HC1 → RC51, 38 PR) : **85 / 127 cases cochées**, **0 commentaire KO** de
sa main, **0 KO nouveau** (🆕 / `new: true`). Revue globale : vide. Aucun
plan `PLAN_CORRECTIONS_2026-10-16*.md` n’est encore sur `main` — les lots
correctifs de la nuit (RC34 → RC51, LY1/LY2, CT1, RC46) sont **déjà
codés et mergés** ; on ne les replanifie pas.

Prérequis : `main` à jour (tête #509). Ce document et les prompts RJ
partent de `main`. Les agents ne touchent qu’aux fichiers listés dans
chaque lot.

## 0. Rappels de la revue (à lire avant tout lot)

- Le porteur regarde Chrome, il ne lance rien (REGLES § 4).
- **Rien de superflu à l’écran** (REGLES § 1) : aucun texte d’aide ajouté ;
  un état inactif est grisé.
- **`main` est le plancher** : ne pas retirer une surface visible (onglets
  Suivre, Calques, Exporter, Polaires, barre film, pilules Berry / ma route).
- Trois parcours : Suivre à Nouméa (Berry), Tracer La Rochelle → Ajaccio,
  Tracer votre propre route Brisbane → SF. Plus **Suivre × ma route**
  (DM8C) et **Revoir l’expédition**.
- Les 177 KO du bot et les parcours de référence répètent surtout des
  défauts **déjà traités** par RC34–RC51 ou des **stocks pas encore
  ressemés**. Voir § 3.
- Images agent (#463, #465) : aucun KO du porteur ne les cite — non
  ouvertes (budget).
- Réviseur de nuit, tranche DM8C / RC27 / RG11A / RG11B
  (20261015-1129) : **aucun lot mis en file** ; revue 0958 tuée à la
  pause ; **aucun commentaire fichier:ligne** posté sur GitHub. Verdicts
  ci-dessous = pré-revue bot + code lu sur `main` (`5c25fb51`).

## 1. Revue par PR (OK / KO du porteur, nuit)

### Déjà bons (porteur ou bot, 0 case vide utile)

| PR | Lot | Verdict |
|---|---|---|
| #461 | DM4 | 3/3. Accueil centré, monde dézoomé. |
| #462 | DM5 | 5/5 porteur. Suivre sur ma route. 502 climo = quota atlas (§ 3). |
| #463 | DM6 | 6/6 bot. Brouillon conservé. Fermée. Parcours bot hors sujet. |
| #464 | DM7 | 5/5. Lecture depuis aujourd’hui, Date de départ en Suivre seulement. |
| #465 | DM9 | 3/3 bot. Onglets Tracer / Suivre conformes à la décision du 14 oct. Fermée. |
| #466 | UI1 | 4/4. Crédits collés à la barre. |
| #473 | DM8A | 3/3 porteur. Aucun changement visible (serveur). |
| #474 | DM8B | 3/3. Film de ma route, même forme. |
| #491 | DM3 | 5/5. Plus de « Simulation » à l’écran. 404 logo / clock = infra (§ 3). |
| #492 | RC34 | 4/4. « réel jusqu’au », couture turquoise — **recette HC1 enfin vue**. |
| #504 | RC47 | 1/1. Madère → phrase d’absence. |
| #505 | CT1 | 2/2. Contrat tête Suivre / Tracer. |
| #506 | RC48 | 2/2. Eaux LR→Ajaccio dans l’ordre + Pacifique. |
| #508 | RC50 | 1/1. Revue du plan : **Cayenne → Papeete**. |
| #509 | RC51 | 2/2 (porteur 1). Caméra Caraïbes. Parcours bot : déjà vus, § 3. |
| #494 | LY1 | 0 case. Chauffe AMP, aucun changement visible. |

### Recettés en partie — le reste est déjà repris par un lot mergé

| PR | Case vide | Déjà couvert par | Suite |
|---|---|---|---|
| #460 HC1 | « réel jusqu’au », turquoise, EN | **RC34** (#492, 4/4) | Rien. |
| #467 RC30 | eaux LR→Ajaccio, phrases coupées, Pacifique | **RC35, RC36, RC48** | Recette RC36 encore à faire. |
| #471 RC31 | « attend à Cayenne », second voilier, dates journal | **RC43, RC44** | Recette RC43 encore à faire. |
| #482 AM1A / #483 AM1B / #502 RC45 | AMP Bonifacio / film / Ici | **RC45, RC46** + stock AMP | Resemer le stock, re-recetter. |
| #486 RG19 | Madère ; Ultra | **RC47** (Madère OK) ; plafond Ultra | Rien à coder. |
| #493 RC35 | eaux LR→Ajaccio | **RC48** (2/2) | Rien. |
| #497 RC40 | un seul mouvement au flip | **RC49, RC51** | Rien. |
| #501 RC44 | jambe mer Cayenne → Papeete | **RC50** (1/1) | Rien. |
| #507 RC49 | glisse Caraïbes | **RC51** (porteur OK) | Rien. |

### Pas vus (revue à la volée) — lots mergés, à recetter, pas à recoder

- **#472 RC32** (0/4) : toponymes Saint-Martin / Sint Maarten. 0 KO.
- **#489 RG20** (0/2) : specs CI — le porteur ne lance pas les tranches.
- **#495 RC36** (0/3) : barre d’étape jusqu’à la fin de phrase.
- **#498 RC41** (2 vides) : rythme / mer formée — télémétrie déjà stable ;
  sous-titre figé traité par **RC43** (épisode SPM). Phrase mer = stock
  (plus de « ≥ », parfois aucune mer sur LR→Ajaccio).
- **#499 RC43** (0/2) : sous-titre Saint-Pierre / reprise Papeete.

### Tranche de nuit DM8C / RC27 / RG11 — ce qui reste vraiment

#### #476 DM8C — Journal de ma route trop court — **RJ1**

- OK : pilule ma route, Revoir (ou « en préparation »), Revue du plan,
  pilule Berry intacte.
- Case vide (bot KO, 0 mot du porteur) : Journal = **2 lignes des
  premières heures** (« 15 oct. 08:00 · vents d’ouest », « 11:00 · Mer »)
  alors que la barre dit déjà « eaux espagnoles » / « Les Sables-d’Olonne ».
- Nuit : pas de verdict fichier:ligne (revue tuée).
- Cause lue sur `main` : § 4 RJ1. Aucun lot à venir ne le couvre (R9b
  réécrirait le hook à l’envers : localStorage pour « ma route »).

#### #477 RC27 — gabarits 2:30 / intégral « inversés » — **stock, pas un lot**

- OK : durée ≈ 2:30, AMP + projet encore là.
- Bot : 2:30 montre le gabarit long RG6, l’intégral le compact.
- Code `main` : `_film_compact_template` (`film_script.py:2495-2498`) =
  `0 < seconds ≤ 150` ; `seconds=0` = intégral. Tests
  `test_rc27_compact_150_vs_full_integral` et
  `test_rc27_rich_150_keeps_amp_project_integral_gabarit_intact` figent
  l’inverse de ce que le bot a lu. Le blob servi au poste était **antérieur
  au bumper de révision** (même classe que le stock pré-RC48 sur #493).
- Suite : ressemer le film (`FILM_SCRIPT_REV`), re-recetter. Pas de RJ.

#### #478 RG11A / #480 RG11B — Rédigé

- OK : pilules Brut / Rédigé, hover honnête, pas d’appel Nebius depuis
  le navigateur, chrome inchangé.
- Case vide #480 : Rédigé cliquable — **non vérifiable** (plafond write,
  `hasWritten: false`). Pas un défaut de code.
- 502 `/bi/climatology` et 400 `/escale?lon=228` : § 3.

#### #484 RG18 — fiche Ici ≠ phrase du film — **RJ2**

- OK : Brut = phrases de règles ; pastille « n récits » seulement après
  Rédigé.
- Case vide : la fiche Ici dit « Le bateau navigue dans Zone économique
  exclusive de Nouvelle-Calédonie… » alors que `filmPhrases.zee-enter` =
  « Le 15 octobre, les eaux de Nouvelle-Calédonie. » (même constat sur
  le parcours #509).
- RG18 a branché `pickFilmPhrase` sur les **événements**
  (`useIciDossier.js:441`) ; l’ouverture de la fiche passe encore par
  `zeeSentence` (`iciBriefing.js:191`), placée **avant**
  `eventSentence` dans `narrateIci` (`:838`). Aucun lot à venir ne
  change cette phrase.

## 2. Revue générale

Rien dans `REVUE_GLOBALE.md`. Vision d’ensemble tirée des cases et du
parcours de tête (#509), sans inventer de demande du porteur :

- La pile Batch 2 est **mergeable** : les modes Suivre / Tracer, la
  position (HC1+RC34), les eaux (RC48), Cayenne → Papeete (RC50), la
  caméra Caraïbes (RC51) sont vus.
- Deux restes **visibles** que ni RC34–RC51 ni le programme R8… / N… / G…
  ne corrigent : Journal de ma route (DM8C), phrase d’ouverture Ici (RG18).
- Le reste est stock, plafond LLM, quota atlas, ou recette pas encore
  rejouée.

## 3. Ce qui est reporté et pourquoi

| Constat | Pourquoi pas de lot | Où ça vit |
|---|---|---|
| Cases vides sans KO (RC32, RC36, RC43, RG20, AM1B…) | Revue à la volée non finie — même règle que le plan s5 § 3 | À cocher au prochain passage, stock ressemé |
| Gabarits 2:30 / intégral inversés (#477) | Code + tests déjà justes ; blob poste périmé | Resemer `FILM_SCRIPT_REV` |
| AMP absentes Ici / film (#482, #483, #502) | RC45/RC46 mergés ; `amp: []` = cache mince / stock | Warm officiel + `amp-route.py` |
| Rédigé / Ultra au plafond | Politique `llm_budget`, pas un bug | Attendre J+1 ou relever le plafond poste |
| 502 `/bi/climatology/*` | Quota atlas, déjà noté s5 / RC34 | Infra / quota ; pas un lot simulateur |
| 400 `/escale?lon=228` | Clic mal placé, lon non wrap ; 1 fois, annulé | Pas de récidive recettée ; hors 8 lots |
| 404 `/logo-naviguide.png`, `/ici/layers/warm` | Infra / chemin de chauffe LY2 | Ticket infra si ça survit au déploiement |
| 524 `/recompute` | Isochrone sur route officielle = NV du parcours | R10c / R10d (programme) |
| Sous-titres restés en FR après langue EN | `useReplay` passe déjà `lang=` ; stock EN souvent absent | Resemer film `lang=en` |
| Export GeoJSON / KML sans téléchargement | **N2** (programme, déjà spec `n2-export`) | Fondu interdit : N2 n’est pas à relancer ici ; si ça casse encore après N2 rejoué, session suivante |
| « Croisière · 36 h » absent | Décision DM9 : Caractère / Anticipation séparés | Cases de parcours à mettre à jour, pas un lot |
| Cinéma ≠ plein écran | Contrat actuel : Cinéma = suivi caméra ; « Plein écran film » masque | Pas une régression demandée |
| Barre film 2 rangées, polaire sans diagramme, calques muets au zoom monde | Parcours répétés, aucun KO porteur, déjà dans RG15 / RF9 / parcours | Pas orphelins d’un plan ; pas de RJ |
| Phrase mer absente LR→Ajaccio | Stock ; interdit « ≥ » déjà tenu (RC41) | Resemer ; RG4 si ça manque encore |
| Journal officiel / ETA « — » sous Nouméa | RG17 / RE5 / stock `eta` | Resemer famille eta |

**Aucun complément fondu** dans R8a–R10d, N1–N4, G0–G7, D0, H1 : les
deux restes visuels **contrediraient** R9b (qui remettrait ma route sur
localStorage) et ne relèvent pas du périmètre R8c (branchement d’encadré,
pas le texte de `zeeSentence`).

## 4. Les lots correctifs

Convention : « Fichiers » = les seuls à ouvrir (`rg -n` + `Read`
offset/limit pour `App.jsx` / `MapSceneController.js`). « Recette » =
Chrome, par écran. Ancres lues sur `main` (`5c25fb51`). Deux lots **S**,
indépendants, chacun depuis `main` (fichiers disjoints).

### RJ1 — Suivre × ma route : le Journal montre ce que la route croise (S)

Cause racine (deux portes, même écran) :

1. `pollOfficialMoments` (`src/hooks/useMomentJournal.js:209-211`)
   **s’arrête dès la première liste non vide**. Or
   `moments_for_voyage` (`server/custom_story.py:339-350`,
   `MAX_CHUNK_S=12` `:41`) rend d’abord `status: "preparing"` avec
   seulement le premier morceau de perles. Le Journal se fige sur 2
   lignes.
2. En Suivre, `visibleJournalEntries` coupe à `until`
   (`useMomentJournal.js:299` + `App.jsx:626` `until: momentIso`).
   DM7 part **aujourd’hui** : l’horloge n’a que 2–3 h de passé → les
   eaux espagnoles, déjà dans le film / la barre, n’apparaissent jamais.

Fichiers : `src/hooks/useMomentJournal.js`,
`src/hooks/useMomentJournal.test.js`, `server/custom_story.py` PAR
EXTRAIT (`rg -n "status|preparing|done|_public"`),
`src/App.jsx` PAR EXTRAIT (`rg -n "until:|momentJournal|suivreCustom"`),
`src/components/IciMaintenant.jsx` PAR EXTRAIT (`JournalList`,
`formatJournalLine` — lecture), `e2e/lots/dm8-recit-ma-route.spec.js`
s’il existe.

Étapes :

1. `pollOfficialMoments` (ou un `pollCustomMoments`) continue tant que
   le corps dit `status !== "ready"` **et** `coverageNm < totalNm` ;
   même recul `nextEtaRetryMs` ; on affiche les lignes déjà là (pas
   d’écran vide). Officiel (`/voyage/official/moments` déjà ready) : un
   seul GET, comme aujourd’hui.
2. En Suivre × **ma route**, ne plus couper la liste à l’horloge live.
   Garder la coupe `until` pour Berry (journal = le passé du tour du
   monde). `nowMoment` (Maintenant) reste ≤ maintenant.
3. Tests : premier GET `{status:"preparing", moments:[2 lignes]}` puis
   ready avec eaux / arrivée → le hook finit sur la liste longue ;
   `visibleJournalEntries` + `suivreCustom` ignore `until` ; Berry +
   `until` inchangé. Spec dm8 : Journal contient au moins une mer / une
   arrivée, pas seulement l’heure de départ.
4. i18n : aucun libellé nouveau. Pas de texte d’aide.

Tests : `npm test` (useMomentJournal), `npx vite build`, spec
`e2e/lots/dm8-recit-ma-route.spec.js` (assertions puis captures).

Recette (visuelle) :

- **Tracer** : deux clics (près de La Rochelle, puis les Antilles),
  Terminer, **Suivre** (pilule de ta route allumée).
- **Changement visible** — onglet **Journal** : plus d’une poignée de
  lignes du matin ; tu lis au moins une mer ou une côte croisée (eaux
  françaises / espagnoles / Antilles) **ou** l’arrivée, alors que
  l’horloge n’est qu’à aujourd’hui. Ce n’est pas le journal Berry
  (Saint-Maur, Ajaccio…).
- **Suivre × Berry-Mappemonde** : le Journal va toujours du 15 mai à
  aujourd’hui, **aucun changement visible**.
- Captures : `docs/recette/lot-rj1/01-journal-ma-route.jpg`,
  `02-journal-berry.jpg`.

### RJ2 — Fiche Ici : l’ouverture dit la phrase du film (S)

Cause racine : `zeeSentence` (`src/engine/iciBriefing.js:189-191`)
écrit « Le bateau navigue dans ${where}. ${formalities} » et
`narrateIci` (`:838`) la place **en tête**, avant `eventSentence`.
RG18 a exposé `filmPhrases` sur le sac et `pickFilmPhrase`
(`:506-532`) ne s’applique qu’aux événements (`useIciDossier.js:441`).
D’où trois formes pour la même ZEE (Ici / film / règles), constat #484
et parcours #509.

Fichiers : `src/engine/iciBriefing.js` (`zeeSentence`, `poeSentence`,
`narrateIci`, `pickFilmPhrase`), `src/engine/iciBriefing.test.js`,
`src/hooks/useIciDossier.js` PAR EXTRAIT (lecture : le sac arrive déjà
avec `filmPhrases`), `src/i18n/fr.js` / `en.js` seulement si un
repli de formalités doit rester hors phrase (sinon ne pas y toucher).

Étapes :

1. `zeeSentence` : si le sac porte `filmPhrases["zee-enter"]` (ou
   `zee-ahead` / `zee-exit` selon l’état), **cette phrase** est
   l’ouverture ; plus de « Le bateau navigue dans Zone économique
   exclusive… ». Formalités : une seule fois, seulement si elles
   n’y sont pas déjà. Repli = phrase actuelle si le sac n’a pas de
   `filmPhrases`.
2. `poeSentence` : même règle avec `filmPhrases["poe-ahead"]` /
   `poe-ahead:<nom>` — évite la redite « Aucun port d’entrée officiel… »
   ×2 du parcours.
3. `narrateIci` : si l’ouverture est déjà la phrase film, ne pas
   recoller `eventSentence` du même type (une ZEE, une fois).
4. Tests : sac Nouvelle-Calédonie + `filmPhrases.zee-enter` =
   « Le 15 octobre, les eaux de Nouvelle-Calédonie. » → `narrateIci`
   **commence** par cette phrase, plus « Le bateau navigue dans Zone
   économique exclusive ». Sans `filmPhrases` : phrase actuelle
   (pas de régression hors sac RG18). FR et EN.

Tests : `npm test` (iciBriefing), `npx vite build`, spec existante
`e2e/lots/rg18-une-seule-plume.spec.js` + une capture Ici.

Recette (visuelle) :

- **Suivre** (Berry), onglet **Maintenant**, bateau en Nouvelle-Calédonie
  (position du jour) : la fiche **Ici** ouvre comme le **Récit** /
  le film (« les eaux de Nouvelle-Calédonie »), **plus** « Le bateau
  navigue dans Zone économique exclusive… ».
- **Brut** enfoncé : toujours des phrases de règles, pas une autre
  plume. **Rédigé** : inchangé (plafond éventuel = pas bloquant).
- **Tracer** : les mêmes Calques / Exporter ; aucun texte nouveau.
- Captures : `docs/recette/lot-rj2/01-ici-phrase-film.jpg`,
  `02-recit-meme-phrase.jpg`.

## 5. Ordre et pile

| # | Lot | Branche depuis | PR vers | Pourquoi cet ordre |
|---|---|---|---|---|
| 1 | RJ1 | `main` | `main` | Journal de ma route (fichiers hook / custom_story) |
| 2 | RJ2 | `main` | `main` | Phrase Ici (fichiers iciBriefing) — **parallèle**, aucun fichier commun |

Pas de pile. Lancement :

```bash
python3 infra/agents/run_lots.py --from RJ1 --until RJ2 --stack none
```

Après merge : ressemer le film officiel (FR + EN, 2:30 et intégral) et
la famille AMP / eta sur le poste avant la prochaine recette à la volée.

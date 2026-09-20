# Plan en lots — NAVIGUIDE simulator (suite du plan général)

Version **1.0** — 19 septembre 2026. Complète le
[plan général](PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md) (v2.0) : ce
document découpe **ce qui reste** en lots **recettables** (tests + recette
visuelle) qu’un agent Cursor peut prendre un par un — y compris un worker
Cloud (`cursor-grok-4.6-xhigh-fast`, `composer-2.5`) sans le contexte de la
conversation.

## 0. Ce que tout agent doit savoir avant de toucher au code

- **Atelier** : `naviguide-simulator/` (client Vite + React dans `src/`,
  serveur FastAPI dans `server/`). Prod : `simulator.naviguide.fr` (VPS OVH,
  déploiement automatique à chaque merge sur `main`). Rien d’autre du dépôt
  n’est concerné par ces lots.
- **Lancer en local** (Mac) : `cd naviguide-simulator && bash dev-mac.sh`
  (API `:8010` + Vite `:5174`). Tests : `npm test` (node --test),
  `.venv/bin/python -m pytest -q` ; build : `npx vite build`. La CI de la PR
  rejoue les trois.
- **Règles qui ne se discutent pas**
  1. `main` est le **plancher de l’UI** : on ajoute, on ne retire pas une
     surface visible sans demande explicite (`.cursor/rules/anti-regression-visuelle-simulateur.mdc`).
  2. **Un chiffre ne passe jamais par un LLM.** Le LLM rédige ce qui est
     collecté ; `kind` honnête (`observation ≠ forecast ≠ climatology`),
     `null + reason` plutôt qu’une valeur inventée.
  3. **Pas de Tavily, Nemotron, LangSmith** ; Nebius (60 $) réservé, à ne
     brancher qu’avec un cache (lot R2).
  4. **Recette = tests + captures fixes**, jamais de vidéo
     (`.cursor/rules/pas-de-verification-video.mdc`).
  5. Ne jamais lancer `infra/vps/sync-from-atlas.sh`.
  6. Une PR par lot, titre conventionnel (`feat(simulator): …`), description
     = objectif, ce qui change, tests, recette faite.
- **Vocabulaire** : *sac `ici()`* = tout ce qu’on sait à 30 nm du bateau
  (`GET /ici`) ; *perle* = sac **thin** (ZEE, ports d’entrée, AMP, ports)
  échantillonné tous les 12 nm le long de la route ; *Suivre* = le bateau
  officiel maintenant (1 s = 1 s) ; *Simulation* = le film ; *carte du
  moment* = NOW (sécurité / décision) + FREE (« pendant ce temps ») ;
  *journal* = mémoire serveur du voyage officiel.

## 1. État au 19 septembre 2026 (soir)

| Fait | Où |
|---|---|
| Sécurité P0 (clé admin partagée, débit, CORS), journal serveur v1, « Écouter » | #185, #186 |
| Carte du moment NOW / FREE, récit de la traversée, correctifs Suivre / crédits Leaflet / fiche Gold | #187 |
| Événements tout le long du film (sac jamais avorté, sac périmé écarté, saut = mémoire remise), **perles pré-générées** (`ici_warm.py`, cache 7 j sur disque, `GET /ici/pearls`), voies NOW / FREE revues, cartes d’escale, récits sobres, caméra, reprise de la Simulation, Stop auto, **sidebars réorganisées**, récit chronologique, journal compact | #188 |
| Journal **v2 partiel** : ZEE entrées / quittées et AMP approchées lues sur les perles, datées par l’horloge (hystérésis 2 perles) ; le récit les raconte par jambe ; `summary.events` = tout le voyage hors positions | PR de cette passe |
| **Vitesse de planning = polaire × vent du moment** (GRIB au bateau en Suivre, climatologie en Simulation), plancher 3 kn, source affichée ; l’anticipation suit | PR de cette passe |

**Exploitation du chauffage des perles** (question du porteur) :
- Le chauffeur tourne **dans le processus serveur** : sur ton Mac quand
  l’API locale tourne, sur le **VPS** en prod. Tu peux fermer ton Mac ou te
  déconnecter : les perles ratées sont comptées en `errors` et reprises au
  prochain démarrage ; rien ne casse. La prod se chauffe toute seule après
  le déploiement (`curl https://simulator.naviguide.fr/ici/warm/status`).
- Il sert surtout à la **Simulation** (le film va 15 à 175 nm/s, seul un
  sac déjà collecté peut suivre). En **Suivre**, le bateau va à sa vraie
  vitesse et le sac complet suffit ; les perles n’y font qu’accélérer
  l’anticipation (ZEE / port d’entrée devant). Une **route dessinée**
  n’en profite pas (échantillonnage propre, à la volée).

## 2. Les lots

Taille : S ≤ ½ jour d’agent, M ≤ 2 jours, L > 2 jours. Chaque lot est
indépendant sauf mention. Ordre conseillé : A → B → C → D, puis au choix.

### Lot A — Journal v2 complet et récit fidèle (M) — *dépend de #188 + cette passe*

**Objectif.** Le journal serveur sait tout ce qui s’est passé sur chaque
jambe, sans client : ports d’entrée franchis, événements météo au bateau
(coup de vent, mer forte), et le récit les raconte.

**Fichiers.** `server/ici_warm.py` (`route_events_from_pearls`),
`server/voyage_journal.py` (`record_route_events`, nouveaux `kind`),
`server/voyage_api.py` (rien ou `GET /voyage/official/journal?kinds=`),
`src/engine/expeditionStory.js`, `src/engine/journalFormat.js`, i18n.

**Étapes.**
1. Perles → `poe` : quand la liste `poe` d’une perle contient un port à
   ≤ 15 nm, entrée `kind: "poe"` (une fois par port, `basis: "pearl"`).
2. GRIB → `kind: "wx"` : à chaque cycle GRIB déjà journalisé (`kind: "grib"`),
   si `windKnots ≥ galeKt` du profil Croisière (34) ou `hs ≥ 3,5 m`, une
   entrée `wx` (« coup de vent 36 kn », « mer 3,8 m ») — dérivée, jamais
   inventée : pas de GRIB, pas de `wx`.
3. Récit : une phrase par jambe pour `poe` (« ports d’entrée passés : … »)
   et `wx` (« coup de vent le 3 juin, 36 kn ») ; `journalFormat` met en mots
   les deux kinds (icônes 🛃 ⚓ 🌬).
4. `GET /voyage/official/journal?kinds=zee,amp,poe,wx` (facultatif).

**Tests.** `server/tests/test_voyage_journal.py` (poe une fois, wx seulement
si seuil, idempotence), `src/engine/expeditionStory.test.js` (phrases),
`journalFormat.test.js`.

**Recette visuelle.** Suivre → panneau gauche → « Le récit de la traversée » :
la jambe Ajaccio → Fort-de-France cite au moins une ZEE, un port d’entrée
et, s’il y a eu un GRIB fort, une phrase météo. Capture du bloc.

### Lot B — ZEE locale, fin des faux « haute mer » (M)

**Objectif.** Le gazetteer MarineRegions par point est bruité (flaps le
long des côtes, « Spanish EEZ » à La Rochelle). Remplacer par un test
point-dans-polygone local sur les **ZEE VLIZ v12** que Blue Intelligence
possède déjà (285 polygones).

**Fichiers.** `backend/app/routers/…` (exposer `GET /api/eez/at?lat&lon`
et/ou `GET /api/export/eez.geojson` simplifié ≤ 5 Mo), `server/ici_engine.py`
(`lookup_zee` : local d’abord, gazetteer en repli), `server/ici_layers.py`.

**Étapes.** 1) endpoint BI point → {mrgid, name, territory} avec shapely
(déjà dans BI) ; 2) `lookup_zee` appelle BI, garde MarineRegions en repli
avec `sources.zee = "marineregions"` ; 3) invalider le cache thin
(`ici_thin_cache.json` : bump d’une version dans la clé).

**Tests.** `server/tests/test_ici_engine.py` : point à La Rochelle → 5677
(français), point 46,15 N 1,16 O jamais espagnol ; repli quand BI indisponible.

**Recette visuelle.** Simulation, lecture « lecture », Stop auto : la première
carte ZEE après La Rochelle est **française**, pas espagnole ; journal
Suivre sans aller-retour ZEE / haute mer au même jour.

### Lot C — Fiche d’escale, liste structurée (L) — *plan général §1.9*

**Objectif.** Pour chacune des 18 escales Bmap : amarrage (marina,
capitainerie, VHF), eau / carburant / électricité, avitaillement, entretien,
accastillage, tourisme, formalités (PoE Gold). Zéro rédaction LLM.

**Fichiers.** `server/escale_api.py` (nouveau, `GET /escale?name=…|lat&lon`,
cache 7 j `voyage_data/escales/*.json`), `server/ici_layers.py` (Overpass :
`amenity=fuel|drinking_water`, `shop=boat|chandlery|supermarket`,
`waterway=boatyard`, `man_made=crane`, `leisure=slipway`, `tourism=*`),
`src/components/EscaleSheet.jsx`, `src/hooks/useEscaleSheet.js`, Sidebar
gauche (Suivre : quand `atQuay` ; Simulation : au clic d’une escale dans
« Expédition »), i18n.

**Contrat.** Chaque ligne = nom cliquable (**Voir sur la carte**), ↗ site,
◎ Google Maps — même mécanique que `briefingLinks.js`. Rien n’est écrit
sans donnée : une section vide n’apparaît pas.

**Tests.** Python : Overpass mocké, cache, bornes ; JS : `escaleSheet.test.js`
(mise en forme, liens).

**Recette visuelle.** Simulation → clic « Ajaccio » dans Expédition → la
fiche s’ouvre dans le panneau gauche, sections non vides seulement, liens
qui ouvrent ; Suivre à quai → fiche de l’escale courante. Capture.

### Lot D — Chatbot journal de bord (L) — *nouveau, demandé le 19 sept.*

**Objectif.** Un chat dans le panneau gauche (Suivre) où le skipper **pose
une question** sur toutes les données de l’application (polaire, GRIB au
bateau, ZEE, ports WPI, AMP, escales, paramètres avancés, journal) **ou
consigne** une entrée de journal. Le bot distingue les deux intentions.

**Cadre.** Sans Nebius pour l’instant : cascade existante
`story_cascade.py` (NIM → OpenRouter → Claude), **contexte = données
sélectionnées**, jamais le monde. Le LLM ne calcule rien : il **cite** un
JSON de faits construit côté serveur (`GET /voyage/official/context` :
position, GRIB, ZEE, PoE, AMP, escale suivante, ordres du skipper, 20
dernières entrées du journal). Une note se consigne par le
`POST /voyage/official/journal/note` existant (clé admin).

**Fichiers.** `server/logbook_chat.py` (nouveau : intention `ask|note`,
construction du contexte, prompt sobre, filtre `tidy_story`),
`server/main.py` (`POST /logbook/chat`, débit 6/min/IP, admin requis pour
`note`), `src/components/LogbookChat.jsx`, `src/hooks/useLogbookChat.js`,
Sidebar gauche (Suivre, sous le journal), i18n.

**Étapes.** 1) contexte serveur (pur, testé) ; 2) intention par règles
d’abord (« note : … », « journal : … », verbe à l’impératif → note) puis
LLM ; 3) réponse ≤ 3 phrases, chaque chiffre traçable au contexte
(post-filtre : un nombre absent du contexte → phrase retirée) ; 4) UI :
champ, historique de session, « Consigné dans le journal » quand c’est une
note.

**Tests.** Python : intention, contexte, post-filtre des chiffres, débit ;
JS : contrat du composant (pas de fetch hors `/logbook/chat`).

**Recette visuelle.** Suivre → « Quel vent au bateau ? » → réponse citant le
GRIB du journal ; « Note : largué les amarres à 8 h » → entrée 📝 visible
dans le journal. Capture des deux.

### Lot E — Replay de l’expédition depuis le journal (S) — *§1.6*

**Objectif.** En Suivre, un curseur « jour J » relit le journal : position
du jour (entrées `position`), événements du jour (ZEE, AMP, GRIB, notes) en
cartes NOW / FREE, sans recalcul ni réseau.

**Fichiers.** `src/hooks/useReplay.js`, `src/components/ReplayBar.jsx`
(dans la barre film, Suivre seulement), `MapSceneController` (position
figée au jour choisi, `previewing`), `momentCard.js` (cartes depuis des
entrées de journal : `cardFromJournalEntry`).

**Tests.** JS : `cardFromJournalEntry`, sélection du jour, retour au live.

**Recette visuelle.** Suivre → curseur au 3 juin → bateau au large du Maroc,
carte « Entrée dans Moroccan EEZ », « Retour au live » ramène à aujourd’hui.

### Lot F — Récits pré-générés + Nebius (M) — *§1.3*

**Objectif.** Le récit LLM d’une carte est prêt **avant** que le bateau
y arrive. Unité = la jambe (Simulation) / le journal (Suivre).

**Fichiers.** `server/story_cache.py` (clé `(type, empreinte payload,
profil, langue)`, disque 7 j), `server/story_cascade.py` (cran Nebius
`NEBIUS_API_KEY`, API OpenAI-compatible, entre NIM et OpenRouter),
`server/ici_warm.py` (pré-génération des récits des événements de perles :
ZEE, PoE — par petits lots, 3 en vol), client : `storyQueue.js` lit le cache
d’abord (`GET /ici/story/cached?key=`).

**Garde-fous.** Jamais sans cache (le crédit brûlerait) ; `tidy_story`
s’applique ; budget journalier `NAVIGUIDE_STORY_BUDGET_PER_DAY` (défaut 300).

**Tests.** Python : cache hit / miss, cascade avec Nebius mocké, budget.

**Recette visuelle.** Simulation, lecture « normale » : la carte « Entrée
dans … » s’affiche déjà rédigée (pas « récit en préparation »).

### Lot G — Fixtures du moteur de route puis re-routing Simulation (L) — *§1.7*

**Étapes.** G1 (M) : fixtures `server/tests/test_route_engine.py` sur les
routes coincées (détours anti-terre, antiméridien, Panama, Corse) ; G2 (L) :
`isochrone.py` × cube de prévision × polaire × ordres du skipper (Hs et
vent max interdits) → `POST /voyage/{id}/recompute` déjà là, brouillon
accepté / rejeté ; G3 (M) : Suivre, **conseil** de route sur la couche
alternative, jamais la route officielle.

**Recette visuelle.** Simulation → Recalculer → un trait alternatif
pointillé, dialogue Accepter / Rejeter, jamais de segment sur terre.

### Lot H — Sécurité P1 (M)

`npm audit --omit=dev` + `pip-audit` en CI (bloquants sur critique) ;
en-têtes nginx (CSP, `X-Frame-Options`, `Referrer-Policy`) ; Playwright de
fumée (ouvrir, Suivre, Simulation, un clic route, un lien briefing) dans
`.github/workflows/ci.yml` ; ZAP baseline mensuel (workflow `schedule`).

**Recette.** CI verte avec les nouveaux jobs ; `curl -I` de la prod montre
les en-têtes.

### Lot I — UX de la première visite et du chauffage (S)

- Barre film : pastille « perles chauffées 42 % » tant que
  `GET /ici/warm/status` n’est pas `done`, et « le film se remplit d’événements
  au fil des perles » dans le panneau gauche quand le sac est en attente.
- Drapeaux stables pendant le suivi caméra (`scheduleWaypoints` :
  recalcul des décalages seulement à l’arrêt de la carte).
- Mode clair : relire cartes NOW / FREE, Paramètres avancés, Expédition.

**Recette visuelle.** Trois captures (sombre / clair, film en lecture).

### Lot J — Découper `App.jsx` (M, sans changement d’UI)

`useSceneWiring`, `useSatellitePopup`, `useSkipperWiring`,
`useMomentWiring` ; `App.jsx` < 800 lignes ; tests de contrat existants
inchangés ; captures avant / après identiques.

### Lot K — Revue de plan par règles (M) — *§1.8*

`src/engine/planReview.js` : par jambe, fenêtre cyclonique (croisements
IBTrACS déjà dans le sac), jours à quai, formalités (PoE Gold), saison
(atlas). Tableau « Revue du plan » dans Expédition (sidebar droite).
Rédaction LLM 1× facultative (après lot F). Aucun chiffre LLM.

### Lot L — Tavily hebdomadaire et juge de vérité (S) — *§1.11, plus tard*

Décision du 18 sept. : **rien pour le moment**. Documenté seulement.

## 3. Comment écrire le brief d’un worker Cloud

Coller : la section 0 entière, l’état (section 1), le lot visé (texte
intégral), et ces trois lignes :

```text
Branche : feat/<lot>-<slug> depuis main à jour. Une PR, pas de merge.
Recette : tests verts (npm test, pytest, vite build) + captures fixes des écrans cités.
Modèle : cursor-grok-4.6-xhigh-fast (ou composer-2.5) — jamais un modèle claude-* sur un worker Cloud.
```

# Plan en lots — NAVIGUIDE simulator (suite du plan général)

Version **1.1** — 19 septembre 2026 (après les 12 commentaires du porteur
sur la v1.0). Complète le [plan général](PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md)
(v2.0) : ce document découpe **ce qui reste** en lots **recettables** (tests
+ recette visuelle) qu'un agent Cursor prend **un par un, dans l'ordre, une
PR par lot, recette visuelle avant le suivant** (consigne du 19 sept.).

## 0. Ce que tout agent doit savoir avant de toucher au code

- **Atelier** : `naviguide-simulator/` (client Vite + React dans `src/`,
  serveur FastAPI dans `server/`). Prod : `simulator.naviguide.fr` (VPS OVH,
  déploiement automatique à chaque merge sur `main`). Rien d'autre du dépôt
  n'est concerné par ces lots.
- **Lancer en local** (Mac) : `cd naviguide-simulator && bash dev-mac.sh`
  (API `:8010` + Vite `:5174`). Tests : `npm test` (node --test),
  `.venv/bin/python -m pytest -q` ; build : `npx vite build`. La CI de la PR
  rejoue les trois.
- **Règles qui ne se discutent pas**
  1. `main` est le **plancher de l'UI** : on ajoute, on ne retire pas une
     surface visible sans demande explicite (`.cursor/rules/anti-regression-visuelle-simulateur.mdc`).
  2. **Un chiffre ne passe jamais par un LLM.** Le LLM rédige ce qui est
     collecté ; `kind` honnête (`observation ≠ forecast ≠ climatology`),
     `null + reason` plutôt qu'une valeur inventée.
  3. **Ni Tavily, ni Nemotron, ni LangSmith, ni Nebius** (commentaire 0).
     Toute rédaction passe par la **cascade LLM habituelle**
     (`story_cascade.py` : NIM → OpenRouter → Claude) avec `tidy_story`.
  4. **Recette = tests + captures fixes**, jamais de vidéo
     (`.cursor/rules/pas-de-verification-video.mdc`).
  5. Ne jamais lancer `infra/vps/sync-from-atlas.sh`.
  6. Une PR par lot, empilée sur la précédente si elle n'est pas encore
     mergée ; titre conventionnel (`feat(simulator): …`) ; description =
     objectif, ce qui change, tests, recette faite (captures).
- **Vocabulaire** : *sac `ici()`* = tout ce qu'on sait à 30 nm du bateau
  (`GET /ici`) ; *perle* = sac **riche** échantillonné tous les 12 nm le
  long de la route (depuis le lot P : toutes les couches **sans
  horodatage** — ZEE, ports d'entrée, AMP, ports, projets, fiches science,
  mouillages, balisage, EMODnet ; la météo, le satellite et la fiche Gold
  restent vivants) ; *Suivre* = le bateau officiel maintenant (1 s = 1 s) ;
  *Simulation* = le film ; *carte du moment* = NOW (sécurité / décision) +
  FREE (« pendant ce temps ») ; *journal* = mémoire serveur du voyage officiel.
- **Stockage** (question du porteur, « faut-il une base de données ? ») :
  oui, à partir du lot P — **SQLite embarqué** (`voyage_data/naviguide.sqlite`,
  module stdlib, un fichier, sauvegardé avec `voyage_data/`) pour les
  perles, puis les récits pré-générés (F) et les fiches d'escale (C). Pas de
  MongoDB côté simulateur : Mongo reste la base de Blue Intelligence, que le
  simulateur lit par HTTP. Le journal reste en fichiers JSON par jour
  (lisibles, versionnables), tant qu'il n'a pas besoin de requêtes.

## 1. État au 19 septembre 2026

> **Soir du 19 sept. — lots livrés en PR empilées (à merger dans l'ordre) :**
> P #190 · A #191 · B #192 · C #193 · D #194 · E #195 · F #196 · G #197 ·
> H #198 · I #199 · J #200 · K #201. Reste : G3 (conseil de route en Suivre),
> L (Tavily, objet du hackathon), second découpage d'`App.jsx` si besoin.
> Correctif transversal (K) : les perles portent l'échelle de milles de
> l'horloge (le tronçon terrestre Saint-Maur → La Rochelle compte) — les
> lignes du journal issues des perles étaient datées ~16 h trop tôt.

| Fait | Où |
|---|---|
| Sécurité P0, journal serveur v1, « Écouter » | #185, #186 |
| Carte du moment NOW / FREE, récit de la traversée, correctifs Suivre / Leaflet / Gold | #187 |
| Événements tout le long du film, perles pré-générées (`ici_warm.py`), voies NOW / FREE, cartes d'escale, récits sobres, caméra, reprise Simulation, Stop auto, sidebars réorganisées, récit chronologique, journal compact | #188 |
| Journal v2 partiel (ZEE, AMP depuis les perles, datés par l'horloge), vitesse de planning polaire × vent, plan en lots v1.0 | #189 |

**Chauffage** : la prod chauffe ses perles seule (`GET /ici/warm/status` sur
`simulator.naviguide.fr`) ; le lot P le **relance** (perles riches) — c'est
pourquoi il vient en premier, pour que la prod chauffe pendant les lots
suivants. **Aucun lot n'attend la fin du chauffage** : A et F consomment
les perles au fil de l'eau (le `tick()` du journal et la pré-génération
reprennent les perles arrivées depuis), B ne dépend que d'un GeoJSON de
ZEE, les autres n'en dépendent pas. Se déconnecter n'arrête rien : le
chauffeur tourne dans le serveur.

## 2. Les lots, dans l'ordre

Taille : S ≤ ½ jour d'agent, M ≤ 2 jours, L > 2 jours.

### Lot P — Perles riches + base SQLite (M) — *commentaire 1 + question base de données*

**Objectif.** Une perle porte **toutes les informations sans horodatage**
(plus un « sac thin ») et vit dans une base embarquée, pas dans un JSON de
60 Mo réécrit toutes les 30 s.

**Fichiers.** `server/pearl_store.py` (nouveau : SQLite WAL, table
`pearls(key, lat, lon, kind thin|rich, bag JSON, ts)`), `server/ici_engine.py`
(`fill_dossier(thin=True, rich=True)` : projets, science, mouillages,
balisage, EMODnet en plus ; cache mémoire L1 + SQLite ; une perle riche sert
une demande thin), `server/ici_warm.py` (chauffe **riche**, migre l'ancien
JSON une fois, `status().store`), client : `iciBriefing.js` (un sac riche
raconte science / balisage / EMODnet ; seul météo / satellite / Gold restent
« vivants »), `momentCard.js` (les FREE science / projets / câbles arrivent
aussi depuis les perles).

**Tests.** `test_pearl_store.py` (put / get / kind / purge / migration JSON),
`test_ici_warm.py` (chauffe riche, une perle riche sert un thin),
`iciBriefing.test.js` (gating riche).

**Recette visuelle.** Simulation, lecture « normale », Stop auto : des cartes
FREE **science / projets / balisage** apparaissent au large (pas seulement
ZEE / ports) ; `GET /ici/warm/status` montre `store.rich` qui monte.

### Lot A — Journal v2 complet et récit fidèle (M)

Ports d'entrée passés (`kind: poe`, depuis les perles, ≤ 15 nm, une fois par
port) et météo au bateau (`kind: wx`, dérivé des entrées `grib` : vent ≥ 34 kn
ou Hs ≥ 3,5 m — pas de GRIB, pas de `wx`). Le récit les raconte par jambe ;
`journalFormat` met en mots ; `GET /voyage/official/journal?kinds=`.
**Recette** : Suivre → récit → la jambe Ajaccio → Fort-de-France cite ZEE,
ports d'entrée et, s'il y a eu du vent fort, une phrase météo.

### Lot B — ZEE locale, fin des faux « haute mer » (M)

Le gazetteer MarineRegions par point est bruité (« Spanish EEZ » à La
Rochelle). Le serveur télécharge **une fois** le GeoJSON des ZEE que Blue
Intelligence sert déjà à la carte (cache 30 j sur disque), et répond par
**point-dans-polygone** (bbox puis ray casting, pur Python) ; MarineRegions
reste en repli (`sources.zee = "marineregions"`). Clé du cache perles
versionnée pour rechauffer la ZEE seule.
**Recette** : la première carte ZEE après La Rochelle est **française** ;
plus d'aller-retour ZEE / haute mer le même jour dans le journal.

### Lot C — Fiche d'escale (L) — *commentaire 2*

Pour chacune des 18 escales : amarrage (marina, capitainerie, VHF), eau /
carburant / électricité, avitaillement, entretien, accastillage, tourisme,
formalités (PoE Gold). **Les faits sont des listes** (OSM Overpass :
`amenity=fuel|drinking_water`, `shop=boat|chandlery|supermarket`,
`waterway=boatyard`, `man_made=crane`, `leisure=slipway`, `tourism=*` ; BI :
marinas, capitaineries, PoE, AMP, projets), chaque ligne = nom cliquable
(**Voir sur la carte**), ↗ site, ◎ Google Maps. **La rédaction** (un
paragraphe de présentation, 3 phrases) passe par la cascade LLM habituelle à
partir de ces listes seulement, filtrée par `tidy_story`, en cache SQLite 7 j ;
sans LLM, les listes seules. Une section vide n'apparaît pas.
`server/escale_api.py`, `src/components/EscaleSheet.jsx`, sidebar gauche
(Suivre à quai : escale courante ; Simulation : clic d'une escale dans
« Expédition »).
**Recette** : Simulation → clic « Ajaccio » → fiche dans le panneau gauche,
sections non vides, liens qui ouvrent ; capture.

### Lot D — Chatbot journal de bord (L) — *commentaires 3, 4*

Dans le **panneau gauche**. Le skipper pose une question sur **toutes les
données de l'application** (position, GRIB au bateau, ZEE, ports, AMP,
escales, polaire, ordres du skipper, journal) ; la réponse cite un JSON de
faits construit côté serveur (`GET /voyage/official/context`), jamais le
monde. **Pas de détection d'intention** : chaque échange est **consigné**
dans le journal (`kind: chat`, horodatage, question, réponse, résumé LLM
d'une phrase) quand la clé admin est là ; sans clé, réponse sans
consignation (marquée « non consigné »). Cascade LLM habituelle, post-filtre
des chiffres (un nombre absent du contexte → phrase retirée), débit 6 / min / IP.
`server/logbook_chat.py`, `POST /logbook/chat`, `src/components/LogbookChat.jsx`.
**Recette** : « Quel vent au bateau ? » → réponse citant le GRIB du journal ;
l'échange apparaît dans le journal en 💬 avec son résumé.

### Lot E — Replay narré de l'expédition (M) — *commentaire 5*

« **Revoir l'expédition** » (Suivre, barre film) : le bateau **rejoue la
route depuis Saint-Maur jusqu'à sa position d'aujourd'hui** sur l'horloge
officielle (1 jour ≈ 1 s, escales marquées), la date rejouée dans la barre,
le **récit** raconté jambe par jambe (paragraphe courant mis en avant et lu à
voix haute si « Écouter » est actif), les événements du journal (ZEE, AMP,
escales, `wx`, notes) surgissant en cartes à leur date. Fin : retour au live.
`src/hooks/useReplay.js`, `src/components/ReplayControls.jsx`, `App.jsx`
(le live devient la position rejouée pendant le replay), `momentCard.js`
(`cardFromJournalEntry`).
**Recette** : Suivre → Revoir → le bateau part de La Rochelle, passe Ajaccio,
traverse l'Atlantique, les cartes défilent, la voix raconte ; capture à
mi-parcours et à l'arrivée sur le live.

### Lot F — Récits pré-générés (M) — *commentaires 6, 7, 8 : sans Nebius*

Le récit LLM d'une carte est prêt **avant** que le bateau y arrive :
`server/story_cache.py` (SQLite, clé `(type, entité, langue)`), `POST /ici/story`
lit le cache d'abord ; après les perles, le chauffeur pré-génère les récits
des événements de route (ZEE entrée, port d'entrée devant) avec la cascade
habituelle, 3 en vol, budget `NAVIGUIDE_STORY_BUDGET_PER_DAY` (300).
**Recette** : Simulation « normale » : la carte « Entrée dans … » s'affiche
déjà rédigée (pas « récit en préparation »).

### Lot G — Moteur de route (L)

G1 fixtures des routes coincées (détours anti-terre, antiméridien, Panama,
Corse) ; G2 **conseil de route** : `POST /voyage/{id}/recompute` sous les
contraintes des ordres du skipper (vent max, Hs max), trait alternatif
pointillé, Accepter / Rejeter, jamais la route officielle.

### Lot H — Sécurité P1 (M)

`npm audit --omit=dev` + `pip-audit` en CI (bloquants sur critique),
en-têtes nginx (`X-Frame-Options`, `Referrer-Policy`, `X-Content-Type-Options`,
`Permissions-Policy`, CSP en *report-only* d'abord), Playwright de fumée
(ouvrir, Suivre, Simulation, un calque, un lien du briefing), ZAP baseline
mensuel.

### Lot I — UX (S/M) — *commentaires 9, 10*

- **Mode « Tracer votre propre route »** (capture du 19 sept.) : pendant le
  tracé, la boîte **Expédition** de droite décrit la **route tracée**
  (distance, waypoints, escales choisies) et non la route officielle ; la
  **barre film** annonce le tracé en cours (pas « La Rochelle → Ajaccio ») ;
  aucun marqueur ni épingle de briefing de la route officielle ne reste sur
  la carte ; le panneau gauche liste les points posés (annuler le dernier).
- Drapeaux stables pendant le suivi caméra ; mode clair relu (cartes NOW /
  FREE, Paramètres avancés, Expédition).
- **Pas** de pastille « perles chauffées » ni de message de remplissage
  (commentaire 10).

### Lot J — Découper `App.jsx` + profiler le build de prod (M)

`useSceneWiring`, `useSatellitePopup`, `useSkipperWiring`, `useMomentWiring` ;
`App.jsx` < 800 lignes ; captures avant / après identiques. Puis **profiler
une fois le build de prod** (`vite build` + `vite preview`, Chrome
Profiler 60 s de lecture « normale ») — les chiffres dev surestiment React ;
consigner les résultats dans `docs/` et ne créer un Web Worker que si le
profil de prod le justifie.

### Lot K — Revue de plan par règles (M)

`planReview.js` : par jambe, fenêtre cyclonique (IBTrACS du sac), jours à
quai, formalités (PoE Gold), saison (atlas). Tableau dans Expédition.

### Lot L — Tavily hebdomadaire et juge de vérité — *plus tard, objet du hackathon (commentaire 11)*

Décision maintenue : rien pour le moment. À concevoir comme **l'objet qui
fait gagner le hackathon** : veille hebdomadaire par escale, juge de vérité
des récits, sources datées. Spécification à écrire après le lot K.

## 3. Comment écrire le brief d'un worker Cloud

Coller : la section 0 entière, l'état (section 1), le lot visé (texte
intégral), et ces trois lignes :

```text
Branche : feat/<lot>-<slug> depuis la branche du lot précédent (ou main). Une PR, pas de merge.
Recette : tests verts (npm test, pytest, vite build) + captures fixes des écrans cités.
Modèle : cursor-grok-4.6-xhigh-fast (ou composer-2.5) — jamais un modèle claude-* sur un worker Cloud.
```

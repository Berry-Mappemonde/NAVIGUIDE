# Plan général de développement — NAVIGUIDE simulator

Atelier **`naviguide-simulator/`** (`simulator.naviguide.fr`). Prod `www` et
Blue Intelligence intouchées. Version **1.0** — 18 septembre 2026.

Ce plan **chapeaute** les plans d’atelier existants (Suivre / Simulation,
événements `ici()`, skipper, chantiers structurants, pipeline d’affichage,
UI produit). Il ne les réécrit pas : il dit **dans quel ordre** et
**pourquoi**, après relecture du code du 18 septembre.

---

## 0. Ce que le code dit (état réel)

| Bloc | Réalité (18 sept. 2026) |
|---|---|
| Client | ~20 000 lignes : `engine/` 8 800 (pur, testé), `hooks/` 2 900, `layers/` 2 100, `components/` 2 200, `map/` 1 400, `App.jsx` **1 549** |
| Serveur | FastAPI `:8010`, ~8 900 lignes, **37 endpoints** ; `ici_layers.py` 1 488, `ici_engine.py` 854, `voyage_api.py` 792, `saildocs.py` 681, `route_engine.py` 640, `polar_engine.py` 619, `isochrone.py` 325, `weather_pipeline.py` 324, `story_cascade.py` 291 |
| Moteur | sac `ici()` 30 nm (14 familles, `kind` honnête, `null + reason`), détecteurs E1 / lookahead E2, juge E3, pastilles E4, récit E5 (NIM → OpenRouter → Claude), ordres skipper S1–S7, pipeline météo async partagé, briefing en langage naturel avec liens |
| Données | Copernicus Marine, Open-Meteo GFS, RTOFS, Saildocs GRIB2, CDSE STAC, EMODnet, MarineRegions, Overpass, API live Blue Intelligence (ZEE, PoE, AMP, projets, science, atlas climatologie) |
| Persistance | **JSON sur disque** (`voyage_data/`, 180 Mo en local : voyages + cubes). Pas de base. Rien n’est archivé jour après jour. |
| Sécurité | **Aucune authentification** sur les écritures : `PUT /voyage/official`, `POST /voyage/official/grib*`, `POST /voyage`, `POST /ici/story` (dépense LLM), `POST /api/v1/polar/upload` (parse PDF / XLSX). CORS `allow_origins=["*"]`. Pas de limite de débit. nginx expose `/voyage` et `/ici` au public. |
| Tests | 381 JS (`node --test`), ~128 Python ; CI simulateur écrite, **à activer** (jeton `workflow`) |
| Perf | 60 fps, 0 long task ; coût = rendu React (dev), pas le moteur ; Web Worker inutile |

**Forces.** Un moteur pur et testé (détecteurs, juge, skipper), une discipline de
vérité des données rare (`observation ≠ forecast ≠ climatology`, jamais un
chiffre inventé), un film qui n’attend jamais un modèle.

**Manques structurels.** Trois, et tout le reste en découle :

1. **Pas de mémoire.** Chaque visite recalcule ; le Suivre montre *maintenant*
   mais ne sait pas raconter *depuis le départ*. Sans journal, ni replay de
   l’expédition, ni histoire, ni « ce qui s’est vraiment passé ».
2. **Pas de pré-calcul.** Le récit arrive après le passage du bateau ; la fiche
   d’escale n’existe pas ; tout ce qui est prévisible est calculé au dernier
   moment.
3. **Pas de garde.** Un inconnu peut réécrire la route officielle, remplir le
   disque de voyages, ou brûler les crédits LLM. C’est le seul point où le
   produit est fragile *aujourd’hui*.

---

## 1. Réanalyse ciblée de chaque idée

Format : ce qu’on pensait → ce que je recommande après lecture du code.

### 1.1 Sécurité et tests web (PenTest) — **priorité absolue**

*Pensé :* « un PenTest et les tests courants ». *Recommandé :* d’abord fermer
ce que la relecture montre, ensuite seulement automatiser un scan.

- **P0 (cette semaine)** : un en-tête `X-Naviguide-Admin` (secret dans
  `~/.config/naviguide/simulator.env`) obligatoire sur `PUT /voyage/official`,
  `POST /voyage/official/grib*`, et l’acceptation / rejet de voyage ;
  `limit_req` nginx sur `/ici/story`, `/voyage`, `/api/v1/polar/upload`
  (ex. 10 / min / IP) ; CORS restreint à `simulator.naviguide.fr` + `localhost` ;
  taille maximale d’upload polaire (2 Mo) et quota de voyages sur disque
  (purge des brouillons > 7 jours).
- **P1** : `npm audit --omit=dev` et `pip-audit` dans la CI ; en-têtes
  (CSP, `X-Frame-Options`, HSTS via Cloudflare) ; tests e2e Playwright de
  fumée (ouvrir, Suivre, Simulation, un clic route, un lien briefing).
- **P2** : scan **OWASP ZAP baseline** mensuel contre le site (lecture seule,
  gratuit) ; un PenTest externe payant seulement si un partenaire l’exige —
  pour un site public en lecture, P0 + P1 + ZAP couvrent l’essentiel.

### 1.2 Journal serveur du voyage officiel (la « mémoire »)

*Pensé :* replay = relire un journal. *Recommandé :* le journal est **le lot
fondateur**, pas un détail du replay. Forme minimale, bon marché :
`voyage_data/official/journal/YYYY-MM-DD.json` — position à 00, 06, 12, 18 UTC,
résumé GRIB au bateau (vent, Hs, pluie), événements jugés `now` / `group` avec
leurs récits, sac `ici()` allégé aux escales. Écrit par le refresh GRIB
quotidien déjà en place (`voyage_api`). Ce journal nourrit : replay, histoire,
fiche d’escale « vécue », carnet de bord public, évaluations LangSmith.

### 1.3 Prélancer les appels LLM

*Pensé :* cache serveur + préchauffage. *Recommandé, plus précis :* l’unité de
pré-calcul est **la jambe** en Simulation (déterministe : route, `t0`, profil,
ordres → les perles `along` existent déjà) et **le journal** en Suivre. Cache
serveur clé = `(type, empreinte payload, profil skipper, langue)` ; préchauffage
d’une jambe par petits lots (max 3 en vol, déjà la règle E5) ; le client
consomme le cache au passage. Les seuls imprévisibles restent le GRIB du jour et
les scènes satellite : racontés en direct. À mesurer honnêtement : si le récit
LLM n’apporte pas plus que la phrase locale sur un type d’événement, on garde la
phrase locale (moins cher, jamais faux).

### 1.4 Carte du moment (popups le long de la route)

*Pensé :* une popup à chaque événement affichable. *Recommandé :* **une seule**
« carte du moment », posée sur la carte au lieu de l’événement, qui remplace la
précédente (pas d’empilement), avec les mêmes liens que le briefing (voir sur la
carte, fiche, Google Maps). Elle prend tout son sens en **Cinéma** (sidebars
rangées) : c’est là qu’aujourd’hui le visiteur ne voit rien. Base technique
déjà là : pane `briefing-focus`, `MapSceneController.api.briefing`, juge E3.

### 1.5 Histoire de l’expédition et « histoire dictée »

*Pensé :* journal lu à la suite, texte puis voix. *Recommandé :* un **chapitre
par jambe**, rédigé une fois (LLM autorisé : c’est de la rédaction de données
déjà collectées, 1× par jambe, mis en cache dans le journal), et une page
publique « carnet de bord ». La voix = `speechSynthesis` du navigateur (gratuit,
local, zéro LLM), un bouton « écouter » par chapitre. Si « dictée » voulait dire
*l’équipage dicte* (saisie vocale à bord), c’est un autre produit : à trancher.

### 1.6 Replay de l’expédition

*Pensé :* comme le replay d’une jambe en Simulation. *Recommandé :* le replay
Suivre **relit le journal** (zéro recalcul, zéro appel réseau) : curseur sur les
jours écoulés, position et événements archivés. Sans journal, on ne peut que
rejouer une reconstruction climatologique — ce serait mentir sur « ce qui s’est
passé ». Donc : après 1.2, petit lot.

### 1.7 Routing et re-routing

*Pensé :* routage météo sur le couloir GRIB 24–48 h en Suivre. *Recommandé :*
inverser l’ordre. En Suivre la route officielle est **figée** par le plan
(« Recalculer absent ») ; le re-routing y est au mieux un **conseil** affiché
sur la couche route alternative, jamais une modification. Le vrai chantier est
en **Simulation** : `isochrone.py` existe (propagation, élagage, test terre) ;
il faut le brancher sur le cube de prévision (Simulation B) et la polaire, et
faire des **ordres du skipper des contraintes** (cases Hs > seuil ou vent >
coup de vent interdites). Avant toute fonctionnalité : des fixtures sur
`route_engine.py` (640 lignes de détours anti-terre, fragiles) — c’est là que
les routes « coincées » sont nées.

### 1.8 Expert en planification de circumnavigation

*Pensé :* Nemotron en raisonnement long. *Recommandé :* un module pur
`planReview.js` de **règles** : fenêtre cyclonique par jambe (les croisements
IBTrACS existent déjà dans le sac), jours à quai (`voyageClock`), formalités par
ZEE (PoE Gold), saison des alizés / mousson (atlas). Sortie = tableau « revue du
plan » par jambe, puis **une** rédaction LLM 1× (Nemotron optionnel). Le LLM ne
produit aucun chiffre. Cela réutilise `climatology_atlas`, `voyage_clock`,
`ici_engine` sans nouveau fournisseur.

### 1.9 Briefing d’escale et ravitaillement (nouvelle idée)

*Recommandé :* une **fiche d’escale** par escale Bmap (18), calculée côté
serveur une fois (cache 7 jours), affichée dans la sidebar quand le bateau est à
quai, et en Simulation quand on clique une escale. Sections : amarrage (marina,
capitainerie, VHF si connue), eau / carburant / électricité, avitaillement
(supermarché, marché), entretien (chantier, grue, aire de carénage → antifouling,
réparations), accastillage, tourisme à terre, formalités (PoE Gold). Sources
déjà à portée : catalogue BI (marinas, capitaineries, PoE), **Overpass** autour
de l’escale (`amenity=fuel`, `drinking_water`, `shop=boat|chandlery`,
`waterway=boatyard`, `man_made=crane`, `leisure=slipway`, `shop=supermarket`,
`tourism=*`) — même mécanique que les capitaineries déjà ajoutées. Chaque
élément garde le contrat du briefing : nom cliquable (carte), ↗ site officiel,
◎ Google Maps. Rédaction LLM facultative, en cache. C’est le lot le plus
**visible** pour un visiteur et le plus utile à l’équipage.

### 1.10 LangSmith (100 $)

*Pensé :* microscope des agents NAVIGUIDE. *Recommandé :* le simulateur a une
seule chaîne LLM qui compte, `story_cascade.py` ; c’est **elle** qu’il faut
observer et **évaluer** : un jeu de ~30 événements JSON, un juge automatique
« cite `skipper.used` ? n’invente aucun chiffre ? bonne langue ? », rejoué à
chaque changement de prompt. La branche `cursor/langsmith-naviguide-local-f5fa`
(garde-fou local, guide Mac, trajets or) se merge telle quelle ; les agents
NAVIGUIDE (orchestrateur) sont un autre produit, plus tard. 100 $ couvrent
largement traces + évaluations ; jamais un batch ports / marinas.

### 1.11 Tavily / Nemotron

*Pensé :* hors scope, puis « cette URL ». *Recommandé :* Tavily en **tâche
serveur hebdomadaire** qui vérifie la fraîcheur des pages PoE Gold déjà dans le
sac (pas par clic utilisateur : moins cher, pas de fuite de charge) ; Nemotron
uniquement pour la revue de plan (1.8) et le juge de vérité 1× par fiche Gold.
Rien pour les récits d’événement : NIM court suffit.

---

## 2. Vision produit (ce qui doit rester vrai)

- Le simulateur est un **instrument honnête** : il montre ce qui est mesuré,
  prévu ou typique, et le dit. Un visiteur comprend où est le bateau, ce qu’il
  y a autour, ce qui l’attend ; l’équipage prépare l’escale et anticipe.
- Deux boutons, un bateau officiel, un film. Le film n’attend jamais un modèle.
- Un chiffre ne passe jamais par un LLM ; le LLM **rédige** ce qui est collecté.
- `main` est le plancher de l’UI ; on ajoute, on ne retire pas.
- Atlas MongoDB figé ; le VPS est la vérité ; jamais `sync-from-atlas.sh`.

---

## 3. Phases

Taille : S ≤ 1 jour d’agent, M ≤ 3 jours, L > 3 jours. Une PR par lot.

### Phase 0 — consolider (cette semaine)

| Lot | Taille | Dépend de |
|---|---|---|
| Merger #180 (S6/S7), #181 (briefing liens + langage naturel), #182 (perf légende) | S | recette locale |
| Activer la CI simulateur (jeton `workflow`, branche `ci/tests-simulateur`) | S | — |
| **Sécurité P0** : `X-Naviguide-Admin` sur les écritures officielles, `limit_req` nginx, CORS restreint, taille d’upload, purge des brouillons | M | — |
| Merger la branche LangSmith (mise à jour sur `main`) | S | — |

### Phase 1 — mémoire et fluidité

| Lot | Taille | Dépend de |
|---|---|---|
| **Journal serveur** du voyage officiel (1.2) | M | P0 |
| **Pré-génération des récits** + cache serveur (1.3) | M | journal (Suivre) ; rien (Simulation) |
| **Carte du moment** sur la carte, surtout en Cinéma (1.4) | S | pré-génération |
| LangSmith : séance guide + jeu d’évaluation du récit (1.10) | S | — |

### Phase 2 — l’escale et l’histoire

| Lot | Taille | Dépend de |
|---|---|---|
| **Fiche d’escale / ravitaillement** (1.9) : endpoint `GET /escale`, Overpass + BI, cache 7 j, carte sidebar | L | liens briefing |
| **Chapitres de l’expédition** + page carnet de bord + bouton « écouter » (1.5) | M | journal |
| **Replay Suivre** depuis le journal (1.6) | S | journal |

### Phase 3 — planifier et router

| Lot | Taille | Dépend de |
|---|---|---|
| Fixtures `route_engine.py` (routes coincées, antiméridien, détours) | M | — |
| **Revue de plan** par règles (1.8) + rédaction 1× | M | atlas, voyageClock |
| **Re-routing Simulation** : isochrone × cube × polaire × ordres skipper (1.7) | L | fixtures, cube |
| Conseil de route Suivre sur la couche alternative (jamais la route officielle) | M | re-routing |

### Phase 4 — vérité et durcissement

| Lot | Taille | Dépend de |
|---|---|---|
| Tavily hebdomadaire : fraîcheur des pages PoE Gold (1.11) | S | P0 |
| Nemotron juge de vérité 1× / fiche Gold visible | S | Tavily |
| Playwright e2e de fumée + `npm audit` / `pip-audit` en CI (P1) | M | CI active |
| ZAP baseline mensuel (P2) | S | P1 |

### Transverse (au fil de l’eau)

- Découper `App.jsx` (1 549 lignes) en hooks de composition : `useSceneWiring`,
  `useSatellitePopup`, `useSkipperWiring` — sans changer l’UI.
- Profiler le **build de prod** une fois (les chiffres dev surestiment React).
- Chaque plan d’atelier reçoit un encart *Statut* quand un lot est mergé.

---

## 4. Ce qu’on ne fait pas (pour l’instant)

Web Worker (le profil dit non). Recalcul de la route officielle en Suivre.
Saisie vocale à bord. Mongo pour le simulateur (le JSON + journal suffit à
cette échelle). Nemotron / Tavily hors des usages nommés ci-dessus. Un PenTest
externe avant P0 + P1.

---

## 5. Décisions à prendre par le porteur du projet

1. « Histoire **dictée** » : lue à voix haute (recommandé) ou dictée par l’équipage ?
2. Fiche d’escale : rédaction LLM (plus fluide, un coût) ou liste structurée seule (gratuit, toujours exact) ? Recommandation : liste d’abord, rédaction en option.
3. Sécurité P0 : un secret admin partagé suffit-il, ou faut-il un vrai compte (GitHub OAuth) ? Recommandation : secret partagé maintenant, compte plus tard.

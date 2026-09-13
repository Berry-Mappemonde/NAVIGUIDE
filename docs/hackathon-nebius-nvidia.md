# Hackathon Nebius × NVIDIA — cahier unique

**Produit :** NAVIGUIDE Simulator — on rejoue Berry-Mappemonde.  
**Track :** Best Apps and Agents  
**Code :** `naviguide-simulator/` (à créer, extractible) — **pas** un patch de la prod  
**Date :** 13 septembre 2026 (soir) — arbitrages **v3.0**

**Chantier étape 1 (cockpit Leaflet) :** [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)

**Deadline soumission :** vendredi 30 octobre 2026, 10:00 PT  
**Jugement :** 1–15 décembre 2026 · résultats vers le 11 janvier 2027  
**IRL :** Builders & Brews **Toronto, mardi 29 septembre 2026** (pas Paris)

Cahier interne, pas une soumission Devpost. Un seul fichier pour les orientations **et** le plan pour gagner. Les anciennes copies (`PLAN_HACKATHON_GAGNER.md`, Clearance Brief dans `backend/`, 4 chats, ConTree, MapLibre, `llm_cascade` en prod) sont **annulées**.

---

## 1. Comment on gagne

Les juges vont voir des centaines de chatbots Nemotron. On gagne si, en **20 secondes de vidéo**, ils comprennent :

> Un bateau avance sur une vraie circumnavigation. Il entre dans une ZEE. La carte montre les Ports d’entrée **Gold**. Tavily **revérifie cette fiche**, pas le monde. Nemotron Ultra **barre** ce qui n’est plus prouvé. Le récit vient d’un petit dossier « vu du cockpit », pas de la carte entière.

On soumet **un seul produit** : le **simulateur**. `ici()` prépare le sac. Nano / Lightning **racontent**. Tavily **revérifie la fiche Gold de cette ZEE**. Ultra **barre**. Un Briefing, **pas** 4 chats.

Le méga-briefing éco-tourisme (toutes les couches) est le **même** produit, sérialisé : d’abord le film + le sac + PoE Gold + Tavily/Ultra ; le reste se branche plus tard sur le même Briefing.

| Critère (poids égal) | Notre preuve |
|---|---|
| **Technological Implementation** | Token Factory runtime (pas NIM). Nano / Lightning racontent. Ultra juge. Tavily ancré sur une fiche. |
| **Design** | Un film Leaflet, un briefing, des boutons de couches. Pas 4 chats, pas la Console BI. |
| **Potential Impact** | Formalités plaisance (ZEE / PoE), expédition Berry-Mappemonde, disclaimer honnête. |
| **Quality of the Idea** | Sac `ici()`, pas un container. Tavily ne cherche pas « ports of entry ». Ultra n’est pas sur chaque clic. |

**Prix visés :** Grand Prize (20 000 $) + bonus Tavily (3 000 $). Un seul bonus : on privilégie Tavily plutôt que City (500 $), tout en allant à Toronto.

**NIM (`integrate.api.nvidia.com`) ne compte pas.** Toute l’inférence de soumission passe par Token Factory + au moins un Nemotron.

---

## 2. Le film (ce que le juge voit)

1. On **rejoue** l’expédition. Le bateau avance (Précédent / Suivant).  
2. Il **entre dans une ZEE** (polygone Blue Intelligence).  
3. Si elle est **Gold** : Ports d’entrée + lien officiel.  
4. Tavily ne cherche pas le monde : il **revérifie cette fiche**.  
5. Ultra barre ce qui n’est plus prouvé.  
6. Un événement météo / climat : l’agent raconte le bulletin (cyclone nommé, avis) — Copernicus reste les **chiffres au point**.  
7. Stretch : proximité AMP / projet (« parc, saison, mouillage ») — pas obligatoire pour la première soumission.

Ce n’est plus un chatbot. C’est un **voyage**.

---

## 3. Le hackathon (règles utiles)

- **Page :** https://nebiusglobalaihackathon.devpost.com/  
- **Sponsor :** Nebius B.V. · **Admin :** Devpost  
- **~3 660** inscrits au 12 septembre 2026  
- France éligible (exclus : Brésil, Québec, Russie, Crimée, Cuba, Iran, RPDC, OFAC)

**Éliminatoire :** appel **runtime Token Factory** **ou** Nebius AI Cloud (Jobs / Endpoints / DevPods) + **au moins un** modèle NVIDIA open source.

Juges **non obligés** de tester le code. « Push past the obvious » : un wrapper Nemotron = perdu.

| Prix | Montant | Notre choix |
|---|---|---|
| Grand / 2e / 3e | 20k / 10k / 6k $ | Objectif Overall |
| Track | Jetson Orin Nano | Si pas Overall |
| Best Use of Tavily | 3 000 $ | **Bonus visé** (appel runtime) |
| City Winner | 500 $ | Toronto — **un seul bonus** : on privilégie Tavily |
| Feedback | 100 $ + swag | Remplir quand même |

---

## 4. Architecture verrouillée (v3.0)

```
Skipper (cockpit Leaflet, 2 sidebars 320 px)
        │  useLegContext
        ▼
ici(lat, lon)     ← sac (~30 nm), PAS 4500 projets
        │
Événement ?  ──non──►  JSON seul (gratuit)
        │ oui
        ▼
Tavily (cette fiche) → Nano raconte → Ultra juge
        ▼
Un Briefing + pastilles sur la carte
```

| Mot | Sens |
|---|---|
| Film | Sidebars NAVIGUIDE, route, bateau, tracer, boutons |
| Projecteur | **Leaflet** (comme Blue Intelligence), **plus** MapLibre |
| Légende | 10 pastilles : ZEE, WPI, Balisage, Projets, Marinas, Capit., PoE, AMP, Science, Climatologie. **Plusieurs allumées ensemble** (contrairement aux 6 modes BI) |
| Moteur bateau | searoute Python + polar (VMG / upload), **sans chat**, **sans** grille 181×61 dans le prompt |
| Moteur situation | `ici()` **avant** tout LLM |
| Le projet | Un récit d’événement |

### Sac à dos

Rayon ~20–50 nm (cible **30 nm**) + « quelle ZEE contient ce point » :

| Couche | Dans le sac | Pas ça |
|---|---|---|
| ZEE | 1 polygone, nom, `mrgid`, Gold ? | 285 textes |
| PoE | Ports **de cette ZEE**, URL officielle, statut | Tous les PoE |
| AMP / Projets | Près du trait | Le catalogue |
| Marinas / capit. / WPI | 3–5 plus proches | OSM entier |
| Balisage | De la zone | Le monde |
| Science | 0 ou 1 jeu localisé | Sextant entier |
| Vent / vague / courant | Au **point** | Le globe |
| Polaires | Vitesse / ETA **de cette jambe** | Grille 181×61 / CSV |
| Tavily | Cette fiche / cet avis | `search("ports of entry")` |

Les boutons allument **toute** la couche sur la carte. Le LLM n’en voit qu’une poignée.

### Interdit

| Interdit | Pourquoi |
|---|---|
| 4 chats Ports / Sécurité / Météo / Cruisers | Remplacés par le Briefing |
| Chat polar (`POST /polar/chat`) | Le récit n’est pas un Q&A VMG |
| Import / export GeoJSON / KML | Route = Berry **ou** crayon + searoute |
| Console / Review / Swarm / 6 modes | UX opérateur BI |
| MapLibre / PMTiles « carte marine » | On change de projecteur |
| Recoller `:8000` / `:8004` | Cassera l’extraction hackathon |
| ConTree en 2ᵉ soumission | Un seul produit, track Apps |
| NIM comme cerveau de soumission | Hors règlement |
| Modifier `frontend/`, `backend/`, `naviguide/`, `infra/vps/` | Prod intouchée |

**Prod `naviguide.fr` / `blueintelligence.online` intouchées.**

---

## 5. Où ça vit

Le monorepo est **public**, licence MIT (PR #78).

```
Blue-Intelligence-Map/
├── frontend/ backend/ naviguide/   # PROD — on lit, on n’édite pas
├── naviguide-simulator/            # NOUVEAU — extractible (hackathon)
└── docs/
    ├── hackathon-nebius-nvidia.md  # ce fichier (orientations + plan)
    └── PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md
```

| Où | Rôle |
|---|---|
| `naviguide-simulator/` dans ce dépôt | Développement extractible — **aucune** import `../../frontend` |
| `main` | Prod VPS — on n’y merge pas le simulateur « pour tester » |
| Dépôt public dédié (plus tard) | URL Devpost : `git subtree split` ou copie, README EN, historique période hackathon |

Créer le dépôt dédié à la main (l’agent GitHub est en lecture seule).

---

## 6. Contraintes réelles

### Gold PoE

Tavily s’appuie sur **la carte**, pas l’inverse. Minimum concours : ZEE de la **route Berry** (et de la jambe démo). Ambition skipper : **285** si l’accélérateur garde le critère Gold (source + géométrie). Un Gold **faux** est pire qu’un « probable » — sinon statut `accelerated` à côté de Gold.

Les 11 polygones déjà Gold restent un **jeu d’éval** (Nano extrait / Ultra barre). Disclaimer : ne convient pas à la navigation.

Le simulateur **lit** `/bi/export/poe.geojson` (ou un export figé dans `public/` pour la démo autonome).

### Crédits reçus (13 septembre)

Organisation **Berry-Mappemonde** :

| Service | Observé | Usage |
|---|---|---|
| Token Factory | ~**60 $** ; essai 29 j / 1,00 $ restant | Nano / Lightning / Ultra. `NEBIUS_API_KEY` hors git |
| Tavily Researcher | **0 / 10 000** + add-on **0 / 3 125** | Extract / Search / Research **mini** sur **cette** fiche |
| Toloka / Tendem | 50 $ + 50 $ | Hors soumission |

Discipline : **un Ultra par action visible**. Tavily `mini`, pas de `pro` au clic, pas de crawl sans `limit`, pas de Search à chaque « Suivant ». Tenir ~30–80 crédits / run démo.

### Routage prototype

Le simulateur **lit** searoute + polar + vent au point. On ne soumet pas le moteur isochrone weather-routing. Draw = crayon + searoute, pas un fichier.

---

## 7. État du code prod (lecture seule)

NIM partout, **pas** Token Factory, **pas** Nemotron actif, **pas** Tavily.

- BI : `backend/app/core/nvidia.py` → `integrate.api.nvidia.com` (DeepSeek / gpt-oss / Muse / Kimi).  
- NAVIGUIDE : `llm_cascade.py` + LangGraph qui **commente** ; 4 chats simulation ; MapLibre ; polar **avec** chat.  
- Recherche web BI : SearXNG, TinyFish, Serper, OpenRouter `:online`.

**À copier (pas importer) dans le simulateur :** `useLegContext`, searoute (`naviguide-api` — `GET /route`, jamais le npm `searoute-js`), `polar_engine.py` **sans** chat, styles Leaflet BI, `backend/data/route.geojson` en fallback, exports `/api/export/*`.

**Risque Stage 1 :** le README prod peut déjà parler Token Factory / Nemotron alors que le code est NIM. La soumission = le **simulateur**, pas ce README.

---

## 8. Roadmap jusqu’au 30 octobre

| Étape | Quoi | Hackathon | Qui |
|---|---|---|---|
| **Fait** | Crédits TF + Tavily ; Toronto choisi | — | Humain |
| **1** | Cockpit Leaflet, Berry, draw, polar sans chat, stub `ici()` | Zéro Tavily / Nemotron | Agent — [plan étape 1](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md) |
| **2** | Sac réel (ZEE, PoE, proches 30 nm, `entered_eez`) sur le serveur simulateur | Toujours pas Tavily | Agent |
| **3** | Gold route Berry, voire 285 | Carburant de la démo | Humain |
| **4** | Nano raconte le JSON (adaptateur **dans** le simulateur) | Token Factory apparaît | Agent |
| **5** | Tavily sentinelle de fiche | Bonus 3 000 $ | Agent |
| **6** | Ultra + stretch AMP + vidéo + dépôt dédié | Soumission | Les deux |
| **29 sept.** | Builders & Brews Toronto — film, idéalement sac amorcé | Mentors, pas besoin d’Ultra | Humain |
| **Fin octobre** | Gel, démo dédiée (pas naviguide.fr), soumission | — | Les deux |

**Pas d’étape 5 si l’étape 1 n’est pas recettable** (A1–A7, A11, E1–E5). Un Nemotron collé sur un cockpit vide = wrapper = Stage 1 fail.

### Étape 1 — poser le cockpit (résumé)

Détail verrouillé : [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md).

`naviguide-simulator/` = cockpit NAVIGUIDE (route Berry, tracer, polaires, simulation) sur Leaflet + légende — sans 4 chats, sans chat polar, sans import/export, sans toucher la prod.

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
# autre Terminal
npm install && npm run dev   # http://localhost:5174
```

On reconnaît NAVIGUIDE. Le bateau avance. Leopard 46 se charge. On trace 3 points searoute. Les pastilles existent. Le dossier cockpit est **presque vide** (honnête). Aucun chat.

**Backend 8010 :** `/route`, polar upload/get/summary (**pas** `/chat`), proxies ZEE/WPI/seamark, `/wind|/wave|/current`. Pas `/agents/*`.

**On crée seulement** `naviguide-simulator/**` : Vite 7 + React 19 + Tailwind 4, port **5174**. Pas de maplibre, pas de react-leaflet, pas de searoute-js, pas de LangGraph « pour agents ». Adaptateur Token Factory / Tavily = **dans ce dossier**, pas dans `backend/app/core/`.

**On n’ouvre pas :** `frontend/src/**`, `backend/app/**`, `naviguide/**` (sauf lecture pour copier), `infra/vps/**`.

**Ne pas open-sourcer :** `.env`, dumps Mongo, PMTiles, Review nominatif, clés.

BI sur `:8001` est **optionnel** pour les couches `/bi`. Le simulateur doit tourner sans (erreurs honnêtes) ; export figé dans `public/` pour la démo autonome.

**Critère de sortie :** recettes A1–A7, A11, E1–E5 du plan étape 1. Sinon pas d’étape 2.

### Étape 2 — le sac réel (`ici()`)

Route **du serveur simulateur** (pas la prod) : « quelle ZEE contient ce point » (shapely / extrait de `zee_crossings`), PoE de ce `mrgid`, 3–5 points dans 30 nm, événement `entered_eez` si le `mrgid` change.

Le Briefing peut déjà **afficher** le JSON en clair (sans LLM). Le juge technique qui ouvre le `<details>` voit le contrat.

### Étape 3 — Gold (travail skipper)

Voir §6. En parallèle des étapes 1–2.

### Étape 4 — Nano / Lightning racontent

Adaptateur Token Factory **dans le dossier simulateur** (`NEBIUS_API_KEY` en env, jamais git).

- Lightning / Nano : 1 paragraphe skipper FR/EN depuis le JSON `ici()`.  
- Thinking OFF pour le JSON / le texte court.  
- HUD visible : modèle, région, latence, coût.  
- Ultra **pas encore**.

Sans clé : le texte local de l’étape 2 reste. La démo ne doit pas être noire.

### Étape 5 — Tavily, sentinelle de la fiche

Éligibilité bonus : **appel runtime** dans la solution.

| Faire | Ne pas faire |
|---|---|
| Extract (puis Search allowlist) sur **l’URL officielle de la ZEE** | `search("ports of entry")` |
| `time_range=week` pour un avis | `include_answer=true` (court-circuite Nemotron) |
| Research **mini** + `files=[leg.json]` si briefing sourcé | Research `pro` à chaque pas |
| Un run à l’**entrée de ZEE** ou au clic | Un Search à chaque « Suivant » |

### Étape 6 — Ultra + soumission

- **Un** Ultra par action visible : cite-or-reject sur les PoE extraits. L’UI **montre** Nano « 12 ports » puis Ultra en barre 2.  
- Stretch : AMP « parc / saison / mouillage » ; bandeau climatologie.  
- Extraire `naviguide-simulator/` → dépôt public, README **anglais**, licence MIT, démo URL, YouTube ≤ 3 min.

---

## 9. Token Factory et Tavily (détail technique)

**Ne pas commencer ici tant que l’étape 1 n’est pas recettable.**

**Endpoints :** `https://api.tokenfactory.nebius.com/v1/` (Nano / Lightning, eu-north1) · `https://api.tokenfactory.us-central1.nebius.com/v1/` (Super / Ultra).

| Rôle | ID (à revérifier `GET /v1/models?verbose=true`) | Prix / M tok |
|---|---|---|
| Volume / récit | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0,06 / 0,24 |
| Agents rapides | `nvidia/Nemotron-3_5-Lightning` | 0,06 / 0,24 |
| Juge (1× / action) | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1,00 / 3,00 |

Raisonnement ON par défaut → thinking OFF pour JSON / texte court. Parser `content` **et** `reasoning_content`.

**Tavily :** Extract sur l’URL officielle de la ZEE d’abord ; Search allowlist seulement si besoin ; Research **mini** + `files=[leg.json]` si briefing sourcé. **Pas** `include_answer`. Envelope ~13 000 crédits (10k + 3 125).

SearXNG / TinyFish restent le volume **prod BI**. Le simulateur ne les recopie pas.

---

## 10. Vidéo 3 min

Anglais, YouTube public, **bateau qui bouge**. Pas de musique copyright.

| Temps | Plan | Le juge doit lire |
|---|---|---|
| 0:00–0:20 | Problème | Skipper, ZEE, formalités — **pas** un chatbot |
| 0:20–0:45 | Film | Bateau avance (Suivant), entre dans une ZEE, pastilles |
| 0:45–1:20 | Gold + Tavily | Fiche PoE + URL ; timeline Search/Extract ; sources .gouv |
| 1:20–1:55 | Ultra | HUD Ultra us-central1 ; **2 ports barrés** (citation absente) |
| 1:55–2:25 | Sac | JSON `ici()` (1 ZEE, 4 PoE, 1 AMP, vent) — pas 4500 projets |
| 2:25–2:45 | Token Factory | Split ~90 % Lightning / 10 % Ultra, coût |
| 2:45–3:00 | Impact | Route Berry, disclaimer, repo |

Audio : nommer **Nebius Token Factory**, **Nemotron 3 Ultra vs Nano**, **Tavily on this EEZ fiche**.

---

## 11. Soumission Devpost

- Track **Best Apps and Agents** uniquement.  
- Demo URL du simulateur (VPS **séparé** ou preview — **pas** casser naviguide.fr).  
- Repo **public** + licence MIT visible.  
- README EN : install, où est Nemotron, où Token Factory accélère, où Tavily, **delta vs NAVIGUIDE/BI**.  
- Paragraphe « significantly updated / built during submission period ».  
- Feedback Nebius / NVIDIA (Most Valuable Feedback).  
- Matériel en **anglais**.  
- YouTube ≤ 3 min.  
- Testable jusqu’au **15 décembre 2026**.

Check-list anti-disqualification : pas de secrets ; pas de Mongo prod ; attribution VLIZ / OSM ; `NEBIUS_API_KEY` / `TAVILY_API_KEY` hors git.

---

## 12. Recette « on peut gagner »

Un inconnu (juge) doit pouvoir :

1. Ouvrir la démo, reconnaître un **cockpit** (pas une Console).  
2. Avancer le bateau, **voir une ZEE**, des PoE, un lien.  
3. Voir Tavily **sur cette fiche** (sources, pas un slide).  
4. Voir Ultra **contredire** Nano une fois.  
5. Lire dans le README le **sac à dos** (contrat `ici()`).  
6. Relancer le repo avec `.env.example` et deux commandes.

Si l’un manque, on a un beau simulateur, pas encore une soumission gagnante.

---

## 13. Risques qui font perdre

| Risque | Parade |
|---|---|
| Wrapper Nemotron sur NAVIGUIDE tel quel | Dossier neuf + Token Factory au cœur + film |
| 4 chats « en attendant le projet » | Briefing = seul récit |
| Tavily hello-world | Extract de **l’URL Gold** |
| Tout Ultra | HUD split 90/10 |
| Sac = carte entière | `ici()` typé, testé |
| Recoller `:8000` / `:8001` en dur | Backend 8010 + `/bi` optionnel ; export figé |
| Gold massif faux | Statut honnête ; démo sur ZEE vraiment Gold |
| Vidéo de slides | Bateau qui bouge, popup sources |
| Toucher nginx / VPS prod | localhost puis hébergement **dédié** |
| Commencer l’étape 5 avant l’étape 1 | Critère de sortie étape 1 |

---

## 14. Sources

- https://nebiusglobalaihackathon.devpost.com/ · /rules · /resources  
- https://dev.nebius.com/builders · https://docs.tokenfactory.nebius.com/ · https://docs.tavily.com/  
- Code prod (lecture) : `nvidia.py`, `zee_crossings.py`, `poe_pipeline.py`, `naviguide-api/main.py`, `polar_engine.py`, `MapView.js`

---

## 15. Prochaine action

1. **Humain :** Gold (route d’abord) ; `NEBIUS_API_KEY` en env ; Toronto le 29.  
2. **Agent :** créer `naviguide-simulator/` jalon 1.0 (Vite + FastAPI 8010 / 5174), **sans** Tavily ni Nemotron.

Le code de l’étape 1 commence au premier `package.json` dans `naviguide-simulator/`. Le détail d’exécution est [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md). La recette de victoire est le §12 de **ce** fichier.

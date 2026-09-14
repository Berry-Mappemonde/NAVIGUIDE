# Hackathon Nebius × NVIDIA — cahier unique

**Produit :** NAVIGUIDE Simulator — on rejoue Berry-Mappemonde.  
**Track :** Best Apps and Agents  
**Code :** `naviguide-simulator/` (posé, extractible) — **pas** un patch de `www.naviguide.fr`  
**Démo live :** https://simulator.naviguide.fr  
**Date :** 14 septembre 2026 — aligné sur la discussion *Naviguide simulation cockpit*  
**English :** [hackathon-nebius-nvidia.en.md](./hackathon-nebius-nvidia.en.md)

**Chantier cockpit Leaflet (FR) :** [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)

**Deadline soumission :** vendredi 30 octobre 2026, 10:00 PT  
**Jugement :** 1–15 décembre 2026 · résultats vers le 11 janvier 2027  
**IRL :** Builders & Brews **Toronto, mardi 29 septembre 2026** (pas Paris)

Cahier interne, pas une soumission Devpost. Un seul fichier FR pour les orientations **et** le plan pour gagner. Les anciennes copies (Clearance Brief dans `backend/`, 4 chats, ConTree en 2ᵉ repo, MapLibre, `llm_cascade` en prod) sont **annulées**.

---

## 1. Comment on gagne

Les juges vont voir des centaines de chatbots Nemotron. On gagne si, en **20 secondes de vidéo**, ils comprennent :

> Un bateau **glisse** sur une vraie circumnavigation (Play, pas 70 clics). Il entre dans une ZEE. La carte montre les Ports d’entrée **Gold**. Tavily **revérifie cette fiche**, pas le monde. Nemotron Ultra **barre** ce qui n’est plus prouvé. Le récit vient d’un petit dossier « vu du cockpit », pas de la carte entière.

On soumet **un seul produit** : le **simulateur**. Le **mode Simulation** *est* le film. `ici()` prépare le sac. Nano / Lightning **racontent**. Tavily **revérifie la fiche Gold de cette ZEE**. Ultra **barre**. Un Briefing, **pas** 4 chats.

Le méga-briefing éco-tourisme (toutes les couches) est le **même** produit, sérialisé : d’abord le film + le sac + PoE Gold + Tavily/Ultra ; le reste se branche plus tard sur le même Briefing.

| Critère (poids égal) | Notre preuve |
|---|---|
| **Technological Implementation** | Token Factory runtime (pas NIM). Nano / Lightning racontent. Ultra juge. Tavily ancré sur une fiche. |
| **Design** | Un **lecteur** Leaflet (Play / cinéma / 4 vitesses), un briefing, des pastilles. Pas 4 chats, pas la Console BI. |
| **Potential Impact** | Formalités plaisance (ZEE / PoE), expédition Berry-Mappemonde, disclaimer honnête. |
| **Quality of the Idea** | Sac `ici()`, pas un container. Tavily = texte officiel. Stretch : sandbox = preuve géo. Ultra n’est pas sur chaque clic. |

**Prix visés :** Grand Prize (20 000 $) + bonus Tavily (3 000 $). Un seul bonus : on privilégie Tavily plutôt que City (500 $), tout en allant à Toronto.

**NIM (`integrate.api.nvidia.com`) ne compte pas.** Toute l’inférence de soumission passe par Token Factory + au moins un Nemotron.

---

## 2. Trois « modes simulation » — ne pas les confondre

| Objet | Où | Ce que c’est | Soumission ? |
|---|---|---|---|
| **Mode Simulation du simulateur** | `naviguide-simulator/` · [simulator.naviguide.fr](https://simulator.naviguide.fr) | Le **film** : catamaran sur Berry (ou crayon + searoute), Leaflet, un Briefing, pastilles | **Oui — c’est le produit** |
| Mode simulation **NAVIGUIDE prod** | `www.naviguide.fr` · MapLibre · `:9004` | Encore les **4 chats** + chat polar + import GeoJSON | **Non.** On n’y touche pas |
| **7 modes** Blue Intelligence | `blueintelligence.online` | UX opérateur (dont Climatologie atlas) — un mode à la fois | **Non.** Le cockpit allume plusieurs pastilles ensemble |

Le skipper (13–14 sept.) : *« Le projet repose sur ce mode [simulation]. »* Puis : *« je voudrais aussi un mode vitesse réelle avec la vraie vitesse de l’expédition. »*

Ce n’est plus un chat. C’est un **voyage**. La prod `www` garde son ancien mode simulation. Le juge ne doit **pas** ouvrir `www.naviguide.fr` en croyant voir la soumission.

---

## 3. Le film (ce que le juge voit)

1. On **rejoue** l’expédition. **Play** : le bateau **glisse** (pas un téléport à chaque Suivant).  
2. Quatre vitesses : lent · normal · accéléré · **réelle** (polar × vent au point ; défaut 7 kt s’il n’y a pas de vent).  
3. Il **entre dans une ZEE** (polygone Blue Intelligence).  
4. Si elle est **Gold** : Ports d’entrée + lien officiel. Si pas Gold : le briefing le dit — on ne fait pas semblant.  
5. Tavily ne cherche pas le monde : il **revérifie cette fiche**.  
6. Ultra barre ce qui n’est plus prouvé.  
7. Un événement météo / climat : l’agent raconte le bulletin — Copernicus / popup satellite = **chiffres au point**.  
8. Stretch AMP : proximité parc / saison / mouillage.  
9. Stretch sandbox (si prêt) : « vérifié dans un sandbox Nebius ».

Contrôles cibles du mode Simulation :

| Contrôle | Rôle |
|---|---|
| **Mode Simulation** / **Quitter simulation** | Entrer / sortir. Au quit : **le bateau disparaît** |
| Play / Pause | Le film tourne tout seul |
| Précédent / Suivant | Pas à pas (escale ou playhead, **pas** les 1 246 points un par un) |
| Barre d’escales | Sauter (Papeete, Fort-de-France…) |
| Clavier | Espace, flèches, C/E (caméra), 1–4 (vitesse) |
| HUD | FROM → TO, restants, parcourus, durée / ETA, cap |
| Caméra | Suit le bateau **sans** coller au zoom 8 (on garde le tour du monde) |
| Cinéma | Sidebars refermables **sans** perdre Play / clavier |

---

## 4. Le hackathon (règles utiles)

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

## 5. Architecture verrouillée (v3.0 + film)

```
Skipper (cockpit Leaflet, 2 sidebars 320 px)
        │  mode Simulation = lecteur (Play / 4 vitesses)
        ▼
ici(lat, lon)     ← sac (~30 nm), PAS 4500 projets
        │
Événement ?  ──non──►  JSON seul (gratuit)
        │ oui
        ▼
Tavily (cette fiche) → Nano raconte → Ultra juge
        │
        ├─ stretch Data Lab : chaque briefing = un log (après Nano)
        └─ stretch Sandbox : preuve géo (entrée de ZEE)
        ▼
Un Briefing + pastilles sur la carte
```

| Mot | Sens |
|---|---|
| Film | **Lecteur** : Play, glissement, 4 vitesses dont réelle, cinéma, clavier |
| Projecteur | **Leaflet** (fond Esri, comme BI), **plus** MapLibre |
| Titre / logo | « NAVIGUIDE simulator » + logo fourni (plus le monogramme NAVIGUIDE) |
| Légende | Pastilles **plusieurs ON** : ZEE, WPI, Balisage, Projets, Marinas, Capit., PoE, AMP, Climat (aperçu), **Science éclatée** (Sextant, Argo, ODATIS, EDMED, CSR, Bathymétrie, Fonds, Câbles) |
| Moteur bateau | searoute Python + polar (VMG / upload), **sans chat**, **sans** grille 181×61 dans le prompt |
| Moteur situation | `ici()` **avant** tout LLM |
| Le projet | Un récit d’événement (Briefing), pas 4 agents |

### Sac à dos

Rayon ~20–50 nm (cible **30 nm**) + « quelle ZEE contient ce point » :

| Couche | Dans le sac | Pas ça |
|---|---|---|
| ZEE | 1 polygone, nom, `mrgid`, Gold ? | 285 textes |
| PoE | Ports **de cette ZEE**, URL officielle, statut | Tous les PoE |
| AMP / Projets | Près du trait | Le catalogue |
| Marinas / capit. / WPI | 3–5 plus proches | OSM entier |
| Balisage | De la zone | Le monde |
| Science | 0 ou 1 jeu **localisé** (une pastille) | Les 8 catalogues entiers |
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
| Console / Review / Swarm / 7 modes opérateur | UX Blue Intelligence |
| MapLibre / PMTiles « carte marine » | On change de projecteur |
| Recoller `:9000` / `:9004` ou `www…/simulator` | Choc `/route`, polar **avec** chat ; nginx **séparé** |
| ConTree / Sandboxes en **2ᵉ** soumission | Un sandbox **dans** le simulateur = stretch |
| NIM comme cerveau de soumission | Hors règlement |
| Modifier `frontend/`, `backend/`, `naviguide/`, `infra/vps/` nginx www | Prod intouchée |

**Prod `www.naviguide.fr` / `blueintelligence.online` intouchées.** Sous-domaine `simulator.` + service systemd `:8010` à part.

---

## 6. Où ça vit

Le monorepo est **public**, licence MIT (PR #78).

```
Blue-Intelligence-Map/
├── frontend/ backend/ naviguide/   # PROD — on lit, on n’édite pas
├── naviguide-simulator/            # PRODUIT hackathon (Vite 5174, FastAPI 8010)
└── docs/
    ├── hackathon-nebius-nvidia.md                         # ce fichier
    └── PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md  # chantier FR
```

| Où | Rôle |
|---|---|
| `naviguide-simulator/` | Code extractible — **aucune** import `../../frontend` |
| https://simulator.naviguide.fr | Démo VPS (DNS A, certbot, nginx **dédié**, `:8010`) |
| `www.naviguide.fr` | Prod NAVIGUIDE — MapLibre, chats, polar `:9004` |
| Dépôt public dédié (plus tard) | URL Devpost : `git subtree split` ou copie, README EN |

Créer le dépôt dédié à la main (l’agent GitHub est en lecture seule).

---

## 7. Contraintes réelles

### Gold PoE

Tavily s’appuie sur **la carte**, pas l’inverse. Minimum concours : ZEE de la **route Berry** (et de la jambe démo). Ambition skipper : **285** si l’accélérateur garde le critère Gold. Un Gold **faux** est pire qu’un « probable ».

Les 11 polygones déjà Gold restent un **jeu d’éval**. Disclaimer : ne convient pas à la navigation.

Le simulateur **lit** `/bi/export/poe.geojson` (ou un export figé dans `public/`).

### Crédits reçus (13 septembre)

Organisation **Berry-Mappemonde** :

| Service | Observé | Usage |
|---|---|---|
| Token Factory | ~**60 $** ; essai 29 j | Nano / Lightning / Ultra. `NEBIUS_API_KEY` hors git |
| Tavily Researcher | **10 000** + add-on **3 125** | Extract / Search / Research **mini** sur **cette** fiche |
| Toloka / Tendem | 50 $ + 50 $ | Hors soumission |

Discipline : **un Ultra par action visible**. Tavily `mini`. Pas de Search à chaque pas du film.

### Routage prototype

Searoute + polar + vent au point. Pas d’isochrone weather-routing. Draw = crayon + searoute. Route Berry observée : **~39 390 nm**, **35** segments (**34** mer, **1** terre Saint-Maur → La Rochelle), **1 246** points de route — d’où le lecteur, pas 1 246 Suivant.

---

## 8. État du code (14 septembre)

### Simulateur (le produit)

**Fait :** dossier `naviguide-simulator/` ; Leaflet ; Berry + draw ; polar **sans** chat ; 2 sidebars ; titre / logo ; pastilles (Science × 8) ; bouton **Mode Simulation** ; Précédent / Suivant ; drag sur le trait ; popup vent/vague/courant ; FR/EN ; thème ; déployé sur `simulator.naviguide.fr`. `/agents/*` et `/polar/chat` → **404**.

**En cours (discussion cockpit, 14 sept.) :** transformer le mode Simulation en **lecteur** — Play / Pause, glissement, barre d’escales, cinéma, clavier, **4 vitesses dont réelle**. Caméra qui suit sans coller. Cartes d’escale. Masquer le bateau au Quitter.

**Pas commencé :** sac réel `ici()` ; Tavily ; Nemotron ; overlay climat opérateur.

### Audit live (13 sept. soir, avant le lecteur)

Ce qui **empêche** encore de filmer 3 min :

- Suivant **téléporte** (grain = 1 246 points, beaucoup de « Point intermédiaire ») ;  
- caméra collée zoom ~8 — plus de plan monde ;  
- clavier mort ; contrôles **piégés** dans la sidebar gauche ;  
- départ déjà « arrivé » (0 nm restants, bateau à La Rochelle) ;  
- Briefing **ne change pas** ;  
- bateau **reste** après Quitter ;  
- ETA encore **7 kt magiques** alors que le popup vent affiche ~18 kt (vent, pas VMG).

Le **dossier cockpit** à l’écran n’est **pas** le sac `ici()` (pas de ZEE / PoE / `entered_eez`). Ne pas le vendre comme tel.

### Prod (lecture seule)

NIM partout. NAVIGUIDE www : 4 chats, MapLibre, polar **avec** chat. BI : 7ᵉ mode Climatologie atlas. **Soumission ≠ ces README.**

---

## 9. Roadmap jusqu’au 30 octobre

| Étape | Quoi | Hackathon | Qui |
|---|---|---|---|
| **Fait** | Crédits ; Toronto ; cockpit Leaflet étape 1 ; démo `simulator.` ; logo ; Science × 8 | Zéro Nemotron | Les deux |
| **1b** | **Lecteur** : Play, glissement, 4 vitesses (dont **réelle**), clavier, caméra, quit propre | Toujours pas Tavily | Agent — **maintenant** (le projet repose sur ce mode) |
| **2** | Sac réel `ici()` (ZEE, PoE, proches, `entered_eez`) | Toujours pas Tavily | Agent — **après** le film recettable |
| **3** | Gold route Berry, voire 285 | Carburant démo | Humain |
| **4** | Nano raconte le JSON | Token Factory | Agent |
| **5** | Tavily sentinelle de fiche | Bonus 3 000 $ | Agent |
| **6** | Ultra + stretch ; vidéo + dépôt | Soumission | Les deux |
| **29 sept.** | Toronto — **montrer le film** (Play), idéalement sac amorcé | Mentors | Humain |

Ordre skipper (14 sept.) : **le film avant `ici()`**. Un Nemotron sur un album à clics = wrapper. Un Nemotron sur un cockpit sans sac = prompt vide.

### Étape 1 — cockpit (livré, à ne pas recasser)

Détail : [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md).

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
# autre Terminal
npm install && npm run dev   # http://localhost:5174
```

**Backend 8010 :** `/route`, polar upload/get/summary (**pas** `/chat`), proxies, `/wind|/wave|/current`. Pas `/agents/*`.

**On n’ouvre pas** en écriture : `frontend/`, `backend/`, `naviguide/`, nginx de `www`.

### Étape 1b — le lecteur (en cours)

Critère de sortie film : un inconnu appuie **Play**, voit le bateau **glisser** de Saint-Maur vers le large en moins de 20 s, change de vitesse (dont **réelle**), quitte : le bateau **disparaît**. Clavier marche **même** sidebars fermées. Noms d’escales lisibles. Pas 70 Suivant pour atteindre les Antilles.

### Étape 2 — le sac réel (`ici()`)

Serveur **simulateur** : ZEE du point, PoE du `mrgid`, 3–5 points / 30 nm, `entered_eez`. Le Briefing **change**. JSON en clair dans `<details>`.

### Étapes 3–6

Gold (skipper) → Nano raconte → Tavily sur **l’URL de cette ZEE** → Ultra 1× / action. Stretch AMP / Data Lab / sandbox : §11.

---

## 10. Token Factory et Tavily (détail technique)

**Pas avant** film recettable **et** sac non vide.

**Endpoints :** `https://api.tokenfactory.nebius.com/v1/` (Nano / Lightning) · `https://api.tokenfactory.us-central1.nebius.com/v1/` (Ultra).

| Rôle | ID (à revérifier `GET /v1/models?verbose=true`) | Prix / M tok |
|---|---|---|
| Volume / récit | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0,06 / 0,24 |
| Agents rapides | `nvidia/Nemotron-3_5-Lightning` | 0,06 / 0,24 |
| Juge (1× / action) | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1,00 / 3,00 |

Thinking OFF pour JSON / texte court. Parser `content` **et** `reasoning_content`.

**Tavily :** Extract sur l’URL officielle d’abord. **Pas** `include_answer`. Pas un Search à chaque frame du Play.

---

## 11. Stretch Token Factory — Data Lab et Sandboxes (même produit)

Pas une 2ᵉ soumission. Pas de SWE-bench. **Après** que Nano parle.

| Priorité | Stretch | Vidéo 3 min ? | Quand |
|---|---|---|---|
| Film | AMP / projet près du trait | Oui si prêt | Étape 6 |
| Dès Nano | **Data Lab** — mesurer les briefings (ZDR **off**) | Non | Après vrais appels Nano |
| Peut entrer dans le film | **Sandbox** — preuve géo (shapely / `zee_crossings`) | 5–8 s si fluide | Après `ici()` + Nano |
| Plus tard | 2 searoute ; polar « 12 nd → 7 nd ? » | Non | Si le cœur est poli |

Tavily = **texte** officiel. Sandbox = **géométrie**. Fallback honnête : le même script sur `:8010`.

Détail Data Lab / ZDR / branches A·B : inchangé — logs = prompt + JSON `ici()` + Nano + Ultra ; SQL « Ultra a barré un port » ; jeu d’éval = 11 Gold + jambe démo. Docs : https://docs.tokenfactory.nebius.com/data-lab/overview · https://docs.tokenfactory.nebius.com/sandboxes/overview

---

## 12. Vidéo 3 min

Anglais, YouTube public, **Play qui tourne**. Pas 70 clics. Pas de musique copyright.

| Temps | Plan | Le juge doit lire |
|---|---|---|
| 0:00–0:20 | Problème | Skipper, ZEE — **pas** un chatbot |
| 0:20–0:45 | Film | **Play**, bateau qui glisse, vitesse réelle un instant, pastilles |
| 0:45–1:20 | Gold + Tavily | Fiche PoE + URL ; sources .gouv |
| 1:20–1:55 | Ultra | 2 ports barrés (citation absente) |
| 1:55–2:25 | Sac | JSON `ici()` — pas 4500 projets |
| 2:25–2:45 | Token Factory | Split ~90 % Lightning / 10 % Ultra |
| 2:45–3:00 | Impact | Route Berry, disclaimer, `simulator.naviguide.fr` |

Audio : **Nebius Token Factory**, **Nemotron 3 Ultra vs Nano**, **Tavily on this EEZ fiche**.

---

## 13. Soumission Devpost

- Track **Best Apps and Agents** uniquement.  
- Demo URL : **https://simulator.naviguide.fr** (pas `www.naviguide.fr`).  
- Repo public + MIT. README **anglais**.  
- « significantly updated » pendant la période.  
- Testable jusqu’au **15 décembre 2026**.  
- Clés hors git.

---

## 14. Recette « on peut gagner »

1. Ouvrir **simulator.naviguide.fr**, reconnaître un **cockpit** (pas www, pas la Console).  
2. **Play** : le bateau glisse ; on peut passer en **vitesse réelle**.  
3. Voir une ZEE, des PoE, un lien.  
4. Voir Tavily **sur cette fiche**.  
5. Voir Ultra **contredire** Nano une fois.  
6. README : contrat `ici()` + deux commandes locales.

Sans 1–2, on n’a pas de film. Sans 3–5, on n’a pas encore une soumission gagnante. Data Lab / sandbox **hors** de cette liste.

---

## 15. Risques qui font perdre

| Risque | Parade |
|---|---|
| Filmer `www.naviguide.fr` (4 chats) | URL **simulator.** ; delta README |
| 70 Suivant / téléports | Lecteur Play + grain escale |
| Contrôles piégés dans la sidebar | Clavier + barre cinéma |
| Bateau qui reste au Quitter | Masquer le marqueur |
| Wrapper Nemotron sur NAVIGUIDE www | Dossier simulateur + Token Factory |
| 4 chats « en attendant » | Briefing seul |
| Tavily hello-world | Extract de **l’URL Gold** |
| Recoller `:9004` / path `/simulator` | Service `:8010` + nginx dédié |
| `ici()` avant un film recettable | Étape 1b d’abord (ordre skipper) |
| Nemotron avant `ici()` | Prompt vide |
| Gold faux / ZDR on / 2ᵉ repo ConTree | Statut honnête ; ZDR off ; un produit |

---

## 16. Sources

- Discussion *Naviguide simulation cockpit* (13–14 sept. 2026) + audit live `simulator.naviguide.fr`  
- https://nebiusglobalaihackathon.devpost.com/ · https://docs.tokenfactory.nebius.com/ · https://docs.tavily.com/  
- Code : `naviguide-simulator/` ; lecture prod `polar_engine.py`, `zee_crossings.py`, `MapView.js`

---

## 17. Prochaine action

1. **Agent :** finir le **lecteur** du mode Simulation (Play, vitesse réelle, quit propre, clavier) — **sans** Tavily ni Nemotron.  
2. **Humain :** Gold (route d’abord) ; Toronto le 29.  
3. **Ensuite :** sac `ici()`, puis Token Factory.

La recette de victoire est le §14. Data Lab / Sandboxes : §11, **après** Nano.

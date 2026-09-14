# Plan d’implémentation — Simulation B (bateau virtuel live)

Document de chantier pour **`naviguide-simulator/`** uniquement.
Il fige **comment suivre un bateau virtuel daté** et **recalculer une
jambe** : prévision 0–10 j, mode Suivre, isochrone jusqu’à la prochaine
escale. Ce n’est **pas** le film climatologique (A), **pas** un GRIB
mondial, **pas** un isochrone de toute Berry.

Version **1.0** — 14 septembre 2026.

**Prérequis :** [PLAN_IMPLEMENTATION_SIMULATION_A.md](./PLAN_IMPLEMENTATION_SIMULATION_A.md)
recettable (table d’horloge, t0, HUD daté, tests mars / juillet).
**Ne pas commencer B tant que A4 n’est pas vert.**

**English :** pas encore.

**Cahier hackathon (FR) :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

---

## Ce que la 1.0 fige

A dit : « en juin, typiquement, sur le trait searoute ».  
B dit : « si je quitte La Rochelle **demain**, voilà les 10 prochains
jours, et voilà où le bateau **est** mercredi ». Un bouton **Recalculer**
propose un **nouveau trait jusqu’à la prochaine escale**.

| On garde (A) | On ajoute (B) | On refuse |
|---|---|---|
| Table `vertex → date` | `windFn(lat, lon, t)` prévu 10 j | GRIB globe sur le VPS |
| Trait searoute par défaut | Mode Suivre (`now()` = playhead) | Isochrone 39 000 nm |
| Polar uploadée | Recalcul **d’une jambe** | Port 3010 de prod |
| HUD + `kind` | Fantôme Play ≠ marqueur live | VISIR / Windy / SignalK en dep |
| Prod intouchée | Cube couloir + cache 12 h | Vent inventé par un LLM |

---

**Sommaire**

1. En une phrase
2. Pourquoi cette étape existe
3. Contrat skipper (dans / hors)
4. Vocabulaire
5. Décisions d’architecture (verrouillées)
6. Cube de prévision
7. Mode Suivre
8. Recalcul d’itinéraire
9. API simulateur (port 8010)
10. UI / UX
11. Arborescence
12. Ordre de chantier (B0 → B8)
13. Fichiers touchés / interdits
14. Recette
15. Risques
16. Lien A → B
17. Hors périmètre
18. Documents dont ce plan hérite

---

## 1. En une phrase

Faire partir un **bateau virtuel à une date réelle** (ex. demain
08:00 UTC) : pendant ~10 jours il avance avec le vent / courant / vague
**prévus** ; tu le **retrouves** où il doit être en rouvrant l’app ; un
bouton **Recalculer** propose un **nouveau trait** jusqu’à la prochaine
escale (isochrone), sans prétendre connaître Papeete au jour près.

---

## 2. Pourquoi cette étape existe

A est honnête pour **toute** l’expédition (des mois). Elle ne dit pas
le vent de **mardi prochain**.

B est le complément **tactique** : fenêtre 0–10 jours, comme le plan
climatologie l’avait mis **hors V1** de l’atlas (`kind: forecast`, autre
chantier). Ce chantier-ci **est** cet autre chantier, borné au
simulateur.

Sans le mode Suivre, B n’est qu’un film A avec un vent plus frais.
Sans le recalcul, le bateau reste collé au trait searoute même si le
modèle dit de passer plus au sud. Les deux gestes partagent la **même**
table d’horloge que A.

---

## 3. Contrat skipper (dans / hors)

### On livre

En local, puis sur `simulator.naviguide.fr` **si** le cube tient en
mémoire (§14.12) :

1. **Nouveau voyage** : t0 (demain 08:00 UTC possible), polar, route
   Berry ou perso.
2. **10 premiers jours** : nœuds = polaire × **prévision** au point et
   à l’heure. HUD : `kind: forecast`, modèle **nommé**
   (ex. GFS 0,25° / CMEMS ANFC), échéance `+36 h`.
3. **Après J+10** : fondu vers la table A. HUD : `kind: climatology`.
   Jamais un GFS inventé pour novembre.
4. **Mode Suivre** : horloge **murale** = horloge mer. Fermer l’ordi,
   revenir 2 jours après : le bateau a avancé de 2 jours (si t0 est
   passé). Si t0 est dans le futur : bateau **à quai** jusqu’à t0.
5. **Play** en mode Suivre = **aperçu** (fantôme) : on peut scruber le
   futur sans déplacer le bateau live. Bouton / touche `L` :
   « Revenir au live ».
6. **Recalculer l’itinéraire** : de la position live → **prochaine
   escale à drapeau** seulement. Isochrone 6 h, vent prévu puis
   climatologie. Aperçu (trait neuf + ancien searoute en pointillés) →
   Accepter / Refuser.
7. Recalcul **refusé par défaut** sur toute la circumnavigation d’un
   coup.
8. Disclaimer double : prévision 0–10 j / climatologie ensuite / ne
   convient pas à la navigation.

Cube down : le voyage reste en **A seul** + bandeau « prévision
indisponible, climatologie ». Le film ne devient pas noir.

### On ne livre pas

| Interdit en B | Pourquoi |
|---|---|
| GRIB mondial sur le VPS | 8 Go, plan climatologie |
| Isochrone 39 000 nm | Mensonger + injouable |
| VISIR-2, plugin Windy, SignalK en dépendance | On copie l’algo, pas les dépôts |
| Brancher le port 3010 de prod | Pas déployé ; autre polar singleton |
| Import GRIB skipper (Saildocs) en v1 | Le serveur découpe le couloir |
| `best_match` Open-Meteo sans nommer le modèle | Loi climatologie |
| Chat météo qui invente un vent | `climatology.no_llm_for_numbers` |
| Modifier `www` / Blue Intelligence | Prod intouchée |
| AIS / Iridium du vrai catamaran | Autre produit |
| Tavily / Nemotron | Autre étape hackathon |

---

## 4. Vocabulaire

| Mot | Sens ici |
|---|---|
| **Voyage** | Instance : `voyageId`, t0, polar, route, révision |
| **Live** | Position = table d’horloge à `now()` (UTC) |
| **Aperçu / fantôme** | Play ou scrub **sans** bouger le live |
| **Couloir** | Buffer ~200 nm autour des ~1 500 nm **devant** le bateau, 10 j, pas 3 h |
| **Cube** | Vent + vague + courant avec un axe **temps** |
| **Fondu** | Entre J+7 et J+10, mélange prévision → climatologie |
| **Recalcul** | Nouvelle géométrie **d’une jambe**, puis on **rejoue** A/B sur ce trait |
| **Révision** | `routeRev` : searoute v0, isochrone v1, v2… |
| **kind** | `"forecast"` ou `"climatology"` sur chaque pas / vertex |

---

## 5. Décisions d’architecture (verrouillées)

### 5.1 B étend A, il ne le remplace pas

Même schéma JSON que A §7. On lui passe `windFn(lat, lon, t)` :

| Quand | Vent |
|---|---|
| `t < t0 + 7 j` | Cube prévision |
| `t` dans `[t0+7 j, t0+10 j]` | Mélange linéaire (vent ou nœuds) |
| `t > t0 + 10 j` | `zoneWindAt` / atlas (A) |

Le Play, la barre, le sillage, `ici()` ne changent pas de contrat.

Le JS `voyageClock.js` **reste** pour A et pour l’aperçu hors ligne
(climo seule). Dès qu’un cube existe, la table **officielle** du voyage
live = réponse serveur (même schéma).

### 5.2 Cube : pas de GRIB globe

**v1 B, pragmatique** (compte Copernicus déjà dans `simulator.env`) :

| Champ | Produit | Ce qu’on change |
|---|---|---|
| Vague | `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i` | Ouvrir `valid_time` de t0 à t0+10 j, **couloir**, plus `time=-1` |
| Courant | `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` | Idem, sous-échantillon 3 h |
| Vent 10 m | Open-Meteo Marine **GFS** (modèle **nommé**) | Le NRT L4 (`getWind.py`) = hier, **interdit** pour B |

**B-alt** (plus tard, pas v1) : GFS GRIB2 NOMADS découpé **hors**
requête live, pipeline type snapshots climo, jamais un `wget` globe au
Play.

Cache disque `server/forecast_cache/{voyageId}/` (gitignore), une
grille petite, TTL 6–12 h. Relancer un fetch en mode Suivre si le
cache a plus de 12 h (nouveau run 00/12 UTC).

### 5.3 Mode Suivre = persistance

Un voyage vit plus longtemps qu’un onglet.

- `localStorage` clé `naviguide_sim_voyage_v1` : `voyageId`, t0,
  routeKind, routeRev, hash isochrone accepté.
- Serveur : `server/voyage_data/voyage_{id}.json` (même esprit que
  `polar_data/`) pour retrouver le bateau sur un autre navigateur /
  après publish.

Position live **calculée**, pas stockée toutes les minutes :

```
position = table.at(now)
```

On persiste t0 + révision de route + polar id.

| Horloge murale | Bateau |
|---|---|
| `now < t0` | À quai, HUD « appareillage dans … » |
| `t0 ≤ now ≤ fin de table` | Live sur le trait |
| `now` après la fin | Arrivée (ou fin d’expédition) |

### 5.4 Play ≠ Live

| Contrôle | Effet |
|---|---|
| Mode Suivre ON | Marqueur **live** (plein). Horloge murale |
| Play / scrub | Marqueur **fantôme** (contour). Le live **reste** |
| « Revenir au live » / `L` | Caméra + HUD sur `now` |
| Quitter Suivre | Retour film A (table figée, plus d’horloge murale) |

On ne laisse pas Play **déplacer** le bateau live.

### 5.5 Recalcul = une jambe, pas le monde

```
position live → prochaine escale à drapeau
horizon 10 j prévision, puis climatologie jusqu’à CETTE escale
pas de temps 6 h, cap 10°, max ~120 pas
```

Si l’isochrone n’atteint pas l’escale : on **épisse** le meilleur
point sur le **searoute restant** de cette jambe. Statut `spliced`.

Le reste de Berry (escales suivantes) : **searoute inchangé**. On
**recrée seulement l’horloge** à partir de la nouvelle heure
d’arrivée.

Ancien trait : pointillés, pane en dessous. Nouveau : trait plein.
Enveloppes isochrones : **off** par défaut (toggle).

Recalcul **désactivé** en phase air / relais (`filmCast` avion ou
`side`). A gère le cast.

### 5.6 Copier l’isochrone, ne pas appeler la prod

`naviguide/naviguide_workspace/naviguide_weather_routing/` : polar
**singleton** Berry, vent **zones**, port 3010 **absent** en prod.

Dans le simulateur :

- copier `isochrone.py` (propagate / prune / land mask) vers
  `naviguide-simulator/server/isochrone.py` ;
- injecter `wind_fn`, `current_fn`, `wave_nogo_fn` ;
- `polar` = polaire **uploadée** (Leopard 46 ou fichier skipper) ;
- `kind` sur chaque pas : `forecast` ou `climatology`.

**Pas** d’`import` depuis `../../naviguide/`. Le dossier simulateur
reste extractible.

### 5.7 Vagues = frein, pas le nœud

`climatology.wave_nogo_m` = 2,5 m
([REGLES_PARAMETRES.md](./REGLES_PARAMETRES.md) §3.6).

- En climo : P90 (quand l’atlas BI existe ; sinon pas de no-go vague
  en v1).
- En prévision : Hs du cube.

Si no-go : le pas isochrone est **jeté**. Sur polyline fixe (sans
recalcul), `dt` × 3 ou capeye 6 h (une constante, testée). On
n’invente pas une polaire de mer formée.

### 5.8 Zéro LLM

B est du vent chiffré. Pas de Nemotron, pas de Tavily, pas de chat
météo.

### 5.9 Création asynchrone

`POST /voyage` répond tout de suite (table A, `forecast: pending`).
Le cube se remplit en fond. `GET /voyage/{id}` passe à `ready`.
L’UI montre un bandeau, jamais un spinner bloquant de 30 s.

---

## 6. Cube de prévision

### Découpe

À la création / au refresh :

1. Prendre ~1 500 nm de route **devant** le live (ou depuis t0 si
   encore à quai).
2. Buffer ~200 nm → bbox (gérer l’antiméridien : deux rectangles si
   besoin).
3. Fenêtre `t0 … t0+10 j` (ou `now … now+10 j` au refresh).
4. Variables : vent 10 m `u/v` (ou force + dir), Hs, courant surface
   `uo/vo`.
5. Écrire le cache. Si trop gros : réduire le couloir, **pas** passer
   au globe.

### Interpolation

`cube.at(lat, lon, t)` : plus proche voisin ou bilinéaire spatial +
linéaire temporel. Terre / NaN → `null` → repli A (zone) **et**
`kind` reste honnête (`climatology` + `reason: "no_forecast_cell"`).

### Mémoire

Objectif : cube d’un voyage **< 80 Mo**. Test de recette. Le VPS a
`MemoryMax=1G` pour `naviguide-simulator`.

---

## 7. Mode Suivre

### Persistance

```js
{
  voyageId, t0, expedition_id,
  routeKind, routeRev,
  follow: true,
  forecastStatus: "pending" | "ready" | "unavailable",
}
```

### Horloge

`GET /voyage/{id}/at?t=` (défaut `now`). Le front n’intègre pas le
cube. Il affiche la position renvoyée.

Un tick local (1/min, ou à la reprise de focus) suffit. Pas de rAF
pour le live.

### Deux marqueurs

- Live : `useCatamaranMarker` plein, `draggable: false` en Suivre
  (le drag casserait `now()`).
- Fantôme : second marqueur contour, seulement si Play / scrub ≠ live.

Caméra : suit le **fantôme** pendant l’aperçu, le **live** sinon.
`useFilmCamera` déjà là : lui passer l’acteur actif.

---

## 8. Recalcul d’itinéraire

### Entrée

```
from = position live
to   = prochaine escale à drapeau (ou to_name)
t    = now
polar = upload
wind_fn / current_fn / wave_nogo_fn = blend §5.1
time_step_h = 6
heading_step_deg = 10
max_steps = 120
arrival_radius_nm = 50
```

### Sortie

```js
{
  status: "arrived" | "spliced" | "failed",
  kind_mix: ["forecast", "climatology"],
  draft_geojson,
  hours, distance_nm,
  versus_searoute: { hours, distance_nm },
}
```

### Acceptation

1. Remplacer la jambe courante par `draft_geojson`.
2. Incrémenter `routeRev`.
3. Reconstruire la table d’horloge **depuis** la nouvelle arrivée
   (aval = searoute A/B).
4. L’amont (déjà parcouru) ne bouge pas.

Refus : rien. Le brouillon expire (ou `GET /draft` le renvoie tant
qu’on n’a pas accepté).

---

## 9. API simulateur (port 8010)

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/voyage` | Crée : t0, `expedition_id`, route, `follow` |
| GET | `/voyage/{id}` | Métadonnées + `routeRev` + `forecastStatus` |
| GET | `/voyage/{id}/clock` | Table d’horloge (schéma A) |
| GET | `/voyage/{id}/at?t=` | Position live / à `t` (défaut `now`) |
| POST | `/voyage/{id}/refresh-forecast` | Recharge le couloir (12 h) |
| POST | `/voyage/{id}/recompute` | Isochrone → jambe candidate |
| GET | `/voyage/{id}/draft` | Trait proposé + status |
| POST | `/voyage/{id}/accept` | Applique la révision |
| POST | `/voyage/{id}/reject` | Jette le brouillon |

`POST /wind|/wave|/current` **inchangés** (NRT clic). Autre `kind`.

Pas de `/agents/*`. Pas de `/api/v1/polar/chat`.

---

## 10. UI / UX

### Création

Champs A + case « Bateau virtuel (prévision 10 j) » + « Mode Suivre ».

Si Suivre et t0 dans le futur : *Le bateau n’appareille pas avant …*.

### HUD live

Date **now**, nœuds, modèle nommé, échéance, `forecast` ou
`climatology`. Pastille verte **LIVE** vs grise **aperçu**.

### Recalculer

Bouton dans `SimulationPanel` seulement si :

- Suivre ON ;
- véhicule = bateau (pas avion, pas relais) ;
- `forecastStatus !== "pending"` (ou climo seule, avec bandeau).

Spinner. Dialog : nm et heures searoute vs proposé, carte double
trait. Accepter / Garder searoute.

### Clavier

`L` = revenir au live. **Pas** de raccourci pour Recalculer
(trop facile à lancer par erreur).

---

## 11. Arborescence

```
naviguide-simulator/server/
  voyage_api.py              # routes §9
  voyage_store.py            # voyage_data/*.json
  forecast_cube.py           # couloir CMEMS + vent nommé
  forecast_blend.py          # wind_fn(t)
  isochrone.py               # copie adaptée (pas d’import prod)
  voyage_clock.py            # même algo que le JS A, côté serveur
  voyage_data/               # gitignore
  forecast_cache/            # gitignore
  tests/test_voyage_clock.py
  tests/test_forecast_blend.py
  tests/test_isochrone_leg.py
src/hooks/useVirtualVessel.js
src/components/FollowToggle.jsx
src/components/RecomputeDialog.jsx
src/layers/useAltRouteLayer.js
src/i18n/fr.js
src/i18n/en.js
```

---

## 12. Ordre de chantier (B0 → B8)

| # | Quoi | Critère de sortie |
|---|---|---|
| **B0** | Contrat JSON table A = table serveur | Un test golden partagé |
| **B1** | `forecast_cube` couloir + cache, **sans** isochrone | 1 point, t0+36 h, vent ≠ zone juin |
| **B2** | `wind_fn` + clock serveur | 10 j forecast, j11 = climo |
| **B3** | `GET /at?t=now` + `useVirtualVessel` + pastille LIVE | F5 : même position |
| **B4** | Play = fantôme, `L` = live | Deux marqueurs, un seul « vrai » |
| **B5** | Copie isochrone + `wind_fn` + polar upload | Test jambe courte (mock cube OK) |
| **B6** | `recompute` + dialog + accept/reject + pointillés | Géométrie d’**une** jambe |
| **B7** | Refresh cube 12 h en Suivre | Après refresh, live peut bouger |
| **B8** | Recette + mémoire cube < 80 Mo + disclaimer | §14 au vert |

Ne pas ouvrir B5 si B3 ne survit pas à un F5.  
Ne pas isochrone toute Berry « pour voir ».

---

## 13. Fichiers touchés / interdits

**Oui :** `naviguide-simulator/server/**` (nouveaux modules + tests),
`naviguide-simulator/src/**` (hooks / UI B), i18n,
`server/.gitignore` (`voyage_data/`, `forecast_cache/`).

**Copie ponctuelle :** `isochrone.py` (et helpers land mask /
bathymetry **si** indispensables), recopiés et adaptés. Ensuite plus
de lien.

**Non :**

- `naviguide/` en import runtime, `www`, nginx skipper
- `frontend/`, `backend/` (sauf **lire** un snapshot climo déjà
  publié, en GET)
- Déployer le port 3010
- `getWind.py` comme source B (NRT 48 h)
- `infra/vps/` sauf, **plus tard**, variables Copernicus déjà prévues
  dans `simulator.env`

---

## 14. Recette

### Live

1. t0 = **demain 08:00 UTC**, La Rochelle, Leopard 46, Suivre ON.
2. Aujourd’hui : bateau à quai, compte à rebours.
3. Recette accélérée : t0 = **il y a 36 h**. Position **au large**,
   HUD `forecast`, modèle nommé, échéance.
4. F5 : même lat/lon ± 1 nm.
5. Play : fantôme avance, live **immobile**. `L` : retour live.
6. Test auto : `GET /at?t=t0+48h` (pas besoin de bouger l’horloge
   système).

### Fondu

7. `GET /at?t=t0+11j` : `kind: climatology`. Plus d’échéance GFS.

### Recalcul

8. Depuis une position Atlantique, Recalculer → Fort-de-France.
   Trait proposé ≠ searoute (souvent). Status `arrived` ou `spliced`.
9. Refuser : searoute inchangé.
10. Accepter : trait plein = isochrone, searoute en pointillés,
    horloge **après** Fort-de-France recalé, le Pacifique **pas**
    recalculé.
11. Cube down : bandeau + A. Pas de vent LLM.

### Mémoire

12. Processus serveur : cube < ~80 Mo. Sinon réduire le couloir.

---

## 15. Risques

| Risque | Parade |
|---|---|
| « Arrivée Papeete le 3 novembre » issue du GFS | j>10 = climo ; HUD l’écrit |
| VPS OOM | Couloir + cache ; jamais GRIB global |
| Deux moteurs de polar (3010 vs upload) | Un seul : celui du simulateur |
| Isochrone à travers une terre | Land mask de la copie ; tests Ibérie / Maroc |
| Live + Play qui se battent | Fantôme vs plein, §5.4 |
| CMEMS lent au POST /voyage | Async, `forecast: pending` |
| Relais Halifax pendant un live | Recalcul off en air / side |
| Licence ECMWF | IFS hors v1 ; GFS ou CMEMS **nommés** |
| Cube qui expire pendant Suivre | Refresh 12 h, bandeau si `unavailable` |

---

## 16. Lien A → B

```
A : trait fixe + vent(mois)      → table (vertex → date)
B : même table + vent(lat,lon,t) → 10 j prévision, puis A
    + now() comme playhead         → Suivre
    + isochrone(jambe)             → nouveau trait, puis table à nouveau
```

| Question skipper | Plan |
|---|---|
| On part le 15 juin, toute Berry, ETA selon la saison | **A** |
| On part demain, je le retrouve mercredi | **B Suivre** |
| Le GFS dit de passer plus au sud jusqu’aux Antilles | **B Recalcul** |
| Toute la mappemonde recalculée chaque matin | **Personne** — hors contrat |

Deux merge requests séparées. Pas de PR unique « A+B ».

---

## 17. Hors périmètre

- VISIR-2, CO₂, voyage plan scientifique.
- Historical Sea Routing comme **remplacement** de searoute (autre
  géométrie mensuelle permanente) : seulement si un jour on veut
  « quel mois, quelle route » **sans** prévision. Ni A ni B.
- Replay AIS du vrai bateau.
- Overlay GRIB opérateur sur toutes les couches.
- Auto-hébergement Open-Meteo, ingestion NOMADS globe.
- Écriture dans `naviguide.fr` / Blue Intelligence.
- 8ᵉ pastille « Climatologie » dans le simulateur.

---

## 18. Documents dont ce plan hérite

- [PLAN_IMPLEMENTATION_SIMULATION_A.md](./PLAN_IMPLEMENTATION_SIMULATION_A.md)
  — horloge, t0, schéma JSON, polar `raw`.
- [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)
  — film, exclusions, prod intouchée.
- [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md)
  §4, §21 — prévision 0–10 j = autre `kind`, hors V1 atlas ; **ce**
  chantier.
- [REGLES_PARAMETRES.md](./REGLES_PARAMETRES.md) §3.6 —
  `wave_nogo_m`, `no_llm_for_numbers`, `avoid_cyclone_tracks`.
- Code à **copier** (pas importer) :
  `naviguide/naviguide_workspace/naviguide_weather_routing/isochrone.py`.
- Code à **étendre** : `naviguide-simulator/server/copernicus/getWave.py`,
  `getCurrent.py` (idée `valid_time`, pas fusion NRT / forecast dans
  le même endpoint clic).

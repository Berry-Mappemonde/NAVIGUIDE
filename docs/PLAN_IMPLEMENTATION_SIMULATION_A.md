# Plan d’implémentation — Simulation A (horloge climatologique)

Document de chantier pour **`naviguide-simulator/`** uniquement.
Il fige **comment dater le film** : même trait searoute, vent typique du
mois, barre en jours de mer. Ce n’est **pas** une prévision, **pas** un
bateau live, **pas** un recalcul d’itinéraire.

Version **1.0** — 14 septembre 2026.

**Suite (interdit tant que A n’est pas recettable) :**
[PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md)
(bateau virtuel, mode Suivre, isochrone d’une jambe).

**English :** pas encore. Le film étape 1 reste
[PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md).

**Cahier hackathon (FR) :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

---

## Ce que la 1.0 fige

Le mode Simulation a déjà un **lecteur** (Play, 4 vitesses d’écran,
playhead en nm, stations 1,4 s, relais Halifax, cinéma). Il n’a pas
d’horloge civile. On ne peut pas dire « on part le 15 juin ».

A ajoute **seulement** ça :

| On garde | On ajoute | On refuse |
|---|---|---|
| Trait searoute (Berry ou crayon) | Date de départ `t0` | GRIB / GFS / IFS |
| Play / Pause / scrub en nm | Table `vertex → date` | Isochrones, port 3010 |
| Polaire moteur (sans chat) | Nœuds = polar × vent **du mois** | Poll Copernicus 25 s pour l’ETA |
| Film air / relais (`filmCast`) | Jours à quai calendaires | « Arrivée mardi 14 h » |
| Leaflet, prod intouchée | HUD daté + `kind: climatology` | Modifier `www` / BI |

---

**Sommaire**

1. En une phrase
2. Pourquoi cette étape existe
3. Contrat skipper (dans / hors)
4. Vocabulaire
5. Décisions d’architecture (verrouillées)
6. État du code (déjà là / à brancher / à écrire)
7. Table d’horloge
8. Polar : câbler le `raw`
9. UI / UX
10. Arborescence
11. Ordre de chantier (A0 → A6)
12. Fichiers touchés / interdits
13. Recette
14. Risques
15. Passage à la simulation B
16. Documents dont ce plan hérite

---

## 1. En une phrase

Donner au mode Simulation une **date de départ** et une **horloge en
jours de mer** : le bateau reste sur le trait searoute, avance à la
polaire × vent **typique du mois** à cet endroit, et l’ETA d’une jambe
**change** si on part en mars plutôt qu’en juillet.

---

## 2. Pourquoi cette étape existe

Aujourd’hui Play est un **film** : milles, 4 vitesses d’écran, nœud de
croisière (VMG moyen) ou vent d’hier toutes les 25 s. On ne peut pas
dire « on part le 15 juin ».

Berry-Mappemonde dure des mois (~39 390 nm). Un modèle de prévision
(GFS, IFS) n’est honnête que **7 à 10 jours**. La seule simulation
honnête de **toute** l’expédition, c’est la climatologie : « en juin,
ici, on a plutôt tel régime ».

Sans A, la simulation B n’a ni calendrier, ni table de temps, ni HUD
daté. Brancher un GRIB avant cette horloge, c’est animer du vent sur
un film qui ne sait pas quel jour on est.

---

## 3. Contrat skipper (dans / hors)

### On livre

En local (`http://localhost:5174`), mode Simulation ON :

1. Un champ **Date de départ** (jour + mois + heure UTC). Défaut :
   **1er juin 08:00 UTC**, départ mer = **La Rochelle**.
2. À **Play**, le bateau glisse toujours. La barre montre les **nm**,
   les **jours de mer** et la **date civile**
   (ex. `j18 · 3 juillet 14:00 UTC`).
3. Le HUD affiche les nœuds **locaux** (polaire × vent du mois), le
   TWA, et `kind: climatology`. L’ETA de la jambe **n’est plus**
   `nm / 7`.
4. Changer le départ de **15 mars** à **15 juillet** recalcule
   l’horloge : Fort-de-France n’a plus la même date d’arrivée.
5. Aux escales à drapeau : **jours à quai** (calendrier), plus
   seulement la pause 1,4 s du film.
6. Sillage + liste d’escales cliquable (composants déjà écrits, à
   monter).
7. Bandeau : *Vent typique du mois, pas la météo de demain.*

Si searoute est down : même horloge sur `public/route.geojson`.

### On ne livre pas

| Interdit en A | Pourquoi |
|---|---|
| Fichiers GRIB, GFS, IFS, Open-Meteo | C’est B |
| Isochrones, port 3010, nouveau trait | C’est B « recalcul » |
| Horloge murale = horloge mer (« je reviens mercredi ») | C’est B « Suivre » |
| Chat polar, 4 agents, import GeoJSON | Déjà exclus du simulateur |
| Grille polaire 181×61 dans le navigateur | Seulement le tableau brut |
| Modifier `naviguide/`, `frontend/`, `www` | Prod intouchée |
| Prétendre une arrivée « le mardi 14 h » | Interdit par le plan climatologie |
| Courant / houle P90 dans l’intégrateur | A+ (après l’atlas BI), pas A.0 |

La prod (`www.naviguide.fr`, `blueintelligence.online`) ne change pas.

---

## 4. Vocabulaire

| Mot | Sens ici |
|---|---|
| **Film** | Play / Pause / scrub déjà là (nm film, avions, relais Halifax) |
| **Horloge civile** | Date et heure UTC du bateau virtuel |
| **t0** | Instant de départ **mer** (La Rochelle par défaut) |
| **Table d’horloge** | Chaque vertex : `filmNm`, `lat/lon`, `tHours` depuis t0, `datetime`, nœuds, vent, `kind` |
| **Jours de mer** | Heures de route **hors** escales, hors avion |
| **Jours à quai** | Pause calendaire à une escale à drapeau |
| **Vent de mois** | Atlas / zones, `kind: climatology`. Pas Copernicus NRT |
| **Intégrateur** | `dt = nm / nœuds_fond` le long du trait **fixe** |
| **kind** | Étiquette obligatoire. En A : toujours `"climatology"` |

---

## 5. Décisions d’architecture (verrouillées)

### 5.1 Même polyline

Le trait reste searoute (Berry ou « draw your own »). A **ne
redessine pas** la route. Seule l’horloge bouge.

### 5.2 Départ mer = La Rochelle

Saint-Maur → La Rochelle : terre, hors intégrateur polaire.

- Défaut : `t0` = première escale maritime (La Rochelle).
- Option : « depuis Saint-Maur » → un `dt` fixe (ex. 4 h), **sans**
  polaire.

Avion Cayenne ↔ Halifax : durée **calendaire** fixe
(`AIR_CALENDAR_HOURS` = 8), pas la polaire.

Relais Halifax ↔ Saint-Pierre : même table, véhicule `side`, vent du
mois sur **ce** trait.

### 5.3 Vent = climatologie, polaire = brute

- Vent : `zoneWindAt` dans
  `naviguide-simulator/src/utils/climatologyWind.js` (copie de
  `climatology.py`). Plus tard, même API atlas que Blue Intelligence
  **si** elle répond ; sinon zones. Toujours `kind: climatology`.
- Vitesse : `polarBoatSpeed` sur le tableau **brut** (~20×15). Pas
  d’appel `POST /wind` toutes les 25 s pour l’horloge A.
- Courant / houle P90 : **hors A.0**. Vitesse = polaire × vent
  seulement.

### 5.4 Une table, deux scrubbers

`playback.nm` reste la source du film (caméra, sillage, `ici()`,
stations 1,4 s).

La table donne `filmNm → datetime`. Un clic sur la barre = seek en nm
(comme aujourd’hui). La date affichée **suit**. Une graduation « jours »
en plus des nm est optionnelle (A+, pas A.0).

Les 4 profils Play (réelle / lecture / normale / rapide) restent des
**vitesses d’écran**. Ils ne calculent pas l’horloge civile.

En A, le profil « réelle » (1 s écran = 1 s mer) n’est **pas** le
défaut : inutile sur 200 jours de mer. Il sert d’aperçu sur **une**
jambe.

### 5.5 Jours à quai

Table par défaut (pas un import fichier) :

| Escale | Jours à quai |
|---|---|
| La Rochelle | 3 |
| Autres escales à drapeau | 2 |
| Relais Halifax (hub) | 1 |
| Saint-Maur | 0 |

Pendant un quai : `datetime` avance, `filmNm` ne bouge pas, HUD
« à quai ». La pause film 1,4 s (`STATION_HOLD_MS`) **reste** pour le
Play accéléré : ce n’est pas le même objet que les jours à quai.

### 5.6 Où ça tourne

Calcul de la table **côté client** (vent de zone + polaire brute =
synchrone, ~1 246 points). Pas de nouvel uvicorn. Le serveur polar
sert déjà `GET /api/v1/polar/{id}` avec `raw`.

### 5.7 Deux `kind` qui ne se mélangent pas

Le clic carte `POST /wind|/wave|/current` reste NRT / ANFC (vent
d’hier). Il **n’alimente pas** l’horloge A. Le HUD du film dit
climatologie. Le popup du clic dit observation récente. Deux phrases,
deux `kind`.

---

## 6. État du code (déjà là / à brancher / à écrire)

### Déjà dans le film (ne pas réécrire)

| Pièce | Fichier |
|---|---|
| Playhead nm + stations | `src/engine/routePlayhead.js`, `src/hooks/useRoutePlayback.js` |
| 4 vitesses d’écran | `src/engine/playSpeeds.js` |
| Acteurs Berry / avion / relais | `src/engine/filmCast.js` |
| Barre + pastilles | `src/components/SimulationFilmBar.jsx` |
| Rotation catamaran | `src/components/CatamaranMarker.jsx` |
| Polaire serveur | `server/polar_engine.py`, `server/polar_api.py` |
| Vent de zone | `src/utils/climatologyWind.js` |
| Polar × vent au point | `src/engine/alongTrackSpeed.js`, `src/engine/polarSpeed.js` |

### Écrit, pas monté (à brancher en A0 / A1)

| Pièce | Fichier | Manque |
|---|---|---|
| Sillage | `src/engine/filmWake.js`, `src/layers/useWakeLayer.js` | appel dans `App.jsx` |
| Liste d’escales | `src/components/EscaleLegend.jsx` | montage dans `Sidebar.jsx` + clés i18n |
| `alongTrackSpeed` | `src/engine/alongTrackSpeed.js` | personne ne l’appelle |
| Polar `raw` | `GET /api/v1/polar/{id}` | `ToolsSidebar` ne garde que `vmg_summary` |

### À écrire

`voyageClock.js`, `useVoyageClock.js`, `DepartureField.jsx`, et la
colle HUD / barre.

---

## 7. Table d’horloge

### Entrée

- `flat` (`flattenRoute`) + `marks` (escales) ;
- `t0` ISO UTC ;
- `polarRaw` ou `null` (alors `boatSpeedFromWind`) ;
- `portDays` ;
- `startAt` = `"la-rochelle"` | `"saint-maur"`.

### Intégrateur (arête mer)

```
month = monthOf(t0 + tHours)
wind  = zoneWindAt(lat, lon, month)
knots = alongTrackSpeed({ lat, lon, bearing, month, polarRaw }).speedKnots
dt    = spanNm / max(knots, 0.5)     # heures ; plancher 0,5 kn
tHours += dt
```

Arête air (`jump`) : `tHours += AIR_CALENDAR_HOURS` (8).  
Quai : au franchissement d’un mark, `tHours += portDays * 24`.

### Sortie (JSON interne, contrat B aussi)

```js
{
  t0,
  kind: "climatology",
  vertices: [
    {
      filmNm, sailNm, lat, lon, bearing,
      tHours, iso, speedKnots, windKnots, twa, month, vehicle,
    },
  ],
  marks: [{ name, filmNm, tHours, iso, holdHours }],
  seaHours, quayHours, arrivalIso,
}
```

Recalcul si : route, polar, t0, portDays ou startAt changent.
**Une fois**, pas à chaque frame.

### Tests unitaires (sans navigateur)

- Mars vs juillet, même nm : `arrivalIso` Fort-de-France **différent**.
- t0 = 15 juin 08:00, départ La Rochelle → date Fort-de-France > 15 juin.
- Quai 2 j : trou de 48 h dans `iso` à `filmNm` constant.
- Hop aérien : +8 h, `speedKnots` null.
- Sans polar : source `climatology`, pas de crash.
- Antiméridien : `tHours` monotone.
- `startAt: "saint-maur"` : premier `dt` sans polaire.

---

## 8. Polar : câbler le `raw`

Aujourd’hui `ToolsSidebar.jsx` ne garde que `vmg_summary`.

Après upload / chargement auto Leopard 46 :

1. `GET /api/v1/polar/{expedition_id}` ;
2. garder `raw: { twa_rows, tws_cols, matrix }` ;
3. **ne pas** garder `grid` (181×61).

`useExpeditionSpeed` (poll 25 s Copernicus + `GET …/speed`) : **couper**
dès que la table d’horloge existe. Sinon deux nœuds à l’écran
(croisière / NRT vs table).

Le tableau VMG de la sidebar droite reste le **moteur bateau** (upload,
résumé). Le film n’a besoin que d’un nombre de nœuds à **cette**
position.

---

## 9. UI / UX

### Sidebar gauche (simulation ON)

- `DepartureField` : date, heure UTC, sélecteur
  « Départ mer : La Rochelle | Saint-Maur ».
- Sous `SimulationPanel` : `EscaleLegend` (clic = `seek`).
- HUD : nœuds locaux, date civile, `climatologie · juin` — plus
  `@ 7 kt` tout seul.

### Barre bas

Remplir déjà parcouru + pastilles d’escales (déjà là). Sous-titre :

`4 210 nm · j18 · 3 juil. 14:00 UTC`

Scrub = nm, comme aujourd’hui.

### Carte

`useWakeLayer(mapRef, { flat, sailNm: cast.sailNm, enabled: simulationMode })`.
Pas de nouvelle couche « atlas » obligatoire (le plan climatologie :
invisible dans NAVIGUIDE).

### Disclaimer

Visible dès que A est ON, une ligne, FR/EN.

---

## 10. Arborescence

Tout dans `naviguide-simulator/` :

```
src/engine/voyageClock.js             # NOUVEAU — construit la table
src/engine/voyageClock.test.js
src/engine/alongTrackSpeed.js         # déjà là — brancher
src/engine/polarSpeed.js              # déjà là
src/utils/climatologyWind.js          # déjà là
src/hooks/useVoyageClock.js           # NOUVEAU — t0, table, seek
src/components/DepartureField.jsx     # NOUVEAU
src/components/SimulationFilmBar.jsx  # dates + jours
src/components/SimulationPanel.jsx    # nœuds locaux + kind
src/components/EscaleLegend.jsx       # déjà là — monter
src/layers/useWakeLayer.js            # déjà là — appeler
src/components/ToolsSidebar.jsx       # garder polar.raw
src/components/Sidebar.jsx            # DepartureField + légende
src/App.jsx                           # colle
src/i18n/fr.js
src/i18n/en.js
```

**Pas** d’import runtime depuis `../../naviguide/` ni
`../../frontend/`. On ne copie **pas** `isochrone.py` en A.

---

## 11. Ordre de chantier (A0 → A6)

| # | Quoi | Critère de sortie |
|---|---|---|
| **A0** | Brancher sillage + liste d’escales + i18n | Visuel, zéro météo |
| **A1** | `polar.raw` dans le state | `alongTrackSpeed` testable avec Leopard 46 |
| **A2** | `voyageClock.js` + tests mars / juillet | Table sans UI |
| **A3** | `useVoyageClock` + `DepartureField` | Changer t0 régénère la table |
| **A4** | HUD + barre (date, jours, nœuds locaux, kind) | Plus de 7 kt magiques |
| **A5** | Quais calendaires | Bannière « à quai N j » + date qui saute |
| **A6** | Recette Atlantique + disclaimer | §13 au vert |

Ne pas commencer A3 si A2 n’a pas les tests mars ≠ juillet.  
Ne pas commencer B tant que A4 n’est pas recettable.

A0 peut partir en parallèle d’A1 (pas de dépendance météo).

---

## 12. Fichiers touchés / interdits

**Oui :** `naviguide-simulator/src/**` (+ tests), clés i18n.

**Non :**

- `naviguide/` (y compris `naviguide_weather_routing/`)
- `frontend/`, `backend/`
- `infra/vps/` (sauf un renvoi doc, pas un deploy)
- `server/copernicus/getWind.py` / `getWave.py` / `getCurrent.py`
  (NRT clic, autre `kind`)
- port 3010

---

## 13. Recette

1. Polar Leopard 46 chargé. Mode Simulation. t0 = **15 juin 08:00 UTC**,
   départ La Rochelle.
2. Play : le bateau part ; la barre affiche une date ≥ 15 juin ;
   `kind` climatologie.
3. Même route, t0 = **15 mars** : date d’arrivée Fort-de-France
   **différente** (plusieurs jours d’écart, visible).
4. Clic « Fort-de-France » dans la liste : bateau **et** date
   cohérents.
5. À une escale : date +2 j (défaut) sans bouger le bateau, puis
   reprise.
6. Hop Cayenne → Halifax : avion, date +~8 h, pas de nœuds polaire.
7. Quitter : le bateau disparaît (contrat étape 1b).
8. Disclaimer visible.
9. Backend éteint : film + horloge A (zones + polar si déjà en
   mémoire). Searoute down = fallback `public/route.geojson`.

---

## 14. Risques

| Risque | Parade |
|---|---|
| Deux nœuds à l’écran (poll 25 s vs table) | Couper `useExpeditionSpeed` dès A4 |
| 1 246 points trop lents | Table **une** fois, pas à chaque frame |
| `tHours` non monotone (sauts, antiméridien) | Tests ; hops = +8 h hors polaire |
| « 15 juin » lu comme prévision | Disclaimer + `kind` obligatoire |
| Départ Saint-Maur = polaire sur l’autoroute | t0 mer = La Rochelle par défaut |
| Confondre pause 1,4 s et jours à quai | Deux constantes, deux HUD |

---

## 15. Passage à la simulation B

A est fini quand : table d’horloge + t0 + ETA qui dépend du mois + HUD
daté + tests mars / juillet + recette §13.

B remplace **seulement** la fonction `vent(lat, lon, t)` pour les
10 premiers jours, ajoute l’horloge murale, puis un bouton qui
**change le trait d’une jambe**. L’intégrateur et la barre ne se
réécrivent pas.

Le schéma JSON du §7 **est** le contrat d’entrée de B.

Détail : [PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md).

---

## 16. Documents dont ce plan hérite

- [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)
  — film, searoute, polar sans chat, Leaflet.
- [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md)
  — `kind: climatology`, pas GFS comme moteur d’une circumnavigation.
- [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md) — le produit
  est le simulateur, pas `www.naviguide.fr`.
- [REGLES_PARAMETRES.md](./REGLES_PARAMETRES.md) §3.6 — `no_llm_for_numbers`,
  `wave_nogo_m` (A+ seulement).
- Code vivant A : `alongTrackSpeed.js`, `climatologyWind.js`,
  `polarSpeed.js`, `routePlayhead.js`, `filmCast.js`,
  `server/polar_api.py`.

# Plan — Audit de la « calculatrice » du simulateur et vitesse instantanée réelle

Version **1.0** — 20 septembre 2026. Règles : `docs/REGLES_WORKFLOW_AGENT.md`.
Demande du porteur : *« faire la liste des calculs que fait l'application,
voir si les bases mathématiques et conceptuelles sont justes »*, et en premier
lieu **la vitesse instantanée** : *« chaque jambe a sa vitesse propre, alors
que la vitesse varie tout le temps »* ; *« reconstituer ce que le bateau a
réellement subi comme météo depuis Saint-Maur (15 mai 2026) et calculer sa
position actuelle par l'addition de ces vitesses »*.

## 0. Ce que l'audit préliminaire a trouvé (20 septembre, code lu)

**A1 — Le passé est raconté à la climatologie, pas au temps réel.**
`server/voyage_api.py` construit l'horloge officielle avec
`make_wind_fn(t0, cube)` (`forecast_blend.py`) : prévision sur les **7 jours
qui suivent `t0` = 15 mai 08:00 UTC**, fondu jusqu'à J+10, **climatologie
mensuelle ensuite**. Depuis juin, toute la route — passée, présente, future —
est donc calculée avec les **vents moyens du mois** (`atlas_wind_at`). Le
bateau « d'aujourd'hui » n'a jamais rencontré un vrai coup de vent ; les
entrées `wx` du journal viennent d'un GRIB posé après coup. C'est la cause de
l'impression « chaque jambe a sa vitesse propre » : entre deux perles la
climatologie change peu.

**A2 — La vitesse affichée n'est pas celle qui déplace le bateau.**
La position vient de l'horloge (A1) ; la vitesse « mesurée » du client
(`useExpeditionSpeed`) vient de la polaire × GRIB au point du bateau. Deux
modèles, deux nombres ; à quai, l'échantillon recopie la vitesse de la jambe
(lot P2 du plan complémentaire).

**A3 — Le vent moyen sous-estime le temps de route.** La vitesse polaire est
convexe en bas et plafonne en haut : `v(moyenne du vent)` ≠ `moyenne de
v(vent)`. Une climatologie « moyenne » ne tient pas compte des calmes ni des
coups de vent, qui coûtent tous deux du temps. Il faut au minimum
échantillonner la rose (p25 / p50 / p75) et non la moyenne.

**A4 — Le courant est transporté mais jamais additionné.** `wind_pack` porte
`currentKn` / `currentToDeg` (et le cube `uo`, `vo`), mais `dt = span_nm /
speed_knots` ignore le courant : dans les alizés (Guyane, Caraïbes,
Mozambique) l'écart atteint 1–2 kn.

**A5 — Le résumé de l'expédition compte des sommets de recherche, pas des
étapes.** `summarizeRoute` (`src/utils/geo.js:131`) compte les **segments du
routeur** (36 = points de passage : Panama, caps, détroits…) et l'`ExpeditionBox`
(`ToolsSidebar.jsx:182`) affiche « 36 segments · 35 mer / 1 terre · 36 waypoints ·
1 248 points ». Le porteur veut des **étapes entre escales** (17 marques :
Saint-Maur, La Rochelle, Ajaccio, Fort-de-France, Pointe-à-Pitre, Gustavia,
Marigot, Cayenne, Saint-Pierre, Papeete, Mata-Utu, Nouméa, Dzaoudzi, Tromelin,
Saint-Gilles, Europa, La Rochelle → **16 étapes, 15 mer + 1 terre**). Les
1 248 points sont justes (points du tracé).

**A6 — Repli de vitesse grossier.** Sans polaire, `boat_speed_from_wind` =
0,45 × vent borné [4 ; 11] kn (`climatology_zones.py:89`) : il ne dépend pas de
l'allure. La polaire du catamaran existe : le repli ne devrait servir qu'en
son absence et le dire (`basis: "fallback"`).

**A7 — Constantes à justifier ou à documenter.** `WAVE_NOGO_M = 2,5 m` et
`WAVE_NOGO_DT_FACTOR = 3` (le temps est triplé dès 2,5 m de Hs — très sévère
pour un catamaran de voyage, et discontinu : 2,4 m → ×1, 2,5 m → ×3) ;
`MIN_KNOTS = 0,5` ; `LAND_CALENDAR_HOURS = 4` (Saint-Maur → La Rochelle en 4 h
de route : plausible) ; `AIR_CALENDAR_HOURS = 8` ; `WX_GALE_KT = 34`
(force 8) et `WX_HS_M = 3,5` ; jours à quai `port_days_for` (3 par défaut).
Aucune n'est fausse en soi ; toutes doivent être dans `REGLES_PARAMETRES.md`
avec leur source et testées aux bornes.

> **Vérification faite le 20 sept. (soir)** : chaque ligne du § 1 a été
> confrontée à l'état de l'art dans
> [`audits/CALCULS_ETAT_DE_L_ART.md`](audits/CALCULS_ETAT_DE_L_ART.md)
> (routeurs qtVlm / LuckGrib / PredictWind, littérature isochrones, biais
> ERA5, conventions WMO et Copernicus). Ce qui change dans les lots :
> C4 remplace la pénalité de mer ×3 par une **polaire de vagues** (facteur
> continu Hs × angle), ajoute un **facteur d'efficacité de croisière**
> (`POLAR_EFFICIENCY`, défaut 0,85) et les **limites d'allure** ; C2 corrige
> les **vents forts d'ERA5** (sous-estimés) et prend les archives de
> prévision comme source primaire ; le conseil de route (§ 1 l. 21) passe de
> **6 h à 3 h** de pas (1 h près des côtes) ; la popup satellite doit tester
> la convention **courant « vers », vent et vagues « de »**.

## 1. Inventaire des calculs (à vérifier un par un)

| # | Calcul | Où | Formule / méthode actuelle | Verdict | À faire |
|---|---|---|---|---|---|
| 1 | Distance entre deux points | `src/utils/geo.js:59`, `route_engine.py` (`cumNm`) | haversine, R = 3 440,065 nm | Juste (erreur sphérique ≤ 0,3 % ; acceptable) | test : Saint-Maur → La Rochelle ≈ 190 nm orthodromiques ; La Rochelle → Ajaccio |
| 2 | Cap initial | `voyage_clock.py:49` `bearing_deg` | formule orthodromique | Juste | test cardinaux |
| 3 | Angle du vent (TWA) | `voyage_clock.py:62`, `skipperOrders.js` `trueWindAngle` | \|cap − vent de\| replié sur [0 ; 180] | Juste | test symétrie |
| 4 | Vitesse polaire | `voyage_clock.py:83` `polar_boat_speed` (bilinéaire TWA × TWS) ; client `polarBoatSpeed` | interpolation bilinéaire, hors grille = bord | Juste ; vérifier que **client et serveur donnent le même nombre** sur 20 cas | test croisé JS/Python sur fixtures |
| 5 | Vitesse de repli sans polaire | `climatology_zones.py:89` | 0,45 × vent, borné [4 ; 11] | Grossier (A6) | n'utiliser que sans polaire, le dire |
| 6 | Temps par segment | `voyage_clock.py:294` `dt = span / v`, vent lu à **l'heure de début** du segment, au **milieu** géographique | Approximation d'Euler explicite ; correcte si segments courts (moyenne 31 nm, max à vérifier) | sous-découper les segments > 60 nm en pas de 30 nm ; vent à mi-temps |
| 7 | Pénalité de mer | `voyage_clock.py:296` Hs ≥ 2,5 m → dt × 3 | Discontinu et sévère (A7) | courbe continue : facteur 1 + k·max(0, Hs − 2)² plafonné à 2 ; source : profil Croisière |
| 8 | Courant | `wind_pack.currentKn`, cube `uo/vo` | transporté, non additionné (A4) | SOG = vecteur bateau + vecteur courant (projection sur la route) |
| 9 | Régimes de vent | `forecast_blend.py` | prévision 0–7 j **depuis t0**, fondu 7–10 j, climatologie | Faux pour le passé (A1) ; le fondu doit être relatif à **maintenant** | lot C2 (trois régimes) |
| 10 | Climatologie | `climatology_atlas.py` `atlas_wind_at` | moyenne mensuelle + direction dominante | Biais (A3) | échantillon p25/p50/p75 de la rose, temps = moyenne des trois |
| 11 | Échantillon à un instant | `voyage_clock.py:362` `sample_clock_at_hours`, `voyageClock.js:486` | interpolation linéaire entre sommets ; vitesse = celle du segment ; à quai = jambe (P2) | Juste hors quai | P2 ; vitesse = dérivée locale après C2 |
| 12 | Vitesse « mesurée » côté client | `useExpeditionSpeed.js` | polaire × GRIB interpolé (`lerpSeries`) | Cohérente en soi, mais ≠ modèle de position (A2) | après C2, une seule vitesse : celle de l'horloge |
| 13 | Vitesse de planification | `skipperOrders.js:307` `planningSpeedFor`, `PLANNING_MIN_KN` | polaire × vent (GRIB ou climato) | Juste | test bornes |
| 14 | Horizons / anticipation | `skipperOrders.js` (`resolveOrders`) | distance / vitesse planifiée | Juste | test |
| 15 | Jours à quai | `voyage_clock.py:24` | 0 (Saint-Maur), 3 par défaut, table | Convention | documenter par escale |
| 16 | Tronçon route / saut avion | `LAND_CALENDAR_HOURS`, `AIR_CALENDAR_HOURS` | constantes | Convention | documenter |
| 17 | Résumé de l'expédition | `geo.js:131`, `ToolsSidebar.jsx:182` | compte les segments du routeur | Trompeur (A5) | lot C1 |
| 18 | `filmNm` vs `cumNm` | `voyage_clock.py:327` `filmCum` | distance « film » sans le saut avion | À expliquer dans l'UI (info-bulle) | test : filmNm ≤ cumNm |
| 19 | Événements météo | `voyage_journal.py:45` `wx_entry_from_grib` (≥ 34 kn ou Hs ≥ 3,5 m) | seuils Beaufort 8 / mer forte | Juste ; ajouter durée/max (plan film F2) | |
| 20 | Composite météo satellite (popup) | `weather_composite.py` / `useSatellitePopup` | Copernicus : plus proche cellule ou bilinéaire ? cardinaux vagues/courants | vérifier l'interpolation et l'unité (m/s → kn : × 1,943 84) | test unités |
| 21 | Isochrones (conseil de route) | `isochrone.py` | pas de temps, résolution angulaire, masque terre, zones interdites skipper | à vérifier : pas ≤ 3 h, 15°, `is_land` sur la corde | tests existants + cas antiméridien |
| 22 | Longitude repliée | `route_engine.py:571`, client | [−180 ; 180] attendu par searoute | bug connu (lot S) | lot S |
| 23 | Échelle du replay | `replay.js` `replayScale` | 1 s / jour | remplacé par le plan film (150 s) | plan film F1 |
| 24 | Revue de plan (`sailNm`, saisons) | `plan_review.py` | corrigé lot K | Juste | |
| 25 | Distance perle ↔ route (`cumNm` des perles) | `ici_warm.py` `sample_route_nm` | corrigé lot K | Juste | |

## 2. Cible : une horloge à trois régimes, une seule vitesse

```
t < maintenant          : HINDCAST  — vent, houle, courant archivés (ce que le bateau a rencontré)
maintenant → +7 j       : PRÉVISION — cube GRIB courant (fondu 7 → 10 j)
> +10 j                 : CLIMATOLOGIE — rose échantillonnée (p25/p50/p75), pas la moyenne
```

- La **position d'aujourd'hui** est l'intégrale des vitesses instantanées
  depuis La Rochelle : `x(t) = Σ v(vent(x_i, t_i), cap_i, courant_i) · Δt`,
  à pas de 30 nm ou 1 h (le plus court), avec les escales (jours à quai).
- La **vitesse affichée** est la vitesse du segment d'intégration courant
  (donc 0 à quai) — la même partout : barre film, chat, bulle, fiche.
- Le régime est **affiché** avec chaque vitesse : « hindcast (ERA5) »,
  « prévision (GFS, +36 h) », « climatologie (juin) ». Champ inconnu = vide.

### Données du hindcast : **tous** les produits Open-Meteo **et** Copernicus Marine

Décision du porteur (20 sept.) : pas d'alternative, **les deux fournisseurs
sont utilisés ensemble**, sur chaque variable, et le système dit combien de
sources il a vues et si elles sont d'accord.

| Variable | Open-Meteo (sans clé, usage non commercial) | Copernicus Marine (`copernicusmarine`, identifiants déjà sur le VPS, fonctions `server/copernicus/get*.py` à doter d'un intervalle de temps) |
|---|---|---|
| Vent 10 m (vitesse, direction, rafales) | **Historical Forecast API** — archives des modèles de prévision (GFS 0,25°, ECMWF IFS, ICON…) : `historical-forecast-api.open-meteo.com/v1/forecast?…&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&wind_speed_unit=kn` (retard ~2 j) ; **Historical Weather API** — réanalyse ERA5 : `archive-api.open-meteo.com/v1/archive` (retard ~5 j, correction des vents forts) | **WIND_GLO_PHY_L4_NRT_012_004**, dataset `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` (`eastward_wind`, `northward_wind`) — vent L4 issu des diffusiomètres, 0,125°, horaire (déjà utilisé par la popup) |
| Houle (Hs, direction, période) | **Marine API** : `marine-api.open-meteo.com/v1/marine?…&hourly=wave_height,wave_direction,wave_period` (MFWAM / GWAM) | **GLOBAL_ANALYSISFORECAST_WAV_001_027**, dataset `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i` (`VHM0`, `VMDR`, `VTM02`) — analyses conservées ~2 ans, 1/12°, 3 h |
| Courant de surface | **Marine API** : `hourly=ocean_current_velocity,ocean_current_direction` | **GLOBAL_ANALYSISFORECAST_PHY_001_024**, dataset `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` (`uo`, `vo`) — 1/12°, horaire |
| Prévision (régime 2) | **Forecast API** (GFS, IFS, ICON — déjà `grib_fetch.py`) et **Ensemble API** (GEFS, IFS ENS) pour l'ETA probabiliste | mêmes produits WAV / PHY / WIND en partie prévision (déjà la popup) |

**Fusion, par variable et par heure** : on collecte toutes les sources
disponibles à `(lat, lon, t)` ; la valeur retenue est la **médiane** ; on
garde la liste des sources et l'**écart** (max − min). L'horloge intègre la
médiane ; chaque sommet porte `sources: [...]` et `spread` ; l'interface
affiche « 3 sources · ±2 kn » ou « 1 source (ERA5) ». Une variable sans
aucune source reste **vide** (jamais inventée). Directions : vent et vagues
« d'où ça vient », courant « vers où ça va » (convention Copernicus / WMO).

Volume : la route parcourue depuis le 15 mai ≈ 450 points de tracé ; **une
requête par point et par produit** (série horaire sur ± 2 jours autour de
l'heure estimée, puis raffinement si l'heure bouge de plus de 12 h) ≈ 450 ×
(3 Open-Meteo + 3 Copernicus) ≈ 2 700 requêtes, **une fois**, séquentielles
(Copernicus : `subset` par point et par dataset, 1–2 s chacun ≈ 40 min ;
Open-Meteo : limite gratuite 10 000/jour), puis **quelques requêtes par jour**
pour prolonger. Tout est mis en cache dans SQLite (`pearl_store.kv`, ns
`hindcast`) — jamais retéléchargé.

## 3. Les lots

Ordre : **C1 → C2 → C3 → C4 → C5**. C1 est indépendant.

### Lot C1 — Résumé de l'expédition juste (S)

**Fichiers.** `src/components/ToolsSidebar.jsx` (`ExpeditionBox`, l. 182–197),
`src/utils/geo.js` (`summarizeRoute` : ajouter `legs` calculées depuis les
marques d'escale), `src/i18n/{fr,en}.js`, `src/utils/geo.test.js`.

**Étapes.** 1) Étapes = marques d'escale consécutives (`escaleMarks`) ; mer /
terre depuis `nonMaritime`. 2) Ligne : « 39 425,9 nm · 16 étapes (15 mer,
1 terre) · 17 escales · 1 248 points » ; info-bulle sur « points » : « 36
points de passage du routeur (caps, canaux), 1 248 sommets du tracé ». 3) Le
mot « waypoints » disparaît de la ligne (il reste dans l'info-bulle).

**Tests.** `geo.test.js` : 17 marques → 16 étapes ; Saint-Maur → La Rochelle
comptée terre.

**Recette (changement visible).** Outils droite, premier encadré : la ligne
ci-dessus exactement ; survol de « points » → info-bulle. Spec :
`data-testid="route-summary"` contient « 16 étapes ». Capture.

### Lot C2 — Hindcast : le vent et la mer que le bateau a vraiment rencontrés (L)

**Fichiers.** nouveau `server/hindcast.py` (+ test, faux serveur HTTP),
`server/forecast_blend.py` (trois régimes, fondu relatif à **maintenant**),
`server/voyage_clock.py` (`build_voyage_clock` : pas de 30 nm / 1 h,
vent à mi-temps, régime dans le sommet), `server/voyage_api.py`
(`_fill_forecast` → `_fill_hindcast_then_forecast`, tâche quotidienne),
`server/pearl_store.py` (ns `hindcast`), `server/voyage_journal.py` (les `wx`
viennent du hindcast : durée, max), `docs/REGLES_PARAMETRES.md`.

**Étapes.** 1) `hindcast.py` : `series(lat, lon, day)` → vent/rafales/houle/
courant horaires depuis **toutes** les sources du tableau ci-dessus
(Open-Meteo Historical Forecast, Historical Weather/ERA5, Marine ; Copernicus
WIND L4, WAV, PHY via `server/copernicus/get*.py` dotés d'un paramètre
d'intervalle de temps), fusion par **médiane** avec `sources` et `spread`,
cache, retries, **correction des vents forts** quand la source est ERA5
(facteur `ERA5_STRONG_WIND_FACTOR` = 1,05 au-dessus de 15 m/s, cité dans
`REGLES_PARAMETRES.md`) ; une source en panne n'empêche rien, elle manque
simplement dans `sources`. 2) Intégration avant :
pour chaque pas, vent/courant à `(x_i, t_i)` ; escales → jours à quai ;
`regime` dans chaque sommet. 3) `blended_wind` : `hours_since(now)` et non
`t0`. 4) Le premier calcul complet tourne en tâche de fond au démarrage
(≈ 10 min) ; l'horloge climatologique reste servie en attendant, marquée
`kind: "climatology"`. 5) Nouvel endpoint `GET /voyage/official/regimes` :
portions de route par régime (pour l'UI, lot C3).

**Tests.** Faux Open-Meteo et faux Copernicus : deux jours de vent connus →
position attendue à 1 nm près ; médiane de trois sources ; une source en
panne → deux sources, `spread` calculé ; à quai 0 kn ; changement de régime à
`now` ; cache : deuxième appel sans réseau ; tout en panne → climatologie
marquée.

**Recette (changement visible).** Barre film, en Suivre : « 7,4 kn · hindcast
· 3 sources ±1,5 kn » ; à quai « à quai · hindcast » ; la position du bateau
d'aujourd'hui **change** (elle bouge de quelques dizaines à quelques centaines
de nm par rapport à la climatologie : le dire dans la PR avec le chiffre).
Journal : les `wx` ont une durée et un max, aux dates réelles des coups de
vent de l'été 2026. Spec (API lancée) : `data-testid="clock-regime"` contient
« hindcast » à Nouméa.

### Lot C3 — Une seule vitesse, partout (M)

**Fichiers.** `src/hooks/useExpeditionSpeed.js`, `src/engine/voyageClock.js`
(`sampleClockAtHours` : vitesse du pas courant), `src/App.jsx` **par extrait**
(`rg -n "expeditionSpeed|boatKnots" src/App.jsx`), `server/logbook_chat.py`
(contexte), `src/components/SimulationFilmBar.jsx` (régime affiché),
`src/layers/useClimatologyLayer.js` (teinte de la route par régime, en option).

**Étapes.** 1) La vitesse affichée = `sample.speedKnots` de l'horloge (0 à
quai) ; `useExpeditionSpeed` ne calcule plus une vitesse concurrente en
Suivre (il reste utile en Simulation pour la vitesse prévue). 2) Chat : la
même vitesse et le régime. 3) Route parcourue teintée par régime (hindcast /
prévision / climatologie) — **ajout**, rien retiré.

**Recette (changement visible).** Barre film, chat, bulle « Aujourd'hui » :
**le même nombre** ; à quai : « à quai » partout ; légende des régimes sous la
route. Spec : la vitesse de la barre = celle du chat (regex).

### Lot C4 — Courant additionné, polaire de vagues, efficacité de croisière, climatologie échantillonnée (M)

**Fichiers.** `server/voyage_clock.py` (§ 1 lignes 4, 7, 8, 10), `server/isochrone.py`
(`_boat_speed`, `time_step_h`, `heading_step_deg`), `server/climatology_atlas.py`
(p25/p50/p75 de la rose), `src/engine/skipperOrders.js` (`planningSpeedFor`),
`server/tests/test_voyage_clock.py`, `docs/REGLES_PARAMETRES.md`.

**Étapes.** 1) Courant : SOG = projection sur la route de (vecteur polaire +
vecteur courant `uo/vo`). 2) Polaire de vagues : `v × f(Hs, angle relatif)`,
f = 1 jusqu'à 1,5 m, linéaire jusqu'à 0,6 à 4 m par mer de face et 0,85 par
mer arrière, plafonné ; remplace `WAVE_NOGO_DT_FACTOR`. 3) `POLAR_EFFICIENCY`
(0,85) appliqué partout où la polaire sert (horloge, planification, conseil
de route) ; limites d'allure (près ≥ 40° TWA, portant ≤ 170°) dans le conseil
de route seulement. 4) Climatologie : trois tirages de la rose (p25/p50/p75)
→ temps moyen. 5) Isochrones : pas 3 h en haute mer, 1 h à moins de 60 nm
d'une côte (`is_path_clear` le sait), `max_steps` recalculé.

**Tests.** Courant 2 kn dans l'axe → SOG = polaire × 0,85 + 2 ; contre →
− 2 ; Hs 2,4 → 2,6 m : facteur continu (pas de saut) ; mer de face plus
pénalisante que mer arrière ; climatologie : temps p25/p50/p75 moyenné ≥
temps à la moyenne (Jensen) ; isochrone : pas 1 h à 30 nm d'une côte.

**Recette (aucun changement visible, sauf les nombres).** Les ETA de la
revue de plan changent (typiquement +3 à +8 % de temps de mer) ; la PR donne
l'avant / après par étape.

### Lot C5 — Cahier des calculs et tests croisés client / serveur (S)

**Fichiers.** nouveau `docs/audits/CALCULS.md` (une fiche par ligne du § 1 :
formule, unités, source, test qui la protège), `src/utils/geo.test.js`,
`server/tests/test_polar_parity.py` + `src/engine/polar.parity.test.js`
(mêmes 20 cas TWA × TWS → même vitesse à 0,05 kn), `weather_composite`
(unités m/s → kn).

**Recette (aucun changement visible).** Tests verts ; le cahier existe et
chaque ligne du § 1 y renvoie.

## 4. Réponse au porteur

- La vitesse **paraît** constante par jambe parce que le passé est calculé
  avec les vents **moyens du mois** ; le vrai vent n'est jamais entré dans
  l'horloge après les 10 premiers jours (A1).
- Oui, on peut télécharger la météo passée — **Open-Meteo et Copernicus
  Marine ensemble** (archives GFS/IFS, réanalyse ERA5, Marine API ; vent L4,
  vagues et courants Copernicus), fusionnés par médiane avec le nombre de
  sources et leur écart affichés —, la rejouer point par point depuis La
  Rochelle et obtenir **la position d'aujourd'hui comme somme des vitesses
  instantanées** (lot C2), la même vitesse partout (C3), le courant compris (C4).
- Le résumé « 36 segments / 36 waypoints » compte les points de passage du
  routeur ; il deviendra « 16 étapes (15 mer, 1 terre) · 17 escales · 1 248
  points » (C1).

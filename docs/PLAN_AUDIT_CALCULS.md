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

### Données du hindcast (gratuites, sans clé, usage non commercial)

| Besoin | Source | Points d'accès | Résolution | Retard |
|---|---|---|---|---|
| Vent 10 m (vitesse, direction, rafales), heure par heure, depuis mai 2026 | **Open-Meteo Historical Forecast API** (archives des modèles de prévision : GFS 0,25°, ECMWF IFS, ICON) | `historical-forecast-api.open-meteo.com/v1/forecast?latitude&longitude&start_date&end_date&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&wind_speed_unit=kn` | 0,25° / horaire | ~2 jours |
| Même chose en réanalyse (référence, plus lisse) | **Open-Meteo Historical Weather API** (ERA5 / ERA5-Land) | `archive-api.open-meteo.com/v1/archive` | 0,25° / horaire | ~5 jours |
| Houle (Hs, direction, période), courant de surface | **Open-Meteo Marine API** | `marine-api.open-meteo.com/v1/marine?hourly=wave_height,wave_direction,wave_period,ocean_current_velocity,ocean_current_direction&start_date&end_date` | 0,08–0,25° / horaire | ~1 jour |
| Alternative « officielle » (déjà utilisée par la popup) | Copernicus Marine (`copernicusmarine`), produits `GLOBAL_ANALYSISFORECAST_WAV`, `_PHY` (analyses passées disponibles) | déjà dans `weather_composite.py` | 1/12° | 1 jour |

Volume : la route parcourue depuis le 15 mai ≈ 450 points de tracé ; **une
requête par point** (série horaire sur ± 2 jours autour de l'heure estimée,
puis raffinement si l'heure bouge de plus de 12 h) ≈ 500–900 requêtes, une
fois, puis **une requête par jour** pour prolonger. Limite gratuite :
10 000 requêtes/jour. Tout est mis en cache dans SQLite (`pearl_store.kv`, ns
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
courant horaires (Open-Meteo Historical Forecast + Marine), cache, retries,
`source` (« GFS archive », « ERA5 », « Marine »). 2) Intégration avant :
pour chaque pas, vent/courant à `(x_i, t_i)` ; escales → jours à quai ;
`regime` dans chaque sommet. 3) `blended_wind` : `hours_since(now)` et non
`t0`. 4) Le premier calcul complet tourne en tâche de fond au démarrage
(≈ 10 min) ; l'horloge climatologique reste servie en attendant, marquée
`kind: "climatology"`. 5) Nouvel endpoint `GET /voyage/official/regimes` :
portions de route par régime (pour l'UI, lot C3).

**Tests.** Faux Open-Meteo : deux jours de vent connus → position attendue à
1 nm près ; à quai 0 kn ; changement de régime à `now` ; cache : deuxième
appel sans réseau ; échec réseau → climatologie marquée.

**Recette (changement visible).** Barre film, en Suivre : « 7,4 kn · hindcast
(GFS archive) » ; à quai « à quai · hindcast » ; la position du bateau
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

### Lot C4 — Courant additionné, pénalité de mer continue, climatologie échantillonnée (M)

**Fichiers.** `server/voyage_clock.py` (§ 1 lignes 8, 7, 10), `server/climatology_atlas.py`
(p25/p50/p75 de la rose), `server/voyage_clock_test.py`, `docs/REGLES_PARAMETRES.md`.

**Tests.** Courant 2 kn dans l'axe → SOG = polaire + 2 ; contre → − 2 ; Hs
2,4 → 2,6 m : facteur continu ; climatologie : temps p25/p50/p75 moyenné ≥
temps à la moyenne (Jensen).

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
- Oui, on peut télécharger la météo passée **gratuitement** (Open-Meteo :
  archives GFS/IFS et réanalyse ERA5, houle et courant par la Marine API),
  la rejouer point par point depuis La Rochelle et obtenir **la position
  d'aujourd'hui comme somme des vitesses instantanées** (lot C2), la même
  vitesse partout (C3), le courant compris (C4).
- Le résumé « 36 segments / 36 waypoints » compte les points de passage du
  routeur ; il deviendra « 16 étapes (15 mer, 1 terre) · 17 escales · 1 248
  points » (C1).

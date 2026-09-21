# Cahier des calculs du simulateur

Version **1.0** — 20 septembre 2026. Lot C5 (`docs/lot-c5-cahier-calculs`).
Inventaire : [`PLAN_AUDIT_CALCULS.md`](../PLAN_AUDIT_CALCULS.md) § 1.
État de l’art : [`CALCULS_ETAT_DE_L_ART.md`](CALCULS_ETAT_DE_L_ART.md).
Paramètres : [`REGLES_PARAMETRES.md`](../REGLES_PARAMETRES.md) § 3.7–3.8.

Ce lot **documente et teste**. Aucune formule n’est changée.

Coordonnées officielles Berry (`public/route.geojson`) :
Saint-Maur (Berry, Indre) 46,8075° N 1,6358° E ;
La Rochelle 46,1541° N 1,167° W ;
Ajaccio 41,9192° N 8,7386° E.

Légende verdict (après C1–C4) : **✔** conforme · **≈** acceptable / convention · **✘** encore à corriger (autre lot).

---

## 1. Distance entre deux points

- **Formule.** Haversine sphérique : \(a=\sin^2(\Delta\varphi/2)+\cos\varphi_1\cos\varphi_2\sin^2(\Delta\lambda/2)\), \(d=2R\arcsin\sqrt{a}\). \(\Delta\lambda\) replié dans \(]-180;180]\).
- **Unités.** lat/lon en degrés ; résultat en milles nautiques. \(R=3440{,}065\) nm \(=6371{,}0088\) km / 1,852.
- **Où.** `src/utils/geo.js` `haversineNm` ; sommets `cumNm` côté route / horloge.
- **Source.** Sphère (erreur ≤ 0,3–0,5 % vs ellipsoïde WGS-84) [1][2].
- **Test.** `src/utils/geo.test.js` — Saint-Maur → La Rochelle = **122,3 nm ± 5** ; La Rochelle → Ajaccio ≈ 497 nm. Le plan § 1 visait 190 ± 5 : écart du brief (pas du code) — déjà 122,3 dans `test_ici_warm.py`.
- **Verdict.** ✔

## 2. Cap initial

- **Formule.** Orthodromie : \(y=\sin\Delta\lambda\cos\varphi_2\), \(x=\cos\varphi_1\sin\varphi_2-\sin\varphi_1\cos\varphi_2\cos\Delta\lambda\), cap \(=(\mathrm{atan2}(y,x)+360)\bmod 360\).
- **Unités.** Degrés vrais, 0 = nord, 90 = est.
- **Où.** `server/voyage_clock.py` `bearing_deg` (Δλ replié) ; client `src/engine/routeWindProfile.js` `bearingDeg` (Δλ non replié — écart antiméridien, lot S).
- **Source.** Formule standard de navigation [1].
- **Test.** `geo.test.js` cardinaux N/E/S/O ; Saint-Maur → La Rochelle ≈ 252° (OSO). `routeWindProfile.test.js` est ≈ 90°.
- **Verdict.** ✔

## 3. Angle du vent (TWA)

- **Formule.** \(|\mathrm{cap}-\mathrm{vent\,«\,de\,»}|\) replié sur \([0;180]\). Symétrique babord / tribord.
- **Unités.** Degrés. Vent **10 m**, pas de correction de hauteur de mât.
- **Où.** `voyage_clock.py` `twa_deg` ; `src/engine/playSpeeds.js` `trueWindAngle` ; `routeWindProfile.js` `twaDeg`.
- **Source.** TWA / TWS de polaire ORC/VPP [4].
- **Test.** `playSpeeds.test.js` (0 / 180 / wrap) ; `polar.parity.test.js` TWA −90° = +90°.
- **Verdict.** ✔

## 4. Vitesse polaire

- **Formule.** Interpolation bilinéaire TWA × TWS sur la table brute. TWA \(<\) premier angle : fondu linéaire vers 0. TWS au-delà du max : plateau (dernière colonne). Arrondi 0,001 kn.
- **Unités.** TWA °, TWS kn, vitesse kn (surface, avant efficacité / vagues / courant).
- **Où.** `voyage_clock.polar_boat_speed` ; `polar_engine.PolarData.speed` ; client `polarBoatSpeed`.
- **Source.** Même convention que LuckGrib (plateau TWS max) [4]. Croisière : × `POLAR_EFFICIENCY` 0,85 (lot C4).
- **Test.** `server/tests/test_polar_parity.py` + `src/engine/polar.parity.test.js` — 20 cas, fixture `server/tests/fixtures/polar_cases.json`, écart ≤ 0,05 kn.
- **Verdict.** ≈ (efficacité C4 ; limites d’allure seulement au conseil de route)

## 5. Vitesse de repli sans polaire

- **Formule.** \(0{,}45\times\mathrm{TWS}\), borné \([4;11]\) kn, arrondi 0,1.
- **Unités.** kn.
- **Où.** `climatology_zones.py` `boat_speed_from_wind`.
- **Source.** Repli interne ; les routeurs refusent de router sans polaire [4].
- **Test.** `test_hindcast.py` (horloge sans polaire). Déclaration `basis: "fallback"` → lot C7.
- **Verdict.** ≈

## 6. Temps par segment

- **Formule.** Euler : \(dt=d/v\). Pas ≤ 30 nm et ≤ 1 h. Vent lu au **milieu** géographique et à **mi-temps** du pas (lot C2).
- **Unités.** nm, kn, h.
- **Où.** `voyage_clock.py` `build_voyage_clock` (boucle `MAX_STEP_NM` / `MAX_STEP_H`).
- **Source.** Isochrones : pas court devant l’évolution du vent [6][7].
- **Test.** `test_voyage_clock.py` (pas ≤ 30 nm).
- **Verdict.** ≈ (C2 fait ; climatologie encore moyenne hors rose)

## 7. Pénalité de mer (polaire de vagues)

- **Formule.** \(v\times f(H_s,\alpha)\). \(f=1\) si \(H_s\le 1{,}5\) m ; linéaire jusqu’à 0,60 (mer de face) / 0,85 (mer arrière) à 4 m ; plafonné au-delà. \(\alpha=0\) = houle « de » dans le cap.
- **Unités.** Hs m ; facteur sans dimension.
- **Où.** `voyage_clock.wave_polar_factor` (remplace `WAVE_NOGO_DT_FACTOR` ×3).
- **Source.** PredictWind / qtVlm, polaire de vagues continue [5][8]. C4.
- **Test.** `test_voyage_clock.py` `test_c4_wave_polar_continuous_and_head_worse_than_follow`.
- **Verdict.** ✔ (après C4)

## 8. Courant (SOG)

- **Formule.** SOG = STW + projection sur la route du vecteur courant. `uo`/`vo` en m/s × 1,943844 ; ou `currentKn` + `currentToDeg` (« vers »). Leeway ignoré.
- **Unités.** kn. Cap courant : 0 = nord, 90 = est.
- **Où.** `voyage_clock.current_along_route_kn`, `sog_along_route` ; `isochrone.py`.
- **Source.** Set and drift [9][10]. C4.
- **Test.** `test_c4_current_along_and_against` ; conventions `test_weather_pipeline.py`.
- **Verdict.** ✔ (après C4)

## 9. Régimes de vent

- **Formule.** \(t<\) maintenant : hindcast ; 0–7 j : prévision ; 7–10 j : fondu linéaire ; \(>\) 10 j : climatologie. Fondu relatif à **maintenant**, plus à `t0`.
- **Unités.** Heures depuis `now`.
- **Où.** `forecast_blend.py` `blended_wind`.
- **Source.** Skill déterministe ≈ 7 j [11][12]. C2.
- **Test.** `test_forecast_blend.py` ; `test_hindcast.py` (changement de régime à `now`).
- **Verdict.** ✔ principe ; ensembles (ETA p10–p90) → lot C6

## 10. Climatologie

- **Formule.** Rose : trois tirages p25 / p50 / p75 → moyenne des **temps** (pas le temps à la moyenne). Inégalité de Jensen.
- **Unités.** kn, ° « de ».
- **Où.** `climatology_atlas.py` ; horloge si `roseKnots` présent.
- **Source.** Pilot charts = roses de fréquence [13]. C4.
- **Test.** `test_c4_climatology_jensen_mean_of_times`.
- **Verdict.** ✔ (après C4)

## 11. Échantillon à un instant

- **Formule.** Interpolation linéaire entre sommets d’horloge. Vitesse = celle du pas. À quai : 0 kn (lot P2 / C3).
- **Unités.** `filmNm`, `sailNm`, kn, ISO 8601 UTC.
- **Où.** `voyage_clock.sample_clock_at_hours` ; `voyageClock.js` `sampleClockAtHours`.
- **Source.** Cinématique d’horloge (contrat A = B).
- **Test.** `voyageClock.test.js` ; `test_voyage_clock.py`.
- **Verdict.** ✔ hors quai ; ✔ à quai après P2/C3

## 12. Vitesse « mesurée » côté client

- **Formule.** En **Suivre** : `sample.speedKnots` de l’horloge (`resolveFollowSpeed`). En **Simulation** : polaire × vent interpolé (`lerpSeries`) — vitesse prévue, pas une seconde cinématique.
- **Unités.** kn.
- **Où.** `src/hooks/expeditionSpeed.js`, `useExpeditionSpeed.js`.
- **Source.** Une seule cinématique (C3).
- **Test.** `uiProductContract.test.js` lot C3 ; `e2e/lots/c3-vitesse.spec.js`.
- **Verdict.** ✔ (après C3)

## 13. Vitesse de planification

- **Formule.** \(\max(3,\mathrm{polaire}\times 0{,}85)\) kn, arrondi 0,1 (demi loin de zéro).
- **Unités.** kn.
- **Où.** `skipperOrders.js` `planningSpeedFor` ; `voyage_clock.planning_speed_for`.
- **Source.** Même table que § 4 + plancher skipper.
- **Test.** `skipperOrders.test.js` (C4) ; `test_c4_planning_speed_parity_with_js`.
- **Verdict.** ✔

## 14. Horizons / anticipation

- **Formule.** Distance d’anticipation = \(H\times v_{\mathrm{plan}}\) (le horizon ne ment pas). \(H\in\{24,36,48\}\) h.
- **Unités.** h, kn, nm.
- **Où.** `skipperOrders.js` `resolveOrders`, `lookaheadBudget`.
- **Source.** Contrat skipper § 2.6.
- **Test.** `skipperOrders.test.js` « lookahead budget » / « S6 — horizon knob ».
- **Verdict.** ✔

## 15. Jours à quai

- **Formule.** 0 (Saint-Maur), 3 (La Rochelle et défaut), 1 (Halifax). \(hold=jours\times 24\) h.
- **Unités.** jours calendaires.
- **Où.** `voyage_clock.port_days_for`.
- **Source.** Convention programme Berry-Mappemonde 2026. Table JSON → lot C7.
- **Test.** Horloge : trou ISO à quai (`voyageClock.test.js` « 2-day quay »).
- **Verdict.** ≈

## 16. Tronçon route / saut avion

- **Formule.** Terre Saint-Maur → La Rochelle : +4 h (`LAND_CALENDAR_HOURS`). Saut avion : +8 h (`AIR_CALENDAR_HOURS`). Pas de polaire.
- **Unités.** h.
- **Où.** `voyage_clock.py`.
- **Source.** Convention (4 h de route ; 8 h de vol). C7 pour exposer `params`.
- **Test.** `voyageClock.test.js` (véhicule `land` / `plane`).
- **Verdict.** ≈

## 17. Résumé de l’expédition

- **Formule.** Étapes = marques d’escale consécutives (`marksForSummary`). Mer / terre via `nonMaritime`. Points = sommets du tracé ; waypoints = segments routeur.
- **Unités.** nm (1 décimale), comptes entiers.
- **Où.** `geo.js` `summarizeLegs` ; `ToolsSidebar` `route-summary`.
- **Source.** C1 (plus les 36 segments routeur).
- **Test.** `geo.test.js` : 17 marques → 16 étapes (15 mer, 1 terre), 1 248 points.
- **Verdict.** ✔ (après C1)

## 18. `filmNm` vs `cumNm`

- **Formule.** `cumNm` / `sailNm` : distance routeur y compris saut avion. `filmCum` / `filmNm` : même route **sans** le saut (le film ne traverse pas le globe). Donc `filmNm` ≤ `sailNm`.
- **Unités.** nm.
- **Où.** `voyage_clock.py` `_emit` ; client `voyageClock.js`.
- **Source.** Convention film. Info-bulle UI → lot C7.
- **Test.** `test_voyage_clock.py` (jambe `jump` : `filmCum` avance, `cumNm` peut rester).
- **Verdict.** ≈

## 19. Événements météo

- **Formule.** Coup de vent : TWS ≥ 34 kn (Beaufort 8). Mer : Hs ≥ 2,5 m durable (≥ 6 h) « forte » ; Hs ≥ 4 m « très forte ».
- **Unités.** kn, m, h.
- **Où.** `voyage_journal.py` `wx_entry_from_grib` (`WX_GALE_KT`, `WX_HS_*`).
- **Source.** Beaufort [14] ; code WMO état de la mer [15]. Durée / max → plan film F2.
- **Test.** `test_voyage_journal.py` (12 kn / 1 m → vide ; 36,5 kn → wx ; Hs 4,1 → mer).
- **Verdict.** ✔ (34 kn) / ≈ (durée mer)

## 20. Composite météo satellite (popup)

- **Formule.** Cellule 0,25° + cycle GFS (`weather_pipeline`). Conversion **1 m/s = 1,943844 kn**. Vent et vagues : direction **« de »** \(\mathrm{atan2}(-u,-v)\). Courant : **« vers »** \(\mathrm{atan2}(u_o,v_o)\) ; \(u_o=1,\,v_o=0\to 90°\). Cardinaux 16 rumbs.
- **Unités.** kn (horloge / cube) ; la popup montre aussi m/s Copernicus pour le courant (`speed_ms`).
- **Où.** Loaders `hindcast.py`, `copernicus/getWind.py`, `getCurrent.py`, `getWave.py` (VMDR déjà « de »), `forecast_cube.py`, `saildocs.knots_from_uv`. Cache : `weather_pipeline.py` (ne convertit pas). UI : `satelliteMet.js`, i18n « depuis » / « vers ».
- **Source.** Copernicus / OMM [16][17]. 1 kn = 1 852 m/h.
- **Test.** `test_weather_pipeline.py` (unités + conventions) ; `satelliteMet.test.js` / `getCardinalDirection.test.js` (16 rumbs). `test_uo_east_vo_zero_current_to_90` (C2).
- **Écarts notés (non corrigés).** (1) Repli `_sim_wind` / `_sim_current` dans `main.py` multiplie par **1,944**. (2) La constante 1,943844 tronque \(3600/1852=1{,}94384449\ldots\) (~5×10⁻⁷).
- **Verdict.** ✔ (unités des loaders) / ✔ (conventions « de » / « vers »)

## 21. Isochrones (conseil de route)

- **Formule.** Isochrones modifiées (Hagiwara). Pas 3 h au large, 1 h à moins de 60 nm d’une côte. Caps tous les 10°. Limites d’allure 40°–170° TWA (conseil seulement). Polaire × 0,85 × vagues + courant.
- **Unités.** h, °, nm.
- **Où.** `isochrone.py` `ISOCHRONE_STEP_*`, `isochrone_time_step_h`.
- **Source.** LuckGrib / littérature [6][7][18]. C4.
- **Test.** `test_isochrone_leg.py` (pas 1 h côtier / 3 h large ; antiméridien existant).
- **Verdict.** ≈ (caps 5° près de l’arrivée : non fait)

## 22. Longitude repliée

- **Formule.** \(\mathrm{wrapLon}=((lon+540)\bmod 360)-180\) (implémenté par boucles ±360). `unwrapPath` pour peindre le Pacifique.
- **Unités.** Degrés.
- **Où.** `geo.js` `wrapLon` / `unwrapPath` ; `route_engine.wrap_lon` ; `weather_pipeline.wrap_lon`.
- **Source.** searoute attend \([-180;180]\) [19]. Lot S.
- **Test.** `geo.test.js` (SF 236,84° → −123,16°) ; `test_route_engine.py` `test_wrap_lon_unfolded_san_francisco`.
- **Verdict.** ✔ côté wrap ; rester vigilant sur les lon dépliées client (lot S)

## 23. Échelle du replay

- **Formule.** `replayScale` : 1 s d’écran / jour d’expédition (défaut). Film : cible **150 s** (`FILM_TARGET_SECONDS`), calibré au prorata des caractères.
- **Unités.** s / jour ; s de film.
- **Où.** `src/engine/replay.js`.
- **Source.** Plan film F1 (150 s).
- **Test.** `replay.test.js` (`replayScale` monotone ; plan à 150 s).
- **Verdict.** ≈ (les deux échelles coexistent)

## 24. Revue de plan (`sailNm`, saisons)

- **Formule.** Distances de mer et saisons lues sur l’horloge (`sailNm`), pas sur un compteur de sommets. Corrigé lot K.
- **Unités.** nm, mois.
- **Où.** `plan_review.py`.
- **Source.** Lot K.
- **Test.** `test_plan_review.py`.
- **Verdict.** ✔

## 25. Distance perle ↔ route (`cumNm` des perles)

- **Formule.** `sample_route_nm` : perles le long de `cumNm` / `sailNm` mer (la terre Saint-Maur et le saut avion sont sautés). Corrigé lot K.
- **Unités.** nm.
- **Où.** `ici_warm.py` `sample_route_nm`.
- **Source.** Lot K.
- **Test.** `test_ici_warm.py` (première perle = premier point mer 128,8 ; monotone).
- **Verdict.** ✔

---

## Index des tests C5 (nouveaux)

| Fiche | Fichier |
|---|---|
| 1, 2 | `naviguide-simulator/src/utils/geo.test.js` |
| 3, 4 | `naviguide-simulator/src/engine/polar.parity.test.js` |
| 4 | `naviguide-simulator/server/tests/test_polar_parity.py` + `fixtures/polar_cases.json` |
| 8, 20 | `naviguide-simulator/server/tests/test_weather_pipeline.py` |

## Sources

Numéros = [`CALCULS_ETAT_DE_L_ART.md`](CALCULS_ETAT_DE_L_ART.md) § Sources.

# Les calculs du simulateur face à l'état de l'art — vérification calcul par calcul

Version **1.0** — 20 septembre 2026. Complète `docs/PLAN_AUDIT_CALCULS.md`
(§ 1, 25 lignes). Pour chaque calcul : ce que fait le code, ce que fait
l'état de l'art (logiciels de routage : qtVlm, LuckGrib, PredictWind,
TIMEZERO ; littérature ; conventions WMO / Copernicus), le verdict, et
l'action retenue. Sources numérotées en bas ; « (code) » = lu dans le dépôt.

Légende des verdicts : **✔ conforme** · **≈ acceptable, à documenter** ·
**✘ à corriger** · **? à vérifier** (le code ne dit pas encore).

| # | Calcul | Code | État de l'art | Verdict | Action |
|---|---|---|---|---|---|
| 1 | Distance | haversine, R = 3 440,065 nm (= 6 371,0088 km / 1,852) (code) | Sphère : erreur ≤ 0,3–0,5 % vs ellipsoïde WGS-84 ; Vincenty / Karney pour le millimètre ; la navigation utilise l'orthodromie pour la distance et souvent la loxodromie pour les caps de jambes [1][2] | **✔** | Aucune ; noter la borne d'erreur (≈ 120 nm sur 39 400 nm au pire, en pratique < 60 nm) dans le cahier |
| 2 | Cap initial | formule orthodromique (code) | idem ; les jambes courtes (≤ 60 nm) rendent orthodromie ≈ loxodromie | **✔** | Test cardinaux |
| 3 | TWA | \|cap − vent « de »\| replié sur [0 ; 180] (code) | définition standard ; le VPP/polaire est en **vent réel** (TWS/TWA), le vent GRIB est à 10 m, ce que supposent les polaires ORC/VPP [4] | **✔** | Documenter « vent 10 m, pas de correction de hauteur de mât » |
| 4 | Vitesse polaire | interpolation bilinéaire TWA × TWS, hors grille = bord (code) | Les routeurs interpolent la table (linéaire ou lissée) ; au-delà de la TWS max, LuckGrib garde la vitesse de la courbe la plus haute (« on réduit et on tient la vitesse ») — même convention que nous ; ils ajoutent des **limites d'allure** (pas de route à moins de ~35–45° du vent, ni plein arrière) et un **facteur d'efficacité** pour la croisière (typ. 70–90 % de la polaire) [4][5] | **≈** | Ajouter `POLAR_EFFICIENCY` (défaut 0,85, documenté) et les limites d'allure (près ≥ 40° TWA, portant ≤ 170°) ; en Suivre/Simulation la route est imposée, la limite ne sert qu'au conseil de route |
| 5 | Repli sans polaire | 0,45 × vent, borné [4 ; 11] kn (code) | Pas de standard ; les routeurs refusent de router sans polaire ou prennent un modèle de bateau du catalogue [4] | **≈** | Ne l'utiliser que sans polaire ; `basis: "fallback"` visible |
| 6 | Intégration temps | `dt = d / v`, vent au **début** du pas, au **milieu** du segment (code) | Isochrones : pas de 1–3 h, vent lu à l'instant du pas ; équivalent d'Euler explicite ; correct si le pas est court devant l'évolution du vent [6][7] | **≈** | Pas ≤ 30 nm / 1 h ; vent lu à mi-pas (méthode du point milieu) — lot C2 |
| 7 | Pénalité de mer | Hs ≥ 2,5 m → temps × 3, discontinu (code) | PredictWind : **polaire de vagues** = facteur de performance (0–100 %) fonction de Hs, de l'angle relatif de la houle et de la TWS, continu ; qtVlm : polaires de vagues aussi ; « manuelle » = table Hs × angle [5][8] | **✘** | Remplacer par un facteur multiplicatif continu : `v × f(Hs, angle)`, f = 1 jusqu'à 1,5 m, décroît linéairement jusqu'à 0,6 à 4 m par mer de face, 0,85 par mer arrière ; documenter dans `REGLES_PARAMETRES.md` — lot C4 |
| 8 | Courant | transporté, non additionné (code) | **SOG = vecteur bateau (STW) + vecteur courant** ; c'est la base de toute navigation (set and drift) et de tous les routeurs ; la dérive due au vent (leeway) est un second ordre souvent négligé en routage [9][10] | **✘** | Addition vectorielle projetée sur la route ; leeway ignoré et dit — lot C4 |
| 9 | Régimes de vent | prévision 0–7 j **depuis t0**, fondu 7–10 j, climatologie (code) | Skill déterministe utile ≈ 7 j sur les champs de surface ; les ensembles gardent du signal à 10–15 j ; trajectoires de dépressions ≈ 3–5 j ; le fondu vers la climatologie est une pratique courante de « departure planning » [11][12] | **✘** (référence t0) / **≈** (principe) | Fondu relatif à **maintenant** ; passé = hindcast ; option : ensembles (Open-Meteo Ensemble API) pour un ETA probabiliste — lot C2 |
| 10 | Climatologie | moyenne mensuelle + direction dominante (code) | Les pilot charts sont des **roses de fréquence** ; la vitesse polaire étant non linéaire, le temps à la vitesse moyenne ≠ moyenne des temps (inégalité de Jensen) ; les outils sérieux échantillonnent la distribution (ex. 11 ans d'ERA5 chez Sail Crossings) [13] | **✘** | Échantillonner la rose (p25 / p50 / p75 ou 3 tirages) et moyenner les temps — lot C4 |
| 11 | Échantillon à un instant | interpolation linéaire entre sommets ; vitesse = celle du segment ; à quai = jambe (code) | — | **≈** (**✘** à quai) | P2 (0 à quai) ; après C2 la vitesse du pas courant est la dérivée |
| 12 | Vitesse « mesurée » client | polaire × GRIB interpolé (code) | Une seule cinématique : la vitesse affichée est celle qui déplace le bateau | **✘** | Une seule vitesse — lot C3 |
| 13 | Vitesse de planification | polaire × vent, plancher `PLANNING_MIN_KN` (code) | idem 4 | **✔** | Appliquer aussi `POLAR_EFFICIENCY` |
| 14 | Horizons / anticipation | distance / vitesse planifiée (code) | — | **✔** | Test bornes |
| 15 | Jours à quai | 0 (Saint-Maur), 3 défaut, table (code) | Convention du projet | **≈** | Table par escale, source (programme de l'expédition) |
| 16 | Tronçon route / saut avion | 4 h / 8 h (code) | Convention | **≈** | Documenter |
| 17 | Résumé de l'expédition | segments du routeur (code) | — | **✘** | Étapes entre escales — lot C1 |
| 18 | `filmNm` vs `cumNm` | distance film sans le saut avion (code) | — | **≈** | Info-bulle |
| 19 | Événements météo | ≥ 34 kn ou Hs ≥ 3,5 m (code) | Beaufort 8 « coup de vent » = 34–40 kn [14] ; code WMO d'état de la mer : 5 « forte » 2,5–4 m, 6 « très forte » 4–6 m [15] | **✔** (34 kn) / **≈** (3,5 m) | Garder 34 kn ; aligner la mer sur le code WMO : événement « mer forte » ≥ 2,5 m **durable** (≥ 6 h), « très forte » ≥ 4 m ; ajouter durée et max — plan film F2 |
| 20 | Composite satellite (popup) | Copernicus ; conversion m/s → kn × 1,943 844 dans le cube (code) ; conventions de direction non lues | 1 kn = 1 852 m/h exactement, 1 m/s = 1,943 844 kn ✔ ; **vent et vagues : direction « d'où ça vient »** (météorologique) ; **courant : direction « vers où ça va »** (océanographique, `uo`/`vo` est/nord → cap = atan2(uo, vo)) [16][17] | **✔** (unités) / **?** (conventions) | Test : `uo = 1, vo = 0` → courant **vers l'est (90°)** ; vagues et vent affichés « de » ; cardinaux sur 16 points |
| 21 | Isochrones | pas **6 h**, cap tous les **10°**, 72 secteurs d'élagage, 120 pas max, masque terre par corde (code) | Méthode des isochrones modifiée (Hagiwara 1989) = standard des routeurs voile (LuckGrib, TIMEZERO, qtVlm) ; pas de temps typiques **1–3 h**, caps tous les **5–10°**, élagage par secteurs ; incertitude météo traitée par ensembles [6][7][18] | **≈** (**✘** sur le pas) | Pas 3 h en haute mer, 1 h à moins de 60 nm d'une côte ; caps 10° → 5° près de l'arrivée ; `max_steps` en conséquence |
| 22 | Longitude repliée | [−180 ; 180] attendu par searoute ; client envoie parfois +360 (code) | Normalisation `((lon + 540) mod 360) − 180` avant tout appel externe ; **déplier** seulement pour dessiner une ligne qui traverse 180° (MapLibre/Leaflet) [19] | **✘** | Lot S ; un seul utilitaire `wrapLon` / `unwrapPath` |
| 23 | Échelle du replay | 1 s / jour (code) | — | **≈** | Remplacé par le film 150 s (plan film) |
| 24 | Revue de plan (`sailNm`, saisons) | corrigé lot K (code) | — | **✔** | — |
| 25 | `cumNm` des perles | corrigé lot K (code) | — | **✔** | — |

## Compléments issus des recherches

- **Hindcast** (lot C2) : ERA5 **sous-estime les vents forts en mer**
  (mise en évidence et correction proposée par Gandoin & Garza, 2024 ; biais
  documenté en Atlantique par Campos et al., 2022) et **sous-estime Hs**
  (Bessonova et al., 2025) [20][21][22]. Décision du porteur : **toutes les
  sources ensemble** — Open-Meteo (archives de prévision GFS 0,25° / IFS /
  ICON, réanalyse ERA5, Marine API) **et** Copernicus Marine (vent L4
  diffusiomètres `WIND_GLO_PHY_L4_NRT_012_004`, vagues
  `GLOBAL_ANALYSISFORECAST_WAV_001_027`, courants
  `GLOBAL_ANALYSISFORECAST_PHY_001_024`) —, fusionnées par **médiane** par
  variable et par heure, avec le nombre de sources et leur écart conservés et
  affichés ; **correction des vents forts** sur ERA5 seulement (facteur 1,05
  au-dessus de 15 m/s, paramétré, cité). La médiane de plusieurs produits
  indépendants est la pratique des hindcasts multi-modèles ; l'écart entre
  sources devient une mesure honnête d'incertitude.
- **Ensembles** : pour l'ETA au-delà de 7 jours, la bonne pratique est
  probabiliste (spread d'ensemble) ; Open-Meteo expose GEFS/IFS ENS. Option
  après C2 : « arrivée entre le 12 et le 15 (p10–p90) ».
- **Polaire de croisière** : les routeurs appliquent un facteur d'efficacité
  (équipage réduit, voiles de croisière, nuit) ; sans lui l'horloge est
  optimiste de 10–20 %.

## Sources

1. movable-type.co.uk, « Vincenty solutions of geodesics on the ellipsoid » — le modèle sphérique (haversine) est précis à ≈ 0,3 %.
2. gis.stackexchange.com, « Difference between Vincenty and great-circle distance » — gain ≈ 0,17 % au point testé, temps de calcul doublé ; coordinately.org, « Great-Circle Distance » — haversine ≤ 0,5 % avec R = 6 371 008,8 m.
3. (réservé)
4. routing.luckgrib.com, « Performance and Polars » — interpolation de la table, vitesse 0 à 0° TWA, limites d'allure au près / au portant, au-delà de la TWS max la vitesse de la courbe la plus haute est conservée.
5. help.predictwind.com, « Weather Routing for Sailboats — Using Wave Polars » (mis à jour 20 sept. 2026) — polaire de vagues : facteur de performance par Hs × angle × TWS ; sorties RMS roll, accélération verticale, slamming ; pour un catamaran le slamming est mesuré à la nacelle.
6. Zis, Psaraftis, Ding (2020), « Ship weather routing: a taxonomy and survey », DTU — méthode des isochrones modifiée (Hagiwara 1989), programmation dynamique, calcul des variations.
7. routing.luckgrib.com, « LuckGrib isochrones » ; Szłapczyńska (2007), « Adopted isochrones method improving ship safety in weather routing » ; Charalambopoulos & Nearchou (2026), « A decision support system for effective ship weather routing », *Ships and Offshore Structures*.
8. meltemus.com (qtVlm), forum « Wave polars? » (28 juil. 2026) — qtVlm gère des polaires de vagues pour les simulations.
9. cruisersforum.com, « SOG or STW for course to steer » — COG/SOG = somme vectorielle courant + vitesse surface + dérive.
10. Zhou et al. (2020), « Impacts of wind and current on ship behavior in ports », *Ocean Engineering* — pour les petits navires, le courant pèse plus sur la SOG que le vent ; le vent agit surtout sur la dérive.
11. AMS 2016, « The Forecast Skill Horizon » — horizon de skill 16–23 j pour les champs de grande échelle ; jua.ai (2026), guide ENS vs déterministe — trajectoires de dépressions en mer du Nord prévisibles 3–5 j.
12. Open-Meteo, Ensemble API (GEFS, IFS ENS) ; Historical Forecast API ; Historical Weather API (ERA5) ; Marine API.
13. sailcrossings.com, « Pilot Charts & Ocean Passage Weather » — roses interactives et simulation météo de route bâties sur 11 ans d'ERA5 ; documentation des routeing charts (roses de fréquence).
14. weather.gov, « Beaufort Scale » — force 8 (gale) : 34–40 kn.
15. Wikipedia, « Sea state » (code WMO) — 5 : 2,5–4 m « rough », 6 : 4–6 m « very rough » ; WMO Community, « Marine FAQ ».
16. help.marine.copernicus.eu, « Which is the direction conventions of currents, wave and wind parameters in Copernicus Marine products » (5 juin 2025) ; api.met.no, Oceanforecast — le courant suit la convention océanographique (« vers »).
17. Définition du mille marin (1 852 m) et du nœud : 1 m/s = 1,943 844 kn.
18. Ukrainian/Polish transnav (2012), « Development of a 3D dynamic programming method for weather routing » — pas de temps et grilles des méthodes isochrones.
19. MapLibre GL JS, « Display line that crosses 180th meridian » ; Leaflet/StackOverflow, « Wrapping lines across the antimeridian ».
20. Gandoin & Garza (2024), « Underestimation of strong wind speeds offshore in ERA5: evidence, discussion and correction », *Wind Energy Science* 9, 1727.
21. Campos et al. (2022), « Assessment and calibration of ERA5 severe winds in the Atlantic Ocean using satellite data », *Remote Sensing* 14, 4918.
22. Bessonova et al. (2025), « Global evaluation of wave data reanalysis: comparison of the ERA5 dataset to buoy observations », *Applied Ocean Research* ; Sharmar & Markina (2020), validation des hindcasts de vagues (ERA5, MERRA2, CFSRv2).

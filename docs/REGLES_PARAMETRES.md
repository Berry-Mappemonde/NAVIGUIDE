# Rules and parameters — principle, catalogue, snapshot per run

The specifications (Projects, Formalities, Marinas) list **numbers**.
Many were hard-coded in Python, chosen once, without saying *why*.
This document fixes **how we are allowed to set a number**, how we
**vary** it from one run to another, and how we **record** what was
chosen.

Machine catalogue: `backend/data/run_rules.json`.
Engine: `backend/app/core/run_rules.py`.
API: `GET /api/run-rules?mode=projects|formalities|marinas|amp|science|climatology`.

---

## 1. The principle

**A number is not an opinion.**

It belongs to **one** of these four families. If it belongs to none,
it has no right to be in the code.

| Family | Meaning | Do we vary it? |
|--------|---------|----------------|
| **Law** | Business contract (no snap, no purge, official sources only, Noonsite out of `source_urls`) | No. We record it. We do not override it. |
| **Geometry** | Distance derived from a physical phenomenon (quay, harbour, day at sea, walk customs→marina) | Yes, **within the interval** where it is still the same phenomenon. |
| **Score** | Classifier or confidence threshold | Yes, but the target is a **calibration** on a labelled set (Gold, ROC), not a new number by feel. |
| **Budget** | Quota, timeout, concurrency, dollars | Yes. It is an operator choice. Always recorded. |

### How we set the default and the interval

1. **Name the phenomenon.** “Hinterland of a harbour-town”, not “15 km because it worked”.
2. **Anchor the default** on a measurement (0.02° VLIZ → 2.2 km; 10 min walk → 800 m; 4–5 h at 5–6 knots → 25 NM).
3. **Set the interval** as the range where *we are still talking about the same thing*.
   - Below: we discard real cases (Cassis at 2.3 km if the sliver falls to 2.0).
   - Above: we accept something else (a headquarters in Washington if `max_inland_km` = 80).
4. **A run does not leave the interval.** Leaving = changing the rule, therefore changing the specification first.

The interval is the **scientific claim**. The default is the **operating point**.

---

## 2. How we vary, and how we record

Three layers, never a secret in the snapshot:

```
run override  >  profile (cdc_default | strict | recall)  >  Mongo settings  >  catalogue default
```

At the start of a run (Projects, Formalities, Marinas / anchorage build):

1. We resolve every rule of the mode (+ `shared`).
2. We write `params.rules`: `hash`, `profile`, `chosen[id].{value, source, unit, principle}`, `overrides`.
3. We **bind** the snapshot in the async context: `get_rule("formalities.eez_sliver_km")` reads this run, not the file.
4. On resume, we **keep** the original snapshot (like the `git_sha`).

Comparing two runs = comparing `params.rules.hash` and the `source=override|profile|settings|catalog` detail.

### API

```http
GET  /api/run-rules
GET  /api/run-rules?mode=formalities&profile=strict
POST /api/poe/runs          { "profile": "recall", "rules": { "formalities.eez_sliver_km": 3.5 } }
POST /api/projects/runs     { "mode": "test", "profile": "strict" }
POST /api/marinas/build     { "profile": "cdc_default", "corridor_radius_nm": 20 }
```

An override outside the interval, a **law** rule, or an unknown id → **400**.

### Profiles

| Profile | Idea |
|---------|------|
| `cdc_default` | Operating point of the specifications. |
| `strict` | Low recall: we discard more, we dare to publish. |
| `recall` | High recall: we keep more for **review**, not for the public map. |

Do not publish a `recall` run as if it were `strict`. The profile is part of the snapshot.

---

## 3. Inventory by mode (specification + code)

The values below are the **defaults**. The detail (principle, interval, file) is in the JSON.

### 3.1 à 3.6 — catalogue Blue Intelligence

Ces sections vivent dans le dépôt Blue Intelligence, fichier `backend/data/run_rules.json` (et `docs/REGLES_PARAMETRES.md` de ce dépôt). On ne les recopie pas ici.

### 3.7 Horloge à trois régimes — hindcast / prévision / climatologie (lot C2)

`docs/audits/CALCULS_ETAT_DE_L_ART.md`. Décision du porteur : **toutes** les sources (Open-Meteo + Copernicus) sont lues ensemble, fusionnées par **médiane**. Un champ sans source reste vide (jamais inventé). Identifiants `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` déjà lus par `server/main.py`.

| Id | Default | Family | Phenomenon / anchor |
|----|---------|--------|---------------------|
| `hindcast.era5_strong_wind_factor` | 1.05 | geometry | Correction vents forts ERA5 **seulement** au-dessus de 15 m/s, **seulement** ERA5 (Open-Meteo Archive / ERA5 sous-estime le vent fort ; facteur revue lot C2). |
| `hindcast.era5_strong_wind_ms` | 15 m/s | geometry | Seuil de la correction ERA5. |
| `hindcast.ms_to_kn` | 1.943844 | **law** | 1 m/s → kn (mille international 1852 m). |
| `hindcast.pad_days` | 2 j | budget | Fenêtre CMEMS ±2 j autour du jour demandé (1 subset / point / dataset). |
| `hindcast.point_decimals` | 3 | budget | Clé de cache (point, produit, jour) — jamais retéléchargé. |
| `hindcast.fetch_timeout_s` | 20 s | budget | Timeout HTTP Open-Meteo. |
| `hindcast.fusion` | médiane | **law** | Par variable et par heure ; `spread` = max − min ; source en panne = absente. |
| `hindcast.om_forecast` | Historical Forecast API | **law** | `historical-forecast-api.open-meteo.com/v1/forecast`, `hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m`, `wind_speed_unit=kn`. |
| `hindcast.om_era5` | Historical Weather / ERA5 | **law** | `archive-api.open-meteo.com/v1/archive`, mêmes variables vent. |
| `hindcast.om_marine` | Marine API | **law** | `marine-api.open-meteo.com/v1/marine` ; courant optionnel : si 400, vagues seules, courant vide. |
| `hindcast.cmems_wind` | `WIND_GLO_PHY_L4_NRT_012_004` | **law** | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` ; `eastward_wind`, `northward_wind` → kn × 1,943844, direction « de ». |
| `hindcast.cmems_wave` | `GLOBAL_ANALYSISFORECAST_WAV_001_027` | **law** | `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i` ; `VHM0`, `VMDR` « de », `VTM02`. |
| `hindcast.cmems_phy` | `GLOBAL_ANALYSISFORECAST_PHY_001_024` | **law** | `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` ; `uo`, `vo` → kn, direction « vers » = atan2(uo, vo) ; uo=1, vo=0 → 90°. |
| `clock.max_step_nm` | 30 nm | geometry | Pas d'intégration plus long (lot C2 / A3 : vent lu à mi-pas). |
| `clock.max_step_h` | 1 h | geometry | Idem, sous-découpage temporel. |
| `forecast.full_hours` | 7 × 24 h | **law** | Prévision pleine **depuis maintenant** (heure du calcul), plus depuis `t0`. |
| `forecast.blend_end_hours` | 10 × 24 h | **law** | Fondu linéaire 7 → 10 j depuis maintenant, puis climatologie. |
| `clock.regimes` | hindcast / forecast / climatology | **law** | Passé = hindcast ; 0–7 j = prévision ; au-delà = climatologie. Horloge officielle `kind: climatology` jusqu'au premier fill (~40 min). |

### 3.8 Mer, polaire et isochrones — lot C4

`docs/audits/CALCULS_ETAT_DE_L_ART.md` lignes 4, 7, 8, 10, 21. Aucun chiffre n'est produit par un LLM.

| Id | Default | Family | Phenomenon / anchor |
|----|---------|--------|---------------------|
| `polar.efficiency` | 0,85 | geometry | Part de croisière de la table polaire (équipage réduit, voiles de croisière, nuit). Variable d'environnement `POLAR_EFFICIENCY`. État de l'art : 70–90 % [4][5]. Appliqué horloge, planification, conseil de route. |
| `polar.twa_min_deg` | 40° | geometry | Limite d'allure au près — conseil de route seulement (la route imposée en Suivre / Simulation n'est pas coupée). LuckGrib ~35–45° [4]. |
| `polar.twa_max_deg` | 170° | geometry | Limite d'allure au portant — conseil de route seulement. Plein arrière rarement tenu en croisière [4]. |
| `wave.polar_hs_flat_m` | 1,5 m | geometry | En dessous : facteur 1 (mer peu pénalisante pour un catamaran de voyage). |
| `wave.polar_hs_full_m` | 4,0 m | geometry | Mer « très forte » (code WMO 6) : facteur saturé. PredictWind / qtVlm : polaire de vagues continue Hs × angle [5][8]. |
| `wave.polar_head` | 0,6 | geometry | Facteur à 4 m, mer de face (houle « de » dans le cap). |
| `wave.polar_follow` | 0,85 | geometry | Facteur à 4 m, mer arrière. Entre 1,5 et 4 m : interpolation linéaire ; au-delà : plafonné. Remplace `WAVE_NOGO_DT_FACTOR` (×3 dès 2,5 m, discontinu). |
| `wave.nogo_m` | 2,5 m | geometry | Seuil d'interdiction isochrone / ordres skipper (WMO mer forte). Inchangé. |
| `current.sog` | STW + projection | **law** | SOG = projection sur la route de (vecteur polaire + vecteur courant `uo`/`vo`). Leeway ignoré (second ordre) [9][10]. Convention : courant « vers », `uo=1, vo=0` → 90°. |
| `current.ms_to_kn` | 1,943844 | **law** | Même constante que `hindcast.ms_to_kn`. |
| `climo.rose_draws` | p25 / p50 / p75 | **law** | Trois tirages de la rose ; le temps de mer est la moyenne des trois temps (inégalité de Jensen : ≠ temps à la moyenne) [13]. |
| `isochrone.step_offshore_h` | 3 h | geometry | Pas en haute mer. État de l'art 1–3 h [6][7][18]. Était 6 h. |
| `isochrone.step_coast_h` | 1 h | geometry | Pas à moins de 60 nm d'une côte (`is_path_clear` sur 12 rayons). |
| `isochrone.coast_nm` | 60 nm | geometry | Distance à la terre qui bascule le pas. |
| `isochrone.max_hours` | 720 h | budget | Même horizon qu'avant (120 × 6 h) ; `max_steps` = plafond / pas min. |
| `isochrone.heading_step_deg` | 10° | geometry | Caps tous les 10° (5° près de l'arrivée : non fait, hors lot). |
| `clock.min_knots` | 0,5 kn | geometry | Plancher SOG (calme / courant contraire). Documenté A7 ; table des jours à quai → lot C7. |

### 3.9 Conventions horloge et repli — lot C7

`docs/audits/CALCULS_ETAT_DE_L_ART.md` lignes 5, 15, 16, 18. Aucune valeur n'est changée : la table reprend les constantes déjà dans le code. Source écrite : **programme Berry-Mappemonde 2026** (`server/data/port_days.json`).

| Id | Default | Family | Phenomenon / anchor |
|----|---------|--------|---------------------|
| `clock.land_hours` | 4 h | convention | `LAND_CALENDAR_HOURS` — tronçon route Saint-Maur → La Rochelle. A7 / état de l'art l. 16. |
| `clock.air_hours` | 8 h | convention | `AIR_CALENDAR_HOURS` — saut avion (durée calendaire, pas une polaire). A7 / l. 16. |
| `clock.min_knots` | 0,5 kn | geometry | `MIN_KNOTS` — plancher SOG (déjà § 3.8). A7. |
| `clock.port_days.default` | 3 j | convention | `DEFAULT_BMAP_PORT_DAYS` / `port_days.json` `default`. Programme 2026. |
| `clock.port_days.Saint-Maur` | 0 j | convention | Départ, pas d'escale. Même table. |
| `clock.port_days.Halifax` | 1 j | convention | Valeur déjà dans `port_days_for` ; inchangée. |
| `clock.port_days.*` | 3 j | convention | Autres escales officielles (Ajaccio, Fort-de-France, …) — défaut historique. |
| `clock.speed_basis` | `polar` \| `fallback` | **law** | Chaque sommet d'horloge. `boat_speed_from_wind` seulement si la polaire est absente. |
| `clock.fallback_speed` | 0,45 × TWS, borné [4 ; 11] kn | convention | Repli interne (A6). Formule inchangée. Les routeurs refusent de router sans polaire [4]. |
| `polar.efficiency` | 0,85 | geometry | Déjà § 3.8 ; exposé dans `GET /voyage/official` `params.polarEfficiency` s'il est présent. |
| `film.air_excluded` | — | convention | Distance affichée / film : saut avion exclu (`cumNm` / `sailNm`). L'axe `filmCum` avance de 80 nm d'animation par saut (`AIR_FILM_NM`) ; info-bulle UI. L. 18. |

`GET /voyage/official` renvoie `params: { landHours, airHours, minKnots, portDaysDefault, polarEfficiency }`.

### 3.10 ETA probabiliste — ensembles Open-Meteo (lot C6)

`docs/audits/CALCULS_ETAT_DE_L_ART.md` ligne 9 et complément « Ensembles ». Au-delà de 7 jours, l'arrivée n'est pas une date unique : p10 / p50 / p90 des membres. Sans ensemble, rien n'est affiché (jamais inventé).

| Id | Default | Family | Phenomenon / anchor |
|----|---------|--------|---------------------|
| `ensemble.url` | `ensemble-api.open-meteo.com/v1/ensemble` | **law** | Open-Meteo Ensemble API, sans clé, usage non commercial. |
| `ensemble.models` | `gfs_seamless,ecmwf_ifs025` | **law** | GEFS seamless (~31 membres) + IFS ENS 0,25° (~51 membres). Vent 10 m, nœuds. |
| `ensemble.hourly` | `wind_speed_10m,wind_direction_10m` | **law** | Membres en colonnes `wind_speed_10m_member01`… (préfixe modèle si les deux sont demandés). |
| `ensemble.forecast_days` | 15 | **law** | Horizon d'ensemble ; au-delà : climatologie médiane (atlas, rose p25/p50/p75 du lot C4). |
| `ensemble.cache_ttl_s` | 6 h | budget | Cache SQLite `pearl_store.kv` ns `ensemble` (point + résultat). Jamais retéléchargé avant expiration. |
| `ensemble.point_nm` | 60 nm | geometry | Une requête par point de la jambe restante ; pas ≤ 60 nm. |
| `ensemble.quantiles` | p10 / p50 / p90 | **law** | Quantiles empiriques des dates d'arrivée (interpolation (n−1)·q). `members` = arrivées valides. |
| `ensemble.physics` | polaire × 0,85 + courant + vagues | **law** | Même cinématique que l'horloge C4 (`POLAR_EFFICIENCY`, SOG, polaire de vagues). |

`GET /voyage/official/eta?stop=<nom>` → `{p10, p50, p90, members, source, computedAt}`. Panne ou escale inconnue / déjà atteinte → `members: 0`, dates vides.

---

## 4. Other ideas (beyond the snapshot)

1. **A/B sweep.** Same seeds, two profiles (`strict` vs `recall`). We compare `listing-control.coverage`, `unlocated`, `confirmed`. The hash says what changed.
2. **Gold calibration, not habit.** `gatekeeper_*`, `min_marine_score`, `listing_*`, `osm_confidence_hi` have no physical phenomenon. As soon as a Gold exists (Projects spec phase D), we set the threshold on a precision-recall curve (e.g. precision ≥ 0.95 for `accept`).
3. **Sensitivity analysis.** A script that replays `classify_poe_point` / `catalog_is_sufficient` / `site_publishable` on the stock while sliding *one* parameter within its interval. We only vary what **moves** the counts.
4. **Remove `max_coast_km`.** Remnant of the snap. The Settings UI still shows it; the Projects pipeline must no longer use it.
5. **A Marinas specification.** The 25 NM corridor has no specification. This document gives the phenomenon; a route specification would freeze it (stopover vs corridor vs anchorage).
6. **Never vary a law “to see”.** If we want to test a bounded snap, it is no longer Blue Intelligence v2.
7. **The hash in the markdown report.** A `rules: abc123 / profile=strict` line at the top of `GET …/report` so a human can compare without opening Mongo.
8. **Settings = operator default, not truth.** Changing 15 → 12 in the UI changes *upcoming* runs, not old ones. That is intended.

---

## 5. Acceptance tests

```bash
cd backend && python3 -m pytest tests/test_run_rules.py tests/test_run_fingerprint.py tests/test_project_runs.py -q
```

- The catalogue loads and each default (except `loi` / bool) is **inside** its interval.
- The Formalities geometry / dedup / WPI / marina-control defaults **equal** the current Python constants (anti-drift).
- An override outside the interval or a law → `RuleError`.
- `open_run` writes `params.rules.hash` and `chosen`.
- `get_rule` + bind varies `catalog_is_sufficient` (3 → 5 ports).

---

*Any change to a number: first the phenomenon and the interval here / in the JSON, then the code.*

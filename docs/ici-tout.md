# `ici()` : toutes les familles au point bateau

Sac moteur (~30 nm), pas un dump GeoJSON monde. Branche `cursor/ici-toutes-couches-3550`, PR #164. `kind` honnête : **observation ≠ climatology ≠ forecast**. Produit absent = `null` + `source` / `reason`, jamais d’invention.

`main` #163 (horloge / chargement) est fusionné dans la branche (force-push interdit).

## Branché

| Famille | Accès | `kind` | Rempli si |
|--------|--------|--------|-----------|
| ZEE / PoE / AMP / projets / marinas / capitaineries / WPI / Science / GEBCO | déjà sur `main` | — | BI / MarineRegions / WPI / OpenTopo |
| AMP `visit_url` ≠ `manager_url` | export AMP | — | les deux URLs sont dans le GeoJSON |
| Mouillages OSM | `GET /api/anchorages` | — | dump BI présent |
| AtoN | NOAA `GET /api/noaa/aids` (US) + Overpass seamark | — | ENC US ou nœud OSM |
| Satellites | CDSE STAC Sentinel-2 L2A au bbox bateau + lien Browser ; `http_status` + `url` | **observation** | le catalogue répond 200 |
| EMODnet point | `GET /api/depth` ou `depth_sample` ; WMS GetFeatureInfo fonds / câbles | **observation** | l’API / le WMS répond |
| Météo vent / vague | Open-Meteo GFS + GFS-Wave (`current`) | **forecast** | Open-Meteo répond |
| **Courant RTOFS** | NOMADS NetCDF `rtofs_glo_2ds_n000_prog.nc` (HTTP Range + h5py) | **forecast** | le modèle répond au point |
| Climatologie | `/climatology/point` + `/crossings` | **climatology** | atlas BI |
| Rose 8 secteurs / calme / coup de vent | `wind_atlas` de l’atlas | climatology | snapshot `stat=rose` |
| Direction de courant (atlas) | `current.direction_to_deg` | climatology | atlas courant |
| `cyclone.nearby` | bloc cyclone du point | climatology | IBTrACS |
| Review / Gold | `GET /api/review/fiche` ZEE + AMP | — | fiche 200 ; sinon 401 = admin |

Le briefing dit **une phrase par famille**, avec `kind` et période / DOI pour climatologie, date pour la scène satellite, nœuds RTOFS si le modèle a répondu.

## Campagne live (2026-09-16) — pas La Rochelle seule

| Point | RTOFS | Sentinel L2A | Autre |
|-------|-------|--------------|--------|
| US Chesapeake 37°N 76°W | **oui** 0,12 kn / 262° (`kind: forecast`) | **oui** `S2B_…T18SUF` 2026-09-11, 3,9 % nuages, STAC 200 | AtoN NOAA (bouées Chesapeake Channel) |
| Pacifique / antiméridien 0° 179,8°E | **oui** 2,34 kn / 88,5° | bbox trop large → 400 (corrigé : clamp ±180) ; catalogue **pas muet** | hors ENC US |
| Europe La Rochelle 46,15°N 1,16°W | **oui** 0,05 kn / 133° | **oui** `S2A_…T30TXR` 2026-09-14, **0 %** nuages | EMODnet DTM 2,4 m + fonds Ifremer/BRGM |
| Mer Rouge 24°N 36,5°E (mer claire) | **oui** 0,38 kn | **oui** `S2C_…T37QBG` 2026-09-08, **0 %** nuages | — |
| Canaries 28,1°N 16,7°W | **oui** 0,20 kn | **oui** `S2A_…T28RCS` 2026-09-03, 0,06 % | — |
| Haute mer 0°N 30°W | **oui** 0,58 kn / 294° | scène océan 2026-07-07, 0,06 % | Review `no_entity` |

Produit RTOFS : `https://nomads.ncep.noaa.gov/pub/data/nccf/com/rtofs/prod/rtofs.20260916/rtofs_glo_2ds_n000_prog.nc`. Plus de `rtofs_not_ingested`.

## Sentinel — catalogue interrogé pour de vrai

- Collection : `GET https://stac.dataspace.copernicus.eu/v1/collections/sentinel-2-l2a` → **200**, id `sentinel-2-l2a`.
- Search : `POST https://stac.dataspace.copernicus.eu/v1/search` → **200** + scènes L2A (Chesapeake, La Rochelle, Mer Rouge, Canaries, Atacama).
- Meilleure scène « mer claire » : **Mer Rouge 24°N 36,5°E**, `S2C_MSIL2A_20260908T080601_N0512_R078_T37QBG_20260908T115314`, 0 % nuages. La Rochelle aussi 0 %.
- 200 + features vides = `no_scene_in_bbox` (catalogue vivant). Muet seulement si status ≥ 400 sur **tous** les essais, avec `http_status` + URL.

## Review / Gold — verdict (API prod réelle, sans cookie)

**Admin obligatoire : oui.** Ce n’est pas « pas de ZEE ».

| Cas | ZEE | `GET /api/review/fiche` sans cookie | Ce que `ici()` voit |
|-----|-----|--------------------------------------|---------------------|
| Gold FR La Rochelle | MRGID **5677** (France métropolitaine) | **401** `Admin key required` — `https://blueintelligence.online/api/review/fiche?kind=eez&id=5677` | `review.reason=review_requires_admin`, `review.zee=null`, `http_status=401`. `zee.gold` reste le flag PoE (autre notion). |
| ZEE non-FR Norfolk | MRGID **8456** United States EEZ | **401** même détail — `…/fiche?kind=eez&id=8456` | identique : admin, pas « pas de ZEE » |
| Haute mer 0°N 30°W | pas de MRGID | **aucun appel** fiche | `review.reason=no_entity`, `zee=null` |

`GET /api/admin/check` sans clé → 401. Sans cookie / `X-Admin-Key`, `ici()` ne lit **jamais** `gold_on` / `gold_ready`.

## Reste `null` — et pourquoi

| Champ | Reason typique | Pourquoi ce n’est pas inventé |
|--------|----------------|------------------------------|
| `satellites.derived.coastline` / `sdb` / `intertidal` | `not_generated` | Pilotes ACOLITE / MNDWI / ICESat-2 hors VPS |
| `satellites.scene` | `no_scene_in_bbox` ou `cdse_stac_unavailable:<status>` | Aucune L2A, ou STAC down (status + URL) |
| `weather.current` | `off_grid` ou `rtofs_unavailable:*` | Fill HYCOM / terre, ou NOMADS mort — **plus** `rtofs_not_ingested` |
| `weather.wind` / `wave` | `openmeteo_unavailable:*` | GFS / GFS-Wave n’a pas répondu |
| `aton.nearby` | `outside_us_enc;no_osm_seamark` | NOAA ENC seulement aux US ; Overpass vide |
| `emodnet.*` | `no_feature_at_point` / `no_sample_at_point` | Couverture Europe ; océan ouvert |
| `review.*` | `review_requires_admin` / `no_entity` | File Review derrière admin en prod ; haute mer sans MRGID |

Tuiles OpenSeaMap, WMS peint, GRIB globe et sync Atlas : hors sujet. Pas de toucher à #139 / Hs compute / `sync-from-atlas`.

## Preuves

- Tests Python : `naviguide-simulator/server/tests/test_ici_engine.py` (29).
- Tests JS : `ici.test.js`, `iciBriefing.test.js`.
- Campagne : [`media/ici-tout-campagne.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-campagne.json)
- US + AtoN + RTOFS : [`media/ici-tout-us-aton.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-us-aton.json)
- Pacifique / antiméridien : [`media/ici-tout-pacifique-antimeridien.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-pacifique-antimeridien.json)
- Europe EMODnet : [`media/ici-tout-europe-emodnet.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-europe-emodnet.json)
- Haute mer RTOFS : [`media/ici-tout-haute-mer-rtofs.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-haute-mer-rtofs.json)
- Sentinel L2A : [`media/ici-tout-sentinel.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-sentinel.json)
- Review / Gold prod : [`media/ici-tout-review-gold.json`](/cursor/stores/bc-4aa592e7-0ecf-4131-b6a8-eae00e39f8b2/media/ici-tout-review-gold.json)

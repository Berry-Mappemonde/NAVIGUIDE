# Profil zoom molette — simulateur, 20 septembre 2026 (lot U)

Méthode : [PROFIL_BUILD_PROD_2026-09-19.md](./PROFIL_BUILD_PROD_2026-09-19.md) — `vite build` + `vite preview` (`PW_PORT=5199`), Playwright Chromium, CDP `Profiler.start` / `Profiler.stop` (échantillonnage 100 µs), `PerformanceObserver('longtask')`, écart max entre `requestAnimationFrame`. Vue Atlantique (20° N, 40° W, z=4). Chiffres lus dans `docs/audits/zoom-profile-*.json`.

L’observateur `longtask` n’a pas déclenché (aucune tâche JS > 50 ms — même constat que le profil du 19 sept.). L’écart de frame (`maxFrameGap`) vaut souvent 16,7 × n ms (vsync sauté) : ce n’est pas une longtask. La recette e2e affirme `maxLongTask < 50`.

## Avant (HEAD `feat/lot-c3-une-vitesse`, 10 s de molette)

Fichier : `docs/audits/zoom-profile-before.json` — 2026-09-21T00:53:45Z.

| Mesure | Valeur |
|---|---|
| Plus longue tâche (écart de frame) | **50,0 ms** |
| Tâches longues `longtask` | 0 |
| Temps JS échantillonné (travail) | 8 873 ms |
| Idle / program / GC | 1 233 ms |

Trois postes (temps propre, noms minifiés du bundle `index-CBW9E702.js`) :

| ms | Fonction | Lecture |
|---|---|---|
| 1 026 | `(anonymous)` | bundle app + Leaflet (handlers zoom / projection) |
| 936 | `sC` | composant React HUD (distance / étape) — re-rendu pendant le zoom |
| 626 | `sw` | React DOM (`update` hôte `div` / `span` / `svg`) |

Cohérent avec la cause racine du plan : `syncWaypoints` × copies-monde à chaque `moveend`, offsets à 120 ms, `viewportRevision` catalogue à chaque `zoomend`.

## Après (branche `perf/lot-u-zoom`)

### 10 s de molette

Relevé conservé ci-dessous (le JSON `zoom-profile-after.json` a ensuite été écrasé par la recette à 10 crans).

| Mesure | Valeur |
|---|---|
| Plus longue tâche (écart de frame) | **33,4 ms** |
| Tâches longues `longtask` | 0 |
| Temps JS échantillonné (travail) | 8 965 ms |
| Idle / program / GC | 1 219 ms |

Trois mêmes postes (`index-dSkZWhs-.js`) : `(anonymous)` 1 125 ms, `sC` 940 ms, `sw` 628 ms. Le CPU total sur 10 s reste du même ordre (Leaflet + React HUD tournent toujours) ; le gain est sur les **pics** : plus de frame à 50 ms.

### Recette (10 crans)

`docs/audits/zoom-profile-after.json` — 2026-09-21T00:55:24Z.

| Mesure | Valeur |
|---|---|
| Plus longue tâche | **33,4 ms** |
| `longtask` | 0 |
| Travail JS échantillonné | 1 365 ms |

## Décisions

1. Copies-monde des drapeaux seulement si la vue touche ±180° (`flagWorldLngsForView`).
2. Pas de recalcul d’offsets pendant `zoomanim` ; `zoomend` + 250 ms (`ZOOM_IDLE_MS`). `moveend` qui suit un zoom ne relance ni offsets ni `syncDynamicWorldCopies`.
3. `preferCanvas: true` sur la carte (polylignes) ; `divIcon` des drapeaux mis en cache ; tuiles fond + WMS ZEE en `updateWhenZooming: false` ; catalogues viewport après `zoomend` + 250 ms. `GET /ici` et le récit n’étaient déjà pas branchés sur `moveend` — contrat de test.

# Profil du build de prod — simulateur, 19 septembre 2026 (lot J)

Pourquoi : les chiffres du profil du 18 septembre venaient du serveur de
dev (React en mode développement, HMR, StrictMode qui double les rendus) et
**surestimaient React**. Avant de créer un Web Worker pour le moteur
d'événements, on mesure le build de prod.

## Protocole

- `vite build` (React production) servi par `vite preview` sur `:5175`, avec
  le même proxy API que le dev (`preview.proxy` ajouté à `vite.config.js`) —
  app complète : sac `ici()`, perles, cartes, récits.
- Chrome (webview Cursor), Simulation, Stop auto coupé, vitesse **normale**,
  départ de Saint-Maur, **60 s de lecture** (0 → 1 239 nm, j0 → j7).
- CDP `Profiler.start` / `Profiler.stop` sur les 60 s ; `performance.memory` ;
  `PerformanceObserver('longtask')`.

## Résultat

| Mesure | Valeur |
|---|---|
| Temps JS échantillonné sur 60 s | **5,7 s** (≈ 9,5 % du fil principal) |
| dont idle / program / GC | 0,3 s |
| Tas JS | 45 Mo |
| Tâches longues (> 50 ms) observées | 0 (observateur `longtask` non déclenché dans cette webview — à confirmer dans Chrome de bureau) |
| Position du film après 60 s | 1 239 nm, 7 jours d'expédition |

Répartition du temps propre (noms minifiés du bundle `index-*.js`) :

| ms | Fonction | Région du bundle |
|---|---|---|
| 589 | `vx` | chunk 8 — rendu / DOM (React DOM) |
| 367 | `Xd` | chunk 7 — réconciliateur React |
| 341 | `(anonymous)` | chunk 8 |
| 324 | `m2` | chunk 30 — Leaflet (projection / positionnement des marqueurs) |
| 271 | `Eg` | chunk 7 — React |
| 251 | `zw` | chunk 8 |
| 213 | `yh` | chunk 7 — React |
| 210 | `k2` | chunk 30 — Leaflet |
| 166 | `(anonymous)` | chunk 36 — code application (moteur / hooks) |
| 72 | `ck` | chunk 90 — code application |

Lecture : environ **2,5 s de React + DOM, 0,6 s de Leaflet, moins de 0,5 s
de code application** (moteur d'événements, juge, cartes, récit) sur 60 s.
Le moteur d'événements n'est pas le poste dominant ; le rendu l'est, et il
tient dans 10 % d'un cœur.

## Décision

**Pas de Web Worker** pour le moteur d'événements : il coûterait de la
complexité (sérialisation des sacs, deux horloges) pour déplacer < 1 % du
fil principal. Les gains, s'il en faut, sont côté rendu :

1. mémoïser les rangées qui se re-rendent 4× / s sans changer (déjà fait pour
   `EscaleLegend`, à étendre au `JournalPanel` et aux pastilles) ;
2. ne pas repositionner les drapeaux pendant le suivi caméra (fait au lot I) ;
3. réduire la fréquence de publication du HUD (4 → 2 Hz) si la barre film
   apparaît dans un futur profil.

À refaire dans Chrome de bureau (DevTools → Performance, 60 s) si un
ralentissement est ressenti en prod ; la méthode ci-dessus prend cinq minutes.

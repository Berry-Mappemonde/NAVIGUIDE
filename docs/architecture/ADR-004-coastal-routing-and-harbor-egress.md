# ADR-004 — Coastal Routing & Harbor Egress (Dette technique)

## Statut

Proposé — en attente de décision d'architecture.

## Contexte

Le solveur de routage officiel de Naviguide (`searoute` / A* hauturier) génère le tracé Berry-Mappemonde embarqué dans `naviguide-simulator/public/route.geojson`. Après le rebuild de la PR #115 (contournement AINCL81), le premier tronçon maritime au départ de La Rochelle (`-1.167, 46.1541` → `Point intermédiaire Avant Corse`) coupe la terre selon l'oracle Shapely :

- Segment 0 (La Rochelle → waypoint d'échappement) : **1 449 m** de traversée terrestre.
- Segment 1 (waypoint d'échappement → point suivant) : **4 628 m** de traversée terrestre.

L'oracle Shapely utilise le masque Natural Earth 1:10m (`ne_10m_land_oracle.json.gz`) chargé par `route_engine._NE_TREE`. La tolérance d'approche maritime est de 20 km (`ENGINE_SHORT_LAND_M = 20_000.0`) : un recouvrement ≤ 20 km collé à une extrémité n'est pas considéré comme une traversée. Au-delà, ou à plus de 20 km des deux bouts, c'est une traversée terrestre invalide.

## Symptôme

Le solveur hauturier global utilise un maillage trop grossier pour la géométrie serrée des Pertuis charentais à la sortie du port de La Rochelle. Le premier waypoint calculé par le routeur pointe vers le large sud-ouest (`-2.43, 45.53`) et traverse la côte sur une distance significative. L'oracle de test (`test_shapely_oracle_allows_panama_and_rejects_other_land`) rejette donc le tracé publié.

## Solution temporaire (appliquée)

Épinglage des coordonnées de chenalage historique dans `public/route.geojson` :

- Le waypoint d'échappement côtier d'avant le rebuild de PR #115 a été restauré :
  `[-1.2141155000000001, 46.136630499999995]`.
- Ce point positionne le navire en eaux saines immédiatement après la sortie du port, avant de rejoindre le reste du tracé.
- Le nombre total de sommets reste inchangé (1 224), préservant le pin de `geo.test.js`.

## Option A (recommandée) — Sas de sortie portuaire (*Harbor Egress Pinning*)

Injecter des waypoints obligatoires d'eaux saines avant tout appel au solveur hauturier, pour chaque départ de port :

1. Définir un polygon de chenal de sortie par port (ex. : Pertuis d'Antioche, Pertuis Breton pour La Rochelle).
2. Le premier waypoint maritime doit impérativement tomber dans ce polygon (eaux saines, à l'abri de la côte).
3. Le solveur hauturier (`searoute_with_exact_end`) est alors appelé avec ce waypoint comme point d'entrée de la zone hauturière, et non avec les coordonnées brutes du quai.
4. Un garde-fou Shapely valide que le segment quai → premier waypoint hauturier ne dépasse pas la tolérance des 20 km et ne traverse pas la terre au-delà de l'extrémité du port.

Avantages :
- Détecte systématiquement les sorties de port invalides avant calcul.
- Compatible avec le solveur existant sans modification de son cœur.
- Faible coût d'implémentation.

## Option B — Raffinement adaptatif du graphe de navigation

Affiner le graphe A* sous contrainte Shapely :

1. Générer un graphe de navigation local à haute résolution autour de chaque port (maillage ≤ 500 m).
2. Guider l'A* par le polygone de côte (Natural Earth) pour pénaliser les arêtes traversant la terre.
3. N'utiliser le solveur hauturier global qu'en dehors de la zone côtière raffinée.

Avantages :
- Traite le problème à la racine (géométrie du solveur).
- Gère automatiquement tous les ports sans configuration manuelle de chenal.

Inconvénients :
- Coût d'implémentation élevé (nouveau module de graphe côtier).
- Risque de régression sur les performances du calcul de route.
- Nécessite une validation Shapely sur chaque arête candidate.

## Décision

Option A retenue pour la release immédiate (pin des coordonnées de chenalage dans `public/route.geojson`). Option B à étudier pour le moyen terme si d'autres ports présentent le même symptôme.

## Tests de non-régression associés

- `test_official_route_land.py::test_shapely_oracle_allows_panama_and_rejects_other_land` — valide qu'aucun segment maritime ne traverse la terre (hors Panama/Suez).
- `test_official_route_land.py::test_official_route_avoids_land` — valide l'absence de hit terrestre sur l'intégralité de la route officielle.
- `test_route_engine.py::test_missing_catalog_marks_amp_unavailable_and_keeps_the_land_line` — valide le comportement fail-closed (`constraintStatus == "fail"`) quand le catalogue AMP est indisponible.
- `test_rz_sync_guardrails.py::test_rz4_route_file_fingerprint_deterministic` — valide la stabilité de l'empreinte de `route.geojson` (1 224 sommets).

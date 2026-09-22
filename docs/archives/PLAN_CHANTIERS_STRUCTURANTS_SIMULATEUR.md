> **Archivé le 22 septembre 2026 — remplacé par** `docs/archives/PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md`. Index : [docs/README.md](../README.md).

# Chantiers structurants — simulator.naviguide.fr

## Fait : MapScene et catalogues spatiaux

`MapScene` est désormais la frontière Leaflet du simulateur. Son contrôleur impératif garde les calques mobiles persistants et applique les mises à jour `add / update / remove`. Le playhead tourne en `requestAnimationFrame` hors de `App` ; seul un instantané HUD est remonté vers React, au maximum à 4 Hz.

## Fait : pipeline météo asynchrone partagé

`server/weather_pipeline.py` ([PR #177](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/177)) : tâche de rafraîchissement dédupliquée, état durable `pending / ready / error`, cache par cellule 0,25° + cycle GFS, pour tous les fournisseurs (Copernicus, Open-Meteo/RTOFS, GRIB, cube).

## Ordre restant

1. ~~**Pipeline météo asynchrone partagé complet**~~ (fait) — généraliser une tâche de rafraîchissement dédupliquée, un état durable et un cache par cellule/cycle à tous les fournisseurs.
2. **Web Worker, seulement après profilage runtime** — décider à partir d’une trace Performance montrant un coût JavaScript notable. Un worker ne réduit ni le dessin Leaflet ni le coût DOM.

Les catalogues sont servis par une API locale à bbox, indexés en mémoire par source et filtrés avant le rendu. Le niveau de détail varie selon le zoom, la réponse est plafonnée à 420 features et les points qui dépassent le budget sont regroupés. Les groupes Leaflet restent vivants entre deux vues ; seules les features entrantes, sortantes ou modifiées sont touchées.

# Archive — NAVIGUIDE NavSecOps + chat + import GeoJSON

**Source :** [NAVIGUIDE-for-Berry-Mappemonde/naviguide](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/naviguide)  
**Commit :** `deb2706` (2026-03-29) — import GeoJSON Point, calque Projects,
`fitBounds` à l’import.  
**Statut :** référence uniquement. Le NAVIGUIDE de production vit dans
`/naviguide/` de ce monorepo (plus récent, NIM / climatologie / couches BI).

`README.source.md` est le README **d’origine** du dépôt.

## Pourquoi c’est là

Ce dépôt de mars 2026 n’est pas « NAVIGUIDE en plus complet ». C’est une
branche **NavSecOps** (la route comme du code) plus le chat contextualisé
et un import GeoJSON que le monorepo n’a pas repris.

| Chemin | Intérêt pour Blue-Intelligence-Map / NAVIGUIDE |
|--------|------------------------------------------------|
| `naviguide-api/naviguide_navsecops_*.py`, `naviguide_duo.py` | `POST /api/v1/navsecops/analyze` : valider une route, scorer les risques, rédiger un briefing |
| `naviguide-api/main.py` | Comment ces routes étaient branchées sur FastAPI |
| `naviguide-api/env.example` | Modèle Copernicus / Gemini / Claude / secret NavSecOps (placeholders) |
| `naviguide_workspace/llm_utils.py` | Appels Gemini (JSON) + Claude — à recabler sur `llm_cascade.py` si réintégration |
| `proxy_server.py` | Proxy `/api/v1/navsecops/*` et `/duo/*` **avant** l’orchestrateur |
| `routes/naviguide-berry-mappemonde.geojson` | Route officielle Berry **versionnée** (absente sous `/naviguide/routes/`) |
| `routes/berry-mappemonde-route-order.json` + `scripts/validate_berry_route_order.py` | Ordre des escales, contrôlable en CI |
| `scripts/gitlab_*.sh`, `.gitlab-ci.yml` | Commentaire auto sur une merge request de route |
| `agents/`, `flows/`, `.ai-catalog-mapping.json` | Catalogue GitLab Duo (prompts MR-only) |
| `frontend/Sidebar.jsx` (`parseGeoJSON`) | Garde les **Point / MultiPoint**, pas seulement les LineString |
| `frontend/App.jsx` | Calque cercles « Projects » + toggle + recentrage carte |
| `frontend/buildChatContext.js` + `docs/CHAT_CONTEXT_SPEC.md` | Résumé structuré (plan, leg, vent/houle) pour le chat skipper |
| `polar_api/main.py` | `POST /api/v1/chat` et `/api/v1/polar/chat` |
| `docs/NAVSECOPS_*.md`, `DATA.md`, `BERRY_MAPPEMONDE_ROUTE_DIGEST.md` | Contrats API, grounding Berry, GEBCO/AIS |
| `Dockerfile` | Image API NavSecOps seule (Cloud Run) — pas la stack VPS actuelle |
| `scripts/download_geodata.sh`, `fetch_data.sh` | Données locales weather routing |

Les docs `PLAN_DEV_NOVA.md` et `SETUP_NOVA_CREDITS.md` étaient déjà dans
ce dépôt ; le **code** Nova différent est sous `../naviguide-nova/`.

## Non copié

Frontend complet (drapeaux, polar CSV), agents 1/3 / weather routing
(déjà dans `/naviguide/`, version plus récente), `venv`, `.env`,
sous-module vide `naviguide-berry-mappemonde/`.

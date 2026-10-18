"""Réglages de la boucle de nuit pour ce dépôt.

Les scripts de ce dossier importent ces noms. On ne recopie pas la
même chaîne dans le texte d'un prompt.
"""
from __future__ import annotations

REPO_SLUG = "Berry-Mappemonde/NAVIGUIDE"
DEFAULT_REPO = "https://github.com/" + REPO_SLUG
BIM_REPO = REPO_SLUG
PROD_URL = "https://naviguide.fr"
RECETTE_HOST = "recette.naviguide.fr"
RECETTE_BRANCH = "recette"

PROMPTS_MD = "docs/LOTS_ORDRE_ET_PROMPTS.md"
REGLES_MD = "docs/REGLES_WORKFLOW_AGENT.md"
PLAN_REVUE_SOIR = "docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md"
WORKFLOW_INDUSTRIEL = "docs/WORKFLOW_INDUSTRIEL.md"
RECETTE_DIR = "docs/recette"
HACKATHON_DEVPOST = "docs/HACKATHON_DEVPOST_SOUMISSION.md"
ESPRIT = "docs/ESPRIT_DE_L_APPLICATION.md"
PLAN_DEUX_MODES = "docs/PLAN_DEUX_MODES_2026-09-29.md"
INFRA_VPS_README = "infra/vps/README.md"
PARCOURS_NAME = "PARCOURS_DE_REFERENCE.md"
SIMULATOR_DIR = "naviguide-simulator"
ENSURE_DEV = "naviguide-simulator/ensure-dev.sh"
APP_JSX = "naviguide-simulator/src/App.jsx"
E2E_LOTS = "naviguide-simulator/e2e/lots"
FILM_CINEMATIQUE = "naviguide-simulator/scripts/film-cinematique.mjs"
SERVER_ENV = "naviguide-simulator/server/.env"

FIXED_DOCS = (REGLES_MD, PROMPTS_MD, PLAN_REVUE_SOIR)
NPM_PROJECTS = ("naviguide-simulator", "frontend")
PIP_PROJECT = ("naviguide-simulator", "server/requirements.txt", ".venv/bin/python")
VOYAGE_ID = "berry-mappemonde-2026-officiel"
SHARED_CACHE_DIRS = ("voyage_data", "forecast_cache", "grib_data")
VOYAGE_DATA_FILES = (
    "eez_vliz_v12.geojson",
    "ici_thin_cache.json",
    "official_journal",
    "voyage_{id}.json",
)

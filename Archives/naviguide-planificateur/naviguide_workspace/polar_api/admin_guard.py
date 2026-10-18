"""Garde admin des écritures du service polaire historique (port 9004).

Même règle que l'API principale (naviguide-simulator/server/admin_guard.py) :
secret partagé NAVIGUIDE_ADMIN_SECRET, envoyé par le client dans l'en-tête
X-Naviguide-Admin, comparé en temps constant.

Fermé par défaut : sans secret configuré, une écriture n'est acceptée que
d'un appel local direct (dev). Derrière nginx (X-Real-IP / X-Forwarded-For
présents), refus 503 tant que le secret n'est pas posé, jamais d'ouverture
silencieuse.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException, Request

log = logging.getLogger("polar_api.guard")

ADMIN_HEADER = "X-Naviguide-Admin"
ADMIN_ENV = "NAVIGUIDE_ADMIN_SECRET"
_warned = False


def admin_secret() -> str:
    return (os.environ.get(ADMIN_ENV) or "").strip()


def _is_direct_local(request: Request) -> bool:
    if request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for"):
        return False
    host = (request.client.host if request.client else "") or ""
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


def is_admin(request: Request) -> bool:
    secret = admin_secret()
    given = (request.headers.get(ADMIN_HEADER) or "").strip()
    if secret:
        return bool(given) and hmac.compare_digest(given, secret)
    return _is_direct_local(request)


def require_admin(request: Request) -> None:
    """Dépendance FastAPI : 401 sans le bon secret ; 503 si aucun secret derrière un proxy."""
    global _warned
    secret = admin_secret()
    if not secret:
        if _is_direct_local(request):
            if not _warned:
                log.warning("%s absent : écritures admin acceptées en local seulement", ADMIN_ENV)
                _warned = True
            return
        raise HTTPException(503, "secret admin non configuré sur le serveur")
    given = (request.headers.get(ADMIN_HEADER) or "").strip()
    if not given or not hmac.compare_digest(given, secret):
        raise HTTPException(401, "clé admin requise")

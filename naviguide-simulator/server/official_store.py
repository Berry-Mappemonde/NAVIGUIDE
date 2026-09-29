"""Stock persistant du voyage officiel — une interface, deux dos (lot RF2, D5').

Lecture/écriture des six familles (moments, film, eta, climo, ici, plan_review).
Clé : (route officielle, t0, date des données). Une entrée porte un horodatage ;
le remplacement est atomique. Derrière : MongoDB si SIMULATOR_MONGO_URL est posé
(base naviguide_simulator), fichiers sur disque sinon.

Aucune donnée n'est inventée : `put` n'accepte que le résultat d'un vrai calcul.
Une famille absente reste « en préparation ». Le travail de fond calcule hors
des requêtes. Aucun test ne se connecte à une vraie base.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("naviguide-simulator.official-store")

FAMILIES = ("moments", "film", "eta", "climo", "ici", "plan_review")
FILM_VARIANT_SECONDS = (150, 180)   # les pilules 2:30 / 3:00 de la barre ; la première est la variante par défaut
PREPARING = "preparing"
READY = "ready"
# Clé film : un snapshot RF2 (avant phrases avion) ne matche plus.
FILM_SCRIPT_REV = "rf5"
DB_NAME = "naviguide_simulator"
COLLECTION = "official_voyage"
# Par défaut, le stock disque vit DANS le checkout (server/voyage_data/, ignoré par git) : un agent qui teste
# dans son worktree ne peut plus écrire dans le stock du poste (27 sept. : l'agent RF2 y avait figé un journal
# sans événements, servi 14 h). Le poste pose NAVIGUIDE_OFFICIAL_STORE_DIR (ensure-dev.sh) → ~/.cache/naviguide/voyage-store.
DEFAULT_DISK = Path(__file__).resolve().parent / "voyage_data" / "official-store"
PERIOD_S = float(os.environ.get("NAVIGUIDE_OFFICIAL_STORE_PERIOD_S") or 6 * 3600)
ROUTE_NEAR_NM = 8.0

_LOCK = threading.RLock()
_INSTANCE: Optional["OfficialStore"] = None
_WORKER_STARTED = False
_FILM_FORCED = False
_REFRESH_LOCK = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    when = dt or _utc_now()
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _data_date(now: datetime | None = None) -> str:
    when = now or _utc_now()
    return when.astimezone(timezone.utc).strftime("%Y-%m-%d")


def route_fingerprint(voy: dict | None) -> str:
    """Empreinte stable de la route officielle (points + marques + t0)."""
    voy = voy or {}
    raw = json.dumps(
        {
            "t0": voy.get("t0") or "",
            "n": len(voy.get("points") or []),
            "rev": voy.get("routeRev") or 0,
            "marks": [
                (m.get("name"), round(float(m.get("nm") or 0), 3))
                for m in (voy.get("marks") or [])
                if isinstance(m, dict)
            ],
            "first": (voy.get("points") or [{}])[0].get("lat") if voy.get("points") else None,
            "last": (voy.get("points") or [{}])[-1].get("lat") if voy.get("points") else None,
        },
        ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_key(route_id: str, t0: str, data_date: str) -> str:
    return f"{route_id}:{t0}:{data_date}"


def _is_data_date(value: str) -> bool:
    return (
        len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
        and value[:4].isdigit()
        and value[5:7].isdigit()
        and value[8:10].isdigit()
    )


def parse_key(key: str) -> tuple[str, str, str, Optional[str]]:
    """Décompose `route:t0:data_date[:rev]` — t0 peut contenir des `:`."""
    if not key or ":" not in key:
        raise ValueError(f"clé invalide: {key}")
    suffix = None
    rest = key
    last = rest.rsplit(":", 1)
    if len(last) == 2 and not _is_data_date(last[1]):
        suffix = last[1]
        rest = last[0]
    if ":" not in rest:
        raise ValueError(f"clé invalide: {key}")
    route_and_t0, data_date = rest.rsplit(":", 1)
    if not _is_data_date(data_date) or ":" not in route_and_t0:
        raise ValueError(f"clé invalide: {key}")
    route_id, t0 = route_and_t0.split(":", 1)
    return route_id, t0, data_date, suffix


def _stamp(hit: Optional[dict]) -> dict:
    """storedAt / dataDate à recopier dans une réponse HTTP."""
    if not hit:
        return {}
    out: dict[str, str] = {}
    stored = hit.get("storedAt")
    if stored:
        out["storedAt"] = stored
    date = hit.get("dataDate")
    if not date:
        try:
            date = parse_key(str(hit.get("key") or ""))[2]
        except (TypeError, ValueError):
            date = None
    if date:
        out["dataDate"] = date
    return out


def preparing_payload(family: str, extra: Optional[dict] = None) -> dict:
    """Réponse honnête — jamais un 500, jamais un calcul. Le client sait déjà
    afficher un journal vide / un film pending / une fourchette absente."""
    body = {"status": PREPARING, "reason": "en préparation", "family": family}
    if extra:
        body.update(extra)
    return body


def worker_enabled() -> bool:
    raw = (os.environ.get("NAVIGUIDE_OFFICIAL_WORKER") or "1").strip().lower()
    if raw in ("0", "false", "no"):
        return False
    if os.environ.get("PYTEST_CURRENT_TEST") and raw != "force":
        return False
    return True


def disk_root() -> Path:
    env = (os.environ.get("NAVIGUIDE_OFFICIAL_STORE_DIR") or "").strip()
    if env:
        return Path(env)
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CI"):
        return Path(tempfile.mkdtemp(prefix="naviguide-voyage-store-"))
    return DEFAULT_DISK


# ── dos disque ───────────────────────────────────────────────────────────────

class DiskBackend:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root is not None else disk_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str, family: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        d = self.root / safe
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{family}.json"

    def get(self, key: str, family: str) -> Optional[dict]:
        dest = self._path(key, family)
        if not dest.exists():
            return None
        try:
            return json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("stock disque illisible %s/%s : %s", key, family, exc)
            return None

    def stamp(self, key: str, family: str) -> Optional[str]:
        """Empreinte de l'entrée telle qu'elle est sur disque (mtime + taille) : un autre PROCESSUS
        (le remplisseur, RC18) a pu la remplacer — l'API relit alors au lieu de servir sa copie mémoire."""
        dest = self._path(key, family)
        try:
            st = dest.stat()
        except OSError:
            return None
        return f"{st.st_mtime_ns}:{st.st_size}"

    def list_family(self, family: str) -> list[tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        if not self.root.exists():
            return out
        for folder in self.root.iterdir():
            dest = folder / f"{family}.json"
            if not dest.is_file():
                continue
            try:
                doc = json.loads(dest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("stock disque illisible %s : %s", dest, exc)
                continue
            if not isinstance(doc, dict) or not doc.get("key"):
                continue
            out.append((str(doc["key"]), doc))
        return out

    def put(self, key: str, family: str, doc: dict) -> dict:
        dest = self._path(key, family)
        tmp = dest.with_suffix(".tmp")
        payload = json.dumps(doc, ensure_ascii=False, indent=2)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(dest)
        return doc


# ── dos Mongo (client injecté en tests — jamais une vraie base) ───────────────

class MongoBackend:
    """Dos MongoDB : base naviguide_simulator uniquement.

    `client` injecté (mongomock / faux client). En production, pymongo à partir
    de SIMULATOR_MONGO_URL — jamais MONGO_URL_LOCAL ni mongo.env.
    """

    def __init__(self, client: Any, db_name: str = DB_NAME):
        self._col = client[db_name][COLLECTION]

    def get(self, key: str, family: str) -> Optional[dict]:
        doc = self._col.find_one({"_id": f"{key}:{family}"})
        if not doc:
            return None
        return {
            "key": doc.get("key") or key,
            "family": doc.get("family") or family,
            "storedAt": doc.get("storedAt"),
            "payload": doc.get("payload"),
        }

    def stamp(self, key: str, family: str) -> Optional[str]:
        """storedAt de l'entrée (requête légère par _id) : change quand le remplisseur a réécrit."""
        try:
            doc = self._col.find_one({"_id": f"{key}:{family}"}, {"storedAt": 1})
        except TypeError:   # faux client de test sans projection
            doc = self._col.find_one({"_id": f"{key}:{family}"})
        if not doc:
            return None
        return str(doc.get("storedAt") or "")

    def list_family(self, family: str) -> list[tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        for doc in self._col.find({"family": family}):
            key = (doc or {}).get("key")
            if not key:
                continue
            out.append((str(key), {
                "key": key,
                "family": doc.get("family") or family,
                "storedAt": doc.get("storedAt"),
                "payload": doc.get("payload"),
            }))
        return out

    def put(self, key: str, family: str, doc: dict) -> dict:
        stored = {
            "_id": f"{key}:{family}",
            "key": key,
            "family": family,
            "storedAt": doc.get("storedAt"),
            "payload": doc.get("payload"),
        }
        self._col.replace_one({"_id": stored["_id"]}, stored, upsert=True)
        return {k: stored[k] for k in ("key", "family", "storedAt", "payload")}


def _mongo_client_from_url(url: str):
    from pymongo import MongoClient  # noqa: PLC0415
    return MongoClient(url, serverSelectionTimeoutMS=2000)


# ── interface unique ─────────────────────────────────────────────────────────

class OfficialStore:
    def __init__(self, backend: Any, *, now: Optional[Callable[[], datetime]] = None):
        self.backend = backend
        self._now = now or _utc_now
        self._mem: dict[tuple[str, str], dict] = {}
        self._stamps: dict[tuple[str, str], Optional[str]] = {}
        self._clock_bytes: Optional[bytes] = None
        self._clock_bytes_key: Optional[str] = None

    def current_key(self, voy: Optional[dict] = None, now: Optional[datetime] = None) -> str:
        voy = voy if voy is not None else _load_official()
        t0 = (voy or {}).get("t0") or ""
        return make_key(route_fingerprint(voy), t0, _data_date(now or self._now()))

    def family_key(
        self,
        family: str,
        voy: Optional[dict] = None,
        now: Optional[datetime] = None,
    ) -> str:
        """Clé de rangement : le film inclut la révision du script (RF5)."""
        base = self.current_key(voy, now)
        if family == "film":
            return f"{base}:{FILM_SCRIPT_REV}"
        return base

    def _with_date(self, hit: Optional[dict]) -> Optional[dict]:
        if not hit:
            return None
        out = dict(hit)
        if not out.get("dataDate"):
            try:
                out["dataDate"] = parse_key(str(out.get("key") or ""))[2]
            except (TypeError, ValueError):
                pass
        return out

    def _latest_hit(self, family: str, current: str) -> Optional[dict]:
        """Plus récente entrée même route + même t0 (minuit UTC / CI)."""
        try:
            route_id, t0, _, want_suf = parse_key(current)
        except ValueError:
            return None
        lister = getattr(self.backend, "list_family", None)
        if not callable(lister):
            return None
        best: Optional[tuple[str, str, dict]] = None
        for stored_key, doc in lister(family):
            try:
                r, t, date, suf = parse_key(stored_key)
            except ValueError:
                continue
            if r != route_id or t != t0:
                continue
            if (want_suf or None) != (suf or None):
                continue
            if best is None or date > best[0]:
                best = (date, stored_key, doc)
        if not best:
            return None
        date, stored_key, doc = best
        out = dict(doc)
        out["key"] = stored_key
        out["dataDate"] = date
        return out

    def get(self, family: str, key: Optional[str] = None) -> Optional[dict]:
        if family not in FAMILIES:
            raise ValueError(f"famille inconnue: {family}")
        dest = key if key is not None else self.family_key(family)
        with _LOCK:
            hit = self._cached(dest, family)
            if hit is not None:
                return self._with_date(hit)
            if key is not None:
                return None
            found = self._latest_hit(family, dest)
            if found is not None and found.get("key"):
                self._remember(found["key"], family, found)
            return self._with_date(found)

    def _stamp(self, key: str, family: str) -> Optional[str]:
        stamper = getattr(self.backend, "stamp", None)
        if not callable(stamper):
            return None
        try:
            return stamper(key, family)
        except Exception:
            return None

    def _remember(self, key: str, family: str, hit: dict) -> None:
        self._mem[(key, family)] = hit
        self._stamps[(key, family)] = self._stamp(key, family)

    def _cached(self, key: str, family: str) -> Optional[dict]:
        """Copie mémoire, relue si le dos a changé sous nos pieds (le remplisseur est un autre processus, RC18)."""
        stamp = self._stamp(key, family)
        hit = self._mem.get((key, family))
        if hit is not None and self._stamps.get((key, family)) == stamp:
            return hit
        hit = self.backend.get(key, family)
        if hit is None:
            self._mem.pop((key, family), None)
            self._stamps.pop((key, family), None)
            return None
        self._mem[(key, family)] = hit
        self._stamps[(key, family)] = stamp
        if family == "climo":
            self._clock_bytes = None
            self._clock_bytes_key = None
        return hit

    def put(self, family: str, payload: dict, key: Optional[str] = None) -> dict:
        if family not in FAMILIES:
            raise ValueError(f"famille inconnue: {family}")
        if payload is None:
            raise ValueError("payload vide — une famille non calculée reste en préparation")
        dest_key = key if key is not None else self.family_key(family)
        doc = {
            "key": dest_key,
            "family": family,
            "storedAt": _iso(self._now()),
            "payload": payload,
        }
        with _LOCK:
            stored = self.backend.put(dest_key, family, doc)
            self._remember(dest_key, family, stored)
            if family == "climo":
                self._clock_bytes = None
                self._clock_bytes_key = None
            return stored

    def status(self, key: Optional[str] = None) -> dict:
        dest = key if key is not None else self.current_key()
        families = {}
        for name in FAMILIES:
            if key is not None:
                hit = self.get(name, key)
            else:
                hit = self.get(name)
            families[name] = {
                "status": READY if hit and hit.get("payload") is not None else PREPARING,
                "storedAt": (hit or {}).get("storedAt"),
                "dataDate": (hit or {}).get("dataDate"),
                "key": (hit or {}).get("key"),
            }
        return {"key": dest, "families": families}


def get_store(*, reset: bool = False) -> OfficialStore:
    """Dos choisi tout seul : Mongo si SIMULATOR_MONGO_URL, disque sinon."""
    global _INSTANCE
    if reset:
        _INSTANCE = None
    if _INSTANCE is not None:
        return _INSTANCE
    url = (os.environ.get("SIMULATOR_MONGO_URL") or "").strip()
    if url:
        _INSTANCE = OfficialStore(MongoBackend(_mongo_client_from_url(url)))
    else:
        _INSTANCE = OfficialStore(DiskBackend())
    return _INSTANCE


def reset_store() -> None:
    """Tests : oublier le singleton (nouveau répertoire / faux client)."""
    global _INSTANCE
    _INSTANCE = None


def get(family: str, key: Optional[str] = None) -> Optional[dict]:
    return get_store().get(family, key)


def put(family: str, payload: dict, key: Optional[str] = None) -> dict:
    return get_store().put(family, payload, key)


def family_status() -> dict:
    return get_store().status()


def payload_of(family: str) -> Optional[dict]:
    hit = get(family)
    if not hit:
        return None
    body = hit.get("payload")
    return body if isinstance(body, dict) else None


def _film_chapters_blob(payload: Optional[dict]) -> str:
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    for key in ("fr", "default", "en"):
        plan = payload.get(key)
        if not isinstance(plan, dict):
            continue
        for ch in plan.get("chapters") or []:
            if isinstance(ch, dict):
                parts.append(str(ch.get("text") or ""))
    return " ".join(parts)


def _itinerary_marks() -> list:
    """Cayenne / Halifax de l'itinéraire Berry (route.geojson), escales ou intermédiaires.

    Halifax est un waypoint `intermediate` : `official_itinerary_body` ne le met
    pas dans les marques d'escales — ce n'est pas une invention, le point est
    dans le GeoJSON officiel.
    """
    try:
        from voyage_api import _ROUTE_GEOJSON  # noqa: PLC0415
        fc = json.loads(_ROUTE_GEOJSON.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[dict] = []
    for feat in fc.get("features") or []:
        geom = (feat or {}).get("geometry") or {}
        props = (feat or {}).get("properties") or {}
        if geom.get("type") != "Point":
            continue
        name = str(props.get("name") or "")
        low = name.lower()
        if "cayenne" not in low and "halifax" not in low:
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        try:
            out.append({
                "name": name,
                "lon": float(coords[0]),
                "lat": float(coords[1]),
            })
        except (TypeError, ValueError):
            continue
    return out


def _voy_stored_marks(voy: Optional[dict]) -> list:
    voy = voy or {}
    marks = [m for m in (voy.get("marks") or []) if isinstance(m, dict)]
    clock = voy.get("clock") if isinstance(voy.get("clock"), dict) else None
    if clock:
        marks.extend(m for m in (clock.get("marks") or []) if isinstance(m, dict))
    else:
        stored = stored_clock()
        if stored:
            marks.extend(m for m in (stored.get("marks") or []) if isinstance(m, dict))
    return marks


def _name_is_cayenne(name: str) -> bool:
    return "cayenne" in (name or "").lower()


def _marks_have_cayenne(marks: list) -> bool:
    return any(_name_is_cayenne(m.get("name") or "") for m in marks if isinstance(m, dict))


def _voy_air_marks(voy: Optional[dict], plan: Optional[dict] = None) -> list:
    """Marques du voyage ; l'itinéraire Berry n'est ajouté que si Cayenne est déjà là."""
    marks = list(_voy_stored_marks(voy))
    if _marks_have_cayenne(marks):
        marks.extend(_itinerary_marks())
        return marks
    blob = ""
    if isinstance(plan, dict):
        blob = " ".join(
            f"{c.get('fromName') or ''} {c.get('toName') or ''} {c.get('text') or ''}"
            for c in (plan.get("chapters") or [])
            if isinstance(c, dict)
        )
    if "cayenne" in blob.lower() or "guyane" in blob.lower():
        marks.extend(_itinerary_marks())
    return marks


def _apply_air_sentences(plan: dict, lang: str, voy: Optional[dict]) -> dict:
    """Garde l'aller/retour avion si la route officielle a la paire — pas d'invention."""
    from film_script import _ensure_air_sentences  # noqa: PLC0415

    if not isinstance(plan, dict):
        return plan
    chapters = [dict(c) for c in (plan.get("chapters") or []) if isinstance(c, dict)]
    if not chapters:
        return plan
    _ensure_air_sentences(
        chapters, marks=_voy_air_marks(voy, plan), moments=None, lang=lang,
    )
    out = dict(plan)
    out["chapters"] = chapters
    return out


def film_snapshot_stale(payload: Optional[dict], voy: Optional[dict] = None) -> bool:
    """True si la route a Cayenne↔Halifax mais le snapshot ne dit pas l'avion.

    Pas d'invention : sans la paire, le snapshot n'est jamais « périmé ».
    """
    from film_script import _AIR_BACK_RE, _AIR_OUT_RE, _route_has_air_pair  # noqa: PLC0415

    if not _route_has_air_pair(_voy_air_marks(voy, payload.get("fr") if isinstance(payload, dict) else None)):
        return False
    blob = _film_chapters_blob(payload)
    if not blob.strip():
        return True
    return not (_AIR_OUT_RE.search(blob) and _AIR_BACK_RE.search(blob))


def stored_clock() -> Optional[dict]:
    body = payload_of("climo")
    clock = (body or {}).get("clock")
    return clock if isinstance(clock, dict) and clock.get("t0") else None


def serve_clock_bytes() -> Optional[bytes]:
    """Horloge déjà sérialisée — GET /clock sans recalcul ni ré-encodage."""
    st = get_store()
    hit = st.get("climo")
    clock = ((hit or {}).get("payload") or {}).get("clock") if hit else None
    if not isinstance(clock, dict) or not clock.get("t0"):
        return None
    key = (hit or {}).get("key") or st.current_key()
    with _LOCK:
        if st._clock_bytes is not None and st._clock_bytes_key == key:
            return st._clock_bytes
        body = dict(clock)
        body.update(_stamp(hit))
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        st._clock_bytes = raw
        st._clock_bytes_key = key
        return raw


# ── proximité route officielle (sac ici) ─────────────────────────────────────

def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from isochrone import haversine  # noqa: PLC0415
    dlon = float(lon2) - float(lon1)
    while dlon > 180.0:
        dlon -= 360.0
    while dlon < -180.0:
        dlon += 360.0
    return haversine(lat1, lon1, lat2, lon1 + dlon)


def _load_official() -> Optional[dict]:
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    return load_voyage(OFFICIAL_VOYAGE_ID)


def on_official_route(lat: float, lon: float, max_nm: float = ROUTE_NEAR_NM) -> bool:
    voy = _load_official()
    points = (voy or {}).get("points") or []
    if not points:
        return False
    step = max(1, len(points) // 400)
    for p in points[::step]:
        try:
            if _haversine_nm(lat, lon, float(p["lat"]), float(p["lon"])) <= max_nm:
                return True
        except (KeyError, TypeError, ValueError):
            continue
    return False


def ici_bag_near(lat: float, lon: float, max_nm: float = ROUTE_NEAR_NM) -> Optional[dict]:
    body = payload_of("ici")
    if not body:
        return None
    best = None
    best_d = max_nm
    for row in body.get("points") or []:
        if not isinstance(row, dict):
            continue
        try:
            d = _haversine_nm(lat, lon, float(row["lat"]), float(row["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
        if d < best_d:
            best_d = d
            best = row.get("bag")
    return best if isinstance(best, dict) else None


def preparing_ici(lat: float, lon: float, radius_nm: float = 30.0) -> dict:
    from ici_engine import empty_dossier  # noqa: PLC0415
    bag = empty_dossier(lat, lon, radius_nm)
    bag["status"] = PREPARING
    bag["reason"] = "en préparation"
    return bag


# ── calculs (mêmes fonctions que le serveur d'aujourd'hui) ───────────────────

def compute_climo(voy: dict, now: datetime) -> Optional[dict]:
    from voyage_api import _climo_clock, _regime_portions  # noqa: PLC0415
    from voyage_store import save_voyage  # noqa: PLC0415

    clock = _climo_clock(voy)
    if not clock or not clock.get("t0"):
        return None
    voy = dict(voy)
    voy["clock"] = clock
    save_voyage(voy)
    fiches = []
    for v in clock.get("vertices") or []:
        if not isinstance(v, dict) or v.get("lat") is None:
            continue
        fiches.append({
            "lat": v.get("lat"), "lon": v.get("lon"),
            "iso": v.get("iso"), "sailNm": v.get("sailNm"),
            "regime": v.get("regime") or v.get("kind"),
            "windKnots": v.get("windKnots"),
            "dirFromDeg": v.get("dirFromDeg"),
        })
    return {"clock": clock, "regimes": _regime_portions(clock), "fiches": fiches}


RICH_EVENT_KINDS = frozenset({"zee", "sci", "science", "poe", "amp", "climo", "wx", "grib", "marina", "port"})


def journal_degraded(summary: dict | None) -> bool:
    """Vrai si le journal ne connaît que des escales / positions alors que le poste a des perles riches
    (donc des ZEE, stations, ports d'entrée, AMP à raconter). Un tel journal est un accident de calcul,
    pas un état du voyage : il ne doit pas être figé comme « prêt »."""
    rows = list((summary or {}).get("events") or []) + list((summary or {}).get("latest") or (summary or {}).get("entries") or [])
    kinds = {str(r.get("kind")) for r in rows if isinstance(r, dict)}
    if kinds & RICH_EVENT_KINDS:
        return False
    try:
        import pearl_store  # noqa: PLC0415
        rich = int((pearl_store.count_pearls() or {}).get("rich") or 0)
    except Exception:
        rich = 0
    return bool(rich)


def compute_moments(voy: dict, now: datetime) -> Optional[dict]:
    import voyage_journal as journal  # noqa: PLC0415
    from moment_journal import read_moments, warm_moments  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415

    if not voy.get("clock"):
        return None
    journal.tick(voy, now, force=True)
    summary = journal.summary(500)
    days = {}
    for row in summary.get("days") or []:
        day = row.get("day")
        if day:
            try:
                days[day] = journal.read_day(day)
            except Exception:
                days[day] = []
    try:
        warm_moments(OFFICIAL_VOYAGE_ID, voy)   # avec l'horloge : sinon 740 moments sans date (27 sept.)
        moments = read_moments(OFFICIAL_VOYAGE_ID)
    except Exception as exc:
        log.warning("moments : %s", exc)
        moments = []
    if (summary.get("count") or 0) <= 0 and not moments:
        return None
    # Garde-fou (27 sept.) : le stock a servi pendant 14 h un journal réduit aux escales et 740 moments
    # sans date, calculés dans un worktree sans perles — puis plus jamais recalculés parce que « prêts ».
    # Une famille dégradée reste « en préparation » : le prochain passage la recalculera.
    if moments and not any(m.get("t") for m in moments):
        log.warning("stock moments : %d moments sans date — non rangés (horloge ?)", len(moments))
        return None
    if journal_degraded(summary):
        log.warning("stock moments : journal sans événements (escales seulement) alors que des perles riches existent — non rangé")
        return None
    payload = {"moments": moments, "journal": summary, "journal_days": days}
    if not moments:
        payload["moments"] = _rows_from_journal(payload)
    return payload


def compute_film(voy: dict, now: datetime) -> Optional[dict]:
    import asyncio  # noqa: PLC0415
    from film_script import official_film  # noqa: PLC0415

    if not voy.get("clock"):
        return None

    # 27 sept. : calculé en mode LIBRE (seconds=0), le film déversait jusqu'à dix changements bruts par chapitre,
    # hors chronologie — exactement le « journal déversé » refusé le 26. On range les variantes BUDGET que les
    # pilules de la barre demandent (2:30 = 150 s, 3:00 = 180 s) ; serve_film sert la plus proche.
    async def _variants():
        out: dict[str, dict[str, dict]] = {}
        for lang in ("fr", "en"):
            for secs in FILM_VARIANT_SECONDS:
                try:
                    plan = await official_film(lang=lang, seconds=secs, style="raw")
                except Exception as exc:
                    if lang == "fr":
                        raise
                    log.warning("film %s %ss : %s", lang, secs, exc)
                    continue
                if isinstance(plan, dict) and (plan.get("chapters") or []):
                    out.setdefault(lang, {})[str(secs)] = plan
        return out

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        variants = asyncio.run(_variants())
    else:
        return None
    fr = (variants.get("fr") or {}).get(str(FILM_VARIANT_SECONDS[0]))
    if not isinstance(fr, dict) or not (fr.get("chapters") or []):
        return None
    for lang, by_secs in variants.items():
        for secs, plan in list(by_secs.items()):
            by_secs[secs] = _apply_air_sentences(plan, lang, voy)
    fr = variants["fr"][str(FILM_VARIANT_SECONDS[0])]
    out = {"fr": fr, "default": fr, "variants": variants}
    en = (variants.get("en") or {}).get(str(FILM_VARIANT_SECONDS[0]))
    if isinstance(en, dict) and (en.get("chapters") or []):
        out["en"] = en
    return out


def compute_eta(voy: dict, now: datetime) -> Optional[dict]:
    from ensemble_eta import (  # noqa: PLC0415
        next_official_stop,
        peek_official_eta,
        preheat_official_eta,
        tighten_eta_payload,
    )
    from voyage_api import _polar_raw  # noqa: PLC0415

    if not voy.get("clock"):
        return None
    try:
        preheat_official_eta(
            voy, now, polar_raw=_polar_raw(voy.get("expedition_id") or ""),
        )
    except Exception as exc:
        log.warning("préchauffage ETA : %s", exc)
    stops: dict[str, dict] = {}
    names = []
    nxt = next_official_stop(voy, now)
    if nxt:
        names.append(nxt)
    for m in voy.get("marks") or []:
        n = (m or {}).get("name")
        if n and n not in names:
            names.append(n)
    for name in names[:12]:
        try:
            raw = peek_official_eta(voy, name, now)
            stops[name] = tighten_eta_payload(raw, now)
        except Exception as exc:
            log.warning("ETA %s : %s", name, exc)
    if not any(int((s or {}).get("members") or 0) > 0 for s in stops.values()):
        return None
    return {"stops": stops}


def compute_ici(voy: dict, now: datetime) -> Optional[dict]:
    from ici_engine import thin_cache_get, thin_cache_key  # noqa: PLC0415
    from ici_warm import official_pearls, sample_route_nm  # noqa: PLC0415

    points = []
    seen = set()

    def _add(lat: float, lon: float, nm: Any, bag: dict) -> None:
        key = (round(lat, 4), round(lon, 4))
        if key in seen:
            return
        seen.add(key)
        points.append({"lat": lat, "lon": lon, "nm": nm, "bag": bag})

    try:
        pearls = official_pearls()
        for p in (pearls.get("pearls") if isinstance(pearls, dict) else pearls) or []:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                lat, lon = float(p[0]), float(p[1])
                bag = thin_cache_get(thin_cache_key(lat, lon, 30.0))
                if bag:
                    _add(lat, lon, None, bag)
                continue
            if not isinstance(p, dict):
                continue
            bag = p.get("bag") if isinstance(p.get("bag"), dict) else None
            lat, lon = p.get("lat"), p.get("lon")
            if lat is None:
                at = (bag or {}).get("at") or {}
                lat, lon = at.get("lat"), at.get("lon")
            if lat is None or lon is None:
                continue
            if bag is None:
                bag = thin_cache_get(thin_cache_key(float(lat), float(lon), 30.0))
            if bag:
                _add(float(lat), float(lon), p.get("sailNm") or p.get("nm"), bag)
    except Exception as exc:
        log.debug("perles officielles : %s", exc)

    for p in sample_route_nm(voy.get("points") or []):
        bag = thin_cache_get(thin_cache_key(p["lat"], p["lon"], 30.0))
        if bag:
            _add(float(p["lat"]), float(p["lon"]), p.get("sailNm"), bag)

    if not points:
        return None
    return {"points": points}


def compute_plan_review(voy: dict, now: datetime) -> Optional[dict]:
    from plan_alerts import evaluate_plan  # noqa: PLC0415
    from plan_review import review_official  # noqa: PLC0415

    if not voy.get("clock"):
        return None
    out = review_official(voy, now, season=False)
    if not isinstance(out, dict) or not (out.get("legs") or []):
        return None
    try:
        ev = evaluate_plan(voy, now=now)
        counts: dict = {}
        for lg in ev.get("legs") or []:
            n = len(lg.get("alerts") or [])
            if lg.get("idx") is not None:
                counts[int(lg["idx"])] = n
            counts[(lg.get("from"), lg.get("to"))] = n
        for i, row in enumerate(out.get("legs") or []):
            n = counts.get(i)
            if n is None:
                n = counts.get((row.get("from"), row.get("to")))
            if n is not None:
                row["alertCount"] = int(n)
    except Exception as exc:
        log.debug("alertCount stock : %s", exc)
    out.setdefault("comment", {"text": "", "source": "rules", "cached": False})
    return out


COMPUTE: dict[str, Callable[[dict, datetime], Optional[dict]]] = {
    "climo": compute_climo,
    "moments": compute_moments,
    "film": compute_film,
    "eta": compute_eta,
    "ici": compute_ici,
    "plan_review": compute_plan_review,
}

# Horloge d'abord : les autres familles s'appuient dessus.
COMPUTE_ORDER = ("climo", "moments", "film", "eta", "ici", "plan_review")


def refresh_family(
    family: str,
    *,
    force: bool = False,
    compute: Optional[Callable[[dict, datetime], Optional[dict]]] = None,
    now: Optional[datetime] = None,
    store: Optional[OfficialStore] = None,
    voy: Optional[dict] = None,
) -> str:
    """Calcule une famille et la range. `unchanged` si la clé est déjà servie."""
    st = store or get_store()
    when = now or st._now()
    current = voy if voy is not None else _load_official()
    if current is None:
        return PREPARING
    key = st.family_key(family, current, when)
    if not force:
        hit = st.get(family, key)
        if hit and hit.get("payload") is not None:
            if family != "film" or not film_snapshot_stale(hit.get("payload"), current):
                return "unchanged"
    fn = compute or COMPUTE[family]
    if family != "climo" and not current.get("clock"):
        clock = stored_clock()
        if clock:
            current = dict(current)
            current["clock"] = clock
    payload = fn(current, when)
    if payload is None:
        return PREPARING
    st.put(family, payload, key)
    return READY


def refresh_missing(
    *,
    force: bool = False,
    progress: Optional[Callable[[str, str, str], None]] = None,
    now: Optional[datetime] = None,
    store: Optional[OfficialStore] = None,
    computes: Optional[dict] = None,
) -> dict:
    """Remplit ce qui manque ou a vieilli — hors chemin HTTP."""
    from voyage_api import seed_official_voyage  # noqa: PLC0415

    def _log(family: str, status: str, detail: str = "") -> None:
        if progress:
            progress(family, status, detail)
        else:
            log.info("stock %s : %s %s", family, status, detail)

    if not _REFRESH_LOCK.acquire(blocking=False):
        _log("*", "busy", "déjà en cours")
        return family_status()
    try:
        voy = seed_official_voyage()
        if voy is None:
            _log("*", PREPARING, "itinéraire officiel absent")
            return family_status()
        st = store or get_store()
        when = now or st._now()
        fns = computes or COMPUTE
        for family in COMPUTE_ORDER:
            try:
                status = refresh_family(
                    family, force=force, compute=fns.get(family),
                    now=when, store=st, voy=_load_official() or voy,
                )
                _log(family, status)
            except Exception as exc:
                log.warning("stock %s : %s", family, exc)
                _log(family, PREPARING, str(exc)[:160])
        return st.status()
    finally:
        _REFRESH_LOCK.release()


# ── remplisseur : un PROCESSUS séparé (RC18) ─────────────────────────────────
# Le calcul (horloge sur 8 878 sommets, 845 moments, films, ETA) tient le GIL : dans le processus de l'API,
# la boucle d'événements ne reprend la main que par miettes — 27 sept. : 97 % CPU, /clock en 7 s au lieu de
# 5 ms, POST /voyage coupé par Cloudflare à 100 s, 1 430 lignes rouges chez le bot. L'API ne calcule donc
# JAMAIS : elle lance scripts/prepare_official_store.py --loop (priorité basse), le réveille par un fichier
# « nudge », et relit le stock quand il change (stamp). Mode « thread » conservé pour les tests.

WORKER_MODE = (os.environ.get("NAVIGUIDE_OFFICIAL_WORKER_MODE") or "process").strip().lower()
FILL_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_official_store.py"
FILL_NICE = int(os.environ.get("NAVIGUIDE_OFFICIAL_FILL_NICE") or 10)


def fill_pidfile() -> Path:
    return disk_root() / "fill-worker.pid"


def fill_nudgefile() -> Path:
    return disk_root() / "fill-worker.nudge"


def fill_logfile() -> Path:
    return disk_root() / "fill-worker.log"


def _process_command(pid: int) -> str:
    import subprocess  # noqa: PLC0415
    try:
        out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def fill_process_alive() -> Optional[int]:
    """PID du remplisseur s'il tourne ET vient de CE checkout (un remplisseur d'un ancien worktree écrirait
    un stock d'un autre format : on le remplace)."""
    try:
        raw = fill_pidfile().read_text(encoding="utf-8").strip().splitlines()
        pid = int(raw[0])
        script = raw[1] if len(raw) > 1 else ""
        stamp = raw[2] if len(raw) > 2 else ""
    except (OSError, ValueError, IndexError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    cmd = _process_command(pid)
    if FILL_SCRIPT.name not in cmd:
        return None
    # Autre checkout, OU même chemin mais code changé (le poste réutilise toujours ~/bim-lots/recette : après un
    # rebuild, le remplisseur en mémoire est celui de l'ancienne branche) → on le remplace.
    if (script and script != str(FILL_SCRIPT)) or (stamp and stamp != _fill_script_stamp()):
        log.warning("stock officiel : remplisseur d'un autre code (%s, pid %s) — arrêté", script or "?", pid)
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        return None
    return pid


def _fill_script_stamp() -> str:
    """Empreinte du code du remplisseur : mtime le plus récent du script ET des modules serveur qu'il importe
    (le poste réutilise le même chemin de worktree : seul le contenu change entre deux rebuilds)."""
    try:
        latest = FILL_SCRIPT.stat().st_mtime_ns
        for p in Path(__file__).resolve().parent.glob("*.py"):
            latest = max(latest, p.stat().st_mtime_ns)
        return str(latest)
    except OSError:
        return ""


def ensure_fill_process() -> Optional[int]:
    """Lance le remplisseur s'il ne tourne pas. Jamais de calcul dans l'API."""
    import subprocess  # noqa: PLC0415
    import sys as _sys  # noqa: PLC0415
    with _LOCK:
        pid = fill_process_alive()
        if pid:
            return pid
        if not FILL_SCRIPT.exists():
            log.warning("stock officiel : %s absent — pas de remplisseur", FILL_SCRIPT)
            return None
        # Le remplisseur est de l'arrière-plan : sous NAVIGUIDE_LLM_MODE=on-demand (défaut, 28 sept.) il ne fait
        # aucun appel LLM payant — le stock porte le brut, le « Rédigé » ne vient que sur demande (mode all).
        env = {**os.environ, "NAVIGUIDE_OFFICIAL_STORE_DIR": str(disk_root()), "NAVIGUIDE_OFFICIAL_WORKER": "0",
               "NAVIGUIDE_LLM_BACKGROUND": "1"}
        try:
            fill_logfile().parent.mkdir(parents=True, exist_ok=True)
            logf = open(fill_logfile(), "a", encoding="utf-8")   # noqa: SIM115 — hérité par l'enfant
            p = subprocess.Popen(
                [_sys.executable, str(FILL_SCRIPT), "--loop", "--period", str(int(max(60.0, PERIOD_S))), "--nice", str(FILL_NICE)],
                cwd=str(FILL_SCRIPT.parents[1]), env=env, stdout=logf, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
            logf.close()
        except Exception as exc:
            log.warning("stock officiel : remplisseur non lancé : %s", exc)
            return None
        try:
            fill_pidfile().write_text(f"{p.pid}\n{FILL_SCRIPT}\n{_fill_script_stamp()}\n", encoding="utf-8")
        except OSError:
            pass
        log.info("stock officiel : remplisseur lancé (pid %s, nice %s, période %s s)", p.pid, FILL_NICE, int(PERIOD_S))
        return p.pid


def nudge_fill_process() -> None:
    """Demande un passage tout de suite : le remplisseur surveille la date de ce fichier."""
    try:
        f = fill_nudgefile()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_iso(_utc_now()), encoding="utf-8")
    except OSError:
        pass


def start_worker() -> None:
    """Au boot. Mode process (défaut) : lance le remplisseur externe. Mode thread : fil daemon (tests)."""
    global _WORKER_STARTED
    if not worker_enabled():
        return
    if WORKER_MODE != "thread":
        ensure_fill_process()
        return
    with _LOCK:
        if _WORKER_STARTED:
            return
        _WORKER_STARTED = True
    threading.Thread(target=_worker_loop, name="naviguide-official-store", daemon=True).start()


def _force_film_once() -> None:
    """Au boot / premier kick : recalcule le script RF5. Pas à chaque passage."""
    global _FILM_FORCED
    with _LOCK:
        if _FILM_FORCED:
            return
        _FILM_FORCED = True
    try:
        refresh_family("film", force=True)
    except Exception:
        log.exception("stock officiel : force film")
        with _LOCK:
            _FILM_FORCED = False


def kick_worker() -> None:
    """Relance un passage en fond — le client n'attend pas, et l'API ne calcule pas (mode process)."""
    if not worker_enabled():
        return
    if WORKER_MODE != "thread":
        ensure_fill_process()
        nudge_fill_process()
        return
    start_worker()
    threading.Thread(
        target=_kick_refresh,
        name="naviguide-official-store-kick",
        daemon=True,
    ).start()


def _kick_refresh() -> None:
    refresh_missing()
    _force_film_once()


def _worker_loop() -> None:
    try:
        refresh_missing()
        _force_film_once()
    except Exception:
        log.exception("stock officiel : premier passage")
    while True:
        time.sleep(max(60.0, PERIOD_S))
        try:
            refresh_missing()
        except Exception:
            log.exception("stock officiel : passage périodique")


def reset_worker_flag() -> None:
    global _WORKER_STARTED, _FILM_FORCED
    _WORKER_STARTED = False
    _FILM_FORCED = False


# ── lecture pour les routes ──────────────────────────────────────────────────

def serve_journal(limit: int = 50, kinds: Optional[tuple] = None) -> dict:
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    import voyage_journal as journal  # noqa: PLC0415

    extra = {
        "voyageId": OFFICIAL_VOYAGE_ID,
        "days": [], "count": 0, "first": None, "last": None,
        "latest": [], "events": [], "kinds": list(journal.KINDS),
    }
    hit = get("moments")
    body = hit.get("payload") if hit and isinstance(hit.get("payload"), dict) else None
    if not body:
        return preparing_payload("moments", extra)
    summary = dict(body.get("journal") or {})
    latest = list(summary.get("latest") or [])
    events = list(summary.get("events") or [])
    if kinds:
        latest = [e for e in latest if (e or {}).get("kind") in kinds]
        events = [e for e in events if (e or {}).get("kind") in kinds]
    summary.update({
        "voyageId": OFFICIAL_VOYAGE_ID,
        "status": READY,
        "latest": latest[: max(1, int(limit))],
        "events": events,
        "kinds": list(journal.KINDS),
        **_stamp(hit),
    })
    return summary


def serve_journal_day(day: str) -> Optional[list]:
    body = payload_of("moments")
    if not body:
        return None
    days = body.get("journal_days") or {}
    return days.get(day)


def _rows_from_journal(body: dict) -> list:
    """Même journal (tick réel) au format attendu par l'onglet Journal (signature)."""
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415

    days = body.get("journal_days") or {}
    raw: list = []
    if days:
        for day in sorted(days):
            raw.extend(e for e in (days.get(day) or []) if isinstance(e, dict))
    if not raw:
        journal = body.get("journal") or {}
        raw = list(journal.get("events") or []) + list(journal.get("latest") or [])
    rows = []
    seen = set()
    for e in raw:
        t = e.get("t")
        if not t:
            continue
        sig = str(e.get("id") or e.get("signature") or f"{e.get('kind')}:{t}")
        if sig in seen:
            continue
        seen.add(sig)
        lat, lon = e.get("lat"), e.get("lon")
        title = e.get("title")
        if isinstance(title, dict):
            title = title.get("fr") or title.get("en")
        fact = e.get("name") or ""
        kind = e.get("kind") or ""
        changes = []
        if kind and kind != "position":
            changes.append({
                "kind": kind, "score": 1,
                "title": str(title or kind), "fact": str(fact),
            })
        rows.append({
            "voyageId": OFFICIAL_VOYAGE_ID,
            "seq": len(rows),
            "t": t,
            "signature": sig,
            "pos": {"lat": lat, "lon": lon} if lat is not None and lon is not None else None,
            "changes": changes,
            "moment": e,
        })
    return rows


def serve_moments(until: Optional[str] = None) -> dict:
    from voyage_clock import OFFICIAL_VOYAGE_ID  # noqa: PLC0415
    from moment_journal import _iso_le  # noqa: PLC0415

    extra = {"voyageId": OFFICIAL_VOYAGE_ID, "until": until, "count": 0, "moments": []}
    hit = get("moments")
    body = hit.get("payload") if hit and isinstance(hit.get("payload"), dict) else None
    if not body:
        return preparing_payload("moments", extra)
    rows = list(body.get("moments") or [])
    if not rows:
        rows = _rows_from_journal(body)
    if until:
        rows = [row for row in rows if _iso_le(row.get("t"), until)]
    return {
        "voyageId": OFFICIAL_VOYAGE_ID,
        "until": until,
        "count": len(rows),
        "moments": rows,
        "status": READY,
        **_stamp(hit),
    }


def serve_film(lang: str = "fr", seconds: int = 0) -> dict:
    extra = {
        "chapters": [], "source": "rules", "chars": 0,
        "targetSeconds": seconds, "hasWritten": False,
    }
    hit = get("film")
    body = hit.get("payload") if hit and isinstance(hit.get("payload"), dict) else None
    if not body:
        return preparing_payload("film", extra)
    if film_snapshot_stale(body, _load_official()):
        return preparing_payload("film", extra)
    lg = (lang or "fr")[:2].lower()
    plan = None
    variants = body.get("variants") if isinstance(body.get("variants"), dict) else {}
    by_secs = variants.get(lg) or variants.get("fr") or {}
    if by_secs:
        # La variante budget la plus proche de la durée demandée (0 = libre → la plus longue).
        want = int(seconds or 0)
        keys = sorted(int(k) for k in by_secs if str(k).isdigit())
        if keys:
            pick = keys[-1] if want <= 0 else min(keys, key=lambda k: (abs(k - want), k))
            plan = by_secs.get(str(pick))
    if plan is None:
        plan = body.get(lg) or body.get("default") or body.get("fr")
    if not isinstance(plan, dict) or not (plan.get("chapters") or []):
        return preparing_payload("film", extra)
    out = dict(plan)
    out["status"] = READY
    out.update(_stamp(hit))
    return out


def serve_eta(stop: str) -> dict:
    from ensemble_eta import empty_eta  # noqa: PLC0415

    empty = empty_eta(_utc_now(), reason="en préparation")
    empty["status"] = PREPARING
    hit = get("eta")
    body = hit.get("payload") if hit and isinstance(hit.get("payload"), dict) else None
    if not body:
        return empty
    stamp = _stamp(hit)
    stops = body.get("stops") or {}
    if stop in stops:
        out = dict(stops[stop])
        out["status"] = READY
        out.update(stamp)
        return out
    needle = (stop or "").strip().lower()
    for name, payload in stops.items():
        if needle and needle in name.lower():
            out = dict(payload)
            out["status"] = READY
            out.update(stamp)
            return out
    return empty


def serve_plan_review() -> dict:
    extra = {"legs": []}
    hit = get("plan_review")
    body = hit.get("payload") if hit and isinstance(hit.get("payload"), dict) else None
    if not body:
        return preparing_payload("plan_review", extra)
    out = dict(body)
    out["status"] = READY
    out.update(_stamp(hit))
    return out


def serve_climo() -> Optional[dict]:
    return payload_of("climo")


def append_note_to_store(note: dict) -> None:
    """Écriture humaine : on met à jour le snapshot, on ne recalcule rien."""
    body = payload_of("moments")
    if not body:
        return
    payload = json.loads(json.dumps(body))
    journal = payload.setdefault("journal", {})
    latest = journal.setdefault("latest", [])
    latest.insert(0, note)
    events = journal.setdefault("events", [])
    events.insert(0, note)
    journal["count"] = int(journal.get("count") or 0) + 1
    day = (note.get("t") or "")[:10]
    if day:
        days = payload.setdefault("journal_days", {})
        days.setdefault(day, []).append(note)
    put("moments", payload)

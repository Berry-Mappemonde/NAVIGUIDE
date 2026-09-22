"""Base embarquée du simulateur — SQLite, un fichier dans `voyage_data/`.

Première table : les **perles** (sacs `ici()` échantillonnés le long de la
route officielle, lot P). Un sac riche (toutes les couches sans horodatage)
ou thin (ZEE, ports d'entrée, AMP, ports), sa position, son moment.

Pourquoi SQLite et pas un JSON : 3 272 perles riches font ~60 Mo ; on les
lit une par une (clé), on les remplace au fil du chauffage, on veut les
garder sur disque entre deux redémarrages sans réécrire tout le fichier
toutes les 30 s. Le module stdlib suffit ; WAL pour que le chauffeur
écrive pendant que les requêtes lisent. Sauvegardé avec `voyage_data/`.
Pas de MongoDB côté simulateur : Mongo reste la base de Blue Intelligence.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

log = logging.getLogger("naviguide-simulator.store")

_LOCK = threading.RLock()
_conn: Optional[sqlite3.Connection] = None
_path: Optional[Path] = None

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS pearls ("
    " key TEXT PRIMARY KEY,"
    " lat REAL, lon REAL,"
    " kind TEXT NOT NULL,"      # thin | rich
    " bag TEXT NOT NULL,"       # JSON
    " ts REAL NOT NULL)",
    "CREATE INDEX IF NOT EXISTS pearls_kind ON pearls(kind)",
    # Generic namespaced cache: escale sheets (lot C), pre-generated stories (lot F)…
    "CREATE TABLE IF NOT EXISTS kv ("
    " ns TEXT NOT NULL,"
    " key TEXT NOT NULL,"
    " value TEXT NOT NULL,"     # JSON
    " ts REAL NOT NULL,"
    " PRIMARY KEY (ns, key))",
)


def db_path() -> Path:
    from voyage_store import voyage_dir  # noqa: PLC0415
    return voyage_dir() / "naviguide.sqlite"


def _connect() -> sqlite3.Connection:
    global _conn, _path
    p = db_path()
    with _LOCK:
        if _conn is not None and _path == p:
            return _conn
        close()
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p), check_same_thread=False, isolation_level=None, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        for stmt in _SCHEMA:
            conn.execute(stmt)
        _conn, _path = conn, p
        return conn


def close() -> None:
    global _conn, _path
    with _LOCK:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:  # defensive
                pass
        _conn, _path = None, None


def reset() -> None:
    """Tests: forget the connection so a new voyage dir takes effect."""
    close()


# ── perles ──────────────────────────────────────────────────────────────────

def get_pearl(key: str) -> Optional[dict]:
    """{ kind, bag, ts } or None. Never raises (a broken store = a cache miss)."""
    try:
        with _LOCK:
            row = _connect().execute("SELECT kind, bag, ts FROM pearls WHERE key = ?", (key,)).fetchone()
    except Exception as exc:
        log.warning("store perles (lecture) : %s", exc)
        return None
    if not row:
        return None
    try:
        return {"kind": row[0], "bag": json.loads(row[1]), "ts": float(row[2])}
    except Exception:
        return None


def put_pearl(key: str, bag: dict, kind: str = "thin", lat: float | None = None,
              lon: float | None = None, ts: float | None = None) -> bool:
    """Insert or replace. A rich pearl is never downgraded by a thin one."""
    try:
        payload = json.dumps(bag, ensure_ascii=False, default=str)
        with _LOCK:
            conn = _connect()
            cur = conn.execute("SELECT kind FROM pearls WHERE key = ?", (key,)).fetchone()
            if cur and cur[0] == "rich" and kind != "rich":
                return False
            conn.execute(
                "INSERT OR REPLACE INTO pearls (key, lat, lon, kind, bag, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (key, lat, lon, kind, payload, float(ts if ts is not None else time.time())),
            )
        return True
    except Exception as exc:
        log.warning("store perles (écriture) : %s", exc)
        return False


def delete_pearl(key: str) -> bool:
    try:
        with _LOCK:
            cur = _connect().execute("DELETE FROM pearls WHERE key = ?", (key,))
            return bool(cur.rowcount)
    except Exception as exc:
        log.warning("store perles (suppression) : %s", exc)
        return False


def count_pearls() -> dict[str, int]:
    try:
        with _LOCK:
            rows = _connect().execute("SELECT kind, COUNT(*) FROM pearls GROUP BY kind").fetchall()
    except Exception:
        return {"total": 0, "rich": 0, "thin": 0}
    out = {"total": 0, "rich": 0, "thin": 0}
    for kind, n in rows:
        out[kind if kind in out else "thin"] += int(n)
        out["total"] += int(n)
    return out


def purge_pearls(older_than_s: float, kind: str | None = None) -> int:
    """Drop pearls older than `older_than_s` (all kinds, or one)."""
    cutoff = time.time() - float(older_than_s)
    try:
        with _LOCK:
            conn = _connect()
            if kind:
                cur = conn.execute("DELETE FROM pearls WHERE ts < ? AND kind = ?", (cutoff, kind))
            else:
                cur = conn.execute("DELETE FROM pearls WHERE ts < ?", (cutoff,))
            return int(cur.rowcount or 0)
    except Exception as exc:
        log.warning("store perles (purge) : %s", exc)
        return 0


def iter_pearls(kind: str | None = None) -> Iterator[tuple[str, dict]]:
    """(key, { kind, bag, ts }) for every pearl — used by the warmer's status only."""
    try:
        with _LOCK:
            if kind:
                rows = _connect().execute("SELECT key, kind, bag, ts FROM pearls WHERE kind = ?", (kind,)).fetchall()
            else:
                rows = _connect().execute("SELECT key, kind, bag, ts FROM pearls").fetchall()
    except Exception as exc:
        log.warning("store perles (parcours) : %s", exc)
        return iter(())
    def gen():
        for key, k, bag, ts in rows:
            try:
                yield key, {"kind": k, "bag": json.loads(bag), "ts": float(ts)}
            except Exception:
                continue
    return gen()


def import_legacy_json(path: Path, ttl_s: float) -> int:
    """One-time migration of the former `ici_thin_cache.json` (thin bags)."""
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        log.warning("ancien cache perles illisible (%s) : ignoré", exc)
        return 0
    now = time.time()
    n = 0
    for key, hit in (data or {}).items():
        if not isinstance(hit, dict) or "bag" not in hit:
            continue
        ts = float(hit.get("ts") or 0)
        if now - ts > ttl_s:
            continue
        parts = key.split(":")
        if len(parts) != 3:  # older keys carried the month: dead weight now
            continue
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except Exception:
            lat = lon = None
        if put_pearl(key, hit["bag"], "thin", lat, lon, ts):
            n += 1
    try:
        path.rename(path.with_suffix(".json.migrated"))
    except Exception:
        pass
    log.info("cache perles : %d sacs thin migrés vers SQLite", n)
    return n


# ── cache générique (ns, key) ────────────────────────────────────────────────

def kv_get(ns: str, key: str, max_age_s: float | None = None) -> Optional[dict]:
    """{ value, ts } or None (missing, stale, or broken store)."""
    try:
        with _LOCK:
            row = _connect().execute("SELECT value, ts FROM kv WHERE ns = ? AND key = ?", (ns, key)).fetchone()
    except Exception as exc:
        log.warning("store kv (lecture) : %s", exc)
        return None
    if not row:
        return None
    ts = float(row[1])
    if max_age_s is not None and time.time() - ts > float(max_age_s):
        return None
    try:
        return {"value": json.loads(row[0]), "ts": ts}
    except Exception:
        return None


def kv_put(ns: str, key: str, value: Any) -> bool:
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        with _LOCK:
            _connect().execute(
                "INSERT OR REPLACE INTO kv (ns, key, value, ts) VALUES (?, ?, ?, ?)",
                (ns, key, payload, time.time()),
            )
        return True
    except Exception as exc:
        log.warning("store kv (écriture) : %s", exc)
        return False


def kv_delete(ns: str, key: str) -> bool:
    """Drop one kv row. True if a row was removed. Never wipes the namespace."""
    try:
        with _LOCK:
            cur = _connect().execute("DELETE FROM kv WHERE ns = ? AND key = ?", (ns, key))
            return int(cur.rowcount or 0) > 0
    except Exception as exc:
        log.warning("store kv (suppression) : %s", exc)
        return False


def kv_count(ns: str) -> int:
    try:
        with _LOCK:
            row = _connect().execute("SELECT COUNT(*) FROM kv WHERE ns = ?", (ns,)).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0


def kv_purge(ns: str, older_than_s: float) -> int:
    cutoff = time.time() - float(older_than_s)
    try:
        with _LOCK:
            cur = _connect().execute("DELETE FROM kv WHERE ns = ? AND ts < ?", (ns, cutoff))
            return int(cur.rowcount or 0)
    except Exception:
        return 0


def info() -> dict[str, Any]:
    p = db_path()
    size = p.stat().st_size if p.exists() else 0
    return {
        "path": str(p),
        "bytes": size,
        **count_pearls(),
        "escales": kv_count("escale"),
        "stories": kv_count("story"),
        "truth": kv_count("truth"),
        "hindcast": kv_count("hindcast"),
        "watch": kv_count("watch"),
        "enrich": kv_count("enrich"),
    }

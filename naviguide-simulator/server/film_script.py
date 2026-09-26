"""Script du film 2:30 — brut (règles), sélection, version rédigée (lots F3 / R9c).

Le LLM ne produit jamais un nombre : `filter_numbers` + balises `[[ev:id]]`.
Rédigé **chapitre par chapitre**, préchauffé, cache SQLite ns `film-story`.
Jamais généré au clic. Repli : le brut.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from story_cascade import cascade_text, expand_spoken_units, filter_numbers, split_short_sentences
from voyage_clock import OFFICIAL_T0

FILM_MAX_CHARS = 2400
FILM_BUDGET_CHARS = 2400
FILM_WRITE_MIN = 2160
FILM_WRITE_MAX = 2640
FILM_CHAPTER_FLOOR = 120
FILM_CHAPTER_MAX_CHANGES = 3
KIND_GROUP_FRAC = 0.10
FILM_MIN_EVENTS = 6
FILM_MAX_EVENTS = 9
FILM_GAP_FRAC = 0.03
KIND_RANK = {"wx": 0, "climo": 1, "sci": 2, "amp": 3, "zee": 4, "poe": 5, "note": 6, "stop": 7}
SCORED = frozenset({"wx", "climo", "sci", "amp", "zee", "poe", "note"})
CANDIDATE_KINDS = frozenset({"stop", "zee", "amp", "poe", "wx", "climo", "sci", "note"})
BUBBLE_KINDS = frozenset({"stop", "zee", "wx", "amp", "sci", "climo"})
SKIPPER_GALE_KT = 34.0
HS_BUBBLE_M = 3.0
CONNECTORS = {
    "fr": ["Puis", "Ensuite", "Plus loin", "De là", "Sur la route", "À la jambe suivante"],
    "en": ["Then", "Next", "Further on", "From there", "On the way", "On the next leg"],
}
CHANGE_PRIORITY = {
    "escale": 0, "approche": 1, "alert-on": 2, "station": 3,
    "zee-enter": 4, "amp": 5, "marina": 6, "cyclone": 7, "culture": 8,
    "port": 9, "regime": 10, "alert-off": 11,
}
BUBBLE_KIND = {
    "escale": "stop", "approche": "stop", "alert-on": "wx", "alert-off": "wx",
    "zee-enter": "zee", "station": "sci", "amp": "amp", "regime": "climo",
    "marina": "stop", "cyclone": "climo", "culture": "stop", "port": "poe",
}
AROUND_TO_KIND = {
    "marina": "marina", "science": "station", "station": "station",
    "mpa": "amp", "amp": "amp", "cyclone": "cyclone", "culture": "culture",
    "port": "port",
}
NAMELESS_CYCLONE = re.compile(
    r"traces de cyclone|cyclone tracks|saison cyclonique|cyclone season|ce mois-ci|this month",
    re.I,
)
CYCLONE_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
DIST_UNIT_RE = re.compile(
    r"(?P<num>\d+(?:[ \u00a0]\d{3})*(?:[.,]\d+)?)\s*"
    r"(?P<unit>nm|milles?\s+nautiques?|nautical\s+miles?)\b",
    re.I,
)
DECIMAL_RE = re.compile(r"\d+[.,]\d{1,2}(?!\d)")
GENERIC_CYCLONE = frozenset({"cyclone", "cyclones"})
COLOR_KINDS = frozenset({
    "station", "zee-enter", "amp", "regime", "marina", "cyclone", "culture", "port",
})
FILM_CHAPTER_MAX_FREE = 10
FILM_FREE_MAX_WORDS = 800
ROUTE_NEAR_NM = 15.0
NM_TO_KM = 1.852
ALWAYS_KINDS = frozenset({
    "escale", "approche", "zee-enter", "alert-on", "cyclone", "culture",
})
GENERIC_TITLES = frozenset({
    "station croisée", "station", "stations", "croisée", "croisee",
    "marina croisée", "marina", "marinas",
    "aire marine protégée", "amp", "mpa",
    "formalités d'entrée", "ports d'entrée", "port d'entrée",
    "autour du bateau", "zee",
})
NO_DATA_RE = re.compile(
    r"aucun port d'entr[ée]e|no official port of entry|n'est connu",
    re.I,
)
DIST_IN_TEXT = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:nm|milles?\s+nautiques?)",
    re.I,
)
DIST_PAREN_RE = re.compile(
    r"\s*\(\s*\d+(?:[.,]\d+)?\s*(?:nm|milles?|km)[^)]*\)\s*",
    re.I,
)
LIST_PREFIX_RE = re.compile(
    r"^(?:ports? d'entr[ée]e|formalit[ée]s d'entr[ée]e|entr[ée]e dans)\s*:?\s*",
    re.I,
)
IUCN_RE = re.compile(r"\bIUCN\s+\S+", re.I)
TECH_PAREN_RE = re.compile(
    r"\s*\((?:unassigned|overlapping claim|wdpa:?\s*\d+|iucn[^)]*|cat(?:egory)?\s*[ivx0-9]+)\)\s*",
    re.I,
)
OVERLAP_RE = re.compile(r"overlapping claim", re.I)
LANE_LABELS = {
    "fr": {
        "dover strait": "détroit du Pas de Calais",
        "north sea": "mer du Nord",
        "bay of biscay": "golfe de Gascogne",
        "gibraltar": "détroit de Gibraltar",
        "strait of gibraltar": "détroit de Gibraltar",
        "western med": "Méditerranée occidentale",
        "red sea": "mer Rouge",
        "gulf of aden": "golfe d'Aden",
        "indian ocean w": "océan Indien ouest",
        "malacca": "détroit de Malacca",
        "south china sea": "mer de Chine méridionale",
        "cape approaches": "approches du Cap",
        "caribbean w": "Caraïbe ouest",
        "n atlantic main": "Atlantique nord",
        "coral sea lane": "mer de Corail",
        "torres commercial": "détroit de Torrès",
    },
    "en": {
        "gibraltar": "Strait of Gibraltar",
        "strait of gibraltar": "Strait of Gibraltar",
        "bay of biscay": "Bay of Biscay",
    },
}
_ZEE_NATION = (
    (re.compile(r"spanish|espagn", re.I), ("espagnoles", "Spanish")),
    (re.compile(r"french|fran[cç]ais", re.I), ("françaises", "French")),
    (re.compile(r"italian|italien", re.I), ("italiennes", "Italian")),
    (re.compile(r"portuguese|portugai", re.I), ("portugaises", "Portuguese")),
    (re.compile(r"british|britann", re.I), ("britanniques", "British")),
    (re.compile(r"american|am[ée]ricain|united states", re.I), ("américaines", "American")),
    (re.compile(r"canadian|canadien", re.I), ("canadiennes", "Canadian")),
    (re.compile(r"brazilian|br[ée]sil", re.I), ("brésiliennes", "Brazilian")),
    (re.compile(r"australian|australien", re.I), ("australiennes", "Australian")),
    (re.compile(r"new zealand|n[ée]o-z[ée]land", re.I), ("néo-zélandaises", "New Zealand")),
    (re.compile(r"moroccan|maroc", re.I), ("marocaines", "Moroccan")),
    (re.compile(r"algerian|alg[ée]rien", re.I), ("algériennes", "Algerian")),
    (re.compile(r"venezuel", re.I), ("vénézuéliennes", "Venezuelan")),
    (re.compile(r"cuban|cubain", re.I), ("cubaines", "Cuban")),
    (re.compile(r"fijian|fidj", re.I), ("fidjiennes", "Fijian")),
    (re.compile(r"indonesian|indon[ée]sien", re.I), ("indonésiennes", "Indonesian")),
    (re.compile(r"mexican|mexic", re.I), ("mexicaines", "Mexican")),
    (re.compile(r"colombian|colombien", re.I), ("colombiennes", "Colombian")),
    (re.compile(r"dutch|n[ée]erland", re.I), ("néerlandaises", "Dutch")),
    (re.compile(r"irish|irland", re.I), ("irlandaises", "Irish")),
    (re.compile(r"norwegian|norv[ée]gien", re.I), ("norvégiennes", "Norwegian")),
    (re.compile(r"japanese|japon", re.I), ("japonaises", "Japanese")),
    (re.compile(r"chinese|chinoi", re.I), ("chinoises", "Chinese")),
    (re.compile(r"south african|sud-africain", re.I), ("sud-africaines", "South African")),
    (re.compile(r"argentine", re.I), ("argentines", "Argentine")),
    (re.compile(r"chilean|chilien", re.I), ("chiliennes", "Chilean")),
    (re.compile(r"senegalese|s[ée]n[ée]gal", re.I), ("sénégalaises", "Senegalese")),
    (re.compile(r"maltese|maltais", re.I), ("maltaises", "Maltese")),
    (re.compile(r"greek|grec", re.I), ("grecques", "Greek")),
    (re.compile(r"tunisian|tunisien", re.I), ("tunisiennes", "Tunisian")),
    (re.compile(r"mauritan", re.I), ("mauritaniennes", "Mauritanian")),
    (re.compile(r"papua|papou", re.I), ("papouanes", "Papua New Guinean")),
    (re.compile(r"philippine", re.I), ("philippines", "Philippine")),
)


def connector_at(i: int, lang: str = "fr") -> str:
    """Connecteur du paragraphe i : `connecteurs[i % n]`, jamais le même à la suite."""
    cons = CONNECTORS["en" if _en(lang) else "fr"]
    return cons[int(i) % len(cons)]


MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
EV_TAG = re.compile(r"\[\[ev:([^\]]+)\]\]")
TAG_STRIP = re.compile(r"\[\[(?:ev|ch):[^\]]+\]\]\s*")
WRITE_MAX_TOKENS = 1200


def _en(lang: str) -> bool:
    return str(lang or "").lower().startswith("en")


def _ms(iso: Any) -> Optional[int]:
    if isinstance(iso, (int, float)) and iso > 1e11:
        return int(iso)
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(t.timestamp() * 1000)


def _iso(ms: Optional[int]) -> Optional[str]:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rebase_iso(iso: Any, from_t0: str, to_t0: str) -> Any:
    """Décale une ISO de from_t0 vers to_t0 (mêmes durées, aucune date inventée)."""
    a, fr, to = _ms(iso), _ms(from_t0), _ms(to_t0)
    if a is None or fr is None or to is None or fr == to:
        return iso
    return _iso(a + (to - fr))


def resolve_film_t0(t0: str | None) -> str:
    if not t0 or _ms(t0) is None:
        return OFFICIAL_T0
    return t0


def day_month(iso: Any, lang: str = "fr", *, year: bool = False) -> str:
    t = _ms(iso)
    if t is None:
        return ""
    d = datetime.fromtimestamp(t / 1000.0, tz=timezone.utc)
    m = MONTHS["en" if _en(lang) else "fr"][d.month - 1]
    day = d.day
    y = f" {d.year}" if year else ""
    if _en(lang):
        return f"{day} {m}{y}"
    return f"{'1er' if day == 1 else day} {m}{y}"


def short_name(name: str) -> str:
    return re.sub(r"\s*\(Berry, Indre\)\s*", "", str(name or "")).strip()


def norm_stop(name: str) -> str:
    """« Ajaccio » ≡ « Ajaccio (Corse) ». Berry n'escale pas deux fois au même port."""
    s = re.sub(r"\s*\([^)]*\)\s*", " ", str(name or ""))
    return re.sub(r"\s+", " ", s).strip().casefold()


def same_stop(a: str, b: str) -> bool:
    na, nb = norm_stop(a), norm_stop(b)
    return bool(na) and na == nb


def _is_generic_title(title: str, kind: str = "") -> bool:
    t = re.sub(r"\s+", " ", str(title or "")).strip().casefold()
    if not t:
        return True
    if t in GENERIC_TITLES:
        return True
    k = str(kind or "").casefold()
    return bool(k) and (t == k or t == f"{k} croisée" or t == f"{k} croisee")


def extract_named(title: Any, fact: Any, kind: str = "") -> str:
    """Nom réel, ou vide. Titre égal au type → silence."""
    for raw in (title, fact):
        s = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not s or NO_DATA_RE.search(s) or _is_generic_title(s, kind):
            continue
        s = LIST_PREFIX_RE.sub("", s).strip(" :")
        s = DIST_PAREN_RE.sub("", s).strip()
        s = re.sub(
            r"^(station|marina|aire marine protégée|amp)\s+",
            "",
            s,
            flags=re.I,
        ).strip()
        if s and not _is_generic_title(s, kind):
            return s
    return ""


def clean_spoken_label(raw: str, lang: str = "fr") -> str:
    """Libellé déclamable : IUCN, parenthèses techniques, anglais des couloirs."""
    s = short_name(raw or "")
    s = IUCN_RE.sub("", s)
    s = TECH_PAREN_RE.sub(" ", s)
    s = OVERLAP_RE.sub("", s)
    s = re.sub(r"\s*\(\s*\)\s*", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" :-—,")
    table = LANE_LABELS["en" if _en(lang) else "fr"]
    return table.get(s.casefold(), s)


def zee_waters_label(name: str, lang: str = "fr") -> str:
    raw = clean_spoken_label(name, lang)
    if not raw:
        return ""
    if re.search(r"haute mer|high seas", raw, re.I):
        return ""
    for rx, (fr, en) in _ZEE_NATION:
        if rx.search(raw):
            return f"{en} waters" if _en(lang) else f"les eaux {fr}"
    rest = re.sub(
        r"zone économique exclusive|exclusive economic zone|eez|zee",
        "",
        raw,
        flags=re.I,
    )
    rest = rest.strip(" ()-")
    had_zee = bool(re.search(
        r"zone économique|exclusive economic|eez|\bzee\b|eaux",
        raw,
        re.I,
    ))
    if rest and had_zee and not _is_generic_title(rest, "zee"):
        return f"{rest} waters" if _en(lang) else f"les eaux {rest}"
    return ""


def change_place_name(change: dict) -> str:
    kind = str(change.get("kind") or "")
    title = str(change.get("title") or "")
    fact = str(change.get("fact") or "")
    if kind == "escale":
        title = title.replace("Arrivée à ", "").replace("Arrival at ", "").strip()
    if kind == "zee-enter":
        title = LIST_PREFIX_RE.sub("", title).strip(" :")
    if kind == "cyclone":
        name, _year = cyclone_name_year(change)
        return name
    return clean_spoken_label(extract_named(title, fact, kind))


def change_distance_nm(change: dict) -> Optional[float]:
    if isinstance(change.get("nm"), (int, float)):
        return float(change["nm"])
    blob = f"{change.get('fact') or ''} {change.get('title') or ''}"
    found = DIST_IN_TEXT.search(blob)
    if not found:
        return None
    try:
        return float(found.group(1).replace(",", "."))
    except ValueError:
        return None


def change_on_route(change: dict) -> bool:
    kind = str(change.get("kind") or "")
    if kind in ALWAYS_KINDS:
        return True
    nm = change_distance_nm(change)
    if nm is not None and nm > ROUTE_NEAR_NM:
        return False
    return True


def change_is_speakable(change: dict) -> bool:
    kind = str(change.get("kind") or "")
    if kind in {"regime", "alert-off"}:
        return False
    if kind == "alert-on":
        return bool(str(change.get("fact") or change.get("title") or "").strip())
    if kind == "cyclone":
        return bool(cyclone_name_year(change)[0])
    if kind == "culture":
        return bool(change_place_name(change) or change.get("fact"))
    return bool(change_place_name(change))


def _air_stop_key(name: str) -> str:
    s = str(name or "").casefold()
    if "cayenne" in s:
        return "cayenne"
    if "halifax" in s:
        return "halifax"
    return ""


def _is_air_leg(a: str, b: str) -> bool:
    x, y = _air_stop_key(a), _air_stop_key(b)
    return (x == "cayenne" and y == "halifax") or (x == "halifax" and y == "cayenne")


def _is_land_leg(a: str, b: str) -> bool:
    return (
        is_saint_maur(a) and bool(_ROCHELLE_RE.search(str(b or "")))
    ) or (
        is_saint_maur(b) and bool(_ROCHELLE_RE.search(str(a or "")))
    )


def _window_vehicle(frm: dict | None, to: dict | None) -> str:
    for src in (frm, to):
        veh = (src or {}).get("vehicle")
        if veh in {"plane", "land", "main"}:
            return str(veh)
    a = (frm or {}).get("name") or ""
    b = (to or {}).get("name") or ""
    if _is_air_leg(a, b):
        return "plane"
    if _is_land_leg(a, b):
        return "land"
    return "main"


def _window_dest_name(w: dict) -> str:
    return short_name(
        w.get("destName") or (w.get("to") or {}).get("name") or w.get("toName") or ""
    )


def _window_depart_ms(w: dict) -> Optional[int]:
    dep = _departure_iso(w["from"]) if w.get("from") else None
    return _ms(dep) if dep else w.get("tA")


def _km_label(nm: Any, lang: str) -> str:
    try:
        km = int(round(float(nm or 0) * NM_TO_KM))
    except (TypeError, ValueError):
        return ""
    if _en(lang):
        return f"{km} kilometer" + ("" if km == 1 else "s")
    return f"{km} kilomètre" + ("" if km == 1 else "s")


def script_words(chapters: list[dict]) -> int:
    blob = " ".join(c.get("text") or "" for c in chapters)
    return len(re.findall(r"\S+", blob))


_SAINT_MAUR_RE = re.compile(r"saint[\s\-]*maur", re.I)
_ROCHELLE_RE = re.compile(r"rochelle", re.I)


def is_saint_maur(name: str) -> bool:
    return bool(_SAINT_MAUR_RE.search(str(name or "")))


def official_dated_stops(marks: list | None, clock: dict | None = None) -> list[dict]:
    """Escales datées, Saint-Maur + 15 mai 2026 en tête. Aucune autre date inventée."""
    raw = marks if marks else (clock or {}).get("marks")
    dated = dated_marks(raw)
    saint_raw = next(
        (m for m in (raw or []) if isinstance(m, dict) and is_saint_maur(m.get("name") or "")),
        None,
    )
    saint = next((s for s in dated if is_saint_maur(s["name"])), None)
    if saint:
        head = {**saint, "iso": OFFICIAL_T0}
    else:
        src = saint_raw or {}
        film = src.get("filmNm") if src.get("filmNm") is not None else src.get("nm")
        head = {
            "name": src.get("name") or "Saint-Maur",
            "iso": OFFICIAL_T0,
            "filmNm": float(film or 0),
            "nm": float(src["nm"]) if isinstance(src.get("nm"), (int, float)) else 0.0,
            "holdHours": float(src.get("holdHours") or 0),
            "lat": src.get("lat") if isinstance(src.get("lat"), (int, float)) else None,
            "lon": src.get("lon") if isinstance(src.get("lon"), (int, float)) else None,
        }
    rest = [s for s in dated if not is_saint_maur(s["name"])]
    # Premier départ mer (La Rochelle, filmNm ~122) : garder au 15 mai même
    # sans iso, et ne pas lui coller la date du retour (même nom, 2027).
    sea = next((s for s in rest if _ROCHELLE_RE.search(s.get("name") or "")), None)
    if sea is None:
        sea = _sea_stop([], raw, clock)
    if sea and _ROCHELLE_RE.search(sea.get("name") or ""):
        film = float(sea.get("filmNm") if sea.get("filmNm") is not None else sea.get("nm") or 0)
        if film < 2000:
            others = [s for s in rest if not same_stop(s["name"], sea["name"])]
            next_ms = _ms(others[0]["iso"]) if others else None
            sea_ms = _ms(sea.get("iso"))
            if sea_ms is None or (next_ms is not None and sea_ms >= next_ms):
                sea = {**sea, "iso": OFFICIAL_T0}
            rest = [sea, *others]
    return [head, *rest]


def _sea_stop(stops: list[dict], marks: list | None, clock: dict | None) -> Optional[dict]:
    for s in (stops or [])[1:]:
        if _ROCHELLE_RE.search(s.get("name") or ""):
            return s
    raw = list(marks or []) + list((clock or {}).get("marks") or [])
    for m in raw:
        if isinstance(m, dict) and _ROCHELLE_RE.search(str(m.get("name") or "")):
            film = m.get("filmNm") if m.get("filmNm") is not None else m.get("nm")
            return {
                "name": m["name"],
                "iso": m.get("iso"),
                "filmNm": float(film or 0),
                "nm": float(m["nm"]) if isinstance(m.get("nm"), (int, float)) else 0.0,
                "holdHours": float(m.get("holdHours") or 0),
                "lat": m.get("lat") if isinstance(m.get("lat"), (int, float)) else None,
                "lon": m.get("lon") if isinstance(m.get("lon"), (int, float)) else None,
            }
    if len(stops or []) > 1:
        return stops[1]
    return {"name": "La Rochelle"}


def merge_route_marks(route_marks: list | None, clock: dict | None) -> list[dict]:
    """Marques de la route + iso de l'horloge. Pas de date inventée."""
    clock_marks = [c for c in ((clock or {}).get("marks") or []) if isinstance(c, dict)]
    if not route_marks:
        return list(clock_marks)
    out: list[dict] = []
    for m in route_marks:
        if not isinstance(m, dict):
            continue
        row = dict(m)
        if _ms(row.get("iso")) is None:
            film = float(row.get("filmNm") if row.get("filmNm") is not None else row.get("nm") or 0)
            name = row.get("name") or ""
            hit = next(
                (
                    c for c in clock_marks
                    if abs(float(c.get("filmNm") if c.get("filmNm") is not None else c.get("nm") or 0) - film) < 0.6
                    and (not name or c.get("name") == name)
                ),
                None,
            )
            if hit is None:
                hit = next((c for c in clock_marks if name and c.get("name") == name), None)
            if hit:
                row["iso"] = hit.get("iso")
                if hit.get("holdHours") is not None:
                    row["holdHours"] = hit.get("holdHours")
                if row.get("lat") is None:
                    row["lat"] = hit.get("lat")
                if row.get("lon") is None:
                    row["lon"] = hit.get("lon")
        out.append(row)
    return out


def _days(hours: Any) -> int:
    try:
        return max(0, round(float(hours or 0) / 24.0))
    except (TypeError, ValueError):
        return 0


def _quay(entry: dict) -> int:
    if isinstance(entry.get("daysAtQuay"), (int, float)):
        return int(round(entry["daysAtQuay"]))
    return _days(entry.get("holdHours"))


def _fact_num(entry: dict, *keys: str) -> Optional[float]:
    facts = entry.get("facts") if isinstance(entry.get("facts"), dict) else {}
    for k in keys:
        v = entry.get(k, facts.get(k))
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _plain(v: Optional[float], digits: int = 0) -> str:
    if v is None:
        return ""
    if digits <= 0:
        return str(int(round(v)))
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return s


def journal_entries(journal: dict | None) -> list[dict]:
    if not isinstance(journal, dict):
        return []
    all_e = list(journal.get("events") or []) + list(journal.get("latest") or journal.get("entries") or [])
    seen: set[str] = set()
    out: list[dict] = []
    for e in all_e:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("id") or f"{e.get('kind')}:{e.get('t')}")
        if eid in seen:
            continue
        seen.add(eid)
        out.append(e)
    return out


def dated_marks(marks: list | None) -> list[dict]:
    out: list[dict] = []
    for m in marks or []:
        if not isinstance(m, dict) or not m.get("name") or _ms(m.get("iso")) is None:
            continue
        film = float(m.get("filmNm") if m.get("filmNm") is not None else m.get("nm") or 0)
        key = norm_stop(m["name"])
        if not key:
            continue
        # Fusion seulement si c'est le même port (« Ajaccio » ≡ « Ajaccio (Corse) »).
        # Deux noms distincts (Saint-Maur / La Rochelle) restent, même à filmNm 0.
        if any(same_stop(x["name"], m["name"]) for x in out):
            continue
        out.append({
            "name": m["name"],
            "iso": m["iso"],
            "filmNm": film,
            "nm": float(m["nm"]) if isinstance(m.get("nm"), (int, float)) else film,
            "holdHours": float(m.get("holdHours") or 0),
            "lat": m.get("lat") if isinstance(m.get("lat"), (int, float)) else None,
            "lon": m.get("lon") if isinstance(m.get("lon"), (int, float)) else None,
            "vehicle": m.get("vehicle") if isinstance(m.get("vehicle"), str) else None,
        })
    return sorted(out, key=lambda x: x["filmNm"])


def score_event(entry: dict) -> float:
    kind = entry.get("kind")
    if kind == "wx":
        peak = _fact_num(entry, "maxWindKnots", "windKnots") or 0.0
        dur = _fact_num(entry, "hours") or 6.0
        return peak * dur
    return {"climo": 50, "sci": 40, "amp": 30, "zee": 20, "poe": 10, "note": 5, "stop": 1}.get(kind, 0)


def is_sea_chapter(ch: dict) -> bool:
    """Jambe de mer : tout sauf Saint-Maur → La Rochelle."""
    frm = short_name(ch.get("fromName") or "")
    to = short_name(ch.get("toName") or "")
    if re.search(r"saint-?maur", frm, re.I) and re.search(r"rochelle", to, re.I):
        return False
    return True


def bubble_score(
    entry: dict | None,
    *,
    role: str | None = None,
    wind_max_kt: float | None = None,
) -> Optional[int]:
    """Score bulle {1,2,3} depuis le journal. None = pas une bulle."""
    if not isinstance(entry, dict):
        return None
    kind = entry.get("kind")
    event = entry.get("event")
    if role in {"depart", "today", "stop"} or kind in {"stop", "escale", "approche"}:
        return 3
    if kind == "alert-on":
        return 3
    if kind == "zee":
        if event and event != "enter":
            return None
        return 2
    if kind == "wx":
        wind = _fact_num(entry, "maxWindKnots", "windKnots")
        hs = _fact_num(entry, "hs", "maxHs")
        thr = float(wind_max_kt) if wind_max_kt is not None else SKIPPER_GALE_KT
        if (wind is not None and wind >= thr) or (hs is not None and hs >= HS_BUBBLE_M):
            return 3
        return None
    if kind == "amp":
        return 1
    if kind == "sci":
        return 2
    if kind == "climo":
        return 1
    return None


def _event_char_idx(ev: dict, chapter: dict, fact: str) -> int:
    text = chapter.get("text") or ""
    if not text:
        return 0
    name = short_name(ev.get("name") or "")
    for needle in (name, (fact or "")[:24]):
        if needle and len(needle) >= 3 and needle in text:
            return text.index(needle)
    t_a, t_b = _ms(chapter.get("tA")), _ms(chapter.get("tB"))
    t = ev.get("tMs")
    if t_a is not None and t_b is not None and t is not None and t_b > t_a:
        frac = max(0.0, min(1.0, (t - t_a) / (t_b - t_a)))
        return int(round(frac * max(0, len(text) - 1)))
    return 0


def _in_chapter(ev: dict, chapter: dict, last: bool, first: bool = False) -> bool:
    t_a, t_b = _ms(chapter.get("tA")), _ms(chapter.get("tB"))
    t = ev.get("tMs")
    if t is None or t_a is None or t_b is None:
        return False
    dest = chapter.get("toName") or ""
    if ev.get("kind") == "stop" and ev.get("role") not in {"depart", "today"} and dest and same_stop(dest, ev.get("name") or ""):
        return True
    # Arrivée à tB = cette jambe (]tA, tB]), pas le chapitre « départ vers » suivant.
    if first:
        return t_a <= t <= t_b
    return t_a < t <= t_b


def _bubble_payload(ev: dict, chapter: dict, lang: str, prev: dict | None = None) -> dict:
    entry = ev.get("entry") if isinstance(ev.get("entry"), dict) else ev
    score = ev.get("bubbleScore")
    if score not in {1, 2, 3}:
        score = bubble_score(entry, role=ev.get("role"))
    title = short_name(ev.get("name") or "") or (prev or {}).get("title") or entry.get("kind") or ev.get("kind") or ""
    fact = event_sentence({**ev, "name": ev.get("name") or title}, lang).strip()
    if not fact:
        fact = ((prev or {}).get("card") or {}).get("text") or (prev or {}).get("fact") or ""
    char_idx = (prev or {}).get("charIdx")
    if char_idx is None:
        char_idx = _event_char_idx(ev, chapter, fact)
    card = dict((prev or {}).get("card") or _card(entry))
    card["title"] = card.get("title") or title
    card["text"] = card.get("text") or fact
    card["kind"] = card.get("kind") or ev.get("kind")
    card["score"] = score
    if not card.get("at"):
        card["at"] = ev.get("t") or entry.get("t")
    return {
        "id": ev.get("id") or (prev or {}).get("id"),
        "charIdx": int(char_idx or 0),
        "kind": ev.get("kind") or card.get("kind"),
        "title": str(title)[:40],
        "fact": fact,
        "score": score,
        "card": card,
    }


def _synthetic_sea_event(chapter: dict, lang: str) -> dict:
    to = short_name(chapter.get("toName") or "")
    frm = short_name(chapter.get("fromName") or "")
    text = chapter.get("text") or ""
    if to:
        raw = {
            "id": f"stop:{to}:{chapter.get('tB')}",
            "kind": "stop",
            "t": chapter.get("tB"),
            "tMs": _ms(chapter.get("tB")),
            "name": to,
            "role": "stop",
            "event": "arrival",
            "entry": {"id": f"stop:{to}:{chapter.get('tB')}", "kind": "stop", "t": chapter.get("tB"), "event": "arrival", "name": to},
        }
        raw["bubbleScore"] = 3
        placed = _bubble_payload(raw, chapter, lang)
        if to in text:
            placed["charIdx"] = text.rfind(to)
        else:
            placed["charIdx"] = max(0, len(text) - 1)
        return placed
    raw = {
        "id": f"stop:{frm}:{chapter.get('tA')}",
        "kind": "stop",
        "t": chapter.get("tA"),
        "tMs": _ms(chapter.get("tA")),
        "name": frm or "mer",
        "role": "depart",
        "event": "departure",
        "entry": {"id": f"stop:{frm}:{chapter.get('tA')}", "kind": "stop", "t": chapter.get("tA"), "event": "departure", "name": frm},
    }
    raw["bubbleScore"] = 3
    placed = _bubble_payload(raw, chapter, lang)
    placed["charIdx"] = 0
    return placed


def collect_bubble_events(
    journal: dict | None,
    packed: dict | None,
    *,
    wind_max_kt: float | None = None,
) -> list[dict]:
    packed = packed or {}
    t0, t_end = packed.get("t0"), packed.get("tEnd")
    out: list[dict] = []
    seen: set[str] = set()

    def push(raw: dict, role: str | None = None) -> None:
        if not isinstance(raw, dict):
            return
        entry = raw.get("entry") if isinstance(raw.get("entry"), dict) else raw
        score = bubble_score(entry, role=role or raw.get("role"), wind_max_kt=wind_max_kt)
        if score is None:
            return
        t = _ms(raw.get("t") or entry.get("t"))
        if t is None:
            return
        if t0 is not None and t < t0:
            return
        if t_end is not None and t > t_end:
            return
        eid = str(raw.get("id") or entry.get("id") or f"{entry.get('kind')}:{entry.get('t')}")
        if not eid or eid in seen:
            return
        seen.add(eid)
        out.append({
            "id": eid,
            "kind": raw.get("kind") or entry.get("kind"),
            "t": raw.get("t") or entry.get("t"),
            "tMs": t,
            "name": short_name(raw.get("name") or entry.get("name") or ""),
            "role": role or raw.get("role"),
            "entry": entry,
            "bubbleScore": score,
        })

    for e in journal_entries(journal):
        if e.get("kind") not in BUBBLE_KINDS:
            continue
        push(e)
    for c in packed.get("candidates") or []:
        push(c, role=c.get("role"))
    out.sort(key=lambda e: (e["tMs"], e["id"]))
    return out


def attach_chapter_events(
    chapters: list[dict],
    packed: dict | None,
    journal: dict | None,
    lang: str = "fr",
    wind_max_kt: float | None = None,
) -> list[dict]:
    """Chaque chapitre porte {charIdx, kind, title, fact, score}. Mer : ≥ 1."""
    pool = collect_bubble_events(journal, packed, wind_max_kt=wind_max_kt)
    n = len(chapters or [])
    for i, ch in enumerate(chapters or []):
        first = i == 0
        last = i == n - 1
        existing = {str(e.get("id")): e for e in (ch.get("events") or []) if e.get("id")}
        placed: list[dict] = []
        seen: set[str] = set()
        for ev in pool:
            if not _in_chapter(ev, ch, last, first):
                continue
            prev = existing.get(str(ev["id"]))
            row = _bubble_payload(ev, ch, lang, prev)
            if row.get("score") not in {1, 2, 3}:
                continue
            eid = str(row.get("id") or "")
            if eid and eid in seen:
                continue
            if eid:
                seen.add(eid)
            placed.append(row)
        if is_sea_chapter(ch) and not placed:
            placed.append(_synthetic_sea_event(ch, lang))
        ch["events"] = sorted(placed, key=lambda e: (int(e.get("charIdx") or 0), str(e.get("id") or "")))
    return chapters


def _cand(entry: dict, *, role: str | None = None, score: float | None = None, name: str | None = None) -> Optional[dict]:
    t_ms = _ms(entry.get("t"))
    if t_ms is None:
        return None
    return {
        "id": str(entry.get("id") or f"{entry.get('kind')}:{entry.get('t')}"),
        "kind": entry.get("kind"),
        "t": entry.get("t"),
        "tMs": t_ms,
        "name": name if name is not None else (entry.get("name") or ""),
        "score": score if score is not None else score_event(entry),
        "role": role,
        "quayDays": _quay(entry),
        "entry": entry,
    }


def film_candidates(
    journal: dict | None,
    marks: list | None,
    clock: dict | None,
    live: dict | None,
    now_ms: int,
) -> dict[str, Any]:
    raw_marks = marks if marks else (clock or {}).get("marks")
    stops = official_dated_stops(raw_marks, clock)
    start = stops[0] if stops else None
    sea = _sea_stop(stops, raw_marks, clock)
    t0 = _ms(OFFICIAL_T0)
    t_end = _ms((live or {}).get("iso")) or now_ms
    out: list[dict] = []
    seen: set[str] = set()

    def push(c: Optional[dict]) -> None:
        if not c or c["id"] in seen:
            return
        seen.add(c["id"])
        out.append(c)

    depart_iso = OFFICIAL_T0
    if _ms(depart_iso) is not None:
        push(_cand({
            "id": "depart", "kind": "stop", "t": depart_iso, "event": "departure",
            "name": short_name((start or {}).get("name") or "Saint-Maur"),
        }, role="depart", score=10_000, name=short_name((start or {}).get("name") or "Saint-Maur")))

    seen_zee: set[Any] = set()
    seen_poe: set[Any] = set()
    seen_sci: set[Any] = set()
    for e in journal_entries(journal):
        if e.get("kind") not in CANDIDATE_KINDS:
            continue
        if e.get("kind") == "zee":
            if e.get("event") and e.get("event") != "enter":
                continue
            key = e.get("mrgid") or e.get("name")
            if not key or key in seen_zee:
                continue
            seen_zee.add(key)
        if e.get("kind") == "poe":
            key = e.get("poeId") or e.get("name")
            if not key or key in seen_poe:
                continue
            seen_poe.add(key)
        if e.get("kind") == "sci":
            key = (e.get("entity") or {}).get("id") if isinstance(e.get("entity"), dict) else e.get("name")
            if not key or key in seen_sci:
                continue
            seen_sci.add(key)
        if e.get("kind") == "stop" and e.get("event") == "departure":
            continue
        t = _ms(e.get("t"))
        if t is None:
            continue
        if t0 is not None and t < t0:
            continue
        if t_end is not None and t > t_end:
            continue
        push(_cand(e, role="stop" if e.get("kind") == "stop" else None))

    for s in stops[1:]:
        t = _ms(s["iso"])
        if t is None or (t_end is not None and t > t_end):
            continue
        if any(
            c["kind"] == "stop" and c.get("role") not in {"depart", "today"}
            and same_stop(c["name"], s["name"]) and abs(c["tMs"] - t) < 3_600_000
            for c in out
        ):
            continue
        push(_cand({
            "id": f"stop:{s['name']}:{s['iso']}", "kind": "stop", "t": s["iso"],
            "event": "arrival", "name": s["name"], "holdHours": s["holdHours"],
            "daysAtQuay": _days(s["holdHours"]),
        }, role="stop", score=1))

    today_iso = (live or {}).get("iso") or (_iso(t_end) if t_end else _iso(now_ms))
    if today_iso:
        push(_cand({
            "id": "today", "kind": "stop", "t": today_iso, "event": "arrival",
            "name": short_name((live or {}).get("fromStop") or ""),
        }, role="today", score=9_000))

    out.sort(key=lambda c: c["tMs"])
    return {"candidates": out, "t0": t0, "tEnd": t_end, "start": start, "sea": sea, "stops": stops}


def _pick_stops(cands: list[dict], max_n: int = 6) -> list[dict]:
    lst = [c for c in cands if c["kind"] == "stop" and c.get("role") not in {"depart", "today"}]
    if len(lst) <= max_n:
        return lst
    first, last = lst[0], lst[-1]
    long = sorted(
        [s for s in lst if s["quayDays"] > 2 and s is not first and s is not last],
        key=lambda s: (-s["quayDays"], s["tMs"]),
    )
    picked: list[dict] = []

    def add(s: dict) -> None:
        if s and all(x["id"] != s["id"] for x in picked):
            picked.append(s)

    add(first)
    add(last)
    for s in long:
        if len(picked) >= max_n:
            break
        add(s)
    for s in lst:
        if len(picked) >= max_n:
            break
        add(s)
    return sorted(picked, key=lambda s: s["tMs"])[:max_n]


def select_film_events(candidates: list[dict], t0: Optional[int], t_end: Optional[int]) -> list[dict]:
    lst = [c for c in candidates if c.get("tMs") is not None]
    span = (t_end or 0) - (t0 or 0)
    gap = span * FILM_GAP_FRAC if span > 0 else 0
    depart = next((c for c in lst if c.get("role") == "depart" or c["id"] == "depart"), None)
    today = next((c for c in lst if c.get("role") == "today" or c["id"] == "today"), None)
    must: list[dict] = []
    if depart:
        must.append(depart)
    must.extend(_pick_stops(lst, 6))
    if today:
        must.append(today)
    selected = list(must)
    must_ids = {m["id"] for m in must}

    def close(ev: dict) -> bool:
        return gap > 0 and any(abs(s["tMs"] - ev["tMs"]) < gap for s in selected)

    scored = [c for c in lst if c["kind"] in SCORED and c["id"] not in must_ids]
    scored.sort(key=lambda c: (-(c.get("score") or 0), KIND_RANK.get(c["kind"], 9), c["tMs"]))
    for ev in scored:
        if len(selected) >= FILM_MAX_EVENTS:
            break
        if close(ev):
            continue
        selected.append(ev)
    if len(selected) < FILM_MIN_EVENTS:
        for ev in scored:
            if len(selected) >= FILM_MIN_EVENTS:
                break
            if any(s["id"] == ev["id"] for s in selected):
                continue
            selected.append(ev)
    return sorted(selected, key=lambda c: c["tMs"])


def _join(parts: list[str], lang: str) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    sep = " and " if _en(lang) else " et "
    return f"{', '.join(parts[:-1])}{sep}{parts[-1]}"


def _day_word(n: int, lang: str) -> str:
    if _en(lang):
        return f"{n} day" + ("s" if n > 1 else "")
    return f"{n} jour" + ("s" if n > 1 else "")


def _film_seconds(seconds: Any) -> int:
    """0 = pas de budget (lot RD7). Toute valeur invalide ou négative → 0."""
    try:
        n = int(seconds)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def _facts_with_rounded(change: dict) -> str:
    """Faits + arrondis : filter_numbers accepte le chiffre déclamé."""
    blob = json.dumps(change, ensure_ascii=False, default=str)
    extras: list[str] = []
    for token in re.findall(r"\d+(?:[.,]\d+)?", blob):
        raw = token.replace(",", ".")
        try:
            extras.append(str(int(round(float(raw)))))
        except ValueError:
            continue
    return f"{blob} {' '.join(extras)}"


def _review_legs(review: dict | None) -> list[dict]:
    if not isinstance(review, dict):
        return []
    legs = review.get("legs")
    return [leg for leg in legs if isinstance(leg, dict)] if isinstance(legs, list) else []


def review_leg_for_chapter(review: dict | None, from_name: str, to_name: str) -> dict | None:
    """Jambe de review_official dont from/to sont la fenêtre du chapitre. Sinon silence."""
    frm, to = from_name or "", to_name or ""
    if not frm or not to:
        return None
    for leg in _review_legs(review):
        if same_stop(leg.get("from") or "", frm) and same_stop(leg.get("to") or "", to):
            return leg
    return None


def review_fingerprint(review: dict | None) -> str:
    bits: list[str] = []
    for leg in _review_legs(review):
        pack = leg.get("antiShipping") if isinstance(leg.get("antiShipping"), dict) else {}
        season = leg.get("season") if isinstance(leg.get("season"), dict) else {}
        lanes = ",".join(
            n.strip() for n in (pack.get("lanes") or []) if isinstance(n, str) and n.strip()
        )
        flags = ",".join(
            str(f.get("kind") or "") for f in (leg.get("flags") or []) if isinstance(f, dict)
        )
        bits.append(
            f"{leg.get('from')}|{leg.get('to')}|{lanes}|{season.get('galePct')}|{season.get('cyclones')}|{flags}"
        )
    return hashlib.sha256("\n".join(bits).encode("utf-8")).hexdigest() if bits else ""


def review_sentences(leg: dict | None, lang: str = "fr") -> list[str]:
    """Ce que la revue signale : verdict, couloirs nommés, saison. Champ inconnu = silence."""
    if not isinstance(leg, dict):
        return []
    en = _en(lang)
    bits: list[str] = []
    flags = [f for f in (leg.get("flags") or []) if isinstance(f, dict)]
    season = leg.get("season") if isinstance(leg.get("season"), dict) else None
    gale = season.get("galePct") if season else None
    cyclones = season.get("cyclones") if season else None
    pack = leg.get("antiShipping") if isinstance(leg.get("antiShipping"), dict) else None
    lanes = [
        clean_spoken_label(n.strip(), lang)
        for n in ((pack or {}).get("lanes") or [])
        if isinstance(n, str) and n.strip()
    ] if pack else []
    lanes = [n for n in lanes if n]

    alert = isinstance(cyclones, (int, float)) and cyclones > 0
    watch = bool(flags)
    if alert:
        bits.append("Alert." if en else "Alerte.")
    elif watch:
        bits.append("To watch." if en else "À surveiller.")

    if lanes:
        names = ", ".join(lanes)
        bits.append(f"Shipping lanes: {names}." if en else f"Couloirs : {names}.")

    if isinstance(gale, (int, float)):
        n = int(round(float(gale)))
        bits.append(
            f"Gale {n} percent of the time."
            if en else
            f"Coup de vent {n} % du temps."
        )

    if isinstance(cyclones, (int, float)) and cyclones > 0:
        bits.append("Cyclone season." if en else "Saison cyclonique.")

    return bits


def _append_review_sentences(bits: list[str], review: dict | None, window: dict, lang: str) -> None:
    """Ajoute les phrases de revue au chapitre. Chiffres via filter_numbers."""
    leg = review_leg_for_chapter(review, window.get("fromName") or "", window.get("toName") or "")
    if not leg:
        return
    facts = _facts_with_rounded(leg)
    for sentence in review_sentences(leg, lang):
        filtered, _dropped = filter_numbers(sentence, facts)
        sentence = (filtered or "").strip()
        if sentence:
            bits.append(sentence)


def cyclone_name_year(change: dict) -> tuple[str, str]:
    """Nom + année d'une trace : champ inconnu → vide (silence)."""
    title = short_name(change.get("title") or "")
    fact = str(change.get("fact") or "")
    blob = f"{title} {fact}".strip()
    if not blob or (NAMELESS_CYCLONE.search(blob) and not CYCLONE_YEAR_RE.search(blob)):
        return "", ""
    year = ""
    found = CYCLONE_YEAR_RE.search(blob)
    if found:
        year = found.group(1)
    name = title
    if name.casefold() in GENERIC_CYCLONE or not name:
        named = re.search(
            r"(?:cyclone\s+)?([A-ZÀ-Ý][\w\-']+)\s*\((?:19|20)\d{2}\)",
            fact, re.I,
        )
        if named:
            name = named.group(1)
        else:
            named = re.search(r"(?:cyclone\s+)([A-ZÀ-Ý][\w\-']+)", fact, re.I)
            name = named.group(1) if named else ""
    if name.casefold() in GENERIC_CYCLONE:
        name = ""
    return name, year


def _parse_dist_num(raw: str) -> Optional[float]:
    cleaned = (raw or "").replace("\u00a0", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        left, right = cleaned.split(",", 1)
        cleaned = left + right if len(right) == 3 and left.isdigit() else f"{left}.{right}"
    try:
        return float(cleaned)
    except ValueError:
        return None


def round_spoken_distances(text: str, lang: str = "fr") -> str:
    """Distances à la voix : entier, unité en toutes lettres, jamais « nm »."""

    def repl(m: re.Match) -> str:
        v = _parse_dist_num(m.group("num"))
        if v is None:
            return m.group(0)
        return _nm_label(int(round(v)), lang)

    return DIST_UNIT_RE.sub(repl, text or "")


def round_spoken_decimals(text: str) -> str:
    """Aucune décimale déclamée (Hs, kn) : on arrondit à l'entier."""

    def repl(m: re.Match) -> str:
        raw = m.group(0).replace(",", ".")
        try:
            return str(int(round(float(raw))))
        except ValueError:
            return m.group(0)

    return DECIMAL_RE.sub(repl, text or "")


def speak_film_text(text: str, lang: str = "fr") -> str:
    """Texte du film : distances arrondies, unités parlées, pas de décimale."""
    spoken = round_spoken_distances(text or "", lang)
    spoken = expand_spoken_units(spoken, lang)
    return round_spoken_decimals(spoken)


def _nm_label(nm: Any, lang: str) -> str:
    """Distance déclamée : « 1 820 milles nautiques », jamais de décimale ni « nm »."""
    try:
        v = int(round(float(nm or 0)))
    except (TypeError, ValueError):
        return ""
    if _en(lang):
        unit = "nautical mile" if v == 1 else "nautical miles"
        return f"{v:,} {unit}"
    unit = "mille nautique" if v == 1 else "milles nautiques"
    return f"{v:,} {unit}".replace(",", " ")


def event_sentence(ev: dict, lang: str = "fr", display_t0: str | None = None) -> str:
    en = _en(lang)
    e = ev.get("entry") or ev
    shown = display_t0 or OFFICIAL_T0
    when = day_month(rebase_iso(e.get("t") or ev.get("t"), OFFICIAL_T0, shown), lang)
    name = short_name(e.get("name") or ev.get("name") or "")
    if ev.get("role") == "depart":
        frm = name or "Saint-Maur"
        d = day_month(rebase_iso(e.get("t"), OFFICIAL_T0, shown), lang, year=True)
        # Pas de seaName figé : la dest de CETTE fenêtre est « départ vers X ».
        sea = short_name(ev.get("seaName") or ev.get("toName") or "")
        if sea:
            return (
                f"The Berry-Mappemonde expedition left {frm} on {d} and took the road to {sea}."
                if en else
                f"L’expédition Berry-Mappemonde a quitté {frm} le {d} et a pris la route vers {sea}."
            )
        return (
            f"The Berry-Mappemonde expedition left {frm} on {d}."
            if en else
            f"L’expédition Berry-Mappemonde a quitté {frm} le {d}."
        )
    if ev.get("role") == "today":
        place = name
        head = "Today" if en else "Aujourd’hui"
        if place:
            return f"{head}, the boat is at {place}." if en else f"{head}, le bateau est à {place}."
        return ""
    if ev.get("kind") == "stop":
        quay = _quay(e)
        sights = e.get("sights") or (e.get("facts") or {}).get("sights") or []
        named = [s if isinstance(s, str) else (s or {}).get("name") for s in sights][:2]
        named = [s for s in named if s]
        extra = f" {_join(named, lang)}." if named else ""
        q = f", {_day_word(quay, lang)} {'in port' if en else 'à quai'}" if quay else ""
        return (f"Stopover in {name} on {when}{q}.{extra}" if en else f"Escale à {name} le {when}{q}.{extra}")
    if ev.get("kind") == "wx":
        kn = _plain(_fact_num(e, "maxWindKnots", "windKnots"))
        hours = _fact_num(e, "hours")
        hs = _fact_num(e, "hs", "maxHs")
        dur = (f" for {_plain(hours)} hours" if en else f" pendant {_plain(hours)} heures") if hours is not None else ""
        sea = f", Hs {_plain(hs, 0)} m" if hs is not None else ""
        place = ""
        return (
            f"On {when}{place}, the wind rose to {kn} kn{dur}{sea}."
            if en else
            f"Le {when}{place}, le vent est monté à {kn} kn{dur}{sea}."
        )
    if ev.get("kind") == "climo":
        event = e.get("event") or ""
        detail = {
            "calms": " — equatorial calms" if en else " — calmes équatoriaux",
            "cyclone-enter": " — cyclone season" if en else " — saison cyclonique",
        }.get(event, " — wind regime" if en else " — régime de vent")
        deg = _fact_num(e, "deltaDeg")
        deg_bit = f" ({_plain(deg)}°)" if deg is not None else ""
        return (
            f"On {when}, the climate regime changed{detail}{deg_bit}."
            if en else
            f"Le {when}, le régime climatique a changé{detail}{deg_bit}."
        )
    if ev.get("kind") == "sci":
        nm = _fact_num(e, "nm")
        nm_bit = (
            (f" at {_plain(nm, 1)} nautical miles" if en else f" à {_plain(nm, 1)} milles nautiques")
            if nm is not None else ""
        )
        return (
            f"On {when}, the route passed{nm_bit} from {name}."
            if en else
            f"Le {when}, la route est passée{nm_bit} de {name}."
        )
    if ev.get("kind") == "amp":
        return (
            f"On {when}, marine protected area within reach: {name}."
            if en else
            f"Le {when}, aire marine protégée à portée : {name}."
        )
    if ev.get("kind") == "zee":
        if not name or NO_DATA_RE.search(name):
            return ""
        if re.search(r"haute mer|high seas", name, re.I):
            return f"On {when}, entered the high seas." if en else f"Le {when}, entrée en haute mer."
        waters = zee_waters_label(name, lang)
        if not waters:
            return ""
        return f"On {when}, entered {waters}." if en else f"Le {when}, entrée dans {waters}."
    if ev.get("kind") == "poe":
        if not name or NO_DATA_RE.search(name):
            return ""
        return f"On {when}, off {name}." if en else f"Le {when}, devant {name}."
    if ev.get("kind") == "note" and e.get("text"):
        note = " ".join(str(e["text"]).split())[:120]
        return (
            f"On {when}, the skipper wrote: « {note} »"
            if en else
            f"Le {when}, le skipper a noté : « {note} »"
        )
    return ""


def _departure_iso(stop: dict) -> Optional[str]:
    t = _ms(stop.get("iso"))
    if t is None:
        return None
    return _iso(t + int(float(stop.get("holdHours") or 0) * 3_600_000))


def _windows(stops: list[dict], t0: int, t_end: int) -> list[dict]:
    pts = list(stops or [{"name": "Saint-Maur", "iso": _iso(t0), "filmNm": 0}])
    pts.sort(key=lambda s: float(
        s.get("filmNm") if s.get("filmNm") is not None else s.get("nm") or 0
    ))
    out: list[dict] = []
    for i, frm in enumerate(pts):
        to = pts[i + 1] if i + 1 < len(pts) else None
        t_a = _ms(frm.get("iso")) if frm.get("iso") else (t0 if i == 0 else None)
        if t_a is None or t_a >= t_end:
            break
        dest_ms = _ms(to["iso"]) if to else None
        arrived = dest_ms is not None and dest_ms <= t_end
        dest_name = (to.get("name") or "") if to else ""
        raw_b = dest_ms if dest_ms is not None else t_end
        t_b = min(raw_b if raw_b is not None else t_end, t_end)
        if t_b <= t_a:
            # Iso égaux (Saint-Maur forcé à T0, La Rochelle le 15 mai à la même
            # heure) : plancher 1 s — `_iso` tronque à la seconde ; 1 ms
            # donnait tA == tB et filmPlan jetait le chapitre 0.
            t_b = t_a + 1000
        out.append({
            "id": f"leg-{i}",
            "from": frm,
            "to": to if arrived else None,
            "tA": t_a,
            "tB": t_b,
            "fromName": frm.get("name") or "",
            "toName": dest_name if arrived else "",
            "destName": dest_name,
            "arrived": arrived,
            "last": to is None,
            "vehicle": _window_vehicle(frm, to),
            "fromLat": frm.get("lat"),
            "fromLon": frm.get("lon"),
            "toLat": (to or {}).get("lat"),
            "toLon": (to or {}).get("lon"),
        })
        if not to or (dest_ms is not None and dest_ms >= t_end):
            break
    if not out and t_end > t0:
        out.append({
            "id": "leg-0", "from": pts[0], "to": None, "tA": t0, "tB": t_end,
            "fromName": (pts[0] or {}).get("name") or "Saint-Maur", "toName": "",
            "destName": "", "arrived": False, "last": True,
            "vehicle": _window_vehicle(pts[0], None),
            "fromLat": None, "fromLon": None, "toLat": None, "toLon": None,
        })
    return out


def _window_owns(w: dict, ev: dict, i: int) -> bool:
    dest = w.get("toName") or ""
    if ev.get("kind") == "stop" and ev.get("role") not in {"depart", "today"} and dest and same_stop(dest, ev.get("name") or ""):
        return True
    if i == 0:
        return ev["tMs"] >= w["tA"] and ev["tMs"] <= w["tB"]
    return ev["tMs"] > w["tA"] and ev["tMs"] <= w["tB"]


def _assign(events: list[dict], windows: list[dict]) -> list[list[dict]]:
    buckets: list[list[dict]] = [[] for _ in windows]
    for ev in events:
        idx = next((i for i, w in enumerate(windows) if _window_owns(w, ev, i)), None)
        if idx is None:
            idx = len(windows) - 1 if ev.get("role") == "today" else 0
        buckets[idx].append(ev)
    return buckets


def _chapter_dest(w: dict) -> dict | None:
    dest = w.get("to") if (w.get("to") or {}).get("name") else None
    return dest


def _air_sentence(w: dict, *, i: int, lang: str, display_t0: str | None = None) -> str:
    dest_name = _window_dest_name(w)
    origin = short_name((w.get("from") or {}).get("name") or "")
    if not dest_name:
        return ""
    en = _en(lang)
    back = _air_stop_key(origin) == "halifax" and _air_stop_key(dest_name) == "cayenne"
    if back:
        head = f"return flight to {dest_name}" if en else f"retour en avion vers {dest_name}"
    else:
        head = f"the crew flies to {dest_name}" if en else f"l'équipage prend l'avion pour {dest_name}"
    if i == 0:
        return f"{head[0].upper()}{head[1:]}."
    conn = connector_at(i - 1, lang)
    dep = _departure_iso(w["from"]) if w.get("from") else None
    when = day_month(rebase_iso(dep, OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    return f"{conn}, on {when}, {head}." if en else f"{conn}, le {when}, {head}."


def _close_sentence(w: dict, live: dict | None, lang: str) -> str:
    place = short_name(
        (live or {}).get("fromStop")
        or (live or {}).get("atStop")
        or (live or {}).get("name")
        or ""
    )
    if not place and w.get("arrived"):
        place = short_name(w.get("toName") or "")
    if not place:
        place = short_name(w.get("fromName") or "")
    if not place:
        return ""
    if _en(lang):
        return f"Today, the boat is at {place}."
    return f"Aujourd’hui, le bateau est à {place}."


def _depart_towards(w: dict, *, i: int, lang: str, display_t0: str | None = None) -> str:
    """Phrase de départ de CETTE fenêtre : dest de la jambe, jamais un seaName figé."""
    dest_name = _window_dest_name(w)
    origin = short_name((w.get("from") or {}).get("name") or "")
    if (w.get("vehicle") == "plane") or _is_air_leg(origin, dest_name):
        return _air_sentence(w, i=i, lang=lang, display_t0=display_t0)
    if not dest_name:
        return ""
    en = _en(lang)
    head = f"departure for {dest_name}" if en else f"départ vers {dest_name}"
    if i == 0:
        return f"{head[0].upper()}{head[1:]}."
    conn = connector_at(i - 1, lang)
    dep = _departure_iso(w["from"]) if w.get("from") else None
    when = day_month(rebase_iso(dep, OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    return f"{conn}, on {when}, {head}." if en else f"{conn}, le {when}, {head}."


def _arrival_sentence(stop: dict | None, lang: str, display_t0: str | None = None) -> str:
    if not stop or not stop.get("name") or _ms(stop.get("iso")) is None:
        return ""
    en = _en(lang)
    name = short_name(stop["name"])
    when = day_month(rebase_iso(stop["iso"], OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    quay = _days(stop.get("holdHours"))
    q = f", {_day_word(quay, lang)} {'in port' if en else 'à quai'}" if quay else ""
    return f"Arrival at {name} on {when}{q}." if en else f"Arrivée à {name} le {when}{q}."


def _card(entry: dict) -> dict:
    return {
        "id": entry.get("id"),
        "kind": entry.get("kind"),
        "title": entry.get("name") or (entry.get("title") or {}).get("fr") or entry.get("kind"),
        "text": "",
        "facts": entry.get("facts"),
        "entity": entry.get("entity"),
        "at": entry.get("t"),
    }


def _compose(windows: list[dict], buckets: list[list[dict]], *, lang: str, sea_name: str, start_name: str, live: dict | None, display_t0: str | None = None, review: dict | None = None) -> list[dict]:
    chapters: list[dict] = []
    cited: set[str] = set()
    dist = ""
    if live:
        dist = _nm_label(live.get("sailNm") if live.get("sailNm") is not None else live.get("filmNm"), lang)

    def push_arrival(bits: list[str], dest: dict | None) -> None:
        key = norm_stop((dest or {}).get("name") or "")
        sentence = _arrival_sentence(dest, lang, display_t0)
        if not sentence or not key or key in cited:
            return
        bits.append(sentence)
        cited.add(key)

    for i, w in enumerate(windows):
        bits: list[str] = []
        placed: list[dict] = []
        dest = _chapter_dest(w)
        dest_name = _window_dest_name(w)
        arrived = bool(w.get("arrived")) if "arrived" in w else bool(dest)
        depart_ms = _window_depart_ms(w) or 0
        # Ch. 0 : Saint-Maur d'abord (ordre de la route), puis la paire de
        # CETTE fenêtre. Plus de seaName figé « La Rochelle ».
        if i == 0:
            bits.append(event_sentence({
                "role": "depart", "kind": "stop", "t": OFFICIAL_T0, "name": start_name,
                "seaName": "" if dest_name else sea_name,
                "entry": {"t": OFFICIAL_T0, "name": start_name},
            }, lang, display_t0=display_t0))

        def speak_ev(ev: dict) -> None:
            if ev.get("kind") == "stop" and ev.get("role") not in {"depart", "today"}:
                return
            if ev.get("role") in {"depart", "today"}:
                return
            rich = {
                **ev,
                "seaName": dest_name or sea_name,
                "toName": dest_name,
                "distLabel": dist,
                "name": ev.get("name"),
            }
            sentence = event_sentence(rich, lang, display_t0=display_t0).strip()
            if not sentence:
                return
            char_idx = len(" ".join(bits)) + (1 if bits else 0)
            bits.append(sentence)
            entry = ev.get("entry") or {}
            card = _card(entry)
            card["text"] = sentence
            placed.append({"id": ev["id"], "charIdx": char_idx, "card": card})

        quay = [ev for ev in buckets[i] if (ev.get("tMs") or 0) < depart_ms]
        sea = [ev for ev in buckets[i] if (ev.get("tMs") or 0) >= depart_ms]
        for ev in quay:
            speak_ev(ev)
        head = _depart_towards(w, i=i, lang=lang, display_t0=display_t0)
        if head:
            bits.append(head)
        for ev in sea:
            speak_ev(ev)
        if arrived:
            push_arrival(bits, dest)
        _append_review_sentences(bits, review, w, lang)
        if i == len(windows) - 1:
            close = _close_sentence(w, live, lang)
            if close and close not in bits:
                bits.append(close)
        text = speak_film_text(re.sub(r"\s{2,}", " ", " ".join(bits)).strip(), lang)
        chapters.append({
            "id": w["id"],
            "tA": _iso(w["tA"]),
            "tB": _iso(w["tB"]),
            "text": text,
            "events": placed,
            "fromName": w.get("fromName") or "",
            "toName": w.get("toName") or "",
            "fromLat": w.get("fromLat"),
            "fromLon": w.get("fromLon"),
            "toLat": w.get("toLat"),
            "toLon": w.get("toLon"),
        })
    return chapters


def script_chars(chapters: list[dict]) -> int:
    return sum(len(c.get("text") or "") for c in chapters)


def _journal_moments(journal: dict | None) -> list[dict]:
    if not isinstance(journal, dict):
        return []
    rows = journal.get("moments")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def allocate_chapter_budgets(
    days: list[float],
    total: int = FILM_BUDGET_CHARS,
    floor: int = FILM_CHAPTER_FLOOR,
) -> list[int]:
    n = len(days)
    if n <= 0:
        return []
    weights = [max(1.0, float(d or 1)) for d in days]
    if n * floor >= total:
        base, rem = divmod(max(total, n), n)
        return [base + (1 if i < rem else 0) for i in range(n)]
    rest = total - n * floor
    total_w = sum(weights) or 1.0
    extra = [int(rest * w / total_w) for w in weights]
    leftover = rest - sum(extra)
    for i in sorted(range(n), key=lambda j: -weights[j]):
        if leftover <= 0:
            break
        extra[i] += 1
        leftover -= 1
    return [floor + e for e in extra]


def _change_t(row: dict) -> Optional[int]:
    return _ms(row.get("t") or ((row.get("moment") or {}).get("t") if isinstance(row.get("moment"), dict) else None))


def _moment_extra_changes(row: dict) -> list[dict]:
    """Faits du Moment (around) : marina, station, AMP, cyclone nommé, culture."""
    moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
    extras: list[dict] = []
    seen: set[tuple] = set()
    for i, item in enumerate(moment.get("around") or []):
        if not isinstance(item, dict):
            continue
        kind = AROUND_TO_KIND.get(str(item.get("kind") or ""))
        if not kind:
            continue
        title = short_name(item.get("title") or "")
        fact = str(item.get("fact") or title or "").strip()
        if kind == "cyclone":
            name, year = cyclone_name_year({"title": title, "fact": fact})
            if not name:
                continue
            title = name
            fact = f"{name} ({year})" if year else name
        title = extract_named(title, fact, kind) or title
        if not title and not fact:
            continue
        extra = {
            "kind": kind,
            "title": title or fact,
            "fact": fact,
            "score": item.get("score") if item.get("score") in {1, 2, 3} else 2,
            "id": str(item.get("id") or f"around:{row.get('seq')}:{kind}:{i}"),
            "nm": item.get("nm") if isinstance(item.get("nm"), (int, float)) else None,
        }
        if not change_is_speakable(extra):
            continue
        key = (kind, norm_stop(title), fact)
        if key in seen:
            continue
        seen.add(key)
        extras.append(extra)
    return extras


def _dest_culture_changes(dest: dict | None) -> list[dict]:
    """Faits de fiche d'escale (sights) : culture nommée, jamais inventée."""
    if not isinstance(dest, dict):
        return []
    sights = dest.get("sights") or (dest.get("facts") or {}).get("sights") or []
    out: list[dict] = []
    for i, item in enumerate(sights[:2]):
        if isinstance(item, str):
            name, extra = item.strip(), ""
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            extra = str(item.get("fact") or item.get("text") or "").strip()
        else:
            continue
        body = extra or name
        if not body:
            continue
        out.append({
            "kind": "culture",
            "title": name or body,
            "fact": body,
            "id": f"culture:{dest.get('name')}:{i}",
            "score": 1,
        })
    return out


def _flatten_changes(moments: list[dict], t_a: int, t_b: int, first: bool) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for row in moments:
        t = _change_t(row)
        if t is None:
            continue
        if first:
            if t < t_a or t > t_b:
                continue
        elif t <= t_a or t > t_b:
            continue
        raw = list(row.get("changes") or []) + _moment_extra_changes(row)
        for i, change in enumerate(raw):
            if not isinstance(change, dict) or not change.get("kind"):
                continue
            title = short_name(change.get("title") or "")
            fact = str(change.get("fact") or "")
            row_change = {
                **change,
                "id": str(change.get("id") or f"{row.get('seq')}:{change.get('kind')}:{i}"),
                "t": row.get("t"),
                "tMs": t,
                "legIdx": row.get("legIdx"),
            }
            if not change_is_speakable(row_change):
                continue
            key = (str(change.get("kind")), norm_stop(change_place_name(row_change) or title), fact)
            if key in seen:
                continue
            seen.add(key)
            out.append(row_change)
    out.sort(key=lambda c: (c["tMs"], str(c.get("id") or "")))
    return out


def _group_changes(changes: list[dict], span_ms: int) -> list[dict]:
    by_kind: dict[str, list[dict]] = {}
    for change in changes:
        by_kind.setdefault(str(change.get("kind") or ""), []).append(change)
    out: list[dict] = []
    grouped_ids: set[str] = set()
    for kind, group in by_kind.items():
        if len(group) < 3:
            continue
        first, last = group[0], group[-1]
        if kind == "zee-enter":
            title = fact = f"{len(group)} ZEE traversées"
        elif kind == "alert-on":
            title = fact = (
                f"{len(group)} alertes entre le {day_month(first.get('t'))} et le {day_month(last.get('t'))}"
            )
        else:
            title = fact = f"{len(group)} {kind}"
        out.append({
            "id": f"group:{kind}:{first.get('id')}",
            "kind": kind,
            "score": max(int(g.get("score") or 0) for g in group),
            "title": title,
            "fact": fact,
            "t": first.get("t"),
            "tMs": first.get("tMs"),
        })
        grouped_ids.update(str(g.get("id")) for g in group)
    gap = span_ms * KIND_GROUP_FRAC if span_ms > 0 else 0
    last_t: dict[str, int] = {}
    for change in changes:
        cid = str(change.get("id") or "")
        if cid in grouped_ids:
            continue
        kind = str(change.get("kind") or "")
        prev = last_t.get(kind)
        if prev is not None and gap > 0 and abs((change.get("tMs") or 0) - prev) < gap:
            continue
        last_t[kind] = int(change.get("tMs") or 0)
        out.append(change)
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return out


def _place_dedup_key(change: dict) -> str:
    kind = str(change.get("kind") or "")
    name = norm_stop(change_place_name(change))
    if not name:
        return ""
    if kind in {"escale", "approche"}:
        return f"{kind}:{name}"
    return name


def _usable_changes(changes: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    out: list[dict] = []
    for change in sorted(changes, key=lambda c: (c.get("tMs") or 0, str(c.get("id") or ""))):
        if not change_is_speakable(change) or not change_on_route(change):
            continue
        cid = str(change.get("id") or "")
        if cid and cid in seen_ids:
            continue
        key = _place_dedup_key(change)
        if key and key in seen_names:
            continue
        if cid:
            seen_ids.add(cid)
        if key:
            seen_names.add(key)
        out.append(change)
    return out


def select_chapter_changes(
    changes: list[dict], t_a: int, t_b: int, *, budget: bool = True,
) -> list[dict]:
    usable = _usable_changes(changes)
    if not budget:
        usable.sort(key=lambda c: (
            CHANGE_PRIORITY.get(str(c.get("kind") or ""), 9),
            c.get("tMs") or 0,
        ))
        return usable[:FILM_CHAPTER_MAX_FREE]
    grouped = _group_changes(usable, (t_b or 0) - (t_a or 0))
    must = [c for c in grouped if c.get("kind") in {"escale", "approche"}]
    rest = [c for c in grouped if c.get("kind") not in {"escale", "approche"}]
    rest.sort(key=lambda c: (
        -int(c.get("score") or 0), CHANGE_PRIORITY.get(str(c.get("kind") or ""), 9), c.get("tMs") or 0,
    ))
    arrival = next((c for c in must if c.get("kind") == "escale"), None)
    approach = next((c for c in must if c.get("kind") == "approche"), None)
    alert = next((c for c in rest if c.get("kind") == "alert-on"), None)
    color = next((c for c in rest if c.get("kind") in COLOR_KINDS), None)
    picked: list[dict] = []

    def add(item: dict | None) -> None:
        if item is None or len(picked) >= FILM_CHAPTER_MAX_CHANGES:
            return
        if any(x.get("id") == item.get("id") for x in picked):
            return
        key = _place_dedup_key(item)
        if key and any(_place_dedup_key(x) == key for x in picked):
            return
        picked.append(item)

    add(arrival)
    add(approach)
    add(alert)
    add(color)
    for item in must + rest:
        add(item)
    picked.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return picked[:FILM_CHAPTER_MAX_CHANGES]


def change_sentence(change: dict, lang: str = "fr") -> str:
    en = _en(lang)
    when = day_month(change.get("t"), lang)
    title = short_name(change.get("title") or "")
    fact = expand_spoken_units(str(change.get("fact") or "").rstrip("."), lang)
    kind = change.get("kind")
    name = title.replace("Arrivée à ", "").replace("Arrival at ", "").strip()
    if kind == "escale":
        if when:
            return f"Arrival at {name} on {when}." if en else f"Arrivée à {name} le {when}."
        return f"Arrival at {name}." if en else f"Arrivée à {name}."
    if kind == "approche":
        if when:
            return f"On {when}, approaching {title}." if en else f"Le {when}, approche de {title}."
        return f"Approaching {title}." if en else f"Approche de {title}."
    if kind == "alert-on":
        body = fact or title
        return f"On {when}, {body}." if en else f"Le {when}, {body}."
    if kind == "zee-enter" and re.search(r"ports? d'entr|formalit", f"{title} {fact}", re.I):
        name = extract_named(title, fact, "port")
        if not name:
            return ""
        return f"On {when}, off {name}." if en else f"Le {when}, devant {name}."
    if kind == "zee-enter":
        raw = title or fact
        if re.search(r"haute mer|high seas", raw, re.I):
            return f"On {when}, entered the high seas." if en else f"Le {when}, entrée en haute mer."
        waters = zee_waters_label(raw, lang)
        if not waters:
            return ""
        return f"On {when}, entered {waters}." if en else f"Le {when}, entrée dans {waters}."
    if kind == "station":
        name = change_place_name(change)
        if not name:
            return ""
        return f"On {when}, station {name}." if en else f"Le {when}, station {name}."
    if kind == "amp":
        name = change_place_name(change)
        if not name:
            return ""
        return f"On {when}, marine protected area: {name}." if en else f"Le {when}, aire marine protégée : {name}."
    if kind == "marina":
        name = change_place_name(change)
        if not name:
            return ""
        return f"On {when}, within reach of {name}." if en else f"Le {when}, à portée de {name}."
    if kind == "cyclone":
        cyc_name, year = cyclone_name_year(change)
        if not cyc_name:
            return ""
        if year:
            return (
                f"Historical track of cyclone {cyc_name} ({year})."
                if en else
                f"Trace historique du cyclone {cyc_name} ({year})."
            )
        return (
            f"Historical track of cyclone {cyc_name}."
            if en else
            f"Trace historique du cyclone {cyc_name}."
        )
    if kind == "culture":
        body = fact or title
        if not body:
            return ""
        return body if body.endswith(".") else f"{body}."
    if kind == "port":
        name = change_place_name(change)
        if not name:
            return ""
        return f"On {when}, off {name}." if en else f"Le {when}, devant {name}."
    if fact:
        return f"{fact}."
    return ""


def _bubble_from_change(change: dict, chapter: dict, lang: str, char_idx: int) -> dict:
    kind = BUBBLE_KIND.get(str(change.get("kind") or ""), change.get("kind") or "stop")
    title = short_name(change.get("title") or "")
    if change.get("kind") in {"approche", "escale"}:
        title = short_name(
            title.replace("Arrivée à ", "").replace("Arrival at ", "")
            or chapter.get("toName") or ""
        )
    fact = change_sentence(change, lang)
    score = change.get("score") if change.get("score") in {1, 2, 3} else bubble_score({"kind": kind})
    return {
        "id": change.get("id"),
        "charIdx": int(char_idx or 0),
        "kind": kind,
        "title": str(title)[:40],
        "fact": fact,
        "score": score if score in {1, 2, 3} else 3,
        "card": {
            "id": change.get("id"), "kind": kind, "title": title, "text": fact,
            "at": change.get("t"), "score": score if score in {1, 2, 3} else 3,
        },
    }


def _sentences(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text or "") if p.strip()]


_KEEP_SENT = re.compile(
    r"arriv|départ|departure|left |quitté|approche|approaching|avion|flies|flight|aujourd|today",
    re.I,
)


def fit_chapter_text(text: str, budget: int, extras: list[str], lang: str) -> str:
    """Assemble le chapitre. Jamais de phrase de remplissage. Budget = plafond, pas un plancher."""
    blob = re.sub(r"\s{2,}", " ", (text or "").strip())
    for bit in extras:
        if bit and bit not in blob:
            blob = f"{blob} {bit}".strip()
    cap = int(budget or 0)
    if cap > 0:
        hi = max(int(cap * 1.1), cap)
        while len(blob) > hi:
            sents = _sentences(blob)
            drop_i = next(
                (i for i in range(len(sents) - 1, 1, -1) if not _KEEP_SENT.search(sents[i])),
                None,
            )
            if drop_i is None:
                break
            sents.pop(drop_i)
            blob = " ".join(sents).strip()
    return speak_film_text(split_short_sentences(blob), lang)


def _trim_free_script(chapters: list[dict], max_words: int = FILM_FREE_MAX_WORDS) -> list[dict]:
    guard = 0
    while script_words(chapters) > max_words and guard < 200:
        guard += 1
        dropped = False
        for ch in reversed(chapters):
            sents = _sentences(ch.get("text") or "")
            drop_i = next(
                (i for i in range(len(sents) - 1, -1, -1) if not _KEEP_SENT.search(sents[i])),
                None,
            )
            if drop_i is None or len(sents) <= 1:
                continue
            sents.pop(drop_i)
            ch["text"] = " ".join(sents).strip()
            dropped = True
            break
        if not dropped:
            break
    return chapters


def _air_bits_from_moments(
    moments: list[dict],
    w: dict,
    *,
    i: int,
    lang: str,
    display_t0: str | None,
    already: str,
) -> list[str]:
    """Jambes avion portées par les moments, si la fenêtre ne les dit pas déjà."""
    bits: list[str] = []
    seen: set[tuple[str, str]] = set()
    window_key = (
        norm_stop((w.get("from") or {}).get("name") or w.get("fromName") or ""),
        norm_stop(_window_dest_name(w)),
    )
    for row in moments:
        t = _change_t(row)
        if t is None:
            continue
        if i == 0:
            if t < w["tA"] or t > w["tB"]:
                continue
        elif t <= w["tA"] or t > w["tB"]:
            continue
        moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        leg = moment.get("leg") if isinstance(moment.get("leg"), dict) else {}
        frm = str(leg.get("from") or "")
        to = str(leg.get("to") or "")
        if not _is_air_leg(frm, to) and leg.get("vehicle") != "plane":
            continue
        key = (norm_stop(frm), norm_stop(to))
        if not key[0] or not key[1] or key in seen or key == window_key:
            continue
        seen.add(key)
        fake = {
            "from": {"name": frm, "iso": row.get("t"), "holdHours": 0},
            "destName": to,
            "vehicle": "plane",
        }
        sentence = _air_sentence(fake, i=max(i, 1), lang=lang, display_t0=display_t0)
        if sentence and sentence not in already and sentence not in bits:
            bits.append(sentence)
    return bits


def build_raw_from_moments(
    clock: dict | None,
    marks: list | None,
    live: dict | None,
    journal: dict | None,
    *,
    lang: str = "fr",
    seconds: int = 150,
    now_ms: Optional[int] = None,
    display_t0: str | None = None,
    review: dict | None = None,
) -> dict[str, Any]:
    moments = _journal_moments(journal)
    now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    packed = film_candidates(journal, marks, clock, live, now)
    t0, t_end = packed["t0"], packed["tEnd"]
    if t0 is None or t_end is None or t_end <= t0:
        return {"chapters": [], "source": "rules", "chars": 0, "targetSeconds": _film_seconds(seconds), "_fromMoments": True}
    start_name = short_name((packed["start"] or {}).get("name") or "Saint-Maur")
    sea_name = short_name((packed["sea"] or {}).get("name") or "La Rochelle")
    windows = _windows(packed["stops"], t0, t_end)
    has_budget = _film_seconds(seconds) > 0
    budget_s = _film_seconds(seconds)
    if has_budget:
        target = FILM_BUDGET_CHARS if budget_s == 150 else max(
            FILM_CHAPTER_FLOOR, int(FILM_BUDGET_CHARS * budget_s / 150),
        )
        days = [max(1.0, (w["tB"] - w["tA"]) / 86_400_000.0) for w in windows]
        budgets = allocate_chapter_budgets(days, target)
    else:
        target = 0
        budgets = [0] * len(windows)
    en = _en(lang)
    cited: set[str] = set()
    chapters: list[dict] = []
    selected_all: list[dict] = []
    for i, w in enumerate(windows):
        dest = _chapter_dest(w)
        dest_name = _window_dest_name(w)
        arrived = bool(w.get("arrived")) if "arrived" in w else bool(dest)
        depart_ms = _window_depart_ms(w) or 0
        flat = _flatten_changes(moments, w["tA"], w["tB"], first=i == 0)
        for extra in _dest_culture_changes(dest):
            extra = {**extra, "t": (dest or {}).get("iso"), "tMs": w["tB"]}
            flat.append(extra)
        selected = select_chapter_changes(flat, w["tA"], w["tB"], budget=has_budget)
        bits: list[str] = []
        placed: list[dict] = []

        def speak_change(change: dict) -> None:
            if change.get("kind") == "escale":
                return
            sentence = change_sentence(change, lang).strip()
            if not sentence:
                return
            filtered, _dropped = filter_numbers(sentence, _facts_with_rounded(change))
            sentence = (filtered or "").strip()
            if not sentence:
                return
            char_idx = len(" ".join(bits)) + (1 if bits else 0)
            bits.append(sentence)
            placed.append(_bubble_from_change(change, w, lang, char_idx))
            selected_all.append(change)

        if i == 0:
            bits.append(event_sentence({
                "role": "depart", "kind": "stop", "t": OFFICIAL_T0, "name": start_name,
                "seaName": "" if dest_name else sea_name,
                "entry": {"t": OFFICIAL_T0, "name": start_name},
            }, lang, display_t0=display_t0))
        quay = [c for c in selected if (c.get("tMs") or 0) < depart_ms]
        sea = [c for c in selected if (c.get("tMs") or 0) >= depart_ms]
        for change in quay:
            speak_change(change)
        head = _depart_towards(w, i=i, lang=lang, display_t0=display_t0)
        if head:
            bits.append(head)
        for extra_air in _air_bits_from_moments(
            moments, w, i=i, lang=lang, display_t0=display_t0, already=" ".join(bits),
        ):
            bits.append(extra_air)
        for change in sea:
            speak_change(change)
        key = norm_stop((dest or {}).get("name") or "")
        arrival = _arrival_sentence(dest, lang, display_t0) if arrived else ""
        if arrival and key and key not in cited:
            char_idx = len(" ".join(bits)) + (1 if bits else 0)
            bits.append(arrival)
            cited.add(key)
            arr_id = f"stop:{dest['name']}:{dest.get('iso')}"
            dest_title = short_name(dest["name"])
            placed.append({
                "id": arr_id, "charIdx": char_idx, "kind": "stop", "title": dest_title,
                "fact": arrival, "score": 3,
                "card": {"id": arr_id, "kind": "stop", "title": dest_title, "text": arrival, "at": dest.get("iso"), "score": 3},
            })
        _append_review_sentences(bits, review, w, lang)
        extras: list[str] = []
        if dest and w.get("from"):
            try:
                a = float((w["from"] or {}).get("nm") if (w["from"] or {}).get("nm") is not None else (w["from"] or {}).get("filmNm") or 0)
                b = float(dest.get("nm") if dest.get("nm") is not None else dest.get("filmNm") or 0)
                gap = b - a
                if gap > 1:
                    land = (w.get("vehicle") == "land") or _is_land_leg(
                        (w.get("from") or {}).get("name") or "", dest.get("name") or "",
                    )
                    label = _km_label(gap, lang) if land else _nm_label(gap, lang)
                    extras.append(
                        f"The leg covers {label}."
                        if en else
                        f"La jambe compte {label}."
                    )
            except (TypeError, ValueError):
                pass
        chapter_budget = budgets[i] if i < len(budgets) else (FILM_CHAPTER_FLOOR if has_budget else 0)
        text = fit_chapter_text(" ".join(bits), chapter_budget, extras, lang)
        if i == len(windows) - 1:
            close = _close_sentence(w, live, lang)
            if close and close not in text:
                text = speak_film_text(f"{text} {close}".strip(), lang)
        chapters.append({
            "id": w["id"],
            "tA": _iso(w["tA"]),
            "tB": _iso(w["tB"]),
            "text": text,
            "events": placed,
            "fromName": w.get("fromName") or "",
            "toName": w.get("toName") or "",
            "fromLat": w.get("fromLat"),
            "fromLon": w.get("fromLon"),
            "toLat": w.get("toLat"),
            "toLon": w.get("toLon"),
        })
    if not has_budget:
        _trim_free_script(chapters)
    if has_budget and target > 0:
        n = script_chars(chapters)
        hi = int(target * 1.1)
        guard = 0
        while n > hi and chapters and guard < 120:
            sents = _sentences(chapters[-1]["text"])
            if len(sents) <= 2 or _KEEP_SENT.search(sents[-1] or ""):
                break
            chapters[-1]["text"] = " ".join(sents[:-1]).strip()
            n = script_chars(chapters)
            guard += 1
    return {
        "chapters": chapters,
        "source": "rules",
        "chars": script_chars(chapters),
        "targetSeconds": budget_s,
        "_events": selected_all,
        "_packed": packed,
        "_fromMoments": True,
    }


def build_raw_script(
    clock: dict | None,
    marks: list | None,
    live: dict | None,
    journal: dict | None,
    *,
    lang: str = "fr",
    seconds: int = 150,
    now_ms: Optional[int] = None,
    selected: list[dict] | None = None,
    display_t0: str | None = None,
    review: dict | None = None,
) -> dict[str, Any]:
    now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    if _journal_moments(journal):
        return build_raw_from_moments(
            clock, marks, live, journal, lang=lang, seconds=seconds, now_ms=now,
            display_t0=display_t0, review=review,
        )
    packed = film_candidates(journal, marks, clock, live, now)
    t0, t_end = packed["t0"], packed["tEnd"]
    if t0 is None or t_end is None or t_end <= t0:
        return {"chapters": [], "source": "rules", "chars": 0, "targetSeconds": _film_seconds(seconds)}
    start_name = short_name((packed["start"] or {}).get("name") or "Saint-Maur")
    sea_name = short_name((packed["sea"] or {}).get("name") or "La Rochelle")
    events = selected if selected is not None else select_film_events(packed["candidates"], t0, t_end)
    events = [{**e, "name": start_name} if e.get("role") == "depart" else e for e in events]
    must_ids = {e["id"] for e in events if e.get("role") in {"depart", "today", "stop"}}
    windows = _windows(packed["stops"], t0, t_end)

    def compose(evs: list[dict]) -> list[dict]:
        return _compose(windows, _assign(evs, windows), lang=lang, sea_name=sea_name, start_name=start_name, live=live, display_t0=display_t0, review=review)

    chapters = compose(events)
    attach_chapter_events(chapters, packed, journal, lang)
    if _film_seconds(seconds) <= 0:
        _trim_free_script(chapters)
    while _film_seconds(seconds) > 0 and script_chars(chapters) > FILM_MAX_CHARS:
        droppable = [e for e in events if e["id"] not in must_ids]
        if not droppable:
            break
        droppable.sort(key=lambda e: (e.get("score") or 0, -e["tMs"]))
        drop = droppable[0]
        events = [e for e in events if e["id"] != drop["id"]]
        chapters = compose(events)
        attach_chapter_events(chapters, packed, journal, lang)
    return {
        "chapters": chapters,
        "source": "rules",
        "chars": script_chars(chapters),
        "targetSeconds": _film_seconds(seconds),
        "_events": events,
        "_packed": packed,
    }


def journal_fingerprint(journal: dict | None, last_stop: str | None = None) -> str:
    bits = []
    for row in _journal_moments(journal):
        bits.append(f"{row.get('seq')}|{row.get('signature')}|{row.get('t')}")
    for e in sorted(journal_entries(journal), key=lambda x: (str(x.get("t") or ""), str(x.get("id") or ""))):
        bits.append(f"{e.get('id')}|{e.get('kind')}|{e.get('t')}")
    bits.append(f"stop:{last_stop or ''}")
    return hashlib.sha256("\n".join(bits).encode("utf-8")).hexdigest()


def last_stop_id(journal: dict | None, marks: list | None) -> str:
    for row in reversed(_journal_moments(journal)):
        for change in row.get("changes") or []:
            if isinstance(change, dict) and change.get("kind") == "escale":
                return str(change.get("title") or "")
    stops = [e for e in journal_entries(journal) if e.get("kind") == "stop" and e.get("event") == "arrival"]
    if stops:
        stops.sort(key=lambda e: e.get("t") or "")
        return str(stops[-1].get("id") or stops[-1].get("name") or "")
    dated = dated_marks(marks)
    return dated[-1]["name"] if dated else ""


def film_facts(raw: dict, events: list[dict]) -> dict[str, Any]:
    blob = {
        "raw": " ".join(c.get("text") or "" for c in raw.get("chapters") or []),
        "ids": [e["id"] for e in events],
        "entries": [e.get("entry") or {} for e in events],
    }
    return blob


def strip_tags(text: str) -> str:
    return TAG_STRIP.sub("", text or "")


def locate_events(tagged: str, events: list[dict]) -> tuple[str, list[dict]]:
    """Strip [[ev:]] / [[ch:]] and attach charIdx on the displayed text."""
    display_parts: list[str] = []
    located: list[dict] = []
    pos = 0
    by_id = {e["id"]: e for e in events}
    for m in re.finditer(r"\[\[(?:ev|ch):([^\]]+)\]\]\s*", tagged or ""):
        display_parts.append(tagged[pos:m.start()])
        if tagged[m.start():].startswith("[[ev:"):
            eid = m.group(1)
            ev = by_id.get(eid)
            if ev:
                entry = ev.get("entry") or {}
                score = ev.get("bubbleScore") if ev.get("bubbleScore") in {1, 2, 3} else bubble_score(entry, role=ev.get("role"))
                located.append({
                    "id": eid,
                    "charIdx": len("".join(display_parts)),
                    "kind": ev.get("kind") or entry.get("kind"),
                    "title": short_name(ev.get("name") or entry.get("name") or ""),
                    "fact": event_sentence(ev, "fr"),
                    "score": score,
                    "card": _card(entry),
                })
        pos = m.end()
    display_parts.append((tagged or "")[pos:])
    display = "".join(display_parts)
    return display, located


def written_is_valid(text: str, facts: Any, event_ids: list[str]) -> tuple[bool, str, int]:
    """No new number, every [[ev:id]] present, budget ±10 % after strip."""
    filtered, dropped = filter_numbers(text, facts)
    if dropped:
        return False, filtered, dropped
    for eid in event_ids:
        if f"[[ev:{eid}]]" not in (text or ""):
            return False, filtered, dropped
    n = len(strip_tags(text))
    if n < FILM_WRITE_MIN or n > FILM_WRITE_MAX:
        return False, filtered, dropped
    return True, filtered, 0


def _parse_selection(text: str, allowed: set[str]) -> Optional[list[str]]:
    raw = (text or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list):
        return None
    kept = [str(i) for i in ids if str(i) in allowed]
    if FILM_MIN_EVENTS <= len(kept) <= FILM_MAX_EVENTS:
        return kept
    return None


def _snap_to_sentence(text: str, pos: int) -> int:
    if pos <= 0:
        return 0
    if pos >= len(text):
        return len(text)
    prev = max(text.rfind(".", 0, pos), text.rfind("!", 0, pos), text.rfind("?", 0, pos))
    nxt_hits = [i for i in (text.find(".", pos), text.find("!", pos), text.find("?", pos)) if i >= 0]
    nxt = min(nxt_hits) if nxt_hits else -1
    if prev >= 0 and (nxt < 0 or pos - prev <= nxt - pos + 8):
        return min(len(text), prev + 1)
    if nxt >= 0:
        return min(len(text), nxt + 1)
    return pos


def _distribute_written(raw_chapters: list[dict], display: str, located: list[dict]) -> list[dict]:
    total = sum(max(1, len(c.get("text") or "")) for c in raw_chapters) or 1
    pos = 0
    out: list[dict] = []
    for i, ch in enumerate(raw_chapters):
        if i == len(raw_chapters) - 1:
            end = len(display)
        else:
            raw_n = max(1, round(len(display) * max(1, len(ch.get("text") or "")) / total))
            end = _snap_to_sentence(display, pos + raw_n)
            if end <= pos:
                end = min(len(display), pos + max(raw_n, 1))
        chunk = display[pos:end]
        evs = []
        for e in located:
            if pos <= e["charIdx"] < max(end, pos + 1) or (i == len(raw_chapters) - 1 and e["charIdx"] >= pos):
                evs.append({**e, "charIdx": max(0, e["charIdx"] - pos)})
        out.append({**ch, "text": chunk, "events": evs})
        pos = end
    return out


SELECT_SYSTEM = (
    "You select 6 to 9 event ids for a 150-second expedition film. "
    "Return JSON only: {\"ids\":[...],\"reason\":\"one line\"}. "
    "Choose only among the given ids. Always keep depart, stopovers and today when present. "
    "Do not invent numbers. Do not write narrative."
)
WRITE_SYSTEM = (
    "You rewrite ONE film chapter from structured facts. "
    "Keep EVERY number, name and date exactly as given. "
    "Write short complete sentences. Never cut a sentence. "
    "Write units in full words (milles nautiques / nautical miles), never nm. "
    "Start every event sentence with [[ev:<id>]] using the provided ids. "
    "Stay chronological. Thinking OFF. No new figure."
)


async def select_with_llm(
    candidates: list[dict],
    fallback_ids: list[str],
    *,
    cascade: Callable = cascade_text,
) -> tuple[list[str], str]:
    slim = [
        {"id": c["id"], "kind": c["kind"], "t": c.get("t"), "name": c.get("name"), "score": c.get("score"), "role": c.get("role")}
        for c in candidates
    ]
    user = json.dumps({"candidates": slim[:150], "need": "6-9 ids"}, ensure_ascii=False)
    if len(user) > 8000:
        user = user[:8000]
    text, source = await cascade(SELECT_SYSTEM, user, tier="fast", fallback="", facts=user, max_tokens=256)
    parsed = _parse_selection(text, {c["id"] for c in candidates})
    if parsed:
        return parsed, source
    return fallback_ids, "rules"


def _chapter_next_summary(raw_chapters: list[dict], i: int, lang: str) -> str:
    if i + 1 >= len(raw_chapters):
        return "end of the voyage" if _en(lang) else "fin du voyage"
    nxt = raw_chapters[i + 1]
    frm = short_name(nxt.get("fromName") or "")
    to = short_name(nxt.get("toName") or "")
    if to:
        return f"the next leg leads to {to}" if _en(lang) else f"la jambe suivante mène à {to}"
    return f"under way from {frm}" if _en(lang) else f"en route depuis {frm}"


def _pad_tagged(text: str, budget: int) -> str:
    """Plus de remplissage : on coupe si trop long, on ne meuble jamais (lot RD7)."""
    body = text or ""
    cap = int(budget or 0)
    if cap <= 0:
        return body
    hi = max(int(cap * 1.1), cap)
    display = strip_tags(body)
    if len(display) > hi:
        body = body[: max(0, len(body) - (len(display) - hi))]
    return body


async def write_with_llm(
    raw: dict,
    events: list[dict],
    *,
    lang: str = "fr",
    cascade: Callable = cascade_text,
) -> tuple[Optional[dict], str]:
    event_ids = [e["id"] for e in events if e.get("id")]
    facts = film_facts(raw, events)
    raw_chapters = list(raw.get("chapters") or [])
    if not raw_chapters:
        return None, "rules"
    budgets = allocate_chapter_budgets(
        [max(1.0, len(c.get("text") or "") or 1) for c in raw_chapters],
        int(raw.get("targetSeconds") or 150) and FILM_BUDGET_CHARS,
    )
    chapters_out: list[dict] = []
    source_last = "rules"
    any_dropped = 0
    tagged_all: list[str] = []
    by_id = {e["id"]: e for e in events if e.get("id")}
    for i, ch in enumerate(raw_chapters):
        ch_ids = [str(e.get("id")) for e in (ch.get("events") or []) if e.get("id")]
        if not ch_ids:
            ch_ids = [eid for eid in event_ids if eid in (ch.get("text") or "")]
        next_sum = _chapter_next_summary(raw_chapters, i, lang)
        budget = budgets[i] if i < len(budgets) else FILM_CHAPTER_FLOOR
        user = (
            f"lang={('en' if _en(lang) else 'fr')}\n"
            f"next={next_sum}\n"
            f"budget={budget}\n"
            f"ids={json.dumps(ch_ids)}\n"
            f"facts={json.dumps(facts, ensure_ascii=False, default=str)[:2500]}\n"
            f"raw:\n{ch.get('text') or ''}"
        )
        text, source = await cascade(
            WRITE_SYSTEM, user, tier="write", fallback="", facts=None, max_tokens=min(WRITE_MAX_TOKENS, 400),
        )
        source_last = source
        text = speak_film_text(text or "", lang)
        filtered, dropped = filter_numbers(text, facts)
        any_dropped += dropped
        if dropped or not filtered.strip():
            filtered = ch.get("text") or ""
        for eid in ch_ids:
            if f"[[ev:{eid}]]" not in filtered:
                filtered = f"[[ev:{eid}]] {filtered}"
        filtered = split_short_sentences(filtered)
        hi = max(int(budget * 1.1), budget)
        if len(strip_tags(filtered)) > hi:
            kept: list[str] = []
            for sent in _sentences(filtered):
                trial = " ".join(kept + [sent])
                if kept and len(strip_tags(trial)) > hi:
                    break
                kept.append(sent)
            filtered = " ".join(kept) or filtered
            for eid in ch_ids:
                if f"[[ev:{eid}]]" not in filtered:
                    filtered = f"[[ev:{eid}]] {filtered}"
        filtered = _pad_tagged(filtered, budget)
        tagged_all.append(filtered)
        ch_events = [by_id[eid] for eid in ch_ids if eid in by_id] or [
            e for e in (ch.get("events") or []) if e.get("id")
        ]
        display, located = locate_events(filtered, ch_events or events)
        display = speak_film_text(split_short_sentences(display), lang)
        chapters_out.append({**ch, "text": display, "events": located or ch.get("events") or []})
    if any_dropped:
        return None, "rules"
    joined = " ".join(tagged_all)
    ok, _, dropped = written_is_valid(joined, facts, event_ids)
    if event_ids and not ok and dropped:
        return None, "rules"
    n = script_chars(chapters_out)
    if n < FILM_WRITE_MIN or n > FILM_WRITE_MAX:
        return None, "rules"
    return {
        "chapters": chapters_out,
        "source": "nemotron" if str(source_last).startswith("nemotron") else source_last,
        "chars": n,
        "targetSeconds": _film_seconds(raw.get("targetSeconds")),
    }, source_last


def _public_plan(plan: dict, source: str) -> dict:
    chapters = []
    for c in plan.get("chapters") or []:
        chapters.append({
            "id": c.get("id"),
            "tA": c.get("tA"),
            "tB": c.get("tB"),
            "text": c.get("text") or "",
            "events": [
                {
                    "id": e.get("id"),
                    "charIdx": e.get("charIdx"),
                    "kind": e.get("kind") or (e.get("card") or {}).get("kind"),
                    "title": e.get("title") or (e.get("card") or {}).get("title"),
                    "fact": e.get("fact") or (e.get("card") or {}).get("text"),
                    "score": e.get("score") if e.get("score") in {1, 2, 3} else bubble_score(e.get("card") or e),
                    "card": e.get("card"),
                }
                for e in (c.get("events") or [])
            ],
            "fromName": c.get("fromName"),
            "toName": c.get("toName"),
            "fromLat": c.get("fromLat"),
            "fromLon": c.get("fromLon"),
            "toLat": c.get("toLat"),
            "toLon": c.get("toLon"),
        })
    chars = script_chars(chapters)
    return {
        "chapters": chapters,
        "source": source,
        "chars": chars,
        "targetSeconds": int(plan["targetSeconds"]) if plan.get("targetSeconds") is not None else 150,
    }


async def build_film_response(
    clock: dict | None,
    live: dict | None,
    journal: dict | None,
    *,
    marks: list | None = None,
    lang: str = "fr",
    seconds: int = 150,
    style: str = "raw",
    now_ms: Optional[int] = None,
    cascade: Callable = cascade_text,
    want_write: bool = False,
    display_t0: str | None = None,
    review: dict | None = None,
) -> dict[str, Any]:
    """Assemble the API payload. `want_write` triggers Nemotron (tier write)."""
    from story_cache import film_cache_key, get_film_cached, put_film_cached  # noqa: PLC0415

    shown = resolve_film_t0(display_t0)
    marks = marks if marks is not None else (clock or {}).get("marks")
    clock = {**(clock or {}), "t0": OFFICIAL_T0}
    last = last_stop_id(journal, marks)
    fp = journal_fingerprint(journal, last)
    rev = review_fingerprint(review)
    if rev:
        fp = f"{fp}|rev={rev}"
    if shown != OFFICIAL_T0:
        fp = f"{fp}|t0={shown}"
    key = film_cache_key(fp, lang, seconds)
    cached = get_film_cached(key) or {}
    raw_full = build_raw_script(
        clock, marks, live, journal, lang=lang, seconds=seconds, now_ms=now_ms,
        display_t0=shown, review=review,
    )
    events = raw_full.get("_events") or []
    packed = raw_full.get("_packed") or {}
    from_moments = bool(raw_full.get("_fromMoments"))
    raw = _public_plan(raw_full, "rules")
    if not from_moments:
        attach_chapter_events(raw.get("chapters") or [], packed, journal, lang)
    written = cached.get("written") if isinstance(cached.get("written"), dict) else None
    written_source = cached.get("writtenSource") or "nemotron"

    if want_write and written is None:
        if not from_moments:
            fallback_ids = [e["id"] for e in events]
            try:
                ids, _sel_src = await select_with_llm(packed.get("candidates") or events, fallback_ids, cascade=cascade)
                by_id = {e["id"]: e for e in (packed.get("candidates") or events)}
                picked = [by_id[i] for i in ids if i in by_id]
                if picked:
                    raw_full = build_raw_script(
                        clock, marks, live, journal, lang=lang, seconds=seconds, now_ms=now_ms, selected=picked,
                        review=review,
                    )
                    events = raw_full.get("_events") or picked
                    raw = _public_plan(raw_full, "rules")
            except Exception:
                pass
        try:
            wplan, wsrc = await write_with_llm(raw_full, events, lang=lang, cascade=cascade)
        except Exception:
            wplan, wsrc = None, "rules"
        if wplan:
            written = _public_plan(wplan, "nemotron" if str(wsrc).startswith("nemotron") else wsrc)
            written_source = written["source"]
            put_film_cached(key, {"raw": raw, "written": written, "writtenSource": written_source, "lastStop": last})
        else:
            put_film_cached(key, {"raw": raw, "written": None, "writtenSource": None, "lastStop": last})
    elif not cached:
        put_film_cached(key, {"raw": raw, "written": written, "writtenSource": written_source if written else None, "lastStop": last})

    if isinstance(written, dict) and not from_moments:
        attach_chapter_events(written.get("chapters") or [], packed, journal, lang)
    use_written = style in {"written", "nemotron", "rédigé", "redige"} and written is not None
    plan = written if use_written else raw
    source = (written_source if use_written else "rules") or "rules"
    out = {**plan, "source": source, "hasWritten": written is not None, "style": "written" if use_written else "raw"}
    return out


async def official_film(
    *,
    lang: str = "fr",
    seconds: int = 150,
    style: str = "raw",
    cascade: Callable = cascade_text,
    t0: str | None = None,
) -> dict[str, Any]:
    from voyage_api import _climo_clock, _journal_safely, _now  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID, sample_clock_at_time  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    import voyage_journal as journal  # noqa: PLC0415

    voy = load_voyage(OFFICIAL_VOYAGE_ID)
    if voy is None:
        raise FileNotFoundError("voyage officiel absent")
    when = _now()
    raw_clock = voy.get("clock") or _climo_clock(voy)
    clock = {**raw_clock, "t0": OFFICIAL_T0}
    marks = merge_route_marks(voy.get("marks") or [], raw_clock)
    _journal_safely(lambda: journal.tick(voy, when))
    live = sample_clock_at_time(raw_clock, when) or {}
    payload = journal.summary(500)
    try:
        from moment_journal import read_moments  # noqa: PLC0415
        moments = read_moments(OFFICIAL_VOYAGE_ID)
    except Exception:
        moments = []
    if moments:
        payload = {**payload, "moments": moments}
    review = None
    try:
        from plan_review import review_official  # noqa: PLC0415
        # Saison atlas hors HTTP (budget 6 s) : les couloirs viennent des points.
        review = review_official(voy, when, season=False)
    except Exception:
        review = None
    return await build_film_response(
        clock, live, payload, marks=marks, lang=lang, seconds=_film_seconds(seconds),
        style=style, cascade=cascade, want_write=False,
        now_ms=int(when.timestamp() * 1000) if hasattr(when, "timestamp") else None,
        display_t0=resolve_film_t0(t0),
        review=review,
    )


async def warm_film_story(
    voyage_id: str | None = None,
    *,
    langs: tuple[str, ...] = ("fr", "en"),
    seconds: int = 150,
    cascade: Callable = cascade_text,
) -> dict[str, Any]:
    """Préchauffe le rédigé chapitre par chapitre — jamais au clic (lot R9c)."""
    from voyage_api import _climo_clock, _now  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID, sample_clock_at_time  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
    from moment_journal import read_moments  # noqa: PLC0415
    import voyage_journal as journal  # noqa: PLC0415

    vid = voyage_id or OFFICIAL_VOYAGE_ID
    voy = load_voyage(vid)
    if voy is None:
        return {"voyageId": vid, "status": "no-voyage", "count": 0}
    when = _now()
    raw_clock = voy.get("clock") or _climo_clock(voy)
    clock = {**raw_clock, "t0": OFFICIAL_T0}
    marks = merge_route_marks(voy.get("marks") or [], raw_clock)
    live = sample_clock_at_time(raw_clock, when) or {}
    try:
        payload = journal.summary(500)
    except Exception:
        payload = {}
    try:
        moments = read_moments(vid)
    except Exception:
        moments = []
    if moments:
        payload = {**payload, "moments": moments}
    review = None
    try:
        from plan_review import review_official  # noqa: PLC0415
        review = review_official(voy, when, season=False)
    except Exception:
        review = None
    now_ms = int(when.timestamp() * 1000) if hasattr(when, "timestamp") else None
    out: dict[str, Any] = {}
    for lang in langs:
        plan = await build_film_response(
            clock, live, payload, marks=marks, lang=lang, seconds=_film_seconds(seconds),
            style="written", cascade=cascade, want_write=True, now_ms=now_ms,
            review=review,
        )
        out[lang] = {"hasWritten": plan.get("hasWritten"), "chars": plan.get("chars"), "source": plan.get("source")}
    return {"voyageId": vid, "status": "ready", "langs": out}

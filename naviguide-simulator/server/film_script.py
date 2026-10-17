"""Script du film 2:30 — brut (règles), sélection, version rédigée (lots F3 / R9c / ED1).

Le LLM ne produit jamais un nombre : `filter_numbers` + balises `[[ev:id]]`.
Rédigé **au clic** Rédigé (lot ED1) : Super écrit le français ; Ultra édite
puis juge si le plafond juge est ouvert ; Lightning traduit. GET et
`warm_film_story` ne lancent aucun modèle. Repli : le brut.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from climo_events import climo_sentence, dose_climo_changes, notable_climo_changes
from story_cascade import cascade_text, expand_spoken_units, filter_numbers, split_short_sentences
import toponyms
from voyage_clock import OFFICIAL_T0

FILM_MAX_CHARS = 2400
FILM_BUDGET_CHARS = 2400
# ED1 : plus de fenêtre fixe 2160–2640. Conservés pour les pads de tests 2:30.
# `written_is_valid` utilise `film_write_window(seconds)`.
FILM_WRITE_MIN = 2160
FILM_WRITE_MAX = 2640
FILM_CHAPTER_FLOOR = 120
FILM_CHAPTER_MAX_CHANGES = 4   # arrivée + un fait de mer + la marina de l'escale + approche (27 sept. ; était 3)
# Ancre au nom du lieu − 12 caractères (lot RG14). Le client ne rajoute plus
# ce décalage : sinon le bateau est ~2 s devant la voix.
FILM_VOICE_LOOKAHEAD_CHARS = 12
KIND_GROUP_FRAC = 0.10
FILM_MIN_EVENTS = 6
FILM_MAX_EVENTS = 9
FILM_GAP_FRAC = 0.03
KIND_RANK = {"wx": 0, "climo": 1, "sci": 2, "amp": 3, "project": 3, "zee": 4, "coast": 4, "poe": 5, "note": 6, "stop": 7}
SCORED = frozenset({"wx", "climo", "sci", "amp", "project", "zee", "coast", "poe", "note"})
CANDIDATE_KINDS = frozenset({"stop", "zee", "coast", "amp", "project", "poe", "wx", "climo", "sci", "note"})
BUBBLE_KINDS = frozenset({"stop", "zee", "coast", "wx", "amp", "project", "sci", "climo"})
ROUTE_NAMING_KINDS = frozenset({"zee-enter", "coast", "port"})
SHORT_CROSSING_MS = 3 * 86_400_000
AMP_NEAR_NM = 30.0
PROJECT_NEAR_NM = 30.0
STATION_NEAR_NM = 30.0  # RC26 : les flotteurs Argo du large (15-30 nm) se disent aussi
LONG_AMP_PROJECT = 3
CLUSTER_MS = 86_400_000
SKIPPER_GALE_KT = 34.0
HS_BUBBLE_M = 3.0
# RG6 : plus de rotation « Puis / À la jambe suivante ». Formes liées au contenu
# (première étape, traversée longue, saut d'île, dernière étape) — chapter_shape.
CONNECTORS = {
    "fr": ["Le lendemain", "Puis", "D'île en île", "La longue traversée", "Pour la dernière étape"],
    "en": ["The next day", "Then", "From island to island", "The long crossing", "For the last stage"],
}
FORBIDDEN_FILM_RE = re.compile(
    r"\bjambe\b|zone économique exclusive|exclusive economic zone|"
    r"\bCouloirs\b|\bShipping lanes\b|À surveiller|To watch\.|"
    r"à portée de|within reach of|\bde de\b",
    re.I,
)
_EN_TITLE_RE = re.compile(
    r"\b(the|center|deposit|licence|license|prohibition|exclusive economic|careenage)\b",
    re.I,
)
_EN_STOP_RE = re.compile(
    r"\b(the|of|and|for|in|to|with|from|into|on|at|by|a|an|global|project|"
    r"blue|economy|caribbean|coral|reef|marine|coastal|laboratory|ship|test|"
    r"innovations|extreme|conditions|coordination|initiative|management|"
    r"strategies|technologies|solutions|bycatch|tropical|ecosystem|fisheries|"
    r"regional|oceanscape|unleashing|cetacean|future|expedition|restoration|"
    r"combatting|fishing|smartphone|technology|educational|recognition|"
    r"underwater|monitoring|gardeners|conservation|children|yacht|club|small|"
    r"harbour|harbor|lesser|antilles|friends|system|intellireefs|speSeas)\b",
    re.I,
)
_FR_MARK_RE = re.compile(
    r"[àâäéèêëïîôùûüçœ]|\b(le|la|les|un|une|des|du|aux|pour|dans|sur|avec)\b",
    re.I,
)
_GENERIC_HARBOR_RE = re.compile(
    r"^(petite marina|marina|harbour|harbor|autorités portuaires|authorities)\b",
    re.I,
)
_DATE_FR_RE = re.compile(
    r"(1er|\d{1,2}) (janvier|février|mars|avril|mai|juin|juillet|août|septembre|"
    r"octobre|novembre|décembre)(?: \d{4})?",
    re.I,
)
_DATE_EN_RE = re.compile(
    r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|"
    r"October|November|December)(?: \d{4})?",
    re.I,
)
_LEAD_DATE_FR_RE = re.compile(
    r"^(?:Le |À partir du )?((?:1er|\d{1,2}) (?:janvier|février|mars|avril|mai|juin|"
    r"juillet|août|septembre|octobre|novembre|décembre)(?: \d{4})?), ",
    re.I,
)
_LEAD_DATE_EN_RE = re.compile(
    r"^(?:On )?((?:\d{1,2}) (?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)(?: \d{4})?), ",
    re.I,
)
# RC26 : climatologie et projets avant les eaux (gabarit FILM_DISCOURS § 4).
# AM1B : AMP devant les eaux, dans les mêmes fenêtres (on ne réécrit pas la sélection).
CHANGE_PRIORITY = {
    "escale": 0, "approche": 1, "alert-on": 2, "climo": 3, "amp": 4, "station": 4,
    "project": 5, "zee-enter": 6, "coast": 6, "marina": 7, "cyclone": 8, "culture": 9,
    "port": 10, "regime": 11, "alert-off": 12,
}
BUBBLE_KIND = {
    "escale": "stop", "approche": "stop", "alert-on": "wx", "alert-off": "wx",
    "zee-enter": "zee", "coast": "coast", "station": "sci", "amp": "amp",
    "project": "project", "regime": "climo", "climo": "climo",
    "marina": "stop", "cyclone": "climo", "culture": "stop", "port": "poe",
    "buoy": "sci", "poe": "poe", "anchorage": "stop",
    "aton": "sci", "cable": "note", "depth": "note", "piracy": "wx", "satellite": "sci",
}
AROUND_TO_KIND = {
    "marina": "marina", "science": "station", "station": "station",
    "mpa": "amp", "amp": "amp", "project": "project", "cyclone": "cyclone",
    "culture": "culture", "port": "port",
    "anchorage": "anchorage", "poe": "poe", "buoy": "buoy",
    "aton": "aton", "balise": "aton", "beacon": "aton", "seamark": "aton",
    "cable": "cable", "depth": "depth", "piracy": "piracy", "satellite": "satellite",
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
    "station", "zee-enter", "coast", "amp", "project", "climo", "regime", "marina", "cyclone", "culture", "port",
})
FILM_CHAPTER_MAX_FREE = 10
# RC26 : budget intégral proportionnel à la durée de la jambe — 1 item par
# 1,5 jour de mer, plancher 4 (une jambe d'un jour garde 3-4 items), plafond 16.
FILM_FREE_ITEM_DAYS = 1.5
FILM_FREE_ITEMS_MAX = 16
# RC26 : le cap annoncé au départ est le relèvement des 30 premiers milles de la trace.
FILM_INITIAL_HEADING_NM = 30.0
FILM_FREE_MAX_WORDS = 800
FILM_ESTIMATE_CPS = 15  # débit constant (27 sept.) : durée = caractères ÷ 15 ; pas de recalibrage
FILM_TIER_SHORT = 2     # 2:30 — ouverture, eaux, une AMP et un projet, escales
FILM_TIER_MEDIUM = 3    # 3:00 — + côtes et climatologie
FILM_TIER_FULL = 4      # intégral — tout, sans plafond
# DC2 : bouée, formalité de port d'entrée, mouillage. Sac VS1 ; intégral
# seulement, une fois par famille sur une longue jambe. Pas le 2:30.
DC2_KINDS = frozenset({"buoy", "poe", "anchorage"})
# DC3 : balise, câble, profondeur, piraterie, satellite. Même verrou : sac
# et intégral (une fois par famille / longue jambe). Pas le 2:30.
# Satellite : légende déjà dans le stock, sinon silence — on n'invente pas
# « image satellite au-dessus du bateau ».
DC3_KINDS = frozenset({"aton", "cable", "depth", "piracy", "satellite"})
DC_DOSAGE_KINDS = DC2_KINDS | DC3_KINDS
DC3_KIND_ALIASES = {
    "balise": "aton", "beacon": "aton", "seamark": "aton",
    "cable-alert": "cable", "câble": "cable",
    "profondeur": "depth", "bathy": "depth", "gebco": "depth",
    "piraterie": "piracy",
    "satellite-scene": "satellite",
}
GENERIC_ANCHORAGE_NAMES = frozenset({"anchorage", "anchor_berth", "mooring", "mouillage"})
GENERIC_ATON_NAMES = frozenset({
    "aton", "balise", "beacon", "lighthouse", "light", "feu", "phare",
    "seamark", "balisage", "aid to navigation", "aids to navigation",
    "light_major", "light_minor", "light_vessel",
    "buoy_lateral", "buoy_cardinal", "buoy_special_purpose",
    "buoy_safe_water", "buoy_isolated_danger", "buoy_installation",
    "beacon_lateral", "beacon_cardinal", "beacon_special_purpose",
    "beacon_isolated_danger", "beacon_safe_water",
    "landmark", "daymark", "fog_signal", "radar_reflector", "mooring",
})
GENERIC_CABLE_NAMES = frozenset({
    "cable", "câble", "submarine cable", "câble sous-marin",
    "active", "inactive", "planned", "operational", "unknown", "status",
    "in service", "out of service", "en service",
})
GENERIC_CABLE_LABEL_RE = re.compile(
    r"cables?\s+de\s+tel[eé]fono|telephone\s+cables?|power\s+cables?|"
    r"cables?\s+sous-marins?|submarine\s+cables?",
    re.I,
)
GENERIC_SATELLITE_TITLES = frozenset({
    "image satellite", "satellite image", "satellite", "sentinel",
    "sentinel-2", "sentinel-2-l2a", "observation", "cdse", "scene",
})
ATON_TYPE_KEY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$")
SATELLITE_PRODUCT_RE = re.compile(
    r"^(?:s2[ab]_|sentinel|l2a|l1c|cdse|msil)",
    re.I,
)
ROUTE_NEAR_NM = 15.0
NM_TO_KM = 1.852
ALWAYS_KINDS = frozenset({
    "escale", "approche", "zee-enter", "coast", "alert-on", "cyclone", "culture", "climo",
})
GENERIC_TITLES = frozenset({
    "station croisée", "station", "stations", "croisée", "croisee",
    "marina croisée", "marina", "marinas",
    "aire marine protégée", "amp", "mpa",
    "projet", "project", "projets",
    "formalités d'entrée", "ports d'entrée", "port d'entrée",
    "autour du bateau", "zee",
    "mouillage", "anchorage", "bouée", "buoy",
    "balise", "aton", "beacon", "câble", "cable",
    "profondeur", "depth", "piraterie", "piracy",
    "image satellite", "satellite image", "satellite",
})
NO_DATA_RE = re.compile(
    # Les deux apostrophes : droite « ' » et typographique « ’ » — le journal écrit « d’entrée », « n’est connu »
    # (27 sept. : avec la seule apostrophe droite, le filtre RE7 ne filtrait rien).
    r"aucun port d['’]entr[ée]e|no official port of entry|n['’]est connu",
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
    r"^(?:ports? d['’]entr[ée]e|formalit[ée]s d['’]entr[ée]e|entr[ée]e dans)\s*:?\s*",
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
        "pacific": "Pacifique",
    },
    "en": {
        "gibraltar": "Strait of Gibraltar",
        "strait of gibraltar": "Strait of Gibraltar",
        "bay of biscay": "Bay of Biscay",
        "pacific": "Pacific",
    },
}
# RC32 : adjectifs / exonymes ZEE — table unique `toponyms` (JO / Marine Regions).

# Titres de source tels qu'ils apparaissent sur la route officielle (Marine Regions / stock).
# Un test échoue si l'un d'eux n'a pas de nom parlé.
OFFICIAL_ROUTE_ZEE_SOURCES = (
    "French Exclusive Economic Zone",
    "Spanish Exclusive Economic Zone",
    "Portuguese Exclusive Economic Zone",
    "Moroccan Exclusive Economic Zone",
    "Italian Exclusive Economic Zone",
    "Canary Islands Exclusive Economic Zone",
    "Madeira Exclusive Economic Zone",
    "Cape Verdean Exclusive Economic Zone",
    "Zone économique exclusive (Barbadian)",
    "Barbadian Exclusive Economic Zone",
    "Saint Vincentian Exclusive Economic Zone",
    "Saint Lucian Exclusive Economic Zone",
    "Dominican Exclusive Economic Zone",
    "Montserrat Exclusive Economic Zone",
    "Antiguan and Barbudan Exclusive Economic Zone",
    "Kittitian and Nevisian Exclusive Economic Zone",
    "Sint-Eustatius Exclusive Economic Zone",
    "Sint-Maarten Exclusive Economic Zone",
    "Saint-Martin Exclusive Economic Zone",
    "Surinamese Exclusive Economic Zone",
    "Guyanese Exclusive Economic Zone",
    "Venezuelan Exclusive Economic Zone",
    "Trinidadian and Tobagonian Exclusive Economic Zone",
    "Bonaire Exclusive Economic Zone",
    "Canadian Exclusive Economic Zone",
    "Cook Islands Exclusive Economic Zone",
    "American Samoa Exclusive Economic Zone",
    "Samoan Exclusive Economic Zone",
    "Tongan Exclusive Economic Zone",
    "Fijian Exclusive Economic Zone",
    "Wallis and Futuna Exclusive Economic Zone",
    "Matthew and Hunter Exclusive Economic Zone",
    "New Caledonia Exclusive Economic Zone",
    "Haute mer",
    "High Seas",
    "Overlapping claim Western Sahara: Western Sahara / Morocco",
    "Zone économique exclusive espagnole",
    "Zone économique exclusive portugaise",
    "Zone économique exclusive marocaine",
    "Zone économique exclusive italienne",
    "Zone économique exclusive française (France métropolitaine)",
    "Zone économique exclusive espagnole (Canary Islands)",
    "Zone économique exclusive portugaise (Madeira)",
    "Zone économique exclusive (Cape Verdean)",
    "Zone économique exclusive (Barbadian)",
    "Zone économique exclusive (Madagascan)",
)

# RC26 / RC32 : dans la phrase de groupe, le site entre parenthèses gagne
# sur la nationalité — « britannique (Montserrat) » se dit « de Montserrat ».

_HEADING_8 = (
    ("nord", "north"),
    ("nord-est", "northeast"),
    ("est", "east"),
    ("sud-est", "southeast"),
    ("sud", "south"),
    ("sud-ouest", "southwest"),
    ("ouest", "west"),
    ("nord-ouest", "northwest"),
)

# Ports du stock → géographie parlée (comme _ZEE_NATION : overlay, le nom du port vient du stock).
_COAST_GEO = (
    (re.compile(r"camari[nñ]as|mux[ií]a|finisterre|la coru[nñ]a|corme", re.I), ("la Galice", "Galicia", "coast")),
    (re.compile(r"cascais|lisboa|lisbon|peniche|sines", re.I), ("le Portugal", "Portugal", "coast")),
    (re.compile(r"tanger|tangier|algeciras|ceuta|europa point|^gibraltar$", re.I), ("le détroit de Gibraltar", "the Strait of Gibraltar", "strait")),
    (re.compile(r"porto torres|cagliari|olbia|alghero", re.I), ("la Sardaigne", "Sardinia", "island")),
    (re.compile(r"^calvi$|bastia|bonifacio|porto-vecchio", re.I), ("la Corse", "Corsica", "island")),
    (re.compile(r"almer[ií]a|motril|m[aá]laga|cartagena", re.I), ("l'Andalousie", "Andalusia", "coast")),
    (re.compile(r"mah[oó]n|palma|ibiza|ciutadella", re.I), ("les Baléares", "the Balearic Islands", "island")),
)

# Forme parlée du port : le titre du stock doit matcher, on ne parle que ce qu'il contient.
_COAST_PORT_SHORT = (
    (re.compile(r"camari[nñ]as", re.I), "Camariñas"),
    (re.compile(r"mux[ií]a", re.I), "Muxía"),
    (re.compile(r"cascais", re.I), "Cascais"),
    (re.compile(r"tanger|tangier", re.I), "Tanger"),
    (re.compile(r"algeciras", re.I), "Algeciras"),
    (re.compile(r"\bceuta\b", re.I), "Ceuta"),
    (re.compile(r"europa point", re.I), "Europa Point"),
    (re.compile(r"almer[ií]a", re.I), "Almería"),
    (re.compile(r"mah[oó]n", re.I), "Mahón"),
    (re.compile(r"porto torres", re.I), "Porto Torres"),
    (re.compile(r"\bcalvi\b", re.I), "Calvi"),
    (re.compile(r"bastia", re.I), "Bastia"),
    (re.compile(r"porto[- ]?vecchio", re.I), "Porto-Vecchio"),
    (re.compile(r"bonifacio", re.I), "Bonifacio"),
    (re.compile(r"finisterre", re.I), "Finisterre"),
    (re.compile(r"sines", re.I), "Sines"),
    (re.compile(r"peniche", re.I), "Peniche"),
)


def connector_at(i: int, lang: str = "fr") -> str:
    """Ancien index de rotation — RG6 ne l'emploie plus pour assembler un chapitre."""
    cons = CONNECTORS["en" if _en(lang) else "fr"]
    return cons[int(i) % len(cons)]


def looks_english_title(name: str) -> bool:
    """Titre anglais interdit à la voix (The Careenage, titres de projets EN)."""
    s = str(name or "").strip()
    if not s:
        return False
    if re.match(r"^The\s+[A-Z]", s):
        return True
    if _EN_TITLE_RE.search(s):
        return True
    if re.search(r"\b(marina|yacht club|harbour|harbor|intellireefs)\b", s, re.I) and not _FR_MARK_RE.search(s):
        return True
    hits = len(_EN_STOP_RE.findall(s))
    if hits >= 2 and not _FR_MARK_RE.search(s):
        return True
    if hits >= 4:
        return True
    return False


def film_has_forbidden(text: str) -> bool:
    return bool(FORBIDDEN_FILM_RE.search(text or ""))


def scrub_spoken(text: str) -> str:
    """Filet : « de de » impossible ; le reste des interdits ne se génère pas."""
    return re.sub(r"\bde de\b", "de", text or "", flags=re.I)


MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}
EV_TAG = re.compile(r"\[\[ev:([^\]]+)\]\]")
TAG_STRIP = re.compile(r"\[\[(?:ev|ch):[^\]]+\]\]\s*")
WRITE_MAX_TOKENS = 1200
WRITTEN_SOURCE = "nemotron-super-token-factory"
REVIEWED_SOURCE = "nemotron-super-reviewed-ultra"


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
    """Exonyme de la langue du récit (RC32) — table `toponyms`, jamais une traduction."""
    raw_in = str(name or "")
    raw = clean_spoken_label(name, lang) or raw_in
    return toponyms.waters_label(raw_in, lang) or toponyms.waters_label(raw, lang)


def zee_group_waters(members: list, lang: str = "fr") -> str:
    """« les eaux françaises, puis celles de Montserrat » (RC26) — Saint-Martin
    et Sint Maarten restent deux eaux distinctes (RC32)."""
    return toponyms.group_waters(members, lang)


def _as_latlon(lat: Any, lon: Any) -> Optional[tuple[float, float]]:
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if la != la or lo != lo:
        return None
    return la, lo


def _row_latlon(row: dict | None) -> Optional[tuple[float, float]]:
    """Position du moment (pos / here / at) — jamais une coordonnée inventée."""
    if not isinstance(row, dict):
        return None
    sources: list[dict] = [row]
    pos = row.get("pos") if isinstance(row.get("pos"), dict) else None
    if pos:
        sources.append(pos)
    moment = row.get("moment") if isinstance(row.get("moment"), dict) else None
    if moment:
        sources.append(moment)
        here = moment.get("here") if isinstance(moment.get("here"), dict) else None
        if here:
            sources.append(here)
            at = here.get("at") if isinstance(here.get("at"), dict) else None
            if at:
                sources.append(at)
        mom_pos = moment.get("pos") if isinstance(moment.get("pos"), dict) else None
        if mom_pos:
            sources.append(mom_pos)
    for src in sources:
        pair = _as_latlon(src.get("lat"), src.get("lon"))
        if pair:
            return pair
    return None


def _zee_basin_from_lonlat(lat: float, lon: float) -> str:
    """Bassin de la ZEE : Gascogne/Pertuis ≠ Corse/Sardaigne ≠ Pacifique (RC35)."""
    if lon <= -80.0:
        return "pacific"
    if lon >= 5.0 and 36.0 <= lat <= 45.0:
        return "med"
    if lon < 1.0 and lat >= 43.0:
        return "biscay"
    if lon < -30.0:
        return "west_atlantic"
    return "east_atlantic"


def _zee_basin_from_change(change: dict | None) -> str:
    pair = _as_latlon((change or {}).get("lat"), (change or {}).get("lon"))
    if pair:
        return _zee_basin_from_lonlat(pair[0], pair[1])
    return ""


def _zee_same_basin(a: dict | None, b: dict | None) -> bool:
    ba, bb = _zee_basin_from_change(a), _zee_basin_from_change(b)
    if ba and bb:
        return ba == bb
    return True


_SPINE_WATERS_RE = re.compile(
    r"spanish|espagnol|portuguese|portugai|moroccan|marocain|"
    r"french|fran[cç]ais|gibraltar|gascogne|biscay",
    re.I,
)


def prefer_journal_moments(primary: list | None, stored: list | None) -> list[dict]:
    """RC48 : le journal avec zee-enter FR l'emporte sur une grille horloge."""
    a = [m for m in (primary or []) if isinstance(m, dict)]
    b = [m for m in (stored or []) if isinstance(m, dict)]

    def zee_n(rows: list[dict]) -> int:
        n = 0
        for row in rows:
            for change in row.get("changes") or []:
                if not isinstance(change, dict):
                    continue
                kind = str(change.get("kind") or "")
                title = str(change.get("title") or "")
                if kind == "zee-enter" or "économique exclusive" in title.lower():
                    n += 1
        return n

    if zee_n(b) > zee_n(a):
        return b
    return a or b


def _official_moments_for_film(voyage_id: str) -> list[dict]:
    moments: list[dict] = []
    try:
        from moment_journal import read_moments  # noqa: PLC0415
        moments = list(read_moments(voyage_id) or [])
    except Exception:
        moments = []
    stored: list[dict] = []
    try:
        from official_store import official_journal_moments  # noqa: PLC0415
        stored = list(official_journal_moments() or [])
    except Exception:
        stored = []
    return prefer_journal_moments(moments, stored)


def _is_spine_route_item(change: dict | None) -> bool:
    """Eaux de la route LR→Ajaccio : ne cèdent pas à un Argo ou une AMP de trop
    (RC35). Titres FR du journal (« Zone économique exclusive espagnole »)
    comme titres EN (RC48)."""
    if not isinstance(change, dict):
        return False
    kind = str(change.get("kind") or "")
    blob = " ".join(
        str(x) for x in (
            change.get("title"), change.get("fact"),
            *(change.get("members") or []),
        ) if x
    )
    if kind == "zee-enter" and _SPINE_WATERS_RE.search(blob):
        return True
    geo = change.get("geo") if isinstance(change.get("geo"), dict) else {}
    return kind == "coast" and geo.get("kind") == "strait"


def _pacific_arrival_ms(
    clock: dict | None, t_a: Optional[int], t_b: Optional[int],
) -> Optional[int]:
    """Premier instant où la TRACE de mer est dans le Pacifique (lon ≤ −80) ;
    l'arrivée n'est dite que si le bateau y est encore (Papeete). Pas une boîte AIS."""
    if not isinstance(clock, dict):
        return None
    t0 = _ms(clock.get("t0"))
    first: Optional[int] = None
    last_lon: Optional[float] = None
    last_t: Optional[int] = None
    for v in clock.get("vertices") or []:
        if not isinstance(v, dict) or v.get("vehicle") in {"plane", "land"}:
            continue
        t = _ms(v.get("iso"))
        if t is None and t0 is not None and v.get("tHours") is not None:
            try:
                t = t0 + int(float(v["tHours"]) * 3_600_000)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        if t_a is not None and t < t_a:
            continue
        if t_b is not None and t > t_b:
            continue
        pair = _as_latlon(v.get("lat"), v.get("lon"))
        if pair is None:
            continue
        _lat, lon = pair
        last_lon, last_t = lon, t
        if lon <= -80.0 and first is None:
            first = t
    if first is None or last_lon is None or last_lon > -80.0:
        return None
    if t_b is not None:
        return int(t_b)
    return int(last_t or first)


def _join_then(parts: list[str], lang: str) -> str:
    names = [p for p in parts if p]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    then = "then" if _en(lang) else "puis"
    if len(names) == 2:
        return f"{names[0]} {then} {names[1]}"
    return f"{', '.join(names[:-1])} {then} {names[-1]}"


def heading_phrase(deg: Any, lang: str = "fr") -> str:
    """Huit directions depuis headingDeg. 246° → « cap au sud-ouest »."""
    if not isinstance(deg, (int, float)) or isinstance(deg, bool):
        return ""
    try:
        d = float(deg)
    except (TypeError, ValueError):
        return ""
    if d != d:  # NaN
        return ""
    idx = int((d % 360.0) / 45.0 + 0.5) % 8
    fr, en = _HEADING_8[idx]
    if _en(lang):
        return f"heading {en}"
    if fr in {"est", "ouest"}:
        return f"cap à l'{fr}"
    return f"cap au {fr}"


def _utc_day(change: dict) -> str:
    t = change.get("tMs")
    if t is None:
        t = _ms(change.get("t"))
    if t is None:
        return ""
    return datetime.fromtimestamp(int(t) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")


def _coast_geo(name: str) -> Optional[tuple[str, str, str]]:
    for rx, triple in _COAST_GEO:
        if rx.search(str(name or "")):
            return triple
    return None


def _coast_port_short(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    for rx, spoken in _COAST_PORT_SHORT:
        if rx.search(raw):
            return spoken
    return short_name(raw)


_GALICE_PAIR_RE = re.compile(r"camari[nñ]as|mux[ií]a", re.I)


def _coast_port_is_listed(name: str) -> bool:
    raw = str(name or "").strip()
    if not raw:
        return False
    return any(rx.search(raw) for rx, _spoken in _COAST_PORT_SHORT)


def _prefer_coast_ports(ports: list[str], geo: dict | None) -> list[str]:
    """Au plus deux ports. Groupe Galice : Muxía et Camariñas tiennent ensemble."""
    seen: set[str] = set()
    uniq: list[str] = []
    for p in ports:
        label = str(p).strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        uniq.append(label)
    if len(uniq) <= 2:
        return uniq
    geo_fr = ((geo or {}).get("fr") or "").casefold()
    if "galice" in geo_fr:
        pair = [p for p in uniq if _GALICE_PAIR_RE.search(p)]
        if len(pair) >= 2:
            return pair[:2]
        rest = [p for p in uniq if p not in pair]
        return (pair + rest)[:2]
    listed = [p for p in uniq if _coast_port_is_listed(p)]
    other = [p for p in uniq if p not in listed]
    return (listed + other)[:2]


def _is_coast_source(change: dict) -> bool:
    """Jalon de côte : kind coast, port du stock, ou marina dont le titre porte un lieu connu."""
    kind = str(change.get("kind") or "")
    if kind not in {"coast", "port", "marina"}:
        return False
    name = change_place_name(change) or short_name(change.get("title") or "")
    if re.search(r"\b(oil|terminal|refinery|raffinerie)\b", name, re.I):
        return False
    if kind == "marina":
        return bool(_coast_geo(name))
    return True


def coast_sentence(change: dict, lang: str = "fr") -> str:
    """Jalon de côte : géographie connue + ports du stock, jamais un titre de source."""
    en = _en(lang)
    when = day_month(change.get("t"), lang)
    ports = [str(p).strip() for p in (change.get("ports") or []) if str(p).strip()]
    if not ports:
        one = change_place_name(change) or short_name(change.get("title") or "")
        if one:
            ports = [one]
    if not ports:
        return ""
    geo = change.get("geo") if isinstance(change.get("geo"), dict) else None
    if not geo:
        hit = _coast_geo(ports[0])
        if hit:
            geo = {"fr": hit[0], "en": hit[1], "kind": hit[2]}
    label = (geo.get("en") if en else geo.get("fr")) if geo else ""
    kind = (geo or {}).get("kind") or ""
    if kind == "strait" and label:
        a, b = ports[0], ports[1] if len(ports) > 1 else ""
        prefer = {p.casefold() for p in ports}
        if "tanger" in prefer or "tangier" in prefer:
            a = next((p for p in ports if re.search(r"tanger|tangier", p, re.I)), a)
        if "algeciras" in prefer:
            b = next((p for p in ports if re.search(r"algeciras", p, re.I)), b or a)
        if b and b.casefold() != a.casefold():
            body = f"{label} between {a} and {b}" if en else f"{label} entre {a} et {b}"
        else:
            body = f"{label} — {a}"
    elif label:
        listed = ", ".join(ports) if len(ports) <= 2 else f"{', '.join(ports[:-1])} {_join_then([ports[-1]], lang)}"
        if len(ports) == 1:
            listed = ports[0]
        elif len(ports) == 2:
            listed = f"{ports[0]}, {ports[1]}"
        else:
            listed = f"{', '.join(ports[:-1])} {'then' if en else 'puis'} {ports[-1]}"
        body = f"{label} — {listed}"
        if kind == "coast":
            body = (
                f"the boat skirts {body}"
                if en else
                f"le bateau longe {body}"
            )
        elif kind == "island" and en:
            body = f"{label} — {listed}"
        elif kind == "island":
            body = f"{label} — {listed}"
    else:
        listed = _join_then(ports, lang)
        body = f"the boat skirts {listed}" if en else f"le bateau longe {listed}"
    if when:
        return f"On {when}, {body}." if en else f"Le {when}, {body}."
    return f"{body[0].upper()}{body[1:]}." if body else ""


def _zee_cluster_change(cluster: list[dict]) -> dict:
    first = cluster[0]
    if len(cluster) == 1:
        return first
    names = [str(c.get("title") or c.get("fact") or "") for c in cluster]
    out = {
        "id": f"zee-cluster:{first.get('id')}",
        "kind": "zee-enter",
        "score": max(int(c.get("score") or 0) for c in cluster),
        "title": names[0],
        "fact": " · ".join(n for n in names if n),
        "members": names,
        "t": first.get("t"),
        "tMs": first.get("tMs"),
        "cluster": cluster,
    }
    if first.get("lat") is not None and first.get("lon") is not None:
        out["lat"] = first.get("lat")
        out["lon"] = first.get("lon")
    return out


def _is_zee_waters_change(change: dict) -> bool:
    """Vraie entrée d'eaux — pas un titre « Ports d'entrée / Formalités » collé sur kind zee-enter."""
    if str(change.get("kind") or "") != "zee-enter":
        return False
    blob = f"{change.get('title') or ''} {change.get('fact') or ''}"
    if re.search(r"ports? d['’]entr|formalit", blob, re.I):
        return False
    return True


def dose_zee_changes(changes: list[dict], span_ms: int) -> list[dict]:
    """Toutes les ZEE en traversée courte ; au plus une par jour en longue ; < 24 h → une phrase."""
    zee = [c for c in changes if _is_zee_waters_change(c)]
    zee.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    clusters: list[list[dict]] = []
    def _zee_high_seas(change: dict) -> bool:
        return bool(re.search(
            r"haute mer|high seas",
            f"{change.get('title') or ''} {change.get('fact') or ''}",
            re.I,
        ))

    for c in zee:
        prev = clusters[-1][-1] if clusters else None
        dt = (c.get("tMs") or 0) - (prev.get("tMs") or 0) if prev else CLUSTER_MS
        # RC35 : Gascogne/Pertuis FR ≠ Corse FR (bassins) ; ES/PT/MA restent
        # des phrases distinctes (Gascogne peut s'intercaler) — on ne colle
        # pas deux eaux de la route dans le même groupe.
        both_spine = bool(prev) and _is_spine_route_item(prev) and _is_spine_route_item(c)
        if (
            clusters and dt < CLUSTER_MS
            and not _zee_high_seas(c) and not _zee_high_seas(prev)
            and _zee_same_basin(c, prev)
            and not both_spine
        ):
            clusters[-1].append(c)
        else:
            clusters.append([c])
    grouped = [_zee_cluster_change(cl) for cl in clusters]
    if span_ms < SHORT_CROSSING_MS:
        return grouped
    kept: list[dict] = []
    days_used: set[str] = set()
    for c in grouped:
        if _is_spine_route_item(c):
            kept.append(c)
            continue
        day = _utc_day(c) or f"_{len(days_used)}"
        if day in days_used:
            continue
        days_used.add(day)
        kept.append(c)
    return kept


def dose_coast_changes(changes: list[dict], span_ms: int) -> list[dict]:
    """Au plus un jalon de côte par jour de film ; même géographie le même jour → une phrase."""
    coasts = [c for c in changes if _is_coast_source(c)]
    coasts.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    buckets: dict[str, list[dict]] = {}
    for c in coasts:
        raw = change_place_name(c) or short_name(c.get("title") or "")
        name = _coast_port_short(raw) or raw
        geo = _coast_geo(raw) or _coast_geo(name)
        day = _utc_day(c)
        key = f"{day}:{(geo[0] if geo else name).casefold()}"
        buckets.setdefault(key, []).append({**c, "ports": [name] if name else [], "geo": (
            {"fr": geo[0], "en": geo[1], "kind": geo[2]} if geo else None
        )})
    merged: list[dict] = []
    for group in buckets.values():
        first = group[0]
        ports: list[str] = []
        seen: set[str] = set()
        for g in group:
            for p in g.get("ports") or []:
                k = p.casefold()
                if k in seen:
                    continue
                seen.add(k)
                ports.append(p)
        geo = first.get("geo")
        ports = _prefer_coast_ports(ports, geo if isinstance(geo, dict) else None)
        merged.append({
            **first,
            "id": first.get("id") or f"coast:{ports[0] if ports else first.get('tMs')}",
            "kind": "coast",
            "title": " — ".join(
                [((geo or {}).get("fr") or "")] + ports
            ).strip(" —") or (ports[0] if ports else first.get("title")),
            "ports": ports,
            "geo": geo,
        })
    by_day: dict[str, dict] = {}
    islands: list[dict] = []
    island_at: dict[str, int] = {}
    rank = {"strait": 3, "island": 2, "coast": 1}
    for c in merged:
        # Île (Sardaigne, Corse…) : un jalon par géographie, jamais écrasé
        # le même jour par un port d'eaux italiennes / françaises.
        # RC26 : la même île sur deux jours ne se dit qu'une fois (ports réunis).
        if (c.get("geo") or {}).get("kind") == "island":
            geo_key = str((c.get("geo") or {}).get("fr") or "").casefold()
            if geo_key and geo_key in island_at:
                prev = islands[island_at[geo_key]]
                seen_ports = {p.casefold() for p in prev.get("ports") or []}
                extra = [p for p in c.get("ports") or [] if p.casefold() not in seen_ports]
                if extra:
                    ports = list(prev.get("ports") or []) + extra
                    islands[island_at[geo_key]] = {
                        **prev,
                        "ports": ports,
                        "title": " — ".join([((prev.get("geo") or {}).get("fr") or "")] + ports).strip(" —"),
                    }
                continue
            if geo_key:
                island_at[geo_key] = len(islands)
            islands.append(c)
            continue
        day = _utc_day(c) or f"_{len(by_day)}"
        prev = by_day.get(day)
        if prev is None:
            by_day[day] = c
            continue
        cur_r = rank.get((c.get("geo") or {}).get("kind") or "", 0)
        prev_r = rank.get((prev.get("geo") or {}).get("kind") or "", 0)
        if cur_r > prev_r or (cur_r == prev_r and len(c.get("ports") or []) > len(prev.get("ports") or [])):
            by_day[day] = c
    out = list(islands)
    out.extend(by_day[k] for k in sorted(by_day))
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return out


def _heading_deg_at(
    moments: list[dict] | None,
    depart_ms: Optional[int],
    clock: dict | None = None,
) -> Optional[float]:
    best: Optional[float] = None
    best_dt: Optional[int] = None
    t_ref = depart_ms or 0
    for row in moments or []:
        if not isinstance(row, dict):
            continue
        if _moment_is_air(row):
            continue  # RC30 : le cap d'une jambe de MER — jamais celui du vol (Cayenne → « cap au nord »)
        t = _ms(row.get("t"))
        if t is None:
            continue
        if depart_ms is not None and t < depart_ms - 3_600_000:
            continue
        mom = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        leg = mom.get("leg") if isinstance(mom.get("leg"), dict) else {}
        deg = leg.get("headingDeg")
        if not isinstance(deg, (int, float)) or isinstance(deg, bool):
            continue
        dt = abs(int(t) - int(t_ref))
        if best_dt is None or dt < best_dt:
            best, best_dt = float(deg), dt
    if best is not None:
        return best
    for v in ((clock or {}).get("vertices") or []):
        if not isinstance(v, dict):
            continue
        if v.get("vehicle") in {"plane", "land"}:
            continue  # RC30 : un sommet d'avion (plein nord vers Halifax) n'est pas un cap de mer
        t = _ms(v.get("iso"))
        if t is None:
            continue
        deg = v.get("headingDeg") if v.get("headingDeg") is not None else v.get("bearing")
        if not isinstance(deg, (int, float)) or isinstance(deg, bool):
            continue
        dt = abs(int(t) - int(t_ref))
        if best_dt is None or dt < best_dt:
            best, best_dt = float(deg), dt
    return best


def _bearing_deg(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> Optional[float]:
    try:
        p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
        dl = math.radians(float(lon2) - float(lon1))
    except (TypeError, ValueError):
        return None
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _initial_route_heading(
    clock: dict | None, depart_ms: Optional[int], nm: float = FILM_INITIAL_HEADING_NM,
) -> Optional[float]:
    """RC26 : le cap annoncé au départ d'une jambe est le relèvement des ~30
    premiers milles de la TRACE après l'appareillage — pas le bearing du premier
    segment (manœuvres de port), ni le relèvement global vers l'arrivée."""
    if depart_ms is None:
        return None
    t0 = _ms((clock or {}).get("t0"))
    verts: list[dict] = []
    for v in (clock or {}).get("vertices") or []:
        if not isinstance(v, dict) or v.get("lat") is None or v.get("lon") is None:
            continue
        if v.get("vehicle") in {"plane", "land"}:
            continue
        t = _ms(v.get("iso"))
        if t is None and v.get("tHours") is not None and t0 is not None:
            try:
                t = t0 + int(float(v["tHours"]) * 3_600_000)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        verts.append({**v, "_t": t})
    if len(verts) < 2:
        return None
    start = next(
        (i for i, v in enumerate(verts) if v["_t"] >= int(depart_ms) and v.get("vehicle") != "quay"),
        None,
    )
    if start is None or start + 1 >= len(verts):
        return None
    acc, j = 0.0, start
    while j + 1 < len(verts) and acc < nm:
        d = _nm_between(verts[j]["lat"], verts[j]["lon"], verts[j + 1]["lat"], verts[j + 1]["lon"])
        if d:
            acc += d
        j += 1
    if acc < nm * 0.5:
        return None
    return _bearing_deg(verts[start]["lat"], verts[start]["lon"], verts[j]["lat"], verts[j]["lon"])


def _leg_heading_deg(
    moments: list[dict] | None,
    depart_ms: Optional[int],
    clock: dict | None = None,
) -> Optional[float]:
    """Cap d'ouverture : la trace d'abord (RC26), sinon l'ancien plus-proche moment."""
    deg = _initial_route_heading(clock, depart_ms)
    if deg is not None:
        return deg
    return _heading_deg_at(moments, depart_ms, clock=clock)


def change_place_name(change: dict) -> str:
    kind = str(change.get("kind") or "")
    title = str(change.get("title") or "")
    fact = str(change.get("fact") or "")
    if kind == "escale":
        title = title.replace("Arrivée à ", "").replace("Arrival at ", "").strip()
    if kind == "zee-enter":
        title = LIST_PREFIX_RE.sub("", title).strip(" :")
    if kind == "coast":
        ports = [str(p).strip() for p in (change.get("ports") or []) if str(p).strip()]
        if ports:
            return toponyms.origin_name(ports[0])
        title = LIST_PREFIX_RE.sub("", title).strip(" :")
    if kind == "climo":
        return str(change.get("title") or change.get("regimeId") or "").strip()
    if kind == "cyclone":
        name, _year = cyclone_name_year(change)
        return name
    if kind == "alert-on" and alert_is_amp(change):
        return toponyms.origin_name(alert_amp_name(change))
    named = clean_spoken_label(extract_named(title, fact, kind))
    if kind == "zee-enter":
        return named
    return toponyms.origin_name(named)


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
    if kind == "project" or _is_amp_change(change):
        limit = PROJECT_NEAR_NM if kind == "project" else AMP_NEAR_NM
        return nm is None or nm <= limit
    if kind in {"station", "buoy", "poe", "anchorage"} | DC3_KINDS:
        return nm is None or nm <= STATION_NEAR_NM
    if nm is not None and nm > ROUTE_NEAR_NM:
        return False
    return True


def _station_item(change: dict) -> dict:
    """Métadonnées du sac (source / type / titre) pour qualifier une station."""
    if not isinstance(change, dict):
        return {}
    entity = change.get("entity") if isinstance(change.get("entity"), dict) else {}
    facts = change.get("facts") if isinstance(change.get("facts"), dict) else {}
    raw_kind = str(change.get("kind") or "")
    sci_kind = raw_kind if raw_kind not in {"station", "sci", "science", "nearby"} else ""
    for cand in (
        change.get("sciKind"), change.get("type"),
        entity.get("sciKind"), facts.get("kind"),
    ):
        s = str(cand or "")
        if s and s not in {"station", "sci", "science", "nearby"}:
            sci_kind = sci_kind or s
            break
    return {
        "name": change.get("name") or change.get("title") or entity.get("name") or facts.get("name") or "",
        "title": change.get("title") or "",
        "fact": change.get("fact") or "",
        "source": change.get("source") or entity.get("source") or facts.get("source") or "",
        "kind": sci_kind,
        "type": change.get("sciType") or facts.get("type") or entity.get("type") or "",
        "wmo": change.get("wmo") or entity.get("wmo") or facts.get("wmo") or "",
        "entity": entity,
        "facts": facts,
    }


def _argo_identifier(item: dict) -> str:
    """Identifiant WMO du flotteur (stock : wmo, nom « Argo 6904216 ») — vide sinon."""
    entity = item.get("entity") if isinstance(item.get("entity"), dict) else {}
    facts = item.get("facts") if isinstance(item.get("facts"), dict) else {}
    blob = " ".join(
        str(v) for v in (
            item.get("wmo"), entity.get("wmo"), facts.get("wmo"),
            item.get("name"), item.get("title"), item.get("fact"),
        ) if v
    )
    found = re.search(r"\b(\d{5,9})\b", blob)
    return found.group(1) if found else ""


def station_spoken_label(change: dict, lang: str = "fr") -> str:
    """Type parlé — jamais le titre de jeu de données (RG5). RC30 : un flotteur
    Argo se dit avec son identifiant (« le flotteur Argo 6904216 ») ; un
    flotteur anonyme ne se dit pas."""
    from ici_engine import science_type_key, spoken_science_type  # noqa: PLC0415
    item = _station_item(change)
    spoken = spoken_science_type(item, lang)
    if not spoken:
        return ""
    if science_type_key(item) == "argo":
        ident = _argo_identifier(item)
        if not ident:
            return ""
        return f"Argo float {ident}" if _en(lang) else f"le flotteur Argo {ident}"
    return spoken


def station_name_speakable(name: str) -> bool:
    """Une station se dit seulement si un type est reconnu (Argo, PELGAS, bouée, CTD, observatoire)."""
    from ici_engine import science_type_key  # noqa: PLC0415
    n = (name or "").strip()
    if not n or _is_generic_title(n, "station"):
        return False
    return bool(science_type_key({"name": n, "title": n}))


def alert_is_amp(change: dict) -> bool:
    """AMP réelle seulement — IUCN / WDPA / parc ; jamais Chaluts / Pétoncles / deposit."""
    from ici_engine import is_protected_amp  # noqa: PLC0415
    return is_protected_amp({
        "name": change.get("title") or change.get("name"),
        "title": change.get("title"),
        "fact": change.get("fact"),
        "iucn_cat": change.get("iucn_cat") or change.get("iucn"),
        "designation": change.get("designation"),
        "site_id": change.get("site_id") or change.get("id"),
    })


def alert_amp_name(change: dict) -> str:
    """« Pertuis charentais - Rochebonne (12,2 nm): IUCN Unassigned; » → « Pertuis charentais - Rochebonne »."""
    from ici_engine import spoken_amp_name  # noqa: PLC0415
    fact = str(change.get("fact") or "")
    head = re.split(r"\s*\(\s*\d", fact, maxsplit=1)[0]
    head = re.split(r":\s*IUCN", head, maxsplit=1, flags=re.I)[0]
    raw = spoken_amp_name(head.strip(" ;:-")) or clean_spoken_label(head.strip(" ;:-"))
    return spoken_amp_name(raw) or raw


def _is_amp_change(change: dict) -> bool:
    kind = str(change.get("kind") or "")
    if kind == "amp":
        from ici_engine import is_fishing_amp  # noqa: PLC0415
        return not is_fishing_amp({
            "name": change.get("title") or change.get("name"),
            "title": change.get("title"),
            "fact": change.get("fact"),
        })
    if kind == "alert-on":
        return alert_is_amp(change)
    return False


def _amp_speak_event(change: dict) -> str:
    """enter | nearby | exit | '' — champ event, sinon inside / nm 0."""
    event = str(change.get("event") or "")
    if event in {"enter", "exit", "nearby"}:
        return event
    nested = change.get("entry") if isinstance(change.get("entry"), dict) else {}
    nested_ev = str(nested.get("event") or "")
    if nested_ev in {"enter", "exit", "nearby"}:
        return nested_ev
    if change.get("inside") is True or nested.get("inside") is True:
        return "enter"
    nm = change_distance_nm(change)
    if nm is not None and nm <= 0:
        return "enter"
    if nm is not None and nm > 0:
        return "nearby"
    return ""


def _amp_activity_codes(item: dict) -> tuple[Any, Any]:
    """Codes ProtectedSeas (0–3). Jamais le dict d'événement imbriqué `entry`."""
    from amp_traffic import as_activity  # noqa: PLC0415
    raw_entry = item.get("entry")
    speed = as_activity(item.get("speed"))
    if isinstance(raw_entry, dict):
        nested_e = as_activity(raw_entry.get("entry"))
        nested_s = as_activity(raw_entry.get("speed"))
        if nested_s is not None:
            speed = nested_s
        return nested_e, speed
    return as_activity(raw_entry), speed


def _amp_stock_traffic(item: dict | None) -> str:
    """interdit / régulé seulement si le stock le porte. Pas inventé."""
    if not isinstance(item, dict):
        return ""
    stored = item.get("traffic")
    if stored in {"forbidden", "regulated"}:
        return stored
    nested = item.get("entry") if isinstance(item.get("entry"), dict) else None
    if isinstance(nested, dict) and nested.get("traffic") in {"forbidden", "regulated"}:
        return nested["traffic"]
    from amp_traffic import traffic_kind  # noqa: PLC0415
    entry, speed = _amp_activity_codes(item)
    if entry is None and speed is None:
        return ""
    kind = traffic_kind(entry, speed)
    return kind if kind in {"forbidden", "regulated"} else ""


def _amp_traffic_paren(item: dict | None, lang: str) -> str:
    kind = _amp_stock_traffic(item)
    if kind == "forbidden":
        return " (no transit)" if _en(lang) else " (circulation interdite)"
    if kind == "regulated":
        return " (regulated transit)" if _en(lang) else " (circulation régulée)"
    return ""


def _amp_relation(change: dict) -> str:
    """crossing | near | '' — champ event / inside / nm du stock."""
    ev = _amp_speak_event(change)
    if ev == "enter":
        return "crossing"
    if ev == "nearby":
        return "near"
    return ""


def _amp_distance_nm(change: dict) -> Optional[float]:
    nm = change_distance_nm(change)
    if nm is not None:
        return nm
    nested = change.get("entry") if isinstance(change.get("entry"), dict) else {}
    return _fact_num(change, "nm") or (_fact_num(nested, "nm") if nested else None)


def _amp_film_sentence(name: str, change: dict, lang: str, when: str) -> str:
    """Phrase d'aire déjà retenue : près ou traversée ; circulation si le stock l'a."""
    en = _en(lang)
    if not name:
        return ""
    if _amp_speak_event(change) == "exit":
        return ""
    tag = _amp_traffic_paren(change, lang)
    rel = _amp_relation(change)
    nm = _amp_distance_nm(change)
    dist = spoken_distance(nm, lang) if nm is not None and nm > 0 else ""
    if rel == "crossing":
        text = (
            f"On {when}, the boat crosses the marine protected area {name}{tag}."
            if en else
            f"Le {when}, le bateau traverse l'aire marine protégée {name}{tag}."
        )
    elif rel == "near" and dist:
        text = (
            f"On {when}, the boat passes near the marine protected area {name}, at {dist}{tag}."
            if en else
            f"Le {when}, le bateau passe près de l'aire marine protégée {name}, à {dist}{tag}."
        )
    elif rel == "near":
        text = (
            f"On {when}, the boat passes near the marine protected area {name}{tag}."
            if en else
            f"Le {when}, le bateau passe près de l'aire marine protégée {name}{tag}."
        )
    elif dist:
        text = (
            f"On {when}, {dist} away, the marine protected area {name}{tag}."
            if en else
            f"Le {when}, à {dist}, l'aire marine protégée {name}{tag}."
        )
    else:
        text = (
            f"On {when}, marine protected area: {name}{tag}."
            if en else
            f"Le {when}, aire marine protégée : {name}{tag}."
        )
    return _tidy_empty_when(text) if not when else text


def _is_buoy_change(change: dict) -> bool:
    """Station dont le type du stock est une bouée — pas un titre de jeu."""
    if not isinstance(change, dict):
        return False
    kind = str(change.get("kind") or "")
    if kind == "buoy":
        return True
    if kind not in {"station", "sci", "science"}:
        return False
    from ici_engine import science_type_key  # noqa: PLC0415
    return science_type_key(_station_item(change)) == "buoy"


def _poe_place_name(change: dict) -> str:
    """Nom d'un port d'entrée officiel du stock. Vide = pas de formalité."""
    if not isinstance(change, dict):
        return ""
    kind = str(change.get("kind") or "")
    title = str(change.get("title") or "")
    fact = str(change.get("fact") or "")
    blob = f"{title} {fact}"
    if NO_DATA_RE.search(blob):
        return ""
    if kind != "poe":
        return ""
    return change_place_name(change) or extract_named(title, fact, "port")


def _is_poe_formality_change(change: dict) -> bool:
    return bool(_poe_place_name(change))


def _anchorage_name(change: dict) -> str:
    """Nom de mouillage du stock. Un type OSM anonyme n'est pas un fait."""
    if not isinstance(change, dict):
        return ""
    raw = (
        change_place_name(change)
        or extract_named(change.get("title"), change.get("fact"), "anchorage")
        or short_name(str(change.get("title") or change.get("name") or ""))
    )
    s = str(raw or "").strip()
    if not s or s.casefold() in GENERIC_ANCHORAGE_NAMES or _is_generic_title(s, "anchorage"):
        return ""
    return s


def _is_anchorage_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if str(change.get("kind") or "") not in {"anchorage", "mouillage"}:
        return False
    return bool(_anchorage_name(change))


def _as_dc2_change(change: dict) -> Optional[dict]:
    """Copie parlable : kind amp | buoy | poe | anchorage. None si pas de fait."""
    if not isinstance(change, dict):
        return None
    if _is_amp_change(change):
        packed = dict(change)
        packed["kind"] = "amp"
        return packed
    if _is_buoy_change(change):
        packed = dict(change)
        packed["kind"] = "buoy"
        packed["id"] = f"dc2:buoy:{change.get('id') or change.get('tMs') or packed.get('title')}"
        return packed
    if _is_poe_formality_change(change):
        name = _poe_place_name(change)
        packed = dict(change)
        packed["kind"] = "poe"
        packed["title"] = name or packed.get("title")
        packed["fact"] = name or packed.get("fact")
        packed["id"] = f"dc2:poe:{change.get('id') or name}"
        return packed
    if _is_anchorage_change(change):
        name = _anchorage_name(change)
        packed = dict(change)
        packed["kind"] = "anchorage"
        packed["title"] = name
        packed["fact"] = packed.get("fact") or name
        packed["id"] = f"dc2:anchorage:{change.get('id') or name}"
        return packed
    return None


def dc_subject_record(change: dict, lang: str = "fr") -> Optional[dict]:
    """Candidat DC : kind, phrase possible, une fois par famille sur une longue jambe."""
    packed = _as_dc_change(change)
    if not packed:
        return None
    phrase = change_sentence(packed, lang).strip()
    if not phrase:
        return None
    kind = str(packed.get("kind") or "")
    name = (
        change_place_name(packed)
        or short_name(packed.get("title") or packed.get("name") or "")
    )
    rec = {
        "kind": kind,
        "phrase": phrase,
        "oncePerFamilyOnLongLeg": True,
        "name": name,
    }
    if kind == "amp":
        rec["relation"] = _amp_relation(change)
    return rec


def dc_subject_candidates(changes: list[dict] | None, lang: str = "fr") -> list[dict]:
    """Sac DC1–DC3 (amp, buoy, poe, anchorage, aton, cable, depth, piracy, satellite).

    Une entrée par famille. VS1 lira cette liste ; le palier 2:30 n'empile pas ces kinds.
    """
    recs: list[dict] = []
    for change in changes or []:
        rec = dc_subject_record(change, lang)
        if rec:
            recs.append(rec)
    rank = {"crossing": 0, "near": 1, "": 2}
    kind_order = {
        "amp": 0, "buoy": 1, "poe": 2, "anchorage": 3,
        "aton": 4, "cable": 5, "depth": 6, "piracy": 7, "satellite": 8,
    }
    recs.sort(key=lambda r: (
        kind_order.get(str(r.get("kind") or ""), 9),
        rank.get(str(r.get("relation") or ""), 9),
    ))
    out: list[dict] = []
    seen: set[str] = set()
    for rec in recs:
        kind = str(rec.get("kind") or "")
        if not kind or kind in seen:
            continue
        seen.add(kind)
        out.append(rec)
    return out


def dose_dc2_leg_changes(changes: list[dict], span_ms: int = 0) -> list[dict]:
    """Intégral, jambe longue : au plus une bouée, une formalité, un mouillage."""
    if span_ms < SHORT_CROSSING_MS:
        return []
    by_kind: dict[str, list[dict]] = {"buoy": [], "poe": [], "anchorage": []}
    for change in changes or []:
        packed = _as_dc2_change(change)
        if not packed:
            continue
        kind = str(packed.get("kind") or "")
        if kind not in by_kind:
            continue
        if not _would_speak(packed):
            continue
        by_kind[kind].append(packed)
    out: list[dict] = []
    for kind in ("buoy", "poe", "anchorage"):
        rows = by_kind[kind]
        if not rows:
            continue
        rows.sort(key=lambda c: (
            change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
            c.get("tMs") or 0,
        ))
        out.append(rows[0])
    return out


def _dc3_kind(change: dict) -> str:
    raw = str((change or {}).get("kind") or "").strip().casefold()
    return DC3_KIND_ALIASES.get(raw, raw)


def _aton_name(change: dict) -> str:
    """Nom de balise du stock. Un type OSM (buoy_lateral) n'est pas un fait."""
    if not isinstance(change, dict):
        return ""
    raw = (
        change.get("name")
        or change_place_name(change)
        or extract_named(change.get("title"), change.get("fact"), "aton")
        or short_name(str(change.get("title") or ""))
    )
    s = str(raw or "").strip()
    if not s:
        return ""
    key = s.casefold()
    if key in GENERIC_ATON_NAMES or _is_generic_title(s, "aton"):
        return ""
    if ATON_TYPE_KEY_RE.match(key):
        return ""
    return s


def _is_aton_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if _dc3_kind(change) != "aton":
        return False
    return bool(_aton_name(change))


def _cable_name(change: dict) -> str:
    """Nom de câble du stock. nearby=true sans nom → silence."""
    if not isinstance(change, dict):
        return ""
    raw = (
        change.get("name")
        or extract_named(change.get("title"), change.get("fact"), "cable")
        or short_name(str(change.get("title") or ""))
    )
    s = str(raw or "").strip()
    if not s or s.casefold() in GENERIC_CABLE_NAMES or _is_generic_title(s, "cable"):
        return ""
    if len(s) < 3 or re.fullmatch(r"\d+", s) or GENERIC_CABLE_LABEL_RE.search(s):
        return ""
    return s


def _is_cable_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if _dc3_kind(change) != "cable":
        return False
    return bool(_cable_name(change))


def _as_depth_m(raw: Any) -> Optional[float]:
    if not isinstance(raw, (int, float)):
        return None
    value = abs(float(raw))
    if value != value or value < 1.0:
        return None
    return value


def _depth_m(change: dict) -> Optional[float]:
    """Sonde du stock (emodnet.depth_m ou gebco depthOffshore). Jamais inventée."""
    if not isinstance(change, dict):
        return None
    facts = change.get("facts") if isinstance(change.get("facts"), dict) else {}
    for raw in (
        change.get("depth_m"), change.get("depthM"), change.get("depthOffshore"),
        facts.get("depth_m"), facts.get("depthM"), facts.get("depthOffshore"),
    ):
        hit = _as_depth_m(raw)
        if hit is not None:
            return hit
    return None


def _is_depth_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if _dc3_kind(change) != "depth":
        return False
    return _depth_m(change) is not None


def _piracy_name(change: dict) -> str:
    if not isinstance(change, dict):
        return ""
    raw = str(change.get("name") or change.get("title") or "").strip()
    if not raw or raw.casefold() in {"piracy", "piraterie", "piraterie —", "piracy —"}:
        return ""
    if _is_generic_title(raw, "piracy"):
        return ""
    return raw


def _piracy_level(change: dict) -> str:
    if not isinstance(change, dict):
        return ""
    token = str(change.get("level") or "").strip().upper()
    if token in {"CRITICAL", "CRIT"}:
        return "HIGH"
    if token in {"MODERATE", "MED"}:
        return "MEDIUM"
    if token in {"HIGH", "MEDIUM", "LOW"}:
        return token
    return token


def _is_piracy_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if _dc3_kind(change) != "piracy":
        return False
    return bool(_piracy_name(change))


def _satellite_field_playable(raw: Any) -> str:
    """Légende déjà écrite. Produit STAC / « Image satellite » → vide."""
    s = str(raw or "").strip()
    if not s or len(s) < 8:
        return ""
    key = s.casefold()
    if key in GENERIC_SATELLITE_TITLES or _is_generic_title(s, "satellite"):
        return ""
    if SATELLITE_PRODUCT_RE.search(s):
        return ""
    if re.fullmatch(r"[A-Za-z0-9._:-]+", s) and ("sentinel" in key or "l2a" in key or "l1c" in key):
        return ""
    return s


def _satellite_caption(change: dict) -> str:
    """Phrase satellite déjà dans le stock. Image seule → silence."""
    if not isinstance(change, dict):
        return ""
    scene = change.get("scene") if isinstance(change.get("scene"), dict) else {}
    sat = change.get("satellites") if isinstance(change.get("satellites"), dict) else {}
    sat_scene = sat.get("scene") if isinstance(sat.get("scene"), dict) else {}
    derived = (
        sat.get("derived") if isinstance(sat.get("derived"), dict)
        else change.get("derived") if isinstance(change.get("derived"), dict)
        else {}
    )
    for raw in (
        change.get("caption"), change.get("description"), change.get("legend"),
        scene.get("caption"), scene.get("description"), scene.get("legend"),
        sat.get("caption"), sat.get("description"), sat.get("legend"),
        sat_scene.get("caption"), sat_scene.get("description"), sat_scene.get("legend"),
        change.get("title"), scene.get("title"), sat_scene.get("title"),
    ):
        hit = _satellite_field_playable(raw)
        if hit:
            return hit
    for key in ("sdb", "coastline", "intertidal"):
        block = derived.get(key) if isinstance(derived.get(key), dict) else {}
        value = block.get("value") if isinstance(block.get("value"), dict) else {}
        hit = _satellite_field_playable(value.get("name"))
        if hit:
            return hit
    return ""


def _is_satellite_change(change: dict) -> bool:
    if not isinstance(change, dict):
        return False
    if _dc3_kind(change) != "satellite":
        return False
    return bool(_satellite_caption(change))


def _as_dc3_change(change: dict) -> Optional[dict]:
    """Copie parlable DC3. None si le champ du stock manque."""
    if not isinstance(change, dict):
        return None
    if _is_aton_change(change):
        name = _aton_name(change)
        packed = dict(change)
        packed["kind"] = "aton"
        packed["title"] = name
        packed["fact"] = packed.get("fact") or name
        packed["id"] = f"dc3:aton:{change.get('id') or name}"
        return packed
    if _is_cable_change(change):
        name = _cable_name(change)
        packed = dict(change)
        packed["kind"] = "cable"
        packed["title"] = name
        packed["fact"] = packed.get("fact") or name
        packed["id"] = f"dc3:cable:{change.get('id') or name}"
        return packed
    if _is_depth_change(change):
        metres = _depth_m(change)
        packed = dict(change)
        packed["kind"] = "depth"
        packed["depth_m"] = metres
        packed["id"] = f"dc3:depth:{change.get('id') or change.get('tMs') or metres}"
        return packed
    if _is_piracy_change(change):
        name = _piracy_name(change)
        packed = dict(change)
        packed["kind"] = "piracy"
        packed["title"] = name
        packed["name"] = name
        packed["level"] = _piracy_level(change) or packed.get("level")
        packed["id"] = f"dc3:piracy:{change.get('id') or name}"
        return packed
    if _is_satellite_change(change):
        caption = _satellite_caption(change)
        packed = dict(change)
        packed["kind"] = "satellite"
        packed["caption"] = caption
        packed["title"] = caption
        packed["fact"] = caption
        packed["id"] = f"dc3:satellite:{change.get('id') or caption[:40]}"
        return packed
    return None


def _as_dc_change(change: dict) -> Optional[dict]:
    packed = _as_dc2_change(change)
    if packed:
        return packed
    return _as_dc3_change(change)


def dose_dc3_leg_changes(changes: list[dict], span_ms: int = 0) -> list[dict]:
    """Intégral, jambe longue : au plus une phrase par famille DC3."""
    if span_ms < SHORT_CROSSING_MS:
        return []
    by_kind: dict[str, list[dict]] = {k: [] for k in ("aton", "cable", "depth", "piracy", "satellite")}
    for change in changes or []:
        packed = _as_dc3_change(change)
        if not packed:
            continue
        kind = str(packed.get("kind") or "")
        if kind not in by_kind:
            continue
        if not _would_speak(packed):
            continue
        by_kind[kind].append(packed)
    out: list[dict] = []
    for kind in ("aton", "cable", "depth", "piracy", "satellite"):
        rows = by_kind[kind]
        if not rows:
            continue
        rows.sort(key=lambda c: (
            change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
            c.get("tMs") or 0,
        ))
        out.append(rows[0])
    return out


def _dc3_from_ici_bag(bag: dict | None, *, seq: Any = 0) -> list[dict]:
    """Candidats DC3 déjà dans un sac ici — copie, jamais inventée."""
    if not isinstance(bag, dict):
        return []
    extras: list[dict] = []
    aton = bag.get("aton") if isinstance(bag.get("aton"), dict) else {}
    for i, mark in enumerate(aton.get("nearby") or []):
        if not isinstance(mark, dict):
            continue
        name = _aton_name({"kind": "aton", "title": mark.get("name"), "name": mark.get("name")})
        if not name:
            continue
        extra = {
            "kind": "aton",
            "title": name,
            "fact": name,
            "name": name,
            "score": 2,
            "id": f"ici:aton:{seq}:{i}",
            "nm": mark.get("nm") if isinstance(mark.get("nm"), (int, float)) else None,
        }
        extras.append(extra)
        break
    emo = bag.get("emodnet") if isinstance(bag.get("emodnet"), dict) else {}
    cables = emo.get("cables") if isinstance(emo.get("cables"), dict) else {}
    cable_name = _cable_name({
        "kind": "cable",
        "title": cables.get("name"),
        "name": cables.get("name"),
        "fact": cables.get("name"),
    })
    if cable_name:
        extras.append({
            "kind": "cable",
            "title": cable_name,
            "fact": cable_name,
            "name": cable_name,
            "score": 2,
            "id": f"ici:cable:{seq}",
        })
    depth = None
    source = ""
    bathy = emo.get("bathy") if isinstance(emo.get("bathy"), dict) else {}
    depth = _as_depth_m(bathy.get("depth_m"))
    if depth is not None:
        source = "emodnet"
    else:
        depth = _as_depth_m(bag.get("depthOffshore"))
        if depth is not None:
            source = "gebco"
    if depth is not None:
        extras.append({
            "kind": "depth",
            "title": source,
            "fact": source,
            "depth_m": depth,
            "source": source,
            "score": 2,
            "id": f"ici:depth:{seq}:{source}",
        })
    pir = bag.get("piracy") if isinstance(bag.get("piracy"), dict) else None
    if isinstance(pir, dict) and pir.get("name"):
        extras.append({
            "kind": "piracy",
            "title": pir.get("name"),
            "fact": pir.get("name"),
            "name": pir.get("name"),
            "level": pir.get("level"),
            "source": pir.get("source"),
            "score": 2,
            "id": f"ici:piracy:{seq}:{pir.get('name')}",
        })
    sat = bag.get("satellites") if isinstance(bag.get("satellites"), dict) else {}
    caption = _satellite_caption({"kind": "satellite", "satellites": sat, "scene": sat.get("scene")})
    if caption:
        extras.append({
            "kind": "satellite",
            "title": caption,
            "fact": caption,
            "caption": caption,
            "score": 2,
            "id": f"ici:satellite:{seq}",
        })
    return extras


def _dc_changes_from_ici_route() -> list[dict]:
    """Recherche le long de la route officielle : sacs ici déjà calculés."""
    try:
        from official_store import payload_of  # noqa: PLC0415
        body = payload_of("ici")
    except Exception:
        return []
    if not isinstance(body, dict):
        return []
    rows: list[dict] = []
    for i, point in enumerate(body.get("points") or []):
        if not isinstance(point, dict):
            continue
        bag = point.get("bag")
        if not isinstance(bag, dict) or "amp" not in bag:
            continue
        for extra in _dc3_from_ici_bag(bag, seq=point.get("sailNm") or point.get("nm") or i):
            pair = _as_latlon(point.get("lat"), point.get("lon"))
            if pair:
                extra["lat"], extra["lon"] = pair
            rows.append(extra)
    return rows


def _dc_amp_changes_from_journal(journal: dict | None) -> list[dict]:
    rows: list[dict] = []
    for moment in _journal_moments(journal):
        for change in moment.get("changes") or []:
            if isinstance(change, dict) and _is_amp_change(change):
                packed = dict(change)
                if not packed.get("t"):
                    packed["t"] = moment.get("t")
                rows.append(packed)
    for entry in journal_entries(journal):
        if str(entry.get("kind") or "") != "amp":
            continue
        rows.append({
            **entry,
            "kind": "amp",
            "title": entry.get("title") or entry.get("name") or "",
            "fact": entry.get("fact") or entry.get("name") or "",
        })
    return rows


def _dc_changes_from_journal(journal: dict | None) -> list[dict]:
    """Faits DC du journal (DC1–DC3) et des sacs ici le long de la route."""
    rows = _dc_amp_changes_from_journal(journal)
    dc3_kinds = DC2_KINDS | DC3_KINDS
    for moment in _journal_moments(journal):
        t = moment.get("t")
        for change in moment.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if (
                _is_buoy_change(change)
                or _is_poe_formality_change(change)
                or _is_anchorage_change(change)
                or _is_aton_change(change)
                or _is_cable_change(change)
                or _is_depth_change(change)
                or _is_piracy_change(change)
                or _is_satellite_change(change)
            ):
                packed = dict(change)
                if not packed.get("t"):
                    packed["t"] = t
                rows.append(packed)
        mom = moment.get("moment") if isinstance(moment.get("moment"), dict) else {}
        for item in mom.get("around") or []:
            if not isinstance(item, dict):
                continue
            mapped = AROUND_TO_KIND.get(str(item.get("kind") or ""))
            kind = mapped or str(item.get("kind") or "")
            if kind not in dc3_kinds:
                continue
            packed = dict(item)
            packed["kind"] = kind
            if not packed.get("t"):
                packed["t"] = t
            rows.append(packed)
        here = mom.get("here") if isinstance(mom.get("here"), dict) else {}
        for i, mark in enumerate(here.get("seamarks") or []):
            if not isinstance(mark, dict) or not mark.get("name"):
                continue
            packed = {
                "kind": "aton",
                "title": mark.get("name"),
                "fact": mark.get("name"),
                "name": mark.get("name"),
                "nm": mark.get("nm") if isinstance(mark.get("nm"), (int, float)) else None,
                "id": f"here:aton:{moment.get('seq')}:{i}",
            }
            if not packed.get("t"):
                packed["t"] = t
            rows.append(packed)
    for entry in journal_entries(journal):
        kind = str(entry.get("kind") or "")
        mapped = DC3_KIND_ALIASES.get(kind.casefold(), kind)
        if mapped not in {"poe", "sci", "station", "anchorage", "buoy"} | DC3_KINDS:
            continue
        rows.append({
            **entry,
            "kind": mapped if mapped in DC3_KINDS else kind,
            "title": entry.get("title") or entry.get("name") or "",
            "fact": entry.get("fact") or entry.get("name") or "",
        })
    rows.extend(_dc_changes_from_ici_route())
    return rows


def _with_dc_subjects(plan: dict, journal: dict | None, lang: str) -> dict:
    plan["dcSubjects"] = dc_subject_candidates(_dc_changes_from_journal(journal), lang)
    return plan


_FR_SMALL = (
    "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
    "dix-sept", "dix-huit", "dix-neuf",
)
_EN_SMALL = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)


def _spoken_int(n: int, lang: str) -> str:
    if _en(lang):
        if 0 <= n <= 19:
            return _EN_SMALL[n]
        if n == 20:
            return "twenty"
        if n == 21:
            return "twenty-one"
        if 22 <= n <= 29:
            return f"twenty-{_EN_SMALL[n - 20]}"
        if n == 30:
            return "thirty"
        return str(n)
    if 0 <= n <= 19:
        return _FR_SMALL[n]
    if n == 20:
        return "vingt"
    if n == 21:
        return "vingt et un"
    if 22 <= n <= 29:
        return f"vingt-{_FR_SMALL[n - 20]}"
    if n == 30:
        return "trente"
    return str(n)


def spoken_distance(nm: Any, lang: str = "fr") -> str:
    """« douze milles » / « twelve miles » — chiffres 1–30 en toutes lettres."""
    try:
        v = int(round(float(nm)))
    except (TypeError, ValueError):
        return ""
    if v < 0:
        return ""
    word = _spoken_int(v, lang)
    if _en(lang):
        unit = "mile" if v == 1 else "miles"
        return f"{word} {unit}"
    unit = "mille" if v == 1 else "milles"
    return f"{word} {unit}"


def dose_amp_changes(changes: list[dict], span_ms: int) -> list[dict]:
    """Au plus une AMP par étape courte, trois par traversée longue ; plus proche d'abord."""
    amps = [c for c in changes if _is_amp_change(c)]
    amps.sort(key=lambda c: (
        change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
        c.get("tMs") or 0,
    ))
    limit = 1 if span_ms < SHORT_CROSSING_MS else LONG_AMP_PROJECT
    return amps[:limit]


def dose_project_changes(changes: list[dict], span_ms: int) -> list[dict]:
    """Au plus un projet par étape courte, trois par traversée ; gold_on puis plus proche."""
    projs = [c for c in changes if str(c.get("kind") or "") == "project"]
    def gold(c: dict) -> int:
        return 0 if c.get("gold_on") in (True, 1, "1", "true", "True") else 1
    projs.sort(key=lambda c: (
        gold(c),
        change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
        c.get("tMs") or 0,
    ))
    limit = 1 if span_ms < SHORT_CROSSING_MS else LONG_AMP_PROJECT
    return projs[:limit]


def dose_station_changes(
    changes: list[dict], span_ms: int = 0,
    t_a: Optional[int] = None, t_b: Optional[int] = None,
) -> list[dict]:
    """Une station qualifiée par étape (RG5), la plus proche de la route ; pas de
    comptage. RC26 : une longue traversée en dit jusqu'à trois, réparties dans le
    temps (une par tranche de la jambe) — le Pacifique ne reste pas muet quinze jours."""
    rows = [
        c for c in changes
        if str(c.get("kind") or "") == "station"
        and station_spoken_label(c, "fr")
        and not (span_ms >= SHORT_CROSSING_MS and _is_buoy_change(c))
    ]
    if not rows:
        return []
    days = max(0.0, float(span_ms or 0) / 86_400_000.0)
    limit = 1 if days < 12 else min(3, math.ceil(days / 10.0))
    if limit <= 1 or len(rows) <= 1:
        rows.sort(key=lambda c: (
            change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
            c.get("tMs") or 0,
        ))
        return rows[:1]
    lo = int(t_a) if t_a is not None else min(int(c.get("tMs") or 0) for c in rows)
    hi = int(t_b) if t_b is not None else max(int(c.get("tMs") or 0) for c in rows)
    width = max(1, (hi - lo) // limit + 1)
    out: list[dict] = []
    by_slot: dict[int, list[dict]] = {}
    for c in rows:
        slot = min(limit - 1, max(0, (int(c.get("tMs") or 0) - lo) // width))
        by_slot.setdefault(slot, []).append(c)
    for slot in sorted(by_slot):
        cands = by_slot[slot]
        cands.sort(key=lambda c: (
            change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
            c.get("tMs") or 0,
        ))
        out.append(cands[0])
        if len(out) >= limit:
            break
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return out


def change_is_speakable(change: dict) -> bool:
    kind = str(change.get("kind") or "")
    if kind in {"regime", "alert-off"}:
        return False
    if is_sea_hs_alert(change):
        return True
    if kind == "alert-on":
        body = str(change.get("fact") or change.get("title") or "").strip()
        if not body or NO_DATA_RE.search(body):
            return False      # « Aucun port d'entrée officiel n'est connu pour … » : l'absence ne se raconte pas
        if alert_is_amp(change):
            return bool(alert_amp_name(change))
        return True
    if kind == "amp":
        from ici_engine import is_fishing_amp, spoken_amp_name  # noqa: PLC0415
        if str(change.get("event") or "") == "exit":
            return False
        if is_fishing_amp({"name": change.get("title"), "fact": change.get("fact")}):
            return False
        name = spoken_amp_name(change_place_name(change) or change.get("title") or "")
        return bool(name) and not _is_generic_title(name, "amp") and len(name) > 2
    if kind == "project":
        return bool(change_place_name(change))
    if kind == "climo":
        return bool(climo_sentence(change, "fr") or climo_sentence(change, "en"))
    if kind == "cyclone":
        return bool(cyclone_name_year(change)[0])
    if kind == "culture":
        return bool(change_place_name(change) or change.get("fact"))
    if kind == "station":
        return bool(station_spoken_label(change, "fr"))
    if kind == "buoy":
        return bool(station_spoken_label({**change, "kind": "station"}, "fr"))
    if kind == "poe":
        return bool(_poe_place_name(change))
    if kind == "anchorage":
        return bool(_anchorage_name(change))
    if kind == "aton":
        return bool(_aton_name(change))
    if kind == "cable":
        return bool(_cable_name(change))
    if kind == "depth":
        return _depth_m(change) is not None
    if kind == "piracy":
        return bool(_piracy_name(change))
    if kind == "satellite":
        return bool(_satellite_caption(change))
    return bool(change_place_name(change))


_EARTH_NM = 3440.065
_PORT_LEAVE_NM = 2.0
_PORT_ANCHOR_NM = 5.0
_AIR_ONLY_KEYS = frozenset({"halifax", "saint-pierre"})
_AIR_KEYS = frozenset({"cayenne", "halifax"})
_SIDE_KEYS = frozenset({"halifax", "saint-pierre"})


def _air_stop_key(name: str) -> str:
    s = str(name or "").casefold()
    if "cayenne" in s:
        return "cayenne"
    if "halifax" in s:
        return "halifax"
    if "miquelon" in s or "saint-pierre" in s or "saint pierre" in s:
        return "saint-pierre"
    return ""


def _is_air_only_stop(name: str) -> bool:
    return _air_stop_key(name) in _AIR_ONLY_KEYS


def _is_air_leg(a: str, b: str) -> bool:
    """Jambe avion : uniquement Cayenne ↔ Halifax (aller et retour)."""
    x, y = _air_stop_key(a), _air_stop_key(b)
    return (x == "cayenne" and y == "halifax") or (x == "halifax" and y == "cayenne")


def _is_side_leg(a: str, b: str) -> bool:
    """Traversée du second bateau : Halifax ↔ Saint-Pierre."""
    x, y = _air_stop_key(a), _air_stop_key(b)
    return {x, y} == _SIDE_KEYS


def _is_land_leg(a: str, b: str) -> bool:
    return (
        is_saint_maur(a) and bool(_ROCHELLE_RE.search(str(b or "")))
    ) or (
        is_saint_maur(b) and bool(_ROCHELLE_RE.search(str(a or "")))
    )


def _nm_between(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> Optional[float]:
    try:
        p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlamb = math.radians(float(lon2) - float(lon1))
    except (TypeError, ValueError):
        return None
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlamb / 2.0) ** 2
    return 2.0 * _EARTH_NM * math.asin(min(1.0, math.sqrt(a)))


def _mode_from_vehicle(veh: Any) -> Optional[str]:
    if veh == "plane":
        return "air"
    if veh == "land":
        return "road"
    if veh in {"main", "boat", "side"}:
        return "sail"
    return None


def _window_mode_name(mode: str) -> str:
    return mode if mode in {"sail", "air", "road"} else "sail"


def _classify_window_mode(
    frm: dict | None,
    to: dict | None,
    clock: dict | None,
    t_a: Optional[int],
    t_b: Optional[int],
) -> str:
    a = (frm or {}).get("name") or ""
    b = (to or {}).get("name") or ""
    if _is_land_leg(a, b):
        return "road"
    if _is_air_leg(a, b):
        return "air"
    plat, plon = (frm or {}).get("lat"), (frm or {}).get("lon")
    for v in ((clock or {}).get("vertices") or []):
        if not isinstance(v, dict):
            continue
        t = _ms(v.get("iso"))
        if t is None:
            continue
        if t_a is not None and t < t_a:
            continue
        if t_b is not None and t > t_b:
            continue
        if v.get("vehicle") == "quay":
            continue
        d = _nm_between(plat, plon, v.get("lat"), v.get("lon"))
        if d is not None and d <= _PORT_LEAVE_NM:
            continue
        found = _mode_from_vehicle(v.get("vehicle"))
        # Sommet route loin du port = autre fenêtre (Saint-Maur → La Rochelle
        # ne doit pas classer La Rochelle → Ajaccio « par la route »).
        if found == "road" and d is not None and d > 80:
            continue
        if found:
            return found
    for src in (frm, to):
        found = _mode_from_vehicle((src or {}).get("vehicle"))
        if found and found != "sail":
            return found
    return "sail"


def _window_vehicle(frm: dict | None, to: dict | None, clock: dict | None = None) -> str:
    a = (frm or {}).get("name") or ""
    b = (to or {}).get("name") or ""
    if _is_side_leg(a, b):
        return "side"
    mode = _classify_window_mode(frm, to, clock, _ms((frm or {}).get("iso")), _ms((to or {}).get("iso")))
    return {"air": "plane", "road": "land", "sail": "main"}.get(mode, "main")


def _window_dest_name(w: dict) -> str:
    return short_name(
        w.get("destName") or (w.get("to") or {}).get("name") or w.get("toName") or ""
    )


def _is_air_window(w: dict | None) -> bool:
    w = w or {}
    if w.get("mode") == "air" or w.get("vehicle") == "plane":
        return True
    return _is_air_leg(
        (w.get("from") or {}).get("name") or w.get("fromName") or "",
        _window_dest_name(w),
    )


def _is_side_window(w: dict | None) -> bool:
    w = w or {}
    if w.get("vehicle") == "side" or w.get("mode") == "side":
        return True
    return _is_side_leg(
        (w.get("from") or {}).get("name") or w.get("fromName") or "",
        _window_dest_name(w),
    )


# RC55 : Saint-Pierre → Halifax est dans l'Atlantique nord (~45–47° N).
# Cayenne / l'équateur / la Guyane (~5° N) n'y ont pas leur place — ces
# phrases restent sur Marigot → Cayenne et Cayenne → Papeete.
_GUYANA_EQUATOR_RE = re.compile(
    r"french guiana|guyane|guyanese|\bequator\b|[\ée]quateur|\bequatorial\b",
    re.I,
)
_SPM_NORTH_LAT = 35.0


def _is_saint_pierre_depart(w: dict | None) -> bool:
    w = w or {}
    frm = w.get("fromName") or (w.get("from") or {}).get("name") or ""
    return _air_stop_key(frm) == "saint-pierre"


def _change_is_guiana_or_equator(change: dict | None) -> bool:
    """Événement de Guyane / d'équateur (titre, lieu dit, ou latitude trop sud)."""
    if not isinstance(change, dict):
        return False
    blob = " ".join(
        str(x) for x in (
            change.get("title"), change.get("fact"), change.get("name"),
            change.get("placeFr"), change.get("placeEn"),
            change.get("event"), change.get("regimeId"),
            *(change.get("members") or []),
        ) if x
    )
    if _GUYANA_EQUATOR_RE.search(blob):
        return True
    lat = None
    try:
        lat = float(change["lat"])
    except (TypeError, ValueError, KeyError):
        pair = _row_latlon(change)
        lat = pair[0] if pair else None
    return lat is not None and lat < _SPM_NORTH_LAT


def _drop_guiana_equator_changes(changes: list[dict]) -> list[dict]:
    return [c for c in changes if not _change_is_guiana_or_equator(c)]


def _is_road_window(w: dict | None) -> bool:
    w = w or {}
    if w.get("mode") == "road" or w.get("vehicle") == "land":
        return True
    return _is_land_leg(
        (w.get("from") or {}).get("name") or w.get("fromName") or "",
        _window_dest_name(w),
    )


def _clock_leave_ms(
    clock: dict | None,
    port_lat: Any,
    port_lon: Any,
    t_a: Optional[int],
    t_b: Optional[int] = None,
    *,
    mode: str = "sail",
) -> Optional[int]:
    """Premier sommet qui quitte le port (d > 2 nm) pour ce mode. Jamais tA + escale."""
    if t_a is None:
        return None
    want = {"air": {"plane"}, "road": {"land"}, "sail": {"main", "boat", "side"}}.get(
        _window_mode_name(mode), {"main", "boat", "side"},
    )
    prev_at = t_a
    for v in ((clock or {}).get("vertices") or []):
        if not isinstance(v, dict):
            continue
        t = _ms(v.get("iso"))
        if t is None or t < t_a:
            continue
        if t_b is not None and t > t_b:
            continue
        veh = v.get("vehicle")
        if veh == "quay":
            continue
        if want and veh not in want:
            continue
        d = _nm_between(port_lat, port_lon, v.get("lat"), v.get("lon"))
        if d is None:
            continue
        if d <= _PORT_LEAVE_NM:
            prev_at = t
            continue
        if t == t_a or d <= _PORT_ANCHOR_NM:
            return t
        return prev_at
    return t_a


def _first_leg_moment_ms(moments: list | None, w: dict) -> Optional[int]:
    """Premier moment émis SUR la jambe (leg.from = port de départ de la fenêtre) :
    la vérité du terrain — si le bateau émet à 13 h, il n'est plus à quai à 13 h."""
    frm = re.split(r"\s*\(", str(w.get("fromName") or ""))[0].strip().casefold()
    if not frm:
        return None
    t_a, t_b = w.get("tA"), w.get("tB")
    best: Optional[int] = None
    for m in moments or []:
        if not isinstance(m, dict):
            continue
        leg = (m.get("moment") or {}).get("leg") or {}
        mf = re.split(r"\s*\(", str(leg.get("from") or ""))[0].strip().casefold()
        if mf != frm:
            continue
        t = _ms(m.get("t"))
        if t is None:
            continue
        if (t_a is not None and t <= t_a) or (t_b is not None and t > t_b):
            continue
        if best is None or t < best:
            best = t
    return best


def _window_depart_ms(w: dict) -> Optional[int]:
    """Départ = premier sommet d'horloge qui quitte le port, jamais tA + jours d'escale."""
    if w.get("departMs"):
        return int(w["departMs"])
    t_a = w.get("tA")
    frm = w.get("from") or {}
    clock = w.get("clock")
    mode = _window_mode_name(str(w.get("mode") or _mode_from_vehicle(w.get("vehicle")) or "sail"))
    leave = _clock_leave_ms(
        clock, frm.get("lat"), frm.get("lon"), t_a, w.get("tB"), mode=mode,
    )
    # RC26 : quand l'horloge répond exactement « départ = tA » (aucune sortie de
    # port trouvée — Papeete, pas de sommet « quay »), l'escale des marks donne
    # l'appareillage (arrivée + holdHours) — les trois jours à quai ne comptent
    # plus comme de la mer dans les fenêtres. Une horloge qui a une vraie trace
    # de sortie garde son départ.
    name = re.split(r"\s*\(", str(w.get("fromName") or ""))[0].strip().casefold()
    t_b = w.get("tB")
    t0 = _ms((clock or {}).get("t0"))
    if name and leave is not None and t_a is not None and leave == t_a:
        for mark in (clock or {}).get("marks") or []:
            mark_name = re.split(r"\s*\(", str(mark.get("name") or ""))[0].strip().casefold()
            if mark_name != name:
                continue
            arr = _ms(mark.get("iso"))
            hold = float(mark.get("holdHours") or 0)
            if arr is not None and t0 is not None and arr <= t0:
                continue  # port de départ du voyage : t0 EST l'appareillage (RG1)
            if arr is not None and hold > 0:
                depart = arr + int(hold * 3_600_000)
                if (
                    t_a is not None and t_a <= depart and (not t_b or depart < t_b)
                    and (leave is None or depart > leave)
                ):
                    return depart
    if leave is not None:
        return leave
    return t_a


def _clock_has_quay(clock: dict | None, stop: dict | None) -> bool:
    if not clock or not stop:
        return False
    lat, lon = stop.get("lat"), stop.get("lon")
    arrived = _ms(stop.get("iso"))
    for v in (clock.get("vertices") or []):
        if not isinstance(v, dict) or v.get("vehicle") != "quay":
            continue
        d = _nm_between(lat, lon, v.get("lat"), v.get("lon"))
        if d is not None and d <= _PORT_ANCHOR_NM:
            return True
    if arrived is None or lat is None or lon is None:
        return False
    leave = _clock_leave_ms(clock, lat, lon, arrived, mode="sail")
    return leave is not None and leave - arrived >= 12 * 3_600_000


def _quay_hours_for_arrival(stop: dict | None, clock: dict | None) -> Any:
    if not stop:
        return 0
    verts = (clock or {}).get("vertices") or []
    if verts:
        return stop.get("holdHours") if _clock_has_quay(clock, stop) else 0
    return stop.get("holdHours")


def _air_return_ms(
    clock: dict | None,
    stay: dict | None,
    after_ms: Optional[int],
    t_end: Optional[int],
) -> Optional[int]:
    lat, lon = (stay or {}).get("lat"), (stay or {}).get("lon")
    if lat is None or lon is None:
        return None
    for v in ((clock or {}).get("vertices") or []):
        if not isinstance(v, dict) or v.get("vehicle") != "plane":
            continue
        t = _ms(v.get("iso"))
        if t is None or (after_ms is not None and t <= after_ms):
            continue
        if t_end is not None and t > t_end:
            continue
        d = _nm_between(lat, lon, v.get("lat"), v.get("lon"))
        if d is not None and d <= _PORT_ANCHOR_NM:
            return t
    return None


def _moment_leg(row: dict) -> dict:
    moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
    leg = moment.get("leg") if isinstance(moment.get("leg"), dict) else {}
    return leg if isinstance(leg, dict) else {}


def _moment_is_air(row: dict) -> bool:
    leg = _moment_leg(row)
    if leg.get("vehicle") == "plane":
        return True
    return _is_air_leg(str(leg.get("from") or ""), str(leg.get("to") or ""))


def _air_return_from_moments(
    moments: list | None,
    stay_name: str,
    after_ms: Optional[int],
) -> Optional[int]:
    stay_key = _air_stop_key(stay_name)
    for row in moments or []:
        if not isinstance(row, dict) or not _moment_is_air(row):
            continue
        t = _ms(row.get("t"))
        if t is None or (after_ms is not None and t <= after_ms):
            continue
        dest = str(_moment_leg(row).get("to") or "")
        if stay_key and _air_stop_key(dest) == stay_key:
            return t
        if stay_name and same_stop(dest, stay_name):
            return t
    return None


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
    sea = next(
        (
            s for s in rest
            if _ROCHELLE_RE.search(s.get("name") or "")
            and float(s.get("filmNm") if s.get("filmNm") is not None else s.get("nm") or 0) < 2000
        ),
        None,
    )
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
    return _recover_air_stops([head, *rest], raw, clock)


def _plane_iso_near(vertices: list | None, lat: Any, lon: Any) -> Optional[str]:
    """Iso d'un sommet avion déjà calculé, près de l'escale — pas une date inventée."""
    try:
        plat, plon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    best_iso = None
    best_d2 = 0.25
    for v in vertices or []:
        if not isinstance(v, dict) or v.get("vehicle") != "plane":
            continue
        try:
            dlat = float(v.get("lat")) - plat
            dlon = float(v.get("lon")) - plon
        except (TypeError, ValueError):
            continue
        d2 = dlat * dlat + dlon * dlon
        if d2 < best_d2 and _ms(v.get("iso")) is not None:
            best_d2 = d2
            best_iso = v.get("iso")
    return str(best_iso) if best_iso else None


def _air_src_row(src: dict, iso: str) -> dict:
    film = src.get("filmNm") if src.get("filmNm") is not None else src.get("nm")
    return {
        "name": src["name"],
        "iso": iso,
        "filmNm": float(film or 0),
        "nm": float(src["nm"]) if isinstance(src.get("nm"), (int, float)) else float(film or 0),
        "holdHours": float(src.get("holdHours") or 0),
        "lat": src.get("lat") if isinstance(src.get("lat"), (int, float)) else None,
        "lon": src.get("lon") if isinstance(src.get("lon"), (int, float)) else None,
        "vehicle": src.get("vehicle") if src.get("vehicle") in {"plane", "land", "main", "side"} else None,
    }


def _recover_air_stops(dated: list[dict], raw: list | None, clock: dict | None) -> list[dict]:
    """Halifax / Cayenne absents des dates (arrivée avion hors clock_marks) : iso du sommet plane."""
    have = {_air_stop_key(s.get("name") or "") for s in dated}
    pool = [m for m in (raw or []) if isinstance(m, dict)]
    pool.extend(m for m in ((clock or {}).get("marks") or []) if isinstance(m, dict))
    vertices = [v for v in ((clock or {}).get("vertices") or []) if isinstance(v, dict)]
    out = list(dated)
    for key in ("cayenne", "halifax"):
        if key in have:
            continue
        src = next((m for m in pool if _air_stop_key(m.get("name") or "") == key), None)
        if src is None:
            continue
        iso = src.get("iso") if _ms(src.get("iso")) is not None else None
        if iso is None:
            hit = next(
                (
                    m for m in ((clock or {}).get("marks") or [])
                    if isinstance(m, dict)
                    and _air_stop_key(m.get("name") or "") == key
                    and _ms(m.get("iso")) is not None
                ),
                None,
            )
            if hit:
                iso = hit.get("iso")
        if iso is None:
            iso = _plane_iso_near(vertices, src.get("lat"), src.get("lon"))
        if iso is None:
            continue
        row = _air_src_row(src, str(iso))
        cay_i = next((i for i, s in enumerate(out) if _air_stop_key(s.get("name") or "") == "cayenne"), None)
        if key == "halifax" and cay_i is not None:
            out.insert(cay_i + 1, row)
        else:
            out.append(row)
        have.add(key)
    return out


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
                named = [
                    c for c in clock_marks
                    if name and same_stop(c.get("name") or "", name)
                ]
                compat = [
                    c for c in named
                    if abs(float(c.get("filmNm") if c.get("filmNm") is not None else c.get("nm") or 0) - film) < 80
                    or (film < 2000 and float(c.get("filmNm") if c.get("filmNm") is not None else c.get("nm") or 0) < 2000)
                ]
                hit = compat[0] if compat else None
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
        # Halifax / Cayenne de l'épisode : aller et retour gardés si l'iso diffère.
        same = [x for x in out if same_stop(x["name"], m["name"])]
        if same:
            key = _air_stop_key(m["name"])
            if key not in {"halifax", "cayenne", "saint-pierre"}:
                continue
            t_new = _ms(m.get("iso"))
            t_old = _ms(same[-1].get("iso"))
            if t_new is None or t_old is None or abs(t_new - t_old) < 6 * 3_600_000:
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
    return {"climo": 50, "sci": 40, "amp": 30, "project": 30, "zee": 20, "poe": 10, "note": 5, "stop": 1}.get(kind, 0)


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
        if event == "exit":
            return None
        return 1
    if kind == "project":
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
        if e.get("kind") == "amp" and e.get("event") == "exit":
            continue
        if e.get("kind") == "poe":
            key = e.get("poeId") or e.get("name")
            if not key or key in seen_poe:
                continue
            seen_poe.add(key)
        if e.get("kind") == "sci":
            from ici_engine import science_type_key  # noqa: PLC0415
            if not science_type_key(_station_item(e)):
                continue
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


def _film_compact_template(seconds: Any) -> bool:
    """Variante 2:30 : ouvertures et arrivées courtes. 3:00 et intégral = gabarit RG6."""
    s = _film_seconds(seconds)
    return 0 < s <= 150


def film_char_budget(seconds: Any) -> int:
    """Plafond en caractères à 15 car./s. 0 = intégral, sans plafond."""
    s = _film_seconds(seconds)
    if s <= 0:
        return 0
    return int(s * FILM_ESTIMATE_CPS)


def film_write_window(seconds: Any) -> Optional[tuple[int, int]]:
    """Fenêtre acceptée du rédigé. None = intégral, pas de rejet de longueur."""
    budget = film_char_budget(seconds)
    if budget <= 0:
        return None
    return int(budget * 0.9), int(budget * 1.1)


def film_priority_tier(seconds: Any) -> int:
    """P2 (2:30), P3 (3:00) ou P4 (intégral)."""
    s = _film_seconds(seconds)
    if s <= 0:
        return FILM_TIER_FULL
    if s <= 150:
        return FILM_TIER_SHORT
    return FILM_TIER_MEDIUM


def film_estimated_seconds(chars: int, cps: float | None = None) -> int:
    """Durée parlée = caractères ÷ débit mesuré ou 15 car./s. Jamais un chiffre inventé."""
    n = int(chars or 0)
    if n <= 0:
        return 0
    rate = float(cps) if cps and float(cps) > 0 else float(FILM_ESTIMATE_CPS)
    return max(1, int(round(n / rate)))


def _best_named_change(rows: list[dict], *, gold_first: bool) -> Optional[dict]:
    usable = [c for c in rows if isinstance(c, dict)]
    if not usable:
        return None

    def gold(c: dict) -> int:
        return 0 if c.get("gold_on") in (True, 1, "1", "true", "True") else 1

    usable.sort(key=lambda c: (
        gold(c) if gold_first else 0,
        change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
        c.get("tMs") or 0,
    ))
    return usable[0]


def _amp_and_project(amp: list[dict], proj: list[dict]) -> list[dict]:
    """2:30 : une AMP et un projet s'ils existent (plus proche ; projet : gold_on
    d'abord). RC26 : seulement des items qui donneront une phrase — un projet au
    titre anglais que speak_change refuse gaspillait le créneau de la variante."""
    out: list[dict] = []
    picked_amp = _best_named_change([c for c in amp if _would_speak(c)], gold_first=False)
    picked_proj = _best_named_change([c for c in proj if _would_speak(c)], gold_first=True)
    if picked_amp is not None:
        out.append(picked_amp)
    if picked_proj is not None:
        out.append(picked_proj)
    return out


def _tier_route_extras(
    zee: list[dict],
    coast: list[dict],
    amp: list[dict],
    proj: list[dict],
    climo: list[dict],
    stations: list[dict],
    *,
    tier: Optional[int],
) -> list[dict]:
    if tier is None or tier >= FILM_TIER_FULL:
        return zee + coast + amp + proj + climo + stations
    extras = list(zee)
    if tier <= FILM_TIER_SHORT:
        extras.extend(_amp_and_project(amp, proj))
        return extras
    return extras + coast + amp + proj + climo


def _tier_allows_kind(kind: str, tier: Optional[int]) -> bool:
    if tier is None or tier >= FILM_TIER_FULL:
        return True
    k = str(kind or "")
    if k in {"escale", "approche", "zee-enter", "alert-on", "cyclone", "marina", "amp", "project"}:
        return True
    if tier >= FILM_TIER_MEDIUM and k in {"coast", "climo"}:
        return True
    return False


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
    legs = _review_legs(review)
    for leg in legs:
        if same_stop(leg.get("from") or "", frm) and same_stop(leg.get("to") or "", to):
            return leg
    # Vol : le bateau repart de Cayenne, la revue date encore Saint-Pierre → dest.
    if _air_stop_key(frm) == "cayenne":
        for leg in legs:
            if same_stop(leg.get("to") or "", to) and _is_air_only_stop(leg.get("from") or ""):
                return leg
    return None


def _window_leg_nm(w: dict) -> Optional[float]:
    """Écart de milles de l'horloge / des marques — même source que plan-review."""
    frm = w.get("from") or {}
    dest = w.get("to") or {}

    def num(row: dict | None, *keys: str) -> Optional[float]:
        for key in keys:
            val = (row or {}).get(key)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return float(val)
        return None

    a_nm, b_nm = num(frm, "nm"), num(dest, "nm")
    if a_nm is not None and b_nm is not None and (b_nm - a_nm) > 1:
        return b_nm - a_nm
    a = num(frm, "nm", "filmNm")
    b = num(dest, "nm", "filmNm")
    if b is None and isinstance(w.get("destNm"), (int, float)):
        b = float(w["destNm"])
    if a is None or b is None:
        return None
    gap = b - a
    return gap if gap > 1 else None


def chapter_metrics(w: dict, review: dict | None = None) -> dict[str, Any]:
    """legNm, daysAtSea, plannedKnots : revue d'abord, sinon la même formule que plan-review."""
    to = w.get("toName") or w.get("destName") or ""
    frm = w.get("fromName") or (w.get("from") or {}).get("name") or ""
    leg = review_leg_for_chapter(review, frm, to)
    nm = days = kn = None
    if leg:
        if isinstance(leg.get("legNm"), (int, float)):
            nm = float(leg["legNm"])
        if isinstance(leg.get("daysAtSea"), (int, float)):
            days = float(leg["daysAtSea"])
        if isinstance(leg.get("plannedKnots"), (int, float)):
            kn = float(leg["plannedKnots"])
    if nm is None and not _is_air_window(w):
        nm = _window_leg_nm(w)
    if nm is not None and not _is_road_window(w) and (days is None or kn is None):
        from plan_review import PLANNED_KNOTS, planned_sea_days  # noqa: PLC0415
        if kn is None:
            kn = float(PLANNED_KNOTS)
        if days is None:
            days = planned_sea_days(float(nm), float(kn))
    return {"legNm": nm, "daysAtSea": days, "plannedKnots": kn}


def chapter_shape(w: dict, i: int, n: int, metrics: dict | None = None) -> str:
    """Connecteur lié au contenu : first / long / hop / last / ''."""
    if _is_air_window(w) or _is_road_window(w):
        return ""
    metrics = metrics or {}
    if w.get("last") or (n and i == n - 1):
        return "last"
    days = metrics.get("daysAtSea")
    nm = metrics.get("legNm")
    if (isinstance(days, (int, float)) and days >= 10) or (
        isinstance(nm, (int, float)) and nm >= 2000
    ):
        return "long"
    if i > 1 and (
        (isinstance(days, (int, float)) and days <= 3)
        or (isinstance(nm, (int, float)) and nm <= 250)
    ):
        return "hop"
    return ""


def spoken_sea_days(days: Any, lang: str = "fr") -> str:
    """Jours de mer arrondis à la voix : 9,5 → « une dizaine de jours de mer »."""
    try:
        d = float(days)
    except (TypeError, ValueError):
        return ""
    en = _en(lang)
    if d < 1.5:
        return "one day at sea" if en else "un jour de mer"
    if d < 8:
        n = int(round(d))
        if en:
            return f"{_spoken_int(n, lang)} day{'' if n == 1 else 's'} at sea"
        return f"{_spoken_int(n, lang)} jour{'' if n == 1 else 's'} de mer"
    if d < 12.5:
        return "about ten days at sea" if en else "une dizaine de jours de mer"
    if d < 17.5:
        return "about fifteen days at sea" if en else "une quinzaine de jours de mer"
    if d < 25:
        return "about twenty days at sea" if en else "une vingtaine de jours de mer"
    if d < 35:
        return "about thirty days at sea" if en else "une trentaine de jours de mer"
    if d < 45:
        return "about forty days at sea" if en else "une quarantaine de jours de mer"
    n = int(round(d))
    return f"{n} days at sea" if en else f"{n} jours de mer"


def _opening_nm_label(nm: Any, lang: str) -> str:
    """« 1 820 milles » / « 1,820 miles » — chiffres du plan-review, pas « nm »."""
    try:
        v = int(round(float(nm)))
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    if _en(lang):
        return f"{v:,} miles"
    return f"{v:,} milles".replace(",", " ")


def _spoken_days_word(n: int, lang: str) -> str:
    if _en(lang):
        return f"{_spoken_int(n, lang)} day" + ("" if n == 1 else "s")
    return f"{_spoken_int(n, lang)} jour" + ("" if n == 1 else "s")


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


def eta_fingerprint(eta: dict | None) -> str:
    stops = (eta or {}).get("stops") if isinstance(eta, dict) else None
    if not isinstance(stops, dict) or not stops:
        return ""
    bits: list[str] = []
    for name in sorted(stops):
        raw = stops[name]
        if not isinstance(raw, dict):
            continue
        bits.append(
            f"{name}|{raw.get('p10')}|{raw.get('p50')}|{raw.get('p90')}|{raw.get('members')}"
        )
    return hashlib.sha256("\n".join(bits).encode("utf-8")).hexdigest() if bits else ""


def _stop_spoken(name: str) -> str:
    """Nom d'escale à la voix : « Nouméa », sans parenthèse de territoire."""
    raw = re.sub(r"\s*\([^)]*\)\s*", " ", short_name(name) or "")
    return re.sub(r"\s+", " ", raw).strip()


def review_plan_stats(review: dict | None) -> dict[str, Any]:
    """Totaux du plan-review : destinations uniques, somme des legNm, destination finale.

    Aucun chiffre inventé : une jambe sans `legNm` n'entre pas dans la somme ;
    sans jambe, `nStops` et `totalNm` restent vides.
    """
    dests: list[str] = []
    seen: set[str] = set()
    total = 0.0
    has_nm = False
    for leg in _review_legs(review):
        to = _stop_spoken(leg.get("to") or "")
        if to:
            key = norm_stop(to)
            if key and key not in seen:
                seen.add(key)
                dests.append(to)
        nm = leg.get("legNm")
        if isinstance(nm, (int, float)) and not isinstance(nm, bool) and float(nm) > 0:
            total += float(nm)
            has_nm = True
    return {
        "nStops": len(dests) if dests else None,
        "totalNm": total if has_nm else None,
        "finalDest": dests[-1] if dests else "",
        "dests": dests,
    }


def upcoming_stop_names(
    review: dict | None,
    current_dest: str,
    *,
    arrived: bool = False,
) -> list[str]:
    """Escales à venir dans l'ordre du plan-review, depuis la dest courante.

    Si la dest courante n'est pas dans la revue, on se tait (rien n'est inventé).
    Les escales avion seules (Halifax…) sont omises : le bateau n'y va pas.
    """
    dests = [
        name for name in (review_plan_stats(review).get("dests") or [])
        if name and not _is_air_only_stop(name)
    ]
    if not dests or not current_dest:
        return []
    idx = next((i for i, name in enumerate(dests) if same_stop(name, current_dest)), None)
    if idx is None:
        return []
    start = idx + 1 if arrived else idx
    return dests[start:]


def eta_payload_for_stop(eta: dict | None, name: str) -> dict | None:
    """Entrée du stock eta pour une escale. `members` ≤ 0 → absente (pas de date inventée)."""
    if not isinstance(eta, dict) or not name:
        return None
    stops = eta.get("stops") if isinstance(eta.get("stops"), dict) else {}
    raw = stops.get(name) if name in stops else None
    if not isinstance(raw, dict):
        needle = name.strip().casefold()
        for key, payload in stops.items():
            if not isinstance(payload, dict):
                continue
            if same_stop(key, name) or needle in key.casefold() or key.casefold() in needle:
                raw = payload
                break
    if not isinstance(raw, dict):
        return None
    try:
        members = int(raw.get("members") or 0)
    except (TypeError, ValueError):
        members = 0
    if members <= 0:
        return None
    return raw


def _honest_bookend(text: str, facts: Any, lang: str) -> str:
    filtered, _dropped = filter_numbers(text, facts)
    sentence = (filtered or "").strip()
    if not sentence:
        return ""
    return speak_film_text(sentence, lang)


def _film_open_sentences(
    *,
    start_name: str,
    sea_name: str,
    lang: str,
    display_t0: str | None = None,
    review: dict | None = None,
    compact: bool = False,
) -> list[str]:
    """Ouverture du film (2 phrases) : qui, d'où, par la route, totaux du plan-review.

    Variante 2:30 (`compact`) : UNE phrase (chapitre 0, Saint-Maur → La Rochelle).
    """
    en = _en(lang)
    shown = display_t0 or OFFICIAL_T0
    when = day_month(rebase_iso(OFFICIAL_T0, OFFICIAL_T0, shown), lang, year=True)
    frm = short_name(start_name or "Saint-Maur") or "Saint-Maur"
    sea = short_name(sea_name or "La Rochelle") or "La Rochelle"
    stats = review_plan_stats(review)
    n = stats.get("nStops")
    total = stats.get("totalNm")
    final = short_name(stats.get("finalDest") or "")
    nm_s = _opening_nm_label(total, lang) if total is not None else ""
    n_s = ""
    if isinstance(n, int) and n > 0:
        if n <= 30:
            n_s = f"{_spoken_int(n, lang)} {'stops' if en else 'escales'}"
        else:
            n_s = f"{n} stops" if en else f"{n} escales"
    if en:
        first = f"The Berry-Mappemonde expedition left {frm} on {when} by road to {sea}."
    else:
        first = (
            f"L’expédition Berry-Mappemonde a quitté {frm} le {when} "
            f"par la route jusqu’à {sea}."
        )
    second = ""
    if n_s and nm_s and final:
        second = (
            f"The plan has {n_s} and {nm_s}, through to {final}."
            if en else
            f"Le plan compte {n_s} et {nm_s}, jusqu’à {final}."
        )
    elif n_s and nm_s:
        second = (
            f"The plan has {n_s} and {nm_s}."
            if en else
            f"Le plan compte {n_s} et {nm_s}."
        )
    elif final:
        second = f"The destination is {final}." if en else f"La destination est {final}."
    facts = _facts_with_rounded({
        "t0": shown,
        "officialT0": OFFICIAL_T0,
        "nStops": n,
        "totalNm": int(round(float(total))) if total is not None else None,
        "totalNmLabel": nm_s,
        "finalDest": final,
    })
    out: list[str] = []
    for raw in (first, second):
        if not raw:
            continue
        spoken = _honest_bookend(raw, facts, lang)
        if spoken:
            out.append(spoken)
    if compact:
        return out[:1]
    return out


def _eta_sentence(name: str, eta: dict | None, lang: str) -> str:
    raw = eta_payload_for_stop(eta, name)
    if not raw or not name:
        return ""
    d10 = day_month(raw.get("p10"), lang)
    d50 = day_month(raw.get("p50"), lang)
    d90 = day_month(raw.get("p90"), lang)
    en = _en(lang)
    if d10 and d90:
        return (
            f"Arrival at {name} between {d10} and {d90}."
            if en else
            f"Arrivée à {name} entre le {d10} et le {d90}."
        )
    when = d50 or d10 or d90
    if not when:
        return ""
    return (
        f"Arrival at {name} on {when}."
        if en else
        f"Arrivée à {name} le {when}."
    )


def _upcoming_sentence(names: list[str], lang: str) -> str:
    if not names:
        return ""
    label = ", ".join(names)
    return f"Stops still to come: {label}." if _en(lang) else f"Les escales à venir : {label}."


def _stored_review_and_eta() -> tuple[dict | None, dict | None]:
    """Lit le stock RF2. Absence → (None, None), jamais une valeur inventée."""
    review = eta = None
    try:
        from official_store import payload_of  # noqa: PLC0415
        stored = payload_of("plan_review")
        if isinstance(stored, dict) and stored.get("legs"):
            review = stored
        stored_eta = payload_of("eta")
        if isinstance(stored_eta, dict):
            eta = stored_eta
    except Exception:
        return None, None
    return review, eta


def _lane_crossings(clock: dict | None, t_a: Optional[int], t_b: Optional[int]) -> dict[str, int] | None:
    """{nom de couloir (SHIPPING_LANES, casefold) : premier instant du chapitre
    dans la boîte} — None si l'horloge n'a pas de sommet daté dans la fenêtre
    (on ne filtre pas : les tests et le chemin sans trace gardent la revue)."""
    from shipping_lanes import SHIPPING_LANES  # noqa: PLC0415
    if not isinstance(clock, dict):
        return None
    t0 = _ms(clock.get("t0"))
    out: dict[str, int] = {}
    saw = False
    for v in clock.get("vertices") or []:
        if not isinstance(v, dict) or v.get("vehicle") in {"plane", "land"}:
            continue
        t = _ms(v.get("iso"))
        if t is None and t0 is not None and v.get("tHours") is not None:
            try:
                t = t0 + int(float(v["tHours"]) * 3_600_000)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        if t_a is not None and t < t_a:
            continue
        if t_b is not None and t > t_b:
            continue
        try:
            lat, lon = float(v["lat"]), float(v["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        saw = True
        for lon_min, lat_min, lon_max, lat_max, _w, name in SHIPPING_LANES:
            key = name.casefold()
            if key in out:
                continue
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                out[key] = t
    return out if saw else None


def _lane_named_in_chapter(name: str, already: str) -> bool:
    """Un couloir déjà dit (Gibraltar en côte) : on le retire, on ne jette pas Gascogne."""
    blob = str(already or "")
    if not blob:
        return False
    for part in re.findall(r"[A-ZÀ-Ÿ][\w'’\-]{3,}", str(name or "")):
        if part and part in blob:
            return True
    return False


def review_sentences(
    leg: dict | None, lang: str = "fr", crossings: dict[str, int] | None = None,
    already: str = "",
) -> list[str]:
    """Faits de revue fondus dans la route : plus d'annexe « À surveiller / Couloirs ».

    RC30 : `crossings` (couloir → instant du premier croisement dans le
    chapitre) filtre « La route passe par … » aux seuls bassins que la TRACE du
    chapitre traverse, dans l'ordre de la route — Papeete n'entend plus
    « Atlantique nord » hérité d'une autre portion de la jambe de revue.
    RC35 : un nom déjà dit (Gibraltar) est retiré de la liste, les autres
    (Gascogne) restent ; le Pacifique n'est pas une boîte AIS (voir
    `_append_review_sentences`)."""
    if not isinstance(leg, dict):
        return []
    en = _en(lang)
    bits: list[str] = []
    season = leg.get("season") if isinstance(leg.get("season"), dict) else None
    gale = season.get("galePct") if season else None
    cyclones = season.get("cyclones") if season else None
    pack = leg.get("antiShipping") if isinstance(leg.get("antiShipping"), dict) else None
    raw_lanes = [
        n.strip() for n in ((pack or {}).get("lanes") or [])
        if isinstance(n, str) and n.strip()
    ] if pack else []
    if crossings is not None:
        raw_lanes = [n for n in raw_lanes if n.casefold() in crossings]
        raw_lanes.sort(key=lambda n: crossings[n.casefold()])
    lanes = [clean_spoken_label(n, lang) for n in raw_lanes]
    lanes = [n for n in lanes if n and not looks_english_title(n)]
    if already:
        lanes = [n for n in lanes if not _lane_named_in_chapter(n, already)]

    if lanes:
        def _lane(n: str) -> str:
            if re.match(r"^(le |la |l['’]|the )", n, re.I):
                return n
            if re.match(r"^(détroit|golfe|canal|cap)\b", n, re.I):
                return f"the {n}" if en else f"le {n}"
            if re.match(r"^(mer|méditerranée|caraïbe|atlantique)\b", n, re.I):
                return n if en else (n if n[:1].islower() else n)
            return n
        names = ", ".join(_lane(n) for n in lanes)
        bits.append(
            f"The route goes through {names}."
            if en else
            f"La route passe par {names}."
        )

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


def _append_review_sentences(
    bits: list[str],
    review: dict | None,
    window: dict,
    lang: str,
    anchored: list | None = None,
) -> None:
    """Ajoute les phrases de revue au chapitre. Chiffres via filter_numbers."""
    to = window.get("toName") or window.get("destName") or ""
    leg = review_leg_for_chapter(review, window.get("fromName") or "", to)
    if not leg:
        return
    already = " ".join(bits)
    facts = _facts_with_rounded(leg)
    clock = window.get("clock")
    marks = (clock or {}).get("marks")
    t_a, t_b = window.get("tA"), window.get("tB")
    crossings = _lane_crossings(clock, t_a, t_b)
    pack = leg.get("antiShipping") if isinstance(leg.get("antiShipping"), dict) else None
    spoken_lanes = [
        n for n in ((pack or {}).get("lanes") or [])
        if isinstance(n, str) and n.strip()
        and (crossings is None or n.strip().casefold() in crossings)
        and not _lane_named_in_chapter(clean_spoken_label(n, lang), already)
    ]
    lane_ts = [
        crossings[str(n).strip().casefold()]
        for n in spoken_lanes
        if crossings and str(n).strip().casefold() in crossings
    ]
    lane_anchor = min(lane_ts) if lane_ts else None
    for sentence in review_sentences(leg, lang, crossings=crossings, already=already):
        filtered, _dropped = filter_numbers(sentence, facts)
        sentence = (filtered or "").strip()
        if not sentence:
            continue
        if (
            not re.search(r"passe par|goes through", sentence, re.I)
            and any(part and part in already for part in re.findall(r"[A-ZÀ-Ý][\w'-]{3,}", sentence))
        ):
            continue
        bits.append(sentence)
        already = " ".join(bits)
        if anchored is None:
            continue
        if lane_anchor is not None and re.search(r"passe par|goes through", sentence, re.I):
            # RC30 : la phrase des bassins se dit QUAND la route les croise —
            # jamais collée à l'arrivée (tri des phrases par ancre ensuite).
            anchored.append((sentence, lane_anchor, {"kind": "coast"}))
            continue
        place = ""
        geo = re.search(
            r"((?:détroit|strait|golfe|bay)(?: de| of)? [A-ZÀ-Ÿ][\w'’\-]+)",
            sentence,
            re.I,
        )
        if geo:
            place = geo.group(1)
        else:
            named = re.search(r"\b([A-ZÀ-Ÿ][\w'’\-]{4,})\b", sentence)
            if named and named.group(1).casefold() not in {"route", "the", "gale", "coup", "then", "puis"}:
                place = named.group(1)
        t_ms = _clock_time_near_place(clock, place, t_a, t_b, marks) if place else None
        if t_ms is None:
            t_ms = t_a
        extra = {"place": place, "kind": "coast"} if place else {}
        anchored.append((sentence, t_ms, extra) if extra else (sentence, t_ms))
    pacific_ms = _pacific_arrival_ms(clock, t_a, t_b)
    if pacific_ms is not None and not re.search(r"\b(pacifique|pacific)\b", already, re.I):
        sentence = "The Pacific." if _en(lang) else "Pacifique."
        bits.append(sentence)
        if anchored is not None:
            anchored.append((
                sentence,
                t_b if t_b is not None else pacific_ms,
                {"kind": "coast", "place": "Pacifique"},
            ))


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


_EN_WATERS_CANON: Optional[dict[str, str]] = None
_EN_WATERS_RE: Optional[re.Pattern[str]] = None
_RC53_EN_WATERS = (
    "French", "Italian", "Moroccan", "Madeira", "Martinique", "Guadeloupe",
)


def _en_waters_canon() -> dict[str, str]:
    """Exonymes EN de la table (adj / nom) → casse canonique. RC53."""
    global _EN_WATERS_CANON, _EN_WATERS_RE
    if _EN_WATERS_CANON is None:
        canon: dict[str, str] = {}
        for row in toponyms.territories():
            for key in ("adj_en", "en"):
                val = str(row.get(key) or "").strip()
                if val and "water" not in val.casefold():
                    canon[val.casefold()] = val
        for extra in _RC53_EN_WATERS:
            canon.setdefault(extra.casefold(), extra)
        names = sorted((n for n in canon if n), key=len, reverse=True)
        alt = "|".join(re.escape(n) for n in names)
        _EN_WATERS_CANON = canon
        _EN_WATERS_RE = re.compile(rf"\b(?:{alt})\s+waters\b", re.I) if alt else re.compile(r"(?!x)x")
    return _EN_WATERS_CANON


def fix_en_waters_casing(text: str) -> str:
    """« french waters » → « French waters ». La forme déjà capitale ne bouge pas.

    Filet à la lecture (RC53) : `thin_chapter_dates` mettait en minuscule la
    tête de phrase après « Then, » — on rétablit le nom propre sans rebuild.
    """
    blob = text or ""
    if not blob:
        return blob
    _en_waters_canon()
    rx = _EN_WATERS_RE
    if rx is None:
        return blob

    def repl(m: re.Match) -> str:
        raw = m.group(0)
        head = re.sub(r"\s+waters$", "", raw, flags=re.I)
        canon = (_EN_WATERS_CANON or {}).get(head.casefold())
        return f"{canon} waters" if canon else raw

    return rx.sub(repl, blob)


def speak_film_text(text: str, lang: str = "fr") -> str:
    """Texte du film : distances arrondies, unités parlées, pas de décimale."""
    spoken = round_spoken_distances(text or "", lang)
    spoken = expand_spoken_units(spoken, lang)
    spoken = round_spoken_decimals(spoken)
    spoken = scrub_spoken(spoken)
    if _en(lang):
        spoken = fix_en_waters_casing(spoken)
    return spoken


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
        packed = {**e, **ev, "t": e.get("t") or ev.get("t"), "kind": "climo"}
        spoken = climo_sentence(packed, lang)
        if spoken:
            return spoken
        event = e.get("event") or ""
        detail = {
            "calms": " — equatorial calms" if en else " — calmes équatoriaux",
            "cyclone-enter": " — cyclone season" if en else " — saison cyclonique",
        }.get(event, "")
        if not detail:
            return ""
        return (
            f"On {when}, the climate regime changed{detail}."
            if en else
            f"Le {when}, le régime climatique a changé{detail}."
        )
    if ev.get("kind") == "sci":
        spoken = station_spoken_label({**e, **ev}, lang)
        if not spoken:
            return ""
        if when:
            return f"On {when}, {spoken}." if en else f"Le {when}, {spoken}."
        return f"{spoken[0].upper()}{spoken[1:]}."
    if ev.get("kind") == "amp":
        from ici_engine import spoken_amp_name  # noqa: PLC0415
        spoken = spoken_amp_name(name) or name
        if not spoken:
            return ""
        packed = dict(ev)
        if isinstance(e, dict) and e is not ev:
            for key in ("event", "inside", "nm", "traffic", "speed", "facts", "name"):
                if e.get(key) not in (None, ""):
                    packed.setdefault(key, e[key])
        return _amp_film_sentence(spoken, packed, lang, when)
    if ev.get("kind") == "project":
        nm = _fact_num(e, "nm")
        dist = spoken_distance(nm, lang) if nm is not None else ""
        if dist:
            return (
                f"On {when}, {dist} away, project {name}."
                if en else
                f"Le {when}, à {dist}, le projet {name}."
            )
        return (
            f"On {when}, project {name}."
            if en else
            f"Le {when}, le projet {name}."
        )
    if ev.get("kind") == "zee":
        if not name or NO_DATA_RE.search(name):
            return ""
        waters = zee_waters_label(name, lang)
        if not waters:
            return ""
        return f"On {when}, {waters}." if en else f"Le {when}, {waters}."
    if ev.get("kind") == "coast":
        return coast_sentence({
            **ev, "title": name, "t": ev.get("t"), "ports": [name] if name else [],
        }, lang)
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


_EMPTY_WHEN_RE = re.compile(r"^(Le|On) ,\s*")


def _tidy_empty_when(text: str) -> str:
    """event_sentence prefixes « Le {when}, » — drop the comma if the date is missing."""
    s = str(text or "").strip()
    s = _EMPTY_WHEN_RE.sub("", s).strip()
    if s and s[0].islower():
        return s[0].upper() + s[1:]
    return s


def _ici_event_iso(ev: dict) -> str | None:
    payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
    for raw in (ev.get("t"), ev.get("iso"), payload.get("t"), payload.get("iso")):
        if raw:
            return str(raw)
    return None


def phrase_for_ici_event(ev: dict | None, lang: str = "fr") -> str:
    """Same film-script sentence the film would say for this ici() event.

    Maps zee-enter / amp-enter / poe-ahead / … onto event_sentence,
    change_sentence or _arrival_sentence. Empty when the film would stay silent
    (the client template remains the fallback).
    """
    if not isinstance(ev, dict):
        return ""
    typ = str(ev.get("type") or ev.get("event") or "")
    payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
    t = _ici_event_iso(ev)
    name = ev.get("name")

    if typ in {"zee-enter", "zee-ahead"}:
        zee = payload.get("zee") if isinstance(payload.get("zee"), dict) else {}
        spoken = name or zee.get("name")
        film_ev = {
            "kind": "zee",
            "name": spoken,
            "t": t,
            "entry": {"t": t, "name": spoken},
        }
        return _tidy_empty_when(event_sentence(film_ev, lang))

    if typ == "zee-exit":
        return ""

    if typ in {"amp-enter", "amp-ahead"}:
        amp = payload.get("amp") if isinstance(payload.get("amp"), dict) else {}
        spoken = name or amp.get("name")
        try:
            from ici_engine import is_fishing_amp  # noqa: PLC0415
            if is_fishing_amp({"name": spoken, "title": spoken}):
                return ""
        except Exception:
            pass
        nm = amp.get("nm")
        if nm is None:
            nm = payload.get("whenNm") if payload.get("whenNm") is not None else ev.get("whenNm")
        ev_kind = "enter" if typ == "amp-enter" else "nearby"
        entry_code = amp.get("entry") if not isinstance(amp.get("entry"), dict) else None
        film_ev = {
            "kind": "amp",
            "name": spoken,
            "t": t,
            "traffic": amp.get("traffic"),
            "speed": amp.get("speed"),
            "entry": {
                "t": t,
                "name": spoken,
                "event": ev_kind,
                "inside": typ == "amp-enter",
                "facts": {"nm": nm},
                "nm": nm,
                "traffic": amp.get("traffic"),
                "speed": amp.get("speed"),
                "entry": entry_code,
            },
        }
        raw = event_sentence(film_ev, lang)
        if not raw:
            raw = change_sentence({
                "kind": "amp",
                "t": t,
                "title": spoken or "",
                "event": ev_kind,
                "inside": typ == "amp-enter",
                "nm": nm,
                "fact": spoken or "",
                "traffic": amp.get("traffic"),
                "speed": amp.get("speed"),
                "entry": entry_code,
            }, lang)
        return _tidy_empty_when(raw)

    if typ == "poe-ahead":
        poe = payload.get("poe") if isinstance(payload.get("poe"), dict) else {}
        spoken = name or poe.get("name")
        raw = event_sentence({
            "kind": "poe",
            "name": spoken,
            "t": t,
            "entry": {"t": t, "name": spoken},
        }, lang)
        return _tidy_empty_when(raw)

    if typ in {"wind-shift", "wind-gale", "wx-alert"}:
        kn = payload.get("tws")
        if kn is None:
            kn = payload.get("maxWindKnots")
        hs = payload.get("hs")
        raw = event_sentence({
            "kind": "wx",
            "t": t,
            "entry": {
                "t": t,
                "facts": {"maxWindKnots": kn, "hs": hs},
                "maxWindKnots": kn,
            },
        }, lang)
        return _tidy_empty_when(raw)

    if typ in {"stop", "escale", "arrival"}:
        spoken = name or (payload.get("harbour") or {}).get("name") or payload.get("stop") or ""
        stop = {"name": spoken, "iso": t, "holdHours": payload.get("holdHours") or 0}
        raw = _arrival_sentence(stop, lang)
        if not raw:
            raw = change_sentence({"kind": "escale", "t": t, "title": spoken}, lang)
        return _tidy_empty_when(raw)

    return ""


def _iso_for_ici_bag(bag: dict) -> str | None:
    if not isinstance(bag, dict):
        return None
    for key in ("t", "iso"):
        if bag.get(key):
            return str(bag[key])
    at = bag.get("at") if isinstance(bag.get("at"), dict) else {}
    if at.get("iso") or at.get("t"):
        return str(at.get("iso") or at.get("t"))
    lat, lon = at.get("lat"), at.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    try:
        from official_store import payload_of  # noqa: PLC0415
        from ici_engine import haversine_nm  # noqa: PLC0415
        body = payload_of("climo") or {}
        best, best_d = None, 40.0
        for f in body.get("fiches") or []:
            if not isinstance(f, dict) or f.get("lat") is None or not f.get("iso"):
                continue
            d = haversine_nm(float(lat), float(lon), float(f["lat"]), float(f["lon"]))
            if d < best_d:
                best, best_d = f, d
        if best:
            return str(best["iso"])
        clock = body.get("clock") if isinstance(body.get("clock"), dict) else {}
        live = clock.get("live") if isinstance(clock.get("live"), dict) else {}
        return live.get("iso") or clock.get("nowIso") or clock.get("iso")
    except Exception:
        return None


def _amp_phrase_key(amp: dict, kind: str) -> str:
    ident = amp.get("site_id") or amp.get("id") or amp.get("wdpaid") or amp.get("name")
    if ident:
        return f"{kind}:{ident}"
    return kind


def _poe_phrase_key(poe: dict) -> str:
    name = poe.get("name")
    return f"poe-ahead:{name}" if name else "poe-ahead"


def _bilingual_ici_phrase(ev: dict) -> dict[str, str]:
    return {
        "fr": phrase_for_ici_event(ev, "fr"),
        "en": phrase_for_ici_event(ev, "en"),
    }


def attach_ici_film_phrases(bag: dict | None, *, t: str | None = None) -> dict | None:
    """Copy of the ici bag plus filmPhrases { key: {fr, en} } from film_script.

    Served on GET /ici (no new route). Does not mutate the cached pearl.
    """
    if not isinstance(bag, dict):
        return bag
    out = dict(bag)
    iso = t or _iso_for_ici_bag(out)
    phrases: dict[str, dict[str, str]] = {}

    zee = out.get("zee") if isinstance(out.get("zee"), dict) else None
    if zee and (zee.get("name") or zee.get("mrgid")):
        ev = {"type": "zee-enter", "name": zee.get("name"), "t": iso, "payload": {"zee": zee}}
        pair = _bilingual_ici_phrase(ev)
        if pair["fr"] or pair["en"]:
            phrases["zee-enter"] = pair
        ahead = {"type": "zee-ahead", "name": zee.get("name"), "t": iso, "payload": {"zee": zee}}
        ahead_pair = _bilingual_ici_phrase(ahead)
        if ahead_pair["fr"] or ahead_pair["en"]:
            phrases["zee-ahead"] = ahead_pair

    for amp in out.get("amp") or []:
        if not isinstance(amp, dict):
            continue
        for kind in ("amp-enter", "amp-ahead"):
            ev = {
                "type": kind,
                "name": amp.get("name"),
                "t": iso,
                "whenNm": amp.get("nm"),
                "payload": {"amp": amp, "whenNm": amp.get("nm")},
            }
            pair = _bilingual_ici_phrase(ev)
            if pair["fr"] or pair["en"]:
                phrases[_amp_phrase_key(amp, kind)] = pair

    for poe in out.get("poe") or []:
        if not isinstance(poe, dict) or not poe.get("name"):
            continue
        ev = {
            "type": "poe-ahead",
            "name": poe.get("name"),
            "t": iso,
            "whenNm": poe.get("nm"),
            "payload": {"poe": poe},
        }
        pair = _bilingual_ici_phrase(ev)
        if pair["fr"] or pair["en"]:
            phrases[_poe_phrase_key(poe)] = pair

    out["filmPhrases"] = phrases
    return out


def _departure_iso(stop: dict) -> Optional[str]:
    t = _ms(stop.get("iso"))
    if t is None:
        return None
    return _iso(t + int(float(stop.get("holdHours") or 0) * 3_600_000))


def _stop_from_mark(m: dict) -> dict:
    film = m.get("filmNm") if m.get("filmNm") is not None else m.get("nm")
    return {
        "name": m.get("name") or "",
        "iso": m.get("iso"),
        "filmNm": float(film or 0),
        "nm": float(m["nm"]) if isinstance(m.get("nm"), (int, float)) else float(film or 0),
        "holdHours": float(m.get("holdHours") or 0),
        "lat": m.get("lat") if isinstance(m.get("lat"), (int, float)) else None,
        "lon": m.get("lon") if isinstance(m.get("lon"), (int, float)) else None,
        "kind": m.get("kind"),
        "vehicle": m.get("vehicle"),
    }


def _inject_episode_stops(stops: list[dict], clock: dict | None) -> list[dict]:
    """Halifax aller/retour, Saint-Pierre, Cayenne de retour — isos des marques d'horloge."""
    out = [_stop_from_mark(s) if "iso" in s or "name" in s else dict(s) for s in (stops or [])]

    def has_near(name: str, iso: Any, hours: float = 6.0) -> bool:
        t = _ms(iso)
        if t is None:
            return False
        for s in out:
            if not same_stop(s.get("name") or "", name):
                continue
            st = _ms(s.get("iso"))
            if st is not None and abs(st - t) < hours * 3_600_000:
                return True
        return False

    def add_row(row: dict) -> None:
        name = str(row.get("name") or "").strip()
        if not name or _ms(row.get("iso")) is None:
            return
        if has_near(name, row.get("iso")):
            return
        out.append(_stop_from_mark(row))

    for m in ((clock or {}).get("marks") or []):
        if not isinstance(m, dict):
            continue
        if _air_stop_key(m.get("name") or "") in {"halifax", "saint-pierre", "cayenne"}:
            add_row(m)
    cayenne = next((s for s in out if _air_stop_key(s.get("name") or "") == "cayenne"), None)
    cayenne_name = (cayenne or {}).get("name") or "Cayenne (Guyane)"
    verts = [v for v in ((clock or {}).get("vertices") or []) if isinstance(v, dict)]
    planes = [
        v for v in verts
        if v.get("vehicle") == "plane" and _ms(v.get("iso")) is not None
        and isinstance(v.get("lat"), (int, float)) and isinstance(v.get("lon"), (int, float))
    ]
    planes.sort(key=lambda v: _ms(v["iso"]))
    hub_hit = None
    park_hit = None
    for v in planes:
        d_park = _nm_between(
            (cayenne or {}).get("lat"), (cayenne or {}).get("lon"), v.get("lat"), v.get("lon"),
        )
        if d_park is None and hub_hit is not None:
            d_hub = _nm_between(hub_hit.get("lat"), hub_hit.get("lon"), v.get("lat"), v.get("lon"))
            near_park = d_hub is None or d_hub > 80
        else:
            near_park = d_park is not None and d_park <= 80
        if not near_park and hub_hit is None:
            hub_hit = v
            add_row({
                "name": "Halifax (Nouvelle-Écosse)",
                "iso": v.get("iso"),
                "lat": v.get("lat"),
                "lon": v.get("lon"),
                "filmNm": v.get("filmNm"),
                "nm": v.get("sailNm"),
                "holdHours": 0,
                "kind": "hub",
                "vehicle": "plane",
            })
        elif near_park:
            park_hit = v
            add_row({
                "name": cayenne_name,
                "iso": v.get("iso"),
                "lat": v.get("lat"),
                "lon": v.get("lon"),
                "filmNm": v.get("filmNm"),
                "nm": v.get("sailNm"),
                "holdHours": 0,
                "vehicle": "plane",
            })
    if hub_hit and park_hit:
        hub_t = _ms(hub_hit.get("iso"))
        park_t = _ms(park_hit.get("iso"))
        ret = None
        for v in verts:
            t = _ms(v.get("iso"))
            if t is None or hub_t is None or park_t is None:
                continue
            if t <= hub_t + 6 * 3_600_000 or t >= park_t:
                continue
            d = _nm_between(hub_hit.get("lat"), hub_hit.get("lon"), v.get("lat"), v.get("lon"))
            if d is not None and d <= 80:
                ret = v
        if ret is not None:
            add_row({
                "name": "Halifax (Nouvelle-Écosse)",
                "iso": ret.get("iso"),
                "lat": ret.get("lat"),
                "lon": ret.get("lon"),
                "filmNm": ret.get("filmNm"),
                "nm": ret.get("sailNm"),
                "holdHours": 0,
                "kind": "hub",
            })
    out.sort(key=lambda s: (
        _ms(s.get("iso")) if _ms(s.get("iso")) is not None else 10**15,
        float(s.get("filmNm") if s.get("filmNm") is not None else s.get("nm") or 0),
    ))
    return out


def _annotate_episode_windows(
    windows: list[dict],
    *,
    clock: dict | None,
    marks: list | None,
    moments: list | None,
    lang: str,
) -> list[dict]:
    boat = _side_boat_spoken(clock, marks, moments, lang)
    for w in windows or []:
        if _is_side_window(w):
            w["sideBoat"] = boat
    return windows


def _windows(stops: list[dict], t0: int, t_end: int, clock: dict | None = None) -> list[dict]:
    pts = _inject_episode_stops(
        list(stops or [{"name": "Saint-Maur", "iso": _iso(t0), "filmNm": 0}]),
        clock,
    )
    pts.sort(key=lambda s: (
        _ms(s.get("iso")) if _ms(s.get("iso")) is not None else 10**15,
        float(s.get("filmNm") if s.get("filmNm") is not None else s.get("nm") or 0),
    ))
    out: list[dict] = []

    def pack(
        frm: dict,
        to: dict | None,
        t_a: int,
        t_b: int,
        dest_name: str,
        arrived: bool,
        last: bool,
        mode: str,
        return_ms: Optional[int],
    ) -> dict:
        vehicle = {"air": "plane", "road": "land", "sail": "main"}.get(mode, "main")
        if _is_side_leg(frm.get("name") or "", dest_name):
            vehicle = "side"
        return {
            "id": f"leg-{len(out)}",
            "from": frm,
            "to": to if arrived else None,
            "tA": t_a,
            "tB": t_b,
            "fromName": frm.get("name") or "",
            "toName": dest_name if arrived else "",
            "destName": dest_name,
            "destNm": (to.get("nm") if isinstance((to or {}).get("nm"), (int, float)) else (to or {}).get("filmNm")) if to else None,
            "arrived": arrived,
            "last": last,
            "vehicle": vehicle,
            "mode": mode,
            "clock": clock,
            "returnMs": return_ms,
            "fromLat": frm.get("lat"),
            "fromLon": frm.get("lon"),
            "toLat": (to or {}).get("lat"),
            "toLon": (to or {}).get("lon"),
        }

    stay_idx = 0
    dest_i = 1
    stay_ready_ms: Optional[int] = None
    while dest_i < len(pts):
        frm = pts[stay_idx]
        t_a = _ms(frm.get("iso")) if frm.get("iso") else (t0 if stay_idx == 0 else None)
        if t_a is None:
            dest_i += 1
            continue
        if stay_ready_ms is not None and stay_ready_ms > t_a:
            t_a = stay_ready_ms
        if t_a >= t_end:
            break
        probe = pts[dest_i]
        mode = _classify_window_mode(frm, probe, clock, t_a, _ms(probe.get("iso")) or t_end)
        named_i = dest_i
        last_i = dest_i
        to = pts[named_i]
        last_stop = pts[last_i]
        dest_ms = _ms(to["iso"]) if to else None
        last_ms = _ms(last_stop.get("iso")) if last_stop else dest_ms
        arrived = dest_ms is not None and dest_ms <= t_end
        dest_name = (to.get("name") or "") if to else ""
        raw_b = last_ms if last_ms is not None else t_end
        t_b = min(raw_b if raw_b is not None else t_end, t_end)
        return_ms = None
        if t_b <= t_a:
            # Iso égaux (Saint-Maur forcé à T0, La Rochelle le 15 mai à la même
            # heure) : plancher 1 s — `_iso` tronque à la seconde ; 1 ms
            # donnait tA == tB et filmPlan jetait le chapitre 0.
            t_b = t_a + 1000
        out.append(pack(
            frm, to, t_a, t_b, dest_name, arrived,
            dest_i >= len(pts) - 1 and last_i >= len(pts) - 1,
            mode, return_ms,
        ))
        stay_idx = dest_i
        stay_ready_ms = t_b
        dest_i += 1
        if not to or (dest_ms is not None and dest_ms >= t_end):
            break
    if not out and t_end > t0:
        mode = _classify_window_mode(pts[0], None, clock, t0, t_end)
        out.append(pack(
            pts[0], None, t0, t_end, "", False, True, mode, None,
        ))
        out[0]["fromLat"] = None
        out[0]["fromLon"] = None
    for i, w in enumerate(out):
        if i == 0:
            continue
        prev = out[i - 1]
        if (
            _is_air_window(prev)
            and _air_stop_key(_window_dest_name(prev)) == "cayenne"
            and _air_stop_key(w.get("fromName") or "") == "cayenne"
            and not _is_air_window(w)
        ):
            w["resumeAfterAir"] = True
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


def _air_place_spoken(name: str, lang: str) -> str:
    key = _air_stop_key(name)
    if key == "saint-pierre":
        return "Saint-Pierre and Miquelon" if _en(lang) else "Saint-Pierre-et-Miquelon"
    if key == "cayenne":
        return "Cayenne"
    if key == "halifax":
        return "Halifax"
    stripped = re.sub(r"\s*\([^)]*\)\s*", " ", short_name(name))
    return " ".join(stripped.split())


_SIDE_BOAT_KEYS = ("boat", "boatName", "vessel", "vesselName", "yacht", "ship", "sideBoat")


def _looks_named_side_boat(val: str) -> bool:
    s = " ".join(str(val or "").split())
    if len(s) < 2 or len(s) > 80:
        return False
    if re.search(r"berry|mappemonde|catamaran|second voilier|second sailing", s, re.I):
        return False
    return True


def _side_boat_spoken(
    clock: dict | None,
    marks: list | None,
    moments: list | None,
    lang: str,
) -> str:
    """Nom du second bateau s'il existe dans les données ; sinon « un second voilier »."""
    pool: list[dict] = []
    for src in (marks or []):
        if isinstance(src, dict):
            pool.append(src)
    for src in ((clock or {}).get("marks") or []):
        if isinstance(src, dict):
            pool.append(src)
    for row in moments or []:
        if not isinstance(row, dict):
            continue
        pool.append(_moment_leg(row))
        moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        if isinstance(moment, dict):
            pool.append(moment)
    for src in pool:
        for key in _SIDE_BOAT_KEYS:
            val = src.get(key)
            if isinstance(val, str) and _looks_named_side_boat(val):
                return val.strip()
    return "a second sailing boat" if _en(lang) else "un second voilier"


def _side_opening_sentence(w: dict, *, lang: str, display_t0: str | None = None) -> str:
    """Ouverture Halifax → Saint-Pierre (et retour) à bord du second bateau."""
    en = _en(lang)
    origin = short_name(w.get("fromName") or (w.get("from") or {}).get("name") or "")
    dest = _window_dest_name(w)
    if not origin or not dest:
        return ""
    boat = w.get("sideBoat") or (
        "a second sailing boat" if en else "un second voilier"
    )
    metrics = chapter_metrics(w, w.get("review") if isinstance(w.get("review"), dict) else None)
    nm = _opening_nm_label(metrics.get("legNm"), lang)
    days = spoken_sea_days(metrics.get("daysAtSea"), lang) if metrics.get("daysAtSea") is not None else ""
    stats = ", ".join(x for x in (nm, days) if x)
    dep_ms = _window_depart_ms(w)
    when = ""
    if dep_ms:
        when = day_month(rebase_iso(_iso(int(dep_ms)), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    outbound = _air_stop_key(dest) == "saint-pierre"
    if en:
        verb = "boards" if outbound else "sails again on"
        body = f"in {origin}, the crew {verb} {boat} for {dest}"
        head = f"On {when}, {body}." if when else f"{body[0].upper()}{body[1:]}."
        return f"{head} {stats[0].upper() + stats[1:]}." if stats else head
    verb = "embarque sur" if outbound else "reprend"
    body = f"à {origin}, l'équipage {verb} {boat} pour {dest}"
    if when:
        head = f"Le {when}, {body}."
    else:
        head = f"À {origin}, l'équipage {verb} {boat} pour {dest}."
    if stats:
        return f"{head} {stats[0].upper() + stats[1:]}."
    return head


def _resume_after_episode(w: dict, *, lang: str, display_t0: str | None = None) -> str:
    """Reprise du catamaran à Cayenne — destination = prochaine marque, jamais un lieu inventé."""
    dest = _window_dest_name(w)
    if not dest:
        return ""
    en = _en(lang)
    dep_ms = _window_depart_ms(w)
    when = ""
    if dep_ms:
        when = day_month(rebase_iso(_iso(int(dep_ms)), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    metrics = chapter_metrics(w, w.get("review") if isinstance(w.get("review"), dict) else None)
    nm = _opening_nm_label(metrics.get("legNm"), lang)
    extra = f". {nm}" if nm else ""
    if en:
        body = f"the catamaran puts to sea again, departure for {dest}{extra}"
        return f"On {when}, {body}." if when else f"{body[0].upper()}{body[1:]}."
    body = f"le catamaran reprend la mer, départ vers {dest}{extra}"
    return f"Le {when}, {body}." if when else f"{body[0].upper()}{body[1:]}."


def _air_window_sentence(w: dict, *, lang: str, display_t0: str | None = None) -> str:
    """Une phrase de vol : destination Halifax (pas Saint-Pierre). Attente dite une fois, à l'aller."""
    origin_raw = (w.get("from") or {}).get("name") or w.get("fromName") or ""
    dest_raw = _window_dest_name(w) or w.get("destName") or ""
    origin = _air_place_spoken(origin_raw, lang)
    dest = _air_place_spoken(dest_raw, lang)
    if not origin or not dest:
        return ""
    en = _en(lang)
    wait = _air_stop_key(origin_raw) == "cayenne"
    dep_ms = _window_depart_ms(w) or w.get("departMs") or w.get("tA")
    when = ""
    if dep_ms:
        when = day_month(rebase_iso(_iso(int(dep_ms)), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    if en:
        head = f"The crew flies from {origin} to {dest}"
        if wait:
            head = f"{head}; the catamaran waits at {origin}"
        if when:
            return f"On {when}, {head[0].lower() + head[1:]}."
        return f"{head}."
    head = f"l'équipage s'envole de {origin} pour {dest}"
    if wait:
        head = f"{head} ; le catamaran attend à {origin}"
    if when:
        return f"Le {when}, {head}."
    return f"{head[0].upper() + head[1:]}."


def _air_sentence(w: dict, *, i: int, lang: str, display_t0: str | None = None) -> str:
    return _air_window_sentence(w, lang=lang, display_t0=display_t0)


def _close_position(w: dict, live: dict | None, lang: str) -> str:
    """Où est le bateau aujourd'hui — horloge / live, jamais une position inventée."""
    en = _en(lang)
    live = live or {}
    at_quay = short_name(live.get("atStop") or "")
    if at_quay:
        return f"Today, the boat is at {at_quay}." if en else f"Aujourd’hui, le bateau est à {at_quay}."
    dest = short_name(w.get("destName") or w.get("toName") or "")
    sail = live.get("sailNm") if live.get("sailNm") is not None else live.get("filmNm")
    dest_nm = w.get("destNm")
    if dest and not w.get("arrived") and isinstance(sail, (int, float)) and isinstance(dest_nm, (int, float)) and dest_nm > sail:
        left = _nm_label(dest_nm - sail, lang)
        return (f"Today, the boat is at sea, {left} from {dest}." if en
                else f"Aujourd’hui, le bateau est en mer, à {left} {_de(dest)}.")
    if dest and not w.get("arrived"):
        return f"Today, the boat is at sea, bound for {dest}." if en else f"Aujourd’hui, le bateau est en mer, en route vers {dest}."
    place = short_name(live.get("fromStop") or live.get("name") or "")
    if not place and w.get("arrived"):
        place = short_name(w.get("toName") or "")
    if not place:
        place = short_name(w.get("fromName") or "")
    if not place:
        return ""
    return f"Today, the boat is at {place}." if en else f"Aujourd’hui, le bateau est à {place}."


def _close_sentence(
    w: dict,
    live: dict | None,
    lang: str,
    review: dict | None = None,
    eta: dict | None = None,
) -> str:
    """Fin du film (2–3 phrases) : aujourd'hui, ETA du stock, escales à venir du plan-review."""
    live = live or {}
    first = _close_position(w, live, lang)
    at_quay = short_name(live.get("atStop") or "")
    dest = short_name(w.get("destName") or w.get("toName") or "")
    next_name = _stop_spoken(at_quay or dest)
    arrived = bool(at_quay or w.get("arrived"))
    eta_s = _eta_sentence(next_name, eta, lang) if next_name else ""
    upcoming = upcoming_stop_names(review, next_name, arrived=arrived)
    up_s = _upcoming_sentence(upcoming, lang)
    raw = " ".join(bit for bit in (first, eta_s, up_s) if bit)
    if not raw:
        return ""
    sail = live.get("sailNm") if live.get("sailNm") is not None else live.get("filmNm")
    dest_nm = w.get("destNm")
    left = None
    if isinstance(sail, (int, float)) and isinstance(dest_nm, (int, float)) and dest_nm > sail:
        left = dest_nm - sail
    eta_raw = eta_payload_for_stop(eta, next_name) if next_name else None
    facts = _facts_with_rounded({
        "live": live,
        "destNm": dest_nm,
        "sailNm": sail,
        "leftNm": left,
        "leftLabel": _nm_label(left, lang) if left is not None else "",
        "eta": eta,
        "etaStop": eta_raw,
        "upcoming": upcoming,
        "review": review_plan_stats(review),
        "first": first,
    })
    return _honest_bookend(raw, facts, lang)


def _harbor_differs_from_city(harbor: str, dest_name: str) -> bool:
    """True si le port / la marina a un nom distinct de la ville d'escale."""
    if not (harbor or "").strip() or not (dest_name or "").strip():
        return False
    city = _stop_spoken(dest_name)
    core = re.sub(r"^(le |la |l['’]|the )", "", harbor.strip(), flags=re.I)
    core = re.sub(
        r"^(port |marina |harbour |harbor )(d['’]|de |of )?",
        "",
        core,
        flags=re.I,
    )
    core = re.sub(r" marina$", "", core, flags=re.I).strip()
    if not core:
        return False
    if same_stop(core, city):
        return False
    city_cf = city.casefold()
    core_cf = core.casefold()
    if city_cf and (city_cf in core_cf or core_cf in city_cf):
        return False
    return True


def _harbor_spoken(name: str, dest: str, kind: str, lang: str) -> str:
    """« le port d'Ajaccio » / « la marina Les Minimes ». Titre anglais → port de l'escale."""
    en = _en(lang)
    raw = (name or "").strip()
    if looks_english_title(raw) or not raw or _GENERIC_HARBOR_RE.search(raw):
        raw = (dest or "").strip()
        kind = "port"
    if not raw:
        return ""
    if re.match(r"^(le |la |l['’]|the )(port|marina|harbour|harbor)\b", raw, re.I):
        return raw
    if re.match(r"^(port|marina|harbour|harbor)\b", raw, re.I):
        return raw if not en else raw
    marina = kind == "marina" or bool(re.search(r"marina|minimes", raw, re.I))
    if marina:
        return f"the {raw} marina" if en else f"la marina {raw}"
    return f"the port of {raw}" if en else f"le port {_de(raw)}"


def _moored_phrase(harbor: str, lang: str) -> str:
    if not harbor:
        return ""
    if _en(lang):
        return f"moored at {harbor}"
    if harbor.startswith("le "):
        return f"amarré au {harbor[3:]}"
    if harbor.startswith("la "):
        return f"amarré à {harbor}"
    if harbor.startswith("l’") or harbor.startswith("l'"):
        return f"amarré à {harbor}"
    return f"amarré à {harbor}"


def _hold_phrase(days: int, chapter_i: int, lang: str) -> str:
    """Durée dite une fois, formulations qui tournent — jamais « 3 jours à quai »."""
    if not days:
        return ""
    spoken = _spoken_days_word(int(days), lang)
    if _en(lang):
        variants = (
            f"a {spoken} stopover",
            f"a stay of {spoken}",
            f"{spoken} at the harbour",
            f"{spoken} alongside",
        )
    else:
        variants = (
            f"{spoken} d'escale",
            f"escale de {spoken}",
            f"{spoken} au port",
            f"on reste {spoken}",
        )
    return variants[int(chapter_i) % len(variants)]


def _item_place(item: dict) -> tuple[str, str]:
    kind = str(item.get("kind") or "")
    if item.get("title") or item.get("fact"):
        name = change_place_name(item)
        if name:
            return name, kind or "port"
    return short_name(item.get("name") or ""), kind or "port"


def _arrival_harbor(items: list | None, dest: dict | None, lang: str) -> str:
    """Marina / port le plus proche de l'escale ; sinon le port d'arrivée nommé."""
    dest = dest or {}
    dest_name = short_name(dest.get("name") or "")
    dest_lat, dest_lon = dest.get("lat"), dest.get("lon")
    scored: list[tuple[tuple, str, str]] = []
    for item in items or []:
        kind = str(item.get("kind") or "")
        if kind not in {"marina", "port", "poe"}:
            continue
        name, k = _item_place(item)
        if not name or looks_english_title(name):
            continue
        dist = _nm_between(dest_lat, dest_lon, item.get("lat"), item.get("lon"))
        near = bool(dest_name) and (
            dest_name.casefold() in name.casefold() or name.casefold() in dest_name.casefold()
        )
        if not near and (dist is None or dist > 25.0):
            continue
        t = item.get("tMs") or _ms(item.get("t")) or 0
        scored.append(((0 if near else 1, dist if dist is not None else 999.0, -int(t)), name, k))
    if scored:
        scored.sort(key=lambda row: row[0])
        return _harbor_spoken(scored[0][1], dest_name, scored[0][2], lang)
    if dest_name:
        return _harbor_spoken(dest_name, dest_name, "port", lang)
    return ""


def _compact_sea_opening(
    w: dict,
    *,
    lang: str,
    display_t0: str | None = None,
    review: dict | None = None,
    include_date: bool = True,
) -> str:
    """Ouverture 2:30 : une phrase — date, destination, milles, jours. Sans redite."""
    dest_name = _stop_spoken(_window_dest_name(w))
    if not dest_name:
        return ""
    en = _en(lang)
    metrics = chapter_metrics(w, review)
    nm_val = metrics.get("legNm")
    days_val = metrics.get("daysAtSea")
    nm = _opening_nm_label(nm_val, lang) if nm_val is not None else ""
    days = spoken_sea_days(days_val, lang) if days_val is not None else ""
    dep_ms = _window_depart_ms(w)
    when = ""
    if include_date and dep_ms:
        when = day_month(rebase_iso(_iso(dep_ms), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    stats = ", ".join(x for x in (nm, days) if x)
    if en:
        if when and stats:
            raw = f"On {when}, heading for {dest_name}: {stats}."
        elif when:
            raw = f"On {when}, heading for {dest_name}."
        elif stats:
            raw = f"Heading for {dest_name}: {stats}."
        else:
            raw = f"Heading for {dest_name}."
    elif when and stats:
        raw = f"Le {when}, cap sur {dest_name} : {stats}."
    elif when:
        raw = f"Le {when}, cap sur {dest_name}."
    elif stats:
        raw = f"Cap sur {dest_name} : {stats}."
    else:
        raw = f"Cap sur {dest_name}."
    facts = _facts_with_rounded({
        "iso": _iso(dep_ms) if dep_ms else None,
        "when": when,
        "dest": dest_name,
        "legNm": int(round(float(nm_val))) if isinstance(nm_val, (int, float)) else None,
        "nmLabel": nm,
        "daysAtSea": days_val,
        "daysLabel": days,
    })
    return _honest_bookend(raw, facts, lang)


def _opening_sentence(
    w: dict,
    *,
    i: int,
    lang: str,
    display_t0: str | None = None,
    heading_deg: Any = None,
    review: dict | None = None,
    n: int = 0,
    include_date: bool = True,
    compact: bool = False,
) -> str:
    """Ouverture d'étape : date, port, cap, dest, milles, jours, vitesse — gabarit § 4.

    `compact` (2:30) : une phrase, sans quitte / nœuds / longue traversée.
    """
    dest_name = _window_dest_name(w)
    if _is_air_window(w):
        return _air_window_sentence(w, lang=lang, display_t0=display_t0)
    if _is_side_window(w):
        return _side_opening_sentence(w, lang=lang, display_t0=display_t0)
    if w.get("resumeAfterAir"):
        return _resume_after_episode(w, lang=lang, display_t0=display_t0)
    if not dest_name:
        return ""
    if compact and not _is_road_window(w):
        return _compact_sea_opening(
            w, lang=lang, display_t0=display_t0, review=review, include_date=include_date,
        )
    en = _en(lang)
    origin = short_name(
        w.get("fromName") or (w.get("from") or {}).get("name") or ""
    )
    metrics = chapter_metrics(w, review)
    shape = chapter_shape(w, i, n or 0, metrics)
    dep_ms = _window_depart_ms(w)
    when = ""
    if include_date and dep_ms:
        when = day_month(rebase_iso(_iso(dep_ms), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    cap = ""
    if not _is_road_window(w):
        cap = heading_phrase(heading_deg if heading_deg is not None else w.get("headingDeg"), lang)
    dest_for = dest_name
    if shape == "long":
        dest_for = f"the long crossing to {dest_name}" if en else f"la longue traversée vers {dest_name}"
    boat = "Berry-Mappemonde"
    if _is_road_window(w):
        km = ""
        gap = metrics.get("legNm")
        if gap and not compact:
            km = _km_label(gap, lang)
        if en:
            body = f"{boat} leaves {origin} by road for {dest_name}" if origin else f"{boat} takes the road to {dest_name}"
            if km:
                body = f"{body}. {km[0].upper()}{km[1:]}" if km else body
        else:
            body = (
                f"{boat} quitte {origin} par la route pour {dest_name}"
                if origin else
                f"{boat} prend la route pour {dest_name}"
            )
            if km:
                body = f"{body}. {km[0].upper()}{km[1:]}"
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body[0].upper()}{body[1:]}."

    stats: list[str] = []
    nm = _opening_nm_label(metrics.get("legNm"), lang)
    days = spoken_sea_days(metrics.get("daysAtSea"), lang) if metrics.get("daysAtSea") is not None else ""
    kn = metrics.get("plannedKnots")
    kn_s = ""
    if isinstance(kn, (int, float)) and not isinstance(kn, bool):
        kn_i = int(round(float(kn)))
        kn_s = f"{kn_i} knots on average" if en else f"{kn_i} nœuds de moyenne"
    if nm:
        stats.append(nm)
    if days:
        stats.append(days)
    if kn_s:
        stats.append(kn_s if not days else (f"at {kn_s}" if en else f"à {kn_s}"))
    extra = ""
    if stats:
        # Point, pas « : » : split_short_sentences reboucle sinon sur le même texte.
        extra = ". " + ", ".join(stats)

    hop = ""
    last = ""
    if shape == "hop":
        hop = "from island to island, " if en else "d'île en île, "
    if shape == "last":
        last = "for the last stage, " if en else "pour la dernière étape, "

    if en:
        mid = f", {cap}" if cap else ""
        leave = f"{hop}{last}{boat} leaves {origin}{mid} for {dest_for}{extra}" if origin else f"{hop}{last}{boat} sails for {dest_for}{extra}"
        if when:
            return f"On {when}, {leave}."
        return f"{leave[0].upper()}{leave[1:]}."
    mid = f", {cap}" if cap else ""
    leave = (
        f"{hop}{last}{boat} quitte {origin}{mid} pour {dest_for}{extra}"
        if origin else
        f"{hop}{last}{boat} met le cap sur {dest_for}{extra}"
    )
    if when:
        return f"Le {when}, {leave}."
    return f"{leave[0].upper()}{leave[1:]}."


def _depart_towards(
    w: dict, *, i: int, lang: str, display_t0: str | None = None,
    heading_deg: Any = None,
    review: dict | None = None,
    n: int = 0,
    include_date: bool = True,
    compact: bool = False,
) -> str:
    return _opening_sentence(
        w, i=i, lang=lang, display_t0=display_t0, heading_deg=heading_deg,
        review=review, n=n, include_date=include_date, compact=compact,
    )


def _arrival_sentence(
    stop: dict | None,
    lang: str,
    display_t0: str | None = None,
    clock: dict | None = None,
    harbor: str = "",
    chapter_i: int = 0,
    compact: bool = False,
) -> str:
    if not stop or not stop.get("name") or _ms(stop.get("iso")) is None:
        return ""
    en = _en(lang)
    if compact:
        when = day_month(rebase_iso(stop["iso"], OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
        dest = _stop_spoken(stop.get("name") or "")
        extra = ""
        if harbor and _harbor_differs_from_city(harbor, dest):
            extra = f", at {harbor}" if en else f", à {harbor}"
        if en:
            raw = f"Arrival on {when}{extra}." if when else (f"Arrival{extra}." if extra else "")
        else:
            raw = f"Arrivée le {when}{extra}." if when else (f"Arrivée{extra}." if extra else "")
        if not raw:
            return ""
        facts = _facts_with_rounded({
            "iso": stop.get("iso"),
            "when": when,
            "dest": dest,
            "harbor": harbor,
        })
        return _honest_bookend(raw, facts, lang)
    name = short_name(stop["name"])
    when = day_month(rebase_iso(stop["iso"], OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    quay = _days(_quay_hours_for_arrival(stop, clock))
    moored = _moored_phrase(harbor, lang)
    hold = _hold_phrase(quay, chapter_i, lang)
    if en:
        head = f"Arrival at {name} on {when}" if when else f"Arrival at {name}"
        if moored:
            head = f"{head}, {moored}"
        if hold:
            head = f"{head}. {hold[0].upper()}{hold[1:]}"
        return f"{head}."
    head = f"Arrivée à {name} le {when}" if when else f"Arrivée à {name}"
    if moored:
        head = f"{head}, {moored}"
    if hold:
        head = f"{head}. {hold[0].upper()}{hold[1:]}"
    return f"{head}."


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


def _compose(windows: list[dict], buckets: list[list[dict]], *, lang: str, sea_name: str, start_name: str, live: dict | None, display_t0: str | None = None, review: dict | None = None, eta: dict | None = None, seconds: int = 0) -> list[dict]:
    chapters: list[dict] = []
    cited: set[str] = set()
    compact = _film_compact_template(seconds)
    dist = ""
    if live:
        dist = _nm_label(live.get("sailNm") if live.get("sailNm") is not None else live.get("filmNm"), lang)

    def push_arrival(
        bits: list[str],
        dest: dict | None,
        clock: dict | None = None,
        harbor: str = "",
        chapter_i: int = 0,
    ) -> None:
        key = norm_stop((dest or {}).get("name") or "")
        sentence = _arrival_sentence(
            dest, lang, display_t0, clock=clock, harbor=harbor, chapter_i=chapter_i,
            compact=compact,
        )
        if not sentence or not key or key in cited:
            return
        bits.append(sentence)
        cited.add(key)

    for i, w in enumerate(windows):
        bits: list[str] = []
        placed: list[dict] = []
        anchored: list[tuple[str, Optional[int]]] = []
        dest = _chapter_dest(w)
        dest_name = _window_dest_name(w)
        arrived = bool(w.get("arrived")) if "arrived" in w else bool(dest)
        depart_ms = _window_depart_ms(w) or 0

        def finish_chapter() -> None:
            thinned = thin_chapter_dates(bits, lang)
            if len(thinned) == len(bits) and len(anchored) == len(bits):
                anchored[:] = [_retarget_anchor(anchored[j], thinned[j]) for j in range(len(thinned))]
            bits[:] = thinned
            text = speak_film_text(re.sub(r"\s{2,}", " ", " ".join(bits)).strip(), lang)
            if film_opens:
                head = " ".join(film_opens)
                if head and head not in text:
                    text = speak_film_text(f"{head} {text}".strip(), lang)
                    for sent in reversed(film_opens):
                        anchored.insert(0, (sent, w["tA"], {"role": "depart"}))
            if i == len(windows) - 1:
                close = _close_sentence(w, live, lang, review=review, eta=eta)
                if close and close not in text:
                    text = speak_film_text(f"{text} {close}".strip(), lang)
                    anchored.append((close, w["tB"]))
            chapters.append({
                "id": w["id"],
                "tA": _iso(w["tA"]),
                "tB": _iso(w["tB"]),
                "text": text,
                "anchors": chapter_anchors(text, anchored, w["tA"], w["tB"], lang),
                "events": placed,
                "fromName": w.get("fromName") or "",
                "toName": w.get("toName") or "",
                "fromLat": w.get("fromLat"),
                "fromLon": w.get("fromLon"),
                "toLat": w.get("toLat"),
                "toLon": w.get("toLon"),
            })

        film_opens: list[str] = []
        skip_depart = False
        if i == 0:
            film_opens = _film_open_sentences(
                start_name=start_name, sea_name=sea_name, lang=lang,
                display_t0=display_t0, review=review, compact=compact,
            )
            skip_depart = _is_road_window(w) and bool(film_opens)
        if _is_air_window(w):
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                review=review, n=len(windows), compact=compact,
            )
            if head:
                bits.append(head)
                anchored.append((head, depart_ms or w["tA"], {"role": "depart"}))
            finish_chapter()
            continue

        def speak_ev(ev: dict) -> None:
            if ev.get("kind") == "stop" and ev.get("role") not in {"depart", "today"}:
                return
            if ev.get("role") in {"depart", "today"}:
                return
            if ev.get("kind") == "marina":
                return
            ev_name = short_name(ev.get("name") or "")
            if ev.get("kind") in {"approche", "stop"} and dest_name and ev_name and (
                same_stop(ev_name, dest_name) or dest_name.casefold() in ev_name.casefold()
            ):
                return
            if looks_english_title(ev_name):
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

        sci_keep_id = ""
        sci_here = [ev for ev in buckets[i] if ev.get("kind") == "sci" and station_spoken_label(ev, lang)]
        if sci_here:
            def _sci_nm(ev: dict) -> float:
                raw = _fact_num(ev, "nm")
                if raw is None:
                    raw = _fact_num(ev.get("entry") or {}, "nm")
                return float(raw) if raw is not None else 999.0
            sci_here.sort(key=lambda ev: (_sci_nm(ev), ev.get("tMs") or 0))
            sci_keep_id = str(sci_here[0].get("id") or "")

        if not skip_depart:
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                heading_deg=_leg_heading_deg(None, depart_ms, clock=w.get("clock")),
                review=review, n=len(windows), include_date=i != 0, compact=compact,
            )
            if head:
                bits.append(head)
                anchored.append((head, depart_ms or w["tA"], {"role": "depart"}))
        spoken_evs = (
            _drop_guiana_equator_changes(buckets[i])
            if _is_saint_pierre_depart(w) else buckets[i]
        )
        for ev in spoken_evs:
            if ev.get("kind") == "sci" and str(ev.get("id") or "") != sci_keep_id:
                continue
            speak_ev(ev)
        _append_review_sentences(bits, review, w, lang, anchored)
        if arrived:
            harbor = _arrival_harbor(buckets[i], dest, lang)
            before = len(bits)
            push_arrival(bits, dest, clock=w.get("clock"), harbor=harbor, chapter_i=i)
            if len(bits) > before:
                dest_place = short_name((dest or {}).get("name") or "")
                anchored.append((bits[-1], w["tB"], {"role": "arrive", "place": dest_place, "kind": "escale"}))
        finish_chapter()
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
            "lat": item.get("lat") if isinstance(item.get("lat"), (int, float)) else None,
            "lon": item.get("lon") if isinstance(item.get("lon"), (int, float)) else None,
        }
        if not change_is_speakable(extra):
            continue
        key = (kind, norm_stop(title), fact)
        if key in seen:
            continue
        seen.add(key)
        extras.append(extra)
    return extras


def _ici_dc2_extras(row: dict) -> list[dict]:
    """Mouillage / port d'entrée déjà dans le sac ici — copie, jamais inventée."""
    pair = _row_latlon(row)
    if not pair:
        return []
    try:
        from official_store import ici_bag_near  # noqa: PLC0415
        bag = ici_bag_near(pair[0], pair[1])
    except Exception:
        return []
    if not isinstance(bag, dict):
        return []
    extras: list[dict] = []
    nearby = bag.get("nearby") if isinstance(bag.get("nearby"), dict) else {}
    for i, anc in enumerate(nearby.get("anchorages") or []):
        if not isinstance(anc, dict):
            continue
        name = str(anc.get("name") or "").strip()
        if not name or name.casefold() in GENERIC_ANCHORAGE_NAMES:
            continue
        extra = {
            "kind": "anchorage",
            "title": name,
            "fact": name,
            "score": 2,
            "id": f"ici:anchorage:{row.get('seq')}:{i}",
            "nm": anc.get("nm") if isinstance(anc.get("nm"), (int, float)) else None,
        }
        if change_is_speakable(extra):
            extras.append(extra)
            break
    for i, poe in enumerate(bag.get("poe") or []):
        if not isinstance(poe, dict):
            continue
        name = str(poe.get("name") or "").strip()
        if not name or NO_DATA_RE.search(name):
            continue
        extra = {
            "kind": "poe",
            "title": name,
            "fact": name,
            "score": 2,
            "id": f"ici:poe:{row.get('seq')}:{i}",
            "nm": poe.get("nm") if isinstance(poe.get("nm"), (int, float)) else None,
        }
        if change_is_speakable(extra):
            extras.append(extra)
            break
    extras.extend(_ici_dc3_extras(row, bag))
    return extras


def _ici_dc3_extras(row: dict, bag: dict | None = None) -> list[dict]:
    """Balise / câble / profondeur / piraterie / satellite du sac ici — copie."""
    if bag is None:
        pair = _row_latlon(row)
        if not pair:
            return []
        try:
            from official_store import ici_bag_near  # noqa: PLC0415
            bag = ici_bag_near(pair[0], pair[1])
        except Exception:
            return []
    extras: list[dict] = []
    for extra in _dc3_from_ici_bag(bag, seq=row.get("seq")):
        extra = {
            **extra,
            "id": extra.get("id") or f"ici:{extra.get('kind')}:{row.get('seq')}",
        }
        if change_is_speakable(extra):
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


def _starting_zee_from_moments(
    moments: list[dict], t_a: int, t_b: int, first: bool,
) -> Optional[dict]:
    """ZEE déjà occupée au départ de la jambe (pas un enter) — Gascogne / Pertuis.

    Calculée depuis le premier moment de mer de la fenêtre, jamais une constante."""
    for row in moments:
        if not isinstance(row, dict) or _moment_is_air(row):
            continue
        t = _change_t(row)
        if t is None:
            continue
        # Y compris tA : l'appareillage de la jambe (non-première) est à tA,
        # alors que flatten laisse ce moment au chapitre précédent.
        if t < t_a or t > t_b:
            continue
        if first and t >= t_b:
            continue
        moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        here = moment.get("here") if isinstance(moment.get("here"), dict) else {}
        zee = here.get("zee") if isinstance(here.get("zee"), dict) else {}
        name = str(zee.get("name") or "").strip()
        if not name or re.search(r"haute mer|high seas", name, re.I):
            continue
        pair = _row_latlon(row)
        extra = {"lat": pair[0], "lon": pair[1]} if pair else {}
        return {
            "id": f"zee-start:{row.get('seq')}:{zee.get('mrgid') or name}",
            "kind": "zee-enter",
            "score": 2,
            "title": name,
            "fact": name,
            "t": row.get("t"),
            "tMs": t,
            **extra,
        }
    return None


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
        raw = list(row.get("changes") or []) + _moment_extra_changes(row) + _ici_dc2_extras(row)
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
            pair = _row_latlon(row)
            if pair and row_change.get("lat") is None:
                row_change["lat"], row_change["lon"] = pair
            if not change_is_speakable(row_change):
                continue
            key = (
                str(change.get("kind")),
                norm_stop(change_place_name(row_change) or title),
                fact,
                _zee_basin_from_change(row_change) if str(change.get("kind") or "") == "zee-enter" else "",
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(row_change)
    start_zee = _starting_zee_from_moments(moments, t_a, t_b, first)
    if start_zee:
        key = (
            "zee-enter",
            norm_stop(change_place_name(start_zee) or start_zee.get("title") or ""),
            str(start_zee.get("fact") or ""),
            _zee_basin_from_change(start_zee),
        )
        if key not in seen:
            seen.add(key)
            out.append(start_zee)
    out.sort(key=lambda c: (c["tMs"], str(c.get("id") or "")))
    return out


def _group_changes(changes: list[dict], span_ms: int, clock: dict | None = None) -> list[dict]:
    by_kind: dict[str, list[dict]] = {}
    for change in changes:
        by_kind.setdefault(str(change.get("kind") or ""), []).append(change)
    out: list[dict] = []
    grouped_ids: set[str] = set()
    for kind, group in by_kind.items():
        if len(group) < 3:
            continue
        if kind in {
            "alert-on", "marina", "port", "amp", "project", "zee-enter", "coast",
            "climo", "station", "buoy", "poe", "anchorage",
            "aton", "cable", "depth", "piracy", "satellite",
        }:
            # Pas de « 10 alertes », « N ZEE » ni « N stations » : une station qualifiée, jamais un comptage (RG5).
            continue
        # RG14 : dater au membre le plus proche du bateau ; sinon éclater (RG2 a déjà réduit).
        spoken_ms = group[0].get("tMs")
        member = _closest_member_to_boat(group, clock, spoken_ms)
        if member is None:
            continue
        title = fact = f"{len(group)} {kind}"
        out.append({
            "id": f"group:{kind}:{member.get('id')}",
            "kind": kind,
            "score": max(int(g.get("score") or 0) for g in group),
            "title": title,
            "fact": fact,
            "t": member.get("t"),
            "tMs": member.get("tMs"),
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
    if kind == "zee-enter":
        # Identité + bassin : les eaux françaises de Gascogne/Pertuis ne sont
        # pas celles de Corse/Sardaigne ni du Pacifique (RC35). Sans coordonnées,
        # le titre brut reste le repli (RC26 : parenthèse = territoire).
        raw = re.sub(r"\s+", " ", str(change.get("title") or change.get("fact") or "")).strip()
        if not raw:
            return ""
        ident = toponyms.identity_key(raw) or raw.casefold()
        basin = _zee_basin_from_change(change)
        return f"zee:{ident}:{basin}" if basin else f"zee:{ident}"
    # Un groupe côte / île porte sa géographie : « l'Andalousie — Cartagena »
    # et « l'Andalousie — Almería » sont le même site (RC26).
    geo = change.get("geo") if isinstance(change.get("geo"), dict) else None
    geo_name = str((geo or {}).get("fr") or (geo or {}).get("en") or "").strip()
    name = norm_stop(geo_name) if geo_name else norm_stop(change_place_name(change))
    if not name:
        return ""
    # RC26 : dédoublonnage par SITE — « Lilleau-des-Niges » et « Lilleau-des-Niges
    # - Zone de Protection » partagent le préfixe significatif (avant « - », « — », « ( »).
    name = re.split(r"\s+[-—–]\s+|\s*\(", name, maxsplit=1)[0].strip() or name
    if kind in {"escale", "approche"}:
        return f"{kind}:{name}"
    return name


def _usable_changes(changes: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    rows: list[dict] = []
    for change in sorted(changes, key=lambda c: (c.get("tMs") or 0, str(c.get("id") or ""))):
        if not change_is_speakable(change) or not change_on_route(change):
            continue
        cid = str(change.get("id") or "")
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        rows.append(change)
    # Même site dit une fois : le nom le plus court gagne (RC26), à l'instant
    # du premier croisement.
    best: dict[str, dict] = {}
    out: list[dict] = []
    for change in rows:
        key = _place_dedup_key(change)
        if not key:
            out.append(change)
            continue
        prev = best.get(key)
        if prev is None:
            best[key] = change
            out.append(change)
            continue
        if _is_amp_change(change) or _is_amp_change(prev):
            rank = {"enter": 0, "nearby": 1, "exit": 2}
            prev_r = rank.get(_amp_speak_event(prev), 9)
            cur_r = rank.get(_amp_speak_event(change), 9)
            if cur_r < prev_r:
                best[key] = change
                out[out.index(prev)] = change
                continue
            if cur_r > prev_r:
                continue
        if len(change_place_name(change)) < len(change_place_name(prev)):
            merged = {
                **change,
                "t": prev.get("t") or change.get("t"),
                "tMs": prev.get("tMs") if prev.get("tMs") is not None else change.get("tMs"),
            }
            best[key] = merged
            out[out.index(prev)] = merged
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return out


def film_free_item_target(span_ms: int) -> int:
    """RC26 : budget d'items du chapitre intégral, proportionnel à la durée —
    1 item par 1,5 jour de mer, plancher 4, plafond 16."""
    days = max(0.0, float(span_ms or 0) / 86_400_000.0)
    return min(FILM_FREE_ITEMS_MAX, max(FILM_CHAPTER_MAX_CHANGES, math.ceil(days / FILM_FREE_ITEM_DAYS)))


# Types encore absents du chapitre, dans l'ordre du gabarit (FILM_DISCOURS § 4).
# L'AMP (8 au stock) passe avant le projet (129) : le type rare ne perd pas
# toujours la fenêtre contre le type abondant.
_DIVERSITY_ORDER = ("climo", "station", "amp", "project", "alert-on", "coast", "zee-enter")


def _diversity_kind(change: dict) -> str:
    kind = str(change.get("kind") or "")
    if kind == "alert-on" and _is_amp_change(change):
        return "amp"
    return kind


def _diversity_bonus(change: dict) -> int:
    """Îles et détroits (Sardaigne, Gibraltar…) : jalons rares, jamais sacrifiés
    en premier (RC19)."""
    geo = change.get("geo") if isinstance(change.get("geo"), dict) else {}
    return 1 if (geo.get("kind") in {"island", "strait"}) else 0


def _pick_diverse(cands: list[dict], picked: list[dict]) -> Optional[dict]:
    """Le meilleur item d'une fenêtre : types encore absents d'abord (climato,
    station, projet, AMP, alerte, côte/eaux), pas deux fois le même type
    d'affilée quand un autre existe, puis score et priorité."""
    if not cands:
        return None
    seen = {_diversity_kind(p) for p in picked}
    last = _diversity_kind(picked[-1]) if picked else ""
    has_other = any(_diversity_kind(c) != last for c in cands)

    def key(c: dict):
        k = _diversity_kind(c)
        absent = 0 if k not in seen else 1
        rank = _DIVERSITY_ORDER.index(k) if (absent == 0 and k in _DIVERSITY_ORDER) else len(_DIVERSITY_ORDER)
        repeat = 1 if (k == last and has_other) else 0
        # RC19 : une île / un détroit ne cède jamais sa place aux eaux du jour —
        # le jalon rare passe AVANT la pénalité de répétition.
        return (
            0 if _is_spine_route_item(c) else 1,
            absent, rank, -_diversity_bonus(c), repeat,
            -int(c.get("score") or 0),
            CHANGE_PRIORITY.get(str(c.get("kind") or ""), 9),
            c.get("tMs") or 0, str(c.get("id") or ""),
        )

    return min(cands, key=key)


def _pin_spine_waters(picked: list[dict], pool: list[dict]) -> list[dict]:
    """RC35 : ES/PT/MA/FR/Gibraltar restent dans le chapitre — un Argo ou une
    AMP de trop cède sa place, la première AMP (Lilleau) est gardée."""
    have = {k for k in (_place_dedup_key(c) for c in picked) if k}
    missing: list[dict] = []
    for c in pool:
        if not _is_spine_route_item(c):
            continue
        k = _place_dedup_key(c)
        if k and k in have:
            continue
        missing.append(c)
        if k:
            have.add(k)
    if not missing:
        return picked
    extras = [
        c for c in picked
        if _diversity_kind(c) in {"amp", "station"} and not _is_spine_route_item(c)
    ]
    drop_ids = {id(c) for c in extras[1:]}
    out = [c for c in picked if id(c) not in drop_ids]
    keep_extra_ids = {id(c) for c in extras[:1]}
    for c in missing:
        if len(out) < FILM_FREE_ITEMS_MAX:
            out.append(c)
            continue
        replaced = False
        for i in range(len(out) - 1, -1, -1):
            if id(out[i]) in keep_extra_ids:
                continue
            if _diversity_kind(out[i]) in {"amp", "station"} and not _is_spine_route_item(out[i]):
                out[i] = c
                replaced = True
                break
        if not replaced:
            continue
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return out


def _spread_free_changes(
    cands: list[dict], t_a: int, t_b: int, *, depart_ms: Optional[int] = None,
    spare: Optional[list[dict]] = None,
) -> list[dict]:
    """RC26 : sélection par fenêtres de temps, pas par type puis date.

    - la période à quai [tA, départ] ne garde qu'UN item de proximité
      (« à cinq milles ») en plus de l'ouverture ;
    - la mer [départ, tB] est découpée en autant de fenêtres que d'items du
      budget (1 / 1,5 jour, plancher 4) : le meilleur item par fenêtre
      (score puis diversité) ; les items non retenus d'une fenêtre comblent
      une fenêtre vide voisine ; `spare` (stations, projets… hors dose) ne
      sert QUE dans les fenêtres restées vides — le Pacifique ne se tait pas ;
    - le tout est plafonné à FILM_FREE_ITEMS_MAX (16).
    """
    rows = sorted(cands, key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    if not rows and not spare:
        return []
    dock_end = int(depart_ms) if depart_ms and int(t_a or 0) < int(depart_ms) < int(t_b or 0) else int(t_a or 0)
    dock = [c for c in rows if (c.get("tMs") or 0) <= dock_end]
    sea = [c for c in rows if (c.get("tMs") or 0) > dock_end]
    picked: list[dict] = []
    # Au quai : au plus deux phrases après l'ouverture (recette RC26), dont UNE
    # seule de proximité (« à cinq milles » : AMP, alerte, projet) — plus jamais six.
    proximity = {"amp", "alert-on", "project", "marina"}
    if dock:
        first = _pick_diverse(dock, picked)
        if first is not None:
            picked.append(first)
            first_prox = str(first.get("kind") or "") in proximity
            other = [
                c for c in dock
                if c is not first and (str(c.get("kind") or "") in proximity) != first_prox
            ]
            if not other:
                # Pas d'autre famille au quai : un 2e item de proximité d'un
                # AUTRE type (le projet ne fait pas taire l'AMP voisine).
                other = [
                    c for c in dock
                    if c is not first and _diversity_kind(c) != _diversity_kind(first)
                ]
            second = _pick_diverse(other, picked)
            if second is not None:
                picked.append(second)
    span = max(1, int(t_b or 0) - dock_end)
    n = max(1, film_free_item_target(span) - len(picked))
    width = span / n
    buckets: list[list[dict]] = [[] for _ in range(n)]
    taken = [0] * n   # au plus 2 items par fenêtre : un amas d'un jour ne mange pas la jambe
    for c in sea:
        i = min(n - 1, int(((c.get("tMs") or 0) - dock_end) / width))
        buckets[max(0, i)].append(c)
    filled: list[Optional[dict]] = [None] * n

    def _take(j: int, into: int) -> Optional[dict]:
        choice = _pick_diverse(buckets[j], picked)
        if choice is None:
            return None
        buckets[j] = [c for c in buckets[j] if c is not choice]
        taken[j] += 1
        filled[into] = choice
        picked.append(choice)
        return choice

    for i in range(n):
        if buckets[i]:
            _take(i, i)
    # Fenêtres vides ← d'abord la réserve DE LA MÊME fenêtre (stations, projets,
    # AMP, climato au-delà de la dose : mieux vaut un flotteur Argo que dix jours
    # muets — et son instant tombe vraiment dans le trou), puis les items non
    # retenus des fenêtres voisines.
    spare_buckets: list[list[dict]] = [[] for _ in range(n)]
    for c in sorted(spare or [], key=lambda c: (c.get("tMs") or 0, str(c.get("id") or ""))):
        t = c.get("tMs") or 0
        if t <= dock_end:
            continue
        i = min(n - 1, int((t - dock_end) / width))
        spare_buckets[max(0, i)].append(c)
    for i in range(n):
        if filled[i] is not None or not spare_buckets[i]:
            continue
        choice = _pick_diverse(spare_buckets[i], picked)
        if choice is not None:
            filled[i] = choice
            taken[i] += 1
            picked.append(choice)
            spare_buckets[i] = [c for c in spare_buckets[i] if c is not choice]
    for i in range(n):
        if filled[i] is not None:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < n and buckets[j] and taken[j] < 2:
                if _take(j, i) is not None:
                    break
    # Capacité restante (jusqu'au plafond) : au plus un item de plus par fenêtre —
    # Sardaigne, Gibraltar et les eaux d'un même jour survivent, sans refaire l'amas.
    while len(picked) < FILM_FREE_ITEMS_MAX:
        open_buckets = [j for j in range(n) if buckets[j] and taken[j] < 2]
        if not open_buckets:
            break
        j = min(open_buckets, key=lambda k: (taken[k], k))
        choice = _pick_diverse(buckets[j], picked)
        if choice is None:
            # RC30 : cette fenêtre n'a que des doublons de site — elle ne doit
            # pas faire taire les fenêtres suivantes (la Seychelloise attend).
            buckets[j] = []
            continue
        buckets[j] = [c for c in buckets[j] if c is not choice]
        taken[j] += 1
        picked.append(choice)
    # RC30 : la réserve complète jusqu'au plafond (même quota ≤ 2 par fenêtre) —
    # le flotteur Argo unique par jambe ne laisse plus la traversée muette.
    while len(picked) < FILM_FREE_ITEMS_MAX:
        open_spare = [j for j in range(n) if spare_buckets[j] and taken[j] < 2]
        if not open_spare:
            break
        j = min(open_spare, key=lambda k: (taken[k], k))
        choice = _pick_diverse(spare_buckets[j], picked)
        if choice is None:
            spare_buckets[j] = []
            continue
        spare_buckets[j] = [c for c in spare_buckets[j] if c is not choice]
        taken[j] += 1
        picked.append(choice)
    # Quand TOUT le chapitre tient sous le plafond, on ne jette rien : le
    # quota par fenêtre protège contre l'amas, pas contre un stock clairsemé.
    # Jamais deux fois le même site (l'Andalousie d'hier ne revient pas demain).
    leftovers = [c for b in buckets for c in b]
    if leftovers and len(picked) + len(leftovers) <= FILM_FREE_ITEMS_MAX:
        keys = {k for k in (_place_dedup_key(p) for p in picked) if k}
        for c in leftovers:
            k = _place_dedup_key(c)
            if k and k in keys:
                continue
            picked.append(c)
            if k:
                keys.add(k)
    # Dédoublonnage final par site (RC26) : les jalons quotidiens d'une même
    # côte (l'Andalousie du 21, l'Andalousie du 22) ne se disent qu'une fois —
    # le nom le plus court gagne, au temps du premier croisement.
    by_site: dict[str, dict] = {}
    out: list[dict] = []
    for c in sorted(picked, key=lambda c: (c.get("tMs") or 0, str(c.get("id") or ""))):
        k = _place_dedup_key(c)
        if not k:
            out.append(c)
            continue
        prev = by_site.get(k)
        if prev is None:
            by_site[k] = c
            out.append(c)
            continue
        if _is_amp_change(c) or _is_amp_change(prev):
            rank = {"enter": 0, "nearby": 1, "exit": 2}
            prev_r = rank.get(_amp_speak_event(prev), 9)
            cur_r = rank.get(_amp_speak_event(c), 9)
            if cur_r < prev_r:
                out[out.index(prev)] = c
                by_site[k] = c
                continue
            if cur_r > prev_r:
                continue
        if len(str(c.get("title") or "")) < len(str(prev.get("title") or "")):
            merged = {**c, "t": prev.get("t"), "tMs": prev.get("tMs")}
            out[out.index(prev)] = merged
            by_site[k] = merged
    out.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return _pin_spine_waters(out, rows)


def _would_speak(change: dict) -> bool:
    """Un item ne prend une fenêtre que s'il donnera vraiment une phrase
    (RC26) : mêmes gardes que speak_change — escale d'avion, titre anglais,
    phrase vide ou interdite."""
    kind = str(change.get("kind") or "")
    place = change_place_name(change) or short_name(str(change.get("title") or ""))
    geo = change.get("geo") if isinstance(change.get("geo"), dict) else None
    if geo and (geo.get("fr") or geo.get("en")):
        place = geo.get("fr") or geo.get("en") or place
    if looks_english_title(place) and kind in {
        "port", "approche", "culture", "project", "amp", "marina",
        "poe", "anchorage", "aton",
    }:
        return False
    sentence = change_sentence(change, "fr").strip()
    return bool(sentence) and not film_has_forbidden(sentence)


def _is_argo_station(change: dict) -> bool:
    from ici_engine import science_type_key  # noqa: PLC0415
    return (
        str(change.get("kind") or "") == "station"
        and science_type_key(_station_item(change)) == "argo"
    )


def _limit_argo_once(rows: list[dict]) -> list[dict]:
    """RC30 : au plus UN flotteur Argo par chapitre — le premier croisé ;
    jamais six « un flotteur Argo » anonymes (transcription du 14 oct.)."""
    out: list[dict] = []
    seen = False
    for c in rows:
        if _is_argo_station(c):
            if seen:
                continue
            seen = True
        out.append(c)
    return out


def _cap_argo_candidates(pool: list[dict], spare: list[dict]) -> tuple[list[dict], list[dict]]:
    """RC30 : un seul flotteur Argo candidat AVANT la répartition par fenêtres.
    On garde celui du passage le plus SILENCIEUX (le plus loin, dans le temps,
    de tout autre stock racontable) : c'est lui qui remplissait le trou de la
    traversée que les Argo surnuméraires comblaient avant — la jambe ne perd
    pas sa densité (RC26)."""
    argos = [c for c in pool if _is_argo_station(c)] + [c for c in spare if _is_argo_station(c)]
    if len(argos) <= 1:
        return pool, spare
    others = [
        c.get("tMs") or 0
        for c in pool + (spare or [])
        if not _is_argo_station(c) and c.get("tMs")
    ]

    def quietness(c: dict) -> float:
        t = c.get("tMs") or 0
        return min((abs(t - o) for o in others), default=0.0)

    best = max(argos, key=lambda c: (
        quietness(c),
        -(change_distance_nm(c) if change_distance_nm(c) is not None else 999.0),
        -(c.get("tMs") or 0),
    ))
    return (
        [c for c in pool if not _is_argo_station(c) or c is best],
        [c for c in spare if not _is_argo_station(c) or c is best],
    )


def select_chapter_changes(
    changes: list[dict], t_a: int, t_b: int, *, budget: bool = True, tier: Optional[int] = None,
    clock: dict | None = None, depart_ms: Optional[int] = None,
) -> list[dict]:
    usable = _usable_changes(changes)
    span = (t_b or 0) - (t_a or 0)
    zee = dose_zee_changes(usable, span)
    coast = dose_coast_changes(usable, span)
    amp = dose_amp_changes(usable, span)
    proj = dose_project_changes(usable, span)
    climo = dose_climo_changes(usable, span)
    stations = dose_station_changes(usable, span, t_a=t_a, t_b=t_b)
    extras = _tier_route_extras(zee, coast, amp, proj, climo, stations, tier=tier)
    rest_src = [
        c for c in usable
        if str(c.get("kind") or "") not in ROUTE_NAMING_KINDS
        and not _is_coast_source(c)
        and not _is_amp_change(c)
        and str(c.get("kind") or "") not in ({"project", "climo", "station"} | DC_DOSAGE_KINDS)
        and _tier_allows_kind(str(c.get("kind") or ""), tier)
    ]
    if not budget:
        # RC26 : fenêtres de temps sur toute la jambe — plus de « type puis date ».
        pool_route = extras if tier is not None else zee + coast + amp + proj + climo + stations
        keep = [c for c in rest_src if str(c.get("kind") or "") in {"escale", "approche"}]
        marinas = [c for c in rest_src if str(c.get("kind") or "") == "marina"]
        if marinas:
            # La marina de l'escale : la dernière à portée (elle nomme le port, pas une phrase).
            keep.append(max(marinas, key=lambda c: (c.get("tMs") or 0, str(c.get("id") or ""))))
        pool = [
            c for c in pool_route + [
                x for x in rest_src
                if str(x.get("kind") or "") not in {"escale", "approche", "marina"}
            ]
            if _would_speak(c)
        ]
        in_pool = {id(c) for c in pool}
        # Une 2e station au-delà de la dose (RG5) ne se justifie que sur une
        # longue jambe (le Pacifique muet) — jamais sur une traversée courte.
        spare_station_ok = span > 5 * 86_400_000
        spare = [
            c for c in usable
            if id(c) not in in_pool
            and (str(c.get("kind") or "") in {"station", "project", "climo"} or _is_amp_change(c))
            and (str(c.get("kind") or "") != "station"
                 or (spare_station_ok and station_spoken_label(c, "fr")))
            and not (span >= SHORT_CROSSING_MS and _is_buoy_change(c))
            and _would_speak(c)
        ]
        pool, spare = _cap_argo_candidates(pool, spare)
        picked_free = _spread_free_changes(pool, t_a, t_b, depart_ms=depart_ms, spare=spare)
        dc2 = dose_dc2_leg_changes(usable, span)
        dc3 = dose_dc3_leg_changes(usable, span)
        out = picked_free + keep + dc2 + dc3  # escale, approche, marina ; DC hors fenêtres
        seen_ids: set[str] = set()
        uniq: list[dict] = []
        for c in out:
            cid = str(c.get("id") or "")
            if cid and cid in seen_ids:
                continue
            if cid:
                seen_ids.add(cid)
            uniq.append(c)
        uniq.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
        return _limit_argo_once(uniq)
    grouped = _group_changes(rest_src, span, clock=clock)
    must = [c for c in grouped if c.get("kind") in {"escale", "approche"}]
    rest = [c for c in grouped if c.get("kind") not in {"escale", "approche"}]
    rest.sort(key=lambda c: (
        -int(c.get("score") or 0), CHANGE_PRIORITY.get(str(c.get("kind") or ""), 9), c.get("tMs") or 0,
    ))
    arrival = next((c for c in must if c.get("kind") == "escale"), None)
    approach = next((c for c in must if c.get("kind") == "approche"), None)
    alert = next((c for c in rest if c.get("kind") == "alert-on"), None)
    color_skip = {"marina", "zee-enter", "coast"}
    if tier is not None and tier <= FILM_TIER_SHORT:
        color_skip = color_skip | {"station", "climo", "culture", "port"} | DC_DOSAGE_KINDS
    color = next((c for c in rest if c.get("kind") in COLOR_KINDS and c.get("kind") not in color_skip), None)
    # La marina de l'escale (« cultures d'escale », 26 sept.) : la dernière marina à portée de la fenêtre.
    marina = next((c for c in sorted(rest, key=lambda c: -(c.get("tMs") or 0)) if c.get("kind") == "marina"), None)
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
    add(color)
    add(marina)
    add(approach)
    add(alert)
    for item in must + rest:
        add(item)
    seen = {str(x.get("id") or "") for x in picked}
    for item in extras:
        cid = str(item.get("id") or "")
        if cid and cid in seen:
            continue
        picked.append(item)
        if cid:
            seen.add(cid)
    picked.sort(key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")))
    return _limit_argo_once(picked)


def _de(name: str) -> str:
    """« de Papeete » mais « d’Ajaccio ». Un nom déjà « de Fineveke » ne devient pas « de de »."""
    n = (name or "").strip()
    if not n:
        return "de"
    if re.match(r"^(de |d['’]|du |des )", n, re.I):
        return n
    if re.match(r"^[aeiouyâàäéèêëîïôöûùüœh]", n, re.I):
        return f"d’{n}"
    return f"de {n}"


def _group_sentence(change: dict, lang: str) -> str:
    """Plus aucun comptage à la voix (ZEE : RG2 ; stations : RG5)."""
    del change, lang
    return ""


_HS_VALUE_RE = re.compile(r"Hs\s+(\d+(?:[.,]\d+)?)\s*m", re.I)
_SEA_TITLE_RE = re.compile(r"^(mer|sea)$", re.I)


def sea_alert_hs_m(change: dict) -> Optional[float]:
    """Hs observée (pas le seuil) : champ structuré, sinon le premier « Hs N m » du fait."""
    n = _fact_num(change, "hs", "maxHs")
    if n is not None:
        return n
    blob = f"{change.get('fact') or ''} {change.get('title') or ''}"
    found = _HS_VALUE_RE.search(blob)
    if not found:
        return None
    try:
        return float(found.group(1).replace(",", "."))
    except ValueError:
        return None


def is_sea_hs_alert(change: dict) -> bool:
    """Alerte mer (kind sea / alert-on « Hs … m ≥ ») — pas une AMP."""
    if not isinstance(change, dict):
        return False
    kind = str(change.get("kind") or "")
    title = str(change.get("title") or "")
    fact = str(change.get("fact") or "")
    if kind == "alert-on" and alert_is_amp(change):
        return False
    if kind == "sea":
        return True
    if kind == "wx" and str(change.get("event") or "") == "sea":
        return True
    if kind == "alert-on" and (_SEA_TITLE_RE.match(title.strip()) or _HS_VALUE_RE.search(fact + " " + title)):
        return True
    return False


def sea_alert_sentence(change: dict, lang: str = "fr") -> str:
    """« mer formée (3 m) » / « Hs 3 m » — jamais ≥, jamais le seuil répété."""
    en = _en(lang)
    when = day_month(change.get("t"), lang)
    hs = sea_alert_hs_m(change)
    hs_s = _plain(hs, 0) if hs is not None else ""
    if hs_s:
        body = f"Hs {hs_s} m" if en else f"mer formée ({hs_s} m)"
    else:
        body = "Hs" if en else "mer formée"
    if when:
        return f"On {when}, {body}." if en else f"Le {when}, {body}."
    return f"{body[0].upper()}{body[1:]}."


def change_sentence(change: dict, lang: str = "fr") -> str:
    en = _en(lang)
    if str(change.get("id") or "").startswith("group:"):
        return _group_sentence(change, lang)
    when = day_month(change.get("t"), lang)
    title = short_name(change.get("title") or "")
    fact = expand_spoken_units(str(change.get("fact") or "").rstrip("."), lang)
    kind = change.get("kind")
    name = title.replace("Arrivée à ", "").replace("Arrival at ", "").strip()
    if is_sea_hs_alert(change):
        return sea_alert_sentence(change, lang)
    if kind == "escale":
        if when:
            return f"Arrival at {name} on {when}." if en else f"Arrivée à {name} le {when}."
        return f"Arrival at {name}." if en else f"Arrivée à {name}."
    if kind == "approche":
        if looks_english_title(title):
            return ""
        if when:
            return (
                f"On {when}, the approach is by {title}."
                if en else
                f"Le {when}, l'approche se fait par {title}."
            )
        return f"The approach is by {title}." if en else f"L'approche se fait par {title}."
    if kind == "alert-on":
        from ici_engine import is_fishing_amp  # noqa: PLC0415
        if is_fishing_amp({"name": title, "title": title, "fact": fact}):
            return ""
        if alert_is_amp(change):
            amp = alert_amp_name(change)
            if not amp:
                return ""
            return _amp_film_sentence(amp, change, lang, when)
        body = IUCN_RE.sub("", fact or title).strip(" ;:")
        if not body or NO_DATA_RE.search(body):
            return ""
        return f"On {when}, {body}." if en else f"Le {when}, {body}."
    if kind == "zee-enter" and re.search(r"ports? d['’]entr|formalit", title, re.I):
        name = extract_named(title, fact, "port")
        if not name:
            return ""
        return f"On {when}, off {name}." if en else f"Le {when}, devant {name}."
    if kind == "zee-enter":
        members = change.get("members")
        if isinstance(members, list) and len(members) > 1:
            # RC26 : « les eaux françaises, puis celles de Montserrat » — jamais
            # un adjectif orphelin ni une minuscule en tête de nom propre.
            body = zee_group_waters(members, lang)
            if not body:
                return ""
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        raw = title or fact
        waters = zee_waters_label(raw, lang)
        if not waters:
            return ""
        return f"On {when}, {waters}." if en else f"Le {when}, {waters}."
    if kind == "coast":
        return coast_sentence(change, lang)
    if kind == "station":
        spoken = station_spoken_label(change, lang)
        if not spoken:
            return ""
        if when:
            return f"On {when}, {spoken}." if en else f"Le {when}, {spoken}."
        return f"{spoken[0].upper()}{spoken[1:]}."
    if kind == "buoy":
        spoken = station_spoken_label({**change, "kind": "station"}, lang)
        if not spoken:
            return ""
        if when:
            return f"On {when}, {spoken}." if en else f"Le {when}, {spoken}."
        return f"{spoken[0].upper()}{spoken[1:]}."
    if kind == "poe":
        name = _poe_place_name(change)
        if not name or looks_english_title(name):
            return ""
        body = (
            f"entry formalities go through {name}"
            if en else
            f"les formalités d'entrée passent par {name}"
        )
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body[0].upper()}{body[1:]}."
    if kind == "anchorage":
        name = _anchorage_name(change)
        if not name or looks_english_title(name):
            return ""
        if when:
            return (
                f"On {when}, anchorage {name}."
                if en else
                f"Le {when}, mouillage {name}."
            )
        return f"Anchorage {name}." if en else f"Mouillage {name}."
    if kind == "aton":
        name = _aton_name(change)
        if not name or looks_english_title(name):
            return ""
        body = f"beacon {name}" if en else f"balise {name}"
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body[0].upper()}{body[1:]}."
    if kind == "cable":
        name = _cable_name(change)
        if not name:
            return ""
        body = f"cable {name}" if en else f"câble {name}"
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body[0].upper()}{body[1:]}."
    if kind == "depth":
        metres = _depth_m(change)
        if metres is None:
            return ""
        if abs(metres - round(metres)) < 0.05:
            spoken = str(int(round(metres)))
        else:
            spoken = f"{metres:.1f}".rstrip("0").rstrip(".")
            if not en:
                spoken = spoken.replace(".", ",")
        body = f"Depth: {spoken} m" if en else f"Profondeur : {spoken} m"
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body}."
    if kind == "piracy":
        name = _piracy_name(change)
        if not name:
            return ""
        level = _piracy_level(change)
        source = str(change.get("source") or "").strip()
        label = "Piracy" if en else "Piraterie"
        body = f"{label} — {name}"
        if level:
            body += f" · {level}"
        if source:
            body += f" · {source}"
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return f"{body}."
    if kind == "satellite":
        caption = _satellite_caption(change)
        if not caption:
            return ""
        body = caption.rstrip(".")
        if when:
            return f"On {when}, {body}." if en else f"Le {when}, {body}."
        return caption if caption.endswith((".", "!", "?", "…")) else f"{caption}."
    if kind == "amp":
        from ici_engine import is_fishing_amp, spoken_amp_name  # noqa: PLC0415
        if is_fishing_amp({"name": title, "title": title, "fact": fact}):
            return ""
        name = spoken_amp_name(change_place_name(change) or title) or change_place_name(change)
        if not name or looks_english_title(name):
            return ""
        if _amp_speak_event(change) == "exit":
            return ""
        return _amp_film_sentence(name, change, lang, when)
    if kind == "project":
        name = change_place_name(change)
        if not name or looks_english_title(name):
            return ""
        nm = change_distance_nm(change)
        dist = spoken_distance(nm, lang) if nm is not None else ""
        if dist:
            return (
                f"On {when}, {dist} away, project {name}."
                if en else
                f"Le {when}, à {dist}, le projet {name}."
            )
        return f"On {when}, project {name}." if en else f"Le {when}, le projet {name}."
    if kind == "climo":
        return climo_sentence(change, lang)
    if kind == "marina":
        return ""
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
        if not name or looks_english_title(name):
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


def _sentence_has_date(text: str, lang: str) -> bool:
    return bool((_DATE_EN_RE if _en(lang) else _DATE_FR_RE).search(text or ""))


def _parse_spoken_date(text: str, lang: str) -> Optional[datetime]:
    rx = _DATE_EN_RE if _en(lang) else _DATE_FR_RE
    found = rx.search(text or "")
    if not found:
        return None
    day_s, month_s = found.group(1), found.group(2)
    rest = found.group(0)
    year_m = re.search(r"(\d{4})$", rest)
    year = int(year_m.group(1)) if year_m else 2026
    try:
        day = 1 if str(day_s).lower() == "1er" else int(day_s)
    except (TypeError, ValueError):
        return None
    months = MONTHS["en" if _en(lang) else "fr"]
    key = str(month_s).casefold()
    idx = next((i for i, m in enumerate(months) if m.casefold() == key), -1)
    if idx < 0:
        return None
    try:
        return datetime(year, idx + 1, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_arrival_sentence(text: str) -> bool:
    return bool(re.match(r"^(Arrivée à|Arrivée le|Arrival at|Arrival on)\b", text or "", re.I))


_DEPART_SENT_RE = re.compile(
    r"\bquitte\b|\bquitté\b|\bdépart vers\b|\bleaves\b|\bleft\b|\bdeparture for\b|"
    r"\bmet le cap\b|\bsails for\b|\bprend la route\b|\btakes the road\b|\bby road\b|"
    r"\bcap sur\b|\bheading for\b",
    re.I,
)
_DURATION_SENT_RE = re.compile(
    r"d['’]escale|escale de |au port\b|on reste |stopover|at the harbour|"
    r"alongside|stay of |jours? à quai|days? (?:at |in )?port",
    re.I,
)
# Coordonnées de lieux nommés (faits géographiques, pas un voyage inventé) — recette RG14.
_NAMED_PLACE_COORDS = {
    "gibraltar": (36.14, -5.35),
    "tanger": (35.78, -5.81),
    "tangier": (35.78, -5.81),
    "algeciras": (36.13, -5.45),
    "ceuta": (35.89, -5.32),
}


def _is_depart_sentence(text: str) -> bool:
    return bool(_DEPART_SENT_RE.search(text or ""))


def _is_duration_sentence(text: str) -> bool:
    return bool(_DURATION_SENT_RE.search(text or ""))


def _voice_lookahead_idx(idx: int, floor: int = 0) -> int:
    return max(int(floor), int(idx) - FILM_VOICE_LOOKAHEAD_CHARS)


def _first_word_idx(sentence: str, origin: int) -> int:
    found = re.search(r"\S", sentence or "")
    return origin + (found.start() if found else 0)


def _last_word_idx(sentence: str, origin: int) -> int:
    found = re.search(r"(\S+)[.\s]*$", sentence or "")
    if not found:
        return origin + max(0, len(sentence or "") - 1)
    return origin + found.start(1)


def _end_idx(sentence: str, origin: int) -> int:
    body = (sentence or "").rstrip()
    return origin + max(0, len(body) - 1)


def _find_ci(hay: str, needle: str) -> int:
    if not hay or not needle:
        return -1
    return hay.casefold().find(needle.casefold())


def _place_idx_in_sentence(sentence: str, origin: int, place: str = "") -> int:
    """Index du nom du lieu dans la phrase, sinon le milieu."""
    sent = sentence or ""
    # Détroit / golfe : le nom géographique, pas le premier port (Tanger ≠ Gibraltar).
    geo = re.search(
        r"(?:détroit de |strait of |golfe de |bay of )([A-ZÀ-Ÿ][\w'’\-]+)",
        sent,
        re.I,
    )
    if geo:
        return origin + geo.start(1)
    candidates: list[str] = []
    if place:
        candidates.append(place)
        tail = place.split()[-1] if place.split() else ""
        if tail and tail.casefold() != place.casefold():
            candidates.append(tail)
    for cand in candidates:
        at = _find_ci(sent, cand)
        if at >= 0:
            return origin + at
    geo = re.search(
        r"(?:eaux |waters of |port d['’]?|marina |quitte |"
        r"leaves |longe |skirts |arrivée à |arrival at )"
        r"([A-ZÀ-Ÿ][\w'’\-]+(?:\s+[A-ZÀ-Ÿ][\w'’\-]+)?)",
        sent,
        re.I,
    )
    if geo:
        return origin + geo.start(1)
    named = re.search(r"\b([A-ZÀ-Ÿ][\w'’\-]{3,}(?:\s+[A-ZÀ-Ÿ][\w'’\-]+)?)\b", sent)
    if named and not re.match(r"^(Le|La|Les|The|On|Puis|Then|Berry|Arrivée|Arrival)$", named.group(1)):
        return origin + named.start(1)
    return origin + max(0, len(sent) // 2)


def _locate_spoken(text: str, spoken: str, start: int = 0) -> int:
    needle = spoken[:28] if len(spoken) > 28 else spoken
    idx = text.find(needle, start) if needle else -1
    if idx < 0 and len(needle) > 12:
        idx = text.find(needle[:12], start)
    if idx < 0 and len(spoken) > 24:
        idx = text.find(spoken[-24:], start)
    return idx


def _unpack_anchored(item) -> dict:
    if isinstance(item, dict):
        return {
            "sentence": str(item.get("sentence") or item.get("text") or ""),
            "t": item.get("t") if item.get("t") is not None else item.get("tMs"),
            "t_end": item.get("t_end") if item.get("t_end") is not None else item.get("tEnd"),
            "place": str(item.get("place") or ""),
            "kind": str(item.get("kind") or ""),
            "role": str(item.get("role") or ""),
        }
    sentence = str(item[0]) if item else ""
    t_ms = item[1] if len(item) > 1 else None
    extra = item[2] if len(item) > 2 else {}
    if not isinstance(extra, dict):
        extra = {"role": extra} if extra else {}
    return {
        "sentence": sentence,
        "t": t_ms,
        "t_end": extra.get("t_end") if extra.get("t_end") is not None else extra.get("tEnd"),
        "place": str(extra.get("place") or ""),
        "kind": str(extra.get("kind") or ""),
        "role": str(extra.get("role") or ""),
    }


def _retarget_anchor(item, sentence: str):
    if isinstance(item, dict):
        return {**item, "sentence": sentence}
    t_ms = item[1] if len(item) > 1 else None
    extra = item[2] if len(item) > 2 else None
    if extra is None:
        return (sentence, t_ms)
    return (sentence, t_ms, extra)


def _bits_offsets(bits: list[str]) -> list[int]:
    """Index du premier caractère de chaque phrase dans « " ".join(bits) »."""
    out: list[int] = []
    acc = 0
    for k, b in enumerate(bits):
        if k:
            acc += 1
        out.append(acc)
        acc += len(b)
    return out


_SPINE_SPOKEN_RE = (
    re.compile(r"eaux françaises|French waters", re.I),
    re.compile(r"Gascogne|Biscay", re.I),
    re.compile(r"eaux espagnoles|Spanish waters", re.I),
    re.compile(r"eaux portugaises|Portuguese waters", re.I),
    re.compile(r"Gibraltar", re.I),
    re.compile(r"eaux marocaines|Moroccan waters", re.I),
)


def _apply_spine_first_order(bits: list[str], order: list[int]) -> list[int]:
    """RC48 : premières mentions FR, Gascogne, ES, PT, Gibraltar, MA dans cet ordre."""
    seq = list(order)

    def first_pos(pat: re.Pattern) -> Optional[int]:
        for pos, i in enumerate(seq):
            if 0 <= i < len(bits) and pat.search(bits[i] or ""):
                return pos
        return None

    for _ in range(len(_SPINE_SPOKEN_RE)):
        ranks = [(r, first_pos(p)) for r, p in enumerate(_SPINE_SPOKEN_RE)]
        ranks = [(r, p) for r, p in ranks if p is not None]
        swapped = False
        for a, b in zip(ranks, ranks[1:]):
            if a[1] > b[1]:
                seq[a[1]], seq[b[1]] = seq[b[1]], seq[a[1]]
                swapped = True
                break
        if not swapped:
            break
    return seq


def _is_lr_ajaccio_chapter(from_name: str = "", to_name: str = "") -> bool:
    return bool(
        re.search(r"rochelle", from_name or "", re.I)
        and re.search(r"ajaccio", to_name or "", re.I)
    )


def _order_chapter_sentences(
    bits: list[str],
    anchored: list,
    placed: list[dict],
    *,
    from_name: str = "",
    to_name: str = "",
) -> None:
    """RC30 : les phrases d'un chapitre se disent dans l'ordre STRICT du temps
    du voyage — tri stable par instant d'ancre, l'ouverture (role depart) reste
    en tête, l'arrivée (role arrive) en queue. Les connecteurs de date sont
    recalculés APRÈS, par thin_chapter_dates. Les charIdx des bulles (`placed`)
    suivent leurs phrases. Ne fait rien si bits et ancres ne sont pas alignés
    (chemin sans ancres). RC48 : la colonne d'eaux LR→Ajaccio (premières
    mentions) reste FR → Gascogne → ES → PT → Gibraltar → MA."""
    if len(bits) != len(anchored) or len(bits) < 3:
        return
    keys: list[tuple[int, int, int]] = []
    last_t = 0
    for i, item in enumerate(anchored):
        row = _unpack_anchored(item)
        role = (row.get("role") or "").strip().lower()
        cls = 0 if role == "depart" else (2 if role == "arrive" else 1)
        t = row.get("t")
        if t is not None:
            last_t = int(t)
        keys.append((cls, last_t if cls == 1 else 0, i))
    timed = sorted(range(len(bits)), key=lambda i: keys[i])
    order = (
        _apply_spine_first_order(bits, timed)
        if _is_lr_ajaccio_chapter(from_name, to_name)
        else timed
    )
    if order == list(range(len(bits))):
        return
    old_off = _bits_offsets(bits)
    new_bits = [bits[i] for i in order]
    new_off = _bits_offsets(new_bits)
    remap = {old_off[i]: new_off[pos] for pos, i in enumerate(order)}
    for bubble in placed:
        old_idx = bubble.get("charIdx")
        if isinstance(old_idx, int) and old_idx in remap:
            bubble["charIdx"] = remap[old_idx]
    anchored[:] = [anchored[i] for i in order]
    bits[:] = new_bits


def _named_place_coords(name: str, marks: list | None = None) -> Optional[tuple[float, float]]:
    raw = str(name or "").strip()
    if not raw:
        return None
    key = norm_stop(raw)
    for mark in marks or []:
        if not isinstance(mark, dict):
            continue
        if key and key in norm_stop(mark.get("name") or ""):
            try:
                return float(mark["lat"]), float(mark["lon"])
            except (TypeError, ValueError, KeyError):
                continue
    folded = raw.casefold()
    for token, pair in _NAMED_PLACE_COORDS.items():
        if token in folded or token in key:
            return pair
    return None


def _clock_latlon_at(clock: dict | None, t_ms: Optional[int]) -> Optional[tuple[float, float]]:
    if clock is None or t_ms is None:
        return None
    t0 = _ms(clock.get("t0"))
    best: Optional[tuple[float, float]] = None
    best_dt: Optional[int] = None
    for v in clock.get("vertices") or []:
        if not isinstance(v, dict):
            continue
        t = _ms(v.get("iso"))
        if t is None and t0 is not None and v.get("tHours") is not None:
            try:
                t = t0 + int(float(v["tHours"]) * 3_600_000)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        try:
            lat, lon = float(v["lat"]), float(v["lon"])
        except (TypeError, ValueError, KeyError):
            continue
        dt = abs(int(t) - int(t_ms))
        if best_dt is None or dt < best_dt:
            best, best_dt = (lat, lon), dt
    return best


def _clock_time_near_place(
    clock: dict | None,
    place: str,
    t_a: Optional[int],
    t_b: Optional[int],
    marks: list | None = None,
) -> Optional[int]:
    coords = _named_place_coords(place, marks or (clock or {}).get("marks"))
    if coords is None or clock is None:
        return None
    plat, plon = coords
    t0 = _ms(clock.get("t0"))
    best_t: Optional[int] = None
    best_d: Optional[float] = None
    for v in clock.get("vertices") or []:
        if not isinstance(v, dict):
            continue
        t = _ms(v.get("iso"))
        if t is None and t0 is not None and v.get("tHours") is not None:
            try:
                t = t0 + int(float(v["tHours"]) * 3_600_000)
            except (TypeError, ValueError):
                t = None
        if t is None:
            continue
        if t_a is not None and t < t_a:
            continue
        if t_b is not None and t > t_b:
            continue
        d = _nm_between(plat, plon, v.get("lat"), v.get("lon"))
        if d is None:
            continue
        if best_d is None or d < best_d:
            best_d, best_t = d, t
    return best_t


def _closest_member_to_boat(
    group: list[dict],
    clock: dict | None,
    spoken_ms: Optional[int],
) -> Optional[dict]:
    """Membre le plus proche du bateau à l'instant où le groupe est dit ; sinon None (éclater)."""
    if not group:
        return None
    boat = _clock_latlon_at(clock, spoken_ms if spoken_ms is not None else group[0].get("tMs"))
    if boat is None:
        return None
    best = None
    best_d: Optional[float] = None
    for member in group:
        d = _nm_between(boat[0], boat[1], member.get("lat"), member.get("lon"))
        if d is None:
            continue
        if best_d is None or d < best_d:
            best, best_d = member, d
    return best


def _relative_lead(prev: Optional[datetime], cur: Optional[datetime], lang: str) -> str:
    if prev and cur:
        try:
            if (cur.date() - prev.date()) == timedelta(days=1):
                return "The next day, " if _en(lang) else "Le lendemain, "
        except (TypeError, ValueError):
            pass
    return "Then, " if _en(lang) else "Puis, "


def _strip_lead_date(text: str, lang: str) -> str:
    rx = _LEAD_DATE_EN_RE if _en(lang) else _LEAD_DATE_FR_RE
    return rx.sub("", text or "", count=1)


def thin_chapter_dates(sentences: list[str], lang: str = "fr") -> list[str]:
    """Au plus une date calendaire toutes les deux phrases. L'arrivée garde sa date."""
    out = [scrub_spoken(s) for s in sentences]
    dated = [_sentence_has_date(s, lang) for s in out]
    i = 1
    while i < len(out):
        if dated[i] and dated[i - 1]:
            if _is_arrival_sentence(out[i]):
                # RC30 : la phrase i-1 perd SA date — « Le lendemain » se mesure
                # contre la dernière date dite AVANT elle, pas contre l'arrivée.
                prev_j = next((j for j in range(i - 2, -1, -1) if dated[j]), None)
                prev_d = _parse_spoken_date(out[prev_j], lang) if prev_j is not None else None
                cur_d = _parse_spoken_date(out[i - 1], lang)
                body = _strip_lead_date(out[i - 1], lang)
                if body == out[i - 1]:
                    body = (_DATE_EN_RE if _en(lang) else _DATE_FR_RE).sub("", out[i - 1], count=1)
                    body = re.sub(r"\s{2,}", " ", body).replace("Le ,", "Puis,").strip()
                else:
                    body = _relative_lead(prev_d, cur_d, lang) + body[0].lower() + body[1:] if body else out[i - 1]
                out[i - 1] = body[0].upper() + body[1:] if body else out[i - 1]
                dated[i - 1] = False
            else:
                prev_d = _parse_spoken_date(out[i - 1], lang)
                cur_d = _parse_spoken_date(out[i], lang)
                body = _strip_lead_date(out[i], lang)
                if body != out[i]:
                    lead = _relative_lead(prev_d, cur_d, lang)
                    out[i] = lead + (body[0].lower() + body[1:] if body else "")
                    if out[i] and not out[i].endswith((".", "!", "?", "…")):
                        pass
                dated[i] = False
        i += 1
    # Deuxième passe : densité globale ≤ 1 date / 2 phrases (ouverture et arrivée gardées).
    while True:
        dated = [_sentence_has_date(s, lang) for s in out]
        if date_density_ok(" ".join(out), lang):
            break
        drop = next(
            (
                j for j in range(1, len(out) - 1)
                if dated[j] and not _is_arrival_sentence(out[j])
            ),
            None,
        )
        if drop is None:
            break
        body = _strip_lead_date(out[drop], lang)
        if body == out[drop]:
            break
        lead = "Puis, " if not _en(lang) else "Then, "
        out[drop] = lead + (body[0].lower() + body[1:] if body else "")
    kept = [s for s in out if s]
    if _en(lang):
        return [fix_en_waters_casing(s) for s in kept]
    return kept


def date_density_ok(text: str, lang: str = "fr") -> bool:
    sents = _sentences(text)
    if not sents:
        return True
    n_dates = sum(1 for s in sents if _sentence_has_date(s, lang))
    return n_dates * 2 <= len(sents) + 1


_AMP_OR_PROJECT_SENT = re.compile(
    r"aire marine|marine protected area|le projet |project ",
    re.I,
)
_WATERS_SENT = re.compile(
    r"eaux |waters|haute mer|high seas",
    re.I,
)
# P1/P2 : ouverture, escales, cap — pas les côtes / climo / stations, pas les eaux en trop.
_CORE_KEEP_SENT = re.compile(
    r"arriv|Berry-Mappemonde|quitte|leaves |jours de mer|days at sea|"
    r"nœuds de moyenne|knots on average|amarré|moored|d'escale|stopover|"
    r"départ|departure|left |quitté|approche|approaching|avion|flies|flight|"
    r"envole|par la route|by road|attend à|waits at|aujourd|today|"
    r"expédition|expedition|escales|stops|destination|entre le |between |"
    r"à venir|still to come|le plan compte|the plan has|"
    r"cap au |cap sur |heading ",
    re.I,
)
_KEEP_SENT = re.compile(
    r"aire marine|marine protected area|le projet |project |"
    r"arriv|Berry-Mappemonde|quitte|leaves |jours de mer|days at sea|"
    r"nœuds de moyenne|knots on average|amarré|moored|d'escale|stopover|"
    r"départ|departure|left |quitté|approche|approaching|avion|flies|flight|"
    r"envole|par la route|by road|attend à|waits at|aujourd|today|"
    r"expédition|expedition|escales|stops|destination|entre le |between |"
    r"à venir|still to come|le plan compte|the plan has|"
    r"cap au |cap sur |heading ",
    re.I,
)

# RC19 : Galice (Muxía, Camariñas) et Sardaigne ne cèdent pas la place aux eaux.
_RG2_LANDMARK_SENT = re.compile(
    r"Galice|Galicia|Mux[ií]a|Camari[nñ]as|Sardaigne|Sardinia|Porto Torres",
    re.I,
)


def _trim_sentence_rank(sent: str) -> int:
    """0 = ne jamais retirer (AMP, projet, ouverture, escales).
    1 = eaux (seulement en trop, après P3/P4).
    2 = P3/P4 (côtes, climo, stations) et le reste — d'abord.
    """
    s = sent or ""
    if _AMP_OR_PROJECT_SENT.search(s) or _CORE_KEEP_SENT.search(s) or _RG2_LANDMARK_SENT.search(s):
        return 0
    if _WATERS_SENT.search(s):
        return 1
    return 2


def _drop_over_budget_sentence(sents: list[str], *, keep_head: int = 0) -> bool:
    """Retire une phrase entière : P3/P4 d'abord, puis une eau en trop. Jamais au milieu."""
    if len(sents) <= keep_head:
        return False
    best_i: Optional[int] = None
    best_rank = 0
    start = min(keep_head, len(sents))
    for i in range(len(sents) - 1, start - 1, -1):
        rank = _trim_sentence_rank(sents[i])
        if rank > best_rank:
            best_rank = rank
            best_i = i
            if rank >= 2:
                break
    if best_i is None or best_rank <= 0:
        return False
    sents.pop(best_i)
    return True


def _count_amp_project(chapters: list[dict]) -> tuple[int, int]:
    amp = proj = 0
    for ch in chapters:
        for s in _sentences(ch.get("text") or ""):
            if re.search(r"aire marine|marine protected area", s or "", re.I):
                amp += 1
            if re.search(r"le projet |project ", s or "", re.I):
                proj += 1
    return amp, proj


def _drop_extra_amp_or_project(
    sents: list[str], amp_n: int, proj_n: int, *, keep_head: int = 0,
) -> bool:
    """Retire une AMP ou un projet en trop — jamais l'unique, jamais au milieu."""
    if len(sents) <= keep_head:
        return False
    start = min(keep_head, len(sents))
    for i in range(len(sents) - 1, start - 1, -1):
        s = sents[i] or ""
        is_amp = bool(re.search(r"aire marine|marine protected area", s, re.I))
        is_proj = bool(re.search(r"le projet |project ", s, re.I))
        if is_amp and amp_n > 1:
            sents.pop(i)
            return True
        if is_proj and proj_n > 1 and not is_amp:
            sents.pop(i)
            return True
    return False


def _trim_script_to_char_budget(
    chapters: list[dict], hi: int, *, keep_head: int = 2,
) -> None:
    """P3/P4 d'abord, puis eaux en trop ; AMP/projet uniques jamais retirés."""
    guard = 0
    while script_chars(chapters) > hi and chapters and guard < 200:
        dropped = False
        for ch in reversed(chapters):
            sents = _sentences(ch.get("text") or "")
            if _drop_over_budget_sentence(sents, keep_head=keep_head):
                ch["text"] = " ".join(sents).strip()
                dropped = True
                break
        if not dropped:
            amp_n, proj_n = _count_amp_project(chapters)
            for ch in reversed(chapters):
                sents = _sentences(ch.get("text") or "")
                if _drop_extra_amp_or_project(sents, amp_n, proj_n, keep_head=keep_head):
                    ch["text"] = " ".join(sents).strip()
                    dropped = True
                    break
        if not dropped:
            break
        guard += 1


def _keep_one_amp_in_script(chapters: list[dict]) -> None:
    """2:30 : une seule phrase d'aire. On n'explique pas une seconde fois."""
    amp_n, _proj = _count_amp_project(chapters)
    guard = 0
    while amp_n > 1 and guard < 20:
        dropped = False
        for idx in range(len(chapters) - 1, -1, -1):
            keep = 1 if idx == 0 else 0
            sents = _sentences(chapters[idx].get("text") or "")
            if _drop_extra_amp_or_project(sents, amp_n, 1, keep_head=keep):
                chapters[idx]["text"] = " ".join(sents).strip()
                dropped = True
                break
        if not dropped:
            break
        amp_n, _proj = _count_amp_project(chapters)
        guard += 1


def _film_apply_char_budget(chapters: list[dict], seconds: Any) -> None:
    """Plafond 150 s ± 10 % à 15 car./s. 2:30 : keep_head=1 (ouverture d'une phrase)."""
    target = film_char_budget(seconds)
    if target <= 0 or not chapters:
        return
    keep = 1 if _film_compact_template(seconds) else 2
    if _film_compact_template(seconds):
        _keep_one_amp_in_script(chapters)
    _trim_script_to_char_budget(chapters, int(target * 1.1), keep_head=keep)


def fit_chapter_text(text: str, budget: int, extras: list[str], lang: str) -> str:
    """Assemble le chapitre. Jamais de phrase de remplissage. Budget = plafond, pas un plancher.

    Au-dessus du plafond : on retire des phrases entières, P3/P4 d'abord (côtes,
    climo, stations), puis des eaux en trop — jamais une AMP ni un projet, jamais
    au milieu d'une phrase.
    """
    blob = re.sub(r"\s{2,}", " ", (text or "").strip())
    for bit in extras:
        if bit and bit not in blob:
            blob = f"{blob} {bit}".strip()
    cap = int(budget or 0)
    if cap > 0:
        hi = max(int(cap * 1.1), cap)
        while len(blob) > hi:
            sents = _sentences(blob)
            if not _drop_over_budget_sentence(sents, keep_head=2):
                break
            blob = " ".join(sents).strip()
    blob = speak_film_text(split_short_sentences(blob), lang)
    blob = " ".join(thin_chapter_dates(_sentences(blob), lang))
    return blob


def chapter_anchors(text: str, anchored: list, t_a: int, t_b: int, lang: str) -> list[dict]:
    """[{charIdx, t}] : nœud dans le texte FINAL → instant du trajet (ISO).

    RG14 / D1 : l'ancre d'un lieu est l'index du nom (− avance voix 12 car., bornée à 0) ;
    une phrase de durée a deux ancres (arrivée au début, départ à la fin) ; un départ
    s'ancre au premier mot, une arrivée au dernier. Instants bornés à [tA, tB],
    croissants. Les phrases coupées par le budget n'ont pas d'ancre.
    """
    out: list[tuple[int, int, str, str]] = []
    if not text or not anchored:
        return []
    search_from = 0
    for item in anchored:
        row = _unpack_anchored(item)
        raw_sent = (row["sentence"] or "").strip()
        if not raw_sent or row["t"] is None:
            continue
        spoken = speak_film_text(raw_sent, lang)
        blob_idx = _locate_spoken(text, spoken, search_from)
        if blob_idx < 0:
            blob_idx = _locate_spoken(text, spoken, 0)
        if blob_idx < 0:
            continue
        search_from = blob_idx + 1
        t = int(row["t"])
        t_end = int(row["t_end"]) if row["t_end"] is not None else t
        if t_a is not None:
            t = max(int(t_a), t)
            t_end = max(int(t_a), t_end)
        if t_b is not None:
            t = min(int(t_b), t)
            t_end = min(int(t_b), t_end)
        if t_end < t:
            t_end = t
        role = (row["role"] or "").strip().lower()
        place = row["place"]
        kind = row["kind"]
        parts = _sentences(spoken) or [spoken]
        cursor = blob_idx
        for part in parts:
            part_idx = text.find(part, cursor)
            if part_idx < 0:
                part_idx = _locate_spoken(text, part, cursor)
            if part_idx < 0:
                part_idx = cursor
            cursor = part_idx + max(1, len(part) // 2)
            if role == "depart" or (not role and _is_depart_sentence(part) and not _is_arrival_sentence(part)):
                idx = _voice_lookahead_idx(_first_word_idx(part, part_idx))
                out.append((idx, t, place, kind or "depart"))
                continue
            if _is_duration_sentence(part):
                start = _voice_lookahead_idx(_first_word_idx(part, part_idx), part_idx)
                end = _voice_lookahead_idx(_end_idx(part, part_idx), part_idx)
                out.append((start, t, place, kind or "escale"))
                if end > start:
                    out.append((end, t_end, place, kind or "escale"))
                continue
            if role == "arrive" or _is_arrival_sentence(part):
                idx = _voice_lookahead_idx(_last_word_idx(part, part_idx), part_idx)
                out.append((idx, t, place, kind or "escale"))
                continue
            idx = _voice_lookahead_idx(_place_idx_in_sentence(part, part_idx, place), part_idx)
            out.append((idx, t, place, kind))
    out.sort(key=lambda p: p[0])
    result: list[dict] = []
    last_t: Optional[int] = None
    for idx, t, place, kind in out:
        if last_t is not None and t < last_t:
            t = last_t
        last_t = t
        if result and result[-1]["charIdx"] == idx:
            result[-1]["t"] = _iso(t)
            if place and not result[-1].get("place"):
                result[-1]["place"] = place
            if kind and not result[-1].get("kind"):
                result[-1]["kind"] = kind
            continue
        row_out: dict = {"charIdx": idx, "t": _iso(t)}
        if place:
            row_out["place"] = place
        if kind:
            row_out["kind"] = kind
        result.append(row_out)
    return result


def _trim_free_script(chapters: list[dict], max_words: int = FILM_FREE_MAX_WORDS) -> list[dict]:
    guard = 0
    while script_words(chapters) > max_words and guard < 200:
        guard += 1
        dropped = False
        for ch in reversed(chapters):
            sents = _sentences(ch.get("text") or "")
            if _drop_over_budget_sentence(sents, keep_head=1):
                ch["text"] = " ".join(sents).strip()
                dropped = True
                break
        if not dropped:
            break
    return chapters


_AIR_OUT_RE = re.compile(
    r"s'envole de Cayenne|prend l'avion pour Halifax|the crew flies from Cayenne|flies to Halifax",
    re.I,
)
_AIR_BACK_RE = re.compile(
    r"s'envole de Halifax|prend l'avion pour Cayenne|flies from Halifax|"
    r"retour en avion vers Cayenne|return flight to Cayenne",
    re.I,
)


def _route_has_air_pair(marks: list | None, moments: list | None = None) -> bool:
    keys = {_air_stop_key(m.get("name") or "") for m in (marks or []) if isinstance(m, dict)}
    if "cayenne" in keys and ("halifax" in keys or "saint-pierre" in keys):
        return True
    for row in moments or []:
        if not isinstance(row, dict):
            continue
        moment = row.get("moment") if isinstance(row.get("moment"), dict) else {}
        leg = moment.get("leg") if isinstance(moment.get("leg"), dict) else {}
        if _is_air_leg(str(leg.get("from") or ""), str(leg.get("to") or "")) or leg.get("vehicle") == "plane":
            return True
    return False


def _air_place_name(marks: list | None, key: str, fallback: str) -> str:
    for m in marks or []:
        if isinstance(m, dict) and _air_stop_key(m.get("name") or "") == key:
            return short_name(m.get("name") or fallback)
    return fallback


def _air_pair_sentences(marks: list | None, lang: str) -> tuple[str, str]:
    cayenne = _air_place_name(marks, "cayenne", "Cayenne (Guyane)")
    halifax = _air_place_name(marks, "halifax", "Halifax (Nouvelle-Écosse)")
    outbound = _air_window_sentence(
        {
            "from": {"name": cayenne}, "fromName": cayenne,
            "destName": halifax, "mode": "air", "vehicle": "plane",
        },
        lang=lang,
    )
    back = _air_window_sentence(
        {
            "from": {"name": halifax}, "fromName": halifax,
            "destName": cayenne, "mode": "air", "vehicle": "plane",
        },
        lang=lang,
    )
    return outbound, back


def _chapter_for_air_leg(chapters: list[dict], origin: str, dest: str) -> dict | None:
    """Chapitre vol dont from/to correspond à cette jambe — jamais le premier Cayenne par défaut."""
    for ch in chapters:
        if (
            _air_stop_key(ch.get("fromName") or "") == origin
            and _air_stop_key(ch.get("toName") or "") == dest
        ):
            return ch
    return None


def _chapter_for_air_fallback(chapters: list[dict]) -> dict | None:
    """RF5 : pas de jambe vol (Halifax sans iso) — un seul chapitre Cayenne, jamais la reprise."""
    for ch in chapters:
        frm = _air_stop_key(ch.get("fromName") or "")
        to = _air_stop_key(ch.get("toName") or "")
        if frm == "cayenne" and to != "papeete":
            return ch
    for ch in chapters:
        if _air_stop_key(ch.get("toName") or "") == "cayenne":
            return ch
    for ch in chapters:
        blob = f"{ch.get('text') or ''} {ch.get('fromName') or ''} {ch.get('toName') or ''}"
        if re.search(r"cayenne", blob, re.I) and _air_stop_key(ch.get("toName") or "") != "papeete":
            return ch
    return None


def _chapter_for_air(chapters: list[dict]) -> dict | None:
    """Aller Cayenne→Halifax s'il existe ; sinon un seul repli Cayenne (pas les deux vols)."""
    return _chapter_for_air_leg(chapters, "cayenne", "halifax") or _chapter_for_air_fallback(chapters)


def _inject_sentence_before_close(chapter: dict | None, sentence: str, lang: str) -> None:
    if not chapter or not sentence:
        return
    text = chapter.get("text") or ""
    if sentence in text:
        return
    sents = _sentences(text)
    close = ""
    if sents and re.search(r"aujourd|today", sents[-1] or "", re.I):
        close = sents.pop()
        text = " ".join(sents).strip()
    blob = f"{text} {sentence}".strip()
    if close:
        blob = f"{blob} {close}".strip()
    chapter["text"] = speak_film_text(blob, lang)


def _ensure_air_sentences(
    chapters: list[dict],
    *,
    marks: list | None,
    moments: list | None,
    lang: str,
) -> list[dict]:
    """Après fusion / budget : chaque phrase avion manquante va dans SON chapitre from/to."""
    if not chapters or not _route_has_air_pair(marks, moments):
        return chapters
    outbound, back = _air_pair_sentences(marks, lang)
    out_ch = _chapter_for_air_leg(chapters, "cayenne", "halifax")
    back_ch = _chapter_for_air_leg(chapters, "halifax", "cayenne")
    blob = " ".join(c.get("text") or "" for c in chapters)
    if outbound and out_ch and not _AIR_OUT_RE.search(out_ch.get("text") or ""):
        _inject_sentence_before_close(out_ch, outbound, lang)
    elif outbound and not out_ch and not _AIR_OUT_RE.search(blob):
        fallback = _chapter_for_air_fallback(chapters)
        if fallback is not None and fallback is not back_ch:
            _inject_sentence_before_close(fallback, outbound, lang)
    if (
        back
        and back_ch
        and back_ch is not out_ch
        and not _AIR_BACK_RE.search(back_ch.get("text") or "")
    ):
        _inject_sentence_before_close(back_ch, back, lang)
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
    """RG1 : le vol est une fenêtre typée, plus un ajout en queue de chapitre."""
    return []


def _climo_from_clock(clock: dict | None, t_a: int, t_b: int, first: bool) -> list[dict]:
    """Bascule d'horloge dans la fenêtre du chapitre — source unique pour la voix."""
    out: list[dict] = []
    for ev in notable_climo_changes(clock or {}):
        t = _ms(ev.get("t") or ev.get("iso"))
        if t is None:
            continue
        if first:
            if t < t_a or t > t_b:
                continue
        elif t <= t_a or t > t_b:
            continue
        change = {**ev, "tMs": t, "id": str(ev.get("id") or f"climo:{ev.get('event')}:{t}")}
        if change_is_speakable(change):
            out.append(change)
    return out


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
    eta: dict | None = None,
) -> dict[str, Any]:
    moments = _journal_moments(journal)
    now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    packed = film_candidates(journal, marks, clock, live, now)
    t0, t_end = packed["t0"], packed["tEnd"]
    if t0 is None or t_end is None or t_end <= t0:
        return {"chapters": [], "source": "rules", "chars": 0, "targetSeconds": _film_seconds(seconds), "_fromMoments": True}
    start_name = short_name((packed["start"] or {}).get("name") or "Saint-Maur")
    sea_name = short_name((packed["sea"] or {}).get("name") or "La Rochelle")
    windows = _annotate_episode_windows(
        _windows(packed["stops"], t0, t_end, clock),
        clock=clock, marks=marks, moments=moments, lang=lang,
    )
    has_budget = _film_seconds(seconds) > 0
    budget_s = _film_seconds(seconds)
    compact = _film_compact_template(seconds)
    tier = film_priority_tier(seconds)
    if has_budget:
        # RG8 : plafond = durée × 15 car./s (pas FILM_BUDGET_CHARS identique pour 150 et 180).
        target = film_char_budget(budget_s)
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
        if _is_air_window(w) and not w.get("returnMs"):
            w["returnMs"] = _air_return_from_moments(
                moments, w.get("fromName") or "", w.get("tA"),
            )
        depart_ms = _window_depart_ms(w) or 0
        # RC26 : la vérité du terrain borne le plan — si un moment de la jambe
        # existe avant l'appareillage déduit des marks, le bateau est déjà parti.
        first_leg = _first_leg_moment_ms(moments, w)
        if depart_ms and first_leg and (w.get("tA") or 0) < first_leg < depart_ms:
            depart_ms = first_leg
        w["departMs"] = depart_ms
        if _is_air_window(w):
            sail_moments: list[dict] = []
        else:
            sail_moments = [m for m in moments if isinstance(m, dict) and not _moment_is_air(m)]
        flat = _flatten_changes(sail_moments, w["tA"], w["tB"], first=i == 0)
        clock_climo = _climo_from_clock(w.get("clock") or clock, w["tA"], w["tB"], first=i == 0)
        if clock_climo:
            flat = [c for c in flat if str(c.get("kind") or "") != "climo"]
            flat.extend(clock_climo)
        for extra in _dest_culture_changes(dest):
            extra = {**extra, "t": (dest or {}).get("iso"), "tMs": w["tB"]}
            flat.append(extra)
        # RC55 : le second bateau (Saint-Pierre → Halifax, ou Saint-Pierre →
        # Cayenne si le titre n'a pas encore Halifax) ne reprend pas les eaux
        # de Guyane ni l'équateur du catamaran resté à quai.
        if _is_saint_pierre_depart(w):
            flat = _drop_guiana_equator_changes(flat)
        selected = select_chapter_changes(
            flat, w["tA"], w["tB"], budget=has_budget, tier=tier if has_budget else None,
            clock=w.get("clock") or clock, depart_ms=depart_ms,
        )
        # DC1 : une aire déjà dite, une fois. Le 2:30 n'en empile pas une seconde.
        if compact and any(_is_amp_change(c) for c in selected_all):
            selected = [c for c in selected if not _is_amp_change(c)]
        bits: list[str] = []
        placed: list[dict] = []

        def speak_change(change: dict) -> None:
            if change.get("kind") in {"escale", "marina"}:
                return
            if _is_air_window(w) and _is_air_only_stop(str(change.get("title") or "")):
                return
            title = short_name(change.get("title") or "")
            if change.get("kind") == "approche" and dest_name and title and (
                same_stop(title, dest_name) or dest_name.casefold() in title.casefold()
            ):
                return
            place = change_place_name(change) or title
            geo = change.get("geo") if isinstance(change.get("geo"), dict) else None
            if geo and (geo.get("fr") or geo.get("en")):
                place = geo.get("fr") or geo.get("en") or place
            if looks_english_title(place) and change.get("kind") in {
                "port", "approche", "culture", "project", "amp", "marina",
                "poe", "anchorage", "aton",
            }:
                return
            sentence = change_sentence(change, lang).strip()
            if not sentence or film_has_forbidden(sentence):
                return
            filtered, _dropped = filter_numbers(sentence, _facts_with_rounded(change))
            sentence = (filtered or "").strip()
            if not sentence or film_has_forbidden(sentence):
                return
            char_idx = len(" ".join(bits)) + (1 if bits else 0)
            bits.append(sentence)
            extra = {"place": place, "kind": str(change.get("kind") or "")}
            if change.get("lat") is not None:
                extra["lat"] = change.get("lat")
                extra["lon"] = change.get("lon")
            t_ms = change.get("tMs")
            # RC35 / RC48 : l'instant du jalon, pas le plus proche homonyme plus
            # loin sur l'horloge (Gibraltar recollé après le Maroc ; Mata-Utu /
            # Nouméa recollés en octobre au milieu d'août–septembre).
            anchored.append((sentence, t_ms, extra))
            placed.append(_bubble_from_change(change, w, lang, char_idx))
            selected_all.append(change)

        # Ancres (27 sept.) : chaque phrase porte l'instant du trajet dont elle parle — le client y cale le
        # bateau pendant qu'elle est dite (« approche d'Ajaccio » quand le bateau approche d'Ajaccio).
        anchored: list[tuple[str, Optional[int]]] = []
        skip_depart = False
        film_opens: list[str] = []
        if i == 0:
            film_opens = _film_open_sentences(
                start_name=start_name, sea_name=sea_name, lang=lang,
                display_t0=display_t0, review=review, compact=compact,
            )
            skip_depart = _is_road_window(w) and bool(film_opens)
        if _is_air_window(w):
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                review=review, n=len(windows), compact=compact,
            )
            if head:
                bits.append(head)
                anchored.append((head, depart_ms or w["tA"], {"role": "depart"}))
            bits[:] = thin_chapter_dates(bits, lang)
            chapter_budget = budgets[i] if i < len(budgets) else (FILM_CHAPTER_FLOOR if has_budget else 0)
            text = fit_chapter_text(" ".join(bits), chapter_budget, [], lang)
            if film_opens:
                head = " ".join(film_opens)
                if head and head not in text:
                    text = speak_film_text(f"{head} {text}".strip(), lang)
                    for sent in reversed(film_opens):
                        anchored.insert(0, (sent, w["tA"], {"role": "depart"}))
            if i == len(windows) - 1:
                close = _close_sentence(w, live, lang, review=review, eta=eta)
                if close and close not in text:
                    text = speak_film_text(f"{text} {close}".strip(), lang)
                    anchored.append((close, w["tB"]))
            chapters.append({
                "id": w["id"],
                "tA": _iso(w["tA"]),
                "tB": _iso(w["tB"]),
                "text": text,
                "anchors": chapter_anchors(text, anchored, w["tA"], w["tB"], lang),
                "events": placed,
                "fromName": w.get("fromName") or "",
                "toName": w.get("toName") or "",
                "fromLat": w.get("fromLat"),
                "fromLon": w.get("fromLon"),
                "toLat": w.get("toLat"),
                "toLon": w.get("toLon"),
            })
            continue
        if not skip_depart:
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                heading_deg=_leg_heading_deg(sail_moments, depart_ms, clock=w.get("clock") or clock),
                review=review, n=len(windows), include_date=i != 0, compact=compact,
            )
            if head:
                bits.append(head)
                anchored.append((head, depart_ms or w["tA"], {"role": "depart"}))
        for change in selected:
            speak_change(change)
        _append_review_sentences(bits, review, w, lang, anchored)
        key = norm_stop((dest or {}).get("name") or "")
        harbor = _arrival_harbor(selected, dest, lang) if arrived else ""
        arrival = (
            _arrival_sentence(
                dest, lang, display_t0, clock=w.get("clock"),
                harbor=harbor, chapter_i=i, compact=compact,
            ) if arrived else ""
        )
        if arrival and key and key not in cited:
            char_idx = len(" ".join(bits)) + (1 if bits else 0)
            bits.append(arrival)
            dest_place = short_name((dest or {}).get("name") or "")
            anchored.append((arrival, w["tB"], {"role": "arrive", "place": dest_place, "kind": "escale"}))
            cited.add(key)
            arr_id = f"stop:{dest['name']}:{dest.get('iso')}"
            dest_title = short_name(dest["name"])
            placed.append({
                "id": arr_id, "charIdx": char_idx, "kind": "stop", "title": dest_title,
                "fact": arrival, "score": 3,
                "card": {"id": arr_id, "kind": "stop", "title": dest_title, "text": arrival, "at": dest.get("iso"), "score": 3},
            })
        # RC30 : tri strict par instant d'ancre AVANT les connecteurs de date —
        # un item déplacé entre fenêtres ou une phrase de revue ancrée tôt ne
        # se dit plus hors de son ordre ; « le lendemain » est recalculé après.
        _order_chapter_sentences(
            bits, anchored, placed,
            from_name=str(w.get("fromName") or ""),
            to_name=str(w.get("toName") or w.get("destName") or ""),
        )
        thinned = thin_chapter_dates(bits, lang)
        if len(thinned) == len(bits) and len(anchored) == len(bits):
            anchored[:] = [_retarget_anchor(anchored[j], thinned[j]) for j in range(len(thinned))]
        bits[:] = thinned
        chapter_budget = budgets[i] if i < len(budgets) else (FILM_CHAPTER_FLOOR if has_budget else 0)
        text = fit_chapter_text(" ".join(bits), chapter_budget, [], lang)
        if film_opens:
            head = " ".join(film_opens)
            if head and head not in text:
                text = speak_film_text(f"{head} {text}".strip(), lang)
                for sent in reversed(film_opens):
                    anchored.insert(0, (sent, w["tA"], {"role": "depart"}))
        if i == len(windows) - 1:
            close = _close_sentence(w, live, lang, review=review, eta=eta)
            if close and close not in text:
                text = speak_film_text(f"{text} {close}".strip(), lang)
                anchored.append((close, w["tB"]))
        chapters.append({
            "id": w["id"],
            "tA": _iso(w["tA"]),
            "tB": _iso(w["tB"]),
            "text": text,
            "anchors": chapter_anchors(text, anchored, w["tA"], w["tB"], lang),
            "events": placed,
            "fromName": w.get("fromName") or "",
            "toName": w.get("toName") or "",
            "fromLat": w.get("fromLat"),
            "fromLon": w.get("fromLon"),
            "toLat": w.get("toLat"),
            "toLon": w.get("toLon"),
        })
    # RG8 / RC22 / RC27 : après opens recollés, puis après l'avion recollé.
    if has_budget and target > 0:
        _film_apply_char_budget(chapters, seconds)
    _ensure_air_sentences(chapters, marks=marks, moments=moments, lang=lang)
    if has_budget and target > 0:
        _film_apply_char_budget(chapters, seconds)
    chars = script_chars(chapters)
    return _with_dc_subjects({
        "chapters": chapters,
        "source": "rules",
        "chars": chars,
        "targetSeconds": budget_s,
        "estimatedSeconds": film_estimated_seconds(chars),
        "_events": selected_all,
        "_packed": packed,
        "_fromMoments": True,
    }, journal, lang)


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
    eta: dict | None = None,
) -> dict[str, Any]:
    now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    if _journal_moments(journal):
        return build_raw_from_moments(
            clock, marks, live, journal, lang=lang, seconds=seconds, now_ms=now,
            display_t0=display_t0, review=review, eta=eta,
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
    windows = _annotate_episode_windows(
        _windows(packed["stops"], t0, t_end, clock),
        clock=clock, marks=marks, moments=_journal_moments(journal), lang=lang,
    )

    def compose(evs: list[dict]) -> list[dict]:
        return _compose(
            windows, _assign(evs, windows), lang=lang, sea_name=sea_name,
            start_name=start_name, live=live, display_t0=display_t0,
            review=review, eta=eta, seconds=seconds,
        )

    chapters = compose(events)
    attach_chapter_events(chapters, packed, journal, lang)
    while _film_seconds(seconds) > 0 and script_chars(chapters) > FILM_MAX_CHARS:
        droppable = [e for e in events if e["id"] not in must_ids]
        if not droppable:
            break
        droppable.sort(key=lambda e: (e.get("score") or 0, -e["tMs"]))
        drop = droppable[0]
        events = [e for e in events if e["id"] != drop["id"]]
        chapters = compose(events)
        attach_chapter_events(chapters, packed, journal, lang)
    if _film_seconds(seconds) > 0:
        _film_apply_char_budget(chapters, seconds)
    _ensure_air_sentences(
        chapters, marks=marks, moments=_journal_moments(journal), lang=lang,
    )
    if _film_seconds(seconds) > 0:
        _film_apply_char_budget(chapters, seconds)
    chars = script_chars(chapters)
    return _with_dc_subjects({
        "chapters": chapters,
        "source": "rules",
        "chars": chars,
        "targetSeconds": _film_seconds(seconds),
        "estimatedSeconds": film_estimated_seconds(chars),
        "_events": events,
        "_packed": packed,
    }, journal, lang)


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


def _uniq_facts(rows: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for row in rows:
        if row is None:
            continue
        key = str(row).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row if not isinstance(row, str) else key)
    return out


def chapter_structured_facts(chapter: dict, *, lang: str = "fr") -> dict[str, Any]:
    """Faits JSON d'une étape (RG6 / RC26 / RC30) : dates, lieux, eaux, AMP, projets, stations, climo, distances, cap."""
    text = chapter.get("text") or ""
    events = [e for e in (chapter.get("events") or []) if isinstance(e, dict)]
    dates: list[str] = []
    for iso in (chapter.get("tA"), chapter.get("tB")):
        spoken = day_month(iso, lang, year=True)
        if spoken:
            dates.append(spoken)
            bare = day_month(iso, lang, year=False)
            if bare:
                dates.append(bare)
    rx = _DATE_EN_RE if _en(lang) else _DATE_FR_RE
    dates.extend(m.group(0) for m in rx.finditer(text))

    places: list[str] = []
    for key in ("fromName", "toName"):
        name = chapter.get(key)
        if name:
            places.append(str(name))
            places.append(short_name(name))

    waters: list[str] = []
    amp: list[str] = []
    projects: list[str] = []
    stations: list[str] = []
    climo: list[str] = []
    for ev in events:
        kind = str(ev.get("kind") or "").lower()
        card = ev.get("card") if isinstance(ev.get("card"), dict) else {}
        title = str(ev.get("title") or card.get("title") or "")
        fact = str(ev.get("fact") or card.get("text") or "")
        name = title or fact
        if kind in {"zee", "zee-enter"}:
            waters.append(name)
        elif kind == "amp":
            amp.append(name)
        elif kind == "project":
            projects.append(name)
        elif kind in {"sci", "station"}:
            stations.append(name)
        elif kind == "climo":
            climo.append(name)
        elif kind in {"coast", "port", "marina", "stop", "escale", "approche"}:
            places.append(name)

    distances: list[str] = []
    for m in re.finditer(
        r"\d+(?:[.,]\d+)?\s*(?:milles nautiques|milles|nautical miles|nœuds|noeuds|knots|jours|days)",
        text,
        re.I,
    ):
        distances.append(m.group(0))

    heading: list[str] = []
    for m in re.finditer(r"cap au [\w\-]+|heading [\w\-]+|cap sur [\w'’\- ]+", text, re.I):
        heading.append(m.group(0).strip())

    return {
        "dates": _uniq_facts(dates),
        "places": _uniq_facts(places),
        "waters": _uniq_facts(waters),
        "amp": _uniq_facts(amp),
        "projects": _uniq_facts(projects),
        "stations": _uniq_facts(stations),
        "climatology": _uniq_facts(climo),
        "distances": _uniq_facts(distances),
        "heading": _uniq_facts(heading),
        "raw": text,
    }


_NAME_STOP = frozenset({
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "au", "aux", "et", "ou", "en",
    "sur", "dans", "par", "pour", "avec", "sans", "sous", "vers", "chez", "entre",
    "puis", "ensuite", "plus", "loin", "arrivée", "arrivé", "arrivée", "départ",
    "aujourd", "hui", "aujourd'hui", "the", "a", "an", "and", "or", "then", "next",
    "after", "from", "into", "on", "at", "by", "for", "with", "cap", "heading",
    "milles", "nautiques", "nautical", "miles", "jours", "days", "nœuds", "noeuds",
    "knots", "janvier", "février", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "août", "aout", "septembre", "octobre", "novembre", "décembre",
    "decembre", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december", "l", "expédition",
    "expedition", "catamaran", "bateau", "boat", "équipage", "equipage", "crew",
    "approche", "approach", "quitte", "leaves", "left", "departed", "today",
    "aujourd’hui",
})
_NAME_TOKEN_RE = re.compile(
    r"[A-ZÉÈÊÀÂÙÛÎÔÇ][A-Za-zÀ-ÿ'’]*(?:-[A-ZÉÈÊÀÂÙÛÎÔÇ]?[A-Za-zÀ-ÿ'’]*)*"
)


def _name_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NAME_TOKEN_RE.finditer(text or ""):
        tok = m.group(0)
        folded = tok.casefold()
        if folded in _NAME_STOP or len(tok) <= 1:
            continue
        out.add(folded)
        for part in tok.split("-"):
            pf = part.casefold()
            if len(part) > 2 and pf not in _NAME_STOP:
                out.add(pf)
    return out


def written_names_subset(written: str, facts: Any) -> bool:
    """Chaque nom propre du rédigé doit déjà figurer dans les faits (y compris le brut)."""
    blob = facts if isinstance(facts, str) else json.dumps(facts, ensure_ascii=False, default=str)
    return _name_tokens(written) <= _name_tokens(blob)


def written_source_label(src: str) -> str:
    s = str(src or "")
    if s.startswith("nemotron") or s == "cache":
        return WRITTEN_SOURCE
    return s


def _sentence_starts(text: str, sents: list[str]) -> list[int]:
    starts: list[int] = []
    pos = 0
    for sent in sents:
        idx = (text or "").find(sent, pos)
        if idx < 0:
            idx = pos
        starts.append(idx)
        pos = idx + max(1, len(sent))
    return starts


def apply_written_guard(
    raw_text: str, written_text: str, facts: Any, *, lang: str = "fr",
) -> tuple[str, int, int]:
    """Une phrase rédigée par phrase du brut ; nombre ou nom inventé → phrase du brut."""
    raw_sents = _sentences(raw_text)
    if not raw_sents:
        return raw_text or "", 0, 0
    written_sents = _sentences(speak_film_text(written_text or "", lang))
    rewritten = 0
    fallen = 0
    kept: list[str] = []
    for i, raw_s in enumerate(raw_sents):
        cand = written_sents[i] if i < len(written_sents) else raw_s
        filtered, dropped = filter_numbers(cand, facts)
        ok = (
            not dropped
            and bool((filtered or "").strip())
            and written_names_subset(cand, facts)
        )
        if ok:
            kept.append(cand if cand.endswith((".", "!", "?", "…")) else f"{cand}.")
            rewritten += 1
        else:
            kept.append(raw_s)
            fallen += 1
    return " ".join(kept), rewritten, fallen


def _trim_written_to_budget(raw_text: str, written_text: str, cap: int) -> tuple[str, int]:
    """Si le rédigé dépasse le budget RC27, on remet des phrases du brut depuis la fin."""
    if cap <= 0 or len(written_text or "") <= cap:
        return written_text, 0
    raw_sents = _sentences(raw_text)
    wr_sents = _sentences(written_text)
    if len(wr_sents) != len(raw_sents):
        wr_sents = (wr_sents + raw_sents)[: len(raw_sents)]
    fallen = 0
    kept = list(wr_sents)
    while kept and len(" ".join(kept)) > cap:
        reverted = False
        for i in range(len(kept) - 1, -1, -1):
            if i < len(raw_sents) and kept[i] != raw_sents[i]:
                kept[i] = raw_sents[i]
                fallen += 1
                reverted = True
                break
        if not reverted:
            break
    return " ".join(kept), fallen


def reanchor_written_chapter(chapter: dict, written_text: str, lang: str) -> list[dict]:
    """Ancres du brut reportées phrase à phrase, puis recalculées sur le rédigé."""
    raw = chapter.get("text") or ""
    raw_sents = _sentences(raw)
    wr_sents = _sentences(written_text)
    raw_starts = _sentence_starts(raw, raw_sents)
    old = [a for a in (chapter.get("anchors") or []) if isinstance(a, dict)]
    t_a, t_b = _ms(chapter.get("tA")), _ms(chapter.get("tB"))
    anchored: list = []
    if old and raw_starts:
        for a in old:
            try:
                idx = int(a.get("charIdx") or 0)
            except (TypeError, ValueError):
                idx = 0
            sent_i = 0
            for i, start in enumerate(raw_starts):
                end = start + (len(raw_sents[i]) if i < len(raw_sents) else 0)
                if start <= idx < max(end, start + 1) or i == len(raw_starts) - 1:
                    sent_i = i
                    if start <= idx < max(end, start + 1):
                        break
            sent = wr_sents[sent_i] if sent_i < len(wr_sents) else (wr_sents[-1] if wr_sents else "")
            t = a.get("t")
            t_ms = t if isinstance(t, int) else _ms(t)
            extra = {
                "place": a.get("place") or "",
                "kind": a.get("kind") or "",
                "role": a.get("role") or "",
            }
            anchored.append((sent, t_ms, extra))
    elif wr_sents:
        anchored = [(sent, t_a, {}) for sent in wr_sents]
    out = chapter_anchors(written_text, anchored, t_a, t_b, lang) if written_text and anchored else []
    if out:
        return _strict_increasing_anchors(out)
    return _strict_increasing_anchors(_fallback_anchors(written_text, wr_sents, old, t_a))


def _fallback_anchors(
    written_text: str, wr_sents: list[str], old: list[dict], t_a: Optional[int],
) -> list[dict]:
    starts = _sentence_starts(written_text, wr_sents)
    if not old:
        return [
            {"charIdx": starts[i] if i < len(starts) else 0, "t": _iso(t_a) or ""}
            for i in range(len(wr_sents))
        ]
    out: list[dict] = []
    for i, a in enumerate(old):
        idx = starts[i] if i < len(starts) else (starts[-1] if starts else 0)
        row = {"charIdx": idx, "t": a.get("t")}
        if a.get("place"):
            row["place"] = a["place"]
        out.append(row)
    return out


def _strict_increasing_anchors(anchors: list[dict]) -> list[dict]:
    ordered = sorted(
        [a for a in anchors if isinstance(a, dict)],
        key=lambda a: int(a.get("charIdx") or 0),
    )
    out: list[dict] = []
    last = -1
    last_t: Optional[int] = None
    for a in ordered:
        try:
            idx = int(a.get("charIdx") or 0)
        except (TypeError, ValueError):
            idx = 0
        if idx <= last:
            idx = last + 1
        last = idx
        t_raw = a.get("t")
        t_ms = t_raw if isinstance(t_raw, int) else _ms(t_raw)
        if last_t is not None and t_ms is not None and t_ms < last_t:
            t_ms = last_t
        if t_ms is not None:
            last_t = t_ms
        row = {**a, "charIdx": idx}
        if t_ms is not None:
            row["t"] = _iso(t_ms) if not isinstance(t_raw, str) else (t_raw or _iso(t_ms))
            if isinstance(t_raw, str) and t_ms == _ms(t_raw):
                row["t"] = t_raw
            elif t_ms is not None:
                row["t"] = _iso(t_ms)
        out.append(row)
    return out


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


def written_is_valid(
    text: str, facts: Any, event_ids: list[str], seconds: Any = 150,
) -> tuple[bool, str, int]:
    """No new number, every [[ev:id]] present, window from film_char_budget."""
    filtered, dropped = filter_numbers(text, facts)
    if dropped:
        return False, filtered, dropped
    for eid in event_ids:
        if f"[[ev:{eid}]]" not in (text or ""):
            return False, filtered, dropped
    n = len(strip_tags(text))
    window = film_write_window(seconds)
    if window is not None:
        lo, hi = window
        if n < lo or n > hi:
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
    "You rewrite ONE film chapter from structured facts, sentence by sentence. "
    "Output EXACTLY one sentence per raw sentence, in the same order. "
    "Keep EVERY number, proper name and date exactly as given. "
    "Do not add a fact. Do not invent a figure, a place or a date. "
    "Write for the ear: spoken French or English as requested. "
    "Units in full words (milles nautiques / nautical miles), never nm. "
    "Thinking OFF. No tags. No new figure."
)
EDIT_SYSTEM = (
    "You edit an already-written French expedition film. "
    "Keep every number, proper name and date exactly. "
    "Same sentence count and order. Do not add a fact. "
    "Output only the edited French. Thinking OFF."
)
JUDGE_SYSTEM = (
    "You judge an already-written film text. Do not rewrite it. "
    "Return JSON only: {\"ok\": true|false, \"reason\": \"one line\"}. "
    "ok=false if a number, name or date was invented."
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


async def write_stored_plan(
    plan: dict,
    *,
    lang: str = "fr",
    cascade: Callable = cascade_text,
    seconds: Any = None,
) -> tuple[Optional[dict], dict[str, Any]]:
    """Réécrit un plan public (stock) phrase par phrase. Aucun appel si la cascade rend rules/budget."""
    raw_chapters = [c for c in (plan.get("chapters") or []) if isinstance(c, dict)]
    stats = {"rewritten": 0, "fallen": 0, "source": "rules"}
    if not raw_chapters:
        return None, stats
    secs = seconds if seconds is not None else plan.get("targetSeconds")
    budget_total = film_char_budget(secs)
    raw_lens = [max(1.0, len(c.get("text") or "") or 1) for c in raw_chapters]
    budgets = allocate_chapter_budgets(raw_lens, budget_total) if budget_total else [0] * len(raw_chapters)
    chapters_out: list[dict] = []
    source_last = "rules"
    any_llm = False
    for i, ch in enumerate(raw_chapters):
        raw = ch.get("text") or ""
        raw_sents = _sentences(raw)
        facts = chapter_structured_facts(ch, lang=lang)
        if not raw_sents:
            chapters_out.append(ch)
            continue
        user = (
            f"lang={'en' if _en(lang) else 'fr'}\n"
            f"facts={json.dumps(facts, ensure_ascii=False, default=str)}\n"
            f"sentences={json.dumps(raw_sents, ensure_ascii=False)}"
        )
        max_tok = min(WRITE_MAX_TOKENS, max(400, 80 * len(raw_sents)))
        text, source = await cascade(
            WRITE_SYSTEM, user, tier="write", fallback="", facts=facts, max_tokens=max_tok,
        )
        if not (text or "").strip() or source in {"rules", "budget"}:
            chapters_out.append(ch)
            stats["fallen"] += len(raw_sents)
            if source == "budget":
                source_last = "budget"
            continue
        any_llm = True
        source_last = source
        guarded, rw, fb = apply_written_guard(raw, text, facts, lang=lang)
        cap = budgets[i] if i < len(budgets) else 0
        if cap:
            hi = max(int(cap * 1.1), cap, len(raw))
            guarded, extra_fb = _trim_written_to_budget(raw, guarded, hi)
            if extra_fb:
                fb += extra_fb
                rw = max(0, rw - extra_fb)
        anchors = reanchor_written_chapter(ch, guarded, lang)
        chapters_out.append({**ch, "text": guarded, "anchors": anchors})
        stats["rewritten"] += rw
        stats["fallen"] += fb
    stats["source"] = source_last
    if not any_llm or stats["rewritten"] <= 0:
        return None, stats
    n = script_chars(chapters_out)
    return {
        "chapters": chapters_out,
        "source": written_source_label(source_last),
        "chars": n,
        "targetSeconds": _film_seconds(plan.get("targetSeconds") if secs is None else secs),
        "hasWritten": True,
    }, stats


async def write_with_llm(
    raw: dict,
    events: list[dict],
    *,
    lang: str = "fr",
    cascade: Callable = cascade_text,
) -> tuple[Optional[dict], str]:
    """RG11A : rédigé phrase par phrase depuis les faits. Repli local, jamais un échec global."""
    _ = events
    plan, stats = await write_stored_plan(raw, lang=lang, cascade=cascade)
    if plan is None:
        return None, stats.get("source") or "rules"
    return plan, stats.get("source") or plan.get("source") or "rules"


def film_ultra_open() -> bool:
    """Ultra (éditer + juger) seulement si le plafond juge est ouvert dans l'env."""
    import os  # noqa: PLC0415
    import llm_budget  # noqa: PLC0415

    raw = (os.environ.get("NAVIGUIDE_LLM_DAILY_TOKENS_JUDGE") or "").strip()
    if not raw:
        return False
    try:
        if int(raw) <= 0:
            return False
    except ValueError:
        return False
    return llm_budget.allow("judge")


def _parse_judge_ok(text: str) -> Optional[bool]:
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
    if not isinstance(data, dict) or "ok" not in data:
        return None
    val = data.get("ok")
    if val is True or val == "true" or val == 1:
        return True
    if val is False or val == "false" or val == 0:
        return False
    return None


def _stamp_written_plan(plan: dict, source: str, seconds: Any) -> dict:
    chapters = [c for c in (plan.get("chapters") or []) if isinstance(c, dict)]
    n = script_chars(chapters)
    out = dict(plan)
    out["chapters"] = chapters
    out["source"] = source
    out["chars"] = n
    out["targetSeconds"] = _film_seconds(seconds if seconds is not None else plan.get("targetSeconds"))
    out["hasWritten"] = True
    return out


def _redistribute_written_blob(raw_plan: dict, blob: str, *, lang: str = "fr") -> Optional[dict]:
    raw_chapters = [c for c in (raw_plan.get("chapters") or []) if isinstance(c, dict)]
    if not raw_chapters:
        return None
    sents = _sentences(blob)
    idx = 0
    out: list[dict] = []
    rewritten = 0
    for ch in raw_chapters:
        raw = ch.get("text") or ""
        n = len(_sentences(raw))
        chunk = " ".join(sents[idx:idx + n]) if n else raw
        idx += n
        facts = chapter_structured_facts(ch, lang=lang)
        guarded, rw, _fb = apply_written_guard(raw, chunk, facts, lang=lang)
        anchors = reanchor_written_chapter(ch, guarded, lang)
        out.append({**ch, "text": guarded, "anchors": anchors})
        rewritten += rw
    if rewritten <= 0:
        return None
    return _stamp_written_plan({**raw_plan, "chapters": out}, WRITTEN_SOURCE, raw_plan.get("targetSeconds"))


async def edit_written_once(
    super_plan: dict,
    raw_plan: dict,
    *,
    cascade: Callable = cascade_text,
) -> Optional[dict]:
    """Un seul appel Ultra : éditer le français déjà écrit par Super."""
    chapters = [c for c in (super_plan.get("chapters") or []) if isinstance(c, dict)]
    blob = " ".join(c.get("text") or "" for c in chapters).strip()
    if not blob:
        return None
    facts = [chapter_structured_facts(c, lang="fr") for c in (raw_plan.get("chapters") or chapters) if isinstance(c, dict)]
    user = f"facts={json.dumps(facts, ensure_ascii=False, default=str)}\ntext={blob}"
    max_tok = min(2048, max(400, (len(blob) // 2) + 80))
    text, source = await cascade(
        EDIT_SYSTEM, user, tier="judge", fallback="", facts=facts, max_tokens=max_tok,
    )
    if not (text or "").strip() or source in {"rules", "budget"}:
        return None
    return _redistribute_written_blob(raw_plan, text, lang="fr")


async def judge_written_once(
    plan: dict,
    *,
    cascade: Callable = cascade_text,
) -> bool:
    """Un autre appel Ultra : juger le texte déjà écrit, sans le réécrire."""
    blob = " ".join(
        c.get("text") or "" for c in (plan.get("chapters") or []) if isinstance(c, dict)
    ).strip()
    if not blob:
        return False
    user = json.dumps({"text": blob[:8000]}, ensure_ascii=False)
    text, source = await cascade(
        JUDGE_SYSTEM, user, tier="judge", fallback="", facts=blob, max_tokens=128,
    )
    if source in {"rules", "budget"}:
        return False
    return _parse_judge_ok(text) is True


async def translate_written_plan(
    fr_plan: dict,
    raw_plan: dict,
    *,
    cascade: Callable = cascade_text,
) -> Optional[dict]:
    """Lightning : français accepté → anglais, puis filter_numbers."""
    from story_cascade import TRANSLATE_SYSTEM  # noqa: PLC0415

    raw_chapters = [c for c in (raw_plan.get("chapters") or []) if isinstance(c, dict)]
    fr_chapters = [c for c in (fr_plan.get("chapters") or []) if isinstance(c, dict)]
    if not fr_chapters:
        return None
    out: list[dict] = []
    any_ok = False
    for i, ch in enumerate(fr_chapters):
        raw_ch = raw_chapters[i] if i < len(raw_chapters) else ch
        src = ch.get("text") or ""
        facts = chapter_structured_facts(raw_ch, lang="fr")
        text, source = await cascade(
            TRANSLATE_SYSTEM,
            f"French text:\n{src}",
            tier="fast",
            fallback="",
            facts=facts,
            max_tokens=min(1200, max(256, (len(src) // 2) + 80)),
        )
        if not (text or "").strip() or source in {"rules", "budget"}:
            return None
        guarded, rw, _fb = apply_written_guard(raw_ch.get("text") or src, text, facts, lang="en")
        if rw <= 0:
            return None
        any_ok = True
        anchors = reanchor_written_chapter(raw_ch, guarded, "en")
        out.append({**raw_ch, "text": guarded, "anchors": anchors})
    if not any_ok:
        return None
    stamped = _stamp_written_plan({**fr_plan, "chapters": out}, fr_plan.get("source") or WRITTEN_SOURCE, fr_plan.get("targetSeconds"))
    return stamped


async def write_film_chain(
    plan: dict,
    *,
    seconds: Any = 150,
    cascade: Callable = cascade_text,
) -> tuple[Optional[dict], Optional[dict], dict[str, Any]]:
    """Au clic : Super FR, puis Ultra édite + juge si plafond ouvert, puis Lightning EN."""
    stats: dict[str, Any] = {
        "super": 0, "ultra_edit": 0, "ultra_judge": 0, "lightning": 0,
        "source": "rules", "reviewed": False,
    }
    raw = dict(plan)
    raw["targetSeconds"] = _film_seconds(seconds if seconds is not None else plan.get("targetSeconds"))
    super_plan, super_stats = await write_stored_plan(raw, lang="fr", cascade=cascade, seconds=seconds)
    if super_plan is None or int((super_stats or {}).get("rewritten") or 0) <= 0:
        return None, None, stats
    stats["super"] = 1
    stats["source"] = WRITTEN_SOURCE
    accepted = _stamp_written_plan(super_plan, WRITTEN_SOURCE, seconds)

    if film_ultra_open():
        edited = await edit_written_once(accepted, raw, cascade=cascade)
        stats["ultra_edit"] = 1
        if edited:
            ok = await judge_written_once(edited, cascade=cascade)
            stats["ultra_judge"] = 1
            if ok:
                accepted = _stamp_written_plan(edited, REVIEWED_SOURCE, seconds)
                stats["reviewed"] = True
                stats["source"] = REVIEWED_SOURCE

    en_plan = await translate_written_plan(accepted, raw, cascade=cascade)
    if en_plan:
        en_plan = _stamp_written_plan(en_plan, accepted.get("source") or WRITTEN_SOURCE, seconds)
        stats["lightning"] = 1
    return accepted, en_plan, stats


def _public_plan(plan: dict, source: str) -> dict:
    chapters = []
    for c in plan.get("chapters") or []:
        chapters.append({
            "id": c.get("id"),
            "tA": c.get("tA"),
            "tB": c.get("tB"),
            "text": fix_en_waters_casing(c.get("text") or ""),
            "anchors": [
                {"charIdx": a.get("charIdx"), "t": a.get("t")}
                for a in (c.get("anchors") or [])
                if isinstance(a, dict) and a.get("t") is not None
            ],
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
    eta: dict | None = None,
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
    eta_fp = eta_fingerprint(eta)
    if eta_fp:
        fp = f"{fp}|eta={eta_fp}"
    if shown != OFFICIAL_T0:
        fp = f"{fp}|t0={shown}"
    key = film_cache_key(fp, lang, seconds)
    cached = get_film_cached(key) or {}
    raw_full = build_raw_script(
        clock, marks, live, journal, lang=lang, seconds=seconds, now_ms=now_ms,
        display_t0=shown, review=review, eta=eta,
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
                        review=review, eta=eta,
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
    raw_clock = voy.get("clock")
    if not raw_clock:
        # Depuis RF2 l'horloge vit dans le stock : la relire (ms) plutôt que la recalculer (5 min, 27 sept.).
        try:
            from official_store import stored_clock  # noqa: PLC0415
            raw_clock = stored_clock()
        except Exception:
            raw_clock = None
    raw_clock = raw_clock or _climo_clock(voy)
    voy = {**voy, "clock": raw_clock}
    clock = {**raw_clock, "t0": OFFICIAL_T0}
    marks = merge_route_marks(voy.get("marks") or [], raw_clock)
    _journal_safely(lambda: journal.tick(voy, when))
    live = sample_clock_at_time(raw_clock, when) or {}
    payload = journal.summary(500)
    moments = _official_moments_for_film(OFFICIAL_VOYAGE_ID)
    if moments:
        payload = {**payload, "moments": moments}
    review, eta = _stored_review_and_eta()
    if review is None:
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
        eta=eta,
    )


async def warm_film_story(
    voyage_id: str | None = None,
    *,
    langs: tuple[str, ...] = ("fr", "en"),
    seconds: int = 150,
    cascade: Callable = cascade_text,
) -> dict[str, Any]:
    """Préchauffe le brut seulement — ED1 : plus de chaîne Super/Ultra ici."""
    from voyage_api import _climo_clock, _now  # noqa: PLC0415
    from voyage_clock import OFFICIAL_VOYAGE_ID, sample_clock_at_time  # noqa: PLC0415
    from voyage_store import load_voyage  # noqa: PLC0415
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
    moments = _official_moments_for_film(vid)
    if moments:
        payload = {**payload, "moments": moments}
    review, eta = _stored_review_and_eta()
    if review is None:
        try:
            from plan_review import review_official  # noqa: PLC0415
            review = review_official(voy, when, season=False)
        except Exception:
            review = None
    now_ms = int(when.timestamp() * 1000) if hasattr(when, "timestamp") else None
    out: dict[str, Any] = {}
    import llm_budget  # noqa: PLC0415
    # Écriture LLM du film en ARRIÈRE-PLAN : sous on-demand (défaut, 28 sept.) la cascade rend le brut.
    with llm_budget.background():
        for lang in langs:
            plan = await build_film_response(
                clock, live, payload, marks=marks, lang=lang, seconds=_film_seconds(seconds),
                style="written", cascade=cascade, want_write=False, now_ms=now_ms,
                review=review, eta=eta,
            )
            out[lang] = {"hasWritten": plan.get("hasWritten"), "chars": plan.get("chars"), "source": plan.get("source")}
    return {"voyageId": vid, "status": "ready", "langs": out}

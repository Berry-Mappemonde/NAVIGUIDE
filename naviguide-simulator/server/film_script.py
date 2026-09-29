"""Script du film 2:30 — brut (règles), sélection, version rédigée (lots F3 / R9c).

Le LLM ne produit jamais un nombre : `filter_numbers` + balises `[[ev:id]]`.
Rédigé **chapitre par chapitre**, préchauffé, cache SQLite ns `film-story`.
Jamais généré au clic. Repli : le brut.
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
from voyage_clock import OFFICIAL_T0

FILM_MAX_CHARS = 2400
FILM_BUDGET_CHARS = 2400
FILM_WRITE_MIN = 2160
FILM_WRITE_MAX = 2640
FILM_CHAPTER_FLOOR = 120
FILM_CHAPTER_MAX_CHANGES = 4   # arrivée + un fait de mer + la marina de l'escale + approche (27 sept. ; était 3)
# Client `FILM_VOICE_LOOKAHEAD_CHARS` : le bateau vise 12 caractères devant la voix.
# L'ancre serveur est déjà compensée (nom du lieu − 12, bornée à 0) — lot RG14.
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
CHANGE_PRIORITY = {
    "escale": 0, "approche": 1, "alert-on": 2, "station": 3,
    "zee-enter": 4, "coast": 4, "amp": 5, "project": 5, "climo": 5, "marina": 6, "cyclone": 7, "culture": 8,
    "port": 9, "regime": 10, "alert-off": 11,
}
BUBBLE_KIND = {
    "escale": "stop", "approche": "stop", "alert-on": "wx", "alert-off": "wx",
    "zee-enter": "zee", "coast": "coast", "station": "sci", "amp": "amp",
    "project": "project", "regime": "climo", "climo": "climo",
    "marina": "stop", "cyclone": "climo", "culture": "stop", "port": "poe",
}
AROUND_TO_KIND = {
    "marina": "marina", "science": "station", "station": "station",
    "mpa": "amp", "amp": "amp", "project": "project", "cyclone": "cyclone",
    "culture": "culture", "port": "port",
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
FILM_FREE_MAX_WORDS = 800
FILM_ESTIMATE_CPS = 15  # débit constant (27 sept.) : durée = caractères ÷ 15 ; pas de recalibrage
FILM_TIER_SHORT = 2     # 2:30 — ouverture, eaux, une AMP ou un projet, escales
FILM_TIER_MEDIUM = 3    # 3:00 — + côtes et climatologie
FILM_TIER_FULL = 4      # intégral — tout, sans plafond
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
    },
    "en": {
        "gibraltar": "Strait of Gibraltar",
        "strait of gibraltar": "Strait of Gibraltar",
        "bay of biscay": "Bay of Biscay",
    },
}
# Plus spécifique d'abord : Samoa américaines avant American, Canaries avant Spanish, etc.
_ZEE_NATION = (
    (re.compile(r"american samoa|samoa am[ée]ricain", re.I), ("des Samoa américaines", "American Samoa")),
    (re.compile(r"canary|canaries", re.I), ("des Canaries", "Canary Islands")),
    (re.compile(r"madeira|mad[èe]re", re.I), ("de Madère", "Madeira")),
    (re.compile(r"sint[- ]eustatius|eustatius", re.I), ("de Sint-Eustatius", "Sint-Eustatius")),
    (re.compile(r"sint[- ]maarten", re.I), ("de Sint-Maarten", "Sint-Maarten")),
    (re.compile(r"wallis", re.I), ("de Wallis-et-Futuna", "Wallis and Futuna")),
    (re.compile(r"matthew|hunter", re.I), ("de Matthew-et-Hunter", "Matthew and Hunter")),
    (re.compile(r"new caledonia|nouvelle-cal[ée]donie", re.I), ("de Nouvelle-Calédonie", "New Caledonia")),
    (re.compile(r"bonaire", re.I), ("de Bonaire", "Bonaire")),
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
    (re.compile(r"venezuel|v[ée]n[ée]zu[ée]l", re.I), ("vénézuéliennes", "Venezuelan")),
    (re.compile(r"cuban|cubain", re.I), ("cubaines", "Cuban")),
    (re.compile(r"fijian|fidj", re.I), ("fidjiennes", "Fijian")),
    (re.compile(r"indonesian|indon[ée]sien", re.I), ("indonésiennes", "Indonesian")),
    (re.compile(r"indian|indien", re.I), ("indiennes", "Indian")),
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
    # Route Berry-Mappemonde (27 sept.) : le film disait « les eaux Antiguan and Barbudan », « dominicaine ».
    (re.compile(r"antigua", re.I), ("d'Antigua-et-Barbuda", "Antiguan")),
    (re.compile(r"dominican republic|r[ée]publique dominicaine", re.I), ("de la République dominicaine", "Dominican Republic")),
    (re.compile(r"dominica|dominiquais", re.I), ("de la Dominique", "Dominican")),
    (re.compile(r"kittitian|saint[- ]kitts|nevis", re.I), ("de Saint-Christophe-et-Niévès", "Kittitian")),
    (re.compile(r"montserrat", re.I), ("de Montserrat", "Montserratian")),
    (re.compile(r"anguill", re.I), ("d'Anguilla", "Anguillan")),
    (re.compile(r"saint[- ]martin", re.I), ("de Saint-Martin", "Saint-Martin")),
    (re.compile(r"surinam", re.I), ("surinamaises", "Surinamese")),
    (re.compile(r"guyanese|guyana\b", re.I), ("du Guyana", "Guyanese")),
    (re.compile(r"trinidad|tobag", re.I), ("de Trinité-et-Tobago", "Trinidadian")),
    (re.compile(r"barbad", re.I), ("barbadiennes", "Barbadian")),
    (re.compile(r"saint[- ]lucia|lucian", re.I), ("de Sainte-Lucie", "Saint Lucian")),
    (re.compile(r"grenad", re.I), ("grenadiennes", "Grenadian")),
    (re.compile(r"vincent", re.I), ("de Saint-Vincent-et-les-Grenadines", "Vincentian")),
    (re.compile(r"panama|panam[ée]", re.I), ("panaméennes", "Panamanian")),
    (re.compile(r"costa ric", re.I), ("costariciennes", "Costa Rican")),
    (re.compile(r"ecuador|[ée]quatorien", re.I), ("équatoriennes", "Ecuadorian")),
    (re.compile(r"peru|p[ée]rou|peruvian", re.I), ("péruviennes", "Peruvian")),
    (re.compile(r"kiribati|gilbert", re.I), ("des Kiribati", "Kiribati")),
    (re.compile(r"cook island", re.I), ("des Îles Cook", "Cook Islands")),
    (re.compile(r"tonga", re.I), ("tongiennes", "Tongan")),
    (re.compile(r"samoa", re.I), ("samoanes", "Samoan")),
    (re.compile(r"tuvalu", re.I), ("des Tuvalu", "Tuvaluan")),
    (re.compile(r"vanuatu|vanuatuan", re.I), ("du Vanuatu", "Vanuatuan")),
    (re.compile(r"solomon", re.I), ("des Îles Salomon", "Solomon Islands")),
    (re.compile(r"comor", re.I), ("comoriennes", "Comorian")),
    (re.compile(r"mauriti|mauricien", re.I), ("mauriciennes", "Mauritian")),
    (re.compile(r"madagas|malgache", re.I), ("malgaches", "Malagasy")),
    (re.compile(r"mozambi", re.I), ("mozambicaines", "Mozambican")),
    (re.compile(r"seychell", re.I), ("seychelloises", "Seychellois")),
    (re.compile(r"tanzan", re.I), ("tanzaniennes", "Tanzanian")),
    (re.compile(r"kenya", re.I), ("kényanes", "Kenyan")),
    (re.compile(r"cape verd|cap-vert|capverd", re.I), ("capverdiennes", "Cape Verdean")),
    (re.compile(r"gibraltar", re.I), ("de Gibraltar", "Gibraltar")),
    (re.compile(r"bermud", re.I), ("des Bermudes", "Bermudian")),
    (re.compile(r"bahamas|bahamian", re.I), ("bahaméennes", "Bahamian")),
    (re.compile(r"haiti|ha[ïi]tien", re.I), ("haïtiennes", "Haitian")),
    (re.compile(r"jamaic", re.I), ("jamaïcaines", "Jamaican")),
    (re.compile(r"honduran|honduras", re.I), ("honduriennes", "Honduran")),
    (re.compile(r"nicaragua", re.I), ("nicaraguayennes", "Nicaraguan")),
)

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

_ZEE_CLUSTER_SHORT = (
    (re.compile(r"antigua", re.I), ("Antigua", "Antigua")),
    (re.compile(r"kittitian|saint[- ]kitts|nevis", re.I), ("Saint-Kitts", "Saint Kitts")),
    (re.compile(r"eustatius", re.I), ("Sint-Eustatius", "Sint-Eustatius")),
    (re.compile(r"sint[- ]maarten", re.I), ("Sint-Maarten", "Sint-Maarten")),
    (re.compile(r"saint[- ]martin", re.I), ("Saint-Martin", "Saint-Martin")),
    (re.compile(r"montserrat", re.I), ("Montserrat", "Montserrat")),
    (re.compile(r"dominica|dominiquais", re.I), ("la Dominique", "Dominica")),
    (re.compile(r"vincent", re.I), ("Saint-Vincent", "Saint Vincent")),
    (re.compile(r"saint[- ]lucia|lucian", re.I), ("Sainte-Lucie", "Saint Lucia")),
    (re.compile(r"barbad", re.I), ("la Barbade", "Barbados")),
    (re.compile(r"bonaire", re.I), ("Bonaire", "Bonaire")),
)

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
    raw_in = str(name or "")
    if re.search(r"western sahara|sahara occidental", raw_in, re.I):
        return (
            "disputed waters of Western Sahara"
            if _en(lang) else
            "les eaux disputées du Sahara occidental"
        )
    raw = clean_spoken_label(name, lang) or raw_in
    if not raw.strip():
        return ""
    if re.search(r"haute mer|high seas", f"{raw_in} {raw}", re.I):
        return "the high seas" if _en(lang) else "haute mer"
    for rx, (fr, en) in _ZEE_NATION:
        if rx.search(raw) or rx.search(raw_in):
            return f"{en} waters" if _en(lang) else f"les eaux {fr}"
    rest = re.sub(
        r"zone économique exclusive|exclusive economic zone|eez|zee",
        "",
        raw,
        flags=re.I,
    )
    rest = rest.strip(" ()-")
    rest = re.sub(r"\s*\([^)]*$", "", rest).strip(" ()-")
    if re.search(r"zone économique exclusive|exclusive economic zone", rest, re.I):
        return ""
    had_zee = bool(re.search(
        r"zone économique|exclusive economic|eez|\bzee\b|eaux",
        raw,
        re.I,
    ))
    if rest and had_zee and not _is_generic_title(rest, "zee"):
        return f"{rest} waters" if _en(lang) else f"les eaux {rest}"
    return ""


def zee_cluster_short(name: str, lang: str = "fr") -> str:
    """Nom court pour un groupe de 24 h : Antigua, pas « les eaux d'Antigua-et-Barbuda »."""
    raw = str(name or "")
    for rx, (fr, en) in _ZEE_CLUSTER_SHORT:
        if rx.search(raw):
            return en if _en(lang) else fr
    waters = zee_waters_label(raw, lang)
    if not waters:
        return ""
    waters = re.sub(r"^(les eaux|the)\s+", "", waters, flags=re.I)
    waters = re.sub(r"\s+waters$", "", waters, flags=re.I)
    waters = re.sub(r"^d['’]", "", waters)
    waters = re.sub(r"^(de|des|du)\s+", "", waters, flags=re.I)
    return waters.strip()


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
    return {
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
        if clusters and dt < CLUSTER_MS and not _zee_high_seas(c) and not _zee_high_seas(prev):
            clusters[-1].append(c)
        else:
            clusters.append([c])
    grouped = [_zee_cluster_change(cl) for cl in clusters]
    if span_ms < SHORT_CROSSING_MS:
        return grouped
    by_day: dict[str, dict] = {}
    for c in grouped:
        day = _utc_day(c)
        if day and day not in by_day:
            by_day[day] = c
        elif not day:
            by_day[f"_{len(by_day)}"] = c
    return [by_day[k] for k in sorted(by_day)]


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
        ports = ports[:2]
        geo = first.get("geo")
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
    rank = {"strait": 3, "island": 2, "coast": 1}
    for c in merged:
        day = _utc_day(c) or f"_{len(by_day)}"
        prev = by_day.get(day)
        if prev is None:
            by_day[day] = c
            continue
        cur_r = rank.get((c.get("geo") or {}).get("kind") or "", 0)
        prev_r = rank.get((prev.get("geo") or {}).get("kind") or "", 0)
        if cur_r > prev_r or (cur_r == prev_r and len(c.get("ports") or []) > len(prev.get("ports") or [])):
            by_day[day] = c
    return [by_day[k] for k in sorted(by_day)]


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
            return ports[0]
        title = LIST_PREFIX_RE.sub("", title).strip(" :")
    if kind == "climo":
        return str(change.get("title") or change.get("regimeId") or "").strip()
    if kind == "cyclone":
        name, _year = cyclone_name_year(change)
        return name
    if kind == "alert-on" and alert_is_amp(change):
        return alert_amp_name(change)   # même clé qu'un changement « amp » : une AMP n'est dite qu'une fois
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
    if kind == "project" or _is_amp_change(change):
        limit = PROJECT_NEAR_NM if kind == "project" else AMP_NEAR_NM
        return nm is None or nm <= limit
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
        "entity": entity,
        "facts": facts,
    }


def station_spoken_label(change: dict, lang: str = "fr") -> str:
    """Type parlé seulement — jamais le titre de jeu de données (RG5)."""
    from ici_engine import spoken_science_type  # noqa: PLC0415
    return spoken_science_type(_station_item(change), lang)


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


def dose_station_changes(changes: list[dict], span_ms: int = 0) -> list[dict]:
    """Une station qualifiée par étape, la plus proche de la route ; pas de comptage (RG5)."""
    del span_ms
    rows = [
        c for c in changes
        if str(c.get("kind") or "") == "station" and station_spoken_label(c, "fr")
    ]
    rows.sort(key=lambda c: (
        change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
        c.get("tMs") or 0,
    ))
    return rows[:1]


def change_is_speakable(change: dict) -> bool:
    kind = str(change.get("kind") or "")
    if kind in {"regime", "alert-off"}:
        return False
    if kind == "alert-on":
        body = str(change.get("fact") or change.get("title") or "").strip()
        if not body or NO_DATA_RE.search(body):
            return False      # « Aucun port d'entrée officiel n'est connu pour … » : l'absence ne se raconte pas
        if alert_is_amp(change):
            return bool(alert_amp_name(change))
        return True
    if kind == "amp":
        from ici_engine import is_fishing_amp, spoken_amp_name  # noqa: PLC0415
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
    return bool(change_place_name(change))


_EARTH_NM = 3440.065
_PORT_LEAVE_NM = 2.0
_PORT_ANCHOR_NM = 5.0
_AIR_ONLY_KEYS = frozenset({"halifax", "saint-pierre"})
_AIR_KEYS = frozenset({"cayenne", "halifax", "saint-pierre"})


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
    x, y = _air_stop_key(a), _air_stop_key(b)
    return bool(x and y and x != y and x in _AIR_KEYS and y in _AIR_KEYS)


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
    if veh in {"main", "boat"}:
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
    if _is_air_leg(a, b) or _is_air_only_stop(b):
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
    want = {"air": {"plane"}, "road": {"land"}, "sail": {"main", "boat"}}.get(
        _window_mode_name(mode), {"main", "boat"},
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


def _window_depart_ms(w: dict) -> Optional[int]:
    """Départ = premier sommet d'horloge qui quitte le port, jamais tA + jours d'escale."""
    t_a = w.get("tA")
    frm = w.get("from") or {}
    clock = w.get("clock")
    mode = _window_mode_name(str(w.get("mode") or _mode_from_vehicle(w.get("vehicle")) or "sail"))
    leave = _clock_leave_ms(
        clock, frm.get("lat"), frm.get("lon"), t_a, w.get("tB"), mode=mode,
    )
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
        "vehicle": src.get("vehicle") if src.get("vehicle") in {"plane", "land", "main"} else None,
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


def film_char_budget(seconds: Any) -> int:
    """Plafond en caractères à 15 car./s. 0 = intégral, sans plafond."""
    s = _film_seconds(seconds)
    if s <= 0:
        return 0
    return int(s * FILM_ESTIMATE_CPS)


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


def _one_amp_or_project(amp: list[dict], proj: list[dict]) -> Optional[dict]:
    """2:30 : une AMP ou un projet, gold_on puis le plus proche."""
    rows = [c for c in list(amp) + list(proj) if isinstance(c, dict)]
    if not rows:
        return None

    def gold(c: dict) -> int:
        return 0 if c.get("gold_on") in (True, 1, "1", "true", "True") else 1

    rows.sort(key=lambda c: (
        gold(c),
        change_distance_nm(c) if change_distance_nm(c) is not None else 999.0,
        c.get("tMs") or 0,
    ))
    return rows[0]


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
        one = _one_amp_or_project(amp, proj)
        if one is not None:
            extras.append(one)
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
) -> list[str]:
    """Ouverture du film (2 phrases) : qui, d'où, par la route, totaux du plan-review."""
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


def review_sentences(leg: dict | None, lang: str = "fr") -> list[str]:
    """Faits de revue fondus dans la route : plus d'annexe « À surveiller / Couloirs »."""
    if not isinstance(leg, dict):
        return []
    en = _en(lang)
    bits: list[str] = []
    season = leg.get("season") if isinstance(leg.get("season"), dict) else None
    gale = season.get("galePct") if season else None
    cyclones = season.get("cyclones") if season else None
    pack = leg.get("antiShipping") if isinstance(leg.get("antiShipping"), dict) else None
    lanes = [
        clean_spoken_label(n.strip(), lang)
        for n in ((pack or {}).get("lanes") or [])
        if isinstance(n, str) and n.strip()
    ] if pack else []
    lanes = [n for n in lanes if n and not looks_english_title(n)]

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
    for sentence in review_sentences(leg, lang):
        filtered, _dropped = filter_numbers(sentence, facts)
        sentence = (filtered or "").strip()
        if not sentence:
            continue
        if any(part and part in already for part in re.findall(r"[A-ZÀ-Ý][\w'-]{3,}", sentence)):
            # Le détroit / la mer est déjà nommé dans la route.
            if re.search(r"passe par|goes through", sentence, re.I):
                continue
        bits.append(sentence)
        if anchored is None:
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
    spoken = round_spoken_decimals(spoken)
    return scrub_spoken(spoken)


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
        nm = _fact_num(e, "nm")
        dist = spoken_distance(nm, lang) if nm is not None else ""
        if dist:
            return (
                f"On {when}, {dist} away, the marine protected area {spoken}."
                if en else
                f"Le {when}, à {dist}, l'aire marine protégée {spoken}."
            )
        return (
            f"On {when}, marine protected area: {spoken}."
            if en else
            f"Le {when}, aire marine protégée : {spoken}."
        )
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


def _departure_iso(stop: dict) -> Optional[str]:
    t = _ms(stop.get("iso"))
    if t is None:
        return None
    return _iso(t + int(float(stop.get("holdHours") or 0) * 3_600_000))


def _collapse_air_dest(
    pts: list[dict],
    dest_i: int,
) -> tuple[int, int]:
    """Regroupe Halifax / Saint-Pierre en une destination aérienne (nommée SPM si possible)."""
    last_i = dest_i
    named_i = dest_i
    k = dest_i + 1
    while k < len(pts) and _is_air_only_stop(pts[k].get("name") or ""):
        last_i = k
        key = _air_stop_key(pts[k].get("name") or "")
        if key == "saint-pierre":
            named_i = k
        elif key == "halifax" and _air_stop_key(pts[named_i].get("name") or "") != "saint-pierre":
            named_i = k
        k += 1
    if _air_stop_key(pts[dest_i].get("name") or "") == "saint-pierre":
        named_i = dest_i
    return named_i, last_i


def _windows(stops: list[dict], t0: int, t_end: int, clock: dict | None = None) -> list[dict]:
    pts = list(stops or [{"name": "Saint-Maur", "iso": _iso(t0), "filmNm": 0}])
    pts.sort(key=lambda s: float(
        s.get("filmNm") if s.get("filmNm") is not None else s.get("nm") or 0
    ))
    out: list[dict] = []

    def boat_stay_idx(idx: int) -> int:
        for j in range(idx, -1, -1):
            if not _is_air_only_stop(pts[j].get("name") or ""):
                return j
        return idx

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
        stay_idx = boat_stay_idx(stay_idx)
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
        last_i = dest_i
        named_i = dest_i
        if mode == "air" or _is_air_only_stop(probe.get("name") or ""):
            mode = "air"
            named_i, last_i = _collapse_air_dest(pts, dest_i)
        to = pts[named_i]
        last_stop = pts[last_i]
        dest_ms = _ms(to["iso"]) if to else None
        last_ms = _ms(last_stop.get("iso")) if last_stop else dest_ms
        arrived = dest_ms is not None and dest_ms <= t_end
        dest_name = (to.get("name") or "") if to else ""
        raw_b = last_ms if last_ms is not None else t_end
        t_b = min(raw_b if raw_b is not None else t_end, t_end)
        return_ms = None
        if mode == "air":
            return_ms = _air_return_ms(clock, frm, t_a, t_end)
            if return_ms is not None:
                t_b = min(max(t_b, return_ms), t_end)
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
        if mode == "air":
            stay_ready_ms = return_ms or t_b
            dest_i = last_i + 1
        else:
            stay_idx = dest_i
            stay_ready_ms = None
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


def _air_window_sentence(w: dict, *, lang: str, display_t0: str | None = None) -> str:
    """Une phrase de vol : l'équipage vole, le bateau reste au port. Aucune date inventée."""
    origin = _air_place_spoken((w.get("from") or {}).get("name") or w.get("fromName") or "", lang)
    dest = _air_place_spoken(_window_dest_name(w) or w.get("destName") or "", lang)
    if not origin or not dest:
        return ""
    en = _en(lang)
    ret = w.get("returnMs")
    when = ""
    if ret:
        when = day_month(rebase_iso(_iso(int(ret)), OFFICIAL_T0, display_t0 or OFFICIAL_T0), lang)
    if en:
        head = f"The crew flies from {origin} to {dest}; the boat waits at {origin}."
        return f"{head} Return on {when}." if when else head
    head = f"L'équipage s'envole de {origin} pour {dest} ; le bateau attend à {origin}."
    return f"{head} Retour le {when}." if when else head


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
) -> str:
    """Ouverture d'étape : date, port, cap, dest, milles, jours, vitesse — gabarit § 4."""
    dest_name = _window_dest_name(w)
    if _is_air_window(w):
        return _air_window_sentence(w, lang=lang, display_t0=display_t0)
    if not dest_name:
        return ""
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
        if gap:
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
) -> str:
    return _opening_sentence(
        w, i=i, lang=lang, display_t0=display_t0, heading_deg=heading_deg,
        review=review, n=n, include_date=include_date,
    )


def _arrival_sentence(
    stop: dict | None,
    lang: str,
    display_t0: str | None = None,
    clock: dict | None = None,
    harbor: str = "",
    chapter_i: int = 0,
) -> str:
    if not stop or not stop.get("name") or _ms(stop.get("iso")) is None:
        return ""
    en = _en(lang)
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


def _compose(windows: list[dict], buckets: list[list[dict]], *, lang: str, sea_name: str, start_name: str, live: dict | None, display_t0: str | None = None, review: dict | None = None, eta: dict | None = None) -> list[dict]:
    chapters: list[dict] = []
    cited: set[str] = set()
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
                display_t0=display_t0, review=review,
            )
            skip_depart = _is_road_window(w) and bool(film_opens)
        if _is_air_window(w):
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                review=review, n=len(windows),
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
                heading_deg=_heading_deg_at(None, depart_ms, clock=w.get("clock")),
                review=review, n=len(windows), include_date=i != 0,
            )
            if head:
                bits.append(head)
                anchored.append((head, depart_ms or w["tA"], {"role": "depart"}))
        for ev in buckets[i]:
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


def _group_changes(changes: list[dict], span_ms: int, clock: dict | None = None) -> list[dict]:
    by_kind: dict[str, list[dict]] = {}
    for change in changes:
        by_kind.setdefault(str(change.get("kind") or ""), []).append(change)
    out: list[dict] = []
    grouped_ids: set[str] = set()
    for kind, group in by_kind.items():
        if len(group) < 3:
            continue
        if kind in {"alert-on", "marina", "port", "amp", "project", "zee-enter", "coast", "climo", "station"}:
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
    changes: list[dict], t_a: int, t_b: int, *, budget: bool = True, tier: Optional[int] = None,
    clock: dict | None = None,
) -> list[dict]:
    usable = _usable_changes(changes)
    span = (t_b or 0) - (t_a or 0)
    zee = dose_zee_changes(usable, span)
    coast = dose_coast_changes(usable, span)
    amp = dose_amp_changes(usable, span)
    proj = dose_project_changes(usable, span)
    climo = dose_climo_changes(usable, span)
    stations = dose_station_changes(usable, span)
    extras = _tier_route_extras(zee, coast, amp, proj, climo, stations, tier=tier)
    rest_src = [
        c for c in usable
        if str(c.get("kind") or "") not in ROUTE_NAMING_KINDS
        and not _is_coast_source(c)
        and not _is_amp_change(c)
        and str(c.get("kind") or "") not in {"project", "climo", "station"}
        and _tier_allows_kind(str(c.get("kind") or ""), tier)
    ]
    if not budget:
        rest_src.sort(key=lambda c: (
            CHANGE_PRIORITY.get(str(c.get("kind") or ""), 9),
            c.get("tMs") or 0,
        ))
        others = rest_src[:FILM_CHAPTER_MAX_FREE]
        # ZEE, côtes, AMP, projets, climatologie et une station : hors plafond des autres faits.
        return sorted(
            extras + others if tier is not None else zee + coast + amp + proj + climo + stations + others,
            key=lambda c: (c.get("tMs") or 0, str(c.get("id") or "")),
        )
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
        color_skip = color_skip | {"station", "climo", "culture", "port"}
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
    return picked


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


def change_sentence(change: dict, lang: str = "fr") -> str:
    en = _en(lang)
    if str(change.get("id") or "").startswith("group:"):
        return _group_sentence(change, lang)
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
            nm = change_distance_nm(change)
            dist = spoken_distance(nm, lang) if nm is not None else ""
            if dist:
                return (
                    f"On {when}, {dist} away, the marine protected area {amp}."
                    if en else
                    f"Le {when}, à {dist}, l'aire marine protégée {amp}."
                )
            return (
                f"On {when}, marine protected area: {amp}."
                if en else
                f"Le {when}, aire marine protégée : {amp}."
            )
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
            shorts = [zee_cluster_short(str(m), lang) for m in members]
            shorts = [s for s in shorts if s]
            body = _join_then(shorts, lang)
            if not body:
                return ""
            # Antigua / Saint-Kitts : noms propres. espagnoles / italiennes : « les eaux … ».
            if not re.search(r"eaux|waters", body, re.I) and all(
                re.search(r"(es|ennes|aises|iques)$", s, re.I) for s in shorts
            ):
                body = f"the {body} waters" if en else f"les eaux {body}"
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
    if kind == "amp":
        from ici_engine import is_fishing_amp, spoken_amp_name  # noqa: PLC0415
        if is_fishing_amp({"name": title, "title": title, "fact": fact}):
            return ""
        name = spoken_amp_name(change_place_name(change) or title) or change_place_name(change)
        if not name or looks_english_title(name):
            return ""
        nm = change_distance_nm(change)
        dist = spoken_distance(nm, lang) if nm is not None else ""
        if dist:
            return (
                f"On {when}, {dist} away, the marine protected area {name}."
                if en else
                f"Le {when}, à {dist}, l'aire marine protégée {name}."
            )
        return f"On {when}, marine protected area: {name}." if en else f"Le {when}, aire marine protégée : {name}."
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
    return bool(re.match(r"^(Arrivée à|Arrival at)\b", text or "", re.I))


_DEPART_SENT_RE = re.compile(
    r"\bquitte\b|\bquitté\b|\bdépart vers\b|\bleaves\b|\bleft\b|\bdeparture for\b|"
    r"\bmet le cap\b|\bsails for\b|\bprend la route\b|\btakes the road\b|\bby road\b",
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
                prev_d = _parse_spoken_date(out[i - 1], lang)
                cur_d = _parse_spoken_date(out[i], lang)
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
    return [s for s in out if s]


def date_density_ok(text: str, lang: str = "fr") -> bool:
    sents = _sentences(text)
    if not sents:
        return True
    n_dates = sum(1 for s in sents if _sentence_has_date(s, lang))
    return n_dates * 2 <= len(sents) + 1


_KEEP_SENT = re.compile(
    r"arriv|Berry-Mappemonde|quitte|leaves |milles|miles|jours de mer|days at sea|"
    r"nœuds de moyenne|knots on average|amarré|moored|d'escale|stopover|"
    r"départ|departure|left |quitté|approche|approaching|avion|flies|flight|"
    r"envole|par la route|by road|attend à|waits at|aujourd|today|"
    r"expédition|expedition|escales|stops|destination|entre le |between |"
    r"à venir|still to come|le plan compte|the plan has|"
    r"eaux |waters|longe |skirts |d[ée]troit|strait|cap au |heading |haute mer|high seas|"
    r"aliz[ée]|trade wind|calmes|calms|de saison|mesur[ée]|seasonal|westerl|mistral|tramontane",
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


_AIR_OUT_RE = re.compile(
    r"s'envole|prend l'avion pour|the crew flies|flies from|flies to",
    re.I,
)
_AIR_BACK_RE = re.compile(
    r"le bateau attend|retour le|retour en avion|the boat waits|return on|return flight",
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
    dest = (
        _air_place_name(marks, "saint-pierre", "")
        or _air_place_name(marks, "halifax", "Halifax (Nouvelle-Écosse)")
    )
    full = _air_window_sentence(
        {"from": {"name": cayenne}, "fromName": cayenne, "destName": dest, "mode": "air", "vehicle": "plane"},
        lang=lang,
    )
    return full, ""


def _chapter_for_air(chapters: list[dict]) -> dict | None:
    for ch in chapters:
        if _air_stop_key(ch.get("fromName") or "") == "cayenne":
            return ch
    for ch in chapters:
        if _air_stop_key(ch.get("toName") or "") == "cayenne":
            return ch
    for ch in chapters:
        if re.search(r"cayenne", (ch.get("text") or "") + " " + (ch.get("fromName") or "") + " " + (ch.get("toName") or ""), re.I):
            return ch
    if len(chapters) >= 2:
        return chapters[-2]
    return chapters[-1] if chapters else None


def _ensure_air_sentences(
    chapters: list[dict],
    *,
    marks: list | None,
    moments: list | None,
    lang: str,
) -> list[dict]:
    """Après fusion / budget : l'aller et le retour avion restent dits s'ils existent sur la route."""
    if not chapters or not _route_has_air_pair(marks, moments):
        return chapters
    outbound, back = _air_pair_sentences(marks, lang)
    blob = " ".join(c.get("text") or "" for c in chapters)
    missing: list[str] = []
    has_air = bool(_AIR_OUT_RE.search(blob) and _AIR_BACK_RE.search(blob))
    if outbound and not has_air:
        missing.append(outbound)
    if back and back not in (outbound or "") and not _AIR_BACK_RE.search(blob):
        missing.append(back)
    if not missing:
        return chapters
    target = _chapter_for_air(chapters)
    if target is None:
        return chapters
    text = target.get("text") or ""
    sents = _sentences(text)
    close = ""
    if sents and re.search(r"aujourd|today", sents[-1] or "", re.I):
        close = sents.pop()
        text = " ".join(sents).strip()
    extra = " ".join(s for s in missing if s not in text)
    blob = f"{text} {extra}".strip()
    if close:
        blob = f"{blob} {close}".strip()
    target["text"] = speak_film_text(blob, lang)
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
    windows = _windows(packed["stops"], t0, t_end, clock)
    has_budget = _film_seconds(seconds) > 0
    budget_s = _film_seconds(seconds)
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
        selected = select_chapter_changes(
            flat, w["tA"], w["tB"], budget=has_budget, tier=tier if has_budget else None,
            clock=w.get("clock") or clock,
        )
        bits: list[str] = []
        placed: list[dict] = []

        def speak_change(change: dict) -> None:
            if change.get("kind") in {"escale", "marina"}:
                return
            if _is_air_only_stop(str(change.get("title") or "")):
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
            near = _clock_time_near_place(
                w.get("clock") or clock, place, w["tA"], w["tB"],
                (w.get("clock") or clock or {}).get("marks"),
            )
            if near is not None:
                t_ms = near
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
                display_t0=display_t0, review=review,
            )
            skip_depart = _is_road_window(w) and bool(film_opens)
        if _is_air_window(w):
            head = _depart_towards(
                w, i=i, lang=lang, display_t0=display_t0,
                review=review, n=len(windows),
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
                heading_deg=_heading_deg_at(sail_moments, depart_ms, clock=w.get("clock") or clock),
                review=review, n=len(windows), include_date=i != 0,
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
                harbor=harbor, chapter_i=i,
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
    # RG8 : intégral sans plafond — on ne coupe plus à FILM_FREE_MAX_WORDS.
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
    _ensure_air_sentences(chapters, marks=marks, moments=moments, lang=lang)
    chars = script_chars(chapters)
    return {
        "chapters": chapters,
        "source": "rules",
        "chars": chars,
        "targetSeconds": budget_s,
        "estimatedSeconds": film_estimated_seconds(chars),
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
    windows = _windows(packed["stops"], t0, t_end, clock)

    def compose(evs: list[dict]) -> list[dict]:
        return _compose(windows, _assign(evs, windows), lang=lang, sea_name=sea_name, start_name=start_name, live=live, display_t0=display_t0, review=review, eta=eta)

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
    _ensure_air_sentences(
        chapters, marks=marks, moments=_journal_moments(journal), lang=lang,
    )
    chars = script_chars(chapters)
    return {
        "chapters": chapters,
        "source": "rules",
        "chars": chars,
        "targetSeconds": _film_seconds(seconds),
        "estimatedSeconds": film_estimated_seconds(chars),
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
    try:
        from moment_journal import read_moments  # noqa: PLC0415
        moments = read_moments(OFFICIAL_VOYAGE_ID)
    except Exception:
        moments = []
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
                style="written", cascade=cascade, want_write=True, now_ms=now_ms,
                review=review, eta=eta,
            )
            out[lang] = {"hasWritten": plan.get("hasWritten"), "chars": plan.get("chars"), "source": plan.get("source")}
    return {"voyageId": vid, "status": "ready", "langs": out}

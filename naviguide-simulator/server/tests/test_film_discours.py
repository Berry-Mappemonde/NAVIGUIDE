"""Lot RG10 — recette automatique du discours (revue du 28 sept., C1–C6 / D1–D4).

Lit le texte FINAL du film (pas un morceau). Chaque règle, en cas d'échec,
signale la phrase fautive. On ne corrige pas la règle pour passer.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pytest

from film_script import (
    _ms,
    _sentence_has_date,
    _sentences,
    build_raw_from_moments,
    date_density_ok,
    film_has_forbidden,
)
from tests.test_film_script import CLOCK, JOURNAL, LIVE, MOMENTS, NOW_MS, _rg6_review

# Chemin du poste, lu à l'import : le fixture autouse de conftest pose ensuite
# un dossier temporaire dans NAVIGUIDE_OFFICIAL_STORE_DIR.
_POSTE_STORE_AT_IMPORT = (os.environ.get("NAVIGUIDE_OFFICIAL_STORE_DIR") or "").strip()
_POSTE_CACHE = Path.home() / ".cache" / "naviguide" / "voyage-store"

# Transcription § 1 de docs/FILM_DISCOURS_ETAT_2026-09-28.md — film servi le
# 28 sept. (avant RG6). Constante de test, jamais écrite dans un stock.
REVUE_28_SEPT = """
L'expédition Berry-Mappemonde a quitté Saint-Maur le 15 mai 2026. Départ vers La Rochelle. Arrivée à La Rochelle le 15 mai, 3 jours à quai.
À partir du 15 mai, 9 stations scientifiques croisées. Le 15 mai, aire marine protégée à portée : Pertuis Charentais - Pétoncles - Center Pertuis Breton deposit. Puis, le 18 mai, départ vers Ajaccio (Corse). Le 25 mai, approche d'Ajaccio. Arrivée à Ajaccio (Corse) le 26 mai, 3 jours à quai.
Ensuite, le 29 mai, départ vers Fort-de-France (Martinique). À partir du 31 mai, 11 stations scientifiques croisées. Le 26 juin, approche de Fort-de-France. Le 27 juin, à portée de The Careenage. Arrivée à Fort-de-France (Martinique) le 28 juin, 3 jours à quai. À surveiller. Couloirs : détroit de Gibraltar, Méditerranée occidentale. La jambe compte 5 153 milles nautiques.
Plus loin, le 1er juillet, départ vers Pointe-à-Pitre (Guadeloupe). À partir du 1er juillet, 3 zones économiques exclusives traversées. Le 2 juillet, approche de Pointe-à-Pitre. Arrivée à Pointe-à-Pitre (Guadeloupe) le 2 juillet, 3 jours à quai.
De là, le 5 juillet, départ vers Gustavia (Saint-Barthélemy). À partir du 5 juillet, 4 zones économiques exclusives traversées. Le 6 juillet, approche de Gustavia. Arrivée à Gustavia (Saint-Barthélemy) le 6 juillet, 3 jours à quai.
Sur la route, le 9 juillet, départ vers Marigot (Saint-Martin). Le 9 juillet, entrée dans les eaux françaises. Arrivée à Marigot (Saint-Martin) le 9 juillet, 3 jours à quai.
À la jambe suivante, le 12 juillet, départ vers Cayenne (Guyane). À partir du 12 juillet, 7 zones économiques exclusives traversées. Le 19 juillet, approche de Cayenne. Arrivée à Cayenne (Guyane) le 19 juillet, 3 jours à quai.
Puis, le 22 juillet, départ vers Saint-Pierre (Saint-Pierre-et-Miquelon). Le 23 juillet, entrée dans les eaux canadiennes. Le 25 juillet, approche de Saint-Pierre. Arrivée à Saint-Pierre (Saint-Pierre-et-Miquelon) le 25 juillet, 3 jours à quai. L'équipage prend l'avion pour Halifax (Nouvelle-Écosse). Retour en avion vers Cayenne (Guyane).
Ensuite, le 28 juillet, départ vers Papeete (Polynésie française). À partir du 28 juillet, 8 zones économiques exclusives traversées. Le 5 septembre, approche de Papeete. Le 6 septembre, à portée de Petite marina. Arrivée à Papeete (Polynésie française) le 8 septembre, 3 jours à quai. À surveiller. Couloirs : Caraïbe ouest, Atlantique nord. La jambe compte 7 007 milles nautiques.
Plus loin, le 11 septembre, départ vers Mata-Utu (Wallis-et-Futuna). À partir du 13 septembre, 5 zones économiques exclusives traversées. Le 18 septembre, approche de Mata-Utu. Arrivée à Mata-Utu (Wallis-et-Futuna) le 19 septembre, 3 jours à quai.
De là, le 22 septembre, départ vers Nouméa (Nouvelle-Calédonie). Le 22 septembre, à portée de de Fineveke. À partir du 24 septembre, 4 zones économiques exclusives traversées. Aujourd'hui, le bateau est en mer, à 232 milles nautiques de Nouméa (Nouvelle-Calédonie).
"""

COUNT_RE = re.compile(
    r"\b(\d+|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze)\s+"
    r"(stations?|zones?)\b",
    re.I,
)
EN_TITLE_MOTIFS = re.compile(
    r"\b(deposit|licence|license|center|fishing|bans?|prohibition|careenage)\b",
    re.I,
)
THE_TITLE_RE = re.compile(r"\bThe\s+[A-Z]")
DE_DE_RE = re.compile(r"\bde de\b", re.I)
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9’'-]+")
OPEN_RE = re.compile(
    r"quitte|quitté|leaves|left |s'envole|flies |par la route|by road|"
    r"expédition|expedition",
    re.I,
)
ARRIVAL_RE = re.compile(r"Arrivée à|Arrival at", re.I)
TODAY_RE = re.compile(r"Aujourd|Today,", re.I)
AIR_RE = re.compile(
    r"s'envole|flies from|the crew flies|prend l'avion|return flight|attend à",
    re.I,
)
MAX_WORDS = 30


@dataclass(frozen=True)
class Fault:
    rule: str
    sentence: str


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text or "")


def _sentence_at(text: str, idx: int) -> str:
    sents = _sentences(text)
    if not sents:
        return text or ""
    pos = 0
    for sent in sents:
        loc = text.find(sent, pos)
        if loc < 0:
            loc = pos
        end = loc + len(sent)
        if loc <= idx < end or sent is sents[-1]:
            return sent
        pos = end
    return sents[0]


def _date_burst_sentence(text: str, lang: str) -> str | None:
    sents = _sentences(text)
    if not sents or date_density_ok(text, lang):
        return None
    n_dates = 0
    for i, sent in enumerate(sents):
        dated = _sentence_has_date(sent, lang)
        if dated and i > 0 and _sentence_has_date(sents[i - 1], lang):
            return sent
        if dated:
            n_dates += 1
            if n_dates * 2 > len(sents) + 1:
                return sent
    dated = [s for s in sents if _sentence_has_date(s, lang)]
    return dated[-1] if dated else sents[0]


def list_faults(text: str, lang: str = "fr") -> list[Fault]:
    """Règles C3–C4, C2, D2, longueur : une Fault par phrase fautive."""
    out: list[Fault] = []
    fr = not str(lang or "").lower().startswith("en")
    for sent in _sentences(text):
        if film_has_forbidden(sent):
            out.append(Fault("interdit", sent))
        if DE_DE_RE.search(sent):
            out.append(Fault("de de", sent))
        if fr and (EN_TITLE_MOTIFS.search(sent) or THE_TITLE_RE.search(sent)):
            out.append(Fault("titre anglais", sent))
        if COUNT_RE.search(sent):
            out.append(Fault("comptage", sent))
        if len(_words(sent)) > MAX_WORDS:
            out.append(Fault("trop longue", sent))
    burst = _date_burst_sentence(text, lang)
    if burst:
        out.append(Fault("dates rafale", burst))
    return out


def _structure_fault(ch: dict, lang: str) -> str | None:
    """Ouverture, puis route (si le chapitre en a), puis escale — dans cet ordre."""
    text = ch.get("text") or ""
    sents = _sentences(text)
    if not sents:
        return "(chapitre vide)"
    if AIR_RE.search(text):
        return None
    open_i = next((i for i, s in enumerate(sents) if OPEN_RE.search(s)), None)
    if open_i is None:
        return sents[0]
    close_i = next(
        (
            i for i, s in enumerate(sents)
            if ARRIVAL_RE.search(s) or TODAY_RE.search(s)
        ),
        None,
    )
    if close_i is None:
        return sents[0]
    if close_i < open_i:
        return sents[close_i]
    return None


def _anchor_fault(ch: dict) -> str | None:
    text = ch.get("text") or ""
    last_idx, last_t = -1, None
    for anc in ch.get("anchors") or []:
        idx = anc.get("charIdx")
        t = _ms(anc.get("t"))
        sent = _sentence_at(text, int(idx) if idx is not None else 0)
        if not isinstance(idx, int) or idx < 0:
            return sent
        if idx < last_idx:
            return sent
        if last_t is not None and t is not None and t < last_t:
            return sent
        last_idx = idx
        if t is not None:
            last_t = t
    return None


def list_plan_faults(plan: dict, lang: str = "fr") -> list[Fault]:
    out: list[Fault] = []
    for ch in plan.get("chapters") or []:
        text = ch.get("text") or ""
        out.extend(list_faults(text, lang))
        struct = _structure_fault(ch, lang)
        if struct:
            out.append(Fault("structure", struct))
        anc = _anchor_fault(ch)
        if anc:
            out.append(Fault("ancres", anc))
    return out


def assert_discours_ok(plan_or_text, lang: str = "fr") -> None:
    if isinstance(plan_or_text, str):
        faults = list_faults(plan_or_text, lang)
    else:
        faults = list_plan_faults(plan_or_text, lang)
    assert not faults, faults[0].sentence


def _moments_plan(lang: str) -> dict:
    return build_raw_from_moments(
        CLOCK, CLOCK["marks"], LIVE, {**JOURNAL, **MOMENTS},
        lang=lang, seconds=0, now_ms=NOW_MS, review=_rg6_review(),
    )


def _plan_from_film_doc(doc: dict, lang: str) -> dict | None:
    body = doc.get("payload") if isinstance(doc.get("payload"), dict) else doc
    if not isinstance(body, dict):
        return None
    lg = (lang or "fr")[:2].lower()
    variants = body.get("variants") if isinstance(body.get("variants"), dict) else {}
    by_secs = variants.get(lg) or {}
    plan = body.get(lg) or body.get("default") or body.get("fr")
    if not (isinstance(plan, dict) and (plan.get("chapters") or [])):
        plan = None
        if isinstance(by_secs, dict):
            for key in ("150", "180", "0"):
                cand = by_secs.get(key)
                if isinstance(cand, dict) and (cand.get("chapters") or []):
                    plan = cand
                    break
    if isinstance(plan, dict) and (plan.get("chapters") or []):
        return plan
    return None


def _iter_poste_plans(doc: dict, lang: str) -> list[tuple[str, dict]]:
    """Toutes les variantes stockées (2:30 / 3:00 / intégral), plus le défaut."""
    body = doc.get("payload") if isinstance(doc.get("payload"), dict) else doc
    if not isinstance(body, dict):
        return []
    lg = (lang or "fr")[:2].lower()
    out: list[tuple[str, dict]] = []
    seen: set[int] = set()
    default = body.get(lg) or body.get("default") or body.get("fr")
    if isinstance(default, dict) and (default.get("chapters") or []):
        out.append(("default", default))
        seen.add(id(default))
    variants = body.get("variants") if isinstance(body.get("variants"), dict) else {}
    by_secs = variants.get(lg) or {}
    if isinstance(by_secs, dict):
        for key, plan in by_secs.items():
            if isinstance(plan, dict) and (plan.get("chapters") or []) and id(plan) not in seen:
                out.append((str(key), plan))
                seen.add(id(plan))
    return out


def _newest_film_json(root: Path) -> Path | None:
    if not root.is_dir():
        return None
    found = [p for p in root.glob("*/film.json") if p.is_file()]
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def _try_poste_api(lang: str) -> dict | None:
    raw = (os.environ.get("NAVIGUIDE_POSTE_API") or "http://127.0.0.1:8010").strip()
    host = urlparse(raw).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        return None
    url = f"{raw.rstrip('/')}/voyage/official/film?lang={lang}&style=raw"
    try:
        with urlopen(Request(url), timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("status") == "preparing":
        return None
    if not (data.get("chapters") or []):
        return None
    return data


def load_poste_film(lang: str = "fr") -> tuple[dict | None, str]:
    roots: list[Path] = []
    if _POSTE_STORE_AT_IMPORT:
        roots.append(Path(_POSTE_STORE_AT_IMPORT))
    if _POSTE_CACHE not in roots:
        roots.append(_POSTE_CACHE)
    for root in roots:
        dest = _newest_film_json(root)
        if dest is None:
            continue
        try:
            doc = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        plan = _plan_from_film_doc(doc if isinstance(doc, dict) else {}, lang)
        if plan:
            return plan, str(dest)
    api = _try_poste_api(lang)
    if api:
        return api, "api:127.0.0.1:8010"
    return None, ""


# ── règles isolées : le message est la phrase ───────────────────────────────


def test_interdit_jambe():
    with pytest.raises(AssertionError, match="La jambe compte"):
        assert_discours_ok("La jambe compte 5 153 milles nautiques.", "fr")


def test_interdit_couloirs_et_surveiller():
    with pytest.raises(AssertionError, match="À surveiller"):
        assert_discours_ok("À surveiller.", "fr")
    with pytest.raises(AssertionError, match="Couloirs"):
        assert_discours_ok("Couloirs : Caraïbe ouest.", "fr")


def test_interdit_a_portee_de():
    with pytest.raises(AssertionError, match="à portée de"):
        assert_discours_ok("Le 27 juin, à portée de The Careenage.", "fr")


def test_de_de():
    with pytest.raises(AssertionError, match="de de"):
        assert_discours_ok("Le 22 septembre, à portée de de Fineveke.", "fr")


def test_titre_anglais_deposit_center():
    sent = (
        "Le 15 mai, aire marine protégée à portée : Pertuis Charentais - "
        "Pétoncles - Center Pertuis Breton deposit."
    )
    with pytest.raises(AssertionError, match="deposit"):
        assert_discours_ok(sent, "fr")


def test_comptage_sans_nom():
    with pytest.raises(AssertionError, match="9 stations"):
        assert_discours_ok("À partir du 15 mai, 9 stations scientifiques croisées.", "fr")
    with pytest.raises(AssertionError, match="3 zones"):
        assert_discours_ok("À partir du 1er juillet, 3 zones économiques exclusives traversées.", "fr")


def test_dates_rafale():
    blob = (
        "Le 1er juillet, départ vers Pointe-à-Pitre. "
        "À partir du 1er juillet, encore une date. "
        "Le 2 juillet, approche de Pointe-à-Pitre. "
        "Arrivée à Pointe-à-Pitre le 2 juillet."
    )
    with pytest.raises(AssertionError, match="juillet"):
        assert_discours_ok(blob, "fr")


def test_phrase_trop_longue():
    sent = (
        "Le quinze mai Berry-Mappemonde quitte La Rochelle cap au sud-ouest "
        "pour Ajaccio avec encore trop de mots ajoutés ici pour dépasser "
        "clairement la limite parlée de trente mots dans cette unique phrase."
    )
    assert len(_words(sent)) > MAX_WORDS
    with pytest.raises(AssertionError, match="Berry-Mappemonde"):
        assert_discours_ok(sent + ".", "fr")


def test_ancres_doivent_etre_chronologiques():
    plan = {
        "chapters": [{
            "fromName": "La Rochelle", "toName": "Ajaccio",
            "text": "Le 15 mai, départ. Puis, les eaux. Arrivée à Ajaccio le 26 mai.",
            "anchors": [
                {"charIdx": 0, "t": "2026-05-16T00:00:00Z"},
                {"charIdx": 20, "t": "2026-05-15T00:00:00Z"},
            ],
        }],
    }
    with pytest.raises(AssertionError):
        assert_discours_ok(plan, "fr")


def test_phrase_propre_passe():
    assert_discours_ok(
        "Le 15 mai, Berry-Mappemonde quitte La Rochelle pour Ajaccio. "
        "Puis, les eaux espagnoles. Arrivée à Ajaccio le 26 mai.",
        "fr",
    )


# ── film du 28 sept. (§ 1) : les règles le refusent ─────────────────────────


def test_revue_28_sept_est_refusee():
    """Le film transcrit le 28 sept. (avant RG6) viole les règles C/D."""
    faults = list_faults(REVUE_28_SEPT, "fr")
    assert faults, "le film du 28 sept. doit encore être refusé"
    sentences = [f.sentence for f in faults]
    assert any("jambe" in s.lower() for s in sentences)
    assert any("de de" in s.lower() for s in sentences)
    assert any("stations" in s.lower() for s in sentences)
    assert any("deposit" in s.lower() or "Center" in s for s in sentences)
    with pytest.raises(AssertionError) as err:
        assert_discours_ok(REVUE_28_SEPT, "fr")
    assert any(s in str(err.value) for s in sentences)


# ── film après RG6 : moments d'exemple FR et EN ─────────────────────────────


def test_moments_fr_passe_apres_rg6():
    plan = _moments_plan("fr")
    assert plan.get("chapters")
    assert_discours_ok(plan, "fr")


def test_moments_en_passe_apres_rg6():
    plan = _moments_plan("en")
    assert plan.get("chapters")
    assert_discours_ok(plan, "en")


# ── stock du poste (ignoré en CI / si absent) ───────────────────────────────


@pytest.mark.poste
def test_poste_stock_discours():
    """Même règles sur le film réellement stocké sur le poste."""
    if os.environ.get("CI"):
        pytest.skip("poste : stock du poste absent en CI")
    plan, src = load_poste_film("fr")
    if plan is None:
        pytest.skip("poste : NAVIGUIDE_OFFICIAL_STORE_DIR / API absents")
    doc = None
    dest = Path(src) if src and not src.startswith("api:") else None
    if dest and dest.is_file():
        try:
            doc = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = None
    plans = _iter_poste_plans(doc, "fr") if isinstance(doc, dict) else [("default", plan)]
    if not plans:
        plans = [("default", plan)]
    total = 0
    print(f"poste FR source={src}", flush=True)
    for label, one in plans:
        faults = list_plan_faults(one, "fr")
        n_sents = sum(len(_sentences(ch.get("text") or "")) for ch in one.get("chapters") or [])
        print(
            f"  variante {label}: chapitres={len(one.get('chapters') or [])} "
            f"phrases={n_sents} fautives={len(faults)}",
            flush=True,
        )
        for fault in faults:
            print(f"    [{fault.rule}] {fault.sentence}", flush=True)
        total += len(faults)
        assert not faults, faults[0].sentence
    print(f"poste FR total fautives={total}", flush=True)
    en, _ = load_poste_film("en")
    if en:
        en_faults = list_plan_faults(en, "en")
        print(f"poste EN fautives={len(en_faults)}", flush=True)
        assert not en_faults, en_faults[0].sentence

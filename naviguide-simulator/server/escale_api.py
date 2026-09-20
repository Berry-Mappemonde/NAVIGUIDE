"""Fiche d'escale (lot C, plan général §1.9).

Pour une escale (nom, position) : ce qu'un équipage veut savoir en arrivant,
**en listes de faits** — chaque ligne a un nom, une position, une distance,
et quand OSM / BI le disent un site et un téléphone :

- amarrage : marinas, capitaineries (BI), ports WPI, mouillages OSM ;
- services : carburant, eau potable, électricité à quai (OSM) ;
- avitaillement : supermarchés, épiceries, laveries (OSM) ;
- entretien : chantiers, grues, cales de mise à l'eau, accastillage (OSM) ;
- tourisme : sites, musées, points de vue, offices de tourisme (OSM) ;
- formalités : ZEE, ports d'entrée officiels (BI), aires marines protégées ;
- autour : projets et fiches science Blue Intelligence.

La **rédaction** (un paragraphe de présentation, trois phrases) passe par
`cascade_text(tier="fast")` (lot L2 / U5) à partir de ces listes seulement,
filtrée comme les cartes ; sans LLM, les listes seules. Rien n'est inventé :
une section vide n'est pas envoyée. Cache SQLite 7 jours (`pearl_store.kv`,
ns « escale »). Chaque paragraphe porte `source`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from admin_guard import rate_limited
from ici_engine import fill_dossier, haversine_nm
from ici_layers import _overpass_elements, _overpass_latlon
from story_cascade import cascade_text, tidy_story

log = logging.getLogger("naviguide-simulator.escale")

router = APIRouter()

ESCALE_TTL_S = 7 * 86400.0
OSM_RADIUS_M = 6000          # ~3.2 nm around the stop: the town, not the coast
BAG_RADIUS_NM = 15.0
MAX_PER_SECTION = 6
PARAGRAPH_SENTENCES = 3
PARAGRAPH_CHARS = 520

# tag → (section, subsection)
_OSM_TAGS: tuple[tuple[str, str, str, str], ...] = (
    ("amenity", "fuel", "services", "fuel"),
    ("waterway", "fuel", "services", "fuel"),
    ("seamark:small_craft_facility:category", "fuel", "services", "fuel"),
    ("amenity", "drinking_water", "services", "water"),
    ("seamark:small_craft_facility:category", "water", "services", "water"),
    ("seamark:small_craft_facility:category", "electricity", "services", "electricity"),
    ("shop", "supermarket", "supplies", "supermarkets"),
    ("shop", "convenience", "supplies", "supermarkets"),
    ("shop", "laundry", "supplies", "laundry"),
    ("shop", "boat", "maintenance", "chandlery"),
    ("shop", "chandler", "maintenance", "chandlery"),
    ("shop", "chandlery", "maintenance", "chandlery"),
    ("waterway", "boatyard", "maintenance", "boatyards"),
    ("seamark:small_craft_facility:category", "boatyard", "maintenance", "boatyards"),
    ("man_made", "crane", "maintenance", "cranes"),
    ("seamark:small_craft_facility:category", "boat_hoist", "maintenance", "cranes"),
    ("leisure", "slipway", "maintenance", "slipways"),
    ("seamark:small_craft_facility:category", "slipway", "maintenance", "slipways"),
    ("tourism", "attraction", "tourism", "sights"),
    ("tourism", "museum", "tourism", "museums"),
    ("tourism", "viewpoint", "tourism", "viewpoints"),
    ("tourism", "information", "tourism", "information"),
    ("amenity", "pharmacy", "health", "pharmacies"),
    ("amenity", "hospital", "health", "hospitals"),
)

SECTION_ORDER = ("mooring", "services", "supplies", "maintenance", "tourism", "health", "formalities", "around")


def osm_query(lat: float, lon: float, radius_m: int = OSM_RADIUS_M) -> str:
    around = f"(around:{int(radius_m)},{lat:.5f},{lon:.5f})"
    seen = set()
    parts = []
    for k, v, _s, _sub in _OSM_TAGS:
        if (k, v) in seen:
            continue
        seen.add((k, v))
        parts.append(f'nwr["{k}"="{v}"]{around};')
    return f"[out:json][timeout:25];({''.join(parts)});out center tags;"


def _website(tags: dict) -> str | None:
    for k in ("website", "contact:website", "url", "seamark:information"):
        v = tags.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v[:300]
    return None


def _phone(tags: dict) -> str | None:
    for k in ("phone", "contact:phone", "seamark:contact:phone"):
        v = tags.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()[:40]
    return None


def classify_osm(elements: list, lat0: float, lon0: float) -> dict[str, dict[str, list[dict]]]:
    """Overpass elements → { section: { subsection: [items] } }, nearest first, capped."""
    out: dict[str, dict[str, list[dict]]] = {}
    seen: set[tuple] = set()
    for el in elements or []:
        tags = el.get("tags") or {}
        pos = _overpass_latlon(el)
        if pos is None:
            continue
        lat, lon = pos
        for k, v, section, sub in _OSM_TAGS:
            if tags.get(k) != v:
                continue
            name = tags.get("name") or tags.get("brand") or tags.get("operator")
            if not name and section in ("tourism", "supplies", "health"):
                continue  # an unnamed shop tells nothing
            label = str(name or v.replace("_", " "))[:120]
            key = (section, sub, round(lat, 4), round(lon, 4), label)
            if key in seen:
                continue
            seen.add(key)
            item = {
                "name": label,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "nm": round(haversine_nm(lat0, lon0, lat, lon), 2),
                "source": "osm-overpass",
            }
            url = _website(tags)
            if url:
                item["url"] = url
            phone = _phone(tags)
            if phone:
                item["phone"] = phone
            if tags.get("opening_hours"):
                item["hours"] = str(tags["opening_hours"])[:80]
            if section == "services" and sub == "fuel":
                kinds = [f for f in ("diesel", "gasoline") if tags.get(f"fuel:{f}") == "yes"]
                if kinds:
                    item["fuel"] = kinds
            out.setdefault(section, {}).setdefault(sub, []).append(item)
            break
    for section in out.values():
        for sub, items in section.items():
            items.sort(key=lambda x: x["nm"])
            # Named places first; anonymous taps / cranes / slipways: the two nearest only.
            named = [i for i in items if i["name"] not in {v.replace("_", " ") for _k, v, _s, _sub in _OSM_TAGS}]
            anon = [i for i in items if i not in named][:2]
            items[:] = sorted(named + anon, key=lambda x: x["nm"])[:MAX_PER_SECTION]
    return out


def _slim(items: list | None, keep: tuple[str, ...] = ("name", "lat", "lon", "nm", "url", "visit_url", "manager_url", "gold_on", "phone", "type", "kind", "source")) -> list[dict]:
    out = []
    for it in items or []:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        out.append({k: it[k] for k in keep if k in it and it[k] is not None})
    return out[:MAX_PER_SECTION]


def sections_from_bag(bag: dict) -> dict[str, Any]:
    nearby = bag.get("nearby") or {}
    sections: dict[str, Any] = {}
    mooring = {
        "marinas": _slim(nearby.get("marinas")),
        "capitaineries": _slim(nearby.get("capitaineries")),
        "wpi": _slim(nearby.get("wpi")),
        "anchorages": _slim(nearby.get("anchorages")),
    }
    mooring = {k: v for k, v in mooring.items() if v}
    if mooring:
        sections["mooring"] = mooring
    zee = bag.get("zee") or {}
    formalities = {
        "zee": {k: zee.get(k) for k in ("name", "mrgid", "territory", "gold", "country") if zee.get(k) is not None} if zee else None,
        "poe": _slim(bag.get("poe")),
        "amp": _slim(bag.get("amp")),
    }
    formalities = {k: v for k, v in formalities.items() if v}
    if formalities:
        sections["formalities"] = formalities
    science = bag.get("science")
    around = {
        "projects": _slim(bag.get("projects")),
        "science": _slim(science.get("nearby") if isinstance(science, dict) else science),
    }
    around = {k: v for k, v in around.items() if v}
    if around:
        sections["around"] = around
    return sections


def merge_sections(base: dict, osm: dict) -> dict:
    merged = {k: dict(v) if isinstance(v, dict) else v for k, v in base.items()}
    for section, subs in osm.items():
        merged.setdefault(section, {})
        for sub, items in subs.items():
            if items:
                merged[section][sub] = items
    return {k: merged[k] for k in SECTION_ORDER if k in merged and merged[k]}


def _paragraph_prompt(name: str, sections: dict, lang: str) -> tuple[str, str]:
    en = (lang or "fr").lower().startswith("en")
    system = (
        "You present a port of call to a sailing crew arriving there, from JSON lists already collected "
        "(marinas, harbour master, fuel, water, shops, boatyards, sights, port of entry, protected areas). "
        "THREE plain sentences at most: what is there for the boat, what is there for the crew, what to know "
        "for formalities. Name only places present in the JSON, never a figure not in it. "
        "No title, no list, no bold, nothing about the machinery or the data sources. Thinking OFF."
        if en else
        "Tu présentes une escale à un équipage de voilier qui y arrive, à partir de listes JSON déjà collectées "
        "(marinas, capitainerie, carburant, eau, commerces, chantiers, sites, port d’entrée, aires protégées). "
        "TROIS phrases simples au plus : ce qu’il y a pour le bateau, ce qu’il y a pour l’équipage, ce qu’il faut "
        "savoir pour les formalités. Ne nomme que des lieux présents dans le JSON, jamais un chiffre absent. "
        "Ni titre, ni liste, ni gras, rien sur la machinerie ni sur les sources. Thinking OFF."
    )
    slim = {}
    for section, subs in sections.items():
        slim[section] = {}
        for sub, items in subs.items():
            if isinstance(items, list):
                slim[section][sub] = [{k: it.get(k) for k in ("name", "nm") if it.get(k) is not None} for it in items[:4]]
            else:
                slim[section][sub] = items
    user = f"{'Port of call' if en else 'Escale'} : {name}\nJSON :\n{json.dumps(slim, ensure_ascii=False, default=str)}"
    return system, user


async def write_paragraph(name: str, sections: dict, lang: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    if not sections:
        return {"status": "empty", "text": None, "engine": None, "source": None}
    system, user = _paragraph_prompt(name, sections, lang)
    try:
        text, source = await cascade_text(system, user, client, tier="fast")
    except Exception as exc:
        return {"status": "failed", "text": None, "engine": None, "source": None, "reason": str(exc)[:160]}
    tidy = tidy_story(text, None, max_sentences=PARAGRAPH_SENTENCES, max_chars=PARAGRAPH_CHARS)
    if not tidy:
        return {"status": "failed", "text": None, "engine": source, "source": source, "reason": "only machinery"}
    return {"status": "ready", "text": tidy, "engine": source, "source": source}


def escale_key(name: str, lat: float, lon: float, lang: str) -> str:
    return f"{name.strip().lower()[:60]}|{lat:.2f}|{lon:.2f}|{(lang or 'fr')[:2]}"


_TOURISM_SUBS = ("sights", "museums", "viewpoints")


def tourism_highlights_from_cache(
    name: str,
    lat: float | None,
    lon: float | None,
    lang: str = "fr",
    limit: int = 2,
) -> list[dict]:
    """Deux lieux remarquables de la section tourisme, si la fiche est en cache.

    Lecture seule — pas de réseau. Champ inconnu = liste vide, jamais inventé.
    """
    if not name or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return []
    try:
        import pearl_store  # noqa: PLC0415
    except Exception:
        return []
    langs = [(lang or "fr")[:2]]
    other = "en" if langs[0] == "fr" else "fr"
    if other not in langs:
        langs.append(other)
    hit = None
    for lg in langs:
        hit = pearl_store.kv_get("escale", escale_key(name, float(lat), float(lon), lg), ESCALE_TTL_S)
        if hit:
            break
    if not hit:
        return []
    tourism = ((hit.get("value") or {}).get("sections") or {}).get("tourism") or {}
    if not isinstance(tourism, dict):
        return []
    items: list[dict] = []
    for sub in _TOURISM_SUBS:
        for it in tourism.get(sub) or []:
            if isinstance(it, dict) and it.get("name"):
                items.append({**it, "subsection": sub})
    items.sort(key=lambda x: (not isinstance(x.get("nm"), (int, float)), x.get("nm") or 0))
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        label = str(it["name"]).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        row = {"name": label, "kind": it.get("subsection")}
        for k in ("lat", "lon", "nm", "url"):
            if it.get(k) is not None:
                row[k] = it[k]
        out.append(row)
        if len(out) >= limit:
            break
    return out


async def build_escale(name: str, lat: float, lon: float, lang: str = "fr",
                       client: httpx.AsyncClient | None = None, *, paragraph: bool = True) -> dict[str, Any]:
    own = client is None
    http = client or httpx.AsyncClient()
    try:
        bag_t = asyncio.create_task(fill_dossier(lat, lon, BAG_RADIUS_NM, client=http, thin=True, rich=True))
        osm_t = asyncio.create_task(_overpass_elements(http, osm_query(lat, lon)))
        bag, (elements, osm_err) = await asyncio.gather(bag_t, osm_t)
        sections = merge_sections(sections_from_bag(bag), classify_osm(elements, lat, lon))
        para = await write_paragraph(name, sections, lang, http) if paragraph else {"status": "disabled", "text": None, "engine": None, "source": None}
        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "lang": lang,
            "sections": sections,
            "paragraph": para,
            "sources": {
                "osm": "osm-overpass" if not osm_err else osm_err,
                "bi": (bag.get("sources") or {}).get("bi"),
                "zee": (bag.get("sources") or {}).get("zee"),
            },
            "builtAt": time.time(),
        }
    finally:
        if own:
            await http.aclose()


_escale_limited = rate_limited("escale", 20, 60.0, global_limit=120)


@router.get("/escale", dependencies=[Depends(_escale_limited)])
async def get_escale(
    name: str = Query(..., min_length=1, max_length=120),
    lat: float = Query(...),
    lon: float = Query(...),
    lang: str = Query("fr"),
    refresh: bool = Query(False),
):
    """La fiche d'une escale : listes de faits + un paragraphe (cascade LLM), en cache 7 j."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(400, "lat/lon hors limites")
    import pearl_store  # noqa: PLC0415
    key = escale_key(name, lat, lon, lang)
    if not refresh:
        hit = pearl_store.kv_get("escale", key, ESCALE_TTL_S)
        if hit:
            return {**hit["value"], "cached": True}
    else:
        # A refresh also re-collects the stop's own pearl (its ZEE, its layers).
        from ici_engine import thin_cache_drop, thin_cache_key  # noqa: PLC0415
        thin_cache_drop(thin_cache_key(lat, lon, BAG_RADIUS_NM))
    fiche = await build_escale(name, lat, lon, lang)
    # Only a fiche with something in it is worth keeping; a failed paragraph
    # is retried on the next request that finds the cache stale.
    if fiche["sections"]:
        pearl_store.kv_put("escale", key, fiche)
    return {**fiche, "cached": False}

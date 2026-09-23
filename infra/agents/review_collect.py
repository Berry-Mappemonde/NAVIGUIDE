#!/usr/bin/env python3
"""Collecte la revue du porteur sur une pile de PR (lot W2).

Pour chaque PR de la pile, on lit :
  - les cases de la rubrique « Recette » du corps de la PR : `- [x]` = vu et OK,
    `- [ ]` = pas vérifié (ou pas OK sans commentaire) ;
  - les commentaires du porteur qui commencent par « KO » / « NON » / « ❌ »
    (« KO : écran, ce que je vois, ce que je voulais »), avec leurs images ;
  - les captures prises par l'agent (`docs/recette/<lot>/…jpg`, sur la branche).

Sortie : `infra/agents/review-<date>.json` (lu par plan_corrections.py) et
`review-<date>.md` (résumé lisible). Les images sont téléchargées dans
`infra/agents/review-<date>/pr-<n>/`. Lecture anonyme (dépôt public) ; le jeton
GitHub, s'il existe, évite la limite de débit. Bibliothèque standard seulement.

Usage :
    python3 infra/agents/review_collect.py                  # les PR de state.json
    python3 infra/agents/review_collect.py --prs 250 251    # des PR précises
    python3 infra/agents/review_collect.py --no-images      # sans télécharger les images
    python3 infra/agents/review_collect.py --out /tmp/rev   # dossier de sortie
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_DIR = Path(os.environ.get("BIM_STATE_DIR", str(HERE)))
STATE_JSON = STATE_DIR / "state.json"
REPO = os.environ.get("BIM_REPO", "Berry-Mappemonde/Blue-Intelligence")
GITHUB_API = "https://api.github.com"

HEADING_RE = re.compile(r"^\s{0,3}#{2,4}\s+(.+?)\s*$")
CHECK_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+?)\s*$")
KO_RE = re.compile(r"^\s*(?:\*\*)?(KO|NON|NOK|BUG|❌|✗)\b", re.I)
GLOBAL_RE = re.compile(r"^\s*(?:\*\*)?(GLOBAL|G[ÉE]N[ÉE]RAL|REVUE GLOBALE|VISION)\s*:", re.I)   # revue d'ensemble du porteur
GLOBAL_MD = STATE_DIR / "REVUE_GLOBALE.md"
GLOBAL_TEMPLATE = """# Revue globale — ce que je pense de l'application dans son ensemble

Écris ici, librement (dicté ou tapé), ce qui dépasse les cases des PR : vision produit, ce qui manque,
ce qui gêne, ce que tu veux voir disparaître, l'ordre des priorités. Une idée par paragraphe ou par
tiret. Tu peux citer un écran (« Suivre : … », « Revoir : … ») et coller le chemin d'une capture.
Le correcteur du matin (Claude Fable) lit ce fichier en entier, comme ta revue du 21 septembre :
chaque point devient un lot correctif, un complément à un lot du programme, ou une décision notée.
Le fichier est archivé (REVUE_GLOBALE-<date>.md) une fois lu, et vidé pour la fois suivante.

---

"""


def global_comments(comments: list[dict]) -> list[dict]:
    """Commentaires « GLOBAL : … » du porteur (revue d'ensemble), avec leurs images."""
    out = []
    for c in comments or []:
        text = (c.get("body") or "").strip()
        if not GLOBAL_RE.match(text) or not trusted(c):
            continue
        images = IMG_MD_RE.findall(text) + [u for u in IMG_URL_RE.findall(text) if u not in IMG_MD_RE.findall(text)]
        out.append({"author": (c.get("user") or {}).get("login"), "at": c.get("created_at"), "url": c.get("html_url"),
                    "text": re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text).strip(), "images": list(dict.fromkeys(images))})
    return out


def global_file_text() -> str:
    """Le texte de REVUE_GLOBALE.md hors gabarit ; vide si rien d'écrit."""
    if not GLOBAL_MD.exists():
        return ""
    body = GLOBAL_MD.read_text(encoding="utf-8")
    if "---" in body:
        body = body.split("---", 1)[1]
    return body.strip()


def ensure_global_template() -> None:
    if not GLOBAL_MD.exists():
        GLOBAL_MD.write_text(GLOBAL_TEMPLATE, encoding="utf-8")


def archive_global_file(date: str) -> str | None:
    """Après lecture par le correcteur : archiver et remettre le gabarit vide."""
    text = global_file_text()
    if not text:
        return None
    dest = STATE_DIR / f"REVUE_GLOBALE-{date}.md"
    dest.write_text(GLOBAL_MD.read_text(encoding="utf-8"), encoding="utf-8")
    GLOBAL_MD.write_text(GLOBAL_TEMPLATE, encoding="utf-8")
    return str(dest)
IMG_MD_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
IMG_URL_RE = re.compile(r"(https?://(?:github\.com/user-attachments/assets/|user-images\.githubusercontent\.com/|private-user-images\.githubusercontent\.com/)[^\s)>\"']+)")
CAPTURE_RE = re.compile(r"(docs/recette/[^\s`)\]]+\.(?:jpe?g|png))", re.I)
RECETTE_TITLES = ("recette", "recipe", "acceptance", "what to check")


def token() -> str | None:
    """Jeton éprouvé (gh_token.py) ; None → lecture anonyme (dépôt public), sans les images privées."""
    sys.path.insert(0, str(HERE))
    from gh_token import token as _token  # noqa: PLC0415
    return _token(required=False)


_TRUSTED: set[str] | None = None


def trusted_logins() -> set[str]:
    """Qui a le droit de parler au pipeline : les ADMINS du dépôt (le porteur) + le compte du jeton,
    + BIM_TRUSTED_LOGINS (env ou fichier de clés, séparés par des virgules). Le dépôt est public :
    n'importe qui peut commenter ; un collaborateur en écriture aussi. Leurs commentaires sont ignorés."""
    global _TRUSTED
    if _TRUSTED is not None:
        return _TRUSTED
    logins: set[str] = set()
    extra = os.environ.get("BIM_TRUSTED_LOGINS") or ""
    env_file = Path(os.environ.get("NAVIGUIDE_ENV_FILE", str(Path.home() / ".config" / "naviguide" / "simulator.env")))
    if not extra and env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("BIM_TRUSTED_LOGINS="):
                extra = line.split("=", 1)[1].strip().strip('"')
    logins.update(x.strip() for x in extra.split(",") if x.strip())
    tok = token()
    if tok:
        try:
            me = gh("/user", tok) or {}
            if me.get("login"):
                logins.add(me["login"])
            for c in gh(f"/repos/{REPO}/collaborators?affiliation=all&per_page=100", tok) or []:
                if (c.get("permissions") or {}).get("admin"):
                    logins.add(c["login"])
        except Exception:
            pass
    _TRUSTED = logins
    return logins


def trusted(comment: dict) -> bool:
    """Un commentaire compte s'il vient d'un auteur de confiance (ou si la liste est vide : pas de jeton)."""
    allowed = trusted_logins()
    return not allowed or ((comment.get("user") or {}).get("login") in allowed)


def gh(path: str, tok: str | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "bim-review-collect", "X-GitHub-Api-Version": "2022-11-28"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(f"{GITHUB_API}{path}", headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code} GET {path}") from e


def sections(body: str) -> dict[str, str]:
    """Corps → {titre en minuscules: texte} pour les titres ## / ### / ####."""
    out: dict[str, str] = {}
    title, buf = "", []
    for line in (body or "").splitlines():
        m = HEADING_RE.match(line)
        if m:
            if title:
                out[title] = "\n".join(buf).strip()
            title, buf = m.group(1).strip().lower(), []
        else:
            buf.append(line)
    if title:
        out[title] = "\n".join(buf).strip()
    return out


def recette_items(body: str) -> list[dict]:
    """Items de la rubrique Recette : {text, checked: True|False|None}. None = pas de case (ancienne PR)."""
    items: list[dict] = []
    for title, text in sections(body).items():
        if not any(title.startswith(t) for t in RECETTE_TITLES):
            continue
        for ln in text.splitlines():
            if not ln.strip() or ln.strip().startswith("```"):
                continue
            m = CHECK_RE.match(ln)
            if m:
                items.append({"text": m.group(2), "checked": m.group(1).lower() == "x"})
                continue
            b = BULLET_RE.match(ln)
            if b and "docs/recette/" not in ln and not re.match(r"(?i)^\**\s*(captures?|écran|screen)\s*:", b.group(1)):
                items.append({"text": b.group(1), "checked": None})
    return items


BOT_MARK_RE = re.compile(r"^\s*#{1,3}\s*🤖\s*(Pr[ée]-?revue|Parcours de r[ée]f[ée]rence)", re.I | re.M)   # titre en début de ligne (pré-revue d'une PR, ou parcours complet sur la PR de tête) — pas le 🔗 qui cite la consigne
BOT_ITEM_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*🤖\s*(.+?)\s*$")
BOT_NOTE_RE = re.compile(r"\s+[—–-]\s+(KO|non v[ée]rifiable)\s*:\s*(.*)$", re.I)
_KEY_DROP_RE = re.compile(r"[*_`«»\"'’]|\s+/\s+.*$")   # gras, guillemets, et la moitié anglaise après « / »


def item_key(text: str) -> str:
    """Clé de rapprochement entre une case du porteur et une ligne 🤖 du bot : minuscules,
    sans gras ni guillemets, moitié FR seulement, 60 premiers caractères."""
    t = _KEY_DROP_RE.sub("", text or "").lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t[:60]


def bot_verdicts(comments: list[dict]) -> dict[str, dict]:
    """Commentaires « 🤖 Pré-revue » (Grok Bot) → {clé d'item: {ok, ko, note, text}}.
    Le bot coche les cases de la PR qu'il a vérifiées et liste ici ce qu'il a fait : c'est
    ce qui permet d'attribuer une case cochée au bot plutôt qu'au porteur."""
    out: dict[str, dict] = {}
    for c in comments or []:
        body = c.get("body") or ""
        if not BOT_MARK_RE.search(body) or not trusted(c):
            continue
        for ln in body.splitlines():
            m = BOT_ITEM_RE.match(ln)
            if not m:
                continue
            text = m.group(2)
            note = ""
            n = BOT_NOTE_RE.search(text)
            if n:
                note = f"{n.group(1)} : {n.group(2)}".strip()
                text = text[: n.start()].strip()
            checked = m.group(1).lower() == "x"
            out[item_key(text)] = {"ok": checked, "ko": (not checked) and note.upper().startswith("KO"), "note": note, "text": text,
                                   "author": (c.get("user") or {}).get("login"), "url": c.get("html_url")}
    return out


def ko_comments(comments: list[dict]) -> list[dict]:
    out = []
    for c in comments or []:
        text = (c.get("body") or "").strip()
        if not KO_RE.match(text) or not trusted(c):
            continue
        images = IMG_MD_RE.findall(text) + [u for u in IMG_URL_RE.findall(text) if u not in IMG_MD_RE.findall(text)]
        out.append({
            "author": (c.get("user") or {}).get("login"),
            "at": c.get("created_at"),
            "url": c.get("html_url"),
            "text": re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text).strip(),
            "images": list(dict.fromkeys(images)),
        })
    return out


def agent_captures(body: str, branch: str) -> list[str]:
    paths = list(dict.fromkeys(CAPTURE_RE.findall(body or "")))
    return [f"https://github.com/{REPO}/raw/{branch}/{p}" for p in paths]


def download(url: str, dest: Path, tok: str | None) -> Path | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "bim-review-collect"}
    if tok and "github.com" in url:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except Exception:
        return None
    ext = ".png" if "png" in ctype else ".jpg" if ("jpeg" in ctype or "jpg" in ctype) else Path(urllib.parse.urlparse(url).path).suffix or ".bin"
    if dest.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        dest = dest.with_suffix(ext)
    dest.write_bytes(data)
    return dest


def pr_review(number: int, tok: str | None, out_dir: Path, *, images: bool = True, lot: str = "", since: str | None = None) -> dict:
    pr = gh(f"/repos/{REPO}/pulls/{number}", tok) or {}
    comments = gh(f"/repos/{REPO}/issues/{number}/comments?per_page=100", tok) or []
    body = pr.get("body") or ""
    branch = (pr.get("head") or {}).get("ref") or ""
    items = recette_items(body)
    kos = [k for k in ko_comments(comments) if not BOT_MARK_RE.search(k["text"])]   # KO du porteur (les KO du bot sont dans bot)
    globals_ = global_comments(comments)
    for k in kos + globals_:   # lot W7 : sessions successives — ce qui est arrivé depuis la session précédente est « nouveau »
        k["new"] = (since is None) or ((k.get("at") or "") >= since)
    bot = bot_verdicts(comments)
    matched: set[str] = set()
    for it in items:   # qui a coché ? bot = coché ET listé [x] 🤖 par le bot ; porteur sinon
        k = item_key(it["text"])
        b = bot.get(k)
        if b is not None:
            matched.add(k)
        it["by"] = ("bot" if (b and b.get("ok")) else "porteur") if it["checked"] else None
        it["bot"] = None if b is None else ("ok" if b.get("ok") else ("ko" if b.get("ko") else "unverifiable"))
        it["bot_note"] = (b or {}).get("note", "")
    # Lignes 🤖 qui ne correspondent à aucune case de la PR : erreurs de console, régressions du
    # parcours de référence… Les KO comptent comme des KO (le correcteur les lit) ; les OK sont gardés à titre d'info.
    bot_extra = [{"text": v["text"], "status": "ok" if v.get("ok") else ("ko" if v.get("ko") else "unverifiable"), "note": v.get("note", ""), "url": v.get("url")}
                 for k, v in bot.items() if k not in matched]
    captures = agent_captures(body, branch)
    entry = {
        "number": number, "lot": lot, "title": pr.get("title"), "url": pr.get("html_url"), "branch": branch,
        "state": pr.get("state"), "merged": bool(pr.get("merged_at")),
        "items": items,
        "ok": sum(1 for i in items if i["checked"] is True),
        "ok_porteur": sum(1 for i in items if i["checked"] is True and i.get("by") == "porteur"),
        "ok_bot": sum(1 for i in items if i["checked"] is True and i.get("by") == "bot"),
        "unchecked": sum(1 for i in items if i["checked"] is False),
        "no_box": sum(1 for i in items if i["checked"] is None),
        "bot_ko": [{"text": i["text"], "note": i["bot_note"]} for i in items if i.get("bot") == "ko"]
                  + [{"text": x["text"], "note": x["note"]} for x in bot_extra if x["status"] == "ko"],
        "bot_extra": bot_extra,
        "ko": kos,
        "global": globals_,
        "captures": captures,
        "local_images": [],
    }
    if images:
        pr_dir = out_dir / f"pr-{number}"
        for i, ko in enumerate(kos, 1):
            for j, url in enumerate(ko["images"], 1):
                p = download(url, pr_dir / f"ko-{i}-{j}.jpg", tok)
                if p:
                    entry["local_images"].append({"kind": "porteur", "ko": i, "path": str(p)})
        for i, g in enumerate(globals_, 1):
            for j, url in enumerate(g["images"], 1):
                p = download(url, pr_dir / f"global-{i}-{j}.jpg", tok)
                if p:
                    entry["local_images"].append({"kind": "porteur-global", "global": i, "path": str(p)})
        for k, url in enumerate(captures, 1):
            name = Path(urllib.parse.urlparse(url).path).name
            p = download(url, pr_dir / f"agent-{k}-{name}", tok)
            if p:
                entry["local_images"].append({"kind": "agent", "path": str(p)})
    return entry


def prs_from_state() -> list[tuple[str, int]]:
    if not STATE_JSON.exists():
        return []
    s = json.loads(STATE_JSON.read_text(encoding="utf-8"))
    out = []
    for lid, e in (s.get("done") or {}).items():
        m = re.search(r"/pull/(\d+)", e.get("pr") or "")
        if m and e.get("status") == "FINISHED":
            out.append((lid, int(m.group(1))))
    return out


def summary_md(review: dict) -> str:
    lines = [f"# Revue de la pile — {review['date']}", ""]
    tot_ok = sum(p["ok"] for p in review["prs"])
    tot_bot = sum(p.get("ok_bot", 0) for p in review["prs"])
    tot_items = sum(len(p["items"]) for p in review["prs"])
    tot_ko = sum(len(p["ko"]) for p in review["prs"])
    tot_bot_ko = sum(len(p.get("bot_ko") or []) for p in review["prs"])
    lines += [f"**{tot_ok} / {tot_items} items cochés** (dont {tot_bot} par le bot 🤖) · **{tot_ko} KO du porteur** · {tot_bot_ko} KO du bot, sur {len(review['prs'])} PR.", ""]
    if review.get("since"):
        new_ko = sum(1 for p in review["prs"] for k in p["ko"] if k.get("new"))
        lines += [f"Session {review.get('session') or '?'} : **{new_ko} KO nouveaux** (🆕) depuis la session précédente ({review['since']}) ; les autres ont déjà été lus par un plan précédent — ne pas les replanifier.", ""]
    glob_comments = [g for p in review["prs"] for g in (p.get("global") or [])]
    if review.get("global_file") or glob_comments:
        lines += ["## Revue globale du porteur (vision d'ensemble — à traiter comme la revue du 21 sept.)", ""]
        if review.get("global_file"):
            lines += [review["global_file"], ""]
        for g in glob_comments:
            lines.append(f"- {g['text']}" + (f" — [commentaire]({g['url']})" if g.get("url") else ""))
        lines.append("")
    for p in review["prs"]:
        tag = f"#{p['number']} {p['lot']}".strip()
        state = "mergée" if p["merged"] else p["state"]
        lines.append(f"## {tag} — {p['title']}  ({state})")
        lines.append(f"Cochés {p['ok']} / {len(p['items'])} (porteur {p.get('ok_porteur', 0)}, bot {p.get('ok_bot', 0)})"
                     + (f" · sans case : {p['no_box']}" if p["no_box"] else "") + f" · KO porteur : {len(p['ko'])} · KO bot : {len(p.get('bot_ko') or [])}")
        for it in p["items"]:
            if it["checked"]:
                mark = "✅🤖" if it.get("by") == "bot" else "✅"
            elif it["checked"] is False:
                mark = "🤖❌" if it.get("bot") == "ko" else "⬜"
            else:
                mark = "•"
            note = f"  — 🤖 {it['bot_note']}" if it.get("bot_note") else ""
            lines.append(f"- {mark} {it['text']}{note}")
        extra_ko = [x for x in (p.get("bot_extra") or []) if x["status"] == "ko"]
        if extra_ko:
            lines.append(f"- 🤖 hors cases (console, parcours de référence) : {len(extra_ko)} KO")
            for x in extra_ko:
                lines.append(f"    - 🤖❌ {x['text'][:120]}" + (f" — {x['note'][:160]}" if x.get("note") else ""))
        for i, ko in enumerate(p["ko"], 1):
            lines.append(f"- {'🆕 ' if review.get('since') and ko.get('new') else ''}❌ KO {i} ({ko['author']}) : {ko['text']}")
            for im in [x for x in p["local_images"] if x.get("ko") == i]:
                lines.append(f"    - image : `{im['path']}`")
        agent_imgs = [x for x in p["local_images"] if x["kind"] == "agent"]
        if agent_imgs:
            lines.append("- captures de l'agent : " + ", ".join(f"`{x['path']}`" for x in agent_imgs))
        lines.append("")
    return "\n".join(lines)


def collect(prs: list[tuple[str, int]], out_dir: Path, *, images: bool = True, since: str | None = None, session: int | None = None) -> dict:
    """`since` (ISO UTC, lot W7) : les KO / GLOBAL postés avant sont marqués déjà lus (new=False) ; `session` nomme les fichiers."""
    tok = token()
    date = time.strftime("%Y-%m-%d")
    tag = f"{date}-s{session}" if session and session > 1 else date
    review = {"date": date, "repo": REPO, "prs": [], "global_file": global_file_text(), "since": since, "session": session}
    for lot, num in prs:
        try:
            review["prs"].append(pr_review(num, tok, out_dir / f"review-{tag}", images=images, lot=lot, since=since))
        except RuntimeError as e:
            review["prs"].append({"number": num, "lot": lot, "error": str(e), "items": [], "ok": 0, "unchecked": 0, "no_box": 0, "ko": [], "captures": [], "local_images": [], "merged": False, "state": "?", "title": "", "url": ""})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"review-{tag}.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"review-{tag}.md").write_text(summary_md(review), encoding="utf-8")
    review["json"] = str(out_dir / f"review-{tag}.json")
    review["md"] = str(out_dir / f"review-{tag}.md")
    return review


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prs", nargs="+", type=int, help="numéros de PR (défaut : les PR FINISHED de state.json)")
    ap.add_argument("--out", default=str(STATE_DIR), help="dossier de sortie (défaut : infra/agents)")
    ap.add_argument("--no-images", action="store_true", help="ne pas télécharger les images")
    ap.add_argument("--since", help="ISO UTC : les KO / GLOBAL antérieurs sont marqués déjà lus (sessions successives, lot W7)")
    ap.add_argument("--session", type=int, help="numéro de session (nomme review-<date>-s<n>.*)")
    args = ap.parse_args()
    prs = [("", n) for n in args.prs] if args.prs else prs_from_state()
    if not prs:
        sys.exit("Aucune PR : passer --prs ou avoir un state.json avec des lots FINISHED.")
    review = collect(prs, Path(args.out), images=not args.no_images, since=args.since, session=args.session)
    print(summary_md(review))
    print(f"\n→ {review['json']}\n→ {review['md']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Chien de garde de la nuit (lot W6) : surveille la boucle et répare ce qu'il sait réparer.

Toutes les 5 min, il regarde ce que la nuit du 22 sept. a laissé passer pendant des heures :
  - la boucle (loop.py) et le batch (run_lots.py) tournent-ils encore alors qu'une phase est en cours ?
  - le tunnel Cloudflare est-il vivant ? le poste répond-il PAR L'URL PUBLIQUE (page + API) ?
  - un agent est-il muet depuis trop longtemps ?
  - Grok Bot a-t-il rendu sa pré-revue sur les PR réveillées il y a plus de 30 min ?
  - le webhook a-t-il été refusé (401/403) ? le fournisseur de modèle bride-t-il ? le disque ?

Remèdes connus, appliqués seuls (avec un délai entre deux tentatives, et un plafond par jour) :
  boucle absente → `loop.py --resume` ; tunnel mort → relance ; poste en panne hors bascule → rebâtir
  le poste sur la tête de pile ; pré-revue absente → un second réveil du bot. Il répare
  l'INFRASTRUCTURE, jamais le produit : un bug d'application reste l'affaire du réviseur et du porteur.

Tout est écrit dans infra/agents/RAPPORT_DE_NUIT.md (vu, fait, pas su faire), et résumé en un
commentaire « 🩺 Nuit » sur la PR de tête à la fin du batch. loop.py et run_lots.py le lancent
d'eux-mêmes ; il vit tant qu'une phase est en cours.

Usage :
    python3 infra/agents/watchdog.py                 # veille (toutes les 5 min)
    python3 infra/agents/watchdog.py --once          # un seul passage, puis le rapport
    python3 infra/agents/watchdog.py --status        # état des processus et du poste, sans rien réparer
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402

STATE_DIR = rl.STATE_DIR
WD_STATE = STATE_DIR / "watchdog-state.json"
WD_LOG = STATE_DIR / "watchdog.log"
WD_PID = STATE_DIR / "watchdog.pid"
REPORT = STATE_DIR / "RAPPORT_DE_NUIT.md"
LOOP_JSON = STATE_DIR / "loop-state.json"

EVERY_S = int(os.environ.get("BIM_WATCHDOG_EVERY", "300"))
STUCK_MIN = 75            # journal du batch muet (agent, CI…) : au-delà, on le dit (pas de remède sûr)
BOT_REWAKE_MIN = 30       # 🔗 posté depuis ≥ 30 min sans 🤖 → un second réveil, une fois par PR
COOLDOWN_S = 1800         # entre deux remèdes du même genre
MAX_RELAUNCH_PER_DAY = 3  # relances de la boucle / du poste : au-delà, c'est au porteur
ACTIVE_PHASES = ("batch", "await_review", "await_pile", "correct", "await_go")
WEBHOOK_KO_RE = re.compile(r"webhook Grok Bot (?:refusé[^0-9]{0,12}HTTP (401|403)|injoignable : HTTP Error (401|403))")
RATE_RE = re.compile(r"rate limited", re.I)


# ---------------------------------------------------------------- outils

def say(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with WD_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_state() -> dict:
    if WD_STATE.exists():
        try:
            return json.loads(WD_STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"incidents": [], "last_remedy": {}, "relaunches": {}, "rewoken": [], "posted_for": [], "seen": []}


def save_state(st: dict) -> None:
    WD_STATE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def pids(pattern: str) -> list[int]:
    p = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return [int(x) for x in p.stdout.split() if x.strip().isdigit() and int(x) != os.getpid()]


def spawn(cmd: list[str], logfile: Path) -> None:
    """Lancer un processus détaché (journal en annexe) — le seul endroit d'où le chien de garde relance quelque chose."""
    with logfile.open("a", encoding="utf-8") as fh:
        subprocess.Popen(cmd, cwd=str(rl.ROOT), stdout=fh, stderr=subprocess.STDOUT, start_new_session=True,
                         env={**os.environ, "BIM_STATE_DIR": str(STATE_DIR)})


def loop_state() -> dict:
    try:
        return json.loads(LOOP_JSON.read_text(encoding="utf-8")) if LOOP_JSON.exists() else {}
    except json.JSONDecodeError:
        return {}


def http_code(url: str, timeout: int = 20) -> int:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "bim-watchdog"}), timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def log_age_min(path: Path) -> float | None:
    try:
        return (time.time() - path.stat().st_mtime) / 60
    except FileNotFoundError:
        return None


def tail(path: Path, n: int = 400) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except FileNotFoundError:
        return []


def today() -> str:
    return time.strftime("%Y-%m-%d")


def can_remedy(st: dict, kind: str) -> bool:
    """Un remède du même genre au plus toutes les 30 min, et au plus 3 relances par jour."""
    last = st["last_remedy"].get(kind, 0)
    if time.time() - last < COOLDOWN_S:
        return False
    count = st["relaunches"].get(f"{kind}:{today()}", 0)
    return count < MAX_RELAUNCH_PER_DAY


def mark_remedy(st: dict, kind: str) -> None:
    st["last_remedy"][kind] = time.time()
    st["relaunches"][f"{kind}:{today()}"] = st["relaunches"].get(f"{kind}:{today()}", 0) + 1


def incident(st: dict, kind: str, seen: str, done: str, *, fixed: bool | None, key: str | None = None) -> None:
    """Une ligne du rapport : ce qu'on a vu, ce qu'on a fait, si c'est réparé. `key` évite les doublons."""
    k = key or f"{kind}:{seen}"
    if k in st["seen"] and fixed is None:
        return
    st["seen"] = (st["seen"] + [k])[-500:]
    st["incidents"] = st["incidents"][-300:]
    st["incidents"].append({"at": time.strftime("%Y-%m-%d %H:%M"), "kind": kind, "seen": seen, "done": done, "fixed": fixed})
    say(f"{'✅' if fixed else ('⚠️' if fixed is None else '❌')} {kind} — {seen} → {done}")


# ---------------------------------------------------------------- contrôles

def check_processes(st: dict, phase: str | None) -> None:
    loop_alive = bool(pids(r"loop\.py"))
    batch_alive = bool(pids(r"run_lots\.py --(from|resume|only)"))
    if not phase:
        return
    if loop_alive or (phase == "batch" and batch_alive):
        return
    # Personne ne tient la barre alors qu'une phase est en cours (22 sept. 01:03 : `--cycles 1`).
    kind = "boucle absente"
    if not can_remedy(st, kind):
        incident(st, kind, f"phase `{phase}` en cours, ni loop.py ni run_lots.py en vie", "pas de nouvelle relance (délai ou plafond du jour atteint) — au porteur : `python3 infra/agents/loop.py --resume`", fixed=False, key=f"{kind}:{today()}:{st['relaunches'].get(f'{kind}:{today()}', 0)}")
        return
    mark_remedy(st, kind)
    spawn(["caffeinate", "-i", sys.executable, str(HERE / "loop.py"), "--resume", "--cycles", "100"], STATE_DIR / "loop.log")
    time.sleep(8)
    ok = bool(pids(r"loop\.py"))
    incident(st, kind, f"phase `{phase}` en cours, ni loop.py ni run_lots.py en vie", "relancé `loop.py --resume`", fixed=ok, key=f"{kind}:{time.time():.0f}")


def check_tunnel(st: dict, phase: str | None) -> str | None:
    url = rl.tunnel_url()
    if url or not phase:
        return url
    kind = "tunnel mort"
    if not can_remedy(st, kind):
        return None
    mark_remedy(st, kind)
    url = rl.start_tunnel()
    incident(st, kind, "cloudflared arrêté (tunnel.pid mort)", f"relancé → {url or 'échec'}", fixed=bool(url), key=f"{kind}:{time.time():.0f}")
    return url


def check_poste(st: dict, phase: str | None, url: str | None) -> None:
    if not phase or not url:
        return
    page, api = http_code(url + "/"), http_code(url + "/ici/warm/status")
    if page == 200 and api == 200:
        return
    time.sleep(90)   # la bascule du poste après un lot dure ~1 s ; un 5xx qui persiste 90 s n'est pas une bascule
    page, api = http_code(url + "/"), http_code(url + "/ici/warm/status")
    if page == 200 and api == 200:
        return
    seen = f"{url} → page HTTP {page}, API HTTP {api}" + (" (Vite refuse l'hôte)" if 403 in (page, api) else "")
    kind = "poste en panne"
    if bool(pids(r"ensure-dev\.sh")):
        return   # quelqu'un rebâtit déjà le poste
    if not can_remedy(st, kind):
        incident(st, kind, seen, "pas de nouvelle relance (délai ou plafond) — au porteur : `python3 infra/agents/run_lots.py --recette`", fixed=False, key=f"{kind}:{today()}:{st['relaunches'].get(f'{kind}:{today()}', 0)}")
        return
    mark_remedy(st, kind)
    try:
        state = rl.State.load()
        args = SimpleNamespace(branch=None, repo=rl.DEFAULT_REPO, no_recette=False, no_tunnel=False, publish_tip=False)
        rl.prepare_recette(state, args, rl.Http(None, rl.github_token_from_git()), quiet=True)
        time.sleep(5)
        page, api = http_code(url + "/"), http_code(url + "/ici/warm/status")
        incident(st, kind, seen, f"poste rebâti sur `{state.last_branch}` → page HTTP {page}, API HTTP {api}", fixed=(page == 200 and api == 200), key=f"{kind}:{time.time():.0f}")
    except Exception as e:
        incident(st, kind, seen, f"rebâtir le poste a échoué : {type(e).__name__}", fixed=False, key=f"{kind}:{time.time():.0f}")


def check_stuck(st: dict, phase: str | None) -> None:
    if phase != "batch":
        return
    age = log_age_min(rl.LOG_FILE)
    if age is None or age < STUCK_MIN:
        return
    last = (tail(rl.LOG_FILE, 1) or [""])[0][:160]
    incident(st, "batch muet", f"rien dans run_lots.log depuis {age:.0f} min — dernière ligne : {last}",
             "rien fait (l'agent a son propre délai de 3 h) — si ça dure, au porteur : regarder l'agent dans Cursor", fixed=None, key=f"muet:{today()}:{int(age // 60)}")


def check_bot(st: dict, phase: str | None, url: str | None) -> None:
    """PR réveillées il y a ≥ 30 min sans pré-revue 🤖 : un second réveil, une seule fois par PR."""
    if phase != "batch" or not url:
        return
    hook, _ = rl.webhook_settings()
    if not hook:
        return
    try:
        state = rl.State.load()
        http = rl.Http(None, rl.github_token_from_git())
        from review_collect import trusted  # noqa: PLC0415
    except Exception:
        return
    lots = [(lid, e) for lid, e in state.done.items() if e.get("status") == "FINISHED" and e.get("pr")][-8:]
    for lid, e in lots:
        num = rl.pr_number(e.get("pr"))
        if not num or num in st["rewoken"]:
            continue
        try:
            comments = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/issues/{num}/comments?per_page=100") or []
        except RuntimeError:
            continue
        links = [c for c in comments if (c.get("body") or "").startswith(rl.BOT_COMMENT_MARK)]
        if not links or any(rl.BOT_PREREVIEW_RE.search(c.get("body") or "") and trusted(c) for c in comments):
            continue
        posted = links[-1].get("created_at") or ""
        try:
            age_min = (time.time() - calendar.timegm(time.strptime(posted, "%Y-%m-%dT%H:%M:%SZ"))) / 60
        except ValueError:
            continue
        if age_min < BOT_REWAKE_MIN:
            continue
        rl.wake_bot("prereview", num, url)
        st["rewoken"].append(num)
        incident(st, "pré-revue absente", f"PR #{num} ({lid}) : 🔗 depuis {age_min:.0f} min, pas de 🤖", "second réveil du bot par webhook", fixed=None, key=f"bot:{num}")


def check_logs(st: dict) -> None:
    lines = tail(rl.LOG_FILE, 600)
    recent = [ln for ln in lines if ln[:16] >= time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 7200))]
    for ln in recent:
        m = WEBHOOK_KO_RE.search(ln)
        if m:
            code = int(m.group(1) or m.group(2))
            # Plus de minuteur (24 sept.) : le porteur doit remettre la clé — on le lui dit sur la PR, une fois par jour.
            try:
                rl.alert_webhook_refused(code, None)
            except Exception:
                pass
            incident(st, "webhook refusé", f"HTTP {code} dans run_lots.log", "alerte postée sur la PR de tête — clé ou en-tête (BIM_BOT_WEBHOOK_TOKEN / _HEADER) à remettre par le porteur ; le batch continue", fixed=False, key=f"webhook:{today()}")
            break
    rate = sum(1 for ln in recent if RATE_RE.search(ln))
    if rate:
        incident(st, "fournisseur bridé", f"{rate} ligne(s) « rate limited » en 2 h", "run_lots patiente seul (5, 10, 20 min) — rien à faire", fixed=None, key=f"rate:{today()}:{rate // 5}")


def check_disk(st: dict) -> None:
    free_gb = shutil.disk_usage(str(rl.ROOT)).free / 1e9
    if free_gb < 3:
        incident(st, "disque", f"{free_gb:.1f} Go libres", "rien fait — au porteur : libérer de la place (worktrees ~/bim-lots, node_modules)", fixed=False, key=f"disk:{today()}")


# ---------------------------------------------------------------- rapport

def write_report(st: dict, phase: str | None, url: str | None) -> None:
    loop_alive = bool(pids(r"loop\.py"))
    batch_alive = bool(pids(r"run_lots\.py --(from|resume|only)"))
    page = http_code(url + "/") if url else 0
    incs = [i for i in st["incidents"] if i["at"].startswith(today()) or i["at"] >= time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 14 * 3600))]
    fixed = [i for i in incs if i["fixed"] is True]
    broken = [i for i in incs if i["fixed"] is False]
    info = [i for i in incs if i["fixed"] is None]
    lines = [
        f"# Rapport de nuit — {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Boucle : {'en vie' if loop_alive else 'absente'} · batch : {'en cours' if batch_alive else 'aucun'} · phase mémorisée : `{phase or 'aucune'}`",
        f"- Poste public : {url or 'pas de tunnel'}" + (f" → HTTP {page}" if url else ""),
        f"- Incidents : {len(incs)} — réparés seuls : {len(fixed)} · **à faire par le porteur : {len(broken)}** · pour information : {len(info)}",
        "",
    ]
    if broken:
        lines += ["## À faire par le porteur", ""]
        lines += [f"- {i['at']} **{i['kind']}** — {i['seen']} → {i['done']}" for i in broken] + [""]
    if fixed:
        lines += ["## Réparé seul", ""]
        lines += [f"- {i['at']} {i['kind']} — {i['seen']} → {i['done']}" for i in fixed] + [""]
    if info:
        lines += ["## Pour information", ""]
        lines += [f"- {i['at']} {i['kind']} — {i['seen']} → {i['done']}" for i in info] + [""]
    if not incs:
        lines += ["Rien à signaler : rien vu, rien réparé.", ""]
    lines += ["_Le chien de garde (infra/agents/watchdog.py) passe toutes les 5 min : boucle, tunnel, poste public, agent muet, pré-revues du bot, webhook, disque._", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def post_night_comment(st: dict) -> None:
    """Fin de batch (« terminé. Récapitulatif » dans le journal, APRÈS le dernier départ de batch « lots : [ ») :
    un commentaire 🩺 sur la PR de tête, une fois par tête."""
    lines = tail(rl.LOG_FILE, 3000)
    started = max((i for i, ln in enumerate(lines) if " lots : [" in ln), default=-1)
    ended = max((i for i, ln in enumerate(lines) if "terminé. Récapitulatif" in ln), default=-1)
    if ended < 0 or ended < started:
        return
    state = rl.State.load()
    num = rl.pr_number((state.done.get(state.last_lot) or {}).get("pr"))
    if not num or num in st["posted_for"]:
        return
    incs = [i for i in st["incidents"] if i["at"] >= time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 14 * 3600))]
    fixed = [i for i in incs if i["fixed"] is True]
    broken = [i for i in incs if i["fixed"] is False]
    body = [f"## 🩺 Nuit — {len(incs)} incident(s), {len(fixed)} réparé(s) seul(s), {len(broken)} à voir / {len(incs)} incident(s), {len(fixed)} self-repaired, {len(broken)} need the owner", ""]
    body += [f"- ❌ **{i['kind']}** — {i['seen']} → {i['done']}" for i in broken]
    body += [f"- ✅ {i['kind']} — {i['seen']} → {i['done']}" for i in fixed]
    body += [f"- ℹ️ {i['kind']} — {i['seen']}" for i in incs if i["fixed"] is None]
    body += ["", f"Détail : `infra/agents/RAPPORT_DE_NUIT.md` (chien de garde, lot W6). / Details in `infra/agents/RAPPORT_DE_NUIT.md` (watchdog, lot W6)."]
    tmp = STATE_DIR / "night-comment.md"
    tmp.write_text("\n".join(body), encoding="utf-8")
    p = subprocess.run([sys.executable, str(HERE / "post_pr_comment.py"), str(num), str(tmp)], capture_output=True, text=True, timeout=120)
    if p.returncode == 0:
        st["posted_for"].append(num)
        say(f"commentaire 🩺 posté sur la PR de tête #{num}")
    else:
        say(f"commentaire 🩺 non posté sur #{num} : {(p.stderr or p.stdout)[-200:]}")


# ---------------------------------------------------------------- boucle

def cycle(st: dict, *, repair: bool = True) -> None:
    phase = loop_state().get("phase")
    url = rl.tunnel_url()
    if repair:
        check_processes(st, phase)
        url = check_tunnel(st, phase) or url
        check_poste(st, phase, url)
        check_stuck(st, phase)
        check_bot(st, phase, url)
        check_logs(st)
        check_disk(st)
        post_night_comment(st)
    write_report(st, phase, url)
    save_state(st)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="un passage puis le rapport")
    ap.add_argument("--status", action="store_true", help="le rapport sans rien réparer")
    ap.add_argument("--every", type=int, default=EVERY_S, help="secondes entre deux passages (défaut 300)")
    args = ap.parse_args()
    st = load_state()
    if args.status:
        cycle(st, repair=False)
        print(REPORT.read_text(encoding="utf-8"))
        return
    if args.once:
        cycle(st)
        print(REPORT.read_text(encoding="utf-8"))
        return
    others = [p for p in pids(r"watchdog\.py") if p != os.getpid()]
    if others:
        sys.exit(f"un chien de garde tourne déjà (pid {others[0]})")
    WD_PID.write_text(str(os.getpid()), encoding="utf-8")
    say(f"chien de garde en veille (toutes les {args.every // 60} min) — rapport : {REPORT}")
    idle_since: float | None = None
    while True:
        try:
            cycle(st)
        except Exception as e:  # ne jamais mourir sur une erreur de contrôle
            say(f"passage interrompu : {type(e).__name__}: {e}")
        phase = loop_state().get("phase")
        if phase in ACTIVE_PHASES:
            idle_since = None
        else:
            idle_since = idle_since or time.time()
            if time.time() - idle_since > 3600:
                say("plus aucune phase en cours depuis 1 h : le chien de garde s'arrête")
                WD_PID.unlink(missing_ok=True)
                return
        time.sleep(args.every)


if __name__ == "__main__":
    main()

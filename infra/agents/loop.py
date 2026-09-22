#!/usr/bin/env python3
"""La boucle (lot W4) : batch → recette du porteur → correcteur → GO → batch suivant.

Phases, mémorisées dans infra/agents/loop-state.json (reprise à tout moment) :

  batch         run_lots.py --from A --until B  (réviseur de nuit toutes les X PR, poste de recette par lot)
  await_review  attendre le signal du porteur : un commentaire « revue finie » (ou « GO ») sur la PR de
                tête — ou son merge. (Ancien nom : await_pile.)
  correct       review_collect + plan_corrections.py → PR « GO » (plan + lots RB…)
  await_go      attendre le merge de la PR GO (et de la tête de pile) ; lire `LOTS: RB1 RB4`
  → batch RB1..RB4 … ; `LOTS: aucun` → fin.

Les seuls gestes humains : cocher les cases des PR (+ « KO : … »), écrire « revue finie » sur la PR de
tête, puis merger la tête et le GO (deux clics). run_lots.py lance cette veille tout seul en fin de batch.
Le Mac reste allumé (`caffeinate -i`). Ne merge jamais lui-même.

Usage :
    caffeinate -i python3 infra/agents/loop.py --from RA1 --until RA8     # démarre par un batch
    caffeinate -i python3 infra/agents/loop.py --start-at await_pile      # la pile est déjà produite : attendre la recette
    caffeinate -i python3 infra/agents/loop.py --resume                   # reprend la phase en cours
    python3 infra/agents/loop.py --status
    python3 infra/agents/loop.py --cycles 1                               # un seul tour complet puis stop (défaut : 3)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402

LOOP_JSON = rl.STATE_DIR / "loop-state.json"
LOTS_LINE_RE = re.compile(r"^\s*LOTS\s*:\s*(.+?)\s*$", re.I | re.M)
REVIEW_DONE_RE = re.compile(r"\b(revue|review)\s+(finie|termin[ée]e|done|finished)\b|^\s*GO\s*[!.]?\s*$", re.I | re.M)


def load() -> dict:
    return json.loads(LOOP_JSON.read_text(encoding="utf-8")) if LOOP_JSON.exists() else {"phase": None, "cycle": 0, "history": []}


def save(st: dict) -> None:
    LOOP_JSON.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def gh_pr(number: int) -> dict:
    req = urllib.request.Request(f"https://api.github.com/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/pulls/{number}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "bim-loop"})
    tok = rl.github_token_from_git()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def run(cmd: list[str], timeout: int | None = None) -> int:
    rl.log("→ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(rl.ROOT), env={**os.environ, "BIM_STATE_DIR": str(rl.STATE_DIR), "BIM_IN_LOOP": "1"}, timeout=timeout)
    return p.returncode


def gh_comments(number: int) -> list:
    req = urllib.request.Request(f"https://api.github.com/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/issues/{number}/comments?per_page=100",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "bim-loop"})
    tok = rl.github_token_from_git()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def wait_review_done(number: int, poll_s: int) -> dict:
    """Le porteur a fini sa revue : commentaire « revue finie » / « GO » sur la PR de tête, ou merge de la tête."""
    rl.log(f"revue du porteur : PR #{number} — en attente d'un commentaire « revue finie » (ou du merge), un coup d'œil toutes les {poll_s} s")
    while True:
        try:
            pr = gh_pr(number)
            if pr.get("state") == "closed":
                rl.log(f"    PR #{number} fermée ({'mergée' if pr.get('merged_at') else 'non mergée'}) — revue considérée finie")
                return {"signal": "closed", "merged": bool(pr.get("merged_at"))}
            for c in gh_comments(number):
                body = c.get("body") or ""
                if REVIEW_DONE_RE.search(body) and "🤖" not in body[:40]:
                    rl.log(f"    signal « revue finie » reçu ({(c.get('user') or {}).get('login')}, {c.get('created_at')})")
                    return {"signal": "comment", "merged": False}
        except Exception as e:
            rl.log(f"    GitHub indisponible ({e}) — nouvel essai")
        time.sleep(poll_s)


def tip_pr_number() -> int | None:
    s = rl.State.load()
    e = s.done.get(s.last_lot) or {}
    return rl.pr_number(e.get("pr"))


def wait_closed(number: int, poll_s: int, what: str) -> dict:
    rl.log(f"{what} : PR #{number} — en attente de fermeture (merge par le porteur), un coup d'œil toutes les {poll_s} s")
    while True:
        try:
            pr = gh_pr(number)
            if pr.get("state") == "closed":
                rl.log(f"{what} : PR #{number} fermée — {'mergée' if pr.get('merged_at') else 'NON mergée (fermée sans merge)'}")
                return pr
        except Exception as e:
            rl.log(f"    GitHub indisponible ({e}) — nouvel essai")
        time.sleep(poll_s)


def ensure_root_on_main() -> None:
    b = rl.local_branch(rl.ROOT)
    if b != "main":
        sys.exit(f"Le dépôt principal {rl.ROOT} est sur `{b}` : il doit être sur `main` (les lots sont lus dans son docs/). `git checkout main` puis relancer avec --resume.")
    rl.sh(["git", "pull", "--ff-only", "-q"], cwd=rl.ROOT, check=False, timeout=180)


def phase_batch(st: dict, args) -> None:
    ensure_root_on_main()
    cmd = [sys.executable, str(HERE / "run_lots.py"), "--from", st["from"], "--until", st["until"], "--review-every", str(args.review_every),
           "--bot-wait-min", str(args.bot_wait_min)]
    if args.model:
        cmd += ["--model", args.model]
    if st.get("stack_on_state"):
        # Empiler sur la pile déjà produite (state.json) au lieu de repartir de main : les lots
        # partent de la tête actuelle, et la revue de demain couvre aussi les PR déjà là.
        cmd.append("--resume")
    rc = run(cmd)
    st["history"].append({"phase": "batch", "from": st["from"], "until": st["until"], "rc": rc, "at": time.strftime("%Y-%m-%d %H:%M")})
    st["tip_pr"] = tip_pr_number()
    st["phase"] = "await_review"
    save(st)


def phase_await_review(st: dict, args) -> None:
    n = st.get("tip_pr") or tip_pr_number()
    if not n:
        sys.exit("Aucune PR de tête de pile dans state.json : rien à attendre.")
    st["tip_pr"] = n
    save(st)
    sig = wait_review_done(n, args.poll)
    st["history"].append({"phase": "await_review", "pr": n, **sig, "at": time.strftime("%Y-%m-%d %H:%M")})
    st["phase"] = "correct"
    save(st)


def phase_correct(st: dict, args) -> None:
    ensure_root_on_main()
    cmd = [sys.executable, str(HERE / "plan_corrections.py"), "--model", args.corrector_model]
    rc = run(cmd, timeout=3 * 3600)
    s = rl.State.load()
    last = (s.extra.get("corrections") or [{}])[-1]
    st["go_pr"] = last.get("go_pr")
    st["history"].append({"phase": "correct", "rc": rc, "go_pr": st["go_pr"], "at": time.strftime("%Y-%m-%d %H:%M")})
    if not st["go_pr"]:
        rl.log("pas de PR GO : la boucle s'arrête ici (relancer --resume quand la PR existe, ou --start-at correct).")
        st["phase"] = "correct"
        save(st)
        sys.exit(1)
    st["phase"] = "await_go"
    save(st)


def phase_await_go(st: dict, args) -> bool:
    """Vrai s'il y a un batch suivant."""
    pr = wait_closed(int(st["go_pr"]), args.poll, "GO")
    if not pr.get("merged_at"):
        rl.log("PR GO fermée sans merge : arrêt de la boucle.")
        st["phase"] = None
        save(st)
        return False
    # La tête de pile doit être mergée avant de repartir de main (sinon les lots repartiraient sans elle).
    if st.get("tip_pr"):
        try:
            if gh_pr(int(st["tip_pr"])).get("state") != "closed":
                wait_closed(int(st["tip_pr"]), args.poll, "tête de pile (à merger aussi)")
        except Exception as e:
            rl.log(f"    tête de pile : vérification impossible ({e})")
    m = LOTS_LINE_RE.findall(pr.get("body") or "")
    lots = (m[-1] if m else "aucun").split()
    st["history"].append({"phase": "await_go", "pr": st["go_pr"], "lots": lots, "at": time.strftime("%Y-%m-%d %H:%M")})
    if not lots or lots[0].lower() in ("aucun", "none", "-"):
        rl.log("GO mergé, `LOTS: aucun` : rien à corriger — fin de la boucle.")
        st["phase"] = None
        save(st)
        return False
    st["from"], st["until"] = lots[0], lots[-1]
    st["cycle"] = int(st.get("cycle") or 0) + 1
    st["phase"] = "batch"
    save(st)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="from_", help="premier lot du batch de départ")
    ap.add_argument("--until", help="dernier lot du batch de départ")
    ap.add_argument("--start-at", choices=["batch", "await_review", "await_pile", "correct", "await_go"], help="commencer à cette phase (pile déjà produite : await_review)")
    ap.add_argument("--resume", action="store_true", help="reprendre la phase mémorisée")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--cycles", type=int, default=3, help="nombre maximal de tours complets (défaut 3)")
    ap.add_argument("--poll", type=int, default=120, help="secondes entre deux lectures GitHub")
    ap.add_argument("--review-every", type=int, default=int(os.environ.get("BIM_REVIEW_EVERY", "4")))
    ap.add_argument("--model", default="", help="modèle des agents de lots (défaut run_lots)")
    ap.add_argument("--corrector-model", default=os.environ.get("BIM_CORRECTOR_MODEL", "claude-fable-5-thinking-xhigh"))
    ap.add_argument("--bot-wait-min", type=int, default=int(os.environ.get("BIM_BOT_WAIT_MIN", "45")), help="attente de la pré-revue Grok Bot par tranche (min ; 0 = aucune)")
    ap.add_argument("--stack-on-state", action="store_true", help="empiler le batch sur la pile déjà dans state.json (ne pas repartir de main) ; la revue couvrira toute la pile")
    args = ap.parse_args()

    st = load()
    if args.status:
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return
    if args.start_at:
        st["phase"] = args.start_at
        if args.from_ and args.until:
            st["from"], st["until"] = args.from_, args.until
    elif args.from_ and args.until:
        st.update({"phase": "batch", "from": args.from_, "until": args.until, "stack_on_state": bool(args.stack_on_state)})
    elif not args.resume or not st.get("phase"):
        sys.exit("Donner --from/--until pour démarrer, --start-at <phase>, ou --resume.")
    save(st)

    while st.get("phase"):
        if int(st.get("cycle") or 0) >= args.cycles and st["phase"] == "batch" and st["history"]:
            rl.log(f"{args.cycles} tour(s) faits : arrêt (relancer avec --resume pour continuer).")
            break
        phase = st["phase"]
        rl.log(f"═══ boucle — phase {phase} (tour {st.get('cycle', 0)})")
        if phase == "batch":
            phase_batch(st, args)
        elif phase in ("await_review", "await_pile"):
            phase_await_review(st, args)
        elif phase == "correct":
            phase_correct(st, args)
        elif phase == "await_go":
            if not phase_await_go(st, args):
                break
    rl.log("boucle terminée.")


if __name__ == "__main__":
    main()

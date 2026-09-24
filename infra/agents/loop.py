#!/usr/bin/env python3
"""La boucle (lot W4) : batch → recette du porteur → correcteur → GO → batch suivant.

Phases, mémorisées dans infra/agents/loop-state.json (reprise à tout moment) :

  batch         run_lots.py --from A --until B  (pré-vol, réviseur de nuit toutes les X PR, poste par lot)
  await_review  veille : le porteur coche et écrit ses KO QUAND IL VEUT ; un commentaire « revue finie »
                (ou « GO ») sur N'IMPORTE QUELLE PR de la pile — ou le merge de la tête — lance une
                session de correction avec ce qui est nouveau depuis la précédente (lot W7).
  correct       review_collect + plan_corrections.py --session n → PR « GO » (plan + lots)
  await_go      attendre le merge de la PR GO ; lire `LOTS: RB1 RB4` → batch RB1..RB4, EMPILÉ sur la
                pile si la tête n'est pas mergée (le porteur merge la tête quand il le décide) ;
                `LOTS: aucun` ou GO fermé sans merge → retour en veille.

Les seuls gestes humains : cocher les cases des PR (+ « KO : … »), écrire « revue finie » sur la dernière
PR relue, merger le GO — et la tête de pile quand on veut. Autant de sessions que voulu dans la journée.
run_lots.py lance cette veille tout seul en fin de batch ; le chien de garde (watchdog.py) la relance si
elle tombe. Le Mac reste allumé (`caffeinate -i`). Ne merge jamais lui-même.

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
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402
import review_collect as rc  # noqa: E402
import plan_corrections as pc  # noqa: E402

LOOP_JSON = rl.STATE_DIR / "loop-state.json"
LOTS_LINE_RE = re.compile(r"^\s*LOTS\s*:\s*(.+?)\s*$", re.I | re.M)


def setting(name: str, default: str) -> str:
    """Réglage BIM_* : variable d'environnement, sinon ~/.config/naviguide/simulator.env (comme run_lots),
    sinon la valeur par défaut. Avant le 22 sept., la boucle ne lisait que l'environnement : BIM_BOT_WAIT_MIN=15
    posé dans le fichier de clés était ignoré et chaque tranche attendait 45 min."""
    return os.environ.get(name) or rl._env_file_values().get(name) or default


REVIEW_DONE_RE = re.compile(r"\b(revue|review)\s+(finie|termin[ée]e|done|finished)\b|^\s*GO\s*[!.]?\s*$", re.I | re.M)
GO_FABLE_RE = re.compile(r"^\s*(?:\*\*)?GO\s+FABLE\b", re.I | re.M)   # lot W8 : le porteur accorde un lancement Fable de plus (et déclenche la session)


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


def gh_repo_comments_since(since_iso: str) -> list:
    """Tous les commentaires du dépôt depuis `since`, toutes PR confondues (un appel par page de 100 ;
    une nuit de bot et de réviseur en produit plus de 100)."""
    tok = rl.github_token_from_git()
    out: list = []
    for page in range(1, 11):
        q = urllib.parse.urlencode({"since": since_iso, "per_page": 100, "page": page, "sort": "created", "direction": "asc"})
        req = urllib.request.Request(f"https://api.github.com/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/issues/comments?{q}",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "bim-loop"})
        if tok:
            req.add_header("Authorization", f"Bearer {tok}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            chunk = json.loads(resp.read().decode())
        out.extend(chunk)
        if len(chunk) < 100:
            break
    return out


def stack_pr_numbers() -> list[int]:
    """Les PR de la pile (lots FINISHED de state.json), la tête en premier."""
    s = rl.State.load()
    nums = [rl.pr_number(e.get("pr")) for e in s.done.values() if e.get("status") == "FINISHED" and e.get("pr")]
    return [n for n in reversed(nums) if n]


def wait_review_signal(st: dict, poll_s: int) -> dict:
    """Lot W7 — revue à la volée : le porteur coche et écrit ses KO quand il veut ; quand il pose
    « revue finie » (ou « GO ») sur N'IMPORTE QUELLE PR de la pile — la dernière qu'il a relue —, la
    boucle part en correction avec tout ce qui est nouveau depuis la fois d'avant. Autant de fois qu'il
    veut dans la journée. Le merge de la tête de pile vaut aussi signal."""
    seen = set(st.get("review_signals_seen") or [])
    since = st.get("review_last_at") or st.get("batch_started_at") or time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime())
    rl.log(f"revue du porteur : « revue finie » sur n'importe quelle PR de la pile (ou merge de la tête) — nouveautés depuis {since}, un coup d'œil toutes les {poll_s} s")
    while True:
        try:
            tip = st.get("tip_pr") or tip_pr_number()
            if tip:
                pr = gh_pr(int(tip))
                if pr.get("state") == "closed":
                    rl.log(f"    tête de pile #{tip} fermée ({'mergée' if pr.get('merged_at') else 'non mergée'}) — revue considérée finie")
                    return {"signal": "closed", "merged": bool(pr.get("merged_at")), "pr": int(tip), "at": pr.get("closed_at")}
            stack = set(stack_pr_numbers())
            for c in gh_repo_comments_since(since):
                m = re.search(r"/issues/(\d+)$", c.get("issue_url") or "")
                num = int(m.group(1)) if m else None
                body = c.get("body") or ""
                if num not in stack or c.get("id") in seen or "🤖" in body[:40] or not rc.trusted(c):
                    continue
                if GO_FABLE_RE.search(body):
                    # Lot W8 : « GO FABLE » = un lancement Fable de plus aujourd'hui, et on part en session tout de suite.
                    day = time.strftime("%Y-%m-%d")
                    grants = st.setdefault("fable_grants", {})
                    grants[day] = int(grants.get(day) or 0) + 1
                    rl.log(f"    « GO FABLE » reçu sur #{num} ({(c.get('user') or {}).get('login')}) : {grants[day]} lancement(s) accordé(s) en plus aujourd'hui")
                    return {"signal": "go_fable", "merged": False, "pr": num, "id": c.get("id"), "at": c.get("created_at")}
                if REVIEW_DONE_RE.search(body):
                    rl.log(f"    signal « revue finie » reçu sur #{num} ({(c.get('user') or {}).get('login')}, {c.get('created_at')})")
                    return {"signal": "comment", "merged": False, "pr": num, "id": c.get("id"), "at": c.get("created_at")}
            auto = auto_trigger(st)
            if auto:
                return auto
        except Exception as e:
            rl.log(f"    GitHub indisponible ({e}) — nouvel essai")
        time.sleep(poll_s)


def fable_extra_runs(st: dict) -> int:
    return int((st.get("fable_grants") or {}).get(time.strftime("%Y-%m-%d")) or 0)


_auto_last_check = 0.0


def auto_trigger(st: dict) -> dict | None:
    """Lot W8 — OPTION, éteinte par défaut (BIM_CORRECTOR_AUTO=0 : pas de Fable sans revue humaine).
    Allumée : toutes les 10 min, on mesure le matériel non encore traité (KO, verdicts du bot, diffs) comme le
    correcteur le ferait ; s'il approche le budget d'un lancement (80 %), on ouvre une session sans attendre le
    porteur — dans la limite du plafond du jour (BIM_CORRECTOR_MAX_RUNS + GO FABLE)."""
    global _auto_last_check
    if setting("BIM_CORRECTOR_AUTO", "0") not in ("1", "true", "yes", "oui"):
        return None
    if time.time() - _auto_last_check < 600:
        return None
    _auto_last_check = time.time()
    try:
        prs = rc.prs_from_state()
        if not prs:
            return None
        state = rl.State.load()
        date = time.strftime("%Y-%m-%d")
        if pc.runs_today(state, date) >= pc.MAX_RUNS + fable_extra_runs(st):
            return None
        review = rc.collect(prs, rl.STATE_DIR / "auto-probe", images=False, since=st.get("review_last_at"), session=int(st.get("session") or 0) + 1)
        new_kos = sum(1 for p in review["prs"] for k in (p.get("ko") or []) if k.get("new", True))
        if not new_kos:
            return None
        est = pc.estimate(review, "", rl.ROOT, date)
        rl.log(f"    auto (BIM_CORRECTOR_AUTO) : {new_kos} KO nouveaux, ~{est['total']:,} tokens estimés / budget {est['budget']:,}".replace(",", " "))
        if est["total"] >= 0.8 * est["budget"]:
            return {"signal": "auto", "merged": False, "pr": None, "id": None, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    except Exception as e:
        rl.log(f"    auto : mesure impossible ({type(e).__name__})")
    return None


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


def finished_ids() -> set[str]:
    s = rl.State.load()
    return {lid for lid, e in s.done.items() if e.get("status") == "FINISHED"}


def must_resume(st: dict) -> bool:
    """Reprendre state.json (--resume) plutôt que repartir de main : quand on empile sur une pile non
    mergée, ou quand des lots de l'intervalle sont déjà FINISHED (boucle relancée en cours de batch —
    sans cela run_lots archiverait state.json et referait tout depuis main)."""
    if st.get("stack_on_state"):
        return True
    try:
        ids = [l.id for l in rl.parse_lots(rl.PROMPTS_MD.read_text(encoding="utf-8"))]
        rng = set(ids[ids.index(st["from"]): ids.index(st["until"]) + 1])
    except (ValueError, SystemExit):
        return False
    return bool(rng & finished_ids())


def phase_batch(st: dict, args) -> None:
    ensure_root_on_main()
    cmd = [sys.executable, str(HERE / "run_lots.py"), "--from", st["from"], "--until", st["until"], "--review-every", str(args.review_every),
           "--bot-wait-min", str(args.bot_wait_min)]
    if args.model:
        cmd += ["--model", args.model]
    if must_resume(st):
        # Empiler sur la pile déjà produite (state.json) au lieu de repartir de main : les lots
        # partent de la tête actuelle, et la revue couvre aussi les PR déjà là.
        cmd.append("--resume")
    before = finished_ids()
    st["batch_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save(st)
    code = run(cmd)
    new = finished_ids() - before
    st["history"].append({"phase": "batch", "from": st["from"], "until": st["until"], "rc": code, "new_lots": sorted(new), "at": time.strftime("%Y-%m-%d %H:%M")})
    try:   # lot W8 : la dépense de la nuit, lisible le matin dans COUTS.md (lots Grok inclus dans l'abonnement, mais comptés)
        reviews = [r for r in (rl.State.load().extra.get("reviews") or []) if str(r.get("at") or "").startswith(time.strftime("%Y-%m-%d"))]
        pc.note_cost(time.strftime("%Y-%m-%d"), int(st.get("session") or 0), "batch", [], 0, args.model or rl.DEFAULT_MODEL,
                     f"{len(new)} lot(s) codé(s), {len(reviews)} revue(s) de nuit")
    except Exception:
        pass
    if code != 0 and not new:
        # Rien n'est parti (pré-vol en échec, CLI, jeton…) : on reste en phase batch, on s'arrête ;
        # le chien de garde relance `--resume` après ses remèdes (au plus 3 fois par jour).
        rl.log(f"batch non parti (code {code}) — phase `batch` conservée ; corriger ce que le pré-vol signale puis `loop.py --resume`")
        save(st)
        sys.exit(code)
    st["tip_pr"] = tip_pr_number()
    st["stack_on_state"] = False
    st["phase"] = "await_review"
    save(st)


def phase_await_review(st: dict, args) -> None:
    n = st.get("tip_pr") or tip_pr_number()
    if not n:
        sys.exit("Aucune PR de tête de pile dans state.json : rien à attendre.")
    st["tip_pr"] = n
    save(st)
    sig = wait_review_signal(st, args.poll)
    st.setdefault("review_signals_seen", [])
    if sig.get("id"):
        st["review_signals_seen"].append(sig["id"])
    st["session"] = int(st.get("session") or 0) + 1
    st["review_since"] = st.get("review_last_at")          # ce qui est nouveau depuis la session précédente
    st["review_last_at"] = sig.get("at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    st["history"].append({"phase": "await_review", **sig, "session": st["session"], "at": time.strftime("%Y-%m-%d %H:%M")})
    st["phase"] = "correct"
    save(st)


def phase_correct(st: dict, args) -> None:
    ensure_root_on_main()
    cmd = [sys.executable, str(HERE / "plan_corrections.py"), "--model", args.corrector_model, "--session", str(st.get("session") or 1)]
    if st.get("review_since"):
        cmd += ["--since", st["review_since"]]
    if fable_extra_runs(st):
        cmd += ["--extra-runs", str(fable_extra_runs(st))]   # lot W8 : « GO FABLE » du porteur
    code = run(cmd, timeout=3 * 3600)
    s = rl.State.load()
    last = (s.extra.get("corrections") or [{}])[-1]
    st["go_pr"] = last.get("go_pr") if last.get("session") in (None, st.get("session")) else None   # le GO de CETTE session
    st["history"].append({"phase": "correct", "rc": code, "go_pr": st["go_pr"], "session": st.get("session"), "at": time.strftime("%Y-%m-%d %H:%M")})
    if code == 3:
        # Lot W8 : budget Fable atteint — la boucle reprend sa veille ; « GO FABLE » sur une PR de la pile autorise un lancement de plus.
        rl.log("correcteur non lancé (budget Fable atteint) — la boucle reprend sa veille ; « GO FABLE » sur une PR de la pile autorise un lancement de plus")
        st["phase"] = "await_review"
        save(st)
        return
    if not st["go_pr"]:
        rl.log("pas de PR GO : la boucle reprend sa veille (un nouveau « revue finie » relancera le correcteur ; ou --start-at correct).")
        st["phase"] = "await_review"
        save(st)
        return
    st["phase"] = "await_go"
    save(st)


def wait_go(st: dict, args) -> dict:
    """Attendre le merge du GO ; entre-temps, chaque commentaire « CORRIGER : » du porteur relance un
    agent Claude qui amende la PR (plan + lots) et répond dedans. Autant de tours que voulu."""
    n = int(st["go_pr"])
    seen = set(st.get("go_comments_seen") or [])
    rl.log(f"GO : PR #{n} — en attente du merge ; un commentaire « CORRIGER : … » la fait amender par un second agent")
    while True:
        try:
            pr = gh_pr(n)
            if pr.get("state") == "closed":
                rl.log(f"GO : PR #{n} fermée — {'mergée' if pr.get('merged_at') else 'NON mergée'}")
                return pr
            pending = [c for c in gh_comments(n) if c.get("id") not in seen and rc.trusted(c)
                       and re.match(r"^\s*(?:\*\*)?(CORRIGER|AMENDER|REVOIR|CHANGER)\s*:", (c.get("body") or "").strip(), re.I)]
            if pending:
                rl.log(f"    {len(pending)} commentaire(s) CORRIGER sur le GO → amendement")
                # `code`, pas `rc` : `rc` est le module review_collect (rc.trusted ci-dessus) — une variable
                # locale du même nom rendait tout `wait_go` inopérant dès le premier commentaire (24 sept., 03:27).
                code = run([sys.executable, str(HERE / "plan_corrections.py"), "--amend", str(n), "--model", args.corrector_model], timeout=2 * 3600)
                seen.update(c.get("id") for c in pending)
                st["go_comments_seen"] = sorted(seen)
                st["history"].append({"phase": "amend_go", "pr": n, "comments": len(pending), "rc": code, "at": time.strftime("%Y-%m-%d %H:%M")})
                save(st)
        except Exception as e:
            rl.log(f"    GitHub indisponible ({e}) — nouvel essai")
        time.sleep(args.poll)


def phase_await_go(st: dict, args) -> bool:
    """Vrai s'il y a un batch suivant."""
    pr = wait_go(st, args)
    if not pr.get("merged_at"):
        rl.log("PR GO fermée sans merge : la boucle reprend sa veille (un nouveau « revue finie » relancera le correcteur).")
        st["phase"] = "await_review"
        save(st)
        return True
    # Lot W7 : on n'attend PLUS le merge de la tête de pile. Si elle est encore ouverte, les correctifs
    # s'empilent dessus (--resume : les lots partent de la tête actuelle) ; si le porteur l'a mergée, on
    # repart de main. Le porteur merge la tête quand IL le décide.
    tip_open = False
    if st.get("tip_pr"):
        try:
            tip_open = gh_pr(int(st["tip_pr"])).get("state") != "closed"
        except Exception as e:
            rl.log(f"    tête de pile : vérification impossible ({e}) — on empile par prudence")
            tip_open = True
    m = LOTS_LINE_RE.findall(pr.get("body") or "")
    lots = (m[-1] if m else "aucun").split()
    st["history"].append({"phase": "await_go", "pr": st["go_pr"], "lots": lots, "tip_open": tip_open, "at": time.strftime("%Y-%m-%d %H:%M")})
    if not lots or lots[0].lower() in ("aucun", "none", "-"):
        rl.log("GO mergé, `LOTS: aucun` : rien à corriger — la boucle reprend sa veille.")
        st["phase"] = "await_review"
        save(st)
        return True
    st["from"], st["until"] = lots[0], lots[-1]
    st["stack_on_state"] = tip_open
    rl.log(f"GO mergé : batch {lots[0]} → {lots[-1]}, " + ("empilé sur la pile en cours (tête non mergée)" if tip_open else "depuis main (tête mergée)"))
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
    ap.add_argument("--cycles", type=int, default=100, help="nombre maximal de tours complets (défaut 100 : la boucle ne s'arrête pas seule)")
    ap.add_argument("--poll", type=int, default=120, help="secondes entre deux lectures GitHub")
    ap.add_argument("--review-every", type=int, default=int(setting("BIM_REVIEW_EVERY", "4")), help="réviseur de nuit toutes les N PR (BIM_REVIEW_EVERY)")
    ap.add_argument("--model", default="", help="modèle des agents de lots (défaut run_lots)")
    ap.add_argument("--corrector-model", default=setting("BIM_CORRECTOR_MODEL", "claude-fable-5-thinking-xhigh"), help="modèle du correcteur du matin (BIM_CORRECTOR_MODEL)")
    ap.add_argument("--bot-wait-min", type=int, default=int(setting("BIM_BOT_WAIT_MIN", "45")), help="attente de la pré-revue Grok Bot par tranche (min ; 0 = aucune ; BIM_BOT_WAIT_MIN)")
    ap.add_argument("--stack-on-state", action="store_true", help="empiler le batch sur la pile déjà dans state.json (ne pas repartir de main) ; la revue couvrira toute la pile")
    args = ap.parse_args()

    st = load()
    if args.status:
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return
    rl.start_watchdog()   # lot W6 : le chien de garde veille à côté de la boucle (boucle absente, tunnel, poste, bot…)
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

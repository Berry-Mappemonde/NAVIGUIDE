#!/usr/bin/env python3
"""Enchaîne les lots de docs/LOTS_ORDRE_ET_PROMPTS.md en agents Cloud Cursor, la nuit.

Un agent Cloud par lot (API Cursor `POST /v1/agents`, modèle Grok 4.6 Extra High
Fast), qui clone le dépôt, travaille, pousse une branche et ouvre la PR. Le
script attend la fin, vérifie la PR et sa CI, puis lance le lot suivant en
l'empilant sur la branche du précédent (pile linéaire : pas de conflit entre
lots ; le porteur merge dans l'ordre le matin). Bibliothèque standard seulement.

Usage (voir docs/LOTS_ORDRE_ET_PROMPTS.md § 3) :
    export CURSOR_API_KEY=…
    caffeinate -i python3 infra/agents/run_lots.py --from P2 --until L6
    python3 infra/agents/run_lots.py --only C1
    python3 infra/agents/run_lots.py --resume
    python3 infra/agents/run_lots.py --dry-run --from P2 --until O
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_MD = ROOT / "docs" / "LOTS_ORDRE_ET_PROMPTS.md"
STATE_JSON = Path(__file__).resolve().parent / "state.json"
LOG_FILE = Path(__file__).resolve().parent / "run_lots.log"

CURSOR_API = "https://api.cursor.com"
GITHUB_API = "https://api.github.com"
DEFAULT_REPO = "https://github.com/Berry-Mappemonde/Blue-Intelligence"
DEFAULT_MODEL = "cursor-grok-4.6-xhigh-fast"
TERMINAL = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}

LOT_RE = re.compile(
    r'<!--\s*LOT\s+id="(?P<id>[^"]+)"\s+title="(?P<title>[^"]*)"\s+plan="(?P<plan>[^"]*)"'
    r'\s+size="(?P<size>[^"]*)"\s+deps="(?P<deps>[^"]*)"\s*-->\s*```text\n(?P<prompt>.*?)\n```',
    re.S,
)


@dataclass
class Lot:
    id: str
    title: str
    plan: str
    size: str
    deps: list[str]
    prompt: str


@dataclass
class State:
    done: dict = field(default_factory=dict)   # id -> {status, branch, pr, agent, run}
    last_branch: str = "main"

    @classmethod
    def load(cls) -> "State":
        if STATE_JSON.exists():
            d = json.loads(STATE_JSON.read_text(encoding="utf-8"))
            return cls(done=d.get("done", {}), last_branch=d.get("last_branch", "main"))
        return cls()

    def save(self) -> None:
        STATE_JSON.write_text(json.dumps({"done": self.done, "last_branch": self.last_branch}, indent=2, ensure_ascii=False), encoding="utf-8")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- lots

def parse_lots(md: str) -> list[Lot]:
    lots = []
    for m in LOT_RE.finditer(md):
        deps = [d.strip() for d in m.group("deps").split(",") if d.strip()]
        lots.append(Lot(m.group("id"), m.group("title"), m.group("plan"), m.group("size"), deps, m.group("prompt").strip()))
    if not lots:
        sys.exit(f"Aucun lot trouvé dans {PROMPTS_MD} (balises <!-- LOT … --> attendues)")
    return lots


def select(lots: list[Lot], args) -> list[Lot]:
    ids = [l.id for l in lots]
    if args.only:
        missing = [x for x in args.only if x not in ids]
        if missing:
            sys.exit(f"Lots inconnus : {missing}. Connus : {ids}")
        return [l for l in lots if l.id in args.only]
    start = ids.index(args.from_) if args.from_ else 0
    end = ids.index(args.until) if args.until else len(ids) - 1
    if start > end:
        sys.exit("--from est après --until")
    return lots[start:end + 1]


# ---------------------------------------------------------------- http

class Http:
    def __init__(self, cursor_key: str, github_token: str | None):
        basic = base64.b64encode(f"{cursor_key}:".encode()).decode()
        self.cursor_headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/json", "User-Agent": "bim-run-lots"}
        self.github_headers = {"Accept": "application/vnd.github+json", "User-Agent": "bim-run-lots", "X-GitHub-Api-Version": "2022-11-28"}
        if github_token:
            self.github_headers["Authorization"] = f"Bearer {github_token}"

    def _call(self, url: str, headers: dict, method: str = "GET", body: dict | None = None, retries: int = 4):
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")[:400]
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    wait = 15 * (attempt + 1)
                    log(f"HTTP {e.code} sur {method} {url} — nouvel essai dans {wait}s ({text})")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"HTTP {e.code} {method} {url}: {text}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < retries - 1:
                    time.sleep(15 * (attempt + 1))
                    continue
                raise RuntimeError(f"réseau: {method} {url}: {e}") from e

    def cursor(self, path: str, method: str = "GET", body: dict | None = None):
        return self._call(f"{CURSOR_API}{path}", self.cursor_headers, method, body)

    def github(self, path: str, method: str = "GET", body: dict | None = None):
        return self._call(f"{GITHUB_API}{path}", self.github_headers, method, body)


def github_token_from_git() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        p = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True, timeout=20)
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        return None
    return None


# ---------------------------------------------------------------- cursor agents

def check_model(http: Http, model: str) -> None:
    models = http.cursor("/v1/models").get("items", [])
    ids = set()
    for m in models:
        ids.add(m.get("id"))
        for a in m.get("aliases", []) or []:
            ids.add(a)
    if model not in ids:
        known = sorted(i for i in ids if i)
        sys.exit(f"Modèle {model!r} absent de GET /v1/models. Disponibles : {known}")


def create_agent(http: Http, lot: Lot, prompt: str, repo: str, ref: str, model: str) -> tuple[str, str]:
    body = {
        "prompt": {"text": prompt},
        "model": {"id": model},
        "repos": [{"url": repo, "startingRef": ref}],
        "workOnCurrentBranch": False,
        "autoCreatePR": True,
        "name": f"Lot {lot.id} — {lot.title}"[:100],
    }
    d = http.cursor("/v1/agents", "POST", body)
    agent_id = d["agent"]["id"]
    run_id = d["run"]["id"]
    log(f"[{lot.id}] agent {agent_id} run {run_id} depuis {ref} — https://cursor.com/agents/{agent_id}")
    return agent_id, run_id


def follow_up(http: Http, agent_id: str, text: str) -> str:
    d = http.cursor(f"/v1/agents/{agent_id}/runs", "POST", {"prompt": {"text": text}})
    return d["run"]["id"]


def wait_run(http: Http, agent_id: str, run_id: str, timeout_s: int, poll_s: int) -> dict:
    t0 = time.time()
    last = None
    while True:
        run = http.cursor(f"/v1/agents/{agent_id}/runs/{run_id}")
        status = run.get("status")
        if status != last:
            log(f"    run {run_id}: {status}")
            last = status
        if status in TERMINAL:
            return run
        if time.time() - t0 > timeout_s:
            log(f"    délai dépassé ({timeout_s // 3600} h) — annulation")
            try:
                http.cursor(f"/v1/agents/{agent_id}/runs/{run_id}/cancel", "POST", {})
            except RuntimeError as e:
                log(f"    annulation impossible: {e}")
            run["status"] = "TIMEOUT"
            return run
        time.sleep(poll_s)


def pushed_branch(run: dict, repo: str) -> str | None:
    repo_key = repo.replace("https://", "").rstrip("/")
    for b in (run.get("git") or {}).get("branches", []) or []:
        if repo_key in (b.get("repoUrl") or "") or not b.get("repoUrl"):
            return b.get("branch")
    return None


# ---------------------------------------------------------------- github

def owner_repo(repo: str) -> str:
    return repo.replace("https://github.com/", "").rstrip("/")


def find_pr(http: Http, repo: str, branch: str) -> dict | None:
    org = owner_repo(repo).split("/")[0]
    q = urllib.parse.urlencode({"head": f"{org}:{branch}", "state": "open"})
    prs = http.github(f"/repos/{owner_repo(repo)}/pulls?{q}")
    return prs[0] if prs else None


def ci_status(http: Http, repo: str, sha: str) -> tuple[str, list[str]]:
    d = http.github(f"/repos/{owner_repo(repo)}/commits/{sha}/check-runs")
    runs = d.get("check_runs", [])
    if not runs:
        return "none", []
    failed = [r["name"] for r in runs if r.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")]
    pending = [r["name"] for r in runs if r.get("status") != "completed"]
    if failed:
        return "failure", failed
    if pending:
        return "pending", pending
    return "success", []


def wait_ci(http: Http, repo: str, branch: str, max_min: int) -> tuple[str, list[str], dict | None]:
    t0 = time.time()
    pr = None
    while time.time() - t0 < max_min * 60:
        pr = find_pr(http, repo, branch)
        if pr:
            status, names = ci_status(http, repo, pr["head"]["sha"])
            if status in ("success", "failure"):
                return status, names, pr
        time.sleep(60)
    return "pending", [], pr


# ---------------------------------------------------------------- main loop

def base_line(ref: str) -> str:
    if ref == "main":
        return "Base de travail : `main` à jour (ton dépôt est cloné sur main). Crée ta branche depuis main."
    return (f"Base de travail : ton dépôt est cloné sur la branche `{ref}` (lot précédent, pas encore mergé). "
            f"Crée ta branche depuis `{ref}`, n'y touche pas, et ouvre ta PR vers `main` (le diff inclura le lot précédent : c'est attendu, il fondra quand il sera mergé).")


def run_lot(http: Http, lot: Lot, state: State, args) -> None:
    ref = "main" if args.stack == "none" else state.last_branch
    prompt = base_line(ref) + "\n\n" + lot.prompt
    if args.dry_run:
        print(f"\n===== {lot.id} — {lot.title} (depuis {ref})\n{prompt}\n")
        return
    agent_id, run_id = create_agent(http, lot, prompt, args.repo, ref, args.model)
    run = wait_run(http, agent_id, run_id, args.timeout_hours * 3600, args.poll)
    if run.get("status") != "FINISHED":
        log(f"[{lot.id}] premier passage : {run.get('status')} — une relance")
        run_id = follow_up(http, agent_id, "Reprends là où tu t'es arrêté : finis le lot, lance les tests, pousse la branche et ouvre la PR (ne merge pas). Si un point bloque, choisis la solution la plus simple et note-la dans la PR.")
        run = wait_run(http, agent_id, run_id, args.timeout_hours * 3600 // 2, args.poll)
    branch = pushed_branch(run, args.repo)
    entry = {"status": run.get("status"), "branch": branch, "agent": agent_id, "run": run_id, "pr": None, "ci": None, "result": (run.get("result") or "")[:500]}
    if run.get("status") != "FINISHED" or not branch:
        log(f"[{lot.id}] RATÉ ({run.get('status')}, branche={branch}) — on continue depuis {state.last_branch}")
        entry["status"] = entry["status"] or "ERROR"
        state.done[lot.id] = entry
        state.save()
        return
    log(f"[{lot.id}] branche poussée : {branch} — attente PR + CI (≤ {args.ci_wait_min} min)")
    status, names, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
    if pr:
        entry["pr"] = pr["html_url"]
        log(f"[{lot.id}] PR {pr['number']} {pr['html_url']} — CI {status} {names or ''}")
    else:
        log(f"[{lot.id}] aucune PR trouvée pour {branch} (autoCreatePR ?) — à ouvrir à la main")
    if status == "failure":
        log(f"[{lot.id}] CI rouge — une relance de correction")
        run_id = follow_up(http, agent_id, "La CI de ta PR échoue sur : " + ", ".join(names) + ". Lis les journaux de la CI (GitHub Actions), corrige, relance les tests en local, pousse. Ne merge pas. Ne retire aucune surface visible.")
        run = wait_run(http, agent_id, run_id, args.timeout_hours * 3600 // 2, args.poll)
        status, names, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
        log(f"[{lot.id}] CI après correction : {status} {names or ''}")
    entry["ci"] = status
    state.done[lot.id] = entry
    state.last_branch = branch
    state.save()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="from_", help="premier lot (id)")
    ap.add_argument("--until", help="dernier lot (id)")
    ap.add_argument("--only", nargs="+", help="un ou plusieurs lots précis")
    ap.add_argument("--stack", choices=["linear", "none"], default="linear", help="linear : chaque lot part de la branche du précédent (défaut) ; none : chacun depuis main")
    ap.add_argument("--resume", action="store_true", help="reprend state.json : saute les lots déjà FINISHED")
    ap.add_argument("--dry-run", action="store_true", help="affiche les prompts, ne lance rien")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--timeout-hours", type=float, default=3.0)
    ap.add_argument("--poll", type=int, default=60, help="secondes entre deux lectures d'état")
    ap.add_argument("--ci-wait-min", type=int, default=25)
    args = ap.parse_args()

    lots = select(parse_lots(PROMPTS_MD.read_text(encoding="utf-8")), args)
    state = State.load() if args.resume else State()
    if not args.resume and STATE_JSON.exists() and not args.dry_run:
        STATE_JSON.rename(STATE_JSON.with_suffix(f".{int(time.time())}.json"))

    if args.dry_run:
        http = None
    else:
        key = os.environ.get("CURSOR_API_KEY")
        if not key:
            sys.exit("CURSOR_API_KEY manquant (cursor.com → Dashboard → Integrations).")
        http = Http(key, github_token_from_git())
        check_model(http, args.model)
        me = http.cursor("/v1/me")
        log(f"connecté : {me.get('userEmail') or me.get('email') or me}")

    log(f"lots : {[l.id for l in lots]} — pile {args.stack} — modèle {args.model}")
    for lot in lots:
        prev = state.done.get(lot.id)
        if args.resume and prev and prev.get("status") == "FINISHED":
            log(f"[{lot.id}] déjà fait ({prev.get('pr')}) — sauté")
            continue
        missing = [d for d in lot.deps if d not in state.done or state.done[d].get("status") != "FINISHED"]
        if missing and args.stack == "linear" and not args.dry_run:
            log(f"[{lot.id}] dépendances non faites dans cette session : {missing} — le lot est lancé quand même (le plan les suppose mergées ou dans la pile) ; vérifier le matin")
        run_lot(http, lot, state, args)

    if not args.dry_run:
        log("terminé. Récapitulatif :")
        for lid, e in state.done.items():
            log(f"  {lid}: {e.get('status')} — {e.get('pr') or e.get('branch')} — CI {e.get('ci')}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Enchaîne les lots de docs/LOTS_ORDRE_ET_PROMPTS.md, un agent Cursor par lot, la nuit.

Deux façons de faire tourner l'agent :

  --runtime local  (défaut)  le CLI Cursor `agent -p --force` sur ce Mac, dans un
                             worktree git par lot (~/bim-lots/<lot>), node_modules et
                             .venv partagés par lien : les tests, le build et Playwright
                             tournent vraiment ; le modèle est celui du compte (Grok 4.6).
  --runtime cloud            l'API Cloud Agents de Cursor (`POST /v1/agents`) : un agent
                             sur une machine Cursor, qui pousse une branche et ouvre la PR.

Dans les deux cas : pile linéaire (chaque lot part de la branche du précédent),
attente de la fin, une relance sur échec, PR + CI (une relance si rouge),
state.json pour reprendre. Ne merge jamais. Bibliothèque standard seulement.

Usage (voir docs/LOTS_ORDRE_ET_PROMPTS.md § 3) :
    python3 infra/agents/run_lots.py --check                       # vérifie l'environnement, ne lance rien
    python3 infra/agents/run_lots.py --only C1                     # un lot, en local
    caffeinate -i python3 infra/agents/run_lots.py --from P2 --until L6
    python3 infra/agents/run_lots.py --runtime cloud --only C1     # via l'API (CURSOR_API_KEY)
    python3 infra/agents/run_lots.py --resume
    python3 infra/agents/run_lots.py --dry-run --from P2 --until O
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
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
HERE = Path(__file__).resolve().parent
STATE_JSON = HERE / "state.json"
LOG_FILE = HERE / "run_lots.log"
WORKTREES = Path(os.environ.get("BIM_LOTS_DIR", str(Path.home() / "bim-lots")))

CURSOR_API = "https://api.cursor.com"
GITHUB_API = "https://api.github.com"
DEFAULT_REPO = "https://github.com/Berry-Mappemonde/Blue-Intelligence"
DEFAULT_MODEL = "cursor-grok-4.6-xhigh-fast"
TERMINAL = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}
AGENT_BIN = os.environ.get("BIM_AGENT_BIN") or shutil.which("agent") or str(Path.home() / ".local" / "bin" / "agent")

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
    done: dict = field(default_factory=dict)   # id -> {status, branch, pr, ci, …}
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


def sh(args: list[str], cwd: Path | None = None, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=check)


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
    def __init__(self, cursor_key: str | None, github_token: str | None):
        self.cursor_headers = {"Content-Type": "application/json", "User-Agent": "bim-run-lots"}
        if cursor_key:
            basic = base64.b64encode(f"{cursor_key}:".encode()).decode()
            self.cursor_headers["Authorization"] = f"Basic {basic}"
        self.github_headers = {"Accept": "application/vnd.github+json", "User-Agent": "bim-run-lots", "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
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
        p2 = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, timeout=20)
        for line in p2.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        return None
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


# ---------------------------------------------------------------- cloud runtime

def cloud_check_model(http: Http, model: str) -> list[str]:
    models = http.cursor("/v1/models").get("items", [])
    ids = set()
    for m in models:
        ids.add(m.get("id"))
        for a in m.get("aliases", []) or []:
            ids.add(a)
    known = sorted(i for i in ids if i)
    if model not in ids:
        sys.exit(f"Modèle {model!r} absent de GET /v1/models. Disponibles : {known}")
    return known


def cloud_create(http: Http, lot: Lot, prompt: str, repo: str, ref: str, model: str) -> tuple[str, str]:
    body = {
        "prompt": {"text": prompt},
        "model": {"id": model},
        "repos": [{"url": repo, "startingRef": ref}],
        "workOnCurrentBranch": False,
        "autoCreatePR": True,
        "name": f"Lot {lot.id} — {lot.title}"[:100],
    }
    d = http.cursor("/v1/agents", "POST", body)
    agent_id, run_id = d["agent"]["id"], d["run"]["id"]
    log(f"[{lot.id}] agent cloud {agent_id} run {run_id} depuis {ref} — https://cursor.com/agents/{agent_id}")
    return agent_id, run_id


def cloud_follow_up(http: Http, agent_id: str, text: str) -> str:
    return http.cursor(f"/v1/agents/{agent_id}/runs", "POST", {"prompt": {"text": text}})["run"]["id"]


def cloud_wait(http: Http, agent_id: str, run_id: str, timeout_s: int, poll_s: int) -> dict:
    t0, last = time.time(), None
    while True:
        run = http.cursor(f"/v1/agents/{agent_id}/runs/{run_id}")
        status = run.get("status")
        if status != last:
            log(f"    run {run_id}: {status}")
            last = status
        if status in TERMINAL:
            return run
        if time.time() - t0 > timeout_s:
            log(f"    délai dépassé — annulation")
            try:
                http.cursor(f"/v1/agents/{agent_id}/runs/{run_id}/cancel", "POST", {})
            except RuntimeError as e:
                log(f"    annulation impossible: {e}")
            run["status"] = "TIMEOUT"
            return run
        time.sleep(poll_s)


def cloud_branch(run: dict, repo: str) -> str | None:
    repo_key = repo.replace("https://", "").rstrip("/")
    for b in (run.get("git") or {}).get("branches", []) or []:
        if repo_key in (b.get("repoUrl") or "") or not b.get("repoUrl"):
            return b.get("branch")
    return None


def run_lot_cloud(http: Http, lot: Lot, prompt: str, ref: str, args) -> dict:
    agent_id, run_id = cloud_create(http, lot, prompt, args.repo, ref, args.model)
    run = cloud_wait(http, agent_id, run_id, int(args.timeout_hours * 3600), args.poll)
    if run.get("status") != "FINISHED":
        log(f"[{lot.id}] premier passage : {run.get('status')} — une relance")
        run_id = cloud_follow_up(http, agent_id, RESUME_TEXT)
        run = cloud_wait(http, agent_id, run_id, int(args.timeout_hours * 1800), args.poll)
    return {"status": run.get("status"), "branch": cloud_branch(run, args.repo), "agent": agent_id, "run": run_id,
            "result": (run.get("result") or "")[:500],
            "fix": lambda names: cloud_wait(http, agent_id, cloud_follow_up(http, agent_id, fix_text(names)), int(args.timeout_hours * 1800), args.poll)}


# ---------------------------------------------------------------- local runtime (CLI dans un worktree)

def local_check() -> dict:
    info = {"agent": None, "logged": False, "models": []}
    if not Path(AGENT_BIN).exists():
        return info
    v = sh([AGENT_BIN, "--version"], check=False, timeout=30)
    info["agent"] = (v.stdout or v.stderr).strip()
    st = sh([AGENT_BIN, "status"], check=False, timeout=60)
    info["logged"] = "Not logged in" not in (st.stdout + st.stderr)
    if info["logged"]:
        m = sh([AGENT_BIN, "models"], check=False, timeout=60)
        info["models"] = [ln.strip() for ln in (m.stdout or "").splitlines() if ln.strip()]
    return info


def resolve_local_model(models: list[str], requested: str) -> str:
    """`agent models` liste les identifiants du compte ; on prend celui demandé s'il y est,
    sinon l'unique candidat « grok », sinon on s'arrête avec la liste."""
    if not requested or not models:
        return requested
    ids = [m.split()[0] for m in models]
    if requested in ids or any(requested == m for m in models):
        return requested
    cands = [i for i in ids if "grok" in i.lower()]
    if len(cands) == 1:
        log(f"modèle {requested!r} inconnu du CLI ; on prend {cands[0]!r}")
        return cands[0]
    sys.exit(f"Modèle {requested!r} inconnu du CLI. Passer --model avec l'un de : {ids}")


def prepare_worktree(lot: Lot, ref: str) -> Path:
    WORKTREES.mkdir(parents=True, exist_ok=True)
    path = WORKTREES / lot.id.lower()
    if path.exists():
        sh(["git", "worktree", "remove", "--force", str(path)], cwd=ROOT, check=False)
        shutil.rmtree(path, ignore_errors=True)
    sh(["git", "worktree", "prune"], cwd=ROOT, check=False)
    sh(["git", "fetch", "-q", "origin"], cwd=ROOT, check=False, timeout=120)
    target = ref
    if ref == "main":
        target = "origin/main"
    elif sh(["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT, check=False).returncode != 0:
        target = f"origin/{ref}"
    sh(["git", "worktree", "add", "--detach", str(path), target], cwd=ROOT, timeout=300)
    # Dépendances partagées par lien : les tests et le build tournent sans réinstaller.
    sim = ROOT / "naviguide-simulator"
    linked = []
    for rel in ("naviguide-simulator/node_modules", "naviguide-simulator/.venv", "node_modules", "frontend/node_modules"):
        src = ROOT / rel
        dst = path / rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src, target_is_directory=True)
            linked.append(rel)
    # Un lien symbolique n'est pas un dossier pour git : les motifs « node_modules/ » ne
    # l'ignorent pas. On l'exclut dans le worktree pour qu'un `git add -A` ne l'embarque pas.
    if linked:
        exclude = Path(sh(["git", "rev-parse", "--git-path", "info/exclude"], cwd=path).stdout.strip())
        if not exclude.is_absolute():
            exclude = path / exclude
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as f:
            f.write("\n".join(f"/{rel}" for rel in linked) + "\n")
    env = sim / "server" / ".env"
    if env.exists() and not (path / "naviguide-simulator" / "server" / ".env").exists():
        shutil.copy2(env, path / "naviguide-simulator" / "server" / ".env")
    return path


def local_prefix(path: Path, ref: str) -> str:
    return (f"Environnement : tu travailles dans le worktree git {path} (dépôt principal : {ROOT}). "
            f"node_modules et .venv sont des liens vers le dépôt principal : ne lance ni npm install ni pip install sauf nécessité absolue. "
            f"Le worktree est sur un HEAD détaché à `{ref}` : commence par `git checkout -b <ta-branche>`. "
            f"Quand tout est vert : `git push -u origin <ta-branche>` puis ouvre la PR avec "
            f"`python3 infra/agents/open_pr.py <ta-branche> main \"<titre>\" /tmp/pr-<lot>.md` (écris d'abord le corps de la PR dans ce fichier). "
            f"Ne pose aucune question : décide et note dans la PR.")


def run_agent_cli(path: Path, prompt: str, model: str, timeout_s: int, resume: bool = False) -> tuple[str, str]:
    cmd = [AGENT_BIN, "-p", "--force", "--trust", "--workspace", str(path), "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    if resume:
        cmd += ["--continue"]
    cmd.append(prompt)
    try:
        p = subprocess.run(cmd, cwd=str(path), text=True, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    out = p.stdout.strip()
    result = out
    for chunk in reversed(out.splitlines()):
        try:
            d = json.loads(chunk)
            if isinstance(d, dict):
                result = d.get("result") or d.get("text") or out
                if d.get("is_error"):
                    return "ERROR", str(result)[:800]
                break
        except json.JSONDecodeError:
            continue
    if p.returncode != 0:
        return "ERROR", (p.stderr or out)[-800:]
    return "FINISHED", str(result)[-800:]


def local_branch(path: Path) -> str | None:
    b = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, check=False).stdout.strip()
    return None if not b or b == "HEAD" else b


def ensure_pushed(path: Path, branch: str) -> bool:
    remote = sh(["git", "ls-remote", "--heads", "origin", branch], cwd=path, check=False, timeout=60).stdout.strip()
    local_sha = sh(["git", "rev-parse", "HEAD"], cwd=path, check=False).stdout.strip()
    if remote and local_sha and remote.split()[0] == local_sha:
        return True
    p = sh(["git", "push", "-u", "origin", branch], cwd=path, check=False, timeout=300)
    if p.returncode != 0:
        log(f"    push impossible: {p.stderr.strip()[-300:]}")
        return False
    return True


def ensure_pr(http: Http, args, lot: Lot, branch: str, result: str) -> None:
    if find_pr(http, args.repo, branch):
        return
    body = HERE / f".pr-{lot.id}.md"
    body.write_text(f"## Lot {lot.id} — {lot.title}\n\nPR ouverte par run_lots.py (l'agent ne l'avait pas ouverte). "
                    f"Plan : `{lot.plan}`.\n\n### Compte rendu de l'agent\n\n{result}\n", encoding="utf-8")
    p = sh([sys.executable, str(HERE / "open_pr.py"), branch, "main", f"lot {lot.id} — {lot.title}", str(body)], cwd=ROOT, check=False, timeout=90)
    log(f"    {('PR ouverte par le script: ' + p.stdout.strip()) if p.returncode == 0 else ('ouverture PR impossible: ' + (p.stderr or p.stdout)[-300:])}")
    body.unlink(missing_ok=True)


def run_lot_local(http: Http, lot: Lot, prompt: str, ref: str, args) -> dict:
    path = prepare_worktree(lot, ref)
    log(f"[{lot.id}] worktree {path} depuis {ref} — agent local ({args.model or 'modèle par défaut du compte'})")
    status, result = run_agent_cli(path, local_prefix(path, ref) + "\n\n" + prompt, args.model, int(args.timeout_hours * 3600))
    log(f"    agent: {status}")
    if status != "FINISHED":
        log(f"[{lot.id}] premier passage : {status} — une relance")
        status, result = run_agent_cli(path, RESUME_TEXT, args.model, int(args.timeout_hours * 1800), resume=True)
        log(f"    relance: {status}")
    branch = local_branch(path)
    if branch is None:
        # L'agent a peut-être commité sur le HEAD détaché : on lui donne une branche.
        dirty = sh(["git", "status", "--porcelain"], cwd=path, check=False).stdout.strip()
        ahead = sh(["git", "rev-list", "--count", f"{ref if ref != 'main' else 'origin/main'}..HEAD"], cwd=path, check=False).stdout.strip()
        if ahead and ahead != "0" and not dirty:
            branch = f"lot/{lot.id.lower()}-auto"
            sh(["git", "checkout", "-b", branch], cwd=path, check=False)
    if branch and ensure_pushed(path, branch):
        ensure_pr(http, args, lot, branch, result)
    else:
        status = "ERROR" if status == "FINISHED" else status
    return {"status": status, "branch": branch, "worktree": str(path), "result": result[:500],
            "fix": lambda names: run_agent_cli(path, fix_text(names), args.model, int(args.timeout_hours * 1800), resume=True)}


# ---------------------------------------------------------------- boucle commune

RESUME_TEXT = ("Reprends là où tu t'es arrêté : finis le lot, lance les tests, pousse la branche et ouvre la PR (ne merge pas). "
               "Si un point bloque, choisis la solution la plus simple et note-la dans la PR.")


def fix_text(names: list[str]) -> str:
    return ("La CI de ta PR échoue sur : " + ", ".join(names) + ". Lis les journaux de la CI (GitHub Actions), corrige, "
            "relance les tests en local, pousse. Ne merge pas. Ne retire aucune surface visible.")


def base_line(ref: str) -> str:
    if ref == "main":
        return "Base de travail : `main` à jour. Crée ta branche depuis main."
    return (f"Base de travail : la branche `{ref}` (lot précédent, pas encore mergé). Crée ta branche depuis `{ref}`, n'y touche pas, "
            f"et ouvre ta PR vers `main` (le diff inclura le lot précédent : c'est attendu, il fondra quand il sera mergé).")


def run_lot(http: Http | None, lot: Lot, state: State, args) -> None:
    ref = "main" if args.stack == "none" else state.last_branch
    prompt = base_line(ref) + "\n\n" + lot.prompt
    if args.dry_run:
        print(f"\n===== {lot.id} — {lot.title} (depuis {ref}, runtime {args.runtime})\n{prompt}\n")
        return
    out = run_lot_cloud(http, lot, prompt, ref, args) if args.runtime == "cloud" else run_lot_local(http, lot, prompt, ref, args)
    entry = {k: v for k, v in out.items() if k != "fix"}
    entry.update({"pr": None, "ci": None})
    branch = out.get("branch")
    if out.get("status") != "FINISHED" or not branch:
        log(f"[{lot.id}] RATÉ ({out.get('status')}, branche={branch}) — on continue depuis {state.last_branch}")
        entry["status"] = entry.get("status") or "ERROR"
        state.done[lot.id] = entry
        state.save()
        return
    log(f"[{lot.id}] branche : {branch} — attente PR + CI (≤ {args.ci_wait_min} min)")
    status, names, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
    if pr:
        entry["pr"] = pr["html_url"]
        log(f"[{lot.id}] PR {pr['number']} {pr['html_url']} — CI {status} {names or ''}")
    else:
        log(f"[{lot.id}] aucune PR trouvée pour {branch} — à ouvrir à la main")
    if status == "failure":
        log(f"[{lot.id}] CI rouge — une relance de correction")
        out["fix"](names)
        if args.runtime == "local":
            ensure_pushed(Path(out["worktree"]), branch)
        status, names, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
        log(f"[{lot.id}] CI après correction : {status} {names or ''}")
    entry["ci"] = status
    state.done[lot.id] = entry
    state.last_branch = branch
    state.save()


# ---------------------------------------------------------------- check

def check(args) -> None:
    ok = True
    print(f"Dépôt : {ROOT}")
    print(f"Prompts : {PROMPTS_MD} — {len(parse_lots(PROMPTS_MD.read_text(encoding='utf-8')))} lots")
    tok = github_token_from_git()
    print(f"Jeton GitHub : {'présent' if tok else 'ABSENT (export GITHUB_TOKEN=… ou git credential)'}")
    ok &= bool(tok)
    if args.runtime == "local":
        info = local_check()
        if not info["agent"]:
            print("CLI Cursor : ABSENT — installer : curl https://cursor.com/install -fsS | bash")
            ok = False
        else:
            print(f"CLI Cursor : {info['agent']} — {'connecté' if info['logged'] else 'NON CONNECTÉ : lancer `agent login` (navigateur) une fois'}")
            ok &= info["logged"]
            if info["models"]:
                print("Modèles du compte :")
                for m in info["models"]:
                    print("   ", m)
                if args.model and not any(args.model in m for m in info["models"]):
                    print(f"   !! {args.model!r} n'apparaît pas tel quel : passer --model avec un des identifiants ci-dessus (ex. celui qui contient « grok »)")
        for rel in ("naviguide-simulator/node_modules", "naviguide-simulator/.venv"):
            print(f"{rel} : {'présent' if (ROOT / rel).exists() else 'ABSENT (npm ci / python -m venv .venv + pip install -r server/requirements.txt)'}")
            ok &= (ROOT / rel).exists()
        print(f"Worktrees : {WORKTREES} ({'existe' if WORKTREES.exists() else 'sera créé'})")
    else:
        key = os.environ.get("CURSOR_API_KEY")
        print(f"CURSOR_API_KEY : {'présent' if key else 'ABSENT — cursor.com/dashboard → Integrations → User API Keys → Create'}")
        if key:
            http = Http(key, tok)
            try:
                me = http.cursor("/v1/me")
                print(f"Compte : {me}")
                known = cloud_check_model(http, args.model)
                print(f"Modèle {args.model} : disponible ({len(known)} modèles au total)")
            except (RuntimeError, SystemExit) as e:
                print(f"API Cursor : {e}")
                ok = False
        else:
            ok = False
    print("\nRÉSULTAT :", "prêt" if ok else "pas encore prêt (voir ci-dessus)")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runtime", choices=["local", "cloud"], default="local")
    ap.add_argument("--check", action="store_true", help="vérifie l'environnement et s'arrête")
    ap.add_argument("--from", dest="from_", help="premier lot (id)")
    ap.add_argument("--until", help="dernier lot (id)")
    ap.add_argument("--only", nargs="+", help="un ou plusieurs lots précis")
    ap.add_argument("--stack", choices=["linear", "none"], default="linear", help="linear : chaque lot part de la branche du précédent (défaut) ; none : chacun depuis main")
    ap.add_argument("--resume", action="store_true", help="reprend state.json : saute les lots déjà FINISHED")
    ap.add_argument("--dry-run", action="store_true", help="affiche les prompts, ne lance rien")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="identifiant de modèle (cloud : GET /v1/models ; local : `agent models`) ; '' = défaut du compte")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--timeout-hours", type=float, default=3.0)
    ap.add_argument("--poll", type=int, default=60, help="secondes entre deux lectures d'état (cloud)")
    ap.add_argument("--ci-wait-min", type=int, default=25)
    args = ap.parse_args()

    if args.check:
        check(args)
        return

    lots = select(parse_lots(PROMPTS_MD.read_text(encoding="utf-8")), args)
    state = State.load() if args.resume else State()
    if not args.resume and STATE_JSON.exists() and not args.dry_run:
        STATE_JSON.rename(STATE_JSON.with_suffix(f".{int(time.time())}.json"))

    http = None
    if not args.dry_run:
        tok = github_token_from_git()
        if not tok:
            sys.exit("Jeton GitHub absent (GITHUB_TOKEN ou trousseau git) : nécessaire pour retrouver les PR et la CI.")
        if args.runtime == "cloud":
            key = os.environ.get("CURSOR_API_KEY")
            if not key:
                sys.exit("CURSOR_API_KEY manquant (cursor.com/dashboard → Integrations → User API Keys).")
            http = Http(key, tok)
            cloud_check_model(http, args.model)
            log(f"connecté (cloud) : {http.cursor('/v1/me')}")
        else:
            info = local_check()
            if not info["agent"] or not info["logged"]:
                sys.exit("CLI Cursor absent ou non connecté : `curl https://cursor.com/install -fsS | bash` puis `agent login`.")
            http = Http(None, tok)
            args.model = resolve_local_model(info["models"], args.model)
            log(f"CLI Cursor {info['agent']} connecté ; modèle : {args.model or 'défaut du compte'}")

    log(f"lots : {[l.id for l in lots]} — runtime {args.runtime} — pile {args.stack}")
    for lot in lots:
        prev = state.done.get(lot.id)
        if args.resume and prev and prev.get("status") == "FINISHED":
            log(f"[{lot.id}] déjà fait ({prev.get('pr')}) — sauté")
            continue
        missing = [d for d in lot.deps if d not in state.done or state.done[d].get("status") != "FINISHED"]
        if missing and args.stack == "linear" and not args.dry_run:
            log(f"[{lot.id}] dépendances non faites dans cette session : {missing} — lancé quand même (le plan les suppose mergées ou dans la pile) ; vérifier le matin")
        run_lot(http, lot, state, args)

    if not args.dry_run:
        log("terminé. Récapitulatif :")
        for lid, e in state.done.items():
            log(f"  {lid}: {e.get('status')} — {e.get('pr') or e.get('branch')} — CI {e.get('ci')}")


if __name__ == "__main__":
    main()

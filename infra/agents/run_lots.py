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

Fin de batch (lot W0) : quand le dernier lot est passé, le script prépare le
poste de recette du porteur — build de prod de la dernière branche, clés lues
dans ~/.config/naviguide/simulator.env, API :8010 + interface :5174 du même
checkout, navigateur ouvert, et infra/agents/RECETTE_DU_BATCH.md : ce qu'il
faut regarder écran par écran, puis l'ordre des merges. `--recette` refait ce
poste seul (sans lancer de lot), `--no-recette` l'omet.

Recette à la volée (lot W1) : après CHAQUE lot, le poste est rebâti sur la tête
de pile (sans ouvrir de fenêtre) et le md régénéré avec les cases cochées par le
porteur dans les PR (open_pr.py transforme la Recette en cases à cocher) et ses
commentaires « KO : … ». `--no-recette-each` pour ne le faire qu'en fin de batch.
La boucle complète (revue → correcteur → GO → batch suivant) : loop.py.

Usage (voir docs/LOTS_ORDRE_ET_PROMPTS.md § 3) :
    python3 infra/agents/run_lots.py --check                       # vérifie l'environnement, ne lance rien
    python3 infra/agents/run_lots.py --only C1                     # un lot, en local
    caffeinate -i python3 infra/agents/run_lots.py --from P2 --until L6
    python3 infra/agents/run_lots.py --runtime cloud --only C1     # via l'API (CURSOR_API_KEY)
    python3 infra/agents/run_lots.py --resume
    python3 infra/agents/run_lots.py --dry-run --from P2 --until O
    python3 infra/agents/run_lots.py --recette                     # poste de recette sur la dernière branche du state
    python3 infra/agents/run_lots.py --recette --branch main       # poste de recette sur main (après les merges)
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
# BIM_STATE_DIR : dossier de state.json et du journal (tests : ne pas toucher à ceux d'une nuit en cours).
STATE_DIR = Path(os.environ.get("BIM_STATE_DIR", str(HERE)))
STATE_JSON = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "run_lots.log"
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
    done: dict = field(default_factory=dict)   # id -> {status, branch, pr, ci, ci_failures, …}
    last_branch: str = "main"
    last_lot: str = ""
    extra: dict = field(default_factory=dict)  # reviews (réviseur de nuit), queued, … — conservé tel quel

    @classmethod
    def load(cls) -> "State":
        if STATE_JSON.exists():
            d = json.loads(STATE_JSON.read_text(encoding="utf-8"))
            extra = {k: v for k, v in d.items() if k not in ("done", "last_branch", "last_lot")}
            return cls(done=d.get("done", {}), last_branch=d.get("last_branch", "main"), last_lot=d.get("last_lot", ""), extra=extra)
        return cls()

    def save(self) -> None:
        d = {**self.extra, "done": self.done, "last_branch": self.last_branch, "last_lot": self.last_lot}
        STATE_JSON.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(args: list[str], cwd: Path | None = None, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=check)


# ---------------------------------------------------------------- lots

def parse_lots_text(md: str) -> list[Lot]:
    """Balises <!-- LOT … --> + bloc ```text``` → lots. Liste vide si rien (queue.md du réviseur)."""
    lots = []
    for m in LOT_RE.finditer(md or ""):
        deps = [d.strip() for d in m.group("deps").split(",") if d.strip()]
        lots.append(Lot(m.group("id"), m.group("title"), m.group("plan"), m.group("size"), deps, m.group("prompt").strip()))
    return lots


def parse_lots(md: str) -> list[Lot]:
    lots = parse_lots_text(md)
    if not lots:
        sys.exit(f"Aucun lot trouvé dans {PROMPTS_MD} (balises <!-- LOT … --> attendues)")
    return lots


QUEUE_MD = STATE_DIR / "queue.md"   # lots correctifs mis en file par le réviseur de nuit (review_agent.py)


def queued_lots(state: "State", exclude: set[str]) -> list[Lot]:
    """Lots de queue.md pas encore faits ni déjà en attente."""
    if not QUEUE_MD.exists():
        return []
    return [l for l in parse_lots_text(QUEUE_MD.read_text(encoding="utf-8")) if l.id not in state.done and l.id not in exclude]


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

    def github_text(self, path: str) -> str:
        """GET qui renvoie du texte (journaux de job : GitHub redirige vers un fichier)."""
        req = urllib.request.Request(f"{GITHUB_API}{path}", headers=self.github_headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} GET {path}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"réseau: GET {path}: {e}") from e


def github_token_from_git() -> str | None:
    """Jeton GitHub éprouvé sur l'API (gh_token.py : variable, trousseau, fichier — le premier qui répond 200).
    Le 21 sept., ~/.git-credentials portait un vieux jeton et le Terminal du porteur recevait des 401."""
    sys.path.insert(0, str(HERE))
    from gh_token import token as _token  # noqa: PLC0415
    return _token(required=False)


# ---------------------------------------------------------------- github

def owner_repo(repo: str) -> str:
    return repo.replace("https://github.com/", "").rstrip("/")


def find_pr(http: Http, repo: str, branch: str) -> dict | None:
    org = owner_repo(repo).split("/")[0]
    q = urllib.parse.urlencode({"head": f"{org}:{branch}", "state": "open"})
    prs = http.github(f"/repos/{owner_repo(repo)}/pulls?{q}")
    return prs[0] if prs else None


FAIL_LINE = re.compile(r"(✘|✖|FAILED|failed|Error:|AssertionError|Expected|Received|\.spec\.js:\d+|test_[a-z_]+\.py::)")


def job_failures(http: Http, repo: str, check_run: dict) -> list[str]:
    """Lit le journal du job GitHub Actions (l'id du check-run = l'id du job) et
    en extrait les lignes qui nomment un test qui échoue. Court, dédoublonné."""
    try:
        raw = http.github_text(f"/repos/{owner_repo(repo)}/actions/jobs/{check_run['id']}/logs")
    except RuntimeError:
        return []
    out: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"^\S+T\S+Z\s*", "", line).strip()            # horodatage GitHub
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)                  # couleurs
        if FAIL_LINE.search(line) and len(line) < 240 and line not in out:
            out.append(line)
        if len(out) >= 25:
            break
    return out


def ci_status(http: Http, repo: str, sha: str) -> tuple[str, list[str], list[str]]:
    """→ (statut, noms des jobs en échec, lignes d'échec extraites de leurs journaux)."""
    d = http.github(f"/repos/{owner_repo(repo)}/commits/{sha}/check-runs")
    runs = d.get("check_runs", [])
    if not runs:
        return "none", [], []
    failed = [r for r in runs if r.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")]
    pending = [r["name"] for r in runs if r.get("status") != "completed"]
    if failed:
        details: list[str] = []
        for r in failed:
            details += [f"[{r['name']}] {ln}" for ln in job_failures(http, repo, r)]
        return "failure", [r["name"] for r in failed], details
    if pending:
        return "pending", pending, []
    return "success", [], []


def wait_ci(http: Http, repo: str, branch: str, max_min: int) -> tuple[str, list[str], list[str], dict | None]:
    t0 = time.time()
    pr = None
    while time.time() - t0 < max_min * 60:
        pr = find_pr(http, repo, branch)
        if pr:
            status, names, details = ci_status(http, repo, pr["head"]["sha"])
            if status in ("success", "failure"):
                return status, names, details, pr
        time.sleep(60)
    return "pending", [], [], pr


def new_failures(details: list[str], inherited: list[str]) -> list[str]:
    """Les lignes d'échec absentes de la base (lot précédent de la pile) : ce sont
    celles que ce lot a introduites et que sa relance doit corriger."""
    base = {re.sub(r"^\[[^\]]*\]\s*", "", d) for d in inherited}
    return [d for d in details if re.sub(r"^\[[^\]]*\]\s*", "", d) not in base]


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
            "fix": lambda names, details=None: cloud_wait(http, agent_id, cloud_follow_up(http, agent_id, fix_text(names, details)), int(args.timeout_hours * 1800), args.poll)}


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


def port_busy(port: int) -> bool:
    p = sh(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], check=False, timeout=20)
    return bool(p.stdout.strip())


def local_prefix(path: Path, ref: str, pw_port: int) -> str:
    ports = ""
    if port_busy(5174):
        ports = (f"Le port 5174 est déjà pris par le serveur de dev du dépôt principal : pour Playwright, lance `PW_PORT={pw_port} npm run e2e` "
                 f"(la config lit PW_PORT ; si ta copie de playwright.config.js ne le lit pas encore, arrête-toi à `npx vite build` + tests unitaires "
                 f"et écris dans la PR que le spec est fourni mais n'a pas été joué). ")
    return (f"Environnement : tu travailles dans le worktree git {path} (dépôt principal : {ROOT}). "
            f"node_modules et .venv sont des liens vers le dépôt principal : ne lance ni npm install ni pip install sauf nécessité absolue. "
            f"Le worktree est sur un HEAD détaché à `{ref}` : commence par `git checkout -b <ta-branche>`. "
            f"{ports}"
            f"RÈGLE CI : la CI n'a PAS d'API. Ton spec Playwright (e2e/lots/<lot>.spec.js) doit passer sans API : sonde `await page.request.get('/voyage/official')` "
            f"et, si elle ne répond pas, saute proprement (annotation + return) les assertions qui en dépendent, sans jamais affaiblir celles qui n'en dépendent pas. "
            f"Avant de pousser, rejoue-le deux fois : comme en CI `API_PROXY_TARGET=http://127.0.0.1:9 PW_PORT={pw_port} npm run e2e -- e2e/lots/<lot>.spec.js` (doit passer), "
            f"puis avec l'API `PW_PORT={pw_port} npm run e2e -- e2e/lots/<lot>.spec.js`. Ne modifie jamais le spec d'un autre lot. "
            f"RÈGLE RECETTE : dans ta PR, la rubrique « Recette (à faire par le porteur) » ne contient que des étapes visuelles — « ouvre …, clique …, tu dois voir … » "
            f"(texte exact, chiffre, bouton présent ou absent) — et JAMAIS de commande, de data-testid, d'URL d'API, de coordonnées ni de nom de fichier : tout cela va dans « Review automatique ». "
            f"Chaque capture est référencée par son URL complète sur ta branche : https://github.com/{owner_repo(DEFAULT_REPO)}/blob/<ta-branche>/docs/recette/<lot>/01-….jpg?raw=true "
            f"(un chemin relatif s'ouvre sur main, où le fichier n'existe pas encore). "
            f"RÈGLE UI : n'ajoute aucun texte d'aide ou d'explication dans l'interface, aucun libellé déjà visible ailleurs sur le même écran, "
            f"aucune rangée supplémentaire dans la barre film ; un bouton nouveau doit marcher ou ne pas exister. "
            f"RÈGLE PR BILINGUE (21 sept.) : le corps de la PR est en français PUIS en anglais — titre de PR « FR — EN », chaque rubrique en deux blocs "
            f"(« ## Objectif / Objective » : paragraphe FR puis paragraphe EN, idem Cause racine / Root cause, Ce qui change / What changes, Tests, "
            f"Review automatique / Automated review, Hors périmètre / Out of scope). La rubrique « Recette / What to check » est UNE liste de cases à cocher "
            f"`- [ ] <étape FR> / <step EN>` (une seule case par item, les deux langues sur la même ligne) : le porteur coche ce qu'il voit et qui est bon, "
            f"et écrit « KO : … » en commentaire sinon ; les lignes Écran/Captures ne sont pas des cases. "
            f"Quand tout est vert : `git push -u origin <ta-branche>` puis ouvre la PR avec "
            f"`python3 {HERE / 'open_pr.py'} <ta-branche> main \"<titre>\" /tmp/pr-<lot>.md` (chemin absolu ; écris d'abord le corps de la PR dans ce fichier). "
            f"Ne pose aucune question : décide et note dans la PR.")


PW_PORT = int(os.environ.get("BIM_PW_PORT", "5199"))


RATE_LIMIT_RE = re.compile(r"rate.?limit|too many requests|\b429\b|quota|capacity|overloaded|try again later", re.I)
RATE_LIMIT_WAITS_S = (300, 600, 1200)   # 5, 10, 20 min : le fournisseur (Grok) bride après une série d'agents


def run_agent_cli(path: Path, prompt: str, model: str, timeout_s: int, resume: bool = False) -> tuple[str, str]:
    """Un agent CLI. Si le fournisseur répond « rate limited », on attend (5, 10, 20 min) et on
    réessaie au lieu de compter le lot comme raté : la nuit est longue, le batch n'est pas pressé."""
    for attempt, wait_s in enumerate((0,) + RATE_LIMIT_WAITS_S):
        if wait_s:
            log(f"    fournisseur de modèle saturé (rate limited) — nouvel essai dans {wait_s // 60} min ({attempt}/{len(RATE_LIMIT_WAITS_S)})")
            time.sleep(wait_s)
        status, result = _run_agent_cli_once(path, prompt, model, timeout_s, resume)
        if status == "ERROR" and RATE_LIMIT_RE.search(result or ""):
            resume = True   # la reprise recolle à la session commencée, s'il y en a une
            continue
        return status, result
    return status, result


def _run_agent_cli_once(path: Path, prompt: str, model: str, timeout_s: int, resume: bool = False) -> tuple[str, str]:
    cmd = [AGENT_BIN, "-p", "--force", "--trust", "--workspace", str(path), "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    if resume:
        cmd += ["--continue"]
    cmd.append(prompt)
    env = {**os.environ, "PW_PORT": str(PW_PORT)}
    try:
        p = subprocess.run(cmd, cwd=str(path), text=True, capture_output=True, timeout=timeout_s, env=env)
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


def adoptable_worktree(lot: Lot) -> tuple[Path, str] | None:
    """Un worktree laissé par une session interrompue, avec une branche poussée et
    pas encore mergée : on l'adopte au lieu de refaire le lot (et d'ouvrir une 2e PR)."""
    path = WORKTREES / lot.id.lower()
    if not path.exists():
        return None
    branch = local_branch(path)
    if not branch or merged_into_main(branch):
        return None
    remote = sh(["git", "ls-remote", "--heads", "origin", branch], cwd=path, check=False, timeout=60).stdout.strip()
    if not remote:
        return None
    dirty = sh(["git", "status", "--porcelain"], cwd=path, check=False).stdout.strip()
    return None if dirty else (path, branch)


def run_lot_local(http: Http, lot: Lot, prompt: str, ref: str, args) -> dict:
    adopted = adoptable_worktree(lot)
    if adopted:
        path, branch = adopted
        log(f"[{lot.id}] worktree {path} déjà poussé sur {branch} — adopté (pas de nouvel agent)")
        ensure_pr(http, args, lot, branch, "(lot adopté après interruption : voir la PR)")
        return {"status": "FINISHED", "branch": branch, "worktree": str(path), "result": "adopté",
                "fix": lambda names, details=None: run_agent_cli(path, fix_text(names, details), args.model, int(args.timeout_hours * 1800), resume=True)}
    path = prepare_worktree(lot, ref)
    log(f"[{lot.id}] worktree {path} depuis {ref} — agent local ({args.model or 'modèle par défaut du compte'})")
    status, result = run_agent_cli(path, local_prefix(path, ref, PW_PORT) + "\n\n" + prompt, args.model, int(args.timeout_hours * 3600))
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
            "fix": lambda names, details=None: run_agent_cli(path, fix_text(names, details), args.model, int(args.timeout_hours * 1800), resume=True)}


# ---------------------------------------------------------------- boucle commune

RESUME_TEXT = ("Reprends là où tu t'es arrêté : finis le lot, lance les tests, pousse la branche et ouvre la PR (ne merge pas). "
               "Si un point bloque, choisis la solution la plus simple et note-la dans la PR.")


def fix_text(names: list[str], details: list[str] | None = None) -> str:
    lines = "\n".join(f"  - {d}" for d in (details or [])[:20]) or "  (voir les journaux GitHub Actions)"
    return ("La CI de ta PR échoue sur : " + ", ".join(names) + ".\nLignes d'échec relevées dans les journaux :\n" + lines +
            "\nCorrige TA PR : la CI n'a pas d'API (un spec de lot doit passer sans API : sonde /voyage/official et saute les assertions qui en dépendent) ; "
            "rejoue en local avec `API_PROXY_TARGET=http://127.0.0.1:9 PW_PORT=" + str(PW_PORT) + " npm run e2e -- e2e/lots/<ton-lot>.spec.js` puis npm test / pytest / vite build ; pousse. "
            "Ne modifie pas le spec d'un autre lot ; ne merge pas ; ne retire aucune surface visible.")


def base_line(ref: str) -> str:
    if ref == "main":
        return "Base de travail : `main` à jour. Crée ta branche depuis main."
    return (f"Base de travail : la branche `{ref}` (lot précédent, pas encore mergé). Crée ta branche depuis `{ref}`, n'y touche pas, "
            f"et ouvre ta PR vers `main` (le diff inclura le lot précédent : c'est attendu, il fondra quand il sera mergé).")


def merged_into_main(branch: str) -> bool:
    """Vrai si la branche (locale ou distante) est déjà contenue dans origin/main : on repart alors de main."""
    if branch == "main":
        return True
    for ref in (branch, f"origin/{branch}"):
        if sh(["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT, check=False).returncode == 0:
            return sh(["git", "merge-base", "--is-ancestor", ref, "origin/main"], cwd=ROOT, check=False).returncode == 0
    return True  # branche disparue (supprimée après merge) : main


def run_lot(http: Http | None, lot: Lot, state: State, args) -> None:
    ref = "main" if args.stack == "none" else state.last_branch
    if ref != "main" and not args.dry_run:
        sh(["git", "fetch", "-q", "origin"], cwd=ROOT, check=False, timeout=120)
        if merged_into_main(ref):
            log(f"[{lot.id}] la branche {ref} est déjà dans main — on repart de main")
            ref = "main"
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
    inherited = (state.done.get(state.last_lot) or {}).get("ci_failures", []) if args.stack == "linear" else []
    status, names, details, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
    if pr:
        entry["pr"] = pr["html_url"]
        log(f"[{lot.id}] PR {pr['number']} {pr['html_url']} — CI {status} {names or ''}")
    else:
        log(f"[{lot.id}] aucune PR trouvée pour {branch} — à ouvrir à la main")
    rounds = 0
    while status == "failure" and rounds < args.fix_rounds:
        fresh = new_failures(details, inherited)
        if details and not fresh:
            log(f"[{lot.id}] CI rouge mais tous les échecs sont hérités du lot précédent ({len(details)} lignes) — pas de relance")
            status = "failure-inherited"
            break
        rounds += 1
        log(f"[{lot.id}] CI rouge — relance de correction {rounds}/{args.fix_rounds} ({len(fresh or details)} lignes d'échec transmises)")
        out["fix"](names, fresh or details)
        if args.runtime == "local":
            ensure_pushed(Path(out["worktree"]), branch)
        status, names, details, pr = wait_ci(http, args.repo, branch, args.ci_wait_min)
        log(f"[{lot.id}] CI après correction {rounds} : {status} {names or ''}")
    entry["ci"] = status
    entry["ci_failures"] = details if status.startswith("failure") else []
    state.done[lot.id] = entry
    state.last_branch = branch
    state.last_lot = lot.id
    state.save()
    # Lot W1 : le poste de recette suit la tête de pile — le porteur (et le bot, par le tunnel) recettent à la volée.
    if pr and not getattr(args, "no_recette", False) and not getattr(args, "no_recette_each", False):
        try:
            prepare_recette(state, args, http, quiet=True)
            if getattr(args, "publish_tip", False) and status == "success" and publish_tip(branch):
                post_poste_link(state, lot.id, PROD_URL, args.repo, published=True)
            else:
                url = None if getattr(args, "no_tunnel", False) else start_tunnel()
                if url:
                    post_poste_link(state, lot.id, url, args.repo)
        except Exception as e:  # jamais bloquant pour le batch
            log(f"    poste de recette non rafraîchi : {e}")


# ---------------------------------------------------------------- fin de batch : poste de recette (lot W0)

RECETTE_MD = STATE_DIR / "RECETTE_DU_BATCH.md"
ENV_FILE = Path(os.environ.get("NAVIGUIDE_ENV_FILE", str(Path.home() / ".config" / "naviguide" / "simulator.env")))
PROD_URL = "https://simulator.naviguide.fr"

# Écrans de l'application, dans l'ordre où le porteur les regarde. Une étape de
# recette est rangée sous le premier écran dont un mot-clé apparaît dans son texte.
SCREENS: list[tuple[str, str, tuple[str, ...]]] = [
    ("revoir", "Revoir l'expédition (le film)", ("revoir", "replay", "film", "chapitre", "bulle", "sous-titre", "cinéma", "cinema")),
    ("tracer", "Tracer ma route", ("tracer", "route dessinée", "dessine", "brisbane", "terminé", "deux clics")),
    ("simulation", "Simulation", ("simulation", "la rochelle", "ajaccio", "recalcul", "ordre du skipper", "ordres skipper", "escale suivante", "prochaine escale")),
    ("suivre", "Suivre l'expédition", ("suivre", "nouméa", "noumea", "live", "position du bateau", "mode-follow")),
    ("reglages", "Panneau droit, revue du plan, réglages", ("panneau droit", "revue du plan", "paramètres", "polaire", "calques", "langue", "anglais", "english", "thème", "clair")),
]
# Ce qui n'est pas « regarder l'écran » : ces lignes vont dans la partie « vérifié par les tests ».
TECH_RE = re.compile(r"data-testid|\bGET\b|\bPUT\b|\bPOST\b|\bcurl\b|\bnpm\b|\bnpx\b|pytest|\.spec\.js|window\.__|localStorage|\bfixture\b|\bspec\b|\d{1,3}\s?[°º]\s?\d", re.I)
HEADING_RE = re.compile(r"^\s{0,3}#{2,4}\s+(.+?)\s*$")


def pr_sections(body: str) -> dict[str, str]:
    """Corps de PR → {titre de rubrique en minuscules: texte}. Les rubriques sont les titres ## / ###."""
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


def section_lines(sections: dict[str, str], *starts: str) -> list[str]:
    """Lignes non vides des rubriques dont le titre commence par un des mots donnés."""
    lines: list[str] = []
    for title, text in sections.items():
        if any(title.startswith(s) for s in starts):
            lines += [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("```")]
    return lines


def screen_of(text: str) -> str:
    low = text.lower()
    for sid, _, words in SCREENS:
        if any(w in low for w in words):
            return sid
    return "partout"


def pr_number(url: str | None) -> int | None:
    m = re.search(r"/pull/(\d+)", url or "")
    return int(m.group(1)) if m else None


def fetch_pr(http: Http | None, repo: str, number: int) -> dict | None:
    try:
        return (http or Http(None, None)).github(f"/repos/{owner_repo(repo)}/pulls/{number}")
    except RuntimeError as e:
        log(f"    PR #{number} illisible : {e}")
        return None


def branch_included(branch: str, last: str) -> bool:
    """Vrai si la branche est déjà contenue dans la dernière branche de la pile (merger la dernière suffit)."""
    if branch == last:
        return True
    for ref in (f"origin/{branch}", branch):
        if sh(["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT, check=False).returncode == 0:
            for lref in (f"origin/{last}", last):
                if sh(["git", "rev-parse", "--verify", "-q", lref], cwd=ROOT, check=False).returncode == 0:
                    return sh(["git", "merge-base", "--is-ancestor", ref, lref], cwd=ROOT, check=False).returncode == 0
    return False


def env_key_names() -> list[str]:
    if not ENV_FILE.exists():
        return []
    names = []
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line.strip())
        if m and re.search(r"API_KEY|PASSWORD|SECRET", m.group(1)):
            names.append(m.group(1))
    return names


def api_status() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8010/ici/warm/status", timeout=10) as resp:
            return json.loads(resp.read().decode() or "{}")
    except Exception:
        return {}


def recette_worktree(state: State, branch: str) -> Path:
    """Le checkout qui sert à la recette : le dépôt principal s'il est sur main et qu'on
    recette main ; sinon le worktree du lot qui a produit la branche ; sinon ~/bim-lots/recette."""
    if branch == "main" and local_branch(ROOT) == "main":
        sh(["git", "pull", "--ff-only", "-q"], cwd=ROOT, check=False, timeout=120)
        return ROOT
    for e in state.done.values():
        wt = Path(e.get("worktree") or "")
        if e.get("branch") == branch and wt.exists() and local_branch(wt) == branch:
            sh(["git", "pull", "--ff-only", "-q"], cwd=wt, check=False, timeout=120)
            return wt
    return prepare_worktree(Lot("recette", "poste de recette", "", "", [], ""), branch)


# ---- tunnel : le poste de recette vu depuis le cloud (Grok Bot), lot W1 bis

TUNNEL_PID = STATE_DIR / "tunnel.pid"
TUNNEL_URL = STATE_DIR / "tunnel.url"
TUNNEL_LOG = STATE_DIR / "tunnel.log"


def tunnel_url() -> str | None:
    """URL publique du poste de recette si un tunnel tourne (cloudflared, quick tunnel)."""
    if not (TUNNEL_PID.exists() and TUNNEL_URL.exists()):
        return None
    try:
        os.kill(int(TUNNEL_PID.read_text().strip()), 0)
    except (OSError, ValueError):
        return None
    return TUNNEL_URL.read_text(encoding="utf-8").strip() or None


def _env_file_values() -> dict[str, str]:
    """~/.config/naviguide/simulator.env : un seul fichier pour les clés ET les réglages BIM_* de la boucle."""
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def tunnel_settings() -> tuple[str | None, str | None]:
    """(nom du tunnel nommé, hôte) — environnement ou fichier de clés ; (None, None) = tunnel rapide."""
    vals = _env_file_values()
    name = os.environ.get("BIM_TUNNEL_NAME") or vals.get("BIM_TUNNEL_NAME")
    host = os.environ.get("BIM_TUNNEL_HOST") or vals.get("BIM_TUNNEL_HOST")
    return (name or None), (host or None)


def start_tunnel(port: int = 5174, wait_s: int = 40) -> str | None:
    """Démarre un tunnel Cloudflare détaché vers :5174 et renvoie son URL.

    Deux formes :
    - **tunnel nommé** sur le domaine du porteur (BIM_TUNNEL_NAME=recette, BIM_TUNNEL_HOST=recette.blueintelligence.online,
      posés une fois : `cloudflared tunnel login` → `tunnel create recette` → `tunnel route dns recette recette.blueintelligence.online`) :
      URL stable, mêmes règles Cloudflare que le site — c'est ce que le navigateur de Grok Bot sait ouvrir ;
    - sinon **tunnel rapide** `https://….trycloudflare.com` : pratique pour un humain, mais Cloudflare y bloque les
      navigateurs automatisés (403 « Your request was blocked », 21 sept.).
    Le tunnel survit à run_lots (le bot travaille aussi après la fin du batch) : `--stop-tunnel` l'arrête."""
    existing = tunnel_url()
    if existing:
        return existing
    exe = shutil.which("cloudflared")
    if not exe:
        log("cloudflared absent : pas de lien pour le bot (brew install cloudflared)")
        return None
    name, host = tunnel_settings()
    TUNNEL_LOG.write_text("", encoding="utf-8")
    if name and host:
        cmd = [exe, "tunnel", "--no-autoupdate", "run", "--url", f"http://127.0.0.1:{port}", name]
    else:
        cmd = [exe, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
    with TUNNEL_LOG.open("a", encoding="utf-8") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    TUNNEL_PID.write_text(str(p.pid), encoding="utf-8")
    for _ in range(wait_s * 2):
        text = TUNNEL_LOG.read_text(encoding="utf-8", errors="replace")
        if name and host:
            if re.search(r"Registered tunnel connection|[Cc]onnection [0-9a-f-]+ registered", text):
                url = f"https://{host}"
                TUNNEL_URL.write_text(url, encoding="utf-8")
                log(f"tunnel nommé « {name} » du poste de recette : {url} (à arrêter avec --stop-tunnel)")
                return url
        else:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
            if m:
                TUNNEL_URL.write_text(m.group(0), encoding="utf-8")
                log(f"tunnel rapide du poste de recette : {m.group(0)} (public, obscur ; navigateurs automatisés bloqués par Cloudflare — préférer un tunnel nommé ; --stop-tunnel pour arrêter)")
                return m.group(0)
        time.sleep(0.5)
    hint = f" (tunnel nommé « {name} » : `cloudflared tunnel login`, `tunnel create {name}`, `tunnel route dns {name} {host}` faits ?)" if name else ""
    log(f"tunnel : pas de connexion après {wait_s} s — voir {TUNNEL_LOG}{hint}")
    stop_tunnel()
    return None


def stop_tunnel() -> None:
    if TUNNEL_PID.exists():
        try:
            os.kill(int(TUNNEL_PID.read_text().strip()), 15)
            log("tunnel arrêté")
        except (OSError, ValueError):
            pass
        TUNNEL_PID.unlink(missing_ok=True)
    TUNNEL_URL.unlink(missing_ok=True)


BOT_COMMENT_MARK = "🔗 Poste de recette"
BOT_PREREVIEW_RE = re.compile(r"^\s*#{1,3}\s*🤖\s*Pr[ée]-?revue", re.I | re.M)   # titre « ## 🤖 Pré-revue » en début de ligne (pas le 🔗 qui cite la consigne)
PARCOURS_MD = HERE / "PARCOURS_DE_REFERENCE.md"   # tout tester, une fois par batch, sur la tête de pile (Grok Bot)
PARCOURS_MARK = "🧭 Parcours de référence"
RECETTE_BRANCH = "recette"   # option --publish-tip : le site publié suit la tête de pile (simulateur seul)


def publish_tip(branch: str) -> bool:
    """Option --publish-tip : pousse la tête de pile (CI verte) sur `recette`, que deploy.yml déploie
    sur le site (simulateur seulement). Le site publié devient alors ce que le bot et le porteur
    recettent. Par défaut OFF : la pile de la nuit écrirait dans la base de prod."""
    if sh(["git", "fetch", "-q", "origin", branch], cwd=ROOT, check=False, timeout=120).returncode != 0:
        log(f"    publish-tip : fetch de {branch} impossible")
        return False
    sha = sh(["git", "rev-parse", f"origin/{branch}"], cwd=ROOT, check=False).stdout.strip()
    p = sh(["git", "push", "-f", "origin", f"{sha}:refs/heads/{RECETTE_BRANCH}"], cwd=ROOT, check=False, timeout=120)
    if p.returncode != 0:
        log(f"    publish-tip : push impossible : {p.stderr.strip()[-200:]}")
        return False
    log(f"    tête de pile {branch} ({sha[:7]}) poussée sur `{RECETTE_BRANCH}` → déploiement du site dans ~8 min")
    return True


def post_poste_link(state: State, lot_id: str, url: str, repo: str, *, published: bool = False) -> None:
    """Un commentaire par PR avec le lien vers la tête de pile et la consigne du bot (une seule fois)."""
    e = state.done.get(lot_id) or {}
    num = pr_number(e.get("pr"))
    if not num or e.get("tunnel_comment") == url:   # déjà posté pour CETTE url ; un nouveau tunnel = nouveau lien
        return
    try:
        from post_pr_comment import post as _post  # noqa: PLC0415
        where = (f"site publié, déployé depuis la tête de pile `{state.last_branch}` — attendre ~8 min après ce commentaire"
                 if published else f"tête de pile `{state.last_branch}`, build de prod, clés chargées")
        body = (f"{BOT_COMMENT_MARK} ({where}) : {url}\n\n"
                "🤖 **Grok Bot** — pré-revue visuelle : ouvre ce lien, vérifie chaque case de la rubrique « Recette » ci-dessus. "
                "**Coche dans la PR** les cases que tu as vues et qui sont bonnes ; laisse vides les autres. Puis poste UN commentaire qui commence par "
                "`## 🤖 Pré-revue` et liste exactement ce que tu as fait, une ligne par item : `- [x] 🤖 <item>` (coché par toi), "
                "`- [ ] 🤖 <item> — KO : <écran, ce que je vois, ce que je voulais>` (défaut vu), `- [ ] 🤖 <item> — non vérifiable : <pourquoi>`. "
                "Le porteur relit le matin : il décoche ce qu'il conteste. Ne ferme ni ne merge rien, ne modifie pas le texte de la PR.")
        _post(num, body)
        e["tunnel_comment"] = url
        state.done[lot_id] = e
        state.save()
        log(f"    lien du poste posté sur la PR #{num}")
    except Exception as ex:  # jamais bloquant
        log(f"    lien du poste non posté sur #{num} : {ex}")


def post_parcours_request(state: State, url: str, repo: str) -> None:
    """Fin de batch : sur la PR de tête, demander à Grok Bot de jouer TOUT le parcours de référence
    (régressions hors des cases des PR, console). Une seule fois par tête de pile."""
    e = state.done.get(state.last_lot) or {}
    num = pr_number(e.get("pr"))
    if not num or e.get("parcours_comment") == url:
        return
    try:
        from post_pr_comment import post as _post  # noqa: PLC0415
        checklist = PARCOURS_MD.read_text(encoding="utf-8") if PARCOURS_MD.exists() else ""
        body = (f"{PARCOURS_MARK} (tête de pile `{state.last_branch}`, tous les lots de la nuit) : {url}\n\n"
                "🤖 **Grok Bot** — quand les pré-revues des PR de la pile sont faites, joue **tout** le parcours ci-dessous sur ce lien "
                "(console ouverte à chaque écran) et poste UN commentaire qui commence par `## 🤖 Parcours de référence`, une ligne par item "
                "(`- [x] 🤖 <item>` / `- [ ] 🤖 <item> — KO : …` / `- [ ] 🤖 Console (<écran>) — KO : <message, fichier:ligne>`), "
                "terminé par « Vu n / total · KO k ». Ne coche rien dans cette PR, ne ferme ni ne merge rien.\n\n"
                "<details><summary>Le parcours (infra/agents/PARCOURS_DE_REFERENCE.md)</summary>\n\n" + checklist + "\n</details>")
        _post(num, body)
        e["parcours_comment"] = url
        state.done[state.last_lot] = e
        state.save()
        log(f"    demande de parcours de référence postée sur la PR de tête #{num}")
    except Exception as ex:
        log(f"    demande de parcours non postée : {ex}")


def prepare_recette(state: State, args, http: Http | None, *, quiet: bool = False) -> None:
    """Poste de recette sur la dernière branche. `quiet` (après chaque lot, lot W1) : on rebâtit
    l'app et le md sans ouvrir de fenêtre — le porteur recharge son onglet, la PR porte ses cases."""
    branch = getattr(args, "branch", None) or state.last_branch or "main"
    log(("poste de recette rafraîchi" if quiet else "fin de batch : poste de recette") + f" sur `{branch}`")
    if not ENV_FILE.exists():
        log(f"!! {ENV_FILE} absent : l'API tournera sans clé (récit « règles », chat et juge éteints)")
    wt = recette_worktree(state, branch)
    sim = wt / "naviguide-simulator"
    try:
        # Toujours le script du checkout principal (à jour), pointé sur le worktree du lot : une branche
        # née avant une correction du script (hôtes autorisés du preview…) en profite quand même.
        script = ROOT / "naviguide-simulator" / "ensure-dev.sh"
        cmd = ["bash", str(script), "--prod", f"--dir={sim}"] + ([] if quiet else ["--open"])
        env = dict(os.environ)
        _name, host = tunnel_settings()
        if host:   # le preview doit accepter l'hôte du tunnel nommé (sinon Vite : « Blocked request »)
            env["NAVIGUIDE_PREVIEW_HOST"] = host
        p = subprocess.run(cmd, cwd=str(sim), text=True, capture_output=True, timeout=1200, env=env)
        for ln in (p.stdout + p.stderr).strip().splitlines()[-(4 if quiet else 12):]:
            log(f"    {ln}")
        launched = p.returncode == 0
    except subprocess.TimeoutExpired:
        log("    ensure-dev.sh --prod : délai dépassé (20 min)")
        launched = False
    write_recette_md(state, args, http, branch, wt, launched)
    log(f"recette : {RECETTE_MD}")
    if quiet:
        return
    if sh(["open", "-a", "Cursor", str(RECETTE_MD)], check=False, timeout=30).returncode != 0:
        sh(["open", str(RECETTE_MD)], check=False, timeout=30)


def write_recette_md(state: State, args, http: Http | None, branch: str, wt: Path, launched: bool) -> None:
    repo = getattr(args, "repo", DEFAULT_REPO)
    keys = env_key_names()
    st = api_status()
    llm = st.get("llm") or {}
    lots = [(lid, e) for lid, e in state.done.items() if e.get("status") == "FINISHED" and e.get("branch")]
    last = state.last_branch or branch

    by_screen: dict[str, list[str]] = {sid: [] for sid, _, _ in SCREENS}
    by_screen["partout"] = []
    tech: list[str] = []
    captures: list[str] = []
    decisions: list[str] = []
    kos: list[str] = []
    ticked = total_items = 0
    blob = f"https://github.com/{owner_repo(repo)}/blob"
    try:
        from review_collect import ko_comments as _ko_comments, bot_verdicts as _bot_verdicts, item_key as _item_key  # noqa: PLC0415
    except Exception:  # pragma: no cover — collecte absente : le md se fait sans les KO ni le bot
        _ko_comments = _bot_verdicts = _item_key = None
    for lid, e in lots:
        num = pr_number(e.get("pr"))
        pr = fetch_pr(http, repo, num) if num else None
        tag = f"(#{num} {lid})" if num else f"({lid})"
        if not pr:
            by_screen["partout"].append(f"- {tag} PR illisible : ouvrir {e.get('pr') or e.get('branch')} et lire sa rubrique « Recette ».")
            continue
        comments: list = []
        if (_ko_comments or _bot_verdicts) and num:
            try:
                comments = (http or Http(None, None)).github(f"/repos/{owner_repo(repo)}/issues/{num}/comments?per_page=100") or []
            except RuntimeError:
                comments = []
        bot = _bot_verdicts(comments) if _bot_verdicts else {}
        sections = pr_sections(pr.get("body") or "")
        steps = section_lines(sections, "recette", "recipe", "acceptance", "what to check")
        if not steps:
            by_screen["partout"].append(f"- {tag} la PR n'a pas de rubrique « Recette » : regarder « Objectif » — {(sections.get('objectif') or '').strip()[:200]}")
        default_screen = screen_of(" ".join(steps) + " " + (pr.get("title") or ""))
        for ln in steps:
            box = re.match(r"^\s*[-*]\s*\[( |x|X)\]\s*(.*)$", ln)             # case cochée par le porteur (lot W1)
            mark = ""
            if box:
                ln = box.group(2)
                checked = box.group(1).lower() == "x"
                b = bot.get(_item_key(ln)) if (bot and _item_key) else None   # pré-revue du bot : qui a coché ?
                if checked:
                    mark = "✅🤖 " if (b and b.get("ok")) else "✅ "            # coché par le bot (non contredit) / par le porteur
                else:
                    mark = "🤖❌ " if (b and b.get("ko")) else "⬜ "            # KO vu par le bot / à voir
            ln = re.sub(r"^(\d+[.)]|[-*•])\s+", "", ln).strip()          # puce ou numéro, pas le gras
            ln = re.sub(r"\]\((docs/recette/[^)]+)\)", rf"]({blob}/{e['branch']}/\1?raw=true)", ln)
            ln = re.sub(r"`(docs/recette/[^`]+\.(?:jpg|jpeg|png))`", rf"[\1]({blob}/{e['branch']}/\1?raw=true)", ln)
            item = f"- {mark}{tag} {ln}"
            if re.match(r"(?i)^\**capture", ln) or "docs/recette/" in ln:
                captures.append(item)
            elif TECH_RE.search(ln):
                tech.append(item)
            else:
                if mark:
                    total_items += 1
                    ticked += mark.startswith("✅")
                sid = screen_of(ln)
                by_screen[sid if sid != "partout" else default_screen].append(item)
        for ln in section_lines(sections, "décisions", "decisions", "libertés", "hors périmètre"):
            ln = re.sub(r"^([-*•])\s+", "", ln).strip()
            decisions.append(f"- {tag} {ln}")
        if _ko_comments and num:
            try:
                for ko in _ko_comments(comments):
                    if not BOT_PREREVIEW_RE.search(ko["text"]) and "Parcours de référence" not in ko["text"]:
                        kos.append(f"- ❌ {tag} {ko['text'][:300]}" + (f" — [commentaire]({ko['url']})" if ko.get("url") else ""))
            except RuntimeError:
                pass
        if bot and _item_key:   # KO du bot hors cases : console, régressions du parcours de référence
            keys_of_items = {_item_key(re.sub(r"^\s*[-*]\s*\[( |x|X)\]\s*", "", ln)) for ln in steps}
            for k, v in bot.items():
                if k not in keys_of_items and v.get("ko"):
                    kos.append(f"- 🤖❌ {tag} {v.get('text', '')[:160]}" + (f" — {v['note'][:160]}" if v.get("note") else ""))

    merges: list[str] = []
    extra: list[str] = []
    for lid, e in lots:
        num = pr_number(e.get("pr"))
        link = f"[#{num}]({e['pr']})" if num else f"`{e['branch']}`"
        ci = e.get("ci") or "?"
        merges.append(f"{len(merges) + 1}. {link} — {lid} — CI {ci}")
        if num and e["branch"] != last and not branch_included(e["branch"], last):
            extra.append(link)
    last_pr = next((f"[#{pr_number(e['pr'])}]({e['pr']})" for lid, e in reversed(lots) if e.get("branch") == last and pr_number(e.get("pr"))), None)

    tip_link = f"[#{pr_number(state.done[state.last_lot]['pr'])}]({state.done[state.last_lot]['pr']})" if state.last_lot in state.done and state.done[state.last_lot].get("pr") else "la dernière PR de la pile"
    lines = [
        f"# Recette du batch — {time.strftime('%d/%m/%Y %H:%M')}",
        "",
        "## 0. À faire maintenant, pas à pas",
        "",
        "1. **Regarder** l'application ouverte dans Chrome (<http://localhost:5174>) en suivant le § 1 ci-dessous, écran par écran.",
        "2. **Cocher** dans chaque PR GitHub (liens au § 1) les cases que tu as vues et qui sont bonnes ; pour ce qui ne va pas, laisser la case vide et écrire un commentaire qui commence par `KO :` (écran, ce que je vois, ce que je voulais). Ce que Grok Bot a déjà coché (✅🤖) reste coché si tu es d'accord.",
        f"3. **Merger la PR de tête** {tip_link} (bouton vert « Merge pull request », option « Create a merge commit ») : GitHub ferme les autres PR de la pile.",
        "4. **Lancer le correcteur** dans le Terminal : `cd ~/Blue-Intelligence-Map && git checkout main && git pull --ff-only && caffeinate -i python3 infra/agents/loop.py --start-at correct --cycles 1`",
        "   → il collecte ta revue et celle du bot, écrit le plan de corrections et ouvre une PR « GO ».",
        "5. **Lire puis merger la PR GO** : le batch suivant part tout seul ; ce fichier sera régénéré à la fin, avec les mêmes cinq étapes.",
        "",
        "Rien d'autre à lancer. Si une étape échoue, voir § 7.",
        "",
        f"Ouvre <http://localhost:5174> ({'déjà ouvert' if launched else 'le poste n’a pas démarré : `cd ' + str(wt / 'naviguide-simulator') + ' && bash ensure-dev.sh --prod --open`'}).",
        f"Branche : `{branch}` — build de prod — API du même checkout (`{wt}`).",
        (f"Clés chargées : {', '.join(keys)}. Source LLM vue par l'API : `{llm.get('lastSource') or '—'}` ; Tavily : {((llm.get('tavily') or {}).get('calls') or 0)} appel(s)."
         if keys else f"Aucune clé ({ENV_FILE} absent) : récit en « règles », chat et juge éteints."),
        "Le hindcast se remplit en fond pendant ~40 min après la première ouverture : les couleurs de la route déjà parcourue peuvent changer.",
        "",
        "**Comment recetter** : chaque PR porte sa recette en **cases à cocher**. Dans GitHub, coche ce que tu vois et qui est bon ; "
        "pour ce qui ne va pas, laisse la case vide et écris un commentaire qui commence par **« KO : »** (écran, ce que je vois, ce que je voulais), "
        "avec une capture si tu veux. Le correcteur lit ces cases et ces commentaires. Ce fichier est régénéré après chaque lot : "
        "l'app sur :5174 est toujours la tête de pile (recharge l'onglet). Grok Bot fait une pré-revue la nuit : il coche ce qu'il a vérifié et le liste "
        "dans son commentaire « 🤖 Pré-revue » — ✅🤖 = coché par le bot (décoche + « KO : » si tu contestes), ✅ = coché par toi, 🤖❌ = défaut vu par le bot.",
        (f"Lien public du poste (pour le bot) : <{tunnel_url()}>" if tunnel_url() else "Pas de tunnel en route (le bot ne voit pas le poste)."),
        (f"État de la revue : **{ticked} / {total_items} items cochés**, **{len(kos)} KO**." if total_items or kos else "État de la revue : aucune case cochée pour l'instant."),
        "",
        "## 1. Ce que tu regardes, écran par écran (✅ toi · ✅🤖 bot · ⬜ à voir · 🤖❌ KO du bot)",
        "",
    ]
    for sid, label, _ in SCREENS + [("partout", "Partout / autres", ())]:
        items = by_screen.get(sid) or []
        if items:
            lines += [f"### {label}", ""] + items + [""]
    if not any(by_screen.values()):
        lines += ["_(aucune PR dans state.json : recette libre des trois parcours — Suivre à Nouméa, Simulation La Rochelle → Ajaccio, Tracer Brisbane → SF — et du film.)_", ""]
    lines += ["## 2. Tes KO déjà notés dans les PR", ""] + (kos or ["- (aucun)"]) + [""]
    lines += ["## 3. Captures prises par les agents (à comparer avec ton écran)", ""] + (captures or ["- (aucune)"]) + [""]
    lines += ["## 4. Vérifié par les tests à ta place (pas à regarder)", ""] + (tech or ["- (rien)"]) + [""]
    lines += ["## 5. Décisions prises seules par les agents — à trancher : garder / défaire", ""] + (decisions or ["- (aucune notée)"]) + [""]
    lines += ["## 6. Merger, quand la recette est bonne", ""]
    if last_pr:
        lines += [f"Pile linéaire : merger **{last_pr}** (la dernière) suffit — GitHub ferme les autres comme mergées.",
                  "Bouton vert « Merge pull request », vérifier « Create a merge commit » (pas Squash), Confirm."]
        if extra:
            lines += [f"Puis merger aussi, si elles restent ouvertes (commits qui ne sont pas dans la dernière) : {', '.join(extra)}."]
        lines += ["", "Ordre de la pile, pour mémoire :"] + merges
        lines += ["", f"Ensuite : onglet Actions → déploiement ~10 min → <{PROD_URL}>. Puis `python3 infra/agents/run_lots.py --recette --branch main` pour recetter la prod en local."]
    else:
        lines += ["Aucune PR de batch dans state.json : rien à merger ici."]
    lines += ["", "## 7. Si quelque chose ne va pas", "",
              "- Le poste ne répond pas : `cd naviguide-simulator && bash ensure-dev.sh --prod --open` dans le checkout ci-dessus ; journaux dans `.dev/api.log`, `.dev/vite.log`, `.dev/build.log`.",
              "- Une clé manque : l'ajouter dans `~/.config/naviguide/simulator.env` (une ligne `NOM=valeur`), relancer la commande ci-dessus.",
              "- Une PR est mauvaise : ne pas la merger ; dicter ce qui ne va pas, un lot de correction repart le soir.", ""]
    RECETTE_MD.write_text("\n".join(lines), encoding="utf-8")


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
    ap.add_argument("--skip", nargs="+", default=[], help="lots à sauter (déjà mergés, ex. --skip C1)")
    ap.add_argument("--stack", choices=["linear", "none"], default="linear", help="linear : chaque lot part de la branche du précédent (défaut) ; none : chacun depuis main")
    ap.add_argument("--resume", action="store_true", help="reprend state.json : saute les lots déjà FINISHED")
    ap.add_argument("--dry-run", action="store_true", help="affiche les prompts, ne lance rien")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="identifiant de modèle (cloud : GET /v1/models ; local : `agent models`) ; '' = défaut du compte")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--timeout-hours", type=float, default=3.0)
    ap.add_argument("--poll", type=int, default=60, help="secondes entre deux lectures d'état (cloud)")
    ap.add_argument("--ci-wait-min", type=int, default=25)
    ap.add_argument("--fix-rounds", type=int, default=2, help="relances de correction quand la CI est rouge sur des échecs nouveaux (défaut 2)")
    ap.add_argument("--recette", action="store_true", help="ne lance aucun lot : prépare le poste de recette (build de prod, clés, API, navigateur, RECETTE_DU_BATCH.md) sur la dernière branche du state ou --branch")
    ap.add_argument("--branch", help="avec --recette : branche à recetter (défaut : dernière branche de state.json, sinon main)")
    ap.add_argument("--no-recette", action="store_true", help="ne prépare pas le poste de recette (ni par lot, ni en fin de batch)")
    ap.add_argument("--no-recette-each", action="store_true", help="ne rafraîchit pas le poste après chaque lot (seulement en fin de batch)")
    ap.add_argument("--review-every", type=int, default=int(os.environ.get("BIM_REVIEW_EVERY", "4")),
                    help="réviseur de nuit (code, Grok) toutes les N PR, lots correctifs en file exécutés en bout de pile ; 0 = jamais (défaut 4)")
    ap.add_argument("--review-model", default=os.environ.get("BIM_REVIEW_MODEL", "cursor-grok-4.6-xhigh-fast"),
                    help="modèle du réviseur de nuit (CLI Cursor). Grok : usage inclus. Fable est réservé au correcteur du matin (plan_corrections.py)")
    ap.add_argument("--review-timeout-hours", type=float, default=1.0)
    ap.add_argument("--bot-wait-min", type=int, default=int(os.environ.get("BIM_BOT_WAIT_MIN", "45")),
                    help="avant le réviseur de code, attendre la pré-revue « 🤖 » de Grok Bot sur la tranche (minutes ; 0 = ne pas attendre ; défaut 45)")
    ap.add_argument("--no-tunnel", action="store_true", help="ne pas exposer le poste de recette au bot (cloudflared) ; sinon un lien 🔗 est posté dans chaque PR")
    ap.add_argument("--stop-tunnel", action="store_true", help="arrête le tunnel laissé en route et s'arrête")
    ap.add_argument("--publish-tip", action="store_true", default=os.environ.get("BIM_PUBLISH_TIP") == "1",
                    help="option : pousser chaque tête de pile (CI verte) sur la branche `recette` → le SITE publié suit la nuit (simulateur seul) ; "
                         "le bot recette alors le vrai site. OFF par défaut : la pile écrirait dans la base de prod")
    args = ap.parse_args()

    if args.check:
        check(args)
        return

    if args.stop_tunnel:
        stop_tunnel()
        return

    if args.recette:
        state = State.load()
        prepare_recette(state, args, Http(None, github_token_from_git()))
        if not args.no_tunnel:
            url = start_tunnel()
            if url:   # le bot trouve le poste par le lien 🔗 de chaque PR de la pile
                for lid, e in state.done.items():
                    if e.get("status") == "FINISHED" and e.get("pr"):
                        post_poste_link(state, lid, url, args.repo)
                post_parcours_request(state, url, args.repo)
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

    log(f"lots : {[l.id for l in lots]} — runtime {args.runtime} — pile {args.stack}" + (f" — revue de nuit toutes les {args.review_every} PR ({args.review_model})" if args.review_every else ""))
    pending = list(lots)
    since_review: list[str] = []          # lots FINISHED pas encore relus par le réviseur de nuit

    def wait_bot_prereview(ids: list[str]) -> None:
        """Grok Bot (pré-revue visuelle) passe AVANT le réviseur de code : on attend son commentaire
        « 🤖 Pré-revue » sur chaque PR de la tranche (au plus --bot-wait-min), puis on continue."""
        if not args.bot_wait_min or not ids:
            return
        nums = {lid: pr_number((state.done.get(lid) or {}).get("pr")) for lid in ids}
        nums = {k: v for k, v in nums.items() if v}
        log(f"attente de la pré-revue Grok Bot sur {sorted(nums.values())} (≤ {args.bot_wait_min} min)")
        t0 = time.time()
        while time.time() - t0 < args.bot_wait_min * 60:
            missing = []
            for lid, num in nums.items():
                try:
                    comments = http.github(f"/repos/{owner_repo(args.repo)}/issues/{num}/comments?per_page=100") or []
                except RuntimeError:
                    comments = []
                if not any(BOT_PREREVIEW_RE.search(c.get("body") or "") for c in comments):
                    missing.append(f"#{num}")
            if not missing:
                log("    pré-revue Grok Bot reçue sur toute la tranche")
                return
            time.sleep(60)
        log(f"    pré-revue Grok Bot absente sur {missing} après {args.bot_wait_min} min — le réviseur de code part sans")

    def night_review() -> None:
        """Lance le réviseur de nuit sur la tranche, puis met en file ses lots correctifs."""
        if not since_review or args.dry_run:
            return
        wait_bot_prereview(list(since_review))
        cmd = [sys.executable, str(HERE / "review_agent.py"), "--lots", *since_review, "--model", args.review_model, "--timeout-hours", str(args.review_timeout_hours)]
        log(f"revue de nuit : {since_review} → {args.review_model}")
        try:
            p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=int(args.review_timeout_hours * 3600) + 600,
                               env={**os.environ, "BIM_STATE_DIR": str(STATE_DIR)})
            for ln in (p.stdout + p.stderr).strip().splitlines()[-8:]:
                log(f"    {ln}")
        except subprocess.TimeoutExpired:
            log("    réviseur : délai dépassé — on continue la pile")
        since_review.clear()
        added = queued_lots(State.load(), {l.id for l in pending})
        if added:
            log(f"    lots correctifs mis en file par le réviseur : {[l.id for l in added]} — exécutés en bout de pile")
            pending.extend(added)

    while pending:
        lot = pending.pop(0)
        if lot.id in args.skip:
            log(f"[{lot.id}] sauté (--skip)")
            continue
        prev = state.done.get(lot.id)
        if args.resume and prev and prev.get("status") == "FINISHED":
            log(f"[{lot.id}] déjà fait ({prev.get('pr')}) — sauté")
            continue
        missing = [d for d in lot.deps if d not in state.done or state.done[d].get("status") != "FINISHED"]
        if missing and args.stack == "linear" and not args.dry_run:
            log(f"[{lot.id}] dépendances non faites dans cette session : {missing} — lancé quand même (le plan les suppose mergées ou dans la pile) ; vérifier le matin")
        run_lot(http, lot, state, args)
        if (state.done.get(lot.id) or {}).get("status") == "FINISHED" and (state.done.get(lot.id) or {}).get("pr"):
            since_review.append(lot.id)
        if args.review_every and len(since_review) >= args.review_every:
            night_review()
        if not pending and args.review_every and since_review:
            night_review()                # dernière tranche, puis les lots RC éventuels reprennent la boucle
        # lots ajoutés à queue.md à la main pendant la nuit
        pending.extend(queued_lots(state, {l.id for l in pending}))

    if not args.dry_run:
        log("terminé. Récapitulatif :")
        for lid, e in state.done.items():
            log(f"  {lid}: {e.get('status')} — {e.get('pr') or e.get('branch')} — CI {e.get('ci')}")
        if not args.no_recette:
            try:
                prepare_recette(state, args, http)
                url = tunnel_url() or (PROD_URL if getattr(args, "publish_tip", False) else None)
                if url:
                    post_parcours_request(state, url, args.repo)
            except Exception as e:  # le poste de recette ne doit jamais faire perdre le batch
                log(f"poste de recette impossible : {e} — à la main : python3 infra/agents/run_lots.py --recette")


if __name__ == "__main__":
    main()

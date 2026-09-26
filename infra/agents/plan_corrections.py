#!/usr/bin/env python3
"""Correcteur du matin (lot W3) : la revue humaine → un plan de corrections + des lots, en PR « GO ».

Le porteur a recetté la pile dans Chrome et coché les cases des PR (KO en commentaires,
captures jointes). Ce script :
  1. collecte cette revue (review_collect.py) — cases, KO, images, captures des agents,
     plus les commentaires du réviseur de nuit et les lots RC déjà exécutés ;
  2. lance un agent fort (Claude Fable, CLI Cursor local) dans un worktree propre sur
     `main`, avec pour base : la revue, le programme complet des lots
     (docs/LOTS_ORDRE_ET_PROMPTS.md — pré-rédigé pour qu'il puisse FONDRE une correction
     dans un lot à venir plutôt qu'en ouvrir un nouveau), les plans, les règles ;
  3. l'agent écrit docs/PLAN_CORRECTIONS_<date>.md et ajoute les prompts <!-- LOT id="RB…" -->
     à docs/LOTS_ORDRE_ET_PROMPTS.md, pousse la branche docs/plan-corrections-<date> et
     ouvre la PR (FR puis EN) dont le corps se termine par `LOTS: RB1 RB4`.
Le merge de cette PR par le porteur est le GO ; loop.py le guette et lance le batch suivant.
Ne merge jamais. Ne touche pas au code applicatif.

Budget (lot W8) : Fable est le seul modèle cher. Le matériel (prompt, revue, diffs propres des PR, commentaires,
images, docs lus) est MESURÉ et comparé à `BIM_CORRECTOR_CONTEXT_TOKENS` (1 000 000) × `BIM_CORRECTOR_BUDGET_SHARE`
(0,6) ; au-delà, découpage en plusieurs lancements dans la même branche, dans la limite de `BIM_CORRECTOR_MAX_RUNS`
par jour (1 ; « GO FABLE » sur une PR de la pile en accorde un de plus). Chaque lancement est noté dans
infra/agents/COUTS.md. `BIM_CORRECTOR_AUTO=1` autorise la boucle à lancer seule (défaut 0 : jamais sans revue humaine).

Usage :
    python3 infra/agents/plan_corrections.py                       # PR de state.json, modèle Fable
    python3 infra/agents/plan_corrections.py --prs 250 251 252     # PR précises
    python3 infra/agents/plan_corrections.py --prefix RB           # préfixe des nouveaux lots (défaut : premier libre RB, RD, RE…)
    python3 infra/agents/plan_corrections.py --session 2 --since 2026-09-22T14:00:00Z   # session suivante (lot W7)
    python3 infra/agents/plan_corrections.py --dry-run             # affiche le prompt et l'estimation, ne lance rien
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402
import review_collect as rc  # noqa: E402

DEFAULT_MODEL = os.environ.get("BIM_CORRECTOR_MODEL", "claude-fable-5-thinking-xhigh")
USED_PREFIXES_RE = re.compile(r'<!--\s*LOT\s+id="([A-Z]+)\d')


# ---------------------------------------------------------------- budget Fable (lot W8)
#
# Fable est le seul modèle cher de la boucle. On MESURE ce qu'on lui envoie et ce qu'il va lire, on
# compare à sa fenêtre (1M chez Cursor, réglable), et on découpe en plusieurs lancements s'il le faut —
# dans la limite d'un plafond journalier que seul le porteur relève (« GO FABLE » sur une PR de la pile).
# Par défaut : un lancement par jour, jamais sans revue humaine (BIM_CORRECTOR_AUTO=0).

def setting(name: str, default: str) -> str:
    return os.environ.get(name) or rl._env_file_values().get(name) or default


CONTEXT_TOKENS = int(setting("BIM_CORRECTOR_CONTEXT_TOKENS", "1000000"))     # fenêtre du modèle (Fable 5.1 Max : 1M)
BUDGET_SHARE = float(setting("BIM_CORRECTOR_BUDGET_SHARE", "0.6"))          # part de la fenêtre qu'on s'autorise à remplir
BUDGET_TOKENS = int(CONTEXT_TOKENS * BUDGET_SHARE)
MAX_RUNS = int(setting("BIM_CORRECTOR_MAX_RUNS", "1"))                       # lancements Fable par jour, hors « GO FABLE »
CHARS_PER_TOKEN = 3.2          # français + code : prudent (surestime un peu)
TOKENS_PER_DIFF_LINE = 14      # une ligne de diff lue par l'agent
TOKENS_PER_IMAGE = 1500
OVERHEAD = 1.5                 # sorties d'outils, raisonnement, relectures : ce que l'agent ajoute lui-même
FIXED_DOCS = ("docs/REGLES_WORKFLOW_AGENT.md", "docs/LOTS_ORDRE_ET_PROMPTS.md", "docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md")
COUTS_MD = rl.STATE_DIR / "COUTS.md"
EXIT_BUDGET = 3


def tokens_of(text: str) -> int:
    return int(len(text or "") / CHARS_PER_TOKEN)


def fixed_tokens(wt: Path, date: str) -> int:
    """Ce que le correcteur lit quoi qu'il arrive : règles, programme complet, plan modèle, plans du jour."""
    total = 0
    for rel in list(FIXED_DOCS) + previous_plans(wt, date):
        p = wt / rel
        if p.exists():
            total += tokens_of(p.read_text(encoding="utf-8", errors="replace"))
    return total


def own_changes(prs: list[dict]) -> dict[int, int]:
    """Lignes de diff PROPRES à chaque PR. Les PR sont empilées et visent toutes main : le diff GitHub de la
    k-ième contient tout ce qui précède ; sommer les 28 compterait la pile 28 fois (6 M de tokens, 22 sept.).
    Dans l'ordre des numéros, le propre = cumul − cumul précédent ; si le cumul redescend, la PR repart de
    main (nouvelle pile) et son diff est déjà le sien."""
    out: dict[int, int] = {}
    prev = 0
    for p in sorted(prs, key=lambda x: x.get("number") or 0):
        cum = int(p.get("changes") or 0)
        out[p["number"]] = cum - prev if cum > prev else cum
        prev = cum
    return out


def pr_tokens(p: dict, own: int) -> int:
    """Ce qu'une PR ajoute : son diff propre, ses commentaires (bot, réviseur, porteur), ses images."""
    return own * TOKENS_PER_DIFF_LINE + int(int(p.get("comments_chars") or 0) / CHARS_PER_TOKEN) + TOKENS_PER_IMAGE * len(p.get("local_images") or [])


def estimate(review: dict, prompt: str, wt: Path, date: str) -> dict:
    fixed = fixed_tokens(wt, date) + tokens_of(prompt) + tokens_of(review.get("global_file") or "")
    own = own_changes(review["prs"])
    per_pr = {p["number"]: pr_tokens(p, own.get(p["number"], 0)) for p in review["prs"]}
    total = int((fixed + sum(per_pr.values())) * OVERHEAD)
    return {"fixed": fixed, "per_pr": per_pr, "total": total, "budget": BUDGET_TOKENS, "context": CONTEXT_TOKENS}


def group_tokens(grp: list[dict], est: dict) -> int:
    return int((est["fixed"] + sum(est["per_pr"].get(p["number"], 0) for p in grp)) * OVERHEAD)


def split_groups(review: dict, est: dict) -> tuple[list[list[dict]], bool]:
    """Découper les PR en groupes qui tiennent chacun dans le budget (le fixe compte dans chaque groupe).
    Second élément : vrai si un groupe dépasse quand même (le fixe seul est trop gros, ou une PR énorme)."""
    room = est["budget"] / OVERHEAD - est["fixed"]
    if room <= 0:   # même le fixe dépasse : un seul groupe, on préviendra l'agent
        return [list(review["prs"])], True
    groups: list[list[dict]] = [[]]
    used = 0
    for p in review["prs"]:
        t = est["per_pr"].get(p["number"], 0)
        if groups[-1] and used + t > room:
            groups.append([])
            used = 0
        groups[-1].append(p)
        used += t
    return groups, any(group_tokens(g, est) > est["budget"] for g in groups)


def runs_today(state: "rl.State", date: str) -> int:
    return sum(int(c.get("runs") or 1) for c in (state.extra.get("corrections") or []) if c.get("at") == date and c.get("status") not in ("dry_run", "budget"))


def note_cost(date: str, session: int, part: str, prs: list[int], est_tokens: int, model: str, status: str) -> None:
    """COUTS.md : une ligne par lancement Fable — la dépense doit être lisible le matin."""
    new = not COUTS_MD.exists()
    with COUTS_MD.open("a", encoding="utf-8") as fh:
        if new:
            fh.write("# Coûts — lancements du correcteur (Fable) et batches\n\n| quand | session | partie | PR couvertes | tokens estimés | modèle | statut |\n|---|---|---|---|---|---|---|\n")
        fh.write(f"| {time.strftime('%Y-%m-%d %H:%M')} | {session} | {part} | {' '.join(f'#{n}' for n in prs) or '—'} | {est_tokens:,} | {model} | {status} |\n".replace(",", " "))


def next_prefix(prompts_md: str) -> str:
    used = set(USED_PREFIXES_RE.findall(prompts_md))
    for letter in "BDEFHJKMPQSTVXYZ":
        cand = "R" + letter
        if cand not in used:
            return cand
    return "RZ"


def lot_already_done(lot_id: str) -> bool:
    """Le lot est FINISHED dans state.json ou dans une pile archivée (state.<ts>.json) : le programme
    jusqu'à lui a déjà été joué — le rejouer depuis main referait 20 PR (garde du 22 sept.)."""
    for p in [rl.STATE_JSON, *rl.STATE_DIR.glob("state.*.json")]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if ((d.get("done") or {}).get(lot_id) or {}).get("status") == "FINISHED":
            return True
    return False


def then_until() -> str | None:
    """BIM_THEN_UNTIL=D0 (environnement ou ~/.config/naviguide/simulator.env) : après les corrections,
    la nuit enchaîne le programme jusqu'à ce lot — la ligne LOTS du GO couvre alors RB1 … D0.
    Ignoré (avec une ligne de journal) si ce lot a déjà été joué."""
    target = os.environ.get("BIM_THEN_UNTIL") or rl._env_file_values().get("BIM_THEN_UNTIL") or None
    if target and lot_already_done(target):
        rl.log(f"BIM_THEN_UNTIL={target} ignoré : ce lot a déjà été joué (retirer la ligne du fichier de clés)")
        return None
    return target


def previous_plans(wt: Path, date: str) -> list[str]:
    """Plans déjà produits aujourd'hui (sessions précédentes, lot W7) — pour ne pas replanifier ce qu'ils couvrent."""
    return sorted(str(p.relative_to(wt)) for p in (wt / "docs").glob(f"PLAN_CORRECTIONS_{date}*.md"))


def build_prompt(review: dict, wt: Path, date: str, prefix: str, model: str, night: list[dict], *, tag: str | None = None, since: str | None = None) -> str:
    tag = tag or date
    md_path = review.get("md")
    json_path = review.get("json")
    imgs = [im["path"] for p in review["prs"] for im in p.get("local_images", [])]
    kos = sum(len(p.get("ko") or []) for p in review["prs"])
    new_kos = sum(1 for p in review["prs"] for k in (p.get("ko") or []) if k.get("new", True))
    ticked = sum(p.get("ok", 0) for p in review["prs"])
    total = sum(len(p.get("items") or []) for p in review["prs"])
    prev = previous_plans(wt, date)
    parts = [
        "Tu es le correcteur du matin de la pile de PR du simulateur NAVIGUIDE (Berry-Mappemonde/Blue-Intelligence). Le porteur a recetté dans Chrome : "
        f"il a coché {ticked} items sur {total} et écrit {kos} commentaire(s) KO" + (f", dont {new_kos} nouveaux depuis la session précédente ({since})" if since else "") + ". "
        "Ta mission : transformer sa revue en un plan de corrections et en lots prêts à être enchaînés par infra/agents/run_lots.py, sur une branche docs, en PR. "
        "Tu ne touches PAS au code applicatif, tu ne merges rien.",
        "",
        f"Environnement : worktree `{wt}` sur `main` à jour (HEAD détaché) : `git checkout -b docs/plan-corrections-{tag}` d'abord. Bibliothèque : "
        "`python3 infra/agents/open_pr.py <branche> main \"<titre FR — EN>\" <fichier-corps.md>` pour ouvrir la PR.",
        "",
        *([f"## Sessions précédentes aujourd'hui (lot W7 — revue à la volée)",
           "Le porteur relit la pile en plusieurs fois ; chaque « revue finie » ouvre une session. Les plans ci-dessous existent déjà sur main et leurs lots sont "
           "en file ou déjà codés : lis-les d'abord, et NE REPLANIFIE PAS ce qu'ils couvrent. Dans la revue, les KO marqués 🆕 (ou `new: true` dans le JSON) sont "
           "arrivés depuis la session précédente : c'est d'abord eux que tu traites, plus toute case décochée ou tout point de la revue globale qu'aucun plan ne couvre encore.",
           *[f"- `{p}`" for p in prev], ""] if (since or prev) else []),
        "## Lis d'abord, en entier",
        "- docs/REGLES_WORKFLOW_AGENT.md (§ 1 rien de superflu à l'écran ; § 3 gabarit de PR bilingue ; § 4 recette visuelle).",
        "- docs/LOTS_ORDRE_ET_PROMPTS.md : le PROGRAMME COMPLET, y compris les lots à venir (R8…, N…, G…). Règle d'or : quand une correction relève d'un lot à venir, "
        "tu FONDS la correction dans ce lot (tu complètes son prompt : « Constat de la revue du <date> : … » + l'étape ajoutée) au lieu d'ouvrir un lot ; tu n'ouvres un lot "
        f"{prefix}<n> que pour ce qu'aucun lot à venir ne couvre.",
        "- docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md : le modèle de plan (structure, niveau de détail, anchors fichier:ligne, recette visuelle par écran).",
        "- Le plan de chaque lot recetté (colonne `plan` de sa balise LOT).",
        "",
        "## La revue du porteur",
        f"- Résumé lisible : `{md_path}` ; données : `{json_path}` (cases cochées = OK vu ; cases vides = pas vu ou pas bon ; `ko` = ce qui ne va pas, dans ses mots).",
        "- **Sa revue globale** (vision d'ensemble, hors cases — le plus important, à traiter comme la revue du 21 sept. : chaque point → un lot, un complément de lot du programme, ou une décision notée dans le plan) :",
        "```",
        (review.get("global_file") or "(rien dans REVUE_GLOBALE.md)")[:12000],
        "```",
        *[f"- GLOBAL (PR #{p['number']}) : {g['text'][:1500]}" for p in review["prs"] for g in (p.get("global") or [])],
        "- Images (ouvre-les avec l'outil de lecture d'image ; chaque image du porteur est rattachée à quelque chose qui ne va pas) : " + (", ".join(f"`{p}`" for p in imgs) if imgs else "aucune"),
        "",
    ]
    if night:
        parts += ["## Ce que le réviseur de nuit a déjà dit et fait", ""]
        for r in night:
            parts.append(f"- Tranche {r.get('lots')} ({r.get('at')}) : lots correctifs déjà exécutés cette nuit : {r.get('queued') or 'aucun'} ; commentaires postés sur les PR (lis-les : ils contiennent des verdicts et des fichier:ligne). Dossier : `{r.get('dir')}`.")
        parts.append("")
    parts += [
        "## Ce que tu produis",
        "",
        f"1. `docs/PLAN_CORRECTIONS_{tag}.md` : § 0 rappels ; § 1 revue par PR (OK / KO du porteur, verdict du réviseur de nuit) ; § 2 revue générale ; "
        "§ 3 ce qui est reporté et pourquoi (fondu dans quel lot à venir) ; § 4 les lots correctifs, chacun avec : cause racine (fichier:ligne — lis le code sur main, "
        "ne devine pas), fichiers à ouvrir (≤ 6, App.jsx / MapSceneController.js par rg -n), étapes, tests, recette VISUELLE par écran ; § 5 ordre et pile. Français.",
        f"2. `docs/LOTS_ORDRE_ET_PROMPTS.md` : (a) une ligne de tableau par lot {prefix}<n> après la dernière ligne ; (b) les balises `<!-- LOT id=\"{prefix}<n>\" title=\"…\" plan=\"docs/PLAN_CORRECTIONS_{tag}.md\" size=\"S|M\" deps=\"…\" -->` "
        "suivies du bloc ```text``` au format exact des lots existants (lis-en deux avant d'écrire), AVANT la section « ## 3. Enchaîner » ; (c) les compléments fondus dans les lots à venir "
        "(une ligne « Constat de la revue du <date> : … » + l'étape, dans le prompt du lot concerné, sans changer son id ni sa balise).",
        f"3. Vérifie : `python3 infra/agents/run_lots.py --dry-run --from {prefix}1 --until {prefix}<dernier>` liste tes lots.",
        f"4. Commit conventionnel (`docs: corrections de la revue du {date} …`), `git push -u origin docs/plan-corrections-{tag}`, puis la PR avec open_pr.py. "
        f"Corps de la PR : gabarit REGLES § 3, en français PUIS en anglais, et en DERNIÈRE ligne exactement : `LOTS: {prefix}1 {prefix}<dernier>` (ou `LOTS: aucun` s'il n'y a rien à corriger).",
        *([f"   PROGRAMME ENCHAÎNÉ : le porteur veut que la nuit continue, après les corrections, avec le programme pré-rédigé jusqu'au lot **{then_until()}**. "
           f"Place donc tes balises `<!-- LOT id=\"{prefix}<n>\" … -->` et tes lignes de tableau JUSTE APRÈS le dernier lot déjà exécuté (la dernière balise RA…) et AVANT le bloc R8a, "
           f"pour que l'ordre du document soit : … RA8, {prefix}1 … {prefix}<dernier>, R8a … {then_until()}. Et la dernière ligne du corps de la PR devient exactement : `LOTS: {prefix}1 {then_until()}` "
           f"(s'il n'y a rien à corriger : `LOTS: R8a {then_until()}`). Vérifie avec `python3 infra/agents/run_lots.py --dry-run --from {prefix}1 --until {then_until()}`."] if then_until() else []),
        "5. Termine par un résumé de 5 lignes : lots créés, corrections fondues (dans quels lots), ce que tu n'as pas su rattacher.",
        "",
        "Interdits : toucher au code applicatif ; merger ; inventer une cause sans l'avoir lue dans le code ; recette technique (data-testid, GET, coordonnées) ; "
        "plus de 8 lots ; un lot > 400 lignes de diff estimé.",
    ]
    return "\n".join(parts)


AMEND_RE = re.compile(r"^\s*(?:\*\*)?(CORRIGER|AMENDER|REVOIR|CHANGER)\s*:", re.I)


def amend_comments(go_pr: int, seen: set[int]) -> list[dict]:
    """Commentaires « CORRIGER : … » du porteur sur la PR GO, pas encore traités."""
    http = rl.Http(None, rl.github_token_from_git())
    out = []
    for c in http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/issues/{go_pr}/comments?per_page=100") or []:
        body = (c.get("body") or "").strip()
        if c.get("id") in seen or not AMEND_RE.match(body) or not rc.trusted(c):
            continue
        out.append({"id": c.get("id"), "author": (c.get("user") or {}).get("login"), "text": body, "url": c.get("html_url")})
    return out


def build_amend_prompt(go_pr: dict, comments: list[dict], wt: Path, model: str) -> str:
    branch = (go_pr.get("head") or {}).get("ref")
    return "\n".join([
        f"Tu es le correcteur du GO. Un premier agent a écrit la PR #{go_pr['number']} ({go_pr['html_url']}) sur la branche `{branch}` : "
        "docs/PLAN_CORRECTIONS_<date>.md + des lots `<!-- LOT -->` dans docs/LOTS_ORDRE_ET_PROMPTS.md. Le porteur l'a lue et demande des changements. "
        "Ta mission : AMENDER cette PR selon ses commentaires — pas la refaire, pas ouvrir une autre PR, pas toucher au code applicatif, pas merger.",
        "",
        f"Environnement : worktree `{wt}`, déjà sur la branche `{branch}` (à jour d'origin). Lis d'abord le plan et les lots que tu dois amender, "
        "puis docs/REGLES_WORKFLOW_AGENT.md § 1, § 3, § 4 et le programme complet (docs/LOTS_ORDRE_ET_PROMPTS.md).",
        "",
        "## Les commentaires du porteur (à traiter tous, dans l'ordre)",
        *[f"- ({c['author']}) {c['text']}" for c in comments],
        "",
        "## Ce que tu produis",
        "1. Modifie le plan et/ou les lots exactement dans le sens demandé (ajouter, retirer, fusionner, reformuler, changer une cause racine ou une recette). "
        "Un point du porteur = un changement visible dans le diff. Si un point te semble impossible ou contradictoire, écris-le dans ta réponse au lieu d'inventer.",
        "2. Garde la cohérence : ids de lots continus, table et balises alignées, `python3 infra/agents/run_lots.py --dry-run --from <premier> --until <dernier>` passe.",
        "3. Commit (`docs: GO amendé selon les commentaires du porteur — …`), `git push` sur la MÊME branche (la PR se met à jour). "
        f"Si la liste des lots à lancer change, mets à jour le corps de la PR avec `python3 {rl.HERE / 'open_pr.py'} {branch} main \"<titre inchangé>\" <corps.md>` "
        "(il remplace le corps) en gardant la dernière ligne `LOTS: <premier> <dernier>` exacte.",
        f"4. Réponds dans la PR : `python3 {rl.HERE / 'post_pr_comment.py'} {go_pr['number']} <fichier.md>` avec un commentaire qui commence par `## 🛠 GO amendé` : "
        "un point par commentaire du porteur → ce que tu as changé (fichier, lot), ou pourquoi non.",
        "5. Termine par un résumé de 5 lignes sur la sortie standard.",
        "",
        "Interdits : nouvelle PR ; code applicatif ; merge ; supprimer un lot que le porteur n'a pas demandé de retirer ; recette technique (data-testid, GET, coordonnées).",
    ])


def amend(go_pr_number: int, *, model: str = DEFAULT_MODEL, seen: set[int] | None = None, dry_run: bool = False, timeout_h: float = 1.0) -> dict:
    """Un second agent Claude corrige le GO selon les commentaires « CORRIGER : » — autant de tours que voulu."""
    seen = set(seen or ())
    http = rl.Http(None, rl.github_token_from_git())
    go_pr = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/pulls/{go_pr_number}") or {}
    comments = amend_comments(go_pr_number, seen)
    if not comments:
        return {"ok": True, "handled": [], "note": "aucun commentaire CORRIGER : nouveau"}
    branch = (go_pr.get("head") or {}).get("ref")
    if dry_run:
        print(build_amend_prompt(go_pr, comments, rl.WORKTREES / "corrector", model))
        return {"ok": True, "dry_run": True, "handled": [c["id"] for c in comments]}
    wt = rl.WORKTREES / "corrector"
    if not wt.exists() or rl.local_branch(wt) != branch:
        wt = rl.prepare_worktree(rl.Lot("corrector", "correcteur du GO", "", "", [], ""), branch)
        rl.sh(["git", "checkout", "-q", branch], cwd=wt, check=False)
    rl.sh(["git", "fetch", "-q", "origin", branch], cwd=wt, check=False, timeout=120)
    rl.sh(["git", "reset", "-q", "--hard", f"origin/{branch}"], cwd=wt, check=False)
    prompt = build_amend_prompt(go_pr, comments, wt, model)
    rl.log(f"GO #{go_pr_number} : {len(comments)} commentaire(s) CORRIGER — agent {model} sur `{branch}`")
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    status, result = rl.run_agent_cli_watched(wt, prompt, model, int(timeout_h * 3600), done=lambda: amend_delivered(http, go_pr_number, started))
    rl.log(f"    amendement : {status}")
    for ln in (result or "").strip().splitlines()[-5:]:
        rl.log(f"    {ln}")
    if status == "STOPPED":
        rl.sh(["git", "checkout", "-q", "--", "."], cwd=wt, check=False)
    if branch:
        rl.ensure_pushed(wt, branch)
    return {"ok": status in ("FINISHED", "STOPPED"), "handled": [c["id"] for c in comments]}


def amend_delivered(http: "rl.Http", go_pr_number: int, since_iso: str) -> str | None:
    """L'agent d'amendement a fini quand sa réponse « ## 🛠 GO amendé » est postée (après le début) et que la
    PR est mergée ou n'a plus bougé depuis GO_IDLE_MIN."""
    try:
        pr = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/pulls/{go_pr_number}") or {}
        if pr.get("merged_at"):
            return f"la PR GO #{go_pr_number} est déjà mergée"
        comments = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/issues/{go_pr_number}/comments?per_page=100") or []
    except Exception:
        return None
    answered = [c for c in comments if (c.get("body") or "").lstrip().startswith("## 🛠") and (c.get("created_at") or "") >= since_iso]
    if not answered:
        return None
    last_ts = calendar.timegm(time.strptime(answered[-1]["created_at"], "%Y-%m-%dT%H:%M:%SZ"))
    if (time.time() - last_ts) / 60 >= 5:   # cinq minutes après sa réponse, il n'a plus rien à faire
        return f"réponse « GO amendé » postée sur #{go_pr_number}, sans suite depuis 5 min"
    return None


def part_prompt(prompt: str, i: int, n: int, tag: str, prefix: str, go_pr: int | None, over_budget: bool) -> str:
    """Le prompt d'une partie quand le matériel est découpé en n lancements (lot W8)."""
    extra = []
    if n > 1 and i == 1:
        extra += [f"## Partie 1/{n}", f"Le matériel dépasse ce qu'un seul lancement peut lire : cette partie ne couvre que les PR listées dans la revue ci-dessus ; "
                  f"{n - 1} autre(s) lancement(s) suivront dans la MÊME branche `docs/plan-corrections-{tag}` et compléteront le plan, les lots et la PR. "
                  "Numérote tes lots à partir de 1, laisse le § 4 du plan ouvert (une sous-section par lot), et ouvre la PR normalement."]
    elif n > 1:
        extra += [f"## Partie {i}/{n} — suite d'un plan déjà commencé",
                  f"Le plan `docs/PLAN_CORRECTIONS_{tag}.md`, des lots `{prefix}<n>` et la PR GO" + (f" #{go_pr}" if go_pr else "") + f" existent déjà (parties précédentes, branche `docs/plan-corrections-{tag}`, "
                  "déjà extraite dans ce worktree : `git pull` d'abord). COMPLÈTE-les avec les PR de cette partie : ids de lots continus après le dernier existant, "
                  "table et balises alignées, et mets à jour la DERNIÈRE ligne `LOTS: <premier> <dernier>` du corps de la PR avec `open_pr.py` (il remplace le corps). Pas de nouvelle PR."]
    if over_budget:
        extra += ["## Attention : matériel au-delà du budget",
                  "Même découpé, ce lancement dépasse le budget prévu : lis les diffs PAR EXTRAITS (`git diff main...<branche> -- <fichier> | head`, `rg -n`), jamais en entier, "
                  "et n'ouvre les images que si un KO les cite."]
    return prompt + ("\n\n" + "\n".join(extra) if extra else "")


def refuse_budget(review: dict, session: int, done: int, allowed: int, est: dict, model: str) -> None:
    """Plafond du jour atteint : rien n'est lancé, on le dit sur la PR de tête (une fois par session)."""
    tip = (review["prs"] or [{}])[-1].get("number")
    rl.log(f"budget Fable : plafond atteint ({done}/{allowed} lancement(s) aujourd'hui, BIM_CORRECTOR_MAX_RUNS={MAX_RUNS}) — correcteur NON lancé ; "
           "« GO FABLE » sur une PR de la pile autorise un lancement de plus")
    note_cost(time.strftime("%Y-%m-%d"), session, "—", [p["number"] for p in review["prs"]], est["total"], model, f"refusé (plafond {done}/{allowed})")
    if tip:
        body = (f"## 🧮 Fable — plafond du jour atteint ({done}/{allowed}) / daily cap reached\n\n"
                f"Session {session} : ~{est['total']:,} tokens estimés à envoyer au correcteur, budget {est['budget']:,}. Rien n'a été lancé. "
                "Écris **`GO FABLE`** ici pour autoriser un lancement de plus (ou relève `BIM_CORRECTOR_MAX_RUNS` dans le fichier de clés).\n"
                "Nothing was launched. Write **`GO FABLE`** here to allow one more run.").replace(",", " ")
        tmp = rl.STATE_DIR / "budget-comment.md"
        tmp.write_text(body, encoding="utf-8")
        rl.sh([sys.executable, str(HERE / "post_pr_comment.py"), str(tip), str(tmp)], check=False, timeout=120)


def run(prs: list[tuple[str, int]], *, model: str = DEFAULT_MODEL, prefix: str | None = None, dry_run: bool = False, timeout_h: float = 1.5,
        session: int = 1, since: str | None = None, extra_runs: int = 0) -> dict:
    state = rl.State.load()
    date = time.strftime("%Y-%m-%d")
    tag = f"{date}-s{session}" if session > 1 else date      # lot W7 : une branche et un plan par session
    review = rc.collect(prs, rl.STATE_DIR, images=True, since=since, session=session)
    night = list(state.extra.get("reviews") or [])
    if review.get("global_file"):
        rl.log(f"revue globale du porteur : {len(review['global_file'])} caractères dans REVUE_GLOBALE.md")
    prefix = prefix or next_prefix(rl.PROMPTS_MD.read_text(encoding="utf-8"))
    wt = rl.WORKTREES / "corrector" if dry_run else rl.prepare_worktree(rl.Lot("corrector", "correcteur du matin", "", "", [], ""), "main")
    docs_root = wt if (wt / "docs").exists() else rl.ROOT
    prompt = build_prompt(review, wt, date, prefix, model, night, tag=tag, since=since)

    # Lot W8 : mesurer, découper, plafonner
    est = estimate(review, prompt, docs_root, date)
    if est["total"] <= est["budget"]:
        groups, over_budget = [list(review["prs"])], False
    else:
        groups, over_budget = split_groups(review, est)
    allowed = MAX_RUNS + int(extra_runs or 0)
    done = runs_today(state, date)
    rl.log((f"budget Fable : ~{est['total']:,} tokens estimés pour {len(review['prs'])} PR (fixe {est['fixed']:,}, budget {est['budget']:,} = {BUDGET_SHARE:.0%} de {CONTEXT_TOKENS:,}) "
            f"→ {len(groups)} lancement(s) ; aujourd'hui {done}/{allowed}").replace(",", " "))
    if not dry_run and done >= allowed:
        refuse_budget(review, session, done, allowed, est, model)
        state = rl.State.load()
        state.extra.setdefault("corrections", []).append({"at": date, "session": session, "since": since, "prs": [n for _, n in prs], "model": model, "status": "budget", "runs": 0})
        state.save()
        return {"ok": False, "budget": True, "session": session}
    if done + len(groups) > allowed:
        keep = max(1, allowed - done)
        groups = groups[:keep - 1] + [sum(groups[keep - 1:], [])]
        over_budget = True
        rl.log(f"    plafond : {keep} lancement(s) seulement → matériel regroupé au-delà du budget (l'agent lira les diffs par extraits)")
    if dry_run:
        print(part_prompt(prompt, 1, len(groups), tag, prefix, None, over_budget))
        print(f"\n[estimation] {json.dumps({k: v for k, v in est.items() if k != 'per_pr'})} ; groupes : {[[p['number'] for p in g] for g in groups]}")
        return {"ok": True, "dry_run": True, "prefix": prefix, "session": session, "estimate": est["total"], "runs": len(groups)}

    (rl.STATE_DIR / f"corrector-prompt-{tag}.md").write_text(prompt, encoding="utf-8")
    rl.log(f"correcteur du matin (session {session}) : {len(prs)} PR, préfixe {prefix}, agent {model} dans {wt}, {len(groups)} lancement(s)")
    http = rl.Http(None, rl.github_token_from_git())
    status, branch, go_pr = "ERROR", None, None
    for i, grp in enumerate(groups, 1):
        rev_i = review if len(groups) == 1 else {**review, "prs": grp, "md": str(rl.STATE_DIR / f"review-{tag}-p{i}.md")}
        if len(groups) > 1:
            Path(rev_i["md"]).write_text(rc.summary_md(rev_i), encoding="utf-8")
            prompt_i = part_prompt(build_prompt(rev_i, wt, date, prefix, model, night, tag=tag, since=since), i, len(groups), tag, prefix, go_pr, over_budget)
        else:
            prompt_i = part_prompt(prompt, 1, 1, tag, prefix, None, over_budget)
        part = f"{i}/{len(groups)}"
        est_i = group_tokens(grp, est)
        status, result = rl.run_agent_cli_watched(wt, prompt_i, model, int(timeout_h * 3600), done=lambda: go_delivered(http, f"docs/plan-corrections-{tag}", last_part=(i == len(groups))))
        rl.log(f"    correcteur (partie {part}) : {status}")
        for ln in (result or "").strip().splitlines()[-6:]:
            rl.log(f"    {ln}")
        note_cost(date, session, part, [p["number"] for p in grp], est_i, model, status)
        if status == "STOPPED":   # le travail était livré ; un brouillon laissé derrière ne doit pas partir
            rl.sh(["git", "checkout", "-q", "--", "."], cwd=wt, check=False)
        branch = rl.local_branch(wt)
        if branch and rl.ensure_pushed(wt, branch):
            pr = rl.find_pr(http, rl.DEFAULT_REPO, branch, state="all")   # même déjà mergée par le porteur
            if pr:
                go_pr = pr["number"]
        if status not in ("FINISHED", "STOPPED"):
            break
    delivered = status in ("FINISHED", "STOPPED")
    if go_pr:
        rl.log(f"    PR GO #{go_pr} https://github.com/{rl.owner_repo(rl.DEFAULT_REPO)}/pull/{go_pr} — à merger par le porteur pour lancer le batch suivant")
    elif branch:
        rl.log("    la PR GO n'a pas été ouverte par l'agent : `python3 infra/agents/open_pr.py " + branch + " main \"docs: corrections\" <corps.md>`")
    archived = rc.archive_global_file(date) if delivered else None
    if archived:
        rl.log(f"revue globale archivée : {archived} (fichier remis à zéro)")
    state = rl.State.load()
    state.extra.setdefault("corrections", []).append({"at": date, "session": session, "since": since, "prs": [n for _, n in prs], "model": model, "status": status,
                                                      "branch": branch, "go_pr": go_pr, "prefix": prefix, "global_archived": archived,
                                                      "runs": len(groups), "estimate_tokens": est["total"], "over_budget": over_budget})
    state.save()
    return {"ok": delivered, "branch": branch, "go_pr": go_pr, "prefix": prefix, "session": session, "runs": len(groups)}


GO_IDLE_MIN = 20   # PR GO ouverte et plus aucun commit depuis 20 min : l'agent a fini, même s'il ne le dit pas


def go_delivered(http: "rl.Http", branch: str, *, last_part: bool = True) -> str | None:
    """Raison d'arrêter le correcteur, ou None. Sa PR existe et : elle est mergée (le porteur n'attend plus
    rien de lui) ; ou elle n'a plus bougé depuis GO_IDLE_MIN (il rumine — 26 sept. : une heure de plus,
    jusqu'à défaire ses lots dans son worktree). Pour une partie intermédiaire (matériel découpé), on
    laisse l'agent finir : la PR sera complétée par la partie suivante."""
    try:
        pr = rl.find_pr(http, rl.DEFAULT_REPO, branch, state="all")
    except Exception:
        return None
    if not pr:
        return None
    if pr.get("merged_at"):
        return f"la PR GO #{pr['number']} est déjà mergée"
    if not last_part:
        return None
    commits = http.github(f"/repos/{rl.owner_repo(rl.DEFAULT_REPO)}/pulls/{pr['number']}/commits?per_page=100") or []
    stamps = [((c.get("commit") or {}).get("committer") or {}).get("date") or "" for c in commits] + [pr.get("created_at") or ""]
    last = max(stamps)
    try:
        last_ts = calendar.timegm(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None
    idle_min = (time.time() - last_ts) / 60
    if idle_min >= GO_IDLE_MIN:
        return f"la PR GO #{pr['number']} est ouverte et n'a plus bougé depuis {idle_min:.0f} min"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prs", nargs="+", type=int, help="numéros de PR (défaut : PR FINISHED de state.json)")
    ap.add_argument("--prefix", help="préfixe des nouveaux lots (défaut : premier libre)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--timeout-hours", type=float, default=1.5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--amend", type=int, metavar="GO_PR", help="corriger la PR GO donnée selon ses commentaires « CORRIGER : » (second agent)")
    ap.add_argument("--session", type=int, default=1, help="numéro de la session de revue du jour (lot W7 : branche et plan suffixés -s<n> à partir de 2)")
    ap.add_argument("--since", help="ISO UTC : les KO antérieurs ont déjà été lus par une session précédente (ne pas replanifier)")
    ap.add_argument("--extra-runs", type=int, default=0, help="lancements Fable accordés en plus du plafond du jour (« GO FABLE » du porteur, lot W8)")
    args = ap.parse_args()
    if args.amend:
        out = amend(args.amend, model=args.model, dry_run=args.dry_run, timeout_h=args.timeout_hours)
        print(json.dumps(out, ensure_ascii=False))
        return
    prs = [("", n) for n in args.prs] if args.prs else rc.prs_from_state()
    if not prs:
        sys.exit("Aucune PR : --prs … ou un state.json avec des lots FINISHED.")
    out = run(prs, model=args.model, prefix=args.prefix, dry_run=args.dry_run, timeout_h=args.timeout_hours, session=args.session, since=args.since,
              extra_runs=args.extra_runs)
    if not args.dry_run:
        print(json.dumps(out, ensure_ascii=False))
    if out.get("budget"):
        sys.exit(EXIT_BUDGET)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Réviseur de nuit (lot W3-nuit) : toutes les X PR, un agent fort relit la tranche.

Pendant la nuit, le porteur ne recette pas. Toutes les X PR (`run_lots.py --review-every X`),
un agent fort (Claude Fable, CLI Cursor local) relit les X dernières PR de la pile :
diff, corps de PR, captures, prompt du lot, plan, règles — et **profite du travail déjà
fait** par les agents Grok sur les PR suivantes (il lit la tête de pile). Il produit :

  1. un commentaire de revue par PR (gabarit WORKFLOW_INDUSTRIEL § 1.3 : conformité,
     libertés prises, plancher main, chiffres LLM / secrets / tests affaiblis, prérequis,
     verdict MERGER / MERGER APRÈS CORRECTION / NE PAS MERGER), posté sur GitHub ;
  2. s'il le faut, des lots correctifs `<!-- LOT id="RC…" -->` dans `infra/agents/queue.md`,
     que run_lots.py relit entre deux lots et exécute en bout de pile **la même nuit** ;
     quand la correction relève d'un lot à venir du programme, il le dit (deps) au lieu
     de refaire son travail.

Il ne commite ni ne pousse de code, ne merge rien, ne touche pas à docs/. Le matin, le
porteur retrouve chaque PR commentée et les corrections déjà faites ; plan_corrections.py
prend le relais avec sa revue humaine.

Usage :
    python3 infra/agents/review_agent.py --lots RA3 RA4 RA5 RA6
    python3 infra/agents/review_agent.py --since-last                # depuis la dernière revue (state.json)
    python3 infra/agents/review_agent.py --dry-run --lots RA3        # affiche le prompt, ne lance rien
    python3 infra/agents/review_agent.py --lots RA3 --model claude-sonnet-5-thinking-high
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402  (mêmes helpers : worktree, CLI, GitHub, state)
import review_collect as rc  # noqa: E402

QUEUE_MD = rl.STATE_DIR / "queue.md"
REVIEW_DIR = rl.STATE_DIR / "reviews"
DEFAULT_REVIEW_MODEL = os.environ.get("BIM_REVIEW_MODEL", "claude-fable-5-thinking-xhigh")

REVIEW_TEMPLATE = """Lot {lot} — revue automatique (nuit, {model})
1. Conformité au lot : chaque étape du prompt → faite / partielle / non faite (fichier:ligne).
2. Libertés prises : décisions de l'agent hors du lot (rubrique « Décisions » de la PR + ce que le diff montre). Pour chacune : acceptable / à discuter / à défaire.
3. Plancher main : surfaces retirées, cachées, conditionnées ? (`git diff origin/main -- naviguide-simulator/src/App.jsx src/components src/map`)
4. Chiffres produits par un LLM, secrets, tests affaiblis, data-testid renommés, fichiers hors liste, texte d'aide ajouté à l'écran, redite.
5. Recette : les cases de la PR sont-elles visuelles (« ouvre, clique, tu dois voir ») et bilingues ? Les captures existent-elles sur la branche ?
6. Prérequis pour recetter : clés, variables, données, redémarrage.
7. Verdict : MERGER / MERGER APRÈS CORRECTION (liste) / NE PAS MERGER (pourquoi).
"""


def lots_since_last_review(state: rl.State) -> list[str]:
    reviewed = set()
    for r in (state.extra.get("reviews") or []):
        reviewed.update(r.get("lots") or [])
    return [lid for lid, e in state.done.items() if e.get("status") == "FINISHED" and e.get("pr") and lid not in reviewed]


def lot_texts(ids: list[str]) -> dict[str, rl.Lot]:
    known = {l.id: l for l in rl.parse_lots(rl.PROMPTS_MD.read_text(encoding="utf-8"))}
    if QUEUE_MD.exists():
        for l in rl.parse_lots_text(QUEUE_MD.read_text(encoding="utf-8")):
            known.setdefault(l.id, l)
    return {i: known[i] for i in ids if i in known}


def build_prompt(state: rl.State, ids: list[str], wt: Path, review_dir: Path, model: str, http: rl.Http | None) -> str:
    texts = lot_texts(ids)
    parts = [
        "Tu es le réviseur de nuit de la pile de PR du simulateur NAVIGUIDE (dépôt Berry-Mappemonde/Blue-Intelligence). "
        "Le porteur dort : tu relis les PR ci-dessous avec le regard qu'il aura demain (visuel, produit, règles), tu commentes chaque PR sur GitHub, "
        "et tu mets en file les corrections que des agents Grok exécuteront cette nuit. Tu ne commites ni ne pousses AUCUN code, tu ne merges rien, tu ne touches pas à docs/.",
        "",
        f"Environnement : worktree `{wt}` sur la TÊTE de pile `{state.last_branch}` (HEAD détaché) : le code que tu lis inclut déjà le travail des lots suivants — tiens-en compte "
        "(une correction déjà faite par un lot suivant n'est pas à refaire). `node_modules` et `.venv` sont des liens : ne réinstalle rien. Tu peux lancer `npm test`, `pytest`, `npx vite build` "
        "et `bash naviguide-simulator/ensure-dev.sh --prod` pour voir l'app sur http://localhost:5174 si nécessaire (Playwright : `PW_PORT=5199`).",
        "",
        "Lis d'abord en entier : docs/REGLES_WORKFLOW_AGENT.md (surtout § 1 « rien de superflu à l'écran », § 3 gabarit, § 4 recette visuelle) et docs/WORKFLOW_INDUSTRIEL.md § 1.3. "
        "Le programme complet des lots (à venir compris) est dans docs/LOTS_ORDRE_ET_PROMPTS.md : quand une correction relève d'un lot à venir (ex. R8 déplace la fiche d'escale, R9 refait le texte du film), "
        "ne la refais pas — écris-le dans le verdict et, si un petit lot est quand même utile, donne-lui `deps` sur ce lot.",
        "",
        "## Les PR à relire (dans l'ordre de la pile)",
        "",
    ]
    prev_branch = "origin/main"
    for lid in ids:
        e = state.done.get(lid) or {}
        lot = texts.get(lid)
        num = rl.pr_number(e.get("pr"))
        pr = rl.fetch_pr(http, rl.DEFAULT_REPO, num) if num else None
        body = (pr or {}).get("body") or ""
        branch = e.get("branch") or ""
        parts += [
            f"### {lid} — PR #{num} {e.get('pr')}",
            f"- Branche `{branch}` ; diff du lot : `git diff {prev_branch}..origin/{branch} -- . ':!docs/recette'` (dans le worktree, après `git fetch origin`).",
            f"- Plan : `{lot.plan if lot else '?'}` ; titre : {lot.title if lot else (pr or {}).get('title')}.",
            "- Prompt du lot (ce qui était demandé) :",
            "```text",
            (lot.prompt if lot else "(prompt introuvable)")[:6000],
            "```",
            "- Corps de la PR (ce que l'agent dit avoir fait ; cases de recette incluses) :",
            "```md",
            body[:8000],
            "```",
        ]
        caps = [str(p) for p in sorted((review_dir / f"pr-{num}").glob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png")] if num else []
        parts.append("- Captures de l'agent (à ouvrir avec l'outil de lecture d'image) : " + (", ".join(f"`{c}`" for c in caps) if caps else "aucune téléchargée"))
        parts.append("")
        prev_branch = f"origin/{branch}" if branch else prev_branch
    parts += [
        "## Ce que tu produis",
        "",
        f"1. Pour CHAQUE PR : écris le commentaire de revue dans `{review_dir}/comment-<numéro>.md` en suivant exactement ce gabarit :",
        "```",
        REVIEW_TEMPLATE.format(lot="<id>", model=model),
        "```",
        f"   puis poste-le : `python3 {HERE / 'post_pr_comment.py'} <numéro> {review_dir}/comment-<numéro>.md`. Un seul commentaire par PR. Français, court, précis (fichier:ligne). "
        "Ne coche AUCUNE case dans la PR : les cases sont au porteur.",
        "",
        f"2. Si au moins une PR a le verdict « MERGER APRÈS CORRECTION » ou « NE PAS MERGER » : ajoute à la fin de `{QUEUE_MD}` (crée-le s'il manque) un lot correctif par groupe de défauts, "
        "au format EXACT lu par run_lots.py — une balise puis un bloc text :",
        "```",
        '<!-- LOT id="RC<n>" title="<titre court>" plan="<plan du lot corrigé>" size="S" deps="<id du lot corrigé>" -->',
        "```text",
        "Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis <plan> et le prompt du lot <id> (docs/LOTS_ORDRE_ET_PROMPTS.md). Tu travailles dans naviguide-simulator/.",
        "",
        "Lot RC<n> — <titre>.",
        "Objectif : <ce que le porteur verra ou ne verra plus>.",
        "Constat de la revue de nuit : <fichier:ligne, ce qui manque ou est faux>.",
        "Fichiers à ouvrir (seulement) : <≤ 6 fichiers, App.jsx / MapSceneController.js par rg -n + Read offset/limit>.",
        "Étapes : 1) … 2) …",
        "Tests : <tests existants à faire passer + 1 test par comportement corrigé>. npm test, pytest -q, npx vite build.",
        "Recette (visuelle, par écran) : <ouvre …, clique …, tu dois voir …>.",
        "Branche fix/lot-rc<n>-<slug> depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.",
        "Interdits : retirer une surface visible ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.",
        "```",
        "   Numérote à la suite des RC déjà présents dans le fichier. Taille S ou M, ≤ 400 lignes de diff. Pas de lot pour un défaut qu'un lot à venir du programme corrigera (dis-le dans le verdict). "
        "Pas de lot « cosmétique » sans constat précis. S'il n'y a rien à corriger, n'écris rien dans queue.md.",
        "",
        f"3. Termine par un résumé de 5 lignes maximum sur la sortie standard : verdict par PR, lots RC ajoutés (ids). Écris aussi ce résumé dans `{review_dir}/summary.md`.",
        "",
        "Interdits absolus : git commit / push / merge ; modifier docs/ ou le code ; inventer un chiffre ; cocher une case de PR ; poster plus d'un commentaire par PR.",
    ]
    return "\n".join(parts)


def run_review(ids: list[str], *, model: str = DEFAULT_REVIEW_MODEL, dry_run: bool = False, timeout_h: float = 1.0) -> dict:
    state = rl.State.load()
    ids = [i for i in ids if i in state.done]
    if not ids:
        rl.log("revue de nuit : aucun lot à relire")
        return {"lots": [], "ok": False}
    stamp = time.strftime("%Y%m%d-%H%M")
    review_dir = REVIEW_DIR / stamp
    review_dir.mkdir(parents=True, exist_ok=True)
    http = rl.Http(None, rl.github_token_from_git())
    # Captures des agents, téléchargées pour que le réviseur les regarde.
    tok = rc.token()
    for lid in ids:
        num = rl.pr_number((state.done.get(lid) or {}).get("pr"))
        if not num:
            continue
        try:
            pr = rl.fetch_pr(http, rl.DEFAULT_REPO, num) or {}
            for k, url in enumerate(rc.agent_captures(pr.get("body") or "", (pr.get("head") or {}).get("ref") or ""), 1):
                rc.download(url, review_dir / f"pr-{num}" / f"agent-{k}-{Path(url).name}", tok)
        except Exception as e:  # les captures sont un plus, jamais bloquantes
            rl.log(f"    captures #{num} : {e}")
    if dry_run:   # aucun effet de bord : pas de worktree, pas d'agent
        prompt = build_prompt(state, ids, rl.WORKTREES / "review", review_dir, model, http)
        (review_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        print(prompt)
        return {"lots": ids, "ok": True, "dry_run": True}
    wt = rl.prepare_worktree(rl.Lot("review", "réviseur de nuit", "", "", [], ""), state.last_branch or "main")
    rl.sh(["git", "fetch", "-q", "origin"], cwd=wt, check=False, timeout=120)
    prompt = build_prompt(state, ids, wt, review_dir, model, http)
    (review_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    rl.log(f"revue de nuit : {ids} — agent {model} dans {wt}")
    status, result = rl.run_agent_cli(wt, prompt, model, int(timeout_h * 3600))
    rl.log(f"    réviseur : {status}")
    for ln in (result or "").strip().splitlines()[-6:]:
        rl.log(f"    {ln}")
    # Garde-fou : le réviseur ne doit avoir rien commité.
    ahead = rl.sh(["git", "rev-list", "--count", f"origin/{state.last_branch}..HEAD"], cwd=wt, check=False).stdout.strip() if state.last_branch != "main" else "0"
    if ahead not in ("", "0"):
        rl.log(f"    !! le réviseur a commité {ahead} commit(s) dans son worktree : ignorés (rien n'est poussé)")
    queued = [l.id for l in (rl.parse_lots_text(QUEUE_MD.read_text(encoding="utf-8")) if QUEUE_MD.exists() else []) if l.id not in state.done]
    state = rl.State.load()  # relu : run_lots a pu écrire entre-temps
    state.extra.setdefault("reviews", []).append({"at": stamp, "lots": ids, "model": model, "status": status, "queued": queued, "dir": str(review_dir)})
    state.save()
    return {"lots": ids, "ok": status == "FINISHED", "queued": queued, "dir": str(review_dir)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lots", nargs="+", help="identifiants des lots à relire")
    ap.add_argument("--since-last", action="store_true", help="tous les lots FINISHED non encore relus")
    ap.add_argument("--model", default=DEFAULT_REVIEW_MODEL)
    ap.add_argument("--timeout-hours", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    state = rl.State.load()
    ids = args.lots or (lots_since_last_review(state) if args.since_last else [])
    if not ids:
        sys.exit("Rien à relire : --lots … ou --since-last.")
    out = run_review(ids, model=args.model, dry_run=args.dry_run, timeout_h=args.timeout_hours)
    if not args.dry_run:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

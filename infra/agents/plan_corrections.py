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

Usage :
    python3 infra/agents/plan_corrections.py                       # PR de state.json, modèle Fable
    python3 infra/agents/plan_corrections.py --prs 250 251 252     # PR précises
    python3 infra/agents/plan_corrections.py --prefix RB           # préfixe des nouveaux lots (défaut : premier libre RB, RD, RE…)
    python3 infra/agents/plan_corrections.py --dry-run             # affiche le prompt
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
import run_lots as rl  # noqa: E402
import review_collect as rc  # noqa: E402

DEFAULT_MODEL = os.environ.get("BIM_CORRECTOR_MODEL", "claude-fable-5-thinking-xhigh")
USED_PREFIXES_RE = re.compile(r'<!--\s*LOT\s+id="([A-Z]+)\d')


def next_prefix(prompts_md: str) -> str:
    used = set(USED_PREFIXES_RE.findall(prompts_md))
    for letter in "BDEFHJKMPQSTVXYZ":
        cand = "R" + letter
        if cand not in used:
            return cand
    return "RZ"


def then_until() -> str | None:
    """BIM_THEN_UNTIL=D0 (environnement ou ~/.config/naviguide/simulator.env) : après les corrections,
    la nuit enchaîne le programme jusqu'à ce lot — la ligne LOTS du GO couvre alors RB1 … D0."""
    return os.environ.get("BIM_THEN_UNTIL") or rl._env_file_values().get("BIM_THEN_UNTIL") or None


def build_prompt(review: dict, wt: Path, date: str, prefix: str, model: str, night: list[dict]) -> str:
    md_path = review.get("md")
    json_path = review.get("json")
    imgs = [im["path"] for p in review["prs"] for im in p.get("local_images", [])]
    kos = sum(len(p.get("ko") or []) for p in review["prs"])
    ticked = sum(p.get("ok", 0) for p in review["prs"])
    total = sum(len(p.get("items") or []) for p in review["prs"])
    parts = [
        "Tu es le correcteur du matin de la pile de PR du simulateur NAVIGUIDE (Berry-Mappemonde/Blue-Intelligence). Le porteur a recetté dans Chrome : "
        f"il a coché {ticked} items sur {total} et écrit {kos} commentaire(s) KO. Ta mission : transformer sa revue en un plan de corrections et en lots "
        "prêts à être enchaînés par infra/agents/run_lots.py, sur une branche docs, en PR. Tu ne touches PAS au code applicatif, tu ne merges rien.",
        "",
        f"Environnement : worktree `{wt}` sur `main` à jour (HEAD détaché) : `git checkout -b docs/plan-corrections-{date}` d'abord. Bibliothèque : "
        "`python3 infra/agents/open_pr.py <branche> main \"<titre FR — EN>\" <fichier-corps.md>` pour ouvrir la PR.",
        "",
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
        f"1. `docs/PLAN_CORRECTIONS_{date}.md` : § 0 rappels ; § 1 revue par PR (OK / KO du porteur, verdict du réviseur de nuit) ; § 2 revue générale ; "
        "§ 3 ce qui est reporté et pourquoi (fondu dans quel lot à venir) ; § 4 les lots correctifs, chacun avec : cause racine (fichier:ligne — lis le code sur main, "
        "ne devine pas), fichiers à ouvrir (≤ 6, App.jsx / MapSceneController.js par rg -n), étapes, tests, recette VISUELLE par écran ; § 5 ordre et pile. Français.",
        f"2. `docs/LOTS_ORDRE_ET_PROMPTS.md` : (a) une ligne de tableau par lot {prefix}<n> après la dernière ligne ; (b) les balises `<!-- LOT id=\"{prefix}<n>\" title=\"…\" plan=\"docs/PLAN_CORRECTIONS_{date}.md\" size=\"S|M\" deps=\"…\" -->` "
        "suivies du bloc ```text``` au format exact des lots existants (lis-en deux avant d'écrire), AVANT la section « ## 3. Enchaîner » ; (c) les compléments fondus dans les lots à venir "
        "(une ligne « Constat de la revue du <date> : … » + l'étape, dans le prompt du lot concerné, sans changer son id ni sa balise).",
        f"3. Vérifie : `python3 infra/agents/run_lots.py --dry-run --from {prefix}1 --until {prefix}<dernier>` liste tes lots.",
        f"4. Commit conventionnel (`docs: corrections de la revue du {date} …`), `git push -u origin docs/plan-corrections-{date}`, puis la PR avec open_pr.py. "
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


def run(prs: list[tuple[str, int]], *, model: str = DEFAULT_MODEL, prefix: str | None = None, dry_run: bool = False, timeout_h: float = 1.5) -> dict:
    state = rl.State.load()
    date = time.strftime("%Y-%m-%d")
    review = rc.collect(prs, rl.STATE_DIR, images=True)
    night = list(state.extra.get("reviews") or [])
    if review.get("global_file"):
        rl.log(f"revue globale du porteur : {len(review['global_file'])} caractères dans REVUE_GLOBALE.md")
    prefix = prefix or next_prefix(rl.PROMPTS_MD.read_text(encoding="utf-8"))
    if dry_run:
        prompt = build_prompt(review, rl.WORKTREES / "corrector", date, prefix, model, night)
        print(prompt)
        return {"ok": True, "dry_run": True, "prefix": prefix}
    wt = rl.prepare_worktree(rl.Lot("corrector", "correcteur du matin", "", "", [], ""), "main")
    prompt = build_prompt(review, wt, date, prefix, model, night)
    (rl.STATE_DIR / f"corrector-prompt-{date}.md").write_text(prompt, encoding="utf-8")
    rl.log(f"correcteur du matin : {len(prs)} PR, préfixe {prefix}, agent {model} dans {wt}")
    status, result = rl.run_agent_cli(wt, prompt, model, int(timeout_h * 3600))
    rl.log(f"    correcteur : {status}")
    for ln in (result or "").strip().splitlines()[-6:]:
        rl.log(f"    {ln}")
    branch = rl.local_branch(wt)
    go_pr = None
    if branch and rl.ensure_pushed(wt, branch):
        http = rl.Http(None, rl.github_token_from_git())
        pr = rl.find_pr(http, rl.DEFAULT_REPO, branch)
        if pr:
            go_pr = pr["number"]
            rl.log(f"    PR GO #{go_pr} {pr['html_url']} — à merger par le porteur pour lancer le batch suivant")
        else:
            rl.log("    la PR GO n'a pas été ouverte par l'agent : `python3 infra/agents/open_pr.py " + branch + " main \"docs: corrections\" <corps.md>`")
    archived = rc.archive_global_file(date) if status == "FINISHED" else None
    if archived:
        rl.log(f"revue globale archivée : {archived} (fichier remis à zéro)")
    state = rl.State.load()
    state.extra.setdefault("corrections", []).append({"at": date, "prs": [n for _, n in prs], "model": model, "status": status, "branch": branch, "go_pr": go_pr, "prefix": prefix, "global_archived": archived})
    state.save()
    return {"ok": status == "FINISHED", "branch": branch, "go_pr": go_pr, "prefix": prefix}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prs", nargs="+", type=int, help="numéros de PR (défaut : PR FINISHED de state.json)")
    ap.add_argument("--prefix", help="préfixe des nouveaux lots (défaut : premier libre)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--timeout-hours", type=float, default=1.5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    prs = [("", n) for n in args.prs] if args.prs else rc.prs_from_state()
    if not prs:
        sys.exit("Aucune PR : --prs … ou un state.json avec des lots FINISHED.")
    out = run(prs, model=args.model, prefix=args.prefix, dry_run=args.dry_run, timeout_h=args.timeout_hours)
    if not args.dry_run:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

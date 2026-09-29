#!/usr/bin/env python3
"""Devpost — l'agent Fable entre Grok Bot et le brouillon (porteur, 29 sept.).

Chaîne :  Grok Bot relève le formulaire (📋, issue #432)  →  CE SCRIPT lance un agent Fable (CLI Cursor
local) qui propose les réponses (✍️)  →  Grok Bot recopie dans le brouillon (📝)  →  le porteur vérifie et
soumet lui-même.

    python3 infra/agents/devpost_answers.py --wake-scrape   # webhook → Grok Bot, tâche A (relever)
    python3 infra/agents/devpost_answers.py                 # lit le dernier 📋, lance Fable, poste ✍️ + PR docs
    python3 infra/agents/devpost_answers.py --wake-fill     # webhook → Grok Bot, tâche B (remplir le brouillon)
    python3 infra/agents/devpost_answers.py --dry-run       # affiche le prompt Fable, ne lance rien

Ce que Fable doit produire (docs/DEVPOST_REPONSES_<date>.md + commentaire ✍️) : langage simple avant
technique ; pour chaque choix multiple l'option recopiée MOT POUR MOT ; une table de conformité aux règles
avec preuve (fichier:ligne ou URL) ; une analyse des critères de jugement ; rien d'annoncé qui ne tourne pas
en production le jour de la soumission. Aucun secret ne transite (le bot n'a que le connecteur GitHub).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_lots as rl  # noqa: E402

ISSUE = 432
MODEL = "claude-fable-5-thinking-xhigh"
FORM_MARK = "📋 Formulaire Devpost relevé"
ANSWERS_MARK = "✍️ Réponses proposées"
FILL_MARK = "📝 Brouillon rempli"
SUBMISSION_DOC = "docs/HACKATHON_DEVPOST_SOUMISSION.md"


def repo_path() -> str:
    return rl.owner_repo(rl.DEFAULT_REPO)


def issue_comments(http: rl.Http) -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        batch = http.github(f"/repos/{repo_path()}/issues/{ISSUE}/comments?per_page=100&page={page}") or []
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def last_comment(comments: list[dict], mark: str) -> dict | None:
    hits = [c for c in comments if mark in (c.get("body") or "")]
    return hits[-1] if hits else None


def json_block(body: str) -> dict | None:
    m = re.search(r"```json\s*\n(.*?)\n```", body or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def wake(kind: str) -> bool:
    """Réveil du bot : même webhook que la pré-revue, `event` devpost_scrape | devpost_fill (routine GROK_BOT_DEVPOST.md)."""
    hook, headers = rl.webhook_settings()
    if not hook:
        print("BIM_BOT_WEBHOOK absent : coller la routine et l'URL du webhook (voir GROK_BOT_ROUTINE.md)")
        return False
    url = f"{rl.DEFAULT_REPO}/issues/{ISSUE}"
    text = {"devpost_scrape": "Relever le formulaire Devpost, les règles et les critères (tâche A)",
            "devpost_fill": "Recopier les réponses ✍️ dans le brouillon Devpost, sans soumettre (tâche B)"}[kind]
    body = json.dumps({"event": kind, "repo": repo_path(), "pr": ISSUE, "url": url, "text": f"{text} — issue #{ISSUE} : {url}"}).encode()
    req = urllib.request.Request(hook, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Grok Bot réveillé ({kind}, HTTP {resp.status}) — il postera sur l'issue #{ISSUE}")
            return True
    except Exception as exc:  # pas de secret dans le message
        print(f"webhook Grok Bot : {type(exc).__name__} — vérifier la routine et l'URL")
        return False


def code_share(since: str = "2026-08-26") -> dict:
    """Part du code écrite depuis le début du hackathon (devpost_code_share.py) — exigée par le porteur dans la
    réponse « existing project : how significantly updated » (29 sept.)."""
    import subprocess  # noqa: PLC0415
    p = subprocess.run([sys.executable, str(HERE / "devpost_code_share.py"), "--since", since, "--json"],
                       cwd=str(rl.ROOT), capture_output=True, text=True, check=False, timeout=900)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"error": (p.stderr or p.stdout)[:200]}


def build_prompt(form_comment: dict, date_tag: str, share: dict | None = None) -> str:
    body = form_comment.get("body") or ""
    data = json_block(body)
    n_fields = len((data or {}).get("fields") or [])
    share = share or {}
    share_txt = share.get("sentenceEn") or "(mesure indisponible : lance python3 infra/agents/devpost_code_share.py et recopie la phrase)"
    return f"""Tu es l'agent Fable de la soumission Devpost de NAVIGUIDE (dépôt Berry-Mappemonde/Blue-Intelligence, hackathon Nebius × NVIDIA Global AI Hackathon). Tu travailles dans ce worktree (main à jour). Tu ne touches à AUCUN code : tu écris un document et un commentaire.

Lis d'abord, en entier : {SUBMISSION_DOC} (la soumission v1.0 du 20 sept. : textes déjà écrits, réponses déjà tranchées, liste de contrôle § 0, critères § 5), README.md, docs/ESPRIT_DE_L_APPLICATION.md, docs/PLAN_DEUX_MODES_2026-09-29.md (l'application a maintenant deux modes : Suivre et Tracer — le mot « Simulation » ne doit plus apparaître), infra/vps/README.md § politique LLM (depuis le 29 sept. : mode on-demand, juge Ultra et veille Tavily coupés par défaut).

Puis lis le relevé de Grok Bot ci-dessous : le formulaire Devpost tel qu'il est AUJOURD'HUI ({n_fields} champs relevés), les règles, les critères de jugement. C'est la seule source pour les libellés, les options et les limites de caractères : ne suppose aucun champ qui n'y est pas.

=== RELEVÉ GROK BOT (commentaire {form_comment.get('html_url')}) ===
{body}
=== FIN DU RELEVÉ ===

Ta mission, dans cet ordre :

1) RÈGLES ET CONFORMITÉ. Pour chaque règle relevée (éligibilité, exigences techniques, livrables, dates, vidéo, licence, dépôt, langue…), dis si le projet est conforme AUJOURD'HUI, avec une preuve vérifiable : un fichier et une ligne du dépôt (ex. server/story_cascade.py : l'appel Token Factory), une URL publique (le site, le dépôt, la licence), ou « non vérifié ». Cherche vraiment dans le code (rg). Points sensibles : l'appel runtime à Nebius Token Factory avec un modèle NVIDIA open source doit tourner en production ; Tavily et le juge Ultra sont COUPÉS par défaut depuis le 29 sept. (NAVIGUIDE_TRUTH_JUDGE=0, NAVIGUIDE_TAVILY_WATCH=0) — si la soumission dit « Yes » à Tavily ou montre un badge « Verified · Tavily », c'est faux le jour de la soumission : dis-le, propose la réponse honnête, et note ce qu'il faudrait réactiver (et son coût) si le porteur veut cocher « Yes ». Toute non-conformité ou promesse non tenue va dans une section « À régler avant de soumettre », en tête du document.

2) CRITÈRES DE JUGEMENT. Pour chaque critère (avec sa pondération si donnée) : ce que le projet montre, où le juge le verra (écran, URL, minute de la vidéo), la faiblesse honnête, et une phrase que la soumission doit contenir pour marquer le point.

3) RÉPONSES. Pour CHAQUE champ du relevé, propose la valeur finale, en anglais, en respectant la limite de caractères (compte-les et écris le nombre). Le champ « existing project : how significantly was it updated since August 26, 2026 » (ou son libellé exact dans le relevé) COMMENCE par le chiffre mesuré dans git, tel quel, puis raconte ce qui a été construit — porteur, 29 sept. :
   « {share_txt} »
   (mesure : python3 infra/agents/devpost_code_share.py ; tu peux la relancer, jamais l'arrondir vers le haut ni la reformuler en promesse). Langage simple d'abord : une personne du marketing ou de l'UX doit comprendre la première phrase ; le technique vient ensuite, jamais de jargon interne (« perles », « sac », « lot RG6 ») sans le dire en clair. Pour chaque case à cocher, menu déroulant ou choix multiple : recopie l'option choisie MOT POUR MOT depuis la liste relevée (jamais une reformulation), avec une ligne de raison ; si aucune option ne convient, dis-le. Repars des textes de {SUBMISSION_DOC} quand ils sont encore vrais ; corrige ce qui a changé (deux modes Suivre / Tracer ; film narré et ancré ; ce qui est coupé ; ce qui est nouveau depuis le 20 sept. — lis git log --since=2026-09-20 --oneline | head -80 et les PR mergées). Aucun chiffre que tu ne peux pas vérifier (notes 1–10 : propose une note ET la raison, marque-la « à confirmer par le porteur »).

4) LIVRABLES.
   a) Écris docs/DEVPOST_REPONSES_{date_tag}.md avec, dans l'ordre : « À régler avant de soumettre » ; conformité (table règle → état → preuve) ; critères (table) ; réponses champ par champ (onglet, libellé, valeur, nombre de caractères / option choisie + raison) ; « Ce que je n'ai pas pu vérifier ». Français pour les consignes, anglais pour les valeurs.
   b) Termine ce document par un bloc ```json au schéma : {{"kind": "devpost_answers", "basedOn": "<url du commentaire 📋>", "answers": [{{"tab": "…", "label": "<libellé exact>", "type": "…", "value": "<texte>" }} ou {{"tab": "…", "label": "…", "type": "select|checkbox", "selected": ["<option mot pour mot>"] }}], "blocking": ["…"]}} — c'est ce bloc que Grok Bot recopiera dans le brouillon : les libellés doivent être ceux du relevé, au caractère près.
   c) Crée la branche docs/devpost-reponses-{date_tag} depuis HEAD, commite le document, pousse, ouvre une PR vers main (titre « docs : réponses Devpost proposées — {date_tag} », corps = la section « À régler avant de soumettre » + le lien du commentaire 📋), avec `gh pr create`.
   d) Poste UN commentaire sur l'issue #{ISSUE} (gh issue comment {ISSUE} --body-file …) intitulé « {ANSWERS_MARK} — {date_tag} » : la section « À régler avant de soumettre », la table de conformité, puis le bloc ```json complet (le même que dans le document), puis le lien de la PR.

Interdits : modifier du code ou un autre document que le tien ; inventer une option, un chiffre, une URL ; annoncer une fonctionnalité qui ne tourne pas en production ; un secret ou un identifiant ; une vidéo. Ne rejoue aucune suite de tests. Décide seul et note-le. Fin : PR, commentaire ✍️, et dans ta dernière réponse la liste des points bloquants."""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wake-scrape", action="store_true", help="réveiller Grok Bot pour relever le formulaire (tâche A)")
    ap.add_argument("--wake-fill", action="store_true", help="réveiller Grok Bot pour recopier les réponses (tâche B)")
    ap.add_argument("--dry-run", action="store_true", help="afficher le prompt Fable sans lancer d'agent")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--timeout-hours", type=float, default=1.5)
    args = ap.parse_args()

    if args.wake_scrape:
        sys.exit(0 if wake("devpost_scrape") else 1)
    if args.wake_fill:
        sys.exit(0 if wake("devpost_fill") else 1)

    http = rl.Http(None, rl.github_token_from_git())
    comments = issue_comments(http)
    form = last_comment(comments, FORM_MARK)
    if not form:
        sys.exit(f"Aucun commentaire « {FORM_MARK} » sur l'issue #{ISSUE} : lancer d'abord --wake-scrape (ou demander au bot).")
    answers = last_comment(comments, ANSWERS_MARK)
    if answers and answers.get("created_at", "") > form.get("created_at", ""):
        print(f"Des réponses ✍️ ({answers.get('html_url')}) sont déjà plus récentes que le relevé 📋 : relancer --wake-scrape pour un nouveau relevé, ou --wake-fill pour remplir.")
    date_tag = time.strftime("%Y-%m-%d")
    share = code_share()
    if share.get("sentenceEn"):
        print("Part du code depuis le 26 août :", share["sentenceEn"])
    prompt = build_prompt(form, date_tag, share)
    if args.dry_run:
        print(prompt)
        return
    wt = rl.prepare_worktree(rl.Lot("devpost", "réponses Devpost", "", "", [], ""), "main")
    rl.log(f"[devpost] agent {args.model} dans {wt} — relevé {form.get('html_url')}")
    status, result = rl.run_agent_cli(wt, prompt, args.model, int(args.timeout_hours * 3600))
    rl.log(f"[devpost] agent : {status}")
    for ln in (result or "").strip().splitlines()[-12:]:
        rl.log(f"    {ln[:200]}")
    if status != "FINISHED":
        sys.exit(2)


if __name__ == "__main__":
    main()

# Workflow industriel — lots la nuit, review le matin, soumission chaque semaine

Version **1.0** — 20 septembre 2026. Ce que la première nuit de lots a appris
(11 PR en 3 h, une cascade de CI rouge évitée, un incident prod détecté), mis
en cycle, avec le porteur **dans la boucle** aux endroits qui comptent, et
un calendrier tenu par trois dates : **28 septembre** (première soumission
Devpost, départ pour Toronto le 29), **9 octobre** (renouvellement Cursor :
crédits), **30 octobre 10:00 PT** (clôture) — une mise à jour de la
soumission **par semaine** entre le 9 et le 30.

## 1. Le cycle (une itération = une nuit + une matinée) — la boucle W1–W4 (21 sept.)

```
 soir                nuit                                        matin                              journée
 ─────               ───────────────────────────────────         ─────────────────────────────      ─────────────────
 GO (merge d'une  →  run_lots.py : un agent Grok par lot,     →  1. le porteur recette dans      →  merge de la pile
 PR docs « plan »)   PR bilingue à cases à cocher, CI ;            Chrome, coche les cases des       (la PR de tête suffit)
                     poste de recette rebâti après chaque lot ;    PR, écrit « KO : … » ;         →  loop.py : collecte
                     toutes les X PR, le RÉVISEUR DE NUIT           merge la pile                     (review_collect) +
                     (Fable) relit la tranche, commente chaque                                        CORRECTEUR (Fable) →
                     PR, met en file des lots RC exécutés                                             PR « GO » (plan +
                     en bout de pile la même nuit                                                     lots RB…, ou fondus
                                                                                                      dans les lots à venir)
                                                                                                   →  merge du GO = nuit suivante
```

Deux moments de revue, pas un : **la nuit**, un agent fort relit toutes les X PR
(`--review-every 4`) et corrige dans la foulée grâce aux agents Grok qui
travaillent encore ; **le matin**, le porteur voit tout, coche, et le
correcteur transforme sa revue en lots. Les seuls gestes humains : cocher,
merger la pile, merger le GO. Tout le programme est **pré-rédigé** dans
`LOTS_ORDRE_ET_PROMPTS.md` pour que le correcteur puisse fondre une correction
dans un lot à venir au lieu d'en ouvrir un.

Outils (`infra/agents/`) : `run_lots.py` (`--review-every`, poste par lot),
`open_pr.py` (cases à cocher, `--retrofit`), `review_collect.py` (cases, KO,
images), `review_agent.py` (réviseur de nuit → commentaires + `queue.md`),
`plan_corrections.py` (correcteur du matin → PR GO), `loop.py` (enchaînement),
`post_pr_comment.py`.

### 1.1 Soir — choisir

Le porteur choisit la tranche (`--from … --until …`, `--skip` pour ce qui est
mergé) dans `LOTS_ORDRE_ET_PROMPTS.md` et lance
`caffeinate -i python3 infra/agents/run_lots.py …`. Rien d'autre.

### 1.2 Nuit — produire

`run_lots.py` : pile linéaire, un agent local par lot, relances sur échec
(nouveaux échecs seulement), PR ouvertes vers `main`. Après la PR #211 :
journaux CI lus, échecs hérités ignorés, règle « spec sans API », reprise
qui adopte.

### 1.3 Matin — revue automatique (nouveau lot **W1**)

Avant que le porteur ouvre quoi que ce soit, un **agent de revue** (Cursor,
modèle **Claude Fable 5.1 Max, 1 M de contexte** — le seul qui lit d'un coup
le diff, la transcription et le plan) passe sur chaque PR de la nuit et
produit **un commentaire par PR** :

```
Lot <X> — revue automatique
1. Conformité au lot : chaque étape du prompt → faite / partielle / non faite (citer fichier:ligne).
2. Libertés prises : décisions de l'agent qui ne sont pas dans le lot (rubrique « Décisions prises seul » de la PR
   + ce que la transcription montre et que la PR ne dit pas). Pour chacune : acceptable / à discuter / à défaire.
3. Plancher main : surfaces retirées, cachées, conditionnées ? (git diff main -- src/App.jsx src/components src/map)
4. Chiffres LLM, secrets, tests affaiblis, data-testid renommés, fichiers hors liste ouverts.
5. Prérequis pour recetter : clés, variables, données, redémarrages (voir § 3).
6. Verdict : MERGER / MERGER APRÈS CORRECTION (liste) / NE PAS MERGER (pourquoi).
```

Entrées : le diff de la PR, le corps de la PR, le texte du lot, `REGLES_WORKFLOW_AGENT.md`,
et la **transcription** de l'agent (`~/.cursor/chats/<ws>/<session>/store.db`,
exportée en texte par `infra/agents/export_transcript.py` — à écrire dans W1).
Sortie : commentaire GitHub + une ligne dans `infra/agents/review.md`
(tableau de la nuit). Exécution : `python3 infra/agents/review_lots.py --night <date>`
(local, CLI Cursor, modèle `claude-fable-5-1-max`), ou une **Automation**
Cursor déclenchée par « Pull request opened » (cloud, voir § 2).

### 1.3 bis Nuit — le réviseur (agent fort, toutes les X PR)

`run_lots.py --review-every 4` : après chaque tranche de 4 PR, `review_agent.py`
lance un agent **Claude Fable** (CLI local, `claude-fable-5-thinking-xhigh`) dans
un worktree sur la **tête de pile** — il voit donc aussi ce que les lots
suivants ont déjà fait. Il relit diff, corps de PR, captures, prompt du lot,
plan et règles ; poste **un commentaire de revue par PR** (gabarit § 1.3 :
conformité, libertés, plancher `main`, chiffres LLM / secrets / tests, recette
visuelle et bilingue, prérequis, **verdict**) ; et, s'il faut corriger, écrit
des lots `RC…` dans `infra/agents/queue.md` que `run_lots.py` relit entre deux
lots et exécute **en bout de pile, la même nuit**. Il ne commite ni ne pousse
de code, ne coche aucune case (les cases sont au porteur), ne merge rien.

### 1.4 Matin — revue du porteur (humain dans la boucle)

Le poste est **déjà prêt** quand le porteur arrive (lot **W0**, 21 sept.) et il
l'a été **après chaque lot** (lot W1) : `run_lots.py` a fait le build de prod de
la tête de pile, chargé les clés (`~/.config/naviguide/simulator.env`), lancé
l'API et l'interface du même checkout, ouvert Chrome sur
`http://localhost:5174` et `infra/agents/RECETTE_DU_BATCH.md` (régénéré à
chaque lot, avec les cases déjà cochées et les KO déjà écrits). S'il ne l'est
pas : `python3 infra/agents/run_lots.py --recette`.

Trois passes, dans l'ordre, **par écran** (Suivre, Simulation, Tracer ma route,
Revoir l'expédition, panneau droit) et non par PR :

1. **Regarder** : `RECETTE_DU_BATCH.md` § 1 dit, écran par écran, quoi cliquer
   et ce qu'on doit voir. Le porteur ne lance rien d'autre que Chrome.
2. **Cocher** dans chaque PR GitHub les items vus et bons ; pour un item qui ne
   va pas, laisser la case vide et commenter « **KO :** écran, ce que je vois,
   ce que je voulais » (capture bienvenue). Lire le commentaire du réviseur de
   nuit et les « Décisions prises seules » (§ 5 du fichier) : garder / défaire.
3. **Merger** (§ 6 du fichier) : pile linéaire → merger la **dernière** PR
   suffit, GitHub ferme les autres ; puis celles qui ont des commits propres.
   Merge commit, jamais squash. Ce merge est le signal : `loop.py` collecte la
   revue, lance le **correcteur du matin** (`plan_corrections.py`, Fable) qui
   écrit le plan de corrections et ses lots — ou les **fond dans les lots à
   venir** du programme — et ouvre la PR « GO ». Merger le GO lance la nuit
   suivante. On ne corrige pas le matin à la main.

### 1.5 Journée — livrer

Merge → `deploy.yml` déploie (BI, NAVIGUIDE, simulateur) → **prérequis**
posés sur le VPS (§ 3) → recette en prod (les trois parcours fixes +
le film) → le vendredi : mise à jour de la soumission Devpost (§ 4).

## 2. Les outils Cursor qui servent (et ceux qui ne servent pas)

Lu dans la documentation Cursor (20 sept.) :

| Outil | Ce que c'est | Pour nous |
|---|---|---|
| **CLI `agent -p`** (local) | agent headless sur le Mac, modèle du compte | **le moteur des lots** (`run_lots.py`) : environnement prêt, Grok 4.6 xhigh fast, aucune vidéo |
| **Automations** | agents **Cloud** lancés par un déclencheur : cron, PR ouverte / poussée / mergée, **CI completed**, commentaire, label, Slack, webhook ; outils : commenter la PR, demander des reviewers, PR, Slack, MCP, mémoires ; modèle au choix ; facturé en usage Cloud ; « computer use » inclus (peut produire captures/enregistrements — à **désactiver dans le prompt** chez nous) | utiles pour trois choses : **(a)** « PR ouverte » → revue automatique (§ 1.3) en cloud si on ne veut pas occuper le Mac ; **(b)** « CI completed = failure » → agent de correction ; **(c)** cron hebdomadaire (jeudi soir) → brouillon de mise à jour Devpost (README, textes, captures) en PR. Réserve : les agents Cloud tournent avec les modèles Cursor et facturent l'usage Cloud ; la règle `pas-de-verification-video` doit être dans le prompt |
| **Bugbot / Security Agents / PR Routing** (Automations gérées par Cursor) | revue de bugs, scan sécurité, routage | Bugbot sur les lots M/L en complément de notre revue ; Security Agents avant chaque soumission |
| **Grok Bot** (bêta, inclus Cursor Ultra) | des « coéquipiers » IA sur un **ordinateur cloud persistant** (navigateur, fichiers, terminal), qui se connectent aux outils comme un humain (computer use), plusieurs bots en parallèle, routines enregistrées et rejouées, approbations quand il faut | **pas pour le code** (nos lots ont besoin de l'environnement du dépôt et de Grok 4.6). Utile pour les **tâches hors dépôt** : remplir et mettre à jour le formulaire Devpost chaque semaine, surveiller la console Nebius (crédits, expiration) et la boîte mail du hackathon, poster les mises à jour. À essayer sur une routine simple d'abord (« vérifier le solde Token Factory et me le dire ») |
| **Cloud Agents API** (`run_lots.py --runtime cloud`) | même chose que le CLI, sur une machine Cursor | secours si le Mac n'est pas disponible |

## 3. Prérequis avant la revue et après le merge (ce que le porteur pose)

Ce que les lots de cette nuit demandent pour **fonctionner** (sans quoi la
recette échoue « honnêtement » : récit en `règles`, chat en `failed`, juge en
`unverifiable`) :

**Un seul fichier, même chemin sur le Mac et sur le VPS :
`~/.config/naviguide/simulator.env`** (une ligne `NOM=valeur` par clé, jamais
dans le dépôt). Sur le VPS c'est l'`EnvironmentFile` du service
`naviguide-simulator` ; sur le Mac, `ensure-dev.sh` (donc `dev-mac.sh`, les
hooks Cursor et le poste de recette) le charge dans l'environnement de l'API.
Posées le 21 sept. : `NEBIUS_API_KEY`, `TAVILY_API_KEY` (VPS et Mac).

| Lot | À poser où | Quoi |
|---|---|---|
| L1, L2, L6 | `~/.config/naviguide/simulator.env` (Mac **et** VPS) | `NEBIUS_API_KEY=…` (Token Factory) ; option `NAVIGUIDE_LLM_PROVIDERS=tokenfactory,nim,openrouter,claude` (défaut désormais) ; `NAVIGUIDE_TF_MODEL_FAST/WRITE/JUDGE` si le catalogue change ; plafonds `NAVIGUIDE_LLM_DAILY_TOKENS_*` |
| L1 (repli) | idem | `NVIDIA_API_KEY` (NIM, déjà), `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` (déjà) |
| L3, L4 | idem | `TAVILY_API_KEY=…` (10 000 + 3 125 crédits reçus) |
| C2 | idem | `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` (déjà) ; laisser tourner le premier hindcast (≈ 40 min de tâche de fond) |
| C4/C7 | idem | `POLAR_EFFICIENCY` (défaut 0,85), `server/data/port_days.json` (livré) |
| G3 (plus tard) | VPS nginx | `/tiles/zee.pmtiles` généré (`infra/tiles/build_zee_pmtiles.sh`) |
| tous | VPS | après merge : `deploy.yml` redémarre les services ; vérifier `/ici/warm/status` → `llm.write.calls` monte quand un récit est demandé |
| BI (hotfix #221) | VPS `backend/.env` | `POE_AUTO_REFRESH` reste à 0 tant que `generate_zone_poe` n'est pas non bloquant |

Comment lire les clés déjà posées sur le VPS (Mac, Terminal — on affiche les noms, pas les valeurs) :
`ssh ubuntu@135.125.226.16 'sed -nE "s/^([A-Z_]+)=.*/\1/p" ~/.config/naviguide/simulator.env'`.
Poser une clé : `ssh ubuntu@135.125.226.16 'echo "NEBIUS_API_KEY=xxx" >> ~/.config/naviguide/simulator.env && sudo systemctl restart naviguide-simulator'`.
Vérifier qu'elle sert : `https://simulator.naviguide.fr/ici/warm/status` → `llm.lastSource` n'est plus `rules`, `llm.tavily.calls` monte.

## 4. Calendrier

| Date | Objectif | Ce qui doit être vrai |
|---|---|---|
| **21 sept. (matin)** | revue de la nuit 1 (P2 → L6), merges dans l'ordre, clés posées, hotfix #221 déployé | prod : récit signé « Nemotron 3 Super · Token Factory », film 2:30 qui se lance, bag qui se remplit |
| 21 sept. | **fait** : pile P2 → L6 mergée ; clés posées ; W0 ; batch R1 → R13 (#239–248) recetté et mergé ; batch RA1 → RA8 lancé ; boucle W1–W4 construite (PR à merger) | `RECETTE_DU_BATCH.md` régénéré à chaque lot ; PR à cases à cocher |
| 22 sept. | matin : recette RA (cocher, merger #tête), test de la boucle (`plan_corrections.py` → GO) ; nuit : **R8a–c, R9a–c** (encadré sans titre, journal → récit préchauffé) + lots RB du GO | le film raconte le journal, sans pop-up sur la carte |
| 23 sept. | matin : recette, merge, GO ; nuit : **N1–N4** (ancien NAVIGUIDE : import/export GeoJSON + KML, anti-trafic, piraterie) + corrections | Tracer ma route importe/exporte ; score anti-trafic visible |
| 24 sept. | matin : recette, merge, GO ; nuit : **R10a–d** (expert en circumnavigation) + corrections | « Ce que je changerais » conseille ; « Demander conseil » borné |
| 25 sept. | matin : recette, merge, GO ; nuit : **D0** (README, manuel, rangement docs) + **G0–G2** (globe) si tout est vert, sinon corrections | docs à jour ; première vidéo du film enregistrée |
| 26–27 sept. | gel : pas de lot risqué ; **H1** séparation des dépôts (public = simulateur seul), recette prod, Security Agents, vidéo finale | `simulator.naviguide.fr` stable 48 h |
| **28 sept.** | **première soumission Devpost** avant minuit (brouillon → Submit) ; tout ce que `HACKATHON_DEVPOST_SOUMISSION.md` § 0 coche ; crédits Token Factory +25 $ ×2 demandés | vidéo YouTube publique, dépôt public MIT, README EN, liens |
| 29 sept. – 8 oct. | Toronto ; nuits légères (G0–G2 globe, C-lots restants) uniquement si crédits ; sinon pause | rien ne casse `main` |
| **9 oct.** | renouvellement Cursor : reprise des nuits complètes | plan des 3 semaines : globe (G3–G7), L4–L6 si non faits, corrections de revue |
| 16, 23 oct. | mises à jour hebdomadaires de la soumission (vendredi) : changelog, captures, vidéo si le film a changé | chaque vendredi une version soumise |
| **30 oct. 10:00 PT** | soumission finale | tout ce qui est en prod est décrit, rien de plus |
| 1–15 déc. | jugement : l'app doit répondre, crédits Token Factory valides | clés et crédits vérifiés le 30 nov. |

## 5. Les lots « workflow » à ajouter à `LOTS_ORDRE_ET_PROMPTS.md`

- **W0 — Fin de batch = poste de recette prêt** (**fait le 21 sept.**, à la main, PR `chore/lot-w0-fin-de-batch`) : `run_lots.py --recette` / fin de batch automatique, `ensure-dev.sh --prod` (build de prod, clés, API et interface du même checkout, santé), `RECETTE_DU_BATCH.md` écran par écran + ordre des merges, règle « recette visuelle seulement » dans le préfixe de chaque prompt et dans `REGLES_WORKFLOW_AGENT.md` § 3–4, règle « rien de superflu à l'écran » § 1.
- **W1 — Recette cochable et poste par lot** (**fait le 21 sept. au soir**, PR `feat/lot-w1-w4-boucle`) : `open_pr.py` transforme la rubrique Recette en cases à cocher GitHub (`--retrofit N…` pour les PR déjà ouvertes) ; `run_lots.py` rebâtit le poste de recette après **chaque** lot (`--no-recette-each` pour l'éviter) et régénère `RECETTE_DU_BATCH.md` avec les cases cochées et les KO ; règle **PR bilingue FR / EN** dans le préfixe de chaque prompt et dans REGLES § 3.
- **W2 — Collecte de la revue** (**fait**) : `review_collect.py` lit cases, commentaires « KO : … », images du porteur et captures des agents → `review-<date>.json` + `.md`.
- **W3 — Deux agents forts** (**fait**) : `review_agent.py`, le **réviseur de nuit** (`run_lots.py --review-every 4`, modèle `claude-fable-5-thinking-xhigh`) : un commentaire de revue par PR + lots `RC…` dans `queue.md`, exécutés en bout de pile la même nuit ; `plan_corrections.py`, le **correcteur du matin** : revue humaine + programme complet → `PLAN_CORRECTIONS_<date>.md` + lots `RB…` (ou corrections fondues dans les lots à venir) → PR « GO » terminée par `LOTS: RB1 RBn`.
- **W4 — La boucle** (**fait**) : `loop.py` — batch → attente du merge de la pile → collecte + correcteur → attente du merge du GO → batch suivant ; `loop-state.json`, `--resume`, `--start-at`, `--cycles`.
- **W5 — Automations Cursor** (à faire, secours cloud) : « PR opened → revue », « CI completed failure → correction », « cron jeudi 22 h → brouillon Devpost ». Prompts avec la règle « pas de vidéo, pas de computer use ».
- **W6 — Suite e2e robuste** : `workers: 1` pour `e2e/lots`, `--repeat-each` sur la fumée, budget de temps par spec.
- **D0 — Rangement de `docs/`** : `ETAT_DES_LIEUX_DOCS.md` § 3, liens réécrits, `ARCHITECTURE.md` réécrit.

## 6. Ce qu'on a appris cette nuit (à garder)

- Un spec de lot qui dépend de l'API casse la CI de **toute la pile** : les specs de lots doivent tenir sans API (règle ajoutée) et la CI les joue en informatif (PR #209).
- Les agents disent ce qu'ils décident seuls quand on le leur demande (rubrique « Décisions prises seul ») : c'est la matière première de la revue humaine — la lire **avant** de regarder l'écran.
- Les libertés les plus fréquentes : un `data-testid` demandé qui n'existe pas (l'agent garde l'existant et ajoute un alias : bien), un fichier hors liste nécessaire (il le dit : bien), un contournement technique (`popup._biFitting`, `window.__naviguideScene` exposé en prod, garde `navigator.webdriver` dans le code produit) : **à trancher au cas par cas**.
- La CI ne détecte pas tout : F1 a rendu la barre film plus haute que ce que le lot O exigeait (109 px vs 96) — seul le porteur le voit ; la revue automatique doit comparer les recettes des lots précédents.
- La prod peut tomber pour une raison sans rapport avec les lots (auto-refresh PoE) : un `curl` de santé sur BI et sur le simulateur au début de chaque revue, et une Automation « cron toutes les 30 min → santé → Slack/mail si rouge » (W2) valent le coup.

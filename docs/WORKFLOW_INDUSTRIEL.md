# Workflow industriel — lots la nuit, review le matin, soumission chaque semaine

Version **1.0** — 20 septembre 2026. Ce que la première nuit de lots a appris
(11 PR en 3 h, une cascade de CI rouge évitée, un incident prod détecté), mis
en cycle, avec le porteur **dans la boucle** aux endroits qui comptent, et
un calendrier tenu par trois dates : **28 septembre** (première soumission
Devpost, départ pour Toronto le 29), **9 octobre** (renouvellement Cursor :
crédits), **30 octobre 10:00 PT** (clôture) — une mise à jour de la
soumission **par semaine** entre le 9 et le 30.

## 1. Le cycle (une itération = une nuit + une matinée)

```
 soir                nuit                          matin                                  journée
 ─────               ─────────────────────         ──────────────────────────────         ─────────────────
 choisir les lots →  run_lots.py (local, pile) →   1. revue automatique (agent Fable) →   merge dans l'ordre →
 (LOTS_ORDRE…)       un agent Grok/lot, PR, CI     2. revue du porteur (visuelle +         déploiement CI →
                     relances auto                    transcripts + « libertés »)          prérequis (clés) →
                                                   3. corrections rapides                  recette en prod →
                                                                                            soumission (hebdo)
```

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

### 1.4 Matin — revue du porteur (humain dans la boucle)

Trois passes, dans l'ordre, 10 minutes par lot :

1. **Lire** le commentaire de revue automatique et la rubrique « Décisions
   prises seul » de la PR. Trancher chaque liberté : garder / défaire (un
   commentaire « défaire : … » suffit, l'agent de correction s'en charge).
2. **Voir** : jouer le spec du lot (`PW_PORT=5199 npm run e2e -- e2e/lots/<lot>.spec.js`
   dans le worktree `~/bim-lots/<lot>`, avec l'API et les clés) et regarder
   les captures `docs/recette/<lot>/`. Ce que le lot dit qu'on doit voir, on
   le voit ; sinon « défaire ».
3. **Décider** : merger dans l'ordre de la pile (merge commit), ou laisser
   ouvert avec les corrections demandées (l'agent de correction = un
   `run_lots.py --only <lot> --fix` qui relance l'agent du lot avec les
   commentaires de la PR ; à écrire dans W1).

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

| Lot | À poser où | Quoi |
|---|---|---|
| L1, L2, L6 | `naviguide-simulator/server/.env` (Mac) **et** VPS (`~/blue-intelligence-map/naviguide-simulator/server/.env` ou l'env du service `naviguide-simulator`) | `NEBIUS_API_KEY=…` (Token Factory) ; option `NAVIGUIDE_LLM_PROVIDERS=tokenfactory,nim,openrouter,claude` (défaut désormais) ; `NAVIGUIDE_TF_MODEL_FAST/WRITE/JUDGE` si le catalogue change ; plafonds `NAVIGUIDE_LLM_DAILY_TOKENS_*` |
| L1 (repli) | idem | `NVIDIA_API_KEY` (NIM, déjà), `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` (déjà) |
| L3, L4 | idem | `TAVILY_API_KEY=…` (10 000 + 3 125 crédits reçus) |
| C2 | idem | `COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD` (déjà) ; laisser tourner le premier hindcast (≈ 40 min de tâche de fond) |
| C4/C7 | idem | `POLAR_EFFICIENCY` (défaut 0,85), `server/data/port_days.json` (livré) |
| G3 (plus tard) | VPS nginx | `/tiles/zee.pmtiles` généré (`infra/tiles/build_zee_pmtiles.sh`) |
| tous | VPS | après merge : `deploy.yml` redémarre les services ; vérifier `/ici/warm/status` → `llm.write.calls` monte quand un récit est demandé |
| BI (hotfix #221) | VPS `backend/.env` | `POE_AUTO_REFRESH` reste à 0 tant que `generate_zone_poe` n'est pas non bloquant |

Comment lire une clé déjà posée sur le VPS (Mac, Terminal) :
`ssh ubuntu@135.125.226.16 'grep -E "NEBIUS|TAVILY|COPERNICUS" ~/blue-intelligence-map/naviguide-simulator/server/.env | sed "s/=.*/=…/"'`
(on affiche les noms, pas les valeurs). Poser une clé : `ssh … 'echo "NEBIUS_API_KEY=xxx" >> …/.env && sudo systemctl restart naviguide-simulator'`.

## 4. Calendrier

| Date | Objectif | Ce qui doit être vrai |
|---|---|---|
| **21 sept. (matin)** | revue de la nuit 1 (P2 → L6), merges dans l'ordre, clés posées, hotfix #221 déployé | prod : récit signé « Nemotron 3 Super · Token Factory », film 2:30 qui se lance, bag qui se remplit |
| 21–22 sept. | nuit 2 : correctifs de la revue + S, T, U s'ils ont raté ; lot W1 (revue automatique) ; lot D0 (rangement docs) | CI verte sur `main`, `docs/README.md` index |
| 23–25 sept. | README EN à jour (depuis `ESPRIT_DE_L_APPLICATION.md`), textes Devpost finalisés, **vidéo 2:30** tournée sur le film (F5 plein écran, EN), captures 3:2 | tout ce que `HACKATHON_DEVPOST_SOUMISSION.md` § 0 coche ; crédits Token Factory +25 $ ×2 demandés |
| 26–27 sept. | gel : pas de lot risqué ; recette complète en prod ; Security Agents ; réponses du formulaire (notes après usage) | `simulator.naviguide.fr` stable 48 h |
| **28 sept.** | **première soumission Devpost** (brouillon → Submit) | vidéo YouTube publique, dépôt public MIT, README, liens |
| 29 sept. – 8 oct. | Toronto ; nuits légères (G0–G2 globe, C-lots restants) uniquement si crédits ; sinon pause | rien ne casse `main` |
| **9 oct.** | renouvellement Cursor : reprise des nuits complètes | plan des 3 semaines : globe (G3–G7), L4–L6 si non faits, corrections de revue |
| 16, 23 oct. | mises à jour hebdomadaires de la soumission (vendredi) : changelog, captures, vidéo si le film a changé | chaque vendredi une version soumise |
| **30 oct. 10:00 PT** | soumission finale | tout ce qui est en prod est décrit, rien de plus |
| 1–15 déc. | jugement : l'app doit répondre, crédits Token Factory valides | clés et crédits vérifiés le 30 nov. |

## 5. Les lots « workflow » à ajouter à `LOTS_ORDRE_ET_PROMPTS.md`

- **W1 — Revue automatique** : `infra/agents/export_transcript.py` (store.db → texte), `infra/agents/review_lots.py` (un commentaire par PR, modèle `claude-fable-5-1-max`, gabarit § 1.3), option `--fix` de `run_lots.py` (relance l'agent du lot avec les commentaires de la PR), `infra/agents/review.md` (tableau de la nuit).
- **W2 — Automations Cursor** : trois automations créées avec `/automate` : « PR opened → revue » (secours cloud), « CI completed failure → correction » (secours), « cron jeudi 22 h → brouillon de mise à jour Devpost en PR ». Prompts avec la règle « pas de vidéo, pas de computer use ».
- **W3 — Suite e2e robuste** : `workers: 1` pour `e2e/lots` (les agents ont vu des timeouts à 4 workers), `--repeat-each` sur la fumée, budget de temps par spec.
- **D0 — Rangement de `docs/`** : `ETAT_DES_LIEUX_DOCS.md` § 3, liens réécrits, `ARCHITECTURE.md` réécrit.

## 6. Ce qu'on a appris cette nuit (à garder)

- Un spec de lot qui dépend de l'API casse la CI de **toute la pile** : les specs de lots doivent tenir sans API (règle ajoutée) et la CI les joue en informatif (PR #209).
- Les agents disent ce qu'ils décident seuls quand on le leur demande (rubrique « Décisions prises seul ») : c'est la matière première de la revue humaine — la lire **avant** de regarder l'écran.
- Les libertés les plus fréquentes : un `data-testid` demandé qui n'existe pas (l'agent garde l'existant et ajoute un alias : bien), un fichier hors liste nécessaire (il le dit : bien), un contournement technique (`popup._biFitting`, `window.__naviguideScene` exposé en prod, garde `navigator.webdriver` dans le code produit) : **à trancher au cas par cas**.
- La CI ne détecte pas tout : F1 a rendu la barre film plus haute que ce que le lot O exigeait (109 px vs 96) — seul le porteur le voit ; la revue automatique doit comparer les recettes des lots précédents.
- La prod peut tomber pour une raison sans rapport avec les lots (auto-refresh PoE) : un `curl` de santé sur BI et sur le simulateur au début de chaque revue, et une Automation « cron toutes les 30 min → santé → Slack/mail si rouge » (W2) valent le coup.

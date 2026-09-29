# Prochain batch — plan du 29 septembre 2026 (après la pile « film 1 + deux modes » mergée)

Le porteur a noté « dans le désordre » : DM3 (Fable obligatoire), les lots mis en attente (RG18, RG19, RG20), le lot
AMP. Ce document met de l'ordre, ajoute ce que le chat de pilotage a relevé dans la journée, et dit comment lancer.
Les prompts complets sont dans `docs/LOTS_ORDRE_ET_PROMPTS.md`, section « Prochain batch » (AM1 → RG18 → RG19 → RG20 → DM3).

## 1. L'ordre et pourquoi

| # | Lot | Modèle | Taille | Ce que le porteur verra |
|---|---|---|---|---|
| 1 | **AM1** — AMP croisées par polygone, base remplie le long de la route | Fable | M | Le film et l'encadré Ici disent « le bateau entre dans la réserve de Bonifacio », « longe le parc de Cabrera à 6 milles » — partout sur la route, plus seulement en Europe et à 15 milles d'un centroïde |
| 2 | **RG18** — Une seule plume | Grok | M | Les fiches Ici parlent comme le film ; le modèle n'écrit que sur « Rédigé » ; plus de pré-génération de récits en fond |
| 3 | **RG19** — Chat à trois paliers | Grok | M | Le chat répond aux faits depuis un paquet complet (réglages, polaire, revue du plan, climato, couches) ; Ultra ne raisonne que sur geste, plafonné |
| 4 | **RG20** — Specs vérité | Grok | M | 23 verts avec réserve → assertions dures, stock figé régénéré (film stabilisé par RC19–RC26, moments AM1) |
| 5 | **DM3** — Le ménage des deux modes | **Fable (obligatoire)** | M | Rien à l'écran ; `VIEW_TRACER`, `isTracer`, `ViewModeSwitch` mort supprimé, helpers e2e, clés i18n ; preuve = suite Playwright complète |

Pourquoi cet ordre : AM1 change les **moments** (échantillonnage des perles) — tout ce qui régénère le stock figé (RG20)
doit passer après ; RG18 et RG19 sont indépendants (récits, chat) ; DM3 en dernier parce qu'il renomme les testids que
RG20 vient de toucher, et parce que c'est le lot risqué : s'il tombe, rien n'en dépend.

## 2. Ce que la journée a relevé (fait, en cours, à décider)

Fait aujourd'hui, hors batch : juge Ultra et veille Tavily coupés (#401), mode LLM off / on-demand / all (#402), specs
« poste » rejouées (#400), CI en six tranches (#399), rapport JSON conservé + triage des specs (#403), fusion
r8a/r8b/r10a/r10b (#405), lecteur de journaux CI réparé + specs re2/re4/rf8 (#417, #405), revue de nuit à la reprise +
parcours lu sur la tranche (#422), modèle par lot + plan deux modes (#423), worktree = tête + main (#425).

En file dans la pile en cours : RC21 (fait), DM1, DM2, RC22 (+RC20), RC23, RC24, RC25, RC19, RC26 (récit dense et réparti).

**Base AMP** : moisson ProtectedSeas lancée le 29 sept. à 13:32 le long de la route (212 boîtes de 4°, endpoint public
`GET /amp?bbox=`, fusion dans `amp_sites`, rien d'effacé) — journal `/tmp/amp-harvest.log`, résumé
`/tmp/amp-harvest-summary.json`. Avant : 374 sites (351 en Europe, 1 Caraïbes, 1 Pacifique). Après : voir le résumé,
recopié dans la PR d'AM1.

À décider par le porteur (pas dans ce batch sans son mot) :
- **RG11** — « Rédigé » du film réécrit par LLM depuis les faits (le chemin rédigé n'est plus servi depuis RF2) : optionnel, coûte du Super à chaque génération.
- **Correcteur du matin moins cher** : `plan_corrections.py` envoie toute la pile (≈ 1 M tokens Fable par lancement, `COUTS.md`) ; ne relire que la tranche non revue et les commentaires du porteur diviserait la note par 3-4. Lot infra, S.
- **#227 / #146** : anciennes PR en attente d'une décision.
- Fenêtre d'attente de Grok Bot (15 min) : ses pré-revues arrivent parfois à 16-20 min ; passer `--bot-wait-min` à 20 coûte cinq minutes par tranche, évite « on continue sans ».

## 3. Lancer (quand la pile en cours est mergée et la boucle en veille)

```bash
cd ~/Blue-Intelligence-Map
bash infra/agents/batch-pause.sh          # si la boucle tourne encore
git pull --ff-only origin main
python3 infra/agents/run_lots.py --from AM1 --until DM3 --review-every 2
```

Le modèle de chaque lot vient de sa balise (`model="…"`) ; les autres prennent celui du batch (Grok). Le réviseur de
nuit et Grok Bot font comme d'habitude. Le chat de pilotage peut lancer ceci à la place du porteur.

## 4. Coût

Fable : AM1 ≈ 300-500 k tokens, DM3 ≈ 300-500 k. Grok : inclus. Nebius : zéro pendant le batch (agents en
`NAVIGUIDE_LLM_MODE=off`) ; le poste en `on-demand` ne paie que ce que le bot ou le porteur demande.

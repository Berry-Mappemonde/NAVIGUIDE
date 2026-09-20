# Plan — Nemotron sur Nebius Token Factory + Tavily : tous les usages, 60 $ maximum

Version **1.0** — 20 septembre 2026. Règles : `docs/REGLES_WORKFLOW_AGENT.md`.
Remplace le « lot L » de `PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md` et met à
jour `docs/hackathon-nebius-nvidia.md` § 5–7. Le porteur a demandé de
**remettre le dossier sur la table** : au-delà du « juge de vérité », quels
usages des LLM dans le code actuel et projeté, avec un budget de **60 $**.

## 0. Faits vérifiés le 20 septembre (sources en bas)

- **Règle du hackathon** : le projet doit faire un **appel runtime à l'API
  d'inférence Token Factory** (ou tourner sur Nebius AI Cloud) **et** utiliser
  au moins un modèle open source NVIDIA. NIM (`integrate.api.nvidia.com`,
  utilisé aujourd'hui par `server/story_cascade.py`) **ne compte pas**.
- **API** : OpenAI-compatible, `base_url = https://api.tokenfactory.nebius.com/v1`
  (ou régionale `api.tokenfactory.us-central1.nebius.com/v1`), clé
  `NEBIUS_API_KEY`. Le SDK `openai` suffit ; chez nous `httpx` comme pour NIM.
- **Modèles Nemotron disponibles et prix (par million de tokens, entrée / sortie)** :

| Modèle (id Token Factory) | Contexte | Entrée | Sortie | Usage |
|---|---|---|---|---|
| `nvidia/Nemotron-3_5-Lightning` | 1 M | 0,06 $ | 0,24 $ | appels rapides, classement, traduction, extraction |
| Nemotron 3 Nano 30B (`nvidia/nemotron-3-nano-30b-a3b`, id à confirmer dans le catalogue) | 256 k | ≈ 0,06 $ | ≈ 0,24 $ | idem, multilingue |
| `nvidia/nemotron-3-super-120b-a12b` | 262 k | 0,30 $ | 0,90 $ | rédaction, chat, revue de plan |
| `nvidia/Nemotron-3-Ultra-550b-a55b` | 1 M | 1 $ | 3 $ | juge de vérité, une action visible à la fois |

- **Crédits** : ~60 $ Token Factory reçus le 13 septembre, **essai 29 jours**
  (→ expire vers le **12 octobre**). Le formulaire Devpost donne **+25 $** et le
  Nebius Builders Program **+25 $** (page Resources). **Les juges testent du
  1ᵉʳ au 15 décembre** : il faut des crédits valides à cette date, sinon la
  cascade tombe sur les règles et la soumission ment. Action : demander les
  deux bonus maintenant, et surveiller la date d'expiration réelle dans la
  console Nebius.
- **Tavily** : 1 000 crédits gratuits par mois sans carte ; ~0,008 $ le crédit
  en paiement à l'usage ; crédits hackathon reçus : 10 000 + 3 125. Un
  `search` basique = 1 crédit, un `extract` = 1 crédit par 5 URL. Bonus
  « Best Use of Tavily » (3 000 $) : appel runtime fonctionnel dans la solution.

## 1. Où un LLM apporte quelque chose — et où il n'a rien à faire

Principe du produit : **les faits viennent des sources, le LLM ne produit
jamais un nombre**. Il sert à quatre choses : **rédiger** (mettre en langue des
faits structurés), **choisir** (parmi des candidats calculés), **relier**
(faire parler une source officielle avec un contexte) et **juger** (dire si un
texte est encore prouvé par sa source).

| # | Usage | Existe ? | Modèle | Quand il est appelé | Tokens / appel | Appels / jour (prod) | $/jour |
|---|---|---|---|---|---|---|---|
| U1 | **Récit `ici()`** (paragraphe du sac du moment) | oui, via NIM → à basculer | Super | pré-génération (`story_cache.py`), ≤ 1 par perle et par jour | 3 k + 0,3 k | ~60 | 0,03 |
| U2 | **Script du film 2:30** (rédaction + balises d'événements) | non (plan film, lot F3) | Super | à chaque nouvelle escale, max 1/jour, 2 langues | 6 k + 1 k | 2 | 0,006 |
| U3 | **Sélection des événements du film** (6–9 parmi ~150) | non (lot F3) | Lightning / Nano | même cadence que U2 | 8 k + 0,2 k | 2 | 0,001 |
| U4 | **Chat journal de bord** | oui, via NIM → à basculer | Super (Nano si question courte) | à la demande | 4 k + 0,3 k | 30 | 0,04 |
| U5 | **Paragraphe de la fiche d'escale** | oui, via NIM → à basculer | Nano | 1 par escale et par semaine (cache) | 3 k + 0,3 k | 3 | 0,001 |
| U6 | **Juge de vérité** (une carte NOW / une fiche Gold vs sa source Tavily) | non | **Ultra** | une action visible : entrée dans une ZEE, ouverture d'une fiche PoE | 6 k + 0,3 k | 10 | 0,07 |
| U7 | **Commentaire de la revue de plan** (« ce que je changerais ») | non | Super | quand le tableau (lot K) change ; cache | 5 k + 0,4 k | 1 | 0,002 |
| U8 | **Explication du conseil de route** (delta isochrone en mots) | non | Nano | à chaque recalcul demandé | 2 k + 0,2 k | 5 | 0,001 |
| U9 | **Traduction FR → EN** des textes rédigés (film, briefing, fiche) | partiel (i18n statique) | Lightning | dérivée de U1/U2/U5, cache | 1 k + 1 k | 20 | 0,006 |
| U10 | **Veille Tavily par escale** (avis aux navigateurs, travaux, fermeture, événement local) → carte FREE datée | non | Tavily + Nano (résumé, sans chiffre nouveau) | 1 `search` par escale et par jour, à J-10 → J+2 | 1 crédit + 3 k | 3 | 0,02 + 0,001 |
| U11 | **Fiche Gold PoE revérifiée** : Tavily `extract` de la page officielle, Ultra dit si la fiche est encore prouvée | non | Tavily + Ultra | quand le bateau entre dans la ZEE (une fois par ZEE et par semaine) | 1 crédit + U6 | 2 | 0,02 |
| U12 | **Enrichissement science / projet** : Tavily `extract` de la page de la station ou du projet croisé → phrase sourcée dans la carte | non | Tavily + Nano | 1 par entité, cache définitif | 1 crédit + 2 k | 3 | 0,02 |
| U13 | **Mémoire sémantique du journal** (« a-t-on déjà eu un coup de vent pareil ? ») | non | embeddings (`Qwen/Qwen3-Embedding-8B`, 0,01 $/M ; pas NVIDIA) | à l'écriture du journal | 0,5 k | 50 | 0,0003 |
| U14 | **Nano Omni** (multimodal) : lire une carte météo image ou une photo de port | non — **écarté** : nos données sont déjà structurées | — | — | — | — | — |
| U15 | **Serverless Jobs** (pré-génération nocturne sur Nebius au lieu du VPS) | non — **optionnel**, pas requis par la piste | — | — | — | — | — |

**Total prod ≈ 0,2 $/jour**, soit **≈ 6 $/mois**. Le film 2:30 pour la vidéo
coûte **moins de 0,01 $** par génération. Les 60 $ ne sont pas un problème de
volume ; ils sont un problème de **date d'expiration** (§ 0) et de **boucles
accidentelles** (un appel par rendu React = ruine). D'où les gardes du § 3.

Ce qui reste **hors LLM** pour toujours : vitesse, position, distances,
horloge, ETA, détection d'événements (règles), classements NOW / FREE,
Gold, cartes de sources ; le chiffre affiché vient d'un calcul ou d'une
source, jamais d'un modèle.

## 2. La cascade cible

```
demande → cache SQLite ? → oui : réponse
                        → non : Token Factory (Nemotron : Lightning/Nano | Super | Ultra selon l'usage)
                                → échec / quota / crédit épuisé : OpenRouter (mêmes prompts) → Claude Haiku
                                → échec total : version « règles » (brut), toujours disponible
→ filtre des nombres (`filter_numbers`) → réponse, avec `source: "nemotron-super" | "openrouter" | "rules"`
```

- **Token Factory d'abord**, toujours : c'est la condition d'éligibilité et
  la démonstration. NIM disparaît de la cascade de soumission (garder le code
  derrière un drapeau `NAVIGUIDE_LLM_PROVIDERS=tokenfactory,openrouter,claude`).
- Le **niveau** (Lightning / Super / Ultra) est un paramètre de `cascade_text`
  (`tier="fast" | "write" | "judge"`), pas un modèle codé en dur.
- **Budget** : compteur journalier de tokens par niveau dans `pearl_store.kv`
  (`llm-budget:<date>:<tier>`), plafonds par défaut : fast 2 M, write 500 k,
  judge 100 k tokens/jour. Au-delà : repli sans appel, et `source: "budget"`
  visible dans l'UI (petit libellé, jamais une surface retirée).
- **Affichage** : chaque texte rédigé porte sa source (« Nemotron 3 Super ·
  Token Factory », « règles ») — c'est ce que le juge regarde.
- **Sécurité** : `NEBIUS_API_KEY` et `TAVILY_API_KEY` dans
  `naviguide-simulator/server/.env` sur le VPS (lecture : `ssh … cat`), jamais
  dans le dépôt ; `.env.example` documente les noms.

## 3. Gardes anti-ruine (à écrire avant le premier appel)

1. Un appel LLM part **du serveur** uniquement, jamais du navigateur.
2. Tout appel passe par `cascade_text` → **cache d'abord** (clé = hash du
   prompt + modèle + lang), TTL par usage (U1 24 h, U2 jusqu'à la prochaine
   escale, U5 7 jours, U6 7 jours, U12 définitif).
3. **Débit** : au plus 4 appels Token Factory en parallèle ; file d'attente
   au-delà ; un même `cache_key` en cours n'est jamais relancé (verrou).
4. **Plafond journalier** § 2 ; compteur affiché sur `/ici/warm/status`
   (`llm: {tier: {tokens, calls, usd}}`).
5. Test de contrat : aucun `useEffect` du client ne peut déclencher un appel
   LLM sans action utilisateur ou sans passage par la pré-génération.

## 4. Les lots

Ordre : **L1 → L2 → L3 → L4 → L5 → L6** ; L4 et L5 indépendants après L2.
L1 est **le préalable à toute soumission**. Le film (lot F3) suppose L1.

### Lot L1 — Fournisseur Token Factory + budget + source affichée (M)

**Fichiers.** `server/story_cascade.py`, nouveau `server/llm_budget.py` (+ test),
`server/pearl_store.py` (ns `kv` existant), `server/ici_warm.py` (status),
`server/.env.example`, `docs/hackathon-nebius-nvidia.md` § 5.

**Étapes.** 1) `_call_tokenfactory(system, user, tier)` : URL § 0, modèle par
`tier` (`fast` → Lightning, `write` → Super, `judge` → Ultra), `max_tokens`
par usage, timeout 25 s. 2) `cascade_text(..., tier=)` : ordre § 2, drapeau
`NAVIGUIDE_LLM_PROVIDERS`. 3) `llm_budget.py` : compteurs, plafonds, `usd`
estimé avec la grille § 0. 4) Toute réponse porte `source`. 5) Status.

**Tests.** Faux serveur HTTP : Token Factory répond → `source=nemotron-super` ;
Token Factory 429 → OpenRouter ; tout tombe → `rules`. Budget : au plafond,
aucun appel réseau. Verrou : deux demandes identiques → un appel.

**Recette (changement visible minime).** Récit `ici()` à Nouméa : libellé
« Nemotron 3 Super · Token Factory » sous le paragraphe ; `/ici/warm/status`
montre `llm.write.calls ≥ 1`. Spec Playwright : le libellé `data-testid="story-source"`
contient « Token Factory » (API lancée).

### Lot L2 — Basculer U1, U4, U5 sur la cascade cible (S)

**Fichiers.** `server/story_cache.py`, `server/logbook_chat.py`,
`server/escale_api.py`, tests associés.

**Recette (aucun changement visible).** Trois parcours fixes (règles § 4) ;
les libellés de source disent « Token Factory » ; le chat répond « à quai,
0 kn » à Nouméa (P2).

### Lot L3 — Juge de vérité (U6) + fiche Gold revérifiée par Tavily (U11) (M)

**Fichiers.** nouveau `server/truth_judge.py` (+ test), nouveau
`server/tavily_client.py` (+ test, faux serveur), `server/ici_engine.py`
(déclencheur : entrée en ZEE / ouverture d'une fiche PoE), `src/components/MomentCards.jsx`
(badge « vérifié le … », « non revérifiable », **rien retiré**), i18n.

**Étapes.** 1) Tavily `extract` de l'URL officielle de la fiche (PoE Gold :
page des douanes / de l'autorité portuaire déjà dans la fiche). 2) Ultra
reçoit : la fiche (faits), l'extrait (≤ 6 k tokens), la question « chaque
affirmation de la fiche est-elle soutenue par l'extrait ? » → JSON
`{supported: [...], unsupported: [...], stale_hint: str|null}`, **aucun
chiffre nouveau**. 3) La carte affiche : « Vérifié le 20 sept. (Tavily +
Nemotron 3 Ultra) » ou barre les affirmations `unsupported` (texte barré,
jamais supprimé). 4) Cache 7 jours par (ZEE, URL).

**Tests.** Faux Tavily + faux Ultra : une affirmation non soutenue → barrée ;
extrait vide → « non revérifiable » ; budget `judge` au plafond → pas d'appel.

**Recette (changement visible).** Simulation, entrée dans la ZEE de
Martinique : carte NOW « Port d'entrée Fort-de-France (Gold) » avec
« Vérifié le … · Tavily + Nemotron 3 Ultra » ; en coupant la clé Tavily :
« non revérifiable ». Spec : `data-testid="truth-badge"` ; captures.

### Lot L4 — Veille Tavily par escale (U10) + enrichissement science / projet (U12) (M)

**Fichiers.** `server/tavily_client.py`, `server/ici_warm.py` (tâche
quotidienne J-10 → J+2 par escale), `server/voyage_journal.py` (kind `news`,
daté, avec URL), `src/engine/momentCard.js` (carte FREE `news`), i18n.

**Étapes.** 1) `search` ciblée : `"<port> marina|port|harbour" + (notice|avis|travaux|fermeture|event)`,
`topic=news`, 7 jours, 5 résultats, `include_domains` officiels quand connus.
2) Nano résume en une phrase **sans chiffre nouveau**, cite l'URL ; carte FREE
datée, expire à J+2. 3) Science / projet : `extract` de la page officielle de
l'entité (une fois), phrase sourcée ajoutée à la perle riche.

**Recette (changement visible).** Suivre, prochaine escale : carte FREE
« Nouméa · veille du 20 sept. : … (source, lien) » ; fiche science croisée
avec une phrase sourcée et son lien. Spec : `data-kind="news"` présent.

### Lot L5 — Revue de plan commentée (U7) et conseil de route expliqué (U8) (S)

**Fichiers.** `server/plan_review.py`, `server/voyage_api.py` (recompute),
`src/components/PlanReview.jsx`, `src/hooks/useVirtualVessel.js`, i18n.

**Recette (changement visible).** Sous le tableau de revue : paragraphe
« Ce que je changerais » avec sa source ; après un recalcul avec vent max 30 kn :
phrase « La route s'écarte de … pour éviter … » (les nombres sont ceux du
recalcul).

### Lot L6 — Traduction des textes rédigés (U9) + mémoire sémantique (U13, option) (S)

**Recette.** Langue EN : récit, film et fiche d'escale en anglais avec la
même source ; option : question au chat « avons-nous déjà eu plus de 35 nœuds ? »
→ réponse qui cite l'entrée `wx` du journal (les faits, pas un souvenir
inventé).

## 5. Ce que dit la soumission (vrai seulement après L1–L3)

- « Every sentence the app writes is generated by **NVIDIA Nemotron 3 on
  Nebius Token Factory** (Super writes, Lightning ranks and translates,
  Ultra judges), from structured facts — the model never produces a number. »
- « When the boat enters an EEZ, **Tavily** re-reads the official port-of-entry
  page and Nemotron 3 Ultra strikes out whatever is no longer supported. »
- Formulaire « Which model(s) did you use, and why » : Lightning / Nano pour
  le volume (sélection, traduction : 0,06 $/M), Super pour la rédaction
  (120 B MoE, 12 B actifs : qualité / coût), Ultra réservé au jugement (une
  action visible = un appel).

## Sources (consultées le 20 sept. 2026)

- Nebius, « NVIDIA Nemotron and Nebius Token Factory » — modèles, extrait de
  code (`base_url`, `nvidia/nemotron-3-super-120b-a12b`) : nebius.com/services/token-factory/nemotron
- Nebius, « Nemotron 3 Super now available on Token Factory » (11 mars 2026).
- Catalogue de prix Token Factory (via models.dev / Mastra, 20 modèles) :
  Lightning 0,06/0,24 ; Super 0,30/0,90 ; Ultra 1/3 ; Qwen3-Embedding-8B 0,01.
- OpenRouter, fournisseur Nebius : Nemotron 3 Nano 30B.
- Tavily, « Credits & Pricing » : 1 000 crédits/mois gratuits ; 0,008 $/crédit.
- Devpost, règles officielles du hackathon (§ 4 Project Requirements, § 6
  Judges & Criteria, § 8 Prizes) et page Resources (crédits +25 $ ×2).

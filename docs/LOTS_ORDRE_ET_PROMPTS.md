# Tous les lots, dans l'ordre, avec le prompt complet de chacun

Version **1.0** — 20 septembre 2026. Un seul document pour lancer le travail :
la liste ordonnée des lots (revue visuelle, Nemotron/Tavily, film, calculs,
globe) et, pour chaque lot, **le prompt à coller tel quel** dans un nouvel
agent Cursor avec le modèle **Grok 4.6 Extra High Fast** (`cursor-grok-4.6-xhigh-fast`).
Chaque prompt est autonome : il dit quoi lire, quels fichiers ouvrir, quoi
faire, quoi tester, quoi recetter, quoi livrer.

Deux façons de l'utiliser :

1. **À la main** : nouvel agent → modèle Grok 4.6 xhigh fast → coller le bloc
   `text` du lot → Envoyer. Quand la PR est ouverte, passer au lot suivant.
2. **En chaîne, la nuit** : `infra/agents/run_lots.py` lit ce fichier, lance
   **un agent par lot** — par défaut le CLI Cursor sur ce Mac dans un worktree
   git (`--runtime local`), sinon un agent Cloud par l'API (`--runtime cloud`) —,
   attend la fin, vérifie la PR et sa CI, puis lance le suivant — voir § 3.
   Les balises `<!-- LOT … -->` qui précèdent chaque prompt sont lues par ce
   script : ne pas les modifier à la main sans mettre le script à jour.

**Préalables** (une fois) : la PR #203 (ces documents) est **mergée sur
`main`** — les agents Cloud clonent `main` et doivent y trouver
`docs/REGLES_WORKFLOW_AGENT.md` et les plans ; la PR #204 (bouton Écouter)
est mergée ; `NEBIUS_API_KEY` et `TAVILY_API_KEY` sont dans le `.env` du VPS
pour les lots L (les agents ne les ont pas et n'en ont pas besoin : ils
testent avec de faux serveurs).

## 1. L'ordre

| # | Lot | Plan | Taille | Dépend de | Ce que le porteur verra |
|---|---|---|---|---|---|
| 1 | P2 | complémentaire | S | — | 0 kn à quai, vitesse mesurée en mer |
| 2 | C1 | audit calculs | S | — | « 16 étapes (15 mer, 1 terre) · 17 escales · 1 248 points » — **fait, PR #207 mergée (20 sept., agent local, 5 min 44)** ; `--skip C1` |
| 3 | L1 | Nemotron | M | — | libellé « Nemotron 3 Super · Token Factory » sous le récit |
| 4 | M | complémentaire | S | — | crédits carte propres, sources cliquables |
| 5 | N | complémentaire | S | — | chat en haut, panneau gauche qui ne saute plus |
| 6 | O | complémentaire | S | — | barre film sur une rangée, un seul bouton son |
| 7 | F1 | film | M | O | film 2 min 30 mené par la voix, zoom stable |
| 8 | F2 | film | M | — | cartes « changement de régime », « station croisée » |
| 9 | L2 | Nemotron | S | L1 | récit, chat, fiche d'escale via Token Factory |
| 10 | F3 | film | M | F1, F2, L1 | script du film brut + rédigé par Nemotron |
| 11 | F4 | film | S | F1 | bulle événement qui part du bateau |
| 12 | L3 | Nemotron | M | L1 | badge « Vérifié · Tavily + Nemotron 3 Ultra » |
| 13 | F5 | film | S | F3, F4 | film en anglais, « plein écran film » |
| 14 | S | complémentaire | S | — | Brisbane → SF direct dans le Pacifique |
| 15 | T | complémentaire | S | S | briefing juste sur la route dessinée |
| 16 | C2 | audit calculs | L | P2 | hindcast : « 7,4 kn · hindcast (GFS archive) » |
| 17 | C3 | audit calculs | M | C2 | une seule vitesse partout, route teintée par régime |
| 18 | U | complémentaire | M | — | zoom fluide |
| 19 | L4 | Nemotron | M | L1 | veille Tavily par escale, science sourcée |
| 20 | L5 | Nemotron | S | L1 | revue de plan commentée, conseil de route expliqué |
| 21 | C4 | audit calculs | M | C2 | courant, polaire de vagues, efficacité, climatologie échantillonnée |
| 22 | C5 | audit calculs | S | C4 | cahier des calculs, parité client/serveur |
| 23 | C7 | audit calculs | S | C5 | jours à quai par escale (table sourcée), repli sans polaire déclaré, info-bulle distance film |
| 24 | C6 | audit calculs | M | C4 | ETA probabiliste par ensembles : « arrivée entre le 11 et le 14 (p10–p90) » |
| 25 | L6 | Nemotron | S | L2 | traduction des textes rédigés, mémoire sémantique (option) |
| 26 | G0 | globe | S | — | éprouvette globe (hors app) + décision A/B |
| 27 | G1 | globe | M | G0 | onglet Carte / Globe |
| 28 | G2 | globe | M | G1 | route, bateau, escales sur le globe |
| 29 | G3 | globe | M | G2 | couches BI, ZEE en PMTiles |
| 30 | G4 | globe | M | G3 | GRIB et climatologie en symboles |
| 31 | G5 | globe | M | G4 | popups, bulle, tracer ma route sur le globe |
| 32 | G6 | globe | S | G5, F1 | le film sur le globe |
| 33 | G7 | globe | S | G6 | parité, tests sur les deux vues |
| **nuit 2** | | **corrections revue 21 sept.** | | | `PLAN_CORRECTIONS_REVUE_21_SEPT.md` — pile P2 → L6 **mergée le 21 sept.** (#208, #237, #210) |
| 34 | R1 | corrections | S | — | plus de phrases d'aide, Esri une fois, « Polaires chargées » seul, bouton de remise qui marche, brut/rédigé grisé |
| 35 | R2 | corrections | S | R1 | barre film sur une rangée, Masquer partout, bouton Escale précédente |
| 36 | R3 | corrections | M | — | Revoir : premier clic fiable, voix jusqu'au bout, caméra directe, voix EN audible |
| 37 | R4 | corrections | M | R3 | film fluide : le bateau glisse, la caméra suit |
| 38 | R5 | corrections | S | — | récit sans « puis, puis », km à terre |
| 39 | R6 | corrections | M | R3 | bulles pendant le film seulement, événements importants, croix |
| 40 | R7 | corrections | S | — | fiche d'escale sur le drapeau, sans Écouter |
| 41 | R11 | corrections | S | — | « arrivée entre le … et le … », jours de mer cohérents |
| 42 | R12 | corrections | S | — | carte bornée aux pôles, zoom vérifié sur build de prod |
| 43 | R13 | corrections | S | R1 | script des redites + première suppression |
| **corrections 2** | | **revue du 21 sept. au soir** | | | `PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md` — après la pile R1 → R13 mergée |
| 44 | RA1 | corrections 2 | M | — | fiche d'escale et chat n'affichent plus le prompt / le raisonnement du modèle |
| 45 | RA2 | corrections 2 | S | — | le récit énonce les escales dans l'ordre exact du voyage, sans répétition |
| 46 | RA3 | corrections 2 | M | RA2 | film : fond de carte gardé, aucun saut, zoom stable en fin, dézoom archipels, bulle utile |
| 47 | RA4 | corrections 2 | M | RA3 | jambes avion en noir pointillé, hors distance ; position live stable ; carte non répétée à l'infini |
| 48 | RA5 | corrections 2 | M | RA4 | Stop stoppe ; pas de fiche d'escale pendant le film ; croix qui ferme |
| 49 | RA6 | corrections 2 | S | — | redite skipper retirée, crédits au-dessus de la barre, km à terre, cadre de réponse du chat |
| 50 | RA7 | corrections 2 | S | — | « arriver entre le … et le … » sous la prochaine escale, intervalle resserré |
| 51 | RA8 | corrections 2 | M | — | vitesse réelle par la météo historique (archive Open-Meteo/ERA5, sans clé) le long de la route — après le film |
| **nuit 3** | | **chantiers** | | | `PLAN_ICI_JOURNAL_EXPERT.md` — pré-rédigés (21 sept. soir) pour que le correcteur puisse y fondre des corrections |
| 52 | R8a | ici / journal | S/M | RA5 | `build_moment` + `signature` (serveur, fixture) — aucun changement visible |
| 53 | R8b | ici / journal | M | R8a | `GET /ici/moment` + encadré unique **sans titre** (Maintenant · Récit · Journal), toute la hauteur |
| 54 | R8c | ici / journal | M | R8b | branchement ; plus aucune pop-up sur la carte (à bord maintenant, fiches science, fiche d'escale) |
| 55 | R9a | ici / journal | M | R8a | table `moments`, remplissage le long des perles, `GET /voyage/official/moments` |
| 56 | R9b | ici / journal | S/M | R8c, R9a | vue Journal chronologique ; clic = curseur à la date |
| 57 | R9c | ici / journal | M | R9a | le film raconte le journal : sélection sous budget, préchauffé, chapitre par chapitre, ordre exact |
| 58 | R10a | expert | M | R8a | `evaluate_plan` : alertes pondérées par jambe, cyclone **daté** |
| 59 | R10b | expert | M | R10a | `advise` : décalages de date en cascade, score, phrase gabarit, `GET /voyage/official/advice` |
| 60 | R10c | expert | M | R10b | écart local borné (+20 %, corridor ± 300 nm) — plus jamais 4 643 nm |
| 61 | R10d | expert | M | R10c, R8c | Revue du plan conseillée, deux colonnes, **Appliquer** ; « Demander conseil » |
| **NAVIGUIDE** | | **ancien code utile** | | | `PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md` — décisions du 21 sept. |
| 62 | N1 | naviguide | M | — | Importer GeoJSON / KML dans « Tracer ma route » |
| 63 | N2 | naviguide | S | — | Exporter GeoJSON / KML (route de la vue), panneau droit |
| 64 | N3 | naviguide | M | — | score anti-trafic par jambe (searoute), pastilles ; trait inchangé |
| 65 | N4 | naviguide | S | — | zones de piraterie → cartes NOW et alertes |
| **hygiène** | | **avant la soumission** | | | |
| 66 | D0 | docs | S | — | README FR/EN, manuel utilisateur, `docs/README.md` index, rangement (`ETAT_DES_LIEUX_DOCS.md` § 3) |
| 67 | H1 | dépôts | M | D0 | préparer la séparation des dépôts : script + procédure (public = simulateur seul) ; l'exécution est au porteur (26–27 sept.) |
| **corrections 3** | | **revue du 22 sept. (matin)** | | | `PLAN_CORRECTIONS_2026-09-22.md` — après la pile RA1 → RA8 mergée ; constats fondus dans R8a, R8c, R9c, R10d ; dans l'ordre du document les RB passent AVANT R8a |
| 68 | RB1 | corrections 3 | M | — | Halifax ↔ Saint-Pierre redevient une jambe mer (climatologie, trait coloré, bateau relais) ; l'avion ne vole que Cayenne ↔ Halifax |
| 69 | RB2 | corrections 3 | S | — | zoom + − horizontal et compact en bas à droite, à côté des crédits, jamais masqué |
| 70 | RB3 | corrections 3 | S | — | plus jamais de prompt : le cache des fiches est re-nettoyé, le journal répond en phrases |
| 71 | RB4 | corrections 3 | S | — | barre de lecture sans barre de scroll : un bouton de vitesse à 4 niveaux, flèches d'escale, haut-parleur |
| 72 | RB5 | corrections 3 | M | — | le film part de Saint-Maur le 15 mai 2026 ; la voix dit « milles nautiques » |
| 73 | RB6 | corrections 3 | M | RB5 | la voix ne coupe plus, Stop coupe tout, la caméra ne saute plus sur la Polynésie |
| 74 | RB7 | corrections 3 | S | — | « arrivée entre le … et le … » visible dès le démarrage (ensemble ETA préchauffé) |
| 75 | RB8 | corrections 3 | S | RB1 | la route est dessinée sur les deux copies du monde ; survol d'un segment parcouru → vitesse de l'époque |
| **corrections 4** | | **revue du 23 sept. (matin)** | | | `PLAN_CORRECTIONS_2026-09-23.md` — après la pile RB1 → RC5 (#269 → #302) mergée ; constats globe fondus dans G2 et G5 |
| 76 | RD1 | corrections 4 | M | — | le clic sur la route ouvre le pop-up Copernicus partout (copies du monde comprises) ; plus d'ouverture du panneau gauche au clic carte ; carrés verts ▤ retirés |
| 77 | RD2 | corrections 4 | S | — | crédits et zoom sur le fond de carte (jamais de bande blanche), toggles gauche/droit à la même hauteur, point de tracé exactement sous le clic |
| 78 | RD3 | corrections 4 | S | — | encadré jaune des couloirs retiré (pastille par jambe conservée), nom du bateau une seule fois, remise du chiffre au profil réparée |
| 79 | RD4 | corrections 4 | M | — | le voyage officiel est semé au démarrage serveur : plus de 404, fourchette « arrivée entre le … et le … », journal et film remplis |
| 80 | RD5 | corrections 4 | S | — | l'app démarre en Suivre ; date de départ visible et efficace en Simulation (année affichée) ; date de Revoir réglable et distincte |
| 81 | RD6 | corrections 4 | S | RD4 | onglet Récit jamais vide (absent hors Suivre), lignes du Journal qui nomment leur événement, plus d'espace mort |
| 82 | RD7 | corrections 4 | M | RD4 | le film déclame les vraies données du journal (marinas, AMP, stations, cyclones, culture) ; durées 2:30/3:00 décochables, aucune par défaut ; plus de phrases de remplissage |

Les lots C couvrent **toutes** les lignes de l'audit (`PLAN_AUDIT_CALCULS.md`
§ 3 donne la correspondance ligne → lot) ; avec P2, S, F1 et F2 pour les
lignes qui leur appartiennent.

Taille : S ≤ ½ jour-agent, M ≤ 2 jours, L ≤ 4 jours. « Dépend de » : le lot
suppose que l'autre est **au moins dans la même pile** (branche empilée) ;
en chaîne nocturne, le script empile chaque lot sur la branche du précédent,
donc l'ordre du tableau suffit.

## 2. Les prompts

Le socle commun est dans chaque prompt (répété volontairement : un agent ne
lit que son prompt). Les numéros de lignes sont indicatifs (`rg -n` d'abord).

<!-- LOT id="P2" title="Vitesse réelle, zéro à quai" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot P2 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot P2 — Vitesse réelle, zéro à quai.
Objectif : un bateau à quai a une vitesse de 0 ; en mer, la vitesse citée est celle du moment, pas celle de la jambe planifiée.
Cause racine : server/voyage_clock.py (~l. 379) et src/engine/voyageClock.js (~l. 486) : à quai, l'échantillon recopie le sommet d'arrivée dont speedKnots = vitesse de la jambe.
Fichiers à ouvrir (seulement) : server/voyage_clock.py (l. 360–400), src/engine/voyageClock.js (l. 458–512), server/logbook_chat.py (build_context), src/components/SimulationFilmBar.jsx (ligne d'horloge), src/App.jsx PAR EXTRAIT : rg -n "chatContextRef.current = |boatKnots|liveKnots" src/App.jsx puis Read avec offset/limit.
Étapes : 1) dans les deux échantillonneurs, la branche « à quai » renvoie speedKnots: 0 et vehicle: "quay" ; 2) le contexte du chat porte official.speedKnots = 0 à quai, sinon la vitesse mesurée envoyée par le client (basis: "measured") et la vitesse planifiée à part (plannedKnots) ; 3) la barre film affiche « à quai » à la place de « 11.9 kt » quand atQuay ; i18n fr + en.
Tests : server/tests/test_voyage_clock.py (échantillon à quai → 0), src/engine/voyageClock.test.js (idem), server/tests/test_logbook_chat.py (contexte à quai → speedKnots 0). npm test, .venv/bin/python -m pytest -q, npx vite build : tout vert.
Recette à rejouer avec un spec Playwright e2e/lots/p2-quai.spec.js (assertions puis captures JPEG q70 dans docs/recette/lot-p2/) : Suivre, bateau à quai → data-testid="clock-line" contient « à quai » ; Simulation en mer → une vitesse en kn qui varie. Captures 01-quai, 02-mer.
Branche fix/lot-p2-vitesse-quai depuis la base indiquée par ton environnement (main à jour si rien n'est dit). Une PR vers main, corps = gabarit REGLES § 3 (Objectif, Cause racine, Ce qui change, Tests, Recette, Review automatique, Hors périmètre). Ne merge pas. Pas de push --force.
Interdits : retirer une surface visible sur main ; un chiffre produit par un LLM ; une vidéo ; un secret dans le diff ; Nemotron / Nebius / Tavily.
Si quelque chose bloque, décide seul la solution la plus simple, note-la dans la PR (« Décisions prises seul »), ne pose pas de question.
Quand tu as fini : numéro de PR, compteurs de tests, liste des captures, ce que tu n'as pas fait.
```

<!-- LOT id="C1" title="Résumé de l'expédition juste" plan="docs/PLAN_AUDIT_CALCULS.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 0 (constat A5) et le « Lot C1 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot C1 — Résumé de l'expédition juste.
Objectif : l'encadré « Expédition » (outils droite) ne compte plus les sommets du routeur (« 36 segments · 36 waypoints ») mais les étapes entre escales : « 39 425,9 nm · 16 étapes (15 mer, 1 terre) · 17 escales · 1 248 points ».
Fichiers à ouvrir (seulement) : src/components/ToolsSidebar.jsx (ExpeditionBox, l. 182–197), src/utils/geo.js (summarizeRoute, l. 131), src/utils/geo.test.js, src/i18n/fr.js, src/i18n/en.js, src/App.jsx PAR EXTRAIT : rg -n "stats\.segments|escaleMarks=|waypointCount" src/App.jsx.
Étapes : 1) summarizeRoute (ou une nouvelle fonction summarizeLegs(escaleMarks, segments)) calcule legs = marques d'escale consécutives, sea/land depuis nonMaritime ; 2) ExpeditionBox affiche la ligne ci-dessus ; « points » a une info-bulle (title) : « 36 points de passage du routeur (caps, canaux) · 1 248 sommets du tracé » ; le mot « waypoints » quitte la ligne ; 3) i18n fr + en ; 4) le compte d'escales vient des marques d'escale (17 pour la route officielle), pas d'un chiffre en dur.
Tests : geo.test.js — 17 marques → 16 étapes ; Saint-Maur → La Rochelle comptée terre ; route dessinée sans marques → « 1 étape ». npm test, npx vite build : verts.
Recette (spec e2e/lots/c1-resume.spec.js, captures dans docs/recette/lot-c1/) : data-testid="route-summary" contient « 16 étapes » et « 17 escales » et ne contient pas « waypoints » ; capture 01-resume.
Branche feat/lot-c1-resume-expedition depuis la base indiquée par ton environnement (main à jour sinon). Une PR vers main, corps = gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une surface visible sur main ; un chiffre produit par un LLM ; une vidéo ; un secret dans le diff.
Si quelque chose bloque, décide seul la solution la plus simple et note-la dans la PR. Quand tu as fini : numéro de PR, compteurs de tests, captures, ce que tu n'as pas fait.
```

<!-- LOT id="L1" title="Fournisseur Token Factory + budget + source affichée" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 0, § 2, § 3 et le « Lot L1 » (texte intégral). Tu travailles dans naviguide-simulator/. Ce lot est LE préalable à la soumission au hackathon : l'app doit appeler Nebius Token Factory (NIM ne compte pas).

Lot L1 — Fournisseur Token Factory + budget + source affichée.
Fichiers à ouvrir (seulement) : server/story_cascade.py, nouveau server/llm_budget.py (+ server/tests/test_llm_budget.py), server/pearl_store.py (ns kv existant : kv_get/kv_put), server/ici_warm.py (endpoint /ici/warm/status), server/.env.example, server/tests/test_story_cascade.py (créer si absent), src/components/Sidebar.jsx PAR EXTRAIT (rg -n "storyStatus|story-source|récit" src/components/Sidebar.jsx) pour le libellé de source, src/i18n/fr.js, src/i18n/en.js, docs/hackathon-nebius-nvidia.md § 5.
Étapes : 1) _call_tokenfactory(system, user, tier, client) : POST https://api.tokenfactory.nebius.com/v1/chat/completions (OpenAI-compatible), clé NEBIUS_API_KEY, modèle par tier : fast → nvidia/Nemotron-3_5-Lightning, write → nvidia/nemotron-3-super-120b-a12b, judge → nvidia/Nemotron-3-Ultra-550b-a55b (ids surchargeables par variables NAVIGUIDE_TF_MODEL_FAST/WRITE/JUDGE), max_tokens par usage, timeout 25 s ; 2) cascade_text(..., tier="write") : ordre = cache SQLite → Token Factory → OpenRouter → Claude → repli règles, drapeau NAVIGUIDE_LLM_PROVIDERS (défaut "tokenfactory,openrouter,claude") ; NIM reste possible derrière le drapeau mais n'est plus dans le défaut ; 3) llm_budget.py : compteurs journaliers par tier dans kv (clé llm-budget:<date>:<tier>), plafonds NAVIGUIDE_LLM_DAILY_TOKENS_FAST/WRITE/JUDGE (défaut 2 000 000 / 500 000 / 100 000), usd estimé avec la grille du plan § 0 ; au plafond : aucun appel réseau, source "budget" ; verrou : deux demandes identiques en cours → un seul appel ; au plus 4 appels Token Factory en parallèle (semaphore) ; 4) toute réponse de cascade_text porte source ∈ {"nemotron-lightning","nemotron-super","nemotron-ultra","openrouter","claude","rules","budget","cache"} et le client affiche « Nemotron 3 Super · Token Factory » (ou l'équivalent) sous le récit ici() : data-testid="story-source" — ajouter, ne rien retirer ; 5) /ici/warm/status expose llm: {tier: {tokens, calls, usd}}.
Tests (faux serveur HTTP avec httpx.MockTransport ou respx) : Token Factory répond → source nemotron-super ; 429 → OpenRouter ; tout tombe → rules ; budget au plafond → aucune requête ; verrou → un appel pour deux demandes ; filter_numbers toujours appliqué. pytest, npm test, vite build : verts.
Recette : le lot est visible seulement si l'API tourne avec une clé : spec e2e/lots/l1-source.spec.js qui, SI la page expose data-testid="story-source", vérifie qu'il contient « Token Factory » ou « règles » (jamais vide) ; capture 01-source dans docs/recette/lot-l1/. Dans la PR, dire explicitement que la recette réelle demande NEBIUS_API_KEY sur le VPS.
Branche feat/lot-l1-token-factory depuis la base indiquée par ton environnement (main sinon). Une PR vers main, corps = gabarit REGLES § 3. Ne merge pas.
Interdits : un chiffre produit par un LLM (le filtre reste) ; une clé dans le diff ; un appel LLM depuis le navigateur ; retirer une surface visible.
Si quelque chose bloque (id de modèle inconnu, format de réponse), décide seul, garde les ids surchargeables par variable d'environnement, note-le dans la PR. Quand tu as fini : numéro de PR, compteurs, captures, ce que tu n'as pas fait.
```

<!-- LOT id="M" title="Crédits carte et citations" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot M » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot M — Crédits carte et citations.
Objectif : une seule mention Esri, fournisseurs nommés une fois avec un lien chacun, OpenStreetMap lié ; dans le briefing chaque source citée est un lien et rien n'est dit deux fois.
Fichiers à ouvrir (seulement) : src/layers/styles.js (TILE_ATTRIBUTION, l. 12), src/engine/iciBriefing.js (rg -n "function sourceSentence|function legSentence|Polaire chargée|climatologySentence"), src/engine/briefingLinks.js (entityLinks), src/engine/iciBriefing.test.js, src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) TILE_ATTRIBUTION = « Tuiles © <a href="https://www.esri.com/">Esri</a> · données Esri, <a href="https://www.here.com/">HERE</a>, <a href="https://www.garmin.com/">Garmin</a>, © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> » (la mention HERE/Garmin est obligatoire dans les conditions Esri : on la garde, liée, une fois) ; 2) sourceSentence : table nom de source → URL (Open-Meteo, NOAA/RTOFS, EMODnet, GEBCO, Copernicus Marine, Marine Regions/VLIZ, OpenStreetMap, douane.gouv.fr, CDSE) et rendu en liens par segmentBriefing ; 3) dédoublonner : « Polaire chargée » une seule fois (ligne d'étape), la climatologie une seule fois (bandeau OU briefing).
Tests : iciBriefing.test.js — chaque source connue produit un lien ; aucune phrase dupliquée dans un briefing complet ; styles.test.js (créer) — l'attribution contient exactement une fois « Esri » comme lien et quatre <a>. npm test, vite build.
Recette (spec e2e/lots/m-credits.spec.js, captures docs/recette/lot-m/) : le contrôle d'attribution Leaflet contient 4 liens et une seule occurrence de « Esri » en texte de lien ; le briefing à La Rochelle contient au moins un lien de source (data-testid="briefing" a > 0). Captures 01-attribution, 02-briefing.
Branche fix/lot-m-credits-citations depuis la base indiquée (main sinon). Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une surface visible ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="N" title="Panneau gauche stable" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot N » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot N — Panneau gauche stable.
Objectif : le chat journal de bord en haut du panneau gauche ; les blocs à contenu variable (carte NOW, sac ici, récit) ont une hauteur fixe avec défilement interne : rien ne saute quand le sac change.
Fichiers à ouvrir (seulement) : src/components/Sidebar.jsx (ordre des blocs, l. 275–360), src/components/LogbookChat.jsx, src/components/MomentCards.jsx (variante inline), src/index.css (règles .light-mode à conserver), src/components/LogbookChat.test.js.
Étapes : 1) ordre : Berry card → chat (hauteur fixe 168 px, historique défilant) → étape (SimulationPanel) → carte NOW (max-h-40, défilement) → FREE → fiche d'escale → sac ici (h-64, défilement, placeholder « Le sac se remplit… » à la même hauteur) → récit (h-56, défilement) → journal ; 2) hauteurs en variables CSS --sim-box-h-chat/-now/-ici/-story dans index.css ; 3) mode clair : mêmes règles. Aucun bloc retiré, aucun texte retiré.
Tests : test de contrat Sidebar.layout.test.js (créer) qui lit Sidebar.jsx et vérifie l'ordre des composants (LogbookChat avant MomentNowCard) et la présence des classes de hauteur ; LogbookChat.test.js passe. npm test, vite build.
Recette (spec e2e/lots/n-panneau.spec.js, captures docs/recette/lot-n/) : la boîte du chat (data-testid="logbook-chat") a le même getBoundingClientRect().top avant et 6 s après le début d'une lecture en Suivre ; captures 01-sombre, 02-clair (activer le mode clair via le bouton thème existant).
Branche feat/lot-n-panneau-gauche depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer/cacher une surface visible sur main (la fiche d'escale, le journal, le FREE restent) ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="O" title="Barre film compacte, un seul bouton son" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot O » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot O — Barre film compacte, un seul bouton son.
Objectif : une seule rangée de commandes : Masquer la barre · Écouter · [Suivre l'expédition | Simulation] · Revoir l'expédition ; à droite les commandes de lecture compactes ; un seul bouton son (le 🔊 du replay disparaît, « Écouter » pilote replay.voice).
Fichiers à ouvrir (seulement) : src/components/SimulationFilmBar.jsx (rangée du haut l. 110–160, rangée du bas l. 226–330), src/components/ListenButton.jsx, src/hooks/useReplay.js (voice), src/hooks/useReplay.test.js, src/components/filmBarLayout.test.js (créer si absent), src/App.jsx PAR EXTRAIT : rg -n "replayControls|speechText=" src/App.jsx.
Étapes : 1) supprimer le bouton replay-voice ; replay.voice suit l'état du bouton Écouter (pendant un replay il lit le paragraphe courant, hors replay le récit + briefing comme aujourd'hui) ; 2) rangée unique à gauche (Masquer la barre en Cinéma seulement · Écouter · Suivre/Simulation · Revoir), à droite lecture/pause, prochaine escale, Stop auto, vitesses (pilules text-[9px]) ; 3) data-testid conservés (mode-follow, mode-sim, replay-start, listen) ; 4) tests de contrat mis à jour sans les affaiblir.
Tests : useReplay.test.js, filmBarLayout.test.js (une seule occurrence de ListenButton dans la barre, plus de replay-voice). npm test, vite build, npm run e2e (fumée).
Recette (spec e2e/lots/o-barre.spec.js, captures docs/recette/lot-o/) : en Suivre et en Simulation, la barre contient exactement un bouton data-testid="listen" et aucun data-testid="replay-voice" ; hauteur de la barre ≤ 96 px ; captures 01-suivre, 02-simulation.
Branche feat/lot-o-barre-film depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une commande existante autre que le doublon son ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="F1" title="Film 2 min 30 : chapitrage et cinématique menée par la voix" plan="docs/PLAN_FILM_REVOIR_EXPEDITION.md" size="M" deps="O" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 0, § 1, § 4 et le « Lot F1 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot O (barre film compacte) est dans ta base.

Lot F1 — Chapitrage et cinématique menée par la voix.
Objectif : « Revoir l'expédition » dure 150 s (option 180 s), la voix mène et le bateau suit (onboundary/onend), zoom fixe par chapitre, bateau au tiers avant de l'écran, sous-titre du chapitre dans la barre film.
Fichiers à ouvrir (seulement) : src/engine/replay.js (+ replay.test.js), src/hooks/useReplay.js (+ test), src/hooks/useReplayVoice.js, src/utils/speech.js, src/components/SimulationFilmBar.jsx (sous-titres + sélecteur 2:30 / 3:00), src/map/MapSceneController.js PAR EXTRAIT : rg -n "syncCamera|zoomForRemaining|replay" src/map/MapSceneController.js, src/i18n/fr.js, src/i18n/en.js, src/map/MapSceneMarkers.test.js.
Étapes : 1) replay.js : filmPlan({chapters, targetSeconds}) répartit les secondes au prorata des caractères et expose timeAt(chapterIdx, charIdx) (monotone) ; les chapitres = jambes entre escales du récit existant (expeditionStory) en attendant F3 ; 2) useReplay : boucle requestAnimationFrame ; onboundary → charIdx → temps rejoué ; onend → chapitre suivant ; sans voix : avance linéaire sur targetSeconds ; 3) calibrage : après le chapitre 1, rate ajusté dans [0,9 ; 1,25] pour retomber sur la cible ± 8 s ; 4) caméra : zoom fixe par chapitre (getBoundsZoom de la jambe, borné [3 ; 7]), transition uniquement au changement de chapitre (flyTo 1,2 s), setView(bateau, zoom, {animate:false}) à 30 Hz avec offset au tiers avant, jamais zoomForRemaining ni fitBounds en cours de chapitre, drapeaux non recalculés pendant le film ; 5) barre film : sous-titre du chapitre courant (data-testid="film-subtitle"), sélecteur 2:30 / 3:00 (data-testid="film-duration"), progression ; 6) fin : le bateau arrive à sa position live, le mode Suivre reprend.
Tests : replay.test.js (répartition des 150 s, timeAt monotone, calibrage borné) ; MapSceneMarkers.test.js : contrat « aucun flyTo hors changement de chapitre » (compter les appels via un faux map). npm test, vite build, npm run e2e.
Recette (spec e2e/lots/f1-film.spec.js, captures docs/recette/lot-f1/) : mode Suivre → replay-start ; en mode sans voix (speechSynthesis absent en headless), la durée mesurée entre le début et l'événement de fin est entre 142 et 158 s ; le zoom (window.__naviguideScene.map.getZoom()) ne varie pas de plus de 0,01 sur 4 s en milieu de chapitre ; film-subtitle contient « Saint-Maur » au départ. Captures 01-depart, 02-atlantique, 03-arrivee.
Branche feat/lot-f1-film-voix depuis la base indiquée (la branche du lot O si elle n'est pas mergée). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une surface visible (le replay actuel reste accessible : c'est lui qu'on améliore) ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="F2" title="Événements climo et sci, enrichissement wx et stop" plan="docs/PLAN_FILM_REVOIR_EXPEDITION.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 2.1 et le « Lot F2 » (texte intégral), et docs/audits/CALCULS_ETAT_DE_L_ART.md ligne 19 (seuils WMO). Tu travailles dans naviguide-simulator/.

Lot F2 — Événements « changement de régime » (climo) et « station croisée » (sci) ; wx et stop enrichis.
Fichiers à ouvrir (seulement) : server/voyage_journal.py (+ server/tests/test_voyage_journal.py), server/ici_warm.py (route_events_from_pearls), server/escale_api.py (section tourisme en cache), src/engine/journalFormat.js (+ test), src/engine/momentCard.js (cardFromJournalEntry) (+ test), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) kind climo : entre deux perles consécutives, rose dominante qui tourne de ≥ 90°, ou passage alizés → calmes (vent moyen < 8 kn sur 2 perles), ou entrée/sortie de saison cyclonique (données climo.rose / climo.cyclones déjà dans la perle) ; 2) kind sci : station/campagne à ≤ 10 nm de la route, une fois par entité ; 3) wx : ajouter durée (heures) et max ; seuils : vent ≥ 34 kn (force 8) ; mer : « forte » Hs ≥ 2,5 m durable (≥ 6 h), « très forte » ≥ 4 m — champ level ; 4) stop : jours à quai + 2 lieux remarquables depuis la fiche d'escale (section tourisme) si en cache ; 5) chaque entrée porte t, lat, lon, kind, title, facts (seuls nombres autorisés dans les textes), entity (liens) ; journalFormat et cardFromJournalEntry rendent les nouveaux kinds (icônes, textes fr/en) — ajout, rien retiré ; 6) GET /voyage/official/journal?kinds=climo,sci fonctionne (paramètre kinds existant).
Tests : test_voyage_journal.py — rose 120° → climo ; deux perles calmes → climo « calmes » ; station à 6 nm → sci une seule fois ; wx avec durée/max et level ; JS : journalFormat.test.js et momentCard.test.js pour les nouveaux kinds. pytest, npm test, vite build.
Recette (spec e2e/lots/f2-evenements.spec.js, captures docs/recette/lot-f2/) : le fil de cartes en Suivre contient au moins un élément data-kind="climo" ou data-kind="sci" (si l'API tourne ; sinon le spec vérifie que le rendu d'une entrée climo de fixture via momentCard donne un titre non vide — test unitaire). Capture 01-regime.
Branche feat/lot-f2-evenements depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; vidéo ; secret ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="L2" title="Basculer récit, chat et fiche d'escale sur la cascade Token Factory" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="S" deps="L1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 2 et le « Lot L2 ». Tu travailles dans naviguide-simulator/. Le lot L1 (cascade Token Factory, budget, source) est dans ta base.

Lot L2 — Basculer U1 (récit ici), U4 (chat journal de bord), U5 (paragraphe de fiche d'escale) sur cascade_text(tier=…) de L1.
Fichiers à ouvrir (seulement) : server/story_cache.py, server/logbook_chat.py, server/escale_api.py, leurs tests (test_story_cache.py, test_logbook_chat.py, test_escale_api.py), src/components/LogbookChat.jsx et src/components/EscaleSheet.jsx PAR EXTRAIT (afficher la source sous le texte, data-testid="chat-source" / "escale-source" — ajout).
Étapes : 1) récit : tier "write" ; chat : tier "write" (ou "fast" si la question fait moins de 80 caractères et ne contient pas « pourquoi/comment/why/how ») ; fiche d'escale : tier "fast" ; 2) chaque réponse conserve source et le client l'affiche ; 3) filter_numbers inchangé ; 4) aucun appel supplémentaire par rendu (test de contrat : aucun useEffect nouveau qui appelle /logbook/chat ou /escale sans action).
Tests : les trois fichiers de tests passent avec un faux Token Factory ; pytest, npm test, vite build.
Recette (aucun changement visible hors libellés de source) : trois parcours fixes (Suivre à Nouméa, Simulation La Rochelle → Ajaccio, Tracer Brisbane → SF) fonctionnent ; spec e2e/lots/l2-sources.spec.js : si data-testid="chat-source" existe après une question, il n'est pas vide ; capture 01-chat dans docs/recette/lot-l2/.
Branche feat/lot-l2-cascade-usages depuis la base indiquée (branche L1 si non mergée). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; clé dans le diff ; appel LLM depuis le navigateur ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="F3" title="Script du film : brut, sélection, version rédigée par Nemotron" plan="docs/PLAN_FILM_REVOIR_EXPEDITION.md" size="M" deps="F1,F2,L1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 2.2, § 2.3 et le « Lot F3 » (texte intégral), et docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 1 (U2, U3). Tu travailles dans naviguide-simulator/. Les lots F1, F2 et L1 sont dans ta base.

Lot F3 — Script du film : brut (règles), sélection des événements, version rédigée par Nemotron.
Fichiers à ouvrir (seulement) : src/engine/expeditionStory.js (+ test), nouveau server/film_script.py (+ server/tests/test_film_script.py), server/story_cache.py (namespace "film"), server/story_cascade.py (cascade_text, tiers), server/main.py (route GET /voyage/official/film?lang=fr&seconds=150), src/hooks/useReplay.js (consomme le plan), src/components/SimulationFilmBar.jsx (libellé source du récit + bascule brut/rédigé), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) candidats = journal (stop, zee, amp, poe, wx, climo, sci, note) ; sélection par règles : départ, escales (max 6), arrivée « aujourd'hui », puis par score wx > climo > sci > amp > zee > poe jusqu'à 6–9 événements, jamais deux à moins de 3 % du temps total ; option Nemotron (tier fast) qui renvoie les identifiants retenus + une raison, repli règles ; 2) script brut : chapitres = jambes entre escales, connecteurs en rotation (jamais deux fois le même d'affilée), phrases d'événement par gabarits, longueur ≤ 2 400 caractères (retirer les événements de score le plus bas d'abord) ; bilingue ; 3) version rédigée : Nemotron tier write reçoit le brut + les faits, doit garder tous les nombres/noms/dates, 2 300–2 500 caractères, balise [[ev:<id>]] au début de chaque phrase d'événement ; le serveur vérifie filter_numbers, présence de toutes les balises, longueur ; sinon repli brut ; cache SQLite (ns film, clé = hash journal + lang + seconds), régénéré au plus 1×/jour et à chaque nouvelle escale ; 4) réponse : {chapters:[{id,tA,tB,text,events:[{id,charIdx,card}]}], source, chars, targetSeconds} ; 5) useReplay consomme ce plan ; sans API il construit le brut en local (expeditionStory.js) ; 6) barre film : « Récit : Nemotron 3 Super · Token Factory » ou « règles » (data-testid="film-source"), bascule brut/rédigé (brut par défaut si la version rédigée n'est pas en cache).
Tests : Python — longueur bornée, toutes les balises présentes, aucun nombre nouveau (faux LLM qui triche → repli brut), cache, sélection déterministe ; JS — brut ≤ 2 400 caractères, connecteurs jamais répétés, événements ancrés à un charIdx valide. pytest, npm test, vite build.
Recette (spec e2e/lots/f3-script.spec.js, captures docs/recette/lot-f3/) : film-subtitle du chapitre 1 contient « Saint-Maur » et « La Rochelle » ; film-source non vide ; capture 01-chapitre-1, 02-source.
Branche feat/lot-f3-script-film depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : un nombre produit par un LLM (le filtre doit le prouver par un test) ; clé dans le diff ; vidéo ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="F4" title="Bulle événement sur le bateau" plan="docs/PLAN_FILM_REVOIR_EXPEDITION.md" size="S" deps="F1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 3 et le « Lot F4 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot F1 est dans ta base.

Lot F4 — Bulle événement ancrée au bateau.
Fichiers à ouvrir (seulement) : nouveau src/components/EventBubble.jsx (+ EventBubble.test.js, test de contrat), src/map/MapSceneController.js PAR EXTRAIT : rg -n "syncMarkers|mainMarker|bindPopup|L.popup" src/map/MapSceneController.js, src/hooks/useReplay.js (cartes du chapitre → bulle), src/components/MomentCards.jsx (hors film : une carte NOW d'alerte/décision ouvre aussi la bulle — ajout), src/index.css (mode clair), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) EventBubble rendu dans un L.popup ancré au marqueur principal (autoPan:false, closeButton:false, className "event-bubble", largeur 280 px), setLatLng à chaque déplacement du marqueur ; 2) contenu : icône du kind, titre ≤ 40 caractères, 1–2 lignes de faits, chips, CardLinks ; 3) apparition/disparition en fondu 200 ms, minimum 3 s, une seule bulle à la fois, Échap la ferme sans arrêter le film ; 4) pendant le film, la bulle s'ouvre quand la lecture franchit charIdx de l'événement (mode sans voix : à la date de l'événement) ; la carte NOW de la sidebar affiche le même texte (rien retiré) ; 5) hors film : une carte NOW alert/decision ouvre la même bulle ; la sidebar reste inchangée.
Tests : contrat — la bulle suit le marqueur (popup.getLatLng() = bateau après update), une seule bulle, minimum 3 s (faux timers). npm test, vite build, npm run e2e.
Recette (spec e2e/lots/f4-bulle.spec.js, captures docs/recette/lot-f4/) : pendant le film (mode sans voix), data-testid="event-bubble" devient visible ≤ 1 s après la date du premier événement ; sa position écran est à moins de 60 px du marqueur du bateau ; captures 01-bulle-escale, 02-bulle-coup-de-vent (ou le premier kind disponible).
Branche feat/lot-f4-bulle-evenement depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer la carte NOW de la sidebar ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="L3" title="Juge de vérité (Ultra) + fiche Gold revérifiée par Tavily" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="M" deps="L1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 1 (U6, U11), § 3 et le « Lot L3 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot L1 est dans ta base.

Lot L3 — Juge de vérité : Tavily relit la page officielle d'une fiche PoE Gold, Nemotron 3 Ultra dit ce qui n'est plus soutenu ; la carte barre (jamais ne supprime).
Fichiers à ouvrir (seulement) : nouveau server/tavily_client.py (+ test avec faux serveur : POST https://api.tavily.com/extract et /search, clé TAVILY_API_KEY), nouveau server/truth_judge.py (+ test), server/ici_engine.py PAR EXTRAIT : rg -n "poe|zee" server/ici_engine.py (déclencheur : entrée en ZEE / ouverture d'une fiche PoE), server/pearl_store.py (cache 7 jours ns "truth"), src/components/MomentCards.jsx (badge data-testid="truth-badge", texte barré pour unsupported — ajout), src/engine/momentCard.js (champ truth dans la carte), src/i18n/fr.js, src/i18n/en.js, server/.env.example.
Étapes : 1) tavily_client.extract(urls, depth="basic") et search(query, topic, days, max_results, include_domains) avec compteur de crédits dans llm_budget (1 crédit/appel) ; 2) truth_judge.judge(fiche, extrait) : Ultra (tier judge) reçoit les faits de la fiche et l'extrait (≤ 6 k tokens), renvoie JSON {supported:[…], unsupported:[…], stale_hint:str|null} — aucun chiffre nouveau (filter_numbers sur stale_hint) ; extrait vide → {status:"unverifiable"} ; budget judge au plafond → pas d'appel ; 3) déclencheur : une fois par (ZEE, URL) et par 7 jours, quand le bateau entre dans la ZEE ou qu'une fiche PoE s'ouvre ; résultat attaché à la carte (truth: {status, checkedAt, unsupported}) ; 4) UI : badge « Vérifié le <date> · Tavily + Nemotron 3 Ultra » / « Non revérifiable » ; affirmations unsupported en texte barré, jamais supprimées.
Tests : faux Tavily + faux Ultra : une affirmation non soutenue → présente dans unsupported ; extrait vide → unverifiable ; budget au plafond → aucun appel réseau ; cache 7 jours ; filter_numbers. pytest, npm test, vite build.
Recette (spec e2e/lots/l3-juge.spec.js, captures docs/recette/lot-l3/) : rendu d'une carte de fixture avec truth.unsupported non vide → data-testid="truth-badge" visible et un élément <s> ou .line-through présent ; capture 01-badge. Dans la PR : la recette réelle (Simulation, entrée dans la ZEE Martinique) demande TAVILY_API_KEY et NEBIUS_API_KEY sur le VPS.
Branche feat/lot-l3-juge-verite depuis la base indiquée (branche L1 si non mergée). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : supprimer un texte de fiche (barrer seulement) ; chiffre LLM ; clé dans le diff ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="F5" title="Film en anglais et plein écran film" plan="docs/PLAN_FILM_REVOIR_EXPEDITION.md" size="S" deps="F3,F4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_FILM_REVOIR_EXPEDITION.md « Lot F5 » et docs/HACKATHON_DEVPOST_SOUMISSION.md § 2 (plan de la vidéo). Tu travailles dans naviguide-simulator/. Les lots F3 et F4 sont dans ta base.

Lot F5 — Version anglaise du film et « plein écran film ».
Fichiers à ouvrir (seulement) : src/i18n/en.js, src/i18n/fr.js, server/film_script.py (lang=en : mêmes règles, gabarits anglais), src/components/SimulationFilmBar.jsx (bouton « Plein écran film » data-testid="film-fullscreen" qui masque les sidebars par CSS et les rend au clic ou à Échap — SANS les démonter), src/App.jsx PAR EXTRAIT : rg -n "Sidebar |ToolsSidebar " src/App.jsx, src/index.css.
Étapes : 1) en langue EN, GET /voyage/official/film?lang=en renvoie un script anglais (gabarits en.js côté client pour le brut local) ; la voix utilise une voix en-* ; 2) plein écran film : classe .film-fullscreen sur le conteneur qui cache les deux sidebars (display:none) et agrandit la carte ; Échap ou le bouton rend tout ; l'état n'est pas persistant ; 3) i18n complet.
Tests : test de contrat filmBarLayout : présence du bouton ; test i18n : chaque clé fr a sa clé en (script existant ou à créer : i18n.parity.test.js). npm test, pytest, vite build, npm run e2e.
Recette (spec e2e/lots/f5-anglais.spec.js, captures docs/recette/lot-f5/) : bascule EN → film-subtitle du chapitre 1 contient « Saint-Maur » et « La Rochelle » et un mot anglais (« left » ou « departed ») ; clic film-fullscreen → les sidebars ne sont plus visibles, Échap → visibles ; capture 01-plein-ecran (c'est le cadre de la vidéo de soumission).
Branche feat/lot-f5-film-anglais depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : démonter/retirer les sidebars (masquage CSS réversible seulement) ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="S" title="Route dessinée transpacifique" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot S » (texte intégral), et docs/audits/CALCULS_ETAT_DE_L_ART.md ligne 22. Tu travailles dans naviguide-simulator/.

Lot S — Route dessinée Brisbane → San Francisco directe dans le Pacifique.
Cause racine : longitude dépliée (236,84°) envoyée à GET /route puis à searoute qui attend [−180, 180].
Fichiers à ouvrir (seulement) : src/hooks/useRouteDrawing.js (fetchSegment), src/utils/geo.js (ajouter wrapLon(lon) et unwrapPath(coords, refLon)), server/main.py (get_route, l. 230–250), server/route_engine.py (searoute_with_exact_end l. 546–620, _normalize_antimeridian), server/tests/test_route_engine.py, src/utils/geo.test.js.
Étapes : 1) serveur : get_route replie start_lon/end_lon dans [−180, 180] (formule ((lon + 540) % 360) − 180) avant searoute_with_exact_end, et redéplie la réponse relativement au point de départ (aucun saut de 360° entre deux sommets) ; 2) client : fetchSegment replie aussi et redéplie le résultat relativement au point précédent ; 3) fixture Brisbane (−27,0 ; 153,4) → San Francisco (37,7 ; −122,4) : aucun sommet au nord de 50° N, aucun sur terre, longueur < 7 500 nm.
Tests : test_route_engine.py (fixture ci-dessus, si searoute est installé ; sinon test du repli/dépli seul) ; geo.test.js (wrapLon(236.84) = −123.16 ; unwrapPath continu). pytest, npm test, vite build.
Recette (spec e2e/lots/s-transpacifique.spec.js, captures docs/recette/lot-s/) : mode Tracer ma route, deux clics (est de l'Australie, San Francisco) → la polyligne dessinée n'a aucun sommet au nord de 50° N (lire window.__naviguideScene ou le GeoJSON exposé) ; le résumé affiche une distance entre 6 000 et 7 500 nm si l'API tourne ; capture 01-pacifique.
Branche fix/lot-s-route-transpacifique depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; vidéo ; secret ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="T" title="Sac ici() et cartes pour la route dessinée" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="S" deps="S" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot T » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot S (wrapLon) est dans ta base.

Lot T — Après « Terminer », le briefing raconte le sac autour du bateau de la route dessinée ; aucune carte ne cite un lieu à plus de 60 nm.
Fichiers à ouvrir (seulement) : src/hooks/useIciDossier.js (rg -n "q.set\(" src/hooks/useIciDossier.js), src/hooks/useIciAlong.js, src/engine/momentCard.js (boucle FREE l. 320–330 et 485–530), src/utils/geo.js (wrapLon du lot S), tests momentCard.test.js, useIciDossier.test.js (créer si absent), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) replier lon dans toute requête /ici, /weather/forecast, /api/climatology/point ; 2) useIciAlong échantillonne la route courante (customRoute) et non l'officielle quand une route est dessinée — vérifier et corriger ; 3) boucle FREE : une carte dont l'entité est à plus de FREE_STALE_NM (60 nm) du bateau sort de la boucle ; 4) le message « Les couches Blue Intelligence n'ont pas répondu, seules les ZEE et les ports WPI sont conservés » ne s'affiche que si sources.bi === "unavailable", pas pour une perle mince.
Tests : momentCard.test.js — carte à 90 nm exclue, à 30 nm gardée ; useIciDossier.test.js — l'URL /ici porte une longitude dans [−180, 180] pour un point à 236,84°. npm test, vite build.
Recette (spec e2e/lots/t-sac-route.spec.js, captures docs/recette/lot-t/) : route dessinée au large de la Mauritanie (deux clics) → après Terminer, data-testid="briefing" ne contient pas « Bourgenay » et, si l'API tourne, contient « Mauritanie » ou « Mauritania » ; capture 01-mauritanie.
Branche fix/lot-t-sac-route-dessinee depuis la base indiquée (branche S si non mergée). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; vidéo ; secret ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="C2" title="Hindcast : le vent et la mer que le bateau a vraiment rencontrés" plan="docs/PLAN_AUDIT_CALCULS.md" size="L" deps="P2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 0 (A1–A3), § 2 et le « Lot C2 » (texte intégral), et docs/audits/CALCULS_ETAT_DE_L_ART.md (lignes 6, 9, compléments hindcast). Tu travailles dans naviguide-simulator/. Le lot P2 est dans ta base.

Lot C2 — Horloge à trois régimes : hindcast (passé), prévision (7 j), climatologie (au-delà) ; position d'aujourd'hui = somme des vitesses réelles. TOUTES les sources sont utilisées ensemble : Open-Meteo ET Copernicus Marine (décision du porteur), fusionnées par médiane.
Fichiers à ouvrir (seulement) : nouveau server/hindcast.py (+ server/tests/test_hindcast.py avec faux serveurs HTTP et faux copernicusmarine), server/copernicus/getWind.py, getWave.py, getCurrent.py (ajouter un paramètre d'intervalle de temps start/end sans casser l'appel actuel), server/forecast_blend.py, server/voyage_clock.py (build_voyage_clock, l. 206–356), server/voyage_api.py (_fill_forecast → _fill_hindcast_then_forecast, tâche quotidienne), server/pearl_store.py (ns "hindcast"), server/voyage_journal.py (wx depuis le hindcast : durée, max), server/tests/test_voyage_clock.py, docs/REGLES_PARAMETRES.md, src/components/SimulationFilmBar.jsx PAR EXTRAIT (afficher le régime : data-testid="clock-regime" — ajout), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) hindcast.series(lat, lon, day) interroge TOUTES les sources : (a) Open-Meteo Historical Forecast API (historical-forecast-api.open-meteo.com/v1/forecast, hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m, wind_speed_unit=kn) ; (b) Open-Meteo Historical Weather API / ERA5 (archive-api.open-meteo.com/v1/archive, mêmes variables) avec correction des vents forts ERA5_STRONG_WIND_FACTOR = 1,05 au-dessus de 15 m/s ; (c) Open-Meteo Marine API (marine-api.open-meteo.com/v1/marine, hourly=wave_height,wave_direction,wave_period,ocean_current_velocity,ocean_current_direction) ; (d) Copernicus WIND_GLO_PHY_L4_NRT_012_004, dataset cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H (eastward_wind, northward_wind → vitesse en kn × 1,943844, direction « de ») ; (e) Copernicus GLOBAL_ANALYSISFORECAST_WAV_001_027, dataset cmems_mod_glo_wav_anfc_0.083deg_PT3H-i (VHM0, VMDR « de », VTM02) ; (f) Copernicus GLOBAL_ANALYSISFORECAST_PHY_001_024, dataset cmems_mod_glo_phy_anfc_0.083deg_PT1H-m (uo, vo → vitesse, direction « vers » = atan2(uo, vo)). Fusion par variable et par heure : médiane des sources disponibles, sources: [...], spread = max − min ; une source en panne manque simplement ; aucune source → champ vide (jamais inventé). Cache SQLite par (point, produit, jour) — jamais retéléchargé ; appels séquentiels (Copernicus 1 subset par point et par dataset sur ± 2 jours) ; 2) build_voyage_clock : pas d'intégration ≤ 30 nm ou 1 h (sous-découper les segments longs), vent lu à mi-pas, régime dans chaque sommet (regime ∈ hindcast/forecast/climatology, sources, spread) ; 3) forecast_blend : le fondu 7 → 10 j est relatif à MAINTENANT (heure du calcul), pas à t0 ; passé = hindcast ; 4) le premier calcul complet tourne en tâche de fond au démarrage (≈ 40 min la première fois) ; l'horloge climatologique reste servie en attendant, marquée kind "climatology" ; 5) GET /voyage/official/regimes : portions de route par régime ; 6) barre film : « 7,4 kn · hindcast · 3 sources ±1,5 kn » ; à quai « à quai · hindcast » ; 7) REGLES_PARAMETRES.md : toutes les constantes nouvelles, avec source ; identifiants COPERNICUS_USERNAME / COPERNICUS_PASSWORD déjà lus par server/main.py.
Tests : faux Open-Meteo et faux copernicusmarine : deux jours de vent connus → position attendue à 1 nm près ; médiane de trois sources ; une source en panne → deux sources et spread calculé ; à quai 0 kn ; changement de régime à now ; cache : deuxième appel sans réseau ; tout en panne → climatologie marquée ; correction ERA5 appliquée seulement au-dessus de 15 m/s et seulement sur ERA5 ; conventions : uo = 1, vo = 0 → courant vers 90°. pytest, npm test, vite build.
Recette (spec e2e/lots/c2-hindcast.spec.js, captures docs/recette/lot-c2/) : si l'API tourne, data-testid="clock-regime" contient « hindcast » et « sources » en Suivre ; la PR donne la position du bateau d'aujourd'hui avant/après (nm d'écart) et, pour trois points de la route, les valeurs de chaque source et la médiane retenue ; capture 01-regime. Sans API : le spec vérifie seulement que la barre film s'affiche (fumée).
Branche feat/lot-c2-hindcast depuis la base indiquée. PR vers main, gabarit REGLES § 3 ; la PR détaille l'écart de position avant/après. Ne merge pas.
Interdits : chiffre LLM ; secret ; vidéo ; retirer une surface. Décide seul en cas de blocage (ex. variable Open-Meteo indisponible → la laisser vide, jamais inventer) et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="C3" title="Une seule vitesse, partout" plan="docs/PLAN_AUDIT_CALCULS.md" size="M" deps="C2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 0 (A2), § 2 et le « Lot C3 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot C2 est dans ta base.

Lot C3 — Une seule vitesse partout (barre film, chat, bulle « Aujourd'hui », fiche), avec son régime ; route parcourue teintée par régime.
Fichiers à ouvrir (seulement) : src/hooks/useExpeditionSpeed.js, src/engine/voyageClock.js (sampleClockAtHours : vitesse du pas courant), src/App.jsx PAR EXTRAIT : rg -n "expeditionSpeed|boatKnots" src/App.jsx, server/logbook_chat.py (contexte : même vitesse + régime), src/components/SimulationFilmBar.jsx (régime), src/layers/useRouteLayer.js (teinte par régime — ajout, la route reste), src/i18n/fr.js, src/i18n/en.js, tests associés.
Étapes : 1) en Suivre, la vitesse affichée = sample.speedKnots de l'horloge (0 à quai) ; useExpeditionSpeed ne calcule plus une vitesse concurrente en Suivre (il reste utile en Simulation pour la vitesse prévue) ; 2) chat : même vitesse et régime ; 3) route parcourue teintée (hindcast / prévision / climatologie) avec une légende (data-testid="regime-legend") — ajout.
Tests : contrat : la barre et le contexte du chat lisent la même source ; voyageClock.test.js : vitesse du pas courant ; npm test, pytest, vite build.
Recette (spec e2e/lots/c3-vitesse.spec.js, captures docs/recette/lot-c3/) : en Suivre, le nombre de kn de data-testid="clock-line" est égal à celui renvoyé par le contexte du chat (poser la question « À quelle vitesse va le bateau ? » et comparer la valeur, ou lire window.__naviguideDebug.speed si tu l'exposes) ; à quai « à quai » partout ; capture 01-legende.
Branche feat/lot-c3-une-vitesse depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; secret ; vidéo ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="U" title="Zoom réactif" plan="docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md § 0 et le « Lot U » (texte intégral), et docs/PROFIL_BUILD_PROD_2026-09-19.md (méthode de profil). Tu travailles dans naviguide-simulator/.

Lot U — Zoom réactif : le zoom à la molette répond immédiatement ; aucune tâche > 50 ms pendant un zoom.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT : rg -n "syncWaypoints|onMoveEnd|syncDynamicWorldCopies|zoomend|zoomanim" src/map/MapSceneController.js, src/hooks/useMarkerOffsets.js, src/layers/useToggleLayers.js (WMS ZEE), src/map/MapSceneMarkers.test.js.
Étapes : 1) profiler un zoom (10 s de molette) sur le build de prod avec Playwright + CDP (Profiler.start/stop) et noter les trois postes dans docs/audits/PROFIL_ZOOM_<date>.md ; 2) mesures : copies-monde des drapeaux seulement si la vue touche ±180° ; pas de recalcul d'offsets pendant l'animation de zoom (attendre zoomend + 250 ms) ; preferCanvas:true pour les polylignes si sans régression visuelle ; réutiliser les divIcon ; ne pas relancer /ici ni le récit sur moveend ; 3) re-profiler et consigner avant/après.
Tests : MapSceneMarkers.test.js (contrat : pas de recalcul pendant zoomanim) ; npm test, vite build, npm run e2e.
Recette (spec e2e/lots/u-zoom.spec.js, captures docs/recette/lot-u/) : 10 crans de molette sur l'Atlantique ; la plus longue tâche mesurée (PerformanceObserver longtask ou profil CDP) est < 50 ms ; capture 01-zoom ; le profil avant/après est joint à la PR.
Branche perf/lot-u-zoom depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une couche ou un marqueur ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="L4" title="Veille Tavily par escale + enrichissement science / projet" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="M" deps="L1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 1 (U10, U12), § 3 et le « Lot L4 » (texte intégral). Tu travailles dans naviguide-simulator/. Les lots L1 et L3 (tavily_client) sont dans ta base ; si tavily_client.py n'existe pas encore, crée-le selon L3.

Lot L4 — Veille Tavily par escale (carte FREE datée) et enrichissement science / projet (phrase sourcée).
Fichiers à ouvrir (seulement) : server/tavily_client.py, server/ici_warm.py (tâche quotidienne J-10 → J+2 par escale), server/voyage_journal.py (kind news, daté, avec URL), src/engine/momentCard.js (carte FREE news), src/engine/journalFormat.js, tests associés, src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) search ciblée par escale : "<port> marina OR port OR harbour" + (notice OR avis OR travaux OR fermeture OR event), topic news, 7 jours, 5 résultats, include_domains officiels quand connus ; 1 crédit par escale et par jour ; 2) Nemotron tier fast résume en une phrase sans chiffre nouveau (filter_numbers), cite l'URL ; carte FREE datée « <Escale> · veille du <date> : … (source) », expire à J+2 ; 3) science / projet : extract de la page officielle de l'entité (une fois, cache définitif ns "enrich"), phrase sourcée ajoutée à la perle riche et à la fiche.
Tests : faux Tavily + faux Nemotron : une veille → une entrée news avec URL ; deux jours → une seule recherche par jour ; extrait science → phrase attachée à l'entité une seule fois ; budget crédits respecté. pytest, npm test, vite build.
Recette (spec e2e/lots/l4-veille.spec.js, captures docs/recette/lot-l4/) : rendu d'une carte news de fixture → data-kind="news" avec un lien ; capture 01-veille. Dans la PR : la recette réelle demande TAVILY_API_KEY.
Branche feat/lot-l4-veille-tavily depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; clé dans le diff ; appel Tavily depuis le navigateur ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="L5" title="Revue de plan commentée + conseil de route expliqué" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="S" deps="L1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 1 (U7, U8) et le « Lot L5 ». Tu travailles dans naviguide-simulator/. Le lot L1 est dans ta base.

Lot L5 — Sous le tableau de revue de plan : paragraphe « Ce que je changerais » (Nemotron tier write, cache, source affichée) ; après un recalcul de route avec contraintes skipper : phrase d'explication (tier fast) dont les nombres sont ceux du recalcul.
Fichiers à ouvrir (seulement) : server/plan_review.py (+ test), server/voyage_api.py (recompute) (+ test), src/components/PlanReview.jsx (paragraphe data-testid="plan-review-comment" — ajout), src/hooks/useVirtualVessel.js (explication data-testid="route-advice-text" — ajout), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) plan_review : après le tableau, cascade_text(tier="write") reçoit les lignes du tableau (faits) et écrit ≤ 4 phrases ; cache par hash du tableau ; source affichée ; 2) recompute : différence entre la route officielle et la route recalculée (distance, écart max, points évités) calculée par règles → phrase par tier fast qui reprend ces nombres, filter_numbers ; 3) UI : ajout sous le tableau et sous le résultat de recalcul.
Tests : faux LLM ; aucun nombre nouveau ; cache ; pytest, npm test, vite build.
Recette (spec e2e/lots/l5-revue.spec.js, captures docs/recette/lot-l5/) : la revue de plan affiche data-testid="plan-review-comment" (texte ou « règles ») ; capture 01-commentaire.
Branche feat/lot-l5-revue-commentee depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; clé ; retirer une surface ; vidéo. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="C4" title="Courant, polaire de vagues, efficacité de croisière, climatologie échantillonnée, pas d'isochrone" plan="docs/PLAN_AUDIT_CALCULS.md" size="M" deps="C2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 0 (A3, A4, A7) et le « Lot C4 » (texte intégral), et docs/audits/CALCULS_ETAT_DE_L_ART.md (lignes 4, 7, 8, 10, 21). Tu travailles dans naviguide-simulator/. Le lot C2 est dans ta base.

Lot C4 — Courant additionné, polaire de vagues, POLAR_EFFICIENCY, climatologie échantillonnée, pas d'isochrone.
Fichiers à ouvrir (seulement) : server/voyage_clock.py (polar_boat_speed, boucle d'intégration), server/isochrone.py (_boat_speed, run_leg_isochrone : time_step_h, heading_step_deg, max_steps), server/climatology_atlas.py (p25/p50/p75 de la rose), src/engine/skipperOrders.js (planningSpeedFor), server/tests/test_voyage_clock.py, server/tests/test_isochrone_leg.py, src/engine/skipperOrders.test.js, docs/REGLES_PARAMETRES.md.
Étapes : 1) courant : SOG = projection sur la route de (vecteur polaire + vecteur courant uo/vo) ; 2) polaire de vagues : v × f(Hs, angle relatif houle/cap) ; f = 1 jusqu'à 1,5 m, linéaire jusqu'à 0,6 à 4 m par mer de face et 0,85 par mer arrière, plafonné ; remplace WAVE_NOGO_DT_FACTOR ; 3) POLAR_EFFICIENCY (défaut 0,85, variable d'environnement) appliqué partout où la polaire sert (horloge, planification, conseil de route) ; limites d'allure (près ≥ 40° TWA, portant ≤ 170°) dans le conseil de route seulement ; 4) climatologie : trois tirages p25/p50/p75 de la rose → temps moyen ; 5) isochrones : pas 3 h en haute mer, 1 h à moins de 60 nm d'une côte (is_path_clear), max_steps recalculé ; 6) REGLES_PARAMETRES.md : chaque constante avec sa source (CALCULS_ETAT_DE_L_ART).
Tests : courant 2 kn dans l'axe → SOG = polaire × 0,85 + 2 ; contre → − 2 ; Hs 2,4 → 2,6 m : facteur continu (pas de saut) ; mer de face plus pénalisante que mer arrière ; climatologie : temps p25/p50/p75 moyenné ≥ temps à la moyenne ; isochrone : pas 1 h à 30 nm d'une côte ; parité JS/Python de planningSpeedFor avec POLAR_EFFICIENCY. pytest, npm test, vite build.
Recette (aucun changement visible sauf les nombres) : la PR donne l'avant/après des ETA par étape (tableau de la revue de plan) ; spec e2e/lots/c4-eta.spec.js : la revue de plan s'affiche et chaque ligne a une date ; capture 01-revue dans docs/recette/lot-c4/.
Branche feat/lot-c4-calculs-mer depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; secret ; retirer une surface ; vidéo. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="C5" title="Cahier des calculs et tests croisés client / serveur" plan="docs/PLAN_AUDIT_CALCULS.md" size="S" deps="C4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 1 et le « Lot C5 », et docs/audits/CALCULS_ETAT_DE_L_ART.md. Tu travailles dans naviguide-simulator/. Le lot C4 est dans ta base.

Lot C5 — Cahier des calculs (une fiche par ligne du § 1 : formule, unités, source, test qui la protège) et tests croisés client / serveur.
Fichiers à ouvrir (seulement) : nouveau docs/audits/CALCULS.md, src/utils/geo.test.js, nouveau server/tests/test_polar_parity.py et src/engine/polar.parity.test.js (mêmes 20 cas TWA × TWS depuis une fixture JSON partagée server/tests/fixtures/polar_cases.json → même vitesse à 0,05 kn), server/weather_pipeline.py (+ test : unités m/s → kn ; convention courant « vers » : uo = 1, vo = 0 → 90° ; vent et vagues « de »), src/utils/geo.js.
Étapes : 1) écrire le cahier (25 fiches, courtes) ; 2) fixture partagée et deux tests de parité ; 3) tests d'unités et de conventions ; 4) geo.test.js : Saint-Maur → La Rochelle ≈ 190 nm ± 5 (orthodromie), cardinaux du cap.
Tests : tout vert (pytest, npm test, vite build).
Recette (aucun changement visible) : spec de fumée existant ; la PR liste les 25 fiches.
Branche docs/lot-c5-cahier-calculs depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : modifier un calcul dans ce lot (documenter et tester seulement ; si un test révèle un écart, l'écrire dans la PR sans le corriger) ; secret ; vidéo. Fin : PR, compteurs, reste à faire.
```

<!-- LOT id="C7" title="Conventions paramétrées et repli déclaré" plan="docs/PLAN_AUDIT_CALCULS.md" size="S" deps="C5" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 1 (lignes 5, 15, 16, 18) et le « Lot C7 », et docs/audits/CALCULS_ETAT_DE_L_ART.md (mêmes lignes). Tu travailles dans naviguide-simulator/. Le lot C5 est dans ta base.

Lot C7 — Conventions paramétrées et repli déclaré : jours à quai par escale (table sourcée), tronçon route et saut avion documentés, repli de vitesse sans polaire déclaré à l'écran, distance film expliquée.
Fichiers à ouvrir (seulement) : server/voyage_clock.py (port_days_for l. 24–34, LAND_CALENDAR_HOURS, AIR_CALENDAR_HOURS, MIN_KNOTS, _emit), nouveau server/data/port_days.json, server/climatology_zones.py (boat_speed_from_wind), server/voyage_api.py (exposer params dans GET /voyage/official), src/components/ToolsSidebar.jsx PAR EXTRAIT (rg -n "filmNm|routeDistanceNm" src/components/ToolsSidebar.jsx : info-bulle), src/components/SimulationFilmBar.jsx PAR EXTRAIT (libellé « (repli sans polaire) » — ajout), src/i18n/fr.js, src/i18n/en.js, docs/REGLES_PARAMETRES.md, server/tests/test_voyage_clock.py.
Étapes : 1) port_days.json : {"default": 3, "source": "programme Berry-Mappemonde 2026", "stops": {"Saint-Maur": 0, …}} lu par port_days_for (les valeurs actuelles deviennent la table ; ne change aucune valeur sans source — laisse le défaut) ; 2) chaque sommet de l'horloge porte basis ∈ {"polar","fallback"} ; boat_speed_from_wind n'est appelé que sans polaire ; 3) GET /voyage/official renvoie params: {landHours, airHours, minKnots, portDaysDefault, polarEfficiency si présent} ; 4) UI : info-bulle sur la distance (« distance du film : saut avion exclu ; distance totale : … ») et libellé « (repli sans polaire) » quand basis === "fallback" ; 5) REGLES_PARAMETRES.md : une ligne par constante avec sa source.
Tests : table lue, défaut 3, Saint-Maur 0 ; sans polaire → basis "fallback" ; params présents dans la réponse. pytest, npm test, vite build.
Recette (spec e2e/lots/c7-conventions.spec.js, captures docs/recette/lot-c7/) : survol de la distance dans data-testid="route-summary" → attribut title non vide ; capture 01-infobulle. La PR liste les constantes et leur source.
Branche feat/lot-c7-conventions depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : changer une valeur de convention sans source écrite ; chiffre LLM ; secret ; vidéo ; retirer une surface. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="C6" title="ETA probabiliste par ensembles" plan="docs/PLAN_AUDIT_CALCULS.md" size="M" deps="C4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_AUDIT_CALCULS.md § 1 (ligne 9) et le « Lot C6 », et docs/audits/CALCULS_ETAT_DE_L_ART.md (ligne 9 et complément « Ensembles »). Tu travailles dans naviguide-simulator/. Les lots C2 et C4 sont dans ta base.

Lot C6 — Au-delà de 7 jours, l'arrivée est une fourchette (p10–p90) calculée sur les membres d'ensemble, pas une date unique.
Fichiers à ouvrir (seulement) : nouveau server/ensemble_eta.py (+ server/tests/test_ensemble_eta.py avec faux serveur HTTP), server/hindcast.py (réutiliser le client HTTP et le cache), server/voyage_api.py (GET /voyage/official/eta?stop=<nom> → {p10, p50, p90, members, source, computedAt}), src/components/EscaleLegend.jsx (fourchette sous la date — ajout), src/components/PlanReview.jsx (colonne ou ligne « p10–p90 » — ajout), src/hooks/usePlanReview.js, src/i18n/fr.js, src/i18n/en.js, docs/REGLES_PARAMETRES.md.
Étapes : 1) Open-Meteo Ensemble API : ensemble-api.open-meteo.com/v1/ensemble?latitude&longitude&models=gfs_seamless,ecmwf_ifs025&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&forecast_days=15 — une requête par point de la jambe courante (pas ≤ 60 nm), membres en colonnes (wind_speed_10m_member01…) ; cache 6 h ; 2) pour chaque membre : intégration de la jambe depuis la position actuelle avec la polaire × POLAR_EFFICIENCY, courant et polaire de vagues du lot C4 (climatologie médiane au-delà de 15 jours) ; 3) dates d'arrivée → p10, p50, p90 (quantiles empiriques), members = nombre de membres utilisés ; 4) UI : « entre le 11 et le 14 (p10–p90, 80 membres) » sous la date de la prochaine escale et dans la revue de plan ; sans ensemble disponible → rien d'affiché (jamais inventé) ; 5) REGLES_PARAMETRES.md : modèles, forecast_days, cache.
Tests : 30 membres identiques → p10 = p50 = p90 ; membres dispersés → p10 < p50 < p90 ; API en panne → réponse {members: 0} et aucune fourchette ; cache 6 h. pytest, npm test, vite build.
Recette (spec e2e/lots/c6-eta.spec.js, captures docs/recette/lot-c6/) : si l'API tourne, data-testid="eta-range" présent sous la prochaine escale et contient « p10 » ou « entre » ; capture 01-fourchette. Sans API : fumée.
Branche feat/lot-c6-eta-ensembles depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; secret ; vidéo ; retirer une surface (la date actuelle reste, la fourchette s'ajoute). Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="L6" title="Traduction des textes rédigés + mémoire sémantique (option)" plan="docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md" size="S" deps="L2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md § 1 (U9, U13) et le « Lot L6 ». Tu travailles dans naviguide-simulator/. Le lot L2 est dans ta base.

Lot L6 — En langue EN, les textes rédigés (récit ici, fiche d'escale, script du film si présent) sont traduits par Nemotron tier fast (cache, source affichée) ; option : mémoire sémantique du journal pour le chat.
Fichiers à ouvrir (seulement) : server/story_cascade.py (translate(text, lang) via cascade_text tier fast, filter_numbers), server/story_cache.py (clé avec lang), server/escale_api.py, server/logbook_chat.py (option : recherche d'entrées wx similaires par mots-clés d'abord ; embeddings Qwen/Qwen3-Embedding-8B seulement si NAVIGUIDE_EMBEDDINGS=1), tests associés, src/i18n/en.js.
Étapes : 1) translate : garde nombres, noms, dates ; source « Nemotron 3.5 Lightning · Token Factory » ; 2) le client demande lang=en et affiche la source ; 3) option mémoire : la question « avons-nous déjà eu plus de 35 nœuds ? » cite l'entrée wx du journal (les faits), sans souvenir inventé.
Tests : faux LLM ; aucun nombre nouveau ; cache par lang ; pytest, npm test, vite build.
Recette (spec e2e/lots/l6-anglais.spec.js, captures docs/recette/lot-l6/) : langue EN → data-testid="story-source" présent et non vide ; capture 01-en.
Branche feat/lot-l6-traduction depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre LLM ; clé ; retirer une surface ; vidéo. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G0" title="Éprouvette globe MapLibre et décision A/B" plan="docs/PLAN_GLOBE_3D.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md (v2, en entier : § 0 à § 3, Lot G0). Tu travailles dans naviguide-simulator/. RÈGLE ABSOLUE : Leaflet reste ; tu ne modifies aucun fichier de src/map/, src/layers/, src/components/ dans ce lot.

Lot G0 — Éprouvette hors application : naviguide-simulator/globe-spike.html (page Vite multi-page, non déployée) avec MapLibre GL JS 6 (npm i maplibre-gl@^6 ; import * as maplibregl from 'maplibre-gl' ; setWorkerUrl selon la doc Installation/Vite) : projection globe dans le style, fond raster sombre (même URL que src/layers/styles.js), WMS ZEE (même URL que useToggleLayers.js), route officielle GET /voyage/official (longitudes dépliées), marqueur HTML catamaran qui avance le long de la route, flyTo, sky.atmosphere-blend.
Mesures à consigner dans docs/audits/GLOBE_SPIKE.md : FPS moyen (requestAnimationFrame sur 10 s) au zoom 2 et 5 ; poids ajouté au bundle (vite build --mode spike ou taille de maplibre-gl.mjs gzip) ; temps de chargement des polygones ZEE VLIZ en GeoJSON brut (public/data ou export) et, si tippecanoe est disponible, en PMTiles (sinon écrire la commande à lancer) ; continuité de la route au Pacifique (capture) ; comportement de getZoom sous inclinaison.
Critères go : ≥ 30 FPS sur MacBook, route continue, ZEE < 3 s. Écris la recommandation A (onglet Globe dans la même app) ou B (deuxième application) avec les arguments du plan.
Tests : npx vite build inchangé pour l'app principale ; npm test vert ; la page spike n'entre pas dans la CI e2e.
Recette : docs/audits/GLOBE_SPIKE.md + 3 captures JPEG dans docs/recette/lot-g0/ (01-globe, 02-pacifique, 03-zee) prises par un spec Playwright e2e/lots/g0-spike.spec.js qui ouvre globe-spike.html (préciser la commande de lancement dans la PR).
Branche spike/lot-g0-globe-maplibre depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; ajouter maplibre-gl au bundle principal (import dynamique ou page séparée seulement) ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, recommandation A/B.
```

<!-- LOT id="G1" title="Onglet Carte / Globe, fond, attribution, caméra" plan="docs/PLAN_GLOBE_3D.md" size="M" deps="G0" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md § 0–§ 2 et le « Lot G1 », et docs/audits/GLOBE_SPIKE.md (décision du porteur ; si elle n'y est pas, option A). Tu travailles dans naviguide-simulator/. RÈGLE ABSOLUE : Leaflet reste la carte et reste monté ; le globe est une deuxième vue.

Lot G1 — Onglet Carte / Globe.
Fichiers : nouveaux src/globe/GlobeScene.jsx, src/globe/GlobeSceneController.js, src/globe/globeStyle.js, src/globe/GlobeToggle.jsx (+ tests de contrat GlobeScene.test.js) ; src/App.jsx PAR EXTRAIT : rg -n "MapScene" src/App.jsx (un seul ajout : montage conditionnel lazy de GlobeScene à côté de MapScene, même objet scene ; MapScene reste monté et masqué par CSS quand view === "globe") ; src/index.css ; src/i18n/fr.js, src/i18n/en.js ; src/layers/styles.js EN LECTURE SEULE (réutiliser les URL et l'attribution).
Étapes : 1) maplibre-gl@^6 en dépendance, import dynamique (import()) pour ne pas alourdir le bundle par défaut ; setWorkerUrl ; 2) style : projection globe, fonds sombre/clair (mêmes URL), attribution avec les liens du lot M, sky, light ; 3) GlobeSceneController : create/destroy, setCamera/flyTo/easeTo, resize ; expose window.__naviguideGlobe ; 4) GlobeToggle : onglet au-dessus de la zone carte (data-testid="view-carte" / "view-globe"), préférence mémorisée (localStorage), ?view=globe ; défaut Carte ; 5) mode clair.
Tests : contrat : App.jsx contient toujours <MapScene ; GlobeScene n'est importé que dynamiquement ; npm test, vite build (taille du bundle principal inchangée ± 5 ko), npm run e2e (fumée inchangée).
Recette (spec e2e/lots/g1-globe.spec.js, captures docs/recette/lot-g1/) : onglet Globe → window.__naviguideGlobe.getProjection().type === "globe" et l'attribution contient 4 liens ; onglet Carte → capture identique à main (comparer avec la fumée) ; captures 01-globe, 02-carte.
Branche feat/lot-g1-onglet-globe depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : modifier src/map/* ou src/layers/* (hors lecture) ; démonter Leaflet ; changer le défaut ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G2" title="Route, bateau, escales, avion, sillage et caméra sur le globe" plan="docs/PLAN_GLOBE_3D.md" size="M" deps="G1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md § 1–§ 2 et le « Lot G2 ». Tu travailles dans naviguide-simulator/src/globe/ (et rien d'autre, hors i18n et tests). Le lot G1 est dans ta base.

Lot G2 — Sur le globe : route faite / à venir (GeoJSON, longitudes dépliées), marqueurs HTML (catamaran, avion, drapeaux d'escale — un exemplaire chacun, réutiliser les composants CatamaranMarker/PlaneMarker via un portal), sillage, saut avion en arc, caméra qui suit en Suivre (easeTo continu), même comportement de pause que Leaflet.
Constat de la revue du 23 sept. (lot RD2) : sur Leaflet, le rond de point était rendu ~5 px à côté de son lat/lon (icône 24×24 ancrée [12,12] pour un rond de 10 px). Étape ajoutée : sur le globe, chaque marqueur de point (escale, point de tracé) est ancré EXACTEMENT sur son lat/lon (ancre au centre du symbole) ; test de contrat : la position écran du marqueur correspond au project() de son lat/lon, au pixel près.
Fichiers : src/globe/layers/route.js, boat.js, stops.js, wake.js ; src/globe/GlobeSceneController.js ; tests de contrat ; src/i18n si besoin. Lecture seule : src/map/MapSceneController.js (pour copier la logique de scene → couches).
Tests : contrat : route source mise à jour quand scene.progress change ; marqueur suit sample ; npm test, vite build, npm run e2e.
Recette (spec e2e/lots/g2-route.spec.js, captures docs/recette/lot-g2/) : Globe + Suivre à Nouméa : marqueur bateau visible, route dessinée ; Simulation : le centre du globe suit le bateau (deux lectures de getCenter espacées de 3 s différentes et proches du bateau) ; capture 01-noumea, 02-pacifique (Papeete → Mata-Utu continue).
Branche feat/lot-g2-globe-route depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G3" title="Couches BI, ZEE en PMTiles, fiches sur le globe" plan="docs/PLAN_GLOBE_3D.md" size="M" deps="G2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md § 1 et le « Lot G3 ». Tu travailles dans naviguide-simulator/src/globe/ et infra/tiles/. Le lot G2 est dans ta base.

Lot G3 — Sur le globe : ports, PoE, AMP, science, projets, balisage (sources GeoJSON depuis les mêmes hooks que Leaflet : lire useToggleLayers.js en lecture seule pour les URL et les couleurs), ZEE en PMTiles (script infra/tiles/build_zee_pmtiles.sh avec tippecanoe, sortie servie par nginx sous /tiles/zee.pmtiles avec Accept-Ranges ; conf nginx dans infra/vps/naviguide/nginx-simulator.conf — ajout d'un location), plugin pmtiles côté client ; clic → mêmes fiches (mêmes callbacks onFocus/onEscaleSheet que Leaflet).
Fichiers : src/globe/layers/bi.js, zee.js ; src/globe/GlobeSceneController.js ; infra/tiles/build_zee_pmtiles.sh ; infra/vps/naviguide/nginx-simulator.conf ; tests de contrat.
Tests : contrat : chaque calque coché ajoute une couche MapLibre ; décoché la retire ; npm test, vite build, npm run e2e.
Recette (spec e2e/lots/g3-couches.spec.js, captures docs/recette/lot-g3/) : Globe, Calques → cocher ZEE, ports : window.__naviguideGlobe.getLayer('zee-fill') et 'ports' existent ; clic sur un port (si l'API tourne) ouvre la fiche ; captures 01-couches.
Branche feat/lot-g3-globe-couches depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; vidéo ; secret. Décide seul en cas de blocage (ex. tippecanoe absent : documenter la commande, servir le GeoJSON simplifié en attendant) et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G4" title="GRIB et climatologie en symboles sur le globe" plan="docs/PLAN_GLOBE_3D.md" size="M" deps="G3" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md § 1 (couches custom → symboles) et le « Lot G4 ». Tu travailles dans naviguide-simulator/src/globe/. Le lot G3 est dans ta base.

Lot G4 — Flèches/barbules GRIB et roses climatologiques en couches symbol : icônes générées par canvas (réutiliser src/utils/gribSymbols.js et src/layers/climatologyPaint.js EN LECTURE pour les dessins) → map.addImage ; rotation icon-rotate par donnée ; mêmes chiffres que la popup satellite. Pas de couche WebGL custom.
Fichiers : src/globe/layers/grib.js, climatology.js ; src/globe/icons.js ; tests.
Tests : contrat : pour un vent de 20 kn du 270°, l'icône choisie et la rotation correspondent à celles de Leaflet (fonction partagée) ; npm test, vite build.
Recette (spec e2e/lots/g4-grib.spec.js, captures docs/recette/lot-g4/) : Globe + Simulation, GRIB visible autour du bateau ; roses au zoom monde ; captures 01-grib-globe et, via ?view=carte, 01-grib-carte (même instant, comparer visuellement dans la PR).
Branche feat/lot-g4-globe-grib depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G5" title="Popups, bulle événement et tracer ma route sur le globe" plan="docs/PLAN_GLOBE_3D.md" size="M" deps="G4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md et le « Lot G5 », et docs/PLAN_FILM_REVOIR_EXPEDITION.md § 3 (bulle). Tu travailles dans naviguide-simulator/src/globe/. Le lot G4 est dans ta base ; si F4 (EventBubble) est dans ta base, réutilise le composant, sinon prévois le point d'ancrage.

Lot G5 — Popup satellite (Vent / Vagues / Courants, mêmes onglets et chiffres) ancrée (maplibregl.Popup.setLngLat), bulle événement ancrée au marqueur bateau, mode Tracer ma route par clics (mêmes callbacks drawing.add/undo/finish que Leaflet), résultat searoute affiché en ligne (longitudes dépliées).
Constat de la revue du 23 sept. (lot RD1) : sur Leaflet, le clic route ne répondait plus (copies du monde non normalisées) et des clics carte ouvraient le panneau gauche — jamais demandé. Étapes ajoutées : sur le globe, un clic sur la route (hors jambes avion) ouvre le pop-up Copernicus à toutes les longitudes (normaliser modulo 360 si le globe déplie les longitudes) ; AUCUN clic sur la carte ou sur un marqueur n'ouvre un panneau latéral (le clic drapeau remplit la section Ici seulement si le panneau est déjà ouvert, parité RD1) ; test de contrat sur les deux comportements.
Fichiers : src/globe/popups.js, src/globe/drawing.js, src/globe/GlobeSceneController.js, tests.
Tests : contrat : un clic en mode dessin appelle drawing.add avec une longitude repliée dans [−180, 180] ; npm test, vite build.
Recette (spec e2e/lots/g5-popups.spec.js, captures docs/recette/lot-g5/) : Globe, clic sur la mer → popup avec trois onglets ; Tracer : Brisbane → SF, ligne dans le Pacifique ; captures 01-popup, 02-trace.
Branche feat/lot-g5-globe-popups depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G6" title="Le film sur le globe" plan="docs/PLAN_GLOBE_3D.md" size="S" deps="G5,F1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md « Lot G6 » et docs/PLAN_FILM_REVOIR_EXPEDITION.md § 4. Tu travailles dans naviguide-simulator/src/globe/. Les lots G5 et F1 sont dans ta base.

Lot G6 — Caméra du film sur le globe : easeTo 30 Hz, altitude (zoom) constante par chapitre, pitch 25–35°, orbite douce (bearing +2°/s) pendant les bulles longues ; le plan de film (useReplay) pilote les deux vues par le même état.
Fichiers : src/globe/camera.js, src/globe/GlobeSceneController.js, src/hooks/useReplay.js PAR EXTRAIT (émettre l'état caméra pour la vue active), tests.
Tests : contrat : aucun flyTo hors changement de chapitre sur le globe ; npm test, vite build, npm run e2e.
Recette (spec e2e/lots/g6-film-globe.spec.js, captures docs/recette/lot-g6/) : Globe + Suivre + Revoir : zoom (window.__naviguideGlobe.getZoom()) stable sur 4 s en milieu de chapitre ; bulle visible ; captures 01-film-globe, 02-bulle-globe.
Branche feat/lot-g6-film-globe depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : toucher à Leaflet ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="G7" title="Parité et tests sur les deux vues" plan="docs/PLAN_GLOBE_3D.md" size="S" deps="G6" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_GLOBE_3D.md « Lot G7 ». Tu travailles dans naviguide-simulator/. Le lot G6 est dans ta base.

Lot G7 — Parité : liste de contrôle docs/audits/GLOBE_PARITE.md (toutes les surfaces du plancher main : disponibles en Globe ? oui/non/écart) ; le spec de fumée e2e/smoke.spec.js est joué deux fois (paramétré par ?view=carte et ?view=globe) sans dupliquer le code ; le défaut reste Carte.
Fichiers : docs/audits/GLOBE_PARITE.md, e2e/smoke.spec.js, playwright.config.js (projets ou paramètre), .github/workflows/ci.yml (le job simulator-e2e joue les deux).
Tests : npm run e2e vert pour les deux vues ; npm test, vite build.
Recette (aucun changement visible) : la PR joint la liste de parité et le rapport Playwright.
Branche chore/lot-g7-parite-globe depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : changer le défaut Carte ; toucher à Leaflet ; vidéo ; secret. Fin : PR, compteurs, reste à faire.
```

### Nuit 2 — corrections de la revue du 21 septembre (R1 → R13)

Socle commun rappelé dans chaque prompt : la rubrique « Recette » de la PR est
**visuelle seulement** (« ouvre, clique, tu dois voir »), rangée par écran ;
**rien de superflu à l'écran** (REGLES § 1) ; les captures sont référencées par
leur URL complète sur la branche.

<!-- LOT id="R1" title="Nettoyage : textes parasites, Esri une fois, polaire, bouton mort, bascule grisée" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (surtout § 1 « rien de superflu à l'écran » et § 4), puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R1 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot R1 — Nettoyage.
Objectif : plus une phrase d'explication dans l'interface ; « Esri » une seule fois dans les crédits carte ; « Polaires chargées » sans nom de bateau ; le bouton « remettre le chiffre du profil » marche ; les pilules brut / rédigé sont grisées pendant le film.
Fichiers à ouvrir (seulement) : src/i18n/fr.js et src/i18n/en.js (clés logbookChatHint, planReviewSummary, skipperExpertHint, polarLoaded), src/components/LogbookChat.jsx (l. 54), src/components/SkipperOrdersPanel.jsx (NumberRow l. 63-95, onReset l. 143 et 191, hint l. 300), src/components/ToolsSidebar.jsx (l. 314), src/layers/styles.js (l. 12) et src/layers/styles.test.js, src/components/SimulationFilmBar.jsx (l. 367 et 445 : disabled={Boolean(replay.active)}), src/App.jsx PAR EXTRAIT : rg -n "planReviewSummary" src/App.jsx.
Étapes : 1) supprimer les trois rendus (LogbookChat l. 54, App planReviewSummary, SkipperOrdersPanel l. 300) et les trois clés dans fr.js et en.js — rien à la place ; 2) ToolsSidebar l. 314 : le texte est t("polarLoaded") seul, sans « — <bateau> » ; 3) styles.js : TILE_ATTRIBUTION = « Tuiles © <a href="https://www.esri.com/">Esri</a> — <a href="https://www.here.com/">HERE</a>, <a href="https://www.garmin.com/">Garmin</a>, © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> » (quatre liens, le mot Esri UNE fois dans toute la chaîne) ; 4) NumberRow : le bouton de remise remet la valeur du profil courant (PROFILES[profil][champ]) et repasse forced à faux ; il est actif dès qu'une valeur est forcée ; vérifier que onReset est bien câblé pour chaque ligne (loa, et les autres chiffres) ; 5) bascule brut / rédigé : ajouter les classes disabled:opacity-30 disabled:cursor-not-allowed et aria-disabled pendant le film.
Tests : styles.test.js — exactement une occurrence de « Esri » dans TILE_ATTRIBUTION et quatre <a> ; SkipperOrdersPanel.test.js (créer si absent, node --test + rendu statique ou test de la fonction de remise) — après remise, la valeur est celle du profil et forced est faux ; test de contrat i18n (i18n/*.test.js) — les clés logbookChatHint, planReviewSummary, skipperExpertHint n'existent plus dans fr.js ni en.js. npm test, npx vite build.
Recette (visuelle, par écran) : Suivre — panneau gauche, Journal de bord : sous « Poser une question », aucune phrase d'explication. Panneau droit — Paramètres avancés → Chiffres : aucune phrase sous les chiffres ; modifier un chiffre puis cliquer le cercle : le chiffre du profil revient. Panneau droit — « Polaires chargées » puis « voir les polaires », sans « Léopard 46 ». Panneau droit — Revue du plan : aucune phrase « Par jambe : calendrier… » en tête. Carte — crédits en bas à droite : « Tuiles © Esri — HERE, Garmin, © OpenStreetMap contributors », Esri une seule fois. Revoir — pendant le film, brut / rédigé grisés. Spec e2e/lots/r1-nettoyage.spec.js : attribution avec une seule occurrence de « Esri » ; absence des trois textes ; captures docs/recette/lot-r1/01-credits.jpg, 02-chiffres.jpg référencées par URL complète sur ta branche.
Branche fix/lot-r1-nettoyage depuis la base indiquée (main sinon). Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une surface visible autre que ces trois phrases ; ajouter un texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le dans la PR. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R2" title="Barre film : une rangée, Masquer partout, Escale précédente" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="R1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu à l'écran », § 4), puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R2 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot R1 est dans ta base.

Lot R2 — Barre film : une seule rangée, « Masquer la barre » partout, « Escale précédente ».
Objectif : la rangée de légende des régimes (hindcast · prévision · climatologie) quitte la barre film ; « Masquer la barre » est disponible en Suivre et en Simulation, Cinéma ou non ; un bouton « Escale précédente » se tient à gauche de « Prochaine escale ».
Fichiers à ouvrir (seulement) : src/components/SimulationFilmBar.jsx (légende l. 225-245 regimeLegend ; hideBar l. 58/116 ; goToNextStop l. 474-479), src/components/filmBarLayout.test.js, src/components/PlanReview.jsx (une ligne de légende au-dessus du tableau), src/i18n/fr.js et src/i18n/en.js (clé previousEscale existante « Escale précédente » ; clockRegime*), src/App.jsx PAR EXTRAIT : rg -n "goToNextStop|onNextStop|hideBar|cinemaMode" src/App.jsx, et le hook qui place le curseur sur une escale (rg -n "nextStop|goToStop" src/hooks).
Étapes : 1) retirer la rangée de légende de la barre ; la légende devient l'info-bulle (attribut title, une phrase par couleur : hindcast = ce que le bateau a vraiment rencontré, prévision = 10 jours devant, climatologie = moyenne du mois au-delà) de la pilule de vitesse / régime déjà présente dans la barre, et une ligne discrète au-dessus du tableau de la Revue du plan ; hauteur de la barre ≤ 96 px (contrat du lot O) ; 2) « Masquer la barre » visible en Suivre ET en Simulation, Cinéma ou non ; « Afficher la barre » réapparaît au même endroit (bord bas) ; 3) bouton « Escale précédente » (data-testid="prev-stop", libellé t("previousEscale")) à gauche de « Prochaine escale », même style, grisé (disabled:opacity-30) sur la première escale ; il place le curseur sur l'escale précédente comme « Prochaine escale » sur la suivante (même mécanique, sens inverse).
Tests : filmBarLayout.test.js — plus de regimeLegend dans la barre, un prev-stop, hauteur ≤ 96 px ; test du hook : depuis la 2e escale, précédente → 1re ; depuis la 1re → inchangé et canPrev faux. npm test, npx vite build, npm run e2e -- e2e/lots/o-barre.spec.js (doit rester vert).
Recette (visuelle, par écran) : Simulation — barre film sur une seule rangée ; « Masquer la barre » présent ; le survol de la pilule de vitesse montre la légende des trois couleurs. Simulation — « Escale précédente » et « Prochaine escale » côte à côte ; à La Rochelle, « Escale précédente » est grisé ; après un clic sur « Prochaine escale », « Escale précédente » ramène à La Rochelle. Suivre — « Masquer la barre » présent hors Cinéma. Spec e2e/lots/r2-barre.spec.js ; captures docs/recette/lot-r2/01-simulation.jpg, 02-suivre.jpg (URL complète sur ta branche).
Branche fix/lot-r2-barre-film depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer une commande existante ; ajouter une rangée ou un texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul en cas de blocage et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R3" title="Revoir l'expédition : premier clic fiable, voix jusqu'au bout, caméra directe, voix EN audible" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R3 » (texte intégral), puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 0 et § 4 (contrat F1). Tu travailles dans naviguide-simulator/.

Lot R3 — Revoir l'expédition : fiable dès le premier clic.
Objectif : le premier clic sur « Revoir l'expédition » lance le film et la voix ; la voix ne s'arrête plus avant la fin ; la caméra se pose directement sur la première jambe (plus de détour vers l'Asie) ; en anglais la voix est compréhensible.
Fichiers à ouvrir (seulement) : src/hooks/useReplay.js (démarrage l. 150-170, fetch du script l. 106, boucle l. 228-310) et useReplay.test.js, src/hooks/useReplayVoice.js, src/utils/speak.js (voix l. 49-62) et speak.test.js (créer si absent), src/map/filmCamera.js et filmCamera.test.js, src/map/MapSceneController.js PAR EXTRAIT : rg -n "flyTo|fitBounds|filmCamera|syncCamera|zoomForRemaining" src/map/MapSceneController.js.
Diagnostic d'abord (note-le dans la PR, rubrique Cause racine) : reproduis le premier clic dans Chrome avec l'API locale (bash ensure-dev.sh) — hypothèses : speechSynthesis.getVoices() vide au premier appel → onend immédiat → tous les chapitres s'enchaînent en 2 s ; ou attente du script GET /voyage/official/film qui échoue puis film vide. Corrige la cause réelle, pas l'hypothèse.
Étapes : 1) démarrage : attendre l'événement voiceschanged (≤ 1 s) avant la première utterance ; si onend arrive sans aucun onboundary en < 500 ms, relancer l'utterance une fois, puis basculer en mode linéaire (sans voix) SANS terminer le film ; le film ne se termine que quand le dernier chapitre est joué ; 2) voix : découper chaque chapitre en phrases (≤ 200 caractères), enchaîner les utterances, charIdx global conservé pour onboundary ; keep-alive speechSynthesis.pause()/resume() toutes les 10 s pendant une utterance (Chrome coupe les longues) ; 3) caméra : le premier mouvement est celui du chapitre 1 (emprise de la jambe, zoom borné [3 ; 7]) ; aucun flyTo / fitBounds sur la route entière au lancement ni au « Retour au live » ; 4) voix par liste de préférence — en : Google UK English Female, Google US English, Samantha, Daniel, Karen, Moira, puis toute voix en-* ; fr : Google français, Thomas, Amélie, Audrey, puis fr-* ; rate 0,95 en anglais.
Tests : useReplay.test.js — scénario « onend immédiat sans boundary » : une relance, puis linéaire, film non terminé, dernier chapitre atteint à la durée cible ; speak.test.js — découpage en phrases ≤ 200 caractères, charIdx global strictement croissant, choix de voix par préférence sur une liste factice ; filmCamera.test.js — le premier mouvement est l'emprise du chapitre 1. npm test, npx vite build, npm run e2e -- e2e/lots/f1-film.spec.js (durée 142-158 s en linéaire : inchangé).
Recette (visuelle, par écran) : Revoir — en Suivre, PREMIER clic sur « Revoir l'expédition » après un rechargement de la page : la voix parle et le bateau part dès ce clic ; la caméra se pose directement sur la première jambe. Revoir — laisser le film entier : la voix ne s'arrête pas avant la fin ; le film finit sur la position du jour et Suivre reprend. Revoir — langue anglaise (bouton langue du panneau droit) : voix anglaise compréhensible, débit normal. Spec e2e/lots/r3-revoir.spec.js (sans voix en headless : vérifier qu'un premier clic après chargement lance bien le film et qu'il n'est pas terminé après 5 s) ; captures docs/recette/lot-r3/01-premier-clic.jpg, 02-chapitre-1.jpg (URL complète sur ta branche).
Branche fix/lot-r3-revoir-fiable depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : changer la durée cible (150 s / 180 s) ; retirer une surface visible ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R4" title="Film fluide : le bateau glisse, la caméra suit" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="M" deps="R3" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R4 » (texte intégral), puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 4. Tu travailles dans naviguide-simulator/. Le lot R3 est dans ta base.

Lot R4 — Film fluide.
Objectif : pendant une jambe, le bateau avance sans à-coups et la carte glisse avec lui — un film, pas une suite de captures. Aujourd'hui, avec la voix, le temps rejoué n'avance qu'à chaque onboundary (mot par mot) : la position est un escalier.
Fichiers à ouvrir (seulement) : src/hooks/useReplay.js (boucle l. 228-310, onVoiceBoundary l. 176-185) et useReplay.test.js, src/engine/replay.js (timeAt, position le long du trait) et replay.test.js, src/map/filmCamera.js et filmCamera.test.js, src/engine/filmWake.js, src/map/MapSceneController.js PAR EXTRAIT : rg -n "setView|filmCamera|replayBoat|wake" src/map/MapSceneController.js.
Étapes : 1) temps rejoué continu : à chaque frame (requestAnimationFrame), t += dt × vitesse nominale du chapitre (secondes du chapitre ÷ caractères, calibrage F1 conservé) ; chaque onboundary fournit une cible timeAt(charIdx) vers laquelle t se recale par interpolation en ≤ 300 ms ; jamais de saut arrière visible (si la cible est derrière, vitesse × 0,7 jusqu'à la rejoindre) ; 2) position du bateau = interpolation le long du trait, entre deux sommets consécutifs de la route (lat/lon dépliée), jamais « le sommet le plus proche » ; 3) caméra : setView(bateau au tiers avant, zoom fixe du chapitre, {animate:false}) à chaque frame ; déplacement par frame borné à 2 % de la largeur de l'écran hors changement de chapitre ; un seul flyTo (1,2 s) au changement de chapitre (F1) ; 4) sillage et marqueur bateau lisent la même position.
Tests : useReplay.test.js — faux timers, 60 frames entre deux boundaries → 60 positions strictement croissantes le long de la jambe, écart max entre deux frames < 1/30 de la jambe ; replay.test.js — positionAt(t) continue (limite à gauche = limite à droite aux sommets) ; filmCamera.test.js — déplacement par frame borné, un seul flyTo par changement de chapitre. npm test, npx vite build, npm run e2e -- e2e/lots/f1-film.spec.js (zoom stable sur 4 s : inchangé).
Recette (visuelle, par écran) : Revoir — pendant une jambe, le bateau avance sans à-coups ; la carte glisse avec lui ; le zoom ne change pas ; au changement de jambe, un seul mouvement de caméra. Spec e2e/lots/r4-fluide.spec.js (en linéaire : la position du marqueur bateau lue 10 fois en 2 s donne 10 valeurs différentes et monotones) ; captures docs/recette/lot-r4/01-jambe.jpg, 02-suivante.jpg (URL complète sur ta branche).
Branche fix/lot-r4-film-fluide depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : changer la durée cible ; zoomer pendant une jambe ; retirer une surface visible ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R5" title="Récit : connecteurs variés, kilomètres à terre" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R5 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot R5 — Récit sans « puis, puis, puis », kilomètres à terre.
Objectif : les paragraphes du récit et du script du film commencent par des connecteurs variés ; l'étape terrestre (Saint-Maur → La Rochelle) est comptée en kilomètres et en heures de route, pas en milles nautiques.
Fichiers à ouvrir (seulement) : src/engine/expeditionStory.js (l. 261 « Puis, le … » en dur ; liste de connecteurs l. 412) et expeditionStory.test.js, server/film_script.py (liste l. 26) et server/tests/test_film_script.py, src/engine/momentCard.js (carte « Escale » : distance de l'étape) et momentCard.test.js, src/utils/berryLegs.js PAR EXTRAIT : rg -n "land|terrestre|kind" src/utils/berryLegs.js, src/i18n/fr.js et en.js (unités).
Étapes : 1) expeditionStory.js : le connecteur du paragraphe i est connecteurs[i % n], jamais deux fois le même à la suite ; mettre à jour les chaînes attendues des tests (c'est voulu) ; 2) film_script.py : même règle pour le script du film ; 3) étape terrestre (jambe de type terre dans berryLegs) : distance en km (1 nm = 1,852 km, arrondi au km), durée en heures de route, libellé « par la route » — dans le récit ET dans la carte « Escale » de momentCard.js ; 4) fr.js / en.js : unités « km » / « h de route ».
Tests : expeditionStory.test.js — deux paragraphes consécutifs n'ont pas le même connecteur ; une étape terrestre donne « km » et pas « nm » ; momentCard.test.js — carte Escale à Saint-Maur en km ; test_film_script.py — connecteurs alternés. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle, par écran) : Suivre — panneau gauche, Récit de la traversée : les paragraphes commencent par des mots différents (« Puis », « Ensuite », « Plus loin »…), jamais trois « Puis » de suite. Simulation — curseur sur Saint-Maur : la carte « Escale » indique « … km par la route », pas de milles nautiques. Spec e2e/lots/r5-recit.spec.js ; capture docs/recette/lot-r5/01-recit.jpg (URL complète sur ta branche).
Branche fix/lot-r5-recit-connecteurs depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre produit par un LLM ; retirer une surface visible ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R6" title="Bulles sur le bateau : pendant le film seulement, événements importants, fermables" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="M" deps="R3" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R6 » (texte intégral), puis docs/PLAN_FILM_REVOIR_EXPEDITION.md « Lot F4 ». Tu travailles dans naviguide-simulator/. Le lot R3 est dans ta base.

Lot R6 — Bulles événement : pendant le film seulement, événements importants, croix.
Objectif : plus aucune bulle sur le bateau hors film (la bulle « balisage » à l'ouverture disparaît) ; pendant « Revoir l'expédition », une bulle ancrée au bateau apparaît à chaque événement important (escale, entrée de ZEE, alerte météo, AMP, station scientifique, changement de régime), une seule à la fois, fermable par une croix et Échap sans arrêter le film ; la carte NOW du panneau gauche montre le même texte.
Fichiers à ouvrir (seulement) : src/components/MomentCards.jsx (effet l. 113-118 : publication hors film — à supprimer) et MomentCards.test.js, src/components/eventBubble.js (pickFilmEvent l. 76, EventBubbleGate l. 105) et eventBubble.test.js, src/components/EventBubble.jsx (croix à ajouter) et EventBubble.test.js, src/hooks/useReplay.js PAR EXTRAIT (l. 270-295 : publication pendant le film), server/film_script.py (événements par chapitre) et server/tests/test_film_script.py, e2e/lots/f4-bulle.spec.js (à mettre à jour), src/i18n/fr.js et en.js.
Diagnostic d'abord : avec l'API locale, lis GET /voyage/official/film — si les chapitres n'ont pas de tableau events non vide, c'est la cause du « rien n'apparaît » : corrige côté serveur.
Étapes : 1) MomentCards.jsx : supprimer la publication dans la bulle hors film ; 2) film_script.py : chaque chapitre porte ses événements {charIdx, kind, title, fact, score} construits depuis le journal du voyage — arrivée/départ d'escale (score 3), entrée dans une ZEE (2), alerte vent ≥ seuil du skipper ou Hs ≥ 3 m (3), AMP à portée (1), station/campagne scientifique croisée (2), changement de régime (1) ; charIdx = position dans le texte du chapitre de la phrase qui en parle (ou proportionnelle à la date) ; 3) client : la bulle s'affiche pour tout événement de score ≥ 2, ou quand la somme des scores des événements non montrés depuis 20 s atteint 3 ; une seule bulle, ≥ 3 s, remplacée par la suivante (gate existante) ; 4) EventBubble.jsx : croix « × » (data-testid="event-bubble-close") ; croix et Échap ferment la bulle, le film continue ; 5) la carte NOW du panneau gauche affiche la même carte pendant le film.
Tests : eventBubble.test.js — seuil de score et somme sur 20 s ; EventBubble.test.js — la croix ferme ; MomentCards.test.js — aucune publication hors film ; test_film_script.py — chaque chapitre de mer du voyage officiel a ≥ 1 événement, scores dans {1,2,3}. npm test, .venv/bin/python -m pytest -q, npx vite build, npm run e2e -- e2e/lots/f4-bulle.spec.js (mis à jour : bulle pendant le film, aucune à l'ouverture).
Recette (visuelle, par écran) : Suivre — à l'ouverture, aucune bulle sur le bateau. Revoir — dans la première minute, une bulle ancrée au bateau apparaît (escale, ZEE, alerte…) ; la croix la ferme et le film continue ; une bulle suivante remplace la précédente ; jamais deux à la fois. Revoir — la carte NOW du panneau gauche montre le même texte que la bulle. Captures docs/recette/lot-r6/01-ouverture-sans-bulle.jpg, 02-bulle-film.jpg (URL complète sur ta branche).
Branche fix/lot-r6-bulles-film depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : bulle hors film ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R7" title="Fiche d'escale sur la carte, au clic sur le drapeau, sans Écouter" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R7 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot R7 — Fiche d'escale sur la carte.
Objectif : la fiche d'escale sort du panneau gauche ; elle s'ouvre en popup ancrée au drapeau de l'escale quand on clique le drapeau (et depuis la légende des escales), sans bouton Écouter, avec une croix.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT (l. 698-735 : marqueurs drapeaux waypointMarkers, clic l. 727-731 réservé au dessin ; rg -n "callbacks\." pour la liste des callbacks), src/map/MapSceneMarkers.test.js, src/components/EscaleSheet.jsx (ListenButton l. 5 et 122) et EscaleSheet.test.js, src/components/Sidebar.jsx (l. 405 : rendu EscaleSheet, props l. 260) et Sidebar.layout.test.js, src/components/EventBubble.jsx PAR EXTRAIT (attachEventBubble l. 134 : le motif « React dans une popup Leaflet ancrée à un marqueur »), src/components/LayerFichePopup.jsx (motif existant), src/hooks/useEscaleSheetState.js, src/App.jsx PAR EXTRAIT : rg -n "escaleStop|openEscaleSheet|closeEscaleSheet|onEscaleSheet|callbacks" src/App.jsx.
Étapes : 1) MapSceneController : hors mode dessin, le clic sur un drapeau appelle this.callbacks.onWaypointClick?.(point, index) ; App relie ce callback à openEscaleSheet(stop) ; 2) nouveau src/components/EscalePopup.jsx : popup Leaflet ancrée au drapeau de l'escale ouverte (comme attachEventBubble), contenu = EscaleSheet (mêmes data-testid escale-*), sans ListenButton, avec croix ; largeur ≤ 340 px, défilement interne au-delà de 260 px ; se ferme par la croix, Échap, ou clic sur un autre drapeau (qui ouvre le sien) ; 3) Sidebar.jsx : retirer le rendu de EscaleSheet ; 4) la légende des escales (bas de carte) ouvre la même popup (même état useEscaleSheetState) ; 5) fr.js / en.js : rien de nouveau.
Tests : MapSceneMarkers.test.js — clic drapeau hors dessin → onWaypointClick(point, index) ; en dessin → inchangé ; EscaleSheet.test.js — aucun ListenButton ; Sidebar.layout.test.js — plus d'EscaleSheet dans le panneau ; EscalePopup.test.js (créer) — contenu et croix. npm test, npx vite build.
Recette (visuelle, par écran) : Simulation — cliquer le drapeau d'Ajaccio : la fiche d'escale s'ouvre sur le drapeau ; pas de bouton Écouter ; la croix la ferme. Suivre — panneau gauche : plus de fiche d'escale ; la légende des escales (bas de carte) ouvre la même fiche sur la carte. Spec e2e/lots/r7-escale.spec.js : clic sur le drapeau d'Ajaccio → popup contenant « Ajaccio » ; captures docs/recette/lot-r7/01-popup.jpg (URL complète sur ta branche).
Branche fix/lot-r7-fiche-escale-carte depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer le contenu de la fiche (il change de place, pas de contenu) ; bouton Écouter ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R11" title="Fourchette d'arrivée lisible et jours de mer cohérents" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R11 » (texte intégral), puis docs/PLAN_AUDIT_CALCULS.md « Lot C6 ». Tu travailles dans naviguide-simulator/.

Lot R11 — Fourchette d'arrivée lisible, jours de mer cohérents.
Objectif : sous la prochaine escale et dans la Revue du plan, « arrivée entre le 31 oct. et le 4 nov. » (deux dates, rien d'autre : « p10–p90 » et « membres » passent en info-bulle) ; les jours de mer d'une jambe sont cohérents avec sa distance et la vitesse planifiée (aujourd'hui Nouméa → Dzaoudzi affiche « 4,5 jours de mer » pour 42 jours).
Fichiers à ouvrir (seulement) : src/hooks/usePlanReview.js (formatEtaRange) et usePlanReview.test.js, src/components/EscaleLegend.jsx (l. 77), src/components/PlanReview.jsx (l. 66), src/i18n/fr.js et en.js (clé etaRange), server/plan_review.py et server/tests/test_plan_review.py, server/voyage_api.py PAR EXTRAIT : rg -n "seaDays|sea_days|plan-review|/eta" server/voyage_api.py.
Étapes : 1) diagnostic : d'où vient « 4,5 jours de mer » (jours à quai ? jambe précédente ? mauvaise unité ?) — test Python sur le voyage officiel : seaDays de chaque jambe = distance ÷ vitesse planifiée ÷ 24, à ± 10 % ; corriger la source ; 2) formatEtaRange → « arrivée entre le {p10} et le {p90} » (dates courtes « 31 oct. »), le détail (p10–p90, n membres) dans title ; 3) Suivre (EscaleLegend) et Revue du plan (PlanReview) lisent la même valeur serveur, même arrondi.
Tests : usePlanReview.test.js — formatage fr/en ; test_plan_review.py — cohérence jours de mer / distance / vitesse sur toutes les jambes du voyage officiel. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle, par écran) : Suivre — sous la prochaine escale : « arrivée entre le … et le … » (deux dates, rien d'autre). Panneau droit — Revue du plan, jambe Nouméa → Dzaoudzi : la même fourchette et un nombre de jours de mer cohérent avec 42 jours à 8 nœuds. Spec e2e/lots/r11-eta.spec.js (sans API : passe ; avec API : les deux libellés sont identiques) ; capture docs/recette/lot-r11/01-eta.jpg (URL complète sur ta branche).
Branche fix/lot-r11-eta-lisible depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : chiffre produit par un LLM ; texte d'aide ; retirer une surface visible ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R12" title="Carte bornée aux pôles, zoom vérifié sur build de prod" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R12 » (texte intégral), puis docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md « Lot U ». Tu travailles dans naviguide-simulator/.

Lot R12 — Carte : limites de déplacement, zoom vérifié sur le build de prod.
Objectif : on ne peut plus tirer la carte au-delà des pôles (plus d'écran entièrement bleu) ; le zoom molette est vérifié fluide sur le build de prod, et corrigé s'il ne l'est pas.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT (l. 170-185 : options de la carte minZoom / worldCopyJump), src/map/MapSceneBoundary.test.js, e2e/lots/u-zoom.spec.js (existant, lot U) ; si un long task subsiste : le seul fichier de la couche fautive (nommé dans la PR).
Étapes : 1) maxBounds en latitude seulement : lat ∈ [−85 ; 85], longitude libre (les routes dépliées dépassent 180°), maxBoundsViscosity 1 ; 2) zoom : cd naviguide-simulator && bash ensure-dev.sh --prod (build de prod + preview sur :5174) puis mesurer au zoom molette sur l'Atlantique (Performance / PerformanceObserver longtask) ; si un long task > 50 ms subsiste, nommer la couche (GRIB, ZEE, sillage…) et différer son redessin à zoomend ; sinon écrire dans la PR « vérifié sur build de prod, aucun long task > 50 ms » avec la mesure.
Tests : MapSceneBoundary.test.js — options maxBounds / viscosity, longitude non bornée ; npm run e2e -- e2e/lots/u-zoom.spec.js sur le build de prod. npm test, npx vite build.
Recette (visuelle, par écran) : Suivre — tirer la carte vers le haut ou le bas au maximum : on ne dépasse pas les pôles, jamais un écran entièrement bleu. Suivre — zoom molette sur l'Atlantique : la carte suit tout de suite, sans saccade. Capture docs/recette/lot-r12/01-bord-nord.jpg (URL complète sur ta branche).
Branche fix/lot-r12-carte-bornes-zoom depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : borner la longitude ; retirer une couche ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R13" title="Redites : compter, puis supprimer" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md" size="S" deps="R1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu à l'écran »), puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md § 0 et le « R13 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot R1 est dans ta base.

Lot R13 — Redites : un outil qui compte, une première passe qui supprime.
Objectif : un libellé n'apparaît qu'une fois par écran ; le nom du bateau une fois (Paramètres avancés) ; « climatologie » et « Polaire » au plus une fois par écran.
Fichiers à ouvrir (seulement) : scripts/redites.mjs (créer), e2e/lots/r13-redites.spec.js (créer), src/i18n/fr.js et en.js, puis UNIQUEMENT les composants que le rapport désigne (les nommer dans la PR avant de les ouvrir).
Étapes : 1) scripts/redites.mjs (node, sans dépendance) : lit src/i18n/fr.js, liste les groupes de ≥ 2 mots (hors mots vides : le, la, de, du, des, et, à, en, un, une, sur, par, au, aux, pour) présents dans ≥ 2 valeurs, et les valeurs identiques sous deux clés ; sortie triée par fréquence, commande npm run redites ; 2) e2e/lots/r13-redites.spec.js : pour Suivre, Simulation, Tracer (deux clics au large) et le panneau droit ouvert, document.body.innerText → lignes (≥ 8 caractères) présentes ≥ 2 fois sur le même écran, écrites dans docs/recette/lot-r13/redites-<écran>.txt ; 3) supprimer les redites évidentes que le rapport révèle : même texte deux fois sur le même écran, « Léopard 46 » hors Paramètres avancés, « climatologie » et « Polaire » au-delà de la première occurrence par écran — garder la première occurrence, et lister chaque suppression (fichier, texte) dans la PR ; ne pas toucher aux textes qui portent une information différente.
Tests : npm test, npx vite build, PW_PORT=5199 npm run e2e -- e2e/lots/r13-redites.spec.js (le rapport est joint à la PR ; il doit être vide pour « même texte deux fois sur le même écran »).
Recette (visuelle, par écran) : Suivre, Simulation, Tracer — parcourir l'écran : aucun texte identique deux fois ; le nom du bateau une seule fois, dans Paramètres avancés. Captures docs/recette/lot-r13/01-suivre.jpg (URL complète sur ta branche).
Branche fix/lot-r13-redites depuis la base indiquée. Une PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : supprimer un texte qui porte une information absente ailleurs sur l'écran ; ajouter un texte ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, rapport, captures, reste à faire.
```

### Corrections 2 — revue du 21 septembre au soir (RA1 → RA8)

À enchaîner après la pile R1 → R13 mergée. Détail, anchors et recette dans
`docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md`.

<!-- LOT id="RA1" title="La pensée du modèle ne s'affiche jamais" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA1 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RA1 — La pensée du modèle ne s'affiche jamais.
Objectif : la fiche d'escale (surtout en anglais) et le chat affichent de vraies phrases, jamais le prompt ni le raisonnement du modèle (« Analyze User Input: Task: Translate… Wait, let me re-read… »).
Cause racine : server/story_cascade.py — _call_tokenfactory (payload ~l. 424-440) n'envoie pas chat_template_kwargs={"thinking": False} / reasoning_effort:"low" (contrairement à _call_nim l. 460-470) ; Nemotron émet son raisonnement, _openai_text (l. 389) le renvoie, _clean_text (l. 284) ne retire que les fences. La fiche d'escale (escale_api.py → cascade_text/translate) et le chat (logbook_chat.py:429 → cascade_text) l'affichent.
Fichiers à ouvrir (seulement) : server/story_cascade.py (_call_tokenfactory, _openai_text, _clean_text, _META_RE l. 290, translate l. 322), server/tests/test_story_cascade.py, server/escale_api.py PAR EXTRAIT (rg -n "translate|tidy_story|cascade_text"), server/logbook_chat.py PAR EXTRAIT (rg -n "cascade_text|filter_numbers"), les tests server/tests/test_escale_api.py / test_logbook_chat.py s'ils existent.
Étapes : 1) _call_tokenfactory : ajouter "chat_template_kwargs": {"thinking": False} et "reasoning_effort": "low" au payload ; 2) _openai_text : ignorer message.reasoning_content, ne lire que message.content, retirer tout bloc <think>…</think> (et un <think> ouvert sans fermeture : couper à partir de la balise) ; 3) _clean_text : après les fences, retirer un préambule méta en tête (« Analyze User Input », « Task: », « Constraints: », « Request: », « Wait, », « Let me », « The user says », « Thinking OFF », lignes de consigne en **gras**) jusqu'à la première vraie phrase ; 4) garde-fou : si le texte nettoyé contient encore un fragment du system prompt (« translate a sailing-log paragraph », « Keep every number »), renvoyer le fallback (source rules) ; 5) ne casse pas filter_numbers ni le contrat de cascade_text.
Tests : test_story_cascade.py — une réponse factice {choices:[{message:{content:"<think>raisonnement…</think> La Rochelle est un port."}}]} → « La Rochelle est un port. » ; une réponse qui n'est que du raisonnement → fallback ; le payload Token Factory contient chat_template_kwargs.thinking == False. npm test si un fichier JS change (sinon non), .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Simulation, langue anglais, clic sur le drapeau de Saint-Maur → la fiche « Port of call sheet » contient de vraies phrases anglaises, jamais « Analyze User Input / Task / Wait, let me… ». Suivre, Journal de bord → « À quelle vitesse va le bateau ? » → une phrase, pas un prompt. Spec e2e/lots/ra1-pensee.spec.js si tu exposes un stub ; sinon capture docs/recette/lot-ra1/01-fiche-en.jpg (URL complète sur ta branche).
Branche fix/lot-ra1-pensee-modele depuis la base indiquée (main sinon). PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : afficher le raisonnement ; inventer un chiffre ; retirer une surface visible ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA2" title="L'ordre du récit suit exactement le voyage" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA2 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RA2 — L'ordre du récit suit exactement le voyage.
Objectif : le récit (FR et EN) et le film énoncent les escales dans l'ordre exact de la route (Saint-Maur → La Rochelle → Ajaccio/Corse → Fort-de-France → …), chaque « départ vers X » suivi de « arrivée à X », sans répéter une escale. Aujourd'hui il annonce « départ vers Fort-de-France » puis « escale à Ajaccio » (décalage d'une jambe) et répète Ajaccio.
Fichiers à ouvrir (seulement) : src/engine/expeditionStory.js (legParagraph ~l. 281-305, stopsWithDates l. 124-141, departureIso l. 145) et expeditionStory.test.js, server/film_script.py (dated_marks l. 138-153, assemblage des chapitres l. 260-293) et server/tests/test_film_script.py.
Étapes : 1) apparier chaque paragraphe/chapitre à une seule jambe stops[i] → stops[i+1] : « départ de stops[i] le {départ} … arrivée à stops[i+1] le {arrivée}, N jours à quai » ; 2) dédoublonner les escales (vérifier qu'aucune marque n'est citée deux fois ; le voisinage filmNm < 0.6 côté serveur suffit-il ?) ; 3) l'ordre est strictement celui de la route (filmNm croissant).
Tests : expeditionStory.test.js et test_film_script.py — sur le voyage officiel, la suite des noms cités est exactement l'ordre de la route, sans répétition, chaque « départ vers X » suivi de « arrivée à X ». npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre → Revoir l'expédition (FR puis EN) : les escales sont énoncées dans l'ordre du voyage (Ajaccio/Corse AVANT Fort-de-France), sans répétition. Capture docs/recette/lot-ra2/01-ordre.jpg (URL complète sur ta branche).
Branche fix/lot-ra2-ordre-recit depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : inventer une date/distance ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA3" title="Revoir l'expédition : fond de carte, pas de saut, zoom stable, dézoom archipels, bulle utile" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="M" deps="RA2" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA3 » (texte intégral), puis docs/PLAN_FILM_REVOIR_EXPEDITION.md § 4. Tu travailles dans naviguide-simulator/. Le lot RA2 est dans ta base.

Lot RA3 — Revoir l'expédition : le rendu.
Objectif : pendant tout le film, le fond de carte reste visible ; le bateau glisse le long du trait sans saut jusqu'à la fin ; le zoom ne saute pas quand le film s'arrête (Cayenne) ; dans les Caraïbes la caméra montre l'archipel sans sauter d'île en île ; une bulle utile apparaît à l'approche des escales.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT (base layer l. 194, switchBaseLayer l. 425-432, caméra film l. 367-415, syncFilmCamera), src/map/filmCamera.js (+ test), src/engine/filmCast.js (interpolation, isAirPhase), src/hooks/useReplay.js (boucle l. 228-310) et useReplay.test.js.
Étapes : 1) fond de carte : la couche de tuiles reste visible pendant filmActive ; si switchBaseLayer est appelé pendant le film, ré-ajouter avant de retirer (jamais de carte sans tuiles) ou ne pas switcher pendant le film ; 2) aucun saut : position interpolée le long du trait sur TOUTE la durée (fin comprise), jamais « le sommet le plus proche » ni un saut de plan ; 3) zoom stable en fin : à l'arrêt du film, pas de saut de zoom, retour au live sans fitBounds sauvage ; 4) dézoom archipels : le zoom d'un chapitre borne l'emprise de la jambe mais plafonne pour montrer une sous-branche « îles proches » d'un coup ; 5) bulle : apparaît à l'approche d'une escale et sur un événement notable, une seule à la fois, fermable (croix, Échap), le film continue (le CHOIX des événements sera raffiné en R9).
Tests : useReplay.test.js — 60 frames entre deux boundaries → positions monotones le long du trait jusqu'au dernier chapitre ; filmCamera.test.js — zoom plafonné pour une jambe à sauts courts, pas de switch de base layer pendant filmActive. npm test, npx vite build, npm run e2e -- e2e/lots/f1-film.spec.js.
Recette (visuelle) : Revoir → pendant tout le film le fond de carte reste ; le bateau glisse sans saut jusqu'à la fin ; le zoom ne saute pas à l'arrêt ; dans les Caraïbes la caméra montre l'archipel sans sauter d'île en île ; une bulle apparaît à l'approche des escales, fermable. Captures docs/recette/lot-ra3/01-fond-carte.jpg, 02-caraibes.jpg (URL complète sur ta branche).
Branche fix/lot-ra3-film-rendu depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : zoomer pendant une jambe ; laisser la carte sans tuiles ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA4" title="Jambes avion, position live stable, carte non répétée à l'infini" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="M" deps="RA3" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA4 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RA3 est dans ta base.

Lot RA4 — Jambes avion, position live stable, bornes de longitude.
Objectif : les jambes avion (Cayenne ↔ Saint-Pierre-et-Miquelon, sauts Pacifique) sont en noir pointillé, non colorées par régime, non cliquables et hors de la distance « à la voile » ; la position live est stable au rechargement ; la carte ne se répète pas à l'infini en longitude.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT (addRouteLine l. 63, segments de route l. 457-492, maxBounds l. 182), src/utils/berryLegs.js (type de jambe mer/terre/air), src/engine/filmCast.js (isAirPhase), server/voyage_clock.py PAR EXTRAIT (jambe avion l. 541-548, distance voile), server/voyage_api.py PAR EXTRAIT (horloge officielle), MapSceneBoundary.test.js, server/tests/test_voyage_clock.py.
Étapes : 1) trait avion : les segments dont la jambe est de type air sont tracés en noir pointillé, non colorés par régime, non cliquables (pas de fiche, pas de survol) ; 2) la couleur/le régime/la vitesse ne s'appliquent qu'aux jambes en mer ; 3) position live : une seule source (horloge officielle serveur), pas de saut cache → recalcul au rechargement ; la distance « à la voile » cumulée exclut les milles des jambes avion (le vol prend AIR_CALENDAR_HOURS, il n'ajoute pas de milles voile) ; 4) longitude bornée : au plus une copie du monde de chaque côté (maxBounds longitude bornée, ex. [-540, 540], tuiles noWrap au-delà) — plus de répétition infinie.
Tests : MapSceneBoundary.test.js — longitude bornée ; test route — une jambe air donne un trait dash noir non interactif ; test_voyage_clock.py — distance voile exclut les jambes air, position live déterministe (deux appels, même date → même position). npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre, carte monde — le trait Cayenne ↔ Saint-Pierre (et les sauts Pacifique) est noir pointillé, pas violet/bleu, non cliquable. Recharger (Cmd R) plusieurs fois : le bateau réapparaît à la même position (pas de saut Nouméa → Panama). Tirer la carte sur les côtés : le monde ne se répète qu'une fois de chaque côté. Captures docs/recette/lot-ra4/01-avion.jpg, 02-bornes.jpg (URL complète sur ta branche).
Branche fix/lot-ra4-avion-live-bornes depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : colorer une jambe avion ; compter l'avion dans la distance voile ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA5" title="Logique des boutons de lecture, pas de fiche d'escale pendant le film" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="M" deps="RA4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA5 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RA4 est dans ta base.

Lot RA5 — Logique des boutons + fiche d'escale hors film.
Objectif : « Stop » arrête vraiment le film (voix + animation + caméra) et revient à la vue Suivre ; « Stop auto » (arrêt à la prochaine escale) et « Écouter » (voix on/off) sont distincts et font ce qu'ils disent ; aucun état où plus aucun bouton ne répond ; passer de Simulation à Suivre ou lancer Revoir ferme la fiche d'escale ; la croix et Échap ferment la fiche.
Fichiers à ouvrir (seulement) : src/hooks/useReplay.js (stop / états), src/components/SimulationFilmBar.jsx (stopAuto l. 78-79, replay controls l. 407), src/App.jsx PAR EXTRAIT (rg -n "escaleStop|openEscaleSheet|closeEscaleSheet|replay|onStop|returnToLive"), src/components/EscalePopup.jsx (ou EscaleSheet en popup ; croix onClose), tests associés.
Étapes : 1) un bouton Stop clair arrête le film et revient à Suivre ; distinct de Stop auto et d'Écouter, chacun étiqueté ; 2) machine à états cohérente Suivre ↔ Simulation ↔ Revoir : passer en Suivre/Revoir vide escaleStop (ferme la fiche) ; 3) pas de fiche pendant le film ; croix et Échap ferment (corrige R7 : la croix ne fermait pas) ; 4) aucun bouton « mort ».
Tests : useReplay.test.js — stop() met active=false, coupe la voix, libère la caméra ; test d'état — passer en Suivre/Revoir met escaleStop à null ; EscalePopup.test.js — la croix appelle onClose. npm test, npx vite build, npm run e2e (fumée + f1-film si présent).
Recette (visuelle) : Simulation → ouvrir la fiche d'escale → Suivre : la fiche disparaît. Lancer Revoir : pas de fiche ; Stop arrête net et revient à Suivre ; Écouter coupe/relance la voix ; aucun bouton mort. Captures docs/recette/lot-ra5/01-stop.jpg (URL complète sur ta branche).
Branche fix/lot-ra5-boutons-lecture depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : fiche d'escale pendant le film ; bouton sans effet ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA6" title="Finitions : redite skipper, crédits au-dessus de la barre, km à terre, cadre de réponse du chat" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu »), puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA6 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RA6 — Finitions.
Objectif : plus de redite « Croisière · 36 h » à côté de « Paramètres avancés » ; les crédits carte ne sont plus coupés par la barre de lecture ; l'info-bulle de vitesse existe aussi en Suivre ; la jambe terrestre s'affiche en km dans la barre film ; le chat a un cadre de réponse (plus de grand vide violet) ; le détecteur de redites voit les états repliés/dépliés.
Fichiers à ouvrir (seulement) : src/components/SkipperOrdersPanel.jsx (<summary> l. 183-195 vs budget l. 257), src/layers/styles.js et src/index.css (position/marge des crédits Leaflet), src/components/SimulationFilmBar.jsx (info-bulle de vitesse en Suivre ; libellé jambe terrestre en km), src/components/LogbookChat.jsx (cadre de réponse ; zone vide ~l. 54), naviguide-simulator/scripts/redites.mjs, src/i18n/fr.js et en.js, tests associés.
Étapes : 1) l'en-tête replié de « Paramètres avancés » ne répète pas le profil + budget déjà dans le panneau (garder une seule occurrence) ; 2) remonter l'attribution Leaflet (marge basse ≥ hauteur de la barre film) pour qu'elle ne soit pas coupée ; 3) même info-bulle « hindcast/prévision/climatologie » sur la pilule de vitesse en Suivre qu'en Simulation ; 4) jambe terrestre en km dans la barre (« … km par la route · h de route ») ; 5) un cadre visible sous « Poser une question » destiné à la réponse (remplit le vide), la réponse s'y écrit ; 6) redites.mjs compte aussi les doublons entre un <summary> replié et le contenu déplié.
Tests : SkipperOrdersPanel.test.js — profil/budget une seule fois ; test de layout/styles — marge des crédits ≥ hauteur barre ; LogbookChat.test.js — cadre de réponse présent. npm test, npx vite build, npm run e2e -- e2e/lots/r13-redites.spec.js.
Recette (visuelle) : Panneau droit → « Paramètres avancés » : « Croisière · 36 h » une seule fois. Carte : crédits non coupés par la barre. Suivre : survol vitesse → info-bulle des trois régimes. Simulation, Saint-Maur : « km par la route ». Journal de bord : un cadre attend la réponse. Captures docs/recette/lot-ra6/01-skipper.jpg, 02-credits.jpg (URL complète sur ta branche).
Branche fix/lot-ra6-finitions depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : ajouter un texte d'aide ; laisser une redite ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA7" title="Fourchette d'arrivée sous la prochaine escale, intervalle resserré" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA7 » (texte intégral), puis docs/PLAN_AUDIT_CALCULS.md « Lot C6 ». Tu travailles dans naviguide-simulator/.

Lot RA7 — Fourchette d'arrivée lisible et resserrée.
Objectif : « arriver entre le … et le … » (deux dates courtes) s'affiche sous la prochaine escale en Suivre ; l'intervalle est de quelques jours, plus « 13 nov. → 10 juin » (7 mois) — cause : un membre d'ensemble à vitesse ~0 fait exploser p90.
Fichiers à ouvrir (seulement) : src/hooks/usePlanReview.js (formatEtaRange l. 25, useOfficialEta), src/components/EscaleLegend.jsx (l. 75-78), server/voyage_api.py PAR EXTRAIT (/voyage/official/eta, ensemble), server/plan_review.py, tests (usePlanReview.test.js, test_plan_review.py).
Étapes : 1) sous la prochaine escale (Suivre), afficher la fourchette quand l'ensemble existe, sinon rien (jamais inventé) ; 2) resserrer : écarter les membres à vitesse dégénérée (plancher 3 kn, comme voyage_clock.boat_speed) et/ou borner p10-p90 à une fenêtre plausible ; le détail p10-p90/membres reste en info-bulle ; 3) même source et même arrondi en Suivre et dans la Revue du plan.
Tests : test_voyage_api/test_plan_review — sur le voyage officiel, l'intervalle Nouméa → Dzaoudzi est de quelques jours ; usePlanReview.test.js — aucun membre à 0 kn dans la fourchette. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre → sous la prochaine escale : « arriver entre le … et le … » (deux dates). Panneau droit → Revue du plan, Nouméa → Dzaoudzi : une fourchette de quelques jours. Capture docs/recette/lot-ra7/01-fourchette.jpg (URL complète sur ta branche).
Branche fix/lot-ra7-fourchette depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : inventer une date ; membre à vitesse nulle ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RA8" title="Vitesse réelle par la météo historique (archive Open-Meteo/ERA5) le long de la route" plan="docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md § 0 et le « RA8 » (texte intégral), puis docs/PLAN_AUDIT_CALCULS.md « Lot C2 ». Tu travailles dans naviguide-simulator/. Ce lot passe APRÈS que le film soit solide.

Lot RA8 — Vitesse réelle par la météo historique le long de la route.
Objectif : en Suivre, la vitesse du tronçon déjà parcouru vient de la météo historique le long de la route depuis le 15 mai 2026 ; les 10 jours devant = prévision GFS ; au-delà = climatologie. Aujourd'hui la route est violette (climatologie) partout car le hindcast n'alimente pas encore la vitesse / le régime.
Source : l'archive Open-Meteo (ERA5), PAS d'obligation Copernicus. server/hindcast.py lit déjà archive-api.open-meteo.com/v1/archive (ERA5, vent horaire depuis 1940, SANS clé) et historical-forecast-api.open-meteo.com, et fusionne par médiane avec CMEMS quand les identifiants existent (une source en panne manque, aucune source → champ vide). RA8 ne dépend donc pas de Copernicus : le vent du passé vient d'ERA5 Open-Meteo ; CMEMS reste un bonus (vagues, courant).
Fichiers à ouvrir (seulement) : server/hindcast.py (OM_ERA5_URL, fusion), server/voyage_api.py PAR EXTRAIT (_fill_hindcast_then_forecast, _kick_official_hindcast l. 629-655), server/voyage_clock.py (régime par sommet _clock_kind l. 421-424, vitesse), server/tests/test_hindcast.py, server/tests/test_voyage_clock.py.
Étapes : 1) vérifier que le vent ERA5 Open-Meteo date/teinte le tronçon parcouru (regime=hindcast), la prévision GFS Open-Meteo sur 10 jours, la climatologie au-delà ; /ici/warm/status → store.hindcast monte SANS dépendre de Copernicus ; 2) si le hindcast ne couvre pas toute la route parcourue, compléter le remplissage ERA5 le long du trait aux dates réelles de passage, en tâche de fond, sans bloquer le démarrage ; 3) la vitesse d'un sommet passé = vent réel de l'époque × polaire, pas la climatologie ; 4) aucun appel réseau dans les tests (fixtures ERA5, pas de Copernicus).
Tests : test_hindcast/test_voyage_clock — un sommet daté dans le passé a regime=hindcast et une vitesse issue du vent ERA5 (fixture), pas de la climatologie ; une réponse Open-Meteo archive factice suffit. npm test si JS, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre — le tronçon déjà parcouru est teinté hindcast (plus tout violet climatologie) ; le survol d'un point passé montre une vitesse issue du vent réel de l'époque, sans clé Copernicus. Capture docs/recette/lot-ra8/01-hindcast.jpg (URL complète sur ta branche).
Branche feat/lot-ra8-vitesse-historique depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : appel réseau dans les tests ; bloquer le démarrage ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

### Corrections 3 — revue du 22 septembre au matin (RB1 → RB8)

À enchaîner après la pile RA1 → RA8 mergée. Détail, causes racines
(fichier:ligne) et recette dans `docs/PLAN_CORRECTIONS_2026-09-22.md`. Le
programme continue ensuite avec R8a → D0 ; les constats du 22 sept. qui
relèvent de ces lots sont fondus dans leurs prompts (R8a, R8c, R9c, R10d).

<!-- LOT id="RB1" title="Halifax ↔ Saint-Pierre redevient une jambe mer ; l'avion ne vole que Cayenne ↔ Halifax" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB1 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RB1 — Halifax ↔ Saint-Pierre redevient une jambe MER (régression majeure de la revue du 22 sept.).
Objectif : le trajet Halifax ↔ Saint-Pierre-et-Miquelon est une jambe en mer (trait coloré par régime, cliquable, climatologie et vitesse calculées dessus) ; seuls Cayenne ↔ Halifax (aller-retour) et les sauts Pacifique restent avion (noir pointillé, non cliquable, hors distance voile). La chorégraphie d'avant est conservée : le bateau reste stationné à Cayenne, l'avion va à Halifax, un bateau relais apparaît à Halifax, navigue jusqu'à Saint-Pierre et revient, l'avion repart vers Cayenne pendant que le bateau relais disparaît, puis le bateau de Cayenne continue vers la Polynésie.
Cause racine : src/utils/berryLegs.js (version RA4) l. 62-77 — airStopKey reconnaît {cayenne, halifax, spm} et isAirLegNames déclare « air » TOUTE paire différente, donc aussi Halifax ↔ Saint-Pierre ; legKind (l. 83) et officialRouteLineStyle (l. 90) propagent l'erreur. La chorégraphie de référence est sur main : src/engine/filmCast.js l. 63-64 et l. 230 (trois acteurs : bateau Berry, avion, bateau relais) ; buildBerryLegs (berryLegs.js l. 18-44) crée déjà les jambes relais Halifax → SPM → Halifax.
Fichiers à ouvrir (seulement) : src/utils/berryLegs.js, src/utils/berryLegs.test.js, src/engine/filmCast.js (lecture : chorégraphie de référence), src/map/MapSceneController.js PAR EXTRAIT (rg -n "officialRouteLineStyle|isAirSegment|addRouteLine"), server/voyage_clock.py PAR EXTRAIT (rg -n "air|AIR_CALENDAR"), server/tests/test_voyage_clock.py.
Étapes : 1) isAirLegNames ne dit « air » que pour Cayenne ↔ Halifax (les deux sens) ; Halifax ↔ Saint-Pierre = mer (style nul, cliquable, régime/vitesse/climato comme les autres jambes de mer) ; 2) serveur : la jambe Halifax ↔ SPM compte ses milles à la voile et son temps de mer ; seules Cayenne ↔ Halifax restent au régime avion (AIR_CALENDAR_HOURS, zéro mille voile) ; 3) vérifier que la chorégraphie de filmCast.js est intacte après la pile RA ; si un lot RA l'a dégradée, la restaurer à l'identique du main d'avant la pile ; 4) rien d'autre de RA4 n'est retiré (bornes de longitude, trait avion des vraies jambes avion).
Tests : berryLegs.test.js — Halifax → SPM et SPM → Halifax donnent legKind "sea" et aucun style noir pointillé ; Cayenne ↔ Halifax donnent "air" ; test_voyage_clock.py — la distance voile inclut Halifax ↔ SPM et exclut Cayenne ↔ Halifax. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre, carte monde — le trait Halifax ↔ Saint-Pierre est coloré comme une jambe de mer, un clic dessus répond ; seuls Cayenne ↔ Halifax et les sauts Pacifique sont noirs pointillés. Revoir l'expédition, passage en Guyane — le bateau reste à Cayenne, l'avion décolle, un bateau navigue Halifax → Saint-Pierre → Halifax, l'avion revient et disparaît à Cayenne, le bateau continue vers la Polynésie. Captures docs/recette/lot-rb1/01-halifax-mer.jpg, 02-choregraphie.jpg (URL complète sur ta branche).
Branche fix/lot-rb1-halifax-mer depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : reclasser une vraie jambe avion en mer ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB2" title="Zoom horizontal compact en bas à droite, à côté des crédits" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB2 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RB2 — Le zoom en bas à droite, horizontal et compact.
Objectif : plus de boutons + − en haut à gauche (masqués par le sidebar) ; un contrôle de zoom horizontal, compact, en bas à droite de la carte, juste à côté des citations « Leaflet | Tuiles © Esri — HERE, Garmin, OpenStreetMap contributors », jamais recouvert par la barre de lecture ni les sidebars.
Cause racine : src/map/MapSceneController.js l. 173-184 — L.map(container, {...}) ne passe pas zoomControl: false : le contrôle Leaflet par défaut s'affiche en haut à gauche, sous le bouton d'ouverture du panneau gauche qui le masque.
Fichiers à ouvrir (seulement) : src/map/MapSceneController.js PAR EXTRAIT (l. 170-200 et rg -n "attributionControl|control"), src/index.css, tests associés (rg -n "zoom" src/map/*.test.js*).
Étapes : 1) zoomControl: false + contrôle de zoom en position bottomright ; 2) CSS : + et − côte à côte (horizontal), plus compacts que le défaut Leaflet, alignés avec l'attribution et au-dessus de la barre de lecture ; 3) aucune autre surface ne bouge (crédits entiers, RA6 conservé) ; 4) test de montage : le contrôle existe et il est en bas à droite.
Tests : npm test, npx vite build, npm run e2e (fumée).
Recette (visuelle) : tous écrans carte — plus de + − en haut à gauche ; en bas à droite, deux petits boutons + − à l'horizontale à côté des crédits ; le zoom marche ; visibles sidebars ouverts ou fermés, barre de lecture affichée ou masquée. Capture docs/recette/lot-rb2/01-zoom.jpg (URL complète sur ta branche).
Branche fix/lot-rb2-zoom-bas-droite depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : masquer les crédits ; retirer une surface ; texte d'aide ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB3" title="Plus jamais de prompt : le cache des fiches est re-nettoyé" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB3 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RB3 — Plus jamais de prompt (fiche d'escale, journal), même depuis le cache.
Objectif : la fiche d'escale et le journal de bord n'affichent jamais un prompt ni un raisonnement — y compris quand le texte sort du cache (le porteur voit encore « Input: A large JSON object… Task: Present a scale stop… » sur la fiche de Pointe-à-Pitre, et « toujours un prompt » au journal).
Cause racine : server/escale_api.py l. 286 et l. 361-374 — la fiche est servie depuis pearl_store.kv_get("escale", …, ESCALE_TTL_S) (TTL 7 jours) SANS repasser par le nettoyage : les paragraphes fuités générés avant RA1 ressortent tels quels. Le garde RA1 (server/story_cascade.py, _PROMPT_LEAK_RE l. 58, _clean_text l. 336-340) ne s'applique qu'à la génération.
Fichiers à ouvrir (seulement) : server/escale_api.py, server/story_cascade.py, server/tests/test_story_cascade.py, server/tests/test_escale_api.py (créer s'il n'existe pas), server/logbook_chat.py PAR EXTRAIT (rg -n "cascade_text|kv_get|cache").
Étapes : 1) à la lecture du cache (fiche, et chat s'il a un cache) : repasser le paragraphe par _clean_text ; texte vide ou fuité → invalider la clé et regénérer (ou servir le repli rules), jamais servir la fuite ; 2) élargir _PROMPT_LEAK_RE aux formes du 22 sept. : « Input: A large JSON object », « What's for the boat », « - Task: » (et équivalents traduits si la fiche est traduite) ; 3) le chat passe par le même garde : réponse fuitée → repli honnête du journal ; 4) ne pas casser filter_numbers ni le contrat de cascade_text.
Tests : une entrée de cache contenant le texte fuité de la capture → la route renvoie le repli rules et la clé est invalidée ; une entrée saine → servie inchangée ; test _PROMPT_LEAK_RE sur les nouvelles formes. .venv/bin/python -m pytest -q, npx vite build (npm test si un fichier JS change).
Recette (visuelle) : Simulation, langue anglaise, drapeau de Pointe-à-Pitre → la fiche contient de vraies phrases sur l'escale, jamais « Input: », « Task: », « JSON ». Suivre, Journal de bord → « À quelle vitesse va le bateau ? » → une phrase (ou l'échec honnête), jamais un prompt, y compris en reposant la même question. Capture docs/recette/lot-rb3/01-fiche.jpg (URL complète sur ta branche).
Branche fix/lot-rb3-cache-prompt depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : afficher un prompt ou un raisonnement ; inventer un chiffre ; vider le cache entier sans raison ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB4" title="Barre de lecture sans scroll : un bouton de vitesse à 4 niveaux, flèches, haut-parleur" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu »), puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB4 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RB4 — Barre de lecture compacte, sans barre de scroll.
Objectif : la barre de lecture tient sur une ligne sans barre de défilement. Un SEUL bouton de vitesse qui cycle à chaque clic : réel → lecture → normale → accélérée → réel (mêmes vitesses qu'avant, aucun niveau supprimé). « Escale précédente / Aller à la prochaine escale » deviennent deux flèches ‹ › (libellé complet en info-bulle). « Écouter » devient l'icône haut-parleur (état coupé/actif visible, libellé en info-bulle). Le libellé météo dit la vérité : « climatologie + GFS » si les deux alimentent le point courant, sinon seulement celui qui est employé (détail des modèles en info-bulle).
Cause racine : src/components/SimulationFilmBar.jsx l. 311 — la rangée de commandes est en overflow-x-auto : avec les 4 pilules de vitesse (SPEEDS l. 9-12 : real/read/normal/fast) et les libellés longs, une barre de défilement apparaît. Libellé météo : clockRegimeText l. 556-570 concatène régime et sources sans dire ce qui est réellement employé.
Fichiers à ouvrir (seulement) : src/components/SimulationFilmBar.jsx, ses tests (rg -n "SimulationFilmBar" src/components/*.test.js*), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) un seul bouton de vitesse cyclique affichant le niveau courant ; 2) flèches ‹ › pour les escales, haut-parleur pour Écouter, info-bulles i18n fr/en ; 3) une ligne sans défilement aux largeurs courantes, retirer l'overflow-x-auto devenu inutile ; 4) libellé météo exact (« climatologie + GFS » ou la seule source employée) ; 5) ne pas retirer un bouton existant (Masquer la barre, Cinéma, Stop auto, modes) ; les data-testid existants restent.
Tests : le cycle du bouton (4 clics → retour à réel) ; aucune pilule de vitesse résiduelle ; libellé météo pour « les deux » et « un seul ». npm test, npx vite build, npm run e2e (fumée).
Recette (visuelle) : Suivre et Simulation, barre de lecture — aucune barre de défilement ; un bouton de vitesse qui passe de réel → lecture → normale → accélérée puis revient à réel ; deux flèches pour les escales ; un haut-parleur à la place d'Écouter ; « climatologie + GFS » seulement si les deux sont utilisés. Capture docs/recette/lot-rb4/01-barre.jpg (URL complète sur ta branche).
Branche fix/lot-rb4-barre-compacte depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : barre de scroll ; retirer un bouton existant ; rangée ajoutée ; texte d'aide ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB5" title="Le film part de Saint-Maur le 15 mai 2026 ; la voix dit « milles nautiques »" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB5 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RB5 — Le film dit le voyage officiel.
Objectif : la voix du film commence par « L'expédition Berry-Mappemonde a quitté Saint-Maur le 15 mai 2026… » (jamais « La Rochelle », jamais « 25 avril 2027 ») et énonce les escales dans l'ordre exact de la route (Saint-Maur → La Rochelle → Ajaccio → Fort-de-France → …) ; dans tout texte déclamé, les unités sont en toutes lettres (« milles nautiques » / « nautical miles », jamais « nm » que la voix lit « nanètres »).
Cause racine : server/film_script.py l. 425-430 — le chapitre « depart » prend (start or {}).get("iso") or (clock or {}).get("t0") et le nom de start : quand le client envoie l'horloge d'une simulation (date réglée dans le panneau), le film déclame la date et l'escale de la simulation au lieu du départ officiel — c'est aussi pour ça que Saint-Maur manque en tête (KO bot RA2 sur le poste). Et l. 595-598, « le bateau est à {distLabel} du départ » emploie l'abréviation « nm » (l. 574).
Fichiers à ouvrir (seulement) : server/film_script.py, server/tests/test_film_script.py, src/hooks/useReplay.js PAR EXTRAIT (rg -n "film|script|fetch" : ce que le client envoie), src/engine/expeditionStory.js (tête du récit, stopsWithDates l. 124-141), src/engine/expeditionStory.test.js.
Étapes : 1) pour le voyage officiel, le chapitre « depart » lit la première marque de la route officielle (Saint-Maur) et la date officielle du départ (15 mai 2026), jamais le t0 d'une horloge de simulation ni une date recalculée ; la suite suit l'ordre de la route (finit RA2 sur le poste réel) ; 2) unités en toutes lettres dans tout texte déclamé (film serveur et récit client) — l'affichage écrit peut garder « nm » ; 3) aucune date ni distance inventée : tout vient de la route et de l'horloge officielles.
Tests : test_film_script.py — le script officiel commence par Saint-Maur et « 15 mai 2026 » même quand la requête porte une horloge de simulation ; aucun « nm » nu dans les phrases du script ; expeditionStory.test.js — la tête du récit nomme Saint-Maur. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre → Revoir l'expédition (FR puis EN) — la voix commence par « a quitté Saint-Maur le 15 mai 2026 », on entend « milles nautiques », jamais « nanomètres » ni « 2027 » ; le sous-titre affiche la même suite d'escales que la liste de droite, dans le même ordre. Capture docs/recette/lot-rb5/01-depart.jpg (URL complète sur ta branche).
Branche fix/lot-rb5-film-officiel depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : inventer une date ou une distance ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB6" title="La voix ne coupe plus, Stop coupe tout, la caméra ne saute pas sur la Polynésie" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="M" deps="RB5" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB6 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RB5 est dans ta base.

Lot RB6 — Voix et Stop fiables pendant Revoir.
Objectif : la voix du film ne s'arrête plus en plein milieu d'une phrase ; un incident de voix ne termine pas le film et ne recale jamais la caméra sur la position live (la « Polynésie » du porteur) ; Stop coupe tout (voix + animation + caméra) au premier clic, même pendant qu'une utterance joue.
Cause racine : src/utils/speak.js l. 182-275 — « onend sans boundary en < 500 ms → une relance, puis mode linéaire » : quand Chrome coupe une utterance (keep-alive l. 9, chunks de 200 caractères l. 10), le film bascule ou finit prématurément ; et src/hooks/useReplay.js l. 48-71 — à la fin (ou sur Stop), retour au live : une fin prématurée recale la caméra sur la position live en plein film. Le « Stop qui ne marche pas » du porteur : pendant la lecture vocale, l'arrêt ne coupe pas tout d'un seul geste.
Fichiers à ouvrir (seulement) : src/utils/speak.js, src/utils/speak.test.js, src/hooks/useReplay.js, src/hooks/useReplay.test.js, src/components/SimulationFilmBar.jsx PAR EXTRAIT (rg -n "onStop|stopReplay|listen").
Étapes : 1) coupure en plein chunk → reprendre au chunk suivant (ou relire le chunk coupé), jamais finir le film sur un incident de voix ; la bascule linéaire ne déclenche pas de retour au live tant que des chapitres restent ; 2) la caméra ne se recale sur la position live QUE si le film est vraiment fini ou si le porteur a cliqué Stop ; 3) Stop : un clic coupe la voix (cancel), l'animation et libère la caméra dans le même geste ; le bouton répond au premier clic ; 4) ne pas casser la bascule linéaire de Playwright (canLeadWithVoice).
Tests : speak.test.js — un onend prématuré au milieu des chunks → le texte continue au chunk suivant ; useReplay.test.js — un incident de voix ne met pas finish ; stop() pendant la lecture coupe voix + animation + caméra. npm test, npx vite build, npm run e2e (fumée + film si présent).
Recette (visuelle) : Suivre → Revoir l'expédition, laisser parler plusieurs minutes — la voix ne s'arrête pas en plein milieu d'une phrase ; la carte ne se recale jamais sur la Polynésie pendant le film. Cliquer Stop pendant que la voix parle — tout s'arrête net au premier clic et « Revoir l'expédition » revient. Capture docs/recette/lot-rb6/01-stop.jpg (URL complète sur ta branche).
Branche fix/lot-rb6-voix-stop depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : bouton sans effet ; retour au live sur incident de voix ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB7" title="Fourchette d'arrivée réellement affichée : ensemble ETA préchauffé" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB7 » (texte intégral), puis docs/PLAN_AUDIT_CALCULS.md « Lot C6 ». Tu travailles dans naviguide-simulator/.

Lot RB7 — La fourchette d'arrivée s'affiche vraiment.
Objectif : « arrivée entre le … et le … » apparaît sous la prochaine escale (Suivre) et dans la Revue du plan sans que le porteur recharge, au plus quelques minutes après le lancement — les 2 KO bot de RA7 venaient d'un ensemble jamais prêt (« perles pas encore chauffées »).
Cause racine : server/voyage_api.py l. 781-788 — /voyage/official/eta appelle ensemble_eta.official_eta qui renvoie {members: 0} tant que rien n'a chauffé les membres ; côté client src/components/EscaleLegend.jsx l. 75-78 et src/hooks/usePlanReview.js l. 47-57 n'affichent rien dans ce cas : sur un poste frais la fourchette n'apparaît jamais.
Fichiers à ouvrir (seulement) : server/voyage_api.py PAR EXTRAIT (rg -n "official/eta|_kick_official"), server/ensemble_eta.py, server/tests/test_ensemble_eta.py (ou le test existant de l'ETA), src/hooks/usePlanReview.js, src/components/EscaleLegend.jsx, tests JS associés.
Étapes : 1) préchauffer l'ensemble ETA du voyage officiel au démarrage du serveur, en tâche de fond (comme _kick_official_hindcast), sans bloquer le démarrage ; rafraîchi avec les perles ; 2) le client re-demande l'ETA tant que members == 0 (léger, recul progressif) : la fourchette apparaît dès qu'elle est prête, sans rechargement ; 3) garder l'intervalle resserré de RA7 (membres à vitesse dégénérée écartés) ; même phrase et même arrondi en Suivre et dans la Revue du plan ; sans ensemble, rien d'inventé ; 4) aucun appel réseau dans les tests (fixtures).
Tests : serveur — après préchauffage sur la fixture officielle, members > 0 et fenêtre de quelques jours pour Nouméa → Dzaoudzi ; client — l'affichage apparaît quand la réponse passe de members: 0 à un ensemble plein. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Suivre, liste des escales, sous la prochaine — « arrivée entre le … et le … » (deux dates proches) visible au plus quelques minutes après le lancement, sans recharger. Panneau droit → Revue du plan, Nouméa → Dzaoudzi — la même fourchette de quelques jours. Capture docs/recette/lot-rb7/01-fourchette.jpg (URL complète sur ta branche).
Branche fix/lot-rb7-eta-prechauffe depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : inventer une date ; bloquer le démarrage ; membre à vitesse nulle ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RB8" title="La route sur les deux copies du monde ; survol d'un segment parcouru" plan="docs/PLAN_CORRECTIONS_2026-09-22.md" size="S" deps="RB1" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-22.md § 0 et le « RB8 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RB1 est dans ta base.

Lot RB8 — La route dessinée des deux côtés du monde, survol du parcouru.
Objectif : en tirant la carte vers la droite jusqu'à la butée, le trajet complet (Halifax, Antilles compris) est dessiné aussi sur la copie de droite (côté africain), comme il l'est déjà à gauche ; et le survol d'un segment déjà parcouru montre la vitesse hindcast de l'époque (complète l'item non vérifiable de RA8), rien sur les jambes avion.
Cause racine : src/utils/geo.js l. 87-94 — worldCopyCoords fait trois copies (0, +360, −360) d'une ligne DÉJÀ dépliée sur près de 360° de longitude : dans les bornes ±540° posées par RA4 (MapSceneController version RA4 l. 44, MAP_LON_BOUND = 540), la copie de droite ne couvre pas le côté africain du second monde.
Fichiers à ouvrir (seulement) : src/utils/geo.js, src/utils/geo.test.js, src/map/MapSceneController.js PAR EXTRAIT (WORLD_OFFSETS l. 40, addRouteLine l. 63, segments l. 457-492), MapSceneBoundary.test.js (ou le test de bornes de RA4), src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) les copies de la route couvrent toute la fenêtre navigable (±540°) : calculer les décalages d'après l'étendue réelle de la ligne dépliée (p. ex. 0, ±360, +720 si besoin) au lieu du triplet fixe ; 2) même règle pour les drapeaux/escales portés par la route s'ils manquent d'un côté ; 3) survol d'un segment déjà parcouru → info-bulle courte avec la vitesse hindcast de l'époque (donnée RA8), rien pour les jambes avion, aucun nouveau panneau ; 4) i18n de l'info-bulle fr/en.
Tests : geo.test.js — une ligne dépliée sur 360° produit des copies couvrant [−540, 540] ; test de bornes — après un grand glissement à droite, des points de route existent dans la fenêtre est ; un segment parcouru expose sa vitesse d'époque. npm test, npx vite build.
Recette (visuelle) : Suivre — tirer la carte vers la droite jusqu'à la butée : le trajet complet est dessiné aussi de ce côté-là, comme à gauche. Survoler le trait déjà parcouru — une petite info-bulle donne la vitesse de l'époque ; sur un trait avion, rien. Captures docs/recette/lot-rb8/01-copie-droite.jpg, 02-survol.jpg (URL complète sur ta branche).
Branche fix/lot-rb8-route-copies depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : répétition infinie du monde ; nouveau panneau ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

### Nuit 3 — « Ici et maintenant », journal des moments, expert en circumnavigation (R8a → R10d)

Pré-rédigés le 21 sept. au soir d'après `docs/PLAN_ICI_JOURNAL_EXPERT.md` (contrats de
données § 1.1, § 2.1, § 3.1 ; sous-lots § 1.2, § 2.3, § 3.4). Choix par défaut
des deux points restés ouverts : poids du score de l'expert **fixes** (constantes
dans `plan_advisor.py`, montrées en info-bulle) ; journal des simulations **local
au navigateur**. Le correcteur du matin peut y **fondre** des corrections
(« Constat de la revue du <date> : … »).

<!-- LOT id="R8a" title="Le modèle build_moment (serveur, sans UI)" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 0, § 1.1 (contrat Moment) et le sous-lot « R8a » (§ 1.2). Tu travailles dans naviguide-simulator/.

Lot R8a — Le modèle build_moment.
Objectif : une seule fonction serveur produit l'encadré « ici et maintenant » : build_moment(perle, clock_point, leg, skipper_thresholds) → Moment (contrat § 1.1) et signature(moment) (champs stables seulement). Aucun changement visible.
Fichiers à ouvrir (seulement) : server/moment.py (créer), server/tests/test_moment.py (créer), server/tests/fixtures/official_mini.json (créer : 3 escales, 40 points, 12 perles, horloge), server/ici_warm.py PAR EXTRAIT (rg -n "bag\[" : forme d'une perle), server/voyage_clock.py PAR EXTRAIT (t par point, régime), server/plan_review.py PAR EXTRAIT (saison, AMP).
Étapes : 1) build_moment : leg (from/to/day/kn/basis/remainingNm/doneNm/headingDeg/eta/regime), alerts (wind, sea, cyclone, entry, mpa, night — chacune avec fact non vide), here (zee, entry, mpa, seamarks, seabed, weather, sentences, links), around (satellite, climatology, science, marina), sources ; 2) signature : sha1 des champs stables (alerts.id, here.zee.mrgid, here.entry, around[].title, leg.to, leg.regime) — un mille de plus ne la change pas, une nouvelle ZEE oui ; 3) aucun chiffre inventé : tout vient de la perle et de l'horloge ; 4) fixture réduite du voyage officiel, réutilisable par R8b, R9a, R10a.
Constat de la revue du 22 sept. : le texte FR mélange les langues — « Le bateau navigue dans French Exclusive Economic Zone (Guadeloupe) (Guadeloupe) » (src/engine/iciBriefing.js l. 187 insère le nom marineregions brut, avec un doublon de parenthèses). Étape ajoutée : 5) here (zee, entry, mpa) et here.sentences portent des noms localisés dans la langue demandée (gabarit « Zone économique exclusive française (Guadeloupe) » / « French EEZ (Guadeloupe) »), sans doublon de parenthèses ; un test le vérifie sur la fixture.
Tests : test_moment.py — mêmes entrées → même signature ; +1 nm → même signature ; nouvelle ZEE → autre signature ; toute alerte a un fact ; le Moment est sérialisable JSON. .venv/bin/python -m pytest -q.
Recette (visuelle) : aucun changement visible — les trois parcours (Suivre Nouméa, Simulation La Rochelle → Ajaccio, Tracer Brisbane → SF) marchent comme avant.
Branche feat/lot-r8a-moment depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : UI ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, reste à faire.
```

<!-- LOT id="R8b" title="GET /ici/moment et l'encadré unique sans titre" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R8a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu »), puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 1.0 (ce que le porteur verra), § 1.1 et le sous-lot « R8b ». Tu travailles dans naviguide-simulator/. R8a est dans ta base.

Lot R8b — L'endpoint et l'encadré.
Objectif : GET /ici/moment?lat&lon&t&mode renvoie un Moment (perle la plus proche ou sac calculé comme /ici, puis build_moment) ; un composant IciMaintenant rend un Moment dans UN encadré SANS TITRE (aucun bandeau « Ici et maintenant »), sélecteur discret Maintenant · Récit · Journal, sections Étape / Alertes (pastilles fermables une à une) / Ici / Autour du bateau / Sources, hauteur = tout le reste du panneau (flex-1 min-h-0 overflow-auto), mode clair inclus. Pas encore branché dans le panneau (R8c).
Fichiers à ouvrir (seulement) : server/main.py PAR EXTRAIT (rg -n "@app.get\(\"/ici" : ajouter la route), server/tests/test_main_moment.py (créer), src/hooks/useMoment.js (créer : fetch + état, repli fixture si l'API ne répond pas), src/components/IciMaintenant.jsx (créer), src/components/IciMaintenant.test.js (créer), src/index.css (variables de hauteur, .light-mode), src/i18n/fr.js, en.js.
Étapes : 1) route serveur + test ; 2) composant : aucun texte d'aide, aucun titre, une pastille d'alerte fermée n'en ouvre pas une autre, liens de sources conservés ; 3) sélecteur discret (3 petits onglets texte), Récit et Journal reçoivent pour l'instant un emplacement vide (R8c/R9b les remplissent) ; 4) fr/en pour chaque libellé nouveau.
Tests : test_main_moment.py — la route répond un Moment avec signature ; IciMaintenant.test.js — rendu des 5 sections, fermeture d'une pastille n'affecte pas les autres, aucun élément de titre. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : aucun changement visible dans l'app tant que R8c n'est pas là ; la PR joint une capture du composant rendu seul (page de test ou story) : un cadre sans titre, cinq sections, trois petits onglets.
Branche feat/lot-r8b-encadre depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : titre ou bandeau sur l'encadré ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R8c" title="Branchement : un seul encadré, plus aucune pop-up sur la carte" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R8b" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 1.0 et le sous-lot « R8c ». Tu travailles dans naviguide-simulator/. R8b est dans ta base.

Lot R8c — Le branchement et le retrait des anciens blocs ET des pop-up de carte.
Objectif : le panneau gauche = carte Berry → chat (inchangé) → IciMaintenant (tout le reste) ; les vues Récit et Journal reçoivent les composants existants (récit de la traversée, journal) ; les blocs séparés (MomentCards inline, FREE, sac ici, récit, journal, fiche d'escale) disparaissent du panneau ; sur la carte, PLUS AUCUNE pop-up flottante : la carte « À bord, maintenant · décision » en haut, les fiches « Pendant ce temps autour du bateau » en bas à droite (et leur bouton Écouter), la popup d'escale — leur contenu vit dans l'encadré. Simulation et Tracer passent par le même endpoint (position du curseur / route dessinée). Aucune surface de main inaccessible, rien de dupliqué carte + encadré.
Fichiers à ouvrir (seulement) : src/components/Sidebar.jsx, src/components/Sidebar.layout.test.js, src/map/MapSceneController.js PAR EXTRAIT (rg -n "momentCard|nowCard|freeCard|escale|popup|EventBubble" : retirer les cartes flottantes hors film ; la bulle du FILM (R6/RA3) reste), src/App.jsx PAR EXTRAIT (rg -n "iciBriefing|freeCards|momentCards|storyText|journal|escaleStop|onEscaleSheet|useMoment"), src/components/IciMaintenant.jsx (vues Récit / Journal), tests de contrat existants (uiProductContract.test.js si présent).
Étapes : 1) un seul objet moment (useMoment) passé au panneau ; 2) Sidebar : remplacer, conserver les data-testid existants par alias ; 3) MapSceneController / App : retirer les cartes flottantes hors film et leurs boutons Écouter ; la fiche d'escale s'ouvre DANS l'encadré (vue Maintenant → section Ici) au clic sur un drapeau ; 4) Simulation / Tracer : même encadré à la position courante ; 5) mode clair.
Constat de la revue du 22 sept. : les cartes « À bord, maintenant · décision » (haut de carte) et « Pendant ce temps autour du bateau » (bas droite) apparaissent en Simulation ET en Suivre, sidebars fermés, chacune avec son bouton Écouter — « il faut tout inclure dans un encadré… il faut que ça soit un produit ; il faut enlever les boutons Écouter de ces encadrés ». C'est exactement ce que ce lot livre : plus rien ne flotte sur la carte hors la bulle du film, et aucun bouton Écouter dupliqué.
Tests : Sidebar.layout.test.js — ordre carte Berry → chat → IciMaintenant, aucun ancien bloc ; test de contrat — aucune pop-up hors film n'est rendue ; les tests de contrat existants passent sans être affaiblis (alias). npm test, npx vite build, npm run e2e (fumée).
Recette (visuelle) : Suivre, Simulation, Tracer — un seul encadré sans titre sous le chat, rempli à la position courante ; plus aucune carte flottante sur la carte (ni « à bord maintenant », ni fiche science, ni fiche d'escale) ; cliquer un drapeau ouvre l'escale DANS l'encadré ; thème clair identique. Captures docs/recette/lot-r8c/01-suivre.jpg, 02-simulation.jpg (URL complète sur ta branche).
Branche feat/lot-r8c-branchement depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : retirer une information (elle change de place) ; laisser une pop-up hors film ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R9a" title="Table moments, remplissage le long des perles, endpoint" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R8a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 2.0, § 2.1 (ligne de journal) et le sous-lot « R9a ». Tu travailles dans naviguide-simulator/. R8a est dans ta base.

Lot R9a — Le journal des moments (serveur).
Objectif : pour le voyage officiel, une table dérivée `moments` : on parcourt les perles dans l'ordre de la route, build_moment → signature, une ligne par changement de signature avec `changes` = diff_moments(prev, cur) (kind, score 1–3, title, fact) ; remplie en tâche de fond après le réchauffage des perles, rafraîchie chaque jour ; GET /voyage/official/moments?until= la lit. Aucun changement visible.
Fichiers à ouvrir (seulement) : server/moment_journal.py (créer : diff_moments, warm_moments(voyage_id), read_moments), server/pearl_store.py PAR EXTRAIT (table `moments` dans _SCHEMA), server/voyage_api.py PAR EXTRAIT (rg -n "_kick_official_hindcast|warm_official_route" : lancement en tâche de fond ; nouvelle route GET), server/tests/test_moment_journal.py (créer), fixture R8a.
Étapes : 1) diff_moments avec les scores § 2.1 (escale 3, alerte qui s'allume 3, ZEE 2, station 2, régime 1, AMP 1, alerte qui s'éteint 1) ; 2) warm_moments idempotent (rejouer ne duplique pas ; une signature qui change met la ligne à jour) ; 3) /ici/warm/status expose `moments: n` ; 4) jamais bloquant au démarrage.
Tests : test_moment_journal.py — sur la fixture, N perles → M moments avec M < N, seq croissant, changes non vides sauf la première ligne ; rejouer → même M ; read_moments(until) coupe bien. .venv/bin/python -m pytest -q.
Recette (visuelle) : aucun changement visible ; la PR cite `/ici/warm/status` → `moments: n` sur le poste local.
Branche feat/lot-r9a-journal depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : UI ; chiffre LLM ; bloquer le démarrage ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, reste à faire.
```

<!-- LOT id="R9b" title="La vue Journal, et l'encadré lit le journal" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="S" deps="R8c,R9a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 2.0 et le sous-lot « R9b ». Tu travailles dans naviguide-simulator/. R8c et R9a sont dans ta base.

Lot R9b — La vue Journal.
Objectif : dans l'encadré, la vue Journal liste chronologiquement « date · position · ce qui a changé » (voyage officiel : serveur ; simulation / route dessinée : journal local au navigateur, localStorage, ≤ 2 000 entrées, construit depuis les Moments reçus) ; cliquer une entrée place le curseur / le film à cette date ; en Suivre, la vue Maintenant lit le moment du journal ≤ maintenant (cohérence exacte).
Fichiers à ouvrir (seulement) : src/hooks/useMomentJournal.js (créer), src/components/IciMaintenant.jsx (vue Journal), src/components/IciMaintenant.test.js, src/App.jsx PAR EXTRAIT (rg -n "useMoment|setPlayhead|seekTo|onSeek" : placer le curseur), src/i18n/fr.js, en.js.
Étapes : 1) hook : officiel → GET /voyage/official/moments ; autres → localStorage clé = identifiant de route ; 2) vue Journal : liste défilante, une ligne par entrée, pas de texte d'aide ; 3) clic → curseur à la date ; 4) Maintenant = dernier moment ≤ t.
Tests : IciMaintenant.test.js — N entrées rendues dans l'ordre ; clic appelle onSeek(t) ; useMomentJournal.test.js — repli localStorage, plafond 2 000. npm test, npx vite build.
Recette (visuelle) : Suivre → vue Journal : les entrées défilent du 15 mai à aujourd'hui ; cliquer une entrée place le film / le curseur à cette date. Simulation → le journal se remplit au fil du curseur. Capture docs/recette/lot-r9b/01-journal.jpg (URL complète sur ta branche).
Branche feat/lot-r9b-vue-journal depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R9c" title="Le film raconte le journal : sélection sous budget, préchauffé, chapitre par chapitre" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R9a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 2.2 (règles de récit, préchauffage, découpe) et le sous-lot « R9c ». Tu travailles dans naviguide-simulator/. R9a est dans ta base.

Lot R9c — Le film raconte le journal.
Objectif : le script du film (GET /voyage/official/film) est construit depuis le journal des moments : chapitres = jambes, dans l'ORDRE EXACT de la route sans répétition (cohérent avec RA2) ; budget 2 400 caractères (150 s) réparti au prorata des jours de mer (plancher 120) ; sélection ≤ 3 changements par chapitre selon les règles de récit § 2.2 (escale, alerte la plus forte, fait de couleur ; regroupements) ; brut par gabarits (connecteurs variés) ; rédigé par Nemotron CHAPITRE PAR CHAPITRE (chaque prompt porte le résumé du chapitre suivant), sous filter_numbers, PRÉCHAUFFÉ en tâche de fond et servi depuis le cache (kv ns film-story) — jamais généré au clic ; events de chaque chapitre = les changements retenus (bulles).
Fichiers à ouvrir (seulement) : server/film_script.py PAR EXTRAIT (rg -n "def build_script|chapters|events|written"), server/story_cascade.py PAR EXTRAIT (réécriture sous filter_numbers), server/pearl_store.py PAR EXTRAIT (kv), server/voyage_api.py PAR EXTRAIT (préchauffage après warm_moments ; /film lit le cache), server/tests/test_film_script.py, fixture R8a. src/hooks/useReplay.js : RIEN (format du script inchangé).
Étapes : 1) sélection sous budget ; 2) brut ; 3) rédigé par chapitre + cache + préchauffage ; 4) events ; 5) ordre strict, aucune escale deux fois, chaque « départ vers X » suivi de « arrivée à X ».
Constat de la revue du 22 sept. : la voix lisait « nm » comme « nanètres » et coupait en plein milieu de phrase ; à l'approche des escales, la bulle carte ne se déclenchait pas (KO bot RA3). Étapes ajoutées : 6) les textes déclamés écrivent les unités en toutes lettres (« milles nautiques » / « nautical miles » — RB5 corrige l'existant, ce lot ne doit pas régresser) et les chapitres préchauffés sont découpés en phrases courtes (aucune coupure) ; 7) le journal fournit un moment « approche d'escale » par escale, que la bulle du film affiche (titre = nom de l'escale).
Tests : test_film_script.py — longueur du brut dans [budget −10 % ; +10 %] ; chaque chapitre ≥ 1 phrase et ≤ 3 changements ; arrivée de chaque escale présente ; ordre = ordre de la route ; aucun nombre du rédigé absent des faits ; deux chapitres consécutifs ne commencent pas par le même connecteur ; /film sert le cache sans appel LLM (client factice compte 0 appel). .venv/bin/python -m pytest -q, npm test, npx vite build.
Recette (visuelle) : Suivre → Revoir l'expédition : le film raconte, dans l'ordre du voyage, ce qui a changé le long de la route (escales, ZEE, alertes, stations) ; il dure 2 min 30 ; au clic le texte rédigé est déjà prêt (aucune attente) ; les bulles montrent les mêmes événements que le texte. Capture docs/recette/lot-r9c/01-film.jpg (URL complète sur ta branche).
Branche feat/lot-r9c-film-journal depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : générer au clic ; un prompt de 2 400 caractères d'un coup ; chiffre LLM hors faits ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R10a" title="L'évaluateur evaluate_plan : alertes pondérées par jambe, cyclone daté" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R8a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 3.0–3.2 (dont « l'alerte cyclone est datée ») et le sous-lot « R10a ». Tu travailles dans naviguide-simulator/. R8a est dans ta base.

Lot R10a — L'évaluateur de plan.
Objectif : evaluate_plan(plan) → {legs:[{alerts:[{kind, severity, when, where, fact, weight}], score, frozen}], total} (contrat § 3.1) : échantillon tous les 60 nm, daté avec la vitesse planifiée, interrogeant climatologie du mois (vent P90, Hs P90, saison cyclonique), prévision < 10 j, hindcast figé pour le passé, seuils du skipper, ZEE / ports d'entrée, AMP, piraterie (N4 si présent), couloirs (N3 si présent). L'alerte cyclone ne compte QUE si l'échantillon passe dans une fenêtre de ± 15 jours de la date historique du cyclone (sinon le mois de saison) — jamais au simple croisement géométrique. < 2 s par plan, cache par (hash du trait, dates au jour, seuils). Aucun changement visible.
Fichiers à ouvrir (seulement) : server/plan_alerts.py (créer), server/tests/test_plan_alerts.py (créer), server/tests/fixtures/climatology_mini.json (créer : 12 mois × 6 cases, avec dates historiques de cyclones), server/plan_review.py PAR EXTRAIT (lecture de l'atlas, jours à quai), server/voyage_clock.py PAR EXTRAIT (dater les échantillons), fixture R8a.
Étapes : 1) échantillonnage + datation ; 2) règles d'alerte avec weight 1–3 et fact ; 3) cyclone daté ; 4) frozen pour les jambes passées ; 5) cache.
Tests : test_plan_alerts.py — voyage officiel (fixture) évalué < 2 s ; décaler Nouméa de +30 jours change le total ; les jambes passées ne changent jamais ; chaque alerte a un fact et un when ; croiser une trace de cyclone HORS saison ne produit pas d'alerte, la croiser à la date historique en produit une. .venv/bin/python -m pytest -q.
Recette (visuelle) : aucun changement visible.
Branche feat/lot-r10a-evaluateur depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : UI ; chiffre LLM ; appel réseau dans les tests ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, reste à faire.
```

<!-- LOT id="R10b" title="Le compromis par décalage de date : advise" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R10a" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 3.1–3.2 et le sous-lot « R10b ». Tu travailles dans naviguide-simulator/. R10a est dans ta base.

Lot R10b — Le compromis par décalage de date.
Objectif : advise(plan, leg_idx) : candidats d ∈ {−21, −14, −7, 0, +7, +14, +21} jours sur le départ de la jambe, propagés à toutes les escales suivantes (jours à quai conservés) ; score = Σ weight des alertes + 0,3 × |d| + 0,02 × extraNm (constantes FIXES dans plan_advisor.py, exposées dans la réponse pour l'info-bulle) ; meilleur + 3 alternatives ; phrase gabarit depuis les facts ; GET /voyage/official/advice?leg= avec état pending|done (calcul en tâche de fond), réécriture LLM de la phrase via ADVICE_SYSTEM sous filter_numbers (repli gabarit). Aucun changement visible.
Fichiers à ouvrir (seulement) : server/plan_advisor.py (créer), server/tests/test_plan_advisor.py (créer), server/voyage_api.py PAR EXTRAIT (rg -n "ADVICE_SYSTEM|advice_facts|advice_fallback" : nouvelle route), fixture R8a + climatology_mini.
Étapes : 1) candidats et cascade ; 2) score et classement ; 3) phrase gabarit (nomme la jambe, le décalage, les alertes avant/après, la cascade) ; 4) route avec état ; 5) déterminisme.
Tests : test_plan_advisor.py — le score du meilleur ≤ celui du plan actuel ; la cascade décale toutes les escales suivantes du même nombre de jours ; jours à quai conservés ; deux appels → même réponse ; aucun nombre de la phrase absent des facts. .venv/bin/python -m pytest -q.
Recette (visuelle) : aucun changement visible ; la PR montre la réponse JSON de /voyage/official/advice?leg=3 sur le poste local.
Branche feat/lot-r10b-compromis-dates depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : UI ; chiffre LLM hors facts ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, reste à faire.
```

<!-- LOT id="R10c" title="L'écart local borné : corridor et cap de distance" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R10b" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 3.2 et le sous-lot « R10c ». Tu travailles dans naviguide-simulator/. R10b est dans ta base.

Lot R10c — L'écart local borné.
Objectif : aux candidats de date s'ajoutent des corridors {référence, nord, sud} (trait décalé de 150 nm puis relissé par grands cercles), distance ≤ +20 % ; l'isochrone ne sert plus qu'À L'INTÉRIEUR du corridor retenu (corridor ± 300 nm, cap +20 %, seuils du skipper), jamais d'écart libre — le cas « La Rochelle → Ajaccio, vent max 30 kn » rend ≤ 1 650 nm, plus jamais 4 643.
Fichiers à ouvrir (seulement) : server/plan_advisor.py (corridors, cap), server/isochrone.py PAR EXTRAIT (rg -n "def route|max_wind|constraints" : corridor et cap de distance en contraintes), server/tests/test_plan_advisor.py, server/tests/test_isochrone.py (si présent).
Étapes : 1) corridors nord/sud relissés ; 2) cap +20 % et ± 300 nm imposés à l'isochrone ; 3) candidats dates × corridors, même score ; 4) le « recalculer » de l'ordre du skipper passe par advise (jambe courante).
Tests : aucun candidat > +20 % de distance ; aucun point à > 300 nm du trait de référence ; La Rochelle → Ajaccio vent max 30 kn → route ≤ 1 650 nm ; déterminisme. .venv/bin/python -m pytest -q.
Recette (visuelle) : Simulation → Ordres du skipper, vent max 30 kn → « Recalculer l'itinéraire » (ou « Demander conseil » si R10d est passé) → la route proposée fait ≤ 1 650 nm. Capture docs/recette/lot-r10c/01-borne.jpg (URL complète sur ta branche).
Branche feat/lot-r10c-ecart-borne depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : écart libre ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="R10d" title="Revue du plan conseillée, deux colonnes, Appliquer ; Demander conseil" plan="docs/PLAN_ICI_JOURNAL_EXPERT.md" size="M" deps="R10c,R8c" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 « rien de superflu »), puis docs/PLAN_ICI_JOURNAL_EXPERT.md § 3.3 et le sous-lot « R10d ». Tu travailles dans naviguide-simulator/. R10c et R8c sont dans ta base.

Lot R10d — L'interface de l'expert.
Objectif : Revue du plan : chaque jambe a « alertes : n » teinté ; « Ce que je changerais » = la phrase du meilleur compromis de la jambe la plus chargée avec trois pastilles « 11 → 5 alertes · +41 nm · +7 j » et un bouton Appliquer (flux existant draft / recompute / accept) qui affiche deux colonnes (aujourd'hui / conseillé : distance, jours de mer, alertes, dates d'escale décalées) ; plus de tableau à six routes sans explication ; Ordres du skipper : « Recalculer l'itinéraire » devient « Demander conseil » → même carte deux colonnes pour la jambe courante.
Fichiers à ouvrir (seulement) : src/components/PlanReview.jsx, src/hooks/usePlanReview.js, src/components/SkipperOrdersPanel.jsx PAR EXTRAIT (bouton), la carte de comparaison existante (rg -n "RouteCompare|comparatif|six routes|proposé" src/components), tests associés, src/i18n/fr.js, en.js, src/App.jsx PAR EXTRAIT (rg -n "recompute|accept|draft").
Étapes : 1) ligne « alertes : n » par jambe ; 2) « Ce que je changerais » = phrase + pastilles ; 3) Appliquer → deux colonnes + dates décalées ; 4) « Demander conseil » remplace « Recalculer l'itinéraire » ; 5) aucun texte d'aide.
Constat de la revue du 22 sept. : « Ce que je changerais » s'affiche en anglais dans l'interface FR (texte LLM non traduit, vu dans la Revue du plan). Étape ajoutée : 6) la phrase du conseil et les pastilles sont rendues dans la langue de l'interface (gabarits FR/EN ; le texte rédigé passe par la traduction du lot L6) — jamais d'anglais dans l'UI française.
Tests : PlanReview.test.js — pastilles, phrase, deux colonnes ; SkipperOrdersPanel.test.js — libellé du bouton ; contrats existants intacts. npm test, npx vite build, npm run e2e (fumée).
Recette (visuelle) : Panneau droit → Revue du plan : « alertes : n » par jambe ; « Ce que je changerais » nomme la jambe, le décalage et l'écart avec « 11 → 5 alertes · +41 nm · +7 j » ; Appliquer montre deux colonnes et les dates d'escale décalées. Simulation → « Demander conseil » remplace « Recalculer l'itinéraire », même carte. Captures docs/recette/lot-r10d/01-revue.jpg, 02-conseil.jpg (URL complète sur ta branche).
Branche feat/lot-r10d-interface-expert depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : texte d'aide ; retirer une surface ; chiffre LLM hors facts ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

### Ancien NAVIGUIDE — ce qui reste utile (N1 → N4)

Décisions du porteur du 21 sept. : import ET export, GeoJSON ET KML ; anti-trafic et
piraterie gardés ; pas de discours thématiques. Détail : `docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md`.

<!-- LOT id="N1" title="Importer GeoJSON / KML dans Tracer ma route" plan="docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md § 0 et le lot « N1 » (texte intégral). Tu travailles dans naviguide-simulator/. Tu LIS naviguide/ (ancien code), tu ne le modifies jamais.

Lot N1 — Importer GeoJSON / KML dans « Tracer ma route ».
Objectif : un bouton Importer (à côté de Terminé / Effacer) accepte .geojson / .json / .kml ; les points (ou la ligne s'il n'y a pas de points) deviennent les waypoints de la route dessinée dans l'ordre du fichier ; le tracé se calcule comme après des clics (searoute par jambes) ; Terminé remplit le sac (lot T). Le dessin au clic reste tel quel.
Source à lire : naviguide/naviguide-app/src/utils/waypointsFromCollection.js (l. 6-30) ; le KML n'y est pas parsé : DOMParser (Placemark > Point > coordinates ; LineString > coordinates).
Fichiers à ouvrir (seulement) : src/utils/routeImport.js (créer : parseRouteFile(text, name) → {points:[{lat,lon,name}], source} ; GeoJSON Point/MultiPoint/LineString/FeatureCollection, KML Placemark ; noms depuis properties.name ; dédoublonnage < 0,1 nm ; max 60 points), src/utils/routeImport.test.js (créer, fixtures), src/hooks/useRouteDrawing.js (importPoints(points) : même flux qu'un clic par point), le composant du mode dessin (rg -n "drawing|Terminé|drawnPoints" src/components/*.jsx : bouton + input file), src/i18n/fr.js, en.js, src/App.jsx PAR EXTRAIT (rg -n "useRouteDrawing|addDrawnPoint|onDrawingWaypointClick").
Étapes : 1) parseur + erreurs lisibles ; 2) importPoints remplace la route en cours (confirmation si non vide) ; 3) bouton Importer, aucun texte d'aide ; 4) fichier invalide → message court, rien d'autre ne change.
Tests : routeImport.test.js — GeoJSON Points, LineString seule, KML Placemarks, KML LineString, fichier vide/invalide ; useRouteDrawing.test.js — importPoints ≡ N clics. npm test, npx vite build, spec e2e/lots/n1-import.spec.js (fixture chargée → route affichée).
Recette (visuelle) : Tracer ma route → Importer → un .geojson de 3 points (fixture jointe à la PR) → tu dois voir 3 drapeaux et la route calculée ; idem avec un .kml ; Terminé → le sac se remplit comme après des clics. Captures docs/recette/lot-n1/01-import.jpg (URL complète sur ta branche).
Branche feat/lot-n1-import-route depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : modifier naviguide/ ; retirer le dessin au clic ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="N2" title="Exporter GeoJSON / KML de la route de la vue, panneau droit" plan="docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md § 0 et le lot « N2 » (texte intégral). Tu travailles dans naviguide-simulator/. Tu LIS naviguide/, tu ne le modifies jamais.

Lot N2 — Exporter GeoJSON / KML.
Objectif : panneau droit, bloc Exporter avec deux boutons GeoJSON et KML qui téléchargent la route de la vue (Suivre = officielle avec escales ; Tracer = dessinée ; Simulation = simulée) ; une LineString par jambe (properties from/to/nm/kind mer|terre|air), un Point par escale ; KML équivalent (jambes avion en pointillé) ; nom naviguide-<mode>-<AAAA-MM-JJ>.geojson|kml.
Source à lire : naviguide/naviguide-app/src/components/ExportSidebar.jsx (downloadFile l. 59-70, buildGeoJSON l. 72-115, buildKML l. 116-225).
Fichiers à ouvrir (seulement) : src/utils/routeExport.js (créer), src/utils/routeExport.test.js (créer), src/components/ToolsSidebar.jsx (bloc Exporter, data-testid="export-geojson" / "export-kml"), src/i18n/fr.js, en.js, src/App.jsx PAR EXTRAIT (rg -n "ToolsSidebar" : passer segments + marques de la vue).
Étapes : 1) porter et alléger buildGeoJSON / buildKML / downloadFile ; 2) route de la vue selon le mode ; 3) deux boutons, aucun texte d'aide.
Tests : routeExport.test.js — GeoJSON valide (types), KML bien formé (DOMParser), N escales → N Points, jambe avion marquée. npm test, npx vite build, spec e2e/lots/n2-export.spec.js (téléchargement intercepté non vide).
Recette (visuelle) : Panneau droit → Exporter → GeoJSON → un fichier téléchargé qui s'ouvre dans geojson.io avec route et escales ; KML → idem dans Google Earth ; en Tracer, l'export contient la route dessinée. Capture docs/recette/lot-n2/01-export.jpg (URL complète sur ta branche).
Branche feat/lot-n2-export-route depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : modifier naviguide/ ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="N3" title="Score anti-trafic par jambe depuis le moteur searoute" plan="docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md § 0 et le lot « N3 » (texte intégral). Tu travailles dans naviguide-simulator/. Tu LIS naviguide/, tu ne le modifies jamais.

Lot N3 — Score anti-trafic.
Objectif : chaque jambe en mer porte antiShipping {score 0–1, lanes[]} calculé après searoute (métadonnée, le trait ne change pas) ; Revue du plan : « couloirs : Gibraltar » sous la jambe, teinte ambre si score < 0,55 ; panneau droit : pastille pour la route de la vue ; exposé à l'expert (R10a, alerte traffic poids 1).
Source à lire : naviguide/naviguide-api/routing_ab/cargo.py (SHIPPING_LANES l. 15-41, point_lane_weight, anti_shipping_score l. 60-73, lane_hits l. 74) et test_routing_ab_metrics.py.
Fichiers à ouvrir (seulement) : server/shipping_lanes.py (créer, source citée), server/tests/test_shipping_lanes.py (créer), server/route_engine.py PAR EXTRAIT (rg -n "def route|segments|meta" : métadonnée par jambe), server/plan_review.py, src/components/PlanReview.jsx, src/components/ToolsSidebar.jsx PAR EXTRAIT (pastille), src/i18n/fr.js, en.js.
Étapes : 1) module + tests ; 2) GET /route et route officielle exposent antiShipping par jambe ; 3) pastilles ; 4) géométrie strictement inchangée ; aucun texte d'aide.
Tests : test_shipping_lanes.py ; test_route_engine — Gibraltar / Aden / Malacca → score < 1, couloirs nommés, géométrie identique ; PlanReview.test.js — pastille. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Panneau droit → Revue du plan → jambe Ajaccio → Fort-de-France : « couloirs : Gibraltar » ; le trait sur la carte est inchangé. Capture docs/recette/lot-n3/01-couloirs.jpg (URL complète sur ta branche).
Branche feat/lot-n3-anti-trafic depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : modifier naviguide/ ; décaler le trait ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="N4" title="Zones de piraterie → cartes NOW et alertes" plan="docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md § 0 et le lot « N4 » (texte intégral). Tu travailles dans naviguide-simulator/. Tu LIS naviguide/, tu ne le modifies jamais.

Lot N4 — Piraterie.
Objectif : quand le bateau est dans une zone de piraterie recensée (Suivre, Simulation, film), une carte NOW « Piraterie — <zone> · <niveau> · IMB/UKMTO » apparaît (alerte si HIGH, décision sinon) et disparaît hors zone ; exposée à l'expert (R10a : alerte piracy, poids 3 HIGH / 2 MEDIUM / 1 LOW). Aucun score composite, aucune note inventée.
Source à lire : naviguide/naviguide_workspace/naviguide_agent3/risk_engine.py (PIRACY_ZONES l. 42-49 ; CYCLONE_BASINS : ne PAS copier).
Fichiers à ouvrir (seulement) : server/data/piracy_zones.json (créer : boîtes, niveau, source, date), server/piracy.py (créer : zone_at(lat, lon)), server/tests/test_piracy.py (créer), server/ici_warm.py ou server/main.py PAR EXTRAIT (rg -n "def ici|bag\[" : `piracy` dans le sac), src/engine/momentCard.js PAR EXTRAIT (rg -n "kind ===|severity" : carte NOW piracy), src/engine/momentCard.test.js, src/i18n/fr.js, en.js.
Étapes : 1) table + zone_at ; 2) sac : piracy {name, level, source} ou rien ; 3) carte NOW unique, disparaît hors zone ; 4) alerte datée pour l'expert.
Tests : test_piracy.py — Aden → HIGH, Atlantique nord → rien ; momentCard.test.js — carte présente / absente. npm test, .venv/bin/python -m pytest -q, npx vite build.
Recette (visuelle) : Simulation → curseur dans le golfe d'Aden → carte NOW « Piraterie — Horn of Africa / Gulf Aden · HIGH · IMB/UKMTO » ; au large de La Rochelle → aucune carte piraterie. Capture docs/recette/lot-n4/01-aden.jpg (URL complète sur ta branche).
Branche feat/lot-n4-piraterie depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : modifier naviguide/ ; copier CYCLONE_BASINS ; score composite ; texte d'aide ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

### Hygiène avant la soumission (D0, H1)

<!-- LOT id="D0" title="README FR/EN, manuel utilisateur, index et rangement de docs/" plan="docs/ETAT_DES_LIEUX_DOCS.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/ETAT_DES_LIEUX_DOCS.md (§ 3 rangement) et docs/ESPRIT_DE_L_APPLICATION.md. Documents seulement : aucun fichier de naviguide-simulator/src ni server.

Lot D0 — Documentation à jour pour un dépôt public.
Objectif : un lecteur du jury comprend l'application en 5 minutes : README.md racine (FR puis EN) — ce que fait le simulateur, les trois modes, Revoir l'expédition, où est la prod, comment lancer en local (dev-mac.sh), licence ; docs/MANUEL_UTILISATEUR.md (FR) + docs/USER_MANUAL.md (EN) — écran par écran, ce que fait chaque bouton, sans jargon ; docs/README.md — index des plans (fait / en cours / à venir) ; rangement selon ETAT_DES_LIEUX_DOCS.md § 3 (déplacer les plans terminés dans docs/archives/, corriger les liens).
Fichiers à ouvrir (seulement) : README.md, docs/README.md (créer), docs/MANUEL_UTILISATEUR.md (créer), docs/USER_MANUAL.md (créer), docs/ETAT_DES_LIEUX_DOCS.md, docs/ESPRIT_DE_L_APPLICATION.md, docs/HACKATHON_DEVPOST_SOUMISSION.md ; git mv pour le rangement.
Étapes : 1) README bilingue court (≤ 150 lignes) ; 2) manuel : un chapitre par écran (Suivre, Simulation, Tracer ma route, Revoir l'expédition, panneau droit), chaque bouton en une ligne « fait quoi » ; 3) index docs/README.md ; 4) rangement + liens vérifiés (script rg des liens morts dans la PR).
Tests : aucun code ; un script de vérification des liens Markdown (aucun lien mort) joint à la PR.
Recette (visuelle) : ouvrir le README sur GitHub → tu dois comprendre en 5 minutes ce que fait l'app et comment la lancer ; le manuel décrit chaque bouton que tu vois à l'écran.
Branche docs/lot-d0-readme-manuel depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : toucher au code ; supprimer un plan (archiver) ; vidéo ; secret. Décide seul et note-le. Fin : PR, liste des fichiers déplacés, reste à faire.
```

<!-- LOT id="H1" title="Préparer la séparation des dépôts (public = simulateur seul)" plan="docs/WORKFLOW_INDUSTRIEL.md" size="M" deps="D0" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/WORKFLOW_INDUSTRIEL.md § 4 (calendrier), .cursor/ask-briefs/02-separer-depots.md s'il existe, et docs/ARCHITECTURE.md. Tu PRÉPARES ; tu n'exécutes PAS la séparation (c'est le porteur, le 26–27 sept.).

Lot H1 — Préparer la séparation des dépôts.
Objectif : le dépôt PUBLIC présenté au jury ne contient que le simulateur (naviguide-simulator/, ses docs, infra de déploiement du simulateur) ; Blue Intelligence (backend/, frontend/, Archives/, naviguide/ legacy) reste PRIVÉ. Livrer : infra/split/README.md (procédure pas à pas pour un débutant sur Mac : création du dépôt public, `git subtree split` ou `git filter-repo` sur naviguide-simulator + docs choisis, réécriture des chemins, CI/deploy adaptés, redirection www.naviguide.fr → simulateur, README legacy dans naviguide/), infra/split/split.sh (idempotent, dry-run par défaut, ne pousse rien sans --push), la liste exacte des fichiers qui partent / restent, et les changements nécessaires dans .github/workflows (deploy du simulateur depuis le nouveau dépôt).
Fichiers à ouvrir (seulement) : infra/split/README.md (créer), infra/split/split.sh (créer), .github/workflows/*.yml (lecture ; modifications proposées dans un dossier infra/split/workflows/ à copier), infra/vps/naviguide/deploy-simulator.sh (lecture), naviguide/README.md (texte legacy proposé dans infra/split/).
Étapes : 1) inventaire partent/restent ; 2) script dry-run qui produit le dépôt public dans un dossier temporaire et vérifie `npm test` + `npx vite build` dedans ; 3) procédure ; 4) rien n'est poussé ni créé sur GitHub par le lot.
Tests : le dry-run produit un dossier où `cd naviguide-simulator && npm ci && npm test && npx vite build` passent ; aucun secret ni .env dans le résultat (rg).
Recette (visuelle) : la PR joint le journal du dry-run et la liste des fichiers ; le porteur lit la procédure et la trouve exécutable en 15 minutes.
Branche chore/lot-h1-split-depots depuis la base indiquée. PR vers main, gabarit REGLES § 3 (FR puis EN). Ne merge pas.
Interdits : créer ou pousser un dépôt ; supprimer des fichiers du dépôt courant ; secret ; vidéo. Décide seul et note-le. Fin : PR, journal du dry-run, reste à faire.
```

### Corrections 4 — revue du 23 septembre au matin (RD1 → RD7)

À enchaîner après la pile RB1 → RC5 (#269 → #302) mergée. Détail, causes
racines (fichier:ligne, lues sur la tête de pile #302) et recette dans
`docs/PLAN_CORRECTIONS_2026-09-23.md`. Les constats qui relèvent du globe
sont fondus dans G2 et G5 ; « Demander conseil » (#290) et les 502
`/bi/climatology/*` (#302) sont des artefacts du poste de recette — voir le
plan § 3.

<!-- LOT id="RD1" title="Le clic sur la carte fait ce qu'il dit : route → pop-up Copernicus, jamais le panneau gauche" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD1 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RD1 — Le clic sur la carte fait ce qu'il dit (revue du 23 sept. : « l'effet escompté, c'est que ça ouvre le pop-up Copernicus » ; « pourquoi le side bar gauche s'ouvre ? j'ai jamais demandé ça »).
Objectif : un clic sur la route (trait coloré ou trait bleu, hors jambes avion) ouvre le pop-up Copernicus (onglets Vent / Vagues / Courants), sur toutes les copies du monde et à tous les zooms ; aucun clic carte n'ouvre le panneau gauche ; les carrés verts ▤ des lignes d'escales disparaissent.
Cause racine : src/map/MapScene.jsx l. 159-173 — le clic ne reconnaît la route que si pointToSegmentPx(...) < 16, et pointToSegmentPx (l. 11-28) compare des longitudes non normalisées : tout clic sur une copie du monde (route RB8 à ±360°) échoue — seul Saint-Pierre-et-Miquelon (copie de base) répondait. Et src/App.jsx l. 855-859 — openEscaleFromUi fait setSidebarOpen(true) ; câblé au clic marqueur (onWaypointClick l. 1557, marqueurs MapSceneController.js l. 843-850) et au bouton ▤ des lignes d'escales (EscaleLegend.jsx l. 34-44, onEscaleSheet l. 1655) : le panneau gauche s'ouvre au clic — jamais demandé.
Fichiers à ouvrir (seulement) : src/map/MapScene.jsx, src/App.jsx PAR EXTRAIT (rg -n "openEscaleFromUi|onWaypointClick|onEscaleSheet|setSidebarOpen"), src/components/EscaleLegend.jsx, src/utils/geo.js (wrapLon, lecture), tests associés (EscaleLegend.test, test utilitaire pour pointToSegmentPx).
Étapes : 1) pointToSegmentPx : normaliser l'écart de longitude modulo 360 (clic et sommets ramenés dans la même copie) — le clic route répond des deux côtés du monde, seuil 16 px inchangé ; 2) le clic route ouvre le pop-up Copernicus (handleMapRouteClick existant), rien d'autre ; 3) openEscaleFromUi n'appelle plus setSidebarOpen(true) : clic drapeau → fiche dans la section Ici de l'encadré si le panneau est déjà ouvert ; panneau fermé → rien ne s'ouvre ; 4) retirer le bouton ▤ (escale-sheet-open) des lignes d'escales ; le clic sur la ligne (déplacer le curseur) reste.
Tests : clic simulé à lng+360 d'un segment → onRouteClick appelé ; openEscaleFromUi sans setSidebarOpen ; EscaleLegend ne rend plus escale-sheet-open. npm test, npx vite build, npm run e2e.
Recette (visuelle) : Suivre, carte monde puis carte tirée d'un tour vers la droite — un clic sur la route ouvre la carte satellite Vent / Vagues / Courants des deux côtés, à tous les zooms ; cliquer un drapeau n'ouvre pas le panneau gauche (panneau ouvert : la section Ici se remplit) ; liste des escales sans aucun carré vert. Captures docs/recette/lot-rd1/01-copernicus.jpg, 02-escales.jpg (URL complète sur ta branche).
Branche fix/lot-rd1-clics-carte depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : ouvrir un panneau au clic carte ; retirer le pop-up Copernicus ; retirer une surface demandée ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD2" title="Habillage carte : crédits sur le fond de carte, toggles alignés, point de tracé sous le clic" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 rien de superflu), puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD2 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RD2 — Habillage carte (revue du 23 sept. : « les citations sont devenues blanches, ils doivent avoir le fond de carte derrière eux » ; « le toggle du side bar gauche, mets-le à la même hauteur que celui du droit » ; « ça met le point de manière imprécise, on n'arrive pas à viser »).
Objectif : les crédits et le zoom se lisent sur le fond de carte sans bande blanche opaque (les deux thèmes) ; les deux chevrons d'ouverture des panneaux sont à la même hauteur ; en Tracer ma route le point se pose exactement sous le clic.
Cause racine : src/index.css l. 28-31 — en mode clair la bande des crédits est blanc opaque (rgba(255,255,255,0.8), préexistant à la pile) et le bloc RB2 .light-mode .leaflet-control-zoom ajoute un second aplat blanc à côté. src/components/Sidebar.jsx l. 327-331 — toggle gauche fermé à top-[92px] alors que le toggle droit (ToolsSidebar.jsx, chevron) est à top-4 ; la raison (zoom en haut à gauche) a disparu avec RB2. src/map/MapSceneController.js l. 806-807 — le rond de tracé fait 10 px (14 avec bordure) posé au coin haut-gauche d'une icône 24×24 ancrée [12,12] : il s'affiche ~5 px au-dessus/à gauche du lat/lon cliqué.
Fichiers à ouvrir (seulement) : src/index.css, src/components/Sidebar.jsx, src/map/MapSceneController.js PAR EXTRAIT (rg -n "10px;height:10px|iconAnchor"), tests associés.
Étapes : 1) reproduire dans Chrome (thème sombre puis clair) ; remplacer tout aplat blanc (attribution et zoom en mode clair) par la bande translucide discrète du mode sombre — le fond de carte reste visible derrière ; ne pas toucher au texte des crédits ; 2) toggle gauche fermé à top-4, même hauteur que le droit, panneaux ouverts ou fermés ; 3) centrer le rond de tracé : le pixel cliqué est le centre du rond (icône 14×14 ancrée [7,7] ou marge centrante), premier point (vert) et suivants (blancs) ; 4) aucun autre changement d'habillage.
Tests : montage — iconAnchor au centre exact du rond ; assertion e2e sur l'alignement vertical des deux toggles. npm test, npx vite build, npm run e2e.
Recette (visuelle) : tous écrans carte, thème sombre puis clair — crédits et zoom lisibles sur le fond de carte, sans bande blanche ; panneaux fermés, les deux chevrons à la même hauteur ; Tracer ma route à zoom moyen puis fort — le point tombe exactement sous la croix. Captures docs/recette/lot-rd2/01-credits.jpg, 02-tracer.jpg (URL complète sur ta branche).
Branche fix/lot-rd2-habillage-carte depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : masquer ou raccourcir les crédits ; déplacer le zoom ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD3" title="Panneau droit : encadré jaune retiré, nom du bateau une fois, remise du chiffre au profil réparée" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 rien de superflu, rien de non demandé), puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD3 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RD3 — Panneau droit (revue du 23 sept. : « un encadré jaune que j'ai jamais demandé » ; KO bot #302 : « Leopard 46 » aussi dans Paramètres avancés ; « la remise du chiffre du profil ne marche plus »).
Objectif : plus d'encadré jaune listant les couloirs commerciaux (la pastille « couloirs : X » par jambe de la Revue du plan reste) ; le nom du bateau ne se lit qu'une fois (sous Polaires) ; la remise d'un chiffre au profil (34 → 29 → ↺ → 34) remarche.
Cause racine : src/components/ToolsSidebar.jsx l. 13-27 — viewRouteAntiShipping agrège les couloirs de toutes les jambes ; rendu l. 397-407 (badge route-anti-shipping, bordure ambre « Bay of Biscay · Gibraltar · … ») — jamais demandé : le lot N3 prévoyait la pastille PAR JAMBE (PlanReview.jsx l. 135-141, conforme, à garder). src/components/SkipperOrdersPanel.jsx l. 192 — la rangée « Bateau » répète le nom du polar déjà affiché sous Polaires. Remise du chiffre : mécanisme SkipperOrdersPanel.jsx l. 69-79 (resetNumberToProfile, handleReset) et l. 106 (disabled={!forced}) ; le diff de la pile ne touche ni le composant ni le hook : REPRODUIRE d'abord (le bouton ↺ reste-t-il grisé ? forced jamais posé ?), chercher côté câblage onSkipperExpert={skipper.setExpert} (App.jsx l. 1666) et resolveOrders — ne pas coder à l'aveugle.
Fichiers à ouvrir (seulement) : src/components/ToolsSidebar.jsx, src/components/SkipperOrdersPanel.jsx, src/components/PlanReview.jsx (lecture seule), src/App.jsx PAR EXTRAIT (rg -n "skipper|setExpert"), tests associés.
Étapes : 1) supprimer le badge route-anti-shipping et viewRouteAntiShipping ; ne rien changer à la pastille par jambe ; 2) retirer la rangée « Bateau : <nom> » de Paramètres avancés (longueur / tirant d'eau restent) ; 3) reproduire la panne de la remise au profil, corriger la cause constatée, la documenter dans la PR (fichier:ligne) ; 4) test de non-régression : forcer une valeur → forced vrai → ↺ actif → retour à la valeur du profil, pour chaque champ numérique.
Tests : ToolsSidebar ne rend plus route-anti-shipping ; SkipperOrdersPanel sans nom de bateau ; cycle remise-au-profil vert. npm test, npx vite build, npm run e2e.
Recette (visuelle) : panneau droit — plus d'encadré jaune ; Revue du plan, chaque jambe garde sa ligne « couloirs : … » quand elle en croise ; Paramètres avancés — pas de nom de bateau (il reste sous Polaires, une fois) ; changer un chiffre (34 → 29) → ↺ s'allume → clic → 34 revient. Captures docs/recette/lot-rd3/01-panneau.jpg, 02-remise.jpg (URL complète sur ta branche).
Branche fix/lot-rd3-panneau-droit depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : retirer la pastille par jambe (N3) ; inventer une cause non reproduite ; retirer une surface demandée ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD4" title="Le voyage officiel existe dès le démarrage serveur : fourchette, journal, moments, film" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="M" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD4 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RD4 — Le voyage officiel est semé au démarrage (KO bot #275 : eta members: 0, pas de « arrivée entre le … et le … » ; KO #284 : journal à 0 entrée ; KO #285 : film en repli — tous causés par GET /voyage/official → 404 sur un poste frais).
Objectif : sur un poste relancé de zéro, GET /voyage/official ne renvoie jamais 404 ; l'ensemble ETA a des membres (la fourchette « arrivée entre le … et le … » s'affiche sous la prochaine escale en quelques minutes) ; le journal des moments et le film officiel se remplissent sans dépendre d'un client.
Cause racine : server/voyage_api.py l. 699-707 — _kick_official_eta (comme les warms moments / film / hindcast) abandonne si load_voyage(OFFICIAL_VOYAGE_ID) est None ; le voyage officiel n'est créé que par l'endpoint client ensure_official (l. 766, PUT) ; le démarrage serveur (server/main.py l. 84-97) préchauffe GRIB et « ici » mais ne sème pas le voyage.
Fichiers à ouvrir (seulement) : server/voyage_api.py PAR EXTRAIT (rg -n "_kick_official|ensure_official|OFFICIAL_VOYAGE_ID"), server/main.py, server/ensemble_eta.py (lecture), server/tests/test_voyage_api.py, server/tests/test_ensemble_eta.py s'il existe.
Étapes : 1) au démarrage serveur, si le voyage officiel n'est pas en base, le créer côté serveur avec le même corps que ensure_official (itinéraire Berry embarqué), sans client ni clé ; 2) enchaîner les préchauffages existants (_kick_official_hindcast, _kick_official_eta, _kick_official_moments, _kick_official_film_story) en tâche de fond, sans bloquer le démarrage ; 3) GET /voyage/official jamais 404 sur poste frais ; ensemble ETA members > 0 quelques minutes après le lancement ; 4) tests pytest sur store vide (fixtures, aucun appel réseau) : après startup le voyage existe, _kick_official_eta ne renvoie plus False pour voyage absent.
Tests : .venv/bin/python -m pytest -q, npm test, npx vite build.
Recette (visuelle) : poste relancé de zéro — Suivre s'ouvre sur le voyage ; sous la prochaine escale, « arrivée entre le … et le … » (deux dates proches) apparaît en quelques minutes sans recharger ; onglet Journal : des lignes du 15 mai à aujourd'hui, jamais une liste vide ; Revoir l'expédition démarre tout de suite. Capture docs/recette/lot-rd4/01-fourchette.jpg (URL complète sur ta branche).
Branche fix/lot-rd4-voyage-seme depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : bloquer le démarrage ; inventer une date ou un membre d'ensemble ; appel réseau dans les tests ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD5" title="Démarrage en Suivre ; dates de départ réglables, avec l'année" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="S" deps="" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD5 » (texte intégral). Tu travailles dans naviguide-simulator/.

Lot RD5 — Démarrage et dates (revue du 23 sept. : « quand on recharge, on tombe sur le mode simulation » ; « la date de départ n'est plus réglable ; il faut qu'elle soit réglable, sauf qu'il ne faut pas que ce soit la même que le mode simulation » ; « 15 mai 8h00 UTC, il n'y a même pas l'année »).
Objectif : l'application s'ouvre en Suivre ; en Simulation le champ « Date de départ » est visible sans dérouler et pilote l'horloge ; l'horloge de la barre film affiche l'année ; la date de départ de « Revoir l'expédition » est réglable (2025 possible), distincte de la Simulation, défaut 15 mai 2026.
Cause racine : src/App.jsx l. 169 — useState(VIEW_SIMULATION) (identique sur main d'avant-pile : pas une régression, mais refusé par le porteur). Le champ Date de départ existe (ToolsSidebar.jsx l. 421-425, showDeparture={isSimulation} App.jsx l. 1658, câblé voyage.t0 l. 1659) mais est enfoui sous la Revue du plan ; l'horloge de la barre film n'affiche pas l'année ; aucun réglage n'existe pour la date de départ du replay (RB5 fixe le départ officiel au 15 mai 2026 — bon défaut, pas réglable).
Fichiers à ouvrir (seulement) : src/App.jsx PAR EXTRAIT (rg -n "VIEW_SIMULATION|view, setView|showDeparture"), src/components/ToolsSidebar.jsx, src/components/DepartureField.jsx, src/components/SimulationFilmBar.jsx PAR EXTRAIT (rg -n "UTC"), src/hooks/useReplay.js PAR EXTRAIT (paramètres envoyés au film), src/i18n/fr.js, src/i18n/en.js, tests associés.
Étapes : 1) vue initiale = Suivre (VIEW_SUIVRE) ; 2) remonter « Date de départ » au-dessus de la Revue du plan (Simulation) et vérifier qu'éditer la date déplace le départ (barre film, positions) ; 3) l'horloge de la barre film affiche l'année (« 15 mai 2026 · 08:00 UTC ») dans tous les modes ; 4) en Suivre, à côté de « Revoir l'expédition » : date de départ du replay réglable (même gabarit que le champ Simulation), défaut 15 mai 2026, indépendante du t0 de Simulation — la régler décale les dates déclamées et affichées du film ; aucune date inventée : tout dérive de la date choisie et des durées réelles des jambes.
Tests : vue initiale Suivre ; le champ replay décale les dates du script (paramètre envoyé + serveur si concerné) ; l'année présente dans le libellé d'horloge. npm test, .venv/bin/python -m pytest -q si le serveur change, npx vite build, npm run e2e.
Recette (visuelle) : recharger → on arrive sur Suivre l'expédition ; Simulation, panneau droit — « Date de départ » visible sans dérouler, la changer déplace le départ, l'horloge affiche l'année ; Suivre — régler la date de Revoir sur 2025 → le film dit « … a quitté Saint-Maur le 15 mai 2025 » ; remettre le défaut → 2026 ; le t0 de la Simulation n'a pas bougé. Captures docs/recette/lot-rd5/01-suivre.jpg, 02-dates.jpg (URL complète sur ta branche).
Branche fix/lot-rd5-demarrage-dates depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : inventer une date ; changer le défaut officiel (15 mai 2026) ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD6" title="Encadré gauche : onglet Récit jamais vide, journal qui nomme, sans trou" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="S" deps="RD4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier (§ 1 : un onglet marche ou n'existe pas), puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD6 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RD4 est dans ta base.

Lot RD6 — L'encadré gauche tient parole (revue du 23 sept. : « Récit est toujours vide », « il y a un espace », « il faudrait qu'on sache à chaque fois ce sont lesquels »).
Objectif : l'onglet Récit n'est jamais un espace vide (absent hors Suivre, rempli en Suivre) ; chaque ligne du Journal nomme son événement ; plus d'espace mort sous les onglets Maintenant · Récit · Journal.
Cause racine : src/App.jsx l. 813-814 — storyParagraphs renvoie [] si !isSuivre || !officialClock ; src/components/Sidebar.jsx l. 472 — le slot story n'est rendu que isSuivre && !isDrawing : en Simulation l'onglet Récit (IciMaintenant.jsx l. 260-263, slot ici-story-slot) affiche du vide. Journal : le serveur nomme les événements (server/moment_journal.py l. 223 passe name pour une AMP) mais des lignes s'affichent sans le nom (« Aire marine protégée » sec, capture PR #284).
Fichiers à ouvrir (seulement) : src/components/IciMaintenant.jsx, src/components/Sidebar.jsx PAR EXTRAIT (rg -n "story=|journal="), src/App.jsx PAR EXTRAIT (rg -n "storyParagraphs"), src/hooks/useMomentJournal.js, server/moment_journal.py (lecture seule), tests associés.
Étapes : 1) en Simulation et Tracer, l'onglet Récit n'apparaît pas (Maintenant · Journal seulement) ; en Suivre il apparaît et se remplit (RD4 garantit l'horloge) ; 2) chaque ligne du Journal nomme son événement : « Aire marine protégée — <nom> », « Cyclone — <nom> (<année>) », « Marina — <nom> » ; le nom vient du fait serveur, jamais inventé ; sans nom en base → le type seul ; 3) resserrer l'espace entre les onglets et le contenu (pas de slot réservé vide) ; 4) aucun texte d'aide ajouté.
Tests : en Simulation l'onglet Récit n'est pas rendu ; en Suivre avec horloge, story-paragraph non vide ; fixture AMP avec nom → la ligne contient le nom. npm test, npx vite build, npm run e2e.
Recette (visuelle) : Simulation, panneau gauche — onglets Maintenant · Journal, aucun onglet Récit vide, pas d'espace mort ; Suivre, onglet Récit — des paragraphes dès l'ouverture ; onglet Journal — chaque ligne dit lequel (« Aire marine protégée — Iroise », pas « Aire marine protégée » sec). Captures docs/recette/lot-rd6/01-simulation.jpg, 02-journal.jpg (URL complète sur ta branche).
Branche fix/lot-rd6-encadre-recit depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : onglet ou slot vide ; texte d'aide ; nom inventé ; retirer une surface ; chiffre LLM ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

<!-- LOT id="RD7" title="Le film déclame les vraies données du journal ; durée libre par défaut" plan="docs/PLAN_CORRECTIONS_2026-09-23.md" size="M" deps="RD4" -->
```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/PLAN_CORRECTIONS_2026-09-23.md § 0 et le « RD7 » (texte intégral). Tu travailles dans naviguide-simulator/. Le lot RD4 est dans ta base.

Lot RD7 — Le film raconte les vraies données (revue du 23 sept. : « tu trouves une solution pour exploiter les vraies données que je me suis cassé le cul à collecter » ; « on va désélectionner la durée par défaut … s'il n'y a pas d'option cochée, tu dis à peu près tout ce qu'il y a dans le produit du side bar gauche, et il prend le temps que ça prend »).
Objectif : plus jamais « Le ciel reste haut / La mer porte le bateau / La route tient le cap / Le vent reste le vent » ; les durées 2:30 et 3:00 sont décochables et aucune n'est cochée par défaut ; sans durée cochée, le film déroule tout le journal des moments (marinas, ports, aires marines protégées, stations scientifiques, traces historiques de cyclones nommées et datées, culture des escales), dans l'ordre de la route, et prend le temps qu'il faut ; avec durée cochée, le budget est tenu jusqu'au bout (plus de film fini à ~121 s, KO bot #302).
Cause racine : server/film_script.py l. 39 — le tuple ATMOS meuble chaque jambe via le pool l. 1215 et le pad l. 1338, plus l. 1599 (« La mer reste la mer… ») : exactement les phrases moquées par le porteur ; les vraies données sont dans les moments (server/moment_journal.py) mais la sélection sous budget de 2 min 30 les écarte. src/components/SimulationFilmBar.jsx l. 458-470 — deux options [150, 180] toujours dont une active ; src/hooks/useReplay.js l. 177 — défaut FILM_TARGET_SECONDS.
Fichiers à ouvrir (seulement) : server/film_script.py, server/tests/test_film_script.py, src/components/SimulationFilmBar.jsx PAR EXTRAIT (rg -n "filmDuration|targetSeconds"), src/hooks/useReplay.js, src/hooks/useReplay.test.js, src/i18n/fr.js, src/i18n/en.js.
Étapes : 1) supprimer ATMOS et tous les pads : une jambe sans fait notable est racontée plus court, la voix ne meuble jamais ; 2) durées décochables (re-clic = décoché), aucune cochée par défaut ; durée cochée → budget appliqué et tenu jusqu'au bout ; aucune durée → pas de budget ; 3) sans budget, le script déroule le journal dans l'ordre de la route (paires départ/arrivée conservées, RC4/RC5) : marina croisée, port de départ, AMP traversée, stations au large, trace historique de cyclone (nom + année), culture de l'escale (faits de la fiche) — chaque fait nommé, chiffres via filter_numbers, champ inconnu = silence ; 4) la voix arrondit les distances (« 1 820 milles nautiques », jamais de décimale ni d'abréviation) — l'affichage écrit garde « nm » ; 5) tests : plus aucune phrase ATMOS ni pad dans le script officiel ; fixture de moments riches → chaque type cité au moins une fois sans budget ; budget 150 s atteint ; aucune décimale déclamée.
Tests : .venv/bin/python -m pytest -q, npm test, npx vite build, npm run e2e -- e2e/lots/rd7-film.spec.js.
Recette (visuelle) : Suivre, barre film — 2:30 et 3:00 décochés par défaut, cliquer coche, recliquer décoche ; Revoir sans durée cochée — le récit nomme marinas, AMP, stations, cyclones (nom et année) et la culture des escales, plus jamais « La mer porte le bateau » ; Revoir avec 2:30 — le film tient ~2 min 30 jusqu'au bout. Captures docs/recette/lot-rd7/01-durees.jpg, 02-recit.jpg (URL complète sur ta branche).
Branche fix/lot-rd7-film-journal depuis la base indiquée. PR vers main, gabarit REGLES § 3. Ne merge pas.
Interdits : phrase de remplissage ; chiffre produit par un LLM ; escale sautée ou répétée ; retirer une surface ; vidéo ; secret. Décide seul et note-le. Fin : PR, compteurs, captures, reste à faire.
```

## 3. Enchaîner les lots la nuit (`infra/agents/run_lots.py`)

Ce que le porteur a décrit — *ouvrir un agent, choisir Grok 4.6 xhigh fast,
coller le prompt, envoyer, attendre la fin, recommencer* — se fait sans
piloter l'interface : le script `infra/agents/run_lots.py` (Python standard,
rien à installer) lit ce fichier, lance **un agent par lot**, attend, vérifie
la PR et sa CI, passe au suivant. Deux façons de faire tourner l'agent :

| | `--runtime local` (**défaut**) | `--runtime cloud` |
|---|---|---|
| Où tourne l'agent | sur le Mac, par le **CLI Cursor** (`agent -p --force`), dans un **worktree git par lot** (`~/bim-lots/<lot>`) | sur une machine Cursor (API Cloud Agents `POST /v1/agents`) |
| Environnement | `node_modules` et `.venv` du dépôt partagés par lien, `.env` copié : `npm test`, `pytest`, `vite build`, Playwright **tournent vraiment**, la recette peut être réelle | machine neuve : l'agent doit réinstaller (npm ci, pip, navigateurs Playwright) à chaque lot — lent, fragile |
| Modèle | ceux du compte (`agent models`) : **Grok 4.6 xhigh fast** ; rien d'autre n'est appelé | idem via `GET /v1/models` ; mais la plateforme Cloud ajoute ses propres étapes (revue automatique, enregistrement vidéo) avec **ses** modèles — que le compte n'a plus |
| Coût | usage normal du forfait (Ultra 200 $ : usage inclus), pas de calcul Cloud facturé | usage + machine Cloud |
| Authentification | `agent login` une fois (navigateur) | `CURSOR_API_KEY` |
| Contrainte | le Mac reste allumé (`caffeinate -i`), un lot à la fois | rien à laisser allumé |
| PR | l'agent pousse et ouvre la PR avec `infra/agents/open_pr.py` (ou le script le fait s'il a oublié) | `autoCreatePR` |

**Réponse à la question du porteur** : oui, avec un compte qui n'a plus que
Grok, **le mode local est le bon choix** : il n'appelle que le modèle choisi,
aucune revue vidéo n'est déclenchée (la règle `pas-de-verification-video`
s'applique, et le CLI n'a pas cette étape), et l'environnement de test est
déjà là. Le Cloud reste possible pour une machine qu'on ne veut pas laisser
allumée.

Dans les deux cas : **pile linéaire** (chaque lot part de la branche du lot
précédent ; PR toutes vers `main`, à merger dans l'ordre — ou `--stack none`
pour partir de `main` à chaque fois), **une** relance si l'agent s'arrête
sans finir, **une** relance si la CI est rouge, 3 h maximum par lot, jamais
de merge ni de `push --force`, `state.json` pour reprendre, `run_lots.log`.

### Mise en route (une fois)

```bash
# 1. le CLI Cursor (déjà installé le 20 sept. sur ce Mac : version 2026.09.18)
curl https://cursor.com/install -fsS | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc   # Terminal en bash : ~/.bash_profile à la place
agent login                       # ouvre le navigateur, se connecter au compte Cursor (Ultra)
agent models                      # doit lister un identifiant contenant « grok »

# 2. vérifier que tout est prêt (ne lance rien)
cd ~/Blue-Intelligence-Map
python3 infra/agents/run_lots.py --check
```

`--check` vérifie : les 31 prompts, le jeton GitHub (trousseau git), le CLI et
sa connexion, le modèle, `node_modules` et `.venv`. Il dit « prêt » ou ce qui
manque.

Pour le mode Cloud, la clé : **cursor.com → Dashboard → Integrations → User
API Keys → Create New API Key** (nom libre, copier la clé, elle ne se
réaffiche pas) puis `export CURSOR_API_KEY="…"` dans le Terminal (ou dans
`~/.zshrc`). `python3 infra/agents/run_lots.py --check --runtime cloud`
confirme la clé et le modèle.

### Lancer

```bash
python3 infra/agents/run_lots.py --only C1                                  # premier essai réel — fait le 20 sept. (PR #207)
caffeinate -i python3 infra/agents/run_lots.py --from P2 --until L6 --skip C1   # la nuit : 24 lots, le Mac ne dort pas
caffeinate -i python3 infra/agents/run_lots.py --from G0 --until G7         # une autre nuit : le globe
python3 infra/agents/run_lots.py --from F1 --until F5 --stack none          # chacun depuis main
python3 infra/agents/run_lots.py --resume                                   # reprend state.json après une coupure
python3 infra/agents/run_lots.py --runtime cloud --only C2                  # via l'API
python3 infra/agents/run_lots.py --dry-run --from P2 --until O              # affiche les prompts, ne lance rien
```

Un lot déjà mergé se saute avec `--skip` ; si la branche du lot précédent a
été mergée entre-temps, le script repart de `main` tout seul.

Le matin : `git fetch`, lire les PR dans l'ordre, jouer les specs
`e2e/lots/*.spec.js` en local si besoin, merger un à un (merge commit ;
comme les PR visent toutes `main`, chaque merge fait fondre le diff de la
suivante), supprimer les branches, vérifier la prod. Les worktrees restent
dans `~/bim-lots/` pour relire le travail ; `git worktree remove --force
~/bim-lots/<lot>` quand c'est mergé.

Testé le 20 sept. avec un faux CLI : worktree créé depuis `origin/main`,
liens `node_modules` / `.venv` exclus de git, prompt transmis, « agent qui
ne fait rien » détecté comme raté sans rien pousser, `state.json` écrit.
Reste à faire par le porteur : `agent login`, puis `--only C1`.

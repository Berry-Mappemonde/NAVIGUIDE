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
| 2 | C1 | audit calculs | S | — | « 16 étapes (15 mer, 1 terre) · 17 escales · 1 248 points » |
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
| 23 | L6 | Nemotron | S | L2 | traduction des textes rédigés, mémoire sémantique (option) |
| 24 | G0 | globe | S | — | éprouvette globe (hors app) + décision A/B |
| 25 | G1 | globe | M | G0 | onglet Carte / Globe |
| 26 | G2 | globe | M | G1 | route, bateau, escales sur le globe |
| 27 | G3 | globe | M | G2 | couches BI, ZEE en PMTiles |
| 28 | G4 | globe | M | G3 | GRIB et climatologie en symboles |
| 29 | G5 | globe | M | G4 | popups, bulle, tracer ma route sur le globe |
| 30 | G6 | globe | S | G5, F1 | le film sur le globe |
| 31 | G7 | globe | S | G6 | parité, tests sur les deux vues |

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
python3 infra/agents/run_lots.py --only C1                                  # premier essai réel : un petit lot
caffeinate -i python3 infra/agents/run_lots.py --from P2 --until L6         # la nuit (le Mac ne dort pas)
python3 infra/agents/run_lots.py --from F1 --until F5 --stack none          # chacun depuis main
python3 infra/agents/run_lots.py --resume                                   # reprend state.json
python3 infra/agents/run_lots.py --runtime cloud --only C1                  # via l'API
python3 infra/agents/run_lots.py --dry-run --from P2 --until O              # affiche les prompts, ne lance rien
```

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

# Deux modes : Suivre et Tracer — plan du 29 septembre 2026

Décision du porteur (29 sept., 11:12) : « le mode Simulation en entier n'a plus sa place […] c'était un mode
intermédiaire qui mentalement m'a permis de fabriquer le mode Suivre ; l'application repose sur deux modes
avec deux grandes fonctions : Suivre et Tracer ». Confirmé après examen du code (ci-dessous) : Simulation est
la seconde moitié de Tracer (« Terminer » un tracé fait `setView(VIEW_SIMULATION)`) et, sur la route Berry,
un doublon du film. Ce qui ne doit pas se perdre : le **« et si » sur le plan officiel** (date de départ,
Recalculer, Demander conseil, ordres skipper sur une jambe) — il devient le contenu par défaut de Tracer,
par le bouton **Berry-Mappemonde** qui existe déjà dans la carte route.

Le porteur confie ces lots à un modèle fort (**Claude Fable**, CLI local : attribut `model="…"` de la balise
LOT, `infra/agents/run_lots.py`) ; le réviseur de nuit et Grok Bot restent ceux du batch. Références de code :
`main` @ `2489eb9`.

## 0. Ce que le code dit aujourd'hui

- Deux vues seulement : `src/constants/viewMode.js` l. 2-3 (`VIEW_SUIVRE`, `VIEW_SIMULATION`). Tracer n'est pas
  une vue : c'est `drawingMode` posé par-dessus (`src/App.jsx` l. 188 `drawRestoreRef`, l. 1163 `handleDrawStart`).
- Le commutateur visible est dans la barre film : `src/components/SimulationFilmBar.jsx` l. 409-433
  (`data-testid="film-view-switch"`, pilules `view-suivre` / `view-simulation`, `data-mode` `mode-follow` / `mode-sim`,
  libellés `followExpeditionButton` / `simulationButton`). `src/components/ViewModeSwitch.jsx` (40 l.) n'est importé
  nulle part : code mort.
- « Terminer » un tracé entre en Simulation : `src/App.jsx` l. 1152-1160 `handleCustomRoute` → `setView(VIEW_SIMULATION)`.
  L'accueil le dit : « Tracez une route perso uniquement en Simulation » (`src/i18n/fr.js` l. 109).
- Le bouton Berry-Mappemonde existe : `src/components/Sidebar.jsx`, composant `BerryCard` l. 31-206 —
  `cardMode` ∈ {`berry-active`, `berry-active-file-loaded`, `file-active`, `draw-mode`} ; pilules
  **Berry-Mappemonde | \<route perso\>** (`switcher`, l. 86-95) affichées seulement quand une route perso existe
  (`hasCustom`) ; `activateBerry` l. 51-54 → `onRouteSwitchToBerry` (`App.jsx` l. 1115-1122 : route jouée = Berry,
  **sans changer de vue**) ; `activateCustom` l. 56-60 → `onCustomRoute(drawnRoute)` ; bouton du bas
  « Berry-Mappemonde · Tracer votre propre route » l. 190-203 → `setCardMode("draw-mode"); onDrawStart()`.
- Le moteur de Simulation est celui que Tracer utilise : vaisseau virtuel (`useVirtualVessel`, `App.jsx` l. 304-314,
  `enabled: isSimulation && routeReady`), ETA, revue du plan, Recalculer (`canRecompute` l. 702-706), Demander conseil,
  ordres skipper « cette jambe (Simulation) » (`fr.js` l. 545), `SimulationPanel` (métriques du catamaran, 209 l.),
  vitesses / Play / escale auto (`App.jsx` l. 1820-1840), raccourcis clavier (l. 1051-1095), champ date de départ
  (`showDeparture={isSimulation}` l. 1688). 40 conditions `isSimulation` dans `App.jsx` : ~35 gardent ce moteur.
- Ce qui est propre au mode et disparaît : le bouton, la mémoire aller-retour Suivre ↔ Simulation
  (`simNmRef`, l. 681 et 999), la restauration de la vue précédente après « Annuler » un tracé (`handleDrawCancel`
  l. 1192-1205, `prev.view`), l'amorçage à l'entrée (`simPrimedRef` l. 683-695 : `setStartAt("saint-maur")`, profil
  normal, pause, seek) qui reste mais s'attache à l'entrée en Tracer.
- Le protocole serveur n'a pas de mode « Tracer » : `mode: isSuivre ? "suivre" : "simulation"` envoyé à `/ici`
  (`App.jsx` l. 556, 561, 717) — **inchangé** (le mot est interne).
- Recette : **34 specs Playwright** cliquent `view-simulation` en dur, 2 passent par le helper `enterSimulation`
  (`e2e/helpers.js` l. 128-131) ; `src/components/filmBarLayout.test.js` l. 28-29 exige les deux testids ;
  `infra/agents/PARCOURS_DE_REFERENCE.md` a des points « Simulation » ; la règle
  `.cursor/rules/anti-regression-visuelle-simulateur.mdc` liste « Suivre / Simulation » parmi les surfaces à garder.

## 1. La cible

| | Suivre | Tracer |
|---|---|---|
| Question | Où en sont-ils ? | Et si ? |
| Route | l'expédition telle qu'elle est (horloge officielle, journal, film « Revoir ») | la route Berry-Mappemonde **ou** la mienne (tracée / importée) |
| Temps | LIVE, ou le film | date de départ au choix, Play, vitesses, escale auto |
| Calculs | lecture seule | vaisseau virtuel, ETA, revue du plan, Recalculer, Demander conseil, ordres skipper |
| Entrée | pilule **Suivre** | pilule **Tracer** ; la carte route montre toujours **Berry-Mappemonde | \<ma route\>** + « Tracer votre propre route » + Importer |

Cliquer **Tracer** = aujourd'hui « Simulation sur la route Berry » avec la carte route sous les yeux : le « et si »
officiel est le contenu par défaut, sans geste supplémentaire. Le moteur ne bouge pas.

## 2. Ce que ça économise — honnêtement

Peu de code : ~100-150 lignes sur ~15 000 (bouton, mémoire aller-retour, restauration de vue, `ViewModeSwitch` mort,
quelques clés i18n). Ce qui est économisé, c'est la **combinatoire** : une même route jouée de deux façons (film en
Suivre, Play en Simulation) et deux jeux de règles à tenir cohérents — pilules grisées, budget 2:30, curseur LIVE,
`stories: !replay.active` — d'où une part des KO du bot et des lots RE2 / RE3 / RC22. Après : un mode de moins pour
chaque futur lot sur `App.jsx`, une branche de moins dans les specs « trois parcours », une section de moins dans le
parcours de référence.

## 3. Les lots (modèle : Claude Fable, CLI local — `model="claude-fable-5-thinking-xhigh"`)

| Lot | Titre | Taille | Risque | Dépend de |
|---|---|---|---|---|
| **DM1** | Fermer la porte : pilule Tracer à la place de Simulation ; la carte route propose toujours Berry-Mappemonde | M | faible (le mode interne ne change pas) | — |
| **DM2** | Les mots : libellés, accueil, parcours de référence, règle anti-régression, docs | S | nul | DM1 |
| **DM3** | Le ménage : `VIEW_TRACER`, `isTracer`, branches mortes, `ViewModeSwitch`, helper e2e | M | moyen (App.jsx) — **à lancer seul, après merge de DM1-DM2** | DM2 |

Ordre : DM1 et DM2 dans une même pile (une nuit) ; DM3 dans une pile à part, quand DM1-DM2 sont mergés et que le
porteur a vu l'application à deux modes. Si DM3 tombe, rien n'en dépend.

## 4. Ce qui ne change pas (plancher)

Toutes les surfaces de `main` restent joignables : carte et couches, barre film, horloge, Revoir et ses pilules, encadré
Ici, panneau droit (polaires, ordres skipper, export, calques), champ date de départ, Play / vitesses / escale auto,
Recalculer, Demander conseil, chat, tracé (Importer, Tracer, Annuler, Terminer, Revenir à Berry). Seul le **mot**
« Simulation » disparaît de l'écran, et le geste « Tracer » gagne un contenu par défaut. Décision explicite du porteur :
la règle anti-régression est mise à jour en ce sens par DM1 (ligne « Suivre / Simulation » → « Suivre / Tracer »).

## 5. Coût

Fable via le CLI : trois lancements (DM1 ≈ 400-600 k tokens avec les 34 specs, DM2 ≈ 150 k, DM3 ≈ 300-500 k). Le
modèle qui a codé chaque lot est écrit dans `state.json` (`done.<lot>.model`) et dans le journal de la boucle
(« agent local (claude-…) ») ; `COUTS.md` ne compte que les lancements du correcteur. Réviseur de nuit et Grok Bot :
inclus (Grok).

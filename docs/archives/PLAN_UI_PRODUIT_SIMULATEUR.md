> **Archivé le 22 septembre 2026 — réalisé.** Lots UI 1–9. Le lot 10 (recalcul public) reste hors périmètre. Index : [docs/README.md](../README.md).

# Plan UI / produit — NAVIGUIDE simulator

## Décisions à prendre tout de suite

- **Démarrage :** ouvrir directement en **Simulation**, carte mondiale au zoom minimal. Ne pas recentrer ensuite sur le premier point de route.
- **Suivre l’expédition :** c’est une **horloge officielle en direct**, pas un film. Le clic ouvre ce mode, referme les deux panneaux et cadre immédiatement le bateau.
- **Escales en Suivre :** les rendre consultables, datées et non cliquables. Les sauts, la lecture et le curseur restent des outils de **Simulation**.
- **Recalculer l’itinéraire :** **retirer maintenant de l’interface**. Le moteur peut rester dormant et testé côté serveur, mais son bouton promet aujourd’hui plus qu’il ne fait.
- **Logos :** rétablir immédiatement le PNG NAVIGUIDE et le favicon déjà présents. Pour Berry-Mappemonde, ne remplacer l’actuel SVG que par le fichier de marque validé par Berry : le dépôt ne permet pas d’identifier un autre original.
- **Titre du briefing :** supprimer « BRIEFING » sans inventer de titre. L’affichage du titre généré dépend d’un ajout au contrat du LLM, qui n’est pas dans ce dépôt.

## Ce que le code fait aujourd’hui

- L’application démarre sur `VIEW_SUIVRE`, avec GRIB2 activé par défaut (`DEFAULT_SHOW_GRIB = true`).
- Leaflet commence au zoom 3, puis `App` recadre la simulation au premier point au zoom 8 ; ce comportement annule la vue mondiale demandée.
- Les boutons de mode sont empilés. Les titres LANGUE, MODES, RÉSUMÉ ROUTE et POLAIRES occupent quatre lignes dans le panneau droit.
- Le panneau gauche affiche d’abord la date, puis l’encadré d’escale, puis le briefing ; les deux choix « La Rochelle / Depuis Saint-Maur » sont encore présents.
- Les fichiers originaux `public/logo-naviguide.png` et `public/favicon-n-bl.png` existent bien. Ils sont aussi servis par `https://simulator.naviguide.fr` avec le même hash ; le P0 a seulement basculé leurs références vers le SVG.
- `public/logo-berry-mappemonde.svg` est le seul asset Berry-Mappemonde trouvé dans l’historique du dépôt. Son caractère « original » ne peut pas être prouvé par le code.

## LIVE / aperçu — explication simple

- **LIVE** ne vient pas d’une balise GPS ni d’AIS : le navigateur prend l’heure actuelle, chaque seconde, et la place sur l’horloge prévue de l’expédition.
- Cette horloge appartient au voyage officiel unique Berry-Mappemonde ; son départ est fixé côté serveur et sa route ne peut pas être recalculée.
- Le GRIB2 peut ajouter la dernière météo autour du bateau, mais ne change pas la position LIVE.
- Un clic sur la barre du film, Lecture ou Précédent/Suivant en mode Suivre met `userPreview` à vrai : la vue devient un **aperçu** de la position choisie.
- Dans cet aperçu, le bateau affiché est un bateau fantôme calculé sur la route ; « Revenir au live » ou la touche `L` remet l’horloge à maintenant.
- La liste actuelle des escales appelle bien le saut, mais n’active pas l’aperçu ; le recalage automatique vers LIVE le remplace aussitôt. C’est la cause précise de son impression de bouton inactif.

## « Recalculer l’itinéraire » — rôle réel et recommandation

- Le bouton n’existe qu’en Simulation, après la création asynchrone d’un voyage virtuel et seulement pendant une navigation du bateau principal.
- Il envoie un calcul d’isochrone pour **une seule jambe**, du point simulé vers la prochaine escale à drapeau ; ce n’est pas un nouveau tour du monde.
- Le serveur renvoie un brouillon : l’ancien trait pointillé et le trait proposé cyan sont dessinés, puis l’utilisateur doit encore Accepter ou Garder Searoute.
- La simulation crée pourtant ce voyage avec `forecast: false` : aucun cube météo de prévision n’est préparé ; le calcul repose donc sur la climatologie de repli, malgré un libellé qui laisse attendre une météo recalculée.
- L’état « prévision indisponible » n’est pas montré dans le panneau Simulation, et le bouton désactivé n’explique pas pourquoi il l’est.
- **Recommandation : retirer le bouton et la boîte de dialogue de l’UI maintenant**, conserver l’API et ses tests, puis ne le réintroduire qu’avec une prévision nommée, un statut lisible et une comparaison explicite de la jambe.

## Lots d’implémentation ordonnés

| Lot | Décision et résultat visible | Fichiers / symboles | Effort | Risque visuel |
|---|---|---|---|---|
| 1 — marque et défauts sûrs | Rebrancher le logo NAVIGUIDE sur `/logo-naviguide.png` et le favicon sur `/favicon-n-bl.png`. Garder le logo Berry actuel tant que Berry n’a pas validé ou fourni son fichier original ; ne pas en fabriquer un nouveau. Décocher GRIB2 au démarrage. | `index.html`; `src/components/Sidebar.jsx` (`NAVIGUIDE_LOGO`, `BERRY_LOGO`); `public/`; `src/constants/layers.js` (`DEFAULT_SHOW_GRIB`); test `src/constants/layers.test.js` | Faible | Faible : taille et rendu du PNG à vérifier dans l’en-tête |
| 2 — panneau droit compact | Supprimer les quatre titres de sections. Mettre le sélecteur FR/EN et le basculeur sombre/clair sur une seule rangée, avec des libellés accessibles (`aria-label` / infobulle). Garder les statistiques et l’import de polaire, sans changer leur comportement ni le chargement automatique de la polaire. | `src/components/ToolsSidebar.jsx` (`Toggle`, structure des sections); `src/i18n/fr.js`, `src/i18n/en.js` si les libellés changent | Faible | Moyen : vérifier les largeurs à 320 px et les textes EN/FR |
| 3 — panneau gauche resserré | Supprimer le choix visible de départ terre/mer, sans changer le scénario Simulation actuel : il conserve `saint-maur` en interne. Réduire les marges verticales entre « Date de départ », « Jour (UTC) » et les champs. Placer la carte de briefing avant la date de départ. | `src/components/DepartureField.jsx`; `src/components/Sidebar.jsx`; `src/App.jsx` (`simPrimedRef`, `selectView`) | Faible | Faible : vérifier que la date et l’heure restent éditables et que les 4 h terrestres ne changent pas sans décision produit |
| 4 — deux modes sur une ligne | Mettre « Suivre l’expédition » et « Simulation » dans deux boutons sur la même ligne. Employer un libellé court sur le bouton et conserver Berry-Mappemonde dans l’infobulle ou le contexte, afin d’éviter trois lignes de texte dans 320 px. | `src/components/ViewModeSwitch.jsx`; `src/i18n/fr.js`; `src/i18n/en.js`; `src/constants/viewMode.test.js` | Faible | Moyen : contraste, retour à la ligne et zone tactile |
| 5 — démarrage Simulation, carte monde | Changer l’état initial en Simulation. Après le chargement, garder une vue mondiale au zoom minimal Leaflet (2), centrée comme la carte initiale, au lieu du recadrage au premier point au zoom 8. Conserver une éventuelle vue de recette explicitement demandée par son paramètre. | `src/App.jsx` (état `view`, placement initial de caméra); `src/hooks/useSimulatorMap.js` (vue et zoom initiaux); `src/utils/sceneGate.js` et tests si la porte de chargement est touchée | Moyen | Moyen : s’assurer que le masque disparaît et qu’aucun effet tardif ne vole la caméra |
| 6 — entrée Suivre = LIVE cinéma | Remplacer le basculement générique par une entrée explicite et idempotente en Suivre : aperçu désactivé, panneaux mémorisés puis fermés, `cinemaMode` et suivi caméra activés. Quand l’horloge devient disponible, cadrer le bateau sans lancer une lecture artificielle : LIVE avance déjà avec l’heure réelle. | `src/App.jsx` (`selectView`, `toggleCinema`, `recaptureBoat`, `goLive`); `src/hooks/useFilmCamera.js` | Moyen | Moyen : ne pas quitter le cinéma par erreur lors d’un second clic et conserver Échap / déplacement manuel |
| 7 — Suivre : programme officiel, pas film | En Suivre, transformer l’encadré « Escales » en « Programme officiel » : escales passées, étape courante et prochaine escale sont déterminées par l’horloge officielle, avec leurs dates prévues et jours à quai. Aucune ligne ne saute dans le temps. Retirer dans ce mode le curseur cliquable, Play/Pause, Précédent/Suivant et leurs raccourcis ; garder ces interactions en Simulation uniquement. | `src/components/EscaleLegend.jsx`; `src/components/SimulationPanel.jsx`; `src/components/SimulationFilmBar.jsx`; `src/App.jsx` (`handleSidebarSeek`, `handleSimNext`, `handleSimPrev`, raccourcis) | Moyen | Moyen : bien distinguer « prévu par l’horloge » d’une position réellement mesurée |
| 8 — Simulation : recentrage ponctuel aux escales | Lorsque la lecture est arrêtée, un clic Précédent/Suivant en Simulation doit, après le saut, recentrer une fois la carte sur le bateau. Préserver le zoom choisi par la personne et ne pas activer le cinéma ni un suivi permanent. Pendant la lecture, conserver le comportement actuel. | `src/App.jsx` (`handleSimNext`, `handleSimPrev`); `src/hooks/useFilmCamera.js` (jeton de focus ponctuel ou équivalent); tests de caméra / mode à créer | Moyen | Faible à moyen : ordre des mises à jour route/caméra et passage des sauts aériens |
| 9 — titre de briefing généré | Retirer le titre fixe « BRIEFING ». Ajouter côté interface un champ optionnel `briefing_title` au contrat `expedition_plan`, le montrer au-dessus du texte uniquement s’il existe et ne jamais fabriquer un faux titre local. Le briefing `ici()` est aujourd’hui généré localement et prioritaire ; décider s’il reçoit lui aussi un titre LLM ou s’il reste sans titre. | `src/components/Sidebar.jsx`; `src/App.jsx` (lecture/cache de `expedition_plan`); `src/utils/customRouteBriefing.js`; contrat externe `${VITE_ORCHESTRATOR_URL}/api/v1/expedition/plan` **hors dépôt** | Moyen, bloqué par le contrat LLM | Faible : contenu plus court, mais dépendance externe à valider avant livraison |
| 10 — retirer le faux recalcul public | Enlever le bouton de `SimulationPanel` et le montage de `RecomputeDialog` de l’interface. Laisser `useVirtualVessel`, `useAltRouteLayer`, l’API `/voyage/{id}/recompute` et leurs tests en place, sans appel utilisateur, pour ne pas détruire le travail expérimental. Documenter le critère de retour : prévision réellement activée, statut visible, une jambe clairement comparée. | `src/components/SimulationPanel.jsx`; `src/App.jsx`; `src/components/RecomputeDialog.jsx` (non monté ou retrait ultérieur); `src/hooks/useVirtualVessel.js`; `server/voyage_api.py` et tests inchangés | Faible | Faible : vérifier que Simulation continue de créer et afficher sa route normalement |

## Suivi d’implémentation — PR #165

- [x] Lot 1 — les PNG NAVIGUIDE et Berry validés sont branchés ; le favicon PNG est rétabli et GRIB2 est décoché par défaut.
- [x] Lot 2 — le panneau droit est compacté, sans ses quatre titres de sections ; langue et thème partagent une rangée.
- [x] Lot 3 — le choix de départ terre/mer est retiré de l’interface, Saint-Maur reste le départ interne de Simulation, et le briefing précède la date.
- [x] Lot 4 — les deux modes sont sur une ligne.
- [x] Lot 5 — Simulation et la vue mondiale au zoom minimal sont les valeurs initiales ; aucun recadrage tardif au premier point.
- [x] Lot 6 — Suivre ouvre LIVE directement en cinéma, ferme les panneaux et cadre le bateau sans lancer de lecture artificielle.
- [x] Lot 7 — la lecture, le curseur, Play/Pause, les sauts et leurs raccourcis sont réservés à Simulation. La transformation des escales en « programme officiel » reste volontairement hors périmètre.
- [x] Lot 8 — un saut Précédent/Suivant arrêté en Simulation recentre ponctuellement le bateau en conservant le zoom, sans activer le cinéma.
- [x] Lot 9 — le titre fixe est supprimé ; `briefing_title` est accepté de façon optionnelle et n’est affiché que s’il vient du plan d’orchestration.
- [ ] Lot 10 — « Recalculer l’itinéraire » reste inchangé, volontairement hors périmètre.

## Dépendances et validations avant mise en ligne

- **Asset Berry :** Berry valide que `logo-berry-mappemonde.svg` est bien le logo attendu, ou fournit le fichier original (nom, format et fond transparent). Aucun logo ne doit être redessiné à partir de l’actuel.
- **Titre LLM :** le service d’orchestration doit renvoyer un `briefing_title` court, dans la langue demandée, en plus de `executive_briefing`. Sans ce contrat, le simulateur peut supprimer le titre statique mais ne peut pas « demander au LLM » lui-même.
- **Tests automatisés :** adapter le test GRIB par défaut, les tests de libellés de mode et les tests de porte de scène ; exécuter `npm test` puis `npm run build`.
- **Vérification manuelle :** démarrage sur Simulation/zoom monde/GRIB décoché ; boutons de mode sur une ligne ; panneaux compacts aux deux langues ; retour des deux PNG NAVIGUIDE ; entrée Suivre directement LIVE cinéma ; escales non scrubbables en Suivre ; Précédent/Suivant recentrent seulement en Simulation arrêtée.
- **Non-régression caméra :** déplacement manuel désactive le suivi cinéma, Échap restaure les panneaux, et les passages Cayenne–Halifax / antiméridien restent cadrés correctement.

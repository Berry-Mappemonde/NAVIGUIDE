# Plan de corrections — 28 septembre 2026 : « le film raconte la route » (RG16, RG1 → RG15, puis RH1, RH2)

Batch décidé par le porteur le 28 sept. au matin, après sa revue globale de la pile #386 (mergée le
28 sept. 06:32 UTC) : *« il faut prévoir un plus gros batch centré sur l'amélioration du film et du
discours »*. Les constats détaillés, la transcription intégrale du film servi, les mesures de cinématique
et le gabarit d'étape validé sont dans **`docs/FILM_DISCOURS_ETAT_2026-09-28.md`** (à lire en entier
avant tout lot — c'est la revue du porteur). Ce plan en tire les causes (lues sur `main` @ `68970d2`),
les décisions et les lots. Les lots RH1 et RH2 du plan s5 (`PLAN_CORRECTIONS_2026-09-27-s5.md`) sont
gardés en queue de ce batch, inchangés.

## 0. Rappels (à lire avant tout lot)

- **Données réelles seulement.** La voix ne dit que ce que le stock (RF2) sait : ZEE, ports, marinas, AMP,
  projets Blue Intelligence, stations, climatologie, distances et dates de l'horloge. Aucune phrase de
  remplissage, aucun chiffre ni nom inventé ou rédigé par un LLM (RG11, optionnel et hors batch, est le
  seul lot qui touche à un LLM — avec vérification automatique).
- **Le bateau suit la voix, jamais l'inverse** (27 sept.) : débit de voix constant ; chaque phrase est
  ancrée à l'instant du trajet dont elle parle ; le bateau est là où la phrase le dit.
- **`main` est le plancher de l'interface** (`.cursor/rules/anti-regression-visuelle-simulateur.mdc`) :
  aucune surface visible ne disparaît (pilules 2:30 / 3:00, Suivre / Simulation, barre film, onglets…).
- **Le stock RF2 est la source** : un lot qui change le script du film ou les moments change le calcul du
  remplisseur (`scripts/prepare_official_store.py`, familles `moments` / `film`), pas un chemin de requête.
  La clé de version du stock doit changer quand le calcul change (sinon le poste sert l'ancien texte).
- **Recette sur le poste** (`ensure-dev.sh --prod`, stock rempli par le vrai calcul) : les valeurs écrites
  dans la rubrique Recette de la PR sont LUES sur le poste, jamais des constantes du code.
- **Pas de vidéo, pas de secret, pas de merge.** Une PR par lot, gabarit `docs/REGLES_WORKFLOW_AGENT.md` § 3.

## 1. Les constats (résumé — le détail est dans FILM_DISCOURS_ETAT § 1-5)

Le film servi le 28 sept. (11 chapitres, 2 913 caractères, variantes 2:30 et 3:00 identiques) :

- **Faits faux** : « le 18 mai, départ vers Ajaccio » alors que l'horloge a le bateau en mer depuis le 15 ;
  le vol Cayenne ⇄ Saint-Pierre raconté comme une traversée puis « départ vers Papeete » depuis
  Saint-Pierre ; l'« AMP » citée est une zone de dépôt de pétoncles ; « Départ vers La Rochelle » pour un
  trajet par la route.
- **Contenu absent** : ZEE jamais nommées (« 3 zones économiques exclusives traversées » ×7) alors que le
  stock en a 134 entrées datées ; aucun port ni côte longée (44 ports dans le stock) ; distance et durée
  d'étape 2 fois sur 11 ; marina d'arrivée jamais nommée ; aucune AMP réelle ; **aucun projet Blue
  Intelligence** (couche absente des perles : 0 moment sur 770) ; **aucun changement de climatologie** ;
  aucun cap ; ni ouverture ni fin.
- **Forme** : un gabarit répété dix fois, « 3 jours à quai » ×10, une date par phrase, jargon (« jambe »,
  « Couloirs : », « À surveiller. », « à portée de »), « de de Fineveke », titres anglais.
- **Cinématique** (mesures § 5.1) : 44 fps avec 8,3 % de frames > 34 ms ; bateau immobile à l'écran deux
  frames sur trois puis bonds de 12-29 px ; caméra à sa butée (29 px/frame) ; vitesse du temps-film de
  0 à 154 h de voyage par seconde d'une phrase à l'autre ; menée par la voix, dent de scie à chaque mot
  (rapport 6,8) ; ancre au début de la phrase (le bateau quitte le lieu pendant qu'on en parle).
- **CI Playwright inutile** (porteur, 28 sept. : « elle est longue et ne sert pas à grand chose ») —
  mesuré sur le dernier run vert de `main` (36388263060) : le job « fumée Playwright » dure **10 min**,
  dont **9 min** pour les specs de lots ; **58 specs sur 101 échouent** et le job est vert quand même
  (`continue-on-error`). Les échecs sont des contrats périmés, pas des régressions : 12 specs attendent
  l'ouverture en Simulation (`view-simulation` = true) alors que RF7 a décidé l'accueil en Suivre ; 9
  attendent `plan-review` visible alors que RD9 l'a mis dans un onglet ; `film-duration` visible hors
  film (RE3 / RF8) ; « Aujourd'hui, le bateau est à » (RC17 a changé la phrase de fin) ; « 15 mai 2025 »
  (année) ; zoom d'accueil ≤ 2,25 (RC18 a posé un plancher de dézoom) ; `regime-legend` /hindcast/
  (la CI n'a pas d'hindcast) ; `route-summary`, `expedition-story`, `ici-story-slot` (surfaces
  déplacées). Personne ne lit ces rouges : la « recette automatique de chaque lot » n'existe plus.
- **Carte au dézoom** (revue du 27 sept.) : drapeaux et bateaux qui se baladent horizontalement au
  zoom / dézoom, monde vu plusieurs fois — deux garde-fous posés dans #386 (plancher de dézoom en
  Suivre, gel des marqueurs pendant l'animation), le reste à reproduire et corriger (RG15).

## 2. Priorités du porteur

1. **Le récit raconte la route** — juste (dates et lieux de l'horloge), complet (eaux, côtes, AMP,
   projets, climatologie, distances), dans l'ordre chronologique, en français parlé sans jargon.
2. **Le bateau avance de manière fluide et est où la phrase le dit** — motion design § 5.4 validé le
   28 sept.
3. **La carte au dézoom** ne bouge pas toute seule (drapeaux, bateaux, monde une fois).
4. **Robustesse et console** (RG9, RH1, RH2).

## 3. Décisions

- **D1 — Ancre au nom du lieu.** L'instant d'un événement ponctuel est atteint quand la voix prononce le
  nom du lieu (compensé de l'avance de 12 caractères du client), pas au premier mot de la phrase. Une
  phrase de durée (escale) porte deux ancres (arrivée au début, départ à la fin). Un départ s'ancre au
  premier mot, une arrivée au dernier.
- **D2 — Gouverneur de rythme.** La vitesse du bateau à l'écran est bornée. Si une phrase porte plus de
  route que la vitesse maximale ne permet, la **voix attend en fin de phrase** (silence, jamais coupée au
  milieu) pendant que le bateau avance à v_max. Si le bateau est à quai, le temps-film **saute l'escale**
  après la phrase qui la dit. L'écran ne reste jamais figé plus de ~2 s.
- **D3 — Débit de voix constant, prédiction entre les mots.** Les frontières de mot corrigent doucement
  une avance prédite au débit mesuré ; plus de bond par mot.
- **D4 — AMP = aires protégées seulement.** Filtre à la source des événements (catégorie IUCN / WDPA ;
  exclusion des zones de réglementation de pêche : « Chaluts », « Filets », « Huîtres », « deposit »,
  « licence », « prohibition »). Noms parlés (pas de titres de jeux de données).
- **D5 — Projets Blue Intelligence dans les perles.** Le sac « ici » des perles du voyage porte la couche
  `projects` (export BI, `gold_on`), et les événements de route en tirent « projet à proximité ».
- **D6 — Climatologie honnête.** Un changement notable est dit avec ses chiffres (force, direction, date)
  et sa nature : « vents moyens de saison » (climatologie) ou « mesuré » (hindcast). Rien n'est inventé
  quand l'atlas manque (repli de zone : dit comme tel, ou tu).
- **D7 — Les pilules 2:30 / 3:00 produisent des textes différents** ; une troisième variante
  « intégral » existe côté serveur ; la durée estimée s'affiche.
- **D8 — RG11 « Rédigé » (LLM) est hors batch**, documenté pour plus tard.
- **D9 — RH1 et RH2 restent en queue du batch**, inchangés.
- **D11 — La CI Playwright devient la recette automatique, bloquante.** Chaque spec de lot est
  ramené au contrat actuel du produit (la décision qui l'a changé est citée), marqué `poste` s'il dépend
  de données que la CI ne peut pas avoir (hindcast, LLM, réseau), ou supprimé si la surface n'existe
  plus par décision — jamais affaibli pour passer. Une vraie régression trouvée en chemin est notée,
  pas masquée. Puis `continue-on-error` disparaît : un spec rouge = PR rouge. Un lot n'est fini que si
  son spec passe avec `npm run e2e:store`. Objectif de durée : ≤ 4 min pour le job.
- **D10 — Chaque lot est mesurable** : le script `naviguide-simulator/scripts/film-cinematique.mjs` (livré
  avec la revue) et un test serveur du discours (RG10) donnent des seuils, écrits dans la rubrique Recette.

## 4. Les lots

Pour chaque lot : constat → cause lue sur `main` (fichier:ligne) → ce qui change → tests → recette.
Le prompt complet, exécutable par `infra/agents/run_lots.py`, est dans `docs/LOTS_ORDRE_ET_PROMPTS.md` § 2.

### RG16 — La CI Playwright utile : recette automatique des lots, bloquante, ≤ 4 min (M) — en premier
- Constat : § 1 « CI Playwright inutile » (58 specs rouges sur 101, 9 min, job vert).
- Causes : `.github/workflows/ci.yml` job `simulator-e2e` (`continue-on-error: true` sur les specs de
  lots ; `npx playwright install --with-deps chromium` à chaque run, 32 s ; deux invocations Playwright) ;
  `naviguide-simulator/playwright.config.js` l. 44-48 (retries 1 en CI, 4 workers) ; `e2e/lots/*.spec.js`
  (101 specs, un par lot, jamais relus quand une décision change le produit) ; `scripts/e2e-store-api.sh`
  + `server/tests/fixtures/official_store.tar.gz` (stock figé : climo, film, ici, moments, plan_review —
  pas d'`eta`) ; `docs/REGLES_WORKFLOW_AGENT.md` (aucune règle « le spec du lot passe avec l'API »).
- Ce qui change : triage des 58 specs rouges, un par un, en trois sorts (contrat actuel, `poste`,
  supprimé) avec la décision citée dans la PR ; les régressions réelles trouvées sont listées dans
  « reste à faire » (pas corrigées ici, pas masquées) ; `continue-on-error` retiré ; une seule invocation
  Playwright (fumée + lots) avec l'API sur le stock figé, navigateurs mis en cache (`actions/cache` sur
  `~/.cache/ms-playwright`, clé = version de Playwright), reporter `github` + résumé d'étape
  (`$GITHUB_STEP_SUMMARY` : specs rouges nommés) ; `eta` ajouté au stock figé si des specs en ont besoin ;
  REGLES § 3 : « un lot n'est fini que si `npm run e2e:store -- e2e/lots/<spec>` passe » ; nom du job :
  « simulateur — recette automatique (Playwright, stock figé) ».
- Tests : la suite complète verte en CI (0 rouge, 0 `did not run`) en ≤ 4 min ; les specs `poste`
  ignorés en CI et joués par le script de recette sur le poste.
- Recette : ouvrir le run CI de la PR → job vert, résumé d'étape listant 0 spec rouge, durée ≤ 4 min ;
  casser volontairement un spec en local → le job passe rouge (montre-le dans la PR, puis retire).

### RG1 — Faits justes : départ de l'horloge, le vol est un vol, la route est la route (M)
- Constat : A1, A2, A5 (FILM_DISCOURS_ETAT § 3).
- Causes : `server/film_script.py` `_window_depart_ms` l. 491 (départ = tA + jours d'escale de la règle,
  pas l'instant où l'horloge quitte le port) ; `_windows` l. 1496 (fenêtres par escale sans distinction
  du mode avion : la jambe Cayenne → Saint-Pierre est traitée comme une navigation, la jambe suivante
  part de Saint-Pierre) ; `_air_bits_from_moments` l. 2327 (l'avion n'est qu'un ajout en fin de
  chapitre) ; `_depart_towards` l. 1619 (« Départ vers La Rochelle » sans « par la route »).
- Ce qui change : le départ d'une étape est lu sur l'horloge (premier sommet qui quitte le port) ; les
  fenêtres avion sont typées (`mode: "air"`), racontées comme un vol (« L'équipage s'envole de Cayenne
  pour Saint-Pierre-et-Miquelon ; le bateau attend à Cayenne ; retour le … »), la navigation suivante
  repart du port où le bateau est resté ; Saint-Maur → La Rochelle est dit « par la route » ; la clé du
  stock `film` change.
- Tests : `server/tests/test_film_script.py` — départ = horloge (écart 0 quand l'horloge quitte à tA) ;
  fenêtre air non racontée comme navigation ; jambe suivante depuis Cayenne ; ancres cohérentes
  (position du bateau à l'ancre « départ » = port).
- Recette : Revoir → « départ » de La Rochelle dit avec le bateau à La Rochelle (pas au large de la
  Galice) ; à Cayenne, la voix dit le vol, le bateau reste à Cayenne, puis repart de Cayenne.

### RG2 — Nommer ce qu'on traverse : eaux, côtes, détroits, ports, cap (M)
- Constat : B1, B2, B6, D4.
- Causes : `server/film_script.py` `_group_changes` l. 1888 et `_group_sentence` l. 2019 (les ZEE sont
  agrégées en « N zones économiques exclusives traversées ») ; `_ZEE_NATION` l. 131 (table incomplète :
  « Zone économique exclusive (Barbadian) », « Overlapping claim Western Sahara ») ; `select_chapter_changes`
  l. 1965 (les ports / WPI croisés ne sont pas des candidats de récit) ; `server/ici_warm.py`
  `route_events_from_pearls` l. 268 (kinds zee / sci / poe / amp ; les ports du sac ne deviennent pas des
  événements « côte longée ») ; cap : `moment.leg.headingDeg` n'est lu nulle part par le film.
- Ce qui change : chaque entrée de ZEE datée devient une phrase courte en français parlé (« le 16 mai,
  les eaux espagnoles ») — dosage : toutes en traversée courte, au plus une par jour de film en
  traversée longue, regroupées quand elles se suivent (« Antigua, Saint-Kitts puis Sint-Eustatius ») ;
  la table des noms parlés est complétée pour toutes les ZEE de la route officielle (y compris
  « eaux disputées du Sahara occidental », « haute mer ») ; les ports / WPI à moins de 25 nm deviennent
  des jalons de côte (« longe la Galice — Camariñas, Muxía », « le détroit de Gibraltar entre Tanger et
  Algeciras ») ; le cap au départ (« cap au sud-ouest ») vient de `headingDeg`.
- Tests : noms parlés pour 100 % des ZEE du plan-review de la route officielle ; aucune phrase « N zones
  économiques exclusives » ; jalons de côte ordonnés par la route.
- Recette : La Rochelle → Ajaccio : la voix nomme, dans l'ordre, les eaux espagnoles, la Galice, le
  Portugal, Gibraltar, le Maroc, la Sardaigne / eaux italiennes, la Corse ; jamais « zone économique
  exclusive » ; le bateau est dans les eaux nommées quand elles sont nommées.

### RG3 — AMP réelles et projets Blue Intelligence à proximité (M)
- Constat : A3, B3, B4, D1.
- Causes : `server/moment_journal.py` l. 32 et `server/ici_warm.py` l. 269 (toute entrée « mpa » du sac
  devient une alerte AMP, y compris les zones de réglementation de pêche) ; `server/film_script.py`
  `alert_is_amp` l. 417 (ne filtre que le vocabulaire IUCN) ; `server/ici_engine.py` l. 795-851
  (`lean = thin and not rich` → `proj_t = None` : les perles du voyage sont calculées sans la couche
  `projects`) ; aucun kind « projet » dans `route_events_from_pearls`.
- Ce qui change : filtre AMP (D4) à la source ; les perles du voyage portent la couche `projects`
  (export BI, `gold_on`, distance) — le remplisseur recalcule les perles concernées ; nouveau kind
  `project` dans les événements de route (« à douze milles, le projet X ») ; dosage : au plus une AMP et
  un projet par étape courte, deux ou trois par traversée, les plus proches d'abord, `gold_on` d'abord.
- Tests : une zone « Chaluts » n'est jamais une AMP ; un projet à 10 nm produit un événement ; dosage
  respecté ; aucune régression des sacs « ici » (mêmes clés + `projects`).
- Recette : Revoir → au moins une AMP au nom réel (Pertuis charentais - Rochebonne…) et au moins un
  projet Blue Intelligence nommé sur le voyage, chacun dit quand le bateau est à moins de 30 nm ;
  panneau gauche « ici » → la fiche projet existe pour le même point.

### RG4 — La climatologie racontée : changements notables, honnêteté (M)
- Constat : B5, D5.
- Causes : `server/official_store.py` `compute_climo` l. 690-711 (régime, `windKnots`, `dirFromDeg` par
  sommet, jamais transformés en événements) ; `server/voyage_api.py` `_regime_portions` l. 935 (portions
  hindcast / prévision / climatologie, non racontées) ; `server/climatology_zones.py` `zone_wind_at` l. 24
  (repli de zone grossier, indistinguable d'un atlas dans le film) ; aucun kind « climo » dans le film.
- Ce qui change : détection sur l'horloge des changements notables — bascule de régime (entrée dans les
  alizés de nord-est, calmes équatoriaux, vents d'ouest…), saut de force ≥ 8 kn ou de direction ≥ 60°
  tenu ≥ 24 h — datés et positionnés ; phrase avec les chiffres (« le 14 juin, au sud du Cap-Vert, les
  alizés de nord-est s'installent : quinze nœuds de saison ») et la nature (« de saison » = climatologie,
  « mesuré » = hindcast) ; repli de zone : dit « vents moyens » sans chiffre précis, ou tu ; dosage : au
  plus deux par traversée.
- Tests : détection sur une horloge synthétique (un saut de régime → un événement, du bruit → aucun) ;
  jamais de chiffre quand la source est le repli de zone ; phrase FR/EN.
- Recette : Ajaccio → Fort-de-France : la voix dit au moins un changement de vent, daté, avec le bateau
  au bon endroit ; la teinte de la route (violet = climatologie) est cohérente avec « de saison ».

### RG5 — Stations qualifiées (S)
- Constat : A4, D2.
- Causes : `server/film_script.py` `station_name_speakable` l. 405 (rejette les codes, pas les titres de
  jeux de données) ; `_group_changes` l. 1888 (comptage « N stations croisées »).
- Ce qui change : une station n'est dite que qualifiée (flotteur Argo n°…, campagne PELGAS, bouée,
  station côtière, observatoire) depuis les métadonnées du sac (source, type) ; une par étape au plus, la
  plus proche ; les titres de jeux de données sont interdits à la voix ; plus de comptage.
- Tests : « Bacteria in Rias of Galicia » jamais prononcé ; « Argo 6904216 » → « un flotteur Argo » ;
  au plus une station par chapitre.

### RG6 — Gabarit narratif par étape (M)
- Constat : C1-C6, B7, B8 ; gabarit validé FILM_DISCOURS_ETAT § 4.
- Causes : `server/film_script.py` `build_raw_from_moments` l. 2373 (ordre fixe : quai → « départ vers »
  → air → mer → « Arrivée à … 3 jours à quai » + annexe « À surveiller. Couloirs : … La jambe compte
  … ») ; `_depart_towards` l. 1619, `_arrival_sentence` l. 1637, `change_sentence` l. 2037 (gabarits
  uniques) ; `_close_sentence` l. 1591 ; connecteurs par rotation ; `fit_chapter_text` l. 2156.
- Ce qui change : ouverture (date, port, cap, destination, milles, jours de mer, vitesse moyenne — tous
  du plan-review / horloge) → route dans l'ordre (RG2-RG5) → escale (arrivée datée, marina ou port
  d'arrivée nommé, durée dite une fois et variée) ; une date toutes les deux phrases au plus ; liste de
  mots interdits (« jambe », « zone économique exclusive », « Couloirs », « À surveiller », « à portée
  de », titres anglais, « de de ») ; connecteurs liés au contenu ; annexe supprimée et fondue ; variantes
  lexicales pour départ / arrivée / escale.
- Tests : structure par chapitre (ouverture, ≥ 1 fait de route, escale) ; mots interdits absents ; dates
  ≤ 1 par 2 phrases ; distance et jours présents dans 100 % des chapitres de navigation.
- Recette : le chapitre La Rochelle → Ajaccio se lit comme le gabarit § 4.

### RG7 — Ouverture et fin du film (S)
- Constat : B9.
- Causes : `build_raw_from_moments` l. 2373 (premier chapitre = « L'expédition … a quitté Saint-Maur ») ;
  `_close_sentence` l. 1591 (« Aujourd'hui, le bateau est en mer, à N milles de X. »).
- Ce qui change : ouverture (expédition, date de départ, nombre d'escales et milles totaux du plan-review,
  destination finale) ; fin (aujourd'hui, ETA de la prochaine escale depuis le stock `eta`, les escales à
  venir nommées).
- Tests : ouverture et fin présentes, chiffres = plan-review / eta.

### RG8 — Budgets réels 2:30 / 3:00 / intégral (S)
- Constat : E1.
- Causes : `server/official_store.py` `FILM_VARIANT_SECONDS = (150, 180)` l. 28 et `compute_film` l. 773
  (mêmes candidats, texte sous le plafond → identique) ; `select_chapter_changes` l. 1965 (budget =
  plafond, pas une sélection par priorité) ; client `SimulationFilmBar.jsx` (pilules sans durée estimée).
- Ce qui change : sélection par priorité et par budget (2:30 = ouverture, eaux principales, une AMP ou
  un projet, escales ; 3:00 = + côtes, climatologie ; intégral = tout) ; durée estimée (caractères /
  débit) affichée à côté des pilules ; débit constant conservé.
- Tests : trois variantes de longueurs strictement croissantes ; la 2:30 tient dans 150 s ± 10 % au
  débit mesuré.

### RG9 — Client robuste : sans voix, onglet caché, sous-titre par phrase (S)
- Constat : E2, E3, E4 ; KO bot #386 (« ended=true à 53 s, chapterIdx 0 »).
- Causes : `src/hooks/useReplay.js` l. 704-712 (`shouldHoldFilmForBudget` / `voiceSpokenAllRef`),
  `onVoiceEnd` sans frontière → `finish()` ; l. 741 (chien de garde 12 s) ; `linearFilmAt` ; boucle rAF
  suspendue quand l'onglet est caché (aucune reprise douce) ; `src/components/SimulationFilmBar.jsx`
  l. 312 (`film-subtitle` = texte du chapitre).
- Ce qui change : sans moteur vocal ou sans frontière après 2 s, horloge murale dès le départ, fin
  seulement à la dernière phrase ; `visibilitychange` → au retour, rattrapage lissé (≤ 2 s) au lieu d'un
  saut ; sous-titre = phrase en cours (découpage serveur en phrases + `charIdx`), nom du lieu mis en
  avant quand il est dit.
- Tests : film sans `speechSynthesis` → dure ≥ 90 % de la durée estimée, `ended` seulement à la fin ;
  sous-titre change à chaque phrase.

### RG10 — Recette automatique du discours (S)
- Constat : tout § 3 C-D.
- Ce qui change : `server/tests/test_film_discours.py` lit le film produit par `build_raw_from_moments`
  sur les moments d'exemple et sur le stock du poste (test marqué `poste`, ignoré en CI) : mots
  interdits, « de de », titres anglais, comptages sans nom, dates en rafale, phrases > 30 mots, ordre
  chronologique des ancres, chaque chapitre avec ouverture / route / escale ; parcours de référence du
  bot (`infra/agents/PARCOURS_DE_REFERENCE.md`) mis à jour avec ces points.

### RG12 — Vitesse continue du bateau (M)
- Constat : § 5.1, § 5.2-1, § 5.2-2 ; D2, D3.
- Causes : `src/engine/replay.js` `anchoredTimeAt` l. 506 (ligne brisée entre ancres : paliers de vitesse
  par phrase) ; `voiceLedStep` l. 208 et `advanceReplayTime` l. 162 (fraction `dt / horizon` de l'écart
  à chaque frame, cible qui ne bouge qu'à la frontière de mot → dent de scie, rapport 6,8) ;
  `FILM_VOICE_LOOKAHEAD_CHARS` l. 32 ; `src/hooks/useReplay.js` (aucune borne de vitesse écran, aucun
  saut d'escale, aucune attente de la voix).
- Ce qui change : interpolation monotone lissée (pente continue) entre ancres ; avance prédite au débit
  mesuré entre deux frontières, correction douce à la frontière (rapport max/min d'avance par frame
  ≤ 1,5 sur une phrase) ; gouverneur : vitesse écran bornée (v_min, v_max en px/s à la frame), la voix
  attend en fin de phrase quand la route dépasse v_max (hook voix : pause entre deux phrases, jamais au
  milieu), saut d'escale après la phrase qui la dit (le bateau à quai ne fige jamais l'écran plus de ~2 s).
- Tests : simulation Node du pas de temps (frontières synthétiques) → rapport ≤ 1,5, aucune frame à
  l'arrêt hors escale, vitesse écran dans les bornes ; l'attente de la voix ne coupe jamais une phrase.
- Recette : `node scripts/film-cinematique.mjs` sur le poste → « pas nuls hors escale » = 0, vitesse du
  temps-film sans saut > ×3 d'une seconde à l'autre ; à l'œil : le bateau glisse, sans à-coup à chaque mot.

### RG13 — Caméra et rendu à 60 Hz (M)
- Constat : § 5.1, § 5.2-3 à 5.2-6.
- Causes : `src/map/filmCamera.js` `applyFilmCamera` l. 336 (`setView(…, { animate: false })` à chaque
  frame = `_resetView` Leaflet, toutes les couches redessinées) ; `clampFilmPan` l. 34 et
  `FILM_PAN_MAX_SCREEN = 0.02` (`src/engine/replay.js` l. 36 — la caméra décroche au-delà de 29 px/frame) ;
  `filmViewCenter` l. 117 (cadrage sur le cap instantané) ; `src/map/ScenePlaybackController.js`
  `SCENE_INTERVAL_MS = 125` l. 6 (sillage et acteurs à 8 Hz via `renderDynamic`
  `MapSceneController.js` l. 1329) ; `syncFilmCamera` l. 1143-1204 (`flyTo` 1,2 s puis rattrapage,
  garde `zoomAnimating` sans repositionnement).
- Ce qui change : déplacement de la carte par translation du plan pendant le film (`panBy` sans
  animation ou transform du pane, un `_resetView` au plus toutes les N frames / à l'arrêt) ; couches
  lourdes (route canvas complète, roses, ZEE) redessinées à l'arrêt seulement — la route visible du film
  est un tracé léger ; cadrage sur le cap lissé de la jambe ; butée de pan liée à la vitesse du bateau
  (le bateau reste dans les 40 % centraux) ; resserrement de zoom à l'approche (dernières 10 % de
  l'étape) et élargissement au départ, animés ; sillage, acteurs et bulle rendus à la frame pendant le
  film ; changement d'étape : un seul mouvement, le bateau continue d'être posé pendant l'animation.
- Tests : tests de `filmCamera.js` (pas de `setView` par frame ; bornes ; cap lissé) ; `ScenePlaybackController`
  à la frame en mode film.
- Recette : `node scripts/film-cinematique.mjs` → ≤ 1 % de frames > 34 ms, pas nuls hors escale = 0,
  bateau jamais à plus de 40 % du centre ; à l'œil : plus de bond au changement d'étape.

### RG15 — La carte au dézoom : drapeaux, bateaux et monde restent à leur place (M)
- Constat : revue du porteur du 27 sept. (« au dézoomage les drapeaux et les bateaux se baladent
  horizontalement », « on ne doit pas voir plusieurs fois le monde »).
- Causes déjà lues : `src/utils/markerOffsets.js` `computeMarkerOffsets` l. 125 (décalages anti-
  chevauchement en pixels, calculés à un zoom, gardés tels quels aux autres) ; `MapSceneController.js`
  `scheduleWaypoints` l. 945-954 (`markerOffsetDelay` : les drapeaux se replacent après un délai → saut
  après le zoom) ; `syncWaypoints` l. 821 ; `syncMarker` l. 684 (copies monde `markerWorldLngs` selon le
  centre — recalculées au `moveend`) ; `applyZoomFloor` l. 998 (plancher posé en Suivre seulement) ;
  garde `zoomAnimating` (#386) qui gèle mais ne corrige pas la mise en page post-zoom.
- Ce qui change : reproduire chaque défaut sur le poste (molette, pincement, boutons ±, en Suivre,
  Simulation, Tracer et pendant le film ; au-dessus de Wallis, Nouvelle-Calédonie, Antilles, La Rochelle)
  et noter la cause exacte dans la PR ; décalages anti-chevauchement exprimés dans l'ancre de l'icône et
  recalculés **synchronement** au `zoomend` (plus de délai visible) ; copies monde choisies sans saut au
  passage de l'antiméridien ; plancher de dézoom cohérent dans tous les modes (Tracer garde la vue
  monde entière mais jamais deux mondes) ; tests de non-régression.
- Recette : zoomer / dézoomer 10 fois au-dessus de Wallis et de Fort-de-France → aucun drapeau ni
  bateau ne bouge par rapport à sa position géographique ; dézoom maximal en Suivre et en Simulation →
  un seul monde ; Tracer → monde entier, une fois.

### RG14 — Ancres au bon mot, recette de la position (S)
- Constat : § 5.3 ; D1.
- Causes : `server/film_script.py` `chapter_anchors` l. 2178 (ancre au début de la phrase, une par
  phrase) ; `build_raw_from_moments` l. 2373 (groupes ancrés au premier membre) ;
  `FILM_VOICE_LOOKAHEAD_CHARS` (avance de 12 caractères non compensée) ; `src/engine/replay.js`
  `chapterAnchors` l. 476.
- Ce qui change : ancre posée à l'index du nom du lieu dans la phrase (− 12 caractères), deux ancres
  pour une durée (arrivée / départ), départ au premier mot, arrivée au dernier ; groupes datés au membre
  le plus proche du bateau à l'instant où il est dit ; test de position : pour chaque ancre, la distance
  entre la position de l'horloge à l'instant ancré et le lieu nommé ≤ N nm (escale 5, marina 15,
  AMP / projet 30, ZEE : à l'intérieur) — sur les moments d'exemple et, marqué `poste`, sur le stock.
- Recette : « Le détroit de Gibraltar » se dit avec le bateau dans le détroit ; « trois jours à quai » avec
  le bateau à quai du premier au dernier mot.

### RH1, RH2 — inchangés (plan s5 § 4).

### RG11 — « Rédigé » depuis les faits (M, optionnel, hors batch)
Réécriture LLM depuis les faits structurés de chaque étape (JSON), zéro invention, chiffres et noms
vérifiés automatiquement contre les faits ; repli sur le brut sinon. À ouvrir seulement si le porteur le
demande après RG10.

## 5. Ordre, pile, lancement

Ordre d'exécution (dépendances respectées, le récit d'abord, la cinématique ensuite, la carte, puis la
robustesse) : **RG16 → RG1 → RG2 → RG3 → RG4 → RG5 → RG6 → RG7 → RG8 → RG9 → RG10 → RG12 → RG13 →
RG15 → RG14 → RH1 → RH2** (RG11 hors batch). RG16 ouvre le batch : les quinze lots suivants ont une CI
qui les juge. Depuis `main` (la pile #386 est mergée) ; chaque lot empile sur
la tête ; poste de recette reconstruit sur la tête après le verdict du bot (`--bot-gate-min`).

`python3 infra/agents/run_lots.py --dry-run --from RG16 --until RH2` doit lister ces 17 lots dans l'ordre.

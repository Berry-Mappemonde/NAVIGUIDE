# Batch 3 — voix une fois, puis les modèles (16 octobre 2026)

Source : les quatre tours de préparation du 16 octobre (film, bateau × voix, discours, trois Nemotron + VL).
Les prompts complets sont dans `docs/LOTS_ORDRE_ET_PROMPTS.md`, section « Batch 3 ».
Ce batch ne part pas tant que la file vive n’est pas vide, et pas depuis une tête qui contient les PR interdites.

## 1. L'ordre et pourquoi

| # | Lot | Modèle | Taille | Ce que le porteur verra |
|---|---|---|---|---|
| 1 | **VF1** — la voix coincée ne fige plus le film | Grok | S | Revoir une deuxième fois, sans recharger : le bateau quitte La Rochelle. La voix peut se taire, le film continue |
| 2 | **NB1** — frein en dollars estimés, défaut du dépôt inchangé | Grok | S | Rien à l'écran. Après la mesure, une ligne à poser sur le poste, sans montant dans le dépôt |
| 3 | **VR1** — VL juge le mouvement d'une PR film | Grok | M | Rien dans l'appli. On **merge** cette PR avant d'ouvrir tout lot qui touche le film |
| 4 | **DC1** — candidat aire marine (proximité ou traversée) | Grok | S | La phrase d'aire déjà dite peut préciser près / traversée / circulation. Pas une seconde aire |
| 5 | **DC2** — candidats bouée, formalité, mouillage | Grok | M | Ces phrases existent pour l'intégral, une fois. Le 2:30 ne s'allonge pas |
| 6 | **DC3** — candidats balise, câble, profondeur, piraterie, satellite | Grok | M | Pareil. Satellite tu si rien n'est jouable. Le 2:30 ne s'allonge pas |
| 7 | **VS1** — quoi dire, dans le budget | Grok | M | Le 2:30 remplace des redites par quelques sujets, et reste à 2:30 |
| 8 | **ED1** — clic Rédigé : Super, Ultra édite, Ultra juge, Lightning traduit | Grok | M | Au clic, le texte change de plume pour la pilule choisie (2:30, 3:00 ou intégral). L'ouverture ne paie rien |
| 9 | **CH1** — chat simple par les règles, chat difficile par Ultra | Grok | M | Une question simple répond avec le journal. Une question difficile passe par Ultra s'il est allumé, sinon par les règles. Pas de case à cocher |
| 10 | **TV1** — questionnaire d'escale, deux tours | Grok | M | Une phrase datée et une adresse, dans la fiche ou le chat. Dans le film seulement si VS1 l'a gardée |

Pourquoi cet ordre : **VF1** part le premier. Le 16 octobre, la pré-revue de la PR #509 s'est figée à La Rochelle (chapitre 0, caractère 231, 90 à 217 s) sur deux lectures sur trois. Seule une lecture juste après un rechargement complet passait. L'horloge `elapsed` continuait, le bateau non. Tant que ce gel est là, le bot ne peut pas juger le film des lots suivants. **NB1** pose ensuite le frein avant tout appel mesuré. **VR1** est codé et **mergé** avant les lots qui modifient le film, pour que leurs PR soient relues avec cette revue déjà sur `main`. Ces lots sont **DC1, DC2, DC3, VS1, ED1** et **TV1** (il touche le script). **CH1** ne touche pas le film ; il part quand même après ce merge, pour ne pas laisser une pile à cheval. **DC1–DC3** remplissent le sac sans toucher à la longueur du 2:30. **VS1** est le seul qui choisit ce qui entre dans cette longueur. **ED1** réécrit un texte déjà choisi, au clic. **CH1** et **TV1** ne rallongent pas le film.

Modèle de chaque lot : Grok de la chaîne (pas d'attribut `model` sur la balise). Les agents tournent avec `NAVIGUIDE_LLM_MODE=off`. Les tests simulent Lightning, Super, Ultra, VL et Tavily. Aucun appel Nebius pendant le lot.

## 2. Où en est la file

État lu le 16 octobre au matin. RC44, RC45 et RC47 sont finis. RC46 a échoué (PR #503 vide) et ne se rejoue pas : son id est déjà dans `state.done`. Il reste **CT1 → RC48 → RC49**. On ne relance pas RC46. RC48 couvre l'ordre des eaux La Rochelle → Ajaccio. DC1 couvre la phrase d'aire.

On ne merge pas #486 (RG19), #489 (RG20), #492 (RC34). On n'en reprend pas les branches. CH1 réécrit l'intention de RG19 sans la case Raisonnement. RG20 (specs qui disent la vérité) et RC34 (date « réel jusqu'au », couture turquoise — déjà le contrat HC1) restent hors de ce batch.

## 3. Cinq verrous

À recopier dans le prompt du lot concerné. Un agent qui les rate casse RC27 ou livre un Rédigé mort.

1. **DC1, DC2, DC3 remplissent le sac. Ils n'allongent pas le 2:30.** `film_char_budget(150)` = `150 × FILM_ESTIMATE_CPS` = **2 250** caractères (`naviguide-simulator/server/film_script.py`). Une aire + une bouée + une formalité + un mouillage + jusqu'à cinq familles DC3, ce serait jusqu'à neuf phrases. À 80–120 caractères, ça dépasse. Chaque lot DC enregistre le kind, la phrase possible, et « une fois par famille sur une longue jambe ». Un test affirme que le 2:30 reste ≤ `film_char_budget(150)`. Les kinds nouveaux sont dans le sac, pas empilés dans le chapitre court.
2. **VS1 tient le budget, repli compris.** VL propose des ids. Lightning ne peut qu'en retirer. Modèles éteints : le repli remplace des redites, dans un ordre fixe, et s'arrête au budget. Il n'écrit pas les neuf phrases. Même règle pour le 3:00 (`film_char_budget(180)` = 2 700). L'intégral (`film_char_budget(0)` = 0) n'a pas de plafond de caractères : il peut être plus riche, toujours une fois par famille et par longue jambe.
3. **ED1 casse la fenêtre 2 160–2 640.** `FILM_WRITE_MIN` / `FILM_WRITE_MAX` rejettent aujourd'hui tout Rédigé qui n'est pas le 2:30. La fenêtre suit `film_char_budget(seconds)` pour les pilules minutées. L'intégral n'est pas rejeté pour sa longueur. On ne se limite pas au 2:30. La chaîne ne part qu'au **clic** Rédigé, pas à l'ouverture de Suivre, pas dans le préchauffage de fond.
4. **Bumper de stock, pas un préchauffage du monde.** DC1, DC2, DC3, VS1 et ED1 incrémentent `FILM_SCRIPT_REV` (`official_store.py`, aujourd'hui `rc26`). DC3 incrémente aussi `MOMENTS_REV` (aujourd'hui `rg4`) s'il crée un kind. Le remplisseur recalcule la famille film, et les moments si leur révision a bougé. Pas un WARM de toutes les perles. Sans bumper, le poste ressert l'ancien film (le piège de RC46).
5. **Tavily et le chat ne débordent pas le film.** TV1 va dans la fiche ou le chat. Il n'entre dans le 2:30 que si VS1 a gardé son id. CH1 : si Lightning est éteint ou au plafond, un analyseur par mots-clés (pourquoi / comment / longueur) classe, puis les règles répondent. Si Ultra est coupé, la question difficile reste sur cette réponse. Jamais Super.

Les specs qui citent un libellé touché (phrase d'aire, Rédigé, source du modèle, parcours « Raisonnement ») sont mises à jour dans la **même PR** que le lot. Ça vaut pour DC1–DC3, ED1 et CH1.

## 4. Contrats des modèles

| Modèle | Métier dans ce batch | Pas son métier |
|---|---|---|
| Lightning | Classer le chat simple ; retirer des ids pour tenir le budget ; traduire le français déjà accepté ; lire le second tour Tavily | Rédiger le film ; inventer une question d'escale ; ajouter un id |
| Super | Auteur du français, au clic Rédigé, depuis les faits | Juger son texte ; écrire le chat ; partir tout seul au chargement |
| Ultra | Éditer le français de Super ; juger ce texte dans **un autre appel** ; écrire le chat difficile | Écrire le film à partir de zéro ; 177 récits par nuit ; un badge invisible |
| VL | Juger le mouvement d'une PR film (VR1, éteint) ; proposer des ids sur la carte du tour (VS1) | Voir la carte autour du bateau ; écrire le script ; inventer un nom |
| Tavily | Deux tours sur une liste pré-écrite, prochaines escales, une phrase et une URL | Blue Intelligence ; moisson de ports d'entrée ; fond avant la mesure |

Le dessin Super → Ultra (édite) → Ultra (juge) → Lightning (anglais) est le **clic Rédigé**. Ouvrir Suivre ne le lance pas. VS1 ne tourne qu'au recalcul du stock film, une fois, mis en cache.

## 5. Ce qu'on ne code pas

Après RC49, une mesure, pas un lot : `naviguide-simulator/scripts/film-cinematique.mjs` (frames, saccades, décrochage, zoom) et le rapport d'avance par frame de la voix. RG12, RG13 et RG14 sont déjà là. Si un seuil casse, le réviseur de nuit écrit un RC.

Hors batch : VL autour du bateau ; VL sur les documents Blue Intelligence ; saisie vocale ; LangSmith ; Ultra auteur du film ; pré-génération des récits ; Tavily en fond avant la mesure ; merger #486, #489, #492.

Polaire, ordres skipper et revue du plan ne deviennent pas des chapitres. Les milles, les jours et le cap sont déjà dans l'ouverture. La polaire et les ordres vont au paquet du chat (CH1).

Satellite (DC3) : s'il n'y a pas une phrase déjà jouable dans le stock, silence. On n'invente pas « image satellite au-dessus du bateau ».

## 6. Lancer — pas maintenant

La PR GO n'est pas ouverte par l'écriture de ce document. Le batch actuel se termine d'abord (**CT1, RC48, RC49**), puis la grande revue du porteur.

Deux lancements, pas un. Entre les deux, on merge.

1. Première tranche, après la revue : **VF1** puis **NB1** puis **VR1**. Dès que VR1 est codé et sa CI verte, on **merge** cette tête sur `main`. Les lots film ne sont pas ouverts avant. VF1 est dans cette tête : le poste de la seconde tranche lit le film sans rechargement forcé.
2. Seconde tranche, depuis ce `main` : **DC1 DC2 DC3 VS1 ED1 CH1 TV1**. DC1 ne s'empile pas sur une PR VR1 encore ouverte.

**La base des deux tranches est une tête sans #486, #489 ni #492.** Si CT1, RC48 ou RC49 sont encore empilés dessus, merger la tête mergerait l'interdit. On vérifie l'ascendance avant le premier lancement. S'ils y sont, on les sort de la pile d'abord.

```text
LOTS: VF1 NB1 VR1
```

```bash
cd ~/Blue-Intelligence-Map && git pull --ff-only origin main
python3 infra/agents/run_lots.py --from VF1 --until VR1 --review-every 4
```

Après le merge de VR1 :

```text
LOTS: DC1 DC2 DC3 VS1 ED1 CH1 TV1
```

```bash
cd ~/Blue-Intelligence-Map && git pull --ff-only origin main
python3 infra/agents/run_lots.py --from DC1 --until TV1 --review-every 4
```

## 7. Argent

Nebius n'arrête pas la dépense (un budget console est une alerte, parfois après le seuil). La coupure est `llm_budget.py`. NB1 ajoute `NAVIGUIDE_LLM_DAILY_USD` : **absent = pas de coupure en dollars**, le temps de mesurer. Le dépôt ne contient aucun montant. Le lot documente la ligne à poser sur le poste après la mesure, dans l'environnement du simulateur, sans secret. Le palier juge reste à **0** dans le dépôt. Le mode reste `on-demand`. Les agents restent en `off`. La mesure se lit sur `GET /ici/warm/status` (compteurs déjà là).

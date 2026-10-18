# Specs Playwright « douteuses » — triage du 29 septembre 2026

Demande du porteur (29 sept.) : « un rapport sur ces environ 83 specs douteux qui sont soit à mettre à jour,
soit à écarter ». Ce document répond spec par spec, avec les chiffres d'un vrai passage CI.

## 1. De quoi on parle

Depuis RG16 (#399), la CI joue `e2e/smoke.spec.js` + `e2e/lots/*.spec.js` en six tranches sur le
**stock figé** (`server/tests/fixtures/official_store.tar.gz`, API hors ligne, `ICI_WARM=0`,
aucun réseau extérieur, aucun LLM). Une spec « douteuse » est une spec qui contient au moins un
**chemin à vide** : quand la surface attendue n'est pas là (pas d'API, film pas prêt, stock sans
famille `eta`…), la spec **annote** au lieu d'échouer (`test.info().annotations.push({ type, description })`)
et passe au vert. Le résumé d'étape (`scripts/e2e-summary.mjs`) les appelle « verts avec réserve ».

Inventaire statique (regex sur les fichiers, main `49a7e10`) :

| | Nombre |
|---|---|
| Specs jouées en CI | **100** (smoke + 99 lots ; `l3-juge` et `l4-veille` archivées par RG16, surfaces disparues depuis R8c) |
| Specs sans aucun chemin à vide (« dures ») | **17** |
| Specs avec au moins un chemin à vide (les « ~83 ») | **83**, portant **210** chemins à vide |

Passage CI de référence : run `36524980446` (PR #403, main `49a7e10` + artefact JSON), **101/101 verts**,
six tranches en 2 min 05 – 2 min 58.

| Résultat réel sur le stock figé | Specs | Chemins |
|---|---|---|
| Tous les chemins à vide **dormants** (la spec a joué son chemin dur) | **60** | 183 jamais pris |
| Au moins une **réserve prise** (vert avec réserve) | **23** | **27** pris (dont 2 simples mesures de perf, rf9) |

Conclusion en une phrase : sur les 83 specs douteuses, **60 ne sont douteuses qu'en apparence** — leurs
chemins à vide sont des replis « sans API » pour le poste local sans serveur, jamais pris en CI ;
le vrai sujet, ce sont **23 specs / 25 réserves**, listées au § 3 avec leur sort.

Comment refaire la mesure : depuis #403 chaque tranche téléverse `e2e-json-<n>` (3 jours) ;
`gh run download <run> --pattern 'e2e-json-*'` puis lire `tests[].annotations` des six `e2e.json`.

## 2. Les trois familles de chemins à vide

1. **« sans API »** (≈ 150 chemins, 60 specs entièrement dans ce cas) : `GET /voyage/official` absent →
   la spec saute ce qui dépend du serveur. En CI l'API du stock figé répond toujours : chemin **jamais pris**.
   Il sert uniquement à `npm run e2e` sur un poste sans serveur. **À garder tel quel**, mais ce n'est
   pas une réserve : le résumé CI ne les compte plus (RG16).
2. **« poste »** (par construction) : ce que la CI ne peut pas avoir — atlas de tuiles BI (rd8, rf9, re6),
   searoute / Overpass (s-transpacifique), hindcast ERA5 (ra8, rb8, rf10), isochrone et conseil LLM
   (r10b, r10c, r10d), chat LLM (ra1), `/escale` enrichi par `ici_warm` (r7). Ces assertions ne se jouent
   que sur le poste de recette (specs « poste » `run_poste_specs`, #400) ou par Grok Bot. **À garder**,
   mais typées `poste` pour que le résumé les range à part — quatre ne le sont pas encore (§ 3).
3. **« décision dépassée »** : la spec attend un ancien contrat et annote quand le nouveau apparaît
   (RE2 curseur LIVE, RE3 pilules/Revoir, RF8 budget client, RC11 Revoir grisé, RC17 clôture, RF7/RC18
   recadrage, R8c fiche flottante, RG1 paires Papeete). Là le chemin annoté **est** le comportement
   actuel : la spec doit l'exiger en dur. **À mettre à jour.**

## 3. Les 23 specs qui passent « avec réserve » en CI — sort proposé

Sort : **MAJ** = réécrire l'assertion sur le contrat actuel · **STOCK** = enrichir/régénérer le stock figé
pour que l'assertion devienne dure · **POSTE** = par construction hors CI, typer `poste` · **OK** = rien à faire.

| Spec | Réserve prise (type · texte) | Cause | Sort |
|---|---|---|---|
| `f5-anglais` | `Revoir grisé` · RC11 : Replay still disabled — sous-titre / plein écran non joués | la spec teste Revoir avant que `/film` (EN) soit prêt ; le stock figé a bien le film FR + EN | **MAJ** — attendre `window.__naviguideFilm.status === "ready"` (comme rb5 corrigé) puis exiger sous-titre et plein écran |
| `r9c` | `hors film` · RE3 : pilules seulement quand Revoir peut partir | même course : pilules cherchées avant `film ready` | **MAJ** — attendre `ready`, exiger les pilules |
| `rb5-film-officiel` | `Revoir grisé` · RC11 : Replay disabled after EN — sous-titre EN non rejoué | après le passage EN, la spec attend la réponse `film?lang=en` mais pas le statut `ready` du client | **MAJ** — attendre `ready` après EN, exiger le sous-titre EN |
| `rd5-demarrage-dates` | `RE3` · Revoir grisé après saisie 15/05/2025 — champ date déjà vérifié | la saisie d'une date relance `/film?t0=…` ; la spec ne rattend pas `ready` | **MAJ** — attendre `ready` après la date, exiger le départ du film |
| `rf8-barre-epuree` | `sans API` · GET /voyage/official absent **ou /film pas prêt** — pilules et lancement non exigés | type trompeur : l'API était là, c'est le film qui n'était pas prêt | **MAJ** — séparer les deux cas, attendre `ready`, exiger pilules + lancement |
| `rc6-clics-ici-curseur` | `RE2` · Suivre LIVE — le curseur ne saute pas sur l'escale au clic drapeau | RE2 **est** le contrat (le curseur reste LIVE) | **MAJ** — en faire l'assertion dure, supprimer le chemin annoté |
| `rd7-film` | `RF8` · stock figé : /film?seconds=150 sert le script libre (targetSeconds=0) — budget 150 tenu côté client | RF8 **est** le contrat (budget tenu par le client) | **MAJ** — exiger en dur le budget client, plus d'annotation |
| `ra2-ordre` (×2) | `reste à faire` · RG1 : paires départ/arrivée incomplètes (Papeete) dans le film figé FR et EN | défaut réel du film, lot **RG1** du batch en cours | **MAJ après RG1** + **STOCK** (régénérer le film du stock figé) — la spec exige alors chaque paire |
| `re7-discours` | `RC17` · sous-titre de fin du stock figé : pas encore la phrase de clôture | le film du stock figé date d'avant RC17 | **STOCK** — régénérer le film figé (même geste que RG1) puis exiger la clôture |
| `rf5-avion-et-fin` | `clôture RC17` · dernier chapitre n'est pas « Aujourd'hui, le bateau est… » | idem | **STOCK** — idem |
| `r9b` | `RF2` · journal du stock figé pas encore listé — clic curseur sauté | famille `moments` du stock sans lignes de journal listables | **STOCK** — ajouter les lignes de journal à la fixture, puis exiger la liste et le clic |
| `rc12-voyage-sans-horloge-sync` | `horloge figée` · j0 sur le stock figé — jour de mer officiel pas encore servi | horloge du stock figé au jour 0 | **STOCK** — figer une horloge avancée (jour de mer > 0) ; sinon exiger en dur le libellé honnête « j0 » |
| `rb7-eta-prechauffe` | `poste` · fourchette absente du stock figé (pas d'eta) | famille `eta` absente de la fixture ; `compute_eta` ne sert rien tant que `members = 0` (RG17) | **STOCK après RG17** — ajouter la famille `eta` ; en attendant le type `poste` est le bon |
| `re5` | `poste` · pas de fourchette (stock sans eta) — aucune date inventée | idem | **STOCK après RG17** |
| `r10b` → `parcours-nominal` | `advice unavailable` · RF1 : /advice honnête (unavailable) sur le stock figé | conseil = isochrone + LLM, jamais en CI | **POSTE** — fait le 29 sept. dans la spec fusionnée (type `poste`, contrat RF1 « unavailable honnête » vérifié en dur) |
| `r10c` | `recalcul inactif` · Recalculer présent mais inactif (voyage / prévision) | recalcul = isochrone, jamais en CI | **POSTE** — typer `poste` |
| `r10d` | `conseil inactif` · Demander conseil présent mais inactif | idem | **POSTE** — typer `poste` |
| `r7-escale` | `poste` · fiche encore « On rassemble » (stock figé sans /escale enrichi) | `/escale` enrichi vient de `ici_warm`, coupé en CI | **STOCK** si la fiche d'Ajaccio tient dans la fixture (famille `ici`), sinon **POSTE** (déjà typé) |
| `ra8-hindcast` | `hindcast en cours` · clock encore climatologie — remplissage ERA5 en fond | ERA5 = réseau | **POSTE** — typer `poste` |
| `rb8-route-copies` | `hindcast en cours` · aucun trait parcouru avec vitesse d'époque | idem | **POSTE** — typer `poste` |
| `rf10-hindcast-quota` | `hindcast incomplet` · hindcastStatus=pending — repli climatologie visible | idem | **POSTE** — typer `poste` |
| `rd8-tuiles` (×3) | `poste` · atlas tuiles / roses (quota, cache) | backend BI absent en CI | **OK** — déjà typé `poste` ; les roses sont vérifiées par la route mockée |
| `rf9-roses-perf` (×2) | `zoom-ms-avant` / `zoom-ms` · mesures (111 ms → 436 ms, plafond 2 000) | ce sont des mesures, pas des réserves | **OK** — typer `mesure` pour que le résumé ne les compte pas |

Bilan des 23 : **8 MAJ** (dont 1 après RG1), **7 STOCK** (dont 2 après RG17, 3 par régénération du film figé),
**7 POSTE** (typage), **2 OK** (rd8, rf9).

## 4. Les 60 specs aux chemins dormants — rien à jouer, trois toilettages

Toutes ont joué leur chemin dur en CI. Aucune n'est à écarter. Trois toilettages sans risque, à faire dans le
même lot que le § 3 :

- **Descriptions périmées** (le texte parle d'un état qui n'existe plus) : `rd5` l. 171 « processus :8010 hors
  lot », `re7` l. 126 « GET /film du processus :8010 n'est pas encore RE7 », `rc11` l. 112 « pas encore RE7 »,
  `r11-eta` l. 92 « pas encore R11 », `n3` / `n4` « API d'un autre checkout » — depuis RF11 l'API de la CI est
  celle du même checkout : ces branches ne peuvent plus se produire → supprimer la branche, garder l'assertion.
- **Chemins « décision dépassée » dormants** (le nouveau contrat est déjà le chemin dur, la branche annotée
  est morte) : `r5-recit` l. 84 (R8c), `rc1-meteo-point` l. 219 (RF7), `rf7-accueil-tracer` l. 135 (RF7 / RC18),
  `r2-barre` l. 86 (RE3), `ra7-fourchette` l. 114 (RE5), `re3-lisibilite` l. 211 (RE3 / RF8), `rf2` l. 145 (RE3),
  `rb1-halifax-mer` l. 165 (« flatten antérieur à RB1 ») → supprimer la branche.
- **Types `?`** (annotation sans `type`, invisible dans le résumé) : `r1-nettoyage` l. 125, `r8c` l. 146,
  `ra3-film-rendu` l. 138 et 168, `rc11` l. 112, `rb8` l. 134 → donner un type (`sans API`, `poste` ou `mesure`).

**Fusion faite (29 sept., décision porteur)** : `r8a`, `r8b`, `r10a`, `r10b` (« aucun changement visible, trois
parcours ») rejouaient le même parcours nominal ; ils sont remplacés par `e2e/lots/parcours-nominal.spec.js`,
qui garde tout ce qu'ils vérifiaient (encadré Ici seul et en mode clair, trois vues, encadré présent dans
l'app, `/advice` typé `poste`). La suite passe de 100 à **97 specs** ; les captures des anciens lots restent
dans `docs/recette/lot-r8a…lot-r10b`.

## 5. Les 17 specs « dures » (aucun chemin à vide)

`smoke`, `c1-resume`, `c2-hindcast`, `c3-vitesse`, `c4-eta`, `c6-eta`, `c7-conventions`, `f2-evenements`,
`f3-script`, `l1-source`, `l2-sources`, `l5-revue`, `l6-anglais`, `m-credits`, `n-panneau`, `o-barre`, `t-sac-route`
(`rg --files-without-match "annotations.push" e2e/lots/*.spec.js e2e/smoke.spec.js`). Rien à faire : rouge = régression.

## 6. Ce que ça donne pour la CI

- Aujourd'hui : 100 specs, 6 tranches, ~3 min chacune, 101/101 verts, **23 verts avec réserve**.
- Après le lot de triage (RG20, en file `infra/agents/queue.md`, deps RG17 pour la famille `eta` et RG1 pour
  le film) : **~9 réserves restantes**, toutes typées `poste` et attendues (atlas, hindcast, isochrone, LLM),
  affichées à part par le résumé. Toute autre réserve devient un signal.
- Les specs `poste` restent jouées sur le poste de recette après chaque rebuild (#400, commentaire 🧪) :
  c'est là que les 7 « POSTE » se vérifient vraiment.

## 7. Références

- Inventaire des 210 chemins à vide (type, texte, ligne) : produit par regex — refaire avec la commande du § 1.
- Rapport CI : run `36524980446`, artefacts `e2e-json-1..6` (PR #403).
- RG16 (#399) : six tranches, `scripts/e2e-summary.mjs`, archive `e2e-archive/` (l3, l4).
- #400 : specs « poste » rejouées sur le poste (`run_poste_specs`).

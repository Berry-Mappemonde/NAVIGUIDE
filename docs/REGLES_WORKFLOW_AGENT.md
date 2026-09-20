# Règles de travail pour un agent Cursor sur `naviguide-simulator/`

Version **1.0** — 20 septembre 2026. Ce fichier est **le prompt** : chaque plan
(`PLAN_*.md`) y renvoie, chaque brief de lot commence par « lis
`docs/REGLES_WORKFLOW_AGENT.md` en entier ». Il est écrit pour un worker
**Cursor Grok 4.6 Extra High Fast (256 k de contexte)** ; il vaut aussi pour
tout autre modèle.

## 1. Ce qui ne se discute pas

- **`main` est le plancher de l'interface.** Une tâche moteur, météo, API ou
  LLM n'autorise jamais à retirer, cacher, vider ou désactiver une surface
  visible sur `main` (cf. `.cursor/rules/anti-regression-visuelle-simulateur.mdc`).
  Avant tout JSX/CSS : `git diff main -- naviguide-simulator/src/App.jsx
  naviguide-simulator/src/components naviguide-simulator/src/map`.
- **Aucun chiffre produit par un LLM.** Un LLM rédige, relie, choisit,
  traduit ; les nombres viennent des faits (`filter_numbers` côté serveur).
  Champ inconnu = vide, jamais inventé.
- **Pas de vidéo.** La preuve, ce sont des tests et des captures fixes.
- **Budget de contexte.** Ne jamais lire `src/App.jsx` ni
  `src/map/MapSceneController.js` en entier : `rg -n "motif" fichier` puis
  `Read` avec `offset`/`limit`. Chaque lot liste **les seuls fichiers à ouvrir**.
- **Le worker ne merge jamais.** Il ouvre la PR et s'arrête. Le porteur recette
  puis merge.
- **Base de données** : la MongoDB vivante est celle du VPS ; ne jamais lancer
  `infra/vps/sync-from-atlas.sh`. Le simulateur a sa SQLite locale
  (`server/pearl_store.py`), c'est la seule mémoire qu'un lot peut toucher.

## 2. Branches

- Une branche **par lot**, créée depuis `main` **à jour** :
  `git checkout main && git pull --ff-only && git checkout -b <type>/lot-<x>-<slug>`.
- Préfixes : `feat/` (fonction), `fix/` (correction), `docs/` (plans, textes),
  `chore/` (outillage, CI), `refactor/`. Le slug est court, en français sans
  accents ou en anglais : `feat/lot-q-replay-fluide`, `fix/carte-now-sans-ecouter`.
- **Lots empilés** (le lot n+1 a besoin du n non encore mergé) : la branche
  n+1 part de la branche n ; la PR n+1 vise la branche n (pas `main`) et son
  titre commence par `[stack n→n+1]`. On évite quand on peut : deux lots sur
  des fichiers différents partent de `main` et vont en parallèle.
- Jamais de `git push --force` sur une branche qui a une PR ouverte, sauf
  demande du porteur. Jamais de commit direct sur `main`.
- Commits **conventionnels** en français : `feat(simulator): …`,
  `fix(server): …`, `docs: …`, `test: …`. Un commit peut regrouper le lot
  entier ; le message dit **quoi et pourquoi**, cite le lot et la revue
  (« revue du 20 sept. »).

## 3. Pull request

- Une PR par lot, vers `main` (ou vers la branche n si empilée). Titre =
  message du commit principal. **Ne pas merger.**
- Le corps suit ce gabarit, dans cet ordre :

```md
## Objectif
Une phrase : ce que le porteur verra ou ne verra plus.

## Cause racine
Fichier:ligne et explication (pour une correction). « — » pour une fonction.

## Ce qui change
- fichier — quoi (1 ligne par fichier notable)

## Tests
`npm test` (n JS), `pytest -q` (n Py), `npx vite build`, `npm run e2e` si UI.
Nouveaux tests : lesquels, ce qu'ils protègent.

## Recette (à faire par le porteur, 5 min)
1. Étape → **ce qu'on doit voir exactement** (texte, chiffre, position).
2. …
Captures : `docs/recette/<lot>/01-….jpg` (≤ 4, 1280×800, JPEG q70).

## Review automatique
`npm run e2e -- e2e/lots/<lot>.spec.js` : vert. Ce que le spec vérifie (liste).

## Hors périmètre / risques
Ce qu'on n'a pas touché exprès, ce qui pourrait bouger.
```

- La PR reste **petite** : ≤ 400 lignes de diff hors tests et données, sinon
  on découpe (le plan le prévoit).
- CI verte obligatoire : `simulator` (tests JS + Python, build, audits) et
  `simulator-e2e` (Playwright sur le build de prod).

## 4. Recette visuelle (ce que le porteur fait)

- Toujours sur le **build de prod** : `cd naviguide-simulator && bash dev-mac.sh`
  (API :8010 + Vite :5174) ou `npm run build && npm run preview` + API.
- Chaque lot donne des **étapes numérotées** et, pour chacune, **ce qu'on doit
  trouver** : un texte exact, un chiffre, une position, un bouton présent ou
  absent. Deux formes seulement :
  - « **Changement visible** » : la liste précise des différences avec `main`.
  - « **Aucun changement visible** » : le lot est interne ; la recette, c'est
    « tout marche comme avant » sur trois parcours fixes (Suivre à Nouméa,
    Simulation La Rochelle → Ajaccio, Tracer ma route Brisbane → SF).
- Les captures sont **fixes** (pas de vidéo), rangées dans
  `docs/recette/<lot>/`, nommées `01-…jpg`, `02-…jpg`, et **référencées dans la
  PR**. Elles se prennent par le spec Playwright du lot (§ 5), pas à la main.

## 5. Review automatique (ce que l'agent fait avant d'ouvrir la PR)

Chaque lot **qui touche l'UI** livre un spec Playwright `e2e/lots/<lot>.spec.js`
qui rejoue la recette et prend les captures :

```js
// e2e/lots/q-replay.spec.js — gabarit
import { test, expect } from "@playwright/test";
const shot = (page, name) => page.screenshot({
  path: `../docs/recette/lot-q/${name}.jpg`, type: "jpeg", quality: 70, fullPage: false,
});

test("lot Q — replay : zoom stable, récit dès le départ", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("mode-follow").click();
  await page.getByTestId("replay-start").click();
  await expect(page.getByTestId("story-paragraph").first()).toContainText("Saint-Maur", { timeout: 5000 });
  const z0 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
  await page.waitForTimeout(4000);
  const z1 = await page.evaluate(() => window.__naviguideScene.map.getZoom());
  expect(Math.abs(z1 - z0)).toBeLessThanOrEqual(0.01);
  await shot(page, "01-replay-mi-parcours");
});
```

Règles du spec :

- Il **vérifie** (assertions sur `data-testid`, textes, `window.__naviguideScene`)
  **puis** capture. Une capture sans assertion ne prouve rien.
- Il tourne sans API (le build doit tenir debout seul) ; s'il a besoin de l'API,
  il le dit en tête et le porteur la lance.
- Un lot « aucun changement visible » réutilise `e2e/smoke.spec.js` et ajoute
  au plus une assertion.
- Chaque `data-testid` nouveau est listé dans la PR ; on ne renomme pas ceux
  qui existent (les tests de contrat les lisent).
- Commande : `npm run e2e -- e2e/lots/<lot>.spec.js` ; en CI, `npm run e2e`
  joue tout le dossier.

## 6. Review humaine (ce que le porteur ou un second agent vérifie)

Liste de contrôle, à cocher dans la PR :

- [ ] `git diff main -- src/App.jsx src/components src/map` : aucune surface
      retirée ; ce qui bouge est demandé par le lot.
- [ ] Pas de nombre issu d'un LLM ; `filter_numbers` (ou équivalent) sur tout
      texte généré ; champ inconnu vide.
- [ ] i18n : chaque texte nouveau existe en `fr.js` **et** `en.js`.
- [ ] Tests : au moins un test par comportement nouveau ; les tests de contrat
      existants passent sans être affaiblis.
- [ ] Spec Playwright présent si l'UI change ; captures dans `docs/recette/`.
- [ ] Taille de la PR ≤ 400 lignes hors tests/données, ou découpage justifié.
- [ ] Pas de clé, de secret, d'URL privée dans le diff ; `.env` jamais commité.
- [ ] Option : review Bugbot (`/review-bugbot`) pour les lots M/L.

## 7. Merge (ce que le porteur fait, jamais le worker)

1. Recette faite, cases cochées, CI verte.
2. **Merge commit** (pas de squash : l'historique des lots reste lisible ;
   pas de rebase : les PR empilées en dépendent).
3. **PR empilées** : merger n, puis **retarget** la PR n+1 sur `main`
   (`PATCH base=main`) **avant** de supprimer la branche n — sinon GitHub
   ferme n+1. Puis supprimer la branche n.
4. Supprimer la branche distante après merge ; en local :
   `git checkout main && git pull --ff-only && git branch -d <branche>`.
5. Le déploiement est automatique sur `main` (CI → VPS). Vérifier la prod
   dans les 10 minutes : `https://simulator.naviguide.fr` charge, la barre
   film et les trois modes répondent.
6. En cas de régression en prod : `git revert` du merge, PR, merge — pas de
   correction à chaud.

## 8. Brief type (à coller dans le champ « prompt » du worker)

```text
Lis docs/REGLES_WORKFLOW_AGENT.md en entier, puis docs/<PLAN>.md § 0 et le lot <X> (texte intégral).
Fichiers : ouvre SEULEMENT ceux listés dans le lot ; App.jsx et MapSceneController.js par `rg -n` + Read avec offset/limit.
Branche : <type>/lot-<x>-<slug> depuis main à jour. Une PR sur main, corps = gabarit § 3. Ne merge pas.
Tests : cd naviguide-simulator && npm test && .venv/bin/python -m pytest -q && npx vite build ; npm run e2e -- e2e/lots/<lot>.spec.js si l'UI change.
Recette : rejoue les étapes « Recette » du lot avec le spec Playwright du lot ; captures JPEG dans docs/recette/<lot>/ ; référence-les dans la PR.
Interdits : retirer une surface visible sur main ; un chiffre produit par un LLM ; une vidéo ; un merge ; un push --force ; un secret dans le diff.
Modèle : cursor-grok-4.6-xhigh-fast (jamais claude-* sur un worker Cloud).
Quand tu as fini : donne le numéro de PR, les compteurs de tests, la liste des captures, et ce que tu n'as pas fait.
```

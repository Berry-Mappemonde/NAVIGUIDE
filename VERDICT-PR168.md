# Verdict PR #168

- **AK1 confirmé** (`src/hooks/useReplay.js`, `src/App.jsx`, `e2e/lots/tour-edited.spec.js`) : le clic de visite ne pouvait pas basculer si le film jouait, et le changement de style passait par POST même quand `hasWritten` était déjà vrai. Le test interdit explicitement tout POST pendant la visite. Le hook arrête maintenant le film puis lit le rédigé existant par GET ; le POST reste le chemin du clic sur la pilule quand `hasWritten` est faux. Le test n'a pas été affaibli.
- **AK2 confirmé** (`src/hooks/useReplay.js`, `server/main.py`) : le POST n'envoyait pas `style=written`. Le paramètre est désormais transmis et déclaré sur la route POST ; le serveur sert le rédigé via sa logique d'écriture POST existante.
- **AJ1 confirmé** (`server/.env.example`) : le commentaire induisait que le défaut désactive les replis. Correction déjà présente dans le worktree avant intervention, conservée. Recherche des README/docs : aucun README ne décrit l'ancien défaut ; `docs/AI_GOVERNANCE.md` décrit la cascade, sans contredire le défaut.
- Vérification d'existant : la tête `af6c1990` avait déjà AH1-AH3/AG1-AG2, mais pas AK1/AK2 ; le changement `.env.example` était non commité au départ. Les worktrees locaux listés ne contiennent pas de travail PR #168 concurrent.

Fichiers modifiés par ce tour : `naviguide-simulator/src/hooks/useReplay.js`, `naviguide-simulator/src/App.jsx`, `naviguide-simulator/server/main.py`, `naviguide-simulator/src/hooks/useReplay.test.js`. Le changement préexistant de `naviguide-simulator/server/.env.example` est préservé.

Tests : `useReplay.test.js` passe ; `npm run build` passe (avertissement de chunk volumineux). `npm test` a d'abord échoué sur `useReplay.test.js` (assertion statique devenue obsolète, corrigée ensuite) et `scripts/film-cinematique.test.mjs` (échec de capture navigateur). Les E2E `film-style-written` n'ont pas pu démarrer : Playwright n'a pas réussi à démarrer son `webServer` dans le bac à sable, qui interdit les tests réseau localhost. Les tests pytest serveur ciblés ont été lancés avec mode offline et clé NEBIUS retirée, mais leur résultat n'a pas été récupéré dans cette session.

## AL1

- **Constat confirmé** : `e2e/lots/tour-edited.spec.js:22` appelait `route.fetch()` sans garde ; une requête de sondage encore en vol peut échouer après la fin du test. L'appel analogue dans `e2e/lots/nav-c-follow-preparing.spec.js:31` avait le même risque.
- **Vérification de l'existant** : aucun correctif AL1 n'était présent dans la tête `0bdc3894` ni dans les commits de la branche. Les autres changements AL1 n'ont pas été repérés dans les worktrees locaux consultés ; aucune information de ticket ou PR supplémentaire n'était disponible au-delà de la contre-revue fournie.
- **Changement** : les deux bouchons retournent sans erreur si `route.fetch()` échoue au démontage. Les assertions du test de visite, dont `state.posts === 0`, `aria-pressed` et les sources, restent inchangées ; aucun code de production modifié.
- **Tests** : `PW_WITH_API=1 env -u NEBIUS_API_KEY NAVIGUIDE_OFFLINE=1 NAVIGUIDE_LLM_MODE=off npx playwright test e2e/lots/tour-edited.spec.js` n'a pas pu démarrer : le `webServer` Playwright échoue dans le bac à sable (réseau localhost interdit), à valider hors sandbox. `env -u NEBIUS_API_KEY NAVIGUIDE_OFFLINE=1 NAVIGUIDE_LLM_MODE=off npm run build` passe (avertissement de chunk volumineux).

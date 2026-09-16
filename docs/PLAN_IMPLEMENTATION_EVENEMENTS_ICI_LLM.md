# Plan — événements `ici()`, juge d’affichage, récit LLM

Atelier **`naviguide-simulator/`** seulement. Prod `www.naviguide.fr` et
Blue Intelligence **intouchées**.

Version **1.0** — 16 septembre 2026.

Hérite de :

- [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)
  §22 (passage à l’étape 2)
- [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)
  (film → sac → événement → Nano / Tavily / Ultra)
- [PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md](./PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md)
  (deux boutons, GRIB du jour, pas de dump cockpit)
- [PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md)
  (couloir / cube, pas un GRIB globe)
- [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md)
  (`kind` honnête, pas de vent inventé par un LLM)

Ce plan **n’allume pas** Nemotron tant que le lot E1 n’est pas
recettable. Il ne relance pas le sac `ici()` depuis zéro : le sac
point existe (`GET /ici`, `mergeDossier`, `narrateIci`).

---

## 1. En une phrase

Le bateau avance. Le moteur détecte des **événements** sur le point
**et** sur le trait plannifié. Une phrase locale s’affiche **tout de
suite**. Un LLM peut raconter plus tard. Un **juge** décide si on
montre, maintenant, plus tard, ou groupé. Le film **n’attend jamais**
le LLM.

---

## 2. Où on en est (ne pas recasser)

| Déjà là | Pas encore |
|---|---|
| Sac point ~30 nm (`ici.js`, `ici_engine.py`) | Conscience du **trajet** (lookahead) |
| Briefing local `narrateIci` (zéro LLM) | File d’analyse async |
| `zeeEnterEvent` (changement de `mrgid`) | Catalogue d’événements + hystérésis |
| Debounce 800 ms, refetch à 3 nm | Juge d’affichage |
| Polar / jambe dans le sac, jamais la grille | Nano / Tavily / Ultra |
| Un panneau Briefing | Pastilles sur la barre du film |

Contrat déjà verrouillé (étape 1 §22) :

> Un pas = `ici()` **gratuit**. Tavily = entrée de ZEE, clic skipper,
> ou alerte. Polar et searoute parlent au **point** et à **cette**
> jambe. Un récit, pas quatre agents.

---

## 3. Quatre couches

```
Trajet GPS (points de cette jambe)
        │
        ▼
1. SENS     ici(point) + iciAlong(lookahead)     ← moteur, gratuit
        │
        ▼
2. RÈGLES   Δ sac → Event {type, severity, whenNm}  ← zéro LLM
        │
        ├─ phrase locale tout de suite
        │
        ▼
3. FILE     analyse async (Tavily si fiche, Nano sinon)
        │         le playhead avance sans attendre
        ▼
4. JUGE     hide | now | later | group
        │
        ▼
Briefing + pastilles sur la barre du film
```

**Simulation** : on peut préchauffer le couloir de **cette** jambe
(climatologie + géo) avant Play.

**Suivre l’expédition** : seulement « maintenant » + 24–48 h devant
(GRIB du jour autour du bateau). Interdit de préchauffer 39 000 nm.

---

## 4. Conscience du trajet

Aujourd’hui `ici(lat, lon)` ignore la route. On ajoute des extras,
sans gonfler le prompt :

| Champ | Rôle | Pas ça |
|---|---|---|
| `at` | Point bateau, sac 30 nm | Le globe |
| `leg` | `from`, `to`, VMG, ETA (déjà amorcé) | Grille 181×61 |
| `route` | Points GPS **de cette jambe**, 1 point / 10–15 nm | Les 12 448 points d’un coup |
| `along` | ZEE / AMP / PoE / marinas **devant** jusqu’à N nm ou la prochaine escale | Catalogue monde |

Le sac au bateau reste petit. Le lookahead nourrit les événements
« dans 40 nm, AMP » sans tout coller dans le JSON LLM.

---

## 5. Catalogue d’événements

Un **chiffre** ne passe pas par un LLM. Vent, courant, Hs, profondeur
= template + `kind`. Le LLM raconte **quoi faire** (PoE, AMP, marina),
pas le nœud.

| id | Déclencheur (moteur) | Anti-spam | LLM ? | Juge par défaut |
|---|---|---|---|---|
| `zee-enter` | `mrgid` change (`zeeEnterEvent` déjà là) | 1× / mrgid | Tavily sur **cette** fiche Gold, puis Nano | **now** |
| `zee-exit` | `mrgid` → null | 1× | phrase locale | later |
| `poe-ahead` | 1er PoE de **cette** ZEE dans le lookahead | groupé avec `zee-enter` | Tavily fiche | **group** |
| `amp-enter` / `amp-ahead` | AMP entre dans le sac / le trait | 5 nm | Nano si `visit_url` | now si parc visitable, sinon later |
| `wind-shift` | ΔTWS ≥ 8 kt **ou** ΔTWD ≥ 40° | 15 nm / 30 min | **non** | later ; **now** si coup de vent |
| `current-shift` | Δ ≥ 1 kn ou inversion | 15 nm | **non** | later |
| `wx-alert` | pluie / Hs / vent au-dessus d’un **seuil nommé** | 1× par seuil | Nano seulement si marina utile | now si sévère |
| `marina-refuge` | `wx-alert` **et** marina / WPI < 25 nm | 1× par alerte | Nano : nom + distance | **now** |
| `cyclone-nearby` | IBTrACS dans le sac (`kind: climatology`) | 1× / trace | phrase + période / DOI | **now** |
| `depth-alert` | GEBCO / EMODnet trop peu profond | 2 nm | **non** | now |
| `science-hit` | 1 jeu local nouveau | suppress si cinéma | **non** | hide / later |
| `escale-in` / `escale-out` | horloge 3 j à quai | déjà calendrier | Nano court | now |

Seuils = constantes nommées dans `run_rules` / un module `eventRules.js`,
pas des magie dans `App.jsx`. Recette = fixture JSON, pas un LLM.

---

## 6. Deux juges, pas un

### Juge d’affichage (règles, lot E1 — pas Ultra)

Entrées : `severity`, `novelty` (déjà dit ?), `ageNm`, vitesse du
film, clic skipper.

| Verdict | Quand |
|---|---|
| `hide` | doublon, cooldown, cinéma, science sans enjeu |
| `now` | ZEE, cyclone, refuge, profondeur, coup de vent |
| `later` | décalage de vent, sortie de ZEE |
| `group` | PoE + ZEE ; plusieurs AMP sur 30 nm ; digest en accéléré |

En **accéléré** : le juge groupe plus (« depuis 80 nm : ZEE + 2 AMP »).
Pas un flash par point.

### Juge de vérité (Ultra, lot E5 — rare)

« Cette mention PoE est-elle encore prouvée ? » — **1×** par fiche
visible. Ce n’est **pas** le juge d’affichage. Interdit sur un coup
de vent.

---

## 7. File : le film n’attend pas

1. Le playhead avance. Le briefing montre **tout de suite** la phrase
   locale (`narrateIci` / template d’événement).
2. L’événement part en file : `pending` → `ready` | `failed`.
3. Quand Nano revient (quelques secondes), le juge d’affichage décide :
   remplacer, coller plus tard, ou jeter.
4. Simulation : au chargement de jambe, prélever le trait. À l’arrivée
   du bateau, le texte est souvent déjà `ready`.
5. Si encore `pending` au passage du playhead : on **garde** le
   template. On ne bloque pas Play.

Tavily **interdit** à chaque frame Play. Seulement `zee-enter` Gold,
clic skipper, ou `wx-alert` sévère.

---

## 8. Comment le LLM travaille (lots E4–E5)

Pas avant E1 recettable.

Prompt = **petit JSON d’événement**, pas le sac entier, pas la carte :

```json
{
  "event": "zee-enter",
  "zee": {"name": "France", "mrgid": 5677, "gold": true},
  "poe": [{"name": "…", "url": "…"}],
  "leg": {"from": "Cayenne", "to": "Papeete"},
  "tavily": null
}
```

| Rôle | Modèle (Token Factory) | Quand |
|---|---|---|
| Récit | Nano / Lightning | événement `ready` à raconter |
| Sentinel fiche | Tavily Extract sur **cette** URL | Gold / clic / alerte |
| Vérité | Ultra | 1× par fiche visible |

Thinking OFF pour JSON / texte court. Climatologie : le LLM **cite**
P50/P90 / période / DOI. Il n’invente pas un vent.

Interdit : 4 chats, `POST /polar/chat`, dump 4 500 projets, Search
Tavily « ports of entry » monde, NIM comme cerveau.

---

## 9. Présentation pendant la Simulation

- **Panneau Briefing** = la carte parlée **maintenant** (dernier `now`,
  ou le digest `group`).
- **Pastilles sur la barre** du film, aux nm de l’événement. Clic =
  cette carte. Play qui passe dessus : si `now` et `ready`, on
  remplace ; si `pending`, on garde le template.
- File visible **minimale** : pas un chat. Tout au plus « 2 récits en
  préparation ».
- **Suivre** : pas de pastilles sur 39 000 nm. Événement live + **un**
  à venir.

Plus de dump JSON « dossier cockpit » pour le public (déjà verrouillé
U8). Le JSON reste pour debug / Data Lab, pas pour le visiteur.

---

## 10. Ordre de construction

| Lot | Quoi | Recette | LLM |
|---|---|---|---|
| **E1** | Catalogue + hystérésis + juge règles. Étendre `zee-enter`. Vent / AMP / marina / profondeur en **templates** | Play : le briefing **change** à une entrée de ZEE et à un `wind-shift` fixture. Zéro Token Factory | non |
| **E2** | `iciAlong` : extras `route` + `along` sur **cette** jambe | Ahead : « AMP dans 40 nm » sans refetch à chaque mètre | non |
| **E3** | File `pending`/`ready` + préchauffage Simulation (jambe) | Play accéléré : digest groupé, pas de freeze | non |
| **E4** | Nano / Lightning sur le JSON d’événement | 1 récit ZEE, 4–6 phrases, le film n’a pas pausé | oui récit |
| **E5** | Tavily **cette** fiche + Ultra 1× | Gold : URL officielle ; Ultra peut rayer un port | oui sentinel |

E4 après E1. E2 peut avancer en parallèle de E1 si ça ne touche pas
l’UI Briefing. E5 après une vraie fiche Gold, pas un stub.

---

## 11. Fichiers

**Oui** (cibles, pas un dump) :

- `naviguide-simulator/src/engine/ici.js` — extras trajet, pas la grille
- `naviguide-simulator/src/engine/eventRules.js` (+ tests) — déclencheurs
- `naviguide-simulator/src/engine/displayJudge.js` (+ tests) — hide/now/later/group
- `naviguide-simulator/src/hooks/useIciDossier.js` — file, pas un await LLM
- `naviguide-simulator/src/engine/iciBriefing.js` — templates d’événement
- plus tard : `server/` file Nano / Tavily (E4–E5 seulement)

**Non** : `naviguide/`, `frontend/`, `www`, `sync-from-atlas.sh`,
GRIB globe, 4 chats, chat polar, Ultra sur chaque Play.

---

## 12. Recette avant E4

1. Play Simulation, jambe avec une **vraie** entrée de ZEE (fixture
   si besoin) → briefing local change, pastille ou pas selon juge.
2. Même jambe en accéléré → **un** digest, pas 20 flashs.
3. `wind-shift` fixture → phrase chiffrée, **aucun** appel réseau LLM.
4. Suivre : pas de préchauffage 39 000 nm (log / test).
5. `www` et `blueintelligence.online` inchangés.

---

## 13. Hors scope (ce plan)

Isochrone des 39 000 nm. Overlay climatologie opérateur BI. Data Lab /
Sandbox Nebius (stretch après Nano). AIS / Iridium du vrai bateau.
Merger #139 Hs. Allumer Token Factory « pour voir ».

---

## 14. Risques

| Risque | Parade |
|---|---|
| Attendre Nano avant d’ouvrir la scène | Phrase locale d’abord ; file async |
| Tavily à chaque frame | Interdit hors ZEE Gold / clic / alerte |
| Ultra = juge d’affichage | Deux juges ; Ultra seulement vérité fiche |
| Lookahead = dump monde | 1 point / 10–15 nm, **cette** jambe |
| LLM qui invente un vent | Template + `kind` ; climatologie citée |
| 4 chats « le temps que ça arrive » | Le Briefing **est** l’emplacement |

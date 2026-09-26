> **Archivé le 22 septembre 2026 — réalisé.** S1 → S5 et S7. Non fait : confort (3 pills), ordre vocal. Index : [docs/README.md](../README.md).

# Plan — ordres du skipper virtuel

> **Statut (18 sept. 2026)** — S1 → S5 **mergés** dans `main`
> ([PR #177](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/177)).
> S6 (Confort + horizon) et S7 (trappe Expert « Chiffres ») : en cours,
> même panneau, même clé `localStorage`.

Atelier **`naviguide-simulator/`** seulement. Prod `www` et Blue
Intelligence **intouchées**. Pas de merge sans le mot « merge ».
Pas de resync Atlas.

Ce fichier **est** le plan skipper. Il **n’écrase pas**
[PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md](./PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md)
(détecteurs E1–E5, juge, cascade NIM → OR → Claude). Il s’y
branche. E1–E5 sont **déjà dans `main`** (`67c99a25`).

Hérite aussi de
[PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md](./PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md)
(deux boutons, pas de dump cockpit, cinéma range les sidebars).

Version **1.1** — 16 septembre 2026 (corrige la v1.0 du même
jour, **même fichier**).

**Ce tour (v1.1) :** une vérité par seuil (Croisière = E1
3,5 m / 15 m) ; horizon 48 h honnête ; v1 = 3 pastilles + bateau
lu sur la polaire ; film : pastilles déjà posées restent ; phrase
Suivre partagé ; S1 depuis `main`.

**En une phrase :** le skipper virtuel choisit un **caractère** ;
le **bateau** se lit sur la polaire ; le moteur en déduit **un**
chiffre par seuil ; le Briefing et les pastilles **à venir**
changent tout de suite ; le LLM **cite** ces ordres, il ne les
invente pas ; Play n’attend jamais.

---

## 0. Carte (où lire quoi)

| Question | § |
|---|---|
| Décisions verrouillées | §1 |
| Toutes les variables + classement | §2 |
| Ce que le skipper voit / ne voit pas | §3 |
| Trois profils et la table de dérivation | §4 |
| UX (où, phrases, cinéma, Suivre / Simulation) | §5 |
| Relier aux LLM (payload, prompt, file) | §6 |
| Contrat objet `SkipperOrders` | §7 |
| Lots d’implémentation | §8 |
| Recette | §9 |
| Hors scope | §10 |

---

## 1. Décisions verrouillées

1. **Pas de tableur.** Interdit d’aligner 40 sliders. **v1** =
   trois pastilles + bateau **lu** depuis la polaire. Confort,
   curseurs métier et trappe Expert = **S6+**.
2. **Deux boutons seulement** : Suivre / Simulation. Pas de 3ᵉ
   interrupteur « Skipper » à côté.
3. **Ordres dans la sidebar outils** (sous la polaire). Pas sur la
   barre film. Cinéma = panneau caché, ordres **actifs**.
4. Les constantes actuelles de `eventRules.js` / `iciAlong.js` =
   profil **Croisière** (défaut). **Un chiffre par seuil**, déjà
   résolu. Croisière **n’a pas** de second chemin « formule vs
   défaut ».
5. **Gale 34 kn / hold 28 kn** = Beaufort 8 / 7. **Lecture seule**
   dans les trois profils.
6. **Film en cours.** Changer un profil **ne rewind pas**. Les
   pastilles **déjà posées restent** (figées sous les anciens
   ordres). **Seules les suivantes** suivent les nouveaux ordres.
   Les récits déjà `ready` ne sont **pas** relancés. Pas de 2ᵉ
   récit sur un `ready`.
7. `useIciDossier` n’`await` **jamais** un LLM. `enqueueStory`
   reste fire-and-forget (E5 déjà dans `main`).
8. **Pas** Nemotron, **pas** Tavily, **pas** Token Factory.
   Cascade habituelle : NIM → OR (± `:online` si URL du sac) →
   Claude.
9. `kind` honnête. Un null reste un null. Le LLM cite le seuil
   **du skipper**, pas un chiffre inventé.
10. Persistance : **onglet + `localStorage`**. Pas Mongo.
11. Pluie / marina = **Suivre seulement**. En Simulation le bloc
    est visible mais off, avec la raison.
12. **Horizon affiché = horizon moteur.** Si l’UI (ou le profil)
    dit 48 h, le plafond **suit** (heures × nœuds, perles). Sinon
    on n’affiche pas 48 h. Voir §2.6.
13. **Suivre partagé / ordres personnels.** L’horloge officielle
    ne change pas. C’est **ton** skipper qui parle plus ou moins.
    Phrase UI au §5.2.
14. **Branche.** S1 part de `main` (`67c99a25`). Plus de pile sur
    une branche E5 morte.

---

## 2. Catalogue — toutes les variables

**Classe**

| Code | Sens | Le skipper le touche ? |
|---|---|---|
| `norme` | Consensus publié (Beaufort, OMM, Met Office) | Non (affichage) |
| `usage` | Règle de pouce skipper, **chiffre de profil** | Via profil |
| `derive` | Calculé (horizon × nœuds, perles) | Indirect |
| `ui` | Choix produit (sac, lookahead) | Via profil si utile |
| `engine` | Anti-spam, perles, caches | Non |

**Édition UI**

| Code | Sens |
|---|---|
| `lock` | Jamais éditable (norme) |
| `profile` | Change avec Côtier / Croisière / Large |
| `boat` | Lu depuis la polaire (v1 : pas de saisie) |
| `knob` | Curseur métier — **S6+**, pas v1 |
| `expert` | Trappe « Chiffres » — **S7+**, pas v1 |
| `hide` | Invisible |

### 2.1 Vent

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `galeKt` | 34 | kn | norme (F8) | lock | oui, si gale / wx |
| `galeHoldKt` | 28 | kn | norme (F7) | lock | oui, si gale |
| `galePct` | 15 | % rose climo | ui | expert (S7+) | oui, Simulation seulement |
| `windShiftKt` | 8 | kn | usage (pas un grain OMM) | profile | oui, si wind-shift |
| `windShiftDeg` | 40 | ° | usage | profile | oui, si wind-shift |
| `windShiftResetKt` | 4 | kn | ui | expert (S7+) | non |
| `windShiftResetDeg` | 20 | ° | ui | expert (S7+) | non |

Grain OMM = **+16 kn** (8 m/s). Le profil Large prend ce chiffre
pour `windShiftKt`. Côtier / Croisière restent en « ça change la
toile ».

### 2.2 Courant et mer

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `currentShiftKn` | 1.0 | kn | usage | profile | oui, si current-shift |
| `currentIgnoreKn` | 0.3 | kn | usage (bruit) | expert (S7+) | non |
| `currentInvertDeg` | 120 | ° | usage | expert (S7+) | oui, si invert |
| `hsShiftM` | 1.0 | m | usage | profile | oui, si hs-shift |
| `hsAlertM` | **3.5** | m | usage | profile | oui, si hs / wx |

**Une vérité par profil — Hs alerte (chiffre écrit, déjà
résolu) :**

| Profil | `hsAlertM` | Pourquoi ce chiffre |
|---|---|---|
| Côtier | **2,5 m** | Plus bas que l’E1 pour « je parle tôt » |
| Croisière | **3,5 m** | Constante E1 actuelle (`HS_ALERT_M`) |
| Large | **5,0 m** | Plus haut que l’E1 pour « je ne parle que si ça compte » |

Ancrage Croisière = E1 3,5 m : un seul chiffre, tests E1 verts.
On **n’applique pas** 0,30 × 14 m = 4,2. La formule Adlard Coles
(vague déferlante ~30 % L) a **informé** Côtier / Large ; ce
n’est **pas** un second chemin runtime.

Le LLM reçoit `hsAlertM` **déjà résolu** + `hsAlertRule`
(`"constante profil, ex. Croisière E1 3,5 m"`), jamais
« invente 3,5 » ni « sinon 0,30×L ».

### 2.3 Pluie et repli (Suivre)

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `rainMmH` | 4 | mm/h | norme UK (heavy ≥ 4.1) | profile | oui, si rain / marina |
| `rain3hMm` | 10 | mm / 3 h | norme OMM (heavy ~10) | profile | oui |
| `marinaRefugeNm` | 25 | nm | ui / usage Plan B | profile | oui, si marina-refuge |
| `marinaRefugeCooldownMin` | 360 | min | ui | expert (S7+) | non |

Simulation : les quatre existent dans l’objet mais
`enabled: false`, `reason: "simulation_no_rain"`.

### 2.4 Fond

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `depthAlertM` | **15** | m | ui (mal nommé « talonnage ») | profile | oui |
| `depthCooldownNm` | 2 | nm | engine | hide | non |
| `draftM` | lu polaire (~1.4 Leopard) | m | boat | lecture polaire | oui, si depth |
| `depthLabel` | « approche de plateau » | — | ux | — | oui (libellé, pas « haut-fond » si 15 m) |

**Une vérité par profil — fond (chiffre écrit, déjà résolu) :**

| Profil | `depthAlertM` | Libellé | Pourquoi ce chiffre |
|---|---|---|---|
| Côtier | **8 m** | plateau | max(8, 5 × 1,4) figé une fois |
| Croisière | **15 m** | plateau | Constante E1 actuelle (`DEPTH_ALERT_M`) |
| Large | **5 m** | talonnage | max(5, 3 × 1,4) figé ; vrai UKC |

Ancrage Croisière = E1 15 m : un seul chiffre, tests E1 verts.
On **n’applique pas** max(12, 8 × 1,4) = 12. Pas de second
défaut « tant que le tirant n’est pas touché » : v1 ne saisit
pas le tirant.

Phrase skipper : Côtier/Croisière = « on approche du plateau » ;
Large = « risque de talonner ».

### 2.5 Formalités / AMP / sac

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `iciRadiusNm` | 30 | nm | ui (Met Éireann côtier = 30) | expert (S7+) | contexte sac |
| `alongAmpNm` | 15 | nm | ui | expert (S7+) | si amp-ahead |
| `alongMarinaNm` | = marinaRefuge | nm | ui | — | — |
| `ampHysteresisNm` | 5 | nm | engine | hide | non |
| `ampAheadMinNm` | 5 | nm | ui | expert (S7+) | si *-ahead |
| `zeeConfirmBags` | 2 | sacs | engine | hide | non |
| `eezAcceptNm` | 240 | nm | engine | hide | non |
| `maxPoe` | 4 | — | engine | hide | non |
| `maxAmp` | 5 | — | engine | hide | non |
| `maxNearby` | 3 | — | engine | hide | non |
| `maxAnchorages` | 5 | — | engine | hide | non |
| `maxScience` | 5 | — | engine | hide | non |
| `gebcoCoastalCutoffNm` | 20 | nm | engine | hide | non |

CNUDM (12 / 24 / 200 nm) **n’est pas** un seuil d’alerte. On
peut le citer en Expert (S7+) comme culture, pas comme curseur.

### 2.6 Route, horloge, lookahead

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `routeSampleNm` | 12 | nm | engine | hide | non |
| `suivreLookaheadH` | 36 | h | usage (fenêtre GRIB) | profile (v1) ; knob S6+ | contexte |
| `suivreLookaheadMaxNm` | **= H × kn** | nm | derive | hide | non |
| `maxPearlsSim` | 60 | — | engine | hide | non |
| `maxPearlsSuivre` | **suit H** | — | derive | hide | non |
| `planningKn` | 7 | kn | usage (cat VMG ; croiseurs ~5) | boat / polaire | contexte ETA |
| `minBoatKnots` | 0.5 | kn | engine | hide | non |
| `fallbackExpeditionKnots` | 7 | kn | usage | hide si polaire | non |
| `speedFromWindFactor` | 0.45 | — | usage | hide | non |
| `speedFromWindMinMax` | 4–11 | kn | usage | hide | non |
| `officialT0` | 2026-05-15T08:00Z | — | norme expédition | lock | non (déjà horloge) |
| `portDays.*` | 3 / 1 / 0 / 3 | j | ui | hide (v1) | non |
| `airCalendarHours` | 8 | h | ui | hide | non |
| `saintMaurLandHours` | 4 | h | ui | hide | non |

Aujourd’hui Suivre plafonne à **24 perles / ~350 nm** (fenêtre
36 h). Afficher 48 h avec ce plafond **ment**.

**Règle — l’horizon ne ment pas :**

1. Le chiffre affiché (profil v1, knob plus tard) **est**
   `suivreLookaheadH`.
2. `plafondNm = suivreLookaheadH × planningKn`  
   (`planningKn` = polaire si elle en donne, sinon défaut du
   profil : Côtier 5, Croisière / Large 7).
3. `maxPearlsSuivre = max(1, ceil(plafondNm / routeSampleNm))`.
4. **Si** on ne peut pas lever le plafond (heures × nœuds,
   perles), **on n’affiche pas** ce cran — ni 48 h sur Large,
   ni un knob 48 h.
5. Interdit de préchauffer toute la route (39 000 nm). Le
   plafond **suit** H ; il ne redevient pas 350 / 24 dès que
   H = 48.

Exemples (sample 12 nm) :

| H | kn | `plafondNm` | perles min |
|---|---|---|---|
| 24 | 5 (Côtier) | 120 | 10 |
| 36 | 7 (Croisière) | 252 | 21 |
| 48 | 7 (Large) | 336 | 28 |
| 48 | 10 (polaire rapide) | 480 | 40 |

### 2.7 Juge / film / file (pas météo)

| id | Valeur Croisière | Unité | Classe | UI | LLM |
|---|---|---|---|---|---|
| `groupNm` | 15 | nm | ui | profile (Côtier 8 / Large 25) | non |
| `groupNmFast` | 80 | nm | ui | hide | non |
| `groupWallMs` | 8000 | ms | engine | hide | non |
| `cooldownNm` | 15 | nm | engine | hide | non |
| `cooldownMin` | 30 | min | engine | hide | non |
| `maxStoryPending` | 3 | — | engine | hide | non |
| `keepStoryTypes` | marina, cyclone, depth, gale | — | norme sécurité | lock | non |
| `playProfiles` | real/read/normal/fast | — | film | déjà barre | non |
| `dwellMs` | 2.4–1.1 s | ms | film | déjà barre | non |

Le **profil film** (`real`…) ≠ **profil skipper** (`coastal`…).
Deux axes. On ne les fusionne pas.

Pastilles **déjà posées** : hors recalcul. Le juge des **prochains**
événements lit les nouveaux ordres. Voir §1.6 et §5.3.

### 2.8 Bateau (entrées, pas des seuils)

| id | Défaut Berry | Classe | UI | LLM |
|---|---|---|---|---|
| `loaM` | 14 | boat | **lu polaire**, pas de champ v1 | oui si Hs (contexte) |
| `draftM` | 1.4 | boat | **lu polaire**, pas de champ v1 | oui si depth |
| `boatName` | polaire | boat | déjà Tools | contexte |
| `polarRaw` | upload | boat | déjà Tools | non (trop gros) |
| `comfort` | normal | knob | **S6+** Souple / Normal / Dur | oui (adjectif) |

v1 : L et tirant **n’entrent pas** dans Hs / fond (chiffres de
profil, §2.2 / §2.4). Ils voyagent dans `skipper.boat` pour le
récit.

`comfort` (S6+) ne touchera **que** `windShift*` et `hsShiftM` /
un cran sur `hsAlertM` (±0,5 m). Pas la gale. Pas v1.

---

## 3. Classement pour l’écran (vue skipper)

**v1 — le skipper décide**  
`coastal` | `cruise` | `ocean` (trois pastilles)

**v1 — le skipper voit, il ne saisit pas**  
Bateau (nom, L, tirant) **lus** depuis la polaire.  
`galeKt` / `galeHoldKt` (« Beaufort 8 / 7 »).

**S6+ — le skipper affine**  
`comfort`, `horizonH` (knob 24 / 36 / 48, déjà dérivé du profil
en v1)

**S7+ Expert plié**  
`galePct`, resets vent, `currentIgnoreKn`, `currentInvertDeg`,
`rain*`, `iciRadiusNm`, `alongAmpNm`, `ampAheadMinNm`,
`marinaRefugeNm` si on veut forcer hors profil

**Jamais à l’écran**  
perles, max*, cooldown engine, GEBCO, EEZ accept, port days,
facteur 0.45, `groupWallMs`, polar grid

---

## 4. Profils et dérivation

### 4.1 Les trois caractères

| | Côtier | Croisière (défaut) | Large |
|---|---|---|---|
| Id | `coastal` | `cruise` | `ocean` |
| Phrase | « Je parle tôt. » | « Ordres Berry. » | « Je ne parle que si ça compte. » |
| Grain vent | +6 kn / 30° | +8 kn / 40° | +16 kn / 60° (OMM) |
| Hs alerte | **2,5 m** | **3,5 m** | **5,0 m** |
| Hs shift | 0.6 m | 1.0 m | 1.5 m |
| Courant | 0.6 kn | 1.0 kn | 1.5 kn |
| Fond | **8 m** | **15 m** | **5 m** |
| Pluie | 3 mm/h, 8 mm/3 h | 4 / 10 | 6 / 15 |
| Marina | 15 nm | 25 nm | 40 nm |
| Horizon Suivre | 24 h | 36 h | 48 h |
| Groupement | 8 nm | 15 nm | 25 nm |
| Planning kn sans polaire | 5 | 7 | 7 |
| Libellé fond | plateau | plateau | talonnage |

Chaque cellule Hs / fond = **le** chiffre. Pas de « ou formule ».

`comfort` (**S6+**, pas v1) :

| | Souple | Normal | Dur |
|---|---|---|---|
| vent notable | −2 kn / −10° | 0 | +4 kn / +15° |
| Hs alert | −0.5 m | 0 | +0.5 m |

Plafond (quand S6 existera) : `windShiftKt` ne dépasse pas 16 en
côtier/croisière (on ne transforme pas un skipper souple en grain
OMM sans passer Large). Gale **jamais** modulée.

### 4.2 Résolution

```
resolveOrders(saved, polar, mode) →
  { profile, boat, knobs, thresholds[], phrase, rainEnabled }
```

- `thresholds[]` : chaque id avec `{ value, unit, source, locked }`
- `source` ∈ `beaufort` | `wmo` | `metoffice` | `usage` | `derive` | `ui`
- `value` = le chiffre du profil (Hs, fond, vent…) **ou** le
  dérivé honnête (horizon × kn, perles). Jamais deux candidats.
- `boat` = lecture polaire (`name`, `loaM`, `draftM`,
  `planningKn` si présent).
- Un changement de polaire **propose** Côtier si L &lt; 11 m ou
  tirant &lt; 1.1 m. Refusable. Pas de bascule silencieuse.

---

## 5. Stratégie UI / UX

### 5.1 Où

`ToolsSidebar`, sous le bloc Polaire, même largeur, titre
**« Ordres du skipper »**.

Interdit : barre film, 3ᵉ bouton view, modal au boot, overlay
cinéma.

### 5.2 Hiérarchie visuelle (haut → bas)

**v1 (S3) :**

1. Trois pastilles Côtier / Croisière / Large (une seule active).
2. **Une phrase** du caractère (change avec la pastille).
3. **Phrase Suivre partagé** (toujours, les deux modes) :  
   « L’horloge officielle ne change pas. C’est **ton** skipper
   qui parle plus ou moins. »
4. **Exemple vivant** (sac actuel, &lt; 2 lignes) :  
   « Vent ici 18 kn — je me tais. À 34 kn je parle. Mer 1,4 m —
   sous 3,5 m. »
5. Bateau **lu** : nom + L + tirant (polaire). Pas de champs.
6. Pluie : Suivre = résumé ; Simulation = « pas de pluie
   inventée ».
7. Lien discret **« Revenir aux ordres Berry »**.

**S6+ (plus tard, même panneau) :** Confort (3 pills) ;
horizon 24 / 36 / 48 — **grisé en Simulation** + « cette jambe »
(le cran 48 h n’existe que si le moteur le tient, §2.6).

**S7+ :** Détail plié **« Chiffres »** (Expert).

### 5.3 Comportement

- Recalcul **local**, &lt; 300 ms, **sans** `GET /ici`.
- Briefing : une ligne cyan **une fois** après un changement
  (« Ordres : croisière · Hs 3,5 m · fond 15 m »), puis elle
  s’efface.
- **Pastilles déjà posées restent.** Densité / langage des
  **suivantes** seulement (Côtier plus dense, Large plus rare).
  Même langage pleine / creuse.
- Clic pastille = déjà `skipper-click` → `now`. On garde.
- Cinéma : sidebars rangées (déjà). Ordres actifs. Expert
  inaccessible (et absent en v1).
- Langue FR/EN via i18n existant. Libellés skipper, **jamais**
  `wind-gale` à l’écran.
- Play **n’attend pas** le LLM.

### 5.4 Ce qu’on ne fait pas

- Pas de dump JSON cockpit.
- Pas d’attendre le LLM pour appliquer un profil.
- Pas de rewind du film.
- Pas de relancer / réécrire un récit `ready`.
- Pas d’éditer Beaufort 8 dans l’UI grand public.
- Pas de saisie tirant / longueur en v1.
- Pas d’afficher 48 h si le plafond reste 24 perles / 350 nm.

### 5.5 Persistance

Clé `ng.sim.skipperOrders.v1` :

```json
{
  "profile": "cruise"
}
```

v1 ne persiste **que** le caractère. Bateau = polaire à chaque
chargement. `planningKn` effectif = polaire, sinon défaut du
profil.

S6+ pourra ajouter `comfort`, `horizonH`, `expert` dans le
**même** objet, même clé. Reset vide tout et remet `cruise`.

---

## 6. Relier aux LLM

E5 est **déjà** dans `main` (`enqueueStory` → `POST /ici/story` →
NIM → OR ± `:online` → Claude). Ce plan **n’allume pas** un
autre fournisseur. Il **enrichit le petit JSON**.

### 6.1 Quand on parle au modèle

Comme aujourd’hui : événement `now` ou `group`, file
fire-and-forget. En plus :

- le payload contient les **ordres qui ont déclenché CET
  événement**, pas les 40 constantes ;
- `tavily: null` toujours ;
- `nvidia` null tant que pas `ready`.

On n’envoie **pas** la grille polaire, pas le GeoJSON, pas le
catalogue Sentinel.

### 6.2 Forme (contrat, pas le prompt entier)

```json
{
  "event": "hs-shift",
  "kind": "climatology",
  "payload": { "hs": 3.6, "p50": 3.6, "p90": 4.8, "kind": "climatology" },
  "skipper": {
    "profile": "cruise",
    "profile_phrase": "Ordres Berry — croisière.",
    "comfort": "normal",
    "boat": { "name": "Leopard 46", "loaM": 14, "draftM": 1.4 },
    "used": [
      {
        "id": "hsAlertM",
        "value": 3.5,
        "unit": "m",
        "source": "usage",
        "rule": "constante Croisière E1 3,5 m"
      }
    ]
  },
  "tavily": null,
  "nvidia": null
}
```

Règles :

1. `used` = uniquement les ids qui ont **fait basculer**
   l’événement (ex. gale → `galeKt` ; marina → `rainMmH` +
   `marinaRefugeNm`). **Un** `value` par id.
2. Le modèle **cite** `value` + `source`. Interdit d’écrire
   « en général on considère 5 m » si `used` dit 3.5.
3. Si `source` = `beaufort`, il peut dire « Beaufort 8 ».
4. Si un champ météo est `null` dans le payload événement, il
   reste null. Les ordres ne **remplissent** pas un trou.
5. Changement de profil : **nouveaux** événements seulement.
   Pastilles déjà posées **conservées**. `ready` antérieur
   **conservé** (c’était vrai sous les anciens ordres ; on
   n’écrit pas l’histoire à l’envers ; pas de 2ᵉ récit).
6. `:online` inchangé : seulement URL **déjà dans le sac** +
   Gold / clic / alerte. Les ordres skipper ne déclenchent
   **pas** une recherche monde.
7. Play ignore `pending`. Phrase locale + ligne d’ordres
   suffisent.

### 6.3 Prompt système (ajout, pas un 2ᵉ chat)

Une phrase en plus du prompt E5 :

> Tu rédiges pour CE skipper. Ses seuils sont dans skipper.used.
> Cite-les. N’invente pas d’autre chiffre. Thinking OFF.

Un récit, pas quatre agents. Pas de `POST /polar/chat`.

### 6.4 Ce que le LLM n’est pas

- Pas le juge d’affichage (E3 règles).
- Pas Nemotron Ultra.
- Pas un réglage : il **raconte** les ordres, il ne les vote pas.

---

## 7. Contrat code

Nouveau module `src/engine/skipperOrders.js` (pur) :

- `PROFILES = ["coastal", "cruise", "ocean"]`
- `DEFAULT_ORDERS` = Croisière = constantes E1 actuelles
  (Hs 3,5 m, fond 15 m, vent +8 / 40°, etc.)
- `resolveOrders(saved, { polar, mode })` — v1 sans `comfort`
- `thresholdsForEvent(type, orders)` → tableau `used`
- `lookaheadBudget(orders)` → `{ hours, maxNm, maxPearls }`
  (règle §2.6)
- `exampleLine(orders, sample)` → phrase vivante FR/EN

`eventRules.detectEvents` et `iciAlong.lookaheadNmFor` reçoivent
`orders.thresholds` via `ctx` (déjà là pour mode / rain / grib).
Les `export const` restent les **défauts Croisière** (tests E1
verts).

`storyPayload` ajoute `skipper` (ci-dessus).

`useSkipperOrders` : charge / sauve `localStorage` (`profile`),
expose `orders` à `App` → `useIciDossier` / `useIciAlong`.

UI : `SkipperOrdersPanel` dans `ToolsSidebar` — **3 pastilles +
bateau lu + phrases**. Pas de champs L/tirant, pas Confort, pas
Expert en S1–S3.

Pas de Mongo. Pas de route BI nouvelle. `POST /ici/story`
inchangé côté URL ; le body grandit.

---

## 8. Lots

| Lot | Quoi | Play attend ? | LLM |
|---|---|---|---|
| **S1** | `skipperOrders.js` + tests (3 profils, **un** chiffre, budget 24/36/48 h) | non | non |
| **S2** | `ctx.orders` dans detect / along / judge ; plafond Suivre **suit** H | non | non |
| **S3** | Panneau : **3 pastilles** + bateau polaire + phrases + persist `profile` | non | non |
| **S4** | `storyPayload.skipper` + phrase système E5 | non (file déjà async) | oui, JSON seulement |
| **S5** | Recette + médias phrases FR/EN | non | mocks |
| **S6** | Confort (Souple / Normal / Dur) ; knob horizon si on l’expose | non | non |
| **S7** | Trappe Expert « Chiffres » | non | non |

Ordre **S1 → S2 → S3 → S4 → S5**. S6 / S7 **après**, pas dans
la v1 allégée. S3 se recette sans clé NIM (templates). S4 se
recette avec fetch mocké comme E5.

**Branche :** S1 part de **`main`** (`67c99a25`). E1–E5 y sont.
Plus de pile sur #172, plus de branche E5 morte. PR draft
possible plus tard. Pas de merge sans le mot « merge ».

---

## 9. Recette

1. Défaut = Croisière : **mêmes** événements qu’aujourd’hui
   (Hs 3,5 m, fond 15 m). Tests E1 **toujours verts**.
2. Côtier : plus de `wind-shift` / `hs-shift` sur la même jambe
   fixture ; Hs bascule à **2,5 m** ; phrase « plateau » si fond
   (seuil **8 m**).
3. Large : le +8 kn **ne** déclenche **pas** ; +16 kn oui ;
   Hs **5,0 m** ; fond **5 m** « talonnage ».
4. Gale 34 kn **identique** sur les 3 profils.
5. Simulation : zéro `marina-refuge` ; UI pluie grisée.
6. Changer de profil en Play : le film **continue** ; 0 `await`
   chat ; pastilles **déjà posées intactes** ; 0 second récit
   sur un `ready` ; les **suivantes** suivent le nouveau profil.
7. Cinéma : pas de panneau ; pastilles suivent le profil pour
   la suite du film.
8. JSON story : `skipper.used` présent, **un** `value` par id,
   `tavily: null`, pas de Nemotron dans les sources.
9. `localStorage` reset → Croisière.
10. Polaire petite (L 9 m) → **proposition** Côtier, pas un
    forçage. Pas de champ L/tirant à remplir.
11. Large (48 h) : `plafondNm = 48 × planningKn` et assez de
    perles. Si on force le vieux 24 / 350, **échec** — et l’UI
    n’a alors **pas** le droit d’écrire 48 h.
12. Phrase visible : horloge officielle inchangée ; c’est **ton**
    skipper qui parle plus ou moins.

---

## 10. Hors scope

- Nemotron / Token Factory / Tavily monde / Ultra
- Réglages dans Blue Intelligence prod
- Jours à quai éditables, polar chat, 3ᵉ view mode
- Saisie tirant / longueur, Confort, Expert (S6 / S7, pas S1–S3)
- Mongo / resync
- Fusion profil film × profil skipper

---

## 11. Fichiers (prévision S1–S4)

| Fichier | Rôle |
|---|---|
| `src/engine/skipperOrders.js` + `.test.js` | Contrat + dérive + budget H |
| `src/engine/eventRules.js` | Lit `ctx.orders` |
| `src/engine/iciAlong.js` | Horizon / perles / marina depuis orders |
| `src/engine/displayJudge.js` | `HS_ALERT_M` depuis orders |
| `src/engine/storyQueue.js` | `skipper` dans le payload |
| `src/hooks/useSkipperOrders.js` | persist `profile` |
| `src/components/SkipperOrdersPanel.jsx` | 3 pastilles + bateau lu |
| `src/components/ToolsSidebar.jsx` | Monte le panneau |
| `src/App.jsx` | Passe `orders` |
| `src/i18n/fr.js` / `en.js` | Phrases skipper |
| `server/story_cascade.py` | Une ligne système (S4) |

`sceneGate.js` intouché.

---

## 12. Lien avec l’état de l’art (rappel)

| Seuil | On le traite comme |
|---|---|
| 34 / 28 kn | norme, lock |
| +16 kn | norme grain, **profil Large seulement** |
| +8 kn / 40° | usage toile, Croisière |
| 1 kn courant | usage routing |
| Hs 2,5 / **3,5** / 5,0 m | usage de profil ; Croisière = E1 ; **pas** 0,30×L runtime |
| 4 mm/h / 10 mm/3 h | Met Office + OMM, profil |
| 5 kn vs 7 kn | usage mono vs cat, profil / polaire |
| Fond 8 / **15** / 5 m | Croisière = E1 ; Côtier/Large figés ; libellé plateau sauf Large |
| 24 / 36 / 48 h | usage fenêtre ; plafond = H × kn, perles suivent |
| 12 nm perles | engine, hide |

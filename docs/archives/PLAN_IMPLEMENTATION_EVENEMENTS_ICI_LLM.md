> **Archivé le 22 septembre 2026 — réalisé.** NVIDIA / Tavily : voir `docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md`. Index : [docs/README.md](../README.md).

# Plan — événements `ici()`, juge d’affichage, récit LLM

Atelier **`naviguide-simulator/`** seulement. Prod `www.naviguide.fr` et
Blue Intelligence **intouchées**.

Version **1.5** — 16 septembre 2026 (complète la v1.4 du même jour).
Ce fichier **est** le plan : on ne crée pas un second document.

Hérite de :

- [ici-tout.md](../ici-tout.md)
  (ce que le sac point contient déjà — on ne le recopie pas)
- [PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md](./PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md)
  (deux boutons, GRIB du jour, pas de dump cockpit)
- `./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`
  §22 (un pas = `ici()` gratuit)
- `./PLAN_IMPLEMENTATION_SIMULATION_B.md`
  (couloir / cube, pas un GRIB globe)
- `./PLAN_IMPLEMENTATION_CLIMATOLOGIE.md`
  (`kind` honnête, pas de vent inventé)

Ce plan **n’allume pas** Nemotron, NVIDIA Token Factory, ni Tavily
tant que les lots E1–E4 ne sont pas recettables. Ces fournisseurs
sont **uniquement** le lot **E5**. Le sac point existe déjà
(`GET /ici`, `mergeDossier`, `narrateIci`) : on ne le relance pas
depuis zéro.

**Ce tour (v1.5) :** **E5** — brancher `enqueueStory` sur la
cascade habituelle **NIM → OpenRouter (± `:online`) → Claude**.
Le film **n’attend jamais** un LLM. **Pas** Nemotron. **Pas**
Tavily. **Pas** Token Factory. **Pas** de merge.

---

## 0. Carte du plan (où lire quoi)

La v1 disait : phrase locale d’abord, LLM plus tard, juge
`hide | now | later | group`. La v1.1 a collé ça sur le code du
16 septembre. La v1.2 a tranché replay / file / pluie / prise E5.
La **v1.3** a **codé** E1 + E3. La **v1.4** a **codé** E2 + E4.
La **v1.5** allume E5 sur la cascade habituelle (NIM → OR ±
`:online` → Claude), **sans** Nemotron ni Tavily.

| Question | Où |
|---|---|
| Comment l’appli **détecte** (ZEE, vent/courant, AMP, marina repli, autres) | §5 + §16 |
| Conscience du **trajet GPS déjà planifié** (pas seulement le point) | §4 + §16 |
| **Ne pas attendre** le LLM (collecte / snapshot / sac 30 nm / file) | §6 + §18 |
| Le LLM travaille le **dossier déjà collecté** + **null honnêtes** | §8 + §19 |
| **Présenter** le long de la route : timeline, grouping, **replay** | §9 + §20 |
| Catalogue + seuils + hystérésis + **Suivre vs Simulation** | §5, §10, §17 |
| **Juge** : afficher / ne pas afficher ; si oui, immédiat ou groupé | §7 + §21 |
| NVIDIA Token Factory / Tavily / Nemotron : **toujours pas** | §22 |
| Cascade **habituelle** NIM → OR ± `:online` → Claude (**E5 branché**) | §22 + §26 |
| Ordre **détecteurs → sac trajet → juge → UI** ; 1er lot sans LLM | §11 + §23 |
| **Catalogue exhaustif** (tous les ids, y compris réservés) | §10 + §17 + §24 |
| **Contrat** collecte / dossier prêt / présentation route | §6 + §18 + §19 + §20 + §24 |
| Ce qui est **codé** en v1.3 | §24 |

### 0.1 Décisions verrouillées v1.2 (à scanner)

1. Conscience du trajet = le trait GPS **déjà** dans `flattenRoute`
   de **cette** jambe (officiel ou perso). Pas un nouveau GPS.
   Pas le globe. Les détecteurs « devant » marchent **sur la
   polyligne**, pas « n’importe quelle AMP dans un rayon ».
2. Détection = fonctions **pures** sur `at` + `prev` + `along`.
   Zéro HTTP, zéro chat.
3. Le film et le HUD **n’attendent jamais** un LLM. Sac point +
   snapshot Δ + sac trajet + liste + file à côté (§18).
   `useIciDossier` ne `await` pas de chat.
4. Pluie / `marina-refuge` = **Suivre seulement** (GRIB `rainMm`
   déjà là). En Simulation on **n’invente pas** la pluie et on
   **n’ajoute pas** `rain` Open-Meteo en E1 (ça mélangerait
   `forecast` et le film `climatology`).
5. Juge = d’abord **afficher ou non** ; ensuite seulement
   **maintenant** ou **plus tard groupé**.
6. Timeline Simulation = pastilles sur la barre du film (déjà
   `SimulationFilmBar`) + digest dans le Briefing. Replay = seek
   sur **cette** jambe, **mêmes** événements déjà calculés.
7. Nemotron / Token Factory / Tavily = **pas maintenant**.
   E5 = cascade **habituelle** déjà dans `backend/app/core/llm.py` :
   **NIM → OpenRouter (± `:online`) → Claude**. **Branchée** en
   v1.5 via `POST /ici/story`. Le film n’`await` pas.
8. Mongo live = VPS (`127.0.0.1:27017`). Atlas figé.
   **Interdit** : `infra/vps/sync-from-atlas.sh`.
9. `kind` honnête : observation ≠ climatology ≠ forecast.
   Produit absent = `null` + `reason`, jamais inventé.
10. E1 + E3 **faits** (v1.3). E2 + E4 **faits** (v1.4). E5 =
    cascade habituelle **branchée** (v1.5). Tavily / Nemotron /
    Token Factory restent hors scope.

---

## 1. En une phrase

Le bateau avance sur un **trait GPS déjà connu**. Le moteur compare
le sac d’**ici** et le sac **devant** (cette jambe). Il sort des
**événements**. Une phrase locale s’affiche **tout de suite**. Un
**juge** décide si on montre, maintenant, plus tard, ou groupé. Un
LLM, **plus tard et ailleurs**, peut raconter le dossier déjà
collecté. Le film **n’attend jamais** le LLM.

---

## 2. Vocabulaire (lire avant les lots)

| Mot | Sens ici | Ce que ce n’est pas |
|---|---|---|
| **Sac `ici()`** | Petit dossier autour du bateau (~30 nm) + extras de **cette** jambe | Toute la carte GeoJSON |
| **Point** | Position actuelle (cast / snap sur le trait) | Le prochain waypoint |
| **Jambe** | Trait entre deux escales Bmap (ex. La Rochelle → Ajaccio) | Les 39 000 nm |
| **Lookahead / `along`** | Points GPS **devant**, jusqu’à la prochaine escale (ou 24–48 h en Suivre) | Un catalogue monde |
| **Événement** | Un **changement** détecté par des **règles** (chiffres, ids) | Un paragraphe LLM |
| **Phrase locale** | Template dans `narrateIci` / `eventRules` | Un appel réseau « chat » |
| **Juge d’affichage** | `hide` / `now` / `later` / `group` | Un modèle « vérité » |
| **File** | Filet async `pending` → `ready` / `failed` | Un `await` dans Play |
| **`kind`** | `observation` ≠ `forecast` ≠ `climatology` | Mélanger GFS et vent du mois |
| **Suivre l’expédition** | Un bateau officiel, `t0` = **15 mai 2026, 08:00 UTC**, 1 s = 1 s, GRIB du jour | Un 3ᵉ bouton |
| **Simulation** | Film, climatologie, Play, route perso possible | Le bateau officiel |

Interdit dans l’UI : « mode suivre », « bateau virtuel » comme
interrupteur. Deux boutons seulement (plan Suivre / Simulation).

---

## 3. Où on en est (ne pas recasser)

Croisé avec le code réel du 16 septembre 2026, pas recopié depuis
`ici-tout.md`.

| Déjà là | Fichier / comportement | Pas encore |
|---|---|---|
| Sac **point** ~30 nm | `GET /ici` → `fill_dossier` ; client `mergeDossier` | Sac **trajet** (`route` + `along`) |
| Briefing local | `narrateIci` : une phrase par famille, zéro LLM | Templates d’événement hors `zee-enter` |
| Un seul événement (avant v1.3) | `zeeEnterEvent(prevMrgid, zee)` — 1× si `mrgid` change | **v1.3** : catalogue E1 + hystérésis + juge |
| Debounce / refetch | 800 ms, 3 nm, mini 8 s, timeout 40 s (`useIciDossier`) | File d’analyse async |
| Jambe **nommée** | `jambe` → `marks.kind = "leg"` (from / to / phase / véhicule) | Points GPS de la jambe dans le sac |
| Destination pour **l’atlas** | `dest_lat` / `dest_lon` = prochaine escale (`destMark`) → croisements IBTrACS | Lookahead ZEE / AMP / marinas sur le trait |
| Polar | bateau + VMG + nœuds / ETA — **jamais** la grille 181×61 | Polar qui « parle » au LLM |
| Horloge | `DEFAULT_T0_ISO = 2026-05-15T08:00:00.000Z`, 3 j à quai Bmap | Événements `escale-in` / `escale-out` câblés |
| Trait GPS | `flattenRoute` (`lat`, `lon`, `cumNm`, `filmCum`) ; GeoJSON `public/route.geojson` ; waypoints nommés | Échantillon 1 pt / 10–15 nm pour `iciAlong` |
| Vent **Suivre** | GRIB2 journalier autour du bateau, déjà `rainMm` (Open-Meteo hourly) | Détecteur `wx-alert` / `marina-refuge` |
| Vent **Simulation** | Climatologie (atlas / zone), `kind: climatology` | Pareil : comparer **climo à climo**, pas GFS |
| Courant | RTOFS dans `weather.current` (`kind: forecast`) ; atlas `current.direction_to_deg` | `current-shift` |
| AMP | `amp[]` + `visit_url` ≠ `manager_url` dans le sac 30 nm | `amp-ahead` sur le trait |
| Marinas / WPI | `nearby.marinas`, `capitaineries`, `wpi` dans 30 nm | Choisir un **repli** si pluie |
| Sentinel | Catalogue CDSE L2A au **bbox bateau**, `kind: observation` | Événement « nouvelle scène » (optionnel, later) |
| Review / Gold | `GET /api/review/fiche` — **401 sans admin** ; `review.reason=review_requires_admin` | Ne pas raconter Gold au public |
| `sceneGate` | Porte **peinture** (route + horloge + caméra) | Ce n’est **pas** un détecteur d’événements |
| Un panneau Briefing | `Sidebar` : `iciBriefing` | Pastilles sur la barre du film |

Contrat déjà verrouillé (étape 1 §22), **sans** allumer Tavily :

> Un pas = `ici()` **gratuit**. Polar et searoute parlent au **point**
> et à **cette** jambe. Un récit, pas quatre agents.

Mongo **live** = VPS (`127.0.0.1:27017`, service `blue-intelligence`).
Atlas est figé. **Interdit** : `infra/vps/sync-from-atlas.sh`.

---

## 4. Conscience du trajet (points GPS / jambes)

Aujourd’hui `ici(lat, lon)` **ignore** le trait. `useIciDossier`
envoie seulement le point bateau + `month` + **un** couple
`dest_lat` / `dest_lon` (la prochaine escale) pour
`/climatology/crossings`. `mergeDossier` ajoute le **nom** de la
jambe, pas les vertex.

Le playhead, lui, **connaît** déjà le trajet :

1. GeoJSON officiel (ou trait Simulation) → segments.
2. `flattenRoute` → liste de points (`lat`, `lon`, `cumNm`).
3. Horloge → nm + date civile depuis `t0`.
4. `jambe` / `destMark` → de quelle escale vers quelle escale.

**Lot E2** (après les détecteurs point) : on ajoute des extras,
sans gonfler un futur prompt.

| Champ | Qui le remplit | Rôle | Interdit |
|---|---|---|---|
| `at` | `GET /ici` déjà | Sac 30 nm au bateau | Le globe |
| `leg` | `jambe` déjà amorcé | `from`, `to`, nœuds, ETA, véhicule | Grille polar |
| `route` | client, depuis `flattenRoute` **de cette jambe** | 1 point GPS / **10–15 nm** (constante `ROUTE_SAMPLE_NM`) | Les 12 000+ vertex d’un coup |
| `along` | `iciAlong` (nouveau, même moteur que `fill_dossier`, **moins** de familles) | ZEE / AMP / PoE / marinas **devant** jusqu’à N nm **ou** la prochaine escale | Export AMP monde, 4 500 projets |

### Comment on « voit » devant sans tout refetch

- On **découpe** le trait de la jambe en perles (10–15 nm).
- Pour chaque perle : un **mini-sac** (ZEE `mrgid`, AMP dans 15 nm,
  marina / WPI dans 25 nm). Vent / RTOFS / Sentinel : **pas** à
  chaque perle (trop cher). Seulement au bateau + 1 ou 2 perles
  « météo » (prochaine + horizon).
- Cache clé = `arrondi(lat, 2)` + `arrondi(lon, 2)` + `month` +
  famille. Un `GET /ici` déjà fait à 3 nm près **sert** encore
  (`MOVE_NM = 3`).
- **Simulation** : au chargement de jambe (Play pas encore lancé),
  préchauffer **cette** jambe (géo + climatologie). Pas les 39 000 nm.
- **Suivre** : maintenant + **24–48 h** de mer devant (couloir GRIB
  déjà borné). Interdit de préchauffer Berry entier.

Le sac au bateau reste petit. Le lookahead nourrit « AMP dans 40 nm »
sans coller tout le JSON dans un LLM.

---

## 5. Comment l’appli **détecte** (zéro LLM)

Un détecteur = une fonction **pure** : deux sacs (ou un sac + le
précédent) → `Event | null`. Pas d’HTTP, pas de chat. Les seuils
sont des **constantes nommées** dans `eventRules.js` (et miroir
Python si le serveur compare aussi), jamais dans `App.jsx`.

On compare **la même `kind`** : GFS avec GFS, atlas avec atlas,
RTOFS avec RTOFS. Interdit : « le vent a changé » parce qu’on a
collé le mois climatologique à côté du GRIB du jour.

### 5.1 Entrée / sortie de ZEE

**Source déjà là** : `dossier.zee.mrgid`, `zeeEnterEvent`.

| | Règle |
|---|---|
| Déclenche | `mrgid` **change** (y compris haute mer `null` → un id) |
| Premier fetch | `prevMrgid === undefined` → **pas** d’événement (déjà le cas) |
| Anti-spam | **1× par `mrgid`** et par voyage / jambe (`seenZee` Set) |
| Hystérésis | Si MarineRegions oscillait (bbox trop large, déjà filtré
`EEZ_ACCEPT_NM = 240`), on exige **2 sacs d’affilée** avec le
nouveau `mrgid` avant de parler |
| Lookahead (E2) | Première perle dont le `mrgid` ≠ `mrgid` bateau →
`zee-ahead` (`whenNm`) |
| Phrase locale | « On vient d’entrer dans {name}. » (déjà `eventSentence`) |

`zee.gold` dans le sac = flag **PoE dans le pack**, pas
`review.gold_on` (admin). Le public n’entend **pas** Review.

### 5.2 Changement vent / courant **significatif**

**Sources déjà là**

- Suivre : GRIB / Open-Meteo horaire (`speedKnots`, `dirFromDeg`,
  `rainMm`) + `weather.wind` / `weather.wave` du sac (`kind: forecast`).
- Simulation : `climatology.wind` / rose / `gale_pct` (`kind: climatology`).
- Courant : `weather.current` RTOFS (`speedKnots`, `dirToDeg`) ou
  atlas `current`.

| id | Seuil (constante) | Hystérésis / cooldown |
|---|---|---|
| `wind-shift` | ΔTWS ≥ **8 kt** **ou** ΔTWD ≥ **40°** (plus petit angle) | Reset seulement si Δ redescend sous **4 kt** et **20°**. Cooldown **15 nm** ou **30 min** d’horloge voyage |
| `wind-gale` | TWS ≥ **34 kt** (coup de vent) **ou** `gale_pct` atlas ≥ **15 %** sur **cette** perle | 1× tant que TWS reste ≥ 28 kt |
| `current-shift` | Δ vitesse ≥ **1,0 kn** **ou** inversion (≥ **120°** sur `dirToDeg`) | Cooldown 15 nm ; ignorer si les deux mesures sont `< 0,3 kn` |
| `hs-shift` | Hs (GFS-Wave) Δ ≥ **1,0 m** ou Hs ≥ **3,5 m** | Même cooldown 15 nm |

Le LLM **ne calcule pas** le nœud. Template : « Vent 18 kn / 240°
(`kind: forecast`, GFS) — +10 kn depuis 20 nm. »

### 5.3 Aire marine à visiter (AMP)

**Source déjà là** : `amp[]` (max 5, `visit_url`, `manager_url`,
`nm`, parfois `gold_on` pack).

| id | Déclenche | Anti-spam |
|---|---|---|
| `amp-enter` | Une AMP **entre** dans le rayon 30 nm (id / `site_id` nouveau) | Hystérésis **5 nm** : elle doit rester dans le sac sur le refetch suivant |
| `amp-ahead` | E2 : première perle où cette AMP apparaît, `whenNm` ≥ 5 | 1× par `site_id` et par jambe |
| Visitable | `visit_url` présent **et** ≠ page gestionnaire seule | Sinon événement **later** / phrase courte |

« À visiter » = il existe une URL skipper (`visit_url`). On ne
télécharge pas la page (Tavily = E5).

### 5.4 Marina de repli si pluie intense

**Pluie : déjà mesurée en Suivre**, pas encore dans `GET /ici`.

- GRIB officiel (`grib_fetch` / `saildocs`) : série horaire
  `rainMm` au point bateau.
- `fetch_weather_forecast` (sac `ici`) : vent + vague + RTOFS,
  **pas** `rain` aujourd’hui.

| | Règle |
|---|---|
| Pluie intense | `rainMm` ≥ **4 mm / h** sur **l’heure courante** **ou** cumul **≥ 10 mm** sur les **3 h** devant (GRIB) |
| `wx-alert` | Ce seuil **ou** `wind-gale` **ou** Hs ≥ 3,5 m |
| `marina-refuge` | `wx-alert` **et** marina / capitainerie / WPI à **< 25 nm** (`MARINA_REFUGE_NM`). 1× par alerte (même port), cooldown 6 h d’horloge |
| Choix du port | Le plus proche **sur le trait** (lookahead) ; à défaut le plus proche dans `nearby` |
| Simulation | **Pas** de `wx-alert` pluie, **pas** de `marina-refuge`. Pas de GRIB. On n’invente pas la pluie. On **n’ajoute pas** `rain` au `current` Open-Meteo du sac en E1 : ce `current` est `kind: forecast`, le film Simulation est `kind: climatology` — les mélanger mentirait. |
| Phrase (Suivre) | « Pluie 6 mm/h (GFS). Repli : {nom} à {n} nm. » — zéro LLM |

### 5.5 Autres événements utiles le long de la route

Tous partent des familles **déjà** dans le sac (voir `ici-tout.md`).

| id | Détection | Utile pourquoi |
|---|---|---|
| `zee-exit` | `mrgid` → `null` (haute mer) | Fin des formalités |
| `poe-ahead` | 1er PoE de **cette** ZEE dans `poe[]` ou lookahead | Groupé avec `zee-enter` |
| `cyclone-nearby` | `climatology.cyclone.nearby` ou croisements jambe | Alerte, `kind: climatology` + période / DOI |
| `depth-alert` | GEBCO `depthOffshore` trop faible **au large filtré** (déjà null près côte) **ou** EMODnet DTM `< 15 m` si présent | Catamaran, pas un sondage inventé |
| `escale-in` / `escale-out` | Horloge `holding` / 3 j à quai / `Go to next stop` | Le calendrier existe ; il manque l’événement |
| `science-hit` | Nouveau jeu dans `science.nearby` | Rarement parlé (juge `hide` en cinéma) |
| `grib-absent` | Suivre, `gribStatus !== "ready"` | Une phrase déjà prévue par U4 — pas un LLM |
| `satellite-scene` | Nouvelle `scene.id` Sentinel | Later ; `kind: observation` + date |
| `review-admin` | `review.reason=review_requires_admin` | **hide** pour le public ; debug admin seulement |

---

## 6. Agencer `ici()` : collecte / cache / préchauffe ≠ rédaction

Le film et le sac **ne s’arrêtent pas** pour un modèle.

```
Playhead (horloge)
    │
    ▼
A. COLLECTE   GET /ici + extras jambe     ← déjà là, gratuit, sync
    │         + iciAlong (E2)             ← cache perles
    ▼
B. RÈGLES     Δ sac → Event               ← CPU, < 1 ms, zéro réseau
    │
    ├─ phrase locale → Briefing tout de suite
    │
    ▼
C. FILE       (E4) pending / ready        ← arrière-plan
    │         Play continue
    ▼
D. JUGE       hide | now | later | group  ← règles (E3), pas Ultra
    │
    ▼
E. RÉDACTION  (E5 seulement) LLM sur le   ← petit JSON d’événement
              dossier déjà collecté
```

Règles d’agencement :

1. **`useIciDossier` ne `await` jamais un LLM.** Le commentaire
   actuel (« One step = one GET /ici. No chat, no Tavily. »)
   **reste vrai** jusqu’à E5, et même après E5 le hook ne bloque pas.
2. Collecte = HTTP **déjà** utilisés (MarineRegions, BI VPS,
   Open-Meteo, RTOFS, CDSE, EMODnet). Cache `_fc_cache` serveur
   (1 h) + debounce client.
3. Préchauffe = relancer **la même** collecte sur des perles
   **devant**, hors chemin Play.
4. Rédaction = lot E5. Si `pending` au passage du playhead : on
   **garde** le template. Play ne pause pas.
5. Interdit : `POST /polar/chat`, quatre agents, Search web monde.
6. Noms des mémoires et de la file : **§18**. Le Play tick
   n’y lit **jamais** une Promise LLM.

---

## 7. Juge d’affichage : hide / now / later / group

Un **seul** juge d’affichage, 100 % règles, lot **E3**.
Ce n’est **pas** Nemotron Ultra.

Entrées : `type`, `severity` (info / watch / alert), `novelty`
(déjà dit ?), `ageNm`, `whenNm`, vitesse du film (`playback.profile`),
cinéma on/off, clic skipper, `ready` ou seulement template.

| Verdict | Signifie | Exemples |
|---|---|---|
| `hide` | Rien à l’écran (ni phrase, ni pastille) | Doublon, cooldown, cinéma + `science-hit`, Review 401 public, `grib-absent` déjà en une ligne HUD |
| `now` | Remplace le Briefing **tout de suite** ; pastille pleine | `zee-enter`, `cyclone-nearby`, `marina-refuge`, `depth-alert`, `wind-gale`, `wx-alert` sévère |
| `later` | Phrase **pas** maintenant ; pastille creuse ou file « à venir » | `wind-shift` doux, `zee-exit`, `satellite-scene`, `amp-enter` sans `visit_url` |
| `group` | Attendre 1–3 copains, **un** digest | `poe-ahead` + `zee-enter` ; 2–3 AMP sur 30 nm ; **accéléré** Simulation (« depuis 80 nm : ZEE + 2 AMP ») |

### Immédiat ou plus tard ?

- **Immédiat (`now`)** si la sécurité ou la formalité change
  **maintenant** (ZEE, cyclone, repli pluie, haut-fond, coup de vent).
- **Plus tard seul (`later`)** si c’est utile mais pas urgent
  (rotation de 40° sans renforcement).
- **Plus tard groupé (`group`)** si plusieurs infos **du même
  endroit** (entrée de ZEE + PoE + AMP visitable) ou si le film
  va trop vite pour un flash par perle.

En **accéléré** : le juge **groupe plus**. Pas un flash par point.

Clic skipper sur une pastille : force `now` pour **cet** événement
(template, puis récit E5 s’il est `ready`).

**Juge de vérité (Ultra)** : uniquement lot E5, 1× par fiche Gold
**visible**, jamais sur un nœud de vent. Ce n’est pas ce juge.

---

## 8. Comment le LLM travaille (lot E5 seulement)

Pas avant E1–E4 recettables. **Aucun** nouveau fournisseur dans
E1–E4.

Le modèle ne « voit » pas la carte. Il reçoit un **petit JSON
d’événement**, découpé dans le sac **déjà** collecté :

```json
{
  "event": "zee-enter",
  "kind_notes": ["zee pack", "poe pack"],
  "zee": {"name": "France", "mrgid": 5677, "gold_pack": true},
  "poe": [{"name": "…", "nm": 12, "url": "…"}],
  "leg": {"from": "La Rochelle", "to": "Ajaccio"},
  "whenNm": 0,
  "tavily": null
}
```

Interdit dans ce JSON : grille polar, export projets, GeoJSON
route brut, tuiles, dump Review admin, catalogue Sentinel entier.

| Rôle | Quand (E5) | Travail |
|---|---|---|
| Récit court | Événement `now` / `group` **et** `ready` à raconter | 4–6 phrases à partir du JSON |
| Extraire **cette** URL | Gold pack + clic skipper + alerte | Une page officielle déjà dans le sac (`visit_url`, PoE) — **pas** une recherche monde |
| Vérité fiche | 1× par fiche visible | « Cette mention PoE est-elle encore sur la page ? » |

Le LLM **cite** `kind`, période, DOI, date de scène. Il n’invente
pas un vent, une pluie, ni un Gold admin.

Thinking OFF pour JSON / texte court. Un récit, pas quatre chats.

---

## 9. Présenter le long de la route

Même moteur d’événements. **Deux** mises en page. Vocabulaire
Suivre / Simulation du plan v2.

### 9.1 Simulation (film)

- **Panneau Briefing** (sidebar déjà branchée sur `iciBriefing`) =
  la carte parlée **maintenant** : dernier `now`, ou le digest
  `group`.
- **Pastilles sur la barre** du film, à `whenNm` (nm de l’événement
  sur `filmCum`). Pleine = `now` (ou `ready` E5). Creuse = `later`
  / `pending`.
- Clic pastille = cette carte. Play qui passe dessus : si `now`
  et texte `ready`, on remplace ; si `pending`, on **garde** le
  template.
- File visible **minimale** : « 2 récits en préparation » — pas un
  chat.
- Accéléré : digest, pas 20 flashs.
- Préchauffe **cette** jambe à l’ouverture / au recalcul. Route
  perso = les mêmes règles, sur **ce** trait (`waypointsFromCollection`
  + `flattenRoute`), pas le briefing Berry.

### 9.2 Suivre l’expédition

- Un bateau pour tout le monde. `t0` non éditable.
- **Pas** de pastilles sur 39 000 nm.
- À l’écran : événement **live** (`now`) + **au plus un** « à
  venir » (lookahead 24–48 h / prochaine perle météo ou AMP).
- Recalculer **absent**. Le trait officiel ne bouge pas.
- GRIB manquant : bateau + **une** ligne déjà prévue — pas un
  événement LLM.
- Aperçu barre : on peut regarder plus loin, le bateau live **ne
  recule pas** ; les pastilles aperçu restent `later` / `group`.
- **Pas** de replay des 39 000 nm. Le live n’a pas de « revenir
  voir la ZEE d’hier » dans E4.

Détail timeline / grouping / replay (Simulation) : **§20**.

### 9.3 Public vs debug

Plus de dump JSON « dossier cockpit » (U8). Le JSON reste pour
tests / Data Lab, pas pour le visiteur.

---

## 10. Catalogue + qui peut faire parler un LLM

Un **chiffre** ne passe **jamais** par un LLM. Vent, courant, Hs,
pluie, profondeur = template + `kind`.

« Faire parler les LLM » (E5) = **rédiger** le dossier, pas
détecter. Colonne **LLM E5** : oui seulement si le juge a laissé
passer `now` / `group` (parfois `later` si le skipper clique).

Liste **exhaustive** des ids (moteur + réservés). Colonne **Lot** :
E1 = détecté maintenant ; E2 = lookahead trait ; réservé = id
figé pour ne pas le « découvrir » plus tard ; juge = E3 sait déjà
les cacher / grouper.

| id | Déclencheur moteur | Seuil / hystérésis / cooldown | LLM E5 ? | Juge défaut | Lot |
|---|---|---|---|---|---|
| `zee-enter` | `mrgid` change | 1× / mrgid ; 2 sacs d’affilée | Oui, **cette** ZEE / PoE du sac | **now** | **E1** |
| `zee-ahead` | Lookahead E2 | 1× / mrgid ; `whenNm` | Optionnel, groupé | **group** | **E2** |
| `zee-exit` | `mrgid` → null | 1× par stretch haute mer | Non (phrase locale) | later | **E1** |
| `poe-ahead` | 1er PoE de cette ZEE | groupé avec `zee-enter` | Oui, URLs **du sac** | **group** | **E2** |
| `amp-enter` | AMP nouvelle dans 30 nm | 2 sacs / ~5 nm ; 1× / site | Oui **si** `visit_url` | now si visitable, sinon later | **E1** |
| `amp-ahead` | AMP **sur le trait** | 1× / site / jambe | Pareil | group / later | **E2** |
| `wind-shift` | ΔTWS ≥ 8 kt ou ΔTWD ≥ 40° | reset 4 kt / 20° ; 15 nm / 30 min | **Non** | later ; **now** si enchaîne `wind-gale` | **E1** |
| `wind-gale` | TWS ≥ 34 kt ou gale_pct ≥ 15 | 1× tant que ≥ 28 kt | **Non** (chiffre) | **now** | **E1** |
| `current-shift` | Δ ≥ 1 kn ou inversion 120° | 15 nm ; ignore < 0,3 kn | **Non** | later | **E1** |
| `hs-shift` | ΔHs ≥ 1 m ou Hs ≥ 3,5 m | 15 nm | **Non** | later ; now si ≥ 3,5 m | **E1** |
| `wx-alert` | **Suivre** : pluie ≥ 4 mm/h ou ≥ 10 mm / 3 h ; ou gale ; ou Hs. **Simulation** : gale / Hs seulement (`kind` climo), **pas** de pluie | 1× par seuil | Nano E5 **seulement** si marina utile | now si sévère | **E1** |
| `marina-refuge` | **Suivre-only.** `wx-alert` pluie **et** port < 25 nm | 1× / alerte / 6 h | Oui : nom + distance **du sac** | **now** | **E1** |
| `cyclone-nearby` | IBTrACS nearby / crossings jambe | 1× / trace / mois | Phrase + DOI ; récit court E5 ok | **now** | réservé |
| `depth-alert` | DTM / GEBCO trop peu (si le produit a répondu) | 2 nm | **Non** | now | **E1** |
| `science-hit` | 1 jeu local nouveau | suppress cinéma | **Non** | hide / later | réservé |
| `escale-in` / `escale-out` | horloge 3 j / holding | déjà calendrier | Court E5 ok | now | réservé |
| `grib-absent` | Suivre, pas de fichier du jour | 1 ligne HUD | **Non** | hide (déjà HUD) | réservé |
| `satellite-scene` | nouvel id L2A | 1× / id | **Non** (date + id) | later | réservé |
| `review-admin` | 401 fiche | — | **Non** | hide public | réservé |
| `aton-nearby` | nouveau jeu AtoN 30 nm | hide cinéma | **Non** | later | réservé |
| `anchorage-ahead` | mouillage OSM **sur le trait** | later | **Non** | later | réservé / E2 |
| `project-nearby` | nouveau projet BI | hide cinéma | **Non** | later | réservé |
| `cable-alert` | EMODnet `cables.nearby === true` | 1× / 2 nm | **Non** | **now** | réservé |
| `air-hop` | début saut `jump` / phase air | 1× / saut | **Non** | **now** | réservé |

Recette des règles = **fixture JSON** (deux sacs → liste
d’événements), pas un LLM.

---

## 11. Ordre de construction (lots)

Ordre demandé : **détecteurs → sac trajet → juge → rendu UI**.
Premier lot **sans** nouveau fournisseur LLM.

| Lot | Quoi | Recette (done) | LLM |
|---|---|---|---|
| **E1** Détecteurs | `eventRules.js` + tests. Étendre `zeeEnterEvent`. `wind-shift`, `current-shift`, `amp-enter`, `wx-alert` + `marina-refuge` **Suivre-only** (GRIB `rainMm`), `depth-alert`. Templates dans `iciBriefing`. Simulation : pas de pluie | Play / fixture : le briefing **change** à une entrée de ZEE et à un `wind-shift`. Suivre + `rainMm` ≥ 4 + port → `marina-refuge`. **Aucun** appel Token Factory / Tavily / NVIDIA | non |
| **E2** Sac trajet | `route` échantillonné + `iciAlong` sur **cette** jambe ; cache perles | « AMP dans 40 nm » sans refetch à chaque mètre ; Suivre : pas de préchauffe 39 000 nm | non |
| **E3** Juge | `displayJudge.js` : hide / now / later / group + hystérésis déjà posée en E1 | Accéléré → **un** digest ; doublon → hide | non |
| **E4** Rendu UI | Pastilles barre Simulation ; Suivre = live + 1 à venir ; file `pending` visible minimale | Pastille cliquable ; Play ne freeze pas ; U8 respecté | non |
| **E5** Fournisseurs **en dernier** | Nemotron / NVIDIA Token Factory / Tavily **sur le JSON d’événement déjà collecté** | 1 récit ZEE, 4–6 phrases, film non pausé ; Tavily = **cette** URL ; Ultra 1× / fiche | oui |

**v1.3 :** E1 + E3 **codés** (fixtures). E2 / E4 / E5 **pas**
commencés. E2 peut avancer sans toucher le Briefing. E4 a besoin
du juge (déjà là). E5 après E4 **et** une vraie fiche Gold, pas
un stub. NVIDIA / Tavily = **TODO dernier moment**, pas maintenant.

---

## 12. Fichiers

**Oui** (cibles, pas un dump) :

- `naviguide-simulator/src/engine/eventRules.js` (+ tests) — **E1 fait**
- `naviguide-simulator/src/engine/displayJudge.js` (+ tests) — **E3 fait**
- `naviguide-simulator/src/engine/iciBriefing.js` — templates E1 **faits**
- `naviguide-simulator/src/hooks/useIciDossier.js` — détecte + juge, **jamais** `await` LLM
- `naviguide-simulator/src/engine/ici.js` — extras trajet **E2**, pas la grille ; `zeeEnterEvent` **gardé**
- `naviguide-simulator/src/utils/sceneGate.js` — **ne pas** y mettre les détecteurs
- `naviguide-simulator/server/ici_engine.py` / `ici_layers.py` — pluie Open-Meteo **pas** en E1
- plus tard seulement : `server/` file récit / extract (E5)

**Non** : `naviguide/`, `frontend/`, `www`, `sync-from-atlas.sh`,
GRIB globe, 4 chats, chat polar, Ultra sur chaque Play, merge
sans ordre « merge ».

---

## 13. Recette avant E5

**v1.3 (E1 + E3) — fixtures, pas le film :**

1. Fixture entrée de ZEE (2 sacs d’affilée) → `zee-enter` + juge
   `now` + phrase « On vient d’entrer… ».
2. `wind-shift` fixture (même `kind`) → phrase chiffrée, **aucun**
   appel réseau LLM. Mélanger GFS et atlas → **aucun** événement.
3. Suivre + `rainMm` ≥ 4 + port dans le sac → `marina-refuge` +
   `now`. Sans port → `wx-alert` seul.
4. Accéléré (`profile === "fast"`) + 2 `later` dans 80 nm → **un**
   digest `group`.
5. Simulation + fixture pluie : **aucun** `marina-refuge`.
6. `www` et `blueintelligence.online` inchangés.
7. Horloge officielle toujours `2026-05-15T08:00Z`.
8. `useIciDossier` : debounce 800 ms / 3 nm / 8 s **inchangé** ;
   zéro `await` chat.

**Encore E2 / E4 :**

9. Suivre : pas de préchauffage 39 000 nm (E2).
10. Seek / rewind sur **cette** jambe (E4) : pas de nouvel appel
    LLM ; les pastilles déjà calculées restent (§20).

---

## 14. Hors scope (ce plan)

Isochrone des 39 000 nm. Overlay climatologie opérateur BI.
Data Lab / Sandbox Nebius (stretch **après** E5). AIS / Iridium
du vrai bateau. Merger #139 Hs. Allumer Token Factory « pour voir ».
**Concevoir** Nemotron / Tavily (prompts, modèles, quotas) —
TODO **dernier moment**, lot E5 uniquement.
E2 / E4 / E5 (pas ce tour).
Ajouter `rain` Open-Meteo dans `GET /ici` (hors scope E1–E4).

---

## 15. Risques

| Risque | Parade |
|---|---|
| Attendre un LLM avant d’ouvrir la scène | Phrase locale d’abord ; `sceneGate` reste une porte **peinture** |
| Tavily / NVIDIA à chaque frame | Interdit avant E5 ; après E5 hors ZEE Gold / clic / alerte |
| Ultra = juge d’affichage | Deux juges ; Ultra seulement vérité fiche (E5) |
| Lookahead = dump monde | 1 point / 10–15 nm, **cette** jambe ; Suivre 24–48 h |
| LLM qui invente un vent / une pluie | Template + `kind` ; climatologie citée |
| Mélanger GFS et vent du mois | Détecteurs **même kind** |
| 4 chats « le temps que ça arrive » | Le Briefing **est** l’emplacement |
| Atlas écrase le VPS | Ne **jamais** lancer `sync-from-atlas.sh` |
| Review 401 lu comme « pas de ZEE » | `review.reason` honnête ; juge `hide` public |
| Pluie absente du sac `ici` | **Suivre** = GRIB `rainMm` déjà là. **Simulation** = pas d’événement pluie (pas d’invention, pas d’Open-Meteo rain en E1) |
| Seek qui relance le monde | Replay = **rejouer la liste** déjà calculée, pas un nouveau `GET /ici` à chaque clic |
| File qui bloque Play | Play lit seulement `EventRecord.phrase` ; `StoryJob` est à côté (§18) |

---

## 16. Conscience du trajet GPS **déjà planifié**

Aujourd’hui `GET /ici` ne voit que le **point** bateau. Le playhead,
lui, a déjà le trait : `flattenRoute` → `points[]` avec `lat`,
`lon`, `cumNm`, `filmCum`, `jump`, `nonMaritime`.

« Conscience du trajet » = les détecteurs lisent **cette**
polyligne, pas « tout ce qui est dans 30 nm autour du bateau dans
n’importe quelle direction ».

### 16.1 Ce qu’on sait déjà (sans nouvel instrument)

| Déjà dans le code | Sert à |
|---|---|
| `flattenRoute` (`routePlayhead.js`) | Le GPS planifié (officiel **ou** perso Simulation) |
| `chapterAtNm` / `destMark` | Prochaine escale Bmap = fin de jambe |
| `jambe` + `marks.kind = "leg"` | De / vers / phase / véhicule |
| `AIR_JUMP_NM` + `jump` / `nonMaritime` | Transfert aérien : **pas** d’événements mer |
| `useIciDossier` + `dest_lat` / `dest_lon` | Croisements IBTrACS **de la jambe**, déjà |

On n’ajoute **pas** un traceur GPS. On n’écoute **pas** Iridium.

### 16.2 Comment on « voit devant » sur le trait

1. Prendre les points `flattenRoute` de **cette** jambe seulement
   (de l’escale courante jusqu’à la suivante).
2. Trouver l’index bateau par `cumNm` (snap déjà fait).
3. Avancer sur la polyligne jusqu’à la prochaine escale **ou**
   le plafond Suivre (24–48 h de mer), pas plus.
4. Poser une perle tous les **10–15 nm** (`ROUTE_SAMPLE_NM`).
5. Sauter les vertex `jump` / `nonMaritime` / phase avion : pas
   de ZEE, pas d’AMP, pas de marina sur un saut aérien.
6. Chaque perle = mini-sac (ZEE `mrgid`, AMP 15 nm, marina / WPI
   25 nm). Vent / RTOFS / Sentinel : **bateau + 1 ou 2 perles
   météo**, pas toutes.
7. `whenNm` = `perle.cumNm − bateau.cumNm`. Pastille = `filmCum`
   de la perle (la barre utilise déjà `filmCum`, pas `cumNm`, à
   cause des sauts avion).

« AMP à visiter dans 40 nm » = la première perle **sur le trait**
où cette AMP apparaît, pas une AMP à 12 nm sur le côté si le
bateau ne s’en approche pas.

« Marina de repli » = d’abord la plus proche **sur le trait**
(lookahead) ; à défaut la plus proche dans `nearby` du sac point
(le skipper peut rentrer au port le plus proche, même un peu
hors trait). **Suivre seulement** (pluie GRIB).

### 16.3 Suivre vs Simulation (même moteur, deux plafonds)

| | Suivre | Simulation |
|---|---|---|
| Trait | Officiel Berry, **figé** | Officiel **ou** perso (`waypointsFromCollection` + `flattenRoute`) |
| Lookahead | Maintenant + **24–48 h** de mer | **Cette** jambe, jusqu’à la prochaine escale |
| Préchauffe | Interdit sur 39 000 nm | Au chargement / recalcul de **cette** jambe |
| Météo Δ | GRIB / Open-Meteo `forecast` vs `forecast` | Atlas / zone `climatology` vs `climatology` |
| Pluie / repli | Oui (`rainMm`) | Non |
| Replay | Non (live + 1 « à venir ») | Oui, **cette** session / **cette** jambe (§20) |

---

## 17. Catalogue : qui peut faire parler un LLM, et quand

Le tableau §10 reste la liste des ids. Ici : **qui vit où**, et
les familles du sac **pas encore** dans §10.

Un **chiffre** ne passe **jamais** par un LLM. « Faire parler »
(E5) = rédiger le dossier **déjà** collecté, si le juge a dit
`now` / `group` (ou `later` + clic skipper).

### 17.1 Suivre vs Simulation par famille

| id | Suivre | Simulation | LLM E5 ? |
|---|---|---|---|
| `zee-enter` / `zee-ahead` / `zee-exit` | oui | oui (climo n’y change rien) | enter / ahead oui ; exit non |
| `poe-ahead` | oui | oui | oui, URLs **du sac** |
| `amp-enter` / `amp-ahead` | oui | oui | oui **si** `visit_url` |
| `wind-shift` / `wind-gale` | GRIB / GFS `forecast` | atlas `climatology` (TWS / rose / `gale_pct`) | **non** |
| `current-shift` | RTOFS `forecast` | atlas courant `climatology` | **non** |
| `hs-shift` | GFS-Wave `forecast` | Hs P50/P90 atlas `climatology` | **non** |
| `wx-alert` pluie | oui (`rainMm`) | **non** | non (chiffre) |
| `marina-refuge` | oui | **non** | oui : nom + nm **du sac** |
| `cyclone-nearby` | atlas + crossings jambe | pareil | phrase + DOI ; récit court ok |
| `depth-alert` | GEBCO / EMODnet si répondu | pareil | **non** |
| `escale-in` / `escale-out` | 3 j à quai (calendrier) | pareil + Stop auto | court ok |
| `grib-absent` | oui (déjà HUD) | sans objet | **non** |
| `satellite-scene` | oui (`kind: observation`) | oui (même catalogue) | **non** |
| `review-admin` | hide public | hide public | **non** |

Comparer **la même `kind`**. Interdit : « le vent a changé » parce
qu’on a collé le mois climatologique à côté du GRIB du jour.

### 17.2 Familles déjà dans le sac, pas des flashs

Déjà racontées par `narrateIci` (une phrase par famille). On ne
crée un événement **que** s’il y a un **changement** utile.

| Famille sac | Événement ? | Juge |
|---|---|---|
| AtoN (NOAA / OSM) | `aton-nearby` seulement si **nouveau** jeu dans 30 nm | later ; hide cinéma |
| Mouillages OSM | `anchorage-ahead` si perle sur le trait | later |
| Projets BI | `project-nearby` | hide cinéma ; later sinon |
| Câble EMODnet `nearby === true` | `cable-alert` | **now** (une fois, 2 nm) |
| Polar / nœuds / ETA | **non** — déjà `legSentence` | — |
| Review Gold 401 | `review-admin` déjà hide | hide public |
| Dérivés satellite `not_generated` | **non** — `null` + `reason` dans le briefing | — |
| Atlas `unavailable` → zone fallback | **non** — phrase `kind` déjà là | — |
| Saut avion (`jump` / phase air) | `air-hop` au **début** du saut | **now** (le bateau reste à quai — phrase déjà dans `legSentence`) |

E1 n’implémente **pas** AtoN / mouillage / projet / câble / air.
Ces ids sont réservés pour ne pas les « découvrir » plus tard.
Lot E1 = ZEE, vent/courant, AMP, wx/marina Suivre, depth.

### 17.3 Anti-spam (rappel, constantes nommées)

À poser dans `eventRules.js`, **pas** dans `App.jsx` :

- `ROUTE_SAMPLE_NM = 12`
- `WIND_SHIFT_KT = 8`, `WIND_SHIFT_DEG = 40`, reset 4 kt / 20°
- `COOLDOWN_NM = 15`, `COOLDOWN_MIN = 30` (horloge voyage)
- `GALE_KT = 34`, hold 28 kt ; `GALE_PCT = 15` (atlas)
- `CURRENT_SHIFT_KN = 1.0`, ignore `< 0.3 kn`, inversion 120°
- `HS_SHIFT_M = 1.0`, `HS_ALERT_M = 3.5`
- `AMP_HYSTERESIS_NM = 5`
- `RAIN_MM_H = 4`, `RAIN_3H_MM = 10`
- `MARINA_REFUGE_NM = 25`, cooldown 6 h
- `DEPTH_ALERT_M = 15` (EMODnet si présent)
- `GROUP_NM = 15` (normal) / `80` (`profile === "fast"`)
- `GROUP_WALL_MS = 8000`

1× par `mrgid` / `site_id` / alerte **et par jambe** (`seen*` Set).
Changer de jambe ou de trait perso → on **vide** les `seen*`.

---

## 18. Architecture : collecte / snapshot / sac 30 nm / file

Le film **n’a pas le droit** d’attendre un modèle. Quatre objets
en mémoire **client** (pas Mongo, pas Atlas) :

| Nom | Quoi | Qui le remplit | Play attend ? |
|---|---|---|---|
| **Sac point** `IciSnapshot` | `GET /ici` ~30 nm au bateau | `useIciDossier` déjà | Non (debounce 800 ms / 3 nm / 8 s) |
| **Snapshot Δ** | Les **2** derniers sacs (hystérésis) | refs du hook | Non |
| **Sac trajet** `AlongIndex` | Perles de **cette** jambe | E2 `iciAlong` + cache | Non (préchauffe hors Play) |
| **Liste** `EventRecord[]` | Événements déjà détectés | règles E1, sync, < 1 ms | Non |
| **File** `StoryJob` | Rédaction E5 **seulement** | file async | **Non** — Play ignore `pending` |

Jusqu’à E4 inclus, `StoryJob` **n’existe pas**. Le statut d’un
événement est toujours `template` (phrase locale). La file est
une **prise** : on la câble en E4 (états `pending` visibles) et
on y branche un fournisseur en E5.

### 18.1 Ce que Play fait à chaque tick

```
horloge / seek
    → position bateau (déjà là)
    → si déplacement ≥ 3 nm : programmer GET /ici (debounce)
    → règles pures (at, prev, along) → 0..n EventRecord
    → juge → hide | now | later | group
    → Briefing = template du now / digest
    → pastilles = EventRecord visibles
    → (E5) si now/group et pas encore de job : enqueue
    → si StoryJob.ready : remplacer le texte ; sinon garder template
```

Aucun `await` chat dans ce chemin. Si la collecte `GET /ici` est
lente : on garde le **dernier** sac ; le bateau continue. Timeout
déjà 40 s. Échec : sac vide + `sources` honnêtes (déjà le cas).

### 18.2 Forme des objets (contrat, pas du code)

`EventRecord` :

- `id` (uuid court), `type`, `severity` (`info` / `watch` / `alert`)
- `whenNm`, `filmCum` (pastille)
- `legId` (from→to)
- `snapshotRef` (pointeur vers le sac **déjà** là, pas une copie globe)
- `phrase` (template, tout de suite)
- `story` : `{ status: "template" }` jusqu’à E5 ; puis
  `pending` / `ready` / `failed`
- `judge` : dernier verdict

`StoryJob` (E5 seulement) :

- `eventId`, `payload` = **petit JSON d’événement** (§8 / §19)
- `status`, `text` optionnel
- **max 3** jobs `pending`. Si trop : on jette le plus vieux
  `later`. On **ne jette pas** `marina-refuge`, `cyclone-nearby`,
  `depth-alert`, `wind-gale`.

Interdit dans ces objets : grille polar, GeoJSON route brut,
catalogue Sentinel entier, dump Review admin, tuiles.

### 18.3 Où ça vit

- E1–E4 : mémoire de l’onglet. Fermer l’onglet = tout oublié.
- Pas d’écriture Mongo. Le VPS sert déjà `GET /ici` + couches.
- E5 pourra poser la file côté `server/` **sans** bloquer le
  client : le client n’envoie le JSON **que** si le juge a dit
  oui, et il n’attend pas la réponse pour Play.

---

## 19. Comment un LLM travaillera (plus tard) sur ce qui est **déjà** là

Pas avant E1–E4 recettables. **Aucun** fournisseur à choisir
maintenant (§22).

Le modèle ne voit **pas** la carte. Il reçoit le JSON **découpé**
dans le sac / l’événement **déjà** collecté. Les `null` restent
des `null`.

Exemple (contrat, pas un prompt) :

```json
{
  "event": "zee-enter",
  "kind_notes": ["zee pack", "poe pack"],
  "zee": {"name": "France", "mrgid": 5677, "gold_pack": true},
  "poe": [{"name": "…", "nm": 12, "url": "…"}],
  "amp": [],
  "leg": {"from": "La Rochelle", "to": "Ajaccio"},
  "whenNm": 0,
  "weather": null,
  "weather_reason": "not_in_this_event",
  "rain": null,
  "rain_reason": "suivre_grib_absent_or_simulation",
  "tavily": null,
  "nvidia": null
}
```

Règles **null honnêtes** (à stocker dès E1, pour ne pas mentir
plus tard) :

1. Champ absent du sac → `null` + `reason` copiée du sac
   (`openmeteo_unavailable:*`, `no_scene_in_bbox`,
   `review_requires_admin`, `rtofs_unavailable:*`, …).
2. Champ hors sujet pour **cet** événement → `null` +
   `not_in_this_event` (on n’envoie pas tout le sac « au cas où »).
3. Interdit de remplir un `null` par un modèle, une moyenne, ou
   « probablement ».
4. `tavily` et `nvidia` restent `null` jusqu’à E5. Même en E5,
   Tavily = **cette** URL déjà dans le sac, pas une recherche
   monde.
5. Le LLM **cite** `kind`, période, DOI, date de scène. Il
   n’invente ni vent, ni pluie, ni `gold_on` admin.

Thinking OFF pour JSON / texte court. Un récit, pas quatre chats.

---

## 20. Timeline, grouping, replay (surtout Simulation)

### 20.1 Timeline

Source de vérité = `EventRecord[]` de **cette** jambe, indexée
par `filmCum`.

À l’écran (E4, pas E1) :

- **Barre du film** (`SimulationFilmBar`) : pastilles aux
  `filmCum`. Pleine = `now` (ou récit `ready`). Creuse = `later`
  / `pending`. Les escales Bmap sont déjà des `marks` : on
  **ajoute** des marques événement, on ne refait pas la barre.
- **Briefing** (sidebar déjà branchée sur `iciBriefing`) : la
  carte **maintenant** (dernier `now` ou digest `group`).
- **Liste compacte** sous cette carte : « le long de cette
  jambe », groupée par seau de nm. **Pas** un 3ᵉ panneau.

Pas de dump JSON public (U8).

### 20.2 Grouping (quand on fusionne)

Fenêtre : **15 nm** (`GROUP_NM`) **ou** 8 s d’horloge murale
(`GROUP_WALL_MS`), le plus large. En `profile === "fast"` :
**80 nm**.

| On groupe ensemble | On ne groupe **jamais** avec le reste |
|---|---|
| `zee-enter` + `poe-ahead` + `amp-ahead` (formalités du même endroit) | `marina-refuge` |
| 2–3 `amp-ahead` dans la fenêtre | `cyclone-nearby` |
| `wind-shift` doux + `current-shift` (digest météo) | `depth-alert` |
| Accéléré : tout ce qui est `later` dans 80 nm → **un** digest | `wind-gale` / `wx-alert` sévère |

Un digest = **une** carte Briefing, **une** pastille pleine à
l’`filmCum` du premier de la grappe. Les autres ids restent
dans le JSON du digest pour E5, pas comme 3 flashs.

### 20.3 Replay (Simulation seulement)

**Replay** = le skipper **revient** sur un moment **déjà** joué
de **cette** jambe, dans **cette** session. Ce n’est pas
recharger Berry, ni Mongo.

| Action | Comportement |
|---|---|
| Clic sur la barre (seek, déjà là) | Playhead bouge. **Pas** de nouveau `GET /ici` si < 3 nm du sac déjà là. **Pas** d’appel LLM. |
| Seek **en arrière** | Les `EventRecord` restent. On **ne** re-flash **pas** les `now` déjà vus. Briefing = événement de **ce** `filmCum` si le skipper est en pause + clic pastille ; sinon on laisse la dernière carte. |
| Seek **en avant** au-delà d’un `later` | Au passage du playhead, le juge peut promouvoir `later` → `now` **une** fois. |
| Rejouer toute la jambe (seek 0 + Play) | `seen*` **gardés** pour cette jambe : pas de 2ᵉ `zee-enter` spam. Pastilles déjà là. Clic skipper = force `now` (template, puis récit s’il est `ready`). |
| Nouvelle jambe **ou** nouveau trait perso | On **vide** `EventRecord`, `seen*`, `AlongIndex`. On recommence. |
| Recalculer une jambe | Comme un nouveau trait : reset. |
| Onglet fermé | Tout oublié (mémoire client). |

Suivre : **pas** de replay. Aperçu plus loin = pastilles `later`,
le bateau live **ne recule pas** (déjà le plan U).

---

## 21. Juge : afficher / ne pas afficher, puis quand

Un seul juge, 100 % règles, lot **E3**. Ce n’est **pas**
Nemotron Ultra.

Arbre, dans cet ordre :

1. **Ne pas afficher (`hide`)** si *un* de ces cas :
   - doublon / déjà dans `seen*` pour cette jambe ;
   - encore dans le cooldown (nm ou minutes) ;
   - cinéma **et** famille bavarde (`science-hit`, `aton-nearby`,
     `project-nearby`) ;
   - `review-admin` (public) ;
   - `grib-absent` (déjà **une** ligne HUD) ;
   - produit `null` sans changement (ce n’est pas un événement).
2. Sinon, **le skipper a cliqué** cette pastille ? → **`now`**
   (template tout de suite ; récit E5 s’il est `ready`).
3. Sinon, **sécurité ou formalité maintenant** ? → **`now`** :
   `zee-enter`, `cyclone-nearby`, `marina-refuge`, `depth-alert`,
   `cable-alert`, `wind-gale`, `wx-alert` sévère, `escale-in` /
   `escale-out`, `air-hop`.
4. Sinon, **1 à 3 copains** dans la fenêtre de groupe (§20.2) ?
   → **`group`** (un digest, pas trois flashs).
5. Sinon → **`later`** (pastille creuse, file « à venir »).
6. `profile === "fast"` : si ≥ 2 événements dans 80 nm, forcer
   **`group`** même s’ils auraient été `later`.

Donc : la question « on montre ? » est le **`hide`**. Si on
montre, « tout de suite » = `now` ; « plus tard avec d’autres »
= `group` ; « plus tard tout seul » = `later`.

**Juge de vérité (Ultra)** : uniquement E5, 1× par fiche Gold
**visible**. Ce n’est pas ce juge. On ne le conçoit pas ici.

---

## 22. LLM : cascade habituelle — **branchée** (v1.5)

Cascade **déjà dans** `backend/app/core/llm.py` /
`nvidia.py` / `claude.py`, recopiée en mince dans
`naviguide-simulator/server/story_cascade.py` (atelier seulement,
prod BI intouchée) :

1. **NIM** (`integrate.api.nvidia.com`, `NVIDIA_API_KEY`) — texte
   court, thinking OFF. Premier essai si pas de page à lire.
2. **OpenRouter** — repli ; **`:online` seulement** s’il faut une
   page **déjà dans le sac** (`visit_url` / PoE) + Gold / clic /
   alerte. NIM n’a pas de search.
3. **Claude** — dernier filet.

**Pas** Nemotron. **Pas** NVIDIA Token Factory. **Pas** Tavily
(recherche monde). `enqueueStory` envoie le **petit JSON déjà
collecté** à `POST /ici/story` en arrière-plan. `useIciDossier`
n’`await` **jamais**.

`tavily: null` toujours. `nvidia` reste `null` tant que le récit
n’est pas `ready` (ce n’est pas « on appelle NIM à chaque frame »).

---

## 23. Prochaines étapes (après v1.5)

**Fait :** E1 + E3 (v1.3), E2 + E4 (v1.4), E5 cascade habituelle
(v1.5, §26).

**Pas encore :** Tavily monde, Nemotron, Token Factory, juge
Ultra 1× / fiche Gold.

Pas de merge sans le mot « merge ». Prod `www` et
`blueintelligence.online` intouchées.

---

## 24. v1.3 — contrat + ce qui est codé

### 24.1 Contrat (comment ça s’agence, sans bloquer l’UI)

```
Playhead (horloge)  ──►  A. COLLECTE   GET /ici  (debounce 800 ms /
                         déjà là                 3 nm / mini 8 s /
                                                 timeout 40 s)
                              │
                              ▼
                         B. RÈGLES     detectEvents(at, prev, along,
                         CPU < 1 ms    ctx, memory)  → EventRecord[]
                              │
                              ▼
                         C. JUGE       judgeEvents(...) →
                         hide|now|     hide | now | later | group
                         later|group
                              │
                              ▼
                         D. BRIEFING   phrase locale tout de suite
                         sidebar       (template). Play continue.
                              │
                              ▼
                         E. E4/E5      pastilles + file pending
                                       + enqueueStory fire-and-forget
```

Règles **non négociables** :

1. `useIciDossier` **ne `await` jamais** un LLM. Le commentaire
   « One step = one GET /ici. No chat, no Tavily. » **reste vrai**.
2. Si `GET /ici` est lent / timeout : on **garde le dernier sac** ;
   le bateau et le film continuent.
3. Le LLM (E5) ne voit **que** le petit JSON d’événement découpé
   dans le dossier **déjà** collecté. `tavily: null` toujours.
   `nvidia` = moteur seulement si `ready`.
4. Conscience du trajet = la polyligne `flattenRoute` de **cette**
   jambe (E2). En E1, `along` est `null` : on détecte au **point**
   + extras GRIB Suivre. Les ids `*-ahead` attendent E2.
5. Simulation / Suivre : **même** moteur. Pluie / marina = Suivre
   seulement. Vent : comparer **la même `kind`**.
6. Présentation le long de la route : E4 = pastilles sur
   `SimulationFilmBar` à `filmCum` + digest Briefing. Ce tour :
   le Briefing **change** (phrase `now` / digest). Pas de pastilles.

### 24.2 Fichiers v1.3

| Fichier | Rôle |
|---|---|
| `src/engine/eventRules.js` | Constantes + `detectEvents` + `sumRainHours` |
| `src/engine/eventRules.test.js` | Fixtures deux sacs → événements |
| `src/engine/displayJudge.js` | `judgeEvents` : hide / now / later / group |
| `src/engine/displayJudge.test.js` | Accéléré, doublon, skipper, marina jamais groupée |
| `src/engine/iciBriefing.js` | `phraseForEvent` FR/EN, `kind` cité |
| `src/hooks/useIciDossier.js` | Sac + Δ + mémoire jambe + juge ; **pas** de chat |
| `src/App.jsx` | Passe `mode`, GRIB `rainMm`, cinéma, profil, nm |

`zeeEnterEvent` dans `ici.js` **reste** (tests existants).
`sceneGate.js` **intouché**.

### 24.3 TODO dernier moment

- [x] `iciAlong` / perles 10–15 nm — **E2** (v1.4)
- [x] Pastilles barre + replay — **E4** (v1.4)
- [x] `enqueueStory` → cascade NIM → OR ± `:online` → Claude — **E5** (v1.5)
- [ ] Tavily / Nemotron / Token Factory — **hors scope**

---

## 25. v1.4 — `iciAlong` + pastilles + cascade

### 25.1 Conscience du trajet (E2)

- Perles tous les `ROUTE_SAMPLE_NM` (12) sur `flattenRoute` de
  **cette** jambe (de l’escale courante à la suivante).
- Saut `jump` / `nonMaritime` : pas de perle mer.
- `GET /ici?thin=1` : ZEE + PoE + AMP (15 nm) + ports (25 nm).
  Pas de vent / Sentinel / Review / climo à chaque perle.
- Cache `arrondi(lat, 2)` + `arrondi(lon, 2)` + `month`.
- **Simulation** : préchauffe **cette** jambe, max 60 perles.
- **Suivre** : 36 h × nœuds (plafond ~350 nm), max 24 perles.
  **Interdit** de préchauffer 39 000 nm.
- Détecteurs `zee-ahead` / `amp-ahead` (`whenNm` ≥ 5) /
  `poe-ahead` : première perle **sur le trait**, pas « dans
  30 nm sur le côté ».
- `along` nourrit aussi le choix de marina de repli (port le
  plus proche **sur le trait**, puis `nearby`).

### 25.2 Pastilles (E4)

- Simulation : pastilles sur `SimulationFilmBar` à `filmCum`.
  Pleine = `now`. Creuse = `later` / `pending`.
- Clic = seek (Simulation) + juge `now` (template).
- Seek arrière : pas de 2ᵉ flash ; ledger **gardé**.
- Seek avant au-delà d’un `later` : promotion `later` → `now`
  **une** fois.
- Suivre : **pas** 39 000 pastilles — live + **au plus une**
  « à venir ».
- File : « N récits en préparation » seulement si `story.status
  === pending`. En v1.4 tout est `template` → rien.

### 25.3 Cascade LLM (réponse « c’est possible ? »)

| | v1.4 | v1.5 E5 |
|---|---|---|
| Phrase / pastille | template local | + récit si `ready` |
| Fournisseur | aucun appel | **NIM → OR ± `:online` → Claude** |
| Play | n’attend pas | n’attend pas |
| Tavily / Nemotron / Token Factory | non | non |

---

## 26. v1.5 — `enqueueStory` branché, film non bloqué

- Client : `enqueueStory` rend `pending` **tout de suite**,
  `fetch POST /ici/story` en arrière-plan. Max 3 `pending` ;
  on jette le plus vieux `later`, jamais `marina-refuge` /
  `cyclone-nearby` / `depth-alert` / `wind-gale`.
- Serveur : `story_cascade.py` — NIM texte court, sinon OR
  (suffixe `:online` seulement si `needPage` + URL du sac),
  sinon Claude. Échec = `failed`, le template reste.
- `useIciDossier` n’`await` pas. Phrase locale tant que
  `pending` / `failed`. Si `ready` : le Briefing prend `story.text`.
- `tavily: null`. Pas de Nemotron. Pas de `POST /polar/chat`.


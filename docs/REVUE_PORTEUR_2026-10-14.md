# Revue du porteur — 14 octobre 2026 (application sur la tête de pile #444, 28 lots)

Revue orale du porteur, réorganisée par le chat de pilotage. Jugement global : « c'est vraiment pas mal » ;
le film de Revoir est « beaucoup plus fluide, enrichi, intéressant ». Ce document sépare ce qui est **décidé**
(→ lots du batch 2, `docs/PLAN_BATCH_2026-10-14.md`), ce qui est **demandé en réflexion** (§ 4 : pas de
décision, des options) et ce qui est **à trancher** (§ 5 : RC27, RG11).

## 1. Constats — décidés, à corriger

### A. Accueil et cadrage
- **A1.** À l'ouverture (Suivre), la carte est centrée sur le point de départ en France. Attendu : **le bateau au
  milieu de la carte**, carte **entièrement dézoomée** (vue monde centrée sur le bateau).
- **A2.** Tracer → Suivre : la caméra zoome trop sur le bateau (Polynésie). Attendu : même règle qu'A1 — bateau
  au centre, monde dézoomé.

### B. Le passage Tracer → Suivre ne tient pas sa promesse
- **B1.** Tracer votre propre route (La Rochelle → Caraïbes) → Terminer → **Suivre l'expédition** : l'application
  remet la route Berry-Mappemonde. Attendu : Suivre s'ouvre sur **la route que je viens de tracer**, et seulement
  elle.
- **B2.** Dans cet état, **deux routes** sont dessinées (la mienne et celle de Berry). Attendu : une seule à la
  fois ; on passe de l'une à l'autre par les pilules **Berry-Mappemonde | route personnalisée** de l'encadré gauche.
- **B3.** Dans cet état, la route Berry **déjà parcourue** est tracée mais **la route à venir ne l'est plus**.
- **B4.** Principe : il y a « un problème de switch » entre les deux modes. Suivre doit pouvoir suivre la route
  Berry **ou** la route personnalisée ; Tracer doit pouvoir montrer la route Berry **ou** le brouillon en cours.

### C. Le mode Tracer : défaut et navigation
- **C1.** À l'arrivée en Tracer, être **par défaut en « Tracer votre propre route »** (le dessin), pas sur la route
  Berry affichée.
- **C2.** La pilule **Berry-Mappemonde** ramène directement à la route Berry — **sans Annuler**, et **sans perdre le
  brouillon** : on doit pouvoir faire Berry → « Tracer votre propre route » et retrouver son tracé en cours.
  **Confirmé par le porteur le 14 oct. au soir** : la pilule Berry affiche la route Berry et garde le brouillon ;
  Annuler reste l'abandon explicite. → DM6.
- **C3.** Dans Tracer, la route Berry est **de l'affichage** : une vitrine de ce qu'on peut faire avec « Tracer votre
  propre route » (un tour du monde, une transat, l'océan Indien). Importer une route existante préfigure aussi
  Tracer. Les deux restent.
- **C4.** En Tracer, la **lecture** (Play) reste — c'est « simuler » — mais **part toujours d'aujourd'hui**, le jour
  où l'utilisateur se connecte. Régler une date de départ antérieure = rejouer l'expédition = Suivre.
  (Observé : horloge au 20 octobre après une lecture ; « repartir au début » → 14 octobre : normal.)
- **C5.** En Tracer sur la route Berry (bateau à Saint-Maur), l'encadré gauche affiche **la fiche d'escale de
  Papeete** : le moteur prend la position de Suivre. Au mieux : la prochaine escale du tracé (La Rochelle).

### D. Barre de mentions légales (Leaflet | Tuiles © Esri — HERE, Garmin, © OSM)
- **D1.** Elle entre en conflit / chevauchement avec la barre film. Attendu : positionnée **relativement à la barre
  film**, toujours juste au-dessus, avec un tout petit espace — pas en dur.
- **D2.** **Même hauteur que les boutons de zoom** (aujourd'hui les boutons sont plus hauts) : rapetisser les
  boutons ou grandir la barre, mais exactement la même hauteur (capture du porteur).

### E. Le film (Revoir) — bien meilleur, quelques défauts
- **E1.** **Coupures** à la fin de certaines escales : le texte dit est coupé ; la clôture finit sur « Aujourd'hui,
  le » (transcription du porteur).
- **E2.** Toujours de petits **décalages** entre la parole et la position du bateau.
- **E3.** **Chronologie** : des événements paraissent avant d'autres qui les précèdent logiquement. Exemple dans la
  transcription : « Le 19 mai, au nord de Gibraltar, le mistral s'installe, 16 nœuds de saison » puis « Le
  lendemain, les eaux portugaises » puis « le détroit de Gibraltar ». Ordre attendu depuis La Rochelle : eaux
  françaises → golfe de Gascogne → eaux espagnoles → eaux portugaises → détroit de Gibraltar → eaux marocaines.
  Autres incohérences relevées dans la même transcription : « Cayenne, cap au nord pour Papeete » ; « la route
  passe par Caraïbes Ouest, Atlantique Nord » à l'arrivée à **Papeete** ; « les eaux de Saint-Martin, puis celles
  de Saint-Martin » ; six « un flotteur Argo » sans nom ni lieu ; « HS 33 m » (3,3 m ?).
- **E4 (ajout du soir).** L'épisode **Caraïbes → Cayenne (bateau 1) → vol → Halifax → bateau 2 → Saint-Pierre-et-Miquelon →
  bateau 2 → Halifax → vol → Cayenne → bateau 1 → Polynésie** n'est pas raconté comme il s'est passé : une seule phrase
  (« l'équipage s'envole de Cayenne pour Saint-Pierre-et-Miquelon ; le bateau attend »), destination du vol fausse, les
  deux traversées du second bateau absentes. → **RC31**.
- **E5 (ajout du soir).** Les noms de lieux en langue d'origine (Saint-Martin / Sint Maarten, Sint Eustatius…) posent
  problème : il faut une règle (exonymes de la langue du récit pour les pays et eaux, nom d'origine pour les ports et
  aires, homonymes distingués). → **RC32**.
- **B3 (rappel du soir).** La route Berry à venir ne s'affiche pas après Tracer → tracer → Suivre : dans DM5 (étape 3,
  test de contrôleur qui rejoue la séquence).

### F. Dependabot et pipeline (faits en séance)
- Huit PR Dependabot mergées (CI verte, une par une) ; label `dependances` créé.
- Tête de pile #444 mergée (28 lots).

## 1 bis. Objectif du week-end (17-18 oct.) : publier la première soumission Devpost
Le batch 2 doit avoir livré au moins HC1 (position stable), RC27 (le 2:30 tient : source de la vidéo) et RG11 (l'appel
Nebius visible) ; la pile mergée et **déployée en production** (`simulator.naviguide.fr`) avant la chaîne Devpost
(issue #432 : relève → réponses Fable → brouillon rempli → le porteur soumet). Détail : `docs/PLAN_BATCH_2026-10-14.md` § 4.

## 2. Ce que la revue valide
- Deux pilules Suivre | Tracer ; Tracer sur la route Berry montre l'expédition complète depuis Saint-Maur (« ça
  c'est bien ») ; la lecture repart bien d'aujourd'hui après « repartir au début ».
- Le film : plus fluide, plus riche (stations, eaux, projets, climatologie).

## 3. Le principe directeur énoncé par le porteur
**Cloisonner** les deux modes et les faire **communiquer**.
- **Tracer** = tracer une route personnalisée (circumnavigation, transat, océan Indien), visualiser la route Berry
  (vitrine), importer une route, **simuler** : partir aujourd'hui et dérouler la traversée en accéléré.
- **Suivre** = suivre une route — celle de Berry (position calculée, journal, Revoir) **ou la mienne** : la rejouer
  à différentes dates de départ et obtenir un récit (calculs « ici », sac, récit).
- La communication : je trace en Tracer → Suivre me permet de rejouer *cette* route et d'en obtenir le récit.

## 4. Réflexions demandées — tranchées par le porteur le 14 oct. au soir (« Encadré OK, Panneau droit OK »)

### 4.1 L'encadré gauche (Maintenant · Journal · Revue du plan · Récit) : à quoi sert-il dans chaque mode ?
Ce qu'il est aujourd'hui : un instrument de **Suivre**. *Maintenant* = le sac « ici » autour du bateau calculé ;
*Journal* = ce que le bateau a croisé (eaux, ports d'entrée, AMP, coups de vent) — c'est la matière du film ;
*Revue du plan* = le plan officiel, jambe par jambe, fourchette, alertes ; *Récit* = le texte.

En **Tracer**, le porteur a raison : *Maintenant* et *Journal* n'ont pas d'objet (il n'y a pas de « maintenant »,
rien n'a été croisé). Ce qui sert le tracé, c'est **la Revue du plan appliquée à la route qu'on trace** : étapes,
milles, jours de mer à la polaire, ETA depuis aujourd'hui, et surtout **ce que la route traverse** (eaux, AMP,
ports d'entrée, zones piraterie / anti-trafic, câbles) — c'est le « sac » calculé le long de la route plutôt
qu'autour d'un point. Le *Récit* peut y avoir sa place pour la route Berry (vitrine : « voilà ce que vous
obtiendrez en Suivre »), et, après DM8, pour la route tracée.

Options :
- **A — masquer** en Tracer *Maintenant* et *Journal*, garder *Revue du plan* (sur la route tracée) et *Récit*
  (vitrine Berry). Le moins de code, le plus clair.
- **B — renommer** en Tracer : *Votre route* (étapes du tracé, distances, jours), *Ce que la route traverse* (le sac
  le long du trait), *Revue du plan*, *Récit*. Plus ambitieux, c'est l'encadré « pratico-pratique » du traceur.
- **C — ne rien changer** mais l'asseoir sur la position du tracé (corrige C5 seulement).

Recommandation du chat : **A maintenant** (c'est le cloisonnement que vous décrivez, et C5 disparaît avec), **B
comme lot ultérieur** quand le sac le long d'une route (RG19 / AM1 fournissent les briques) sera en place.

**Décision (porteur, 14 oct.) : option A → lot DM9.**

### 4.2 Le panneau droit en Tracer : qu'est-ce qui doit rester ?
| Élément | En Tracer | Pourquoi |
|---|---|---|
| Calques | **oui** | on trace en regardant les couches (AMP, câbles, bathy, ZEE) |
| Exporter (GeoJSON / KML) | **oui** | c'est la sortie naturelle d'un tracé |
| Polaires | oui, replié | la vitesse de la simulation et les jours de mer de la Revue du plan en dépendent |
| Paramètres avancés (ordres skipper) | discutable → **replié** | utile seulement pour Recalculer / Demander conseil sur la route tracée |
| Date de départ | **non** (masquée) | la lecture part d'aujourd'hui (C4) ; une date antérieure = rejouer = Suivre |
| Isochrone / Recalculer / Conseil | oui | c'est l'outil du traceur |

Recommandation : masquer **Date de départ** en Tracer (elle y serait inerte après C4), tout le reste reste,
Polaires et Paramètres avancés repliés par défaut.

**Décision (porteur, 14 oct.) : recommandation retenue → DM7 (date) et DM9 (replis).**

### 4.3 Où mettre l'IA (Nemotron via Nebius Token Factory) ?
Règle déjà posée et qui tient : **les règles décident *quand* et *de quoi* on parle, les sources décident de ce qui
est vrai, le modèle décide *comment le dire*** — et jamais un chiffre. Depuis le 29 sept., le modèle ne tourne
que sur demande (`on-demand`), le juge Ultra et la veille Tavily sont coupés. Aujourd'hui le seul usage vivant
est le chat. Or les **règles du hackathon exigent un appel Nebius à l'exécution, visible** — il faut donc des
usages visibles, maîtrisés, étiquetés « Nemotron 3 … · Token Factory ».

| Usage | Palier | Déclencheur | Coût | Lot |
|---|---|---|---|---|
| **Récit « Rédigé »** du film (réécriture fluide du brut, faits vérifiés) | Super | pilule Rédigé ; régénéré 1×/jour/langue/variante, mis en stock | ~3 appels/jour | **RG11** (§ 5) |
| **Chat** : comprendre la question | Lightning | chaque question | centimes | RG19 |
| **Chat** : raisonner (conseil, « que faire si ») sur le paquet de faits complet | Ultra | case « raisonnement », plafond 10/jour | maîtrisé | RG19 |
| Récit des fiches « ici » | Super | pilule Rédigé seulement | sur demande | RG18 |
| Récit de **ma** route (Suivre sur route perso) | Super | sur demande, après DM8 | sur demande | DM8+ |
| « Ce que je changerais » (Revue du plan) | règles aujourd'hui ; Ultra possible | — | — | plus tard |
| Juge de vérité (Tavily + Ultra) sur les ports d'entrée | coupé | — | cher | non |
| Pré-génération de récits en fond | coupé (RG18 la supprime) | — | 177 appels/nuit | non |

Recommandation : **RG11 et RG19 dans ce batch** — ce sont les deux usages que les juges verront (une pilule, un
chat), bornés et étiquetés ; RG18 pour que rien ne tourne sans geste.

**Décision (porteur, 14 oct.) : RG11 « bien évidemment, c'est l'objet du hackathon » → dans le batch ; RG19 et RG18 restent ; DM8 (récit de ma route) entre dans le batch.**

## 5. Les deux décisions en suspens, expliquées — et tranchées le 14 oct. au soir

### RC27 — « le 2:30 tient vraiment à 150 s »
Le film a trois durées : **2:30**, **3:00** (pilules) et **intégral** (sans pilule). Le 2:30 existe pour la **vidéo
Devpost** (règle : vidéo YouTube < 3 min). Aujourd'hui la pilule 2:30 produit **3 min 23** : sur 3 051 caractères,
les ouvertures et arrivées de chapitre — protégées par RC22 — en font 2 757, le milieu (AMP, projet, eaux) 393 ;
le plafond (2 475 car.) est inatteignable en élaguant le milieu. RC27 propose un **gabarit compact** pour la
variante 2:30 seulement (« Le 26 mai, cap sur Fort-de-France : 5 153 milles, une trentaine de jours de mer. »
au lieu de trois phrases où le lieu est dit quatre fois). Vous l'avez **parqué** le 29 sept. : « c'est pour la
vidéo du hackathon, c'est un faux problème : d'abord un film et un récit qui se tiennent ». Le film se tient
mieux maintenant (RC26). **Décision (porteur)** : « ce qui serait bien, c'est que la vidéo du 30 octobre soit faite à partir de la vidéo de 2:30 ; si c'est trop compliqué on fera autrement » → **RC27 entre dans le batch** (après RC30, avant RG11 : le Rédigé doit tenir dans le même budget).

### RG11 — « Rédigé » depuis les faits
La barre film a deux pilules **Brut | Rédigé**. *Brut* = le texte des règles (ce qu'on entend). *Rédigé* devait
être le même récit **réécrit par Nemotron 3 Super** pour être plus fluide à l'oreille — sans ajouter un fait, sans
changer un nombre. Depuis RF2 (le stock), la version rédigée **n'est plus servie** : la pilule est morte (elle
rend le brut). RG11 la ferait vivre : réécriture depuis les faits structurés de chaque étape, vérification
(nombres, noms, dates — `filter_numbers`), repli sur le brut au moindre écart, régénérée une fois par jour et par
langue dans le stock, étiquette « Nemotron 3 Super · Token Factory » affichée. Coût : quelques appels Super par
jour. C'est **l'usage le plus visible de Nebius** pour les juges (§ 4.3). **Décision (porteur)** : « on le fait bien évidemment, c'est l'objet du hackathon » → **RG11 dans le batch** (Fable), servi par le stock, une génération par jour et par variante, étiqueté.

## 6. Transcription du film (porteur, 14 oct.) — lecture
Points justes : ouverture, escales, eaux, projets, climatologie, clôture présente. Défauts (→ RC30) : ordre
climatologie / eaux (E3), coupures (E1), étiquette géographique d'un événement climato posée loin du bateau
(« au nord de Gibraltar » le 19 mai alors que le bateau longe la Galice), cap de la jambe Cayenne → Papeete, nom
de bassin à l'arrivée (« Caraïbes Ouest, Atlantique Nord » pour Papeete), redite Saint-Martin / Sint Maarten, six
flotteurs Argo anonymes. Les nombres « 39 304 000 » / « 1 820 000 » sont la transcription de « milles » par la
reconnaissance vocale, pas un défaut du texte ; à écouter une fois pour s'en assurer.

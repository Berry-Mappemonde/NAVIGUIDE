# Parcours de référence — tout tester, sur la tête de pile, avec les yeux

Joué par **Grok Bot** (navigateur) sur le poste de recette, à la demande postée par `run_lots.py` sur
la PR de tête (« 🧭 Parcours de référence ») : **avant chaque passage du réviseur de nuit** (toutes
les N PR) et en fin de batch. Le réviseur lit le verdict du parcours avant de relire le code. Aussi
jouable par le porteur, ou par un agent Playwright. But : attraper les **régressions que les cases des
PR ne couvrent pas**.

**L'interface affichée est la source de vérité.** Ce fichier décrit l'écran du 15–16 oct. 2026
(Suivre / Tracer / film après DM6–DM9, UI1, RF7, RG11, RG19). Un item qui parle d'un contrat
retiré (Simulation comme mode — la pilule livrée se lit **Suivre / Tracer**, cliquer
« Simulation » n'est plus un item ; « Croisière · 36 h » d'un seul tenant, Tracer = vitrine Berry,
Cinéma qui masque les panneaux) est une case à ignorer, pas un KO produit.

**Tout ce qui suit se voit** — à l'écran, dans la console, ou dans la télémétrie du film
`window.__naviguideFilm`. Aucun item ne demande d'écouter : ce que seule l'oreille peut juger est
dans la dernière section, réservée au porteur, et **le bot ne la compte pas**.

Résultat : **un** commentaire sur la PR de tête, qui commence par `## 🤖 Parcours de référence`, une
ligne par item, même format que la pré-revue : `- [x] 🤖 <item>` vu et bon · `- [ ] 🤖 <item> — KO :
<écran, ce que je vois, ce que je voulais>` · `- [ ] 🤖 <item> — non vérifiable : <pourquoi>` (doit
rester rare : chaque item ci-dessous a été écrit pour être vérifiable par un navigateur). Les erreurs de
console s'écrivent `- [ ] 🤖 Console (<écran>) — KO : <message, fichier:ligne ou URL en 4xx/5xx>`.
Terminer par « Vu n / total · KO k ». La collecte lit ces lignes ; le réviseur et le correcteur les
traitent comme des KO du porteur.

**Console** : à chaque écran, console ouverte (F12 / ⌥⌘J), noter toute **exception JS** et tout
`Failed to load` applicatif (`/voyage`, `/route`, `/wind`, `/film` en 5xx inattendu). **Ne pas KO**
sur : avertissements jaunes ; `net::ERR_ABORTED` (RH2) ; `502` `/bi/climatology/point` ou
`/bi/climatology/crossings` (atlas hors quota) ; `429` `/ici/story` ; `400` `/escale` si la
longitude n'est pas ramenée ; `524` `/voyage/…/recompute` (isochrone poste). Recharger une fois
avant de commencer (Cmd R).

**Télémétrie du film** (à copier dans la console pendant Revoir) :

```js
JSON.stringify(window.__naviguideFilm)   // chapterIdx, charIdx, elapsed, tMs, lat, lon, chapterText, status
```

Deux relevés à 10 s d'intervalle suffisent pour juger le rythme (`charIdx` augmente régulièrement),
l'avance (`elapsed` et `tMs` augmentent, `lat`/`lon` bougent) et la position (le bateau est près du
lieu que le sous-titre nomme).

## A. Chargement (Cmd R)

- La carte s'affiche avec le fond (tuiles), la route Berry (trait) et le catamaran ; les crédits « Tuiles © Esri — HERE, Garmin, © OpenStreetMap contributors » sont lisibles en bas à droite, **collés à la barre**, à la même hauteur que les boutons + / − (UI1). Ne pas KO sur le nombre de `<div>` ni sur le nombre de rangées de la barre.
- L'application ouvre en **Suivre** + **Cinéma** (suivi caméra) + carte monde (RF7) ; aucune bulle ni fiche n'est collée au bateau. **Cinéma ne masque pas les panneaux** — c'est **Plein écran film** qui le fait.
- Panneau gauche : carte Berry (logos), « Journal de bord » avec son champ, onglets **Maintenant / Récit / Journal / Revue du plan**, puis les encadrés ; aucune phrase d'explication superflue.
- Barre : **Masquer la barre**, **Cinéma**, **Plein écran film**, **Écouter**, pilules **Brut / Rédigé**, **Suivre / Tracer**, **Revoir**, pilules **2:30 / 3:00** si le film est là.
- Console : aucune exception JS au chargement (les 502 climatologie ne comptent pas).

## B. Suivre l'expédition

- Cliquer **Suivre l'expédition** → le bateau se place sur sa position du jour ; la barre indique la jambe courante (« <escale> → <escale> »), le jour (J…), les milles restants, l'ETA et une vitesse en kn. Exemple vu le 16 oct. : `Mata-Utu → Nouméa` + `Restants … nm` + `ETA` + `LIVE` + régime.
- Ligne d'état : elle se termine par le **régime** (`climatologie` / `prévision` / `hindcast`). « réel jusqu'au \<date\> » n'apparaît **que** s'il existe un segment hindcast ; tant que `clock-regime` dit climatologie, **ne pas KO** l'absence de cette phrase (HC1).
- La route déjà parcourue est teintée **selon le régime** : hindcast turquoise `#2dd4bf`, prévision bleu `#38bdf8`, climatologie violet `#c084fc`. Tout le parcouru violet est **normal** si la ligne d'état dit climatologie — ne pas exiger le turquoise.
- Les jambes **avion** (Cayenne ↔ Halifax, sauts Pacifique) sont en **pointillé** (liseré clair `#e5e7eb` + trait sombre `#111`) : ça peut paraître gris/blanc sur le fond, ce n'est pas un KO. Halifax ↔ Saint-Pierre est une jambe de mer (trait plein, éventuellement plus clair).
- Fourchette d'arrivée : **soit** une ligne « arriver entre le … et le … » sous la prochaine escale (`eta-range`), **soit** la même info (ou « fourchette indisponible — … ») dans **Revue du plan**. Un `eta-range` vide n'est pas un KO si la revue du plan dit pourquoi (ensemble / atlas).
- Panneau gauche, onglet **Maintenant** : le sac « ici » se remplit (ZEE, ports, AMP, météo…). Une phrase honnête du type « Aucun port d'entrée officiel n'est connu pour cette ZEE » n'est **pas** une redite. Tous les liens n'ont pas à être soulignés.
- Survol de la pilule de vitesse **ou** de `clock-regime` → info-bulle des trois régimes (hindcast / prévision / climatologie). Le `title` est souvent sur `clock-regime`, pas sur le chiffre `0.5 kt`.
- Cliquer **Masquer la barre** → la barre disparaît ; **Afficher la barre** → elle revient. L'attribution reste collée juste au-dessus.
- Cliquer **Cinéma** (s'il est déjà enfoncé, le laisser) → la caméra suit le bateau ; zoom ou glisser libère la carte ; recliquer recadre. **Les panneaux restent.** Pour les masquer : **Plein écran film** → classe `film-fullscreen`, panneaux cachés ; Échap ou recliquer les rend.
- Cliquer **Écouter** → le bouton passe à l'état pressé et, dans la console, `speechSynthesis.speaking` devient `true` en moins de 3 s ; recliquer → il redevient `false`.
- Recharger (Cmd R) puis **Suivre** : le bateau réapparaît **à la même position** (pas de saut).
- Console : règles du préambule.

## C. Revoir l'expédition (le film)

- En Suivre, **premier clic** sur **Revoir l'expédition** (bouton actif) → le bateau part de Saint-Maur ; en moins de 3 s le sous-titre affiche le premier texte et `__naviguideFilm.elapsed` augmente ; la caméra se pose sur la première jambe. Si Revoir est grisé : noter le `status` (`pending` / `stale` / `empty`) et **NV**, pas KO produit — le stock EN rf5 est stale RE7 (« Bay of Biscay »).
- **Rythme constant** : relever `charIdx` et `elapsed` à ~10 s puis à ~40 s (hors changement de chapitre) → le débit `Δ charIdx / Δ elapsed` est le même à ± 20 % (la voix n'accélère pas ; le film n'est pas mené par le budget).
- **Le film ne se coupe pas** : à 60 s, `__naviguideFilm.ended` est `false` et `chapterIdx` a avancé ou `charIdx` a dépassé 300 ; à la fin, `ended` passe à `true` seulement après le dernier chapitre (`chapterIdx` = `chapterCount − 1`).
- **Le bateau est où le texte le dit** : quand le sous-titre nomme une escale (La Rochelle, Ajaccio, Fort-de-France, Pointe-à-Pitre…), le catamaran est à côté du drapeau de cette escale (pas à l'escale précédente) ; quand il nomme un départ, le bateau quitte le port ; quand il dit « à quai », il ne bouge pas. Relever 3 alignements au moins, en noter les lieux.
- **Le bateau avance sans à-coup** : entre deux relevés à 1 s d'écart en pleine traversée, `lat`/`lon` ont changé ; aucun bond visible du bateau à l'écran hors changement de jambe ; le fond de carte reste visible (pas de damier gris) ; le zoom ne change pas au milieu d'une jambe.
- Dans les Caraïbes, la caméra montre l'archipel sans sauter d'île en île ; au changement de jambe, un seul mouvement.
- Une **bulle** ancrée au bateau peut apparaître à l'approche des escales / sur un événement ; la croix la ferme ; le film continue ; jamais deux bulles à la fois ; aucune fiche d'escale ne s'ouvre pendant le film. Absence de bulle sur un film court (2:30) : **NV**, pas KO.
- Les pilules **Brut / Rédigé** restent visibles (grisées ou non selon `hasWritten`) ; le sous-titre du chapitre s'affiche dans la barre ; sélecteur **2:30 / 3:00** présent. Le sous-titre est **la phrase en cours**, pas tout le chapitre : la clôture « Aujourd'hui, le bateau est… » se juge dans `chapterText` / le script, pas sur la dernière ligne coupée (« Les escales à venir… »).
- **Stop** arrête net le film : `speechSynthesis.speaking` repasse à `false`, le bateau revient à la vue Suivre ; **Retour au live** / recliquer Suivre le replace sur sa position du jour ; dézoomer à la molette fonctionne dès le premier geste.
- Laisser un film entier (ou le 2:30) : la barre de progression avance ; à l'arrêt, pas de saut de zoom. Ne pas KO un 2:30 qui dure un peu plus que 150 s à l'oreille si `targetSeconds` côté client est 150.
- Passer la langue en **anglais** (panneau droit) → si Revoir reste actif : le sous-titre est en anglais, même ordre d'escales (Saint-Maur, La Rochelle, Ajaccio…). Si Revoir passe au gris (`status === "stale"`) : **NV** — le blob EN du stock figé est stale RE7 ; le GET `/film?lang=en` peut quand même contenir « 15 May 2026 ».
- **Une étape complète** (RG10) : juger `chapterText` (pas seulement le sous-titre coupé). Ordre : ouverture (départ, milles) → faits de route quand le chapitre en a → arrivée (ou « Aujourd'hui » si le bateau est encore en mer). Relever un chapitre atlantique.
- **Mots interdits absents** du sous-titre et de `chapterText` : « jambe », « zone économique exclusive », « Couloirs », « À surveiller », « à portée de », « de de ». Les titres anglais **de projets / jeux de données réellement nommés ainsi** (Panama Expedition, Shark spy…) ne sont pas un KO de libellé UI.
- **Ordre chronologique** : dans un même `chapterText`, les dates et les lieux vont dans l'ordre de la route. Les ancres (`anchors`) du chapitre ont des `t` non décroissants.
- Console : règles du préambule.

## D. Tracer

Depuis DM6 / DM7 / DM9, **Tracer ouvre le dessin**. L'horloge part d'**aujourd'hui** (j0). Pas de champ libellé « Date de départ ».

- Cliquer **Tracer** → cadre `drawing-box` : « TRACÉ EN COURS » + « Choisissez votre point de départ » (ou l'équivalent EN) ; horloge du type `0 nm · j0 · <aujourd'hui> 08:00 UTC`.
- Carte route : **Importer**, **Annuler**, **Terminer** (Terminer grisé tant qu'il n'y a pas deux points) ; la pilule de tracé est active. **Berry-Mappemonde** ramène la route officielle sans perdre le brouillon.
- Encadré gauche : onglets **Revue du plan** et **Récit** seulement — **pas** Maintenant ni Journal.
- Les boutons **Lecture / Escale précédente / Prochaine escale / Stop auto** peuvent rester dans la barre : **ne pas KO** s'ils sont là ; **ne pas exiger** qu'ils fassent défiler Saint-Maur → La Rochelle (ce n'est plus le contrat Tracer). Escale précédente est grisé tant qu'aucun point n'est posé.
- Popup satellite (icône, en Suivre ou sur le brouillon) : onglets **Vent / Vagues / Courants** avec des chiffres — souvent NV en headless.
- Aucun mot « Simulation » à l'écran (barre, panneaux, info-bulles), en français comme en anglais.
- Console : règles du préambule.

## E. Tracer ma route

- **Tracer votre propre route** → le monde entier, une fois → deux clics au large (ex. Australie → Californie) → la route se calcule **en ligne droite dans le Pacifique** (pas par le détroit de Béring).
- **Terminer** → le sac se remplit autour du bateau ; les cartes se parcourent avec la flèche sans disparaître. GeoJSON / KML deviennent cliquables.
- **Importer** : un `.geojson` de 3 points → 3 drapeaux + route ; un `.kml` → idem.
- **Annuler** (pas de bouton « Effacer ») → brouillon vidé, retour à l'état vide sans erreur.
- Console : règles du préambule.

## F. Panneau droit

- **Paramètres avancés** (déplié) : profil **Côtier / Croisière / Large** et horizon **24 h / 36 h / 48 h** sont des **boutons séparés**. La phrase « Croisière · 36 h » **n'existe plus** dans l'en-tête replié — ne pas la chercher. **Chiffres** : changer « Coup de vent » puis le cercle « Remettre le chiffre du profil » ramène la valeur.
- **Polaires** : « Polaires chargées » puis **Voir**. Le nom « Léopard 46 » n'est plus exigé s'il n'est pas à l'écran. Diagramme : le juger seulement si **Voir** l'ouvre ; sinon NV.
- **Calques** : interrupteurs **ZEE, Ports WPI, Balisage, Projets, Marinas, Capitainerie, Port d'entrée, AMP, Sextant, Argo, Bathymétrie, Fonds, Câbles, Vent, Houle, Courants, Cyclones, GRIB2**. Il n'y a **pas** de toggle unique « climatologie » (c'est Vent / Houle / Courants / Cyclones). Au zoom monde, Balisage et Bathymétrie peuvent ne rien changer à l'œil — ne pas KO si le bouton s'enfonce.
- **Revue du plan** : chaque jambe a une date, des milles, des jours. Les chiffres **actuels** (ex. Nouméa → Dzaoudzi ≈ 6 144 nm · 32 j, Ajaccio → Fort-de-France 5 153 nm · 26,8 j) remplacent l'ancien exemple 9 152 nm / 47 j. « Ce que je changerais » est une phrase qui nomme une jambe.
- **Recalculer / Demander conseil / Calcul isochrone** : présents. Sur la route officielle ou un brouillon vide ils sont souvent **grisés ou en 524** — NV, pas KO, et **ne pas exiger** « ≤ 1 650 nm La Rochelle → Ajaccio ».
- **Exporter** : boutons GeoJSON et KML présents. Grisés tant qu'aucune route terminée n'est sélectionnée ; un téléchargement n'est exigé qu'après **Terminer** sur un tracé.
- Survol de la **distance** (si une info-bulle existe) → « distance du film, saut avion exclu ». Absence du `title` : NV.
- **Thème** clair → mêmes encadrés, même collage crédits / barre ; **Langue** EN → libellés anglais (Follow, Trace, Replay, Hide the bar…).
- Console : règles du préambule.

## G. Journal de bord (chat)

- Le champ est sous les logos, placeholder du type « Quel vent au bateau ? Prochaine escale ? ». Case **Raisonnement** à côté s'il s'agit de RG19 (libellé seul).
- Poser « À quelle vitesse va le bateau ? » → une **phrase** (chiffre en kn, source **règles**), jamais un prompt.
- Poser « Quel vent au bateau ? » → une phrase avec un vent en kn, source **règles**.
- Console : règles du préambule (pas d'appel Nebius / Token Factory hors case Raisonnement).

## H. Carte

- Tirer la carte vers le haut / le bas au maximum → on ne dépasse pas les pôles (jamais un écran tout bleu).
- Tirer sur les côtés → le monde ne se répète **qu'une fois** de chaque côté.
- En Suivre, dézoomer au maximum (molette, bouton −) → **on ne voit jamais deux fois le monde d'affilée**.
- Zoom molette sur l'Atlantique → la carte suit tout de suite, sans saccade.
- Zoomer / dézoomer dix fois au-dessus des drapeaux (Wallis, Nouvelle-Calédonie, Fort-de-France) → **aucun glissement latéral**.
- Cliquer une fiche de couche (port, projet) → la fiche s'ouvre ; un lien s'il existe dans les données (certains ports WPI n'en ont pas — ne pas KO l'absence) ; la croix la ferme.
- Console : règles du préambule.

## I. À l'oreille — porteur seulement (le bot ne compte pas ces lignes)

- La voix garde le même rythme du début à la fin ; aucune accélération après le premier chapitre.
- Le récit se comprend : escales dans l'ordre, pas de jargon (« jambe », « zone économique exclusive »), pas de « de de ».
- En anglais, la voix est anglaise et compréhensible — seulement si Revoir EN est actif.
- **Rédigé** (dernier passage seulement : coûte un appel Super) : **Suivre**, film prêt, cliquer « Rédigé », attendre ≤ 30 s → le texte change de plume (source **Nemotron 3 Super · Token Factory**) et chaque nombre reste celui du Brut ; puis revenir sur Brut. Si Rédigé est grisé (« pas encore rédigé pour cette durée ») : c'est l'état honnête, pas un KO.

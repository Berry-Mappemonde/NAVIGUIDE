# Parcours de référence — tout tester, sur la tête de pile, avec les yeux

Joué par **Grok Bot** (navigateur) sur le poste de recette, à la demande postée par `run_lots.py` sur
la PR de tête (« 🧭 Parcours de référence ») : **avant chaque passage du réviseur de nuit** (toutes
les N PR) et en fin de batch. Le réviseur lit le verdict du parcours avant de relire le code. Aussi
jouable par le porteur, ou par un agent Playwright. But : attraper les **régressions que les cases des
PR ne couvrent pas**.

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

**Console** : à chaque écran, console ouverte (F12 / ⌥⌘J), noter toute erreur rouge (exception JS,
`Failed to load`, 4xx/5xx sur `/ici`, `/voyage`, `/route`, `/wind`…), ignorer les avertissements jaunes
et les `net::ERR_ABORTED` (connus, lot RH2). Recharger une fois avant de commencer (Cmd R) : aucune
erreur au chargement.

**Télémétrie du film** (à copier dans la console pendant Revoir) :

```js
JSON.stringify(window.__naviguideFilm)   // chapterIdx, charIdx, elapsed, tMs, lat, lon, chapterText
```

Deux relevés à 10 s d'intervalle suffisent pour juger le rythme (`charIdx` augmente régulièrement),
l'avance (`elapsed` et `tMs` augmentent, `lat`/`lon` bougent) et la position (le bateau est près du
lieu que le sous-titre nomme).

## A. Chargement (Cmd R)

- La carte s'affiche avec le fond (tuiles), la route Berry (trait) et le catamaran ; les crédits « Tuiles © Esri — HERE, Garmin, © OpenStreetMap contributors » sont lisibles en bas à droite, non coupés par la barre.
- L'application ouvre en **Suivre** + Cinéma + carte monde (RF7) ; la barre film est sur **une seule rangée** ; aucune bulle ni fiche n'est collée au bateau.
- Panneau gauche : carte Berry (logos), « Journal de bord — posez une question » avec son champ, puis les encadrés à hauteur fixe ; aucune phrase d'explication superflue.
- Console : aucune erreur au chargement.

## B. Suivre l'expédition

- Cliquer **Suivre l'expédition** → le bateau se place sur sa position du jour ; la barre indique la jambe courante (« <escale> → <escale> »), le jour (J…), les milles restants, l'ETA et une vitesse en kn.
- La route déjà parcourue est teintée (régime), le reste en couleur de régime ; les jambes **avion** (Cayenne ↔ Saint-Pierre-et-Miquelon) sont en pointillé noir.
- Sous la prochaine escale (légende des escales, bas de carte) : **soit** « arriver entre le … et le … », **soit** une ligne qui dit pourquoi la fourchette manque (RG17) — jamais rien.
- Panneau gauche : le sac « ici » se remplit (ZEE, port d'entrée, AMP, balisage, météo) avec des **liens** de sources soulignés ; le récit de la traversée est là ; aucune redite visible.
- Survol de la pilule de vitesse → info-bulle des trois régimes (hindcast / prévision / climatologie).
- Cliquer **Masquer la barre** → la barre disparaît ; **Afficher la barre** → elle revient.
- Cliquer **Cinéma** → panneaux masqués, carte plein écran ; recliquer → panneaux de retour.
- Cliquer **Écouter** → le bouton passe à l'état pressé et, dans la console, `speechSynthesis.speaking` devient `true` en moins de 3 s ; recliquer → il redevient `false`.
- Recharger (Cmd R) puis **Suivre** : le bateau réapparaît **à la même position** (pas de saut).
- Console : aucune erreur.

## C. Revoir l'expédition (le film)

- En Suivre, **premier clic** sur **Revoir l'expédition** → le bateau part de Saint-Maur ; en moins de 3 s le sous-titre affiche le premier texte et `__naviguideFilm.elapsed` augmente ; la caméra se pose directement sur la première jambe.
- **Rythme constant** : relever `charIdx` et `elapsed` à ~10 s puis à ~40 s (hors changement de chapitre) → le débit `Δ charIdx / Δ elapsed` est le même à ± 20 % (la voix n'accélère pas ; le film n'est pas mené par le budget).
- **Le film ne se coupe pas** : à 60 s, `__naviguideFilm.ended` est `false` et `chapterIdx` a avancé ou `charIdx` a dépassé 300 ; à la fin, `ended` passe à `true` seulement après le dernier chapitre (`chapterIdx` = `chapterCount − 1`).
- **Le bateau est où le texte le dit** : quand le sous-titre nomme une escale (La Rochelle, Ajaccio, Fort-de-France, Pointe-à-Pitre…), le catamaran est à côté du drapeau de cette escale sur la carte (pas à l'escale précédente) ; quand il nomme un départ, le bateau quitte le port ; quand il dit « à quai », il ne bouge pas. Relever 3 alignements au moins, en noter les lieux.
- **Le bateau avance sans à-coup** : entre deux relevés à 1 s d'écart en pleine traversée, `lat`/`lon` ont changé ; aucun bond visible du bateau à l'écran hors changement de jambe ; le fond de carte reste visible (pas de damier gris) ; le zoom ne change pas au milieu d'une jambe.
- Dans les Caraïbes, la caméra montre l'archipel sans sauter d'île en île ; au changement de jambe, un seul mouvement.
- Une **bulle** ancrée au bateau apparaît à l'approche des escales / sur un événement notable ; la croix la ferme ; le film continue ; jamais deux bulles à la fois ; aucune fiche d'escale ne s'ouvre pendant le film.
- Les pilules **brut / rédigé** sont grisées pendant le film ; le sous-titre du chapitre s'affiche dans la barre ; sélecteur 2:30 / 3:00 présent.
- **Stop** arrête net le film : `speechSynthesis.speaking` repasse à `false`, le bateau revient à la vue Suivre ; **Retour au live** le replace sur sa position du jour ; Suivre est de nouveau actif ; dézoomer à la molette fonctionne dès le premier geste.
- Laisser un film entier : la barre de progression atteint la fin, le film finit sur la position du jour, pas de saut de zoom à l'arrêt.
- Passer la langue en **anglais** (panneau droit) → relancer : le sous-titre est en anglais, même ordre d'escales (Saint-Maur, La Rochelle, Ajaccio…).
- Console : aucune erreur pendant le film.

## D. Simulation

- Cliquer **Simulation** → la barre montre Saint-Maur → La Rochelle ; **Escale précédente** est grisé, **Prochaine escale** actif.
- **Prochaine escale** → la barre passe à La Rochelle → Ajaccio ; **Escale précédente** ramène à Saint-Maur.
- Cliquer deux points en mer sur la barre → une vitesse en kn qui **change** d'un point à l'autre ; sur une escale : « à quai 3 j ».
- Curseur sur Saint-Maur : la carte « Escale » compte en **km par la route**, pas en milles.
- **Lecture / pause**, **Stop auto**, vitesses de lecture (réelle / normale / accélérer) : chaque bouton fait ce qu'il dit.
- Cliquer le **drapeau d'Ajaccio** → la fiche d'escale s'ouvre (sur la carte ou dans l'encadré selon le lot en cours), en **vraies phrases** (jamais « Analyze User Input / Task / Wait, let me… »), sans bouton Écouter ; la croix la ferme ; passer en Suivre la ferme aussi.
- Popup satellite (clic sur l'icône) : onglets **Vent / Vagues / Courants** avec des chiffres.
- Console : aucune erreur.

## E. Tracer ma route

- Cliquer **Tracer votre propre route** → la carte montre le monde entier, une fois → deux clics au large (ex. Australie → Californie) → la route se calcule **en ligne droite dans le Pacifique** (pas par le détroit de Béring).
- **Terminé** → le sac se remplit autour du bateau (ZEE australienne, ports d'entrée, cartes) ; les cartes se parcourent avec la flèche sans disparaître.
- **Importer** : un `.geojson` de 3 points → 3 drapeaux + route ; un `.kml` → idem.
- Effacer la route → retour à l'état vide sans erreur.
- Console : aucune erreur.

## F. Panneau droit

- **Paramètres avancés** : « Croisière · 36 h » n'apparaît **qu'une fois** ; **Chiffres** : changer « Coup de vent » puis cliquer le cercle → la valeur du profil revient ; aucune phrase d'explication sous les chiffres.
- **Polaires** : « Polaires chargées » puis « Voir » → le diagramme polaire / VMG s'affiche ; le nom du bateau n'apparaît qu'ici (Bateau : Léopard 46).
- **Calques** : activer / désactiver ZEE, ports, balisage, bathy, câbles, climatologie → chaque couche apparaît / disparaît sur la carte.
- **Revue du plan** (onglet de l'encadré gauche) : chaque jambe a une date, des milles, des jours de mer cohérents (ex. Nouméa → Dzaoudzi ≈ 9 152 nm, ≈ 47 j) ; la fourchette d'arrivée fait quelques jours, pas des mois ; « Ce que je changerais » est une phrase qui nomme une jambe.
- **Ordres du skipper** : vent max 30 kn → **Recalculer l'itinéraire / Demander conseil** → la route proposée fait **≤ 1 650 nm** pour La Rochelle → Ajaccio (jamais 4 643).
- **Exporter** : GeoJSON et KML téléchargent un fichier non vide.
- Survol de la **distance** → info-bulle « distance du film, saut avion exclu ».
- **Thème** clair → mêmes encadrés, mêmes hauteurs ; **Langue** EN → libellés anglais partout, y compris la barre.
- Console : aucune erreur.

## G. Journal de bord (chat)

- Poser « À quelle vitesse va le bateau ? » → une **phrase** de réponse (ou le message d'échec honnête), jamais un prompt ; le chiffre est celui de la barre.
- Poser « Quel vent au bateau ? » → une phrase avec un vent en kn.
- Console : aucune erreur.

## H. Carte

- Tirer la carte vers le haut / le bas au maximum → on ne dépasse pas les pôles (jamais un écran tout bleu).
- Tirer sur les côtés → le monde ne se répète **qu'une fois** de chaque côté.
- En Suivre, dézoomer au maximum (molette, bouton −) → **on ne voit jamais deux fois le monde d'affilée** : le dézoom s'arrête quand le monde tient dans l'écran ; le glisser gauche / droite reste possible.
- Zoom molette sur l'Atlantique → la carte suit tout de suite, sans saccade.
- Zoomer / dézoomer dix fois au-dessus des drapeaux (Wallis, Nouvelle-Calédonie, Fort-de-France) et des bateaux → **aucun glissement latéral** : chaque drapeau reste sur le même point de côte, avant, pendant et après l'animation.
- Cliquer une fiche de couche (port, balise) → la fiche s'ouvre avec un lien ; la croix la ferme.
- Console : aucune erreur.

## I. À l'oreille — porteur seulement (le bot ne compte pas ces lignes)

- La voix garde le même rythme du début à la fin ; aucune accélération après le premier chapitre.
- Le récit se comprend : escales dans l'ordre, pas de jargon (« jambe », « zone économique exclusive », « Couloirs »), pas de titre de jeu de données, pas de « de de ».
- En anglais, la voix est anglaise et compréhensible.

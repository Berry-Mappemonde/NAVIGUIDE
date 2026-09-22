# Parcours de référence — tout tester, une fois par batch, sur la tête de pile

Joué par **Grok Bot** (navigateur) quand la dernière PR de la pile a reçu sa
pré-revue, à la demande postée par `run_lots.py` sur la PR de tête (« 🧭 Parcours
de référence »). Aussi jouable par le porteur, ou par un agent Playwright plus
tard. But : attraper les **régressions que les cases des PR ne couvrent pas**
(ce qu'aucun lot de la nuit n'a touché mais que la nuit a cassé).

Résultat : **un** commentaire sur la PR de tête, qui commence par
`## 🤖 Parcours de référence`, une ligne par item, même format que la pré-revue :
`- [x] 🤖 <item>` vu et bon · `- [ ] 🤖 <item> — KO : <écran, ce que je vois, ce que je voulais>`
· `- [ ] 🤖 <item> — non vérifiable : <pourquoi>`. Les erreurs de console s'écrivent
`- [ ] 🤖 Console (<écran>) — KO : <message, fichier:ligne ou URL en 4xx/5xx>`.
Terminer par « Vu n / total · KO k ». La collecte lit ces lignes ; le correcteur du
matin les traite comme des KO du porteur.

**Console** : à chaque écran, ouvrir la console du navigateur (F12 / ⌥⌘J), noter
toute erreur rouge (exception JS, `Failed to load`, 4xx/5xx sur `/ici`, `/voyage`,
`/route`, `/wind`…), ignorer les avertissements jaunes. Recharger la page une fois
avant de commencer (Cmd R) et vérifier qu'aucune erreur n'apparaît au chargement.

## A. Chargement (Cmd R)

- La carte s'affiche avec le fond (tuiles), la route Berry (trait) et le catamaran ; les crédits « Tuiles © Esri — HERE, Garmin, © OpenStreetMap contributors » sont lisibles en bas à droite, non coupés par la barre.
- L'application ouvre en **Simulation** ; la barre film est sur **une seule rangée** ; aucune bulle ni fiche n'est collée au bateau.
- Panneau gauche : carte Berry (logos), « Journal de bord — posez une question » avec son champ, puis les encadrés à hauteur fixe ; aucune phrase d'explication superflue.
- Console : aucune erreur au chargement.

## B. Suivre l'expédition

- Cliquer **Suivre l'expédition** → le bateau se place sur sa position du jour ; la barre indique la jambe courante (« <escale> → <escale> »), le jour (J…), les milles restants, l'ETA et une vitesse en kn.
- La route déjà parcourue est teintée (régime), le reste en couleur de régime ; les jambes **avion** (Cayenne ↔ Saint-Pierre-et-Miquelon) sont en pointillé noir.
- Sous la prochaine escale (légende des escales, bas de carte) : « arriver entre le … et le … » quand la fourchette existe.
- Panneau gauche : le sac « ici » se remplit (ZEE, port d'entrée, AMP, balisage, météo) avec des **liens** de sources soulignés ; le récit de la traversée est là ; aucune redite visible.
- Survol de la pilule de vitesse → info-bulle des trois régimes (hindcast / prévision / climatologie).
- Cliquer **Masquer la barre** → la barre disparaît ; **Afficher la barre** → elle revient.
- Cliquer **Cinéma** → panneaux masqués, carte plein écran ; recliquer → panneaux de retour.
- Cliquer **Écouter** → la voix lit le récit + le briefing ; recliquer → elle s'arrête.
- Recharger (Cmd R) puis **Suivre** : le bateau réapparaît **à la même position** (pas de saut).
- Console : aucune erreur.

## C. Revoir l'expédition (le film)

- En Suivre, **premier clic** sur **Revoir l'expédition** → le bateau part de Saint-Maur et la voix parle **dès ce clic** ; la caméra se pose directement sur la première jambe.
- Le récit énonce les escales **dans l'ordre du voyage** (Saint-Maur, La Rochelle, Ajaccio/Corse, Fort-de-France…), sans répéter une escale, avec des connecteurs variés (pas « puis, puis, puis »).
- Pendant une jambe : le **fond de carte reste visible**, le bateau **glisse** (pas de sauts), le zoom ne change pas ; au changement de jambe, un seul mouvement de caméra.
- Dans les Caraïbes, la caméra montre l'archipel sans sauter d'île en île.
- Une **bulle** ancrée au bateau apparaît à l'approche des escales / sur un événement notable ; la croix la ferme ; le film continue ; jamais deux bulles à la fois ; aucune fiche d'escale ne s'ouvre pendant le film.
- Les pilules **brut / rédigé** sont grisées pendant le film ; le sous-titre du chapitre s'affiche dans la barre ; sélecteur 2:30 / 3:00 présent.
- **Stop** arrête net le film (voix + animation) et revient à la vue Suivre ; **Retour au live** replace le bateau sur sa position du jour ; Suivre est de nouveau actif.
- Laisser un film entier (2 min 30) : la voix tient jusqu'à la fin ; le film finit sur la position du jour ; pas de saut de zoom à l'arrêt.
- Passer la langue en **anglais** (panneau droit) → relancer : voix anglaise compréhensible, même ordre d'escales.
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

- Cliquer **Tracer votre propre route** → deux clics au large (ex. Australie → Californie) → la route se calcule **en ligne droite dans le Pacifique** (pas par le détroit de Béring).
- **Terminé** → le sac se remplit autour du bateau (ZEE australienne, ports d'entrée, cartes) ; les cartes se parcourent avec la flèche sans disparaître.
- **Importer** (si le lot N1 est passé) : un `.geojson` de 3 points → 3 drapeaux + route ; un `.kml` → idem.
- Effacer la route → retour à l'état vide sans erreur.
- Console : aucune erreur.

## F. Panneau droit

- **Paramètres avancés** : « Croisière · 36 h » n'apparaît **qu'une fois** ; **Chiffres** : changer « Coup de vent » puis cliquer le cercle → la valeur du profil revient ; aucune phrase d'explication sous les chiffres.
- **Polaires** : « Polaires chargées » puis « Voir » → le diagramme polaire / VMG s'affiche ; le nom du bateau n'apparaît qu'ici (Bateau : Léopard 46).
- **Calques** : activer / désactiver ZEE, ports, balisage, bathy, câbles, climatologie → chaque couche apparaît / disparaît sur la carte.
- **Revue du plan** : chaque jambe a une date, des milles, des jours de mer cohérents (ex. Nouméa → Dzaoudzi ≈ 9 152 nm, ≈ 47 j) ; la fourchette d'arrivée fait quelques jours, pas des mois ; « Ce que je changerais » est une phrase qui nomme une jambe.
- **Ordres du skipper** : vent max 30 kn → **Recalculer l'itinéraire / Demander conseil** → la route proposée fait **≤ 1 650 nm** pour La Rochelle → Ajaccio (jamais 4 643).
- **Exporter** (si le lot N2 est passé) : GeoJSON et KML téléchargent un fichier non vide.
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
- Zoom molette sur l'Atlantique → la carte suit tout de suite, sans saccade.
- Cliquer une fiche de couche (port, balise) → la fiche s'ouvre avec un lien ; la croix la ferme.
- Console : aucune erreur.

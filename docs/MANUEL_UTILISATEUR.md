# Manuel utilisateur — NAVIGUIDE simulator

Ce manuel décrit **chaque bouton** que vous voyez à l’écran, en une ligne.
Aucun jargon. L’application **ne convient pas à la navigation**.

En ligne : [simulator.naviguide.fr](https://simulator.naviguide.fr).
Version anglaise : [USER_MANUAL.md](USER_MANUAL.md).

Au premier lancement, une fenêtre **Ne convient pas à la navigation**
apparaît. **Accepter** ferme la fenêtre et ouvre la carte.

La carte occupe le centre. Un **panneau gauche** (expédition, calques,
briefing), un **panneau droit** (outils), une **barre** en bas (temps,
lecture). **Masquer le panneau** replie le panneau concerné ;
recliquer le réouvre.

---

## 1. Suivre l’expédition

Le bateau est à la position d’**aujourd’hui**. La carte le suit.
La date de départ officielle est le 15 mai 2026, 08:00 UTC — elle
ne se change pas dans ce mode.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Suivre l’expédition** | Affiche le bateau à la position du jour et cadre la carte dessus. |
| **Simulation** | Quitte Suivre et ouvre le mode lecture (voir chapitre 2). |
| **Berry** | Revient à la route officielle Berry-Mappemonde. |
| **Tracer votre propre route** | Passe en dessin de route (voir chapitre 3). |
| **Revoir l’expédition** | Lance le film raconté (voir chapitre 4). |
| **Maintenant** | Montre ce qui compte autour du bateau en ce moment. |
| **Récit** | Montre le récit de la traversée jusqu’à aujourd’hui. |
| **Journal** | Montre le journal de bord, dans l’ordre des jours. |
| **Écouter** | Lit le récit à voix haute. |
| **Stop** (à côté d’Écouter) | Coupe la voix. |
| **Envoyer** | Envoie votre question au journal de bord. |
| **Voir sur la carte** | Cadre le bateau et le lieu dont parle la carte. |
| **Fiche / site officiel** | Ouvre la page officielle (port d’entrée, aire protégée…). |
| **Source des données** | Ouvre la source du chiffre affiché. |
| **Fiche Google Maps** | Ouvre le lieu dans Google Maps. |
| **Suivant** (sur une carte) | Passe à la carte suivante. |
| **Fermer** (sur une carte) | Range la carte. |
| **Revenir au live (L)** | Si vous avez bougé dans le temps : retour à « maintenant ». |
| **Calques** | Allume ou éteint une couche sur la carte (voir plus bas). |
| **Masquer le panneau** | Replie le panneau gauche. |

Les **calques** (panneau gauche) :

| Bouton | Ce qu’il fait |
|--------|----------------|
| **GRIB2** | Affiche le vent et la mer de la dernière prévision autour du bateau. |
| **ZEE** | Affiche les zones économiques exclusives. |
| **Ports WPI** | Affiche les ports du World Port Index. |
| **Balisage** | Affiche les marques de mer (OpenSeaMap). |
| **Projets** | Affiche les projets de conservation marine. |
| **Marinas** | Affiche les marinas. |
| **Capitainerie** | Affiche les capitaineries. |
| **Port d'entrée** | Affiche les ports d’entrée officiels. |
| **AMP** | Affiche les aires marines protégées. |
| **Sextant / Argo / ODATIS / EDMED / CSR** | Affiche une couche scientifique. |
| **Bathymétrie** | Affiche les fonds en relief. |
| **Fonds** | Affiche la nature des fonds. |
| **Câbles** | Affiche les câbles sous-marins. |
| **Climat** | Affiche l’atlas du mois (vent typique, pas demain). |
| **Vent / Houle / Courants / Cyclones** (sous Climat) | Allume une carte de l’atlas. |

Cliquez un point de la route : une fiche **Données satellite** s’ouvre.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Vent** | Montre force et direction du vent à cet endroit. |
| **Vagues** | Montre la hauteur et la période des vagues. |
| **Courants** | Montre le courant de surface. |

Si le bateau entre dans une zone de piraterie recensée, une carte
**Piraterie** apparaît. Hors zone, elle disparaît.

---

## 2. Simulation

Même carte, même briefing. Vous **faites avancer** le temps.
La date de départ est celle du jour ; vous pouvez la changer.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Simulation** | Entre dans ce mode (Play, vitesses, sauts d’escale). |
| **Suivre l’expédition** | Quitte la simulation et revient à la position du jour. |
| **Jour (UTC)** | Change le jour de départ. |
| **Heure UTC** | Change l’heure de départ. |
| **Lecture** | Fait avancer le bateau. |
| **Pause** | Arrête le bateau là où il est. |
| **Escale précédente** | saute à l’escale d’avant et recentre la carte. |
| **Prochaine escale** | saute à l’escale suivante et recentre la carte. |
| **réel** | 1 seconde à l’écran = 1 seconde en mer. |
| **lecture** | Lent : on a le temps de lire pendant une traversée. |
| **normale** | Vitesse de lecture habituelle. |
| **accélérée** | Traversée rapide. |
| **Cinéma** | La carte suit le bateau. Un zoom ou un déplacement libère la vue ; recliquer recentre. |
| **Plein écran film** | Cache les panneaux : la carte prend tout l’écran. Échap ou recliquer les rend. |
| **Stop auto** | En marche : pause à chaque escale. Éteint : on traverse les escales. |
| **Masquer la barre** | Replie la barre du bas. |
| **Demander conseil** | Propose un autre trait jusqu’à la prochaine escale, sous vos limites. |
| **Garder searoute** | Garde le trait actuel. |
| **Accepter** | Remplace le trait de cette étape par le trait proposé. |
| **Escales** (liste) | Un clic sur un nom va à cette escale. |

Les calques, le briefing, le journal et **Revoir l’expédition**
restent les mêmes qu’en Suivre.

---

## 3. Tracer ma route

Vous dessinez une route. Le briefing parle **de cette route**,
pas de Berry-Mappemonde.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Tracer votre propre route** | Passe en dessin : chaque clic sur la mer pose un point. |
| **Terminer** | Ferme le tracé et lance le briefing de cette route. |
| **Annuler le dernier point** | Enlève le dernier point posé. |
| **Importer** | Charge un fichier GeoJSON ou KML (points ou ligne) comme waypoints. |
| **Continuer le tracé** | Rajoute des points à une route déjà terminée. |
| **Supprimer la route** | Efface la route dessinée. |
| **Revenir à la route Berry-Mappemonde** | Quitte le dessin et reprend la route officielle. |

Si une route est déjà là, **Importer** demande
**Remplacer la route en cours ?** — confirmer remplace, annuler garde l’ancienne.
Un fichier illisible affiche **Fichier illisible** ; rien d’autre ne change.
Au-delà de 60 points : **60 points maximum**.

---

## 4. Revoir l’expédition

Un film de la route, de Saint-Maur jusqu’à aujourd’hui, raconté à voix haute.
On le lance depuis **Suivre l’expédition**.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Revoir l’expédition** | Démarre le film. La voix mène le bateau. |
| **Stop** | Arrête le film et revient à Suivre. |
| **Plein écran film** | Cache les panneaux le temps du film. |
| **Brut** | Montre le récit écrit par les règles (sans modèle). Grisé s’il n’est pas disponible. |
| **Rédigé** | Montre le récit rédigé (Nemotron). Grisé s’il n’est pas disponible. |
| **2:30** / **3:00** | Choisit la durée du film. |

Pendant le film, une **bulle** peut sortir du bateau au moment d’un
événement (coup de vent, escale). **Fermer** range la bulle.
Les fiches d’escale ne s’ouvrent pas pendant le film.

---

## 5. Panneau droit

L’expédition et les outils. **Afficher le panneau** / **Masquer le panneau**
l’ouvre ou le replie.

| Bouton | Ce qu’il fait |
|--------|----------------|
| **Langue** | Passe l’interface en français ou en anglais. |
| **Sombre** / **Clair** | Change le thème de la carte et des panneaux. |
| **Voir** / **Masquer** (polaires) | Ouvre ou ferme le tableau des polaires. |
| **Glissez un fichier** | Charge une polaire (PDF, CSV ou XLSX) à la place de la polaire par défaut. |
| **Revue du plan** | Liste les étapes avec ce qu’il faut surveiller (vent, couloirs de cargos…). |
| **Appliquer** | Applique le conseil de date ou de corridor proposé pour une étape. |
| **Fiche d’escale** | Ouvre la fiche du port (services, formalités, sources). Un clic sur le drapeau de l’escale fait la même chose. |
| **GeoJSON** | Télécharge la route de l’écran (Berry, simulation ou tracé). |
| **KML** | Télécharge la même route au format KML. |
| **Côtier** / **Croisière** / **Large** | Choisit le caractère du skipper (limites de vent et de mer). |
| **Revenir aux ordres Berry** | Remet les limites de l’expédition. |
| **Demander conseil** | Même action qu’en Simulation : un autre trait jusqu’à la prochaine escale. |
| **Paramètres avancés** | Ouvre ou ferme les réglages détaillés (chiffres du skipper). |
| **OK** (clé admin) | Enregistre la clé dans ce navigateur seulement (modifier la route officielle, le GRIB ou la polaire). |

Le **résumé route** n’est pas un bouton : il affiche le nombre d’étapes,
d’escales et la distance. Une pastille peut nommer un **couloir** de cargos
traversé ; le trait sur la carte ne bouge pas.

---

## Ce que l’application ne fait pas

Ce n’est **pas** une carte marine, **pas** un GPS, **pas** un chatbot
qui invente. Un champ vide veut dire : on ne sait pas. Le vent de
l’atlas est celui d’un mois typique, pas celui de demain.

# Routine Grok Bot — pré-revue visuelle de nuit (à coller dans Grok Bot)

Grok Bot tourne sur un ordinateur cloud avec un navigateur : il ne voit pas
`localhost`. `run_lots.py` ouvre un **tunnel Cloudflare** vers le poste de recette du
Mac et poste dans chaque PR un commentaire « 🔗 Poste de recette : <url> » avec la
consigne ci-dessous.

**Il faut un tunnel nommé sur ton domaine** (21 sept.) : sur un tunnel rapide
`trycloudflare.com`, Cloudflare bloque le navigateur automatisé du bot (403 « Your
request was blocked ») alors que le HTTP simple passe. Sur `recette.blueintelligence.online`
(`naviguide.fr` est chez OVH, hors Cloudflare : seule la zone `blueintelligence.online`
peut porter le tunnel), le bot est traité comme sur un site normal. Mise en place, **une fois**,
dans le Terminal du Mac (la 1ʳᵉ commande ouvre le navigateur : choisir la zone
`blueintelligence.online`) :

```bash
cloudflared tunnel login
cloudflared tunnel create recette
cloudflared tunnel route dns recette recette.blueintelligence.online
printf 'BIM_TUNNEL_NAME=recette\nBIM_TUNNEL_HOST=recette.blueintelligence.online\n' >> ~/.config/naviguide/simulator.env
python3 infra/agents/run_lots.py --stop-tunnel && python3 infra/agents/run_lots.py --recette
```

Le dernier appel rebâtit le poste (preview autorise `recette.blueintelligence.online`), ouvre
le tunnel nommé et re-poste le lien 🔗 dans chaque PR. Si le bot voit encore un
403 : dans Cloudflare → Sécurité → WAF → règle personnalisée « hôte =
recette.blueintelligence.online → Ignorer (Skip) : Bot Fight Mode, niveau de sécurité ».

Option `--publish-tip` : le lien devient le site publié lui-même (la tête de pile est
déployée sur `simulator.naviguide.fr` via la branche `recette`) — à réserver au
moment où le dépôt public du simulateur sera la source du déploiement.

Grok Bot a besoin du **connecteur GitHub** (lire les PR, cocher, commenter) :
accepter sa proposition « Oui, ajoute GitHub ».

Le bot **coche les mêmes cases que le porteur** quand il a vérifié, et **liste ce
qu'il a coché** dans son commentaire : c'est cette liste qui dit « coché par le
bot ». Le matin, le porteur relit : il décoche ce qu'il conteste et écrit
« KO : … » ; ce qu'il laisse coché vaut accord.

## Texte de la routine (français ; le bot lit aussi les PR en anglais)

**Ordre de la nuit** : Grok Bot passe **avant** le réviseur de code. Après chaque
tranche de PR, `run_lots.py` attend son commentaire « 🤖 Pré-revue » (au plus
45 min, `--bot-wait-min`) puis lance le réviseur Grok CLI, qui reçoit les KO du bot
dans son prompt (« où chercher dans le code »). D'où la fréquence de la routine :
**toutes les 30 min la nuit**, sur les PR qui ont un 🔗 et pas encore de 🤖.

```text
Toutes les 30 minutes entre 21 h et 8 h (et à la demande), pré-revue visuelle des
PR du dépôt Berry-Mappemonde/Blue-Intelligence :

1. Liste les pull requests OUVERTES dont le titre contient « (lot » et qui ont un
   commentaire commençant par « 🔗 Poste de recette » mais PAS encore de
   commentaire commençant par « ## 🤖 Pré-revue ». S'il n'y en a aucune, arrête-toi
   sans rien poster. Sinon traite-les dans l'ordre croissant des numéros, au plus 3
   par passage (les autres au passage suivant). Utilise le lien 🔗 le plus récent
   de la PR (un nouveau tunnel = un nouveau lien).
2. Pour chaque PR : ouvre le lien du commentaire 🔗 dans le navigateur (c'est la
   tête de pile, build de prod, clés chargées ; recharge si la page tarde). Lis la
   rubrique « Recette » du corps de la PR : chaque case `- [ ] …` est une étape
   « ouvre …, clique … → tu dois voir … » (FR / EN sur la même ligne).
3. Pour chaque case : fais l'étape dans l'application, à l'écran indiqué (Suivre,
   Simulation, Tracer ma route, Revoir l'expédition, panneau droit), **la console
   du navigateur ouverte** (F12 / ⌥⌘J). Si tu VOIS exactement ce qui est attendu :
   coche la case dans la PR. Sinon : laisse-la vide. Prends une capture pour chaque
   défaut. Note toute **erreur rouge de console** (exception JS, appel `/ici`,
   `/voyage`, `/route`, `/wind` en 4xx/5xx) avec l'écran où elle est apparue ;
   ignore les avertissements jaunes.
4. Poste UN commentaire par PR, qui commence par `## 🤖 Pré-revue` puis une ligne
   par case, dans l'ordre :
   - `- [x] 🤖 <texte de la case>` si tu l'as cochée ;
   - `- [ ] 🤖 <texte de la case> — KO : <écran, ce que je vois, ce que je voulais>`
     si tu as vu un défaut (joins la capture) ;
   - `- [ ] 🤖 <texte de la case> — non vérifiable : <pourquoi>` si tu ne peux pas
     (son, voix, fichier à choisir…) ;
   puis une ligne par erreur de console :
   - `- [ ] 🤖 Console (<écran>) — KO : <message, fichier:ligne ou URL et code HTTP>`.
   Termine par une ligne « Vu <n> / <total> · KO <k> ».
5. Ne modifie pas le texte de la PR, ne ferme ni ne merge rien, ne coche pas ce
   que tu n'as pas vu, n'invente aucun chiffre. Un seul commentaire 🤖 par PR : si
   tu repasses, édite ton commentaire au lieu d'en ajouter un.
6. **Parcours de référence** (tout tester) : quand la PR de TÊTE de la pile porte un
   commentaire « 🧭 Parcours de référence » et pas encore de commentaire
   `## 🤖 Parcours de référence`, et que toutes les PR de la pile ont leur
   `## 🤖 Pré-revue` : joue l'intégralité du parcours donné dans ce commentaire
   (A → H, console ouverte), sur le lien indiqué, et poste UN commentaire
   `## 🤖 Parcours de référence` au même format (une ligne par item, console
   comprise), terminé par « Vu n / total · KO k ». Une fois par tête de pile.
7. À la fin, envoie-moi un résumé : PR traitées, cases cochées, KO avec captures,
   erreurs de console, résultat du parcours.
```

**Pourquoi des commentaires et pas une PR du bot** : il ne code pas ; une PR
ajouterait un merge à faire pour un simple rapport ; ses commentaires entrent
déjà dans la boucle — `review_collect.py` les lit (cases cochées, KO, console,
parcours) et le correcteur du matin les traite comme les KO du porteur.

## Ce que le porteur voit le matin

Dans `infra/agents/RECETTE_DU_BATCH.md` et dans `review_collect.py` :
✅ = coché par le porteur · ✅🤖 = coché par le bot (non contredit) · ⬜ = à voir ·
🤖❌ = défaut vu par le bot (sa note suit). Le correcteur du matin (Fable) reçoit
les deux : la revue humaine fait foi, la pré-revue du bot l'éclaire.

## Sécurité du tunnel

L'URL `trycloudflare.com` est publique mais aléatoire ; l'API derrière porte les
clés (Token Factory, Tavily) et peut consommer des jetons si quelqu'un la trouve.
`python3 infra/agents/run_lots.py --stop-tunnel` l'arrête ; le tunnel ne survit
pas à un redémarrage du Mac. Passer à un tunnel nommé + Cloudflare Access (e-mail
autorisé) si l'usage se prolonge : lot W5.

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
dans son prompt (« où chercher dans le code »).

**Un seul déclencheur : le webhook** (depuis le 24 sept. ; le porteur a retiré
« commentaire de PR » et le minuteur de repli — un réveil de trop coûtait un
passage à vide, et le minuteur faisait doublon avec le réveil par PR) :

- **Webhook** : l'URL exposée par la routine est dans
  `~/.config/naviguide/simulator.env` : `BIM_BOT_WEBHOOK=https://…` —
  `run_lots.py` l'appelle (POST JSON `{event: prereview|parcours|ping, pr, url}`) :
  `prereview` juste après chaque commentaire 🔗 (un réveil par PR, le bot ne traite
  que celle-là), `parcours` après le 🧭 de fin de batch sur la PR de tête, `ping` au
  pré-vol (`run_lots.py --preflight`) pour vérifier URL et clé — la routine l'ignore
  (étape 0). Le chien de garde (`watchdog.py`) renvoie un `prereview` si une PR n'a
  toujours pas de 🤖 trente minutes après son 🔗. Sans minuteur, **un réveil manqué
  n'est rattrapé que par lui** : le pré-vol refuse donc de partir si le webhook
  répond 401/403.
  Si Grok Bot donne aussi une clé et un en-tête
  (22 sept.) : `BIM_BOT_WEBHOOK_TOKEN=<clé>` et `BIM_BOT_WEBHOOK_HEADER=<nom de
  l'en-tête>` (défaut `Authorization`, envoyé en `Bearer <clé>`). Écrire ces lignes
  sans les faire transiter par un chat : coller la commande `printf 'BIM_BOT_WEBHOOK=%s\n'
  "$(pbpaste)" >> ~/.config/naviguide/simulator.env` dans le Terminal sans Entrée, copier
  la valeur, revenir, Entrée. Le fichier doit être en `chmod 600`.
- **Ni minuteur ni événement GitHub** : retirés le 24 sept. Un lancement à la main
  de la routine (sans message webhook) vaut balayage : toutes les PR avec 🔗 et sans
  🤖 (étape 1, dernier cas).

```text
Tu es réveillé par un webhook. Son message JSON dit ce qu'on attend de toi : `"event"`
(`ping`, `prereview` ou `parcours`), `"pr"` (numéro de la pull request) et `"url"` (le poste
de recette). Pré-revue visuelle des PR du dépôt Berry-Mappemonde/Blue-Intelligence — UNE PR
À LA FOIS :

0. `"event": "ping"` : c'est un test de branchement — arrête-toi sans rien faire ni poster.
1. Choisis ta cible :
   - `"event": "prereview"` avec `"pr"` : traite UNIQUEMENT cette PR, même si d'autres
     attendent (un autre réveil s'en occupe : ils arrivent un par un, et plusieurs de tes
     passages peuvent tourner en même temps sans se gêner) ;
   - `"event": "parcours"` avec `"pr"` : c'est la PR de TÊTE en fin de batch → étape 6 ;
   - pas de message, ou message sans `"pr"` (lancement à la main) : liste les pull
     requests OUVERTES dont le titre contient « (lot » et qui ont un commentaire
     commençant par « 🔗 Poste de recette » mais PAS encore de commentaire commençant
     par « ## 🤖 Pré-revue », et traite-les toutes, dans l'ordre croissant des numéros,
     en postant le commentaire de chacune dès qu'elle est finie.
   S'il n'y a rien à traiter, arrête-toi sans rien poster. Utilise le lien 🔗 le plus
   récent de la PR (un nouveau tunnel = un nouveau lien).
2. Pour chaque PR : ouvre le lien du commentaire 🔗 dans le navigateur (c'est la
   tête de pile, build de prod, clés chargées) et **recharge complètement la page
   en commençant chaque PR** (⇧⌘R / Ctrl+Shift+R) : le poste change de build à
   chaque lot et une page déjà ouverte garde l'ancien (22 sept., #290 : le bot a
   jugé « Recalculer l'itinéraire » sur une page chargée avant le build qui disait
   « Demander conseil »). Recharge aussi si la page tarde. Si la page ou l'API
   répond 5xx (502, 503…), ce n'est pas une panne : le poste se rebâtit pendant
   quelques secondes après chaque lot — attends 60 s et réessaie, deux fois au
   plus, avant de conclure « poste inaccessible ». Lis la
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
6. **Parcours de référence** (tout tester) — réveil `"event": "parcours"` : la PR
   `"pr"` est la TÊTE de la pile et porte un commentaire « 🧭 Parcours de référence ».
   Si elle a déjà un commentaire `## 🤖 Parcours de référence`, arrête-toi. Sinon :
   d'abord, s'il reste des PR de la pile avec 🔗 et sans `## 🤖 Pré-revue`, fais leur
   pré-revue (étapes 2 à 5) ; puis joue l'intégralité du parcours donné dans le
   commentaire 🧭 (A → H, console ouverte, page rechargée), sur le lien indiqué, et
   poste UN commentaire `## 🤖 Parcours de référence` au même format (une ligne par
   item, console comprise), terminé par « Vu n / total · KO k ». Une fois par tête.
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

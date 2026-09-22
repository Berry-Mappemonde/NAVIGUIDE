# Routine Grok Bot — pré-revue visuelle de nuit (à coller dans Grok Bot)

Grok Bot tourne sur un ordinateur cloud avec un navigateur : il ne voit pas
`localhost`. Par défaut, `run_lots.py` ouvre un **tunnel Cloudflare** vers le poste
de recette du Mac (`cloudflared`, URL `https://….trycloudflare.com`) et poste dans
chaque PR un commentaire « 🔗 Poste de recette : <url> » avec la consigne ci-dessous.
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

```text
Chaque soir à 23 h (et à la demande), pré-revue visuelle des PR du dépôt
Berry-Mappemonde/Blue-Intelligence :

1. Liste les pull requests OUVERTES dont le titre contient « (lot » et qui ont un
   commentaire commençant par « 🔗 Poste de recette ». Traite-les dans l'ordre
   croissant des numéros.
2. Pour chaque PR : ouvre le lien du commentaire 🔗 dans le navigateur (c'est la
   tête de pile, build de prod, clés chargées ; recharge si la page tarde). Lis la
   rubrique « Recette » du corps de la PR : chaque case `- [ ] …` est une étape
   « ouvre …, clique … → tu dois voir … » (FR / EN sur la même ligne).
3. Pour chaque case : fais l'étape dans l'application, à l'écran indiqué (Suivre,
   Simulation, Tracer ma route, Revoir l'expédition, panneau droit). Si tu VOIS
   exactement ce qui est attendu : coche la case dans la PR. Sinon : laisse-la
   vide. Prends une capture pour chaque défaut.
4. Poste UN commentaire par PR, qui commence par `## 🤖 Pré-revue` puis une ligne
   par case, dans l'ordre :
   - `- [x] 🤖 <texte de la case>` si tu l'as cochée ;
   - `- [ ] 🤖 <texte de la case> — KO : <écran, ce que je vois, ce que je voulais>`
     si tu as vu un défaut (joins la capture) ;
   - `- [ ] 🤖 <texte de la case> — non vérifiable : <pourquoi>` si tu ne peux pas
     (son, voix, fichier à choisir…).
   Termine par une ligne « Vu <n> / <total> · KO <k> ».
5. Ne modifie pas le texte de la PR, ne ferme ni ne merge rien, ne coche pas ce
   que tu n'as pas vu, n'invente aucun chiffre. Un seul commentaire 🤖 par PR : si
   tu repasses, édite ton commentaire au lieu d'en ajouter un.
6. À la fin, envoie-moi un résumé : PR traitées, cases cochées, KO avec captures.
```

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

# Routine Grok Bot — Devpost : relever, remplir, filmer (à coller dans Grok Bot)

Complément de `GROK_BOT_ROUTINE.md` (pré-revue de nuit). Même bot, même connecteur GitHub.
Point d'échange : l'issue
**https://github.com/Berry-Mappemonde/Blue-Intelligence/issues/432**. Le bot ne clique **jamais** sur
Submit : il relève, il recopie dans le brouillon, il filme, il montre. Le porteur soumet.

Textes à coller : `docs/HACKATHON_DEVPOST_SOUMISSION.md`. Chaîne Mac : `infra/agents/devpost_answers.py`.

---

## Session Devpost (Chrome du porteur)

Grok Bot tourne sur un **ordinateur cloud**. Son navigateur n'est **pas** Chrome du Mac : les cookies
de `chrome://` sur le Mac sont invisibles pour lui. Il n'existe **pas** de pont sûr (pas de tunnel
vers le port de débogage Chrome : ce serait donner la session à n'importe qui).

Ce que prévoit ce document :

1. Le bot ouvre la page de connexion Devpost **dans son navigateur à lui** (session persistante
   sur la machine cloud).
2. Le porteur se connecte **une fois** dans cette fenêtre (le bot s'arrête et écrit sur #432
   « connecte-toi, puis dis OK »). Aucun mot de passe ne transite par GitHub ni par le webhook.
3. Les tâches A et B reprennent sur cette session. Une seule soumission active : ne crée pas
   un second projet.

Si le porteur ne peut pas ouvrir le navigateur du bot : les tâches A/B s'arrêtent après le
message « session absente ». Ne pas inventer les champs. Ne pas demander un export de cookies.

La tâche C (app, anglais, Rédigé, Revoir, captures, vidéo) n'a **pas** besoin de Devpost :
elle utilise le poste de recette (`recette.blueintelligence.online` / le lien 🔗 de la PR de tête).

---

## Texte de la routine (français ; Devpost est en anglais)

### Tâche A — « devpost_scrape » : relever le formulaire, les règles, les critères

1. Ouvre le brouillon de soumission du projet NAVIGUIDE sur Devpost (hackathon Nebius × NVIDIA Global AI
   Hackathon), onglet par onglet : **Project overview**, **Project details**, **Additional info**, et toute
   autre page du formulaire (galerie, vidéo, équipe). Ouvre aussi la page **Rules** et la page **Judging
   criteria** du hackathon.
2. Pour **chaque champ** du formulaire, relève : le libellé exact (anglais), le type (texte court, texte long /
   Markdown, nombre, case unique, cases multiples, menu déroulant, fichier, URL), obligatoire ou non, la limite
   de caractères si affichée, l'aide sous le champ si elle existe, et la **valeur actuelle du brouillon**
   (texte intégral, ou la liste des options déjà cochées).
3. Pour chaque case à cocher, menu déroulant ou choix multiple : la **liste complète des options, mot pour mot**,
   dans l'ordre affiché. Ne résume pas, ne traduis pas.
4. Copie le texte des **règles** (au minimum : éligibilité, exigences techniques — ex. appel runtime à Nebius
   Token Factory avec un modèle NVIDIA open source —, livrables exigés, dates limites, contraintes sur la
   vidéo, la licence, le dépôt, la langue) et le texte des **critères de jugement** avec leurs pondérations
   si elles sont données. Garde les URL.
5. Poste UN commentaire sur l'issue #432, titre **« 📋 Formulaire Devpost relevé — <date> »**, en trois parties
   lisibles (Formulaire · Règles · Critères) puis un bloc ```json qui suit exactement ce schéma :

```json
{
  "kind": "devpost_form",
  "scrapedAt": "2026-10-02T18:00:00Z",
  "urls": {"submission": "…", "rules": "…", "judging": "…"},
  "fields": [
    {"tab": "Project overview", "label": "Project name", "type": "text", "required": true, "maxChars": 60,
     "help": "…", "current": "…", "options": []},
    {"tab": "Additional info", "label": "Track", "type": "select", "required": true, "maxChars": null,
     "help": "", "current": "Best apps and agents",
     "options": ["Best apps and agents", "…", "…"]}
  ],
  "rules": [{"title": "Eligibility", "text": "…"}, {"title": "Technical requirements", "text": "…"}],
  "judging": [{"criterion": "Technological Implementation", "weight": null, "text": "…"}]
}
```

6. Si une page refuse de s'ouvrir (connexion perdue, 403), dis-le dans le commentaire au lieu de deviner :
   « non relevé : <page> — <raison> ». Aucune capture d'écran n'est nécessaire à cette étape.

### Tâche B — « devpost_fill » : recopier les réponses dans le brouillon

Déclenchée quand l'issue #432 porte un commentaire **« ✍️ Réponses proposées »** plus récent que le dernier
« 📝 Brouillon rempli » (ou par le webhook `devpost_fill`).

1. Lis le bloc ```json du dernier commentaire « ✍️ » : `answers` = une entrée par champ
   (`label`, `tab`, `value` ou `selected` pour les options).
2. Sur le brouillon Devpost, champ par champ, dans l'ordre des onglets : remplace la valeur par `value`
   (texte intégral, Markdown accepté dans « About the project ») ; pour un choix, coche / sélectionne
   **exactement** l'option `selected` (même orthographe) ; si l'option n'existe pas telle quelle, ne coche
   rien et note-le. Ne touche pas aux fichiers (miniature, galerie, vidéo) : note ce qu'il faudrait changer
   (la tâche C fournit les captures et le fichier vidéo).
3. **Sauvegarde le brouillon** (« Save » / « Save draft »). **Ne clique jamais sur Submit**, ni sur un bouton
   qui rend la soumission publique.
4. Recharge la page et vérifie que chaque champ porte bien la valeur ; prends **une capture par onglet**.
5. Poste UN commentaire sur l'issue #432, titre **« 📝 Brouillon rempli — à vérifier — <date> »** : la liste
   des champs modifiés (ancienne → nouvelle valeur, tronquée à 200 caractères), les options cochées, ce qui
   n'a pas pu être fait et pourquoi, les captures. Termine par « Rien soumis : le porteur soumet. »

### Tâche C — « devpost_demo » : anglais, Rédigé, Revoir, captures, vidéo

Déclenchée par le webhook `devpost_demo` ou à la demande du porteur. **Pas besoin de Devpost.**
Poste de recette : le lien 🔗 de la PR de tête, ou `https://recette.blueintelligence.online`.

Plan de tournage (règles du hackathon : vidéo YouTube publique < 3 min, app en anglais) :
`docs/HACKATHON_DEVPOST_SOUMISSION.md` § 2.

1. Ouvre le poste. Bascule **EN** (sélecteur de langue). Clique **Follow the expedition** / Suivre.
2. Clique **Rédigé** (Written) s'il est là — l'étiquette sous le texte doit dire
   « Nemotron 3 Super · Token Factory » (ou Lightning). Si l'étiquette manque, note-le : ne pas inventer.
3. Clique **Replay the expedition** / Revoir l'expédition. Plein écran si le bouton existe (lot F5).
   Pilule **2:30** si elle est là. Laisse tourner jusqu'à ~2 min 05 (la pilule peut encore durer plus
   que 150 s tant que RC27 n'est pas passé : coupe avant 3 min).
4. Cinq captures 3:2, app en anglais, postées sur #432 :
   1. Follow, position du jour, une carte NOW
   2. Film à mi-parcours (bulle d'événement si elle apparaît)
   3. Fiche d'escale
   4. Revue du plan (onglet Review)
   5. Draw your own route (deux points au large)
5. Enregistre la fenêtre (écran de l'app seulement, pas le bureau du bot) : fichier < 3 min,
   sans musique protégée. La voix est celle de l'app (`speechSynthesis`). Si le navigateur cloud
   n'émet pas le son, le fichier est muet : le dire clairement sur #432 ; ne pas inventer une voix
   ni ajouter une musique. Le porteur pourra alors tourner le son sur le Mac (OBS, son système).
6. N'upload **pas** sur YouTube sauf si une session YouTube est déjà ouverte dans le navigateur
   du bot. Sinon : dépose le fichier (lien, pièce, ou chemin) sur #432.
7. Poste UN commentaire **« 🎬 Démo — captures + vidéo — <date> »** : les 5 captures, le fichier
   ou son lien, ce qui a manqué (étiquette Nemotron, son, 2:30 trop long).

### Règles du bot

- Langage simple, phrases courtes ; jamais de jargon interne dans ce qui va sur Devpost.
- Aucun identifiant, aucune clé, aucun mot de passe dans un commentaire, un fichier ou un journal.
- Une seule soumission active : ne crée pas de second projet Devpost.
- Si un doute (quel projet, quel hackathon, une option ambiguë) : pose la question dans l'issue et arrête-toi.
- Tâches A/B : captures d'onglets Devpost. Tâche C : captures d'app + vidéo de l'app. Jamais Submit.

---

## Côté Mac : l'agent entre les deux (`infra/agents/devpost_answers.py`)

```bash
cd ~/Blue-Intelligence-Map
python3 infra/agents/devpost_answers.py --wake-scrape      # réveille le bot : tâche A
python3 infra/agents/devpost_answers.py                    # lit le dernier 📋, lance l'agent, poste ✍️ (+ PR docs)
python3 infra/agents/devpost_answers.py --wake-fill        # réveille le bot : tâche B
python3 infra/agents/devpost_answers.py --wake-demo        # réveille le bot : tâche C (anglais, Rédigé, Revoir, vidéo)
python3 infra/agents/devpost_answers.py --dry-run          # affiche le prompt sans rien lancer
```

Le prompt exige : le champ « existing project — how significantly updated since August 26 » commence par le chiffre mesuré dans git (`python3 infra/agents/devpost_code_share.py`), langage simple avant technique, options recopiées mot pour mot, une table de conformité aux règles avec preuve (fichier:ligne, URL), une analyse des critères, et l'honnêteté (aucune fonctionnalité annoncée qui ne tourne pas en production). Depuis le 15 oct. la veille Tavily est **rallumée** (une recherche par escale, une fois) : « Did you use Tavily? » = Yes seulement après déploiement de cette veille et un appel visible dans `/ici/warm/status` (`llm.tavily`). Le juge Ultra reste coupé sauf `NAVIGUIDE_TRUTH_JUDGE=1`.

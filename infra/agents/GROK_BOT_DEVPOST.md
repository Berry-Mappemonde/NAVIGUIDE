# Routine Grok Bot — Devpost : relever le formulaire, remplir le brouillon (à coller dans Grok Bot)

Complément de `GROK_BOT_ROUTINE.md` (pré-revue de nuit). Même bot, même connecteur GitHub, deux
tâches de plus, déclenchées par le webhook (`event: devpost_scrape` et `event: devpost_fill`) ou à la
demande du porteur. Point d'échange : l'issue
**https://github.com/Berry-Mappemonde/Blue-Intelligence/issues/432**. Le bot ne clique **jamais** sur
Submit : il relève, il recopie dans le brouillon, il montre. Le porteur soumet.

Le porteur doit s'être connecté à Devpost **une fois** dans le navigateur du bot (session persistante) ;
aucun identifiant ne transite par GitHub ni par le webhook.

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
   rien et note-le. Ne touche pas aux fichiers (miniature, galerie, vidéo) : note ce qu'il faudrait changer.
3. **Sauvegarde le brouillon** (« Save » / « Save draft »). **Ne clique jamais sur Submit**, ni sur un bouton
   qui rend la soumission publique.
4. Recharge la page et vérifie que chaque champ porte bien la valeur ; prends **une capture par onglet**.
5. Poste UN commentaire sur l'issue #432, titre **« 📝 Brouillon rempli — à vérifier — <date> »** : la liste
   des champs modifiés (ancienne → nouvelle valeur, tronquée à 200 caractères), les options cochées, ce qui
   n'a pas pu être fait et pourquoi, les captures. Termine par « Rien soumis : le porteur soumet. »

### Règles du bot pour ces deux tâches

- Langage simple, phrases courtes ; jamais de jargon interne dans ce qui va sur Devpost.
- Aucun identifiant, aucune clé, aucun mot de passe dans un commentaire, un fichier ou un journal.
- Une seule soumission active : ne crée pas de second projet Devpost.
- Si un doute (quel projet, quel hackathon, une option ambiguë) : pose la question dans l'issue et arrête-toi.
- Pas de vidéo, pas d'enregistrement d'écran : des captures fixes seulement.

---

## Côté Mac : l'agent Fable entre les deux (`infra/agents/devpost_answers.py`)

```bash
cd ~/Blue-Intelligence-Map
python3 infra/agents/devpost_answers.py --wake-scrape      # réveille le bot : tâche A
python3 infra/agents/devpost_answers.py                    # lit le dernier 📋, lance Fable, poste ✍️ (+ PR docs)
python3 infra/agents/devpost_answers.py --wake-fill        # réveille le bot : tâche B
python3 infra/agents/devpost_answers.py --dry-run          # affiche le prompt Fable sans rien lancer
```

Le prompt Fable exige : langage simple avant technique, options recopiées mot pour mot, une table de
conformité aux règles avec preuve (fichier:ligne, URL), une analyse des critères, et l'honnêteté (aucune
fonctionnalité annoncée qui ne tourne pas en production — ex. Tavily et le juge Ultra sont coupés par défaut
depuis le 29 sept. : la réponse « Did you use Tavily? » doit dire ce qui est vrai le jour de la soumission).

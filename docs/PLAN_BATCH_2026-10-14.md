# Batch 2 — plan du 14 octobre 2026 (après la pile « film 1 + deux modes » #444 mergée)

Source : la revue orale du porteur du 14 octobre (`docs/REVUE_PORTEUR_2026-10-14.md`) et les constats du chat de
pilotage des 29-30 septembre (position du bateau non déterministe, cache ERA5 orphelin, incident du voyage officiel).
Ce plan remplace `docs/PLAN_BATCH_SUIVANT_2026-09-29.md` (dont il reprend AM1, RG18, RG19, RG20, DM3).
Les prompts complets sont dans `docs/LOTS_ORDRE_ET_PROMPTS.md`, section « Batch 2 ».

## 1. L'ordre et pourquoi

| # | Lot | Modèle | Taille | Ce que le porteur verra |
|---|---|---|---|---|
| 1 | **HC1** — position vraie : passé en météo réelle (ERA5 téléchargé une fois), horloge déterministe | Fable | L | Le bateau est là où la météo réelle l'a mené ; recharger ne le déplace plus ; route parcourue turquoise (réel) puis violette (climatologie) ; plus de quota Open-Meteo brûlé |
| 2 | **DM4** — accueil et retour en Suivre : bateau au milieu, monde dézoomé | Grok | S | À l'ouverture, le bateau au centre de l'écran, le monde autour |
| 3 | **DM5** — Suivre suit la route que je viens de tracer ; une seule route à l'écran ; pilules Berry \| ma route | Fable | L | Tracer → Terminer → Suivre : ma route, seule, le bateau dessus, date de départ au choix |
| 4 | **DM6** — Tracer : on arrive sur le dessin ; la pilule Berry affiche la route Berry sans jeter le brouillon | Grok | M | « Choisissez votre point de départ » tout de suite ; aller-retour Berry ↔ mon tracé sans rien perdre |
| 5 | **DM7** — Tracer : la lecture part d'aujourd'hui ; l'encadré suit le bateau du tracé | Grok | S | Play part le jour de la connexion ; plus de fiche Papeete quand le bateau est à Saint-Maur ; champ Date de départ en Suivre seulement |
| 6 | **DM9** — Tracer : encadré gauche (Revue du plan + Récit seulement) et panneau droit (Polaires, Paramètres repliés) | Grok | S | Les panneaux de Tracer servent le tracé ; Suivre intact |
| 7 | **UI1** — barre de mentions légales posée au-dessus de la barre film, même hauteur que le zoom | Grok | S | Plus de chevauchement ; une seule hauteur pour la barre et les boutons + / − |
| 8 | **RC30** — film : chronologie stricte eaux / climatologie, phrases jamais coupées, clôture entière | Fable | M | Gascogne → eaux espagnoles → portugaises → Gibraltar → marocaines ; plus de phrase coupée aux escales ; « Aujourd'hui, le bateau est… » jusqu'au bout |
| 9 | **RC31** — film : l'épisode Saint-Pierre-et-Miquelon (deux vols, second bateau, catamaran à quai à Cayenne) | Fable | M | L'aller-retour Halifax ↔ Saint-Pierre raconté comme il s'est passé, trace du second bateau distincte |
| 10 | **RC32** — toponymes : exonymes FR/EN pour pays et eaux, noms d'origine pour ports et aires, homonymes distingués | Grok | S | « Sint Maarten (partie néerlandaise), puis Saint-Martin (partie française) » |
| 11 | **DM8** — Suivre sur ma route : Revoir et le récit de la route que j'ai tracée | Fable | L | Je trace, Suivre me rejoue ma route et me la raconte (même moteur que le film officiel, à la demande, borné) |
| 12 | **RC27** — le 2:30 tient à 150 s (gabarit compact des ouvertures / arrivées en 2:30) | Grok | S | La pilule 2:30 dure 2:30 : c'est la source de la vidéo Devpost du 30 octobre |
| 13 | **RG11** — « Rédigé » : le film réécrit par Nemotron 3 Super depuis les faits, vérifié, servi par le stock | Fable | M | La pilule Rédigé vit : plus fluide, mêmes faits, étiquette « Nemotron 3 Super · Token Factory » — l'appel Nebius visible exigé par le hackathon |
| 14 | **AM1** — AMP croisées par polygone (base remplie : 3 769 sites) | Fable | M | « Le bateau entre dans la réserve de … » partout sur la route |
| 15 | **RG18** — une seule plume (récits sur demande) | Grok | M | Les fiches Ici parlent comme le film ; le modèle n'écrit que sur « Rédigé » |
| 16 | **RG19** — chat à trois paliers (Lightning comprend, règles répondent, Ultra raisonne) | Grok | M | Le chat répond aux faits depuis un paquet complet ; Ultra sur geste, plafonné |
| 17 | **RG20** — specs vérité (stock figé régénéré) | Grok | M | Une réserve en CI = un cas « poste » attendu, rien d'autre |
| 18 | **DM3** — le ménage des deux modes (`VIEW_TRACER`, `isTracer`…) | Fable | M | Rien à l'écran ; lancé en dernier, rien n'en dépend |

Pourquoi cet ordre : **HC1 d'abord** — la position du bateau est la donnée que tout le reste regarde (film, fourchette,
encadré Ici, AMP croisées, pré-revues du bot) ; tant qu'elle change au gré de l'atlas, aucune recette n'est
comparable d'un jour à l'autre. Puis **les deux modes** (DM4 → DM7), qui sont le cœur de la revue du porteur, du plus
simple au plus structurant ; UI1 et RC30 sont indépendants ; AM1 change les moments → avant RG20 qui régénère le stock
figé ; DM3 renomme ce que tout le monde touche → en dernier.

## 2. Décisions du porteur (14 oct. au soir)

- **RC27** : « ce qui serait bien, c'est que la vidéo du 30 octobre soit faite à partir de la vidéo de 2:30 » → dans le batch.
- **RG11** : « on le fait bien évidemment, c'est l'objet du hackathon » → dans le batch (Fable).
- Encadré gauche en Tracer : **option A** ; panneau droit : **Date masquée (DM7), Polaires et Paramètres repliés** → DM9.
- **DM8** (Revoir et récit sur ma route) : dans le batch, après RC30 (il hérite de l'ordre et des phrases entières).

- **Confirmé** : la pilule Berry affiche la route Berry et garde le brouillon ; Annuler reste l'abandon explicite (DM6).
- **Ajouts du soir** : **RC31** (épisode Saint-Pierre-et-Miquelon) et **RC32** (toponymes), après RC30.

Plus rien n'est hors batch. 18 lots : deux nuits et demie environ.

## 3. Lancer

La boucle (`infra/agents/loop.py`) est en phase **`await_go`** sur la PR GO de ce plan : **merger la PR GO lance le batch**
(ligne `LOTS: HC1 DM4 DM5 DM6 DM7 DM9 UI1 RC30 RC31 RC32 DM8 RC27 RG11 AM1 RG18 RG19 RG20 DM3` dans son corps ; tête #444 mergée → les lots partent de
`main`). Un commentaire « CORRIGER : … » sur la PR GO la fait amender avant le merge. À la main, l'équivalent :

```bash
cd ~/Blue-Intelligence-Map && git pull --ff-only origin main
python3 infra/agents/run_lots.py --from HC1 --until DM3 --review-every 4
```

Le modèle de chaque lot vient de sa balise (`model="…"`) ; les autres prennent celui du batch (Grok). Réviseur de nuit
et Grok Bot comme d'habitude (parcours de référence avant chaque revue).

## 4. Objectif du week-end (17-18 octobre) : publier la première soumission Devpost

| Quand | Quoi | Qui |
|---|---|---|
| mer. 14 soir → ven. 16 | batch 2 (18 lots, revues de nuit, pré-revues Grok Bot) | boucle |
| ven. 16 | revue du porteur sur le poste ; merge de la tête ; **déploiement en production** (`infra/vps/deploy-app.sh`, `simulator.naviguide.fr`) avec RG11 actif (NEBIUS_API_KEY sur le VPS, mode on-demand, plafond write) | porteur + chat |
| ven. 16 soir | « relève » : Grok Bot relève le formulaire Devpost (📋 sur #432) → Fable propose les réponses (✍️, PR docs) → le bot remplit le brouillon (📝) | chat + bot |
| sam. 17 | vidéo < 3 min tournée depuis la pilule 2:30 (RC27) en anglais, YouTube public ; README EN section Nemotron / Token Factory ; crédits Token Factory valides jusqu'au 15 déc. | porteur |
| sam. 17 – dim. 18 | relecture du brouillon, **Submit** | porteur |

Ensuite : mises à jour le vendredi 23 ; soumission finale le **30 octobre 10:00 PT**. Préalable à coller une fois dans Grok Bot : `infra/agents/GROK_BOT_DEVPOST.md` (si ce n'est pas déjà fait).

## 5. Coût
Fable : HC1 ≈ 500-800 k tokens, DM5 ≈ 500 k, RC30 ≈ 300 k, DM8 ≈ 600 k, RG11 ≈ 300 k, AM1 ≈ 400 k, DM3 ≈ 400 k. Nebius : RG11 génère le rédigé une fois par jour et par variante (quelques appels Super, plafonnés), c'est le seul usage payant du batch. Grok : inclus. Nebius : zéro
pendant le batch (agents en `NAVIGUIDE_LLM_MODE=off`).

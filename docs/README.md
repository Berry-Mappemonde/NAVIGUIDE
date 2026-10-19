# Index de `docs/`

Quoi lire pour quoi.

## Pour comprendre l’application

| Document | Langue | Rôle |
|----------|--------|------|
| [README.md](https://github.com/Berry-Mappemonde/NAVIGUIDE/blob/main/README.md) | EN | 5 minutes : quoi, où, comment lancer |
| [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) | FR | Chaque bouton, écran par écran |
| [USER_MANUAL.md](USER_MANUAL.md) | EN | Same, in English |
| [ESPRIT_DE_L_APPLICATION.md](ESPRIT_DE_L_APPLICATION.md) | FR | Chaîne sources → écran, pour un lecteur technique |
| [FILM_DISCOURS_ETAT_2026-09-28.md](FILM_DISCOURS_ETAT_2026-09-28.md) | FR | Le film de l’expédition : discours et état |
| [ici-tout.md](ici-tout.md) | FR | Familles autour du bateau |

## Règles et calculs

| Document | Rôle |
|----------|------|
| [REGLES_PARAMETRES.md](REGLES_PARAMETRES.md) | Seuils et constantes |
| [audits/CALCULS.md](audits/CALCULS.md) | Cahier des calculs du simulateur |
| [audits/CALCULS_ETAT_DE_L_ART.md](audits/CALCULS_ETAT_DE_L_ART.md) | Les calculs face à l’état de l’art |

## Conception

| Document | Quoi |
|----------|------|
| [PLAN_NEMOTRON_NEBIUS_TAVILY.md](PLAN_NEMOTRON_NEBIUS_TAVILY.md) | Usages des LLM (Nemotron sur Nebius Token Factory, Tavily) et budget |
| [PLAN_GLOBE_3D.md](PLAN_GLOBE_3D.md) | Globe en plus de la carte plane — pas commencé |

Audits : [`audits/`](audits/). Captures de recette : [`recette/`](recette/).

## Vérifier les liens

```bash
python3 docs/check_md_links.py
```

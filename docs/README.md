# Index de `docs/`

Quoi lire pour quoi. Les plans **terminés** sont dans
[`archives/`](archives/) (bandeau en tête, rien n’est supprimé).
Les audits PoE restent à la racine de `docs/` et dans `data/` :
le backend les cite encore (décision du lot D0, 22 sept. 2026).

Le découpage cible `plans/` · `hackathon/` · `cdc/`
(`ETAT_DES_LIEUX_DOCS.md` § 3) n’est **pas** fait ici : les prompts
des agents citent encore `docs/PLAN_*.md`.

## Pour comprendre l’application

| Document | Langue | Rôle |
|----------|--------|------|
| [../README.md](../README.md) | FR puis EN | 5 minutes : quoi, où, comment lancer |
| [MANUEL_UTILISATEUR.md](MANUEL_UTILISATEUR.md) | FR | Chaque bouton, écran par écran |
| [USER_MANUAL.md](USER_MANUAL.md) | EN | Same, in English |
| [ESPRIT_DE_L_APPLICATION.md](ESPRIT_DE_L_APPLICATION.md) | FR | Chaîne sources → écran, pour un jury technique |
| [HACKATHON_DEVPOST_SOUMISSION.md](HACKATHON_DEVPOST_SOUMISSION.md) | EN (textes jury) | Soumission Devpost, Nemotron / Token Factory / Tavily |

## Fait

Plans réalisés, rangés dans [`archives/`](archives/).

| Document | Quoi |
|----------|------|
| [PLAN_LOTS_AGENT_SIMULATEUR.md](archives/PLAN_LOTS_AGENT_SIMULATEUR.md) | Lots P → K, tous mergés |
| [PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md](archives/PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md) | v2 gelé (décisions du 18 sept.) |
| [PLAN_UI_PRODUIT_SIMULATEUR.md](archives/PLAN_UI_PRODUIT_SIMULATEUR.md) | Lots UI 1–9 |
| [PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md](archives/PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md) | S1 → S5, S7 |
| [PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md](archives/PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md) | Juge NOW/FREE, récit, StoryJob |
| [PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md](archives/PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md) | Les deux modes |
| [PLAN_IMPLEMENTATION_SIMULATION_A.md](archives/PLAN_IMPLEMENTATION_SIMULATION_A.md) | Horloge climatologique |
| [PLAN_IMPLEMENTATION_SIMULATION_B.md](archives/PLAN_IMPLEMENTATION_SIMULATION_B.md) | Bateau virtuel |
| [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md) | Étape 1 (FR) |
| [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md](archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md) | Étape 1 (EN) |
| [PLAN_IMPLEMENTATION_CLIMATOLOGIE.md](archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md) | Atlas climatologique BI |
| [PLAN_IMPLEMENTATION_FILIERES_CARTO.md](archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md) | Filières carte / hydro / satellite |
| [PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md](archives/PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md) | Pipeline d’affichage (P1 GRIB `pending`) |
| [PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md](archives/PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md) | Pointeur, fusionné dans le pipeline |
| [hackathon-nebius-nvidia.md](archives/hackathon-nebius-nvidia.md) | Cahier 13–14 sept. — remplacé |
| [hackathon-nebius-nvidia.en.md](archives/hackathon-nebius-nvidia.en.md) | Idem, anglais |
| [HACKATHON_OPEN_AGENT_2026.md](archives/HACKATHON_OPEN_AGENT_2026.md) | Autre hackathon |
| [nvidia-llm-audit.md](archives/nvidia-llm-audit.md) | Replis NIM — remplacé par la cascade L1 |

## En cours

Plans encore ouverts (des lots sont faits, d’autres non).

| Document | État |
|----------|------|
| [LOTS_ORDRE_ET_PROMPTS.md](LOTS_ORDRE_ET_PROMPTS.md) | Ordre et prompts de tous les lots |
| [REGLES_WORKFLOW_AGENT.md](REGLES_WORKFLOW_AGENT.md) | Règles branches / PR / recette |
| [PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md](PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md) | Revue 19–20 sept. (S, T, U…) |
| [PLAN_FILM_REVOIR_EXPEDITION.md](PLAN_FILM_REVOIR_EXPEDITION.md) | Film F1–F5 |
| [PLAN_NEMOTRON_NEBIUS_TAVILY.md](PLAN_NEMOTRON_NEBIUS_TAVILY.md) | Cascade L1–L6 |
| [PLAN_AUDIT_CALCULS.md](PLAN_AUDIT_CALCULS.md) | Calculs C1–C7 |
| [PLAN_ICI_JOURNAL_EXPERT.md](PLAN_ICI_JOURNAL_EXPERT.md) | Encadré ici, journal, expert (R8–R10) |
| [PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md](PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md) | Import / export / trafic / piraterie (N1–N4) |
| [PLAN_CORRECTIONS_REVUE_21_SEPT.md](PLAN_CORRECTIONS_REVUE_21_SEPT.md) | Corrections R1–R13 |
| [PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md](PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md) | Corrections RA1–RA8 |
| [PLAN_CORRECTIONS_2026-09-22.md](PLAN_CORRECTIONS_2026-09-22.md) | Corrections RB1–RB8 |
| [WORKFLOW_INDUSTRIEL.md](WORKFLOW_INDUSTRIEL.md) | Calendrier jusqu’à la soumission |
| [ETAT_DES_LIEUX_DOCS.md](ETAT_DES_LIEUX_DOCS.md) | Rôle de chaque document, mémoire § 2 |

## À venir

| Document | Quoi |
|----------|------|
| [PLAN_GLOBE_3D.md](PLAN_GLOBE_3D.md) | Globe (G0–G7) — pas commencé |
| [HACKATHON_DEVPOST_SOUMISSION.md](HACKATHON_DEVPOST_SOUMISSION.md) | 1ʳᵉ soumission le 28 sept. ; vidéo à tourner |
| [WORKFLOW_INDUSTRIEL.md](WORKFLOW_INDUSTRIEL.md) § 4 | Lot H1 : séparation des dépôts (après D0) |

Mémoire (noté, pas implémenté) : [ETAT_DES_LIEUX_DOCS.md](ETAT_DES_LIEUX_DOCS.md) § 2
— ordre vocal, page carnet, confort skipper, conseil de route en Suivre,
houle climatologique, compte utilisateur, onglet Globe.

## Références produit (Blue Intelligence)

| Document | Rôle |
|----------|------|
| [PRD.md](PRD.md) | Produit BI |
| [CAHIER_DES_CHARGES_POE.md](CAHIER_DES_CHARGES_POE.md) | Ports d’entrée |
| [CAHIER_DES_CHARGES_PROJETS.md](CAHIER_DES_CHARGES_PROJETS.md) | Projets marins |
| [CAHIER_DES_CHARGES_REVIEW.md](CAHIER_DES_CHARGES_REVIEW.md) | Onglet Review |
| [CONTRATS_MODES.md](CONTRATS_MODES.md) · [CONTRATS_REVIEW_PAR_MODE.md](CONTRATS_REVIEW_PAR_MODE.md) | Contrats des 7 modes |
| [CATALOGUE_SEAMARK.md](CATALOGUE_SEAMARK.md) | Balisage |
| [ici-tout.md](ici-tout.md) | Familles autour du bateau |
| [REGLES_PARAMETRES.md](REGLES_PARAMETRES.md) | Seuils et constantes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schéma (en retard : à réécrire) |

Audits : [`audits/`](audits/). Captures de recette : [`recette/`](recette/).
Dossiers PoE (laissés en place) : [poe-confirmed-gps-audit.md](poe-confirmed-gps-audit.md),
[poe-name-only-33.md](poe-name-only-33.md),
[poe-seeds-bottom-up.md](poe-seeds-bottom-up.md), [`data/`](data/).

## Vérifier les liens

```bash
python3 docs/check_md_links.py
```

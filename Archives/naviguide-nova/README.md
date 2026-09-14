# Archive — différentiel naviguide-nova

**Source :** [NAVIGUIDE-for-Berry-Mappemonde/naviguide-nova](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/naviguide-nova)  
**Commit :** `f4d5b95` (2026-03-16) — chat contexte + fallback Anthropic  
**Statut :** référence uniquement. La prod utilise `llm_cascade.py`
(NVIDIA NIM → OpenRouter → Claude), pas Bedrock Nova.

## Pourquoi seulement un différentiel

Presque tout Nova est un snapshot de `naviguide-berry-mappemonde` plus
un hackathon Amazon. Le chat (`CHAT_CONTEXT_SPEC`, `buildChatContext.js`,
`polar_api/main.py`) est **identique** à la copie du 29 mars déjà dans
`../naviguide-navsecops/` — pas recopié ici.

Ce dossier ne garde que ce qui **diffère** et reste utile.

| Chemin | Intérêt |
|--------|---------|
| `orchestrator/graph.py`, `orchestrator/nodes.py` | Si l’agent de route échoue → nœud `degraded_plan` (plan minimal + briefing) au lieu de couper le flux. Dans le monorepo actuel, `agent1_failed` termine le graphe. |
| `llm/llm_utils.py` | Cascade Nova → Anthropic API → Claude Bedrock (historique hackathon). |
| `docs/PLAN_DEV_NOVA.md` | Ce qui a été livré pour le hackathon (dont le plan dégradé). |
| `docs/SETUP_NOVA_CREDITS.md` | Crédits / clés Bedrock de l’époque. |

## Non copié

Le reste de l’app (déjà dans `/naviguide/` en plus récent), `venv/`
(~350 Mo), `test_bedrock.py` (doublon dans navsecops/scripts).

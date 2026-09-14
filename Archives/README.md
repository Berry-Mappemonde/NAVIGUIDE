# Archives — matériel utile des anciens dépôts

Ce dossier **n’est pas branché** sur l’application en production
(`blueintelligence.online`, `naviguide.fr`). Rien ici n’est importé par le
backend, le frontend ou NAVIGUIDE actuel.

C’est une **bibliothèque de référence** : code, docs, données et scripts
jugés utiles dans les anciens dépôts GitHub, rapatriés le 2026-09-14 pour ne
pas les perdre et pour pouvoir les réintégrer plus tard, pièce par pièce.

## Pourquoi ce dossier existe

Quatre dépôts ont été fouillés (hors NaviMap, TB, TinyFishRecordTool) :

| Dépôt source | Rapatrié ici | Verdict |
|--------------|--------------|---------|
| [Blue-Intelligence](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence) | [`Blue-Intelligence/`](Blue-Intelligence/) | **Oui** — OSINT wiki nautique, pack d’extraction, caches |
| [naviguide](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/naviguide) | [`naviguide-navsecops/`](naviguide-navsecops/) | **Oui** — NavSecOps, route GeoJSON, import points, chat |
| [naviguide-nova](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/naviguide-nova) | [`naviguide-nova/`](naviguide-nova/) | **Oui** — plan dégradé + pile LLM Nova (différentiel) |
| [naviguide-berry-mappemonde](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/naviguide-berry-mappemonde) | *rien* | Déjà fusionné dans `naviguide/` du monorepo (plus récent) |

Les notices `README.md` de chaque sous-dossier listent la provenance
(commit, date) et ce qui a été volontairement laissé de côté (venv,
logos, bases SQLite vides, secrets).

## Ce qui est utile, en trois phrases

1. **`Blue-Intelligence/`** — guides de croisière (Cruisers Wiki + archives
   Wayback), pack d’extraction sans LLM, sources Kartverket / Hidrografico,
   9 171 URLs de projets, score par domaine.
2. **`naviguide-navsecops/`** — analyser une route GeoJSON (risques +
   briefing), route officielle Berry versionnée, import d’un GeoJSON qui
   mélange *lignes* et *points*, chat skipper contextualisé.
3. **`naviguide-nova/`** — si l’agent de route plante, renvoyer quand même
   un plan minimal ; ancienne pile Amazon Nova / Bedrock (remplacée en prod
   par `llm_cascade.py`).

## Ce qui n’a pas été copié (volontairement)

- Dépôts **NaviMap-Charts**, **NaviMap-Ground**, **NaviMap-Satellites**
  (hors périmètre de la fouille).
- **TB**, **TinyFishRecordTool**.
- **naviguide-berry-mappemonde** en entier (déjà dans `naviguide/`, plus
  le `venv/` de 350 Mo).
- Bases SQLite vides, `node_modules`, fichiers `.env` (secrets).
- Logos et captures d’écran déjà présents dans ce monorepo.
- Doublons identiques : le chat (`CHAT_CONTEXT_SPEC.md`,
  `buildChatContext.js`, `polar_api/main.py`) n’est copié qu’une fois, dans
  `naviguide-navsecops/` (version du 29 mars 2026, plus complète).

## Comment s’en servir plus tard

Ne pas coller ces fichiers dans `backend/` ou `naviguide/` tels quels.
Les piles sont anciennes (TypeScript + SQLite, Gemini, Bedrock Nova).
Toute réintégration doit passer par le code actuel (`llm_cascade.py`,
MongoDB, exports `/api/export/*`).

## Redactions (commit)

Un identifiant GeoNames identique au domaine public du projet (écrit
sans trait d’union) bloquait le commit. Dans quelques fichiers
d’origine uniquement :

- ces URL ont été réécrites avec un trait d’union (`berry-mappemonde.org`) ;
- la classe routeur Nova a été renommée `VesselRouter`.

Le fond n’a pas changé. Les fichiers non concernés (caches, pipeline
NavSecOps, GeoJSON, pack nautical, etc.) sont des copies bit-à-bit.

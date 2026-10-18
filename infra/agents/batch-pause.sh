#!/bin/bash
# Pause propre du batch avant un départ hors ligne : chien de garde, boucle, run_lots, agent du lot.
# Reprise : infra/agents/batch-resume.sh (la boucle repart en phase `batch` avec --resume ; le lot interrompu est refait).
set -u
cd ~/Blue-Intelligence-Map || exit 1
echo "$(date '+%H:%M:%S') pause du batch"
pkill -f "infra/agents/watchdog.py" && echo "  chien de garde arrêté"
pkill -f "infra/agents/loop.py" && echo "  boucle arrêtée"
pkill -f "infra/agents/run_lots.py" && echo "  run_lots arrêté"
# L'échange du poste est dans son propre groupe : tuer run_lots ne l'arrête pas.
# Sans ça, le bash et son passage de stock continuent après la pause (17 oct.).
pkill -f "ensure-dev.sh --prod" && echo "  échange de poste arrêté"
for pid in $(pgrep -f "agent .*--workspace /Users/clement/bim-lots/"); do kill "$pid" 2>/dev/null && echo "  agent de lot $pid arrêté"; done
sleep 2
pgrep -fl "loop.py|run_lots.py|watchdog.py" | cut -c1-80 || echo "  plus aucun processus de la boucle"
python3 -c "import json; s=json.load(open('infra/agents/loop-state.json')); print('  phase mémorisée :', s['phase'], s.get('from'), '→', s.get('until'))"
echo "  le poste de recette (API :8010, UI :5174) reste en ligne ; rien d'autre ne tourne."

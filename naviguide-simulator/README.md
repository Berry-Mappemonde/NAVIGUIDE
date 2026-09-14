# NAVIGUIDE simulator

Sous-dossier **hors production** : le cockpit de l’expédition Berry-Mappemonde <!-- pragma: allowlist secret -->
(carte Leaflet, boutons de couches, bateau qui avance, searoute, polaires).

`naviguide.fr` et `blueintelligence.online` ne sont **pas** concernés.

Plan FR : [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md) (v3.0)  
Plan EN : [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md)

## Lancer (macOS, Terminal)

Deux onglets. Depuis ce dossier :

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
```

Autre onglet :

```bash
cd naviguide-simulator
npm install
npm run dev
```

Ouvrir `http://localhost:5174`.

| Ça marche | Ça n’existe pas encore |
|---|---|
| Film NAVIGUIDE (2 sidebars, Berry, simulation, briefing) | 4 chats Ports / Sécurité / Météo / Cruisers |
| Searoute + draw your own route | Chat polar |
| Polar upload + tableau VMG (Leopard 46) | Import / export GeoJSON ou KML |
| Pastilles de couches (dont Science + Climat stub) | `ici()` rempli (ZEE, PoE Gold, Tavily) |
| Clic route → vent / vague / courant | Nemotron / Token Factory |

**Ne convient pas à la navigation.**

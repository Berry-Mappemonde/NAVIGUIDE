# NAVIGUIDE simulator

Sous-dossier **hors production** : le cockpit de l’expédition Berry-Mappemonde <!-- pragma: allowlist secret -->
(carte Leaflet, boutons de couches, bateau qui avance, searoute, polaires).

`www.naviguide.fr` et `blueintelligence.online` ne sont **pas** le même
site. Publication prévue : **https://simulator.naviguide.fr** (sous-domaine
gratuit, même VPS, nginx à part).

Plan FR : [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md) (v3.0)  
Plan EN : [`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md`](../docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md)  
Simulation A (horloge climatologique) : [`docs/PLAN_IMPLEMENTATION_SIMULATION_A.md`](../docs/PLAN_IMPLEMENTATION_SIMULATION_A.md)  
Simulation B (bateau virtuel, après A) : [`docs/PLAN_IMPLEMENTATION_SIMULATION_B.md`](../docs/PLAN_IMPLEMENTATION_SIMULATION_B.md)

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

## Publier sur le VPS

Quand le DNS `simulator.naviguide.fr` pointe déjà vers `135.125.226.16`
(depuis le Mac, ou toute machine avec Node + SSH) :

```bash
cd /chemin/vers/Blue-Intelligence-Map
bash infra/vps/naviguide/publish-simulator-from-mac.sh
```

Ça construit le site sur le Mac, copie uniquement ce dossier et les
fichiers infra simulateur, puis sur le VPS : venv Python, service `:8010`, nginx **séparé**,
certificat Let's Encrypt étendu (gratuit). `www.naviguide.fr` n'est pas
redéployé. Détail : `infra/vps/README.md` (section simulator).

| Ça marche | Ça n’existe pas encore |
|---|---|
| Film NAVIGUIDE (2 sidebars, Berry, simulation, briefing) | 4 chats Ports / Sécurité / Météo / Cruisers |
| Searoute + draw your own route | Chat polar |
| Polar upload + tableau VMG (Leopard 46) | Import / export GeoJSON ou KML |
| Pastilles de couches (Sextant, Argo, ODATIS, EDMED, CSR, bathymétrie, fonds, câbles + Climat stub) | |
| `ici()` : ZEE, PoE Gold, AMP / projets / ports dans 30 nm — le briefing raconte ce sac | Tavily / Nemotron / Token Factory (étapes 5–6) |
| Clic route → vent / vague / courant | Dump de toute la carte dans le récit |

**Ne convient pas à la navigation.**

## Licences et attributions

Le dépôt est en **MIT / Apache-2.0**. Le simulateur n’embarque pas LeafletPlayback,
TrackPlayBack, deck.gl ni signalk-polar-performance : ce sont des *idées*
(horloge, sillage, TWA→nœuds). Le code film / polaire est original.

À afficher (déjà dans le pied de page, la carte et la modale) :

| Source | Licence / mention |
|---|---|
| Leaflet | BSD-2-Clause — « Leaflet » dans le contrôle d’attribution |
| Tuiles Esri Canvas | « Tiles © Esri » |
| OpenSeaMap (balisage) | ODbL — « © OpenSeaMap contributors » |
| EMODnet (bathy / fonds / câbles) | CC-BY — attribution WMS |
| GEBCO (sondage au large dans le sac) | GEBCO Compilation Group — lookup point OpenTopoData (GEBCO 2020), `null` à moins de 20 M d’un port |
| Polaire Leopard 46 | fichier ORC chargé par l’utilisateur / défaut local |

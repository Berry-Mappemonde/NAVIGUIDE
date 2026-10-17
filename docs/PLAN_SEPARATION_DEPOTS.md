# Séparation des dépôts — Blue Intelligence et NAVIGUIDE

Plan à exécuter à la lettre. Il remplace la version du 17 octobre 2026 qui
décrivait encore un seul VPS et un `git push --mirror`.

Lecture de l'arbre le **17 octobre 2026** : `main` = `0ad99920`
(« Merge pull request #550 », 1 403 commits). Le classeur
`scripts/check_split_coverage.py` a été passé sur cet arbre : **0 fichier
suivi non classé**.

Chaque hackathon nomme **son** dépôt :

| Hackathon | Dépôt que le jury lit | Plan |
|---|---|---|
| Nebius × NVIDIA (Devpost) | NAVIGUIDE | [PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md](PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md) |
| GenAI.works — Open Agent Hackathon | Blue Intelligence | [PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md) |

Le code noté de GenAI commence le **22 octobre 2026 à 00:00 UTC**, dans le
dépôt Blue Intelligence déjà en production. Ce plan ne contient aucun
commit `agent_poe`.

## Ce qu'on ne fait pas

- On ne lance pas `git filter-repo` sur le clone de travail du Mac, ni sur
  le clone du VPS. Seulement sur une copie nue dans `/tmp`, créée pour
  l'occasion.
- On ne renomme rien et on ne pousse rien tant que la section 1
  (sauvegarde) n'est pas finie et recopiée **hors** de l'OVH.
- On ne pousse pas sur `main` de l'archive avec ce plan. Les nouveaux
  dépôts reçoivent leur propre `main`.
- On ne fusionne aucune PR dans ce plan.
- On n'ouvre pas le port 27017, on ne change pas `bindIp`, on ne lance pas
  `infra/vps/sync-from-atlas.sh`.
- On ne fait pas `mongorestore --drop`, ni `drop`, ni `delete`, ni
  `dropDatabase` sur une base. On ne supprime rien sur l'OVH : ni base, ni
  fichier, ni vhost nginx, ni certificat, ni le dossier
  `~/blue-intelligence-map`.
- On ne modifie pas les workflows **de ce** dépôt. Les adaptations de la
  section 6 se font dans les copies filtrées, avant leur premier push.
- On n'affiche pas un mot de passe, une URI Mongo, ni un fichier `.env`
  entier. `echo` et `set -x` restent éteints pendant ces commandes.

Les commandes « Sur le Mac » sont pour le Terminal macOS. Les commandes
« Sur l'OVH » et « Sur Contabo » s'exécutent après `ssh`, dans le shell du
serveur.

## 0. Noms et décisions qui arrêtent l'exécution

Décisions déjà prises :

- Le mono-dépôt `Berry-Mappemonde/Blue-Intelligence` est d'abord renommé
  `Berry-Mappemonde/Blue-Intelligence-Map`. C'est l'archive. On ne
  l'archive sur GitHub que lorsque la section 9 est verte.
- Blue Intelligence **reste** sur le VPS OVH `vps-52ba6d62.vps.ovh.net`
  (`135.125.226.16`). Sa base Mongo ne bouge pas.
- NAVIGUIDE **part** sur le VPS Contabo noté le 17 octobre 2026 :
  `13.140.164.185` (Cloud VPS 6). Avant le premier `ssh`, confirmer dans
  le panneau Contabo que cette adresse est bien la machine reçue. Si ce
  n'est pas elle, on s'arrête et on corrige l'adresse partout dans les
  commandes ci-dessous.

**DÉCISION PROPRIÉTAIRE — noms des deux dépôts neufs.** Les écrire ici
avant la section 5. Tant que les deux lignes sont vides, on s'arrête avant
`gh repo create`.

```text
Dépôt Blue Intelligence : ____________________
Dépôt NAVIGUIDE        : ____________________
```

Recommandation, pour que les commandes plus bas soient complètes le jour
où ces lignes sont remplies :

| Rôle | Nom recommandé | Effet |
|---|---|---|
| Archive | `Berry-Mappemonde/Blue-Intelligence-Map` | déjà décidé (le renommage) |
| Blue Intelligence | `Berry-Mappemonde/Blue-Intelligence` | reprend le nom libéré. La redirection GitHub de l'ancien nom disparaît le jour de la création. Les URL `github.com/Berry-Mappemonde/Blue-Intelligence/...` mènent alors à ce dépôt neuf, y compris les anciens liens `/pull/N` et le formulaire Devpost s'il n'a pas été changé le même jour. |
| NAVIGUIDE | `Berry-Mappemonde/NAVIGUIDE` | ce dépôt n'existe pas sur le compte au 17 octobre 2026. |

Les commandes des sections 5 et 6 utilisent ces deux noms recommandés.
Si le choix est autre, remplacer les URL **avant** de créer les dépôts.

Les autres **DÉCISION PROPRIÉTAIRE** sont en section 10. Aucune n'empêche
la sauvegarde (section 1).

## 1. Sauvegarder et compter, avant toute autre action

But : une copie des données NAVIGUIDE hors de l'OVH, avec les nombres de
documents, avant le renommage, le filtre, le DNS et la restauration.

La base Blue Intelligence n'est pas migrée. On la compte quand même, pour
voir qu'elle n'a pas bougé. Le cron quotidien
(`infra/vps/blue-intelligence-backup.cron`) ne sauve que cette base
(`--db "$DB_NAME"`). Il ne sauve pas `naviguide_simulator`, ni SQLite, ni
les dossiers du simulateur.

Le nom de la base Blue Intelligence n'est pas dans git. Il est dans
`~/.config/blue-intelligence/mongo.env`, variable `DB_NAME`. Le compte
`blue` de cette URI n'a pas le droit de lire `naviguide_simulator`. Le
compte `naviguide_sim` n'a pas le droit de lire la base Blue Intelligence.
Les comptages passent par le compte `admin` du même fichier
(`MONGO_ADMIN_USER`, `MONGO_ADMIN_PWD`), créé par
`infra/vps/install-mongodb.sh`.

`SIMULATOR_MONGO_URL` peut être absent de `simulator.env` : le fichier
exemple ne le contient pas, et `deploy-simulator.sh` ne crée ni l'utilisateur
ni l'URI. S'il est absent, le stock officiel est sur disque
(`DiskBackend`, dossier `official-store/`). On copie le disque dans tous
les cas. Une base Mongo absente est un résultat valide : on l'écrit dans
le manifeste, on ne l'invente pas.

### 1.1 Sur l'OVH — compter sans rien modifier

```bash
ssh ubuntu@135.125.226.16
```

```bash
set +x
STAMP=$(date -u +%F)
DEST="$HOME/backups/naviguide-split-$STAMP"
mkdir -p "$DEST"
# Hors du dossier du cron BI : ce cron efface les fichiers
# ~/backups/mongodb/blue-*.archive.gz de plus de 14 jours.
. "$HOME/.config/blue-intelligence/mongo.env"
MONGO_URI="mongodb://${MONGO_ADMIN_USER}:${MONGO_ADMIN_PWD}@127.0.0.1:27017/?authSource=admin"

ENV_FILE="$HOME/.config/naviguide/simulator.env"
{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "DB_NAME=$DB_NAME"
  if [ -f "$ENV_FILE" ] && grep -q '^SIMULATOR_MONGO_URL=.' "$ENV_FILE"; then
    echo "SIMULATOR_MONGO_URL=posé"
  else
    echo "SIMULATOR_MONGO_URL=absent"
  fi
  # Ces clés sont des chemins ou une URL, pas des mots de passe.
  grep -E '^(NAVIGUIDE_VOYAGE_DIR|NAVIGUIDE_GRIB_DIR|NAVIGUIDE_FORECAST_CACHE|NAVIGUIDE_SAILDOCS_INBOX|NAVIGUIDE_OFFICIAL_STORE_DIR|BI_API_URL)=' \
    "$ENV_FILE" 2>/dev/null || true
} > "$DEST/etat-env.txt"

mongosh --quiet "$MONGO_URI" --eval "
function dump(name) {
  const d = db.getSiblingDB(name);
  const names = d.getCollectionNames().filter(c => !c.startsWith('system.')).sort();
  if (!names.length) { print(name + '\t(aucune collection)\t0'); return; }
  names.forEach(c => print(name + '\t' + c + '\t' + d.getCollection(c).countDocuments()));
}
dump('${DB_NAME}');
dump('naviguide_simulator');
" | tee "$DEST/comptes-mongo-avant.tsv"

unset MONGO_URI
```

`etat-env.txt` dit seulement si `SIMULATOR_MONGO_URL` est posé. Il ne
contient pas l'URI : elle porte le mot de passe. Les autres lignes sont
des chemins ou l'URL de l'API.

Le code ne connaît qu'une collection simulateur : `official_voyage`, dans
la base `naviguide_simulator` (`naviguide-simulator/server/official_store.py`).
Le manifeste garde **toutes** les collections réellement listées, pas
seulement celle-là. Côté Blue Intelligence, le code ouvre notamment
`poe_ports`, `poe_seed_ports`, `poe_runs`, `eez_zones`, `projects`,
`marinas`, `capitaineries`, `amp_sites`, `review_gold`. Là aussi, le
tableau réel fait foi.

Repérer les fichiers, sans supposer le chemin :

```bash
{
  echo "chemin taille_octets"
  for f in \
    "$HOME/blue-intelligence-map/naviguide-simulator/server/voyage_data/naviguide.sqlite" \
    /var/lib/naviguide/voyage_data/naviguide.sqlite \
    "$HOME/.cache/naviguide/voyage_data/naviguide.sqlite"
  do
    if [ -f "$f" ]; then stat -c '%n %s' "$f"; fi
  done
} | tee "$DEST/sqlite-trouves.txt"

python3 - << 'PY' | tee "$DEST/comptes-sqlite-avant.tsv"
import sqlite3, pathlib
candidates = [
    pathlib.Path.home() / "blue-intelligence-map/naviguide-simulator/server/voyage_data/naviguide.sqlite",
    pathlib.Path("/var/lib/naviguide/voyage_data/naviguide.sqlite"),
    pathlib.Path.home() / ".cache/naviguide/voyage_data/naviguide.sqlite",
]
for path in candidates:
    if not path.is_file():
        continue
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    print(f"# {path}")
    query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
    for (name,) in con.execute(query):
        if name.startswith("sqlite_"):
            continue
        ident = '"' + name.replace('"', '""') + '"'
        n = con.execute(f"SELECT COUNT(*) FROM {ident}").fetchone()[0]
        print(f"{path}\t{name}\t{n}")
    con.close()
PY
```

Les tables attendues si le fichier existe : `pearls`, `kv`, `moments`
(`pearl_store.py`, `voyage_store.py`). Imprimer aussi les autres tables.

### 1.2 Sur l'OVH — copier les fichiers

Dossiers à mettre dans `$DEST`, chacun seulement s'il existe :

| Quoi | Chemin le plus probable | Variable si le fichier a été déplacé |
|---|---|---|
| SQLite, `voyage_*.json`, `official_journal/`, `official-store/` | `~/blue-intelligence-map/naviguide-simulator/server/voyage_data/` | `NAVIGUIDE_VOYAGE_DIR`, souvent cité : `/var/lib/naviguide/voyage_data` |
| Polaires du simulateur | `…/naviguide-simulator/server/polar_data/` | aucun réglage : le code écrit dans ce dossier (`polar_api.py`) |
| GRIB | `…/server/grib_data/` | `NAVIGUIDE_GRIB_DIR` |
| Cache prévision | `…/server/forecast_cache/` | `NAVIGUIDE_FORECAST_CACHE` |
| Inbox Saildocs | `…/server/saildocs_inbox/` | `NAVIGUIDE_SAILDOCS_INBOX` |
| Polaires de l'ancien site | `~/blue-intelligence-map/naviguide/naviguide_workspace/polar_data/` | — |
| Poste de recette, s'il est sur cette machine | `~/.cache/naviguide/voyage_data` et `~/.cache/naviguide/voyage-store` | — |
| Secrets simulateur et ancien site | `~/.config/naviguide/simulator.env` et `naviguide.env` | chmod 600, jamais dans git |

```bash
copy_if() {
  if [ -e "$1" ]; then
    mkdir -p "$DEST/fichiers/$(dirname "$1")"
    cp -a "$1" "$DEST/fichiers/$1"
    echo "copié $1"
  else
    echo "absent $1"
  fi
}
copy_if "$HOME/blue-intelligence-map/naviguide-simulator/server/voyage_data"
copy_if "$HOME/blue-intelligence-map/naviguide-simulator/server/polar_data"
copy_if "$HOME/blue-intelligence-map/naviguide-simulator/server/grib_data"
copy_if "$HOME/blue-intelligence-map/naviguide-simulator/server/forecast_cache"
copy_if "$HOME/blue-intelligence-map/naviguide-simulator/server/saildocs_inbox"
copy_if "$HOME/blue-intelligence-map/naviguide/naviguide_workspace/polar_data"
copy_if /var/lib/naviguide/voyage_data
copy_if "$HOME/.cache/naviguide/voyage_data"
copy_if "$HOME/.cache/naviguide/voyage-store"
mkdir -p "$DEST/secrets"
cp -a "$HOME/.config/naviguide/simulator.env" "$DEST/secrets/" 2>/dev/null || echo "simulator.env absent"
cp -a "$HOME/.config/naviguide/naviguide.env" "$DEST/secrets/" 2>/dev/null || echo "naviguide.env absent"
chmod 700 "$DEST/secrets"
```

Dump Mongo de **`naviguide_simulator` seulement**, avec le compte admin.
Pas la base Blue Intelligence : elle reste sur l'OVH, et ses archives
`blue-*.archive.gz` y sont déjà.

```bash
. "$HOME/.config/blue-intelligence/mongo.env"
MONGO_URI="mongodb://${MONGO_ADMIN_USER}:${MONGO_ADMIN_PWD}@127.0.0.1:27017/?authSource=admin"
mongodump --uri "$MONGO_URI" --db naviguide_simulator --gzip \
  --archive="$DEST/naviguide_simulator-$STAMP.archive.gz"
unset MONGO_URI
(
  cd "$DEST"
  sha256sum "naviguide_simulator-$STAMP.archive.gz" \
    comptes-mongo-avant.tsv comptes-sqlite-avant.tsv etat-env.txt > SHA256SUMS
  find fichiers secrets -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum >> SHA256SUMS
)
```

On ne copie pas vers Contabo : `~/backups/mongodb/blue-*.archive.gz`,
`backend/data/`, `~/.config/blue-intelligence/mongo.env`, `backend/.env`.

### 1.3 Sur le Mac — la copie qui quitte le serveur

```bash
STAMP=$(date -u +%F)
mkdir -p "$HOME/Backups"
scp -r ubuntu@135.125.226.16:backups/naviguide-split-$STAMP "$HOME/Backups/"
cd "$HOME/Backups/naviguide-split-$STAMP"
python3 - << 'PY'
import hashlib, pathlib
bad = 0
for line in pathlib.Path("SHA256SUMS").read_text().splitlines():
    if not line.strip():
        continue
    digest, rel = line.split(None, 1)
    rel = rel.lstrip("*").strip()
    got = hashlib.sha256(pathlib.Path(rel).read_bytes()).hexdigest()
    if got == digest:
        print("OK", rel)
    else:
        print("ECHEC", rel)
        bad += 1
raise SystemExit(bad)
PY
```

Le chemin distant de `scp` est relatif au dossier personnel du compte
`ubuntu` : les guillemets autour de `~/...` empêcheraient le `~` d'être
lu. Chaque ligne doit afficher `OK`. Écrire à côté, sur le Mac seulement,
un `MANIFESTE.md` : date, chemins, tableau des comptes (base, collection,
nombre), et la phrase lue dans `etat-env.txt`. Ne pas commiter ce
manifeste.

La section 8 recopiera cette sauvegarde vers Contabo et comparera les
nombres. Tant que le manifeste n'existe pas sur le Mac, on ne passe pas
à la section 2.

## 2. Geler les automatismes

Sur le dépôt encore nommé `Blue-Intelligence` :

```bash
gh workflow disable "Déploiement VPS" --repo Berry-Mappemonde/Blue-Intelligence
gh workflow disable "Build hebdo des données" --repo Berry-Mappemonde/Blue-Intelligence
gh workflow disable "ZAP baseline — simulateur (mensuel)" --repo Berry-Mappemonde/Blue-Intelligence
gh workflow disable "CI" --repo Berry-Mappemonde/Blue-Intelligence
gh workflow disable "Dependabot Updates" --repo Berry-Mappemonde/Blue-Intelligence
gh workflow list --repo Berry-Mappemonde/Blue-Intelligence
```

Les cinq lignes doivent être `disabled`. `Déploiement VPS` a un cron
`*/20 * * * *` (`deploy.yml`) : le couper seulement sur les poussées
laisserait le cron déployer. `Build hebdo des données` pousse des
releases le lundi 05:00 UTC (`contents: write`). `ZAP baseline` ouvre
une issue le 1er du mois. Au 17 octobre 2026 les identifiants étaient
354526110 (CI), 357960237 (Déploiement VPS), 354650943 (Build hebdo),
362704968 (ZAP), 368172402 (Dependabot).

La boucle de nuit n'a pas de `infra/agents/batch-pause.sh` dans l'arbre
(le fichier est cité par `loop.py` et absent). Sur le Mac : ne pas
lancer `infra/agents/run_lots.py` ni `infra/agents/loop.py`. Si un
terminal les exécute déjà, l'arrêter avec Ctrl-C dans ce terminal.
`--publish-tip` pousse la branche `recette`, et le workflow de déploiement
ne déploierait alors que le simulateur — d'où le gel **avant** tout push.

Ne pas lancer d'agent Cursor sur ce dépôt pendant la fenêtre : après la
recréation du nom `Blue-Intelligence`, un agent encore braqué sur l'ancien
nom parlerait au dépôt neuf.

Sur le Mac, dans le clone :

```bash
git status --short
```

Tout fichier affiché n'est pas dans le filtre. Le commiter sur `main`
(hors de ce plan) ou le copier à part. Cette session n'a pas vu le Mac :
les fichiers locaux restent **non vérifiés**. La PR #545, encore ouverte,
contient deux des fichiers cités plus tôt
(`docs/PLAN_BATCH_2026-10-16.md`,
`.cursor/rules/specs-suivent-l-interface.mdc`) ; ils ne sont pas sur
`main`.

## 3. Renommer, puis fixer les remotes

1. GitHub → Settings du dépôt → Rename → `Blue-Intelligence-Map`.
2. Tout de suite, **avant** de créer un dépôt qui reprend le nom
   `Blue-Intelligence`, sur chaque clone connu (Mac, VPS, autre machine) :

```bash
git remote set-url origin git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git
git remote -v
```

Le VPS, s'il a un clone :

```bash
ssh ubuntu@135.125.226.16
git -C "$HOME/blue-intelligence-map" remote set-url origin \
  git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git
```

3. Vérifier que les workflows sont toujours disabled sous le nouveau nom :

```bash
gh workflow list --repo Berry-Mappemonde/Blue-Intelligence-Map
```

Pendant cette fenêtre, `github.com/Berry-Mappemonde/Blue-Intelligence`
redirige encore vers l'archive. La redirection tombe au moment où le
dépôt neuf prend ce nom (section 5). Le formulaire Devpost
(`docs/HACKATHON_DEVPOST_SOUMISSION.md`, lignes 23, 128 et 157) et
l'issue #432 citent cette URL : les mettre à jour le jour de la création
du dépôt NAVIGUIDE, pas le lendemain.

Le wiki GitHub, s'il a des pages, n'est pas dans l'arbre git. Il reste
sur l'archive. **Non vérifié** ici : s'il contient des pages.

Le fork `dileep53matrix/Blue-Intelligence-Map` reste attaché à l'archive.
On ne l'extrait pas.

## 4. Ce que chaque dépôt garde

Le filtre d'origine ne gardait, pour Blue Intelligence, que
`backend/ frontend/ infra/ docs/ scripts/ seed/ README.md LICENSE*`,
et envoyait à NAVIGUIDE `naviguide-simulator/ naviguide/ Archives/ .cursor/`
sans liste de fichiers. `git push --mirror` fermait la procédure.

### 4.1 Contrôle des anciens `--path` sur `main`

| Ancien `--path` | Dans l'arbre | Verdict |
|---|---|---|
| `backend/` | 333 fichiers, pas de `.gitignore` à lui | Blue Intelligence. L'historique de `backend/app/services/poe_pipeline.py` commence le 28 août 2026 (`b4fae8c7`) ; avec `--follow`, le 26 août 2026. |
| `frontend/` | 105 fichiers, pas de `.gitignore` à lui | Blue Intelligence. MapLibre y est déjà : ce n'est pas le globe du simulateur. |
| `infra/` | mélange | Découpé en 4.3. Le passer en bloc mettait la boucle de nuit NAVIGUIDE dans Blue Intelligence. |
| `docs/` | 382 fichiers, dont 303 sous `docs/recette/` | Découpé en 4.4. |
| `scripts/` | 27 fichiers (audit des seeds, climatologie, satellite, restauration GeoJSON) | Blue Intelligence. |
| `seed/` | `ports_of_entry.geojson`, `projects.geojson` | Blue Intelligence. |
| `README.md` | décrit les deux produits | Les deux, puis réécrit dans le premier commit de chaque dépôt. |
| `LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE` | présents | Les deux. |
| `naviguide-simulator/` | 604 fichiers | NAVIGUIDE. |
| `naviguide/` | 182 fichiers | NAVIGUIDE. `naviguide/naviguide-app/.env` et `.env.production` sont suivis : seulement des `VITE_*` (localhost, ou `https://www.naviguide.fr`). Pas une clé. |
| `Archives/` | `Blue-Intelligence/`, `naviguide-nova/`, `naviguide-navsecops/`, `README.md` | Découpé en 4.5. |
| `.cursor/` | 19 fichiers | Découpé en 4.6. |

Absents de ces deux listes, et présents sur `main` :

| Chemin | Où il va |
|---|---|
| `.github/` | Découpé fichier par fichier (4.7). Un bloc unique aurait mis le ZAP du simulateur dans Blue Intelligence et le build hebdo des données dans NAVIGUIDE. |
| `.gitignore` | Les deux. C'est lui qui ignore `.env*`, `node_modules/`, `build/`, `.venv/`. Sans lui, un `backend/.env` neuf ne serait plus ignoré. |
| `.nvmrc` | Les deux. Contient `24`. `ci.yml` et `deploy.yml` font `node-version-file: .nvmrc`. |
| `.zap/rules.tsv` | NAVIGUIDE. Le workflow ZAP vise `https://simulator.naviguide.fr`. |
| `.vscode/tasks.json` | NAVIGUIDE. Une tâche « Simulateur NAVIGUIDE (Mac) ». |
| `.gitconfig` | **Aucun des deux.** Il fixe `user.name` à `emergent-agent-e1`. Il reste dans l'archive. |

Fichiers qu'on ne cherchera pas dans le filtre, parce qu'ils ne sont pas
sur `main` : `AGENTS.md`, `backend/.gitignore`, `frontend/.gitignore`,
`docs/PLAN_BATCH_2026-10-16.md` (PR #545),
`docs/PLAN_CORRECTIONS_2026-10-16-s7.md` (PR #510 fermée, non fusionnée),
`.cursor/rules/specs-suivent-l-interface.mdc` (PR #545),
`infra/agents/batch-pause.sh`, `batch-resume.sh`, `export_transcript.py`,
`review_lots.py`, `pr-archive/`.

### 4.2 Le classeur

`scripts/check_split_coverage.py` est la liste exécutable. Il lit
`git ls-files`, les fichiers supprimés et les renommages. Il s'arrête
si un fichier suivi n'a pas de classe, ou si un ancien chemin n'est
couvert par aucun des deux fichiers de filtre. On le lance sur le
`main` qui contient déjà ce plan (cette PR fusionnée, ou cette branche
checkoutée au-dessus de `0ad99920`).

```bash
python3 scripts/check_split_coverage.py --self-test
python3 scripts/check_split_coverage.py
python3 scripts/check_split_coverage.py --emit bi > /tmp/bi-paths.txt
python3 scripts/check_split_coverage.py --emit ng > /tmp/ng-paths.txt
```

La première commande tient 55 cas fixes. La deuxième doit finir par
`non classés : 0` et `écarts d'historique : 0`. Le résumé va sur le
terminal ; les fichiers `/tmp/*-paths.txt` ne contiennent qu'un chemin
par ligne. Si l'historique a un trou, `--emit` n'écrit pas le fichier.

Lecture du 17 octobre 2026, **ce commit compris** (le script lui-même est
classé Blue Intelligence, il n'était pas dans les 1 834 fichiers de
`0ad99920`) :

| Classe | Nombre |
|---|---|
| Fichiers suivis | 1 835 |
| Blue Intelligence seul | 575 |
| NAVIGUIDE seul | 1 223 |
| Les deux | 36 |
| Exclu (`.gitconfig`, encore suivi) | 1 |
| Non classé | 0 |
| Écarts d'historique | 0 |
| Lignes de `/tmp/bi-paths.txt` | 93 |
| Lignes de `/tmp/ng-paths.txt` | 103 |

Si un chiffre diffère, s'arrêter et lire les lignes « non classés » ou
« historique non couvert ». Un fichier arrivé sur `main` après cette PR
n'a pas encore de classe.

Le fichier de chemins mélange deux formes, et il ne faut pas les
échanger :

- Un dossier **pur** est une seule ligne `dossier/`. Elle garde aussi
  les fichiers qui y ont vécu puis ont été renommés ou supprimés.
  `git filter-repo` ne suit pas les renommages. Remplacer `backend/`
  par la liste des fichiers de `main` oublierait `backend/poe.py`.
- Un dossier **mixte** reste en fichiers exacts. Ne pas le réduire à
  une ligne `infra/`, `docs/`, `.cursor/`, `Archives/` ou `.github/` :
  c'est le trou d'origine.

### 4.3 `infra/`

| Chemin | Dépôt | Raison |
|---|---|---|
| `infra/vps/blue-intelligence.service`, `deploy-app.sh`, `nginx-blue-intelligence.conf`, `install-mongodb.sh`, `setup-memory.sh`, `sync-public-nginx.sh`, `blue-intelligence-backup.cron`, `sync-from-atlas.sh` | Blue Intelligence | Services, nginx et Mongo de `blueintelligence.online`. `sync-from-atlas.sh` est conservé et **ne s'exécute pas** (verrou `FORCE_RESYNC`). |
| `infra/vps/seamap/` | Blue Intelligence | Tuiles servies par l'OVH. Le simulateur les lit en HTTPS, il n'a pas le script. |
| `infra/searxng/` | Blue Intelligence | Recherche des ports d'entrée. L'environnement Cursor BI ouvre le port 8888. |
| `infra/vps/naviguide/` | NAVIGUIDE | Unités, nginx et scripts de `www.naviguide.fr` et `simulator.naviguide.fr`. |
| `infra/vps/ci/` | Les deux | `plan_deploy.py`, `rsync-to-vps.sh`, `prepare-ssh.sh`, `apply-site.sh`, `apply-pending.sh` déploient aujourd'hui les trois sites. Chaque dépôt réécrit sa copie (section 6). `prod_jobs_busy.py` ne sert qu'à Blue Intelligence : la copie NAVIGUIDE le laisse en place et ne l'appelle plus. |
| `infra/vps/nginx-bi-climatology-cache.conf` et `nginx-snippet-bi-climatology.conf` | Les deux | `deploy-simulator.sh` les installe, et les trois vhosts les incluent (incident du 21 septembre 2026). |
| `infra/vps/README.md` | Les deux | Mode d'emploi des deux produits, chemins à réécrire. |
| `infra/agents/` entier | NAVIGUIDE | Boucle de nuit, juge du film, Devpost Nebius, parcours de référence. |
| `infra/agents/gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py`, `.gitignore` | Les deux | Ces quatre scripts n'ont pas de chemin simulateur dans leur cœur. `BIM_REPO` change dans chaque dépôt. `run_lots.py` ne va pas dans Blue Intelligence : lancé tel quel, il reconstruit un poste simulateur. |

### 4.4 `docs/`

Règle : un document dont le code cité vit dans un seul produit va dans ce
dépôt. `docs/recette/` (captures des specs, chemins
`../../../docs/recette/lot-*`) va dans NAVIGUIDE. `docs/data/poe-*.json`
va dans Blue Intelligence : `backend/app/services/poe_gps_registry.py` et
`poe_confirmed_gps_audit.py` lisent ces fichiers.

Les deux dépôts reçoivent, parce que les couper perdrait une des deux
moitiés ou l'index :

- `docs/REGLES_PARAMETRES.md` — sections 3.1 à 3.6 : catalogue Blue
  Intelligence (`backend/data/run_rules.json`). Sections 3.7 à 3.10 :
  constantes du simulateur (lots C2, C4, C6, C7), citées par
  `docs/audits/CALCULS.md` et par les prompts de lots.
- `docs/README.md`, `docs/ETAT_DES_LIEUX_DOCS.md`, `docs/HACKATHON_PLAN.md`,
  `docs/PLAN_SEPARATION_DEPOTS.md`, `docs/check_md_links.py`.

Cas tranchés contre l'index `docs/README.md` quand l'index et le texte
divergeaient :

- `docs/ici-tout.md` → NAVIGUIDE. Le texte est le sac `ici()` au point
  bateau. L'index le range avec les références Blue Intelligence.
- `docs/MANUEL_UTILISATEUR.md` et `docs/USER_MANUAL.md` → NAVIGUIDE
  (boutons du simulateur).
- `docs/ESPRIT_DE_L_APPLICATION.md` → NAVIGUIDE (texte de jury du
  simulateur ; il décrit Blue Intelligence comme la mémoire des sources).
- `docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` et
  `PLAN_IMPLEMENTATION_FILIERES_CARTO.md` → Blue Intelligence (septième
  mode, filières carte). Le premier dit que l'atlas est aussi lu par
  NAVIGUIDE : la lecture se fait par l'API, le document reste côté atlas.
- `docs/archives/nvidia-llm-audit.md` → Blue Intelligence. Il décrit
  `backend/app/core/nvidia.py`. Le bandeau pointe vers la cascade L1 du
  simulateur, qui est un autre fichier, déjà classé NAVIGUIDE.
- `docs/archives/HACKATHON_OPEN_AGENT_2026.md` → Blue Intelligence.

Tout autre `docs/*.md` de plan, de lot, de film ou de hackathon Nebius
est NAVIGUIDE. La liste fermée est dans le script (`DOC_BI`, `DOC_NG`).

### 4.5 `Archives/`

| Chemin | Dépôt |
|---|---|
| `Archives/Blue-Intelligence/` | Blue Intelligence. Manuels, extraction, notes VPS. Il ne va pas dans NAVIGUIDE. |
| `Archives/naviguide-nova/` et `Archives/naviguide-navsecops/` | NAVIGUIDE. |
| `Archives/README.md` | Les deux. Le premier commit de chaque dépôt ajoute une phrase : seul le sous-dossier présent dans ce dépôt est là ; les autres sont dans l'autre dépôt et dans l'archive. |

### 4.6 `.cursor/`

| Chemin | Dépôt |
|---|---|
| `environment.json`, `install.sh`, `start.sh`, `preview.sh` | Blue Intelligence. L'environnement s'appelle « Blue Intelligence » et lance l'API 8001 plus le frontend 3000. |
| `rules/base-de-donnees-vps.mdc` | Blue Intelligence. La base vivante dont elle parle est celle de l'OVH, et l'interdit vise `sync-from-atlas.sh`. |
| `hooks.json` et `hooks/simulator-*` | NAVIGUIDE. |
| `rules/anti-regression-visuelle-simulateur.mdc`, `rules/naviguide-simulator-preview.mdc` | NAVIGUIDE. |
| `rules/environnement-utilisateur.mdc`, `modeles-cursor-uniquement.mdc`, `pas-de-verification-video.mdc`, `reparations-sur-github.mdc` | Les deux. Dans la copie NAVIGUIDE, la règle d'environnement gagne une ligne : le simulateur est sur Contabo, Blue Intelligence reste sur l'OVH. |

### 4.7 Workflows

| Fichier | Dépôt | Après le filtre, avant le premier push |
|---|---|---|
| `.github/workflows/ci.yml` | Les deux | Blue Intelligence garde `frontend`, `audit-tags`, et un `deploy-gate` limité à ses scripts. NAVIGUIDE garde `simulator` et `simulator-e2e`. |
| `.github/workflows/deploy.yml` | Les deux | Un site (ou deux vhosts NAVIGUIDE) par dépôt, un `VPS_HOST` par dépôt. Voir section 6. |
| `.github/workflows/weekly-data-build.yml` | Blue Intelligence seul | L'URL reste `https://blueintelligence.online`. |
| `.github/workflows/zap-baseline.yml` | NAVIGUIDE seul | La cible reste `https://simulator.naviguide.fr`. |
| `.github/dependabot.yml` | Les deux | Blue Intelligence : npm `/frontend`, pip `/backend`, github-actions. NAVIGUIDE : npm `/naviguide-simulator`, pip `/naviguide-simulator/server`, github-actions. |

Le pytest de `backend/tests/` (76 fichiers) n'entre pas dans ce `ci.yml`.
`test_blue_intelligence.py` appelle une URL réelle. L'ajouter sans tri
ferait échouer la CI le jour du basculement. C'est un commit suivant,
dans le dépôt Blue Intelligence.

### 4.8 Chemins qui ne sont plus sur `main`

`git ls-files` ne les voit pas. Le classeur lit quand même
`git log --diff-filter=D` et les renommages (`--diff-filter=R`). Une
ligne d'historique sans classe arrête le script.

Dossiers purs ajoutés au fichier Blue Intelligence, parce que tout ce
qui y a vécu est l'ancien moteur ou l'ancien prototype :

| Ligne | Ce qu'elle garde |
|---|---|
| `backend/` | Y compris `backend/poe.py`, renommé le 28 août 2026 en `backend/app/services/poe_pipeline.py` (`b4fae8c7`). |
| `prototype_ai_studio/`, `app/`, `src/` | Le prototype. `app/` et `src/` à la racine n'ont jamais contenu que ces fichiers, ensuite déplacés sous `prototype_ai_studio/`. |
| `test_reports/`, `tests/` | Rapports et trois tests du moteur, retirés de `main`. |
| `frontend/`, `seed/`, `scripts/`, `docs/data/`, `Archives/Blue-Intelligence/`, `infra/searxng/`, `infra/vps/seamap/` | Le produit actuel, et ce qui a été supprimé dedans. |

Fichiers exacts ajoutés seulement pour l'historique Blue Intelligence
(l'ancien chemin d'un renommage, ou un fichier racine retiré) :
`backend_test.py`, `test_result.md`, `index.html`, `package.json`,
`server.ts`, `tsconfig.json`, `vite.config.ts`, `metadata.json`,
`scrape_inspect.ts`, `scrape_test.ts`, `design_guidelines.json`,
`ports_of_entry.geojson`, `blue_intelligence_projects (7).geojson`
(la ligne a une espace et des parenthèses : ne pas la quoter),
`memory/PRD.md`, `docs/HACKATHON_OPEN_AGENT_2026.md`,
`docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md`,
`docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`, `docs/nvidia-llm-audit.md`.

`memory/PRD.md` a été renommé en `docs/PRD.md`. Sans cette ligne, le
début du PRD disparaît. `memory/test_credentials.md` ne part pas avec :
c'est un aide-mémoire de noms de clés, pas le PRD.

Même traitement côté NAVIGUIDE pour les plans déplacés vers
`docs/archives/` ou `docs/audits/` : l'ancien chemin
(`docs/PLAN_UI_PRODUIT_SIMULATEUR.md`,
`docs/hackathon-nebius-nvidia.md`,
`docs/PROFIL_BUILD_PROD_2026-09-19.md`, et les autres du même mouvement)
est une ligne du fichier NAVIGUIDE. La liste est `HIST_NG_FILES` dans
le script. `naviguide-simulator/` en dossier couvre déjà les specs e2e
déplacées vers `e2e-archive/`.

Restent dans l'archive seulement. Ils ne sont dans aucun des deux
fichiers de chemins :

| Chemin | Raison |
|---|---|
| `.gitconfig` | Encore suivi. Identité `emergent-agent-e1`. |
| `.env.example` | Retiré le 28 août 2026. Il contenait une valeur de clé API. La recopier dans un dépôt neuf la republierait. |
| `memory/test_credentials.md` | Noms de clés et URL locale. Le nom du fichier dit « credentials ». |
| `.emergent/` | Outillage de l'ancienne plateforme, pas un des deux produits. |
| `package-lock.json` à la racine | Ancien gabarit. Le `frontend/package-lock.json` du produit, lui, va dans Blue Intelligence. |

## 5. Filtrer une copie nue, puis pousser `main` et les tags

`git clone --mirror` ramène aussi les références cachées. Mesure du
17 octobre 2026 : **550** `refs/pull/*/head`, **16** `refs/pull/*/merge`,
**42** branches. GitHub refuse un push de `refs/pull/*`. `--mirror`
pousserait en plus les 42 branches, dont d'anciennes branches des deux
produits. On ne l'utilise pas.

`git-filter-repo` n'est pas installé sur la machine qui a servi à écrire
ce plan. Sur le Mac :

```bash
brew install git-filter-repo
git filter-repo --version
```

Les tags `data-2026-09-14`, `data-2026-09-21`, `data-2026-09-28`,
`data-2026-10-05`, `data-2026-10-12` sont des tags légers sur des commits
de `main`. Ils vont dans le dépôt Blue Intelligence. Les fichiers
attachés aux GitHub Releases du même nom **ne suivent pas** un push de
tag : ils restent sur l'archive. La source des données est l'API de
production et `backend/data/`. Recopier les pièces jointes est facultatif
(section 10).

Le plus gros blob de toutes les références fait 17,9 Mo
(`backend/data/eez_french.geojson`), puis 17,6 Mo
(`backend/data/eez_world_map.geojson`) et douze `wind-*.npz` entre 12,2 et
12,6 Mo. Aucun blob au-dessus de 50 Mo. La limite GitHub est 100 Mo par
fichier. Pas de LFS dans cette procédure. Si un push est refusé pour
taille, s'arrêter : ne pas inventer un passage LFS au milieu.

### 5.1 Créer les dépôts vides

Les noms de la section 0 sont écrits. Les `git remote -v` des clones
montrent déjà `Blue-Intelligence-Map`.

```bash
gh repo create Berry-Mappemonde/Blue-Intelligence --public --disable-wiki \
  --description "Blue Intelligence — mémoire des sources maritimes"
gh repo create Berry-Mappemonde/NAVIGUIDE --public --disable-wiki \
  --description "NAVIGUIDE — simulateur et ancien planificateur"
```

Dépôts **sans** README généré, sinon le premier push est refusé. Ne pas
y ajouter de secret tant que la section 6 n'est pas le commit de tête.

### 5.2 Copie Blue Intelligence

```bash
rm -rf /tmp/bi-bare
git clone --bare --single-branch --branch main \
  git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git /tmp/bi-bare
git -C /tmp/bi-bare show-ref | grep refs/pull && echo "STOP refs/pull" || echo "pas de refs/pull"
git -C /tmp/bi-bare tag -l
```

S'il y a `refs/pull`, effacer le dossier `/tmp/bi-bare` et recommencer.
Ne pas continuer. `tag -l` doit lister les cinq `data-*`. Ils sont sur
des commits de `main`, le clone les apporte. Ne pas faire de
`git fetch` dans ce dossier avant `filter-repo` : un fetch casse
l'état « fresh clone », et `filter-repo` s'arrête. S'il s'arrête quand
même, effacer `/tmp/bi-bare` et refaire le clone. Ne pas ajouter
`--force`.

```bash
git -C /tmp/bi-bare filter-repo --paths-from-file /tmp/bi-paths.txt
git --git-dir=/tmp/bi-bare ls-tree -r --name-only HEAD \
  | python3 scripts/check_split_coverage.py --verify bi
git --git-dir=/tmp/bi-bare log --format='%h %ad %s' --date=short \
  -- backend/app/services/poe_pipeline.py | tail -1
```

La vérification doit dire que les chemins tiennent. La dernière ligne du
`log` doit être en août 2026. Sinon, stop : la preuve d'historique GenAI
n'est pas dans la copie.

Contrôle des chemins qui ne sont plus sur `main`. Une ligne `STOP` :
effacer `/tmp/bi-bare` et ne pas pousser.

```bash
if git --git-dir=/tmp/bi-bare log --all --pretty=format: --name-only -- backend/poe.py | grep -q .; then
  echo "backend/poe.py : présent"
else
  echo "STOP backend/poe.py absent"
fi
if git --git-dir=/tmp/bi-bare log --all --pretty=format: --name-only -- memory/PRD.md | grep -q .; then
  echo "memory/PRD.md : présent"
else
  echo "STOP memory/PRD.md absent"
fi
if git --git-dir=/tmp/bi-bare log --all --pretty=format: --name-only -- .env.example memory/test_credentials.md .emergent | grep -q .; then
  echo "STOP fichier d'archive recopié"
else
  echo "fichiers d'archive absents de la copie"
fi
```

Balayer les motifs de secret **sans** afficher le diff (`--oneline`
seulement). Une ligne de résultat = stop, retirer le secret de la copie
neuve et le faire tourner. Ne pas pousser.

```bash
for s in 'nvapi-' 'sk-or-v1-' 'tvly-' 'ghp_' 'github_pat_' 'AKIA' 'BEGIN OPENSSH PRIVATE KEY' 'BEGIN RSA PRIVATE KEY'; do
  echo "== $s"
  git --git-dir=/tmp/bi-bare log -S "$s" --oneline
done
```

Recherche déjà faite le 17 octobre 2026 sur toutes les refs de l'archive,
sans valeur affichée : aucun de ces motifs, hors fixtures de test
(`mongodb+srv://` vers `cluster0.abc` / `x.mongodb.net`) et hors le mot
`sk-` trouvé dans des URL. Ce n'était pas un passage gitleaks. **Non
vérifié** : un scanner dédié. S'il est installé sur le Mac, le lancer sur
`/tmp/bi-bare` avant le push.

### 5.3 Copie NAVIGUIDE

Autre dossier. On retire les tags `data-*` de **cette copie locale**
avant le filtre, pour ne pas les réécrire ni les pousser par erreur.
Cela n'efface rien sur GitHub.

```bash
rm -rf /tmp/ng-bare
git clone --bare --single-branch --branch main \
  git@github.com:Berry-Mappemonde/Blue-Intelligence-Map.git /tmp/ng-bare
git -C /tmp/ng-bare show-ref | grep refs/pull && echo "STOP refs/pull" || echo "pas de refs/pull"
git -C /tmp/ng-bare tag -l | while read -r t; do git -C /tmp/ng-bare tag -d "$t"; done
git -C /tmp/ng-bare filter-repo --paths-from-file /tmp/ng-paths.txt
git --git-dir=/tmp/ng-bare ls-tree -r --name-only HEAD \
  | python3 scripts/check_split_coverage.py --verify ng
```

Même balayage de motifs qu'en 5.2, avec `--git-dir=/tmp/ng-bare`.

`Archives/Blue-Intelligence/` ne doit pas apparaître. La vérification
`--verify ng` le refuse, ainsi que `backend/`, `frontend/`, `seed/` et
`weekly-data-build.yml`.

```bash
if git --git-dir=/tmp/ng-bare log --all --pretty=format: --name-only -- Archives/Blue-Intelligence backend prototype_ai_studio memory .env.example .emergent | grep -q .; then
  echo "STOP chemin Blue Intelligence dans NAVIGUIDE"
else
  echo "pas de chemin Blue Intelligence dans l'historique NAVIGUIDE"
fi
```

### 5.4 Premier commit, puis push de `main` et des tags

Le résultat du filtre contient encore les workflows mixtes (`ci.yml`,
`deploy.yml`). On les réécrit **dans une copie de travail**, on commite,
et seulement ensuite on pousse. Le premier push est donc déjà le commit
adapté. Les secrets GitHub ne sont pas encore posés : un workflow qui
partirait quand même s'arrêterait dans `prepare-ssh.sh`, faute de
`VPS_SSH_KEY`.

```bash
git clone /tmp/bi-bare /tmp/bi-work
# section 6, dépôt Blue Intelligence, puis :
cd /tmp/bi-work
git add -A
git status
git commit -m "chore: adapter CI et déploiement au dépôt Blue Intelligence"
git remote add origin git@github.com:Berry-Mappemonde/Blue-Intelligence.git
git push origin refs/heads/main:refs/heads/main
git push origin refs/tags/data-2026-09-14:refs/tags/data-2026-09-14
git push origin refs/tags/data-2026-09-21:refs/tags/data-2026-09-21
git push origin refs/tags/data-2026-09-28:refs/tags/data-2026-09-28
git push origin refs/tags/data-2026-10-05:refs/tags/data-2026-10-05
git push origin refs/tags/data-2026-10-12:refs/tags/data-2026-10-12
```

```bash
git clone /tmp/ng-bare /tmp/ng-work
# section 6, dépôt NAVIGUIDE, puis :
cd /tmp/ng-work
git add -A
git status
git commit -m "chore: adapter CI et déploiement au dépôt NAVIGUIDE"
git remote add origin git@github.com:Berry-Mappemonde/NAVIGUIDE.git
git push origin refs/heads/main:refs/heads/main
```

Pas de `--mirror`, pas de `--all`, pas de `--tags` global, pas de
`refs/pull`. `git status` avant le commit ne doit montrer que les
fichiers de la section 6.

Les 16 PR ouvertes au 17 octobre 2026 restent sur l'archive, avec leurs
branches. Le filtre ne les transporte pas (les SHA changent). Numéros :
#529, #530, #533, #534, #536, #540, #541, #542, #543, #544, #545, #546,
#547, #548, #549, #551. #550 est déjà sur `main`. #146, #227, #510, #537
et #552 sont fermées et ne sont pas sur `main`. Rien de tout cela n'est
effacé de l'archive.

## 6. Ce que le premier commit change dans chaque dépôt

Chemins codés en dur aujourd'hui : `~/blue-intelligence-map` et
`/home/ubuntu/blue-intelligence-map`. Cibles :

| Dépôt | Dossier sur le serveur | Hôte du secret `VPS_HOST` |
|---|---|---|
| Blue Intelligence | `/home/ubuntu/blue-intelligence` | `ubuntu@135.125.226.16` |
| NAVIGUIDE | `/home/ubuntu/naviguide` | `ubuntu@13.140.164.185` |

`prepare-ssh.sh` écrit aujourd'hui `REMOTE_APP=/home/ubuntu/blue-intelligence-map`
et, si `VPS_HOST` est vide, `ubuntu@135.125.226.16`. Dans la copie
NAVIGUIDE, retirer ce défaut : un secret oublié doit arrêter le job, pas
déployer sur l'OVH.

### 6.1 Dépôt Blue Intelligence

- `infra/vps/blue-intelligence.service` : `WorkingDirectory` et `ExecStart`
  sous `/home/ubuntu/blue-intelligence/backend`.
- `infra/vps/nginx-blue-intelligence.conf` : les quatre `alias` vers
  `frontend/build/` (robots, sitemap, clé IndexNow, `static/`). Le
  `proxy_pass` vers `127.0.0.1:8001` reste : l'API est sur cette machine.
- `infra/vps/deploy-app.sh` : `APP="$HOME/blue-intelligence"`.
- `infra/vps/sync-public-nginx.sh` : même `APP`. N'installer que le vhost
  `blue-intelligence`. Retirer l'installation du vhost `naviguide` et le
  `sed` qui réécrit `root …/naviguide-app/dist`.
- `infra/vps/ci/apply-pending.sh`, `apply-site.sh`, `prod_jobs_busy.py`,
  `rsync-to-vps.sh` : même dossier. `rsync-to-vps.sh` ne garde que le cas
  `blue-intelligence`.
- `infra/vps/ci/prepare-ssh.sh` : `REMOTE_APP=/home/ubuntu/blue-intelligence`.
  Le défaut d'hôte OVH peut rester.
- `infra/vps/ci/plan_deploy.py` : un seul site. Plus de branche `recette`
  (elle appartient à NAVIGUIDE). Garder le cron de rattrapage et la sonde
  des files uvicorn.
- `.github/workflows/deploy.yml` : un job, cron `*/20 * * * *` conservé,
  plus de jobs `naviguide` ni `simulator`.
- `.github/workflows/ci.yml` : jobs `frontend`, `audit-tags`, `deploy-gate`
  sur `deploy-app.sh`, `sync-public-nginx.sh`, `prepare-ssh.sh`,
  `rsync-to-vps.sh`, `apply-site.sh`, `apply-pending.sh` et
  `test_prod_jobs_busy.py`.
- `.github/dependabot.yml` : retirer les blocs `naviguide-simulator`.
  Ajouter pip sur `/backend`.
- `infra/agents/gh_token.py`, `open_pr.py`, `post_pr_comment.py`,
  `review_collect.py` : `BIM_REPO` par défaut
  `Berry-Mappemonde/Blue-Intelligence`.
- `README.md` : le produit est Blue Intelligence. Lien vers le dépôt
  NAVIGUIDE. Tableau préexistant / nouveau pour le jury GenAI : le seul
  paquet nouveau prévu est `backend/app/agent_poe/` (pas encore dans
  l'arbre).
- `infra/vps/README.md`, `infra/vps/seamap/README.md`,
  `scripts/climatology/README.md`, `scripts/satellite/README.md` : le
  dossier d'application devient `~/blue-intelligence`. Ne pas réécrire
  les plans datés dans `docs/archives/`.
- `.cursor/rules/reparations-sur-github.mdc` : retirer les exemples qui
  ne parlent que du simulateur.

Le dépôt ne contient pas `zap-baseline.yml` ni `infra/vps/naviguide/` :
le filtre les a déjà écartés. `weekly-data-build.yml` part tel quel.

### 6.2 Dépôt NAVIGUIDE

- Les quatre unités `infra/vps/naviguide/*.service` :
  `WorkingDirectory` et `ExecStart` sous `/home/ubuntu/naviguide/...`.
- `deploy-naviguide.sh`, `deploy-simulator.sh`,
  `publish-simulator-from-mac.sh` : `APP` et `REMOTE_APP` =
  `/home/ubuntu/naviguide`.
- `infra/vps/ci/*` : même dossier, hôte sans défaut OVH. `rsync-to-vps.sh`
  ne garde que les cas `naviguide` et `simulator`. Le cas `simulator`
  utilise `--delete` et n'exclut aujourd'hui que `server/voyage_data/` et
  `server/polar_data/*.json`. Ajouter les exclusions
  `server/grib_data/`, `server/forecast_cache/`, `server/saildocs_inbox/`,
  pour qu'un déploiement ne les efface pas s'ils sont encore dans le
  checkout. La section 8 les place de préférence **hors** du checkout.
- `plan_deploy.py` : `www.naviguide.fr` et `simulator.naviguide.fr`.
  La branche `recette` ne déploie que le simulateur, comme aujourd'hui.
  Pas de cron de rattrapage des files Blue Intelligence.
- `.github/workflows/deploy.yml` : ces deux jobs, poussée sur `main` et
  `recette`, `workflow_dispatch`. Pas de cron `*/20`.
- `.github/workflows/ci.yml` : jobs `simulator`, `simulator-e2e`, et un
  `deploy-gate` sur les scripts NAVIGUIDE.
- `.github/dependabot.yml` : retirer le bloc `/frontend`.
- `nginx-naviguide.conf` et `nginx-simulator.conf` : les `location /bi/`
  et `/bi/climatology/` font aujourd'hui
  `proxy_pass http://127.0.0.1:8001/api/…` parce que les trois sites
  étaient sur la même machine. Sur Contabo, l'amont est
  `https://blueintelligence.online/api/…`, avec
  `proxy_ssl_server_name on;` et
  `proxy_set_header Host blueintelligence.online;`. Le navigateur
  continue de parler à `naviguide.fr` : le proxy nginx évite un appel
  direct du navigateur vers l'autre domaine.
- `simulator.env` (sur le serveur, pas dans git) : si `BI_API_URL` vaut
  `http://127.0.0.1:8001/api`, le remplacer par
  `https://blueintelligence.online/api`. Le défaut du code
  (`bi_proxy.py`, `ici_engine.py` `BI_LIVE_API`, `amp_nogo.py`,
  `climatology_atlas.py`, `main.py`) est déjà l'URL publique. L'exemple
  `simulator.env.example` documente le loopback « même VPS » : le commenter
  comme valable seulement quand l'API est sur la même machine.
- `infra/agents/gh_token.py`, `open_pr.py`, `post_pr_comment.py`,
  `review_collect.py`, et `run_lots.py` (`DEFAULT_REPO`) :
  `Berry-Mappemonde/NAVIGUIDE`. Même dépôt dans les prompts de
  `review_agent.py`, `plan_corrections.py`, `devpost_answers.py`,
  `GROK_BOT_ROUTINE.md`, `GROK_BOT_DEVPOST.md`.
- `README.md` : le produit est NAVIGUIDE. L'API Blue Intelligence reste
  `https://blueintelligence.online/api`.
- `.cursor/rules/environnement-utilisateur.mdc` : ajouter Contabo pour
  NAVIGUIDE, OVH pour Blue Intelligence.

`vite.config.js` proxy `/bi` vers le serveur local du simulateur, et
connaît `BI_PROXY_TARGET` plus l'hôte `recette.blueintelligence.online`
(`.blueintelligence.online` dans `allowedHosts`). On ne change pas ce
proxy de développement dans le commit de séparation : il parle au
poste local, pas au Mongo de l'OVH.

Issues ouvertes au 17 octobre 2026, toutes deux NAVIGUIDE : **#432**
(Devpost, citée par `GROK_BOT_DEVPOST.md`) et **#446** (ouverte par le
workflow ZAP). Les transférer vers le dépôt NAVIGUIDE (même propriétaire,
action Transfer d'une issue) ou les recréer, puis corriger l'URL dans
`GROK_BOT_DEVPOST.md`. Les issues fermées restent sur l'archive.

### 6.3 Secrets GitHub, après ce commit

Sur chaque dépôt neuf : `VPS_SSH_KEY` (la clé de déploiement) et
`VPS_HOST` avec la valeur du tableau. Autres secrets, environnements et
règles de protection de branche : **non vérifiés** (il faut un accès
admin). Avant de considérer la liste complète :

```bash
gh secret list --repo Berry-Mappemonde/Blue-Intelligence-Map
```

Recréer sur le bon dépôt neuf chaque secret qui apparaît. Ne pas poser
le `VPS_HOST` de l'OVH sur le dépôt NAVIGUIDE.

## 7. Deux serveurs

Aujourd'hui, un seul dossier `~/blue-intelligence-map` sert les trois
sites. `infra/vps/README.md` décrit le DNS :

- `blueintelligence.online` est derrière Cloudflare, enregistrement A vers
  `135.125.226.16`. On n'y touche pas.
- `www.naviguide.fr` est un A vers `135.125.226.16`, **sans** Cloudflare,
  zone DNS chez OVH.
- `simulator` est un A de la même zone vers `135.125.226.16`.
- Le certificat Let's Encrypt `naviguide.fr` (apex + www, puis
  `simulator` ajouté) est sur l'OVH.

| | Blue Intelligence | NAVIGUIDE |
|---|---|---|
| Machine | OVH `135.125.226.16` | Contabo `13.140.164.185` |
| Dossier | `~/blue-intelligence` | `~/naviguide` |
| Mongo | le `mongod` déjà en place, `127.0.0.1:27017`, base `$DB_NAME` | un `mongod` **neuf**, `127.0.0.1:27017`, base `naviguide_simulator` seulement |
| Sites | `blueintelligence.online` | `www.naviguide.fr`, `simulator.naviguide.fr` |

Le dossier OVH `~/blue-intelligence-map` reste sur le disque. En cas
d'échec, les services OVH sont encore là : on remet les unités systemd
vers ce dossier, et les enregistrements A de `naviguide.fr` vers
`135.125.226.16`.

### 7.1 Préparer Contabo, sans y mettre les données

Utilisateur non root pour la suite, clé SSH, mises à jour. Pare-feu :
22, 80 et 443 seulement. Dans le panneau Contabo, le groupe de sécurité
ne doit pas non plus exposer 27017.

MongoDB 8, canal `noble` comme `install-mongodb.sh`, **sans** lancer ce
script : il exige `DB_NAME` depuis `atlas.env` et crée l'utilisateur
`blue` de Blue Intelligence.

- `bindIp: 127.0.0.1` dans `/etc/mongod.conf`. Si la ligne est autre, ne
  pas continuer.
- `security.authorization: enabled`.
- Compte `admin` (rôle `root` sur `admin`) et compte `naviguide_sim`
  (`readWrite` sur `naviguide_simulator` seulement). Pas de rôle sur une
  base Blue Intelligence : cette base n'existe pas ici.
- Mot de passe nouveau, dans `~/.config/naviguide/simulator.env` sur
  Contabo, clé `SIMULATOR_MONGO_URL`, hôte `127.0.0.1`.

```javascript
use naviguide_simulator
db.createUser({
  user: "naviguide_sim",
  pwd: passwordPrompt(),
  roles: [ { role: "readWrite", db: "naviguide_simulator" } ]
})
```

`passwordPrompt()` évite de laisser le mot de passe dans l'historique
du shell.

Vérifier depuis le Mac que le port n'est pas joignable :

```bash
nc -vz -G 5 13.140.164.185 27017
```

L'échec de connexion est le résultat attendu. Le même contrôle sur
`135.125.226.16` doit échouer aussi (le script d'install l'exige déjà
sur l'OVH).

## 8. Migrer les données NAVIGUIDE

Le transport est SSH, port 22. Le fichier d'archive voyage dans `scp`.
On ne fait pas `ssh -L 27017`, on ne pointe pas `SIMULATOR_MONGO_URL`
vers l'IP de l'OVH, on n'ouvre pas 27017. Le simulateur n'a pas besoin
du Mongo Blue Intelligence : ports, AMP et climatologie passent par
`https://blueintelligence.online/api`.

### 8.1 Copier la sauvegarde de la section 1

Sur le Mac, une fois Contabo joignable en SSH :

```bash
STAMP=LA_DATE_DE_LA_SECTION_1
ssh ubuntu@13.140.164.185 "mkdir -p backups"
scp -r "$HOME/Backups/naviguide-split-$STAMP" ubuntu@13.140.164.185:backups/
ssh ubuntu@13.140.164.185 "cd backups/naviguide-split-$STAMP && sha256sum -c SHA256SUMS"
```

Les sommes doivent coïncider avec le Mac et avec l'OVH.

### 8.2 Restaurer, sans `--drop`

Sur Contabo, base encore vide. Si `comptes-mongo-avant.tsv` dit
« aucune collection », il n'y a rien à restaurer en Mongo : le stock
est sur disque, et on passe au paragraphe suivant.

```bash
. ~/.config/naviguide/simulator.env
# SIMULATOR_MONGO_URL pointe vers 127.0.0.1. Ne pas l'afficher.
mongorestore --uri "$SIMULATOR_MONGO_URL" --gzip \
  --archive="$HOME/backups/naviguide-split-$STAMP/naviguide_simulator-$STAMP.archive.gz" \
  --nsInclude='naviguide_simulator.*'
```

Pas de `--drop`. Si `mongorestore` signale que la cible n'est pas vide,
s'arrêter et regarder le manifeste. Ne pas relancer avec `--drop`.

Replacer les dossiers. Hors du checkout, pour qu'un `rsync --delete`
ne soit pas leur seul exemplaire :

```text
/var/lib/naviguide/voyage_data/     ← voyage_data (sqlite, json, official-store, official_journal)
/var/lib/naviguide/grib_data/
/var/lib/naviguide/forecast_cache/
/var/lib/naviguide/saildocs_inbox/
```

Dans `simulator.env` sur Contabo :

```text
NAVIGUIDE_VOYAGE_DIR=/var/lib/naviguide/voyage_data
NAVIGUIDE_GRIB_DIR=/var/lib/naviguide/grib_data
NAVIGUIDE_FORECAST_CACHE=/var/lib/naviguide/forecast_cache
NAVIGUIDE_SAILDOCS_INBOX=/var/lib/naviguide/saildocs_inbox
BI_API_URL=https://blueintelligence.online/api
SIMULATOR_MONGO_URL=mongodb://naviguide_sim:…@127.0.0.1:27017/naviguide_simulator?authSource=naviguide_simulator
```

`polar_data/` du simulateur n'a pas de variable : le poser dans
`~/naviguide/naviguide-simulator/server/polar_data/` **après** le premier
`rsync` du code, ou avant si le déploiement exclut déjà
`server/polar_data/*.json`. Les polaires de l'ancien site vont dans
`~/naviguide/naviguide/naviguide_workspace/polar_data/`.

`naviguide.env` (clés LLM / Copernicus de l'ancien site) va dans
`~/.config/naviguide/naviguide.env`, chmod 600.

### 8.3 Recompter

Même commande `mongosh` qu'en section 1, sur Contabo, avec le compte
admin de **cette** machine. Écrire `comptes-mongo-apres.tsv`. Même
script Python pour SQLite, en lecture seule, sur
`/var/lib/naviguide/voyage_data/naviguide.sqlite`.

Le tableau du manifeste, une ligne par collection et par table, a trois
colonnes : nombre OVH avant, nombre Contabo après, égalité. Les deux
premières colonnes viennent des fichiers TSV. On ne déclare pas la
migration faite tant qu'une ligne diffère, ou tant qu'un dossier copié
en section 1.2 n'est pas au chemin prévu.

Sur l'OVH, refaire le comptage Blue Intelligence (`$DB_NAME`, dont
`poe_ports`) et le comptage `naviguide_simulator`. Ils doivent être
identiques au TSV d'avant. L'OVH n'a rien perdu. On n'y supprime toujours
rien.

Ajouter ensuite sur Contabo un cron quotidien qui archive
`naviguide_simulator` et le dossier `/var/lib/naviguide`, sur 14 jours,
dans `~/backups/naviguide/` — pas sous le nom `blue-*.archive.gz`. Ce
cron n'existe pas encore : le cron du dépôt ne sauve que la base Blue
Intelligence, et il reste sur l'OVH.

## 9. DNS, puis la liste qui autorise l'archivage

Baisser le TTL des A de la zone `naviguide.fr` avant le jour J (valeur
actuelle : **non vérifiée**, la lire dans le panneau OVH). Le jour J,
chaque A qui vaut `135.125.226.16` pour `www`, `simulator` et l'apex
`naviguide.fr` passe à `13.140.164.185`. Ne pas modifier la zone
Cloudflare de `blueintelligence.online`.

Émettre le certificat sur Contabo à ce moment (`certbot`), pour
`naviguide.fr`, `www.naviguide.fr` et `simulator.naviguide.fr`. Le
certificat de l'OVH reste en place : c'est le retour arrière.

Déployer depuis chaque dépôt neuf (workflow_dispatch) seulement après
les secrets de la section 6.3. Le dépôt NAVIGUIDE doit rsync vers
`~/naviguide` sur Contabo. Le dépôt Blue Intelligence doit rsync vers
`~/blue-intelligence` sur l'OVH.

Liste. Tout est vert avant d'archiver `Blue-Intelligence-Map` :

1. Sur l'OVH, `GET http://127.0.0.1:8001/api/` répond 200.
2. `https://blueintelligence.online/api/` répond 200.
3. `https://www.naviguide.fr` répond 200, et le serveur qui répond est
   Contabo (le dossier `~/naviguide` y est servi).
4. `https://simulator.naviguide.fr` répond 200, même contrôle.
5. Le simulateur lit Blue Intelligence par l'URL publique : une couche
   ports, PoE ou AMP s'affiche, et `BI_API_URL` sur Contabo est
   `https://blueintelligence.online/api`.
6. `systemctl is-active` : `blue-intelligence` est `active` sur l'OVH ;
   `naviguide-simulator` et les services NAVIGUIDE qui tournaient
   (`naviguide-api`, `naviguide-polar`, `naviguide-orchestrator`) sont
   `active` sur Contabo.
7. Les comptes du manifeste sont égaux : collections Blue Intelligence
   sur l'OVH (avant = après), collections `naviguide_simulator`
   (OVH = Contabo), tables SQLite (OVH = Contabo).
8. Un déploiement part de chaque dépôt neuf vers le bon hôte. Une
   poussée sur `Blue-Intelligence-Map` ne déploie plus (workflows
   disabled). Le workflow NAVIGUIDE ne contient pas `135.125.226.16`.
9. `ss -ltn` sur les deux machines montre `27017` sur `127.0.0.1`
   seulement. Depuis le Mac, le `nc` de la section 7.1 échoue toujours.

Tant qu'une ligne est rouge, l'archive reste la référence et les
services OVH restent capables de reprendre le DNS. Quand les neuf lignes
sont vertes, l'archivage GitHub de `Blue-Intelligence-Map` est possible.
L'arrêter des unités NAVIGUIDE sur l'OVH est un geste séparé, après un
mot du propriétaire : ce plan ne donne pas la commande.

Retour arrière DNS, si une ligne 3, 4 ou 5 est rouge : remettre les A de
`naviguide.fr` sur `135.125.226.16`. Les données OVH sont encore là.

Si le 22 octobre 00:00 UTC arrive avant la fin : pas de commit `agent_poe`
dans l'archive avant cette heure. Après cette heure, une branche
`agent-poe` dans l'archive, déclarée dans le README du hackathon GenAI,
en attendant que le dépôt Blue Intelligence soit celui que le jury lit.

## 10. Décisions qui restent au propriétaire

| Sujet | État dans ce plan |
|---|---|
| Noms exacts des deux dépôts neufs | **DÉCISION PROPRIÉTAIRE.** Recommandation en section 0. Stop avant `gh repo create` si les lignes sont vides. |
| Fusionner les 16 PR ouvertes avant le filtre | **DÉCISION PROPRIÉTAIRE.** Elles restent sur l'archive dans tous les cas. Les fusionner avant le filtre les fait entrer dans le `main` filtré. Les reprendre après demande un rebase, parce que les SHA ont changé. Ce plan ne fusionne rien. #545 porte le plan de batch du 16 octobre, absent de `main`. |
| `recette.blueintelligence.online` | **DÉCISION PROPRIÉTAIRE**, non bloquante. Le tunnel de recette des lots est dans la zone Cloudflare de Blue Intelligence. Le laisser là jusqu'après les hackathons évite de casser la nuit des lots. Le déplacer est un autre chantier. |
| Pièces jointes des Releases `data-*` | **DÉCISION PROPRIÉTAIRE**, non bloquante. Les tags git vont dans Blue Intelligence. Les fichiers attachés restent sur l'archive. L'API et `backend/data/` suffisent à reconstruire. |
| Fichiers non commités sur le Mac | **DÉCISION PROPRIÉTAIRE** au vu de `git status --short` (section 2). Non vérifiés ici. |
| Autres secrets GitHub, rulesets, wiki | **Non vérifié.** `gh secret list` sur l'archive, et un coup d'œil au wiki, avant d'archiver. |
| Ancienne valeur de clé dans `.env.example` | **DÉCISION PROPRIÉTAIRE**, non bloquante pour le filtre. Le fichier (retiré le 28 août 2026) n'est recopié dans aucun dépôt neuf. La valeur reste dans l'historique de l'archive. La faire tourner, si elle a servi, est un geste à part : ce plan n'affiche pas la valeur et ne la renouvelle pas. |
| Arrêter nginx et systemd NAVIGUIDE sur l'OVH après le vert | **DÉCISION PROPRIÉTAIRE.** Pas de commande dans ce plan. Les données OVH restent jusqu'à ce mot, et après : les supprimer n'est pas une étape écrite ici. |
| Pytest backend dans la CI Blue Intelligence | Reporté au commit d'après le tri hermétique. Pas un bloquant du 27 octobre. |
| Profil « lots de nuit » pour Blue Intelligence | Plus tard. `run_lots.py` n'est pas dans ce dépôt. Les quatre scripts GitHub génériques y sont, avec `BIM_REPO` à changer. |

Tranché dans ce plan, pour qu'un exécutant n'ait pas à choisir en cours
de route : découpage de `infra/`, `docs/`, `.cursor/`, `Archives/`,
`.github/` ; dossiers purs en une ligne `dossier/` et dossiers mixtes
en fichiers exacts ; historique des renommages (`backend/poe.py`,
`memory/PRD.md`, anciens `docs/` déplacés) ; `.env.example`,
`memory/test_credentials.md`, `.emergent/` et le `package-lock.json` de
la racine hors des deux dépôts neufs ; `.gitconfig` hors des deux
dépôts ; `.gitignore` et `.nvmrc` dans les deux ; cache nginx
climatologie dans les deux ;
`infra/agents/` dans NAVIGUIDE avec les quatre scripts génériques aussi
dans Blue Intelligence ; push de `main` et des cinq tags, jamais
`--mirror` ; NAVIGUIDE sur Contabo, Blue Intelligence et sa base sur
l'OVH ; copie SSH sans exposer 27017 ; pas de suppression OVH.

## 11. Journal des modifications

Chaque ligne est un écart avec le plan du 17 octobre 2026 tel qu'il était
sur `main` avant cette PR. « Arbre » = lecture de `main` `0ad99920`.
« Fusion B » = partie B de l'audit du 17 octobre 2026 sur le plan de
fusion des PR. « Inventaire 4 » = section 4 de l'inventaire avant
séparation. « Base » = note sur la base du simulateur. « Outillage » =
note sur l'outillage CI/CD. « Avant-split » = plan d'avant-split du
17 octobre 2026.

| Changement | Source |
|---|---|
| Le dépôt réel est `Berry-Mappemonde/Blue-Intelligence`, 1 403 commits à `0ad99920`, pas « Blue-Intelligence-Map, 1 249 commits au 16 octobre ». `Blue-Intelligence-Map` est le nom d'**après** le renommage. | Arbre ; Fusion B.1 |
| Section 1 ajoutée en tête : sauvegarde de `naviguide_simulator`, SQLite et dossiers, copies hors OVH, comptes par collection avant et après. | Demande ; Base §1 et §4 ; Avant-split phase 1 ; Fusion B, ajouts du 17 oct. |
| Le cron BI ne sauve pas la base du simulateur. Le compte `blue` ne peut pas la dumper. Dump avec `admin`, base `naviguide_simulator` seulement. | `blue-intelligence-backup.cron` ; `install-mongodb.sh` ; `infra/vps/README.md` ; Base §1.2 et §1.4 |
| `SIMULATOR_MONGO_URL` peut être absent : on copie le disque même si le dump Mongo est vide, et on l'écrit dans le manifeste. | `simulator.env.example` ; `official_store.py` ; Base §1.2 |
| Dossiers en plus de la liste demandée, s'ils existent : `saildocs_inbox/`, `official-store/`, `official_journal/`, `/var/lib/naviguide/voyage_data`, polaires de l'ancien site, `simulator.env`, `naviguide.env`. | `voyage_store.py`, `saildocs.py`, `forecast_cube.py`, `polar_api.py` ; Base §3 et §4.1 |
| Restauration sans `--drop`. Rien n'est supprimé sur l'OVH. Pas de commande d'arrêt des services NAVIGUIDE sur l'OVH. | Demande ; Avant-split (pas de drop en production) |
| Transport par `scp` sur le port 22. 27017 reste sur `127.0.0.1`. Pas de tunnel `ssh -L` vers Mongo, pas d'URI vers l'IP OVH. | Demande ; `install-mongodb.sh` ; Base §4.2 |
| NAVIGUIDE sur Contabo `13.140.164.185`, Blue Intelligence sur l'OVH. Deux `VPS_HOST`, deux dossiers. | Décision du 17 oct. ; Avant-split ; Fusion B.8 et ajouts |
| DNS : A `www` et `simulator` (et l'apex s'il pointe vers l'OVH) vers Contabo. `blueintelligence.online` reste sur Cloudflare / OVH. Certificat neuf sur Contabo, certificat OVH conservé. | `infra/vps/README.md` lignes 217–220 et 362 |
| `proxy_pass` de `/bi/` vers `127.0.0.1:8001` réécrit vers `https://blueintelligence.online` avec le bon en-tête `Host`. `BI_API_URL` de production aligné sur l'URL publique. | `nginx-simulator.conf`, `nginx-naviguide.conf` ; `simulator.env.example` ; Fusion B.4 ; Inventaire 4.3 |
| Le classeur remplace les `--path` de dossiers mixtes. 0 fichier non classé sur l'arbre lu. 0 écart d'historique. | Arbre ; Fusion B.5 ; Inventaire 4.1 et 4.2 |
| Les dossiers purs (`backend/`, `frontend/`, `naviguide-simulator/`, …) sont une ligne `dossier/`, pour garder les fichiers supprimés ou renommés. Les dossiers mixtes restent en fichiers exacts. | Aide de `git-filter-repo` 2.47.0 (`filename_matches` ne suit pas un renommage) ; `git log --diff-filter=R` |
| `backend/poe.py`, `memory/PRD.md`, le prototype (`app/`, `src/`, `prototype_ai_studio/`) et les anciens chemins `docs/` avant leur déplacement vers `docs/archives/` sont des lignes du filtre du bon dépôt. | `git log --diff-filter=R` sur `0ad99920` ; section 4.8 |
| `.env.example`, `memory/test_credentials.md`, `.emergent/` et le `package-lock.json` racine restent dans l'archive. `.env.example` contenait une valeur de clé : elle n'est pas recopiée, et la valeur n'est pas écrite ici. | `git log --diff-filter=D` ; lecture du blob sans l'afficher |
| `.github/`, `.gitignore`, `.nvmrc`, `.zap/` entrent dans le filtre. `.github/` est découpé : build hebdo côté Blue Intelligence, ZAP côté NAVIGUIDE, `ci.yml` / `deploy.yml` / `dependabot.yml` dans les deux puis adaptés. | Arbre ; Fusion B.5 ; Inventaire 4.1 ; Outillage §4 |
| `.gitconfig` (`emergent-agent-e1`) n'est copié dans aucun dépôt neuf. | Arbre ; Fusion B.5 |
| `.vscode/tasks.json` va dans NAVIGUIDE. | Arbre |
| `Archives/Blue-Intelligence/` va dans Blue Intelligence seulement. | Arbre ; Inventaire 4.2 ; Fusion B, ajouts |
| `docs/recette/`, plans simulateur, `LOTS_ORDRE_ET_PROMPTS.md`, `REGLES_WORKFLOW_AGENT.md` vont dans NAVIGUIDE. `docs/data/poe-*.json` et les CDC restent dans Blue Intelligence. `REGLES_PARAMETRES.md` va dans les deux. | Arbre ; `poe_gps_registry.py` ; Inventaire 4.2 ; Outillage §1 |
| `ici-tout.md`, les deux manuels et `ESPRIT_DE_L_APPLICATION.md` vont dans NAVIGUIDE, même là où l'index `docs/README.md` les range autrement. | Lecture de ces fichiers |
| `.cursor/environment.json`, `install.sh`, `start.sh`, `preview.sh` et la règle Mongo vont dans Blue Intelligence. Les hooks simulateur vont dans NAVIGUIDE. Quatre règles communes vont dans les deux. | `.cursor/environment.json` ; Inventaire 4.2 ; Outillage §3.5 et §6 |
| `infra/agents/` va dans NAVIGUIDE. Quatre scripts GitHub vont aussi dans Blue Intelligence. `run_lots.py` n'y va pas. | Inventaire 4.2 et 4.7 ; Outillage §2 et lot O4 |
| `infra/vps/ci/` et les deux fichiers de cache nginx climatologie vont dans les deux dépôts. `infra/searxng/` et `infra/vps/seamap/` restent dans Blue Intelligence. | `deploy-simulator.sh` ; `rsync-to-vps.sh` ; Inventaire 4.3 ; Outillage §5 |
| `git clone --bare --single-branch`, puis push de `refs/heads/main` et, pour Blue Intelligence, des cinq tags `data-*`. Pas de `--mirror`. | Fusion B.5 ; mesure 550 + 16 refs pull et 42 branches |
| Les workflows de l'archive, cron compris, sont désactivés avant le renommage. `batch-pause.sh` est signalé absent. | `deploy.yml`, `weekly-data-build.yml`, `zap-baseline.yml` ; Fusion B.1 point 5 ; Outillage §2.1 |
| Premier commit d'adaptation **avant** le premier push. Liste des fichiers à `blue-intelligence-map` et de `BIM_REPO`. | Fusion B.4 ; Outillage §4 et §5 ; grep sur l'arbre |
| Le défaut OVH de `prepare-ssh.sh` est retiré dans la copie NAVIGUIDE. | `prepare-ssh.sh` lignes 11 et 31 |
| Exclusions `rsync` à ajouter pour `grib_data`, `forecast_cache`, `saildocs_inbox`. | `rsync-to-vps.sh` lignes 77–84 |
| Preuve GenAI : le `log` de `poe_pipeline.py` doit rester en août 2026 après le filtre. `backend/` est gardé en entier. | Arbre (`b4fae8c7`, `--follow` jusqu'au 26 août) ; Fusion B.8 |
| Balayage de motifs de secrets avant push, sans afficher les valeurs. gitleaks non vérifié. | Fusion B.8 |
| Issues #432 et #446 à transférer vers NAVIGUIDE. | `gh issue list` ; Fusion B.7 |
| Les 16 PR ouvertes restent sur l'archive. #550 est sur `main`. Les PR fermées #146, #227, #510, #537, #552 n'y sont pas. `pr-archive/` n'est pas dans git. | `gh pr list` ; Arbre |
| Gros fichiers : max 17,9 Mo, pas de LFS dans la procédure. | `git cat-file` sur toutes les refs ; Fusion B.6 ; Inventaire 4.4 |
| Pytest backend reporté. Les cinq tags `data-*` ne vont pas dans NAVIGUIDE. Les assets de Release ne suivent pas le push. | Outillage §3.3 et §4.3 ; `git for-each-ref refs/tags` |
| Neuf contrôles remplacent les huit de l'ancien §6 (deux machines, comptes simulateur, port 27017 fermé). | Ancien §6 ; Base §4 ; décision serveurs |
| `docs/PLAN_BATCH_2026-10-16.md` et la règle Cursor des specs ne sont pas sur `main` (PR #545). | Arbre ; Outillage §1.3 ; Inventaire 4.5 |

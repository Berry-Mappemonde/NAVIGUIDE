# Séparation des dépôts — Blue Intelligence et NAVIGUIDE

Plan à exécuter à la lettre. Il remplace la version du 17 octobre 2026 qui
décrivait encore un seul VPS et un `git push --mirror`.

Lecture de l'arbre le **17 octobre 2026 au soir** : `main` = `6dabfb84`
(« Merge pull request #544 », 1 429 commits). Le classeur
`scripts/check_split_coverage.py` de cette PR a été passé sur cet arbre,
copié à côté (il n'y est pas encore suivi) : **0 fichier suivi non classé**.

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
- On n'installe pas MongoDB sur Contabo, on n'y crée pas la base
  `naviguide_simulator`, on n'y crée pas l'utilisateur `naviguide_sim`,
  et on ne pose pas `SIMULATOR_MONGO_URL`. Le relevé du 17 octobre 2026
  montre que cette base n'existe pas sur l'OVH : le simulateur lit le
  disque.
- On ne fait pas `mongodump` ni `mongorestore` pour NAVIGUIDE, ni
  `mongorestore --drop`, ni `drop`, ni `delete`, ni `dropDatabase`.
  On ne supprime rien sur l'OVH : ni base, ni fichier, ni vhost nginx,
  ni certificat, ni le dossier `~/blue-intelligence-map`, ni
  `voyage_data/`. Un arrêt de `naviguide-simulator` ne sert qu'à copier
  un SQLite cohérent, et la commande de redémarrage est dans la même
  section. L'arrêt définitif sur l'OVH reste la décision du propriétaire
  (section 10).
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
  `13.140.164.185` (Cloud VPS 6). La machine est déjà en Ubuntu 24.04,
  utilisateur `naviguide`, pare-feu `ufw` ouvert sur 22, 80 et 443
  seulement. L'accès SSH est `naviguide@13.140.164.185`, pas `ubuntu@`.
  Avant le premier `ssh`, confirmer dans le panneau Contabo que cette
  adresse est bien la machine reçue. Si ce n'est pas elle, on s'arrête
  et on corrige l'adresse partout dans les commandes ci-dessous.
- Sur l'OVH, le code tourne dans `~/blue-intelligence-map` et l'accès
  SSH est `ubuntu@135.125.226.16`.

Données NAVIGUIDE, relevé sur l'OVH le 17 octobre 2026. Ce sont des
faits, pas des chemins à deviner :

| Élément | État ce jour-là |
|---|---|
| Bases du `mongod` | `admin`, `blueintel_db`, `config`, `local`. Rien d'autre. |
| Base `naviguide_simulator`, utilisateur `naviguide_sim`, variable `SIMULATOR_MONGO_URL` | absents. Le stock officiel est le dossier disque `official-store/` (`DiskBackend` dans `official_store.py`). |
| `~/blue-intelligence-map/naviguide-simulator/server/voyage_data/` | présent, 5,5 Go. Dedans : `naviguide.sqlite` (`pearls` 11 159, `kv` 95 136, `moments` 1) et `official-store/` (690 Mo, stock RF2). |
| `polar_data/`, `grib_data/`, `saildocs_inbox/` à côté de `voyage_data/` | présents. |
| `forecast_cache/`, `/var/lib/naviguide`, `~/.cache/naviguide` | absents. On ne les crée pas pour la copie. |

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

Le 17 octobre 2026 au soir, le propriétaire a tranché le nom public, la
recette, la CI et les archives (section 10.1). Les deux lignes ci-dessus
restent à remplir : ce sont les noms GitHub des dépôts neufs.

Les autres **DÉCISION PROPRIÉTAIRE** sont en section 10.2. Aucune
n'empêche la sauvegarde (section 1).

## 1. Sauvegarder et compter, avant toute autre action

But : une copie des fichiers NAVIGUIDE hors de l'OVH, avec les comptes
SQLite et les SHA-256, avant le renommage, le filtre et le DNS. Ce n'est
pas une migration Mongo. La base `naviguide_simulator` n'est pas sur le
serveur : il n'y a rien à dumper.

La base Blue Intelligence (`blueintel_db`) n'est pas migrée. On la compte
quand même, pour voir qu'elle n'a pas bougé. Le cron quotidien
(`infra/vps/blue-intelligence-backup.cron`) ne sauve que cette base. Il
ne sauve ni le SQLite ni les dossiers du simulateur. On ne le lance pas
ici, et on n'écrit rien dans `~/backups/mongodb/` : ce cron y efface les
`blue-*.archive.gz` de plus de 14 jours.

Le mot de passe admin est dans
`~/.config/blue-intelligence/mongo.env` (`MONGO_ADMIN_USER`,
`MONGO_ADMIN_PWD`), créé par `infra/vps/install-mongodb.sh`. On ne
l'affiche pas.

### 1.1 Sur l'OVH — vérifier le relevé, compter `blueintel_db`

```bash
ssh ubuntu@135.125.226.16
```

```bash
set +x
whoami
STAMP=$(date -u +%F)
DEST="$HOME/backups/naviguide-split-$STAMP"
APP="$HOME/blue-intelligence-map"
SIM="$APP/naviguide-simulator/server"
mkdir -p "$DEST"
test "$(whoami)" = ubuntu || { echo "STOP compte inattendu"; exit 1; }
test -d "$APP" || { echo "STOP dossier $APP absent"; exit 1; }

. "$HOME/.config/blue-intelligence/mongo.env"
test "$DB_NAME" = blueintel_db || { echo "STOP DB_NAME n'est pas blueintel_db"; exit 1; }
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
  grep -E '^(NAVIGUIDE_VOYAGE_DIR|NAVIGUIDE_GRIB_DIR|NAVIGUIDE_FORECAST_CACHE|NAVIGUIDE_SAILDOCS_INBOX|NAVIGUIDE_OFFICIAL_STORE_DIR|BI_API_URL)=' \
    "$ENV_FILE" 2>/dev/null || true
} > "$DEST/etat-env.txt"
grep -q '^SIMULATOR_MONGO_URL=absent$' "$DEST/etat-env.txt" || { echo "STOP SIMULATOR_MONGO_URL est posé : ne pas continuer ce plan"; exit 1; }

mongosh --quiet "$MONGO_URI" --eval '
const names = db.adminCommand({listDatabases:1}).databases.map(d => d.name).sort();
print("DBS " + names.join(","));
const users = db.getSiblingDB("admin").system.users.distinct("user");
print("SIM_USER " + (users.indexOf("naviguide_sim") >= 0 ? "présent" : "absent"));
' | tee "$DEST/etat-mongo.txt"
grep -q 'DBS admin,blueintel_db,config,local$' "$DEST/etat-mongo.txt" || { echo "STOP liste de bases différente du 17 oct."; exit 1; }
grep -q 'SIM_USER absent$' "$DEST/etat-mongo.txt" || { echo "STOP utilisateur naviguide_sim apparu"; exit 1; }

mongosh --quiet "$MONGO_URI" --eval '
const d = db.getSiblingDB("blueintel_db");
d.getCollectionNames().filter(c => !c.startsWith("system.")).sort()
  .forEach(c => print("blueintel_db\t" + c + "\t" + d.getCollection(c).countDocuments()));
' | tee "$DEST/comptes-mongo-avant.tsv"
unset MONGO_URI
```

`etat-env.txt` ne contient pas l'URI : elle porte le mot de passe. Une
ligne `STOP` : on ne passe pas à la copie. Une base `naviguide_simulator`
apparue après le 17 octobre changerait la nature de la migration. Ce
plan ne la dump pas « pour voir ».

Le code Blue Intelligence ouvre notamment `poe_ports`, `poe_seed_ports`,
`poe_runs`, `eez_zones`, `projects`, `marinas`, `capitaineries`,
`amp_sites`, `review_gold`. Le tableau réel de `blueintel_db` fait foi.
Il n'y a pas de collection simulateur à compter : le stock RF2 est le
dossier `official-store/`.

Contrôle des chemins. Un dossier obligatoire absent, ou un dossier
absent le 17 octobre devenu présent : `STOP`. On ne le copie pas en
silence.

```bash
for d in "$SIM/voyage_data" "$SIM/polar_data" "$SIM/grib_data" "$SIM/saildocs_inbox"; do
  test -d "$d" || { echo "STOP absent $d"; exit 1; }
  echo "présent $d"
done
test -f "$SIM/voyage_data/naviguide.sqlite" || { echo "STOP sqlite absent"; exit 1; }
test -d "$SIM/voyage_data/official-store" || { echo "STOP official-store absent"; exit 1; }
for ghost in "$SIM/forecast_cache" /var/lib/naviguide "$HOME/.cache/naviguide"; do
  if [ -e "$ghost" ]; then echo "STOP apparu depuis le 17 oct. : $ghost"; exit 1; fi
  echo "toujours absent $ghost"
done
{
  echo "chemin octets"
  du -sb "$SIM/voyage_data" "$SIM/voyage_data/official-store" \
    "$SIM/polar_data" "$SIM/grib_data" "$SIM/saildocs_inbox"
} | tee "$DEST/etat-tailles-source.txt"
```

Place libre : la copie locale pèse la taille de `voyage_data` (5,5 Go
le 17 octobre) plus les trois autres dossiers. On exige 8 Go libres.
S'il en manque, on s'arrête. On ne supprime rien pour faire de la place.

```bash
free=$(df -B1 --output=avail "$HOME" | tail -1)
echo "libre_octets $free" | tee "$DEST/etat-disque.txt"
test "$free" -ge 8000000000 || { echo "STOP moins de 8 Go libres"; exit 1; }
```

### 1.2 Sur l'OVH — copie cohérente, puis redémarrage

`naviguide-simulator` est arrêté le temps de la copie, puis relancé
avant la section 2. `systemctl stop` ne désinstalle pas l'unité et ne
touche pas aux fichiers. On n'arrête pas `blue-intelligence`.

```bash
sudo systemctl stop naviguide-simulator
test "$(systemctl is-active naviguide-simulator)" = inactive || { echo "STOP le simulateur tourne encore"; exit 1; }
command -v fuser >/dev/null || { echo "STOP fuser absent (paquet psmisc) — relancer le service avant d'installer quoi que ce soit"; sudo systemctl start naviguide-simulator; exit 1; }
if sudo fuser "$SIM/voyage_data/naviguide.sqlite"; then
  echo "STOP un processus tient encore le sqlite"
  sudo systemctl start naviguide-simulator
  exit 1
fi
echo "sqlite libre"

mkdir -p "$DEST/fichiers/voyage_data"
sqlite3 "$SIM/voyage_data/naviguide.sqlite" ".backup $DEST/fichiers/voyage_data/naviguide.sqlite"
test -s "$DEST/fichiers/voyage_data/naviguide.sqlite" || { echo "STOP backup sqlite vide"; sudo systemctl start naviguide-simulator; exit 1; }

rsync -a \
  --exclude 'naviguide.sqlite' \
  --exclude 'naviguide.sqlite-wal' \
  --exclude 'naviguide.sqlite-shm' \
  "$SIM/voyage_data/" "$DEST/fichiers/voyage_data/"
rsync -a "$SIM/polar_data/" "$DEST/fichiers/polar_data/"
rsync -a "$SIM/grib_data/" "$DEST/fichiers/grib_data/"
rsync -a "$SIM/saildocs_inbox/" "$DEST/fichiers/saildocs_inbox/"

sudo systemctl start naviguide-simulator
test "$(systemctl is-active naviguide-simulator)" = active || { echo "STOP redémarrage échoué — ne rien faire d'autre avant que ce service soit active"; exit 1; }
```

Le fichier copié est celui de `.backup`, pas une copie brute du SQLite
ouvert. `.backup` est la commande retenue. On ne fait `.dump` en plus :
cela doublerait l'espace. Si `.backup` échoue, on relance le service
comme la ligne `STOP backup sqlite vide`, et on s'arrête.

`.dump` n'est le recours que si `sqlite3` refuse `.backup`. Dans ce cas
seulement, service toujours arrêté :

```bash
sqlite3 "$SIM/voyage_data/naviguide.sqlite" .dump > "$DEST/fichiers/voyage_data/naviguide.sql"
```

Puis on note `format=sql` dans le manifeste. La section 8 restaure alors
avec `sqlite3 naviguide.sqlite < naviguide.sql` au lieu de copier le
fichier `.backup`. On ne mélange pas les deux formats.

Comptes sur **le fichier de sauvegarde** (le service a déjà repris, le
fichier vivant peut avoir bougé) :

```bash
python3 - << PY | tee "$DEST/comptes-sqlite-avant.tsv"
import sqlite3
path = "$DEST/fichiers/voyage_data/naviguide.sqlite"
con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY 1"
for (name,) in con.execute(query):
    ident = '"' + name.replace('"', '""') + '"'
    n = con.execute(f"SELECT COUNT(*) FROM {ident}").fetchone()[0]
    print(f"{name}\t{n}")
con.close()
PY
grep -q '^pearls	' "$DEST/comptes-sqlite-avant.tsv" || { echo "STOP table pearls absente"; exit 1; }
grep -q '^kv	' "$DEST/comptes-sqlite-avant.tsv" || { echo "STOP table kv absente"; exit 1; }
grep -q '^moments	' "$DEST/comptes-sqlite-avant.tsv" || { echo "STOP table moments absente"; exit 1; }
```

Le 17 octobre les comptes étaient `pearls` 11 159, `kv` 95 136,
`moments` 1. Le site a pu écrire depuis : le chiffre du jour est le
contrat de la copie, pas une erreur. Un compte à 0, ou une table
manquante, est un `STOP`.

Secrets, s'ils sont là. On ne les affiche pas.

```bash
mkdir -p "$DEST/secrets"
cp -a "$HOME/.config/naviguide/simulator.env" "$DEST/secrets/" 2>/dev/null || echo "simulator.env absent"
cp -a "$HOME/.config/naviguide/naviguide.env" "$DEST/secrets/" 2>/dev/null || echo "naviguide.env absent"
chmod 700 "$DEST/secrets"
```

Sommes, après le redémarrage (la sauvegarde ne change plus) :

```bash
(
  cd "$DEST"
  find fichiers -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum comptes-mongo-avant.tsv comptes-sqlite-avant.tsv etat-env.txt \
    etat-mongo.txt etat-tailles-source.txt etat-disque.txt >> SHA256SUMS
)
```

On ne copie pas vers Contabo : `~/backups/mongodb/blue-*.archive.gz`,
`backend/data/`, `~/.config/blue-intelligence/mongo.env`, `backend/.env`,
ni la base `blueintel_db`.

### 1.3 Sur le Mac — la copie qui quitte le serveur

`voyage_data` pesait 5,5 Go. `rsync` reprend si la liaison coupe.
`scp -r` ne reprend pas : on ne l'utilise pas pour ce dossier.

```bash
STAMP=$(date -u +%F)
mkdir -p "$HOME/Backups/naviguide-split-$STAMP"
rsync -a --partial ubuntu@135.125.226.16:backups/naviguide-split-$STAMP/ \
  "$HOME/Backups/naviguide-split-$STAMP/"
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
    if got != digest:
        print("ECHEC", rel)
        bad += 1
print("fichiers", sum(1 for line in pathlib.Path("SHA256SUMS").read_text().splitlines() if line.strip()), "echecs", bad)
raise SystemExit(bad)
PY
```

Le chemin distant est relatif au dossier personnel du compte `ubuntu`.
La dernière ligne doit finir par `echecs 0`. Une ligne `ECHEC` : on s'arrête,
on ne supprime pas la copie OVH, on relance le `rsync`. Écrire à côté,
sur le Mac seulement,
un `MANIFESTE.md` : date, les quatre dossiers, les comptes `blueintel_db`,
les comptes `pearls` / `kv` / `moments`, la phrase
`SIMULATOR_MONGO_URL=absent`, et la comparaison avec le relevé du
17 octobre. Ne pas commiter ce manifeste.

La section 8 refait une copie cohérente le jour du transfert (les
fichiers auront vécu entre-temps) et compare les SHA-256 de **cette**
copie-là. Tant que le manifeste de la section 1 n'existe pas sur le Mac,
on ne passe pas à la section 2.

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
les fichiers locaux restent **non vérifiés**. La PR #545 est sur `main`
(`7d1f8d14`). Ses deux fichiers sont classés NAVIGUIDE (section 4.2).

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

Le filtre qui était sur `main` avant cette PR ne gardait, pour Blue
Intelligence, que
`backend/ frontend/ infra/ docs/ scripts/ seed/ README.md LICENSE*`,
et envoyait à NAVIGUIDE `naviguide-simulator/ naviguide/ Archives/ .cursor/`
sans liste de fichiers. `git push --mirror` fermait la procédure.
La classification des 132 documents (PR #553, section 4.9) part de ce
filtre-là : tout `docs/` aurait suivi Blue Intelligence, tout `Archives/`
et tout `.cursor/` auraient suivi NAVIGUIDE. Le classeur de cette PR
découpe ces trois arbres. Cette PR ne déplace aucun fichier et ne
fusionne pas la #553.

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
| `naviguide/` | 182 fichiers | NAVIGUIDE, par le filtre, pour ne rien perdre. C'est l'ancien planificateur (`www.naviguide.fr`, `csw6hpki.run.complete.dev`). Le premier commit du dépôt filtré le déplace sous `Archives/naviguide-planificateur/` (section 6.4). Il n'est plus déployé. `naviguide/naviguide-app/.env` et `.env.production` sont suivis : seulement des `VITE_*` (localhost, ou `https://www.naviguide.fr`). Pas une clé. |
| `Archives/` | `Blue-Intelligence/`, `naviguide-nova/`, `naviguide-navsecops/`, `README.md` | Découpé en 4.5. |
| `.cursor/` | 19 fichiers | Découpé en 4.6. |

Absents de ces deux listes, et présents sur `main` :

| Chemin | Où il va |
|---|---|
| `.github/` | Découpé fichier par fichier (4.7). Un bloc unique aurait mis le ZAP du simulateur dans Blue Intelligence et le build hebdo des données dans NAVIGUIDE. |
| `.gitignore` | Les deux. C'est lui qui ignore `.env*`, `node_modules/`, `build/`, `.venv/`. Sans lui, un `backend/.env` neuf ne serait plus ignoré. |
| `.nvmrc` | Les deux. Contient `24`. `ci.yml` et `deploy.yml` font `node-version-file: .nvmrc`. |
| `.zap/rules.tsv` | NAVIGUIDE. Le workflow ZAP vise aujourd'hui `https://simulator.naviguide.fr`. Après la bascule, la cible est `https://naviguide.fr` (section 6.4). On n'active pas ce workflow avant que la liste de la section 9 soit verte. |
| `.vscode/tasks.json` | NAVIGUIDE. Une tâche « Simulateur NAVIGUIDE (Mac) ». |
| `.gitconfig` | **Aucun des deux.** Il fixe `user.name` à `emergent-agent-e1`. Il reste dans l'archive. |

Fichiers qu'on ne cherchera pas dans le filtre, parce qu'ils ne sont pas
sur `main` : `AGENTS.md`, `backend/.gitignore`, `frontend/.gitignore`,
`docs/PLAN_CORRECTIONS_2026-10-16-s7.md` (PR #510 fermée, non fusionnée),
`infra/agents/batch-pause.sh`, `batch-resume.sh`, `export_transcript.py`,
`review_lots.py`, `pr-archive/`.

### 4.2 Le classeur

`scripts/check_split_coverage.py` est la liste exécutable. Il lit
`git ls-files`, les fichiers supprimés et les renommages. Il s'arrête
si un fichier suivi n'a pas de classe, ou si un ancien chemin n'est
couvert par aucun des deux fichiers de filtre.

On le lance sur la tête de `main`, pas seulement sur la branche de
cette PR. Le 17 octobre 2026 au soir, cette tête est `6dabfb84`. Le
script n'y est pas encore suivi : on copie celui de cette PR, puis on
mesure. Le résumé de `--emit` va sur la sortie d'erreur. Le fichier de
chemins ne reçoit que la sortie standard.

```bash
git fetch origin main
git worktree add --detach /tmp/split-main origin/main
cp scripts/check_split_coverage.py /tmp/split-main/scripts/check_split_coverage.py
cd /tmp/split-main
python3 scripts/check_split_coverage.py --self-test
python3 scripts/check_split_coverage.py
python3 scripts/check_split_coverage.py --emit bi > /tmp/bi-paths.txt
python3 scripts/check_split_coverage.py --emit ng > /tmp/ng-paths.txt
```

La première commande tient 64 cas fixes. La deuxième doit finir par
`non classés : 0` et `écarts d'historique : 0`, et son code de sortie
est 0. Si l'historique a un trou, `--emit` n'écrit pas le fichier et
le code de sortie est 1.

Lecture du 17 octobre 2026 au soir, script copié et non suivi, sur
`6dabfb84` :

| Classe | Nombre |
|---|---|
| Fichiers suivis | 1 853 |
| Blue Intelligence seul | 574 |
| NAVIGUIDE seul | 1 241 |
| Les deux | 35 |
| Exclus (`.gitconfig` et deux doublons nova, encore suivis) | 3 |
| Non classé | 0 |
| Écarts d'historique | 0 |
| Lignes de `/tmp/bi-paths.txt` | 91 |
| Lignes de `/tmp/ng-paths.txt` | 116 |

`/tmp/ng-paths.txt` contient `docs/PLAN_BATCH_2026-10-16.md` et
`.cursor/rules/specs-suivent-l-interface.mdc`. `/tmp/bi-paths.txt` ne
les contient pas.

Le jour où cette PR est sur `main`, le script devient un fichier suivi
de plus, classé Blue Intelligence par la ligne de dossier `scripts/`.
Les comptes passent à 1 854 fichiers suivis et 575 pour Blue
Intelligence seul. Les lignes de chemins restent 91 et 116.

On s'arrête si `non classés` n'est pas 0, si `écarts d'historique`
n'est pas 0, si l'un des deux fichiers de la #545 manque dans le
fichier NAVIGUIDE, ou s'il apparaît dans le fichier Blue Intelligence.
Un fichier arrivé sur `main` après `6dabfb84` n'a pas encore de classe :
le script s'arrête, et on le classe avant de filtrer. Les comptes de
la branche de cette PR ne servent pas de seuil : elle part de
`0ad99920`, et le script y est déjà suivi.

Le fichier de chemins mélange deux formes, et il ne faut pas les
échanger :

- Un dossier **pur** est une seule ligne `dossier/`. Elle garde aussi
  les fichiers qui y ont vécu puis ont été renommés ou supprimés.
  `git filter-repo` ne suit pas les renommages. Remplacer `backend/`
  par la liste des fichiers de `main` oublierait `backend/poe.py`.
- Un dossier **mixte** reste en fichiers exacts. Ne pas le réduire à
  une ligne `infra/`, `docs/`, `.cursor/`, `Archives/` ou `.github/` :
  c'est le trou d'origine. `Archives/naviguide-nova/` non plus : deux
  de ses markdown sont des doublons exclus, le reste part dans
  NAVIGUIDE. `infra/vps/ci/` est une ligne de dossier seulement dans
  le fichier Blue Intelligence, qui garde aussi le `README.md`. Le
  fichier NAVIGUIDE liste les scripts un par un et omet ce `README.md`.

### 4.3 `infra/`

| Chemin | Dépôt | Raison |
|---|---|---|
| `infra/vps/blue-intelligence.service`, `deploy-app.sh`, `nginx-blue-intelligence.conf`, `install-mongodb.sh`, `setup-memory.sh`, `sync-public-nginx.sh`, `blue-intelligence-backup.cron`, `sync-from-atlas.sh` | Blue Intelligence | Services, nginx et Mongo de `blueintelligence.online`. `sync-from-atlas.sh` est conservé et **ne s'exécute pas** (verrou `FORCE_RESYNC`). |
| `infra/vps/seamap/` | Blue Intelligence | Tuiles servies par l'OVH. Le simulateur les lit en HTTPS, il n'a pas le script. |
| `infra/searxng/` | Blue Intelligence | Recherche des ports d'entrée. L'environnement Cursor BI ouvre le port 8888. |
| `infra/vps/naviguide/` | NAVIGUIDE | Unités, nginx et scripts. Après la section 6.4, seul le simulateur (renommé NAVIGUIDE) est installé, sur `naviguide.fr`. Les trois unités de l'ancien planificateur ne sont pas démarrées. |
| `infra/vps/ci/` sauf `README.md` | Les deux | `plan_deploy.py`, `rsync-to-vps.sh`, `prepare-ssh.sh`, `apply-site.sh`, `apply-pending.sh`, `prod_jobs_busy.py`, `test_prod_jobs_busy.py` déploient aujourd'hui les trois sites. Chaque dépôt réécrit sa copie (section 6). `prod_jobs_busy.py` ne sert qu'à Blue Intelligence : la copie NAVIGUIDE le laisse en place et ne l'appelle plus. Le fichier Blue Intelligence porte le dossier en une ligne `infra/vps/ci/`. Le fichier NAVIGUIDE porte chaque script, sans le `README.md`. |
| `infra/vps/ci/README.md` | Blue Intelligence | La sonde de deploy et le User-Agent qui passe Cloudflare. La classification #553 le range (b). Une ligne `infra/vps/ci/` dans le fichier NAVIGUIDE l'emporterait avec les scripts. |
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

Les deux dépôts reçoivent le fichier entier. Le premier commit raccourcit
la copie qui n'est pas l'original (section 6.0) :

- `docs/REGLES_PARAMETRES.md` — original Blue Intelligence. Sections 3.1
  à 3.6 : catalogue Blue Intelligence (`backend/data/run_rules.json`).
  Sections 3.7 à 3.10 : constantes du simulateur (lots C2, C4, C6, C7),
  citées par `docs/audits/CALCULS.md` et par les prompts de lots. La
  copie NAVIGUIDE garde le principe et les sections 3.7 à 3.10.
- `docs/README.md` — original NAVIGUIDE. Blue Intelligence en reçoit un
  index court (cahiers, PoE, plan GenAI).
- `docs/HACKATHON_PLAN.md` — original Blue Intelligence. Index des trois
  plans du 17 octobre. La copie NAVIGUIDE garde les lignes séparation et
  Nebius ; la ligne GenAI devient un lien vers l'autre dépôt.
- `docs/PLAN_SEPARATION_DEPOTS.md` — original Blue Intelligence (ce
  fichier, en entier). La copie NAVIGUIDE garde les sections qui nomment
  son dépôt, la preuve d'historique et les dix contrôles.
- `docs/check_md_links.py` — outil, hors des 132 documents. Les deux
  index en ont besoin. Il reste entier dans les deux dépôts.

`docs/ETAT_DES_LIEUX_DOCS.md` et `docs/PRD.md` restent dans Blue
Intelligence, à leur chemin actuel. La classification #553 les range (d) :
une PR ultérieure pourra les déplacer dans `docs/archives/` de ce dépôt.
Cette PR ne les déplace pas.

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
- `docs/archives/nvidia-llm-audit.md` → NAVIGUIDE. L'ancien ordre de
  repli NIM, bandeau « remplacé ». L'ordre vivant est dans `README.md`
  et `docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md`. L'ancien chemin
  `docs/nvidia-llm-audit.md` suit le même dépôt (section 4.8).
- `docs/archives/HACKATHON_OPEN_AGENT_2026.md` → Blue Intelligence.

Tout autre `docs/*.md` de plan, de lot, de film ou de hackathon Nebius
est NAVIGUIDE, y compris les dix-sept plans que la #553 range (d) et
qui sont encore à la racine de `docs/`. Ils restent à ce chemin. Une
PR ultérieure pourra les déplacer dans `docs/archives/` du dépôt
NAVIGUIDE. La liste fermée est dans le script (`DOC_BI`, `DOC_NG`) et
elle reprend la #553 fichier par fichier (section 4.9).

### 4.5 `Archives/`

| Chemin | Dépôt |
|---|---|
| `Archives/Blue-Intelligence/` | Blue Intelligence, en une ligne de dossier. Manuels, extraction, notes VPS. |
| `Archives/naviguide-navsecops/` | NAVIGUIDE, en une ligne de dossier. Les copies canoniques de `docs/PLAN_DEV_NOVA.md` et `docs/SETUP_NOVA_CREDITS.md` sont ici. |
| `Archives/naviguide-nova/README.md`, `llm/llm_utils.py`, `orchestrator/graph.py`, `orchestrator/nodes.py` | NAVIGUIDE, quatre lignes exactes. |
| `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` et `docs/SETUP_NOVA_CREDITS.md` | Aucun des deux dépôts neufs. Mêmes octets que les copies navsecops (3 063 et 8 072). Ils restent dans le monodépôt. On ne les supprime pas. On ne réécrit aucun fichier de `Archives/naviguide-nova/` : ni ces deux markdown, ni le README, ni le code. La décision de les retirer de la tête est annulée. |
| `Archives/README.md` | Les deux. Original NAVIGUIDE. La copie Blue Intelligence ne garde que les paragraphes `Archives/Blue-Intelligence/`. |

### 4.6 `.cursor/`

| Chemin | Dépôt |
|---|---|
| `environment.json`, `install.sh`, `start.sh`, `preview.sh` | Blue Intelligence. L'environnement s'appelle « Blue Intelligence » et lance l'API 8001 plus le frontend 3000. |
| `rules/base-de-donnees-vps.mdc` | Les deux. Original Blue Intelligence : Mongo vivant sur l'OVH, Atlas gelé, `sync-from-atlas.sh` interdit. La copie NAVIGUIDE, au premier commit, tient en trois phrases : le simulateur n'a pas de Mongo, `blueintel_db` reste sur l'OVH, on ne lance pas `sync-from-atlas.sh`. |
| `hooks.json` et `hooks/simulator-*` | NAVIGUIDE. |
| `rules/anti-regression-visuelle-simulateur.mdc`, `rules/naviguide-simulator-preview.mdc`, `rules/specs-suivent-l-interface.mdc` | NAVIGUIDE. La troisième est sur `main` depuis la #545. |
| `rules/environnement-utilisateur.mdc`, `modeles-cursor-uniquement.mdc`, `reparations-sur-github.mdc` | Les deux. Original Blue Intelligence. Dans la copie NAVIGUIDE, la règle d'environnement gagne une ligne : le simulateur est sur Contabo, Blue Intelligence reste sur l'OVH. `modeles-cursor-uniquement.mdc` et `reparations-sur-github.mdc` restent entiers dans les deux dépôts. |
| `rules/pas-de-verification-video.mdc` | Les deux. Original NAVIGUIDE. La copie Blue Intelligence garde les trois interdictions : pas de vidéo, preuve par tests, `curl` ou capture fixe. |

### 4.7 Workflows

| Fichier | Dépôt | Après le filtre, avant le premier push |
|---|---|---|
| `.github/workflows/ci.yml` | Les deux | Blue Intelligence garde `frontend`, `audit-tags`, et un `deploy-gate` limité à ses scripts. NAVIGUIDE garde `changes`, `simulator`, `simulator-e2e`, et un `deploy-gate` limité aux siens. Diff en section 6.6. |
| `.github/workflows/deploy.yml` | Les deux | Blue Intelligence garde le cron OVH. NAVIGUIDE déploie `naviguide.fr` sur Contabo à chaque poussée sur `main`. Diff en section 6.6. |
| `.github/workflows/weekly-data-build.yml` | Blue Intelligence seul | L'URL reste `https://blueintelligence.online`. |
| `.github/workflows/zap-baseline.yml` | NAVIGUIDE seul | La cible devient `https://naviguide.fr`. On n'active le workflow qu'après le vert de la section 9. |
| `.github/dependabot.yml` | Les deux | Blue Intelligence : npm `/frontend`, pip `/backend`, github-actions. NAVIGUIDE : npm `/naviguide-simulator`, pip `/naviguide-simulator/server`, github-actions. |

`.gitignore`, `.nvmrc`, `.github/` et `.zap/` ne font pas partie des
132 documents de la PR #553. Le découpage du tableau est celui qui
reste : `.gitignore` et `.nvmrc` dans les deux (le premier ignore
`.env*`, `node_modules/`, `build/`, `.venv/` ; le second contient `24`,
lu par `node-version-file`) ; `ci.yml`, `deploy.yml` et `dependabot.yml`
dans les deux, puis adaptés ; `weekly-data-build.yml` dans Blue
Intelligence seul ; `zap-baseline.yml` et `.zap/rules.tsv` dans
NAVIGUIDE seul.

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
`docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.

`memory/PRD.md` a été renommé en `docs/PRD.md`. Sans cette ligne, le
début du PRD disparaît. `memory/test_credentials.md` ne part pas avec :
c'est un aide-mémoire de noms de clés, pas le PRD.

Même traitement côté NAVIGUIDE pour les plans déplacés vers
`docs/archives/` ou `docs/audits/` : l'ancien chemin
(`docs/PLAN_UI_PRODUIT_SIMULATEUR.md`,
`docs/hackathon-nebius-nvidia.md`,
`docs/PROFIL_BUILD_PROD_2026-09-19.md`, et les autres du même mouvement)
est une ligne du fichier NAVIGUIDE. La liste est `HIST_NG_FILES` dans
le script. Elle comprend `docs/nvidia-llm-audit.md`, ancien chemin de
`docs/archives/nvidia-llm-audit.md`. `naviguide-simulator/` en dossier
couvre déjà les specs e2e déplacées vers `e2e-archive/`.

Restent dans l'archive seulement. Ils ne sont dans aucun des deux
fichiers de chemins :

| Chemin | Raison |
|---|---|
| `.gitconfig` | Encore suivi. Identité `emergent-agent-e1`. |
| `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` | Encore suivi. Doublon de la copie navsecops. La classification #553 le range (e). Il reste dans le monodépôt. Le filtre l'exclut. On ne le supprime pas. |
| `Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md` | Encore suivi. Même traitement, 8 072 octets. |
| `.env.example` | Retiré le 28 août 2026. Il contenait une valeur de clé API. La recopier dans un dépôt neuf la republierait. |
| `memory/test_credentials.md` | Noms de clés et URL locale. Le nom du fichier dit « credentials ». |
| `.emergent/` | Outillage de l'ancienne plateforme, pas un des deux produits. |
| `package-lock.json` à la racine | Ancien gabarit. Le `frontend/package-lock.json` du produit, lui, va dans Blue Intelligence. |

### 4.9 Correspondance avec les 132 documents (PR #553)

La PR #553 (`cursor/menage-documentaire-proposition-39d0`, commit
`9c6f6e0d`, fichier `docs/MENAGE_DOCUMENTAIRE_PROPOSITION.md`) classe
132 documents de `main` : 46 vers NAVIGUIDE (a), 35 vers Blue
Intelligence (b), 12 vers les deux (c), 37 vers `docs/archives/` du
dépôt propriétaire (d), 2 à retirer des dépôts neufs (e). Cette PR ne
fusionne pas la #553 et ne déplace aucun de ces fichiers.

Le classeur a été comparé à ce tableau, chemin par chemin. **132
documents, 0 écart.** Un document (d) suit le dépôt nommé dans la #553
et **garde son chemin actuel**. Les 18 déjà sous `docs/archives/` y
restent (15 NAVIGUIDE, 3 Blue Intelligence). Les 19 encore à la racine
de `docs/` y restent aussi : 17 plans NAVIGUIDE, plus
`docs/ETAT_DES_LIEUX_DOCS.md` et `docs/PRD.md` pour Blue Intelligence.
Les ranger dans `docs/archives/` est une PR ultérieure.

Les 12 communs. `git filter-repo` copie le fichier entier dans les deux
dépôts. La copie qui n'est pas l'original se raccourcit au premier
commit (section 6.0).

| Original | Documents |
|---|---|
| Blue Intelligence (9) | `.cursor/rules/base-de-donnees-vps.mdc`, `environnement-utilisateur.mdc`, `modeles-cursor-uniquement.mdc`, `reparations-sur-github.mdc`, `README.md`, `docs/HACKATHON_PLAN.md`, `docs/PLAN_SEPARATION_DEPOTS.md`, `docs/REGLES_PARAMETRES.md`, `infra/vps/README.md` |
| NAVIGUIDE (3) | `.cursor/rules/pas-de-verification-video.mdc`, `docs/README.md`, `Archives/README.md` |

Six chemins du classeur d'avant cette relecture ne suivaient pas la #553.
Ils sont alignés :

| Chemin | Avant | Après |
|---|---|---|
| `.cursor/rules/base-de-donnees-vps.mdc` | Blue Intelligence seul | Les deux. Original Blue Intelligence. |
| `docs/ETAT_DES_LIEUX_DOCS.md` | Les deux | Blue Intelligence seul, chemin actuel. |
| `docs/archives/nvidia-llm-audit.md` et l'ancien chemin `docs/nvidia-llm-audit.md` | Blue Intelligence | NAVIGUIDE. |
| `infra/vps/ci/README.md` | Les deux, parce que le dossier `infra/vps/ci/` l'emportait | Blue Intelligence seul. Les scripts du même dossier restent dans les deux. |
| `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` et `SETUP_NOVA_CREDITS.md` | NAVIGUIDE, parce que le dossier entier partait | Aucun des deux dépôts neufs. Les copies canoniques sous `Archives/naviguide-navsecops/docs/` partent dans NAVIGUIDE. Le dossier nova n'est pas modifié. |

`.github/`, `.gitignore`, `.nvmrc` et `.zap/` sont hors de ces 132.
Leur place est celle des sections 4.1 et 4.7. `docs/check_md_links.py`
est un outil, hors des 132, présent dans les deux dépôts.

`docs/PLAN_BATCH_2026-10-16.md` et
`.cursor/rules/specs-suivent-l-interface.mdc` sont sur `main` depuis
la fusion de la PR #545 (`7d1f8d14`, 17 octobre 2026). Le classeur les
envoie dans NAVIGUIDE. Les PR fermées
#510 et #227 sont récupérées après le filtre, section 6.4 : le plan
s7 sous `docs/archives/` de NAVIGUIDE, l'outil de fiches sous
`docs/archives/` de Blue Intelligence. Le filtre ne les invente pas.
Cette PR ne les copie pas.

Le 17 octobre au soir, le propriétaire suit les recommandations de la
#553 qui restaient ouvertes : le dossier d'archive est `docs/archives/`
(pas un second dossier `docs/archive/`) ; les quatre reçus
`redites-*.txt` restent ; `docs/FILM_DISCOURS_ETAT_2026-09-28.md` reste
entier dans NAVIGUIDE. Le filtre le copie à ce chemin. Le commit de la
section 6.5 le déplace ensuite dans `naviguide-simulator/`.
`docs/LOTS_ORDRE_ET_PROMPTS.md` reste à ce chemin ; l'original de
`docs/REGLES_PARAMETRES.md` reste
dans Blue Intelligence ; l'index et les manuels sont réécrits après le
filtre, dans chaque dépôt ; chaque dépôt a sa copie des règles Cursor
communes ; l'archive s'appelle `Blue-Intelligence-Map`. Le déplacement
des 19 documents (d) encore à la racine de `docs/` se fait dans les
dépôts filtrés, avant leur premier push (section 6.4). Cette PR ne
déplace rien.

## 5. Filtrer une copie nue, puis pousser `main` et les tags

`git clone --mirror` ramène aussi les références cachées. Mesure du
17 octobre 2026 au soir, `git ls-remote origin`, au moment où `main`
vaut `6dabfb84` : **37** branches (`refs/heads/*`), **553**
`refs/pull/*/head`, **11** `refs/pull/*/merge`, **5** tags. GitHub
refuse un push de `refs/pull/*`. `--mirror` pousserait en plus les 37
branches, dont d'anciennes branches des deux produits. On ne l'utilise
pas.

`git clone --bare --single-branch --branch main` ne ramène pas ces
références. La mesure ancienne (550 têtes de pull, 16 fusions de pull,
42 branches) ne décrit plus cette tête.

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
  --description "NAVIGUIDE — voyage en direct sur naviguide.fr"
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

Plusieurs commits, dans la copie de travail, avant le premier push.
Les diffs exacts sont en 6.6, 6.7 et 6.8. On ne les réécrit pas à la
main. Les quatre fichiers du commit 6.6 restent tels que le filtre les
a copiés jusqu'au `git apply`.

```bash
git clone /tmp/bi-bare /tmp/bi-work
cd /tmp/bi-work
# 1. Édition à la main : sections 6.0 et 6.1, sans toucher
#    .github/workflows/ci.yml, .github/workflows/deploy.yml,
#    .github/dependabot.yml, infra/vps/ci/prepare-ssh.sh.
# 2. Les quatre git apply Blue Intelligence de la section 6.6, puis :
git add -A
git status
git commit -m "chore: limiter la CI Blue Intelligence à son déploiement OVH"
# 3. Le git apply de la section 6.8 (retrait du test), puis :
git add -A
git status
git commit -m "test: retirer l'import de climatology_query du dépôt Blue Intelligence"
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
cd /tmp/ng-work
# 1. Édition à la main : sections 6.0, 6.2 et 6.4, sans toucher les
#    quatre fichiers du commit 6.6.
# 2. Les quatre git apply NAVIGUIDE de la section 6.6, puis :
git add -A
git status
git commit -m "chore: limiter la CI NAVIGUIDE au déploiement de naviguide.fr"
# 3. Section 6.7, puis :
git add -A
git status
git commit -m "test: figer la parité climatologie du simulateur hors de frontend"
# 4. Section 6.8, le fichier de test à côté de climatology_query, puis :
git add -A
git status
git commit -m "test: placer test_naviguide_query_not_painted à côté de climatology_query"
# 5. Les deux commits de la section 6.5, puis :
git remote add origin git@github.com:Berry-Mappemonde/NAVIGUIDE.git
git push origin refs/heads/main:refs/heads/main
```

Pas de `--mirror`, pas de `--all`, pas de `--tags` global, pas de
`refs/pull`. `git status` avant chaque commit ne montre que les
fichiers de ce commit. Ces commandes restent dans `/tmp/bi-work` et
`/tmp/ng-work`. On ne les lance pas dans le clone du monodépôt.

Les PR ouvertes au 17 octobre 2026 au soir restent sur l'archive, avec
leurs branches. Le filtre ne les transporte pas (les SHA changent).
Il y en a **11** : #541, #542, #543, #546, #547, #548, #549, #551,
#553, #554, #555. Depuis la liste qui en comptait 16, sont sur `main` :
#529, #530, #533, #534, #536, #540, #544, #545, #550. #146, #227, #510,
#537 et #552 sont fermées et ne sont pas sur `main`. Rien de tout cela
n'est effacé de l'archive. Les textes de #510 et #227 sont recopiés
dans les dépôts neufs après le filtre (section 6.4), depuis les SHA
d'origine.

## 6. Ce que le premier commit change dans chaque dépôt

Le filtre a copié chaque document commun en entier. Ce commit raccourcit
la copie qui n'est pas l'original. On n'édite pas ces fichiers dans le
monodépôt : seulement dans la copie filtrée, avant le premier push.

`ci.yml`, `deploy.yml`, `dependabot.yml` et `prepare-ssh.sh` ne se
réécrivent pas en prose. Leur diff est en section 6.6, un commit par
dépôt. Les commits des tests sont en 6.7 et 6.8. Les sections 6.0,
6.4 et 6.5 restent : elles ne sont pas ces quatre fichiers.

### 6.0 Copies communes

| Fichier | Original | L'autre copie, dans ce commit |
|---|---|---|
| `.cursor/rules/base-de-donnees-vps.mdc` | Blue Intelligence, fichier entier | NAVIGUIDE : trois phrases. Le simulateur n'a pas de Mongo. `blueintel_db` reste sur l'OVH. On ne lance pas `sync-from-atlas.sh`. |
| `.cursor/rules/environnement-utilisateur.mdc` | Blue Intelligence, fichier entier | NAVIGUIDE : la même règle, plus une ligne. Le simulateur est sur Contabo (`naviguide@13.140.164.185`). Blue Intelligence reste sur l'OVH. |
| `.cursor/rules/modeles-cursor-uniquement.mdc` | Blue Intelligence | NAVIGUIDE : fichier entier. La règle vaut pour les deux produits. |
| `.cursor/rules/reparations-sur-github.mdc` | Blue Intelligence | NAVIGUIDE : fichier entier. La règle vaut pour les deux produits. |
| `.cursor/rules/pas-de-verification-video.mdc` | NAVIGUIDE, fichier entier | Blue Intelligence : les trois interdictions (pas de vidéo ; preuve par tests, `curl` ou capture fixe). |
| `README.md` | Blue Intelligence | NAVIGUIDE : page du produit. Il s'appelle NAVIGUIDE, il est en ligne sur `https://naviguide.fr`, et chaque merge sur `main` déploie cette version. L'API Blue Intelligence reste `https://blueintelligence.online/api`. |
| `docs/HACKATHON_PLAN.md` | Blue Intelligence | NAVIGUIDE : lignes séparation et Nebius. La ligne GenAI devient un lien vers le dépôt Blue Intelligence. |
| `docs/PLAN_SEPARATION_DEPOTS.md` | Blue Intelligence, ce fichier entier | NAVIGUIDE : les sections qui nomment son dépôt, la preuve d'historique (`poe_pipeline.py` en août 2026) et les dix contrôles. La procédure Mongo de l'OVH devient un renvoi vers la copie Blue Intelligence. |
| `docs/REGLES_PARAMETRES.md` | Blue Intelligence, fichier entier | NAVIGUIDE : le principe et les sections 3.7 à 3.10. Les sections 3.1 à 3.6 deviennent un renvoi vers `backend/data/run_rules.json` dans l'autre dépôt. |
| `docs/README.md` | NAVIGUIDE, fichier entier | Blue Intelligence : index court des cahiers, de l'audit PoE et du plan GenAI. |
| `infra/vps/README.md` | Blue Intelligence | NAVIGUIDE : le site live est `naviguide.fr` (le voyage, port 8010). `www` et `simulator` sont des `301`. Les unités de l'ancien planificateur sont nommées comme archives, pas comme services à lancer. La restauration Mongo devient un renvoi. Le dossier d'application devient `/home/naviguide/naviguide`. |
| `Archives/README.md` | NAVIGUIDE | Blue Intelligence : paragraphes de `Archives/Blue-Intelligence/` seulement. |

`Archives/naviguide-nova/README.md` part dans NAVIGUIDE tel qu'il est
aujourd'hui. Il cite `docs/PLAN_DEV_NOVA.md` et
`docs/SETUP_NOVA_CREDITS.md` à côté de lui. Ces deux fichiers ne sont
pas dans le dépôt filtré : ils restent dans le monodépôt. Les mêmes
textes sont dans `Archives/naviguide-navsecops/docs/`, qui part dans
NAVIGUIDE. On ne réécrit pas le README nova. La décision de le modifier,
puis de supprimer les doublons, est annulée.

Chemins codés en dur aujourd'hui : `~/blue-intelligence-map` et
`/home/ubuntu/blue-intelligence-map`. Cibles :

| Dépôt | Dossier sur le serveur | Hôte du secret `VPS_HOST` |
|---|---|---|
| Blue Intelligence | `/home/ubuntu/blue-intelligence` | `ubuntu@135.125.226.16` |
| NAVIGUIDE | `/home/naviguide/naviguide` | `naviguide@13.140.164.185` |

`prepare-ssh.sh` écrit aujourd'hui `REMOTE_APP=/home/ubuntu/blue-intelligence-map`
et, si `VPS_HOST` est vide, `ubuntu@135.125.226.16`. Le diff de la
section 6.6 fait le changement. Blue Intelligence reçoit
`REMOTE_APP=/home/ubuntu/blue-intelligence` et garde le défaut OVH.
NAVIGUIDE reçoit `REMOTE_APP=/home/naviguide/naviguide` et n'a plus de
défaut : un secret `VPS_HOST` vide arrête le job.

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
- `infra/vps/ci/prepare-ssh.sh`, `.github/workflows/ci.yml`,
  `.github/workflows/deploy.yml`, `.github/dependabot.yml` : le diff
  exact est en section 6.6. On ne les édite pas à la main.
- `infra/vps/ci/plan_deploy.py` et `test_prod_jobs_busy.py` restent tels
  que le filtre les a copiés. Leurs 31 tests décrivent encore trois
  sites et restent verts. Le workflow ne lance plus les jobs
  `naviguide` ni `simulator`. On ne réécrit pas ces deux fichiers dans
  le commit 6.6.
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
- Copies communes dont l'original est NAVIGUIDE : les raccourcir selon
  le tableau 6.0 (`pas-de-verification-video.mdc`, `docs/README.md`,
  `Archives/README.md`). `reparations-sur-github.mdc` et
  `modeles-cursor-uniquement.mdc` restent entiers.

Le dépôt ne contient pas `zap-baseline.yml` ni `infra/vps/naviguide/` :
le filtre les a déjà écartés. `weekly-data-build.yml` part tel quel.

### 6.2 Dépôt NAVIGUIDE

- `naviguide-simulator.service` : `User=naviguide` (aujourd'hui
  `User=ubuntu`), `WorkingDirectory` et `ExecStart` sous
  `/home/naviguide/naviguide/naviguide-simulator`, `EnvironmentFile` vers
  `/home/naviguide/.config/naviguide/simulator.env`. Les trois autres
  unités (`naviguide-api`, `naviguide-polar`, `naviguide-orchestrator`)
  suivent le code de l'ancien planificateur sous
  `Archives/naviguide-planificateur/` (section 6.4). On ne les installe
  pas sur Contabo.
- `deploy-simulator.sh` et `publish-simulator-from-mac.sh` : `APP` et
  `REMOTE_APP` = `/home/naviguide/naviguide`. Le défaut
  `ubuntu@135.125.226.16` de `publish-simulator-from-mac.sh` est retiré.
  `deploy-naviguide.sh` n'est plus le déploiement live : il reste à
  côté de l'ancien planificateur et n'est pas appelé.
- `polar_api.py` n'a pas de variable : il écrit dans
  `server/polar_data/` à côté du code. Dans cette copie, lire
  `NAVIGUIDE_POLAR_DIR` quand elle est posée, sinon garder ce dossier.
  Même forme que `NAVIGUIDE_GRIB_DIR` dans `saildocs.py`.
- `infra/vps/ci/prepare-ssh.sh`, `.github/workflows/ci.yml`,
  `.github/workflows/deploy.yml`, `.github/dependabot.yml` : le diff
  exact est en section 6.6. On ne les édite pas à la main.
  `prepare-ssh.sh` n'a plus de défaut OVH.
  `REMOTE_APP=/home/naviguide/naviguide`.
- `rsync-to-vps.sh` reste une édition à la main, hors du diff 6.6.
  Ne garder que le cas du site live (le dossier `naviguide-simulator/`).
  Ce cas utilise `--delete` et n'exclut aujourd'hui que
  `server/voyage_data/` et `server/polar_data/*.json`. Ajouter les
  exclusions `server/grib_data/`, `server/forecast_cache/`,
  `server/saildocs_inbox/`. `forecast_cache/` n'existait pas le
  17 octobre : l'exclusion empêche un déploiement futur de l'effacer le
  jour où le code le crée. La section 8 place les données **hors** du
  checkout, dans `/home/naviguide/naviguide-data/`. Le `deploy-gate`
  est vert sans cette édition.
- `plan_deploy.py` et `test_prod_jobs_busy.py` restent tels que le
  filtre les a copiés. Le workflow 6.6 ne les appelle plus : chaque
  poussée sur `main` déploie `naviguide.fr`. Leurs 31 tests restent
  verts. On ne les réécrit pas dans ce commit.
- nginx, détail en section 6.4. En bref : `naviguide.fr` sert le
  simulateur (port `8010`). `www.naviguide.fr` et
  `simulator.naviguide.fr` répondent `301` vers `https://naviguide.fr`.
  Les `location /bi/` et `/bi/climatology/` du vhost live font
  aujourd'hui `proxy_pass http://127.0.0.1:8001/api/…` parce que les
  trois sites étaient sur la même machine. Sur Contabo, l'amont est
  `https://blueintelligence.online/api/…`, avec
  `proxy_ssl_server_name on;` et
  `proxy_set_header Host blueintelligence.online;`.
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
  `GROK_BOT_ROUTINE.md`, `GROK_BOT_DEVPOST.md`. Le commit de la
  section 6.5 range ensuite ces noms dans `infra/agents/repo_paths.py`.
  Ce commit-ci les écrit encore à leur place actuelle, pour que le
  dépôt démarre même si 6.5 suit juste après.
- `README.md` et `naviguide-simulator/README.md` : le produit s'appelle
  NAVIGUIDE. Il est en ligne sur `https://naviguide.fr`. Chaque merge
  sur `main` déploie cette version. La première phrase ne dit plus
  « hors production », « Off-production » ni « publication prévue ».
  L'API Blue Intelligence reste `https://blueintelligence.online/api`.
- Copies communes dont l'original est Blue Intelligence : les raccourcir
  selon le tableau 6.0. `environnement-utilisateur.mdc` gagne la ligne
  Contabo. `modeles-cursor-uniquement.mdc` et
  `reparations-sur-github.mdc` restent entiers.
- `Archives/naviguide-nova/` : aucun fichier de ce dossier n'est
  réécrit. Les deux doublons markdown ne sont pas dans l'arbre filtré.

`vite.config.js` proxy `/bi` vers le serveur local du simulateur. On
ne change pas ce proxy : il parle au poste local. On ajoute
`.naviguide.fr` à `allowedHosts` (server et preview), à côté de
`.blueintelligence.online`, pour le tunnel `recette.naviguide.fr`.

### 6.4 Nom public, CI, archives, textes récupérés

Décisions du 17 octobre 2026 au soir. Tout ce qui suit se fait dans les
copies filtrées, avant leur premier push, ou sur l'archive au moment
dit. Cette PR ne déplace aucun fichier.

**Le produit s'appelle NAVIGUIDE et il est sur `naviguide.fr`.**
L'ancien planificateur (`naviguide/`, `www.naviguide.fr`,
`csw6hpki.run.complete.dev`) n'est plus le site. Dans la copie
NAVIGUIDE :

```bash
git mv naviguide Archives/naviguide-planificateur
```

Le README de ce dossier dit que c'est l'ancien planificateur, et que
l'adresse `https://csw6hpki.run.complete.dev` est celle de l'époque.
Le site public ne le sert plus.

**Redirection.** On garde les trois noms dans le certificat, et un seul
sert le site. `https://naviguide.fr` est l'adresse canonique (aujourd'hui
l'apex renvoie vers `www` : on inverse). `https://www.naviguide.fr` et
`https://simulator.naviguide.fr` répondent `301` vers
`https://naviguide.fr` en gardant le chemin (`$request_uri`). Un `301`
laisse vivants les liens déjà publiés (Devpost, ZAP, marque-pages).
Retirer le nom `simulator` du DNS casserait ces liens.

`nginx-simulator.conf` devient le vhost de `naviguide.fr` : `server_name
naviguide.fr`, proxy vers `127.0.0.1:8010`, `/bi/` vers l'API publique
comme ci-dessus. `nginx-naviguide.conf` ne proxy plus vers les ports
`9000`, `9004` et `9008`. Il ne contient que les `301`. Le port 80 des
trois noms renvoie aussi vers `https://naviguide.fr`.

**DNS et TLS, le jour de la bascule** (après la section 8, détail en
section 9). Zone `naviguide.fr` chez OVH, sans Cloudflare sur l'apex.

1. Lire le TTL. Le baisser la veille.
2. Quand Contabo répond en HTTP sur le port 80, passer les A de
   l'apex, de `www` et de `simulator` de `135.125.226.16` à
   `13.140.164.185`. Ne pas toucher la zone Cloudflare de
   `blueintelligence.online`.
3. Sur Contabo : `certbot` pour les trois noms
   (`naviguide.fr`, `www.naviguide.fr`, `simulator.naviguide.fr`).
   Le certificat OVH reste en place : c'est le retour arrière.
4. Recharger nginx. Vérifier : `naviguide.fr` répond 200 et montre le
   voyage ; `www` et `simulator` répondent 301 vers
   `https://naviguide.fr/`.

**Recette.** Le poste de recette n'est pas un vhost Contabo. C'est le
tunnel Cloudflare nommé `recette`, lancé sur le Mac par
`run_lots.py`, vers le Vite du port 5174. Aujourd'hui l'hôte est
`recette.blueintelligence.online`. Il devient
`recette.naviguide.fr`.

La zone `naviguide.fr` n'est pas chez Cloudflare, donc
`cloudflared tunnel route dns` ne peut pas y écrire. Sur le Mac :

1. `cloudflared tunnel info recette` donne l'UUID du tunnel.
2. Dans le tableau de bord du tunnel, ajouter le nom public
   `recette.naviguide.fr` vers `http://localhost:5174`.
3. Dans le DNS OVH, un CNAME `recette` vers
   `<UUID>.cfargotunnel.com`. Ne pas mettre l'apex derrière Cloudflare.
4. Dans `~/.config/naviguide/simulator.env` du Mac :
   `BIM_TUNNEL_HOST=recette.naviguide.fr`. On n'affiche pas les autres
   clés.
5. `python3 infra/agents/run_lots.py --recette`, puis
   `curl -fsS -o /dev/null -w '%{http_code}\n' https://recette.naviguide.fr`.
   Attendu : `200`. Si Cloudflare répond une erreur, on s'arrête. On ne
   ramène pas le tunnel sur `blueintelligence.online`, et on ne déplace
   pas la zone `naviguide.fr` chez Cloudflare : le site public doit
   rester un A vers Contabo.
6. Quand le nouveau lien répond, retirer
   `recette.blueintelligence.online` du tunnel.

**CI.** Principe : chaque merge sur `main` déploie la dernière version
en live. Blue Intelligence le fait déjà vers `blueintelligence.online`,
avec le cron de rattrapage des files uvicorn. NAVIGUIDE le fait vers
`naviguide.fr`, sans cron et sans la branche `recette`.

**URL à changer dans la copie NAVIGUIDE**, là où le texte dit où aller
aujourd'hui. On ne réécrit pas les plans déjà sous `docs/archives/`, ni
`docs/REVUE_PORTEUR_2026-10-14.md` : ces pages citent l'adresse de leur
jour.

| Fichier | Changement |
|---|---|
| `naviguide-simulator/README.md`, `README.md` | Produit NAVIGUIDE, live `https://naviguide.fr`, merge sur `main` = déploiement. Plus de « hors production ». |
| `naviguide-simulator/server/admin_guard.py` | La liste CORS par défaut commence par `https://naviguide.fr`. On garde `www` et `simulator` le temps des `301`. |
| `naviguide-simulator/server/tests/test_admin_guard.py` | L'assertion suit cette liste. |
| `naviguide-simulator/src/utils/adminSecret.test.js` | L'URL d'exemple devient `https://naviguide.fr`. |
| `naviguide-simulator/scripts/amp-route.py` | `FALLBACK_API` = `https://naviguide.fr`. |
| `naviguide-simulator/vite.config.js` | `allowedHosts` contient `.naviguide.fr`. |
| `infra/agents/run_lots.py` | `PROD_URL` = `https://naviguide.fr`. Le commentaire du tunnel dit `recette.naviguide.fr`. La section 6.5 déplace ensuite cette constante dans `infra/agents/repo_paths.py`. |
| `infra/agents/GROK_BOT_ROUTINE.md`, `GROK_BOT_DEVPOST.md` | Même hôte de recette. |
| `docs/MANUEL_UTILISATEUR.md`, `docs/USER_MANUAL.md`, `docs/README.md` | L'adresse live est `https://naviguide.fr`. L'écran s'appelle comme aujourd'hui (Suivre / Tracer). |
| `docs/HACKATHON_DEVPOST_SOUMISSION.md`, `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md` | Les liens à coller ou à vérifier pointent vers `https://naviguide.fr`. |
| `docs/REGLES_WORKFLOW_AGENT.md` | Le contrôle « dans les 10 minutes » ouvre `https://naviguide.fr`. |
| `docs/WORKFLOW_INDUSTRIEL.md` | Le contrôle `/ici/warm/status` utilise `https://naviguide.fr`. |
| `.github/workflows/zap-baseline.yml` | `target` = `https://naviguide.fr`. |
| `.github/workflows/deploy.yml`, `infra/vps/ci/plan_deploy.py` | Un job, `main` seulement, construit `naviguide-simulator/`. |

Les e2e Playwright (`naviguide-simulator/playwright.config.js`) parlent
au poste local. On ne les pointe pas vers `naviguide.fr`.

**Calendrier.** `docs/WORKFLOW_INDUSTRIEL.md` reste un document vivant.
La section 4 (le tableau des dates) est remplacée par une seule ligne,
sans autre date :

```text
| à dater par le propriétaire | | |
```

On n'invente pas de date. Les anciennes lignes (21 septembre, 30 octobre,
et les autres) restent dans l'historique git. On ne les recopie pas
comme si elles étaient encore le calendrier.

**Documents (d) encore à la racine de `docs/`.** `git mv` vers
`docs/archives/` du dépôt qui les possède. Les liens internes qui
cassent sont réécrits dans le même commit. On ne les déplace pas dans
le monodépôt.

Blue Intelligence :

- `docs/ETAT_DES_LIEUX_DOCS.md`
- `docs/PRD.md`

NAVIGUIDE :

- `docs/PLAN_AUDIT_CALCULS.md`
- `docs/PLAN_BATCH_2026-10-14.md`
- `docs/PLAN_BATCH_SUIVANT_2026-09-29.md`
- `docs/PLAN_CORRECTIONS_2026-09-22.md`
- `docs/PLAN_CORRECTIONS_2026-09-23.md`
- `docs/PLAN_CORRECTIONS_2026-09-26-s2.md`
- `docs/PLAN_CORRECTIONS_2026-09-26-s4.md`
- `docs/PLAN_CORRECTIONS_2026-09-27-s5.md`
- `docs/PLAN_CORRECTIONS_2026-09-28-film.md`
- `docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md`
- `docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md`
- `docs/PLAN_DEUX_MODES_2026-09-29.md`
- `docs/PLAN_FILM_REVOIR_EXPEDITION.md`
- `docs/PLAN_ICI_JOURNAL_EXPERT.md`
- `docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md`
- `docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md`
- `docs/SPECS_E2E_TRIAGE_2026-09-29.md`

`docs/FILM_DISCOURS_ETAT_2026-09-28.md` traverse le filtre entier, à
son chemin, dans NAVIGUIDE. Le commit de la section 6.5 le déplace
dans `naviguide-simulator/` et laisse un renvoi à l'ancien chemin.
`docs/LOTS_ORDRE_ET_PROMPTS.md` reste à son chemin. Les
quatre `docs/recette/lot-r13/redites-*.txt` restent. Les règles Cursor
communes sont déjà dans les deux dépôts (section 6.0).

**PR fermées, pour ne rien perdre.** Les SHA d'origine sont sur
l'archive. Le filtre les réécrit : on copie le contenu depuis l'archive,
on ne cherry-pick pas dans le dépôt filtré.

#510, tête `15e41b4e546955b9d65a773cab5f4a2c63e7f5c2`, vers NAVIGUIDE :

```bash
git -C /chemin/vers/Blue-Intelligence-Map \
  show 15e41b4e546955b9d65a773cab5f4a2c63e7f5c2:docs/PLAN_CORRECTIONS_2026-10-16-s7.md \
  > docs/archives/PLAN_CORRECTIONS_2026-10-16-s7.md
```

Le même commit ajoute 31 lignes à `docs/LOTS_ORDRE_ET_PROMPTS.md`
(deux lignes de tableau RJ1 et RJ2, puis deux blocs `<!-- LOT id="RJ1"`
et `RJ2`). On les reporte à la fin du fichier vivant, si ces id n'y
sont pas déjà. Dans ces blocs, le chemin du plan devient
`docs/archives/PLAN_CORRECTIONS_2026-10-16-s7.md`. On ne remplace pas
le fichier entier : `main` a bougé depuis le 16 octobre.

#227, tête `bef9f0f34c0bcdfdd93d3b7c26f1c93b095613d5`, vers Blue
Intelligence, sous `docs/archives/verify-fiche-urls/` :

- `docs/VERIFY_FICHE_URLS.md`
- `scripts/verify_fiche_urls.py`
- `scripts/fiche_url_extract.py`
- `backend/tests/test_verify_fiche_urls.py`

Même `git show <sha>:<chemin>`. Un `README.md` d'une demi-page dans ce
dossier rappelle les quatre chemins d'origine et le SHA. On ne rejoue
pas les hunks de `ci.yml`, `weekly-data-build.yml` et `README.md` de
ce commit : ils visaient la CI du monodépôt. Le commit reste lisible
sur l'archive. Brancher l'outil dans la CI Blue Intelligence est un
commit plus tard, pas celui de la séparation.

**Houle, après le split.** Le bandeau de
`docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` dit « swell not
shipped ». On ne retire pas cette phrase dans le commit de séparation.
Tâche d'après-bascule : ouvrir l'écran climatologie sur
`https://naviguide.fr` et regarder la couche houle. Si elle s'affiche,
un commit suivant retire la phrase. Si elle ne s'affiche pas, la phrase
reste.

Issues ouvertes au 17 octobre 2026, toutes deux NAVIGUIDE : **#432**
(Devpost, citée par `GROK_BOT_DEVPOST.md`) et **#446** (ouverte par le
workflow ZAP). Les transférer vers le dépôt NAVIGUIDE (même propriétaire,
action Transfer d'une issue) ou les recréer, puis corriger l'URL dans
`GROK_BOT_DEVPOST.md` : l'adresse live est `https://naviguide.fr`.
Les issues fermées restent sur l'archive. Les textes des PR #510 et
#227 sont copiés à part (section 6.4).

### 6.5 Deux commits dans NAVIGUIDE, après le filtre

Correction du 17 octobre au soir. Ces deux travaux sont écrits ici.
Cette PR ne les fait pas : aucun fichier n'est déplacé, aucun script
n'est réécrit. Ils ne font pas partie des commits 6.6, 6.7 et 6.8. Ils
arrivent après ces trois commits, dans la copie filtrée NAVIGUIDE,
avant le premier push. L'ordre est en section 5.4.

#### Les deux façons

**Façon 1 — une PR préparatoire sur le monodépôt, avant le filtre.**
On ouvre une PR pendant que l'arbre est encore unique. Elle déplace le
discours du film et elle ajoute le fichier de réglages. La CI actuelle
peut tourner avant la séparation.

Cette PR doit être fusionnée sur `main` avant le clone nu. Sinon le
filtre copie encore les anciens chemins. Le classeur
(`scripts/check_split_coverage.py`, liste `DOC_NG`) et la section 4 de
ce plan nomment `docs/FILM_DISCOURS_ETAT_2026-09-28.md`. Un déplacement
avant le filtre demande de réécrire le classeur, de réécrire la
section 4, puis de revérifier les 132 documents. Le propriétaire a
demandé de ne rien déplacer dans cette PR. Les 11 PR ouvertes restent
une décision à part (section 10.2) : la PR préparatoire en serait une
de plus à fusionner d'abord.

`naviguide-simulator/server/tests/test_film_discours.py` n'ouvre pas le
markdown. La transcription est la constante `REVUE_28_SEPT`, collée
dans le test (lignes 37 à 49). `film_script.py` ne le lit pas non plus :
les lignes 102 et 5050 sont des commentaires (« gabarit FILM_DISCOURS
§ 4 »). Une CI verte sur le monodépôt ne voit donc pas un chemin de
lecture cassé : il n'y a pas de lecture.

**Façon 2 — deux commits dans la copie filtrée NAVIGUIDE.**
Le filtre copie le discours à `docs/FILM_DISCOURS_ETAT_2026-09-28.md`
et laisse les chemins en dur dans `infra/agents/`. Le classeur reste
juste. On lance `--verify ng` sur le résultat du filtre, puis le commit
de la section 6, puis ces deux commits, puis le premier push.

Un commit faux se corrige dans cette copie. On ne relance pas
`git filter-repo`.

**Recommandation : la façon 2.** Le discours et la boucle de nuit sont
le produit NAVIGUIDE. Les faire avant le filtre change la liste de
chemins que ce plan vient de figer, et demande une fusion que la
section 10.2 laisse ouverte. Les faire dans `/tmp/ng-work`, après le
commit de la section 6 et avant le premier push, publie un `main`
NAVIGUIDE déjà à jour. La façon 1 ne protège pas un test qui ne lit pas
le fichier.

Même façon 2, autre moment : pousser d'abord le filtre et le commit de
la section 6, puis ouvrir ces deux commits en PR sur le dépôt
NAVIGUIDE neuf. À retenir seulement si l'on veut que le premier push
soit uniquement le filtre plus la section 6. Le moment recommandé reste
avant ce push : la copie de travail est là, les tests du film tournent
dessus, et le `main` publié n'a pas une fenêtre avec l'ancien chemin.

Ordre, dans `/tmp/ng-work` :

1. Déplacer le discours du film.
2. Remplacer les chemins en dur de la boucle par le fichier de réglages.

#### 6.5.1 Déplacer le discours du film

```bash
mkdir -p naviguide-simulator/server/tests/fixtures
git mv docs/FILM_DISCOURS_ETAT_2026-09-28.md \
  naviguide-simulator/server/tests/fixtures/FILM_DISCOURS_ETAT_2026-09-28.md
```

À l'ancien chemin, un court fichier
`docs/FILM_DISCOURS_ETAT_2026-09-28.md` dit seulement où le texte est
passé. Un marque-page et un ancien prompt retrouvent le document. Le
fichier entier, lui, vit à côté du test qui le cite.

Chemins à réécrire dans le même commit. Lecture du 17 octobre 2026 :

- `naviguide-simulator/server/tests/test_film_discours.py`, le
  commentaire de la ligne 35. Il cite
  `docs/FILM_DISCOURS_ETAT_2026-09-28.md`. On le fait citer le nouveau
  chemin. `REVUE_28_SEPT` reste dans le test.
- `naviguide-simulator/server/film_script.py`, commentaires des
  lignes 102 et 5050. On y ajoute le nouveau chemin, à côté de
  « gabarit FILM_DISCOURS § 4 ».
- `docs/LOTS_ORDRE_ET_PROMPTS.md` : 21 occurrences
  (`FILM_DISCOURS_ETAT_2026-09-28.md`), lues sur le monodépôt aux
  lignes 141, 1697, 1720, 1735, 1750, 1765, 1780, 1795, 1810, 1825,
  1840, 1855, 1885, 1900, 1930, 2161, 2177, 2209, 2232, 2281 et 2331.
  L'ajout RJ1/RJ2 de la section 6.4 décale les lignes : on cherche la
  chaîne, on ne se fie pas au numéro. Chacune prend le nouveau chemin.
  Après le commit, chercher l'ancien chemin dans ce fichier ne doit
  plus rien trouver.
- `docs/archives/PLAN_CORRECTIONS_2026-09-28-film.md`. Le `git mv` de
  la section 6.4 a déjà rangé ce plan. Sa ligne 6 cite
  `docs/FILM_DISCOURS_ETAT_2026-09-28.md` : elle prend le nouveau
  chemin. Les mentions « FILM_DISCOURS_ETAT § … » sans chemin restent
  des renvois de section.
- Le renvoi laissé dans `docs/` est le seul fichier de `docs/` qui
  garde l'ancien nom. Il pointe vers
  `naviguide-simulator/server/tests/fixtures/FILM_DISCOURS_ETAT_2026-09-28.md`.

`docs/README.md` ne cite pas ce fichier aujourd'hui. Si le commit de
la section 6 l'a ajouté à l'index, l'index pointe vers le nouveau
chemin.

Le classeur n'est pas modifié. Il décrit l'arbre avant ce déplacement.
`--verify ng` a déjà été lancé sur le résultat du filtre.

Vérification de ce commit, dans la copie filtrée. Le contrôle est le
`grep` : il ne doit rien afficher.

```bash
grep -n "docs/FILM_DISCOURS_ETAT_2026-09-28.md" \
  docs/LOTS_ORDRE_ET_PROMPTS.md \
  docs/archives/PLAN_CORRECTIONS_2026-09-28-film.md \
  naviguide-simulator/server/tests/test_film_discours.py \
  naviguide-simulator/server/film_script.py
```

Si `naviguide-simulator/server/.venv` existe déjà, lancer aussi le
test. Un clone filtré tout neuf n'a pas ce dossier : il n'est pas dans
git. L'absence de pytest n'arrête pas le commit. Le test ne lit pas le
markdown, il doit passer comme avant le déplacement.

```bash
naviguide-simulator/server/.venv/bin/python -m pytest \
  naviguide-simulator/server/tests/test_film_discours.py -q
```

#### 6.5.2 Un fichier de réglages pour la boucle

Les scripts de `infra/agents/` portent les chemins du monodépôt en dur.
Blue Intelligence pourra réutiliser la boucle le jour où ces chemins
vivent dans un seul fichier, avec d'autres valeurs. Ce plan ne copie
pas `run_lots.py` dans Blue Intelligence. Le fichier de réglages est
la condition de cette copie, plus tard (section 10.2).

Fichier : `infra/agents/repo_paths.py`. Un module Python, bibliothèque
standard seulement : `run_lots.py` n'ajoute pas de dépendance. Les
scripts l'importent. Les prompts sont construits avec ces noms. La
même chaîne n'est pas recopiée dans le texte du prompt.

Un `infra/agents/paths.toml` lu seulement par ce module revient au
même. On ne tient pas la liste à la fois dans le toml et dans des
constantes à côté. Le module est le fichier de réglages.

Les valeurs NAVIGUIDE sont celles d'après la section 6 : dépôt
`Berry-Mappemonde/NAVIGUIDE`, site `https://naviguide.fr`. Le commit
6.5 les retire de leur place actuelle et les met dans le module.

Chemins et adresses à couvrir. Lecture des scripts le 17 octobre 2026.

Dépôt, site, branche :

| Nom aujourd'hui | Valeur lue | Fichiers |
|---|---|---|
| `DEFAULT_REPO` | `https://github.com/Berry-Mappemonde/Blue-Intelligence` | `run_lots.py` (ligne 69). `loop.py`, `plan_corrections.py`, `review_agent.py`, `vl_film_review.py`, `devpost_answers.py`, `watchdog.py` passent par ce nom. |
| `BIM_REPO`, défaut | `Berry-Mappemonde/Blue-Intelligence` | `gh_token.py`, `open_pr.py`, `post_pr_comment.py`, `review_collect.py`. L'environnement peut encore écraser le défaut. |
| `PROD_URL` | `https://simulator.naviguide.fr` (la section 6 l'a déjà mise à `https://naviguide.fr`) | `run_lots.py` (ligne 1049). |
| `RECETTE_BRANCH` | `recette` | `run_lots.py` (ligne 1266). |
| Hôte du tunnel, dans les commentaires | `recette.blueintelligence.online` | `run_lots.py` (docstring vers les lignes 1198 et 1204). `GROK_BOT_ROUTINE.md`, `GROK_BOT_DEVPOST.md`. La section 6 les réécrit déjà en `recette.naviguide.fr`. Le module porte la valeur ; les commentaires citent le module. |

Documents que le code ouvre ou que les prompts disent de lire :

| Chemin | Où il est écrit en dur |
|---|---|
| `docs/LOTS_ORDRE_ET_PROMPTS.md` | `run_lots.py` `PROMPTS_MD` (ligne 59). `plan_corrections.py` `FIXED_DOCS` (ligne 70) et les prompts (lignes 10, 13, 208, 235, 272, 276). `review_agent.py` (lignes 129, 130, 203). `loop.py` lit `rl.PROMPTS_MD`, sans second chemin. |
| `docs/REGLES_WORKFLOW_AGENT.md` | `FIXED_DOCS`. Prompts de `plan_corrections.py` (207, 276), `review_agent.py` (129, 203), `run_lots.py` (643–644). |
| `docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md` | `FIXED_DOCS`. Prompt `plan_corrections.py` ligne 211. |
| `docs/PLAN_CORRECTIONS_{date}*.md` | `plan_corrections.py` `previous_plans` (glob sous `docs/`). |
| `docs/PLAN_CORRECTIONS_{tag}.md` | Sortie demandée par les prompts de `plan_corrections.py`, et attribut `plan=` des balises `<!-- LOT -->`. |
| Branche `docs/plan-corrections-{tag}` | `plan_corrections.py` (checkout, push, recherche de la PR). |
| `docs/PLAN_*.md` | Phrase du prompt `run_lots.py` (ligne 643) : « le plan ». |
| `docs/WORKFLOW_INDUSTRIEL.md` | Prompt `review_agent.py` ligne 129. |
| `docs/recette/` | Captures. `run_lots.py` (lignes 653, 1756–1759). `review_collect.py` `CAPTURE_RE` (ligne 101) et le filtre de ligne 199. `open_pr.py` ligne 61. `review_agent.py` : `git diff` avec `:!docs/recette` (ligne 153). |
| `docs/HACKATHON_DEVPOST_SOUMISSION.md` | `devpost_answers.py` `SUBMISSION_DOC` (ligne 38) et le prompt ligne 114. |
| `README.md` | Prompt `devpost_answers.py` ligne 114. |
| `docs/ESPRIT_DE_L_APPLICATION.md` | Même prompt. |
| `docs/PLAN_DEUX_MODES_2026-09-29.md` | Même prompt. |
| `infra/vps/README.md` | Même prompt, section « politique LLM ». |
| `docs/DEVPOST_REPONSES_{date}.md` | Sortie demandée par `devpost_answers.py` (ligne 133). |
| Branche `docs/devpost-reponses-{date}` | Même script, ligne 135. |
| `infra/agents/PARCOURS_DE_REFERENCE.md` | `run_lots.py` `PARCOURS_MD` (ligne 1264) et le commentaire de PR ligne 1489. |

Arbre du produit :

| Chemin | Où |
|---|---|
| `naviguide-simulator/` | Racine de travail. `run_lots.py` (553, 1563, 1647, 1811, 1850). `review_agent.py` (127, 203). `vl_film_review.py` (ligne 302 : `parents[2] / "naviguide-simulator"`). |
| `naviguide-simulator/ensure-dev.sh` | `run_lots.py` ligne 1567. Prompts `review_agent.py` ligne 127 et `run_lots.py` lignes 1811 et 1850. |
| `naviguide-simulator/server/.env` | Copie vers le worktree, `run_lots.py` lignes 571–573. |
| `naviguide-simulator/node_modules`, `naviguide-simulator/.venv` | Liens de worktree, `run_lots.py` lignes 555 et 1879. |
| `frontend/node_modules` et `node_modules` à la racine | Même liste, ligne 555. |
| `naviguide-simulator/.gitignore` | Commentaire `run_lots.py` ligne 591. |
| `NPM_PROJECTS` = `naviguide-simulator`, `frontend` | `run_lots.py` ligne 1918. Chacun : `package-lock.json` et `node_modules`. |
| `PIP_PROJECT` = `naviguide-simulator`, `server/requirements.txt`, `.venv/bin/python` | `run_lots.py` ligne 1919. |
| `naviguide-simulator/src/App.jsx`, `src/components`, `src/map` | `review_agent.py` ligne 56, `git diff` du plancher `main`. |
| `naviguide-simulator/e2e/lots/*.spec.js` | `run_lots.py` ligne 1609, et les prompts lignes 647–650 et 925 (`e2e/lots/<lot>.spec.js`). |
| `naviguide-simulator/scripts/film-cinematique.mjs` | `vl_film_review.py` ligne 303. |
| Préfixes de `devpost_code_share.py` `area()` | `naviguide-simulator/`, `backend/`, `frontend/`, `infra/`, `.github/`, `scripts/`, et l'exclusion `Archives/` (lignes 29 et 37–44). |
| Caches liés au poste | `run_lots.py` `SHARED_CACHE_DIRS` (ligne 581) : `voyage_data`, `forecast_cache`, `grib_data`, sous le serveur du simulateur. `VOYAGE_DATA_FILES` (ligne 582) : `eez_vliz_v12.geojson`, `ici_thin_cache.json`, `official_journal`, `voyage_{id}.json`. L'id `berry-mappemonde-2026-officiel` (ligne 578) va dans le même module : ce n'est pas un chemin, c'est l'identité du voyage que ces fichiers nomment. |

Hors du fichier de réglages. Ce sont des fichiers d'exécution, à côté
des scripts, ou des chemins de machine déjà remplaçables par une
variable :

- `infra/agents/state.json`, `state.*.json`, `queue.md`,
  `loop-state.json`, `watchdog-state.json`, `loop.log`, `run_lots.log`
- `infra/agents/COUTS.md`, `RECETTE_DU_BATCH.md`, `REVUE_GLOBALE.md`,
  `RAPPORT_DE_NUIT.md`, `review-<date>.json`, `tunnel.pid`,
  `tunnel.url`, `tunnel.log`, `watchdog.pid`
- `infra/agents/batch-resume.sh` : cité par `loop.py` et `run_lots.py`,
  absent du dépôt. On ne l'invente pas dans le module.
- `~/.config/naviguide/simulator.env` (`NAVIGUIDE_ENV_FILE`),
  `~/bim-lots` (`BIM_LOTS_DIR`), `BIM_STATE_DIR`,
  `/tmp/film-cinematique.png`
- Les lignes d'usage `python3 infra/agents/run_lots.py` (et les autres
  scripts du même dossier). C'est l'emplacement de l'outil. Il reste
  `infra/agents/` dans les deux dépôts le jour où on copie la boucle.

`GROK_BOT_ROUTINE.md` et `GROK_BOT_DEVPOST.md` sont des textes lus par
une personne. Ils n'importent pas le module. La section 6 y réécrit
déjà l'hôte de recette et le nom du dépôt. Le commit 6.5 ajoute en tête
de chacun une ligne : les chemins exécutables sont dans
`infra/agents/repo_paths.py`.

Vérification de ce commit :

```bash
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('infra/agents/repo_paths.py').read_text())"
python3 infra/agents/run_lots.py --dry-run --only C1
grep -nE "LOTS_ORDRE_ET_PROMPTS|REGLES_WORKFLOW_AGENT|Berry-Mappemonde/Blue-Intelligence|simulator.naviguide.fr" \
  infra/agents/*.py | grep -v "repo_paths.py:"
```

Le `grep` ne doit plus trouver ces chaînes dans les scripts. Elles
vivent dans `repo_paths.py`. `--dry-run` doit encore lister le lot,
lu via le module. Si `--only C1` n'existe plus dans le fichier de lots
filtré, prendre le premier id que `--dry-run` affiche sans `--only`,
et relancer avec cet id. Un échec de réseau ou de clé API n'est pas un
échec de ce commit : `--dry-run` ne lance pas d'agent.

### 6.6 Diffs de CI, un commit par dépôt

Ces commandes s'exécutent dans `/tmp/bi-work` ou `/tmp/ng-work`, sur les
fichiers tels que le filtre les a laissés. `git apply` refuse le diff
si le fichier a déjà été édité à la main : on s'arrête, on remet le
fichier du filtre, on relance le `git apply`. On ne lance pas ces
diffs dans le monodépôt.

Contrôle du 17 octobre 2026 au soir : `git apply --check` accepte les
huit diffs sur `6dabfb84`. Les six fichiers YAML obtenus se lisent.
`bash -n` accepte les deux `prepare-ssh.sh`.
`python3 infra/vps/ci/test_prod_jobs_busy.py` finit par 31 tests, OK.
Ce fichier Python n'est pas dans le diff.

Chaque dépôt ne garde que ses jobs. Blue Intelligence déploie vers
l'OVH (`ubuntu@135.125.226.16`, dossier
`/home/ubuntu/blue-intelligence`). NAVIGUIDE déploie vers Contabo
(`naviguide@13.140.164.185`, dossier `/home/naviguide/naviguide`),
et le nom public du job est `naviguide.fr`. La clé de site passée à
`apply-site.sh` reste `simulator` : c'est le nom que le script connaît
pour l'unité `naviguide-simulator`.

Les quotes autour de `END_…` sont obligatoires : le diff contient des
`${{ }}` que le shell ne doit pas développer.

#### Blue Intelligence

Jobs de `ci.yml` après le diff : `frontend`, `audit-tags`,
`deploy-gate`. Jobs de `deploy.yml` : `plan`, `blue-intelligence`,
`catch-up`. Branches : `main` seulement. Le cron `*/20` reste.
`dependabot.yml` garde npm `/frontend` et github-actions, retire npm
`/naviguide-simulator` et pip `/naviguide-simulator/server`, ajoute
pip `/backend` (groupe `backend-mineures-et-patchs`).
`prepare-ssh.sh` écrit `REMOTE_APP=/home/ubuntu/blue-intelligence`.
Le défaut `ubuntu@135.125.226.16` reste.

```bash
cd /tmp/bi-work
git apply <<'END_BI_CI'
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -4,9 +4,7 @@
 #   - jest verrouille l'ordre des couches carte et le registre des fonds ;
 #   - le build CRA attrape les régressions de bundling (maplibre chargé à la demande) ;
 #   - le script d'audit des tags tourne en mode GeoJSON sur les seeds (stdlib pur) ;
-#   - simulateur : si la PR touche naviguide-simulator/, `npm test` (node --test),
-#     `vite build` et `pytest` (fetch mocké) — une croix rouge sur la PR avant
-#     qu'un lot casse S1–S7, le juge ou le sac ici() sans qu'on le voie.
+# Copie Blue Intelligence. Les jobs simulateur ne sont pas dans ce dépôt.
 
 on:
   pull_request:
@@ -40,133 +38,6 @@
         env:
           CI: "true"
 
-  # Le simulateur n'est testé que si la PR (ou le push) le touche : les PR
-  # Blue Intelligence / NAVIGUIDE restent aussi rapides qu'avant.
-  changes:
-    runs-on: ubuntu-latest
-    outputs:
-      simulator: ${{ steps.filter.outputs.simulator }}
-    steps:
-      - uses: actions/checkout@v7
-      - uses: dorny/paths-filter@v4
-        id: filter
-        with:
-          filters: |
-            simulator:
-              - 'naviguide-simulator/**'
-              - '.github/workflows/ci.yml'
-
-  simulator:
-    name: simulateur — tests JS, build, pytest
-    runs-on: ubuntu-latest
-    # Un test qui ne rend pas la main doit échouer vite, pas bloquer 6 h.
-    timeout-minutes: 20
-    needs: changes
-    if: needs.changes.outputs.simulator == 'true'
-    defaults:
-      run:
-        working-directory: naviguide-simulator
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: naviguide-simulator/package-lock.json
-      - run: npm ci
-      - name: Tests JS (moteur, juge, skipper, briefing, contrats UI)
-        run: npm test
-      - name: Build Vite
-        run: npm run build
-      - uses: actions/setup-python@v7
-        with:
-          python-version: "3.12"
-          cache: pip
-          cache-dependency-path: naviguide-simulator/server/requirements.txt
-      - run: pip install -r server/requirements.txt
-      - name: Tests Python (API 8010, sac ici(), pipeline météo, récit)
-        run: python -m pytest -q
-        env:
-          # Aucun secret : Copernicus et les LLM restent en repli / mock.
-          PYTHONDONTWRITEBYTECODE: "1"
-      # Sécurité P1 (lot H) : une dépendance avec une faille connue bloque la
-      # PR — critique côté npm (prod seulement), toute faille côté pip.
-      - name: Audit npm (dépendances de prod, critique = bloquant)
-        run: npm audit --omit=dev --audit-level=critical
-      - name: Audit pip (server/requirements.txt)
-        run: |
-          pip install -q pip-audit
-          python -m pip_audit -r server/requirements.txt --progress-spinner off
-
-  # Recette automatique des lots (RG16 / D11) : une invocation Playwright
-  # (fumée + lots) sur le build de prod, API hors ligne, stock figé.
-  # Un spec rouge bloque la PR. Specs `poste` (hindcast, LLM, réseau) ignorés en CI.
-  simulator-e2e:
-    # 28 sept. : la suite (101 specs, ~6 min en un job) est coupée en six tranches parallèles (--shard) :
-    # même contenu, même API sur le stock figé, ~1 min de tests chacune + ~1 min 30 de mise en place.
-    # Six jobs verts = recette verte. Dépôt public : les runners Actions sont gratuits et illimités.
-    name: simulateur — recette automatique (Playwright, stock figé) ${{ matrix.shard }}/6
-    runs-on: ubuntu-latest
-    timeout-minutes: 12
-    needs: changes
-    if: needs.changes.outputs.simulator == 'true'
-    strategy:
-      fail-fast: false
-      matrix:
-        shard: [1, 2, 3, 4, 5, 6]
-    defaults:
-      run:
-        working-directory: naviguide-simulator
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: naviguide-simulator/package-lock.json
-      - uses: actions/setup-python@v7
-        with:
-          python-version: "3.12"
-          cache: pip
-          cache-dependency-path: naviguide-simulator/server/requirements.txt
-      - run: npm ci
-      - run: npm run build
-      - run: pip install -r server/requirements.txt
-      - name: Version Playwright (clé de cache)
-        id: pw
-        run: |
-          echo "version=$(node -p "require('./package-lock.json').packages['node_modules/@playwright/test'].version")" >> "$GITHUB_OUTPUT"
-      - uses: actions/cache@v6
-        with:
-          path: ~/.cache/ms-playwright
-          key: playwright-${{ runner.os }}-${{ steps.pw.outputs.version }}
-          restore-keys: |
-            playwright-${{ runner.os }}-
-      - run: npx playwright install --with-deps chromium
-      - name: Recette automatique (fumée + lots, stock figé) — tranche ${{ matrix.shard }}/6
-        env:
-          PW_WITH_API: "1"
-        run: npx playwright test e2e/smoke.spec.js e2e/lots --shard=${{ matrix.shard }}/6
-      - name: Résumé d'étape
-        if: always()
-        run: node scripts/e2e-summary.mjs test-results/e2e.json >> "$GITHUB_STEP_SUMMARY"
-      # Le rapport JSON (quelques dizaines de ko) est toujours conservé : c'est lui qui liste
-      # les « verts avec réserve » (chemins à vide) relus dans docs/SPECS_E2E_TRIAGE_2026-09-29.md.
-      - uses: actions/upload-artifact@v7
-        if: always()
-        with:
-          name: e2e-json-${{ matrix.shard }}
-          path: naviguide-simulator/test-results/e2e.json
-          retention-days: 3
-          if-no-files-found: ignore
-      - uses: actions/upload-artifact@v7
-        if: failure()
-        with:
-          name: playwright-report-${{ matrix.shard }}
-          path: naviguide-simulator/playwright-report
-          retention-days: 7
-          if-no-files-found: ignore
-
   audit-tags:
     runs-on: ubuntu-latest
     steps:
@@ -184,8 +55,6 @@
         run: |
           bash -n infra/vps/deploy-app.sh
           bash -n infra/vps/sync-public-nginx.sh
-          bash -n infra/vps/naviguide/deploy-naviguide.sh
-          bash -n infra/vps/naviguide/deploy-simulator.sh
           bash -n infra/vps/ci/prepare-ssh.sh
           bash -n infra/vps/ci/rsync-to-vps.sh
           bash -n infra/vps/ci/apply-site.sh
END_BI_CI
git apply <<'END_BI_DEPLOY'
--- a/.github/workflows/deploy.yml
+++ b/.github/workflows/deploy.yml
@@ -1,14 +1,13 @@
 name: Déploiement VPS
 
-# Trois sites, un job chacun. Build sur GitHub (pas de npm/pip sur le VPS
-# 8 Go). Blue Intelligence attend qu'aucun run d'enrichissement / Complet
-# n'occupe uvicorn ; le rattrapage toutes les 20 min reprend la file.
+# Blue Intelligence seul, vers l'OVH. Secret VPS_HOST (le défaut de
+# prepare-ssh.sh reste ubuntu@135.125.226.16). Dossier distant :
+# /home/ubuntu/blue-intelligence. Le cron */20 reprend les runs uvicorn
+# reportés. Pas de branche recette, pas de job naviguide ni simulator.
 
 on:
   push:
-    # `recette` = tête de pile poussée par infra/agents/run_lots.py --publish-tip :
-    # simulateur seulement (plan_deploy.py), jamais BI ni l'ancien NAVIGUIDE.
-    branches: [main, recette]
+    branches: [main]
   schedule:
     - cron: "*/20 * * * *"
   workflow_dispatch:
@@ -16,8 +15,8 @@
       site:
         description: "Site à déployer"
         type: choice
-        options: [all, blue-intelligence, naviguide, simulator]
-        default: all
+        options: [blue-intelligence]
+        default: blue-intelligence
       force:
         description: "Forcer Blue Intelligence même si un run est en cours"
         type: boolean
@@ -93,79 +92,6 @@
             "$VPS_HOST" \
             "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh blue-intelligence"
 
-  naviguide:
-    name: www.naviguide.fr
-    needs: plan
-    if: needs.plan.outputs.naviguide == 'true'
-    runs-on: ubuntu-latest
-    timeout-minutes: 40
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: naviguide/naviguide-app/package-lock.json
-      - name: Env production Vite
-        run: |
-          printf '%s\n' \
-            'VITE_API_URL=https://www.naviguide.fr' \
-            'VITE_ORCHESTRATOR_URL=https://www.naviguide.fr' \
-            'VITE_WEATHER_ROUTING_URL=https://www.naviguide.fr' \
-            'VITE_POLAR_API_URL=https://www.naviguide.fr' \
-            'VITE_SEAMAP_STYLE_URL=https://www.naviguide.fr/tiles/seamap/style.json' \
-            > naviguide/naviguide-app/.env.production
-      - working-directory: naviguide/naviguide-app
-        run: npm ci
-      - working-directory: naviguide/naviguide-app
-        run: npm run build
-      - run: test -f naviguide/naviguide-app/dist/index.html
-      - name: SSH
-        env:
-          VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
-          VPS_HOST: ${{ secrets.VPS_HOST }}
-        run: bash infra/vps/ci/prepare-ssh.sh
-      - name: Rsync + apply
-        env:
-          SHA: ${{ github.sha }}
-        run: |
-          bash infra/vps/ci/rsync-to-vps.sh naviguide
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" \
-            "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh naviguide"
-
-  simulator:
-    name: simulator.naviguide.fr
-    needs: plan
-    if: needs.plan.outputs.simulator == 'true'
-    runs-on: ubuntu-latest
-    timeout-minutes: 40
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: naviguide-simulator/package-lock.json
-      - working-directory: naviguide-simulator
-        run: npm ci
-      - working-directory: naviguide-simulator
-        run: npm run build
-      - run: test -f naviguide-simulator/dist/index.html
-      - name: SSH
-        env:
-          VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
-          VPS_HOST: ${{ secrets.VPS_HOST }}
-        run: bash infra/vps/ci/prepare-ssh.sh
-      - name: Rsync + apply
-        env:
-          SHA: ${{ github.sha }}
-        run: |
-          bash infra/vps/ci/rsync-to-vps.sh simulator
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" \
-            "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh simulator"
-
   catch-up:
     name: Rattrapage (runs reportés)
     needs: plan
END_BI_DEPLOY
git apply <<'END_BI_DEPENDABOT'
--- a/.github/dependabot.yml
+++ b/.github/dependabot.yml
@@ -4,19 +4,6 @@
 version: 2
 updates:
   - package-ecosystem: npm
-    directory: /naviguide-simulator
-    schedule: { interval: weekly, day: monday, time: "07:00", timezone: Europe/Paris }
-    open-pull-requests-limit: 5
-    groups:
-      # Vite et ses plugins avancent ensemble (27 sept. : plugin-react 6 seul → rouge, il exige Vite 8).
-      vite:
-        patterns: ["vite", "@vitejs/*"]
-        update-types: [major, minor, patch]
-      simulateur-mineures-et-patchs:
-        update-types: [minor, patch]
-    commit-message: { prefix: "chore(deps)" }
-    labels: [dependances]
-  - package-ecosystem: npm
     directory: /frontend
     schedule: { interval: weekly, day: monday, time: "07:00", timezone: Europe/Paris }
     open-pull-requests-limit: 5
@@ -35,11 +22,11 @@
     commit-message: { prefix: "chore(deps)" }
     labels: [dependances]
   - package-ecosystem: pip
-    directory: /naviguide-simulator/server
+    directory: /backend
     schedule: { interval: weekly, day: monday, time: "07:00", timezone: Europe/Paris }
     open-pull-requests-limit: 5
     groups:
-      serveur-mineures-et-patchs:
+      backend-mineures-et-patchs:
         update-types: [minor, patch]
     commit-message: { prefix: "chore(deps)" }
     labels: [dependances]
END_BI_DEPENDABOT
git apply <<'END_BI_PREPARE'
--- a/infra/vps/ci/prepare-ssh.sh
+++ b/infra/vps/ci/prepare-ssh.sh
@@ -28,7 +28,7 @@
 {
   echo "VPS_HOST=$VPS_HOST"
   echo "VPS_SSH_IDENTITY=$KEY_FILE"
-  echo "REMOTE_APP=/home/ubuntu/blue-intelligence-map"
+  echo "REMOTE_APP=/home/ubuntu/blue-intelligence"
 } >> "${GITHUB_ENV:-/dev/stdout}"
 
 echo "SSH prêt pour $VPS_HOST"
END_BI_PREPARE
bash -n infra/vps/deploy-app.sh
bash -n infra/vps/sync-public-nginx.sh
bash -n infra/vps/ci/prepare-ssh.sh
bash -n infra/vps/ci/rsync-to-vps.sh
bash -n infra/vps/ci/apply-site.sh
bash -n infra/vps/ci/apply-pending.sh
python3 infra/vps/ci/test_prod_jobs_busy.py
git add .github/workflows/ci.yml .github/workflows/deploy.yml .github/dependabot.yml infra/vps/ci/prepare-ssh.sh
git commit -m "chore: limiter la CI Blue Intelligence à son déploiement OVH"
```

Le `deploy-gate` de cette copie ne nomme plus
`infra/vps/naviguide/deploy-naviguide.sh` ni `deploy-simulator.sh`.
Ces deux fichiers ne sont pas dans le dépôt filtré. Les six `bash -n`
et les 31 tests doivent finir sans erreur. C'est le vert du
`deploy-gate` côté Blue Intelligence.

#### NAVIGUIDE

Jobs de `ci.yml` après le diff : `changes`, `simulator`,
`simulator-e2e`, `deploy-gate`. `deploy.yml` n'a qu'un job,
`naviguide`, affiché `naviguide.fr`. Déclencheurs : poussée sur `main`,
et `workflow_dispatch`. Pas de cron, pas de branche `recette`, pas de
job `plan`. Chaque poussée sur `main` déploie. `FORCE_DEPLOY=0`.
`dependabot.yml` garde npm `/naviguide-simulator`, pip
`/naviguide-simulator/server` et github-actions. Le bloc npm
`/frontend` est retiré. `prepare-ssh.sh` exige `VPS_HOST`. La valeur
attendue est `naviguide@13.140.164.185`.
`REMOTE_APP=/home/naviguide/naviguide`.

```bash
cd /tmp/ng-work
git apply <<'END_NG_CI'
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1,12 +1,7 @@
 name: CI
 
-# Tests rapides et hermétiques (aucun secret, aucun service) :
-#   - jest verrouille l'ordre des couches carte et le registre des fonds ;
-#   - le build CRA attrape les régressions de bundling (maplibre chargé à la demande) ;
-#   - le script d'audit des tags tourne en mode GeoJSON sur les seeds (stdlib pur) ;
-#   - simulateur : si la PR touche naviguide-simulator/, `npm test` (node --test),
-#     `vite build` et `pytest` (fetch mocké) — une croix rouge sur la PR avant
-#     qu'un lot casse S1–S7, le juge ou le sac ici() sans qu'on le voie.
+# Copie NAVIGUIDE. Frontend Blue Intelligence et audit des tags ne sont pas
+# dans ce dépôt. Le simulateur est testé si la PR le touche.
 
 on:
   pull_request:
@@ -17,29 +12,6 @@
   contents: read
 
 jobs:
-  frontend:
-    runs-on: ubuntu-latest
-    defaults:
-      run:
-        working-directory: frontend
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: frontend/package-lock.json
-      - run: npm ci
-      - run: npm test
-        env:
-          CI: "true"
-      # frontend/scripts/build.js ignore uniquement le warning webpack de
-      # maplibre-gl (workers via new URL dynamique). Les autres warnings
-      # restent des erreurs. Le worker est copié dans public/maplibre/.
-      - run: npm run build
-        env:
-          CI: "true"
-
   # Le simulateur n'est testé que si la PR (ou le push) le touche : les PR
   # Blue Intelligence / NAVIGUIDE restent aussi rapides qu'avant.
   changes:
@@ -167,13 +139,6 @@
           retention-days: 7
           if-no-files-found: ignore
 
-  audit-tags:
-    runs-on: ubuntu-latest
-    steps:
-      - uses: actions/checkout@v7
-      - name: Audit des tags (mode GeoJSON, sans Mongo)
-        run: python3 scripts/audit_tags.py --geojson seed/projects.geojson seed/ports_of_entry.geojson
-
   deploy-gate:
     runs-on: ubuntu-latest
     steps:
@@ -182,8 +147,6 @@
         run: python3 infra/vps/ci/test_prod_jobs_busy.py
       - name: Syntaxe bash des scripts VPS
         run: |
-          bash -n infra/vps/deploy-app.sh
-          bash -n infra/vps/sync-public-nginx.sh
           bash -n infra/vps/naviguide/deploy-naviguide.sh
           bash -n infra/vps/naviguide/deploy-simulator.sh
           bash -n infra/vps/ci/prepare-ssh.sh
END_NG_CI
git apply <<'END_NG_DEPLOY'
--- a/.github/workflows/deploy.yml
+++ b/.github/workflows/deploy.yml
@@ -1,143 +1,27 @@
 name: Déploiement VPS
 
-# Trois sites, un job chacun. Build sur GitHub (pas de npm/pip sur le VPS
-# 8 Go). Blue Intelligence attend qu'aucun run d'enrichissement / Complet
-# n'occupe uvicorn ; le rattrapage toutes les 20 min reprend la file.
+# NAVIGUIDE seul, vers Contabo. Secret VPS_HOST = naviguide@13.140.164.185.
+# prepare-ssh.sh de cette copie n'a pas de défaut OVH. Dossier distant :
+# /home/naviguide/naviguide. Chaque poussée sur main déploie https://naviguide.fr.
+# Pas de cron, pas de branche recette (la recette est le tunnel du Mac).
+# La clé de site `simulator` est celle de apply-site.sh : c'est l'unité
+# naviguide-simulator, qui sert le nom public naviguide.fr.
 
 on:
   push:
-    # `recette` = tête de pile poussée par infra/agents/run_lots.py --publish-tip :
-    # simulateur seulement (plan_deploy.py), jamais BI ni l'ancien NAVIGUIDE.
-    branches: [main, recette]
-  schedule:
-    - cron: "*/20 * * * *"
+    branches: [main]
   workflow_dispatch:
-    inputs:
-      site:
-        description: "Site à déployer"
-        type: choice
-        options: [all, blue-intelligence, naviguide, simulator]
-        default: all
-      force:
-        description: "Forcer Blue Intelligence même si un run est en cours"
-        type: boolean
-        default: false
 
 concurrency:
-  group: deploy-vps
+  group: deploy-naviguide
   cancel-in-progress: false
 
 permissions:
   contents: read
 
-env:
-  FORCE_DEPLOY: ${{ github.event.inputs.force == 'true' && '1' || '0' }}
-
 jobs:
-  plan:
-    name: Plan
-    runs-on: ubuntu-latest
-    outputs:
-      bi: ${{ steps.plan.outputs.bi }}
-      naviguide: ${{ steps.plan.outputs.naviguide }}
-      simulator: ${{ steps.plan.outputs.simulator }}
-      catch_up: ${{ steps.plan.outputs.catch_up }}
-    steps:
-      - uses: actions/checkout@v7
-        with:
-          fetch-depth: 0
-      - id: plan
-        env:
-          EVENT_NAME: ${{ github.event_name }}
-          EVENT_BEFORE: ${{ github.event.before }}
-          INPUT_SITE: ${{ github.event.inputs.site }}
-          GITHUB_SHA: ${{ github.sha }}
-          REF_NAME: ${{ github.ref_name }}
-        run: python3 infra/vps/ci/plan_deploy.py >> "$GITHUB_OUTPUT"
-
-  blue-intelligence:
-    name: blueintelligence.online
-    needs: plan
-    if: needs.plan.outputs.bi == 'true'
-    runs-on: ubuntu-latest
-    timeout-minutes: 40
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: frontend/package-lock.json
-      - working-directory: frontend
-        run: npm ci
-      - name: Build production
-        working-directory: frontend
-        env:
-          CI: "true"
-          REACT_APP_BACKEND_URL: ""
-          REACT_APP_SEAMAP_STYLE_URL: https://blueintelligence.online/tiles/seamap/style.json
-        run: npm run build
-      - name: Vérifier le bundle
-        run: test -f frontend/build/index.html
-      - name: SSH
-        env:
-          VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
-          VPS_HOST: ${{ secrets.VPS_HOST }}
-        run: bash infra/vps/ci/prepare-ssh.sh
-      - name: Rsync + apply
-        env:
-          SHA: ${{ github.sha }}
-        run: |
-          bash infra/vps/ci/rsync-to-vps.sh blue-intelligence
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" \
-            "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh blue-intelligence"
-
   naviguide:
-    name: www.naviguide.fr
-    needs: plan
-    if: needs.plan.outputs.naviguide == 'true'
-    runs-on: ubuntu-latest
-    timeout-minutes: 40
-    steps:
-      - uses: actions/checkout@v7
-      - uses: actions/setup-node@v7
-        with:
-          node-version-file: .nvmrc
-          cache: npm
-          cache-dependency-path: naviguide/naviguide-app/package-lock.json
-      - name: Env production Vite
-        run: |
-          printf '%s\n' \
-            'VITE_API_URL=https://www.naviguide.fr' \
-            'VITE_ORCHESTRATOR_URL=https://www.naviguide.fr' \
-            'VITE_WEATHER_ROUTING_URL=https://www.naviguide.fr' \
-            'VITE_POLAR_API_URL=https://www.naviguide.fr' \
-            'VITE_SEAMAP_STYLE_URL=https://www.naviguide.fr/tiles/seamap/style.json' \
-            > naviguide/naviguide-app/.env.production
-      - working-directory: naviguide/naviguide-app
-        run: npm ci
-      - working-directory: naviguide/naviguide-app
-        run: npm run build
-      - run: test -f naviguide/naviguide-app/dist/index.html
-      - name: SSH
-        env:
-          VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
-          VPS_HOST: ${{ secrets.VPS_HOST }}
-        run: bash infra/vps/ci/prepare-ssh.sh
-      - name: Rsync + apply
-        env:
-          SHA: ${{ github.sha }}
-        run: |
-          bash infra/vps/ci/rsync-to-vps.sh naviguide
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" \
-            "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh naviguide"
-
-  simulator:
-    name: simulator.naviguide.fr
-    needs: plan
-    if: needs.plan.outputs.simulator == 'true'
+    name: naviguide.fr
     runs-on: ubuntu-latest
     timeout-minutes: 40
     steps:
@@ -164,27 +48,4 @@
           bash infra/vps/ci/rsync-to-vps.sh simulator
           ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
             "$VPS_HOST" \
-            "SHA=$SHA FORCE_DEPLOY=$FORCE_DEPLOY SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh simulator"
-
-  catch-up:
-    name: Rattrapage (runs reportés)
-    needs: plan
-    if: needs.plan.outputs.catch_up == 'true'
-    runs-on: ubuntu-latest
-    timeout-minutes: 20
-    steps:
-      - uses: actions/checkout@v7
-      - name: SSH
-        env:
-          VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
-          VPS_HOST: ${{ secrets.VPS_HOST }}
-        run: bash infra/vps/ci/prepare-ssh.sh
-      - name: Synchroniser la sonde puis apply-pending
-        run: |
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" "mkdir -p $REMOTE_APP/infra/vps/ci"
-          rsync -az -e "ssh -i $VPS_SSH_IDENTITY -o BatchMode=yes -o IdentitiesOnly=yes" \
-            infra/vps/ci/ "$VPS_HOST:$REMOTE_APP/infra/vps/ci/"
-          ssh -i "$VPS_SSH_IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes \
-            "$VPS_HOST" \
-            "chmod +x $REMOTE_APP/infra/vps/ci/*.sh $REMOTE_APP/infra/vps/ci/*.py && bash $REMOTE_APP/infra/vps/ci/apply-pending.sh"
+            "SHA=$SHA FORCE_DEPLOY=0 SKIP_FRONTEND_BUILD=1 bash $REMOTE_APP/infra/vps/ci/apply-site.sh simulator"
END_NG_DEPLOY
git apply <<'END_NG_DEPENDABOT'
--- a/.github/dependabot.yml
+++ b/.github/dependabot.yml
@@ -16,24 +16,6 @@
         update-types: [minor, patch]
     commit-message: { prefix: "chore(deps)" }
     labels: [dependances]
-  - package-ecosystem: npm
-    directory: /frontend
-    schedule: { interval: weekly, day: monday, time: "07:00", timezone: Europe/Paris }
-    open-pull-requests-limit: 5
-    # Le frontend est un CRA 5 (react-scripts) : React 19 et Tailwind 4 sont des migrations, pas des bumps
-    # (27 sept. : PR rouges #376 #378 #379). On garde les mineures/patchs, on ignore ces majeures.
-    ignore:
-      - dependency-name: react
-        update-types: ["version-update:semver-major"]
-      - dependency-name: react-dom
-        update-types: ["version-update:semver-major"]
-      - dependency-name: tailwindcss
-        update-types: ["version-update:semver-major"]
-    groups:
-      frontend-mineures-et-patchs:
-        update-types: [minor, patch]
-    commit-message: { prefix: "chore(deps)" }
-    labels: [dependances]
   - package-ecosystem: pip
     directory: /naviguide-simulator/server
     schedule: { interval: weekly, day: monday, time: "07:00", timezone: Europe/Paris }
END_NG_DEPENDABOT
git apply <<'END_NG_PREPARE'
--- a/infra/vps/ci/prepare-ssh.sh
+++ b/infra/vps/ci/prepare-ssh.sh
@@ -1,6 +1,8 @@
 #!/usr/bin/env bash
 # Prépare la clé SSH du secret GitHub (à lancer sur le runner).
-# Variables : VPS_SSH_KEY (obligatoire), VPS_HOST (défaut ubuntu@135.125.226.16)
+# Variables : VPS_SSH_KEY et VPS_HOST, tous deux obligatoires.
+# VPS_HOST = naviguide@13.140.164.185. Pas de défaut : un secret vide
+# ne doit pas déployer sur l'OVH.
 set -euo pipefail
 
 if [ -z "${VPS_SSH_KEY:-}" ]; then
@@ -8,7 +10,10 @@
   exit 1
 fi
 
-VPS_HOST="${VPS_HOST:-ubuntu@135.125.226.16}"
+if [ -z "${VPS_HOST:-}" ]; then
+  echo "Secret VPS_HOST manquant. Valeur attendue : naviguide@13.140.164.185." >&2
+  exit 1
+fi
 HOST="${VPS_HOST##*@}"
 KEY_FILE="${HOME}/.ssh/github-deploy-vps"
 
@@ -28,7 +33,7 @@
 {
   echo "VPS_HOST=$VPS_HOST"
   echo "VPS_SSH_IDENTITY=$KEY_FILE"
-  echo "REMOTE_APP=/home/ubuntu/blue-intelligence-map"
+  echo "REMOTE_APP=/home/naviguide/naviguide"
 } >> "${GITHUB_ENV:-/dev/stdout}"
 
 echo "SSH prêt pour $VPS_HOST"
END_NG_PREPARE
bash -n infra/vps/naviguide/deploy-naviguide.sh
bash -n infra/vps/naviguide/deploy-simulator.sh
bash -n infra/vps/ci/prepare-ssh.sh
bash -n infra/vps/ci/rsync-to-vps.sh
bash -n infra/vps/ci/apply-site.sh
bash -n infra/vps/ci/apply-pending.sh
python3 infra/vps/ci/test_prod_jobs_busy.py
git add .github/workflows/ci.yml .github/workflows/deploy.yml .github/dependabot.yml infra/vps/ci/prepare-ssh.sh
git commit -m "chore: limiter la CI NAVIGUIDE au déploiement de naviguide.fr"
```

Le `deploy-gate` de cette copie ne nomme plus `infra/vps/deploy-app.sh`
ni `infra/vps/sync-public-nginx.sh`. Ces deux fichiers ne sont pas
dans le dépôt filtré. Les six `bash -n` et les 31 tests doivent finir
sans erreur. C'est le vert du `deploy-gate` côté NAVIGUIDE.

### 6.7 Parité climatologie du simulateur, commit NAVIGUIDE

`naviguide-simulator/src/utils/recetteAg.test.js` lit quatre fois un
fichier sous `frontend/src/components/map/`. Après le filtre, ce
dossier n'est pas dans NAVIGUIDE. Le test I (« atlas climatologie »)
échoue. Les deux lectures de `cycloneTracks.js` sont celles que la
répétition a nommées. Les deux lectures suivantes visent
`useClimatologyLayer.js`, dans le même dossier. Le même commit copie
les deux fichiers.

Les quatre assertions ne changent pas. Ce sont toujours
`unwrapCycloneCoords`, l'absence de `splitCycloneAtMeridian`,
`cycloneLatLngCopies` et `groupCycloneFeatures`. Le test lit aussi,
sans changement, `../layers/climatologyWorld.js` et
`../layers/useClimatologyLayer.js` : la copie locale du simulateur
reste contrôlée, et la copie figée vient de Blue Intelligence.

La copie se fait depuis le bare Blue Intelligence, qui a encore
`frontend/`. Dans `/tmp/ng-work` :

```bash
cd /tmp/ng-work
mkdir -p naviguide-simulator/src/utils/fixtures/climatology-bi
git --git-dir=/tmp/bi-bare show HEAD:frontend/src/components/map/cycloneTracks.js \
  > naviguide-simulator/src/utils/fixtures/climatology-bi/cycloneTracks.js
git --git-dir=/tmp/bi-bare show HEAD:frontend/src/components/map/useClimatologyLayer.js \
  > naviguide-simulator/src/utils/fixtures/climatology-bi/useClimatologyLayer.js
test "$(wc -c < naviguide-simulator/src/utils/fixtures/climatology-bi/cycloneTracks.js)" -eq 1870
test "$(wc -c < naviguide-simulator/src/utils/fixtures/climatology-bi/useClimatologyLayer.js)" -eq 10513
git apply <<'END_RECETTE_AG'
--- a/naviguide-simulator/src/utils/recetteAg.test.js
+++ b/naviguide-simulator/src/utils/recetteAg.test.js
@@ -93,10 +93,10 @@
     assert.match(read("../layers/useClimatologyLayer.js"), /groupCycloneFeatures/);
     assert.match(read("../layers/climatologyWorld.js"), /unwrapCycloneCoords/);
     assert.doesNotMatch(read("../layers/climatologyWorld.js"), /splitCycloneAtMeridian/);
-    assert.match(read("../../../frontend/src/components/map/cycloneTracks.js"), /unwrapCycloneCoords/);
-    assert.doesNotMatch(read("../../../frontend/src/components/map/cycloneTracks.js"), /splitCycloneAtMeridian/);
-    assert.match(read("../../../frontend/src/components/map/useClimatologyLayer.js"), /cycloneLatLngCopies/);
-    assert.match(read("../../../frontend/src/components/map/useClimatologyLayer.js"), /groupCycloneFeatures/);
+    assert.match(read("./fixtures/climatology-bi/cycloneTracks.js"), /unwrapCycloneCoords/);
+    assert.doesNotMatch(read("./fixtures/climatology-bi/cycloneTracks.js"), /splitCycloneAtMeridian/);
+    assert.match(read("./fixtures/climatology-bi/useClimatologyLayer.js"), /cycloneLatLngCopies/);
+    assert.match(read("./fixtures/climatology-bi/useClimatologyLayer.js"), /groupCycloneFeatures/);
     assert.match(read("../layers/layerOrder.js"), /climatology-raster/);
     assert.match(read("../utils/atlasPoint.js"), /kind !== "climatology"/);
     assert.match(read("../engine/voyageClock.js"), /windAt/);
END_RECETTE_AG
node --test naviguide-simulator/src/utils/recetteAg.test.js
git add naviguide-simulator/src/utils/recetteAg.test.js naviguide-simulator/src/utils/fixtures/climatology-bi
git commit -m "test: figer la parité climatologie du simulateur hors de frontend"
```

`node --test` sur ce seul fichier doit afficher 8 tests et 0 échec.
Contrôle du 17 octobre 2026 au soir, sur une copie de travail de
`6dabfb84` : 8 tests, 0 échec. Le test ne charge pas les fichiers, il
les lit. Les tailles 1 870 et 10 513 octets sont celles de `main`.

### 6.8 `climatology_query`, deux commits

`backend/tests/test_climatology.py` contient
`test_naviguide_query_not_painted`. La fonction ajoute
`naviguide/naviguide-api` au `sys.path` et importe `climatology_query`.
Ce module est dans NAVIGUIDE. Après le filtre Blue Intelligence,
l'import lève `ModuleNotFoundError: No module named 'climatology_query'`.

La consigne est de ne modifier un test que s'il contredit une
instruction du propriétaire. Celui-ci ne la contredit pas : il vérifie
le module qui vit dans l'autre dépôt. On ne l'affaiblit pas et on ne
le marque pas `skip`. On le déplace vers le dépôt qui possède le
module. Les nombres 14,6 / −61,0 vers 38,7 / −27,2, le compte de
septembre supérieur à 0 et le compte de mars égal à 0, restent couverts
dans Blue Intelligence par `test_crossings_martinique_azores` (mêmes
coordonnées, via l'API du dépôt). Les deux `painted is False` partent
avec la fonction, parce que seul `climatology_query` les pose.

#### Commit Blue Intelligence

Dans `/tmp/bi-work`, sur le fichier tel que le filtre l'a copié :

```bash
cd /tmp/bi-work
git apply <<'END_BI_CLIMATO'
--- a/backend/tests/test_climatology.py
+++ b/backend/tests/test_climatology.py
@@ -497,20 +497,6 @@
     assert r.status_code == 422
 
 
-def test_naviguide_query_not_painted():
-    ng_api = Path(__file__).resolve().parents[2] / "naviguide" / "naviguide-api"
-    sys.path.insert(0, str(ng_api))
-    import climatology_query as nq
-    meta = nq.meta(9)
-    assert meta["kind"] == KIND
-    assert meta["painted"] is False
-    pt = nq.point(14.6, -61.0, 9, dest_lat=38.7, dest_lon=-27.2)
-    assert pt["painted"] is False
-    assert pt["cyclone"]["crossings_if_leg"]["count"] > 0
-    mar = nq.crossings(14.6, -61.0, 38.7, -27.2, 3)
-    assert mar["count"] == 0
-
-
 def test_live_cmems_snapshots_are_honest():
     """Recipe A on committed grids — skip if generation has not run."""
     if not (wind_mod.has_snapshot(3) and wave_mod.has_snapshot(7) and current_mod.has_snapshot(2)):
END_BI_CLIMATO
git add backend/tests/test_climatology.py
git commit -m "test: retirer l'import de climatology_query du dépôt Blue Intelligence"
```

`pytest backend/tests/test_climatology.py -k test_naviguide_query_not_painted`
ne collecte plus cette fonction.

`test_meteo_agent_cites_ibtracs_integer`, plus bas dans le même
fichier, fait le même détour par `naviguide/naviguide-api` puis importe
`agents.meteo_agent`. `pytest.importorskip("langgraph")` le saute :
`langgraph` n'est pas dans les requirements du backend. La répétition
ne l'a pas vu échouer. Ce commit ne le déplace pas.

#### Commit NAVIGUIDE

Dans `/tmp/ng-work`. Le fichier est nouveau. Les cinq assertions sont
celles du monodépôt. `KIND` est la constante que le test d'origine
importait de `app.services.climatology_common`. Le module la lit au
même endroit (`climatology_query._services`). L'import
`climatology_query` se fait dans le dossier du module : pytest ajoute
ce dossier au chemin, le `sys.path` vers `naviguide/naviguide-api`
n'est plus utile.

```bash
cd /tmp/ng-work
mkdir -p naviguide/naviguide-api
cat > naviguide/naviguide-api/test_climatology_query.py <<'END_NG_CLIMATO'
"""test_naviguide_query_not_painted, repris de backend/tests/test_climatology.py.

Le module est dans ce dossier. Les cinq assertions sont celles du monodépôt.
"""
import climatology_query as nq


def test_naviguide_query_not_painted():
    KIND = nq._services()["KIND"]
    meta = nq.meta(9)
    assert meta["kind"] == KIND
    assert meta["painted"] is False
    pt = nq.point(14.6, -61.0, 9, dest_lat=38.7, dest_lon=-27.2)
    assert pt["painted"] is False
    assert pt["cyclone"]["crossings_if_leg"]["count"] > 0
    mar = nq.crossings(14.6, -61.0, 38.7, -27.2, 3)
    assert mar["count"] == 0
END_NG_CLIMATO
git add naviguide/naviguide-api/test_climatology_query.py
git commit -m "test: placer test_naviguide_query_not_painted à côté de climatology_query"
```

Limite, à lire avant de lancer ce fichier. `climatology_query._services`
importe encore `app.services` depuis `backend/`, que le filtre
NAVIGUIDE n'a pas. L'exécution de ce test lève donc
`ModuleNotFoundError` sur `app` tant que cette frontière n'est pas un
appel HTTP. La collecte du fichier, elle, passe : l'import backend est
dans la fonction, pas au chargement du module. Le pytest de la
répétition est celui de `backend/tests/`. Il ne collecte pas
`naviguide/`. Ce commit rend ce pytest-là libre de l'import
`climatology_query`. Il ne prétend pas que le test NAVIGUIDE passe
sans le backend.

#### L'autre échec backend, déjà sur le monodépôt

`backend/tests/test_poe_v2_pipeline.py::TestFindSourcesTinyfish::test_serper_google_style_merged`
échoue déjà avant le filtre. L'assertion (ligne 1045) attend une
requête serper qui contient « Ports of Entry » ou « port d'entrée ».
La répétition l'a revue après le filtre, même échec. Ce plan ne
modifie ni ce test ni le code qu'il appelle.

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
  zone DNS chez OVH. Après la bascule, ce nom répond `301` vers
  `https://naviguide.fr`.
- `simulator` est un A de la même zone vers `135.125.226.16`. Après la
  bascule, même `301`.
- L'apex `naviguide.fr` est aujourd'hui un `301` vers `www`. Après la
  bascule, c'est l'adresse du produit.
- Le certificat Let's Encrypt `naviguide.fr` (apex + www, puis
  `simulator` ajouté) est sur l'OVH. Un certificat neuf, trois noms,
  est émis sur Contabo le jour J. L'ancien reste.

| | Blue Intelligence | NAVIGUIDE |
|---|---|---|
| Machine | OVH `135.125.226.16`, compte `ubuntu` | Contabo `13.140.164.185`, compte `naviguide`, Ubuntu 24.04 |
| Code aujourd'hui | `~/blue-intelligence-map` | pas encore là |
| Code après la séparation | `~/blue-intelligence` | `~/naviguide` |
| Données runtime | Mongo `blueintel_db` sur `127.0.0.1:27017` | fichiers dans `~/naviguide-data/`. Pas de Mongo. |
| Sites | `blueintelligence.online` | `naviguide.fr` (le produit). `www` et `simulator` répondent `301`. Recette : `recette.naviguide.fr` (tunnel du Mac, pas Contabo). |

Le dossier OVH `~/blue-intelligence-map` et son `voyage_data/` restent
sur le disque. En cas d'échec, les services OVH sont encore là : on remet
les unités systemd vers ce dossier, et les enregistrements A de
`naviguide.fr` vers `135.125.226.16`.

### 7.1 Vérifier Contabo, sans y installer Mongo

La machine est déjà sécurisée. On vérifie. On ne réécrit pas `ufw`
(une règle fausse peut fermer le SSH). On n'installe pas `mongod`.

```bash
ssh naviguide@13.140.164.185
```

```bash
whoami
. /etc/os-release
echo "$PRETTY_NAME"
sudo ufw status verbose
ss -ltn | grep 27017 || echo "rien n'écoute sur 27017"
```

Résultats attendus : `naviguide`, une ligne `Ubuntu 24.04`, `ufw` actif,
entrées 22, 80 et 443, pas d'autre port public, et « rien n'écoute sur
27017 ». Un écart : on s'arrête, on ne « corrige » pas le pare-feu dans
cette procédure.

Depuis le Mac, le port Mongo n'est pas joignable. L'échec est le
résultat attendu, sur les deux machines :

```bash
nc -vz -G 5 13.140.164.185 27017
nc -vz -G 5 135.125.226.16 27017
```

Place libre sur Contabo, avant la copie de 5,5 Go et plus. On ne
supprime rien pour la faire :

```bash
df -B1 --output=avail "$HOME"
```

Il faut au moins 8 Go. Sinon, stop.

## 8. Copier les fichiers NAVIGUIDE vers Contabo

Le transfert est une copie de fichiers sur le port 22. Pas de tunnel
`ssh -L` vers Mongo, pas d'URI vers l'IP de l'OVH, pas de
`mongodump`. Le simulateur n'a pas besoin du Mongo Blue Intelligence :
ports, AMP et climatologie passent par
`https://blueintelligence.online/api`. Passer le stock `official-store/`
sur Mongo serait un autre chantier (section 10). Ce plan ne le fait pas.

La copie de la section 1 est la sauvegarde d'avant les opérations git.
Le jour du transfert, on en refait une : le SQLite a pu recevoir des
perles depuis. Les deux restent. On ne supprime pas celle de l'OVH.

### 8.1 Arrêt bref, export, rsync

Sur l'OVH, compte `ubuntu` :

```bash
set +x
STAMP=$(date -u +%F)
SRC="$HOME/blue-intelligence-map/naviguide-simulator/server"
DEST="$HOME/backups/naviguide-move-$STAMP"
mkdir -p "$DEST/fichiers"
sudo systemctl stop naviguide-simulator
test "$(systemctl is-active naviguide-simulator)" = inactive || { echo "STOP"; exit 1; }
if sudo fuser "$SRC/voyage_data/naviguide.sqlite"; then
  echo "STOP sqlite encore ouvert"
  sudo systemctl start naviguide-simulator
  exit 1
fi

mkdir -p "$DEST/fichiers/voyage_data"
sqlite3 "$SRC/voyage_data/naviguide.sqlite" ".backup $DEST/fichiers/voyage_data/naviguide.sqlite"
rsync -a \
  --exclude 'naviguide.sqlite' --exclude 'naviguide.sqlite-wal' --exclude 'naviguide.sqlite-shm' \
  "$SRC/voyage_data/" "$DEST/fichiers/voyage_data/"
rsync -a "$SRC/polar_data/" "$DEST/fichiers/polar_data/"
rsync -a "$SRC/grib_data/" "$DEST/fichiers/grib_data/"
rsync -a "$SRC/saildocs_inbox/" "$DEST/fichiers/saildocs_inbox/"

sudo systemctl start naviguide-simulator
test "$(systemctl is-active naviguide-simulator)" = active || { echo "STOP redémarrage OVH échoué"; exit 1; }
```

Le service OVH est de nouveau `active` avant le long transfert. Les
fichiers d'origine n'ont pas été effacés. La sauvegarde dans `$DEST`
ne change plus : c'est elle qu'on envoie.

Comptes et sommes de cette sauvegarde :

```bash
python3 - << PY | tee "$DEST/comptes-sqlite-move.tsv"
import sqlite3
path = "$DEST/fichiers/voyage_data/naviguide.sqlite"
con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY 1"
for (name,) in con.execute(query):
    ident = '"' + name.replace('"', '""') + '"'
    n = con.execute(f"SELECT COUNT(*) FROM {ident}").fetchone()[0]
    print(f"{name}\t{n}")
con.close()
PY
(
  cd "$DEST"
  find fichiers -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum comptes-sqlite-move.tsv >> SHA256SUMS
)
```

Depuis l'OVH, essai de liaison vers Contabo. `BatchMode` évite d'attendre
un mot de passe :

```bash
ssh -o BatchMode=yes naviguide@13.140.164.185 echo ok
```

Si la ligne est `ok` :

```bash
ssh naviguide@13.140.164.185 "mkdir -p naviguide-data"
rsync -a --partial -e ssh "$DEST/fichiers/" naviguide@13.140.164.185:naviguide-data/
rsync -a -e ssh "$DEST/SHA256SUMS" "$DEST/comptes-sqlite-move.tsv" \
  naviguide@13.140.164.185:naviguide-data/
```

Si l'essai échoue, on ne fabrique pas une clé à la va-vite. On passe par
le Mac, qui a déjà les deux accès :

```bash
mkdir -p "$HOME/Backups/naviguide-move-$STAMP"
rsync -a --partial ubuntu@135.125.226.16:backups/naviguide-move-$STAMP/ \
  "$HOME/Backups/naviguide-move-$STAMP/"
rsync -a --partial "$HOME/Backups/naviguide-move-$STAMP/fichiers/" \
  naviguide@13.140.164.185:naviguide-data/
rsync -a "$HOME/Backups/naviguide-move-$STAMP/SHA256SUMS" \
  "$HOME/Backups/naviguide-move-$STAMP/comptes-sqlite-move.tsv" \
  naviguide@13.140.164.185:naviguide-data/
```

### 8.2 Vérifier les comptes et les SHA-256

Sur Contabo, compte `naviguide`. Les chemins du fichier `SHA256SUMS`
commencent par `fichiers/` parce qu'il a été calculé dans `$DEST` sur
l'OVH. Sur Contabo, ce contenu est directement dans `~/naviguide-data/`.
On ne lance pas `sha256sum -c` : le préfixe ne correspondrait pas.

```bash
python3 - << 'PY'
import hashlib, pathlib
root = pathlib.Path.home() / "naviguide-data"
listed = (root / "SHA256SUMS").read_text().splitlines()
bad = 0
seen = set()
for line in listed:
    if not line.strip() or line.endswith("comptes-sqlite-move.tsv"):
        continue
    digest, rel = line.split(None, 1)
    rel = rel.lstrip("*").strip()
    if not rel.startswith("fichiers/"):
        print("ECHEC préfixe", rel)
        bad += 1
        continue
    path = root / rel[len("fichiers/"):]
    seen.add(path)
    if not path.is_file():
        print("ECHEC absent", path)
        bad += 1
        continue
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != digest:
        print("ECHEC", path)
        bad += 1
print("fichiers", len(seen), "echecs", bad)
raise SystemExit(bad)
PY
```

Puis les comptes, sur le SQLite reçu :

```bash
python3 - << 'PY' | tee "$HOME/naviguide-data/comptes-sqlite-apres.tsv"
import sqlite3, pathlib
path = pathlib.Path.home() / "naviguide-data/voyage_data/naviguide.sqlite"
con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY 1"
for (name,) in con.execute(query):
    ident = '"' + name.replace('"', '""') + '"'
    n = con.execute(f"SELECT COUNT(*) FROM {ident}").fetchone()[0]
    print(f"{name}\t{n}")
con.close()
PY
diff -u "$HOME/naviguide-data/comptes-sqlite-move.tsv" "$HOME/naviguide-data/comptes-sqlite-apres.tsv"
```

`diff` ne doit rien afficher. `pearls`, `kv` et `moments` sont les trois
tables du contrat. `official-store/` est dans les SHA-256 : un fichier
manquant ou différent est un `ECHEC` du script Python.

On ne déclare pas la copie faite tant qu'une somme ou un compte diffère.
On ne supprime pas l'original OVH pour « recommencer propre ». On
recommence le `rsync` par-dessus.

### 8.3 Dire au simulateur où sont les fichiers

Dans `/home/naviguide/.config/naviguide/simulator.env`, chmod 600. Ne
pas y mettre `SIMULATOR_MONGO_URL`. Ne pas y mettre
`NAVIGUIDE_FORECAST_CACHE` : le dossier n'existe pas, le code le créera
dans le checkout le jour où il en a besoin, et le `rsync` du déploiement
l'exclut.

```text
NAVIGUIDE_VOYAGE_DIR=/home/naviguide/naviguide-data/voyage_data
NAVIGUIDE_GRIB_DIR=/home/naviguide/naviguide-data/grib_data
NAVIGUIDE_SAILDOCS_INBOX=/home/naviguide/naviguide-data/saildocs_inbox
NAVIGUIDE_POLAR_DIR=/home/naviguide/naviguide-data/polar_data
BI_API_URL=https://blueintelligence.online/api
```

`NAVIGUIDE_POLAR_DIR` ne marche qu'après la modification de `polar_api.py`
décrite en section 6.2. Tant que cette ligne de code n'est pas dans le
dépôt déployé, les polaires restent introuvables : on ne démarre pas le
service public Contabo avant ce commit.

`naviguide.env` (clés de l'ancien planificateur) reste dans la
sauvegarde de la section 1. On ne l'installe pas sur Contabo : les
unités `naviguide-api`, `naviguide-polar` et `naviguide-orchestrator`
ne sont pas démarrées. On n'affiche pas le fichier.

Sur l'OVH, recompter `blueintel_db` avec la commande `mongosh` de la
section 1.1. Le TSV doit être identique à `comptes-mongo-avant.tsv`
de la section 1 (les écritures Blue Intelligence du jour peuvent avoir
augmenté un compte : le noter dans le manifeste, ce n'est pas une perte).
Il n'y a toujours pas de base `naviguide_simulator` à recompter. Les
fichiers `voyage_data/` de l'OVH sont encore là : `du -sb` le montre.
On n'y supprime toujours rien.

Cron Contabo, ensuite : une fois par jour, `sqlite3 .backup` de
`naviguide.sqlite` et une archive du dossier `~/naviguide-data`, 14 jours,
dans `~/backups/naviguide/`. Pas de `mongodump`, pas du nom
`blue-*.archive.gz`. Ce cron n'existe pas dans le dépôt : le cron du
dépôt ne sauve que `blueintel_db`, et il reste sur l'OVH.

## 9. DNS, puis la liste qui autorise l'archivage

L'ordre des noms, des `301` et du certificat est en section 6.4. Ici,
le jour J.

Baisser le TTL des A de la zone `naviguide.fr` avant le jour J (valeur
actuelle : **non vérifiée**, la lire dans le panneau OVH). Le jour J,
chaque A qui vaut `135.125.226.16` pour l'apex, `www` et `simulator`
passe à `13.140.164.185`. Ajouter le CNAME `recette` vers
`<UUID>.cfargotunnel.com` (section 6.4). Ne pas modifier la zone
Cloudflare de `blueintelligence.online`, et ne pas y laisser l'apex
`naviguide.fr`.

Émettre le certificat sur Contabo à ce moment (`certbot`), pour
`naviguide.fr`, `www.naviguide.fr` et `simulator.naviguide.fr`. Le
certificat de l'OVH reste en place : c'est le retour arrière.

Déployer depuis chaque dépôt neuf (workflow_dispatch) seulement après
les secrets de la section 6.3. Le dépôt NAVIGUIDE doit rsync vers
`/home/naviguide/naviguide` sur Contabo, compte `naviguide`. Le dépôt
Blue Intelligence doit rsync vers `~/blue-intelligence` sur l'OVH,
compte `ubuntu`. Un merge sur `main` de chaque dépôt neuf déploie
ensuite la dernière version, sans action manuelle.

Juste avant de changer les A, refaire la section 8.1 et 8.2 (arrêt,
`.backup`, `rsync`, comptes, SHA-256, redémarrage OVH). La première
copie a vieilli dès que le simulateur OVH a repris. Cette deuxième
copie est celle que le DNS doit servir. L'original OVH reste en place.

Liste. Tout est vert avant d'archiver `Blue-Intelligence-Map` :

1. Sur l'OVH, `GET http://127.0.0.1:8001/api/` répond 200.
2. `https://blueintelligence.online/api/` répond 200.
3. `https://naviguide.fr` répond 200. La page est le voyage (le
   simulateur renommé NAVIGUIDE), servie par Contabo
   (`~/naviguide`). Ce n'est pas l'ancien planificateur.
4. `https://www.naviguide.fr` et `https://simulator.naviguide.fr`
   répondent `301` vers `https://naviguide.fr/`.
5. Le site lit Blue Intelligence par l'URL publique : une couche
   ports, PoE ou AMP s'affiche, et `BI_API_URL` sur Contabo est
   `https://blueintelligence.online/api`.
6. `systemctl is-active` : `blue-intelligence` est `active` sur l'OVH ;
   `naviguide-simulator` est `active` sur Contabo. `naviguide-api`,
   `naviguide-polar` et `naviguide-orchestrator` n'y sont pas installés.
7. Les comptes du manifeste sont égaux : collections `blueintel_db`
   sur l'OVH toujours présentes, tables `pearls`, `kv`, `moments` du
   dernier `.backup` égales sur Contabo, et `sha256sum` de
   `naviguide-data/` sans ligne `ECHEC`. Le dossier
   `voyage_data/` est encore sur l'OVH.
8. Un déploiement part de chaque dépôt neuf vers le bon hôte. Une
   poussée sur `main` déploie le site live. Une poussée sur
   `Blue-Intelligence-Map` ne déploie plus (workflows disabled). Le
   workflow NAVIGUIDE ne contient pas `135.125.226.16` ni `ubuntu@`,
   ni la branche `recette`.
9. Sur l'OVH, `ss -ltn` montre `27017` sur `127.0.0.1` seulement. Sur
   Contabo, rien n'écoute sur `27017`. Depuis le Mac, les deux `nc` de
   la section 7.1 échouent toujours.
10. Avec le tunnel du Mac démarré, `https://recette.naviguide.fr`
    répond 200. `BIM_TUNNEL_HOST` sur le Mac vaut
    `recette.naviguide.fr`.

Tant qu'une ligne est rouge, l'archive reste la référence et les
services OVH restent capables de reprendre le DNS. Quand les dix lignes
sont vertes, l'archivage GitHub de `Blue-Intelligence-Map` est possible.
L'arrêter des unités NAVIGUIDE sur l'OVH est un geste séparé, après un
mot du propriétaire : ce plan ne donne pas la commande. La tâche houle
de la section 6.4 se fait après ce vert, et elle ne bloque pas
l'archivage.

Retour arrière DNS, si une ligne 3, 4 ou 5 est rouge : remettre les A de
`naviguide.fr` sur `135.125.226.16`. Les données OVH sont encore là.

Si le 22 octobre 00:00 UTC arrive avant la fin : pas de commit `agent_poe`
dans l'archive avant cette heure. Après cette heure, une branche
`agent-poe` dans l'archive, déclarée dans le README du hackathon GenAI,
en attendant que le dépôt Blue Intelligence soit celui que le jury lit.

## 10. Décisions

### 10.1 Décidées le 17 octobre 2026 au soir

| Sujet | Décision |
|---|---|
| Nom public | Le simulateur est déployé sur `naviguide.fr` (Contabo) et s'appelle NAVIGUIDE. `www.naviguide.fr` et `simulator.naviguide.fr` répondent `301` vers `https://naviguide.fr`. L'ancien planificateur (`naviguide/`, `csw6hpki.run.complete.dev`) passe sous `Archives/naviguide-planificateur/` dans le dépôt filtré. Étapes DNS, nginx, TLS, CI et URL : section 6.4 et section 9. |
| CI | Chaque merge sur `main` déploie la dernière version en live. Le README du produit le dit, et ne dit plus « hors production ». |
| `docs/WORKFLOW_INDUSTRIEL.md` | Reste vivant. Le calendrier de la section 4 devient une ligne `à dater par le propriétaire`. Aucune date n'est inventée. |
| Doublons nova | Annulé. On ne touche pas à `Archives/naviguide-nova/`. `PLAN_DEV_NOVA.md` et `SETUP_NOVA_CREDITS.md` restent dans le monodépôt, exclus des deux fichiers de chemins. Rien n'est supprimé. Le README nova n'est pas réécrit. Les copies navsecops vont dans NAVIGUIDE. C'est le traitement d'avant la décision de suppression, sans le renvoi qui aurait modifié le dossier. |
| PR fermées | Confirmé. #510 (`15e41b4e`) : le plan s7 sous `docs/archives/` de NAVIGUIDE, et les lots RJ1/RJ2 ajoutés à `docs/LOTS_ORDRE_ET_PROMPTS.md`. #227 (`bef9f0f3`) : la notice et l'outil sous `docs/archives/verify-fiche-urls/` de Blue Intelligence. Section 6.4. |
| Recommandations #553 | Dossier `docs/archives/` (pas `docs/archive/`). Reçus `redites-*.txt` gardés. `FILM_DISCOURS_ETAT_2026-09-28.md` entier dans NAVIGUIDE : le filtre le copie à son chemin, puis la section 6.5 le déplace dans `naviguide-simulator/`. `LOTS_ORDRE_ET_PROMPTS.md` au même chemin. `REGLES_PARAMETRES.md` : original dans Blue Intelligence, copie du principe et des § 3.7 à 3.10 dans NAVIGUIDE. Index et manuels mis à jour après le filtre, dans chaque dépôt. Copie des règles Cursor communes dans chaque dépôt. Renommage de l'archive en `Blue-Intelligence-Map`. |
| Discours du film et réglages de la boucle | Décidés comme travaux d'après-filtre, pas faits dans cette PR. Deux commits dans la copie NAVIGUIDE (section 6.5), recommandés avant le premier push. Le discours va dans `naviguide-simulator/server/tests/fixtures/`, avec un renvoi dans `docs/`. Les chemins en dur de `infra/agents/` passent dans `infra/agents/repo_paths.py`. |
| Houle | Le bandeau « swell not shipped » n'est pas retiré au split. Après la bascule, on vérifie la couche à l'écran. On retire la phrase seulement si la houle s'affiche. |

### 10.2 Qui restent ouvertes

| Sujet | État dans ce plan |
|---|---|
| Noms exacts des deux dépôts neufs | **DÉCISION PROPRIÉTAIRE.** Recommandation en section 0. Stop avant `gh repo create` si les lignes sont vides. Le renommage de l'archive en `Blue-Intelligence-Map` est décidé (10.1). |
| Fusionner les 11 PR ouvertes avant le filtre | **DÉCISION PROPRIÉTAIRE.** Elles restent sur l'archive dans tous les cas. Les fusionner avant le filtre les fait entrer dans le `main` filtré. Les reprendre après demande un rebase, parce que les SHA ont changé. Ce plan ne fusionne rien. La liste du soir est en section 5. #545 est déjà sur `main`. |
| Pièces jointes des Releases `data-*` | **DÉCISION PROPRIÉTAIRE**, non bloquante. Les tags git vont dans Blue Intelligence. Les fichiers attachés restent sur l'archive. L'API et `backend/data/` suffisent à reconstruire. |
| Fichiers non commités sur le Mac | **DÉCISION PROPRIÉTAIRE** au vu de `git status --short` (section 2). Non vérifiés ici. |
| Autres secrets GitHub, rulesets, wiki | **Non vérifié.** `gh secret list` sur l'archive, et un coup d'œil au wiki, avant d'archiver. |
| Ancienne valeur de clé dans `.env.example` | **DÉCISION PROPRIÉTAIRE**, non bloquante pour le filtre. Le fichier (retiré le 28 août 2026) n'est recopié dans aucun dépôt neuf. La valeur reste dans l'historique de l'archive. La faire tourner, si elle a servi, est un geste à part : ce plan n'affiche pas la valeur et ne la renouvelle pas. |
| Arrêter nginx et systemd NAVIGUIDE sur l'OVH après le vert | **DÉCISION PROPRIÉTAIRE.** Pas de commande d'arrêt définitif dans ce plan. Les arrêts des sections 1 et 8 sont suivis d'un `systemctl start`. Les fichiers OVH restent jusqu'à un accord explicite, et après : les supprimer n'est pas une étape écrite ici. |
| Mettre le stock `official-store/` dans Mongo | **DÉCISION PROPRIÉTAIRE.** Aujourd'hui `SIMULATOR_MONGO_URL` est absent et la base n'existe pas. Ce plan copie les fichiers. Y passer demanderait un autre plan, après la copie disque vérifiée. |
| Pytest backend dans la CI Blue Intelligence | Reporté au commit d'après le tri hermétique. Pas un bloquant du 27 octobre. |
| Profil « lots de nuit » pour Blue Intelligence | Plus tard. `run_lots.py` n'est pas dans ce dépôt au moment du filtre. La section 6.5 prépare le fichier de réglages qui rend la copie possible. Les quatre scripts GitHub génériques y sont déjà. |

Tranché dans ce plan, pour qu'un exécutant n'ait pas à choisir en cours
de route : découpage de `infra/`, `docs/`, `.cursor/`, `Archives/`,
`.github/` ; les 132 documents de la PR #553, fichier par fichier
(section 4.9), sans les déplacer ; les 12 communs copiés en entier
puis raccourcis au premier commit (section 6.0) ; les deux doublons
nova absents des deux dépôts neufs et encore présents dans le
monodépôt, dossier `Archives/naviguide-nova/` non modifié ; le produit
public sur `naviguide.fr` avec
`301` depuis `www` et `simulator` ; l'ancien planificateur sous
`Archives/naviguide-planificateur/` après le filtre ; dossiers purs
en une ligne `dossier/` et dossiers mixtes
en fichiers exacts ; historique des renommages (`backend/poe.py`,
`memory/PRD.md`, anciens `docs/` déplacés, dont
`docs/nvidia-llm-audit.md` vers NAVIGUIDE) ; `.env.example`,
`memory/test_credentials.md`, `.emergent/` et le `package-lock.json` de
la racine hors des deux dépôts neufs ; `.gitconfig` hors des deux
dépôts ; `.gitignore` et `.nvmrc` dans les deux ; cache nginx
climatologie dans les deux ;
`infra/agents/` dans NAVIGUIDE avec les quatre scripts génériques aussi
dans Blue Intelligence ; push de `main` et des cinq tags, jamais
`--mirror` ; NAVIGUIDE sur Contabo (compte `naviguide`, Ubuntu 24.04,
ufw 22/80/443), Blue Intelligence et `blueintel_db` sur l'OVH (compte
`ubuntu`, dossier `~/blue-intelligence-map`) ; copie de fichiers du
simulateur, pas de transfert Mongo ; pas de suppression OVH sans accord
explicite.

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
| Section 1 en tête : sauvegarde des fichiers du simulateur et comptes de `blueintel_db`, avant le reste. Pas de dump d'une base simulateur. | Demande ; relevé OVH du 17 oct. 2026 |
| Le cron BI ne sauve que `blueintel_db`. On ne l'utilise pas pour NAVIGUIDE, et on n'écrit pas dans `~/backups/mongodb/`. | `blue-intelligence-backup.cron` ; relevé OVH |
| `SIMULATOR_MONGO_URL` est absent, l'utilisateur `naviguide_sim` n'existe pas, et `mongod` n'a que `admin`, `blueintel_db`, `config`, `local`. Le stock officiel est `official-store/` sur disque. Si l'un de ces faits a changé le jour J, stop. | Relevé OVH du 17 oct. 2026 ; `official_store.py` |
| Données présentes : `voyage_data/` (5,5 Go, dont `naviguide.sqlite` et `official-store/` 690 Mo), `polar_data/`, `grib_data/`, `saildocs_inbox/`, sous `~/blue-intelligence-map/naviguide-simulator/server/`. Absents : `forecast_cache/`, `/var/lib/naviguide`, `~/.cache/naviguide`. | Relevé OVH du 17 oct. 2026 |
| Copie cohérente : `systemctl stop`, `sqlite3 .backup` (`.dump` seulement si `.backup` échoue), `rsync` des quatre dossiers, SHA-256, comptes `pearls` / `kv` / `moments`, puis `systemctl start`. L'original n'est pas supprimé. | Demande du 17 oct. au soir ; `pearl_store.py` |
| Transport par `rsync` sur le port 22 vers `naviguide@` Contabo, ou par le Mac si l'OVH n'a pas la clé. Pas de tunnel Mongo. | Demande du 17 oct. au soir |
| NAVIGUIDE sur Contabo `13.140.164.185`, compte `naviguide`, Ubuntu 24.04, ufw 22/80/443, dossier `/home/naviguide/naviguide`. Blue Intelligence sur l'OVH, compte `ubuntu`, code dans `~/blue-intelligence-map`. Pas de Mongo sur Contabo. | Décision du 17 oct. ; relevé OVH et état Contabo du même jour |
| DNS : A `www` et `simulator` (et l'apex s'il pointe vers l'OVH) vers Contabo. `blueintelligence.online` reste sur Cloudflare / OVH. Certificat neuf sur Contabo, certificat OVH conservé. | `infra/vps/README.md` lignes 217–220 et 362 |
| `proxy_pass` de `/bi/` vers `127.0.0.1:8001` réécrit vers `https://blueintelligence.online` avec le bon en-tête `Host`. `BI_API_URL` de production aligné sur l'URL publique. | `nginx-simulator.conf`, `nginx-naviguide.conf` ; `simulator.env.example` ; Fusion B.4 ; Inventaire 4.3 |
| Le classeur remplace les `--path` de dossiers mixtes. 0 fichier non classé sur l'arbre lu. 0 écart d'historique. | Arbre ; Fusion B.5 ; Inventaire 4.1 et 4.2 |
| Les dossiers purs (`backend/`, `frontend/`, `naviguide-simulator/`, …) sont une ligne `dossier/`, pour garder les fichiers supprimés ou renommés. Les dossiers mixtes restent en fichiers exacts. | Aide de `git-filter-repo` 2.47.0 (`filename_matches` ne suit pas un renommage) ; `git log --diff-filter=R` |
| `backend/poe.py`, `memory/PRD.md`, le prototype (`app/`, `src/`, `prototype_ai_studio/`) et les anciens chemins `docs/` avant leur déplacement vers `docs/archives/` sont des lignes du filtre du bon dépôt. | `git log --diff-filter=R` sur `0ad99920` ; section 4.8 |
| `.env.example`, `memory/test_credentials.md`, `.emergent/` et le `package-lock.json` racine restent dans l'archive. `.env.example` contenait une valeur de clé : elle n'est pas recopiée, et la valeur n'est pas écrite ici. | `git log --diff-filter=D` ; lecture du blob sans l'afficher |
| `.github/`, `.gitignore`, `.nvmrc`, `.zap/` entrent dans le filtre. `.github/` est découpé : build hebdo côté Blue Intelligence, ZAP côté NAVIGUIDE, `ci.yml` / `deploy.yml` / `dependabot.yml` dans les deux puis adaptés. | Arbre ; Fusion B.5 ; Inventaire 4.1 ; Outillage §4 |
| `.gitconfig` (`emergent-agent-e1`) n'est copié dans aucun dépôt neuf. | Arbre ; Fusion B.5 |
| `.vscode/tasks.json` va dans NAVIGUIDE. | Arbre |
| `Archives/Blue-Intelligence/` va dans Blue Intelligence seulement. `Archives/naviguide-navsecops/` va dans NAVIGUIDE. `Archives/naviguide-nova/` y va en quatre fichiers ; les deux doublons markdown n'y vont pas. | Arbre ; #553 §10 ; Inventaire 4.2 |
| `docs/recette/`, plans simulateur, `LOTS_ORDRE_ET_PROMPTS.md`, `REGLES_WORKFLOW_AGENT.md` vont dans NAVIGUIDE. `docs/data/poe-*.json` et les CDC restent dans Blue Intelligence. `REGLES_PARAMETRES.md` va dans les deux. | Arbre ; `poe_gps_registry.py` ; Inventaire 4.2 ; Outillage §1 |
| `ici-tout.md`, les deux manuels et `ESPRIT_DE_L_APPLICATION.md` vont dans NAVIGUIDE, même là où l'index `docs/README.md` les range autrement. | Lecture de ces fichiers |
| `.cursor/environment.json`, `install.sh`, `start.sh`, `preview.sh` vont dans Blue Intelligence. Les hooks simulateur et les deux règles d'écran vont dans NAVIGUIDE. Les cinq règles communes vont dans les deux, original indiqué en 4.9. | `.cursor/environment.json` ; #553 §1 ; Inventaire 4.2 |
| `infra/agents/` va dans NAVIGUIDE. Quatre scripts GitHub vont aussi dans Blue Intelligence. `run_lots.py` n'y va pas. | Inventaire 4.2 et 4.7 ; Outillage §2 et lot O4 |
| Les scripts de `infra/vps/ci/` et les deux fichiers de cache nginx climatologie vont dans les deux dépôts. `infra/vps/ci/README.md` va dans Blue Intelligence seul. `infra/searxng/` et `infra/vps/seamap/` restent dans Blue Intelligence. | `deploy-simulator.sh` ; `rsync-to-vps.sh` ; #553 §7 ; Inventaire 4.3 |
| `git clone --bare --single-branch`, puis push de `refs/heads/main` et, pour Blue Intelligence, des cinq tags `data-*`. Pas de `--mirror`. | Fusion B.5 ; mesure du soir sur `6dabfb84` : 37 branches, 553 `refs/pull/*/head`, 11 `refs/pull/*/merge` |
| Les workflows de l'archive, cron compris, sont désactivés avant le renommage. `batch-pause.sh` est signalé absent. | `deploy.yml`, `weekly-data-build.yml`, `zap-baseline.yml` ; Fusion B.1 point 5 ; Outillage §2.1 |
| Premier commit d'adaptation **avant** le premier push. Liste des fichiers à `blue-intelligence-map` et de `BIM_REPO`. | Fusion B.4 ; Outillage §4 et §5 ; grep sur l'arbre |
| Le défaut OVH de `prepare-ssh.sh` est retiré dans la copie NAVIGUIDE. | `prepare-ssh.sh` lignes 11 et 31 |
| Exclusions `rsync` à ajouter pour `grib_data`, `forecast_cache`, `saildocs_inbox`. Les données vivent dans `/home/naviguide/naviguide-data/`. `polar_api.py` de la copie NAVIGUIDE lit `NAVIGUIDE_POLAR_DIR`. `forecast_cache/` n'est pas migré : il était absent. | `rsync-to-vps.sh` lignes 77–84 ; `polar_api.py` ; relevé OVH |
| Les unités systemd NAVIGUIDE passent de `User=ubuntu` et `/home/ubuntu/...` à `User=naviguide` et `/home/naviguide/naviguide`. | `naviguide-simulator.service` ; état Contabo du 17 oct. |
| Contrôle final : SHA-256 et comptes SQLite, `blueintel_db` toujours sur l'OVH, rien à l'écoute sur 27017 chez Contabo. Pas d'égalité de collections `naviguide_simulator`. | Relevé OVH du 17 oct. ; demande du soir |
| Preuve GenAI : le `log` de `poe_pipeline.py` doit rester en août 2026 après le filtre. `backend/` est gardé en entier. | Arbre (`b4fae8c7`, `--follow` jusqu'au 26 août) ; Fusion B.8 |
| Balayage de motifs de secrets avant push, sans afficher les valeurs. gitleaks non vérifié. | Fusion B.8 |
| Issues #432 et #446 à transférer vers NAVIGUIDE. | `gh issue list` ; Fusion B.7 |
| Les 11 PR ouvertes au soir du 17 octobre restent sur l'archive (#541, #542, #543, #546, #547, #548, #549, #551, #553, #554, #555). #529, #530, #533, #534, #536, #540, #544, #545 et #550 sont sur `main`. Les PR fermées #146, #227, #510, #537, #552 n'y sont pas. `pr-archive/` n'est pas dans git. | `gh pr list` ; `git ls-remote` |
| Gros fichiers : max 17,9 Mo, pas de LFS dans la procédure. | `git cat-file` sur toutes les refs ; Fusion B.6 ; Inventaire 4.4 |
| Pytest backend reporté. Les cinq tags `data-*` ne vont pas dans NAVIGUIDE. Les assets de Release ne suivent pas le push. | Outillage §3.3 et §4.3 ; `git for-each-ref refs/tags` |
| Dix contrôles remplacent les huit de l'ancien §6. Le septième compare le SQLite et les SHA-256. Le quatrième attend un `301`, pas un second site. | Ancien §6 ; relevé OVH du 17 oct. ; décisions du 17 oct. au soir |
| `docs/PLAN_BATCH_2026-10-16.md` et `.cursor/rules/specs-suivent-l-interface.mdc` sont sur `main` (`7d1f8d14`, PR #545 fusionnée). Le classeur les envoie dans NAVIGUIDE. | Arbre `6dabfb84` ; `--emit ng` |
| Les 132 documents de la PR #553 suivent le classeur, chemin par chemin : 46 NAVIGUIDE, 35 Blue Intelligence, 12 les deux, 37 dans le dépôt nommé par la #553 en gardant leur chemin actuel, 2 doublons nova hors des dépôts neufs. 0 écart. Cette PR ne les déplace pas et ne fusionne pas la #553. | PR #553, `docs/MENAGE_DOCUMENTAIRE_PROPOSITION.md`, commit `9c6f6e0d` |
| `.cursor/rules/base-de-donnees-vps.mdc` va dans les deux. Original Blue Intelligence. La copie NAVIGUIDE dit que le simulateur n'a pas de Mongo. | #553 §1 et §11 ; relevé OVH du 17 oct. |
| `docs/ETAT_DES_LIEUX_DOCS.md` et `docs/PRD.md` restent dans Blue Intelligence, à leur chemin actuel. | #553 §3 et §11 |
| `docs/archives/nvidia-llm-audit.md` et l'ancien chemin `docs/nvidia-llm-audit.md` vont dans NAVIGUIDE. | #553 §4 |
| `infra/vps/ci/README.md` va dans Blue Intelligence seul. Les scripts de `infra/vps/ci/` restent dans les deux. | #553 §7 |
| `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` et `SETUP_NOVA_CREDITS.md` ne vont dans aucun dépôt neuf. Les copies navsecops vont dans NAVIGUIDE. Le dossier nova n'est pas réécrit. | #553 §10 et §12 ; correction du propriétaire, 17 oct. au soir |
| `.github/`, `.gitignore`, `.nvmrc`, `.zap/` restent au découpage des sections 4.1 et 4.7. Ils sont hors des 132. | #553 §11 ; arbre |
| Le produit public est NAVIGUIDE sur `https://naviguide.fr`. `www` et `simulator` répondent `301` vers cette adresse. Certificat Contabo pour les trois noms. L'apex n'est pas mis derrière Cloudflare. | Décisions du propriétaire, 17 oct. 2026 au soir ; `nginx-naviguide.conf` ; `nginx-simulator.conf` |
| L'ancien planificateur (`naviguide/`) est filtré vers NAVIGUIDE puis déplacé sous `Archives/naviguide-planificateur/` avant le premier push. Ses trois unités systemd ne sont pas installées. `naviguide.env` reste dans la sauvegarde. | Décisions du 17 oct. au soir ; `naviguide-api.service` |
| Chaque merge sur `main` déploie le site live. Le README ne dit plus « hors production ». La branche `recette` ne déploie plus le VPS. | Décisions du 17 oct. au soir ; `deploy.yml` ; `naviguide-simulator/README.md` |
| Le poste de recette passe de `recette.blueintelligence.online` à `recette.naviguide.fr` (tunnel Cloudflare du Mac, CNAME OVH vers `cfargotunnel.com`). | Décisions du 17 oct. au soir ; `GROK_BOT_ROUTINE.md` ; `vite.config.js` |
| `docs/WORKFLOW_INDUSTRIEL.md` reste vivant. Son calendrier devient la ligne `à dater par le propriétaire`. | Décisions du 17 oct. au soir ; #553 décision 8 |
| La suppression des deux doublons nova est annulée. Ils restent dans le monodépôt, exclus des deux fichiers de chemins. `Archives/naviguide-nova/` n'est ni vidé ni réécrit. | Correction du propriétaire, 17 oct. au soir ; retour au traitement du commit `7a859ed8`, sans le renvoi de README |
| #510 (`15e41b4e`) est copiée dans NAVIGUIDE : plan sous `docs/archives/`, lots RJ1/RJ2 ajoutés au fichier `LOTS` vivant. #227 (`bef9f0f3`) est copiée dans Blue Intelligence sous `docs/archives/verify-fiche-urls/`. Pas de cherry-pick : les SHA d'origine restent sur l'archive. Confirmé de nouveau le même soir. | Décisions du 17 oct. au soir ; `git diff-tree` de ces deux commits |
| Les 19 documents (d) encore à la racine de `docs/` sont déplacés vers `docs/archives/` dans le dépôt filtré, avant le premier push. Les reçus `redites` et `LOTS_ORDRE_ET_PROMPTS.md` restent à leur chemin. `FILM_DISCOURS` traverse le filtre à son chemin, puis la section 6.5 le déplace. | Décisions du 17 oct. au soir ; #553 §11 ; correction du même soir |
| Le discours du film est déplacé, après le filtre, vers `naviguide-simulator/server/tests/fixtures/FILM_DISCOURS_ETAT_2026-09-28.md`. Un renvoi reste dans `docs/`. Les 21 citations de `docs/LOTS_ORDRE_ET_PROMPTS.md`, le plan film, le commentaire du test et les deux commentaires de `film_script.py` suivent le nouveau chemin. Le test ne lit pas le fichier (`REVUE_28_SEPT` est une constante). | Correction du propriétaire, 17 oct. au soir ; `test_film_discours.py` ligne 35 ; `film_script.py` lignes 102 et 5050 |
| Les chemins en dur de la boucle (`FIXED_DOCS`, `PROMPTS_MD`, `DEFAULT_REPO`, `PROD_URL`, arbre `naviguide-simulator/`, `docs/recette/`, documents Devpost, et la liste de la section 6.5.2) passent dans `infra/agents/repo_paths.py`. Les fichiers d'exécution (`state.json`, `queue.md`, `COUTS.md`, …) restent à côté des scripts. | Correction du propriétaire, 17 oct. au soir ; lecture de `infra/agents/*.py` |
| Ces deux travaux se font en deux commits dans la copie filtrée NAVIGUIDE, après la section 6 et avant le premier push. Une PR préparatoire sur le monodépôt est décrite, puis écartée : elle demanderait une fusion avant le filtre et une réécriture du classeur. | Correction du propriétaire, 17 oct. au soir |
| La phrase « swell not shipped » reste. La vérifier à l'écran après la bascule, avant de la retirer. | Décisions du 17 oct. au soir ; bandeau de `docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` |
| La répétition #555, sur `main` `6dabfb84`, s'arrêtait : deux fichiers de la #545 non classés, workflows recopiés tels quels, `recetteAg.test.js` lit `frontend/`, `test_naviguide_query_not_painted` importe `climatology_query`, décompte 550 / 16 / 42. | `docs/REPETITION_SPLIT_RAPPORT.md`, commit `f5c26ed6` |
| Le classeur envoie les deux fichiers de la #545 dans NAVIGUIDE. `--emit` sur `6dabfb84` (script copié, non suivi) : 1 853 suivis, 574 / 1 241 / 35 / 3, 0 non classé, 0 écart, 91 et 116 lignes. Self-test : 64 cas. | `scripts/check_split_coverage.py` ; sortie du 17 oct. au soir |
| `ci.yml`, `deploy.yml`, `dependabot.yml` et `prepare-ssh.sh` ont un diff exact par dépôt (section 6.6), appliqué tel quel après le filtre. `plan_deploy.py` et `test_prod_jobs_busy.py` ne sont pas réécrits : 31 tests verts. | `git apply --check` sur `6dabfb84` |
| Le commit NAVIGUIDE 6.7 copie `cycloneTracks.js` et `useClimatologyLayer.js` dans le simulateur. Les quatre assertions de `recetteAg.test.js` restent. `node --test` : 8 tests, 0 échec. | Lecture du test, lignes 96–99 ; exécution du 17 oct. au soir |
| Le commit Blue Intelligence 6.8 retire `test_naviguide_query_not_painted`. Le commit NAVIGUIDE le place à côté de `climatology_query.py`, assertions gardées. `test_serper_google_style_merged` échoue déjà sur le monodépôt : on n'y touche pas. | `backend/tests/test_climatology.py` ; `test_poe_v2_pipeline.py` ligne 1045 ; consigne du propriétaire |

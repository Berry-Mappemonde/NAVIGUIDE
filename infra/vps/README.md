# OVH VPS deployment — blueintelligence.online

Self-hosted production on the OVH VPS `vps-52ba6d62.vps.ovh.net` (135.125.226.16,
Ubuntu, 4 vCores / 8 GB / 75 GB): **local MongoDB 8.0 Community** (end of
Atlas M0 throttling), FastAPI backend + React frontend served by **uvicorn**
behind the server **nginx**, domain behind **Cloudflare**.

```
Internet → Cloudflare → nginx (443, Let's Encrypt certificate)
                          └→ uvicorn 127.0.0.1:8001 (SERVE_FRONTEND=1: UI + /api/*)
                               └→ MongoDB 8.0 (127.0.0.1:27017, authentication enabled)
```

## Locations on the VPS

| What | Where |
|------|-------|
| Application code | `~/blue-intelligence-map/` |
| Local MongoDB secrets (`admin` and `blue` accounts) | `~/.config/blue-intelligence/mongo.env` (chmod 600) |
| Atlas connection string (for resync) | `~/.config/blue-intelligence/atlas.env` (chmod 600) |
| Application API keys | `~/blue-intelligence-map/backend/.env` (chmod 600) |
| Daily backups (04:00, 14-day rotation) | `~/backups/mongodb/` + `/etc/cron.d/blue-intelligence-backup` |
| Application service | `/etc/systemd/system/blue-intelligence.service` |
| Reverse proxy | `/etc/nginx/sites-available/blue-intelligence` (TLS managed by certbot) |

## First install (already done on 2026-09-09)

```bash
# 1. Secured MongoDB 8 (idempotent — creates accounts on the first pass)
bash infra/vps/install-mongodb.sh

# 2. Data from Atlas (OVERWRITES the local database)
bash infra/vps/sync-from-atlas.sh

# 3. Application (Python 3.12 venv via uv, frontend build, systemd, cron)
bash infra/vps/deploy-app.sh
```

The nginx `proxy_pass` must target `127.0.0.1:8001` (see
`nginx-blue-intelligence.conf`, reference copy).

## VPS memory (8 GB, no slack)

The VPS has **no swap** by default. NAVIGUIDE used to preload worldwide EEZs
in RAM (~3.5 GB) and an `npm run build` / `uv pip` would saturate the machine.

Once, outside a Full run:

```bash
bash infra/vps/setup-memory.sh
# 4 GB swap + swappiness 10 + capped Mongo cache (restart mongod later)
sudo cp infra/vps/blue-intelligence.service /etc/systemd/system/
sudo cp infra/vps/naviguide/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart naviguide-api   # frees the EEZ cache; Blue Intelligence unchanged
```

systemd `MemoryMax`: 3 GB (Blue Intelligence), 1 GB (naviguide-api), 512 MB
(orchestrator / polar). A Full Projects run does not need NAVIGUIDE.

## Redeploy after a code update

```bash
cd ~/blue-intelligence-map
# code up to date (rsync from a workstation, or git pull if a remote is configured).
# After an rsync -a from a 700 workspace: chmod o+x ~/blue-intelligence-map
# (NAVIGUIDE nginx reads /var/www/naviguide, but other tools may still
# walk the repository).
bash infra/vps/deploy-app.sh
```

With little free RAM: first `bash infra/vps/setup-memory.sh`, then rsync
the code and `sudo systemctl restart blue-intelligence` (without `npm`/`uv` if
dependencies have not changed). Do not run `deploy-app.sh` during a
Full run — it restarts the service.

## Resync data from Atlas — ⛔ NEVER DO THIS AGAIN

**Since the DNS cutover of 2026-09-10, the VPS is the live database.** Atlas is
frozen at its pre-cutover state: rerunning `sync-from-atlas.sh` would overwrite
recent data (new runs, enrichments, review…) with that stale
state. The script now has a lock and refuses to run;
there is no longer a legitimate reason to force it, except disaster recovery
decided with full knowledge of the data loss (`FORCE_RESYNC=oui-ecraser-la-base`).

If you need a restore, use the **daily local
backups** (see Backups), never Atlas.

## Backups

- Automatic: daily cron at 04:00, `blue-YYYY-MM-DD.archive.gz` archives,
  14-day rotation. Remember to copy an archive **off the VPS** regularly.
- Restore an archive:

```bash
. ~/.config/blue-intelligence/mongo.env
mongorestore --uri "$MONGO_URL_LOCAL" --gzip \
  --archive=$HOME/backups/mongodb/blue-YYYY-MM-DD.archive.gz --drop
```

## Cloudflare cutover (done on 2026-09-10)

The domain (OVH registrar) pointed at the old platform's Cloudflare;
it was brought back into the owner's Cloudflare account:

1. Cloudflare → **Connect a domain** → `blueintelligence.online`, Free plan.
   Zone imported from OVH then fixed: **A `@` → 135.125.226.16**
   (proxied), CNAME `www` → apex (proxied), MX/TXT kept as-is.
2. OVH (manager → Web Cloud → Domain names → DNS servers tab):
   servers replaced with `coby.ns.cloudflare.com` / `eve.ns.cloudflare.com`.
   **DNSSEC disabled** beforehand (required); transfer protection left
   enabled.
3. “Universal SSL” edge certificate issued on activation; SSL/TLS in
   **Full (strict)** mode (the VPS Let's Encrypt certificate covers apex + www).
4. Verified: `https://blueintelligence.online/api/` → `"mongo": "local"`,
   HTTP 200 via the Cloudflare edge, admin gate 401/200, 15 MB marinas in ~3 s.
5. Rollback: at OVH, restore the `ns14.ovh.net` /
   `dns14.ovh.net` servers (the original OVH zone, intact, becomes authoritative again and
   re-points at the old platform).

After cutover, check certificate renewal: `sudo certbot renew
--dry-run` (the HTTP challenge goes through Cloudflare; if “Always Use HTTPS”
blocks `/.well-known/acme-challenge/`, create an exception or use a
Cloudflare Origin certificate).

## Admin access (Console / Review)

The Console and Review tabs, plus every API write
(`POST/PUT/PATCH/DELETE /api/*`, except the public project report) are
protected by an admin key:

- The key lives in `~/blue-intelligence-map/backend/.env` on the VPS
  (`ADMIN_KEY=...`). Without this variable (local dev), everything stays open.
- To unlock the UI: open once
  `https://blueintelligence.online/?admin=<key>`. The key is stored in the
  browser (localStorage) and then sent via the `X-Admin-Key` header.
- To lock a browser: `https://blueintelligence.online/?admin=off`.
- To regenerate the key: `openssl rand -hex 24`, replace the value in
  `backend/.env`, then `sudo systemctl restart blue-intelligence` (old
  admin browsers will need to enter the new key).

## Security / access

- MongoDB listens only on 127.0.0.1, authentication required — never
  exposed on the Internet, no port to open.
- Revoke Cursor agent access: delete the
  `cursor-agent-blue-intelligence` line from `~/.ssh/authorized_keys` on the VPS.
- Application logs: `sudo journalctl -u blue-intelligence -f`;
  MongoDB: `/var/log/mongodb/mongod.log`.

## NAVIGUIDE — www.naviguide.fr (same VPS)

NAVIGUIDE (`naviguide/` of the monorepo) is published on the same VPS, under the
**www.naviguide.fr** domain (A DNS → 135.125.226.16, no Cloudflare).
See `infra/vps/naviguide/`.

```
Internet → nginx (443, Let's Encrypt)
   www.naviguide.fr        → /var/www/naviguide (copy of naviguide-app/dist/)
   /route /wind /wave …    → uvicorn 127.0.0.1:9000  (naviguide-api)
   /api/v1/polar/*         → uvicorn 127.0.0.1:9004  (polar-api)
   /api/v1/*               → uvicorn 127.0.0.1:9008  (LangGraph orchestrator)
   /bi/*                   → uvicorn 127.0.0.1:8001  (Blue Intelligence /api/*)
```

| What | Where |
|------|-------|
| Code | `~/blue-intelligence-map/naviguide/` (shared `.venv/`) |
| Frontend served by nginx | `/var/www/naviguide` (not the repo `dist/`) |
| Secrets (NVIDIA/OpenRouter/Anthropic LLM cascade, Copernicus, StormGlass) | `~/.config/naviguide/naviguide.env` (chmod 600) |
| Services | `naviguide-api`, `naviguide-orchestrator`, `naviguide-polar` (systemd) |
| Reverse proxy | `/etc/nginx/sites-available/naviguide` (certbot TLS) |

```bash
# (Re)deploy — frontend build + venv + systemd + nginx
bash infra/vps/naviguide/deploy-naviguide.sh
# First deploy only: fill in secrets then restart
vim ~/.config/naviguide/naviguide.env && sudo systemctl restart naviguide-api naviguide-orchestrator naviguide-polar
```

TLS: the Let's Encrypt `live/naviguide.fr` certificate (SAN naviguide.fr +
www.naviguide.fr) already existed on the VPS and is reused as-is by
`nginx-naviguide.conf` (certbot renewal unchanged). The old nginx site
`default` (placeholder `/var/www/html` + proxies to dead ports 8000/8001/3008)
was removed from `sites-enabled` on 2026-09-10 — backup in
`sites-available/default`. The frontend is copied to `/var/www/naviguide`
(readable by `www-data`): an `rsync -a` or `chmod 700` of the repo must no longer
take the site down (incident of 2026-09-13: nginx 500 / `try_files` loop
because `~/blue-intelligence-map` was `drwx------`).

NAVIGUIDE map “Blue Intelligence” layers consume the local Blue Intelligence
GeoJSON exports via the nginx `/bi/*` route — no
CORS, no external network call. Logs: `sudo journalctl -u naviguide-api -f`
(same for `-orchestrator`, `-polar`). Ports 9000/9004/9008 reserved for NAVIGUIDE
(8001 = Blue Intelligence). `naviguide-weather-routing` (3010) is not
deployed: the frontend does not call it.

## NAVIGUIDE simulator — simulator.naviguide.fr (same VPS)

**Separate** subdomain: the skipper site `www.naviguide.fr` and its APIs
(`:9000` / `:9004` with chat / `:9008`) are not reused.

```
Internet → nginx (443, Let's Encrypt, SAN + simulator.naviguide.fr)
   simulator.naviguide.fr  → /var/www/naviguide-simulator
   /route /wind /wave …    → uvicorn 127.0.0.1:8010  (naviguide-simulator)
   /api/v1/*               → the same :8010 (polar without chat)
   /bi/*                   → uvicorn 127.0.0.1:8001  (Blue Intelligence, read-only)
```

| What | Where |
|------|-------|
| Code | `~/blue-intelligence-map/naviguide-simulator/` (dedicated `.venv/`) |
| nginx frontend | `/var/www/naviguide-simulator` |
| Optional secrets (Copernicus only) | `~/.config/naviguide/simulator.env` |
| Service | `naviguide-simulator` (systemd, `MemoryMax=1G`) |
| Reverse proxy | `/etc/nginx/sites-available/naviguide-simulator` |

DNS: **A** record `simulator` → `135.125.226.16` (`naviguide.fr` zone,
free). First deploy from a machine with Node + SSH (local Vite
build, no `npm` on the VPS):

```bash
cd /path/to/Blue-Intelligence-Map
bash infra/vps/naviguide/publish-simulator-from-mac.sh
```

The script extends the existing certificate (`certbot --expand`, free) if it
does not yet contain `simulator.naviguide.fr`. It does not rewrite
`sites-available/naviguide` and does not restart skipper / BI services.

nginx rollback (www becomes the only NAVIGUIDE vhost again):

```bash
ssh ubuntu@135.125.226.16
sudo rm -f /etc/nginx/sites-enabled/naviguide-simulator
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl disable --now naviguide-simulator
```

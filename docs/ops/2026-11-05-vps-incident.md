# VPS incident 2026-11-05 (Contabo NAVIGUIDE)

## Cause

1. **nginx down (2026-11-04 ~01:41 Toronto):** an unattended upgrade restarted nginx. Configuration referenced `proxy_pass https://blueintelligence.online/...` with a hostname resolved at config load time. DNS for `blueintelligence.online` failed briefly, so `nginx -t` / service start failed with `host not found in upstream "blueintelligence.online"` (notably in `naviguide-http-bootstrap`, line ~138). `naviguide.fr` stayed offline until 2026-11-05.
2. **OOM kills:** on an 11 GB RAM host with no swap, `naviguide-simulator` (`MemoryMax=4G`, cgroup shared with `prepare_official_store.py`) and `naviguide-film-front` (`MemoryMax=512M`) were repeatedly OOM-killed under load.

## Changes codified in the repo

- **systemd:** drop-ins `naviguide-simulator.service.d/memory.conf` (`MemoryMax=6G`) and `naviguide-film-front.service.d/memory.conf` (`MemoryMax=1G`), installed by `deploy-simulator.sh` (base units unchanged at 4G / 512M).
- **swap:** idempotent 4G `/swapfile` + `/etc/fstab` entry in `deploy-simulator.sh`.
- **nginx:** `resolver` + `$bi_host` in `proxy_pass` for Blue Intelligence upstreams in `nginx-simulator.conf` and `nginx-http-bootstrap.conf` so nginx starts even if DNS is unavailable at reload time.
- **bootstrap vhost:** `nginx-http-bootstrap.conf` versioned and deployed to `sites-available/naviguide-http-bootstrap`.

## Rollback (on the VPS)

1. Remove memory drop-ins and reload systemd:
   - `sudo rm -f /etc/systemd/system/naviguide-simulator.service.d/memory.conf`
   - `sudo rm -f /etc/systemd/system/naviguide-film-front.service.d/memory.conf`
   - `sudo systemctl daemon-reload && sudo systemctl restart naviguide-simulator naviguide-film-front`
2. Disable swap (optional): `sudo swapoff /swapfile`, remove the `/swapfile` line from `/etc/fstab`, `sudo rm -f /swapfile`.
3. Restore nginx/systemd backups from the live fix if present: files named `*.bak-20261105` (or redeploy the previous git revision).

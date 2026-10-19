#!/usr/bin/env bash
# Deploy the NAVIGUIDE simulator on simulator.naviguide.fr (same VPS).
# Does NOT restart blue-intelligence, naviguide-api, polar, orchestrator.
# Does NOT touch /etc/nginx/sites-available/naviguide.
#
# Prerequisites: code in /home/naviguide/naviguide/naviguide-simulator
# (rsync from the Mac — see publish-simulator-from-mac.sh).
# DNS : naviguide.fr, www et simulator pointent encore vers l'OVH
# (135.125.226.16). La bascule vers Contabo (13.140.164.185) est écrite
# plus bas et n'est pas appliquée : le geste DNS reste à Clément.
# Run on the VPS, outside a Blue Intelligence Full run if dist/ is missing
# (npm would then run here).
set -euo pipefail

APP="/home/naviguide/naviguide"
SIM="$APP/naviguide-simulator"
CONF_DIR="$HOME/.config/naviguide"
UV="$HOME/.local/bin/uv"
WWW_ROOT=/var/www/naviguide-simulator
NGINX_SRC="$APP/infra/vps/naviguide/nginx-simulator.conf"
UNIT_SRC="$APP/infra/vps/naviguide/naviguide-simulator.service"

if [ ! -d "$SIM/server" ]; then
  echo "Dossier $SIM/server introuvable. Rsync d'abord depuis le Mac." >&2
  exit 1
fi
require_file() {
  local path="$1"
  local label="$2"
  if [ ! -f "$path" ]; then
    echo "ERREUR déploiement simulateur : $label introuvable." >&2
    echo "  Attendu dans le dépôt rsyncé : $path" >&2
    echo "  (PR #549 : film-front + nginx ; le workflow rsync doit copier infra/vps/naviguide/naviguide-film-front.service)" >&2
    exit 1
  fi
}

require_file "$NGINX_SRC" "nginx-simulator.conf"
require_file "$UNIT_SRC" "naviguide-simulator.service"
require_file "$APP/infra/vps/naviguide/nginx-simulator-limits.conf" "nginx-simulator-limits.conf"
require_file "$APP/infra/vps/naviguide/nginx-simulator-443-redirects.conf" "nginx-simulator-443-redirects.conf"

FILM_UNIT="$APP/infra/vps/naviguide/naviguide-film-front.service"
FILM_PY="$SIM/server/film_front.py"

SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
SKIP_PIP="${SKIP_PIP:-0}"

command -v "$UV" >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

# ── Dedicated venv (not the naviguide/ one) ─────────────────────────────────────
cd "$SIM"
[ -d .venv ] || "$UV" venv --python 3.12 .venv
if [ "$SKIP_PIP" = "1" ] && [ -x .venv/bin/python ]; then
  echo "SKIP_PIP=1 — venv simulateur inchangé"
else
  "$UV" pip install --python .venv/bin/python -r server/requirements.txt
fi

mkdir -p "$CONF_DIR"
if [ ! -f "$CONF_DIR/simulator.env" ]; then
  umask 077
  cp "$APP/infra/vps/naviguide/simulator.env.example" "$CONF_DIR/simulator.env"
  # Copernicus only — never the naviguide.env file (LLM keys).
  if [ -f "$CONF_DIR/naviguide.env" ]; then
    grep -E '^COPERNICUS_(USERNAME|PASSWORD)=' "$CONF_DIR/naviguide.env" \
      >> "$CONF_DIR/simulator.env" || true
  fi
  echo "⚠  $CONF_DIR/simulator.env créé (Copernicus optionnel, sans clés LLM)"
fi
chmod 600 "$CONF_DIR/simulator.env"

# ── Sécurité P0 : secret admin partagé (X-Naviguide-Admin) ──────────────────
# Sans lui, derrière nginx, les écritures officielles répondent 503 : on en
# génère un à la première passe. Le lire : grep NAVIGUIDE_ADMIN_SECRET "$CONF_DIR/simulator.env"
if ! grep -qE '^NAVIGUIDE_ADMIN_SECRET=.+' "$CONF_DIR/simulator.env"; then
  ADMIN_SECRET="$(openssl rand -hex 32)"
  printf '\n# généré par deploy-simulator.sh le %s\nNAVIGUIDE_ADMIN_SECRET=%s\n' "$(date -u +%F)" "$ADMIN_SECRET" \
    >> "$CONF_DIR/simulator.env"
  echo "🔐 NAVIGUIDE_ADMIN_SECRET généré dans $CONF_DIR/simulator.env"
  echo "   Sur ton Mac : ouvre https://simulator.naviguide.fr/?admin=<la clé> une fois."
fi

# ── Blue Intelligence : sans BI_API_URL, aucun appel BI (pas de défaut dans le code)
if ! grep -qE '^BI_API_URL=.+' "$CONF_DIR/simulator.env"; then
  echo "⚠  BI_API_URL absente de $CONF_DIR/simulator.env : Blue Intelligence désactivée." >&2
  echo "   Voir infra/vps/naviguide/simulator.env.example." >&2
fi

# ── Frontend: dist/ already built on the Mac / GitHub preferably ───────────
if [ "$SKIP_FRONTEND_BUILD" = "1" ]; then
  if [ ! -f "$SIM/dist/index.html" ]; then
    echo "SKIP_FRONTEND_BUILD=1 but $SIM/dist/index.html is missing." >&2
    exit 1
  fi
  echo "SKIP_FRONTEND_BUILD=1 — reusing the GitHub / Mac bundle"
elif [ ! -f "$SIM/dist/index.html" ]; then
  echo "dist/ absent — npm run build sur le VPS (RAM : pas pendant un Complet)"
  cd "$SIM"
  npm install --no-audit --no-fund
  npm run build
fi

sudo mkdir -p "$WWW_ROOT"
# robots.txt, sitemap.xml et la clé IndexNow viennent de public/ (versionnés) ;
# le filtre P les protège en plus de --delete si un bundle les omettait.
sudo rsync -a --delete \
  --filter='P /robots.txt' \
  --filter='P /sitemap.xml' \
  --filter='P /27424ae0389d9d7fb74e3ad6db0e9780.txt' \
  "$SIM/dist/" "$WWW_ROOT/"
# Contabo : compte naviguide (plus de compte ubuntu côté NAVIGUIDE).
sudo chown -R "$(id -un):$(id -gn)" "$WWW_ROOT"
sudo chmod -R a+rX "$WWW_ROOT"

# ── systemd : naviguide-simulator (+ film-front si le code est sur disque) ───
# #546 : retirer l'ancien drop-in MemoryHigh=3500M (l'unité du dépôt n'en impose pas).
ZZ_MEM_DROPIN=/etc/systemd/system/naviguide-simulator.service.d/zz-memory.conf
if [ -f "$ZZ_MEM_DROPIN" ]; then
  echo "→ Suppression du drop-in hérité $ZZ_MEM_DROPIN (#546)"
  sudo rm -f "$ZZ_MEM_DROPIN"
  if [ -d /etc/systemd/system/naviguide-simulator.service.d ] \
      && [ -z "$(ls -A /etc/systemd/system/naviguide-simulator.service.d 2>/dev/null)" ]; then
    sudo rmdir /etc/systemd/system/naviguide-simulator.service.d 2>/dev/null || true
  fi
fi

sudo cp "$UNIT_SRC" /etc/systemd/system/naviguide-simulator.service

film_deploy_ok=0
have_film_unit=0
have_film_py=0
[ -f "$FILM_UNIT" ] && have_film_unit=1
[ -f "$FILM_PY" ] && have_film_py=1
if [ "$have_film_unit" -eq 1 ] && [ "$have_film_py" -eq 1 ]; then
  film_deploy_ok=1
elif [ "$have_film_unit" -eq 1 ] || [ "$have_film_py" -eq 1 ]; then
  echo "ERREUR déploiement simulateur : film-front incomplet sur le VPS." >&2
  [ "$have_film_unit" -eq 0 ] && echo "  manquant : $FILM_UNIT" >&2
  [ "$have_film_py" -eq 0 ] && echo "  manquant : $FILM_PY" >&2
  echo "  Le rsync GitHub doit envoyer infra/vps/naviguide/naviguide-film-front.service et naviguide-simulator/server/film_front.py." >&2
  exit 1
else
  echo "⚠  film-front absent du dépôt rsyncé — naviguide-film-front n'est pas (re)configuré." >&2
  if systemctl is-active --quiet naviguide-film-front 2>/dev/null; then
    echo "    processus existant sur :8011 conservé (pas de restart)." >&2
  fi
fi

if [ "$film_deploy_ok" -eq 1 ]; then
  sudo cp "$FILM_UNIT" /etc/systemd/system/naviguide-film-front.service
fi

sudo systemctl daemon-reload
sudo systemctl enable naviguide-simulator >/dev/null 2>&1 || true

sim_was_active=0
if systemctl is-active --quiet naviguide-simulator 2>/dev/null; then
  sim_was_active=1
fi
if ! sudo systemctl restart naviguide-simulator; then
  echo "ERREUR : naviguide-simulator n'a pas redémarré." >&2
  exit 1
fi

if [ "$film_deploy_ok" -eq 1 ]; then
  sudo systemctl enable naviguide-film-front >/dev/null 2>&1 || true
  if ! sudo systemctl restart naviguide-film-front; then
    echo "ERREUR : naviguide-film-front n'a pas redémarré alors que le code est présent." >&2
    if [ "$sim_was_active" -eq 1 ]; then
      echo "  naviguide-simulator a été redémarré ; vérifiez :8011 et nginx film/clock." >&2
    fi
    exit 1
  fi
fi

# ── nginx: cache climatologie BI partagé (zone + snippet inclus par le vhost) ─
# Idempotent. Le vhost blue-intelligence (certbot) et naviguide (installé une
# fois) incluent le même snippet : voir infra/vps/nginx-*.conf.
sudo install -d -o www-data -g www-data -m 750 /var/cache/nginx/bi-climatology
sudo install -m 644 "$APP/infra/vps/nginx-bi-climatology-cache.conf" \
  /etc/nginx/conf.d/bi-climatology-cache.conf
sudo install -m 644 "$APP/infra/vps/nginx-snippet-bi-climatology.conf" \
  /etc/nginx/snippets/bi-climatology-cache.conf

# ── nginx: separate file, sites-available/naviguide untouched ───────────────
if [ -f /etc/nginx/sites-available/naviguide ]; then
  sudo cp -a /etc/nginx/sites-available/naviguide \
    "/etc/nginx/sites-available/naviguide.bak-before-simulator-$(date +%Y%m%d)"
fi
CERT=/etc/letsencrypt/live/naviguide.fr/fullchain.pem
HAVE_CERT=0
sudo test -f "$CERT" && HAVE_CERT=1
# BEGIN nginx-sites
# Zones de débit (conf.d), vhost 443 et redirections 443 de www/simulator
# sont posés dans le même passage, puis nginx -t. En cas d'échec, tout revient
# à l'état sauvegardé et nginx n'est pas rechargé.
# Les zones sim_write/sim_story ne doivent être déclarées qu'une fois : si un
# autre site actif (ancien bootstrap HTTP) les déclare encore, on n'installe
# pas le fichier conf.d.
NGINX_ETC="${NGINX_ETC:-/etc/nginx}"
LIMITS_SRC="${LIMITS_SRC:-${APP:-/home/naviguide/naviguide}/infra/vps/naviguide/nginx-simulator-limits.conf}"
REDIRECTS_SRC="${REDIRECTS_SRC:-${APP:-/home/naviguide/naviguide}/infra/vps/naviguide/nginx-simulator-443-redirects.conf}"
LIMITS_DST="$NGINX_ETC/conf.d/naviguide-simulator-limits.conf"
SIM_AVAIL="$NGINX_ETC/sites-available/naviguide-simulator"
SIM_ENABLED="$NGINX_ETC/sites-enabled/naviguide-simulator"
REDIR_AVAIL="$NGINX_ETC/sites-available/naviguide-443-redirects"
REDIR_ENABLED="$NGINX_ETC/sites-enabled/naviguide-443-redirects"
NGINX_BAK="$NGINX_ETC/naviguide-deploy-bak/$(date -u +%Y%m%dT%H%M%SZ)"

sudo mkdir -p "$NGINX_BAK"
for f in "$LIMITS_DST" "$SIM_AVAIL" "$REDIR_AVAIL"; do
  if sudo test -f "$f"; then sudo cp -a "$f" "$NGINX_BAK/"; fi
done
SIM_WAS_ENABLED=0
[ -L "$SIM_ENABLED" ] && SIM_WAS_ENABLED=1
REDIR_WAS_ENABLED=0
[ -L "$REDIR_ENABLED" ] && REDIR_WAS_ENABLED=1

nginx_restore_file() {
  local dst="$1" bak
  bak="$NGINX_BAK/$(basename "$dst")"
  if sudo test -f "$bak"; then
    sudo cp -a "$bak" "$dst"
  else
    sudo rm -f "$dst"
  fi
}
nginx_restore_link() {
  local was="$1" avail="$2" enabled="$3"
  if [ "$was" -eq 1 ]; then
    sudo ln -sf "$avail" "$enabled"
  else
    sudo rm -f "$enabled"
  fi
}
nginx_restore() {
  echo "ERREUR : nginx -t a échoué. Retour à la configuration sauvegardée ($NGINX_BAK)." >&2
  nginx_restore_file "$LIMITS_DST"
  nginx_restore_file "$SIM_AVAIL"
  nginx_restore_file "$REDIR_AVAIL"
  nginx_restore_link "$SIM_WAS_ENABLED" "$SIM_AVAIL" "$SIM_ENABLED"
  nginx_restore_link "$REDIR_WAS_ENABLED" "$REDIR_AVAIL" "$REDIR_ENABLED"
}

# Sites actifs (hors fichiers posés ici) qui déclarent encore les zones.
sim_zones_elsewhere() {
  local f
  for f in "$NGINX_ETC"/conf.d/*.conf "$NGINX_ETC"/sites-enabled/*; do
    [ -e "$f" ] || continue
    [ "$f" = "$LIMITS_DST" ] && continue
    [ "$f" = "$SIM_ENABLED" ] && [ -L "$f" ] && continue
    if grep -qsE '^[[:space:]]*limit_req_zone[^#]*zone=sim_(write|story):' "$f"; then
      echo "$f"
    fi
  done
}

sudo cp "$NGINX_SRC" "$SIM_AVAIL"
ZONES_ELSEWHERE="$(sim_zones_elsewhere)"
if [ -n "$ZONES_ELSEWHERE" ]; then
  echo "⚠  zones sim_write/sim_story déjà déclarées dans : $ZONES_ELSEWHERE" >&2
  echo "   $LIMITS_DST non installé (pas de doublon)." >&2
  sudo rm -f "$LIMITS_DST"
else
  sudo install -m 644 "$LIMITS_SRC" "$LIMITS_DST"
fi
sudo install -m 644 "$REDIRECTS_SRC" "$REDIR_AVAIL"
if [ "$HAVE_CERT" -eq 1 ]; then
  sudo ln -sf "$SIM_AVAIL" "$SIM_ENABLED"
  if [ -e "$NGINX_ETC/sites-enabled/naviguide" ]; then
    echo "  sites-enabled/naviguide actif : redirections 443 déjà servies, naviguide-443-redirects non activé."
  else
    sudo ln -sf "$REDIR_AVAIL" "$REDIR_ENABLED"
  fi
else
  # Avant la bascule DNS (Contabo) : pas de certificat. Le vhost 443 du dépôt
  # ferait échouer nginx -t ; on garde le bootstrap HTTP (naviguide-http-bootstrap).
  echo "⚠  $CERT absent : vhost 443 copié mais non activé (mode bootstrap HTTP)." >&2
fi
if ! sudo nginx -t; then
  nginx_restore
  sudo nginx -t || echo "ERREUR : nginx -t échoue encore après le retour arrière." >&2
  exit 1
fi
sudo systemctl reload nginx
# END nginx-sites

# ── TLS: add the SAN if missing (Let's Encrypt, free) ──────────────────
# nginx plugin (not webroot): the www vhost still redirects /.well-known
# to HTTPS. certonly does not write a new skipper vhost.
if [ "$HAVE_CERT" -eq 0 ]; then
  :  # certificat émis le jour J (plan §6.4), pas par ce script
elif ! sudo openssl x509 -in "$CERT" -noout -text | grep -q 'DNS:simulator.naviguide.fr'; then
  echo "Extension du certificat Let's Encrypt (naviguide.fr + www + simulator)…"
  sudo certbot certonly --nginx --cert-name naviguide.fr \
    -d naviguide.fr -d www.naviguide.fr -d simulator.naviguide.fr \
    --expand --non-interactive --agree-tos --no-eff-email
  sudo nginx -t
  sudo systemctl reload nginx
fi

# ── Health ────────────────────────────────────────────────────────────────────
code=000
for _ in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8010/" || true)
  [ "$code" = "200" ] && break
  sleep 1
done
echo "  naviguide-simulator (:8010) → HTTP $code"

film_code=000
for _ in $(seq 1 20); do
  film_code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8011/voyage/official/clock" || true)
  [ "$film_code" != "000" ] && break
  sleep 1
done
echo "  naviguide-film-front (:8011) → HTTP $film_code"

# BEGIN bascule-contabo
# Bascule préparée, non appliquée. Ce bloc n'ouvre aucune connexion.
# Accord explicite : NAVIGUIDE_APPLY_CONTABO_SWITCH=accord-clement
# Même alors, ce script ne change pas le DNS.
report_contabo_switch() {
  local agreement="${NAVIGUIDE_APPLY_CONTABO_SWITCH:-}"
  echo "Bascule préparée : naviguide.fr, www.naviguide.fr, simulator.naviguide.fr"
  echo "  A actuel (OVH) : 135.125.226.16"
  echo "  A préparé (Contabo) : 13.140.164.185"
  if [ "$agreement" != "accord-clement" ]; then
    echo "En attente de l'accord explicite de Clément. Aucun changement DNS."
    return 0
  fi
  echo "Accord lu. Le DNS n'est pas modifié par ce script : Clément change les trois A vers 13.140.164.185."
  return 0
}
# END bascule-contabo
report_contabo_switch

# BEGIN film-chapters
count_film_chapters() {
  printf '%s' "${1:-}" | python3 -c 'import json,sys
raw=sys.stdin.read()
try:
    body=json.loads(raw) if raw.strip() else {}
except Exception:
    print(0)
    raise SystemExit(0)
chapters=body.get("chapters") if isinstance(body, dict) else None
print(len(chapters) if isinstance(chapters, list) else 0)
'
}
FILM_READY_TRIES="${FILM_READY_TRIES:-20}"
FILM_READY_PAUSE="${FILM_READY_PAUSE:-1}"
film_chapters=0
for _ in $(seq 1 "$FILM_READY_TRIES"); do
  film_body="$(curl -fsS -m 15 "http://127.0.0.1:8011/voyage/official/film?lang=en&seconds=150" || true)"
  film_chapters="$(count_film_chapters "$film_body" || true)"
  film_chapters="${film_chapters//[^0-9]/}"
  film_chapters="${film_chapters:-0}"
  if [ "$film_chapters" -ge 1 ]; then
    break
  fi
  sleep "$FILM_READY_PAUSE"
done
if [ "${film_chapters:-0}" -lt 1 ]; then
  echo "ERREUR : GET /voyage/official/film?lang=en&seconds=150 n'a aucun chapitre. Déploiement arrêté." >&2
  exit 1
fi
echo "  film 150 s → ${film_chapters} chapitre(s)"
# END film-chapters

if [ "$HAVE_CERT" -eq 0 ]; then
  echo "  mode bootstrap : contrôles HTTPS publics sautés (le DNS pointe encore ailleurs)"
  exit 0
fi
www_code=$(curl -s -o /dev/null -w "%{http_code}" "https://www.naviguide.fr/" || true)
sim_code=$(curl -s -o /dev/null -w "%{http_code}" "https://simulator.naviguide.fr/" || true)
echo "  https://www.naviguide.fr/ → HTTP $www_code (doit rester 200)"
echo "  https://simulator.naviguide.fr/ → HTTP $sim_code"

if [ "$www_code" != "200" ] && [ "$www_code" != "301" ] && [ "$www_code" != "302" ]; then
  echo "⚠  www.naviguide.fr ne répond plus comme prévu. Retour arrière nginx :" >&2
  echo "    sudo rm -f /etc/nginx/sites-enabled/naviguide-simulator" >&2
  echo "    sudo nginx -t && sudo systemctl reload nginx" >&2
  exit 1
fi

"""deploy-simulator.sh : zones de débit déclarées une seule fois, redirections 443.

On exécute le vrai bloc nginx du script sur un /etc/nginx factice (NGINX_ETC).
`sudo` exécute la commande (sauf le test du certificat), `nginx -t` est un
substitut qui refuse, comme nginx, une zone déclarée deux fois ou utilisée sans
être déclarée, et `systemctl` ne fait que journaliser.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAV = ROOT / "infra/vps/naviguide"
SCRIPT = NAV / "deploy-simulator.sh"
VHOST = NAV / "nginx-simulator.conf"
LIMITS = NAV / "nginx-simulator-limits.conf"
REDIRECTS = NAV / "nginx-simulator-443-redirects.conf"
CERT = "/etc/letsencrypt/live/naviguide.fr/fullchain.pem"

ZONE_LINES = (
    "limit_req_zone $binary_remote_addr zone=sim_write:10m rate=30r/m;\n"
    "limit_req_zone $binary_remote_addr zone=sim_story:10m rate=12r/m;\n"
)
USES = (
    "        limit_req zone=sim_story burst=6 nodelay;\n"
    "        limit_req zone=sim_write burst=10 nodelay;\n"
)

SUDO_STUB = f"""#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
if [ "$1" = test ] && [ "${{3:-}}" = "{CERT}" ]; then
  [ "$STUB_HAVE_CERT" = 1 ]; exit $?
fi
exec "$@"
"""

SYSTEMCTL_STUB = """#!/usr/bin/env bash
echo "systemctl $*" >> "$STUB_LOG"
"""

NGINX_STUB = r"""#!/usr/bin/env python3
import os, re, sys
from pathlib import Path
etc = Path(os.environ["NGINX_ETC"])
with open(os.environ["STUB_LOG"], "a") as log:
    log.write("nginx-stub " + " ".join(sys.argv[1:]) + "\n")
if os.environ.get("STUB_NGINX_FAIL") == "1" and not Path(os.environ["STUB_FAIL_ONCE"]).exists():
    Path(os.environ["STUB_FAIL_ONCE"]).write_text("x")
    print("nginx: [emerg] échec forcé", file=sys.stderr); sys.exit(1)
files = sorted((etc / "conf.d").glob("*.conf")) + sorted((etc / "sites-enabled").glob("*"))
decl = {}
used = set()
for f in files:
    for line in f.read_text().splitlines():
        line = line.split("#", 1)[0]
        m = re.search(r"limit_req_zone\s.*zone=(\w+):", line)
        if m:
            decl[m.group(1)] = decl.get(m.group(1), 0) + 1
        for u in re.findall(r"\blimit_req\s+zone=(\w+)", line):
            used.add(u)
for z, n in decl.items():
    if n > 1:
        print(f'nginx: [emerg] limit_req_zone "{z}" is already bound', file=sys.stderr); sys.exit(1)
for z in used:
    if z not in decl:
        print(f'nginx: [emerg] zero size shared memory zone "{z}"', file=sys.stderr); sys.exit(1)
print("nginx: configuration file test is successful", file=sys.stderr)
"""


def _block() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    i = text.index("CERT=/etc/letsencrypt/live/naviguide.fr/fullchain.pem")
    j = text.index("# END nginx-sites", i)
    return text[i:j]


def _zone_count(etc: Path, zone: str) -> int:
    n = 0
    files = list((etc / "conf.d").glob("*.conf")) + list((etc / "sites-enabled").glob("*"))
    for f in files:
        for line in f.read_text().splitlines():
            if re.search(rf"^\s*limit_req_zone\s.*zone={zone}:", line):
                n += 1
    return n


class NginxLimitsFileTests(unittest.TestCase):
    def test_vhost_du_depot_ne_declare_plus_les_zones(self):
        text = VHOST.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"^\s*limit_req_zone", text, re.M), "zones encore dans le vhost")
        self.assertIn("limit_req zone=sim_write", text)
        self.assertIn("limit_req zone=sim_story", text)

    def test_hsts_un_an_et_csp_complete_encore_en_report_only(self):
        text = VHOST.read_text(encoding="utf-8")
        active = [line.strip() for line in text.splitlines() if not line.strip().startswith("#")]
        hsts = [line for line in active if "Strict-Transport-Security" in line]
        self.assertEqual(
            hsts,
            ['add_header Strict-Transport-Security "max-age=31536000" always;'],
        )
        enforced = [line for line in active if line.startswith("add_header Content-Security-Policy ")]
        self.assertEqual(len(enforced), 1, enforced)
        self.assertIn("frame-ancestors", enforced[0])
        self.assertNotIn("default-src", enforced[0])
        report = [line for line in active if line.startswith("add_header Content-Security-Policy-Report-Only ")]
        self.assertEqual(len(report), 1, report)
        self.assertIn("default-src 'self'", report[0])

    def test_fichier_conf_d_declare_les_deux_zones_une_fois(self):
        text = LIMITS.read_text(encoding="utf-8")
        for zone in ("sim_write", "sim_story"):
            self.assertEqual(len(re.findall(rf"^limit_req_zone .*zone={zone}:", text, re.M)), 1, zone)
        self.assertIn("zone=sim_write:10m rate=30r/m", text)
        self.assertIn("zone=sim_story:10m rate=12r/m", text)

    def test_redirections_443_www_et_simulator(self):
        text = REDIRECTS.read_text(encoding="utf-8")
        self.assertIn("listen 443 ssl;", text)
        self.assertIn("server_name www.naviguide.fr simulator.naviguide.fr;", text)
        self.assertIn("return 301 https://naviguide.fr$request_uri;", text)
        self.assertIn("ssl_certificate /etc/letsencrypt/live/naviguide.fr/fullchain.pem;", text)
        self.assertNotIn("listen 80", text)

    def test_rsync_et_publication_envoient_les_nouveaux_fichiers(self):
        for rel in ("infra/vps/ci/rsync-to-vps.sh", "infra/vps/naviguide/publish-simulator-from-mac.sh"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("nginx-simulator-limits.conf", text, rel)
            self.assertIn("nginx-simulator-443-redirects.conf", text, rel)


class DeploySimulatorNginxSequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.etc = base / "nginx"
        for d in ("conf.d", "sites-available", "sites-enabled"):
            (self.etc / d).mkdir(parents=True)
        self.bin = base / "bin"
        self.bin.mkdir()
        for name, body in (("sudo", SUDO_STUB), ("systemctl", SYSTEMCTL_STUB), ("nginx", NGINX_STUB)):
            p = self.bin / name
            p.write_text(body, encoding="utf-8")
            p.chmod(p.stat().st_mode | stat.S_IEXEC)
        self.log = base / "calls.log"
        self.fail_once = base / "failed-once"

    def tearDown(self):
        self.tmp.cleanup()

    def _site(self, name: str, body: str, enabled: bool):
        p = self.etc / "sites-available" / name
        p.write_text(body, encoding="utf-8")
        if enabled:
            (self.etc / "sites-enabled" / name).symlink_to(p)

    def _bootstrap(self, with_zones: bool):
        body = "# bootstrap HTTP\n" + (ZONE_LINES if with_zones else "") + (
            "server {\n    listen 80;\n    server_name naviguide.fr www.naviguide.fr simulator.naviguide.fr;\n"
            "    location ^~ /.well-known/acme-challenge/ { root /var/www/letsencrypt; }\n"
            "    location /api/ {\n" + USES + "    }\n}\n"
        )
        self._site("naviguide-http-bootstrap", body, enabled=True)

    def _old_vhost(self, enabled: bool):
        self._site(
            "naviguide-simulator",
            ZONE_LINES + "server {\n    listen 443 ssl;\n    server_name naviguide.fr;\n    location /api/ {\n" + USES + "    }\n}\n",
            enabled=enabled,
        )

    def _run(self, have_cert: bool, nginx_fail: bool = False):
        self.log.write_text("", encoding="utf-8")
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            STUB_LOG=str(self.log),
            STUB_HAVE_CERT="1" if have_cert else "0",
            STUB_NGINX_FAIL="1" if nginx_fail else "0",
            STUB_FAIL_ONCE=str(self.fail_once),
            NGINX_ETC=str(self.etc),
            NGINX_SRC=str(VHOST),
            LIMITS_SRC=str(LIMITS),
            REDIRECTS_SRC=str(REDIRECTS),
        )
        proc = subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + _block()],
            env=env, capture_output=True, text=True, timeout=60,
        )
        return proc, self.log.read_text(encoding="utf-8").splitlines()

    def _snapshot(self):
        out = {}
        for p in sorted(self.etc.rglob("*")):
            rel = str(p.relative_to(self.etc))
            if rel.startswith("naviguide-deploy-bak"):
                continue
            if p.is_symlink():
                out[rel] = "-> " + os.readlink(p)
            elif p.is_file():
                out[rel] = p.read_text(encoding="utf-8")
        return out

    def assertSingleZones(self):
        for zone in ("sim_write", "sim_story"):
            self.assertEqual(_zone_count(self.etc, zone), 1, zone)

    def test_contabo_apres_correctif_manuel_passe_sans_doublon(self):
        # État de Contabo le 19 oct. : bootstrap sans zones, ancien vhost (avec
        # zones) actif, redirections posées à la main et actives, certificat.
        self._bootstrap(with_zones=False)
        self._old_vhost(enabled=True)
        self._site("naviguide-443-redirects", "# manuel\n", enabled=True)
        proc, calls = self._run(have_cert=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertSingleZones()
        self.assertTrue((self.etc / "conf.d/naviguide-simulator-limits.conf").is_file())
        self.assertEqual(
            (self.etc / "sites-available/naviguide-simulator").read_text(), VHOST.read_text()
        )
        self.assertEqual(
            (self.etc / "sites-available/naviguide-443-redirects").read_text(), REDIRECTS.read_text()
        )
        self.assertTrue((self.etc / "sites-enabled/naviguide-simulator").is_symlink())
        self.assertTrue((self.etc / "sites-enabled/naviguide-443-redirects").is_symlink())
        self.assertIn("systemctl reload nginx", calls)

    def test_bootstrap_avec_zones_sans_certificat_pas_de_fichier_conf_d(self):
        self._bootstrap(with_zones=True)
        proc, calls = self._run(have_cert=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertSingleZones()
        self.assertFalse((self.etc / "conf.d/naviguide-simulator-limits.conf").exists())
        self.assertFalse((self.etc / "sites-enabled/naviguide-simulator").exists())
        self.assertFalse((self.etc / "sites-enabled/naviguide-443-redirects").exists())
        self.assertIn("non activé", proc.stderr)
        self.assertIn("systemctl reload nginx", calls)

    def test_bootstrap_avec_zones_et_certificat_toujours_une_seule_declaration(self):
        self._bootstrap(with_zones=True)
        self._old_vhost(enabled=False)
        proc, _ = self._run(have_cert=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertSingleZones()
        self.assertFalse((self.etc / "conf.d/naviguide-simulator-limits.conf").exists())
        self.assertTrue((self.etc / "sites-enabled/naviguide-simulator").is_symlink())

    def test_bootstrap_sans_zones_et_sans_certificat_zones_en_conf_d(self):
        self._bootstrap(with_zones=False)
        proc, _ = self._run(have_cert=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertSingleZones()
        self.assertTrue((self.etc / "conf.d/naviguide-simulator-limits.conf").is_file())

    def test_site_naviguide_actif_redirections_non_activees(self):
        self._bootstrap(with_zones=False)
        self._site("naviguide", "# redirections historiques\n", enabled=True)
        proc, _ = self._run(have_cert=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((self.etc / "sites-enabled/naviguide-443-redirects").exists())

    def test_nginx_t_en_echec_retour_a_l_etat_sauvegarde(self):
        self._bootstrap(with_zones=False)
        self._old_vhost(enabled=True)
        self._site("naviguide-443-redirects", "# manuel\n", enabled=False)
        before = self._snapshot()
        proc, calls = self._run(have_cert=True, nginx_fail=True)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("Retour à la configuration sauvegardée", proc.stderr)
        self.assertEqual(self._snapshot(), before)
        self.assertNotIn("systemctl reload nginx", calls)
        self.assertEqual(sum(1 for c in calls if c == "nginx-stub -t"), 2, calls)


if __name__ == "__main__":
    unittest.main()

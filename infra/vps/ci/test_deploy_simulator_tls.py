"""deploy-simulator.sh : sans certificat, nginx reste valide et le script réussit.

On exécute les blocs nginx/TLS et contrôles HTTPS du script réel avec des
substituts de `sudo` et `curl` qui journalisent les appels sans rien toucher.
"""
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/vps/naviguide/deploy-simulator.sh"

SUDO_STUB = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
case "$1" in
  test) [ "$STUB_HAVE_CERT" = 1 ]; exit $? ;;
  openssl) echo "DNS:naviguide.fr, DNS:www.naviguide.fr, DNS:simulator.naviguide.fr" ;;
esac
exit 0
"""

CURL_STUB = """#!/usr/bin/env bash
echo "curl $*" >> "$STUB_LOG"
printf '%s' "${STUB_HTTP_CODE:-000}"
"""


def _section(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


class DeploySimulatorTlsTests(unittest.TestCase):
    def setUp(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.nginx_block = _section(
            text, "CERT=/etc/letsencrypt/live/naviguide.fr/fullchain.pem", "# ── Health"
        )
        self.public_block = _section(text, 'if [ "$HAVE_CERT" -eq 0 ]; then\n  echo "  mode bootstrap', None)
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name) / "bin"
        self.bin.mkdir()
        for name, body in (("sudo", SUDO_STUB), ("curl", CURL_STUB)):
            p = self.bin / name
            p.write_text(body, encoding="utf-8")
            p.chmod(p.stat().st_mode | stat.S_IEXEC)
        self.log = Path(self.tmp.name) / "calls.log"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, body: str, have_cert: bool, http_code: str = "000"):
        self.log.write_text("", encoding="utf-8")
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            STUB_LOG=str(self.log),
            STUB_HAVE_CERT="1" if have_cert else "0",
            STUB_HTTP_CODE=http_code,
            NGINX_SRC="/nonexistent/nginx-simulator.conf",
        )
        script = "set -euo pipefail\n" + body
        proc = subprocess.run(
            ["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30
        )
        return proc, self.log.read_text(encoding="utf-8").splitlines()

    def test_sans_certificat_vhost_443_non_active_et_pas_de_certbot(self):
        proc, calls = self._run(self.nginx_block, have_cert=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(any(c.startswith("ln ") for c in calls), calls)
        self.assertFalse(any(c.startswith("certbot") for c in calls), calls)
        self.assertIn("nginx -t", calls)
        self.assertIn("non activé", proc.stderr)

    def test_avec_certificat_vhost_443_active(self):
        proc, calls = self._run(self.nginx_block, have_cert=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "ln -sf /etc/nginx/sites-available/naviguide-simulator "
            "/etc/nginx/sites-enabled/naviguide-simulator",
            calls,
        )
        self.assertIn("nginx -t", calls)

    def test_sans_certificat_controles_https_publics_sautes(self):
        proc, calls = self._run("HAVE_CERT=0\n" + self.public_block, have_cert=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(any("https://" in c for c in calls), calls)

    def test_avec_certificat_www_en_echec_fait_echouer(self):
        proc, calls = self._run("HAVE_CERT=1\n" + self.public_block, have_cert=True)
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(any("https://www.naviguide.fr/" in c for c in calls), calls)

    def test_avec_certificat_www_ok(self):
        proc, _ = self._run("HAVE_CERT=1\n" + self.public_block, have_cert=True, http_code="200")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_chown_vers_le_compte_de_deploiement(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('sudo chown -R "$(id -un):$(id -gn)" "$WWW_ROOT"', text)
        self.assertNotIn("chown -R ubuntu:ubuntu", text)

    def _marked(self, begin: str, end: str) -> str:
        text = SCRIPT.read_text(encoding="utf-8")
        return _section(text, begin, end)

    def test_film_sans_chapitre_arrete_le_deploiement(self):
        curl = self.bin / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s' '{\"status\":\"preparing\",\"chapters\":[]}'\n",
            encoding="utf-8",
        )
        curl.chmod(curl.stat().st_mode | stat.S_IEXEC)
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            STUB_LOG=str(self.log),
            FILM_READY_TRIES="1",
            FILM_READY_PAUSE="0",
        )
        proc = subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + self._marked("# BEGIN film-chapters", "# END film-chapters")],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("aucun chapitre", proc.stderr)

    def test_film_avec_chapitres_laisse_passer(self):
        curl = self.bin / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s' '{\"status\":\"ready\",\"chapters\":[{\"text\":\"Saint-Maur\"},{\"text\":\"La Rochelle\"}]}'\n",
            encoding="utf-8",
        )
        curl.chmod(curl.stat().st_mode | stat.S_IEXEC)
        env = dict(
            os.environ,
            PATH=f"{self.bin}:{os.environ['PATH']}",
            STUB_LOG=str(self.log),
            FILM_READY_TRIES="1",
            FILM_READY_PAUSE="0",
        )
        proc = subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + self._marked("# BEGIN film-chapters", "# END film-chapters")],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("2 chapitre", proc.stdout)

    def test_bascule_ecrite_sans_contact_et_sans_accord(self):
        block = self._marked("# BEGIN bascule-contabo", "# END bascule-contabo")
        for banned in ("curl", "ssh", "wget", "nc ", "nmap"):
            self.assertNotIn(banned, block)
        self.assertIn("135.125.226.16", block)
        self.assertIn("13.140.164.185", block)
        script = "set -euo pipefail\n" + block + "\nreport_contabo_switch\n"
        waiting = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, timeout=15,
            env=dict(os.environ, NAVIGUIDE_APPLY_CONTABO_SWITCH=""),
        )
        self.assertEqual(waiting.returncode, 0, waiting.stderr)
        self.assertIn("En attente de l'accord explicite de Clément", waiting.stdout)
        agreed = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, timeout=15,
            env=dict(os.environ, NAVIGUIDE_APPLY_CONTABO_SWITCH="accord-clement"),
        )
        self.assertEqual(agreed.returncode, 0, agreed.stderr)
        self.assertIn("n'est pas modifié", agreed.stdout)
        self.assertNotIn("En attente", agreed.stdout)

    def test_apply_scripts_par_defaut_sur_naviguide(self):
        for name in ("apply-site.sh", "apply-pending.sh"):
            text = (ROOT / "infra/vps/ci" / name).read_text(encoding="utf-8")
            self.assertIn('APP="${APP:-${REMOTE_APP:-/home/naviguide/naviguide}}"', text, name)
            self.assertNotIn("$HOME/blue-intelligence-map", text, name)


if __name__ == "__main__":
    unittest.main()

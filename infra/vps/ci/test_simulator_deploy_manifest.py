"""Le déploiement simulateur doit rsyncer film-front et ne pas effacer polar_data."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class SimulatorDeployManifestTests(unittest.TestCase):
    def test_rsync_includes_film_front_unit(self):
        text = (ROOT / "infra/vps/ci/rsync-to-vps.sh").read_text(encoding="utf-8")
        self.assertIn("naviguide-film-front.service", text)

    def test_publish_mac_includes_film_front_unit(self):
        text = (ROOT / "infra/vps/naviguide/publish-simulator-from-mac.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("naviguide-film-front.service", text)

    def test_rsync_excludes_polar_data_directory(self):
        text = (ROOT / "infra/vps/ci/rsync-to-vps.sh").read_text(encoding="utf-8")
        self.assertIn("--exclude server/polar_data/", text)

    def test_deploy_script_removes_zz_memory_dropin(self):
        text = (ROOT / "infra/vps/naviguide/deploy-simulator.sh").read_text(encoding="utf-8")
        self.assertIn("zz-memory.conf", text)

    def test_film_front_sources_present_in_repo(self):
        self.assertTrue(
            (ROOT / "infra/vps/naviguide/naviguide-film-front.service").is_file()
        )
        self.assertTrue((ROOT / "naviguide-simulator/server/film_front.py").is_file())


if __name__ == "__main__":
    unittest.main()

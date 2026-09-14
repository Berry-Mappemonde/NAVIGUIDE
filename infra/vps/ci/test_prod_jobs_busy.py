#!/usr/bin/env python3
"""Tests hermétiques de la sonde des files produit (pas de réseau)."""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prod_jobs_busy as probe  # noqa: E402


class PayloadReasonsTests(unittest.TestCase):
    def test_idle_empty(self):
        self.assertEqual(probe.payload_reasons({}), [])

    def test_running_flag(self):
        self.assertIn("running", probe.payload_reasons({"running": True}))
        self.assertEqual(probe.payload_reasons({"running": False}), [])

    def test_cycle_running(self):
        self.assertIn("cycle_running", probe.payload_reasons({"cycle_running": True}))

    def test_active_run_ids(self):
        self.assertIn("active_run_ids", probe.payload_reasons(
            {"active_run_ids": ["20260914-full"]}))
        self.assertEqual(probe.payload_reasons({"active_run_ids": []}), [])
        self.assertEqual(probe.payload_reasons({"active_run_ids": [None, ""]}), [])

    def test_active_run_id(self):
        self.assertIn("active_run_id", probe.payload_reasons(
            {"active_run_id": "abc"}))
        self.assertEqual(probe.payload_reasons({"active_run_id": None}), [])
        self.assertEqual(probe.payload_reasons({"active_run_id": ""}), [])

    def test_nested_live_and_task(self):
        self.assertIn("live.running", probe.payload_reasons(
            {"live": {"running": True}}))
        self.assertIn("task.running", probe.payload_reasons(
            {"task": {"running": True}}))
        self.assertIn("run.state", probe.payload_reasons(
            {"run": {"state": "started"}}))
        self.assertEqual(probe.payload_reasons({"run": {"state": "done"}}), [])

    def test_ignores_enabled_auto_refresh(self):
        self.assertEqual(
            probe.payload_reasons({"enabled": True, "cycle_running": False}),
            [],
        )


class ConnectionRefusedTests(unittest.TestCase):
    def test_direct_refused(self):
        self.assertTrue(probe.is_connection_refused(ConnectionRefusedError("nope")))

    def test_urlerror_wrapper(self):
        inner = ConnectionRefusedError()
        self.assertTrue(probe.is_connection_refused(urllib.error.URLError(inner)))

    def test_urlerror_text(self):
        self.assertTrue(probe.is_connection_refused(
            urllib.error.URLError("Connection refused")))

    def test_other_error(self):
        self.assertFalse(probe.is_connection_refused(TimeoutError("slow")))
        self.assertFalse(probe.is_connection_refused(
            urllib.error.URLError("timed out")))


class ProbeLoopTests(unittest.TestCase):
    def test_first_path_busy_stops_with_10(self):
        def fake_fetch(url, timeout, admin_key=""):
            if url.endswith("/api/swarm/status"):
                return {"running": True, "run_id": "r1"}
            return {"running": False}

        with mock.patch.object(probe, "fetch_json", side_effect=fake_fetch):
            code, hits = probe.probe("http://127.0.0.1:8001")
        self.assertEqual(code, probe.BUSY_EXIT)
        self.assertEqual(hits[0]["path"], "/api/swarm/status")
        self.assertIn("running", hits[0]["reasons"])

    def test_all_idle(self):
        with mock.patch.object(probe, "fetch_json", return_value={"running": False}):
            code, hits = probe.probe("https://blueintelligence.online")
        self.assertEqual(code, 0)
        self.assertEqual(len(hits), len(probe.PROBE_PATHS))

    def test_refused_is_idle(self):
        with mock.patch.object(
            probe, "fetch_json",
            side_effect=urllib.error.URLError(ConnectionRefusedError()),
        ):
            code, hits = probe.probe("http://127.0.0.1:8001")
        self.assertEqual(code, 0)
        self.assertTrue(hits[0].get("idle"))

    def test_timeout_is_error(self):
        with mock.patch.object(
            probe, "fetch_json",
            side_effect=TimeoutError("timed out"),
        ):
            code, hits = probe.probe("http://127.0.0.1:8001")
        self.assertEqual(code, probe.ERROR_EXIT)
        self.assertIn("error", hits[0])

    def test_gone_endpoint_is_skipped(self):
        def fake_fetch(url, timeout, admin_key=""):
            if url.endswith("/generate-batch/status"):
                raise urllib.error.HTTPError(
                    url, 410, "Gone", hdrs=None, fp=None)
            return {"running": False}

        # Le chemin 410 n'est plus dans PROBE_PATHS : on simule via side_effect
        # sur le premier chemin.
        with mock.patch.object(
            probe, "PROBE_PATHS",
            ("/api/poe/generate-batch/status", "/api/swarm/status"),
        ), mock.patch.object(probe, "fetch_json", side_effect=fake_fetch):
            code, hits = probe.probe("http://127.0.0.1:8001")
        self.assertEqual(code, 0)
        self.assertTrue(hits[0].get("skipped"))
        self.assertEqual(hits[1]["path"], "/api/swarm/status")

    def test_review_suggest_running_is_busy(self):
        def fake_fetch(url, timeout, admin_key=""):
            if url.endswith("/api/review/suggest/status"):
                return {"running": True}
            return {"running": False}

        with mock.patch.object(probe, "fetch_json", side_effect=fake_fetch):
            code, hits = probe.probe("http://127.0.0.1:8001", admin_key="sesame")
        self.assertEqual(code, probe.BUSY_EXIT)
        self.assertEqual(hits[0]["path"], "/api/review/suggest/status")

    def test_review_401_without_key_is_skipped(self):
        def fake_fetch(url, timeout, admin_key=""):
            if url.endswith("/api/review/suggest/status"):
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized", hdrs=None, fp=None)
            return {"running": False}

        with mock.patch.object(probe, "fetch_json", side_effect=fake_fetch):
            code, hits = probe.probe("http://127.0.0.1:8001")
        self.assertEqual(code, 0)
        review = next(h for h in hits if h["path"].endswith("/review/suggest/status"))
        self.assertTrue(review.get("skipped"))

    def test_review_401_with_key_is_error(self):
        def fake_fetch(url, timeout, admin_key=""):
            if url.endswith("/api/review/suggest/status"):
                raise urllib.error.HTTPError(
                    url, 401, "Unauthorized", hdrs=None, fp=None)
            return {"running": False}

        with mock.patch.object(probe, "fetch_json", side_effect=fake_fetch):
            code, hits = probe.probe("http://127.0.0.1:8001", admin_key="mauvaise")
        self.assertEqual(code, probe.ERROR_EXIT)
        self.assertIn("review/suggest", hits[0]["path"])


class FetchHeaderTests(unittest.TestCase):
    def test_user_agent_is_not_python_urllib(self):
        captured = {}

        class _Resp:
            def read(self):
                return b'{"running":false}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=0):
            captured["ua"] = req.get_header("User-agent") or req.headers.get("User-Agent")
            captured["accept"] = req.get_header("Accept")
            return _Resp()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            data = probe.fetch_json("http://127.0.0.1:8001/api/swarm/status", 2)
        self.assertEqual(data, {"running": False})
        self.assertIn("BlueIntelligence-DeployProbe", captured["ua"] or "")
        self.assertNotIn("Python-urllib", captured["ua"] or "")

    def test_admin_key_header(self):
        captured = {}

        class _Resp:
            def read(self):
                return b'{"running":false}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=0):
            captured["admin"] = req.get_header("X-admin-key")
            return _Resp()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            probe.fetch_json(
                "http://127.0.0.1:8001/api/review/suggest/status",
                2, admin_key="sesame")
        self.assertEqual(captured["admin"], "sesame")

    def test_load_admin_key_from_env_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            backend = Path(tmp) / "backend"
            backend.mkdir()
            (backend / ".env").write_text('ADMIN_KEY="sesame-file"\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"APP": tmp, "ADMIN_KEY": ""}, clear=False):
                os.environ.pop("ADMIN_KEY", None)
                self.assertEqual(probe.load_admin_key(), "sesame-file")


class CliTests(unittest.TestCase):
    def test_json_busy_exit(self):
        with mock.patch.object(
            probe, "probe",
            return_value=(probe.BUSY_EXIT, [{
                "path": "/api/swarm/status",
                "reasons": ["running"],
            }]),
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                code = probe.main(["--json", "--base-url", "http://example"])
        self.assertEqual(code, probe.BUSY_EXIT)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["exit"], probe.BUSY_EXIT)


class PlanTests(unittest.TestCase):
    def test_dispatch_all(self):
        import plan_deploy
        out = plan_deploy.decide("workflow_dispatch", input_site="all")
        self.assertEqual(out, {
            "bi": "true", "naviguide": "true", "simulator": "true",
            "catch_up": "false",
        })

    def test_schedule_only_catch_up(self):
        import plan_deploy
        out = plan_deploy.decide("schedule", files=["frontend/src/App.js"])
        self.assertEqual(out["catch_up"], "true")
        self.assertEqual(out["bi"], "false")

    def test_push_paths(self):
        import plan_deploy
        files = [
            "frontend/src/App.js",
            "naviguide/naviguide-app/src/App.jsx",
            "infra/vps/naviguide/deploy-simulator.sh",
            "docs/PRD.md",
        ]
        out = plan_deploy.decide("push", files=files)
        self.assertEqual(out["bi"], "true")
        self.assertEqual(out["naviguide"], "true")
        self.assertEqual(out["simulator"], "true")
        self.assertEqual(out["catch_up"], "false")

    def test_readme_alone_deploys_nothing(self):
        import plan_deploy
        out = plan_deploy.decide("push", files=["infra/vps/README.md"])
        self.assertEqual(out["bi"], "false")
        self.assertEqual(out["naviguide"], "false")
        self.assertEqual(out["simulator"], "false")

    def test_ci_scripts_alone_do_not_redeploy_sites(self):
        import plan_deploy
        out = plan_deploy.decide("push", files=[
            "infra/vps/ci/prod_jobs_busy.py",
            ".github/workflows/deploy.yml",
        ])
        self.assertEqual(out["bi"], "false")
        self.assertEqual(out["naviguide"], "false")
        self.assertEqual(out["simulator"], "false")
        self.assertEqual(out["catch_up"], "true")

    def test_docs_only_no_catch_up(self):
        import plan_deploy
        out = plan_deploy.decide("push", files=["infra/vps/README.md"])
        self.assertEqual(out["catch_up"], "false")

    def test_naviguide_infra_excludes_simulator(self):
        import plan_deploy
        out = plan_deploy.decide("push", files=[
            "infra/vps/naviguide/nginx-naviguide.conf",
        ])
        self.assertEqual(out["naviguide"], "true")
        self.assertEqual(out["simulator"], "false")

    def test_dispatch_one_site(self):
        import plan_deploy
        out = plan_deploy.decide("workflow_dispatch", input_site="simulator")
        self.assertEqual(out["simulator"], "true")
        self.assertEqual(out["bi"], "false")
        self.assertEqual(out["naviguide"], "false")


if __name__ == "__main__":
    unittest.main()

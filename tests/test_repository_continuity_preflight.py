# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise Relay's local continuity adapter without requiring Cargo."""

from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "actions/repository-continuity-preflight/scripts/run_repository_continuity_preflight.py"
SPEC = importlib.util.spec_from_file_location("relay_continuity_preflight", MODULE)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
FIXTURES = json.loads((ROOT / "tests/fixtures/continuity-preflight/cases.v1.json").read_text(encoding="utf-8"))

class RepositoryContinuityPreflightTests(unittest.TestCase):
    def test_command_is_offline_and_explicit(self) -> None:
        request = FIXTURES["requests"]["public-updated"]
        command = adapter.build_command(Path("/egolint"), Path("/consumer"), ".config/continuity.toml", request)
        self.assertIn("--offline", command)
        self.assertIn("--continuity-base", command)
        self.assertNotIn("fetch", command)

    def test_normalizes_allowlisted_report(self) -> None:
        request = FIXTURES["requests"]["public-updated"]
        raw = {"status": "incomplete", "comparison": {"base": {"requested": request["comparison"]["base_revision"], "resolved_revision": request["comparison"]["base_revision"]}, "head": {"requested": "working-tree", "resolved_revision": None}, "topology": "working_tree"}, "evidence_layers": {"structural": "valid", "freshness_declaration": "incomplete", "local_git": "valid", "external_live_state": "verified"}, "diagnostics": [{"rule_id": "EGO-CONTINUITY-FRESHNESS-001", "severity": "warning", "message": "Checkpoint transition is incomplete.", "remediation": "Refresh the checkpoint."}]}
        result = adapter.normalize(raw, request, FIXTURES["profile_sha256"])
        self.assertEqual(result["outcome"], "warning")
        self.assertEqual(result["findings"][0]["layer"], "freshness-declaration")
        self.assertEqual(adapter.contract.validate_result(result), [])

    def test_missing_runner_writes_unavailable_result_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = json.loads(json.dumps(FIXTURES["requests"]["public-updated"]))
            request["output"]["path"] = "evidence/result.json"
            (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
            (root / "policy.toml").write_text("policy\n", encoding="utf-8")
            namespace = adapter.parser().parse_args(["--repository-root", str(root), "--request", "request.json", "--egolint-source", str(root / "egolint"), "--continuity-policy", "policy.toml"])
            with mock.patch.object(adapter, "verify_egolint_source"), mock.patch.object(adapter.shutil, "which", return_value=None):
                result, output = adapter.run(namespace)
            self.assertEqual(result["semantic_status"], "unavailable")
            self.assertEqual(adapter.contract.validate_result(result), [])
            self.assertTrue(output.is_file())
            self.assertFalse((root / ".reports").exists())

if __name__ == "__main__":
    unittest.main()

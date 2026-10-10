# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""ADR build admission, full action parity, and truthful partial-domain rendering."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_repository_adr_collector as native
import test_repository_intelligence_portability as portability

SCRIPT = native.SCRIPT.with_name("prepare_repository_adr_build.py")
site = native.load("adr_build_site", native.SCRIPT.with_name("generate_repository_intelligence_site.py"))
contract = native.load("adr_build_contract", native.SCRIPT.with_name("repository_adr_build_contract.py"))


@unittest.skipUnless(os.environ.get("RELAY_ADR_RUNTIME"), "prepare the locked ADR runtime and set RELAY_ADR_RUNTIME")
class AdrBuildTests(unittest.TestCase):
    setUp = native.NativeTests.setUp
    def commit(self):
        native.git(self.consumer, "add", "--all", "docs/decisions")
        native.git(self.consumer, "commit", "--quiet", "--allow-empty", "--message", "test: ADR build corpus")
        return native.git(self.consumer, "rev-parse", "HEAD")
    change = native.NativeTests.change

    def build(self, **overrides):
        values = dict(runtime=str(self.runtime), repository_root=str(self.consumer),
                      repository="egohygiene/relay", visibility="public",
                      source_commit=native.git(self.consumer, "rev-parse", "HEAD"),
                      observed_at="2026-10-04T21:00:00Z")
        values.update(overrides)
        command = [sys.executable, "-I", str(SCRIPT)]
        for key, value in values.items():
            command.extend(["--" + key.replace("_", "-"), value])
        return subprocess.run(command, capture_output=True, text=True)

    def outputs(self):
        directory = self.consumer / ".cache/repository-intelligence/adr"
        return (json.loads((directory / "snapshot.json").read_text()),
                json.loads((directory / "receipt.json").read_text()))

    def test_native_cli_admits_valid_source_and_binds_complete_provenance(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot, receipt = self.outputs()
        site.validate_snapshot(snapshot, "egohygiene/relay", receipt["source_commit"])
        self.assertEqual(receipt["validation"]["egolint"], "incomplete")
        self.assertEqual(receipt["coverage"]["decisions"]["collection"], "observed")
        self.assertEqual(len(snapshot["views"]["decisions"]["decisions"]), 3)
        self.assertEqual(native.git(self.consumer, "status", "--short", "--untracked-files=no"), "")
        contract.validate(receipt, "egohygiene/relay", receipt["source_commit"])
        for mutation in ("commit", "pin", "coverage", "source", "digest"):
            altered = deepcopy(receipt)
            if mutation == "commit": altered["source_commit"] = "f" * 40
            if mutation == "pin": altered["runtime"]["lock_sha256"] = "f" * 64
            if mutation == "coverage": altered["coverage"]["git"]["collection"] = "observed_empty"
            if mutation == "source": altered["sources"][0]["path"] = "../secret"
            if mutation == "digest": altered["candidate_digests"]["snapshot_sha256"] = None
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contract.validate(altered, "egohygiene/relay", receipt["source_commit"])

    def test_invalid_retry_removes_previous_candidate_and_preserves_canonical_source(self):
        self.assertEqual(self.build().returncode, 0)
        (self.consumer / native.POLICY).unlink()
        self.commit()
        result = self.build()
        self.assertEqual(result.returncode, 2)
        self.assertIn("source-validation", result.stderr)
        self.assertNotIn(str(self.consumer), result.stderr)
        self.assertFalse((self.consumer / ".cache/repository-intelligence/adr/snapshot.json").exists())
        self.assertEqual(native.git(self.consumer, "status", "--short", "--untracked-files=no"), "")

    def test_legacy_and_private_source_cannot_be_admitted(self):
        legacy = self.consumer / "docs/decisions/ADR-004-legacy.md"
        legacy.write_text("# Legacy decision\n")
        self.commit()
        self.assertNotEqual(self.build().returncode, 0)
        result = self.build(visibility="private")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("egohygiene/relay", result.stderr)

    def test_conflicting_inputs_and_unsafe_output_or_runtime_fail_closed(self):
        for values in ({"observatory_snapshot": "snapshot.json"}, {"observatory_comparison": "compare.json"},
                       {"work_directory": "docs/decisions"}, {"runtime": str(self.consumer)},
                       {"work_directory": "../outside"}):
            with self.subTest(values=values):
                self.assertEqual(self.build(**values).returncode, 2)
        (self.consumer / ".cache/link").symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.build(work_directory=".cache/link").returncode, 2)

    def test_alpha2_coverage_roundtrip_rejects_missing_contradictory_and_cross_view_claims(self):
        self.assertEqual(self.build().returncode, 0)
        snapshot, receipt = self.outputs()
        for mutation in ("missing", "mixed", "claim", "view", "time", "private"):
            altered = deepcopy(snapshot)
            if mutation == "private": altered["visibility"] = "private"
            if mutation == "missing": del altered["coverage"]["domains"]["checks"]
            if mutation == "mixed": altered["coverage"]["status"] = "current"
            if mutation == "claim": altered["coverage"]["domains"]["git"]["collection"] = "observed_empty"
            if mutation == "view": altered["views"]["health"]["collection_coverage"]["checks"]["reason"] = "complete"
            if mutation == "time": altered["coverage"]["domains"]["decisions"]["observed_at"] = "2099-01-01T00:00:00Z"
            with self.subTest(mutation=mutation), self.assertRaises(site.SiteInputError):
                site.validate_snapshot(altered, "egohygiene/relay", receipt["source_commit"])
        for route in ("roadmap", "journey", "health", "releases", "work"):
            self.assertEqual(site.projection_freshness(snapshot, route), "unknown")
            self.assertIn("Uncollected", site.collection_notice(snapshot, route))
        self.assertEqual(site.projection_freshness(snapshot, "decisions"), "current")
        self.assertEqual(site.projection_freshness(snapshot, "now"), "partial")

    def test_complete_action_bundles_match_across_checkouts_and_cli(self):
        harness = portability.RepositoryIntelligencePortabilityTests()
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        harness.seed = self.consumer
        harness.commit = native.git(self.consumer, "rev-parse", "HEAD")
        one, two = harness.checkout("first/consumer"), harness.checkout("second/different")
        environment = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}
        inputs = {"collect-adrs": "true", "adr-runtime": str(self.runtime), "repository": "egohygiene/relay",
                  "as-of": "2026-10-04T21:00:00Z"}
        from unittest.mock import patch
        with patch.object(portability, "REPOSITORY", "egohygiene/relay"):
            for index, checkout in enumerate((one, two)):
                replay = os.environ.get("RELAY_ADR_REPLAY_RUNTIME", str(self.runtime)) if index else str(self.runtime)
                try:
                    harness.run_action(checkout, inputs={**inputs, "adr-runtime": replay}, environment=environment)
                except subprocess.CalledProcessError as error:
                    self.fail(error.stderr)
        self.assertEqual(portability.inventory(one / "dist/intelligence"), portability.inventory(two / "dist/intelligence"))
        provenance = json.loads((one / "dist/intelligence/provenance.json").read_text())
        self.assertIn("adr_collection", provenance)
        schema = json.loads((native.SCRIPT.parent.parent / "schemas/repository-intelligence-provenance.schema.json").read_text())
        native.collector.jsonschema.Draft202012Validator(schema, format_checker=native.collector.jsonschema.FormatChecker()).validate(provenance)
        html = (one / "dist/intelligence/decisions/index.html").read_text()
        for value in ("ADR-001", "ADR-002", "ADR-003", "Declared human approval", "/pull/24", "/docs/decisions/README.md"):
            self.assertIn(value, html)
        self.assertIn("Uncollected", (one / "dist/intelligence/roadmap/index.html").read_text())
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.outputs()[1], provenance["adr_collection"])

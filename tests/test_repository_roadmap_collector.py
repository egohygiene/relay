# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise collector trust boundaries and the actual pinned upstream pipeline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "actions/repository-intelligence/scripts/collect_repository_roadmap.py"
FIXTURES = ROOT / "tests/fixtures/repository-roadmap-collector"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    collector = load("roadmap_collector", SCRIPT)
except ModuleNotFoundError as error:
    if error.name not in {"jsonschema", "yaml"}:
        raise
    raise unittest.SkipTest("install roadmap-collector-requirements.txt for the experimental native collector") from error
site = load("roadmap_collector_site", SCRIPT.with_name("generate_repository_intelligence_site.py"))

VALID = """# Synthetic roadmap
<!-- roadmap-manifest
schema: hygiene.roadmap/v1alpha1
repository: egohygiene/relay
visibility: public
publication: artifact-only
route: /roadmap/
updated: 2026-09-26
-->
<!-- roadmap-step
id: REL-ONE
status: complete
depends_on: []
issues: []
-->
### REL-ONE — Foundation
**State:** `complete`
**Outcome:** A stable foundation exists.
**Exit criteria:**
- [x] A useful foundation is available.

<!-- roadmap-step
id: REL-TWO
status: active
depends_on: [REL-ONE]
issues: [112]
-->
### REL-TWO — Collector
**State:** `active`
**Outcome:** Canonical intent is collected
without changing its meaning.
**Exit criteria:**
- [ ] Real source and dependencies survive.
  Continuation text stays attached.
- [ ] Provider observations stay separate.

**Current evidence:**
This section is not a second criteria list.
""".replace("publication: artifact-only", "publication: composed")


def git(root, *args, **kwargs):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_AUTHOR_DATE": "2026-09-26T12:00:00Z", "GIT_COMMITTER_DATE": "2026-09-26T12:00:00Z"}
    return subprocess.check_output(["git", "-C", str(root), *args], env=env, stderr=subprocess.PIPE, **kwargs).decode().strip()


def repository(root, text=VALID):
    root.mkdir()
    git(root, "init", "--quiet", "--initial-branch", "main")
    git(root, "config", "user.name", "Synthetic fixture")
    git(root, "config", "user.email", "fixture@example.test")
    (root / "ROADMAP.md").write_text(text)
    git(root, "add", "ROADMAP.md")
    git(root, "commit", "--quiet", "--message", "test: immutable roadmap input")
    return git(root, "rev-parse", "HEAD")


class CollectorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_exact_real_canary_bytes_and_mapping(self):
        metadata = json.loads((FIXTURES / "akashic-source.json").read_text())
        data = (FIXTURES / "akashic.ROADMAP.md").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), metadata["sha256"])
        steps = collector.extract(data.decode())
        self.assertEqual([s["id"] for s in steps], [f"AKA-Q0{i}" for i in range(1, 6)])
        self.assertEqual(steps[2]["status"], "ready")
        self.assertEqual(steps[2]["depends_on"], ["AKA-Q02"])
        self.assertEqual(len(steps[0]["exit_criteria"]), 2)
        self.assertIn("publicly accessible", steps[0]["exit_criteria"][0]["text"])

    def test_multiline_criteria_and_outcome_are_bounded_to_sections(self):
        step = collector.extract(VALID)[1]
        self.assertEqual(step["outcome"], "Canonical intent is collected without changing its meaning.")
        self.assertEqual(len(step["exit_criteria"]), 2)
        self.assertTrue(step["exit_criteria"][0]["text"].endswith("Continuation text stays attached."))

    def test_duplicate_keys_aliases_and_hostile_paths_are_rejected(self):
        for value in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(collector.CollectorError):
                collector.load_json(value.encode())
        for value in ("id: A\nid: B", "id: &id X\nother: *id"):
            with self.assertRaises(collector.CollectorError):
                collector.metadata(value)
        target = self.root / "target"
        target.write_text("sensitive")
        link = self.root / "link"
        link.symlink_to(target)
        with self.assertRaises(collector.CollectorError):
            collector.read_file(link)
        with self.assertRaises(collector.CollectorError):
            collector.safe_path(self.root / ".." / "target")

    def test_provider_capture_rejects_protected_extra_and_unreferenced_data(self):
        value = {"schema": collector.PROVIDER_SCHEMA, "repository": "egohygiene/relay", "visibility": "public",
                 "observed_at": "2026-09-26T12:00:00Z", "status": "observed", "issues": [{"number": 112, "state": "open"}]}
        path = self.root / "provider.json"
        variants = [dict(value, visibility="private"), dict(value, visibility="unknown"),
                    dict(value, repository="protected/hidden"), dict(value, token="sensitive"),
                    dict(value, issues=[{"number": 999, "state": "open"}]),
                    dict(value, issues=[{"number": 112, "state": "open", "body": "sensitive"}]),
                    dict(value, issues=value["issues"] * 2), dict(value, status="unavailable"),
                    dict(value, observed_at="2026-09-27T00:00:00Z")]
        for candidate in variants:
            with self.subTest(candidate=candidate):
                path.write_text(json.dumps(candidate))
                with self.assertRaises(collector.CollectorError):
                    collector.provider_capture(path, "egohygiene/relay", {112}, collector.utc("2026-09-26T19:00:00Z"), 86400)

    def test_nonpublic_request_exports_only_closed_denial(self):
        output = self.root / collector.OUTPUT_NAME
        result = subprocess.run(["python3", str(SCRIPT), "collect", "--runtime", str(self.root),
            "--repository-root", str(self.root), "--repository", "protected/hidden",
            "--source-commit", "a" * 40, "--visibility", "private", "--observed-at", "2026-09-26T19:00:00Z",
            "--output", str(output)], capture_output=True)
        self.assertEqual(result.returncode, 3)
        exported = output.read_text() + result.stdout.decode() + result.stderr.decode()
        for protected in ("protected/hidden", "hidden", str(self.root), "a" * 40):
            self.assertNotIn(protected, exported)
        self.assertEqual(json.loads(output.read_text())["publication"], "denied")


@unittest.skipUnless(os.environ.get("RELAY_ROADMAP_RUNTIME"), "prepare pinned runtime and set RELAY_ROADMAP_RUNTIME for native integration")
class CollectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = Path(os.environ["RELAY_ROADMAP_RUNTIME"])

    def collect(self, text=VALID, *, provider=None, as_of="2026-09-26T19:00:00Z"):
        root = self.root / f"consumer-{len(list(self.root.iterdir()))}"
        sha = repository(root, text)
        args = argparse.Namespace(runtime=self.runtime, repository_root=root, repository="egohygiene/relay",
            visibility="public", source_commit=sha, observed_at=as_of, provider_evidence=provider,
            maximum_intent_age_days=30, maximum_provider_age_seconds=86400)
        return collector.collect(args), args

    def test_pinned_validators_normalizer_and_existing_renderer(self):
        result, args = self.collect()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["publication"], "denied")
        self.assertEqual(result["validation"]["hygiene"], "valid")
        self.assertEqual(result["validation"]["egolint"], "incomplete")
        snapshot = result["snapshot_candidate"]
        site.validate_snapshot(snapshot, args.repository, args.source_commit)
        html = site.roadmap_body(snapshot)
        self.assertIn("REL-ONE", html)
        self.assertIn("Continuation text stays attached.", html)
        self.assertNotIn("Observatory roadmap unavailable", html)
        # Public entry point must never accept the review envelope.
        with self.assertRaises(site.SiteInputError):
            site.validate_snapshot(result, args.repository, args.source_commit)
        for domain in ("adrs", "checks", "releases", "deployments", "work_inventory", "history"):
            self.assertEqual(result["coverage"][domain], "uncollected")

    def test_complete_envelopes_reproduce_across_paths_and_ignore_dirty_source(self):
        first, args = self.collect()
        clone = self.root / "different-parent" / "different-name"
        clone.parent.mkdir()
        subprocess.run(["git", "clone", "--quiet", str(args.repository_root), str(clone)], check=True)
        (clone / "ROADMAP.md").write_text("uncommitted source must never be used")
        args.repository_root = clone
        second = collector.collect(args)
        self.assertEqual(collector.json_bytes(first), collector.json_bytes(second))
        self.assertNotIn(str(self.root), collector.json_bytes(first).decode())
        self.assertNotIn("fixture@example.test", collector.json_bytes(first).decode())

    def test_owning_validator_reports_invalid_structure_state_links_and_cycles(self):
        variants = {
            "EGO-INTEL-ROADMAP-STRUCTURE-001": VALID.replace("id: REL-TWO", "id: REL-ONE"),
            "EGO-INTEL-ROADMAP-STATE-001": VALID.replace("status: complete", "status: active").replace("`complete`", "`active`"),
            "EGO-INTEL-LINK-001": VALID.replace("depends_on: [REL-ONE]", "depends_on: [REL-MISSING]"),
            "EGO-INTEL-CYCLE-001": VALID.replace("depends_on: []", "depends_on: [REL-TWO]"),
        }
        for rule, source in variants.items():
            with self.subTest(rule=rule):
                # Duplicate IDs also make extraction ambiguous; upstream diagnostics
                # are asserted from the owning executable before any projection.
                if rule == "EGO-INTEL-ROADMAP-STRUCTURE-001":
                    source = source.replace("### REL-TWO", "### REL-ONE")
                result, _ = self.collect(source)
                self.assertEqual(result["status"], "invalid")
                self.assertIn(rule, [d["code"] for d in result["diagnostics"]])
                self.assertEqual(result["publication"], "denied")

    def test_malformed_step_retains_owner_diagnostics_without_partial_snapshot(self):
        result, _ = self.collect(VALID.replace("depends_on: [REL-ONE]", "depends_on: ["))
        self.assertEqual(result["status"], "invalid")
        self.assertIn("EGO-INTEL-ROADMAP-STRUCTURE-001", [d["code"] for d in result["diagnostics"]])
        self.assertIsNone(result["snapshot_candidate"])

    def test_committed_symlink_and_foreign_reference_fail_closed(self):
        result, args = self.collect()
        source = args.repository_root / "ROADMAP.md"
        source.unlink()
        source.symlink_to("private-source.md")
        git(args.repository_root, "add", "ROADMAP.md")
        git(args.repository_root, "commit", "--quiet", "--message", "test: hostile source link")
        args.source_commit = git(args.repository_root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(collector.CollectorError, "PATH"):
            collector.collect(args)
        with self.assertRaisesRegex(collector.CollectorError, "PROVIDER"):
            self.collect(VALID.replace("issues: [112]", "issues: ['https://github.com/protected/hidden/issues/1']"))

    def test_stale_provider_cannot_complete_canonical_intent(self):
        capture = self.root / "provider.json"
        capture.write_text(json.dumps({"schema": collector.PROVIDER_SCHEMA, "repository": "egohygiene/relay",
            "visibility": "public", "observed_at": "2026-09-26T12:00:00Z", "status": "observed",
            "issues": [{"number": 112, "state": "closed"}]}))
        result, _ = self.collect(provider=capture, as_of="2026-11-26T19:00:00Z")
        steps = result["snapshot_candidate"]["views"]["roadmap"]["steps"]
        self.assertEqual(steps[1]["entity"]["state"], "active")
        self.assertEqual(steps[1]["tracked_by"][0]["state"], "closed")
        self.assertEqual(steps[1]["tracked_by"][0]["freshness"], "stale")
        self.assertIn("STALE_INTENT", [d["code"] for d in result["diagnostics"]])
        self.assertIn("STALE_PROVIDER", [d["code"] for d in result["diagnostics"]])

    def test_unavailable_provider_and_tampered_runtime_fail_honestly(self):
        capture = self.root / "provider.json"
        capture.write_text(json.dumps({"schema": collector.PROVIDER_SCHEMA, "repository": "egohygiene/relay",
            "visibility": "public", "observed_at": "2026-09-26T12:00:00Z", "status": "unavailable", "issues": []}))
        result, args = self.collect(provider=capture)
        self.assertEqual(result["coverage"]["issue_references"], "unavailable")
        self.assertEqual(result["snapshot_candidate"]["views"]["roadmap"]["steps"][1]["tracked_by"], [])
        self.assertEqual(result["references"][0]["url"], "https://github.com/egohygiene/relay/issues/112")
        tampered = self.root / "runtime"
        shutil.copytree(self.runtime, tampered)
        (tampered / "hygiene/tools/intelligence.py").write_text("raise RuntimeError('must never execute')")
        args.runtime = tampered
        with self.assertRaisesRegex(collector.CollectorError, "PIN"):
            collector.collect(args)

    @unittest.skipUnless(os.environ.get("RELAY_AKASHIC_REPOSITORY"), "set RELAY_AKASHIC_REPOSITORY to replay exact real Git source")
    def test_real_akashic_revision_retains_intent_and_source_defect(self):
        result, args = self.collect()
        source = json.loads((FIXTURES / "akashic-source.json").read_text())
        args.repository_root = Path(os.environ["RELAY_AKASHIC_REPOSITORY"])
        args.repository = source["repository"]
        args.source_commit = source["revision"]
        result = collector.collect(args)
        self.assertEqual(result["inputs"]["roadmap_sha256"], source["sha256"])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("EGO-INTEL-ROADMAP-STATE-001", [d["code"] for d in result["diagnostics"]])
        steps = result["snapshot_candidate"]["views"]["roadmap"]["steps"]
        self.assertEqual([s["entity"]["key"] for s in steps], [f"AKA-Q0{i}" for i in range(1, 6)])
        self.assertEqual(steps[2]["entity"]["state"], "ready")
        self.assertEqual(steps[2]["readiness"]["value"], "waiting")
        self.assertEqual(len(steps[4]["dependencies"]), 2)
        self.assertEqual(len(result["references"]), 10)
        self.assertIn("AKA-Q05", site.roadmap_body(result["snapshot_candidate"]))


if __name__ == "__main__":
    unittest.main()

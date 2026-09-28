# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

"""Exercise real offline architecture validation and its hostile-input boundary."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_repository_architecture_validation as adapter

RUNTIME = os.environ.get("RELAY_ARCHITECTURE_RUNTIME")

ADR = """---
schema: egohygiene.architecture-decision/v1
id: ADR-001
title: Keep decisions in the repository
status: proposed
date: 2026-09-20
decision_scope: repository
visibility: public
owners: [egohygiene/example]
issue: https://github.com/egohygiene/example/issues/1
pull_request: null
related: []
supersedes: []
superseded_by: []
affected_repositories: [egohygiene/example]
affected_contracts: [egohygiene.architecture-decision/v1]
implementation_status: not_started
evidence: []
exceptions: []
approval: null
extensions: {}
---

# ADR-001: Keep decisions in the repository

## Context

Decisions need reviewable source evidence.

## Decision

Keep the records in this repository.

## Alternatives considered and rejected

A separate mutable log would lose the source review boundary.

## Consequences and tradeoffs

Maintainers review record changes alongside implementation.

## Implementation and evidence links

The linked issue tracks implementation.

## Replacement or exit strategy

Propose a replacement while preserving this record.

## Follow-up work

Run the shared validator.
"""


class AdapterFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "consumer"
        self.root.mkdir()
        self.runtime = Path(RUNTIME).resolve() if RUNTIME else self.directory / "missing-runtime"
        self.request_path = self.directory / "request.json"
        template = self.directory / "empty-template"
        template.mkdir()
        adapter.git(self.root, "init", "--quiet", "--template", str(template))
        self.put(".gitignore", ".reports/\n")
        self.put("README.md", "# Example\n")
        self.request = {
            "schema_version": adapter.contract.REQUEST_SCHEMA,
            "profile": {"version": adapter.profile()["version"], "sha256": adapter.digest(adapter.read_file(adapter.PROFILE_PATH))},
            "repository": {"id": "egohygiene/example", "visibility": "public", "root": ".", "represented_revision": "working-tree"},
            "mode": "advisory",
            "adoption": {"repository-contracts": "unknown", "architecture-records": "not-applicable", "diagram-sources": "not-applicable"},
            "inputs": {"repository_contracts": [], "repository_intelligence_policy": None, "diagram_roots": []},
            "bounds": {"maximum_findings": 256, "maximum_scanned_files": 1000, "maximum_scanned_bytes": 4 * 1024 * 1024},
            "output": {"format": "json", "path": ".reports/architecture-validation/result.json"},
        }

    def put(self, name: str, data: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    def commit(self) -> str:
        adapter.git(self.root, "add", "--all")
        adapter.git(self.root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "--quiet", "--allow-empty", "--message", "test: capture fixture")
        revision = adapter.git(self.root, "rev-parse", "HEAD").decode().strip()
        self.request["repository"]["represented_revision"] = revision
        return revision

    def invoke(self) -> dict:
        self.request_path.write_bytes(adapter.encoded(self.request))
        result = adapter.run(argparse.Namespace(repository_root=self.root, request=self.request_path, runtime=self.runtime))
        self.assertEqual(adapter.contract.validate_result(result), [])
        self.assertEqual(json.loads((self.root / self.request["output"]["path"]).read_bytes()), result)
        return result

    def add_contract(self, requirements: str | None = None) -> None:
        self.put("policy/contract.toml", """schema-version = 1
id = "hygiene.fixture/v1"
version = "1.0.0"
profile = "fixture"
provisional = false
[source]
repository = "egohygiene/hygiene"
revision = "c589587395750cd1c79c6fa0bef010189c547249"
revision-kind = "git-commit"
path = "contracts/repository-context.v1.toml"
decision = "https://github.com/egohygiene/hygiene/issues/15"
""" + (requirements or """[[requirements]]
id = "readme"
path = "README.md"
kind = "file"
ownership = "repository-owned"
"""))
        self.request["adoption"]["repository-contracts"] = "present"
        self.request["inputs"]["repository_contracts"] = ["policy/contract.toml"]

    def add_adrs(self) -> None:
        definitions = adapter.catalog(self.runtime)
        policy = 'schema-version = 1\nid = "egolint.repository-intelligence-validation/v1"\nrepository = "egohygiene/example"\n'
        rules = [r for r in definitions["rules"] if r.startswith("EGO-INTEL-")]
        policy += '[profile]\nid = "fixture"\nenforcement = "advisory"\nenabled-rules = ' + json.dumps(rules) + "\n"
        for pin in definitions["pins"]:
            policy += "\n[[contracts]]\n" + "".join(f"{key} = {json.dumps(value)}\n" for key, value in pin.items())
        policy += """
[adrs]
state = "present"
policy-reference = "docs/decisions/policy-reference.json"
decision-directory = "docs/decisions"
index = "docs/decisions/README.md"
[roadmap]
state = "not-applicable"
path = "ROADMAP.md"
[commit-history]
state = "not-applicable"
maximum-commits = 256
"""
        self.put("policy/intelligence.toml", policy)
        self.put("docs/decisions/ADR-001-repository-records.md", ADR)
        self.put("docs/decisions/README.md", "# Decisions\n\n[ADR-001](ADR-001-repository-records.md)\n")
        pin = next(p for p in definitions["pins"] if p["id"] == "egohygiene.architecture-decision/v1")
        reference = {"schema": "egohygiene.architecture-decision-policy-reference/v1", "repository": "egohygiene/example",
                     "policy": {"contract": pin["id"], "version": pin["version"],
                                "source": {"repository": pin["source-repository"], "revision": pin["source-revision"], "path": "docs/decisions/POLICY.md"}},
                     "decision_directory": "docs/decisions", "index": "docs/decisions/README.md", "extensions": [], "exceptions": []}
        self.put("docs/decisions/policy-reference.json", json.dumps(reference))
        self.request["adoption"]["repository-contracts"] = "not-applicable"
        self.request["adoption"]["architecture-records"] = "present"
        self.request["inputs"]["repository_intelligence_policy"] = "policy/intelligence.toml"

    def artifact(self, result: dict, name: str) -> dict:
        return json.loads((self.root / result["artifacts"][name]).read_bytes())


class ArchitectureAdapterBoundaryTests(AdapterFixture):
    def test_runtime_cannot_be_supplied_from_the_consumer(self) -> None:
        self.runtime = self.root / "runtime"
        result = self.invoke()
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-PATH-001")

    def test_missing_python_dependency_is_explicit_unavailable(self) -> None:
        with mock.patch.object(adapter.importlib.metadata, "version", side_effect=adapter.importlib.metadata.PackageNotFoundError):
            result = self.invoke()
        self.assertEqual(result["semantic_status"], "unavailable")

    def test_missing_runtime_is_explicit_unavailable_and_sanitized(self) -> None:
        self.runtime = self.directory / "PRIVATE_CANARY_runtime"
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "unavailable")
        self.assertNotIn("PRIVATE_CANARY", json.dumps(result))
        self.assertTrue(all(value is None for value in result["artifacts"].values()))

    def test_required_mode_cannot_activate_before_release(self) -> None:
        self.request["mode"] = "required"
        result = self.invoke()
        self.assertEqual(result["outcome"], "unavailable")
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-MODE-001")

    def test_all_not_applicable_needs_no_runtime_or_scan(self) -> None:
        self.request["adoption"]["repository-contracts"] = "not-applicable"
        self.request["repository"]["represented_revision"] = "not-applicable"
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "not-applicable")
        self.assertEqual(result["bounds"]["observed_scanned_files"], 0)

    def test_output_symlink_is_rejected_without_writing_outside(self) -> None:
        outside = self.directory / "outside"
        outside.mkdir()
        (self.root / ".reports").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(adapter.AdapterError):
            self.invoke()
        self.assertEqual(list(outside.iterdir()), [])

    def test_wrong_profile_duplicate_json_and_traversal_are_rejected(self) -> None:
        self.request["profile"]["sha256"] = "0" * 64
        with self.assertRaises(adapter.AdapterError):
            self.invoke()
        with self.assertRaises(adapter.AdapterError):
            adapter.decode(b'{"mode":"advisory","mode":"required"}')
        self.request["output"]["path"] = ".reports/architecture-validation/../../outside.json"
        with self.assertRaises(adapter.AdapterError):
            self.invoke()
        self.assertFalse((self.directory / "outside.json").exists())

    def test_fifo_read_is_rejected_before_open_can_block(self) -> None:
        path = self.directory / "pipe"
        os.mkfifo(path)
        with self.assertRaises(adapter.AdapterError):
            adapter.read_file(path)

    def test_process_output_and_time_are_bounded(self) -> None:
        with self.assertRaises(adapter.AdapterError):
            adapter.execute([sys.executable, "-c", "print('x' * 10000)"], cwd=self.directory, limit=100)
        with self.assertRaises(adapter.AdapterError):
            adapter.execute([sys.executable, "-c", "import time; time.sleep(3)"], cwd=self.directory, timeout=0.1)


@unittest.skipUnless(RUNTIME, "set RELAY_ARCHITECTURE_RUNTIME to a prepared pinned native runtime")
class ArchitectureAdapterNativeTests(AdapterFixture):
    def test_runtime_artifact_tamper_is_rejected(self) -> None:
        copied = self.directory / "trusted-runtime-copy"
        shutil.copytree(self.runtime, copied)
        self.runtime = copied
        (copied / "egolint/.config/rules/repository-intelligence.v1.toml").write_text("tampered\n")
        result = self.invoke()
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-PIN-001")
        self.assertEqual(result["semantic_status"], "unavailable")

    def test_report_schema_rejects_arbitrary_upstream_prose(self) -> None:
        self.add_adrs()
        self.commit()
        result = self.invoke()
        evidence = self.artifact(result, "repository_intelligence")
        evidence["source_text"] = "PRIVATE_CANARY"
        with self.assertRaises(adapter.AdapterError):
            adapter.validate_evidence(evidence)

    def test_conformant_contract_is_read_only_and_reproducible(self) -> None:
        self.add_contract()
        self.commit()
        before = adapter.git(self.root, "status", "--porcelain=v1")
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "conformant")
        self.assertEqual(before, adapter.git(self.root, "status", "--porcelain=v1"))
        copied = self.directory / "differently-named-checkout"
        shutil.copytree(self.root, copied)
        self.root = copied
        again = self.invoke()
        self.assertEqual(result, again)
        for path in result["artifacts"].values():
            if path:
                self.assertEqual((copied / path).read_bytes(), (self.directory / "consumer" / path).read_bytes())

    def test_missing_contract_file_preserves_rule_location_and_sarif(self) -> None:
        self.add_contract()
        (self.root / "README.md").unlink()
        self.commit()
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(result["outcome"], "warning")
        self.assertEqual(result["findings"][0]["id"], "EGO-CONTRACT-FILE-001")
        self.assertEqual(result["findings"][0]["path"], "README.md")
        sarif = self.artifact(result, "egolint_sarif")
        self.assertEqual(sarif["runs"][0]["results"][0]["properties"]["egolintRuleId"], "EGO-CONTRACT-FILE-001")
        self.assertTrue(sarif["runs"][0]["tool"]["driver"]["rules"])

    def test_ratified_adr_is_conformant_with_exact_upstream_provenance(self) -> None:
        self.add_adrs()
        self.commit()
        before = adapter.git(self.root, "status", "--porcelain=v1")
        result = self.invoke()
        self.assertEqual(self.artifact(result, "repository_intelligence")["status"], "valid")
        self.assertEqual(result["semantic_status"], "conformant")
        self.assertEqual(result["coverage"]["architecture-records"], "passed")
        self.assertEqual(result["findings"], [])
        self.assertEqual(before, adapter.git(self.root, "status", "--porcelain=v1"))
        self.assertIn({"repository": "egohygiene/egolint",
                       "revision": "933472b6322d2060c487e5a8a6f0bc5197696af0",
                       "profile_source_id": "egolint-repository-validation"}, result["provenance"])

    def test_catalog_drift_still_caps_native_validity_at_partial(self) -> None:
        self.add_adrs()
        self.commit()
        definitions = deepcopy(adapter.catalog(self.runtime))
        pin = next(p for p in definitions["pins"] if p["id"] == "egohygiene.architecture-decision/v1")
        pin["source-revision"] = "f598ed659a43dd759d4ede41c27f9e5daf991aa7"
        with mock.patch.object(adapter, "catalog", return_value=definitions):
            result = self.invoke()
        self.assertEqual(self.artifact(result, "repository_intelligence")["status"], "valid")
        self.assertEqual(result["semantic_status"], "incomplete")
        self.assertEqual(result["coverage"]["architecture-records"], "partial")
        self.assertIn("RELAY-ARCH-COMPAT-001", [f["id"] for f in result["findings"]])

    def test_accepted_without_authority_is_invalid_even_in_advisory_mode(self) -> None:
        self.add_adrs()
        self.put("docs/decisions/ADR-001-repository-records.md", ADR.replace("status: proposed", "status: accepted"))
        self.commit()
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(result["outcome"], "warning")
        self.assertIn("EGO-INTEL-ADR-LIFECYCLE-001", [f["id"] for f in result["findings"]])
        self.assertEqual(self.artifact(result, "repository_intelligence")["status"], "invalid")

    def test_old_policy_pin_is_rejected_without_rewriting_the_consumer(self) -> None:
        self.add_adrs()
        path = self.root / "docs/decisions/policy-reference.json"
        reference = json.loads(path.read_bytes())
        reference["policy"]["source"]["revision"] = "f598ed659a43dd759d4ede41c27f9e5daf991aa7"
        path.write_text(json.dumps(reference))
        self.commit()
        before = path.read_bytes()
        result = self.invoke()
        self.assertIn("EGO-INTEL-CONTRACT-001", [f["id"] for f in result["findings"]])
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(result["coverage"]["architecture-records"], "failed")
        self.assertEqual(path.read_bytes(), before)

    def test_missing_index_and_duplicate_id_are_native_findings(self) -> None:
        self.add_adrs()
        self.put("docs/decisions/ADR-001-duplicate.md", ADR)
        (self.root / "docs/decisions/README.md").unlink()
        self.commit()
        result = self.invoke()
        ids = {f["id"] for f in result["findings"]}
        self.assertTrue({"EGO-INTEL-ADR-INDEX-001", "EGO-INTEL-ADR-METADATA-001"}.issubset(ids))

    def test_disabled_adr_rules_cannot_create_false_conformance(self) -> None:
        self.add_adrs()
        path = self.root / "policy/intelligence.toml"
        path.write_text(path.read_text().replace('"EGO-INTEL-ADR-LIFECYCLE-001", ', ""))
        self.commit()
        result = self.invoke()
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-POLICY-001")
        self.assertEqual(result["semantic_status"], "nonconformant")

    def test_malformed_policy_is_distinct_from_missing_runtime(self) -> None:
        self.add_contract()
        self.put("policy/contract.toml", "invalid = [\n")
        self.commit()
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-POLICY-001")

    def test_immutable_snapshot_ignores_later_worktree_changes(self) -> None:
        self.add_contract()
        self.commit()
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "conformant")
        self.put("README.md", "changed after the represented commit\r\nline\n")
        self.assertEqual(result, self.invoke())

    def test_working_tree_includes_edits_without_claiming_a_commit(self) -> None:
        self.add_contract()
        self.commit()
        self.request["repository"]["represented_revision"] = "working-tree"
        self.put("README.md", "changed\n")
        result = self.invoke()
        self.assertEqual(result["semantic_status"], "incomplete")
        self.assertIn("RELAY-ARCH-REVISION-001", [f["id"] for f in result["findings"]])
        self.assertEqual((self.root / "README.md").read_text(), "changed\n")

    def test_snapshot_does_not_execute_git_filters_or_fsmonitor(self) -> None:
        self.add_contract()
        self.commit()
        marker = self.directory / "executed"
        adapter.git(self.root, "config", "core.fsmonitor", f"touch {marker}")
        adapter.git(self.root, "config", "filter.poison.clean", f"touch {marker}")
        self.put(".gitattributes", "*.md filter=poison\n")
        self.request["repository"]["represented_revision"] = "working-tree"
        result = self.invoke()
        self.assertNotEqual(result["semantic_status"], "unavailable")
        self.assertFalse(marker.exists())

    def test_symlink_snapshot_never_reads_target(self) -> None:
        self.add_contract()
        outside = self.directory / "PRIVATE_CANARY"
        outside.write_text("PRIVATE_CANARY_CONTENT")
        (self.root / "linked").symlink_to(outside)
        self.commit()
        result = self.invoke()
        self.assertEqual(result["findings"][0]["id"], "RELAY-ARCH-PATH-001")
        self.assertNotIn("PRIVATE_CANARY", json.dumps(result))

    def test_snapshot_bounds_prevent_partial_validation(self) -> None:
        self.add_contract()
        self.commit()
        self.request["bounds"]["maximum_scanned_files"] = 1
        result = self.invoke()
        self.assertTrue(result["bounds"]["scan_truncated"])
        self.assertEqual(result["semantic_status"], "incomplete")
        self.assertIsNone(result["artifacts"]["egolint_run"])

    def test_private_source_text_is_absent_from_all_retained_reports(self) -> None:
        self.add_contract('''[[requirements]]
id = "source-marker"
path = "README.md"
kind = "file"
ownership = "generated"
markers = ["PRIVATE_CANARY_CONTENT"]
''')
        self.request["repository"]["visibility"] = "private"
        self.commit()
        result = self.invoke()
        self.assertEqual(result["privacy"]["classification"], "private-repository")
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertIsNotNone(result["artifacts"]["egolint_sarif"])
        for path in (self.root / ".reports").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"PRIVATE_CANARY", path.read_bytes())
                self.assertNotIn(str(self.directory).encode(), path.read_bytes())

    def test_findings_are_bounded_without_losing_invalid_status(self) -> None:
        self.add_adrs()
        self.put("docs/decisions/ADR-001-repository-records.md", ADR.replace("status: proposed", "status: accepted"))
        (self.root / "docs/decisions/README.md").unlink()
        self.commit()
        self.request["bounds"]["maximum_findings"] = 1
        result = self.invoke()
        self.assertEqual(result["counts"]["total"], 1)
        self.assertTrue(result["bounds"]["findings_truncated"])
        self.assertEqual(result["semantic_status"], "nonconformant")
        self.assertEqual(len(self.artifact(result, "egolint_sarif")["runs"][0]["results"]), 1)

    def test_legacy_and_diagram_states_remain_distinct(self) -> None:
        self.add_contract()
        self.commit()
        self.request["adoption"]["repository-contracts"] = "legacy"
        legacy = self.invoke()
        self.assertEqual(legacy["semantic_status"], "legacy")
        self.assertEqual(legacy["coverage"]["repository-contracts"], "partial")
        self.request["adoption"]["repository-contracts"] = "present"
        self.request["adoption"]["diagram-sources"] = "present"
        self.request["inputs"]["diagram_roots"] = ["diagrams"]
        result = self.invoke()
        self.assertEqual(result["coverage"]["diagram-sources"], "unavailable")
        self.assertEqual(result["semantic_status"], "incomplete")

    def test_bounded_history_retains_upstream_truncation(self) -> None:
        self.add_adrs()
        self.commit()
        self.commit()
        with mock.patch.object(adapter, "MAX_HISTORY", 1):
            result = self.invoke()
        self.assertTrue(self.artifact(result, "repository_intelligence")["commit_history_truncated"])
        self.assertEqual(result["semantic_status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
